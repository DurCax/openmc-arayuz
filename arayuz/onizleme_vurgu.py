# -*- coding: utf-8 -*-
"""
onizleme_vurgu.py -- onizleme widget'inin gelismis geometri katmani (Dalga G-3):
sol tik noktadaki hucreyi openmc.Geometry.find ile bulur, GeometriDizini onu
agactaki dugume cevirir (dugum_secildi); vurgula(yol) secili dugumu vurgular.
arayuz/onizleme.py'den bolundu (v3 K5; davranis degismedi). Kapsamli (alt
model) cizimde tiklama ve vurgu kapalidir: id haritasi tam modelin degildir.
"""

from cekirdek import onbellek
from cekirdek.gunluk import kaydedici
from arayuz import tema

_log = kaydedici("arayuz.onizleme")
_SOLUK_ORTU = 0.6                 # secili olmayan bolgenin soluk ortusu (saydamlik)


def _rgb01(ad):
    from matplotlib.colors import to_rgb
    return to_rgb(tema.renk(ad))


class VurguMixin(object):
    """OnizlemeWidget'a karisir: tiklama -> dugum, secili dugum vurgusu."""

    def vurgula(self, yol):
        """Secili dugum (Geometri sayfasi). Yeniden cizim ister."""
        self._vurgu = tuple(yol) if yol else None
        if self.spec is not None:
            self.iste()

    def _model(self):
        """Ana surecteki (onbellekli) model: yalniz vurgu ve tiklama icin."""
        try:
            model, bilgi = onbellek.kur_onbellekli(self.spec)
        except Exception:                   # cizim hatasi iscide ayrica bildirilir
            _log.info("onizleme modeli ana surecte kurulamadi", exc_info=True)
            return None, None
        return model, bilgi

    def _vurgu_renkleri(self):
        """Hucre renklendirmesinde (renkler {hucre id: RGB}, soluk RGB) ya da (None, None)."""
        if not self._vurgu:
            return None, None
        model, bilgi = self._model()
        if model is None:
            return None, None
        from arayuz.geometri.onizleme_secim import vurgu_renkleri
        vurgu = tuple(int(255 * v) for v in _rgb01("vurgu"))
        soluk = tuple(int(255 * v) for v in _rgb01("yuzey3"))
        renkler = vurgu_renkleri(model, bilgi.get("geometri_dizini"), self._agac(),
                                 self._vurgu, vurgu, soluk) or {}
        return {h.id: r for h, r in renkler.items()}, soluk

    def _malzeme_vurgusu(self, ax, geom, kapsam):
        """Malzeme renklendirmesinde secili dugum: soluk ortu + vurgu kontur."""
        if not self._vurgu:
            return
        import numpy as np
        from arayuz.geometri.onizleme_secim import secili_hucreler, vurgu_maskesi
        model, bilgi = self._model()
        if model is None:
            return
        secili = secili_hucreler(model, bilgi.get("geometri_dizini"), self._agac(), self._vurgu)
        if not secili:
            return
        maske = vurgu_maskesi(model, geom, secili)
        ortu = np.zeros(maske.shape + (4,))
        ortu[..., :3] = _rgb01("yuzey3")
        ortu[..., 3] = np.where(maske, 0.0, _SOLUK_ORTU)
        ax.imshow(ortu, extent=kapsam, interpolation="nearest", zorder=2).set_gid("vurgu")
        if maske.any() and not maske.all():
            kontur = ax.contour(maske.astype(float), levels=[0.5], extent=kapsam,
                                origin="upper", colors=[tema.renk("vurgu")],
                                linewidths=1.6, zorder=3)
            kontur.set_gid("vurgu")

    def _agac(self):
        from cekirdek import geometri
        try:
            return geometri.genislet(self.spec)
        except Exception:
            _log.info("onizleme agaci kurulamadi", exc_info=True)
            return {}

    def nokta_sec(self, eksen, a, b):
        """Kesit duzlemindeki (a, b) noktasinin dugum yolu; bulunursa yayar."""
        if not self._son_eksenler:
            return None
        from arayuz.geometri.onizleme_secim import nokta_yolu
        nokta = {"xy": (a, b, 0.0), "xz": (a, 0.0, b), "yz": (0.0, a, b)}.get(eksen)
        if nokta is None:
            return None
        model, bilgi = self._model()
        if model is None:
            return None
        yol = nokta_yolu(model, bilgi.get("geometri_dizini"), self._agac(), nokta)
        if yol is not None:
            self.dugum_secildi.emit(yol)
        return yol

    def _tiklandi(self, olay):
        if olay.button != 1 or olay.inaxes is None or olay.xdata is None:
            return
        if getattr(self.arac_cubugu, "mode", ""):
            return                        # kaydirma / yakinlastirma araci acik
        for eksen, ax in self._son_eksenler:
            if ax is olay.inaxes:
                self.nokta_sec(eksen, olay.xdata, olay.ydata)
                return

