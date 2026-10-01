# -*- coding: utf-8 -*-
"""
 kod_uret/tally.py  --  betik tally ve guc dagilimi bolumleri
"""

from cekirdek import sema
from cekirdek.kod_uret.ad import _ad, _f, _bolum, _mat_ifade  # noqa: F401
from cekirdek.geometri.yapici import yorum_metni


def _guc_dagilimi(spec, satirlar, uretilen, gx, gy):
    """Cubuk bazli guc dagilimi tally'sini uretir; tally degisken adlarini dondurur."""
    g = spec.get("guc_dagilimi") or {}
    if not g.get("var"):
        return []
    hedefler, eksik = _guc_hedefleri(spec, uretilen)
    for cubuk_ad in eksik:
        satirlar.append("")
        satirlar.append("# Uyarı: güç dağılımı için '%s' çubuğu geometride" % yorum_metni(cubuk_ad))
        satirlar.append("# bulunamadı; tally üretilmedi.")
    if not hedefler:
        return []

    satirlar.append("")
    satirlar.append("# --- çubuk bazlı güç dağılımı ---")
    satirlar.append("# pin() hücreleri bölge sırasında oluşturur, bu yüzden id'ye")
    satirlar.append("# göre sıralamak bölge sırasını verir.")
    if len(hedefler) > 1:
        satirlar.append("# Her çubuk türü için ayrı 'guc_dagilimi' tally'si (DistribcellFilter")
        satirlar.append("# tek hücre alır); hepsi aynı eksenel mesh'i paylaşır. Hücre adı = tür.")
    degiskenler = []
    for i, (cubuk_ad, degisken, bolge) in enumerate(hedefler):
        ek = "" if i == 0 else "_%d" % (i + 1)
        degiskenler.append(("guc_tally" + ek, "_guc_hedef" + ek))
        _guc_tur_satirlari(satirlar, ek, degisken, bolge, g,
                           cubuk_ad if len(hedefler) > 1 else None)
        if i == 0:
            _guc_mesh_satirlari(spec, satirlar, [h[0] for h in hedefler], g, gx, gy)
        satirlar.append("guc_tally%s.filters = _guc_filtreler%s" % (ek, ek))
    hucreler = ", ".join(h for _t, h in degiskenler)
    satirlar.append("")
    satirlar.append("# Toplam korunumu kontrolü: aynı hücre, bölünmemiş.")
    satirlar.append("# Eksenel mesh'in hücrenin tamamını kapsayıp kapsamadığını da sınar.")
    satirlar.append("guc_ref = openmc.Tally(name='guc_toplam_ref')")
    satirlar.append("guc_ref.scores = list(guc_tally.scores)")
    satirlar.append("guc_ref.filters = [openmc.CellFilter(%s)]"
                    % (hucreler if len(hedefler) == 1 else "[%s]" % hucreler))
    satirlar.append("")
    satirlar.append("# Mutlak güç payı: hedef bölgenin model geneli fisyon enerjisindeki")
    satirlar.append("# payı = guc_toplam_ref / guc_model_toplam (filtresiz, aynı skor).")
    satirlar.append("guc_model = openmc.Tally(name='guc_model_toplam')")
    satirlar.append("guc_model.scores = list(guc_tally.scores)")
    return [t for t, _h in degiskenler] + ["guc_ref", "guc_model"]


def _guc_hedefleri(spec, uretilen):
    """kurucu.guc_hedef_hucreleri'nin betik karsiligi: ([(ad, degisken, bolge)],
    [geometride olmayan adlar]); ayni (cubuk, bolge) bir kez."""
    hedefler, eksik, gorulen = [], [], set()
    for h in sema.guc_hedefleri(spec.get("guc_dagilimi")):
        if (h["cubuk"], h["bolge"]) in gorulen:
            continue
        gorulen.add((h["cubuk"], h["bolge"]))
        degisken = uretilen.get(h["cubuk"])
        if degisken is None:
            eksik.append(h["cubuk"])
        else:
            hedefler.append((h["cubuk"], degisken, h["bolge"]))
    return hedefler, eksik


def _guc_tur_satirlari(satirlar, ek, degisken, bolge, g, hucre_adi):
    """Bir cubuk turunun hedef hucresi ve tally'si (filtreler sonra atanir)."""
    if ek:
        satirlar.append("")
    satirlar.append("_guc_hucreler%s = sorted(%s.cells.values(), key=lambda c: c.id)"
                    % (ek, degisken))
    satirlar.append("_guc_hedef%s = _guc_hucreler%s[%d]" % (ek, ek, bolge))
    if hucre_adi:
        satirlar.append("_guc_hedef%s.name = %r" % (ek, hucre_adi))
    satirlar.append("guc_tally%s = openmc.Tally(name='guc_dagilimi')" % ek)
    satirlar.append("guc_tally%s.scores = [%r]" % (ek, g.get("skor") or "kappa-fission"))
    satirlar.append("_guc_filtreler%s = [openmc.DistribcellFilter(_guc_hedef%s)]" % (ek, ek))
    if ek:
        satirlar.append("if _guc_mesh_filtresi is not None:")
        satirlar.append("    _guc_filtreler%s.append(_guc_mesh_filtresi)" % ek)


