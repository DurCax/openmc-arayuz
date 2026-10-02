# -*- coding: utf-8 -*-
"""
 test_k2_guvenlik.py  --  v3 K2 inceleme bulgulari: indirici ve arsiv acmanin
                          sertlestirilmesi (agsiz sahte sunucu)

 sha256 dogrulama bayragi, bozuk arsiv dongusu, symlink / izin denetimleri,
 bozuk basliklar, Content-Encoding, hedef klasor kurallari, katalog adlari,
 karma hesabinda iptal, artik .aciliyor-* temizligi, komut satiri hatalari.
"""

import hashlib
import io
import json
import os
import stat
import tarfile
import tempfile
import threading

from testler.ortak_test import kontrol, KOK
from testler.k2_sahte_sunucu import SahteSunucu

_VERI = bytes(range(256)) * 2048
_SHA = hashlib.sha256(_VERI).hexdigest()
_XS = b"<cross_sections><library materials='H1' path='n/H1.h5' type='neutron'/></cross_sections>"


def _politika():
    from cekirdek import veri_indir
    return veri_indir.UrlPolitikasi(semalar=frozenset({"http"}),
                                    alanlar=frozenset({"127.0.0.1"}), port_serbest=True)


def _hata(islev, *a, **kw):
    try:
        islev(*a, **kw)
    except Exception as e:                     # noqa: BLE001 -- test yardimcisi
        return e
    return None


def _tar(uyeler):
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode="w:xz") as tf:
        for ad, icerik in uyeler:
            bilgi = tarfile.TarInfo(ad)
            bilgi.size = len(icerik)
            tf.addfile(bilgi, io.BytesIO(icerik))
    return tampon.getvalue()


def _oge(veri_indir, url, bayt, sha=None, tur="kutuphane"):
    return veri_indir.Oge(kimlik="sahte", ad="Sahte", tur=tur, url=url, bayt=bayt, sha256=sha,
                          dizin_adi="sahte-hdf5", dosya_adi="chain_x.xml", acik_bayt=10 ** 6)


def test_sha256_dogrulama_bayragi():
    print("\n[K2-G1] Kurulum.dogrulandi ve makbuz sha256_dogrulandi: sha256 yoksa False")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        arsiv = _tar([("k/cross_sections.xml", _XS)])
        s.dosyalar.update({"/k.xz": arsiv, "/z.xml": _VERI})
        k = veri_indir.kutuphane_kur(_oge(veri_indir, s.url("/k.xz"), len(arsiv)), d, 4.0,
                                     politika=_politika())
        kontrol("kutuphane: dogrulanmadi", k.dogrulandi is False)
        with open(os.path.join(d, "sahte-hdf5", veri_indir.MAKBUZ), encoding="utf-8") as f:
            kontrol("makbuz bayragi", json.load(f).get("sha256_dogrulandi") is False)
        z = veri_indir.zincir_kur(_oge(veri_indir, s.url("/z.xml"), len(_VERI), _SHA, "zincir"),
                                  d, politika=_politika())
        kontrol("zincir: dogrulandi", z.dogrulandi is True)
        kontrol("etiket metni", "sha256" in veri_indir.dogrulama_etiketi(k)
                and veri_indir.dogrulama_etiketi(z) == "")


def test_bozuk_arsiv_silinir():
    print("\n[K2-G2] bozuk arsiv: hata + arsiv silinir (yeniden denemede bastan indirilir)")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        bozuk = b"\xfd7zXZ\x00" + b"bozuk" * 1000
        s.dosyalar["/k.xz"] = bozuk
        hata = _hata(veri_indir.kutuphane_kur, _oge(veri_indir, s.url("/k.xz"), len(bozuk)),
                     d, 4.0, politika=_politika())
        kontrol("hata", isinstance(hata, veri_indir.VeriHatasi) and "silindi" in str(hata),
                repr(hata))
        kontrol("arsiv silindi", os.listdir(os.path.join(d, veri_indir.INDIRME_DIZINI)) == [])


