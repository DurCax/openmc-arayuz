# -*- coding: utf-8 -*-
"""
dogrulama_seridi.py -- ana pencerenin dogrulama akisi: bulgu listesi, alt
dogrulama seridi, bulguya gitme, onizleme/kosu durumlari ve CALISTIR kapisi

arayuz/pencere/ana_pencere.py'den YALNIZ TASINDI (v3 T2, dosya boyu): "dogrulama"
bolumu bir karisim (mixin) sinifinda; AnaPencere bundan (ILK taban olarak)
turer, yani yontem cozumu ve adlar aynidir. _seviye_renk ve _SEVIYE_ADI da
buradadir; ana_pencere'den yeniden disa aktarilir.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import dogrula
from cekirdek.ceviri import _, _n, N_
from cekirdek.gunluk import kaydedici
from arayuz import baslangic_adim, tema
from arayuz.ortak import cumle_basi
from arayuz.pencere import sekme_arayuzu
from arayuz.pencere.model_islemleri import yer_etiketi, yer_sekme_anahtari

# Kaydedici adi tasimadan once neyse o (log satirlari ayni kalir).
_log = kaydedici("arayuz.pencere.ana_pencere")


def _seviye_renk(seviye):
    """Dogrulama seviyesi rengi -- etkin temadan gelir."""
    return tema.renk({"hata": "hata", "uyari": "uyari", "bilgi": "bilgi"}.get(seviye, "bilgi"))


# Yalniz isaretlenir (N_); gosterirken _().
_SEVIYE_ADI = {"hata": N_("Hata"), "uyari": N_("Uyarı"), "bilgi": N_("Bilgi")}
_EKSIK_ADIM = N_("Eksik aşama")
# Adim sayfasi -> o sayfaya goturen bulgu yeri (model_islemleri._YER_SEKME).
_ADIM_YERI = {"malzemeler": "malzemeler", "parcalar": "cubuk", "demet": "demet",
              "kor": "kor"}


class DogrulamaMixin(object):
    """AnaPencere'nin dogrulama yontemleri (bkz. modul belgesi)."""
    # ==================================================================
    # dogrulama
    # ==================================================================
    def _bulgu_ogeleri(self, liste):
        """Bulgulari bir QListWidget'a yazar (acilir liste). Eksik adimlar
        (v3 K1) en ustte bilgi tonunda; onlarin sonucu olan hatalar da."""
        liste.clear()
        self._adim_ogeleri(liste)
        for b in self._bulgular:
            adim = baslangic_adim.adim_bulgusu_mu(self.spec, b)
            seviye_adi = _EKSIK_ADIM if adim else _SEVIYE_ADI.get(b.seviye, b.seviye)
            oge = QtWidgets.QListWidgetItem(
                "%s · %s: %s" % (_(seviye_adi), yer_etiketi(b.yer), cumle_basi(b.mesaj)))
            oge.setForeground(QtGui.QColor(_seviye_renk("bilgi" if adim else b.seviye)))
            oge.setData(QtCore.Qt.UserRole, b.yer)
            tiklama = _("Tıklayınca ilgili sayfaya gider; sağ tık: kılavuzda aç.")
            oge.setToolTip((b.oneri + "\n\n" + tiklama) if b.oneri else tiklama)
            liste.addItem(oge)
        if not self._bulgular:
            oge = QtWidgets.QListWidgetItem(_("✓ Bulgu yok — model tutarlı görünüyor."))
            oge.setForeground(QtGui.QColor(tema.renk("basari")))
            oge.setFlags(QtCore.Qt.ItemIsEnabled)
            liste.addItem(oge)

    def _adim_ogeleri(self, liste: QtWidgets.QListWidget) -> None:
        """Eksik adimlar listenin basinda (tiklaninca adimin sayfasi)."""
        for adim in baslangic_adim.eksik_adimlar(self.spec):
            oge = QtWidgets.QListWidgetItem("%s · %s: %s" % (
                _(_EKSIK_ADIM), adim.baslik, adim.aciklama))
            oge.setForeground(QtGui.QColor(_seviye_renk("bilgi")))
            oge.setData(QtCore.Qt.UserRole, _ADIM_YERI[adim.sekme])
            oge.setToolTip(_("Tıklayınca ilgili sayfaya gider."))
            liste.addItem(oge)

    def _dogrula(self, veri=False):
        try:
            self._bulgular = dogrula.tum_kontroller(self.spec, veri_kontrolu=veri)
        except Exception as e:                                  # noqa: BLE001
            _log.exception("dogrulama sirasinda hata")
            self._bulgular = [dogrula.Bulgu("hata", "dogrulama",
                                            _("doğrulama sırasında hata: %s") % e)]
        self._bulgu_ogeleri(self.dogrulama)
        self._serit_guncelle()
        self.s_calistir.kapi_guncelle()
        self.s_analiz.kapi_guncelle()
        self.s_tukenme.kapi_guncelle()
        self._isaretleri_guncelle()
        if veri:
            self.bildir_mesaj(_("Doğrulama yenilendi (veri kütüphanesi dahil)."), "bilgi")

    def _serit_guncelle(self, ipucu=None):
        """Alt dogrulama seridi: ozet, rozet, ilk bulgu, sonraki adim."""
        if ipucu is None:
            ipucu = self._sonraki_ipucu
        self._sonraki_ipucu = ipucu
        self._adim_rehberini_guncelle()
        # Kapi her serit tazelenisinde: editore donuste ust cubuk dugmesi
        # (model_gorunur) onizleme sinyali gelene dek acik kaliyordu.
        self._kosu_dugmesi_guncelle()
        if self._eksik_adim_seridi():
            return
        n = {s: sum(1 for b in self._bulgular if b.seviye == s)
             for s in ("hata", "uyari", "bilgi")}
        if n["hata"]:
            seviye, ozet = "hata", _n("Doğrulama: {n} hata", "Doğrulama: {n} hata",
                                      n["hata"]).format(n=n["hata"])
        elif n["uyari"]:
            seviye, ozet = "uyari", _n("Doğrulama: {n} uyarı", "Doğrulama: {n} uyarı",
                                       n["uyari"]).format(n=n["uyari"])
        else:
            seviye, ozet = "basari", _("Doğrulama: hata yok")
        rozet = (_n("{n} bilgi", "{n} bilgi", n["bilgi"]).format(n=n["bilgi"]) if n["bilgi"]
                 else _n("{n} uyarı", "{n} uyarı", n["uyari"]).format(n=n["uyari"])
                 if n["uyari"] else _("Tamam"))
        onemli = [b for b in self._bulgular if b.seviye in ("hata", "uyari")]
        ilk = ("%s · %s" % (yer_etiketi(onemli[0].yer), cumle_basi(onemli[0].mesaj))
               if onemli else "")
        self.serit.ayarla(seviye, ozet, rozet, ilk, ipucu)
        self.serit.setToolTip(_("{h} hata, {u} uyarı, {b} bilgi").format(
            h=n["hata"], u=n["uyari"], b=n["bilgi"]))

    def _eksik_adim_seridi(self) -> bool:
        """Model henuz kuruluyorsa (eksik adim) serit BILGI tonunda adimi
        soyler -- hata kirmizisi degil (v3 K1). Gosterildiyse True."""
        adim = baslangic_adim.siradaki(self.spec)
        if adim is None:
            return False
        tamam, toplam = baslangic_adim.ilerleme(self.spec)
        sira = _("Sıradaki aşama: {baslik} — {aciklama}").format(
            baslik=adim.baslik, aciklama=adim.aciklama)
        self.serit.ayarla("bilgi", _("Model kuruluyor: {tamam}/{toplam} aşama").format(
            tamam=tamam, toplam=toplam), _(_EKSIK_ADIM), sira,
            _("Çalıştır, eksik aşamalar tamamlanınca açılır."))
        self.serit.setToolTip(_("Eksik aşamalar tamamlanınca doğrulama sonucu burada "
                                "görünür."))
        return True

    def _bulgu_listesini_ac(self):
        self._bulgu_ogeleri(self.bulgu_acilir.liste)
        self.bulgu_acilir.goster(self.serit.rozet)

    def _acilirdan_git(self, oge):
        self.bulgu_acilir.hide()
        self._bulguya_git(oge)

    def _ilk_bulguya_git(self):
        adim = baslangic_adim.siradaki(self.spec)
        if adim is not None:
            self._adima_git(adim.sekme)
            return
        onemli = [b for b in self._bulgular if b.seviye in ("hata", "uyari")]
        if onemli:
            self.sekmeye_gitmeyi_dene(onemli[0].yer)

    def sekmeye_gitmeyi_dene(self, yer):
        """Bulgunun yerinden sayfaya gider; sayfa destekliyorsa odaklar."""
        anahtar = yer_sekme_anahtari(yer)
        if anahtar is None:
            return False
        if self.baslangic_acik_mi():
            self._editoru_goster()
        if not self.sekmeye_git(anahtar):
            return False
        sekme_arayuzu.odakla(self.sekme_widget(anahtar), yer)
        return True

    def _bulguya_git(self, oge):
        """Dogrulama satirina tiklayinca ilgili sayfayi ac."""
        self.sekmeye_gitmeyi_dene(oge.data(QtCore.Qt.UserRole))

    def _onizleme_durum(self, mesaj, basarili):
        # Yalnizca SORUN bildirilir: her duzenlemeden sonra gelen "onizleme
        # guncel" mesaji gereksizdir.
        if not basarili and not self.baslangic_acik_mi():
            self.bildir_mesaj(mesaj, "uyari", 8000)
        self.s_calistir.kapi_guncelle()
        self.s_tukenme.kapi_guncelle()
        self._durum_ipucu_guncelle()
        self._kosu_dugmesi_guncelle()

    def _sekme_durum_mesaji(self, mesaj, basarili):
        """Calistir/Analiz/Tukenme bildirimi."""
        self.bildir_mesaj(mesaj, "basari" if basarili else "uyari", 8000)
        self._isaretleri_guncelle()

    def _kosu_durumu_degisti(self, kosuyor):
        self.ust.kosu_durumu(kosuyor)
        if not kosuyor:
            self._kosu_dugmesi_guncelle()

    def _kosu_dugmesi_guncelle(self):
        if not self.ust.kosuyor_mu():
            self.ust.kosu_izni(*self._kosu_izni())

    def _kosu_izni(self):
        """CALISTIR kapisi: once model kurulmali (eksik adim yok), geometri
        cizilmeli, hata olmamali."""
        adim = baslangic_adim.siradaki(self.spec)
        if adim is not None:
            n = len(baslangic_adim.eksik_adimlar(self.spec))
            return False, _n(
                "Model henüz kurulmadı: {n} aşama eksik. Sıradaki aşama: {baslik} — "
                "{aciklama} Alttaki aşama rehberinden ilgili sayfaya gidin.",
                "Model henüz kurulmadı: {n} aşama eksik. Sıradaki aşama: {baslik} — "
                "{aciklama} Alttaki aşama rehberinden ilgili sayfaya gidin.", n).format(
                    n=n, baslik=adim.baslik, aciklama=adim.aciklama)
        if dogrula.hata_var(self._bulgular):
            n = sum(1 for b in self._bulgular if b.seviye == "hata")
            return False, _n("Doğrulamada %d hata var — önce bunları giderin. Alttaki "
                             "rozete tıklayıp bir bulguyu seçince ilgili sayfaya "
                             "gidersiniz.",
                             "Doğrulamada %d hata var — önce bunları giderin. Alttaki "
                             "rozete tıklayıp bir bulguyu seçince ilgili sayfaya "
                             "gidersiniz.", n) % n
        if not self.onizleme.cizildi_mi():
            return False, _("Geometri önizlemesi henüz çizilmedi. Önce çiz, "
                            "sonra çalıştır: yanlış geometriyle saatlerce koşmamak "
                            "için önizlemenin çizilmesi bekleniyor.")
        uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        if uyari:
            return True, _n("Çalıştırılabilir. %d uyarı var — sonucu etkileyebilir, "
                            "doğrulama listesini gözden geçirin.",
                            "Çalıştırılabilir. %d uyarı var — sonucu etkileyebilir, "
                            "doğrulama listesini gözden geçirin.", uyari) % uyari
        return True, _("Model çalıştırılmaya hazır.")

    def _calistir_menuden(self):
        if self.baslangic_acik_mi():
            return
        self.sekmeye_git("calistir")
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_calistir.calistir()
