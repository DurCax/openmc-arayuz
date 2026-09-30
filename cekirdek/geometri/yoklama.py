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

import math
import random
from collections import namedtuple

import numpy as np

YoklamaSonucu = namedtuple("YoklamaSonucu", "n bosluklar ortusmeler")
RAPOR_SINIRI = 5


def _iceren_hucreler(evren, p):
    nokta = tuple(float(v) for v in p)
    return [c for c in evren.cells.values() if c.region is None or nokta in c.region]


def _yerel(hucre, p):
    if hucre.translation is not None:
        p = p - np.asarray(hucre.translation, dtype=float)
    if hucre.rotation is not None:
        p = np.asarray(hucre.rotation_matrix, dtype=float) @ p
    return p


def _in(evren, p, kok, icinde, derinlik=0):
    """(durum, [hucre], nokta) -- durum: 'tamam' | 'bosluk' | 'ortusme' | 'dis'."""
    yol = []
    while derinlik < 60:
        icerenler = _iceren_hucreler(evren, p)
        if not icerenler:
            if kok and icinde is not None and not icinde(p[0], p[1]):
                return "dis", yol, p
            return ("dis" if kok and icinde is None else "bosluk"), yol, p
        if len(icerenler) > 1:
            return "ortusme", yol + icerenler, p
        hucre = icerenler[0]
        yol.append(hucre)
        kok = False
        if hucre.fill_type == "universe":
            p, evren = _yerel(hucre, p), hucre.fill
        elif hucre.fill_type == "lattice":
            p = _yerel(hucre, p)
            kafes = hucre.fill
            idx, p = kafes.find_element(p)
            if kafes.is_valid_index(idx):
                evren = kafes.get_universe(idx)
            elif kafes.outer is not None:
                evren = kafes.outer
            else:
                return "bosluk", yol, p
        else:
            return "tamam", yol, p
        derinlik += 1
    return "tamam", yol, p


def nokta_yoklama(geo, n=20000, tohum=1, kutu=None, icinde=None):
    """Rastgele noktalarda ortusme/bosluk sayimi (bkz. modul notu)."""
    if kutu is None:
        alt, ust = geo.bounding_box
        kutu = (tuple(alt), tuple(ust))
    (x0, y0, z0), (x1, y1, z1) = kutu
    rnd = random.Random(tohum)
    bosluk, ortusme, icerde = [], [], 0
    for _i in range(int(n)):
        p = np.array([rnd.uniform(x0, x1), rnd.uniform(y0, y1),
                      rnd.uniform(z0, z1) if z1 > z0 else z0])
        durum, hucreler, _yerel_p = _in(geo.root_universe, p, True, icinde)
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


def yokla(spec, n=20000, tohum=1):
    """spec -> (YoklamaSonucu, [okunur sorun metni]) (ilk RAPOR_SINIRI sorun)."""
    from cekirdek import geometri, kurucu
    model, bilgi = kurucu.kur(spec)
    m = geometri.model(spec)
    gx, gy = geometri.sinir_kutusu(m)
    h = geometri.yukseklik(m)
    z = h / 2.0 * (1.0 - 1.0e-9) if h else 0.0
    kutu = ((-gx / 2.0, -gy / 2.0, -z), (gx / 2.0, gy / 2.0, z))
    sonuc = nokta_yoklama(model.geometry, n, tohum, kutu, _dis_sinir(m))
    dizin = bilgi.get("geometri_dizini")
    return sonuc, _metinler(sonuc, dizin)


def _hucre_adi(h, dizin):
    yol = (getattr(dizin, "hucre_yolu", None) or {}).get(h.id)
    return yol or h.name or "hücre %d" % h.id


def _metinler(sonuc, dizin):
    metinler = []
    for tur, liste in (("örtüşme", sonuc.ortusmeler), ("boşluk", sonuc.bosluklar)):
        for p, hucreler in liste[:RAPOR_SINIRI]:
            yol = " > ".join(_hucre_adi(h, dizin) for h in hucreler) or "kök"
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
    return True, "geometri hata ayıklama koşusu temiz (%d × %d parçacık)" % (
        int(parcacik), int(cevrim))


def oran_metni(sonuc):
    """'n noktada k ortusme, b bosluk' ozeti."""
    return "%d noktada %d örtüşme, %d boşluk" % (sonuc.n, len(sonuc.ortusmeler),
                                                 len(sonuc.bosluklar))


def guven_siniri(n, oran=0.0):
    """Hic sorun gorulmezse sorunlu hacim kesrinin %95 ust siniri (3/n kurali)."""
    return 3.0 / n if n and not oran else math.nan
