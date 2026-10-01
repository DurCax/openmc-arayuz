# -*- coding: utf-8 -*-
"""
geometri_ui_arayuz.py -- test_geometri_ui.py'nin Qt testleri (Dalga G-3).

Bu dosya test_ onekli DEGILDIR: islevleri test_geometri_ui.HIZLI'ya girer
(conftest ikinci kez toplamasin). Yalniz offscreen; modal diyalog acilmaz.
"""

import copy
import glob
import os
import warnings

from testler.ortak_test import kontrol, ORNEK

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _ozet(spec):
    from cekirdek import onbellek
    return onbellek.ozet(spec)


class _Pencere(object):
    """GecmisMixin'i gercek pencere olmadan sinayan kucuk ev sahibi."""

    def __init__(self, spec):
        from PySide6 import QtCore
        from arayuz.pencere.gecmis import GecmisMixin
        from arayuz.sekme_kor import KorSekmesi
        self.__class__ = type("_GecmisliPencere", (GecmisMixin, _Pencere), {})
        self.spec = spec
        self._gecmis, self._gecmis_ix, self._gecmis_yaziyor = [], -1, False
        self._gecmis_sayac = QtCore.QTimer()
        self._kirli = False
        self.mesajlar = []
        self.kor = KorSekmesi()
        self.kor._onay_al = lambda *_a: True
        self.kor.islem_uygulayici = self.spec_islemi_uygula
        self.kor.degisti.connect(lambda _k: self._gecmis_sayac.start())
        self._spec_uygula()
        self._gecmise_it(ilk=True)

    def _spec_uygula(self):
        self.kor.spec_yukle(self.spec)

    def _baslik_guncelle(self):
        pass

    def bildir_mesaj(self, metin, *_a, **_k):
        self.mesajlar.append(metin)


def _kurulur(spec):
    """Tam model kurulur mu. Agac modunu henuz okumayan bir TUKETICI
    (AgacModuHatasi; G-2'nin isi, or. kaynak.entropi_boyutu) kurulumu
    durdurursa geometri duzeyi sinanir: yapisal denetim temiz ve sematik kesit
    cizilir. G-2 birlesince tam yol kendiliginden sinanir."""
    from cekirdek import geometri, kurucu, sema
    from arayuz.geometri import cizim
    try:
        kurucu.kur(spec)
        return True
    except sema.AgacModuHatasi as e:
        print("    bilgi: G-2 tuketicisi agac modunu okumuyor (%s); geometri duzeyi" % e)
    hatalar = [b for b in geometri.yapisal_denetim(spec) if b.seviye == "hata"]
    return not hatalar and bool(cizim.xy_ogeleri(spec)[0])


# ============================================================================
# gecis ve geri al
# ============================================================================

def test_gelismise_gecis_tek_adimda_geri_alinir():
    print("\n[GU5] gelismise gecis tek yonlu; Geri Al tek adimda sablona doner")
    _qt()
    from cekirdek import geometri
    p = _Pencere(_ornek("tamburlu_kor"))
    k = p.kor
    kontrol("sablon gorunumu acik, editor kapali",
            k.sablon_gorunumu.isVisibleTo(k) and not k.gelismis_gorunumu.isVisibleTo(k))
    k.tb_kor_r.setValue(17.0)          # bekleyen (henuz yigilmamis) duzenleme
    kontrol("bekleyen duzenleme spec'te", p.spec["kor"]["kor_yaricap"] == 17.0)
    once = _ozet(p.spec)
    kontrol("gecis yapildi", k.gelismise_gec(onaysiz=True) and geometri.agac_modu(p.spec))
    kontrol("gelismis modda sihirbaz gizli",
            not k.sablon_gorunumu.isVisibleTo(k) and k.gelismis_gorunumu.isVisibleTo(k))
    kontrol("agac halkadaki kor yaricapini tasiyor",
            p.spec["geometri"]["kok"]["kesit"]["yaricap"] == 17.0)
    kontrol("gelismis modda tekrar gecis yok", not k.gelismise_gec(onaysiz=True))
    p.geri_al()
    kontrol("tek Geri Al: sablon + bekleyen duzenleme",
            not geometri.agac_modu(p.spec) and _ozet(p.spec) == once
            and k.sablon_gorunumu.isVisibleTo(k))
    p.yinele()
    kontrol("Yinele gecisi yeniden uygular", geometri.agac_modu(p.spec)
            and k.gelismis_gorunumu.isVisibleTo(k))


