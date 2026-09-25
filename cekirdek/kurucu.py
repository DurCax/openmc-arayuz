# -*- coding: utf-8 -*-
"""
================================================================================
 kurucu.py  --  spec -> openmc.Model
================================================================================

 Model tanimini (sema.py bicimimde JSON spec) calisir bir openmc.Model
 nesnesine cevirir. XML elle uretilmez; her sey openmc nesneleri uzerinden
 gecer, boylece OpenMC'nin kendi dogrulamasi devrede kalir.

 KULLANIM
   from cekirdek import kurucu, sema
   spec = sema.yukle("ornekler/pwr_pinhucre.json")
   model, bilgi = kurucu.kur(spec)
   model.export_to_model_xml("kosu/model.xml")

 DONEN BILGI SOZLUGU
   bilgi["malzemeler"] : {spec_adi: openmc.Material}
   bilgi["renkler"]    : {openmc.Material: (R,G,B)}   -- Model.plot() icin
   bilgi["universeler"]: {spec_adi: openmc.Universe}
   bilgi["sinir_kutu"] : (genislik_x, genislik_y)     -- onizleme icin

 DESTEKLENEN KOR TURLERI
   tek_cubuk   : tek yakit cubugu, yansitici/vakum sinirli hucre (pin cell)
   tek_demet   : tek kafes demeti
   kare_kafes  : demetlerden olusan kare kor + istege bagli yansitici
   tek_plaka   : MTR tipi plaka yakit elemani

 NOT
   Kafes katmani kafes tipinden bagimsiz yazilmistir: spec'te "kare" ->
   RectLattice, "altigen" -> HexLattice. Altigen destegi hazir ama ilk
   surumde ornek/arayuz tarafinda kullanilmiyor.
================================================================================
"""

import math

import openmc

from cekirdek import altigen
from cekirdek import tambur as _tambur
from cekirdek import kaynak as _kaynak
from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import eksenel_katmanlar as sema_eksenel_katmanlar
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul

# Varsayilan renk (spec'te renk verilmemis malzemeler icin)
_VARSAYILAN_RENK = (170, 170, 170)


# ============================================================================
# 1. MALZEMELER
# ============================================================================

def malzemeleri_kur(spec):
    """
    spec["malzemeler"] -> {ad: openmc.Material}, openmc.Materials, renk haritasi
    """
    nesneler = {}
    renkler = {}
    for m in spec["malzemeler"]:
        mat = openmc.Material(name=m.get("gorunen_ad") or m["ad"])
        for b in m["bilesim"]:
            miktar = b["miktar"]
            birim = b.get("birim", "ao")
            if b.get("tur") == "nuklid":
                mat.add_nuclide(b["isim"], miktar, percent_type=birim)
            else:
                zeng = b.get("zenginlik")
                if zeng is not None:
                    mat.add_element(b["isim"], miktar, percent_type=birim,
                                    enrichment=zeng)
                else:
                    mat.add_element(b["isim"], miktar, percent_type=birim)
        yog = m["yogunluk"]
        mat.set_density(yog["birim"], yog["deger"])
        if m.get("sicaklik"):
            mat.temperature = m["sicaklik"]
        for s in m.get("sab", []):
            mat.add_s_alpha_beta(s)
        nesneler[m["ad"]] = mat
        renkler[mat] = tuple(m["renk"]) if m.get("renk") else _VARSAYILAN_RENK
    return nesneler, openmc.Materials(list(nesneler.values())), renkler


def _mat(nesneler, ad):
    """Malzeme adini nesneye cevirir; "bosluk" veya None -> None (void)."""
    if ad is None or ad == BOSLUK:
        return None
    if ad not in nesneler:
        raise KeyError("tanimsiz malzeme: %s" % ad)
    return nesneler[ad]


# ============================================================================
# 2. CUBUK VE PLAKA UNIVERSE'LERI
# ============================================================================

def cubuk_universe(spec, cubuk_ad, nesneler):
    """
    Es merkezli silindirik cubugu bir openmc.Universe olarak kurar.
    openmc.model.pin() kullanilir: n yuzey -> n+1 bolge.
    """
    c = cubuk_bul(spec, cubuk_ad)
    if c is None:
        raise KeyError("tanimsiz cubuk: %s" % cubuk_ad)

    bolgeler = c["bolgeler"]
    if not bolgeler:
        raise ValueError("cubuk '%s' bos" % cubuk_ad)
    if bolgeler[-1].get("r") is not None:
        raise ValueError("cubuk '%s': son bolgenin 'r' degeri null olmali "
                         "(disarisi anlamina gelir)" % cubuk_ad)

    yuzeyler = [openmc.ZCylinder(r=b["r"]) for b in bolgeler[:-1]]
    dolgular = [_mat(nesneler, b["malzeme"]) for b in bolgeler]

    if c.get("tur") != "kontrol":
        return openmc.model.pin(yuzeyler, dolgular)

    # ---------------- eksenel hareket eden kontrol cubugu ----------------
    # Emici bolge, cubuk UCUNDE bir ZPlane ile ikiye bolunur:
    #   ucun USTU  -> emici   (cubuk oraya dalmis)
    #   ucun ALTI  -> izleyici (henuz dalmamis kisim)
    # Diger bolgeler (zarf, sogutucu) tum yuksekligi kaplar.
    #
    # pin() burada kullanilamaz: pin() yalnizca RADYAL bolme yapar.
    h = sema_kor_yuksekligi(spec["kor"])
    if not h:
        raise ValueError(
            "kontrol cubugu '%s' 3B model gerektirir: kor yuksekligi tanimli degil. "
            "Eksenel bir uc konumu olmadan daldirma tanimlanamaz." % cubuk_ad)
    daldirma = float(c.get("daldirma") or 0.0)
    if not (0.0 <= daldirma <= 100.0):
        raise ValueError("kontrol cubugu '%s': daldirma %%0-%%100 arasinda olmali (%s)"
                         % (cubuk_ad, daldirma))
    # Daldirma AKTIF YAKIT araliginda tanimlidir, modelin toplam yuksekliginde
    # degil: %0 = uc aktif bolgenin tepesinde, %100 = dibinde. Eksenel
    # katmanlama yokken ikisi ayni sey oldugu icin eski davranis korunur.
    z_alt, z_ust = aktif_eksenel_aralik(spec) or (-h / 2.0, h / 2.0)
    z_uc = z_ust - (daldirma / 100.0) * (z_ust - z_alt)
    uc_duzlem = openmc.ZPlane(z_uc)

    emici_ix = int(c.get("emici_bolge") or 0)
    if not (0 <= emici_ix < len(bolgeler)):
        raise ValueError("kontrol cubugu '%s': gecersiz emici bolge %d"
                         % (cubuk_ad, emici_ix))
    izleyici = _mat(nesneler, c.get("izleyici_malzeme"))

    hucreler = []
    for i in range(len(bolgeler)):
        if i == 0:
            radyal = -yuzeyler[0] if yuzeyler else None
        elif i == len(bolgeler) - 1:
            radyal = +yuzeyler[-1]
        else:
            radyal = +yuzeyler[i - 1] & -yuzeyler[i]
        if i == emici_ix:
            ust = radyal & +uc_duzlem if radyal is not None else +uc_duzlem
            alt = radyal & -uc_duzlem if radyal is not None else -uc_duzlem
            hucreler.append(openmc.Cell(fill=dolgular[i], region=ust))
            hucreler.append(openmc.Cell(fill=izleyici, region=alt))
        else:
            hucreler.append(openmc.Cell(fill=dolgular[i], region=radyal))
    return openmc.Universe(cells=hucreler)


