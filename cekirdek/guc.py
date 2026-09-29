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
   Tam korda (kafes icinde kafes) HER kafes duzeyi icin ayri bir 'level N'
   grubu gelir (olculdu, 2x2 kare kor: level 2 = kor kafesi, level 4 = demet
   kafesi). Anahtar tum duzeylerin konumundan kurulur (bkz. bolum 2).

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

import functools
import math

from cekirdek import guc_kor as _guc_kor
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


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
            "'%s' çubuğu: %d bölge bekleniyor ama geometride %d hücre var. "
            "Güç dağılımı için hücre-bölge eşleşmesi güvenilir değil."
            % (cubuk["ad"], len(bolgeler), len(hucreler)))
    for i, (h, b) in enumerate(zip(hucreler, bolgeler)):
        beklenen = nesneler.get(b.get("malzeme"))
        if beklenen is not None and h.fill is not beklenen:
            raise ValueError(
                "'%s' çubuğu, %d. bölge: beklenen malzeme '%s' ama hücrede '%s' var. "
                "Hücre-bölge eşleşmesi bozulmuş."
                % (cubuk["ad"], i + 1, b.get("malzeme"),
                   getattr(h.fill, "name", h.fill)))
    return hucreler


# ============================================================================
# 2. STATEPOINT'TEN DAGILIMI OKUMA
# ============================================================================
#
# ANAHTAR = TAM KAFES YOLU (duzeltme, 28.09.2026 -- olculdu)
#   Eski surum yalnizca EN ICTEKI kafesin (x, y) konumunu anahtar yapiyordu.
#   Tam korda (kafes icinde kafes) farkli demetlerin ayni konumdaki cubuklari
#   AYNI anahtara yaziliyor, harita SON demetin degerini gosteriyordu:
#   2x2 kare korda 96 cubuk yerine 24 anahtar, toplamin %80'i kayip; F_dH
#   yanlis demetten ve yanlis ortalamadan okunuyordu (testler/test_guc_kor.py).
#
#   Simdi anahtar her kafes duzeyindeki konumun demetidir (distan ice):
#     tek duzey (tek demet) : (x, y)                     -- eskisiyle AYNI
#     iki duzey (tam kor)   : ((demet_x, demet_y), (x, y))
#   Altigen duzeyde konum HER DUZEYDE HexLattice.get_universe_index ile
#   (halka, sira)'ya cevrilir.
#
#   Anahtar kafes KIMLIGINI ve ara hucreleri icermez: eksenel katmanlarda
#   ayni cubuk konumu her katmanda ayri bir distribcell ornegidir (katman
#   hucresi ya da katmana ozel kafes farkli), ama fiziksel olarak AYNI
#   cubuk sutunudur. Bu ornekler dilim dilim TOPLANIR. (Eski surum bunlari
#   uzerine yaziyordu: ust katmanin o dilimde SIFIR olan degeri alt katmanin
#   degerini siliyordu.)

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


def _kafes_turu(kafes):
    import openmc
    if isinstance(kafes, (openmc.HexLattice, _guc_kor.OtelemeDuzeyi)):
        return "altigen"
    return "kare"


def _duzey_konumu(kafes, x, y):
    """Bir kafes duzeyindeki ham DataFrame konumunu haritanin konumuna cevirir.
    Kare: (x, y) aynen (x soldan, y alttan). Altigen: ham (x, alfa) --
    OpenMC'nin kendi ceviri islevi kullanilir; elle turetmek hataya cok acik."""
    if _kafes_turu(kafes) == "altigen":
        return tuple(int(i) for i in kafes.get_universe_index((x, y)))[:2]
    return (x, y)


