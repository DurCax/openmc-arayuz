# -*- coding: utf-8 -*-
"""
veri_indir_komut.py -- `python -m cekirdek.veri_indir` / veri_indir.sh komut
satiri (cekirdek/veri_indir.py'den bolundu; is mantigi orada).

  --liste | --hedef DIZIN | --kutuphane KIMLIK | --zincir KIMLIK ... |
  --yalniz-zincir | --bashrc
Basarida secim uygulama ayarina yazilir (cekirdek/veri_yolu.py); cikis 0 tamam,
1 indirme/kurma/ayar hatasi, 2 kullanim hatasi.
"""

import argparse
import os
import shlex
import sys
from typing import List, Optional

from cekirdek import veri_arsiv
from cekirdek.ceviri import _
from cekirdek.veri_indir import (VARSAYILAN_KUTUPHANE, Katalog, UrlPolitikasi, VeriHatasi,
                                 dogrulama_etiketi, katalog_politikasi, katalog_yukle,
                                 kutuphane_kur, zincir_kur)

def _argumanlar() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veri_indir", description=_("OpenMC nükleer verisini openmc.org kataloğundan "
                                         "güvenli indirir (sürdürülebilir, sha256)."))
    p.add_argument("--liste", action="store_true", help=_("katalogu listele ve çık"))
    p.add_argument("--hedef", help=_("hedef klasör (varsayılan: ~/nucdata ya da son seçim)"))
    p.add_argument("--kutuphane", default=VARSAYILAN_KUTUPHANE,
                   help=_("kütüphane kimliği (--liste)"))
    p.add_argument("--zincir", action="append",
                   help=_("zincir kimliği; birden çok verilebilir (varsayılan: uygulamanın "
                          "kullandığı termal/hızlı/CASL zincirleri)"))
    p.add_argument("--yalniz-zincir", action="store_true", help=_("yalnız zincirleri indir"))
    p.add_argument("--bashrc", action="store_true",
                   help=_("bitince ortam değişkenlerini ~/.bashrc'ye ekle"))
    return p


def _liste(kat: Katalog) -> None:
    print(_("Kaynak: %s (erişim %s)") % (kat.kaynak.get("sayfa"), kat.kaynak.get("erisim_tarihi")))
    print(_("\nKütüphaneler:"))
    for o in kat.kutuphaneler:
        print("  %-18s %-26s %6.2f GB  %s" % (o.kimlik, o.ad, o.bayt / veri_arsiv.GB, o.grup))
    print(_("\nZincirler:"))
    for o in kat.zincirler:
        print("  %-20s %-32s %7.1f MB%s" % (o.kimlik, o.ad, o.bayt / 1e6,
                                             "  *" if o.uygulamada_kullanilir else ""))
    print(_("\n* uygulamanın tükenme hesabında kullandığı zincirler"))


def _ilerleme_yazici():
    son = {}

    def yaz(asama, alinan, toplam):
        yuzde = int(100 * alinan / toplam) if toplam else 0
        if son.get(asama) != yuzde // 5:
            son[asama] = yuzde // 5
            print("   %s %3d%%" % (asama, yuzde), flush=True)
    return yaz


def _secimler(a, kat: Katalog):
    """(kutuphane | None, [zincirler]) ya da hata metni."""
    kutup = None if a.yalniz_zincir else kat.bul(a.kutuphane)
    if not a.yalniz_zincir and (kutup is None or kutup.tur != "kutuphane"):
        return _("bilinmeyen kütüphane: %s (--liste)") % a.kutuphane
    kimlikler = a.zincir or [o.kimlik for o in kat.zincirler if o.uygulamada_kullanilir]
    zincirler = [kat.bul(k) for k in kimlikler]
    if any(z is None or z.tur != "zincir" for z in zincirler):
        return _("bilinmeyen zincir: %s (--liste)") % ", ".join(kimlikler)
    return kutup, zincirler


