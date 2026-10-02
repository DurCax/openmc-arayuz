# -*- coding: utf-8 -*-
"""
================================================================================
 cizim_sureci.py  --  Onizleme cizim ISCISI (ayri surec) ve cerceve protokolu
================================================================================

 NEDEN AYRI SUREC
   openmc.lib surec-geneli TEK bir durumdur (init/finalize global); ayni anda
   yalniz bir model yuklenebilir ve C++ tarafindaki olumcul hatalar (or. tally
   filtresi cozulemezse std::terminate) Python istisnasi olarak gelmez, sureci
   oldurur. Ana surecte bu, BUTUN arayuzun kapanmasi demekti; is parcacigi da
   ayni durumu paylasir. Iscide cokme yalniz isciyi oldurur: arayuz acik bir
   hata gosterir ve isciyi yeniden baslatir (arayuz/onizleme_istemci.py).
   Ayrica openmc.lib.TemporarySession bir istisnada comm.Abort(1) cagirir --
   eski yolda (Model.plot) cizim hatasi da sureci sonlandirabiliyordu.

 OLCUM (SFR-MET1000, bu makine, 800 px; .h2_olcum betikleri, rapor H2)
   eski Model.plot yolu (ana is parcacigi, xy + xz): 10.8 s
     -- Model.plot her cagrida Geometry.bounding_box hesaplar (SFR: 2.0 s/kesit)
   iscide: kurulum 0.25 s + openmc.lib.init 1.6 s + xy 0.43 s + xz 0.42 s
   oturum ACIK tutulur: model degismedikce (spec ozeti ayni) kesit/cozunurluk/
   renk degisikligi yalniz dilimleme maliyetidir (init tekrarlanmaz).

 KESIT MERKEZI
   Model.plot origin vermeyince sinir kutusunun merkezini (nan -> 0) kullanir;
   kurucu modelleri orijinde merkezler: 30 ornegin hepsinde bu merkez (0,0,0)
   cikti (olculdu, 0.16.0). Pahali bounding_box yerine KESIT_MERKEZI kullanilir;
   genislikler bilgi["sinir_kutu"] ve sema.model_yuksekligi'nden gelir.

 PROTOKOL (stdin -> isci, stdout -> arayuz; ikili cerceve, pickle YOK)
   cerceve = SIHIR(4) | baslik_boyu(4, big-endian) | veri_boyu(8) | baslik | veri
   baslik  = UTF-8 JSON sozluk; "_diziler": [{"ad", "dtype", "sekil"}] veri
             icindeki ham numpy dizilerini sirasiyla tanimlar (izinli dtype).
   Istekler (arayuz -> isci):
     {"tur": "ciz", "no", "spec", "kesitler": [{"eksen", "piksel"}], "cakisma"}
     {"tur": "kontrol", "no", "spec"}   -- yalniz kur + init (gizli onizleme:
                                          Calistir kapisi icin hata denetimi)
     {"tur": "cik", "no"}
   Yanitlar (isci -> arayuz), her biri istegin "no"suyla:
     {"tur": "hazir", "surum", "pid"}                         (acilista bir kez)
     {"tur": "model", "sinir_kutu", "yukseklik", "renkler", "gosterge",
      "yeniden", "sure"}
     {"tur": "kesit", "sira", "eksen", "genislik", "piksel", "cakismalar",
      "sure"} + dizi "geom" (v, h, 3) int32 = [hucre, ornek, malzeme]
     {"tur": "son", "durum": "tamam" | "hata" | "iptal", "hata", "iz", "sure"}
   IPTAL: isci her kesitten once girdiye bakar; yeni istek geldiyse isi birakir
   ("iptal") ve kuyruktaki EN SON istege gecer (aradakiler atlanir). Arayuz de
   no'su guncel olmayan her yaniti atar.
   id haritasi kodlari (OpenMC plot.cpp): -1 bosluk malzemesi, -2 hucre yok
   (tanimsiz bolge / geometri disi), -3 cakisma (yalniz cakisma denetiminde).
================================================================================
"""

import json
import os
import select
import shutil
import sys
import tempfile
import time
import traceback
from typing import NamedTuple

import numpy as np

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

