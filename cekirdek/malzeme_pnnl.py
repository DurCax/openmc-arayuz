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
   "N.  ","Ad"                              -> numara + ad (ARDINDAN "Formula =")
   "Formula =","U3O8",...                   -> formul ("-" = yok)
   "Density (g/cm3) =",,8.300000,...        -> yogunluk
   "Element","Neutron ZA",...               -> bilesim tablosu basligi
   "O",8016,8000,<agirlik kesri>,...        -> satirlar ("U-235" = nuklid)
   "Total",...                              -> tablo sonu
   "Comments & references:"                 -> ilk "0" satirina kadar kaynak
 Bir numara satiri YALNIZCA hemen ardindan "Formula =" geliyorsa yeni kayit
 baslatir (yorum metnindeki "12." gibi satirlar sahte kayit acmaz).

 GUVENLIK/DOGRULUK: dosya boyutu, kayit, bilesen ve kaynak satiri sayilari
 sinirlidir (PnnlHatasi). NaN/sonsuz/negatif agirlik ya da yogunluk, agirlik
 toplami 1'den sapan ya da yinelenen numarali kayit atlanir ve sorun
 listesine yazilir (sessiz degil).
================================================================================
"""

import csv
import io
import math
import os
import re
from typing import Iterable, Optional, Sequence, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_NO_KALIBI = re.compile(r"^\s*(\d+)\.\s*$")
_IZOTOP_KALIBI = re.compile(r"^([A-Za-z]{1,2})-(\d{1,3})$")
_ELEMENT_KALIBI = re.compile(r"^[A-Za-z]{1,2}$")
# Once UTF-8 (BOM'lu ya da degil) denenir; Excel/PyNE cikisi latin-1'dir.
_KODLAMALAR = ("utf-8-sig", "latin-1")
_AGIRLIK_SUTUNU = 3
_YUZDE = 100.0
_KAYNAK_AYIRICI = " "

# Sinirlar: PyNE dosyasi ~1 MB / 372 kayit / en cok 17 bilesen / en uzun kaynak
# 1443 karakter (olculdu, 02.10.2026). Rev.2 411 kayit. Sinirlar bunun
# katlaridir; asilirsa dosya PNNL derlemesi sayilmaz.
AZAMI_BOYUT = 20 * 1024 * 1024
AZAMI_KAYIT = 5000
AZAMI_BILESEN = 200
AZAMI_KAYNAK_SATIRI = 100
AZAMI_HUCRE = 4000
# Yogunluk ust siniri [g/cm3]: en yogun element osmiyum 22.59 g/cm3 (CRC
# Handbook); 30 bunun ustunde pay birakir.
AZAMI_YOGUNLUK = 30.0
# Agirlik kesirleri toplami toleransi: tabloda 6 ondalikli kesirler; 40 satirda
# yuvarlama <= 2e-5. 1e-3'ten buyuk sapma veri hatasidir (or. Rev.1'de SS-440
# toplami 0.99014) -- normalize etmek bilesimi sessizce degistirirdi.
TOPLAM_TOLERANSI = 1.0e-3


class PnnlHatasi(ValueError):
    """Dosya okunamadi ya da PNNL derleme bicimi degil."""


def _hucre(satir, i):
    return satir[i].strip() if i < len(satir) else ""


def _sonlu(metin, etiket):
    x = float(metin)                              # sayi degilse ValueError
    if not math.isfinite(x):
        raise ValueError(_("%s sonlu bir sayı değil: %r") % (etiket, metin))
    return x


def _ilk_sayi(satir, bas=1):
    for h in satir[bas:]:
        h = h.strip()
        if h:
            return _sonlu(h, _("yoğunluk"))
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


def _kayit_sorunu(k):
    """Tamamlanmis kaydin sorunu (metin) ya da None."""
    if k.get("hata"):
        return k["hata"]
    if k.get("yogunluk") is None or not k["bilesim"]:
        return _("yoğunluk ya da bileşim eksik")
    if not 0.0 < k["yogunluk"] <= AZAMI_YOGUNLUK:
        return _("yoğunluk 0–%g g/cm³ aralığında değil: %g") % (AZAMI_YOGUNLUK, k["yogunluk"])
    toplam = sum(w for _i, _t, w in k["bilesim"])
    if abs(toplam - 1.0) > TOPLAM_TOLERANSI:
        return _("ağırlık kesirlerinin toplamı %.6f (1'den sapma > %g)") % (toplam, TOPLAM_TOLERANSI)
    return None


class _Okuyucu:
    """Satir satir durum makinesi; tamamlanan kayitlari ve sorunlari toplar."""

    def __init__(self):
        self.malzemeler, self.sorunlar = [], []
        self._k = None
        self._numaralar = set()
        self._tablo = self._yorum = False

    def _bitir(self):
        k, self._k = self._k, None
        if k is None:
            return
        sorun = _kayit_sorunu(k)
        if sorun is None and k["no"] in self._numaralar:
            sorun = _("numara %d daha önce kullanıldı") % k["no"]
        if sorun:
            self.sorunlar.append(_("PNNL kaydı %d (%s) atlandı: %s") % (k["no"], k["ad"], sorun))
            _log.warning("PNNL kaydi %d atlandi: %s", k["no"], sorun)
            return
        self._numaralar.add(k["no"])
        k.pop("hata", None)
        k["bilesim"] = tuple(k["bilesim"])
        k["kaynak"] = _KAYNAK_AYIRICI.join(k["kaynak"])
        self.malzemeler.append(k)
        if len(self.malzemeler) > AZAMI_KAYIT:
            raise PnnlHatasi(_("PNNL dosyasında %d kayıttan fazlası var") % AZAMI_KAYIT)

    def _hata(self, metin):
        if self._k is not None and not self._k.get("hata"):
            self._k["hata"] = metin

    def satir(self, s, sonraki):
        if any(len(h) > AZAMI_HUCRE for h in s):
            raise PnnlHatasi(_("PNNL dosyasında %d karakterden uzun hücre var") % AZAMI_HUCRE)
        bas = _hucre(s, 0)
        e = _NO_KALIBI.match(bas)
        if e and _hucre(sonraki, 0) == "Formula =":
            self._bitir()
            self._k = {"no": int(e.group(1)), "ad": _hucre(s, 1), "formul": None,
                       "yogunluk": None, "bilesim": [], "kaynak": []}
            self._tablo = self._yorum = False
            return
        if self._k is not None:
            self._alan(bas, s)

    def _kaynak_satiri(self, bas):
        if bas == "0":
            self._yorum = False
        elif bas:
            if len(self._k["kaynak"]) >= AZAMI_KAYNAK_SATIRI:
                raise PnnlHatasi(_("PNNL kaydı %d: %d kaynak satırından fazlası var")
                                 % (self._k["no"], AZAMI_KAYNAK_SATIRI))
            self._k["kaynak"].append(bas)

    def _alan(self, bas, s):
        if self._yorum:
            self._kaynak_satiri(bas)
        elif bas == "Formula =":
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
        if len(self._k["bilesim"]) >= AZAMI_BILESEN:
            raise PnnlHatasi(_("PNNL kaydı %d: %d bileşenden fazlası var")
                             % (self._k["no"], AZAMI_BILESEN))
        try:
            agirlik = _sonlu(_hucre(s, _AGIRLIK_SUTUNU), _("ağırlık kesri"))
            if agirlik < 0.0:
                raise ValueError(_("negatif ağırlık kesri: %s = %g") % (bas, agirlik))
            if agirlik > 0.0:                      # sifir satir: bilesene katkisi yok
                self._k["bilesim"].append(_bilesen(bas, agirlik))
        except ValueError as e:
            self._hata(str(e))

    def son(self):
        self._bitir()
        return tuple(self.malzemeler), tuple(self.sorunlar)


def _metin_oku(yol):
    boyut = os.stat(yol).st_size
    if boyut > AZAMI_BOYUT:
        raise PnnlHatasi(_("PNNL dosyası çok büyük (%d bayt; sınır %d)") % (boyut, AZAMI_BOYUT))
    with open(yol, "rb") as f:
        ham = f.read()
    for kodlama in _KODLAMALAR:
        try:
            return ham.decode(kodlama)
        except UnicodeDecodeError:
            continue
    raise PnnlHatasi(_("PNNL dosyasının kodlaması okunamadı: %s") % yol)  # latin-1 her baytı okur


def oku(yol: str) -> Tuple[Tuple[dict, ...], Tuple[str, ...]]:
    """DONER (malzemeler, sorunlar). Malzeme: {no, ad, formul, yogunluk,
    bilesim: ((isim, tur, agirlik_kesri), ...), kaynak}."""
    okuyucu = _Okuyucu()
    try:
        satirlar = list(csv.reader(io.StringIO(_metin_oku(yol), newline="")))
    except OSError as e:
        raise PnnlHatasi(_("PNNL dosyası açılamadı: %s (%s)") % (yol, e)) from e
    except csv.Error as e:
        raise PnnlHatasi(_("PNNL dosyası CSV olarak okunamadı: %s (%s)") % (yol, e)) from e
    for i, s in enumerate(satirlar):
        okuyucu.satir(s, satirlar[i + 1] if i + 1 < len(satirlar) else [])
    malzemeler, sorunlar = okuyucu.son()
    if not malzemeler:
        raise PnnlHatasi(_("Dosyada PNNL-15870 biçiminde malzeme bulunamadı: %s") % yol)
    return malzemeler, sorunlar


def ara(malzemeler: Iterable[dict], sorgu: Optional[str]) -> Tuple[dict, ...]:
    """Ad ya da formulde (buyuk/kucuk harf duyarsiz) sorgu gecenler."""
    q = (sorgu or "").strip().casefold()
    if not q:
        return tuple(malzemeler)
    return tuple(m for m in malzemeler
                 if q in m["ad"].casefold() or q in (m["formul"] or "").casefold())


def malzemeye_cevir(kayit: dict, ad: Optional[str] = None, sicaklik: float = 293.6) -> dict:
    """PNNL kaydini sema malzemesine cevirir (agirlikca yuzde, g/cm3).
    Toplam tolerans icinde 1'dir; kalan yuvarlama farki normalize edilir."""
    from cekirdek.sema import malzeme, bilesen
    bil = [bilesen(isim, _YUZDE * w, tur=tur, birim="wo") for isim, tur, w in kayit["bilesim"]]
    toplam = sum(b["miktar"] for b in bil)
    bil = [dict(b, miktar=b["miktar"] * _YUZDE / toplam) for b in bil]
    return malzeme(ad or "pnnl_%d" % kayit["no"], bil, kayit["yogunluk"], sicaklik=sicaklik,
                   gorunen_ad=kayit["ad"][:200])


__all__: Sequence[str] = ("PnnlHatasi", "oku", "ara", "malzemeye_cevir")
