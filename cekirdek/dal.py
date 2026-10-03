# -*- coding: utf-8 -*-
"""
================================================================================
 dal.py  --  Dal (branch) hesaplari: yanma x T_yakit x C_bor (x T_mod / rho_mod)
================================================================================

 Kafes kodlarinin "branch" / "shutdown" tablosu. Bir tukenme sonucundaki
 (Y4, depletion_results.h5) secili yanma noktalarinda BILESIM SABIT tutulur
 (yanma ilerlemez); yalniz kosul degisir ve yalniz transport kosulur:

   yanma adimi i  x  {T_yakit} x {C_bor} x {T_mod, rho_mod}  ->  k +- sigma

 Bu, ayni bilesimde kosul degisiminin ANLIK etkisidir (Doppler, bor degeri,
 moderator sicaklik/yogunluk katsayilari yanmanin fonksiyonu olarak); yeni bir
 tukenme degildir. Reaktivite katsayisi icin tek degiskenli tarama
 (cekirdek/tarama.py) ayni kosullari AYNI kodla (tarama.parametre_uygula)
 uygular: yanma adimi 0 dali ayni kosuldaki taramayla istatistik icinde ayni
 k'yi verir (testler/test_y5_dal.py).

 NASIL CALISIR
   1. Kosul degistirilmis spec: dal_spec (tarama.parametre_uygula; taban spec
      DEGISMEZ).
   2. Model tukenme.hazirla(spec) ile kurulur (bolme + cubuk cubuk klonlar
      tukenme kosusundakiyle AYNI sirada; malzeme kimlikleri kurucu.kur'un
      reset_auto_ids'i sayesinde ayni). Her klonun hacmi sonuc dosyasindakiyle
      karsilastirilir; uyusmazsa ValueError (yanlis bilesim sessizce
      yazilmaz).
   3. Bilesim_uygula: sonuc dosyasindaki adim bilesimi malzemelere yazilir.
      Mantik OpenMC 0.16 Results.export_to_materials ile AYNI (once
      malzemenin atom/b-cm yogunluklari, sonra zincirde olup tesir kesiti
      bulunan nuklidlerin yanma adimindaki atom sayilari / hacim); fark: bellek
      icinde ve kimlik/hacim denetimiyle.
   4. Model model.xml olarak yazilir ve Y10 kuyruguna spec'siz is olarak
      girer (cekirdek/kuyruk.py). Etiket: {"dal": {"adim", "yanma",
      "zaman_d", "nokta", "degerler"}}.

 TABLO: dal_tablosu(durumlar) -> DalSatiri; dk [pcm] = (k - k_taban) x 1e5,
 sigma_dk = hypot(sigma, sigma_taban) x 1e5 (kosular bagimsiz sayilir;
 ayni tohum kullanildigindan gercek belirsizlik daha kucuktur: muhafazakar).
 rho_pcm = (1/k_taban - 1/k) x 1e5: REAKTIVITE farki (kosu_gecmisi.k_farki ile
 ayni tanim; katsayi okumasi icin dk degil bu sutun). sigma_rho = 1e5 x
 hypot(sigma/k^2, sigma_taban/k_taban^2).
 KRITIK ARAMA: tukenmede bor/cubuk aramasi aciksa dal modeli spec'in STATIK
 degeriyle kurulur (adim basina aranan deger uygulanmaz): kritik_arama_notu uyarir.

 TERMINAL
   python3 -m cekirdek.dal model.json tukenme_dizini --adimlar 0,4,8 \\
       --yakit-sicaklik 600,900 --bor 0,500 --cikti dal_kosulari
================================================================================
"""

from __future__ import annotations

import copy
import functools
import itertools
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from cekirdek import sema
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

PCM = 1.0e5
BICIMLER = ("kartezyen", "tek")
HACIM_TOLERANSI = 1.0e-9           # klon hacmi: model ile sonuc dosyasi (goreli)
ETIKET = "dal"
KUYRUK_ADI = N_("Dal")

