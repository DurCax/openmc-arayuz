# -*- coding: utf-8 -*-
"""
rapor_sablon -- rapor icerigini (cekirdek.rapor.icerik_topla) HTML'e cevirir.

    html(icerik, gomulu=True) -> tam HTML metni

gomulu=True : gorseller data:image/png;base64 olarak gomulur (tek dosya HTML).
gomulu=False: <img src="<ad>"> -- PDF yolunda rapor_pdf bu adlari
              QTextDocument kaynagi olarak ekler.

Sablon stdlib string.Template'tir (rapor.html, stil.css); bagimlilik yok.
Butun metin html.escape'ten gecer; gorunen metinler _() ile sarilidir.
Renkler tasarim tokenlarindan (arayuz/tasarim/tokenlar.py, Qt'siz) gelir.
"""

import base64
import html as _html
import os
from string import Template

from cekirdek.ceviri import _, N_, etkin_dil, pgettext
from cekirdek.rapor_sablon import uygunluk_eki
from cekirdek.rapor_sablon.bicim import bm, gosterim_notu

SABLON_DIZINI = os.path.dirname(os.path.abspath(__file__))
_SEVIYE = {"hata": ("hata", N_("HATA")), "uyari": ("uyari", N_("UYARI")),
           "bilgi": ("bilgi", N_("BİLGİ"))}
GORSEL_GENISLIK = 640        # px (A4 metin genisligi, ~96 dpi)


def _e(metin):
    return _html.escape("" if metin is None else str(metin))


def _sablon(ad):
    with open(os.path.join(SABLON_DIZINI, ad), encoding="utf-8") as f:
        return Template(f.read())


def _stil():
    from arayuz.tasarim import tokenlar
    return _sablon("stil.css").substitute(tokenlar.palet("acik"))


def _tablo(basliklar, satirlar, sinif=None):
    bas = "".join("<th>%s</th>" % _e(b) for b in basliklar) if basliklar else ""
    govde = []
    for satir in satirlar:
        govde.append("<tr>%s</tr>" % "".join(
            '<td class="%s">%s</td>' % (sinif[i], _e(h)) if sinif and sinif[i]
            else "<td>%s</td>" % _e(h) for i, h in enumerate(satir)))
    return ('<table border="1" cellspacing="0" cellpadding="3" width="100%%">'
            "%s%s</table>" % ("<tr>%s</tr>" % bas if bas else "", "".join(govde)))


def _anahtar_deger(satirlar):
    return _tablo(None, satirlar, sinif=("etiket", None))


def _gorsel(icerik, ad, gomulu, genislik=GORSEL_GENISLIK, alt=""):
    veri = icerik["gorseller"].get(ad)
    if not veri:
        return ""
    kaynak = ("data:image/png;base64," + base64.b64encode(veri).decode("ascii")
              if gomulu else ad)
    return '<p><img src="%s" width="%d" alt="%s"></p>' % (kaynak, genislik, _e(alt))


# ============================================================================
# BOLUMLER
# ============================================================================

def _kapak(icerik):
    k = icerik["kapak"]
    satirlar = [(_("Tarih"), k["tarih"]), (_("Kullanıcı"), k["kullanici"]),
                (_("Koşu dizini"), icerik.get("kosu_dizini") or _("yok (yalnız model)"))]
    parca = ["<h1>%s</h1>" % _e(k["baslik"])]
    if k["aciklama"]:
        parca.append("<p>%s</p>" % _e(k["aciklama"]))
    parca.append(_anahtar_deger(satirlar))
    parca.append('<p class="soluk">%s</p>' % _e(gosterim_notu()))
    if icerik["uyarilar"]:
        parca.append('<p class="kutu"><b>%s</b><br>%s</p>' % (
            _e(_("Uyarılar")), "<br>".join(_e(u) for u in icerik["uyarilar"])))
    return "".join(parca)


