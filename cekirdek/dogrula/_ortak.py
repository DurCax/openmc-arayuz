# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/_ortak.py  --  Bulgu, seviye yardimcilari, yer etiketi

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek import uygunluk


def _kor_turu_adi(tur):
    """Kor turunun sade adi (uygunluk.KOR_TURU_ADLARI); bilinmiyorsa kendisi."""
    return uygunluk.KOR_TURU_ADLARI.get(tur, str(tur))


# Bulgu "yer" kodunun kullaniciya gorunen adi. Kod degismez (sekme eslemesi
# ona bakar); yalnizca listede okunur bir ad gosterilir.
_YER_ETIKETI = [
    ("malzemeler", "Malzemeler"), ("malzeme:", "Malzeme "), ("cubuk:", "Çubuk "),
    ("plaka:", "Plaka elemanı "), ("demet:", "Demet "), ("kor/katman ", "Kor, katman "),
    ("kor", "Kor"), ("ayarlar", "Hesap ayarları"), ("veri kutuphanesi", "Veri kütüphanesi"),
    ("kaynak", "Kaynak"), ("tally:", "Tally "), ("guc dagilimi", "Güç dağılımı"),
    ("guc_dagilimi", "Güç dağılımı"), ("tukenme/", "Tükenme, "), ("tukenme", "Tükenme"),
    ("dogrulama", "Doğrulama"),
]


def yer_etiketi(yer):
    """Bulgu yerinin okunur adi: "malzeme:uo2" -> "Malzeme uo2". Kod degismez."""
    yer = yer or ""
    for onek, ad in _YER_ETIKETI:
        if yer == onek or (onek.endswith((":", "/", " ")) and yer.startswith(onek)):
            return ad + yer[len(onek):]
    return yer


class Bulgu(object):
    """Tek bir dogrulama bulgusu."""

    def __init__(self, seviye, yer, mesaj, oneri=None):
        self.seviye = seviye        # "hata" | "uyari" | "bilgi"
        self.yer = yer              # "malzeme:uo2", "kor", "ayarlar" ...
        self.mesaj = mesaj
        self.oneri = oneri

    def __str__(self):
        im = {"hata": "HATA ", "uyari": "UYARI", "bilgi": "BİLGİ"}[self.seviye]
        s = "[%s] %-22s %s" % (im, yer_etiketi(self.yer), self.mesaj)
        if self.oneri:
            s += "\n                             -> %s" % self.oneri
        return s

    def __repr__(self):
        return "Bulgu(%s, %s)" % (self.seviye, self.mesaj)


def hata_var(bulgular):
    """Listede en az bir 'hata' seviyesinde bulgu varsa True."""
    return any(b.seviye == "hata" for b in bulgular)
