# -*- coding: utf-8 -*-
"""
 test_geometri_tuketici.py  --  G-2: geometri API'si tuketicileri (agac modu)

 gez/icerik sablon icerigiyle ayni (27 ornek); analitik hacim sablon
 hacmiyle ayni ve agac duzeneklerinde elle hesapla ayni; basvurular ve
 ad_degistir; sinir_bilgisi; grup_degeri_yaz. Sozlesme: testler/ortak_test.py.
 Tukenme/guc/tarama/dogrulama tuketicileri: test_geometri_tuketici2.py.
"""

import copy
import glob
import math
import os

from testler.ortak_test import kontrol, ORNEK
from testler import geometri_ortak as go

SQ3 = math.sqrt(3.0)
ICERIK_ANAHTARLARI = ("malzeme", "cubuk", "plaka", "demet", "kafesteki_cubuk")


def _ornekler():
    from cekirdek import sema
    return [(os.path.basename(y), sema.yukle(y))
            for y in sorted(glob.glob(os.path.join(ORNEK, "*.json")))]


def test_icerik_sablonla_ayni():
    print("\n[GT1] geometri.icerik(model) = uygunluk.geometri_icerigi (butun ornekler)")
    from cekirdek import geometri, uygunluk
    farkli = []
    ornekler = _ornekler()
    for ad, spec in ornekler:
        yeni = geometri.icerik(geometri.model(spec))
        eski = uygunluk.geometri_icerigi(spec)
        fark = {k: sorted(eski[k] ^ yeni[k]) for k in ICERIK_ANAHTARLARI if eski[k] != yeni[k]}
        if fark:
            farkli.append((ad, fark))
    kontrol("%d ornekte icerik ayni" % len(ornekler), not farkli and len(ornekler) >= 27,
            "-> %s" % farkli[:3])


def test_hacim_sablonla_ayni():
    print("\n[GT2] geometri.hacim.analitik = tukenme sablon hacmi (butun ornekler)")
    from cekirdek import geometri, tukenme
    from cekirdek.geometri import hacim
    farkli, sayi = [], 0
    for ad, spec in _ornekler():
        m = geometri.model(spec)
        for mal, k in tukenme._hacim_tablosu(spec).items():
            y = hacim.analitik(m, mal)
            sayi += 1
            e = k["hacim"]
            ayni = (e is None and y.hacim is None) or (
                e is not None and y.hacim is not None and abs(e - y.hacim) <= 1e-9 * e)
            if not ayni:
                farkli.append((ad, mal, e, y.hacim))
    kontrol("%d yanabilir malzeme kaydinda hacim ayni" % sayi, not farkli and sayi > 50,
            "-> %s" % farkli[:3])


def test_ad_cakismasi_hacmi():
    print("\n[GT3] cubukla ayni adli malzeme demet anahtarinda cubugu gosterir (cift sayim yok)")
    from cekirdek import sema, tukenme
    spec = sema.yukle(os.path.join(ORNEK, "pwr_mox_demet.json"))
    hv = tukenme.hacimler(spec)
    c = sema.cubuk_bul(spec, "mox_25")
    d = spec["demetler"][0]
    n = sum(1 for s in d["harita"] for h in s if d["anahtar"].get(h) == "mox_25")
    beklenen = n * math.pi * c["bolgeler"][0]["r"] ** 2
    v = hv["mox_25"]["hacim"]
    kontrol("mox_25: %d pin x pi r^2 = %.6g (olculen %.6g)" % (n, beklenen, v or 0),
            v is not None and abs(v - beklenen) <= 1e-9 * beklenen)


def test_sablon_kare_pin_hacmi():
    print("\n[GT3b] sablon modunda kare/altigen kesitli pin: alan (2r)^2 / (sqrt3/2)(2r)^2")
    from cekirdek import sema, tukenme
    for sekil, carpan in (("kare", 4.0), ("altigen", SQ3 / 2.0 * 4.0)):
        spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
        c = spec["cubuklar"][0]
        c["kesit"] = sekil
        yakit = c["bolgeler"][0]["malzeme"]
        v = tukenme.hacimler(spec)[yakit]["hacim"]
        beklenen = carpan * c["bolgeler"][0]["r"] ** 2 * (sema.model_yuksekligi(spec) or 1.0)
        kontrol("%s pin: %.6g (beklenen %.6g)" % (sekil, v or 0, beklenen),
                v is not None and abs(v - beklenen) <= 1e-9 * beklenen)


def _pin_alani(c, i):
    r = c["bolgeler"][i]["r"]
    r0 = c["bolgeler"][i - 1]["r"] if i else 0.0
    from cekirdek.geometri.kesit import pin_bolge_alani
    s = c.get("kesit") or "silindir"
    return pin_bolge_alani(s, r) - pin_bolge_alani(s, r0)


