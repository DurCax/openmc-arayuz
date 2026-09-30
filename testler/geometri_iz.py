# -*- coding: utf-8 -*-
"""
================================================================================
 testler/geometri_iz.py  --  Esdegerlik kapisi: kimlikten bagimsiz nokta parmak izi
================================================================================

 docs/GEOMETRI_MODELI.md §9-A. G-1 sahibi; G-2 (ice aktarma gidis-donusu)
 yalniz okur.

 Bir noktanin izi (kimlik icermez):
   (malzeme adi | None (void) | "DISARI",
    kafes indeksleri dizisi   -- her kafes duzeyinde (kafes dis dolgusu: "dis"),
    oteleme dizisi (1e-9)     -- oteleme tasiyan her hucre,
    donme dizisi (1e-9)       -- donme tasiyan her hucre,
    yaprak hucrenin distribcell ornek sirasi, yaprak hucrenin ornek sayisi)
 Ornek sirasi Python Cell.paths sirasidir (= C++ distribcell sirasi; TH10).
 paths listesi uretilmez: determine_paths ile AYNI gezinti sirasiyla sayilir
 (buyuk korlarda paths milyonlarca dize olurdu).
 Gezinti C++ ile ayni: dolgulu hucreye girerken yerel = R (p - t) -- kafes
 dolgusunda da (openmc Python Universe.find kafes dolgusunda otelemeyi
 uygulamaz; burada uygulanir).

 Yapisal sarmalayici farklari (eski kurucunun katman dolgusu icin kurdugu
 tek hucreli ara evren, paylasilmayan kafes kopyalari) ize girmez: iz,
 fiziksel olarak anlamli olan her seyi (malzeme, konum indeksleri, yerel
 cerceveler, ornek numarasi) karsilastirir.
================================================================================
"""

import math
import random

SQ3 = math.sqrt(3.0)


def _yuvarla(v, basamak=9):
    return tuple(round(float(x), basamak) + 0.0 for x in v)


class OrnekSayaci(object):
    """determine_paths sirasiyla ornek sayimi (onbellekli)."""

    def __init__(self):
        self._evren = {}
        self._kafes = {}

    def evren(self, u, hedef):
        a = (id(u), id(hedef))
        if a not in self._evren:
            self._evren[a] = sum(self.hucre(c, hedef) for c in u._cells.values())
        return self._evren[a]

    def hucre(self, c, hedef):
        n = 1 if c is hedef else 0
        if c.fill_type == "universe":
            n += self.evren(c.fill, hedef)
        elif c.fill_type == "lattice":
            onek, _sira = self.kafes(c.fill, hedef)
            n += onek[-1]
        return n

    def kafes(self, lat, hedef):
        a = (id(lat), id(hedef))
        if a not in self._kafes:
            onek, sira, t = [0], {}, 0
            for i, idx in enumerate(lat._natural_indices):
                sira[tuple(idx)] = i
                t += self.evren(lat.get_universe(idx), hedef)
                onek.append(t)
            self._kafes[a] = (onek, sira)
        return self._kafes[a]


def _kafes_indeksi(lat, idx):
    import openmc
    if isinstance(lat, openmc.HexLattice) and lat.num_axial is None:
        return tuple(int(i) for i in idx[:2])
    return tuple(int(i) for i in idx[:lat.ndim])


_HIZLI_ESIK = 40          # bu kadar hucreden buyuk evrenlerde vektorel arama
_HIZLI = {}


def _yari_uzaylar(bolge):
    """Salt kesisim bolgesi -> [(yuzey, isaret)]; baska yapi None."""
    import openmc
    if isinstance(bolge, openmc.Halfspace):
        return [(bolge.surface, bolge.side)]
    if isinstance(bolge, openmc.Intersection):
        cikti = []
        for n in bolge:
            alt = _yari_uzaylar(n)
            if alt is None:
                return None
            cikti += alt
        return cikti
    return None


def _yuzey_katsayi(s):
    """Vektorel degerlendirme: ('d', a, b, c, d) duzlem, ('s', x0, y0, r) silindir."""
    import openmc
    if isinstance(s, (openmc.Plane, openmc.XPlane, openmc.YPlane, openmc.ZPlane)):
        return ("d",) + tuple(float(v) for v in s._get_base_coeffs())
    if isinstance(s, openmc.ZCylinder):
        return ("s", float(s.x0), float(s.y0), float(s.r))
    return None


