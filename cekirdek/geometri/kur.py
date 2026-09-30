# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/kur.py  --  Agac -> OpenMC (ya da betik): TEK gezinti (R1-R12)
================================================================================

 Kurucu agaci bir kez gezer ve her yapiyi bir Yapici'ya yazar
 (geometri/yapici.py): NesneYapici -> openmc nesneleri, BetikYapici -> ayni
 cagrilarin Python satirlari. Kurucu ile betik boylece ayrisamaz (§12 R-4/R-5).

 KURALLAR (docs/GEOMETRI_MODELI.md §5)
   R1  malzeme her zaman satir ici; kap bolgesinin dogrudan icindeki eksenel
       yigin satir ici (katman hucresi = bolge x z dilimi); bilesen ve kafes
       bir hucrenin fill'idir. Bir bilesenin dogal dolgusu: cubuk/plaka/tambur
       evreni, kilifsiz demette KAFESIN KENDISI (eski tek_demet gibi).
   R2  bilesen ad basina tek evren (distribcell) -- kontrol cubugu HARIC
       (§15 karar 5: her yerlesimi ayri evren; iceren demet/parca da tekil).
   R3  kafes: RectLattice / HexLattice; '.' -> dis. R3b: kafes_zarfi kokte
       altigen kafes KURULMAZ, her konum kendi prizmasiyla kok hucresidir
       (altigen_kor.altigen_kor_hucreleri ile ayni duzlem havuzu ve sira).
   R4  halka i'nin dis yuzeyi halka i+1'in ic yuzeyiyle ayni nesne; BC yalniz
       kokun en dis yuzeyinde ve alt/ust duzlemlerde; kok olmayan kapta
       '+en dis' hucresi dis dolgusuyla.
   R5  yerlesim: delik (daire: ZCylinder(x0, y0, r); prizma: otelenmis
       prizma), ornek hucresi -delik, translation (x, y, 0), rotation
       (0, 0, psi); sahip bolgeye +delik (prizmada ~(-prizma)).
   R6  donusum: yuvayi tutan hucreye translation/rotation.
   R7  ic katman duzlemleri transmission; kok disi yiginda uclar acik.
   R8  kontrol cubugu daldirmasi modelin aktif eksenel araligina gore.
   R10 kafes adi "g:<id>", yerlesim ornegi hucresi "g:<ad>#<i>".
 Yuz basina yan sinir (§15 karar 4): kok sinir.yuzler -- dikdortgende
 {"-x", "+x", "-y", "+y"}, altigende 6 ogeli liste (yuz normali acisi artan
 sirada: prizma 'y' 0, 60, ...; 'x' 30, 90, ...). Periyodik ciftler
 periodic_surface ile eslenir.
================================================================================
"""

import math

from cekirdek.geometri import bilesen as _b
from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer
from cekirdek.geometri.eksenel import model_yuksekligi
from cekirdek.geometri.kap import KapKurucu
from cekirdek.geometri.sema import bilesen_tanimi, kisaltma_coz

SQ3 = math.sqrt(3.0)
DIKDORTGEN_YUZLERI = ("-x", "+x", "-y", "+y")


class _Sinir(object):
    """Bir kesitin kapali siniri: ic() ve dis() bolgeleri."""

    def __init__(self, yuzey=None, duzlemler=None, daire=False):
        self.yuzey = yuzey
        self.duzlemler = duzlemler
        self.daire = daire

    def ic(self):
        if self.duzlemler is None:
            return -self.yuzey
        a, b, c, d = self.duzlemler
        return +a & -b & +c & -d if len(self.duzlemler) == 4 else self._cok_ic()

    def _cok_ic(self):
        bolge = None
        for p in self.duzlemler:
            bolge = -p if bolge is None else bolge & -p
        return bolge

    def dis(self):
        if self.duzlemler is None:
            return +self.yuzey
        return ~self.ic()

    def delik_disi(self):
        """Sahip bolgeye eklenen: daire +delik, prizma ~(-prizma) (R5)."""
        return +self.yuzey if self.daire else ~self.ic()


class GeometriDizini(object):
    """kur'un dizini (R11): hucre/kafes -> dugum yolu, kesik konumlar."""

    def __init__(self):
        self.hucre_yolu = {}
        self.kafes_yolu = {}
        self.kesik = []
        self.kontrol_cubuklari = {}

    def hucre(self, h, yol):
        if hasattr(h, "id"):
            self.hucre_yolu[h.id] = yol
        return h