def _satir_anahtarlari(df, seviyeler, kafesler, kok_demet=None):
    """
    Her satirin konum anahtari ve her duzeyin temsilci kafesi.
    kok_demet: {kok hucre kimligi: demet anahtari} (altigen_kafes; bkz.
    guc_kor) -- verilirse anahtarin EN DIS parcasi budur.
    DONER (anahtarlar listesi, [duzey kafesi, ...])
    """
    sutunlar = [[df[(s, "lat", e)].astype(int).tolist() for e in ("id", "x", "y")]
                for s in seviyeler]
    temsilci = []
    for (ids, _xs, _ys) in sutunlar:
        kafes = kafesler.get(ids[0])
        if kafes is None:
            raise RuntimeError(_("kafes (id = %d) geometride bulunamadı") % ids[0])
        temsilci.append(kafes)

    onbellek = {}

    def cevir(lid, x, y):
        k = (lid, x, y)
        if k not in onbellek:
            kafes = kafesler.get(lid)
            if kafes is None:
                raise RuntimeError(_("kafes (id = %d) geometride bulunamadı") % lid)
            onbellek[k] = _duzey_konumu(kafes, x, y)
        return onbellek[k]

    kok = (df[_guc_kor.KOK_HUCRE_SUTUNU].astype(int).tolist()
           if kok_demet is not None else None)
    tek = len(seviyeler) == 1 and kok is None
    anahtarlar = []
    for i in range(len(df)):
        parca = tuple(cevir(ids[i], xs[i], ys[i]) for ids, xs, ys in sutunlar)
        if kok is not None:
            parca = (kok_demet[kok[i]],) + parca
        anahtarlar.append(parca[0] if tek else parca)
    return anahtarlar, temsilci


def _konumlari_topla(anahtarlar, dilimler, ortalar, sapmalar, eksenel_dilim):
    """
    Satirlari konum x dilim bin'lerine yerlestirir. Ayni bin'e dusen birden
    cok ornek (eksenel katmanlar) TOPLANIR, sapmalari karesel birlesir.
    Tek ornekli bin'de deger ham okunan degerin kendisidir (bitwise).
    DONER (konumlar, birlesen_bin_sayisi)
    """
    konumlar = {}
    birlesen = 0
    for anahtar, dilim, m, s in zip(anahtarlar, dilimler, ortalar, sapmalar):
        kayit = konumlar.setdefault(anahtar, {"eksenel": [None] * eksenel_dilim})
        onceki = kayit["eksenel"][dilim]
        if onceki is None:
            kayit["eksenel"][dilim] = (float(m), float(s))
        else:
            birlesen += 1
            kayit["eksenel"][dilim] = (onceki[0] + float(m),
                                       math.sqrt(onceki[1] ** 2 + float(s) ** 2))
    return konumlar, birlesen


def _tally_bul(sp, tally_adi):
    """Tally'yi dondurur; statepoint'te yoksa None (guc dagilimi istenmemis)."""
    try:
        return sp.get_tally(name=tally_adi)
    except LookupError:
        # OpenMC bulunamayan tally icin LookupError verir: guc dagilimi bu
        # kosuda istenmemis demektir, hata degil. Diger istisnalar (bozuk
        # dosya vb.) yukari cikar; kosucu.sonuc_oku onlari "guc_hata" yapar.
        _log.debug("'%s' tally'si statepoint'te yok", tally_adi)
        return None


