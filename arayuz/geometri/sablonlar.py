# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/sablonlar.py  --  Uc yeni duzenek sablonu (§10; SAF islevler)
================================================================================
 Mevcut 7 kor turu (kor.tur) sihirbaz alanlariyla kalir. Bu uc duzenek icin
 kor.tur YOKTUR: sablon, formdaki olculerden dogrudan bir AGAC uretir ve model
 gelismis moda gecer (tek geri al adimi; §15 karar 1).

   kare_altigen   Kare cekirdek + altigen halka     (§4.1 hedef a)
   altigen_tambur Altigen cekirdek + tambur halkasi (§4.2 hedef b)
   kafes_tambur   Kafesli cekirdek + tamburlu yansitici (§4.3 hedef c)

 varsayilanlar(spec, anahtar) -> {alan: deger}; uret(spec, anahtar, p) -> YENI
 spec (girdi degismez). Eksik parca (kare/altigen demet) SablonHatasi verir;
 mesaj kullaniciya gosterilir. Olcu kurallari belgedeki orneklerle aynidir:
   kafes zarfi apotemi (n-1) P sqrt3/2 + P/sqrt3 (kesit.kafes_zarfi_apotemi);
   altigen blok prizmasi ters(kafes yonelimi), apotem P/2 - aralik;
   altigen demet pin 'y' -> kor 'x' (90 derece kurali).
