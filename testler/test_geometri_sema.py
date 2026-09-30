# -*- coding: utf-8 -*-
"""
 test_geometri_sema.py  --  G-1: dugum semasi, normalize, yapisal denetim (§3, §8)

 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy

from testler.ortak_test import kontrol
from testler import geometri_ortak as go


def _hatalar(spec):
    from cekirdek import geometri
    return [b for b in geometri.yapisal_denetim(spec) if b.seviye == "hata"]


def _mesajlar(spec, seviye="hata"):
    from cekirdek import geometri
    return [b.mesaj for b in geometri.yapisal_denetim(spec) if b.seviye == seviye]


def test_hedef_duzenekler_temiz():
    print("\n[GS1] hedef duzenekler (a)(b)(c)(d)(e) yapisal denetimden temiz gecer")
    for ad, spec in (("a", go.duzenek_a()), ("a-yakit", go.duzenek_a(True)),
                     ("b", go.duzenek_b()), ("c", go.duzenek_c()),
                     ("d-kare", go.duzenek_d("kare")), ("d-altigen", go.duzenek_d("altigen")),
                     ("e-ceyrek", go.duzenek_e_ceyrek()), ("e-tam", go.duzenek_e_tam())):
        h = _hatalar(spec)
        kontrol("(%s) hata yok" % ad, not h, "-> %s" % [str(b) for b in h[:3]])


def test_normalize_saf_ve_kisaltma():
    print("\n[GS2] normalize: kisaltmalar acik dugum, girdi degismez, referans -> parca")
    from cekirdek.geometri import sema as gs
    spec = go.duzenek_c()
    agac = copy.deepcopy(spec["geometri"])
    agac["kok"]["ic"]["anahtar"]["A"] = "demet_24"
    agac["kok"]["halkalar"][0]["icerik"] = "berilyum"
    agac["kok"]["halkalar"][0]["yerlesimler"][0]["icerik"] = "tambur_b4c"
    once = copy.deepcopy(agac)
    n = gs.normalize(spec, agac)
    kontrol("girdi degismedi", agac == once)
    kontrol("demet kisaltmasi -> bilesen",
            n["kok"]["ic"]["anahtar"]["A"] == {"tur": "bilesen", "ad": "demet_24"})
    kontrol("malzeme kisaltmasi -> malzeme",
            n["kok"]["halkalar"][0]["icerik"] == {"tur": "malzeme", "ad": "berilyum"})
    kontrol("tambur kisaltmasi -> bilesen",
            n["kok"]["halkalar"][0]["yerlesimler"][0]["icerik"]
            == {"tur": "bilesen", "ad": "tambur_b4c"})
    kontrol("'bosluk' -> void malzeme", gs.kisaltma_coz(gs.tanimlar(spec), "bosluk")
            == {"tur": "malzeme", "ad": "bosluk"})
    # kisaltma sirasi: cubuk -> plaka -> demet -> tambur -> parca -> malzeme
    s2 = copy.deepcopy(spec)
    s2["malzemeler"].append(dict(copy.deepcopy(s2["malzemeler"][0]), ad="demet_24"))
    kontrol("ayni ad demet ve malzeme: kisaltma demeti secer",
            gs.kisaltma_coz(gs.tanimlar(s2), "demet_24")["tur"] == "bilesen")
    # referans -> parca
    s3 = copy.deepcopy(spec)
    blok = {"tur": "kap", "id": "blokx", "kesit": {"sekil": "silindir", "yaricap": 1.0},
            "ic": {"tur": "malzeme", "ad": "su"}, "dis": {"tur": "malzeme", "ad": "su"},
            "halkalar": [], "yerlesimler": []}
    s3["geometri"]["kok"]["ic"]["anahtar"]["A"] = blok
    s3["geometri"]["kok"]["ic"]["anahtar"]["B"] = {"tur": "referans", "id": "blokx"}
    n3 = gs.normalize(s3, s3["geometri"])
    kontrol("referans parcaya cevrildi",
            [p["ad"] for p in n3["parcalar"]] == ["blokx"]
            and n3["kok"]["ic"]["anahtar"]["B"] == {"tur": "bilesen", "ad": "blokx"})


def _bozuk(islev):
    spec = go.duzenek_c()
    islev(spec, spec["geometri"])
    return spec


def _bozuk_b(islev):
    spec = go.duzenek_b()
    islev(spec, spec["geometri"])
    return spec


def test_yapisal_hatalar():
    print("\n[GS3] yapisal denetim her hata sinifini yakalar")
    kok = lambda g: g["kok"]  # noqa: E731
    durumlar = [
        ("bilinmeyen tur", lambda s, g: kok(g)["halkalar"][0].update(icerik={"tur": "kutu"}),
         "Bilinmeyen düğüm türü"),
        ("kap ic eksik", lambda s, g: kok(g).pop("ic"), "'ic' yuvası zorunlu"),
        ("tanimsiz bilesen", lambda s, g: kok(g)["ic"]["anahtar"].update(
            A={"tur": "bilesen", "ad": "yok_boyle"}), "Tanımsız bileşen"),
        ("tanimsiz malzeme", lambda s, g: kok(g)["halkalar"][0].update(
            icerik={"tur": "malzeme", "ad": "yok"}), "Tanımsız malzeme"),
        ("tanimsiz kisaltma", lambda s, g: kok(g)["ic"]["anahtar"].update(A="yok_ad"),
         "Tanımsız ad"),
        ("belirsiz ad", lambda s, g: s["cubuklar"].append(
            dict(copy.deepcopy(s["cubuklar"][0]), ad="demet_24")), "Belirsiz ad"),
        ("harita satir", lambda s, g: kok(g)["ic"].update(harita=["ABA", "BAB"]),
         "satır; boyut"),
        ("tanimsiz harf", lambda s, g: kok(g)["ic"].update(harita=["ABA", "BZB", "ABA"]),
         "tanımsız harf"),
        ("kafes dis eksik", lambda s, g: kok(g)["ic"].pop("dis"), "'dis' yuvası zorunlu"),
        ("adim sifir", lambda s, g: kok(g)["ic"].update(adim=0), "adımı sıfırdan büyük"),
        ("halka iki alan", lambda s, g: kok(g)["halkalar"][0].update(kalinlik=3.0),
         "tam olarak biri"),
        ("halka kapsamiyor", lambda s, g: kok(g)["halkalar"][0].update(
            dis={"sekil": "silindir", "yaricap": 30.0}), "kapsamıyor"),
        ("kokte dis", lambda s, g: kok(g).update(dis={"tur": "malzeme", "ad": "su"}),
         "Kök kapta 'dis' olamaz"),
        ("malzemede donusum", lambda s, g: kok(g)["halkalar"][0].update(
            icerik={"tur": "malzeme", "ad": "su", "donusum": {"donme": 30.0}}),
         "dönüşüm uygulanamaz"),
        ("grup uyesi tanimsiz", lambda s, g: g["gruplar"][0].update(uyeler=["yok"]),
         "tanımsız ya da türü uyuşmuyor"),
        ("iki grupta", lambda s, g: g["gruplar"].append(
            {"ad": "ikinci", "tur": "donme", "deger": 0.0, "uyeler": ["tamburlar4"]}),
         "aynı türden iki grupta"),
        ("yukseklik cakisma", lambda s, g: kok(g).update(ic={
            "tur": "eksenel", "icerik": kok(g)["ic"],
            "katmanlar": [{"ad": "a", "yukseklik": 50.0, "icerik": None}]}),
         "farklı toplamlı"),
        ("katman anahtari kafes degil", lambda s, g: kok(g).update(yukseklik=None, ic={
            "tur": "eksenel", "icerik": {"tur": "malzeme", "ad": "su"},
            "katmanlar": [{"ad": "a", "yukseklik": 50.0, "icerik": None,
                           "anahtar": {"A": "demet_31"}}]}), "yalnız varsayılan içerik"),
        ("periyodik tek yuz", lambda s, g: kok(g).update(
            kesit={"sekil": "dikdortgen", "boyut": [64.26, 64.26]}, halkalar=[],
            sinir={"yan": "vacuum", "yuzler": {"-x": "periodic", "+x": "vacuum"}}),
         "Periyodik sınır karşılıklı"),
        ("delik kesiti eksik", lambda s, g: kok(g)["halkalar"][0]["yerlesimler"][0].update(
            icerik={"tur": "malzeme", "ad": "su"}), "Delik kesiti"),
        ("kafes konumu yok", lambda s, g: kok(g)["halkalar"][0]["yerlesimler"].append(
            {"ad": "kk", "mod": "kafes_konumu", "kafes": "yok", "harf": "A",
             "kesit": {"sekil": "silindir", "yaricap": 1.0}, "icerik": "su"}),
         "kimlikli kafes"),
        ("kimlik iki kez", lambda s, g: kok(g)["ic"].update(id="kok"), "iki kez"),
    ]
    for ad, islev, parca in durumlar:
        m = _mesajlar(_bozuk(islev))
        kontrol("%s -> HATA" % ad, any(parca in x for x in m), "-> %s" % m[:3])


def test_yapisal_hatalar_ozel():
    print("\n[GS4] dongu, derinlik, kafes_zarfi ve kok disi kap kurallari")
    # dongu: A -> B -> A
    spec = go.duzenek_c()
    kap = lambda ic: {"tur": "kap", "kesit": {"sekil": "silindir", "yaricap": 1.0},  # noqa: E731
                      "ic": ic, "dis": "su", "halkalar": [], "yerlesimler": []}
    spec["geometri"]["parcalar"] = [{"ad": "pA", "dugum": kap("pB")},
                                    {"ad": "pB", "dugum": kap("pA")}]
    spec["geometri"]["kok"]["ic"]["anahtar"]["A"] = "pA"
    m = _mesajlar(spec)
    kontrol("dongu -> HATA", any("Döngü" in x for x in m), "-> %s" % m[:2])
    # derinlik: 12 ic ice kap
    spec = go.duzenek_c()
    d = "su"
    for _i in range(12):
        d = kap(d)
    spec["geometri"]["kok"]["ic"]["anahtar"]["A"] = d
    m = _mesajlar(spec)
    kontrol("derinlik > 10 -> HATA", any("derinlik" in x for x in m), "-> %s" % m[:2])
    kontrol("derinlik > 6 -> UYARI", any("derinlik" in x for x in _mesajlar(spec, "uyari")))
    # kok disinda kap 'dis' zorunlu
    spec = go.duzenek_c()
    k2 = kap("su")
    k2.pop("dis")
    spec["geometri"]["kok"]["ic"]["anahtar"]["A"] = k2
    m = _mesajlar(spec)
    kontrol("kok disi kapta dis yok -> HATA", any("Kök olmayan kapta" in x for x in m))
    # kafes_zarfi + kalinlik
    s = _bozuk_b(lambda s, g: g["kok"]["halkalar"][0].update(
        dis=None, kalinlik=5.0))
    m = _mesajlar(s)
    kontrol("kafes_zarfi + kalinlik -> HATA", any("kafes_zarfi" in x for x in m), "-> %s" % m)
    # kafes_zarfi kare kafeste
    s = go.duzenek_c()
    s["geometri"]["kok"]["kesit"] = {"sekil": "kafes_zarfi"}
    s["geometri"]["kok"]["halkalar"] = []
    m = _mesajlar(s)
    kontrol("kafes_zarfi + kare kafes -> HATA", any("altıgen kafes" in x for x in m))
    # altigen harita halka uzunlugu
    s = _bozuk_b(lambda s, g: g["kok"]["ic"].update(harita=["D" * 11, "D" * 6, "D"]))
    kontrol("altigen halka uzunlugu -> HATA",
            any("halka bekliyor" in x for x in _mesajlar(s)))
    # kafes_zarfi: kafes.dis bilgi
    s = _bozuk_b(lambda s, g: g["kok"]["ic"].update(dis="celik"))
    kontrol("kafes_zarfi + kafes.dis -> BILGI",
            any("R3b" in x for x in _mesajlar(s, "bilgi")))
    # kullanilmayan parca -> bilgi
    s = go.duzenek_c()
    s["geometri"]["parcalar"] = [{"ad": "bos_parca", "dugum": kap("su")}]
    kontrol("kullanilmayan parca -> BILGI",
            any("kullanılmıyor" in x for x in _mesajlar(s, "bilgi")))


HIZLI = [test_hedef_duzenekler_temiz, test_normalize_saf_ve_kisaltma,
         test_yapisal_hatalar, test_yapisal_hatalar_ozel]
YAVAS = []
