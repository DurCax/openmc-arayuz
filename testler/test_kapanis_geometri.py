# -*- coding: utf-8 -*-
"""
 test_kapanis_geometri.py  --  D1-Kapanis B8, B10, B11: kesit alani ve
                               duzlem dogrultu kumelemesi

 HATA (inceleme, dogrulandi):
   B8  tukenme_hacim._dugunluk_alani yalniz TEK yonde sinirli bir bolgeyi
       (ornek: iki XPlane arasi serit) 2 * dx * R gibi SONLU bir alanla
       donduruyordu (esik alan > R*R yalniz tamamen sinirsizi yakalar):
       sessizce yanlis hacim. Kirpilan cokgen yardimci kutunun kenarina
       dokunuyorsa bolge acik sayilir (None -> "stokastik gerekli").
   B10 guc_kor._dogrultu_gruplari acilari round(aci, 6) ile anahtarliyordu:
       yuvarlama sinirinin iki yanindaki (1e-6 dereceden yakin) iki duzlem
       ayri dogrultu sayiliyordu. Toleransli kumeleme (sirala + ardisik fark).
   B11 ornek_hacmi `if u` -> `if u is not None` (davranis ayni; 0 uzunluk
       artik sessizce atlanmaz).

 HIZLI: saf Python + openmc yuzey nesneleri; nukleer veri yok.
"""

import math

from testler.ortak_test import kontrol

SQ3 = math.sqrt(3.0)


def test_yari_sinirli_bolge_acik():
    print("\n[KG1] _dugunluk_alani: yari sinirli bolge -> None; kapali cokgen -> alan")
    import openmc
    from cekirdek import tukenme_hacim as th
    serit = +openmc.XPlane(-1.0) & -openmc.XPlane(1.0)
    kontrol("iki XPlane serit -> None", th.bolge_alani(serit) is None,
            "-> %r" % th.bolge_alani(serit))
    uc = serit & +openmc.YPlane(0.0)
    kontrol("uc duzlem (U bicimli, bir yon acik) -> None", th.bolge_alani(uc) is None,
            "-> %r" % th.bolge_alani(uc))
    kose = +openmc.XPlane(0.0) & +openmc.YPlane(0.0)
    kontrol("ceyrek duzlem (kose) -> None", th.bolge_alani(kose) is None,
            "-> %r" % th.bolge_alani(kose))
    kare = serit & +openmc.YPlane(-2.0) & -openmc.YPlane(3.0)
    kontrol("kapali dikdortgen 2 x 5 = 10", abs((th.bolge_alani(kare) or 0) - 10.0) < 1e-9,
            "-> %r" % th.bolge_alani(kare))
    a = 1.7
    alti = -openmc.model.HexagonalPrism(edge_length=a, orientation="y")
    beklenen = 3.0 * SQ3 / 2.0 * a * a
    kontrol("altigen prizma (3 sqrt3/2) a^2",
            abs((th.bolge_alani(alti) or 0) / beklenen - 1.0) < 1e-10,
            "-> %r vs %r" % (th.bolge_alani(alti), beklenen))
    alti_x = -openmc.model.HexagonalPrism(edge_length=a, orientation="x", origin=(5.0, -3.0))
    kontrol("x yonelimli, otelenmis altigen",
            abs((th.bolge_alani(alti_x) or 0) / beklenen - 1.0) < 1e-10)
    yarim_alti = +openmc.Plane(a=1.0, b=SQ3, d=0.0) & -openmc.Plane(a=1.0, b=SQ3, d=2.0)
    kontrol("egik serit (genel Plane, iki paralel) -> None",
            th.bolge_alani(yarim_alti) is None)


def _duzlem(aci_derece, uzaklik=1.0):
    import openmc
    r = math.radians(aci_derece)
    return openmc.Plane(a=math.cos(r), b=math.sin(r), c=0.0, d=uzaklik)


def test_dogrultu_toleransli_kumeleme():
    print("\n[KG2] _dogrultu_gruplari: 1e-6 dereceden yakin acilar ayni dogrultu")
    from cekirdek import guc_kor
    for a1, a2 in ((59.9999995, 60.0000005), (60.0000004, 60.0000006),
                   (30.00000049, 30.00000051)):
        g = guc_kor._dogrultu_gruplari([_duzlem(a1, 1.0), _duzlem(a2, -1.0)])
        kontrol("%.8f ve %.8f tek grup" % (a1, a2),
                g is not None and len(g) == 1 and len(next(iter(g.values()))) == 2,
                "-> %r" % g)
    g = guc_kor._dogrultu_gruplari([_duzlem(179.99999995, 1.0), _duzlem(0.00000005, 2.0)])
    kontrol("0/180 derece sarmasi tek grup", g is not None and len(g) == 1, "-> %r" % g)
    if g and len(g) == 1:
        uz = sorted(next(iter(g.values())))
        kontrol("sarmada isaret: karsi yonlu normal -> -1 ve +2",
                abs(uz[0] + 1.0) < 1e-6 and abs(uz[1] - 2.0) < 1e-6, "-> %r" % uz)
    g = guc_kor._dogrultu_gruplari([_duzlem(0.0), _duzlem(60.0), _duzlem(120.0),
                                    _duzlem(180.0, -1.0), _duzlem(240.0, -1.0),
                                    _duzlem(300.0, -1.0)])
    kontrol("altigen: 3 dogrultu x 2", g is not None and len(g) == 3
            and all(len(v) == 2 for v in g.values()), "-> %r" % g)
    g = guc_kor._dogrultu_gruplari([_duzlem(60.0), _duzlem(60.001)])
    kontrol("gercekten farkli (1e-3 derece) iki dogrultu ayri", g is not None and len(g) == 2)


def test_altigen_hucre_kucuk_donme():
    print("\n[KG3] altigen_hucre: yuvarlama sinirindaki duzlemlerle altigen yine taninir")
    import openmc
    from cekirdek import guc_kor
    P = 2.0
    uz = P / 2.0
    yarilar = None
    for i, aci in enumerate((0.0, 60.0, 120.0)):
        e = 5e-7 if i == 1 else 0.0          # 60 derece yuvarlama sinirinda
        alt, ust = _duzlem(aci - e, -uz), _duzlem(aci + e, uz)
        parca = +alt & -ust
        yarilar = parca if yarilar is None else (yarilar & parca)
    hucre = openmc.Cell(region=yarilar)
    s = guc_kor.altigen_hucre(hucre)
    kontrol("altigen taninir, adim = P, merkez 0",
            s is not None and abs(s[2] - P) < 1e-6 and abs(s[0]) < 1e-6 and abs(s[1]) < 1e-6,
            "-> %r" % (s,))


HIZLI = [test_yari_sinirli_bolge_acik, test_dogrultu_toleransli_kumeleme,
         test_altigen_hucre_kucuk_donme]
YAVAS = []
