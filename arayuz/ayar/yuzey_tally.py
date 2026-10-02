# -*- coding: utf-8 -*-
"""
 arayuz/ayar/yuzey_tally.py  --  YuzeyTallyMixin: tally formunda "Tür" (Y7)

 Hacim tally'si (eski davranis) ya da yuzey akimi: model siniri (kacak;
 SurfaceFilter vakum yuzeyleri) veya kutu agi (giren/cikan; MeshSurfaceFilter).
 Yuzey turunde skor yalniz 'current' (OpenMC kurali), enerji filtresi kalir
 (kacak spektrumu), malzeme/mesh filtreleri kaldirilir (dogrula/yuzey.py).
 Tanimlar cekirdek/yuzey_akim.py'den; TallyFormuMixin uc kanca satiriyla
 cagirir (_yuzey_doldur, _yuzey_gorunurluk, _yuzey_kaydet).
"""

from PySide6 import QtWidgets

from arayuz.ortak import ipucu, tamsayi
from cekirdek import sema, yuzey_akim as _y
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

HACIM = ""
_TURLER = ((HACIM, N_("Hacim (akı, tepkime)")),
           (_y.FILTRE_SINIR, N_("Yüzey: model sınırı (kaçak)")),
           (_y.FILTRE_KUTU, N_("Yüzey: kutu ağı (giren / çıkan)")))
_EN_COK_BOLME = 1000
_VARSAYILAN_ENERJI = [0.0, 0.625, 2.0e7]


