# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/tanim.py  --  mesh tally filtresinin TANIMI (v3 Y1)

 Spec'teki mesh filtresi (tallyler[i].filtreler[j], "tur": "mesh"):

   duzenli    {"tur": "mesh", "boyut": [nx, ny, nz], "otomatik": true}
              ya da acik "alt": [x, y, z], "ust": [x, y, z] (cm)
              ("mesh_turu" yoksa duzenli -- eski dosyalar aynen calisir)
   silindirik {"tur": "mesh", "mesh_turu": "silindirik", "boyut": [nr, nphi, nz],
               "otomatik": true}  ya da acik "r_ust", "z_alt", "z_ust" (cm);
               istege bagli "merkez": [x, y, z]
   kuresel    {"tur": "mesh", "mesh_turu": "kuresel", "boyut": [nr, ntheta, nphi],
               "otomatik": true}  ya da acik "r_ust"; istege bagli "merkez"

 TEK KAYNAK: kurucu.tallyleri_kur ve kod_uret (betik) AYNI mesh_tanimi()
 sonucundan kurar -- ayni sayiyi iki yoldan hesaplayan iki kod ayrisir.
 Izgaralar esit aralikli (numpy.linspace; betik de ayni cagriyi yazar, sonuc
 bit bit aynidir).

 OpenMC 0.16.0 (kurulu surum, kaynaktan dogrulandi: openmc/mesh.py):
 RegularMesh, RectilinearMesh, CylindricalMesh, SphericalMesh, UnstructuredMesh
 var; HexagonalMesh YOK (bkz. HEKSAGONAL_NOTU).
