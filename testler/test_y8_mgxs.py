# -*- coding: utf-8 -*-
"""
 test_y8_mgxs.py  --  v3 Y8: grup sabiti uretimi (cekirdek/mgxs_uret.py)

 HIZLI: ayar dogrulama ve varsayilanlar, etkin tur kumesi (MG kutuphanesi
        icin zorunlular her zaman), bolge -> OpenMC domain turu, kurucu
        kancasi (tally eklenir, kullanici tally'si birlesmez), uretilen
        betigin AYNI tally'leri kurmasi, kapaliyken modelin degismemesi,
        xsdata adlari (HDF5 guvenli, tekil), dogrulama bulgulari.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import importlib.util
import os
import tempfile

from cekirdek import sema
from testler.ortak_test import kontrol, ORNEK


def _pin(**mgxs):
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    if mgxs is not None:
        ayar = {"var": True}
        ayar.update(mgxs)
        spec["ayarlar"]["mgxs"] = ayar
    return spec


def _betik_modeli(spec, dizin):
    """Betigi yukler. Betik kimlik sayaclarini sifirlamaz; ayni surecte once
    kurucu kostugu icin sayaclar burada sifirlanir (bagimsiz betik kosusu gibi)."""
    import openmc
    from cekirdek import kod_uret
    openmc.reset_auto_ids()
    yol = os.path.join(dizin, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    sm = importlib.util.spec_from_file_location("y8_betik_%d" % id(spec), yol)
    mod = importlib.util.module_from_spec(sm)
    sm.loader.exec_module(mod)
    return mod.model


def _tally_ozeti(model):
    ozet = []
    for t in model.tallies:
        filtreler = []
        for f in t.filters:
            bins = f.bins.tolist() if hasattr(f.bins, "tolist") else list(f.bins)
            filtreler.append((type(f).__name__, str(bins)))
        ozet.append((tuple(t.scores), tuple(t.nuclides), tuple(filtreler), t.estimator))
    return sorted(ozet)


def test_ayar_varsayilan_ve_dogrulama():
    print("\n[Y8-M1] ayar: varsayilanlar, bilinmeyen bolge/grup/tur ValueError")
    from cekirdek import mgxs_uret as mu
    # Arrange / Act
    a = mu.ayar(_pin())
    # Assert
    kontrol("varsayilan: malzeme, CASMO-2, P0", (a.bolge, a.grup_yapisi, a.duzeltme)
            == ("malzeme", "CASMO-2", "P0"), "-> %r" % (a,))
    kontrol("kapali spec -> var False", mu.ayar(sema.yukle(
        os.path.join(ORNEK, "pwr_pinhucre.json"))).var is False)
    hata = 0
    for ek in ({"bolge": "kure"}, {"grup_yapisi": "CASMO-3"}, {"turler": ["bilinmez"]},
               {"duzeltme": "P1"}):
        try:
            mu.ayar(_pin(**ek))
        except ValueError:
            hata += 1
    kontrol("dort gecersiz ayar reddedilir", hata == 4, "-> %d" % hata)


def test_etkin_turler_mg_icin_zorunlulari_icerir():
    print("\n[Y8-M2] etkin turler: zorunlular + secilenler; P0'da nu-transport")
    from cekirdek import mgxs_uret as mu
    # Arrange / Act
    p0 = mu.ayar(_pin(turler=["kappa-fission"]))
    yok = mu.ayar(_pin(duzeltme="yok"))
    # Assert
    for t in ("total", "absorption", "nu-fission", "chi", "nu-scatter matrix",
              "scatter matrix"):
        kontrol("zorunlu: %s" % t, t in p0.etkin_turler)
    kontrol("P0 -> nu-transport", "nu-transport" in p0.etkin_turler)
    kontrol("duzeltme yok -> nu-transport yok", "nu-transport" not in yok.etkin_turler)
    kontrol("secilen kappa-fission", "kappa-fission" in p0.etkin_turler)
    kontrol("tekrarsiz ve sirali", len(set(p0.etkin_turler)) == len(p0.etkin_turler))


def test_kurucu_kancasi_tally_ekler_kullanici_tallysi_birlesmez():
    print("\n[Y8-M3] kurucu: MGXS tally'leri eklenir; kutuphane bilgi['mgxs'] icinde")
    from cekirdek import kurucu
    # Arrange
    kapali = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    acik = _pin()
    # Act
    m0, _b0 = kurucu.kur(kapali)
    m1, b1 = kurucu.kur(acik)
    # Assert
    kontrol("tally sayisi artti", len(m1.tallies) > len(m0.tallies),
            "-> %d / %d" % (len(m0.tallies), len(m1.tallies)))
    kontrol("bilgi['mgxs'] Library", type(b1.get("mgxs")).__name__ == "Library")
    kontrol("kullanici tally'si ayni kaldi", _tally_ozeti(m0)[0] in _tally_ozeti(m1))
    kontrol("kapali: bilgi['mgxs'] None", _b0.get("mgxs") is None)


def test_bolge_turu_domainleri():
    print("\n[Y8-M4] bolge: malzeme -> material, hucre -> cell, demet -> universe (kok)")
    from cekirdek import kurucu
    sonuc = {}
    for bolge in ("malzeme", "hucre", "demet"):
        # Act
        _m, b = kurucu.kur(_pin(bolge=bolge))
        lib = b["mgxs"]
        sonuc[bolge] = (lib.domain_type, len(lib.domains))
    # Assert
    kontrol("malzeme: 3 material", sonuc["malzeme"] == ("material", 3), "-> %r" % sonuc)
    kontrol("hucre: material cell", sonuc["hucre"][0] == "cell" and sonuc["hucre"][1] >= 3)
    kontrol("demet: tek universe", sonuc["demet"] == ("universe", 1))


def test_xsdata_adlari_guvenli_ve_tekil():
    print("\n[Y8-M5] xsdata adlari [A-Za-z0-9_], bolge kimligiyle tekil")
    import re
    from cekirdek import kurucu, mgxs_uret as mu
    # Arrange
    _m, b = kurucu.kur(_pin(bolge="hucre"))
    # Act
    adlar = mu.xsdata_adlari(b["mgxs"])
    # Assert
    kontrol("hepsi guvenli", all(re.fullmatch(r"[A-Za-z0-9_]+", a) for a in adlar.values()),
            "-> %r" % adlar)
    kontrol("tekil", len(set(adlar.values())) == len(adlar))


def test_kurucu_ve_betik_ayni_tallyler():
    print("\n[Y8-M6] uretilen betik kurucu ile AYNI MGXS tally'lerini kurar")
    from cekirdek import kurucu
    for bolge in ("malzeme", "hucre", "demet"):
        # Arrange
        spec = _pin(bolge=bolge, grup_yapisi="CASMO-4", turler=["kappa-fission"])
        # Act
        model, _b = kurucu.kur(spec)
        with tempfile.TemporaryDirectory() as d:
            eski = os.getcwd()
            os.chdir(d)
            try:
                betik = _betik_modeli(spec, d)
            finally:
                os.chdir(eski)
        # Assert
        kontrol("%s: betik = kurucu" % bolge, _tally_ozeti(model) == _tally_ozeti(betik),
                "-> %d / %d tally" % (len(model.tallies), len(betik.tallies)))


def test_kapaliyken_model_ve_betik_degismez():
    print("\n[Y8-M7] mgxs kapaliyken betikte openmc.mgxs yok")
    from cekirdek import kod_uret
    # Arrange
    spec = _pin(var=False)
    # Act
    kod = kod_uret.uret(spec, "model.py")
    # Assert
    kontrol("betikte mgxs yok", "openmc.mgxs" not in kod)


def test_tukenmede_kapatilir_ve_dogrulama_bulgulari():
    print("\n[Y8-M8] tukenme acikken MGXS eklenmez (bilgi); gecersiz ayar hata bulgusu")
    from cekirdek import kurucu
    from cekirdek.dogrula import mgxs_kontrol
    # Arrange
    spec = _pin()
    spec["tukenme"] = dict(spec.get("tukenme") or {}, var=True)
    # Act
    _m, b = kurucu.kur(spec)
    bulgular = mgxs_kontrol(spec)
    hatali = mgxs_kontrol(_pin(bolge="kure"))
    # Assert
    kontrol("tukenmede kutuphane yok", b.get("mgxs") is None)
    kontrol("tukenme bilgisi", any(g.seviye == "bilgi" for g in bulgular),
            "-> %r" % (bulgular,))
    kontrol("gecersiz bolge hata", any(g.seviye == "hata" for g in hatali))


def test_bellek_tahmini():
    print("\n[Y8-M9] tally bellek tahmini: D x G^2 sacilma kutusu baskin")
    from cekirdek import mgxs_uret as mu
    # Arrange
    a2 = mu.ayar(_pin(grup_yapisi="CASMO-2"))
    a70 = mu.ayar(_pin(grup_yapisi="CASMO-70"))
    # Act
    b2, b70 = mu.bellek_tahmini(a2, 3), mu.bellek_tahmini(a70, 3)
    # Assert
    kontrol("70 grup 2 gruptan >= 35^2/2 kat", b70 > b2 * 35 ** 2 / 2, "-> %d / %d" % (b2, b70))


HIZLI = [test_ayar_varsayilan_ve_dogrulama, test_etkin_turler_mg_icin_zorunlulari_icerir,
         test_kurucu_kancasi_tally_ekler_kullanici_tallysi_birlesmez, test_bolge_turu_domainleri,
         test_xsdata_adlari_guvenli_ve_tekil, test_kurucu_ve_betik_ayni_tallyler,
         test_kapaliyken_model_ve_betik_degismez, test_tukenmede_kapatilir_ve_dogrulama_bulgulari,
         test_bellek_tahmini]
YAVAS = []
