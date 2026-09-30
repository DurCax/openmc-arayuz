# -*- coding: utf-8 -*-
"""
arayuz/kor/katmanlar.py -- KorKatmanMixin: eksenel katman tablosu
(arayuz/sekme_kor.py'den bolundu; davranis degismedi).

KATMAN TABLOSU FIZIKSEL SIRADA: spec katmanlari ALTTAN USTE tutar
(sema.eksenel_katmanlar). Tablo ise EN UST katmani EN USTTE gosterir: satir
r <-> spec indeksi n-1-r. Yukari ok katmani gercekten yukari (spec'te bir
sonraki indekse) tasir.
"""

from PySide6 import QtWidgets

from cekirdek import sema, uygunluk
from cekirdek.gunluk import kaydedici
from arayuz.ortak import sayi

_log = kaydedici("arayuz.sekme_kor")
_BOS_ETIKET = "Boş (madde yok)"
_KATMAN_EN_COK_SATIR = 10


def tablo_yuksekligi(tablo, en_cok_satir):
    """Tablo yuksekligi satir sayisina uysun (en_cok_satir'a kadar kaydirmasiz)."""
    n = max(1, min(tablo.rowCount(), en_cok_satir))
    satir = tablo.verticalHeader().defaultSectionSize()
    if tablo.rowCount():
        satir = max(satir, max(tablo.rowHeight(i) for i in range(tablo.rowCount())))
    tablo.setFixedHeight(tablo.horizontalHeader().sizeHint().height()
                         + n * satir + 2 * tablo.frameWidth() + 2)


