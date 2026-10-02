# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/y7.py  --  Y7 foton tasinimi ve sicaklik isleme kontrolleri

   - gecersiz foton / sicaklik ayari                                  -> hata
   - foton tasinimi acik, modeldeki element icin foton verisi yok     -> hata
     (OpenMC kosu basinda durur)
   - 'heating' skoru, foton KAPALI: gama enerjisi sayilmaz            -> uyari
   - 'heating-local' skoru, foton ACIK: gama iki kez sayilir          -> uyari
   - multipole acik, kutuphanede wmp kaydi yok (OpenMC yalniz uyarir) -> uyari
   - malzeme sicakligi icin kutuphanede veri yok (OpenMC durur)       -> hata
     nearest: baska bir kutuphane sicakligi kullanilir                -> uyari
     interpolation: uca yapisir                                       -> uyari
     interpolation: iki komsu sicaklik arasinda                       -> bilgi
 Kural kaynagi: cekirdek/foton.py, cekirdek/sicaklik.py modul belgeleri.
"""

from typing import Dict, List, Optional, Tuple

from cekirdek import foton, sicaklik
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
_YER = "ayarlar"
_EN_COK_AD = 6           # mesajda listelenen bilesen sayisi (gerisi "…")


def _adlar(adlar: List[str]) -> str:
    adlar = sorted(set(adlar))
    ek = ", …" if len(adlar) > _EN_COK_AD else ""
    return ", ".join(adlar[:_EN_COK_AD]) + ek


def _foton_kontrol(spec: dict, veri_kontrolu: bool, kutuphane: Optional[str]) -> List[Bulgu]:
    try:
        foton.ayar(spec)
    except ValueError as e:
        return [Bulgu("hata", _YER, str(e))]
    if not (veri_kontrolu and foton.tasinim_var_mi(spec)):
        return []
    var = foton.kutuphane_elementleri(kutuphane)
    if not var and foton.kaynak_foton_mu(spec):
        return []        # hic foton kaydi yok: dogrula/kaynak.py zaten hata verir
    eksik = foton.eksik_elementler(spec, kutuphane)
    if not eksik:
        return []
    return [Bulgu("hata", _YER,
                  _("foton taşınımı açık ama şu elementlerin foton verisi yok: %s") % _adlar(eksik),
                  _("cross_sections.xml'de type='photon' kaydı gerekir; OpenMC koşu başında "
                    "durur. Foton verisi içeren kütüphane kurun ya da foton taşınımını kapatın."))]


def _tally_skorlari(spec: dict) -> List[Tuple[str, str]]:
    sonuc = [(t.get("ad", "?"), s) for t in spec.get("tallyler") or []
             for s in t.get("skorlar") or []]
    g = spec.get("guc_dagilimi") or {}
    if g.get("var") and g.get("skor"):
        sonuc.append((None, g["skor"]))
    return sonuc


def _isinma_kontrol(spec: dict) -> List[Bulgu]:
    tasinim = foton.tasinim_var_mi(spec)
    bulgular = []
    for ad, skor in _tally_skorlari(spec):
        yer = "tally:%s" % ad if ad is not None else "guc dagilimi"
        if skor == "heating" and not tasinim:
            bulgular.append(Bulgu(
                "uyari", yer,
                _("'heating' skoru foton taşınımı kapalıyken gama enerjisini içermez"),
                _("Yalnız nötron KERMA'sı (MT301) sayılır; fisyon ve yakalama gamaları kaybolur. "
                  "Toplam ısınma için foton taşınımını açın ya da 'heating-local' kullanın.")))
        elif skor == "heating-local" and tasinim:
            bulgular.append(Bulgu(
                "uyari", yer,
                _("'heating-local' foton taşınımı açıkken gamayı ikinci kez sayar"),
                _("heating-local gama enerjisini çarpışma yerinde bırakır (MT901); fotonlar ayrıca "
                  "taşınırken toplam ısınma için 'heating' kullanın.")))
    return bulgular


def _multipole_kontrol(a: "sicaklik.SicaklikAyari", veri_kontrolu: bool,
                       kutuphane: Optional[str]) -> List[Bulgu]:
    if not (a.multipole and veri_kontrolu):
        return []
    wmp = sicaklik.wmp_nuklidleri(kutuphane)
    if wmp is None or wmp:
        return []
    return [Bulgu("uyari", _YER,
                  _("windowed multipole açık ama kütüphanede wmp verisi yok"),
                  _("OpenMC yalnız uyarır ve noktasal veriye döner; sıcaklık yöntemi ve "
                    "toleransı yine geçerlidir."))]


def _sicaklik_bulgulari(satirlar: List["sicaklik.MalzemeSicakligi"],
                        a: "sicaklik.SicaklikAyari") -> List[Bulgu]:
    """hata/uyari malzeme basina; ara sicakliklar TEK bilgi bulgusunda."""
    gruplar: Dict[Tuple[str, str], List["sicaklik.MalzemeSicakligi"]] = {}
    for s in satirlar:
        gruplar.setdefault((s.malzeme, s.karar.durum), []).append(s)
    bulgular, aralar = [], []
    for (malzeme, durum), liste in sorted(gruplar.items()):
        if durum == "ara":
            aralar.append(liste[0])
            continue
        b = _sicaklik_bulgusu(malzeme, durum, liste, a)
        if b is not None:
            bulgular.append(b)
    if aralar:
        bulgular.append(_ara_bulgusu(aralar))
    return bulgular


def _ara_bulgusu(aralar: List["sicaklik.MalzemeSicakligi"]) -> Bulgu:
    parcalar = ["%s %g K (%s K)" % (s.malzeme, s.sicaklik,
                                    "–".join("%d" % t for t in s.karar.kullanilan))
                for s in aralar]
    ek = ", …" if len(parcalar) > _EN_COK_AD else ""
    return Bulgu("bilgi", _YER,
                 _("ara sıcaklık, komşu kütüphane sıcaklıkları arasında stokastik "
                   "interpolasyon: %s") % (", ".join(parcalar[:_EN_COK_AD]) + ek),
                 _("Her çarpışmada iki komşu sıcaklıktan biri kT'ye göre doğrusal olasılıkla "
                   "seçilir (OpenMC 0.16). Sonuç, iki sıcaklıktaki koşuların arasında kalır."))


def _sicaklik_bulgusu(malzeme: str, durum: str, liste: list,
                      a: "sicaklik.SicaklikAyari") -> Optional[Bulgu]:
    ilk = liste[0]
    yer = "malzeme:%s" % malzeme
    adlar = _adlar([s.ad for s in liste])
    kullanilan = " / ".join("%d K" % t for t in ilk.karar.kullanilan)
    mevcut = ", ".join("%d" % round(t) for t in ilk.mevcut)
    if durum == "yok":
        return Bulgu("hata", yer,
                     _("%g K için kütüphanede veri yok (%s; yöntem %s, tolerans %g K)")
                     % (ilk.sicaklik, adlar, a.yontem, a.tolerans),
                     _("Mevcut sıcaklıklar: %s K. Sıcaklığı değiştirin, toleransı artırın ya da "
                       "ara değer (interpolation) yöntemini seçin.") % mevcut)
    if durum == "yakin":
        return Bulgu("uyari", yer,
                     _("%g K istendi, yalnız kütüphane sıcaklığı kullanılır: %s (%s)")
                     % (ilk.sicaklik, kullanilan, adlar),
                     _("En yakın sıcaklık yöntemi ara sıcaklık üretmez. Mevcut: %s K.") % mevcut)
    if durum == "kenar":
        return Bulgu("uyari", yer,
                     _("%g K kütüphane aralığı dışında, uç sıcaklık kullanılır: %s (%s)")
                     % (ilk.sicaklik, kullanilan, adlar),
                     _("Tolerans (%g K) içinde uca yapışır; fizik o sıcaklığınkidir.") % a.tolerans)
    return None


def _sicaklik_kontrol(spec: dict, veri_kontrolu: bool, kutuphane: Optional[str],
                      sicaklik_denetimi: bool) -> List[Bulgu]:
    try:
        a = sicaklik.ayar(spec)
    except ValueError as e:
        return [Bulgu("hata", _YER, str(e))]
    bulgular = _multipole_kontrol(a, veri_kontrolu, kutuphane)
    if not (veri_kontrolu and sicaklik_denetimi):
        return bulgular
    try:
        satirlar = sicaklik.model_degerlendirmesi(spec, kutuphane)
    except (ValueError, KeyError, TypeError):
        # bozuk malzeme tanimi: dogrula/malzeme.py ayrica raporlar
        _log.info("Y7 sıcaklık denetimi atlandı (malzemeler kurulamadı)", exc_info=True)
        return bulgular
    return bulgular + _sicaklik_bulgulari(satirlar, a)


def y7_kontrol(spec: dict, veri_kontrolu: bool = True, kutuphane: Optional[str] = None,
               sicaklik_denetimi: bool = True) -> List[Bulgu]:
    """Y7 kurallari (modul belgesi). kutuphane: cross_sections.xml yolu
    (None: OPENMC_CROSS_SECTIONS)."""
    return (_foton_kontrol(spec, veri_kontrolu, kutuphane) + _isinma_kontrol(spec)
            + _sicaklik_kontrol(spec, veri_kontrolu, kutuphane, sicaklik_denetimi))
