# -*- coding: utf-8 -*-
"""
================================================================================
 onizleme_kapsam.py  --  Onizleme KAPSAMI (v3 K5): neyin cizildigi + kapi
================================================================================

 KAPSAM (otomatik kip)
   Parcalar sayfasi  -> secili pin / plaka / tambur
   Demet sayfasi     -> secili demet
   Geometri sayfasi  -> gelismis geometride secili dugum (kafes, kap, bilesen);
                        sablon modunda, kokte ya da malzeme dugumunde tam kor
   diger sayfalar    -> tam model
   "Tam model" kipi her sayfada tam modeli cizer. Alt model cekirdek/alt_model.py
   ile kurulur (yansitici sinir, tek evren); cizim iscisine SIRADAN bir spec
   olarak gider -- protokol degismedi.

 CALISTIR KAPISI YALNIZ TAM MODELE BAKAR
   Kapsamli cizim tam modeli denetlemez. Tam modelin ozeti degistiyse kapsamli
   cizimin ardindan iscide TAM MODEL icin ayri bir "kontrol" istegi surulur
   (kur + init, kesit yok); kapi onun sonucuyla acilir/kapanir. Ayni tam
   modelde kapsam degisimi (baska pin secmek) kontrolu tekrarlamaz. Kapsamli
   cizim basarisiz olsa da kapi tam modelin sonucunu gosterir.

 GOSTERGE
   Kapsamli cizimde gosterge yalniz kesitte gercekten bulunan malzemeleri
   listeler (iscinin id haritasindan).

 Kapsamli cizimde onizlemeye tiklayip dugum secme ve dugum vurgusu kapalidir:
 id haritasi tam modelin degil alt modelin hucrelerini tasir.
================================================================================
"""

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
from PySide6 import QtCore, QtWidgets

from cekirdek import alt_model, cizim_sureci as cs
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.onizleme")

KAPSAM_OTOMATIK, KAPSAM_TAM = "otomatik", "tam"
KAPSAM_SECENEKLERI = ((KAPSAM_OTOMATIK, N_("Otomatik")), (KAPSAM_TAM, N_("Tam model")))
_MALZEME_KANALI = 2               # id haritasi [hucre, ornek, malzeme] (cizim_sureci)


@dataclass(frozen=True)
class KapsamSonucu:
    """Cizilecek model: spec None ise tam model; etiket gorunen kapsam adi."""
    spec: dict | None = None
    etiket: str = ""
    hata: str | None = None


TAM_MODEL = KapsamSonucu()


def kullanilan_gosterge(meta: dict | None, geomlar) -> list:
    """meta["gosterge"]nin yalniz id haritalarinda bulunan malzemeleri (sira korunur).
    gosterge ile renkler ayni dongude uretilir (cizim_sureci.Oturum.ozellikler)."""
    if not meta:
        return []
    var = set()
    for geom in geomlar:
        var.update(int(m) for m in np.unique(geom[..., _MALZEME_KANALI]) if m >= 0)
    return [g for kimlik, g in zip(meta.get("renkler", {}), meta.get("gosterge", []))
            if int(kimlik) in var]


