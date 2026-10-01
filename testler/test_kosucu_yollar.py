# -*- coding: utf-8 -*-
"""
 test_kosucu_yollar.py  --  kosucu terminal girisi, alt surec yolu ve
                            guc_yorum yardimcilari (Monte Carlo YOK)

 kosucu hizli suitte %23 kapsaniyordu: terminal girisi (_terminal), openmc alt
 sureci ve tally tablosu yalniz Monte Carlo testlerinde calisiyordu. Burada
 sahte bir 'openmc' calistirilabiliri (sh betigi) ve sahte sonuc_oku ile
 bu yollar nukleer veri olmadan kosulur. D1-A.
"""

import contextlib
import io
import json
import os
import shutil
import stat
import tempfile

from testler.ortak_test import kontrol, ORNEK


def _sahte_openmc(dizin):
    """Cevrim satirlari basan ve statepoint dosyasi yazan sahte openmc."""
    yol = os.path.join(dizin, "openmc")
    with open(yol, "w") as f:
        f.write("#!/bin/sh\n"
                "echo ' Simulating batch 1'\n"
                "echo '  1/1   1.32041'\n"
                "echo '  2/1   1.33000   1.32500 +/- 0.00400'\n"
                "echo sp > statepoint.2.h5\n")
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC)
    return yol


def _spec():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def test_calistir_alt_surec():
    print("\n[KY1] calistir: sahte openmc alt sureci, cevrim satirlari, statepoint")
    from cekirdek import kosucu
    d = tempfile.mkdtemp()
    eski = kosucu.openmc_yolu
    kosucu.openmc_yolu = lambda: _sahte_openmc(d)
    satirlar = []
    try:
        kosu = kosucu.calistir(_spec(), os.path.join(d, "kosu"), veri_kontrolu=False,
                               geri_cagir=lambda s, b: satirlar.append((s, b)))
    finally:
        kosucu.openmc_yolu = eski
    kontrol("basarili, statepoint.2.h5", kosu["basarili"]
            and kosu["statepoint"].endswith("statepoint.2.h5"), "-> %r" % kosu)
    kontrol("iki cevrim satiri ayristirildi", len(kosu["cevrimler"]) == 2
            and kosu["cevrimler"][1]["ortalama"] == 1.325)
    kontrol("geri cagirma her cikti satiri (3)", len(satirlar) == 3)
    kontrol("log yazildi", "Simulating batch" in open(kosu["log"], encoding="utf-8").read())
    shutil.rmtree(d, True)


def _sahte_sonuc(sabit=False):
    from cekirdek import guc
    from testler.test_guc_kor import _kare_2x2_sentetik
    d = guc.dagilim_oku(_kare_2x2_sentetik())
    import pandas as pd
    df = pd.DataFrame({"material": [1], "energy low [eV]": [0.0], "energy high [eV]": [0.625],
                       "nuclide": ["U235"], "score": ["flux"], "mean": [2.0],
                       "std. dev.": [0.1]})
    s = {"mod": "fixed source" if sabit else "eigenvalue",
         "keff": None if sabit else (1.1, 0.001), "cevrim": 60, "pasif": 0 if sabit else 20,
         "parcacik": 100, "entropi": [] if sabit else [5.0 + 0.001 * (i % 3) for i in range(60)],
         "tallyler": {"aki": df}, "malzeme_adlari": {1: "uo2"},
         "kinetik": {"beta_eff": 0.0065, "beta_eff_sapma": 0.0001,
                     "lambda": 2e-5, "lambda_sapma": 1e-7}}
    if not sabit:
        s["guc"] = {"dagilim": d, "faktorler": guc.tepe_faktorleri(d), "korunum": 1e-9,
                    "hedef_payi": 0.9}
    return s


