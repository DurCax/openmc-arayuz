# -*- coding: utf-8 -*-
"""
 test_h1_bellek.py  --  v3 H1: icerige gore bellek (uygunluk, geometri.hacim,
                        tukenme) ve tembel sekme (kirli/temiz)

 BELLEK SOZLESMESI (cekirdek/uygunluk_bellek.py)
   * Ayni spec icerigi icin agac gezintisi BIR kez yapilir (sayilir).
   * Spec degisince (yerinde degistirilse bile) sonuc yeniden hesaplanir:
     anahtar her cagrida icerikten uretilir, bayat sonuc donmez.
   * Cagirana verilen nesne bellekteki nesne degildir: cagiran onu
     degistirse de sonraki cagri etkilenmez (degismezlik kurali).
   * Bellekli sonuc, bellek bosken hesaplanan sonucla AYNIDIR (butun ornekler).

 TEMBEL SEKME (arayuz/pencere/ana_pencere.py)
   * Spec yuklenince yalniz gorunur editor doldurulur; digerleri "kirli".
   * Kirli sekme acilinca bir kez doldurulur ve temizlenir; temiz sekme
     yeniden acilinca doldurulmaz.
   * Editor doldurmak spec'i degistirmez (tembel yukleme davranisi degistirmez).
"""

import copy
import glob
import json
import os

from testler.ortak_test import kontrol, ORNEK

_AGAC_ORNEGI = "pwr_kare_altigen_halka"        # agac modu, ~120 ziyaret (hizli)
_HACIM_ORNEGI = "kafes_tamburlu_yansitici"     # agac modu, birden cok malzeme


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


class _GeziSayaci:
    """Agac gezintilerini sayar: gezinti.gez ve hacim'in ice aktardigi gez."""

    def __init__(self, monkeypatch):
        from cekirdek.geometri import gezinti, hacim
        self.sayi = 0
        asil = gezinti.gez

        def sayan(m):
            self.sayi += 1
            return asil(m)
        monkeypatch.setattr(gezinti, "gez", sayan)
        monkeypatch.setattr(hacim, "gez", sayan)


def _bos_bellek():
    from cekirdek import uygunluk_bellek
    uygunluk_bellek.temizle()


# ---------------------------------------------------------------------------
# uygunluk
# ---------------------------------------------------------------------------

def test_uygunluk_ayni_spec_tek_gezinti(monkeypatch):
    print("\n[H1-B1] uygunluk: ayni spec icin agac bir kez gezilir")
    from cekirdek import uygunluk
    _bos_bellek()
    spec = _yukle(_AGAC_ORNEGI)
    sayac = _GeziSayaci(monkeypatch)
    ilk = (uygunluk.gecerli_sekmeler(spec), uygunluk.model_ozeti(spec),
           uygunluk.ayar_alanlari(spec), uygunluk.gecerli_taramalar(spec))
    ilk_sayi = sayac.sayi
    ikinci = (uygunluk.gecerli_sekmeler(spec), uygunluk.model_ozeti(spec),
              uygunluk.ayar_alanlari(spec), uygunluk.gecerli_taramalar(spec))
    kontrol("ilk tur en cok 2 gezinti (icerik + agac ozeti)", ilk_sayi <= 2,
            "gezinti=%d" % ilk_sayi)
    kontrol("ikinci tur gezintisiz", sayac.sayi == ilk_sayi, "gezinti=%d" % sayac.sayi)
    kontrol("sonuclar ayni", ilk == ikinci)


