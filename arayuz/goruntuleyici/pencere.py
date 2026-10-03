# -*- coding: utf-8 -*-
"""
================================================================================
 pencere.py  --  Geometri goruntuleyicisi penceresi (v3 Y2; Araclar -> Goruntuleyici…)
================================================================================

 MIMARI
   Kendi kalici cizim iscisi (cekirdek/cizim_sureci.py, H2) vardir: onizlemenin
   oturumunu ve Calistir kapisini ETKILEMEZ (onizleme kendi istemcisini kullanir).
   Butun dilimleme, 3B isin izleme ve kaynak ornekleme iscidedir; pencere istegi
   gonderir ve hemen doner (IstekSirasi: kesit/kaynak/3B ayni isciyi paylasir).
   Ana is parcacigi yalniz boyama (renk_kipi), bindirme ornekleme (bindirme) ve
   matplotlib cizimini yapar; statepoint okumasi QThread'de (okuyucu.py).

 YENIDEN ISTEME KURALI
   Isciye yalniz kesit penceresi (eksen, merkez, genislik, cozunurluk) ya da
   cakisma denetimi degisince gidilir. Renk kipi, tally secimi, saydamlik, sigma
   maskesi, kaynak dilim kalinligi eldeki dilimden yeniden boyanir.
================================================================================
"""

import dataclasses
import os

from PySide6 import QtCore, QtWidgets

from cekirdek import cizim_sureci as cs
from cekirdek import cizim_goruntu as cg
from cekirdek import mesh_tally as mt
from cekirdek import onbellek
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.goruntuleyici import bindirme as bd
from arayuz.goruntuleyici import gorunum as gr
from arayuz.goruntuleyici import kamera as km
from arayuz.goruntuleyici import renk_kipi as rk
from arayuz.goruntuleyici.istek_sirasi import IstekSirasi
from arayuz.goruntuleyici.okuyucu import TallyOkuyucu
from arayuz.goruntuleyici.paneller import (KAYNAK_STATEPOINT, KaynakPaneli, KesitPaneli,
                                           TallyPaneli, UcBoyutPaneli)
from arayuz.goruntuleyici.tuval import GoruntuTuvali, KesitTuvali
from arayuz.onizleme_boyama import tema_rgb01
from arayuz.onizleme_istemci import CizimIstemcisi
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK

KESIT, KAYNAK, ISIN = "kesit", "kaynak", "isin"
_GECIKME_MS = 250                 # ardisik degisiklikler tek istege duser
_PANEL_GENISLIGI = 320
_KAYDET_DPI = 150
_TEKIL = {}
_SAHIPSIZ = set()                 # kapanista beklemeyi asan okuyucular (bitince birakilir)
_OKUMA_BEKLEME_MS = 10_000        # kapanista okuyucu basina bekleme (buyuk statepoint ~1 s)
# Istek bekcisi: H2'nin 120 s'si yerine 30 s. En agir olculen kesit (SFR + cakisma
# denetimi) ~12 s (H2); OpenMC 0.16 isin izleyicisi bazi kor modellerinde (VVER-1000,
# BEAVRS kor; olculdu 02.10.2026) "pure virtual method called" ile ASILI kalir --
# 30 s'de isci oldurulur, acik hata verilir, isci yeniden baslar.
BEKCI_MS = 30_000
# Iscinin ilk istegi soguk hazirlamadir (import + kurulum + init): H2'nin 120 s'si.
ILK_BEKCI_MS = 120_000


def _tanimsiz_rengi():
    from matplotlib.colors import to_rgb
    return to_rgb(tokenlar.OKABE_ITO["turuncu"])


