# -*- coding: utf-8 -*-
"""
test_calistir_pano.py -- Dalga 2 / Ajan 8: Calistir sayfasinin sonuc panosu.

  * Fixture kosu dizininden (testler/veri/kosu_ornek, Ajan 10) pano dolar:
    k-eff ± sigma, F_dH ve F_q statepoint'le BIREBIR; sure ve hiz gunlukten;
    yakinsama ve entropi grafikleri gunlukteki cevrimlerden cizilir.
  * calistir/gunluk_ozeti, calistir/ozet saf islevleri (girdiyi degistirmez).
  * Pano kartlari: sabit kaynak, entropi kapali (bos durum), hedef belirsizlik,
    dogrulama kapisi satiri.
  * Grafik kartlari: PNG kaydet (basari / iptal / yazma hatasi).
  * Kosu dizini yolu ortadan kisaltilir; 1280 genislikte yatay kaydirma yok.

Yalnizca offscreen calisir; modal diyaloglar exec() EDILMEZ.
"""

import copy
import json
import os
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")

GUNLUK = """
 Bat./Gen.      k       Entropy         Average k
 =========   ========   ========   ====================
        1/1    1.10000    6.50000
        2/1    1.20000    6.90000
        3/1    1.18000    7.00000    1.18000 +/- 0.01000
 Creating state point statepoint.3.h5...
 =======================>     TIMING STATISTICS     <=======================
 Total time elapsed                = 1.9250e+02 seconds
 Calculation Rate (inactive)       = 12000.0 particles/second
 Calculation Rate (active)         = 52400.4 particles/second
"""


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _fixture_kopyasi():
    """Fixture'in gecici kopyasi (testler kaynak dizini degistirmesin)."""
    gecici = tempfile.mkdtemp(prefix="pano_")
    hedef = os.path.join(gecici, "kosu")
    shutil.copytree(FIXTURE, hedef)
    return gecici, hedef


def _fixture_spec():
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        return json.load(f)


def _yuklu_sayfa():
    from arayuz.sekme_calistir import CalistirSekmesi
    gecici, dizin = _fixture_kopyasi()
    c = CalistirSekmesi()
    c.spec_ayarla(_fixture_spec(), os.path.join(gecici, "proje.json"))
    return c, gecici, c.kosu_dizinini_yukle(dizin)


# ---------------------------------------------------------------------------
# 1. Fixture -> pano (statepoint ile birebir)
# ---------------------------------------------------------------------------
def test_fixture_pano_statepoint_birebir():
    _qt()
    import openmc
    from cekirdek import kosucu
    c, gecici, tamam = _yuklu_sayfa()
    try:
        kontrol("fixture kosu dizini yuklendi", tamam and c.sonuc_var())
        with openmc.StatePoint(kosucu.son_statepoint(FIXTURE)) as sp:
            k, s = sp.keff.nominal_value, sp.keff.std_dev
        beklenen = "%.5f ± %.5f" % (k, s)
        kontrol("k-eff karti statepoint ile birebir (%s)" % beklenen,
                c.pano.k.deger.text() == beklenen, "-> %r" % c.pano.k.deger.text())
        kontrol("pcm rozeti sigma'dan", c.pano.k.rozet.text() == "±%d pcm" % round(s * 1e5),
                "-> %r" % c.pano.k.rozet.text())
        kontrol("hedef belirsizlik yazili", "pcm" in c.pano.k.alt.text())
        metin = c.sonuc_metin.toPlainText()
        kontrol("F_ΔH 1.1214 ve F_q 1.7935 (fixture) tam sonuc metninde",
                "F_ΔH     = 1.1214" in metin and "F_q      = 1.7935" in metin)
        kontrol("guc haritasi karti gorunur", c.guc_karti.isVisibleTo(c)
                and c.guc_harita.isVisibleTo(c))
        kontrol("sure ve hiz gunlukten", c.pano.sure.deger.text() != "—"
                and c.pano.hiz.deger.text() != "—",
                "-> %r %r" % (c.pano.sure.deger.text(), c.pano.hiz.deger.text()))
        kontrol("gunlukteki 40 cevrim grafige", len(c._cevrimler) == 40
                and c.yakinsama.isVisibleTo(c) and c.entropi_karti.isVisibleTo(c),
                "-> %d" % len(c._cevrimler))
        kontrol("entropi karti son degeri gunlukle ayni",
                c.pano.entropi.deger.text() == "%.3f" % c._cevrimler[-1]["entropi"],
                "-> %r" % c.pano.entropi.deger.text())
        kontrol("dogrulama satiri: diskten yuklendi",
                c.pano.dogrulama_rozeti.text() == "Diskten yüklendi")
        kontrol("son kosu dizini gercek dizin (rapor)",
                c.son_kosu_dizini() and os.path.isdir(c.son_kosu_dizini()))
        kontrol("cekmece satir sayisi", "satır" in c.ayrinti_karti.satir_etiketi.text()
                and not c.ayrinti_karti.satir_etiketi.text().startswith("OpenMC günlüğü · 0"))
    finally:
        c.deleteLater()
        shutil.rmtree(gecici, ignore_errors=True)


