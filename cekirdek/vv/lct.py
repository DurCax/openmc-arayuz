# -*- coding: utf-8 -*-
"""
vv/lct.py -- LEU oksit kafes V&V vakalari (v3 Y11): TCA (LEU-COMP-THERM-006).

KAYNAK (kamuya acik, yeniden uretilebilir)
  Model: H. Tsuruta vd., "Critical Sizes of Light-Water Moderated UO2 and
  PuO2-UO2 Lattices", JAERI 1254 (1978), JAEA acik arsiv
  https://jopss.jaea.go.jp/pdfdata/JAERI-1254.pdf -- Tablo 1 (yakit), Sekil 3-4
  (cubuk, tank), Tablo 2 (adim), Tablo 8-1 (20 C kritik su seviyesi), Ek A1
  (atom yogunluklari), Ek A3 (desenler).
  Durum eslemesi: K. Okumura, T. Mori, JAERI-Conf 2003-006 Tablo 1
  (OSTI ETDEWEB 20435859): LCT-006 durum 1-3 = 1.50U 19x19..21x21,
  4-8 = 1.83U 17x17..21x21, 9-13 = 2.48U 16x16..20x20, 14-18 = 3.00U 15x15..19x19.
  E +- sigma: ICSBEP degerlendirmesi 1.0000 +- 0.0020 (butun 18 durum), yayimlanmis
  hali S.C. van der Marck, Nucl. Data Sheets 107 (2006) 3061, Tablo IX.

BU MODEL ICSBEP BASITLESTIRILMIS MODELI DEGILDIR. ICSBEP el kitabi metni kullanilmadi
(STANDARTLAR.md §6 md. 13); model birincil deney raporundan kurulur ve
basitlestirmeleri (TCA_BASITLESTIRMELERI) referans alaninda yazilir. Basitlestirme
yanliligi docs/VV.md'de duyarlilik kosusuyla olculur.

  TCA_DURUMLARI                 -> (TcaDurumu, ...)  18 durum
  tca_durumu(no)                -> TcaDurumu (bilinmeyen no: ValueError)
  tca_birim_hucre(adim)         -> BirimHucre (Vsu/Vyakit, H/U, H/U-235)
  tca_spec(no, varyant=None)    -> YENI spec sozlugu (gelismis/agac modu)
"""

import copy
import math
from dataclasses import dataclass
from typing import Optional

from cekirdek.ceviri import _

SERI_TCA = "LEU-COMP-THERM-006"
E_TCA, SIGMA_ICSBEP_TCA = 1.0000, 0.0020  # van der Marck (2006) Tablo IX
# Bu modelin (ICSBEP modeli degil) basitlestirme belirsizligi: U-234 icerigi JAERI 1254'te
# yok; "u234" varyanti durum 1 ve 14'te k'yi -143 ve -187 pcm degistirdi (docs/VV.md,
# 02.10.2026; sigma_c ~ 36 pcm). Ortalama 165 pcm 1σ kabul edilir (muhafazakar: etkinin
# tamami). "alt_tapa" etkisi (-12, -24 pcm) istatistik icinde, eklenmedi.
SIGMA_BASIT_TCA = 0.00165
SIGMA_E_TCA = round(math.hypot(SIGMA_ICSBEP_TCA, SIGMA_BASIT_TCA), 4)   # 0.0026

