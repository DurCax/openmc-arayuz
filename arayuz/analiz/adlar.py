# -*- coding: utf-8 -*-
"""
adlar.py -- Analiz sekmesinin GORUNEN adlari ve varsayilan araliklari.

Tanimlayicilar ve fizik cekirdek/tarama.py'dedir (TURLER); burada yalnizca
kullaniciya gosterilen ad, kisa aciklama (ipucu), katsayinin adi ve makul
baslangic araliklari durur. Qt'ye bagimli tek yer form yardimcilaridir.
"""

from PySide6 import QtWidgets

from cekirdek import sema, tarama
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)

# Formlar okunur genislikte kalir (tam ekranda 1500 px'lik sayi kutusu okunmaz).
FORM_GENISLIGI = 760


def aciklama(metin):
    """Kisa aciklama satiri (tema: soluk metin rengi, okunur karsitlik)."""
    e = QtWidgets.QLabel(metin)
    e.setObjectName("kartAlt")
    e.setWordWrap(True)
    return e


def dar(duzen_ya_da_widget, genislik=FORM_GENISLIGI):
    """Bir formu en fazla 'genislik' px genislikte, sola yasli tutar."""
    if isinstance(duzen_ya_da_widget, QtWidgets.QWidget):
        w = duzen_ya_da_widget
    else:
        w = QtWidgets.QWidget()
        w.setLayout(duzen_ya_da_widget)
        duzen_ya_da_widget.setContentsMargins(0, 0, 0, 0)
    w.setMaximumWidth(genislik)
    return w


def renk(ad):
    """Etkin temadan renk. Kodda sabit #rrggbb YOKTUR (Dalga 1 kurali):
    butun renkler arayuz/tasarim/tokenlar.py'den gelir."""
    from arayuz import tema
    return tema.renk(ad)


def form_duzeni():
    """Tasarim sistemine uygun form: token araliklari, sola yasli etiket."""
    from PySide6 import QtCore
    f = QtWidgets.QFormLayout()
    f.setHorizontalSpacing(tokenlar.ARALIK["l"])
    f.setVerticalSpacing(tokenlar.ARALIK["s"])
    f.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    return f


PARAMETRE_ADLARI = {
    "yakit_sicaklik": ("Yakıt sıcaklığı (Doppler)",
                       "Yakıtın sıcaklığı değişir; yoğunluğu sabit tutulur (katı yakıt)."),
    "sogutucu_sicaklik": ("Soğutucu sıcaklığı",
                          "Sıcaklıkla birlikte yoğunluk da değişir (su tablosu, Na ve "
                          "Pb-Bi korelasyonları); moderatör sıcaklık katsayısını verir."),
    "void_orani": ("Soğutucu boşluğu (void)",
                   "Soğutucu yoğunluğu boşluk oranı kadar azaltılır."),
    "bor_ppm": ("Çözünmüş bor",
                "Suya doğal bor eklenir (ppm, kütlece)."),
    "zenginlik": ("Uranyum zenginliği",
                  "U-235'in ağırlıkça yüzdesi."),
    "cubuk_daldirma": ("Kontrol çubuğu daldırma",
                       "%0 tamamen çekilmiş, %100 tamamen dalmış."),
    "tambur_donme": ("Kontrol tamburu dönmesi",
                     "0° emici kora bakar (en düşük k), 180° dışa bakar (en yüksek k)."),
    "yansitici_kalinlik": ("Yansıtıcı kuşak kalınlığı",
                           "Yansıtıcı kuşağın radyal kalınlığı."),
    "kafes_adim": ("Çubuk adımı (moderasyon oranı)",
                   "Demetteki çubuk adımı; moderatör/yakıt oranını değiştirir."),
    "kor_adim": ("Kor hücre adımı",
                 "Pin hücrede hücre adımı, tam korda demet adımı."),
    "cubuk_yaricap": ("Çubuk bölge yarıçapı",
                      "Çubuğun seçilen bölgesinin dış yarıçapı."),
    "malzeme_yogunluk": ("Malzeme yoğunluğu",
                         "Seçilen malzemenin yoğunluğu (g/cm³)."),
}

# Katsayinin adi (sonuc kartinda). Listede olmayan: "Reaktivite katsayısı".
KATSAYI_ADLARI = {
    "yakit_sicaklik": "Doppler katsayısı",
    "sogutucu_sicaklik": "Moderatör sıcaklık katsayısı",
    "void_orani": "Boşluk (void) katsayısı",
    "bor_ppm": "Bor değeri",
    "zenginlik": "Zenginlik duyarlılığı",
    "cubuk_daldirma": "Çubuk değeri (diferansiyel)",
    "tambur_donme": "Tambur değeri (diferansiyel)",
}

# Liste sirasi: en yaygin analizler basta. Tasarim etutleri (geometri ve
# yogunluk) "Gelismis" altindadir.
SIRA = ("yakit_sicaklik", "sogutucu_sicaklik", "void_orani", "bor_ppm", "zenginlik",
        "cubuk_daldirma", "tambur_donme", "yansitici_kalinlik",
        "kafes_adim", "kor_adim", "cubuk_yaricap", "malzeme_yogunluk")
GELISMIS_PARAMETRELER = ("kafes_adim", "kor_adim", "cubuk_yaricap", "malzeme_yogunluk")

