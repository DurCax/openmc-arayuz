# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/yardimcilar.py  --  sabitler, saf metin yardimcilari, kucuk etiket kuruculari

 arayuz/sekme_malzeme.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_malzeme; sekme_malzeme.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from cekirdek import malzeme_kutup as mk
from cekirdek.ceviri import _, N_, pgettext
from cekirdek import sema
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


# Spec degerleri AYNEN kalir; kullanici yalnizca okunur etiketi gorur.
# Gorunen etiketler yalnizca isaretli (N_); gosterirken _() (bilesim.py).
TUR_SECENEKLERI = (("element", N_("Doğal element")), ("nuklid", N_("İzotop (nüklid)")))
BIRIM_SECENEKLERI = (("ao", N_("Atom oranı")), ("wo", N_("Ağırlık oranı")))
YOGUNLUK_BIRIMLERI = (("g/cm3", "g/cm³"), ("atom/b-cm", "atom/b-cm"),
                      ("kg/m3", "kg/m³"))
_YOGUNLUK_ETIKETI = dict(YOGUNLUK_BIRIMLERI)

# Kutuphane listesinin gruplari, SIRAYLA.
GRUPLAR = (("yakit", N_("Yakıt")), ("yapisal", N_("Zarf ve yapısal")),
           ("sogutucu", N_("Soğutucu ve moderatör")), ("emici", N_("Emici")),
           ("gaz", N_("Gaz")))
ROL_ETIKETLERI = {"yakit": N_("yakıt"), "sogutucu": N_("soğutucu"), "moderator": N_("moderatör"),
                  "emici": N_("emici"), "yapisal": N_("yapısal"), "gaz": N_("gaz")}
_ROL_SIRASI = ("yakit", "emici", "gaz", "sogutucu", "moderator", "yapisal")

_KELVIN = 273.15


def rol_grubu(roller):
    """uygunluk rollerinden kutuphane grubu (GRUPLAR anahtari)."""
    roller = set(roller or ())
    if "yakit" in roller:
        return "yakit"
    if "emici" in roller:
        return "emici"
    if "gaz" in roller:
        return "gaz"
    if roller & {"sogutucu", "moderator"}:
        return "sogutucu"
    return "yapisal"


_GRUP_ONBELLEK = {}


def kutuphane_gruplari():
    """
    [(grup, etiket, [anahtar, ...]), ...] -- bos gruplar atlanir; etiket etkin dilde. Grup,
    kutuphanenin varsayilan malzemesinin uygunluk rollerinden turetilir;
    grup ici sira malzeme_kutup.KATALOG sirasidir (ilk: UO2).
    """
    if not _GRUP_ONBELLEK:
        from cekirdek import uygunluk
        for anahtar in mk.KATALOG:
            _GRUP_ONBELLEK[anahtar] = rol_grubu(
                uygunluk.tek_malzeme_rolleri(mk.uret(anahtar)))
    cikti = []
    for grup, etiket in GRUPLAR:
        anahtarlar = [k for k in mk.KATALOG if _GRUP_ONBELLEK.get(k) == grup]
        if anahtarlar:
            cikti.append((grup, _(etiket), anahtarlar))
    return cikti


def sab_onerileri(m):
    """
    Bilesime uyan S(a,b) tablolari [(ad, tanim), ...], EN DAR kural once.
    dogrula._sab_kontrol ile AYNI kural tablosu: dogrulamanin "eksik" diye
    uyardigi durumda burada oneri cikar. Gaz (< 0.1 g/cm3) icin oneri yok.
    """
    from cekirdek import dogrula, uygunluk
    try:
        yog = uygunluk._yogunluk_gcm3(m)
    except Exception as e:                  # eksik/bozuk yogunluk: kural yogunluksuz uygulanir
        _log.warning("sab_onerileri: yogunluk okunamadi (%s)", e)
        yog = None
    if yog is not None and yog <= dogrula._YOGUN_FAZ_ESIGI:
        return []
    elemanlar = dogrula._element_kumesi(m)
    if not elemanlar:
        return []
    eslesen = sorted((len(uygun), onerilen, tanim)
                     for uygun, zorunlu, onerilen, tanim in dogrula._SAB_KURALLARI
                     if zorunlu <= elemanlar <= uygun)
    cikti, gorulen = [], set()
    for _n, onerilen, tanim in eslesen:
        if onerilen not in gorulen:
            gorulen.add(onerilen)
            cikti.append((onerilen, tanim))
    return cikti


