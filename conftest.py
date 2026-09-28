# -*- coding: utf-8 -*-
"""
conftest.py -- eski test sozlesmesi (testler/ortak_test.py) icin pytest koprusu.

  pytest -m hizli -q                 # eski --hizli ile ayni islevler
  pytest -m hizli -n auto            # pytest-xdist ile paralel
  pytest -m yavas                    # Monte Carlo testleri (gecici dizin = tmp_path)
  pytest -m "hizli and not veri"     # CI: nukleer veri gerektirmeyenler

NASIL CALISIR
  - testler/test_*.py modullerinin HIZLI ve YAVAS listelerindeki her islev bir
    pytest ogesi olur (isaret: hizli / yavas). Listesi olmayan modulde
    (bugun test_regresyon) main() govdesindeki dogrudan test_* cagrilari
    okunur: `if not hizli:` blogunun icindekiler YAVAS, digerleri HIZLI.
  - kontrol() KALDI yazinca test dururmaz (eski sozlesme); bu kopru her testin
    oncesi/sonrasi _kaldi listesinin farkina bakar ve yeni KALDI varsa testi
    basarisiz sayar.
  - YAVAS islevlerinin `gecici` argumani pytest'in tmp_path'idir.
  - pytest'in kendi test_* kesfi bu dosyalari ikinci kez toplamasin diye
    pytest_pycollect_makemodule kancasi Module yerine OrtakTestDosyasi verir.
  - `veri` isareti: nukleer veri (OPENMC_CROSS_SECTIONS ya da tukenme zinciri)
    gerektiren testler. Otomatik anlasilamadigi icin VERI_GEREKTIREN listesinde
    tutulur (CI taklidiyle olculdu). Veri yoksa bu testler ATLANIR: veri
    olmadan Model.plot/openmc.lib sureci C++ tarafinda sonlandirir, yani
    pytest'in kendisi de olurdu.
"""

import ast
import importlib
import os

import pytest

# ortak_test ice aktarilinca ayar (XDG_CONFIG_HOME) ve log (XDG_STATE_HOME)
# gecici dizine yonlenir -- PySide6'dan ONCE olmali.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from testler import ortak_test  # noqa: E402

# Modul:islev -> nukleer veri gerektirir. YAVAS listesindekilerin hepsi
# (Monte Carlo) ayrica otomatik isaretlenir. Olcum (28.09.2026): veri yokken
# (OPENMC_CROSS_SECTIONS/OPENMC_CHAIN_FILE bos, ~/nucdata yok) hizli suit.
# (*) = veri olmadan openmc.lib sureci SONLANDIRIR (Model.plot ya da onizleme
#       widget'i tesir kesitlerini yukler); digerleri KALDI/istisna verir.
# Test tasinirsa modul adi burada guncellenir; bilinmeyen ad zararsizdir
# ama test_veri_listesi_gecerli uyarir.
VERI_GEREKTIREN = frozenset({
    "test_nuklid_secici:test_dogrulama_yazim_hatasi",
    "test_nuklid_secici:test_sonuc_oku_bulunamayan",
    "test_dogrulama:test_dogrulama_negatif",
    "test_dogrulama:test_dogrulama_temiz",
    "test_guc:test_guc_dogrulama",
    "test_kaynak:test_kaynak_dogrulama",
    "test_kontrol_cubugu:test_kontrol_cubugu_dogrulama",
    "test_kosu_yardimcilari:test_kuresel_kor",
    "test_tambur:test_tambur_kor",
    "test_tukenme_temel:test_tukenme_dogrulama",
    "test_tukenme_temel:test_tukenme_hacimleri",
    "test_kosu_yardimcilari:test_veri_sicaklik_araligi",
    "test_tukenme_temel:test_zincir_butunlugu",
})

# Tesir kesitine EK OLARAK tukenme zinciri isteyen testler: tesir kesiti var
# ama zincir yoksa (OPENMC_CHAIN_FILE / ~/nucdata/chain) atlanir; aksi halde
# FileNotFoundError ile KALDI gorunurdu.
ZINCIR_GEREKTIREN = frozenset({
    "test_nuklid_secici:test_zincir_nuklidleri",
    "test_nuklid_secici:test_dogrulama_yazim_hatasi",
    "test_nuklid_secici:test_sekme_onceki_sonuc_yeni_secim",
    "test_dogrulama:test_dogrulama_temiz",           # pwr_tukenme ornegi zinciri denetler
    "test_tukenme_temel:test_tukenme_dogrulama",
    "test_tukenme_temel:test_zincir_butunlugu",
    "test_tukenme_temel:test_tukenme_hacimleri",
})

_TEST_DIZINI = os.path.join(ortak_test.KOK, "testler")


def veri_var(ortam=None):
    """Tesir kesiti kutuphanesi erisilebilir mi (CI'da yok)."""
    ortam = os.environ if ortam is None else ortam
    yol = ortam.get("OPENMC_CROSS_SECTIONS", "")
    return bool(yol) and os.path.isfile(yol)


def zincir_var():
    """Tukenme zincir dosyalari (termal + hizli) erisilebilir mi."""
    from cekirdek import tukenme, veri_bilgi
    dizin = veri_bilgi.zincir_dizini()
    return all(os.path.isfile(os.path.join(dizin, f)) for f in tukenme.ZINCIRLER.values())


