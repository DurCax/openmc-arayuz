# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/yoklama_arka.py  --  Nokta yoklamasi AYRI SURECTE (H1b)
================================================================================

 NEDEN
   Arayuzun dogrulama zamanlayicisi her tustan sonra gelismis agaci dogrular;
   nokta yoklamasi modeli kurar (kurucu.kur, SFR ~0.4 s) ve 600 noktayi yoklar
   (~0.3 s): ana is parcaciginda ~0.7 s donma (hedef: hicbir islem > 200 ms).
   Model kurulumu IS PARCACIGINDA yapilamaz: kurucu.kur openmc.reset_auto_ids()
   cagirir ve openmc kimlik sayaclari surec geneli; ayni anda ana is parcaciginda
   kurulan bir model (kosu, XML disa aktarma) cakisan kimlikler alirdi. Bu
   yuzden yoklama tek iscili bir SUREC havuzunda (spawn) calisir; ana surecin
   openmc durumuna dokunmaz.

 SOZLESME
   istek(anahtar, spec, n, tohum, bildir) -> None
       Is kuyruga girer (ayni anahtar zaten bekliyorsa yeniden girmez; daha
       eski, baslamamis isler iptal edilir). Sonuc gelince sonuc_al(anahtar)
       onu verir ve bildir() (ISCI is parcacigindan) cagrilir.
   sonuc_al(anahtar) -> (YoklamaSonucu, None) | None
       Hucreler HucreOzu(id, name) anlik goruntusudur (ad: GeometriDizini yolu
       ya da hucre adi); kurulum hatasi ayni istisna olarak yeniden firlatilir.
   Havuz bozulursa (isci coktu) istek False doner: cagiran esli yola duser.
================================================================================
"""

import atexit
import collections
import concurrent.futures
import multiprocessing
import threading

from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

HucreOzu = collections.namedtuple("HucreOzu", "id name")
_SINIR = 8                     # saklanan sonuc (icerik) sayisi; uygunluk_bellek ile ayni

_kilit = threading.Lock()
_havuz = []                    # [ProcessPoolExecutor] (tembel, tek)
_bekleyen = {}                 # anahtar -> Future
_sonuclar = collections.OrderedDict()


def _isci_yokla(spec, n, tohum):
    """ISCI surecinde: (YoklamaSonucu[HucreOzu], None) ya da ('hata', istisna)."""
    from cekirdek.geometri import yoklama
    try:
        sonuc, dizin = yoklama._yokla_hesapla(spec, n, tohum)
    except (KeyError, ValueError, RuntimeError) as e:
        return "hata", e
    yollar = getattr(dizin, "hucre_yolu", None) or {}

    def oz(liste):
        return tuple((tuple(float(v) for v in p),
                      tuple(HucreOzu(h.id, yollar.get(h.id) or h.name or "") for h in hucreler))
                     for p, hucreler in liste)
    return "tamam", yoklama.YoklamaSonucu(sonuc.n, oz(sonuc.bosluklar), oz(sonuc.ortusmeler))


def _havuz_al():
    if not _havuz:
        _havuz.append(concurrent.futures.ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn")))
    return _havuz[0]


def _kapat():
    for h in _havuz:
        h.shutdown(wait=False, cancel_futures=True)


atexit.register(_kapat)


def _bitti(anahtar, bildir, gelecek):
    with _kilit:
        if _bekleyen.get(anahtar) is gelecek:
            del _bekleyen[anahtar]
    if gelecek.cancelled():
        return
    try:
        sonuc = gelecek.result()
    except Exception:           # isci coktu / turetilemedi: esli yola dusulur
        _log.warning("arka plan yoklamasi basarisiz; esli yola dusulecek", exc_info=True)
        return
    with _kilit:
        _sonuclar[anahtar] = sonuc
        _sonuclar.move_to_end(anahtar)
        while len(_sonuclar) > _SINIR:
            _sonuclar.popitem(last=False)
    try:
        bildir()
    except Exception:
        _log.warning("yoklama bildirimi basarisiz", exc_info=True)


def sonuc_al(anahtar):
    """Hazir sonuc ya da None (bkz. modul notu); kurulum hatasi yeniden firlatilir."""
    with _kilit:
        kayit = _sonuclar.get(anahtar)
    if kayit is None:
        return None
    durum, deger = kayit
    if durum == "hata":
        raise deger
    return deger, None


def bekliyor_mu(anahtar):
    with _kilit:
        return anahtar in _bekleyen


def istek(anahtar, spec, n, tohum, bildir):
    """Isi kuyruga koyar (bkz. modul notu). DONER kuyrukta mi (False: havuz yok/bozuk)."""
    with _kilit:
        if anahtar in _bekleyen:
            return True
        eskiler = list(_bekleyen.values())
        try:
            gelecek = _havuz_al().submit(_isci_yokla, spec, int(n), tohum)
        except (RuntimeError, concurrent.futures.BrokenExecutor):
            _log.warning("yoklama sureci kullanilamiyor; esli yoklama", exc_info=True)
            _havuz.clear()
            return False
        _bekleyen[anahtar] = gelecek
    for eski in eskiler:            # kilit DISINDA: iptal geri cagrisi kilidi ister
        eski.cancel()               # baslamamissa iptal; basladiysa sonucu saklanir
    gelecek.add_done_callback(lambda g: _bitti(anahtar, bildir, g))
    return True


def temizle():
    """Saklanan sonuclari bosaltir (testler)."""
    with _kilit:
        _sonuclar.clear()
