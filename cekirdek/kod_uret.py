# -*- coding: utf-8 -*-
"""
================================================================================
 kod_uret.py  --  spec -> tek basina calisan Python betigi
================================================================================

 Arayuzde kurulan modeli, elle duzenlenebilir bir OpenMC betigine cevirir.
 Uretilen betik openmc_arayuz'a bagimli DEGILDIR; sadece openmc gerektirir.

 KULLANIM
   from cekirdek import kod_uret, sema
   spec = sema.yukle("ornekler/pwr_pinhucre.json")
   kod = kod_uret.uret(spec)
   open("model.py", "w", encoding="utf-8").write(kod)

 !!! ONEMLI !!!
   Uretilen betik kurucu.py ile AYNI modeli vermek zorundadir. Bunun tek
   gercek kaniti testler/test_regresyon.py icindeki "betik esdegerligi"
   testidir: ayni tohumla iki yol da birebir ayni k-eff vermelidir.
   kurucu.py degistirilirse bu modul de guncellenmeli ve test tekrar kosulmalidir.

 TEK YONLU
   Uretilen betik spec'e geri cevrilemez (keyfi Python cozumlenemez).
   Betik uzerinde calismaya devam edilecekse arayuz tarafi birakilmalidir.
================================================================================
"""

import datetime
import re

from cekirdek import altigen
from cekirdek.sema import BOSLUK, cubuk_bul, plaka_bul, demet_bul

BANNER = "# " + "=" * 74


def _ad(metin, onek="m"):
    """Spec adini gecerli bir Python degisken adina cevirir."""
    temiz = re.sub(r"[^0-9a-zA-Z_]", "_", metin)
    if not temiz or temiz[0].isdigit():
        temiz = onek + "_" + temiz
    return temiz


def _f(deger):
    """Float'i tam duyarlikla yazar (yuvarlama kaybi olmasin)."""
    if deger is None:
        return "None"
    if isinstance(deger, bool):
        return repr(deger)
    if isinstance(deger, float):
        return repr(deger)
    return repr(deger)


def _bolum(satirlar, no, baslik):
    satirlar.append("")
    satirlar.append(BANNER)
    satirlar.append("# %d. %s" % (no, baslik))
    satirlar.append(BANNER)


# ============================================================================
# BOLUMLER
# ============================================================================

def _malzemeler(spec, satirlar):
    _bolum(satirlar, 1, "MALZEMELER")
    adlar = []
    for m in spec["malzemeler"]:
        v = _ad(m["ad"])
        adlar.append(v)
        satirlar.append("")
        satirlar.append("%s = openmc.Material(name=%r)" % (v, m.get("gorunen_ad") or m["ad"]))
        for b in m["bilesim"]:
            birim = b.get("birim", "ao")
            if b.get("tur") == "nuklid":
                satirlar.append("%s.add_nuclide(%r, %s, percent_type=%r)"
                                % (v, b["isim"], _f(b["miktar"]), birim))
            elif b.get("zenginlik") is not None:
                satirlar.append("%s.add_element(%r, %s, percent_type=%r, enrichment=%s)"
                                % (v, b["isim"], _f(b["miktar"]), birim, _f(b["zenginlik"])))
            else:
                satirlar.append("%s.add_element(%r, %s, percent_type=%r)"
                                % (v, b["isim"], _f(b["miktar"]), birim))
        yog = m["yogunluk"]
        satirlar.append("%s.set_density(%r, %s)" % (v, yog["birim"], _f(yog["deger"])))
        if m.get("sicaklik"):
            satirlar.append("%s.temperature = %s" % (v, _f(m["sicaklik"])))
        for s in m.get("sab", []):
            satirlar.append("%s.add_s_alpha_beta(%r)      # termal sacilma" % (v, s))
    satirlar.append("")
    satirlar.append("malzemeler = openmc.Materials([%s])" % ", ".join(adlar))
    return adlar


def _mat_ifade(ad):
    """Malzeme adini betikteki ifadeye cevirir; bosluk -> None (void)."""
    if ad is None or ad == BOSLUK:
        return "None"
    return _ad(ad)


