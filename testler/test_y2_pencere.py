# -*- coding: utf-8 -*-
"""
 test_y2_pencere.py  --  v3 Y2 goruntuleyici penceresi: gercek iscide kesit/renk
                         kipleri/kaynak/3B, cakisma kipinin goruntusu, tally
                         bindirmesinin konum dogrulugu, fare bilgisi, arayuz donmaz
                         (H2 donma olcumu kalibi), Araclar menusu
"""

import math
import os
import time

import numpy as np

from testler.ortak_test import kontrol, ORNEK

_DONMA_SINIRI = 0.200      # s; plan Dalga H: "hicbir islemde arayuz 200 ms'den uzun donmaz"
_DONMA_DENEMESI = 3
_ZAMAN_ASIMI = 60.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _bekle(kosul, sure=_ZAMAN_ASIMI):
    from PySide6 import QtCore
    uyg = _uyg()
    bas = time.monotonic()
    while not kosul() and time.monotonic() - bas < sure:
        uyg.processEvents(QtCore.QEventLoop.AllEvents, 20)
        time.sleep(0.002)
    return kosul()


class _DonmaOlcer:
    """Olay dongusu araliklarinin en buyugu (test_h2_onizleme ile ayni kalip)."""

    _ARALIK_MS = 10

    def __init__(self):
        from PySide6 import QtCore
        self.en_buyuk = 0.0
        self._son = time.perf_counter()
        self._sayac = QtCore.QTimer()
        self._sayac.setInterval(self._ARALIK_MS)
        self._sayac.timeout.connect(self._tik)
        self._sayac.start()

    def _tik(self):
        simdi = time.perf_counter()
        self.en_buyuk = max(self.en_buyuk, simdi - self._son)
        self._son = simdi

    def durdur(self):
        self._sayac.stop()
        return self.en_buyuk


class _SahteIstemci:
    """Isci yerine verilen cerceveleri yayan istemci."""

    def __init__(self):
        from PySide6 import QtCore

        class _S(QtCore.QObject):
            cerceve_geldi = QtCore.Signal(object)
            coktu = QtCore.Signal(str)
        self._s = _S()
        self.cerceve_geldi, self.coktu = self._s.cerceve_geldi, self._s.coktu
        self.giden, self._no = [], 0

    def iste(self, istek):
        self._no += 1
        self.giden.append(dict(istek, no=self._no))
        return self._no

    def yanitla(self, baslik, diziler=None):
        from cekirdek.cizim_sureci import Cerceve
        self.cerceve_geldi.emit(Cerceve(dict(baslik, no=self._no), diziler or {}))

    def kapat(self):
        pass


def _pencere(spec=None, istemci=None):
    _uyg()
    from arayuz.goruntuleyici.pencere import GoruntuleyiciPenceresi
    p = GoruntuleyiciPenceresi(spec, istemci=istemci)
    p.resize(1100, 750)
    p.show()
    return p


def _sahte_kesit(ist, geom, genislik=(10.0, 10.0), renkler=None):
    """Sahte isci: model + kesit + son (xy, orijin)."""
    ist.yanitla({"tur": "model", "sinir_kutu": list(genislik), "yukseklik": None,
                 "renkler": renkler or {"1": [200, 0, 0], "2": [0, 0, 200]},
                 "gosterge": [], "malzeme_adlari": {"1": "yakit"}, "hucre_adlari": {}})
    ist.yanitla({"tur": "kesit", "sira": 0, "eksen": "xy", "genislik": list(genislik),
                 "piksel": geom.shape[1], "cakismalar": []}, {"geom": geom})
    ist.yanitla({"tur": "son", "durum": "tamam"})


