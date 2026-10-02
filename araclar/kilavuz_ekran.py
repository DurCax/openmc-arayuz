# -*- coding: utf-8 -*-
"""
kilavuz_ekran.py -- kullanim kilavuzunun ekran goruntuleri (offscreen, dil
parametreli). Kilavuz metni bu adlara baglanir: docs/kilavuz/<dil>/*.md ->
../resimler/<dil>/<ad>.png.

    python araclar/kilavuz_ekran.py --dil tr        # docs/kilavuz/resimler/tr/
    python araclar/kilavuz_ekran.py --dil en        # Ajan 12 (EN arayuz) sonrasi
    python araclar/kilavuz_ekran.py --dil tr --yalniz analiz --yalniz tukenme

Basliksiz calisir (QT_QPA_PLATFORM=offscreen kendiliginden). Kullanicinin
gercek QSettings'i degismez (gecici dizine yonlendirilir). Acik tema,
1280x800 pencere; PNG 256 renkli paletle ve en yuksek sikistirmayla yazilir.

MANIFEST (ekranlar.json, resimlerin yaninda): her ekranin ornegi, sekmesi,
boyutu ve sha256'si + girdi_ozeti: bu betigin, arayuz/ kaynak kodunun,
kullanilan orneklerin ve dilin sha256 ozeti. testler/test_kilavuz.py (KL6)
ozeti yeniden hesaplar; farkliysa goruntulerin eskidigini UYARI olarak yazar
(kati kapi degil: pikseller makineden makineye degisir).
"""

import argparse
import glob
import hashlib
import json
import os
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)
RESIM_DIZINI = os.path.join(KOK, "docs", "kilavuz", "resimler")
MANIFEST = "ekranlar.json"
DILLER = ("tr", "en")
BOYUT = (1280, 800)
PNG_KALITESI = 0                  # Qt: PNG icin 0 = en yuksek sikistirma
_EN_AZ_BEKLEME = 0.6              # s; onizleme zamanlayicisi + cizim
_EN_COK_BEKLEME = 20.0

# ad -> (ornek, sekme anahtari). sekme None: baslangic ekrani; "kilavuz": kilavuz penceresi.
EKRANLAR = (
    {"ad": "baslangic", "ornek": None, "sekme": None},
    {"ad": "ilk-hesap-malzemeler", "ornek": "pwr_17x17.json", "sekme": "malzemeler"},
    {"ad": "ilk-hesap-parcalar", "ornek": "pwr_17x17.json", "sekme": "parcalar"},
    {"ad": "ilk-hesap-demet", "ornek": "pwr_17x17.json", "sekme": "demet"},
    {"ad": "ilk-hesap-geometri", "ornek": "pwr_17x17.json", "sekme": "kor"},
    {"ad": "ilk-hesap-hesap-ayarlari", "ornek": "pwr_17x17.json", "sekme": "ayarlar"},
    {"ad": "ilk-hesap-calistir", "ornek": "pwr_17x17.json", "sekme": "calistir"},
    {"ad": "analiz", "ornek": "pwr_17x17.json", "sekme": "analiz"},
    {"ad": "geometri-altigen-kor", "ornek": "vver1000_kor.json", "sekme": "kor"},
    {"ad": "geometri-gelismis", "ornek": "pwr_kare_altigen_halka.json", "sekme": "kor"},
    {"ad": "geometri-tambur", "ornek": "kafes_tamburlu_yansitici.json", "sekme": "kor"},
    {"ad": "tukenme", "ornek": "pwr_tukenme.json", "sekme": "tukenme"},
    {"ad": "kilavuz", "ornek": None, "sekme": "kilavuz", "bolum": "geometri"},
)


def _dosya_ozeti(ozet, yol):
    ozet.update(os.path.relpath(yol, KOK).replace(os.sep, "/").encode("utf-8"))
    with open(yol, "rb") as f:
        ozet.update(hashlib.sha256(f.read()).digest())


def girdi_ozeti(dil):
    """Goruntuleri belirleyen girdilerin sha256 ozeti (betik, arayuz/, ornekler, dil)."""
    ozet = hashlib.sha256(("dil=%s;boyut=%dx%d" % ((dil,) + BOYUT)).encode("utf-8"))
    _dosya_ozeti(ozet, os.path.abspath(__file__))
    for yol in sorted(glob.glob(os.path.join(KOK, "arayuz", "**", "*.py"), recursive=True)):
        _dosya_ozeti(ozet, yol)
    for ornek in sorted({e["ornek"] for e in EKRANLAR if e["ornek"]}):
        _dosya_ozeti(ozet, os.path.join(KOK, "ornekler", ornek))
    katalog = os.path.join(KOK, "locale", dil, "LC_MESSAGES", "openmc_arayuz.mo")
    if os.path.exists(katalog):
        _dosya_ozeti(ozet, katalog)
    return ozet.hexdigest()


# ----------------------------------------------------------------------------
def _ayarlari_yalit():
    from PySide6 import QtCore
    dizin = tempfile.mkdtemp(prefix="openmc_arayuz_ayar_")
    os.environ["XDG_CONFIG_HOME"] = dizin
    for bicim in (QtCore.QSettings.NativeFormat, QtCore.QSettings.IniFormat):
        QtCore.QSettings.setPath(bicim, QtCore.QSettings.UserScope, dizin)
    return dizin


