# -*- coding: utf-8 -*-
"""
giris.py -- paket giris noktalari (pyproject.toml [project.scripts]).

  openmc-arayuz        -> gui()   = python -m arayuz.ana_pencere [spec.json]
  openmc-arayuz-kosu   -> kosu()  = python -m cekirdek.kosucu spec.json [...]
  openmc-arayuz-kosu rapor <kosu_dizini> [-o rapor.pdf] [--spec spec.json]
                       -> rapor_komutu() (cekirdek/rapor.py; kosucu'ya uğramaz)
  openmc-arayuz-kosu uygunluk <kosu_dizini> [--profil A,B,C,D] [--siki]
                       -> uygunluk_komutu(): bulgulari basar; cikis 1 = hata
                          bulgusu var, 0 = yok, 2 = kullanim hatasi, 3 = --siki
                          ile degerlendirilemeyen kural var (CI / ders)
  openmc-arayuz-kosu --alt tukenme spec.json [-s N] [--dizin D] [...]
                       -> arayuzun alt surecleri: tukenme (= python -m
                          cekirdek.tukenme ...) ve cizim (onizleme iscisi,
                          stdin/stdout cerceve protokolu; cekirdek/cizim_sureci.py)

Ince sarmalayicilar: davranis mevcut modul girislerinin aynisidir. GUI
arayuz.ana_pencere.main()'i dogrudan cagirir (pencere modulu arayuz/pencere/
paketine tasinsa da giris yolu degismez).

ALT SURECLER (alt_surec_komutu)
  Arayuz bir alt sureci `sys.executable -m cekirdek.giris --alt <ad> ...` ile
  baslatir. Neden bu komut: (1) sys.executable arayuzu calistiran yorumlayicinin
  KENDISIDIR -- ayni ortam (openmc, numpy) garanti; (2) `-m cekirdek.giris`
  hem kurulu pakette (site-packages) hem kaynak agacindan (PYTHONPATH = paket
  koku) calisir, oysa `openmc-arayuz-kosu` betigi yalniz pip kurulumundan sonra
  vardir ve etkinlestirilmemis bir venv/conda ortaminda PATH'te olmayabilir;
  (3) dagitici tek: `openmc-arayuz-kosu --alt tukenme` ile ayni kod yolu;
  (4) `-P` (Python >= 3.11) calisma dizinini modul yoluna eklemez: cwd'den
  modul kacirma olmaz. Cagiran ayrica calisma dizinini paket kokune sabitler.
"""

import os
import sys

RAPOR_KOMUTU = "rapor"
UYGUNLUK_KOMUTU = "uygunluk"
ALT_SECENEGI = "--alt"
ALT_TUKENME = "tukenme"
ALT_CIZIM = "cizim"
# -P (Python >= 3.11): `-m` calisma dizinini sys.path'in basina KOYMAZ; aksi halde
# cwd'deki sahte bir `cekirdek/` paketi gercegin yerine yuklenirdi (modul kacirma).
# Kaynak agacinda paket koku PYTHONPATH ile gelir (alt_surec_pythonpath).
_GUVENLI_YOL = ["-P"] if sys.version_info >= (3, 11) else []
_RAPOR_UZANTILARI = {".html": "html", ".htm": "html", ".pdf": "pdf"}
_SPEC_ADAYLARI = ("spec.json", "tukenme_spec.json")


def _rapor_yardimi():
    from cekirdek.ceviri import _
    return _(
        "KULLANIM\n"
        "  openmc-arayuz-kosu rapor <koşu_dizini> [-o rapor.pdf] [--spec model.json]\n\n"
        "  -o, --cikti   rapor dosyası; biçim uzantıdan (.pdf | .html).\n"
        "                Verilmezse <koşu_dizini>/rapor.pdf\n"
        "  --spec        modelin JSON dosyası. Verilmezse koşu dizinindeki\n"
        "                spec.json ya da tukenme_spec.json okunur.")