def _cakismali_geom():
    """20 x 20 piksel (0.5 cm): sol yari malzeme 1, sag yari 2; ortada iki sutun
    cakisma (malzeme -3, hucre -4), ust iki satir tanimsiz (-2)."""
    hucre = np.ones((20, 20), np.int32)
    malzeme = np.ones((20, 20), np.int32)
    hucre[:, 10:], malzeme[:, 10:] = 2, 2
    hucre[:, 9:11], malzeme[:, 9:11] = -4, -3
    hucre[:2], malzeme[:2] = -2, -2
    return np.stack([hucre, np.zeros_like(hucre), malzeme], axis=-1)


def _resim(p):
    return p.kesit_tuvali.ax.images[0].get_array()


# ----------------------------------------------------------------------------

def test_cakisma_kipi_goruntusu():
    print("\n[Y2P-1] cakisma kipi: -3 pikselleri hata renginde, -2 turuncu, model soluk")
    from arayuz.onizleme_boyama import tema_rgb01
    from arayuz.goruntuleyici import renk_kipi as rk
    ist = _SahteIstemci()
    p = _pencere(_spec("pwr_17x17"), ist)
    try:
        p.p_kesit.renk.setCurrentIndex(p.p_kesit.renk.findData(rk.CAKISMA_KIPI))
        p._kesit_iste()
        kontrol("cakisma kipinde istek cakisma denetimli", ist.giden[-1]["cakisma"] is True)
        _sahte_kesit(ist, _cakismali_geom())
        img = np.asarray(_resim(p))
        hata = tuple(int(round(255 * v)) for v in tema_rgb01("hata"))
        kontrol("cakisma pikseli hata rengi", tuple(img[10, 9, :3]) == hata
                and img[10, 9, 3] == 255, "-> %s" % (img[10, 9].tolist(),))
        kontrol("tanimsiz piksel opak turuncu", img[0, 0, 3] == 255 and img[0, 0, 0] > img[0, 0, 2])
        kontrol("normal bolge yari saydam gri", img[10, 2, 3] < 255
                and img[10, 2, 0] == img[10, 2, 1])
        kontrol("durum cakisma (36) ve tanimsiz (40) sayisini yazar",
                "36 piksel" in p.durum.text() and "40 piksel" in p.durum.text(), "-> %s" % p.durum.text())
        n = len(ist.giden)
        p.p_kesit.renk.setCurrentIndex(p.p_kesit.renk.findData(rk.MALZEME))
        img = np.asarray(_resim(p))
        kontrol("malzeme kipine gecis isciye gitmez (eldeki dilim)", len(ist.giden) == n)
        kontrol("malzeme kipinde malzeme 1 kirmizi", tuple(img[10, 2, :3]) == (200, 0, 0))
    finally:
        p.kapat()


def test_fare_bilgisi_ve_yakinlastirma():
    print("\n[Y2P-2] fare: koordinat + hucre/malzeme bilgisi; tekerlek yeni pencere ister")
    ist = _SahteIstemci()
    p = _pencere(_spec("pwr_17x17"), ist)
    try:
        p._kesit_iste()
        _sahte_kesit(ist, _cakismali_geom())
        p._fare(-3.0, 0.0)
        bilgi = p.bilgi.text()
        p._fare(0.0, 0.0)
        cak = p.bilgi.text()
        kontrol("bilgi: x, hucre 1, malzeme 1 (yakit)", "x = -3" in bilgi and "1 (yakit)" in bilgi,
                "-> %s" % bilgi)
        kontrol("cakisma noktasi belirtilir", "ÇAKIŞMA" in cak, "-> %s" % cak)
        p._yakinlastir(2.0, 2.0, 0.0)
        p._kesit_iste()
        oge = ist.giden[-1]["kesitler"][0]
        kontrol("yakinlastirma: genislik 5, merkez (1, 0)", oge["genislik"] == [5.0, 5.0]
                and oge["merkez"][:2] == [1.0, 0.0], "-> %s" % oge)
        p._kaydir(1.0, -1.0)
        p._kesit_iste()
        kontrol("kaydirma merkezi tasir", ist.giden[-1]["kesitler"][0]["merkez"][:2] == [2.0, -1.0])
    finally:
        p.kapat()


