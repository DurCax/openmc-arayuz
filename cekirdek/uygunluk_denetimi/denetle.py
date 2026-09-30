# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_denetimi/denetle.py  --  Sonuc uygunluk denetimi (Dalga S-1)
================================================================================

 SOZLESME (S-2 panel/rapor eki ve CLI buna dayanir)

   from cekirdek.uygunluk_denetimi.denetle import denetle, ozet
   bulgular = denetle(spec, kosu_dizini, ("A", "D"),
                      vv=None, kor=None, rapor_metni=None, uygulama=None)

   spec         proje sozlugu; None ise kosu_dizini/spec.json okunur (yoksa None)
   kosu_dizini  statepoint, kosu.log, (istege bagli) uygunluk_girdisi.json
   profiller    kimlikler ("A".."D") ya da profiller.Profil nesneleri;
                None -> ("A",)
   vv           vv_arayuz.VVOzeti (S-3) -- Profil B
   kor          kor sonuclari sozlugu (kurallar_kor) -- Profil C; verilmezse
                uygunluk_girdisi.json'un "kor" anahtari
   rapor_metni  denetlenecek rapor (HTML/duz) -- Profil D K5
   uygulama     AOA parametreleri {"zenginlik": 4.5, "tayf": "termal", ...};
                verilmezse uygunluk_girdisi.json'un "uygulama" anahtari

   DONER [DenetimBulgusu]  (cekirdek.dogrula._ortak.Bulgu alt sinifi) --
   profil ve kural sirasiyla; GECEN kurallar da "karsilandi" durumuyla
   listede yer alir. Sorunlar: sorunlar(bulgular); sayilar: ozet(bulgular).

 Hicbir kural istisnayla denetimi durdurmaz: kural hatasi loglanir ve
 "hata" bulgusu olarak doner (sessiz hata yok).
 spec DEGISMEZ.
================================================================================
"""

import json
import os

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.uygunluk_denetimi import ayristir, kurallar as _k, profiller as _p

_log = kaydedici(__name__)

GIRDI_DOSYASI = "uygunluk_girdisi.json"
VARSAYILAN_PROFILLER = ("A",)


def _profilleri_coz(profiller):
    sonuc = []
    for p in profiller or VARSAYILAN_PROFILLER:
        sonuc.append(p if isinstance(p, _p.Profil) else _p.profil_getir(p))
    return sonuc


def _spec_yukle(spec, kosu_dizini):
    if spec is not None or not kosu_dizini:
        return spec
    yol = os.path.join(kosu_dizini, "spec.json")
    if not os.path.exists(yol):
        return None
    from cekirdek import sema
    try:
        return sema.yukle(yol)
    except Exception:
        _log.warning("koşu dizinindeki spec.json okunamadı: %s", yol, exc_info=True)
        return None


def girdi_dosyasi_oku(kosu_dizini):
    """kosu_dizini/uygunluk_girdisi.json -> sozluk (yoksa {}). Bozuksa ValueError."""
    yol = os.path.join(kosu_dizini, GIRDI_DOSYASI) if kosu_dizini else None
    if not yol or not os.path.exists(yol):
        return {}
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError(_("%s okunamadı: %s") % (GIRDI_DOSYASI, e)) from e
    if not isinstance(veri, dict):
        raise ValueError(_("%s bir JSON nesnesi olmalı") % GIRDI_DOSYASI)
    return veri


def baglam_kur(spec, kosu_dizini, vv=None, kor=None, rapor_metni=None, uygulama=None):
    """Kurallarin ortak baglami (profil esikleri denetle() icinde eklenir)."""
    girdi = girdi_dosyasi_oku(kosu_dizini)
    kosu, kosu_hatasi = ayristir.kosu_verisi(kosu_dizini)
    return _k.Baglam(
        spec=_spec_yukle(spec, kosu_dizini), kosu_dizini=kosu_dizini, kosu=kosu,
        kosu_hatasi=kosu_hatasi,
        cikti=ayristir.cikti_ozeti(kosu_dizini) if kosu_dizini else None,
        vv=vv, kor=kor if kor is not None else girdi.get("kor"),
        rapor_metni=rapor_metni,
        uygulama=dict(uygulama if uygulama is not None else girdi.get("uygulama") or {}))


def _kurali_isle(kural, baglam):
    try:
        return list(kural.islev(kural, baglam))
    except Exception as e:
        _log.exception("uygunluk kuralı %s değerlendirilemedi", kural.kimlik)
        return [kural.ihlal("hata", _("Kural değerlendirilemedi (%s): %s")
                            % (type(e).__name__, e),
                            _("Günlük dosyasına bakın ve hatayı bildirin."))]


def denetle(spec, kosu_dizini, profiller=None, vv=None, kor=None, rapor_metni=None,
            uygulama=None):
    """Bkz. modul basligi. DONER [DenetimBulgusu]."""
    profil_listesi = _profilleri_coz(profiller)
    baglam = baglam_kur(spec, kosu_dizini, vv=vv, kor=kor, rapor_metni=rapor_metni,
                        uygulama=uygulama)
    kayit = {k.kimlik: k for k in _k.tum_kurallar()}
    bulgular = []
    for profil in profil_listesi:
        pb = baglam.profil_ile(profil.esikler)
        for kimlik in profil.kurallar:
            bulgular += _kurali_isle(kayit[kimlik], pb)
    return bulgular


def sorunlar(bulgular):
    """Yalniz karsilanmayan (hata/uyari/bilgi) bulgular."""
    return [b for b in bulgular if getattr(b, "durum", None) == _k.KARSILANMADI]


def alarmlar(bulgular):
    """Hata ya da uyari seviyesindeki bulgular (yanlis alarm olcumu bunu sayar)."""
    return [b for b in bulgular if b.seviye in ("hata", "uyari")]


def ozet(bulgular):
    """{"durum": {durum: sayi}, "seviye": {seviye: sayi}} -- panel/rapor basligi."""
    durum = {d: 0 for d in _k.DURUMLAR}
    seviye = {"hata": 0, "uyari": 0, "bilgi": 0}
    for b in bulgular:
        durum[getattr(b, "durum", _k.BILGI)] += 1
        seviye[b.seviye] += 1
    return {"durum": durum, "seviye": seviye}