def _rapor_argumanlari(argv):
    """(dizin, cikti, spec_yolu) ya da hata metni (str)."""
    from cekirdek.ceviri import _
    dizin = cikti = spec_yolu = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-o", "--cikti", "--spec"):
            if i + 1 >= len(argv):
                return _("%s bir değer bekliyor") % a
            if a == "--spec":
                spec_yolu = argv[i + 1]
            else:
                cikti = argv[i + 1]
            i += 2
            continue
        if a.startswith("-") or dizin is not None:
            return _("bilinmeyen seçenek: %s") % a
        dizin = a
        i += 1
    if dizin is None:
        return _("koşu dizini verilmedi")
    return dizin, cikti or os.path.join(dizin, "rapor.pdf"), spec_yolu


def _rapor_speci(dizin, spec_yolu):
    """Spec yolu: verilen, yoksa kosu dizinindeki adaylardan ilki; yoksa None."""
    if spec_yolu:
        return spec_yolu
    for ad in _SPEC_ADAYLARI:
        yol = os.path.join(dizin, ad)
        if os.path.exists(yol):
            return yol
    return None


def rapor_komutu(argv):
    """`openmc-arayuz-kosu rapor` alt komutu. Cikis kodu: 0 tamam, 1 rapor
    hatasi, 2 kullanim hatasi."""
    from cekirdek import rapor, sema
    from cekirdek.ceviri import _
    if argv and argv[0] in ("-h", "--yardim", "--help"):
        print(_rapor_yardimi())
        return 0
    sonuc = _rapor_argumanlari(argv)
    if isinstance(sonuc, str):
        print(sonuc, file=sys.stderr)
        print(_rapor_yardimi(), file=sys.stderr)
        return 2
    dizin, cikti, spec_yolu = sonuc
    bicim = _RAPOR_UZANTILARI.get(os.path.splitext(cikti)[1].lower())
    if bicim is None:
        print(_("rapor uzantısı .pdf ya da .html olmalı: %s") % cikti, file=sys.stderr)
        return 2
    spec_yolu = _rapor_speci(dizin, spec_yolu)
    if spec_yolu is None or not os.path.exists(spec_yolu):
        print(_("model (spec) bulunamadı: koşu dizininde spec.json yok; --spec ile "
                "verin (%s)") % (spec_yolu or dizin), file=sys.stderr)
        return 2
    try:
        spec = sema.yukle(spec_yolu)
        sonuc = rapor.olustur(spec, dizin, cikti, bicim)
    except (OSError, ValueError) as e:      # RaporHatasi da ValueError'dir
        from cekirdek.gunluk import kaydedici
        kaydedici(__name__).warning("rapor alt komutu başarısız", exc_info=True)
        print(_("rapor oluşturulamadı: %s") % e, file=sys.stderr)
        return 1
    for uyari in sonuc.uyarilar:
        print(_("uyarı: %s") % uyari)
    print(_("rapor yazıldı: %s") % sonuc.yol)
    return 0


def _uygunluk_yardimi():
    from cekirdek.ceviri import _
    return _(
        "KULLANIM\n"
        "  openmc-arayuz-kosu uygunluk <koşu_dizini> [--profil A,B,C,D] [--siki]\n\n"
        "  --profil   denetim profilleri (virgülle). Verilmezse koşu dizinindeki\n"
        "             spec.json'un seçimi; o da yoksa A,D.\n"
        "             A Monte Carlo iyi uygulaması, B kritiklik güvenliği,\n"
        "             C reaktör kor tasarımı, D raporlama.\n"
        "  --siki     değerlendirilemeyen (uygulanamadı) kural da başarısızlıktır.\n\n"
        "  Çıkış kodu: 0 hata bulgusu yok, 1 hata bulgusu var, 2 kullanım hatası,\n"
        "  3 (--siki ile) değerlendirilemeyen kural var.")


