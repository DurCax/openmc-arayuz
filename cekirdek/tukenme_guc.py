# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_guc.py  --  Tukenmede adim basina pin gucu (yanmaya gore guc dagilimi)
================================================================================

 OPENMC NE SAKLAR (0.16.0 kaynagindan dogrulandi)
   openmc.deplete.Integrator.integrate() her adimin BASINDAKI transportu
   kosar (Integrator._get_bos_data_from_operator) ve hemen ardindan
   CoupledOperator.write_bos_data(step) ile kosu dizinine
   "openmc_simulation_n<step>.h5" statepoint'ini yazar (write_source=False);
   son adimdan sonraki son transport da (final operator evaluation) ayni yolla
   yazilir. Yani N adimlik kosuda n0 ... nN, depletion_results.h5'teki N+1
   zaman noktasina BIRE BIR karsilik gelir. CECM'in duzeltici transportu
   statepoint yazmaz: dosyadaki tally adimin BASI (ongorucu) dagilimidir.
   model.tallies CoupledOperator tarafindan tallies.xml'e yazilir; kurucu.kur'un
   ekledigi "guc_dagilimi" (distribcell + eksenel mesh), "guc_toplam_ref" ve
   "guc_model_toplam" tally'leri boylece HER adimda uretilir. Integrator icin
   ek ayar gerekmez.

 MUTLAK GUC
   Tukenmede guc = guc yogunlugu [W/gHM] × agir metal kutlesi; adimin kaynak
   gucu (Results.get_source_rates, W) toplam_guc olarak guc.mutlak_guc'a
   verilir; hedef payi o adimin kendi tally'lerinden (kappa hedef / model).
   q′ paydasi aktif yukseklik (geometri.hedef_yuksekligi). 2B modelde
   tukenme hacmi 1 cm yukseklik icindir (tukenme.hacimler) -- guc de 1 cm
   basinadir; q′ = W / 1 cm.

 Bu modul YALNIZ okur ve tablo kurar (guc.dagilim_oku, guc.tepe_faktorleri,
 kosucu guc korunumu, guc_tablo.pin_tablosu yeniden kullanilir). Kosuya
 dokunan iki parca tukenme.calistir'dan cagrilir: olcum_spec (guc tally'si
 acik model) ve tukenme_temizlik.onceki_sonucu_temizle (eski adim dosyalari yeni sonuca
 karismasin).
================================================================================
"""

import collections
import copy
import os
import threading
import types

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

IKI_BOYUT_YUKSEKLIGI = 1.0          # cm: 2B tukenme hacmi 1 cm icin (tukenme.hacimler)
_ONBELLEK = collections.OrderedDict()
_KILIT = threading.Lock()
_ONBELLEK_EN_COK = 2


# ============================================================================
# Kosu tarafi (tukenme.calistir cagirir)
# ============================================================================

def olcum_spec(spec):
    """
    Tukenme kosusunun modelini kuracak spec. Guc tally'si kurulabiliyorsa
    (uygunluk.guc_cubuklari) ve tukenme.adim_gucu false degilse
    guc_dagilimi.var acik bir KOPYA; aksi halde spec'in kendisi. Girdi
    degismez. Guc tally'si fizigi degistirmez (yalniz sayar).
    """
    from cekirdek import uygunluk
    if (spec.get("tukenme") or {}).get("adim_gucu") is False:
        return spec
    if (spec.get("guc_dagilimi") or {}).get("var"):
        return spec
    try:
        cubuklar = uygunluk.guc_cubuklari(spec)
    except Exception:
        _log.warning("güç çubukları belirlenemedi; tükenmede adım başına güç yok",
                     exc_info=True)
        return spec
    if not cubuklar:
        return spec
    from cekirdek import guc, sema
    yeni = copy.deepcopy(spec)
    g = yeni.setdefault("guc_dagilimi", {})
    g["var"] = True
    if not sema.guc_hedefleri(g):
        # Hedef secilmemis (ornekte "cubuk": null): butun yakit cubuklari,
        # arayuzun "Butun yakit cubuklari" secimiyle ayni (guc.varsayilan_hedefler).
        g.pop("cubuk", None)
        g.pop("bolge", None)
        g["cubuklar"] = guc.varsayilan_hedefler(yeni)
    return yeni


def olcumlu_hazirla(hazirla, spec):
    """
    hazirla(olcum_spec(spec)); guc tally'si kurulamazsa (ValueError) tukenme
    guc olcumsuz kurulur ve UYARI kaydedilir. Gercek bir model hatasiysa
    ikinci hazirla(spec) ayni hatayi verir (gizlenmez).
    """
    olcum = olcum_spec(spec)
    try:
        return hazirla(olcum)
    except ValueError:
        if olcum is spec:
            raise
        _log.warning("adım başına güç tally'si kurulamadı; tükenme pin gücü olmadan "
                     "koşuyor", exc_info=True)
        return hazirla(spec)


def adim_dosyalari(dizin):
    """[(adim, yol)] sayisal sirayla (tukenme_temizlik.adim_dosyalari)."""
    from cekirdek import tukenme_temizlik
    return tukenme_temizlik.adim_dosyalari(dizin)


# ============================================================================
# Okuma
# ============================================================================

def _yukseklik(spec):
    from cekirdek import geometri
    try:
        h = geometri.hedef_yuksekligi(spec)
    except Exception:
        _log.warning("aktif yükseklik okunamadı; q′ 1 cm başına", exc_info=True)
        h = None
    return float(h) if h else IKI_BOYUT_YUKSEKLIGI


class Iptal(Exception):
    """adim_gucleri iptal edildi (kapanis / yeni proje)."""


def _ozet(dizin):
    """Adimlarin ORTAK summary'si (geometri + distribcell yollari bir kez); yoksa None."""
    import openmc
    yol = os.path.join(dizin, "summary.h5")
    return openmc.Summary(yol) if os.path.isfile(yol) else None