class Kurucu(KapKurucu):
    """Agac gezgini. y: Yapici; universeler: {bilesen adi: evren} (dis API)."""

    def __init__(self, spec, m, yapici, universeler=None, degisken_adi=None):
        self.spec, self.m, self.y = spec, m, yapici
        self.tanim = m.tanimlar
        self.gruplar = m.gruplar
        self.universeler = {} if universeler is None else universeler
        self.dizin = GeometriDizini()
        self._degisken_adi = degisken_adi
        self._on = {}
        self._tekil = {}
        self._zhavuz = {}
        self.yukseklik = model_yuksekligi(m)
        self._aktif = None
        self.zk = None
        self.kok_z = None

    # ------------------------------------------------------------------
    # yardimcilar
    # ------------------------------------------------------------------
    def degisken(self, onek, ad):
        """Betikte okunur degisken adi (nesne yolunda None)."""
        if self._degisken_adi is None or ad is None:
            return None
        return self._degisken_adi(ad, onek)

    @property
    def aktif(self):
        if self._aktif is None:
            from cekirdek.geometri.eksenel import aktif_aralik
            self._aktif = aktif_aralik(self.spec) or ()
        return self._aktif or None

    def daldirma(self, c):
        g = _yer.grup_degeri(self.gruplar, c.get("ad"), "daldirma")
        return float(c.get("daldirma") or 0.0) if g is None else g

    def _coz(self, d):
        return kisaltma_coz(self.tanim, d) if isinstance(d, str) or d is None else d

    def zduz(self, z):
        """Ic (transmission) z duzlemi havuzu."""
        if z not in self._zhavuz:
            self._zhavuz[z] = self.y.zduzlem(z)
        return self._zhavuz[z]

    # ------------------------------------------------------------------
    # tekillik (kontrol cubugu ve onu iceren her sey paylasilmaz)
    # ------------------------------------------------------------------
    def tekil_ad(self, ad, derinlik=0):
        if ad in self._tekil:
            return self._tekil[ad]
        self._tekil[ad] = False
        tur, t = bilesen_tanimi(self.tanim, ad)
        sonuc = False
        if tur == "cubuk":
            sonuc = t.get("tur") == "kontrol"
        elif tur == "demet" and derinlik < 12:
            sonuc = any(self.tekil(v, derinlik + 1) for v in (t.get("anahtar") or {}).values())
        elif tur == "parca" and derinlik < 12:
            sonuc = self.tekil(t.get("dugum"), derinlik + 1)
        self._tekil[ad] = sonuc
        return sonuc

    def tekil(self, d, derinlik=0):
        from cekirdek.geometri.sema import cocuklar
        d = self._coz(d)
        if not isinstance(d, dict) or derinlik > 12:
            return False
        if d.get("tur") == "bilesen":
            return self.tekil_ad(d.get("ad"), derinlik)
        return any(self.tekil(c, derinlik + 1) for c in cocuklar(d))

    def _onbellek(self, anahtar, tekil, uret):
        if tekil:
            return uret()
        if anahtar not in self._on:
            self._on[anahtar] = uret()
        return self._on[anahtar]

    # ------------------------------------------------------------------
    # dolgu ve evren
    # ------------------------------------------------------------------
    def dolgu(self, d):
        """Dugumun dogal dolgusu: ("malzeme" | "evren" | "kafes", tutamak)."""
        d = self._coz(d)
        tur = d.get("tur")
        if tur == "malzeme":
            return ("malzeme", self.y.malzeme(d.get("ad")))
        if tur == "bilesen":
            return self.bilesen(d.get("ad"))
        if tur == "kafes":
            return ("kafes", self.kafes(d))
        if tur == "kap":
            return ("evren", self._onbellek(("kap", id(d)), self.tekil(d),
                                            lambda: self.kap_evreni(d)))
        if tur == "eksenel":
            return ("evren", self._onbellek(("eks", id(d)), self.tekil(d),
                                            lambda: self.eksenel_evreni(d)))
        raise ValueError("kurulamayan düğüm türü: %r" % (tur,))

    def evren(self, d):
        """Dugumu evren olarak (kafes elemani, dis dolgu, yerlesim icerigi)."""
        d = self._coz(d)
        if d.get("donusum"):
            return self._donusumlu_evren(d)
        tur = d.get("tur")
        if tur == "malzeme":
            ad = d.get("ad")
            return self._onbellek(("mu", ad), False, lambda: self.y.evren(
                [self.y.hucre(self.y.malzeme(ad))], degisken=self.degisken("u", ad)))
        if tur == "bilesen":
            return self.bilesen_evreni(d.get("ad"))
        if tur == "kafes":
            return self._onbellek(("ku", id(d)), self.tekil(d), lambda: self.y.evren(
                [self.y.hucre(self.kafes(d))]))
        return self.dolgu(d)[1]

    def _donusumlu_evren(self, d):
        """Donusumlu dugum evren olarak: tek hucreli sarmalayici (R6)."""
        if d.get("tur") == "malzeme":
            raise ValueError("malzeme düğümüne dönüşüm uygulanamaz")
        return self.y.evren([self.yuva_hucresi(d, None)])

    def dis_evreni(self, d):
        """Kafes dis dolgusu: malzemede her kafese AYRI evren (eski kurucu gibi)."""
        d = self._coz(d)
        if d.get("tur") == "malzeme" and not d.get("donusum"):
            return self.y.evren([self.y.hucre(self.y.malzeme(d.get("ad")))])
        return self.evren(d)

    def yuva_hucresi(self, d, bolge, name=None, yol=None):
        """Yuvayi tutan hucre: fill = dogal dolgu, donusum (R6)."""
        d = self._coz(d)
        don = d.get("donusum") or {}
        if don:
            d = {k: v for k, v in d.items() if k != "donusum"}
        tur, h = self.dolgu(d)
        oteleme = rotation = None
        if don and tur != "malzeme":
            o = don.get("oteleme")
            oteleme = (float(o[0]), float(o[1]), 0.0) if o else None
            rotation = (0.0, 0.0, float(don["donme"])) if don.get("donme") else None
        return self.dizin.hucre(self.y.hucre(h, bolge, name=name, translation=oteleme,
                                             rotation=rotation), yol)

    def bilesen(self, ad):
        tur, t = bilesen_tanimi(self.tanim, ad)
        if tur is None:
            raise KeyError("tanımsız ad: %s (çubuk, plaka elemanı, demet ya da malzeme değil)"
                           % ad)
        if tur == "demet":
            return self._onbellek(("dd", ad), self.tekil_ad(ad),
                                  lambda: _b.demet_dolgusu(self, t, ad))
        if tur == "parca":
            return self._onbellek(("pd", ad), self.tekil_ad(ad),
                                  lambda: self.dolgu(t.get("dugum")))
        return ("evren", self.bilesen_evreni(ad))

    def bilesen_evreni(self, ad):
        tur, t = bilesen_tanimi(self.tanim, ad)
        if tur is None:
            raise KeyError("tanımsız ad: %s (çubuk, plaka elemanı, demet ya da malzeme değil)"
                           % ad)
        tekil = self.tekil_ad(ad)
        if tur == "cubuk":
            u = self._onbellek(("c", ad), tekil, lambda: _b.cubuk(self, t, ad))
        elif tur == "plaka":
            u = self._onbellek(("p", ad), False, lambda: _b.plaka(self, t, ad))
        elif tur == "tambur":
            u = self._onbellek(("t", ad), False, lambda: _b.tambur(self, t, ad))
        elif tur == "demet":
            u = self._onbellek(("du", ad), tekil, lambda: self._demet_evreni(t, ad))
        else:
            u = self._onbellek(("pu", ad), tekil, lambda: self.evren(t.get("dugum")))
        self.universeler.setdefault(ad, u)
        if tekil and tur == "cubuk":
            self.dizin.kontrol_cubuklari.setdefault(ad, []).append(u)
        return u

    def _demet_evreni(self, t, ad):
        tur, h = self.bilesen(ad)
        if tur == "evren":
            return h
        return self.y.evren([self.y.hucre(h)], name=ad, degisken=self.degisken("du", ad))

    # ------------------------------------------------------------------
    # kafes
    # ------------------------------------------------------------------
    def harf_evrenleri(self, harita, anahtar, dis=None):
        """({harf: evren}, {(satir, sutun): evren}) -- tekil harfler her
        konumda ayri evren (kontrol cubugu)."""
        esleme, ozel = {}, {}
        for i, satir in enumerate(harita):
            for j, h in enumerate(satir):
                if h in esleme and not self.tekil(anahtar.get(h, dis)):
                    continue
                d = anahtar.get(h, dis) if h != "." or "." in anahtar else dis
                u = self.evren(d)
                if h in esleme:
                    ozel[(i, j)] = u
                else:
                    esleme[h] = u
        return esleme, ozel

    def kafes(self, d, ek=None):
        """Kafes dugumu -> RectLattice/HexLattice. ek: katmana ozgu anahtar."""
        anahtar_ek = tuple(sorted((h, id(v)) for h, v in (ek or {}).items()))
        return self._onbellek(("k", id(d), anahtar_ek), self.tekil(d),
                              lambda: self._kafes_kur(d, ek))

    def _kafes_kur(self, d, ek):
        anahtar = dict(d.get("anahtar") or {})
        anahtar.update(ek or {})
        harita = d.get("harita") or []
        for h in {c for s in harita for c in s}:
            if h not in anahtar and h != ".":
                raise KeyError("kor haritasında tanımsız harf: '%s'" % h
                               if d.get("_sablon_harita") else
                               "'%s' kafesi: haritada tanımsız harf '%s'" % (d.get("id"), h))
        if d.get("dis") is None:
            raise ValueError("'%s' kafesinin 'dis' yuvası boş" % d.get("id"))
        esleme, ozel = self.harf_evrenleri(harita, anahtar, d.get("dis"))
        if "." in {c for s in harita for c in s} and "." not in esleme:
            esleme["."] = self.evren(d["dis"])
        dis = self.dis_evreni(d["dis"])
        P = d["adim"]
        ad = "g:%s" % d["id"] if d.get("id") else None
        if d.get("sekil") == "kare":
            nx, ny = d["boyut"]
            lat = self.y.kare_kafes(P, (-P * nx / 2.0, -P * ny / 2.0), harita, esleme, dis,
                                    ozel, ad=ad)
        else:
            lat = self.y.altigen_kafes(P, d.get("yonelim", "y"), harita, esleme, dis, ozel,
                                       ad=ad)
        if d.get("id") and hasattr(lat, "id"):
            self.dizin.kafes_yolu[lat.id] = d["id"]
        return lat

    # ------------------------------------------------------------------
    # kesit yuzeyleri
    # ------------------------------------------------------------------
    def kesit_siniri(self, kes, bc=None, yuzler=None, merkez=None):
        s = kes["sekil"]
        y = self.y
        if s == "dikdortgen":
            gx, gy = kes["boyut"]
            if yuzler:
                return self._dikdortgen_yuzleri(gx, gy, bc, yuzler)
            return _Sinir(y.dikdortgen_prizma(gx, gy, origin=merkez, bc=bc))
        if s == "silindir":
            if merkez is None:
                return _Sinir(y.zsilindir(float(kes["yaricap"]), bc=bc), daire=True)
            return _Sinir(y.zsilindir(float(kes["yaricap"]), x0=merkez[0], y0=merkez[1], bc=bc),
                          daire=True)
        if s == "kure":
            return _Sinir(y.kure(float(kes["yaricap"]), bc=bc), daire=True)
        if s == "altigen":
            a = float(kes["apotem"])
            yon = kes.get("yonelim", "y")
            if yuzler:
                return self._altigen_yuzleri(a, yon, bc, yuzler)
            return _Sinir(y.altigen_prizma(2.0 * a / math.sqrt(3.0), yon, origin=merkez, bc=bc))
        raise ValueError("kurulamayan kesit: %s" % s)

    def _dikdortgen_yuzleri(self, gx, gy, bc, yuzler):
        y = self.y
        b = {k: yuzler.get(k, bc) for k in DIKDORTGEN_YUZLERI}
        x0, x1 = y.xduzlem(-gx / 2.0, bc=b["-x"]), y.xduzlem(gx / 2.0, bc=b["+x"])
        y0, y1 = y.yduzlem(-gy / 2.0, bc=b["-y"]), y.yduzlem(gy / 2.0, bc=b["+y"])
        for p, q, a, c in ((x0, x1, "-x", "+x"), (y0, y1, "-y", "+y")):
            if b[a] == "periodic" and b[c] == "periodic":
                y.periyodik(p, q)
        return _Sinir(duzlemler=(x0, x1, y0, y1))

    def _altigen_yuzleri(self, a, yon, bc, yuzler):
        y = self.y
        duz = []
        for i, aci in enumerate(_k.altigen_normal_acilari(yon)):
            t = math.radians(aci)
            duz.append(y.duzlem(math.cos(t), math.sin(t), 0.0, a, bc=yuzler[i] or bc))
        for i in range(3):
            if yuzler[i] == "periodic" and yuzler[i + 3] == "periodic":
                y.periyodik(duz[i], duz[i + 3])
        return _Sinir(duzlemler=tuple(duz))