def _malzeme_tablosu(malzemeler):
    """Malzeme tablosu; ilk sutun geometri kesitindeki rengin ornegi."""
    bas = "".join("<th>%s</th>" % _e(b) for b in (
        "", _("Ad"), _("Kimlik"), _("Yoğunluk"), _("Sıcaklık"), _("Bileşim"), "S(α,β)"))
    satirlar = []
    for m in malzemeler:
        renk = ' bgcolor="%s"' % _e(m["renk"]) if m.get("renk") else ""
        satirlar.append("<tr><td%s>&nbsp;&nbsp;&nbsp;</td>%s</tr>" % (renk, "".join(
            "<td>%s</td>" % _e(m[k]) for k in ("ad", "kimlik", "yogunluk", "sicaklik",
                                                "bilesim", "sab"))))
    return ('<table border="1" cellspacing="0" cellpadding="3" width="100%%">'
            "<tr>%s</tr>%s</table>" % (bas, "".join(satirlar)))


def _model(icerik, gomulu):
    parca = ["<h2>%s</h2>" % _e(_("Tekrarlanabilirlik")), _anahtar_deger(icerik["tekrar"]),
             "<h2>%s</h2>" % _e(_("Malzemeler")), _malzeme_tablosu(icerik["malzemeler"]),
             "<h2>%s</h2>" % _e(_("Geometri"))]
    xy = _gorsel(icerik, "geo_xy", gomulu, 420, _("xy kesiti"))
    xz = _gorsel(icerik, "geo_xz", gomulu, 360, _("xz kesiti"))
    if xy or xz:
        parca += [xy, xz, '<p class="soluk">%s</p>' % _e(
            _("Kesitler malzemeye göre renklidir; xz kesiti y = model merkezindedir."))]
    else:
        parca.append('<p class="soluk">%s</p>' % _e(_("Geometri kesiti çizilemedi.")))
    parca += ["<h2>%s</h2>" % _e(_("Hesap ayarları")), _anahtar_deger(icerik["ayarlar"])]
    return "".join(parca)


def _kosu(icerik, gomulu):
    k = icerik["kosu"]
    if k is None:
        return '<h2>%s</h2><p class="soluk">%s</p>' % (
            _e(_("Sonuçlar")), _e(_("koşu dizini verilmedi — yalnız model raporu")))
    parca = ["<h2>%s</h2>" % _e(_("Koşu sonucu"))]
    if k["keff"] is None:
        parca.append("<p>%s</p>" % _e(_("Sabit kaynak hesabı — k-eff tanımsız.")))
    else:
        # Butun dis sinirlar sizintisizsa (yansitici/periyodik) sonuc k∞'dur
        parca.append('<p class="buyuk">%s = <span class="sayi">%s</span></p>'
                     % ("k∞" if k.get("sonsuz") else "k-eff", _e(bm(k["keff"], k["sigma"]))))
        parca.append("<p>%s<br>%s</p>" % (_e(k["durum"]), _e(k["ayrinti"])))
    satirlar = [(_("Çevrim (pasif)"), "%d (%d)" % (k["cevrim"], k["pasif"])),
                (_("Parçacık / çevrim"), str(k["parcacik"]))]
    if k["yakinsama"]:
        satirlar.append((_("Kaynak yakınsaması"), k["yakinsama"]))
    if k.get("kinetik"):
        kin = k["kinetik"]
        satirlar += [("β_eff", bm(kin["beta_eff"] * 1e5, kin["beta_eff_sapma"] * 1e5,
                                  "pcm")),
                     ("Λ", k.get("lambda_metni", ""))]
    parca.append(_anahtar_deger(satirlar))
    parca.append(_gorsel(icerik, "yakinsama", gomulu, alt=_("yakınsama")))
    return "".join(parca)


