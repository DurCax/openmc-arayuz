# -*- coding: utf-8 -*-
"""
test_eksik_araclar.py -- araclar/ eksikleri (Dalga 4 oncesi).

  [EA1] araclar/vv_kriter_uret.py: kriteri yeniden uretirken dosyadaki elle
        yazilmis baslik_en / aciklama_en (ve diger *_en) alanlari KORUNUR.
  [EA2] araclar/ekran_turu.py --dil tr|en: secenek, dosya adi soneki, EN
        katalogla calisip cikista Turkceye donus.
  [EA3] README.md / README.en.md: "Önce çiz" ve "Bilinen tuzaklar" kisa ozet +
        kilavuz baglantisi (uzun bolum kilavuzda).
"""

import importlib.util
import json
import os
import re
import tempfile

from testler.ortak_test import kontrol, KOK, ORNEK


def _arac(ad):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "araclar", ad + ".py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_vv_kriter_en_alanlari_korunur():
    print("\n[EA1] vv_kriter_uret: yeniden uretimde *_en alanlari korunur")
    vk = _arac("vv_kriter_uret")
    with open(os.path.join(ORNEK, "vv", "kriter_pmf002.json"), encoding="utf-8") as f:
        mevcut = json.load(f)
    uretilen = dict(mevcut, baslik_en="PU-MET-FAST-002 (ICSBEP benchmark, V&V set)",
                    aciklama_en="otomatik metin", baslik="yeni TR baslik")
    with tempfile.TemporaryDirectory() as d:
        eski_hedef = vk.HEDEF
        vk.HEDEF = d
        try:
            yol = os.path.join(d, "kriter_pmf002.json")
            with open(yol, "w", encoding="utf-8") as f:
                json.dump(mevcut, f, ensure_ascii=False)
            vk._yaz(uretilen, "pmf002")
            with open(yol, encoding="utf-8") as f:
                yazilan = json.load(f)
            vk._yaz(dict(uretilen), "yeni_vaka")
            with open(os.path.join(d, "kriter_yeni_vaka.json"), encoding="utf-8") as f:
                yeni = json.load(f)
        finally:
            vk.HEDEF = eski_hedef
    kontrol("baslik_en korundu", yazilan["baslik_en"] == mevcut["baslik_en"],
            "-> %s" % yazilan["baslik_en"])
    kontrol("aciklama_en korundu", yazilan["aciklama_en"] == mevcut["aciklama_en"])
    kontrol("TR alan yenilendi", yazilan["baslik"] == "yeni TR baslik")
    kontrol("girdi spec degismedi", uretilen["aciklama_en"] == "otomatik metin")
    kontrol("yeni dosyada uretilen EN metni yazilir", yeni["aciklama_en"] == "otomatik metin")


def test_ekran_turu_dil():
    print("\n[EA2] ekran_turu --dil tr|en")
    et = _arac("ekran_turu")
    kontrol("--dil varsayilan tr", et._ayristirici().parse_args([]).dil == "tr")
    kontrol("--dil en", et._ayristirici().parse_args(["--dil", "en"]).dil == "en")
    try:
        et._ayristirici().parse_args(["--dil", "de"])
        reddetti = False
    except SystemExit:
        reddetti = True
    kontrol("--dil de reddedilir", reddetti)
    kontrol("dosya adi: tr soneksiz, en '_en'",
            et.dosya_adi("x", "acik", (10, 20)) == "x_acik_10x20.png"
            and et.dosya_adi("x", "acik", (10, 20), "en") == "x_acik_10x20_en.png")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cekirdek import ceviri
    with et.dil_baglami("en"):
        en = (ceviri.etkin_dil(), ceviri._("Parçalar"))
    kontrol("en baglaminda Ingilizce", en == ("en", "Components"), "-> %r" % (en,))
    kontrol("cikista Turkceye doner", ceviri.etkin_dil() == "tr"
            and ceviri._("Parçalar") == "Parçalar")
    with et.dil_baglami("tr"):
        kontrol("tr baglami dili degistirmez", ceviri.etkin_dil() == "tr")


def _bolum(metin, baslik_deseni):
    """Basligi desene uyan bolumun govdesi (bir sonraki ## basligina kadar)."""
    m = re.search(r"^##+ [^\n]*?(%s)[^\n]*\n(.*?)(?=^## |\Z)" % baslik_deseni, metin, re.M | re.S)
    return m.group(2) if m else None


def test_readme_ozet_ve_kilavuz():
    print("\n[EA3] README: Once ciz / Bilinen tuzaklar kisa ozet + kilavuz baglantisi")
    for ad, desenler in (("README.md", ("ÖNCE ÇİZ", "Bilinen tuzaklar")),
                         ("README.en.md", ("DRAW FIRST", "Known pitfalls"))):
        with open(os.path.join(KOK, ad), encoding="utf-8") as f:
            metin = f.read()
        for desen in desenler:
            govde = _bolum(metin, re.escape(desen))
            satir = [s for s in (govde or "").splitlines() if s.strip()]
            kontrol("%s: '%s' bolumu var" % (ad, desen), govde is not None)
            kontrol("%s: '%s' 3-5 satir" % (ad, desen), 3 <= len(satir) <= 5,
                    "-> %d satir" % len(satir))
            kontrol("%s: '%s' kilavuz 06 bolumune bagli" % (ad, desen),
                    re.search(r"docs/kilavuz/(tr|en)/06-", govde or "") is not None)


HIZLI = [test_vv_kriter_en_alanlari_korunur, test_ekran_turu_dil, test_readme_ozet_ve_kilavuz]
YAVAS = []