def test_agac_islemleri_geri_alinir():
    print("\n[GU6] agac islemleri (ekle/adlandir/sil/tasi) birer geri al adimi")
    _qt()
    from cekirdek import geometri
    p = _Pencere(geometri.gelismise_gec(_ornek("tamburlu_kor")))
    e = p.kor.gelismis_editor
    e.sec(("kok",))
    e.halka_ekle()
    kontrol("halka eklendi", len(p.spec["geometri"]["kok"]["halkalar"]) == 2)
    kontrol("yeni halka secili", e.secili_yol() == ("kok", "halkalar", 1))
    e.sec(("kok", "halkalar", 0, "yerlesimler", 0))
    e._ad_sor = lambda *_a: "tb8"
    e.yeniden_adlandir()
    kontrol("yerlesim adlandirildi, grup izledi",
            p.spec["geometri"]["gruplar"][0]["uyeler"] == ["tb8"])
    e._tasi(("kok", "halkalar", 0, "yerlesimler", 0), ("kok", "halkalar", 1))
    kontrol("surukle-birak: yerlesim ikinci halkada",
            p.spec["geometri"]["kok"]["halkalar"][1]["yerlesimler"][0]["ad"] == "tb8")
    p.geri_al()
    kontrol("Geri Al tasimayi geri aldi",
            p.spec["geometri"]["kok"]["halkalar"][0]["yerlesimler"][0]["ad"] == "tb8")
    p.geri_al()
    p.geri_al()
    kontrol("uc Geri Al: ilk agac", len(p.spec["geometri"]["kok"]["halkalar"]) == 1
            and p.spec["geometri"]["gruplar"][0]["uyeler"] == ["tamburlar"])
    e.sec(("kok",))
    e.sil()
    kontrol("kok silinemez (hata bildirilir, spec degismez)",
            "silinemez" in (getattr(e, "son_hata", "") or "")
            and len(p.spec["geometri"]["kok"]["halkalar"]) == 1)
    e.sec(("kok", "halkalar", 0, "icerik"))
    e.dugum_ekle("kafes")
    kontrol("+ Dugum: halka icerigi kafes", p.spec["geometri"]["kok"]["halkalar"][0]
            ["icerik"]["tur"] == "kafes")
    kontrol("yapisal denetimde hata yok",
            not [b for b in geometri.yapisal_denetim(p.spec) if b.seviye == "hata"])


def test_form_alani_agaci_yazar():
    print("\n[GU7] form alanlari: yerlesim sayisi, grup degeri, halka kalinligi")
    _qt()
    from cekirdek import geometri
    p = _Pencere(geometri.gelismise_gec(_ornek("tamburlu_kor")))
    e = p.kor.gelismis_editor
    e.sec(("kok", "halkalar", 0, "yerlesimler", 0))
    f = e.formlar["yerlesim"]
    kontrol("yerlesim formu gorunur", f.isVisibleTo(e) and f.sayi.value() == 8)
    f.sayi.setValue(6)
    kontrol("sayi agaca yazildi",
            p.spec["geometri"]["kok"]["halkalar"][0]["yerlesimler"][0]["sayi"] == 6)
    e.sec(("gruplar", 0))
    g = e.formlar["grup"]
    g.deger.deger_ayarla(90.0)
    kontrol("grup degeri yazildi", p.spec["geometri"]["gruplar"][0]["deger"] == 90.0)
    kontrol("kaydirici izledi", g.kaydirici.value() == 900)
    e.sec(("kok", "halkalar", 0))
    h = e.formlar["halka"]
    h.kalinlik.deger_ayarla(10.0)
    kontrol("halka kalinligi yazildi",
            p.spec["geometri"]["kok"]["halkalar"][0]["kalinlik"] == 10.0)
    e.sec(("kok",))
    kap = e.formlar["kap"]
    kontrol("kok formu: sinir bolumu gorunur, donusum gizli",
            kap.sinir.isVisibleTo(kap) and not kap.donusum.isVisibleTo(kap))


