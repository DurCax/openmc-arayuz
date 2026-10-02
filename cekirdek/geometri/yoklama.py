# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/yoklama.py  --  Geometri yoklamasi: ortusme ve bosluk (M1, §8)
================================================================================

   nokta_yoklama(geo, n, tohum, kutu, icinde) -> YoklamaSonucu
       Kurulan openmc.Geometry'de rastgele n nokta: her noktada ulasilan HER
       evrende noktayi iceren hucre sayilir. 0 -> bosluk (tanimsiz nokta =
       kayip parcacik), 1'den fazla -> ortusme. Kokte 'icinde(x, y)' disinda
       kalan nokta modelin disidir (sayilmaz).
   yokla(spec, n, tohum) -> YoklamaSonucu
       spec -> kurucu.kur -> nokta_yoklama; kutu = sinir kutusu x yukseklik,
       dis sinir = en dis kesit (kafes zarfli kokte konum prizmalari).
       Ilk 5 sorunlu nokta hucre yoluyla (GeometriDizini) raporlanir.
   derin_dogrulama(spec, dizin, parcacik, cevrim) -> (tamam, metin)
       Kisa "openmc --geometry-debug" kosusu: OpenMC her adimda hucre
       ortusmesini denetler ("Overlapping cells detected" ile durur).

 Python bolge denetimi (Region.__contains__) OpenMC'nin kendi yuzey
 esitsizlikleridir; hucre arama C++ ile ayni kurali izler (region None =
 her yer).
================================================================================
"""

import random
from collections import namedtuple

import numpy as np
from cekirdek.ceviri import _, pgettext
from cekirdek.uygunluk_bellek import Bellek, icerik_anahtari

YoklamaSonucu = namedtuple("YoklamaSonucu", "n bosluklar ortusmeler")
RAPOR_SINIRI = 5


_DERINLIK_SINIRI = 60      # evren icine inis siniri (dongu korumasi)


# ----------------------------------------------------------------------------
# toplu bolge degerlendirmesi (H1b): yuzey denklemi nokta dizisinde BIR kez
#   openmc Region.__contains__ her noktada her hucrenin agacini yurur; ayni
#   yuzey komsu hucrelerde tekrar tekrar hesaplanir (SFR: 600 nokta 11.5 s).
#   Burada bir evrenin butun noktalari birlikte degerlendirilir: her yuzey
#   numpy dizisinde bir kez (bellek: id(yuzey) -> deger dizisi). Aritmetik
#   openmc'nin kendi evaluate()'idir (ayni islem sirasi, IEEE ayni sonuc);
#   yalniz eleman bazli evaluate'i olan yuzey turleri dizide calistirilir,
#   digerleri nokta nokta (tekil yedek yol). Halfspace kurali openmc ile ayni:
#   '+' -> deger >= 0, '-' -> deger < 0.
# ----------------------------------------------------------------------------

_VEKTOREL_YUZEY_ADLARI = ("Plane", "XPlane", "YPlane", "ZPlane", "XCylinder",
                          "YCylinder", "ZCylinder", "Sphere")
_vektorel = []


def _vektorel_turler():
    """evaluate()'i eleman bazli olan openmc yuzey siniflari (tembel: openmc)."""
    if not _vektorel:
        import openmc
        _vektorel.append(frozenset(getattr(openmc, a) for a in _VEKTOREL_YUZEY_ADLARI))
    return _vektorel[0]


def _yuzey_degeri(yuzey, xyz, P, bellek):
    deger = bellek.get(id(yuzey))
    if deger is None:
        if type(yuzey) in _vektorel_turler():
            deger = np.broadcast_to(yuzey.evaluate(xyz), (len(P),))
        else:
            deger = np.array([yuzey.evaluate(tuple(float(v) for v in p)) for p in P],
                             dtype=float)
        bellek[id(yuzey)] = deger
    return deger


def bolge_maskesi(bolge, xyz, P, bellek):
    """openmc bolgesi -> P'nin (k x 3) her satiri icin 'nokta in bolge' (bool dizisi).
    xyz = (P[:, 0], P[:, 1], P[:, 2]); bellek: ayni noktalar icin yuzey degerleri."""
    import openmc
    if isinstance(bolge, openmc.Halfspace):
        deger = _yuzey_degeri(bolge.surface, xyz, P, bellek)
        return deger >= 0.0 if bolge.side == "+" else deger < 0.0
    if isinstance(bolge, openmc.Intersection):
        maske = np.ones(len(P), dtype=bool)
        for alt in bolge:
            maske &= bolge_maskesi(alt, xyz, P, bellek)
        return maske
    if isinstance(bolge, openmc.Union):
        maske = np.zeros(len(P), dtype=bool)
        for alt in bolge:
            maske |= bolge_maskesi(alt, xyz, P, bellek)
        return maske
    if isinstance(bolge, openmc.Complement):
        return ~bolge_maskesi(bolge.node, xyz, P, bellek)
    return np.array([tuple(float(v) for v in p) in bolge for p in P], dtype=bool)