def _uygunluk_argumanlari(argv):
    """(dizin, profiller | None, siki) ya da hata metni (str)."""
    from cekirdek import rapor_uygunluk
    from cekirdek.ceviri import _
    dizin = profiller = None
    siki = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--siki":
            siki = True
            i += 1
            continue
        if a == "--profil":
            if i + 1 >= len(argv):
                return _("%s bir değer bekliyor") % a
            try:
                profiller = rapor_uygunluk.profil_ayristir(argv[i + 1])
            except ValueError as e:
                return str(e)
            i += 2
            continue
        if a.startswith("-") or dizin is not None:
            return _("bilinmeyen seçenek: %s") % a
        dizin = a
        i += 1
    if dizin is None:
        return _("koşu dizini verilmedi")
    if not os.path.isdir(dizin):
        return _("koşu dizini bulunamadı: %s") % dizin
    return dizin, profiller, siki


def _bulgu_satirlari(bulgular):
    from cekirdek import rapor_uygunluk
    from cekirdek.ceviri import _
    adlar = {"karsilandi": _("kontrolü geçti"), "karsilanmadi": _("KONTROLÜ GEÇMEDİ"),
             "uygulanamadi": _("uygulanamadı"), "bilgi": _("not")}
    seviyeler = {"hata": _("HATA"), "uyari": _("UYARI"), "bilgi": _("BİLGİ")}
    satirlar = []
    for b in rapor_uygunluk.sirala(bulgular):
        satirlar.append("[%s] %s (%s) %s: %s" % (seviyeler.get(b.seviye, b.seviye),
                                                b.kural, b.profil,
                                                adlar.get(b.durum, b.durum), b.mesaj))
        if b.oneri and b.durum != "karsilandi":
            satirlar.append("    " + _("Öneri: %s") % b.oneri)
    return satirlar


def uygunluk_komutu(argv):
    """`openmc-arayuz-kosu uygunluk` alt komutu. Cikis: 0 hata bulgusu yok,
    1 hata bulgusu var ya da denetim yapilamadi, 2 kullanim hatasi, 3 --siki
    ile degerlendirilemeyen kural var."""
    from cekirdek import rapor_uygunluk, sema
    from cekirdek.ceviri import _
    from cekirdek.uygunluk_denetimi.denetle import ozet
    from cekirdek.uygunluk_denetimi.profiller import durust_cerceve
    if argv and argv[0] in ("-h", "--yardim", "--help"):
        print(_uygunluk_yardimi())
        return 0
    sonuc = _uygunluk_argumanlari(argv)
    if isinstance(sonuc, str):
        print(sonuc, file=sys.stderr)
        print(_uygunluk_yardimi(), file=sys.stderr)
        return 2
    dizin, profiller, siki = sonuc
    spec_yolu = _rapor_speci(dizin, None)
    spec = None
    try:
        spec = sema.yukle(spec_yolu) if spec_yolu else None
    except (OSError, ValueError) as e:
        print(_("uyarı: model (spec) okunamadı, yalnız koşu denetlenir: %s") % e,
              file=sys.stderr)
    if profiller is None:
        profiller = rapor_uygunluk.secili_profiller(spec)
    vv, uygulama = rapor_uygunluk.vv_baglami(spec, dizin, profiller)
    bulgular, hata = rapor_uygunluk.denetle(spec, dizin, profiller, vv=vv, uygulama=uygulama)
    if hata:
        print(hata, file=sys.stderr)
        return 1
    print("\n".join(_bulgu_satirlari(bulgular)))
    sayi = ozet(bulgular)
    print(_("\nProfiller: %s · %d hata, %d uyarı · %d kontrolü geçti, %d kontrolü geçmedi, "
            "%d uygulanamadı") % (",".join(profiller), sayi["seviye"]["hata"],
                                  sayi["seviye"]["uyari"], sayi["durum"]["karsilandi"],
                                  sayi["durum"]["karsilanmadi"], sayi["durum"]["uygulanamadi"]))
    notu = rapor_uygunluk.usl_notu(profiller, vv)
    if notu:
        print(notu)
    print("\n" + durust_cerceve())
    return rapor_uygunluk.cikis_kodu(bulgular, siki=siki)


def _tukenme_alt_sureci(argv):
    from cekirdek import tukenme
    return tukenme._terminal(argv)


def _cizim_alt_sureci(argv):
    from cekirdek import cizim_sureci
    return cizim_sureci.ana(argv)


