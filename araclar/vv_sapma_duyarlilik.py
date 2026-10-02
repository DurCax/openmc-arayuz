# -*- coding: utf-8 -*-
"""
araclar/vv_sapma_duyarlilik.py -- PU-MET-FAST-008 ve U233-SOL-INTER-001 sapmalarinin
model duyarlilik kosulari (v3 Y11). Tek kutuphane (ENDF/B-VIII.0) oldugu icin
nukleer veri degistirilmez; yalniz MODEL varyantlari kosulur:

  pmf008_1b_ozgun   mit-crpg case-1 (1B kure) OZGUN OpenMC girdisi  -> arac esdegerligi
  pmf008_2b_ozgun   mit-crpg case-2 (2B: kure + Th silindir) OZGUN   -> 1B basitlestirme etkisi
  usi001_ozgun      mit-crpg case-1 OZGUN girdisi                    -> arac esdegerligi
  usi001_sab_h_yok  cozeltide H S(a,b) yok (serbest gaz)             -> termal sacilma etkisinin ust siniri
  usi001_sab_be_yok Be yansiticida S(a,b) yok                        -> Be termal sacilma etkisi
  usi001_300k       butun malzemeler 300 K (interpolasyon)           -> sicaklik duyarliligi

KULLANIM
  python araclar/vv_sapma_duyarlilik.py <mit-crpg/benchmarks> [varyant ...]
      --is N (vars. 6), --kosu-kok D, --sonuc D (JSON ozet)
Kosular Y10 kuyruguyla SIRALI; sonuc <sonuc>/sapma_duyarlilik.json'a eklenir.
"""

import argparse
import copy
import json
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
CIKTI = os.path.expanduser("~/openmc_v3_ciktilar/y11")
VARSAYILAN_IS = 6
OZGUN_KOSU = (100000, 200, 50)          # v2 olcumleriyle ayni istatistik
USI_KOSU = (200000, 200, 50)            # v2 usi001 ayari (vv_kriter_uret.KOSU_AYARI)
SICAKLIK_300K = 300.0

_log = logging.getLogger("vv_sapma_duyarlilik")


def _ornek(ad: str) -> Dict[str, Any]:
    with open(os.path.join(KOK, "ornekler", "vv", ad), encoding="utf-8") as f:
        return json.load(f)


def sab_kaldir(spec: Dict[str, Any], malzeme: str) -> Dict[str, Any]:
    """YENI spec: malzemenin S(a,b) listesi bos (girdi degismez)."""
    yeni = copy.deepcopy(spec)
    adlar = [m["ad"] for m in yeni["malzemeler"]]
    if malzeme not in adlar:
        raise ValueError("malzeme yok: %s (var: %s)" % (malzeme, adlar))
    for m in yeni["malzemeler"]:
        if m["ad"] == malzeme:
            m["sab"] = []
    return yeni


def sicaklik_ata(spec: Dict[str, Any], kelvin: float) -> Dict[str, Any]:
    """YENI spec: butun malzemeler kelvin sicakliginda."""
    yeni = copy.deepcopy(spec)
    for m in yeni["malzemeler"]:
        m["sicaklik"] = float(kelvin)
    return yeni


def _usi_spec() -> Dict[str, Any]:
    from cekirdek import sema
    return sema.tamamla(_ornek("kriter_usi001.json"))


SPEC_VARYANTLARI: Dict[str, Callable[[], Dict[str, Any]]] = {
    "usi001_sab_h_yok": lambda: sab_kaldir(_usi_spec(), "ieu_flouride_solution"),
    "usi001_sab_be_yok": lambda: sab_kaldir(_usi_spec(), "beryllium_reflector"),
    "usi001_300k": lambda: sicaklik_ata(_usi_spec(), SICAKLIK_300K),
}
OZGUN = {"pmf008_1b_ozgun": ("pu-met-fast-008/openmc/case-1", OZGUN_KOSU),
         "pmf008_2b_ozgun": ("pu-met-fast-008/openmc/case-2", OZGUN_KOSU),
         "usi001_ozgun": ("u233-sol-inter-001/openmc/case-1", USI_KOSU)}


def ozgun_model_yaz(depo: str, goreli: str, ayar: tuple, dizin: str) -> None:
    """mit-crpg girdisini (geometri/malzeme/ayar XML) model.xml'e cevirir; yalniz
    parcacik/cevrim/pasif degisir (kaynak tanimi ozgun)."""
    import openmc
    kaynak = os.path.join(depo, "icsbep", goreli)
    model = openmc.Model.from_xml(os.path.join(kaynak, "geometry.xml"),
                                  os.path.join(kaynak, "materials.xml"),
                                  os.path.join(kaynak, "settings.xml"))
    model.settings.particles, model.settings.batches, model.settings.inactive = ayar
    os.makedirs(dizin, exist_ok=True)
    model.export_to_model_xml(os.path.join(dizin, "model.xml"))


def isler(depo: str, adlar: List[str], is_parcacigi: int, kosu_kok: str) -> list:
    from cekirdek import kuyruk
    sonuc = []
    for ad in adlar:
        dizin = kuyruk.ayri_dizin(kosu_kok, "sapma_" + ad)
        if ad in OZGUN:
            goreli, ayar = OZGUN[ad]
            ozgun_model_yaz(depo, goreli, ayar, dizin)
            spec = None
        elif ad in SPEC_VARYANTLARI:
            spec = SPEC_VARYANTLARI[ad]()
        else:
            raise SystemExit("bilinmeyen varyant: %s" % ad)
        sonuc.append(kuyruk.KosuIsi(ad=ad, dizin=dizin, spec=spec, is_parcacigi=is_parcacigi,
                                    dogrulama=spec is not None))
    return sonuc


def _kaydet(yol: str, kayit: Dict[str, Any]) -> None:
    mevcut: Dict[str, Any] = {}
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            mevcut = json.load(f)
    mevcut.update(kayit)
    with open(yol + ".tmp", "w", encoding="utf-8") as f:
        json.dump(mevcut, f, ensure_ascii=False, indent=2)
    os.replace(yol + ".tmp", yol)


def main(argv: Optional[List[str]] = None) -> int:
    from cekirdek import kuyruk
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("depo")
    p.add_argument("varyantlar", nargs="*")
    p.add_argument("--is", type=int, default=VARSAYILAN_IS, dest="is_parcacigi")
    p.add_argument("--kosu-kok", default=os.path.join(CIKTI, "kosu"))
    p.add_argument("--sonuc", default=CIKTI)
    a = p.parse_args(argv)
    adlar = a.varyantlar or sorted(OZGUN) + sorted(SPEC_VARYANTLARI)
    hedef = os.path.join(a.sonuc, "sapma_duyarlilik.json")
    basarisiz = []
    with kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=a.is_parcacigi) as k:
        kimlikler = [k.ekle(i) for i in isler(a.depo, adlar, a.is_parcacigi, a.kosu_kok)]
        k.baslat()
        k.bekle(zaman_asimi=None)
        for x in kimlikler:
            d = k.durum(x)
            if d.asama != kuyruk.Asama.BITTI or not d.k:
                basarisiz.append(d.ad)
                _log.error("%s: %s %s", d.ad, d.asama.value, d.hata or "")
                continue
            _kaydet(hedef, {d.ad: {"k": round(d.k[0], 5), "sigma": round(d.k[1], 5),
                                   "sure_s": round((d.bitis or 0) - (d.baslangic or 0), 1),
                                   "is_parcacigi": a.is_parcacigi, "dizin": d.dizin}})
            _log.info("%s: k = %.5f ± %.5f", d.ad, d.k[0], d.k[1])
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