def test_kosu_dizini_hatalari():
    _qt()
    from arayuz.sekme_calistir import CalistirSekmesi
    from cekirdek import kosucu
    gecici = tempfile.mkdtemp(prefix="pano_bos_")
    c = CalistirSekmesi()
    eski = kosucu.sonuc_oku
    try:
        kontrol("statepoint yok: yuklenmez, basarisiz gosterilir",
                c.kosu_dizinini_yukle(gecici) is False and c._basarisiz
                and "statepoint" in c.durum_etiket.text())
        _g, dizin = _fixture_kopyasi()

        def bozuk(_sp):
            raise ValueError("bozuk dosya")
        kosucu.sonuc_oku = bozuk
        kontrol("sonuc okunamadi: yuklenmez, neden yazilir",
                c.kosu_dizinini_yukle(dizin) is False and "bozuk dosya" in
                c.durum_etiket.text() and not c.sonuc_var())
        shutil.rmtree(_g, ignore_errors=True)
        kontrol("gunluk yoksa bos metin", c._gunlugu_oku(gecici) == "")
    finally:
        kosucu.sonuc_oku = eski
        c.deleteLater()
        shutil.rmtree(gecici, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2. Saf islevler
# ---------------------------------------------------------------------------
def test_gunluk_ozeti():
    from arayuz.calistir import gunluk_ozeti as g
    o = g.ozetle(GUNLUK)
    kontrol("sure okunur", o["sure_s"] == 192.5, "-> %r" % o)
    kontrol("hiz: etkin cevrim hizi", o["hiz"] == 52400.4)
    kontrol("statepoint adi", o["statepoint"] == "statepoint.3.h5")
    bos = g.ozetle("")
    kontrol("bos gunluk: hepsi None", bos == {"sure_s": None, "hiz": None, "statepoint": None})
    pasif = g.ozetle(" Calculation Rate (inactive)       = 900.0 particles/second")
    kontrol("etkin yoksa pasif hiz", pasif["hiz"] == 900.0)
    kontrol("sure metni", (g.sure_metni(192.5), g.sure_metni(3725), g.sure_metni(None),
                           g.sure_metni(-1)) == ("3:12", "1:02:05", "—", "—"))
    kontrol("hiz metni binlik ince bosluk", g.hiz_metni(52400.4) == "52\u2009400"
            and g.hiz_metni(None) == "—" and g.hiz_metni(-2) == "—")
    import re
    kontrol("bozuk sayi None", g._son_sayi(re.compile(r"x=(\S+)"), "x=1e+") is None)


def _guc(zayif=False, f_q=1.5, dilim=(0, 2)):
    return {"faktorler": {"F_dH": 1.12, "F_q": f_q, "sicak_cubuk": (1, 2),
                          "kafes_turu": "kare", "kafes_turleri": None,
                          "sicak_dilim": dilim,
                          "F_dH_tepe_yakini": 8 if zayif else 1,
                          "F_dH_yanlilik": 0.004 if zayif else 0.0}}


def test_ozet_satirlari():
    from arayuz.calistir import ozet
    s = {"keff": (1.0, 0.001), "cevrim": 50, "pasif": 10, "parcacik": 1000,
         "entropi": [], "tallyler": {}, "kinetik": {"beta_eff": 0.0065,
                                                     "beta_eff_sapma": 0.0001,
                                                     "lambda": 2e-5, "lambda_sapma": 1e-6}}
    kopya = copy.deepcopy(s)
    satirlar, yakinsadi = ozet.ozdeger_ozeti(s)
    kontrol("ozdeger ozeti: cevrim, kaynak, kinetik",
            satirlar[0].startswith("çevrim") and "kapalı" in satirlar[1]
            and any("β_eff" in x for x in satirlar) and yakinsadi is None)
    kontrol("entropi okunamadi satiri",
            "okunamadı" in ozet.kaynak_satiri(dict(s, entropi_hata="yok"))[0])
    ent = dict(s, entropi=[5.0 + 0.001 * (i % 3) for i in range(50)])
    kontrol("entropi degerlendirilir", ozet.kaynak_satiri(ent)[0].startswith("kaynak   = ["))
    sabit = ozet.sabit_ozeti(s, {"kuvvet": 1.0})
    kontrol("sabit ozet siddet 1: NOT satiri", sabit[-1].startswith("NOT"))
    kontrol("sabit ozet mutlak birim notu",
            ozet.sabit_ozeti(s, {"kuvvet": 1e10})[-1].startswith("Not"))
    kontrol("guc yok: bos", ozet.guc_ozeti(s) == [])
    kontrol("guc hatasi yazilir", "okunamadı" in ozet.guc_ozeti(dict(s, guc_hata="x"))[0])
    g = ozet.guc_ozeti(dict(s, guc=_guc(zayif=True)))
    kontrol("guc: F_dH + zayif istatistik uyarisi + dilim",
            "F_ΔH" in g[0] and "yukarı yanlı" in g[0] and "dilim 3" in g[2])
    g2 = ozet.guc_ozeti(dict(s, guc=_guc(f_q=None, dilim=None)))
    kontrol("2B: F_q tanimsiz", "tanımsız" in g2[1] and "dilim" not in g2[2])
    kontrol("tally yok: bos liste", ozet.tally_metinleri(s, False) == [])
    kontrol("saf islevler girdiyi degistirmez", s == kopya)


# ---------------------------------------------------------------------------
# 3. Pano kartlari
# ---------------------------------------------------------------------------
def test_pano_kartlari():
    _qt()
    from arayuz.calistir.pano import SonucPanosu
    p = SonucPanosu()
    spec = {"ayarlar": {"mod": "eigenvalue", "parcacik": 10000, "cevrim": 100, "pasif": 20},
            "calistirma": {"is_parcacigi": 6}}
    kopya = copy.deepcopy(spec)
    p.sonuc_yaz({"keff": (1.0, 0.00001), "cevrim": 100, "pasif": 20, "parcacik": 10000},
                spec, {"sure_s": 10.0})
    kontrol("hedefin altinda: basari rozeti", p.k.rozet.tur() == "basari",
            "-> %r" % p.k.rozet.tur())
    kontrol("hiz cevrim zamanindan (hiz yoksa)", p.hiz.deger.text() == "100\u2009000",
            "-> %r" % p.hiz.deger.text())
    kontrol("is parcacigi alt metni", p.hiz.alt.text() == "6 iş parçacığı")
    kontrol("etkin + pasif cevrim", p.sure.alt.text().startswith("80 etkin + 20"))
    kontrol("entropi kapali: bos durum metni", p.entropi.deger.text() == "—"
            and "kapalı" in p.entropi.alt.text())
    p.sonuc_yaz({"keff": None, "cevrim": 5, "pasif": 0},
                {"ayarlar": {"mod": "fixed source"}})
    kontrol("sabit kaynak: k-eff tanimsiz", p.k.deger.text() == "—"
            and "tanımsız" in p.k.alt.text())
    kontrol("sabit kaynakta hedef yok", SonucPanosu._hedef_pcm({"ayarlar": {"mod": "x"}})
            is None)
    p.sonuc_yaz({"keff": (1.0, 0.001), "entropi_hata": "dosya bozuk"}, {})
    kontrol("entropi hatasi kartta", "bozuk" in p.entropi.alt.text())
    p.sonuc_yaz({"keff": (1.0, 0.001), "pasif": 2, "entropi": [1.0, 2.0, 3.0]}, {})
    kontrol("entropi belirsiz rozeti + ipucu", p.entropi.rozet.text() == "Belirsiz"
            and p.entropi.toolTip() != "")
    for tur in ("basari", "uyari", "hata", "notr"):
        p.dogrulama_ayarla("x", tur, "")
    kontrol("dogrulama aciklamasi bosken gizli", not p.dogrulama_metni.isVisibleTo(p))
    p.temizle()
    kontrol("temizle: k bos", p.k.deger.text() == "—" and p.k.etiket.text() == "k-eff")
    kontrol("pano spec'i degistirmez", spec == kopya)
    p.deleteLater()


# ---------------------------------------------------------------------------
# 4. Grafik kartlari
# ---------------------------------------------------------------------------
def test_grafik_kartlari_ve_kaydet():
    _qt()
    from PySide6 import QtWidgets
    from arayuz.calistir.yakinsama import EntropiKarti, YakinsamaKarti
    y, e = YakinsamaKarti(), EntropiKarti()
    cevrimler = [{"cevrim": i, "k": 1.0 + 0.01 * (i % 2), "entropi": 5.0 + i * 0.01,
                  "ortalama": 1.0 if i > 3 else None, "sapma": 0.001 if i > 3 else None}
                 for i in range(1, 11)]
    y.ciz(cevrimler, pasif=3)
    kontrol("yakinsama: iki seri + bant + pasif cizgisi", len(y.eksen.lines) >= 3)
    y.ciz([])
    kontrol("bos veri: eksen temiz", len(y.eksen.lines) == 0)
    e.ciz([{"cevrim": 1, "entropi": None}])
    kontrol("entropisiz cevrimler: bos durum", not e.eksen.axison)
    e.ciz(cevrimler, pasif=3)
    kontrol("entropi cizildi", e.eksen.axison and len(e.eksen.lines) == 2)
    gecici = tempfile.mkdtemp(prefix="grafik_")
    uyari = QtWidgets.QMessageBox.warning
    try:
        yol = os.path.join(gecici, "y.png")
        y.dosya_sor = lambda _v: yol
        kontrol("PNG kaydedildi", y.kaydet() == yol and os.path.getsize(yol) > 0)
        y.dosya_sor = lambda _v: ""
        kontrol("iptal: None", y.kaydet() is None)
        gorulen = []
        QtWidgets.QMessageBox.warning = lambda *a: gorulen.append(a)
        y.dosya_sor = lambda _v: os.path.join(gecici, "yok", "y.png")
        kontrol("yazma hatasi kullaniciya gosterilir", y.kaydet() is None and gorulen)
    finally:
        QtWidgets.QMessageBox.warning = uyari
        shutil.rmtree(gecici, ignore_errors=True)
        y.deleteLater(); e.deleteLater()


# ---------------------------------------------------------------------------
# 5. Yerlesim: kisaltilan yol, 1280 genislik
# ---------------------------------------------------------------------------
def test_kisaltilan_yol():
    _qt()
    from arayuz.calistir.kartlar import KisaltilanYol
    w = KisaltilanYol("/" + "/".join(["cok_uzun_dizin_adi"] * 20))
    w.resize(200, 20)
    kontrol("en az genislik 0 (sayfayi genisletmez)", w.minimumSizeHint().width() == 0)
    kontrol("dar alanda ortadan kisaltilir", "…" in w.gorunen_metin()
            and w.text().startswith("/cok_uzun"))
    w.grab()
    w.deleteLater()


def test_pano_1280_yatay_kaydirma_yok():
    _qt()
    from PySide6 import QtWidgets
    c, gecici, _t = _yuklu_sayfa()
    alan = QtWidgets.QScrollArea()
    alan.setWidgetResizable(True)
    alan.setWidget(c)
    try:
        alan.resize(1280 - 212, 720)       # kenar cubugu cikarilmis sayfa alani
        alan.show()
        QtWidgets.QApplication.processEvents()
        kontrol("1280: Calistir panosunda yatay kaydirma yok",
                alan.horizontalScrollBar().maximum() == 0,
                "-> %d px" % alan.horizontalScrollBar().maximum())
    finally:
        alan.deleteLater()
        shutil.rmtree(gecici, ignore_errors=True)


HIZLI = [test_fixture_pano_statepoint_birebir, test_kosu_dizini_hatalari, test_gunluk_ozeti,
         test_ozet_satirlari, test_pano_kartlari, test_grafik_kartlari_ve_kaydet,
         test_kisaltilan_yol, test_pano_1280_yatay_kaydirma_yok]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
