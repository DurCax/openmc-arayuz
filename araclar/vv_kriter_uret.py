# -*- coding: utf-8 -*-
"""
araclar/vv_kriter_uret.py -- V&V kriter kumesini (Dalga S-3) mit-crpg/benchmarks
OpenMC girdilerinden uretir, kosar ve olcumu JSON'a yazar.

KAYNAK VE LISANS
  Modeller: https://github.com/mit-crpg/benchmarks (MIT lisansi, (c) 2011-2024
  Paul Romano ve katkida bulunanlar). E +/- sigma: ayni deponun
  icsbep/icsbep/uncertainties.csv tablosu (ICSBEP degerleri). ICSBEP el
  kitabinin metni YENIDEN DAGITILMAZ (docs/STANDARTLAR.md §6 md. 13): yalniz
  acik model ve yayimlanmis E +/- sigma kullanilir; her JSON kaynagini yazar.

KULLANIM
  python araclar/vv_kriter_uret.py <mit-crpg/benchmarks dizini> [kimlik ...]
      --yalniz-uret   kosmadan JSON yaz
      --is N          OpenMP is parcacigi (varsayilan 12)
  Uretilen dosyalar: ornekler/vv/kriter_<kimlik>.json

Geometri yalniz es merkezli kuresel kabuklarsa kabul edilir (sablon modu
"kuresel"); degilse gerekceyle reddedilir.
"""

import argparse
import datetime
import json
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
HEDEF = os.path.join(KOK, "ornekler", "vv")
SIGMA_HEDEF = 28e-5