class _HizliEvren(object):
    """Cok hucreli evrende (R3b kok) ilk iceren hucreyi numpy ile bulur."""

    def __init__(self, evren):
        import numpy as np
        self.hucreler = list(evren._cells.values())
        yuzeyler, sutun, satirlar = [], {}, []
        for c in self.hucreler:
            yarilar = _yari_uzaylar(c.region) if c.region is not None else []
            if yarilar is None:
                raise ValueError("salt kesisim degil")
            satir = []
            for s, isaret in yarilar:
                if id(s) not in sutun:
                    if _yuzey_katsayi(s) is None:
                        raise ValueError("desteklenmeyen yuzey")
                    sutun[id(s)] = len(yuzeyler)
                    yuzeyler.append(_yuzey_katsayi(s))
                satir.append((sutun[id(s)], 1.0 if isaret == "+" else -1.0))
            satirlar.append(satir)
        k = max(1, max(len(s) for s in satirlar))
        self.sut = np.zeros((len(satirlar), k), dtype=int)
        self.isr = np.zeros((len(satirlar), k))
        for i, satir in enumerate(satirlar):
            for j, (c, isr) in enumerate(satir):
                self.sut[i, j], self.isr[i, j] = c, isr
        self.duz = np.array([[y[1], y[2], y[3], y[4]] if y[0] == "d" else [0, 0, 0, 0]
                             for y in yuzeyler])
        self.sil = [(i, y[1], y[2], y[3]) for i, y in enumerate(yuzeyler) if y[0] == "s"]

    def bul(self, p):
        import numpy as np
        v = self.duz[:, :3].dot(p) - self.duz[:, 3]
        for i, x0, y0, r in self.sil:
            v[i] = (p[0] - x0) ** 2 + (p[1] - y0) ** 2 - r * r
        d = v[self.sut] * self.isr
        # '+' taraf: v >= 0; '-' taraf: v < 0  (openmc Halfspace.__contains__)
        tamam = np.where(self.isr > 0, d >= 0.0, np.where(self.isr < 0, d > 0.0, True))
        i = np.flatnonzero(tamam.all(axis=1))
        return self.hucreler[i[0]] if len(i) else None


def _hucre_bul(evren, p):
    if len(evren._cells) > _HIZLI_ESIK:
        kayit = _HIZLI.get(id(evren))
        if kayit is None or kayit[0] is not evren:     # id yeniden kullanilmis olabilir
            try:
                kayit = (evren, _HizliEvren(evren))
            except ValueError:
                kayit = (evren, None)
            _HIZLI.clear()
            _HIZLI[id(evren)] = kayit
        if kayit[1] is not None:
            return kayit[1].bul(p)
    for c in evren._cells.values():
        if c.region is None or tuple(p) in c.region:
            return c
    return None


def nokta_izi(kok, nokta, mat_adi, sayac):
    """Tek noktanin kimlikten bagimsiz izi (bkz. modul notu)."""
    import numpy as np
    evren, p = kok, np.array(nokta, dtype=float)
    kafesler, otelemeler, donmeler, yol = [], [], [], []
    while True:
        hucre = _hucre_bul(evren, p)
        if hucre is None:
            return ("DISARI",)
        yol.append(("evren", evren, hucre))
        if hucre.fill_type in ("material", "void", "distribmat"):
            break
        if hucre.translation is not None:
            p = p - np.asarray(hucre.translation, dtype=float)
            otelemeler.append(_yuvarla(hucre.translation))
        if hucre.rotation is not None:
            p = hucre.rotation_matrix.dot(p)
            donmeler.append(_yuvarla(hucre.rotation))
        if hucre.fill_type == "universe":
            evren = hucre.fill
            continue
        lat = hucre.fill
        idx, p = lat.find_element(p)
        if lat.is_valid_index(idx):
            ki = _kafes_indeksi(lat, idx)
            kafesler.append(ki)
            yol.append(("kafes", lat, ki))
            evren = lat.get_universe(idx)
        else:
            kafesler.append("dis")
            yol.append(("dis", lat, None))
            evren = lat.outer
            if evren is None:
                return ("DISARI",)
    yaprak = yol[-1][2]
    mat = yaprak.fill if yaprak.fill_type == "material" else None
    ad = mat_adi.get(id(mat)) if mat is not None else None
    return (ad, tuple(kafesler), tuple(otelemeler), tuple(donmeler)) + _ornek(yol, yaprak, sayac)


