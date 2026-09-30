# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_denetimi/profiller.py  --  Denetim profilleri ve KAYNAKLI esikler
================================================================================

 KURAL: kaynagi gosterilemeyen esik konmaz (STANDARTLAR.md §1). Her esik
 degeriyle birlikte atfini tasir; standartta sayisal deger YOKSA varsayilan
 None'dir ve ilgili kural "karsilastirilamadi" der (ör. F_dH, F_q, kapatma
 marji -- NUREG-0800 §4.3 bunlari tesise ozel birakir).

 Profiller (STANDARTLAR.md §3):
   A  Monte Carlo iyi uygulamasi (her kosu)          K1, K2, K3
   B  Kritiklik guvenligi (istege bagli)            K6, K6-AOA, K8-K14
   C  Reaktor kor tasarimi                          K7, K7-SDM, K7-F, K16
   D  Raporlama                                     K4, K5

 Kullanici esikleri: uyarla(profil, ad=deger | (deger, kaynak)) YENI profil
 dondurur; dosyadan_uyarla(profiller, yol) JSON okur:
     {"C": {"F_dH_siniri": {"deger": 1.55, "kaynak": "Tesis TS 3.2.1"}}}
================================================================================
"""

import json
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Tuple

from cekirdek.ceviri import _, N_

# --- atif metinleri (tek yerde; STANDARTLAR.md kaynakcasi) ---
BROWN_2009 = "F.B. Brown, LA-UR-09-03136 (2009) 'A Review of Best Practices for Monte Carlo Criticality Calculations'"
NUREG_6698 = "NUREG/CR-6698 (2001)"
NUREG_1520 = "NUREG-1520 Bl. 5 Ek B / NUREG-1718 §6.4.3.3.4 (0.05 değeri DOĞRULANMADI)"
SRP_43 = "NUREG-0800 §4.3 Rev. 3 (2007)"
GUM = "JCGM 100:2008 (GUM)"
KULLANICI = N_("kullanıcı girdisi")
KAYNAKSIZ = N_("kullanıcı girdisi — kaynak belirtilmedi")


@dataclass(frozen=True)
class Esik:
    """Kaynakli esik. deger None: standart sayi vermez, kullanici girer."""
    deger: Any
    kaynak: str
    aciklama: str = ""


@dataclass(frozen=True)
class Profil:
    kimlik: str
    ad: str
    aciklama: str
    kurallar: Tuple[str, ...]
    esikler: Mapping[str, Esik] = field(default_factory=dict)

    def gorunen_ad(self):
        return _(self.ad)


def durust_cerceve():
    """Rapor eki ve panelde AYNEN gosterilecek cerceve metni (plan, Dalga S)."""
    return _("Bu program hiçbir standarda sertifika vermez ve bir analizi "
             "\"standarda uygun\" diye onaylayamaz. Yaptığı iş, bir koşu ya da model "
             "için standartların ve iyi uygulamanın isteyeceği kanıtı üretmek ve "
             "eksikleri görünür kılmaktır. Tesis lisanslaması ya da güvenlik "
             "analizinde kullanım için kullanıcı kuruluşun kendi kalite güvence "
             "programı ve bağımsız gözden geçirmesi ayrıca gerekir. Kaynağı "
             "gösterilemeyen eşik konmaz; eşikler profilde ayarlanabilir.")


_A = Profil(
    kimlik="A", ad=N_("Monte Carlo iyi uygulaması"),
    aciklama=N_("Her koşu: kaynak yakınsaması, istatistik yeterliliği, kayıp parçacık. "
                "Standart maddesi değildir; iyi uygulama olarak etiketlidir."),
    kurallar=("K1", "K2", "K3"),
    esikler={
        "sigma_hedef": Esik(None, N_("standart değeri yok — kullanıcı/proje hedefi "
                                     "(STANDARTLAR.md §3 satır 2)"),
                            N_("k-eff standart belirsizliği (1σ) üst hedefi")),
        "parcacik_asgari": Esik(1000, BROWN_2009 + " §III.C",
                                N_("her hesap için çevrim başına binlerce nötron")),
        "parcacik_uretim": Esik(5000, BROWN_2009 + " §V",
                                N_("uzun üretim koşuları için çevrim başına en az 5000")),
        "aktif_asgari": Esik(None, BROWN_2009 + " §V ('birkaç yüz aktif çevrim'; sayı "
                                                "verilmez → kullanıcı)"),
        "korelasyon_z": Esik(2.0, N_("Bartlett yaklaşımı: bağımsız dizide gecikme-1 öz "
                                     "ilinti ≈ N(0, 1/N); MC σ'sı çevrimler arası "
                                     "ilintiyi yok sayar (") + BROWN_2009 + " §IV)"),
        "kayip_azami": Esik(0, N_("iyi uygulama (OpenMC): kayıp parçacık geometri "
                                  "hatası belirtisidir")),
    })

_B = Profil(
    kimlik="B", ad=N_("Kritiklik güvenliği"),
    aciklama=N_("İsteğe bağlı: k + 2σ < USL (NUREG/CR-6698 eş. 36), AOA ve doğrulama "
                "kümesinin istatistik koşulları. Doğrulama kümesi yoksa USL "
                "hesaplanamadı denir."),
    kurallar=("K6", "K6-AOA", "K8", "K9", "K10", "K11", "K12", "K13", "K14"),
    esikler={
        "kabul_carpani": Esik(2.0, NUREG_6698 + " eş. (36): k + 2σ < USL"),
        "delta_sm": Esik(0.05, NUREG_1520),
        "delta_sm_asgari": Esik(0.02, NUREG_6698 + " §2.4.5 (mutlak alt sınır)"),
        "n_asgari": Esik(10, NUREG_6698 + " §2.2 (10'dan az deney teknik gerekçe ister)"),
        "guven_asgari": Esik(0.40, NUREG_6698 + " Tablo 2.2 (β ≤ %40 → ek veri gerekli)"),
        "dis_degerleme_azami": Esik(0.10, NUREG_6698 + " §1.2, §5 (%10'u aşan dış "
                                                        "değerleme → küme genişletilmeli)"),
    })

_C = Profil(
    kimlik="C", ad=N_("Reaktör kor tasarımı"),
    aciklama=N_("Reaktivite katsayılarının işareti (GDC 11 çerçevesi), kapatma marjı "
                "(en değerli çubuk sıkışık, N−1), F_ΔH / F_q. Sayısal sınırlar tesise "
                "özeldir: varsayılan sınır YOK."),
    kurallar=("K7", "K7-SDM", "K7-F", "K16"),
    esikler={
        "F_dH_siniri": Esik(None, SRP_43 + N_(" — güç dağılımı sınırı tesise özel")),
        "F_q_siniri": Esik(None, SRP_43 + N_(" — güç dağılımı sınırı tesise özel")),
        "sdm_siniri_pcm": Esik(None, SRP_43 + N_(" — kapatma marjı değeri SRP'de boş, "
                                                  "tesise özel")),
        "anlamlilik_carpani": Esik(2.0, N_("proje ölçütü: |eğim| > 2σ ise işaret "
                                           "anlamlı (cekirdek/tarama.yorumla)")),
        "reaktor_turu": Esik("guc", N_("IAEA SSG-22 (Rev. 1) kademeli yaklaşım: 'guc' → "
                                       "SSG-52 / SRP 4.3; 'arastirma' → SSR-3")),
    })

_D = Profil(
    kimlik="D", ad=N_("Raporlama"),
    aciklama=N_("Veri izlenebilirliği (K4) ve belirsizlik/birim bildirimi (K5)."),
    kurallar=("K4", "K5"),
    esikler={
        "anlamli_rakam_azami": Esik(2, GUM + " §7.2.6"),
    })

VARSAYILAN = {p.kimlik: p for p in (_A, _B, _C, _D)}
PROFIL_KIMLIKLERI = tuple(VARSAYILAN)


def profil_getir(kimlik):
    """Varsayilan profil; bilinmeyen kimlikte ValueError."""
    try:
        return VARSAYILAN[kimlik]
    except KeyError:
        raise ValueError(_("bilinmeyen denetim profili: %s (geçerli: %s)")
                         % (kimlik, ", ".join(PROFIL_KIMLIKLERI))) from None


def _esik_cozumle(profil, ad, girdi):
    if isinstance(girdi, Esik):
        return girdi
    if isinstance(girdi, Mapping):
        deger, kaynak = girdi.get("deger"), girdi.get("kaynak")
    elif isinstance(girdi, (tuple, list)) and len(girdi) == 2:
        deger, kaynak = girdi
    else:
        deger, kaynak = girdi, None
    eski = profil.esikler.get(ad)
    return Esik(deger, kaynak or _(KAYNAKSIZ), eski.aciklama if eski else "")


def uyarla(profil, **esikler):
    """
    Profilin esiklerini degistirilmis YENI kopyasi. Deger: sayi | (sayi, kaynak)
    | {"deger":..,"kaynak":..} | Esik. Bilinmeyen esik adinda ValueError
    (yazim hatasi sessizce yok sayilmasin).
    """
    bilinmeyen = sorted(set(esikler) - set(profil.esikler))
    if bilinmeyen:
        raise ValueError(_("%s profilinde bilinmeyen eşik: %s")
                         % (profil.kimlik, ", ".join(bilinmeyen)))
    yeni = dict(profil.esikler)
    for ad, girdi in esikler.items():
        yeni[ad] = _esik_cozumle(profil, ad, girdi)
    return replace(profil, esikler=yeni)


def dosyadan_uyarla(yol, profiller=None):
    """
    JSON profil dosyasini okur: {"<kimlik>": {"<esik>": deger | {...}}}.
    DONER {kimlik: Profil} (verilen ya da varsayilan profiller uzerine).
    Dosya/JSON hatasi ValueError olarak yukari cikar (metin kullaniciya).
    """
    taban = dict(profiller or VARSAYILAN)
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError(_("profil dosyası okunamadı: %s (%s)") % (yol, e)) from e
    if not isinstance(veri, dict):
        raise ValueError(_("profil dosyası bir JSON nesnesi olmalı: %s") % yol)
    for kimlik, esikler in veri.items():
        profil = taban.get(kimlik) or profil_getir(kimlik)
        taban[kimlik] = uyarla(profil, **(esikler or {}))
    return taban
