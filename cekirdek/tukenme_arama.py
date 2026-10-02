# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_arama.py  --  Tukenme sirasinda kritiklik aramasi (v3 Y4)
================================================================================

 OpenMC 0.16: Integrator.add_keff_search_control(function, x0, x1, bracket,
 **search_kwargs). Her guclu adimin BASINDA openmc.Model.keff_search (GRsecant,
 Price & Roskoff 2023) kosar; bulunan deger h5'te StepResult.keff_search_root
 olarak saklanir ve adimin transport'u o degerle kosar. Islev modeli YALNIZ
 openmc.lib uzerinden degistirmelidir (OpenMC belgesi): CoupledOperator
 openmc.lib'i zaten baslatmistir, arama ayni oturumda kosar.

   bor    cozunmus bor [ppm] -- su malzemesinin nuklid yogunluklari
          openmc.lib.Material.set_densities ile; bilesim tarama.parametre_uygula
          ("bor_ppm") ile AYNI tariften (statik kritik bor aramasiyla tutarli).
          B10/B11 ilk kurulumda malzemede bulunsun diye su, iki tahminin
          buyugundeki bor ile kurulur (openmc.lib yeni nuklid yukleyemez).
   cubuk  kontrol cubugu daldirmasi [%] -- cubuk evreninde emici (ucun ustu)
          ve izleyici (ucun alti) hucreleri tek bir ic evrene tasinir; ic
          evrende uc z = 0'dadir ve dis hucrenin translation'i ucun konumudur:
          z_uc(d) = z_ust - d/100 (z_ust - z_alt) (geometri/bilesen._kontrol
          ile ayni tanim). openmc.lib.Cell.translation ile hareket eder.
          Emici malzeme hareket ettigi icin TUKENMEZ (hacmi sabit degil).

 KABUL (test_y4_arama): her guclu adimin k'si |k - 1| <= k_tol + 3 sigma.
 Arama |k - hedef| <= k_tol ve sigma <= sigma_final olunca durur; adimin
 kendi transport'u bagimsiz bir olcumdur, o yuzden ek 3 sigma (%99.7).
================================================================================
"""

from __future__ import annotations

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


# ---------------------------------------------------------------------------
# bor
# ---------------------------------------------------------------------------

def bor_yogunluklari(spec: dict, hedef: str, ppm: float) -> dict:
    """{nuklid: atom/b-cm}: hedef su malzemesi ppm borla (tarama tarifi)."""
    from cekirdek import kurucu, tarama
    yeni, _not = tarama.parametre_uygula(spec, "bor_ppm", hedef, float(ppm))
    nesneler, _m, _r = kurucu.malzemeleri_kur(yeni)
    return {n: float(v) for n, v in nesneler[hedef].get_nuclide_atom_densities().items()}


def bor_tablosu(spec: dict, hedef: str, ust_ppm: float) -> tuple:
    """
    (y0, egim): {nuklid: atom/b-cm} dogrusal tablo, y(ppm) = y0 + ppm egim.
    Su bilesimi sabit kutle yogunlugunda ppm'le DOGRUSALDIR (agirlikca kesirler
    ppm'le dogrusal; N_i = rho N_A w_i / A_i). Tablo ppm > 0 dalinin iki
    noktasindan (ust/2, ust) kurulur: tarif ppm = 0'da atomca H2O'dur
    (malzeme_kutup.su) ve H yogunlugu 1.2e-5 oraninda farklidir; tablo bu
    sicramayi tasimaz. Tarif (kurucu.malzemeleri_kur) yalniz burada, KURULUMDA
    iki kez cozulur; arama sirasinda openmc.Material olusturulmaz.
    """
    ya = bor_yogunluklari(spec, hedef, ust_ppm / 2.0)
    yb = bor_yogunluklari(spec, hedef, ust_ppm)
    adlar = sorted(set(ya) | set(yb))
    egim = {n: (yb.get(n, 0.0) - ya.get(n, 0.0)) / (ust_ppm / 2.0) for n in adlar}
    return {n: yb.get(n, 0.0) - ust_ppm * egim[n] for n in adlar}, egim


def _malzemeyi_doldur(m, yogunluk: dict) -> None:
    """openmc.Material'in nuklidlerini yogunluk ile degistirir (kurulum, lib oncesi)."""
    for n in list(m.get_nuclides()):
        m.remove_nuclide(n)
    for n, y in yogunluk.items():
        m.add_nuclide(n, float(y), "ao")
    m.set_density("atom/b-cm", float(sum(yogunluk.values())))