def test_uygunluk_spec_degisince_yeniden_hesaplar():
    print("\n[H1-B2] uygunluk: spec yerinde degisince bayat sonuc donmez")
    from cekirdek import uygunluk
    _bos_bellek()
    spec = _yukle(_AGAC_ORNEGI)
    ilk = uygunluk.geometri_icerigi(spec)
    ad = sorted(ilk["malzeme"])[0]
    yeni_ad = "h1_yeni_malzeme"
    # yerinde degisiklik: malzemeyi yeniden adlandir (tanim + agactaki basvurular)
    metin = json.dumps(spec).replace('"%s"' % ad, '"%s"' % yeni_ad)
    yeni = json.loads(metin)
    spec.clear()
    spec.update(yeni)
    sonra = uygunluk.geometri_icerigi(spec)
    kontrol("eski ad artik yok", ad not in sonra["malzeme"], sorted(sonra["malzeme"]))
    kontrol("yeni ad var", yeni_ad in sonra["malzeme"])
    geri = json.loads(metin.replace('"%s"' % yeni_ad, '"%s"' % ad))
    spec.clear()
    spec.update(geri)
    kontrol("geri donunce ilk sonuc", uygunluk.geometri_icerigi(spec) == ilk)


def test_uygunluk_donen_nesne_paylasilmaz():
    print("\n[H1-B3] uygunluk: cagiranin degistirdigi sonuc bellegi bozmaz")
    from cekirdek import uygunluk
    _bos_bellek()
    spec = _yukle(_AGAC_ORNEGI)
    ic = uygunluk.geometri_icerigi(spec)
    beklenen = copy.deepcopy(ic)
    ic["malzeme"].add("sahte")
    ic["cubuk"].clear()
    kontrol("geometri_icerigi kopya doner", uygunluk.geometri_icerigi(spec) == beklenen)
    sekmeler = uygunluk.gecerli_sekmeler(spec)
    sekmeler.append("sahte")
    kontrol("gecerli_sekmeler kopya doner", "sahte" not in uygunluk.gecerli_sekmeler(spec))


def _uygunluk_ozeti(spec):
    from cekirdek import uygunluk, tarama
    return {
        "sekmeler": uygunluk.gecerli_sekmeler(spec),
        "ozet": uygunluk.model_ozeti(spec),
        "ayar": uygunluk.ayar_alanlari(spec),
        "parca": uygunluk.parca_turleri(spec),
        "guc": uygunluk.guc_cubuklari(spec),
        "taramalar": uygunluk.gecerli_taramalar(spec),
        "kritik": uygunluk.gecerli_taramalar(spec, "kritik"),
        "hedefler": {t: uygunluk.gecerli_hedefler(spec, t) for t in tarama.TURLER},
        "icerik": uygunluk.geometri_icerigi(spec),
        "tukenme": uygunluk.tukenme_uygun(spec),
        "ayirma": uygunluk.tukenme_ayirma_anlamli(spec),
    }


def test_bellekli_sonuc_belleksizle_ayni():
    print("\n[H1-B4] butun ornekler: bellekli sonuc = bos bellekle hesaplanan")
    from cekirdek import geometri, uygunluk_bellek
    farkli = []
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.splitext(os.path.basename(yol))[0]
        spec = _yukle(ad)
        adaylar = [spec]
        if not geometri.agac_modu(spec):
            try:
                adaylar.append(geometri.gelismise_gec(spec))
            except (ValueError, KeyError):
                pass                       # gelismise gecilemeyen sablon (kuresel)
        for s in adaylar:
            uygunluk_bellek.temizle()
            bos = _uygunluk_ozeti(s)
            dolu = _uygunluk_ozeti(s)      # ikinci tur bellekten
            if bos != dolu:
                farkli.append(ad)
    kontrol("bellekli = belleksiz (tum ornekler, sablon + gelismis)", not farkli, farkli)


# ---------------------------------------------------------------------------
# geometri.hacim ve tukenme
# ---------------------------------------------------------------------------

