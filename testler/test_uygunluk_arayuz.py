# -*- coding: utf-8 -*-
"""
test_uygunluk_arayuz.py -- Dalga S-2: uygunluk denetiminin rapor eki, arayuz
paneli ve `openmc-arayuz-kosu uygunluk` alt komutu.

  * Raporun kendisi K5'ten (belirsizlik/birim bildirimi) temiz gecer.
  * Rapora "Uygunluk eki" girer (HTML + PDF): profiller, karsilanan /
    karsilanmayan / uygulanamayan tablosu, durust cerceve metni AYNEN; B
    profilinde V&V yoksa "USL hesaplanamadi" notu.
  * Profil secimi spec["calistirma"]["uygunluk_profilleri"]; gidis-donus bozulmaz.
  * Panel: kural kimligi, seviye ikonu, oneri; "bulguya git"; Calistir sayfasinda
    kosu yuklenince dolar; kayip parcacik ve OpenMC uyarilari gorunur (M5).
  * CLI: hata varsa cikis kodu 1, yoksa 0; kullanim hatasi 2.

Fixture: testler/veri/kosu_ornek (Monte Carlo KOSULMAZ). Yalniz offscreen.
"""

import contextlib
import copy
import glob
import io
import json
import os
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")
KAYIP_UYARISI = (" WARNING: After particle 1234 crossed surface 7 it could not be located in\n"
                 "          any cell and it did not leak.\n")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec():
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        return json.load(f)


def _gecici_kosu(kayip=False):
    """Fixture'in gecici kopyasi; kayip=True ise kosu.log'a kayip parcacik eklenir."""
    kok = tempfile.mkdtemp(prefix="uyg_arayuz_")
    hedef = os.path.join(kok, "kosu")
    shutil.copytree(FIXTURE, hedef)
    if kayip:
        with open(os.path.join(hedef, "kosu.log"), "a", encoding="utf-8") as f:
            f.write(KAYIP_UYARISI)
    return kok, hedef


def _k5_sorunlari(spec, metin):
    from cekirdek.uygunluk_denetimi.denetle import denetle, sorunlar
    return [b for b in sorunlar(denetle(spec, FIXTURE, ("D",), rapor_metni=metin))
            if b.kural.startswith("K5")]


# ============================================================================
# RAPOR
# ============================================================================

@gereksinim("R-S-06")
def test_rapor_k5_temiz():
    print("\n[S2-1] uretilen rapor K5'ten (1σ, 2 anlamli rakam, pcm tanimi, SI) temiz")
    from cekirdek import rapor
    spec = _spec()
    dizin = tempfile.mkdtemp(prefix="uyg_rapor_")
    try:
        yol = rapor.olustur(spec, FIXTURE, os.path.join(dizin, "r.html"), "html").yol
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        k5 = _k5_sorunlari(spec, metin)
        kontrol("K5 sorunu yok", not k5, "-> %s" % [(b.kural, b.mesaj) for b in k5])
        from cekirdek.uygunluk_denetimi.kurallar_rapor import belirsizlik_metni, pcm_tanimi
        g = rapor.icerik_topla(spec, FIXTURE)["kosu"]
        kontrol("k-eff GUM bicimi", belirsizlik_metni(g["keff"], g["sigma"]) in metin)
        kontrol("pcm tanimi yazili", pcm_tanimi("drho") in metin)
        kontrol("1σ aciklamasi yazili", "standart belirsizlik" in metin)
        model = rapor.olustur(spec, None, os.path.join(dizin, "m.html"), "html").yol
        with open(model, encoding="utf-8") as f:
            k5m = _k5_sorunlari(spec, f.read())
        kontrol("yalniz model raporu da K5 temiz", not k5m, "-> %s" % [b.mesaj for b in k5m])
    finally:
        shutil.rmtree(dizin, True)


