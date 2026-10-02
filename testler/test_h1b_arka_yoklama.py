# -*- coding: utf-8 -*-
"""
 test_h1b_arka_yoklama.py  --  v3 H1b: nokta yoklamasi ayri surecte (arayuz)

 yoklama.arka_planda(bildir) blogunda yokla() sonucu hazir degilse isi tek
 iscili spawn surecine verir ve None doner; agac_kontrol bunu "arka planda
 suruyor" BILGI'si olarak yazar. Sonuc gelince bildir() cagrilir ve ayni
 icerikte yokla() esli yolla AYNI sonucu (nokta + hucre kimligi + metin) verir.
 Kosu kapisi (dogrula.kapi) blok disinda: esli, eksiksiz.
"""

import os
import threading

from testler.ortak_test import kontrol, ORNEK

_BEKLEME = 120.0               # s: isci sureci (spawn + openmc ice aktarma) + yoklama


def _ozet(sonuc, metinler):
    def liste(x):
        return [(tuple(p), [h.id for h in hucreler]) for p, hucreler in x]
    return sonuc.n, liste(sonuc.bosluklar), liste(sonuc.ortusmeler), list(metinler)


def _arka_planda_bekle(islev):
    """islev() blokta calisir; sonuc gelene kadar bekler, sonra ikinci cagri."""
    from cekirdek.geometri import yoklama
    geldi = threading.Event()
    with yoklama.arka_planda(geldi.set):
        ilk = islev()
    tamam = geldi.wait(_BEKLEME)
    with yoklama.arka_planda(geldi.set):
        ikinci = islev()
    return ilk, tamam, ikinci


def test_arka_plan_sonucu_esli_ile_ayni():
    print("\n[H1b-A1] arka planda yokla: once None, sonra esli yolla birebir ayni")
    from cekirdek import uygunluk_bellek
    from cekirdek.geometri import yoklama, yoklama_arka
    from testler.test_geometri_dogrulama import ortusen_model
    spec = ortusen_model()
    uygunluk_bellek.temizle()
    yoklama_arka.temizle()
    ilk, tamam, ikinci = _arka_planda_bekle(lambda: yoklama.yokla(spec, n=1500, tohum=3))
    kontrol("ilk cagri None (is surecte)", ilk is None)
    kontrol("bildirim geldi", tamam)
    esli = yoklama.yokla(spec, n=1500, tohum=3)
    kontrol("arka plan sonucu esli ile ayni (nokta, hucre kimligi, metin)",
            ikinci is not None and _ozet(*ikinci) == _ozet(*esli))
    kontrol("ortusme bulundu", ikinci is not None and len(ikinci[0].ortusmeler) > 0)


def test_agac_kontrol_bekleyen_bilgi_sonra_ayni_bulgular():
    print("\n[H1b-A2] agac_kontrol arka planda: once BILGI, sonra esli ile ayni bulgular")
    from cekirdek import uygunluk_bellek
    from cekirdek.dogrula import agac
    from cekirdek.geometri import yoklama_arka
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kare_altigen_halka.json"))
    uygunluk_bellek.temizle()
    yoklama_arka.temizle()
    ilk, tamam, ikinci = _arka_planda_bekle(lambda: agac.agac_kontrol(spec))
    kontrol("ilk: 'arka planda' BILGI", any(b.seviye == "bilgi" and "arka planda" in b.mesaj
                                            for b in ilk), "-> %s" % [b.mesaj for b in ilk])
    kontrol("bildirim geldi", tamam)
    esli = agac.agac_kontrol(spec)
    def t(liste):
        return [(b.seviye, b.yer, b.mesaj, b.oneri) for b in liste]
    kontrol("sonra esli ile ayni bulgular (bekleyen BILGI yok)", t(ikinci) == t(esli),
            "-> %s" % [b.mesaj[:60] for b in ikinci])


def test_blok_disinda_esli():
    print("\n[H1b-A3] arka_planda blogu disinda yokla esli (None donmez)")
    from cekirdek import sema
    from cekirdek.geometri import yoklama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kare_altigen_halka.json"))
    kontrol("esli sonuc", yoklama.yokla(spec, n=50) is not None)


