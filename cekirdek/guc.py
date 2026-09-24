# -*- coding: utf-8 -*-
"""
================================================================================
 guc.py  --  Cubuk bazli guc dagilimi ve tepe faktorleri
================================================================================

 "Bu kor kritik mi" sorusunun yanina "sicak nokta nerede" sorusunu ekler.
 Bir reaktor tasarimi iki tepe faktoru olmadan tamamlanmaz:

   F_dH  = maks cubuk gucu / ortalama cubuk gucu        (radyal)
           Sicak kanalda sogutucu sicaklik artisini, dolayisiyla DNB marjini
           sinirlar.

   F_q   = maks yerel guc yogunlugu / ortalama          (radyal x eksenel)
           Yakit merkez sicakligini ve lineer guc sinirini (~400-500 W/cm)
           sinirlar. 3B model gerektirir; 2B modelde TANIMSIZDIR.

 YONTEM
   OpenMC'nin DistribcellFilter'i kafeste tekrarlanan bir hucrenin HER ORNEGINI
   ayri sayar. Eksenel cozunurluk icin buna 1x1xN'lik bir MeshFilter eklenir.
   (pin(subdivisions=...) radyal boler, eksenel degil -- o yol kullanilamaz.)

 DOGRULANMIS VERI BICIMI (OpenMC 0.16.0, olcum)
   tally.get_pandas_dataframe(paths=True) su sutunlari verir:
     ('level N','lat','id'/'x'/'y')   kafes kimligi ve konumu
     ('distribcell','','')            ornek indeksi
     ('mesh M','x'/'y'/'z')           eksenel bin (z, 1 tabanli)
     ('mean',''), ('std. dev.','')
   Kare kafeste (x,y) dogrudan izgara konumudur.
   ALTIGEN kafeste (x,y) aslinda (x, alfa) eksenel koordinatidir; (halka,sira)
   duzenine cevirmek icin HexLattice.get_universe_index() kullanilir.

 !!! BELIRSIZLIK -- OKUMADAN GECMEYIN !!!

   OpenMC'nin RAPORLADIGI tally belirsizligi ozdeger hesaplarinda OLDUGUNDAN
   KUCUKTUR. Sebep: ardisik cevrimlerin fisyon kaynaklari birbirinden bagimsiz
   degildir (cevrimler arasi korelasyon). Cevrim-ici sacilmadan hesaplanan
   sigma bu korelasyonu goremez.

   BU MODELDE OLCULDU (pwr_3b, 4000 parcacik, 3 bagimsiz tohum):
     raporlanan sigma (bin basina)     : 0.003 - 0.008
     tohumlar arasi gercek sacilma     : 0.07  - 0.17
     -> gercek belirsizlik yaklasik 20 KAT buyuk

   Bu yuzden F_dH ve F_q icin burada hesaplanan sapmalar IYIMSERDIR.
   (Ilk surumde "muhafazakardir" yaziyordu; bu YANLISTI ve olcumle duzeltildi:
   oran korelasyonunu ihmal etmek muhafazakar yonde etki eder, ama alttaki bin
   sigmalarinin kendisi cok daha buyuk bir carpanla kucuk raporlanir; net etki
   iyimser kalir.)

   GERCEK BELIRSIZLIK NASIL OLCULUR
     coklu_tohum() ile N bagimsiz tohumda kosup sonuclarin sacilmasina bakin.
     Tek kosunun sigmasi bir ALT SINIRDIR, gercek hata degildir.
================================================================================
"""

import math


# ============================================================================
# 1. HEDEF HUCREYI BULMA
# ============================================================================

