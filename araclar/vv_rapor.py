# -*- coding: utf-8 -*-
"""
araclar/vv_rapor.py -- V&V kumesinin docs/VV*.md tablolarini JSON olcumlerinden uretir
(v3 Y11) ve LEU oksit kafes alt kumesinin C/E grafiklerini cizer.

  python araclar/vv_rapor.py satirlar [--dil tr|en] [desen]   # deney tablosu satirlari
  python araclar/vv_rapor.py aoa [--dil tr|en] [desen]        # AOA tablosu satirlari
  python araclar/vv_rapor.py usl [--dil tr|en]                # alt kume yanlilik/USL tablosu
  python araclar/vv_rapor.py grafik [--cikti D]               # C/E - H/X ve EALF (PNG)
  python araclar/vv_rapor.py guncelle [desen]                 # VV.md + VV.en.md tablolarina yaz

Sayilar dosyalardan okunur; elle yazilmaz (test_benchmark BM4 ayni sayilari arar).
"""

import argparse
import glob
import json
import math
import os
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
ORNEK = os.path.join(KOK, "ornekler")
CIKTI = os.path.expanduser("~/openmc_v3_ciktilar/y11")
PCM = 1e5
EKSI = "−"                       # tipografik eksi (mevcut tablolarla ayni)
LEU_KAFES = {"bolunebilir": "U-235", "fiziksel_bicim": "oksit", "tayf": "termal",
             "zenginlik": ("aralik", 0.0, 10.0)}

METIN = {
    "tr": {"gecti": "geçti", "kaldi": "kaldı", "durum": "durum", "oksit": "oksit",
           "su": "su", "termal": "termal", "heterojen": "heterojen", "normal": "normal",
           "normal_degil": "normal değil", "yok": "yok", "var": "VAR",
           "parametrik_olmayan": "parametrik olmayan", "tolerans_siniri": "tolerans sınırı",
           "tolerans_bandi": "tolerans bandı", "hesaplanamadi": "**hesaplanamadı**"},
    "en": {"gecti": "passed", "kaldi": "failed", "durum": "case", "oksit": "oxide",
           "su": "water", "termal": "thermal", "heterojen": "heterogeneous", "normal": "normal",
           "normal_degil": "not normal", "yok": "none", "var": "YES",
           "parametrik_olmayan": "non-parametric", "tolerans_siniri": "tolerance limit",
           "tolerans_bandi": "tolerance band", "hesaplanamadi": "**not computed**"},
}
KABUL_SIGMA = 3.0                     # VV.md kabul olcutu |C - E| <= 3 sigma


def _isaret(x: float, bicim: str = "%+.0f") -> str:
    return (bicim % x).replace("-", EKSI)


def deney_satiri(goreli: str, ham: Mapping[str, Any], dil: str = "tr") -> str:
    """VV.md deney tablosu satiri (BM4: C %.5f ve parcacik sayisi satirda)."""
    m = METIN[dil]
    ref, olc = ham["referans"], ham["referans"]["olcum"]
    fark = olc["k"] - ref["k"]
    sigma = math.hypot(olc["sigma"], ref["sigma"])
    z = abs(fark) / sigma
    ad = ref["kaynak"].split(";")[0].replace("ICSBEP ", "").split(" (")[0]
    if dil == "en":
        ad = ad.replace("durum", "case")
    return ("| %s | %s | %.4f ± %.4f | %.5f ± %.5f | %s | %.2f | %.5f | %d | %d/%d | %.1f | %s |"
            % (goreli, ad, ref["k"], ref["sigma"], olc["k"], olc["sigma"],
               _isaret(PCM * fark), z, olc["k"] / ref["k"], olc["parcacik"], olc["cevrim"],
               olc["pasif"], olc["sure_s"], m["gecti"] if z <= KABUL_SIGMA else m["kaldi"]))