def _cubuk(spec, cubuk_ad, satirlar):
    """Cubuk universe'ini uretir, degisken adini dondurur."""
    c = cubuk_bul(spec, cubuk_ad)
    v = _ad(cubuk_ad, "c")
    yaricaplar = [b["r"] for b in c["bolgeler"][:-1]]
    dolgular = [_mat_ifade(b["malzeme"]) for b in c["bolgeler"]]
    satirlar.append("")
    satirlar.append("# %s -- es merkezli %d bolge" % (cubuk_ad, len(c["bolgeler"])))
    satirlar.append("%s_yuzeyler = [%s]"
                    % (v, ", ".join("openmc.ZCylinder(r=%s)" % _f(r) for r in yaricaplar)))
    if c.get("tur") != "kontrol":
        satirlar.append("%s = openmc.model.pin(%s_yuzeyler, [%s])"
                        % (v, v, ", ".join(dolgular)))
        return v

    # ---- eksenel hareket eden kontrol cubugu ----
    h = spec["kor"].get("yukseklik") or 0.0
    daldirma = float(c.get("daldirma") or 0.0)
    z_uc = h / 2.0 - (daldirma / 100.0) * h
    emici_ix = int(c.get("emici_bolge") or 0)
    satirlar.append("")
    satirlar.append("# Kontrol cubugu: emici bolge UC KONUMUNDA ikiye bolunur.")
    satirlar.append("#   ucun ustu -> emici,  ucun alti -> izleyici")
    satirlar.append("# daldirma %%%.1f  ->  z_uc = %s cm" % (daldirma, _f(z_uc)))
    satirlar.append("%s_uc = openmc.ZPlane(%s)" % (v, _f(z_uc)))
    satirlar.append("%s_hucreler = []" % v)
    n = len(c["bolgeler"])
    for i in range(n):
        if i == 0:
            radyal = "-%s_yuzeyler[0]" % v
        elif i == n - 1:
            radyal = "+%s_yuzeyler[-1]" % v
        else:
            radyal = "+%s_yuzeyler[%d] & -%s_yuzeyler[%d]" % (v, i - 1, v, i)
        if i == emici_ix:
            satirlar.append("%s_hucreler.append(openmc.Cell(fill=%s, region=(%s) & +%s_uc))"
                            % (v, dolgular[i], radyal, v))
            satirlar.append("%s_hucreler.append(openmc.Cell(fill=%s, region=(%s) & -%s_uc))"
                            % (v, _mat_ifade(c.get("izleyici_malzeme")), radyal, v))
        else:
            satirlar.append("%s_hucreler.append(openmc.Cell(fill=%s, region=%s))"
                            % (v, dolgular[i], radyal))
    satirlar.append("%s = openmc.Universe(cells=%s_hucreler)" % (v, v))
    return v


def _plaka(spec, plaka_ad, satirlar):
    """MTR plaka elemani universe'ini uretir."""
    p = plaka_bul(spec, plaka_ad)
    v = _ad(plaka_ad, "p")
    satirlar.append("")
    satirlar.append("# %s -- %d plakali MTR elemani" % (plaka_ad, p["plaka_sayisi"]))
    satirlar.append("N_PLAKA   = %s" % _f(p["plaka_sayisi"]))
    satirlar.append("ET        = %-12s # cm   yakit eti kalinligi" % _f(p["et_kalinlik"]))
    satirlar.append("ZARF      = %-12s # cm   her yuzdeki zarf" % _f(p["zarf_kalinlik"]))
    satirlar.append("KANAL     = %-12s # cm   plakalar arasi sogutucu" % _f(p["kanal_kalinlik"]))
    satirlar.append("GENISLIK  = %-12s # cm   aktif genislik (y)" % _f(p["plaka_genislik"]))
    satirlar.append("YAN_LEVHA = %-12s # cm   yan levha kalinligi" % _f(p.get("yan_levha_kalinlik", 0.0)))
    satirlar.append("")
    satirlar.append("PLAKA_KAL = 2.0 * ZARF + ET")
    satirlar.append("TOP_X = N_PLAKA * PLAKA_KAL + (N_PLAKA + 1) * KANAL")
    satirlar.append("TOP_Y = GENISLIK + 2.0 * YAN_LEVHA")
    satirlar.append("")
    satirlar.append("_xd = {}")
    satirlar.append("def _x(deger):")
    satirlar.append("    \"\"\"Ayni x degeri icin tek bir XPlane paylas.\"\"\"")
    satirlar.append("    a = round(deger, 9)")
    satirlar.append("    if a not in _xd:")
    satirlar.append("        _xd[a] = openmc.XPlane(a)")
    satirlar.append("    return _xd[a]")
    satirlar.append("")
    satirlar.append("_y_alt = openmc.YPlane(-GENISLIK / 2.0)")
    satirlar.append("_y_ust = openmc.YPlane(+GENISLIK / 2.0)")
    satirlar.append("")
    satirlar.append("%s_hucreler = []" % v)
    satirlar.append("_x_imlec = -TOP_X / 2.0")
    satirlar.append("for _i in range(N_PLAKA):")
    satirlar.append("    for _kal, _mat in ((KANAL, %s), (ZARF, %s), (ET, %s), (ZARF, %s)):"
                    % (_mat_ifade(p["sogutucu"]), _mat_ifade(p["zarf_malzeme"]),
                       _mat_ifade(p["et_malzeme"]), _mat_ifade(p["zarf_malzeme"])))
    satirlar.append("        _b = +_x(_x_imlec) & -_x(_x_imlec + _kal) & +_y_alt & -_y_ust")
    satirlar.append("        %s_hucreler.append(openmc.Cell(fill=_mat, region=_b))" % v)
    satirlar.append("        _x_imlec += _kal")
    satirlar.append("_b = +_x(_x_imlec) & -_x(_x_imlec + KANAL) & +_y_alt & -_y_ust")
    satirlar.append("%s_hucreler.append(openmc.Cell(fill=%s, region=_b))"
                    % (v, _mat_ifade(p["sogutucu"])))
    if p.get("yan_levha_kalinlik", 0.0) > 0:
        yan_mat = _mat_ifade(p.get("yan_levha_malzeme") or p["zarf_malzeme"])
        satirlar.append("")
        satirlar.append("# yan levhalar")
        satirlar.append("_x_sol, _x_sag = _x(-TOP_X / 2.0), _x(+TOP_X / 2.0)")
        satirlar.append("_yy_alt = openmc.YPlane(-TOP_Y / 2.0)")
        satirlar.append("_yy_ust = openmc.YPlane(+TOP_Y / 2.0)")
        satirlar.append("%s_hucreler.append(openmc.Cell(fill=%s, "
                        "region=+_x_sol & -_x_sag & +_yy_alt & -_y_alt))" % (v, yan_mat))
        satirlar.append("%s_hucreler.append(openmc.Cell(fill=%s, "
                        "region=+_x_sol & -_x_sag & +_y_ust & -_yy_ust))" % (v, yan_mat))
    satirlar.append("")
    satirlar.append("%s = openmc.Universe(cells=%s_hucreler)" % (v, v))
    return v