def dagilim_oku(sp, tally_adi="guc_dagilimi"):
    """
    Statepoint'ten guc dagilimini okur.

    DONER sozluk (ya da tally yoksa None):
      kafes_turu     "kare" | "altigen"            (EN IC kafesin turu)
      kafes          openmc.Lattice                 (en ic kafes)
      kafes_id       int
      eksenel_dilim  int (1 = 2B)
      konumlar       {anahtar: {"eksenel": [(ort, sapma), ...], "toplam": (ort, sapma)}}
                     tek demet : anahtar (x, y) kare / (halka, sira) altigen
                     tam kor   : anahtar ((demet konumu), (cubuk konumu))
      notlar         list of str
      --- 28.09.2026'da eklendi (tam kor) ---
      duzey_sayisi   int: kafes duzeyi sayisi (1 = tek demet, 2 = tam kor)
      tam_kor        bool: duzey_sayisi >= 2
      kafesler       [openmc.Lattice, ...] duzey basina temsilci kafes, DISTAN ICE
      kafes_turleri  ["kare"|"altigen", ...] ayni sirada
      kor_kafes      en dis kafes (tam korda); tek demette None
      kor_kafes_turu en dis kafesin turu (tam korda); tek demette None
      birlesen_bin   int: ayni konum x dilim bin'inde toplanan ek ornek sayisi
      --- 29.09.2026 (D1-A, altigen_kafes) ---
      kor_duzeyi     "oteleme" (altigen_kafes: demet konumu = kok hucre
                     otelemesi; kafesler[0] bir guc_kor.OtelemeDuzeyi),
                     "kafes" (kor kafesi) ya da None (tek demet)
    """
    tal = _tally_bul(sp, tally_adi)
    if tal is None:
        return None

    # distribcell yollari summary'den gelen geometriye ve determine_paths()'e baglidir
    if sp.summary is None:
        raise RuntimeError(
            "summary.h5 bulunamadı; güç dağılımının hücre konumları okunamaz. "
            "Koşu dizininde statepoint ile summary.h5 yan yana olmalıdır.")
    geometri = sp.summary.geometry
    geometri.determine_paths()

    df = tal.get_pandas_dataframe(paths=True)
    notlar = []

    seviyeler = _kafes_seviyeleri(df)
    if not seviyeler:
        raise RuntimeError(
            "Güç dağılımı sonucunda demet (kafes) düzeyi bulunamadı. Hedef "
            "çubuk bir demette tekrarlanmıyor olabilir; güç dağılımı yalnızca "
            "demet içindeki çubuklar için anlamlıdır.")

    duzen = _guc_kor.oteleme_duzeni(df, geometri)
    kok_demet, oteleme = duzen if duzen else (None, None)
    anahtarlar, kafesler = _satir_anahtarlari(df, seviyeler, geometri.get_all_lattices(),
                                              kok_demet)
    if oteleme is not None:
        kafesler = [oteleme] + kafesler
    kafes = kafesler[-1]
    kafes_turleri = [_kafes_turu(k) for k in kafesler]
    kafes_turu = kafes_turleri[-1]
    tam_kor = len(kafesler) > 1

    z_sut = _eksenel_sutun(df)
    eksenel_dilim = int(df[z_sut].max()) if z_sut is not None else 1
    dilimler = ((df[z_sut].astype(int) - 1).tolist() if z_sut is not None
                else [0] * len(df))
    ort = df[("mean", "", "")] if ("mean", "", "") in df.columns else df["mean"]
    sap = df[("std. dev.", "", "")] if ("std. dev.", "", "") in df.columns else df["std. dev."]

    konumlar, birlesen = _konumlari_topla(anahtarlar, dilimler, ort.tolist(),
                                         sap.tolist(), eksenel_dilim)

    # eksik dilim var mi (olmamali) ve toplamlari hesapla
    for anahtar, kayit in konumlar.items():
        if any(d is None for d in kayit["eksenel"]):
            raise RuntimeError(
                "%s konumunda bazı eksenel dilimler eksik; veri biçimi "
                "beklenenden farklı." % konum_metni(anahtar, kafes_turu, kafes_turleri))
        toplam = sum(d[0] for d in kayit["eksenel"])
        sapma = math.sqrt(sum(d[1] ** 2 for d in kayit["eksenel"]))
        kayit["toplam"] = (toplam, sapma)

    if tam_kor:
        notlar.append(
            _("Tam kor: %d kafes düzeyi. Her çubuk kordaki tam konumuyla "
              "(demet konumu + demet içi konum) ayrı sayılır; bağıl güç tüm "
              "kordaki yakıt çubuklarının ortalamasına göredir.") % len(kafesler))
    if birlesen:
        notlar.append(
            _("%d bin'de aynı çubuk konumu birden çok eksenel katmanda "
              "bulundu; katman örnekleri dilim dilim toplandı.") % birlesen)

    return {
        "kafes_turu": kafes_turu,
        "kafes": kafes,
        "kafes_id": kafes.id,
        "eksenel_dilim": eksenel_dilim,
        "konumlar": konumlar,
        "notlar": notlar,
        "duzey_sayisi": len(kafesler),
        "tam_kor": tam_kor,
        "kor_duzeyi": "oteleme" if oteleme is not None else ("kafes" if tam_kor else None),
        "kafesler": kafesler,
        "kafes_turleri": kafes_turleri,
        "kor_kafes": kafesler[0] if tam_kor else None,
        "kor_kafes_turu": kafes_turleri[0] if tam_kor else None,
        "birlesen_bin": birlesen,
    }