def test_belirsizlik_bicimi_buyuk_sigma():
    print("\n[S2-2] buyuk sigma ortak kuvvetle; K5 denetcisi bu bicimi kabul eder")
    from cekirdek.uygunluk_denetimi.kurallar_rapor import belirsizlik_metni, pcm_tanimi
    m = belirsizlik_metni(15411.0, 205.0, birim="pcm")
    kontrol("olcekli bicim", m == "(154.1 ± 2.0) × 10² pcm (1σ)", "-> %s" % m)
    kontrol("K5 temiz", not _k5_sorunlari(_spec(), "ρ = %s; %s" % (m, pcm_tanimi())))


def _ek_metni(profiller, bicim="html"):
    from cekirdek import rapor, rapor_uygunluk
    spec = rapor_uygunluk.profilleri_yaz(_spec(), profiller)
    dizin = tempfile.mkdtemp(prefix="uyg_ek_")
    try:
        yol = rapor.olustur(spec, FIXTURE, os.path.join(dizin, "r." + bicim), bicim).yol
        if bicim == "pdf":
            return os.path.getsize(yol)
        with open(yol, encoding="utf-8") as f:
            return f.read()
    finally:
        shutil.rmtree(dizin, True)


@gereksinim("R-S-13", "R-S-01")
def test_rapor_uygunluk_eki_html():
    print("\n[S2-3] HTML raporda Uygunluk eki: profiller, tablo, cerceve AYNEN, USL notu")
    from cekirdek.uygunluk_denetimi.kurallar import etiket_metni, IYI_UYGULAMA
    from cekirdek.uygunluk_denetimi.kurallar_rapor import duz_metin
    from cekirdek.uygunluk_denetimi.profiller import durust_cerceve
    metin = _ek_metni(("A", "B", "D"))
    duz = " ".join(duz_metin(metin).split())
    kontrol("baslik", "Uygunluk eki" in duz)
    kontrol("cerceve AYNEN", " ".join(durust_cerceve().split()) in duz)
    for parca in ("Karşılanan", "Karşılanmayan", "Uygulanamayan", "K1", "K3", "K4",
                  "K5", "K6", "Monte Carlo iyi uygulaması", "Kritiklik güvenliği",
                  etiket_metni(IYI_UYGULAMA), "LA-UR-09-03136", "NUREG/CR-6698"):
        kontrol("ek icerir: %s" % parca, parca in duz)
    kontrol("USL notu", "USL hesaplanamadı" in duz
            and "kritiklik güvenliği kanıtı değildir" in duz)
    k5 = _k5_sorunlari(_spec(), metin)
    kontrol("ekli rapor da K5 temiz", not k5, "-> %s" % [b.mesaj for b in k5])
    a = " ".join(duz_metin(_ek_metni(("A",))).split())
    kontrol("B secilmezse USL notu yok", "USL hesaplanamadı" not in a and "Uygunluk eki" in a)


@gereksinim("R-S-13")
def test_rapor_uygunluk_eki_pdf():
    print("\n[S2-4] PDF: ekli belge metni Uygunluk eki ve cerceveyi icerir")
    _qt()
    from cekirdek import rapor, rapor_pdf, rapor_uygunluk
    from cekirdek.uygunluk_denetimi.profiller import durust_cerceve
    spec = rapor_uygunluk.profilleri_yaz(_spec(), ("A", "B", "D"))
    icerik = rapor.icerik_topla(spec, FIXTURE)
    duz = " ".join(rapor_pdf._belge(icerik).toPlainText().split())
    kontrol("PDF belgesinde ek", "Uygunluk eki" in duz and "USL hesaplanamadı" in duz)
    kontrol("PDF belgesinde cerceve", " ".join(durust_cerceve().split()) in duz)
    kontrol("PDF yazildi", _ek_metni(("A", "B", "D"), "pdf") > 0)


@gereksinim("R-S-13")
def test_rapor_uygunluk_hatasi_raporu_durdurmaz():
    print("\n[S2-5] bozuk uygunluk_girdisi.json: rapor yazilir, ekte ve uyarida hata")
    from cekirdek import rapor
    from cekirdek.uygunluk_denetimi.kurallar_rapor import duz_metin
    kok, dizin = _gecici_kosu()
    try:
        with open(os.path.join(dizin, "uygunluk_girdisi.json"), "w", encoding="utf-8") as f:
            f.write("{bozuk")
        s = rapor.olustur(_spec(), dizin, os.path.join(kok, "r.html"), "html")
        with open(s.yol, encoding="utf-8") as f:
            duz = duz_metin(f.read())
        kontrol("uyarilarda", any("uygunluk" in u for u in s.uyarilar), "-> %s" % (s.uyarilar,))
        kontrol("ekte hata metni", "uygunluk_girdisi.json" in duz)
    finally:
        shutil.rmtree(kok, True)