def _bagimliliklar(spec, ad, satirlar, uretilen):
    """Bir adin (cubuk/plaka/demet/malzeme) universe'ini gerektiginde uretir."""
    if ad in uretilen:
        return uretilen[ad]
    if cubuk_bul(spec, ad) is not None:
        uretilen[ad] = _cubuk(spec, ad, satirlar)
    elif plaka_bul(spec, ad) is not None:
        uretilen[ad] = _plaka(spec, ad, satirlar)
    elif demet_bul(spec, ad) is not None:
        uretilen[ad] = _demet(spec, ad, satirlar, uretilen, sarmala=True)
    else:
        v = _ad(ad, "u")
        satirlar.append("")
        satirlar.append("%s = openmc.Universe(cells=[openmc.Cell(fill=%s)])"
                        % (v, _mat_ifade(ad)))
        uretilen[ad] = v
    return uretilen[ad]


def _demet(spec, demet_ad, satirlar, uretilen, sarmala=False):
    """Kafes uretir. sarmala=True ise Universe'e sarilir."""
    d = demet_bul(spec, demet_ad)
    v = _ad(demet_ad, "d")
    for harf, hedef in sorted(d["anahtar"].items()):
        _bagimliliklar(spec, hedef, satirlar, uretilen)

    satirlar.append("")
    satirlar.append("# %s -- %s kafes, adim %s cm" % (demet_ad, d["tur"], _f(d["adim"])))
    satirlar.append("%s_disi = openmc.Universe(cells=[openmc.Cell(fill=%s)])"
                    % (v, _mat_ifade(d.get("dolgu_disi"))))
    if d["tur"] == "kare":
        nx, ny = d["boyut"]
        satirlar.append("%s = openmc.RectLattice()" % v)
        satirlar.append("%s.pitch = (%s, %s)" % (v, _f(d["adim"]), _f(d["adim"])))
        satirlar.append("%s.lower_left = (%s, %s)"
                        % (v, _f(-d["adim"] * nx / 2.0), _f(-d["adim"] * ny / 2.0)))
        satirlar.append("%s.outer = %s_disi" % (v, v))
        satirlar.append("")
        satirlar.append("# kafes haritasi (%d x %d)" % (nx, ny))
        for harf, hedef in sorted(d["anahtar"].items()):
            satirlar.append("#   '%s' -> %s" % (harf, hedef))
        satirlar.append("_harita = [")
        for satir in d["harita"]:
            satirlar.append("    %r," % satir)
        satirlar.append("]")
        satirlar.append("_anahtar = {%s}"
                        % ", ".join("%r: %s" % (h, uretilen[t])
                                    for h, t in sorted(d["anahtar"].items())))
        satirlar.append("%s.universes = [[_anahtar[_h] for _h in _s] for _s in _harita]" % v)
    else:
        halka = d.get("halka_sayisi") or d["boyut"][0]
        satirlar.append("# halkalar DISTAN ICE; her halka tepeden saat yonunde")
        satirlar.append("# yaricapi k olan halkada 6k oge, merkezde 1 oge")
        satirlar.append("%s = openmc.HexLattice()" % v)
        satirlar.append("%s.center = (0.0, 0.0)" % v)
        satirlar.append("%s.pitch = (%s,)" % (v, _f(d["adim"])))
        satirlar.append("%s.orientation = %r" % (v, d.get("yonelim", "y")))
        satirlar.append("%s.outer = %s_disi" % (v, v))
        satirlar.append("_harita = [   # %d halka" % halka)
        for i, satir in enumerate(d["harita"]):
            # !!! VIRGUL SART !!! virgulsuz ardarda string literal'leri Python
            # ortuk olarak birlestirir ve harita tek bir dizeye cokup sessizce
            # yanlis kafes uretir.
            satirlar.append("    %-*s  # yaricap %d, %d oge"
                            % (max(len(repr(s)) for s in d["harita"]) + 2,
                               repr(satir) + ",", halka - 1 - i, len(satir)))
        satirlar.append("]")
        satirlar.append("_anahtar = {%s}"
                        % ", ".join("%r: %s" % (h, uretilen[t])
                                    for h, t in sorted(d["anahtar"].items())))
        satirlar.append("%s.universes = [[_anahtar[_h] for _h in _s] for _s in _harita]" % v)

    if sarmala:
        vs = v + "_u"
        satirlar.append("%s = openmc.Universe(cells=[openmc.Cell(fill=%s)])" % (vs, v))
        return vs
    return v


