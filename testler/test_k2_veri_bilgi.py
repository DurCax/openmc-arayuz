# -*- coding: utf-8 -*-
"""
 test_k2_veri_bilgi.py  --  v3 K2: secilen kutuphane klasorunun denetimi
                            (veri_bilgi.klasor_denetle) ve gereksinim ozeti
                            (veri_bilgi.gereksinimler)

 Sahte kutuphane: cross_sections.xml + h5py ile yazilan, yalniz sicaklik
 gruplarini iceren kucuk HDF5 dosyalari (gercek veri gerekmez).
"""

import os
import subprocess
import tempfile

from testler.ortak_test import kontrol


def _h5(yol, ad, sicakliklar, tur="neutron"):
    import h5py
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with h5py.File(yol, "w") as f:
        g = f.create_group(ad)
        alt = g.create_group("energy" if tur == "neutron" else "kTs")
        for t in sicakliklar:
            alt.create_dataset("%dK" % t, data=[1.0e-5, 2.0e7])


def _kutuphane(dizin, eksik=False):
    """U235 + H1 notron, c_H_in_H2O termal, bir foton kaydi; eksik=True ise
    H1.h5 yazilmaz (dosyasi olmayan kayit)."""
    _h5(os.path.join(dizin, "neutron", "U235.h5"), "U235", (294, 600, 900))
    if not eksik:
        _h5(os.path.join(dizin, "neutron", "H1.h5"), "H1", (250, 294, 2500))
    _h5(os.path.join(dizin, "thermal", "c_H_in_H2O.h5"), "c_H_in_H2O", (294, 800), "thermal")
    os.makedirs(os.path.join(dizin, "photon"), exist_ok=True)
    open(os.path.join(dizin, "photon", "U.h5"), "w").close()
    xml = os.path.join(dizin, "cross_sections.xml")
    with open(xml, "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0'?>\n<cross_sections>\n"
                "  <library materials=\"U235\" path=\"neutron/U235.h5\" type=\"neutron\"/>\n"
                "  <library materials=\"H1\" path=\"neutron/H1.h5\" type=\"neutron\"/>\n"
                "  <library materials=\"c_H_in_H2O\" path=\"thermal/c_H_in_H2O.h5\" "
                "type=\"thermal\"/>\n"
                "  <library materials=\"U\" path=\"photon/U.h5\" type=\"photon\"/>\n"
                "</cross_sections>\n")
    return xml


def test_klasor_denetle_gecerli_kutuphane():
    print("\n[K2-B1] gecerli klasor: nuklid / termal / foton sayilari, sicakliklar, S(a,b)")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        # Arrange
        xml = _kutuphane(os.path.join(kok, "endfb"))
        # Act: ust klasor verilir, cross_sections.xml bir alt dizinde bulunur
        d = veri_bilgi.klasor_denetle(kok)
        # Assert
        kontrol("tamam", d.tamam, repr(d.hatalar))
        kontrol("xml bulundu", d.xml == xml, d.xml)
        kontrol("2 notron, 1 termal, 1 foton", (d.notron, d.termal, d.foton) == (2, 1, 1))
        kontrol("S(a,b) adi", d.sab == ("c_H_in_H2O",), repr(d.sab))
        sic = dict(d.sicakliklar)
        kontrol("U235 araligi", sic.get("U235") == (294, 900), repr(d.sicakliklar))
        kontrol("su S(a,b) araligi", sic.get("c_H_in_H2O") == (294, 800))
        kontrol("eksik dosya yok", d.eksik == ())
        kontrol("dogrudan xml de kabul", veri_bilgi.klasor_denetle(xml).tamam)


