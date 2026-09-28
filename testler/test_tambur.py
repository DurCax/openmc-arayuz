# -*- coding: utf-8 -*-
"""
 test_tambur.py  --  3y. kontrol tamburu: yerlesim, geometri kontrolu, kor, emici yonu, fizik

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import importlib.util
import os

from cekirdek import sema, kurucu, dogrula, kod_uret
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK


# ============================================================================
# 3y. KONTROL TAMBURU
# ============================================================================

def test_tambur_yerlesim():
    """Tambur yerlesimi ve psi acisi dogru olmali."""
    print("\n[3y] Tambur yerlesimi")
    import math
    from cekirdek import tambur
    t = {"sayi": 8, "yaricap": 4.0, "merkez_yaricap": 19.5,
         "emici_aci": 120.0, "donme": 0.0}
    yer = tambur.yerlesim(t)
    kontrol("tambur sayisi", len(yer) == 8)
    # her tamburda psi - azimut = 180 (emici kore bakiyor)
    tamam = True
    for x, y, psi in yer:
        fi = math.degrees(math.atan2(y, x)) % 360
        tamam &= abs(((psi - fi) % 360) - 180.0) < 1e-6
    kontrol("donme=0 -> psi = azimut + 180 (emici kore bakiyor)", tamam)
    # donme uygulanınca psi kadar kayar
    yer2 = tambur.yerlesim(dict(t, donme=90.0))
    kontrol("donme 90 -> psi 90 derece kayiyor",
            all(abs(((b[2] - a[2]) % 360) - 90.0) < 1e-6 for a, b in zip(yer, yer2)))
    # merkezden uzaklik sabit
    kontrol("tum tamburlar merkez yaricapinda",
            all(abs(math.hypot(x, y) - 19.5) < 1e-9 for x, y, _ in yer))


def test_tambur_geometri_kontrol():
    """Yerlesim hatalari yakalanmali."""
    print("\n[3z] Tambur geometri kontrolu")
    from cekirdek import tambur
    saglam = {"sayi": 8, "yaricap": 4.0, "merkez_yaricap": 19.5,
              "emici_ic_yaricap": 2.6, "emici_aci": 120.0, "donme": 0.0}
    kontrol("saglam yerlesim temiz",
            not tambur.geometri_kontrol(saglam, 14.0, 12.0))
    for ad, degisim, anahtar in (
            ("kora giriyor", {"merkez_yaricap": 16.0}, "kora giriyor"),
            ("yansiticidan tasiyor", {"merkez_yaricap": 24.0}, "taşıyor"),
            ("komsular cakisiyor", {"sayi": 20}, "çakışıyor"),
            ("emici ic yaricap buyuk", {"emici_ic_yaricap": 5.0}, "küçük olmalı")):
        h = tambur.geometri_kontrol(dict(saglam, **degisim), 14.0, 12.0)
        kontrol(ad, any(anahtar in x for x in h))


def test_tambur_kor():
    """Tamburlu kor kurulmali ve olculeri dogru olmali."""
    print("\n[3aa] Tamburlu kor")
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    b = dogrula.tum_kontroller(spec)
    kontrol("ornek dogrulamadan geciyor", not dogrula.hata_var(b),
            "(%s)" % dogrula.ozet(b))
    model, bilgi = kurucu.kur(spec)
    R = spec["kor"]["kor_yaricap"] + spec["kor"]["yansitici"]["kalinlik"]
    kontrol("sinir kutusu = 2 x dis yaricap",
            abs(bilgi["sinir_kutu"][0] - 2 * R) < 1e-9,
            "%.3f" % bilgi["sinir_kutu"][0])
    n = int(spec["kor"]["tambur"]["sayi"])
    kontrol("kok hucre sayisi = 1 kor + %d tambur + 1 yansitici" % n,
            len(model.geometry.root_universe.cells) == n + 2,
            "%d hucre" % len(model.geometry.root_universe.cells))

    # cakisan yerlesim kurulumda HATA vermeli
    import copy as _c
    bozuk = _c.deepcopy(spec)
    bozuk["kor"]["tambur"]["sayi"] = 24
    try:
        kurucu.kur(bozuk)
        kontrol("cakisan yerlesim reddediliyor", False, "reddetmedi")
    except ValueError as e:
        kontrol("cakisan yerlesim reddediliyor", "çakışıyor" in str(e))


def test_tambur_emici_yonu():
    """
    Emici yay GERCEKTEN dogru yone bakmali -- geometriye nokta sorgusu.
    (Bu, 'cell.rotation nesneyi mi cerceveyi mi donduruyor' sorusunu
    tahminle degil olcumle cozer.)
    """
    print("\n[3ab] Tambur emici yonu (nokta sorgusu)")
    import math
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    emici_ad = spec["kor"]["tambur"]["emici_malzeme"]

    def emici_acisi(donme, tambur_ix=0):
        import copy as _c
        s = _c.deepcopy(spec)
        s["kor"]["tambur"]["donme"] = donme
        model, bilgi = kurucu.kur(s)
        emici_mat = bilgi["malzemeler"][emici_ad]
        t = s["kor"]["tambur"]
        from cekirdek import tambur as _t
        x0, y0, _ = _t.yerlesim(t)[tambur_ix]
        r = (float(t["emici_ic_yaricap"]) + float(t["yaricap"])) / 2.0
        bulunan = []
        for a in range(0, 360, 2):
            x = x0 + r * math.cos(math.radians(a))
            y = y0 + r * math.sin(math.radians(a))
            try:
                yol = model.geometry.find((x, y, 0.0))
            except Exception:
                continue
            if any(isinstance(o, openmc.Cell) and o.fill is emici_mat for o in yol):
                bulunan.append(a)
        if not bulunan:
            return None
        sx = sum(math.cos(math.radians(a)) for a in bulunan)
        sy = sum(math.sin(math.radians(a)) for a in bulunan)
        return math.degrees(math.atan2(sy, sx)) % 360

    # 0. tambur +x ekseninde (azimut 0); emici kore bakmasi = 180 derece
    a0 = emici_acisi(0.0)
    kontrol("donme=0 -> emici KORE bakiyor (180 derece)",
            a0 is not None and abs(((a0 - 180.0) % 360)) < 12.0,
            "olculen %.1f derece" % (a0 if a0 is not None else -1))
    a180 = emici_acisi(180.0)
    kontrol("donme=180 -> emici DISA bakiyor (0 derece)",
            a180 is not None and min(a180, 360 - a180) < 12.0,
            "olculen %.1f derece" % (a180 if a180 is not None else -1))


def test_tambur_fizik(gecici):
    """
    Tambur donmesi k'yi ARTIRMALI (0 = emici kore bakiyor = en dusuk k),
    ve uretilen betik ayni sonucu vermeli.
    """
    print("\n[11] TAMBUR: donme -> k ve betik esdegerligi")
    import openmc
    from cekirdek import tarama
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    spec["ayarlar"].update(parcacik=2500, cevrim=35, pasif=12)

    kler = []
    for d in (0.0, 180.0):
        s2, _ = tarama.parametre_uygula(spec, "tambur_donme", None, d)
        dizin = os.path.join(gecici, "tambur_%d" % int(d))
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            model, _ = kurucu.kur(s2)
            kler.append(openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False)).keff)
        finally:
            os.chdir(eski)
    kontrol("donme 0 -> 180 k'yi ARTIRIYOR (%.5f -> %.5f)"
            % (kler[0].nominal_value, kler[1].nominal_value),
            kler[1].nominal_value > kler[0].nominal_value + 0.01)

    s3, _ = tarama.parametre_uygula(spec, "tambur_donme", None, 90.0)
    sonuclar = []
    for ad, betikten in (("tb_a", False), ("tb_b", True)):
        dizin = os.path.join(gecici, ad)
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            if betikten:
                betik = os.path.join(dizin, "model.py")
                with open(betik, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(s3, "model.py"))
                sm = importlib.util.spec_from_file_location("tburet", betik)
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
    test_tambur_yerlesim, test_tambur_geometri_kontrol, test_tambur_kor,
    test_tambur_emici_yonu,
]
YAVAS = [
    test_tambur_fizik,
]