def _geometri(spec, satirlar):
    """
    Kor duzenini uretir.
    DONER (gx, gy, uretilen) -- uretilen: {spec_adi: betikteki degisken adi}
    Guc dagilimi tally'si hedef cubugun betikteki degisken adina ihtiyac duyar.
    """
    _bolum(satirlar, 2, "GEOMETRI")
    kor = spec["kor"]
    tur = kor["tur"]
    uretilen = {}

    if tur == "tek_cubuk":
        ic = _cubuk(spec, kor["cubuk"], satirlar)
        uretilen[kor["cubuk"]] = ic
        gx = gy = kor["adim"]
    elif tur == "tek_plaka":
        ic = _plaka(spec, kor["plaka"], satirlar)
        uretilen[kor["plaka"]] = ic
        p = plaka_bul(spec, kor["plaka"])
        gx = (p["plaka_sayisi"] * (2 * p["zarf_kalinlik"] + p["et_kalinlik"])
              + (p["plaka_sayisi"] + 1) * p["kanal_kalinlik"])
        gy = p["plaka_genislik"] + 2 * p.get("yan_levha_kalinlik", 0.0)
    elif tur == "tek_demet":
        ic = _demet(spec, kor["demet"], satirlar, uretilen)
        d = demet_bul(spec, kor["demet"])
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or d["boyut"][0]
            gx, gy = altigen.kapsayan_olcu(halka, d["adim"], d.get("yonelim", "y"))
        else:
            gx, gy = d["adim"] * d["boyut"][0], d["adim"] * d["boyut"][1]
    elif tur == "kuresel":
        kabuklar = kor.get("kabuklar") or []
        satirlar.append("")
        satirlar.append("# Es merkezli kuresel kabuklar (icten disa).")
        satirlar.append("# En dis kabugun yuzeyi modelin sinir yuzeyidir.")
        sinir_bc = (kor.get("sinir") or {}).get("yan", "vacuum")
        satirlar.append("_kure_hucreler = []")
        satirlar.append("_onceki = None")
        for i, k in enumerate(kabuklar):
            son = (i == len(kabuklar) - 1)
            bc = ", boundary_type=%r" % sinir_bc if son else ""
            satirlar.append("_y%d = openmc.Sphere(r=%s%s)" % (i, _f(k["r"]), bc))
            if i == 0:
                satirlar.append("_kure_hucreler.append(openmc.Cell(fill=%s, region=-_y0))"
                                % _mat_ifade(k.get("malzeme")))
            else:
                satirlar.append("_kure_hucreler.append(openmc.Cell(fill=%s, "
                                "region=+_y%d & -_y%d))"
                                % (_mat_ifade(k.get("malzeme")), i - 1, i))
        satirlar.append("kok = openmc.Universe(cells=_kure_hucreler)")
        satirlar.append("")
        satirlar.append("geometri = openmc.Geometry(kok)")
        capi = 2.0 * (kabuklar[-1]["r"] if kabuklar else 1.0)
        return capi, capi, uretilen

    elif tur == "kare_kafes":
        for harf, hedef in sorted(kor["anahtar"].items()):
            _bagimliliklar(spec, hedef, satirlar, uretilen)
        nx, ny = kor["boyut"]
        satirlar.append("")
        satirlar.append("# kor kafesi (%d x %d demet), adim %s cm" % (nx, ny, _f(kor["adim"])))
        satirlar.append("kor_disi = openmc.Universe(cells=[openmc.Cell(fill=%s)])"
                        % _mat_ifade((kor.get("yansitici") or {}).get("malzeme")))
        satirlar.append("kor_kafes = openmc.RectLattice()")
        satirlar.append("kor_kafes.pitch = (%s, %s)" % (_f(kor["adim"]), _f(kor["adim"])))
        satirlar.append("kor_kafes.lower_left = (%s, %s)"
                        % (_f(-kor["adim"] * nx / 2.0), _f(-kor["adim"] * ny / 2.0)))
        satirlar.append("kor_kafes.outer = kor_disi")
        satirlar.append("_kor_harita = [")
        for satir in kor["harita"]:
            satirlar.append("    %r," % satir)
        satirlar.append("]")
        satirlar.append("_kor_anahtar = {%s}"
                        % ", ".join("%r: %s" % (h, uretilen[t])
                                    for h, t in sorted(kor["anahtar"].items())))
        satirlar.append("kor_kafes.universes = "
                        "[[_kor_anahtar[_h] for _h in _s] for _s in _kor_harita]")
        ic = "kor_kafes"
        gx, gy = kor["adim"] * nx, kor["adim"] * ny
    else:
        raise ValueError("bilinmeyen kor turu: %s" % tur)

    # --- sinir ve kok universe ---
    sinir = kor.get("sinir") or {}
    yan_bc = sinir.get("yan", "reflective")
    h = kor.get("yukseklik")
    yans = kor.get("yansitici") or {}

    satirlar.append("")
    satirlar.append("# --- sinirlar ve kok universe ---")
    if h:
        satirlar.append("z_alt = openmc.ZPlane(%s, boundary_type=%r)"
                        % (_f(-h / 2.0), sinir.get("alt", "reflective")))
        satirlar.append("z_ust = openmc.ZPlane(%s, boundary_type=%r)"
                        % (_f(+h / 2.0), sinir.get("ust", "reflective")))
        eksen = " & +z_alt & -z_ust"
    else:
        satirlar.append("# yukseklik verilmemis -> eksenel yonde sonsuz (2B)")
        eksen = ""

    # --- altigen kor: HexagonalPrism sinirlari ---
    hex_demet = None
    if tur == "tek_demet":
        _d = demet_bul(spec, kor["demet"])
        if _d.get("tur") == "altigen":
            hex_demet = _d
    if hex_demet is not None:
        halka = hex_demet.get("halka_sayisi") or hex_demet["boyut"][0]
        yonelim = hex_demet.get("yonelim", "y")
        adim = hex_demet["adim"]
        satirlar.append("")
        satirlar.append("# Altigen duct. HexLattice ve HexagonalPrism yonelimleri AYNIDIR:")
        satirlar.append("# kafes 'y' -> zarf tepede sivri, sag/solda duz; prizma 'y' de oyle.")
        satirlar.append("# apothem = (halka-1)*adim*sqrt(3)/2 + adim/2   (yarim adim aciklik)")
        satirlar.append("import math")
        satirlar.append("_apothem = (%s - 1) * %s * math.sqrt(3) / 2 + %s / 2"
                        % (_f(halka), _f(adim), _f(adim)))
        if yans.get("var"):
            satirlar.append("_ic_prizma = openmc.model.HexagonalPrism("
                            "edge_length=2*_apothem/math.sqrt(3), orientation=%r)" % yonelim)
            satirlar.append("_dis_prizma = openmc.model.HexagonalPrism("
                            "edge_length=2*(_apothem + %s)/math.sqrt(3), orientation=%r, "
                            "boundary_type=%r)" % (_f(yans["kalinlik"]), yonelim, yan_bc))
            satirlar.append("kok = openmc.Universe(cells=[")
            satirlar.append("    openmc.Cell(fill=%s, region=-_ic_prizma%s)," % (ic, eksen))
            satirlar.append("    openmc.Cell(fill=%s, region=+_ic_prizma & -_dis_prizma%s),"
                            % (_mat_ifade(yans.get("malzeme")), eksen))
            satirlar.append("])")
            gx, gy = gx + 2 * yans["kalinlik"], gy + 2 * yans["kalinlik"]
        else:
            satirlar.append("_prizma = openmc.model.HexagonalPrism("
                            "edge_length=2*_apothem/math.sqrt(3), orientation=%r, "
                            "boundary_type=%r)" % (yonelim, yan_bc))
            satirlar.append("kok = openmc.Universe(cells=["
                            "openmc.Cell(fill=%s, region=-_prizma%s)])" % (ic, eksen))
        satirlar.append("")
        satirlar.append("geometri = openmc.Geometry(kok)")
        return gx, gy, uretilen

    if yans.get("var") and tur in ("tek_demet", "kare_kafes"):
        kal = yans["kalinlik"]
        dgx, dgy = gx + 2 * kal, gy + 2 * kal
        satirlar.append("ic_kutu  = openmc.model.RectangularPrism(%s, %s)" % (_f(gx), _f(gy)))
        satirlar.append("dis_kutu = openmc.model.RectangularPrism(%s, %s, boundary_type=%r)"
                        % (_f(dgx), _f(dgy), yan_bc))
        satirlar.append("kok = openmc.Universe(cells=[")
        satirlar.append("    openmc.Cell(fill=%s, region=-ic_kutu%s)," % (ic, eksen))
        satirlar.append("    openmc.Cell(fill=%s, region=+ic_kutu & -dis_kutu%s),"
                        % (_mat_ifade(yans.get("malzeme")), eksen))
        satirlar.append("])")
        gx, gy = dgx, dgy
    else:
        satirlar.append("kutu = openmc.model.RectangularPrism(%s, %s, boundary_type=%r)"
                        % (_f(gx), _f(gy), yan_bc))
        satirlar.append("kok = openmc.Universe(cells=[openmc.Cell(fill=%s, region=-kutu%s)])"
                        % (ic, eksen))
    satirlar.append("")
    satirlar.append("geometri = openmc.Geometry(kok)")
    return gx, gy, uretilen


