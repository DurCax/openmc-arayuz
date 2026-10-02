# -*- coding: utf-8 -*-
"""
test_kapsul.py -- Dalga S-4 (Y2, Ek oneri M4): tekrarlanabilirlik kapsulu
(kapsul.json) ve `openmc-arayuz-kosu yeniden <kosu_dizini>`.
"""

import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI, gereksinim

_SAHTE_ORTAM = {"yontem": "sahte", "sha256": "0" * 64, "satir_sayisi": 3}


def _spec():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@contextlib.contextmanager
def _sahte_ortam():
    """conda list --export ~2 s surer; hizli testlerde sabit ozet kullanilir."""
    from cekirdek import kapsul
    eski = kapsul.ortam_kilidi
    kapsul.ortam_kilidi = lambda: dict(_SAHTE_ORTAM)
    try:
        yield
    finally:
        kapsul.ortam_kilidi = eski


def _kapsullu_dizin(spec=None, is_parcacigi=3):
    from cekirdek import kapsul, sema
    dizin = tempfile.mkdtemp(prefix="kapsul_")
    sema.kaydet(spec or _spec(), os.path.join(dizin, "spec.json"))
    with _sahte_ortam():
        kapsul.yaz(dizin, spec or _spec(), is_parcacigi=is_parcacigi)
    return dizin


def _cikti(islev, *a):
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(tampon):
        kod = islev(*a)
    return kod, tampon.getvalue()


@gereksinim("R-S-16")
def test_kapsul_icerigi():
    print("\n[KP1] kapsul.json: spec karmasi, surumler, kutuphane, zincir, tohum, ortam")
    from cekirdek import kapsul, surum
    import openmc
    dizin = _kapsullu_dizin()
    try:
        yol = os.path.join(dizin, kapsul.KAPSUL_ADI)
        kontrol("kapsul.json yazildi", os.path.isfile(yol))
        k = kapsul.oku(dizin)
        kontrol("surum alani", k["kapsul_surumu"] == kapsul.KAPSUL_SURUMU)
        kontrol("spec sha256 = spec.json bayt karmasi",
                k["spec"]["sha256"] == _sha(os.path.join(dizin, "spec.json")))
        kontrol("uygulama surumu", k["uygulama"]["surum"] == surum.surum())
        kontrol("git commit alani var", "git_commit" in k["uygulama"])
        kontrol("openmc surumu", k["openmc"]["surum"] == openmc.__version__)
        from cekirdek import veri_yolu
        xs = veri_yolu.cross_sections().deger      # kapsul ayni cozumleyiciden okur
        kut = k["kutuphane"]
        if xs and os.path.isfile(xs):
            kontrol("cross_sections.xml karmasi", kut["cross_sections"]["sha256"] == _sha(xs))
            kontrol("kutuphane dizin ozeti", kut["dosya_sayisi"] > 0 and kut["toplam_boyut"] > 0)
        else:
            kontrol("kutuphane yoksa durum yazilir", kut.get("durum") == "yok", "-> %r" % kut)
        kontrol("tukenme kapali -> zincir None", k["zincir"] is None)
        kontrol("tohum spec'ten", k["tohum"] == int(_spec()["ayarlar"]["tohum"]))
        kontrol("is parcacigi", k["is_parcacigi"] == 3)
        kontrol("ortam kilidi", k["ortam"] == _SAHTE_ORTAM)
        kontrol("JSON okunur metin", json.load(open(yol, encoding="utf-8"))["spec"]["dosya"]
                == "spec.json")
    finally:
        shutil.rmtree(dizin, True)


