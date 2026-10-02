# -*- coding: utf-8 -*-
"""
================================================================================
 guc_tablo.py  --  Pin (cubuk) gucu tablosu, demet ozeti, ceyrek katlama, CSV
================================================================================

 Guc haritasinin (arayuz/guc_harita.py) cizdigi degerlerin satir satir hali.
 Tablo YENI hesap yapmaz: bagil guc ve σ guc.tepe_faktorleri'nin "bagil"
 sozlugunden AYNEN alinir (tablo = harita); mutlak guc guc.mutlak_guc'un
 cubuk ortalamasiyla olceklenir. Boylece tablo, harita, F_ΔH ve rapor ayni
 sayilari gosterir.

 SATIR (sozluk; her cagri yeni nesneler dondurur, girdi degismez)
   anahtar      guc konum anahtari (guc.dagilim_oku)
   demet        demet konum metni (tam kor) ya da ""
   konum        cubuk konum metni (guc.konum_metni, 1'den numarali)
   x, y         cubugun modeldeki merkezi [cm] (guc.cubuk_merkezi)
   tur          cubuk turu (cok turlu guc) ya da ""
   kesik        F_ΔH/F_q disinda tutulan kesik cubuk (guc_faktor.kesik_cubuklar)
   sicak        F_ΔH'nin cubugu
   bagil, sigma bagil guc (kor/demet geneli yakit cubugu ortalamasi = 1) ve σ
   W, W_sigma   cubuk gucu [W] (mutlak guc verilmisse; yoksa None)
   q            ortalama lineer guc q′ = W / aktif yukseklik [W/cm]
   dilimler     3B: [{"dilim", "z_alt", "z_ust", "bagil", "sigma", "W", "q"}]
                bagil dilimde F_q'nun referansina (ortalama yerel guc) gore;
                q = W_k / Δz. 2B'de bos liste.
   tepe_q       satirin en buyuk dilim q′'su (3B) ya da q (2B)

 NORMALIZASYON (guc.tepe_faktorleri ile ayni)
   bagil_i = P_i / ortalama(kesik olmayan yakit cubuklari)
   W_i     = bagil_i × cubuk_ortalama_W   (cubuk_ortalama_W = hedef_guc / n)
   Σ W_i (kesikler DAHIL) = toplam_guc × hedef_payi  -- toplam korunur.

 CEYREK KATLAMA (yalniz simetri DOGRULANIRSA)
   Geometrideki her kare kafes x ve y'de ayna simetrik (evren kimlikleri) ve
   kendi elemaninda ortalanmissa, ve tablonun konum kumesi aynalamaya kapaliysa
   (ayni cubuk turleriyle) dort ayna goruntusunun ortalamasi alinir.
   Altigen kafes, gelismis (agac) mod, tamburlu kor, kesik cubuk: REDDEDILIR.
   Katlama istatistik gurultuyu azaltir; fiziksel bir asimetriyi (kontrol
   cubugu, asimetrik yukleme) SAKLAMAMASI icin geometri denetimi zorunludur.
   "asimetri" alani yorungedeki en buyuk |deger − ortalama| / ortalama'dir.
================================================================================
"""

import csv
import io
import math

from cekirdek import guc as _guc
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_MERKEZ_TOLERANSI = 1e-6     # kafes ortalanmis mi [cm] (yuvarlama payi)


# ============================================================================
# 1. TABLO
# ============================================================================

def _demet_metni(dagilim, anahtar, turler):
    if not dagilim.get("tam_kor"):
        return ""
    return _guc.demet_metni(_guc.demet_anahtari(anahtar), {"kafes_turleri": turler})


def _cubuk_metni(anahtar, dagilim, turler):
    son = anahtar[-1] if dagilim.get("tam_kor") else anahtar
    return _guc._tek_konum_metni(son, (turler or [dagilim.get("kafes_turu")])[-1])


