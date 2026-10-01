# -*- coding: utf-8 -*-
"""
maket_veri.py -- maket ekranlarinin SABIT ornek verisi ve ortak kurucular.
Maketler islev baglamaz; buradaki sayilar gorsel ornektir, hesap degildir.
"""

from cekirdek import ornek_bilgi
from cekirdek.ceviri import N_, _

# (anahtar, metin, ikon, grup) -- Dalga 2 kabugunun is akisi sirasi
GEZINME = (
    ("malzemeler", N_("Malzemeler"), "flask-conical", N_("Model")),
    ("parcalar", N_("Parçalar"), "cylinder", N_("Model")),
    ("demet", N_("Demet"), "grid-3x3", N_("Model")),
    ("kor", N_("Kor"), "hexagon", N_("Model")),
    ("hesap", N_("Hesap"), "sliders-horizontal", N_("Hesap")),
    ("calistir", N_("Çalıştır"), "play", N_("Hesap")),
    ("sonuclar", N_("Sonuçlar"), "chart-line", N_("Sonuç")),
    ("analiz", N_("Analiz"), "activity", N_("Sonuç")),
    ("tukenme", N_("Tükenme"), "hourglass", N_("Sonuç")),
)

DURUMLAR = {"malzemeler": "tamam", "parcalar": "tamam", "demet": "tamam",
            "kor": "eksik", "hesap": "tamam", "calistir": "eksik",
            "sonuclar": None, "analiz": None, "tukenme": None}

MODEL = {"ad": N_("PWR 17×17 yakıt demeti"), "tur": N_("Yakıt demeti — kare"),
         "ozet": N_("2B · Özdeğer (k-eff)"), "olcu": "21.42 × 21.42 cm"}

MALZEMELER = (
    ("UO2 %3.20", "10.257 g/cm³", "600 K", N_("yakıt"), 0),
    ("Zircaloy-4", "6.550 g/cm³", "580 K", N_("zarf"), 4),
    ("He", "0.0015 g/cm³", "580 K", N_("boşluk"), 6),
    ("H2O + 1300 ppm B", "0.700 g/cm³", "580 K", N_("soğutucu"), 5),
    ("B4C", "1.760 g/cm³", "580 K", N_("soğurucu"), 3),
)

BILESIM = (("U234", "0.000286"), ("U235", "0.032000"), ("U238", "0.967714"),
           ("O16", "2.000000"))

PARCALAR = (("yakit_cubugu", N_("YÇ"), N_("Yakıt çubuğu"), 264, 0),
            ("kilavuz_boru", N_("KB"), N_("Kılavuz boru"), 24, 1),
            ("enstruman", N_("EN"), N_("Enstrüman borusu"), 1, 2),
            ("su", N_("SU"), N_("Su hücresi"), 0, 5))

# 17x17 Westinghouse: kilavuz boru konumlari (satir, sutun), merkez enstruman
KILAVUZ = {(2, 5), (2, 8), (2, 11), (3, 3), (3, 13), (5, 2), (5, 5), (5, 8), (5, 11),
           (5, 14), (8, 2), (8, 5), (8, 11), (8, 14), (11, 2), (11, 5), (11, 8), (11, 11),
           (11, 14), (13, 3), (13, 13), (14, 5), (14, 8), (14, 11)}
ENSTRUMAN = {(8, 8)}

# Baslangic ekrani: model turu kartlari (ikon, baslik, aciklama)
MODEL_TURLERI = (
    ("circle-dot", N_("Yakıt çubuğu (pin hücre)"), N_("Tek çubuk ve soğutucu; en hızlı başlangıç.")),
    ("grid-3x3", N_("Yakıt demeti — kare"), N_("Kare ızgarada çubuklar ve kılavuz borular (PWR).")),
    ("hexagon", N_("Yakıt demeti — altıgen"), N_("Altıgen ızgarada demet (VVER, hızlı reaktör).")),
    ("layers", N_("Tam kor"), N_("Demetlerden oluşan kor haritası ve yansıtıcı.")),
    ("list", N_("MTR plaka elemanı"), N_("Araştırma reaktörünün düz plakalı yakıtı.")),
    ("refresh-cw", N_("Tamburlu kompakt kor"), N_("Dönen kontrol tamburlu hızlı kor.")),
    ("shield", N_("Zırhlama"), N_("Sabit kaynaktan zırh katmanlarında zayıflama.")),
)

# Galeri kategorileri tek kaynaktan: cekirdek/ornek_bilgi.py
KATEGORILER = (("hepsi", N_("Tümü")),) + tuple(
    (k, ornek_bilgi.KATEGORI_ADLARI[k]) for k in ornek_bilgi.KATEGORILER)

# (baslik, kategori, aciklama, kucuk resim motifi)
ORNEKLER = (
    (N_("PWR yakıt hücresi"), "pwr", N_("Klasik PWR pin hücresi, 2B."), "pin"),
    (N_("PWR 17×17 yakıt demeti"), "pwr", N_("264 yakıt çubuğu, 24 kılavuz boru."), "kare"),
    (N_("PWR demeti — 3B"), "pwr", N_("366 cm aktif yükseklik, eksenel yansıtıcı."), "kare3b"),
    (N_("VVER-1000 demeti"), "vver", N_("331 konum, 312 yakıt çubuğu."), "altigen"),
    (N_("SFR altıgen demet"), "sfr", N_("Sodyum soğutmalı, 127 çubuk."), "altigen"),
    (N_("MTR plaka elemanı"), "arastirma", N_("23 düz plaka, U3Si2-Al."), "plaka"),
    (N_("TRIGA kor"), "arastirma", N_("Havuz tipi araştırma reaktörü koru."), "kor"),
    (N_("Godiva kritik küresi"), "kriter", N_("ICSBEP HEU-MET-FAST-001."), "kure"),
    (N_("Jezebel"), "kriter", N_("ICSBEP PU-MET-FAST-001."), "kure"),
    (N_("Beton zırh"), "zirh", N_("14 MeV nötron, beton katmanlarda zayıflama."), "zirh"),
)

SON_KULLANILANLAR = (("kor_taslak.json", "~/modeller", N_("2 saat önce")),
                     ("pwr_17x17_b1300.json", "~/ders/hafta5", N_("dün")),
                     ("godiva_dogrulama.json", "~/tez", N_("3 gün önce")))

SONUC = {"keff": "1.18342", "sigma": "0.00041", "pcm": "41", "hedef_pcm": "50",
         "entropi": "7.921", "sure": "3:12", "hiz": "52 400", "parcacik": "10 000",
         "cevrim": "250 / 50"}

GUNLUK = (
    " Bat./Gen.      k        Entropy         Average k",
    " =========   ========   ========   ====================",
    "     248/1    1.18317    7.92044    1.18341 +/- 0.00042",
    "     249/1    1.18402    7.92107    1.18342 +/- 0.00041",
    "     250/1    1.18355    7.92079    1.18342 +/- 0.00041",
    " Creating state point statepoint.250.h5...",
    " Combined k-effective        = 1.18336 +/- 0.00037",
)


def kenar_cubugu_kur(secili="demet", durumlar=None, gruplu=True):
    from arayuz.bilesenler import KenarCubugu
    k = KenarCubugu()
    onceki_grup = None
    for anahtar, metin, ikon, grup in GEZINME:
        if gruplu and grup != onceki_grup:
            k.grup_ekle(_(grup))
            onceki_grup = grup
        k.ekle(anahtar, _(metin), ikon)
    for anahtar, durum in (durumlar or DURUMLAR).items():
        k.durum_ayarla(anahtar, durum)
    k.sec(secili)
    return k
