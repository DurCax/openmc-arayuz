# -*- coding: utf-8 -*-
"""
 test_k2_veri_indir.py  --  v3 K2: guvenli indirme (cekirdek/veri_indir.py) ve
                            guvenli arsiv acma (cekirdek/veri_arsiv.py)

 AGSIZ: testler/k2_sahte_sunucu.py (http.server, 127.0.0.1). Uretimde yalniz
 https + katalogdaki alan adlari kabul edilir; testler bunu YALNIZ
 UrlPolitikasi nesnesini acikca vererek gevsetir (ortam degiskeni / ayar yok).
 Kabul: kesinti + surdurme (Range), sha256 hatasi, yol gecisi / symlink /
 zip bombasi, disk alani, hedef klasor denetimi.
"""

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import threading

from testler.ortak_test import kontrol, KOK
from testler.k2_sahte_sunucu import SahteSunucu

_VERI = bytes(range(256)) * 4096          # 1 MiB, tekrarsiz olmayan ama sabit icerik
_SHA = hashlib.sha256(_VERI).hexdigest()


def _test_politikasi():
    from cekirdek import veri_indir
    return veri_indir.UrlPolitikasi(semalar=frozenset({"http"}),
                                    alanlar=frozenset({"127.0.0.1"}), port_serbest=True)


def _hata(islev, *a, **kw):
    """islev'in firlattigi istisna (yoksa None)."""
    try:
        islev(*a, **kw)
    except Exception as e:                     # noqa: BLE001 -- test yardimcisi
        return e
    return None


# ---------------------------------------------------------------------------
# katalog
# ---------------------------------------------------------------------------

def test_katalog_kaynakli_ve_gecerli():
    print("\n[K2-I1] katalog: kaynak + tarih, https, izinli alan adi, bayt, sha256 bicimi")
    from cekirdek import veri_indir
    kat = veri_indir.katalog_yukle()
    kontrol("kaynak sayfa ve erisim tarihi",
            kat.kaynak.get("sayfa", "").startswith("https://openmc.org/")
            and kat.kaynak.get("erisim_tarihi"), repr(kat.kaynak))
    kimlikler = [o.kimlik for o in kat.kutuphaneler] + [o.kimlik for o in kat.zincirler]
    kontrol("kimlikler essiz", len(kimlikler) == len(set(kimlikler)))
    adlar = {o.ad for o in kat.kutuphaneler}
    kontrol("ENDF/B-VIII.0, JEFF-3.3, JENDL-5 var",
            {"ENDF/B-VIII.0", "JEFF-3.3", "JENDL-5"} <= adlar, repr(sorted(adlar)))
    politika = veri_indir.katalog_politikasi(kat)
    for o in kat.kutuphaneler + kat.zincirler:
        kontrol("url politikaya uyar: %s" % o.kimlik, _hata(politika.denetle, o.url) is None)
        kontrol("bayt > 0: %s" % o.kimlik, o.bayt > 0)
    zincir_spektrum = {(o.kutuphane, o.spektrum) for o in kat.zincirler}
    kontrol("termal / hizli / CASL zincirleri",
            {("endfb-viii.0", "termal"), ("endfb-viii.0", "hizli"), (None, "termal"),
             (None, "hizli")} <= zincir_spektrum)
    destekli = [o for o in kat.zincirler if o.uygulamada_kullanilir]
    kontrol("uygulamanin kullandigi zincirlerde sha256 var",
            destekli and all(o.sha256 and len(o.sha256) == 64 for o in destekli))
    kontrol("acik boyut orani kaynakli", kat.oran > 1 and "du -sb" in kat.oran_kaynagi)


