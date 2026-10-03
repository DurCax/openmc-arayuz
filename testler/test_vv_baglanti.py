# -*- coding: utf-8 -*-
"""
test_vv_baglanti.py -- V&V (cekirdek/vv) -> uygunluk denetimi baglantisi.

  [VB1] kume.aoa_filtresi: tur + bicim + tayf (+ zenginlik sinifi); eksikse None.
  [VB2] kume.uygulama_ozeti: AOA'ya uygun alt kume -> USL; uygun alt kume
        yoksa durust "bu uygulama için USL yok (AOA dışında)".
  [VB3] rapor_uygunluk.denetle / ek_verisi: B secilince V&V ozeti ve uygulama
        denetle()'ye gecer; K6 artik her zaman "V&V kümesi yok" demez.
  [VB4] CLI `openmc-arayuz-kosu uygunluk --profil B`: ayni baglanti.
  [VB5] Panel: B secili ve EALF tally'si yoksa oneri dugmesi; onaylaninca
        spec'e EALF tally'si eklenir (otomatik EKLENMEZ).

Fixture: testler/veri/kosu_ornek (Monte Carlo KOSULMAZ). Yalniz offscreen.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")


def _spec():
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        return json.load(f)


@contextlib.contextmanager
def _gecici_kosu(uygulama=None):
    """Fixture kopyasi; uygulama verilirse uygunluk_girdisi.json'a yazilir."""
    kok = tempfile.mkdtemp(prefix="vv_baglanti_")
    hedef = os.path.join(kok, "kosu")
    shutil.copytree(FIXTURE, hedef)
    if uygulama is not None:
        with open(os.path.join(hedef, "uygunluk_girdisi.json"), "w", encoding="utf-8") as f:
            json.dump({"uygulama": uygulama}, f)
    try:
        yield hedef
    finally:
        shutil.rmtree(kok, True)


def _k6(bulgular):
    return [b for b in bulgular if b.kural == "K6"]


def _leu_oksit_kume(n=12):
    """Fixture uygulamasina (U-235 %3.2 oksit, termal) uyan sahte deney kumesi."""
    from cekirdek.vv.istatistik import Vaka
    return [Vaka("l%d" % i, 0.998 + 0.0004 * ((i * 5) % 7 - 3), 0.0003, 1.0, 0.002,
                 {"bolunebilir": "U-235", "fiziksel_bicim": "oksit", "tayf": "termal",
                  "zenginlik": 2.5 + 0.2 * i, "ealf": 0.2 + 0.01 * i, "yansitici": "su"},
                 "LCT-%d" % i) for i in range(n)]


@contextlib.contextmanager
def _sahte_depo():
    """kume.vakalar -> sahte LEU oksit kumesi (depodaki kume bu AOA'yi tutamaz)."""
    from cekirdek.vv import kume
    asil = kume.vakalar
    kume.vakalar = lambda dosyalar=None, filtre=None: [
        v for v in _leu_oksit_kume() if kume._uyar(v, filtre)]
    try:
        yield
    finally:
        kume.vakalar = asil


def test_aoa_filtresi():
    print("\n[VB1] AOA filtresi: tur + bicim + tayf (+ zenginlik sinifi)")
    from cekirdek.vv import kume
    kontrol("tayf yok -> None", kume.aoa_filtresi({"bolunebilir": "U-235"}) is None)
    kontrol("bos -> None", kume.aoa_filtresi({}) is None)
    f = kume.aoa_filtresi({"bolunebilir": "U-235", "fiziksel_bicim": "metal",
                           "tayf": "hizli", "zenginlik": 93.0})
    kontrol("filtre -> U-235 metal hizli HEU", f == {
        "bolunebilir": "U-235", "fiziksel_bicim": "metal", "tayf": "hizli",
        "zenginlik": ("aralik", 60.0, 100.0)}, "-> %r" % f)
    hizli = kume.vakalar(filtre=f)
    kontrol("alt kume yalniz uyan vakalar", hizli and all(
        v.parametreler.get("tayf") == "hizli" and v.parametreler.get("fiziksel_bicim")
        == "metal" and v.parametreler.get("bolunebilir") == "U-235" for v in hizli),
        "-> %d" % len(hizli))