@gereksinim("R-S-16")
def test_dosya_kimligi_ve_zincir():
    print("\n[KP2] buyuk dosya: yol + boyut + mtime; kucuk: tam sha256; zincir tukenmede")
    from cekirdek import kapsul
    d = tempfile.mkdtemp()
    try:
        yol = os.path.join(d, "a.bin")
        with open(yol, "wb") as f:
            f.write(b"x" * 100)
        kucuk = kapsul.dosya_kimligi(yol)
        kontrol("kucuk dosya tam karma", kucuk["sha256"] == _sha(yol)
                and kucuk["karma_yontemi"] == "tam")
        buyuk = kapsul.dosya_kimligi(yol, sinir=10)
        kontrol("buyuk dosya: sha yok, boyut+mtime", buyuk["sha256"] is None
                and buyuk["karma_yontemi"] == "boyut+mtime" and buyuk["boyut"] == 100
                and buyuk["mtime"] > 0, "-> %r" % buyuk)
        yok = kapsul.dosya_kimligi(os.path.join(d, "yok"))
        kontrol("olmayan dosya: durum yok", yok["durum"] == "yok")
        spec = _spec()
        spec["tukenme"] = dict(spec.get("tukenme") or {}, var=True)
        z = kapsul.zincir_kimligi(spec)
        kontrol("tukenmede zincir kimligi", z is not None and z["yol"].endswith(".xml"),
                "-> %r" % z)
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-16")
def test_ortam_kilidi_yedekleri():
    print("\n[KP3] ortam kilidi: conda yoksa pip freeze, hicbiri yoksa yontem None + log")
    from cekirdek import kapsul
    py = sys.executable
    yok = ("conda list --export", ["/yok/conda-yok", "list", "--export"])
    pip = ("pip freeze", [py, "-c", "print('a==1'); print('b==2')"])
    k = kapsul.ortam_kilidi_hesapla([yok, pip])
    kontrol("ikinci adaya duser", k["yontem"] == "pip freeze" and k["satir_sayisi"] == 2,
            "-> %r" % k)
    kontrol("karma satirlarin karmasi",
            k["sha256"] == hashlib.sha256(b"a==1\nb==2\n").hexdigest())
    hic = kapsul.ortam_kilidi_hesapla([yok])
    kontrol("hicbiri yoksa yontem None", hic["yontem"] is None and hic["sha256"] is None)
    kontrol("neden yazilir", bool(hic.get("neden")), "-> %r" % hic)


@gereksinim("R-S-17")
def test_farklar():
    print("\n[KP4] farklar(): degisen alanlar; olusturma zamani sayilmaz")
    from cekirdek import kapsul
    a = {"olusturma": "t1", "openmc": {"surum": "0.16.0"}, "ortam": {"sha256": "aa"},
         "tohum": 1, "zincir": None}
    b = copy.deepcopy(a)
    b.update(olusturma="t2", tohum=1)
    kontrol("ayni -> fark yok", kapsul.farklar(a, b) == [])
    b["openmc"]["surum"] = "0.15.2"
    b["ortam"]["sha256"] = "bb"
    b["zincir"] = {"sha256": "cc"}
    f = {alan: (e, y) for alan, e, y in kapsul.farklar(a, b)}
    kontrol("openmc surumu farki", f.get("openmc.surum") == ("0.16.0", "0.15.2"), "-> %r" % f)
    kontrol("ortam farki", f.get("ortam.sha256") == ("aa", "bb"))
    kontrol("None -> sozluk farki", "zincir.sha256" in f)
    kontrol("olusturma yok", not any(k.startswith("olusturma") for k in f))


@gereksinim("R-S-17")
def test_yeniden_kuru_calisma():
    print("\n[KP5] yeniden --kuru: plan + ortam farki; kosu yok; spec degisirse ret")
    from cekirdek import kapsul
    dizin = _kapsullu_dizin()
    hedef = dizin + "_yeniden"
    try:
        with _sahte_ortam():
            kod, metin = _cikti(kapsul.yeniden_komutu, [dizin, "--kuru"])
        kontrol("cikis 0", kod == 0, "-> %r\n%s" % (kod, metin))
        kontrol("kuru calisma yazildi", "kuru" in metin.lower(), metin)
        kontrol("hedef dizin olusmadi", not os.path.exists(hedef))
        kontrol("ortam ayni denir", "farkı yok" in metin, metin)
        # kapsuldeki ortam farkli -> fark listelenir
        yol = os.path.join(dizin, kapsul.KAPSUL_ADI)
        k = kapsul.oku(dizin)
        k["openmc"]["surum"] = "0.0.1"
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(k, f)
        with _sahte_ortam():
            kod, metin = _cikti(kapsul.yeniden_komutu, [dizin, "--kuru"])
        kontrol("ortam farki raporlandi", kod == 0 and "openmc.surum" in metin and "0.0.1" in metin,
                metin)
        # spec.json kapsulden sonra degisti -> ret (2)
        with open(os.path.join(dizin, "spec.json"), "a", encoding="utf-8") as f:
            f.write(" ")
        kod, metin = _cikti(kapsul.yeniden_komutu, [dizin, "--kuru"])
        kontrol("degismis spec reddedilir", kod == 2 and "spec" in metin, "-> %r %s" % (kod, metin))
        # kapsulsuz dizin / hedef = kaynak
        bos = tempfile.mkdtemp()
        kod, metin = _cikti(kapsul.yeniden_komutu, [bos, "--kuru"])
        kontrol("kapsulsuz dizin -> 2", kod == 2 and kapsul.KAPSUL_ADI in metin, metin)
        shutil.rmtree(bos, True)
        kod, metin = _cikti(kapsul.yeniden_komutu, [dizin, "--hedef", dizin, "--kuru"])
        kontrol("hedef = kaynak reddedilir", kod == 2, metin)
        kod, metin = _cikti(kapsul.yeniden_komutu, ["--help"])
        kontrol("yardim", kod == 0 and "yeniden" in metin)
    finally:
        shutil.rmtree(dizin, True)
        shutil.rmtree(hedef, True)