def _dilim_satirlari(kayit, faktorler, anahtar, W, sinirlar, n):
    """3B: dilim kayitlari. Kesik cubugun bagil_eksenel kaydi yoktur; dilim
    degeri ortalama yerel guce bolunerek ayni referansta yazilir."""
    toplam = kayit["toplam"][0]
    ort_yerel = faktorler.get("ortalama_yerel") or 0.0
    bagil_e = (faktorler.get("bagil_eksenel") or {}).get(anahtar)
    z0, z1 = sinirlar if sinirlar else (0.0, float(n))
    dz = (z1 - z0) / n
    satirlar = []
    for k, (deger, sapma) in enumerate(kayit["eksenel"]):
        if bagil_e is not None:
            b, s = bagil_e[k]
        else:
            b = deger / ort_yerel if ort_yerel > 0 else None
            s = sapma / ort_yerel if ort_yerel > 0 else None
        w_k = W * deger / toplam if (W is not None and toplam > 0) else None
        satirlar.append({"dilim": k + 1, "z_alt": z0 + k * dz, "z_ust": z0 + (k + 1) * dz,
                         "bagil": b, "sigma": s, "W": w_k,
                         "q": (w_k / dz) if (w_k is not None and sinirlar) else None})
    return satirlar


def _satir(dagilim, faktorler, anahtar, kayit, cubuk_W, yukseklik):
    turler = faktorler.get("kafes_turleri")
    ort = faktorler["ortalama_cubuk"]
    if anahtar in faktorler["bagil"]:
        bagil, sigma = faktorler["bagil"][anahtar]
    else:                                  # kesik cubuk: ayni payda
        bagil, sigma = kayit["toplam"][0] / ort, kayit["toplam"][1] / ort
    W = bagil * cubuk_W if cubuk_W is not None else None
    n = dagilim.get("eksenel_dilim") or 1
    dilimler = (_dilim_satirlari(kayit, faktorler, anahtar, W, dagilim.get("eksenel_sinirlar"), n)
                if n > 1 else [])
    q = W / yukseklik if (W is not None and yukseklik) else None
    tepe = [d["q"] for d in dilimler if d["q"] is not None]
    x, y = _guc.cubuk_merkezi(dagilim, anahtar)
    return {
        "anahtar": anahtar,
        "demet": _demet_metni(dagilim, anahtar, turler),
        "konum": _cubuk_metni(anahtar, dagilim, turler),
        "x": x, "y": y,
        "tur": ((dagilim.get("cubuk_turleri") or {}).get(anahtar) or ""),
        "kesik": anahtar in set(faktorler.get("kesik_cubuklar") or ()),
        "sicak": anahtar == faktorler.get("sicak_cubuk"),
        "bagil": bagil, "sigma": sigma,
        "W": W, "W_sigma": sigma * cubuk_W if cubuk_W is not None else None,
        "q": q,
        "dilimler": dilimler,
        "tepe_q": max(tepe) if tepe else q,
    }


def pin_tablosu(dagilim, faktorler, mutlak=None, yukseklik=None):
    """
    Pin gucu tablosu (satir sozlukleri listesi, dagilim konum sirasiyla).
    dagilim: guc.dagilim_oku; faktorler: guc.tepe_faktorleri;
    mutlak: guc.mutlak_guc (yoksa W/q′ None); yukseklik: aktif yukseklik [cm]
    (lineer guc paydasi; mutlak_guc'a verilenle ayni olmali).
    """
    if not dagilim or not faktorler:
        return []
    cubuk_W = (mutlak or {}).get("cubuk_ortalama_W")
    return [_satir(dagilim, faktorler, a, k, cubuk_W, yukseklik)
            for a, k in dagilim["konumlar"].items()]


def satir_bul(tablo, anahtar):
    """Anahtarin satiri; yoksa None."""
    for r in tablo:
        if r["anahtar"] == anahtar:
            return r
    return None


def tablo_toplami(tablo):
    """Σ W (kesikler dahil) [W]; mutlak guc yoksa None."""
    if not tablo or any(r["W"] is None for r in tablo):
        return None
    return math.fsum(r["W"] for r in tablo)


def demet_ozeti(tablo):
    """
    Demet basina ozet (tam kor; tek demette tek satir): demet_anahtari, demet,
    cubuk_sayisi, ortalama (bagil), tepe (bagil), tepe_konum, W (toplam |
    None). Kesik cubuklar ortalamaya ve tepeye girmez (guc._demet_faktorleri).
    """
    gruplar = {}
    for r in tablo:
        if r["kesik"]:
            continue
        a = r["anahtar"]
        d = _guc.demet_anahtari(a) if r["demet"] else None
        gruplar.setdefault(d, []).append(r)
    ozet = []
    for d, uyeler in gruplar.items():
        tepe = max(uyeler, key=lambda r: r["bagil"])
        W = [r["W"] for r in uyeler]
        ozet.append({"demet_anahtari": d, "demet": uyeler[0]["demet"],
                     "cubuk_sayisi": len(uyeler),
                     "ortalama": sum(r["bagil"] for r in uyeler) / len(uyeler),
                     "tepe": tepe["bagil"], "tepe_konum": tepe["konum"],
                     "W": math.fsum(W) if None not in W else None})
    return ozet


