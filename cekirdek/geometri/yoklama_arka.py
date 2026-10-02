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
   kurulan bir model (kosu, XML disa aktarma) cakisan kimlikler alirdi.

 SUREC
   Depodaki alt surec deseni (cekirdek/giris.py ALT SURECLER):
   `python -P -m cekirdek.giris --alt yoklama`, sabit calisma dizini (paket
   koku), PYTHONPATH = alt_surec_pythonpath, dil OPENMC_ARAYUZ_DIL ile. Arayuz
   yigini (PySide6) iscide YUKLENMEZ. Protokol satir basina bir JSON:
     istek  {"no", "spec", "n", "tohum"}
     yanit  {"no", "durum": "tamam", "n", "bosluklar", "ortusmeler"}
            {"no", "durum": "hata", "tur": KeyError|ValueError|RuntimeError, "argumanlar"}
   bosluk/ortusme: [[x, y, z], [[hucre kimligi, yol ya da ad], ...]]. Okunur
   metin (_metinler) ANA surecte, etkin dilde uretilir; yol parcasi iscide
   ayni dille (ortam) uretilir, anahtar dili icerir.

 KUYRUK
   Tek kosan + tek bekleyen (en yeni): yeni istek bekleyeni DEGISTIRIR, kosani
   kesmez. Kosan bitince bekleyen gonderilir.

 BASARISIZLIK
   Isci coker, baslatilamaz ya da ZAMAN_ASIMI asilirsa o anahtar "coktu" olarak
   isaretlenir ve bildir() cagrilir; yoklama.yokla bu isarette esli yola duser
   (sonsuz yeniden istek yok). Isci bir sonraki istekte yeniden baslatilir.
   kapat(): isciyi sonlandirir (pencere kapanisi, aboutToQuit, atexit).
