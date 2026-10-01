# -*- coding: utf-8 -*-
"""
uygunluk_eki.py -- raporun "Uygunluk eki" bolumu (Dalga S-2).

    html(ek) -> HTML parcasi; ek None ise "" (taslak: K5 eksiz metni denetler)

ek: cekirdek/rapor_uygunluk.ek_verisi sozlugu. Bolum sirasi: durust cerceve
(AYNEN), secilen profiller, ozet sayilar, (B secili ve V&V yoksa) USL notu,
sonra durum gruplari: karsilanmayan, not, uygulanamayan, karsilanan. Her
satirda kural kimligi, profil, seviye, etiket kisaltmasi (IU/S/P/K), bulgu +
oneri, kaynak. QTextDocument (PDF) alt kumesiyle uyumlu: basit tablo + sinif.
"""

import html as _html

from cekirdek.ceviri import _, N_

_DURUM_BASLIKLARI = {
    "karsilanmadi": N_("Karşılanmayan kurallar"),
    "bilgi": N_("Notlar (bilgi)"),
    "uygulanamadi": N_("Uygulanamayan kurallar (değerlendirilemedi)"),
    "karsilandi": N_("Karşılanan kurallar"),
}
_OZET_ADLARI = (("karsilandi", N_("karşılanan")), ("karsilanmadi", N_("karşılanmayan")),
                ("uygulanamadi", N_("uygulanamayan")), ("bilgi", N_("not")))
_SEVIYE = {"hata": ("hata", N_("HATA")), "uyari": ("uyari", N_("UYARI")),
           "bilgi": ("bilgi", N_("BİLGİ"))}
# Etiket kisaltmalari (kurallar.etiket_metni'nin tam adlari aciklamada).
ETIKET_KISA = {"iyi_uygulama": N_("İU"), "standart": N_("S"), "proje_olcutu": N_("P"),
               "kullanici_siniri": N_("K")}
_TABLO = '<table border="1" cellspacing="0" cellpadding="3" width="100%%">%s</table>'


def _e(metin):
    return _html.escape("" if metin is None else str(metin))


def _etiket_kisa(satir):
    from cekirdek.uygunluk_denetimi.kurallar import etiket_metni
    for kimlik, kisa in ETIKET_KISA.items():
        if etiket_metni(kimlik) == satir["etiket"]:
            return _(kisa)
    return satir["etiket"]


def etiket_aciklamasi():
    """"İU = iyi uygulama (...); S = ..." -- tablo altindaki aciklama."""
    from cekirdek.uygunluk_denetimi.kurallar import etiket_metni
    return "; ".join("%s = %s" % (_(kisa), etiket_metni(k)) for k, kisa in ETIKET_KISA.items())


def _satir_html(s):
    css, ad = _SEVIYE.get(s["seviye"], ("", s["seviye"]))
    bulgu = _e(s["mesaj"])
    if s["oneri"]:
        bulgu += "<br><i>%s</i> %s" % (_e(_("Öneri:")), _e(s["oneri"]))
    return ('<tr><td class="sayi">%s</td><td>%s</td><td class="%s">%s</td><td>%s</td>'
            "<td>%s</td><td class=\"etiket\">%s</td></tr>"
            % (_e(s["kural"]), _e(s["profil"]), css, _e(_(ad)), _e(_etiket_kisa(s)),
               bulgu, _e(s["kaynak"])))


def _grup(durum, satirlar):
    baslik = _e(_(_DURUM_BASLIKLARI.get(durum, durum)))
    if not satirlar:
        return '<h3>%s (0)</h3><p class="soluk">%s</p>' % (baslik, _e(_("yok")))
    bas = "".join("<th>%s</th>" % _e(b) for b in (
        _("Kural"), _("Profil"), _("Seviye"), _("Etiket"), _("Bulgu"), _("Kaynak")))
    govde = "".join(_satir_html(s) for s in satirlar)
    return "<h3>%s (%d)</h3>%s" % (baslik, len(satirlar),
                                   _TABLO % ("<tr>%s</tr>%s" % (bas, govde)))


def _ozet(ek):
    durum = ek["ozet"]["durum"]
    return ", ".join("%d %s" % (durum.get(k, 0), _(ad)) for k, ad in _OZET_ADLARI)


def html(ek):
    """Uygunluk eki HTML parcasi; ek None ise bos metin."""
    if not ek:
        return ""
    profiller = "; ".join("%s — %s" % (k, ad) for k, ad in ek["profiller"]) or _("seçilmedi")
    parca = ["<h2>%s</h2>" % _e(_("Uygunluk eki")),
             '<p class="kutu">%s</p>' % _e(ek["cerceve"]),
             "<p><b>%s</b> %s</p>" % (_e(_("Seçilen denetim profilleri:")), _e(profiller)),
             "<p><b>%s</b> %s</p>" % (_e(_("Özet:")), _e(_ozet(ek)))]
    if ek["usl_notu"]:
        parca.append('<p class="uyari">%s</p>' % _e(ek["usl_notu"]))
    if ek["hata"]:
        parca.append('<p class="hata">%s</p>' % _e(ek["hata"]))
    parca += [_grup(d, ek["gruplar"].get(d) or []) for d in _DURUM_BASLIKLARI]
    parca.append('<p class="soluk">%s</p>' % _e(_("Etiketler: %s. Kural kimlikleri ve "
                                                  "kaynaklar: docs/STANDARTLAR.md §3.")
                                                % etiket_aciklamasi()))
    return "".join(parca)