class GoruntuleyiciPenceresi(QtWidgets.QMainWindow):
    """Kesit (malzeme/hucre/cakisma), mesh bindirmesi, kaynak noktalari, 3B gorunum."""

    istek_bitti = QtCore.Signal(str, bool)       # (tur, basarili) -- testler ve durum

    def __init__(self, spec=None, statepoint=None, parent=None, istemci=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Görüntüleyici"))
        self.spec, self.statepoint = None, None
        self.gorunum = None               # istenen pencere
        self._kesit = None                # (Gorunum, geom, cakisma) son gelen dilim
        self._meta, self._adlar, self._adlar_ozet = None, None, None
        self._noktalar, self._noktalar_anahtari = None, None
        self._raster = None
        self._okuyucular = []             # calisan statepoint okuyuculari (QThread)
        self._okuma_kusagi = 0            # yalniz son statepoint_ayarla'nin sonucu kabul
        self._kaynak_hatasi = None        # basarisiz kaynak isteginin anahtari (tekrarlanmaz)
        self._kapandi = False
        self._istenen_cakisma = False     # son kesit isteginde cakisma denetimi
        self._istenen_kaynak = None       # son kaynak isteginin anahtari
        self._kaynak_bilgisi = None
        self._istemci = istemci or CizimIstemcisi(self, zaman_asimi_ms=BEKCI_MS,
                                                  ilk_zaman_asimi_ms=ILK_BEKCI_MS)
        self._istemci.cerceve_geldi.connect(self._cerceve_geldi)
        self._istemci.coktu.connect(self._coktu)
        self._sira = IstekSirasi(self._istemci.iste)
        self._sayac = QtCore.QTimer(self)
        self._sayac.setSingleShot(True)
        self._sayac.setInterval(_GECIKME_MS)
        self._sayac.timeout.connect(self._kesit_iste)
        self._kur()
        uyg = QtCore.QCoreApplication.instance()
        if uyg is not None:
            uyg.aboutToQuit.connect(self.kapat)
        self.spec_ayarla(spec, statepoint)

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _kur(self) -> None:
        self.p_kesit, self.p_tally = KesitPaneli(), TallyPaneli()
        self.p_kaynak, self.p_3b = KaynakPaneli(), UcBoyutPaneli()
        self.d_yenile = QtWidgets.QPushButton(_("Modeli yenile"))
        self.d_kaydet = QtWidgets.QPushButton(_("PNG olarak kaydet…"))
        sol = QtWidgets.QWidget()
        duzen = QtWidgets.QVBoxLayout(sol)
        for w in (self.p_kesit, self.p_tally, self.p_kaynak, self.p_3b, self.d_yenile,
                  self.d_kaydet):
            duzen.addWidget(w)
        duzen.addStretch(1)
        kaydirma = QtWidgets.QScrollArea()
        kaydirma.setWidgetResizable(True)
        kaydirma.setWidget(sol)
        kaydirma.setMinimumWidth(_PANEL_GENISLIGI)
        self.kesit_tuvali, self.uc_tuvali = KesitTuvali(), GoruntuTuvali()
        self.sekmeler = QtWidgets.QTabWidget()
        self.sekmeler.addTab(self.kesit_tuvali, _("Kesit"))
        self.sekmeler.addTab(self.uc_tuvali, _("3B görünüm"))
        self.bilgi = QtWidgets.QLabel("")
        self.bilgi.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.durum = QtWidgets.QLabel("")
        self.durum.setWordWrap(True)
        sag = QtWidgets.QWidget()
        sd = QtWidgets.QVBoxLayout(sag)
        sd.setContentsMargins(A["s"], A["s"], A["s"], A["s"])
        sd.addWidget(self.sekmeler, 1)
        sd.addWidget(self.bilgi)
        sd.addWidget(self.durum)
        bolucu = QtWidgets.QSplitter()
        bolucu.addWidget(kaydirma)
        bolucu.addWidget(sag)
        bolucu.setStretchFactor(1, 1)
        self.setCentralWidget(bolucu)
        self._baglan()

    def _baglan(self) -> None:
        self.p_kesit.degisti.connect(self._kesit_paneli_degisti)
        self.p_kesit.sifirla.connect(self.tum_modeli_goster)
        self.p_kesit.boya.connect(self._yeniden_boya)
        self.p_tally.degisti.connect(self._yeniden_boya)
        self.p_tally.statepoint_sec.connect(self._statepoint_diyalogu)
        self.p_kaynak.degisti.connect(self._kaynak_degisti)
        self.p_3b.ciz.connect(self.uc_boyut_iste)
        self.d_yenile.clicked.connect(self._modeli_yenile)
        self.d_kaydet.clicked.connect(self._kaydet_diyalogu)
        self.kesit_tuvali.fare_hareketi.connect(self._fare)
        self.kesit_tuvali.yakinlastir.connect(self._yakinlastir)
        self.kesit_tuvali.kaydir.connect(self._kaydir)

    # ------------------------------------------------------------------
    # disaridan
    # ------------------------------------------------------------------
    def spec_ayarla(self, spec, statepoint=None) -> None:
        """Yeni model (ve varsa son kosunun statepoint'i): gorunum sifirlanir."""
        self.spec = spec
        self.gorunum, self._kesit, self._raster = None, None, None
        self._meta, self._kaynak_hatasi = None, None
        self._noktalar, self._noktalar_anahtari = None, None
        self.bilgi.setText("")
        if statepoint != self.statepoint:
            self.statepoint_ayarla(statepoint)
        if spec is None:
            self.kesit_tuvali.mesaj(_("Açık model yok: önce bir model açın."))
            return
        self.iste()

    def statepoint_ayarla(self, yol):
        """Mesh tally sonuclari ve kaynak bankasi icin statepoint (arka planda okunur)."""
        self.statepoint = yol
        self._okuma_kusagi += 1
        if not yol or self._kapandi:
            self.p_tally.sonuclari_ayarla(None, [])
            return
        kusak = self._okuma_kusagi
        okuyucu = TallyOkuyucu(yol, self)
        okuyucu.bitti.connect(lambda *a, k=kusak: self._tallyler_geldi(k, *a))
        okuyucu.finished.connect(lambda o=okuyucu: self._okuyucu_bitti(o))
        self._okuyucular.append(okuyucu)
        okuyucu.start()

    def _okuyucu_bitti(self, okuyucu) -> None:
        if okuyucu in self._okuyucular:
            self._okuyucular.remove(okuyucu)
            okuyucu.deleteLater()

    def iste(self) -> None:
        """Kesiti gecikmeli ister (ardisik cagrilar tek istege duser)."""
        if not self._kapandi:
            self._sayac.start()

    def tum_modeli_goster(self) -> None:
        self.gorunum = None
        self._kesit_iste()

    def mesgul_mu(self):
        return (self._sayac.isActive() or self._sira.mesgul_mu()
                or any(o.isRunning() for o in self._okuyucular))

    def bekle(self, zaman_asimi):
        """Testler ve ekran goruntusu araci: istekler bitene dek olay dongusu."""
        import time
        uyg = QtWidgets.QApplication.instance()
        bitis = time.monotonic() + zaman_asimi
        while self.mesgul_mu() and time.monotonic() < bitis:
            uyg.processEvents(QtCore.QEventLoop.AllEvents, 20)
        uyg.processEvents()
        return not self.mesgul_mu()

    def kaydet(self, yol):
        """Etkin sekmenin tuvalini PNG olarak kaydeder."""
        tuval = self.sekmeler.currentWidget()
        tuval.figur.savefig(yol, dpi=_KAYDET_DPI, bbox_inches="tight")
        return yol

    # ------------------------------------------------------------------
    # istekler
    # ------------------------------------------------------------------
    def _kesit_iste(self) -> None:
        self._sayac.stop()
        if self._kapandi or self.spec is None:
            return
        piksel = self.p_kesit.piksel()
        oge = (self.gorunum.istek_ogesi() if self.gorunum is not None else
               {"eksen": self.p_kesit.eksen.currentData(), "piksel": piksel})
        ozet = onbellek.ozet(self.spec)
        istek = {"tur": cs.ISTEK_CIZ, "spec": self.spec, "kesitler": [oge],
                 "cakisma": self.p_kesit.cakisma_istenir(), "adlar": ozet != self._adlar_ozet}
        self.durum.setText(_("Çiziliyor…"))
        self._istenen_cakisma = istek["cakisma"]
        self._sira.iste(KESIT, istek)

    def _kaynak_iste(self) -> None:
        anahtar = self._kaynak_anahtari()
        if self.spec is None or anahtar == self._noktalar_anahtari:
            self._yeniden_boya()
            return
        if anahtar == self._istenen_kaynak and self._sira.mesgul_mu():
            return                          # ayni istek zaten iscide ya da sirada
        if anahtar == self._kaynak_hatasi:
            return                          # ayni istek basarisizdi: her boyamada yinelenmez
        istek = {"tur": cg.ISTEK_KAYNAK, "spec": self.spec, "sayi": self.p_kaynak.sayi.value(),
                 "tohum": 1}
        if self.p_kaynak.kaynak.currentData() == KAYNAK_STATEPOINT:
            if not self.statepoint:
                self.durum.setText(_("Kaynak bankası için statepoint seçin (Ağ tally "
                                     "bindirmesi > Statepoint seç…)."))
                return
            istek["statepoint"] = self.statepoint
        self._noktalar_anahtari = None
        self._istenen_kaynak = anahtar
        self._sira.iste(KAYNAK, istek)

    def _kaynak_anahtari(self):
        tur = self.p_kaynak.kaynak.currentData()
        sp = None
        if tur == KAYNAK_STATEPOINT and self.statepoint:
            sp = (self.statepoint, _mtime(self.statepoint))   # ayni yola yeni kosu yazilabilir
        return (onbellek.ozet(self.spec) if self.spec else None, tur,
                self.p_kaynak.sayi.value(), sp)

    def uc_boyut_iste(self) -> None:
        """3B golgeli goruntuyu ister (model bilgisi once kesitle gelir)."""
        if self.spec is None or self._meta is None:
            self.uc_tuvali.mesaj(_("Önce kesit çizilmeli (model bilgisi bekleniyor)."))
            return
        w, h = self.uc_tuvali.piksel()
        olcek = min(1.0, cs.PIKSEL_EN_COK / max(w, h))
        piksel = tuple(max(cs.PIKSEL_EN_AZ, int(v * olcek)) for v in (w, h))
        renk = self.p_3b.renk.currentData()
        gizli = self.p_3b.gizlenenler() if renk == rk.MALZEME else []
        govde = km.istek(self.p_3b.kamera(), self._meta["sinir_kutu"], self._meta["yukseklik"],
                         piksel, renk, gizli)
        self.uc_tuvali.mesaj(_("3B görünüm çiziliyor…"))
        self._sira.iste(ISIN, dict(govde, tur=cg.ISTEK_ISIN, spec=self.spec))

    # ------------------------------------------------------------------
    # yanitlar
    # ------------------------------------------------------------------
    def _cerceve_geldi(self, c) -> None:
        b = c.baslik
        tur = self._sira.tur(b.get("no"))
        if tur is None:
            return
        yt = b.get("tur")
        if yt == cs.YANIT_MODEL:
            self._model_geldi(b)
        elif yt == cs.YANIT_KESIT:
            self._kesit_geldi(b, c.diziler["geom"])
        elif yt == cg.YANIT_GORUNTU:
            self.uc_tuvali.ciz(c.diziler["rgb"])
        elif yt == cg.YANIT_KAYNAK:
            self._noktalar = c.diziler["r"]
            self._noktalar_anahtari = self._istenen_kaynak
            self._kaynak_bilgisi = b
        elif yt == cs.YANIT_SON:
            self._son_geldi(tur, b)

    def _model_geldi(self, b) -> None:
        self._meta = b
        if "malzeme_adlari" in b:
            self._adlar = {"malzeme_adlari": b["malzeme_adlari"],
                           "hucre_adlari": b.get("hucre_adlari", {})}
            self._adlar_ozet = onbellek.ozet(self.spec) if self.spec else None
        adlar = (self._adlar or {}).get("malzeme_adlari", {})
        self.p_3b.malzemeleri_ayarla([(int(k), adlar.get(k, k)) for k in b.get("renkler", {})])

    def _kesit_geldi(self, b, geom) -> None:
        merkez = tuple(b.get("merkez") or cs.KESIT_MERKEZI)
        g = gr.Gorunum(b["eksen"], merkez, tuple(b["genislik"]), int(b["piksel"]))
        if self.gorunum is None:
            self.gorunum = g
            self.p_kesit.gorunumu_yaz(g)
        self._kesit = (g, geom, self._istenen_cakisma)
        self._raster = None

    def _son_geldi(self, tur, b) -> None:
        self._sira.bitti(b.get("no"))
        if b.get("durum") == cs.DURUM_IPTAL:
            return
        if b.get("durum") != cs.DURUM_TAMAM:
            self._hata(tur, b.get("hata") or "")
            return
        if tur == KESIT:
            self._yeniden_boya()
            if self.p_kaynak.isChecked():
                self._kaynak_iste()
        elif tur == KAYNAK:
            self._yeniden_boya()
        self.istek_bitti.emit(tur, True)

    def _hata(self, tur, metin) -> None:
        self.durum.setText(_("Görüntüleyici: %s") % metin)
        if tur == KAYNAK:
            self._kaynak_hatasi, self._istenen_kaynak = self._istenen_kaynak, None
        if tur == ISIN:
            self.uc_tuvali.mesaj(_("3B görünüm üretilemedi:\n\n%s") % metin, hata=True)
        elif tur == KESIT:
            self._kesit = None
            self.kesit_tuvali.mesaj(_("Kesit çizilemedi:\n\n%s") % metin, hata=True)
        self.istek_bitti.emit(tur, False)

    def _coktu(self, mesaj) -> None:
        tur = self._sira.suren_tur()
        if tur == ISIN:
            self.uc_tuvali.mesaj(_("3B ışın izleme bu modelde başarısız oldu (OpenMC 0.16 "
                                   "SolidRayTracePlot sınırlaması; bazı tam kor modellerinde "
                                   "süreç çöker ya da asılı kalır).\n\n%s") % mesaj, hata=True)
        if tur == KAYNAK:
            self._kaynak_hatasi = self._istenen_kaynak
        self._istenen_kaynak = None
        self._sira.sifirla()
        self.durum.setText(mesaj)
        self.istek_bitti.emit("", False)

    # ------------------------------------------------------------------
    # boyama
    # ------------------------------------------------------------------
    def _yeniden_boya(self, *_a) -> None:
        """Eldeki dilimden boyar; cakisma secimi dilimle uyusmuyorsa yeniden ister."""
        if self._kesit is None:
            return
        g, geom, cakismali = self._kesit
        if self.p_kesit.cakisma_istenir() and not cakismali:
            self._kesit_iste()
            return
        renkler = {int(k): v for k, v in (self._meta or {}).get("renkler", {}).items()}
        img = rk.goruntu(geom, self.p_kesit.renk.currentData(), renkler,
                         tema_rgb01("hata"), _tanimsiz_rengi())
        bindirme = self._bindirme(g, geom.shape)
        noktalar = None
        if self.p_kaynak.isChecked() and self._noktalar is not None:
            noktalar = bd.izdusum(self._noktalar, g, self.p_kaynak.kalinlik_degeri())
        self.kesit_tuvali.ciz(img, g, self._baslik(g), bindirme, noktalar)
        self._durum_yaz(geom, noktalar)

    def _bindirme(self, g, sekil):
        s = self.p_tally.secili()
        self._raster = None
        if not self.p_tally.isChecked() or s is None or self.p_tally.skor.currentData() is None:
            return None
        try:
            deger, maske, birim = bd.tally_dizileri(
                s, self.p_tally.skor.currentData(), self.p_tally.grup.currentData(),
                self.p_tally.normalizasyon.currentData(), self.p_tally.esik_orani(),
                mt.eksenel_sonsuz(self.spec or {}))
        except ValueError as e:
            self.durum.setText(_("Bindirme yapılamadı: %s") % e)
            return None
        self._raster = bd.raster(s, deger, maske, g, self.p_tally.sigma.isChecked(), sekil)
        return self._raster, self.p_tally.opaklik(), birim

    def _baslik(self, g):
        _h, _d, n = gr.EKSENLER[g.eksen]
        return "%s   %s = %.4g cm   %.4g × %.4g cm" % (
            (self.spec or {}).get("ad", ""), gr.EKSEN_ADLARI[n], g.konum, *g.genislik)

    def _durum_yaz(self, geom, noktalar) -> None:
        say = rk.sayim(geom)
        parcalar = [_("Kesit güncel.")]
        if say["cakisma"]:
            parcalar.append(_("ÇAKIŞMA: %d piksel birden çok hücrede.") % say["cakisma"])
        if say["tanimsiz"] and self.p_kesit.renk.currentData() == rk.CAKISMA_KIPI:
            parcalar.append(_("Hücresiz (geometri dışı ya da tanımsız): %d piksel.")
                            % say["tanimsiz"])
        if noktalar is not None:
            parcalar.append(_("Kaynak noktası: %d / %d gösteriliyor.")
                            % (len(noktalar[0]), len(self._noktalar)))
        self.durum.setText("  ".join(parcalar))

    # ------------------------------------------------------------------
    # etkilesim
    # ------------------------------------------------------------------
    def _kesit_paneli_degisti(self) -> None:
        if self._meta is None or self.gorunum is None:
            self.iste()
            return
        g, p = self.gorunum, self.p_kesit
        eksen = p.eksen.currentData()
        if eksen != g.eksen:
            g = gr.varsayilan(self._meta["sinir_kutu"], self._meta["yukseklik"], eksen,
                              p.piksel())
        else:
            g = gr.konum_ayarla(g, p.konum.value())
            g = gr.yakinlastir(g, g.genislik[0] / p.genislik.value())
        self._yeni_gorunum(dataclasses.replace(g, piksel=p.piksel()))

    def _yeni_gorunum(self, g) -> None:
        if g != self.gorunum:
            self.gorunum = g
            self.p_kesit.gorunumu_yaz(g)
            self.iste()
        else:
            self._yeniden_boya()

    def _yakinlastir(self, kat, u, v) -> None:
        if self.gorunum is not None:
            self._yeni_gorunum(gr.yakinlastir(self.gorunum, kat, odak=(u, v)))

    def _kaydir(self, du, dv) -> None:
        if self.gorunum is not None:
            self._yeni_gorunum(gr.kaydir(self.gorunum, du, dv))

    def _fare(self, u, v) -> None:
        if self._kesit is None:
            return
        g, geom, _c = self._kesit
        b = gr.nokta_bilgisi(g, geom, u, v, self._adlar)
        if b is None:
            self.bilgi.setText("")
            return
        metin = gr.bilgi_metni(b)
        if self._raster is not None:
            yer = gr.piksel_indeksi(g, u, v, self._raster.deger.shape)
            if yer is not None:
                metin += "   " + _("tally: %.4g") % self._raster.deger[yer]
        self.bilgi.setText(metin)

    def _kaynak_degisti(self) -> None:
        self._kaynak_hatasi = None          # kullanici secimi: yeniden denenir
        if self.p_kaynak.isChecked():
            self._kaynak_iste()
        else:
            self._yeniden_boya()

    def _tallyler_geldi(self, kusak, yol, sonuclar, atlanan, hata) -> None:
        if kusak != self._okuma_kusagi or self._kapandi:
            return                          # bayat okuma (sonra baska statepoint istendi)
        self.p_tally.sonuclari_ayarla(yol, sonuclar)
        if hata:
            self.durum.setText(_("Statepoint okunamadı: %s") % hata)
        elif not sonuclar:
            self.durum.setText(_("Statepoint'te ağ (mesh) tally'si yok."))
        if atlanan:
            _log.info("atlanan mesh tally'leri: %s", atlanan)

    def _statepoint_diyalogu(self) -> None:
        yol, _f = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Statepoint seç"), os.path.dirname(self.statepoint or "") or "",
            _("Statepoint (statepoint*.h5);;HDF5 (*.h5)"))
        if yol:
            self.statepoint_ayarla(yol)
            self._noktalar_anahtari = None

    def _modeli_yenile(self) -> None:
        ana = self.parent()
        self.spec_ayarla(getattr(ana, "spec", self.spec), son_statepoint(ana) or self.statepoint)

    def _kaydet_diyalogu(self) -> None:
        yol, _f = QtWidgets.QFileDialog.getSaveFileName(
            self, _("PNG olarak kaydet"), "goruntuleyici.png", _("PNG resmi (*.png)"))
        if not yol:
            return
        try:
            self.kaydet(yol)
            self.durum.setText(_("Kaydedildi: %s") % yol)
        except (OSError, ValueError) as e:
            _log.warning("goruntuleyici resmi kaydedilemedi", exc_info=True)
            QtWidgets.QMessageBox.warning(self, _("Kaydedilemedi"), str(e))

    # ------------------------------------------------------------------
    def closeEvent(self, olay) -> None:                    # noqa: N802 (Qt adi)
        self.kapat()
        super().closeEvent(olay)

    def kapat(self) -> None:
        """Isciyi temiz sonlandirir (kalici, tekrar cagrilabilir); suren butun
        okumalari zaman asimli bekler, asani sahipsiz birakir (QThread calisirken
        silinmesin); tekil kaydi temizler (ac() kapanmis pencereyi kullanmasin)."""
        if _TEKIL.get("pencere") is self:
            _TEKIL.pop("pencere", None)
        if self._kapandi:
            return
        self._kapandi = True
        self._sayac.stop()
        self._istemci.kapat()
        for okuyucu in list(self._okuyucular):
            okuyucu.requestInterruption()
            if not okuyucu.wait(_OKUMA_BEKLEME_MS):
                _log.warning("statepoint okuyucusu %d ms'de bitmedi; arka planda birakildi",
                             _OKUMA_BEKLEME_MS)
                okuyucu.setParent(None)
                _SAHIPSIZ.add(okuyucu)
                okuyucu.finished.connect(lambda o=okuyucu: _SAHIPSIZ.discard(o))
        self._okuyucular = []