def aoa_satiri(goreli: str, ham: Mapping[str, Any], dil: str = "tr") -> str:
    m = METIN[dil]
    ref = ham["referans"]
    a = ref["aoa"]
    return "| %s | %s | %s | %.2f | %s | %s | %.3g | %.3g | %s |" % (
        goreli, ref["seri"], a["bolunebilir"], a["zenginlik"],
        m.get(a["fiziksel_bicim"], a["fiziksel_bicim"]), m.get(a["yansitici"], a["yansitici"]),
        a["h_x"], a["ealf"], m.get(a["tayf"], a["tayf"]))


def _anahtar(satir: str) -> str:
    return satir.split("|")[1].strip()


def _tablo_araligi(satirlar: List[str], baslik: str) -> Tuple[int, int]:
    """baslik satirindan sonraki ilk tablonun veri satirlari [bas, son)."""
    if baslik not in satirlar:
        raise ValueError("başlık bulunamadı: %s" % baslik)
    i = satirlar.index(baslik) + 1
    while i < len(satirlar) and not satirlar[i].startswith("|"):
        i += 1
    bas = i + 2                                   # baslik + ayirici satiri
    son = bas
    while son < len(satirlar) and satirlar[son].startswith("|"):
        son += 1
    return bas, son


def tabloya_yerlestir(metin: str, baslik: str, yeni_satirlar: Sequence[str]) -> str:
    """Bolumdeki tabloda ayni dosyanin satirini degistirir; olmayani, anahtari kendisinden
    kucuk son satirin arkasina ekler. Tablo disi metin degismez (YENI metin doner)."""
    satirlar = metin.split("\n")
    bas, son = _tablo_araligi(satirlar, baslik)
    veri = satirlar[bas:son]
    for yeni in yeni_satirlar:
        anahtar = _anahtar(yeni)
        konum = next((i for i, x in enumerate(veri) if _anahtar(x) == anahtar), None)
        if konum is not None:
            veri[konum] = yeni
            continue
        once = [i for i, x in enumerate(veri) if _anahtar(x) < anahtar]
        veri.insert(once[-1] + 1 if once else 0, yeni)
    return "\n".join(satirlar[:bas] + veri + satirlar[son:])


def dosyalar(desen: str = "vv/kriter_lct*.json") -> List[Tuple[str, Dict[str, Any]]]:
    sonuc = []
    for yol in sorted(glob.glob(os.path.join(ORNEK, desen))):
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        if "olcum" in (ham.get("referans") or {}):
            sonuc.append((os.path.relpath(yol, ORNEK), ham))
    return sonuc


def _egilim_metni(egilim: Mapping[str, Mapping[str, Any]], dil: str) -> str:
    m = METIN[dil]
    return ", ".join("%s: %s (t = %.2f)" % (p, m["var"] if e["anlamli"] else m["yok"], e["t"])
                     for p, e in sorted(egilim.items())) or "—"


def usl_satiri(ad: str, d: Mapping[str, Any], dil: str = "tr") -> str:
    """istatistik.degerlendir sonucu -> VV.md USL tablosu satiri."""
    m = METIN[dil]
    norm = d.get("normallik") or {}
    norm_metni = ("W = %.3f, p = %.3f → %s" % (norm["W"], norm["p"],
                                              m["normal"] if norm["normal"] else m["normal_degil"])
                  if norm else "—")
    yontem = m.get(d["yontem"], d["yontem"])
    if d["yontem"] == "parametrik_olmayan" and d.get("guven") is not None:
        yontem += " (β = %%%.1f)" % (100 * d["guven"])
    k_l = "—" if d.get("K_L") is None else "%.4f" % d["K_L"]
    usl = "%.4f" % d["usl"] if d.get("usl") is not None else m["hesaplanamadi"]
    return "| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
        ad, d["n"], _isaret(d["bias"], "%+.5f"), "%.5f" % d.get("S_p", float("nan")),
        norm_metni, _egilim_metni(d["egilim"], dil), yontem, k_l, usl)


ALT_KUMELER = (("U-235, oksit, termal, LEU (LCT-006 + LCT-008)", None),
               ("LCT-006 (TCA)", "LEU-COMP-THERM-006"),
               ("LCT-008 (B&W Core XI)", "LEU-COMP-THERM-008"))