def _ayarlar(spec, satirlar, gx, gy):
    _bolum(satirlar, 3, "AYARLAR")
    a = spec["ayarlar"]
    satirlar.append("")
    satirlar.append("ayar = openmc.Settings()")
    satirlar.append("ayar.run_mode  = %r" % a.get("mod", "eigenvalue"))
    satirlar.append("ayar.particles = %-10s # cevrim basina parcacik" % _f(int(a["parcacik"])))
    satirlar.append("ayar.batches   = %-10s # toplam cevrim" % _f(int(a["cevrim"])))
    if a.get("mod", "eigenvalue") == "eigenvalue":
        satirlar.append("ayar.inactive  = %-10s # pasif cevrim" % _f(int(a["pasif"])))
    if a.get("tohum"):
        satirlar.append("ayar.seed      = %s" % _f(int(a["tohum"])))
    if a.get("sicaklik_yontemi"):
        satirlar.append("ayar.temperature = {'method': %r}" % a["sicaklik_yontemi"])

    k = a.get("kaynak") or {}
    satirlar.append("")
    if k.get("tur") == "kutu":
        # Z araligi modelin yuksekligini kapsamali (bkz. kurucu.py notu):
        # dar bir baslangic kutusu eksenel sekli yanlis yakinsatir.
        _h = spec["kor"].get("yukseklik")
        _yari_z = (_h / 2.0) if _h else 1.0
        alt = k.get("alt") or [-gx / 2, -gy / 2, -_yari_z]
        ust = k.get("ust") or [+gx / 2, +gy / 2, +_yari_z]
        satirlar.append("_uzay = openmc.stats.Box(%r, %r)"
                        % (list(alt), list(ust)))
        satirlar.append("_kisit = {'fissionable': True}   # kaynak sadece fisil bolgelerde")
    else:
        satirlar.append("_uzay = openmc.stats.Point(%r)"
                        % (tuple(k.get("konum") or (0.0, 0.0, 0.0)),))
        satirlar.append("_kisit = None")
    satirlar.append("ayar.source = openmc.IndependentSource(space=_uzay,")
    satirlar.append("                                       energy=openmc.stats.Watt(),")
    satirlar.append("                                       constraints=_kisit)")
    ent = a.get("entropi_mesh") or {}
    if ent.get("var") and a.get("mod", "eigenvalue") == "eigenvalue":
        satirlar.append("")
        satirlar.append("# Shannon entropisi mesh'i -- kaynak yakinsamasini olcer.")
        satirlar.append("# Entropi pasif cevrimler boyunca kayiyorsa pasif cevrim")
        satirlar.append("# sayisi yetersizdir ve k-eff yanli cikar.")
        satirlar.append("_ent_mesh = openmc.RegularMesh()")
        satirlar.append("_ent_mesh.dimension = %r" % (list(ent.get("boyut") or [8, 8, 1]),))
        satirlar.append("_ent_mesh.lower_left  = (%s, %s, -1.0e10)" % (_f(-gx/2.0), _f(-gy/2.0)))
        satirlar.append("_ent_mesh.upper_right = (%s, %s, +1.0e10)" % (_f(gx/2.0), _f(gy/2.0)))
        satirlar.append("ayar.entropy_mesh = _ent_mesh")


