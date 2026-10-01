# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_denetimi/kurallar.py  --  Kural, bulgu ve baglam turleri; kural kaydi
================================================================================

 Kural kimlikleri docs/STANDARTLAR.md §3 uygunluk matrisindekilerdir (K1-K16).
 Bir kural bir islevdir: islev(kural, baglam) -> [DenetimBulgusu]. Kural
 GECTIGINDE de bulgu uretir (durum "karsilandi", seviye "bilgi"); boylece
 rapor eki karsilanan / karsilanmayan / uygulanamayan listesini kurabilir.

 ETIKET (kaynagin turu -- STANDARTLAR.md §6 madde 16-17)
   iyi_uygulama     standart maddesi DEGIL (K1-K3); kaynak yayin/uygulama
   standart         acik bir standart/kilavuz maddesine dayanir
   proje_olcutu     projenin kendi ölçütü (ör. |e| > 2σ anlamlilik)
   kullanici_siniri esik kullanicidan/tesisten gelir (varsayilan YOK)

 Kural gövdeleri: kurallar_mc (A), kurallar_kritiklik (B), kurallar_kor (C),
 kurallar_rapor (D).
================================================================================
"""

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Optional

from cekirdek.ceviri import _, N_
from cekirdek.dogrula._ortak import Bulgu
from cekirdek.uygunluk_denetimi.profiller import atif_metni

# --- durumlar ---
KARSILANDI = "karsilandi"
KARSILANMADI = "karsilanmadi"
UYGULANAMADI = "uygulanamadi"
BILGI = "bilgi"
DURUMLAR = (KARSILANDI, KARSILANMADI, UYGULANAMADI, BILGI)

# --- etiketler ---
IYI_UYGULAMA = "iyi_uygulama"
STANDART = "standart"
PROJE_OLCUTU = "proje_olcutu"
KULLANICI_SINIRI = "kullanici_siniri"
_ETIKET_ADLARI = {
    IYI_UYGULAMA: N_("iyi uygulama (standart maddesi değil)"),
    STANDART: N_("standart / kılavuz"),
    PROJE_OLCUTU: N_("proje ölçütü (standarttan gelmez)"),
    KULLANICI_SINIRI: N_("kullanıcı / tesis sınırı"),
}


def etiket_metni(etiket):
    """Etiketin gorunen adi."""
    return _(_ETIKET_ADLARI.get(etiket, etiket))


class DenetimBulgusu(Bulgu):
    """
    Uygunluk denetimi bulgusu. Bulgu'nun (seviye, yer, mesaj, oneri) alanlarina
    ek olarak: kural (kimlik), profil, kaynak (atif metni), etiket, durum.
    yer = "uygunluk:<kural>"; dogrula.hata_var() ve Bulgu gosterimi aynen calisir.
    """

    def __init__(self, seviye, kural, mesaj, oneri=None, kaynak="",
                 etiket=IYI_UYGULAMA, durum=KARSILANMADI, profil=""):
        super().__init__(seviye, "uygunluk:" + kural, mesaj, oneri)
        self.kural = kural
        self.kaynak = kaynak
        self.etiket = etiket
        self.durum = durum
        self.profil = profil

    def sozluk(self):
        """JSON'a yazilabilir kopya (CLI / rapor eki)."""
        return {"seviye": self.seviye, "kural": self.kural, "profil": self.profil,
                "durum": self.durum, "mesaj": self.mesaj, "oneri": self.oneri,
                "kaynak": self.kaynak, "etiket": self.etiket}

    def __repr__(self):
        return "DenetimBulgusu(%s, %s, %s)" % (self.kural, self.seviye, self.durum)


@dataclass(frozen=True)
class Kural:
    """Tek bir denetim kurali (degismez). baslik N_() ile isaretlidir."""
    kimlik: str
    profil: str
    baslik: str
    kaynak: str
    etiket: str
    islev: Callable

    def bulgu(self, seviye, durum, mesaj, oneri=None, kaynak=None, kimlik=None):
        """Bu kuralin kaynak/etiketiyle doldurulmus bulgu. kimlik: alt kural
        (ör. "K2-parcacik"); kaynak: alt kuralin kendi atfi. Atif etkin
        dilde yazilir (profiller.atif_metni)."""
        return DenetimBulgusu(seviye, kimlik or self.kimlik, mesaj, oneri,
                              kaynak=atif_metni(kaynak or self.kaynak), etiket=self.etiket,
                              durum=durum, profil=self.profil)

    def gecti(self, mesaj, **kw):
        return self.bulgu("bilgi", KARSILANDI, mesaj, **kw)

    def uygulanamadi(self, mesaj, oneri=None, **kw):
        return self.bulgu("bilgi", UYGULANAMADI, mesaj, oneri, **kw)

    def not_(self, mesaj, oneri=None, **kw):
        return self.bulgu("bilgi", BILGI, mesaj, oneri, **kw)

    def ihlal(self, seviye, mesaj, oneri=None, **kw):
        return self.bulgu(seviye, KARSILANMADI, mesaj, oneri, **kw)


@dataclass(frozen=True)
class Baglam:
    """
    Bir kuralin gordugu her sey (degismez). denetle() kurar; kurallar okur.
      spec          proje sozlugu (None olabilir: yalniz kosu dizini)
      kosu          ayristir.KosuVerisi | None;  kosu_hatasi: okuma hatasi
      cikti         ayristir.CiktiOzeti | None
      esikler       etkin profilin {ad: Esik}
      vv            vv_arayuz.VVOzeti | None (S-3 uretir)
      kor           kor tasarim sonuclari sozlugu | None (bkz. kurallar_kor)
      rapor_metni   denetlenecek rapor metni (HTML ya da duz) | None
      uygulama      uygulamanin AOA parametreleri {ad: deger}
    """
    spec: Optional[Mapping] = None
    kosu_dizini: Optional[str] = None
    kosu: Any = None
    kosu_hatasi: Optional[str] = None
    cikti: Any = None
    esikler: Mapping = field(default_factory=dict)
    vv: Any = None
    kor: Optional[Mapping] = None
    rapor_metni: Optional[str] = None
    uygulama: Mapping = field(default_factory=dict)

    def esik(self, ad, varsayilan=None):
        """Esigin degeri (profilde yoksa varsayilan)."""
        e = self.esikler.get(ad)
        return varsayilan if e is None else e.deger

    def esik_kaynagi(self, ad):
        e = self.esikler.get(ad)
        return "" if e is None else e.kaynak

    def profil_ile(self, esikler):
        return replace(self, esikler=esikler)


def tum_kurallar():
    """Kayitli butun kurallar, profil sirasiyla (A, B, C, D)."""
    from cekirdek.uygunluk_denetimi import (kurallar_mc, kurallar_kritiklik,
                                            kurallar_kor, kurallar_rapor)
    return (kurallar_mc.KURALLAR + kurallar_kritiklik.KURALLAR
            + kurallar_kor.KURALLAR + kurallar_rapor.KURALLAR)


def kural_getir(kimlik):
    """Kimlige gore kural; yoksa KeyError."""
    for k in tum_kurallar():
        if k.kimlik == kimlik:
            return k
    raise KeyError(kimlik)