def test_katalog_gecersiz_reddedilir():
    print("\n[K2-I2] katalog dogrulamasi: http, izinsiz alan adi, kotu sha256, yol iceren ad")
    from cekirdek import veri_indir
    with open(veri_indir.katalog_yolu(), encoding="utf-8") as f:
        temel = json.load(f)

    def bozuk(degistir):
        veri = json.loads(json.dumps(temel))
        degistir(veri)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(veri, f)
        try:
            return _hata(veri_indir.katalog_yukle, f.name)
        finally:
            os.unlink(f.name)

    kontrol("http url", isinstance(bozuk(lambda v: v["kutuphaneler"][0].update(
        url="http://anl.box.com/x.xz")), ValueError))
    kontrol("izinsiz alan", isinstance(bozuk(lambda v: v["zincirler"][0].update(
        url="https://kotu.example.com/x.xml")), ValueError))
    kontrol("kotu sha256", isinstance(bozuk(lambda v: v["zincirler"][2].update(
        sha256="abc")), ValueError))
    kontrol("dosya adinda yol", isinstance(bozuk(lambda v: v["zincirler"][0].update(
        dosya_adi="../x.xml")), ValueError))
    kontrol("dizin adinda yol", isinstance(bozuk(lambda v: v["kutuphaneler"][0].update(
        dizin_adi="/etc")), ValueError))
    kontrol("negatif bayt", isinstance(bozuk(lambda v: v["kutuphaneler"][0].update(
        bayt=-1)), ValueError))


def test_url_politikasi():
    print("\n[K2-I3] uretim politikasi: yalniz https + katalog alan adlari; kullanici bilgisi yok")
    from cekirdek import veri_indir
    p = veri_indir.katalog_politikasi(veri_indir.katalog_yukle())
    kontrol("https izinli alan", _hata(p.denetle, "https://anl.box.com/shared/static/a.xml") is None)
    for kotu in ("http://anl.box.com/a.xml", "ftp://anl.box.com/a", "file:///etc/passwd",
                 "https://evil.com/a", "https://anl.box.com.evil.com/a",
                 "https://user:pw" + "@" + "anl.box.com/a", "https://anl.box.com:8443/a"):
        kontrol("reddedildi: %s" % kotu,
                isinstance(_hata(p.denetle, kotu), veri_indir.IndirmeHatasi))
    kontrol("varsayilan politika https", veri_indir.UrlPolitikasi(alanlar=frozenset(
        {"127.0.0.1"})).semalar == frozenset({"https"}))


# ---------------------------------------------------------------------------
# dosya indirme
# ---------------------------------------------------------------------------

def test_tam_indirme_atomik():
    print("\n[K2-I4] tam indirme: sha256 dogru, .part kalmaz, ilerleme bildirilir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/a.xml"] = _VERI
        hedef = os.path.join(d, "a.xml")
        olaylar = []
        sha = veri_indir.dosya_indir(s.url("/a.xml"), hedef, len(_VERI), _SHA,
                                     politika=_test_politikasi(),
                                     ilerleme=lambda a, t: olaylar.append((a, t)))
        kontrol("sha256 dondu", sha == _SHA)
        with open(hedef, "rb") as f:
            kontrol("icerik ayni", f.read() == _VERI)
        kontrol(".part yok", not os.path.exists(hedef + veri_indir.PARCA_UZANTISI))
        kontrol("ilerleme sonu tam", olaylar and olaylar[-1] == (len(_VERI), len(_VERI)))
        ikinci = veri_indir.dosya_indir(s.url("/a.xml"), hedef, len(_VERI), _SHA,
                                        politika=_test_politikasi())
        kontrol("zaten dogru dosya yeniden indirilmez", ikinci == _SHA and len(s.istekler) == 1)


def test_kesinti_ve_surdurme():
    print("\n[K2-I5] kesinti -> .part kalir; yeniden cagrida Range ile kaldigi yerden surer")
    from cekirdek import veri_indir
    kesik = 300000
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/b.xml"] = _VERI
        s.ayar["/b.xml"] = {"kes": kesik}
        hedef = os.path.join(d, "b.xml")
        hata = _hata(veri_indir.dosya_indir, s.url("/b.xml"), hedef, len(_VERI), _SHA,
                     politika=_test_politikasi())
        kontrol("kesinti IndirmeHatasi", isinstance(hata, veri_indir.IndirmeHatasi), repr(hata))
        parca = hedef + veri_indir.PARCA_UZANTISI
        kontrol("yarim parca kaldi", os.path.getsize(parca) == kesik)
        kontrol("hedef olusmadi", not os.path.exists(hedef))
        sha = veri_indir.dosya_indir(s.url("/b.xml"), hedef, len(_VERI), _SHA,
                                     politika=_test_politikasi())
        kontrol("surdurme Range basligi", s.istekler[-1] == ("/b.xml", "bytes=%d-" % kesik),
                repr(s.istekler))
        kontrol("surdurulen dosya dogru", sha == _SHA and os.path.getsize(hedef) == len(_VERI))