# ============================================================================
# kesit: tiklama -> agac, vurgu, kesik
# ============================================================================

def test_kesit_tiklamasi_agacta_secer():
    print("\n[GU8] sematik kesit: tiklama agacta secer; secili vurgulu")
    uyg = _qt()
    import math
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    from cekirdek import geometri
    from arayuz.geometri.editor import GelismisEditor
    spec = geometri.gelismise_gec(_ornek("tamburlu_kor"))
    e = GelismisEditor()
    e.resize(1100, 700)
    e.yukle(spec)
    e.show()
    uyg.processEvents()
    t = e.kesit.tuval
    kontrol("kesit ogeleri var", len(t.ogeler) > 5)
    R = 21.5
    nokta = t.pikseli_bul(R * math.cos(0.0), R * math.sin(0.0)).toPoint()
    QTest.mouseClick(t, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, nokta)
    uyg.processEvents()
    hedef = ("kok", "halkalar", 0, "yerlesimler", 0, "icerik")
    kontrol("tambura tiklama: yerlesim icerigi secildi", e.secili_yol() == hedef,
            "-> %s" % (e.secili_yol(),))
    kontrol("tuval secimi izliyor", t.secili == hedef)
    merkez = t.pikseli_bul(0.0, 0.0).toPoint()
    QTest.mouseClick(t, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, merkez)
    kontrol("merkeze tiklama: kap ici", e.secili_yol() == ("kok", "ic"))
    e.kesit.eksen.sec("xz")
    kontrol("xz kesiti 3B modelde cizilir", len(t.ogeler) > 0)
    e.close()


def test_kesik_konumlar_isaretlenir():
    print("\n[GU9] kare cekirdek + altigen halka: kesik konumlar UYARI olarak isaretli")
    _qt()
    from arayuz.geometri import cizim, sablonlar
    from arayuz.geometri.editor import GelismisEditor
    spec = sablonlar.uret(_ornek("pwr_ceyrek_kor"), "kare_altigen")
    ogeler, _k, _o = cizim.xy_ogeleri(spec)
    kesik = [o for o in ogeler if o.kesik == "kesik"]
    gizli = [o for o in ogeler if o.kesik == "gizli"]
    kontrol("sematik kesitte 16 kesik blok taranir (§16 sapma 1: 12 + 4)", len(kesik) == 16,
            "-> %d" % len(kesik))
    kontrol("gizli konum isaretli degil (delik altinda, cizilmez)", len(gizli) == 0)
    e = GelismisEditor()
    e.yukle(spec)
    kontrol("alt serit kesik sayisini yazar", "16" in e.kesik_etiketi.text(),
            "-> %s" % e.kesik_etiketi.text())
    yol = e.kesige_git()
    kontrol("Git: blok kafesini secer", yol == ("kok", "ic"))
    f = e.formlar["kafes"]
    kontrol("kafes formu kesik notu", "16" in f.kesik_notu.text(), "-> %s" % f.kesik_notu.text())
    kontrol("izgara isaretleri 16 kesik + 7 gizli",
            sum(1 for v in f.altigen._isaretler.values() if v == "kesik") == 16
            and sum(1 for v in f.altigen._isaretler.values() if v == "gizli") == 7)


