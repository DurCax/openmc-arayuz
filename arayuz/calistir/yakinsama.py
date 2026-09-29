# -*- coding: utf-8 -*-
"""
yakinsama.py -- Calistir sayfasinin iki grafik karti (maket: sonuclar_*).

    YakinsamaKarti : cevrim basina k ve etkin ortalama ± 1 sigma
    EntropiKarti   : Shannon entropisi (kapaliysa bos durum metni)

Ikisi de canli kosu sirasinda ayni `cevrimler` listesinden cizer:
    [{"cevrim": n, "k": float, "ortalama": float|None, "sapma": float|None,
      "entropi": float|None}, ...]   (kosucu.cevrim_satiri ciktisi)

Renkler tema tokenlarindan (tema.renk / tema.grafik_paleti) gelir.
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtWidgets

from arayuz import bilesenler as b
from arayuz import tema
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
_EN_AZ_YUKSEKLIK = 190


class GrafikKarti(b.Kart):
    """Matplotlib tuvali tasiyan kart (+ "PNG kaydet" eylemi)."""

    def __init__(self, baslik, aciklama=None, yukseklik=_EN_AZ_YUKSEKLIK, parent=None):
        self.d_kaydet = b.ikon_dugmesi("download", _("Grafiği PNG olarak kaydet"))
        super().__init__(baslik, aciklama, eylem=self.d_kaydet, parent=parent)
        self.figur = Figure(figsize=(5, 2.6), dpi=100, layout="constrained")
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.tuval.setMinimumHeight(yukseklik)
        # Tuvalin sizeHint'i mevcut boyutudur; yerlesim onu dikkate alirsa sayfa
        # her cizimde biraz daha buyur ve kaydirma cubugu cikar.
        self.tuval.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                 QtWidgets.QSizePolicy.Ignored)
        self.eksen = self.figur.add_subplot(111)
        self.ekle(self.tuval, 1)
        self.d_kaydet.clicked.connect(self.kaydet)

    # ------------------------------------------------------------------
    def eksenleri_hazirla(self, y_etiketi):
        self.eksen.clear()
        self.eksen.set_ylabel(y_etiketi, fontsize=8)
        self.eksen.set_xlabel(_("çevrim"), fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.eksen.grid(True, alpha=0.3, lw=0.6)

    def bos_yaz(self, metin):
        """Veri yokken tuvalde ortalanmis aciklama (bos durum)."""
        self.eksen.clear()
        self.eksen.set_axis_off()
        self.eksen.text(0.5, 0.5, metin, ha="center", va="center", wrap=True,
                        fontsize=9, color=tema.renk("metin_soluk"))
        self.tuval.draw_idle()

    def dosya_sor(self, varsayilan):
        """Kaydetme yolu (testler bunu degistirir; modal acilmaz)."""
        yol, _secilen = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Grafiği kaydet"), varsayilan, "PNG (*.png)")
        return yol

    def kaydet(self):
        yol = self.dosya_sor("yakinsama.png")
        if not yol:
            return None
        try:
            self.figur.savefig(yol, dpi=150,
                               facecolor=self.figur.get_facecolor())
        except OSError as hata:
            _log.exception("grafik kaydedilemedi: %s", yol)
            QtWidgets.QMessageBox.warning(self, _("Kaydedilemedi"), str(hata))
            return None
        return yol


class YakinsamaKarti(GrafikKarti):
    """Cevrim basina k-eff ve etkin (kumulatif) ortalama ± 1 sigma."""

    def __init__(self, parent=None):
        super().__init__(_("Yakınsama"), _("Çevrim başına k ve etkin ortalama ± 1σ"),
                         parent=parent)
        self.sifirla()

    def sifirla(self):
        self.eksenleri_hazirla("k-eff")
        self.tuval.draw_idle()

    def ciz(self, cevrimler, pasif=0):
        if not cevrimler:
            self.sifirla()
            return
        palet = tema.grafik_paleti()
        self.eksenleri_hazirla("k-eff")
        self.eksen.plot([c["cevrim"] for c in cevrimler], [c["k"] for c in cevrimler],
                        lw=0.8, alpha=0.5, color=palet[0], label=_("k (çevrim)"))
        ort = [(c["cevrim"], c["ortalama"], c["sapma"]) for c in cevrimler
               if c.get("ortalama") is not None]
        if ort:
            x = [a for a, _b, _c in ort]
            y = [b for _a, b, _c in ort]
            s = [c or 0.0 for _a, _b, c in ort]
            self.eksen.plot(x, y, lw=1.6, color=palet[1], label=_("k ort."))
            self.eksen.fill_between(x, [a - b for a, b in zip(y, s)],
                                    [a + b for a, b in zip(y, s)],
                                    color=palet[1], alpha=0.18, lw=0)
        if pasif:
            self._pasif_cizgisi(pasif, _(" etkin çevrimler"))
        self.eksen.legend(fontsize=7, loc="best")
        self.tuval.draw_idle()

    def _pasif_cizgisi(self, pasif, etiket):
        self.eksen.axvline(pasif + 0.5, lw=1.0, ls="--", color=tema.renk("metin_soluk"))
        self.eksen.text(pasif + 0.5, self.eksen.get_ylim()[1], etiket, va="top",
                        fontsize=7, color=tema.renk("metin_soluk"))


class EntropiKarti(GrafikKarti):
    """Shannon entropisi; kapaliysa neden yazilir (bos durum)."""

    def __init__(self, parent=None):
        super().__init__(_("Kaynak entropisi"), _("Kaynak dağılımının yakınsaması"),
                         parent=parent)
        self.sifirla()

    def sifirla(self):
        self.bos_yaz(_("Shannon entropisi kapalı"))

    def ciz(self, cevrimler, pasif=0):
        veri = [(c["cevrim"], c["entropi"]) for c in (cevrimler or [])
                if c.get("entropi") is not None]
        if not veri:
            self.bos_yaz(_("Henüz entropi verisi yok"))
            return
        self.eksen.set_axis_on()
        self.eksenleri_hazirla("H (bit)")
        self.eksen.plot([a for a, _b in veri], [b for _a, b in veri],
                        lw=1.2, color=tema.grafik_paleti()[0])
        if pasif:
            self.eksen.axvline(pasif + 0.5, lw=1.0, ls="--", alpha=0.7,
                               color=tema.renk("metin_soluk"))
        self.tuval.draw_idle()
