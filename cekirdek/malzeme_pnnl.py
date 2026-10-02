# -*- coding: utf-8 -*-
"""
================================================================================
 malzeme_pnnl.py  --  PNNL-15870 malzeme derlemesinden ICE AKTARMA
================================================================================

 KAYNAK: McConn, Gesh, Pagh, Rucker, Williams, "Compendium of Material
 Composition Data for Radiation Transport Modeling", PNNL-15870 Rev.1 (2011),
 372 malzeme; Rev.2 (Detwiler vd., 2021, 411 malzeme) ayni bilesim alanlarini
 web veritabaninda sunar.

 LISANS DURUMU (02.10.2026'da denetlendi): rapor yalnizca DOE/Battelle
 sorumluluk reddi tasir; acik bir lisans ya da kamu mali beyani YOKTUR
 (Battelle yuklenici eseri; ABD hukumeti eseri sayilmaz). Bu yuzden veri
 programla DAGITILMAZ: kullanici kendi edindigi dosyayi secer, program onu
 yalnizca OKUR (diske kopyalamaz).

 BICIM: Rev.1 Excel calisma kitabinin CSV cikisi (PyNE'nin
 pyne/dbgen/materials_compendium.csv dosyasi bu bicimdedir). Her malzeme:
   "N.  ","Ad"                              -> numara + ad
   "Formula =","U3O8",...                   -> formul ("-" = yok)
   "Density (g/cm3) =",,8.300000,...        -> yogunluk
   "Element","Neutron ZA",...               -> bilesim tablosu basligi
   "O",8016,8000,<agirlik kesri>,...        -> satirlar ("U-235" = nuklid)
   "Total",...                              -> tablo sonu
   "Comments & references:"                 -> ilk "0" satirina kadar kaynak
 Bozuk kayit atlanir ve sorun listesine yazilir (sessiz degil).
================================================================================
"""

import csv
import re

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_NO_KALIBI = re.compile(r"^\s*(\d+)\.\s*$")
_IZOTOP_KALIBI = re.compile(r"^([A-Za-z]{1,2})-(\d{1,3})$")
_ELEMENT_KALIBI = re.compile(r"^[A-Za-z]{1,2}$")
_KODLAMA = "latin-1"         # Excel CSV cikisi (PyNE dosyasi) latin-1'dir
_AGIRLIK_SUTUNU = 3
_YUZDE = 100.0
_KAYNAK_AYIRICI = " "


class PnnlHatasi(ValueError):
    """Dosya okunamadi ya da PNNL derleme bicimi degil."""


def _hucre(satir, i):
    return satir[i].strip() if i < len(satir) else ""


def _ilk_sayi(satir, bas=1):
    for h in satir[bas:]:
        h = h.strip()
        if h:
            return float(h)          # sayi degilse ValueError -> kayit sorunu
    raise ValueError(_("yoğunluk değeri yok"))


def _bilesen(ad, agirlik):
    """('U-235', 0.02) -> ('U235', 'nuklid', 0.02); ('AL', 0.3) -> ('Al', 'element', 0.3)."""
    from cekirdek import malzeme_hesap as mh
    e = _IZOTOP_KALIBI.match(ad)
    if e:
        sembol = e.group(1).capitalize()
        mh.atom_numarasi(sembol)                  # bilinmeyen element: ValueError
        return sembol + str(int(e.group(2))), "nuklid", agirlik
    if not _ELEMENT_KALIBI.match(ad):
        raise ValueError(_("tanınmayan bileşen: %r") % ad)
    sembol = ad.capitalize()
    mh.atom_numarasi(sembol)
    return sembol, "element", agirlik


