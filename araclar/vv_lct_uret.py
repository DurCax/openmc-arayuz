# -*- coding: utf-8 -*-
"""
araclar/vv_lct_uret.py -- LEU oksit kafes V&V vakalarini (v3 Y11) uretir, Y10 kosu
kuyruguyla SIRALI kosar ve olcumu JSON'a yazar.

KAYNAKLAR: cekirdek/vv/lct.py basligi (TCA: JAERI 1254; LCT-008: mit-crpg/benchmarks,
MIT lisansi). ICSBEP el kitabi metni kullanilmaz ve yeniden dagitilmaz.

KULLANIM
  python araclar/vv_lct_uret.py tca [no ...]            # LCT-006 durumlari (vars. hepsi)
  python araclar/vv_lct_uret.py tca 1 --varyant alt_tapa --cikti <dizin>
  python araclar/vv_lct_uret.py lct008 <benchmarks dizini> [durum ...]
      --yalniz-uret     kosmadan JSON yaz
      --yeniden         olcumu olan dosyayi da yeniden kos
      --is N            OpenMP is parcacigi (varsayilan 6)
      --kosu-kok D      kosu dizinlerinin koku (vars. ~/openmc_v3_ciktilar/y11/kosu)
      --cikti D         JSON hedef dizini (vars. ornekler/vv; varyantlar icin baska dizin)
  Uretilen dosyalar: ornekler/vv/kriter_lct006_NN.json, kriter_lct008_NN.json
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
HEDEF = os.path.join(KOK, "ornekler", "vv")
KOSU_KOK = os.path.expanduser("~/openmc_v3_ciktilar/y11/kosu")
VARSAYILAN_IS = 6                     # ORTAK_KURALLAR md. 3
SIGMA_HEDEF = 50e-5                   # sigma_c << sigma_e (200 pcm TCA, 120 pcm LCT-008)

_log = logging.getLogger("vv_lct_uret")


def dosya_adi(seri: str, no: int) -> str:
    """'lct006', 3 -> 'kriter_lct006_03.json'."""
    return "kriter_%s_%02d.json" % (seri, int(no))


def _kutuphane() -> str:
    yol = os.environ.get("OPENMC_CROSS_SECTIONS", "")
    return "ENDF/B-VIII.0" if "endfb-viii.0" in yol.lower() else (yol or "bilinmiyor")


def olcum_ekle(spec: Dict[str, Any], keff: Tuple[float, float], sure_s: float,
               is_parcacigi: int, param: Dict[str, Any]) -> Dict[str, Any]:
    """YENI spec: referans.olcum ve referans.aoa doldurulmus (girdi degismez)."""
    import openmc
    a = spec["ayarlar"]
    ref = dict(spec["referans"])
    ref["olcum"] = {"k": round(keff[0], 5), "sigma": round(keff[1], 5),
                    "parcacik": a["parcacik"], "cevrim": a["cevrim"], "pasif": a["pasif"],
                    "sure_s": round(sure_s, 1), "is_parcacigi": is_parcacigi,
                    "openmc": openmc.__version__, "kutuphane": _kutuphane(),
                    "tarih": datetime.date.today().isoformat()}
    birlesik = dict(param)
    birlesik.update(ref.get("aoa_girdi") or {})
    birlesik.pop("h_x_not", None)
    ref["aoa"] = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in birlesik.items()}
    return dict(spec, referans=ref)


def yaz(spec: Dict[str, Any], yol: str) -> str:
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(gecici, yol)            # yarim yazilmis JSON kalmaz
    return yol


def _olcumlu_mu(yol: str) -> bool:
    if not os.path.exists(yol):
        return False
    with open(yol, encoding="utf-8") as f:
        return "olcum" in (json.load(f).get("referans") or {})


def isler_kur(uretilenler: List[Tuple[str, Dict[str, Any]]], is_parcacigi: int,
              kosu_kok: str) -> list:
    """(hedef yol, spec) -> [KosuIsi]; sonuc kancasi olcumu dosyaya yazar."""
    from cekirdek import kosucu, kuyruk, sema
    from cekirdek.vv import aoa
    isler = []
    for yol, spec in uretilenler:
        tam = sema.tamamla(spec)

        def kanca(sp: str, is_: Any, _yol: str = yol, _spec: Dict[str, Any] = spec,
                  _tam: Dict[str, Any] = tam) -> Dict[str, Any]:
            keff = kosucu.sonuc_oku(sp)["keff"]
            param = aoa.parametreler(_tam, is_.dizin)
            sure = time.time() - os.path.getmtime(os.path.join(is_.dizin, "model.xml"))
            yaz(olcum_ekle(_spec, keff, sure, is_parcacigi, param), _yol)
            _log.info("%s: C = %.5f ± %.5f (%.0f s) -> %s", os.path.basename(_yol),
                      keff[0], keff[1], sure, _yol)
            if keff[1] > SIGMA_HEDEF:
                _log.warning("%s: σc %.0f pcm > %.0f pcm", _yol, 1e5 * keff[1],
                             1e5 * SIGMA_HEDEF)
            return {"keff": keff}

        ad = os.path.splitext(os.path.basename(yol))[0]
        isler.append(kuyruk.KosuIsi(ad=ad, dizin=kuyruk.ayri_dizin(kosu_kok, ad), spec=tam,
                                    is_parcacigi=is_parcacigi, sonuc_kancasi=kanca))
    return isler


AOA_AYAR = (20000, 60, 20)            # EALF icin kisa kosu (vv_kriter_uret.AOA_AYAR ile ayni)


def aoa_tamamla(uretilenler: List[Tuple[str, Dict[str, Any]]], is_parcacigi: int,
                kosu_kok: str) -> List[str]:
    """Olcumu olup AOA'sinda EALF/tayf eksik dosyalar: EALF tally'li kisa kosu ile
    referans.aoa tamamlanir; k olcumu (referans.olcum) DEGISMEZ. DONER: guncellenenler."""
    from cekirdek import kuyruk, sema
    from cekirdek.vv import aoa
    hedefler = []
    for yol, spec in uretilenler:
        if not os.path.exists(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        ref = ham.get("referans") or {}
        if "olcum" not in ref or "tayf" in (ref.get("aoa") or {}):
            continue
        kisa = sema.tamamla(spec)
        kisa["ayarlar"]["parcacik"], kisa["ayarlar"]["cevrim"], kisa["ayarlar"]["pasif"] = AOA_AYAR
        hedefler.append((yol, ham, kisa))
    with kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=is_parcacigi) as k:
        kimlikler = [(k.ekle(kuyruk.KosuIsi(
            ad="aoa_" + os.path.basename(y), spec=kisa, is_parcacigi=is_parcacigi,
            dizin=kuyruk.ayri_dizin(kosu_kok, "aoa_" + os.path.basename(y)))), y, ham, kisa)
            for y, ham, kisa in hedefler]
        k.baslat()
        k.bekle(zaman_asimi=None)
        guncel = []
        for kimlik, yol, ham, kisa in kimlikler:
            d = k.durum(kimlik)
            if d.asama != kuyruk.Asama.BITTI:
                _log.error("%s EALF koşusu: %s %s", yol, d.asama.value, d.hata or "")
                continue
            param = aoa.parametreler(kisa, d.dizin)
            param.update(ham["referans"].get("aoa_girdi") or {})
            param.pop("h_x_not", None)
            ref = dict(ham["referans"], aoa={a: (round(v, 6) if isinstance(v, float) else v)
                                             for a, v in param.items()},
                       aoa_not=("EALF %d parçacık × %d çevrim kısa koşusundan; k ölçümü "
                                "(olcum) ayrı referans koşusudur." % AOA_AYAR[:2]))
            guncel.append(yaz(dict(ham, referans=ref, tallyler=kisa["tallyler"]), yol))
    return guncel


def kos(isler: list, is_parcacigi: int) -> List[str]:
    """Y10 kuyrugu, en_fazla_paralel=1 (sirali). DONER: basarisiz is adlari."""
    from cekirdek import kuyruk

    def dinle(d: Any) -> None:
        if d.bitti_mi:
            _log.info("%s: %s %s", d.ad, d.asama.value, d.hata or "")

    with kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=is_parcacigi) as k:
        k.dinleyici_ekle(dinle)
        kimlikler = [k.ekle(i) for i in isler]
        k.baslat()
        k.bekle(zaman_asimi=None)
        return [k.durum(x).ad for x in kimlikler if k.durum(x).asama != kuyruk.Asama.BITTI]


def _tca_uret(a: argparse.Namespace) -> List[Tuple[str, Dict[str, Any]]]:
    from cekirdek.vv import lct
    nolar = [int(x) for x in a.durumlar] or [d.no for d in lct.TCA_DURUMLARI]
    return [(os.path.join(a.cikti, dosya_adi("lct006", no)), lct.tca_spec(no, a.varyant))
            for no in nolar]


def _lct008_uret(a: argparse.Namespace) -> List[Tuple[str, Dict[str, Any]]]:
    from cekirdek.vv import lct008
    if not a.durumlar:
        raise SystemExit("lct008: önce mit-crpg/benchmarks dizini, sonra durumlar")
    depo, nolar = a.durumlar[0], [int(x) for x in a.durumlar[1:]] or list(lct008.DURUMLAR)
    return [(os.path.join(a.cikti, dosya_adi("lct008", no)), lct008.spec(depo, no))
            for no in nolar]


URETICILER: Dict[str, Callable[[argparse.Namespace], List[Tuple[str, Dict[str, Any]]]]] = {
    "tca": _tca_uret, "lct008": _lct008_uret}


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("seri", choices=sorted(URETICILER))
    p.add_argument("durumlar", nargs="*")
    p.add_argument("--varyant", default=None)
    p.add_argument("--yalniz-uret", action="store_true")
    p.add_argument("--aoa-tamamla", action="store_true",
                   help="olcumlu dosyada eksik EALF/tayf: kisa kosuyla tamamla (k degismez)")
    p.add_argument("--yeniden", action="store_true")
    p.add_argument("--is", type=int, default=VARSAYILAN_IS, dest="is_parcacigi")
    p.add_argument("--kosu-kok", default=KOSU_KOK)
    p.add_argument("--cikti", default=HEDEF)
    a = p.parse_args(argv)
    uretilenler = URETICILER[a.seri](a)
    if a.aoa_tamamla:
        for yol in aoa_tamamla(uretilenler, a.is_parcacigi, a.kosu_kok):
            _log.info("AOA tamamlandı: %s", yol)
        return 0
    if a.yalniz_uret:
        for yol, spec in uretilenler:
            _log.info("%s", yaz(spec, yol))
        return 0
    kosulacak = [(y, s) for y, s in uretilenler if a.yeniden or not _olcumlu_mu(y)]
    _log.info("%d vaka koşulacak (%d atlandı: ölçümü var)", len(kosulacak),
              len(uretilenler) - len(kosulacak))
    basarisiz = kos(isler_kur(kosulacak, a.is_parcacigi, a.kosu_kok), a.is_parcacigi)
    if basarisiz:
        _log.error("başarısız: %s", ", ".join(basarisiz))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