class KapsamMixin(object):
    """OnizlemeWidget'a karisir: kapsam secici, saglayici, tam model kapi denetimi."""

    def _kapsam_kur(self) -> None:
        self._kapsam_saglayici = None
        self.etkin_kapsam = TAM_MODEL
        self._son_kapsamli = False         # son cizim alt model miydi (tiklama/vurgu kapali)
        self._tam_ozet = None              # tam modelin (self.spec) son bilinen ozeti
        self._kapi_ozet = None             # kapi sonucunun ait oldugu tam model ozeti
        self._tam_kirli = False            # gecikmeli istek tam modeli degistirmis olabilir
        self.kapsam = QtWidgets.QComboBox()
        # EN "Automatic" dar panelde kesilmesin (Q1-07): en uzun ogeye gore genislik.
        self.kapsam.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.kapsam.setMinimumContentsLength(10)
        for veri, ad in KAPSAM_SECENEKLERI:
            self.kapsam.addItem(_(ad), veri)
        self.kapsam.setToolTip(_(
            "Otomatik: Parçalar sayfasında seçili parça, Demet sayfasında seçili demet,\n"
            "gelişmiş Geometri'de seçili düğüm çizilir (yansıtıcı sınırlı alt model);\n"
            "diğer sayfalarda tam model. Tam model: her zaman bütün model.\n"
            "Çalıştır kapısı her iki kipte de yalnız tam modele bakar."))
        self.kapsam_etiket = QtWidgets.QLabel(_("Kapsam:"))
        self.kapsam_bilgi = QtWidgets.QLabel("")
        self.kapsam_bilgi.setObjectName("kucuk")
        self.kapsam.currentIndexChanged.connect(lambda *_a: self._ciz())

    def kapsam_saglayici_ayarla(self, saglayici: Callable[[dict], KapsamSonucu]) -> None:
        """saglayici(spec) -> KapsamSonucu: otomatik kipte neyin cizilecegi."""
        self._kapsam_saglayici = saglayici
        self.kapsam_degisti()

    def kapsam_kipi(self) -> str:
        return self.kapsam.currentData()

    def kapsam_degisti(self) -> None:
        """Secim/sayfa degisti: tam model ayni, yalniz cizilecek kapsam degisebilir
        (kapi kapanmaz)."""
        if not self._kapandi and self.spec is not None:
            self._sayac.start()

    def _kapsam_coz(self) -> KapsamSonucu:
        if self.kapsam_kipi() == KAPSAM_TAM or self._kapsam_saglayici is None:
            return TAM_MODEL
        try:
            sonuc = self._kapsam_saglayici(self.spec) or TAM_MODEL
        except alt_model.AltModelHatasi as e:   # secim bayat/bozuk: tam model cizilir, yazilir
            _log.warning("onizleme kapsami kurulamadi; tam model cizilecek", exc_info=True)
            return KapsamSonucu(None, "", hata=str(e.args[0] if e.args else e))
        return sonuc

    def _kapsam_bilgisi(self, kapsam: KapsamSonucu) -> None:
        if kapsam.hata:
            self.kapsam_bilgi.setText(_("tam model (alt model kurulamadı)"))
            self.kapsam_bilgi.setToolTip(kapsam.hata)
        else:
            self.kapsam_bilgi.setText(kapsam.etiket if kapsam.spec is not None else "")
            self.kapsam_bilgi.setToolTip("")

    # ------------------------------------------------------------------ kapi
    # Kapi durumu TEK yerden yazilir: _kapi_bilinmez() ya da _kapi_kaydet().
    # _son_basarili hic tek basina sifirlanmaz; aksi halde (inceleme bulgusu)
    # basarisi silinmis ama ozeti "biliniyor" kalan kapi kapsamli cizimden
    # sonra yeniden denetlenmez ve kalici kapali kalirdi.
    def _kapi_bilinmez(self) -> None:
        """Kapi sonucu artik gecerli degil: kapali, ilk firsatta yeniden denetlenir."""
        self._son_basarili = False
        self._kapi_ozet = None

    def _kapi_kaydet(self, ozet: str | None, basarili: bool, hata: str | None = None,
                     gecici: bool = False) -> None:
        """Tam modelin sonucu. gecici (cokme, zaman asimi): kapi kapali ama sonuc
        hatirlanmaz -- sonraki kapsamli cizim yeniden dener."""
        self._son_basarili = basarili
        self._son_hata = None if basarili else (hata or "")
        self._kapi_ozet = None if gecici else ozet

    def _tam_ozet_guncelle(self, ozet: str) -> None:
        """Tam model degistiyse kapi bilinmez olur (kapali)."""
        self._tam_kirli = False
        if ozet != self._tam_ozet:
            self._tam_ozet = ozet
            self._kapi_bilinmez()

    def _kapi_bilinmiyor(self) -> bool:
        return self._kapi_ozet is None or self._kapi_ozet != self._tam_ozet

    def _kapi_acik(self) -> bool:
        tam_suruyor = self._istek is not None and not self._istek.get("kapsam")
        return (self._son_basarili and self._son_hata is None and not self._kapi_bilinmiyor()
                and not tam_suruyor and not (self._tam_kirli and self._sayac.isActive()))

    def _kapi_denetle(self) -> None:
        """Kapsamli cizimden sonra: tam model bu ozet icin denetlenmediyse 'kontrol'."""
        if self._kapandi or self.spec is None or not self._kapi_bilinmiyor():
            return
        self._istek = {"kontrol": True, "kapi": True, "kapsam": False, "kesitler": [],
                       "t0": time.perf_counter(), "tam_ozet": self._tam_ozet, "toplanan": {}}
        self._istek["no"] = self._istemci.iste({"tur": cs.ISTEK_KONTROL, "spec": self.spec})

    def _kapi_sonucu(self, ist: dict, b: dict, gecici: bool = False) -> None:
        if b.get("durum") == cs.DURUM_TAMAM:
            self._kapi_kaydet(ist["tam_ozet"], True)
            self.durum.emit(_("Önizleme: tam model denetlendi."), True)
            return
        self._kapi_kaydet(ist["tam_ozet"], False, b.get("iz") or b.get("hata"), gecici=gecici)
        self.durum.emit(_("Tam model kurulamadı (Çalıştır kapalı): %s") % (b.get("hata") or ""),
                        False)