def test_sha256_hatasi():
    print("\n[K2-I6] sha256 tutmazsa hedef olusmaz, bozuk parca silinir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/c.xml"] = _VERI
        hedef = os.path.join(d, "c.xml")
        hata = _hata(veri_indir.dosya_indir, s.url("/c.xml"), hedef, len(_VERI), "0" * 64,
                     politika=_test_politikasi())
        kontrol("sha256 hatasi", isinstance(hata, veri_indir.IndirmeHatasi)
                and "sha256" in str(hata), repr(hata))
        kontrol("hedef yok", not os.path.exists(hedef))
        kontrol("parca silindi", not os.path.exists(hedef + veri_indir.PARCA_UZANTISI))


def test_aralik_yok_sayilirsa_bastan():
    print("\n[K2-I7] sunucu Range'i yok sayarsa (200) parca atilir, bastan yazilir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/d.xml"] = _VERI
        s.ayar["/d.xml"] = {"aralik": False}
        hedef = os.path.join(d, "d.xml")
        with open(hedef + veri_indir.PARCA_UZANTISI, "wb") as f:
            f.write(b"\xff" * 1000)                     # yanlis icerikli eski parca
        sha = veri_indir.dosya_indir(s.url("/d.xml"), hedef, len(_VERI), _SHA,
                                     politika=_test_politikasi())
        kontrol("dogru dosya", sha == _SHA)


def test_boyut_tutmazsa_hata():
    print("\n[K2-I8] sunucunun bildirdigi boyut katalogdan farkliysa indirme yapilmaz")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/e.xml"] = _VERI
        hedef = os.path.join(d, "e.xml")
        hata = _hata(veri_indir.dosya_indir, s.url("/e.xml"), hedef, len(_VERI) - 10, None,
                     politika=_test_politikasi())
        kontrol("boyut hatasi", isinstance(hata, veri_indir.IndirmeHatasi), repr(hata))
        kontrol("hedef yok", not os.path.exists(hedef))


def test_iptal_parcayi_korur():
    print("\n[K2-I9] iptal: IptalEdildi, parca surdurme icin kalir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/f.xml"] = _VERI
        hedef = os.path.join(d, "f.xml")
        iptal = threading.Event()

        def ilerleme(alinan, toplam):
            if alinan >= veri_indir.PARCA_BOYUTU:
                iptal.set()
        hata = _hata(veri_indir.dosya_indir, s.url("/f.xml"), hedef, len(_VERI), _SHA,
                     politika=_test_politikasi(), ilerleme=ilerleme, iptal=iptal)
        kontrol("IptalEdildi", isinstance(hata, veri_indir.IptalEdildi), repr(hata))
        kontrol("parca var", os.path.exists(hedef + veri_indir.PARCA_UZANTISI))


def test_yonlendirme_politikasi():
    print("\n[K2-I10] izinsiz alan adina yonlendirme reddedilir; izinliye yonlendirme izlenir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/gercek.xml"] = _VERI
        s.ayar["/izinli"] = {"yonlendir": s.url("/gercek.xml")}
        s.ayar["/izinsiz"] = {"yonlendir": s.url("/gercek.xml", ana="localhost")}
        sha = veri_indir.dosya_indir(s.url("/izinli"), os.path.join(d, "a"), len(_VERI), _SHA,
                                     politika=_test_politikasi())
        kontrol("izinli yonlendirme", sha == _SHA)
        hata = _hata(veri_indir.dosya_indir, s.url("/izinsiz"), os.path.join(d, "b"),
                     len(_VERI), _SHA, politika=_test_politikasi())
        kontrol("izinsiz yonlendirme reddi", isinstance(hata, veri_indir.IndirmeHatasi)
                and "localhost" in str(hata), repr(hata))
        kontrol("izinsiz hedefe istek yok", not any(y == "/gercek.xml" and a is None and i > 1
                                                    for i, (y, a) in enumerate(s.istekler)))