# Tarama turu -> (kisa ad, birim, hedef rolu). Turler tarama.TURLER anahtaridir:
# dal koşulu tek degiskenli taramayla AYNI yoldan uygulanir.
TURLER = {
    "yakit_sicaklik": ("T_yakit", "K", "yakit"),
    "bor_ppm": ("C_bor", "ppm", "sogutucu"),
    "sogutucu_sicaklik": ("T_mod", "K", "sogutucu"),
    "malzeme_yogunluk": ("rho_mod", "g/cm3", "sogutucu"),
}
TUR_ADLARI = {
    "yakit_sicaklik": N_("Yakıt sıcaklığı [K]"),
    "bor_ppm": N_("Çözünmüş bor [ppm]"),
    "sogutucu_sicaklik": N_("Soğutucu sıcaklığı [K] (yoğunluk korelasyonla)"),
    "malzeme_yogunluk": N_("Soğutucu yoğunluğu [g/cm³]"),
}


@dataclass(frozen=True)
class DalDegiskeni:
    """Bir dal degiskeni: tarama turu, uygulanacak malzemeler ve degerleri."""
    tur: str
    hedefler: Tuple[str, ...]
    degerler: Tuple[float, ...]

    def __post_init__(self) -> None:
        if self.tur not in TURLER:
            raise ValueError(_("bilinmeyen dal değişkeni: %s") % self.tur)
        if not self.hedefler:
            raise ValueError(_("'%s' dal değişkeninin hedef malzemesi yok") % self.ad)
        if not self.degerler:
            raise ValueError(_("'%s' dal değişkeninin değeri yok") % self.ad)
        for d in self.degerler:
            if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d):
                raise ValueError(_("dal değeri sonlu bir sayı olmalı: %r") % (d,))

    @property
    def ad(self) -> str:
        return TURLER[self.tur][0]

    @property
    def birim(self) -> str:
        return TURLER[self.tur][1]


@dataclass(frozen=True)
class DalAyar:
    """Dal hesabi: yanma adimlari (sonuc dosyasindaki zaman noktasi indeksleri) ve degiskenler."""
    adimlar: Tuple[int, ...]
    degiskenler: Tuple[DalDegiskeni, ...] = ()
    taban: bool = True            # kosulu degismemis (taban) dal da kosulur
    bicim: str = "kartezyen"      # kartezyen (butun bilesimler) | tek (her degisken kendi basina)

    def __post_init__(self) -> None:
        if not self.adimlar:
            raise ValueError(_("en az bir yanma adımı seçin"))
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in self.adimlar):
            raise ValueError(_("yanma adımı indeksi negatif olmayan tam sayı olmalı"))
        if self.bicim not in BICIMLER:
            raise ValueError(_("dal biçimi %s olmalı: %s") % (" / ".join(BICIMLER), self.bicim))
        adlar = [d.ad for d in self.degiskenler]
        if len(set(adlar)) != len(adlar):
            raise ValueError(_("dal değişkenleri benzersiz olmalı: %s") % ", ".join(adlar))
        if not self.degiskenler and not self.taban:
            raise ValueError(_("dal değişkeni yok ve taban dal kapalı: koşulacak bir şey yok"))
        n = len(self.adimlar) * len(noktalar(self))
        from cekirdek import parametre
        if n > parametre.MAKS_NOKTA:
            raise ValueError(_("dal tablosu %d koşu üretir; en çok %d") % (n, parametre.MAKS_NOKTA))


@dataclass(frozen=True)
class DalSatiri:
    adim: int
    zaman_d: float
    yanma: float
    nokta: int
    degerler: Mapping[str, float]
    k: Optional[float]
    sapma: Optional[float]
    dk_pcm: Optional[float]
    dk_sapma_pcm: Optional[float]
    hata: Optional[str] = None
    rho_pcm: Optional[float] = None
    rho_sapma_pcm: Optional[float] = None


# ============================================================================
# degiskenler
# ============================================================================

def _yakit_adlari(spec: Mapping[str, Any]) -> Tuple[str, ...]:
    from cekirdek import tukenme
    return tuple(m["ad"] for m in spec.get("malzemeler") or []
                 if m["ad"] in tukenme.yanabilir_adlar(spec) and tukenme._fisil_mi(m))


def _sogutucu_adlari(spec: Mapping[str, Any]) -> Tuple[str, ...]:
    from cekirdek import uygunluk
    return tuple(m["ad"] for m in spec.get("malzemeler") or []
                 if uygunluk.tek_malzeme_rolleri(m) & {"sogutucu", "moderator"})