def okunur_ad(anahtar):
    """Kutuphane malzemesinin gorunen adi, etkin dilde (metin cekirdek KATALOG'unda)."""
    return _(mk.okunur_ad(anahtar))


def katalog_aciklamasi(anahtar):
    """Kutuphane malzemesinin kisa aciklamasi, etkin dilde (bos olabilir)."""
    return _(mk.katalog_aciklamasi(anahtar))


def uretim_ozeti(m, sorun=None):
    """Parametre formunun urettigi malzemenin ozeti (m) ya da kurulamama nedeni."""
    if sorun:
        return _("Bu değerlerle malzeme kurulamıyor: {sorun}").format(sorun=sorun)
    sab = ", ".join(m.get("sab") or []) or pgettext("sab", "yok")
    return _("Bileşim: {bilesim}   ·   S(α,β): {sab}\nAçıklama: {aciklama}").format(
        bilesim=bilesim_ozeti(m), sab=sab, aciklama=m.get("gorunen_ad"))


def sicaklik_metni(k):
    if not k:
        return "—"
    return "%.1f K (%.1f °C)" % (float(k), float(k) - _KELVIN)


def yogunluk_metni(m):
    y = m.get("yogunluk") or {}
    birim = y.get("birim") or "g/cm3"
    return "%.5g %s" % (float(y.get("deger") or 0.0), _YOGUNLUK_ETIKETI.get(birim, birim))


def bilesim_ozeti(m):
    parca = []
    for b in m.get("bilesim") or []:
        isim = b.get("isim") or "?"
        z = b.get("zenginlik")
        parca.append(_("{isim} (%{z:.2f} U-235)").format(isim=isim, z=z)
                     if z is not None else isim)
    return ", ".join(parca)


_PLAKA_ALANI = {"et_malzeme": N_("yakıt tabakası"), "zarf_malzeme": N_("zarf"),
                "sogutucu": N_("soğutucu"), "yan_levha_malzeme": N_("yan levha")}


def _plaka_alani(k):
    """Plaka malzeme alaninin okunur adi (etkin dilde); bilinmeyen alan aynen."""
    return _(_PLAKA_ALANI[k]) if k in _PLAKA_ALANI else k


# Metinler lambda GOVDESINDE cevrilir (cagri aninda, etkin dilde).
_YOL_KALIPLARI = (
    (r"cubuklar/(.+)/bolgeler/(\d+)$",
     lambda a, i: _("‘{ad}’ çubuğunun {n}. bölgesi").format(ad=a, n=int(i) + 1)),
    (r"cubuklar/(.+)/izleyici_malzeme$", lambda a: _("‘%s’ kontrol çubuğunun izleyicisi") % a),
    (r"plakalar/(.+)/(\w+)$",
     lambda a, k: _("‘{ad}’ plakasının {alan} malzemesi").format(ad=a, alan=_plaka_alani(k))),
    (r"demetler/(.+)/dolgu_disi$", lambda a: _("‘%s’ demetinin dış dolgusu") % a),
    (r"demetler/(.+)/anahtar/.+$", lambda a: _("‘%s’ demet haritası") % a),
    (r"demetler/(.+)/kilif$", lambda a: _("‘%s’ demetinin kılıfı") % a),
    (r"kor/yansitici$", lambda: _("kor yansıtıcısı")),
    (r"kor/kabuklar/(\d+)$", lambda i: _("{n}. küresel kabuk").format(n=int(i) + 1)),
    (r"kor/tambur/govde_malzeme$", lambda: _("tambur gövdesi")),
    (r"kor/tambur/emici_malzeme$", lambda: _("tambur emicisi")),
    (r"kor/anahtar/.+$", lambda: _("kor haritası")),
    (r"kor/dolgu$", lambda: _("kor dolgusu")),
    (r"kor/eksenel/(\d+)/dolgu$", lambda i: _("{n}. eksenel katman").format(n=int(i) + 1)),
    (r"kor/eksenel/(\d+)/anahtar/.+$",
     lambda i: _("{n}. eksenel katmanın haritası").format(n=int(i) + 1)),
    (r"tallyler/(.+)/filtreler/\d+/adlar/\d+$", lambda a: _("‘%s’ tally filtresi") % a),
    (r"tukenme/ek_malzemeler/\d+$", lambda: _("tükenme ek malzemeleri")),
    (r"tamburlar/(.+)/govde_malzeme$", lambda a: _("‘%s’ tamburunun gövdesi") % a),
    (r"tamburlar/(.+)/emici_malzeme$", lambda a: _("‘%s’ tamburunun emicisi") % a),
    (r"geometri/(.+)$", lambda y: _geometri_yolu(y)),
)