def test_hacim_katkilar_tek_gezinti(monkeypatch):
    print("\n[H1-B5] hacim: butun malzemelerin katkilari tek gezintide")
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    _bos_bellek()
    spec = _yukle(_HACIM_ORNEGI)
    adlar = [m["ad"] for m in spec["malzemeler"]]
    belleksiz = {}
    for ad in adlar:
        _bos_bellek()
        belleksiz[ad] = hacim.katkilar(geometri.model(spec), ad)
    _bos_bellek()
    sayac = _GeziSayaci(monkeypatch)
    bellekli = {ad: hacim.katkilar(geometri.model(spec), ad) for ad in adlar}
    kontrol("tek gezinti", sayac.sayi == 1, "gezinti=%d" % sayac.sayi)
    kontrol("sonuclar belleksizle ayni", bellekli == belleksiz)
    bellekli[adlar[0]].append(("sahte", 1.0, 1, None))
    kontrol("donen liste kopya", hacim.katkilar(geometri.model(spec), adlar[0])
            == belleksiz[adlar[0]])


def test_hacim_model_degisince_yeniden_hesaplar():
    print("\n[H1-B6] hacim: agac degisince katkilar yeniden hesaplanir")
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    _bos_bellek()
    spec = _yukle(_HACIM_ORNEGI)
    ad = next(a for a in (m["ad"] for m in spec["malzemeler"])
              if hacim.analitik(geometri.model(spec), a).hacim)
    once = hacim.analitik(geometri.model(spec), ad).hacim
    kok = spec["geometri"]["kok"]
    kesit = kok.get("kesit") or {}
    anahtar = "yaricap" if "yaricap" in kesit else None
    if anahtar is None:                     # dis halka kalinligi
        h = next(h for h in kok.get("halkalar") or [] if h.get("kalinlik") is not None)
        h["kalinlik"] = h["kalinlik"] * 1.5
    else:
        kesit[anahtar] = kesit[anahtar] * 1.5
    sonra = hacim.analitik(geometri.model(spec), ad).hacim
    _bos_bellek()
    taze = hacim.analitik(geometri.model(spec), ad).hacim
    kontrol("yerinde degisiklik sonrasi bellekli = taze", sonra == taze,
            "%s %s %s" % (once, sonra, taze))


def test_yakit_ornek_sayisi_bellegi(monkeypatch):
    print("\n[H1-B7] tukenme.yakit_ornek_sayisi: ikinci cagri gezintisiz, ayni sonuc")
    from cekirdek import tukenme
    _bos_bellek()
    spec = _yukle("pwr_17x17")
    sayac = _GeziSayaci(monkeypatch)
    ilk = tukenme.yakit_ornek_sayisi(spec)
    ilk_sayi = sayac.sayi
    ikinci = tukenme.yakit_ornek_sayisi(spec)
    kontrol("ilk cagri en cok bir gezinti", ilk_sayi <= 1, "gezinti=%d" % ilk_sayi)
    kontrol("ikinci cagri gezintisiz", sayac.sayi == ilk_sayi)
    kontrol("sonuc ayni ve > 1 (17x17)", ilk == ikinci and ilk > 1, ilk)


# ---------------------------------------------------------------------------
# tembel sekme
# ---------------------------------------------------------------------------

def _pencere():
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    p.onizleme._ciz = lambda *a, **k: None      # onizleme H2'nin; burada gereksiz
    return p


def _kapat(p):
    p.s_tukenme.bekle()
    p._kirli = False
    p.close()
    p.deleteLater()


def _yukleme_sayaci(p):
    sayim = {}
    for e in p.editorler:
        asil = e.spec_yukle

        def sayan(spec, _e=e, _asil=asil):
            sayim[_e] = sayim.get(_e, 0) + 1
            return _asil(spec)
        e.spec_yukle = sayan
    return sayim