def test_uretimde_http_reddi():
    print("\n[K2-I11] politika verilmezse (uretim) http sahte sunucu bile reddedilir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/g.xml"] = _VERI
        hata = _hata(veri_indir.dosya_indir, s.url("/g.xml"), os.path.join(d, "g"),
                     len(_VERI), _SHA)
        kontrol("reddedildi", isinstance(hata, veri_indir.IndirmeHatasi), repr(hata))
        kontrol("hic istek gitmedi", s.istekler == [])


# ---------------------------------------------------------------------------
# disk, hedef klasor, arsiv
# ---------------------------------------------------------------------------

def test_disk_alani_denetimi():
    print("\n[K2-A1] disk alani: gereken + pay yoksa hata (indirmeden once)")
    from cekirdek import veri_arsiv
    import collections
    Kullanim = collections.namedtuple("Kullanim", "total used free")
    with tempfile.TemporaryDirectory() as d:
        az = lambda _yol: Kullanim(100, 90, 10)            # noqa: E731
        hata = _hata(veri_arsiv.disk_denetle, d, 1000, kullanim=az)
        kontrol("yetersiz", isinstance(hata, veri_arsiv.ArsivHatasi), repr(hata))
        bol = lambda _yol: Kullanim(10 ** 15, 0, 10 ** 15)   # noqa: E731
        kontrol("yeterli", _hata(veri_arsiv.disk_denetle, d, 1000, kullanim=bol) is None)
        kontrol("olmayan alt dizin ust dizinden olculur",
                _hata(veri_arsiv.disk_denetle, os.path.join(d, "x", "y"), 1,
                      kullanim=bol) is None)


def test_hedef_klasor_dogrulama():
    print("\n[K2-A2] hedef klasor: mutlak, sistem dizini degil, dosya degil, yazilabilir")
    from cekirdek import veri_arsiv
    with tempfile.TemporaryDirectory() as d:
        kontrol("gecerli (yoksa olusturulur)",
                veri_arsiv.hedef_dogrula(os.path.join(d, "yeni")) == os.path.join(
                    os.path.realpath(d), "yeni"))
        for kotu in ("goreli/dizin", "/", "/usr", "/etc/openmc", "/proc/x", ""):
            kontrol("reddedildi: %r" % kotu,
                    isinstance(_hata(veri_arsiv.hedef_dogrula, kotu), veri_arsiv.ArsivHatasi))
        dosya = os.path.join(d, "dosya")
        open(dosya, "w").close()
        kontrol("dosya reddi", isinstance(_hata(veri_arsiv.hedef_dogrula, dosya),
                                          veri_arsiv.ArsivHatasi))
        kilitli = os.path.join(d, "kilitli")
        os.makedirs(kilitli)
        os.chmod(kilitli, 0o500)
        if not os.access(kilitli, os.W_OK):               # root degilse
            kontrol("yazilamaz reddi", isinstance(_hata(veri_arsiv.hedef_dogrula, kilitli),
                                                  veri_arsiv.ArsivHatasi))
        os.chmod(kilitli, 0o700)


def _tar_xz(yol, uyeler):
    """uyeler: [(ad, bytes | None (dizin) | ("symlink"|"hardlink"|"fifo", hedef))]."""
    with tarfile.open(yol, "w:xz") as tf:
        for ad, icerik in uyeler:
            bilgi = tarfile.TarInfo(ad)
            if icerik is None:
                bilgi.type = tarfile.DIRTYPE
                tf.addfile(bilgi)
            elif isinstance(icerik, tuple):
                bilgi.type = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE,
                              "fifo": tarfile.FIFOTYPE}[icerik[0]]
                bilgi.linkname = icerik[1]
                tf.addfile(bilgi)
            else:
                bilgi.size = len(icerik)
                tf.addfile(bilgi, io.BytesIO(icerik))
    return yol


_XS = b"<cross_sections><library materials='H1' path='neutron/H1.h5' type='neutron'/></cross_sections>"


