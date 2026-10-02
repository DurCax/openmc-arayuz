# -*- coding: utf-8 -*-
"""
 arayuz/sonuc/spektrum.py  --  Calistir sayfasi: "Spektrum ve dört faktör" karti (Y3)

 Statepoint'teki y3_* tally'lerinden (cekirdek/spektrum.py) letarji basina
 aki grafigi (log-log; model geneli ve yakit), dort faktor tablosu, (n,xn) ve
 sizinti carpanlari ile spektral indeksler. Y3 tally'si yoksa kart gizlidir.
 Tanimlar ve varsayimlar kartta acikca yazilir (profesor denetimi: kaynaksiz
 ya da etiketsiz bir sayi gosterilmez).
"""

import html
import math

from PySide6 import QtCore, QtWidgets

from arayuz import tema
from arayuz.calistir.yakinsama import GrafikKarti
from arayuz.ortak import ipucu
from cekirdek import spektrum
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
_YUKSEKLIK = 240            # grafik [px]

# (anahtar, sembol, ad, tanim) -- tanimlar cekirdek/spektrum.py modul belgesiyle ayni
_FAKTORLER = (
    ("eps", "ε", N_("hızlı fisyon çarpanı"), "νF / νF_th"),
    ("p", "p", N_("rezonanstan kaçma olasılığı"), "A_th / A"),
    ("f", "f", N_("termal yararlanma"), "A_F,th / A_th"),
    ("eta", "η", N_("termal soğurma başına nötron"), "νF_th / A_F,th"),
    ("carpim", "ε·p·f·η", N_("dört faktör çarpımı"), "νF / A"),
    ("c_xn", "c_xn", N_("(n,xn) düzeltmesi"), "A / (A − X)"),
    ("p_nl", "P_NL", N_("sızmama olasılığı (P_FNL·P_TNL)"), "(A − X) / (A − X + L)"),
    ("k", "k", N_("tally'lerden k"), "νF / (A − X + L)"),
)
_INDEKSLER = (
    ("rho28", "ρ28", N_("U-238 yakalama, epitermal / termal")),
    ("delta25", "δ25", N_("U-235 fisyon, epitermal / termal")),
    ("delta28", "δ28", N_("U-238 fisyon / U-235 fisyon")),
    ("C*", "C*", N_("U-238 yakalama / U-235 fisyon")),
)


def deger_metni(d):
    """Deger -> 'ort ± sapma' (5 ondalik); None -> 'tanımsız'."""
    if d is None or not math.isfinite(d.ort):
        return _("tanımsız")
    return "%.5f ± %.5f" % (d.ort, d.sapma)


def _k_sembolu(sonsuz):
    if sonsuz is None:
        return "k"                      # sizinti bilinmiyor: k∞/k-eff denmez
    return "k∞" if sonsuz else "k-eff"


def tablo_satirlari(sonuc, sonsuz):
    """[(sembol, ad, tanim, deger metni)] -- faktorler (ozdegerde) + indeksler.
    sonsuz: True sizintisiz (k∞), False sizintili (k-eff), None bilinmiyor (k)."""
    satirlar = []
    f = sonuc.get("faktorler")
    if f:
        for anahtar, sembol, ad, tanim in _FAKTORLER:
            if anahtar == "k":
                sembol = _k_sembolu(sonsuz)
            satirlar.append((sembol, _(ad), tanim, deger_metni(f.get(anahtar))))
        if sonuc.get("keff") is not None:
            satirlar.append(("k (OpenMC)", _("birleşik k tahmincisi"), "",
                             deger_metni(sonuc["keff"])))
    indeksler = sonuc.get("indeksler")
    if indeksler is not None:
        for anahtar, sembol, ad in _INDEKSLER:
            satirlar.append((sembol, _(ad), "", deger_metni(indeksler.get(anahtar))))
    return satirlar


def varsayim_notlari(sonuc, sonsuz):
    """Kartta gosterilen varsayim ve kaynak notlari (liste)."""
    notlar = [
        _("Termal kesim %g eV: OpenMC tally-arithmetic örneği, CASMO-2 sınırı, CSEWG/ENDF-202 "
          "hesap kesimi (deneydeki etkin kadmiyum kesimi kalınlığa bağlı, ~0.4–0.5 eV).")
        % sonuc.get("termal_kesim", spektrum.TERMAL_KESIM_EV),
        _("ε, p, f, η sızıntısız (k∞) tanımlardır: νF nu-fission, A absorption, X = (n,xn) net "
          "üretim; F (yakıt) = fisil nüklid içeren malzemeler."),
        _("Belirsizlik birinci derece, tally'ler arası korelasyon yok sayıldı (ihtiyatlı; "
          "çarpımın sapması νF/A oranından)."),
        _("X yalnız MT 11, 16, 17, 24, 25, 30, 37, 41, 42 kanallarını sayar; Be ya da D₂O "
          "içeren modellerde (n,2n) önemlidir, c_xn'e bakın."),
    ]
    notlar += _durum_notlari(sonuc, sonsuz)
    return notlar


