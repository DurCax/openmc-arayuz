# -*- coding: utf-8 -*-
"""
gunluk.py -- uygulama logu (stdlib logging).

  from cekirdek.gunluk import kaydedici
  log = kaydedici(__name__)
  log.exception("tally okunamadi")       # except blogu icinde: iz dahil

Dosya: $XDG_STATE_HOME/openmc_arayuz/openmc_arayuz.log
       (XDG_STATE_HOME yoksa ~/.local/state/openmc_arayuz/...)
Donen dosya: ~1 MB x 5 yedek. Testler (testler/ortak_test.py) XDG_STATE_HOME'u
gecici dizine yonlendirir; gercek kullanici dizinine yazilmaz.

Dizin yazilamazsa uygulama COKMEZ: dosya isleyicisi kurulmaz, durum bir kez
stderr'e yazilir ve kayitlar logging'in son care isleyicisine (stderr, WARNING
ve ustu) duser.
"""

import logging
import logging.handlers
import os
import sys
import threading

from cekirdek import yollar

KOK_KAYDEDICI = "openmc_arayuz"
UYGULAMA_DIZINI = yollar.UYGULAMA_DIZINI      # geriye uyum (tek kaynak: yollar)
LOG_DOSYASI = "openmc_arayuz.log"
AZAMI_BAYT = 1_000_000
YEDEK_SAYISI = 5
BICIM = "%(asctime)s %(levelname)-8s %(name)s [%(process)d:%(threadName)s] %(message)s"

_kilit = threading.Lock()
_durum = {"isleyici": None, "yol": None}


def durum_dizini(ortam=None):
    """Uygulamanin durum (log) dizini; XDG Base Directory kurali (tek kaynak:
    yollar.durum_dizini; goreli XDG_STATE_HOME yok sayilir)."""
    return yollar.durum_dizini(ortam)


def dosyaya_yaziliyor():
    """Dosya isleyicisi kurulu mu (log gercekten diske yaziliyor mu)."""
    return _durum["isleyici"] is not None


def log_yolu():
    """Etkin log dosyasinin tam yolu."""
    return os.path.join(durum_dizini(), LOG_DOSYASI)


def _dosya_isleyicisi_kur(yol):
    """Donen dosya isleyicisi; dizin olusturulamaz/acilamazsa None."""
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        isleyici = logging.handlers.RotatingFileHandler(
            yol, maxBytes=AZAMI_BAYT, backupCount=YEDEK_SAYISI, encoding="utf-8")
    except OSError as e:
        sys.stderr.write("openmc_arayuz: log dosyasi acilamadi (%s): %s\n" % (yol, e))
        return None
    isleyici.setFormatter(logging.Formatter(BICIM))
    return isleyici


def kur(seviye=logging.INFO):
    """Kok kaydediciye dosya isleyicisini baglar. Tekrar cagrilabilir: log
    yolu degistiyse (ornek XDG_STATE_HOME) eski isleyici kapatilip yenisi
    kurulur. Kok kaydediciyi doner."""
    kok = logging.getLogger(KOK_KAYDEDICI)
    yol = log_yolu()
    with _kilit:
        if _durum["yol"] != yol:
            eski = _durum["isleyici"]
            if eski is not None:
                kok.removeHandler(eski)
                eski.close()
            yeni = _dosya_isleyicisi_kur(yol)
            if yeni is not None:
                kok.addHandler(yeni)
            _durum.update(isleyici=yeni, yol=yol)
        if kok.level == logging.NOTSET or kok.level > seviye:
            kok.setLevel(seviye)
    return kok


def kaydedici(ad):
    """Uygulama ad alaninda kaydedici: kaydedici("cekirdek.kosucu") ->
    "openmc_arayuz.cekirdek.kosucu". Ilk cagrida dosya isleyicisini kurar."""
    kur()
    return logging.getLogger("%s.%s" % (KOK_KAYDEDICI, ad) if ad else KOK_KAYDEDICI)


_BILDIRILEN = set()


def uyar_bir_kez(log, mesaj, *args):
    """Yakalanan istisnayi (exc_info) WARNING olarak BIR KEZ loglar.

    Dogrulama her duzenlemede kosar; ayni bozuk durum her tus vurusunda
    loga yazilmasin diye (kaydedici, mesaj, istisna turu ve metni) anahtari
    surec boyunca bir kez yazilir. Yalnizca except blogu icinden cagrilir."""
    import sys
    tur, deger, _iz = sys.exc_info()
    anahtar = (log.name, mesaj % args if args else mesaj,
               getattr(tur, "__name__", ""), str(deger))
    with _kilit:
        if anahtar in _BILDIRILEN:
            return
        _BILDIRILEN.add(anahtar)
    log.warning(mesaj, *args, exc_info=True)


def dosya_isleyicisi():
    """Kurulu donen dosya isleyicisi (yoksa None)."""
    return _durum["isleyici"]


def bosalt():
    """Tamponu dosyaya yazar (test ve cikis oncesi)."""
    isleyici = _durum["isleyici"]
    if isleyici is not None:
        isleyici.flush()
