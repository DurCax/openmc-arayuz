# -*- coding: utf-8 -*-
"""
giris.py -- paket giris noktalari (pyproject.toml [project.scripts]).

  openmc-arayuz        -> gui()   = python -m arayuz.ana_pencere [spec.json]
  openmc-arayuz-kosu   -> kosu()  = python -m cekirdek.kosucu spec.json [...]
  openmc-arayuz-kosu rapor <kosu_dizini> [-o rapor.pdf] [--spec spec.json]
                       -> rapor_komutu() (cekirdek/rapor.py; kosucu'ya uğramaz)

Ince sarmalayicilar: davranis mevcut modul girislerinin aynisidir. GUI tarafi
runpy ile `python -m arayuz.ana_pencere` gibi calistirilir; boylece pencere
modulu yeniden duzenlense de (arayuz/pencere/ paketi) giris yolu degismez.
"""

import os
import runpy
import sys

RAPOR_KOMUTU = "rapor"
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


def kosu(argv=None):
    """Terminal kosucusu: cekirdek.kosucu'nun komut satiri. Ilk arguman
    `rapor` ise rapor alt komutu calisir (kosucu._terminal cagrilmaz)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == RAPOR_KOMUTU:
        return rapor_komutu(argv[1:])
    from cekirdek import kosucu
    return kosucu._terminal(argv)


def gui(argv=None):
    """Arayuz: `python -m arayuz.ana_pencere` ile ayni."""
    if argv is not None:
        sys.argv = [sys.argv[0]] + list(argv)
    try:
        runpy.run_module("arayuz.ana_pencere", run_name="__main__", alter_sys=True)
    except SystemExit as cikis:
        return cikis.code
    return 0


if __name__ == "__main__":
    sys.exit(gui())