def bolge_hucresi(universe, cubuk, nesneler):
    """
    Bir cubuk universe'inin bolgelerine karsilik gelen hucreleri dondurur.

    openmc.model.pin() hucreleri BOLGE SIRASINDA olusturur
    (cells = [Cell(fill=f, region=r) for r, f in zip(regions, items)]),
    bu yuzden id'ye gore siralamak bolge sirasini verir. Yine de dolgu
    malzemeleri beklenenle karsilastirilir; uyusmazsa sessizce yanlis hucreyi
    secmek yerine acik hata verilir.

    DONER bolge sirasinda openmc.Cell listesi
    """
    hucreler = sorted(universe.cells.values(), key=lambda c: c.id)
    bolgeler = cubuk["bolgeler"]
    if len(hucreler) != len(bolgeler):
        raise ValueError(
            "cubuk '%s': %d bolge bekleniyor ama universe'de %d hucre var. "
            "Guc dagilimi icin hucre-bolge eslesmesi guvenilir degil."
            % (cubuk["ad"], len(bolgeler), len(hucreler)))
    for i, (h, b) in enumerate(zip(hucreler, bolgeler)):
        beklenen = nesneler.get(b.get("malzeme"))
        if beklenen is not None and h.fill is not beklenen:
            raise ValueError(
                "cubuk '%s' %d. bolge: beklenen malzeme '%s' ama hucrede '%s' var. "
                "Hucre-bolge eslesmesi bozulmus."
                % (cubuk["ad"], i + 1, b.get("malzeme"),
                   getattr(h.fill, "name", h.fill)))
    return hucreler


# ============================================================================
# 2. STATEPOINT'TEN DAGILIMI OKUMA
# ============================================================================

def _kafes_seviyeleri(df):
    """DataFrame sutunlarindan kafes seviyelerini bulur (distan ice sirali)."""
    seviyeler = []
    for sut in df.columns:
        if isinstance(sut, tuple) and len(sut) == 3 and sut[1] == "lat" and sut[2] == "id":
            seviyeler.append(sut[0])          # "level 2" gibi
    return sorted(set(seviyeler), key=lambda s: int(s.split()[-1]))


def _eksenel_sutun(df):
    """Mesh filtresinin z sutununu bulur; yoksa None."""
    for sut in df.columns:
        if isinstance(sut, tuple) and len(sut) == 3 and sut[0].startswith("mesh") \
                and sut[1] == "z":
            return sut
    return None