def usl_tablosu(dil: str = "tr", delta_sm: float = 0.05) -> List[str]:
    """LEU oksit kafes alt kumesi ve seri bazinda dokum (ΔSM = 0.05, ΔAOA = 0)."""
    from cekirdek.vv import istatistik, kume
    vlar = kume.vakalar(filtre=LEU_KAFES)
    satirlar = []
    for ad, seri in ALT_KUMELER:
        alt = [v for v in vlar if seri is None or v.seri == seri]
        satirlar.append(usl_satiri(ad, istatistik.degerlendir(alt, delta_sm=delta_sm), dil))
    return satirlar


def grafik(cikti: str = CIKTI) -> List[str]:
    """C/E (± σ) - H/X ve - EALF, LEU oksit kafes alt kumesi; PNG yollari."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cekirdek.vv import kume
    vlar = kume.vakalar(filtre=LEU_KAFES)
    os.makedirs(cikti, exist_ok=True)
    yollar = []
    for par, etiket, log in (("h_x", "H/U-235 (birim hücre)", False),
                             ("ealf", "EALF [eV]", True)):
        fig, ax = plt.subplots(figsize=(7, 4.2))
        for seri, isaret in (("LEU-COMP-THERM-006", "o"), ("LEU-COMP-THERM-008", "s")):
            alt = [v for v in vlar if v.seri == seri]
            ax.errorbar([v.parametreler[par] for v in alt], [v.k / v.k_exp for v in alt],
                        yerr=[math.hypot(v.sigma_calc, v.sigma_exp) for v in alt],
                        fmt=isaret, capsize=3, label=seri)
        ax.axhline(1.0, color="0.5", lw=0.8)
        if log:
            ax.set_xscale("log")
        ax.set_xlabel(etiket)
        ax.set_ylabel("C/E")
        ax.set_title("OpenMC 0.16.0 + ENDF/B-VIII.0 — LEU oksit kafes")
        ax.legend()
        yol = os.path.join(cikti, "ce_%s.png" % par)
        fig.tight_layout()
        fig.savefig(yol, dpi=130)
        plt.close(fig)
        yollar.append(yol)
    return yollar


BELGELER = {"tr": (os.path.join(KOK, "docs", "VV.md"), "## Deney kriterleri (C/E)",
                   "## V&V kümesi: AOA parametreleri"),
            "en": (os.path.join(KOK, "docs", "VV.en.md"), "## Experimental benchmarks (C/E)",
                   "## V&V set: AOA parameters")}


def belgeleri_guncelle(desen: str) -> List[str]:
    """docs/VV.md ve VV.en.md deney ve AOA tablolarina desenin satirlarini yerlestirir."""
    secili = dosyalar(desen)
    yazilan = []
    for dil, (yol, deney_baslik, aoa_baslik) in BELGELER.items():
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        metin = tabloya_yerlestir(metin, deney_baslik, [deney_satiri(g, h, dil) for g, h in secili])
        metin = tabloya_yerlestir(metin, aoa_baslik, [aoa_satiri(g, h, dil) for g, h in secili])
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
        yazilan.append(yol)
    return yazilan


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("is_", choices=("satirlar", "aoa", "usl", "grafik", "guncelle"))
    p.add_argument("desen", nargs="?", default="vv/kriter_lct*.json")
    p.add_argument("--dil", choices=("tr", "en"), default="tr")
    p.add_argument("--cikti", default=CIKTI)
    a = p.parse_args(argv)
    if a.is_ == "grafik":
        satirlar = grafik(a.cikti)
    elif a.is_ == "guncelle":
        satirlar = belgeleri_guncelle(a.desen)
    elif a.is_ == "usl":
        satirlar = usl_tablosu(a.dil)
    else:
        bicim = deney_satiri if a.is_ == "satirlar" else aoa_satiri
        satirlar = [bicim(g, h, a.dil) for g, h in dosyalar(a.desen)]
    sys.stdout.write("\n".join(satirlar) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