def _geometri_yolu(yol):
    """'kok/halkalar/0/icerik' -> 'geometri: kök › 1. halka › içerik' (cekirdek.geometri.yol_metni)."""
    from cekirdek.geometri.yol_metni import okunur
    return _("geometri: %s") % okunur(yol)


def yol_okunur(yol):
    """sema.malzeme_adini_degistir yolunu okunur metne (etkin dilde) cevirir."""
    import re
    for kalip, metin in _YOL_KALIPLARI:
        e = re.match(kalip, yol)
        if e:
            return metin(*e.groups())
    return yol


def _isim_duzelt(isim, tur):
    """Element/nuklid adini OpenMC yazimina getirir: "zr" -> "Zr", "u235" -> "U235"."""
    isim = (isim or "").strip()
    if not isim:
        return isim
    if tur == "nuklid":
        i = 0
        while i < len(isim) and isim[i].isalpha():
            i += 1
        harf = isim[:i]
        return harf[:1].upper() + harf[1:].lower() + isim[i:]
    return isim[:1].upper() + isim[1:].lower()


def _sayi_metni(v):
    """Float'i kayipsiz ama okunur yazar (0.0001785 -> '0.0001785')."""
    return repr(float(v))


def _tema_renk(ad, vars_=None):
    """Etkin tema rengi. Tema (Qt) yuklenemezse acik temanin token rengi;
    vars_ yalniz eski cagrilar icin kalir (ikisi de yoksa)."""
    try:
        from arayuz import tema
        return tema.renk(ad)
    except (ImportError, KeyError) as e:
        from arayuz.tasarim import tokenlar
        _log.debug("tema rengi %r okunamadi (%s); token rengi kullaniliyor", ad, e)
        return tokenlar.palet("acik").get(ad, vars_)


# Diyalogdaki butun form etiketleri ayni genislikte: ust "Ad" satiri,
# parametre formu ve elle formu ayri QFormLayout'lardir; hizalanmalari icin.
ETIKET_GENISLIGI = 180


def _etiket(metin):
    e = QtWidgets.QLabel(metin)
    e.setMinimumWidth(ETIKET_GENISLIGI)
    return e


def _ozet_etiketi():
    e = QtWidgets.QLabel()
    e.setWordWrap(True)
    e.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    return e


def _hata_etiketi():
    e = QtWidgets.QLabel()
    e.setWordWrap(True)
    e.setStyleSheet("color: %s;" % _tema_renk("hata"))
    e.setVisible(False)
    return e


def _benzersiz_ad(spec, taban):
    ad, i = taban, 2
    while sema.malzeme_adi_sorunu(spec, ad) is not None:
        ad = "%s_%d" % (taban, i)
        i += 1
    return ad