def _adim_oku(yol, ozet=None):
    """Tek adim statepoint'i: kosucu.guc_oku -> (guc | None, hata | None)."""
    import openmc
    from cekirdek import kosucu
    with openmc.StatePoint(yol, autolink=ozet is None) as sp:
        if ozet is not None:
            sp.link_with_summary(ozet)
        g, hata = kosucu.guc_oku(sp)
    if g is None and hata is None:
        return None, _("bu adımda güç dağılımı tally'si yok")
    return g, hata


def _zamanlar(h5, spec):
    """(gun listesi, kaynak gucu listesi W, yanma listesi) -- Results'tan."""
    from cekirdek import tukenme
    r = tukenme._sonuc_kaynagi(h5, spec)[0]
    gun = [float(x) for x in r.get_times(time_units="d")]
    kaynak = [float(x) for x in r.get_source_rates()]
    p = float((spec.get("tukenme") or {}).get("guc_yogunlugu") or 0.0)
    return gun, kaynak, [tukenme.yanma(z, p) for z in gun]


def _kaynak_gucu(kaynak, i):
    """Adim i'nin kaynak gucu [W]. Results N adim icin N oran saklar, N+1 zaman
    noktasi: son nokta (son transport, "final operator evaluation") ayrica bir
    oran tasimaz -- OpenMC o transportu son araligin oraniyla normalize eder
    (Integrator.integrate: res_final = operator(n, source_rate)). Bu yuzden
    son adim son araligin oranini alir."""
    return kaynak[min(i, len(kaynak) - 1)] if kaynak else None


def _adim_kaydi(i, yol, gun, kaynak, yanma, h, ozet=None):
    from cekirdek import guc, guc_tablo
    g, hata = _adim_oku(yol, ozet)
    kayit = {"adim": i, "zaman_d": gun[i], "yanma": yanma[i], "yol": yol, "yukseklik": h,
             "kaynak_W": _kaynak_gucu(kaynak, i),
             "guc": g, "hata": hata, "tablo": [], "mutlak": None}
    if g and g.get("faktorler"):
        m = guc.mutlak_guc(g["faktorler"], kayit["kaynak_W"], h, hedef_payi=g.get("hedef_payi"))
        kayit["mutlak"] = m
        kayit["tablo"] = guc_tablo.pin_tablosu(g["dagilim"], g["faktorler"], m, h)
    return kayit


