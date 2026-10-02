# -*- coding: utf-8 -*-
"""
 kod_uret/tukenme.py  --  betik tukenme (yanma) bolumu

 Hacimler cekirdek/tukenme.py'deki AYNI islevden gelir.
"""

from cekirdek import sema
from cekirdek.kod_uret.ad import _ad, _f, _bolum, _mat_ifade  # noqa: F401
from cekirdek.ceviri import _


def _tukenme(spec, satirlar):
    """
    Tukenme bolumu. Hacimler cekirdek/tukenme.py'deki AYNI fonksiyondan gelir:
    ayni sayiyi iki ayri yoldan hesaplayan iki kod er ya da gec ayrisir
    (eksenel katmanlamada tam bu yuzden 1300 pcm'lik bir fark cikmisti).
    DONER tukenme bolumu yazildi mi.
    """
    t = spec.get("tukenme") or {}
    if not t.get("var"):
        return False
    from cekirdek import tukenme as _tk
    from cekirdek.geometri.yapici import yorum_metni   # tembel: openmc (H1b)
    zs = _tk.zincir_secimi(spec)
    # kosucuyla (tukenme.hazirla) AYNI hacim kaynagi: agac modunda kesin
    # olmayan hacim stokastik hacme duser; zorunlu malzemenin hacmi yoksa
    # betik de uretilmez (eskiden 'm.volume = None' yazilirdi)
    hv, _atlanan, stokastik = _tk._hazir_hacimler(spec)
    eksik = [a for a, v in hv.items() if not v["hacim"]]
    if eksik:
        raise ValueError(
            _("hacmi hesaplanamayan yanabilir malzeme: %s (%s). Tükenme betiği kesin "
            "hacim gerektirir.") % (", ".join(eksik), "; ".join(hv[a]["ayrinti"] for a in eksik)))
    _bolum(satirlar, 6, "TÜKENME (YANMA)")
    satirlar.append("")
    if stokastik:
        satirlar.append("# Stokastik hacim (OpenMC VolumeCalculation; koşucuyla aynı hesap): %s"
                        % yorum_metni(", ".join(sorted(stokastik))))
    satirlar.append("# Yanabilir malzemeler ve analitik hacimleri. Hacim yanlışsa yanma")
    satirlar.append("# hızı aynı oranda yanlış olur ve k-eff'te iz bırakmaz.")
    for ad, v in hv.items():
        satirlar.append("%s.depletable = True" % _ad(ad))
        satirlar.append("%s.volume = %r   # cm³ — %s" % (_ad(ad), v["hacim"], yorum_metni(v["ayrinti"])))
    ayir = bool(t.get("malzemeleri_ayir"))
    if ayir:
        _ornek_ayirma_satirlari(spec, hv, satirlar)
    satirlar.append("")
    satirlar.append("# Zincir: %s" % yorum_metni(zs["gerekce"]))
    satirlar.append("# Bu yol bu makineye aittir; başka yerde OPENMC_CHAIN_FILE'a bakın.")
    satirlar.append("TUKENME_ZINCIRI = %r" % zs["yol"])
    _plan_satirlari(t, satirlar)
    from cekirdek import tukenme_ayar as _ta
    arama = _ta.kritik_arama(t)
    if arama.var:
        from cekirdek.kod_uret.tukenme_arama import arama_satirlari
        arama_satirlari(spec, arama, satirlar)
    satirlar.append("")
    satirlar.append("")
    satirlar.append("def tukenme_kos():")
    satirlar.append('    """Yanma hesabı; depletion_results.h5 üretir."""')
    satirlar.append("    import openmc.deplete")
    if ayir:
        satirlar.append("    _ornekleri_ayir(model)   # örnek başına kesin hacim (aşağıda False)")
    if arama.var:
        satirlar.append("    arama_islevi = _arama_hazirla(model)   # kritiklik araması (yukarıda)")
    _operator_satirlari(t, zs, satirlar)
    _entegrator_satirlari(t, satirlar)
    if arama.var:
        satirlar.append("    integ.add_keff_search_control(")
        satirlar.append("        arama_islevi, %r, %r, %r, target=1.0, k_tol=%r, sigma_final=%r)"
                        % (arama.alt, arama.ust, list(arama.sinir), arama.k_tol, arama.sigma))
    satirlar.append("    # write_rates: reaksiyon hızları kaydedilir (sürdürme doğru başlasın)")
    satirlar.append("    integ.integrate(write_rates=%r)" % (not ayir))
    satirlar.append("    return 'depletion_results.h5'")
    return True


def _plan_satirlari(t, satirlar):
    """Zaman plani: yanma + sogutma (guc 0) -- tukenme_ayar.zaman_plani ile AYNI."""
    from cekirdek import tukenme_ayar as _ta
    adimlar, guc = _ta.zaman_plani(t)
    satirlar.append("# Adımlar (değer, birim); soğuma adımlarında güç 0: OpenMC transport koşmaz,")
    satirlar.append("# yalnız bozunma çözülür.")
    satirlar.append("TUKENME_ADIMLARI = %r" % adimlar)
    satirlar.append("TUKENME_GUC_YOGUNLUGU = %r   # W/gHM (mutlak güç değil)" % guc)


