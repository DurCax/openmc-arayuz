# -*- coding: utf-8 -*-
"""
 test_betik_kacis.py  --  M3: uretilen betikte kullanici adlarinin kacisi (fuzz)

 Paylasilan proje dosyasi GUVENILMEYEN girdidir: malzeme/cubuk/demet/katman/
 tally adlari, model adi ve aciklamasi betige yazilir. Tirnak, uclu tirnak,
 satir sonu, ters bolu, Unicode satir ayiricilari ve __import__ iceren adlarla
 uretilen betik (1) derlenir, (2) calistirilinca hicbir yan etki (isaret
 dosyasi) uretmez, (3) adlari AYNEN korur (malzeme ve hucre adlari).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import os
import random
import tempfile

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik


def _parcalar(isaret):
    kod = "__import__('pathlib').Path(%r).touch()" % isaret
    return ["'", '"', '"""', "'''", "\\", "\\n", "\n", "\r", "\r\n", "\x0b", "\x0c",
            " ", " ", "\x85", "#", "%s", "{}", ")", "]", "\t",
            "\n" + kod + "\n", "'); " + kod + " #", '"""\n' + kod + '\n"""',
            "\\\n" + kod, " " + kod, "ğüşıöç", "a b", "class"]


def _adlar(r, isaret, n):
    parca = _parcalar(isaret)
    return ["x" + "".join(r.choice(parca) for _k in range(r.randint(1, 4))) + str(i)
            for i in range(n)]


def _spec(adlar):
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    for m, ad in zip(spec["malzemeler"], adlar):
        eski = m["ad"]
        sema.malzeme_adini_degistir(spec, eski, ad)
        m["gorunen_ad"] = ad + " gorunen"
    spec["ad"] = adlar[-1]
    spec["aciklama"] = adlar[-2] + "\n" + adlar[-3]
    for i, b in enumerate(spec["kor"]["eksenel"]["bolgeler"]):
        b["ad"] = adlar[i % len(adlar)] + " katman"
    spec["tallyler"] = [sema.tally(adlar[0] + " tally", ["flux"])]
    return spec


def _calistir(metin, dizin):
    import importlib.util
    yol = os.path.join(dizin, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    compile(metin, yol, "exec")
    sm = importlib.util.spec_from_file_location("kacis_%d" % id(metin), yol)
    mo = importlib.util.module_from_spec(sm)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        sm.loader.exec_module(mo)
    finally:
        os.chdir(eski)
    return mo


@gereksinim("R-G-10")
def test_betik_ad_kacisi_fuzz():
    print("\n[M3] BETIK: tehlikeli adlarla 12 fuzz turu; derlenir, yan etki yok, adlar aynen")
    from cekirdek import kod_uret
    r = random.Random(20260930)
    for tur in range(12):
        d = tempfile.mkdtemp(prefix="m3_")
        isaret = os.path.join(d, "ENJEKSIYON")
        adlar = _adlar(r, isaret, 8)
        spec = _spec(adlar)
        try:
            mo = _calistir(kod_uret.uret(spec, "model.py\n" + adlar[1]), d)
            hata = None
        except Exception as e:     # noqa: BLE001 -- test: her turlu hata raporlanir
            mo, hata = None, "%s: %s" % (type(e).__name__, e)
        kontrol("tur %d: betik derlendi ve calisti" % tur, hata is None, "-> %s" % hata)
        kontrol("tur %d: yan etki yok (isaret dosyasi olusmadi)" % tur,
                not os.path.exists(isaret))
        if mo is None:
            continue
        beklenen = sorted(m["gorunen_ad"] for m in spec["malzemeler"])
        kontrol("tur %d: malzeme adlari aynen" % tur,
                sorted(m.name for m in mo.model.materials) == beklenen)
        hucre_adlari = {c.name for c in mo.model.geometry.get_all_cells().values()}
        kontrol("tur %d: katman adlari aynen" % tur,
                all(b["ad"] in hucre_adlari for b in spec["kor"]["eksenel"]["bolgeler"]))
        kontrol("tur %d: tally adi aynen" % tur,
                spec["tallyler"][0]["ad"] in [t.name for t in mo.model.tallies])


@gereksinim("R-G-10")
def test_yorum_ve_dokuman_kacisi():
    print("\n[M3b] yorum_metni ve dokuman_metni tek satir / kapanmayan docstring")
    from cekirdek.geometri.yapici import yorum_metni
    from cekirdek.kod_uret.ad import dokuman_metni
    for metin in _parcalar("/yok"):
        y = "# " + yorum_metni(metin)
        kontrol("yorum tek satir: %r" % metin, len(y.splitlines()) == 1)
        kod = '"""\n%s\n"""\nX = 1\n' % dokuman_metni(metin)
        ns = {}
        exec(compile(kod, "<m3>", "exec"), ns)      # noqa: S102 -- yalniz sabit + atama
        kontrol("docstring kapanmadi: %r" % metin, ns.get("X") == 1)


HIZLI = [test_betik_ad_kacisi_fuzz, test_yorum_ve_dokuman_kacisi]
YAVAS = []