@gereksinim("R-S-16")
def test_kosucu_kapsul_yazar():
    print("\n[KP6] kosucu.xml_yaz kapsul.json yazar; dizin_hazirla eskisini siler; CLI yonlendirir")
    from cekirdek import giris, kapsul, kosucu
    dizin = tempfile.mkdtemp(prefix="kapsul_kosu_")
    try:
        with _sahte_ortam():
            kosucu.xml_yaz(_spec(), dizin, is_parcacigi=5)
        k = kapsul.oku(dizin)
        kontrol("xml_yaz kapsul yazdi", k["is_parcacigi"] == 5
                and k["spec"]["sha256"] == _sha(os.path.join(dizin, "spec.json")))
        with _sahte_ortam():
            kosucu.xml_yaz(_spec(), dizin)
        kontrol("is parcacigi verilmezse spec'teki", kapsul.oku(dizin)["is_parcacigi"]
                == _spec()["calistirma"].get("is_parcacigi"))
        with _sahte_ortam():
            kod, metin = _cikti(kosucu._terminal, ["yeniden", dizin, "--kuru"])
        kontrol("kosucu._terminal yeniden", kod == 0, metin)
        with _sahte_ortam():
            kod, metin = _cikti(giris.kosu, ["yeniden", dizin, "--kuru"])
        kontrol("openmc-arayuz-kosu yeniden", kod == 0, metin)
        kosucu.dizin_hazirla(dizin, temizle=True)
        kontrol("dizin_hazirla eski kapsulu siler",
                not os.path.exists(os.path.join(dizin, kapsul.KAPSUL_ADI)))
    finally:
        shutil.rmtree(dizin, True)


@gereksinim("R-S-16", "R-M10-02")
def test_rapor_kapsul_satiri():
    print("\n[KP7] rapor tekrarlanabilirlik blogu kapsule baglanir")
    from cekirdek import kapsul, rapor
    dizin = _kapsullu_dizin()
    try:
        d = dict(rapor.tekrarlanabilirlik(_spec(), dizin)[0])
        satir = d.get("Tekrarlanabilirlik kapsülü", "")
        kontrol("kapsul satiri", kapsul.KAPSUL_ADI in satir and "eşleşiyor" in satir,
                "-> %r" % satir)
        with open(os.path.join(dizin, "spec.json"), "a", encoding="utf-8") as f:
            f.write(" ")
        satir = dict(rapor.tekrarlanabilirlik(_spec(), dizin)[0]).get(
            "Tekrarlanabilirlik kapsülü", "")
        kontrol("degismis spec raporda yazilir", "EŞLEŞMİYOR" in satir, "-> %r" % satir)
        bos = tempfile.mkdtemp()
        alanlar, uyarilar = rapor.tekrarlanabilirlik(_spec(), bos)
        kontrol("kapsulsuz dizinde satir yok, uyari yok",
                "Tekrarlanabilirlik kapsülü" not in dict(alanlar)
                and not any("kapsül" in u for u in uyarilar))
        shutil.rmtree(bos, True)
    finally:
        shutil.rmtree(dizin, True)


@gereksinim("R-S-17")
def test_yavas_yeniden_kosu(gecici):
    print("\n[KP8] kisa koşu + yeniden: ayni tohum ve ortamla k-eff ayni")
    from cekirdek import kapsul, kosucu
    spec = _spec()
    spec["ayarlar"].update(parcacik=500, cevrim=12, pasif=4)
    dizin = os.path.join(gecici, "kosu")
    sonuc = kosucu.calistir(spec, dizin, is_parcacigi=ISLEM_PARCACIGI)
    kontrol("ilk kosu basarili", sonuc["basarili"])
    kontrol("kosu dizininde kapsul", os.path.isfile(os.path.join(dizin, kapsul.KAPSUL_ADI)))
    hedef = os.path.join(gecici, "yeniden")
    kod, metin = _cikti(kapsul.yeniden_komutu, [dizin, "--hedef", hedef])
    print(metin)
    kontrol("yeniden kosu cikis 0", kod == 0, "-> %r" % kod)
    kontrol("hedefte statepoint", kosucu.son_statepoint(hedef) is not None)
    kontrol("k-eff ayni denir (birebir ya da yuvarlama duzeyinde)",
            "birebir aynı" in metin or "k-eff aynı (yalnız kayan nokta" in metin, metin)


HIZLI = [test_kapsul_icerigi, test_dosya_kimligi_ve_zincir, test_ortam_kilidi_yedekleri,
         test_farklar, test_yeniden_kuru_calisma, test_kosucu_kapsul_yazar,
         test_rapor_kapsul_satiri]
YAVAS = [test_yavas_yeniden_kosu]
