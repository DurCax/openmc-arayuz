# -*- coding: utf-8 -*-
"""
kayit.py -- Veri sayfasinin ana pencereye baglanmasi (v3 K2).

  kur(pencere)        AnaPencere.__init__ sonunda: sayfayi kenar cubuguna
                      ("Kurulum" grubu, anahtar "veri") ve sayfa yiginina ekler;
                      secim degisince surec ortamini, dogrulamayi ve Calistir
                      kapisini yeniler. aboutToQuit'te arka plan islerini durdurur.
  kapat(pencere)      closeEvent'te (kaydetme onayindan SONRA): indirme iptal,
                      isler sinirli sure beklenir.
  ilk_acilis(pencere) uygulama acilisinda (arayuz/ana_pencere.main): veri
                      yoksa editoru Veri sayfasinda acar ve ustte "Başlamadan
                      önce" bandini gosterir. Doner: acildi mi.

Model sayfalarinin sozlesmesi (uygunluk.SEKMELER, sekme_anahtarlari) DEGISMEZ:
Veri sayfasi `_ek_sayfalar`da durur, `_sayfalar`da degil (model turune gore
gizlenmez, isaretlenmez). Gezinme: arayuz/pencere/gezinme.py.
"""

from PySide6 import QtWidgets

from cekirdek import veri_bilgi, veri_yolu
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ANAHTAR = "veri"
BASLIK = N_("Veri")
GRUP = N_("Kurulum")
IKON = "atom"


def kur(pencere, sayfa=None):
    """Sayfayi pencereye kaydeder (modul belgesi). Doner: VeriSayfasi. Surec
    ortamina DOKUNMAZ (widget kurucusunda global yan etki yok): uygulama
    acilisinda arayuz/ana_pencere.main() veri_yolu.surece_uygula() cagirir."""
    from arayuz.veri.sayfa import VeriSayfasi
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
    uygulama = QtWidgets.QApplication.instance()
    if uygulama is not None:
        uygulama.aboutToQuit.connect(sayfa.kapat)
    return sayfa


def kapat(pencere) -> bool:
    """Pencere kapanisi onaylandiktan SONRA (closeEvent): indirme iptal, isler beklenir."""
    sayfa = getattr(pencere, "veri_sayfasi", None)
    return sayfa.kapat() if sayfa is not None else True


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


def ilk_acilis(pencere, proje_acik: bool = False) -> bool:
    """Veri yoksa editoru Veri sayfasinda acar (bant gorunur). Komut satirindan
    bir proje acildiysa (proje_acik) sayfaya GECILMEZ: yalniz "Veri sayfasi"
    eylemli bir bildirim gosterilir (model ekrani korunur). Doner: sayfa acildi mi."""
    if veri_yolu.veri_hazir_mi():
        return False
    pencere.veri_sayfasi.ilk_acilis_goster(True)
    if proje_acik:
        pencere.bildir_mesaj(_("Nükleer veri kütüphanesi bulunamadı; koşu için Veri "
                               "sayfasından seçin ya da indirin."), "uyari", 12000,
                             eylem_metni=_("Veri sayfası"),
                             eylem=lambda: pencere.sekmeye_git(ANAHTAR))
        _log.info("nukleer veri bulunamadi: proje acik, yalniz bildirim")
        return False
    pencere._editoru_goster()
    pencere.sekmeye_git(ANAHTAR, sessiz=True)
    _log.info("nukleer veri bulunamadi: Veri sayfasi acildi")
    return True
