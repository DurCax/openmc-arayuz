# -*- coding: utf-8 -*-
"""
================================================================================
 bolge_bol.py  --  Tukenme bolgesi bolme: radyal halka ve eksenel dilim (v3 Y5)
================================================================================

 Serpent'in `div` komutunun karsiligi. Tukenmede ayni malzemeden yapilmis
 bir pin tek bir ortalama bilesimle yanar; oysa yanabilir zehirli (Gd) pinde
 dis kabuk once yanar (kendinden perdeleme) ve ic kisim cok daha gec yanar.
 Pini radyal halkalara, katmani eksenel dilimlere bolup HER PARCAYI ayri
 malzeme olarak yakmak bu farki yakalar.

 SPEC ANAHTARI  tukenme.bolme  (sema.VARSAYILAN_TUKENME'de DEGIL; yoksa eski
 dosyalar gidis-donuste degismez)
   {"cubuklar": [{"cubuk": ad, "bolgeler": [i, ...] | None,
                  "halka": n, "tur": "esit_hacim" | "esit_kalinlik" |
                                      "dista_incelen", "oran": 0.6 (yalniz dista_incelen)}],
    "eksenel": {"dilim": n, "katmanlar": [i, ...] | None}}
   bolgeler None: pinin yanabilir (fisil ya da Gd/Er/B zehirli) bolgeleri.
   katmanlar None: yanabilir pin/plaka iceren eksenel katmanlar.

 NASIL CALISIR  (uygula)
   Bolme SPEC DUZEYINDE yapilir: halkalar cubugun "bolgeler" listesine (ayni
   malzeme, yeni yaricaplar), dilimler "kor.eksenel.bolgeler" listesine girer
   ve tukenme.malzemeleri_ayir acilir. Boylece geometri kurucusu, analitik
   hacimler (tukenme_hacim.cubuk_hacmi: bolge alani x katman yuksekligi),
   cubuk cubuk yanmanin ornek hacimleri, betik uretici ve K3 pin gucu
   (guc.varsayilan_hedefler butun yakit halkalarini hedefler;
   guc._parcalari_birlestir ayni konumun halka tally'lerini TOPLAR) degisiklik
   gerektirmeden ayni yolu izler. Pin gucu = tum alt bolgelerin toplami.

 HACIM KORUNUMU (analitik)
   Halka sinirlari yarim aciklikli ve son yaricap AYNEN dis yaricaptir; halka
   alanlarinin toplami pi (r_dis^2 - r_ic^2)'ye esittir (halka_hacim_denetimi,
   goreli 1e-9). Eksenel dilimler katmani h/n'lik n parcaya boler.

 HALKA SECENEKLERI (hicbiri tek "dogru" degil; etiketlidir)
   esit_hacim     her halka ayni alani (hacmi) tasir: r_k^2 = r_ic^2 + k/n (r_dis^2 - r_ic^2).
                  Cizgisel olarak dista INCELEN halkalar verir; Gd icin onerilen
                  baslangic (kendinden perdeleme dista yogun: dis halka gucun
                  cogunu tasir, K3 incelemesi). Kaynak: Serpent `div`/CASMO uygulamalari
                  Gd pinini esit hacimli ya da dista sikilasan halkalara boler.
   esit_kalinlik  r_k = r_ic + k/n (r_dis - r_ic): dista daha buyuk hacimli halkalar;
                  kiyas icindir, Gd icin onerilmez.
   dista_incelen  halka kalinliklari geometrik azalir (her halka bir icerdekinin
                  `oran` kadari, varsayilan 0.6): esit hacimden de sikisik dis halka.
                  Oran bir muhendislik tercihidir, olculmus bir esik degil.
================================================================================
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from cekirdek import sema
from cekirdek.ceviri import N_, _

ANAHTAR = "bolme"
ESIT_HACIM = "esit_hacim"
ESIT_KALINLIK = "esit_kalinlik"
DISTA_INCELEN = "dista_incelen"
TURLER = {
    ESIT_HACIM: N_("Eşit hacimli halkalar (Gd için önerilen başlangıç)"),
    ESIT_KALINLIK: N_("Eşit kalınlıklı halkalar (karşılaştırma için)"),
    DISTA_INCELEN: N_("Dışa doğru incelen halkalar (geometrik)"),
}
VARSAYILAN_TUR = ESIT_HACIM
# Arayuz sinirlari (fizik esigi degil): Serpent/CASMO uygulamalari Gd pinini
# birkac ile on halkaya boler; 20 halka ustunde her halka ayri malzeme ve
# ayri transport hucresi demektir (maliyet), anlamli ek ayrinti saglamaz.
MAKS_HALKA = 20
MAKS_DILIM = 50
INCELME_ORANI = 0.6              # dista_incelen varsayilani (tercih)
INCELME_ARALIGI = (0.2, 0.95)
GORELI_TOLERANS = 1.0e-9         # halka hacim korunumu (kabul karti)


@dataclass(frozen=True)
class HalkaBolme:
    cubuk: str
    halka: int
    tur: str = VARSAYILAN_TUR
    bolgeler: Optional[Tuple[int, ...]] = None
    oran: float = INCELME_ORANI


@dataclass(frozen=True)
class Bolme:
    cubuklar: Tuple[HalkaBolme, ...] = ()
    eksenel_dilim: int = 1
    eksenel_katmanlar: Optional[Tuple[int, ...]] = None

    @property
    def var(self) -> bool:
        return any(h.halka > 1 for h in self.cubuklar) or self.eksenel_dilim > 1


@dataclass(frozen=True)
class Halka:
    """Onizleme icin tek radyal bolge: yaricaplar [cm], malzeme, bolunmus mu."""
    r_ic: float
    r_dis: Optional[float]
    malzeme: str
    bolunmus: bool


# ============================================================================
# halka yaricaplari (saf matematik)
# ============================================================================

def halka_yaricaplari(r_ic: float, r_dis: float, n: int, tur: str = VARSAYILAN_TUR,
                      oran: float = INCELME_ORANI) -> Tuple[float, ...]:
    """r_ic..r_dis arasini n halkaya boler; n dis yaricap dondurur (sonuncusu
    TAM r_dis). 0 <= r_ic < r_dis ve n >= 1 olmali."""
    if not (isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= MAKS_HALKA):
        raise ValueError(_("halka sayısı 1–%d arasında tam sayı olmalı: %r") % (MAKS_HALKA, n))
    if not (math.isfinite(r_ic) and math.isfinite(r_dis) and 0.0 <= r_ic < r_dis):
        raise ValueError(_("halka bölmek için 0 ≤ iç yarıçap < dış yarıçap olmalı "
                           "(%r, %r)") % (r_ic, r_dis))
    if tur == ESIT_HACIM:
        a0, a1 = r_ic * r_ic, r_dis * r_dis
        r = [math.sqrt(a0 + (a1 - a0) * k / n) for k in range(1, n)]
    elif tur == ESIT_KALINLIK:
        r = [r_ic + (r_dis - r_ic) * k / n for k in range(1, n)]
    elif tur == DISTA_INCELEN:
        if not (INCELME_ARALIGI[0] <= oran <= INCELME_ARALIGI[1]):
            raise ValueError(_("incelme oranı %g–%g arasında olmalı: %r") % (*INCELME_ARALIGI, oran))
        agirlik = [oran ** k for k in range(n)]
        toplam = sum(agirlik)
        r, kum = [], 0.0
        for w in agirlik[:-1]:
            kum += w
            r.append(r_ic + (r_dis - r_ic) * kum / toplam)
    else:
        raise ValueError(_("bilinmeyen halka türü: %s") % tur)
    return tuple(r) + (float(r_dis),)


def halka_alanlari(r_ic: float, yaricaplar: Sequence[float]) -> Tuple[float, ...]:
    """Her halkanin kesit alani [cm2] (silindir): pi (r_k^2 - r_(k-1)^2)."""
    alt = [r_ic] + list(yaricaplar[:-1])
    return tuple(math.pi * (ust * ust - a * a) for a, ust in zip(alt, yaricaplar))


# ============================================================================
# okuma ve dogrulama
# ============================================================================

def _tam(deger: Any, ad: str, alt: int, ust: int) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int) or not (alt <= deger <= ust):
        raise ValueError(_("%s %d–%d arasında tam sayı olmalı: %r") % (ad, alt, ust, deger))
    return deger


def _indeksler(deger: Any) -> Optional[Tuple[int, ...]]:
    if deger is None:
        return None
    if not isinstance(deger, (list, tuple)) or not all(
            isinstance(i, int) and not isinstance(i, bool) and i >= 0 for i in deger):
        raise ValueError(_("indeks listesi geçersiz: %r") % (deger,))
    return tuple(deger)


def _halka_oku(h: Mapping[str, Any]) -> HalkaBolme:
    tur = h.get("tur") or VARSAYILAN_TUR
    if tur not in TURLER:
        raise ValueError(_("bilinmeyen halka türü: %s") % tur)
    ad = h.get("cubuk")
    if not ad or not isinstance(ad, str):
        raise ValueError(_("bölme girdisinde çubuk adı yok"))
    oran = h.get("oran", INCELME_ORANI)
    if isinstance(oran, bool) or not isinstance(oran, (int, float)):
        raise ValueError(_("incelme oranı sayı olmalı: %r") % (oran,))
    return HalkaBolme(ad, _tam(h.get("halka", 1), _("halka sayısı"), 1, MAKS_HALKA), tur,
                      _indeksler(h.get("bolgeler")), float(oran))


def bolme_oku(spec: Mapping[str, Any]) -> Optional[Bolme]:
    """spec['tukenme']['bolme'] -> Bolme; yoksa ya da bolme yapmiyorsa None.
    Gecersiz girdi ValueError (sessizce yok sayilmaz)."""
    ham = (spec.get("tukenme") or {}).get(ANAHTAR)
    if not ham:
        return None
    if not isinstance(ham, Mapping):
        raise ValueError(_("tükenme bölmesi bir sözlük olmalı"))
    halkalar = tuple(_halka_oku(h) for h in ham.get("cubuklar") or [])
    adlar = [h.cubuk for h in halkalar]
    if len(set(adlar)) != len(adlar):
        raise ValueError(_("aynı çubuk bölmede birden fazla kez: %s")
                         % ", ".join(sorted({a for a in adlar if adlar.count(a) > 1})))
    e = ham.get("eksenel") or {}
    b = Bolme(halkalar, _tam(e.get("dilim", 1), _("eksenel dilim sayısı"), 1, MAKS_DILIM),
              _indeksler(e.get("katmanlar")))
    return b if b.var else None


def yazilacak(bolme: Bolme) -> Dict[str, Any]:
    """Bolme -> spec sozlugu (varsayilanlar yazilmaz)."""
    cikti: Dict[str, Any] = {"cubuklar": []}
    for h in bolme.cubuklar:
        g: Dict[str, Any] = {"cubuk": h.cubuk, "halka": h.halka, "tur": h.tur}
        if h.bolgeler is not None:
            g["bolgeler"] = list(h.bolgeler)
        if h.tur == DISTA_INCELEN:
            g["oran"] = h.oran
        cikti["cubuklar"].append(g)
    if bolme.eksenel_dilim > 1:
        cikti["eksenel"] = {"dilim": bolme.eksenel_dilim}
        if bolme.eksenel_katmanlar is not None:
            cikti["eksenel"]["katmanlar"] = list(bolme.eksenel_katmanlar)
    return cikti


# ============================================================================
# yanabilir bolgeler
# ============================================================================

def yanabilir_bolgeler(spec: Mapping[str, Any], cubuk: Mapping[str, Any]) -> List[int]:
    """Cubugun yanabilir (fisil ya da yanabilir zehirli) malzemeli bolgeleri."""
    from cekirdek import tukenme
    sonuc = []
    for i, b in enumerate(cubuk.get("bolgeler") or []):
        m = sema.malzeme_bul(spec, b.get("malzeme")) if b.get("malzeme") else None
        if m and (tukenme._fisil_mi(m) or tukenme._zehir_mi(m)):
            sonuc.append(i)
    return sonuc


def yanabilir_cubuklar(spec: Mapping[str, Any]) -> List[str]:
    """Bolunebilir (silindirik, kontrol olmayan, yanabilir bolgeli) cubuk adlari."""
    return [c["ad"] for c in spec.get("cubuklar") or []
            if c.get("tur") != "kontrol" and (c.get("kesit") or "silindir") == "silindir"
            and yanabilir_bolgeler(spec, c)]


# ============================================================================
# uygulama (spec -> yeni spec)
# ============================================================================

def _cubugu_bol(spec: Dict[str, Any], h: HalkaBolme) -> Dict[int, List[int]]:
    """Cubugu yerinde (kopya spec) boler. DONER {eski bolge: [yeni bolgeler]}."""
    c = sema.cubuk_bul(spec, h.cubuk)
    if c is None:
        raise ValueError(_("bölmede tanımsız çubuk: %s") % h.cubuk)
    if c.get("tur") == "kontrol":
        raise ValueError(_("'%s' kontrol çubuğu bölünemez (emici bölge daldırmaya bağlı)") % h.cubuk)
    if (c.get("kesit") or "silindir") != "silindir":
        raise ValueError(_("'%s' çubuğu silindirik değil; halka bölme yalnız silindirde") % h.cubuk)
    eski = c.get("bolgeler") or []
    secili = set(h.bolgeler if h.bolgeler is not None else yanabilir_bolgeler(spec, c))
    if not secili:
        raise ValueError(_("'%s' çubuğunda bölünecek yanabilir bölge yok") % h.cubuk)
    gecersiz = sorted(i for i in secili if i >= len(eski))
    if gecersiz:
        raise ValueError(_("'%s' çubuğunda olmayan bölge: %s")
                         % (h.cubuk, ", ".join(str(i + 1) for i in gecersiz)))
    yeni: List[Dict[str, Any]] = []
    harita: Dict[int, List[int]] = {}
    r_ic = 0.0
    for i, b in enumerate(eski):
        if i not in secili or h.halka == 1:
            harita[i] = [len(yeni)]
            yeni.append(copy.deepcopy(b))
        else:
            if b.get("r") is None:
                raise ValueError(_("'%s' çubuğunun dış bölgesi (yarıçapsız) bölünemez") % h.cubuk)
            harita[i] = []
            for r in halka_yaricaplari(r_ic, float(b["r"]), h.halka, h.tur, h.oran):
                harita[i].append(len(yeni))
                yeni.append(dict(copy.deepcopy(b), r=r))
        if b.get("r") is not None:
            r_ic = float(b["r"])
    c["bolgeler"] = yeni
    return harita


def _guc_hedeflerini_tasi(spec: Dict[str, Any], haritalar: Mapping[str, Mapping[int, List[int]]]
                          ) -> None:
    """Kullanicinin guc hedefleri eski bolge numarasindadir; halka bolmeden sonra
    bolunen bolgenin TUM halkalari hedef olur (pin gucu = toplam), sonrakiler kayar."""
    g = spec.get("guc_dagilimi")
    if not isinstance(g, dict):
        return
    hedefler = sema.guc_hedefleri(g)
    if not hedefler:
        return
    yeni, goruldu = [], set()
    for hd in hedefler:
        harita = haritalar.get(hd["cubuk"])
        indeksler = harita.get(hd["bolge"], [hd["bolge"]]) if harita else [hd["bolge"]]
        for i in indeksler:
            anahtar = (hd["cubuk"], i)
            if anahtar not in goruldu:
                goruldu.add(anahtar)
                yeni.append({"cubuk": hd["cubuk"], "bolge": i})
    g.pop("cubuk", None)
    g.pop("bolge", None)
    g["cubuklar"] = yeni


def _yanabilir_parca_adlari(spec: Mapping[str, Any]) -> List[str]:
    """Yanabilir malzeme iceren cubuk ve plaka adlari (eksenel katman secimi icin)."""
    from cekirdek import tukenme
    adlar = [c["ad"] for c in spec.get("cubuklar") or [] if yanabilir_bolgeler(spec, c)]
    yanabilir = set(tukenme.yanabilir_adlar(spec))
    adlar += [p["ad"] for p in spec.get("plakalar") or [] if p.get("et_malzeme") in yanabilir]
    return adlar


def _katman_hedefleri(spec: Mapping[str, Any], katmanlar: Sequence[Mapping[str, Any]],
                      secim: Optional[Tuple[int, ...]]) -> List[int]:
    if secim is not None:
        gecersiz = [i for i in secim if i >= len(katmanlar)]
        if gecersiz:
            raise ValueError(_("olmayan eksenel katman: %s") % ", ".join(str(i + 1) for i in gecersiz))
        return sorted(set(secim))
    from cekirdek import tukenme
    kor = spec["kor"]
    parcalar = _yanabilir_parca_adlari(spec)
    hedef = []
    for i, k in enumerate(katmanlar):
        if any(tukenme._kor_sayimi(spec, kor, k.get("dolgu"), p, k.get("anahtar"))
               for p in parcalar):
            hedef.append(i)
    return hedef


def _eksenel_bol(spec: Dict[str, Any], b: Bolme) -> None:
    """Yanabilir parca iceren eksenel katmanlari h/n'lik n katmana boler (yerinde, kopya)."""
    if sema.agac_modu(spec):
        raise ValueError(_("eksenel dilim bölme gelişmiş (ağaç) modda desteklenmiyor"))
    kor = spec["kor"]
    if kor.get("tur") not in sema.EKSENEL_DESTEKLI:
        raise ValueError(_("eksenel dilim bölme bu kor türünde desteklenmiyor: %s") % kor.get("tur"))
    eks = kor.setdefault("eksenel", {})
    katmanlar = [dict(k) for k in (eks.get("bolgeler") or []) if float(k.get("yukseklik") or 0) > 0]
    if not (eks.get("var") and katmanlar):
        yuk = kor.get("yukseklik")
        if not yuk:
            raise ValueError(_("eksenel dilim bölme 3B (yükseklikli) model gerektirir"))
        katmanlar = [{"ad": _("aktif"), "yukseklik": float(yuk), "dolgu": None}]
    hedef = set(_katman_hedefleri(spec, katmanlar, b.eksenel_katmanlar))
    if not hedef:
        raise ValueError(_("eksenel olarak bölünecek yanabilir katman bulunamadı"))
    n = b.eksenel_dilim
    yeni: List[Dict[str, Any]] = []
    for i, k in enumerate(katmanlar):
        if i not in hedef:
            yeni.append(k)
            continue
        for j in range(n):
            dilim = copy.deepcopy(k)
            dilim["yukseklik"] = float(k["yukseklik"]) / n
            dilim["ad"] = "%s (%d/%d)" % (k.get("ad") or _("katman"), j + 1, n)
            yeni.append(dilim)
    eks["var"] = True
    eks["bolgeler"] = yeni


