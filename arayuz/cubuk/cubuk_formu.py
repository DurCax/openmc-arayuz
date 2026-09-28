# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/cubuk_formu.py  --  CubukFormuMixin: secili cubugun formu

 arayuz/sekme_cubuk.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_cubuk; sekme_cubuk.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from cekirdek import sema, uygunluk
from arayuz.ortak import renk_simgesi, sayi
from arayuz.cubuk.parca_islemleri import (
    BOS_ETIKETI, SECILMEDI_ETIKETI, _renk, bolge_aciklamasi, eksik_malzemeler,
    malzeme_etiketi, parca_rengi, rol_malzemesi, roller)
from arayuz.cubuk.malzeme_kutusu import MalzemeKutusu


class CubukFormuMixin(object):
    """Secili cubugun formu: bolge tablosu, kontrol cubugu, kaydetme."""

    # ------------------------------------------------------------------
    # cubuk
    # ------------------------------------------------------------------
    def _cubuk_doldur(self, c):
        if c is None:
            return
        self.c_ad.setText(c["ad"])
        self._hata_goster(self.c_ad_hata, "")
        kontrol = c.get("tur") == "kontrol"
        self.c_baslik.setText("Kontrol çubuğu" if kontrol else "Çubuk")
        # Tur: kontrol cubugu yalnizca modelde anlamliysa (3B + kafes) ya da
        # zaten kontrol cubuguysa (dosyadaki veri gizlenmez).
        izin = uygunluk.parca_turleri(self.spec)["kontrol_cubugu"]
        self.c_tur.clear()
        self.c_tur.addItem("Sabit çubuk", "silindirik")
        if izin or kontrol:
            self.c_tur.addItem("Kontrol çubuğu (eksenel hareketli)", "kontrol")
        self.c_tur.setCurrentIndex(max(self.c_tur.findData(c.get("tur", "silindirik")), 0))
        tek = self.c_tur.count() < 2
        self.e_tur.setVisible(not tek)
        self.c_tur.setVisible(not tek)

        self._emici_doldur(c)
        self._izleyici_doldur(c)
        dd = float(c.get("daldirma") or 0.0)
        self.c_daldirma.setValue(dd)
        self.c_daldirma_kaydirici.setValue(int(round(dd * 10)))
        self._kontrol_gorunurluk()
        self._uc_guncelle()
        self._tablo_doldur(c)

    def _emici_doldur(self, c):
        """Emici bolge: dis bolge haric; numaralandirma 1'den."""
        self.c_emici.clear()
        bolgeler = c.get("bolgeler") or []
        for j in range(max(len(bolgeler) - 1, 0)):
            self.c_emici.addItem("%d. bölge — %s" % (
                j + 1, malzeme_etiketi(self.spec, bolgeler[j].get("malzeme"))), j)
        ix = c.get("emici_bolge", 0)
        if c.get("tur") == "kontrol" and self.c_emici.findData(ix) < 0:
            self.c_emici.addItem("%s. bölge — geçersiz (dış bölge daldırılamaz)"
                                 % (ix + 1 if isinstance(ix, int) else ix), ix)
        self.c_emici.setCurrentIndex(max(self.c_emici.findData(ix), 0))

    def _izleyici_doldur(self, c):
        rol_tablosu = roller(self.spec)
        adaylar = [ad for ad, r in rol_tablosu.items() if not r & {"yakit", "emici"}]
        secili = c.get("izleyici_malzeme")
        self.c_izleyici.clear()
        if secili is None:
            self.c_izleyici.addItem(SECILMEDI_ETIKETI, None)
        self.c_izleyici.addItem(BOS_ETIKETI, sema.BOSLUK)
        for m in self.spec.get("malzemeler", []):
            if m["ad"] in adaylar:
                self.c_izleyici.addItem(malzeme_etiketi(self.spec, m["ad"], True, rol_tablosu),
                                        m["ad"])
        if secili is not None and self.c_izleyici.findData(secili) < 0:
            self.c_izleyici.addItem("%s — izleyici olamaz"
                                    % malzeme_etiketi(self.spec, secili), secili)
        self.c_izleyici.setCurrentIndex(max(self.c_izleyici.findData(secili), 0))

    def _tablo_doldur(self, c):
        self.c_tablo.setRowCount(0)
        bolgeler = c.get("bolgeler") or []
        n = len(bolgeler)
        for i, b in enumerate(bolgeler):
            son = i == n - 1
            self.c_tablo.insertRow(i)
            if son:
                oge = QtWidgets.QTableWidgetItem("dış bölge")
                oge.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                oge.setToolTip("Son bölgenin yarıçapı yoktur: hücrenin kalanını doldurur.")
                self.c_tablo.setItem(i, 0, oge)
            else:
                w = sayi(b.get("r") or 0.0, 5, 0.00001, 1000.0, 0.01, "cm")
                w.setKeyboardTracking(False)
                w.valueChanged.connect(self._yaricap_degisti)
                self._takip_et(w, i)
                self.c_tablo.setCellWidget(i, 0, w)
            k = MalzemeKutusu(self.spec, b.get("malzeme"))
            k.currentIndexChanged.connect(self._cubuk_kaydet)
            self._takip_et(k, i)
            self.c_tablo.setCellWidget(i, 1, k)
            aciklama = QtWidgets.QTableWidgetItem("")
            aciklama.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.c_tablo.setItem(i, 2, aciklama)
        self._aciklamalari_guncelle(c)
        self._yaricap_sinirlari()
        self._bolge_dugmeleri()

    def _takip_et(self, w, satir):
        w.setProperty("satir", satir)
        w.installEventFilter(self._satir_takibi)
        if isinstance(w, QtWidgets.QAbstractSpinBox) and w.lineEdit() is not None:
            w.lineEdit().setProperty("satir", satir)
            w.lineEdit().installEventFilter(self._satir_takibi)

    def _aciklamalari_guncelle(self, c):
        for i in range(self.c_tablo.rowCount()):
            oge = self.c_tablo.item(i, 2)
            if oge is not None:
                oge.setText(bolge_aciklamasi(self.spec, c, i))
        eksik = eksik_malzemeler(self.spec, c)
        self._hata_goster(self.c_eksik, (
            "Malzemesi seçilmemiş: %s. Uygun malzeme yoksa önce Malzemeler "
            "sekmesinden ekleyin." % ", ".join(eksik)) if eksik else "")

    def _yaricap_kutulari(self):
        n = self.c_tablo.rowCount()
        return [self.c_tablo.cellWidget(i, 0) for i in range(max(n - 1, 0))]

    def _yaricap_sinirlari(self):
        """Her yaricap kutusunun alt/ust siniri komsularindan: sira bozulamaz."""
        kutular = [k for k in self._yaricap_kutulari() if k is not None]
        r = [k.value() for k in kutular]
        artan = all(r[i] < r[i + 1] for i in range(len(r) - 1))
        eps = 1e-5
        for i, k in enumerate(kutular):
            k.blockSignals(True)
            try:
                if artan:
                    k.setRange(r[i - 1] + eps if i > 0 else eps,
                               r[i + 1] - eps if i + 1 < len(r) else 1000.0)
                else:
                    k.setRange(eps, 1000.0)
            finally:
                k.blockSignals(False)
        self._hata_goster(self.c_sira_uyari, "" if artan else (
            "Yarıçaplar içten dışa artmalı: %s. Değerleri düzeltin."
            % " → ".join("%.5g" % x for x in r)))

    def _bolge_dugmeleri(self):
        n = self.c_tablo.rowCount()
        satir = self.c_tablo.currentRow()
        ic = 0 <= satir < n - 1
        self.d_bolge_sil.setEnabled(ic and n > 2)
        self.d_ice.setEnabled(ic and satir > 0)
        self.d_disa.setEnabled(ic and satir + 1 < n - 1)

    def _kontrol_gorunurluk(self):
        kontrol = self.c_tur.currentData() == "kontrol"
        for w in list(self.c_kontrol_etiketleri.values()) + [
                self.c_emici, self.c_izleyici, self.c_daldirma,
                self.c_daldirma_kaydirici, self.c_uc_etiket, self.c_kontrol_not]:
            w.setVisible(kontrol)

    def _uc_guncelle(self):
        """
        Daldirma oranindan uc konumunu hesaplayip gosterir.

        Kurucu ile AYNI formul (kurucu.cubuk_universe): daldirma AKTIF yakit
        araliginda olculur, modelin toplam yuksekliginde degil:
            z_uc = z_ust - daldirma/100 * (z_ust - z_alt)
        """
        h = sema.kor_yuksekligi((self.spec or {}).get("kor") or {})
        if not h:
            self.c_uc_etiket.setText("Model 2B: Kor sekmesinde yükseklik tanımlayın")
            self.c_uc_etiket.setStyleSheet("color: %s;" % _renk("hata", "#b3261e"))
            return
        try:
            from cekirdek import kurucu
            z_alt, z_ust = kurucu.aktif_eksenel_aralik(self.spec) or (-h / 2.0, h / 2.0)
        except Exception:
            z_alt, z_ust = -h / 2.0, h / 2.0
        z = z_ust - (self.c_daldirma.value() / 100.0) * (z_ust - z_alt)
        self.c_uc_etiket.setText("z = %+.2f cm   (aktif yakıt: %+.1f … %+.1f cm)"
                                 % (z, z_alt, z_ust))
        self.c_uc_etiket.setStyleSheet("")

    def _cubuk_tur_degisti(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        yeni_tur = self.c_tur.currentData()
        c["tur"] = yeni_tur
        if yeni_tur == "kontrol":
            if "emici_bolge" not in c:
                rol_tablosu = roller(self.spec)
                emici = [i for i, b in enumerate(c["bolgeler"][:-1])
                         if "emici" in rol_tablosu.get(b.get("malzeme"), ())]
                c["emici_bolge"] = emici[0] if emici else 0
            c.setdefault("daldirma", 0.0)
            if not c.get("izleyici_malzeme"):
                c["izleyici_malzeme"] = rol_malzemesi(self.spec, "sogutucu") or sema.BOSLUK
        self.spec_yukle(self.spec)
        self._sec(("cubuk", ad))
        self.bildir()

    def _daldirma_degisti(self, *_):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.c_daldirma_kaydirici.setValue(int(round(self.c_daldirma.value() * 10)))
        finally:
            self._yukleniyor = False
        self._uc_guncelle()
        self._cubuk_kaydet()

    def _kaydirici_degisti(self, deger):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.c_daldirma.setValue(deger / 10.0)
        finally:
            self._yukleniyor = False
        self._uc_guncelle()
        self._cubuk_kaydet()

    def _yaricap_degisti(self, *_):
        if self._yukleniyor:
            return
        self._cubuk_kaydet()
        self._yaricap_sinirlari()

    def _cubuk_kaydet(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        bolgeler = []
        n = self.c_tablo.rowCount()
        for i in range(n):
            w = self.c_tablo.cellWidget(i, 0)
            r = None if (i == n - 1 or w is None) else w.value()
            k = self.c_tablo.cellWidget(i, 1)
            bolgeler.append({"r": r, "malzeme": k.currentData() if k else None})
        c["bolgeler"] = bolgeler
        if c.get("tur") == "kontrol":
            ix = self.c_emici.currentData()
            c["emici_bolge"] = ix if isinstance(ix, int) else 0
            c["izleyici_malzeme"] = self.c_izleyici.currentData()
            c["daldirma"] = self.c_daldirma.value()
        # Aciklama, eksik uyarisi ve emici listesi malzemeye bagli.
        self._yukleniyor = True
        try:
            self._aciklamalari_guncelle(c)
            if c.get("tur") == "kontrol":
                self._emici_doldur(c)
        finally:
            self._yukleniyor = False
        self._liste_ogesini_yenile(c)
        self.bildir()

    def _liste_ogesini_yenile(self, parca):
        oge = self.liste.currentItem()
        if oge is None:
            return
        tur = oge.data(QtCore.Qt.UserRole)[0]
        ek = ("  · plaka" if tur == "plaka"
              else "  · kontrol" if parca.get("tur") == "kontrol" else "")
        oge.setText(parca["ad"] + ek)
        oge.setIcon(renk_simgesi(parca_rengi(self.spec, parca)))
        oge.setData(QtCore.Qt.ForegroundRole, None)
        oge.setToolTip("")
        self._liste_isareti(oge, parca)

    def _secili_cubuk_yenile(self, c, satir=None):
        self._yukleniyor = True
        try:
            self._cubuk_doldur(c)
            if satir is not None:
                self.c_tablo.setCurrentCell(satir, 2)
        finally:
            self._yukleniyor = False
        self._bolge_dugmeleri()
        self._liste_ogesini_yenile(c)

    def _bolge_ekle(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        yaricaplar = [b["r"] for b in c["bolgeler"] if b.get("r")]
        yeni_r = (max(yaricaplar) * 1.1) if yaricaplar else 0.4
        n = len(c["bolgeler"])
        # Malzemesi SECILMEMIS olarak eklenir: sessizce bosluk/su olmasin,
        # kullanici secene kadar kirmizi isaretli kalir.
        c["bolgeler"].insert(n - 1, {"r": round(yeni_r, 5), "malzeme": None})
        self._secili_cubuk_yenile(c, n - 1)
        self.bildir()

    def _bolge_sil(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        satir = self.c_tablo.currentRow()
        if satir < 0 or satir >= len(c["bolgeler"]) - 1 or len(c["bolgeler"]) <= 2:
            return                     # dugme zaten kapali
        c["bolgeler"].pop(satir)
        if c.get("tur") == "kontrol":
            ix = c.get("emici_bolge", 0)
            if isinstance(ix, int) and satir < ix:
                c["emici_bolge"] = ix - 1
            elif ix == satir:
                c["emici_bolge"] = 0
        self._secili_cubuk_yenile(c, min(satir, len(c["bolgeler"]) - 2))
        self.bildir()

    def _bolge_tasi(self, yon):
        """Secili bolgenin MALZEMESINI komsusuyla degistirir; yaricaplar yerinde."""
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        i = self.c_tablo.currentRow()
        j = i + yon
        son = len(c["bolgeler"]) - 1
        if i < 0 or i >= son or j < 0 or j >= son:
            return
        b = c["bolgeler"]
        b[i]["malzeme"], b[j]["malzeme"] = b[j].get("malzeme"), b[i].get("malzeme")
        if c.get("tur") == "kontrol":
            ix = c.get("emici_bolge", 0)
            if ix == i:
                c["emici_bolge"] = j
            elif ix == j:
                c["emici_bolge"] = i
        self._secili_cubuk_yenile(c, j)
        self.bildir()
