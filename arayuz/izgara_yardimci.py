# -*- coding: utf-8 -*-
"""
izgara_yardimci.py -- izgara bilesenlerinin saf yardimcilari: harf haritasi
<-> parca adlari, parca renkleri, palet ogeleri, renk karesi simgesi

arayuz/izgara.py'den YALNIZ TASINDI (v3 T2, dosya boyu): sabitler ve "saf
yardimcilar" bolumu. Davranis aynidir; adlar izgara'dan da erisilir
(izgara.harita_adlara, izgara.adlardan_harita, izgara.palet_ogeleri ...).
Sozlesme ve ornekler: arayuz/izgara.py modul belgesi.
"""

import math
import string

from PySide6 import QtCore, QtGui

from cekirdek import sema
from cekirdek.ceviri import N_, _


# Tanimsiz (anahtarda karsiligi olmayan) hucre icin harita karakteri.
BOS_HARF = "."

# Otomatik harf adaylari -- ASCII: harf haritasi dosyada okunur kalmali.
_HARF_ADAYLARI = string.ascii_lowercase + string.ascii_uppercase + string.digits

# Ayirt edilebilir kategorik palet (acik ve koyu zeminde okunur).
_PALET = [(222, 93, 40), (90, 150, 220), (120, 190, 110), (200, 170, 70),
          (160, 110, 200), (70, 180, 180), (215, 120, 160), (150, 150, 160),
          (130, 100, 70), (40, 110, 170), (190, 60, 60), (100, 140, 60)]
_BOSLUK_RENGI = (55, 58, 64)
_TANIMSIZ_RENGI = (200, 200, 205)


# ============================================================================
# saf yardimcilar
# ============================================================================

def harita_adlara(harita, anahtar):
    """
    Harf haritasini parca adlarina cevirir.

    harita : ["yyk", ...]  (kare: satirlar, altigen: DISTAN ICE halkalar)
    anahtar: {"y": "yakit_cubugu", ...}
    DONER  : [["yakit_cubugu", ...], ...]; anahtarda olmayan harf -> None
    """
    anahtar = anahtar or {}
    return [[anahtar.get(h) for h in satir] for satir in (harita or [])]


def _yeni_harf(ad, kullanilan):
    """
    Yeni bir parca icin harf: once adin ilk harfi (kucuk, sonra buyuk) --
    "yakit_cubugu" -> y, "kilavuz_boru" -> k -- dolu ise a-z, A-Z, 0-9 sirasi.
    Deterministiktir: ayni girdi her zaman ayni harfi verir.
    """
    adaylar = []
    ilk = next((ch for ch in str(ad) if ch.isascii() and ch.isalnum()), None)
    if ilk:
        adaylar += [ilk.lower(), ilk.upper()]
    adaylar += list(_HARF_ADAYLARI)
    for h in adaylar:
        if h not in kullanilan:
            return h
    raise ValueError(_("haritada en fazla %d farklı parça kullanılabilir") % len(_HARF_ADAYLARI))


def adlardan_harita(adlar, eski_anahtar=None, eski_harita=None):
    """
    Parca adlari izgarasindan (harita, anahtar) uretir.

    adlar       : [[ad | None, ...], ...]  (harita_adlara'nin bicimi)
    eski_anahtar: dosyadaki mevcut anahtar. Butun girdileri AYNEN korunur
                  (kullanilmayanlar dahil: dosya gereksiz yere degismesin);
                  yeni parcalar sona eklenir.
    eski_harita : dosyadaki mevcut harita. Verilirse her hucre, eski harfi
                  hala AYNI parcayi gosteriyorsa o harfi korur. Bu olmadan
                  ayni parcaya iki harf veren dosyalar (pwr_17x17: kilavuz
                  borusu 'k', enstruman borusu 'e') birebir geri yazilamazdi.
    Hucre adi None ise (tanimsiz) BOS_HARF yazilir -- dogrulama bunu
    "tanimsiz harf" olarak yakalar; sessizce bir parcaya cevrilmez.

    Ayni parca icin birden fazla eski harf varsa (ve konum bilgisi yoksa)
    anahtardaki ILK harf kullanilir.
    """
    anahtar = dict(eski_anahtar or {})
    tercih = {}
    for h, ad in anahtar.items():
        tercih.setdefault(ad, h)
    kullanilan = set(anahtar) | {BOS_HARF}
    for satir in (eski_harita or []):
        kullanilan.update(satir)

    harita = []
    for r, satir in enumerate(adlar or []):
        eski_satir = (eski_harita[r] if eski_harita is not None
                      and r < len(eski_harita) else "")
        yeni = []
        for c, ad in enumerate(satir):
            eski_h = eski_satir[c] if c < len(eski_satir) else None
            if eski_h is not None and anahtar.get(eski_h) == ad:
                yeni.append(eski_h)
            elif ad is None:
                yeni.append(BOS_HARF)
            elif ad in tercih:
                yeni.append(tercih[ad])
            else:
                h = _yeni_harf(ad, kullanilan)
                anahtar[h] = ad
                tercih[ad] = h
                kullanilan.add(h)
                yeni.append(h)
        harita.append("".join(yeni))
    return harita, anahtar


def _mesafe(a, b):
    return math.sqrt(sum((int(x) - int(y)) ** 2 for x, y in zip(a, b)))


