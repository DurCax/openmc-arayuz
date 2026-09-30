# -*- coding: utf-8 -*-
"""
================================================================================
 _eski_kurucu.py  --  DONMUS eski kor kurucusu (yalniz esdegerlik kapisi icin)
================================================================================

 Dalga G-1'in ilk isi (docs/GEOMETRI_MODELI.md §9): bugunku kurucu.kor_kur ve
 butun yardimcilari (altigen_kor.kor_kur, tambur.universe/yerlesim dahil)
 DEGISTIRILMEDEN buraya kopyalandi. Yalniz testler kullanir: agac kurucusu
 (cekirdek/geometri/kur.py) ile nokta parmak izi, yapi ve hacim karsilastirmasi.
 Kapi gecince bu dosya silinir; kapi kayitli parmak izi dosyasiyla
 (testler/veri/geometri_parmak_izi.json) calismayi surdurur.

 Uretim: kurucu.py / altigen_kor.py / tambur.py'den ast ile kopya (48300b4).
 Bu dosya DUZENLENMEZ.
================================================================================
"""

import math

import openmc

from cekirdek import altigen
from cekirdek import altigen_kor as _akor
from cekirdek import tambur as _tambur
from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import eksenel_katmanlar as sema_eksenel_katmanlar
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul


def _mat(nesneler, ad):
    """Malzeme adini nesneye cevirir; "bosluk" veya None -> None (void)."""
    if ad is None or ad == BOSLUK:
        return None
    if ad not in nesneler:
        raise KeyError("tanımsız malzeme: %s" % ad)
    return nesneler[ad]


def cubuk_universe(spec, cubuk_ad, nesneler):
    """
    Es merkezli silindirik cubugu bir openmc.Universe olarak kurar.
    openmc.model.pin() kullanilir: n yuzey -> n+1 bolge.
    """
    c = cubuk_bul(spec, cubuk_ad)
    if c is None:
        raise KeyError("tanımsız çubuk: %s" % cubuk_ad)

    bolgeler = c["bolgeler"]
    if not bolgeler:
        raise ValueError("'%s' çubuğunda bölge yok" % cubuk_ad)
    if bolgeler[-1].get("r") is not None:
        raise ValueError("'%s' çubuğu: son bölgenin yarıçapı boş olmalı "
                         "(son bölge çubuğun dışıdır)" % cubuk_ad)

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
            "'%s' kontrol çubuğu 3B model gerektirir: kor yüksekliği tanımlı değil. "
            "Eksenel bir uç konumu olmadan daldırma tanımlanamaz." % cubuk_ad)
    daldirma = float(c.get("daldirma") or 0.0)
    if not (0.0 <= daldirma <= 100.0):
        raise ValueError("'%s' kontrol çubuğu: daldırma %%0–%%100 arasında olmalı (%s)"
                         % (cubuk_ad, daldirma))
    # Daldirma AKTIF YAKIT araliginda tanimlidir, modelin toplam yuksekliginde
    # degil: %0 = uc aktif bolgenin tepesinde, %100 = dibinde. Eksenel
    # katmanlama yokken ikisi ayni sey oldugu icin eski davranis korunur.
    z_alt, z_ust = aktif_eksenel_aralik(spec) or (-h / 2.0, h / 2.0)
    z_uc = z_ust - (daldirma / 100.0) * (z_ust - z_alt)
    uc_duzlem = openmc.ZPlane(z_uc)

    emici_ix = int(c.get("emici_bolge") or 0)
    if not (0 <= emici_ix < len(bolgeler)):
        raise ValueError("'%s' kontrol çubuğu: geçersiz emici bölge %d"
                         % (cubuk_ad, emici_ix + 1))
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
        raise KeyError("tanımsız plaka elemanı: %s" % plaka_ad)

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