# JAERI 1254 Tablo 1 / Sekil 3 [cm]
TCA_YAKIT_R = 1.250 / 2.0                 # pelet capi 12.50 mm
TCA_KILIF_IC_R = 1.265 / 2.0              # kilif ic capi 12.65 mm
TCA_KILIF_DIS_R = TCA_KILIF_IC_R + 0.076  # kalinlik 0.76 mm
TCA_YAKIT_BOYU = 144.15                   # yigin boyu 1441.5 mm
TCA_ALT_TAPA = 16.83                      # Al alt uc tapasi 168.3 mm (Sekil 3)
# JAERI 1254 §2.1 / Sekil 4: tank ic capi 1832 mm; §2.3: alt yansitici 30 cm
TCA_TANK_R = 183.2 / 2.0
TCA_ALT_YANSITICI = 30.0
# Ek A1, 20 C [1e24 atom/cm3]; kilif bolgesi hava boslugu dahil (pelet - kilif dis)
N_U235, N_U238, N_O_YAKIT = 6.086e-4, 2.255e-2, 4.725e-2
N_AL_KILIF = 5.587e-2
N_H2O = 3.338e-2
SICAKLIK_K = 293.15                       # 20 C (Tablo 8-1 20 C'ye indirgenmis)
# Duyarlilik varyanti "u234": JAERI 1254 U-234 vermez; ICSBEP modeli U-234 icerir
# (van der Marck 2006 izotop listesi). Oran LCT-008 yakitindan (2.459 w/o, mit-crpg:
# 4.5689e-6 / 5.6868e-4) -- benzer zenginlikte TAHMIN, olcum degil.
U234_U235_ORANI = 4.5689e-6 / 5.6868e-4
O_DOGAL = (("O16", 0.99757), ("O17", 0.00038), ("O18", 0.00205))  # IUPAC; openmc.data

# Kosu ayari: 1.5e7 aktif oyku -> sigma_c ~ 27 pcm (proje olcutu <= 30 pcm, VV.md) << sigma_e = 200 pcm
KOSU = {"parcacik": 100000, "cevrim": 200, "pasif": 50}

TCA_BASITLESTIRMELERI = (
    "Alt yansıtıcı (30 cm) yalnız su: alt ızgara plakası, Al alt uç tapası (16.83 cm) "
    "ve yakıt destek plakası modellenmedi (varyant 'alt_tapa' ile ölçülür).",
    "Tank duvarı ve tank dışı modellenmedi: yatay su yansıtıcısı tank iç yarıçapına "
    "(91.6 cm) kadar, dışı vakum (JAERI 1254 §2.3: yatay yansıtıcı > 40 cm).",
    "Su seviyesinin üstü: kuru yakıt bölgesi boşlukta; üst ızgara, Al yünü ve üst tapa "
    "modellenmedi.",
    "Yakıtta U-234 ve safsızlıklar yok (JAERI 1254 Ek A1 yalnız U-235, U-238, O verir); "
    "kılıf saf Al, hava boşluğu kılıf bölgesine karıştırılmış (Ek A1 bölgesel yoğunluğu).",
    "Kritik su seviyesi 20 °C'ye indirgenmiş tavsiye değeridir (Tablo 8-1); bütün "
    "malzemeler 293 K.",
)


@dataclass(frozen=True)
class TcaDurumu:
    no: int
    kafes: str            # JAERI adlandirmasi: su/yakit hacim orani + U
    adim: float           # cm (Tablo 2)
    n: int                # N x N cubuk
    desen: int            # Ek A3 desen numarasi
    su_seviyesi: float    # cm, aktif yakitin alt ucundan (Tablo 8-1, 20 C)


@dataclass(frozen=True)
class BirimHucre:
    su_yakit_hacim_orani: float
    h_u: float            # H / U atom orani (Tablo 2 ile karsilastirma)
    h_x: float            # H / U-235 atom orani (AOA h_x)


def _durumlar():
    # (kafes, adim, [(n, desen, H), ...]) -- JAERI 1254 Tablo 8-1; eslesme JAERI-Conf 2003-006
    tablo = (("1.50U", 1.849, ((19, 18, 99.45), (20, 20, 73.73), (21, 22, 60.81))),
             ("1.83U", 1.956, ((17, 13, 114.59), (18, 15, 75.32), (19, 18, 60.38),
                               (20, 20, 51.65), (21, 22, 46.01))),
             ("2.48U", 2.150, ((16, 11, 78.67), (17, 13, 59.96), (18, 15, 50.52),
                               (19, 18, 44.55), (20, 20, 40.44))),
             ("3.00U", 2.293, ((15, 5, 90.75), (16, 11, 64.42), (17, 13, 52.87),
                               (18, 15, 46.06), (19, 18, 41.54))))
    sonuc, no = [], 1
    for kafes, adim, satirlar in tablo:
        for n, desen, h in satirlar:
            sonuc.append(TcaDurumu(no, kafes, adim, n, desen, h))
            no += 1
    return tuple(sonuc)