def test_arsiv_guvenli_acma():
    print("\n[K2-A3] guvenli acma: alt dizindeki cross_sections.xml hedef ada tasinir")
    from cekirdek import veri_arsiv
    with tempfile.TemporaryDirectory() as d:
        arsiv = _tar_xz(os.path.join(d, "k.tar.xz"), [
            ("endfb-viii.0-hdf5", None), ("endfb-viii.0-hdf5/cross_sections.xml", _XS),
            ("endfb-viii.0-hdf5/neutron/H1.h5", b"h5")])
        hedef = os.path.join(d, "veri")
        os.makedirs(hedef)
        xml = veri_arsiv.arsiv_ac(arsiv, hedef, "kutup", en_cok_bayt=10 ** 6)
        kontrol("xml hedefte", xml == os.path.join(hedef, "kutup", "cross_sections.xml"), xml)
        kontrol("alt dosya", os.path.isfile(os.path.join(hedef, "kutup", "neutron", "H1.h5")))
        kontrol("gecici dizin kalmadi",
                sorted(os.listdir(hedef)) == ["kutup"], repr(os.listdir(hedef)))
        hata = _hata(veri_arsiv.arsiv_ac, arsiv, hedef, "kutup", en_cok_bayt=10 ** 6)
        kontrol("var olan hedef ezilmez", isinstance(hata, veri_arsiv.ArsivHatasi))


def test_arsiv_kotu_uyeler():
    print("\n[K2-A4] yol gecisi, mutlak yol, symlink, hardlink, fifo, zip bombasi reddedilir")
    from cekirdek import veri_arsiv
    kotuler = {
        "yol gecisi": [("a/../../kacak.txt", b"x")],
        "mutlak yol": [("/tmp/k2_kacak_mutlak.txt", b"x")],
        "symlink": [("a/cross_sections.xml", ("symlink", "/etc/passwd"))],
        "hardlink": [("a/h", ("hardlink", "/etc/passwd"))],
        "fifo": [("a/f", ("fifo", ""))],
        "bomba": [("a/cross_sections.xml", _XS), ("a/buyuk.h5", b"0" * 5000)],
        "xml yok": [("a/b.h5", b"x")],
    }
    for ad, uyeler in kotuler.items():
        with tempfile.TemporaryDirectory() as d:
            arsiv = _tar_xz(os.path.join(d, "k.tar.xz"), uyeler)
            hedef = os.path.join(d, "veri")
            os.makedirs(hedef)
            hata = _hata(veri_arsiv.arsiv_ac, arsiv, hedef, "kutup", en_cok_bayt=1000)
            kontrol("%s reddi" % ad, isinstance(hata, veri_arsiv.ArsivHatasi), repr(hata))
            kontrol("%s: hedefte iz kalmadi" % ad, os.listdir(hedef) == [],
                    repr(os.listdir(hedef)))
            kontrol("%s: disari yazilmadi" % ad, not os.path.exists(
                os.path.join(d, "kacak.txt")) and not os.path.exists("/tmp/k2_kacak_mutlak.txt"))


def test_arsiv_uye_sayisi_siniri():
    print("\n[K2-A5] uye sayisi siniri asilirsa reddedilir")
    from cekirdek import veri_arsiv
    with tempfile.TemporaryDirectory() as d:
        arsiv = _tar_xz(os.path.join(d, "k.tar.xz"),
                        [("a/%d" % i, b"") for i in range(5)])
        hedef = os.path.join(d, "veri")
        os.makedirs(hedef)
        hata = _hata(veri_arsiv.arsiv_ac, arsiv, hedef, "kutup", en_cok_bayt=10 ** 6,
                     en_cok_uye=3)
        kontrol("uye siniri", isinstance(hata, veri_arsiv.ArsivHatasi), repr(hata))


# ---------------------------------------------------------------------------
# uctan uca kurulum
# ---------------------------------------------------------------------------

def _oge(veri_indir, url, bayt, sha=None, tur="kutuphane", kimlik="sahte", dosya_adi=None):
    return veri_indir.Oge(kimlik=kimlik, ad="Sahte", tur=tur, url=url, bayt=bayt, sha256=sha,
                          dizin_adi="sahte-hdf5", dosya_adi=dosya_adi, acik_bayt=None)