def plaka_universe(spec, plaka_ad, nesneler):
    """
    MTR tipi duz plaka yakit elemanini bir Universe olarak kurar.

    x yonu (istifleme):  kanal [zarf|et|zarf] kanal [zarf|et|zarf] ... kanal
    y yonu:              -G/2 .. +G/2 aktif genislik; disinda yan levhalar
    Eleman merkezi orijindedir.
    """
    p = plaka_bul(spec, plaka_ad)
    if p is None:
        raise KeyError("tanimsiz plaka elemani: %s" % plaka_ad)

    n = p["plaka_sayisi"]
    et = p["et_kalinlik"]
    zarf = p["zarf_kalinlik"]
    kanal = p["kanal_kalinlik"]
    gen = p["plaka_genislik"]
    yan = p.get("yan_levha_kalinlik", 0.0)

    plaka_kal = 2.0 * zarf + et
    top_x = n * plaka_kal + (n + 1) * kanal
    top_y = gen + 2.0 * yan

    m_et = _mat(nesneler, p["et_malzeme"])
    m_zarf = _mat(nesneler, p["zarf_malzeme"])
    m_sog = _mat(nesneler, p["sogutucu"])
    m_yan = _mat(nesneler, p.get("yan_levha_malzeme") or p["zarf_malzeme"])

    # x sinirlarini kumulatif olarak uret: (x0, x1, malzeme)
    katmanlar = []
    x = -top_x / 2.0
    for i in range(n):
        katmanlar.append((x, x + kanal, m_sog)); x += kanal
        katmanlar.append((x, x + zarf, m_zarf)); x += zarf
        katmanlar.append((x, x + et,   m_et));   x += et
        katmanlar.append((x, x + zarf, m_zarf)); x += zarf
    katmanlar.append((x, x + kanal, m_sog))

    # y sinirlari: aktif bolge ve yan levhalar
    y_alt = openmc.YPlane(-gen / 2.0)
    y_ust = openmc.YPlane(+gen / 2.0)

    hucreler = []
    x_duzlemler = {}

    def xd(deger):
        """Ayni x degeri icin tek bir XPlane nesnesi paylas."""
        anahtar = round(deger, 9)
        if anahtar not in x_duzlemler:
            x_duzlemler[anahtar] = openmc.XPlane(anahtar)
        return x_duzlemler[anahtar]

    for x0, x1, mat in katmanlar:
        bolge = +xd(x0) & -xd(x1) & +y_alt & -y_ust
        hucreler.append(openmc.Cell(fill=mat, region=bolge))

    if yan > 0:
        x_sol, x_sag = xd(-top_x / 2.0), xd(+top_x / 2.0)
        yy_alt = openmc.YPlane(-top_y / 2.0)
        yy_ust = openmc.YPlane(+top_y / 2.0)
        hucreler.append(openmc.Cell(
            fill=m_yan, region=+x_sol & -x_sag & +yy_alt & -y_alt))
        hucreler.append(openmc.Cell(
            fill=m_yan, region=+x_sol & -x_sag & +y_ust & -yy_ust))

    univ = openmc.Universe(cells=hucreler)
    univ.arayuz_boyut = (top_x, top_y)     # onizleme icin saklanir
    return univ


# ============================================================================
# 3. KAFES (LATTICE)
# ============================================================================

