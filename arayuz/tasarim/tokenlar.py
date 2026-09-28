# -*- coding: utf-8 -*-
"""
tokenlar.py -- tasarim tokenlari: renk, aralik, yaricap, yukselti, tipografi.

Arayuzde renk, bosluk ve yazi boyutu YALNIZCA buradan gelir (Dalga 1 sonrasi
kural: kodda #rrggbb ya da sabit piksel bosluk yazilmaz). Qt'ye bagli degildir;
test ve betikler PySide6 olmadan da okuyabilir.

RENK MODELI
  Notr (gri) tonlar tema basina sabittir; VURGU bir secenektir (VURGULAR).
  palet(tema, vurgu) ikisini birlestirip duz bir sozluk verir. Anahtarlar:

  zemin, yuzey1..3          pencere zemini ve yukseltilmis yuzeyler
  kenar, kenar_guclu        ayirici cizgi / giris kutusu kenari
  metin, metin_ikincil, metin_soluk
  vurgu, vurgu_hover, vurgu_basili, vurgu_metin (vurgu zemin uzerindeki yazi),
  vurgu_soluk (secili satir / hover zemini), odak (klavye odak halkasi)
  basari|uyari|hata|bilgi (+ _soluk zemin) -- rozet, bildirim, dogrulama

KONTRAST (WCAG 2.x) kontrast() ile olculur; KONTRAST_KURALLARI testte
denetlenir (testler/test_tasarim.py): normal metin >= 4.5, ikon/odak >= 3.
"""

from cekirdek.ceviri import N_

# ----------------------------------------------------------------------------
# Aralik, yaricap, yukselti, tipografi (piksel)
# ----------------------------------------------------------------------------
ARALIK = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32}

YARICAP = {"kucuk": 4, "orta": 6, "buyuk": 8, "kart": 10, "tam": 999}

# QGraphicsDropShadowEffect icin: (bulaniklik, y kaymasi, opaklik 0-255)
YUKSELTI = {
    0: (0, 0, 0),
    1: (6, 1, 28),       # kart (hafif)
    2: (18, 4, 48),      # acilir menu, bildirim
    3: (32, 10, 70),     # komut paleti, diyalog
}

# ad -> (piksel boyutu, agirlik 400/500/600, satir yuksekligi carpani)
TIPOGRAFI = {
    "ekran_basligi": (22, 600, 1.25),
    "baslik": (17, 600, 1.3),
    "altbaslik": (14, 600, 1.35),
    "govde": (13, 400, 1.45),
    "govde_vurgulu": (13, 500, 1.45),
    "kucuk": (12, 400, 1.4),
    "etiket": (11, 600, 1.3),        # BOLUM BASLIGI (buyuk harf, harf araligi)
    "mono": (12, 400, 1.45),
    "sayi_buyuk": (26, 500, 1.2),     # k-eff gibi one cikan sayi (mono)
}

YAZI_AILESI = "Inter"
# Sistemde aranir (sirayla); hicbiri yoksa Qt'nin sabit genislikli yazisi.
MONO_ADAYLARI = ("JetBrains Mono", "DejaVu Sans Mono", "Noto Sans Mono",
                 "Liberation Mono", "Ubuntu Mono")

# Denetim boyutlari
BOYUT = {
    "giris_yuksekligi": 30,
    "dugme_yuksekligi": 30,
    "ikon": 16,
    "ikon_buyuk": 20,
    "kenar_cubugu_genis": 212,
    "kenar_cubugu_dar": 52,
    "kenar_cubugu_satir": 34,
    "ust_cubuk": 52,
    "serit": 30,
    "bildirim_genislik": 360,
}