================================================================================
"""

import copy
import math

from cekirdek.ceviri import N_, _
from cekirdek.geometri.kesit import kafes_zarfi_apotemi, ters_yonelim
from arayuz.geometri.cizim import altigen_koseleri, kafes_konumlari

SQ3 = math.sqrt(3.0)
YENI_SABLONLAR = {
    "kare_altigen": N_("Kare çekirdek + altıgen halka"),
    "altigen_tambur": N_("Altıgen çekirdek + tambur halkası"),
    "kafes_tambur": N_("Kafesli çekirdek + tamburlu yansıtıcı"),
}
YANSITICI_BLOK = "__yansitici_blok__"
_YAPI_ADAYLARI = ("ss304", "ss316", "celik", "ht9", "zirkaloy4", "zr1nb", "al6061")
_YANSITICI_ADAYLARI = ("berilyum", "grafit", "su", "sodyum", "celik", "ss316", "ss304")
_EMICI_ADAYLARI = ("b4c", "bor", "hafniyum")


class SablonHatasi(ValueError):
    """Sablon bu modelle kurulamaz (mesaj kullaniciya)."""


def _malzemeler(spec):
    return [m["ad"] for m in spec.get("malzemeler") or []]


def _aday(spec, adaylar, yedek_son=True):
    adlar = _malzemeler(spec)
    for a in adaylar:
        for m in adlar:
            if m == a or m.startswith(a):
                return m
    if not adlar:
        return "bosluk"
    return adlar[-1] if yedek_son else adlar[0]


def _demetler(spec, tur):
    return [d for d in spec.get("demetler") or [] if d.get("tur", "kare") == tur]


def _demet_olcusu(d):
    """Demetin dis olcusu: kare P*nx; altigen duz-duz ((n-1) sqrt3 + 1) p."""
    if d.get("tur", "kare") == "kare":
        return float(d["adim"]) * int((d.get("boyut") or [1])[0])
    n = int(d.get("halka_sayisi") or 1)
    return ((n - 1) * SQ3 + 1.0) * float(d["adim"])


def _tambur_tanimi(spec, p):
    return {"ad": p["tambur_adi"], "yaricap": p["tambur_yaricap"],
            "govde_malzeme": p["tambur_govde"], "emici_malzeme": p["tambur_emici"],
            "emici_ic_yaricap": p["tambur_emici_ic"], "emici_aci": p["tambur_emici_aci"]}


def _tambur_varsayilanlari(spec, yaricap, govde):
    mevcut = next(iter(spec.get("tamburlar") or []), None)
    if mevcut:
        return {"tambur_adi": mevcut["ad"], "tambur_yaricap": float(mevcut.get("yaricap") or yaricap),
                "tambur_govde": mevcut.get("govde_malzeme") or govde,
                "tambur_emici": mevcut.get("emici_malzeme") or _aday(spec, _EMICI_ADAYLARI),
                "tambur_emici_ic": float(mevcut.get("emici_ic_yaricap") or 0.75 * yaricap),
                "tambur_emici_aci": float(mevcut.get("emici_aci") or 120.0)}
    return {"tambur_adi": "tambur_b4c", "tambur_yaricap": yaricap, "tambur_govde": govde,
            "tambur_emici": _aday(spec, _EMICI_ADAYLARI), "tambur_emici_ic": 0.75 * yaricap,
            "tambur_emici_aci": 120.0}


# ============================================================================
# varsayilanlar
# ============================================================================

def varsayilanlar(spec, anahtar):
    """Sablon formunun baslangic degerleri (modelin parcalarindan)."""
    if anahtar == "kare_altigen":
        kare = _demetler(spec, "kare")
        a = kare[0]["ad"] if kare else None
        b = kare[1]["ad"] if len(kare) > 1 else a
        P = _demet_olcusu(kare[0]) if kare else 21.42
        return {"demet_a": a, "demet_b": b, "n": 5, "adim": P, "blok_adim": 30.0,
                "blok_halka": 5, "blok_icerik": YANSITICI_BLOK,
                "blok_malzeme": _aday(spec, _YAPI_ADAYLARI), "kanal_yaricap": 3.0,
                "dolgu": _aday(spec, ("su", "sodyum", "helyum"), yedek_son=False),
                "yansitici_kalinlik": 20.0,
                "yansitici_malzeme": _aday(spec, ("su", "sodyum", "grafit")),
                "yukseklik": None}
    if anahtar == "altigen_tambur":
        hex_ = _demetler(spec, "altigen")
        d = hex_[0] if hex_ else None
        P = round(_demet_olcusu(d) + 0.01, 4) if d else 10.26
        zarf = kafes_zarfi_apotemi(3, P)
        yans = _aday(spec, ("celik", "ss316", "ss304", "ht9", "berilyum"))
        p = {"demet": d["ad"] if d else None, "halka": 3, "adim": P,
             "yonelim": ters_yonelim((d or {}).get("yonelim", "y")),
             "dis_dolgu": "bosluk", "yansitici_apotem": round(zarf + 25.0, 2),
             "yansitici_malzeme": yans, "tambur_sayi": 6,
             "tambur_merkez": round(zarf + 12.3, 2), "tambur_baslangic": 30.0,
             "donme": 180.0, "yukseklik": 80.0}
        p.update(_tambur_varsayilanlari(spec, 6.0, yans))
        return p
    if anahtar == "kafes_tambur":
        kare = _demetler(spec, "kare")
        a = kare[0]["ad"] if kare else None
        b = kare[1]["ad"] if len(kare) > 1 else a
        P = _demet_olcusu(kare[0]) if kare else 21.42
        yans = _aday(spec, _YANSITICI_ADAYLARI, yedek_son=False)
        p = {"demet_a": a, "demet_b": b, "n": 3, "adim": P, "yansitici_yaricap": 80.0,
             "yansitici_malzeme": yans, "tambur_sayi": 4, "tambur_merkez": 60.0,
             "tambur_baslangic": 45.0, "donme": 180.0, "yukseklik": 200.0}
        p.update(_tambur_varsayilanlari(spec, 8.0, yans))
        return p
    raise SablonHatasi(_("Bilinmeyen şablon: {a}").format(a=anahtar))


# ============================================================================
# uretim
# ============================================================================

def _dama(n, a, b):
    """n x n dama tahtasi haritasi (kose b)."""
    return ["".join("B" if (r + i) % 2 == 0 else "A" for i in range(n)) for r in range(n)], \
        {"A": {"tur": "bilesen", "ad": a}, "B": {"tur": "bilesen", "ad": b}}


def _sinir(yukseklik):
    return ({"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"} if yukseklik
            else {"yan": "vacuum"})


def _yeni_spec(spec, geometri, tamburlar=()):
    yeni = copy.deepcopy(spec)
    yeni["kor"] = {"tur": "agac"}
    mevcut = {t.get("ad") for t in yeni.get("tamburlar") or []}
    yeni["tamburlar"] = list(yeni.get("tamburlar") or []) + [
        copy.deepcopy(t) for t in tamburlar if t["ad"] not in mevcut]
    yeni["geometri"] = geometri
    return yeni


def _gizli_harita(kafes, yari):
    """Kare delik (yari kenar) altinda TAMAMEN kalan konumlar '.', digerleri 'B'."""
    P = float(kafes["adim"])
    n = int(kafes["halka_sayisi"])
    harita = [["B"] * (1 if r == n - 1 else 6 * (n - 1 - r)) for r in range(n)]
    for (r, i), (x, y) in kafes_konumlari("altigen", P, [], None, n, kafes["yonelim"]):
        koseler = altigen_koseleri(P / 2.0, ters_yonelim(kafes["yonelim"]), (x, y))
        if all(abs(kx) <= yari and abs(ky) <= yari for kx, ky in koseler):
            harita[r][i] = "."
    return ["".join(s) for s in harita]


def _kare_altigen(spec, p):
    if not p.get("demet_a"):
        raise SablonHatasi(_("Bu şablon için bir kare demet gerekli (Demet sayfasında "
                             "kare demet tanımlayın)."))
    harita, anahtar = _dama(int(p["n"]), p["demet_a"], p["demet_b"] or p["demet_a"])
    kenar = float(p["adim"]) * int(p["n"])
    cekirdek = {"tur": "kafes", "id": "cekirdek_kafesi", "sekil": "kare",
                "adim": float(p["adim"]), "boyut": [int(p["n"])] * 2, "harita": harita,
                "anahtar": anahtar, "dis": {"tur": "malzeme", "ad": p["dolgu"]}}
    parcalar = []
    if p["blok_icerik"] == YANSITICI_BLOK:
        blok = {"tur": "kap", "id": "blok",
                "kesit": {"sekil": "altigen", "yonelim": "y",
                          "apotem": round(float(p["blok_adim"]) / 2.0 - 0.2, 6)},
                "ic": {"tur": "malzeme", "ad": p["blok_malzeme"]},
                "yerlesimler": [], "halkalar": [], "dis": {"tur": "malzeme", "ad": p["dolgu"]}}
        if float(p.get("kanal_yaricap") or 0) > 0:
            blok["yerlesimler"].append(
                {"ad": "blok_kanali", "mod": "liste", "konumlar": [[0.0, 0.0]],
                 "kesit": {"sekil": "silindir", "yaricap": float(p["kanal_yaricap"])},
                 "icerik": {"tur": "malzeme", "ad": p["dolgu"]}})
        parcalar.append({"ad": "yansitici_blok", "dugum": blok})
        blok_icerik = {"tur": "bilesen", "ad": "yansitici_blok"}
    else:
        blok_icerik = {"tur": "bilesen", "ad": p["blok_icerik"]}
    bloklar = {"tur": "kafes", "id": "blok_kafesi", "sekil": "altigen",
               "adim": float(p["blok_adim"]), "halka_sayisi": int(p["blok_halka"]),
               "yonelim": "x", "anahtar": {"B": blok_icerik},
               "dis": {"tur": "malzeme", "ad": p["dolgu"]}}
    bloklar["harita"] = _gizli_harita(bloklar, kenar / 2.0)
    kok = {"tur": "kap", "id": "kok",
           "kesit": {"sekil": "altigen", "yonelim": "x",
                     "apotem": round(kafes_zarfi_apotemi(int(p["blok_halka"]),
                                                         float(p["blok_adim"])), 6)},
           "ic": bloklar,
           "yerlesimler": [{"ad": "kare_cekirdek", "mod": "liste", "konumlar": [[0.0, 0.0]],
                            "kesit": {"sekil": "dikdortgen", "boyut": [kenar, kenar]},
                            "icerik": cekirdek}],
           "halkalar": [], "yukseklik": p.get("yukseklik"), "sinir": _sinir(p.get("yukseklik"))}
    if float(p.get("yansitici_kalinlik") or 0) > 0:
        kok["halkalar"].append({"kalinlik": float(p["yansitici_kalinlik"]),
                                "icerik": {"tur": "malzeme", "ad": p["yansitici_malzeme"]},
                                "yerlesimler": []})
    return _yeni_spec(spec, {"kok": kok, "parcalar": parcalar, "gruplar": []})


def _tambur_yerlesimi(p, ad):
    return {"ad": ad, "mod": "halka", "sayi": int(p["tambur_sayi"]),
            "merkez_yaricap": float(p["tambur_merkez"]),
            "baslangic_acisi": float(p["tambur_baslangic"]),
            "icerik": {"tur": "bilesen", "ad": p["tambur_adi"]}, "kesit": None,
            "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}


def _gruplar(p, ad):
    if int(p["tambur_sayi"]) <= 0:
        return []
    return [{"ad": "tamburlar", "tur": "donme", "deger": float(p["donme"]), "uyeler": [ad]}]


def _altigen_tambur(spec, p):
    if not p.get("demet"):
        raise SablonHatasi(_("Bu şablon için bir altıgen demet gerekli (Demet sayfasında "
                             "altıgen demet tanımlayın)."))
    n = int(p["halka"])
    harita = ["D" * (1 if r == n - 1 else 6 * (n - 1 - r)) for r in range(n)]
    halka = {"dis": {"sekil": "altigen", "yonelim": p["yonelim"],
                     "apotem": float(p["yansitici_apotem"])},
             "icerik": {"tur": "malzeme", "ad": p["yansitici_malzeme"]}, "yerlesimler": []}
    if int(p["tambur_sayi"]) > 0:
        halka["yerlesimler"].append(_tambur_yerlesimi(p, "tambur_halkasi"))
    kok = {"tur": "kap", "id": "kok", "kesit": {"sekil": "kafes_zarfi"},
           "ic": {"tur": "kafes", "id": "kor_kafesi", "sekil": "altigen",
                  "adim": float(p["adim"]), "halka_sayisi": n, "yonelim": p["yonelim"],
                  "harita": harita, "anahtar": {"D": {"tur": "bilesen", "ad": p["demet"]}},
                  "dis": {"tur": "malzeme", "ad": p.get("dis_dolgu") or "bosluk"}},
           "yerlesimler": [], "halkalar": [halka], "yukseklik": p.get("yukseklik"),
           "sinir": _sinir(p.get("yukseklik"))}
    tamburlar = [_tambur_tanimi(spec, p)] if int(p["tambur_sayi"]) > 0 else []
    return _yeni_spec(spec, {"kok": kok, "parcalar": [],
                             "gruplar": _gruplar(p, "tambur_halkasi")}, tamburlar)


def _kafes_tambur(spec, p):
    if not p.get("demet_a"):
        raise SablonHatasi(_("Bu şablon için bir kare demet gerekli (Demet sayfasında "
                             "kare demet tanımlayın)."))
    n = int(p["n"])
    harita, anahtar = _dama(n, p["demet_a"], p["demet_b"] or p["demet_a"])
    kenar = float(p["adim"]) * n
    halka = {"dis": {"sekil": "silindir", "yaricap": float(p["yansitici_yaricap"])},
             "icerik": {"tur": "malzeme", "ad": p["yansitici_malzeme"]}, "yerlesimler": []}
    if int(p["tambur_sayi"]) > 0:
        halka["yerlesimler"].append(_tambur_yerlesimi(p, "tamburlar_yansitici"))
    kok = {"tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [kenar, kenar]},
           "ic": {"tur": "kafes", "id": "kor_kafesi", "sekil": "kare", "adim": float(p["adim"]),
                  "boyut": [n, n], "harita": harita, "anahtar": anahtar,
                  "dis": {"tur": "malzeme", "ad": p["yansitici_malzeme"]}},
           "yerlesimler": [], "halkalar": [halka], "yukseklik": p.get("yukseklik"),
           "sinir": _sinir(p.get("yukseklik"))}
    tamburlar = [_tambur_tanimi(spec, p)] if int(p["tambur_sayi"]) > 0 else []
    return _yeni_spec(spec, {"kok": kok, "parcalar": [],
                             "gruplar": _gruplar(p, "tamburlar_yansitici")}, tamburlar)


_URETICILER = {"kare_altigen": _kare_altigen, "altigen_tambur": _altigen_tambur,
               "kafes_tambur": _kafes_tambur}


def uret(spec, anahtar, parametreler=None):
    """Sablondan YENI spec (gelismis mod). Girdi degismez."""
    if anahtar not in _URETICILER:
        raise SablonHatasi(_("Bilinmeyen şablon: {a}").format(a=anahtar))
    p = varsayilanlar(spec, anahtar)
    p.update(parametreler or {})
    return _URETICILER[anahtar](spec, p)
