# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/kor/geometri_sayfasi.py  --  Geometri sayfasi: sablon <-> gelismis (Dalga G-3)
================================================================================
 KADEMELI ACILIM (§10)
   Varsayilan: sablon gorunumu (eski Kor sayfasi; ogrenci icin kolay yol).
   "Gelişmiş geometriye geç…" onay ister ve geometri.gelismise_gec ile agaca
   donusturur. Gecis TEK YONLUDUR: sihirbaz kapanir, donus yalniz Geri Al ile
   (§15 karar 1). Geri Al gecisin kendisini TEK ADIMDA geri alir: pencere
   (pencere/gecmis.py spec_islemi_uygula) gecisten once bekleyen duzenlemeyi
   ayri adim olarak yigar, sonra gecisi ikinci adim olarak yigar.

 DUZENEK SABLONU secicisi: 7 kor turu (kor.tur; pencerenin "Türü değiştir"
 yolu -- tur_secildi) + 3 yeni duzenek (arayuz/geometri/sablonlar.py; agac
 uretir, dogrudan gelismis moda gecer).

 PENCERE BAGLANTISI
   islem_uygulayici(yeni_spec, mesaj): pencere verir; yoksa (tek basina test)
   spec yerinde degistirilir ve degisti yayilir.
   dugum_secildi(yol) -> onizleme vurgusu; dugum_sec(yol) <- onizleme tiklamasi.