# ============================================================================
# PROFIL SECIMI (spec)
# ============================================================================

def test_profil_secimi_spec():
    print("\n[S2-6] profil secimi spec['calistirma']; varsayilan A+D; spec degismez")
    from cekirdek import rapor_uygunluk, sema
    spec = _spec()
    kontrol("varsayilan", rapor_uygunluk.secili_profiller(spec) == ("A", "D"))
    kopya = copy.deepcopy(spec)
    yeni = rapor_uygunluk.profilleri_yaz(spec, ("D", "B", "A", "B"))
    kontrol("girdi degismedi", spec == kopya)
    kontrol("sirali, tekil", rapor_uygunluk.secili_profiller(yeni) == ("A", "B", "D"))
    bozuk = dict(spec, calistirma={"uygunluk_profilleri": ["A", "Z", 3]})
    kontrol("bilinmeyen atlanir", rapor_uygunluk.secili_profiller(bozuk) == ("A",))
    kontrol("bos secim -> varsayilan degil, bos",
            rapor_uygunluk.secili_profiller(rapor_uygunluk.profilleri_yaz(spec, ())) == ())
    dizin = tempfile.mkdtemp(prefix="uyg_spec_")
    try:
        yol = os.path.join(dizin, "m.json")
        sema.kaydet(yeni, yol)
        kontrol("kaydet/yukle gidis-donus",
                rapor_uygunluk.secili_profiller(sema.yukle(yol)) == ("A", "B", "D"))
    finally:
        shutil.rmtree(dizin, True)


def test_ornekler_gidis_donus_bozulmaz():
    print("\n[S2-7] ornekler: yukle -> kaydet -> yukle ayni; anahtar kendiliginden eklenmez")
    from cekirdek import rapor_uygunluk, sema
    dosyalar = sorted(glob.glob(os.path.join(KOK, "ornekler", "*.json")))
    dizin = tempfile.mkdtemp(prefix="uyg_ornek_")
    bozulan = []
    try:
        for yol in dosyalar:
            spec = sema.yukle(yol)
            if rapor_uygunluk.SPEC_ANAHTARI in (spec.get("calistirma") or {}):
                bozulan.append(os.path.basename(yol) + " (anahtar eklendi)")
            hedef = os.path.join(dizin, os.path.basename(yol))
            sema.kaydet(rapor_uygunluk.profilleri_yaz(spec, ("A", "C")), hedef)
            geri = sema.yukle(hedef)
            beklenen = rapor_uygunluk.profilleri_yaz(spec, ("A", "C"))
            if geri != beklenen:
                bozulan.append(os.path.basename(yol))
    finally:
        shutil.rmtree(dizin, True)
    kontrol("ornek var", len(dosyalar) >= 20, "-> %d" % len(dosyalar))
    kontrol("gidis-donus bozulmadi", not bozulan, "-> %s" % bozulan)


# ============================================================================
# CLI
# ============================================================================

def _cli(argv):
    from cekirdek import giris
    cikti, hata = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(hata):
        kod = giris.kosu(argv)
    return kod, cikti.getvalue(), hata.getvalue()


