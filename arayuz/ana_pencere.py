# -*- coding: utf-8 -*-
"""
================================================================================
 ana_pencere.py  --  Ana uygulama penceresi: giris noktasi + eski ice aktarma yolu
================================================================================
 Pencerenin kendisi arayuz/pencere/ paketindedir (bkz. arayuz/pencere/__init__.py
 ve ayrintili yerlesim notlari icin arayuz/pencere/ana_pencere.py).

 Bu dosya ince bir yonlendiricidir:
   python -m arayuz.ana_pencere [dosya.json]     (calistir.sh bunu kullanir)
   from arayuz import ana_pencere; ana_pencere.X  (testler ve sekme_kor.py)
 Eski modulun ad alanindaki her ad buradan yeniden dis verilir.
================================================================================
"""

# Eski modulun importlari: ad alani aynen korunur (ana_pencere.QtWidgets vb.).
import copy  # noqa: F401
import os  # noqa: F401
import sys

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: F401

from cekirdek import sema, dogrula, ice_aktar, kod_uret, onbellek, uygunluk  # noqa: F401
from arayuz.onizleme import OnizlemeWidget  # noqa: F401
from arayuz.sekme_analiz import AnalizSekmesi  # noqa: F401
from arayuz.sekme_tukenme import TukenmeSekmesi  # noqa: F401
from arayuz.sekme_ayar import AyarSekmesi  # noqa: F401
from arayuz.sekme_calistir import CalistirSekmesi  # noqa: F401
from arayuz.sekme_cubuk import CubukSekmesi  # noqa: F401
from arayuz.sekme_demet import DemetSekmesi  # noqa: F401
from arayuz.sekme_kor import KorSekmesi  # noqa: F401
from arayuz.sekme_malzeme import MalzemeSekmesi  # noqa: F401
from arayuz import baslangic, tema  # noqa: F401
from arayuz.ortak import (  # noqa: F401
    DurumRozeti, cumle_basi, qt_cevirisi_kur, qt_turkce_cevirisi, tekerlek_korumasi_kur)
from arayuz import hata_yakalayici
from arayuz.veri import kayit as veri_kayit
from cekirdek import ceviri, gunluk, masaustu, surum

from arayuz.pencere.model_islemleri import (  # noqa: F401
    KOK, ORNEKLER, UYGULAMA_ADI, _KONU_BAGIMLILIK, _YER_SEKME, EDITOR_ANAHTARI,
    SEKME_ADLARI, TASARIM_SEKMELERI, DOGRULAMA_SEKMELERI, TUR_ADLARI,
    yer_sekme_anahtari, yer_etiketi, tur_ozeti, model_ozet_parcalari, model_ozet_metni,
    sekme_isaretleri, sonraki_adim, _alan_varsayilan_mi, _AD_LISTELERI, model_adlari,
    _adlari_cevir, tur_hafizasini_esitle, _eksik_parcayi_kur, _SABLON_ADLARI,
    kor_turu_degistir)
from arayuz.pencere.gecmis import _GECMIS_SINIR, GecmisMixin  # noqa: F401
from arayuz.pencere.proje import _ICE_AKTAR_NOTU, ProjeMixin  # noqa: F401
from arayuz.pencere.menuler import YARDIM_HTML, _BulguAcilir, MenulerMixin  # noqa: F401
from arayuz.pencere.ana_pencere import _seviye_renk, _SEVIYE_ADI, AnaPencere  # noqa: F401


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    # Ondalik ayirici her yerde nokta: sayi kutulari sistem diline (tr_TR'de
    # virgul) degil C yerel ayarina gore yazar/okur; etiketler de nokta kullanir.
    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    app = QtWidgets.QApplication(sys.argv[:1])
    gunluk.kur()
    hata_yakalayici.kur(app)
    ayar = QtCore.QSettings("openmc_arayuz", "arayuz")
    ceviri.dil_ayarla(ceviri.varsayilan_dil(ayar=ayar.value("gorunum/dil", "", str)))
    qt_cevirisi_kur(app, ceviri.etkin_dil())
    ceviri.dinleyici_ekle(lambda kod: qt_cevirisi_kur(app, kod))
    # P2: Qt uygulama adi = masaustu kimligi (.desktop adi, StartupWMClass, Wayland
    # app_id); gorunen urun adi pencere basliklarinda surum.UYGULAMA_ADI'dir.
    app.setApplicationName(masaustu.UYGULAMA_KIMLIGI)
    app.setDesktopFileName(masaustu.UYGULAMA_KIMLIGI)
    app.setWindowIcon(QtGui.QIcon(masaustu.simge_yolu()))
    app.setApplicationVersion(surum.surum())
    tema.uygula(app)
    tekerlek_korumasi_kur(app)
    from cekirdek import veri_yolu
    veri_yolu.surece_uygula()           # K2: Veri sayfasi secimi -> surec ortami
    pencere = AnaPencere(argv[0] if argv else None)
    pencere.show()
    veri_kayit.ilk_acilis(pencere, proje_acik=bool(argv))   # K2: veri yoksa Veri sayfasi

    # Pencereyi buyutme:
    #   showMaximized() bu makinedeki pencere yoneticisinde yok sayiliyor,
    #   show()'dan hemen sonra setWindowState() de tutmuyor -- pencerenin
    #   once HARITALANMASI gerekiyor. Bu yuzden olay dongusu basladiktan
    #   kisa bir sure sonra uygulaniyor.
    def _buyut_gecikmeli():
        pencere.setWindowState(pencere.windowState() | QtCore.Qt.WindowMaximized)
    # Baglam nesnesi pencere: pencere daha once kapanirsa zamanlayici iptal olur.
    QtCore.QTimer.singleShot(120, pencere, _buyut_gecikmeli)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
