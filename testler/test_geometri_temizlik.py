# -*- coding: utf-8 -*-
"""
 test_geometri_temizlik.py  --  Dalga G temizlik: kurucu sarmalayicilari gitti,
 tuketiciler geometri API'sinde; sinir formu / yeniden adlandirma G-2 API'sinde;
 guc haritasi yeni anahtar parcalari; onizleme vurgusu.

 Ucu de agac modu sablonlariyla (arayuz/geometri/sablonlar.uret) sinanir; MC yok.
 Sozlesme: testler/ortak_test.py.
"""

import os
import re

from testler.ortak_test import KOK, ORNEK, kontrol

SABLONLAR = (("pwr_ceyrek_kor", "kare_altigen"), ("sfr_altigen", "altigen_tambur"),
             ("pwr_ceyrek_kor", "kafes_tambur"))
SILINEN = ("kor_kur", "_tek_bilesen", "cubuk_universe", "plaka_universe", "_altigen_sinir",
           "aktif_eksenel_aralik", "cubuk_eksenel_aralik", "guc_eksenel_araligi",
           "guc_yuksekligi", "_spec_fisil_mi", "_iceriyor_mu", "_guc_hedef_adlari",
           "kor_ic_olcusu")


def agac_specleri():
    """[(sablon anahtari, agac modundaki spec)] -- uc yeni sablon."""
    from cekirdek import sema
    from arayuz.geometri import sablonlar
    return [(a, sablonlar.uret(sema.yukle(os.path.join(ORNEK, o + ".json")), a))
            for o, a in SABLONLAR]


def _kaynaklar():
    for kok_dizin in ("arayuz", "cekirdek", "testler"):
        for dizin, _alt, dosyalar in os.walk(os.path.join(KOK, kok_dizin)):
            for d in dosyalar:
                if d.endswith(".py"):
                    yol = os.path.join(dizin, d)
                    with open(yol, encoding="utf-8") as f:
                        yield os.path.relpath(yol, KOK), f.read()


def test_kurucu_sarmalayicilari_silindi():
    print("\n[GT1] kurucu sarmalayicilari silindi; cagiran kalmadi")
    from cekirdek import kurucu
    kalan = [a for a in SILINEN if hasattr(kurucu, a)]
    kontrol("kurucu'da sarmalayici yok", not kalan, "-> %s" % kalan)
    desen = re.compile(r"\b(?:kurucu|_kur|_k)\.(%s)\(" % "|".join(SILINEN))
    cagri = ["%s: %s" % (yol, e.group(0)) for yol, metin in _kaynaklar()
             if not yol.endswith("test_geometri_temizlik.py")
             for e in desen.finditer(metin)]
    kontrol("hicbir modul sarmalayici cagirmiyor", not cagri, "-> %s" % cagri[:5])


def test_agac_modu_tuketicileri():
    print("\n[GT2] guc_harita / katman ozeti / cubuk ucu agac modunda geometri API'siyle")
    from PySide6 import QtWidgets
    from cekirdek import geometri
    from arayuz import guc_harita
    from arayuz.sekme_cubuk import CubukSekmesi
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for anahtar, spec in agac_specleri():
        kontrol("%s: guc paydasi = geometri.hedef_yuksekligi" % anahtar,
                guc_harita._aktif_yukseklik(spec) == geometri.hedef_yuksekligi(spec))
        w = CubukSekmesi()
        w.spec_yukle(spec)
        w._uc_guncelle()
        ar = geometri.aktif_aralik(spec)
        metin = w.c_uc_etiket.text()
        kontrol("%s: kontrol ucu etiketi aktif araliktan" % anahtar,
                ar is None or ("%+.1f" % ar[1]) in metin, "-> %s / %s" % (metin, ar))