def imza(dizin, h5, spec):
    """Sonucun icerik imzasi: adim dosyalari (yol, mtime, boyut), sonuc dosyasi ve
    spec. Onbellek ve arayuz ayni anahtari kullanir; dosya degisince yeniden okunur."""
    import json
    adimlar = [(y, os.path.getmtime(y), os.path.getsize(y)) for _i, y in adim_dosyalari(dizin)]
    return (os.path.abspath(dizin), tuple(adimlar), os.path.getmtime(h5), os.path.getsize(h5),
            json.dumps(spec, sort_keys=True, default=str))


def _dondur(x):
    """Sozluk -> MappingProxyType, liste -> demet (ozyinelemeli); diger nesneler aynen.
    Onbellekteki sonuc paylasilir: cagiran onu degistiremez."""
    if isinstance(x, dict):
        return types.MappingProxyType({k: _dondur(v) for k, v in x.items()})
    if isinstance(x, (list, tuple)):
        return tuple(_dondur(v) for v in x)
    return x


def onbellegi_bosalt():
    with _KILIT:
        _ONBELLEK.clear()


def adim_gucleri(dizin, spec, h5=None, iptal=None):
    """
    Tukenme dizinindeki adim basina guc dagilimi; adim dosyasi ya da sonuc
    dosyasi yoksa None.
    DONER (DEGISMEZ: MappingProxyType / demet)
          {"adimlar": ({"adim", "zaman_d", "yanma", "kaynak_W", "yukseklik",
                        "guc" (kosucu.guc_oku sozlugu | None), "hata" (metin | None),
                        "mutlak", "tablo" (guc_tablo satirlari)}, ...),
           "notlar": (metin, ...), "imza": imza()}
    Hatali adim (tally yok / okunamadi) "hata" ile doner, sessizce atlanmaz;
    dosyasi olmayan adim ve sonuctan fazla (eski) dosya notlara yazilir.
    iptal: cagrilabilir; True donerse adimlar arasinda Iptal yukselir.
    Onbellek kilitli LRU; hesap kilit DISINDA yapilir.
    """
    h5 = h5 or os.path.join(dizin, "depletion_results.h5")
    dosyalar = adim_dosyalari(dizin)
    if not dosyalar or not os.path.exists(h5):
        return None
    anahtar = imza(dizin, h5, spec)
    with _KILIT:
        if anahtar in _ONBELLEK:
            _ONBELLEK.move_to_end(anahtar)
            return _ONBELLEK[anahtar]
    sonuc = _dondur(dict(_hesapla(dizin, dosyalar, h5, spec, iptal), imza=anahtar))
    with _KILIT:
        _ONBELLEK[anahtar] = sonuc
        _ONBELLEK.move_to_end(anahtar)
        while len(_ONBELLEK) > _ONBELLEK_EN_COK:
            _ONBELLEK.popitem(last=False)
    return sonuc


def _notlar_dosya(dosyalar, gun):
    notlar = []
    fazla = [i for i, _y in dosyalar if i >= len(gun)]
    if fazla:
        notlar.append(_("Sonuç dosyasında karşılığı olmayan adım dosyaları yok sayıldı "
                        "(önceki koşudan kalmış): %s") % ", ".join(str(i) for i in fazla))
    var = {i for i, _y in dosyalar}
    eksik = [i for i in range(len(gun)) if i not in var]
    if eksik:
        notlar.append(_("Güç dosyası bulunmayan adımlar: %s") % ", ".join(str(i) for i in eksik))
    return notlar


def _hesapla(dizin, dosyalar, h5, spec, iptal=None):
    gun, kaynak, yanma = _zamanlar(h5, spec)
    h = _yukseklik(spec)
    notlar = _notlar_dosya(dosyalar, gun)
    ozet = _ozet(dizin)
    adimlar = []
    for i, yol in dosyalar:
        if iptal is not None and iptal():
            raise Iptal()
        if i >= len(gun):
            continue
        try:
            adimlar.append(_adim_kaydi(i, yol, gun, kaynak, yanma, h, ozet))
        except Exception as e:
            _log.exception("tükenme adımı %d gücü okunamadı (%s)", i, yol)
            adimlar.append({"adim": i, "zaman_d": gun[i], "yanma": yanma[i], "yol": yol,
                            "yukseklik": h, "kaynak_W": None, "guc": None, "hata": str(e),
                            "tablo": [], "mutlak": None})
    hatali = [a["adim"] for a in adimlar if a["hata"]]
    if hatali:
        notlar.append(_("Güç tablosu okunamayan adımlar: %s")
                      % ", ".join(str(i) for i in hatali))
    if h == IKI_BOYUT_YUKSEKLIGI and not _uc_boyut(adimlar):
        notlar.append(_("2B model: güç ve q′ 1 cm yükseklik başınadır (tükenme hacmi gibi)."))
    return {"adimlar": adimlar, "notlar": notlar, "iki_boyut": h == IKI_BOYUT_YUKSEKLIGI
            and not _uc_boyut(adimlar)}


