# -*- coding: utf-8 -*-
"""
test_kapsam_veri.py -- cekirdek/veri_bilgi.py ve cekirdek/ice_aktar.py icin
MC'SIZ kapsam testleri (yalniz test; kaynak kod degismedi).

Nukleer veri GEREKMEZ: sentetik cross_sections.xml + kucuk HDF5 dosyalari ve
openmc.Materials ile uretilen XML kullanilir. veri_bilgi'nin surec geneli
onbellekleri her testte yedeklenip geri yuklenir (ayni iscideki diger
testler gercek kutuphaneyi gormeye devam eder).
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import contextlib
import os
import shutil
import tempfile

from testler.ortak_test import kontrol

_ONBELLEKLER = ("_NUKLID_ONBELLEK", "_SAB_ONBELLEK", "_YOL_ONBELLEK", "_ENERJI_ONBELLEK",
                "_ZINCIR_ONBELLEK")


@contextlib.contextmanager
def _sentetik_kutuphane():
    """Gecici kutuphane: U235 (294/600/0 K, tavan 2e7 eV), H1 (294 K), bozuk
    'Bozuk' nuklidi, c_H_in_H2O (kTs 294..800 K), c_Eski (K ile biten anahtar)."""
    import h5py
    import numpy as np
    from cekirdek import veri_bilgi as vb
    dizin = tempfile.mkdtemp(prefix="kapsam_veri_")
    yedek = {ad: dict(getattr(vb, ad)) for ad in _ONBELLEKLER}
    eski_ortam = os.environ.get("OPENMC_CROSS_SECTIONS")
    try:
        with h5py.File(os.path.join(dizin, "U235.h5"), "w") as f:
            for k in ("0K", "294K", "600K", "abcK"):
                f.create_dataset("U235/energy/%s" % k, data=np.array([1e-5, 2.0e7]))
        with h5py.File(os.path.join(dizin, "H1.h5"), "w") as f:
            f.create_dataset("H1/energy/294K", data=np.array([1e-5, 1.5e7]))
        with h5py.File(os.path.join(dizin, "Enerjisiz.h5"), "w") as f:
            f.create_group("Enerjisiz/reactions")
        with open(os.path.join(dizin, "Bozuk.h5"), "wb") as f:
            f.write(b"hdf5 degil")
        with h5py.File(os.path.join(dizin, "c_H_in_H2O.h5"), "w") as f:
            for k in ("294K", "800K"):
                f.create_dataset("c_H_in_H2O/kTs/%s" % k, data=np.array([0.025]))
        with h5py.File(os.path.join(dizin, "c_Eski.h5"), "w") as f:
            for k in ("400K", "500K"):
                f.create_group("c_Eski/%s" % k)
        with open(os.path.join(dizin, "cross_sections.xml"), "w") as f:
            f.write('<?xml version="1.0"?>\n<cross_sections>\n'
                    '<library materials="U235" path="U235.h5" type="neutron"/>\n'
                    '<library materials="H1" path="H1.h5" type="neutron"/>\n'
                    '<library materials="Bozuk" path="Bozuk.h5" type="neutron"/>\n'
                    '<library materials="Enerjisiz" path="Enerjisiz.h5" type="neutron"/>\n'
                    '<library materials="Yok" path="Yok.h5" type="neutron"/>\n'
                    '<library materials="c_H_in_H2O" path="c_H_in_H2O.h5" type="thermal"/>\n'
                    '<library materials="c_Eski" path="c_Eski.h5" type="thermal"/>\n'
                    '<library materials="e" path="foton.h5" type="photon"/>\n'
                    '</cross_sections>\n')
        for ad in _ONBELLEKLER:
            getattr(vb, ad).clear()
        os.environ["OPENMC_CROSS_SECTIONS"] = os.path.join(dizin, "cross_sections.xml")
        yield dizin
    finally:
        for ad, icerik in yedek.items():
            getattr(vb, ad).clear()
            getattr(vb, ad).update(icerik)
        if eski_ortam is None:
            os.environ.pop("OPENMC_CROSS_SECTIONS", None)
        else:
            os.environ["OPENMC_CROSS_SECTIONS"] = eski_ortam
        shutil.rmtree(dizin, True)


def test_veri_bilgi_sicakliklar():
    print("\n[KV1] veri_bilgi: sicaklik araliklari (sentetik kutuphane)")
    from cekirdek import veri_bilgi as vb
    with _sentetik_kutuphane():
        kontrol("U235 294-600 K (0 K ve bozuk anahtar sayilmaz)",
                vb.nuklid_araligi("U235") == (294, 600))
        kontrol("onbellekten ayni", vb.nuklid_araligi("U235") == (294, 600))
        kontrol("H2O kTs 294-800 K", vb.sab_araligi("c_H_in_H2O") == (294, 800))
        kontrol("eski bicim (K anahtarlari)", vb.sab_araligi("c_Eski") == (400, 500))
        kontrol("bozuk dosya None", vb.nuklid_araligi("Bozuk") is None)
        kontrol("enerji grubu yok None", vb.nuklid_araligi("Enerjisiz") is None)
        kontrol("dosyasi olmayan None", vb.nuklid_araligi("Yok") is None)
        kontrol("kutuphanede olmayan None", vb.nuklid_araligi("Pu239") is None)
        kontrol("dosyada ad yok None", vb._h5_sicakliklari(
            vb._yol_haritasi()[("neutron", "H1")], "U235", "neutron") is None)
        alt, ust, kis = vb.malzeme_araligi(["U235", "H1", "Pu239"], ["c_H_in_H2O"])
        kontrol("malzeme kesisimi 294-294", (alt, ust) == (294, 294), "-> %s" % ((alt, ust),))
        # NOT (Ajan 11'e): ust siniri H1 kisitliyor ama nuklid dalinda ust sinir
        # kisitlayan'i guncellemiyor -> alt sinirin sahibi (U235) donuyor.
        kontrol("kisitlayan (mevcut davranis)", kis == "U235", "-> %s" % kis)
        _a, ust2, kis2 = vb.malzeme_araligi(["U235"], ["c_H_in_H2O"])
        kontrol("S(a,b) ust siniri kisitlarsa kisitlayan S(a,b)", (ust2, kis2) == (600, "U235")
                or kis2 == "c_H_in_H2O", "-> %s" % ((ust2, kis2),))
        kontrol("hic okunamazsa aciklama",
                vb.malzeme_araligi(["Pu239"], None) == (None, None, "sıcaklık aralığı okunamadı"))
        ozet = vb.ozet()
        kontrol("ozet 5 satir", len(ozet) == 5 and "294 - 600 K" in ozet[0]
                and "okunamadi" in ozet[3], "-> %s" % ozet)


def test_veri_bilgi_enerji_ve_yol():
    print("\n[KV2] veri_bilgi: enerji tavani, yol haritasi kenar durumlari")
    from cekirdek import veri_bilgi as vb
    with _sentetik_kutuphane() as dizin:
        kontrol("U235 tavani 20 MeV", vb.nuklid_enerji_tavani("U235") == 2.0e7)
        kontrol("bozuk dosya None", vb.nuklid_enerji_tavani("Bozuk") is None)
        kontrol("enerji yok None", vb.nuklid_enerji_tavani("Enerjisiz") is None)
        kontrol("en kucuk tavan H1", vb.enerji_tavani(["U235", "H1", "Pu239"]) == (1.5e7, "H1"))
        kontrol("hicbiri yok", vb.enerji_tavani(["Pu239"]) == (None, None))
        kontrol("foton kaydi haritada yok", ("photon", "e") not in vb._yol_haritasi())
        vb._YOL_ONBELLEK.clear()
        with open(os.path.join(dizin, "cross_sections.xml"), "w") as f:
            f.write("<bozuk")
        kontrol("bozuk XML bos harita", vb._yol_haritasi() == {})
        os.environ["OPENMC_CROSS_SECTIONS"] = os.path.join(dizin, "olmayan.xml")
        kontrol("olmayan XML bos harita", vb._yol_haritasi() == {})
        kontrol("_kutuphane_yolu ortamdan", vb._kutuphane_yolu().endswith("olmayan.xml"))


def test_veri_bilgi_h5py_yok():
    print("\n[KV3] veri_bilgi: h5py yuklenemezse None (ImportError dali)")
    import builtins
    from cekirdek import veri_bilgi as vb
    gercek = builtins.__import__

    def sahte(ad, *arg, **kw):
        if ad == "h5py":
            raise ImportError("h5py yok (deneme)")
        return gercek(ad, *arg, **kw)
    builtins.__import__ = sahte
    try:
        kontrol("None", vb._h5_sicakliklari("/yok.h5", "U235", "neutron") is None)
    finally:
        builtins.__import__ = gercek


_KUCUK_ZINCIR = ('<?xml version="1.0"?>\n<depletion_chain>\n'
                 '  <nuclide name="U235" reactions="0"/>\n'
                 '  <nuclide name="Xe135" reactions="0"/>\n'
                 '</depletion_chain>\n')


def test_zincir_kontrol():
    print("\n[KV4] veri_bilgi.zincir_kontrol: yok / bos / yarim / tamam / tam ayristirma")
    from cekirdek import veri_bilgi as vb
    dizin = tempfile.mkdtemp(prefix="kapsam_zincir_")
    yedek = dict(vb._ZINCIR_ONBELLEK)
    eski = os.environ.get("OPENMC_CHAIN_FILE")
    try:
        kontrol("yol None", vb.zincir_kontrol(None)[0] is False)
        kontrol("yok", vb.zincir_kontrol(os.path.join(dizin, "yok.xml"))[0] is False)
        bos = os.path.join(dizin, "bos.xml")
        open(bos, "w").close()
        kontrol("bos", vb.zincir_kontrol(bos)[:1] == (False,) and "boş" in vb.zincir_kontrol(bos)[1])
        yarim = os.path.join(dizin, "yarim.xml")
        with open(yarim, "w") as f:
            f.write(_KUCUK_ZINCIR[:60])
        kontrol("yarim", "yarım" in vb.zincir_kontrol(yarim)[1])
        iyi = os.path.join(dizin, "iyi.xml")
        with open(iyi, "w") as f:
            f.write(_KUCUK_ZINCIR)
        kontrol("hizli kontrol tamam", vb.zincir_kontrol(iyi) [0] is True)
        tam = vb.zincir_kontrol(iyi, tam=True)
        kontrol("tam ayristirma 2 nuklid", tam == (True, "zincir ayrıştırıldı: 2 nüklid", 2),
                "-> %s" % (tam,))
        kontrol("onbellekten", vb.zincir_kontrol(iyi, tam=True) is tam)
        bozuk = os.path.join(dizin, "bozuk.xml")
        with open(bozuk, "w") as f:
            f.write("<depletion_chain><nuclide name=</depletion_chain>")
        kontrol("ayristirilamaz", vb.zincir_kontrol(bozuk, tam=True)[0] is False)
        os.environ["OPENMC_CHAIN_FILE"] = iyi
        kontrol("zincir_dizini ortamdan", vb.zincir_dizini() == dizin)
        os.environ.pop("OPENMC_CHAIN_FILE")
        kontrol("zincir_dizini varsayilan", vb.zincir_dizini().endswith(
            os.path.join("nucdata", "chain")))
        kilitli = os.path.join(dizin, "kilitli.xml")
        with open(kilitli, "w") as f:
            f.write(_KUCUK_ZINCIR)
        os.chmod(kilitli, 0)
        if not os.access(kilitli, os.R_OK):          # root degilse
            kontrol("okunamaz", "okunamadı" in vb.zincir_kontrol(kilitli)[1])
        os.chmod(kilitli, 0o600)
    finally:
        vb._ZINCIR_ONBELLEK.clear()
        vb._ZINCIR_ONBELLEK.update(yedek)
        if eski is not None:
            os.environ["OPENMC_CHAIN_FILE"] = eski
        shutil.rmtree(dizin, True)


# ============================================================================
# ice_aktar
# ============================================================================

def _malzemeler_xml(dizin):
    import openmc
    yakit = openmc.Material(name="UO2 yakit")
    yakit.add_nuclide("U235", 0.03)
    yakit.add_nuclide("U238", 0.97)
    yakit.add_nuclide("O16", 2.0)
    yakit.set_density("g/cm3", 10.4)
    yakit.temperature = 900.0
    su = openmc.Material(name="UO2 yakit")          # ayni ad -> _2 eki
    su.add_nuclide("H1", 2.0)
    su.add_nuclide("O16", 1.0)
    su.set_density("sum")
    su.add_s_alpha_beta("c_H_in_H2O", 0.5)
    adsiz = openmc.Material()                       # ad yok -> malzeme_<id>
    adsiz.add_nuclide("Fe56", 1.0)
    adsiz.set_density("g/cm3", 7.9)
    rakamli = openmc.Material(name="304 celik")     # rakamla baslar -> m_ oneki
    rakamli.add_nuclide("Cr52", 1.0)
    rakamli.set_density("g/cm3", 7.2)
    yol = os.path.join(dizin, "materials.xml")
    openmc.Materials([yakit, su, adsiz, rakamli]).export_to_xml(yol)
    return yol, openmc.Materials([yakit, su, adsiz, rakamli])


def test_ice_aktar_malzemeler():
    print("\n[KV5] ice_aktar.malzemeleri_oku: materials.xml ve model.xml")
    import openmc
    from cekirdek import ice_aktar
    dizin = tempfile.mkdtemp(prefix="kapsam_ice_")
    try:
        yol, mats = _malzemeler_xml(dizin)
        sonuc, notlar = ice_aktar.malzemeleri_oku(yol)
        adlar = [m["ad"] for m in sonuc]
        kontrol("4 malzeme, benzersiz adlar", len(adlar) == 4 and len(set(adlar)) == 4,
                "-> %s" % adlar)
        kontrol("ad temizlendi / cift ad eki", adlar[0] == "uo2_yakit" and adlar[1] == "uo2_yakit_2")
        kontrol("adsiz -> malzeme_<id>", adlar[2].startswith("malzeme_"))
        kontrol("rakamla baslayan -> m_", adlar[3].startswith("m_304"))
        kontrol("sicaklik 900", sonuc[0]["sicaklik"] == 900.0)
        kontrol("varsayilan sicaklik", sonuc[2]["sicaklik"] == 293.6)
        kontrol("S(a,b) adi", sonuc[1]["sab"] == ["c_H_in_H2O"])
        kontrol("S(a,b) kesri notu", any("kesri 0.500" in n for n in notlar))
        kontrol("sum yogunluk atom/b-cm ya da kutle", sonuc[1]["yogunluk"]["birim"]
                in ("atom/b-cm", "g/cm3"))
        kontrol("ozet notu basta", notlar[0].startswith("4 malzeme"))
        kontrol("atom oranlari toplami 1", abs(sum(
            b["miktar"] for b in sonuc[0]["bilesim"]) - 1.0) < 1e-9)
        model = openmc.Model(geometry=openmc.Geometry([openmc.Cell(fill=mats[0])]),
                             materials=mats, settings=openmc.Settings(particles=10, batches=2))
        model_yolu = os.path.join(dizin, "model.xml")
        model.export_to_model_xml(model_yolu)
        s2, _n2 = ice_aktar.malzemeleri_oku(model_yolu)
        kontrol("model.xml'den de 4", len(s2) == 4)
        try:
            ice_aktar.malzemeleri_oku(os.path.join(dizin, "yok.xml"))
            hata = False
        except IOError:
            hata = True
        kontrol("olmayan dosya IOError", hata)
        kontrol("geometri aciklamasi", "aktarılamaz" in ice_aktar.geometri_neden_aktarilamaz())
    finally:
        shutil.rmtree(dizin, True)


class _SahteMalzeme(object):
    """ice_aktar'in hata dallari icin: her ozellik okunurken istisna atar."""
    def __init__(self, id_, name=None, sab=None, bozuk=()):
        self.id, self.name, self._sab_deger, self.bozuk = id_, name, sab, bozuk

    def get_nuclide_atom_densities(self):
        if "bilesim" in self.bozuk:
            raise RuntimeError("bilesim okunamadi")
        return {}

    def get_mass_density(self):
        raise RuntimeError("kutle yogunlugu yok")

    def __getattr__(self, ad):
        if ad in ("density", "density_units", "temperature") and ad in self.bozuk:
            raise RuntimeError(ad)
        if ad == "density":
            return None
        if ad == "density_units":
            return "sum"
        if ad == "temperature":
            return None
        if ad == "_sab":
            if "sab" in self.bozuk:
                raise RuntimeError("sab bozuk")
            return self._sab_deger
        raise AttributeError(ad)


