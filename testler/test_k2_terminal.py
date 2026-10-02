# -*- coding: utf-8 -*-
"""
 test_k2_terminal.py  --  v3 K2 inceleme: terminal kosucusu ve alt surecler
                          cozulen nukleer veriyi (Veri sayfasi secimi) gorur

 OPENMC_CROSS_SECTIONS yokken ayardaki kutuphane: kosucu.calistir'in openmc
 alt sureci env'inde, giris.kosu() ve tukenme._terminal surec ortaminda olmali.
"""

import os
import subprocess

from testler.ortak_test import kontrol, ORNEK
from testler.k2_yalitim import VeriYalitimi


class _Durdur(Exception):
    pass


def _kutuphane(dizin):
    os.makedirs(os.path.join(dizin, "neutron"), exist_ok=True)
    open(os.path.join(dizin, "neutron", "H1.h5"), "w").close()
    xml = os.path.join(dizin, "cross_sections.xml")
    with open(xml, "w", encoding="utf-8") as f:
        f.write("<cross_sections><library materials='H1' path='neutron/H1.h5' "
                "type='neutron'/></cross_sections>")
    return xml


def test_kosucu_alt_sureci_secili_veriyi_alir():
    print("\n[K2-T1] kosucu.calistir: Popen env = veri_yolu.alt_surec_ortami() (ayardan)")
    from cekirdek import kosucu, sema, veri_yolu
    yakalanan = {}

    gercek = subprocess.Popen

    def sahte_popen(komut, **kw):
        if "cwd" not in kw:                  # baska bir alt surec (surum sorgusu): dokunma
            return gercek(komut, **kw)
        yakalanan.update(kw)
        raise _Durdur()
    with VeriYalitimi() as y:
        xml = _kutuphane(os.path.join(y.kok, "secilen"))
        veri_yolu.ayar_yaz({"cross_sections": xml})
        spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
        eski = kosucu.subprocess.Popen
        kosucu.subprocess.Popen = sahte_popen
        try:
            try:
                kosucu.calistir(spec, os.path.join(y.kok, "kosu"), dogrulama=False)
            except _Durdur:
                pass
        finally:
            kosucu.subprocess.Popen = eski
        env = yakalanan.get("env") or {}
        kontrol("env verildi", bool(env), repr(sorted(yakalanan)))
        kontrol("OPENMC_CROSS_SECTIONS ayardan", env.get("OPENMC_CROSS_SECTIONS") == xml,
                env.get("OPENMC_CROSS_SECTIONS"))
        kontrol("surec ortami degismedi", "OPENMC_CROSS_SECTIONS" not in os.environ)


def test_terminal_girisleri_surece_uygular():
    print("\n[K2-T2] giris.kosu() ve tukenme._terminal surece_uygula cagirir")
    from cekirdek import giris, kosucu, tukenme, veri_yolu
    gorulen = []
    with VeriYalitimi() as y:
        xml = _kutuphane(os.path.join(y.kok, "secilen"))
        veri_yolu.ayar_yaz({"cross_sections": xml})
        eski = kosucu._terminal
        kosucu._terminal = lambda argv: gorulen.append(
            os.environ.get("OPENMC_CROSS_SECTIONS")) or 0
        try:
            giris.kosu(["model.json"])
        finally:
            kosucu._terminal = eski
        kontrol("giris.kosu ortami kurdu", gorulen == [xml], repr(gorulen))
    with VeriYalitimi() as y:
        xml = _kutuphane(os.path.join(y.kok, "secilen"))
        veri_yolu.ayar_yaz({"cross_sections": xml})
        eski = tukenme.sema.yukle
        tukenme.sema.yukle = lambda yol: (_ for _ in ()).throw(_Durdur())
        try:
            try:
                tukenme._terminal(["yok.json"])
            except _Durdur:
                pass
        finally:
            tukenme.sema.yukle = eski
        kontrol("tukenme._terminal ortami kurdu",
                os.environ.get("OPENMC_CROSS_SECTIONS") == xml)


def test_alt_surec_gercek_ortam():
    print("\n[K2-T3] gercek alt surec: ayardaki kutuphane OPENMC_CROSS_SECTIONS olarak gorunur")
    import sys
    from cekirdek import veri_yolu
    from testler.ortak_test import KOK
    with VeriYalitimi() as y:
        xml = _kutuphane(os.path.join(y.kok, "secilen"))
        veri_yolu.ayar_yaz({"cross_sections": xml})
        r = subprocess.run([sys.executable, "-c", "import os;print(os.environ.get("
                            "'OPENMC_CROSS_SECTIONS'))"], capture_output=True, text=True,
                           env=veri_yolu.alt_surec_ortami(), timeout=60, cwd=KOK)
        kontrol("cocuk surec goruyor", r.stdout.strip() == xml, r.stdout)


HIZLI = [test_kosucu_alt_sureci_secili_veriyi_alir, test_terminal_girisleri_surece_uygular,
         test_alt_surec_gercek_ortam]
YAVAS = []