# ----------------------------------------------------------------------------
# Notr tonlar (tema basina)
# ----------------------------------------------------------------------------
_NOTR = {
    "acik": {
        "zemin": "#f5f6f8",
        "yuzey1": "#ffffff",
        "yuzey2": "#f0f2f5",
        "yuzey3": "#e6e9ee",
        "kenar": "#dfe3e8",
        "kenar_guclu": "#c3c9d2",
        "metin": "#15181d",
        "metin_ikincil": "#434a55",
        "metin_soluk": "#5f6773",
        "metin_pasif": "#9aa1ab",
        "golge": "#0b0f19",
        "basari": "#17693f",
        "basari_soluk": "#e3f3e9",
        "uyari": "#8a5000",
        "uyari_soluk": "#fcf0d9",
        "hata": "#b42318",
        "hata_soluk": "#fdeceb",
        "bilgi": "#3d5a80",
        "bilgi_soluk": "#e8eef6",
        "grafik_izgara": "#e3e7ec",
    },
    "koyu": {
        "zemin": "#101216",
        "yuzey1": "#171a1f",
        "yuzey2": "#1e2228",
        "yuzey3": "#262b32",
        "kenar": "#2b3038",
        "kenar_guclu": "#3e4550",
        "metin": "#e7e9ec",
        "metin_ikincil": "#b7bdc6",
        "metin_soluk": "#8e96a1",
        "metin_pasif": "#5c636d",
        "golge": "#000000",
        "basari": "#4cc38a",
        "basari_soluk": "#15291f",
        "uyari": "#e9a23b",
        "uyari_soluk": "#2e2412",
        "hata": "#f47067",
        "hata_soluk": "#361a19",
        "bilgi": "#8fb0d9",
        "bilgi_soluk": "#1a2533",
        "grafik_izgara": "#2a2f37",
    },
}

# ----------------------------------------------------------------------------
# Vurgu secenekleri (KAPI G1'de kullanici secer; varsayilan VARSAYILAN_VURGU)
# ----------------------------------------------------------------------------
VURGULAR = {
    "kobalt": {
        "ad": N_("Kobalt"),
        "acik": {"vurgu": "#2f5bd3", "vurgu_hover": "#284fbb", "vurgu_basili": "#2144a3",
                 "vurgu_metin": "#ffffff", "vurgu_soluk": "#e9eefc", "odak": "#2f5bd3"},
        "koyu": {"vurgu": "#7c9cf5", "vurgu_hover": "#93aef7", "vurgu_basili": "#6887e0",
                 "vurgu_metin": "#0c1330", "vurgu_soluk": "#1d2640", "odak": "#7c9cf5"},
    },
    "teal": {
        "ad": N_("Deniz yeşili"),
        "acik": {"vurgu": "#0c6d66", "vurgu_hover": "#0a5f59", "vurgu_basili": "#08514c",
                 "vurgu_metin": "#ffffff", "vurgu_soluk": "#e1f2f0", "odak": "#0c6d66"},
        "koyu": {"vurgu": "#3cc7b6", "vurgu_hover": "#5dd3c4", "vurgu_basili": "#2fb0a1",
                 "vurgu_metin": "#06231f", "vurgu_soluk": "#15302d", "odak": "#3cc7b6"},
    },
    "indigo": {
        "ad": N_("Çivit"),
        "acik": {"vurgu": "#5b47c9", "vurgu_hover": "#4f3db3", "vurgu_basili": "#43339c",
                 "vurgu_metin": "#ffffff", "vurgu_soluk": "#efecfb", "odak": "#5b47c9"},
        "koyu": {"vurgu": "#a594f9", "vurgu_hover": "#b6a8fa", "vurgu_basili": "#9180eb",
                 "vurgu_metin": "#17113a", "vurgu_soluk": "#252043", "odak": "#a594f9"},
    },
}
VARSAYILAN_VURGU = "kobalt"

TEMA_ADLARI = {"acik": N_("Açık"), "koyu": N_("Koyu")}