# ============================================================================
# 2b. KONUM -> FIZIKSEL MERKEZ (cizim ve nokta-hucre olcumu ayni kaynagi kullanir)
# ============================================================================

@functools.lru_cache(maxsize=32)
def _altigen_konumlar(halka, yonelim):
    from cekirdek import altigen
    return altigen.konumlar(halka, yonelim)


def eleman_merkezi(kafes, konum):
    """
    Kafes elemaninin merkezi, kafesin kendi koordinatinda [cm].
    Kare: lower_left + (i + 1/2) * adim. Altigen: center + adim * konum
    (konum cekirdek/altigen.konumlar'dan; OpenMC ile nokta-hucre olcumuyle
    dogrulandi, testler/test_guc_kor.py).
    """
    if isinstance(kafes, _guc_kor.OtelemeDuzeyi):
        return kafes.merkezler[tuple(konum)]      # kafessiz: kok hucre otelemesi
    if _kafes_turu(kafes) == "altigen":
        kx, ky = _altigen_konumlar(int(kafes.num_rings), kafes.orientation)[tuple(konum)]
        cx, cy = tuple(kafes.center)[:2]
        adim = kafes.pitch[0]
        return (cx + adim * kx, cy + adim * ky)
    llx, lly = tuple(kafes.lower_left)[:2]
    px, py = tuple(kafes.pitch)[:2]
    return (llx + (konum[0] + 0.5) * px, lly + (konum[1] + 0.5) * py)


def _duzeyler(dagilim, anahtar):
    """Anahtari duzey konumlari listesine acar (tek demette [anahtar])."""
    return list(anahtar) if dagilim.get("tam_kor") else [anahtar]


def cubuk_merkezi(dagilim, anahtar):
    """
    Cubugun modeldeki (x, y) merkezi [cm]: duzey merkezlerinin toplami.
    OpenMC kafes elemanina girerken koordinati eleman merkezine tasir; ara
    hucrelerde oteleme/donme olmadigi varsayilir (kurucu bunu kullanmaz).
    """
    x = y = 0.0
    for kafes, konum in zip(dagilim["kafesler"], _duzeyler(dagilim, anahtar)):
        ex, ey = eleman_merkezi(kafes, konum)
        x, y = x + ex, y + ey
    return (x, y)


def demet_anahtari(anahtar):
    """Tam kor anahtarindan demet anahtari (en ic duzey haric konum)."""
    return anahtar[0] if len(anahtar) == 2 else tuple(anahtar[:-1])


def demet_merkezi(dagilim, demet):
    """Demetin modeldeki (x, y) merkezi [cm] (tam kor)."""
    duzeyler = [demet] if dagilim.get("duzey_sayisi", 1) == 2 else list(demet)
    x = y = 0.0
    for kafes, konum in zip(dagilim["kafesler"][:-1], duzeyler):
        ex, ey = eleman_merkezi(kafes, konum)
        x, y = x + ex, y + ey
    return (x, y)


