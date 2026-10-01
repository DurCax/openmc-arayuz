# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_paneli.py  --  "Uygunluk" karti (Dalga S-2; Calistir/Sonuclar sayfasi)
================================================================================
 Koşu bitince (ya da kayitli kosu yuklenince) cekirdek/uygunluk_denetimi
 bulgularini listeler: kural kimligi, seviye ikonu, bulgu ve oneri; kaynak ve
 etiket ipucunda. Sorunlar once gelir (rapor_uygunluk.sirala).

   p = UygunlukPaneli()
   p.profilleri_ayarla(("A", "D"))       # spec'ten; sinyal YAYMAZ
   p.denetle(spec, kosu_dizini)          # denetler ve gosterir
   p.profiller_degisti -> tuple          # kullanici kutu degistirdi (spec'e yazilir)
   p.git_istendi -> str                  # sayfa anahtari (uygunluk.SEKMELER)

 Durust cerceve metni (profiller.durust_cerceve) AYNEN gosterilir. Kılavuz
 baglantisi icin KILAVUZ_BOLUMU ayrilmistir (yardim.ac henuz yok; simdilik metin).
 Renk/aralik tokenlardan; ikonlar tema renk tokenlariyla boyanir.
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz import tema
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon
from cekirdek import rapor_uygunluk
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

A = tokenlar.ARALIK
_log = kaydedici(__name__)

KILAVUZ_BOLUMU = "uygunluk-denetimi"     # ileride yardim.ac(KILAVUZ_BOLUMU)
_IKON_BOYUT = 16
_LISTE_EN_AZ = 160
_ROL_KURAL = QtCore.Qt.UserRole
_ROL_HEDEF = QtCore.Qt.UserRole + 1

# (durum, seviye) -> (ikon, renk tokeni)
_IKONLAR = {
    ("karsilanmadi", "hata"): ("circle-x", "hata"),
    ("karsilanmadi", "uyari"): ("triangle-alert", "uyari"),
    ("karsilanmadi", "bilgi"): ("circle-alert", "bilgi"),
    ("bilgi", None): ("info", "bilgi"),
    ("uygulanamadi", None): ("circle-dot", "metin_soluk"),
    ("karsilandi", None): ("circle-check", "basari"),
}
_DURUM_ADLARI = {"karsilandi": N_("karşılandı"), "karsilanmadi": N_("karşılanmadı"),
                 "uygulanamadi": N_("uygulanamadı"), "bilgi": N_("not")}


def hedef_sayfa(kural):
    """Bulgunun duzeltilecegi sayfa anahtari; yoksa None.
    K1/K2 Hesap ayarlari (pasif cevrim, parcacik); K3 kayip parcacik -> Geometri;
    K4 sicakligi tanimsiz malzeme -> Malzemeler."""
    if kural == "K3":
        return "kor"
    if kural.startswith(("K1", "K2")):
        return "ayarlar"
    if kural == "K4-sicaklik":
        return "malzemeler"
    return None


def _ikon_bilgisi(bulgu):
    durum = getattr(bulgu, "durum", "bilgi")
    anahtar = (durum, bulgu.seviye if durum == "karsilanmadi" else None)
    return _IKONLAR.get(anahtar, ("info", "bilgi"))


def _profil_kutulari():
    from cekirdek.uygunluk_denetimi.profiller import PROFIL_KIMLIKLERI, profil_getir
    kutular = {}
    for kimlik in PROFIL_KIMLIKLERI:
        p = profil_getir(kimlik)
        kutu = QtWidgets.QCheckBox("%s · %s" % (kimlik, p.gorunen_ad()))
        kutu.setToolTip(_(p.aciklama))
        kutular[kimlik] = kutu
    return kutular


def _degerlendirilemeyen_kurallar(bulgular):
    """'uygulanamadi' bulgusu olan ayri kural sayisi (bir kural birden cok
    bulgu verebilir)."""
    return len({b.kural for b in bulgular if getattr(b, "durum", None) == "uygulanamadi"})