def _casus(modul, ad):
    """modul.ad'i sarar; cagrilar listesi ve geri yukleyici dondurur."""
    asil = getattr(modul, ad)
    cagrilar = []

    def sarili(*a, **k):
        cagrilar.append(a)
        return asil(*a, **k)
    setattr(modul, ad, sarili)
    return cagrilar, lambda: setattr(modul, ad, asil)


def _basvuru_adlari(spec, tur):
    from cekirdek import geometri
    return sorted(b.ad for b in geometri.basvurular(spec) if b.tur == tur)


def test_yeniden_adlandirma_g2_api():
    print("\n[GT3] duzenle: yerlesim/parca adi geometri.ad_degistir, grup degeri grup_degeri_yaz")
    from cekirdek import geometri
    from arayuz.geometri import duzenle
    spec = dict(agac_specleri()[2][1])            # kafes_tambur: tambur yerlesimi + grup
    agac = spec["geometri"]
    yol = next(("kok", "halkalar", i, "yerlesimler", j)
               for i, h in enumerate(agac["kok"].get("halkalar") or [])
               for j, _y in enumerate(h.get("yerlesimler") or []))
    eski = duzenle.al(agac, yol)["ad"]
    cagri, geri = _casus(geometri, "ad_degistir")
    try:
        yeni = duzenle.yeniden_adlandir(agac, yol, "tamburlar_yeni")
    finally:
        geri()
    kontrol("yerlesim adi geometri.ad_degistir ile", cagri and cagri[0][1:] ==
            ("yerlesim", eski, "tamburlar_yeni"), "-> %s" % cagri)
    kontrol("grup uyesi de degisti", any("tamburlar_yeni" in g.get("uyeler", [])
                                         for g in yeni.get("gruplar") or []))
    kontrol("girdi agac degismedi", duzenle.al(agac, yol)["ad"] == eski)
    cagri, geri = _casus(geometri, "grup_degeri_yaz")
    try:
        g_ad = agac["gruplar"][0]["ad"]
        yeni = duzenle.grup_degeri_yaz(agac, g_ad, 33.0)
    finally:
        geri()
    kontrol("grup degeri geometri.grup_degeri_yaz ile", cagri and yeni["gruplar"][0]["deger"] == 33.0
            and agac["gruplar"][0]["deger"] != 33.0)
    try:
        duzenle.grup_degeri_yaz(agac, "yok_boyle", 1.0)
        hata = None
    except duzenle.DuzenlemeHatasi as e:
        hata = e
    kontrol("tanimsiz grup DuzenlemeHatasi", hata is not None)


def test_parca_adi_agac_modunda():
    print("\n[GT4] parca_adini_degistir agac modunda agac basvurularini da gunceller")
    import copy
    from arayuz.cubuk import parca_islemleri as pi
    for anahtar, spec in agac_specleri():
        demet = next(a for a in _basvuru_adlari(spec, "demet"))
        once = _basvuru_adlari(spec, "demet").count(demet)
        s = copy.deepcopy(spec)
        n = pi.parca_adini_degistir(s, demet, demet + "_y")
        sonra = _basvuru_adlari(s, "demet")
        kontrol("%s: agactaki '%s' basvurulari yeni adda (%d)" % (anahtar, demet, once),
                demet not in sonra and sonra.count(demet + "_y") == once and n >= once,
                "-> n=%d %s" % (n, sonra))
    try:
        pi.parca_adini_degistir(copy.deepcopy(spec), "yok_boyle", "x")
        hata = None
    except KeyError as e:
        hata = e
    kontrol("tanimsiz parca KeyError", hata is not None)