# ============================================================================
# 3. TEPE FAKTORLERI
# ============================================================================

def _tek_konum_metni(konum, tur):
    a, b = int(konum[0]), int(konum[1])
    if tur == "altigen":
        return "dıştan %d. halka, %d. konum" % (a + 1, b + 1)
    return "x = %d, y = %d" % (a + 1, b + 1)


def konum_metni(anahtar, kafes_turu=None, kafes_turleri=None):
    """
    Kafes konumunun okunur, 1'den numarali metni. Kare: (x, y) indisleri
    (x soldan, y alttan); altigen: (halka, sira) -- halka distan ice.
    Tam kor anahtari ((demet), (cubuk)) icin "demet ... · çubuk ...";
    kafes_turleri verilirse her duzey kendi turuyle yazilir.
    """
    try:
        if isinstance(anahtar[0], tuple):
            n = len(anahtar)
            turler = list(kafes_turleri or [kafes_turu] * n)
            demet = ", ".join(_tek_konum_metni(k, t)
                              for k, t in zip(anahtar[:-1], turler[:-1]))
            return _("demet %s · çubuk %s") % (
                demet, _tek_konum_metni(anahtar[-1], turler[-1]))
        return _tek_konum_metni(anahtar, kafes_turu)
    except (TypeError, ValueError, IndexError):
        return str(anahtar)


def demet_metni(demet, faktorler_ya_da_dagilim):
    """Demet anahtarinin okunur metni (tam kor)."""
    turler = faktorler_ya_da_dagilim.get("kafes_turleri") or []
    tur = turler[0] if turler else None
    if demet and isinstance(demet[0], tuple):
        return ", ".join(_tek_konum_metni(k, t) for k, t in zip(demet, turler))
    return _tek_konum_metni(demet, tur)


def _demet_faktorleri(bagil, bagil_eksenel):
    """
    Demet basina ozet (bagil birimde; kor geneli cubuk ortalamasi = 1).
      ortalama   (demetteki yakit cubuklarinin ortalamasi, sapma)
      tepe       (en guclu cubuk, sapma);  tepe_cubuk: anahtari
      F_dH_ic    tepe / ortalama  (demet ici radyal tepe)
      tepe_yerel (en yuksek yerel dilim, sapma) ve tepe_dilim: 3B'de; 2B'de None
    Sapmalar IYIMSERDIR (modul basligi): cubuklar bagimsiz sayilir.
    """
    gruplar = {}
    for a, v in bagil.items():
        gruplar.setdefault(demet_anahtari(a), []).append((a, v))
    sonuc = {}
    for demet, uyeler in gruplar.items():
        n = len(uyeler)
        ort = sum(v[0] for _a, v in uyeler) / n
        sap = math.sqrt(sum(v[1] ** 2 for _a, v in uyeler)) / n
        tepe_a, tepe = max(uyeler, key=lambda av: av[1][0])
        kayit = {"cubuk_sayisi": n, "ortalama": (ort, sap), "tepe": tepe,
                 "tepe_cubuk": tepe_a, "F_dH_ic": tepe[0] / ort if ort > 0 else None,
                 "tepe_yerel": None, "tepe_dilim": None}
        if bagil_eksenel:
            yerel = [(a, i, d) for a, _v in uyeler
                     for i, d in enumerate(bagil_eksenel[a])]
            ya, yi, yd = max(yerel, key=lambda t: t[2][0])
            kayit["tepe_yerel"], kayit["tepe_dilim"] = yd, (ya, yi)
        sonuc[demet] = kayit
    return sonuc