def varsayilan_hedefler(spec: Mapping[str, Any], tur: str) -> Tuple[str, ...]:
    """Dal degiskeninin varsayilan malzemeleri: yakit (fisil yanabilir) ya da sogutucu/moderator."""
    if tur not in TURLER:
        raise ValueError(_("bilinmeyen dal değişkeni: %s") % tur)
    return _yakit_adlari(spec) if TURLER[tur][2] == "yakit" else _sogutucu_adlari(spec)


def degisken(spec: Mapping[str, Any], tur: str, degerler: Sequence[float],
             hedefler: Optional[Sequence[str]] = None) -> DalDegiskeni:
    """Dal degiskeni; hedefler verilmezse varsayilan_hedefler. Bos hedef ValueError."""
    h = tuple(hedefler) if hedefler else varsayilan_hedefler(spec, tur)
    if not h:
        raise ValueError(_("'%s' için modelde uygun malzeme yok") % TURLER[tur][0])
    return DalDegiskeni(tur, h, tuple(float(d) for d in degerler))


def kritik_arama_notu(spec: Mapping[str, Any]) -> Optional[str]:
    """Tukenmede kritiklik aramasi (bor/cubuk) acikken dal tablosunun taban
    kosulu uyarisi; arama kapaliysa None."""
    from cekirdek import tukenme_ayar
    k = tukenme_ayar.kritik_arama((spec or {}).get("tukenme") or {})
    if not k.var:
        return None
    return _("Tükenmede kritiklik araması (%s) açıktı: dal modeli adım başına aranan değeri "
             "değil, modeldeki sabit değeri kullanır; taban dal tükenmenin k'sına "
             "eşit değildir.") % (_("bor") if k.tur == "bor" else _("çubuk"))


def noktalar(ayar: DalAyar) -> List[Dict[str, float]]:
    """Kosul noktalari: once taban ({}), sonra kartezyen biciminde degiskenlerin
    carpimi (ilk degisken en dista); "tek" biciminde her degiskenin degerleri
    ayri (digerleri tabanda; tek degiskenli taramayla ayni nokta kumesi)."""
    cikti: List[Dict[str, float]] = [{}] if ayar.taban else []
    if ayar.bicim == "tek":
        return cikti + [{d.ad: v} for d in ayar.degiskenler for v in d.degerler]
    if ayar.degiskenler:
        adlar = [d.ad for d in ayar.degiskenler]
        for b in itertools.product(*[d.degerler for d in ayar.degiskenler]):
            cikti.append(dict(zip(adlar, b)))
    return cikti


def dal_spec(spec: Mapping[str, Any], ayar: DalAyar, nokta: Mapping[str, float]
             ) -> Tuple[Dict[str, Any], List[str]]:
    """Kosul noktasi uygulanmis YENI spec (taban DEGISMEZ) ve notlar. Uygulama
    tek degiskenli tarama ile AYNI: tarama.parametre_uygula."""
    from cekirdek import tarama
    sonuc: Dict[str, Any] = copy.deepcopy(dict(spec))
    notlar: List[str] = []
    for d in ayar.degiskenler:
        if d.ad not in nokta:
            continue
        for hedef in d.hedefler:
            sonuc, notu = tarama.parametre_uygula(sonuc, d.tur, hedef, nokta[d.ad], taban=spec)
            if notu and notu not in notlar:
                notlar.append(notu)
    return sonuc, notlar


# ============================================================================
# model: bilesim yazma
# ============================================================================

@functools.lru_cache(maxsize=4)
def _veri_nuklidleri(yol: Optional[str] = None) -> frozenset:
    """Tesir kesiti kutuphanesindeki notron nuklidleri (OpenMC DataLibrary)."""
    import openmc.data
    kutuphane = openmc.data.DataLibrary.from_xml(yol) if yol else openmc.data.DataLibrary.from_xml()
    return frozenset(n for k in kutuphane.libraries if k["type"] == "neutron"
                     for n in k["materials"])


