# -*- coding: utf-8 -*-
"""
================================================================================
 guc_harita.py  --  Cubuk bazli guc dagilimi isi haritasi
================================================================================
 Kare kafeste izgara, altigen kafeste gercek altigen yerlesim. Altigen konumlar
 cekirdek/altigen.py'den gelir -- yani harita, modelde kullanilan AYNI kaynagi
 kullanir; ayri bir cizim mantigi yoktur.

 3B modelde eksenel dilim kaydiricisi ve eksenel guc profili de gosterilir.
================================================================================
"""

import math

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.patches import RegularPolygon

from PySide6 import QtCore, QtWidgets

from cekirdek import altigen, sema, guc as _guc


def _aktif_yukseklik(spec):
    """Lineer guc icin AKTIF yakit yuksekligi (yansitici/plenum haric)."""
    try:
        from cekirdek import kurucu
        ar = kurucu.aktif_eksenel_aralik(spec)
        return (ar[1] - ar[0]) if ar else None
    except Exception:
        return sema.kor_yuksekligi(spec.get("kor") or {})
from arayuz.ortak import baslik, ipucu


class GucHaritaWidget(QtWidgets.QWidget):
    """Guc dagilimi haritasi ve tepe faktorleri."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dagilim = None
        self.faktorler = None
        self.mutlak = None

        # --- denetimler ---
        self.gorunum = QtWidgets.QComboBox()
        self.gorunum.addItem("Cubuk toplam gucu (F_dH)", "toplam")
        self.gorunum.addItem("Tek eksenel dilim (F_q)", "dilim")
        self.dilim = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.dilim.setMinimum(1); self.dilim.setMaximum(1); self.dilim.setValue(1)
        self.dilim_etiket = QtWidgets.QLabel("dilim 1")
        self.degerler = QtWidgets.QCheckBox("Degerleri yaz")
        self.d_kaydet = QtWidgets.QPushButton("PNG kaydet...")

        self.gorunum.currentIndexChanged.connect(self._ciz)
        self.dilim.valueChanged.connect(self._ciz)
        self.degerler.toggled.connect(self._ciz)
        self.d_kaydet.clicked.connect(self._kaydet)

        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(QtWidgets.QLabel("Gorunum:"))
        ust.addWidget(self.gorunum)
        ust.addWidget(self.dilim_etiket)
        ust.addWidget(self.dilim, 1)
        ust.addWidget(self.degerler)
        ust.addWidget(self.d_kaydet)

        # --- ozet ---
        self.ozet = QtWidgets.QLabel("Henuz guc dagilimi hesaplanmadi.")
        self.ozet.setWordWrap(True)
        self.ozet.setTextFormat(QtCore.Qt.RichText)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ozet.setStyleSheet(
            "background: palette(alternate-base); padding: 10px; "
            "border: 1px solid palette(mid); border-radius: 8px;")

        # --- tuval ---
        self.figur = Figure(figsize=(6, 4), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.arac = NavigationToolbar2QT(self.tuval, self)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Cubuk bazli guc dagilimi"))
        duzen.addWidget(ipucu(
            "F_dH = maks cubuk gucu / ortalama (radyal). "
            "F_q = maks yerel guc yogunlugu / ortalama (radyal x eksenel, 3B gerekir). "
            "Renk olcegi ORTALAMAYA gore bagildir: 1.00 = ortalama cubuk."))
        duzen.addLayout(ust)
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(self.arac)
        self._bos("Henuz kosu yapilmadi")

    # ==================================================================
    def sonuc_ayarla(self, sonuc, spec=None):
        """kosucu.sonuc_oku() ciktisindan guc bolumunu alir."""
        g = (sonuc or {}).get("guc") or {}
        self.dagilim = g.get("dagilim")
        self.faktorler = g.get("faktorler")
        self.korunum = g.get("korunum")
        self.mutlak = None
        if self.faktorler and spec:
            sg = spec.get("guc_dagilimi") or {}
            self.mutlak = _guc.mutlak_guc(self.faktorler, sg.get("toplam_guc"),
                                          _aktif_yukseklik(spec))
        if self.faktorler:
            n = self.faktorler["eksenel_dilim"]
            self.dilim.setMaximum(max(n, 1))
            self.dilim.setValue(max(1, n // 2 + 1))
            uc_boyut = n > 1
            for w in (self.dilim, self.dilim_etiket):
                w.setVisible(uc_boyut)
            self.gorunum.model().item(1).setEnabled(uc_boyut)
            if not uc_boyut:
                self.gorunum.setCurrentIndex(0)
        self._ozet_yaz()
        self._ciz()

    def _bos(self, metin):
        self.figur.clear()
        eks = self.figur.add_subplot(111)
        eks.set_axis_off()
        eks.text(0.5, 0.5, metin, ha="center", va="center",
                 fontsize=10, color="#7f8c8d")
        self.tuval.draw_idle()

    def _ozet_yaz(self):
        if not self.faktorler:
            self.ozet.setText("Henuz guc dagilimi hesaplanmadi. "
                              "5. sekmede 'Guc dagilimi'ni acin ve kosun.")
            return
        f = self.faktorler
        p = ["<b>F_&Delta;H = %.4f</b>" % f["F_dH"]]
        if f["F_q"]:
            p.append("<b>F_q = %.4f</b>" % f["F_q"])
        p.append("%d cubuk, %d eksenel dilim" % (f["cubuk_sayisi"], f["eksenel_dilim"]))
        p.append("sicak cubuk %s" % (f["sicak_cubuk"],))
        if f["sicak_dilim"]:
            p.append("sicak dilim %d" % (f["sicak_dilim"][1] + 1))
        metin = " &nbsp;|&nbsp; ".join(p)
        if self.korunum is not None:
            iyi = self.korunum < 1e-6
            metin += ("<br><span style='color:%s'>toplam korunumu: bagil fark "
                      "%.1e %s</span>"
                      % ("#1e6b3a" if iyi else "#8b1a1a", self.korunum,
                         "OK" if iyi else "BOZUK -- haritaya guvenmeyin"))
        satirlar = _guc.yorumla(f, self.mutlak)
        metin += "<br><br>" + "<br>".join("&bull; " + s.strip() for s in satirlar)
        self.ozet.setText(metin)

    # ==================================================================
    def _veri(self):
        """Secili goruntuye gore {konum: bagil_deger} dondurur."""
        f = self.faktorler
        if self.gorunum.currentData() == "dilim" and f["bagil_eksenel"]:
            i = self.dilim.value() - 1
            return {a: v[i][0] for a, v in f["bagil_eksenel"].items()}, \
                   "dilim %d / %d" % (i + 1, f["eksenel_dilim"])
        return {a: v[0] for a, v in f["bagil"].items()}, "cubuk toplami"

    def _ciz(self):
        if not self.faktorler or not self.dagilim:
            self._bos("Henuz guc dagilimi hesaplanmadi")
            return
        f = self.faktorler
        self.dilim_etiket.setText("dilim %d" % self.dilim.value())
        veri, alt_baslik = self._veri()

        self.figur.clear()
        uc_boyut = f["eksenel_dilim"] > 1
        if uc_boyut:
            eks = self.figur.add_subplot(1, 2, 1)
            eks_p = self.figur.add_subplot(1, 2, 2)
        else:
            eks = self.figur.add_subplot(111)
            eks_p = None

        if self.dagilim["kafes_turu"] == "altigen":
            self._ciz_altigen(eks, veri)
        else:
            self._ciz_kare(eks, veri)
        eks.set_title("Bagil guc -- %s" % alt_baslik, fontsize=9)

        if eks_p is not None and f["eksenel_profil"]:
            y = [p[0] for p in f["eksenel_profil"]]
            x = list(range(1, len(y) + 1))
            eks_p.plot(y, x, "o-", ms=3, lw=1.2, color="#2c3e50")
            eks_p.axvline(1.0, color="#95a5a6", ls="--", lw=0.8)
            if self.gorunum.currentData() == "dilim":
                eks_p.axhline(self.dilim.value(), color="#c0392b", ls="-", lw=1.2)
            eks_p.set_xlabel("bagil guc", fontsize=8)
            eks_p.set_ylabel("eksenel dilim", fontsize=8)
            eks_p.tick_params(labelsize=7)
            eks_p.grid(alpha=0.3)
            eks_p.set_title("Eksenel profil", fontsize=9)
        self.tuval.draw_idle()

    def _renk_olcegi(self, veri):
        d = list(veri.values())
        return (min(d), max(d)) if d else (0.0, 1.0)

    def _ciz_kare(self, eks, veri):
        import numpy as np
        xs = [a[0] for a in veri]; ys = [a[1] for a in veri]
        nx, ny = max(xs) + 1, max(ys) + 1
        izgara = np.full((ny, nx), np.nan)
        for (x, y), v in veri.items():
            izgara[y, x] = v
        alt, ust = self._renk_olcegi(veri)
        im = eks.imshow(izgara, origin="lower", cmap="inferno",
                        vmin=alt, vmax=ust, interpolation="nearest")
        self.figur.colorbar(im, ax=eks, fraction=0.046, label="bagil guc")
        sicak = self.faktorler["sicak_cubuk"]
        eks.plot(sicak[0], sicak[1], marker="o", ms=11, mfc="none",
                 mec="#00e5ff", mew=2.0, label="en sicak")
        eks.legend(fontsize=7, loc="upper right")
        eks.set_xlabel("kafes x", fontsize=8); eks.set_ylabel("kafes y", fontsize=8)
        eks.tick_params(labelsize=7)
        if self.degerler.isChecked() and nx * ny <= 400:
            for (x, y), v in veri.items():
                eks.text(x, y, "%.2f" % v, ha="center", va="center", fontsize=5,
                         color="white" if v < (alt + ust) / 2 else "black")

    def _ciz_altigen(self, eks, veri):
        kafes = self.dagilim["kafes"]
        halka = kafes.num_rings
        yonelim = getattr(kafes, "orientation", "y")
        konum = altigen.konumlar(halka, yonelim)
        alt, ust = self._renk_olcegi(veri)
        renk_es = matplotlib.cm.get_cmap("inferno") if hasattr(matplotlib.cm, "get_cmap") \
            else matplotlib.colormaps["inferno"]
        norm = matplotlib.colors.Normalize(vmin=alt, vmax=ust)
        # hucre koseleri: kafes yonelimine gore (cekirdek/altigen ile ayni kural)
        kose_aci = altigen.hucre_kose_acilari(yonelim)[0]
        yaricap = 1.0 / math.sqrt(3.0)
        for anahtar, v in veri.items():
            if anahtar not in konum:
                continue
            x, y = konum[anahtar]
            eks.add_patch(RegularPolygon(
                (x, y), numVertices=6, radius=yaricap,
                orientation=math.radians(kose_aci - 30.0),
                facecolor=renk_es(norm(v)), edgecolor="#444444", linewidth=0.4))
            if self.degerler.isChecked() and len(veri) <= 200:
                eks.text(x, y, "%.2f" % v, ha="center", va="center", fontsize=5,
                         color="white" if v < (alt + ust) / 2 else "black")
        sicak = self.faktorler["sicak_cubuk"]
        if sicak in konum:
            sx, sy = konum[sicak]
            eks.plot(sx, sy, marker="o", ms=11, mfc="none", mec="#00e5ff",
                     mew=2.0, label="en sicak")
            eks.legend(fontsize=7, loc="upper right")
        tum = list(konum.values())
        pay = yaricap * 1.5
        eks.set_xlim(min(p[0] for p in tum) - pay, max(p[0] for p in tum) + pay)
        eks.set_ylim(min(p[1] for p in tum) - pay, max(p[1] for p in tum) + pay)
        eks.set_aspect("equal")
        eks.set_xlabel("adim birimi", fontsize=8)
        eks.tick_params(labelsize=7)
        self.figur.colorbar(
            matplotlib.cm.ScalarMappable(norm=norm, cmap="inferno"),
            ax=eks, fraction=0.046, label="bagil guc")

    def _kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Guc haritasini kaydet", "guc_haritasi.png", "PNG (*.png)")
        if yol:
            self.figur.savefig(yol, dpi=150, bbox_inches="tight")