================================================================================
"""

import atexit
import collections
import json
import os
import subprocess
import sys
import threading

from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

HucreOzu = collections.namedtuple("HucreOzu", "id name")
COKTU = "coktu"
# Bir istegin en uzun suresi (s). Olculen: SFR-MET1000 kurulum 0.4 s + 600 nokta
# 0.3 s; ilk istekte isci acilisi (python + numpy + openmc) ~2-3 s. 60 s, yuklu
# ya da yavas makinede ~20x pay birakir; asilirsa isci olu sayilir.
ZAMAN_ASIMI = 60.0
_SINIR = 8                     # saklanan sonuc sayisi (uygunluk_bellek.VARSAYILAN_SINIR)
_ISTISNALAR = {"KeyError": KeyError, "ValueError": ValueError, "RuntimeError": RuntimeError}


# ============================================================================
# isci tarafi
# ============================================================================

def _isci_yanit(istek):
    from cekirdek.geometri import yoklama
    try:
        sonuc, dizin = yoklama._yokla_hesapla(istek["spec"], int(istek["n"]), istek["tohum"])
    except tuple(_ISTISNALAR.values()) as e:
        return {"durum": "hata", "tur": type(e).__name__, "argumanlar": [str(a) for a in e.args]}
    yollar = getattr(dizin, "hucre_yolu", None) or {}

    def liste(x):
        return [[[float(v) for v in p], [[h.id, yollar.get(h.id) or h.name or ""]
                                          for h in hucreler]] for p, hucreler in x]
    return {"durum": "tamam", "n": sonuc.n, "bosluklar": liste(sonuc.bosluklar),
            "ortusmeler": liste(sonuc.ortusmeler)}


def ana(argv=None, girdi=None, cikti=None):
    """`--alt yoklama` isci dongusu: stdin'den istek satiri, stdout'a yanit satiri."""
    girdi, cikti = girdi or sys.stdin, cikti or sys.stdout
    for satir in girdi:
        if not satir.strip():
            continue
        istek = json.loads(satir)
        yanit = dict(_isci_yanit(istek), no=istek.get("no"))
        cikti.write(json.dumps(yanit) + "\n")
        cikti.flush()
    return 0


# ============================================================================
# arayuz tarafi
# ============================================================================

class _Yonetici(object):
    """Tek isci sureci, tek kosan + tek bekleyen istek, sonuc bellegi."""

    def __init__(self):
        self.kilit = threading.Lock()
        self.surec = None
        self.kosan = None          # (no, anahtar, bildir, zamanlayici)
        self.bekleyen = None       # (anahtar, istek, bildir)
        from cekirdek.uygunluk_bellek import Bellek
        self.sonuclar = Bellek("yoklama_arka", sinir=_SINIR)   # uygunluk_bellek.temizle bosaltir
        self.no = 0

    # -- surec ----------------------------------------------------------------
    def _baslat(self):
        from cekirdek import ceviri, giris, yollar
        program, arg = giris.alt_surec_komutu(giris.ALT_YOKLAMA, [], python=sys.executable)
        ortam = isci_ortami(dict(os.environ), ceviri.etkin_dil())
        surec = subprocess.Popen([program] + arg, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, cwd=yollar.paket_koku(), env=ortam,
                                 text=True, encoding="utf-8")
        threading.Thread(target=self._oku, args=(surec,), daemon=True,
                         name="yoklama-okuyucu").start()
        self.surec = surec

    def _oku(self, surec):
        for satir in surec.stdout:
            try:
                yanit = json.loads(satir)
            except ValueError:
                _log.warning("yoklama iscisi bozuk satir: %r", satir[:200])
                continue
            self._yanit(surec, yanit)
        self._coktu(surec, "isci sureci sonlandi")

    # -- durum gecisleri (kilit icinde karar, kilit disinda bildir) ----------
    def _yanit(self, surec, yanit):
        with self.kilit:
            if self.kosan is None or surec is not self.surec or yanit.get("no") != self.kosan[0]:
                return
            _no, anahtar, bildir, zamanlayici = self.kosan
            zamanlayici.cancel()
            self._sakla(anahtar, yanit)
            self.kosan = None
            gonderilemeyen = self._siradakini_gonder()
        _bildir(bildir)
        _bildir(gonderilemeyen)

    def _coktu(self, surec, neden):
        with self.kilit:
            if surec is not self.surec:
                return
            self.surec = None
            kosan, self.kosan = self.kosan, None
            if kosan is None:
                return
            kosan[3].cancel()
            _log.warning("arka plan yoklamasi basarisiz (%s); esli yola dusulecek", neden)
            self._sakla(kosan[1], {"durum": COKTU})
            gonderilemeyen = self._siradakini_gonder()
        _bildir(kosan[2])
        _bildir(gonderilemeyen)

    def _zaman_asimi(self, surec, no):
        with self.kilit:
            if self.kosan is None or self.kosan[0] != no or surec is not self.surec:
                return
        _log.warning("arka plan yoklamasi %.0f s'de bitmedi; isci sonlandiriliyor", ZAMAN_ASIMI)
        surec.kill()               # okuyucu EOF gorur -> _coktu

    def _sakla(self, anahtar, yanit):
        self.sonuclar.unut(anahtar)
        self.sonuclar.al(anahtar, lambda: yanit)

    def bul(self, anahtar):
        try:
            return self.sonuclar.al(anahtar, _yok)
        except _Yok:
            return None

    def _siradakini_gonder(self):
        """Kilit ICINDE cagrilir. Bekleyen gonderilemezse 'coktu' isaretlenir ve
        onun bildir'i DONER (cagiran kilit disinda cagirir); aksi halde None."""
        if self.kosan is not None or self.bekleyen is None:
            return None
        anahtar, istek, bildir = self.bekleyen
        self.bekleyen = None
        try:
            if self.surec is None or self.surec.poll() is not None:
                self._baslat()
            self.no += 1
            self.surec.stdin.write(json.dumps(dict(istek, no=self.no)) + "\n")
            self.surec.stdin.flush()
        except (OSError, ValueError) as e:
            _log.warning("yoklama iscisi kullanilamiyor (%s); esli yoklama", e)
            self.surec = None
            self._sakla(anahtar, {"durum": COKTU})
            return bildir
        zamanlayici = threading.Timer(ZAMAN_ASIMI, self._zaman_asimi, (self.surec, self.no))
        zamanlayici.daemon = True
        zamanlayici.start()
        self.kosan = (self.no, anahtar, bildir, zamanlayici)
        return None

    # -- disa acik ------------------------------------------------------------
    def istek(self, anahtar, spec, n, tohum, bildir):
        with self.kilit:
            if (self.kosan and self.kosan[1] == anahtar) or \
                    (self.bekleyen and self.bekleyen[0] == anahtar):
                return True
            self.bekleyen = (anahtar, {"spec": spec, "n": int(n), "tohum": tohum}, bildir)
            return self._siradakini_gonder() is None

    def kapat(self):
        with self.kilit:
            surec, self.surec = self.surec, None
            kosan, self.kosan, self.bekleyen = self.kosan, None, None
        if kosan is not None:
            kosan[3].cancel()
        if surec is not None and surec.poll() is None:
            surec.terminate()
            try:
                surec.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                surec.kill()