def uygula(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    """Bolmeyi uygulanmis YENI spec; bolme yoksa girdinin kendisi. Girdi degismez.
    Donen spec'te tukenme.bolme YOKTUR (ikinci uygulama bolmez) ve cubuk cubuk
    yanma (malzemeleri_ayir) aciktir: bolunen parcalar ancak boylece ayri yanar."""
    b = bolme_oku(spec)
    if b is None:
        return spec
    if sema.agac_modu(spec):
        raise ValueError(_("tükenme bölgesi bölme gelişmiş (ağaç) modda desteklenmiyor"))
    yeni = copy.deepcopy(dict(spec))
    haritalar = {h.cubuk: _cubugu_bol(yeni, h) for h in b.cubuklar}
    if b.eksenel_dilim > 1:
        _eksenel_bol(yeni, b)
    _guc_hedeflerini_tasi(yeni, haritalar)
    t = yeni["tukenme"]
    t.pop(ANAHTAR, None)
    t["malzemeleri_ayir"] = True
    return yeni


# ============================================================================
# denetim ve onizleme
# ============================================================================

def halka_hacim_denetimi(spec: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Her bolunen bolge icin analitik hacim korunumu (1 cm yukseklik basina):
    [{"cubuk", "bolge", "halka", "alan_once", "alan_sonra", "goreli_hata"}].
    alan_once = pi (r_dis^2 - r_ic^2); alan_sonra = halka alanlari toplami."""
    b = bolme_oku(spec)
    cikti = []
    for h in (b.cubuklar if b else ()):
        if h.halka < 2:
            continue
        c = sema.cubuk_bul(spec, h.cubuk)
        if c is None:
            continue
        secili = h.bolgeler if h.bolgeler is not None else tuple(yanabilir_bolgeler(spec, c))
        r_ic = 0.0
        for i, bol in enumerate(c.get("bolgeler") or []):
            if bol.get("r") is None:
                break
            r_dis = float(bol["r"])
            if i in secili:
                rr = halka_yaricaplari(r_ic, r_dis, h.halka, h.tur, h.oran)
                once = math.pi * (r_dis ** 2 - r_ic ** 2)
                sonra = math.fsum(halka_alanlari(r_ic, rr))
                cikti.append({"cubuk": h.cubuk, "bolge": i, "halka": h.halka,
                              "alan_once": once, "alan_sonra": sonra,
                              "goreli_hata": abs(sonra - once) / once})
            r_ic = r_dis
    return cikti


def kesit_onizleme(spec: Mapping[str, Any], cubuk: str) -> Tuple[Halka, ...]:
    """Cubugun bolme SONRASI radyal bolgeleri (arayuz kesiti cizer). Bolme yoksa
    ya da cubuk bolmede degilse orijinal bolgeler (bolunmus=False)."""
    b = bolme_oku(spec)
    h = next((x for x in (b.cubuklar if b else ()) if x.cubuk == cubuk and x.halka > 1), None)
    kopya = copy.deepcopy(dict(spec))
    harita = _cubugu_bol(kopya, h) if h is not None else {}
    c = sema.cubuk_bul(kopya, cubuk)
    if c is None:
        return ()
    bolunen = {j for liste in harita.values() if len(liste) > 1 for j in liste}
    sonuc, r_ic = [], 0.0
    for j, bol in enumerate(c.get("bolgeler") or []):
        sonuc.append(Halka(r_ic, bol.get("r"), bol.get("malzeme") or "", j in bolunen))
        if bol.get("r") is not None:
            r_ic = float(bol["r"])
    return tuple(sonuc)


def ornek_sayilari(spec: Mapping[str, Any]) -> Tuple[int, int]:
    """(bolmeden once, sonra) yanabilir malzeme ornek (ayri tukenme malzemesi)
    sayisi: kullaniciya maliyeti gostermek icin."""
    return _ornek_say(spec), _ornek_say(uygula(spec))


def _ornek_say(spec: Mapping[str, Any]) -> int:
    from cekirdek import tukenme, tukenme_hacim
    return sum(tukenme_hacim.ornek_sayisi(spec, ad) for ad in tukenme.yanabilir_adlar(spec))