PROTOKOL_SURUMU = 1
_SIHIR = b"OMZ1"
_ON_EK = 16                                # sihir + baslik boyu + veri boyu
BASLIK_SINIRI = 16 * 1024 * 1024           # en buyuk spec ~63 KB (sfr_met1000_kor)
VERI_SINIRI = 512 * 1024 * 1024            # tek kesit cercevesi: 4096^2 x 3 x int32 = 201 MB
_IZINLI_DTYPE = frozenset({"int32", "uint8", "float64"})
_OKUMA_BOYU = 1 << 20

ISTEK_CIZ, ISTEK_KONTROL, ISTEK_CIK = "ciz", "kontrol", "cik"
YANIT_HAZIR, YANIT_MODEL, YANIT_KESIT, YANIT_SON = "hazir", "model", "kesit", "son"
DURUM_TAMAM, DURUM_HATA, DURUM_IPTAL = "tamam", "hata", "iptal"

EKSENLER = ("xy", "xz", "yz")
EN_COK_KESIT = 3
PIKSEL_EN_AZ, PIKSEL_EN_COK = 16, 4096     # arayuz secenekleri 400-1400
KESIT_MERKEZI = (0.0, 0.0, 0.0)            # gerekce: modul belgesi (KESIT MERKEZI)

BOSLUK, TANIMSIZ, CAKISMA = -1, -2, -3      # id haritasi kodlari (OpenMC plot.cpp)


class ProtokolHatasi(ValueError):
    """Bozuk cerceve ya da gecersiz istek."""


class Cerceve(NamedTuple):
    baslik: dict
    diziler: dict


# ----------------------------------------------------------------------------
# cerceve
# ----------------------------------------------------------------------------

def cerceve(baslik, diziler=None):
    """baslik (JSON'a cevrilebilir sozluk) + {ad: numpy dizisi} -> bayt."""
    tanimlar, parcalar = [], []
    for ad, dizi in (diziler or {}).items():
        dizi = np.ascontiguousarray(dizi)
        if dizi.dtype.name not in _IZINLI_DTYPE:
            raise ProtokolHatasi(_("izinsiz dizi türü: %s") % dizi.dtype)
        tanimlar.append({"ad": ad, "dtype": dizi.dtype.name, "sekil": list(dizi.shape)})
        parcalar.append(dizi.tobytes())
    ham = json.dumps(dict(baslik, _diziler=tanimlar), ensure_ascii=False).encode("utf-8")
    veri = b"".join(parcalar)
    if len(ham) > BASLIK_SINIRI or len(veri) > VERI_SINIRI:
        raise ProtokolHatasi(_("çerçeve çok büyük"))
    return _SIHIR + len(ham).to_bytes(4, "big") + len(veri).to_bytes(8, "big") + ham + veri


def _dizileri_coz(tanimlar, veri):
    diziler, konum = {}, 0
    if not isinstance(tanimlar, list):
        raise ProtokolHatasi(_("dizi tanımı liste değil"))
    for t in tanimlar:
        try:
            ad, dtype, sekil = str(t["ad"]), np.dtype(t["dtype"]), tuple(int(s) for s in t["sekil"])
        except (KeyError, TypeError, ValueError) as e:
            raise ProtokolHatasi(_("bozuk dizi tanımı: %s") % e) from e
        if dtype.name not in _IZINLI_DTYPE or any(s < 0 for s in sekil):
            raise ProtokolHatasi(_("geçersiz dizi tanımı: %s") % (t,))
        boy = int(np.prod(sekil, dtype=np.int64)) * dtype.itemsize
        if konum + boy > len(veri):
            raise ProtokolHatasi(_("dizi verisi eksik"))
        diziler[ad] = np.frombuffer(veri, dtype=dtype, count=boy // dtype.itemsize,
                                    offset=konum).reshape(sekil)
        konum += boy
    if konum != len(veri):
        raise ProtokolHatasi(_("dizi verisi tanımla uyuşmuyor"))
    return diziler


