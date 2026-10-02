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

 TEMBEL SEKME (arayuz/pencere/ana_pencere.py, _degisti / _sekme_degisti)
   * Proje yuklenince (_spec_uygula) butun editorler doldurulur, hepsi temiz
     (bilerek hevesli; gerekce ana_pencere._spec_uygula belgesinde).
   * Bir duzenlemede konuya BAGIMLI gizli sekmeler kirli isaretlenir,
     doldurulmaz; gorunur bagimli sekme hemen doldurulur.
   * Kirli sekme acilinca bir kez doldurulur ve temizlenir; temiz sekme
     yeniden acilinca doldurulmaz. Ertelenmis doldurma hevesliyle ayni ekrani
     verir; editor doldurmak spec'i degistirmez (erteleme guvenli).
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
# Bellek sinifi
# ---------------------------------------------------------------------------

def test_bellek_lru_ve_anahtar():
    print("\n[H1-B0] Bellek: LRU siniri, temizle, JSON disi deger hic eslesmez")
    from cekirdek import uygunluk_bellek as ub
    b = ub.Bellek("test_lru", sinir=2)
    hesap = []

    def uret(x):
        hesap.append(x)
        return x * 10
    kontrol("ilk hesap", b.al("a", lambda: uret(1)) == 10 and hesap == [1])
    kontrol("isabet hesaplamaz", b.al("a", lambda: uret(99)) == 10 and hesap == [1])
    b.al("b", lambda: uret(2))
    b.al("a", lambda: uret(99))          # a en son kullanilan
    b.al("c", lambda: uret(3))           # sinir 2: en eski (b) atilir
    kontrol("LRU: en eski atildi", len(b) == 2 and b.al("b", lambda: uret(4)) == 40)
    ub.temizle()
    kontrol("temizle butun bellekleri bosaltir", len(b) == 0)
    try:
        ub.Bellek("gecersiz", sinir=0)
        kontrol("sinir < 1 reddedilir", False)
    except ValueError:
        kontrol("sinir < 1 reddedilir", True)
    kontrol("ayni icerik ayni anahtar",
            ub.icerik_anahtari({"x": [1, 2], "y": "a"}) == ub.icerik_anahtari({"x": [1, 2], "y": "a"}))
    kontrol("farkli icerik farkli anahtar",
            ub.icerik_anahtari({"x": 1}) != ub.icerik_anahtari({"x": 1.0001}))
    nesne = object()
    kontrol("JSON disi deger her seferinde farkli anahtar (bellek atlanir)",
            ub.icerik_anahtari({"x": nesne}) != ub.icerik_anahtari({"x": nesne}))


def test_ornek_spec_ve_modelleri_json_saf():
    print("\n[H1-B0b] ornek spec'leri ve GeometriModeli alanlari JSON'a cevrilebilir")
    from cekirdek import geometri
    sorunlu = []

    def json_disi(o):
        sorunlu.append(type(o).__name__)
        return None
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        spec = _yukle(os.path.splitext(os.path.basename(yol))[0])
        json.dumps(spec, default=json_disi)
        m = geometri.model(spec)
        json.dumps([m.kok, m.parcalar, m.gruplar, m.tanimlar, m.sablon, m.kaynaklar],
                   default=json_disi)
    kontrol("JSON disi deger yok (bellek anahtari icerigi tam yansitir)", not sorunlu,
            sorted(set(sorunlu)))

    def str_disi_anahtar(x):
        if isinstance(x, dict):
            return any(not isinstance(k, str) or str_disi_anahtar(v) for k, v in x.items())
        if isinstance(x, (list, tuple)):
            return any(str_disi_anahtar(v) for v in x)
        return False
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        spec = _yukle(os.path.splitext(os.path.basename(yol))[0])
        m = geometri.model(spec)
        if str_disi_anahtar(spec) or str_disi_anahtar([m.kok, m.parcalar, m.gruplar,
                                                        m.tanimlar, m.agac]):
            sorunlu.append(os.path.basename(yol))
    kontrol("sozluk anahtarlari hep str ({1: x} ile {'1': x} cakismasi olusmaz)",
            not sorunlu, sorunlu)


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


def test_gecerli_sekmeler_tek_gezinti(monkeypatch):
    print("\n[H1-B1b] gecerli_sekmeler: yakitli modelde yalniz icerik gezintisi")
    from cekirdek import uygunluk
    _bos_bellek()
    spec = _yukle(_AGAC_ORNEGI)
    sayac = _GeziSayaci(monkeypatch)
    sekmeler = uygunluk.gecerli_sekmeler(spec)
    kontrol("analiz sekmesi gorunur (on kosul)", "analiz" in sekmeler, sekmeler)
    kontrol("tek gezinti: analiz icin ilk gecerli tarama yeter", sayac.sayi == 1,
            "gezinti=%d" % sayac.sayi)


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
    from cekirdek.geometri.sema import BOSLUK
    kontrol("bosluk malzemesinin katkisi yok", hacim.katkilar(geometri.model(spec), BOSLUK) == [])