def test_uygulama_ozeti():
    print("\n[VB2] uygulama_ozeti: alt kume -> USL ya da durust 'USL yok'")
    from cekirdek.vv import kume
    spec = _spec()
    vv, uyg = kume.uygulama_ozeti(spec, FIXTURE)
    kontrol("EALF yok -> tayf bilinmiyor, USL None", vv.usl is None and "tayf" not in uyg,
            "-> %r" % (uyg,))
    kontrol("neden: bu uygulama icin USL yok + EALF onerisi",
            "bu uygulama için USL yok" in vv.usl_neden and "EALF" in vv.usl_neden,
            "-> %s" % vv.usl_neden)
    vv, uyg = kume.uygulama_ozeti(spec, FIXTURE, uygulama={"tayf": "termal"},
                                  vlar=_leu_oksit_kume())
    kontrol("termal LEU oksit: uyan alt kume n = 12", vv.n == 12, "-> %d" % vv.n)
    kontrol("uyan alt kume n >= 10 -> USL hesaplandi", vv.usl is not None and vv.usl < 1.0,
            "-> %r (%s)" % (vv.usl, vv.usl_neden))
    kontrol("uygulama birlesti (spec + verilen)", uyg.get("tayf") == "termal"
            and uyg.get("bolunebilir") == "U-235")
    vv, _u = kume.uygulama_ozeti(spec, FIXTURE, uygulama={"tayf": "termal"})
    kontrol("depodaki kume (v3 Y11: LEU oksit termal n >= 10) -> USL, alt kume oksit",
            vv.usl is not None and vv.n >= 10 and "oksit" in vv.alt_kume,
            "-> n %d, %r (%s)" % (vv.n, vv.usl, vv.usl_neden))
    kontrol("girdi spec degismedi", spec == _spec())


def test_rapor_uygunluk_vv_gecer():
    print("\n[VB3] rapor_uygunluk.denetle/ek_verisi: B'de V&V ozeti denetle()'ye gecer")
    from cekirdek import rapor_uygunluk as ru
    spec = _spec()
    b, hata = ru.denetle(spec, FIXTURE, ("B",))
    k6 = _k6(b)
    kontrol("hata yok", not hata, "-> %s" % hata)
    kontrol("K6: 'V&V kümesi yok' DEGIL, AOA nedeni", k6 and "bu uygulama için USL yok"
            in k6[0].mesaj and "kümesi yok" not in k6[0].mesaj, "-> %s" % k6[0].mesaj)
    kontrol("K8 V&V ile degerlendirildi", any(
        x.kural == "K8" and x.durum == "karsilandi" for x in b))
    with _gecici_kosu({"tayf": "termal"}) as dizin, _sahte_depo():
        b, _h = ru.denetle(spec, dizin, ("B",))
        k6 = _k6(b)
        kontrol("tayf verilince K6 USL ile karsilastirdi", k6 and "USL =" in k6[0].mesaj,
                "-> %s" % (k6[0].mesaj if k6 else None))
        ek = ru.ek_verisi(spec, dizin, ("A", "B"))
        kontrol("ekte USL notu yok (USL var)", ek["usl_notu"] == "", "-> %s" % ek["usl_notu"])
    ek = ru.ek_verisi(spec, FIXTURE, ("A", "B"))
    kontrol("ekte USL notu: AOA nedeni", "bu uygulama için USL yok" in ek["usl_notu"],
            "-> %s" % ek["usl_notu"])
    b, _h = ru.denetle(spec, FIXTURE, ("A",))
    kontrol("B secili degilse K6 yok", not _k6(b))


