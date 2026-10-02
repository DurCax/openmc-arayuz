# -*- coding: utf-8 -*-
"""
 test_k2_veri_yolu.py  --  v3 K2: tek nukleer veri cozumleyicisi
                           (cekirdek/veri_yolu.py: ortam -> ayar -> aday)

 Her test kendi gecici HOME / XDG dizinlerini `ortam=` ile verir: gercek
 ~/nucdata ve kullanici ayarlari okunmaz, yazilmaz.
"""

import json
import os
import tempfile

from testler.ortak_test import kontrol
from testler.k2_yalitim import VeriYalitimi

_ZINCIR = "chain_endfb80_thermal.xml"


def _ortam(kok):
    """Gecici ev dizini ve XDG dizinleri; OPENMC_* yok."""
    return {"HOME": kok, "XDG_CONFIG_HOME": os.path.join(kok, "cfg"),
            "XDG_DATA_HOME": os.path.join(kok, "data")}


def _kutuphane(dizin):
    """En kucuk gecerli cross_sections.xml (bir notron kaydi) yazar."""
    os.makedirs(os.path.join(dizin, "neutron"), exist_ok=True)
    yol = os.path.join(dizin, "cross_sections.xml")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0'?>\n<cross_sections>\n"
                "  <library materials=\"H1\" path=\"neutron/H1.h5\" type=\"neutron\"/>\n"
                "</cross_sections>\n")
    open(os.path.join(dizin, "neutron", "H1.h5"), "w").close()
    return yol


def _zincir(dizin, ad=_ZINCIR):
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write("<depletion_chain>\n</depletion_chain>\n")
    return yol


def test_ortam_degiskeni_once_gelir():
    print("\n[K2-Y1] OPENMC_CROSS_SECTIONS verilmisse ayar ve aday okunmaz (gecersiz olsa da)")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        # Arrange
        ortam = _ortam(kok)
        aday = _kutuphane(os.path.join(kok, "nucdata", "endfb-viii.0-hdf5"))
        ortam["OPENMC_CROSS_SECTIONS"] = os.path.join(kok, "yok", "cross_sections.xml")
        # Act
        sonuc = veri_yolu.cross_sections(ortam)
        # Assert
        kontrol("kaynak ortam", sonuc.kaynak == "ortam", sonuc.kaynak)
        kontrol("deger ortamdaki", sonuc.deger == ortam["OPENMC_CROSS_SECTIONS"], sonuc.deger)
        kontrol("dosya yok -> gecersiz", not sonuc.gecerli)
        kontrol("aday secilmedi", sonuc.deger != aday)
        kontrol("hazir degil", not veri_yolu.veri_hazir_mi(ortam))


def test_ayar_sonra_aday():
    print("\n[K2-Y2] ortam bossa kayitli ayar, o da yoksa ~/nucdata adayi")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        ortam = _ortam(kok)
        aday = _kutuphane(os.path.join(kok, "nucdata", "endfb-viii.0-hdf5"))
        secilen = _kutuphane(os.path.join(kok, "baska", "jeff33"))
        ilk = veri_yolu.cross_sections(ortam)
        kontrol("aday bulundu", ilk.kaynak == "aday" and ilk.deger == aday, repr(ilk))
        kontrol("aday gecerli", ilk.gecerli and veri_yolu.veri_hazir_mi(ortam))
        veri_yolu.ayar_yaz({"cross_sections": secilen}, ortam)
        ikinci = veri_yolu.cross_sections(ortam)
        kontrol("ayar adaydan once", ikinci.kaynak == "ayar" and ikinci.deger == secilen,
                repr(ikinci))
        ortam["OPENMC_CROSS_SECTIONS"] = ""
        kontrol("bos ortam degiskeni yok sayilir",
                veri_yolu.cross_sections(ortam).kaynak == "ayar")


def test_hicbiri_yoksa_yok():
    print("\n[K2-Y3] veri hicbir yerde yoksa kaynak 'yok', deger None")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        sonuc = veri_yolu.cross_sections(_ortam(kok))
        kontrol("yok", sonuc.kaynak == "yok" and sonuc.deger is None and not sonuc.gecerli,
                repr(sonuc))


