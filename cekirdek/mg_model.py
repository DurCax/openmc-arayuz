# -*- coding: utf-8 -*-
"""
================================================================================
 mg_model.py  --  CE modeli -> cok gruplu (MG) model (v3 Y8)
================================================================================

 MGXS koşusunun spec'inden (kimlikler ayni olsun diye AYNI spec) model
 yeniden kurulur; her bolge mgxs.h5'teki xsdata'ya bagli makroskopik
 malzemeyle degistirilir (openmc.Model.convert_to_multigroup ile ayni yol:
 set_density('macro', 1) + add_macroscopic):

   malzeme : her malzeme kendi xsdata'si
   hucre   : her malzemeli hucreye kendi xsdata'siyla YENI malzeme
   demet   : butun malzemeler tek (homojen) xsdata -> ayni sinirlar icinde
             sonsuz homojen ortam; k = sabitlerin GxG ozdegeri (mgxs_k)

 Tally'ler kaldirilir (nuklid/skor kumeleri MG makroskopik modda anlamsiz
 ya da desteksiz); ayarlar yalniz koşu buyuklukleri, kaynak ve entropi
 mesh'i ile yeniden kurulur (sicaklik/foton/olasilik tablosu CE'ye ozgu).
 Sicakliklar silinir: kutuphane tek sicaklikta (mgxs_uret.ROOM_K).
================================================================================
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Mapping

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

if TYPE_CHECKING:                     # yalniz tur aciklamalari (openmc tembel yuklenir)
    import openmc
    import openmc.mgxs  # noqa: F401

_log = kaydedici(__name__)

# Bu modul ve random_ray.rr_modeli OpenMC'nin IC ayrintilarina dayanir
# (Material._nuclides/_sab, Settings._entropy_mesh); 0.16.0'da dogrulandi:
# openmc/model/model.py Model.convert_to_multigroup, satir 2881-2887 ("Convert
# all continuous energy materials to multigroup" blogu) ayni yazimi yapar.
# Surum degisince testler/test_y8_kosu.py::test_openmc_ic_ayrinti_varsayimlari
# KIRMIZI olur ve calisma aninda surum_uyarisi() kaydedilir.
DOGRULANAN_OPENMC = "0.16"
MG_KIPI = "multi-group"
_KOPYALANAN_AYARLAR = ("run_mode", "particles", "batches", "inactive", "seed",
                       "generations_per_batch")


def surum_uyarisi() -> "str | None":
    """Kurulu OpenMC dogrulanan surum degilse uyari metni (ic ayrinti degismis olabilir)."""
    import openmc
    if openmc.__version__.startswith(DOGRULANAN_OPENMC):
        return None
    return _("OpenMC %s: MG/random ray dönüşümü %s.x iç ayrıntılarıyla doğrulandı") % (
        openmc.__version__, DOGRULANAN_OPENMC)


def _makro(malzeme: "openmc.Material", xsdata: str) -> None:
    """Taze kurulmus modelin malzemesini makroskopige cevirir (yerinde: nesne
    bu islevin cagiraninin kurdugu modele aittir, disariya paylasilmaz)."""
    malzeme._nuclides = []          # noqa: SLF001 (openmc convert_to_multigroup ile ayni)
    malzeme._sab = []               # noqa: SLF001
    malzeme.set_density("macro", 1.0)
    malzeme.add_macroscopic(xsdata)
    malzeme.temperature = None


def _adlar(ozet: Mapping) -> dict:
    return {int(k): v for k, v in (ozet.get("adlar") or {}).items()}


def _malzemeleri_cevir(model: "openmc.Model", bolge: str, adlar: dict) -> list:
    import openmc
    geo = model.geometry
    if bolge == "hucre":
        yeni = []
        for hucre in sorted(geo.get_all_material_cells().values(), key=lambda c: c.id):
            if hucre.id not in adlar:
                raise ValueError(_("hücre %d için grup sabiti yok") % hucre.id)
            m = openmc.Material(name=adlar[hucre.id])
            m.set_density("macro", 1.0)
            m.add_macroscopic(adlar[hucre.id])
            hucre.fill = m
            hucre.temperature = None
            yeni.append(m)
        return yeni
    malzemeler = sorted(geo.get_all_materials().values(), key=lambda m: m.id)
    if bolge == "demet":
        if len(adlar) != 1:
            raise ValueError(_("demet bölgesinde tek xsdata beklenir (%d)") % len(adlar))
        tek = next(iter(adlar.values()))
        for m in malzemeler:
            _makro(m, tek)
        return malzemeler
    for m in malzemeler:
        if m.id not in adlar:
            raise ValueError(_("malzeme %d (%s) için grup sabiti yok") % (m.id, m.name))
        _makro(m, adlar[m.id])
    return malzemeler


def _ayarlar(ce: "openmc.Settings") -> "openmc.Settings":
    import openmc
    s = openmc.Settings()
    for ad in _KOPYALANAN_AYARLAR:
        deger = getattr(ce, ad, None)
        if deger is not None:
            setattr(s, ad, deger)
    s.source = ce.source
    if ce.entropy_mesh is not None:
        s.entropy_mesh = ce.entropy_mesh
    s.energy_mode = MG_KIPI
    return s


def mg_modeli(spec: Mapping, ozet: Mapping, h5: str) -> "openmc.Model":
    """MGXS koşusunun spec'i + mgxs_ozet.json + mgxs.h5 -> YENI MG openmc.Model."""
    import openmc
    from cekirdek import kurucu
    if not os.path.isfile(h5):
        raise FileNotFoundError(_("MG kütüphanesi bulunamadı: %s") % h5)
    uyari = surum_uyarisi()
    if uyari:
        _log.warning("%s", uyari)
    model, _bilgi = kurucu.kur(spec)
    bolge = (ozet.get("ayar") or {}).get("bolge", "malzeme")
    malzemeler = _malzemeleri_cevir(model, bolge, _adlar(ozet))
    model.materials = openmc.Materials(malzemeler)
    model.materials.cross_sections = os.path.abspath(h5)
    model.tallies = openmc.Tallies()
    model.settings = _ayarlar(model.settings)
    return model