def bilesim_uygula(model: Any, sonuclar: Any, adim: int,
                   veri_nuklidleri: Optional[frozenset] = None) -> int:
    """
    Sonuc dosyasindaki 'adim' bilesimini model malzemelerine YERINDE yazar
    (tukenme.hazirla'nin dondurdugu model; bu fonksiyon dalin kendi modelini
    degistirir). DONER bilesimi yazilan malzeme sayisi.

    Sonuctaki her malzeme modelde kimlikle bulunmali ve hacmi eslesmeli
    (HACIM_TOLERANSI); aksi halde ValueError. Sonuc dosyasinda olmayan
    (yanmayan) malzemeler aynen kalir.
    """
    if not (0 <= adim < len(sonuclar)):
        raise ValueError(_("yanma adımı %d: sonuç dosyasında %d zaman noktası var")
                         % (adim, len(sonuclar)))
    if veri_nuklidleri is None:
        veri_nuklidleri = _veri_nuklidleri()
    res = sonuclar[adim]
    modeldekiler = {str(m.id): m for m in model.materials}
    eksik = [i for i in res.index_mat if i not in modeldekiler]
    if eksik:
        raise ValueError(_("sonuç dosyasındaki malzemeler modelde yok (kimlik: %s): tükenme "
                           "koşusundaki modelle bu model aynı değil") % ", ".join(sorted(eksik)))
    for mid in res.index_mat:
        m = modeldekiler[mid]
        v = float(res.volume[mid])
        if not m.volume or abs(m.volume - v) > HACIM_TOLERANSI * v:
            raise ValueError(_("malzeme %s hacmi modelde %r, sonuç dosyasında %r cm³: tükenme "
                               "koşusundaki modelle bu model aynı değil") % (mid, m.volume, v))
        _malzemeye_yaz(m, res, mid, v, veri_nuklidleri)
    return len(res.index_mat)


def _malzemeye_yaz(m: Any, res: Any, mid: str, hacim: float, veri: frozenset) -> None:
    yogunluklar = m.get_nuclide_atom_densities()          # atom/b-cm (elementler acilmis)
    for nuklid, deger in yogunluklar.items():
        m.remove_nuclide(nuklid)
        m.add_nuclide(nuklid, deger)
    m.set_density("sum")
    for nuklid in res.index_nuc:
        if nuklid not in veri:
            continue
        atom = res[mid, nuklid]
        if atom > 0.0:
            m.remove_nuclide(nuklid)                       # varsa degistir
            m.add_nuclide(nuklid, 1.0e-24 * atom / hacim)
    m.depletable = False                                   # dal: yalniz transport


def dal_modeli(spec: Mapping[str, Any], sonuclar: Any, adim: int, ayar: DalAyar,
               nokta: Mapping[str, float]) -> Tuple[Any, List[str]]:
    """(model, notlar): kosulu uygulanmis spec'ten tukenme.hazirla modeli +
    adim bilesimi. spec TUKENME KOSUSUNDA KULLANILAN spec olmali (kosu dizinindeki
    spec kaydi: tukenme_kayit); farkliysa hacim/kimlik denetimi ValueError verir."""
    from cekirdek import tukenme
    s, notlar = dal_spec(spec, ayar, nokta)
    model, _bilgi = tukenme.hazirla(s)
    bilesim_uygula(model, sonuclar, adim)
    return model, notlar


# ============================================================================
# kuyruk
# ============================================================================