def demet_lattice(spec, demet_ad, nesneler, universeler):
    """
    Kafes tanimini RectLattice (kare) veya HexLattice (altigen) olarak kurar.
    Kafes tipinden bagimsiz yazilmistir; yeni tip eklemek buraya bir dal eklemektir.
    """
    d = demet_bul(spec, demet_ad)
    if d is None:
        raise KeyError("tanimsiz demet: %s" % demet_ad)

    # harf -> universe cozumlemesi
    def coz(harf):
        if harf not in d["anahtar"]:
            raise KeyError("demet '%s': haritada tanimsiz harf '%s'"
                           % (demet_ad, harf))
        hedef = d["anahtar"][harf]
        if hedef not in universeler:
            universeler[hedef] = _universe_uret(spec, hedef, nesneler, universeler)
        return universeler[hedef]

    dis_mat = _mat(nesneler, d.get("dolgu_disi"))
    dis_univ = openmc.Universe(cells=[openmc.Cell(fill=dis_mat)])

    if d["tur"] == "kare":
        nx, ny = d["boyut"]
        harita = d["harita"]
        if len(harita) != ny:
            raise ValueError("demet '%s': harita %d satir, boyut %d bekliyor"
                             % (demet_ad, len(harita), ny))
        matris = []
        for satir in harita:
            if len(satir) != nx:
                raise ValueError("demet '%s': '%s' satiri %d karakter, %d bekleniyor"
                                 % (demet_ad, satir, len(satir), nx))
            matris.append([coz(h) for h in satir])
        lat = openmc.RectLattice()
        lat.pitch = (d["adim"], d["adim"])
        lat.lower_left = (-d["adim"] * nx / 2.0, -d["adim"] * ny / 2.0)
        lat.universes = matris
        lat.outer = dis_univ
        lat.arayuz_boyut = (d["adim"] * nx, d["adim"] * ny)
        return lat

    if d["tur"] == "altigen":
        halka = d.get("halka_sayisi") or d["boyut"][0]
        yonelim = d.get("yonelim", "y")
        beklenen = altigen.halka_uzunluklari(halka)
        harita = d["harita"]
        if len(harita) != len(beklenen):
            raise ValueError(
                "demet '%s': %d halka bekleniyor, haritada %d satir var"
                % (demet_ad, len(beklenen), len(harita)))
        for i, (satir, uzunluk) in enumerate(zip(harita, beklenen)):
            if len(satir) != uzunluk:
                raise ValueError(
                    "demet '%s': %d. halka (yaricap %d) %d oge bekliyor, %d var"
                    % (demet_ad, i + 1, halka - 1 - i, uzunluk, len(satir)))
        lat = openmc.HexLattice()
        lat.center = (0.0, 0.0)
        lat.pitch = (d["adim"],)
        lat.orientation = yonelim
        lat.outer = dis_univ
        # harita: DISTAN ICE halka listesi; her halka tepeden saat yonunde
        lat.universes = [[coz(h) for h in satir] for satir in harita]
        lat.arayuz_boyut = altigen.kapsayan_olcu(halka, d["adim"], yonelim)
        return lat

    raise ValueError("bilinmeyen kafes turu: %s" % d["tur"])


def _spec_fisil_mi(spec, ad, derinlik=0):
    """
    Spec'teki bir ad (cubuk / plaka / demet / malzeme) fisil malzeme iceriyor mu?

    Geometri kurulmadan cevaplanmasi gerekiyor: kontrol cubugunun daldirma
    ekseni ve arayuzdeki aktif yukseklik gostergesi buna bagli.
    Olcut: Z >= 90 (aktinit) bir bilesen.
    """
    import openmc.data
    if derinlik > 8 or not ad:
        return False
    m = malzeme_bul(spec, ad)
    if m is not None:
        for b in m.get("bilesim", []):
            isim = b.get("isim") or ""
            try:
                if b.get("tur") == "element":
                    z = openmc.data.ATOMIC_NUMBER.get(isim, 0)
                else:
                    z = openmc.data.zam(isim)[0]
            except Exception:
                z = 0
            if z >= 90:
                return True
        return False
    c = cubuk_bul(spec, ad)
    if c is not None:
        return any(_spec_fisil_mi(spec, b.get("malzeme"), derinlik + 1)
                   for b in c.get("bolgeler", []))
    p = plaka_bul(spec, ad)
    if p is not None:
        return any(_spec_fisil_mi(spec, p.get(k), derinlik + 1)
                   for k in ("et_malzeme", "zarf_malzeme", "kanal_malzeme",
                             "yan_levha_malzeme"))
    d = demet_bul(spec, ad)
    if d is not None:
        adaylar = list((d.get("anahtar") or {}).values()) + [d.get("dolgu_disi")]
        return any(_spec_fisil_mi(spec, x, derinlik + 1) for x in adaylar if x)
    return False


def aktif_eksenel_aralik(spec):
    """
    Aktif (fisil) yakitin eksenel araligi (z_alt, z_ust); 2B modelde None.

    Eksenel katmanlama yokken tum yukseklik aktiftir. Katmanlama varken
    yalnizca fisil dolgusu olan katmanlar sayilir -- alt/ust yansitici ve
    plenum aktif bolgeye DAHIL DEGILDIR. Kontrol cubugu daldirmasi ve
    lineer guc [W/cm] bu araliga gore tanimlidir.
    """
    kor = spec["kor"]
    h = sema_kor_yuksekligi(kor)
    if not h:
        return None
    katmanlar = sema_eksenel_katmanlar(kor)
    if katmanlar is None:
        return (-h / 2.0, h / 2.0)
    ana = kor.get("cubuk") or kor.get("demet") or kor.get("plaka") or kor.get("dolgu")
    alt, ust = None, None
    for z0, z1, katman in katmanlar:
        ad = katman.get("dolgu") or ana
        fisil = _spec_fisil_mi(spec, ad)
        if not fisil and katman.get("anahtar"):
            fisil = any(_spec_fisil_mi(spec, x)
                        for x in (katman["anahtar"] or {}).values())
        if not fisil:
            continue
        alt = z0 if alt is None else min(alt, z0)
        ust = z1 if ust is None else max(ust, z1)
    if alt is None:
        return (-h / 2.0, h / 2.0)       # fisil katman bulunamadi: tumunu kullan
    return (alt, ust)