_BIRIM_GORUNEN = {"g/cm3": "g/cm³", "derece": "°"}

# Makul varsayilan araliklar (bas, son, nokta). Geometri ve yogunluk
# parametrelerinde aralik modeldeki MEVCUT degerden turetilir (bkz.
# _varsayilan_aralik): sabit bir 0.35-0.45 cm yaricap araligi ic ice
# bolgeleri cakistirabiliyordu.
_VARSAYILAN = {
    "yakit_sicaklik": (600, 1200, 5), "sogutucu_sicaklik": (540, 620, 5),
    "void_orani": (0, 50, 5), "bor_ppm": (0, 2000, 5),
    "zenginlik": (2.0, 5.0, 5), "kafes_adim": (1.1, 1.5, 5),
    "malzeme_yogunluk": (0.4, 0.8, 5), "kor_adim": (1.1, 1.5, 5),
    "cubuk_yaricap": (0.35, 0.45, 5), "yansitici_kalinlik": (5, 40, 5),
    "cubuk_daldirma": (0, 100, 6), "tambur_donme": (0, 180, 5),
}


def parametre_adi(tur):
    if tur in PARAMETRE_ADLARI:
        return PARAMETRE_ADLARI[tur][0]
    return tarama.TURLER.get(tur, (tur,))[0]


def birim(tur):
    b = tarama.TURLER.get(tur, ("", "", "", ""))[2]
    return _BIRIM_GORUNEN.get(b, b)


def katsayi_birimi(tur):
    b = tarama.TURLER.get(tur, ("", "", "", ""))[3]
    for eski, yeni in _BIRIM_GORUNEN.items():
        b = b.replace(eski, yeni)
    return b


def sirali_taramalar(turler):
    """Gecerli tarama turlerini gorunen siraya dizer (bilinmeyenler sonda)."""
    turler = list(turler)
    return [t for t in SIRA if t in turler] + [t for t in turler if t not in SIRA]


def varsayilan_aralik(spec, tur, hedef):
    """
    (bas, son, nokta). Geometri/yogunluk parametrelerinde modeldeki MEVCUT
    degerden turetilir; ic ice bolgeler cakismasin diye komsu yaricaplarla
    sinirlanir.
    """
    a, b, n = _VARSAYILAN.get(tur, (0.0, 1.0, 5))
    try:
        if tur == "cubuk_yaricap" and hedef:
            c = sema.cubuk_bul(spec, hedef[0])
            bolgeler = c["bolgeler"]
            i = int(hedef[1])
            r = float(bolgeler[i]["r"])
            r_once = float(bolgeler[i - 1]["r"]) if i > 0 else 0.0
            r_sonra = bolgeler[i + 1].get("r") if i + 1 < len(bolgeler) else None
            a = max(0.9 * r, 0.5 * (r_once + r))
            b = min(1.1 * r, 0.5 * (r + float(r_sonra))) if r_sonra else 1.05 * r
        elif tur in ("kafes_adim", "kor_adim"):
            if tur == "kafes_adim":
                adim = float(sema.demet_bul(spec, hedef)["adim"])
            else:
                adim = float((spec.get("kor") or {}).get("adim") or 0.0)
            if adim > 0:
                r_en = max([float(x["r"]) for c in spec.get("cubuklar", [])
                            for x in c.get("bolgeler") or [] if x.get("r")] or [0.0])
                if tur == "kor_adim" and (spec.get("kor") or {}).get("tur") == "kare_kafes":
                    a, b = adim, 1.05 * adim     # demetler ust uste binmesin
                else:
                    a, b = max(0.95 * adim, 2.02 * r_en), 1.25 * adim
        elif tur == "malzeme_yogunluk" and hedef:
            rho = float(sema.malzeme_bul(spec, hedef)["yogunluk"]["deger"])
            a, b = 0.9 * rho, 1.1 * rho
        elif tur == "sogutucu_sicaklik" and hedef:
            T = float(sema.malzeme_bul(spec, hedef).get("sicaklik") or 0.0)
            if T > 0:
                a, b = T - 40.0, T + 40.0
                m = sema.malzeme_bul(spec, hedef)
                from cekirdek import malzeme_kutup as mk
                if tarama._yogunluk_korelasyonu(m)[0] is mk.su_yogunluk:
                    a, b = max(a, 280.0), min(b, 620.0)   # doymus su tablosu
        elif tur == "yansitici_kalinlik":
            k = float(((spec.get("kor") or {}).get("yansitici") or {}).get("kalinlik") or 0.0)
            if k > 0:
                a, b = max(0.25 * k, 1.0), 2.0 * k
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        # Model bu parametre icin beklenen bicimde degil (ornek sekme
        # acikken silinen bolge): sabit varsayilanla devam edilir, ama
        # sessiz kalinmaz -- yanlis aralik kullaniciyi yaniltir.
        _log.warning("%r parametresi icin varsayilan aralik modelden "
                     "turetilemedi; sabit aralik kullanildi", tur, exc_info=True)
    yuvarla = 4 if tur in ("cubuk_yaricap", "kafes_adim", "kor_adim",
                           "malzeme_yogunluk") else 1
    return round(a, yuvarla), round(b, yuvarla), n