def _mtime(yol):
    try:
        return os.path.getmtime(yol)
    except OSError:
        _log.info("statepoint degisim zamani okunamadi: %s", yol)
        return None


def son_statepoint(ana):
    """Ana pencerenin son basarili kosusunun statepoint'i; yoksa None."""
    calistir = getattr(ana, "s_calistir", None)
    if calistir is None:
        return None
    from cekirdek import kosucu
    dizin = calistir.son_kosu_dizini()
    if not dizin:
        # Bu oturumda kosu yok: projenin kosu dizininde kayitli son statepoint (Q1-22);
        # yol goruntuleyicide gorunur, kullanici baska dosya secebilir.
        aday = calistir._kosu_dizini()
        dizin = aday if aday and os.path.isdir(aday) else None
    return kosucu.son_statepoint(dizin) if dizin else None


def ac(ana=None):
    """Tekil goruntuleyici penceresi; varsa one getirir ve modeli gunceller."""
    p = _TEKIL.get("pencere")
    spec, sp = getattr(ana, "spec", None), son_statepoint(ana)
    if p is None:
        p = GoruntuleyiciPenceresi(spec, sp, parent=ana)
        p.setWindowFlag(QtCore.Qt.Window, True)
        p.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        p.destroyed.connect(lambda *_a: _TEKIL.pop("pencere", None))
        p.resize(1200, 800)
        _TEKIL["pencere"] = p
    else:
        p.spec_ayarla(spec, sp or p.statepoint)
    p.show()
    p.raise_()
    p.activateWindow()
    return p