# ============================================================================
# 2. CEYREK KATLAMA
# ============================================================================

def _kafes_simetrik(kafes):
    """(bool, neden): kare kafes x ve y'de ayna simetrik ve ortalanmis mi."""
    import numpy as np
    import openmc
    if not isinstance(kafes, openmc.RectLattice):
        return False, _("kare olmayan kafes (%s)") % type(kafes).__name__
    kimlik = np.vectorize(lambda u: u.id)(np.asarray(kafes.universes, dtype=object))
    if not (np.array_equal(kimlik, kimlik[..., ::-1]) and
            np.array_equal(kimlik, kimlik[..., ::-1, :])):
        return False, _("kafes %d ayna simetrik değil") % kafes.id
    adim = np.asarray(kafes.pitch, dtype=float)[:2]
    boyut = np.asarray(kafes.shape, dtype=float)[:2]
    if np.any(np.abs(np.asarray(kafes.lower_left, dtype=float)[:2] + adim * boyut / 2.0)
              > _MERKEZ_TOLERANSI):
        return False, _("kafes %d elemanında ortalanmamış") % kafes.id
    return True, ""


def _ayna(anahtar, boyutlar, eksen):
    """Anahtarin x (eksen 0) ya da y (eksen 1) aynasi; duzey basina boyutla."""
    tek = not isinstance(anahtar[0], tuple)
    parcalar = [anahtar] if tek else list(anahtar)
    yeni = []
    for p, (nx, ny) in zip(parcalar, boyutlar):
        p = list(p)
        p[eksen] = (nx if eksen == 0 else ny) - 1 - p[eksen]
        yeni.append(tuple(p))
    return yeni[0] if tek else tuple(yeni)


def _model_reddi(dagilim, spec):
    """Katlamayi geometriye bakmadan reddeden durumlar; yoksa None."""
    from cekirdek import sema
    if spec is not None and sema.agac_modu(spec):
        return _("gelişmiş (ağaç) modelde simetri doğrulanamıyor")
    if spec is not None and int(((spec.get("kor") or {}).get("tambur") or {}).get("sayi") or 0):
        return _("kontrol tamburlu kor simetrik sayılmaz")
    turler = dagilim.get("kafes_turleri") or [dagilim.get("kafes_turu")]
    if any(t != "kare" for t in turler):
        return _("çeyrek katlama yalnız kare kafeste")
    if dagilim.get("kesik_cubuklar"):
        return _("kesik çubuklu modelde katlanmaz")
    return None


def ceyrek_simetri(tablo, dagilim, spec=None):
    """(bool, neden) -- ceyrek katlama yapilabilir mi (bkz. modul basligi)."""
    red = _model_reddi(dagilim, spec)
    if red:
        return False, red
    tum = dagilim.get("tum_kafesler") or {}
    if not tum:
        return False, _("geometri kafesleri okunamadı")
    for kafes in tum.values():
        tamam, neden = _kafes_simetrik(kafes)
        if not tamam:
            return False, neden
    boyutlar = [tuple(k.shape[:2]) for k in dagilim["kafesler"]]
    turler = {r["anahtar"]: r["tur"] for r in tablo}
    for a, tur in turler.items():
        for eksen in (0, 1):
            ayna = _ayna(a, boyutlar, eksen)
            if turler.get(ayna) != tur:
                return False, _("%s konumunun aynası tabloda yok ya da farklı türde") % (
                    _guc.konum_metni(a, None, dagilim.get("kafes_turleri")))
    return True, ""


def _yorunge(a, boyutlar):
    ax = _ayna(a, boyutlar, 0)
    return sorted({a, ax, _ayna(a, boyutlar, 1), _ayna(ax, boyutlar, 1)}, key=repr)