def test_grup_degeri_geri_alinir():
    print("\n[GT5] grup formu degeri grup_degeri_yaz ile yazar; geri al / yinele")
    from PySide6 import QtWidgets
    from cekirdek import geometri
    from testler.geometri_ui_arayuz import _ornek, _Pencere
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    p = _Pencere(geometri.gelismise_gec(_ornek("tamburlu_kor")))
    e = p.kor.gelismis_editor
    e.sec(("gruplar", 0))
    f = e.formlar["grup"]
    once = p.spec["geometri"]["gruplar"][0]["deger"]
    cagri, geri = _casus(geometri, "grup_degeri_yaz")
    try:
        f.deger.kutu.setValue(once + 40.0)
        p._gecmis_sayac.stop()
        p._gecmise_it()
    finally:
        geri()
    kontrol("deger spec'te ve API ile yazildi",
            p.spec["geometri"]["gruplar"][0]["deger"] == once + 40.0 and bool(cagri),
            "-> %s" % p.spec["geometri"]["gruplar"][0]["deger"])
    p.geri_al()
    kontrol("Geri Al eski degere doner", p.spec["geometri"]["gruplar"][0]["deger"] == once)
    p.yinele()
    kontrol("Yinele yeniden uygular", p.spec["geometri"]["gruplar"][0]["deger"] == once + 40.0)


# ----------------------------------------------------------------------------
# guc haritasi: yeni anahtar parcalari (MC'siz, sahte dagilim)
# ----------------------------------------------------------------------------

_PINLER = ((0, 0), (8, 8), (16, 16), (3, 12))


def _dagilim(kafesler, turler, anahtarlar, kesik=()):
    konumlar = {a: {"eksenel": [(1.0 + 0.01 * i, 0.01)], "toplam": (1.0 + 0.01 * i, 0.01)}
                for i, a in enumerate(anahtarlar)}
    tam = len(kafesler) > 1
    return {"konumlar": konumlar, "eksenel_dilim": 1, "tam_kor": tam, "kafesler": kafesler,
            "kafes": kafesler[-1], "kafes_turleri": turler, "kafes_turu": turler[-1],
            "duzey_sayisi": len(kafesler), "cubuk_turleri": {}, "notlar": [],
            "kesik_cubuklar": list(kesik)}


def guc_fiksturleri():
    """[(ad, dagilim)] -- uc agac sablonunun kurulan kafesleri + iki yerlesim duzeyi."""
    from cekirdek import altigen, guc_kor, kurucu
    specler = dict(agac_specleri())
    cikti = []
    for anahtar in ("kare_altigen", "altigen_tambur", "kafes_tambur"):
        model, _b = kurucu.kur(specler[anahtar])
        adli = {k.name: k for k in model.geometry.get_all_lattices().values() if k.name}
        adsiz = [k for k in model.geometry.get_all_lattices().values() if not k.name]
        if anahtar == "kare_altigen":
            kor, blok = adli["g:cekirdek_kafesi"], adli["g:blok_kafesi"]
            duzey = guc_kor.KarisikDuzey(kafesler={kor.name: kor, blok.name: blok})
            a = [((kor.name, i, j), p) for i in range(5) for j in range(5) for p in _PINLER]
            b = [((blok.name, r, k), (8, 8)) for r, k in sorted(altigen.konumlar(5, "x"))
                 if r == 1][:6]
            cikti.append((anahtar, _dagilim([duzey, adsiz[0]], ["karisik", "kare"], a + b,
                                            kesik=b[:3])))
        elif anahtar == "altigen_tambur":
            hex_k = adsiz[0]
            a = sorted(altigen.konumlar(int(hex_k.num_rings), hex_k.orientation))
            cikti.append((anahtar, _dagilim([hex_k], ["altigen"], a)))
        else:
            kor = adli["g:kor_kafesi"]
            a = [((i, j), p) for i in range(3) for j in range(3) for p in _PINLER]
            cikti.append((anahtar, _dagilim([kor, adsiz[0]], ["kare", "kare"], a)))
            yer = guc_kor.YerlesimDuzeyi(merkezler={("iki", 0): (-34.0, 0.0),
                                                    ("iki", 1): (34.0, 0.0)})
            a3 = [(("iki", n),) + k for n in (0, 1) for k in a]
            cikti.append(("yerlesim+kafes", _dagilim([yer, kor, adsiz[0]],
                                                    ["yerlesim", "kare", "kare"], a3)))
            a2 = [(("iki", n), p) for n in (0, 1) for p in _PINLER]
            cikti.append(("yerlesim+pin", _dagilim([yer, adsiz[0]], ["yerlesim", "kare"], a2)))
    return cikti


