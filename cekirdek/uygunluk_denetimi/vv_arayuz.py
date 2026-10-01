# -*- coding: utf-8 -*-
"""
uygunluk_denetimi/vv_arayuz.py -- Profil B'nin S-3 (cekirdek/vv/) ile SOZLESMESI.

S-1 yanlilik/USL HESAPLAMAZ; S-3 NUREG/CR-6698 yontemiyle (STANDARTLAR.md §4)
bir VVOzeti uretir, denetci onu kurallarla (K6, K6-AOA, K8-K14) denetler.
VVOzeti yoksa K6 "USL hesaplanamadi" der -- sahte guven uretilmez.

ALANLAR
  n                  kumedeki kriter vakasi sayisi
  yontem             "tolerans_siniri" (eş. 20-22) | "tolerans_bandi" (eş. 23-30)
                     | "parametrik_olmayan" (eş. 31-34)
  usl                ust alt-kritik sinir; None = hesaplanamadi
  usl_neden          usl None ise neden (kullaniciya gosterilir)
  bias               k̄ - 1 (ham, isaretli)
  bias_kullanilan    USL'de kullanilan yanlilik (pozitif OLMAMALI, K8)
  delta_sm, delta_aoa  alt-kritik pay ve AOA payi (Δk)
  guven              parametrik olmayan yontemde β (0-1); digerlerinde None
  normallestirildi   k_calc / k_exp uygulandi mi (eş. 9, K9)
  normallik          {"test": ad, "p": deger, "normal": bool} | None (K13)
  egilim             {parametre: {"egim": b, "anlamli": bool}} (K13)
  aralik             {parametre: (min, max)} sayisal AOA araligi (K12)
  aoa_kategorik      {"bolunebilir"|"fiziksel_bicim"|"yansitici"|"tayf": (degerler)}
  seriler            {deney serisi: vaka sayisi} (K14)
  kaynak             kume ve yontem atfi (ör. "NUREG/CR-6698; mit-crpg")
  alt_kume           USL'nin hesaplandigi alt kumenin betimi (ör. "U-235, metal,
                     hızlı, HEU (%60–100)"); bos = tum kume (K6 metnine yazilir)
"""

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from cekirdek.ceviri import _

YONTEMLER = ("tolerans_siniri", "tolerans_bandi", "parametrik_olmayan")
AOA_KATEGORILERI = ("bolunebilir", "fiziksel_bicim", "yansitici", "tayf")


@dataclass(frozen=True)
class VVOzeti:
    n: int
    yontem: str
    usl: Optional[float]
    usl_neden: str = ""
    bias: float = 0.0
    bias_kullanilan: float = 0.0
    delta_sm: float = 0.05
    delta_aoa: float = 0.0
    guven: Optional[float] = None
    normallestirildi: bool = True
    normallik: Optional[Mapping] = None
    egilim: Mapping = field(default_factory=dict)
    aralik: Mapping[str, Tuple[float, float]] = field(default_factory=dict)
    aoa_kategorik: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    seriler: Mapping[str, int] = field(default_factory=dict)
    kaynak: str = ""
    alt_kume: str = ""

    def __post_init__(self):
        if self.yontem not in YONTEMLER:
            raise ValueError(_("bilinmeyen V&V yöntemi: %r (geçerli: %s)")
                             % (self.yontem, ", ".join(YONTEMLER)))
