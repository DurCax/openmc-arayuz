# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_hacim.py  --  Tukenme hacimleri: dogrudan yerlesim ve ornek hacimleri
================================================================================

 tukenme.py'nin yardimcisi (orada 800 satir siniri). Iki is:

 1. DOGRUDAN YERLESIM (spec uzerinde, openmc gerekmez)
    Bir yakit malzemesi cubuk/plaka icinde degil, bir kafes KONUMUNU dogrudan
    doldurabilir: kor haritasinda (altigen_kafes / kare_kafes) ya da bir
    demetin anahtarinda. Eskiden bu hacim SAYILMIYORDU (olculdu: 7 demetli
    korda merkeze 'uo2' -> 5336 cm3 raporlaniyordu, dogrusu 5336 + 2806;
    %34 eksik, uyarisiz). Konum hucresinin alani kesindir:
        kare kafes hucresi     P^2
        altigen kafes hucresi  (sqrt3/2) P^2      (duz yuzden duz yuze P)
    KESIN OLMAYANLAR ("stokastik hesap gerekli"; sessizce yanlis sayi YOK):
      * altigen demetin EN DIS halkasi: pin hucreleri demet zarfiyla (ya da
        kilifin ic yuzuyle) kirpilir, zarfin koselerinde kafesin dis dolgusu
        kalir (olculdu: tek demette kafes hucresi noktalarinin ~%1'i zarf
        disinda)
      * demetin dis dolgusu, kilifi, kor yansiticisi (alan kafes adimina ve
        zarfa bagli)

 1b. CUBUK / PLAKA / EMICI HACIMLERI (cubuk_hacmi, plaka_hacmi, tambur_emici_hacmi)
    Kontrol cubugu emicisi (Dalga 2 kapanis, TH6): katmansiz 3B modelde emici
    bolge ucta ikiye bolunur; emici = daldirma x yukseklik, izleyici = kalan
    (kurucu.cubuk_universe ile ayni). Katmanli / 2B modelde kesin degil.
    Tamamen cekili cubukta emici hacmi sifir: malzeme "yok" sayilir.

 2. ORNEK HACIMLERI (cubuk cubuk yanma, kurulan model uzerinde)
    OpenMC diff_burnable_mats'te toplam hacmi orneklere ESIT boler
    ('divide equally'). Bu iki durumda yanlistir:
      * esit olmayan eksenel katmanlar (50 + 20 cm'de her ornek 35 cm alir)
      * ayni yakiti farkli yaricapla kullanan iki cubuk turu
    Burada her ornek (Cell.paths sirasi = C++ distribcell sirasi; openmc.lib
    ile olculdu, testler/test_tukenme_hacim.py) kendi hucre alani x kendi
    katman yuksekligi ile ayri malzeme olur. Ornek toplami analitik toplamla
    tutmazsa ValueError: tahminle devam edilmez.

    NOT -- SIRA VARSAYIMI VE OPENMC SURUMU: toplam denetimi iki ornegin YER
    DEGISTIRMESINI yakalamaz (toplam ayni kalir). Sira esitligi yalniz
    testler/test_tukenme_hacim.py:test_ornek_sirasi_openmc (TH10; kare, altigen,
    ic ice kafes + esit olmayan katman + katmana ozel demet) ile olculur.
    environment.yml openmc=0.16.0'a sabittir; OpenMC surumu yukseltilirken
    bu test KAPIDIR (once o kosulur, gecmeden surum degismez).
================================================================================
"""

import math

from cekirdek import sema
from cekirdek.geometri.kesit import pin_bolge_alani
from cekirdek.ceviri import _, N_

SQ3 = math.sqrt(3.0)
KESIN_DEGIL = "stokastik hesap gerekli"
_GORELI_TOLERANS = 1e-9
# "yontem" degerleri tanimlayicidir (karsilastirilir); gorunen adlari:
_YONTEM_ADLARI = {KESIN_DEGIL: N_("stokastik hesap gerekli"), "analitik": N_("analitik"),
                  "stokastik": N_("stokastik"), "yok": N_("yok")}


def yontem_metni(yontem):
    """Hacim yonteminin gorunen adi, etkin dilde; bilinmiyorsa kendisi."""
    ad = _YONTEM_ADLARI.get(yontem)
    return _(ad) if ad else str(yontem)


# ============================================================================
# 1. dogrudan yerlesim (spec)
# ============================================================================

def kor_hucre_alani(kor):
    """Haritali korun konum hucresi alani [cm2]."""
    P = float(kor.get("adim") or 0.0)
    return SQ3 / 2.0 * P * P if kor.get("tur") == "altigen_kafes" else P * P


def _parca_adi_mi(spec, ad):
    """'ad' bir cubuk/plaka/demet adi mi? Kisaltma cozum sirasi (cubuk -> plaka
    -> demet -> malzeme) geregi ayni adli malzeme o konumu DOLDURMAZ (olculdu:
    pwr_mox_demet'te 'mox_25' hem cubuk hem malzeme; eskiden konum hucresi
    P^2 ayrica sayiliyor, hacim 4.2 kat cikiyordu)."""
    return any(x.get("ad") == ad for b in ("cubuklar", "plakalar", "demetler")
               for x in spec.get(b) or [])


def _demet_konum_sayilari(d, ad):
    """Demet anahtarinda dogrudan 'ad' olan konumlar: (ic, dis_halka)."""
    anahtar = d.get("anahtar") or {}
    harita = d.get("harita") or []
    if d.get("tur") != "altigen":
        return sum(1 for s in harita for h in s if anahtar.get(h) == ad), 0
    dis = sum(1 for h in (harita[0] if harita else "") if anahtar.get(h) == ad)
    ic = sum(1 for s in harita[1:] for h in s if anahtar.get(h) == ad)
    return ic, dis


def _demet_hucre_alani(d):
    p = float(d.get("adim") or 0.0)
    return SQ3 / 2.0 * p * p if d.get("tur") == "altigen" else p * p


def _kor_konum_sayisi(kor, ad, esleme):
    """Kor haritasinda (katmana ozel esleme uygulanmis) dogrudan 'ad' olan konumlar."""
    anahtar = dict(kor.get("anahtar") or {})
    anahtar.update(esleme or {})
    return sum(1 for s in kor.get("harita") or [] for h in s if anahtar.get(h) == ad)


def dogrudan_yerlesim(spec, kor, ad, dilimler):
    """
    Haritaya / demet anahtarina / altigen kor katmanina dogrudan konan 'ad'.

    dilimler: tukenme._eksenel_dilimler(kor) [(yukseklik, dolgu|None, esleme)]
    DONER {"hacim": cm3, "ornek": int, "parcalar": [str], "sorunlar": [str]}
    """
    from cekirdek import tukenme as _tk
    V, ornek, parcalar, sorunlar = 0.0, 0, [], []
    if _parca_adi_mi(spec, ad):
        return {"hacim": V, "ornek": ornek, "parcalar": parcalar,
                "sorunlar": _alan_bagimli_kullanim(spec, kor, ad)}
    haritali = kor.get("tur") in sema.HARITALI_KORLAR
    for h, dolgu, esleme in dilimler:
        if haritali and dolgu is None:
            n = _kor_konum_sayisi(kor, ad, esleme)
        elif kor.get("tur") == "altigen_kafes" and dolgu == ad:
            n = sum(len(s) for s in kor.get("harita") or [])     # katman dolgusu
        else:
            n = 0
        if n:
            V += n * kor_hucre_alani(kor) * h
            ornek += n
            parcalar.append(_("kor haritası: %d konum × %g cm") % (n, h))
        for d in spec.get("demetler") or []:
            ic, dis = _demet_konum_sayilari(d, ad)
            if not (ic or dis):
                continue
            m = _tk._kor_sayimi(spec, kor, dolgu, d["ad"], esleme)
            if not m:
                continue
            if dis:
                sorunlar.append(_("'%s' demetinin dış halkasında (pin hücresi zarfla "
                                "kırpılır)") % d["ad"])
            if ic:
                V += m * ic * _demet_hucre_alani(d) * h
                ornek += m * ic
                parcalar.append(_("%s: %d konum × %d demet × %g cm") % (d["ad"], ic, m, h))
    sorunlar += _alan_bagimli_kullanim(spec, kor, ad)
    return {"hacim": V, "ornek": ornek, "parcalar": parcalar, "sorunlar": sorunlar}


def _alan_bagimli_kullanim(spec, kor, ad):
    """Alani zarfa/adima bagli yerler: demet dis dolgusu, kilif, kor yansiticisi."""
    from cekirdek import uygunluk
    sorunlar = []
    kullanilan = uygunluk.geometri_icerigi(spec).get("demet") or set()
    for d in spec.get("demetler") or []:
        if d["ad"] not in kullanilan:
            continue
        if d.get("dolgu_disi") == ad:
            sorunlar.append(_("'%s' demetinin dış dolgusu") % d["ad"])
        k = d.get("kilif") if d.get("tur") == "altigen" else None
        if isinstance(k, dict) and k.get("malzeme") == ad:
            sorunlar.append(_("'%s' demetinin kılıfı") % d["ad"])
    y = kor.get("yansitici") or {}
    if y.get("var") and y.get("malzeme") == ad and kor.get("tur") != "tamburlu":
        sorunlar.append(_("kor yansıtıcısı"))
    return sorunlar


# ============================================================================
# 1b. kontrol tamburu ve kontrol cubugu emicisi (analitik)
# ============================================================================

def tambur_emici_hacmi(kor, ad):
    """
    Tamburlu korda 'ad' tambur emicisi ise emici yaylarinin toplam hacmi.
    Emici: r_ic..R arasinda emici_aci genisliginde halka dilimi (tambur.universe);
    tambur TAM yuksekligi kaplar (2B: 1 cm). Donme hacmi degistirmez.
    DONER (hacim cm3, [ayrinti]) -- ilgisizse (0.0, []).
    """
    t = kor.get("tambur") or {}
    n = int(t.get("sayi") or 0)
    if kor.get("tur") != "tamburlu" or n <= 0 or t.get("emici_malzeme") != ad:
        return 0.0, []
    R, r_ic = float(t["yaricap"]), float(t.get("emici_ic_yaricap") or 0.0)
    aci = float(t.get("emici_aci") or 120.0)
    H = sema.kor_yuksekligi(kor) or 1.0
    v = n * (aci / 360.0) * math.pi * (R * R - r_ic * r_ic) * H
    return v, [_("%d tambur emici yayı %g° (r = %g…%g cm) × %g cm") % (n, aci, r_ic, R, H)]


def kontrol_emici_uzunlugu(spec, cubuk):
    """
    Katmansiz 3B modelde kontrol cubugu emicisinin eksenel uzunlugu (cm):
    ucun ustu (kurucu.cubuk_universe: z_uc = z_ust - daldirma x aktif) ile
    modelin tepesi arasi. Izleyici = kalan. Katmanli ya da 2B modelde None
    (emici katman sinirlarini asabilir; kesin degil).
    DONER (emici_uzunlugu, izleyici_uzunlugu) ya da None
    """
    kor = spec["kor"]
    h = sema.kor_yuksekligi(kor)
    if not h or sema.eksenel_katmanlar(kor) is not None:
        return None
    daldirma = float(cubuk.get("daldirma") or 0.0)
    emici = daldirma / 100.0 * h
    return emici, h - emici


def kontrol_emici_kesri(spec, cubuk, ad):
    """
    Kontrol cubugunun EMICI bolgesinde 'ad' malzemesinin kapladigi eksenel
    kesir (0..1). Emici bolge ucta ikiye bolunur (kurucu.cubuk_universe):
    ustu emici malzemesi, alti izleyici. Kesin degilse (katmanli / 2B) None.
    """
    uz = kontrol_emici_uzunlugu(spec, cubuk)
    if uz is None:
        return None
    emici, izleyici = uz
    i = int(cubuk.get("emici_bolge") or 0)
    pay = (emici if cubuk["bolgeler"][i].get("malzeme") == ad else 0.0) \
        + (izleyici if cubuk.get("izleyici_malzeme") == ad else 0.0)
    return pay / (emici + izleyici)


def cubuk_hacmi(spec, kor, ad, dilimler, sorunlar):
    """Cubuk bolgelerindeki 'ad' hacmi (V, parcalar); kesin olmayanlar sorunlar'a.
    Kontrol cubugunun emici bolgesi daldirmaya gore emici/izleyici diye
    bolunur (kontrol_emici_kesri); diger bolgeleri tam boydur."""
    from cekirdek import tukenme as _tk
    V, parcalar = 0.0, []
    for c in spec.get("cubuklar", []):
        bolgeler = c.get("bolgeler") or []
        emici_ix = int(c.get("emici_bolge") or 0) if c.get("tur") == "kontrol" else -1
        for i, b in enumerate(bolgeler):
            kontrol = i == emici_ix
            if b.get("malzeme") != ad and not (kontrol and c.get("izleyici_malzeme") == ad):
                continue
            if b.get("r") is None:
                sorunlar.append(_("'%s' çubuğunun dış bölgesi (alan kafes adımına bağlı)")
                                % c["ad"])
                continue
            kesir = kontrol_emici_kesri(spec, c, ad) if kontrol else 1.0
            if kesir is None:
                sorunlar.append(_("'%s' kontrol çubuğu (daldırmaya bağlı)") % c["ad"])
                continue
            r_ic = bolgeler[i - 1]["r"] if i > 0 else 0.0
            # kare/altigen kesitli pin (§15.3): alan pi r^2 degil
            sekil = c.get("kesit") or "silindir"
            alan = pin_bolge_alani(sekil, b["r"]) - pin_bolge_alani(sekil, r_ic)
            ek = _(" (daldırma %%%g: boyun %%%.4g'i)") % (
                float(c.get("daldirma") or 0.0), 100.0 * kesir) if kontrol else ""
            for h, dolgu, esleme in dilimler:
                n = _tk._kor_sayimi(spec, kor, dolgu, c["ad"], esleme)
                if n:
                    V += alan * h * kesir * n
                    parcalar.append(_("%s, %d. bölge: %d adet × %g cm%s")
                                    % (c["ad"], i + 1, n, h, ek))
    return V, parcalar


def plaka_hacmi(spec, kor, ad, dilimler):
    """Plaka etlerindeki 'ad' hacmi (V, parcalar)."""
    from cekirdek import tukenme as _tk
    V, parcalar = 0.0, []
    for p in spec.get("plakalar", []):
        if p.get("et_malzeme") != ad:
            continue
        alan = p["et_kalinlik"] * p["plaka_genislik"] * p["plaka_sayisi"]
        for h, dolgu, esleme in dilimler:
            n = _tk._kor_sayimi(spec, kor, dolgu, p["ad"], esleme)
            if n:
                V += alan * h * n
                parcalar.append(_("%s: %d eleman × %g cm") % (p["ad"], n, h))
    return V, parcalar


# ============================================================================
# 1c. malzeme hacim kaydi ve ornek sayisi (tukenme.py'den tasindi, Dalga G-2)
#     Sablon modunda asagidaki spec yolu; gelismis (agac) modunda
#     geometri.hacim (agac gezintisi). Iki yolun ayni sonucu verdigi 27
#     ornekte olculur: testler/test_geometri_tuketici.py (GT2).
# ============================================================================

def _agac_mi(spec):
    return ((spec or {}).get("kor") or {}).get("tur") == "agac"


def malzeme_hacimleri(spec, adlar):
    """{ad: {"hacim": cm3|None, "yontem", "ayrinti"}} -- sablon ya da agac modu."""
    if _agac_mi(spec):
        from cekirdek import geometri
        from cekirdek.geometri import hacim
        m = geometri.model(spec)
        return {ad: hacim.analitik(m, ad).sozluk() for ad in adlar}
    from cekirdek import tukenme as _tk
    dilimler = _tk._eksenel_dilimler(spec["kor"])
    return {ad: sablon_malzeme_hacmi(spec, ad, dilimler) for ad in adlar}


def ornek_sayisi(spec, ad):
    """
    'ad' malzemesinin geometrideki ornek (hacmi sifir olmayan hucre) sayisi --
    sablon ve agac modunda AYNI yol: agac gezintisi (geometri.hacim). Eski
    sablon sayimi tambur emicisini saymiyordu (tamburlu_kor: b4c 8 tamburda 8
    ornek, eskiden 1); 26 ornekte diger sayilar aynidir (GV1).
    """
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    return hacim.ornek_sayisi(geometri.model(spec), ad)


def kuresel_hacim(kor, ad):
    """Kuresel kor: 'ad' kabuklarinin hacmi (analitik)."""
    V, parcalar, r_ic = 0.0, [], 0.0
    for k in kor.get("kabuklar") or []:
        if k.get("malzeme") == ad:
            v = 4.0 / 3.0 * math.pi * (k["r"] ** 3 - r_ic ** 3)
            V += v
            parcalar.append(_("kabuk r = %g cm: %.4g cm³") % (k["r"], v))
        r_ic = k["r"]
    return {"hacim": V if V > 0 else None, "yontem": "analitik" if V > 0 else "yok",
            "ayrinti": "; ".join(parcalar)}


def _sablon_parcalari(spec, kor, ad, dilimler):
    """Cubuk, plaka, tambur ve dogrudan yerlesim katkilari: (V, parcalar, sorunlar)."""
    sorunlar = []
    V, parcalar = cubuk_hacmi(spec, kor, ad, dilimler, sorunlar)
    v, p = plaka_hacmi(spec, kor, ad, dilimler)
    V, parcalar = V + v, parcalar + p
    if kor["tur"] == "tamburlu":
        v, p = tambur_emici_hacmi(kor, ad)
        V, parcalar = V + v, parcalar + p
        # kor silindirini dogrudan dolduran homojen malzeme
        R = float(kor.get("kor_yaricap") or 0.0)
        for h, dolgu, _e in dilimler:
            if (dolgu or kor.get("dolgu")) == ad:
                V += math.pi * R * R * h
                parcalar.append(_("kor silindiri R = %g cm × %g cm") % (R, h))
        return V, parcalar, sorunlar
    d = dogrudan_yerlesim(spec, kor, ad, dilimler)
    V, parcalar, sorunlar = V + d["hacim"], parcalar + d["parcalar"], sorunlar + d["sorunlar"]
    altigen = kor["tur"] == "altigen_kafes"
    if kor.get("dolgu") == ad or any(dd == ad and not altigen for _h, dd, _e in dilimler):
        sorunlar.append(_("katmanı/koru doğrudan dolduruyor"))
    return V, parcalar, sorunlar


def sablon_malzeme_hacmi(spec, ad, dilimler):
    """Sablon modunda tek bir yanabilir malzemenin hacim kaydi."""
    kor = spec["kor"]
    if kor["tur"] == "kuresel":
        return kuresel_hacim(kor, ad)
    V, parcalar, sorunlar = _sablon_parcalari(spec, kor, ad, dilimler)
    if sorunlar:
        return {"hacim": None, "yontem": KESIN_DEGIL,
                "ayrinti": _("hacmi kesin değil: ") + "; ".join(sorunlar)}
    if V > 0:
        return {"hacim": V, "yontem": "analitik", "ayrinti": "; ".join(parcalar)}
    if parcalar:
        # yerlesim var ama hacmi sifir (tamamen cekili kontrol cubugu emicisi):
        # malzeme fiilen geometride yok, yakilacak bir sey yok
        return {"hacim": None, "yontem": "yok",
                "ayrinti": _("hacmi sıfır: ") + "; ".join(parcalar)}
    from cekirdek import uygunluk
    if ad in (uygunluk.geometri_icerigi(spec).get("malzeme") or set()):
        # geometride var ama analitik yolu yok (or. kontrol tamburu emicisi)
        return {"hacim": None, "yontem": KESIN_DEGIL,
                "ayrinti": _("bu yerleşim için analitik hacim yok")}
    return {"hacim": None, "yontem": "yok", "ayrinti": _("malzeme geometride bulunamadı")}


def stokastik_tamamla(spec, tablo, orneklem=2_000_000, dizin=None):
    """
    Gelismis (agac) mod: analitik hacmi kesin olmayan kayitlar (kesik konum,
    kesik cubuk, duzensiz bolge -- §8 UYARI 1) OpenMC stokastik hacmiyle
    tamamlanir ve yontem "stokastik" olarak BILDIRILIR (sessizce degil).
    Sablon modunda tablo aynen doner (tukenme orada kesin hacim ister).
    DONER (yeni tablo, [stokastige dusen adlar])
    """
    eksik = [a for a, v in tablo.items() if not v.get("hacim") and v.get("yontem") == KESIN_DEGIL]
    if not eksik or not _agac_mi(spec):
        return tablo, []
    from cekirdek.geometri import hacim
    # bagil sigma denetimli (geometri.hacim.BAGIL_SIGMA_SINIRI); olculemeyenin
    # nedeni ayrintiya yazilir
    olculen, nedenler = hacim.denetimli_stokastik(spec, eksik, orneklem, dizin)
    yeni, dusen = dict(tablo), []
    for ad in eksik:
        if ad in olculen:
            v, s = olculen[ad]
            yeni[ad] = dict(tablo[ad], hacim=v, yontem=hacim.STOKASTIK,
                            ayrinti=_("stokastik hacim %.6g ± %.2g cm³ (%s)")
                            % (v, s, tablo[ad].get("ayrinti")))
            dusen.append(ad)
        else:
            yeni[ad] = dict(tablo[ad], ayrinti="%s; %s" % (nedenler[ad],
                                                           tablo[ad].get("ayrinti")))
    return yeni, dusen


# ============================================================================
# 2. ornek hacimleri (kurulan model)
# ============================================================================

def _yarim_uzaylar(bolge):
    """Kesisim bolgesinin yarim uzaylari; baska yapi (birlesim, tumleyen) -> None."""
    import openmc
    if isinstance(bolge, openmc.Halfspace):
        return [bolge]
    if isinstance(bolge, openmc.Intersection):
        cikti = []
        for b in bolge:
            alt = _yarim_uzaylar(b)
            if alt is None:
                return None
            cikti += alt
        return cikti
    return None


_YARDIMCI_KUTU = 1.0e5              # cm; kor olculerinin cok ustunde
# Kirpilan cokgenin bir kosesi yardimci kutunun kenarinda kaldiysa bolge o
# yonde ACIKTIR (yalniz bir yonde sinirli serit, ceyrek duzlem...).
_KUTU_KENAR_TOL = 1.0e-9


def _dugunluk_alani(yarilar):
    """
    Duz yuzlerle sinirli konveks cokgenin alani (yarim duzlem kirpmasi).
    Bolge her yonde kapali degilse None: eskiden yalniz bir yonde sinirli bir
    serit (iki XPlane) 2 * dx * R gibi SONLU ama anlamsiz bir alan donuyordu.
    """
    import openmc
    R = _YARDIMCI_KUTU
    cokgen = [(-R, -R), (R, -R), (R, R), (-R, R)]
    for y in yarilar:
        s = y.surface
        if isinstance(s, openmc.XPlane):
            a, b, d = 1.0, 0.0, s.x0
        elif isinstance(s, openmc.YPlane):
            a, b, d = 0.0, 1.0, s.y0
        else:
            a, b, d = s.a, s.b, s.d
        isaret = -1.0 if y.side == "-" else 1.0     # icerisi: isaret*(ax+by-d) >= 0
        cokgen = _kirp(cokgen, a * isaret, b * isaret, d * isaret)
        if not cokgen:
            return 0.0
    sinir = R * (1.0 - _KUTU_KENAR_TOL)
    if any(abs(x) >= sinir or abs(y) >= sinir for x, y in cokgen):
        return None                 # kutunun kenarina/kosesine dokunuyor: acik bolge
    alan = 0.0
    for (x0, y0), (x1, y1) in zip(cokgen, cokgen[1:] + cokgen[:1]):
        alan += x0 * y1 - x1 * y0
    return abs(alan) / 2.0


def _kirp(cokgen, a, b, d):
    """Sutherland-Hodgman: a x + b y - d >= 0 tarafini birak."""
    cikti = []
    for i, p in enumerate(cokgen):
        q = cokgen[(i + 1) % len(cokgen)]
        fp, fq = a * p[0] + b * p[1] - d, a * q[0] + b * q[1] - d
        if fp >= 0:
            cikti.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            cikti.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return cikti


def bolge_alani(bolge):
    """
    Hucre bolgesinin eksenel kesit alani [cm2]; hesaplanamazsa None.
    Desteklenen: es merkezli ZCylinder halkasi (cubuk bolgeleri) ya da
    X/Y/genel dusey duzlemlerle sinirli konveks cokgen (plaka eti, altigen
    kor hucresi). ZPlane'ler (katman sinirlari) alana girmez.
    """
    import openmc
    if bolge is None:
        return None
    yarilar = _yarim_uzaylar(bolge)
    if yarilar is None:
        return None
    yarilar = [y for y in yarilar if not isinstance(y.surface, openmc.ZPlane)]
    silindir = [y for y in yarilar if isinstance(y.surface, openmc.ZCylinder)]
    duzlem = [y for y in yarilar if isinstance(y.surface, (openmc.XPlane, openmc.YPlane))
              or (type(y.surface) is openmc.Plane and abs(y.surface.c) < 1e-12)]
    if len(silindir) + len(duzlem) != len(yarilar) or (silindir and duzlem):
        return None
    if duzlem:
        return _dugunluk_alani(duzlem)
    ic = [y.surface.r for y in silindir if y.side == "-"]
    dis = [y.surface.r for y in silindir if y.side == "+"]
    merkez = {(y.surface.x0, y.surface.y0) for y in silindir}
    if len(ic) != 1 or len(dis) > 1 or len(merkez) != 1:
        return None
    return math.pi * (ic[0] ** 2 - (dis[0] ** 2 if dis else 0.0))


def _z_araligi(bolge):
    """Bolgenin z sinirlari (alt, ust); bir yonde acik olabilir (+-inf).
    Hesaplanamazsa (-inf, inf)."""
    if bolge is None:
        return -math.inf, math.inf
    try:
        alt, ust = bolge.bounding_box
    except (AttributeError, NotImplementedError, TypeError, ValueError):
        return -math.inf, math.inf
    return float(alt[2]), float(ust[2])


def _yol_z_uzunlugu(ogeler):
    """
    Yol uzerindeki hucrelerin z araliklarinin KESISIMI; sonsuzsa None.
    Kesisim (en kisa aralik degil): kontrol cubugu emicisi yalniz ucta bir
    ZPlane ile sinirlidir (ustu acik), sonlu ust sinirini kor/katman hucresi
    verir. Kurucu hucreleri yalniz (x, y, 0) oteler; z her duzeyde ortaktir.
    """
    alt, ust = -math.inf, math.inf
    for t, n in ogeler:
        if t == "c":
            a, u = _z_araligi(n.region)
            alt, ust = max(alt, a), min(ust, u)
    uzun = ust - alt
    return max(uzun, 0.0) if math.isfinite(uzun) else None


def _yol_ogeleri(yol, hucreler, kafesler):
    """'u1->c5->l3(0,1)->u2->c7' -> [("c", Cell) | ("l", Lattice)]."""
    ogeler = []
    for parca in yol.split("->"):
        if parca.startswith("c"):
            ogeler.append(("c", hucreler[int(parca[1:])]))
        elif parca.startswith("l"):
            ogeler.append(("l", kafesler[int(parca[1:parca.index("(")])]))
    return ogeler


def _kafes_hucre_alani(kafes):
    import openmc
    if isinstance(kafes, openmc.HexLattice):
        return SQ3 / 2.0 * kafes.pitch[0] ** 2
    return float(kafes.pitch[0]) * float(kafes.pitch[1])


def ornek_hacmi(yol, hucreler, kafesler):
    """
    Bir hucre orneginin hacmi [cm3] ya da None.
    Alan: hucrenin kendi bolgesi; bolgesi yoksa (malzeme universe'u bir kafes
    konumunu ya da kor hucresini dolduruyor) yol uzerinde geriye dogru ilk
    kafes hucresi / alani hesaplanabilen hucre. Yukseklik: yol uzerindeki en
    yol hucrelerinin z araliklarinin kesisimi (katman, kontrol ucu); sonsuzsa 2B, 1 cm.
    """
    ogeler = _yol_ogeleri(yol, hucreler, kafesler)
    alan = None
    for tur, nesne in reversed(ogeler):
        alan = _kafes_hucre_alani(nesne) if tur == "l" else bolge_alani(nesne.region)
        if alan is not None or (tur == "c" and nesne.region is not None):
            break
    if alan is None:
        return None
    uzun = _yol_z_uzunlugu(ogeler)
    return alan * (1.0 if uzun is None else uzun)


def ornekleri_ayir(model, spec, hv, yanacak):
    """
    Cubuk cubuk yanma: birden fazla ornegi olan yanabilir malzemeleri ornek
    basina ayri malzemeye boler; her klonun hacmi kendi ornegininkidir.
    model yerinde degistirilir (openmc Model nesnesi; spec degismez).

    yanacak: {ad: openmc.Material} (depletable, volume ayarli)
    DONER ayrilan ornek (klon) sayisi. Toplam analitik hacimle tutmazsa ValueError.
    """
    import openmc
    geo = model.geometry
    geo.determine_paths()
    hucreler = geo.get_all_cells()
    kafesler = geo.get_all_lattices()
    klon_sayisi = 0
    for ad, mat in yanacak.items():
        if mat.num_instances <= 1:
            continue
        toplam = 0.0
        for hucre in (c for c in hucreler.values() if c.fill is mat):
            hacimler = [ornek_hacmi(y, hucreler, kafesler) for y in hucre.paths]
            if any(v is None for v in hacimler):
                raise ValueError(_("'%s' malzemesinin bir örneğinin hacmi hesaplanamıyor "
                                 "(hücre %d); çubuk çubuk yanma kesin hacim gerektirir")
                                 % (ad, hucre.id))
            klonlar = [_klon(mat, v) for v in hacimler]
            hucre.fill = klonlar if len(klonlar) > 1 else klonlar[0]
            toplam += sum(hacimler)
            klon_sayisi += len(klonlar)
        beklenen = hv[ad]["hacim"]
        if abs(toplam - beklenen) > _GORELI_TOLERANS * beklenen:
            raise ValueError(_("'%s': örnek hacimleri toplamı %.8g cm³, analitik hacim "
                             "%.8g cm³ — tutmuyor") % (ad, toplam, beklenen))
    model.materials = openmc.Materials(geo.get_all_materials().values())
    return klon_sayisi


def _klon(mat, hacim):
    k = mat.clone()
    k.depletable = True
    k.volume = hacim
    return k


def nokta_yolu(geo, nokta):
    """
    (yaprak hucre, Cell.paths bicimli yol dizesi) ya da None (model disi ya da
    kafesin dis dolgusu). Test yardimcisi: ornek sirasini openmc.lib ile
    karsilastirmak icin.
    """
    import numpy as np
    import openmc
    evren, p, yol = geo.root_universe, np.array(nokta, dtype=float), ""
    while True:
        yol += "u%d" % evren.id
        hucre = next((c for c in evren.cells.values()
                      if c.region is None or tuple(p) in c.region), None)
        if hucre is None:
            return None
        yol += "->c%d" % hucre.id
        if hucre.translation is not None:
            p = p - np.array(hucre.translation, dtype=float)
        if hucre.fill_type == "universe":
            evren, yol = hucre.fill, yol + "->"
        elif hucre.fill_type == "lattice":
            kafes = hucre.fill
            idx, p = kafes.find_element(p)
            if not kafes.is_valid_index(idx):
                return None
            # Cell.paths 2B altigen kafeste (x, alfa) yazar; find_element z ekler
            yazim = idx[:2] if (isinstance(kafes, openmc.HexLattice)
                                and kafes.num_axial is None) else idx
            yol += "->l%d(%s)->" % (kafes.id, ",".join(str(i) for i in yazim))
            evren = kafes.get_universe(idx)
        else:
            return hucre, yol