def test_guc_haritasi_yeni_anahtarlar():
    print("\n[GT6] guc haritasi: karisik / yerlesim duzeyleri cizilir, kesik ayri isaretli")
    from PySide6 import QtWidgets
    from cekirdek import guc
    from arayuz.guc_harita import GucHaritaWidget
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for ad, dag in guc_fiksturleri():
        f = guc.tepe_faktorleri(dag)
        w = GucHaritaWidget()
        for olcek in ("cubuk", "demet"):
            hata = None
            try:
                w.olcek.setCurrentIndex(w.olcek.findData(olcek))
                w.sonuc_ayarla({"guc": {"dagilim": dag, "faktorler": f}})
            except Exception as e:          # testin amaci cokmeyi raporlamak
                hata = "%s: %s" % (type(e).__name__, e)
            kesik = len(dag["kesik_cubuklar"])
            ipucu = [o[3] for o in w._ipucu_ogeleri]
            beklenen = (len(dag["konumlar"]) if olcek == "cubuk" or not dag["tam_kor"]
                        else len(f["demetler"]) + kesik)
            kontrol("%s (%s): cizildi, %d oge" % (ad, olcek, beklenen),
                    hata is None and (len(ipucu) == beklenen or not dag["tam_kor"]),
                    "-> %s, %d oge" % (hata, len(ipucu)))
            if kesik:
                kontrol("%s (%s): kesik cubuklar ayri isaretli" % (ad, olcek),
                        sum("kesik" in m for m in ipucu) == kesik
                        and "kesik" in w.figur.axes[0].get_title())
        if dag["tam_kor"]:
            x0, x1 = w.figur.axes[0].get_xlim()
            xs = [guc.cubuk_merkezi(dag, a)[0] for a in dag["konumlar"]]
            kontrol("%s: eksenler butun cubuklari kapsar" % ad, x0 < min(xs) and x1 > max(xs))


def test_onizleme_malzeme_vurgusu():
    print("\n[GT7] onizleme: secili dugum 'Malzeme' renklendirmesinde de vurgulanir")
    from PySide6 import QtWidgets
    from arayuz.onizleme import OnizlemeWidget
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    spec = dict(agac_specleri())["kafes_tambur"]
    w = OnizlemeWidget()
    istenen = []
    w.iste = lambda: istenen.append(w.renklendirme.currentData())
    w.spec_ayarla(spec)
    w.renklendirme.setCurrentIndex(w.renklendirme.findData("material"))
    istenen.clear()
    w.vurgula(("kok", "ic"))
    kontrol("malzeme renklendirmesinde vurgula yeniden cizim ister", istenen == ["material"])
    w._ciz()
    eks = w.figur.axes[0]
    vurgu = [a for a in eks.get_children() if getattr(a, "get_gid", lambda: None)() == "vurgu"]
    kontrol("malzeme renkleri korunur + vurgu katmani cizildi",
            w.cizildi_mi() and len(eks.images) >= 2 and vurgu, "-> %s %s" % (w._son_hata, vurgu))
    w.vurgula(None)
    w._ciz()
    eks = w.figur.axes[0]
    kontrol("vurgu kalkinca katman yok",
            not [a for a in eks.get_children() if getattr(a, "get_gid", lambda: None)() == "vurgu"])


HIZLI = [test_kurucu_sarmalayicilari_silindi, test_agac_modu_tuketicileri,
         test_yeniden_adlandirma_g2_api, test_parca_adi_agac_modunda,
         test_grup_degeri_geri_alinir, test_guc_haritasi_yeni_anahtarlar,
         test_onizleme_malzeme_vurgusu]
YAVAS = []