def adim_listesi(h5: str, spec: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Sonuc dosyasinin zaman noktalari: [{"adim", "zaman_d", "yanma", "guclu"}] --
    arayuz yanma adimi secimi icin."""
    from cekirdek import tukenme
    r = tukenme.sonuc_oku(h5, spec, izlenen=[])
    return [{"adim": i, "zaman_d": r["zaman_d"][i], "yanma": r["yanma"][i],
             "guclu": r["guclu"][i]} for i in range(len(r["zaman_d"]))]


def _k_kancasi(statepoint: str, _is: Any) -> Dict[str, Any]:
    import openmc
    with openmc.StatePoint(statepoint, autolink=False) as f:
        k = f.keff
    return {"keff": None if k is None else (float(k.n), float(k.s))}


def _is_adi(adim: int, yanma: float, nokta: Mapping[str, float]) -> str:
    kosul = ", ".join("%s=%g" % kv for kv in nokta.items()) or _("taban")
    return "%s %d (%.3g MWd/kg): %s" % (_(KUYRUK_ADI), adim, yanma, kosul)


def kuyruga_ekle(spec: Mapping[str, Any], h5: str, ayar: DalAyar, kuyruk: Any, kok_dizin: str,
                 is_parcacigi: int = 1) -> List[str]:
    """
    Her (yanma adimi x kosul) icin model.xml yazar ve spec'siz is olarak
    kuyruga ekler. DONER kimlikler (adim sirasiyla, sonra nokta sirasiyla).
    ATOMIK: hazirlikta hata (ValueError, sonuc/model uyusmazligi) olursa HICBIR is
    eklenmez; ekleme yarida hata verirse eklenenler geri alinir.
    """
    import openmc.deplete as d
    from cekirdek import kuyruk as _kq
    sonuclar = d.Results(h5)
    adimlar = adim_listesi(h5, spec)
    gecersiz = [i for i in ayar.adimlar if i >= len(adimlar)]
    if gecersiz:
        raise ValueError(_("yanma adımı %d: sonuç dosyasında %d zaman noktası var")
                         % (gecersiz[0], len(adimlar)))
    hazir = []
    arama_notu = kritik_arama_notu(spec)
    alinmis = [x.dizin for x in kuyruk.durumlar()]
    for adim in ayar.adimlar:
        for sira, nokta in enumerate(noktalar(ayar)):
            with _kq.hazirlik_kilidi():            # openmc Python API is parcacigi guvenli degil
                model, notlar = dal_modeli(spec, sonuclar, adim, ayar, nokta)
                if arama_notu:
                    notlar = list(notlar) + [arama_notu]
                dizin = _kq.ayri_dizin(kok_dizin, "adim%02d_dal%03d" % (adim, sira), alinmis,
                                       olustur=True)
                alinmis.append(dizin)
                model.export_to_model_xml(os.path.join(dizin, "model.xml"))
            etiket = {ETIKET: {"adim": adim, "yanma": adimlar[adim]["yanma"],
                               "zaman_d": adimlar[adim]["zaman_d"], "nokta": sira,
                               "degerler": dict(nokta), "notlar": list(notlar)}}
            hazir.append(_kq.KosuIsi(ad=_is_adi(adim, adimlar[adim]["yanma"], nokta), dizin=dizin,
                                     spec=None, is_parcacigi=int(is_parcacigi),
                                     sonuc_kancasi=_k_kancasi, etiket=etiket))
    kimlikler: List[str] = []
    try:
        for is_ in hazir:
            kimlikler.append(kuyruk.ekle(is_))
    except Exception:
        _log.warning("dal koşuları kuyruğa eklenemedi; %d iş geri alınıyor", len(kimlikler),
                     exc_info=True)
        for kimlik in kimlikler:
            kuyruk.iptal(kimlik)
            if kuyruk.durum(kimlik).bitti_mi:
                kuyruk.kaldir(kimlik)
        raise
    return kimlikler


# ============================================================================
# tablo
# ============================================================================

def dal_tablosu(durumlar: Sequence[Any]) -> List[DalSatiri]:
    """Kuyruk durumlarindan dal tablosu (adim, nokta sirasiyla). Dal etiketi
    olmayan isler atlanir. dk, ayni adimin TABAN dalina (nokta 0, degerler bos)
    gore; taban yoksa ya da basarisizsa None."""
    etiketli = [x for x in durumlar if ETIKET in (x.etiket or {})]
    taban: Dict[int, Tuple[float, float]] = {}
    for x in etiketli:
        e = x.etiket[ETIKET]
        if not e["degerler"] and x.k is not None:
            taban[e["adim"]] = x.k
    satirlar = []
    for x in sorted(etiketli, key=lambda y: (y.etiket[ETIKET]["adim"], y.etiket[ETIKET]["nokta"])):
        e = x.etiket[ETIKET]
        k = x.k
        t = taban.get(e["adim"])
        dk = ds = rho = rho_s = None
        if k is not None and t is not None:
            dk = (k[0] - t[0]) * PCM
            ds = math.hypot(k[1], t[1]) * PCM
            if k[0] > 0 and t[0] > 0:
                rho = (1.0 / t[0] - 1.0 / k[0]) * PCM
                rho_s = PCM * math.hypot(k[1] / k[0] ** 2, t[1] / t[0] ** 2)
        satirlar.append(DalSatiri(
            e["adim"], e["zaman_d"], e["yanma"], e["nokta"], dict(e["degerler"]),
            None if k is None else k[0], None if k is None else k[1], dk, ds,
            x.hata if x.asama.value in ("basarisiz", "iptal") else None, rho, rho_s))
    return satirlar


def degisken_adlari(satirlar: Sequence[DalSatiri]) -> List[str]:
    """Tablodaki degisken adlari (ilk gorulme sirasiyla)."""
    adlar: List[str] = []
    for s in satirlar:
        for a in s.degerler:
            if a not in adlar:
                adlar.append(a)
    return adlar


def csv_metni(satirlar: Sequence[DalSatiri]) -> str:
    """Dal tablosu CSV (ondalik nokta; sutun anahtarlari sabit, cevrilmez)."""
    from cekirdek.guc_tablo import satirlar_csv
    adlar = degisken_adlari(satirlar)
    veri: List[List[Any]] = [["adim", "zaman_gun", "yanma_MWd_kg"] + adlar
                             + ["k", "k_sigma", "dk_pcm", "dk_sigma_pcm",
                                                "rho_pcm", "rho_sigma_pcm", "hata"]]
    for s in satirlar:
        veri.append([s.adim, s.zaman_d, s.yanma] + [s.degerler.get(a) for a in adlar]
                    + [s.k, s.sapma, s.dk_pcm, s.dk_sapma_pcm,
                                  s.rho_pcm, s.rho_sapma_pcm, s.hata or ""])
    return satirlar_csv(veri)


# ============================================================================
# terminal
# ============================================================================

def _sayilar(metin: str) -> Tuple[float, ...]:
    return tuple(float(p) for p in metin.replace(";", ",").split(",") if p.strip())


def _terminal(argv: Sequence[str]) -> int:
    import argparse
    from cekirdek import kuyruk as _kq, tukenme_kayit
    ap = argparse.ArgumentParser(prog="python3 -m cekirdek.dal", description=__doc__.split("\n")[1])
    ap.add_argument("spec")
    ap.add_argument("tukenme_dizini")
    ap.add_argument("--adimlar", required=True, help="sonuc zaman noktasi indeksleri: 0,4,8")
    ap.add_argument("--yakit-sicaklik")
    ap.add_argument("--bor")
    ap.add_argument("--sogutucu-sicaklik")
    ap.add_argument("--sogutucu-yogunluk")
    ap.add_argument("--cikti", default="dal_kosulari")
    ap.add_argument("--is-parcacigi", type=int, default=0)
    ap.add_argument("--csv")
    ap.add_argument("--bicim", choices=BICIMLER, default="kartezyen")
    a = ap.parse_args(list(argv))
    spec = sema.yukle(a.spec)
    kayit = tukenme_kayit._kayit_oku(a.tukenme_dizini)
    taban = kayit or spec
    h5 = os.path.join(a.tukenme_dizini, "depletion_results.h5")
    secim = (("yakit_sicaklik", a.yakit_sicaklik), ("bor_ppm", a.bor),
             ("sogutucu_sicaklik", a.sogutucu_sicaklik), ("malzeme_yogunluk", a.sogutucu_yogunluk))
    ayar = DalAyar(tuple(int(x) for x in _sayilar(a.adimlar)),
                   tuple(degisken(taban, t, _sayilar(v)) for t, v in secim if v),
                   bicim=a.bicim)
    with _kq.Kuyruk(en_fazla_paralel=1) as k:
        kuyruga_ekle(taban, h5, ayar, k, os.path.abspath(a.cikti),
                     is_parcacigi=a.is_parcacigi or (os.cpu_count() or 1))
        k.baslat()
        k.bekle()
        satirlar = dal_tablosu(k.durumlar())
    metin = csv_metni(satirlar)
    if a.csv:
        with open(a.csv, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
    sys.stdout.write(metin)
    return 1 if any(s.hata for s in satirlar) else 0


if __name__ == "__main__":
    from cekirdek.ceviri import terminal_dili
    terminal_dili()
    sys.exit(_terminal(sys.argv[1:]))
