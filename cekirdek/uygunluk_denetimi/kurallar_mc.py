# -*- coding: utf-8 -*-
"""
uygunluk_denetimi/kurallar_mc.py -- Profil A: Monte Carlo iyi uygulamasi.

K1-K3 hicbir standardin maddesi DEGILDIR (STANDARTLAR.md §6 madde 16); bu
yuzden hepsi "iyi_uygulama" etiketlidir.

  K1  kaynak yakinsamasi   Shannon entropisi pasif donem sonunda duzlesmis mi
                           (yontem: kosucu.entropi_yakinsama, proje yontemi)
  K2  istatistik           sigma <= hedef (kullanici), parcacik/cevrim alt
                           siniri (Brown 2009), aktif cevrim alt siniri
                           (kullanici), cevrimler arasi ilinti notu
  K3  kayip parcacik = 0   kosu.log + particle_*.h5; diger OpenMC uyarilari
                           bilgi olarak listelenir (M5)
"""

import math

from cekirdek.ceviri import _, N_
from cekirdek.uygunluk_denetimi.kurallar import IYI_UYGULAMA, Kural
from cekirdek.uygunluk_denetimi.profiller import BROWN_2009

_ORNEK = 3


def _ozdeger_degil(kural, baglam):
    """Kosu yok / okunamadi / sabit kaynak -> uygulanamadi bulgusu; aksi None."""
    if baglam.kosu_hatasi:
        return [kural.ihlal("uyari", _("Statepoint okunamadı: %s") % baglam.kosu_hatasi,
                            _("Koşuyu yeniden çalıştırın."))]
    if baglam.kosu is None:
        return [kural.uygulanamadi(_("Koşu dizininde statepoint yok."))]
    if not baglam.kosu.ozdeger:
        return [kural.uygulanamadi(_("Sabit kaynak koşusu: k-eff ve kaynak yakınsaması "
                                     "tanımsız."))]
    return None


# ----------------------------------------------------------------------------
# K1
# ----------------------------------------------------------------------------

def k1_entropi(kural, baglam):
    erken = _ozdeger_degil(kural, baglam)
    if erken:
        return erken
    kosu = baglam.kosu
    if not kosu.entropi:
        return [kural.ihlal("uyari", _("Shannon entropisi kapalı — kaynak yakınsaması "
                                       "gösterilemiyor."),
                            _("Hesap ayarlarında entropi ağını açın."))]
    from cekirdek import kosucu
    # entropi NESIL basinadir: pasif donem pasif x nesil_basina nesildir
    yakinsadi, mesaj = kosucu.entropi_yakinsama(list(kosu.entropi),
                                                kosu.pasif * max(kosu.nesil_basina, 1))
    if yakinsadi is None:
        return [kural.uygulanamadi(mesaj)]
    if not yakinsadi:
        return [kural.ihlal("uyari", mesaj,
                            _("Pasif çevrim sayısını entropi platosu başlayana dek "
                              "artırın."))]
    return [kural.gecti(mesaj)]


# ----------------------------------------------------------------------------
# K2
# ----------------------------------------------------------------------------

def _k2_sigma(kural, baglam, kosu):
    hedef = baglam.esik("sigma_hedef")
    kimlik, kaynak = "K2-sigma", baglam.esik_kaynagi("sigma_hedef")
    if hedef is None:
        return kural.uygulanamadi(
            _("σ hedefi tanımlı değil; k = %.5f, σ = %.5f (1σ) karşılaştırılmadı.")
            % (kosu.keff, kosu.sigma),
            _("Profil A'da sigma_hedef eşiğini girin."), kimlik=kimlik, kaynak=kaynak)
    if kosu.sigma > hedef:
        return kural.ihlal("uyari", _("σ_k = %.5f hedefin (%.5f) üstünde.")
                           % (kosu.sigma, hedef),
                           _("Aktif çevrim ya da çevrim başı parçacık sayısını "
                             "artırın."), kimlik=kimlik, kaynak=kaynak)
    return kural.gecti(_("σ_k = %.5f ≤ hedef %.5f.") % (kosu.sigma, hedef),
                       kimlik=kimlik, kaynak=kaynak)