def _guc_dagilimi(spec, satirlar, uretilen, gx, gy):
    """Cubuk bazli guc dagilimi tally'sini uretir; tally degisken adlarini dondurur."""
    g = spec.get("guc_dagilimi") or {}
    if not g.get("var"):
        return []
    cubuk_ad = g.get("cubuk")
    degisken = uretilen.get(cubuk_ad)
    if degisken is None:
        satirlar.append("")
        satirlar.append("# UYARI: guc dagilimi icin '%s' cubugu geometride" % cubuk_ad)
        satirlar.append("# bulunamadi; tally uretilmedi.")
        return []

    bolge = int(g.get("bolge") or 0)
    satirlar.append("")
    satirlar.append("# --- cubuk bazli guc dagilimi ---")
    satirlar.append("# pin() hucreleri BOLGE SIRASINDA olusturur, bu yuzden id'ye")
    satirlar.append("# gore siralamak bolge sirasini verir.")
    satirlar.append("_guc_hucreler = sorted(%s.cells.values(), key=lambda c: c.id)" % degisken)
    satirlar.append("_guc_hedef = _guc_hucreler[%d]" % bolge)
    satirlar.append("guc_tally = openmc.Tally(name='guc_dagilimi')")
    satirlar.append("guc_tally.scores = [%r]" % (g.get("skor") or "kappa-fission"))
    satirlar.append("_guc_filtreler = [openmc.DistribcellFilter(_guc_hedef)]")

    h = spec["kor"].get("yukseklik")
    dilim = int(g.get("eksenel_dilim") or 1)
    if h and dilim > 1:
        pay = max(gx, gy)
        satirlar.append("")
        satirlar.append("# Eksenel mesh AKTIF YAKIT YUKSEKLIGIYLE tam ortusmelidir;")
        satirlar.append("# tasarsa bos bin'ler ortalamayi duserir ve F_q sisrer.")
        satirlar.append("_guc_mesh = openmc.RegularMesh()")
        satirlar.append("_guc_mesh.dimension   = [1, 1, %d]" % dilim)
        satirlar.append("_guc_mesh.lower_left  = (%s, %s, %s)" % (_f(-pay), _f(-pay), _f(-h/2.0)))
        satirlar.append("_guc_mesh.upper_right = (%s, %s, %s)" % (_f(pay), _f(pay), _f(h/2.0)))
        satirlar.append("_guc_filtreler.append(openmc.MeshFilter(_guc_mesh))")
    satirlar.append("guc_tally.filters = _guc_filtreler")
    satirlar.append("")
    satirlar.append("# Toplam korunumu kontrolu icin filtresiz esdes tally")
    satirlar.append("guc_ref = openmc.Tally(name='guc_toplam_ref')")
    satirlar.append("guc_ref.scores = list(guc_tally.scores)")
    return ["guc_tally", "guc_ref"]