def demet_lattice(spec, demet_ad, nesneler, universeler):
    """
    Kafes tanimini RectLattice (kare) veya HexLattice (altigen) olarak kurar.
    Kafes tipinden bagimsiz yazilmistir; yeni tip eklemek buraya bir dal eklemektir.
    """
    d = demet_bul(spec, demet_ad)
    if d is None:
        raise KeyError("tanımsız demet: %s" % demet_ad)

    # harf -> universe cozumlemesi
    def coz(harf):
        if harf not in d["anahtar"]:
            raise KeyError("'%s' demeti: haritada tanımsız harf '%s'"
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
            raise ValueError("'%s' demeti: harita %d satır, boyut %d bekliyor"
                             % (demet_ad, len(harita), ny))
        matris = []
        for satir in harita:
            if len(satir) != nx:
                raise ValueError("'%s' demeti: '%s' satırı %d karakter, %d bekleniyor"
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
                "'%s' demeti: %d halka bekleniyor, haritada %d satır var"
                % (demet_ad, len(beklenen), len(harita)))
        for i, (satir, uzunluk) in enumerate(zip(harita, beklenen)):
            if len(satir) != uzunluk:
                raise ValueError(
                    "'%s' demeti: %d. halka (yarıçap %d) %d öğe bekliyor, %d var"
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

    raise ValueError("bilinmeyen demet türü: %s" % d["tur"])


def _demet_universe(spec, ad, nesneler, universeler):
    """Demeti bir universe olarak kurar; altigen demette varsa kilifiyla."""
    d = demet_bul(spec, ad)
    lat = demet_lattice(spec, ad, nesneler, universeler)
    k = _akor.kilif(d)
    if k is None:
        return openmc.Universe(cells=[openmc.Cell(fill=lat)], name=ad)
    u = kilifli_demet_universe(
        lat, float(k["ic_duz"]), float(k["kalinlik"]), d.get("yonelim", "y"),
        _mat(nesneler, k.get("malzeme")), _mat(nesneler, d.get("dolgu_disi")))
    u.name = ad
    return u


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
            except (KeyError, ValueError):   # bilinmeyen nuklid/element adi: fisil sayilmaz
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
                   for k in ("et_malzeme", "zarf_malzeme", "sogutucu",
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
    from cekirdek.sema import katman_adaylari
    alt, ust = None, None
    for z0, z1, katman in katmanlar:
        if not any(_spec_fisil_mi(spec, x) for x in katman_adaylari(kor, katman)):
            continue
        alt = z0 if alt is None else min(alt, z0)
        ust = z1 if ust is None else max(ust, z1)
    if alt is None:
        return (-h / 2.0, h / 2.0)       # fisil katman bulunamadi: tumunu kullan
    return (alt, ust)


def _universe_uret(spec, ad, nesneler, universeler):
    """Ad bir cubuk, plaka, demet ya da malzeme olabilir -- uygun universe'i uretir."""
    if cubuk_bul(spec, ad) is not None:
        return cubuk_universe(spec, ad, nesneler)
    if plaka_bul(spec, ad) is not None:
        return plaka_universe(spec, ad, nesneler)
    if demet_bul(spec, ad) is not None:
        return _demet_universe(spec, ad, nesneler, universeler)
    if ad == BOSLUK or malzeme_bul(spec, ad) is not None:
        return openmc.Universe(cells=[openmc.Cell(fill=_mat(nesneler, ad))])
    raise KeyError("tanımsız ad: %s (çubuk, plaka elemanı, demet ya da malzeme değil)" % ad)


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
            raise KeyError("kor haritasında tanımsız harf: '%s'" % harf)
        hedef = esleme[harf]
        if hedef not in universeler:
            universeler[hedef] = _universe_uret(spec, hedef, nesneler, universeler)
        return universeler[hedef]

    if len(harita) != ny:
        raise ValueError("kor haritası %d satır, boyut %d bekliyor"
                         % (len(harita), ny))
    lat = openmc.RectLattice()
    lat.pitch = (kor["adim"], kor["adim"])
    lat.lower_left = (-kor["adim"] * nx / 2.0, -kor["adim"] * ny / 2.0)
    lat.universes = [[coz(h) for h in satir] for satir in harita]
    dis_mat = _mat(nesneler, (kor.get("yansitici") or {}).get("malzeme"))
    lat.outer = openmc.Universe(cells=[openmc.Cell(fill=dis_mat)])
    return lat


def _katman_dolgusu(spec, kor, katman, ana_ic, nesneler, universeler):
    """Bir eksenel katmani dolduracak universe/lattice. (altigen_kafes'te
    katmana ozel anahtar konum konum cozulur: altigen_kor.konum_dolgu_adlari.)"""
    if katman.get("anahtar"):
        # altigen_kafes buraya anahtarli katman GETIRMEZ (altigen_kor konum
        # konum cozer); tek_demet / tamburlu gibi haritasiz korlarda ise bu
        # dal ULASILIR (D1 izleme maddesinde "olu" denmisti; olculdu, 29.09.2026:
        # tek_demet + katman anahtari -> bu hata). Mesaj dogrula/eksenel ile ayni.
        if kor["tur"] != "kare_kafes":
            raise ValueError(
                "'%s' eksenel katmanı: katmana özel harf eşlemesi yalnızca kare "
                "haritalı tam korda ya da altıgen haritalı tam korda kullanılabilir"
                % katman.get("ad"))
        return _kare_kafes_kur(spec, kor, nesneler, universeler, katman["anahtar"])
    dolgu = katman.get("dolgu")
    if not dolgu:
        return ana_ic
    anahtar = "__katman__%s" % dolgu
    if anahtar not in universeler:
        universeler[anahtar] = _universe_uret(spec, dolgu, nesneler, universeler)
    return universeler[anahtar]


def _ad_universe(spec, ad, nesneler, universeler):
    """Adin universe'i (bir kez kurulur, sonra paylasilir: distribcell)."""
    if not ad:
        raise KeyError("kor haritasında tanımsız harf")
    if ad not in universeler:
        universeler[ad] = _universe_uret(spec, ad, nesneler, universeler)
    return universeler[ad]


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
        if altigen_kor and _akor.kilif(demet_bul(spec, kor["demet"])):
            ic = _demet_universe(spec, kor["demet"], nesneler, universeler)
            gx, gy = _akor.prizma_kutusu(
                _akor.demet_dis_olcu(demet_bul(spec, kor["demet"])) / 2.0,
                demet_bul(spec, kor["demet"]).get("yonelim", "y"))
    elif tur == "altigen_kafes":
        return _altigen_kor_kur(spec, nesneler, universeler)
    elif tur == "tamburlu":
        # Silindirik kor + yansitici kusak + kusaga gomulu donen tamburlar.
        R_kor = float(kor.get("kor_yaricap") or 0.0)
        yans = kor.get("yansitici") or {}
        kal = float(yans.get("kalinlik") or 0.0)
        R_dis = R_kor + kal
        if R_kor <= 0 or kal <= 0:
            raise ValueError("tamburlu korda kor yarıçapı ve yansıtıcı kuşak "
                             "kalınlığı sıfırdan büyük olmalı")
        t = kor.get("tambur") or {}
        hatalar = _tambur.geometri_kontrol(t, R_kor, kal) if int(t.get("sayi") or 0) else []
        if hatalar:
            raise ValueError("tambur yerleşimi geçersiz: " + hatalar[0])

        dolgu_ad = kor.get("dolgu")
        if not dolgu_ad:
            raise ValueError("tamburlu korda kor dolgusu seçilmeli "
                             "(demet, çubuk ya da malzeme)")
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
            t_univ = _tambur_universe(t, nesneler, _mat)
            for x, y, psi in _tambur_yerlesim(t):
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
            raise ValueError("küresel düzenekte en az bir kabuk gerekir")
        yaricaplar = [k["r"] for k in kabuklar]
        for i in range(len(yaricaplar) - 1):
            if yaricaplar[i] >= yaricaplar[i + 1]:
                raise ValueError("kabuk yarıçapları artan sırada olmalı: "
                                 "r%d = %.5f ≥ r%d = %.5f"
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
        raise ValueError("bilinmeyen kor türü: %s" % tur)

    yans = kor.get("yansitici") or {}
    yans_var = yans.get("var") and tur in ("tek_demet", "kare_kafes")

    # --- altigen kor: HexagonalPrism sinirlari ---
    if altigen_kor:
        d = demet_bul(spec, kor["demet"])
        halka = d.get("halka_sayisi") or d["boyut"][0]
        yonelim = d.get("yonelim", "y")
        # Kilifli demette sinir kilifin dis yuzudur (kilifsizda pin zarfi).
        buy = (_akor.demet_dis_olcu(d) - _akor.pin_zarfi(d)) / 2.0 if _akor.kilif(d) else 0.0
        if yans_var:
            kal = yans["kalinlik"]
            ic_prizma = _altigen_sinir(halka, d["adim"], yonelim, "transmission", buy)
            dis_prizma = _altigen_sinir(halka, d["adim"], yonelim, yan_bc, buyutme=kal + buy)
            hucreler = _eksenel_hucreler(spec, kor, -ic_prizma, ic,
                                         nesneler, universeler)
            hucreler.append(openmc.Cell(
                fill=_mat(nesneler, yans.get("malzeme")),
                region=_eksenel_bolge(kor, +ic_prizma & -dis_prizma)))
            olcu = altigen.kapsayan_olcu(halka, d["adim"], yonelim) if not buy else (gx, gy)
            return openmc.Universe(cells=hucreler), (olcu[0] + 2 * kal, olcu[1] + 2 * kal)
        prizma = _altigen_sinir(halka, d["adim"], yonelim, yan_bc, buy)
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


def kilifli_demet_universe(kafes, ic_duz, kalinlik, yonelim, kilif_malzeme, dis_malzeme):
    """
    Altigen demet + kilif (duct): kilifin ici pin kafesi, kilif, disi dolgu.
    Kilif prizmasi pin kafesiyle AYNI yonelimdedir (zarf gibi; olculdu).
    """
    import math
    import openmc
    ic = openmc.model.HexagonalPrism(edge_length=ic_duz / math.sqrt(3.0),
                                     orientation=yonelim)
    dis = openmc.model.HexagonalPrism(edge_length=(ic_duz + 2.0 * kalinlik) / math.sqrt(3.0),
                                      orientation=yonelim)
    return openmc.Universe(cells=[
        openmc.Cell(fill=kafes, region=-ic, name="kilif ici"),
        openmc.Cell(fill=kilif_malzeme, region=+ic & -dis, name="kilif"),
        openmc.Cell(fill=dis_malzeme, region=+dis, name="demetler arasi"),
    ])


def altigen_kor_hucreleri(merkezler, adim, yonelim, dolgular, katmanlar, yan_bc,
                          yansitici=None):
    """
    Altigen tam korun kok hucreleri.

    merkezler : [(x, y)] demet merkezleri (tam altigen harita)
    yonelim   : kor kafesi yonelimi ('x' | 'y'; HexLattice anlaminda)
    dolgular  : konum basina, katman basina dolgu: dolgular[i][j]
    katmanlar : [(z_bolgesi | None, ad)] -- eksenel dilimler (alttan uste)
    yan_bc    : yan sinir kosulu
    yansitici : None | (malzeme, kalinlik, tam_z_bolgesi | None)
    Yansitici yoksa sinir kosulu en dis demetlerin DIS YUZLERINDEDIR.
    """
    import math
    import openmc
    sq3 = math.sqrt(3.0)
    taban = 0.0 if yonelim == "x" else 30.0
    nor = [(math.cos(math.radians(taban + 60.0 * k)),
            math.sin(math.radians(taban + 60.0 * k))) for k in range(6)]

    def anahtar(x, y):
        return (round(x / adim, 6) + 0.0, round(y / adim, 6) + 0.0)

    kume = {anahtar(x, y) for x, y in merkezler}
    duzlemler = {}

    def duzlem(kk, m, bc):
        a = (kk, m, bc)
        if a not in duzlemler:
            duzlemler[a] = openmc.Plane(a=nor[kk][0], b=nor[kk][1], c=0.0,
                                        d=m * adim / 2.0, boundary_type=bc)
        return duzlemler[a]

    bolgeler, dis_halka = [], []
    for x, y in merkezler:
        bolge, sinirda = None, False
        for k in range(6):
            nx, ny = nor[k]
            komsu = anahtar(x + adim * nx, y + adim * ny) in kume
            sinirda = sinirda or not komsu
            bc = "transmission" if (komsu or yansitici is not None) else yan_bc
            isaret = 1.0 if k < 3 else -1.0
            m = int(round(2.0 * isaret * (nx * x + ny * y + adim / 2.0) / adim))
            p = duzlem(k % 3, m, bc)
            yari = -p if isaret > 0 else +p
            bolge = yari if bolge is None else bolge & yari
        bolgeler.append(bolge)
        if sinirda:
            dis_halka.append(bolge)

    hucreler = []
    for i, (x, y) in enumerate(merkezler):
        for j, (z_bolge, ad) in enumerate(katmanlar):
            dolgu = dolgular[i][j]
            h = openmc.Cell(fill=dolgu, name=ad or "",
                            region=bolgeler[i] if z_bolge is None else bolgeler[i] & z_bolge)
            if isinstance(dolgu, (openmc.Universe, openmc.Lattice)):
                h.translation = (x, y, 0.0)
            hucreler.append(h)

    if yansitici is not None:
        malzeme, kalinlik, tam_z = yansitici
        halka = int(round(max(math.hypot(x, y) for x, y in merkezler) / adim)) + 1
        apotem = (halka - 1) * adim * sq3 / 2.0 + adim / sq3 + kalinlik
        dis = openmc.model.HexagonalPrism(edge_length=2.0 * apotem / sq3,
                                          orientation=yonelim, boundary_type=yan_bc)
        bolge = -dis
        if halka > 1:
            orta = openmc.model.HexagonalPrism(
                edge_length=2.0 * ((halka - 1) * adim * sq3 / 2.0) / sq3, orientation=yonelim)
            bolge = bolge & +orta
        for b in dis_halka:
            bolge = bolge & ~b
        if tam_z is not None:
            bolge = bolge & tam_z
        hucreler.append(openmc.Cell(fill=malzeme, region=bolge, name="yansıtıcı"))
    return hucreler


def z_dilimleri(kor):
    """
    Eksenel dilimler [(z_bolgesi | None, katman | None)] ve tam yukseklik
    bolgesi. Ic arayuzler transmission; BC yalnizca en alt ve en ust yuzeyde
    (kurucu._eksenel_hucreler ile ayni kural).
    """
    import openmc
    from cekirdek.sema import eksenel_katmanlar, kor_yuksekligi
    h = kor_yuksekligi(kor)
    if not h:
        return [(None, None)], None
    sinir = kor.get("sinir", {})
    katmanlar = eksenel_katmanlar(kor)
    sinirlar = ([-h / 2.0] + [z1 for _z0, z1, _b in katmanlar[:-1]] + [h / 2.0]
                if katmanlar else [-h / 2.0, h / 2.0])
    duz = [openmc.ZPlane(sinirlar[0], boundary_type=sinir.get("alt", "reflective"))]
    duz += [openmc.ZPlane(z) for z in sinirlar[1:-1]]
    duz.append(openmc.ZPlane(sinirlar[-1], boundary_type=sinir.get("ust", "reflective")))
    dilimler = [(+duz[i] & -duz[i + 1], (katmanlar[i][2] if katmanlar else None))
                for i in range(len(duz) - 1)]
    return dilimler, +duz[0] & -duz[-1]


def katman_adlari(dilimler):
    """z_dilimleri -> [(z_bolgesi, hucre adi)]."""
    return [(z, ((k or {}).get("ad") or "katman %d" % (i + 1)) if k else "")
            for i, (z, k) in enumerate(dilimler)]


def konum_dolgu_adlari(kor, dilimler):
    """
    Konum basina, dilim basina dolgu: ("ad", ad) ana/katmana ozel anahtarla
    cozulen harf; ("katman", katman) katmanin kendi dolgusu.
    """
    esleme = kor.get("anahtar") or {}
    sonuc = []
    for harf in (h for satir in kor.get("harita") or [] for h in satir):
        satir = []
        for _z, k in dilimler:
            if k and k.get("anahtar"):
                e = dict(esleme)
                e.update(k["anahtar"])
                satir.append(("ad", e.get(harf)))
            elif k and k.get("dolgu"):
                satir.append(("katman", k))
            else:
                satir.append(("ad", esleme.get(harf)))
        sonuc.append(satir)
    return sonuc


def _altigen_kor_kur(spec, nesneler, universeler):
    """altigen_kafes: (kok_universe, sinir_kutusu). kurucu.kor_kur buradan cagirir."""
    import openmc
    import sys
    _k = sys.modules[__name__]
    kor = spec["kor"]
    _akor.harita_kontrol(kor)
    n, P = _akor.halka_sayisi(kor), float(kor["adim"])
    yonelim = kor.get("yonelim") or "x"
    dilimler, tam_z = z_dilimleri(kor)
    dolgular = []
    for satir in konum_dolgu_adlari(kor, dilimler):
        dolgular.append([
            _k._ad_universe(spec, deger, nesneler, universeler) if tur == "ad"
            else _k._katman_dolgusu(spec, kor, deger, None, nesneler, universeler)
            for tur, deger in satir])
    yan_bc = kor.get("sinir", {}).get("yan", "reflective")
    kal = _akor.yansitici_kalinligi(kor)
    yans = None if kal is None else (
        _k._mat(nesneler, (kor.get("yansitici") or {}).get("malzeme")), kal, tam_z)
    hucreler = altigen_kor_hucreleri(_akor.kor_merkezleri(n, P, yonelim), P, yonelim, dolgular,
                                     katman_adlari(dilimler), yan_bc, yans)
    return openmc.Universe(cells=hucreler), _akor.kor_sinir_kutusu(kor)


def _duzlem(aci_derece):
    """z ekseninden gecen, verilen aciya ait yari-duzlem siniri."""
    a = math.radians(aci_derece)
    return openmc.Plane(a=-math.sin(a), b=math.cos(a), c=0.0, d=0.0)


def _kama(aci_genislik):
    """
    LOKAL +x yonunde ortalanmis, verilen genislikte aci kamasi.
    180 dereceden genis yaylarda kesisim yerine BIRLESIM gerekir.
    """
    yari = aci_genislik / 2.0
    p1, p2 = _duzlem(-yari), _duzlem(+yari)
    if aci_genislik <= 180.0:
        return +p1 & -p2
    return +p1 | -p2


def _tambur_universe(tambur, nesneler, _mat):
    """
    Tambur universe'i: emici yay LOKAL +x yonunde ortalanmistir.
    Yerlestirme sirasinda cell.rotation ile dondurulur.
    """
    R = float(tambur["yaricap"])
    r_ic = float(tambur.get("emici_ic_yaricap") or 0.0)
    aci = float(tambur.get("emici_aci") or 120.0)

    dis = openmc.ZCylinder(r=R)
    govde = _mat(nesneler, tambur.get("govde_malzeme"))
    emici_mal = _mat(nesneler, tambur.get("emici_malzeme"))

    if r_ic > 0:
        ic = openmc.ZCylinder(r=r_ic)
        emici_bolge = +ic & -dis & _kama(aci)
    else:
        emici_bolge = -dis & _kama(aci)

    return openmc.Universe(cells=[
        openmc.Cell(fill=emici_mal, region=emici_bolge),
        openmc.Cell(fill=govde, region=(-dis) & ~emici_bolge),
        # tamburun disi: yerlestirildigi hucre zaten -delik ile sinirlidir,
        # ama universe'un her yeri tanimli olmalidir
        openmc.Cell(fill=govde, region=+dis),
    ])


def _tambur_yerlesim(tambur):
    """
    Tamburlarin (x, y, psi) yerlesimini dondurur.

    psi = fi + 180 + donme   ->  donme=0'da emici kore bakar.
    """
    n = int(tambur.get("sayi") or 0)
    R_m = float(tambur.get("merkez_yaricap") or 0.0)
    donme = float(tambur.get("donme") or 0.0)
    baslangic = float(tambur.get("baslangic_acisi") or 0.0)
    liste = []
    for i in range(n):
        fi = baslangic + 360.0 * i / n
        liste.append((R_m * math.cos(math.radians(fi)),
                      R_m * math.sin(math.radians(fi)),
                      fi + 180.0 + donme))
    return liste