def bor_islevi(nesneler: dict, spec: dict, hedef: str, baslangic_ppm: float):
    """Arama islevi f(ppm). Modelin su malzemesi baslangic_ppm ile kurulur."""
    m = _malzeme(nesneler, hedef)
    _malzemeyi_doldur(m, bor_yogunluklari(spec, hedef, baslangic_ppm))
    y0, egim = bor_tablosu(spec, hedef, baslangic_ppm)
    adlar = list(y0)
    mid = m.id

    def ayarla(ppm: float) -> None:
        import openmc.lib
        x = max(float(ppm), 0.0)
        openmc.lib.materials[mid].set_densities(
            adlar, [max(y0[n] + x * egim[n], 0.0) for n in adlar])
    return ayarla


def _malzeme(nesneler: dict, ad: str):
    """Spec adina karsilik openmc.Material (hazirla bilgisi "nesneler")."""
    if ad in nesneler:
        return nesneler[ad]
    raise ValueError(_("kritiklik araması: modelde '%s' malzemesi yok") % ad)


# ---------------------------------------------------------------------------
# cubuk
# ---------------------------------------------------------------------------

def _ortak_zduzlem(a, b):
    import openmc
    sa = {s.id: s for s in a.region.get_surfaces().values()
          if isinstance(s, openmc.ZPlane)} if a.region is not None else {}
    sb = {s.id for s in b.region.get_surfaces().values()} if b.region is not None else set()
    ortak = [s for i, s in sa.items() if i in sb]
    return ortak[0] if len(ortak) == 1 else None


def _cubuk_ciftleri(model, emici, izleyici):
    """[(evren, emici_hucre, izleyici_hucre, uc_duzlemi)]: kontrol cubugu evrenleri."""
    ciftler = []
    for u in model.geometry.get_all_universes().values():
        hucreler = list(u.cells.values())
        for a in (h for h in hucreler if h.fill is emici):
            for f in (h for h in hucreler if h.fill is izleyici and h is not a):
                uc = _ortak_zduzlem(a, f)
                if uc is not None:
                    ciftler.append((u, a, f, uc))
    return ciftler


def uc_konumu(daldirma: float, z_alt: float, z_ust: float) -> float:
    """Cubuk ucunun z'si: z_ust - d/100 (z_ust - z_alt); d %0-100'e kirpilir
    (geometri/bilesen._kontrol ile ayni tanim)."""
    d = min(max(float(daldirma), 0.0), 100.0)
    return z_ust - d / 100.0 * (z_ust - z_alt)


def hareketli_yap(model, emici, izleyici) -> list:
    """
    Kontrol cubugu evrenlerinde emici + izleyici hucre ciftini tek bir dis
    hucreye cevirir; doner [dis hucre id]. Dis hucrenin bolgesi iki ORIJINAL
    hucrenin BIRLESIMIDIR (a.region | f.region): uc duzleminin iki yari uzayi
    birbirini tamamlar, emicinin ust ve izleyicinin alt sinirlari korunur --
    evrendeki baska eksenel hucrelerle (plenum, uc tipasi) cakisma olmaz. Ic
    evrende uc z = 0'dadir: emici z > 0, izleyici z < 0; dis hucre bunlari
    kendi bolgesiyle kirpar. translation = (0, 0, uc z'si).
    """
    import openmc
    idler = []
    for u, a, f, uc in _cubuk_ciftleri(model, emici, izleyici):
        sifir = openmc.ZPlane(0.0)
        ic = openmc.Universe(cells=[openmc.Cell(fill=emici, region=+sifir),
                                    openmc.Cell(fill=izleyici, region=-sifir)])
        dis = openmc.Cell(fill=ic, region=a.region | f.region)
        dis.translation = (0.0, 0.0, uc.z0)
        u.remove_cell(a)
        u.remove_cell(f)
        u.add_cell(dis)
        idler.append(dis.id)
    return idler