def test_onizleme_hucre_yolu():
    print("\n[GU10] onizleme: nokta -> hucre -> dugum yolu (openmc.lib gerekmez)")
    from cekirdek import geometri, kurucu
    from arayuz.geometri.onizleme_secim import agac_yolu, nokta_yolu
    spec = geometri.gelismise_gec(_ornek("tamburlu_kor"))
    agac = spec["geometri"]
    kontrol("dizin yolu -> yerlesim icerigi",
            agac_yolu("/kok/halkalar/0/yerlesim/tamburlar#3", agac)
            == ("kok", "halkalar", 0, "yerlesimler", 0, "icerik"))
    kontrol("bilinmeyen kuyruk en yakin ataya duser",
            agac_yolu("/kok/ic/yok/3", agac) == ("kok", "ic"))
    model, bilgi = kurucu.kur(spec)
    dizin = bilgi.get("geometri_dizini")
    kontrol("tambur merkezi -> yerlesim", nokta_yolu(model, dizin, agac, (21.5, 0.0, 0.0))
            == ("kok", "halkalar", 0, "yerlesimler", 0, "icerik"))
    kontrol("kor merkezi -> kap ici", nokta_yolu(model, dizin, agac, (0.0, 0.0, 0.0))
            == ("kok", "ic"))


# ============================================================================
# sablonlar, sinir, pin kesiti
# ============================================================================

def test_uc_yeni_sablon_kurulur():
    print("\n[GU11] uc yeni duzenek: agac, denetim temiz, kurulur; sayfadan tek adim")
    _qt()
    from cekirdek import geometri, kurucu
    from arayuz.geometri import sablonlar
    from arayuz.geometri.sablon_diyalogu import SablonDiyalogu
    for ornek, anahtar in (("pwr_ceyrek_kor", "kare_altigen"), ("sfr_altigen", "altigen_tambur"),
                           ("pwr_ceyrek_kor", "kafes_tambur")):
        spec = _ornek(ornek)
        once = _ozet(spec)
        yeni = sablonlar.uret(spec, anahtar)
        hatalar = [b.mesaj for b in geometri.yapisal_denetim(yeni) if b.seviye == "hata"]
        kontrol("%s: girdi degismedi, agac modu" % anahtar,
                _ozet(spec) == once and geometri.agac_modu(yeni))
        kontrol("%s: yapisal denetim temiz" % anahtar, not hatalar, "-> %s" % hatalar[:2])
        try:
            _m, bilgi = kurucu.kur(yeni)
            kuruldu = bilgi.get("sinir_kutu") is not None
        except Exception as e:                    # rapor icin
            kuruldu = False
            print("    kurulamadi: %s" % e)
        kontrol("%s: OpenMC modeli kurulur" % anahtar, kuruldu)
        d = SablonDiyalogu(spec, anahtar)
        kontrol("%s: diyalog varsayilanlarla ayni agaci uretir" % anahtar,
                d.spec_uret()["geometri"] == yeni["geometri"])
    p = _Pencere(_ornek("sfr_altigen"))
    kontrol("sayfa: yeni sablon tek adimda", p.kor.yeni_sablon_uygula("altigen_tambur",
                                                                       diyalogsuz=True)
            and geometri.agac_modu(p.spec) and len(p.spec["tamburlar"]) == 1)
    p.geri_al()
    kontrol("Geri Al: sablon oncesi", not geometri.agac_modu(p.spec))
    bos = _ornek("tamburlu_kor")
    kontrol("demetsiz modelde kare sablon hatayi soyler",
            not p.kor.yeni_sablon_uygula("kare_altigen", diyalogsuz=True)
            or bool(bos.get("demetler")))


