# -*- coding: utf-8 -*-
"""
vv/kume.py -- kayitli kriter (benchmark) olcumlerinden V&V ozeti (vv_arayuz.VVOzeti).

Kume: ornekler/kriter_*.json, ornekler/godiva_kriter.json ve ornekler/vv/kriter_*.json
icinden referans.tur == "deney" olup referans.olcum (bu aracin hesabi) bulunanlar.
Hesap-hesap kriterleri (tur = "hesap") kumeye GIRMEZ: E olculmus bir deney degildir.

  vakalar(dosyalar=None, filtre=None) -> [istatistik.Vaka]
  ozet(vakalar=None, filtre=None, uygulama=None, delta_sm=0.05, delta_aoa=0.0) -> VVOzeti
  uygulama(spec, kosu_dizini=None) -> AOA parametreleri (aoa.parametreler)

filtre: {parametre: deger | (deger, ...) | ("aralik", alt, ust)} -- AOA'ya gore alt
kume secimi (6698: USL her AOA icin ayri hesaplanir).
"""

import glob
import json
import os
from collections import Counter

from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici
from cekirdek.uygunluk_denetimi.vv_arayuz import AOA_KATEGORILERI, VVOzeti
from cekirdek.vv import aoa as _aoa
from cekirdek.vv import istatistik as _ist

_log = kaydedici(__name__)

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORNEK = os.path.join(KOK, "ornekler")
SAYISAL = ("zenginlik", "h_x", "ealf")
DELTA_SM_VARSAYILAN = 0.05
DELTA_SM_KAYNAK = (N_("ΔSM = 0.05: NUREG-1718 §6.4.3.3.4 / NUREG-1520 Bl. 5 Ek B'de ek gerekçesiz "
                   "kabul edildiği bildirilen değer (DOĞRULANMADI); alt sınır 0.02 "
                   "(NUREG/CR-6698 §2.4.5)"))
KAYNAK = (N_("NUREG/CR-6698 (2001) yöntemi; kriter modelleri mit-crpg/benchmarks (MIT lisansı) "
          "ve ICSBEP E ± σ (uncertainties.csv)"))


def kriter_dosyalari():
    """Kumeye aday JSON dosyalari (sirali)."""
    yollar = glob.glob(os.path.join(ORNEK, "kriter_*.json"))
    yollar += [os.path.join(ORNEK, "godiva_kriter.json")]
    yollar += glob.glob(os.path.join(ORNEK, "vv", "kriter_*.json"))
    return sorted(y for y in yollar if os.path.exists(y))


def _oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError(_("kriter dosyası okunamadı: %s (%s)") % (yol, e)) from e


def _vaka(yol, ham):
    ref = ham.get("referans") or {}
    olc = ref.get("olcum") or {}
    if ref.get("tur") != "deney" or "k" not in olc:
        return None
    return _ist.Vaka(ad=os.path.basename(yol), k=float(olc["k"]),
                     sigma_calc=float(olc["sigma"]), k_exp=float(ref["k"]),
                     sigma_exp=float(ref["sigma"]), parametreler=dict(ref.get("aoa") or {}),
                     seri=ref.get("seri") or ref.get("kaynak", ""))


def _uyar(vaka, filtre):
    for ad, kosul in (filtre or {}).items():
        deger = vaka.parametreler.get(ad)
        if isinstance(kosul, tuple) and kosul and kosul[0] == "aralik":
            if deger is None or not kosul[1] <= float(deger) <= kosul[2]:
                return False
        elif isinstance(kosul, (tuple, list, set, frozenset)):
            if deger not in kosul:
                return False
        elif deger != kosul:
            return False
    return True


def vakalar(dosyalar=None, filtre=None):
    """Deney kriterlerinden olcumu olanlar -> [Vaka] (filtreye uyanlar)."""
    sonuc = []
    for yol in dosyalar or kriter_dosyalari():
        v = _vaka(yol, _oku(yol))
        if v is None:
            _log.info("V&V kümesine alınmadı (deney değil ya da ölçüm yok): %s", yol)
            continue
        if _uyar(v, filtre):
            sonuc.append(v)
    return sonuc


def _aralik(vlar):
    sonuc = {}
    for ad in SAYISAL:
        degerler = [float(v.parametreler[ad]) for v in vlar if v.parametreler.get(ad) is not None]
        if degerler:
            sonuc[ad] = (min(degerler), max(degerler))
    return sonuc


def _kategorik(vlar):
    sonuc = {}
    for ad in AOA_KATEGORILERI:
        degerler = sorted({v.parametreler[ad] for v in vlar if v.parametreler.get(ad)})
        if degerler:
            sonuc[ad] = tuple(degerler)
    return sonuc


def ozet(vlar=None, filtre=None, uygulama=None, delta_sm=DELTA_SM_VARSAYILAN,
         delta_aoa=0.0, egilim_parametreleri=SAYISAL, n_usl_asgari=_ist.N_USL_ASGARI):
    """Kume -> VVOzeti (NUREG/CR-6698). uygulama verilirse bant yonteminde USL
    uygulamanin parametre degerinde hesaplanir."""
    vlar = vakalar(filtre=filtre) if vlar is None else [v for v in vlar if _uyar(v, filtre)]
    d = _ist.degerlendir(vlar, delta_sm=delta_sm, delta_aoa=delta_aoa,
                         egilim_parametreleri=egilim_parametreleri, uygulama=uygulama,
                         n_usl_asgari=n_usl_asgari)
    neden = d["usl_neden"]
    if d.get("usl_noktasi"):
        neden = _("USL tolerans bandından, %s noktasında") % d["usl_noktasi"]
    norm = d["normallik"]
    return VVOzeti(
        n=d["n"], yontem=d["yontem"], usl=d["usl"], usl_neden=neden, bias=d["bias"],
        bias_kullanilan=d["bias_kullanilan"], delta_sm=delta_sm, delta_aoa=delta_aoa,
        guven=d["guven"], normallestirildi=d["normallestirildi"],
        normallik=None if norm is None else dict(norm),
        egilim=d["egilim"], aralik=_aralik(vlar), aoa_kategorik=_kategorik(vlar),
        seriler=dict(Counter(v.seri for v in vlar)),
        kaynak=_(KAYNAK) + "; " + _(DELTA_SM_KAYNAK))


def uygulama(spec, kosu_dizini=None):
    """Uygulamanin AOA parametreleri (spec + kosu dizini; cikarilamayan yok)."""
    return _aoa.parametreler(spec, kosu_dizini)
