# -*- coding: utf-8 -*-
"""
test_kor_ayar.py -- Dalga 3 / Ajan 6: Kor ve Hesap ayarlari sekmeleri,
geometri onizlemesi.

  * Kor sekmesinde tur secimi yok; tur model basligindan degisir ve sekme
    spec_yukle ile dogru yerlesimi kurar.
  * Gorunen alanlar uygunluk.kor_alanlari / kor_ortak_alanlari /
    sinir_secenekleri ile AYNI; gizli alan spec'e yazilmaz.
  * Yukseklik tek secim (2B / 3B tek bolge / 3B katmanli); katman tablosu
    fiziksel sirada, "Yukari tasi" katmani GERCEKTEN yukari tasir.
  * Kor haritasi boyanir (palet + izgara); boyut haritadan turetilir,
    hucre kaybettiren kucultme onay ister.
  * Hesap hassasiyeti onayarlari; beklenen belirsizlik olcumle tutarli.
  * Moda gore gizlenen ayarlar spec'ten SILINMEZ; calistirma ayarlarina
    dokunulmaz.
  * Onizleme 3B'de xy + xz yan yana; tally'siz model ve yeniden giris
    korumasi korunur.

Yalnizca offscreen calisir; modal diyaloglar exec() EDILMEZ.
"""

import copy
import glob
import os
import re
import time
import warnings

