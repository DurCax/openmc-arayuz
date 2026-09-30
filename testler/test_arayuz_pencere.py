# -*- coding: utf-8 -*-
"""
 test_arayuz_pencere.py  --  18. ARAYUZ HATA AVI (pencere duzeyi): proje sifirlama, ornek kopyasi, bulgular, kafes onayi

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import os
import shutil
import tempfile

from cekirdek import sema, kurucu
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK, _ana_pencere, _pencere_kapat, _qt


# ============================================================================
# 18. ARAYUZ HATA AVI -- veriyi SESSIZCE degistiren / kaybeden / yanlis
#     sonuc gosteren hatalar (kullanilabilirlik denetimi, dalga 1)
#
#   Her test once DUZELTMEDEN ONCEKI kodda calistirilip KALDIGI gorulmustur;
#   duzeltmeden once gecen bir test hicbir sey kanitlamaz.
# ============================================================================

def test_arayuz_proje_sifirlama():
    """
    [11] Onceki projenin sonuclari ekranda kaliyordu: Calistir/Analiz yeni
    projede de eski k-eff'i ve katsayiyi gosteriyor, _son_basarili tasiniyor
    ve rehber seridi hic kosulmamis modele "Kosu tamam" diyordu.
    (Dalga 2: rehber seridi kaldirildi; ayni bilgi artik Calistir sekmesinin
    basligindaki isarette -- "✓" yalnizca bu projede basarili kosu varsa.)
    """
    print("\n[18l] ARAYUZ: proje degisince sonuclar sifirlaniyor")
    uyg = _qt()
    if uyg is None:
        return
    p = _ana_pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        c, an = p.s_calistir, p.s_analiz
        c._son_basarili = True
        c.keff_etiket.setText("1.35700 +/- 0.00100")
        c.durum_etiket.setText("KRITIK USTU")
        c.sonuc_metin.setPlainText("k-eff = 1.35700")
        an._sonuclar = [{"deger": 0.0, "keff": 1.3, "sapma": 0.001}]
        an._tabloya_ekle(an._sonuclar[0])
        an.sonuc_kutusu.setText("<b>KATSAYI = -8.000 pcm/ppm</b>")
        p.onizleme.cizildi_mi = lambda: True
        p._isaretleri_guncelle()
        kontrol("(on kosul) Calistir sekmesi 'tamam' (✓)",
                p.sekme_isareti("calistir")[0] == "✓",
                "-> %r" % (p.sekme_isareti("calistir"),))

        # sekme degisimi SONUCU SILMEMELI
        for k in ("calistir", "malzemeler", "analiz", "calistir"):
            p.sekmeye_git(k)
        kontrol("sekme degisimi sonucu silmiyor",
                c._son_basarili and "1.35700" in c.keff_etiket.text()
                and an.tablo.rowCount() == 1)

        p.proje_ac(os.path.join(ORNEK, "godiva_kriter.json"))
        kontrol("yeni proje: _son_basarili sifirlandi", not c._son_basarili)
        kontrol("yeni proje: k-eff etiketi sifirlandi", "1.357" not in c.keff_etiket.text(),
                "-> %r" % c.keff_etiket.text())
        kontrol("yeni proje: calistir sonuc metni bos", c.sonuc_metin.toPlainText() == "")
        kontrol("yeni proje: durum etiketi bos", c.durum_etiket.text() == "")
        kontrol("yeni proje: analiz sonuclari silindi",
                an._sonuclar == [] and an.tablo.rowCount() == 0)
        kontrol("yeni proje: analiz katsayisi silindi", "katsay" not in an.sonuc_kutusu.text().lower())
        kontrol("yeni proje: Calistir sekmesi 'tamam' DEMIYOR (✓ yok)",
                p.sekme_isareti("calistir")[0] != "✓",
                "-> %r" % (p.sekme_isareti("calistir"),))
    finally:
        _pencere_kapat(p)


def test_arayuz_ornek_kopya():
    """
    [12] 'Dosya > Ornek ac' gercek ornek dosyasini aciyordu: Ctrl+S
    ornekler/*.json'u (testlerin referanslarini) USTUNE YAZIYORDU. Ornek artik
    kaydedilmemis bir KOPYA olarak acilir; Kaydet 'Farkli kaydet'e gider.
    (Dalga 2: ornekler baslangic ekraninin listesinden acilir.)
    """
    print("\n[18m] ARAYUZ: ornek dosyalar kopya olarak aciliyor")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    yol = os.path.join(ORNEK, "pwr_17x17.json")
    with open(yol, "rb") as f:
        ham = f.read()
    gecici = tempfile.mkdtemp(prefix="ornek_kopya_")
    hedef = os.path.join(gecici, "benim_modelim.json")
    eski_diyalog = QtWidgets.QFileDialog.getSaveFileName
    cagrilar = []
    p = None
    eski_dizin = os.getcwd()
    try:
        p = _ana_pencere()
        oge = [k for k in p.baslangic.ornek_kartlari() if k.bilgi.dosya == "pwr_17x17.json"]
        kontrol("(on kosul) baslangic ekraninin ornek galerisinde PWR 17x17 var", len(oge) == 1)
        oge[0].secildi.emit()
        kontrol("ornek acildi (demet_17x17)", p.spec["kor"].get("demet") == "demet_17x17")
        kontrol("ornek KOPYA: proje_yolu None", p.proje_yolu is None, "-> %r" % p.proje_yolu)
        kontrol("baslikta 'örnek: pwr_17x17'", "örnek: pwr_17x17" in p.windowTitle(),
                "-> %r" % p.windowTitle())

        def sahte_diyalog(*a, **k):
            cagrilar.append(a)
            return (hedef, "JSON model (*.json)")
        QtWidgets.QFileDialog.getSaveFileName = sahte_diyalog
        p.spec["ad"] = "degistirilmis kopya"
        p._kirli = True
        p.proje_kaydet()
        with open(yol, "rb") as f:
            kontrol("ornek dosyasi DEGISMEDI", f.read() == ham)
        kontrol("Kaydet 'Farkli kaydet' diyalogunu acti", len(cagrilar) == 1)
        kontrol("kopya secilen yere yazildi",
                os.path.exists(hedef) and sema.yukle(hedef)["ad"] == "degistirilmis kopya")
        kontrol("proje artik kullanicinin dosyasi", p.proje_yolu == hedef)

        # Tukenme: onceki sonuclar ORNEGIN dizininden OKUNUR (yazma degil)
        os.chdir(gecici)
        p.proje_ac(os.path.join(ORNEK, "pwr_tukenme.json"))
        from cekirdek import tukenme as _tk
        beklenen = _tk.kosu_dizini(p.spec, os.path.join(ORNEK, "pwr_tukenme.json"))
        okuma = getattr(p.s_tukenme, "_okuma_dizini", lambda: None)()
        kontrol("tukenme onceki sonucu ornegin dizininden okuyor", okuma == beklenen,
                "-> %r" % okuma)
        kontrol("tukenme YENI kosuyu ornek dizinine yazmiyor",
                _tk.kosu_dizini(p.spec, p.s_tukenme.proje_yolu) != beklenen)
    finally:
        os.chdir(eski_dizin)
        QtWidgets.QFileDialog.getSaveFileName = eski_diyalog
        with open(yol, "rb") as f:
            if f.read() != ham:                 # duzeltmeden once: ornegi geri yukle
                with open(yol, "wb") as g:
                    g.write(ham)
        if p is not None:
            _pencere_kapat(p)
        shutil.rmtree(gecici, ignore_errors=True)


def test_arayuz_bulgu_sekme():
    """
    [13] Dogrulama satirina tiklamak 'kaynak', 'tally:', 'guc dagilimi',
    'tukenme' bulgularinda hicbir sey yapmiyordu; rehber tukenme hatalarini
    Tukenme (8.) yerine Ayarlar (5.) sekmesine gonderiyordu.
    (Dalga 2: uygun olmayan sekmeler gizlenir -- butun sekmeleri gosteren
    bir ornek acilir. Rehberin yerini sekme isaretleri aldi: tukenme hatasi
    Tukenme sekmesinin basliginda "!" olarak gorunmeli.)
    """
    print("\n[18n] ARAYUZ: dogrulama bulgusu dogru sekmeye gidiyor")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore, QtWidgets
    p = _ana_pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        beklenen = {
            "malzeme:uo2": "malzemeler", "malzemeler": "malzemeler",
            "cubuk:yakit_cubugu": "parcalar", "plaka:mtr_eleman": "parcalar",
            "demet:demet_17x17": "demet", "kor": "kor", "kor/katman 1 (aktif)": "kor",
            "ayarlar": "ayarlar", "veri kutuphanesi": "ayarlar", "kaynak": "ayarlar",
            "tally:aki": "ayarlar", "guc dagilimi": "ayarlar", "guc_dagilimi": "ayarlar",
            "tukenme": "tukenme", "tukenme/uo2": "tukenme",
        }
        for yer, hedef in beklenen.items():
            p.sekmeye_git("calistir" if hedef != "calistir" else "analiz")
            oge = QtWidgets.QListWidgetItem("x")
            oge.setData(QtCore.Qt.UserRole, yer)
            p._bulguya_git(oge)
            kontrol("'%s' -> sekme %s" % (yer, hedef), p.gecerli_sekme() == hedef,
                    "-> %s" % p.gecerli_sekme())
        s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
        s["tukenme"]["guc_yogunlugu"] = -1.0
        p.spec = s
        p._dogrula(veri=False)
        hatalar = [b for b in p._bulgular if b.seviye == "hata"]
        kontrol("(on kosul) ilk hata tukenme", bool(hatalar) and hatalar[0].yer == "tukenme",
                "-> %s" % ([b.yer for b in hatalar],))
        isaretli = [k for k in p.sekme_anahtarlari() if p.sekme_isareti(k)[0] == "!"]
        kontrol("tukenme hatasi Tukenme sekmesinde '!' isareti olarak gorunuyor",
                isaretli == ["tukenme"], "-> %s" % isaretli)
    finally:
        _pencere_kapat(p)


def test_arayuz_bulgu_ipucu():
    """[14] Oncelik hatasi: oneri varken 'Tiklayinca ...' ipucu dusuyordu."""
    print("\n[18o] ARAYUZ: dogrulama satiri ipucu")
    uyg = _qt()
    if uyg is None:
        return
    p = _ana_pencere()
    try:
        s = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
        for m in s["malzemeler"]:
            if m["ad"] == "su":
                m["sab"] = []                   # oneri iceren bir UYARI uretir
        p.spec = s
        p._dogrula(veri=False)
        onerili = [(i, b) for i, b in enumerate(p._bulgular) if b.oneri]
        kontrol("(on kosul) onerili bulgu var", bool(onerili))
        for i, b in onerili[:3]:
            ipucu = p.dogrulama.item(i).toolTip()
            kontrol("'%s' ipucu oneri + tiklama bilgisi" % b.yer,
                    b.oneri in ipucu and "ilgili sayfaya gider" in ipucu, "-> %r" % ipucu[-60:])
        onerisiz = [(i, b) for i, b in enumerate(p._bulgular) if not b.oneri]
        if onerisiz:
            kontrol("onerisiz bulguda da tiklama bilgisi",
                    "ilgili sayfaya gider" in p.dogrulama.item(onerisiz[0][0]).toolTip())
    finally:
        _pencere_kapat(p)


def test_arayuz_kontrol_cubugu_uc():
    """
    [15] Cubuk sekmesindeki uc konumu TOPLAM yukseklikten hesaplaniyordu;
    kurucu AKTIF yakit araligini kullanir. Katmanli modelde %50'de etiket
    z=+0.00 derken kurucu ucu z=-2.5'e koyuyordu.
    """
    print("\n[18p] ARAYUZ: kontrol cubugu uc etiketi = kurucunun uc konumu")
    uyg = _qt()
    if uyg is None:
        return
    import re
    from PySide6 import QtCore
    from arayuz.sekme_cubuk import CubukSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    spec["kor"]["yukseklik"] = None
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt yansitici", 25.0, "su"),
        sema.eksenel_bolge("aktif", 300.0, None),
        sema.eksenel_bolge("plenum", 30.0, "su"),
    ]}
    kc = [c for c in spec["cubuklar"] if c.get("tur") == "kontrol"][0]
    w = CubukSekmesi()
    w.spec_yukle(spec)
    for i in range(w.liste.count()):
        if w.liste.item(i).data(QtCore.Qt.UserRole) == ("cubuk", kc["ad"]):
            w.liste.setCurrentRow(i)
    for daldirma in (0.0, 50.0, 100.0):
        w.c_daldirma.setValue(daldirma)
        univ = kurucu.cubuk_universe(spec, kc["ad"], kurucu.malzemeleri_kur(spec)[0])
        z0lar = sorted({float(srf.z0) for c in univ.cells.values()
                        for srf in c.region.get_surfaces().values()
                        if srf.type == "z-plane"})
        m = re.search(r"z = ([+-]?\d+\.\d+)", w.c_uc_etiket.text())
        z_etiket = float(m.group(1)) if m else None
        kontrol("daldirma %%%g: etiket z = kurucu z (%s)" % (daldirma, z0lar),
                z_etiket is not None and len(z0lar) == 1 and abs(z_etiket - z0lar[0]) < 0.006,
                "-> etiket %r" % w.c_uc_etiket.text())
    uyg  # noqa: B018


def test_arayuz_kafes_onay():
    """
    [16] 'Kafes tipi' degisimi haritayi SORMADAN siliyordu (17x17 -> altigen:
    tum kilavuz borular gitti, geri donmek geri getirmiyor); nx kucultmek
    haritayi sessizce kirpiyordu. Kafes secili degilken form duzenlenebiliyordu.
    """
    print("\n[18q] ARAYUZ: kafes haritasini silen islemler onay istiyor")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    from arayuz.sekme_demet import DemetSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    d = spec["demetler"][0]
    harita0 = list(d["harita"])
    w = DemetSekmesi()
    w.spec_yukle(spec)
    sorular = []

    def hayir(baslik_, metin):
        sorular.append(baslik_)
        return False

    def evet(baslik_, metin):
        sorular.append(baslik_)
        return True

    w._onay_al = hayir
    # Dalga 3: "Kafes tipi" kutusu KALDIRILDI (tip "+ Kare/Altigen demet" ile
    # belirlenir). Korunan davranis ayni: harita bir tip degisimiyle silinemez.
    tip_kutulari = [k for k in w.findChildren(QtWidgets.QComboBox) if k.findData("altigen") >= 0]
    kontrol("tip degistiren kutu yok (harita tip degisimiyle silinemez)",
            not hasattr(w, "tur") and not tip_kutulari)
    kontrol("tip kare kaldi", d["tur"] == "kare", "-> %s" % d["tur"])
    kontrol("harita AYNI (kilavuz borular yerinde)", d["harita"] == harita0)
    kontrol("arayuz tipi kare gosteriyor", w.oz_baslik.text() == "Kare demet")

    sorular.clear()
    w.nx.setValue(15)
    kontrol("nx kucultme onay sordu", len(sorular) == 1)
    kontrol("reddedilince boyut 17x17 kaldi", d["boyut"] == [17, 17], "-> %s" % d["boyut"])
    kontrol("reddedilince harita AYNI", d["harita"] == harita0)
    kontrol("reddedilince nx kutusu 17'ye dondu", w.nx.value() == 17)

    sorular.clear()
    w.nx.setValue(18)
    kontrol("nx buyutme onay SORMUYOR (veri kaybi yok)", len(sorular) == 0)
    w.nx.setValue(17)                     # buyutulen sutunu geri al (onay: kucultme)
    w._onay_al = evet
    w.nx.setValue(17)

    sorular.clear()
    ad_hex = w._yeni("altigen")
    yeni_hex = sema.demet_bul(spec, ad_hex) if ad_hex else None
    kontrol("altigen demet '+ Altigen demet' ile kuruluyor; eski kare harita yerinde",
            yeni_hex is not None and yeni_hex["tur"] == "altigen" and d["tur"] == "kare"
            and d["harita"] == harita0 and len(sorular) == 0)

    # hic kafes yokken form devre disi
    bos = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    w2 = DemetSekmesi()
    w2.spec_yukle(bos)
    kontrol("(on kosul) kafes yok", not bos.get("demetler"))
    kontrol("kafes secili degilken form devre disi",
            not w2.palet.isEnabled() and not w2.nx.isEnabled() and not w2.adim.isEnabled(),
            "-> palet %s nx %s" % (w2.palet.isEnabled(), w2.nx.isEnabled()))
    uyg  # noqa: B018


HIZLI = [
    test_arayuz_proje_sifirlama, test_arayuz_ornek_kopya, test_arayuz_bulgu_sekme,
    test_arayuz_bulgu_ipucu, test_arayuz_kontrol_cubugu_uc, test_arayuz_kafes_onay,
]
YAVAS = []
