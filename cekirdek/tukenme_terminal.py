# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_terminal.py  --  python3 -m cekirdek.tukenme komut satiri
================================================================================

 cekirdek/tukenme.py'den bolundu (v3 Y4). Tukenme islevleri tukenme
 modulunden CAGRI ANINDA okunur: testler ve giris.py `tukenme._terminal`
 ile `tukenme.calistir` vb. uzerinden calisir.
================================================================================
"""

import os

from cekirdek.ceviri import _


# ============================================================================
# Terminal
# ============================================================================

# MAKINE ISARETI -- CEVRILMEZ. arayuz/sekme_tukenme._cikti_oku alt surecin
# ciktisini suzerken baslik satirini bu sabitle tanir ("TÜKENME" in satir);
# Ingilizce arayuzde de ayni kalmali (testler/test_ceviri_cekirdek CC5).
KOSU_ISARETI = "TÜKENME"


def kosu_basligi(spec):
    """Terminal ciktisinin baslik satiri: " TÜKENME: <model adi>" (isaret sabit)."""
    return " %s: %s" % (KOSU_ISARETI, spec.get("ad", ""))


def _terminal(argv):
    from cekirdek import tukenme as _tk
    sema = _tk.sema
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m cekirdek.tukenme")
    ap.add_argument("spec")
    ap.add_argument("-s", "--is-parcacigi", type=int, default=None)
    ap.add_argument("--dizin", default=None)
    ap.add_argument("--hazirla", action="store_true",
                    help=_("koşmadan hacim, zincir ve ağır metal bilgisini yazdır"))
    ap.add_argument("--veri-kontrolu-yok", action="store_true",
                    help=_("doğrulamada nüklid/kütüphane denetimini atla"))
    a = ap.parse_args(argv)
    from cekirdek import veri_yolu
    veri_yolu.surece_uygula()   # K2: Veri sayfasi secimi (openmc.deplete ortami okur)

    # libgomp OMP_NUM_THREADS'i KUTUPHANE YUKLENIRKEN okur; openmc.deplete'in
    # ice aktarilmasi kutuphaneyi yukler. Bu yuzden once ortam, sonra import.
    if a.is_parcacigi:
        os.environ["OMP_NUM_THREADS"] = str(a.is_parcacigi)

    import warnings
    warnings.filterwarnings("ignore")
    spec = sema.yukle(a.spec)
    spec.setdefault("tukenme", {})["var"] = True
    zs = _tk.zincir_secimi(spec)
    t = spec["tukenme"]
    print("=" * 74)
    print(kosu_basligi(spec))
    print("=" * 74)
    print(_("  zincir        : %s  (%s)") % (os.path.basename(zs["yol"]), zs["gerekce"]))
    print(_("  fisyon verimi : %s eV (%s spektrum)")
          % (zs["verim_enerjisi"], _tk.spektrum_adi(zs["temel"])))
    print(_("  güç yoğunluğu : %g W/gHM") % float(t["guc_yogunlugu"]))
    print(_("  adımlar       : %s %s  → %d transport")
          % (", ".join("%g" % float(x) for x in t["adimlar"]),
             {"d": _("gün")}.get(t.get("adim_birimi", "d"), t.get("adim_birimi", "d")),
             _tk.transport_sayisi(spec)))
    from cekirdek import tukenme_hacim
    for ad, v in _tk.hacimler(spec).items():
        print(_("  hacim %-10s: %s cm³ [%s] %s") % (ad, ("%.6g" % v["hacim"]) if v["hacim"] else "—",
                                                  tukenme_hacim.yontem_metni(v["yontem"]), v["ayrinti"]))
    if a.hazirla:
        _m, b = _tk.hazirla(spec)
        print(_("  ağır metal    : %.6g g") % b["agir_metal_g"])
        return 0

    dizin = a.dizin or os.path.join(os.path.dirname(os.path.abspath(a.spec)),
                                    (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme")
    from cekirdek import dogrula
    try:
        h5, bilgi = _tk.calistir(spec, dizin, veri_kontrolu=not a.veri_kontrolu_yok)
    except dogrula.DogrulamaHatasi as e:
        print(_("\n  DOĞRULAMA: koşu başlatılmadı (%d hata)") % len(e.bulgular))
        for b in e.tum_bulgular:          # hatalar + uyari/bilgi (tek denetim)
            print("  %s" % b)
        return 2
    for b in bilgi["dogrulama"]:
        print("  %s" % b)
    s = _tk.sonuc_oku(h5, spec)
    print(_("\n  ağır metal: %.6g g") % bilgi["agir_metal_g"])
    print("  %8s %10s %18s" % (_("gün"), "MWd/kg", "k-eff"))
    for z, b, k, sk in zip(s["zaman_d"], s["yanma"], s["k"], s["k_sapma"]):
        print("  %8.2f %10.3f %10.5f ± %.5f" % (z, b, k, sk))
    print(_("\n  sonuç: %s") % h5)
    return 0
