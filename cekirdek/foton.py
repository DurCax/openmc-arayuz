# -*- coding: utf-8 -*-
"""
================================================================================
 foton.py  --  Y7: foton tasinimi (gama isinmasi) ayari ve veri denetimi
================================================================================
 Ayar: spec["ayarlar"]["foton"] = {"var": bool, "elektron": "ttb" | "led"}
 (alan yoksa kapali; sema.VARSAYILAN_AYARLAR'a EKLENMEZ -- onbellek kimligi
 spec'in tamamini hashler, eski dosyalar degismeden ayni kalir).

 OPENMC 0.16 (kaynak: src/settings.cpp, docs/usersguide/settings.rst)
   settings.photon_transport   : notronlardan dogan fotonlar da tasinir
   settings.electron_treatment : 'ttb' (varsayilan; thick-target
       bremsstrahlung -- elektron/pozitron enerjisi dogdugu yerde birakilir,
       frenleme fotonlari tasinir) ya da 'led' (yerel birakim; frenleme
       fotonu uretilmez). Elektronlar hicbir kipte iz iz izlenmez.
   Foton kaynagi (kaynak.parcacik = photon) ayar kapali olsa da tasinimi
   acar (kurucu.ayarlari_kur; kapaliyken foton hicbir etkilesime girmez).

 ISINMA SKORLARININ ANLAMI (docs/methods/energy_deposition.rst)
   heating        foton KAPALI: yalniz notron KERMA'si (MT301); fisyon ve
                  yakalama gamalarinin enerjisi YOKTUR (kayip).
                  foton ACIK  : notron KERMA'si (gama haric) + fotonlarin
                  carpisma basina birakimi (carpisma tahmincisi) -- toplam.
   heating-local  yalniz notron icin; gama enerjisi carpisma yerinde
                  birakilmis sayilir (MT901). Foton acikken heating ile
                  birlikte toplamak gamayi IKI KEZ sayar.
   damage-energy  MT444 (NJOY HEATR) hasar enerjisi; yalniz notron, foton
                  kipinden bagimsiz.
   kappa-fission  geri kazanilabilir fisyon enerjisi (notrinosuz; gamalar
                  yerel); yakalama gamalarini ICERMEZ. Bu yuzden H_n+γ / κF
                  birden biraz buyuktur (yakalama gamalari) -- olculen deger
                  ders 5.16'da.

 VERI: foton tasinimi modeldeki HER element icin cross_sections.xml'de
 type="photon" kaydi ister; yoksa OpenMC koşu basinda durur.
================================================================================
"""

import re
from dataclasses import dataclass
from typing import FrozenSet, List, Optional

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ELEKTRON_YONTEMLERI = ("ttb", "led")
VARSAYILAN_ELEKTRON = "ttb"          # OpenMC src/settings.cpp: ElectronTreatment::TTB
_ELEMENT = re.compile(r"^([A-Z][a-z]?)")


@dataclass(frozen=True)
class FotonAyari:
    """Foton tasinimi istegi ve elektron islemi."""
    var: bool
    elektron: str


def ayar(spec: dict) -> FotonAyari:
    """spec["ayarlar"]["foton"] -> FotonAyari. Alan sozluk degilse kapali.
    Acikken bilinmeyen elektron islemi ValueError; kapaliyken varsayilan."""
    ham = ((spec or {}).get("ayarlar") or {}).get("foton")
    if not isinstance(ham, dict):
        return FotonAyari(False, VARSAYILAN_ELEKTRON)
    var = bool(ham.get("var"))
    elektron = ham.get("elektron") or VARSAYILAN_ELEKTRON
    if elektron not in ELEKTRON_YONTEMLERI:
        if var:
            raise ValueError(_("bilinmeyen elektron işlemi: %s (geçerli: %s)")
                             % (elektron, ", ".join(ELEKTRON_YONTEMLERI)))
        elektron = VARSAYILAN_ELEKTRON
    return FotonAyari(var, elektron)


def kaynak_foton_mu(spec: dict) -> bool:
    k = ((spec or {}).get("ayarlar") or {}).get("kaynak") or {}
    return (k.get("parcacik") or "neutron") == "photon"


def tasinim_var_mi(spec: dict) -> bool:
    """Kosuda foton tasinimi acik olacak mi (ayar ya da foton kaynagi)."""
    try:
        return ayar(spec).var or kaynak_foton_mu(spec)
    except ValueError:
        return kaynak_foton_mu(spec)


def uygula(settings: "openmc.Settings", spec: dict) -> None:
    """kurucu.ayarlari_kur kancasi: ayar acikken photon_transport ve
    electron_treatment atanir (kurulmakta olan Settings nesnesi)."""
    a = ayar(spec)
    if not a.var:
        return
    settings.photon_transport = True
    settings.electron_treatment = a.elektron


def betik_satirlari(spec: dict) -> List[str]:
    """uygula() ile ayni ayarin betik satirlari (kapaliysa bos)."""
    a = ayar(spec)
    if not a.var:
        return []
    return ["ayar.photon_transport = True      # fotonlar da taşınır (gama ısınması)",
            "ayar.electron_treatment = %r   # ttb: frenleme fotonları, led: yerel bırakım"
            % a.elektron]


# ----------------------------------------------------------------------------
# veri denetimi
# ----------------------------------------------------------------------------

def kutuphane_elementleri(yol: Optional[str] = None) -> Optional[FrozenSet[str]]:
    """cross_sections.xml'deki type="photon" element adlari; dosya yok ya da
    okunamazsa None (bilinmiyor; sicaklik.kutuphane_kayitlari loglar)."""
    from cekirdek import sicaklik
    harita = sicaklik.kutuphane_kayitlari(yol)
    if harita is None:
        return None
    return frozenset(ad for tur, ad in harita if tur == "photon")


def model_elementleri(spec: dict) -> FrozenSet[str]:
    """Malzeme bilesimlerindeki element adlari (nuklid adindan element)."""
    adlar = set()
    for m in spec.get("malzemeler") or []:
        for b in m.get("bilesim") or []:
            if float(b.get("miktar") or 0) <= 0:
                continue
            eslesme = _ELEMENT.match(str(b.get("isim") or ""))
            if eslesme:
                adlar.add(eslesme.group(1))
    return frozenset(adlar)


def eksik_elementler(spec: dict, yol: Optional[str] = None) -> Optional[List[str]]:
    """Foton verisi olmayan model elementleri (sirali); kutuphane okunamazsa None."""
    var = kutuphane_elementleri(yol)
    if var is None:
        return None
    return sorted(model_elementleri(spec) - var)
