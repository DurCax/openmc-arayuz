# -*- coding: utf-8 -*-
"""
================================================================================
 parametre.py  --  Parametrik model: adlandirilmis degiskenler + tarama (Y10)
================================================================================

 Bir taban spec, ona uygulanacak ADLI degiskenler ve (istege bagli) bu
 degiskenlerin tarama degerleri. Fizik uygulamasi tarama.parametre_uygula'dir
 (Doppler, yogunluk korelasyonu, bor, zenginlik, grup... AYNI kod); burada
 yalniz birden cok degiskeni bir arada tasimak, nokta listesi uretmek, JSON
 gidis-donusu ve kosu kuyruguna eklemek vardir.

   Degisken(ad, tur, hedef=None, deger=None, birim="")
     ad    : Python tanimlayicisi (zen, T_yakit ...)
     tur   : tarama.TURLER anahtari ya da YOL_TURU ("yol")
     hedef : tura gore malzeme / demet / (cubuk, bolge) / grup adi;
             YOL_TURU icin spec'te noktali yol ("ayarlar.parcacik",
             "ayarlar.entropi_mesh.boyut.0")
     deger : taramada olmayan noktalarda uygulanacak deger; None ise taban
             spec'teki deger korunur
   Tarama(degerler={ad: (d1, d2, ...)}, bicim="kartezyen" | "esli")
     kartezyen: butun bilesimler (ilk degisken en dista); esli: zip (esit boy)
   ParametrikModel(ad, taban, degiskenler, tarama=None)

   uygula(model, {ad: deger}) -> (spec, notlar)      taban DEGISMEZ
   noktalar(model) -> [{ad: deger}, ...]
   sozluge / sozlukten / kaydet (atomik) / yukle      JSON (BICIM_ADI, BICIM_SURUMU)
   kuyruga_ekle(model, kuyruk, kok_dizin, ...) -> [kimlik]
     her nokta kok_dizin/nokta_NNN'de; IsDurumu.etiket = {"parametrik",
     "sira", "degerler", "notlar"}
   yol_uygula(spec, yol, deger) -> yeni spec          (YOL_TURU; yalniz sayisal alan)

 Mevcut tarama ile birlesme: tarama.parametre_uygula YOL_TURU'nu taniyip buraya
 devreder; tarama.parametrik_model(spec, tur, hedef, degerler) tek degiskenli
 bir taramayi ParametrikModel'e cevirir (kaydedilebilir, kuyrukla kosulabilir).
================================================================================
"""

from __future__ import annotations

import copy
import itertools
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

YOL_TURU = "yol"
BICIM_ADI = "openmc-arayuz-parametrik"
BICIM_SURUMU = 1
TARAMA_BICIMLERI = ("kartezyen", "esli")
_AD_DESENI = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _gecerli_turler() -> Tuple[str, ...]:
    from cekirdek import tarama
    return tuple(tarama.TURLER) + (YOL_TURU,)


def _sayi(deger: Any) -> float | int:
    if isinstance(deger, bool) or not isinstance(deger, (int, float)):
        raise ValueError(_("sayısal değer bekleniyordu: %r") % (deger,))
    return deger


def _hedef_normal(hedef: Any) -> Any:
    # JSON'dan gelen liste (cubuk_yaricap: [ad, bolge]) tarama'nin bekledigi demete
    return tuple(hedef) if isinstance(hedef, list) else hedef


@dataclass(frozen=True)
class Degisken:
    ad: str
    tur: str
    hedef: Any = None
    deger: Optional[float] = None
    birim: str = ""

    def __post_init__(self) -> None:
        if not _AD_DESENI.fullmatch(str(self.ad or "")):
            raise ValueError(_("değişken adı bir tanımlayıcı olmalı (harf/_ ile başlar): %r")
                             % (self.ad,))
        if self.tur not in _gecerli_turler():
            raise ValueError(_("bilinmeyen değişken türü: %s") % self.tur)
        if self.tur == YOL_TURU and not str(self.hedef or "").strip():
            raise ValueError(_("'%s' değişkeninin spec yolu boş") % self.ad)
        if self.deger is not None:
            _sayi(self.deger)
        object.__setattr__(self, "hedef", _hedef_normal(self.hedef))


@dataclass(frozen=True)
class Tarama:
    degerler: Mapping[str, Tuple[float, ...]] = field(default_factory=dict)
    bicim: str = "kartezyen"

    def __post_init__(self) -> None:
        if self.bicim not in TARAMA_BICIMLERI:
            raise ValueError(_("tarama biçimi %s olmalı: %s")
                             % (" / ".join(TARAMA_BICIMLERI), self.bicim))
        normal = {str(a): tuple(_sayi(d) for d in v) for a, v in dict(self.degerler).items()}
        if any(not v for v in normal.values()):
            raise ValueError(_("taranan her değişkenin en az bir değeri olmalı"))
        if self.bicim == "esli" and len({len(v) for v in normal.values()}) > 1:
            raise ValueError(_("eşli taramada bütün değer listeleri aynı uzunlukta olmalı"))
        object.__setattr__(self, "degerler", normal)