def test_klasor_denetle_hatalar():
    print("\n[K2-B2] eksik dosya, bozuk XML, cross_sections.xml yok, bos kutuphane")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        _kutuphane(os.path.join(kok, "a"), eksik=True)
        d = veri_bilgi.klasor_denetle(os.path.join(kok, "a"))
        kontrol("eksik dosya -> tamam degil", not d.tamam and d.eksik == ("neutron/H1.h5",),
                repr(d.eksik))
        kontrol("eksik icin hata metni", any("H1.h5" in h for h in d.hatalar), repr(d.hatalar))
        bos = os.path.join(kok, "bos")
        os.makedirs(bos)
        d = veri_bilgi.klasor_denetle(bos)
        kontrol("xml yok", not d.tamam and d.xml is None and d.hatalar, repr(d.hatalar))
        bozuk = os.path.join(kok, "bozuk")
        os.makedirs(bozuk)
        with open(os.path.join(bozuk, "cross_sections.xml"), "w") as f:
            f.write("<cross_sections><library")
        d = veri_bilgi.klasor_denetle(bozuk)
        kontrol("bozuk XML", not d.tamam and d.notron == 0 and d.hatalar, repr(d.hatalar))
        notronsuz = os.path.join(kok, "notronsuz")
        os.makedirs(notronsuz)
        with open(os.path.join(notronsuz, "cross_sections.xml"), "w") as f:
            f.write("<cross_sections></cross_sections>")
        kontrol("notron kaydi yok", not veri_bilgi.klasor_denetle(notronsuz).tamam)
        kontrol("olmayan yol", not veri_bilgi.klasor_denetle(os.path.join(kok, "yok")).tamam)


class _Calistirici:
    """subprocess.run yerine: openmc --version ciktisi verir."""

    def __init__(self, cikti="OpenMC version 0.16.0\nCommit hash: x\n", kod=0, hata=None):
        self.cikti, self.kod, self.hata, self.cagrilar = cikti, kod, hata, []

    def __call__(self, komut, **kw):
        self.cagrilar.append((komut, kw))
        if self.hata:
            raise self.hata
        return subprocess.CompletedProcess(komut, self.kod, stdout=self.cikti, stderr="")


def _sahte_openmc(dizin):
    yol = os.path.join(dizin, "bin", "openmc")
    os.makedirs(os.path.dirname(yol))
    with open(yol, "w") as f:
        f.write("#!/bin/sh\n")
    os.chmod(yol, 0o755)
    return yol


def test_gereksinimler_tam():
    print("\n[K2-B3] gereksinimler: openmc ikilisi + surum, Python API, HDF5, kutuphane, zincir")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        exe = _sahte_openmc(kok)
        xml = _kutuphane(os.path.join(kok, "nucdata", "endfb"))
        zdir = os.path.join(kok, "nucdata", "chain")
        os.makedirs(zdir)
        with open(os.path.join(zdir, "chain_endfb80_thermal.xml"), "w") as f:
            f.write("<depletion_chain>\n</depletion_chain>\n")
        ortam = {"HOME": kok, "PATH": os.path.dirname(exe), "XDG_CONFIG_HOME": kok + "/c",
                 "XDG_DATA_HOME": kok + "/d"}
        calistir = _Calistirici()
        g = {x.anahtar: x for x in veri_bilgi.gereksinimler(ortam, calistir=calistir,
                                                            python="/yok/python")}
        kontrol("bes satir", set(g) == {"openmc", "python_api", "hdf5", "kutuphane", "zincir"},
                repr(sorted(g)))
        kontrol("openmc tamam + surum", g["openmc"].durum == "tamam"
                and "0.16.0" in g["openmc"].deger, repr(g["openmc"]))
        kontrol("ikili --version ile, zaman asimli",
                calistir.cagrilar[0][0] == [exe, "--version"]
                and calistir.cagrilar[0][1].get("timeout"), repr(calistir.cagrilar))
        kontrol("kutuphane tamam", g["kutuphane"].durum == "tamam" and xml in g["kutuphane"].deger)
        kontrol("zincir tamam", g["zincir"].durum == "tamam", repr(g["zincir"]))
        kontrol("hdf5 surumu", g["hdf5"].durum == "tamam" and g["hdf5"].deger)


def test_gereksinimler_eksik():
    print("\n[K2-B4] openmc yok / --version hata verir / veri yok -> eksik + oneri")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        ortam = {"HOME": kok, "PATH": "", "XDG_CONFIG_HOME": kok + "/c",
                 "XDG_DATA_HOME": kok + "/d"}
        g = {x.anahtar: x for x in veri_bilgi.gereksinimler(ortam, calistir=_Calistirici(),
                                                            python="/yok/python")}
        kontrol("openmc eksik", g["openmc"].durum == "eksik" and g["openmc"].oneri)
        kontrol("kutuphane eksik", g["kutuphane"].durum == "eksik" and g["kutuphane"].oneri)
        kontrol("zincir yalniz uyari (tukenme icin)", g["zincir"].durum == "uyari")
        exe = _sahte_openmc(kok)
        ortam["PATH"] = os.path.dirname(exe)
        hatali = _Calistirici(hata=subprocess.TimeoutExpired("openmc", 10))
        g = {x.anahtar: x for x in veri_bilgi.gereksinimler(ortam, calistir=hatali,
                                                            python="/yok/python")}
        kontrol("zaman asimi -> uyari", g["openmc"].durum == "uyari", repr(g["openmc"]))