def _mesh_sonucu():
    from cekirdek.mesh_tally.sonuc import MeshSonuc
    izg = (np.linspace(-5, 5, 6), np.linspace(-5, 5, 6), np.array([-1.0, 1.0]))
    o = np.arange(25, dtype=float).reshape(5, 5, 1, 1, 1, 1) + 1.0
    return MeshSonuc(ad="aki", tur="duzenli", izgaralar=izg, merkez=(0.0, 0.0, 0.0),
                     skorlar=("flux",), nuklidler=("total",), enerji=None, ortalama=o,
                     sapma=0.01 * o, ozdeger=True)


def test_tally_bindirme_konumu():
    print("\n[Y2P-3] tally bindirmesi: bilinen mesh hucresi geometri koordinatinin ustunde")
    from arayuz.goruntuleyici import gorunum as gr
    ist = _SahteIstemci()
    p = _pencere(_spec("pwr_17x17"), ist)
    try:
        p._kesit_iste()
        _sahte_kesit(ist, _cakismali_geom())
        p.p_tally.sonuclari_ayarla("/yok/statepoint.h5", [_mesh_sonucu()])
        p.p_tally.normalizasyon.setCurrentIndex(p.p_tally.normalizasyon.findData("kaynak"))
        p.p_tally.setChecked(True)
        ax = p.kesit_tuvali.ax
        kontrol("geometri + bindirme iki resim", len(ax.images) == 2)
        ust = ax.images[1]
        kontrol("ayni extent", tuple(ust.get_extent()) == tuple(ax.images[0].get_extent()))
        dizi = ust.get_array()
        g = p.gorunum
        # (x, y) = (3, -3): i = 4 (x 3-5), j = 0 (y -5..-3) -> 4 * 5 + 0 + 1 = 21
        i, j = gr.piksel_indeksi(g, 3.4, -4.0, dizi.shape)
        kontrol("(3.4, -4) -> hucre (4, 0) = 21", float(dizi[i, j]) == 21.0,
                "-> %s" % dizi[i, j])
        i, j = gr.piksel_indeksi(g, -4.5, 4.5, dizi.shape)
        kontrol("(-4.5, 4.5) -> hucre (0, 4) = 5", float(dizi[i, j]) == 5.0)
        kontrol("opaklik paneldeki deger", math.isclose(ust.get_alpha(), p.p_tally.opaklik()))
        p._fare(3.4, -4.0)
        kontrol("fare bilgisi tally degerini yazar", "tally: 21" in p.bilgi.text(),
                "-> %s" % p.bilgi.text())
        p.p_tally.setChecked(False)
        kontrol("kapatinca bindirme kalkar", len(ax.images) == 1)
    finally:
        p.kapat()


def test_gercek_iscide_kesit_kaynak_3b():
    print("\n[Y2P-4] gercek isci: pwr_3b kesit, kaynak noktalari ve 3B goruntu")
    p = _pencere(_spec("pwr_3b"))
    try:
        kontrol("kesit cizildi", p.bekle(_ZAMAN_ASIMI) and p._kesit is not None
                and len(p.kesit_tuvali.ax.images) == 1)
        g, geom, _c = p._kesit
        kontrol("kesitte malzeme var", int((geom[..., 2] > 0).sum()) > 0)
        p.p_kaynak.setChecked(True)
        kontrol("kaynak noktalari geldi", p.bekle(_ZAMAN_ASIMI) and p._noktalar is not None
                and len(p._noktalar) == p.p_kaynak.sayi.value())
        kontrol("noktalar tuvalde", len(p.kesit_tuvali.ax.collections) == 1)
        p.sekmeler.setCurrentIndex(1)
        p.uc_boyut_iste()
        kontrol("3B istek bitti", p.bekle(_ZAMAN_ASIMI))
        rgb = np.asarray(p.uc_tuvali.ax.images[0].get_array()) if p.uc_tuvali.ax.images else None
        kontrol("3B goruntu cizildi ve duz degil", rgb is not None and rgb.ndim == 3
                and len(np.unique(rgb.reshape(-1, 3), axis=0)) > 10)
        import tempfile
        yol = p.kaydet(os.path.join(tempfile.mkdtemp(prefix="y2_png_"), "uc.png"))
        kontrol("PNG kaydedildi", os.path.getsize(yol) > 1000)
    finally:
        p.kapat()