@dataclass(frozen=True)
class ParametrikModel:
    ad: str
    taban: Mapping[str, Any]
    degiskenler: Tuple[Degisken, ...] = ()
    tarama: Optional[Tarama] = None

    def __post_init__(self) -> None:
        adlar = [d.ad for d in self.degiskenler]
        if len(set(adlar)) != len(adlar):
            raise ValueError(_("değişken adları benzersiz olmalı: %s") % ", ".join(adlar))
        if self.tarama is not None:
            eksik = [a for a in self.tarama.degerler if a not in adlar]
            if eksik:
                raise ValueError(_("taramada tanımsız değişken: %s") % ", ".join(eksik))
        object.__setattr__(self, "degiskenler", tuple(self.degiskenler))
        object.__setattr__(self, "taban", copy.deepcopy(dict(self.taban)))


# ============================================================================
# UYGULAMA
# ============================================================================

def _yol_parcalari(yol: str) -> List[str]:
    parcalar = [p for p in str(yol or "").split(".")]
    if not parcalar or any(not p for p in parcalar):
        raise ValueError(_("geçersiz spec yolu: %r") % (yol,))
    return parcalar


def _adim(kap: Any, parca: str, yol: str) -> Tuple[Any, Any]:
    """(kap, anahtar): kap[anahtar] var olmali."""
    if isinstance(kap, list):
        if not parca.isdigit() or int(parca) >= len(kap):
            raise KeyError(_("spec yolunda liste öğesi yok: %s") % yol)
        return kap, int(parca)
    if isinstance(kap, dict) and parca in kap:
        return kap, parca
    raise KeyError(_("spec yolunda alan yok: %s") % yol)


def yol_uygula(spec: Mapping[str, Any], yol: str, deger: float) -> Dict[str, Any]:
    """spec'in kopyasinda noktali yoldaki SAYISAL alani degistirir."""
    yeni = copy.deepcopy(dict(spec))
    kap: Any = yeni
    parcalar = _yol_parcalari(yol)
    for parca in parcalar[:-1]:
        kap, anahtar = _adim(kap, parca, yol)
        kap = kap[anahtar]
    kap, anahtar = _adim(kap, parcalar[-1], yol)
    eski = kap[anahtar]
    if isinstance(eski, bool) or not isinstance(eski, (int, float)):
        raise ValueError(_("'%s' sayısal bir alan değil") % yol)
    deger = _sayi(deger)
    tam = isinstance(eski, int) and float(deger).is_integer()
    kap[anahtar] = int(deger) if tam else float(deger)
    return yeni


def uygula(model: ParametrikModel, degerler: Mapping[str, float]
           ) -> Tuple[Dict[str, Any], List[str]]:
    """Degiskenleri sirayla taban spec'in kopyasina uygular. DONER (spec, notlar)."""
    from cekirdek import tarama
    bilinmeyen = [a for a in degerler if a not in {d.ad for d in model.degiskenler}]
    if bilinmeyen:
        raise ValueError(_("tanımsız değişken: %s") % ", ".join(bilinmeyen))
    spec: Dict[str, Any] = copy.deepcopy(dict(model.taban))
    notlar: List[str] = []
    for d in model.degiskenler:
        deger = degerler.get(d.ad, d.deger)
        if deger is None:
            continue
        spec, notu = tarama.parametre_uygula(spec, d.tur, d.hedef, deger, taban=model.taban)
        if notu and notu not in notlar:
            notlar.append(notu)
    return spec, notlar


def noktalar(model: ParametrikModel) -> List[Dict[str, float]]:
    """Taramanin noktalari (tarama yoksa tek bos nokta: taban + varsayilanlar)."""
    if model.tarama is None or not model.tarama.degerler:
        return [{}]
    adlar = list(model.tarama.degerler)
    listeler = [model.tarama.degerler[a] for a in adlar]
    if model.tarama.bicim == "esli":
        bilesimler = zip(*listeler)
    else:
        bilesimler = itertools.product(*listeler)
    return [dict(zip(adlar, b)) for b in bilesimler]


# ============================================================================
# JSON
# ============================================================================

def _degisken_sozlugu(d: Degisken) -> Dict[str, Any]:
    return {"ad": d.ad, "tur": d.tur,
            "hedef": list(d.hedef) if isinstance(d.hedef, tuple) else d.hedef,
            "deger": d.deger, "birim": d.birim}


