# -*- coding: utf-8 -*-
"""
kayit.py -- Veri sayfasinin ana pencereye baglanmasi (v3 K2).

  kur(pencere)        AnaPencere.__init__ sonunda: sayfayi kenar cubuguna
                      ("Kurulum" grubu, anahtar "veri") ve sayfa yiginina ekler,
                      surec ortamini cozulen veriyle gunceller
                      (veri_yolu.surece_uygula) ve secim degisince dogrulamayi
                      / Calistir kapisini yeniler.
  ilk_acilis(pencere) uygulama acilisinda (arayuz/ana_pencere.main): veri
                      yoksa editoru Veri sayfasinda acar ve ustte "Başlamadan
                      önce" bandini gosterir. Doner: acildi mi.

Model sayfalarinin sozlesmesi (uygunluk.SEKMELER, sekme_anahtarlari) DEGISMEZ:
Veri sayfasi `_ek_sayfalar`da durur, `_sayfalar`da degil (model turune gore
gizlenmez, isaretlenmez). Gezinme: arayuz/pencere/gezinme.py.
"""

from PySide6 import QtCore

from cekirdek import veri_bilgi, veri_yolu
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ANAHTAR = "veri"
BASLIK = N_("Veri")
GRUP = N_("Kurulum")
IKON = "atom"


def kur(pencere, sayfa=None):
    """Sayfayi pencereye kaydeder (modul belgesi). Doner: VeriSayfasi."""
    from arayuz.veri.sayfa import VeriSayfasi
    yazilan = veri_yolu.surece_uygula()
    if yazilan:
        _log.info("nukleer veri surec ortamina yazildi: %s", sorted(yazilan))
    sayfa = sayfa or VeriSayfasi()
    pencere.kenar.grup_ekle(_(GRUP))
    pencere.kenar.ekle(ANAHTAR, _(BASLIK), IKON)
    alan = pencere._kaydirma(sayfa)
    pencere.yigin_sekme.addWidget(alan)
    pencere._ek_sayfalar = dict(getattr(pencere, "_ek_sayfalar", {}), **{ANAHTAR: alan})
    pencere._sayfa_editor[alan] = sayfa
    pencere.veri_sayfasi = sayfa
    pencere.kenar.secildi.connect(lambda anahtar: _kenardan(pencere, anahtar))
    sayfa.veri_degisti.connect(lambda: veri_degisti(pencere))
    sayfa.baslangica_don.connect(pencere.baslangici_goster)
    sayfa.durum.connect(lambda metin, iyi: pencere.bildir_mesaj(
        metin, "basari" if iyi else "uyari", 8000))
    pencere._veri_kapanis_suzgeci = _KapanisSuzgeci(sayfa, pencere)
    pencere.installEventFilter(pencere._veri_kapanis_suzgeci)
    return sayfa


class _KapanisSuzgeci(QtCore.QObject):
    """Pencere kapanirken suren indirmeyi iptal edip isciyi bekler: canli bir
    QThread'in yok edilmesi sureci cokertirdi. Yarim indirme .part olarak kalir
    ve sonra surdurulur, yani iptal ucuzdur."""

    def __init__(self, sayfa, parent):
        super().__init__(parent)
        self._sayfa = sayfa

    def eventFilter(self, nesne, olay):                  # noqa: N802 (Qt adi)
        if olay.type() == QtCore.QEvent.Close and self._sayfa.indirme.indiriyor_mu():
            _log.info("pencere kapaniyor: suren veri indirmesi iptal edildi")
            self._sayfa.indirme.iptal()
            self._sayfa.bekle()
        return False


def _kenardan(pencere, anahtar):
    """Kenar cubugunda Veri secildi: ana pencerenin _sekme_degisti'si bu
    anahtari tanimaz (model sayfasi degil); yigini burada cevir."""
    if anahtar != ANAHTAR:
        return
    pencere.yigin_sekme.setCurrentWidget(pencere._ek_sayfalar[ANAHTAR])
    pencere.veri_sayfasi.yenile()


def veri_degisti(pencere):
    """Secim degisti: surec ortami, onbellekler, dogrulama, Calistir kapisi."""
    veri_yolu.surece_uygula()
    veri_bilgi.onbellek_temizle()
    pencere._dogrula(veri=False)
    pencere._kosu_dugmesi_guncelle()


def ilk_acilis(pencere):
    """Veri yoksa editoru Veri sayfasinda acar (bant gorunur). Doner: acildi mi."""
    if veri_yolu.veri_hazir_mi():
        return False
    pencere._editoru_goster()
    pencere.sekmeye_git(ANAHTAR, sessiz=True)
    pencere.veri_sayfasi.ilk_acilis_goster(True)
    _log.info("nukleer veri bulunamadi: Veri sayfasi acildi")
    return True