class KorKatmanMixin(object):
    """Katman tablosu <-> spec["kor"]["eksenel"]["bolgeler"]."""

    def _katmanlar(self):
        return ((self.spec["kor"].get("eksenel") or {}).get("bolgeler") or [])

    def _spec_indeksi(self, satir):
        n = len(self._katmanlar())
        return n - 1 - satir if 0 <= satir < n else -1

    def _satir_indeksi(self, i):
        n = len(self._katmanlar())
        return n - 1 - i if 0 <= i < n else -1

    def _dolgu_secenekleri(self):
        """
        Bir katmani doldurabilecek adlar. Ilk oge None = korun ana dolgusu;
        etiketi sema.katman_adaylari'nin o katman icin donecegi adlardir.
        """
        kor = self.spec["kor"]
        tur = kor.get("tur")
        ana = sema.katman_adaylari(kor, {})
        if tur == "kare_kafes":
            ana_etiket = "Ana dolgu (kor haritası)"
        elif ana:
            ana_etiket = "Ana dolgu (%s)" % ", ".join(ana)
        else:
            ana_etiket = "Ana dolgu (seçilmedi)"
        izinli = uygunluk.katman_dolgu_turleri(self.spec)
        ogeler = [(None, ana_etiket), (sema.BOSLUK, _BOS_ETIKET)]
        ana_demet = sema.demet_bul(self.spec, kor.get("demet")) if kor.get("demet") else None
        if "demet" in izinli:
            for d in self.spec.get("demetler", []):
                # tek demette katman, ana demetle AYNI kafes tipinde olmali
                if tur == "tek_demet" and ana_demet is not None \
                        and d.get("tur", "kare") != ana_demet.get("tur", "kare"):
                    continue
                ogeler.append((d["ad"], "demet: %s" % d["ad"]))
        if "cubuk" in izinli:
            ogeler += [(c["ad"], "çubuk: %s" % c["ad"]) for c in self.spec.get("cubuklar", [])]
        if "plaka" in izinli:
            ogeler += [(p["ad"], "plaka: %s" % p["ad"]) for p in self.spec.get("plakalar", [])]
        if "malzeme" in izinli:
            ogeler += [(m["ad"], "malzeme: %s" % sema.malzeme_etiketi(m))
                       for m in self.spec["malzemeler"]]
        return ogeler

    def _katman_doldur(self):
        """spec -> tablo (en ust katman ilk satirda)."""
        katmanlar = self._katmanlar()
        secenekler = self._dolgu_secenekleri()
        n = len(katmanlar)
        self.katman_tablo.setRowCount(0)
        self.katman_tablo.setRowCount(n)
        z = sema.eksenel_katmanlar(dict(self.spec["kor"], eksenel={"var": True,
                                                                   "bolgeler": katmanlar}))
        z_adi = {id(b): (z0, z1) for z0, z1, b in (z or [])}
        for i, b in enumerate(katmanlar):
            satir = n - 1 - i
            ad = QtWidgets.QLineEdit(b.get("ad") or "")
            ad.editingFinished.connect(self._katman_kaydet)
            if id(b) in z_adi:
                ad.setToolTip("z = %g … %g cm" % z_adi[id(b)])
            self.katman_tablo.setCellWidget(satir, 0, ad)
            h = sayi(float(b.get("yukseklik") or 1.0), 3, 0.001, 10000.0, 1.0, "cm")
            h.valueChanged.connect(self._katman_kaydet)
            self.katman_tablo.setCellWidget(satir, 1, h)
            kutu = QtWidgets.QComboBox()
            for deger, etiket in secenekler:
                kutu.addItem(etiket, deger)
            if b.get("anahtar"):
                # Katmana ozel harf eslemesi arayuzde duzenlenmiyor; secim
                # kutusu bunu SESSIZCE SILMESIN diye ayri bir oge gosterilir.
                kutu.insertItem(0, "(katmana özel harita — dosyadan)", "__anahtar__")
                kutu.setCurrentIndex(0)
                kutu.setEnabled(False)
            else:
                j = kutu.findData(b.get("dolgu"))
                if j < 0:
                    # listede olmayan (ture uymayan / tanimsiz) dolgu korunur
                    kutu.addItem("%s (bu kor türünde uygun değil)" % b.get("dolgu"),
                                 b.get("dolgu"))
                    j = kutu.count() - 1
                kutu.setCurrentIndex(j)
            kutu.currentIndexChanged.connect(self._katman_kaydet)
            self.katman_tablo.setCellWidget(satir, 2, kutu)
        self.katman_tablo.resizeColumnsToContents()
        tablo_yuksekligi(self.katman_tablo, _KATMAN_EN_COK_SATIR)
        self._katman_ozet_guncelle()

    def _katman_kaydet(self, *_):
        """Tablo -> spec. Duzenlenmeyen alanlar (anahtar) KORUNUR."""
        if self._yukleniyor:
            return
        eski = self._katmanlar()
        n = self.katman_tablo.rowCount()
        yeni = []
        for i in range(n):                       # spec sirasi: alttan uste
            satir = n - 1 - i
            b = dict(eski[i]) if i < len(eski) else {}
            ad_w = self.katman_tablo.cellWidget(satir, 0)
            h_w = self.katman_tablo.cellWidget(satir, 1)
            d_w = self.katman_tablo.cellWidget(satir, 2)
            b["ad"] = ad_w.text().strip() or ("katman %d" % (i + 1))
            b["yukseklik"] = h_w.value()
            if not b.get("anahtar"):
                b["dolgu"] = d_w.currentData()
            yeni.append(b)
        eks = self.spec["kor"].setdefault("eksenel", {})
        eks["bolgeler"] = yeni
        self._katman_ozet_guncelle()
        self._ozet_guncelle()
        self.bildir()

    def _katman_ozet_guncelle(self):
        """Toplam / aktif / cubuk araliklarini canli gosterir."""
        kor = self.spec["kor"]
        if not (kor.get("eksenel") or {}).get("var"):
            self.katman_ozet.setText("")
            return
        toplam = sema.kor_yuksekligi(kor)
        if not toplam:
            self.katman_ozet.setText("Geçerli katman yok (her katmanın yüksekliği pozitif olmalı).")
            return
        satir = "Toplam yükseklik = %g cm" % toplam
        try:
            from cekirdek import kurucu
            ar = kurucu.aktif_eksenel_aralik(self.spec)
            if ar:
                satir += ("   ·   aktif yakıt = %g cm  (z = %g … %g)"
                          % (ar[1] - ar[0], ar[0], ar[1]))
            g = self.spec.get("guc_dagilimi") or {}
            adlar = list(dict.fromkeys(h["cubuk"] for h in sema.guc_hedefleri(g)
                                       if h["cubuk"]))
            if g.get("var") and adlar:
                cr = kurucu.guc_eksenel_araligi(self.spec, adlar)
                if cr and (cr[1] - cr[0]) != (ar[1] - ar[0] if ar else None):
                    satir += ("\n“%s” çubuğu = %g cm (z = %g … %g) — güç ağı bunu kullanır"
                              % ("”, “".join(adlar), cr[1] - cr[0], cr[0], cr[1]))
        except Exception as hata:
            # Gorunen metne yazilir VE loglanir (sessiz yutma degil).
            _log.exception("eksenel aralık hesaplanamadı")
            satir += "   ·   aralık hesaplanamadı: %s" % hata
        self.katman_ozet.setText(satir)

    def _katmanlari_yenile(self, secili_spec=None):
        self._yukleniyor = True
        try:
            self._katman_doldur()
        finally:
            self._yukleniyor = False
        if secili_spec is not None:
            satir = self._satir_indeksi(secili_spec)
            if satir >= 0:
                self.katman_tablo.setCurrentCell(satir, 0)
        self._gorunurluk()
        self._ozet_guncelle()

    def _katman_ekle(self):
        eks = self.spec["kor"].setdefault("eksenel", {})
        bolgeler = eks.setdefault("bolgeler", [])
        bolgeler.append(sema.eksenel_bolge("katman %d" % (len(bolgeler) + 1), 20.0, None))
        self._katmanlari_yenile(len(bolgeler) - 1)          # en ust = ilk satir
        self.bildir()

    def _katman_sil(self):
        i = self._spec_indeksi(self.katman_tablo.currentRow())
        katmanlar = self._katmanlar()
        if i < 0:
            return
        katmanlar.pop(i)
        self._katmanlari_yenile(min(i, len(katmanlar) - 1) if katmanlar else None)
        self.bildir()

    def _katman_tasi(self, yon):
        """yon: -1 = tabloda yukari (fiziksel olarak YUKARI), +1 = asagi."""
        i = self._spec_indeksi(self.katman_tablo.currentRow())
        katmanlar = self._katmanlar()
        hedef = i - yon                  # spec alttan uste: yukari = indeks + 1
        if i < 0 or hedef < 0 or hedef >= len(katmanlar):
            return
        katmanlar[i], katmanlar[hedef] = katmanlar[hedef], katmanlar[i]
        self._katmanlari_yenile(hedef)
        self.bildir()