# Renk koruge uygun kategorik grafik paleti: Okabe & Ito (2008), "Color
# Universal Design". Sira temaya gore: acik zeminde sari (#F0E442) okunmaz,
# koyu zeminde koyu mavi (#0072B2) zayif kalir -- sona alinir.
OKABE_ITO = {"turuncu": "#E69F00", "gok": "#56B4E9", "yesil": "#009E73", "sari": "#F0E442",
             "mavi": "#0072B2", "kiremit": "#D55E00", "mor": "#CC79A7", "siyah": "#000000"}
_O = OKABE_ITO
GRAFIK_PALETI = {
    "acik": (_O["mavi"], _O["kiremit"], _O["yesil"], _O["mor"], _O["turuncu"], _O["gok"], _O["siyah"]),
    "koyu": (_O["gok"], _O["turuncu"], _O["yesil"], _O["mor"], _O["sari"], _O["kiremit"], _O["mavi"]),
}
# Surekli haritalar (guc, aki): algisal olarak duzgun ve renk koruge uygun.
GRAFIK_HARITASI = "cividis"


def palet(tema="acik", vurgu=None):
    """Tema + vurgu -> duz renk sozlugu (YENI sozluk; kaynak degismez)."""
    if tema not in _NOTR:
        raise KeyError("bilinmeyen tema: %r" % (tema,))
    v = VURGULAR.get(vurgu or VARSAYILAN_VURGU)
    if v is None:
        raise KeyError("bilinmeyen vurgu: %r" % (vurgu,))
    return {**_NOTR[tema], **v[tema]}


# ----------------------------------------------------------------------------
# Kontrast (WCAG 2.x goreli parlaklik)
# ----------------------------------------------------------------------------
def _kanal(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def parlaklik(hex_renk):
    h = hex_renk.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _kanal(r) + 0.7152 * _kanal(g) + 0.0722 * _kanal(b)


def kontrast(on, arka):
    a, b = sorted((parlaklik(on), parlaklik(arka)), reverse=True)
    return (a + 0.05) / (b + 0.05)


METIN_ESIGI = 4.5
BUYUK_ESIGI = 3.0     # buyuk metin (>= 18.66 px kalin / 24 px), ikon, odak halkasi

# (on plan, arka plan, esik) -- her tema ve her vurgu icin denetlenir.
KONTRAST_KURALLARI = (
    [(m, z, METIN_ESIGI)
     for m in ("metin", "metin_ikincil", "metin_soluk")
     for z in ("zemin", "yuzey1", "yuzey2", "yuzey3")]
    + [("vurgu_metin", "vurgu", METIN_ESIGI),
       ("vurgu_metin", "vurgu_hover", METIN_ESIGI),
       ("vurgu_metin", "vurgu_basili", METIN_ESIGI),
       ("vurgu", "yuzey1", METIN_ESIGI),         # baglanti, secili sekme yazisi
       ("vurgu", "zemin", METIN_ESIGI),
       ("vurgu", "vurgu_soluk", METIN_ESIGI),    # secili kenar cubugu ogesi
       ("metin", "vurgu_soluk", METIN_ESIGI),
       ("odak", "yuzey1", BUYUK_ESIGI),
       ("odak", "zemin", BUYUK_ESIGI)]
    + [(d, d + "_soluk", METIN_ESIGI) for d in ("basari", "uyari", "hata", "bilgi")]
    + [(d, z, METIN_ESIGI) for d in ("basari", "uyari", "hata", "bilgi")
       for z in ("yuzey1", "zemin")]
    + [("kenar_guclu", "yuzey1", 1.5)]           # giris kenari: gorunur ama sakin
)


def kontrast_raporu(tema, vurgu=None):
    """[(on, arka, oran, esik, gecti)] -- test ve rapor icin."""
    p = palet(tema, vurgu)
    return [(on, arka, kontrast(p[on], p[arka]), esik, kontrast(p[on], p[arka]) >= esik)
            for on, arka, esik in KONTRAST_KURALLARI]
