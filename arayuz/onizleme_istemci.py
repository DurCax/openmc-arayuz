# -*- coding: utf-8 -*-
"""
onizleme_istemci.py -- onizleme cizim iscisinin (cekirdek/cizim_sureci.py)
arayuz tarafi: KALICI tek alt surec + istek numarasi.

  ist = CizimIstemcisi(parent)
  ist.cerceve_geldi.connect(f)      # yalniz GUNCEL istegin yanitlari (Cerceve)
  ist.coktu.connect(g)              # beklenmedik sonlanma / baslatilamama (metin)
  no = ist.iste({"tur": "ciz", "spec": ..., "kesitler": [...]})   # hemen doner
  ist.mesgul_mu()                   # guncel istegin "son" yaniti gelmedi mi
  ist.kapat()                       # 'cik' -> bekle -> terminate -> kill (zombisiz)

Kurallar
  - Ana is parcacigi HIC beklemez: yazma QProcess tamponuna, okuma
    readyReadStandardOutput ile olay dongusunden.
  - Yeni istek eskisini gecersiz kilar: no'su guncel olmayan her yanit atilir
    (isci de kesitler arasinda yeni istegi gorup eskisini birakir).
  - Isci olurse: coktu(mesaj) yayilir; isci daha once 'hazir' olmussa hemen
    yeniden baslatilir (sicak). Coken istek YENIDEN GONDERILMEZ (ayni model
    tekrar oldurebilir); bir sonraki istek yeni surece gider.
  - Kapanista surec beklenip toplanir (QProcess waitForFinished = waitpid);
    uygulama cikisinda (aboutToQuit + atexit) canli istemcilerin hepsi kapatilir.
"""

import atexit
import sys
import weakref

from PySide6 import QtCore

from cekirdek import cizim_sureci as cs
from cekirdek import giris as _giris
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_KAPANIS_MS = 3000          # 'cik' sonrasi temiz cikis beklemesi (init yok: < 0.1 s olculdu)
_SONLANDIRMA_MS = 2000      # terminate (SIGTERM) sonrasi bekleme, sonra SIGKILL
_HATA_GUNLUGU_SINIRI = 4000  # stderr'den gunluge aktarilan en cok karakter (parca basina)

_CANLI = weakref.WeakSet()


def _hepsini_kapat():
    for ist in list(_CANLI):
        try:
            ist.kapat()
        except RuntimeError:                # Qt nesnesi zaten silinmis
            _log.info("onizleme istemcisi kapanista silinmisti", exc_info=True)


atexit.register(_hepsini_kapat)