@gereksinim("R-S-12")
def test_cli_uygunluk():
    print("\n[S2-8] openmc-arayuz-kosu uygunluk: 0 temiz, 1 hata, 2 kullanim")
    kod, cikti, _h = _cli(["uygunluk", FIXTURE])
    kontrol("temiz fixture -> 0", kod == 0, "-> %r\n%s" % (kod, cikti))
    kontrol("kural kimlikleri basildi", "K1" in cikti and "K4" in cikti)
    kontrol("cerceve basildi", "sertifika" in cikti)
    kod, cikti, _h = _cli(["uygunluk", FIXTURE, "--profil", "A,B"])
    kontrol("--profil A,B", kod == 0 and "K6" in cikti and "K4" not in cikti
            and "USL hesaplanamadı" in cikti)
    kok, dizin = _gecici_kosu(kayip=True)
    try:
        kod, cikti, _h = _cli(["uygunluk", dizin, "--profil", "A"])
        kontrol("kayip parcacik -> 1", kod == 1 and "K3" in cikti, "-> %r\n%s" % (kod, cikti))
    finally:
        shutil.rmtree(kok, True)
    for argv, neden in ((["uygunluk"], "dizin yok"),
                        (["uygunluk", FIXTURE, "--profil", "A,Z"], "bilinmeyen profil"),
                        (["uygunluk", FIXTURE, "--profil"], "deger yok"),
                        (["uygunluk", os.path.join(FIXTURE, "yok")], "olmayan dizin")):
        kod, _c, hata = _cli(argv)
        kontrol("kullanim hatasi 2: %s" % neden, kod == 2 and hata.strip(), "-> %r" % kod)
    kod, cikti, _h = _cli(["uygunluk", "--yardim"])
    kontrol("yardim 0", kod == 0 and "--profil" in cikti)


# ============================================================================
# ARAYUZ
# ============================================================================

def _bulgular(profiller=("A", "B", "D"), dizin=FIXTURE):
    from cekirdek.uygunluk_denetimi.denetle import denetle
    return denetle(_spec(), dizin, profiller)


def test_panel_bulgular():
    print("\n[S2-9] panel: kural kimligi, seviye ikonu, oneri; sorunlar once; cerceve")
    _qt()
    from arayuz.uygunluk_paneli import UygunlukPaneli
    from cekirdek.uygunluk_denetimi.profiller import durust_cerceve
    p = UygunlukPaneli()
    kok, dizin = _gecici_kosu(kayip=True)
    try:
        bulgular = _bulgular(("A", "B", "D"), dizin)
        p.goster(bulgular, ("A", "B", "D"))
        n = p.liste.count()
        kontrol("her bulgu bir satir", n == len(bulgular), "-> %d / %d" % (n, len(bulgular)))
        ilk = p.liste.item(0)
        kontrol("sorun once (K3 hata)", ilk.text().startswith("K3"), "-> %s" % ilk.text())
        kontrol("seviye ikonu", not ilk.icon().isNull())
        kontrol("oneri metinde", "Öneri" in ilk.text() or "Öneri" in ilk.toolTip())
        kontrol("kaynak ipucunda", "Kaynak" in ilk.toolTip())
        kontrol("ozet rozeti hata", p.rozet.tur() == "hata", "-> %s" % p.rozet.tur())
        kontrol("cerceve AYNEN", p.cerceve.text() == durust_cerceve())
        kontrol("USL notu (B, V&V yok)", "USL" in p.usl_notu.text() and not p.usl_notu.isHidden())
        kontrol("kilavuz yer tutucu", bool(p.kilavuz.text()))
        hedefler = []
        p.git_istendi.connect(hedefler.append)
        p.liste.setCurrentRow(0)
        kontrol("bulguya git etkin (K3 -> geometri)", p.d_git.isEnabled())
        p.d_git.click()
        kontrol("git sinyali", hedefler == ["kor"], "-> %s" % hedefler)
        k5 = [i for i in range(n) if p.liste.item(i).text().startswith("K5")]
        p.liste.setCurrentRow(k5[0])
        kontrol("gidilecek sayfa yoksa dugme kapali", not p.d_git.isEnabled())
        p.goster(_bulgular(("A",)), ("A",))
        kontrol("B yoksa USL notu gizli", p.usl_notu.isHidden())
        p.hata_goster("uygunluk_girdisi.json okunamadı")
        kontrol("hata gosterimi", p.liste.count() == 1 and p.rozet.tur() == "hata")
    finally:
        shutil.rmtree(kok, True)
        p.deleteLater()