def _iceriyor_mu(spec, kapsayan, aranan, derinlik=0):
    """'kapsayan' adli dolgu, 'aranan' cubugu/plakayi iceriyor mu?"""
    if derinlik > 8 or not kapsayan:
        return False
    if kapsayan == aranan:
        return True
    d = demet_bul(spec, kapsayan)
    if d is not None:
        adaylar = list((d.get("anahtar") or {}).values()) + [d.get("dolgu_disi")]
        return any(_iceriyor_mu(spec, x, aranan, derinlik + 1) for x in adaylar if x)
    return False


def cubuk_eksenel_aralik(spec, cubuk_ad):
    """
    Belirli bir cubugun eksenel olarak BULUNDUGU aralik (z_alt, z_ust).

    Guc dagilimi eksenel mesh'i bunu kullanir. "Fisil aralik" yetmez:
    dogal uranyum blanket fisildir ama iceriginde HEDEF cubuk yoktur; mesh
    oraya tasarsa bos bin'ler ortalamayi duserir ve F_q YAPAY OLARAK SISER.
    (Olculdu: pwr_eksenel'de F_q 1.815 -> 1.712, %6 fark.)
    """
    kor = spec["kor"]
    h = sema_kor_yuksekligi(kor)
    if not h:
        return None
    katmanlar = sema_eksenel_katmanlar(kor)
    if katmanlar is None:
        return (-h / 2.0, h / 2.0)
    ana = kor.get("cubuk") or kor.get("demet") or kor.get("plaka") or kor.get("dolgu")
    alt, ust = None, None
    for z0, z1, katman in katmanlar:
        adaylar = [katman.get("dolgu") or ana]
        adaylar += list((katman.get("anahtar") or {}).values())
        if not any(_iceriyor_mu(spec, x, cubuk_ad) for x in adaylar if x):
            continue
        alt = z0 if alt is None else min(alt, z0)
        ust = z1 if ust is None else max(ust, z1)
    if alt is None:
        return aktif_eksenel_aralik(spec)
    return (alt, ust)


def _universe_uret(spec, ad, nesneler, universeler):
    """Ad bir cubuk, plaka, demet ya da malzeme olabilir -- uygun universe'i uretir."""
    if cubuk_bul(spec, ad) is not None:
        return cubuk_universe(spec, ad, nesneler)
    if plaka_bul(spec, ad) is not None:
        return plaka_universe(spec, ad, nesneler)
    if demet_bul(spec, ad) is not None:
        lat = demet_lattice(spec, ad, nesneler, universeler)
        return openmc.Universe(cells=[openmc.Cell(fill=lat)])
    if ad == BOSLUK or malzeme_bul(spec, ad) is not None:
        return openmc.Universe(cells=[openmc.Cell(fill=_mat(nesneler, ad))])
    raise KeyError("cozumlenemeyen ad: %s (cubuk/plaka/demet/malzeme degil)" % ad)


# ============================================================================
# 4. KOR VE GEOMETRI
# ============================================================================

def _eksenel_bolge(kor, taban_bolge):
    """yukseklik verilmisse alt/ust ZPlane ekler, verilmemisse 2B birakir."""
    h = sema_kor_yuksekligi(kor)
    if not h:
        return taban_bolge
    sinir = kor.get("sinir", {})
    z_alt = openmc.ZPlane(-h / 2.0, boundary_type=sinir.get("alt", "reflective"))
    z_ust = openmc.ZPlane(+h / 2.0, boundary_type=sinir.get("ust", "reflective"))
    return taban_bolge & +z_alt & -z_ust


def _altigen_mi(spec, kor):
    """Kor dolgusu bir altigen kafes mi? (sinir yuzeyi secimi icin)"""
    if kor["tur"] == "tek_demet":
        d = demet_bul(spec, kor.get("demet") or "")
        return d is not None and d.get("tur") == "altigen"
    return False


def _altigen_sinir(halka_sayisi, adim, kafes_yonelimi, bc, buyutme=0.0):
    """
    Altigen kafesi saran HexagonalPrism uretir.

    YONELIM  (olcumle dogrulandi, bkz. testler -> test_altigen_sinir)
      HexLattice 'y' : halkanin ilk ogesi TEPEDE  -> pin zarfi tepede SIVRI,
                       sag/solda DUZ kenar.
      HexagonalPrism 'y' : duz yuzler y eksenine paralel, yani sag/solda DUSEY.
      Ikisi ortusur -> prizma yonelimi kafes yonelimiyle AYNIDIR.
      ('x' icin de ayni sekilde ortusur.)

    OLCU
      Duz yuze en yakin pinler, zarfin duz kenarindaki pinlerdir:
          en_yakin = (halka_sayisi - 1) * adim * cos(30)
      Komsu demetle pin araligi surekli olsun diye yariM adim bosluk birakilir:
          apothem = (halka_sayisi - 1) * adim * sqrt(3)/2 + adim/2
      HexagonalPrism'de apothem = kenar * sqrt(3)/2  ->  kenar = 2*apothem/sqrt(3)

      NOT: koselerde acikliK yariM adimdan buyuktur; bu altigen demetlerin
      gercek geometrisinde de boyledir.
    """
    ic_yaricap = (halka_sayisi - 1) * adim * math.sqrt(3.0) / 2.0 + adim / 2.0 + buyutme
    kenar = 2.0 * ic_yaricap / math.sqrt(3.0)
    return openmc.model.HexagonalPrism(edge_length=kenar,
                                       orientation=kafes_yonelimi,
                                       boundary_type=bc)