def dagilim_oku(sp, tally_adi="guc_dagilimi"):
    """
    Statepoint'ten guc dagilimini okur.

    DONER sozluk:
      kafes_turu     "kare" | "altigen"
      kafes          openmc.Lattice (en ic kafes)
      eksenel_dilim  int (1 = 2B)
      konumlar       {anahtar: {"eksenel": [(ort,sapma), ...], "toplam": (ort,sapma)}}
                     anahtar kare icin (x, y); altigen icin (halka, sira)
      notlar         list of str
    ya da tally bulunamazsa None.
    """
    try:
        tal = sp.get_tally(name=tally_adi)
    except Exception:
        return None
    if tal is None:
        return None

    # distribcell yollari summary'den gelen geometriye ve determine_paths()'e baglidir
    if sp.summary is None:
        raise RuntimeError(
            "summary.h5 bulunamadi; distribcell yollari okunamaz. "
            "Kosu dizininde statepoint ile summary yan yana olmalidir.")
    geometri = sp.summary.geometry
    geometri.determine_paths()

    df = tal.get_pandas_dataframe(paths=True)
    notlar = []

    seviyeler = _kafes_seviyeleri(df)
    if not seviyeler:
        raise RuntimeError(
            "Distribcell yolunda kafes seviyesi bulunamadi. Hedef cubuk bir "
            "kafeste tekrarlanmiyor olabilir; guc dagilimi yalnizca kafes "
            "icindeki cubuklar icin anlamlidir.")
    if len(seviyeler) > 1:
        notlar.append(
            "Ic ice %d kafes seviyesi var; harita EN IC kafese gore ciziliyor, "
            "tepe faktorleri ise tum cubuklar uzerinden hesaplaniyor."
            % len(seviyeler))
    ic_seviye = seviyeler[-1]

    kafes_id = int(df[(ic_seviye, "lat", "id")].iloc[0])
    kafesler = geometri.get_all_lattices()
    kafes = kafesler.get(kafes_id)
    if kafes is None:
        raise RuntimeError("kafes id=%d geometride bulunamadi" % kafes_id)

    import openmc
    altigen_mi = isinstance(kafes, openmc.HexLattice)
    kafes_turu = "altigen" if altigen_mi else "kare"

    z_sut = _eksenel_sutun(df)
    if z_sut is not None:
        eksenel_dilim = int(df[z_sut].max())
    else:
        eksenel_dilim = 1

    xs = df[(ic_seviye, "lat", "x")].astype(int)
    ys = df[(ic_seviye, "lat", "y")].astype(int)
    ort = df[("mean", "", "")] if ("mean", "", "") in df.columns else df["mean"]
    sap = df[("std. dev.", "", "")] if ("std. dev.", "", "") in df.columns else df["std. dev."]

    konumlar = {}
    for i in range(len(df)):
        ham = (int(xs.iloc[i]), int(ys.iloc[i]))
        if altigen_mi:
            # (x, alfa) -> (halka, sira).  OpenMC'nin kendi cevirimi kullanilir;
            # elle turetmek hataya cok acik.
            anahtar = tuple(kafes.get_universe_index(ham))
        else:
            anahtar = ham
        dilim = int(df[z_sut].iloc[i]) - 1 if z_sut is not None else 0
        kayit = konumlar.setdefault(
            anahtar, {"eksenel": [None] * eksenel_dilim})
        kayit["eksenel"][dilim] = (float(ort.iloc[i]), float(sap.iloc[i]))

    # eksik dilim var mi (olmamali) ve toplamlari hesapla
    for anahtar, kayit in konumlar.items():
        if any(d is None for d in kayit["eksenel"]):
            raise RuntimeError(
                "konum %s icin bazi eksenel dilimler eksik; veri bicimi "
                "beklenenden farkli." % (anahtar,))
        toplam = sum(d[0] for d in kayit["eksenel"])
        sapma = math.sqrt(sum(d[1] ** 2 for d in kayit["eksenel"]))
        kayit["toplam"] = (toplam, sapma)

    return {
        "kafes_turu": kafes_turu,
        "kafes": kafes,
        "kafes_id": kafes_id,
        "eksenel_dilim": eksenel_dilim,
        "konumlar": konumlar,
        "notlar": notlar,
    }


# ============================================================================
# 3. TEPE FAKTORLERI
# ============================================================================

