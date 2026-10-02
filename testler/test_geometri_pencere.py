# -*- coding: utf-8 -*-
"""
 test_geometri_pencere.py  --  gercek ana pencere agac modundaki modeli acar

 Hata (G-2 + G-3 birlesmesi, 01.10.2026): G-3'un testleri agac modundaki
 spec'i yalniz kucuk bir ev sahibi pencerede sinadi; gercek AnaPencere
 _proje_kur ile agac modundaki modeli yuklerken arayuz cagiranlari
 (cubuk_formu, sekme_ayar, guc_harita ...) sema.kor_yuksekligi'ni cagirip
 AgacModuHatasi ile cokuyordu. Her sayfada kaydet / dogrula / onizleme
 istegi; sonda gercek onizleme cizimi ve kaydedilen dosyanin geri okunmasi.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

from testler.ortak_test import kontrol

SABLONLAR = (("pwr_ceyrek_kor", "kare_altigen"), ("sfr_altigen", "altigen_tambur"),
             ("pwr_ceyrek_kor", "kafes_tambur"))


def _sayfa_eylemleri(p, uyg, anahtar_s, hatalar):
    """Bir sayfada temel eylemler: kaydet, dogrula, onizleme yenile iste."""
    if not p.proje_kaydet():
        hatalar.append("%s: kaydedilemedi" % anahtar_s)
    p._dogrula()
    ic = [b.mesaj for b in p._bulgular if "doğrulama sırasında hata" in b.mesaj]
    if ic:
        hatalar.append("%s: %s" % (anahtar_s, ic[0]))
    p.onizleme.iste()
    uyg.processEvents()


def test_ana_pencere_agac_modunu_acar():
    print("\n[GP1] gercek ana pencere uc agac modu sablonunu acar, sayfalari gezer; "
          "her sayfada kaydet / dogrula / onizleme")
    import os
    import tempfile
    from PySide6 import QtWidgets
    from cekirdek import geometri, sema
    from arayuz.geometri import sablonlar
    from arayuz.pencere.ana_pencere import AnaPencere
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dizin = tempfile.mkdtemp(prefix="geo_pencere_")
    asil_kritik = QtWidgets.QMessageBox.critical
    kritik = []
    QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **k: kritik.append(a[1:3]))
    try:
        for ornek, anahtar in SABLONLAR:
            spec = sablonlar.uret(sema.yukle("ornekler/%s.json" % ornek), anahtar)
            yol = os.path.join(dizin, anahtar + ".json")
            p = AnaPencere()
            try:
                hata, eylem = None, []
                try:
                    p._proje_kur(spec, yol, None)
                    uyg.processEvents()
                    for anahtar_s in list(p._sayfalar):   # gizli sayfalar dahil hepsi
                        p.sekmeye_git(anahtar_s, sessiz=True)
                        uyg.processEvents()
                        _sayfa_eylemleri(p, uyg, anahtar_s, eylem)
                    # v3 H2: onizleme yalniz gorunurken cizer (tasarim sayfasi)
                    p.sekmeye_git("kor", sessiz=True)
                    p.onizleme._ciz()
                    p.onizleme.bekle(120)
                except Exception as e:      # testin amaci cokmeyi raporlamak
                    hata = "%s: %s" % (type(e).__name__, e)
                kontrol("%s: pencere agac modundaki modeli acti, butun sayfalari gezdi"
                        % anahtar, hata is None, "-> %s" % hata)
                kontrol("%s: her sayfada kaydet / dogrula hatasiz" % anahtar,
                        not eylem and not kritik, "-> %s %s" % (eylem[:3], kritik[:2]))
                cizim = p.onizleme.figur.axes and p.onizleme.figur.axes[0].images
                kontrol("%s: onizleme cizildi" % anahtar, p.onizleme.cizildi_mi() and bool(cizim),
                        "-> %s" % (p.onizleme.son_hata() or "")[-300:])
                geri = sema.yukle(yol) if os.path.exists(yol) else {}
                kontrol("%s: kaydedilen dosya agac modunda geri okunur" % anahtar,
                        geometri.agac_modu(geri) and geri.get("geometri") == p.spec.get("geometri"))
            finally:
                p._kirli = False
                p.close()
    finally:
        QtWidgets.QMessageBox.critical = asil_kritik


HIZLI = [test_ana_pencere_agac_modunu_acar]
YAVAS = []