================================================================================
"""

import copy

from PySide6 import QtWidgets

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz.geometri import sablonlar
from arayuz.geometri.editor import GelismisEditor
from arayuz.geometri.sinir_formu import SinirFormu
from arayuz.tasarim import tokenlar

_log = kaydedici("arayuz.kor.geometri_sayfasi")
A = tokenlar.ARALIK
_EDITOR_EN_AZ_YUKSEKLIK = 36 * A["l"]


def sablon_ogeleri():
    """[(anahtar, gorunen ad)] -- 7 kor turu + 3 yeni duzenek (§10 sirasi)."""
    from cekirdek import uygunluk
    ogeler = [(t, uygunluk.KOR_TURU_ADLARI.get(t, t)) for t in (
        "tek_cubuk", "tek_plaka", "tek_demet", "kare_kafes", "altigen_kafes", "kuresel",
        "tamburlu")]
    ogeler += [(k, _(v)) for k, v in sablonlar.YENI_SABLONLAR.items()]
    return ogeler


class KorGeometriMixin(object):
    """KorSekmesi'ne karisir: sablon secici, gelismis editor, mod gecisi."""

    islem_uygulayici = None

    # ------------------------------------------------------------------ kurulum
    def _geometri_alanlarini_kur(self):
        self.sablon_secici = QtWidgets.QComboBox()
        self.sablon_secici.setAccessibleName(_("Düzenek şablonu"))
        for anahtar, ad in sablon_ogeleri():
            self.sablon_secici.addItem(_(ad), anahtar)
        self.sablon_secici.setToolTip(_(
            "Kor türü değişince bu türün alanları gösterilir; son üç düzenek geometri "
            "ağacı kurar ve gelişmiş geometriye geçer. Geri almak için Ctrl+Z."))
        self.sablon_secici.activated.connect(self._sablon_secildi)
        self.d_gelismis = b.ikincil_dugme(_("Gelişmiş geometriye geç…"), "layers",
                                          _("Şablonu düzenlenebilir bir düğüm ağacına "
                                            "dönüştürür (tek yönlü; Geri Al ile dönülür)."))
        self.d_gelismis.clicked.connect(self.gelismise_gec)
        self.yuz_sinir = SinirFormu(yalniz_yuzler=True)
        self.yuz_sinir.degisti.connect(self._yuz_siniri_degisti)
        self.gelismis_editor = GelismisEditor()
        self.gelismis_editor.setMinimumHeight(_EDITOR_EN_AZ_YUKSEKLIK)
        self.gelismis_editor.agac_islemi.connect(self._agac_islemi)
        self.gelismis_editor.agac_duzenlendi.connect(self._agac_duzenlendi)
        self.gelismis_editor.dugum_secildi.connect(self.dugum_secildi)
        self.gelismis_notu = QtWidgets.QLabel(_(
            "Gelişmiş geometri: model bir düğüm ağacıdır. Şablon sihirbazı kapalıdır; "
            "şablona dönmek için Geri Al (Ctrl+Z)."))
        self.gelismis_notu.setObjectName("soluk")
        self.gelismis_notu.setWordWrap(True)

    def _gelismis_gorunumu(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        d.addWidget(self.gelismis_notu)
        d.addWidget(self.gelismis_editor, 1)
        self.gelismis_gorunumu = w
        return w

    def _gecis_satiri(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.d_gelismis)
        d.addStretch(1)
        return w

    # ------------------------------------------------------------------ durum
    def agac_modunda_mi(self):
        from cekirdek import geometri
        return geometri.agac_modu(self.spec)

    def _mod_goster(self, agac):
        self.sablon_gorunumu.setVisible(not agac)
        self.gelismis_gorunumu.setVisible(agac)

    def _geometri_doldur(self):
        """doldur()'un gelismis kolu: True -> sablon alanlari doldurulmaz."""
        agac = self.agac_modunda_mi()
        self._mod_goster(agac)
        if agac:
            self._tur = "agac"
            self.gelismis_editor.yukle(self.spec)
            return True
        i = self.sablon_secici.findData(self.spec["kor"].get("tur"))
        eski = self.sablon_secici.blockSignals(True)
        self.sablon_secici.setCurrentIndex(max(i, 0))
        self.sablon_secici.blockSignals(eski)
        return False

    def _yuz_sinirini_doldur(self):
        from cekirdek import geometri
        from arayuz.geometri.cizim import bolge_kesitleri
        try:
            kok = geometri.model(self.spec).kok
            dis = bolge_kesitleri(kok)[-1]
            ic = kok.get("ic") or {}
            ic = ic.get("icerik") if ic.get("tur") == "eksenel" else ic
            yon = ic.get("yonelim", "y") if isinstance(ic, dict) else "y"
        except Exception as e:
            _log.info("yuz basina sinir icin dis kesit bulunamadi: %s", e)
            dis, yon = None, "y"
        self.yuz_sinir.ayarla(self.spec["kor"].get("sinir"), dis, False, None, yon)
        self._eksen_form.setRowVisible(self.yuz_sinir, self.yuz_sinir.yuz_basina_uygun())

    # ------------------------------------------------------------------ islemler
    def _spec_islemi(self, yeni_spec, mesaj):
        """Tek geri al adimi: pencere varsa ona, yoksa yerinde."""
        if callable(self.islem_uygulayici):
            self.islem_uygulayici(yeni_spec, mesaj)
            return
        self.spec.clear()
        self.spec.update(copy.deepcopy(yeni_spec))
        self.spec_yukle(self.spec)
        self.bildir()

    def gelismise_gec(self, onaysiz=False):
        """Sablonu agaca donusturur (onay ister; tek yonlu)."""
        from cekirdek import geometri
        if self.spec is None or self.agac_modunda_mi():
            return False
        if not onaysiz and not self._onay_al(
                _("Gelişmiş geometriye geç"),
                _("Şablon düğüm ağacına dönüştürülecek. Sonra sihirbaz kapanır; "
                  "Geri Al (Ctrl+Z) ile dönebilirsiniz.")):
            return False
        try:
            yeni = geometri.gelismise_gec(self.spec)
        except (ValueError, KeyError) as e:
            _log.warning("gelismis moda gecilemedi", exc_info=True)
            self._pencere_bildir(_("Gelişmiş geometriye geçilemedi: {e}").format(e=e), "hata")
            return False
        self._spec_islemi(yeni, _("Gelişmiş geometriye geçildi — geri almak için Ctrl+Z."))
        return True

    def _sablon_secildi(self, _ix=None):
        anahtar = self.sablon_secici.currentData()
        if anahtar in sablonlar.YENI_SABLONLAR:
            self.yeni_sablon_uygula(anahtar)
        elif anahtar and anahtar != self.spec["kor"].get("tur"):
            self.tur_secildi.emit(anahtar)
        self._geometri_doldur()

    def yeni_sablon_uygula(self, anahtar, parametreler=None, diyalogsuz=False):
        """Uc yeni duzenekten birini kurar (diyalog; testte diyalogsuz)."""
        if diyalogsuz:
            try:
                yeni = sablonlar.uret(self.spec, anahtar, parametreler)
            except sablonlar.SablonHatasi as e:
                self._pencere_bildir(str(e), "hata")
                return False
        else:
            from arayuz.geometri import sablon_diyalogu
            yeni = sablon_diyalogu.calistir(self.spec, anahtar, self)
            if yeni is None:
                return False
        self._spec_islemi(yeni, _("Düzenek kuruldu: {ad} — geri almak için Ctrl+Z.").format(
            ad=_(sablonlar.YENI_SABLONLAR[anahtar])))
        return True

    def _agac_islemi(self, yeni_agac, mesaj, secim):
        yeni = copy.deepcopy(self.spec)
        yeni["geometri"] = yeni_agac
        self.gelismis_editor._secili = tuple(secim) if secim else self.gelismis_editor._secili
        self._spec_islemi(yeni, mesaj)

    def _agac_duzenlendi(self, yeni_agac):
        if self.spec is None:
            return
        self.spec["geometri"] = yeni_agac
        self.gelismis_editor.agaci_tazele(self.spec)
        self.bildir()

    def _yuz_siniri_degisti(self, *_a):
        if self._yukleniyor or self.spec is None:
            return
        sinir = self.spec["kor"].setdefault("sinir", {})
        yuzler = self.yuz_sinir.yuzler()
        if yuzler is None:
            sinir.pop("yuzler", None)
        else:
            sinir["yuzler"] = yuzler
        self._ozet_guncelle()
        self.bildir()

    def dugum_sec(self, yol):
        """Onizleme tiklamasi: agacta secer (yalniz gelismis modda)."""
        if self.spec is not None and self.agac_modunda_mi():
            self.gelismis_editor.sec(yol)

    def _pencere_bildir(self, metin, tur="bilgi"):
        pencere = self.window()
        if pencere is not None and pencere is not self:
            b.bildir(pencere, metin, tur)
        self.son_bildirim = metin


def tur_etiketi_metni(tur_adi):
    return _("Düzenek: <b>{tur}</b> — <a href=\"tur\">Türü değiştir…</a> "
             "(model başlığındaki menüyle aynı)").format(tur=tur_adi)