def _tallyler(spec, satirlar, ek_tallyler=None, on_satirlar=None):
    ek_tallyler = list(ek_tallyler or [])
    if not spec.get("tallyler") and not ek_tallyler:
        return
    _bolum(satirlar, 4, "TALLY'LER")
    satirlar.extend(on_satirlar or [])
    adlar = []
    for i, t in enumerate(spec["tallyler"]):
        v = "tally_%d" % (i + 1)
        adlar.append(v)
        satirlar.append("")
        satirlar.append("%s = openmc.Tally(name=%r)" % (v, t["ad"]))
        satirlar.append("%s.scores = %r" % (v, list(t["skorlar"])))
        if t.get("nuklidler"):
            satirlar.append("%s.nuclides = %r" % (v, list(t["nuklidler"])))
        filtre_ifadeleri = []
        for j, f in enumerate(t.get("filtreler", [])):
            if f["tur"] == "enerji":
                filtre_ifadeleri.append("openmc.EnergyFilter(%r)" % list(f["gruplar"]))
            elif f["tur"] == "mesh":
                mv = "%s_mesh_%d" % (v, j)
                satirlar.append("%s = openmc.RegularMesh()" % mv)
                satirlar.append("%s.dimension  = %r" % (mv, list(f["boyut"])))
                satirlar.append("%s.lower_left = %r" % (mv, list(f["alt"])))
                satirlar.append("%s.upper_right = %r" % (mv, list(f["ust"])))
                filtre_ifadeleri.append("openmc.MeshFilter(%s)" % mv)
            elif f["tur"] == "malzeme":
                filtre_ifadeleri.append("openmc.MaterialFilter([%s])"
                                        % ", ".join(_ad(a) for a in f["adlar"]))
        if filtre_ifadeleri:
            satirlar.append("%s.filters = [%s]" % (v, ", ".join(filtre_ifadeleri)))
    satirlar.append("")
    satirlar.append("tallyler = openmc.Tallies([%s])" % ", ".join(adlar + ek_tallyler))