from testler.ortak_test import kontrol, KOK, ORNEK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    try:
        from PySide6 import QtWidgets
    except Exception as e:                         # pragma: no cover
        kontrol("PySide6 yok, kor/ayar testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _ornek_adlari():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(ORNEK, "*.json")))


def _sablonlar():
    from arayuz import baslangic
    return [("sablon:" + k["anahtar"], baslangic.bos_sablon(k["anahtar"]))
            for k in baslangic.KARTLAR if k["bos"]]


def _butun_specler():
    return _sablonlar() + [(ad, _ornek(ad)) for ad in _ornek_adlari()]


def _sablon_modu_specler():
    """Sablon (kor.tur) modundaki specler. Sablon formunu sinayan testler
    bunlari kullanir: agac (gelismis) modunda sablon gorunumu gizlidir ve
    alanlari doldurulmaz (arayuz/kor/geometri_sayfasi._geometri_doldur);
    agac modunun sinir/alan davranisi test_geometri_ui/temizlik'te sinanir."""
    from cekirdek import geometri
    return [(ad, s) for ad, s in _butun_specler() if not geometri.agac_modu(s)]


def _kor(spec):
    from arayuz.sekme_kor import KorSekmesi
    k = KorSekmesi()
    k.spec_yukle(spec)
    return k


def _ayar(spec):
    from arayuz.sekme_ayar import AyarSekmesi
    a = AyarSekmesi()
    a.spec_yukle(spec)
    return a


def _oge_verileri(kutu):
    return [kutu.itemData(i) for i in range(kutu.count())]


def _tur_degistir(k, spec, tur, hafiza=None):
    """Model basligindaki 'Turu degistir...' yolu: ana_pencere.kor_turu_degistir
    + editorun spec_yukle'si (ana_pencere._spec_uygula ile ayni sira)."""
    from arayuz.ana_pencere import kor_turu_degistir
    kor_turu_degistir(spec, tur, hafiza)
    k.spec_yukle(spec)


# ============================================================================
# KOR
# ============================================================================

def test_kor_tur_bilgisi():
    print("\n[A6-1] KOR: tur secimi yok; tur bilgisi ve yerlesim spec'ten")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    from cekirdek import uygunluk
    from arayuz.ana_pencere import TUR_ADLARI
    spec = _ornek("pwr_17x17")
    k = _kor(spec)
    tur_kutusu = [w for w in k.findChildren(QtWidgets.QComboBox)
                  if "tek_cubuk" in _oge_verileri(w) or "kare_kafes" in _oge_verileri(w)]
    # Dalga G-3 (§10, KAPI G-A onayi): tek tur secicisi "Duzenek sablonu"dur ve
    # turu KENDISI degistirmez -- pencerenin kor_turunu_degistir yoluna
    # (tur_secildi) iletir: tek yol, tek kural korunur.
    istenen = []
    k.tur_secildi.connect(istenen.append)
    k.sablon_secici.setCurrentIndex(k.sablon_secici.findData("kare_kafes"))
    k.sablon_secici.activated.emit(k.sablon_secici.currentIndex())
    kontrol("tek tur secicisi (duzenek sablonu); turu pencereye iletir, spec degismez",
            tur_kutusu == [k.sablon_secici] and not hasattr(k, "tur")
            and istenen == ["kare_kafes"] and spec["kor"]["tur"] == "tek_demet",
            "-> %s %s" % (istenen, spec["kor"]["tur"]))
    kontrol("tur bilgisi: ad + nereden degisir",
            TUR_ADLARI["tek_demet"] in k.tur_etiket.text()
            and "model başlığı" in k.tur_etiket.text(), "-> %s" % k.tur_etiket.text())
    hafiza = {}
    for tur in uygunluk.KOR_TURLERI:
        _tur_degistir(k, spec, tur, hafiza)
        alan = set(uygunluk.kor_alanlari(tur))
        kontrol("%s: sekme turu spec'ten okuyor" % tur,
                k.gosterilen_tur() == tur and TUR_ADLARI[tur] in k.tur_etiket.text())
        kontrol("%s: harita kutusu yalnizca haritali turde" % tur,
                k.kafes_kutu.isVisibleTo(k) == ("harita" in alan))
        kontrol("%s: tambur kutusu yalnizca tamburluda" % tur,
                k.tambur_kutu.isVisibleTo(k) == ("tambur" in alan))
    uyg  # noqa: B018


def test_kor_gorunen_alanlar():
    print("\n[A6-2] KOR: her turde yalnizca o turun alanlari (uygunluk)")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import uygunluk
    for ad, spec in _sablon_modu_specler():
        k = _kor(spec)
        tur = spec["kor"]["tur"]
        alan = set(uygunluk.kor_alanlari(tur))
        ortak = uygunluk.kor_ortak_alanlari(spec)
        beklenen = {
            "cubuk": ("cubuk" in alan, k.satir_cubuk[1].isVisibleTo(k)),
            "plaka": ("plaka" in alan, k.satir_plaka[1].isVisibleTo(k)),
            "demet": ("demet" in alan, k.satir_demet[1].isVisibleTo(k)),
            "adim": ("adim" in alan, k.satir_adim[1].isVisibleTo(k)),
            "dolgu": ("dolgu" in alan, k.satir_tb_dolgu[1].isVisibleTo(k)),
            "kor_yaricap": ("kor_yaricap" in alan, k.satir_tb_kor_r[1].isVisibleTo(k)),
            "harita": ("harita" in alan, k.kafes_kutu.isVisibleTo(k)),
            "tambur": ("tambur" in alan, k.tambur_kutu.isVisibleTo(k)),
            "kabuklar": ("kabuklar" in alan, k.kabuk_kutu.isVisibleTo(k)),
            "yansitici": ("yansitici" in alan, k.yans_kutu.isVisibleTo(k)),
            "yukseklik": (ortak["yukseklik"], k._eksen_form.isRowVisible(k.yukseklik_modu)),
            "sinir_alt": (ortak["sinir_alt"], k._eksen_form.isRowVisible(k.bc_alt)),
            "sinir_ust": (ortak["sinir_ust"], k._eksen_form.isRowVisible(k.bc_ust)),
        }
        yanlis = {a: v for a, v in beklenen.items() if v[0] != v[1]}
        kontrol("%s (%s): gorunen alanlar = uygunluk" % (ad, tur), not yanlis,
                "-> (beklenen, gorunen) %s" % yanlis)
        if "yansitici" in alan:
            kontrol("%s: 'Yansitici kusak ekle' yalnizca istege bagli turde" % ad,
                    k.yans_var.isVisibleTo(k) == (tur != "tamburlu"))
        if tur == "kuresel":
            kontrol("%s: kurede 'Dis yuzey siniri'" % ad, "Dış yüzey" in k.yan_etiket.text())
    from cekirdek import geometri
    for ad, spec in _butun_specler():
        if geometri.agac_modu(spec):
            k = _kor(spec)
            kontrol("%s (agac): sablon gorunumu gizli, gelismis editor gorunur" % ad,
                    not k.sablon_gorunumu.isVisibleTo(k) and k.gelismis_gorunumu.isVisibleTo(k))
    uyg  # noqa: B018


def test_kor_sinir_ogeleri():
    print("\n[A6-3] KOR: sinir listeleri = uygunluk.sinir_secenekleri, Turkce + ozgun ad")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import uygunluk
    for ad, spec in _sablon_modu_specler():
        k = _kor(spec)
        for yuzey, kutu in (("yan", k.bc_yan), ("alt", k.bc_alt), ("ust", k.bc_ust)):
            beklenen = list(uygunluk.sinir_secenekleri(spec, yuzey))
            if not beklenen:
                continue
            kontrol("%s/%s: ogeler = %s" % (ad, yuzey, beklenen),
                    _oge_verileri(kutu) == beklenen, "-> %s" % _oge_verileri(kutu))
    k = _kor(_ornek("pwr_17x17"))
    metinler = [k.bc_yan.itemText(i) for i in range(k.bc_yan.count())]
    kontrol("oge metinleri Turkce + parantezde ozgun ad",
            "Yansıtıcı (reflective)" in metinler and "Vakum (vacuum)" in metinler
            and "Periyodik (periodic)" in metinler, "-> %s" % metinler)
    # Elle yazilmis gecersiz deger: silinmez, gecersizligi gorunur
    g = _ornek("godiva_kriter")
    g["kor"]["sinir"]["yan"] = "periodic"
    g0 = copy.deepcopy(g)
    k = _kor(g)
    kontrol("kurede periodic sunulmuyor ama dosyadaki deger gosteriliyor",
            k.bc_yan.currentData() == "periodic" and "geçersiz" in k.bc_yan.currentText())
    k._kaydet()
    kontrol("gecersiz sinir degeri kayitta silinmedi", g == g0)
    # pwr_17x17 (2B): alt/ust sinir gizli ama dosyadaki degerleri korunur
    s = _ornek("pwr_17x17")
    s["kor"]["sinir"]["alt"] = "white"
    k = _kor(s)
    k.bc_yan.setCurrentIndex(k.bc_yan.findData("vacuum"))
    kontrol("yan sinir yazildi", s["kor"]["sinir"]["yan"] == "vacuum")
    kontrol("2B'de gizli alt sinir degeri korundu", s["kor"]["sinir"]["alt"] == "white")
    uyg  # noqa: B018


def test_kor_yukseklik_secimi():
    print("\n[A6-4] KOR: yukseklik tek secim (2B / 3B tek bolge / 3B katmanli)")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import sema, uygunluk
    s = _ornek("pwr_17x17")
    k = _kor(s)
    kontrol("secenekler 2B / 3B / katmanli",
            _oge_verileri(k.yukseklik_modu) == ["2B", "3B", "katmanli"])
    kontrol("2B dosya '2B (sonsuz yukseklik)' gosteriyor",
            k.yukseklik_modu.currentData() == "2B"
            and "sonsuz" in k.yukseklik_modu.currentText())
    kontrol("2B: yukseklik alani ve alt/ust sinir gizli",
            not k._eksen_form.isRowVisible(k.yukseklik)
            and not k._eksen_form.isRowVisible(k.bc_alt))
    k.yukseklik_modu.setCurrentIndex(k.yukseklik_modu.findData("3B"))
    kontrol("3B tek bolge: yukseklik = H (366 cm), katman kapali",
            s["kor"]["yukseklik"] == 366.0 and not (s["kor"].get("eksenel") or {}).get("var"),
            "-> %r" % s["kor"]["yukseklik"])
    kontrol("3B: yukseklik alani ve alt/ust sinir gorunur",
            k._eksen_form.isRowVisible(k.yukseklik) and k._eksen_form.isRowVisible(k.bc_alt)
            and _oge_verileri(k.bc_alt) == uygunluk.sinir_secenekleri(s, "alt"))
    kontrol("uygunluk: model 3B", uygunluk.model_ozeti(s)["boyut"] == "3B")
    k.yukseklik.setValue(200.0)
    kontrol("yukseklik alani yaziliyor", s["kor"]["yukseklik"] == 200.0)
    k.yukseklik_modu.setCurrentIndex(k.yukseklik_modu.findData("katmanli"))
    b = (s["kor"].get("eksenel") or {}).get("bolgeler") or []
    kontrol("katmanli: tek 'aktif' katman, yukseklik katman toplami (200 cm)",
            s["kor"]["eksenel"]["var"] and len(b) == 1 and b[0]["yukseklik"] == 200.0
            and s["kor"]["yukseklik"] is None and sema.kor_yuksekligi(s["kor"]) == 200.0,
            "-> %s" % b)
    kontrol("katmanli: katman tablosu gorunur, yukseklik alani gizli",
            k.katman_kutu.isVisibleTo(k) and not k._eksen_form.isRowVisible(k.yukseklik))
    k.katman_tablo.cellWidget(0, 1).setValue(250.0)
    k.yukseklik_modu.setCurrentIndex(k.yukseklik_modu.findData("3B"))
    kontrol("katmanli -> 3B: yukseklik = katman toplami (250 cm)",
            s["kor"]["yukseklik"] == 250.0 and not s["kor"]["eksenel"]["var"],
            "-> %r" % s["kor"]["yukseklik"])
    kontrol("katmanli -> 3B: katmanlar SILINMEDI (gizli)",
            len(s["kor"]["eksenel"]["bolgeler"]) == 1 and not k.katman_kutu.isVisibleTo(k))
    k.yukseklik_modu.setCurrentIndex(k.yukseklik_modu.findData("2B"))
    kontrol("2B: yukseklik None, model 2B",
            s["kor"]["yukseklik"] is None and sema.kor_yuksekligi(s["kor"]) is None)
    # dosyadan: pwr_3b -> 3B, pwr_eksenel -> katmanli; kurede secim yok
    for ad, mod in (("pwr_3b", "3B"), ("pwr_eksenel", "katmanli"), ("tamburlu_kor", "3B")):
        kk = _kor(_ornek(ad))
        kontrol("%s aciliyor: '%s'" % (ad, mod), kk.yukseklik_modu.currentData() == mod)
    kk = _kor(_ornek("godiva_kriter"))
    kontrol("kure: yukseklik secimi gizli",
            not kk._eksen_form.isRowVisible(kk.yukseklik_modu)
            and not kk.katman_kutu.isVisibleTo(kk))
    uyg  # noqa: B018


def test_kor_katman_sirasi():
    print("\n[A6-5] KOR: katman tablosu fiziksel sirada, 'Yukari tasi' gercekten yukari")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import sema
    s = _ornek("pwr_eksenel")
    k = _kor(s)
    adlar = lambda: [b["ad"] for b in s["kor"]["eksenel"]["bolgeler"]]
    tablo = lambda: [k.katman_tablo.cellWidget(r, 0).text()
                     for r in range(k.katman_tablo.rowCount())]
    ilk = adlar()
    kontrol("tablo = spec tersi (en ust katman ilk satirda)",
            tablo() == list(reversed(ilk)), "-> %s" % tablo())
    kontrol("ilk satir 'ust yansitici', son satir 'alt yansitici'",
            tablo()[0] == "üst yansıtıcı" and tablo()[-1] == "alt yansıtıcı")

    def z_araligi(ad):
        for z0, z1, b in sema.eksenel_katmanlar(s["kor"]):
            if b["ad"] == ad:
                return z0, z1
    h0 = sema.kor_yuksekligi(s["kor"])
    z0 = z_araligi("aktif yakıt")
    k.katman_tablo.setCurrentCell(tablo().index("aktif yakıt"), 0)
    k.d_kat_yukari.click()
    z1 = z_araligi("aktif yakıt")
    kontrol("'Yukari tasi': aktif yakit fiziksel olarak YUKARI (z arttı)",
            z1[0] > z0[0], "-> %s -> %s" % (z0, z1))
    kontrol("yukari: spec'te bir sonraki katmanla yer degisti",
            adlar() == ["alt yansıtıcı", "alt örtü", "üst örtü", "aktif yakıt",
                        "plenum", "üst yansıtıcı"], "-> %s" % adlar())
    kontrol("yukari: secim tasinan katmanda kaldi",
            tablo()[k.katman_tablo.currentRow()] == "aktif yakıt")
    kontrol("yukari: toplam yukseklik degismedi", sema.kor_yuksekligi(s["kor"]) == h0)
    k.d_kat_asagi.click()
    kontrol("'Asagi tasi' geri getirdi", adlar() == ilk, "-> %s" % adlar())
    k.katman_tablo.setCurrentCell(0, 0)
    k.d_kat_yukari.click()
    kontrol("en ustteki katman daha yukari cikmaz", adlar() == ilk)
    k.katman_tablo.setCurrentCell(k.katman_tablo.rowCount() - 1, 0)
    k.d_kat_asagi.click()
    kontrol("en alttaki katman daha asagi inmez", adlar() == ilk)
    k.d_kat_ekle.click()
    kontrol("+ Katman en uste ekler (spec sonu, tablo ilk satir)",
            len(adlar()) == 7 and adlar()[:6] == ilk and tablo()[0] == adlar()[-1]
            and k.katman_tablo.currentRow() == 0)
    k.d_kat_sil.click()
    kontrol("Sil secili (yeni) katmani siler", adlar() == ilk, "-> %s" % adlar())
    k.katman_tablo.cellWidget(tablo().index("plenum"), 1).setValue(30.0)
    kontrol("tablodan yukseklik dogru katmana yaziliyor",
            [b["yukseklik"] for b in s["kor"]["eksenel"]["bolgeler"] if b["ad"] == "plenum"]
            == [30.0])

    # Dolgu listeleri sema.katman_adaylari ile tutarli
    kor = s["kor"]
    kutu = k.katman_tablo.cellWidget(tablo().index("aktif yakıt"), 2)
    veri = _oge_verileri(kutu)
    ana = sema.katman_adaylari(kor, {})
    kontrol("'ana dolgu' ogesi katman_adaylari'ni adlandiriyor (%s)" % ana,
            veri[0] is None and all(a in kutu.itemText(0) for a in ana))
    kontrol("tek demette katman dolgusu: demetler + malzemeler (cubuk yok)",
            set(veri) == ({None, sema.BOSLUK} | {d["ad"] for d in s["demetler"]}
                          | {m["ad"] for m in s["malzemeler"]}),
            "-> %s" % veri)
    for r in range(k.katman_tablo.rowCount()):
        i = len(kor["eksenel"]["bolgeler"]) - 1 - r
        b = kor["eksenel"]["bolgeler"][i]
        kontrol("satir %d dolgusu = spec (%s)" % (r + 1, b.get("dolgu")),
                k.katman_tablo.cellWidget(r, 2).currentData() == b.get("dolgu"))
    # tam korda ana dolgu haritanin kendisidir: ayri katmana yalnizca malzeme
    t = dict(_sablonlar())["sablon:tam_kor"]
    kt = _kor(t)
    kt.yukseklik_modu.setCurrentIndex(kt.yukseklik_modu.findData("katmanli"))
    veri = _oge_verileri(kt.katman_tablo.cellWidget(0, 2))
    kontrol("tam kor katmani: ana dolgu (kor haritasi) + malzemeler",
            veri[0] is None and "kor haritası" in kt.katman_tablo.cellWidget(0, 2).itemText(0)
            and not (set(veri) & {d["ad"] for d in t["demetler"]}), "-> %s" % veri)
    uyg  # noqa: B018


def test_kor_harita_boyama():
    print("\n[A6-6] KOR: kor haritasi palet + izgara ile boyaniyor, boyut haritadan")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    from cekirdek import dogrula, kurucu, sema
    from arayuz import izgara
    t = dict(_sablonlar())["sablon:tam_kor"]
    t0 = copy.deepcopy(t)
    k = _kor(t)
    kontrol("duz metin harita ve harf tablosu yok",
            not k.findChildren(QtWidgets.QPlainTextEdit) and not hasattr(k, "anahtar_tablo"))
    kontrol("izgara 3x3, boyut kutulari haritadan (3, 3)",
            k.izgara.boyut() == (3, 3) and (k.nx.value(), k.ny.value()) == (3, 3))
    palet = k.palet.adlar()
    kontrol("palet: kafes + malzemeler + bosluk",
            "demet_17x17" in palet and "su" in palet and sema.BOSLUK in palet
            and "yakit_cubugu" not in palet, "-> %s" % palet)
    kontrol("yukleme spec'i degistirmedi", t == t0)

    k.palet.sec("su")
    k.izgara.hucreyi_boya((0, 0), "su")
    k.izgara.degisti.emit()
    adlar = izgara.harita_adlara(t["kor"]["harita"], t["kor"]["anahtar"])
    kontrol("boyanan hucre spec'te 'su'", adlar[0][0] == "su" and adlar[1][1] == "demet_17x17")
    kontrol("eski harf korundu ('d' -> demet_17x17)",
            t["kor"]["anahtar"].get("d") == "demet_17x17" and t["kor"]["harita"][2] == "ddd")
    kontrol("boyut [3, 3] yazildi", t["kor"]["boyut"] == [3, 3])

    sorular = []
    k._onay_al = lambda b, m: (sorular.append(b), False)[1]
    k.palet.sec("demet_17x17")
    k.nx.setValue(4)
    kontrol("buyutme onay sormadi", not sorular)
    kontrol("buyutme: harita 4 sutun, yeni sutun secili parcayla",
            t["kor"]["boyut"] == [4, 3] and all(len(r) == 4 for r in t["kor"]["harita"])
            and all(r[3] == "d" for r in t["kor"]["harita"]), "-> %s" % t["kor"]["harita"])
    once = copy.deepcopy(t["kor"])
    k.nx.setValue(3)
    kontrol("dolu hucre silen kucultme onay sordu", len(sorular) == 1)
    kontrol("reddedilince harita ve boyut ayni, kutu geri dondu",
            t["kor"] == once and k.nx.value() == 4)
    k._onay_al = lambda b, m: (sorular.append(b), True)[1]
    k.nx.setValue(3)
    kontrol("onaylaninca 3 sutuna kuculdu", t["kor"]["boyut"] == [3, 3]
            and all(len(r) == 3 for r in t["kor"]["harita"]))
    # tanimsiz (bos) hucreleri silen kucultme sormaz
    sorular.clear()
    k.izgara.yukle([["demet_17x17", None], ["demet_17x17", None]], k.palet.renkler())
    k._harita_boyandi()
    k._harita_doldur()
    k.nx.setValue(1)
    kontrol("yalnizca tanimsiz hucre silen kucultme onay sormadi", not sorular)
    k.palet.sec("demet_17x17")
    k.nx.setValue(3)
    k.ny.setValue(3)
    k._tumunu_doldur()
    kontrol("'Tumunu doldur' butun haritayi secili parcayla doldurdu",
            t["kor"]["harita"] == ["ddd"] * 3)
    bul = [b.mesaj for b in dogrula.tum_kontroller(t, veri_kontrolu=False) if b.seviye == "hata"]
    kontrol("boyanan harita gecerli (0 hata)", not bul, "-> %s" % bul[:3])
    try:
        kurucu.kur(t)
        kontrol("boyanan harita kuruluyor", True)
    except Exception as e:
        kontrol("boyanan harita kuruluyor", False, "-> %s" % e)

    # anahtarda olmayan harf: baska hucre boyaninca harfi korunur
    t2 = copy.deepcopy(t0)
    t2["kor"]["harita"] = ["dxd", "ddd", "ddd"]
    k2 = _kor(t2)
    k2.izgara.hucreyi_boya((2, 2), "su")
    k2.izgara.degisti.emit()
    kontrol("tanimsiz harf ('x') sessizce degistirilmedi", t2["kor"]["harita"][0] == "dxd")
    uyg  # noqa: B018


def test_kor_yalniz_tur_alanlari_yazilir(gecici=None):
    print("\n[A6-7] KOR: kayit yalnizca turun alanlarini yazar; yukleme spec'i degistirmez")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import dogrula, kurucu, sema, uygunluk
    for ad, spec in _sablon_modu_specler():
        s0 = copy.deepcopy(spec)
        k = _kor(spec)
        kontrol("%s: spec_yukle spec'i degistirmedi" % ad, spec == s0)
        k._kaydet()
        kontrol("%s: degisiklik yokken kayit spec'i degistirmedi" % ad, spec == s0,
                "-> %s" % [a for a in spec["kor"] if spec["kor"].get(a) != s0["kor"].get(a)])
        yeni = "vacuum" if k.bc_yan.currentData() != "vacuum" else "reflective"
        k.bc_yan.setCurrentIndex(k.bc_yan.findData(yeni))
        izinli = set(uygunluk.kor_alanlari(spec["kor"]["tur"])) | {"sinir"}
        degisen = {a for a in set(spec["kor"]) | set(s0["kor"])
                   if spec["kor"].get(a) != s0["kor"].get(a)}
        kontrol("%s: sinir degisikligi yalnizca 'sinir'i degistirdi" % ad,
                degisen <= izinli and "sinir" in degisen, "-> %s" % degisen)
        ozgu = [a for a in sema.KOR_TURE_OZGU if a not in izinli and a not in sema.KOR_KORUNAN]
        kontrol("%s: baska turlerin alanlari varsayilan" % ad,
                all(spec["kor"].get(a) == sema.VARSAYILAN_KOR[a] for a in ozgu))
    # butun ornekler: arayuzden kaydetmek modeli ve dogrulamayi degistirmez
    for ad in _ornek_adlari():
        s = _ornek(ad)
        olcu0 = kurucu.kur(s)[1]["sinir_kutu"]
        b0 = sorted((b.seviye, b.mesaj) for b in dogrula.tum_kontroller(s, veri_kontrolu=False))
        k = _kor(s)
        k._kaydet()
        olcu1 = kurucu.kur(s)[1]["sinir_kutu"]
        b1 = sorted((b.seviye, b.mesaj) for b in dogrula.tum_kontroller(s, veri_kontrolu=False))
        kontrol("%s: kayit olcuyu ve dogrulamayi degistirmedi" % ad,
                olcu0 == olcu1 and b0 == b1)
    uyg  # noqa: B018


def test_kor_tur_gecisi_ve_yansitici():
    print("\n[A6-8] KOR: tur gecisleri (model basligi yolu) + yansitici davranisi")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import kurucu
    s = _ornek("pwr_17x17")
    olcu0 = kurucu.kur(s)[1]["sinir_kutu"]
    k = _kor(s)
    hafiza = {}
    _tur_degistir(k, s, "tamburlu", hafiza)
    kontrol("tamburlu: 'Yansitici kusak ekle' gizli, kalinlik/malzeme gorunur",
            not k.yans_var.isVisibleTo(k) and k.yans_kal.isVisibleTo(k)
            and k.yans_mal.isVisibleTo(k))
    k.yans_kal.setValue(15.0)
    kontrol("tamburlu kayit yansitici.var'i degistirmedi", s["kor"]["yansitici"]["var"] is False)
    k.yans_kal.setValue(20.0)
    _tur_degistir(k, s, "tek_demet", hafiza)
    k._kaydet()
    kontrol("tamburlu gidis-donus: olcu ayni", kurucu.kur(s)[1]["sinir_kutu"] == olcu0)
    kontrol("tek_demet: yansitici kapali -> kalinlik/malzeme gizli",
            not k.yans_kal.isVisibleTo(k) and not k.yans_mal.isVisibleTo(k))
    s["kor"]["yansitici"]["malzeme"] = None
    k.spec_yukle(s)
    k.yans_var.setChecked(True)
    kontrol("yansitici acilinca malzeme bos kalmadi (moderator onerildi)",
            s["kor"]["yansitici"]["var"] and s["kor"]["yansitici"]["malzeme"] == "su",
            "-> %s" % s["kor"]["yansitici"])
    kontrol("yansitici + reflective yan sinir: uyari gorunur",
            k._eksen_form.isRowVisible(k.sinir_notu) and "Vakum" in k.sinir_notu.text())
    k.bc_yan.setCurrentIndex(k.bc_yan.findData("vacuum"))
    kontrol("vakum secilince uyari kalkti", not k._eksen_form.isRowVisible(k.sinir_notu))
    uyg  # noqa: B018


def test_numarali_sekme_atfi_yok():
    print("\n[A6-9] METIN: eski numarali sekme atiflari yok")
    desen = re.compile(r"[\"'][^\"'\n]*\b\d\.\s?(Malzeme|Par[cç]a|Demet|Kor|Ayar|Hesap|"
                       r"[CÇ]al[iı][sş]t[iı]r|Analiz|T[uü]kenme)")
    for dosya in ("arayuz/sekme_kor.py", "arayuz/sekme_ayar.py", "arayuz/onizleme.py"):
        with open(os.path.join(KOK, dosya), encoding="utf-8") as f:
            bulunan = desen.findall(f.read())
        kontrol("%s: numarali sekme atfi yok" % dosya, not bulunan, "-> %s" % bulunan)


# ============================================================================
# HESAP AYARLARI
# ============================================================================

# pwr_pinhucre / pwr_17x17 olcumleri (OpenMC 0.16, 4 is parcacigi):
# (ornek, parcacik, cevrim, pasif, tohum, sigma_pcm)
SIGMA_OLCUMU = [
    ("pwr_pinhucre", 1000, 60, 20, 1, 531.7), ("pwr_pinhucre", 1000, 60, 20, 2, 447.2),
    ("pwr_pinhucre", 1000, 60, 20, 3, 310.8),
    ("pwr_pinhucre", 10000, 150, 40, 1, 81.8), ("pwr_pinhucre", 10000, 150, 40, 2, 86.4),
    ("pwr_pinhucre", 10000, 150, 40, 3, 87.6),
    ("pwr_pinhucre", 50000, 300, 80, 1, 27.8), ("pwr_pinhucre", 50000, 300, 80, 2, 27.7),
    ("pwr_17x17", 1000, 60, 20, 1, 488.9), ("pwr_17x17", 1000, 60, 20, 2, 447.4),
    ("pwr_17x17", 10000, 150, 40, 1, 74.9), ("pwr_17x17", 10000, 150, 40, 2, 88.9),
    ("pwr_17x17", 50000, 300, 80, 1, 27.7), ("pwr_3b", 10000, 150, 40, 1, 81.5),
]


def test_ayar_hassasiyet():
    print("\n[A6-10] AYAR: hesap hassasiyeti onayarlari")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz import sekme_ayar as sa
    kontrol("onayarlar: Hizli deneme / Normal / Hassas / Ozel",
            [a[1] for a in sa.HASSASIYET] == ["Hızlı deneme", "Normal", "Hassas"])
    s = _ornek("pwr_pinhucre")          # 5000 x 60 / 10 -- onayar degil
    s0 = copy.deepcopy(s)
    a = _ayar(s)
    kontrol("onayar olmayan dosya 'Ozel' gosteriyor, spec degismedi",
            a.hassasiyet.currentData() == sa.OZEL and s == s0)
    kontrol("Ozel'de de belirsizlik tahmini yaziyor",
            "±" in a.hassasiyet_ozet.text() and "pcm" in a.hassasiyet_ozet.text())
    beklenen = {"hizli": (1000, 60, 20), "normal": (10000, 150, 40), "hassas": (50000, 300, 80)}
    for anahtar, (n, c, p) in beklenen.items():
        a.hassasiyet.setCurrentIndex(a.hassasiyet.findData(anahtar))
        ay = s["ayarlar"]
        kontrol("'%s' secildi -> %d x %d (%d pasif)" % (anahtar, n, c, p),
                (ay["parcacik"], ay["cevrim"], ay["pasif"]) == (n, c, p),
                "-> %s" % ((ay["parcacik"], ay["cevrim"], ay["pasif"]),))
    a.parcacik.setValue(12345)
    kontrol("elle degisiklik -> 'Ozel'", a.hassasiyet.currentData() == sa.OZEL
            and s["ayarlar"]["parcacik"] == 12345)
    a.parcacik.setValue(50000)
    kontrol("onayar degerlerine donunce onayar gorunur", a.hassasiyet.currentData() == "hassas")
    a.hassasiyet.setCurrentIndex(a.hassasiyet.findData(sa.OZEL))
    kontrol("'Ozel' secmek degerleri degistirmez ve Ozel kalir",
            a.hassasiyet.currentData() == sa.OZEL and s["ayarlar"]["parcacik"] == 50000)
    an = _ayar(_ornek("pwr_17x17"))
    kontrol("Normal onayarli dosya 'Normal' gosteriyor", an.hassasiyet.currentData() == "normal")
    # sabit kaynak: pasif gizli, onayar ona dokunmaz
    z = _ornek("zirh_kure")
    z["ayarlar"]["pasif"] = 7
    az = _ayar(z)
    az.hassasiyet.setCurrentIndex(az.hassasiyet.findData("normal"))
    kontrol("sabit kaynakta onayar pasif cevrime dokunmuyor (7)",
            z["ayarlar"]["pasif"] == 7 and z["ayarlar"]["parcacik"] == 10000
            and z["ayarlar"]["cevrim"] == 150)
    kontrol("sabit kaynakta pcm degil parcacik sayisi yaziyor",
            "pcm" not in az.hassasiyet_ozet.text() and "1 500 000" in az.hassasiyet_ozet.text(),
            "-> %s" % az.hassasiyet_ozet.text())
    # belirsizlik tahmini olcumle tutarli
    for ornek, n, c, p, tohum, olcum in SIGMA_OLCUMU:
        tahmin = sa.belirsizlik_pcm(n, c, p)
        tolerans = 0.45 if c - p < 100 else 0.15      # 40 aktif cevrimde sigma'nin kendisi oynak
        kontrol("%s %dx%d/%d t%d: tahmin %.0f pcm ~ olcum %.1f pcm"
                % (ornek, n, c, p, tohum, tahmin, olcum),
                abs(tahmin - olcum) / olcum < tolerans)
    kontrol("aktif cevrim yoksa tahmin yok", sa.belirsizlik_pcm(1000, 20, 20) is None)
    uyg  # noqa: B018


def test_ayar_moda_gore_gizleme():
    print("\n[A6-11] AYAR: gorunen alanlar = uygunluk.ayar_alanlari / kaynak_secenekleri")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import uygunluk
    for ad, spec in _butun_specler():
        a = _ayar(spec)
        alan = uygunluk.ayar_alanlari(spec)
        secenek = uygunluk.kaynak_secenekleri(spec)
        gorunen = {
            "pasif": a._hesap_form.isRowVisible(a.pasif),
            "entropi": a._gelismis_form.isRowVisible(a.entropi_var),
            "kinetik": a._hesap_form.isRowVisible(a.kinetik_var),
            "kaynak_siddeti": a._kaynak_form.isRowVisible(a.kaynak_kuvvet),
            "kaynak_tayfi_temel": a._tayf_yeri is a._kaynak_tayf_yeri,
            "guc_dagilimi": a.guc_kutu.isVisibleTo(a),
        }
        yanlis = {k: (alan[k], v) for k, v in gorunen.items() if alan[k] != v}
        kontrol("%s: gorunen alanlar = ayar_alanlari" % ad, not yanlis,
                "-> (beklenen, gorunen) %s" % yanlis)
        kontrol("%s: kaynak tipi ogeleri = %s" % (ad, secenek["turler"]),
                _oge_verileri(a.kaynak_tur) == secenek["turler"])
        kontrol("%s: parcacik ogeleri = %s" % (ad, secenek["parcaciklar"]),
                _oge_verileri(a.kaynak_parcacik) == secenek["parcaciklar"])
        kontrol("%s: parcacik satiri yalnizca secenek varsa" % ad,
                a._kaynak_form.isRowVisible(a.kaynak_parcacik)
                == (len(secenek["parcaciklar"]) > 1))
    # ozdeger -> sabit kaynak -> ozdeger: gizlenen degerler SILINMEZ
    s = _ornek("pwr_pinhucre")
    s["ayarlar"]["entropi_mesh"] = {"var": True, "boyut": [5, 6, 1]}
    s["ayarlar"]["kinetik"] = {"var": True, "nesil": 7}
    a = _ayar(s)
    a.mod.setCurrentIndex(a.mod.findData("fixed source"))
    ay = s["ayarlar"]
    kontrol("sabit kaynak: pasif, entropi, kinetik gizli",
            not a._hesap_form.isRowVisible(a.pasif)
            and not a._gelismis_form.isRowVisible(a.entropi_var)
            and not a._hesap_form.isRowVisible(a.kinetik_var))
    kontrol("sabit kaynak: siddet gorunur, foton sunuluyor, tayf ana bolumde",
            a._kaynak_form.isRowVisible(a.kaynak_kuvvet)
            and "photon" in _oge_verileri(a.kaynak_parcacik)
            and a._tayf_yeri is a._kaynak_tayf_yeri)
    kontrol("baslik 'Kaynak'", a.kaynak_baslik.text() == "Kaynak")
    a.parcacik.setValue(6000)
    kontrol("gizlenen pasif/entropi/kinetik degerleri spec'te duruyor",
            ay["pasif"] == 10 and ay["entropi_mesh"] == {"var": True, "boyut": [5, 6, 1]}
            and ay["kinetik"] == {"var": True, "nesil": 7}, "-> %s %s %s"
            % (ay["pasif"], ay["entropi_mesh"], ay["kinetik"]))
    a.kaynak_kuvvet.setText("5e9")
    a.kaynak_kuvvet.editingFinished.emit()
    a.mod.setCurrentIndex(a.mod.findData("eigenvalue"))
    kontrol("ozdeger: siddet ve foton gizli, tayf Gelismis'te",
            not a._kaynak_form.isRowVisible(a.kaynak_kuvvet)
            and _oge_verileri(a.kaynak_parcacik) == ["neutron"]
            and a._tayf_yeri is a._gelismis_tayf_yeri
            and a.gelismis.isAncestorOf(a.tayf_kutu))
    a.parcacik.setValue(7000)
    kontrol("ozdegerde gizlenen siddet (5e9) spec'te duruyor",
            ay["kaynak"]["kuvvet"] == 5e9, "-> %r" % ay["kaynak"]["kuvvet"])
    kontrol("ozdegere donunce eski degerler geri gorunur",
            a.pasif.value() == 10 and a.entropi_nx.value() == 5 and a.kinetik_var.isChecked()
            and a.kinetik_nesil.value() == 7)
    # 2B'de nokta kaynagin z'si gizli ve korunur; kurede z gorunur
    s2 = _ornek("pwr_pinhucre")
    s2["ayarlar"]["kaynak"]["konum"] = [0.0, 0.0, 4.5]
    a2 = _ayar(s2)
    a2.kx.setValue(0.1)
    kontrol("2B: z konumu gizli, degeri korundu",
            not a2.kz.isVisibleTo(a2) and s2["ayarlar"]["kaynak"]["konum"] == [0.1, 0.0, 4.5])
    az = _ayar(_ornek("zirh_kure"))
    kontrol("kure (sabit kaynak): nokta z gorunur", az.kz.isVisibleTo(az))
    # ozdegerde gecersiz foton kaynagi: gosterilir, sessizce notrona donmez
    s3 = _ornek("pwr_pinhucre")
    s3["ayarlar"]["kaynak"]["parcacik"] = "photon"
    a3 = _ayar(s3)
    kontrol("ozdeger + foton (dosyadan): satir gorunur, 'gecersiz' isaretli",
            a3._kaynak_form.isRowVisible(a3.kaynak_parcacik)
            and a3.kaynak_parcacik.currentData() == "photon"
            and "geçersiz" in a3.kaynak_parcacik.currentText())
    a3.parcacik.setValue(5001)
    kontrol("kayit gecersiz foton degerini sessizce degistirmedi",
            s3["ayarlar"]["kaynak"]["parcacik"] == "photon")
    uyg  # noqa: B018


def test_ayar_calistirma_dokunulmaz():
    print("\n[A6-12] AYAR: is parcacigi ve kosu dizini bu sekmede yok, dokunulmaz")
    uyg = _qt()
    if uyg is None:
        return
    s = _ornek("pwr_17x17")
    s["calistirma"] = {"is_parcacigi": 3, "dizin": "ozel_kosu"}
    a = _ayar(s)
    kontrol("is parcacigi / kosu dizini alanlari yok",
            not hasattr(a, "is_parcacigi") and not hasattr(a, "kosu_dizini"))
    a.parcacik.setValue(2222)
    a.hassasiyet.setCurrentIndex(a.hassasiyet.findData("hizli"))
    a.mod.setCurrentIndex(a.mod.findData("fixed source"))
    a.mod.setCurrentIndex(a.mod.findData("eigenvalue"))
    a.tohum.setValue(99)
    a._tally_ekle()
    a._kaydet()
    kontrol("calistirma ayarlari degismedi",
            s["calistirma"] == {"is_parcacigi": 3, "dizin": "ozel_kosu"}, "-> %s" % s["calistirma"])
    uyg  # noqa: B018


def test_ayar_gelismis_ve_entropi():
    print("\n[A6-13] AYAR: Gelismis bolumu; entropi agi otomatik")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import kaynak
    s = _ornek("pwr_17x17")
    s0 = copy.deepcopy(s)
    a = _ayar(s)
    for ad in ("tohum", "sicaklik_yontemi", "entropi_var", "entropi_nx", "kinetik_nesil",
               "tayf", "aci_tur"):
        kontrol("'%s' Gelismis icinde" % ad, a.gelismis.isAncestorOf(getattr(a, ad)))
    for ad in ("mod", "hassasiyet", "parcacik", "kinetik_var", "kaynak_tur"):
        kontrol("'%s' ana bolumde" % ad, not a.gelismis.isAncestorOf(getattr(a, ad)))
    kontrol("sicaklik yontemi Turkce + ozgun ad",
            [a.sicaklik_yontemi.itemText(i) for i in range(2)]
            == ["Ara değer (interpolation)", "En yakın sıcaklık (nearest)"]
            and _oge_verileri(a.sicaklik_yontemi) == ["interpolation", "nearest"])
    kontrol("[8,8,1] 2B dosya: 'otomatik' gorunur, spec degismedi",
            a.entropi_oto.isChecked() and s == s0)
    # Gelismis kapaliyken icindeki her sey "gorunmez"; gizleme bayragina bakilir.
    kontrol("otomatikte bolme kutulari kapali, 2B'de nz gizli",
            not a.entropi_nx.isEnabled() and a.entropi_nz.isHidden())
    t = _ornek("tamburlu_kor")
    at = _ayar(t)
    kontrol("[6,6,6] dosya: 'Ozel' (otomatik degil), degerler gorunur",
            not at.entropi_oto.isChecked() and at.entropi_nx.value() == 6
            and not at.entropi_nz.isHidden() and at.entropi_nx.isEnabled())
    at.entropi_oto.setChecked(True)
    kontrol("otomatik secildi: 3B -> [8,8,8], otomatik isaretli",
            t["ayarlar"]["entropi_mesh"]["boyut"] == [8, 8, 8]
            and t["ayarlar"]["entropi_mesh"].get("otomatik") is True
            and kaynak.entropi_boyutu(t) == [8, 8, 8])
    at.entropi_oto.setChecked(False)
    at.entropi_nx.setValue(5)
    kontrol("otomatik kapatildi: elle deger yazildi",
            t["ayarlar"]["entropi_mesh"]["boyut"] == [5, 8, 8]
            and t["ayarlar"]["entropi_mesh"]["otomatik"] is False)
    # otomatik kural: 2B [8,8,1], 3B [8,8,8]
    p = _ornek("pwr_17x17")
    kontrol("kural 2B -> [8,8,1]", kaynak.entropi_boyutu_otomatik(p) == [8, 8, 1])
    p["kor"]["yukseklik"] = 100.0
    kontrol("kural 3B -> [8,8,8]", kaynak.entropi_boyutu_otomatik(p) == [8, 8, 8])
    p["ayarlar"]["entropi_mesh"]["otomatik"] = True
    kontrol("entropi_boyutu 'otomatik'te modelden", kaynak.entropi_boyutu(p) == [8, 8, 8])
    p["ayarlar"]["entropi_mesh"]["otomatik"] = False
    kontrol("entropi_boyutu otomatik degilken dosyadan",
            kaynak.entropi_boyutu(p) == p["ayarlar"]["entropi_mesh"]["boyut"])
    uyg  # noqa: B018


def test_ayar_guc_dagilimi():
    print("\n[A6-14] AYAR: guc dagilimi yalnizca uygun modelde, yalnizca fisil cubuklar")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import uygunluk
    s = _ornek("pwr_17x17")
    a = _ayar(s)
    kontrol("pwr_17x17: guc bolumu gorunur", a.guc_kutu.isVisibleTo(a))
    a.guc_var.setChecked(True)
    kontrol("hedef cubuk ogeleri = guc_cubuklari (kilavuz boru yok)",
            _oge_verileri(a.guc_cubuk) == uygunluk.guc_cubuklari(s) == ["yakit_cubugu"],
            "-> %s" % _oge_verileri(a.guc_cubuk))
    kontrol("2B: eksenel dilim gizli", not a._guc_form.isRowVisible(a.guc_dilim))
    kontrol("bolge numaralari 1'den", a.guc_bolge.itemText(0).startswith("1. bölge"))
    from cekirdek import sema as _sema
    kontrol("guc acildi, YENI bicimde yazildi (cubuklar; eski tek alan yok)",
            s["guc_dagilimi"]["var"]
            and _sema.guc_hedefleri(s["guc_dagilimi"]) == [{"cubuk": "yakit_cubugu",
                                                            "bolge": 0}]
            and "cubuk" not in s["guc_dagilimi"] and "bolge" not in s["guc_dagilimi"],
            "-> %r" % s["guc_dagilimi"])
    a3 = _ayar(_ornek("pwr_3b"))
    kontrol("3B: eksenel dilim gorunur", a3._guc_form.isRowVisible(a3.guc_dilim))
    p = _ornek("pwr_pinhucre")
    ap = _ayar(p)
    kontrol("pin hucre: guc bolumu gizli", not ap.guc_kutu.isVisibleTo(ap))
    p["guc_dagilimi"]["var"] = True
    ap = _ayar(p)
    kontrol("pin hucre + dosyada acik guc: bolum gorunur ve uyarir (kapatilabilsin)",
            ap.guc_kutu.isVisibleTo(ap) and "hesaplanamaz" in ap.guc_uyari.text())
    ap.guc_var.setChecked(False)
    kontrol("kapatildi", p["guc_dagilimi"]["var"] is False)
    # guc kapaliyken alanlar yazilmaz (gizli deger korunur)
    s2 = _ornek("pwr_17x17")
    s2["guc_dagilimi"]["toplam_guc"] = 12345.0
    a2 = _ayar(s2)
    a2.parcacik.setValue(9999)
    kontrol("guc kapaliyken gizli toplam guc korundu",
            s2["guc_dagilimi"]["toplam_guc"] == 12345.0)
    uyg  # noqa: B018


def test_ayar_tally_setleri():
    print("\n[A6-15] AYAR: tally skor setleri ve filtre alanlari")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz import sekme_ayar as sa
    s = _ornek("pwr_17x17")
    a = _ayar(s)
    kontrol("setler: Aki / Reaksiyon hizlari / Isi-guc / Ozel",
            _oge_verileri(a.t_set) == ["aki", "reaksiyon", "isi", sa.OZEL])
    a.tally_liste.setCurrentRow(0)
    kontrol("'reaksiyonlar' tally -> 'Reaksiyon hizlari'", a.t_set.currentData() == "reaksiyon")
    kontrol("hazir sette skor listesi gizli", not a._t_form.isRowVisible(a.t_skor))
    kontrol("filtre secili degil: enerji/mesh alanlari gizli",
            not a._t_form.isRowVisible(a.t_enerji) and not a._t_form.isRowVisible(a.mesh_satiri))
    t = s["tallyler"][0]
    a.t_set.setCurrentIndex(a.t_set.findData("isi"))
    kontrol("'Isi / guc' -> kappa-fission + heating",
            t["skorlar"] == ["kappa-fission", "heating"], "-> %s" % t["skorlar"])
    a.t_set.setCurrentIndex(a.t_set.findData(sa.OZEL))
    kontrol("'Ozel': liste gorunur, skorlar degismedi",
            a._t_form.isRowVisible(a.t_skor) and t["skorlar"] == ["kappa-fission", "heating"]
            and a.t_set.currentData() == sa.OZEL)
    kontrol("skor adlari Turkce + ozgun ad",
            a.t_skor.item(0).text() == "Akı (flux)"
            and a.t_skor.item(0).data(0x0100) == "flux")
    a.t_enerji_var.setChecked(True)
    kontrol("enerji filtresi acilinca alan gorunur ve filtre yazildi",
            a._t_form.isRowVisible(a.t_enerji)
            and [f["tur"] for f in t["filtreler"]] == ["enerji"])
    a.tally_liste.setCurrentRow(1)
    kontrol("'iki_grup_aki' -> 'Aki', enerji alani gorunur",
            a.t_set.currentData() == "aki" and a._t_form.isRowVisible(a.t_enerji))
    # bilinmeyen skor korunur
    s2 = _ornek("pwr_17x17")
    s2["tallyler"][0]["skorlar"] = ["flux", "fission-q-recoverable"]
    a2 = _ayar(s2)
    a2.tally_liste.setCurrentRow(0)
    a2.t_ad.editingFinished.emit()
    kontrol("listede olmayan skor (fission-q-recoverable) silinmedi",
            s2["tallyler"][0]["skorlar"] == ["flux", "fission-q-recoverable"],
            "-> %s" % s2["tallyler"][0]["skorlar"])
    kontrol("bilinmeyen skorlu tally 'Ozel' gosteriyor", a2.t_set.currentData() == sa.OZEL)
    # zirh_kure: malzeme filtresi korunur ve belirtilir
    z = _ornek("zirh_kure")
    az = _ayar(z)
    az.tally_liste.setCurrentRow(0)
    kontrol("yonetilmeyen filtre (malzeme) not olarak gorunur",
            "malzeme" in az.t_diger.text() and az._t_form.isRowVisible(az.t_diger))
    # tally yokken bos durum
    b = _ornek("pwr_17x17")
    b["tallyler"] = []
    ab = _ayar(b)
    kontrol("tally yokken ipucu gorunur, duzenleyici gizli",
            ab.tally_bos.isVisibleTo(ab) and not ab.tally_duzenleyici.isVisibleTo(ab))
    ab._tally_ekle()
    kontrol("+ Tally: 'Aki' setiyle yeni tally",
            b["tallyler"][-1]["skorlar"] == ["flux"] and ab.t_set.currentData() == "aki")
    uyg  # noqa: B018


def test_ayar_yukleme_kayit_kimligi():
    print("\n[A6-16] AYAR: yukleme ve degisikliksiz kayit spec'i degistirmez")
    uyg = _qt()
    if uyg is None:
        return
    for ad, spec in _butun_specler():
        s0 = copy.deepcopy(spec)
        a = _ayar(spec)
        kontrol("%s: spec_yukle degistirmedi" % ad, spec == s0)
        a._kaydet()
        kontrol("%s: degisikliksiz kayit degistirmedi" % ad, spec == s0)
    uyg  # noqa: B018


def test_enerji_girdisi_degistirilmeden_tam_geri_verir():
    print("\n[A6-16b] AYAR: EnerjiGirdi ayarla -> deger float yuvarlamasiyla kaymaz")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.ortak import EnerjiGirdi
    g = EnerjiGirdi()
    for ev in (1.025e6, 14.1e6, 0.0253, 2.5e3, 1.0e6, 3.3e-2):
        g.ayarla(ev)
        kontrol("ayarla(%r) -> deger ayni" % ev, g.deger() == ev, "-> %r" % g.deger())
    g.ayarla(1.025e6)
    g.kutu.setValue(2.0)
    kontrol("kullanici degistirince yeni deger okunur",
            g.deger() == 2.0 * 1.0e6, "-> %r" % g.deger())
    uyg  # noqa: B018


# ============================================================================
# ONIZLEME
# ============================================================================

def test_onizleme_ikili_kesit(gecici=None):
    print("\n[A6-17] ONIZLEME: 3B'de xy + xz yan yana, 2B'de tek; API ve korumalar")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.onizleme import OnizlemeWidget, IKILI
    w = OnizlemeWidget()
    for ad in ("durum", "olcu_bulundu", "arac_cubugu", "_ciz", "spec_ayarla", "iste",
               "cizildi_mi", "son_olcu", "kaydet", "kapat", "bekle", "mesgul_mu"):
        kontrol("API: %s" % ad, hasattr(w, ad))
    kontrol("cozunurluk ve cakisma secenegi Gelismis altinda",
            w.gelismis.isAncestorOf(w.cozunurluk) and w.gelismis.isAncestorOf(w.cakisma))
    kontrol("renk ogeleri Turkce", [w.renklendirme.itemText(i) for i in range(2)]
            == ["Malzeme", "Hücre"])

    # v3 H2: kesitler cizim iscisine istek olarak gider; giden kesitler kaydedilir.
    gorulen = []
    asil = w._istemci.iste

    def izleyen(istek):
        gorulen.append([k["eksen"] for k in istek.get("kesitler", [])])
        return asil(istek)

    w._istemci.iste = izleyen
    try:
        s3 = _ornek("pwr_3b")                       # 3B + guc dagilimi (CellFilter)
        w.spec_ayarla(s3)
        w._ciz()
        w.bekle(120)
        kontrol("pwr_3b: gorunum xy + xz, iki eksen cizildi",
                w.gorunum() == ["xy", "xz"] and len(w.figur.axes) == 2 and w.cizildi_mi()
                and gorulen[-1] == ["xy", "xz"], "-> %s %s" % (gorulen, w.son_hata()))
        kontrol("3B: kesit secimi gorunur, varsayilan xy + xz",
                not w.eksen.isHidden() and w.eksen.currentText() == IKILI)
        gorulen.clear()
        w.eksen.setCurrentText("xz")          # secim degisince kendisi cizer
        w.bekle(120)
        kontrol("3B'de tek kesit secilebilir (xz; eldeki dilimden, isciye gitmeden)",
                len(w.figur.axes) == 1 and gorulen == [], "-> %s" % gorulen)
        gorulen.clear()
        w.spec_ayarla(_ornek("pwr_17x17"))
        w._ciz()
        w.bekle(120)
        kontrol("2B: yalnizca xy, kesit secimi gizli",
                w.gorunum() == ["xy"] and len(w.figur.axes) == 1 and w.eksen.isHidden()
                and gorulen[-1] == ["xy"])
        w.spec_ayarla(s3)
        kontrol("2B -> 3B: gorunum yeniden xy + xz", w.eksen.currentText() == IKILI)
        w.cozunurluk.setCurrentIndex(0)       # yeni dilim: isciye gider
        w.bekle(120)
        kontrol("cozunurluk degisimi yeniden dilimler, cizim gecerli",
                w.cizildi_mi() and len(w.figur.axes) == 2 and gorulen[-1] == ["xy", "xz"])
    finally:
        w._istemci.iste = asil
        w.kapat()
        os.chdir(KOK)

    # sure: ayni modelde ikinci cizim init'siz (oturum acik): ilkinden kisa
    def sure(ww, spec):
        ww.spec_ayarla(spec)
        t0 = time.perf_counter()
        ww._ciz()
        ww.bekle(120)
        return time.perf_counter() - t0
    ww = OnizlemeWidget()
    try:
        ilk = sure(ww, _ornek("pwr_3b"))
        ww.cozunurluk.setCurrentIndex(2)
        t0 = time.perf_counter()
        ww.bekle(120)
        ikinci = time.perf_counter() - t0
    finally:
        ww.kapat()
    kontrol("ayni modelde yeniden dilimleme ilk cizimden kisa (%.0f / %.0f ms)"
            % (ikinci * 1000, ilk * 1000), ikinci < ilk)
    uyg  # noqa: B018


HIZLI = [test_kor_tur_bilgisi, test_kor_gorunen_alanlar, test_kor_sinir_ogeleri,
         test_kor_yukseklik_secimi, test_kor_katman_sirasi, test_kor_harita_boyama,
         test_kor_tur_gecisi_ve_yansitici,
         test_numarali_sekme_atfi_yok, test_ayar_hassasiyet, test_ayar_moda_gore_gizleme,
         test_ayar_calistirma_dokunulmaz, test_ayar_gelismis_ve_entropi,
         test_ayar_guc_dagilimi, test_ayar_tally_setleri, test_ayar_yukleme_kayit_kimligi,
         test_enerji_girdisi_degistirilmeden_tam_geri_verir,
         ]
YAVAS = [test_onizleme_ikili_kesit, test_kor_yalniz_tur_alanlari_yazilir]


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
