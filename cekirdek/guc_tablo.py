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
from collections.abc import Mapping

from cekirdek import guc as _guc
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)



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


def _satir(dagilim, faktorler, anahtar, kayit, cubuk_W, yukseklik, kesikler):
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
        "kesik": anahtar in kesikler,
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
    kesikler = set(faktorler.get("kesik_cubuklar") or ())
    return _tepe_isaretle([_satir(dagilim, faktorler, a, k, cubuk_W, yukseklik, kesikler)
                           for a, k in dagilim["konumlar"].items()])


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
# 2. CEYREK KATLAMA -- cekirdek/guc_katlama.py (adlar buradan da erisilir)
# ============================================================================

from cekirdek.guc_katlama import ceyrek_katla, ceyrek_simetri  # noqa: E402,F401
from cekirdek.guc_katlama import _tepe_isaretle  # noqa: E402


# ============================================================================
# 3. DISA AKTARMA (CSV her zaman; Excel yalniz openpyxl kuruluysa)
# ============================================================================

def _sayi(x):
    return "" if x is None else repr(float(x))


# Dosya sutun ANAHTARLARI sabittir (cevrilmez): CSV/Excel'i okuyan betikler dilden
# bagimsiz calissin. Ekrandaki basliklar arayuzde cevrilir.
_TEMEL_SUTUNLAR = ("demet", "konum", "x_cm", "y_cm", "tur", "kesik", "sicak", "tepe_yakini",
                   "bagil", "sigma")
# Formul enjeksiyonu: elektronik tablo bu karakterlerle baslayan metni formul sayar.
_FORMUL_BASLARI = ("=", "+", "-", "@", "\t", "\r")


def hucre_guvenli(h):
    """Metin hucresi formul gibi baslarsa ' oneki (CSV/Excel enjeksiyonu); diger aynen."""
    if isinstance(h, str) and h.startswith(_FORMUL_BASLARI):
        return "'" + h
    return h


def basliklar(tablo, iki_boyut=False):
    """Disa aktarma sutun anahtarlari (dilim sayisina ve katlamaya gore).
    iki_boyut: 2B tukenmede guc 1 cm yukseklik basinadir -> "W_per_cm"."""
    n = max((len(r["dilimler"]) for r in tablo), default=0)
    w = "W_per_cm" if iki_boyut else "W"
    temel = list(_TEMEL_SUTUNLAR) + [w, w + "_sigma", "q_W_cm"]
    if any(r.get("uyeler") for r in tablo):
        temel += ["katlanan_m", "asimetri", "asimetri_sigma"]
    return temel + ["q_W_cm_%d" % (k + 1) for k in range(n)] + \
        ["bagil_%d" % (k + 1) for k in range(n)]


def _hucreler(r, n, katli):
    d = list(r["dilimler"])
    dq = [x["q"] for x in d] + [None] * (n - len(d))
    db = [x["bagil"] for x in d] + [None] * (n - len(d))
    ek = [len(r.get("uyeler") or ()), r.get("asimetri"), r.get("asimetri_sigma")] if katli else []
    return ([r["demet"], r["konum"], r["x"], r["y"], r["tur"], int(r["kesik"]), int(r["sicak"]),
             int(bool(r.get("tepe_yakini"))), r["bagil"], r["sigma"], r["W"], r["W_sigma"],
             r["q"]] + ek + dq + db)


def satirlar(tablo, iki_boyut=False):
    """Baslik + veri satirlari (sayilar float / None)."""
    n = max((len(r["dilimler"]) for r in tablo), default=0)
    katli = any(r.get("uyeler") for r in tablo)
    return [basliklar(tablo, iki_boyut)] + [_hucreler(r, n, katli) for r in tablo]


def satirlar_csv(veri):
    """Baslik + satirlar -> CSV metni: alan ayirici virgul, ondalik NOKTA,
    sayilar repr() hassasiyetinde (yerel ayardan bagimsiz), None bos, metin
    hucreleri formul enjeksiyonuna karsi korunur (hucre_guvenli)."""
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    for s in veri:
        yazici.writerow([_sayi(h) if isinstance(h, float) else
                         ("" if h is None else hucre_guvenli(h)) for h in s])
    return tampon.getvalue()


def csv_metni(tablo):
    """Pin tablosu CSV'si (satirlar_csv bicimi)."""
    return satirlar_csv(satirlar(tablo))


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
    veri = (satirlar(tablo_satirlari) if tablo_satirlari
            and isinstance(tablo_satirlari[0], Mapping) else tablo_satirlari)
    kitap = openpyxl.Workbook()
    sayfa = kitap.active
    sayfa.title = sayfa_adi or "pin_gucu"
    for i, s in enumerate(veri, 1):
        for j, h in enumerate(s, 1):
            hucre = sayfa.cell(row=i, column=j, value=hucre_guvenli(h))
            if isinstance(h, str):
                hucre.data_type = "s"          # metin: formul olarak yorumlanmaz
    kitap.save(yol)
    return yol


def dosyaya_yaz(yol, veri, sayfa_adi=None):
    """Baslik + satirlari uzantiya gore yazar: .xlsx -> Excel (openpyxl
    gerekir), diger -> CSV (UTF-8). DONER yol."""
    if yol.lower().endswith(".xlsx"):
        return excel_yaz(veri, yol, sayfa_adi)
    # utf-8-sig: Excel/LibreOffice Turkce karakterleri BOM ile dogru tanir
    with open(yol, "w", encoding="utf-8-sig", newline="") as f:
        f.write(satirlar_csv(veri))
    return yol