def _kare_kafes_kur(spec, kor, nesneler, universeler, anahtar=None):
    """
    kare_kafes korunun RectLattice'ini kurar.

    "anahtar" verilirse harita ayni kalir ama harf -> demet eslemesi degisir.
    Eksenel zenginlik kusaklama boyle yapilir: hangi konumda ne oldugu
    (harita) eksenel olarak degismez -- fiziksel olarak da degismez, demetler
    yerinden oynamaz -- degisen yalnizca her harfin O KATMANDA ne anlama
    geldigidir.
    """
    nx, ny = kor["boyut"]
    harita = kor["harita"]
    esleme = dict(kor["anahtar"])
    if anahtar:
        esleme.update(anahtar)

    def coz(harf):
        if harf not in esleme:
            raise KeyError("kor haritasinda tanimsiz harf: '%s'" % harf)
        hedef = esleme[harf]
        if hedef not in universeler:
            universeler[hedef] = _universe_uret(spec, hedef, nesneler, universeler)
        return universeler[hedef]

    if len(harita) != ny:
        raise ValueError("kor haritasi %d satir, boyut %d bekliyor"
                         % (len(harita), ny))
    lat = openmc.RectLattice()
    lat.pitch = (kor["adim"], kor["adim"])
    lat.lower_left = (-kor["adim"] * nx / 2.0, -kor["adim"] * ny / 2.0)
    lat.universes = [[coz(h) for h in satir] for satir in harita]
    dis_mat = _mat(nesneler, (kor.get("yansitici") or {}).get("malzeme"))
    lat.outer = openmc.Universe(cells=[openmc.Cell(fill=dis_mat)])
    return lat


def _katman_dolgusu(spec, kor, katman, ana_ic, nesneler, universeler):
    """Bir eksenel katmani dolduracak universe/lattice."""
    if katman.get("anahtar"):
        if kor["tur"] != "kare_kafes":
            raise ValueError(
                "eksenel katman '%s': katmana ozel 'anahtar' yalnizca kare_kafes "
                "korunda kullanilabilir" % katman.get("ad"))
        return _kare_kafes_kur(spec, kor, nesneler, universeler, katman["anahtar"])
    dolgu = katman.get("dolgu")
    if not dolgu:
        return ana_ic
    anahtar = "__katman__%s" % dolgu
    if anahtar not in universeler:
        universeler[anahtar] = _universe_uret(spec, dolgu, nesneler, universeler)
    return universeler[anahtar]


def _eksenel_hucreler(spec, kor, taban_bolge, ana_ic, nesneler, universeler,
                      ad_oneki=""):
    """
    Yanal bolgesi "taban_bolge" olan hacmi eksenel katmanlara boler.

    Katmanlama kapaliysa tek bir hucre doner ve davranis eskisiyle aynidir.
    Katman arayuzleri DAIMA 'transmission'dir; sinir kosulu yalnizca en alt
    ve en ust yuzeye uygulanir -- ic bir yuzeye yansitici sinir konmasi
    korun ustunu altindan koparir ve bunu k-eff'e bakarak fark etmek zordur.
    """
    katmanlar = sema_eksenel_katmanlar(kor)
    if katmanlar is None:
        return [openmc.Cell(fill=ana_ic, region=_eksenel_bolge(kor, taban_bolge))]

    sinir = kor.get("sinir", {})
    h = katmanlar[-1][1] - katmanlar[0][0]
    duzlemler = [openmc.ZPlane(-h / 2.0, boundary_type=sinir.get("alt", "reflective"))]
    for _z0, z1, _b in katmanlar[:-1]:
        duzlemler.append(openmc.ZPlane(z1))          # ic arayuz: transmission
    duzlemler.append(openmc.ZPlane(+h / 2.0, boundary_type=sinir.get("ust", "reflective")))

    hucreler = []
    for i, (_z0, _z1, katman) in enumerate(katmanlar):
        ic = _katman_dolgusu(spec, kor, katman, ana_ic, nesneler, universeler)
        bolge = +duzlemler[i] & -duzlemler[i + 1]
        if taban_bolge is not None:
            bolge = taban_bolge & bolge
        hucreler.append(openmc.Cell(
            fill=ic, region=bolge,
            name="%s%s" % (ad_oneki, katman.get("ad") or "katman %d" % (i + 1))))
    return hucreler