def test_kurulum_hatasi_ayni_istisna():
    print("\n[H1b-A4] kurulamayan model: arka plan sonucu esli ile ayni istisna")
    import copy
    from cekirdek import uygunluk_bellek
    from cekirdek.geometri import yoklama, yoklama_arka
    from testler.test_geometri_dogrulama import ortusen_model
    spec = copy.deepcopy(ortusen_model())
    spec["malzemeler"] = []
    uygunluk_bellek.temizle()
    yoklama_arka.temizle()

    def dene():
        try:
            return yoklama.yokla(spec, n=50)
        except (KeyError, ValueError, RuntimeError) as e:
            return ("hata", type(e).__name__, str(e))
    ilk, tamam, ikinci = _arka_planda_bekle(dene)
    esli = dene()
    kontrol("esli yol hata veriyor", isinstance(esli, tuple) and esli[0] == "hata", "-> %r" % (esli,))
    kontrol("arka plan ayni hata", tamam and ikinci == esli, "-> %r / %r" % (ikinci, esli))


HIZLI = [test_blok_disinda_esli, test_arka_plan_sonucu_esli_ile_ayni,
         test_agac_kontrol_bekleyen_bilgi_sonra_ayni_bulgular, test_kurulum_hatasi_ayni_istisna]
YAVAS = []


# ---------------------------------------------------------------------------
# inceleme 2. tur: kuyruk, cokme, zaman asimi, kapat, dil, Qt koprusu
# ---------------------------------------------------------------------------

def _kucuk_spec():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def _istek_bekle(anahtar, spec, n=30):
    from cekirdek.geometri import yoklama_arka
    geldi = threading.Event()
    kontrol("istek kuyrukta", yoklama_arka.istek(anahtar, spec, n, 1, geldi.set))
    return geldi.wait(_BEKLEME)


def test_isci_cokerse_coktu_isareti_ve_esli_yol():
    print("\n[H1b-A5] isci sonlandirilirsa: anahtar 'coktu', bildir cagrilir, yokla esli yola duser")
    from cekirdek.geometri import yoklama, yoklama_arka
    spec = _kucuk_spec()
    yoklama_arka.temizle()
    _istek_bekle("isinma", spec)                 # isci acik
    geldi = threading.Event()
    yoklama_arka.istek("cokme", spec, 20000, 7, geldi.set)
    yoklama_arka._YONETICI.surec.kill()
    kontrol("bildir cagrildi", geldi.wait(_BEKLEME))
    kontrol("anahtar coktu", yoklama_arka.sonuc_al("cokme") == yoklama_arka.COKTU)
    anahtar = yoklama_arka.anahtar_dilli(
        yoklama.icerik_anahtari([spec, 10, 1]))
    yoklama_arka._YONETICI._sakla(anahtar, {"durum": yoklama_arka.COKTU})
    with yoklama.arka_planda(lambda: None):
        sonuc = yoklama.yokla(spec, n=10, tohum=1)
    kontrol("coktu isaretinde yokla esli sonuc verir (None degil)", sonuc is not None)


def test_isci_baslatilamazsa_istek_false(monkeypatch):
    print("\n[H1b-A6] isci baslatilamazsa istek False, yokla esli sonuc verir")
    from cekirdek import giris, uygunluk_bellek
    from cekirdek.geometri import yoklama, yoklama_arka
    yoklama_arka.kapat()
    monkeypatch.setattr(giris, "alt_surec_komutu",
                        lambda *a, **k: ("/olmayan/yorumlayici", []))
    uygunluk_bellek.temizle()
    kontrol("istek False", yoklama_arka.istek("x", _kucuk_spec(), 10, 1, lambda: None) is False)
    with yoklama.arka_planda(lambda: None):
        sonuc = yoklama.yokla(_kucuk_spec(), n=11, tohum=1)
    kontrol("esli sonuc (None degil)", sonuc is not None)


def test_art_arda_isteklerde_bekleyen_en_yeni():
    print("\n[H1b-A7] art arda istek: kosan kesilmez, aradaki atlanir, en yeni kosar")
    from cekirdek.geometri import yoklama_arka
    yoklama_arka.temizle()
    spec = _kucuk_spec()
    bitti = {k: threading.Event() for k in ("k1", "k2", "k3")}
    for k in ("k1", "k2", "k3"):
        yoklama_arka.istek(k, spec, 3000, 1, bitti[k].set)
    kontrol("k1 ve k3 bitti", bitti["k1"].wait(_BEKLEME) and bitti["k3"].wait(_BEKLEME))
    kontrol("k2 atlandi (sonuc yok, bildirim yok)", yoklama_arka.sonuc_al("k2") is None
            and not bitti["k2"].is_set())
    kontrol("k1, k3 sonuclari var", yoklama_arka.sonuc_al("k1") not in (None, "coktu")
            and yoklama_arka.sonuc_al("k3") not in (None, "coktu"))