def test_yedi_sablon_sayfadan_ve_gecis():
    print("\n[GU12] 7 sablon turu sayfada; her biri gelismise gecip kurulur")
    _qt()
    from cekirdek import geometri, kurucu
    from arayuz import baslangic
    from arayuz.sekme_kor import KorSekmesi
    k = KorSekmesi()
    turler = {k.sablon_secici.itemData(i) for i in range(k.sablon_secici.count())}
    kontrol("secicide 10 duzenek (7 + 3)", len(turler) == 10)
    for kart in baslangic.KARTLAR:
        if not kart["bos"]:
            continue
        spec = baslangic.bos_sablon(kart["anahtar"])
        k.spec_yukle(spec)
        tur = spec["kor"]["tur"]
        kontrol("%s: secici turu gosteriyor" % tur, k.sablon_secici.currentData() == tur)
        agacli = geometri.gelismise_gec(spec)
        k.spec_yukle(agacli)
        kontrol("%s: gelismis editor + kurulum" % tur,
                k.gelismis_gorunumu.isVisibleTo(k) and _kurulur(agacli))


def test_yuz_basina_sinir():
    print("\n[GU13] yuz basina sinir: dikdortgen 4 yuz, altigen 6 yuz, periyodik cifti")
    _qt()
    from cekirdek import geometri, kurucu
    from arayuz.geometri.sinir_formu import SinirFormu, secenekler, tek_tarafli_periyodik
    from testler import geometri_ortak as go
    f = SinirFormu()
    gelen = []
    f.degisti.connect(gelen.append)
    ceyrek = go.duzenek_e_ceyrek()
    f.ayarla({"yan": "vacuum"}, secenekler(ceyrek), True)
    f.yuz_basina.setChecked(True)
    f._yuz_kutulari[0].setCurrentIndex(f._yuz_kutulari[0].findData("reflective"))
    kontrol("dikdortgen: 4 yuz, -x yansitici",
            len(f._yuz_kutulari) == 4 and gelen[-1]["yuzler"]["-x"] == "reflective"
            and gelen[-1]["yuzler"]["+x"] == "vacuum")
    f._yuz_kutulari[0].setCurrentIndex(f._yuz_kutulari[0].findData("periodic"))
    kontrol("tek tarafli periyodik isaretlenir", bool(f.not_etiketi.text()))
    altigen = copy.deepcopy(ceyrek)
    altigen["geometri"]["kok"]["kesit"] = {"sekil": "altigen", "apotem": 200.0, "yonelim": "x"}
    s = secenekler(altigen)
    f.ayarla({"yan": "vacuum"}, s, False)
    kontrol("altigen: 6 yuz, adlar sinir_bilgisi'nden",
            len(f._yuz_kutulari) == 6 and s.yuz_adlari == geometri.sinir_bilgisi(
                geometri.model(altigen)).yuz_adlari, "-> %s" % (s.yuz_adlari,))
    f.ayarla({"yan": "vacuum"}, secenekler(go.duzenek_c()), False)
    kontrol("silindirde yuz basina yok", not f.yuz_basina_uygun())
    # dis sinira degen delik: periyodik ne yanda ne yuzlerde sunulur (uygunluk)
    delikli = go.duzenek_e_ceyrek()
    delikli["geometri"]["kok"]["yerlesimler"].append(
        {"ad": "kenar", "mod": "liste", "konumlar": [[42.0, 0.0]],
         "kesit": {"sekil": "silindir", "yaricap": 2.0},
         "icerik": {"tur": "malzeme", "ad": "bosluk"}})
    s = secenekler(delikli)
    kontrol("delik dis sinira degiyor: periodic sunulmaz",
            "periodic" not in s.yan and all("periodic" not in v for v in s.yuzler.values())
            and "periodic" in secenekler(ceyrek).yan, "-> %s %s" % (s.yan, s.yuzler))
    kontrol("bozuk spec: bos secenek, cokmez",
            secenekler({"kor": {"tur": "agac"}, "geometri": {"kok": 5}}).duzen is None)
    kontrol("cift kurali", tek_tarafli_periyodik(["periodic"] + ["vacuum"] * 5, "altigen") == [0])
    from arayuz.sekme_kor import KorSekmesi
    spec = _ornek("pwr_ceyrek_kor")
    k = KorSekmesi()
    k.spec_yukle(spec)
    kontrol("sablon: cekirdek kare -> yuz basina sunuluyor", k.yuz_sinir.yuz_basina_uygun())
    k.yuz_sinir.yuz_basina.setChecked(True)
    kutular = k.yuz_sinir._yuz_kutulari
    for i, deger in enumerate(("reflective", "vacuum", "reflective", "vacuum")):
        kutular[i].setCurrentIndex(kutular[i].findData(deger))
    yuz = spec["kor"]["sinir"].get("yuzler")
    kontrol("kor.sinir.yuzler yazildi (ceyrek kor: iki simetri yuzu)",
            yuz == {"-x": "reflective", "+x": "vacuum", "-y": "reflective", "+y": "vacuum"},
            "-> %s" % yuz)
    kontrol("yapisal denetim temiz",
            not [b for b in geometri.yapisal_denetim(spec) if b.seviye == "hata"])
    model, _b = kurucu.kur(spec)
    bcler = sorted({s.boundary_type for s in model.geometry.get_all_surfaces().values()
                    if s.boundary_type != "transmission"})
    kontrol("kurulan modelde iki sinir turu", bcler == ["reflective", "vacuum"], "-> %s" % bcler)
    k.yuz_sinir.yuz_basina.setChecked(False)
    kontrol("kapatinca yuzler silinir", "yuzler" not in spec["kor"]["sinir"])