def test_hacim_model_degisince_yeniden_hesaplar():
    print("\n[H1-B6] hacim: agac yerinde degisince katkilar yeniden hesaplanir")
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    _bos_bellek()
    spec = _yukle(_HACIM_ORNEGI)
    adlar = [m["ad"] for m in spec["malzemeler"]]

    def hacimler():
        m = geometri.model(spec)
        return {ad: hacim.analitik(m, ad).hacim for ad in adlar}
    once = hacimler()
    sahip, anahtar = _ilk_yaricap(spec["geometri"]["kok"])
    sahip[anahtar] = sahip[anahtar] * 1.5          # yerinde degisiklik
    sonra = hacimler()
    _bos_bellek()
    taze = hacimler()
    kontrol("yaricap bir hacmi degistirdi", sonra != once)
    kontrol("yerinde degisiklik sonrasi bellekli = taze", sonra == taze)


def _ilk_yaricap(d):
    """(sozluk, "yaricap") -- agactaki ilk yaricap alani (derinlik oncelikli)."""
    if isinstance(d, dict):
        if isinstance(d.get("yaricap"), (int, float)):
            return d, "yaricap"
        ogeler = d.values()
    elif isinstance(d, list):
        ogeler = d
    else:
        return None
    for v in ogeler:
        r = _ilk_yaricap(v)
        if r:
            return r
    return None


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
    print("\n[H1-T1] tembel sekme: duzenlemede bagimli gizli sekmeler kirli, acilinca dolar")
    from arayuz.pencere.model_islemleri import _KONU_BAGIMLILIK
    p = _pencere()
    try:
        p.ornek_ac(os.path.join(ORNEK, "pwr_17x17.json"))
        kontrol("proje acilinca butun sekmeler temiz", not p._kirli_sekmeler)
        p.sekmeye_git("malzemeler", sessiz=True)
        sayim = _yukleme_sayaci(p)
        p._degisti("malzeme")
        bagimli = {p._konu_sekme[k] for k in _KONU_BAGIMLILIK["malzeme"]}
        kontrol("bagimli gizli sekmeler kirli", bagimli <= p._kirli_sekmeler,
                sorted(type(e).__name__ for e in p._kirli_sekmeler))
        kontrol("gizli sekmeler duzenlemede doldurulmadi", not sayim, sayim)
        kontrol("gorunur editor kirli degil", p.s_malzeme not in p._kirli_sekmeler)
        p.sekmeye_git("tukenme", sessiz=True)
        kontrol("kirli sekme acilinca bir kez dolar", sayim.get(p.s_tukenme) == 1, sayim)
        kontrol("acilan sekme temizlendi", p.s_tukenme not in p._kirli_sekmeler)
        kontrol("acilan sekmenin spec'i guncel", p.s_tukenme.spec is p.spec)
        p.sekmeye_git("malzemeler", sessiz=True)
        sayim.clear()
        p.sekmeye_git("tukenme", sessiz=True)
        kontrol("temiz sekme yeniden acilinca dolmaz", not sayim.get(p.s_tukenme), sayim)
        p._degisti("ayar")                     # bagimlisi olmayan konu
        kontrol("bagimsiz konu yeni sekme kirletmez",
                p.s_tukenme not in p._kirli_sekmeler and not sayim.get(p.s_tukenme))
        p._degisti("calistirma")               # gorunur bagimli: hemen dolar
        kontrol("gorunur bagimli sekme hemen dolar ve temiz kalir",
                sayim.get(p.s_tukenme) == 1 and p.s_tukenme not in p._kirli_sekmeler, sayim)
    finally:
        _kapat(p)


def test_tembel_sekme_sonucu_hevesliyle_ayni():
    print("\n[H1-T2] tembel sekme: ertelenmis doldurma hevesli doldurma ile ayni ekran")
    yol = os.path.join(ORNEK, "pwr_17x17.json")
    sonuc = []
    for tembel in (True, False):
        p = _pencere()
        try:
            p.ornek_ac(yol)
            p.sekmeye_git("malzemeler", sessiz=True)
            p.spec["malzemeler"][0]["sicaklik"] = 600.0
            p._degisti("malzeme")              # tukenme kirli (gizli)
            if not tembel:                      # eski/hevesli yol: hemen doldur
                p.s_tukenme.spec_yukle(p.spec)
                p._kirli_sekmeler.discard(p.s_tukenme)
            p.sekmeye_git("tukenme", sessiz=True)
            sonuc.append(_sekme_metinleri(p.s_tukenme))
        finally:
            _kapat(p)
    kontrol("tukenme sekmesinin gorunen metinleri ayni", sonuc[0] == sonuc[1])
    kontrol("karsilastirma bos degil", len(sonuc[0]) > 5, len(sonuc[0]))


def _sekme_metinleri(w):
    """Gorunen etiket/dugme/liste/sayi kutusu metinleri (sirayla)."""
    from PySide6 import QtWidgets
    metinler = []
    for c in w.findChildren(QtWidgets.QWidget):
        if not c.isVisibleTo(w):
            continue
        if isinstance(c, (QtWidgets.QLabel, QtWidgets.QAbstractButton)):
            metinler.append((c.objectName(), c.text()))
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


