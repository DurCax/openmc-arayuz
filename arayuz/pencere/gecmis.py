# -*- coding: utf-8 -*-
"""
 arayuz/pencere/gecmis.py  --  geri al / yinele

 arayuz/ana_pencere.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import ana_pencere; ana_pencere.X` aynen calisir.

 SPEC ISLEMI (Dalga G-3): spec_islemi_uygula(yeni_spec, mesaj) butun spec'i
 degistiren TEK ADIMLIK islemdir -- gelismis geometriye gecis, yeni duzenek
 sablonu, agac islemleri (ekle / sil / tasi / adlandir / parcaya cikar /
 sarmala). Once bekleyen duzenleme kendi adimi olarak yigilir, sonra islem
 ikinci adim olarak: Geri Al islemi (gecisin kendisi dahil) tek adimda
 geri alir (§15 karar 1), Yinele yeniden uygular.
"""

import copy

from cekirdek.ceviri import _

from cekirdek import onbellek


_GECMIS_SINIR = 50


class GecmisMixin(object):
    """Geri al / yinele: spec anlik goruntuleri yigini (AnaPencere'ye karisir)."""

    # ==================================================================
    # geri al / yinele
    # ==================================================================
    def _gecmise_it(self, ilk=False):
        if self._gecmis_yaziyor:
            return
        anlik = copy.deepcopy(self.spec)
        if self._gecmis and self._gecmis_ix >= 0:
            if onbellek.ozet(self._gecmis[self._gecmis_ix]) == onbellek.ozet(anlik):
                return          # degisiklik yok
        del self._gecmis[self._gecmis_ix + 1:]
        self._gecmis.append(anlik)
        if len(self._gecmis) > _GECMIS_SINIR:
            self._gecmis.pop(0)
        self._gecmis_ix = len(self._gecmis) - 1
        self._baslik_guncelle()

    def _gecmisten_yukle(self, ix):
        self._gecmis_yaziyor = True
        try:
            self.spec = copy.deepcopy(self._gecmis[ix])
            self._gecmis_ix = ix
            self._spec_uygula()
            self._kirli = True
        finally:
            self._gecmis_yaziyor = False
        self._baslik_guncelle()

    def spec_islemi_uygula(self, yeni_spec, mesaj=None):
        """Butun spec'i degistiren islem: tek geri al adimi."""
        self._gecmis_sayac.stop()
        self._gecmise_it()
        self.spec = copy.deepcopy(yeni_spec)
        self._kirli = True
        try:
            self._spec_uygula()
        finally:
            self._gecmise_it()
        if mesaj:
            self.bildir_mesaj(mesaj, "basari", 6000)
        return True

    def geri_al(self):
        self._gecmis_sayac.stop()
        self._gecmise_it()
        if self._gecmis_ix > 0:
            self._gecmisten_yukle(self._gecmis_ix - 1)
            self.bildir_mesaj(_("Geri alındı ({i}/{n})").format(
                i=self._gecmis_ix + 1, n=len(self._gecmis)), "bilgi", 3000)

    def yinele(self):
        if self._gecmis_ix < len(self._gecmis) - 1:
            self._gecmisten_yukle(self._gecmis_ix + 1)
            self.bildir_mesaj(_("Yinelendi ({i}/{n})").format(
                i=self._gecmis_ix + 1, n=len(self._gecmis)), "bilgi", 3000)
