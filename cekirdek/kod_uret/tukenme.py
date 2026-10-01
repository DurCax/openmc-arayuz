# -*- coding: utf-8 -*-
"""
 kod_uret/tukenme.py  --  betik tukenme (yanma) bolumu

 Hacimler cekirdek/tukenme.py'deki AYNI islevden gelir.
"""

from cekirdek import sema
from cekirdek.kod_uret.ad import _ad, _f, _bolum, _mat_ifade  # noqa: F401
from cekirdek.geometri.yapici import yorum_metni
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
    satirlar.append("TUKENME_ADIMLARI = %r   # %s" % ([float(a) for a in t["adimlar"]],
                                                    yorum_metni(t.get("adim_birimi") or "d")))
    satirlar.append("")
    satirlar.append("")
    satirlar.append("def tukenme_kos():")
    satirlar.append('    """Yanma hesabı; depletion_results.h5 üretir."""')
    satirlar.append("    import openmc.deplete")
    if ayir:
        satirlar.append("    _ornekleri_ayir(model)   # örnek başına kesin hacim (aşağıda False)")
    satirlar.append("    op = openmc.deplete.CoupledOperator(")
    satirlar.append("        model, TUKENME_ZINCIRI,")
    satirlar.append("        diff_burnable_mats=False,")
    satirlar.append("        normalization_mode='fission-q',")
    satirlar.append("        fission_yield_mode='constant',")
    satirlar.append("        # Fisyon ürünü verimleri bu enerjide okunur: 0.0253 eV termal,")
    satirlar.append("        # 5e5 eV hızlı. OpenMC'nin varsayılanı 0.0253 eV'tur — hızlı")
    satirlar.append("        # zincir seçilse bile. Hızlı sistemde bu ayrıca verilmelidir.")
    satirlar.append("        fission_yield_opts={'energy': %r})" % zs["verim_enerjisi"])
    sinif = {"cecm": "CECMIntegrator", "predictor": "PredictorIntegrator"}[
        t.get("entegrator") or "cecm"]
    satirlar.append("    integ = openmc.deplete.%s(" % sinif)
    satirlar.append("        op, TUKENME_ADIMLARI,")
    satirlar.append("        power_density=%r,   # W/gHM (mutlak güç değil)"
                    % float(t["guc_yogunlugu"]))
    satirlar.append("        timestep_units=%r)" % (t.get("adim_birimi") or "d"))
    satirlar.append("    integ.integrate()")
    satirlar.append("    return 'depletion_results.h5'")
    return True


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
