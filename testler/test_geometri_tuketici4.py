# -*- coding: utf-8 -*-
"""
 test_geometri_tuketici4.py  --  G-2: basvuru/ad_degistir kenar durumlari, hacim
 kayitlari (kure, sifir hacim, yok), kesik cubuk yoklamasi (MC'siz, kurulan
 geometride) ve eksenel guc faktorleri. Sozlesme: testler/ortak_test.py.
"""

import copy
import math
import os

from testler.ortak_test import kontrol, ORNEK
from testler import geometri_ortak as go


def test_ad_degistir_kenar():
    print("\n[GK1] ad_degistir: cubuk (demet anahtari + guc hedefi), parca, kafes; hatalar")
    from cekirdek import geometri, kurucu, sema
    spec = go.duzenek_a()
    spec["guc_dagilimi"] = {"var": True, "cubuklar": [{"cubuk": "yakit_24", "bolge": 0}]}
    y = geometri.ad_degistir(spec, "cubuk", "yakit_24", "pin24")
    d = sema.demet_bul(y, "demet_24")
    kontrol("cubuk: tanim, demet anahtari ve guc hedefi degisti",
            sema.cubuk_bul(y, "pin24") is not None and "pin24" in d["anahtar"].values()
            and y["guc_dagilimi"]["cubuklar"][0]["cubuk"] == "pin24")
    y = geometri.ad_degistir(spec, "parca", "celik_blok", "blok2")
    kontrol("parca: tanim ve bilesen basvurusu degisti",
            y["geometri"]["parcalar"][0]["ad"] == "blok2"
            and y["geometri"]["kok"]["ic"]["anahtar"]["B"]["ad"] == "blok2")
    y = geometri.ad_degistir(spec, "kafes", "cekirdek_kafesi", "kare3")
    kafes = y["geometri"]["kok"]["yerlesimler"][0]["icerik"]
    kontrol("kafes: kimlik degisti", kafes["id"] == "kare3")
    try:
        kurucu.kur(copy.deepcopy(geometri.ad_degistir(spec, "cubuk", "yakit_24", "pin24")))
        kuruldu = True
    except Exception as e:     # noqa: BLE001 -- test: her hata raporlanir
        kuruldu = "%s" % e
    kontrol("yeniden adlandirilmis cubukla model kurulur", kuruldu is True, "-> %s" % kuruldu)
    for tur, eski, yeni, hata in (("cubuk", "yok", "x", KeyError),
                                  ("cubuk", "yakit_24", "yakit_31", ValueError)):
        try:
            geometri.ad_degistir(spec, tur, eski, yeni)
            olan = None
        except (KeyError, ValueError) as e:
            olan = type(e)
        kontrol("%s %s -> %s: %s" % (tur, eski, yeni, hata.__name__), olan is hata)
    kontrol("ayni ad: kopya doner", geometri.ad_degistir(spec, "cubuk", "yakit_24",
                                                         "yakit_24") == spec)
    sablon = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    kontrol("sablon modunda basvuru listesi bos", geometri.basvurular(sablon) == [])
    y = geometri.ad_degistir(sablon, "demet", sablon["kor"]["demet"], "d17")
    kontrol("sablon: kor.demet de degisti", y["kor"]["demet"] == "d17")
    b = go.duzenek_b()
    b["geometri"]["kok"]["ic"]["anahtar"]["D"] = "demet_hex"      # kisaltma
    bas = {(x.tur, x.ad) for x in geometri.basvurular(b)}
    kontrol("kisaltma dize basvurusu cozulur", ("demet", "demet_hex") in bas, "-> %s" % bas)
    y = geometri.ad_degistir(b, "demet", "demet_hex", "dh")
    kontrol("kisaltma dize de yeniden adlandirilir",
            y["geometri"]["kok"]["ic"]["anahtar"]["D"] == "dh")


