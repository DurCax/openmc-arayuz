# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/yapici_triso.py  --  Y9: TRISO kafesi (nesne yolu ve betik yolu)
================================================================================
 Yapici arayuzune (geometri/yapici.py) tek yontem ekler: triso_kafesi(parcacik, t,
 matris). Nesne yolu openmc nesneleri kurar; betik yolu AYNI cagrilari yazar:

   rastgele : openmc.model.pack_spheres(radius, region, num_spheres, seed)
              (RSP / CRP; tohum belirleyici, bkz. cekirdek/triso.py)
   duzenli  : basit kubik izgara; betik ayni izgara ifadesini yazar
   ardindan : openmc.model.TRISO(...) listesi ve openmc.model.create_triso_lattice(...)
 Kafes parcaciklari hucre basina yerel listeye boler: parcacik basina arama yerine
 kafes hucresi basina arama (OpenMC belgesi: TRISO modelleri icin sart).
================================================================================
"""

from cekirdek import triso as _t


class NesneTriso(object):
    """NesneYapici'ya karisan TRISO yontemi."""

    def _triso_bolgesi(self, kap):
        import openmc
        if kap.sekil == "pebble":
            return -openmc.Sphere(r=kap.yaricap)
        return (-openmc.ZCylinder(r=kap.yaricap) & +openmc.ZPlane(-kap.yukseklik / 2.0)
                & -openmc.ZPlane(kap.yukseklik / 2.0))

    def triso_kafesi(self, parcacik, t, matris):
        import openmc
        import openmc.model
        kap, r_p = _t.konteyner(t), _t.parcacik_yaricap(t)
        if (t.get("yontem") or "rastgele") == "duzenli":
            oz = _t.yerlesim_ozeti(t)
            merkezler = _t.duzenli_merkezler(kap, r_p, oz.adim, oz.kayma)
        else:
            merkezler = openmc.model.pack_spheres(
                radius=r_p, region=self._triso_bolgesi(kap), num_spheres=_t.hedef_sayi(t),
                seed=int(t.get("tohum") or _t.VARSAYILAN_TOHUM))
        parcaciklar = [openmc.model.TRISO(r_p, fill=parcacik, center=c) for c in merkezler]
        return openmc.model.create_triso_lattice(
            parcaciklar, lower_left=_t.kafes_alt_sol(t), pitch=_t.kafes_adimi(t),
            shape=_t.kafes_bolmesi(t), background=matris)


class BetikTriso(object):
    """BetikYapici'ya karisan TRISO yontemi (nesne yoluyla ayni cagrilar)."""

    def triso_kafesi(self, parcacik, t, matris):
        from cekirdek.geometri.yapici import sayi
        kap, r_p = _t.konteyner(t), _t.parcacik_yaricap(t)
        if (t.get("yontem") or "rastgele") == "duzenli":
            merkezler = self._duzenli_satirlari(t, kap, r_p, sayi)
        else:
            bolge = self._ata("_tb", self._bolge_metni(kap, sayi))
            self.satirlar.append("# rastgele paketleme (RSP/CRP): tohum belirleyici")
            merkezler = self._ata("_tc", "openmc.model.pack_spheres(radius=%s, region=%s, "
                                  "num_spheres=%d, seed=%d)"
                                  % (sayi(r_p), bolge, _t.hedef_sayi(t),
                                     int(t.get("tohum") or _t.VARSAYILAN_TOHUM)))
        trisolar = self._ata("_tt", "[openmc.model.TRISO(%s, fill=%s, center=_c) for _c in %s]"
                             % (sayi(r_p), parcacik, merkezler))
        return self._ata(
            "_k", "openmc.model.create_triso_lattice(%s, lower_left=%s, pitch=%s, shape=%s, "
            "background=%s)" % (trisolar, _tuple(_t.kafes_alt_sol(t), sayi),
                                _tuple(_t.kafes_adimi(t), sayi),
                                _tuple(_t.kafes_bolmesi(t), repr), matris))

    def _bolge_metni(self, kap, sayi):
        if kap.sekil == "pebble":
            return "-openmc.Sphere(r=%s)" % sayi(kap.yaricap)
        return ("(-openmc.ZCylinder(r=%s) & +openmc.ZPlane(%s) & -openmc.ZPlane(%s))"
                % (sayi(kap.yaricap), sayi(-kap.yukseklik / 2.0), sayi(kap.yukseklik / 2.0)))

    def _duzenli_satirlari(self, t, kap, r_p, sayi):
        oz = _t.yerlesim_ozeti(t)
        nx, nz = _t.izgara_sayilari(kap, oz.adim)
        self.satirlar.append("# duzenli (basit kubik) yerlesim: adim %s cm, gercek paketleme %.5f"
                             % (sayi(oz.adim), oz.gercek_pf))
        for ad, n, k in (("_tgx", nx, oz.kayma[0]), ("_tgy", nx, oz.kayma[1]),
                         ("_tgz", nz, oz.kayma[2])):
            self.satirlar.append("%s = [%s * (_i - (%d - 1) / 2.0 + %s) for _i in range(%d)]"
                                 % (ad, sayi(oz.adim), n, sayi(k), n))
        limit = sayi((kap.yaricap - r_p) ** 2)
        if kap.sekil == "pebble":
            kosul = "(_x * _x + _y * _y + _z * _z) <= %s" % limit
        else:
            kosul = ("((_x * _x + _y * _y) <= %s) and (abs(_z) <= %s)"
                     % (limit, sayi(kap.yukseklik / 2.0 - r_p)))
        return self._ata("_tc", "[(_x, _y, _z) for _x in _tgx for _y in _tgy for _z in _tgz "
                         "if %s]" % kosul)


def _tuple(degerler, bicim):
    degerler = list(degerler)
    return "(%s)" % ", ".join(bicim(v) for v in degerler)