def cubuk_islevi(model, nesneler: dict, spec: dict, hedef: str, aralik: tuple):
    """
    Arama islevi f(daldirma %). Cubuk evrenleri hareketli yapilir; doner
    (islev, [emici malzeme]). aralik: (z_alt, z_ust) aktif bolge.
    """
    from cekirdek import sema
    c = sema.cubuk_bul(spec, hedef)
    emici = _malzeme(nesneler, c["bolgeler"][int(c.get("emici_bolge") or 0)]["malzeme"])
    izleyici = _malzeme(nesneler, c.get("izleyici_malzeme"))
    hucre_idler = hareketli_yap(model, emici, izleyici)
    if not hucre_idler:
        raise ValueError(_("kritiklik araması: '%s' kontrol çubuğunun hareketli hücresi bulunamadı "
                           "(3B model ve kontrol çubuğu gerekli)") % hedef)
    _log.info("çubuk araması: %d hareketli çubuk evreni (%s)", len(hucre_idler), hedef)
    z_alt, z_ust = aralik

    def ayarla(daldirma: float) -> None:
        import openmc.lib
        z = uc_konumu(daldirma, z_alt, z_ust)
        for i in hucre_idler:
            openmc.lib.cells[i].translation = (0.0, 0.0, z)
    return ayarla, [emici]


# ---------------------------------------------------------------------------
# kurulum
# ---------------------------------------------------------------------------

def hazirla(model, nesneler: dict, spec: dict) -> object | None:
    """
    Arama acıksa modeli hazirlar (operator kurulmadan ONCE) ve islevi doner;
    kapaliysa None. Cubuk aramasinda emici malzeme tukenmeden cikarilir.
    """
    from cekirdek import tukenme_ayar
    k = tukenme_ayar.kritik_arama(spec.get("tukenme") or {})
    if not k.var:
        return None
    if k.tur == "bor":
        return bor_islevi(nesneler, spec, k.hedef, max(k.alt, k.ust))
    islev, emiciler = cubuk_islevi(model, nesneler, spec, k.hedef, _aktif_aralik(spec))
    for m in emiciler:
        if m.depletable:
            _log.warning("çubuk araması: hareketli emici '%s' tükenmeden çıkarıldı", m.name)
            m.depletable = False
    model.materials = openmc_malzemeleri(model)
    return islev


def openmc_malzemeleri(model):
    import openmc
    return openmc.Materials(model.geometry.get_all_materials().values())


def _aktif_aralik(spec: dict) -> tuple:
    from cekirdek import geometri, sema
    aralik = geometri.aktif_aralik(spec)
    if aralik:
        return tuple(aralik)
    h = sema.kor_yuksekligi(spec["kor"]) if spec.get("kor", {}).get("tur") != sema.AGAC else None
    if not h:
        raise ValueError(_("kontrol çubuğu araması 3B model gerektirir"))
    return (-h / 2.0, h / 2.0)


def ekle(integ, islev, spec: dict) -> None:
    """Entegratore aramayi ekler (OpenMC add_keff_search_control)."""
    from cekirdek import tukenme_ayar
    k = tukenme_ayar.kritik_arama(spec.get("tukenme") or {})
    integ.add_keff_search_control(islev, k.alt, k.ust, list(k.sinir), target=1.0,
                                  k_tol=k.k_tol, sigma_final=k.sigma)