def test_arayuz_donmaz():
    print("\n[Y2P-5] goruntuleyici: VVER-1000 kor kesit + kaynak + 3B sirasinda olay dongusu "
          "%d ms'den uzun durmaz" % (_DONMA_SINIRI * 1000))
    p = _pencere(None)
    try:
        p._istemci.baslat()
        _bekle(p._istemci.hazir_mi)
        en_buyuk = None
        for deneme in range(_DONMA_DENEMESI):
            olcer = _DonmaOlcer()
            t0 = time.perf_counter()
            p.spec_ayarla(_spec("vver1000_kor" if deneme % 2 == 0 else "pwr_beavrs_kor"))
            p._kesit_iste()
            cagri = time.perf_counter() - t0
            p.bekle(_ZAMAN_ASIMI)
            p.uc_boyut_iste()
            p.bekle(_ZAMAN_ASIMI)
            _bekle(lambda: False, 0.3)
            b = olcer.durdur()
            en_buyuk = b if en_buyuk is None else min(en_buyuk, b)
            if en_buyuk < _DONMA_SINIRI:
                break
        kontrol("istek hemen doner (< 50 ms)", cagri < 0.05, "-> %.0f ms" % (cagri * 1e3))
        kontrol("en uzun olay dongusu araligi < %d ms" % (_DONMA_SINIRI * 1000),
                en_buyuk < _DONMA_SINIRI, "-> %.0f ms" % (en_buyuk * 1e3))
        kontrol("kesit ve 3B cizildi", p._kesit is not None and bool(p.uc_tuvali.ax.images))
    finally:
        p.kapat()


def test_hata_ve_cokme_gosterilir():
    print("\n[Y2P-6] hata yaniti tuvalde gosterilir; cokmede sira bosalir")
    ist = _SahteIstemci()
    p = _pencere(_spec("pwr_17x17"), ist)
    try:
        p._kesit_iste()
        ist.yanitla({"tur": "son", "durum": "hata", "hata": "bozuk geometri", "iz": ""})
        kontrol("hata durum satirinda", "bozuk geometri" in p.durum.text())
        p._kesit_iste()
        ist.coktu.emit("isci coktu")
        kontrol("cokme: sira bos, ileti", not p._sira.mesgul_mu() and "coktu" in p.durum.text())
        p.uc_boyut_iste()
        kontrol("model bilgisi yokken 3B istenmez", ist.giden[-1]["tur"] == "ciz")
    finally:
        p.kapat()


def test_araclar_menusu():
    print("\n[Y2P-7] Araclar menusunde 'Goruntuleyici…' tekil pencereyi acar")
    _uyg()
    from arayuz.ana_pencere import AnaPencere
    from arayuz.goruntuleyici import pencere as gp
    ana = AnaPencere()
    ana._kaydetme_sor = lambda: True
    try:
        eylem = ana.e_goruntuleyici
        kontrol("eylem metni", "Görüntüleyici" in eylem.text())
        eylem.trigger()
        p = gp._TEKIL.get("pencere")
        kontrol("pencere acildi", p is not None and p.isVisible())
        eylem.trigger()
        kontrol("ikinci tetik ayni pencere", gp._TEKIL.get("pencere") is p)
        p.close()
    finally:
        ana._kirli = False
        ana.close()
        ana.deleteLater()


HIZLI = [test_cakisma_kipi_goruntusu, test_fare_bilgisi_ve_yakinlastirma,
         test_tally_bindirme_konumu, test_hata_ve_cokme_gosterilir, test_araclar_menusu,
         test_gercek_iscide_kesit_kaynak_3b, test_arayuz_donmaz]
YAVAS = []