# kimlik: (mit-crpg goreli dizin, ICSBEP adi, E, sigma_e, bicim, yansitici, kisa aciklama)
VAKALAR = {
    "imf003": ("ieu-met-fast-003/openmc/case-2", "IEU-MET-FAST-003, durum 2", 1.0, 0.0017,
               "metal", "yok", "Çıplak %36 U-235 metal küresi (basitleştirilmiş model)"),
    "imf004": ("ieu-met-fast-004/openmc/case-2", "IEU-MET-FAST-004, durum 2", 1.0, 0.0030,
               "metal", "grafit", "Grafit yansıtıcılı %36 U-235 metal küresi"),
    "pmf002": ("pu-met-fast-002/openmc", "PU-MET-FAST-002 (Jezebel-240)", 1.0, 0.0020,
               "metal", "yok", "Çıplak Pu küresi, %20 Pu-240"),
    "pmf006": ("pu-met-fast-006/openmc", "PU-MET-FAST-006 (Flattop-Pu)", 1.0, 0.0030,
               "metal", "dogal_u", "Doğal U yansıtıcılı Pu küresi"),
    "pmf008": ("pu-met-fast-008/openmc/case-1", "PU-MET-FAST-008 (Thor), 1B model", 1.0,
               0.0006, "metal", "toryum", "Toryum yansıtıcılı Pu küresi"),
    "pmf011": ("pu-met-fast-011/openmc", "PU-MET-FAST-011", 1.0, 0.0010,
               "metal", "su", "Su yansıtıcılı Pu küresi"),
    "mmf001": ("mix-met-fast-001/openmc", "MIX-MET-FAST-001 (Planet)", 1.0, 0.0016,
               "metal", "heu", "HEU kabuklu Pu küresi"),
    "umf001": ("u233-met-fast-001/openmc", "U233-MET-FAST-001 (Jezebel-233)", 1.0, 0.0010,
               "metal", "yok", "Çıplak U-233 metal küresi"),
    "umf005": ("u233-met-fast-005/openmc/case-2", "U233-MET-FAST-005, durum 2", 1.0, 0.0030,
               "metal", "berilyum", "Berilyum yansıtıcılı U-233 küresi"),
    "umf006": ("u233-met-fast-006/openmc", "U233-MET-FAST-006 (Flattop-23)", 1.0, 0.0014,
               "metal", "dogal_u", "Doğal U yansıtıcılı U-233 küresi"),
    "pci001": ("pu-comp-inter-001/openmc", "PU-COMP-INTER-001 (HISS/HPG)", 1.0, 0.0110,
               "bilesik", "sonsuz", "Pu + polietilen + grafit sonsuz homojen ortam"),
    "usi001": ("u233-sol-inter-001/openmc/case-1", "U233-SOL-INTER-001, durum 1", 1.0,
               0.0083, "cozelti", "berilyum", "Be yansıtıcılı U-233 uranil florür çözeltisi"),
    "hst032": ("heu-sol-therm-032/openmc", "HEU-SOL-THERM-032 (ORNL-10)", 1.0015, 0.0026,
               "cozelti", "yok", "Büyük HEU uranil nitrat çözeltisi küresi"),
    "hst013": ("heu-sol-therm-013/openmc/case-1", "HEU-SOL-THERM-013, durum 1", 1.0012,
               0.0026, "cozelti", "yok", "Yansıtıcısız HEU uranil nitrat küresi"),
    "pst001": ("pu-sol-therm-001/openmc/case-1", "PU-SOL-THERM-001, durum 1", 1.0, 0.0050,
               "cozelti", "su", "Su yansıtıcılı Pu nitrat çözeltisi küresi"),
    "pst021": ("pu-sol-therm-021/openmc/case-3", "PU-SOL-THERM-021, durum 3", 1.0, 0.0065,
               "cozelti", "yok", "Yansıtıcısız Pu nitrat çözeltisi küresi"),
    "ust008": ("u233-sol-therm-008/openmc", "U233-SOL-THERM-008 (ORNL-11)", 1.0006, 0.0029,
               "cozelti", "yok", "Büyük U-233 uranil nitrat küresi"),
    "lst002a": ("leu-sol-therm-002/openmc/case-1", "LEU-SOL-THERM-002, durum 1", 1.0038,
                0.0040, "cozelti", "su", "%4.9 U-235 uranil florür çözeltisi küresi"),
    "lst002b": ("leu-sol-therm-002/openmc/case-2", "LEU-SOL-THERM-002, durum 2", 1.0024,
                0.0037, "cozelti", "yok", "%4.9 U-235 uranil florür çözeltisi küresi"),
    "lst003c": ("leu-sol-therm-003/openmc/case-3", "LEU-SOL-THERM-003, durum 3", 0.9995,
                0.0042, "cozelti", "yok", "%10 U-235 uranil nitrat çözeltisi küresi"),
    "hst009a": ("heu-sol-therm-009/openmc/case-1", "HEU-SOL-THERM-009, durum 1", 0.9990,
                0.0043, "cozelti", "su", "Su yansıtıcılı HEU uranil florür küresi"),
    "pmf018": ("pu-met-fast-018/openmc", "PU-MET-FAST-018", 1.0, 0.0030,
               "metal", "berilyum", "Berilyum yansıtıcılı Pu küresi"),
}

KAYNAK_MODEL = ("mit-crpg/benchmarks (MIT lisansı) icsbep/%s; E ± σ: aynı depo "
                "icsbep/icsbep/uncertainties.csv (ICSBEP değeri)")
LISANS = ("Model girdisi MIT lisanslıdır; ICSBEP el kitabı metni yeniden dağıtılmaz, "
          "yalnız açık model ve yayımlanmış E ± σ kullanılır (STANDARTLAR.md §6 md. 13).")


def _seri(icsbep):
    return icsbep.split(",")[0].split(" (")[0].strip()


def _ham_malzemeler(dizin):
    import openmc
    return list(openmc.Materials.from_xml(os.path.join(dizin, "materials.xml")))


def _dogal_ac(nuklidler):
    """ENDF/B-VIII.0'da dogal element nuklidi (C0) yok: dogal bollukla izotoplara acar."""
    import openmc.data
    sonuc = {}
    for n, d in nuklidler.items():
        if n.endswith("0") and not n[-2].isdigit():
            el = n[:-1]
            izo = {i: b for i, b in openmc.data.NATURAL_ABUNDANCE.items()
                   if "".join(c for c in i if c.isalpha()) == el}
            for i, b in izo.items():
                sonuc[i] = sonuc.get(i, 0.0) + d * b
        else:
            sonuc[n] = sonuc.get(n, 0.0) + d
    return sonuc