class UygunlukPaneli(b.Kart):
    """Uygunluk denetimi bulgulari, profil secimi ve durust cerceve."""

    profiller_degisti = QtCore.Signal(tuple)
    git_istendi = QtCore.Signal(str)

    def __init__(self, parent=None):
        self.d_git = b.duz_dugme(_("Bulguya git"), "external-link")
        self.d_git.setEnabled(False)
        self.d_git.setToolTip(_("Seçili bulgunun düzeltileceği sayfayı açar."))
        super().__init__(_("Uygunluk"),
                         aciklama=_("Koşunun Monte Carlo iyi uygulaması ve standartların "
                                    "isteyeceği kanıta göre denetimi."),
                         eylem=self.d_git, parent=parent)
        self._yukleniyor = False
        self.kutular = _profil_kutulari()
        self.govde.addLayout(self._profil_satiri())
        self.govde.addLayout(self._ozet_satiri())
        self.liste = QtWidgets.QListWidget()
        self.liste.setWordWrap(True)
        self.liste.setMinimumHeight(_LISTE_EN_AZ)
        self.liste.setAccessibleName(_("Uygunluk bulguları"))
        self.liste.currentItemChanged.connect(self._secim_degisti)
        self.liste.itemDoubleClicked.connect(self._ogeye_git)
        self.d_git.clicked.connect(self._secilene_git)
        self.ekle(self.liste)
        self.usl_notu = self._metin("uyari")
        self.cerceve = self._metin(None)
        self.kilavuz = self._metin(None)
        self.kilavuz.setText(_("Kuralların açıklaması: Kullanıcı kılavuzu → \"Uygunluk "
                               "denetimi\" bölümü; kaynak tablosu docs/STANDARTLAR.md §3."))
        from cekirdek.uygunluk_denetimi.profiller import durust_cerceve
        self.cerceve.setText(durust_cerceve())
        self.usl_notu.hide()

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _profil_satiri(self):
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["m"])
        etiket = QtWidgets.QLabel(_("Profiller:"))
        etiket.setObjectName("ikincil")
        satir.addWidget(etiket)
        for kutu in self.kutular.values():
            kutu.toggled.connect(self._kutu_degisti)
            satir.addWidget(kutu)
        satir.addStretch(1)
        return satir

    def _ozet_satiri(self):
        self.rozet = b.Rozet("", "notr")
        self.ozet = QtWidgets.QLabel("")
        self.ozet.setObjectName("kucuk")
        self.ozet.setWordWrap(True)
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["s"])
        satir.addWidget(self.rozet)
        satir.addWidget(self.ozet, 1)
        return satir

    def _metin(self, renk):
        w = QtWidgets.QLabel("")
        w.setWordWrap(True)
        w.setObjectName("kucuk")
        w.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        if renk:
            w.setStyleSheet("color: %s;" % tema.renk(renk))
        return self.ekle(w)

    # ------------------------------------------------------------------
    # profil secimi
    # ------------------------------------------------------------------
    def profilleri_ayarla(self, profiller):
        """Kutulari secime gore isaretler (sinyal YAYMAZ)."""
        self._yukleniyor = True
        try:
            for kimlik, kutu in self.kutular.items():
                kutu.setChecked(kimlik in profiller)
        finally:
            self._yukleniyor = False

    def secili(self):
        return tuple(k for k, kutu in self.kutular.items() if kutu.isChecked())

    def _kutu_degisti(self, *_a):
        if not self._yukleniyor:
            self.profiller_degisti.emit(self.secili())

    # ------------------------------------------------------------------
    # gosterim
    # ------------------------------------------------------------------
    def denetle(self, spec, kosu_dizini):
        """Secili profillerle denetler ve gosterir. Girdi hatasi panelde gorunur."""
        profiller = self.secili()
        bulgular, hata = rapor_uygunluk.denetle(spec, kosu_dizini, profiller)
        if hata:
            self.hata_goster(hata)
        else:
            self.goster(bulgular, profiller)

    def temizle(self):
        self.liste.clear()
        self.rozet.setText("")
        self.rozet.tur_ayarla("notr")
        self.ozet.setText("")
        self.usl_notu.hide()
        self.d_git.setEnabled(False)

    def goster(self, bulgular, profiller, vv=None):
        """Bulgulari (DenetimBulgusu) listeler; sorunlar once."""
        from cekirdek.uygunluk_denetimi.denetle import ozet
        self.temizle()
        for bulgu in rapor_uygunluk.sirala(bulgular):
            self.liste.addItem(self._oge(bulgu))
        if not profiller:
            self.ozet.setText(_("Hiçbir profil seçilmedi; denetim yapılmadı."))
            return
        sayi = ozet(bulgular)
        self._rozet_yaz(sayi["seviye"], sayi["durum"]["karsilanmadi"],
                        sayi["durum"]["karsilandi"], _degerlendirilemeyen_kurallar(bulgular))
        self.ozet.setText(_("Profiller %s · %d karşılandı · %d karşılanmadı · %d "
                            "uygulanamadı · %d not") % (
            ", ".join(profiller), sayi["durum"]["karsilandi"],
            sayi["durum"]["karsilanmadi"], sayi["durum"]["uygulanamadi"],
            sayi["durum"]["bilgi"]))
        notu = rapor_uygunluk.usl_notu(profiller, vv)
        self.usl_notu.setText(notu)
        self.usl_notu.setVisible(bool(notu))

    def hata_goster(self, metin):
        """Denetim yapilamadi (bozuk uygunluk_girdisi.json vb.)."""
        self.temizle()
        oge = QtWidgets.QListWidgetItem(ikon("circle-x", "hata", _IKON_BOYUT), metin)
        oge.setToolTip(_("Günlük dosyasında ayrıntı var."))
        self.liste.addItem(oge)
        self.rozet.setText(_("Denetlenemedi"))
        self.rozet.tur_ayarla("hata")

    def _rozet_yaz(self, seviye, karsilanmayan, karsilanan=1, degerlendirilemeyen=0):
        """Hata > uyari > not > degerlendirme kapsami. Hicbir kural
        degerlendirilmediyse (statepoint yok vb.) yesil 'Sorun yok' DEGIL."""
        if seviye["hata"]:
            metin, tur = _("%d hata") % seviye["hata"], "hata"
        elif seviye["uyari"]:
            metin, tur = _("%d uyarı") % seviye["uyari"], "uyari"
        elif karsilanmayan:
            metin, tur = _("%d not") % karsilanmayan, "bilgi"
        elif not karsilanan:
            metin, tur = _("Değerlendirilemedi: %d kural") % degerlendirilemeyen, "notr"
        elif degerlendirilemeyen:
            metin, tur = (_("%d kontrol geçti · %d kural değerlendirilemedi")
                          % (karsilanan, degerlendirilemeyen), "notr")
        else:
            metin, tur = _("Sorun yok"), "basari"
        self.rozet.setText(metin)
        self.rozet.tur_ayarla(tur)

    def _oge(self, bulgu):
        from cekirdek.uygunluk_denetimi.kurallar import etiket_metni
        durum = getattr(bulgu, "durum", "bilgi")
        satirlar = ["%s · %s — %s" % (bulgu.kural, _(_DURUM_ADLARI.get(durum, durum)),
                                      bulgu.mesaj)]
        if bulgu.oneri and durum != "karsilandi":
            satirlar.append(_("Öneri: %s") % bulgu.oneri)
        ad, renk = _ikon_bilgisi(bulgu)
        oge = QtWidgets.QListWidgetItem(ikon(ad, renk, _IKON_BOYUT), "\n".join(satirlar))
        hedef = hedef_sayfa(bulgu.kural) if durum != "karsilandi" else None
        ipucu = [_("Kaynak: %s") % bulgu.kaynak, _("Etiket: %s") % etiket_metni(bulgu.etiket),
                 _("Profil: %s") % bulgu.profil]
        if hedef:
            ipucu.append(_("Çift tıklayınca ilgili sayfaya gider."))
        oge.setToolTip("\n".join(ipucu))
        oge.setData(_ROL_KURAL, bulgu.kural)
        oge.setData(_ROL_HEDEF, hedef)
        return oge

    # ------------------------------------------------------------------
    # bulguya git
    # ------------------------------------------------------------------
    def _secim_degisti(self, oge, _onceki=None):
        self.d_git.setEnabled(bool(oge is not None and oge.data(_ROL_HEDEF)))

    def _ogeye_git(self, oge):
        hedef = oge.data(_ROL_HEDEF) if oge is not None else None
        if hedef:
            self.git_istendi.emit(hedef)

    def _secilene_git(self):
        self._ogeye_git(self.liste.currentItem())