def _guc_mesh_satirlari(spec, satirlar, adlar, g, gx, gy):
    """Eksenel mesh (3B, dilim > 1): kurucu ile AYNI aralik (geometri.hedef_araligi).
    Cok turde mesh filtresi turler arasinda paylasilir (_guc_mesh_filtresi)."""
    from cekirdek import geometri
    h = sema.model_yuksekligi(spec)
    dilim = int(g.get("eksenel_dilim") or 1)
    cok_tur = len(adlar) > 1
    if not (h and dilim > 1):
        if cok_tur:
            satirlar.append("_guc_mesh_filtresi = None")
        return
    pay = max(gx, gy)
    _z0, _z1 = geometri.hedef_araligi(spec, adlar)
    satirlar.append("")
    satirlar.append("# Eksenel mesh aktif yakıt yüksekliğiyle tam örtüşmelidir;")
    satirlar.append("# taşarsa boş bin'ler ortalamayı düşürür ve F_q şişer.")
    satirlar.append("_guc_mesh = openmc.RegularMesh()")
    satirlar.append("_guc_mesh.dimension   = [1, 1, %d]" % dilim)
    satirlar.append("_guc_mesh.lower_left  = (%s, %s, %s)" % (_f(-pay), _f(-pay), _f(_z0)))
    satirlar.append("_guc_mesh.upper_right = (%s, %s, %s)" % (_f(pay), _f(pay), _f(_z1)))
    if cok_tur:
        satirlar.append("_guc_mesh_filtresi = openmc.MeshFilter(_guc_mesh)")
        satirlar.append("_guc_filtreler.append(_guc_mesh_filtresi)")
    else:
        satirlar.append("_guc_filtreler.append(openmc.MeshFilter(_guc_mesh))")


def _tallyler(spec, satirlar, ek_tallyler=None, on_satirlar=None, sinir_kutu=None):
    ek_tallyler = list(ek_tallyler or [])
    if not spec.get("tallyler") and not ek_tallyler:
        return
    _bolum(satirlar, 4, "TALLY'LER")
    satirlar.extend(on_satirlar or [])
    adlar = []
    for i, t in enumerate(spec["tallyler"]):
        v = "tally_%d" % (i + 1)
        adlar.append(v)
        satirlar.append("")
        satirlar.append("%s = openmc.Tally(name=%r)" % (v, t["ad"]))
        satirlar.append("%s.scores = %r" % (v, list(t["skorlar"])))
        if t.get("nuklidler"):
            satirlar.append("%s.nuclides = %r" % (v, list(t["nuklidler"])))
        filtre_ifadeleri = []
        for j, f in enumerate(t.get("filtreler", [])):
            if f["tur"] == "enerji":
                filtre_ifadeleri.append("openmc.EnergyFilter(%r)" % list(f["gruplar"]))
            elif f["tur"] == "mesh":
                mv = "%s_mesh_%d" % (v, j)
                # kurucu.py ile AYNI fonksiyon: otomatik sinirlar modelin sinir
                # kutusundan ve kor yuksekliginden turetilir.
                from cekirdek import kurucu as _kur
                alt, ust = _kur.tally_mesh_sinirlari(spec, f, sinir_kutu)
                if f.get("otomatik"):
                    satirlar.append("# mesh sınırları modelin sınır kutusundan türetildi")
                satirlar.append("%s = openmc.RegularMesh()" % mv)
                satirlar.append("%s.dimension  = %r" % (mv, list(f["boyut"])))
                satirlar.append("%s.lower_left = %r" % (mv, list(alt)))
                satirlar.append("%s.upper_right = %r" % (mv, list(ust)))
                filtre_ifadeleri.append("openmc.MeshFilter(%s)" % mv)
            elif f["tur"] == "malzeme":
                filtre_ifadeleri.append("openmc.MaterialFilter([%s])"
                                        % ", ".join(_ad(a) for a in f["adlar"]))
        if filtre_ifadeleri:
            satirlar.append("%s.filters = [%s]" % (v, ", ".join(filtre_ifadeleri)))
    satirlar.append("")
    satirlar.append("tallyler = openmc.Tallies([%s])" % ", ".join(adlar + ek_tallyler))