def test_symlink_reddi():
    print("\n[K2-G3] hedef / .part / .indirilen symlink ise reddedilir; .indirilen 0700")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/z.xml"] = _VERI
        baska = os.path.join(d, "baska")
        open(baska, "wb").close()
        hedef = os.path.join(d, "a.xml")
        os.symlink(baska, hedef + veri_indir.PARCA_UZANTISI)
        hata = _hata(veri_indir.dosya_indir, s.url("/z.xml"), hedef, len(_VERI), _SHA,
                     politika=_politika())
        kontrol(".part symlink reddi", isinstance(hata, veri_indir.IndirmeHatasi), repr(hata))
        kontrol("hedefe yazilmadi", os.path.getsize(baska) == 0)
        hedef2 = os.path.join(d, "b.xml")
        os.symlink(baska, hedef2)
        hata = _hata(veri_indir.dosya_indir, s.url("/z.xml"), hedef2, len(_VERI), None,
                     politika=_politika())
        kontrol("hedef symlink reddi", isinstance(hata, veri_indir.IndirmeHatasi), repr(hata))
        kok = os.path.join(d, "kok")
        os.makedirs(kok)
        os.symlink(d, os.path.join(kok, veri_indir.INDIRME_DIZINI))
        arsiv = _tar([("k/cross_sections.xml", _XS)])
        s.dosyalar["/k.xz"] = arsiv
        hata = _hata(veri_indir.kutuphane_kur, _oge(veri_indir, s.url("/k.xz"), len(arsiv)),
                     kok, 4.0, politika=_politika())
        kontrol(".indirilen symlink reddi", isinstance(hata, veri_indir.VeriHatasi), repr(hata))
        kok2 = os.path.join(d, "kok2")
        veri_indir.kutuphane_kur(_oge(veri_indir, s.url("/k.xz"), len(arsiv)), kok2, 4.0,
                                 politika=_politika())
        mod = stat.S_IMODE(os.stat(os.path.join(kok2, veri_indir.INDIRME_DIZINI)).st_mode)
        kontrol(".indirilen 0700", mod == 0o700, oct(mod))
        mod = stat.S_IMODE(os.stat(os.path.join(kok2, "sahte-hdf5")).st_mode)
        kontrol("kutuphane dizini 0755", mod == 0o755, oct(mod))


def test_bozuk_basliklar():
    print("\n[K2-G4] bozuk Content-Length, Content-Encoding -> IndirmeHatasi")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar.update({"/a": _VERI, "/b": _VERI})
        s.ayar["/a"] = {"uzunluk": "abc"}
        s.ayar["/b"] = {"kodlama": "gzip"}
        for yol in ("/a", "/b"):
            hata = _hata(veri_indir.dosya_indir, s.url(yol), os.path.join(d, yol[1:]),
                         len(_VERI), None, politika=_politika())
            kontrol("reddedildi %s" % yol, isinstance(hata, veri_indir.IndirmeHatasi), repr(hata))


def test_hedef_klasor_kurallari():
    print("\n[K2-G5] baskasinin yazabildigi, ~/.ssh, ~/.gnupg, ev koku hedef olamaz")
    from cekirdek import veri_arsiv
    with tempfile.TemporaryDirectory() as d:
        acik = os.path.join(d, "acik")
        os.makedirs(acik)
        os.chmod(acik, 0o777)
        kontrol("o+w reddi", isinstance(_hata(veri_arsiv.hedef_dogrula, acik),
                                        veri_arsiv.ArsivHatasi))
        eski = os.environ.get("HOME")
        os.environ["HOME"] = d
        try:
            for kotu in (d, os.path.join(d, ".ssh"), os.path.join(d, ".gnupg", "x")):
                kontrol("reddi %s" % os.path.relpath(kotu, d),
                        isinstance(_hata(veri_arsiv.hedef_dogrula, kotu), veri_arsiv.ArsivHatasi))
            kontrol("ev alti serbest", _hata(veri_arsiv.hedef_dogrula,
                                             os.path.join(d, "nucdata")) is None)
        finally:
            os.environ["HOME"] = eski


def test_katalog_ad_ve_baglanti_kurallari():
    print("\n[K2-G6] katalog: dizin/dosya adi deseni; degerlendirme sayfasi https + izinli")
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
    kontrol("bosluklu ad", isinstance(bozuk(lambda v: v["zincirler"][0].update(
        dosya_adi="a b.xml")), ValueError))
    kontrol("http degerlendirme", isinstance(bozuk(lambda v: v["kutuphaneler"][0].update(
        degerlendirme_sayfasi="http://www.nndc.bnl.gov/")), ValueError))
    kontrol("izinsiz degerlendirme alani", isinstance(bozuk(lambda v: v["kutuphaneler"][0].update(
        degerlendirme_sayfasi="https://kotu.example.com/")), ValueError))