def tepe_faktorleri(dagilim):
    """
    F_dH ve F_q hesaplar.

    F_dH = maks(cubuk toplam gucu) / ortalama(cubuk toplam gucu)
    F_q  = maks(yerel dilim gucu)  / ortalama(yerel dilim gucu)
           yalnizca eksenel_dilim > 1 ise tanimli.

    Bagil guc = her degerin ortalamaya bolunmus hali (ortalama tam olarak 1.000).
    """
    konumlar = dagilim["konumlar"]
    if not konumlar:
        return None
    n = len(konumlar)

    toplamlar = {a: k["toplam"] for a, k in konumlar.items()}
    ort_cubuk = sum(v[0] for v in toplamlar.values()) / n
    if ort_cubuk <= 0:
        return None

    sicak_cubuk = max(toplamlar.items(), key=lambda kv: kv[1][0])
    f_dh = sicak_cubuk[1][0] / ort_cubuk
    # NOT: bu sapma IYIMSERDIR (modul basligindaki belirsizlik notuna bakin).
    # Gercek belirsizlik icin coklu_tohum() kullanin.
    f_dh_sapma = f_dh * (sicak_cubuk[1][1] / sicak_cubuk[1][0]) if sicak_cubuk[1][0] else 0.0

    bagil = {a: (v[0] / ort_cubuk, v[1] / ort_cubuk) for a, v in toplamlar.items()}

    # --- MAKSIMUMUN ISTATISTIKSEL YANLILIGI ---
    # F_dH bir MAKSIMUMDUR. N tane gurultulu degerin maksimumu YUKARI yanlidir:
    # gurultu buyudukce maks buyur, gercek tepe degismese bile. Olcut olarak
    # cubuk basina istatistik sapmayi dagilimin gercek sacilmasiyla kiyaslariz.
    # (Olculdu: 3000 parcacikta sapma 0.043, sacilma 0.063 -> F_dH sisirilmis.)
    degerler = [v[0] for v in bagil.values()]
    ort_bagil = sum(degerler) / n
    sacilma = math.sqrt(sum((d - ort_bagil) ** 2 for d in degerler) / n) if n > 1 else 0.0
    ist_sapma = sum(v[1] for v in bagil.values()) / n

    sonuc = {
        "cubuk_sayisi": n,
        "eksenel_dilim": dagilim["eksenel_dilim"],
        "ortalama_cubuk": ort_cubuk,
        "F_dH": f_dh,
        "F_dH_sapma": f_dh_sapma,
        "sicak_cubuk": sicak_cubuk[0],
        "sacilma": sacilma,
        "istatistik_sapma": ist_sapma,
        "yanlilik_orani": (ist_sapma / sacilma) if sacilma > 0 else None,
        "bagil": bagil,
        "F_q": None, "F_q_sapma": None, "sicak_dilim": None,
        "bagil_eksenel": None, "eksenel_profil": None,
    }

    if dagilim["eksenel_dilim"] > 1:
        hepsi = []
        for a, k in konumlar.items():
            for i, d in enumerate(k["eksenel"]):
                hepsi.append((a, i, d[0], d[1]))
        ort_yerel = sum(h[2] for h in hepsi) / len(hepsi)
        sicak = max(hepsi, key=lambda h: h[2])
        f_q = sicak[2] / ort_yerel if ort_yerel > 0 else None
        sonuc["F_q"] = f_q
        sonuc["F_q_sapma"] = (f_q * sicak[3] / sicak[2]) if (f_q and sicak[2]) else None
        sonuc["sicak_dilim"] = (sicak[0], sicak[1])
        sonuc["ortalama_yerel"] = ort_yerel
        sonuc["bagil_eksenel"] = {
            a: [(d[0] / ort_yerel, d[1] / ort_yerel) for d in k["eksenel"]]
            for a, k in konumlar.items()}
        # eksenel guc profili (tum cubuklar toplanarak)
        profil = []
        for i in range(dagilim["eksenel_dilim"]):
            t = sum(k["eksenel"][i][0] for k in konumlar.values())
            s = math.sqrt(sum(k["eksenel"][i][1] ** 2 for k in konumlar.values()))
            profil.append((t, s))
        ort_profil = sum(p[0] for p in profil) / len(profil)
        sonuc["eksenel_profil"] = [(p[0] / ort_profil, p[1] / ort_profil)
                                   for p in profil] if ort_profil > 0 else None
    return sonuc


# ============================================================================
# 4. MUTLAK GUC
# ============================================================================

