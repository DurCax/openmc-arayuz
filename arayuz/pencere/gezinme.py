# -*- coding: utf-8 -*-
"""
gezinme.py -- GezinmeCephesi: ana pencerenin sekme gezinmesinin HERKESE ACIK
yuzu (Dalga 2 on-commit 3).

Testler ve araclar/ekran_turu.py sekmelere
yalniz bu yontemlerle erisir. Dalga 2'de (Ajan 6) altyapi QTabWidget'tan
KenarCubugu + QStackedWidget'a gecti: imzalar ve davranis AYNI kaldi, yalniz
bu dosyanin govdesi degisti.

Anahtarlar uygunluk.SEKMELER'dir: malzemeler, parcalar, demet, kor, ayarlar,
calistir, analiz, tukenme.

Gereken oznitelikler (AnaPencere kurar): self.kenar (KenarCubugu),
self.yigin_sekme (QStackedWidget), self._sayfalar {anahtar: QScrollArea},
self._sayfa_editor {QScrollArea: sekme}, self._isaretler {anahtar: (isaret, ipucu)}.

EK SAYFALAR (v3 K2): modele bagli olmayan sayfalar (bugun yalniz "veri",
arayuz/veri/kayit.py) self._ek_sayfalar {anahtar: QScrollArea}'dadir;
sekme_anahtarlari() onlari ICERMEZ (uygunluk.SEKMELER sozlesmesi), diger
yontemler tanir. Veri yoksa dogrulamaya "veri kutuphanesi" hata bulgusu
eklenir (Calistir kapanir) ve bulgu Veri sayfasina goturur.
"""

from arayuz.pencere.kabuk import DURUM_ISARETI
from arayuz.pencere.model_islemleri import SEKME_ADLARI
from cekirdek.ceviri import _, N_

# Ek sayfa anahtari -> gorunen ad (N_; gosterirken _()).
EK_SAYFA_ADLARI = {"veri": N_("Veri")}
# Bulgu "yer" oneki -> ek sayfa (dogrula: veri_kutuphanesi_kontrol yeri).
EK_SAYFA_YERLERI = (("veri kutuphanesi", "veri"),)

# Sekme basliginin yaninda gosterilen durum isaretleri (sekme_isaretleri).
ISARETLER = ("!", "•", "✓")


class GezinmeCephesi:
    """Sekme gezinmesi; AnaPencere'ye karistirilir."""

    def sekme_anahtarlari(self):
        """Butun sekmelerin anahtarlari, pencerede gorunen sirayla (gizliler
        dahil; bugun uygunluk.SEKMELER sirasi). Ek sayfalar haric."""
        ek = self._ek()
        return tuple(k for k in self.kenar.anahtarlar() if k not in ek)

    def _ek(self):
        return getattr(self, "_ek_sayfalar", {})

    def ek_sayfa_anahtarlari(self):
        """Modele bagli olmayan sayfalar (kenar cubugu sirasiyla)."""
        ek = self._ek()
        return tuple(k for k in self.kenar.anahtarlar() if k in ek)

    def ek_sayfa_anahtari(self, yer):
        """Bulgu yerinden ek sayfa anahtari ("veri kutuphanesi" -> "veri"); yoksa None."""
        yer = (yer or "").lower()
        for onek, anahtar in EK_SAYFA_YERLERI:
            if yer.startswith(onek) and anahtar in self._ek():
                return anahtar
        return None

    def veri_bulgusu_ekle(self, bulgular):
        """Nukleer veri cozulemiyorsa "veri kutuphanesi" hata bulgusu eklenmis
        YENI liste (zaten varsa ayni icerik). Calistir kapisi hata_var ile kapanir."""
        from cekirdek import dogrula, veri_yolu
        if veri_yolu.veri_hazir_mi() or any(
                (b.yer or "").startswith("veri kutuphanesi") for b in bulgular):
            return list(bulgular)
        return list(bulgular) + [dogrula.Bulgu(
            "hata", "veri kutuphanesi", _("nükleer veri kütüphanesi bulunamadı"),
            _("Veri sayfasından cross_sections.xml içeren klasörü seçin ya da bir "
              "kütüphane indirin."))]

    def sekmeye_git(self, anahtar, sessiz=False):
        """Sekmeye gecer. Sekme bu modelde gizliyse ya da anahtar bilinmiyorsa
        gecmez ve False dondurur (sessiz degilse neden bildirilir)."""
        if anahtar in self._ek():
            self.kenar.sec(anahtar)
            self.yigin_sekme.setCurrentWidget(self._ek()[anahtar])
            return True
        if anahtar not in self._sayfalar:
            return False
        if not self.kenar.gorunur_mu(anahtar):
            if not sessiz:
                self.bildir_mesaj(
                    _("{sekme} sayfası bu model türünde kullanılmıyor.").format(
                        sekme=_(SEKME_ADLARI[anahtar])), "bilgi")
            return False
        self.kenar.sec(anahtar)
        self.yigin_sekme.setCurrentWidget(self._sayfalar[anahtar])
        return True

    def gecerli_sekme(self):
        """Etkin sekmenin anahtari (yoksa None)."""
        return self.kenar.secili()

    def sekme_gorunur_mu(self, anahtar):
        """Sekme bu modelde gorunur mu (uygunluk.gecerli_sekmeler)."""
        if anahtar in self._ek():
            return self.kenar.gorunur_mu(anahtar)
        return anahtar in self._sayfalar and self.kenar.gorunur_mu(anahtar)

    def sekme_widget(self, anahtar):
        """Sekmenin kendisi (SekmeTabani / CalistirSekmesi ...); yoksa None."""
        sayfa = self.sekme_sayfasi(anahtar)
        return self._sayfa_editor.get(sayfa) if sayfa is not None else None

    def sekme_sayfasi(self, anahtar):
        """Sekmeyi saran kaydirma alani (QScrollArea); yoksa None."""
        return self._sayfalar.get(anahtar) or self._ek().get(anahtar)

    def sekme_basligi(self, anahtar):
        """Gorunen sekme adi, durum isareti OLMADAN."""
        if anahtar in self._ek():
            return _(EK_SAYFA_ADLARI.get(anahtar, anahtar))
        return _(SEKME_ADLARI[anahtar]) if anahtar in self._sayfalar else ""

    def sekme_isareti(self, anahtar):
        """(isaret, ipucu): isaret ISARETLER'den biri ya da "" (isaretsiz)."""
        if anahtar not in self._sayfalar and anahtar not in self._ek():
            return "", ""
        durum = self.kenar.durum(anahtar)
        ipucu = self._isaretler.get(anahtar, ("", ""))[1]
        return DURUM_ISARETI.get(durum, ""), ipucu