TCA_DURUMLARI = _durumlar()


def tca_durumu(no: int) -> TcaDurumu:
    for d in TCA_DURUMLARI:
        if d.no == no:
            return d
    raise ValueError(_("bilinmeyen TCA durumu: %r (1-%d)") % (no, len(TCA_DURUMLARI)))


def tca_birim_hucre(adim: float) -> BirimHucre:
    """Kare birim hucre: Vsu = p² - π r_kilif², Vyakit = π r_yakit²."""
    if adim <= 2.0 * TCA_KILIF_DIS_R:
        raise ValueError(_("adım çubuk çapından küçük: %g cm") % adim)
    v_su = adim ** 2 - math.pi * TCA_KILIF_DIS_R ** 2
    v_yakit = math.pi * TCA_YAKIT_R ** 2
    n_h = 2.0 * N_H2O * v_su
    return BirimHucre(su_yakit_hacim_orani=v_su / v_yakit,
                      h_u=n_h / ((N_U235 + N_U238) * v_yakit),
                      h_x=n_h / (N_U235 * v_yakit))


def _nuklid(isim: str, miktar: float) -> dict:
    return {"tur": "nuklid", "isim": isim, "miktar": miktar, "birim": "ao"}


def _oksijen(n_o: float) -> list:
    return [_nuklid(i, n_o * pay) for i, pay in O_DOGAL]


def _malzeme(ad: str, gorunen: str, bilesim: list, renk: list, sab: Optional[list] = None) -> dict:
    return {"ad": ad, "gorunen_ad": gorunen,
            "yogunluk": {"birim": "atom/b-cm", "deger": sum(b["miktar"] for b in bilesim)},
            "sicaklik": SICAKLIK_K, "bilesim": bilesim, "sab": list(sab or []), "renk": renk}


def _uranyum(varyant: Optional[str]) -> list:
    if varyant != "u234":
        return [_nuklid("U235", N_U235), _nuklid("U238", N_U238)]
    n_u234 = U234_U235_ORANI * N_U235          # toplam U korunur: U-238'den dusulur
    return [_nuklid("U234", n_u234), _nuklid("U235", N_U235), _nuklid("U238", N_U238 - n_u234)]


def _malzemeler(varyant: Optional[str] = None) -> list:
    return [
        _malzeme("uo2_tca", "UO2 2.596 w/o (TCA)", _uranyum(varyant) + _oksijen(N_O_YAKIT),
                 [222, 93, 40]),
        _malzeme("al_tca", "Al kılıf (hava boşluğu dahil)", [_nuklid("Al27", N_AL_KILIF)],
                 [170, 170, 180]),
        _malzeme("su_tca", "Hafif su 20 °C",
                 [_nuklid("H1", 2.0 * N_H2O)] + _oksijen(N_H2O), [60, 120, 220],
                 sab=["c_H_in_H2O"]),
    ]


def _cubuklar() -> list:
    def cubuk(ad, dis):
        return {"ad": ad, "tur": "silindirik",
                "bolgeler": [{"r": TCA_YAKIT_R, "malzeme": "uo2_tca"},
                             {"r": TCA_KILIF_DIS_R, "malzeme": "al_tca"},
                             {"r": None, "malzeme": dis}]}
    tapa = {"ad": "alt_tapa", "tur": "silindirik",
            "bolgeler": [{"r": TCA_KILIF_DIS_R, "malzeme": "al_tca"},
                         {"r": None, "malzeme": "su_tca"}]}
    return [cubuk("yakit_islak", "su_tca"), cubuk("yakit_kuru", "bosluk"), tapa]