def mutlak_guc(faktorler, toplam_guc, yukseklik=None):
    """
    Bagil dagilimi mutlak guce cevirir.

    toplam_guc : modelin temsil ettigi bolgenin toplam gucu [W]
    yukseklik  : aktif yukseklik [cm]; verilirse lineer guc [W/cm] hesaplanir

    !!! DIKKAT !!!
      toplam_guc MODELIN KAPSADIGI bolgenin gucudur. Sonsuz kafes (yansitici
      sinirli tek demet) hesabinda bu "bir demetin gucu"dur, tum korun degil.
      Yanlis deger girilirse tum mutlak sayilar ayni oranda yanlis cikar.

      ORNEK: 3400 MWth / 193 demet = 17.6 MW. Tek demetlik bir modelde
      toplam_guc = 17.6e6 W girilir (3400e6 DEGIL, 17.6e6/193 de DEGIL).
      Dogru girdiyle 17x17 / 366 cm icin ortalama lineer guc ~182 W/cm cikar --
      gercek PWR degeri. Sonuc bu mertebede degilse girdi yanlistir.
    """
    if not faktorler or not toplam_guc or toplam_guc <= 0:
        return None
    n = faktorler["cubuk_sayisi"]
    cubuk_ort = toplam_guc / n
    sonuc = {
        "toplam_guc": toplam_guc,
        "cubuk_ortalama_W": cubuk_ort,
        "cubuk_maks_W": cubuk_ort * faktorler["F_dH"],
    }
    if yukseklik and yukseklik > 0:
        sonuc["lineer_ortalama_W_cm"] = cubuk_ort / yukseklik
        # Maks lineer guc yerel tepeye baglidir: F_q varsa onu, yoksa F_dH'yi kullan
        tepe = faktorler["F_q"] or faktorler["F_dH"]
        sonuc["lineer_maks_W_cm"] = (cubuk_ort / yukseklik) * tepe
        sonuc["lineer_tepe_kaynagi"] = "F_q" if faktorler["F_q"] else "F_dH (2B -- eksenel tepe dahil degil)"
    return sonuc


# ============================================================================
# 5. YORUM
# ============================================================================

def yorumla(faktorler, mutlak=None):
    """Ogrenciye yonelik kisa yorum satirlari."""
    if not faktorler:
        return ["Guc dagilimi hesaplanamadi."]
    satirlar = []
    f = faktorler["F_dH"]
    satirlar.append(
        "F_dH = %.4f -- en sicak cubuk ortalamanin %.1f%% ustunde guc uretiyor."
        % (f, (f - 1) * 100))
    if f < 1.02:
        satirlar.append("  Dagilim neredeyse duz. Yansitici sinirli tek demet "
                        "hesaplarinda beklenen budur; gercek bir korda kenar "
                        "etkileri ve yakit yuklemesi tepeyi buyutur.")
    elif f > 1.65:
        satirlar.append("  YUKSEK. Tipik PWR tasarim siniri F_dH ~ 1.65 "
                        "civarindadir; yakit yuklemesi duzeltilmeli.")
    # --- maksimumun yukari yanliligi ---
    oran = faktorler.get("yanlilik_orani")
    if oran is not None and oran > 0.3:
        satirlar.append(
            "  DIKKAT: cubuk basina istatistik sapma (%.4f) dagilimin gercek "
            "sacilmasinin (%.4f) %.0f%%'i kadar. Bir MAKSIMUM hesaplandigi icin "
            "F_dH bu durumda YUKARI YANLIDIR -- gercek tepe daha dusuktur. "
            "Cevrim basina parcacik sayisini artirin."
            % (faktorler["istatistik_sapma"], faktorler["sacilma"], oran * 100))

    if faktorler["F_q"]:
        satirlar.append(
            "F_q = %.4f -- yerel guc yogunlugu tepesi. Eksenel sekil dahil."
            % faktorler["F_q"])
        if faktorler["eksenel_dilim"] < 10:
            satirlar.append(
                "  DIKKAT: yalnizca %d eksenel dilim var. Kaba dilimler tepeyi "
                "ortalar ve F_q'yu KUCUK gosterir (saf kosinus profilinde ince "
                "dilim limiti pi/2 = 1.571'dir). En az 10-20 dilim kullanin."
                % faktorler["eksenel_dilim"])
        if faktorler["F_q"] > 2.6:
            satirlar.append("  YUKSEK. Tipik PWR siniri F_q ~ 2.3-2.6.")
    else:
        satirlar.append("F_q TANIMSIZ -- model 2B (eksenel yukseklik yok). "
                        "Eksenel tepe olmadan yerel guc yogunlugu hesaplanamaz; "
                        "kor yuksekligi tanimlayin.")
    if mutlak:
        satirlar.append("Cubuk basina ortalama %.1f W, en sicak cubuk %.1f W."
                        % (mutlak["cubuk_ortalama_W"], mutlak["cubuk_maks_W"]))
        if "lineer_maks_W_cm" in mutlak:
            lm = mutlak["lineer_maks_W_cm"]
            satirlar.append("Maks lineer guc %.1f W/cm (kaynak: %s)."
                            % (lm, mutlak["lineer_tepe_kaynagi"]))
            if lm > 500:
                satirlar.append("  SINIR USTU. Tipik PWR lineer guc siniri "
                                "~400-500 W/cm.")
    satirlar.append(
        "UYARI: buradaki sapmalar IYIMSERDIR. Ozdeger hesaplarinda ardisik "
        "cevrimler korelasyonlu oldugu icin OpenMC'nin raporladigi tally "
        "belirsizligi olcumle ~20 kat kucuk cikti. Gercek belirsizlik icin "
        "birkac BAGIMSIZ TOHUMLA kosup sacilmaya bakin (coklu_tohum).")
    return satirlar


