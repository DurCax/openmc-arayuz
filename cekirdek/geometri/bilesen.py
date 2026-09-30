# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/bilesen.py  --  Kutuphane bilesenleri: cubuk, plaka, demet, tambur
================================================================================

 Her kurucu bir Yapici'ya (geometri/yapici.py) yazar; nesne ve betik ayni
 cagrilari alir. Olculer ve yuzey siralari eski kurucu.cubuk_universe,
 plaka_universe, demet_lattice, altigen_kor.kilifli_demet_universe ve
 tambur.universe ile ayni.

 YAKIT PINI KESITI (§15.3)
   cubuk["kesit"] = "silindir" (varsayilan) | "kare" | "altigen";
   cubuk["kesit_yonelim"] = "x" | "y" (yalniz altigen; HexagonalPrism anlami).
   Bolge "r" alani yari olcudur: silindir yaricap, kare yari kenar (kenar 2r),
   altigen apotem (duz yuzden duz yuze 2r). Butun bolgeler ayni sekilde ic
   icedir; en dis bolge hucrenin geri kalanidir (hucre adimi).
   Altigen pin, yerlestigi altigen kafesin eleman hucresiyle ayni yonde
   olmali: kesit_yonelim = ters(kafes.yonelim) (olculdu:
   testler/test_geometri_yonelim.py).

 KONTROL CUBUGU (§15 karar 5)
   Her yerlesim AYRI bir evrendir (ayri hucre, ayri hacim, ayri ornek):
   ayni tanim distribcell ile paylasilmaz. Daldirma, uyesi oldugu daldirma
   grubunun degeri (yoksa tanimdaki daldirma); modelin aktif eksenel
   araligina gore tanimlidir (R8).
