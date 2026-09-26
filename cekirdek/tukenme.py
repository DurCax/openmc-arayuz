# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme.py  --  Yanma (depletion) hesabi
================================================================================

 KULLANIM
   python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 8
   python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json --hazirla   # kosmadan

 NE YAPAR
   Spec'teki "tukenme" bolumune gore yanabilir malzemeleri isaretler, hacimlerini
   ANALITIK olarak hesaplar, uygun zinciri secer ve openmc.deplete ile
   transport-bozunum dongusunu kosar. Sonuc: depletion_results.h5.

 TASARIM KARARLARI (hepsi olcume ya da bilinen bir tuzaga dayanir)

   1. GUC = GUC YOGUNLUGU [W/gHM].
      Mutlak guc [W] 2B bir modelde "cm basina" olmak zorunda kalirdi -- tam
      bu projede daha once birkac kez yakaladigimiz turden sessiz bir birim
      tuzagi. W/gHM geometriden bagimsizdir ve muhendislerin gercekten verdigi
      sayidir (PWR ~38-40).

   2. HACIMLER ANALITIK VE KESIN OLMALI.
      Tukenmede reaksiyon hizi / (N x V) atom basina hizi verir. Hacim f kat
      yanlissa yanma hizi da f kat yanlis olur -- k-eff'te hicbir iz birakmadan.
      Hacim = bolge alani x (katman yuksekligi x o katmandaki cubuk sayisi)
      toplami. Testte OpenMC'nin stokastik hacim hesabiyla karsilastirilir.

   3. ZINCIR SPEKTRUMA GORE, VE FISYON VERIMI DE.
      Termal/hizli zincir yalnizca YAKALAMA DALLANMA ORANLARINI degistirir
      (olculdu: 101 nuklid; or. Am241(n,g)->Am242m termalde %8.1, hizlida
      %13.2). Fisyon urunu verimleri ise ayri bir ayardir ve OpenMC'nin
      varsayilani SABIT 0.0253 eV'tur -- hizli zincir secilse bile. Hizli
      sistemde verim enerjisi ayrica 500 keV'e cekilir.

   4. ALT SURECTE KOSAR.
      openmc.lib icindeki bir C++ terminate() butun sureci oldurur (onizlemede
      yasandi). Arayuz bu kodu kendi surecinde asla calistirmaz.

 OLCULEN MALIYET (pin hucre, 2000 x 20 parcacik, 2 transport)
   CASL 228 nuklid: 37 s     ENDF/B-VIII.0 3820 nuklid: 125 s
   Zincirdeki nuklidler yakita eklenir; transport bu yuzden yavaslar.