# ============================================================================
# pencere baglantisi: sayfa + secim -> kapsam
# ============================================================================

def kapsam_sonucu(spec: dict, sayfa: str | None, parca: tuple | None = None,
                  demet: str | None = None, dugum: tuple | None = None) -> KapsamSonucu:
    """Sayfa ve sayfadaki secimden kapsam (saf). parca: (tur, ad); demet: ad;
    dugum: gelismis geometride secili yol (sablon modunda None)."""
    sonuc = None
    if sayfa == "parcalar" and parca and parca[0] in alt_model.PARCA_TURLERI and parca[1]:
        sonuc = alt_model.parca_kapsami(spec, parca[0], parca[1])
    elif sayfa == "demet" and demet:
        sonuc = alt_model.parca_kapsami(spec, "demet", demet)
    elif sayfa == "kor" and dugum:
        sonuc = alt_model.dugum_kapsami(spec, dugum)
    return TAM_MODEL if sonuc is None else KapsamSonucu(sonuc.spec, sonuc.etiket)


class PencereKapsami(QtCore.QObject):
    """Ana pencerenin sayfa/secim sinyallerini onizleme kapsamina baglar."""

    def __init__(self, pencere: QtWidgets.QMainWindow):
        super().__init__(pencere)
        self._p = pencere
        on = pencere.onizleme
        pencere.s_cubuk.oge_secildi.connect(lambda: self._tetik("parcalar"))
        pencere.s_demet.oge_secildi.connect(lambda: self._tetik("demet"))
        pencere.s_kor.dugum_secildi.connect(lambda *_a: self._tetik("kor"))
        pencere.yigin_sekme.currentChanged.connect(lambda *_a: on.kapsam_degisti())
        on.kapsam_saglayici_ayarla(self)

    def _tetik(self, sayfa: str) -> None:
        if self._p.gecerli_sekme() == sayfa:
            self._p.onizleme.kapsam_degisti()

    def __call__(self, spec: dict) -> KapsamSonucu:
        p = self._p
        sayfa = p.gecerli_sekme()
        dugum = (p.s_kor.gelismis_editor.secili_yol()
                 if sayfa == "kor" and p.s_kor.agac_modunda_mi() else None)
        return kapsam_sonucu(spec, sayfa, parca=p.s_cubuk.secili_oge(),
                             demet=p.s_demet.secili_oge(), dugum=dugum)