def kor_kur(spec, nesneler, universeler):
    """Kor duzenini kurar; (kok_universe, (genislik_x, genislik_y)) dondurur."""
    kor = spec["kor"]
    tur = kor["tur"]
    yan_bc = kor.get("sinir", {}).get("yan", "reflective")
    altigen_kor = _altigen_mi(spec, kor)

    # --- ic dolgu ve onun yanal olculeri ---
    if tur == "tek_cubuk":
        # universeler sozlugune kaydedilir: guc dagilimi tally'si hedef cubugun
        # GEOMETRIDEKI universe nesnesine ihtiyac duyar, yeniden kurulmus bir
        # kopyaya degil (distribcell hucre kimligine baglidir).
        ic = universeler.setdefault(kor["cubuk"],
                                    cubuk_universe(spec, kor["cubuk"], nesneler))
        gx = gy = kor["adim"]
    elif tur == "tek_plaka":
        ic = universeler.setdefault(kor["plaka"],
                                    plaka_universe(spec, kor["plaka"], nesneler))
        gx, gy = ic.arayuz_boyut
    elif tur == "tek_demet":
        ic = demet_lattice(spec, kor["demet"], nesneler, universeler)
        gx, gy = ic.arayuz_boyut
    elif tur == "tamburlu":
        # Silindirik kor + yansitici kusak + kusaga gomulu donen tamburlar.
        R_kor = float(kor.get("kor_yaricap") or 0.0)
        yans = kor.get("yansitici") or {}
        kal = float(yans.get("kalinlik") or 0.0)
        R_dis = R_kor + kal
        if R_kor <= 0 or kal <= 0:
            raise ValueError("tamburlu korda kor yaricapi ve yansitici "
                             "kalinligi pozitif olmali")
        t = kor.get("tambur") or {}
        hatalar = _tambur.geometri_kontrol(t, R_kor, kal) if int(t.get("sayi") or 0) else []
        if hatalar:
            raise ValueError("tambur yerlesimi gecersiz: " + hatalar[0])

        dolgu_ad = kor.get("dolgu")
        if not dolgu_ad:
            raise ValueError("tamburlu korda 'dolgu' secilmeli "
                             "(kafes, cubuk ya da malzeme adi)")
        if dolgu_ad not in universeler:
            universeler[dolgu_ad] = _universe_uret(spec, dolgu_ad, nesneler, universeler)
        ic_univ = universeler[dolgu_ad]

        kor_silindir = openmc.ZCylinder(r=R_kor)
        dis_silindir = openmc.ZCylinder(r=R_dis, boundary_type=yan_bc)

        # Kor silindirinin ici eksenel katmanlara ayrilabilir (alt/ust
        # yansitici, plenum). Tamburlar ve yanal yansitici kusak TAM
        # YUKSEKLIGI kaplar -- tambur eksenel olarak bolunmez.
        hucreler = _eksenel_hucreler(spec, kor, -kor_silindir, ic_univ,
                                     nesneler, universeler)
        yansitici_bolge = +kor_silindir & -dis_silindir
        if int(t.get("sayi") or 0) > 0:
            t_univ = _tambur.universe(t, nesneler, _mat)
            for x, y, psi in _tambur.yerlesim(t):
                delik = openmc.ZCylinder(x0=x, y0=y, r=float(t["yaricap"]))
                h = openmc.Cell(fill=t_univ,
                                region=_eksenel_bolge(kor, -delik))
                h.translation = (x, y, 0.0)
                # psi emici yayi DOGRUDAN psi acisina koyar (olcumle dogrulandi)
                h.rotation = (0.0, 0.0, psi)
                hucreler.append(h)
                yansitici_bolge = yansitici_bolge & +delik
        hucreler.append(openmc.Cell(fill=_mat(nesneler, yans.get("malzeme")),
                                    region=_eksenel_bolge(kor, yansitici_bolge)))
        return openmc.Universe(cells=hucreler), (2 * R_dis, 2 * R_dis)

    elif tur == "kuresel":
        # Es merkezli kuresel kabuklar. Eksenel sinir yoktur; en dis kabugun
        # yuzeyi modelin sinir yuzeyidir. Kritik kure kriterleri icin.
        kabuklar = kor.get("kabuklar") or []
        if not kabuklar:
            raise ValueError("kuresel korda en az bir kabuk gerekir")
        yaricaplar = [k["r"] for k in kabuklar]
        for i in range(len(yaricaplar) - 1):
            if yaricaplar[i] >= yaricaplar[i + 1]:
                raise ValueError("kabuk yaricaplari artan sirada olmali: "
                                 "r%d=%.5f >= r%d=%.5f"
                                 % (i + 1, yaricaplar[i], i + 2, yaricaplar[i + 1]))
        hucreler = []
        onceki = None
        for i, k in enumerate(kabuklar):
            son = (i == len(kabuklar) - 1)
            yuzey = openmc.Sphere(r=k["r"],
                                  boundary_type=yan_bc if son else "transmission")
            bolge = -yuzey if onceki is None else (+onceki & -yuzey)
            hucreler.append(openmc.Cell(fill=_mat(nesneler, k.get("malzeme")),
                                        region=bolge))
            onceki = yuzey
        capi = 2.0 * yaricaplar[-1]
        return openmc.Universe(cells=hucreler), (capi, capi)

    elif tur == "kare_kafes":
        nx, ny = kor["boyut"]
        ic = _kare_kafes_kur(spec, kor, nesneler, universeler)
        gx, gy = kor["adim"] * nx, kor["adim"] * ny
    else:
        raise ValueError("bilinmeyen kor turu: %s" % tur)

    yans = kor.get("yansitici") or {}
    yans_var = yans.get("var") and tur in ("tek_demet", "kare_kafes")

    # --- altigen kor: HexagonalPrism sinirlari ---
    if altigen_kor:
        d = demet_bul(spec, kor["demet"])
        halka = d.get("halka_sayisi") or d["boyut"][0]
        yonelim = d.get("yonelim", "y")
        if yans_var:
            kal = yans["kalinlik"]
            ic_prizma = _altigen_sinir(halka, d["adim"], yonelim, "transmission")
            dis_prizma = _altigen_sinir(halka, d["adim"], yonelim, yan_bc, buyutme=kal)
            hucreler = _eksenel_hucreler(spec, kor, -ic_prizma, ic,
                                         nesneler, universeler)
            hucreler.append(openmc.Cell(
                fill=_mat(nesneler, yans.get("malzeme")),
                region=_eksenel_bolge(kor, +ic_prizma & -dis_prizma)))
            olcu = altigen.kapsayan_olcu(halka, d["adim"], yonelim)
            return openmc.Universe(cells=hucreler), (olcu[0] + 2 * kal, olcu[1] + 2 * kal)
        prizma = _altigen_sinir(halka, d["adim"], yonelim, yan_bc)
        return (openmc.Universe(cells=_eksenel_hucreler(
            spec, kor, -prizma, ic, nesneler, universeler)), (gx, gy))

    # --- yansitici (dikdortgen) ---
    if yans_var:
        kal = yans["kalinlik"]
        ic_kutu = openmc.model.RectangularPrism(gx, gy)
        dis_gx, dis_gy = gx + 2 * kal, gy + 2 * kal
        dis_kutu = openmc.model.RectangularPrism(dis_gx, dis_gy,
                                                 boundary_type=yan_bc)
        hucreler = _eksenel_hucreler(spec, kor, -ic_kutu, ic, nesneler, universeler)
        hucreler.append(openmc.Cell(
            fill=_mat(nesneler, yans.get("malzeme")),
            region=_eksenel_bolge(kor, +ic_kutu & -dis_kutu)))
        return openmc.Universe(cells=hucreler), (dis_gx, dis_gy)

    kutu = openmc.model.RectangularPrism(gx, gy, boundary_type=yan_bc)
    return (openmc.Universe(cells=_eksenel_hucreler(
        spec, kor, -kutu, ic, nesneler, universeler)), (gx, gy))