def sozluge(model: ParametrikModel) -> Dict[str, Any]:
    tarama = None
    if model.tarama is not None:
        tarama = {"bicim": model.tarama.bicim,
                  "degerler": {a: list(v) for a, v in model.tarama.degerler.items()}}
    return {"bicim": BICIM_ADI, "surum": BICIM_SURUMU, "ad": model.ad,
            "degiskenler": [_degisken_sozlugu(d) for d in model.degiskenler],
            "tarama": tarama, "taban": copy.deepcopy(dict(model.taban))}


def sozlukten(veri: Mapping[str, Any]) -> ParametrikModel:
    if veri.get("bicim") != BICIM_ADI:
        raise ValueError(_("parametrik model dosyası değil (bicim = %r)") % (veri.get("bicim"),))
    if int(veri.get("surum") or 0) > BICIM_SURUMU:
        raise ValueError(_("parametrik model daha yeni bir sürümle yazılmış (%s)")
                         % veri.get("surum"))
    if not isinstance(veri.get("taban"), Mapping):
        raise ValueError(_("parametrik modelde taban spec yok"))
    degiskenler = tuple(Degisken(**{a: d.get(a) for a in ("ad", "tur", "hedef", "deger")},
                                 birim=d.get("birim") or "")
                        for d in veri.get("degiskenler") or ())
    t = veri.get("tarama")
    tarama = Tarama(degerler=t.get("degerler") or {}, bicim=t.get("bicim") or "kartezyen") \
        if t else None
    return ParametrikModel(ad=str(veri.get("ad") or ""), taban=veri["taban"],
                           degiskenler=degiskenler, tarama=tarama)


def kaydet(model: ParametrikModel, yol: str) -> str:
    """JSON'u ATOMIK yazar (ayni dizinde gecici dosya + os.replace). DONER yol."""
    yol = os.path.abspath(yol)
    dizin = os.path.dirname(yol)
    os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".parametrik_", suffix=".tmp", dir=dizin)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(sozluge(model), f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    except BaseException:
        _log.warning("parametrik model yazilamadi: %s", yol, exc_info=True)
        if os.path.exists(gecici):
            os.remove(gecici)
        raise
    return yol


def yukle(yol: str) -> ParametrikModel:
    with open(yol, encoding="utf-8") as f:
        return sozlukten(json.load(f))


# ============================================================================
# KUYRUK
# ============================================================================

def _nokta_adi(model: ParametrikModel, nokta: Mapping[str, float]) -> str:
    if not nokta:
        return model.ad or _("taban")
    return "%s [%s]" % (model.ad, ", ".join("%s=%g" % kv for kv in nokta.items()))


def kuyruga_ekle(model: ParametrikModel, kuyruk: Any, kok_dizin: str, is_parcacigi: int = 1,
                 mpi_surec: int = 0, dogrulama: bool = True, veri_kontrolu: bool = True,
                 sonuc_kancasi: Any = None) -> List[str]:
    """Her noktayi ayri dizinde kuyruga ekler. DONER kimlikler (nokta sirasiyla).
    Bir nokta uygulanamazsa (ValueError/KeyError) HICBIR nokta eklenmez."""
    from cekirdek import kuyruk as _kuyruk
    hazir: List[Tuple[Dict[str, float], Dict[str, Any], List[str]]] = []
    for nokta in noktalar(model):
        spec, notlar = uygula(model, nokta)
        hazir.append((nokta, spec, notlar))
    kimlikler: List[str] = []
    for i, (nokta, spec, notlar) in enumerate(hazir):
        kimlikler.append(kuyruk.ekle(_kuyruk.KosuIsi(
            ad=_nokta_adi(model, nokta), spec=spec,
            dizin=os.path.join(kok_dizin, "nokta_%03d" % i),
            is_parcacigi=is_parcacigi, mpi_surec=mpi_surec, dogrulama=dogrulama,
            veri_kontrolu=veri_kontrolu, sonuc_kancasi=sonuc_kancasi,
            etiket={"parametrik": model.ad, "sira": i, "degerler": dict(nokta),
                    "notlar": list(notlar)})))
    return kimlikler


def tek_degiskenli(spec: Mapping[str, Any], tur: str, hedef: Any,
                   degerler: Sequence[float], ad: Optional[str] = None) -> ParametrikModel:
    """Tek degiskenli tarama -> ParametrikModel (tarama.parametrik_model kullanir)."""
    degisken = Degisken(ad=tur if _AD_DESENI.fullmatch(tur) else "x", tur=tur, hedef=hedef)
    return ParametrikModel(ad=ad or tur, taban=spec, degiskenler=(degisken,),
                           tarama=Tarama(degerler={degisken.ad: tuple(degerler)}))
