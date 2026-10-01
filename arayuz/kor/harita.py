# -*- coding: utf-8 -*-
"""
arayuz/kor/harita.py -- KorHaritasiMixin: kare kor haritasinin boyanmasi
(arayuz/sekme_kor.py'den bolundu; davranis degismedi).

Kare kor haritasi izgara.ParcaPaleti + izgara.KareIzgara ile boyanir; harfler
arka planda atanir (izgara.adlardan_harita), spec bicimi ayni kalir. Boyut
(nx, ny) haritadan turetilir; hucre kaybettiren kucultme onay ister.
"""

from PySide6 import QtWidgets

from arayuz import izgara
from cekirdek.ceviri import _, _n


class KorHaritasiMixin(object):
    """Kare harita <-> spec["kor"]["harita"/"anahtar"/"boyut"]."""

    def _palet_ogeleri(self):
        """Kor haritasina konabilecek parcalar: kare kafesler, malzemeler, bosluk;
        ayrica haritada zaten gecen (or. dosyadan gelen bir cubuk) her ad."""
        kor = self.spec["kor"]
        kullanilan = {ad for satir in izgara.harita_adlara(kor.get("harita"), kor.get("anahtar"))
                      for ad in satir if ad}
        altigen = {d["ad"] for d in self.spec.get("demetler", []) if d.get("tur") == "altigen"}
        ogeler = []
        for oge in izgara.palet_ogeleri(self.spec, turler=("demet", "cubuk", "plaka",
                                                           "malzeme", "bosluk")):
            ad, tur = oge[0], oge[3]
            if ad in kullanilan or (tur == "kafes" and ad not in altigen) \
                    or tur in ("malzeme", "boşluk"):
                ogeler.append(oge)
        return ogeler

    def _harita_doldur(self):
        kor = self.spec["kor"]
        harita = kor.get("harita") or []
        if harita:
            adlar = izgara.harita_adlara(harita, kor.get("anahtar"))
        else:
            nx, ny = (list(kor.get("boyut") or [1, 1]) + [1, 1])[:2]
            adlar = [[None] * max(int(nx), 1) for _ in range(max(int(ny), 1))]
        onceki = self.palet.secili()
        self.palet.blockSignals(True)
        try:
            self.palet.parcalari_ayarla(self._palet_ogeleri(), secili=onceki)
        finally:
            self.palet.blockSignals(False)
        if onceki is None or self.palet.secili() != onceki:
            # Ilk yukleme: firca haritada en cok gecen kafes olsun.
            sayac = {}
            for satir in adlar:
                for ad in satir:
                    if ad:
                        sayac[ad] = sayac.get(ad, 0) + 1
            if sayac:
                self.palet.sec(max(sayac, key=sayac.get))
        self.izgara.firca_ayarla(self.palet.secili())
        self.izgara.yukle(adlar, self.palet.renkler())
        nx = max((len(s) for s in adlar), default=0)
        for kutu, deger in ((self.nx, nx), (self.ny, len(adlar))):
            eski = kutu.blockSignals(True)
            kutu.setValue(max(deger, 1))
            kutu.blockSignals(eski)

    def _harita_yaz(self, adlar):
        """Parca adlari izgarasini spec'e yazar (harfler otomatik, eskiler korunur)."""
        kor = self.spec["kor"]
        try:
            harita, anahtar = izgara.adlardan_harita(adlar, kor.get("anahtar"),
                                                     kor.get("harita"))
        except ValueError as hata:
            QtWidgets.QMessageBox.warning(self, _("Harita yazılamadı"), str(hata))
            return False
        kor["harita"] = harita
        kor["anahtar"] = anahtar
        kor["boyut"] = [max((len(s) for s in adlar), default=0), len(adlar)]
        return True

    def _harita_boyandi(self):
        if self._yukleniyor or self.spec is None:
            return
        if self._harita_yaz(self.izgara.adlar()):
            self._ozet_guncelle()
            self.bildir()

    def _altigen_boyandi(self):
        if self._yukleniyor or self.spec is None:
            return
        self._ozet_guncelle()
        self.bildir()

    def _boyut_degisti(self, *_arg):
        if self._yukleniyor or self.spec is None:
            return
        adlar = self.izgara.adlar()
        nx, ny = self.nx.value(), self.ny.value()
        eski_nx = max((len(s) for s in adlar), default=0)
        eski_ny = len(adlar)
        kaybolan = sum(1 for r, satir in enumerate(adlar) for c, ad in enumerate(satir)
                       if (r >= ny or c >= nx) and ad is not None)
        if kaybolan:
            if not self._onay_al(
                    _("Kor haritası küçülüyor"),
                    _n("Harita %d×%d'den %d×%d'ye küçülüyor: sağdaki/alttaki %d dolu hücre "
                       "silinecek (büyütmek onları geri getirmez).\n\nDevam edilsin mi?",
                       "Harita %d×%d'den %d×%d'ye küçülüyor: sağdaki/alttaki %d dolu hücre "
                       "silinecek (büyütmek onları geri getirmez).\n\nDevam edilsin mi?",
                       kaybolan)
                    % (eski_nx, eski_ny, nx, ny, kaybolan)):
                for kutu, deger in ((self.nx, eski_nx), (self.ny, eski_ny)):
                    eski = kutu.blockSignals(True)
                    kutu.setValue(deger)
                    kutu.blockSignals(eski)
                return
        firca = self.palet.secili()
        yeni = [[(adlar[r][c] if r < len(adlar) and c < len(adlar[r]) else firca)
                 for c in range(nx)] for r in range(ny)]
        self.izgara.yukle(yeni, self.palet.renkler())
        self._harita_boyandi()

    def _tumunu_doldur(self):
        if self.palet.secili() is None:
            return
        self.izgara.firca_ayarla(self.palet.secili())
        self.izgara.tumunu_doldur(self.palet.secili())   # degisti -> _harita_boyandi