def test_zaman_asiminda_isci_sonlanir(monkeypatch):
    print("\n[H1b-A8] zaman asimi: isci sonlandirilir, anahtar coktu")
    from cekirdek.geometri import yoklama_arka
    _istek_bekle("isinma2", _kucuk_spec())
    monkeypatch.setattr(yoklama_arka, "ZAMAN_ASIMI", 0.01)
    geldi = threading.Event()
    yoklama_arka.istek("yavas", _kucuk_spec(), 200000, 3, geldi.set)
    kontrol("bildir cagrildi", geldi.wait(_BEKLEME))
    kontrol("anahtar coktu", yoklama_arka.sonuc_al("yavas") == yoklama_arka.COKTU)


def test_kapat_isciyi_sonlandirir():
    print("\n[H1b-A9] kapat(): isci sureci sonlanir")
    from cekirdek.geometri import yoklama_arka
    _istek_bekle("isinma3", _kucuk_spec())
    surec = yoklama_arka._YONETICI.surec
    yoklama_arka.kapat()
    kontrol("surec sonlandi", surec is not None and surec.poll() is not None)


def test_isci_ortami_dil_ve_yol():
    print("\n[H1b-A10] isci ortami: OPENMC_ARAYUZ_DIL etkin dil; anahtar dili icerir")
    from cekirdek import ceviri
    from cekirdek.geometri import yoklama_arka
    ortam = yoklama_arka.isci_ortami({}, "en")
    kontrol("dil ortamda", ortam.get(ceviri.ORTAM_DEGISKENI) == "en")
    kontrol("anahtar dilli", yoklama_arka.anahtar_dilli("a").endswith(":" + ceviri.etkin_dil()))


def test_isci_dongusu_satir_protokolu():
    print("\n[H1b-A11] isci dongusu (ayni surecte): istek satiri -> yanit satiri, hata turu")
    import io
    import json
    from cekirdek.geometri import yoklama_arka
    spec = _kucuk_spec()
    bozuk = dict(spec, malzemeler=[])
    girdi = io.StringIO(json.dumps({"no": 1, "spec": spec, "n": 20, "tohum": 1}) + "\n\n"
                        + json.dumps({"no": 2, "spec": bozuk, "n": 20, "tohum": 1}) + "\n")
    cikti = io.StringIO()
    yoklama_arka.ana([], girdi, cikti)
    yanitlar = [json.loads(s) for s in cikti.getvalue().splitlines()]
    kontrol("iki yanit, no'lar korunur", [y["no"] for y in yanitlar] == [1, 2])
    kontrol("tamam + hata(KeyError)", yanitlar[0]["durum"] == "tamam"
            and yanitlar[1]["durum"] == "hata" and yanitlar[1]["tur"] == "KeyError",
            "-> %s" % [y["durum"] for y in yanitlar])


def test_bildirim_hatasi_kuyrugu_durdurmaz():
    print("\n[H1b-A12] bildir() hata verirse gunluge yazilir, okuyucu/kuyruk surer")
    from cekirdek.geometri import yoklama_arka
    yoklama_arka.temizle()

    def bozuk():
        raise RuntimeError("bildirim")
    yoklama_arka.istek("bozuk_bildirim", _kucuk_spec(), 25, 1, bozuk)
    kontrol("sonraki istek yine biter", _istek_bekle("sonraki", _kucuk_spec(), 26))


def test_qt_koprusu_silinmis_habercide_sessiz():
    print("\n[H1b-A13] haberci silinince bildir() hata vermez (shiboken6.isValid)")
    import shiboken6
    from PySide6 import QtWidgets
    from arayuz.pencere.dogrulama_seridi import DogrulamaMixin
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    class Sahte(DogrulamaMixin, QtWidgets.QWidget):
        pass
    w = Sahte()
    bildir = w._yoklama_bildirimi()
    shiboken6.delete(w._yoklama_haberci)
    try:
        bildir()
        kontrol("hata yok", True)
    except RuntimeError as e:
        kontrol("hata yok", False, repr(e))
    w.deleteLater()


HIZLI += [test_isci_cokerse_coktu_isareti_ve_esli_yol, test_isci_baslatilamazsa_istek_false,
          test_art_arda_isteklerde_bekleyen_en_yeni, test_zaman_asiminda_isci_sonlanir,
          test_kapat_isciyi_sonlandirir, test_isci_ortami_dil_ve_yol,
          test_isci_dongusu_satir_protokolu, test_bildirim_hatasi_kuyrugu_durdurmaz,
          test_qt_koprusu_silinmis_habercide_sessiz]
