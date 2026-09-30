# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/yapici.py  --  Yapici arayuzu: ayni gezinti -> nesne YA DA betik (R12)
================================================================================

 geometri/kur.py agaci bir kez gezer ve her yapiyi bir Yapici'ya yazar:
   NesneYapici  openmc nesneleri uretir (kurucu).
   BetikYapici  AYNI cagrilari okunur Python satirlari olarak yazar (kod_uret).
 Iki yol ayni sirada ayni cagrilari yaptigi icin ayni kimlikli ayni modeli
 kurar; eskiden iki ayri kod yolu vardi ve ayrisiyordu (§12 R-4, R-5).

 BOLGE CEBIRI
   Nesne yolunda openmc'nin kendi islecleri (-yuzey, &, |, ~) kullanilir.
   Betik yolunda Ifade nesneleri ayni islecleri METIN olarak birlestirir;
   gruplama (parantez) nesne yolundaki degerlendirme sirasiyla aynidir.

 KACIS (M3)
   Betige giden her kullanici metni (ad, katman adi, malzeme adi) repr ile
   yazilir; yorumlara giden metin yorum_metni() ile tek satira indirgenir
   (satir sonu / denetim karakteri yorumdan cikip kod olamaz).
================================================================================
"""

import re

import openmc

# ----------------------------------------------------------------------------
# ortak
# ----------------------------------------------------------------------------

_SATIR_KIRAN = re.compile(r"[\x00-\x1f\x7f\x85  ]")


def yorum_metni(metin):
    """Kullanici metnini tek satirlik guvenli yorum metnine cevirir."""
    return _SATIR_KIRAN.sub(" ", str(metin))


def sayi(deger):
    """Sayiyi tam duyarlikla yazar (repr; yuvarlama kaybi yok)."""
    if deger is None:
        return "None"
    if isinstance(deger, bool):
        return repr(deger)
    if isinstance(deger, (int, float)):
        return repr(deger)
    return repr(float(deger))


def _demet(degerler):
    degerler = list(degerler)
    if len(degerler) == 1:
        return "(%s,)" % sayi(degerler[0])
    return "(%s)" % ", ".join(sayi(v) for v in degerler)


class NesneYapici(object):
    """openmc nesneleri ureten yapici (kurucu yolu)."""
    betik = False

    def __init__(self, nesneler):
        self.nesneler = nesneler

    # --- ozel ---
    def yorum(self, metin):
        return None

    def malzeme(self, ad):
        """Malzeme adi -> openmc.Material; 'bosluk'/None -> None (void)."""
        if ad is None or ad == "bosluk":
            return None
        if ad not in self.nesneler:
            raise KeyError("tanımsız malzeme: %s" % ad)
        return self.nesneler[ad]

    # --- yuzeyler ---
    def zduzlem(self, z0, bc=None):
        return openmc.ZPlane(z0, **_bc(bc))

    def xduzlem(self, x0, bc=None):
        return openmc.XPlane(x0, **_bc(bc))

    def yduzlem(self, y0, bc=None):
        return openmc.YPlane(y0, **_bc(bc))

    def duzlem(self, a, b, c, d, bc=None):
        return openmc.Plane(a=a, b=b, c=c, d=d, **_bc(bc))

    def zsilindir(self, r, x0=None, y0=None, bc=None):
        kw = _bc(bc)
        if x0 is not None:
            kw.update(x0=x0, y0=y0)
        return openmc.ZCylinder(r=r, **kw)

    def kure(self, r, bc=None):
        return openmc.Sphere(r=r, **_bc(bc))

    def dikdortgen_prizma(self, gx, gy, origin=None, bc=None):
        kw = _bc(bc)
        if origin is not None:
            kw["origin"] = origin
        return openmc.model.RectangularPrism(gx, gy, **kw)

    def altigen_prizma(self, kenar, yonelim, origin=None, bc=None):
        kw = _bc(bc)
        if origin is not None:
            kw["origin"] = origin
        return openmc.model.HexagonalPrism(edge_length=kenar, orientation=yonelim, **kw)

    def periyodik(self, s1, s2):
        s1.periodic_surface = s2

    # --- hucre / evren / kafes ---
    def hucre(self, fill, region=None, name=None, translation=None, rotation=None):
        kw = {"fill": fill}
        if region is not None:
            kw["region"] = region
        if name is not None:
            kw["name"] = name
        h = openmc.Cell(**kw)
        if translation is not None:
            h.translation = translation
        if rotation is not None:
            h.rotation = rotation
        return h

    def evren(self, hucreler, name=None, degisken=None):
        kw = {"cells": list(hucreler)}
        if name is not None:
            kw["name"] = name
        return openmc.Universe(**kw)

    def pin(self, yuzeyler, dolgular, degisken=None):
        return openmc.model.pin(list(yuzeyler), list(dolgular))

    def kare_kafes(self, adim, sol_alt, harita, anahtar, dis, ozel=None, ad=None,
                   degisken=None):
        lat = openmc.RectLattice(**({"name": ad} if ad else {}))
        lat.pitch = (adim, adim)
        lat.lower_left = sol_alt
        lat.outer = dis
        lat.universes = _matris(harita, anahtar, ozel)
        return lat

    def altigen_kafes(self, adim, yonelim, harita, anahtar, dis, ozel=None, ad=None,
                      degisken=None):
        lat = openmc.HexLattice(**({"name": ad} if ad else {}))
        lat.center = (0.0, 0.0)
        lat.pitch = (adim,)
        lat.orientation = yonelim
        lat.outer = dis
        lat.universes = _matris(harita, anahtar, ozel)
        return lat


def _bc(bc):
    return {} if bc in (None, "transmission") else {"boundary_type": bc}


def _matris(harita, anahtar, ozel):
    m = [[anahtar[h] for h in satir] for satir in harita]
    for (i, j), u in sorted((ozel or {}).items()):
        m[i][j] = u
    return m


# ----------------------------------------------------------------------------
# betik
# ----------------------------------------------------------------------------

_ATOM, _VE, _VEYA = 3, 2, 1


class Ifade(object):
    """Betikteki bir degiskenin ya da bolge ifadesinin metni."""

    def __init__(self, metin, oncelik=_ATOM):
        self.metin = metin
        self.oncelik = oncelik

    def __str__(self):
        return self.metin

    def __neg__(self):
        return Ifade("-" + self.metin)

    def __pos__(self):
        return Ifade("+" + self.metin)

    def __invert__(self):
        ic = self.metin if self.oncelik == _ATOM else "(%s)" % self.metin
        return Ifade("~" + ic)

    def _ikili(self, diger, isl, oncelik):
        sol = self.metin if self.oncelik >= oncelik else "(%s)" % self.metin
        sag = diger.metin if diger.oncelik > oncelik else "(%s)" % diger.metin
        return Ifade("%s %s %s" % (sol, isl, sag), oncelik)

    def __and__(self, diger):
        return self._ikili(diger, "&", _VE)

    def __or__(self, diger):
        return self._ikili(diger, "|", _VEYA)


def _ifade(x):
    return "None" if x is None else str(x)


class BetikYapici(object):
    """Ayni yapici cagrilarini Python satirlari olarak yazan yapici."""
    betik = True

    def __init__(self, satirlar, malzeme_degiskeni):
        self.satirlar = satirlar
        self._malzeme_degiskeni = malzeme_degiskeni
        self._sayac = {}

    def _yeni(self, onek):
        n = self._sayac.get(onek, 0) + 1
        self._sayac[onek] = n
        return "%s%d" % (onek, n)

    def _ata(self, onek, ifade, degisken=None):
        v = degisken or self._yeni(onek)
        self.satirlar.append("%s = %s" % (v, ifade))
        return Ifade(v)

    def yorum(self, metin):
        self.satirlar.append("# " + yorum_metni(metin))

    def bos_satir(self):
        self.satirlar.append("")

    def malzeme(self, ad):
        if ad is None or ad == "bosluk":
            return None
        return Ifade(self._malzeme_degiskeni(ad))

    # --- yuzeyler ---
    def _bc(self, bc):
        return "" if bc in (None, "transmission") else ", boundary_type=%r" % bc

    def zduzlem(self, z0, bc=None):
        return self._ata("_s", "openmc.ZPlane(%s%s)" % (sayi(z0), self._bc(bc)))

    def xduzlem(self, x0, bc=None):
        return self._ata("_s", "openmc.XPlane(%s%s)" % (sayi(x0), self._bc(bc)))

    def yduzlem(self, y0, bc=None):
        return self._ata("_s", "openmc.YPlane(%s%s)" % (sayi(y0), self._bc(bc)))

    def duzlem(self, a, b, c, d, bc=None):
        return self._ata("_s", "openmc.Plane(a=%s, b=%s, c=%s, d=%s%s)"
                         % (sayi(a), sayi(b), sayi(c), sayi(d), self._bc(bc)))

    def zsilindir(self, r, x0=None, y0=None, bc=None):
        yer = "" if x0 is None else "x0=%s, y0=%s, " % (sayi(x0), sayi(y0))
        return self._ata("_s", "openmc.ZCylinder(%sr=%s%s)" % (yer, sayi(r), self._bc(bc)))

    def kure(self, r, bc=None):
        return self._ata("_s", "openmc.Sphere(r=%s%s)" % (sayi(r), self._bc(bc)))

    def dikdortgen_prizma(self, gx, gy, origin=None, bc=None):
        o = "" if origin is None else ", origin=%s" % _demet(origin)
        return self._ata("_s", "openmc.model.RectangularPrism(%s, %s%s%s)"
                         % (sayi(gx), sayi(gy), o, self._bc(bc)))

    def altigen_prizma(self, kenar, yonelim, origin=None, bc=None):
        o = "" if origin is None else ", origin=%s" % _demet(origin)
        return self._ata("_s", "openmc.model.HexagonalPrism(edge_length=%s, orientation=%r%s%s)"
                         % (sayi(kenar), yonelim, o, self._bc(bc)))

    def periyodik(self, s1, s2):
        self.satirlar.append("%s.periodic_surface = %s" % (s1, s2))

    # --- hucre / evren / kafes ---
    def hucre(self, fill, region=None, name=None, translation=None, rotation=None):
        ek = ""
        if region is not None:
            ek += ", region=%s" % region
        if name is not None:
            ek += ", name=%r" % (name,)
        h = self._ata("_h", "openmc.Cell(fill=%s%s)" % (_ifade(fill), ek))
        if translation is not None:
            self.satirlar.append("%s.translation = %s" % (h, _demet(translation)))
        if rotation is not None:
            self.satirlar.append("%s.rotation = %s" % (h, _demet(rotation)))
        return h

    def evren(self, hucreler, name=None, degisken=None):
        ad = "" if name is None else ", name=%r" % (name,)
        return self._ata("_u", "openmc.Universe(cells=[%s]%s)"
                         % (", ".join(str(h) for h in hucreler), ad), degisken)

    def pin(self, yuzeyler, dolgular, degisken=None):
        return self._ata("_u", "openmc.model.pin([%s], [%s])"
                         % (", ".join(str(s) for s in yuzeyler),
                            ", ".join(_ifade(d) for d in dolgular)), degisken)

    def _kafes_ortak(self, v, dis, harita, anahtar, ozel):
        self.satirlar.append("%s.outer = %s" % (v, dis))
        harfler = sorted({h for s in harita for h in s})
        self.satirlar.append("_anahtar = {%s}" % ", ".join(
            "%r: %s" % (h, _ifade(anahtar[h])) for h in harfler))
        self.satirlar.append("_harita = [")
        # !!! VIRGUL SART !!! virgulsuz ardarda dizeler ortuk birlesir
        self.satirlar.extend("    %r," % s for s in harita)
        self.satirlar.append("]")
        self.satirlar.append("_matris = [[_anahtar[_c] for _c in _s] for _s in _harita]")
        for (i, j), u in sorted((ozel or {}).items()):
            self.satirlar.append("_matris[%d][%d] = %s" % (i, j, u))
        self.satirlar.append("%s.universes = _matris" % v)

    def kare_kafes(self, adim, sol_alt, harita, anahtar, dis, ozel=None, ad=None, degisken=None):
        a = "" if not ad else "name=%r" % (ad,)
        v = self._ata("_k", "openmc.RectLattice(%s)" % a, degisken)
        self.satirlar.append("%s.pitch = (%s, %s)" % (v, sayi(adim), sayi(adim)))
        self.satirlar.append("%s.lower_left = %s" % (v, _demet(sol_alt)))
        self._kafes_ortak(v, dis, harita, anahtar, ozel)
        return v

    def altigen_kafes(self, adim, yonelim, harita, anahtar, dis, ozel=None, ad=None,
                      degisken=None):
        a = "" if not ad else "name=%r" % (ad,)
        v = self._ata("_k", "openmc.HexLattice(%s)" % a, degisken)
        self.satirlar.append("%s.center = (0.0, 0.0)" % v)
        self.satirlar.append("%s.pitch = (%s,)" % (v, sayi(adim)))
        self.satirlar.append("%s.orientation = %r" % (v, yonelim))
        self.yorum("halkalar dıştan içe; her halka tepeden (x: sağdan) saat yönünde")
        self._kafes_ortak(v, dis, harita, anahtar, ozel)
        return v