def _ornek(yol, yaprak, sayac):
    """(ornek sirasi, ornek sayisi); kafes dis dolgusundan gecen yolda sira None."""
    toplam = sayac.evren(yol[0][1], yaprak)
    sira = 0
    for tur, nesne, secim in yol:
        if tur == "dis":
            return (None, toplam)
        if tur == "evren":
            for c in nesne._cells.values():
                if c is secim:
                    break
                sira += sayac.hucre(c, yaprak)
        else:
            onek, siralar = sayac.kafes(nesne, yaprak)
            sira += onek[siralar[secim]]
    return (sira, toplam)


# ----------------------------------------------------------------------------
# olcum noktalari
# ----------------------------------------------------------------------------

def hex_merkez(lat, idx):
    """HexLattice (x, alfa) indeksinin yerel merkez koordinati (center = 0)."""
    P = lat.pitch[0]
    ix, ia = idx[0], idx[1]
    if lat.orientation == "y":
        return (ix * P * SQ3 / 2.0, (ia + ix / 2.0) * P)
    return ((ix + ia / 2.0) * P, ia * P * SQ3 / 2.0)


def _kafes_merkezleri(lat):
    import openmc
    if isinstance(lat, openmc.RectLattice):
        nx, ny = lat.shape[:2]
        px, py = lat.pitch[0], lat.pitch[1]
        x0, y0 = lat.lower_left[0], lat.lower_left[1]
        return [(x0 + (i + 0.5) * px, y0 + (j + 0.5) * py, px / 2.0, py / 2.0)
                for i in range(nx) for j in range(ny)]
    P = lat.pitch[0]
    return [hex_merkez(lat, idx) + (P / 2.0, P / 2.0) for idx in lat._natural_indices]


def _kafes_komsu_noktalari(kok, r, zmax, sinir=300):
    """Kok duzeyindeki kafeslerin eleman kose/yuz ortalarinin +/-1e-6 komsulari."""
    cikti = []
    for c in kok._cells.values():
        if c.fill_type != "lattice":
            continue
        t = c.translation if c.translation is not None else (0.0, 0.0, 0.0)
        merkezler = _kafes_merkezleri(c.fill)
        r.shuffle(merkezler)
        for x, y, ax, ay in merkezler[:sinir]:
            z = r.uniform(-zmax, zmax) * 0.999
            for dx, dy in ((ax, 0.0), (-ax, 0.0), (0.0, ay), (0.0, -ay), (ax, ay), (-ax, -ay)):
                for e in (1e-6, -1e-6):
                    cikti.append((x + dx + (e if dx else 0.0) + t[0],
                                  y + dy + (e if dy else 0.0) + t[1], z))
    return cikti


def _yuzey_noktalari(kok, gx, gy, r, zmax):
    """Kok hucrelerinin yuzeyleri uzerinde 8'er nokta, +/-1e-6 cm."""
    import openmc
    yuzeyler = {}
    for c in kok._cells.values():
        if c.region is not None:
            yuzeyler.update(c.region.get_surfaces())
    cikti = []
    olcek = max(gx, gy) / 2.0
    for _sid, s in sorted(yuzeyler.items()):
        for _i in range(8):
            z = r.uniform(-zmax, zmax) * 0.999
            if isinstance(s, openmc.ZCylinder):
                a = r.uniform(0, 2 * math.pi)
                cikti += [(s.x0 + (s.r + e) * math.cos(a), s.y0 + (s.r + e) * math.sin(a), z)
                          for e in (1e-6, -1e-6)]
            elif isinstance(s, openmc.Sphere):
                a, b = r.uniform(0, 2 * math.pi), r.uniform(-1, 1)
                q = math.sqrt(1 - b * b)
                cikti += [((s.r + e) * q * math.cos(a), (s.r + e) * q * math.sin(a), (s.r + e) * b)
                          for e in (1e-6, -1e-6)]
            elif isinstance(s, openmc.ZPlane):
                x, y = r.uniform(-gx / 2, gx / 2) * 0.999, r.uniform(-gy / 2, gy / 2) * 0.999
                cikti += [(x, y, s.z0 + e) for e in (1e-6, -1e-6)]
            elif isinstance(s, (openmc.XPlane, openmc.YPlane, openmc.Plane)):
                a, b, cc, d = s._get_base_coeffs()
                nn = math.hypot(a, b)
                if abs(cc) > 0 or nn == 0:
                    continue
                t = r.uniform(-olcek, olcek)
                x0, y0 = a * d / nn ** 2, b * d / nn ** 2
                cikti += [(x0 - b / nn * t + a / nn * e, y0 + a / nn * t + b / nn * e, z)
                          for e in (1e-6, -1e-6)]
    return [p for p in cikti if abs(p[0]) <= gx / 2 * 0.99999 and abs(p[1]) <= gy / 2 * 0.99999]


