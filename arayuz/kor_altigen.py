# -*- coding: utf-8 -*-
"""
================================================================================
 kor_altigen.py  --  Kor sekmesinde altigen tam kor haritasi (altigen_kafes)
================================================================================
 Kare kor haritasinin (sekme_kor) altigen karsiligi: izgara.ParcaPaleti +
 izgara.AltigenIzgara ile boyanir; harfler arka planda atanir
 (izgara.adlardan_harita), spec bicimi demet haritasiyla ayni (DISTAN ICE
 halkalar). Halka sayisini kucultmek dolu hucre kaybettiriyorsa onay ister.

 Palete yalnizca ALTIGEN demetler, malzemeler ve bosluk girer: kare demet
 ya da tek cubuk altigen kor hucresine oturmaz (dogrula/kor.py hata sayar).
 Haritada zaten gecen her ad (dosyadan) yine gosterilir.

 Kor yonelimi: demet pin kafesi 'y' ise kor 'x' (birbirine 90 derece;
 cekirdek/altigen_kor.py'de olculdu). Secim kutusu bunu ipucunda soyler.
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import altigen, altigen_kor
from cekirdek.ceviri import N_, _, _n
from arayuz import izgara
from arayuz.ortak import ipucu, tamsayi

YONELIMLER = (("x", N_("x — komşu demetler sağda/solda")),
              ("y", N_("y — komşu demetler üstte/altta")))


class AltigenKorHaritasi(QtWidgets.QWidget):
    """Altigen kor haritasi editoru. Spec'i YERINDE degistirir, degisti yayar."""

    degisti = QtCore.Signal()

    def __init__(self, onay_al, parent=None):
        super().__init__(parent)
        self._onay_al = onay_al          # (baslik, metin) -> bool
        self.spec = None
        self._yukleniyor = False
        self.palet = izgara.ParcaPaleti()
        self.palet.setMaximumWidth(230)
        self.izgara = izgara.AltigenIzgara()
        self.izgara.setMinimumHeight(280)
        self.izgara.etiketleri_goster(True)
        self.halka = tamsayi(2, 1, 30, 1, _("halka"))
        self.halka.setToolTip(_("Merkez dahil halka sayısı: 2 halka = 7 demet, "
                                "3 halka = 19 demet. Büyütünce yeni halka paletteki "
                                "seçili parçayla dolar."))
        self.yonelim = QtWidgets.QComboBox()
        for veri, ad in YONELIMLER:
            self.yonelim.addItem(_(ad), veri)
        self.yonelim_notu = ipucu("")
        self.d_doldur = QtWidgets.QPushButton(_("Tümünü seçili parçayla doldur"))
        self._yerlestir()
        self.palet.secildi.connect(self.izgara.firca_ayarla)
        self.izgara.firca_istendi.connect(self.palet.sec)
        self.izgara.degisti.connect(self._boyandi)
        self.halka.valueChanged.connect(self._halka_degisti)
        self.yonelim.currentIndexChanged.connect(self._yonelim_degisti)
        self.d_doldur.clicked.connect(self._tumunu_doldur)

    def _yerlestir(self):
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(QtWidgets.QLabel(_("Halka sayısı:")))
        ust.addWidget(self.halka)
        ust.addWidget(QtWidgets.QLabel(_("Yönelim:")))
        ust.addWidget(self.yonelim)
        ust.addStretch(1)
        ust.addWidget(self.d_doldur)
        d.addLayout(ust)
        d.addWidget(self.yonelim_notu)
        boya = QtWidgets.QHBoxLayout()
        boya.addWidget(self.palet, 0)
        boya.addWidget(self.izgara, 1)
        d.addLayout(boya, 1)
        d.addWidget(ipucu(_(
            "Paletten bir demet seçip hücrelere tıklayın ya da sürükleyin; sağ tık o "
            "hücredeki parçayı seçer. Yan sınır en dış demetlerin dış yüzlerindedir; "
            "yansıtıcı kuşak açıksa kuşak bu yüzlerden başlar.")))

    # ------------------------------------------------------------------
    def _palet_ogeleri(self):
        kor = self.spec["kor"]
        kullanilan = {ad for satir in izgara.harita_adlara(kor.get("harita"), kor.get("anahtar"))
                      for ad in satir if ad}
        altigenler = {d["ad"] for d in self.spec.get("demetler", [])
                      if d.get("tur") == "altigen"}
        return [o for o in izgara.palet_ogeleri(self.spec, turler=("demet", "malzeme", "bosluk"))
                if o[0] in kullanilan or o[0] in altigenler or o[3] != "kafes"]

    def yukle(self, spec):
        """spec -> izgara (sinyal yaymadan)."""
        self.spec = spec
        kor = spec["kor"]
        self._yukleniyor = True
        try:
            n = altigen_kor.halka_sayisi(kor)
            self.halka.setValue(n)
            self.yonelim.setCurrentIndex(max(0, self.yonelim.findData(kor.get("yonelim") or "x")))
            onceki = self.palet.secili()
            self.palet.parcalari_ayarla(self._palet_ogeleri(), secili=onceki)
            adlar = self._adlar()
            if onceki is None or self.palet.secili() != onceki:
                sayac = {}
                for ad in (a for satir in adlar for a in satir if a):
                    sayac[ad] = sayac.get(ad, 0) + 1
                if sayac:
                    self.palet.sec(max(sayac, key=sayac.get))
            self.izgara.firca_ayarla(self.palet.secili())
            self.izgara.yukle(adlar, n, kor.get("yonelim") or "x", self.palet.renkler())
            self._yonelim_notunu_yaz()
        finally:
            self._yukleniyor = False

    def _adlar(self):
        kor = self.spec["kor"]
        n = altigen_kor.halka_sayisi(kor)
        harita = kor.get("harita") or []
        if [len(s) for s in harita] != altigen.halka_uzunluklari(n):
            # bicimi bozuk (elle yazilmis) harita: bos hucrelerle gosterilir,
            # dosya boyanana kadar degismez; dogrulama ayrica bildirir
            return [[None] * u for u in altigen.halka_uzunluklari(n)]
        return izgara.harita_adlara(harita, kor.get("anahtar"))

    def _yonelim_notunu_yaz(self):
        kor = self.spec["kor"]
        pin = {d.get("yonelim", "y") for d in self.spec.get("demetler", [])
               if d.get("tur") == "altigen"
               and d["ad"] in (kor.get("anahtar") or {}).values()}
        yon = kor.get("yonelim") or "x"
        uyumsuz = sorted(p for p in pin if p == yon)
        self.yonelim_notu.setText(
            _("Demetlerin pin kafesi '%s': kor yönelimi '%s' olmalı (birbirine 90°); "
              "aksi halde demet köşeleri komşu hücreye taşar.")
            % (uyumsuz[0], altigen_kor.ters_yonelim(uyumsuz[0])) if uyumsuz else "")
        self.yonelim_notu.setVisible(bool(uyumsuz))

    # ------------------------------------------------------------------
    def _yaz(self, adlar):
        kor = self.spec["kor"]
        try:
            harita, anahtar = izgara.adlardan_harita(adlar, kor.get("anahtar"), kor.get("harita"))
        except ValueError as hata:
            QtWidgets.QMessageBox.warning(self, _("Harita yazılamadı"), str(hata))
            return False
        kor["harita"], kor["anahtar"] = harita, anahtar
        return True

    def _boyandi(self):
        if self._yukleniyor or self.spec is None:
            return
        if self._yaz(self.izgara.adlar()):
            self.degisti.emit()

    def _halka_degisti(self, yeni):
        if self._yukleniyor or self.spec is None:
            return
        kor = self.spec["kor"]
        eski = altigen_kor.halka_sayisi(kor)
        adlar = self.izgara.adlar()
        kaybolan = sum(1 for satir in adlar[:max(0, eski - yeni)] for ad in satir if ad)
        if kaybolan and not self._onay_al(
                _("Kor haritası küçülüyor"),
                _n("Harita %d halkadan %d halkaya küçülüyor: dış halkalardaki %d dolu "
                   "hücre silinecek (büyütmek onları geri getirmez).\n\nDevam edilsin mi?",
                   "Harita %d halkadan %d halkaya küçülüyor: dış halkalardaki %d dolu "
                   "hücre silinecek (büyütmek onları geri getirmez).\n\nDevam edilsin mi?",
                   kaybolan)
                % (eski, yeni, kaybolan)):
            self._yukleniyor = True
            try:
                self.halka.setValue(eski)
            finally:
                self._yukleniyor = False
            return
        firca = self.palet.secili()
        yeni_adlar = [[firca] * u for u in altigen.halka_uzunluklari(yeni)]
        # halkalar ICTEN hizalanir: merkez sabit (altigen.harita_yeniden_boyutlandir)
        for i in range(min(eski, yeni)):
            yeni_adlar[yeni - 1 - i] = list(adlar[eski - 1 - i])
        kor["halka_sayisi"] = int(yeni)
        self.izgara.yukle(yeni_adlar, yeni, kor.get("yonelim") or "x", self.palet.renkler())
        if self._yaz(yeni_adlar):
            self.degisti.emit()

    def _yonelim_degisti(self, *_a):
        if self._yukleniyor or self.spec is None:
            return
        kor = self.spec["kor"]
        kor["yonelim"] = self.yonelim.currentData()
        self.izgara.yukle(self.izgara.adlar(), altigen_kor.halka_sayisi(kor),
                          kor["yonelim"], self.palet.renkler())
        self._yonelim_notunu_yaz()
        self.degisti.emit()

    def _tumunu_doldur(self):
        if self.palet.secili() is None:
            return
        self.izgara.firca_ayarla(self.palet.secili())
        self.izgara.tumunu_doldur(self.palet.secili())      # degisti -> _boyandi