def test_tembel_sekme_kirli_temiz():
    print("\n[H1-T1] tembel sekme: yalniz gorunur editor dolar, digerleri kirli")
    p = _pencere()
    try:
        sayim = _yukleme_sayaci(p)
        p.ornek_ac(os.path.join(ORNEK, "pwr_17x17.json"))
        gorunur = p._gorunur_editor()
        kontrol("acilista yalniz gorunur editor dolduruldu",
                set(sayim) <= {gorunur}, [type(e).__name__ for e in sayim])
        gizli = set(p.editorler) - {gorunur}
        kontrol("digerleri kirli", gizli <= p._kirli_sekmeler)
        kontrol("gorunur editor temiz", gorunur not in p._kirli_sekmeler)
        sayim.clear()
        p.sekmeye_git("tukenme", sessiz=True)
        kontrol("kirli sekme acilinca bir kez dolar", sayim.get(p.s_tukenme) == 1, sayim)
        kontrol("acilan sekme temizlendi", p.s_tukenme not in p._kirli_sekmeler)
        kontrol("acilan sekmenin spec'i guncel", p.s_tukenme.spec is p.spec)
        p.sekmeye_git("malzemeler", sessiz=True)
        sayim.clear()
        p.sekmeye_git("tukenme", sessiz=True)
        kontrol("temiz sekme yeniden acilinca dolmaz", not sayim.get(p.s_tukenme), sayim)
        # malzeme degisikligi tukenmeyi (gizliyken) kirletir
        p.sekmeye_git("malzemeler", sessiz=True)
        p._degisti("malzeme")
        kontrol("bagimli gizli sekme kirlendi", p.s_tukenme in p._kirli_sekmeler)
    finally:
        _kapat(p)


def test_tembel_sekme_sonucu_hevesliyle_ayni():
    print("\n[H1-T2] tembel sekme: acildiginda hevesli yukleme ile ayni icerik")
    from arayuz.ortak import SekmeTabani
    p = _pencere()
    try:
        p.ornek_ac(os.path.join(ORNEK, "pwr_17x17.json"))
        p.sekmeye_git("tukenme", sessiz=True)
        tembel = _sekme_metinleri(p.s_tukenme)
        p.s_tukenme.spec_yukle(p.spec)      # hevesli (eski) yol
        hevesli = _sekme_metinleri(p.s_tukenme)
        kontrol("tukenme sekmesi metinleri ayni", tembel == hevesli)
        kontrol("SekmeTabani turu", isinstance(p.s_tukenme, SekmeTabani))
    finally:
        _kapat(p)


def _sekme_metinleri(w):
    from PySide6 import QtWidgets
    metinler = []
    for c in w.findChildren(QtWidgets.QWidget):
        if isinstance(c, (QtWidgets.QLabel, QtWidgets.QAbstractButton)):
            metinler.append((c.objectName(), c.text(), c.isVisibleTo(w)))
        elif isinstance(c, QtWidgets.QComboBox):
            metinler.append((c.objectName(), c.currentText(), c.count()))
        elif isinstance(c, QtWidgets.QAbstractSpinBox):
            metinler.append((c.objectName(), c.text()))
    return metinler


def test_editor_doldurmak_spec_degistirmez():
    print("\n[H1-T3] editor doldurmak spec'i degistirmez (tembel yukleme guvenli)")
    from cekirdek import sema
    p = _pencere()
    try:
        degisen = []
        for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
            spec = sema.yukle(yol)
            for e in p.editorler:
                once = json.dumps(spec, sort_keys=True, default=str)
                e.spec_yukle(spec)
                if json.dumps(spec, sort_keys=True, default=str) != once:
                    degisen.append((os.path.basename(yol), type(e).__name__))
        kontrol("hicbir editor spec'i doldururken degistirmedi", not degisen, degisen)
    finally:
        _kapat(p)


HIZLI = [test_uygunluk_ayni_spec_tek_gezinti, test_uygunluk_spec_degisince_yeniden_hesaplar,
         test_uygunluk_donen_nesne_paylasilmaz, test_hacim_katkilar_tek_gezinti,
         test_hacim_model_degisince_yeniden_hesaplar, test_yakit_ornek_sayisi_bellegi,
         test_tembel_sekme_kirli_temiz, test_tembel_sekme_sonucu_hevesliyle_ayni]
YAVAS = [test_bellekli_sonuc_belleksizle_ayni, test_editor_doldurmak_spec_degistirmez]