def _durum_notlari(sonuc, sonsuz):
    """Sonuca ozgu notlar: sizinti, eksik tally, homojen yakit, hizli sistem."""
    notlar = []
    if sonsuz is None:
        notlar.append(_("Sızıntı bilinmiyor (global sızıntı tally'si yok): P_NL ve k "
                        "hesaplanmadı; sonuç k∞ olarak etiketlenmedi."))
    elif not sonsuz:
        notlar.append(_("Sızıntı var: P_NL global sızıntı tally'sinden tek çarpan; P_FNL ve "
                        "P_TNL ayrı verilmez (enerjiye bağlı sızıntı tally'si gerekir)."))
    if sonuc.get("indeksler") is not None:
        notlar.append(_("Spektral indeksler (CSEWG tanımları) tüm yakıt malzemelerinin "
                        "ortalamasıdır; deneyler merkez çubukta ölçer."))
    if sonuc.get("eksik"):
        notlar.append(_("Y3 tally'leri eksik (%s): dört faktör hesaplanmadı.")
                      % ", ".join(sonuc["eksik"]))
    f = sonuc.get("faktorler")
    if f is None and not sonuc.get("eksik"):
        notlar.append(_("Sabit kaynak hesabı: dört faktör ve k tanımsız; yalnız spektrum."))
    elif f is not None and f.get("eta") is None:
        notlar.append(_("Termal fisyon yok (hızlı sistem): ε, p, f, η termal reaktör "
                        "tanımlarıdır ve burada tanımsızdır."))
    elif f is not None and f.get("f") is not None and f["f"].ort == 1.0:
        notlar.append(_("f = 1: termal soğurmanın tamamı yakıt malzemesinde (homojen karışım); "
                        "η yakıt + moderatör karışımına aittir, ders kitabı anlamını yitirir."))
    return notlar


def _html_tablo(satirlar):
    renk = tema.renk("metin_soluk")
    govde = "".join(
        "<tr><td><b>%s</b></td><td>%s</td><td style='color:%s'>%s</td>"
        "<td align='right'><tt>%s</tt></td></tr>"
        % tuple([html.escape(s), html.escape(a), renk, html.escape(t), html.escape(d)])
        for s, a, t, d in satirlar)
    return "<table cellspacing='4'>%s</table>" % govde


class SpektrumKarti(GrafikKarti):
    """Letarji basina aki (log-log) + dort faktor ve indeks tablosu."""

    def __init__(self, parent=None):
        super().__init__(_("Spektrum ve dört faktör"),
                         _("Letarji başına akı, ε·p·f·η ve spektral indeksler"),
                         yukseklik=_YUKSEKLIK, parent=parent)
        self.tablo = QtWidgets.QLabel()
        self.tablo.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ekle(self.tablo)
        self.notlar = ipucu("")
        self.ekle(self.notlar)
        self.sonuc = None
        self.setVisible(False)

    def dosya_sor(self, varsayilan):
        return super().dosya_sor("spektrum.png")

    def sonuc_ayarla(self, statepoint):
        """Statepoint'ten okur ve gosterir; None ya da Y3 tally'si yoksa gizlenir."""
        if statepoint is None:
            self.goster(None)
            return
        try:
            sonuc = spektrum.oku(statepoint)
            if sonuc is None:             # kosuda Y3 tally'si yok (ayar kapali)
                self.goster(None)
                return
            self.goster(sonuc, self._sonsuz(sonuc))
        except Exception as e:
            # Kart hatasi Calistir sayfasinin geri kalanini dusurmez (k-eff, guc ...).
            _log.exception("spektrum/dört faktör sonucu gösterilemedi: %s", statepoint)
            self._hata_goster(e)

    def _hata_goster(self, hata):
        self.goster(None)
        self.setVisible(True)
        self.tablo.setText(_("Spektrum sonucu okunamadı: %s") % html.escape(str(hata)))

    @staticmethod
    def _sonsuz(sonuc):
        """Olculen global sizinti tam sifirsa sizintisiz (k∞): yansitici/periyodik
        sinirda hicbir parcacik kacmaz; tek bir kacis bile k-eff demektir.
        Sizinti tally'si yoksa None (bilinmiyor)."""
        sizinti = sonuc.get("sizinti")
        return None if sizinti is None else sizinti.ort == 0.0

    def goster(self, sonuc, sonsuz=True):
        self.sonuc = sonuc
        self.setVisible(sonuc is not None)
        if sonuc is None:
            self.tablo.clear()
            self.notlar.clear()
            self.eksen.clear()
            self.tuval.draw_idle()
            return
        self.tablo.setText(_html_tablo(tablo_satirlari(sonuc, sonsuz)))
        self.notlar.setText("\n".join("• " + n for n in varsayim_notlari(sonuc, sonsuz)))
        self.ciz(sonuc.get("spektrum") or {})

    def ciz(self, spk):
        if "kenarlar" not in spk:
            self.bos_yaz(_("Spektrum tally'si yok"))
            return
        self.eksen.set_axis_on()
        self.eksen.clear()
        palet = tema.grafik_paleti()
        for sira, (anahtar, etiket) in enumerate((("model", _("model geneli")),
                                               ("yakit", _("yakıt")))):
            if anahtar not in spk:
                continue
            e, y, _s = spektrum.letarji_basina(spk["kenarlar"], *spk[anahtar])
            self.eksen.stairs(y, e, color=palet[sira], lw=1.2, label=etiket)
        self.eksen.set_xscale("log")
        self.eksen.set_yscale("log")
        self.eksen.axvline(spektrum.TERMAL_KESIM_EV, ls="--", lw=1.0,
                           color=tema.renk("metin_soluk"))
        self.eksen.set_xlabel(_("enerji [eV]"), fontsize=8)
        self.eksen.set_ylabel(_("φ·V / Δu [cm / kaynak nötronu]"), fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.eksen.grid(True, which="major", alpha=0.3, lw=0.6)
        self.eksen.legend(fontsize=7, loc="best")
        self.tuval.draw_idle()
