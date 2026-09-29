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

SQ3 = math.sqrt(3.0)
KESIN_DEGIL = "stokastik hesap gerekli"
_GORELI_TOLERANS = 1e-9


# ============================================================================
# 1. dogrudan yerlesim (spec)
# ============================================================================

def kor_hucre_alani(kor):
    """Haritali korun konum hucresi alani [cm2]."""
    P = float(kor.get("adim") or 0.0)
    return SQ3 / 2.0 * P * P if kor.get("tur") == "altigen_kafes" else P * P


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
            parcalar.append("kor haritası: %d konum × %g cm" % (n, h))
        for d in spec.get("demetler") or []:
            ic, dis = _demet_konum_sayilari(d, ad)
            if not (ic or dis):
                continue
            m = _tk._kor_sayimi(spec, kor, dolgu, d["ad"], esleme)
            if not m:
                continue
            if dis:
                sorunlar.append("'%s' demetinin dış halkasında (pin hücresi zarfla "
                                "kırpılır)" % d["ad"])
            if ic:
                V += m * ic * _demet_hucre_alani(d) * h
                ornek += m * ic
                parcalar.append("%s: %d konum × %d demet × %g cm" % (d["ad"], ic, m, h))
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
            sorunlar.append("'%s' demetinin dış dolgusu" % d["ad"])
        k = d.get("kilif") if d.get("tur") == "altigen" else None
        if isinstance(k, dict) and k.get("malzeme") == ad:
            sorunlar.append("'%s' demetinin kılıfı" % d["ad"])
    y = kor.get("yansitici") or {}
    if y.get("var") and y.get("malzeme") == ad and kor.get("tur") != "tamburlu":
        sorunlar.append("kor yansıtıcısı")
    return sorunlar


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


def _z_uzunlugu(bolge):
    """Bolgenin z yonundeki sonlu uzunlugu; sonsuzsa None."""
    if bolge is None:
        return None
    try:
        alt, ust = bolge.bounding_box
    except (AttributeError, NotImplementedError, TypeError, ValueError):
        return None
    uzun = float(ust[2]) - float(alt[2])
    return uzun if math.isfinite(uzun) else None


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
    kisa sonlu z uzunlugu (katman); hic yoksa 2B, 1 cm.
    """
    ogeler = _yol_ogeleri(yol, hucreler, kafesler)
    alan = None
    for tur, nesne in reversed(ogeler):
        alan = _kafes_hucre_alani(nesne) if tur == "l" else bolge_alani(nesne.region)
        if alan is not None or (tur == "c" and nesne.region is not None):
            break
    if alan is None:
        return None
    uzunluklar = [u for t, n in ogeler if t == "c" for u in [_z_uzunlugu(n.region)]
                  if u is not None]
    return alan * (min(uzunluklar) if uzunluklar else 1.0)


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
                raise ValueError("'%s' malzemesinin bir örneğinin hacmi hesaplanamıyor "
                                 "(hücre %d); çubuk çubuk yanma kesin hacim gerektirir"
                                 % (ad, hucre.id))
            klonlar = [_klon(mat, v) for v in hacimler]
            hucre.fill = klonlar if len(klonlar) > 1 else klonlar[0]
            toplam += sum(hacimler)
            klon_sayisi += len(klonlar)
        beklenen = hv[ad]["hacim"]
        if abs(toplam - beklenen) > _GORELI_TOLERANS * beklenen:
            raise ValueError("'%s': örnek hacimleri toplamı %.8g cm³, analitik hacim "
                             "%.8g cm³ — tutmuyor" % (ad, toplam, beklenen))
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