def _bashrc(satirlar) -> None:
    yol = os.path.expanduser("~/.bashrc")
    isaret = "# OpenMC verisi (openmc_arayuz veri_indir)"
    mevcut = ""
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8") as f:
            mevcut = f.read()
    if isaret in mevcut:
        print(_("~/.bashrc'de zaten bir openmc_arayuz bölümü var; değiştirilmedi."))
        return
    with open(yol, "a", encoding="utf-8") as f:
        f.write("\n%s\n%s\n" % (isaret, "\n".join(satirlar)))
    print(_("~/.bashrc'ye eklendi. Yeni bir terminal açın ya da: source ~/.bashrc"))


def _etiket_yaz(kurulum) -> None:
    etiket = dogrulama_etiketi(kurulum)
    if etiket:
        print("   " + etiket)


def disa_aktarma_satirlari(xml: Optional[str], zincir: Optional[str]) -> List[str]:
    """~/.bashrc / terminal icin export satirlari (yollar shlex ile tirnakli)."""
    return (["export OPENMC_CROSS_SECTIONS=%s" % shlex.quote(xml)] if xml else []) + (
        ["export OPENMC_CHAIN_FILE=%s" % shlex.quote(zincir)] if zincir else [])


def _kur_hepsi(kutup, zincirler, hedef, kat, politika):
    """(cross_sections.xml | None, ayara yazilacak zincir | None)."""
    from cekirdek import veri_yolu
    yaz = _ilerleme_yazici()
    zincir_yollari = []
    for z in zincirler:
        print(_("== zincir: %s") % z.gorunen_ad())
        kurulum = zincir_kur(z, hedef, politika=politika, ilerleme=yaz)
        zincir_yollari.append(kurulum.yol)
        _etiket_yaz(kurulum)
    xml = None
    if kutup is not None:
        print(_("== kütüphane: %s (%.2f GB)") % (kutup.ad, kutup.bayt / veri_arsiv.GB))
        kurulum = kutuphane_kur(kutup, hedef, kat.oran, politika=politika, ilerleme=yaz)
        xml = kurulum.yol
        _etiket_yaz(kurulum)
    varsayilan = [y for y in zincir_yollari
                  if os.path.basename(y) == veri_yolu.VARSAYILAN_ZINCIR]
    return xml, (varsayilan or zincir_yollari or [None])[0]


def main(argv=None, katalog: Optional[Katalog] = None,
         politika: Optional[UrlPolitikasi] = None) -> int:
    """Cikis: 0 tamam, 1 indirme/kurma hatasi, 2 kullanim hatasi.
    katalog/politika yalniz Python'dan (test) verilir; komut satiri her zaman
    paket katalogunu ve uretim politikasini (yalniz https) kullanir."""
    from cekirdek import veri_yolu
    a = _argumanlar().parse_args(argv)
    kat = katalog or katalog_yukle()
    politika = politika or katalog_politikasi(kat)
    if a.liste:
        _liste(kat)
        return 0
    secim = _secimler(a, kat)
    if isinstance(secim, str):
        print(secim, file=sys.stderr)
        return 2
    try:
        hedef = veri_arsiv.hedef_dogrula(a.hedef or veri_yolu.varsayilan_indirme_hedefi())
        xml, zincir_yolu = _kur_hepsi(secim[0], secim[1], hedef, kat, politika)
    except VeriHatasi as e:
        print(_("HATA: %s") % e, file=sys.stderr)
        return 1
    ayar = {"indirme_hedefi": hedef, "zincir": zincir_yolu}
    if xml:
        ayar.update(cross_sections=xml, kutuphane=secim[0].kimlik)
    try:
        veri_yolu.ayar_yaz({k: v for k, v in ayar.items() if v})
    except (OSError, ValueError) as e:
        print(_("HATA: indirildi ama seçim kaydedilemedi: %s") % e, file=sys.stderr)
        return 1
    satirlar = disa_aktarma_satirlari(xml, zincir_yolu)
    print(_("\nBitti. Seçim uygulama ayarına yazıldı (%s).") % veri_yolu.ayar_yolu())
    if a.bashrc:
        _bashrc(satirlar)
    else:
        print(_("Terminalden openmc kullanacaksanız:\n%s") % "\n".join(satirlar))
    return 0