def test_hacim_agac_duzenekleri():
    print("\n[GT4] agac duzeneklerinde analitik hacim elle hesapla ayni; kesik -> stokastik")
    from cekirdek import geometri, sema
    from cekirdek.geometri import hacim
    # (a): 12 demet_24 x 264 yakit pini (2B, 1 cm)
    spec = go.duzenek_a()
    m = geometri.model(spec)
    c = sema.cubuk_bul(spec, "yakit_24")
    k = hacim.analitik(m, "uo2_24")
    beklenen = 12 * 264 * _pin_alani(c, 0)
    kontrol("(a) uo2_24 = 12 x 264 pin: %.6g" % beklenen,
            k.hacim is not None and abs(k.hacim - beklenen) < 1e-9 * beklenen
            and k.ornek == 12 * 264, "-> %s" % (k,))
    kontrol("(a) kesik blok celigi stokastige duser", hacim.analitik(m, "ss304").yontem
            == hacim.KESIN_DEGIL)
    # (c): 4 tambur emicisi x 200 cm
    spec = go.duzenek_c()
    k = hacim.analitik(geometri.model(spec), "b4c")
    beklenen = 4 * (120.0 / 360.0) * math.pi * (8.0 ** 2 - 6.5 ** 2) * 200.0
    kontrol("(c) b4c = 4 tambur emici yayi: %.6g" % beklenen,
            k.hacim is not None and abs(k.hacim - beklenen) < 1e-9 * beklenen and k.ornek == 4,
            "-> %s" % (k,))
    # (d) kare kesitli pin: (2r)^2 (eski pi r^2 degil)
    spec = go.duzenek_d("kare")
    c = sema.cubuk_bul(spec, "yakit_kare")
    k = hacim.analitik(geometri.model(spec), "uo2_24")
    beklenen = 264 * (2 * c["bolgeler"][0]["r"]) ** 2
    kontrol("(d-kare) uo2 = 264 x (2r)^2: %.6g" % beklenen,
            k.hacim is not None and abs(k.hacim - beklenen) < 1e-9 * beklenen, "-> %s" % (k,))
    # (d) altigen kesitli pin: (sqrt3/2)(2r)^2; butun yakit hucrelere sigar
    spec = go.duzenek_d("altigen")
    c = sema.cubuk_bul(spec, "yakit_altigen")
    d = spec["demetler"][0]
    n = sum(1 for s in d["harita"] for h in s if d["anahtar"].get(h) == "yakit_altigen")
    k = hacim.analitik(geometri.model(spec), "u10mo")
    beklenen = n * SQ3 / 2.0 * (2 * c["bolgeler"][0]["r"]) ** 2
    kontrol("(d-altigen) u10mo = %d x (sqrt3/2)(2r)^2: %.6g" % (n, beklenen),
            k.hacim is not None and abs(k.hacim - beklenen) < 1e-9 * beklenen, "-> %s" % (k,))


def test_basvuru_ve_ad_degistir():
    print("\n[GT5] basvurular + ad_degistir (malzeme, demet, tambur, grup uyesi); saf")
    from cekirdek import geometri, kurucu, sema
    spec = go.duzenek_c()
    bas = geometri.basvurular(spec)
    turler = {(b.tur, b.ad) for b in bas}
    kontrol("basvurular: berilyum malzeme, demet_24 demet, tambur_b4c tambur, grup uyesi",
            {("malzeme", "berilyum"), ("demet", "demet_24"), ("tambur", "tambur_b4c"),
             ("yerlesim", "tamburlar4")} <= turler, "-> %s" % sorted(turler))
    once = copy.deepcopy(spec)
    yeni = geometri.ad_degistir(spec, "malzeme", "berilyum", "be_yans")
    kontrol("ad_degistir saf (girdi degismedi)", spec == once)
    kalan = [b for b in geometri.basvurular(yeni) if b.ad == "berilyum"]
    kontrol("malzeme agacta ve tambur govdesinde degisti",
            not kalan and yeni["tamburlar"][0]["govde_malzeme"] == "be_yans"
            and sema.malzeme_bul(yeni, "be_yans") is not None, "-> %s" % kalan)
    yeni = geometri.ad_degistir(yeni, "demet", "demet_24", "d24")
    yeni = geometri.ad_degistir(yeni, "tambur", "tambur_b4c", "tb")
    yeni = geometri.ad_degistir(yeni, "yerlesim", "tamburlar4", "t4")
    adlar = {(b.tur, b.ad) for b in geometri.basvurular(yeni)}
    kontrol("demet, tambur ve yerlesim/grup adlari degisti",
            {("demet", "d24"), ("tambur", "tb"), ("yerlesim", "t4")} <= adlar
            and not {("demet", "demet_24"), ("tambur", "tambur_b4c")} & adlar, "-> %s" % adlar)
    try:
        model, _b = kurucu.kur(yeni)
        hata = None
    except Exception as e:     # noqa: BLE001 -- test: her hata raporlanir
        hata = "%s: %s" % (type(e).__name__, e)
    kontrol("yeniden adlandirilmis model kurulur", hata is None, "-> %s" % hata)
    try:
        geometri.ad_degistir(spec, "demet", "demet_24", "demet_31")
        cakisma = False
    except ValueError:
        cakisma = True
    kontrol("var olan ada yeniden adlandirma reddedilir", cakisma)
    kullanilan = sema.kullanilan_malzemeler(spec)
    kontrol("kullanilan_malzemeler agac modunda berilyum ve b4c'yi gorur",
            {"berilyum", "b4c"} <= set(kullanilan), "-> %s" % sorted(kullanilan))


