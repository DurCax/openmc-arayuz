# -*- coding: utf-8 -*-
"""
 kod_uret/tukenme_arama.py  --  betikte tukenme sirasinda kritiklik aramasi (v3 Y4)

 cekirdek/tukenme_arama.py'nin betik karsiligi; betik cekirdek'i ice AKTARMAZ.
   bor    su bilesimi sabit kutle yogunlugunda bor ppm'ine gore DOGRUSALDIR
          (agirlikca kesirler ppm ile dogrusal; N_i = rho N_A w_i / A_i).
          Betik iki ppm > 0 noktasindaki bilesimi (cekirdekle AYNI tariften,
          tarama "bor_ppm") gomer ve aradegerler; test_y4_betik dogrusalligi
          cekirdegin tam tarifiyle karsilastirir.
   cubuk  cekirdek/tukenme_arama.cubuk_islevi ile ayni donusum (emici +
          izleyici ic evrene, dis hucrenin translation'i uc konumu).
"""

from cekirdek.kod_uret.ad import _ad


def bor_tablosu(spec, hedef, ust_ppm):
    """(y0, egim): {nuklid: atom/b-cm} 0 ppm'e dogrusal uzatma ve ppm basina degisim.
    Iki nokta ppm > 0 dalindan (ust/2, ust): tarif ppm = 0'da agirlikca degil
    atomca H2O'dur (malzeme_kutup.su) ve H yogunlugu 1.2e-5 oraninda farklidir;
    dogrusal tablo bu kucuk sicramayi tasimaz (kilavuzda yazili)."""
    from cekirdek import tukenme_arama
    ya = tukenme_arama.bor_yogunluklari(spec, hedef, ust_ppm / 2.0)
    yb = tukenme_arama.bor_yogunluklari(spec, hedef, ust_ppm)
    adlar = sorted(set(ya) | set(yb))
    egim = {n: (yb.get(n, 0.0) - ya.get(n, 0.0)) / (ust_ppm / 2.0) for n in adlar}
    return {n: yb.get(n, 0.0) - ust_ppm * egim[n] for n in adlar}, egim


def arama_satirlari(spec, arama, satirlar):
    """_arama_hazirla(model) islevini betige yazar."""
    satirlar.append("")
    satirlar.append("# Kritiklik araması (OpenMC Integrator.add_keff_search_control):")
    satirlar.append("# her güçlü adımın başında k = 1 olacak değer aranır (Model.keff_search).")
    if arama.tur == "bor":
        _bor_satirlari(spec, arama, satirlar)
    else:
        _cubuk_satirlari(spec, arama, satirlar)


def _bor_satirlari(spec, arama, satirlar):
    ust = max(arama.alt, arama.ust)
    y0, egim = bor_tablosu(spec, arama.hedef, ust)
    satirlar.append("_BOR_Y0 = %r   # atom/b-cm, 0 ppm" % y0)
    satirlar.append("_BOR_EGIM = %r   # atom/b-cm / ppm" % egim)
    satirlar.append("")
    satirlar.append("")
    satirlar.append("def _bor_yogunluk(ppm):")
    satirlar.append("    return {n: _BOR_Y0[n] + ppm * _BOR_EGIM[n] for n in _BOR_Y0}")
    satirlar.append("")
    satirlar.append("")
    satirlar.append("def _arama_hazirla(model):")
    satirlar.append('    """Su %r ppm borla kurulur (B10/B11 openmc.lib\'de yüklü olsun)."""' % ust)
    satirlar.append("    m = %s" % _ad(arama.hedef))
    satirlar.append("    y = _bor_yogunluk(%r)" % ust)
    satirlar.append("    for n in list(m.get_nuclides()):")
    satirlar.append("        m.remove_nuclide(n)")
    satirlar.append("    for n, v in y.items():")
    satirlar.append("        m.add_nuclide(n, v, 'ao')")
    satirlar.append("    m.set_density('atom/b-cm', sum(y.values()))")
    satirlar.append("")
    satirlar.append("    def ayarla(ppm):")
    satirlar.append("        import openmc.lib")
    satirlar.append("        y = _bor_yogunluk(max(float(ppm), 0.0))")
    satirlar.append("        openmc.lib.materials[m.id].set_densities(list(y), list(y.values()))")
    satirlar.append("    return ayarla")


_CUBUK_ISLEVI = '''

def _arama_hazirla(model):
    """Kontrol çubuğu evrenlerinde emici + izleyici hücreleri hareketli bir iç
    evrene taşınır; dış hücrenin translation'ı ucun z konumudur."""
    emici, izleyici = {emici}, {izleyici}
    z_alt, z_ust = {z_alt!r}, {z_ust!r}
    emici.depletable = False   # hareket eden emicinin hacmi sabit değil
    idler = []
    for u in model.geometry.get_all_universes().values():
        hucreler = list(u.cells.values())
        for a in [h for h in hucreler if h.fill is emici]:
            for f in [h for h in hucreler if h.fill is izleyici and h is not a]:
                za = {{s.id: s for s in a.region.get_surfaces().values()
                      if isinstance(s, openmc.ZPlane)}}
                ortak = [s for i, s in za.items() if i in f.region.get_surfaces()]
                if len(ortak) != 1:
                    continue
                uc = ortak[0]
                parca = ([p for p in a.region if not (isinstance(p, openmc.Halfspace)
                                                     and p.surface is uc)]
                         if not isinstance(a.region, openmc.Halfspace) else [])
                sifir = openmc.ZPlane(0.0)
                ic = openmc.Universe(cells=[openmc.Cell(fill=emici, region=+sifir),
                                            openmc.Cell(fill=izleyici, region=-sifir)])
                bolge = (openmc.Intersection(parca) if len(parca) > 1
                         else (parca[0] if parca else None))
                dis = openmc.Cell(fill=ic, region=bolge) if bolge is not None else openmc.Cell(fill=ic)
                dis.translation = (0.0, 0.0, uc.z0)
                u.remove_cell(a)
                u.remove_cell(f)
                u.add_cell(dis)
                idler.append(dis.id)
    model.materials = openmc.Materials(model.geometry.get_all_materials().values())

    def ayarla(daldirma):
        import openmc.lib
        d = min(max(float(daldirma), 0.0), 100.0)
        z = z_ust - d / 100.0 * (z_ust - z_alt)
        for i in idler:
            openmc.lib.cells[i].translation = (0.0, 0.0, z)
    return ayarla'''


def _cubuk_satirlari(spec, arama, satirlar):
    from cekirdek import sema, tukenme_arama
    c = sema.cubuk_bul(spec, arama.hedef)
    emici = c["bolgeler"][int(c.get("emici_bolge") or 0)]["malzeme"]
    z_alt, z_ust = tukenme_arama._aktif_aralik(spec)
    satirlar.append("# Çubuk: %s (daldırma %%; 0 = çekilmiş, 100 = tam dalmış)" % arama.hedef)
    satirlar.extend(_CUBUK_ISLEVI.format(emici=_ad(emici), izleyici=_ad(c["izleyici_malzeme"]),
                                         z_alt=float(z_alt), z_ust=float(z_ust)).split("\n"))
