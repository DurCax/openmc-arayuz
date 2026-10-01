# -*- coding: utf-8 -*-
"""
 arayuz/yardim  --  uygulama ici kullanim kilavuzu (cevrimdisi)

 Dalga 3 sozlesmesi (orkestrator, 01.10.2026; imzalar DEGISMEZ):
   ac(bolum_kimligi, pencere=None)  kilavuzu verilen bolumde acar -> bool
   BOLUMLER                         {bolum_kimligi: gorunen baslik (N_)}
   bolum_var(bolum_kimligi)         kimlik kilavuzda tanimli mi
 Ek:
   ara(metin, pencere=None)         kilavuzu acip metni arar -> eslesme sayisi
   bolum_basligi(bolum_kimligi)     BOLUMLER basligi, etkin dilde

 Ajan 12 arayuzdeki baglantilari (Yardim menusu, F1, alan "?" dugmeleri,
 bulgu -> bolum, uygunluk paneli KILAVUZ_BOLUMU) BU API ile kurar.

 Icerik: docs/kilavuz/{tr,en}/*.md (kaynak.py okur). Gosterim: QTextBrowser
 + Qt'nin Markdown destegi (belge.py, gosterici.py); yeni bagimlilik yok.
 Derleme (HTML + PDF): araclar/kilavuz.sh -> arayuz/yardim/derle.py.

 Hata yollari sessiz degildir: kilavuz dizini yoksa ya da kimlik bilinmiyorsa
 log + kullaniciya bildirim, donus False.
"""

from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

VARSAYILAN_BOLUM = "giris"

# Kimlikler docs/kilavuz/*/*.md basliklarindaki <a id="..."> capalaridir
# (testler/test_kilavuz.py KL1 ikisinin esligini denetler).
BOLUMLER = {
    "giris": N_("Bu kılavuz kime, nasıl okunur"),
    "kurulum": N_("Kurulum ve ilk açılış"),
    "nukleer-veri": N_("Nükleer veri ve tükenme zinciri"),
    "baslangic": N_("Başlangıç ekranı"),
    "ilk-hesap": N_("15 dakikada ilk hesap"),
    "kavramlar": N_("Kavramlar"),
    "karar-tablosu": N_("Hangi düzenek, hangi düğümler"),
    "sekmeler": N_("Sekme sekme başvuru"),
    "pencere-duzeni": N_("Pencerenin düzeni"),
    "malzemeler": N_("Malzemeler"),
    "parcalar": N_("Parçalar"),
    "demet": N_("Demet"),
    "geometri": N_("Geometri"),
    "geometri-gelismis": N_("Gelişmiş geometri editörü"),
    "hesap-ayarlari": N_("Hesap ayarları"),
    "calistir": N_("Çalıştır"),
    "analiz": N_("Analiz"),
    "tukenme": N_("Tükenme"),
    "dersler": N_("Rehberli dersler"),
    "ders-demet": N_("Ders: demet k∞"),
    "ders-tam-kor": N_("Ders: tam kor"),
    "ders-altigen-kor": N_("Ders: altıgen kor"),
    "ders-kare-altigen": N_("Ders: kare çekirdek + altıgen halka"),
    "ders-tambur": N_("Ders: tamburu herhangi bir geometriye yerleştirmek"),
    "ders-tukenme": N_("Ders: tükenme ve nüklid seçimi"),
    "ders-guc": N_("Ders: güç haritası ve F_ΔH"),
    "ders-benchmark": N_("Ders: benchmark ve C/E"),
    "ders-kritik-arama": N_("Ders: kritik arama"),
    "ders-rapor": N_("Ders: rapor ve uygunluk eki"),
    "sonuclar": N_("Sonuçları yorumlamak"),
    "once-ciz": N_("Önce çiz, sonra çalıştır"),
    "tuzaklar": N_("Bilinen tuzaklar"),
    "uygunluk-denetimi": N_("Uygunluk denetimi"),
    "vv": N_("Doğrulama ve geçerleme (V&V)"),
    "terminal": N_("Terminal ve HPC kullanımı"),
    "sorun-giderme": N_("Sorun giderme"),
    "uygunluk-kurallari": N_("Uygunluk kuralları (K1–K16)"),
    "sozluk": N_("Terim sözlüğü"),
}


def bolum_var(bolum_kimligi):
    """Kimlik kilavuzda tanimli mi."""
    return bolum_kimligi in BOLUMLER


def bolum_basligi(bolum_kimligi):
    """Bolumun gorunen basligi, etkin dilde ("" bilinmiyorsa)."""
    baslik = BOLUMLER.get(bolum_kimligi)
    return _(baslik) if baslik else ""


def _bildir(pencere, metin, tur):
    if pencere is None:
        return
    from arayuz.bilesenler.bildirim import bildir
    bildir(pencere, metin, tur=tur)


def _gosterici(pencere):
    """Etkin dilde yuklu kilavuz penceresi; kilavuz yoksa None (bildirilir)."""
    from arayuz.yardim import gosterici, kaynak
    g = gosterici.gosterici_al(pencere)
    dil = gosterici.dil()
    if g.klv is None or g.dil != dil or g.dizin is not None:
        try:
            g.yukle(dil)
        except (kaynak.KilavuzYok, OSError) as e:
            _log.error("kullanim kilavuzu yuklenemedi: %s", e)
            _bildir(pencere, _("Kullanım kılavuzu bulunamadı: {yol}").format(yol=e), "hata")
            return None
    g.show()
    g.raise_()
    g.activateWindow()
    return g


def ac(bolum_kimligi, pencere=None):
    """Kilavuzu bolum_kimligi bolumunde acar. Basari True; kilavuz yoksa ya da
    bolum bilinmiyorsa False (kullaniciya bildirilir, loglanir)."""
    kimlik = bolum_kimligi or VARSAYILAN_BOLUM
    g = _gosterici(pencere)
    if g is None:
        return False
    if bolum_var(kimlik) and g.bolume_git(kimlik):
        _log.info("kilavuz acildi: %s (%s)", kimlik, g.dil)
        return True
    _log.warning("kilavuzda bolum yok: %s", kimlik)
    _bildir(pencere if pencere is not None else g,
            _("Kılavuzda bu bölüm yok: {b}").format(b=kimlik), "uyari")
    return False


def ara(metin, pencere=None):
    """Kilavuzu acar ve metni arar (Ctrl+K paleti icin). Eslesme sayisi."""
    g = _gosterici(pencere)
    if g is None:
        return 0
    g.arama.setText(metin or "")
    return g.ara(metin)