def _tam_kor_alanlari(sonuc):
    """tepe_faktorleri sonucuna demet duzeyi alanlarini ekler (tam kor)."""
    demetler = _demet_faktorleri(sonuc["bagil"], sonuc["bagil_eksenel"])
    sicak = max(demetler.items(), key=lambda kv: kv[1]["ortalama"][0])
    sonuc["demetler"] = demetler
    sonuc["demet_sayisi"] = len(demetler)
    sonuc["sicak_demet"] = sicak[0]
    sonuc["F_demet"] = sicak[1]["ortalama"][0]
    sonuc["F_demet_sapma"] = sicak[1]["ortalama"][1]
    return sonuc


def tepe_faktorleri(dagilim):
    """
    F_dH ve F_q hesaplar.

    NORMALIZASYON (tek demet ve tam kor icin AYNI):
      Payda, tally'nin kapsadigi TUM yakit cubuklarinin (hedef hucrenin tum
      distribcell ornekleri; tam korda butun demetlerdeki) ortalamasidir.
      Kilavuz/olcum borusu gibi yakitsiz konumlar tally'de yoktur, paydaya
      girmez. Bagil guc = deger / bu ortalama; bagil ortalama tam olarak 1.

    F_dH = maks(cubuk toplam gucu) / ortalama(cubuk toplam gucu)   -- TUM korda
    F_q  = maks(yerel dilim gucu)  / ortalama(yerel dilim gucu)    -- TUM korda
           yalnizca eksenel_dilim > 1 ise tanimli.

    Tam korda ek olarak (tek demette bu alanlar None):
      demetler     {demet: _demet_faktorleri kaydi} -- her demetin kendi
                   ortalamasi ve tepesi, KOR ortalamasina gore bagil
      sicak_demet  ortalamasi en yuksek demet
      F_demet      o demetin bagil ortalamasi (demet tepe faktoru)
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

    tam_kor = bool(dagilim.get("tam_kor"))
    sonuc = {
        "cubuk_sayisi": n,
        "eksenel_dilim": dagilim["eksenel_dilim"],
        "ortalama_cubuk": ort_cubuk,
        "F_dH": f_dh,
        "F_dH_sapma": f_dh_sapma,
        "sicak_cubuk": sicak_cubuk[0],
        "kafes_turu": dagilim.get("kafes_turu"),
        "sacilma": sacilma,
        "istatistik_sapma": ist_sapma,
        "yanlilik_orani": (ist_sapma / sacilma) if sacilma > 0 else None,
        "bagil": bagil,
        "F_q": None, "F_q_sapma": None, "sicak_dilim": None,
        "bagil_eksenel": None, "eksenel_profil": None,
        # --- tam kor (28.09.2026) ---
        "tam_kor": tam_kor,
        "kafes_turleri": list(dagilim.get("kafes_turleri") or [dagilim.get("kafes_turu")]),
        "demetler": None, "demet_sayisi": None, "sicak_demet": None,
        "F_demet": None, "F_demet_sapma": None,
    }

    if dagilim["eksenel_dilim"] > 1:
        _eksenel_faktorler(sonuc, konumlar, dagilim["eksenel_dilim"])
    if tam_kor:
        _tam_kor_alanlari(sonuc)
    return sonuc


def _eksenel_faktorler(sonuc, konumlar, eksenel_dilim):
    """F_q, sicak dilim, bagil eksenel harita ve eksenel profil (3B)."""
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
    for i in range(eksenel_dilim):
        t = sum(k["eksenel"][i][0] for k in konumlar.values())
        s = math.sqrt(sum(k["eksenel"][i][1] ** 2 for k in konumlar.values()))
        profil.append((t, s))
    ort_profil = sum(p[0] for p in profil) / len(profil)
    sonuc["eksenel_profil"] = [(p[0] / ort_profil, p[1] / ort_profil)
                               for p in profil] if ort_profil > 0 else None


# ============================================================================
# 4. MUTLAK GUC
# ============================================================================

def mutlak_guc(faktorler, toplam_guc, yukseklik=None, hedef_payi=None):
    """
    Bagil dagilimi mutlak guce cevirir.

    toplam_guc : modelin temsil ettigi bolgenin toplam gucu [W]
    yukseklik  : aktif yukseklik [cm]; verilirse lineer guc [W/cm] hesaplanir
    hedef_payi : hedef cubuk bolgesinin model geneli fisyon enerjisindeki payi
                 = kappa_hedef / kappa_model (kosucu.sonuc_oku: guc_toplam_ref /
                 guc_model_toplam). Verilirse cubuklara toplam_guc * pay
                 dagitilir; None ise (eski statepoint) tum guc hedef cubuklarda
                 sayilir -- baska fisil bolge (blanket, ikinci cubuk turu) varsa
                 cubuk gucu OLDUGUNDAN BUYUK cikar.

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
    pay = hedef_payi if (hedef_payi is not None and hedef_payi > 0) else None
    hedef = toplam_guc * pay if pay is not None else toplam_guc
    cubuk_ort = hedef / n
    sonuc = {
        "toplam_guc": toplam_guc,
        "hedef_payi": pay,
        "hedef_guc": hedef,
        "cubuk_ortalama_W": cubuk_ort,
        "cubuk_maks_W": cubuk_ort * faktorler["F_dH"],
    }
    if yukseklik and yukseklik > 0:
        sonuc["lineer_ortalama_W_cm"] = cubuk_ort / yukseklik
        # Maks lineer guc yerel tepeye baglidir: F_q varsa onu, yoksa F_dH'yi kullan
        tepe = faktorler["F_q"] or faktorler["F_dH"]
        sonuc["lineer_maks_W_cm"] = (cubuk_ort / yukseklik) * tepe
        sonuc["lineer_tepe_kaynagi"] = "F_q" if faktorler["F_q"] else "F_ΔH (2B — eksenel tepe dahil değil)"
    return sonuc