def test_hacim_kayitlari():
    print("\n[GK2] hacim: kure kabugu, hacmi sifir (cekili emici), bulunamayan, hesapla")
    from cekirdek import geometri, sema
    from cekirdek.geometri import hacim
    s = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    m = geometri.model(s)
    mal = s["kor"]["kabuklar"][0]["malzeme"]
    k = hacim.analitik(m, mal)
    r = s["kor"]["kabuklar"][0]["r"]
    kontrol("kure: 4/3 pi r^3", k.hacim and abs(k.hacim - 4 / 3 * math.pi * r ** 3) < 1e-9 * k.hacim,
            "-> %s" % (k,))
    kontrol("bulunamayan malzeme 'yok'", hacim.analitik(m, "yok_boyle").yontem == hacim.YOK)
    s = geometri.gelismise_gec(sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json")))
    kc = next(c for c in s["cubuklar"] if c.get("tur") == "kontrol")
    kc["daldirma"] = 0.0
    em = kc["bolgeler"][int(kc.get("emici_bolge") or 0)]["malzeme"]
    k = hacim.analitik(geometri.model(s), em)
    kontrol("tamamen cekili emici: hacmi sifir", k.yontem == hacim.YOK and "sıfır" in k.ayrinti,
            "-> %s" % (k,))
    k = hacim.hesapla(go.duzenek_a(True), "uo2_24", stokastik_yedek=False)
    kontrol("hesapla yedeksiz: kesin degil kalir", k.yontem == hacim.KESIN_DEGIL and k.sorunlar)
    k = hacim.hesapla(go.duzenek_c(), "b4c")
    kontrol("hesapla: analitik kesinse stokastik kosulmaz", k.yontem == hacim.ANALITIK)
    kontrol("sozluk bicimi", set(k.sozluk()) == {"hacim", "yontem", "ayrinti"})
    kutu = hacim._kutu(sema.yukle(os.path.join(ORNEK, "godiva_kriter.json")))
    kontrol("kure kokunde stokastik kutu kup", kutu[0][2] == kutu[0][0])


def _yakit_blok_dagilimi():
    """(a-yakit) kurulan geometriden MC'siz dagilim: blok ve cekirdek pin anahtarlari."""
    from cekirdek import altigen, guc_kor, kurucu
    model, bilgi = kurucu.kur(go.duzenek_a(True))
    geo = model.geometry
    kafesler = {k.name: k for k in geo.get_all_lattices().values() if k.name}
    kor, blok = kafesler["g:cekirdek_kafesi"], kafesler["g:blok_kafesi"]
    demet = next(k for k in geo.get_all_lattices().values() if k not in (kor, blok)
                 and k.pitch[0] < 2.0)
    konumlar = {}
    for r, i in sorted(altigen.konumlar(5, "x")):
        if r not in (1, 2):          # yaricap 3 ve 2: kare delikle kirpilan halkalar
            continue
        for pin in ((0, 0), (16, 16), (0, 16), (16, 0), (8, 8)):
            konumlar[(("g:blok_kafesi", r, i), pin)] = {"eksenel": [(1.0, 0.1)],
                                                         "toplam": (1.0, 0.1)}
    konumlar[(("g:cekirdek_kafesi", 2, 2), (8, 8))] = {"eksenel": [(1.0, 0.1)],
                                                       "toplam": (1.0, 0.1)}
    duzey = guc_kor.KarisikDuzey(kafesler={"g:cekirdek_kafesi": kor, "g:blok_kafesi": blok})
    hedef = {h.id for _a, h in bilgi.get("guc_hucreler") or []}
    if not hedef:
        hedef = {c.id for c in geo.get_all_cells().values()
                 if getattr(c.fill, "name", "") in ("uo2_24",) or
                 (bilgi["malzemeler"].get("uo2_24") is c.fill)}
    return {"konumlar": konumlar, "tam_kor": True, "kafesler": [duzey, demet],
            "eksenel_dilim": 1}, geo, hedef


def test_kesik_cubuk_yoklamasi():
    print("\n[GK3] kesik/gizli cubuk yoklamasi (MC'siz): blok halkasi kesik, cekirdek temiz")
    from cekirdek import guc
    from cekirdek.guc_faktor import kesik_cubuklar, kesikler
    dagilim, geo, hedef = _yakit_blok_dagilimi()
    kesik = set(kesik_cubuklar(dagilim, geo, hedef, 0.0))
    blok = [a for a in dagilim["konumlar"] if a[0][0] == "g:blok_kafesi"]
    kontrol("blok halkasinda kesik/gizli cubuk var, hepsi degil",
            0 < len(kesik & set(blok)) < len(blok), "-> %d / %d" % (len(kesik), len(blok)))
    kontrol("cekirdek merkez cubugu kesik degil",
            (("g:cekirdek_kafesi", 2, 2), (8, 8)) not in kesik)
    f = guc.tepe_faktorleri(dict(dagilim, kesik_cubuklar=sorted(kesik, key=repr),
                                 kafes_turu="kare", kafes_turleri=["karisik", "kare"]))
    kontrol("tepe_faktorleri kesikleri disarida birakir",
            f["cubuk_sayisi"] == len(dagilim["konumlar"]) - len(kesik)
            and len(f["kesik_cubuklar"]) == len(kesik))
    kontrol("karisik duzey yoksa kesik yoklamasi calismaz",
            kesikler(dict(dagilim, kafesler=[]), geo, [], []) == [])
    kontrol("tam kor degilse bos", kesik_cubuklar(dict(dagilim, tam_kor=False), geo, hedef) == [])


def test_eksenel_faktorler():
    print("\n[GK4] eksenel faktorler: F_q, bos dilim ortalamaya girmez")
    from cekirdek.guc_faktor import _bos_dilimler, _eksenel_faktorler
    konumlar = {(0, 0): {"eksenel": [(1.0, 0.1), (0.0, 0.0), (3.0, 0.1)]},
                (1, 0): {"eksenel": [(1.0, 0.1), (0.0, 0.0), (1.0, 0.1)]}}
    kontrol("bos dilim 1", _bos_dilimler(konumlar, 3) == [1])
    s = {}
    _eksenel_faktorler(s, konumlar, 3)
    kontrol("F_q = 3 / 1.5 = 2", abs(s["F_q"] - 2.0) < 1e-12 and s["sicak_dilim"] == ((0, 0), 2),
            "-> %s" % s.get("F_q"))
    kontrol("eksenel profil 3 dilim", len(s["eksenel_profil"]) == 3)


HIZLI = [test_ad_degistir_kenar, test_hacim_kayitlari, test_kesik_cubuk_yoklamasi,
         test_eksenel_faktorler]
YAVAS = []