# ============================================================================
# 5. AYARLAR VE TALLY'LER
# ============================================================================

def ayarlari_kur(spec, sinir_kutu, fisil_aralik=None):
    """spec["ayarlar"] -> openmc.Settings"""
    a = spec["ayarlar"]
    s = openmc.Settings()
    s.run_mode = a.get("mod", "eigenvalue")
    s.particles = int(a["parcacik"])
    s.batches = int(a["cevrim"])
    if s.run_mode == "eigenvalue":
        s.inactive = int(a["pasif"])
    if a.get("tohum"):
        s.seed = int(a["tohum"])
    if a.get("sicaklik_yontemi"):
        s.temperature = {"method": a["sicaklik_yontemi"]}

    k = a.get("kaynak") or {}
    if k.get("tur") == "kutu":
        # !!! Z ARALIGI MODELIN YUKSEKLIGINI KAPSAMALIDIR !!!
        #   Onceki surumde z araligi +/-1.0 cm'ye sabitti. 2B modelde sorun
        #   degildi ama 366 cm'lik 3B bir modelde kaynak merkezdeki 2 cm'lik
        #   bir dilimde basliyordu; eksenel sekil onlarca cevrim boyunca
        #   yayilmaya calisiyor ve GUC DAGILIMI YANLIS (asiri tepeli) cikiyordu.
        #   Shannon entropisi bunu gostermiyor: entropi global bir skalerdir ve
        #   bu geometride radyal dagilim baskin geliyor.
        h = sema_kor_yuksekligi(spec["kor"])
        # Eksenel katmanlamada kutu, tum modeli degil FISIL araligi kapsar:
        # yansitici ve plenum katmanlarinda orneklenen noktalar "fissionable"
        # kisiti yuzunden reddedilirdi, bu da yakinsamayi bosa yavaslatir.
        if fisil_aralik:
            z_alt, z_ust = fisil_aralik
        else:
            yari_z = (h / 2.0) if h else 1.0
            z_alt, z_ust = -yari_z, +yari_z
        alt = k.get("alt") or [-sinir_kutu[0] / 2, -sinir_kutu[1] / 2, z_alt]
        ust = k.get("ust") or [+sinir_kutu[0] / 2, +sinir_kutu[1] / 2, z_ust]
        uzay = openmc.stats.Box(alt, ust)
        kisit = {"fissionable": True}
    else:
        uzay = openmc.stats.Point(tuple(k.get("konum") or (0.0, 0.0, 0.0)))
        kisit = None
    s.source = _kaynak.kaynak_kur(k, uzay, kisit)
    # Foton kaynagi foton tasinimi gerektirir; acilmazsa parcaciklar hicbir
    # etkilesime girmeden gecer ve sonuc sessizce ANLAMSIZ olur.
    if (k.get("parcacik") or "neutron") == "photon":
        s.photon_transport = True

    # --- Shannon entropisi mesh'i (kaynak yakinsamasi olcumu) ---
    ent = a.get("entropi_mesh") or {}
    if ent.get("var") and s.run_mode == "eigenvalue":
        gx, gy = sinir_kutu
        mesh = openmc.RegularMesh()
        mesh.dimension = list(ent.get("boyut") or [8, 8, 1])
        # Eksenel sinirlar: 3B modelde GERCEK kor yuksekligi kullanilmali.
        #   Onceki surumde z daima +/-1e10 idi. nz=1 iken zararsizdi, ama
        #   nz>1 istendiginde iki bin de 1e10 cm yuksekliginde oluyor, hepsi
        #   ayni dilime dusuyor ve EKSENEL yakinsama olculmemis oluyordu --
        #   entropi yine de "yakinsadi" diyordu. Eksenel heterojen bir korda
        #   (blanket, plenum) asil riskli yon tam da budur.
        h = sema_kor_yuksekligi(spec["kor"])
        z = (h / 2.0) if h else 1.0e10
        mesh.lower_left = (-gx / 2.0, -gy / 2.0, -z)
        mesh.upper_right = (gx / 2.0, gy / 2.0, z)
        s.entropy_mesh = mesh
    return s


def tallyleri_kur(spec, nesneler):
    """spec["tallyler"] -> openmc.Tallies"""
    liste = []
    for t in spec.get("tallyler", []):
        tal = openmc.Tally(name=t["ad"])
        tal.scores = list(t["skorlar"])
        if t.get("nuklidler"):
            tal.nuclides = list(t["nuklidler"])
        filtreler = []
        for f in t.get("filtreler", []):
            if f["tur"] == "enerji":
                filtreler.append(openmc.EnergyFilter(f["gruplar"]))
            elif f["tur"] == "mesh":
                mesh = openmc.RegularMesh()
                mesh.dimension = f["boyut"]
                mesh.lower_left = f["alt"]
                mesh.upper_right = f["ust"]
                filtreler.append(openmc.MeshFilter(mesh))
            elif f["tur"] == "malzeme":
                filtreler.append(openmc.MaterialFilter(
                    [nesneler[a] for a in f["adlar"]]))
            else:
                raise ValueError("bilinmeyen filtre turu: %s" % f["tur"])
        tal.filters = filtreler
        liste.append(tal)
    return openmc.Tallies(liste)


# ============================================================================
# 6. ANA GIRIS
# ============================================================================