def test_kutuphane_kur_uctan_uca():
    print("\n[K2-K1] kutuphane_kur: indir + ac + makbuz + arsiv silinir; ikinci cagri atlar")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        arsiv = _tar_xz(os.path.join(d, "kaynak.tar.xz"), [
            ("lib/cross_sections.xml", _XS), ("lib/neutron/H1.h5", b"h5")])
        with open(arsiv, "rb") as f:
            veri = f.read()
        s.dosyalar["/lib.xz"] = veri
        hedef = os.path.join(d, "nucdata")
        oge = _oge(veri_indir, s.url("/lib.xz"), len(veri))
        asamalar = []
        sonuc = veri_indir.kutuphane_kur(oge, hedef, oran=4.0, politika=_test_politikasi(),
                                         ilerleme=lambda a, x, t: asamalar.append(a))
        kontrol("xml yolu", sonuc.yol == os.path.join(hedef, "sahte-hdf5", "cross_sections.xml"))
        kontrol("sha256 hesaplandi", sonuc.sha256 == hashlib.sha256(veri).hexdigest())
        with open(os.path.join(hedef, "sahte-hdf5", veri_indir.MAKBUZ), encoding="utf-8") as f:
            makbuz = json.load(f)
        kontrol("makbuz url + sha", makbuz["url"] == oge.url and makbuz["sha256"] == sonuc.sha256)
        kontrol("indirme dizini bos", os.listdir(os.path.join(hedef, veri_indir.INDIRME_DIZINI))
                == [])
        kontrol("asamalar", "indirme" in asamalar and "acma" in asamalar, repr(set(asamalar)))
        istek = len(s.istekler)
        ikinci = veri_indir.kutuphane_kur(oge, hedef, oran=4.0, politika=_test_politikasi())
        kontrol("kurulu kutuphane yeniden indirilmez", ikinci.atlandi
                and len(s.istekler) == istek)


def test_zincir_kur():
    print("\n[K2-K2] zincir_kur: <hedef>/chain/<dosya_adi>, sha256 dogrulanir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/z.xml"] = _VERI
        oge = _oge(veri_indir, s.url("/z.xml"), len(_VERI), _SHA, tur="zincir",
                   dosya_adi="chain_endfb80_thermal.xml")
        sonuc = veri_indir.zincir_kur(oge, d, politika=_test_politikasi())
        kontrol("chain dizininde", sonuc.yol == os.path.join(
            os.path.realpath(d), "chain", "chain_endfb80_thermal.xml"), sonuc.yol)


def test_komut_satiri_liste_ve_betik():
    print("\n[K2-K3] python -m cekirdek.veri_indir --liste; veri_indir.sh modulu cagirir")
    r = subprocess.run([sys.executable, "-m", "cekirdek.veri_indir", "--liste"], cwd=KOK,
                       capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, PYTHONPATH=KOK))
    kontrol("cikis 0", r.returncode == 0, r.stderr[-300:])
    kontrol("kutuphaneler listelendi", "endfb-viii.0" in r.stdout and "jendl-5" in r.stdout)
    kontrol("zincirler listelendi", "casl-termal" in r.stdout)
    with open(os.path.join(KOK, "veri_indir.sh"), encoding="utf-8") as f:
        betik = f.read()
    kontrol("betik module yonlendirir", "-m cekirdek.veri_indir" in betik)
    kontrol("betikte curl kalmadi", "curl " not in betik)
    r = subprocess.run(["bash", os.path.join(KOK, "veri_indir.sh"), "--liste"], cwd=KOK,
                       capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, PYTHON=sys.executable))
    kontrol("betik --liste", r.returncode == 0 and "endfb-viii.0" in r.stdout, r.stderr[-300:])


def test_komut_satiri_hatali_secim():
    print("\n[K2-K4] bilinmeyen kutuphane kimligi -> cikis 2, ag istegi yok")
    from cekirdek import veri_indir
    kod = veri_indir.main(["--kutuphane", "yok-boyle-bir-sey", "--hedef", tempfile.gettempdir()])
    kontrol("cikis 2", kod == 2)