def _terminal(argv, sonuc=None, kosu=None):
    """Terminal girisi; nukleer veri denetimi kapali (CI'da veri yok)."""
    from cekirdek import dogrula, kosucu
    eski = kosucu.calistir, kosucu.sonuc_oku
    eski_kapi = dogrula.kapi
    dogrula.kapi = lambda spec, veri_kontrolu=True: eski_kapi(spec, veri_kontrolu=False)
    cagri = []

    def sahte_calistir(spec, dizin, **k):
        cagri.append(k)
        return kosu or {"basarili": True, "cikis_kodu": 0, "statepoint": "sp.h5",
                        "sure": 1.0, "log": "kosu.log", "cevrimler": []}
    kosucu.calistir = sahte_calistir
    kosucu.sonuc_oku = lambda yol: sonuc
    cikti = io.StringIO()
    try:
        with contextlib.redirect_stdout(cikti):
            kod = kosucu._terminal(argv)
    finally:
        kosucu.calistir, kosucu.sonuc_oku = eski
        dogrula.kapi = eski_kapi
    return kod, cikti.getvalue(), cagri


def _spec_dosyasi(d, degistir=None):
    s = _spec()
    s["guc_dagilimi"]["toplam_guc"] = 1.0e5
    if degistir:
        degistir(s)
    yol = os.path.join(d, "model.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(s, f)
    return yol


def test_terminal_ozdeger_ve_guc():
    print("\n[KY2] Terminal: ozdeger + guc + kinetik + tally, dogrulama bir kez")
    d = tempfile.mkdtemp()
    try:
        kod, cikti, cagri = _terminal([_spec_dosyasi(d), "--dizin", d], _sahte_sonuc())
    finally:
        shutil.rmtree(d, True)
    kontrol("cikis 0", kod == 0, cikti[-300:])
    kontrol("calistir dogrulama=False (cift dogrulama yok)",
            cagri and cagri[0].get("dogrulama") is False, "-> %r" % cagri)
    for parca in ("k-eff    = 1.10000", "β_eff", "güç dağılımı (16 çubuk", "korunumu",
                  "F_ΔH", "uo2", "yakınsama"):
        kontrol("cikti: %s" % parca, parca in cikti)


def test_terminal_sabit_kaynak():
    print("\n[KY3] Terminal: sabit kaynak (siddet 1 ve 1e12)")
    d = tempfile.mkdtemp()
    try:
        kod, cikti, _c = _terminal([_spec_dosyasi(d), "--dizin", d], _sahte_sonuc(True))
        kontrol("siddet 1: kaynak parcacigi basina notu", kod == 0
                and "kaynak parçacığı başınadır" in cikti)

        def guclu(s):
            s["ayarlar"]["mod"] = "fixed source"
            s["ayarlar"]["kaynak"]["kuvvet"] = 1e12
        kod, cikti, _c = _terminal([_spec_dosyasi(d, guclu), "--dizin", d], _sahte_sonuc(True))
        kontrol("siddet 1e12: mutlak birim notu", "mutlak birimdedir" in cikti, cikti[-300:])
    finally:
        shutil.rmtree(d, True)


def test_terminal_secenekler():
    print("\n[KY4] Terminal: yardim, bilinmeyen secenek, --sadece-dogrula, --betik, basarisiz")
    d = tempfile.mkdtemp()
    try:
        kod, cikti, _c = _terminal(["-h"])
        kontrol("yardim 0", kod == 0 and "KULLANIM" in cikti)
        yol = _spec_dosyasi(d)
        kod, cikti, _c = _terminal([yol, "--yok"])
        kontrol("bilinmeyen secenek 2", kod == 2)
        betik = os.path.join(d, "model.py")
        kod, cikti, cagri = _terminal([yol, "--sadece-dogrula", "--betik", betik, "-s", "2"])
        kontrol("sadece dogrula 0, betik yazildi, kosu yok",
                kod == 0 and os.path.isfile(betik) and not cagri)
        kod, cikti, _c = _terminal([yol, "--dizin", d], None,
                                   {"basarili": False, "cikis_kodu": 3, "statepoint": None,
                                    "sure": 0.0, "log": "kosu.log", "cevrimler": []})
        kontrol("kosu basarisiz 1", kod == 1 and "çıkış kodu 3" in cikti)
        kod, cikti, _c = _terminal([yol, "--dizin", d], {"mod": "eigenvalue", "keff": (1.0, 0.1),
                                                         "cevrim": 5, "pasif": 1, "parcacik": 10,
                                                         "entropi": [], "tallyler": {},
                                                         "guc_hata": "bozuk 5"})
        kontrol("guc_hata ve entropi kapali metni", "bozuk 5" in cikti and "entropisi kapalı" in cikti)
    finally:
        shutil.rmtree(d, True)


def test_coklu_tohum_sahte():
    print("\n[KY5] coklu_tohum: 5 tohum varsayilan, hatalar ve sacilma (sahte kosu)")
    from cekirdek import guc, kosucu
    eski = kosucu.calistir, kosucu.sonuc_oku
    sayac = []

    def calistir(spec, dizin, **k):
        t = spec["ayarlar"]["tohum"]
        sayac.append(t)
        if t == 2:
            raise ValueError("dogrulama 2")
        return {"basarili": t != 3, "statepoint": str(t)}

    def sonuc_oku(yol):
        t = int(yol)
        if t == 4:
            return {}
        return {"guc": {"faktorler": {"F_dH": 1.0 + 0.01 * t, "F_q": 2.0 + 0.01 * t}}}
    kosucu.calistir, kosucu.sonuc_oku = calistir, sonuc_oku
    ilerleme = []
    try:
        r = guc.coklu_tohum({"ayarlar": {}}, tempfile.gettempdir(),
                            geri_cagir=lambda i, n, f: ilerleme.append((i, n)))
        tek = guc.coklu_tohum({"ayarlar": {}}, tempfile.gettempdir(), tohumlar=(1,))
    finally:
        kosucu.calistir, kosucu.sonuc_oku = eski
    kontrol("5 tohum denendi", sayac[:5] == [1, 2, 3, 4, 5])
    kontrol("2 basarili (1, 5), 3 hata", r["F_dH"] == [1.01, 1.05] and len(r["ozet"]["hatalar"]) == 3,
            "-> %r" % r)
    kontrol("sacilma hesaplandi", abs(r["ozet"]["F_dH_ort"] - 1.03) < 1e-12
            and "F_q_sacilma" in r["ozet"])
    kontrol("tek tohumda sacilma yok", "F_dH_sacilma" not in tek["ozet"])
    kontrol("ilerleme 3 kez (continue olanlar haric)", len(ilerleme) == 3, "-> %r" % ilerleme)


def test_yorum_ve_ozet_dallari():
    print("\n[KY6] guc_yorum: sinir uyarilari, mutlak, ozet_metni")
    from cekirdek import guc
    from testler.test_guc_kor import _kare_2x2_sentetik
    f = guc.tepe_faktorleri(guc.dagilim_oku(_kare_2x2_sentetik()))
    y = guc.yorumla(dict(f, F_dH=1.8, F_q=2.9, F_q_sapma=0.01, eksenel_dilim=5,
                         F_dH_tepe_yakini=8, F_dH_yanlilik=0.004),
                    {"cubuk_ortalama_W": 100.0, "cubuk_maks_W": 180.0, "hedef_payi": None,
                     "lineer_maks_W_cm": 600.0, "lineer_tepe_kaynagi": "F_q"}, kategori="pwr")
    metin = " ".join(y)
    for parca in ("1.65", "2.3–2.6", "5 eksenel dilim", "yukarı yanlı", "400–500", "eski koşu"):
        kontrol("yorum: %s" % parca, parca in metin)
    kontrol("duz dagilim notu", any("neredeyse düz" in s for s in guc.yorumla(dict(f, F_dH=1.01, F_dH_sapma=0.001))))
    kontrol("faktor yoksa", guc.yorumla(None) == ["Güç dağılımı hesaplanamadı."]
            and guc.ozet_metni(None) == "güç dağılımı yok")
    o = guc.ozet_metni(dict(f, F_q=1.5, F_q_sapma=0.01))
    kontrol("ozet: F_q ve en sicak demet", "F_q = 1.5000" in o and "en sıcak demet" in o, o)


HIZLI = [test_calistir_alt_surec, test_terminal_ozdeger_ve_guc, test_terminal_sabit_kaynak,
         test_terminal_secenekler, test_coklu_tohum_sahte, test_yorum_ve_ozet_dallari]
YAVAS = []