"""

import math

from cekirdek.ceviri import _, N_

DUZENLI = "duzenli"
SILINDIRIK = "silindirik"
KURESEL = "kuresel"
MESH_TURLERI = (DUZENLI, SILINDIRIK, KURESEL)
MESH_TUR_ADLARI = {
    DUZENLI: N_("Düzenli (x, y, z)"),
    SILINDIRIK: N_("Silindirik (r, φ, z)"),
    KURESEL: N_("Küresel (r, θ, φ)"),
}
# Bolme sayilarinin eksen adlari (OpenMC axis_labels sirasi)
EKSEN_ADLARI = {
    DUZENLI: ("x", "y", "z"),
    SILINDIRIK: ("r", "φ", "z"),
    KURESEL: ("r", "θ", "φ"),
}
HEKSAGONAL_NOTU = N_(
    "Altıgen ağ kapsam dışı: kurulu OpenMC 0.16.0'da HexagonalMesh sınıfı yok "
    "(openmc/mesh.py yalnız RegularMesh, RectilinearMesh, CylindricalMesh, "
    "SphericalMesh, UnstructuredMesh sunar). Altıgen demette düzenli ya da "
    "silindirik ağ kullanın.")

# 2B (eksenel yonde SONSUZ, z sinirsiz) modelde otomatik agin z yari yuksekligi [cm].
# Ag butun z kolonunu kapsar: tally degeri z UZERINDEN INTEGRALDIR (kaynak
# dagiliminin z'deki kaymasindan bagimsiz). v2'de +/-1 cm idi: 2 cm'lik dilim
# iz uzunlugunun kucuk bir kesrini sayiyordu (olculdu, pwr_mesh_aki 5000 x 40
# aktif: kappa-fission bagil hata medyani %21 -> %2.7, ayni gecmis sayisi).
# Bu yuzden 2B'de hacim basina deger AG YUKSEKLIGINE gore ortalamadir ve mutlak
# anlami yoktur; sonuc.olcu() 2B'de hucre ALANINI verir (z integrali / cm2),
# mutlak kip cizgisel guc [W/cm] ister. 1e4 cm, kaynagin 60-300 cevrimdeki z
# rastgele yuruyusunden (~sqrt(cevrim) x goc uzunlugu ~ 1e2 cm) iki mertebe buyuk.
Z_2B_YARI = 1.0e4

# Ozdeger hesabinda mesh tally varsa eklenen FILTRESIZ isinma tally'si: mutlak
# normalizasyonun H'si buradan alinir (ag fisil bolgeyi kapsamasa da dogru).
# kappa-fission: guc.py ile ayni tanim; heating-local: yakalanma gamalari dahil
# (foton tasinimi kapaliyken yerel birakim) -- aki/tepkime normalizasyonu icin.
GENEL_ISI_TALLY = "mesh_genel_isi"
GENEL_ISI_SKORLARI = ("kappa-fission", "heating-local")

TAM_TUR = 2.0 * math.pi           # phi araligi [rad]
YARIM_TUR = math.pi               # theta araligi [rad]
_EKSEN_SAYISI = 3

# Ortak enerji grup yapilari: sinirlar openmc.mgxs.GROUP_STRUCTURES'tan
# (elle yazilmaz). CASMO: Studsvik CASMO-4 grup yapilari; XMAS-172 ve SHEM-361
# OpenMC belgesindeki kaynaklariyla.
GRUP_YAPILARI = ("CASMO-2", "CASMO-4", "CASMO-8", "CASMO-16", "CASMO-25",
                 "CASMO-40", "CASMO-70", "XMAS-172", "SHEM-361")


def mesh_turu(f: dict) -> str:
    """Filtrenin mesh turu; yoksa duzenli. Bilinmeyen tur ValueError."""
    tur = (f or {}).get("mesh_turu") or DUZENLI
    if tur not in MESH_TURLERI:
        raise ValueError(_("bilinmeyen ağ türü: %s (geçerli: %s)")
                         % (tur, ", ".join(MESH_TURLERI)))
    return tur


# ---------------------------------------------------------------------------
# kuruculari (spec sozlukleri; yeni nesne doner)
# ---------------------------------------------------------------------------

def filtre_duzenli(boyut, alt=None, ust=None) -> dict:
    """Duzenli mesh filtresi; alt/ust verilmezse sinirlar otomatik."""
    if alt is None or ust is None:
        return {"tur": "mesh", "boyut": list(boyut), "otomatik": True}
    return {"tur": "mesh", "boyut": list(boyut), "alt": list(alt), "ust": list(ust)}


def filtre_silindirik(boyut, r_ust=None, z_alt=None, z_ust=None, merkez=None) -> dict:
    """Silindirik mesh filtresi [nr, nphi, nz]; r_ust yoksa sinirlar otomatik."""
    f = {"tur": "mesh", "mesh_turu": SILINDIRIK, "boyut": list(boyut)}
    if r_ust is None:
        f["otomatik"] = True
    else:
        f.update(r_ust=float(r_ust), z_alt=float(z_alt), z_ust=float(z_ust))
    if merkez is not None:
        f["merkez"] = list(merkez)
    return f


def filtre_kuresel(boyut, r_ust=None, merkez=None) -> dict:
    """Kuresel mesh filtresi [nr, ntheta, nphi]; r_ust yoksa otomatik."""
    f = {"tur": "mesh", "mesh_turu": KURESEL, "boyut": list(boyut)}
    if r_ust is None:
        f["otomatik"] = True
    else:
        f["r_ust"] = float(r_ust)
    if merkez is not None:
        f["merkez"] = list(merkez)
    return f


# ---------------------------------------------------------------------------
# dogrulama
# ---------------------------------------------------------------------------

def _boyut_hatalari(f):
    b = f.get("boyut")
    if not isinstance(b, (list, tuple)) or len(b) != _EKSEN_SAYISI:
        return [_("ağ bölme sayısı üç değer olmalı (%s)") % (b,)]
    try:
        if any(int(n) != n or int(n) < 1 for n in b):
            return [_("ağ bölme sayıları pozitif tam sayı olmalı (%s)") % (b,)]
    except (TypeError, ValueError):
        return [_("ağ bölme sayıları sayı olmalı (%s)") % (b,)]
    return []


def _acik_sinir_hatalari(f, tur):
    if f.get("otomatik"):
        return []
    if tur == DUZENLI:
        alt, ust = f.get("alt"), f.get("ust")
        if not (alt and ust):
            return []        # sinir yok -> otomatik (kurucu.tally_mesh_sinirlari)
        if len(alt) != 3 or len(ust) != 3 or any(a >= u for a, u in zip(alt, ust)):
            return [_("ağ alt sınırı her eksende üst sınırdan küçük olmalı")]
        return []
    hatalar = []
    r = f.get("r_ust")
    if r is None or float(r) <= 0.0:
        hatalar.append(_("ağ dış yarıçapı sıfırdan büyük olmalı"))
    if tur == SILINDIRIK and not float(f.get("z_alt", 0.0)) < float(f.get("z_ust", 0.0)):
        hatalar.append(_("ağın z alt sınırı üst sınırdan küçük olmalı"))
    return hatalar


def filtre_hatalari(f: dict) -> list:
    """Mesh filtresindeki hatalar (gorunen metin listesi); [] = gecerli."""
    try:
        tur = mesh_turu(f)
    except ValueError as e:
        return [str(e)]
    return _boyut_hatalari(f) + _acik_sinir_hatalari(f, tur)


# ---------------------------------------------------------------------------
# sinirlar ve tanim
# ---------------------------------------------------------------------------

def model_sinir_kutusu(spec: dict) -> tuple:
    """Modelin sinir kutusu (gx, gy) [cm] -- OpenMC modeli KURMADAN (geometri
    modelinden; kurucu.kur'un bilgi["sinir_kutu"] degeriyle ayni, test edilir)."""
    from cekirdek import geometri
    return tuple(float(x) for x in geometri.sinir_kutusu(geometri.model(spec)))


def sinir_onerisi(spec: dict, sinir_kutu, tur: str, z_aralik=None) -> dict:
    """
    Modelin sinir kutusundan (gx, gy) [cm] otomatik sinir onerisi.
      duzenli    : x, y kurucu.tally_mesh_sinirlari ile ayni (sinir kutusu); z kor
                   yuksekligi, kurede kure capi, 2B (eksenel sonsuz) modelde
                   +/-Z_2B_YARI (bkz. sabitin notu) -- ya da z_aralik verilmisse
                   (geometri z'de sinirliysa; genel.geometri_z_araligi) o aralik
      silindirik : r = max(gx, gy)/2: yuvarlak modelde tam; KARE/ALTIGEN modelde
                   koseler agin DISINDA kalir (kare demette ~%21.5 alan), z duzenli
                   ile ayni
      kuresel    : r = max(gx, gy)/2 (ayni not)
    """
    from cekirdek import kurucu
    alt, ust = kurucu.tally_mesh_sinirlari(spec, {"otomatik": True}, sinir_kutu)
    if eksenel_sonsuz(spec):
        z0, z1 = z_aralik if z_aralik is not None else (-Z_2B_YARI, Z_2B_YARI)
        alt, ust = alt[:2] + [float(z0)], ust[:2] + [float(z1)]
    if tur == DUZENLI:
        return {"alt": alt, "ust": ust}
    r = max(float(sinir_kutu[0]), float(sinir_kutu[1])) / 2.0
    if tur == SILINDIRIK:
        return {"r_ust": r, "z_alt": alt[2], "z_ust": ust[2]}
    if tur == KURESEL:
        return {"r_ust": r}
    raise ValueError(_("bilinmeyen ağ türü: %s") % tur)


def eksenel_sonsuz(spec: dict) -> bool:
    """2B model: kor yuksekligi yok ve kure degil (spec'e gore z ekseninde sinir
    yok). Geometri yine de z'de sinirliysa kurucu/betik z_aralik ile kirpar
    (genel.geometri_z_araligi); butun orneklerde iki olcut ayni (test D7)."""
    from cekirdek import kurucu, sema
    return not sema.model_yuksekligi(spec) and not kurucu._kure_mu(spec)


def _sinirlar(spec, f, tur, sinir_kutu, z_aralik):
    if tur == DUZENLI:
        if not f.get("otomatik") and f.get("alt") and f.get("ust"):
            return {"alt": list(f["alt"]), "ust": list(f["ust"])}
        return sinir_onerisi(spec, sinir_kutu, tur, z_aralik)
    if not f.get("otomatik") and f.get("r_ust") is not None:
        return {k: float(f[k]) for k in ("r_ust", "z_alt", "z_ust") if k in f}
    return sinir_onerisi(spec, sinir_kutu, tur, z_aralik)


def mesh_tanimi(spec, f, sinir_kutu, z_aralik=None) -> dict:
    """
    Filtre -> mesh tanimi (yeni sozluk; girdi degismez):
      {"tur", "boyut": (3 tam sayi), "merkez": (x, y, z),
       duzenli: "alt", "ust" | silindirik: "r", "phi", "z" | kuresel: "r", "theta", "phi"}
    (her eksen (alt, ust) cifti). Gecersiz filtre ValueError. z_aralik: 2B
    modelde geometrinin sonlu z sinirlari (yoksa None -> +/-Z_2B_YARI).
    """
    hatalar = filtre_hatalari(f)
    if hatalar:
        raise ValueError("; ".join(hatalar))
    tur = mesh_turu(f)
    boyut = tuple(int(n) for n in f["boyut"])
    merkez = tuple(float(x) for x in (f.get("merkez") or (0.0, 0.0, 0.0)))
    s = _sinirlar(spec, f, tur, sinir_kutu, z_aralik)
    tanim = {"tur": tur, "boyut": boyut, "merkez": merkez}
    if tur == DUZENLI:
        tanim.update(alt=tuple(s["alt"]), ust=tuple(s["ust"]))
    elif tur == SILINDIRIK:
        tanim.update(r=(0.0, s["r_ust"]), phi=(0.0, TAM_TUR), z=(s["z_alt"], s["z_ust"]))
    else:
        tanim.update(r=(0.0, s["r_ust"]), theta=(0.0, YARIM_TUR), phi=(0.0, TAM_TUR))
    return tanim


def izgaralar(tanim: dict) -> tuple:
    """(eksen1, eksen2, eksen3) sinir izgaralari -- numpy.linspace (betikle ayni)."""
    import numpy as np
    eksenler = {DUZENLI: None, SILINDIRIK: ("r", "phi", "z"),
                KURESEL: ("r", "theta", "phi")}[tanim["tur"]]
    if eksenler is None:
        return tuple(np.linspace(a, u, n + 1) for a, u, n in
                     zip(tanim["alt"], tanim["ust"], tanim["boyut"]))
    return tuple(np.linspace(tanim[e][0], tanim[e][1], n + 1)
                 for e, n in zip(eksenler, tanim["boyut"]))


def mesh_kur(tanim: dict):
    """Tanimdan openmc mesh nesnesi."""
    import openmc
    tur = tanim["tur"]
    if tur == DUZENLI:
        m = openmc.RegularMesh()
        m.dimension = list(tanim["boyut"])
        m.lower_left = list(tanim["alt"])
        m.upper_right = list(tanim["ust"])
        return m
    g = izgaralar(tanim)
    if tur == SILINDIRIK:
        return openmc.CylindricalMesh(r_grid=g[0], phi_grid=g[1], z_grid=g[2],
                                      origin=list(tanim["merkez"]))
    return openmc.SphericalMesh(r_grid=g[0], theta_grid=g[1], phi_grid=g[2],
                                origin=list(tanim["merkez"]))


def _linspace_ifadesi(aralik, n):
    return "np.linspace(%r, %r, %d)" % (float(aralik[0]), float(aralik[1]), n + 1)


def betik_satirlari(tanim: dict, degisken: str) -> list:
    """Tanimdan betik satirlari (yeni liste); mesh_kur ile AYNI nesneyi kurar."""
    tur, b = tanim["tur"], tanim["boyut"]
    if tur == DUZENLI:
        # Eski betik ciktisiyla ayni satirlar (degismedi).
        return ["%s = openmc.RegularMesh()" % degisken,
                "%s.dimension  = %r" % (degisken, list(b)),
                "%s.lower_left = %r" % (degisken, list(tanim["alt"])),
                "%s.upper_right = %r" % (degisken, list(tanim["ust"]))]
    sinif, eksenler = (("CylindricalMesh", (("r_grid", "r"), ("phi_grid", "phi"),
                                            ("z_grid", "z")))
                       if tur == SILINDIRIK else
                       ("SphericalMesh", (("r_grid", "r"), ("theta_grid", "theta"),
                                          ("phi_grid", "phi"))))
    satirlar = ["%s = openmc.%s(" % (degisken, sinif)]
    for (arg, e), n in zip(eksenler, b):
        satirlar.append("    %s=%s," % (arg, _linspace_ifadesi(tanim[e], n)))
    satirlar.append("    origin=%r)" % [float(x) for x in tanim["merkez"]])
    return satirlar


NUMPY_SATIRI = "import numpy as np"


def betik_filtresi(spec: dict, f: dict, sinir_kutu, degisken: str, z_aralik=None,
                   onceki=()) -> list:
    """kod_uret kancasi: mesh filtresinin betik satirlari (aciklama dahil).
    onceki: betigin o ana kadarki satirlari -- numpy ice aktarimi BIR KEZ yazilir."""
    tanim = mesh_tanimi(spec, f, sinir_kutu, z_aralik)
    satirlar = []
    if f.get("otomatik"):
        satirlar.append("# mesh sınırları modelin sınır kutusundan türetildi")
    if tanim["tur"] != DUZENLI and NUMPY_SATIRI not in onceki:
        satirlar.append(NUMPY_SATIRI)
    return satirlar + betik_satirlari(tanim, degisken)


def mesh_filtresi_kur(spec, f, sinir_kutu, z_aralik=None):
    """kurucu kancasi: spec filtresi -> openmc.MeshFilter."""
    import openmc
    return openmc.MeshFilter(mesh_kur(mesh_tanimi(spec, f, sinir_kutu, z_aralik)))


# ---------------------------------------------------------------------------
# enerji grup yapilari
# ---------------------------------------------------------------------------

def grup_sinirlari(ad: str) -> list:
    """Grup yapisinin sinirlari [eV] (artan; yeni liste). Bilinmeyen ad ValueError."""
    if ad not in GRUP_YAPILARI:
        raise ValueError(_("bilinmeyen enerji grup yapısı: %s") % ad)
    from openmc.mgxs import GROUP_STRUCTURES
    return [float(x) for x in GROUP_STRUCTURES[ad]]


def yapi_bul(gruplar) -> str | None:
    """Sinir listesi bilinen bir yapiya esitse adi, degilse None."""
    hedef = [float(x) for x in gruplar or []]
    for ad in GRUP_YAPILARI:
        if grup_sinirlari(ad) == hedef:
            return ad
    return None