def test_pin_kesiti_parcalarda():
    print("\n[GU14] Parcalar: pin kesiti silindir / kare / altigen")
    _qt()
    from arayuz.sekme_cubuk import CubukSekmesi
    spec = _ornek("pwr_pinhucre")
    s = CubukSekmesi()
    s.spec_yukle(spec)
    ad = spec["cubuklar"][0]["ad"]
    s.sec("cubuk", ad) if hasattr(s, "sec") else None
    kontrol("varsayilan silindir, yonelim gizli",
            s.c_kesit.currentData() == "silindir" and not s.c_kesit_yonelim.isVisibleTo(s))
    s.c_kesit.setCurrentIndex(s.c_kesit.findData("altigen"))
    c = spec["cubuklar"][0]
    kontrol("altigen yazildi + yonelim", c.get("kesit") == "altigen"
            and c.get("kesit_yonelim") in ("x", "y"), "-> %s" % c)
    s.c_kesit.setCurrentIndex(s.c_kesit.findData("kare"))
    kontrol("kare yazildi, yonelim silindi", c.get("kesit") == "kare"
            and "kesit_yonelim" not in c)


def test_spec_gidis_donusu_27_ornek():
    print("\n[GU15] 27 ornek: sayfa yuklemek spec'i degistirmez (sablon ve gelismis)")
    _qt()
    from cekirdek import geometri, sema
    from arayuz.sekme_kor import KorSekmesi
    import tempfile
    k = KorSekmesi()
    adlar = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(ORNEK, "*.json")))
    bozulan = []
    for ad in adlar:
        spec = _ornek(ad)
        once = _ozet(spec)
        k.spec_yukle(spec)
        agac = geometri.gelismise_gec(spec)
        agac_once = copy.deepcopy(agac)
        k.spec_yukle(agac)
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "a.json")
            sema.kaydet(agac, yol)
            geri = sema.yukle(yol)
        if _ozet(spec) != once or agac != agac_once or \
                geri.get("geometri") != agac.get("geometri"):
            bozulan.append(ad)
    kontrol("%d ornek: gidis-donus bozulmaz" % len(adlar), not bozulan and len(adlar) >= 27,
            "-> %s" % bozulan)


HIZLI = [test_gelismise_gecis_tek_adimda_geri_alinir, test_agac_islemleri_geri_alinir,
         test_form_alani_agaci_yazar, test_kesit_tiklamasi_agacta_secer,
         test_kesik_konumlar_isaretlenir, test_onizleme_hucre_yolu, test_uc_yeni_sablon_kurulur,
         test_yedi_sablon_sayfadan_ve_gecis, test_yuz_basina_sinir, test_pin_kesiti_parcalarda,
         test_spec_gidis_donusu_27_ornek]