def test_ayar_dosyasi_kalici_ve_bozuga_dayanikli():
    print("\n[K2-Y4] ayar JSON'u kalici, atomik; bozuk dosya cokertmez; goreli yol reddedilir")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        ortam = _ortam(kok)
        xs = _kutuphane(os.path.join(kok, "k"))
        yol = veri_yolu.ayar_yaz({"cross_sections": xs}, ortam)
        kontrol("ayar dizininde", yol.startswith(ortam["XDG_CONFIG_HOME"]), yol)
        kontrol("okunur", veri_yolu.ayar_oku(ortam).get("cross_sections") == xs)
        kontrol("gecici dosya kalmadi",
                [a for a in os.listdir(os.path.dirname(yol)) if a.endswith(".tmp")] == [])
        veri_yolu.ayar_yaz({"zincir": _zincir(os.path.join(kok, "z"))}, ortam)
        kontrol("guncelleme eski anahtari korur",
                veri_yolu.ayar_oku(ortam).get("cross_sections") == xs)
        with open(yol, "w") as f:
            f.write("{bozuk")
        kontrol("bozuk JSON -> bos ayar", veri_yolu.ayar_oku(ortam) == {})
        hata = None
        try:
            veri_yolu.ayar_yaz({"cross_sections": "goreli/cross_sections.xml"}, ortam)
        except ValueError as e:
            hata = e
        kontrol("goreli yol ValueError", hata is not None)
        hata = None
        try:
            veri_yolu.ayar_yaz({"bilinmeyen": "/x"}, ortam)
        except ValueError as e:
            hata = e
        kontrol("bilinmeyen anahtar ValueError", hata is not None)


def test_zincir_cozumu():
    print("\n[K2-Y5] zincir: ortam > ayar > kutuphanenin yanindaki chain/ > ~/nucdata/chain")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        ortam = _ortam(kok)
        yok = veri_yolu.zincir(ortam)
        kontrol("zincir yok", yok.kaynak == "yok" and yok.deger is None, repr(yok))
        kontrol("zincir dizini eski varsayilan",
                veri_yolu.zincir_dizini(ortam) == os.path.join(kok, "nucdata", "chain"))
        ev = _zincir(os.path.join(kok, "nucdata", "chain"))
        kontrol("ev adayi", veri_yolu.zincir(ortam).deger == ev)
        kutup = os.path.join(kok, "veri")
        veri_yolu.ayar_yaz({"cross_sections": _kutuphane(os.path.join(kutup, "endfb"))}, ortam)
        yan = _zincir(os.path.join(kutup, "chain"))
        kontrol("kutuphanenin yanindaki chain/", veri_yolu.zincir(ortam).deger == yan,
                veri_yolu.zincir(ortam).deger)
        ayarli = _zincir(os.path.join(kok, "ozel"))
        veri_yolu.ayar_yaz({"zincir": ayarli}, ortam)
        kontrol("ayar", veri_yolu.zincir(ortam).kaynak == "ayar")
        ortam["OPENMC_CHAIN_FILE"] = os.path.join(kok, "yok.xml")
        z = veri_yolu.zincir(ortam)
        kontrol("ortam (gecersiz) once", z.kaynak == "ortam" and not z.gecerli)
        kontrol("zincir dizini ortamdan", veri_yolu.zincir_dizini(ortam) == kok)


def test_alt_surec_ortami_yeni_sozluk():
    print("\n[K2-Y6] alt surec ortami: cozulen yollar yazilir, girdi degismez")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        ortam = _ortam(kok)
        xs = _kutuphane(os.path.join(kok, "nucdata", "endfb-viii.0-hdf5"))
        z = _zincir(os.path.join(kok, "nucdata", "chain"))
        once = dict(ortam)
        yeni = veri_yolu.alt_surec_ortami(ortam)
        kontrol("girdi degismedi", ortam == once)
        kontrol("yeni nesne", yeni is not ortam)
        kontrol("XS yazildi", yeni.get("OPENMC_CROSS_SECTIONS") == xs)
        kontrol("zincir yazildi", yeni.get("OPENMC_CHAIN_FILE") == z)
        kontrol("diger degiskenler korundu", yeni["HOME"] == kok)
    with tempfile.TemporaryDirectory() as kok:
        yeni = veri_yolu.alt_surec_ortami(_ortam(kok))
        kontrol("veri yoksa degisken eklenmez", "OPENMC_CROSS_SECTIONS" not in yeni)


