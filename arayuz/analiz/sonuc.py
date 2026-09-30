# -*- coding: utf-8 -*-
"""
sonuc.py -- Analiz sonucunun GOSTERIMI: sure metni, k(p) grafigi, tablo satiri
ve katsayi / kritik arama ozet metni.

Hepsi saf islevdir (Qt widget'i almaz; grafik islevleri matplotlib eksenini
alir). AnalizSekmesi (sekme.py) bunlari cagirir; boylece sekme dosyasi 800
satir sinirinin altinda kalir ve metinler tek yerde cevrilir.
"""

from cekirdek import tarama
from cekirdek.ceviri import _
from arayuz.analiz.adlar import birim, katsayi_adi, katsayi_birimi, parametre_adi, renk

YAZI_EKSEN = 8          # eksen etiketi [pt] (matplotlib; tema tokenlari piksel)
YAZI_ISARET = 7         # isaret ve lejant [pt]
DAKIKA_ESIGI = 90       # bu kadar saniyeden kisa sure "sn" ile yazilir
SAAT_ESIGI = 5400       # bundan uzun sure "saat" ile yazilir
HATA_METNI_EN_COK = 60  # tabloda basarisiz noktanin hata metni kirpilir


def sure_metni(saniye):
    """Okunur sure: '45 sn', '2.5 dk', '1.8 saat'."""
    if saniye < DAKIKA_ESIGI:
        return _("%.0f sn") % saniye
    if saniye < SAAT_ESIGI:
        return _("%.1f dk") % (saniye / 60.0)
    return _("%.1f saat") % (saniye / 3600.0)


def eksen_etiketi(tur):
    """X ekseni etiketi: 'Yakit sicakligi (Doppler) [K]' ya da 'parametre'."""
    if not tur:
        return _("parametre")
    return "%s [%s]" % (parametre_adi(tur), birim(tur))


def grafik_sifirla(eksen):
    eksen.clear()
    eksen.set_xlabel(_("parametre"), fontsize=YAZI_EKSEN)
    eksen.set_ylabel("k-eff", fontsize=YAZI_EKSEN)
    eksen.tick_params(labelsize=YAZI_ISARET)
    eksen.grid(alpha=0.3)


def grafik_ciz(eksen, sonuclar, tur, arama=False, hedef_k=None, kats=None):
    """
    k(p) noktalari (hata cubuklu). Kritik aramada hedef k cizgisi, taramada
    (kats verilmisse) dogrusal uyum rho = kesisim + egim*p, k olceginde.
    """
    eksen.clear()
    eksen.grid(alpha=0.3)
    gecerli = [s for s in sonuclar if s.get("keff")]
    if gecerli:
        x = [s["deger"] for s in gecerli]
        eksen.errorbar(x, [s["keff"] for s in gecerli], yerr=[s["sapma"] for s in gecerli],
                       fmt="o-", ms=4, lw=1.2, capsize=3, color=renk("vurgu"))
        if arama and hedef_k is not None:
            eksen.axhline(hedef_k, color=renk("hata"), ls="--", lw=1.0, label=_("hedef k"))
            eksen.legend(fontsize=YAZI_ISARET)
        elif kats:
            _uyum_ciz(eksen, x, kats)
    eksen.set_xlabel(eksen_etiketi(tur), fontsize=YAZI_EKSEN)
    eksen.set_ylabel("k-eff", fontsize=YAZI_EKSEN)
    eksen.tick_params(labelsize=YAZI_ISARET)


def _uyum_ciz(eksen, x, kats):
    """rho dogrusunu k olceginde gosterir: rho = 1 - 1/k -> k = 1/(1-rho)."""
    import numpy as np
    px = np.linspace(min(x), max(x), 50)
    rho = (kats["kesisim"] + kats["egim"] * px) / 1.0e5
    eksen.plot(px, 1.0 / (1.0 - rho), lw=1.0, ls="--", color=renk("uyari"),
               label=_("doğrusal uyum"))
    eksen.legend(fontsize=YAZI_ISARET)


def tablo_satiri(s):
    """Bir tarama/arama noktasinin tablo hucreleri (4 metin)."""
    if s.get("keff"):
        r, _sr = tarama.reaktivite(s["keff"], s["sapma"])
        return ["%.6g" % s["deger"], "%.5f" % s["keff"], "%.5f" % s["sapma"], "%+.1f" % r]
    return ["%.6g" % s["deger"], _("başarısız"), "—", (s.get("hata") or "")[:HATA_METNI_EN_COK]]


def tarama_metni(tur, kats, notlar):
    """Tarama sonucu (zengin metin): katsayi +/- sapma, R^2, yorum, notlar."""
    if kats:
        metin = (_("<b>%s = %+.3f &plusmn; %.3f %s</b><br>"
                   "doğrusal uyum R&sup2; = %.4f, %d nokta<br><br>%s")
                 % (katsayi_adi(tur),
                    kats["egim"], kats["egim_sapma"], katsayi_birimi(tur),
                    kats["r2"], kats["nokta"], tarama.yorumla(tur, kats)))
    else:
        metin = _("Katsayı hesaplanamadı (yeterli geçerli nokta yok).")
    if notlar:
        metin += (_("<br><br><i>Notlar:</i><br>")
                  + "<br>".join("&bull; " + n for n in notlar))
    return metin


def arama_metni(tur, s):
    """Kritik arama sonucu (zengin metin)."""
    if not s.basarili:
        return _("<b>Çözüm bulunamadı.</b><br><br>%s") % s.mesaj
    bel = "" if s.cozum_belirsizlik is None else " &plusmn; %.4g" % s.cozum_belirsizlik
    return (_("<b>Çözüm: %s = %.6g%s %s</b><br>"
              "k = %.5f &plusmn; %.5f &nbsp;&nbsp; (%d koşu)<br><br>%s")
            % (parametre_adi(tur), s.cozum, bel, birim(tur),
               s.cozum_keff, s.cozum_sapma, len(s.adimlar), s.mesaj))


def tahmin_metni(tek_saniye, adet, arama):
    """Baslamadan once: '~45 sn   (5 kosu x ~9 sn)'."""
    ek = _(" (arama genellikle 4–8 koşu sürer)") if arama else ""
    return (_("~%s   (%d koşu × ~%s)%s")
            % (sure_metni(tek_saniye * adet), adet, sure_metni(tek_saniye), ek))