def _atom_yogunlugu_ile(spec_mat, ham):
    """Malzemeyi nuklid ao olarak yaz; 'sum' yogunlukta atom/b-cm (kayipsiz)."""
    from cekirdek.sema import bilesen
    yog = _dogal_ac(ham.get_nuclide_atom_densities())
    toplam = float(sum(yog.values()))
    yeni = dict(spec_mat)
    if ham.density_units == "sum":
        yeni["yogunluk"] = {"birim": "atom/b-cm", "deger": toplam}
        yeni["bilesim"] = [bilesen(n, float(d), tur="nuklid") for n, d in sorted(yog.items())]
    else:
        yeni["bilesim"] = [bilesen(n, float(d) / toplam, tur="nuklid")
                           for n, d in sorted(yog.items())]
    return yeni


def _kabuklar(kok):
    if kok.get("tur") != "kap" or (kok.get("kesit") or {}).get("sekil") != "kure":
        raise ValueError("kök küre değil: %s" % kok.get("kesit"))
    if kok.get("yerlesimler"):
        raise ValueError("kürede yerleşim var")
    kabuklar = [{"r": kok["kesit"]["yaricap"], "malzeme": kok["ic"]["ad"]}]
    for h in kok.get("halkalar") or []:
        if h["dis"].get("sekil") != "kure" or h.get("yerlesimler"):
            raise ValueError("eş merkezli küre kabuğu değil: %s" % h["dis"])
        kabuklar.append({"r": h["dis"]["yaricap"], "malzeme": h["icerik"]["ad"]})
    for k in kabuklar:
        if k["malzeme"] in (None, "bosluk", "void"):
            k["malzeme"] = None
    return kabuklar


def spec_uret(depo, kimlik):
    from cekirdek import ice_aktar, sema
    from cekirdek.vv import aoa
    yol, icsbep, e, se, bicim, yansitici, kisa = VAKALAR[kimlik]
    dizin = os.path.join(depo, "icsbep", yol)
    parca, notlar = ice_aktar.geometri_oku(os.path.join(dizin, "geometry.xml"))
    if parca is None:
        raise ValueError("%s: geometri aktarılamadı: %s" % (kimlik, notlar[-1:]))
    ham = _ham_malzemeler(dizin)
    spec = sema.yeni_spec(icsbep)
    spec["malzemeler"] = [_atom_yogunlugu_ile(m, h) for m, h in zip(parca["malzemeler"], ham)]
    kok = parca["geometri"]["kok"]
    spec["kor"]["tur"] = "kuresel"
    spec["kor"]["kabuklar"] = _kabuklar(kok)
    spec["kor"]["sinir"] = {"yan": kok["sinir"]["yan"], "alt": "vacuum", "ust": "vacuum"}
    a = spec["ayarlar"]
    a["parcacik"], a["cevrim"], a["pasif"] = 100000, 200, 50
    a["kaynak"]["tur"] = "kutu"
    # Kutu ilk dolu kabugu kapsar (merkezi bosluklu kabukta +/-1 cm kutu reddedilirdi);
    # "fissionable" kisiti yansiticidaki noktalari eler.
    r = next(k["r"] for k in spec["kor"]["kabuklar"] if k["malzeme"])
    a["kaynak"]["alt"], a["kaynak"]["ust"] = [-r, -r, -r], [r, r, r]
    spec["tallyler"] = [aoa.ealf_tally_tanimi()]
    spec["baslik"] = "%s — %s" % (icsbep, kisa)
    spec["baslik_en"] = "%s (ICSBEP benchmark, V&V set)" % icsbep
    spec["kategori"] = "kriter"
    spec["seviye"] = "ileri"
    spec["aciklama"] = ("ICSBEP kriteri %s: %s. V&V kümesinin (NUREG/CR-6698 yanlılık/USL) "
                        "bir vakası. Deneysel kriter değeri k = %.4f ± %.4f.\nModel: "
                        "mit-crpg/benchmarks icsbep/%s (MIT lisansı) geometri ve atom "
                        "yoğunlukları birebir aktarıldı (eş merkezli küre kabukları)."
                        % (icsbep, kisa, e, se, yol))
    spec["aciklama_en"] = ("ICSBEP benchmark %s, k = %.4f ± %.4f; model from mit-crpg/"
                           "benchmarks (MIT license)." % (icsbep, e, se))
    spec["referans"] = {
        "k": e, "sigma": se, "tur": "deney", "kaynak": "ICSBEP %s" % icsbep,
        "kaynak_model": KAYNAK_MODEL % yol, "lisans": LISANS, "seri": _seri(icsbep),
        "aoa_girdi": {"fiziksel_bicim": bicim, "yansitici": yansitici},
    }
    return spec


