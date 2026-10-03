# -*- coding: utf-8 -*-
"""
sonuc_gosterimi.py -- Calistir sekmesinin sonuc gosterimi: diskteki kosu
dizinini yukleme ve sonuc_oku() ciktisini panoya/metne yazma

arayuz/sekme_calistir.py'den YALNIZ TASINDI (v3 T2, dosya boyu): ayni
yontemler bir karisim (mixin) sinifinda; CalistirSekmesi bundan turer, yani
davranis ve yontem adlari aynidir (CalistirSekmesi.kosu_dizinini_yukle,
CalistirSekmesi.gunluk_cevrimleri ...). Ozniteliklerin (pano, kart, log,
durum sinyali ...) kurulumu sekme_calistir.CalistirSekmesi'ndedir.
"""

import os

from cekirdek import kosucu, uygunluk
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import tema
from arayuz.calistir import cikti, gunluk_ozeti, ozet

# Kaydedici adi tasimadan once neyse o (log satirlari ayni kalir).
_log = kaydedici("arayuz.sekme_calistir")


class SonucGosterimiMixin(object):
    """CalistirSekmesi'nin sonuc yukleme/gosterme yontemleri (bkz. modul belgesi)."""

    # ==================================================================
    # var olan bir kosu dizinini yukleme (fixture / onceki kosu)
    # ==================================================================
    def kosu_dizinini_yukle(self, dizin):
        """
        Diskteki bir kosu dizinini panoya yukler (kosu.log + son statepoint).
        Kosu BASLATMAZ. DONER True: sonuc gosterildi.
        """
        sp = kosucu.son_statepoint(dizin)
        if sp is None:
            self._basarisiz_goster(_("Koşu dizininde statepoint dosyası yok: %s") % dizin)
            return False
        gunluk = self._gunlugu_oku(dizin)
        self.log.setPlainText(gunluk)
        self._zaman = gunluk_ozeti.ozetle(gunluk)
        self._dizin = dizin
        self._kosu_kusagi = self._kusak
        try:
            s = kosucu.sonuc_oku(sp)
        except Exception as e:
            self._basarisiz_goster(_("Sonuç okunamadı: %s") % e)
            return False
        self._cevrimler = self.gunluk_cevrimleri(gunluk)
        self._grafik_kur(self._entropi_acik(self.spec) and s.get("keff") is not None)
        self.pano.dogrulama_ayarla(_("Diskten yüklendi"), "notr",
                                   _("Kayıtlı koşu gösteriliyor; koşu öncesi doğrulama "
                                     "bu oturumda yapılmadı."))
        self._sonuc_goster(s, sp)
        self._grafik_guncelle()
        return True

    @staticmethod
    def gunluk_cevrimleri(gunluk):
        """Gunluk metnindeki cevrim satirlari (kosucu.cevrim_satiri) -- yeni liste."""
        satirlar = (kosucu.cevrim_satiri(x.rstrip()) for x in (gunluk or "").splitlines())
        return [c for c in satirlar if c]

    @staticmethod
    def _gunlugu_oku(dizin, ad="kosu.log"):
        """Kosu dizinindeki gunluk metni; okunamazsa bos metin (loglanir)."""
        yol = os.path.join(dizin, ad)
        try:
            with open(yol, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            _log.info("koşu günlüğü okunamadı: %s", yol, exc_info=True)
            return ""

    # ==================================================================
    # sonuc
    # ==================================================================
    def _sonuc_goster(self, s, sp):
        """
        kosucu.sonuc_oku() ciktisini gosterir. Sabit kaynak modunda k-eff YOKTUR
        (s["keff"] is None): eskiden "%.5f" % None ile cokuyor, tally'ler hic
        gosterilmiyor ve kosu basarili sayilmiyordu. Metinler calistir/ozet.py'den.
        """
        sabit = s.get("keff") is None
        self._gosterilen_sabit = sabit
        self.pano.sonuc_yaz(s, self.spec, self._zaman)
        k_tanim = self._kaynak_tanimi()
        satirlar = (self._sabit_durumu_yaz(s, k_tanim) if sabit
                    else self._ozdeger_durumu_yaz(s))
        satirlar += ozet.guc_ozeti(s)
        tally = ozet.tally_metinleri(self._yerel_k_disi(s), sabit,
                                     float(k_tanim.get("kuvvet") or 1.0))
        tam = ([] if sabit else ["k-eff    = %.5f ± %.5f" % s["keff"]]) + satirlar
        tam += ["statepoint: %s" % sp, ""] + tally
        self.ozet_etiket.setText("\n".join(satirlar))
        self.sonuc_metin.setPlainText("\n".join(tam))
        self.tally_metin.setPlainText("\n".join(tally) if sabit else "")
        self.guc_harita.sonuc_ayarla(s, self.spec)
        self.mesh_harita.statepoint_ayarla(sp, self.spec)       # v3 Y1
        self.spektrum_karti.sonuc_ayarla(sp)                 # Y3
        self._yerel_k_goster(s, sp)                          # K4
        self.yuzey_karti.sonuc_ayarla(sp, self.spec)         # Y7
        self.varyans_karti.sonuc_ayarla(sp, self.spec)       # Y9
        self.kart.cikti_yaz(*cikti.uyari_ozeti(self._dizin))     # M5
        self.uygunluk.denetle(self.spec, self._dizin)
        self._guc_var = bool((s.get("guc") or {}).get("faktorler"))
        self._son_basarili = True
        self._basarisiz = False
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        if sabit:
            self.durum.emit(_("Koşu tamamlandı (sabit kaynak) — sonuçlar tally'lerde"),
                            True)
        else:
            self.durum.emit(_("Koşu tamamlandı: k-eff = %.5f ± %.5f") % s["keff"], True)

    @staticmethod
    def _yerel_k_disi(s):
        """Yerel k tally'leri metin ozetine girmez: haritada gosterilir ve mesh
        DataFrame'i (MultiIndex) kosucu.tally_metni'ni bozuyordu (K4)."""
        from cekirdek import yerel_k
        adlar = set(yerel_k.TALLY_ADLARI.values()) | {yerel_k.TOPLAM_TALLY}
        taller = {a: v for a, v in (s.get("tallyler") or {}).items() if a not in adlar}
        return dict(s, tallyler=taller)

    def _yerel_k_goster(self, s, sp):
        """K4: yerel k karti yalniz kosuda yerel k tally'si varsa gorunur."""
        from cekirdek import yerel_k
        var = any(ad in (s.get("tallyler") or {}) for ad in yerel_k.TALLY_ADLARI.values())
        self.yerel_k_karti.setVisible(var)
        if var:
            self.yerel_k.kosu_sonucu_ayarla(s, self.spec, statepoint=sp)

    def _kaynak_tanimi(self):
        return ((self.spec or {}).get("ayarlar") or {}).get("kaynak") or {}

    def _durum_yaz(self, metin, renk):
        self.durum_etiket.setText(metin)
        self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;" % tema.renk(renk))

    def _sabit_durumu_yaz(self, s, k_tanim):
        """Sabit kaynak: k-eff tanimsiz; ozet satirlari (ozet.sabit_ozeti)."""
        self.keff_etiket.setText("-")
        self._durum_yaz(_("Sabit kaynak — k-eff tanımsız\nSonuç tally'lerdir (aşağıda)."),
                        "vurgu")
        return ozet.sabit_ozeti(s, k_tanim)

    @staticmethod
    def _keff_rengi(k, sapma, sonsuz):
        """Kritiklik yorumunun rengi (kosucu.keff_yorumu ile ayni siniflama).
        Yorum METNI geri okunmaz: etkin dile cevrilmis olabilir."""
        if sonsuz or k <= 0:
            return "vurgu"
        if abs(k - 1.0) <= 2.0 * sapma:
            return "basari"
        return "hata" if k > 1.0 else "vurgu"

    def _ozdeger_durumu_yaz(self, s):
        """Ozdeger: kritiklik yorumu + ozet satirlari; kaynak yakinsamadiysa uyarir."""
        self.keff_etiket.setText("%.5f ± %.5f" % s["keff"])
        kin = s.get("kinetik") or {}
        sonsuz = uygunluk.sonsuz_ortam(self.spec or {})
        self.keff_baslik.setText("k∞" if sonsuz else "k-eff")
        durum, ayrinti = kosucu.keff_yorumu(s["keff"][0], s["keff"][1],
                                            kin.get("beta_eff"), sonsuz=sonsuz)
        renk = self._keff_rengi(s["keff"][0], s["keff"][1], sonsuz)
        self._durum_yaz("%s\n%s" % (durum, ayrinti), renk)
        satirlar, yakinsadi = ozet.ozdeger_ozeti(s)
        satirlar = ozet.referans_satirlari(self.spec, s["keff"]) + satirlar
        if yakinsadi is False:
            self.durum.emit(_("Dikkat: kaynak yakınsamamış olabilir — "
                              "pasif çevrim sayısını artırın"), False)
        return satirlar
