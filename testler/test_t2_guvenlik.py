# -*- coding: utf-8 -*-
"""
 test_t2_guvenlik.py  --  v3 T2 inceleme bulgulari: alt surec PYTHONPATH'i,
                          giris.gui cikis kodu, kilavuz derleyicisinin kurulu
                          pakette kurulum onekine yazmamasi, SOZLUK.md korumasi

 (yol cozumu ve openmc ikilisi testleri: test_t2_yollar.py)
"""

import os

from testler.ortak_test import kontrol, KOK


def test_alt_surec_pythonpath():
    print("\n[T2G-1] alt surec PYTHONPATH: mevcut ezilmez, kurulu pakette eklenmez")
    from cekirdek import giris, yollar
    kok = yollar.paket_koku()
    kontrol("kaynak agaci, bos -> paket koku",
            giris.alt_surec_pythonpath("", kaynak_agaci=True) == kok)
    kontrol("kaynak agaci, mevcut korunur (onune eklenir)",
            giris.alt_surec_pythonpath("/a:/b", kaynak_agaci=True)
            == os.pathsep.join([kok, "/a:/b"]))
    kontrol("zaten bastaysa tekrar eklenmez",
            giris.alt_surec_pythonpath(kok + os.pathsep + "/a", kaynak_agaci=True)
            == kok + os.pathsep + "/a")
    kontrol("kurulu pakette dokunulmaz (None)",
            giris.alt_surec_pythonpath("/a", kaynak_agaci=False) is None)
    kontrol("varsayilan: kaynak agacinda (bu depo) ekler",
            giris.alt_surec_pythonpath("").split(os.pathsep)[0] == kok)
    sekme = open(os.path.join(KOK, "arayuz", "sekme_tukenme.py"), encoding="utf-8").read()
    kontrol("sekme_tukenme alt_surec_pythonpath kullanir", "alt_surec_pythonpath" in sekme)
    kontrol("sekme_tukenme PYTHONPATH'i KOK ile ezmez",
            'insert("PYTHONPATH", KOK)' not in sekme)


def test_gui_cikis_kodu(monkeypatch, capsys):
    print("\n[T2G-2] giris.gui: SystemExit kodu None/int/metin -> int")
    from arayuz import ana_pencere
    from cekirdek import giris

    def _cik(kod):
        def _main(argv=None):
            raise SystemExit(kod)
        return _main
    for kod, beklenen in ((None, 0), (0, 0), (3, 3), ("bozuk dosya", 1)):
        monkeypatch.setattr(ana_pencere, "main", _cik(kod))
        kontrol("SystemExit(%r) -> %d" % (kod, beklenen), giris.gui([]) == beklenen)
    kontrol("metin kodu stderr'e yazilir", "bozuk dosya" in capsys.readouterr().err)
    monkeypatch.setattr(ana_pencere, "main", lambda argv=None: 5)
    kontrol("normal donus kodu aynen", giris.gui([]) == 5)


def test_alt_surec_bilinmeyen_mesaji():
    print("\n[T2G-3] bilinmeyen alt surec: ceviri isaretli mesaj")
    from cekirdek import giris
    try:
        giris.alt_surec_komutu("yok", [])
        kontrol("ValueError", False)
    except ValueError as e:
        kontrol("mesaj adi icerir", "yok" in str(e), str(e))
    kaynak = open(os.path.join(KOK, "cekirdek", "giris.py"), encoding="utf-8").read()
    kontrol("mesaj _() ile", '_("bilinmeyen alt süreç' in kaynak)


def test_derle_kurulu_pakette_onege_yazmaz(tmp_path, monkeypatch):
    print("\n[T2G-4] kilavuz derleme: varsayilan cikti; kurulu pakette onbellek dizini")
    from cekirdek import yollar
    from arayuz.yardim import derle
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "onbellek"))
    kontrol("kaynak agacinda <kok>/build/kilavuz",
            derle.varsayilan_cikti(kaynak_agaci=True)
            == os.path.join(yollar.veri_koku(), "build", "kilavuz"))
    kontrol("kurulu pakette onbellek_dizini()/kilavuz",
            derle.varsayilan_cikti(kaynak_agaci=False)
            == os.path.join(yollar.onbellek_dizini(), "kilavuz"))
    kontrol("bu depoda varsayilan kaynak agaci",
            derle.varsayilan_cikti() == os.path.join(yollar.veri_koku(), "build", "kilavuz"))


def test_derle_sozluk_yoksa_acik_hata(tmp_path, monkeypatch, capsys):
    print("\n[T2G-5] SOZLUK.md yoksa acik hata (kurulu paket), hicbir dosya yazilmaz")
    from arayuz.yardim import derle
    yok = str(tmp_path / "SOZLUK.md")
    monkeypatch.setattr(derle, "SOZLUK_KAYNAGI", yok)
    try:
        derle.sozluk_terimleri()
        kontrol("FileNotFoundError", False)
    except FileNotFoundError as e:
        kontrol("FileNotFoundError, yol mesajda", yok in str(e), str(e))
    kopya = tmp_path / "kilavuz"
    os.makedirs(kopya / "tr")
    hedef = kopya / "tr" / derle.SOZLUK_DOSYASI
    hedef.write_text("degismemeli", encoding="utf-8")
    try:
        derle.sozluk_yenile(dizin=str(kopya))
        kontrol("sozluk_yenile hata verir", False)
    except FileNotFoundError:
        kontrol("sozluk_yenile hata verir", True)
    kontrol("dosya degismedi", hedef.read_text(encoding="utf-8") == "degismemeli")
    kontrol("CLI --sozluk -> 2", derle.main(["--sozluk"]) == 2)
    kontrol("CLI hata metni stderr'de", "SOZLUK.md" in capsys.readouterr().err)


HIZLI = [test_alt_surec_pythonpath, test_gui_cikis_kodu, test_alt_surec_bilinmeyen_mesaji,
         test_derle_kurulu_pakette_onege_yazmaz, test_derle_sozluk_yoksa_acik_hata]
YAVAS = []