def _kutuphane():
    yol = os.environ.get("OPENMC_CROSS_SECTIONS", "")
    return "ENDF/B-VIII.0" if "endfb-viii.0" in yol.lower() else (yol or "bilinmiyor")


def kos(spec, kimlik, is_parcacigi):
    import openmc
    from cekirdek import kosucu
    from cekirdek.vv import aoa
    dizin = os.path.join("/tmp", "vv_kosu", kimlik)
    bas = time.time()
    r = kosucu.calistir(spec, dizin, is_parcacigi=is_parcacigi)
    if not r["basarili"]:
        raise RuntimeError("%s koşusu başarısız: %s" % (kimlik, r.get("log")))
    k, s = kosucu.sonuc_oku(r["statepoint"])["keff"]
    olcum = {"k": round(k, 5), "sigma": round(s, 5), "parcacik": spec["ayarlar"]["parcacik"],
             "cevrim": spec["ayarlar"]["cevrim"], "pasif": spec["ayarlar"]["pasif"],
             "sure_s": round(time.time() - bas, 1), "is_parcacigi": is_parcacigi,
             "openmc": openmc.__version__, "kutuphane": _kutuphane(),
             "tarih": datetime.date.today().isoformat()}
    param = aoa.parametreler(spec, dizin)
    param.update(spec["referans"].get("aoa_girdi") or {})
    return olcum, {a: (round(v, 6) if isinstance(v, float) else v) for a, v in param.items()}


def _yaz(spec, kimlik):
    os.makedirs(HEDEF, exist_ok=True)
    yol = os.path.join(HEDEF, "kriter_%s.json" % kimlik)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return yol


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("depo")
    p.add_argument("kimlikler", nargs="*")
    p.add_argument("--yalniz-uret", action="store_true")
    p.add_argument("--is", type=int, default=12, dest="is_parcacigi")
    a = p.parse_args(argv)
    basarisiz = []
    for kimlik in a.kimlikler or sorted(VAKALAR):
        try:
            _isle(a, kimlik)
        except (RuntimeError, ValueError, OSError) as e:
            print("HATA %s: %s" % (kimlik, e), file=sys.stderr, flush=True)
            basarisiz.append(kimlik)
    if basarisiz:
        print("başarısız vakalar: %s" % ", ".join(basarisiz), file=sys.stderr)
        sys.exit(1)


def _isle(a, kimlik):
    spec = spec_uret(a.depo, kimlik)
    if not a.yalniz_uret:
        olcum, param = kos(spec, kimlik, a.is_parcacigi)
        spec["referans"]["olcum"], spec["referans"]["aoa"] = olcum, param
        print("%s: C = %.5f ± %.5f, %.0f s, %s" % (kimlik, olcum["k"], olcum["sigma"],
                                                   olcum["sure_s"], param), flush=True)
        if olcum["sigma"] > SIGMA_HEDEF:
            print("  UYARI: σc > %.0f pcm" % (1e5 * SIGMA_HEDEF), flush=True)
    print(_yaz(spec, kimlik), flush=True)

if __name__ == "__main__":
    main()