def _kafes(kimlik: str, d: TcaDurumu, cubuk: str, dis: str) -> dict:
    return {"tur": "kafes", "id": kimlik, "sekil": "kare", "adim": d.adim,
            "boyut": [d.n, d.n], "harita": ["y" * d.n] * d.n,
            "anahtar": {"y": {"tur": "bilesen", "ad": cubuk}},
            "dis": {"tur": "malzeme", "ad": dis}}


def _alt_katmanlar(d: TcaDurumu, varyant: Optional[str]) -> list:
    su = {"tur": "malzeme", "ad": "su_tca"}
    if varyant == "alt_tapa":
        return [{"ad": "alt su", "yukseklik": TCA_ALT_YANSITICI - TCA_ALT_TAPA, "icerik": su},
                {"ad": "alt tapa", "yukseklik": TCA_ALT_TAPA,
                 "icerik": _kafes("tapa_kafesi", d, "alt_tapa", "su_tca")}]
    return [{"ad": "alt su", "yukseklik": TCA_ALT_YANSITICI, "icerik": su}]


def _geometri(d: TcaDurumu, varyant: Optional[str]) -> dict:
    katmanlar = _alt_katmanlar(d, varyant) + [
        {"ad": "ıslak yakıt", "yukseklik": d.su_seviyesi, "icerik": None},
        {"ad": "kuru yakıt", "yukseklik": round(TCA_YAKIT_BOYU - d.su_seviyesi, 6),
         "icerik": _kafes("kuru_kafes", d, "yakit_kuru", "bosluk")}]
    yigin = {"tur": "eksenel", "id": "tca_eksen",
             "icerik": _kafes("islak_kafes", d, "yakit_islak", "su_tca"),
             "katmanlar": katmanlar}
    kok = {"tur": "kap", "id": "kok", "kesit": {"sekil": "silindir", "yaricap": TCA_TANK_R},
           "ic": yigin, "yerlesimler": [], "halkalar": [], "yukseklik": None,
           "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}}
    return {"kok": kok, "parcalar": [], "gruplar": []}


def _ayarlar(d: TcaDurumu) -> dict:
    from cekirdek import sema
    a = copy.deepcopy(sema.yeni_spec()["ayarlar"])
    a.update(KOSU)
    yari = d.n * d.adim / 2.0
    z_alt = -(TCA_ALT_YANSITICI + TCA_YAKIT_BOYU) / 2.0 + TCA_ALT_YANSITICI
    a["kaynak"] = dict(a["kaynak"], tur="kutu", alt=[-yari, -yari, z_alt],
                       ust=[yari, yari, z_alt + d.su_seviyesi])
    return a


VARYANTLAR = (None, "alt_tapa", "u234")


def tca_spec(no: int, varyant: Optional[str] = None) -> dict:
    """LCT-006 durum no -> YENI spec (gelismis mod). varyant: None (temel model)
    "alt_tapa" (duyarlilik: Al alt uc tapalari alt yansiticida) ya da "u234"
    (duyarlilik: tahmini U-234, U234_U235_ORANI)."""
    from cekirdek import sema
    from cekirdek.vv import aoa
    if varyant not in VARYANTLAR:
        raise ValueError(_("bilinmeyen TCA varyantı: %r") % (varyant,))
    d = tca_durumu(no)
    hucre = tca_birim_hucre(d.adim)
    ad = "%s, durum %d (TCA %s, %dx%d)" % (SERI_TCA, d.no, d.kafes, d.n, d.n)
    spec = sema.yeni_spec(ad)
    spec.update(malzemeler=_malzemeler(varyant), cubuklar=_cubuklar(), kor={"tur": "agac"},
                geometri=_geometri(d, varyant), tamburlar=[], ayarlar=_ayarlar(d),
                tallyler=[aoa.ealf_tally_tanimi()], kategori="kriter", seviye="ileri")
    spec["baslik"] = "%s — TCA %s, %d×%d kafes, H = %.2f cm" % (ad, d.kafes, d.n, d.n,
                                                                d.su_seviyesi)
    spec["baslik_en"] = "%s, case %d (TCA %s, %dx%d; ICSBEP benchmark, V&V set)" % (
        SERI_TCA, d.no, d.kafes, d.n, d.n)
    spec["aciklama"] = _aciklama(d, hucre)
    spec["aciklama_en"] = (
        "TCA critical lattice (JAERI): %dx%d 2.6 w/o UO2 rods, pitch %.3f cm, critical water "
        "level %.2f cm at 20 C. Model built from the public primary report JAERI 1254 "
        "(not the ICSBEP simplified model); benchmark k = %.4f ± %.4f (ICSBEP ± 0.0020 as "
        "published by van der Marck 2006, combined with this model's simplification "
        "uncertainty, mainly the missing U-234)." % (d.n, d.n, d.adim, d.su_seviyesi, E_TCA, SIGMA_E_TCA))
    spec["referans"] = _referans(d, hucre, varyant)
    return spec


def _aciklama(d: TcaDurumu, hucre: BirimHucre) -> str:
    return ("ICSBEP kriteri %s durum %d: TCA (JAERI) %s kafesi, %d×%d %%2.596 UO2 çubuğu, "
            "Al kılıf, kare adım %.3f cm (Vsu/Vyakıt = %.2f, H/U = %.2f), 20 °C kritik su "
            "seviyesi %.2f cm. Deneysel kriter değeri k = %.4f ± %.4f.\nModel birincil "
            "rapordan (JAERI 1254, JAEA açık arşiv) kurulmuştur; ICSBEP basitleştirilmiş "
            "modeli DEĞİLDİR. Basitleştirmeler:\n- %s"
            % (SERI_TCA, d.no, d.kafes, d.n, d.n, d.adim, hucre.su_yakit_hacim_orani,
               hucre.h_u, d.su_seviyesi, E_TCA, SIGMA_E_TCA, "\n- ".join(TCA_BASITLESTIRMELERI)))


def _referans(d: TcaDurumu, hucre: BirimHucre, varyant: Optional[str]) -> dict:
    """ornek_bilgi meta sozlesmesinin referans alanlari (bilinmeyen alan yok);
    kaynaklar metinde, basitlestirmeler aciklamada."""
    varyant_notu = "" if varyant is None else "; DUYARLILIK VARYANTI: %s" % varyant
    return {
        "k": E_TCA, "sigma": SIGMA_E_TCA, "tur": "deney", "seri": SERI_TCA,
        "kaynak": ("ICSBEP %s, durum %d (TCA %s, %dx%d, desen %d)%s; E = %.4f ± %.4f "
                   "(ICSBEP; S.C. van der Marck, Nucl. Data Sheets 107 (2006) 3061, Tablo IX) "
                   "⊕ %.5f model basitleştirmesi (U-234 yok; docs/VV.md) = ± %.4f"
                   % (SERI_TCA, d.no, d.kafes, d.n, d.n, d.desen, varyant_notu, E_TCA,
                      SIGMA_ICSBEP_TCA, SIGMA_BASIT_TCA, SIGMA_E_TCA)),
        "kaynak_model": ("JAERI 1254 (Tsuruta vd., 1978; JAEA açık arşiv "
                         "https://jopss.jaea.go.jp/pdfdata/JAERI-1254.pdf) Tablo 1, 2, 8-1, "
                         "Ek A1, A3; durum eşlemesi JAERI-Conf 2003-006 Tablo 1"),
        "lisans": ("Birincil rapor kamuya açık (JAEA); ICSBEP el kitabı metni kullanılmadı ve "
                   "yeniden dağıtılmaz (STANDARTLAR.md §6 md. 13)."),
        "aoa_girdi": {"fiziksel_bicim": "oksit", "yansitici": "su",
                      "h_x": round(hucre.h_x, 6), "h_x_not": "birim hücre H/U-235 (heterojen)"},
    }