def _yerel(hucre, p):
    if hucre.translation is not None:
        p = p - np.asarray(hucre.translation, dtype=float)
    if hucre.rotation is not None:
        p = np.asarray(hucre.rotation_matrix, dtype=float) @ p
    return p


def _iceren_matrisi(hucreler, P):
    """(hucre sayisi x nokta) bool: hucre noktayi iceriyor mu (region None = her yer)."""
    xyz, bellek = (P[:, 0], P[:, 1], P[:, 2]), {}
    satirlar = [np.ones(len(P), dtype=bool) if c.region is None
                else bolge_maskesi(c.region, xyz, P, bellek) for c in hucreler]
    return np.vstack(satirlar) if satirlar else np.zeros((0, len(P)), dtype=bool)


def _bos_durum(p, kok, icinde):
    if kok and icinde is not None and not icinde(p[0], p[1]):
        return "dis"
    return "dis" if kok and icinde is None else "bosluk"


def _inis(hucre, p):
    """Tek iceren hucreden sonraki adim: (alt evren | None, yeni nokta, durum)."""
    if hucre.fill_type == "universe":
        return hucre.fill, _yerel(hucre, p), None
    if hucre.fill_type == "lattice":
        kafes = hucre.fill
        idx, p = kafes.find_element(_yerel(hucre, p))
        if kafes.is_valid_index(idx):
            return kafes.get_universe(idx), p, None
        if kafes.outer is not None:
            return kafes.outer, p, None
        return None, p, "bosluk"
    return None, p, "tamam"


def _in_toplu(evren, P, kok, icinde, derinlik=0):
    """P (k x 3) -> [(durum, [hucre], nokta)] her satir icin (bkz. _in)."""
    if derinlik >= _DERINLIK_SINIRI:
        return [("tamam", [], p) for p in P]
    hucreler = list(evren.cells.values())
    matris = _iceren_matrisi(hucreler, P)
    sonuc, gruplar = [None] * len(P), {}
    for i, p in enumerate(P):
        icerenler = [hucreler[j] for j in np.flatnonzero(matris[:, i])]
        if len(icerenler) != 1:
            sonuc[i] = ("ortusme", icerenler, p) if icerenler else \
                (_bos_durum(p, kok, icinde), [], p)
            continue
        alt, q, durum = _inis(icerenler[0], p)
        if alt is None:
            sonuc[i] = (durum, icerenler, q)
            continue
        grup = gruplar.setdefault((id(icerenler[0]), id(alt)), (icerenler[0], alt, [], []))
        grup[2].append(i)
        grup[3].append(q)
    for hucre, alt, sira, noktalar in gruplar.values():
        alt_sonuc = _in_toplu(alt, np.array(noktalar, dtype=float), False, icinde,
                              derinlik + 1)
        for i, (durum, yol, q) in zip(sira, alt_sonuc):
            sonuc[i] = (durum, [hucre] + yol, q)
    return sonuc


def _in(evren, p, kok, icinde, derinlik=0):
    """(durum, [hucre], nokta) -- durum: 'tamam' | 'bosluk' | 'ortusme' | 'dis'."""
    return _in_toplu(evren, np.array([p], dtype=float), kok, icinde, derinlik)[0]


def nokta_yoklama(geo, n=20000, tohum=1, kutu=None, icinde=None):
    """Rastgele noktalarda ortusme/bosluk sayimi (bkz. modul notu)."""
    if kutu is None:
        alt, ust = geo.bounding_box
        kutu = (tuple(alt), tuple(ust))
    (x0, y0, z0), (x1, y1, z1) = kutu
    rnd = random.Random(tohum)
    P = np.array([[rnd.uniform(x0, x1), rnd.uniform(y0, y1),
                   rnd.uniform(z0, z1) if z1 > z0 else z0] for _i in range(int(n))],
                 dtype=float).reshape(-1, 3)
    bosluk, ortusme, icerde = [], [], 0
    for p, (durum, hucreler, _q) in zip(P, _in_toplu(geo.root_universe, P, True, icinde)):
        if durum == "dis":
            continue
        icerde += 1
        if durum == "bosluk":
            bosluk.append((tuple(p), hucreler))
        elif durum == "ortusme":
            ortusme.append((tuple(p), hucreler))
    return YoklamaSonucu(icerde, bosluk, ortusme)