def _malzeme_rengi(spec, ad):
    for m in spec.get("malzemeler", []):
        if m["ad"] == ad and m.get("renk"):
            return tuple(int(x) for x in m["renk"][:3])
    return None


def _parca_rengi(spec, ad, derinlik=0):
    """Parcanin dogal rengi: cubukta en ic bolgenin, plakada yakit etinin,
    kafeste en cok kullanilan parcanin, malzemede kendi rengi."""
    if ad == "bosluk":
        return _BOSLUK_RENGI
    for c in spec.get("cubuklar", []):
        if c["ad"] == ad:
            for b in c.get("bolgeler", []):
                r = _malzeme_rengi(spec, b.get("malzeme"))
                if r:
                    return r
            return None
    for p in spec.get("plakalar", []):
        if p["ad"] == ad:
            return _malzeme_rengi(spec, p.get("et_malzeme"))
    for d in spec.get("demetler", []):
        if d["ad"] == ad and derinlik < 4:
            sayac = {}
            for satir in d.get("harita") or []:
                for h in satir:
                    sayac[h] = sayac.get(h, 0) + 1
            for h, _n in sorted(sayac.items(), key=lambda x: -x[1]):
                hedef = (d.get("anahtar") or {}).get(h)
                if hedef and hedef != ad:
                    return _parca_rengi(spec, hedef, derinlik + 1)
            return None
    return _malzeme_rengi(spec, ad)


_TUR_ETIKETI = {"cubuk": N_("çubuk"), "plaka": N_("plaka"), "demet": N_("kafes"),
                "malzeme": N_("malzeme"), "bosluk": N_("boşluk")}   # anahtar; gosterirken _()


def palet_ogeleri(spec, turler=("cubuk", "plaka", "demet", "malzeme", "bosluk"),
                  haric=()):
    """
    Spec'teki parcalardan palet girdileri: [(ad, etiket, rgb, tur_etiketi)].

    Renkler birbirinden AYIRT EDILIR: iki parcanin dogal rengi yakinsa
    (or. ikisi de su ile dolu iki boru) sonraki kategorik palet rengi verilir.
    haric: listelenmeyecek adlar (or. kendi icine yerlestirilemeyen kafes).
    """
    ogeler = []
    for tur in turler:
        if tur == "bosluk":
            ogeler.append(("bosluk", _("Boş (madde yok)"), "bosluk"))
            continue
        liste = {"cubuk": "cubuklar", "plaka": "plakalar", "demet": "demetler",
                 "malzeme": "malzemeler"}[tur]
        for x in spec.get(liste, []):
            # Malzemeler her listede ayni bicimde: "ad — aciklama".
            # Parca adlari kimliktir ve her listede aynen gorunur ("yakit_cubugu");
            # alt cizgiyi bosluga cevirmek "yakit cubugu" gibi ASCII'lestirilmis
            # Turkce gibi okunuyordu.
            etiket = sema.malzeme_etiketi(x) if tur == "malzeme" else x["ad"]
            ogeler.append((x["ad"], etiket, tur))
    sonuc, kullanilan = [], []
    yedek = iter(_PALET * 4)
    for ad, etiket, tur in ogeler:
        if ad in haric:
            continue
        rgb = _parca_rengi(spec, ad)
        if rgb is None or any(_mesafe(rgb, u) < 60 for u in kullanilan):
            rgb = None
            for aday in yedek:
                if all(_mesafe(aday, u) >= 60 for u in kullanilan):
                    rgb = aday
                    break
            if rgb is None:
                rgb = _PALET[len(sonuc) % len(_PALET)]
        kullanilan.append(rgb)
        sonuc.append((ad, etiket, rgb, _TUR_ETIKETI[tur]))
    return sonuc


def _qrenk(deger):
    if isinstance(deger, QtGui.QColor):
        return QtGui.QColor(deger)
    if deger is None:
        return QtGui.QColor(*_TANIMSIZ_RENGI)
    return QtGui.QColor(*[int(x) for x in deger[:3]])


def _yazi_rengi(zemin):
    """Zemine gore okunur yazi rengi (siyah/beyaz)."""
    parlaklik = 0.299 * zemin.red() + 0.587 * zemin.green() + 0.114 * zemin.blue()
    return QtGui.QColor(20, 20, 20) if parlaklik > 150 else QtGui.QColor(250, 250, 250)


def _renk_karesi(rgb, boyut=18):
    """Kenarli, yuvarlatilmis renk karesi simgesi."""
    pix = QtGui.QPixmap(boyut, boyut)
    pix.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    # Orta gri kenar: hem acik hem koyu zeminde koyu/acik renkli kare secilir.
    p.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128, 200), 1))
    p.setBrush(_qrenk(rgb))
    p.drawRoundedRect(QtCore.QRectF(1.5, 1.5, boyut - 3, boyut - 3), 4, 4)
    p.end()
    simge = QtGui.QIcon()
    # Secili satirda stil simgeyi vurgu rengiyle BOYUYORDU (turuncu -> kahve):
    # renk karesi her durumda ayni gorunmeli.
    for kip in (QtGui.QIcon.Normal, QtGui.QIcon.Selected, QtGui.QIcon.Active):
        simge.addPixmap(pix, kip)
    return simge