# ---------------------------------------------------------------------------
# inceleme (python-reviewer) bulgulari
# ---------------------------------------------------------------------------

def test_hacim_anahtari_agaci_kapsar():
    print("\n[H1-R1] hacim: model anahtari GeometriModeli.agac'i da kapsar")
    import dataclasses
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    m = geometri.model(_yukle(_HACIM_ORNEGI))
    baska = dataclasses.replace(m, agac=dict(m.agac, h1_isaret=1))
    kontrol("agac farkli -> anahtar farkli",
            hacim._model_anahtari(m) != hacim._model_anahtari(baska))


def test_anahtar_json_disi_ve_karisik_sozluk():
    print("\n[H1-R2] icerik_anahtari: tuple/karisik anahtarli sozluk hata vermez, eslesmez")
    from cekirdek import uygunluk_bellek as ub
    try:
        nesne = {(1, 2): "a"}
        kontrol("tuple anahtar: hata yok, her seferinde farkli (bellek atlanir)",
                ub.icerik_anahtari(nesne) != ub.icerik_anahtari(nesne))
        nesne = {1: "a", "b": 2}
        kontrol("karisik anahtar: hata yok, kararli",
                ub.icerik_anahtari(nesne) == ub.icerik_anahtari(nesne))
    except TypeError as e:
        kontrol("TypeError yok", False, str(e))
    kontrol("sira duyarli: farkli sira farkli anahtar (yalniz iska, bayat isabet degil)",
            ub.icerik_anahtari({"a": 1, "b": 2}) != ub.icerik_anahtari({"b": 2, "a": 1}))
    b = ub.Bellek("test_sayac")
    b.al("x", lambda: 1)
    b.al("x", lambda: 2)
    b.al("y", lambda: 3)
    kontrol("isabet/iska sayaci", (b.isabet, b.iska) == (1, 2), (b.isabet, b.iska))


def test_hacim_tablosu_dil_yarisi(monkeypatch):
    print("\n[H1-R3] tukenme: hesap sirasinda dil degisirse kayit eski dil anahtariyla saklanmaz")
    from cekirdek import tukenme
    _bos_bellek()
    spec = _yukle("pwr_17x17")
    diller = iter(["tr", "en"])
    monkeypatch.setattr(tukenme, "etkin_dil", lambda: next(diller, "en"))
    tukenme.hacimler(spec)
    kontrol("'tr' anahtariyla kayit yok",
            not any(k[1] == "tr" for k in tukenme._HACIM_KAYDI._kayit), list(tukenme._HACIM_KAYDI._kayit))


def test_sayim_hashlenemeyen_dolgu():
    print("\n[H1-R4] tukenme._sayim: hashlenemeyen dolgu eskisi gibi 0 (hata yok)")
    from cekirdek import tukenme
    spec = _yukle("pwr_17x17")
    try:
        kontrol("sozluk dolgu -> 0", tukenme._sayim(spec, {"tur": "x"}, "cubuk") == 0)
    except TypeError as e:
        kontrol("sozluk dolgu -> 0", False, str(e))
    kor = spec["kor"]
    hedef = spec["cubuklar"][0]["ad"]
    kontrol("bellekli sayim > 0 (17x17)", tukenme._kor_sayimi(spec, kor, None, hedef) > 0)


def test_tarama_var_eski_kurala_esdeger():
    print("\n[H1-R5] _tarama_var == bool(_gecerli_taramalar(b, 'katsayi')) butun orneklerde")
    from cekirdek import geometri, uygunluk
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
            b = uygunluk._Baglam(s)
            if uygunluk._tarama_var(b) != bool(uygunluk._gecerli_taramalar(b, "katsayi")):
                farkli.append(ad)
    kontrol("esdeger (sablon + gelismis)", not farkli, farkli)


HIZLI = [test_bellek_lru_ve_anahtar, test_ornek_spec_ve_modelleri_json_saf,
         test_uygunluk_ayni_spec_tek_gezinti, test_gecerli_sekmeler_tek_gezinti,
         test_uygunluk_spec_degisince_yeniden_hesaplar,
         test_uygunluk_donen_nesne_paylasilmaz, test_hacim_katkilar_tek_gezinti,
         test_hacim_model_degisince_yeniden_hesaplar, test_yakit_ornek_sayisi_bellegi,
         test_tembel_sekme_kirli_temiz, test_tembel_sekme_sonucu_hevesliyle_ayni,
         test_hacim_anahtari_agaci_kapsar, test_anahtar_json_disi_ve_karisik_sozluk,
         test_hacim_tablosu_dil_yarisi, test_sayim_hashlenemeyen_dolgu]
YAVAS = [test_bellekli_sonuc_belleksizle_ayni, test_editor_doldurmak_spec_degistirmez,
         test_tarama_var_eski_kurala_esdeger]