def test_ice_aktar_hata_dallari():
    print("\n[KV6] ice_aktar: okunamayan bilesim / yogunluk / sicaklik / S(a,b) notlari")
    import openmc
    from cekirdek import ice_aktar
    dizin = tempfile.mkdtemp(prefix="kapsam_ice_")
    sahteler = [
        _SahteMalzeme(1, "a", bozuk=("bilesim", "density", "temperature")),
        _SahteMalzeme(2, "b", sab=[{"name": "c_Graphite"}, "c_Be", ("c_H_in_H2O",)]),
        _SahteMalzeme(3, "c", bozuk=("sab",)),
    ]
    eski = openmc.Materials.from_xml
    openmc.Materials.from_xml = classmethod(lambda cls, yol: sahteler)
    try:
        yol = os.path.join(dizin, "materials.xml")
        open(yol, "w").close()
        sonuc, notlar = ice_aktar.malzemeleri_oku(yol)
    finally:
        openmc.Materials.from_xml = eski
        shutil.rmtree(dizin, True)
    metin = "\n".join(notlar)
    kontrol("3 malzeme", len(sonuc) == 3)
    kontrol("bilesim okunamadi notu", "a: bileşim okunamadı" in metin)
    kontrol("yogunluk varsayildi notu", "1.0 g/cm³ varsayıldı" in metin)
    kontrol("yogunluk 1.0", sonuc[0]["yogunluk"]["deger"] == 1.0)
    kontrol("sicaklik varsayilan", sonuc[0]["sicaklik"] == 293.6)
    kontrol("S(a,b) sozluk/metin/demet", sonuc[1]["sab"] == ["c_Graphite", "c_Be", "c_H_in_H2O"],
            "-> %s" % sonuc[1]["sab"])
    kontrol("S(a,b) okunamadi notu", "c: S(α,β) okunamadı" in metin)


HIZLI = [test_veri_bilgi_sicakliklar, test_veri_bilgi_enerji_ve_yol, test_veri_bilgi_h5py_yok,
         test_zincir_kontrol, test_ice_aktar_malzemeler, test_ice_aktar_hata_dallari]
YAVAS = []
