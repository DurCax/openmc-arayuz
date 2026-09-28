# -*- coding: utf-8 -*-
"""
 test_kontrol_cubugu.py  --  3u. kontrol cubugu: geometri, parametre, dogrulama, arama, fizik

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import importlib.util
import os

from cekirdek import sema, kurucu, dogrula, kod_uret
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK


# ============================================================================
# 3u. KONTROL CUBUGU
# ============================================================================

def test_kontrol_cubugu_geometri():
    """Kontrol cubugu emici bolgeyi eksenel olarak ikiye bolmeli."""
    print("\n[3u] Kontrol cubugu geometrisi")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    _, bilgi = kurucu.kur(spec)
    u = bilgi["universeler"]["kontrol_cubugu"]
    c = sema.cubuk_bul(spec, "kontrol_cubugu")
    kontrol("hucre sayisi = bolge + 1 (eksenel bolme)",
            len(u.cells) == len(c["bolgeler"]) + 1,
            "%d hucre, %d bolge" % (len(u.cells), len(c["bolgeler"])))
    dolgular = [getattr(x.fill, "name", "") for x in u.cells.values()]
    kontrol("emici malzeme universe'de var", any("B4C" in d for d in dolgular))

    # daldirma -> uc konumu: universe'deki ZPlane'in GERCEK konumu olculur
    h = spec["kor"]["yukseklik"]
    import copy as _c
    import openmc

    def uc_konumu(universe):
        """Kontrol universe'undeki tek ZPlane'i bulur (cubugun ucu)."""
        bulunan = set()
        for hucre in universe.cells.values():
            if hucre.region is None:
                continue
            for y in hucre.region.get_surfaces().values():
                if isinstance(y, openmc.ZPlane):
                    bulunan.add(round(float(y.z0), 9))
        return bulunan

    for d, beklenen in ((0.0, h / 2), (25.0, h / 2 - 0.25 * h),
                        (50.0, 0.0), (100.0, -h / 2)):
        s = _c.deepcopy(spec)
        sema.cubuk_bul(s, "kontrol_cubugu")["daldirma"] = d
        _, b2 = kurucu.kur(s)
        z = uc_konumu(b2["universeler"]["kontrol_cubugu"])
        kontrol("daldirma %%%.0f -> uc z = %+.2f cm" % (d, beklenen),
                len(z) == 1 and abs(list(z)[0] - beklenen) < 1e-9,
                "olculen %s" % sorted(z))

    # 2B modelde HATA vermeli
    s2 = _c.deepcopy(spec)
    s2["kor"]["yukseklik"] = None
    try:
        kurucu.kur(s2)
        kontrol("2B modelde hata veriyor", False, "hata vermedi")
    except ValueError as e:
        kontrol("2B modelde hata veriyor", "3B model gerektirir" in str(e))


def test_kontrol_cubugu_parametre():
    """cubuk_daldirma parametresi dogru uygulanmali."""
    print("\n[3v] Kontrol cubugu tarama parametresi")
    from cekirdek import tarama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    kontrol("tarama turunde var", "cubuk_daldirma" in tarama.TURLER)
    y, _ = tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", 75.0)
    kontrol("daldirma uygulandi",
            abs(sema.cubuk_bul(y, "kontrol_cubugu")["daldirma"] - 75.0) < 1e-9)
    kontrol("kaynak spec bozulmadi",
            abs(sema.cubuk_bul(spec, "kontrol_cubugu")["daldirma"] - 0.0) < 1e-9)
    # kontrol olmayan cubukta reddetmeli
    try:
        tarama.parametre_uygula(spec, "cubuk_daldirma", "yakit_cubugu", 50.0)
        kontrol("kontrol olmayan cubugu reddediyor", False, "reddetmedi")
    except ValueError as e:
        kontrol("kontrol olmayan cubugu reddediyor", "kontrol çubuğu değil" in str(e))
    # aralik disi
    for d in (-5.0, 150.0):
        try:
            tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", d)
            kontrol("daldirma %g reddedilmeli" % d, False, "reddedilmedi")
        except ValueError:
            kontrol("daldirma %g reddedildi" % d, True)


def test_kontrol_cubugu_dogrulama():
    """Kontrol cubugu ayar hatalari yakalanmali."""
    print("\n[3w] Kontrol cubugu dogrulamasi")
    import copy as _c
    temiz = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    kontrol("temiz model hatasiz",
            not dogrula.hata_var(dogrula.tum_kontroller(temiz)))

    def dene(ad, degistir, anahtar):
        s = _c.deepcopy(temiz)
        degistir(s)
        b = dogrula.tum_kontroller(s)
        kontrol(ad, any(anahtar.lower() in x.mesaj.lower() for x in b))

    dene("2B model -> hata", lambda s: s["kor"].update({"yukseklik": None}),
         "3B model gerektirir")
    dene("daldirma araligi",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update({"daldirma": 150.0}),
         "daldırma")
    dene("gecersiz emici bolge",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update({"emici_bolge": 9}),
         "geçersiz emici bölge")
    dene("sogurucu olmayan emici",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update({"emici_bolge": 1}),
         "emici içermiyor")
    dene("tanimsiz izleyici",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update(
             {"izleyici_malzeme": "yok_boyle"}), "tanımsız izleyici")


def test_arama_tekrar_etmiyor():
    """Kritik arama ayni noktayi iki kez KOSMAMALI (parantez korumali yontem)."""
    print("\n[3x] Kritik arama: tekrar eden nokta yok")
    from cekirdek import kritik_arama
    import tempfile as _t
    cagrilar = []

    def sahte(spec, tur, hedef, deger, dizin, is_parcacigi, taban):
        cagrilar.append(deger)
        return 1.3 - 0.0001 * deger, 0.0005

    orj = kritik_arama._nokta_kos
    kritik_arama._nokta_kos = sahte
    try:
        spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
        s = kritik_arama.ara(spec, "bor_ppm", "su", 0, 5000, _t.mkdtemp())
        kontrol("cozum bulundu", s.basarili)
        yuvarlak = [round(x, 6) for x in cagrilar]
        kontrol("hicbir nokta tekrar edilmedi",
                len(yuvarlak) == len(set(yuvarlak)),
                "%d kosu, %d benzersiz" % (len(yuvarlak), len(set(yuvarlak))))
        kontrol("kok belirsizligi raporlandi", s.cozum_belirsizlik is not None)
    finally:
        kritik_arama._nokta_kos = orj


def test_kontrol_cubugu_fizik(gecici):
    """
    Kontrol cubugu daldirildikca k DUSMELI, ve uretilen betik ayni sonucu
    vermeli.
    """
    print("\n[10] KONTROL CUBUGU: daldirma -> k ve betik esdegerligi")
    import openmc
    from cekirdek import tarama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    spec["ayarlar"].update(parcacik=2500, cevrim=35, pasif=12)

    kler = []
    for d in (0.0, 100.0):
        s2, _ = tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", d)
        dizin = os.path.join(gecici, "kontrol_%d" % int(d))
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            model, _ = kurucu.kur(s2)
            kler.append(openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False)).keff)
        finally:
            os.chdir(eski)
    kontrol("daldirma k'yi dusuruyor (%.5f -> %.5f)"
            % (kler[0].nominal_value, kler[1].nominal_value),
            kler[1].nominal_value < kler[0].nominal_value - 0.05)

    # betik esdegerligi (daldirma %50)
    s3, _ = tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", 50.0)
    sonuclar = []
    for ad, betikten in (("kk_a", False), ("kk_b", True)):
        dizin = os.path.join(gecici, ad)
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            if betikten:
                betik = os.path.join(dizin, "model.py")
                with open(betik, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(s3, "model.py"))
                sm = importlib.util.spec_from_file_location("kkuret", betik)
                mo = importlib.util.module_from_spec(sm)
                sm.loader.exec_module(mo)
                model = mo.model
            else:
                model, _ = kurucu.kur(s3)
            sonuclar.append(openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False)).keff)
        finally:
            os.chdir(eski)
    fark = abs(sonuclar[0].nominal_value - sonuclar[1].nominal_value)
    kontrol("betik ayni k (%.8f vs %.8f)"
            % (sonuclar[0].nominal_value, sonuclar[1].nominal_value), fark < 1e-10)


HIZLI = [
    test_kontrol_cubugu_geometri, test_kontrol_cubugu_parametre,
    test_kontrol_cubugu_dogrulama, test_arama_tekrar_etmiyor,
]
YAVAS = [
    test_kontrol_cubugu_fizik,
]