def _operator_satirlari(t, zs, satirlar):
    from cekirdek import tukenme_ayar as _ta
    if _ta.hizli_kip(t):
        satirlar.append("    # HIZLI KİP: tek transport'tan MicroXS; tesir kesitleri adımlar boyunca SABİT")
        satirlar.append("    yanan = [m for m in model.materials if m.depletable]")
        satirlar.append("    akilar, mikrolar = openmc.deplete.get_microxs_and_flux(")
        satirlar.append("        model, yanan, chain_file=TUKENME_ZINCIRI,")
        satirlar.append("        path_statepoint='microxs_statepoint.h5')")
        satirlar.append("    op = openmc.deplete.IndependentOperator(")
        satirlar.append("        openmc.Materials(yanan), akilar, mikrolar, chain_file=TUKENME_ZINCIRI,")
        satirlar.append("        normalization_mode='fission-q',")
        satirlar.append("        fission_yield_opts={'energy': %r})" % zs["verim_enerjisi"])
        return
    satirlar.append("    op = openmc.deplete.CoupledOperator(")
    satirlar.append("        model, TUKENME_ZINCIRI,")
    satirlar.append("        diff_burnable_mats=False,")
    satirlar.append("        normalization_mode='fission-q',")
    satirlar.append("        fission_yield_mode='constant',")
    satirlar.append("        # Fisyon ürünü verimleri bu enerjide okunur: 0.0253 eV termal,")
    satirlar.append("        # 5e5 eV hızlı. OpenMC'nin varsayılanı 0.0253 eV'tur — hızlı")
    satirlar.append("        # zincir seçilse bile. Hızlı sistemde bu ayrıca verilmelidir.")
    satirlar.append("        fission_yield_opts={'energy': %r})" % zs["verim_enerjisi"])


def _entegrator_satirlari(t, satirlar):
    from cekirdek import tukenme_ayar as _ta
    from cekirdek.geometri.yapici import yorum_metni   # tembel: openmc (H1b)
    e = _ta.entegrator(t)
    satirlar.append("    # Entegratör: %s" % yorum_metni(e.gorunen_ad()))
    satirlar.append("    integ = openmc.deplete.%s(" % e.sinif)
    satirlar.append("        op, TUKENME_ADIMLARI,")
    if e.si:
        satirlar.append("        n_steps=%d,   # SI iç yineleme" % _ta.si_ic_adim(t))
    satirlar.append("        power_density=TUKENME_GUC_YOGUNLUGU)")


def _ornek_hacimleri(spec, hv):
    """Cubuk cubuk yanma: {malzeme adi: [[ornek hacmi, ...] hucre basina]}.
    tukenme.hazirla ile AYNI kaynak (tukenme_hacim.ornek_hacmi, Cell.paths
    sirasi); yalniz birden cok ornegi olan malzemeler. Hacmi hesaplanamayan
    ornek ValueError (tukenme.hazirla da durur)."""
    from cekirdek import kurucu, tukenme_hacim as th
    model, bilgi = kurucu.kur(spec)
    geo = model.geometry
    geo.determine_paths()
    hucreler, kafesler = geo.get_all_cells(), geo.get_all_lattices()
    sonuc = {}
    for ad in hv:
        mat = bilgi["malzemeler"][ad]
        if mat.num_instances <= 1:
            continue
        liste = [[th.ornek_hacmi(y, hucreler, kafesler) for y in c.paths]
                 for c in hucreler.values() if c.fill is mat]
        if any(v is None for h in liste for v in h):
            raise ValueError(_("'%s' malzemesinin bir örneğinin hacmi hesaplanamıyor; "
                             "çubuk çubuk yanma kesin hacim gerektirir") % ad)
        sonuc[ad] = liste
    return sonuc


def _ornek_ayirma_satirlari(spec, hv, satirlar):
    """Betige _ornekleri_ayir(model): tukenme_hacim.ornekleri_ayir'in betik
    karsiligi. OpenMC'nin diff_burnable_mats'i toplam hacmi orneklere ESIT
    bolerdi (esit olmayan katmanlarda yanlis); hacimler burada uretilir."""
    hacimler = _ornek_hacimleri(spec, hv)
    satirlar.append("")
    satirlar.append("# Çubuk çubuk yanma: her örnek kendi hacmiyle ayrı malzeme olur.")
    satirlar.append("# (malzeme, hücre başına [örnek hacmi, ...]); sıra = Cell.paths.")
    satirlar.append("_ORNEK_HACIMLERI = [")
    for ad, liste in hacimler.items():
        satirlar.append("    (%s, %r)," % (_ad(ad), liste))
    satirlar.append("]")
    satirlar.append("")
    satirlar.append("")
    satirlar.append("def _ornekleri_ayir(model):")
    satirlar.append('    """Yanabilir malzemeleri örnek başına klonlar; klon sayısını döndürür."""')
    satirlar.append("    geo = model.geometry")
    satirlar.append("    geo.determine_paths()")
    satirlar.append("    sayi = 0")
    satirlar.append("    for mat, liste in _ORNEK_HACIMLERI:")
    satirlar.append("        hucreler = [c for c in geo.get_all_cells().values() if c.fill is mat]")
    satirlar.append("        for hucre, hacimler in zip(hucreler, liste):")
    satirlar.append("            klonlar = []")
    satirlar.append("            for v in hacimler:")
    satirlar.append("                k = mat.clone()")
    satirlar.append("                k.depletable, k.volume = True, v")
    satirlar.append("                klonlar.append(k)")
    satirlar.append("            hucre.fill = klonlar if len(klonlar) > 1 else klonlar[0]")
    satirlar.append("            sayi += len(klonlar)")
    satirlar.append("    model.materials = openmc.Materials(geo.get_all_materials().values())")
    satirlar.append("    return sayi")