def _k2_parcacik(kural, baglam, kosu):
    asgari, uretim = baglam.esik("parcacik_asgari"), baglam.esik("parcacik_uretim")
    kimlik = "K2-parcacik"
    if asgari is not None and kosu.parcacik < asgari:
        return kural.ihlal(
            "uyari", _("Çevrim başına %d parçacık: k-eff ve yerel tally'lerde yanlılık "
                       "beklenir (alt sınır %d).") % (kosu.parcacik, asgari),
            _("Çevrim başı parçacık sayısını artırın."), kimlik=kimlik,
            kaynak=baglam.esik_kaynagi("parcacik_asgari"))
    if uretim is not None and kosu.parcacik < uretim:
        return kural.not_(
            _("Çevrim başına %d parçacık: deneme koşusu için yeterli; uzun üretim "
              "koşusunda en az %d önerilir.") % (kosu.parcacik, uretim),
            kimlik=kimlik, kaynak=baglam.esik_kaynagi("parcacik_uretim"))
    return kural.gecti(_("Çevrim başına %d parçacık.") % kosu.parcacik, kimlik=kimlik,
                       kaynak=baglam.esik_kaynagi("parcacik_uretim"))


def _k2_aktif(kural, baglam, kosu):
    asgari = baglam.esik("aktif_asgari")
    kimlik, kaynak = "K2-aktif", baglam.esik_kaynagi("aktif_asgari")
    if asgari is None:
        return kural.uygulanamadi(
            _("Aktif çevrim alt sınırı tanımlı değil (%d aktif çevrim).") % kosu.aktif,
            kimlik=kimlik, kaynak=kaynak)
    if kosu.aktif < asgari:
        return kural.ihlal("uyari", _("%d aktif çevrim, alt sınır %d.")
                           % (kosu.aktif, asgari),
                           _("Çevrim sayısını artırın."), kimlik=kimlik, kaynak=kaynak)
    return kural.gecti(_("%d aktif çevrim ≥ %d.") % (kosu.aktif, asgari),
                       kimlik=kimlik, kaynak=kaynak)


def gecikme1_ilinti(dizi):
    """Gecikme-1 oz ilinti katsayisi; hesaplanamazsa None."""
    n = len(dizi)
    if n < 3:
        return None
    ort = sum(dizi) / n
    payda = sum((x - ort) ** 2 for x in dizi)
    if payda <= 0:
        return None
    return sum((dizi[i] - ort) * (dizi[i + 1] - ort) for i in range(n - 1)) / payda


def aktif_cevrim_k(kosu):
    """Aktif CEVRIMLERIN k degerleri. k_nesil nesil basinadir (generations_per_
    batch > 1 ise cevrim x g); pasif nesiller atilir, her cevrimin nesilleri
    ortalanir (Brown 2009 §IV: ilinti cevrimler arasidir)."""
    g = max(int(kosu.nesil_basina or 1), 1)
    nesil = list(kosu.k_nesil[kosu.pasif * g:])
    return [sum(nesil[i:i + g]) / g for i in range(0, len(nesil) - g + 1, g)]