def olcum_noktalari(kok, kutu, h, n, tohum=1):
    """Rastgele noktalar + kafes eleman komsulari + kok yuzeylerine yakin noktalar."""
    r = random.Random(tohum)
    gx, gy = kutu
    zmax = (h / 2.0) if h else 1.0
    noktalar = [(r.uniform(-gx / 2, gx / 2) * 0.9999, r.uniform(-gy / 2, gy / 2) * 0.9999,
                 r.uniform(-zmax, zmax) * 0.9999) for _i in range(n)]
    noktalar += _kafes_komsu_noktalari(kok, r, zmax)
    noktalar += _yuzey_noktalari(kok, gx, gy, r, zmax)
    return noktalar


# ----------------------------------------------------------------------------
# parmak izi
# ----------------------------------------------------------------------------

def kok_kur(kurucu_islevi, spec):
    """(kok evren, sinir kutusu, {id(malzeme): ad}); kurucu_islevi(spec,
    nesneler, universeler) eski ya da yeni kor kurucusu."""
    import openmc
    from cekirdek import kurucu
    openmc.reset_auto_ids()
    nesneler, _m, _r = kurucu.malzemeleri_kur(spec)
    sonuc = kurucu_islevi(spec, nesneler, {})
    return sonuc[0], tuple(sonuc[1]), {id(m): ad for ad, m in nesneler.items()}


def model_yuksekligi(spec):
    from cekirdek import sema
    return sema.model_yuksekligi(spec)


def malzeme_ornekleri(kok, mat_adi):
    """Her malzemenin ornek sayisi (num_instances; determine_paths saymasi)."""
    sayac = {}

    def gez(u, carpan):
        for c in u._cells.values():
            if c.fill_type == "material":
                a = mat_adi.get(id(c.fill))
                sayac[a] = sayac.get(a, 0) + carpan
            elif c.fill_type == "universe":
                gez(c.fill, carpan)
            elif c.fill_type == "lattice":
                adet = {}
                for idx in c.fill._natural_indices:
                    uu = c.fill.get_universe(idx)
                    adet[id(uu)] = (uu, adet.get(id(uu), (uu, 0))[1] + 1)
                for uu, k in adet.values():
                    gez(uu, carpan * k)
    gez(kok, 1)
    return sayac


def parmak_izi(kurucu_islevi, spec, n=2000, tohum=1, noktalar=None):
    """{"kutu", "noktalar", "izler", "malzeme_ornekleri"}."""
    kok, kutu, mat_adi = kok_kur(kurucu_islevi, spec)
    if noktalar is None:
        noktalar = olcum_noktalari(kok, kutu, model_yuksekligi(spec), n, tohum)
    sayac = OrnekSayaci()
    return {"kutu": kutu, "noktalar": noktalar,
            "izler": [nokta_izi(kok, p, mat_adi, sayac) for p in noktalar],
            "malzeme_ornekleri": malzeme_ornekleri(kok, mat_adi)}


def iz_farki(a, b, en_cok=4):
    """Iki parmak izinin farki: bos liste = ayni."""
    sorun = []
    if _yuvarla(a["kutu"], 12) != _yuvarla(b["kutu"], 12):
        sorun.append("sinir kutusu %s / %s" % (a["kutu"], b["kutu"]))
    if a["malzeme_ornekleri"] != b["malzeme_ornekleri"]:
        sorun.append("malzeme ornek sayilari %s / %s" % (a["malzeme_ornekleri"],
                                                          b["malzeme_ornekleri"]))
    farkli = [(p, x, y) for p, x, y in zip(a["noktalar"], a["izler"], b["izler"]) if x != y]
    if farkli:
        sorun.append("%d/%d noktada farkli iz; ilk: %s" % (
            len(farkli), len(a["izler"]),
            "; ".join("%s: %s != %s" % f for f in farkli[:en_cok])))
    return sorun