def test_sinir_bilgisi():
    print("\n[GT6] sinir_bilgisi: yuzey, yuzler, periyodik uygunluk")
    from cekirdek import geometri, sema
    beklenen = {"b": ("altigen", True), "c": ("silindir", False), "e": ("kare", True),
                "d-kare": ("kare", True)}
    uretici = {"b": go.duzenek_b, "c": go.duzenek_c, "e": go.duzenek_e_ceyrek,
               "d-kare": lambda: go.duzenek_d("kare")}
    for ad, (yuzey, per) in beklenen.items():
        sb = geometri.sinir_bilgisi(geometri.model(uretici[ad]()))
        kontrol("(%s) yuzey %s, periyodik %s" % (ad, yuzey, per),
                sb.yuzey == yuzey and sb.periyodik_uygun == per, "-> %s" % (sb,))
    sb = geometri.sinir_bilgisi(geometri.model(go.duzenek_e_ceyrek()))
    kontrol("(e) yuz basina sinir ve yuz adlari",
            sb.yuzler == {"-x": "reflective", "-y": "reflective", "+x": "vacuum",
                          "+y": "vacuum"} and sb.yuz_adlari == ("-x", "+x", "-y", "+y"))
    for dosya, yuzey in (("zirh_kure.json", "kure"), ("tamburlu_kor.json", "silindir"),
                         ("sfr_met1000_kor.json", None)):
        sb = geometri.sinir_bilgisi(geometri.model(sema.yukle(os.path.join(ORNEK, dosya))))
        kontrol("%s -> %s" % (dosya, sb.yuzey), yuzey is None or sb.yuzey == yuzey,
                "-> %s" % (sb,))
    # dis sinira degen delik: periodic sunulmaz
    spec = go.duzenek_c()
    kok = spec["geometri"]["kok"]
    kok["halkalar"] = [dict(kok["halkalar"][0], dis={"sekil": "dikdortgen",
                                                      "boyut": [140.0, 140.0]})]
    kok["halkalar"][0]["yerlesimler"][0]["merkez_yaricap"] = 60.0
    kok["halkalar"][0]["yerlesimler"][0]["baslangic_acisi"] = 0.0
    kok["halkalar"][0]["yerlesimler"][0]["icerik"] = {"tur": "bilesen", "ad": "tambur_b4c"}
    spec["tamburlar"][0]["yaricap"] = 8.0
    sb = geometri.sinir_bilgisi(geometri.model(spec))
    kok["halkalar"][0]["dis"]["boyut"] = [136.0, 136.0]
    sb2 = geometri.sinir_bilgisi(geometri.model(spec))
    kontrol("uzak delik periyodigi engellemez, degen delik engeller",
            sb.periyodik_uygun and not sb2.periyodik_uygun
            and sb2.dokunan_delikler == ("tamburlar4",), "-> %s | %s" % (sb, sb2))


def test_grup_degeri_yaz():
    print("\n[GT7] grup_degeri_yaz: agacta grup degeri, sablonda kor.tambur.donme")
    from cekirdek import geometri, sema
    spec = go.duzenek_b()
    yeni = geometri.grup_degeri_yaz(spec, "tamburlar", 45.0)
    g = {x["ad"]: x["deger"] for x in yeni["geometri"]["gruplar"]}
    kontrol("agac: grup degeri 45, girdi degismedi",
            g["tamburlar"] == 45.0 and spec["geometri"]["gruplar"][0]["deger"] == 180.0)
    s = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    yeni = geometri.grup_degeri_yaz(s, "tamburlar", 90.0)
    kontrol("sablon: kor.tambur.donme = 90", yeni["kor"]["tambur"]["donme"] == 90.0
            and geometri.gruplar(geometri.model(yeni))[0]["deger"] == 90.0)
    for sp in (spec, s):
        try:
            geometri.grup_degeri_yaz(sp, "yok_boyle", 1.0)
            hata = False
        except KeyError:
            hata = True
        kontrol("tanimsiz grup KeyError", hata)


HIZLI = [test_icerik_sablonla_ayni, test_hacim_sablonla_ayni, test_ad_cakismasi_hacmi,
         test_sablon_kare_pin_hacmi,
         test_hacim_agac_duzenekleri, test_basvuru_ve_ad_degistir, test_sinir_bilgisi,
         test_grup_degeri_yaz]
YAVAS = []