def test_komut_satiri_uctan_uca():
    print("\n[K2-K5] main(): sahte katalogla zincir + kutuphane, ayar yazilir, --bashrc eklenir")
    from cekirdek import veri_indir, veri_yolu
    eski = {k: os.environ.get(k) for k in ("HOME", "XDG_CONFIG_HOME")}
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        try:
            os.environ.update(HOME=d, XDG_CONFIG_HOME=os.path.join(d, "cfg"))
            arsiv = _tar_xz(os.path.join(d, "a.tar.xz"), [("x/cross_sections.xml", _XS)])
            with open(arsiv, "rb") as f:
                veri = f.read()
            s.dosyalar.update({"/k.xz": veri, "/z.xml": _VERI})
            kutup = _oge(veri_indir, s.url("/k.xz"), len(veri))
            zincir = veri_indir.Oge(kimlik="z", ad="Z termal", tur="zincir", url=s.url("/z.xml"),
                                    bayt=len(_VERI), sha256=_SHA, kutuphane="sahte",
                                    spektrum="termal", dosya_adi="chain_endfb80_thermal.xml",
                                    uygulamada_kullanilir=True)
            kat = veri_indir.Katalog((kutup,), (zincir,), frozenset({"127.0.0.1"}), 4.0, "t",
                                     {"sayfa": "https://openmc.org/data/"})
            hedef = os.path.join(d, "nucdata")
            kod = veri_indir.main(["--hedef", hedef, "--kutuphane", "sahte", "--bashrc"],
                                  katalog=kat, politika=_test_politikasi())
            kontrol("cikis 0", kod == 0)
            ayar = veri_yolu.ayar_oku()
            kontrol("ayar kutuphane", ayar.get("cross_sections") == os.path.join(
                hedef, "sahte-hdf5", "cross_sections.xml"), repr(ayar))
            kontrol("ayar zincir", ayar.get("zincir") == os.path.join(
                hedef, "chain", "chain_endfb80_thermal.xml"))
            with open(os.path.join(d, ".bashrc"), encoding="utf-8") as f:
                kontrol("bashrc satirlari", "OPENMC_CROSS_SECTIONS" in f.read())
            kod = veri_indir.main(["--hedef", hedef, "--kutuphane", "sahte", "--bashrc"],
                                  katalog=kat, politika=_test_politikasi())
            with open(os.path.join(d, ".bashrc"), encoding="utf-8") as f:
                kontrol("bashrc ikinci kez eklenmez", f.read().count("openmc_arayuz") == 1)
            kontrol("bilinmeyen zincir cikis 2", veri_indir.main(
                ["--hedef", hedef, "--zincir", "yok"], katalog=kat) == 2)
            kontrol("uretim politikasiyla http reddi cikis 1", veri_indir.main(
                ["--hedef", os.path.join(d, "b"), "--yalniz-zincir"], katalog=kat) == 1)
        finally:
            for k, v in eski.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def test_katalog_paket_verisinde():
    print("\n[K2-K6] pyproject package-data katalogu kapsar (kurulu pakette de bulunur)")
    import tomllib
    with open(os.path.join(KOK, "pyproject.toml"), "rb") as f:
        paket = tomllib.load(f)["tool"]["setuptools"]["package-data"]
    kontrol("cekirdek veri_katalogu.json", "veri_katalogu.json" in paket.get("cekirdek", []))


HIZLI = [test_katalog_kaynakli_ve_gecerli, test_katalog_gecersiz_reddedilir, test_url_politikasi,
         test_tam_indirme_atomik, test_kesinti_ve_surdurme, test_sha256_hatasi,
         test_aralik_yok_sayilirsa_bastan, test_boyut_tutmazsa_hata, test_iptal_parcayi_korur,
         test_yonlendirme_politikasi, test_uretimde_http_reddi, test_disk_alani_denetimi,
         test_hedef_klasor_dogrulama, test_arsiv_guvenli_acma, test_arsiv_kotu_uyeler,
         test_arsiv_uye_sayisi_siniri, test_kutuphane_kur_uctan_uca, test_zincir_kur,
         test_komut_satiri_liste_ve_betik, test_komut_satiri_hatali_secim,
         test_komut_satiri_uctan_uca, test_katalog_paket_verisinde]
YAVAS = []