class _Okuyucu:
    """Satir satir durum makinesi; tamamlanan kayitlari ve sorunlari toplar."""

    def __init__(self):
        self.malzemeler, self.sorunlar = [], []
        self._k = None
        self._tablo = self._yorum = False

    def _bitir(self):
        k, self._k = self._k, None
        if k is None:
            return
        try:
            if k.get("hata"):
                raise ValueError(k["hata"])
            if k.get("yogunluk") is None or not k["bilesim"]:
                raise ValueError(_("yoğunluk ya da bileşim eksik"))
            if not k["yogunluk"] > 0.0:
                raise ValueError(_("yoğunluk pozitif değil"))
        except ValueError as e:
            self.sorunlar.append(_("PNNL kaydı %d (%s) atlandı: %s") % (k["no"], k["ad"], e))
            _log.warning("PNNL kaydi %d atlandi: %s", k["no"], e)
            return
        k.pop("hata", None)
        k["bilesim"] = tuple(k["bilesim"])
        k["kaynak"] = _KAYNAK_AYIRICI.join(k["kaynak"])
        self.malzemeler.append(k)

    def _hata(self, metin):
        if self._k is not None and not self._k.get("hata"):
            self._k["hata"] = metin

    def satir(self, s):
        bas = _hucre(s, 0)
        e = _NO_KALIBI.match(bas)
        if e:
            self._bitir()
            self._k = {"no": int(e.group(1)), "ad": _hucre(s, 1), "formul": None,
                       "yogunluk": None, "bilesim": [], "kaynak": []}
            self._tablo = self._yorum = False
            return
        if self._k is None:
            return
        self._alan(bas, s)

    def _alan(self, bas, s):
        if self._yorum:
            if bas == "0":
                self._yorum = False
            elif bas:
                self._k["kaynak"].append(bas)
            return
        if bas == "Formula =":
            f = _hucre(s, 1)
            self._k["formul"] = None if f in ("", "-") else f
        elif bas.startswith("Density (g/cm3)"):
            try:
                self._k["yogunluk"] = _ilk_sayi(s)
            except ValueError as e:
                self._hata(str(e))
        elif bas == "Element":
            self._tablo = True
        elif bas == "Total":
            self._tablo = False
        elif bas.startswith("Comments & references"):
            self._yorum = True
        elif self._tablo and bas:
            self._tablo_satiri(bas, s)

    def _tablo_satiri(self, bas, s):
        try:
            agirlik = float(_hucre(s, _AGIRLIK_SUTUNU))
            if agirlik > 0.0:
                self._k["bilesim"].append(_bilesen(bas, agirlik))
        except ValueError as e:
            self._hata(str(e))

    def son(self):
        self._bitir()
        return tuple(self.malzemeler), tuple(self.sorunlar)


def oku(yol):
    """DONER (malzemeler, sorunlar). Malzeme: {no, ad, formul, yogunluk,
    bilesim: ((isim, tur, agirlik_kesri), ...), kaynak}."""
    okuyucu = _Okuyucu()
    try:
        with open(yol, encoding=_KODLAMA, newline="") as f:
            for s in csv.reader(f):
                okuyucu.satir(s)
    except OSError as e:
        raise PnnlHatasi(_("PNNL dosyası açılamadı: %s (%s)") % (yol, e)) from e
    except csv.Error as e:
        raise PnnlHatasi(_("PNNL dosyası CSV olarak okunamadı: %s (%s)") % (yol, e)) from e
    malzemeler, sorunlar = okuyucu.son()
    if not malzemeler:
        raise PnnlHatasi(_("Dosyada PNNL-15870 biçiminde malzeme bulunamadı: %s") % yol)
    return malzemeler, sorunlar


def ara(malzemeler, sorgu):
    """Ad ya da formulde (buyuk/kucuk harf duyarsiz) sorgu gecenler."""
    q = (sorgu or "").strip().casefold()
    if not q:
        return tuple(malzemeler)
    return tuple(m for m in malzemeler
                 if q in m["ad"].casefold() or q in (m["formul"] or "").casefold())


def malzemeye_cevir(kayit, ad=None, sicaklik=293.6):
    """PNNL kaydini sema malzemesine cevirir (agirlikca yuzde, g/cm3)."""
    from cekirdek.sema import malzeme, bilesen
    bil = [bilesen(isim, _YUZDE * w, tur=tur, birim="wo") for isim, tur, w in kayit["bilesim"]]
    toplam = sum(b["miktar"] for b in bil)
    bil = [dict(b, miktar=b["miktar"] * _YUZDE / toplam) for b in bil]   # Total ~1.000001
    return malzeme(ad or "pnnl_%d" % kayit["no"], bil, kayit["yogunluk"], sicaklik=sicaklik,
                   gorunen_ad=kayit["ad"])