def _guc(icerik, gomulu):
    g = icerik["guc"]
    if not g:
        return ""
    parca = ["<h2>%s</h2>" % _e(_("Güç dağılımı"))]
    if g.get("hata"):
        return parca[0] + '<p class="hata">%s</p>' % _e(_("okunamadı: %s") % g["hata"])
    f = g["faktorler"]
    iyimser = " " + _("(tek koşu σ'sı iyimser)")
    satirlar = [("F_ΔH", bm(f["F_dH"], f["F_dH_sapma"]) + iyimser),
                ("F_q", bm(f["F_q"], f["F_q_sapma"]) + iyimser if f.get("F_q")
                 else _("tanımsız (2B model)")),
                (_("En sıcak çubuk"), g["sicak_cubuk"]),
                (_("Çubuk / eksenel dilim"), "%d / %d" % (f["cubuk_sayisi"], f["eksenel_dilim"]))]
    m = g.get("mutlak")
    if m and m.get("lineer_maks_W_cm"):
        satirlar += [(_("Ortalama lineer güç"), "%.1f W/cm" % m["lineer_ortalama_W_cm"]),
                     (_("En yüksek lineer güç"), "%.1f W/cm (%s)" % (
                         m["lineer_maks_W_cm"], m["lineer_tepe_kaynagi"]))]
    parca.append(_anahtar_deger(satirlar))
    parca.append("<p>%s</p>" % "<br>".join(_e(s) for s in g["yorum"]))
    parca.append(_gorsel(icerik, "guc_haritasi", gomulu, 520, _("güç haritası")))
    parca.append(_gorsel(icerik, "eksenel", gomulu, 400, _("eksenel profil")))
    return "".join(parca)


def _tallyler(icerik):
    if not icerik["tallyler"]:
        return ""
    parca = ["<h2>%s</h2>" % _e(_("Tally özetleri"))]
    for t in icerik["tallyler"]:
        parca.append("<h3>%s</h3>" % _e(t["ad"]))
        if t["hata"]:
            parca.append('<p class="hata">%s</p>' % _e(t["hata"]))
            continue
        parca.append(_tablo(t["sutunlar"], t["satirlar"]))
        if t["kirpildi"]:
            parca.append('<p class="soluk">%s</p>' % _e(
                _("… %d satır daha (tam tablo statepoint'te)") % t["kirpildi"]))
    return "".join(parca)


def _tukenme(icerik, gomulu):
    t = icerik["tukenme"]
    if not t:
        return ""
    satirlar = [(str(i), "%.2f" % z, "%.3f" % y, bm(k, s))
                for i, z, y, k, s in t["satirlar"]]
    parca = ["<h2>%s</h2>" % _e(_("Tükenme")),
             _tablo((pgettext("tükenme", "Adım"), _("Zaman [gün]"), _("Yanma [MWd/kgHM]"), "k"), satirlar),
             _gorsel(icerik, "tukenme", gomulu, alt=_("tükenme"))]
    if t["bulunamayan"]:
        parca.append('<p class="uyari">%s</p>' % _e(
            _("Sonuçta bulunamayan nüklidler: %s") % ", ".join(t["bulunamayan"])))
    return "".join(parca)


def _bulgular(icerik):
    parca = ["<h2>%s</h2>" % _e(_("Doğrulama bulguları"))]
    if not icerik["bulgular"]:
        return parca[0] + "<p>%s</p>" % _e(_("Bulgu yok."))
    satirlar = []
    for b in icerik["bulgular"]:
        css, ad = _SEVIYE.get(b["seviye"], ("", b["seviye"]))
        satirlar.append('<tr><td class="%s">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                        % (css, _e(_(ad)), _e(b["yer"]), _e(b["mesaj"]), _e(b["oneri"])))
    bas = "".join("<th>%s</th>" % _e(x) for x in (_("Seviye"), _("Yer"), _("Mesaj"), _("Öneri")))
    return parca[0] + ('<table border="1" cellspacing="0" cellpadding="3" width="100%%">'
                       "<tr>%s</tr>%s</table>" % (bas, "".join(satirlar)))


def _ek(icerik):
    return "<h2>%s</h2><pre>%s</pre>" % (_e(_("Ek: model (JSON)")), _e(icerik["spec_json"]))


def html(icerik, gomulu=True):
    """Rapor icerigini tam HTML belgesine cevirir."""
    from cekirdek import surum
    govde = "".join((_kapak(icerik), _model(icerik, gomulu), _kosu(icerik, gomulu),
                     _guc(icerik, gomulu), _tallyler(icerik), _tukenme(icerik, gomulu),
                     _bulgular(icerik), uygunluk_eki.html(icerik.get("uygunluk")),
                     _ek(icerik)))
    return _sablon("rapor.html").substitute(
        dil=_e(etkin_dil()), uretici=_e("%s %s" % (_(surum.UYGULAMA_ADI), surum.surum())),
        baslik=_e(icerik["kapak"]["baslik"]), stil=_stil(), govde=govde)
