# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/tukenme.py  --  tukenme ayarlari kontrolleri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import malzeme_bul
from cekirdek import veri_bilgi
from cekirdek import uygunluk
from cekirdek.dogrula._ortak import Bulgu


_SPEKTRUM_ADI = {"termal": "termal", "hizli": "hızlı"}


def tukenme_kontrol(spec, veri_kontrolu=True):
    """
    Tukenme ayarlari tutarli mi?

    Tukenmenin sessiz hatalari: yarim indirilmis zincir, yanlis spektrumlu
    zincir, hacmi yanlis malzeme (yanma hizi o oranda yanlis olur ve k-eff'te
    iz birakmaz), Xe-135 dengesini kaciran uzun ilk adim.
    """
    from cekirdek import tukenme as _tk
    bulgular = []
    t = spec.get("tukenme") or {}
    if not t.get("var"):
        return bulgular
    yer = "tukenme"

    # Tukenmenin bu modelde yapilabilir olup olmadigi: uygunluk.tukenme_uygun
    # (arayuz tukenme sekmesini ayni kuralla gizler).
    uygun, sebep = uygunluk.tukenme_uygun(spec)
    if not uygun:
        if spec["ayarlar"].get("mod", "eigenvalue") != "eigenvalue":
            bulgular.append(Bulgu("hata", yer,
                                  "tükenme Özdeğer (k-eff) hesabı gerektirir",
                                  "Sabit kaynaklı tükenme (aktivasyon) bu sürümde yok."))
        else:
            bulgular.append(Bulgu("hata", yer, "tükenme yapılamaz: %s" % sebep,
                                  "Yanacak yakıt geometride yer almalı."))

    # --- zincir ---
    zs = _tk.zincir_secimi(spec)
    # Hizli kontrol yalnizca dosyanin SONUNU okur (<1 ms); veri_kontrolu
    # kapaliyken bile yapilir ki arayuz yarim bir zinciri aninda gostersin.
    tamam, mesaj, _n = veri_bilgi.zincir_kontrol(zs["yol"])
    if not tamam:
        bulgular.append(Bulgu("hata", yer, mesaj,
                              "Kaynak ve sha256: ~/nucdata/chain/KAYNAK.txt"))
    if t.get("zincir", "otomatik") != "otomatik" and zs["temel"] != zs["spektrum"]:
        bulgular.append(Bulgu(
            "uyari", yer,
            "%s zincir seçildi ama model %s spektrumlu görünüyor"
            % (_SPEKTRUM_ADI.get(zs["temel"], zs["temel"]),
               _SPEKTRUM_ADI.get(zs["spektrum"], zs["spektrum"])),
            "Termal/hızlı zincir yakalama dallanma oranlarını ve fisyon "
            "verimlerini belirler (ör. Am241(n,γ)→Am242m termalde %8.1, "
            "hızlıda %13.2)."))
    if zs["tur"].startswith("casl"):
        bulgular.append(Bulgu(
            "bilgi", yer,
            "basitleştirilmiş CASL zinciri: 228 nüklid (tam zincir 3820)",
            "Yaklaşık 3 kat hızlı; ön inceleme içindir. Sonuçları tam zincirle "
            "doğrulayın."))

    # --- guc ve adimlar ---
    p = t.get("guc_yogunlugu")
    if p is None or float(p) <= 0:
        bulgular.append(Bulgu("hata", yer, "güç yoğunluğu sıfırdan büyük olmalı [W/gHM]"))
    elif not (1.0 <= float(p) <= 200.0):
        bulgular.append(Bulgu(
            "uyari", yer, "güç yoğunluğu %g W/gHM olağan dışı" % float(p),
            "Tipik: PWR 38–40, BWR ~25, SFR 50–100 W/gHM. Birim W/gHM'dir, "
            "mutlak güç değil."))
    adimlar = t.get("adimlar") or []
    if not adimlar:
        bulgular.append(Bulgu("hata", yer, "en az bir zaman adımı gerekli"))
    elif any(float(a) <= 0 for a in adimlar):
        bulgular.append(Bulgu("hata", yer, "zaman adımları sıfırdan büyük olmalı"))
    else:
        birim = t.get("adim_birimi") or "d"
        ilk_gun = float(adimlar[0])
        if birim == "MWd/kg" and p:
            ilk_gun = float(adimlar[0]) * 1000.0 / float(p)
        if ilk_gun > 2.0:
            bulgular.append(Bulgu(
                "uyari", yer,
                "ilk adım %.3g gün — Xe-135 dengesi (~2 gün) tek adıma eziliyor"
                % ilk_gun,
                "İlk adımları kısa tutun (ör. 0.5 ve 1.5 gün). Xe-135 PWR'da "
                "birkaç bin pcm'lik hızlı bir düşüş yaratır; uzun bir ilk adım "
                "bunu görünmez kılar."))

    # --- yanabilir malzemeler ve hacimler ---
    try:
        hv = _tk.hacimler(spec)
    except Exception as e:
        hv = None
        bulgular.append(Bulgu("hata", yer, "hacimler hesaplanamadı: %s" % e))
    if hv is not None:
        if not hv and uygun:
            bulgular.append(Bulgu("hata", yer,
                                  "modelde yanabilir (fisil) malzeme yok"))
        for ad, v in hv.items():
            if not v["hacim"]:
                bulgular.append(Bulgu(
                    "hata", "tukenme/%s" % ad,
                    "hacim hesaplanamıyor: %s" % v["ayrinti"],
                    "Tükenme kesin hacim gerektirir: yanlış hacim yanma hızını "
                    "aynı oranda bozar ve k-eff'te iz bırakmaz."))
    for ad in t.get("ek_malzemeler") or []:
        if malzeme_bul(spec, ad) is None:
            bulgular.append(Bulgu("hata", yer, "tanımsız ek malzeme: '%s'" % ad))

    # --- istatistik ---
    a = spec["ayarlar"]
    aktif = int(a.get("cevrim", 0)) - int(a.get("pasif", 0))
    if int(a.get("parcacik", 0)) * max(aktif, 0) < 100000:
        bulgular.append(Bulgu(
            "uyari", yer,
            "aktif istatistik az (%d parçacık × %d çevrim)"
            % (int(a.get("parcacik", 0)), aktif),
            "Tükenme her adımda reaksiyon hızlarını transport hesabından alır; "
            "gürültü adımdan adıma birikir. Parçacık × aktif çevrim ≥ 100 000 "
            "önerilir."))
    if t.get("malzemeleri_ayir"):
        bulgular.append(Bulgu(
            "bilgi", yer, "çubuk çubuk yanma açık",
            "Her hücre ayrı malzeme olur; bellek ve süre hücre sayısıyla artar."))
    return bulgular