def guc_tally_ekle(spec, model, nesneler, universeler, sinir_kutu,
                   fisil_aralik=None):
    """
    Cubuk bazli guc dagilimi tally'sini modele ekler.

    DistribcellFilter hedef cubugun belirtilen bolgesinin hucresine baglanir;
    3B modelde buna 1x1xN'lik bir MeshFilter eklenerek eksenel cozunurluk
    saglanir.

    !!! EKSENEL MESH AKTIF YAKIT YUKSEKLIGIYLE TAM ORTUSMELIDIR !!!
      Mesh yakittan tasarsa bos bin'ler ortalamayi dusurur ve F_q yapay olarak
      sisrer. Bu yuzden mesh sinirlari kor yuksekliginden TURETILIR, elle
      girilmez.

    DONER (hucre, kafes_var_mi)
    """
    from cekirdek import guc as _guc

    g = spec.get("guc_dagilimi") or {}
    cubuk_ad = g.get("cubuk")
    c = cubuk_bul(spec, cubuk_ad) if cubuk_ad else None
    if c is None:
        raise ValueError("guc dagilimi icin gecerli bir cubuk secilmeli "
                         "(secili: %r)" % cubuk_ad)
    univ = universeler.get(cubuk_ad)
    if univ is None:
        raise ValueError(
            "'%s' cubugu modelde kullanilmiyor. Guc dagilimi yalnizca geometride "
            "yer alan bir cubuk icin hesaplanabilir." % cubuk_ad)

    hucreler = _guc.bolge_hucresi(univ, c, nesneler)
    bolge_no = int(g.get("bolge") or 0)
    if not (0 <= bolge_no < len(hucreler)):
        raise ValueError("gecersiz bolge numarasi %d (cubukta %d bolge var)"
                         % (bolge_no, len(hucreler)))
    hedef = hucreler[bolge_no]

    tal = openmc.Tally(name="guc_dagilimi")
    tal.scores = [g.get("skor") or "kappa-fission"]
    filtreler = [openmc.DistribcellFilter(hedef)]

    h = sema_kor_yuksekligi(spec["kor"])
    dilim = int(g.get("eksenel_dilim") or 1)
    if h and dilim > 1:
        gx, gy = sinir_kutu
        pay = max(gx, gy)          # x,y'de tek bin -- her seyi kapsamasi yeter
        # Mesh AKTIF YAKIT araligini kapsar, tum modeli degil: eksenel
        # katmanlamada yansitici/plenum katmanlari mesh'e girerse bos bin'ler
        # ortalamayi duserir ve F_q yapay olarak siser.
        # Mesh HEDEF CUBUGUN bulundugu araligi kapsar.
        z_alt, z_ust = cubuk_eksenel_aralik(spec, cubuk_ad) or (-h / 2.0, h / 2.0)
        mesh = openmc.RegularMesh()
        mesh.dimension = [1, 1, dilim]
        mesh.lower_left = (-pay, -pay, z_alt)
        mesh.upper_right = (pay, pay, z_ust)
        filtreler.append(openmc.MeshFilter(mesh))
    tal.filters = filtreler

    # Toplam korunumu testi icin AYNI HUCREYE bagli, bolunmemis tally.
    #   Once filtresizdi (tum model). Eksenel katmanlama gelince bu
    #   karsilastirma anlamsizlasti: dogal uranyum blanket de fisyon yapiyor
    #   ama distribcell'e dahil degil, korunum sahte olarak "BOZUK" cikiyordu.
    #   Ayni hucreye baglayinca kontrol GUCLENIYOR: artik eksenel mesh'in
    #   hucrenin tamamini kapsayip kapsamadigini da sinar.
    ref = openmc.Tally(name="guc_toplam_ref")
    ref.scores = list(tal.scores)
    ref.filters = [openmc.CellFilter(hedef)]

    model.tallies = openmc.Tallies(list(model.tallies) + [tal, ref])
    return hedef


def kur(spec):
    """
    Spec'i tam bir openmc.Model'e cevirir.

    DONER  (model, bilgi)
      model : openmc.Model
      bilgi : {"malzemeler", "renkler", "universeler", "sinir_kutu"}
    """
    openmc.reset_auto_ids()          # ardarda kurulumlarda id cakismasini onler

    nesneler, materials, renkler = malzemeleri_kur(spec)
    universeler = {}
    kok, sinir_kutu = kor_kur(spec, nesneler, universeler)

    geometry = openmc.Geometry(kok)
    # AKTIF (fisil) eksenel aralik: kaynak kutusu, guc mesh'i ve kontrol
    # cubugu daldirmasi hep bu TEK tanimdan okur. Bir zamanlar geometriden
    # turetilen ikinci bir tanim daha vardi; uretilen betik onu bilemedigi
    # icin betik ile kurucu FARKLI kaynak kutusu kuruyordu (1300 pcm).
    fisil = aktif_eksenel_aralik(spec)
    settings = ayarlari_kur(spec, sinir_kutu, fisil)
    tallies = tallyleri_kur(spec, nesneler)

    model = openmc.Model(geometry=geometry, materials=materials,
                         settings=settings, tallies=tallies)

    # --- kinetik parametreler (IFP) ---
    # add_kinetics_parameters_tallies() modele tally EKLER; bu yuzden model
    # kurulurken yapilmalidir, sonradan degil (onbellek kimliginin parcasi).
    kin = spec["ayarlar"].get("kinetik") or {}
    if kin.get("var") and settings.run_mode == "eigenvalue":
        model.add_kinetics_parameters_tallies()
        model.settings.ifp_n_generation = int(kin.get("nesil") or 10)
    bilgi = {
        "malzemeler": nesneler,
        "renkler": renkler,
        "universeler": universeler,
        "sinir_kutu": sinir_kutu,
        "guc_hucre": None,
        "aktif_aralik": fisil,
    }

    # --- cubuk bazli guc dagilimi ---
    g = spec.get("guc_dagilimi") or {}
    if g.get("var"):
        bilgi["guc_hucre"] = guc_tally_ekle(spec, model, nesneler, universeler,
                                            sinir_kutu, fisil)
    return model, bilgi
