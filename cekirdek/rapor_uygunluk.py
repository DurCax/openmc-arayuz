# -*- coding: utf-8 -*-
"""
rapor_uygunluk.py -- uygunluk denetiminin (cekirdek/uygunluk_denetimi) rapor
eki, arayuz paneli ve komut satiri icin ortak yuzu (Dalga S-2).

    from cekirdek import rapor_uygunluk as ru
    ru.secili_profiller(spec)            -> ("A", "D")   (proje ayari)
    ru.profilleri_yaz(spec, ("A", "B"))  -> YENI spec (girdi degismez)
    ek = ru.ek_verisi(spec, kosu_dizini, rapor_metni=html)
    ru.cikis_kodu(bulgular)              -> 1 hata varsa, yoksa 0 (CLI)

PROFIL SECIMI spec["calistirma"]["uygunluk_profilleri"] listesindedir.
"calistirma" sema.tamamla'da derin birlestirilir (ek anahtar korunur) ve
fizik imzasinin disindadir (tukenme._FIZIK_DISI): secim degisince kosu
sonucu eskimez. Anahtar yoksa varsayilan A + D'dir ve dosyaya YAZILMAZ
(ornekler gidis-donusu bozulmaz).

Durust cerceve (profiller.durust_cerceve) ekte ve panelde AYNEN yazilir.
"""

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

SPEC_ANAHTARI = "uygunluk_profilleri"
VARSAYILAN_PROFILLER = ("A", "D")
# Ekte ve panelde durumlarin sirasi (once sorunlar).
DURUM_SIRASI = ("karsilanmadi", "bilgi", "uygulanamadi", "karsilandi")
_SEVIYE_SIRASI = {"hata": 0, "uyari": 1, "bilgi": 2}


def _gecerli_kimlikler():
    from cekirdek.uygunluk_denetimi.profiller import PROFIL_KIMLIKLERI
    return PROFIL_KIMLIKLERI


def _sirala(kimlikler):
    istenen = set(kimlikler)
    return tuple(k for k in _gecerli_kimlikler() if k in istenen)


def secili_profiller(spec):
    """Projenin sectigi profiller (gecerli kimlik sirasiyla). Anahtar yoksa
    VARSAYILAN_PROFILLER; bilinmeyen kimlikler atlanir ve loglanir."""
    ham = ((spec or {}).get("calistirma") or {}).get(SPEC_ANAHTARI)
    if ham is None:
        return VARSAYILAN_PROFILLER
    if not isinstance(ham, (list, tuple)):
        _log.warning("uygunluk profilleri liste değil (%r); varsayılan kullanılıyor", ham)
        return VARSAYILAN_PROFILLER
    bilinmeyen = [k for k in ham if k not in _gecerli_kimlikler()]
    if bilinmeyen:
        _log.warning("bilinmeyen uygunluk profilleri atlandı: %r", bilinmeyen)
    return _sirala(k for k in ham if k in _gecerli_kimlikler())


def profilleri_yaz(spec, profiller):
    """spec'in profil secimi `profiller` olan YENI kopyasi (sig kopya; yalniz
    "calistirma" yenilenir). Bilinmeyen kimlikte ValueError."""
    bilinmeyen = [k for k in profiller if k not in _gecerli_kimlikler()]
    if bilinmeyen:
        raise ValueError(_("bilinmeyen denetim profili: %s") % ", ".join(map(str, bilinmeyen)))
    calis = dict((spec or {}).get("calistirma") or {})
    calis[SPEC_ANAHTARI] = list(_sirala(profiller))
    return dict(spec or {}, calistirma=calis)


def profil_ayristir(metin):
    """"A,B" -> ("A", "B"). Bos ya da bilinmeyen kimlikte ValueError."""
    kimlikler = [p.strip().upper() for p in (metin or "").split(",") if p.strip()]
    if not kimlikler:
        raise ValueError(_("profil listesi boş (ör. A,D)"))
    profilleri_yaz({}, kimlikler)             # dogrulama (ValueError)
    return _sirala(kimlikler)


