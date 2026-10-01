# -*- coding: utf-8 -*-
"""
 arayuz/yardim/kaynak.py  --  kilavuz kaynaklarini (Markdown) okur ve birlestirir

 Qt'ye BAGLI DEGILDIR: test, derleme (derle.py) ve gosterici (gosterici.py)
 ayni ayristiriciyi kullanir.

 KAYNAK DUZENI (docs/kilavuz/)
   tr/NN-ad.md, en/NN-ad.md   ayni dosya adlari; dil dizinle ayrilir
   resimler/<dil>/<ad>.png    ekran goruntuleri (araclar/kilavuz_ekran.py)

 KIMLIK (capa) BICIMI
   Basligin HEMEN ustundeki satir, tek basina:   <a id="geometri"></a>
   GitHub bunu capa olarak gosterir; burada satir silinir ve kimlik sonraki
   basliga baglanir (gosterici QTextDocument'te capa adi olarak koyar).

 BIRLESTIRME (kilavuz(dil))
   - Dosyalar TR dizinindeki sirayla birlesir; EN dosyasi yoksa TR'si alinir
     ve Kilavuz.eksik'e yazilir (gosterici uyari seridi gosterir, loglar).
   - "NN-ad.md#k" baglantilari "#k" olur (tek belge); "NN-ad.md" o dosyanin
     ilk kimligine gider; diger goreli yollar mutlak dosya adresine cevrilir.
   - EN resmi yoksa TR resmi kullanilir (Kilavuz.yedek_resimler).
   - Tek satirlik HTML yorumlari (<!-- ... -->, ör. sozluk isaretleri) silinir.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORTAM_DEGISKENI = "OPENMC_ARAYUZ_KILAVUZ"
KILAVUZ_DIZINI = os.environ.get(ORTAM_DEGISKENI) or os.path.join(KOK, "docs", "kilavuz")
KAYNAK_DIL = "tr"
DILLER = ("tr", "en")
RESIM_DIZINI = "resimler"

_KIMLIK = re.compile(r'^<a id="([a-z0-9][a-z0-9-]*)"></a>\s*$')
_BASLIK = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_CIT = re.compile(r"^(```|~~~)")
_YORUM = re.compile(r"^<!--.*-->\s*$")
_BAGLANTI = re.compile(r'(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(\s*([^)\s]+)(?:\s+"[^"]*")?\s*\)')


class KilavuzYok(Exception):
    """Kilavuz dizini ya da kaynak dil dosyalari bulunamadi."""


@dataclass(frozen=True)
class Baslik:
    seviye: int
    metin: str
    kimlik: Optional[str]
    satir: int
    dosya: str = ""


@dataclass(frozen=True)
class Baglanti:
    metin: str
    hedef: str
    resim: bool
    satir: int


@dataclass(frozen=True)
class Ayrisim:
    basliklar: Tuple[Baslik, ...]
    kimlikler: Tuple[str, ...]
    baglantilar: Tuple[Baglanti, ...]
    sorunlar: Tuple[str, ...]


@dataclass(frozen=True)
class Kilavuz:
    dil: str
    markdown: str
    basliklar: Tuple[Baslik, ...]
    taban: str                      # goreli resim yollarinin cozuldugu dizin
    eksik: Tuple[str, ...] = ()     # EN'de olmayip TR'den alinan dosyalar
    yedek_resimler: Tuple[str, ...] = ()

    @property
    def kimlikler(self):
        return tuple(b.kimlik for b in self.basliklar if b.kimlik)


def duz_baslik(metin):
    """Basliktaki Markdown isaretlerini ayiklar (Qt blok metniyle karsilastirma)."""
    m = _BAGLANTI.sub(lambda e: e.group(2), metin)
    m = re.sub(r"<[^>]+>", "", m)
    for isaret in ("**", "__", "`", "*"):
        m = m.replace(isaret, "")
    return re.sub(r"\s+", " ", m.replace("\\", "")).strip()


def ayristir(metin):
    """Basliklar, kimlikler, baglantilar ve kimlik satiri sorunlari (kod bloklari haric)."""
    basliklar, kimlikler, baglantilar, sorunlar = [], [], [], []
    bekleyen = None
    cit = False
    for no, satir in enumerate(metin.splitlines(), 1):
        if _CIT.match(satir.strip()):
            cit = not cit
            continue
        if cit:
            continue
        k = _KIMLIK.match(satir.strip())
        if k:
            if bekleyen:
                sorunlar.append("satir %d: kimlik '%s' basliksiz" % (no - 1, bekleyen))
            bekleyen = k.group(1)
            kimlikler.append(bekleyen)
            continue
        b = _BASLIK.match(satir)
        if b:
            basliklar.append(Baslik(len(b.group(1)), duz_baslik(b.group(2)), bekleyen, no))
            bekleyen = None
        elif bekleyen:
            sorunlar.append("satir %d: kimlik '%s' basliktan hemen once degil" % (no, bekleyen))
            bekleyen = None
        for e in _BAGLANTI.finditer(satir):
            baglantilar.append(Baglanti(e.group(2), e.group(3), e.group(1) == "!", no))
    if bekleyen:
        sorunlar.append("dosya sonu: kimlik '%s' basliksiz" % bekleyen)
    return Ayrisim(tuple(basliklar), tuple(kimlikler), tuple(baglantilar), tuple(sorunlar))


def dosya_adlari(dizin=None):
    """Kaynak dildeki bolum dosyalari, sirali (00-giris.md, 01-..., 04a-...)."""
    tr = os.path.join(dizin or KILAVUZ_DIZINI, KAYNAK_DIL)
    if not os.path.isdir(tr):
        return []
    return sorted(a for a in os.listdir(tr) if a.endswith(".md"))


def dosya_yolu(dil, ad, dizin=None):
    return os.path.join(dizin or KILAVUZ_DIZINI, dil, ad)


def dosya_oku(dil, ad, dizin=None):
    with open(dosya_yolu(dil, ad, dizin), encoding="utf-8") as f:
        return f.read()


def _ilk_kimlikler(metinler):
    sonuc = {}
    for ad, metin in metinler.items():
        kimlikler = ayristir(metin).kimlikler
        if kimlikler:
            sonuc[ad] = kimlikler[0]
    return sonuc


def _hedefi_cevir(hedef, resim, ilk, taban, dil, yedekler):
    if re.match(r"^[a-z]+:", hedef) or hedef.startswith("#"):
        return hedef
    dosya, _ayr, capa = hedef.partition("#")
    if dosya in ilk or (dosya.endswith(".md") and "/" not in dosya):
        return "#" + (capa or ilk.get(dosya, ""))
    if resim:
        yol = os.path.normpath(os.path.join(taban, dosya))
        if dil != KAYNAK_DIL and not os.path.exists(yol):
            tr = dosya.replace("/%s/" % dil, "/%s/" % KAYNAK_DIL)
            if os.path.exists(os.path.normpath(os.path.join(taban, tr))):
                yedekler.append(os.path.basename(dosya))
                return tr
        return dosya
    yol = os.path.normpath(os.path.join(taban, dosya))
    return "file://" + yol.replace(os.sep, "/") + ("#" + capa if capa else "")


def _donustur(metin, ilk, taban, dil, yedekler):
    satirlar, cit = [], False
    for satir in metin.splitlines():
        if _CIT.match(satir.strip()):
            cit = not cit
        elif not cit and (_KIMLIK.match(satir.strip()) or _YORUM.match(satir.strip())):
            continue
        elif not cit:
            satir = _BAGLANTI.sub(lambda e: "%s[%s](%s)" % (
                e.group(1), e.group(2),
                _hedefi_cevir(e.group(3), e.group(1) == "!", ilk, taban, dil, yedekler)), satir)
        satirlar.append(satir)
    return "\n".join(satirlar)


def kilavuz(dil, dizin=None):
    """Dilin birlesik kilavuzu (Kilavuz). Kaynak dil dosyalari yoksa KilavuzYok."""
    dizin = dizin or KILAVUZ_DIZINI
    adlar = dosya_adlari(dizin)
    if not adlar:
        raise KilavuzYok(os.path.join(dizin, KAYNAK_DIL))
    dil = dil if dil in DILLER else KAYNAK_DIL
    metinler, eksik = {}, []
    for ad in adlar:
        kaynak_dil = dil if os.path.exists(dosya_yolu(dil, ad, dizin)) else KAYNAK_DIL
        if kaynak_dil != dil:
            eksik.append(ad)
        metinler[ad] = dosya_oku(kaynak_dil, ad, dizin)
    ilk = _ilk_kimlikler(metinler)
    taban = os.path.join(dizin, dil)
    yedekler, parcalar, basliklar = [], [], []
    for ad in adlar:
        basliklar += [Baslik(b.seviye, b.metin, b.kimlik, b.satir, ad)
                      for b in ayristir(metinler[ad]).basliklar]
        parcalar.append(_donustur(metinler[ad], ilk, taban, dil, yedekler))
    return Kilavuz(dil, "\n\n".join(parcalar) + "\n", tuple(basliklar), taban,
                   tuple(eksik), tuple(dict.fromkeys(yedekler)))