def test_surece_uygula():
    print("\n[K2-Y7] surece_uygula: os.environ ve (yukluyse) openmc.config guncellenir")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        ortam = _ortam(kok)
        xs = _kutuphane(os.path.join(kok, "nucdata", "x"))
        hedef = {}
        degisen = veri_yolu.surece_uygula(ortam=ortam, hedef=hedef)
        kontrol("hedefe yazildi", hedef.get("OPENMC_CROSS_SECTIONS") == xs, repr(hedef))
        kontrol("degisen anahtarlar", "OPENMC_CROSS_SECTIONS" in degisen, repr(degisen))


def test_surece_uygulanan_sonraki_secimi_engellemez():
    print("\n[K2-Y7b] os.environ'a bizim yazdigimiz deger 'kullanici ortami' sayilmaz")
    from cekirdek import veri_yolu
    with VeriYalitimi() as y:
        kok = y.kok
        ilk = _kutuphane(os.path.join(kok, "nucdata", "a"))
        veri_yolu.surece_uygula()
        kontrol("ilk secim ortamda", os.environ.get("OPENMC_CROSS_SECTIONS") == ilk)
        ikinci = _kutuphane(os.path.join(kok, "b"))
        veri_yolu.ayar_yaz({"cross_sections": ikinci})
        kontrol("yeni ayar ortamdaki enjekte degerden once",
                veri_yolu.cross_sections().deger == ikinci)
        veri_yolu.surece_uygula()
        kontrol("ortam yeni secime gecti", os.environ.get("OPENMC_CROSS_SECTIONS") == ikinci)
        os.remove(ikinci)
        veri_yolu.ayar_yaz({"cross_sections": None})
        os.remove(ilk)
        veri_yolu.surece_uygula()
        kontrol("cozulmeyen enjekte deger kaldirildi",
                "OPENMC_CROSS_SECTIONS" not in os.environ)
    kontrol("yalitim openmc.config'i geri getirdi",
            _config_xs() == _ONCEKI_CONFIG_XS or _ONCEKI_CONFIG_XS is _YOK_ISARETI,
            repr(_config_xs()))


_YOK_ISARETI = object()


def _config_xs():
    import sys
    if "openmc" not in sys.modules:
        return _YOK_ISARETI
    import openmc
    return openmc.config.get("cross_sections")


_ONCEKI_CONFIG_XS = _config_xs()


def test_surece_uygula_openmc_config():
    print("\n[K2-Y7c] openmc yukluyse surece_uygula openmc.config'i yazar, kaldirinca siler")
    import openmc
    from cekirdek import veri_yolu
    with VeriYalitimi() as y:
        xs = _kutuphane(os.path.join(y.kok, "nucdata", "a"))
        veri_yolu.surece_uygula()
        kontrol("config yazildi", str(openmc.config.get("cross_sections")) == xs)
        os.remove(xs)
        veri_yolu.surece_uygula()
        kontrol("config silindi", "cross_sections" not in openmc.config)


def test_varsayilan_zincir_adi_tukenmeyle_ayni():
    print("\n[K2-Y9] VARSAYILAN_ZINCIR = tukenme.ZINCIRLER['termal']")
    from cekirdek import tukenme, veri_yolu
    kontrol("ayni ad", veri_yolu.VARSAYILAN_ZINCIR == tukenme.ZINCIRLER["termal"])


def test_ayar_dosyasi_json_bicimi():
    print("\n[K2-Y8] ayar dosyasi okunur JSON (surum + anahtarlar)")
    from cekirdek import veri_yolu
    with tempfile.TemporaryDirectory() as kok:
        ortam = _ortam(kok)
        xs = _kutuphane(os.path.join(kok, "k"))
        yol = veri_yolu.ayar_yaz({"cross_sections": xs, "kutuphane": "endfb-viii.0"}, ortam)
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        kontrol("surum alani", veri.get("surum") == veri_yolu.AYAR_SURUMU, repr(veri))
        kontrol("kutuphane kimligi", veri.get("kutuphane") == "endfb-viii.0")


HIZLI = [test_ortam_degiskeni_once_gelir, test_ayar_sonra_aday, test_hicbiri_yoksa_yok,
         test_ayar_dosyasi_kalici_ve_bozuga_dayanikli, test_zincir_cozumu,
         test_alt_surec_ortami_yeni_sozluk, test_surece_uygula,
         test_surece_uygulanan_sonraki_secimi_engellemez, test_surece_uygula_openmc_config,
         test_ayar_dosyasi_json_bicimi,
         test_varsayilan_zincir_adi_tukenmeyle_ayni]
YAVAS = []