def sirala(bulgular):
    """Bulgular: once karsilanmayanlar (hata > uyari > bilgi), sonra not,
    uygulanamayan, karsilanan; esitlikte denetim sirasi korunur (YENI liste)."""
    def anahtar(ib):
        i, b = ib
        durum = getattr(b, "durum", "bilgi")
        return (DURUM_SIRASI.index(durum) if durum in DURUM_SIRASI else len(DURUM_SIRASI),
                _SEVIYE_SIRASI.get(b.seviye, 3), i)
    return [b for _i, b in sorted(enumerate(bulgular), key=anahtar)]


def usl_notu(profiller, vv=None):
    """B secili ve V&V ozeti (USL) yoksa ekte/panelde yazilacak not; yoksa ""."""
    if "B" not in profiller or (vv is not None and getattr(vv, "usl", None) is not None):
        return ""
    return _("USL hesaplanamadı: doğrulama (V&V) kümesi yok. Bu koşunun k değeri bir "
             "üst alt-kritiklik sınırıyla karşılaştırılmadı; bu sonuç kritiklik "
             "güvenliği kanıtı değildir.")


def denetle(spec, kosu_dizini, profiller=None, rapor_metni=None, vv=None):
    """(bulgular, hata_metni). Girdi hatasi (bozuk uygunluk_girdisi.json vb.)
    istisna olarak yukari cikmaz: hata_metni doner ve loglanir."""
    from cekirdek.uygunluk_denetimi import denetle as _d
    profiller = secili_profiller(spec) if profiller is None else tuple(profiller)
    if not profiller:
        return [], ""
    try:
        return _d.denetle(spec, kosu_dizini, profiller, vv=vv, rapor_metni=rapor_metni), ""
    except (OSError, ValueError) as e:
        _log.warning("uygunluk denetimi yapılamadı: %s", kosu_dizini, exc_info=True)
        return [], _("uygunluk denetimi yapılamadı: %s") % e


def _satir(b):
    from cekirdek.uygunluk_denetimi.kurallar import etiket_metni
    return {"kural": b.kural, "profil": b.profil, "seviye": b.seviye,
            "durum": getattr(b, "durum", "bilgi"), "mesaj": b.mesaj,
            "oneri": b.oneri or "", "kaynak": b.kaynak,
            "etiket": etiket_metni(b.etiket)}


def ek_verisi(spec, kosu_dizini, profiller=None, rapor_metni=None, vv=None):
    """
    Rapor eki sozlugu (YENI):
      profiller [(kimlik, gorunen ad)], gruplar {durum: [satir]}, ozet,
      cerceve (AYNEN), usl_notu, hata ("" | metin)
    satir: kural, profil, seviye, durum, mesaj, oneri, kaynak, etiket (metin).
    """
    from cekirdek.uygunluk_denetimi.denetle import ozet
    from cekirdek.uygunluk_denetimi.profiller import durust_cerceve, profil_getir
    profiller = secili_profiller(spec) if profiller is None else tuple(profiller)
    bulgular, hata = denetle(spec, kosu_dizini, profiller, rapor_metni=rapor_metni, vv=vv)
    gruplar = {d: [] for d in DURUM_SIRASI}
    for b in sirala(bulgular):
        gruplar.setdefault(getattr(b, "durum", "bilgi"), []).append(_satir(b))
    return {"profiller": [(k, profil_getir(k).gorunen_ad()) for k in profiller],
            "gruplar": gruplar, "ozet": ozet(bulgular), "cerceve": durust_cerceve(),
            "usl_notu": usl_notu(profiller, vv), "hata": hata}


def cikis_kodu(bulgular):
    """CI / ders otomasyonu: karsilanmayan "hata" bulgusu varsa 1, yoksa 0."""
    from cekirdek.uygunluk_denetimi.denetle import sorunlar
    return 1 if any(b.seviye == "hata" for b in sorunlar(bulgular)) else 0