def coklu_tohum(spec, kok_dizin, tohumlar=(1, 2, 3), is_parcacigi=None,
                geri_cagir=None):
    """
    Ayni modeli birkac BAGIMSIZ tohumla kosar ve tepe faktorlerinin GERCEK
    sacilmasini olcer.

    Tek bir kosunun raporladigi sigma, cevrimler arasi korelasyon yuzunden
    gercek belirsizligin altindadir (bu modulun basligindaki olcume bakin).
    Bagimsiz tohumlar arasindaki sacilma ise dogrudan gercek belirsizliktir.

    DONER {"F_dH": [...], "F_q": [...], "ozet": {...}}
    """
    import os
    import statistics as st
    from cekirdek import kosucu

    f_dh, f_q, hatalar = [], [], []
    for i, t in enumerate(tohumlar):
        alt = dict(spec)
        alt["ayarlar"] = dict(spec["ayarlar"], tohum=int(t))
        dizin = os.path.join(kok_dizin, "tohum_%d" % t)
        try:
            kosu = kosucu.calistir(alt, dizin, is_parcacigi=is_parcacigi)
            if not kosu["basarili"]:
                hatalar.append("tohum %d: kosu basarisiz" % t)
                continue
            s = kosucu.sonuc_oku(kosu["statepoint"])
            f = (s.get("guc") or {}).get("faktorler")
            if not f:
                hatalar.append("tohum %d: guc dagilimi okunamadi" % t)
                continue
            f_dh.append(f["F_dH"])
            if f["F_q"]:
                f_q.append(f["F_q"])
        except Exception as e:
            hatalar.append("tohum %d: %s" % (t, e))
        if geri_cagir:
            geri_cagir(i, len(tohumlar), f_dh[-1] if f_dh else None)

    ozet = {"hatalar": hatalar, "tohum_sayisi": len(f_dh)}
    if len(f_dh) >= 2:
        ozet["F_dH_ort"] = st.mean(f_dh)
        ozet["F_dH_sacilma"] = st.stdev(f_dh)
    if len(f_q) >= 2:
        ozet["F_q_ort"] = st.mean(f_q)
        ozet["F_q_sacilma"] = st.stdev(f_q)
    return {"F_dH": f_dh, "F_q": f_q, "ozet": ozet}


def ozet_metni(faktorler, mutlak=None):
    """Tek satirlik ozet (terminal ve durum cubugu icin)."""
    if not faktorler:
        return "guc dagilimi yok"
    p = ["F_dH = %.4f +/- %.4f" % (faktorler["F_dH"], faktorler["F_dH_sapma"])]
    if faktorler["F_q"]:
        p.append("F_q = %.4f +/- %.4f" % (faktorler["F_q"], faktorler["F_q_sapma"]))
    p.append("sicak cubuk %s" % (faktorler["sicak_cubuk"],))
    return "  |  ".join(p)
