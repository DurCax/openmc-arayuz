# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/_ortak.py  --  Bulgu, seviye yardimcilari, yer etiketi

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek import uygunluk
from cekirdek.ceviri import _, N_


def _kor_turu_adi(tur):
    """Kor turunun sade adi (uygunluk.KOR_TURU_ADLARI), etkin dilde;
    bilinmiyorsa kendisi."""
    ad = uygunluk.KOR_TURU_ADLARI.get(tur)
    return _(ad) if ad else str(tur)


# Bulgu "yer" kodunun kullaniciya gorunen adi. Kod degismez (sekme eslemesi
# ona bakar); yalnizca listede okunur bir ad gosterilir. Ad etkin dilde
# verilir (N_ ile isaretli); onekin ardindaki ayrinti (malzeme adi, katman
# numarasi) ayiricidan sonra eklenir: "/" ile biten onek ", ", digerleri " ".
_YER_ETIKETI = [
    ("malzemeler", N_("Malzemeler")), ("malzeme:", N_("Malzeme")), ("cubuk:", N_("Çubuk")),
    ("plaka:", N_("Plaka elemanı")), ("demet:", N_("Demet")),
    ("kor/katman ", N_("Kor, katman")),
    ("kor", N_("Kor")), ("ayarlar", N_("Hesap ayarları")),
    ("veri kutuphanesi", N_("Veri kütüphanesi")),
    ("kaynak", N_("Kaynak")), ("tally:", N_("Tally")), ("guc dagilimi", N_("Güç dağılımı")),
    ("guc_dagilimi", N_("Güç dağılımı")), ("tukenme/", N_("Tükenme")),
    ("tukenme", N_("Tükenme")), ("dogrulama", N_("Doğrulama")),
]


def yer_etiketi(yer):
    """Bulgu yerinin okunur adi: "malzeme:uo2" -> "Malzeme uo2". Kod degismez."""
    yer = yer or ""
    if yer.startswith("geometri:"):
        from cekirdek.geometri.yol_metni import okunur
        return _("Geometri") + ": " + okunur(yer[len("geometri:"):])
    for onek, ad in _YER_ETIKETI:
        if yer == onek:
            return _(ad)
        if onek.endswith((":", "/", " ")) and yer.startswith(onek):
            ayirici = ", " if onek.endswith("/") else " "
            return _(ad) + ayirici + yer[len(onek):]
    return yer


# Seviye etiketleri (terminal ciktisi, Bulgu.__str__)
_SEVIYE_IMI = {"hata": N_("HATA"), "uyari": N_("UYARI"), "bilgi": N_("BİLGİ")}


# Bilinen BOSLUK bulgularinin sabit kodu (v3 K1): henuz atilmamis bir model
# kurma asamasinin dogal sonucu (or. bos modelde "cubuk secilmemis"). Arayuz
# bunlari metne ya da yere gore degil YALNIZ bu koda gore "eksik asama"
# olarak sunar; gercek hatalar kodsuzdur.
BOS_ADIM_ONEKI = "bos_adim:"
BOS_ADIM_GEOMETRI = BOS_ADIM_ONEKI + "geometri"


class Bulgu(object):
    """Tek bir dogrulama bulgusu. kod: istege bagli sabit kimlik (bkz.
    BOS_ADIM_ONEKI); eski cagrilar kodsuz kalir (None)."""

    def __init__(self, seviye, yer, mesaj, oneri=None, kod=None):
        self.seviye = seviye        # "hata" | "uyari" | "bilgi"
        self.yer = yer              # "malzeme:uo2", "kor", "ayarlar" ...
        self.mesaj = mesaj
        self.oneri = oneri
        self.kod = kod

    def __str__(self):
        im = _(_SEVIYE_IMI[self.seviye])
        s = "[%-5s] %-22s %s" % (im, yer_etiketi(self.yer), self.mesaj)
        if self.oneri:
            s += "\n                             -> %s" % self.oneri
        return s

    def __repr__(self):
        return "Bulgu(%s, %s)" % (self.seviye, self.mesaj)


def hata_var(bulgular):
    """Listede en az bir 'hata' seviyesinde bulgu varsa True."""
    return any(b.seviye == "hata" for b in bulgular)