def _bekle(app, pencere=None):
    """Olay dongusunu onizleme zamanlayicisi bitene dek (en cok _EN_COK_BEKLEME) dondurur."""
    bas = time.monotonic()
    while True:
        app.processEvents()
        gecen = time.monotonic() - bas
        onizleme = getattr(pencere, "onizleme", None)
        mesgul = onizleme is not None and onizleme.mesgul_mu()   # gecikme + arka plan cizimi
        if gecen > _EN_COK_BEKLEME or (gecen > _EN_AZ_BEKLEME and not mesgul):
            break
        time.sleep(0.05)
    app.processEvents()


def _bildirimleri_kapat(widget):
    """Ornek acilisinin "kopya olarak acildi" bildirimleri goruntuye girmesin."""
    from arayuz.bilesenler.bildirim import Bildirim
    for b in widget.findChildren(Bildirim):
        b.hide()
        b.deleteLater()


def _kaydet(widget, yol):
    from PySide6 import QtCore, QtGui
    _bildirimleri_kapat(widget)
    # 256 renkli paletle (titremesiz): arayuz goruntusunde kayip gozle secilmez,
    # dosya ~5 kat kucuk (olculdu: 182 kB -> 38 kB).
    resim = widget.grab().toImage().convertToFormat(
        QtGui.QImage.Format_Indexed8,
        QtCore.Qt.AutoColor | QtCore.Qt.ThresholdDither | QtCore.Qt.AvoidDither)
    if not resim.save(yol, "PNG", PNG_KALITESI):
        raise OSError("ekran goruntusu yazilamadi: %s" % yol)
    with open(yol, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return {"boyut": [resim.width(), resim.height()], "sha256": sha}


def _ekran(app, pencere, e, hedef):
    from arayuz import yardim
    from arayuz.yardim import gosterici
    yol = os.path.join(hedef, e["ad"] + ".png")
    if e["sekme"] == "kilavuz":
        if not yardim.ac(e.get("bolum", "giris"), pencere):
            raise RuntimeError("kilavuz acilamadi")
        g = gosterici.etkin_gosterici()
        g.resize(*BOYUT)
        _bekle(app)
        yardim.ac(e.get("bolum", "giris"), pencere)
        _bekle(app)
        kayit = _kaydet(g, yol)
        g.close()
        return kayit
    if e["ornek"] and getattr(pencere, "_kilavuz_ornegi", None) != e["ornek"]:
        if not pencere.proje_ac(os.path.join(KOK, "ornekler", e["ornek"])):
            raise OSError("ornek acilamadi: %s" % e["ornek"])
        pencere._kilavuz_ornegi = e["ornek"]
        _bekle(app, pencere)
    if e["ornek"] and not pencere.sekmeye_git(e["sekme"], sessiz=True):
        raise RuntimeError("%s: sekme gorunmuyor: %s" % (e["ornek"], e["sekme"]))
    _bekle(app, pencere)
    return _kaydet(pencere, yol)


def cek(dil, yalniz=()):
    """Ekranlari ceker, manifesti yazar; yazilan PNG yollari."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _ayarlari_yalit()
    from PySide6 import QtCore, QtWidgets
    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    from cekirdek import ceviri
    ceviri.dil_ayarla(dil)
    from arayuz import ana_pencere, ortak, tema
    ortak.tekerlek_korumasi_kur(app)
    tema.uygula(app, "acik")
    hedef = os.path.join(RESIM_DIZINI, dil)
    os.makedirs(hedef, exist_ok=True)
    manifest_yolu = os.path.join(hedef, MANIFEST)
    ekranlar = {}
    if yalniz and os.path.exists(manifest_yolu):
        with open(manifest_yolu, encoding="utf-8") as f:
            ekranlar = json.load(f).get("ekranlar", {})
    pencere = ana_pencere.AnaPencere()
    pencere._kaydetme_sor = lambda: True
    pencere.resize(*BOYUT)
    pencere.show()
    _bekle(app, pencere)
    yazilan = []
    try:
        for e in EKRANLAR:
            if yalniz and e["ad"] not in yalniz:
                continue
            kayit = _ekran(app, pencere, e, hedef)
            ekranlar[e["ad"]] = dict(kayit, ornek=e["ornek"], sekme=e["sekme"])
            yazilan.append(os.path.join(hedef, e["ad"] + ".png"))
            print("  %s.png  %dx%d" % (e["ad"], kayit["boyut"][0], kayit["boyut"][1]))
    finally:
        pencere.s_tukenme.bekle()
        pencere._kirli = False
        pencere.close()
        pencere.deleteLater()
        app.processEvents()
    with open(manifest_yolu, "w", encoding="utf-8") as f:
        json.dump({"dil": dil, "girdi_ozeti": girdi_ozeti(dil), "boyut": list(BOYUT),
                   "ekranlar": ekranlar}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    return yazilan


def main(argv=None):
    a = argparse.ArgumentParser(description="Kullanım kılavuzu ekran görüntüleri (offscreen)")
    a.add_argument("--dil", choices=DILLER, required=True, help="arayüz ve kılavuz dili")
    a.add_argument("--yalniz", action="append", default=[], help="yalnız bu ekran(lar)")
    arg = a.parse_args(argv)
    bilinmeyen = set(arg.yalniz) - {e["ad"] for e in EKRANLAR}
    if bilinmeyen:
        print("bilinmeyen ekran: %s" % ", ".join(sorted(bilinmeyen)), file=sys.stderr)
        return 2
    yollar = cek(arg.dil, tuple(arg.yalniz))
    print("%d ekran -> %s" % (len(yollar), os.path.join(RESIM_DIZINI, arg.dil)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
