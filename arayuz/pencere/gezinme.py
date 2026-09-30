# -*- coding: utf-8 -*-
"""
gezinme.py -- GezinmeCephesi: ana pencerenin sekme gezinmesinin HERKESE ACIK
yuzu (Dalga 2 on-commit 3).

Testler, arayuz/tasarim/once_goruntu.py ve araclar/ekran_turu.py sekmelere
yalniz bu yontemlerle erisir. Dalga 2'de (Ajan 6) altyapi QTabWidget'tan
KenarCubugu + QStackedWidget'a gecti: imzalar ve davranis AYNI kaldi, yalniz
bu dosyanin govdesi degisti.

Anahtarlar uygunluk.SEKMELER'dir: malzemeler, parcalar, demet, kor, ayarlar,
calistir, analiz, tukenme.

Gereken oznitelikler (AnaPencere kurar): self.kenar (KenarCubugu),
self.yigin_sekme (QStackedWidget), self._sayfalar {anahtar: QScrollArea},
self._sayfa_editor {QScrollArea: sekme}, self._isaretler {anahtar: (isaret, ipucu)}.
"""

from arayuz.pencere.kabuk import DURUM_ISARETI
from arayuz.pencere.model_islemleri import SEKME_ADLARI
from cekirdek.ceviri import _

# Sekme basliginin yaninda gosterilen durum isaretleri (sekme_isaretleri).
ISARETLER = ("!", "•", "✓")


class GezinmeCephesi:
    """Sekme gezinmesi; AnaPencere'ye karistirilir."""

    def sekme_anahtarlari(self):
        """Butun sekmelerin anahtarlari, pencerede gorunen sirayla (gizliler
        dahil; bugun uygunluk.SEKMELER sirasi)."""
        return tuple(self.kenar.anahtarlar())

    def sekmeye_git(self, anahtar, sessiz=False):
        """Sekmeye gecer. Sekme bu modelde gizliyse ya da anahtar bilinmiyorsa
        gecmez ve False dondurur (sessiz degilse neden bildirilir)."""
        if anahtar not in self._sayfalar:
            return False
        if not self.kenar.gorunur_mu(anahtar):
            if not sessiz:
                self.bildir_mesaj(
                    _("{sekme} sayfası bu model türünde kullanılmıyor.").format(
                        sekme=SEKME_ADLARI[anahtar]), "bilgi")
            return False
        self.kenar.sec(anahtar)
        self.yigin_sekme.setCurrentWidget(self._sayfalar[anahtar])
        return True

    def gecerli_sekme(self):
        """Etkin sekmenin anahtari (yoksa None)."""
        return self.kenar.secili()

    def sekme_gorunur_mu(self, anahtar):
        """Sekme bu modelde gorunur mu (uygunluk.gecerli_sekmeler)."""
        return anahtar in self._sayfalar and self.kenar.gorunur_mu(anahtar)

    def sekme_widget(self, anahtar):
        """Sekmenin kendisi (SekmeTabani / CalistirSekmesi ...); yoksa None."""
        sayfa = self.sekme_sayfasi(anahtar)
        return self._sayfa_editor.get(sayfa) if sayfa is not None else None

    def sekme_sayfasi(self, anahtar):
        """Sekmeyi saran kaydirma alani (QScrollArea); yoksa None."""
        return self._sayfalar.get(anahtar)

    def sekme_basligi(self, anahtar):
        """Gorunen sekme adi, durum isareti OLMADAN."""
        return SEKME_ADLARI[anahtar] if anahtar in self._sayfalar else ""

    def sekme_isareti(self, anahtar):
        """(isaret, ipucu): isaret ISARETLER'den biri ya da "" (isaretsiz)."""
        if anahtar not in self._sayfalar:
            return "", ""
        durum = self.kenar.durum(anahtar)
        ipucu = self._isaretler.get(anahtar, ("", ""))[1]
        return DURUM_ISARETI.get(durum, ""), ipucu