class YuzeyTallyMixin(object):
    """Tally formuna yuzey turu, kutu bolmeleri ve sinirlari."""

    def _yuzey_satirlari_ekle(self, t_form):
        self.t_tur = QtWidgets.QComboBox()
        for veri, ad in _TURLER:
            self.t_tur.addItem(_(ad), veri)
        self.t_tur.setToolTip(_(
            "Hacim: bölgedeki akı ve tepkime hızları.\n"
            "Model sınırı: vakum sınırından kaçan parçacıklar (yüzey başına).\n"
            "Kutu ağı: ağ hücrelerinin yüzlerinden giren ve çıkan kısmi akımlar ve\n"
            "nötron dengesi (giren − çıkan + kaynak + üretim = soğurma)."))
        self.t_kutu_nx, self.t_kutu_ny, self.t_kutu_nz = (
            tamsayi(1, 1, _EN_COK_BOLME) for _i in range(3))
        self.kutu_satiri = self._uclu((("nx", self.t_kutu_nx), ("ny", self.t_kutu_ny),
                                       ("nz", self.t_kutu_nz)))
        self.t_kutu_alt, self.t_kutu_ust = QtWidgets.QLineEdit(), QtWidgets.QLineEdit()
        for w in (self.t_kutu_alt, self.t_kutu_ust):
            w.setPlaceholderText(_("otomatik (model kutusu)"))
            w.setToolTip(_("x, y, z [cm]; ikisi de boşsa model kutusu kullanılır."))
        self.kutu_sinir_satiri = self._uclu(((_("alt"), self.t_kutu_alt),
                                             (_("üst"), self.t_kutu_ust)))
        self.t_yuzey_not = ipucu(_(
            "Yüzey tally'sinde skor 'current'tır; enerji grupları açıksa kaçak spektrumu verilir. "
            "Akım kaynak parçacığına süzülür. Sonuç Çalıştır sayfasındaki “Yüzey akımı” "
            "kartındadır."))
        t_form.insertRow(1, _("Tür:"), self.t_tur)
        t_form.addRow(_("Kutu bölmeleri:"), self.kutu_satiri)
        t_form.addRow(_("Kutu sınırları [cm]:"), self.kutu_sinir_satiri)
        t_form.addRow(self.t_yuzey_not)
        self.t_tur.currentIndexChanged.connect(self._yuzey_turu_secildi)
        for w in (self.t_kutu_nx, self.t_kutu_ny, self.t_kutu_nz):
            w.valueChanged.connect(self._tally_kaydet)
        for w in (self.t_kutu_alt, self.t_kutu_ust):
            w.editingFinished.connect(self._tally_kaydet)

    # ------------------------------------------------------------------
    def _yuzey_doldur(self, t):
        f = _y.yuzey_filtresi(t) or {}
        self.t_tur.setCurrentIndex(max(self.t_tur.findData(f.get("tur", HACIM)), 0))
        boyut = list(f.get("boyut") or [1, 1, 1])
        for w, n in zip((self.t_kutu_nx, self.t_kutu_ny, self.t_kutu_nz), boyut):
            w.setValue(int(n))
        for w, anahtar in ((self.t_kutu_alt, "alt"), (self.t_kutu_ust, "ust")):
            deger = f.get(anahtar)
            w.setText(", ".join("%g" % x for x in deger) if deger else "")

    def _yuzey_gorunurluk(self, t):
        tf = self._t_form
        tur = self.t_tur.currentData()
        yuzey = tur != HACIM
        if yuzey:
            for w in (self.t_set, self.t_set_ozet, self.t_skor, self.t_mesh_var,
                      self.mesh_satiri):
                tf.setRowVisible(w, False)
            # yuzey filtresi "dosyadan gelen filtre" degildir: bu form yonetir
            diger = [f for f in (t or {}).get("filtreler") or []
                     if f.get("tur") not in _y.YUZEY_FILTRELERI + ("enerji", "mesh")]
            if not diger:
                tf.setRowVisible(self.t_diger, False)
        tf.setRowVisible(self.kutu_satiri, tur == _y.FILTRE_KUTU)
        tf.setRowVisible(self.kutu_sinir_satiri, tur == _y.FILTRE_KUTU)
        tf.setRowVisible(self.t_yuzey_not, yuzey)
        uc_b = self._mesh_nz_anlamli()
        self.t_kutu_nz.setVisible(uc_b)
        self.t_kutu_nz._etiket.setVisible(uc_b)

    def _yuzey_turu_secildi(self, *_a):
        if self._yukleniyor:
            return
        t = self._secili_tally()
        if t is None:
            return
        tur = self.t_tur.currentData()
        enerji = [f for f in t.get("filtreler") or [] if f.get("tur") == "enerji"]
        if tur == HACIM:
            t["filtreler"] = [f for f in t.get("filtreler") or []
                              if f.get("tur") not in _y.YUZEY_FILTRELERI]
            if t.get("skorlar") == [_y.YUZEY_SKORU]:
                t["skorlar"] = ["flux"]
        else:
            yeni = _y.filtre_sinir() if tur == _y.FILTRE_SINIR else _y.filtre_kutu([1, 1, 1])
            t["filtreler"] = [yeni] + enerji
            t["skorlar"] = [_y.YUZEY_SKORU]
        self._tally_secildi(self.tally_liste.currentRow())
        self.bildir()

    # ------------------------------------------------------------------
    @staticmethod
    def _uc_sayi(metin):
        """'x, y, z' -> [x, y, z]; bos -> []; okunamazsa None."""
        parcalar = [p.strip() for p in (metin or "").replace(";", ",").split(",") if p.strip()]
        if not parcalar:
            return []
        try:
            sayilar = [float(p) for p in parcalar]
        except ValueError:
            return None
        return sayilar if len(sayilar) == 3 else None

    def _kutu_filtresi(self, eski):
        boyut = [self.t_kutu_nx.value(), self.t_kutu_ny.value(),
                 self.t_kutu_nz.value() if self._mesh_nz_anlamli()
                 else (eski.get("boyut") or [1, 1, 1])[2]]
        alt, ust = self._uc_sayi(self.t_kutu_alt.text()), self._uc_sayi(self.t_kutu_ust.text())
        if alt == [] and ust == []:
            return _y.filtre_kutu(boyut)
        if alt and ust:
            return _y.filtre_kutu(boyut, alt, ust)
        _log.info("kutu sınırı okunamadı (alt=%r üst=%r); önceki sınır korunur",
                  self.t_kutu_alt.text(), self.t_kutu_ust.text())
        return dict(eski, boyut=boyut)

    def _enerji_filtresi(self, eski):
        if not self.t_enerji_var.isChecked():
            return None
        gruplar = self._sayi_listesi(self.t_enerji.text())
        if len(gruplar) >= 2:
            yeni = sema.filtre_enerji(sorted(gruplar))
            return eski if eski and eski.get("gruplar") == yeni["gruplar"] else yeni
        return eski or sema.filtre_enerji(_VARSAYILAN_ENERJI)

    def _yuzey_kaydet(self, t):
        """Yuzey tally'sinin formu kaydedilir; hacim tally'siyse False."""
        f = _y.yuzey_filtresi(t)
        if f is None:
            return False
        t["ad"] = self.t_ad.text().strip() or t["ad"]
        t["skorlar"] = [_y.YUZEY_SKORU]
        eski_enerji = next((x for x in t.get("filtreler") or [] if x.get("tur") == "enerji"), None)
        yeni = [self._kutu_filtresi(f) if f["tur"] == _y.FILTRE_KUTU else f]
        enerji = self._enerji_filtresi(eski_enerji)
        t["filtreler"] = yeni + ([enerji] if enerji else [])
        i = self.tally_liste.currentRow()
        if i >= 0:
            self.tally_liste.item(i).setText(t["ad"])
        self._tally_gorunurluk()
        self.bildir()
        return True