def _k2_ilinti(kural, baglam, kosu):
    kimlik, kaynak = "K2-ilinti", baglam.esik_kaynagi("korelasyon_z")
    aktif = aktif_cevrim_k(kosu)
    r1 = gecikme1_ilinti(aktif)
    if r1 is None:
        return kural.uygulanamadi(_("Çevrim k değerleri ilinti için yetersiz."),
                                  kimlik=kimlik, kaynak=kaynak)
    sinir = baglam.esik("korelasyon_z", 2.0) / math.sqrt(len(aktif))
    if r1 > sinir:
        return kural.not_(
            _("Çevrimler arası ilinti belirgin (gecikme-1 r = %.2f > %.2f): bildirilen "
              "σ bu ilintiyi yok sayar ve gerçek belirsizliği küçümser (%s §IV.A). "
              "Kaynak, yerel tally'lerde (fisyon hızları) 1.7–4.7 kat küçümseme ölçer "
              "(§IV.B Tablo 2); k-eff için büyüklük vermez.")
            % (r1, sinir, BROWN_2009),
            _("Bağımsız tohumlarla birkaç koşu yapıp sonuçların saçılımını "
              "karşılaştırın."), kimlik=kimlik, kaynak=kaynak)
    return kural.gecti(_("Gecikme-1 ilinti r = %.2f ≤ %.2f.") % (r1, sinir),
                       kimlik=kimlik, kaynak=kaynak)


def k2_istatistik(kural, baglam):
    erken = _ozdeger_degil(kural, baglam)
    if erken:
        return erken
    kosu = baglam.kosu
    return [_k2_sigma(kural, baglam, kosu), _k2_parcacik(kural, baglam, kosu),
            _k2_aktif(kural, baglam, kosu), _k2_ilinti(kural, baglam, kosu)]


# ----------------------------------------------------------------------------
# K3
# ----------------------------------------------------------------------------

def _k3_diger(kural, cikti):
    bulgular = []
    for m in cikti.hatalar[:_ORNEK]:
        bulgular.append(kural.ihlal("hata", _("OpenMC hata iletisi: %s") % m,
                                    kimlik="K3-hata"))
    if cikti.uyarilar:
        ornek = "; ".join(cikti.uyarilar[:_ORNEK])
        bulgular.append(kural.not_(
            _("OpenMC %d uyarı yazdı (kayıp parçacık dışı): %s")
            % (len(cikti.uyarilar), ornek),
            _("Uyarıların sonucu etkileyip etkilemediğini koşu logunda inceleyin."),
            kimlik="K3-uyari"))
    return bulgular


def k3_kayip(kural, baglam):
    cikti = baglam.cikti
    if cikti is None or (not cikti.log_var and not cikti.yeniden_baslatma):
        return [kural.uygulanamadi(
            _("Koşu logu (kosu.log) yok: kayıp parçacık sayısı denetlenemedi."),
            _("Koşuyu bu uygulamayla yeniden çalıştırın; log koşu dizinine yazılır."))]
    azami = baglam.esik("kayip_azami", 0)
    bulgular = []
    if cikti.kayip_parcacik > azami:
        ornek = "; ".join(cikti.kayip_iletileri[:_ORNEK])
        bulgular.append(kural.ihlal(
            "hata", _("%d kayıp parçacık (izin verilen %d). %s")
            % (cikti.kayip_parcacik, azami, ornek),
            _("Geometride boşluk ya da çakışan hücre var: kesit çizimlerini ve sınır "
              "koşullarını denetleyin.")))
    elif not cikti.log_var:
        bulgular.append(kural.uygulanamadi(_("Koşu logu yok; kayıp parçacık "
                                             "yeniden başlatma dosyası da yok.")))
    else:
        bulgular.append(kural.gecti(_("Kayıp parçacık yok.")))
    return bulgular + _k3_diger(kural, cikti)


KURALLAR = (
    Kural("K1", "A", N_("Kaynak yakınsaması (Shannon entropisi platosu)"),
          N_("iyi uygulama; ") + BROWN_2009 + N_(" §II; NUREG/CR-6698 §2.4 dipnotu "
                                                  "(yakınsama kullanıcı yargısıdır)"),
          IYI_UYGULAMA, k1_entropi),
    Kural("K2", "A", N_("İstatistik yeterliliği"),
          N_("iyi uygulama; eşik standarttan gelmez (profil değeri)"),
          IYI_UYGULAMA, k2_istatistik),
    Kural("K3", "A", N_("Kayıp parçacık = 0"),
          N_("iyi uygulama (OpenMC)"), IYI_UYGULAMA, k3_kayip),
)
