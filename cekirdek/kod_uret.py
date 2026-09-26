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
from cekirdek import sema
from cekirdek import kaynak as _kaynak
from cekirdek.sema import BOSLUK, cubuk_bul, plaka_bul, demet_bul

BANNER = "# " + "=" * 74


# Spec adlarindan uretilen degiskenler TURE GORE onek alir (m_ malzeme,
# c_ cubuk, p_ plaka, d_ demet, u_ malzeme/cubuk sarmalayan universe) ve
# uret() boyunca bir kayitla BENZERSIZ tutulur. Eskiden ad aynen degisken
# oluyordu (olculdu, testler/test_butunlesme.py):
#   'a b' ve 'a_b' malzemeleri ayni degiskene dusup betikte iki malzeme
#   karisiyordu -- betik SESSIZCE farkli geometri kuruyordu;
#   'class', 'None', 'openmc', 'malzemeler' adli malzemeler betigi
#   calismaz yapiyordu (SyntaxError / ic degiskenin ustune yazma).
# Betigin ic adlari (ayar, geometri, kok, _harita...) bu oneklerle baslamaz.
_TUREV_EKLERI = ("_yuzeyler", "_hucreler", "_disi", "_u", "_uc")
_KAYIT = None                          # uret() icinde: {"esle": {}, "kullanilan": set()}


def _cakisiyor(aday, kullanilan):
    if aday in kullanilan:
        return True
    for k in kullanilan:
        for ek in _TUREV_EKLERI:
            if aday == k + ek or k == aday + ek:
                return True
    return False


def _ad(metin, onek="m"):
    """Spec adini betikte (tur onekli, benzersiz) bir degisken adina cevirir."""
    temiz = re.sub(r"[^0-9a-zA-Z_]", "_", str(metin))
    taban = "%s_%s" % (onek, temiz)
    if _KAYIT is None:
        return taban
    anahtar = (onek, metin)
    if anahtar in _KAYIT["esle"]:
        return _KAYIT["esle"][anahtar]
    aday, i = taban, 2
    while _cakisiyor(aday, _KAYIT["kullanilan"]):
        aday = "%s_%d" % (taban, i)
        i += 1
    _KAYIT["esle"][anahtar] = aday
    _KAYIT["kullanilan"].add(aday)
    return aday


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
            satirlar.append("%s.add_s_alpha_beta(%r)      # termal saçılma" % (v, s))
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
    satirlar.append("# %s — eş merkezli %d bölge" % (cubuk_ad, len(c["bolgeler"])))
    satirlar.append("%s_yuzeyler = [%s]"
                    % (v, ", ".join("openmc.ZCylinder(r=%s)" % _f(r) for r in yaricaplar)))
    if c.get("tur") != "kontrol":
        satirlar.append("%s = openmc.model.pin(%s_yuzeyler, [%s])"
                        % (v, v, ", ".join(dolgular)))
        return v

    # ---- eksenel hareket eden kontrol cubugu ----
    h = sema.kor_yuksekligi(spec["kor"]) or 0.0
    daldirma = float(c.get("daldirma") or 0.0)
    z_uc = h / 2.0 - (daldirma / 100.0) * h
    emici_ix = int(c.get("emici_bolge") or 0)
    satirlar.append("")
    satirlar.append("# Kontrol çubuğu: emici bölge uç konumunda ikiye bölünür.")
    satirlar.append("#   ucun üstü -> emici,  ucun altı -> izleyici")
    satirlar.append("# daldırma %%%.1f  ->  z_uc = %s cm" % (daldirma, _f(z_uc)))
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
    satirlar.append("# %s — %d plakalı MTR elemanı" % (plaka_ad, p["plaka_sayisi"]))
    satirlar.append("N_PLAKA   = %s" % _f(p["plaka_sayisi"]))
    satirlar.append("ET        = %-12s # cm   yakıt eti kalınlığı" % _f(p["et_kalinlik"]))
    satirlar.append("ZARF      = %-12s # cm   her yüzdeki zarf" % _f(p["zarf_kalinlik"]))
    satirlar.append("KANAL     = %-12s # cm   plakalar arası soğutucu" % _f(p["kanal_kalinlik"]))
    satirlar.append("GENISLIK  = %-12s # cm   aktif genişlik (y)" % _f(p["plaka_genislik"]))
    satirlar.append("YAN_LEVHA = %-12s # cm   yan levha kalınlığı" % _f(p.get("yan_levha_kalinlik", 0.0)))
    satirlar.append("")
    satirlar.append("PLAKA_KAL = 2.0 * ZARF + ET")
    satirlar.append("TOP_X = N_PLAKA * PLAKA_KAL + (N_PLAKA + 1) * KANAL")
    satirlar.append("TOP_Y = GENISLIK + 2.0 * YAN_LEVHA")
    satirlar.append("")
    satirlar.append("_xd = {}")
    satirlar.append("def _x(deger):")
    satirlar.append("    \"\"\"Aynı x değeri için tek bir XPlane paylaş.\"\"\"")
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


