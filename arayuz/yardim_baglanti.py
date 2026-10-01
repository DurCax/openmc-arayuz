# -*- coding: utf-8 -*-
"""
yardim_baglanti.py -- arayuzden kullanim kilavuzuna baglantilar (Dalga 3 / Ajan 12).

Sozlesme (arayuz/yardim, Ajan 13b): `yardim.ac(bolum_kimligi, pencere)`.
Bu modul YALNIZ eslemeyi ve dugmeyi tutar; kilavuzun icerigi ve gosterimi
arayuz/yardim'dadir.

  sayfa_bolumu("kor")                -> "geometri"
  sayfa_bolumu("kor", gelismis=True) -> "geometri-gelismis"
  bulgu_bolumu("malzeme:uo2")        -> "malzemeler"
  ac("vv", pencere)                  -> kilavuzu o bolumde acar
  yardim_dugmesi("demet")            -> sayfa basligi icin "?" dugmesi

Bolum kimlikleri 13b ile ortaktir (BOLUM_KIMLIKLERI); burada olmayan bir
kimlik kullanilmaz (testler/test_dil.py denetler).
"""

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

BOLUM_KIMLIKLERI = (
    "baslangic", "ilk-hesap", "kavramlar", "malzemeler", "parcalar", "demet",
    "geometri", "geometri-gelismis", "hesap-ayarlari", "calistir", "sonuclar",
    "analiz", "tukenme", "uygunluk-denetimi", "vv", "terminal", "sorun-giderme",
    "sozluk",
)

# Sayfa anahtari (uygunluk.SEKMELER + "baslangic") -> bolum kimligi.
SAYFA_BOLUMU = {
    "baslangic": "baslangic",
    "malzemeler": "malzemeler",
    "parcalar": "parcalar",
    "demet": "demet",
    "kor": "geometri",
    "ayarlar": "hesap-ayarlari",
    "calistir": "calistir",
    "analiz": "analiz",
    "tukenme": "tukenme",
}
GELISMIS_GEOMETRI_BOLUMU = "geometri-gelismis"
VARSAYILAN_BOLUM = "baslangic"

# Dogrulama bulgusunun "yer" oneki -> bolum kimligi (ilk eslesen; uzun onek once).
BULGU_BOLUMU = (
    ("geometri:", "geometri-gelismis"),
    ("kor/katman", "geometri"),
    ("kor", "geometri"),
    ("malzemeler", "malzemeler"),
    ("malzeme", "malzemeler"),
    ("cubuk", "parcalar"),
    ("plaka", "parcalar"),
    ("demet", "demet"),
    ("ayarlar", "hesap-ayarlari"),
    ("kaynak", "hesap-ayarlari"),
    ("tally", "hesap-ayarlari"),
    ("guc dagilimi", "hesap-ayarlari"),
    ("guc_dagilimi", "hesap-ayarlari"),
    ("tukenme", "tukenme"),
    ("veri kutuphanesi", "sorun-giderme"),
    ("dogrulama", "sorun-giderme"),
)
# Yeri taninmayan bulgu: sorun giderme bolumu (hata metni -> neden -> cozum).
BULGU_VARSAYILAN = "sorun-giderme"


def sayfa_bolumu(anahtar, gelismis=False):
    """Sayfa anahtarinin kilavuz bolumu; Geometri gelismis kipte ayri bolum."""
    if anahtar == "kor" and gelismis:
        return GELISMIS_GEOMETRI_BOLUMU
    return SAYFA_BOLUMU.get(anahtar, VARSAYILAN_BOLUM)


def bulgu_bolumu(yer):
    """Bulgu yerinden ("malzeme:uo2", "kor/katman 2 (su)") kilavuz bolumu."""
    yer = (yer or "").strip().lower()
    for onek, bolum in BULGU_BOLUMU:
        if yer.startswith(onek):
            return bolum
    return BULGU_VARSAYILAN


def ac(bolum_kimligi, pencere=None):
    """Kilavuzu bolumde acar (arayuz.yardim sozlesmesi); sonucu doner."""
    from arayuz import yardim
    if bolum_kimligi not in BOLUM_KIMLIKLERI:
        _log.warning("bilinmeyen kilavuz bolumu: %r; baslangic aciliyor", bolum_kimligi)
        bolum_kimligi = VARSAYILAN_BOLUM
    return yardim.ac(bolum_kimligi, pencere)


def yardim_dugmesi(bolum_kimligi, parent=None):
    """Sayfa basligi icin "?" dugmesi: tiklayinca kilavuzu o bolumde acar.
    bolum_kimligi bir metin ya da tiklama aninda kimligi veren bir islevdir
    (Geometri sayfasi: sablon / gelismis kip)."""
    from PySide6 import QtCore, QtWidgets
    d = QtWidgets.QToolButton(parent)
    d.setText("?")
    d.setObjectName("yardimDugmesi")
    d.setAutoRaise(True)
    d.setCursor(QtCore.Qt.PointingHandCursor)
    d.setFocusPolicy(QtCore.Qt.StrongFocus)
    d.setToolTip(_("Kullanım kılavuzunda bu sayfanın bölümünü açar (F1)"))
    d.setAccessibleName(_("Kullanım kılavuzu"))

    def bolum():
        return bolum_kimligi() if callable(bolum_kimligi) else bolum_kimligi

    d.kilavuz_bolumu = bolum
    d.clicked.connect(lambda _c=False: ac(bolum(), d.window()))
    return d