================================================================================
"""

import math
import os
import sys

from cekirdek import sema, veri_bilgi

ZINCIRLER = {
    "termal":      "chain_endfb80_thermal.xml",
    "hizli":       "chain_endfb80_fast.xml",
    "casl_termal": "chain_casl_thermal.xml",
    "casl_hizli":  "chain_casl_fast.xml",
}

# Zincirdeki fisyon verimi enerjileri 0.0253 eV, 500 keV ve 14 MeV'tir.
VERIM_ENERJISI = {"termal": 0.0253, "hizli": 5.0e5}

# Yanabilir zehirler: fisil olmasalar da yanmalari reaktiviteyi belirler.
YANABILIR_ZEHIR = {"Gd", "Er"}

# Moderator sayilan S(a,b) kayitlari (on eklerine gore). Berilyum BILEREK
# yok: tamburlu korda Be yalnizca yansiticidir, kor spektrumu hizlidir.
_MODERATOR_SAB = ("c_H_", "c_D_", "c_Graphite", "c_ortho", "c_para")


# ============================================================================
# Zincir secimi
# ============================================================================

def spektrum_tahmini(spec):
    """
    ("termal"|"hizli", gerekce).

    Kural: modelde hidrojen ya da doteryum iceren, ya da grafit S(a,b)'si
    tanimli bir malzeme varsa TERMAL; yoksa HIZLI. Hidrojen baskin
    yavaslaticidir; su, ZrH, polietilen hepsini kapsar.
    """
    for m in spec.get("malzemeler", []):
        for s in m.get("sab") or []:
            if any(str(s).startswith(o) for o in _MODERATOR_SAB):
                return "termal", "'%s' malzemesinde %s var" % (m["ad"], s)
        for b in m.get("bilesim", []):
            isim = b.get("isim") or ""
            eleman = isim.rstrip("0123456789") if b.get("tur") == "nuklid" else isim
            if eleman in ("H", "D") and float(b.get("miktar") or 0) > 0:
                return "termal", "'%s' malzemesi hidrojen içeriyor" % m["ad"]
    return "hizli", "modelde hidrojen ya da grafit moderatör yok"


def zincir_secimi(spec):
    """
    DONER {"tur", "yol", "spektrum", "verim_enerjisi", "gerekce"}
    """
    t = spec.get("tukenme") or {}
    istek = t.get("zincir") or "otomatik"
    spektrum, gerekce = spektrum_tahmini(spec)
    if istek == "otomatik":
        tur = spektrum
        gerekce = "otomatik: " + gerekce
    else:
        tur = istek
        gerekce = "kullanıcı seçimi"
    temel = "hizli" if tur.endswith("hizli") else "termal"
    return {
        "tur": tur,
        "yol": os.path.join(veri_bilgi.zincir_dizini(), ZINCIRLER[tur]),
        "spektrum": spektrum,
        "temel": temel,
        "verim_enerjisi": VERIM_ENERJISI[temel],
        "gerekce": gerekce,
    }


# ============================================================================
# Yanabilir malzemeler ve analitik hacimler
# ============================================================================

def _z(nuklid_ya_da_element):
    import openmc.data
    try:
        return openmc.data.zam(nuklid_ya_da_element)[0]
    except Exception:
        return openmc.data.ATOMIC_NUMBER.get(nuklid_ya_da_element, 0)


def yanabilir_adlar(spec):
    """Yanacak malzemelerin adlari: fisil olanlar + yanabilir zehirler + ek liste."""
    adlar = []
    for m in spec.get("malzemeler", []):
        fisil = zehir = False
        for b in m.get("bilesim", []):
            isim = b.get("isim") or ""
            if _z(isim) >= 90:
                fisil = True
            eleman = isim.rstrip("0123456789_m") if b.get("tur") == "nuklid" else isim
            if eleman in YANABILIR_ZEHIR:
                zehir = True
        if fisil or zehir:
            adlar.append(m["ad"])
    for ad in (spec.get("tukenme") or {}).get("ek_malzemeler") or []:
        if ad not in adlar and sema.malzeme_bul(spec, ad) is not None:
            adlar.append(ad)
    return adlar


def _sayim(spec, dolgu, hedef, esleme=None, derinlik=0):
    """'dolgu' icinde 'hedef' cubuk/plaka kac kez geciyor (demetler icinden)."""
    if not dolgu or derinlik > 8:
        return 0
    if dolgu == hedef:
        return 1
    d = sema.demet_bul(spec, dolgu)
    if d is None:
        return 0
    anahtar = d.get("anahtar") or {}
    toplam = 0
    for satir in d.get("harita") or []:
        for harf in satir:
            if harf in anahtar:
                toplam += _sayim(spec, anahtar[harf], hedef, None, derinlik + 1)
    return toplam


def _kor_sayimi(spec, kor, dolgu, hedef, esleme=None):
    """Bir katmanin dolgusunda hedef kac kez var (kare_kafes kor haritasi dahil)."""
    if kor["tur"] == "kare_kafes" and dolgu is None:
        anahtar = dict(kor.get("anahtar") or {})
        if esleme:
            anahtar.update(esleme)
        toplam = 0
        for satir in kor.get("harita") or []:
            for harf in satir:
                if harf in anahtar:
                    toplam += _sayim(spec, anahtar[harf], hedef)
        return toplam
    return _sayim(spec, dolgu or sema.ana_dolgu(kor), hedef)


def _eksenel_dilimler(kor):
    """[(yukseklik, dolgu_adi|None, anahtar|None)]. 2B modelde tek dilim, 1 cm."""
    katmanlar = sema.eksenel_katmanlar(kor)
    if katmanlar:
        return [(z1 - z0, b.get("dolgu"), b.get("anahtar")) for z0, z1, b in katmanlar]
    h = sema.kor_yuksekligi(kor)
    return [(h if h else 1.0, None, None)]



def yakit_ornek_sayisi(spec):
    """
    Yanabilir malzemelerin geometrideki en buyuk ORNEK (hucre) sayisi.
    "Cubuk cubuk yanma" (diff_burnable_mats) her ornegi ayri malzeme yapar;
    tek ornekte (pin hucre, tek kabuklu kure, homojen tek katmanli kor)
    hicbir sey degistirmez. Sayim tukenme.hacimler()'in izledigi yolu izler.
    uygunluk.tukenme_ayirma_anlamli bunu kullanir.
    """
    kor = spec.get("kor") or {}
    adlar = yanabilir_adlar(spec)
    if kor.get("tur") == "kuresel":
        return max([sum(1 for k in kor.get("kabuklar") or [] if k.get("malzeme") == ad)
                    for ad in adlar] or [0])
    dilimler = _eksenel_dilimler(kor)

    def sayim(parca):
        return sum(_kor_sayimi(spec, kor, d, parca, e) for _h, d, e in dilimler)

    en_cok = 0
    for ad in adlar:
        n = 0
        for c in spec.get("cubuklar", []):
            bolge = sum(1 for b in c.get("bolgeler") or [] if b.get("malzeme") == ad)
            if bolge:
                n += bolge * sayim(c["ad"])
        for p in spec.get("plakalar", []):
            if p.get("et_malzeme") == ad:
                n += int(p.get("plaka_sayisi") or 1) * sayim(p["ad"])
        if kor.get("tur") == "tamburlu":
            n += sum(1 for _h, d, _e in dilimler if (d or kor.get("dolgu")) == ad)
        en_cok = max(en_cok, n)
    return en_cok


def hacimler(spec):
    """
    {malzeme_adi: {"hacim": cm3|None, "yontem": str, "ayrinti": str}}

    2B modelde hacim 1 cm yukseklik icindir; guc yogunlugu kullanildigi icin
    bu tutarlidir (kutle ve guc ayni oranda olceklenir).
    Analitik hesaplanamayan (or. dolgu olarak dogrudan kullanilan homojen)
    malzemeler icin hacim None doner; bunlar icin stokastik_hacimler()'e bakin.
    """
    kor = spec["kor"]
    sonuc = {}
    dilimler = _eksenel_dilimler(kor)

    for ad in yanabilir_adlar(spec):
        V = 0.0
        parcalar = []
        analitik_disi = False

        # --- kuresel kabuklar ---
        if kor["tur"] == "kuresel":
            r_ic = 0.0
            for k in kor.get("kabuklar") or []:
                if k.get("malzeme") == ad:
                    v = 4.0 / 3.0 * math.pi * (k["r"] ** 3 - r_ic ** 3)
                    V += v
                    parcalar.append("kabuk r = %g cm: %.4g cm³" % (k["r"], v))
                r_ic = k["r"]
            sonuc[ad] = {"hacim": V if V > 0 else None,
                         "yontem": "analitik" if V > 0 else "yok",
                         "ayrinti": "; ".join(parcalar)}
            continue

        # --- cubuk bolgeleri ---
        for c in spec.get("cubuklar", []):
            bolgeler = c.get("bolgeler") or []
            for i, b in enumerate(bolgeler):
                if b.get("malzeme") != ad:
                    continue
                if b.get("r") is None:
                    analitik_disi = True       # dis bolge: alan kafes adimina bagli
                    continue
                r_ic = bolgeler[i - 1]["r"] if i > 0 else 0.0
                alan = math.pi * (b["r"] ** 2 - r_ic ** 2)
                for h, dolgu, esleme in dilimler:
                    n = _kor_sayimi(spec, kor, dolgu, c["ad"], esleme)
                    if n:
                        V += alan * h * n
                        parcalar.append("%s, %d. bölge: %d adet × %g cm" % (c["ad"], i + 1, n, h))

        # --- plaka eti ---
        for p in spec.get("plakalar", []):
            if p.get("et_malzeme") != ad:
                continue
            alan = p["et_kalinlik"] * p["plaka_genislik"] * p["plaka_sayisi"]
            for h, dolgu, esleme in dilimler:
                n = _kor_sayimi(spec, kor, dolgu, p["ad"], esleme)
                if n:
                    V += alan * h * n
                    parcalar.append("%s: %d eleman × %g cm" % (p["ad"], n, h))

        # --- tamburlu kor: kor silindirini dogrudan dolduran homojen malzeme ---
        if kor["tur"] == "tamburlu":
            R = float(kor.get("kor_yaricap") or 0.0)
            for h, dolgu, _e in dilimler:
                if (dolgu or kor.get("dolgu")) == ad:
                    v = math.pi * R * R * h
                    V += v
                    parcalar.append("kor silindiri R = %g cm × %g cm" % (R, h))
        # --- baska bir yerde dogrudan dolgu olarak kullanilan malzeme ---
        elif kor.get("dolgu") == ad or any(d == ad for _h, d, _e in dilimler):
            analitik_disi = True

        if analitik_disi:
            sonuc[ad] = {"hacim": None, "yontem": "stokastik hesap gerekli",
                         "ayrinti": "malzeme çubuk/plaka dışında da kullanılıyor"}
        elif V > 0:
            sonuc[ad] = {"hacim": V, "yontem": "analitik", "ayrinti": "; ".join(parcalar)}
        else:
            sonuc[ad] = {"hacim": None, "yontem": "yok",
                         "ayrinti": "malzeme geometride bulunamadı"}
    return sonuc


def stokastik_hacimler(spec, adlar, orneklem=2_000_000, dizin=None):
    """
    OpenMC'nin stokastik hacim hesabi. Analitik hacmin DOGRULANMASI ve
    analitik hesaplanamayan malzemeler icin. {ad: (hacim, sapma)}.
    """
    import tempfile
    import openmc
    from cekirdek import kurucu
    model, bilgi = kurucu.kur(spec)
    model.tallies = openmc.Tallies()
    nesneler = bilgi["malzemeler"]
    alanlar = [nesneler[a] for a in adlar if a in nesneler]
    gx, gy = bilgi["sinir_kutu"]
    h = sema.kor_yuksekligi(spec["kor"])
    z = (h / 2.0) if h else 0.5
    if spec["kor"]["tur"] == "kuresel":
        r = gx / 2.0
        alt, ust = (-r, -r, -r), (r, r, r)
    else:
        alt, ust = (-gx / 2, -gy / 2, -z), (gx / 2, gy / 2, z)
    vc = openmc.VolumeCalculation(alanlar, orneklem, alt, ust)
    model.settings.volume_calculations = [vc]
    dizin = dizin or tempfile.mkdtemp(prefix="tukenme_hacim_")
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model.export_to_model_xml()
        openmc.calculate_volumes(output=False)
        sonuc = openmc.VolumeCalculation.from_hdf5(os.path.join(dizin, "volume_1.h5"))
    finally:
        os.chdir(eski)
    cikti = {}
    ters = {id(v): k for k, v in nesneler.items()}
    for m in alanlar:
        v = sonuc.volumes[m.id]
        cikti[ters[id(m)]] = (float(v.nominal_value), float(v.std_dev))
    return cikti


# ============================================================================
# Model hazirlama ve kosu
# ============================================================================

def hazirla(spec):
    """
    Tukenmeye hazir model. DONER (model, bilgi).

    bilgi: {"zincir": zincir_secimi(), "hacimler": hacimler(),
            "agir_metal_g": float, "yanabilir": [ad]}
    Hacmi hesaplanamayan yanabilir malzeme varsa ValueError -- tahminle
    devam etmek yanma hizini sessizce bozardi.
    """
    from cekirdek import kurucu
    model, kbilgi = kurucu.kur(spec)
    zs = zincir_secimi(spec)
    tamam, mesaj, _ = veri_bilgi.zincir_kontrol(zs["yol"])
    if not tamam:
        raise ValueError(mesaj)

    hv = hacimler(spec)
    eksik = [a for a, v in hv.items() if not v["hacim"]]
    if eksik:
        raise ValueError(
            "hacmi analitik hesaplanamayan yanabilir malzeme: %s (%s). "
            "Tükenme kesin hacim gerektirir."
            % (", ".join(eksik), "; ".join(hv[a]["ayrinti"] for a in eksik)))
    nesneler = kbilgi["malzemeler"]
    agir = 0.0
    for ad, v in hv.items():
        m = nesneler[ad]
        m.depletable = True
        m.volume = v["hacim"]
        agir += _agir_metal_kutlesi(m)
    if not hv:
        raise ValueError("modelde yanabilir (fisil) malzeme yok")
    return model, {"zincir": zs, "hacimler": hv, "agir_metal_g": agir,
                   "yanabilir": list(hv)}


def _agir_metal_kutlesi(m):
    """Malzemedeki Z >= 90 nuklidlerin kutlesi [g] (m.volume ayarli olmali)."""
    import openmc.data
    toplam = 0.0
    for nuklid, yog in m.get_nuclide_atom_densities().items():   # atom/b-cm
        if _z(nuklid) >= 90:
            toplam += yog * 1e24 * m.volume * openmc.data.atomic_mass(nuklid) \
                / openmc.data.AVOGADRO
    return toplam


def yanma(zaman_gun, guc_yogunlugu):
    """Yanma [MWd/kgHM] = p [W/g] x t [gun] / 1000."""
    return guc_yogunlugu * zaman_gun / 1000.0


def calistir(spec, dizin, geri_cagir=None):
    """
    Tukenme kosusu. dizin icinde depletion_results.h5 uretir.
    OMP_NUM_THREADS bu fonksiyondan ONCE ayarlanmis olmali (bkz. _terminal).
    """
    import openmc.deplete as d
    t = spec["tukenme"]
    model, bilgi = hazirla(spec)
    zs = bilgi["zincir"]
    os.makedirs(dizin, exist_ok=True)
    # Eski sonuc SILINIR, sonra spec kaydi yazilir. Sira onemli: kosu yarida
    # kalirsa dizinde eski bir sonuc ile YENI bir spec kaydi yan yana kalir
    # ve eski sonuc "guncel" diye gosterilirdi.
    onceki = os.path.join(dizin, "depletion_results.h5")
    if os.path.exists(onceki):
        os.remove(onceki)
    spec_kaydet(spec, dizin)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        op = d.CoupledOperator(
            model, zs["yol"],
            diff_burnable_mats=bool(t.get("malzemeleri_ayir")),
            normalization_mode="fission-q",
            fission_yield_mode="constant",
            fission_yield_opts={"energy": zs["verim_enerjisi"]},
        )
        Sinif = {"cecm": d.CECMIntegrator,
                 "predictor": d.PredictorIntegrator}[t.get("entegrator") or "cecm"]
        integ = Sinif(op, list(t["adimlar"]),
                      power_density=float(t["guc_yogunlugu"]),
                      timestep_units=t.get("adim_birimi") or "d")
        integ.integrate()
    finally:
        os.chdir(eski)
    return os.path.join(dizin, "depletion_results.h5"), bilgi


def sonuc_oku(h5, spec):
    """
    DONER {"zaman_d", "yanma", "k", "k_sapma", "atomlar": {malz: {nuklid: [..]}},
           "yogunluk": {malz: {nuklid: [atom/b-cm]}}}
    """
    import openmc.deplete as d
    r = d.Results(h5)
    zaman, k = r.get_keff(time_units="d")
    p = float(spec["tukenme"]["guc_yogunlugu"])
    hv = hacimler(spec)
    izlenen = (spec.get("tukenme") or {}).get("izlenen") or []
    atomlar, yogunluk = {}, {}
    malz_idleri = list(r[0].index_mat.keys())
    from cekirdek import kurucu
    _m, kb = kurucu.kur(spec)
    ad_by_id = {str(m.id): ad for ad, m in kb["malzemeler"].items()}
    for mid in malz_idleri:
        ad = ad_by_id.get(str(mid), str(mid))
        atomlar[ad], yogunluk[ad] = {}, {}
        V = (hv.get(ad) or {}).get("hacim")
        for n in izlenen:
            try:
                _t, a = r.get_atoms(str(mid), n)
            except Exception:
                continue
            atomlar[ad][n] = [float(x) for x in a]
            if V:
                yogunluk[ad][n] = [float(x) / V * 1e-24 for x in a]
    return {
        "zaman_d": [float(x) for x in zaman],
        "yanma": [yanma(float(x), p) for x in zaman],
        "k": [float(x) for x in k[:, 0]],
        "k_sapma": [float(x) for x in k[:, 1]],
        "atomlar": atomlar,
        "yogunluk": yogunluk,
        "adim_sayisi": len(zaman) - 1,
    }


# ============================================================================
# Onceki kosu
#   Arayuz acildiginda son koşunun sonucu gosterilir. Tuzak: sonuc SU ANKI
#   spec'e ait olmayabilir (kullanici kosudan sonra gucu ya da zenginligi
#   degistirmis olabilir). Eski bir sonucu guncelmis gibi gostermek, hic
#   gostermemekten kotudur. Bu yuzden kosu basinda spec'in kopyasi yazilir;
#   acilista karsilastirilir ve sonuc O KOPYAYA gore okunur (malzeme
#   kimlikleri ve hacimler kosudaki modelden gelsin).
# ============================================================================

SPEC_KAYDI = "tukenme_spec.json"

# Fizigi etkilemeyen bolumler: bunlar degisti diye sonuc eskimez.
_FIZIK_DISI = ("ad", "aciklama", "calistirma")


def kosu_dizini(spec, proje_yolu=None):
    """Tukenme sonuclarinin dizini: <proje dizini>/<calistirma.dizin>_tukenme."""
    taban = os.path.dirname(os.path.abspath(proje_yolu)) if proje_yolu else os.getcwd()
    dizin = (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme"
    return dizin if os.path.isabs(dizin) else os.path.join(taban, dizin)


def _fizik_kismi(spec):
    """
    Sonucu etkileyen kisim. ad/aciklama/calistirma ve tukenme.var cikarilir:
    tukenmeyi kapatip acmak sonucu eskitmez.

    Karsilastirma METIN (json/hash) ile degil Python esitligiyle yapilir:
    JSON'da 3 ile 3.0 farkli metindir ama ayni sayidir; hash kullanmak
    degismemis bir modeli "eski" gosterirdi.
    """
    import copy
    sade = {k: copy.deepcopy(v) for k, v in sema.tamamla(spec).items()
            if k not in _FIZIK_DISI}
    sade.get("tukenme", {}).pop("var", None)
    sade.pop("surum", None)
    return sade


def spec_kaydet(spec, dizin):
    import json
    with open(os.path.join(dizin, SPEC_KAYDI), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)


def onceki_sonuc(spec, dizin):
    """
    Dizindeki son tukenme sonucu. Sonuc yoksa None.
    DONER {"h5", "tarih": float, "durum": "guncel"|"eski"|"bilinmiyor",
           "farklar": [bolum], "sonuc": sonuc_oku(...)}
    """
    h5 = os.path.join(dizin, "depletion_results.h5")
    if not os.path.exists(h5):
        return None
    durum, farklar = eskime(spec, dizin)
    kayit = _kayit_oku(dizin)
    return {"h5": h5, "tarih": os.path.getmtime(h5), "durum": durum,
            "farklar": farklar, "sonuc": sonuc_oku(h5, kayit or spec)}


def _kayit_oku(dizin):
    yol = os.path.join(dizin, SPEC_KAYDI)
    return sema.yukle(yol) if os.path.exists(yol) else None


# Spec bolumlerinin kullaniciya gorunen adlari (eskime farklari icin).
BOLUM_ADLARI = {
    "malzemeler": "malzemeler", "cubuklar": "çubuklar", "plakalar": "plaka elemanları",
    "demetler": "demetler", "kor": "kor", "ayarlar": "hesap ayarları",
    "tallyler": "tally'ler", "guc_dagilimi": "güç dağılımı", "tukenme": "tükenme ayarları",
}
SPEKTRUM_ADLARI = {"termal": "termal", "hizli": "hızlı"}


def fark_metni(farklar):
    """Eskime farklarinin okunur listesi: "malzemeler, hesap ayarları"."""
    return ", ".join(BOLUM_ADLARI.get(f, f) for f in farklar)


def eskime(spec, dizin):
    """
    (durum, farklar): sonuc bu spec'e mi ait? Sonucu OKUMAZ -- arayuz her
    duzenlemede cagirir, ucuz olmali.
      "guncel"     : fizigi etkileyen her sey ayni
      "eski"       : farklar = degisen spec bolumleri
      "bilinmiyor" : kosunun spec kaydi yok
    """
    kayit = _kayit_oku(dizin)
    if kayit is None:
        return "bilinmiyor", []
    a, b = _fizik_kismi(spec), _fizik_kismi(kayit)
    farklar = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return ("eski" if farklar else "guncel"), farklar


def transport_sayisi(spec):
    """Toplam transport cozumu: (adim + 1) x entegrator basina transport."""
    t = spec.get("tukenme") or {}
    n = len(t.get("adimlar") or [])
    basina = 2 if (t.get("entegrator") or "cecm") == "cecm" else 1
    return n * basina + 1


# ============================================================================
# Terminal
# ============================================================================

def _terminal(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m cekirdek.tukenme")
    ap.add_argument("spec")
    ap.add_argument("-s", "--is-parcacigi", type=int, default=None)
    ap.add_argument("--dizin", default=None)
    ap.add_argument("--hazirla", action="store_true",
                    help="kosmadan hacim/zincir/agir metal bilgisini yazdir")
    a = ap.parse_args(argv)

    # libgomp OMP_NUM_THREADS'i KUTUPHANE YUKLENIRKEN okur; openmc.deplete'in
    # ice aktarilmasi kutuphaneyi yukler. Bu yuzden once ortam, sonra import.
    if a.is_parcacigi:
        os.environ["OMP_NUM_THREADS"] = str(a.is_parcacigi)

    import warnings
    warnings.filterwarnings("ignore")
    spec = sema.yukle(a.spec)
    spec.setdefault("tukenme", {})["var"] = True
    zs = zincir_secimi(spec)
    t = spec["tukenme"]
    print("=" * 74)
    print(" TÜKENME: %s" % spec.get("ad", ""))
    print("=" * 74)
    print("  zincir        : %s  (%s)" % (os.path.basename(zs["yol"]), zs["gerekce"]))
    print("  fisyon verimi : %s eV (%s spektrum)"
          % (zs["verim_enerjisi"], SPEKTRUM_ADLARI.get(zs["temel"], zs["temel"])))
    print("  güç yoğunluğu : %g W/gHM" % float(t["guc_yogunlugu"]))
    print("  adımlar       : %s %s  → %d transport"
          % (", ".join("%g" % float(x) for x in t["adimlar"]),
             {"d": "gün"}.get(t.get("adim_birimi", "d"), t.get("adim_birimi", "d")),
             transport_sayisi(spec)))
    for ad, v in hacimler(spec).items():
        print("  hacim %-10s: %s cm³ [%s] %s" % (ad, ("%.6g" % v["hacim"]) if v["hacim"] else "—",
                                                  v["yontem"], v["ayrinti"]))
    if a.hazirla:
        _m, b = hazirla(spec)
        print("  ağır metal    : %.6g g" % b["agir_metal_g"])
        return 0

    dizin = a.dizin or os.path.join(os.path.dirname(os.path.abspath(a.spec)),
                                    (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme")
    h5, bilgi = calistir(spec, dizin)
    s = sonuc_oku(h5, spec)
    print("\n  ağır metal: %.6g g" % bilgi["agir_metal_g"])
    print("  %8s %10s %18s" % ("gün", "MWd/kg", "k-eff"))
    for z, b, k, sk in zip(s["zaman_d"], s["yanma"], s["k"], s["k_sapma"]):
        print("  %8.2f %10.3f %10.5f ± %.5f" % (z, b, k, sk))
    print("\n  sonuç: %s" % h5)
    return 0


if __name__ == "__main__":
    sys.exit(_terminal(sys.argv[1:]))