def _kor_kafesi(spec, kor, satirlar, uretilen, anahtar=None, sonek=""):
    """
    kare_kafes korunun RectLattice'ini ureten satirlari yazar; degisken adini
    dondurur. "anahtar" verilirse harita ayni kalir, harf -> demet eslemesi
    degisir (eksenel zenginlik kusaklama).
    """
    esleme = dict(kor["anahtar"])
    if anahtar:
        esleme.update(anahtar)
    for _harf, hedef in sorted(esleme.items()):
        _bagimliliklar(spec, hedef, satirlar, uretilen)
    nx, ny = kor["boyut"]
    v = "kor_kafes%s" % ("_" + sonek if sonek else "")
    satirlar.append("")
    satirlar.append("# kor kafesi (%d x %d demet), adım %s cm%s"
                    % (nx, ny, _f(kor["adim"]),
                       (" — katman: %s" % sonek) if sonek else ""))
    satirlar.append("%s_disi = openmc.Universe(cells=[openmc.Cell(fill=%s)])"
                    % (v, _mat_ifade((kor.get("yansitici") or {}).get("malzeme"))))
    satirlar.append("%s = openmc.RectLattice()" % v)
    satirlar.append("%s.pitch = (%s, %s)" % (v, _f(kor["adim"]), _f(kor["adim"])))
    satirlar.append("%s.lower_left = (%s, %s)"
                    % (v, _f(-kor["adim"] * nx / 2.0), _f(-kor["adim"] * ny / 2.0)))
    satirlar.append("%s.outer = %s_disi" % (v, v))
    satirlar.append("_harita%s = [" % sonek)
    for satir in kor["harita"]:
        satirlar.append("    %r," % satir)
    satirlar.append("]")
    satirlar.append("_anahtar%s = {%s}"
                    % (sonek, ", ".join("%r: %s" % (h, uretilen[t])
                                        for h, t in sorted(esleme.items()))))
    satirlar.append("%s.universes = [[_anahtar%s[_h] for _h in _s] "
                    "for _s in _harita%s]" % (v, sonek, sonek))
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
    satirlar.append("# %s — %s demet, adım %s cm" % (demet_ad, d["tur"], _f(d["adim"])))
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
        satirlar.append("# kafes haritası (%d x %d)" % (nx, ny))
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
        satirlar.append("# halkalar dıştan içe; her halka tepeden saat yönünde")
        satirlar.append("# yarıçapı k olan halkada 6k öğe, merkezde 1 öğe")
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
            satirlar.append("    %-*s  # yarıçap %d, %d öğe"
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
    _bolum(satirlar, 2, "GEOMETRİ")
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
    elif tur == "tamburlu":
        from cekirdek import tambur as _t
        # yan_bc bu fonksiyonda DAHA SONRA tanimlaniyor; bu dal erken dondugu
        # icin burada yerel olarak okunur.
        yan_bc = (kor.get("sinir") or {}).get("yan", "vacuum")
        R_kor = float(kor.get("kor_yaricap") or 0.0)
        yans = kor.get("yansitici") or {}
        kal = float(yans.get("kalinlik") or 0.0)
        R_dis = R_kor + kal
        t = kor.get("tambur") or {}
        ic_ad = _bagimliliklar(spec, kor["dolgu"], satirlar, uretilen)
        h = sema.kor_yuksekligi(kor)
        eksen = ""
        if h:
            sinir_d = kor.get("sinir") or {}
            satirlar.append("")
            satirlar.append("z_alt = openmc.ZPlane(%s, boundary_type=%r)"
                            % (_f(-h / 2.0), sinir_d.get("alt", "vacuum")))
            satirlar.append("z_ust = openmc.ZPlane(%s, boundary_type=%r)"
                            % (_f(+h / 2.0), sinir_d.get("ust", "vacuum")))
            eksen = " & +z_alt & -z_ust"
        satirlar.append("")
        satirlar.append("# --- tamburlu kor: silindirik kor + yansıtıcı + dönen tamburlar ---")
        satirlar.append("import math")
        satirlar.append("kor_silindir = openmc.ZCylinder(r=%s)" % _f(R_kor))
        satirlar.append("dis_silindir = openmc.ZCylinder(r=%s, boundary_type=%r)"
                        % (_f(R_dis), yan_bc))
        satirlar.append("_hucreler = [openmc.Cell(fill=%s, region=-kor_silindir%s)]"
                        % (ic_ad, eksen))
        satirlar.append("_yansitici = +kor_silindir & -dis_silindir")
        n = int(t.get("sayi") or 0)
        if n > 0:
            aci = float(t.get("emici_aci") or 120.0)
            satirlar.append("")
            satirlar.append("# Tambur universe'i: emici yay yerel +x yönünde ortalanmış.")
            satirlar.append("# cell.rotation = psi yayı doğrudan psi açısına koyar")
            satirlar.append("# (nokta sorgusuyla ölçüldü); ters çevirme yoktur.")
            satirlar.append("def _yari_duzlem(aci):")
            satirlar.append("    a = math.radians(aci)")
            satirlar.append("    return openmc.Plane(a=-math.sin(a), b=math.cos(a), c=0.0, d=0.0)")
            satirlar.append("_t_dis = openmc.ZCylinder(r=%s)" % _f(t["yaricap"]))
            birlesim = aci > 180.0
            if float(t.get("emici_ic_yaricap") or 0) > 0:
                satirlar.append("_t_ic  = openmc.ZCylinder(r=%s)" % _f(t["emici_ic_yaricap"]))
                taban = "+_t_ic & -_t_dis"
            else:
                taban = "-_t_dis"
            kama = ("(+_yari_duzlem(%s) | -_yari_duzlem(%s))" if birlesim
                    else "(+_yari_duzlem(%s) & -_yari_duzlem(%s))") % (_f(-aci/2), _f(aci/2))
            satirlar.append("_t_emici = (%s) & %s" % (taban, kama))
            satirlar.append("_tambur = openmc.Universe(cells=[")
            satirlar.append("    openmc.Cell(fill=%s, region=_t_emici),"
                            % _mat_ifade(t.get("emici_malzeme")))
            satirlar.append("    openmc.Cell(fill=%s, region=(-_t_dis) & ~_t_emici),"
                            % _mat_ifade(t.get("govde_malzeme")))
            satirlar.append("    openmc.Cell(fill=%s, region=+_t_dis)])"
                            % _mat_ifade(t.get("govde_malzeme")))
            satirlar.append("")
            satirlar.append("# yerleşim: psi = azimut + 180 + dönme  ->  dönme=0'da emici kora bakar")
            satirlar.append("_tambur_yerlesim = [")
            for x, y, psi in _t.yerlesim(t):
                satirlar.append("    (%s, %s, %s)," % (_f(x), _f(y), _f(psi)))
            satirlar.append("]")
            satirlar.append("for _x, _y, _psi in _tambur_yerlesim:")
            satirlar.append("    _delik = openmc.ZCylinder(x0=_x, y0=_y, r=%s)" % _f(t["yaricap"]))
            satirlar.append("    _h = openmc.Cell(fill=_tambur, region=-_delik%s)" % eksen)
            satirlar.append("    _h.translation = (_x, _y, 0.0)")
            satirlar.append("    _h.rotation = (0.0, 0.0, _psi)")
            satirlar.append("    _hucreler.append(_h)")
            satirlar.append("    _yansitici = _yansitici & +_delik")
        satirlar.append("_hucreler.append(openmc.Cell(fill=%s, region=_yansitici%s))"
                        % (_mat_ifade(yans.get("malzeme")), eksen))
        satirlar.append("kok = openmc.Universe(cells=_hucreler)")
        satirlar.append("")
        satirlar.append("geometri = openmc.Geometry(kok)")
        return 2 * R_dis, 2 * R_dis, uretilen

    elif tur == "kuresel":
        kabuklar = kor.get("kabuklar") or []
        satirlar.append("")
        satirlar.append("# Eş merkezli küresel kabuklar (içten dışa).")
        satirlar.append("# En dış kabuğun yüzeyi modelin sınır yüzeyidir.")
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
        nx, ny = kor["boyut"]
        ic = _kor_kafesi(spec, kor, satirlar, uretilen)
        gx, gy = kor["adim"] * nx, kor["adim"] * ny
    else:
        raise ValueError("bilinmeyen kor türü: %s" % tur)

    # --- sinir ve kok universe ---
    sinir = kor.get("sinir") or {}
    yan_bc = sinir.get("yan", "reflective")
    h = sema.kor_yuksekligi(kor)
    yans = kor.get("yansitici") or {}

    satirlar.append("")
    satirlar.append("# --- sınırlar ve kök universe ---")
    katmanlar = sema.eksenel_katmanlar(kor)
    if h:
        satirlar.append("z_alt = openmc.ZPlane(%s, boundary_type=%r)"
                        % (_f(-h / 2.0), sinir.get("alt", "reflective")))
        satirlar.append("z_ust = openmc.ZPlane(%s, boundary_type=%r)"
                        % (_f(+h / 2.0), sinir.get("ust", "reflective")))
        eksen = " & +z_alt & -z_ust"
    else:
        satirlar.append("# yükseklik verilmemiş -> eksenel yönde sonsuz (2B)")
        eksen = ""

    if katmanlar:
        satirlar.append("")
        satirlar.append("# --- eksenel katmanlar (alttan üste) ---")
        satirlar.append("# İç arayüzler 'transmission'dir; sınır koşulu yalnızca")
        satirlar.append("# en alt ve en üst yüzeye uygulanır.")
        for i, (_z0, z1, _b) in enumerate(katmanlar[:-1]):
            satirlar.append("z_ara%d = openmc.ZPlane(%s)" % (i, _f(z1)))
        parcalar = []
        for i, (_z0, _z1, b) in enumerate(katmanlar):
            if b.get("anahtar"):
                dolgu_ifade = _kor_kafesi(spec, kor, satirlar, uretilen,
                                          b["anahtar"], "kat%d" % i)
            elif b.get("dolgu"):
                dolgu_ifade = _bagimliliklar(spec, b["dolgu"], satirlar, uretilen)
            else:
                dolgu_ifade = ic
            alt = "z_alt" if i == 0 else "z_ara%d" % (i - 1)
            ust = "z_ust" if i == len(katmanlar) - 1 else "z_ara%d" % i
            parcalar.append("    (%s, +%s & -%s, %r),"
                            % (dolgu_ifade, alt, ust, b.get("ad") or "katman %d" % (i + 1)))
        satirlar.append("_katmanlar = [")
        satirlar.extend(parcalar)
        satirlar.append("]")

    def _kok_hucreler(taban):
        """Kok universe'in ic hucrelerini ureten Python ifadesi."""
        if katmanlar:
            return ("[openmc.Cell(fill=_d, region=%s & _r, name=_a)\n"
                    "         for _d, _r, _a in _katmanlar]" % taban)
        return "[openmc.Cell(fill=%s, region=%s%s)]" % (ic, taban, eksen)

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
        satirlar.append("# Altıgen duct. HexLattice ve HexagonalPrism yönelimleri aynıdır:")
        satirlar.append("# kafes 'y' -> zarf tepede sivri, sağ/solda düz; prizma 'y' de öyle.")
        satirlar.append("# apothem = (halka-1)*adım*sqrt(3)/2 + adım/2   (yarım adım açıklık)")
        satirlar.append("import math")
        satirlar.append("_apothem = (%s - 1) * %s * math.sqrt(3) / 2 + %s / 2"
                        % (_f(halka), _f(adim), _f(adim)))
        if yans.get("var"):
            satirlar.append("_ic_prizma = openmc.model.HexagonalPrism("
                            "edge_length=2*_apothem/math.sqrt(3), orientation=%r)" % yonelim)
            satirlar.append("_dis_prizma = openmc.model.HexagonalPrism("
                            "edge_length=2*(_apothem + %s)/math.sqrt(3), orientation=%r, "
                            "boundary_type=%r)" % (_f(yans["kalinlik"]), yonelim, yan_bc))
            satirlar.append("_kok_hucreler = %s" % _kok_hucreler("-_ic_prizma"))
            satirlar.append("_kok_hucreler.append(openmc.Cell(fill=%s, "
                            "region=+_ic_prizma & -_dis_prizma%s))"
                            % (_mat_ifade(yans.get("malzeme")), eksen))
            satirlar.append("kok = openmc.Universe(cells=_kok_hucreler)")
            gx, gy = gx + 2 * yans["kalinlik"], gy + 2 * yans["kalinlik"]
        else:
            satirlar.append("_prizma = openmc.model.HexagonalPrism("
                            "edge_length=2*_apothem/math.sqrt(3), orientation=%r, "
                            "boundary_type=%r)" % (yonelim, yan_bc))
            satirlar.append("kok = openmc.Universe(cells=%s)"
                            % _kok_hucreler("-_prizma"))
        satirlar.append("")
        satirlar.append("geometri = openmc.Geometry(kok)")
        return gx, gy, uretilen

    if yans.get("var") and tur in ("tek_demet", "kare_kafes"):
        kal = yans["kalinlik"]
        dgx, dgy = gx + 2 * kal, gy + 2 * kal
        satirlar.append("ic_kutu  = openmc.model.RectangularPrism(%s, %s)" % (_f(gx), _f(gy)))
        satirlar.append("dis_kutu = openmc.model.RectangularPrism(%s, %s, boundary_type=%r)"
                        % (_f(dgx), _f(dgy), yan_bc))
        satirlar.append("_kok_hucreler = %s" % _kok_hucreler("-ic_kutu"))
        satirlar.append("_kok_hucreler.append(openmc.Cell(fill=%s, "
                        "region=+ic_kutu & -dis_kutu%s))"
                        % (_mat_ifade(yans.get("malzeme")), eksen))
        satirlar.append("kok = openmc.Universe(cells=_kok_hucreler)")
        gx, gy = dgx, dgy
    else:
        satirlar.append("kutu = openmc.model.RectangularPrism(%s, %s, boundary_type=%r)"
                        % (_f(gx), _f(gy), yan_bc))
        satirlar.append("kok = openmc.Universe(cells=%s)" % _kok_hucreler("-kutu"))
    satirlar.append("")
    satirlar.append("geometri = openmc.Geometry(kok)")
    return gx, gy, uretilen


def _ayarlar(spec, satirlar, gx, gy):
    _bolum(satirlar, 3, "AYARLAR")
    a = spec["ayarlar"]
    satirlar.append("")
    satirlar.append("ayar = openmc.Settings()")
    satirlar.append("ayar.run_mode  = %r" % a.get("mod", "eigenvalue"))
    satirlar.append("ayar.particles = %-10s # çevrim başına parçacık" % _f(int(a["parcacik"])))
    satirlar.append("ayar.batches   = %-10s # toplam çevrim" % _f(int(a["cevrim"])))
    if a.get("mod", "eigenvalue") == "eigenvalue":
        satirlar.append("ayar.inactive  = %-10s # pasif çevrim" % _f(int(a["pasif"])))
    if a.get("tohum"):
        satirlar.append("ayar.seed      = %s" % _f(int(a["tohum"])))
    if a.get("sicaklik_yontemi"):
        satirlar.append("ayar.temperature = {'method': %r}" % a["sicaklik_yontemi"])

    k = a.get("kaynak") or {}
    satirlar.append("")
    if k.get("tur") == "kutu":
        # Z araligi modelin yuksekligini kapsamali (bkz. kurucu.py notu):
        # dar bir baslangic kutusu eksenel sekli yanlis yakinsatir.
        # Kutu AKTIF yakit araligini kapsar (kurucu.py ile ayni tanim):
        # yansitici/plenum katmanlarinda orneklenen noktalar zaten reddedilir.
        from cekirdek import kurucu as _kur
        _ar = _kur.aktif_eksenel_aralik(spec)
        _z0, _z1 = _ar if _ar else (-1.0, 1.0)
        # Yanal olcu yansitici HARIC (kurucu.kor_ic_olcusu ile ayni).
        _kx, _ky = _kur.kor_ic_olcusu(spec, (gx, gy))
        alt = k.get("alt") or [-_kx / 2, -_ky / 2, _z0]
        ust = k.get("ust") or [+_kx / 2, +_ky / 2, _z1]
        satirlar.append("_uzay = openmc.stats.Box(%r, %r)"
                        % (list(alt), list(ust)))
        satirlar.append("_kisit = {'fissionable': True}   # kaynak yalnızca fisil bölgelerde")
    else:
        satirlar.append("_uzay = openmc.stats.Point(%r)"
                        % (tuple(k.get("konum") or (0.0, 0.0, 0.0)),))
        satirlar.append("_kisit = None")
    satirlar.append("_enerji = %s" % _kaynak.enerji_kod(k.get("enerji")))
    satirlar.append("_aci    = %s" % _kaynak.aci_kod(k.get("aci")))
    satirlar.append("ayar.source = openmc.IndependentSource(space=_uzay,")
    satirlar.append("                                       angle=_aci,")
    satirlar.append("                                       energy=_enerji,")
    satirlar.append("                                       strength=%r,"
                    % float(k.get("kuvvet") or 1.0))
    satirlar.append("                                       particle=%r,"
                    % (k.get("parcacik") or "neutron"))
    satirlar.append("                                       constraints=_kisit)")
    if (k.get("parcacik") or "neutron") == "photon":
        satirlar.append("ayar.photon_transport = True   # foton kaynağı foton taşınımı gerektirir")
    ent = a.get("entropi_mesh") or {}
    if ent.get("var") and a.get("mod", "eigenvalue") == "eigenvalue":
        satirlar.append("")
        satirlar.append("# Shannon entropisi ağı — kaynak yakınsamasını ölçer.")
        satirlar.append("# Entropi pasif çevrimler boyunca kayıyorsa pasif çevrim")
        satirlar.append("# sayısı yetersizdir ve k-eff yanlı çıkar.")
        satirlar.append("_ent_mesh = openmc.RegularMesh()")
        satirlar.append("_ent_mesh.dimension = %r" % (_kaynak.entropi_boyutu(spec),))
        _hz = sema.kor_yuksekligi(spec["kor"])
        _ez = (_hz / 2.0) if _hz else 1.0e10
        satirlar.append("_ent_mesh.lower_left  = (%s, %s, %s)" % (_f(-gx/2.0), _f(-gy/2.0), _f(-_ez)))
        satirlar.append("_ent_mesh.upper_right = (%s, %s, %s)" % (_f(gx/2.0), _f(gy/2.0), _f(_ez)))
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
        satirlar.append("# Uyarı: güç dağılımı için '%s' çubuğu geometride" % cubuk_ad)
        satirlar.append("# bulunamadı; tally üretilmedi.")
        return []

    bolge = int(g.get("bolge") or 0)
    satirlar.append("")
    satirlar.append("# --- çubuk bazlı güç dağılımı ---")
    satirlar.append("# pin() hücreleri bölge sırasında oluşturur, bu yüzden id'ye")
    satirlar.append("# göre sıralamak bölge sırasını verir.")
    satirlar.append("_guc_hucreler = sorted(%s.cells.values(), key=lambda c: c.id)" % degisken)
    satirlar.append("_guc_hedef = _guc_hucreler[%d]" % bolge)
    satirlar.append("guc_tally = openmc.Tally(name='guc_dagilimi')")
    satirlar.append("guc_tally.scores = [%r]" % (g.get("skor") or "kappa-fission"))
    satirlar.append("_guc_filtreler = [openmc.DistribcellFilter(_guc_hedef)]")

    h = sema.kor_yuksekligi(spec["kor"])
    dilim = int(g.get("eksenel_dilim") or 1)
    if h and dilim > 1:
        pay = max(gx, gy)
        satirlar.append("")
        satirlar.append("# Eksenel mesh aktif yakıt yüksekliğiyle tam örtüşmelidir;")
        satirlar.append("# taşarsa boş bin'ler ortalamayı düşürür ve F_q şişer.")
        satirlar.append("_guc_mesh = openmc.RegularMesh()")
        satirlar.append("_guc_mesh.dimension   = [1, 1, %d]" % dilim)
        from cekirdek import kurucu as _kur
        _z0, _z1 = _kur.cubuk_eksenel_aralik(spec, g.get("cubuk")) or (-h / 2.0, h / 2.0)
        satirlar.append("_guc_mesh.lower_left  = (%s, %s, %s)" % (_f(-pay), _f(-pay), _f(_z0)))
        satirlar.append("_guc_mesh.upper_right = (%s, %s, %s)" % (_f(pay), _f(pay), _f(_z1)))
        satirlar.append("_guc_filtreler.append(openmc.MeshFilter(_guc_mesh))")
    satirlar.append("guc_tally.filters = _guc_filtreler")
    satirlar.append("")
    satirlar.append("# Toplam korunumu kontrolü: aynı hücre, bölünmemiş.")
    satirlar.append("# Eksenel mesh'in hücrenin tamamını kapsayıp kapsamadığını da sınar.")
    satirlar.append("guc_ref = openmc.Tally(name='guc_toplam_ref')")
    satirlar.append("guc_ref.scores = list(guc_tally.scores)")
    satirlar.append("guc_ref.filters = [openmc.CellFilter(_guc_hedef)]")
    return ["guc_tally", "guc_ref"]


def _tallyler(spec, satirlar, ek_tallyler=None, on_satirlar=None, sinir_kutu=None):
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
                # kurucu.py ile AYNI fonksiyon: otomatik sinirlar modelin sinir
                # kutusundan ve kor yuksekliginden turetilir.
                from cekirdek import kurucu as _kur
                alt, ust = _kur.tally_mesh_sinirlari(spec, f, sinir_kutu)
                if f.get("otomatik"):
                    satirlar.append("# mesh sınırları modelin sınır kutusundan türetildi")
                satirlar.append("%s = openmc.RegularMesh()" % mv)
                satirlar.append("%s.dimension  = %r" % (mv, list(f["boyut"])))
                satirlar.append("%s.lower_left = %r" % (mv, list(alt)))
                satirlar.append("%s.upper_right = %r" % (mv, list(ust)))
                filtre_ifadeleri.append("openmc.MeshFilter(%s)" % mv)
            elif f["tur"] == "malzeme":
                filtre_ifadeleri.append("openmc.MaterialFilter([%s])"
                                        % ", ".join(_ad(a) for a in f["adlar"]))
        if filtre_ifadeleri:
            satirlar.append("%s.filters = [%s]" % (v, ", ".join(filtre_ifadeleri)))
    satirlar.append("")
    satirlar.append("tallyler = openmc.Tallies([%s])" % ", ".join(adlar + ek_tallyler))


def _tukenme(spec, satirlar):
    """
    Tukenme bolumu. Hacimler cekirdek/tukenme.py'deki AYNI fonksiyondan gelir:
    ayni sayiyi iki ayri yoldan hesaplayan iki kod er ya da gec ayrisir
    (eksenel katmanlamada tam bu yuzden 1300 pcm'lik bir fark cikmisti).
    DONER tukenme bolumu yazildi mi.
    """
    t = spec.get("tukenme") or {}
    if not t.get("var"):
        return False
    from cekirdek import tukenme as _tk
    zs = _tk.zincir_secimi(spec)
    hv = _tk.hacimler(spec)
    _bolum(satirlar, 6, "TÜKENME (YANMA)")
    satirlar.append("")
    satirlar.append("# Yanabilir malzemeler ve analitik hacimleri. Hacim yanlışsa yanma")
    satirlar.append("# hızı aynı oranda yanlış olur ve k-eff'te iz bırakmaz.")
    for ad, v in hv.items():
        satirlar.append("%s.depletable = True" % _ad(ad))
        satirlar.append("%s.volume = %r   # cm³ — %s" % (_ad(ad), v["hacim"], v["ayrinti"]))
    satirlar.append("")
    satirlar.append("# Zincir: %s" % zs["gerekce"])
    satirlar.append("# Bu yol bu makineye aittir; başka yerde OPENMC_CHAIN_FILE'a bakın.")
    satirlar.append("TUKENME_ZINCIRI = %r" % zs["yol"])
    satirlar.append("TUKENME_ADIMLARI = %r   # %s" % ([float(a) for a in t["adimlar"]],
                                                    t.get("adim_birimi") or "d"))
    satirlar.append("")
    satirlar.append("")
    satirlar.append("def tukenme_kos():")
    satirlar.append('    """Yanma hesabı; depletion_results.h5 üretir."""')
    satirlar.append("    import openmc.deplete")
    satirlar.append("    op = openmc.deplete.CoupledOperator(")
    satirlar.append("        model, TUKENME_ZINCIRI,")
    satirlar.append("        diff_burnable_mats=%r," % bool(t.get("malzemeleri_ayir")))
    satirlar.append("        normalization_mode='fission-q',")
    satirlar.append("        fission_yield_mode='constant',")
    satirlar.append("        # Fisyon ürünü verimleri bu enerjide okunur: 0.0253 eV termal,")
    satirlar.append("        # 5e5 eV hızlı. OpenMC'nin varsayılanı 0.0253 eV'tur — hızlı")
    satirlar.append("        # zincir seçilse bile. Hızlı sistemde bu ayrıca verilmelidir.")
    satirlar.append("        fission_yield_opts={'energy': %r})" % zs["verim_enerjisi"])
    sinif = {"cecm": "CECMIntegrator", "predictor": "PredictorIntegrator"}[
        t.get("entegrator") or "cecm"]
    satirlar.append("    integ = openmc.deplete.%s(" % sinif)
    satirlar.append("        op, TUKENME_ADIMLARI,")
    satirlar.append("        power_density=%r,   # W/gHM (mutlak güç değil)"
                    % float(t["guc_yogunlugu"]))
    satirlar.append("        timestep_units=%r)" % (t.get("adim_birimi") or "d"))
    satirlar.append("    integ.integrate()")
    satirlar.append("    return 'depletion_results.h5'")
    return True


def _kapanis(spec, satirlar, renkli):
    _bolum(satirlar, 5, "MODEL VE ÇALIŞTIRMA")
    tallyler = ("tallyler" if (spec.get("tallyler")
                or (spec.get("guc_dagilimi") or {}).get("var"))
                else "openmc.Tallies()")
    satirlar.append("")
    satirlar.append("model = openmc.Model(geometry=geometri, materials=malzemeler,")
    satirlar.append("                     settings=ayar, tallies=%s)" % tallyler)
    kin = spec["ayarlar"].get("kinetik") or {}
    if kin.get("var") and spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        # kurucu.kur ile ayni: onceden betik IFP'yi hic yazmiyordu ve disa
        # aktarilan Godiva beta_eff / notron omru vermiyordu.
        satirlar.append("")
        satirlar.append("# Kinetik parametreler (IFP): etkin gecikmiş nötron kesri (beta_eff)")
        satirlar.append("# ve ortalama nötron nesil süresi. Koşu süresini biraz uzatır.")
        satirlar.append("model.add_kinetics_parameters_tallies()")
        satirlar.append("model.settings.ifp_n_generation = %d" % int(kin.get("nesil") or 10))
    if renkli:
        satirlar.append("")
        satirlar.append("# Model.plot() SVG renk adı ya da (R,G,B) demeti ister — hex dize kabul etmez")
        satirlar.append("renkler = {")
        for m in spec["malzemeler"]:
            if m.get("renk"):
                satirlar.append("    %s: %r," % (_ad(m["ad"]), tuple(m["renk"])))
        satirlar.append("}")
    tukenme_var = _tukenme(spec, satirlar)
    satirlar.append("")
    if tukenme_var:
        satirlar.append("")
    satirlar.append("if __name__ == '__main__':")
    satirlar.append("    import matplotlib.pyplot as plt")
    satirlar.append("")
    satirlar.append("    # --- Önce çiz, sonra çalıştır ---")
    satirlar.append("    # Geometri doğru görünmeden koşu başlatmak zaman kaybıdır.")
    satirlar.append("    for _eksen in ('xy',):")
    satirlar.append("        _ax = model.plot(basis=_eksen, color_by='material',")
    satirlar.append("                         colors=%s pixels=(600, 600))"
                    % ("renkler," if renkli else "None,"))
    satirlar.append("        _ax.get_figure().savefig('geometri_%s.png' % _eksen, dpi=110)")
    satirlar.append("        print('çizildi: geometri_%s.png' % _eksen)")
    satirlar.append("")
    satirlar.append("    # Çizimler doğruysa aşağıdaki satırın yorumunu kaldırın.")
    satirlar.append("    # sp = model.run(threads=%d)" % spec["calistirma"].get("is_parcacigi", 8))
    satirlar.append("    # print(openmc.StatePoint(sp).keff)")
    if tukenme_var:
        satirlar.append("")
        satirlar.append("    # Yanma hesabı (uzun sürer; OMP_NUM_THREADS ortam değişkeniyle")
        satirlar.append("    # iş parçacığı sayısını ayarlayın):")
        satirlar.append("    # tukenme_kos()")


# ============================================================================
# ANA GIRIS
# ============================================================================

def uret(spec, kaynak_dosya=None, renkli=True):
    """Spec'ten tek basina calisan Python betigi metni uretir."""
    global _KAYIT
    _KAYIT = {"esle": {}, "kullanilan": set()}
    try:
        return _uret(spec, kaynak_dosya, renkli)
    finally:
        _KAYIT = None


def _uret(spec, kaynak_dosya, renkli):
    tarih = datetime.date.today().isoformat()
    satirlar = [
        "# -*- coding: utf-8 -*-",
        '"""',
        "=" * 78,
        " %s" % spec.get("ad", "adsız model"),
        "=" * 78,
    ]
    if spec.get("aciklama"):
        for satir in spec["aciklama"].split("\n"):
            satirlar.append(" %s" % satir)
        satirlar.append("")
    satirlar += [
        " Bu betik openmc_arayuz tarafından üretilmiştir (%s)." % tarih,
    ]
    if kaynak_dosya:
        satirlar.append(" Kaynak model dosyası: %s" % kaynak_dosya)
    satirlar += [
        "",
        " Betik tek başına çalışır; openmc_arayuz'a bağımlı değildir.",
        " Elle düzenlenebilir, ancak arayüze geri yüklenemez.",
        "",
        " Kullanım",
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
    _tallyler(spec, satirlar, ek_tallyler=ek, on_satirlar=guc_satirlari,
              sinir_kutu=(gx, gy))
    _kapanis(spec, satirlar, renkli)
    satirlar.append("")
    return "\n".join(satirlar)