def _dis_sinir(m):
    """Kokun dis siniri (x, y) -> bool; kafes zarfli kokte konum prizmalari."""
    from cekirdek.geometri import kesit as _k
    from cekirdek.geometri.gezinti import eleman_kesiti, kafes_konumlari
    from cekirdek.geometri.kap import en_dis_kesit
    kok = m.kok
    dis = en_dis_kesit(kok)
    if dis.get("sekil") != "kafes_zarfi":
        return lambda x, y: _k.icinde(dis, x, y, pay=-1.0e-7)
    ic = kok.get("ic") or {}
    kafes = ic.get("icerik") if ic.get("tur") == "eksenel" else ic
    el = eleman_kesiti("altigen", kafes["adim"], kafes.get("yonelim", "y"))
    merkezler = [c for _i, c, _h in kafes_konumlari(kafes)]
    return lambda x, y: any(_k.icinde(el, x, y, merkez=c, pay=-1.0e-7) for c in merkezler)


_YOKLAMALAR = Bellek("yoklama")


def yokla(spec, n=20000, tohum=1):
    """spec -> (YoklamaSonucu, [okunur sorun metni]) (ilk RAPOR_SINIRI sorun).
    H1b: model onbellek.kur_onbellekli'den (salt okunur: yalniz bolge/kafes
    sorgulanir); sonuc icerik anahtariyla bellekte (degismez demetler), metin
    her cagrida etkin dilde uretilir."""
    anahtar = icerik_anahtari([spec, int(n), tohum])
    sonuc, dizin = _YOKLAMALAR.al(anahtar, lambda: _yokla_hesapla(spec, n, tohum))
    return sonuc, _metinler(sonuc, dizin)


def _yokla_hesapla(spec, n, tohum):
    from cekirdek import geometri, onbellek
    model, bilgi = onbellek.kur_onbellekli(spec)
    m = geometri.model(spec)
    gx, gy = geometri.sinir_kutusu(m)
    h = geometri.yukseklik(m)
    z = h / 2.0 * (1.0 - 1.0e-9) if h else 0.0
    kutu = ((-gx / 2.0, -gy / 2.0, -z), (gx / 2.0, gy / 2.0, z))
    s = nokta_yoklama(model.geometry, n, tohum, kutu, _dis_sinir(m))
    donmus = YoklamaSonucu(s.n, tuple((p, tuple(h)) for p, h in s.bosluklar),
                           tuple((p, tuple(h)) for p, h in s.ortusmeler))
    return donmus, bilgi.get("geometri_dizini")


def _hucre_adi(h, dizin):
    yol = (getattr(dizin, "hucre_yolu", None) or {}).get(h.id)
    return yol or h.name or _("hücre %d") % h.id


def _metinler(sonuc, dizin):
    metinler = []
    for tur, liste in ((pgettext("yoklama", "örtüşme"), sonuc.ortusmeler),
                       (pgettext("yoklama", "boşluk"), sonuc.bosluklar)):
        for p, hucreler in liste[:RAPOR_SINIRI]:
            yol = " > ".join(_hucre_adi(h, dizin) for h in hucreler) or _("kök")
            metinler.append("%s (%.4g, %.4g, %.4g): %s" % (tur, p[0], p[1], p[2], yol))
    return metinler


def derin_dogrulama(spec, dizin, parcacik=500, cevrim=3):
    """
    Kisa 'openmc --geometry-debug' kosusu (ozdeger, az parcacik). DONER
    (tamam, metin): tamam False ise metin OpenMC'nin ortusme/kayip parcacik
    iletisidir. Nukleer veri gerektirir.
    """
    import os
    import openmc
    from cekirdek import kurucu
    model, _b = kurucu.kur(spec)
    model.tallies = openmc.Tallies()
    s = model.settings
    s.particles, s.batches = int(parcacik), int(cevrim)
    s.inactive = min(int(getattr(s, "inactive", 0) or 0), int(cevrim) - 1)
    os.makedirs(dizin, exist_ok=True)
    model.export_to_model_xml(os.path.join(dizin, "model.xml"))
    try:
        openmc.run(cwd=dizin, geometry_debug=True, output=False,
                   path_input=os.path.join(dizin, "model.xml"))
    except RuntimeError as e:
        return False, str(e).strip().splitlines()[-1] if str(e).strip() else repr(e)
    return True, _("geometri hata ayıklama koşusu temiz (%d × %d parçacık)") % (
        int(parcacik), int(cevrim))


def oran_metni(sonuc):
    """'n noktada k ortusme, b bosluk' ozeti."""
    return _("%d noktada %d örtüşme, %d boşluk") % (sonuc.n, len(sonuc.ortusmeler),
                                                 len(sonuc.bosluklar))
