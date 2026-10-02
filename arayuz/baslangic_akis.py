# -*- coding: utf-8 -*-
"""
baslangic_akis.py -- ana pencerenin baslangic akisi (v3 K1): acilis karari,
"Sifirdan" model, adim rehberi seridi ve "acilista goster" ayari

AnaPencere bu karisimdan (mixin) turer; pencerenin kendi dosyasina yalniz
uc cagri eklenir (_baslangic_akisini_kur, acilis_akisi, _adim_hatalarini_ayikla).

ACILIS (acilis_akisi)
  Komut satirinda dosya yoksa: "acilista goster" ayari KAPALI ve son kullanilan
  bir proje varsa o acilir; aksi halde baslangic ekrani. Ornek dosyasi hicbir
  zaman kendiliginden yuklenmez. (K2'nin "veri yoksa Veri sayfasi" kancasi
  bundan ONCE calisir; sira: veri -> baslangic secimi.)
"""

from PySide6 import QtCore

from arayuz import baslangic_adim
from arayuz.baslangic_rehber import AdimRehberi
from arayuz.pencere.model_islemleri import yer_sekme_anahtari
from cekirdek import sema
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ACILISTA_GOSTER_AYARI = "baslangic/acilista_goster"
_SIFIRDAN_ADI = N_("Yeni model")


_KAPALI_DEGERLER = ("false", "0", "no")


def acilista_goster_mi(ayarlar: QtCore.QSettings) -> bool:
    """QSettings'teki tercih. Yalniz acik "kapali" degerleri (false/0/no)
    False doner; yok, bos ("") ya da okunamayan deger varsayilan True'dur
    (eski davranis: baslangic ekrani)."""
    try:
        deger = ayarlar.value(ACILISTA_GOSTER_AYARI, True)
    except (RuntimeError, TypeError, ValueError):
        _log.warning("acilista goster ayari okunamadi; varsayilan (goster)", exc_info=True)
        return True
    return str(deger).strip().lower() not in _KAPALI_DEGERLER


def sifirdan_spec(kor_turu: str) -> dict:
    """Gercekten bos model; yalniz kor turu (rehberli turlerden biri)."""
    if kor_turu not in baslangic_adim.SIFIRDAN_TURLERI:
        raise ValueError(_("sıfırdan başlatılamayan kor türü: %s") % kor_turu)
    return sema.yeni_spec(_(_SIFIRDAN_ADI), kor_turu=kor_turu)


class BaslangicAkisi(object):
    """AnaPencere'nin baslangic akisi yontemleri (bkz. modul belgesi)."""

    def _baslangic_akisini_kur(self) -> None:
        """Rehber seridini dogrulama seridinin ustune yerlestirir, sinyalleri baglar.
        _yerlesim_kur'dan SONRA cagrilir."""
        # Acilis on kancalari (K2: "veri yoksa Veri sayfasi"): acilis_akisi
        # baslangic secimine gecmeden ONCE sirayla cagirir.
        self._acilis_on_kancalari = []
        self.adim_rehberi = AdimRehberi()
        duzen = self.centralWidget().layout()
        duzen.insertWidget(duzen.indexOf(self.serit), self.adim_rehberi)
        self.adim_rehberi.adim_secildi.connect(self._adima_git)
        self.yigin.currentChanged.connect(lambda *_a: self._adim_rehberini_guncelle())
        self.baslangic.sifirdan_istendi.connect(self._sifirdan_basla)
        self.baslangic.acilista_goster.setChecked(acilista_goster_mi(self.ayarlar))
        self.baslangic.acilista_goster_degisti.connect(
            lambda acik: self.ayarlar.setValue(ACILISTA_GOSTER_AYARI, bool(acik)))

    def acilis_akisi(self, dosya_verildi: bool = False) -> None:
        """Acilis: once on kancalar; sonra model yoksa baslangic secimi.
        Komut satirinda dosya verildiyse (acilsin acilmasin) son proje
        DENENMEZ; tercih kapaliysa son proje, aksi halde baslangic ekrani."""
        for kanca in list(self._acilis_on_kancalari):
            kanca()
        if self._model_var:
            return
        if not dosya_verildi and not acilista_goster_mi(self.ayarlar):
            son = self._son_listesi()
            if son and self.proje_ac(son[0]):
                return
            if son:
                _log.warning("son proje acilamadi, baslangic ekrani: %s", son[0])
        self.baslangici_goster()

    def _sifirdan_basla(self, kor_turu: str) -> bool:
        """"Sifirdan basla": bos model + Malzemeler sayfasi + adim rehberi."""
        if not self._kaydetme_sor():
            return False
        try:
            spec = sifirdan_spec(kor_turu)
        except ValueError as e:
            _log.exception("sifirdan model kurulamadi: %s", kor_turu)
            self.bildir_mesaj(str(e), "hata", 8000)
            return False
        self._proje_kur(spec, proje_yolu=None, ornek_kaynagi=None)
        self.sekmeye_git("malzemeler", sessiz=True)
        self._adim_rehberini_guncelle()
        self.bildir_mesaj(_("Boş model açıldı. Alttaki aşama rehberini izleyin: malzeme → "
                            "parça → geometri."), "bilgi", 8000)
        return True

    def _adima_git(self, sekme: str) -> None:
        if self.baslangic_acik_mi():
            self._editoru_goster()
        self.sekmeye_git(sekme)

    def _adim_rehberini_guncelle(self) -> None:
        rehber = getattr(self, "adim_rehberi", None)
        if rehber is not None:
            rehber.guncelle(self.spec, editorde=not self.baslangic_acik_mi())

    def _adim_hatalarini_ayikla(self, hata: dict) -> dict:
        """Kenar cubugu hata sayilari ({sekme: n}) kodlu bosluk bulgulari
        dusulmus olarak (YENI sozluk): eksik asamanin sayfasi "!" (hata) degil
        "•" (eksik) gorunur. Gercek hatalar (kodsuz) aynen sayilir."""
        dusen = {}
        for bulgu in self._bulgular:
            if bulgu.seviye == "hata" and baslangic_adim.adim_bulgusu_mu(bulgu):
                sekme = yer_sekme_anahtari(bulgu.yer)
                dusen[sekme] = dusen.get(sekme, 0) + 1
        return {s: n - dusen.get(s, 0) for s, n in hata.items() if n - dusen.get(s, 0) > 0}