================================================================================
"""

import math

SQ3 = math.sqrt(3.0)
PIN_SEKILLERI = ("silindir", "kare", "altigen")


# ----------------------------------------------------------------------------
# cubuk
# ----------------------------------------------------------------------------

def _pin_yuzeyi(y, sekil, r, yonelim):
    if sekil == "kare":
        return y.dikdortgen_prizma(2.0 * r, 2.0 * r)
    if sekil == "altigen":
        return y.altigen_prizma(2.0 * r / SQ3, yonelim)
    return y.zsilindir(r)


def _radyal(yuzeyler, i, n):
    if i == 0:
        return -yuzeyler[0] if yuzeyler else None
    if i == n - 1:
        return +yuzeyler[-1]
    return +yuzeyler[i - 1] & -yuzeyler[i]


def cubuk(k, c, ad):
    """Cubuk evreni (k: Kurucu). Silindirik yakit cubugu openmc.model.pin."""
    y = k.y
    bolgeler = c["bolgeler"]
    if not bolgeler:
        raise ValueError("'%s' çubuğunda bölge yok" % ad)
    if bolgeler[-1].get("r") is not None:
        raise ValueError("'%s' çubuğu: son bölgenin yarıçapı boş olmalı "
                         "(son bölge çubuğun dışıdır)" % ad)
    sekil = c.get("kesit") or "silindir"
    if sekil not in PIN_SEKILLERI:
        raise ValueError("'%s' çubuğu: bilinmeyen kesit şekli %r" % (ad, sekil))
    yon = c.get("kesit_yonelim") or "y"
    y.yorum("%s — %s kesitli, %d bölge" % (ad, sekil, len(bolgeler)))
    yuzeyler = [_pin_yuzeyi(y, sekil, b["r"], yon) for b in bolgeler[:-1]]
    dolgular = [y.malzeme(b["malzeme"]) for b in bolgeler]
    if c.get("tur") == "kontrol":
        return _kontrol(k, c, ad, yuzeyler, dolgular)
    if sekil == "silindir":
        return y.pin(yuzeyler, dolgular, degisken=k.degisken("c", ad))
    n = len(bolgeler)
    hucreler = [y.hucre(dolgular[i], _radyal(yuzeyler, i, n)) for i in range(n)]
    return y.evren(hucreler, degisken=k.degisken("c", ad))


def _kontrol(k, c, ad, yuzeyler, dolgular):
    """Eksenel hareket eden kontrol cubugu: emici bolge uc duzleminde bolunur."""
    y = k.y
    h = k.yukseklik
    if not h:
        raise ValueError(
            "'%s' kontrol çubuğu 3B model gerektirir: kor yüksekliği tanımlı değil. "
            "Eksenel bir uç konumu olmadan daldırma tanımlanamaz." % ad)
    daldirma = k.daldirma(c)
    if not (0.0 <= daldirma <= 100.0):
        raise ValueError("'%s' kontrol çubuğu: daldırma %%0–%%100 arasında olmalı (%s)"
                         % (ad, daldirma))
    z_alt, z_ust = k.aktif or (-h / 2.0, h / 2.0)
    z_uc = z_ust - (daldirma / 100.0) * (z_ust - z_alt)
    y.yorum("kontrol çubuğu: daldırma %%%.1f -> uç z = %r cm; ucun üstü emici, altı izleyici"
            % (daldirma, z_uc))
    uc = y.zduzlem(z_uc)
    bolgeler = c["bolgeler"]
    emici_ix = int(c.get("emici_bolge") or 0)
    if not (0 <= emici_ix < len(bolgeler)):
        raise ValueError("'%s' kontrol çubuğu: geçersiz emici bölge %d" % (ad, emici_ix + 1))
    izleyici = y.malzeme(c.get("izleyici_malzeme"))
    hucreler = []
    n = len(bolgeler)
    for i in range(n):
        radyal = _radyal(yuzeyler, i, n)
        if i == emici_ix:
            ust = radyal & +uc if radyal is not None else +uc
            alt = radyal & -uc if radyal is not None else -uc
            hucreler.append(y.hucre(dolgular[i], ust))
            hucreler.append(y.hucre(izleyici, alt))
        else:
            hucreler.append(y.hucre(dolgular[i], radyal))
    return y.evren(hucreler, degisken=k.degisken("kc", ad))


# ----------------------------------------------------------------------------
# plaka
# ----------------------------------------------------------------------------

def plaka(k, p, ad):
    """MTR plaka elemani evreni (kurucu.plaka_universe ile ayni yuzeyler)."""
    y = k.y
    n = p["plaka_sayisi"]
    et, zarf, kanal = p["et_kalinlik"], p["zarf_kalinlik"], p["kanal_kalinlik"]
    gen = p["plaka_genislik"]
    yan = p.get("yan_levha_kalinlik", 0.0)
    plaka_kal = 2.0 * zarf + et
    top_x = n * plaka_kal + (n + 1) * kanal
    top_y = gen + 2.0 * yan
    y.yorum("%s — %d plakalı MTR elemanı (%r x %r cm)" % (ad, n, top_x, top_y))
    m_et, m_zarf = y.malzeme(p["et_malzeme"]), y.malzeme(p["zarf_malzeme"])
    m_sog = y.malzeme(p["sogutucu"])
    m_yan = y.malzeme(p.get("yan_levha_malzeme") or p["zarf_malzeme"])
    katmanlar, x = [], -top_x / 2.0
    for _i in range(n):
        for kal, mat in ((kanal, m_sog), (zarf, m_zarf), (et, m_et), (zarf, m_zarf)):
            katmanlar.append((x, x + kal, mat))
            x += kal
    katmanlar.append((x, x + kanal, m_sog))
    y_alt, y_ust = y.yduzlem(-gen / 2.0), y.yduzlem(+gen / 2.0)
    havuz = {}

    def xd(deger):
        a = round(deger, 9)
        if a not in havuz:
            havuz[a] = y.xduzlem(a)
        return havuz[a]

    hucreler = [y.hucre(mat, +xd(x0) & -xd(x1) & +y_alt & -y_ust) for x0, x1, mat in katmanlar]
    if yan > 0:
        x_sol, x_sag = xd(-top_x / 2.0), xd(+top_x / 2.0)
        yy_alt, yy_ust = y.yduzlem(-top_y / 2.0), y.yduzlem(+top_y / 2.0)
        hucreler.append(y.hucre(m_yan, +x_sol & -x_sag & +yy_alt & -y_alt))
        hucreler.append(y.hucre(m_yan, +x_sol & -x_sag & +y_ust & -yy_ust))
    return y.evren(hucreler, degisken=k.degisken("p", ad))


# ----------------------------------------------------------------------------
# demet
# ----------------------------------------------------------------------------

def _kilif(d):
    kf = d.get("kilif") if d.get("tur") == "altigen" else None
    return kf if isinstance(kf, dict) and kf else None


def demet_kafesi(k, d, ad):
    """Demet kafesi (RectLattice / HexLattice). Harf evrenleri paylasilir;
    kontrol cubugu harfleri her konumda ayri evrendir."""
    from cekirdek import altigen
    y = k.y
    anahtar = d.get("anahtar") or {}
    harita = d["harita"]
    if d["tur"] == "kare":
        nx, ny = d["boyut"]
        if len(harita) != ny:
            raise ValueError("'%s' demeti: harita %d satır, boyut %d bekliyor"
                             % (ad, len(harita), ny))
        for satir in harita:
            if len(satir) != nx:
                raise ValueError("'%s' demeti: '%s' satırı %d karakter, %d bekleniyor"
                                 % (ad, satir, len(satir), nx))
    elif d["tur"] == "altigen":
        halka = d.get("halka_sayisi") or d["boyut"][0]
        beklenen = altigen.halka_uzunluklari(halka)
        if len(harita) != len(beklenen):
            raise ValueError("'%s' demeti: %d halka bekleniyor, haritada %d satır var"
                             % (ad, len(beklenen), len(harita)))
        for i, (satir, uzunluk) in enumerate(zip(harita, beklenen)):
            if len(satir) != uzunluk:
                raise ValueError("'%s' demeti: %d. halka (yarıçap %d) %d öğe bekliyor, %d var"
                                 % (ad, i + 1, halka - 1 - i, uzunluk, len(satir)))
    else:
        raise ValueError("bilinmeyen demet türü: %s" % d["tur"])
    for harf in {h for s in harita for h in s}:
        if harf not in anahtar:
            raise KeyError("'%s' demeti: haritada tanımsız harf '%s'" % (ad, harf))
    esleme, ozel = k.harf_evrenleri(harita, {h: anahtar[h] for h in anahtar})
    dis = k.dis_evreni(d.get("dolgu_disi"))
    y.yorum("%s — %s demet, adım %r cm" % (ad, d["tur"], d["adim"]))
    P = d["adim"]
    if d["tur"] == "kare":
        nx, ny = d["boyut"]
        return y.kare_kafes(P, (-P * nx / 2.0, -P * ny / 2.0), harita, esleme, dis, ozel,
                            degisken=k.degisken("d", ad))
    return y.altigen_kafes(P, d.get("yonelim", "y"), harita, esleme, dis, ozel,
                           degisken=k.degisken("d", ad))


def demet_dolgusu(k, d, ad):
    """Demetin dogal dolgusu: kilifsizda ('kafes', lat), kiliflida ('evren', u)."""
    lat = demet_kafesi(k, d, ad)
    kf = _kilif(d)
    if kf is None:
        return ("kafes", lat)
    y = k.y
    yon = d.get("yonelim", "y")
    ic_duz, kal = float(kf["ic_duz"]), float(kf["kalinlik"])
    y.yorum("kılıf (duct): iç düz %r cm, kalınlık %r cm; kılıf pin kafesiyle aynı yönde"
            % (ic_duz, kal))
    ic = y.altigen_prizma(ic_duz / math.sqrt(3.0), yon)
    dis = y.altigen_prizma((ic_duz + 2.0 * kal) / math.sqrt(3.0), yon)
    u = y.evren([y.hucre(lat, -ic, name="kilif ici"),
                 y.hucre(y.malzeme(kf.get("malzeme")), +ic & -dis, name="kilif"),
                 y.hucre(y.malzeme(d.get("dolgu_disi")), +dis, name="demetler arasi")],
                name=ad, degisken=k.degisken("du", ad))
    return ("evren", u)


# ----------------------------------------------------------------------------
# tambur
# ----------------------------------------------------------------------------

def _yari_duzlem(y, aci_derece):
    a = math.radians(aci_derece)
    return y.duzlem(-math.sin(a), math.cos(a), 0.0, 0.0)


def tambur(k, t, ad):
    """Tambur evreni: emici yay YEREL +x yonunde ortalanmis (tambur.universe)."""
    y = k.y
    R = float(t["yaricap"])
    r_ic = float(t.get("emici_ic_yaricap") or 0.0)
    aci = float(t.get("emici_aci") or 120.0)
    y.yorum("%s — tambur r = %r cm, emici yay %r° yerel +x yönünde" % (ad, R, aci))
    dis = y.zsilindir(R)
    govde = y.malzeme(t.get("govde_malzeme"))
    emici = y.malzeme(t.get("emici_malzeme"))
    yari = aci / 2.0
    if r_ic > 0:
        ic = y.zsilindir(r_ic)
        p1, p2 = _yari_duzlem(y, -yari), _yari_duzlem(y, +yari)
        kama = (+p1 & -p2) if aci <= 180.0 else (+p1 | -p2)
        emici_bolge = +ic & -dis & kama
    else:
        p1, p2 = _yari_duzlem(y, -yari), _yari_duzlem(y, +yari)
        kama = (+p1 & -p2) if aci <= 180.0 else (+p1 | -p2)
        emici_bolge = -dis & kama
    return y.evren([y.hucre(emici, emici_bolge),
                    y.hucre(govde, (-dis) & ~emici_bolge),
                    y.hucre(govde, +dis)], degisken=k.degisken("t", ad))