class _Yok(Exception):
    """Bellekte kayit yok (Bellek.al yoklamasi)."""


def _yok():
    raise _Yok()


def _bildir(bildir):
    if bildir is None:
        return
    try:
        bildir()
    except Exception:          # bildirim (arayuz) hatasi isciyi/okuyucuyu durdurmasin
        _log.warning("yoklama bildirimi basarisiz", exc_info=True)


def isci_ortami(ortam: dict, dil: str) -> dict:
    """Iscinin ortami: PYTHONPATH (kaynak agaci) ve etkin dil (OPENMC_ARAYUZ_DIL)."""
    from cekirdek import ceviri, giris
    yeni = dict(ortam)
    yol = giris.alt_surec_pythonpath(yeni.get("PYTHONPATH"))
    if yol:
        yeni["PYTHONPATH"] = yol
    yeni[ceviri.ORTAM_DEGISKENI] = dil
    return yeni


_YONETICI = _Yonetici()


def anahtar_dilli(anahtar: str) -> str:
    """Sonuc anahtari: icerik + etkin dil (yol parcalari iscide o dille uretilir)."""
    from cekirdek import ceviri
    return "%s:%s" % (anahtar, ceviri.etkin_dil())


def sonuc_al(anahtar: str):
    """(YoklamaSonucu[HucreOzu], None) | COKTU | None. Kurulum hatasi her cagrida
    YENI bir istisna nesnesi olarak firlatilir (esli yoldakiyle ayni tur ve metin)."""
    yanit = _YONETICI.bul(anahtar)
    if yanit is None:
        return None
    if yanit["durum"] == COKTU:
        return COKTU
    if yanit["durum"] == "hata":
        raise _ISTISNALAR[yanit["tur"]](*yanit["argumanlar"])
    from cekirdek.geometri import yoklama

    def demet(liste):
        return tuple((tuple(p), tuple(HucreOzu(i, ad) for i, ad in hucreler))
                     for p, hucreler in liste)
    return yoklama.YoklamaSonucu(yanit["n"], demet(yanit["bosluklar"]),
                                 demet(yanit["ortusmeler"])), None


def istek(anahtar: str, spec: dict, n: int, tohum: int, bildir) -> bool:
    """Isi kuyruga koyar (bkz. KUYRUK). DONER kuyrukta mi (False: isci yok; esli yol)."""
    return _YONETICI.istek(anahtar, spec, n, tohum, bildir)


def kapat() -> None:
    """Isciyi sonlandirir; bekleyen/kosan istek birakilir."""
    _YONETICI.kapat()


def temizle() -> None:
    """Saklanan sonuclari bosaltir (testler; uygunluk_bellek.temizle de cagirir)."""
    _YONETICI.sonuclar.temizle()


atexit.register(kapat)