def test_klasorde_birden_cok_kutuphane():
    print("\n[K2-B6] ust klasorde birden cok kutuphane: VIII.0 varsa o, yoksa secim istenir")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        _kutuphane(os.path.join(kok, "endfb-vii.1-hdf5"))
        _kutuphane(os.path.join(kok, "jeff-3.3-hdf5"))
        d = veri_bilgi.klasor_denetle(kok)
        kontrol("otomatik secilmez", not d.tamam and d.xml is None
                and any("jeff-3.3-hdf5" in h for h in d.hatalar), repr(d.hatalar))
        xml = _kutuphane(os.path.join(kok, "endfb-viii.0-hdf5"))
        kontrol("varsayilan secilir", veri_bilgi.klasor_denetle(kok).xml == xml)


def test_zincir_kutuphane_uyumu():
    print("\n[K2-B7] ENDF/B-VIII.0 zinciri baska kutuphaneyle -> uyari")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        _kutuphane(os.path.join(kok, "nucdata", "jendl-5-hdf5"))
        zdir = os.path.join(kok, "nucdata", "chain")
        os.makedirs(zdir)
        with open(os.path.join(zdir, "chain_endfb80_thermal.xml"), "w") as f:
            f.write("<depletion_chain>\n</depletion_chain>\n")
        ortam = {"HOME": kok, "PATH": "", "XDG_CONFIG_HOME": kok + "/c",
                 "XDG_DATA_HOME": kok + "/d"}
        g = {x.anahtar: x for x in veri_bilgi.gereksinimler(ortam, calistir=_Calistirici(),
                                                            python="/yok/python")}
        kontrol("uyumsuz zincir uyarisi", g["zincir"].durum == "uyari"
                and "ENDF/B-VIII.0" in g["zincir"].oneri, repr(g["zincir"]))
        kontrol("kutuphane kimligi dizin adindan",
                veri_bilgi.kutuphane_kimligi(os.path.join(kok, "nucdata", "jendl-5-hdf5",
                                                          "cross_sections.xml")) == "jendl-5")


def test_surum_onbellegi():
    print("\n[K2-B8] openmc --version sonucu onbellekte; Yenile (tazele) yeniden calistirir")
    from cekirdek import veri_bilgi
    with tempfile.TemporaryDirectory() as kok:
        exe = _sahte_openmc(kok)
        ortam = {"HOME": kok, "PATH": os.path.dirname(exe), "XDG_CONFIG_HOME": kok + "/c",
                 "XDG_DATA_HOME": kok + "/d"}
        c = _Calistirici()
        veri_bilgi.gereksinimler(ortam, calistir=c, python="/yok/python", tazele=True)
        veri_bilgi.gereksinimler(ortam, calistir=c, python="/yok/python")
        kontrol("bir kez calisti", len(c.cagrilar) == 1, repr(len(c.cagrilar)))
        veri_bilgi.gereksinimler(ortam, calistir=c, python="/yok/python", tazele=True)
        kontrol("tazele yeniden calistirir", len(c.cagrilar) == 2)


def test_onbellek_temizle():
    print("\n[K2-B5] secim degisince sicaklik/yol onbellegi bosaltilir")
    from cekirdek import veri_bilgi
    veri_bilgi._YOL_ONBELLEK[("neutron", "X")] = "/x"
    veri_bilgi._NUKLID_ONBELLEK["X"] = (1, 2)
    veri_bilgi.onbellek_temizle()
    kontrol("bos", not veri_bilgi._YOL_ONBELLEK and "X" not in veri_bilgi._NUKLID_ONBELLEK)


HIZLI = [test_klasor_denetle_gecerli_kutuphane, test_klasor_denetle_hatalar,
         test_gereksinimler_tam, test_gereksinimler_eksik, test_onbellek_temizle,
         test_klasorde_birden_cok_kutuphane, test_zincir_kutuphane_uyumu, test_surum_onbellegi]
YAVAS = []
