# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/ice_aktar.py  --  OpenMC geometrisinden agaca (donusturebildigi olcude)
================================================================================

   xml_den(geo, malzeme_adlari) -> (agac | None, [not])
       geo: openmc.Geometry (geometry.xml / model.xml'den okunmus).
       malzeme_adlari: {openmc malzeme kimligi: spec adi}.
       agac: {"kok", "parcalar", "gruplar", "cubuklar"} -- "cubuklar" pin
       evrenlerinden turetilen kutuphane cubuklaridir (spec'e eklenir).

 TANINAN DESENLER (kurucunun urettikleri; docs/GEOMETRI_MODELI.md §7):
   * es merkezli pin: -c1 | +c1 -c2 | ... | +cn, hepsi malzeme -> cubuk
   * tek hucreli evren (bolgesiz) -> icerigi
   * RectLattice (merkezli), HexLattice (merkez 0) -> kafes
   * es merkezli kap: ic (-S0 [~delikler]), halkalar (+S(i-1) -S(i)),
     kok disinda '+S(n)' dis hucresi; S: ZCylinder, eksene hizali dikdortgen
     prizma, altigen prizma (merkez 0)
   * delikler: "g:<yerlesim>#<i>" adli hucreler (daire/prizma), otelemeli
     dolgu -> liste yerlesimi; donmus delik (tambur) -> sabit bakis
   * kokteki z dilimleri -> eksenel yigin; dis yuzeyin BC'si -> sinir
   * birden cok kez kullanilan evren -> parca (tek Universe, distribcell)
 TANINMAYAN desen GEREKCEYLE reddedilir (agac None): birlesim/tumleyen
 iceren keyfi bolge, merkezsiz kafes, kafes zarfli altigen tam kor (konum
 hucreleri, R3b), dikey olmayan donme, yuz basina farkli BC ...
 "Kismi ama durust": yanlis bir tahmin sessizce yanlis model uretirdi.
================================================================================
"""

import json
import math
import re

from cekirdek.gunluk import kaydedici

SQ3 = math.sqrt(3.0)
PAY = 1.0e-6
_log = kaydedici(__name__)
_DELIK_ADI = re.compile(r"^g:(.+)#(\d+)$")
HARITA_HARFLERI = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
# tambur emici yayi yoklamasi: aci adimi ve yay kenarindan uzak durma payi (derece)
_YOKLAMA_ADIMI = 1.0
_KENAR_PAYI = 0.5


class Desteklenmez(ValueError):
    """Donusturulemeyen geometri deseni (gerekceli)."""


# ----------------------------------------------------------------------------
# bolge -> sekil atomlari
# ----------------------------------------------------------------------------

def _duzlem(yuzey, taraf):
    """Halfspace -> (nx, ny, d): n.p <= d; z duzlemi -> ('z', z0, taraf)."""
    import openmc
    t = yuzey.type
    if t == "z-plane":
        return ("z", float(yuzey.z0), taraf)
    if t == "x-plane":
        n, d = (1.0, 0.0), float(yuzey.x0)
    elif t == "y-plane":
        n, d = (0.0, 1.0), float(yuzey.y0)
    elif isinstance(yuzey, openmc.Plane) and abs(float(yuzey.c)) < 1e-12:
        L = math.hypot(float(yuzey.a), float(yuzey.b))
        n, d = (float(yuzey.a) / L, float(yuzey.b) / L), float(yuzey.d) / L
    else:
        raise Desteklenmez("desteklenmeyen yüzey türü: %s" % t)
    return (n[0], n[1], d) if taraf == "-" else (-n[0], -n[1], -d)


def _yari_uzaylar(bolge, tumleyen=False):
    """Kesisim -> [(yuzey, taraf)]; Union of halfspaces -> tumleyenin kesisimi."""
    import openmc
    if isinstance(bolge, openmc.Halfspace):
        taraf = bolge.side if not tumleyen else ("+" if bolge.side == "-" else "-")
        return [(bolge.surface, taraf)]
    grup = openmc.Union if tumleyen else openmc.Intersection
    if isinstance(bolge, grup):
        return [h for b in bolge for h in _yari_uzaylar(b, tumleyen)]
    raise Desteklenmez("bölge yapısı çözülemedi (%s)" % type(bolge).__name__)


def _cokgen(duzlemler):
    """Duzlem kisitlarindan kesit (merkez, kesit) -- dikdortgen ya da altigen."""
    if len(duzlemler) == 4:
        xs = [d for nx, ny, d in duzlemler if abs(nx - 1) < PAY and abs(ny) < PAY]
        xa = [-d for nx, ny, d in duzlemler if abs(nx + 1) < PAY and abs(ny) < PAY]
        ys = [d for nx, ny, d in duzlemler if abs(ny - 1) < PAY and abs(nx) < PAY]
        ya = [-d for nx, ny, d in duzlemler if abs(ny + 1) < PAY and abs(nx) < PAY]
        if len(xs) == len(xa) == len(ys) == len(ya) == 1:
            return ((xs[0] + xa[0]) / 2.0, (ys[0] + ya[0]) / 2.0), {
                "sekil": "dikdortgen", "boyut": [xs[0] - xa[0], ys[0] - ya[0]]}
    if len(duzlemler) == 6:
        acilar = sorted(math.degrees(math.atan2(ny, nx)) % 360.0 for nx, ny, _d in duzlemler)
        taban = acilar[0] % 60.0
        yon = "y" if min(taban, 60 - taban) < 1e-4 else ("x" if abs(taban - 30) < 1e-4 else None)
        a = [d for _nx, _ny, d in duzlemler]
        if yon and max(a) - min(a) < PAY * max(1.0, abs(a[0])):
            return (0.0, 0.0), {"sekil": "altigen", "apotem": a[0], "yonelim": yon}
    raise Desteklenmez("düzlemlerden tanınan bir kesit çıkmadı (%d düzlem)" % len(duzlemler))


def _atomlar(bolge):
    """{"ic": (merkez, kesit) | None, "dislar": [(merkez, kesit)], "z": (z0, z1)}."""
    import openmc
    atom = {"ic": None, "dislar": [], "z": [-math.inf, math.inf]}
    if bolge is None:
        return atom
    parcalar = list(bolge) if isinstance(bolge, openmc.Intersection) else [bolge]
    ic_duzlem = []
    for p in parcalar:
        if isinstance(p, openmc.Halfspace) and p.surface.type in ("z-cylinder", "sphere"):
            s = p.surface
            if s.type == "sphere" and any(abs(float(v)) > PAY for v in (s.x0, s.y0, s.z0)):
                raise Desteklenmez("merkezi (0, 0, 0) olmayan küre")
            sekil = "silindir" if s.type == "z-cylinder" else "kure"
            kes = ((float(s.x0), float(s.y0)), {"sekil": sekil, "yaricap": float(s.r)})
            if p.side == "-":
                atom["ic"] = kes
            else:
                atom["dislar"].append(kes)
        elif isinstance(p, openmc.Halfspace):
            d = _duzlem(p.surface, p.side)
            if d[0] == "z":
                atom["z"][0 if d[2] == "+" else 1] = d[1]
            else:
                ic_duzlem.append(d)
        elif isinstance(p, (openmc.Complement, openmc.Union)):
            ic = p.node if isinstance(p, openmc.Complement) else p
            hs = _yari_uzaylar(ic, tumleyen=isinstance(p, openmc.Union))
            atom["dislar"].append(_cokgen([_duzlem(s, t) for s, t in hs]))
        elif isinstance(p, openmc.Intersection):
            ic_duzlem += [_duzlem(s, t) for s, t in _yari_uzaylar(p)]
        else:
            raise Desteklenmez("bölge yapısı çözülemedi (%s)" % type(p).__name__)
    if ic_duzlem:
        if atom["ic"] is not None:
            raise Desteklenmez("hücrede hem silindir hem prizma iç sınırı var")
        atom["ic"] = _cokgen(ic_duzlem)
    atom["z"] = tuple(atom["z"])
    return atom


def _ayni(a, b):
    if a is None or b is None:
        return a is b
    (ma, ka), (mb, kb) = a, b
    if math.hypot(ma[0] - mb[0], ma[1] - mb[1]) > PAY or ka["sekil"] != kb["sekil"]:
        return False
    return all(abs(float(x) - float(y)) <= PAY * max(1.0, abs(float(x)))
               for x, y in zip(_olcu(ka), _olcu(kb))) and ka.get("yonelim") == kb.get("yonelim")


def _olcu(k):
    return k.get("boyut") or [k.get("yaricap") or k.get("apotem")]


def _emici_yayi_dogrula(hucre, r_ic, R, yari):
    """Tambur emici hucresi gercekten yerel +x'te ortalanmis, yari acisi 'yari'
    olan yay mi (geometri/bilesen.tambur kurali)? Iki yari duzlem ters yonde
    secilmisse (emici -x'te) duzlem acisi aynidir; bu yuzden noktasal yoklanir.
    Uymazsa Desteklenmez (yanlis yonlu tambur sessizce kurulmazdi)."""
    r = (r_ic + R) / 2.0
    n = int(round(360.0 / _YOKLAMA_ADIMI))
    for i in range(n):
        fi = -180.0 + (i + 0.5) * _YOKLAMA_ADIMI
        if abs(abs(fi) - yari) < _KENAR_PAYI:
            continue
        t = math.radians(fi)
        icinde = (r * math.cos(t), r * math.sin(t), 0.0) in hucre.region
        if icinde != (abs(fi) < yari):
            raise Desteklenmez("tambur emici yayı yerel +x yönünde ortalanmamış (hücre %d, "
                               "%g° yoklaması)" % (hucre.id, fi))


def _merkezde(sekil):
    return sekil is not None and math.hypot(*sekil[0]) <= PAY


def _alan(k):
    from cekirdek.geometri import kesit as _k
    return _k.alan(k)


# ----------------------------------------------------------------------------
# evren / hucre -> dugum
# ----------------------------------------------------------------------------

class _Donusturucu(object):
    def __init__(self, geo, malzeme_adlari):
        self.geo = geo
        self.adlar = malzeme_adlari
        self.notlar = []
        self.cubuklar = []
        self.tamburlar = []
        self.parcalar = []
        self.parca_adi = {}
        self.kullanim = self._kullanim_say()
        self._harf = {}
        self._adlar = {}           # bilesen adi -> icerik (json); ad cakismasi denetimi

    def _kullanim_say(self):
        import openmc
        sayi = {}
        for c in self.geo.get_all_cells().values():
            dolgu = c.fill
            if isinstance(dolgu, (openmc.Universe, openmc.Lattice)):
                sayi[("u", dolgu.id)] = sayi.get(("u", dolgu.id), 0) + 1
        for lat in self.geo.get_all_lattices().values():
            for u in _kafes_evrenleri(lat) + ([lat.outer] if lat.outer is not None else []):
                sayi[("u", u.id)] = sayi.get(("u", u.id), 0) + 1
        return sayi

    def tekil_ad(self, ad, icerik):
        """Bilesen ad uzayinda (cubuk, tambur, parca) tekil ad. Ayni ad ayni
        icerik -> (ad, False): yeniden kullanilir; ayni ad FARKLI icerik ->
        son ekli yeni ad (bildirilir), (ad_2, True). Eskiden ikinci evren
        sessizce birincisine birlesiyordu."""
        anahtar = json.dumps(icerik, sort_keys=True)
        aday, i = ad, 1
        while aday in self._adlar:
            if self._adlar[aday] == anahtar:
                return aday, False
            i += 1
            aday = "%s_%d" % (ad, i)
        self._adlar[aday] = anahtar
        if aday != ad:
            self.notlar.append("aynı adlı farklı evren: '%s' -> '%s' olarak alındı" % (ad, aday))
        return aday, True

    def malzeme(self, m):
        if m is None:
            return {"tur": "malzeme", "ad": "bosluk"}
        ad = self.adlar.get(m.id)
        if ad is None:
            raise Desteklenmez("malzeme kimliği %d aktarılan malzemelerde yok" % m.id)
        return {"tur": "malzeme", "ad": ad}

    def dolgu(self, fill):
        import openmc
        if fill is None or isinstance(fill, openmc.Material):
            return self.malzeme(fill)
        if isinstance(fill, (openmc.Universe, openmc.Lattice)) and \
                self.kullanim.get(("u", fill.id), 0) > 1:
            return self._parca(fill)
        return self.evren(fill)

    def _parca(self, fill):
        """Cok kullanilan evren: tek parca (ya da kutuphane bileseni) -- onbellekli."""
        if fill.id not in self.parca_adi:
            dugum = self.evren(fill)
            if dugum.get("tur") != "bilesen":        # cubuk/tambur: kutuphane zaten tekil
                ad, yeni = self.tekil_ad(_temiz_ad(fill.name) or "parca_%d" % fill.id,
                                         {"parca": dugum})
                if yeni:
                    self.parcalar.append({"ad": ad, "dugum": dugum})
                dugum = {"tur": "bilesen", "ad": ad}
            self.parca_adi[fill.id] = dugum
        return dict(self.parca_adi[fill.id])

    def evren(self, u):
        import openmc
        if isinstance(u, openmc.RectLattice):
            return self.kare_kafes(u)
        if isinstance(u, openmc.HexLattice):
            return self.altigen_kafes(u)
        hucreler = list(u.cells.values())
        if len(hucreler) == 1 and hucreler[0].region is None:
            return self._donusumlu(hucreler[0], self.dolgu(hucreler[0].fill))
        for taniyici in (self.pin, self.tambur):
            dugum = taniyici(u, hucreler)
            if dugum is not None:
                return dugum
        return self.kap(hucreler, kok=False)

    # --- tambur (geometri/bilesen.tambur deseni) ---
    def tambur(self, u, hucreler):
        """3 hucre: emici (r_ic..R, iki yari duzlemli kama), govde (-R ~emici), +R govde."""
        import openmc
        if len(hucreler) != 3 or not all(isinstance(c.fill, openmc.Material) for c in hucreler):
            return None
        emici = None
        for c in hucreler:
            yuzeyler = list((c.region.get_surfaces() if c.region is not None else {}).values())
            duzlem = [s for s in yuzeyler if s.type == "plane" and abs(float(s.d)) < PAY
                      and abs(float(s.c)) < PAY]
            if len(duzlem) == 2 and isinstance(c.region, openmc.Intersection) and \
                    all(isinstance(b, openmc.Halfspace) for b in c.region):
                emici = (c, duzlem, [s for s in yuzeyler if s.type == "z-cylinder"])
        if emici is None:
            return None
        c, duzlem, silindir = emici
        if not silindir or any(abs(float(s.x0)) > PAY or abs(float(s.y0)) > PAY
                               for s in silindir):
            return None
        R = max(float(s.r) for s in silindir)
        r_ic = min(float(s.r) for s in silindir) if len(silindir) > 1 else 0.0
        yari = abs(math.degrees(math.atan2(float(duzlem[0].a), float(duzlem[0].b))))
        govde = [x for x in hucreler if x is not c]
        if govde[0].fill is not govde[1].fill:
            return None
        _emici_yayi_dogrula(c, r_ic, R, yari)
        tanim = {"yaricap": R, "emici_ic_yaricap": r_ic, "emici_aci": 2.0 * yari,
                 "govde_malzeme": self.malzeme(govde[0].fill)["ad"],
                 "emici_malzeme": self.malzeme(c.fill)["ad"]}
        ad, yeni = self.tekil_ad(_temiz_ad(u.name) or "tambur_%d" % u.id, {"tambur": tanim})
        if yeni:
            self.tamburlar.append(dict(tanim, ad=ad))
        return {"tur": "bilesen", "ad": ad}

    def _donusumlu(self, hucre, dugum):
        t, r = hucre.translation, hucre.rotation
        don = {}
        if t is not None and any(abs(float(v)) > PAY for v in t):
            if abs(float(t[2])) > PAY:
                raise Desteklenmez("z yönünde öteleme desteklenmiyor (hücre %d)" % hucre.id)
            don["oteleme"] = [float(t[0]), float(t[1])]
        if r is not None and any(abs(float(v)) > PAY for v in r):
            if abs(float(r[0])) > PAY or abs(float(r[1])) > PAY:
                raise Desteklenmez("yalnız z ekseni etrafında dönme desteklenir (hücre %d)"
                                   % hucre.id)
            don["donme"] = float(r[2])
        if don:
            if dugum.get("tur") == "malzeme":
                raise Desteklenmez("malzeme dolgulu hücre döndürülemez/ötelenemez")
            dugum = dict(dugum, donusum=don)
        return dugum

    # --- pin ---
    def pin(self, u, hucreler):
        import openmc
        if not all(isinstance(c.fill, openmc.Material) or c.fill is None for c in hucreler):
            return None
        kayit = []
        for c in hucreler:
            try:
                a = _atomlar(c.region)
            except Desteklenmez as e:     # pin degil: kap deseni denenir
                _log.debug("pin deseni değil (hücre %d): %s", c.id, e)
                return None
            if a["z"] != (-math.inf, math.inf):
                return None
            ic = a["ic"]
            dis = a["dislar"]
            if (ic is not None and (ic[1]["sekil"] != "silindir" or not _merkezde(ic))) or \
                    len(dis) > 1 or (dis and (dis[0][1]["sekil"] != "silindir" or
                                              not _merkezde(dis[0]))):
                return None
            kayit.append((ic[1]["yaricap"] if ic else math.inf,
                          dis[0][1]["yaricap"] if dis else 0.0, c))
        kayit.sort(key=lambda k: k[0])
        onceki = 0.0
        for r_dis, r_ic, _c in kayit:
            if abs(r_ic - onceki) > PAY:
                return None
            onceki = r_dis
        if not math.isinf(kayit[-1][0]):
            return None
        bolgeler = [{"r": None if math.isinf(r) else r, "malzeme": self.malzeme(c.fill)["ad"]}
                    for r, _r0, c in kayit]
        ad, yeni = self.tekil_ad(_temiz_ad(u.name) or "cubuk_%d" % u.id, {"cubuk": bolgeler})
        if yeni:
            # semadaki cubuk turu (sema_yapici); yakit/zehir rolu malzemeden gelir
            self.cubuklar.append({"ad": ad, "tur": "silindirik", "bolgeler": bolgeler})
        return {"tur": "bilesen", "ad": ad}

    # --- kafesler ---
    def _harita_harfi(self, dugum, anahtar):
        k = json.dumps(dugum, sort_keys=True)
        if k not in self._harf:
            kullanilan = set(anahtar)
            h = next((h for h in HARITA_HARFLERI if h not in kullanilan or
                      anahtar.get(h) == dugum), None)
            if h is None:
                raise Desteklenmez("kafeste %d'den çok farklı evren var; harita harfleri "
                                   "yetmiyor" % len(HARITA_HARFLERI))
            self._harf[k] = h
        h = self._harf[k]
        anahtar[h] = dugum
        return h

    def kare_kafes(self, lat):
        P = [float(v) for v in lat.pitch][:2]
        if abs(P[0] - P[1]) > PAY:
            raise Desteklenmez("kare olmayan kafes adımı (%g × %g)" % tuple(P))
        ny, nx = len(lat.universes), len(lat.universes[0])
        ll = [float(v) for v in lat.lower_left][:2]
        if abs(ll[0] + P[0] * nx / 2.0) > PAY or abs(ll[1] + P[0] * ny / 2.0) > PAY:
            raise Desteklenmez("merkezlenmemiş kare kafes (lower_left %s)" % (ll,))
        self._harf = {}
        anahtar, harita = {}, []
        for satir in lat.universes:
            harita.append("".join(self._harita_harfi(self.dolgu(u), anahtar) for u in satir))
        return {"tur": "kafes", "id": _temiz_ad(lat.name) or "kafes_%d" % lat.id,
                "sekil": "kare", "adim": P[0], "boyut": [nx, ny], "harita": harita,
                "anahtar": anahtar, "dis": self.dolgu(lat.outer) if lat.outer is not None
                else {"tur": "malzeme", "ad": "bosluk"}}

    def altigen_kafes(self, lat):
        if any(abs(float(v)) > PAY for v in list(lat.center)[:2]):
            raise Desteklenmez("merkezi (0, 0) olmayan altıgen kafes")
        if getattr(lat, "num_axial", None):
            raise Desteklenmez("eksenel katmanlı altıgen kafes desteklenmiyor")
        self._harf = {}
        anahtar = {}
        harita = ["".join(self._harita_harfi(self.dolgu(u), anahtar) for u in halka)
                  for halka in lat.universes]
        return {"tur": "kafes", "id": _temiz_ad(lat.name) or "kafes_%d" % lat.id,
                "sekil": "altigen", "adim": float(lat.pitch[0]),
                "halka_sayisi": len(lat.universes), "yonelim": lat.orientation,
                "harita": harita, "anahtar": anahtar,
                "dis": self.dolgu(lat.outer) if lat.outer is not None
                else {"tur": "malzeme", "ad": "bosluk"}}

    # --- kap ---
    def kap(self, hucreler, kok):
        from cekirdek.geometri.ice_aktar_kap import kap_dugumu
        return kap_dugumu(self, hucreler, kok)


def _kafes_evrenleri(lat):
    import openmc
    cikti = []

    def gez(x):
        if isinstance(x, (list, tuple)):
            for y in x:
                gez(y)
        elif isinstance(x, openmc.Universe):
            cikti.append(x)
    gez(list(lat.universes))
    return cikti


def _temiz_ad(ad):
    ad = (ad or "").strip()
    if ad.startswith("g:"):
        ad = ad[2:]
    ad = re.sub(r"[^0-9a-zA-Z_]+", "_", ad).strip("_")
    return ad or None


def xml_den(geo, malzeme_adlari):
    """openmc.Geometry -> (agac | None, [not]). Bkz. modul notu."""
    d = _Donusturucu(geo, malzeme_adlari)
    try:
        kok = d.kap(list(geo.root_universe.cells.values()), kok=True)
    except Desteklenmez as e:
        return None, d.notlar + ["geometri içe aktarılamadı: %s" % e]
    agac = {"kok": kok, "parcalar": d.parcalar, "gruplar": [], "cubuklar": d.cubuklar,
            "tamburlar": d.tamburlar}
    d.notlar.insert(0, "geometri ağaca dönüştürüldü: %d parça, %d çubuk tanımı"
                    % (len(d.parcalar), len(d.cubuklar)))
    return agac, d.notlar
