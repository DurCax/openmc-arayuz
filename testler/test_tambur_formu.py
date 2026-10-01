# -*- coding: utf-8 -*-
"""
test_tambur_formu.py -- Parcalar > Tamburlar (kontrol tamburu kutuphanesi) formu.

  [TF1] Gelismis modda Tamburlar bolumu gorunur; sablon modunda gizli.
  [TF2] Form spec["tamburlar"] tanimini okur/yazar (yaricap, govde/emici
        malzeme, emici ic yaricap, emici yay acisi); emici ic yaricap < yaricap.
  [TF3] Ekle: benzersiz ad, malzemeler rolden; sil: kullaniliyorsa onay.
  [TF4] Ad degisimi geometri.ad_degistir(spec, "tambur", ...) ile: agactaki
        yerlesim icerigi de yeni adi gosterir; cakisan ad reddedilir.
  [TF5] Gelismis editorun Yerlesim formu icerigi kutuphaneden secer.
  [TF6] Spec gidis-donusu: butun orneklerde Parcalar/Demet/Tukenme sayfalarini
        yuklemek spec'i degistirmez.
"""

import copy
import glob
import os

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _sekme(spec):
    from arayuz.sekme_cubuk import CubukSekmesi
    w = CubukSekmesi()
    w.spec_yukle(spec)
    return w


def _yerlesim_yolu(d, ad, yol=()):
    """Agacta 'ad' adli yerlesimin yolu (ilk bulunan)."""
    if isinstance(d, dict):
        if d.get("ad") == ad and "mod" in d:
            return yol
        for k, v in d.items():
            r = _yerlesim_yolu(v, ad, yol + (k,))
            if r is not None:
                return r
    elif isinstance(d, list):
        for i, v in enumerate(d):
            r = _yerlesim_yolu(v, ad, yol + (i,))
            if r is not None:
                return r
    return None


def test_tambur_bolumu_gorunurluk():
    print("\n[TF1] Tamburlar bolumu: gelismis modda gorunur, sablonda gizli")
    _qt()
    w = _sekme(_yukle("altigen_tambur_halkasi"))
    kontrol("gelismis: bolum gorunur", not w.tambur_karti.isHidden())
    adlar = [w.t_liste.item(i).text() for i in range(w.t_liste.count())]
    kontrol("listede tambur_b4c", adlar == ["tambur_b4c"], "-> %s" % adlar)
    kontrol("bolum basligi 'Tamburlar'", w.tambur_karti.baslik_etiketi.text() == "Tamburlar")
    w.spec_yukle(_yukle("pwr_17x17"))
    kontrol("sablon modu: bolum gizli", w.tambur_karti.isHidden())


def test_tambur_formu_okur_yazar():
    print("\n[TF2] form spec['tamburlar']'i okur ve yazar")
    _qt()
    spec = _yukle("altigen_tambur_halkasi")
    w = _sekme(spec)
    olaylar = []
    w.degisti.connect(olaylar.append)
    w.t_liste.setCurrentRow(0)
    kontrol("tambur sayfasi acik", w.yigin.currentWidget() is w.tambur_sayfa)
    t = spec["tamburlar"][0]
    kontrol("alanlar spec'ten", (w.t_ad.text(), w.t_yaricap.value(), w.t_ic.value(),
                                 w.t_aci.value(), w.t_govde.currentData(),
                                 w.t_emici.currentData())
            == ("tambur_b4c", 6.0, 4.5, 120.0, "berilyum", "b4c"))
    w.t_yaricap.setValue(7.0)
    w.t_aci.setValue(90.0)
    kontrol("yaricap ve yay yazildi", t["yaricap"] == 7.0 and t["emici_aci"] == 90.0,
            "-> %s" % t)
    kontrol("degisti yayildi", bool(olaylar))
    kontrol("emici ic yaricap ust siniri < yaricap", w.t_ic.maximum() < 7.0)
    w.t_ic.setValue(6.9)
    w.t_yaricap.setValue(5.0)
    kontrol("yaricap kuculunce ic yaricap sinirlanir", t["emici_ic_yaricap"] < 5.0,
            "-> %s" % t)
    i = w.t_emici.findData("celik") if w.t_emici.findData("celik") >= 0 else 0
    w.t_emici.setCurrentIndex(i)
    kontrol("emici malzeme yazildi", t["emici_malzeme"] == w.t_emici.currentData())