# ============================================================================
# giris noktalari
# ============================================================================

def kur(spec, nesneler, universeler=None, m=None):
    """
    Agac -> openmc kok evreni. DONER (kok evreni, (gx, gy), GeometriDizini).
    universeler: {bilesen adi: evren} -- kurulan bilesen evrenleri buraya
    yazilir (guc tally'si hedef cubugun GEOMETRIDEKI evrenine ihtiyac duyar).
    """
    from cekirdek import geometri
    from cekirdek.geometri.yapici import NesneYapici
    m = geometri.model(spec) if m is None else m
    k = Kurucu(spec, m, NesneYapici(nesneler), universeler)
    kok, kutu = k.kok_kur()
    return kok, kutu, k.dizin


def betik(spec, satirlar, malzeme_degiskeni, degisken_adi=None, m=None):
    """
    Ayni gezintiyle betik satirlari. satirlar listesine yazar;
    DONER (gx, gy, {bilesen adi: betikteki degisken adi}).
    """
    from cekirdek import geometri
    from cekirdek.geometri.yapici import BetikYapici
    m = geometri.model(spec) if m is None else m
    universeler = {}
    y = BetikYapici(satirlar, malzeme_degiskeni)
    k = Kurucu(spec, m, y, universeler, degisken_adi=degisken_adi)
    _kok, (gx, gy) = k.kok_kur()
    satirlar.append("")
    satirlar.append("geometri = openmc.Geometry(kok)")
    return gx, gy, {ad: str(v) for ad, v in universeler.items()}