def test_karma_hesabinda_iptal():
    print("\n[K2-G7] surdurmede var olan parcanin karmasi hesaplanirken iptal dinlenir")
    from cekirdek import veri_indir
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/z"] = _VERI
        hedef = os.path.join(d, "z")
        with open(hedef + veri_indir.PARCA_UZANTISI, "wb") as f:
            f.write(_VERI[:len(_VERI) // 2])
        iptal = threading.Event()
        iptal.set()
        hata = _hata(veri_indir.dosya_indir, s.url("/z"), hedef, len(_VERI), _SHA,
                     politika=_politika(), iptal=iptal)
        kontrol("IptalEdildi", isinstance(hata, veri_indir.IptalEdildi), repr(hata))
        kontrol("ag istegi yok", s.istekler == [])


def test_artik_acma_dizini_temizlenir():
    print("\n[K2-G8] onceki yarim acmadan kalan .aciliyor-* dizini temizlenir")
    from cekirdek import veri_arsiv
    with tempfile.TemporaryDirectory() as d:
        artik = os.path.join(d, ".aciliyor-eski")
        os.makedirs(os.path.join(artik, "x"))
        arsiv = os.path.join(d, "a.tar.xz")
        with open(arsiv, "wb") as f:
            f.write(_tar([("k/cross_sections.xml", _XS)]))
        veri_arsiv.arsiv_ac(arsiv, d, "kutup", en_cok_bayt=10 ** 6)
        kontrol("artik silindi", not os.path.exists(artik), repr(os.listdir(d)))


def test_komut_satiri_hatalari_ve_bashrc_tirnak():
    print("\n[K2-G9] ayar yazilamazsa cikis 1; --bashrc satiri shlex ile tirnaklanir")
    from cekirdek import veri_indir, veri_indir_komut, veri_yolu
    satirlar = veri_indir_komut.disa_aktarma_satirlari("/a b/x.xml", "/c'd/z.xml")
    kontrol("tirnakli", satirlar == ["export OPENMC_CROSS_SECTIONS='/a b/x.xml'",
                                     "export OPENMC_CHAIN_FILE='/c'\"'\"'d/z.xml'"], repr(satirlar))
    with SahteSunucu() as s, tempfile.TemporaryDirectory() as d:
        s.dosyalar["/z.xml"] = _VERI
        z = veri_indir.Oge(kimlik="z", ad="Z termal", tur="zincir", url=s.url("/z.xml"),
                           bayt=len(_VERI), sha256=_SHA, kutuphane="x", spektrum="termal",
                           dosya_adi="chain_endfb80_thermal.xml", uygulamada_kullanilir=True)
        kat = veri_indir.Katalog((), (z,), frozenset({"127.0.0.1"}), 4.0, "t", {})
        eski = veri_yolu.ayar_yaz

        def bozuk_yaz(*a, **k):
            raise OSError("salt okunur")
        veri_yolu.ayar_yaz = bozuk_yaz
        try:
            kod = veri_indir.main(["--hedef", os.path.join(d, "n"), "--yalniz-zincir"],
                                  katalog=kat, politika=_politika())
        finally:
            veri_yolu.ayar_yaz = eski
        kontrol("cikis 1", kod == 1)


def test_dosya_boyu():
    print("\n[K2-G10] K2 kaynak dosyalari < 800 satir")
    for yol in ("cekirdek/veri_indir.py", "cekirdek/veri_indir_komut.py", "cekirdek/veri_arsiv.py",
                "cekirdek/veri_bilgi.py", "cekirdek/veri_yolu.py"):
        with open(os.path.join(KOK, yol), encoding="utf-8") as f:
            n = sum(1 for _ in f)
        kontrol("%s %d" % (yol, n), n < 800)


HIZLI = [test_sha256_dogrulama_bayragi, test_bozuk_arsiv_silinir, test_symlink_reddi,
         test_bozuk_basliklar, test_hedef_klasor_kurallari, test_katalog_ad_ve_baglanti_kurallari,
         test_karma_hesabinda_iptal, test_artik_acma_dizini_temizlenir,
         test_komut_satiri_hatalari_ve_bashrc_tirnak, test_dosya_boyu]
YAVAS = []
