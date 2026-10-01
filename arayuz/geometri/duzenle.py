# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/duzenle.py  --  Agac islemleri (SAF; docs/GEOMETRI_MODELI.md §10)
================================================================================
 Gelismis geometri editorunun her islemi burada SAF bir islevdir: girdi agaci
 (spec["geometri"]) DEGISMEZ, yeni agac doner. Arayuz yeni agaci spec'e yazar
 ve pencere/gecmis.py onu tek adim olarak yigar (geri al / yinele).

 YOL
   Agac icindeki bir yer anahtar demetidir: ("kok", "halkalar", 0, "icerik").
   Metin bicimi JSON isaretcisidir: "/kok/halkalar/0/icerik" (yol_metni).

 YUVA (bir dugumun konabilecegi yer; §2)
   kap.ic, kap.dis (kok disi), halka.icerik, yerlesim.icerik, kafes.anahtar[h],
   kafes.dis, eksenel.icerik, katman.icerik, parca.dugum ve kok'un kendisi.
   halka.dis bir KESITTIR (dugum degil); yuva sayilmaz.

 Qt gerektirmez; testler/test_geometri_ui.py sinar. Hata: DuzenlemeHatasi
 (kullaniciya gosterilecek, cevrilebilir mesaj).
================================================================================
"""

import copy
import re

from cekirdek import geometri
from cekirdek.ceviri import _

BOSLUK = "bosluk"
KOK = ("kok",)
_LISTE_ALANLARI = ("halkalar", "yerlesimler", "katmanlar", "parcalar", "gruplar")
_ICERIK_SAHIPLERI = ("halka", "yerlesim", "eksenel", "katman")


class DuzenlemeHatasi(ValueError):
    """Gecersiz agac islemi (mesaj kullaniciya gosterilir)."""


# ============================================================================
# yollar
# ============================================================================

def yol_metni(yol):
    """("kok", "halkalar", 0) -> "/kok/halkalar/0"."""
    return "/" + "/".join(str(p) for p in yol)


def yol_coz(metin):
    """"/kok/halkalar/0" -> ("kok", "halkalar", 0). Sayi parcalari int olur."""
    parcalar = [p for p in str(metin or "").split("/") if p != ""]
    return tuple(int(p) if p.isdigit() else p for p in parcalar)


def al(agac, yol):
    """Yoldaki deger; yol gecersizse None."""
    d = agac
    for p in yol:
        if isinstance(d, dict) and not isinstance(p, int) and p in d:
            d = d[p]
        elif isinstance(d, list) and isinstance(p, int) and 0 <= p < len(d):
            d = d[p]
        else:
            return None
    return d


def _ayarla(kopya, yol, deger):
    """kopya (zaten derin kopya) icinde yolu yerinde ayarlar."""
    if not yol:
        raise DuzenlemeHatasi(_("Boş yol ayarlanamaz."))
    ebeveyn = al(kopya, yol[:-1])
    son = yol[-1]
    if isinstance(ebeveyn, list) and isinstance(son, int) and 0 <= son < len(ebeveyn):
        ebeveyn[son] = deger
    elif isinstance(ebeveyn, dict) and not isinstance(son, int):
        ebeveyn[son] = deger
    else:
        raise DuzenlemeHatasi(_("Geçersiz yol: {yol}").format(yol=yol_metni(yol)))


def yaz(agac, yol, deger):
    """Yeni agac: yoldaki deger 'deger' (kopya) olur."""
    kopya = copy.deepcopy(agac)
    _ayarla(kopya, tuple(yol), copy.deepcopy(deger))
    return kopya


def alan_yaz(agac, yol, alan, deger):
    """Yeni agac: yoldaki sozlugun 'alan'i = deger (None -> alan silinir)."""
    kopya = copy.deepcopy(agac)
    hedef = al(kopya, tuple(yol))
    if not isinstance(hedef, dict):
        raise DuzenlemeHatasi(_("Geçersiz yol: {yol}").format(yol=yol_metni(yol)))
    if deger is None:
        hedef.pop(alan, None)
    else:
        hedef[alan] = copy.deepcopy(deger)
    return kopya


# ============================================================================
# yuvalar ve ogeler
# ============================================================================

def oge_turu(agac, yol):
    """
    Yoldaki ogenin turu: "dugum" (bir yuvadaki dugum), "halka", "yerlesim",
    "katman", "parca", "grup", "parcalar", "gruplar" ya da None.
    """
    yol = tuple(yol)
    if yol in (("parcalar",), ("gruplar",)):
        return yol[0]
    if len(yol) >= 2 and isinstance(yol[-1], int):
        liste = yol[-2]
        return {"halkalar": "halka", "yerlesimler": "yerlesim", "katmanlar": "katman",
                "parcalar": "parca", "gruplar": "grup"}.get(liste)
    return "dugum" if yuva_mu(agac, yol) else None


def yuva_mu(agac, yol):
    """Yol bir dugum yuvasi mi (kok, kap.ic, halka.icerik, ...)?"""
    yol = tuple(yol)
    if yol == KOK:
        return True
    if len(yol) < 2:
        return False
    son, ebeveyn_yolu = yol[-1], yol[:-1]
    ebeveyn = al(agac, ebeveyn_yolu)
    if not isinstance(ebeveyn, dict):
        return False
    if len(ebeveyn_yolu) >= 1 and ebeveyn_yolu[-1] == "anahtar":
        return True
    if son == "dugum":
        return oge_turu(agac, ebeveyn_yolu) == "parca"
    tur = ebeveyn.get("tur")
    if son == "ic":
        return tur == "kap"
    if son == "dis":
        return tur in ("kap", "kafes")
    if son == "icerik":
        return tur == "eksenel" or oge_turu(agac, ebeveyn_yolu) in _ICERIK_SAHIPLERI
    return False


def ata_mi(ata, yol):
    """'ata' yolu 'yol'un kendisi ya da atasi mi?"""
    ata, yol = tuple(ata), tuple(yol)
    return yol[:len(ata)] == ata


def kap_yolu(agac, yol):
    """Yolu iceren en yakin kap dugumunun yolu (yoksa None)."""
    yol = tuple(yol)
    while yol:
        d = al(agac, yol)
        if isinstance(d, dict) and d.get("tur") == "kap" and yuva_mu(agac, yol):
            return yol
        yol = yol[:-1]
    return None


# ============================================================================
# kimlikler ve adlar
# ============================================================================

def _butun_idler(deger, sonuc):
    if isinstance(deger, dict):
        if isinstance(deger.get("id"), str):
            sonuc.add(deger["id"])
        for v in deger.values():
            _butun_idler(v, sonuc)
    elif isinstance(deger, list):
        for v in deger:
            _butun_idler(v, sonuc)
    return sonuc


def yeni_id(agac, onek="d"):
    """Agacta kullanilmayan kimlik: d1, d2, ..."""
    var = _butun_idler(agac, set())
    i = 1
    while "%s%d" % (onek, i) in var:
        i += 1
    return "%s%d" % (onek, i)


def yerlesim_adlari(agac):
    """Agactaki butun yerlesim adlari (grup uyeleri icin)."""
    adlar = []

    def gez(d):
        if isinstance(d, dict):
            for y in d.get("yerlesimler") or []:
                if isinstance(y, dict) and y.get("ad"):
                    adlar.append(y["ad"])
            for v in d.values():
                gez(v)
        elif isinstance(d, list):
            for v in d:
                gez(v)
    gez(agac.get("kok"))
    for p in agac.get("parcalar") or []:
        gez(p.get("dugum"))
    return adlar


def _tekil_ad(taban, kullanilan):
    if taban not in kullanilan:
        return taban
    i = 2
    while "%s_%d" % (taban, i) in kullanilan:
        i += 1
    return "%s_%d" % (taban, i)


_AD_DESENI = re.compile(r"^[A-Za-z0-9_\-. çğıöşüÇĞİÖŞÜ]+$")


def ad_gecerli_mi(ad):
    """Bos olmayan, '/' icermeyen okunur ad."""
    return bool(ad) and bool(_AD_DESENI.match(ad)) and ad.strip() == ad


# ============================================================================
# yeni dugumler
# ============================================================================

def malzeme(ad=BOSLUK):
    return {"tur": "malzeme", "ad": ad or BOSLUK}


def yeni_dugum(tur, agac, varsayilan_malzeme=BOSLUK, bilesen_adi=None):
    """Editorun "+ Dugum" menusu icin makul varsayilanli yeni dugum."""
    dolgu = malzeme(varsayilan_malzeme)
    if tur == "malzeme":
        return dolgu
    if tur == "bilesen":
        return {"tur": "bilesen", "ad": bilesen_adi}
    if tur == "kafes":
        return {"tur": "kafes", "id": yeni_id(agac), "sekil": "kare", "adim": 1.26,
                "boyut": [3, 3], "harita": ["AAA", "AAA", "AAA"],
                "anahtar": {"A": copy.deepcopy(dolgu)}, "dis": copy.deepcopy(dolgu)}
    if tur == "kap":
        return {"tur": "kap", "id": yeni_id(agac),
                "kesit": {"sekil": "silindir", "yaricap": 5.0},
                "ic": copy.deepcopy(dolgu), "yerlesimler": [], "halkalar": [],
                "dis": malzeme(BOSLUK)}
    if tur == "eksenel":
        return {"tur": "eksenel", "id": yeni_id(agac), "icerik": copy.deepcopy(dolgu),
                "katmanlar": [{"ad": _("aktif"), "yukseklik": 100.0, "icerik": None}]}
    raise DuzenlemeHatasi(_("Bilinmeyen düğüm türü: {tur}").format(tur=tur))


def dugum_koy(agac, yuva, dugum):
    """Yuvaya yeni dugum koyar (eskisinin yerine)."""
    yuva = tuple(yuva)
    if not yuva_mu(agac, yuva):
        raise DuzenlemeHatasi(_("Buraya düğüm konamaz."))
    if yuva == KOK and (dugum or {}).get("tur") != "kap":
        raise DuzenlemeHatasi(_("Kök yalnızca bir kap olabilir."))
    return yaz(agac, yuva, dugum)


# ============================================================================
# ekleme
# ============================================================================

def halka_ekle(agac, kap_yol, kalinlik=10.0, icerik=None):
    """Kaba dis halka ekler (kalinlik ile duzgun buyur)."""
    kap = al(agac, kap_yol)
    if not (isinstance(kap, dict) and kap.get("tur") == "kap"):
        raise DuzenlemeHatasi(_("Halka yalnızca bir kaba eklenir."))
    if (kap.get("kesit") or {}).get("sekil") == "kafes_zarfi" and not kap.get("halkalar"):
        # kafes zarfinda kalinlik kullanilamaz (§3.6): dis kesit verilir.
        halka = {"dis": {"sekil": "altigen", "yonelim": _kafes_yonelimi(kap),
                         "apotem": _zarf_apotemi(kap) + float(kalinlik)}}
    else:
        halka = {"kalinlik": float(kalinlik)}
    halka["icerik"] = copy.deepcopy(icerik) if icerik else malzeme(BOSLUK)
    halka["yerlesimler"] = []
    kopya = copy.deepcopy(agac)
    al(kopya, kap_yol).setdefault("halkalar", []).append(halka)
    return kopya


def _kafes_yonelimi(kap):
    ic = kap.get("ic")
    if isinstance(ic, dict) and ic.get("tur") == "eksenel":
        ic = ic.get("icerik")
    return (ic or {}).get("yonelim", "y") if isinstance(ic, dict) else "y"


def _zarf_apotemi(kap):
    from cekirdek.geometri.kesit import kafes_zarfi_apotemi
    ic = kap.get("ic")
    if isinstance(ic, dict) and ic.get("tur") == "eksenel":
        ic = ic.get("icerik")
    if not (isinstance(ic, dict) and ic.get("tur") == "kafes"):
        return 0.0
    return kafes_zarfi_apotemi(int(ic.get("halka_sayisi") or 1), float(ic.get("adim") or 0.0))


def bolge_yerlesim_listesi(agac, bolge_yol):
    """Bolge (kap ya da halka) yolunun yerlesim listesi yolu."""
    bolge = al(agac, bolge_yol)
    tur = oge_turu(agac, bolge_yol)
    if tur == "halka" or (isinstance(bolge, dict) and bolge.get("tur") == "kap"):
        return tuple(bolge_yol) + ("yerlesimler",)
    raise DuzenlemeHatasi(_("Yerleşim bir kabın içine ya da bir halkaya eklenir."))


_VARSAYILAN_KESIT = {"sekil": "silindir", "yaricap": 1.0}


def yerlesim_ekle(agac, bolge_yol, icerik=None, ad=None, kesit=_VARSAYILAN_KESIT):
    """Bolgeye 'halka' modlu yeni yerlesim ekler (tek ornek, merkezde degil).
    kesit=None: dogal kesit (tambur dairesi)."""
    liste_yolu = bolge_yerlesim_listesi(agac, bolge_yol)
    ad = _tekil_ad(ad or _("yerlesim"), set(yerlesim_adlari(agac)))
    y = {"ad": ad, "mod": "halka", "sayi": 1, "merkez_yaricap": 5.0,
         "baslangic_acisi": 0.0,
         "icerik": copy.deepcopy(icerik) if icerik else malzeme(BOSLUK),
         "kesit": copy.deepcopy(kesit)}
    kopya = copy.deepcopy(agac)
    ebeveyn = al(kopya, liste_yolu[:-1])
    ebeveyn.setdefault("yerlesimler", []).append(y)
    return kopya


def katman_ekle(agac, eksenel_yol, yukseklik=10.0):
    """Eksenel yigina en uste katman ekler."""
    eks = al(agac, eksenel_yol)
    if not (isinstance(eks, dict) and eks.get("tur") == "eksenel"):
        raise DuzenlemeHatasi(_("Katman yalnızca eksenel yığına eklenir."))
    adlar = {k.get("ad") for k in eks.get("katmanlar") or []}
    kopya = copy.deepcopy(agac)
    al(kopya, eksenel_yol).setdefault("katmanlar", []).append(
        {"ad": _tekil_ad(_("katman"), adlar), "yukseklik": float(yukseklik), "icerik": None})
    return kopya


def grup_ekle(agac, tur="donme", ad=None):
    """Bos grup ekler (donme / daldirma)."""
    if tur not in ("donme", "daldirma"):
        raise DuzenlemeHatasi(_("Bilinmeyen grup türü: {tur}").format(tur=tur))
    adlar = {g.get("ad") for g in agac.get("gruplar") or []}
    kopya = copy.deepcopy(agac)
    kopya.setdefault("gruplar", []).append(
        {"ad": _tekil_ad(ad or _("grup"), adlar), "tur": tur,
         "deger": 0.0, "uyeler": []})
    return kopya


# ============================================================================
# silme ve tasima
# ============================================================================

def _bos_yuva_degeri(agac, yuva):
    """Silinen dugumun yerine konan deger (katman icerigi: varsayilan)."""
    if len(yuva) >= 3 and yuva[-1] == "icerik" and yuva[-3] == "katmanlar":
        return None
    return malzeme(BOSLUK)


def sil(agac, yol):
    """Ogeyi siler: liste ogesi listeden cikar, yuvadaki dugum bosluga doner."""
    yol = tuple(yol)
    tur = oge_turu(agac, yol)
    if yol == KOK or tur is None or tur in ("parcalar", "gruplar"):
        raise DuzenlemeHatasi(_("Bu öğe silinemez."))
    if len(yol) >= 2 and yol[-2] == "anahtar":
        return _harf_sil(agac, yol)
    if tur == "dugum":
        return yaz(agac, yol, _bos_yuva_degeri(agac, yol))
    if tur == "parca":
        ad = al(agac, yol).get("ad")
        if ad in bilesen_basvurulari(agac):
            raise DuzenlemeHatasi(_("“{ad}” parçası kullanılıyor; önce başvuruları "
                                    "kaldırın.").format(ad=ad))
    kopya = copy.deepcopy(agac)
    silinen = al(kopya, yol[:-1]).pop(yol[-1])
    if tur == "yerlesim":
        kopya = _uyeyi_cikar(kopya, silinen.get("ad"))
    return kopya


def _harf_sil(agac, yol):
    kafes = al(agac, yol[:-2])
    harf = yol[-1]
    if any(harf in satir for satir in kafes.get("harita") or []):
        raise DuzenlemeHatasi(_("“{harf}” harfi haritada kullanılıyor; önce haritadan "
                                "kaldırın.").format(harf=harf))
    kopya = copy.deepcopy(agac)
    al(kopya, yol[:-1]).pop(harf, None)
    return kopya


def _uyeyi_cikar(agac, ad):
    for g in agac.get("gruplar") or []:
        g["uyeler"] = [u for u in g.get("uyeler") or [] if u != ad]
    return agac


def tasi(agac, kaynak, hedef):
    """
    Surukle-birak: kaynak yuvadaki dugum hedef yuvaya tasinir, kaynak bosalir.
    Yerlesim bir bolgeden digerine (kap ya da halka) de tasinabilir.
    """
    kaynak, hedef = tuple(kaynak), tuple(hedef)
    if kaynak == hedef:
        return copy.deepcopy(agac)
    if oge_turu(agac, kaynak) == "yerlesim":
        return _yerlesimi_tasi(agac, kaynak, hedef)
    if not (yuva_mu(agac, kaynak) and yuva_mu(agac, hedef)) or kaynak == KOK:
        raise DuzenlemeHatasi(_("Bu öğe buraya taşınamaz."))
    if ata_mi(kaynak, hedef):
        raise DuzenlemeHatasi(_("Bir düğüm kendi içine taşınamaz."))
    dugum = al(agac, kaynak)
    if hedef == KOK and (dugum or {}).get("tur") != "kap":
        raise DuzenlemeHatasi(_("Kök yalnızca bir kap olabilir."))
    kopya = yaz(agac, hedef, dugum)
    if ata_mi(hedef, kaynak):
        return kopya            # hedef kaynagin atasiydi: kaynak zaten yok
    return yaz(kopya, kaynak, _bos_yuva_degeri(agac, kaynak))


def _yerlesimi_tasi(agac, kaynak, hedef):
    liste_yolu = bolge_yerlesim_listesi(agac, hedef)
    if ata_mi(kaynak, hedef):
        raise DuzenlemeHatasi(_("Bir düğüm kendi içine taşınamaz."))
    kopya = copy.deepcopy(agac)
    y = al(kopya, kaynak[:-1]).pop(kaynak[-1])
    # kaynak listeden cikinca hedef yolundaki indeksler kayabilir: hedefi
    # yeni kopyada yeniden bul (ayni liste icindeyse sona eklenir).
    ebeveyn = al(kopya, liste_yolu[:-1]) if _yol_hala_gecerli(kaynak, liste_yolu) else None
    if ebeveyn is None:
        raise DuzenlemeHatasi(_("Bu öğe buraya taşınamaz."))
    ebeveyn.setdefault("yerlesimler", []).append(y)
    return kopya


def _yol_hala_gecerli(silinen, yol):
    """silinen liste ogesi yolun uzerindeki bir indeksi kaydiriyor mu?"""
    n = len(silinen) - 1
    if len(yol) > n and yol[:n] == silinen[:n] and isinstance(yol[n], int):
        return yol[n] < silinen[n]
    return True


def sira_tasi(agac, yol, yon):
    """Liste ogesini (halka, yerlesim, katman, parca, grup) yukari/asagi tasir."""
    yol = tuple(yol)
    if oge_turu(agac, yol) not in ("halka", "yerlesim", "katman", "parca", "grup"):
        raise DuzenlemeHatasi(_("Bu öğenin sırası değiştirilemez."))
    liste = al(agac, yol[:-1])
    i, j = yol[-1], yol[-1] + int(yon)
    if not (0 <= j < len(liste)):
        return copy.deepcopy(agac)
    kopya = copy.deepcopy(agac)
    l2 = al(kopya, yol[:-1])
    l2[i], l2[j] = l2[j], l2[i]
    return kopya


# ============================================================================
# yeniden adlandirma, parcaya cikarma, sarmalama
# ============================================================================

def bilesen_basvurulari(agac):
    """Agactaki bilesen dugumlerinin adlari (kume)."""
    adlar = set()

    def gez(d):
        if isinstance(d, dict):
            if d.get("tur") == "bilesen" and d.get("ad"):
                adlar.add(d["ad"])
            for v in d.values():
                gez(v)
        elif isinstance(d, list):
            for v in d:
                gez(v)
    gez(agac)
    return adlar


def _agac_speci(agac):
    """Agaci cekirdek API'sinin bekledigi (gelismis modda) spec'e sarar."""
    return {"kor": {"tur": "agac"}, "geometri": agac}


def _api_adi(agac, tur, eski, yeni):
    """geometri.ad_degistir ile yeni agac (grup uyelikleri, bilesen ve kafes
    basvurulari dahil). Girdi DEGISMEZ."""
    try:
        return geometri.ad_degistir(_agac_speci(agac), tur, eski, yeni)["geometri"]
    except (KeyError, ValueError) as e:
        raise DuzenlemeHatasi(_("Ad değiştirilemedi: {neden}").format(neden=e)) from e


def grup_degeri_yaz(agac, grup, deger):
    """'grup' adli grubun degeri (geometri.grup_degeri_yaz). Girdi DEGISMEZ."""
    try:
        return geometri.grup_degeri_yaz(_agac_speci(agac), grup, deger)["geometri"]
    except KeyError as e:
        raise DuzenlemeHatasi(_("Tanımsız grup: {ad}").format(ad=grup)) from e


def yeniden_adlandir(agac, yol, yeni_ad, kutuphane_adlari=()):
    """
    Gorunen adi degistirir. Yerlesim adi grup uyeliklerinde, parca adi bilesen
    basvurularinda da degisir. Malzeme ve bilesen dugumlerinin 'ad'i bir
    BASVURUDUR; onlar formdan secilir, burada adlandirilmaz.
    """
    yol = tuple(yol)
    yeni_ad = (yeni_ad or "").strip()
    if not ad_gecerli_mi(yeni_ad):
        raise DuzenlemeHatasi(_("Geçersiz ad: boş olamaz ve “/” içeremez."))
    tur = oge_turu(agac, yol)
    oge = al(agac, yol)
    if not isinstance(oge, dict) or tur is None:
        raise DuzenlemeHatasi(_("Bu öğe adlandırılamaz."))
    if tur == "dugum" and oge.get("tur") in ("malzeme", "bilesen"):
        raise DuzenlemeHatasi(_("Malzeme ve bileşen başvurusu adlandırılmaz; "
                                "formdan başka bir içerik seçin."))
    eski = oge.get("ad")
    if tur == "yerlesim":
        if yeni_ad != eski and yeni_ad in yerlesim_adlari(agac):
            raise DuzenlemeHatasi(_("“{ad}” adlı bir yerleşim zaten var.").format(ad=yeni_ad))
        return _api_adi(agac, "yerlesim", eski, yeni_ad)
    if tur == "parca":
        adlar = {p.get("ad") for p in agac.get("parcalar") or []} | set(kutuphane_adlari)
        if yeni_ad != eski and yeni_ad in adlar:
            raise DuzenlemeHatasi(_("“{ad}” adı zaten kullanılıyor.").format(ad=yeni_ad))
        return _api_adi(agac, "parca", eski, yeni_ad)
    if tur == "grup":
        adlar = {g.get("ad") for g in agac.get("gruplar") or []}
        if yeni_ad != eski and yeni_ad in adlar:
            raise DuzenlemeHatasi(_("“{ad}” adlı bir grup zaten var.").format(ad=yeni_ad))
    return alan_yaz(agac, yol, "ad", yeni_ad)


def parcaya_cikar(agac, yol, ad, kutuphane_adlari=()):
    """Secili alt agaci adlandirilmis parcaya cevirir; yuvaya basvuru konur."""
    yol = tuple(yol)
    dugum = al(agac, yol)
    if not yuva_mu(agac, yol) or yol == KOK or not isinstance(dugum, dict):
        raise DuzenlemeHatasi(_("Yalnızca bir yuvadaki düğüm parçaya çıkarılır."))
    if dugum.get("tur") in ("malzeme", "bilesen"):
        raise DuzenlemeHatasi(_("Malzeme ve bileşen zaten tekil başvurudur."))
    adlar = {p.get("ad") for p in agac.get("parcalar") or []} | set(kutuphane_adlari)
    ad = (ad or "").strip()
    if not ad_gecerli_mi(ad) or ad in adlar:
        raise DuzenlemeHatasi(_("Parça adı boş olamaz ve kullanılmamış olmalı."))
    kopya = yaz(agac, yol, {"tur": "bilesen", "ad": ad})
    kopya.setdefault("parcalar", []).append({"ad": ad, "dugum": copy.deepcopy(dugum)})
    return kopya


def sarmala(agac, yol):
    """
    Seciliyi yeni bir kabin ic'ine alir. Kok sarmalaninca yukseklik ve sinir
    yeni koke tasinir (yalniz kokte bulunurlar; §3.6).
    """
    yol = tuple(yol)
    dugum = al(agac, yol)
    if not yuva_mu(agac, yol) or not isinstance(dugum, dict):
        raise DuzenlemeHatasi(_("Yalnızca bir yuvadaki düğüm sarmalanır."))
    kimlik = yeni_id(agac, "kap")
    if yol == KOK:
        ic = {k: copy.deepcopy(v) for k, v in dugum.items()
              if k not in ("yukseklik", "sinir")}
        ic["id"] = ic.get("id") if ic.get("id") != "kok" else yeni_id(agac)
        ic["dis"] = malzeme(BOSLUK)
        yeni = {"tur": "kap", "id": "kok", "kesit": copy.deepcopy(dugum.get("kesit")),
                "ic": ic, "yerlesimler": [], "halkalar": [],
                "yukseklik": dugum.get("yukseklik"),
                "sinir": copy.deepcopy(dugum.get("sinir") or {"yan": "vacuum"})}
        if (yeni["kesit"] or {}).get("sekil") == "kafes_zarfi":
            raise DuzenlemeHatasi(_("Kafes zarflı kök sarmalanamaz; önce kesit "
                                    "şeklini değiştirin."))
        return yaz(agac, yol, yeni)
    sahip = kap_yolu(agac, yol[:-1])
    kesit = copy.deepcopy((al(agac, sahip) or {}).get("kesit")) if sahip else None
    if dugum.get("tur") == "kap":
        kesit = copy.deepcopy(dugum.get("kesit"))
    if not kesit or kesit.get("sekil") in ("kafes_zarfi", "kure"):
        kesit = {"sekil": "silindir", "yaricap": 5.0}
    yeni = {"tur": "kap", "id": kimlik, "kesit": kesit, "ic": copy.deepcopy(dugum),
            "yerlesimler": [], "halkalar": [], "dis": malzeme(BOSLUK)}
    return yaz(agac, yol, yeni)