def _katli_satir(uyeler):
    m = len(uyeler)
    ort = sum(u["bagil"] for u in uyeler) / m
    W = [u["W"] for u in uyeler]
    q = [u["q"] for u in uyeler]
    temsilci = max(uyeler, key=lambda u: (u["x"], u["y"]))      # sag ust ceyrek
    return dict(temsilci, uyeler=[u["anahtar"] for u in uyeler], bagil=ort,
                sigma=math.sqrt(sum(u["sigma"] ** 2 for u in uyeler)) / m,
                W=(sum(W) / m) if None not in W else None,
                q=(sum(q) / m) if None not in q else None,
                sicak=any(u["sicak"] for u in uyeler),
                asimetri=(max(abs(u["bagil"] - ort) for u in uyeler) / ort) if ort else 0.0,
                dilimler=[], tepe_q=None)


def ceyrek_katla(tablo, dagilim, spec=None):
    """
    (katli tablo | None, neden). Katli satir: temsilci (sag ust ceyrek)
    konumuyla, "uyeler" [anahtar], yorunge ortalamasi bagil/W/q, σ = √Σσ² / m,
    "asimetri". Dilim ayrintisi katlanmaz (bos). Simetri yoksa (None, neden).
    """
    tamam, neden = ceyrek_simetri(tablo, dagilim, spec)
    if not tamam:
        return None, neden
    boyutlar = [tuple(k.shape[:2]) for k in dagilim["kafesler"]]
    satirlar = {r["anahtar"]: r for r in tablo}
    goruldu, katli = set(), []
    for r in tablo:
        if r["anahtar"] in goruldu:
            continue
        yorunge = _yorunge(r["anahtar"], boyutlar)
        goruldu.update(yorunge)
        katli.append(_katli_satir([satirlar[a] for a in yorunge]))
    return katli, ""


# ============================================================================
# 3. DISA AKTARMA (CSV her zaman; Excel yalniz openpyxl kuruluysa)
# ============================================================================

def _sayi(x):
    return "" if x is None else repr(float(x))


def basliklar(tablo):
    """Disa aktarma sutun basliklari (dilim sayisina gore)."""
    n = max((len(r["dilimler"]) for r in tablo), default=0)
    temel = [_("demet"), _("konum"), "x [cm]", "y [cm]", _("tür"), _("kesik"), _("sıcak"),
             _("bağıl güç"), "σ", "W", "σ(W)", "q′ [W/cm]"]
    return temel + ["q′_%d [W/cm]" % (k + 1) for k in range(n)] + \
        [_("bağıl_%d") % (k + 1) for k in range(n)]


def _hucreler(r, n):
    dq = [d["q"] for d in r["dilimler"]] + [None] * (n - len(r["dilimler"]))
    db = [d["bagil"] for d in r["dilimler"]] + [None] * (n - len(r["dilimler"]))
    return ([r["demet"], r["konum"], r["x"], r["y"], r["tur"], int(r["kesik"]), int(r["sicak"]),
             r["bagil"], r["sigma"], r["W"], r["W_sigma"], r["q"]] + dq + db)


def satirlar(tablo):
    """Baslik + veri satirlari (sayilar float / None)."""
    n = max((len(r["dilimler"]) for r in tablo), default=0)
    return [basliklar(tablo)] + [_hucreler(r, n) for r in tablo]


def csv_metni(tablo):
    """Pin tablosu CSV'si: alan ayirici virgul, ondalik NOKTA, repr hassasiyeti."""
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    hepsi = satirlar(tablo)
    yazici.writerow(hepsi[0])
    for s in hepsi[1:]:
        yazici.writerow([_sayi(h) if isinstance(h, float) else ("" if h is None else h)
                         for h in s])
    return tampon.getvalue()


def excel_var():
    """openpyxl kurulu mu (yeni bagimlilik eklenmez; varsa kullanilir)."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return False
    return True


def excel_yaz(tablo_satirlari, yol, sayfa_adi=None):
    """
    Satirlari (satirlar() ya da baslik + satir listesi) .xlsx'e yazar; tablo
    sozlukleri verilirse satirlar() ile cevrilir. openpyxl yoksa ImportError.
    """
    import openpyxl
    veri = (satirlar(tablo_satirlari) if tablo_satirlari and isinstance(tablo_satirlari[0], dict)
            else tablo_satirlari)
    kitap = openpyxl.Workbook()
    sayfa = kitap.active
    sayfa.title = sayfa_adi or _("pin gücü")
    for s in veri:
        sayfa.append(list(s))
    kitap.save(yol)
    return yol
