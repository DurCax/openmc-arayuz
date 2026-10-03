# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_denetimi/ayristir.py  --  Kosu dizininden denetim girdisi
================================================================================

 Uc kaynak okunur; hicbiri openmc.Model kurmaz, nukleer veri gerektirmez:

   cikti_ozeti(dizin)   kosu.log  -> kayip parcacik, OpenMC uyarilari/hatalari
                        (+ dizindeki particle_*.h5 yeniden baslatma dosyalari)
   kosu_verisi(dizin)   statepoint -> mod, k, sigma, cevrim, entropi, k_nesil
   guc_faktorleri(sp)   statepoint -> F_dH / F_q (guc tally'si varsa)

 OPENMC CIKTI BICIMI (0.16; libopenmc.so dizgileri ve kosu loglariyla olculdu)
   warning()     " WARNING: <ileti>"   stderr; kosucu stdout'a birlestirir
   fatal_error() " ERROR: <ileti>"
   Uzun ileti 80 sutunda kaydirilir; devam satirlari TAM 10 bosluk girintilidir.
   Kayip parcacik uyarilari (GeometryState::mark_as_lost):
     "After particle N crossed surface S it could not be located in any cell
      and it did not leak."
     "Particle N could not be located after crossing a boundary of lattice L"
     "Lost particle after reflection."  /  "Lost a ray, ..."
   Esik asilinca: " ERROR: Maximum number of lost particles has been reached."
   Her kayip parcacik icin (max_write_lost_particles'a dek) kosu dizinine
   particle_<cevrim>_<kimlik>.h5 yazilir; log yoksa bu dosyalar tek kanittir.

 Bu modul kosucu.py tarafindan da ice aktarilir (M5: uyarilar kullaniciya
 gosterilir); bu yuzden modul duzeyinde kosucu'yu ICE AKTARMAZ.
================================================================================
"""

import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

LOG_ADI = "kosu.log"
_LOG_AZAMI_BAYT = 8_000_000          # dev loglarin yalniz basi okunur
_ORNEK_SAYISI = 3                    # ozet satirinda gosterilen ileti sayisi

_UYARI_BASI = re.compile(r"^\s*WARNING:\s?(.*)$")
_HATA_BASI = re.compile(r"^\s*ERROR:\s?(.*)$")
_DEVAM = re.compile(r"^ {10}\S")     # OpenMC satir kaydirma girintisi (10)
# OpenMC 0.16 kayip parcacik (mark_as_lost) iletileri -- libopenmc.so dizgilerinden
# dogrulandi (01.10.2026): "After particle {} crossed surface {} it could not be
# located in any cell...", "Particle {} could not be located after crossing a
# boundary of lattice {}", "Lost particle after reflection.", "Lost a ray, ...",
# "Particle {} left lattice {}, but it has no outer definition.", "Particle {}
# had a negative distance to a lattice boundary.", "Could not find the cell
# containing particle ...", "Couldn't find particle after hitting periodic
# boundary on surface ...".
_KAYIP = re.compile(r"could not be located|lost particle after|lost a ray"
                    r"|left lattice .*no outer definition"
                    r"|negative distance to a lattice boundary"
                    r"|could not find the cell containing particle"
                    r"|couldn't find particle after hitting periodic boundary", re.I)
_YENIDEN_BASLATMA = re.compile(r"^particle_\d+_\d+\.h5$")


@dataclass(frozen=True)
class CiktiOzeti:
    """kosu.log'un denetim icin ozeti (degismez)."""
    log_var: bool
    kayip_iletileri: Tuple[str, ...] = ()
    uyarilar: Tuple[str, ...] = ()           # kayip parcacik DISI uyarilar
    hatalar: Tuple[str, ...] = ()
    yeniden_baslatma: int = 0                # particle_*.h5 sayisi

    @property
    def kayip_parcacik(self):
        """Kayip parcacik sayisi: log iletileri ile restart dosyalarinin
        buyugu (log kesilmis ya da silinmis olabilir)."""
        return max(len(self.kayip_iletileri), self.yeniden_baslatma)


def iletileri_topla(satirlar):
    """
    OpenMC WARNING/ERROR iletilerini (kaydirilmis devam satirlariyla
    birlestirerek) toplar. DONER (uyarilar, hatalar) -- demetler.
    """
    uyarilar, hatalar = [], []
    etkin = None                    # (hedef liste, parcalar)
    for satir in satirlar:
        satir = satir.rstrip("\n")
        if etkin is not None and _DEVAM.match(satir):
            etkin[1].append(satir.strip())
            continue
        if etkin is not None:
            etkin[0].append(" ".join(" ".join(etkin[1]).split()))
            etkin = None
        for desen, hedef in ((_UYARI_BASI, uyarilar), (_HATA_BASI, hatalar)):
            m = desen.match(satir)
            if m:
                etkin = (hedef, [m.group(1).strip()])
                break
    if etkin is not None:
        etkin[0].append(" ".join(" ".join(etkin[1]).split()))
    return tuple(uyarilar), tuple(hatalar)


def _log_satirlari(yol):
    with open(yol, encoding="utf-8", errors="replace") as f:
        return f.read(_LOG_AZAMI_BAYT).splitlines()


def _yeniden_baslatma_sayisi(dizin):
    try:
        return sum(1 for ad in os.listdir(dizin) if _YENIDEN_BASLATMA.match(ad))
    except OSError:
        _log.warning("koşu dizini listelenemedi: %s", dizin, exc_info=True)
        return 0


def cikti_ozeti(kosu_dizini):
    """
    Kosu dizininin kosu.log'unu ayristirir. Log yoksa ya da okunamazsa
    log_var=False (restart dosyalari yine sayilir). DONER CiktiOzeti.
    """
    restart = _yeniden_baslatma_sayisi(kosu_dizini) if kosu_dizini else 0
    yol = os.path.join(kosu_dizini, LOG_ADI) if kosu_dizini else None
    if not yol or not os.path.exists(yol):
        return CiktiOzeti(log_var=False, yeniden_baslatma=restart)
    try:
        satirlar = _log_satirlari(yol)
    except OSError:
        _log.warning("koşu logu okunamadı: %s", yol, exc_info=True)
        return CiktiOzeti(log_var=False, yeniden_baslatma=restart)
    uyarilar, hatalar = iletileri_topla(satirlar)
    kayip = tuple(u for u in uyarilar if _KAYIP.search(u))
    diger = tuple(u for u in uyarilar if not _KAYIP.search(u))
    return CiktiOzeti(log_var=True, kayip_iletileri=kayip, uyarilar=diger,
                      hatalar=hatalar, yeniden_baslatma=restart)


_OLASILIK_TABLOSU_IZI = "probability table"


def ozet_satirlari(ozet):
    """Kullaniciya gosterilecek kisa satirlar (terminal ve Calistir sekmesi).
    Sorun yoksa bos liste."""
    if ozet is None:
        return []
    satirlar = []
    if ozet.kayip_parcacik:
        satirlar.append(_("KAYIP PARÇACIK: %d — geometride boşluk ya da çakışma "
                          "olabilir; sonuçlara güvenmeden önce geometriyi "
                          "denetleyin.") % ozet.kayip_parcacik)
        satirlar += ["  " + m for m in ozet.kayip_iletileri[:_ORNEK_SAYISI]]
    for m in ozet.hatalar[:_ORNEK_SAYISI]:
        satirlar.append(_("OpenMC hatası: %s") % m)
    if ozet.uyarilar:
        satirlar.append(_("OpenMC %d uyarı yazdı (ilk %d):")
                        % (len(ozet.uyarilar), min(len(ozet.uyarilar), _ORNEK_SAYISI)))
        satirlar += ["  " + m for m in ozet.uyarilar[:_ORNEK_SAYISI]]
        if any(_OLASILIK_TABLOSU_IZI in m.lower() for m in ozet.uyarilar):
            satirlar.append(_("  Not: \"probability table\" uyarısı, nüklid verisindeki "
                              "rezonans-ötesi (URR) olasılık tablosunda negatif değer "
                              "bulunduğunu söyler; model hatası değildir. Sonuçtan "
                              "şüphe ediyorsanız başka bir kütüphane sürümüyle "
                              "karşılaştırın (Kılavuz: Sorun giderme)."))
    return satirlar


# ============================================================================
# STATEPOINT
# ============================================================================

@dataclass(frozen=True)
class KosuVerisi:
    """Statepoint'in denetim icin gereken alanlari (degismez)."""
    statepoint: str
    mod: str                                 # "eigenvalue" | "fixed source"
    keff: Optional[float]
    sigma: Optional[float]
    parcacik: int
    cevrim: int
    pasif: int
    entropi: Tuple[float, ...] = ()          # bos: entropi kapali
    k_nesil: Tuple[float, ...] = ()          # NESIL basina (cevrim x nesil_basina)
    openmc_surum: str = ""
    nesil_basina: int = 1                    # settings.generations_per_batch

    @property
    def ozdeger(self):
        return self.mod == "eigenvalue"

    @property
    def aktif(self):
        return self.cevrim - self.pasif


def kosu_verisi(kosu_dizini):
    """
    Dizindeki son statepoint'i okur (summary.h5 BAGLANMAZ: hizli).
    DONER (KosuVerisi | None, hata metni | None). Statepoint yoksa (None, None).
    """
    from cekirdek import kosucu
    yol = kosucu.son_statepoint(kosu_dizini) if kosu_dizini else None
    if not yol:
        return None, None
    try:
        import openmc
        with openmc.StatePoint(yol, autolink=False) as sp:
            ozdeger = sp.run_mode == "eigenvalue"
            entropi = tuple(float(x) for x in sp.entropy) if (
                ozdeger and sp.entropy is not None) else ()
            veri = KosuVerisi(
                statepoint=yol, mod=str(sp.run_mode),
                keff=float(sp.keff.nominal_value) if ozdeger else None,
                sigma=float(sp.keff.std_dev) if ozdeger else None,
                parcacik=int(sp.n_particles), cevrim=int(sp.n_batches),
                pasif=int(sp.n_inactive) if ozdeger else 0, entropi=entropi,
                k_nesil=tuple(float(x) for x in sp.k_generation) if ozdeger else (),
                openmc_surum=".".join(str(int(x)) for x in sp.version),
                nesil_basina=int(getattr(sp, "generations_per_batch", 1) or 1))
        return veri, None
    except Exception as e:
        _log.warning("statepoint okunamadı: %s", yol, exc_info=True)
        return None, "%s: %s" % (os.path.basename(yol), e)


def guc_faktorleri(statepoint_yolu):
    """
    Statepoint'teki guc tally'sinden F_dH / F_q (guc.tepe_faktorleri).
    DONER (faktorler | None, hata metni | None); guc tally'si yoksa (None, None).
    """
    try:
        import openmc
        from cekirdek import guc
        with openmc.StatePoint(statepoint_yolu) as sp:
            dagilim = guc.dagilim_oku(sp)
        if not dagilim:
            return None, None
        return guc.tepe_faktorleri(dagilim), None
    except Exception as e:
        _log.warning("güç tepe faktörleri okunamadı: %s", statepoint_yolu, exc_info=True)
        return None, str(e)
