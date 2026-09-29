# -*- coding: utf-8 -*-
"""
gezinme.py -- GezinmeCephesi: ana pencerenin sekme gezinmesinin HERKESE ACIK
yuzu (Dalga 2 on-commit 3).

Testler, arayuz/tasarim/once_goruntu.py ve araclar/ekran_turu.py sekmelere
yalniz bu yontemlerle erisir; `pencere.sekmeler` (bugun QTabWidget) dogrudan
kullanilmaz. Boylece Ajan 6 QTabWidget'i KenarCubugu + QStackedWidget ile
degistirirken yalniz bu dosyanin govdesi degisir, imzalar ve davranis ayni
kalir.

Anahtarlar uygunluk.SEKMELER'dir: malzemeler, parcalar, demet, kor, ayarlar,
calistir, analiz, tukenme.

Gereken oznitelikler (AnaPencere kurar): self.sekmeler, self._sekme_ix
{anahtar: indeks}, self._sayfa_editor {kaydirma_alani: sekme}.
"""

from arayuz.pencere.model_islemleri import SEKME_ADLARI

# Sekme basliginda adin arkasina eklenen durum isaretleri (sekme_isaretleri).
ISARETLER = ("!", "•", "✓")
_ISARET_AYIRICI = "  "


class GezinmeCephesi:
    """Sekme gezinmesi; AnaPencere'ye karistirilir."""

    def sekme_anahtarlari(self):
        """Butun sekmelerin anahtarlari, pencerede gorunen sirayla (gizliler
        dahil; bugun uygunluk.SEKMELER sirasi)."""
        return tuple(sorted(self._sekme_ix, key=self._sekme_ix.get))

    def sekmeye_git(self, anahtar, sessiz=False):
        """Sekmeye gecer. Sekme bu modelde gizliyse ya da anahtar bilinmiyorsa
        gecmez ve False dondurur (sessiz degilse durum cubuguna neden yazilir)."""
        i = self._sekme_ix.get(anahtar)
        if i is None:
            return False
        if not self.sekmeler.isTabVisible(i):
            if not sessiz:
                self.statusBar().showMessage(
                    "%s sekmesi bu model türünde kullanılmıyor." % SEKME_ADLARI[anahtar], 6000)
            return False
        self.sekmeler.setCurrentIndex(i)
        return True

    def gecerli_sekme(self):
        """Etkin sekmenin anahtari (yoksa None)."""
        return self._sekme_anahtari()

    def sekme_gorunur_mu(self, anahtar):
        """Sekme bu modelde gorunur mu (uygunluk.gecerli_sekmeler)."""
        i = self._sekme_ix.get(anahtar)
        return i is not None and self.sekmeler.isTabVisible(i)

    def sekme_widget(self, anahtar):
        """Sekmenin kendisi (SekmeTabani / CalistirSekmesi ...); yoksa None."""
        sayfa = self.sekme_sayfasi(anahtar)
        return self._sayfa_editor.get(sayfa) if sayfa is not None else None

    def sekme_sayfasi(self, anahtar):
        """Sekmeyi saran kaydirma alani (QScrollArea); yoksa None."""
        i = self._sekme_ix.get(anahtar)
        return self.sekmeler.widget(i) if i is not None else None

    def sekme_basligi(self, anahtar):
        """Gorunen sekme adi, durum isareti OLMADAN."""
        return self._sekme_metni(anahtar)[0]

    def sekme_isareti(self, anahtar):
        """(isaret, ipucu): isaret ISARETLER'den biri ya da "" (isaretsiz)."""
        i = self._sekme_ix.get(anahtar)
        if i is None:
            return "", ""
        return self._sekme_metni(anahtar)[1], self.sekmeler.tabToolTip(i)

    def _sekme_metni(self, anahtar):
        i = self._sekme_ix.get(anahtar)
        if i is None:
            return "", ""
        metin = self.sekmeler.tabText(i)
        for isaret in ISARETLER:
            son = _ISARET_AYIRICI + isaret
            if metin.endswith(son):
                return metin[:-len(son)], isaret
        return metin, ""