def _kapanis(spec, satirlar, renkli):
    _bolum(satirlar, 5, "MODEL VE CALISTIRMA")
    tallyler = ("tallyler" if (spec.get("tallyler")
                or (spec.get("guc_dagilimi") or {}).get("var"))
                else "openmc.Tallies()")
    satirlar.append("")
    satirlar.append("model = openmc.Model(geometry=geometri, materials=malzemeler,")
    satirlar.append("                     settings=ayar, tallies=%s)" % tallyler)
    if renkli:
        satirlar.append("")
        satirlar.append("# Model.plot() SVG renk adi ya da (R,G,B) demeti ister -- hex dize KABUL ETMEZ")
        satirlar.append("renkler = {")
        for m in spec["malzemeler"]:
            if m.get("renk"):
                satirlar.append("    %s: %r," % (_ad(m["ad"]), tuple(m["renk"])))
        satirlar.append("}")
    satirlar.append("")
    satirlar.append("if __name__ == '__main__':")
    satirlar.append("    import matplotlib.pyplot as plt")
    satirlar.append("")
    satirlar.append("    # --- ONCE CIZ, SONRA CALISTIR ---")
    satirlar.append("    # Geometri dogru gorunmeden kosu baslatmak zaman kaybidir.")
    satirlar.append("    for _eksen in ('xy',):")
    satirlar.append("        _ax = model.plot(basis=_eksen, color_by='material',")
    satirlar.append("                         colors=%s pixels=(600, 600))"
                    % ("renkler," if renkli else "None,"))
    satirlar.append("        _ax.get_figure().savefig('geometri_%s.png' % _eksen, dpi=110)")
    satirlar.append("        print('cizildi: geometri_%s.png' % _eksen)")
    satirlar.append("")
    satirlar.append("    # Plotlar dogruysa asagidaki satirin yorumunu kaldirin.")
    satirlar.append("    # sp = model.run(threads=%d)" % spec["calistirma"].get("is_parcacigi", 8))
    satirlar.append("    # print(openmc.StatePoint(sp).keff)")


# ============================================================================
# ANA GIRIS
# ============================================================================

def uret(spec, kaynak_dosya=None, renkli=True):
    """Spec'ten tek basina calisan Python betigi metni uretir."""
    tarih = datetime.date.today().isoformat()
    satirlar = [
        "# -*- coding: utf-8 -*-",
        '"""',
        "=" * 78,
        " %s" % spec.get("ad", "isimsiz model"),
        "=" * 78,
    ]
    if spec.get("aciklama"):
        for satir in spec["aciklama"].split("\n"):
            satirlar.append(" %s" % satir)
        satirlar.append("")
    satirlar += [
        " Bu betik openmc_arayuz tarafindan uretilmistir (%s)." % tarih,
    ]
    if kaynak_dosya:
        satirlar.append(" Kaynak spec: %s" % kaynak_dosya)
    satirlar += [
        "",
        " Betik tek basina calisir; openmc_arayuz'a bagimli degildir.",
        " Elle duzenlenebilir, ancak arayuze GERI YUKLENEMEZ.",
        "",
        " KULLANIM",
        "   python3 %s" % (kaynak_dosya or "model.py"),
        "=" * 78,
        '"""',
        "",
        "import openmc",
    ]

    _malzemeler(spec, satirlar)
    gx, gy, uretilen = _geometri(spec, satirlar)
    _ayarlar(spec, satirlar, gx, gy)
    guc_satirlari = []
    ek = _guc_dagilimi(spec, guc_satirlari, uretilen, gx, gy)
    _tallyler(spec, satirlar, ek_tallyler=ek, on_satirlar=guc_satirlari)
    _kapanis(spec, satirlar, renkli)
    satirlar.append("")
    return "\n".join(satirlar)