class CizimIstemcisi(QtCore.QObject):
    """Onizleme iscisiyle konusan tek nokta (bkz. modul belgesi)."""

    cerceve_geldi = QtCore.Signal(object)
    coktu = QtCore.Signal(str)
    hazir = QtCore.Signal()

    def __init__(self, parent=None, komut=None):
        super().__init__(parent)
        self._komut = komut
        self._surec = None
        self._cozucu = None
        self._hazir = False
        self._son_no = 0
        self._bitmedi = False
        self._kapaniyor = False
        _CANLI.add(self)
        uyg = QtCore.QCoreApplication.instance()
        if uyg is not None:
            uyg.aboutToQuit.connect(self.kapat)

    # ------------------------------------------------------------------
    def _komut_ve_ortam(self):
        if self._komut is not None:
            return self._komut, QtCore.QProcessEnvironment.systemEnvironment()
        program, arg = _giris.alt_surec_komutu(_giris.ALT_CIZIM, [], python=sys.executable)
        ortam = QtCore.QProcessEnvironment.systemEnvironment()
        yol = _giris.alt_surec_pythonpath(ortam.value("PYTHONPATH"))
        if yol:                             # kaynak agaci: paket koku MEVCUDUN onune
            ortam.insert("PYTHONPATH", yol)
        from cekirdek import ceviri as _ceviri
        ortam.insert(_ceviri.ORTAM_DEGISKENI, _ceviri.etkin_dil())   # hata metinleri ayni dilde
        return (program, arg), ortam

    def baslat(self):
        """Isciyi baslatir (zaten calisiyorsa bir sey yapmaz)."""
        if self.calisiyor_mu():
            return
        (program, arg), ortam = self._komut_ve_ortam()
        surec = QtCore.QProcess(self)
        surec.setProcessEnvironment(ortam)
        surec.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        surec.readyReadStandardOutput.connect(self._oku)
        surec.readyReadStandardError.connect(self._hata_ciktisi)
        surec.finished.connect(self._bitti)
        surec.errorOccurred.connect(self._surec_hatasi)
        self._surec, self._cozucu, self._hazir = surec, cs.CerceveCozucu(), False
        self._kapaniyor = False
        surec.start(program, arg)

    def calisiyor_mu(self):
        return self._surec is not None and self._surec.state() != QtCore.QProcess.NotRunning

    def hazir_mi(self):
        return self._hazir and self.calisiyor_mu()

    def pid(self):
        return int(self._surec.processId()) if self.calisiyor_mu() else None

    def mesgul_mu(self):
        return self._bitmedi

    # ------------------------------------------------------------------
    def iste(self, istek):
        """Istegi gonderir (kopyasina yeni no yazilir); no'yu dondurur."""
        self._son_no += 1
        self.baslat()
        if self._surec is None:             # baslatma hemen basarisiz oldu (coktu yayildi)
            return self._son_no
        self._bitmedi = True
        try:
            self._surec.write(cs.cerceve(dict(istek, no=self._son_no)))
        except cs.ProtokolHatasi as e:
            self._bitmedi = False
            _log.warning("onizleme istegi gonderilemedi", exc_info=True)
            self.coktu.emit(_("Önizleme isteği gönderilemedi: %s") % e)
        return self._son_no

    def iptal(self):
        """Guncel istegi gecersiz kilar: yanitlari artik iletilmez."""
        self._son_no += 1
        self._bitmedi = False

    def kapat(self):
        """Isciyi temiz sonlandirir ve toplar (tekrar cagrilabilir)."""
        surec, self._surec = self._surec, None
        self._bitmedi, self._hazir, self._kapaniyor = False, False, True
        if surec is None:
            return
        for sinyal in (surec.readyReadStandardOutput, surec.readyReadStandardError,
                       surec.finished, surec.errorOccurred):
            sinyal.disconnect()
        if surec.state() != QtCore.QProcess.NotRunning:
            surec.write(cs.cerceve({"tur": cs.ISTEK_CIK, "no": self._son_no + 1}))
            surec.closeWriteChannel()
            if not surec.waitForFinished(_KAPANIS_MS):
                _log.warning("onizleme iscisi 'cik'a yanit vermedi; sonlandiriliyor")
                surec.terminate()
                if not surec.waitForFinished(_SONLANDIRMA_MS):
                    surec.kill()
                    surec.waitForFinished(_SONLANDIRMA_MS)
        surec.deleteLater()

    # ------------------------------------------------------------------
    def _oku(self):
        surec = self._surec
        if surec is None:
            return
        try:
            cerceveler = self._cozucu.besle(bytes(surec.readAllStandardOutput()))
        except cs.ProtokolHatasi:
            _log.error("onizleme iscisinden bozuk yanit; surec yeniden baslatilacak",
                       exc_info=True)
            surec.kill()                    # _bitti cokme yolunu isler
            return
        for c in cerceveler:
            self._cerceve_isle(c)

    def _cerceve_isle(self, c):
        tur, no = c.baslik.get("tur"), c.baslik.get("no")
        if tur == cs.YANIT_HAZIR:
            self._hazir = True
            self.hazir.emit()
            return
        if no != self._son_no:
            return                          # eski istegin yaniti: atilir
        if tur == cs.YANIT_SON:
            self._bitmedi = False
        self.cerceve_geldi.emit(c)

    def _hata_ciktisi(self):
        if self._surec is not None:
            self._hata_ciktisi_al(self._surec)

    def _bitti(self, kod, durum):
        if self._kapaniyor:
            return
        surec, self._surec = self._surec, None
        sicakti = self._hazir
        self._bitmedi, self._hazir = False, False
        if surec is not None:
            self._hata_ciktisi_al(surec, son=True)
            surec.deleteLater()
        nasil = (_("çöktü") if durum == QtCore.QProcess.CrashExit
                 else _("çıkış kodu %d") % kod)
        mesaj = _("Önizleme süreci beklenmedik biçimde sonlandı (%s); yeniden "
                  "başlatıldı. Model değişince önizleme yeniden çizilir.") % nasil
        _log.warning("onizleme iscisi sonlandi: kod=%s durum=%s", kod, durum)
        self.coktu.emit(mesaj)
        if sicakti:
            self.baslat()

    @staticmethod
    def _hata_ciktisi_al(surec, son=False):
        """Iscinin stderr'i gunluge (cokmede uyari duzeyinde: son satirlar ipucudur)."""
        metin = bytes(surec.readAllStandardError()).decode("utf-8", "replace").strip()
        if metin:
            (_log.warning if son else _log.info)("onizleme iscisi: %s",
                                                 metin[-_HATA_GUNLUGU_SINIRI:])

    def _surec_hatasi(self, hata):
        if hata != QtCore.QProcess.FailedToStart or self._kapaniyor:
            return                          # cokme _bitti'de islenir
        surec, self._surec = self._surec, None
        self._bitmedi, self._hazir = False, False
        aciklama = surec.errorString() if surec is not None else ""
        if surec is not None:
            surec.deleteLater()
        _log.error("onizleme iscisi baslatilamadi: %s", aciklama)
        self.coktu.emit(_("Önizleme süreci başlatılamadı: %s") % aciklama)