def _cli(argv):
    from cekirdek import giris
    cikti, hata = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(hata):
        kod = giris.kosu(argv)
    return kod, cikti.getvalue(), hata.getvalue()


def test_cli_vv():
    print("\n[VB4] CLI uygunluk --profil B: V&V ozeti ve uygulama gecer")
    kod, cikti, _h = _cli(["uygunluk", FIXTURE, "--profil", "A,B"])
    kontrol("cikis 0", kod == 0, "-> %r" % kod)
    kontrol("K6 AOA nedeni basildi", "bu uygulama için USL yok" in cikti, "-> %s" % cikti[-800:])
    with _gecici_kosu({"tayf": "termal"}) as dizin, _sahte_depo():
        kod, cikti, _h = _cli(["uygunluk", dizin, "--profil", "B"])
        kontrol("tayf verilince K6 'USL =' basildi", "USL =" in cikti, "-> %s" % cikti[-800:])
        kontrol("USL notu basilmadi", "USL hesaplanamadı:" not in cikti)


def test_panel_ealf_onerisi():
    print("\n[VB5] panel: B secili + EALF tally'si yok -> oneri; onayla eklenir")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.uygunluk_paneli import UygunlukPaneli
    from cekirdek.vv import aoa
    p = UygunlukPaneli()
    gelen = []
    p.tally_eklensin.connect(gelen.append)
    spec = _spec()
    p.profilleri_ayarla(("A",))
    p.denetle(spec, FIXTURE)
    kontrol("B yok -> oneri gizli", p.d_ealf.isHidden())
    p.profilleri_ayarla(("A", "B"))
    p.denetle(spec, FIXTURE)
    kontrol("B var, tally yok -> oneri gorunur", not p.d_ealf.isHidden())
    kontrol("K6 USL nedeni panelde", any(
        "bu uygulama için USL yok" in p.liste.item(i).text() for i in range(p.liste.count())))
    p._onay_al = lambda *_a: False
    p.d_ealf.click()
    kontrol("onay yok -> eklenmez", not gelen)
    p._onay_al = lambda *_a: True
    p.d_ealf.click()
    kontrol("onay -> EALF tally'si sinyali", len(gelen) == 1
            and gelen[0]["ad"] == aoa.EALF_TALLY, "-> %r" % [g.get("ad") for g in gelen])
    spec2 = dict(spec, tallyler=list(spec.get("tallyler") or []) + [aoa.ealf_tally_tanimi()])
    p.denetle(spec2, FIXTURE)
    kontrol("tally varsa oneri gizli", p.d_ealf.isHidden())


def test_calistir_sayfasi_ealf_ekler():
    print("\n[VB5b] Calistir sayfasi: oneri onaylaninca spec'e EALF tally'si eklenir")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_calistir import CalistirSekmesi
    from cekirdek import sema
    from cekirdek.vv import aoa
    w = CalistirSekmesi()
    spec = sema.tamamla(_spec())
    w.spec_ayarla(spec)
    olaylar = []
    w.degisti.connect(olaylar.append)
    w.uygunluk.tally_eklensin.emit(aoa.ealf_tally_tanimi())
    adlar = [t.get("ad") for t in w.spec.get("tallyler") or []]
    kontrol("spec'e eklendi", adlar.count(aoa.EALF_TALLY) == 1, "-> %s" % adlar)
    kontrol("degisti yayildi", bool(olaylar))
    w.uygunluk.tally_eklensin.emit(aoa.ealf_tally_tanimi())
    adlar = [t.get("ad") for t in w.spec.get("tallyler") or []]
    kontrol("ikinci kez eklenmez", adlar.count(aoa.EALF_TALLY) == 1, "-> %s" % adlar)


HIZLI = [test_aoa_filtresi, test_uygulama_ozeti, test_rapor_uygunluk_vv_gecer, test_cli_vv,
         test_panel_ealf_onerisi, test_calistir_sayfasi_ealf_ekler]
YAVAS = []