class CerceveCozucu:
    """Akistan gelen baytlari biriktirip tam cerceveleri verir."""

    def __init__(self):
        self._tampon = bytearray()

    def besle(self, veri):
        """Yeni baytlar -> tamamlanan cerceveler (liste; bos olabilir)."""
        self._tampon += veri
        cikan = []
        while len(self._tampon) >= _ON_EK:
            if bytes(self._tampon[:4]) != _SIHIR:
                raise ProtokolHatasi(_("bozuk çerçeve başı"))
            bboy = int.from_bytes(self._tampon[4:8], "big")
            vboy = int.from_bytes(self._tampon[8:16], "big")
            if bboy > BASLIK_SINIRI or vboy > VERI_SINIRI:
                raise ProtokolHatasi(_("çerçeve sınırı aşıldı"))
            son = _ON_EK + bboy + vboy
            if len(self._tampon) < son:
                break
            ham = bytes(self._tampon[_ON_EK:_ON_EK + bboy])
            veri = bytes(self._tampon[_ON_EK + bboy:son])
            del self._tampon[:son]
            try:
                baslik = json.loads(ham.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ProtokolHatasi(_("çerçeve başlığı okunamadı: %s") % e) from e
            if not isinstance(baslik, dict):
                raise ProtokolHatasi(_("çerçeve başlığı sözlük değil"))
            diziler = _dizileri_coz(baslik.pop("_diziler", []), veri)
            cikan.append(Cerceve(baslik, diziler))
        return cikan


# ----------------------------------------------------------------------------
# istek dogrulamasi ve olculer
# ----------------------------------------------------------------------------

def _tamsayi_mi(deger):
    return isinstance(deger, int) and not isinstance(deger, bool)


def _kesitleri_dogrula(kesitler):
    if not isinstance(kesitler, list) or not 1 <= len(kesitler) <= EN_COK_KESIT:
        raise ProtokolHatasi(_("kesit listesi 1-%d öğe olmalı") % EN_COK_KESIT)
    for k in kesitler:
        if not isinstance(k, dict) or k.get("eksen") not in EKSENLER:
            raise ProtokolHatasi(_("geçersiz kesit: %r") % (k,))
        piksel = k.get("piksel")
        if not _tamsayi_mi(piksel) or not PIKSEL_EN_AZ <= piksel <= PIKSEL_EN_COK:
            raise ProtokolHatasi(_("piksel %d-%d arası tamsayı olmalı: %r")
                                 % (PIKSEL_EN_AZ, PIKSEL_EN_COK, piksel))


def istegi_dogrula(baslik):
    """Sinir denetimi: gecerli istegin kopyasi; aksi halde ProtokolHatasi."""
    tur = baslik.get("tur")
    if tur not in (ISTEK_CIZ, ISTEK_KONTROL, ISTEK_CIK):
        raise ProtokolHatasi(_("bilinmeyen istek: %r") % (tur,))
    if not _tamsayi_mi(baslik.get("no")):
        raise ProtokolHatasi(_("istek numarası tamsayı olmalı"))
    if tur != ISTEK_CIK and not isinstance(baslik.get("spec"), dict):
        raise ProtokolHatasi(_("istekte model (spec) yok"))
    if tur == ISTEK_CIZ:
        _kesitleri_dogrula(baslik.get("kesitler"))
        if not isinstance(baslik.get("cakisma", False), bool):
            raise ProtokolHatasi(_("cakisma mantıksal değer olmalı"))
    return dict(baslik)


def kesit_genisligi(eksen, sinir_kutu, yukseklik):
    """Kesitin (yatay, dikey) genisligi [cm]. 2B modelde (yukseklik yok)
    eksenel kesitin dikeyi en buyuk yatay olcudur (eski onizlemeyle ayni)."""
    gx, gy = (float(v) for v in sinir_kutu)
    if eksen == "xy":
        return (gx, gy)
    if eksen not in EKSENLER:
        raise ProtokolHatasi(_("bilinmeyen eksen: %r") % (eksen,))
    dikey = float(yukseklik) if yukseklik else max(gx, gy)
    return ((gx if eksen == "xz" else gy), dikey)


def cizim_modeli(model):
    """Tally'siz kabuk model: openmc.lib init tally filtrelerini cozmeye
    calisir; guc dagilimi CellFilter'i cozulemeyince C++ terminate() cagriliyordu
    (olculdu, v2). Onizlemenin yalniz geometri/malzeme/ayara ihtiyaci var."""
    import openmc
    if len(model.tallies) == 0:
        return model
    return openmc.Model(geometry=model.geometry, materials=model.materials,
                        settings=model.settings)


def _model_yuksekligi(spec):
    from cekirdek import sema
    try:
        return sema.model_yuksekligi(spec)
    except (ValueError, KeyError, TypeError):
        _log.info("model yuksekligi okunamadi", exc_info=True)
        return None


def hata_metni(e):
    """Istisna -> kullanici cumlesi (KeyError tirnaksiz)."""
    return str(e.args[0] if isinstance(e, KeyError) and e.args else e)


# ----------------------------------------------------------------------------
# openmc.lib oturumu
# ----------------------------------------------------------------------------

class Oturum:
    """Iscinin tek openmc.lib oturumu: spec ozeti degismedikce acik kalir."""

    def __init__(self):
        self.ozet = None
        self.bilgi = None
        self.yukseklik = None
        self._dizin = None
        self._eski_dizin = None

    def hazirla(self, spec):
        """Spec icin kutuphaneyi hazirlar; yeniden baslatildiysa True."""
        import openmc.lib
        from cekirdek import kurucu, onbellek
        ozet = onbellek.ozet(spec)
        if ozet == self.ozet and openmc.lib.is_initialized:
            return False
        self.kapat()
        try:
            model, bilgi = kurucu.kur(spec)
            self._dizin = tempfile.mkdtemp(prefix="openmc_arayuz_cizim_")
            self._eski_dizin = os.getcwd()
            os.chdir(self._dizin)
            cizim_modeli(model).export_to_model_xml()
            openmc.lib.init(args=["-c"], output=False)
        except Exception:
            self.kapat()
            raise
        self.ozet, self.bilgi, self.yukseklik = ozet, bilgi, _model_yuksekligi(spec)
        return True

    def ozellikler(self):
        """Model bilgisinin arayuze gidecek kismi (JSON)."""
        renkler, gosterge = {}, []
        for mat, renk in self.bilgi["renkler"].items():
            rgb = [int(v) for v in renk]
            renkler[str(mat.id)] = rgb
            gosterge.append([mat.name if mat.name != "" else str(mat.id), rgb])
        return {"sinir_kutu": [float(v) for v in self.bilgi["sinir_kutu"]],
                "yukseklik": self.yukseklik, "renkler": renkler, "gosterge": gosterge}

    def kesit(self, eksen, piksel, cakisma=False):
        """(genislik, geom (v, h, 3) int32, cakismalar [[evren, hucre1, hucre2]])."""
        import openmc.lib
        genislik = kesit_genisligi(eksen, self.bilgi["sinir_kutu"], self.yukseklik)
        geom, _ozellik = openmc.lib.slice_data(
            KESIT_MERKEZI, width=genislik, basis=eksen, pixels=(piksel, piksel),
            show_overlaps=bool(cakisma), include_properties=False)
        cakismalar = openmc.lib.slice_data_overlap_info().tolist() if cakisma else []
        return genislik, geom, cakismalar

    def kapat(self):
        """Kutuphaneyi kapatir, gecici dizini siler (tekrar cagrilabilir)."""
        import openmc.lib
        if openmc.lib.is_initialized:
            openmc.lib.finalize()
        if self._eski_dizin:
            os.chdir(self._eski_dizin)
        if self._dizin:
            shutil.rmtree(self._dizin, ignore_errors=True)
        self.ozet = self.bilgi = self.yukseklik = None
        self._dizin = self._eski_dizin = None


# ----------------------------------------------------------------------------
# kanal ve dongu
# ----------------------------------------------------------------------------

class Kanal:
    """Isci tarafi: girdi dosya tanimlayicisindan istek okur, cikisa yazar."""

    def __init__(self, giris_fd, cikis):
        self._fd = giris_fd
        self._cikis = cikis
        self._cozucu = CerceveCozucu()
        self._kuyruk = []
        self.kapandi = False

    def _oku(self, zaman_asimi):
        if self.kapandi:
            return False
        hazir, _y, _h = select.select([self._fd], [], [], zaman_asimi)
        if not hazir:
            return False
        veri = os.read(self._fd, _OKUMA_BOYU)
        if not veri:
            self.kapandi = True
            return False
        self._kuyruk.extend(self._cozucu.besle(veri))
        return True

    def _bosalt(self):
        while self._oku(0):
            pass

    def yeni_var(self):
        """Bekleyen yeni istek (ya da girdi kapandi) mi -- engellemez."""
        self._bosalt()
        return bool(self._kuyruk) or self.kapandi

    def sonraki(self):
        """Siradaki istek: kuyruktaki EN SON (cik varsa o); girdi kapandiysa None."""
        while not self._kuyruk and not self.kapandi:
            self._oku(None)
        self._bosalt()
        if not self._kuyruk:
            return None
        cik = next((c for c in self._kuyruk if c.baslik.get("tur") == ISTEK_CIK), None)
        secilen = cik or self._kuyruk[-1]
        self._kuyruk = []
        return secilen

    def gonder(self, baslik, diziler=None):
        self._cikis.write(cerceve(baslik, diziler))
        self._cikis.flush()


def _son(no, durum, t0, **ek):
    return dict({"tur": YANIT_SON, "no": no, "durum": durum,
                 "sure": time.perf_counter() - t0}, **ek)


def isle(istek, oturum, kanal):
    """Tek istegi isler; yanitlari kanala yazar. Hata yanit olur (yutulmaz)."""
    no, t0 = istek["no"], time.perf_counter()
    try:
        yeniden = oturum.hazirla(istek["spec"])
        kanal.gonder(dict(oturum.ozellikler(), tur=YANIT_MODEL, no=no, yeniden=yeniden,
                          sure=time.perf_counter() - t0))
        kesitler = (istek.get("kesitler") or []) if istek["tur"] == ISTEK_CIZ else []
        for sira, k in enumerate(kesitler):
            if kanal.yeni_var():
                kanal.gonder(_son(no, DURUM_IPTAL, t0))
                return DURUM_IPTAL
            t1 = time.perf_counter()
            genislik, geom, cakismalar = oturum.kesit(k["eksen"], k["piksel"],
                                                      istek.get("cakisma", False))
            kanal.gonder({"tur": YANIT_KESIT, "no": no, "sira": sira, "eksen": k["eksen"],
                          "genislik": list(genislik), "piksel": k["piksel"],
                          "cakismalar": cakismalar, "sure": time.perf_counter() - t1},
                         {"geom": geom})
    except Exception as e:                  # sinir: her hata arayuze yanit olarak gider
        _log.warning("onizleme istegi %s basarisiz", no, exc_info=True)
        kanal.gonder(_son(no, DURUM_HATA, t0, hata=hata_metni(e), iz=traceback.format_exc()))
        return DURUM_HATA
    kanal.gonder(_son(no, DURUM_TAMAM, t0))
    return DURUM_TAMAM


def dongu(kanal, oturum):
    """Istek dongusu: girdi kapanana ya da 'cik' gelene dek. Cikis kodu 0."""
    kanal.gonder({"tur": YANIT_HAZIR, "no": 0, "surum": PROTOKOL_SURUMU, "pid": os.getpid()})
    while True:
        gelen = kanal.sonraki()
        if gelen is None:
            return 0
        try:
            istek = istegi_dogrula(gelen.baslik)
        except ProtokolHatasi as e:
            no = gelen.baslik.get("no")
            kanal.gonder(_son(no if _tamsayi_mi(no) else -1, DURUM_HATA, time.perf_counter(),
                              hata=str(e), iz=""))
            continue
        if istek["tur"] == ISTEK_CIK:
            return 0
        isle(istek, oturum, kanal)


def ana(argv=None):
    """`python -m cekirdek.giris --alt cizim` girisi. stdout YALNIZ protokole
    ayrilir: C/C++ tarafinin yazdiklari stderr'e yonlendirilir (fd 1 -> fd 2)."""
    if argv:
        print(_("cizim alt süreci argüman almaz: %s") % " ".join(argv), file=sys.stderr)
        return 2
    cikis = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    oturum = Oturum()
    try:
        return dongu(Kanal(sys.stdin.fileno(), cikis), oturum)
    except ProtokolHatasi:
        _log.error("onizleme iscisi: bozuk istek akisi", exc_info=True)
        return 3
    except BrokenPipeError:
        _log.info("onizleme iscisi: arayuz kapandi")
        return 0
    finally:
        oturum.kapat()