_ALT_SURECLER = {ALT_TUKENME: _tukenme_alt_sureci, ALT_CIZIM: _cizim_alt_sureci}


def alt_surec_komutu(ad, argumanlar, python=None):
    """Arayuzun `ad` alt surecini baslatan (program, argumanlar); QProcess.start
    ve subprocess icin. Gerekce: modul belgesi (ALT SURECLER). python:
    yorumlayici (varsayilan sys.executable). Bilinmeyen ad ValueError. Kaynak
    agacindan calisirken cagiran PYTHONPATH'e yollar.paket_koku()'nu koyar."""
    if ad not in _ALT_SURECLER:
        from cekirdek.ceviri import _
        raise ValueError(_("bilinmeyen alt süreç: %r") % (ad,))
    return (python or sys.executable,
            _GUVENLI_YOL + ["-m", "cekirdek.giris", ALT_SECENEGI, ad] + list(argumanlar))


def alt_surec_pythonpath(mevcut, kaynak_agaci=None):
    """Alt surecin PYTHONPATH'i ya da None (degistirme). Kaynak agacindan
    calisirken paket koku MEVCUT degerin ONUNE eklenir (ezilmez); kurulu
    pakette paket zaten yorumlayicinin yolundadir, dokunulmaz.
    kaynak_agaci: None -> yollar.kaynak_agaci_mi()."""
    from cekirdek import yollar
    if kaynak_agaci is None:
        kaynak_agaci = yollar.kaynak_agaci_mi()
    if not kaynak_agaci:
        return None
    kok = yollar.paket_koku()
    ogeler = [o for o in (mevcut or "").split(os.pathsep) if o]
    if ogeler and ogeler[0] == kok:
        return mevcut
    return os.pathsep.join([kok] + ([mevcut] if mevcut else []))


def alt_komutu(argv):
    """`--alt <ad> ...` dagiticisi. Cikis: alt surecin kodu; ad yok ya da
    bilinmiyorsa 2."""
    from cekirdek.ceviri import _
    if not argv or argv[0] not in _ALT_SURECLER:
        print(_("--alt bir alt süreç adı bekliyor: %s") % ", ".join(sorted(_ALT_SURECLER)),
              file=sys.stderr)
        return 2
    return _ALT_SURECLER[argv[0]](argv[1:])


def kosu(argv=None):
    """Terminal kosucusu: cekirdek.kosucu'nun komut satiri. Ilk arguman
    `rapor` / `uygunluk` / `--alt` ise alt komut calisir (kosucu._terminal
    cagrilmaz)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    from cekirdek.ceviri import terminal_dili
    terminal_dili()                   # OPENMC_ARAYUZ_DIL verilmisse o dil
    from cekirdek import veri_yolu
    veri_yolu.surece_uygula()         # K2: Veri sayfasi secimi terminalde de gecerli
    if argv and argv[0] == ALT_SECENEGI:
        return alt_komutu(argv[1:])
    if argv and argv[0] == RAPOR_KOMUTU:
        return rapor_komutu(argv[1:])
    if argv and argv[0] == UYGUNLUK_KOMUTU:
        return uygunluk_komutu(argv[1:])
    from cekirdek import kosucu
    return kosucu._terminal(argv)


def gui(argv=None):
    """Arayuz: `python -m arayuz.ana_pencere` ile ayni; cikis kodu doner."""
    from arayuz import ana_pencere
    try:
        return ana_pencere.main(argv)
    except SystemExit as cikis:
        return _cikis_kodu(cikis.code)


def _cikis_kodu(kod):
    """SystemExit.code -> int (sys.exit anlamiyla: None 0, metin stderr'e + 1)."""
    if kod is None:
        return 0
    if isinstance(kod, int):
        return kod
    print(kod, file=sys.stderr)
    return 1


if __name__ == "__main__":
    # `python -m cekirdek.giris --alt <ad> ...` -> alt surec; aksi halde arayuz
    sys.exit(kosu() if sys.argv[1:2] == [ALT_SECENEGI] else gui())