def test_tambur_ekle_sil():
    print("\n[TF3] ekle (benzersiz ad, rol) / sil (kullaniliyorsa onay)")
    _qt()
    spec = _yukle("altigen_tambur_halkasi")
    w = _sekme(spec)
    ad = w.tambur_ekle()
    kontrol("yeni tambur eklendi", [t["ad"] for t in spec["tamburlar"]] == ["tambur_b4c", ad]
            and ad != "tambur_b4c", "-> %s" % ad)
    yeni = spec["tamburlar"][1]
    kontrol("zorunlu alanlar dolu", all(k in yeni for k in (
        "yaricap", "govde_malzeme", "emici_malzeme", "emici_ic_yaricap", "emici_aci")))
    kontrol("emici rolden (b4c)", yeni["emici_malzeme"] == "b4c", "-> %s" % yeni)
    kontrol("yeni tambur secili", w.t_ad.text() == ad)
    w._onay_al = lambda *_a: (_ for _ in ()).throw(AssertionError("onay sorulmamali"))
    w._tambur_sil()
    kontrol("kullanilmayan tambur onaysiz silindi", [t["ad"] for t in spec["tamburlar"]]
            == ["tambur_b4c"])
    w.t_liste.setCurrentRow(0)
    sorular = []
    w._onay_al = lambda *a: sorular.append(a) or False
    w._tambur_sil()
    kontrol("kullanilan tambur: onay soruldu, hayir -> kalir",
            sorular and len(spec["tamburlar"]) == 1)
    kontrol("onay metni kullanim yerini soyler", "tambur_halkasi" in sorular[0][1]
            or "yerleşim" in sorular[0][1], "-> %s" % (sorular[0][1] if sorular else ""))
    w._onay_al = lambda *_a: True
    w._tambur_sil()
    kontrol("evet -> silindi", spec["tamburlar"] == [])


def test_tambur_ad_degisimi():
    print("\n[TF4] ad degisimi agactaki basvurulari gunceller")
    _qt()
    from cekirdek.geometri.basvuru import basvurular
    spec = _yukle("altigen_tambur_halkasi")
    w = _sekme(spec)
    w.t_liste.setCurrentRow(0)
    w.t_ad.setText("tambur_yeni")
    w.t_ad.editingFinished.emit()
    tamburlar = [t["ad"] for t in spec["tamburlar"]]
    bas = {b.ad for b in basvurular(spec) if b.tur == "tambur"}
    kontrol("kutuphanede yeni ad", tamburlar == ["tambur_yeni"], "-> %s" % tamburlar)
    kontrol("agac basvurusu yeni ad", bas == {"tambur_yeni"}, "-> %s" % bas)
    kontrol("secim korundu", w.t_ad.text() == "tambur_yeni")
    w.t_ad.setText("berilyum")
    w.t_ad.editingFinished.emit()
    kontrol("malzeme adiyla cakisan ad reddedilir",
            [t["ad"] for t in spec["tamburlar"]] == ["tambur_yeni"]
            and not w.t_ad_hata.isHidden())