# ============================================================================
# 5. YORUM
# ============================================================================

def yorumla(faktorler, mutlak=None):
    """Ogrenciye yonelik kisa yorum satirlari."""
    if not faktorler:
        return ["Güç dağılımı hesaplanamadı."]
    satirlar = []
    f = faktorler["F_dH"]
    satirlar.append(
        "F_ΔH = %.4f — en sıcak çubuk ortalamanın %%%.1f üstünde güç üretiyor."
        % (f, (f - 1) * 100))
    if f < 1.02:
        satirlar.append("  Dağılım neredeyse düz. Yansıtıcı sınırlı tek demet "
                        "hesaplarında beklenen budur; gerçek bir korda kenar "
                        "etkileri ve yakıt yüklemesi tepeyi büyütür.")
    elif f > 1.65:
        satirlar.append("  Yüksek: tipik PWR tasarım sınırı F_ΔH ≈ 1.65 "
                        "civarındadır; yakıt yüklemesi düzeltilmeli.")
    if faktorler.get("tam_kor"):
        satirlar.append(
            _("Tam kor: %d demet, %d yakıt çubuğu. En sıcak demet %s; ortalaması "
              "kor ortalamasının %.4f katı (F_demet). F_ΔH ve F_q tüm kordaki "
              "yakıt çubukları üzerinden hesaplanır.")
            % (faktorler["demet_sayisi"], faktorler["cubuk_sayisi"],
               demet_metni(faktorler["sicak_demet"], faktorler), faktorler["F_demet"]))
    # --- maksimumun yukari yanliligi ---
    oran = faktorler.get("yanlilik_orani")
    if oran is not None and oran > 0.3:
        satirlar.append(
            "  Dikkat: çubuk başına istatistik sapma (%.4f) dağılımın gerçek "
            "saçılmasının (%.4f) %%%.0f kadarı. Bir en büyük değer hesaplandığı "
            "için F_ΔH bu durumda yukarı yanlıdır — gerçek tepe daha düşüktür. "
            "Çevrim başına parçacık sayısını artırın."
            % (faktorler["istatistik_sapma"], faktorler["sacilma"], oran * 100))

    if faktorler["F_q"]:
        satirlar.append(
            "F_q = %.4f — yerel güç yoğunluğu tepesi (eksenel şekil dahil)."
            % faktorler["F_q"])
        if faktorler["eksenel_dilim"] < 10:
            satirlar.append(
                "  Dikkat: yalnızca %d eksenel dilim var. Kaba dilimler tepeyi "
                "ortalar ve F_q'yu olduğundan küçük gösterir (saf kosinüs "
                "profilinde ince dilim sınırı π/2 = 1.571'dir). En az 10–20 "
                "dilim kullanın."
                % faktorler["eksenel_dilim"])
        if faktorler["F_q"] > 2.6:
            satirlar.append("  Yüksek: tipik PWR sınırı F_q ≈ 2.3–2.6.")
    else:
        satirlar.append("F_q tanımsız — model 2B (eksenel yükseklik yok). "
                        "Eksenel tepe olmadan yerel güç yoğunluğu hesaplanamaz; "
                        "Kor sekmesinde yükseklik tanımlayın.")
    if mutlak:
        satirlar.append("Çubuk başına ortalama %.1f W, en sıcak çubuk %.1f W."
                        % (mutlak["cubuk_ortalama_W"], mutlak["cubuk_maks_W"]))
        if mutlak.get("hedef_payi") is not None:
            satirlar.append(_("  Modelin fisyon enerjisinin %%%.1f'i bu çubuklarda "
                              "(%.4g W); kalanı diğer fisil bölgelerde.")
                            % (100.0 * mutlak["hedef_payi"], mutlak["hedef_guc"]))
        else:
            satirlar.append(_("  Not: güç payı ölçülemedi (eski koşu); toplam gücün "
                              "tamamı bu çubuklara yazıldı. Başka fisil bölge varsa "
                              "çubuk gücü olduğundan büyüktür."))
        if "lineer_maks_W_cm" in mutlak:
            lm = mutlak["lineer_maks_W_cm"]
            satirlar.append("En yüksek çizgisel güç %.1f W/cm (tepe faktörü: %s)."
                            % (lm, mutlak["lineer_tepe_kaynagi"]))
            if lm > 500:
                satirlar.append("  Sınırın üstünde: tipik PWR çizgisel güç "
                                "sınırı ~400–500 W/cm.")
    satirlar.append(
        "Not: çubuk başına sapmalar iyimser olabilir. Özdeğer hesabında ardışık "
        "çevrimler birbirine bağlıdır ve OpenMC'nin raporladığı tally belirsizliği "
        "bunu hesaba katmaz; gerçek belirsizlik daha büyüktür. Kesin değer için "
        "modeli birkaç farklı rastgele tohumla koşup sonuçların saçılmasına bakın.")
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
                hatalar.append("tohum %d: koşu başarısız" % t)
                continue
            s = kosucu.sonuc_oku(kosu["statepoint"])
            f = (s.get("guc") or {}).get("faktorler")
            if not f:
                hatalar.append("tohum %d: güç dağılımı okunamadı" % t)
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
        return "güç dağılımı yok"
    p = ["F_ΔH = %.4f ± %.4f" % (faktorler["F_dH"], faktorler["F_dH_sapma"])]
    if faktorler["F_q"]:
        p.append("F_q = %.4f ± %.4f" % (faktorler["F_q"], faktorler["F_q_sapma"]))
    p.append("en sıcak çubuk: %s" % konum_metni(faktorler["sicak_cubuk"],
                                                 faktorler.get("kafes_turu"),
                                                 faktorler.get("kafes_turleri")))
    if faktorler.get("tam_kor"):
        p.append(_("en sıcak demet: %s (F_demet = %.4f)")
                 % (demet_metni(faktorler["sicak_demet"], faktorler), faktorler["F_demet"]))
    return "  |  ".join(p)