def test_panel_profil_secimi():
    print("\n[S2-10] panel profil kutulari spec'i izler; degisince sinyal")
    _qt()
    from arayuz.uygunluk_paneli import UygunlukPaneli
    p = UygunlukPaneli()
    gelen = []
    p.profiller_degisti.connect(gelen.append)
    p.profilleri_ayarla(("A", "D"))
    kontrol("yuklemede sinyal yok", not gelen)
    kontrol("kutular", [p.kutular[k].isChecked() for k in "ABCD"] == [True, False, False, True])
    p.kutular["C"].setChecked(True)
    kontrol("sinyal secimi tasir", gelen == [("A", "C", "D")], "-> %s" % gelen)
    p.deleteLater()


@gereksinim("R-S-04")
def test_calistir_sayfasi_panel_ve_m5():
    print("\n[S2-11] Calistir: kosu yuklenince panel dolar; kayip parcacik gorunur (M5)")
    _qt()
    from arayuz.sekme_calistir import CalistirSekmesi
    s = CalistirSekmesi()
    kok, dizin = _gecici_kosu(kayip=True)
    try:
        s.spec_ayarla(_spec(), os.path.join(kok, "m.json"))
        s.resize(1280, 900)
        s.show()
        kontrol("yuklendi", s.kosu_dizinini_yukle(dizin))
        kontrol("panel gorunur", s.uygunluk.isVisible())
        kontrol("panel doldu", s.uygunluk.liste.count() > 3)
        uyari = s.kart.cikti_etiket
        kontrol("kayip parcacik Calistir sayfasinda", uyari.isVisible()
                and "KAYIP PARÇACIK" in uyari.text(), "-> %r" % uyari.text())
        degisen = []
        s.degisti.connect(degisen.append)
        s.uygunluk.kutular["B"].setChecked(True)
        kontrol("profil spec'e yazildi", s.spec["calistirma"]["uygunluk_profilleri"]
                == ["A", "B", "D"] and degisen == [s.KONU], "-> %s" % degisen)
        kontrol("yeniden denetlendi (K6 listede)", any(
            s.uygunluk.liste.item(i).text().startswith("K6")
            for i in range(s.uygunluk.liste.count())))
        s.sifirla()
        kontrol("sifirla paneli gizler", not s.uygunluk.isVisible()
                and not s.kart.cikti_etiket.isVisible())
    finally:
        s.close()
        s.deleteLater()
        shutil.rmtree(kok, True)


def test_qprocess_yolu_gunluk_ve_uyarilar():
    print("\n[S2-12] QProcess yolu: cikti kosu.log'a yazilir, ozet_satirlari gorunur")
    _qt()
    from arayuz.sekme_calistir import CalistirSekmesi
    s = CalistirSekmesi()
    kok, dizin = _gecici_kosu()
    try:
        os.remove(os.path.join(dizin, "kosu.log"))
        with open(os.path.join(FIXTURE, "kosu.log"), encoding="utf-8") as f:
            gunluk = f.read() + KAYIP_UYARISI
        s.spec_ayarla(_spec(), os.path.join(kok, "m.json"))
        s._dizin = dizin
        s._kosu_kusagi = s._kusak
        for satir in gunluk.splitlines():
            s._satir_isle(satir)
        s._bitti(0, None)
        kontrol("kosu.log yazildi", os.path.exists(os.path.join(dizin, "kosu.log")))
        kontrol("sonuc gosterildi", s.sonuc_var())
        kontrol("kayip parcacik gorunur", "KAYIP PARÇACIK" in s.kart.cikti_etiket.text())
        kontrol("panelde K3 hata", s.uygunluk.rozet.tur() == "hata")
    finally:
        s.deleteLater()
        shutil.rmtree(kok, True)


HIZLI = [test_rapor_k5_temiz, test_belirsizlik_bicimi_buyuk_sigma,
         test_rapor_uygunluk_eki_html, test_rapor_uygunluk_eki_pdf,
         test_rapor_uygunluk_hatasi_raporu_durdurmaz, test_profil_secimi_spec,
         test_ornekler_gidis_donus_bozulmaz, test_cli_uygunluk, test_panel_bulgular,
         test_panel_profil_secimi, test_calistir_sayfasi_panel_ve_m5,
         test_qprocess_yolu_gunluk_ve_uyarilar]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for t in HIZLI:
        t()
    print("\n%d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