def _main_cagrilari(modul):
    """Listesi olmayan modulde main() icindeki test_* cagrilari:
    (hizli_adlari, yavas_adlari). `if not hizli:` blogu YAVAS sayilir."""
    with open(modul.__file__, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    main = next((d for d in agac.body
                 if isinstance(d, ast.FunctionDef) and d.name == "main"), None)
    if main is None:
        return [], []
    hizli, yavas = [], []

    def _cagri_adi(ifade):
        if (isinstance(ifade, ast.Expr) and isinstance(ifade.value, ast.Call)
                and isinstance(ifade.value.func, ast.Name)
                and ifade.value.func.id.startswith("test_")):
            return ifade.value.func.id
        return None

    def _yavas_blogu_mu(ifade):
        return (isinstance(ifade, ast.If) and isinstance(ifade.test, ast.UnaryOp)
                and isinstance(ifade.test.op, ast.Not)
                and isinstance(ifade.test.operand, ast.Name)
                and ifade.test.operand.id == "hizli")

    for ifade in main.body:
        if _cagri_adi(ifade):
            hizli.append(_cagri_adi(ifade))
        elif _yavas_blogu_mu(ifade):
            for alt in ast.walk(ifade):
                if isinstance(alt, ast.stmt) and _cagri_adi(alt):
                    yavas.append(_cagri_adi(alt))
    return hizli, yavas


def test_listeleri(modul):
    """(HIZLI islevleri, YAVAS islevleri) -- eski calistiricinin kostugu sirayla."""
    if hasattr(modul, "HIZLI") or hasattr(modul, "YAVAS"):
        return list(getattr(modul, "HIZLI", [])), list(getattr(modul, "YAVAS", []))
    hizli, yavas = _main_cagrilari(modul)
    return ([getattr(modul, a) for a in hizli if hasattr(modul, a)],
            [getattr(modul, a) for a in yavas if hasattr(modul, a)])


class OrtakTestDosyasi(pytest.File):
    """testler/test_*.py: HIZLI/YAVAS listelerini pytest ogelerine cevirir."""

    def collect(self):
        ad = os.path.splitext(self.path.name)[0]
        # Eski calistiriciyla AYNI modul nesnesi (testler.<ad>) kullanilir.
        modul = importlib.import_module("testler." + ad)
        hizli, yavas = test_listeleri(modul)
        for isaret, islevler in (("hizli", hizli), ("yavas", yavas)):
            for fn in islevler:
                oge = pytest.Function.from_parent(self, name=fn.__name__, callobj=fn)
                oge.add_marker(isaret)
                if isaret == "yavas" or "%s:%s" % (ad, fn.__name__) in VERI_GEREKTIREN:
                    oge.add_marker("veri")
                if "%s:%s" % (ad, fn.__name__) in ZINCIR_GEREKTIREN:
                    oge.add_marker("zincir")
                oge.ortak_test = True
                yield oge


def pytest_pycollect_makemodule(module_path, parent):
    """pytest'in python eklentisi testler/test_*.py icin Module yerine bu
    toplayiciyi kullanir; boylece dosya tek kez ve yalnizca listelerle toplanir
    (yardimci test_* islevleri ya da `gecici` alan YAVAS islevleri pytest'in
    kendi kesfine dusmez)."""
    if str(module_path.parent) == _TEST_DIZINI:
        return OrtakTestDosyasi.from_parent(parent, path=module_path)
    return None


@pytest.fixture
def gecici(tmp_path):
    """YAVAS islevlerinin gecici dizin argumani (eski calistiricida mkdtemp)."""
    return str(tmp_path)


def pytest_collection_modifyitems(config, items):
    veri, zincir = veri_var(), zincir_var()
    atla_veri = pytest.mark.skip(reason="nukleer veri yok (OPENMC_CROSS_SECTIONS)")
    atla_zincir = pytest.mark.skip(reason="tukenme zinciri yok (OPENMC_CHAIN_FILE)")
    for oge in items:
        if not veri and oge.get_closest_marker("veri"):
            oge.add_marker(atla_veri)
        elif not zincir and oge.get_closest_marker("zincir"):
            oge.add_marker(atla_zincir)


@pytest.fixture(autouse=True)
def _verisiz_openmc_lib_korumasi(monkeypatch):
    """Veri yokken openmc.lib.init sureci C++ tarafinda SONLANDIRIR ve xdist
    iscisiyle birlikte baska testlerin sonucu da kaybolur. "veri" isareti
    unutulmus bir test bunun yerine acik bir mesajla KALIR."""
    if veri_var():
        yield
        return
    try:
        import openmc.lib
    except ImportError:          # openmc.lib yuklenemiyorsa korunacak bir sey yok
        yield
        return

    def _engelle(*_a, **_k):
        pytest.fail("nukleer veri yokken openmc.lib.init cagrildi: bu test "
                    "conftest.py VERI_GEREKTIREN listesine eklenmeli", pytrace=False)
    monkeypatch.setattr(openmc.lib, "init", _engelle)
    yield


@pytest.hookimpl(wrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    """kontrol() KALDI sayacini pytest basarisizligina cevirir."""
    if not getattr(pyfuncitem, "ortak_test", False):
        return (yield)
    once = len(ortak_test._kaldi)
    sonuc = yield
    yeni = ortak_test._kaldi[once:]
    if yeni:
        pytest.fail("%d kontrol KALDI:\n  - %s" % (len(yeni), "\n  - ".join(yeni)),
                    pytrace=False)
    return sonuc