def _uc_boyut(adimlar):
    return any((a.get("guc") or {}).get("faktorler", {}).get("eksenel_dilim", 1) > 1
               for a in adimlar if a.get("guc"))


# ============================================================================
# Seriler ve disa aktarma
# ============================================================================

def gecerli_adimlar(sonuc):
    """Tablosu olan adimlar."""
    return [a for a in (sonuc or {}).get("adimlar") or [] if a["tablo"]]


def pin_serisi(sonuc, anahtar):
    """Secili pin icin [{"adim", "yanma", "zaman_d", "bagil", "sigma", "q", "tepe_q"}]."""
    from cekirdek import guc_tablo
    seri = []
    for a in gecerli_adimlar(sonuc):
        r = guc_tablo.satir_bul(a["tablo"], anahtar)
        if r is not None:
            seri.append({"adim": a["adim"], "yanma": a["yanma"], "zaman_d": a["zaman_d"],
                         "bagil": r["bagil"], "sigma": r["sigma"], "q": r["q"],
                         "tepe_q": r["tepe_q"]})
    return seri


def faktor_serisi(sonuc):
    """Adim basina [{"adim", "zaman_d", "yanma", "F_dH", "F_dH_sapma", "F_q",
    "F_q_sapma", "sicak_cubuk", "lineer_maks"}]."""
    seri = []
    for a in gecerli_adimlar(sonuc):
        f = a["guc"]["faktorler"]
        seri.append({"adim": a["adim"], "zaman_d": a["zaman_d"], "yanma": a["yanma"],
                     "F_dH": f["F_dH"], "F_dH_sapma": f["F_dH_sapma"],
                     "F_q": f.get("F_q"), "F_q_sapma": f.get("F_q_sapma"),
                     "sicak_cubuk": f["sicak_cubuk"],
                     "lineer_maks": (a["mutlak"] or {}).get("lineer_maks_W_cm")})
    return seri


# Dosya sutun anahtarlari sabittir (cevrilmez; bkz. guc_tablo._TEMEL_SUTUNLAR).
_ADIM_SUTUNLARI = ("adim", "zaman_gun", "yanma_MWd_kg")


def _bas():
    return list(_ADIM_SUTUNLARI)


def satirlar(sonuc):
    """Adim × pin: baslik + satirlar (sayilar float)."""
    from cekirdek import guc_tablo
    adimlar = gecerli_adimlar(sonuc)
    if not adimlar:
        return []
    iki = bool((sonuc or {}).get("iki_boyut"))
    cikti = [_bas() + guc_tablo.basliklar(adimlar[0]["tablo"], iki)]
    for a in adimlar:
        for s in guc_tablo.satirlar(a["tablo"], iki)[1:]:
            cikti.append([a["adim"], a["zaman_d"], a["yanma"]] + s)
    return cikti


def csv_metni(sonuc):
    """Adim × pin CSV (ondalik nokta, repr hassasiyeti)."""
    from cekirdek.guc_tablo import satirlar_csv
    return satirlar_csv(satirlar(sonuc))


def faktor_satirlari(sonuc):
    """Adim basina tepe faktorleri: baslik + satirlar."""
    cikti = [_bas() + ["F_dH", "F_dH_sigma", "F_q", "F_q_sigma", "q_maks_W_cm"]]
    for x in faktor_serisi(sonuc):
        cikti.append([x["adim"], x["zaman_d"], x["yanma"], x["F_dH"], x["F_dH_sapma"],
                      x["F_q"], x["F_q_sapma"], x["lineer_maks"]])
    return cikti


def faktor_csv_metni(sonuc):
    from cekirdek.guc_tablo import satirlar_csv
    return satirlar_csv(faktor_satirlari(sonuc))