def test_yerlesim_formu_kutuphaneden_secer():
    print("\n[TF5] Yerlesim formu icerigi kutuphaneden (tambur) secer")
    _qt()
    from arayuz.geometri import duzenle
    from arayuz.geometri.form_yerlesim import YerlesimFormu
    spec = _yukle("altigen_tambur_halkasi")
    spec["tamburlar"].append(dict(spec["tamburlar"][0], ad="tambur_iki"))
    agac = spec["geometri"]
    yol = _yerlesim_yolu(agac, "tambur_halkasi")
    f = YerlesimFormu()
    f.yukle(spec, agac, yol)
    veriler = [f.icerik.itemData(i) for i in range(f.icerik.count())]
    kontrol("icerik kutusunda tamburlar", "tambur_b4c" in veriler and "tambur_iki" in veriler,
            "-> %s" % veriler)
    kontrol("secili: mevcut icerik", f.icerik.currentData() == "tambur_b4c")
    yayilan = []
    f.agac_degisti.connect(yayilan.append)
    f.icerik.setCurrentIndex(f.icerik.findData("tambur_iki"))
    y = duzenle.al(yayilan[-1], yol) if yayilan else {}
    kontrol("yeni icerik agaca yazildi", (y.get("icerik") or {}).get("ad") == "tambur_iki"
            and y["icerik"].get("tur") == "bilesen", "-> %s" % (y.get("icerik"),))
    kontrol("dogal kesit tamburda etkin", f.dogal.isEnabled())
    agac2 = duzenle.yaz(yayilan[-1], yol + ("icerik",), {"tur": "malzeme", "ad": "berilyum"})
    f.yukle(spec, agac2, yol)
    kontrol("bilesen olmayan icerik: secilemeyen ilk oge", f.icerik.currentData() is None
            and f.icerik.currentIndex() == 0)
    n = len(yayilan)
    f.icerik.setCurrentIndex(0)
    kontrol("bos secim agaci degistirmez", len(yayilan) == n)
    f.icerik.setCurrentIndex(f.icerik.findData("yakit_cubugu"))
    y = duzenle.al(yayilan[-1], yol)
    kontrol("cubuk secilince dogal kesit kapali", not f.dogal.isEnabled()
            and y["icerik"]["ad"] == "yakit_cubugu" and y.get("kesit") is not None,
            "-> %s" % (y.get("icerik"), ))


def test_yerlesim_formu_liste_ve_ad():
    print("\n[TF5b] Yerlesim formu: liste modu konum ekle/sil, ad degisimi")
    _qt()
    from arayuz.geometri import duzenle
    from arayuz.geometri.form_yerlesim import YerlesimFormu
    spec = _yukle("altigen_tambur_halkasi")
    agac = spec["geometri"]
    yol = _yerlesim_yolu(agac, "tambur_halkasi")
    f = YerlesimFormu()
    f.yukle(spec, agac, yol)
    f.mod.setCurrentIndex(f.mod.findData("liste"))
    f.d_konum_ekle.click()
    f.d_konum_ekle.click()
    y = duzenle.al(f.agac, yol)
    kontrol("liste modu: iki konum", y.get("mod") == "liste"
            and y.get("konumlar") == [[0.0, 0.0], [0.0, 0.0]], "-> %s" % y.get("konumlar"))
    f.konumlar.setCurrentCell(0, 0)
    f.d_konum_sil.click()
    kontrol("konum silindi", len(duzenle.al(f.agac, yol).get("konumlar")) == 1)
    f.ad.setText("halka_yeni")
    f.ad.editingFinished.emit()
    kontrol("ad degisti (grup uyesi de)", duzenle.al(f.agac, yol).get("ad") == "halka_yeni"
            and "halka_yeni" in (f.agac.get("gruplar") or [{}])[0].get("uyeler", []),
            "-> %s" % f.agac.get("gruplar"))


def test_spec_gidis_donusu_ornekler():
    print("\n[TF6] butun ornekler: Parcalar/Demet/Tukenme yuklemek spec'i degistirmez")
    _qt()
    from cekirdek import sema
    from arayuz.sekme_cubuk import CubukSekmesi
    from arayuz.sekme_demet import DemetSekmesi
    from arayuz.sekme_tukenme import TukenmeSekmesi
    sayfalar = (CubukSekmesi(), DemetSekmesi(), TukenmeSekmesi())
    yollar = sorted(glob.glob(os.path.join(ORNEK, "*.json")))
    bozulan = []
    for yol in yollar:
        spec = sema.yukle(yol)
        once = copy.deepcopy(spec)
        for s in sayfalar:
            s.spec_yukle(spec)
        if spec != once:
            bozulan.append(os.path.basename(yol))
    kontrol("%d ornek: gidis-donus bozulmaz" % len(yollar), len(yollar) >= 30 and not bozulan,
            "-> %s" % bozulan)


HIZLI = [test_tambur_bolumu_gorunurluk, test_tambur_formu_okur_yazar, test_tambur_ekle_sil,
         test_tambur_ad_degisimi, test_yerlesim_formu_kutuphaneden_secer,
         test_yerlesim_formu_liste_ve_ad,
         test_spec_gidis_donusu_ornekler]
YAVAS = []
