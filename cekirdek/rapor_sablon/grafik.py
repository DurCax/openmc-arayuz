# -*- coding: utf-8 -*-
"""
grafik.py -- rapor gorselleri (PNG bayt): geometri kesitleri, yakinsama,
guc haritasi, eksenel profil, tukenme.

matplotlib.figure.Figure + FigureCanvasAgg kullanilir; pyplot YOK (global
durum, arayuz tuvalleriyle karismaz) ve Qt YOK. Renkler tasarim
tokenlarindan (arayuz/tasarim/tokenlar.py -- Qt'siz saf veri) gelir; rapor
her zaman acik temadadir (baski).

Geometri kesitleri `openmc -p` (cizim kipi, alt surec) ile uretilir:
nukleer veri gerektirmez ve openmc.lib'in surec-geneli durumuna (onizleme
paneli ayni surecte acik olabilir) dokunmaz. Olculdu: 17x17 3B demet iki
kesit ~0.3 s.
"""

import io
import math
import os
import shutil
import subprocess
import tempfile

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

DPI = 110
GENIS = (6.4, 3.6)           # inc; A4 metin genisligine sigar
KARE = (5.2, 4.4)
GEOMETRI_PIKSEL = 600
_EKSENEL_BASIK = 3.0         # yukseklik/genislik bundan buyukse eksen basik cizilir
_ETIKET_SINIRI = 300         # bundan az cubukta degerler hucreye yazilir
_CIZIM_SURESI = 60           # s; openmc -p zaman asimi


def _renkler():
    from arayuz.tasarim import tokenlar
    p = tokenlar.palet("acik")
    return {"metin": p["metin"], "ikincil": p["metin_ikincil"], "izgara": p["grafik_izgara"],
            "seri": tokenlar.GRAFIK_PALETI["acik"], "harita": tokenlar.GRAFIK_HARITASI,
            "vurgu": p["vurgu"], "hata": p["hata"]}


def _figur(boyut=GENIS):
    from matplotlib.figure import Figure
    fig = Figure(figsize=boyut, dpi=DPI, layout="constrained")
    r = _renkler()
    fig.set_facecolor("white")
    return fig, r


def _eksen_bicimi(ax, r):
    ax.grid(True, color=r["izgara"], linewidth=0.6)
    ax.tick_params(colors=r["ikincil"], labelsize=8)
    for kenar in ax.spines.values():
        kenar.set_color(r["izgara"])


def png(fig):
    """Figure -> PNG bayt (Agg)."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    FigureCanvasAgg(fig)
    tampon = io.BytesIO()
    fig.savefig(tampon, format="png", dpi=DPI, facecolor="white")
    return tampon.getvalue()


# ============================================================================
# KOSU GRAFIKLERI
# ============================================================================

def yakinsama(kosu):
    """Cevrim k'si + aktif ortalama (+ varsa Shannon entropisi)."""
    k, pasif, ent = kosu["k_nesil"], kosu["pasif"], kosu["entropi"]
    fig, r = _figur()
    eksenler = fig.subplots(1, 2) if ent else [fig.subplots(1, 1)]
    ax = eksenler[0]
    x = list(range(1, len(k) + 1))
    ax.plot(x, k, ".", color=r["seri"][0], markersize=3, label=_("çevrim k"))
    ort = [sum(k[pasif:i]) / (i - pasif) for i in range(pasif + 1, len(k) + 1)]
    ax.plot(x[pasif:], ort, "-", color=r["seri"][1], linewidth=1.2, label=_("aktif ortalama"))
    if kosu.get("keff") is not None:
        ax.axhspan(kosu["keff"] - kosu["sigma"], kosu["keff"] + kosu["sigma"],
                   color=r["seri"][2], alpha=0.25, label=_("sonuç ± σ"))
    ax.axvline(pasif + 0.5, color=r["ikincil"], linestyle=":", linewidth=0.8)
    ax.set_xlabel(_("çevrim"), fontsize=8)
    ax.set_ylabel("k", fontsize=8)
    ax.legend(fontsize=7, frameon=False)
    _eksen_bicimi(ax, r)
    if ent:
        e = eksenler[1]
        e.plot(range(1, len(ent) + 1), ent, "-", color=r["seri"][3], linewidth=1.0)
        e.axvline(pasif + 0.5, color=r["ikincil"], linestyle=":", linewidth=0.8)
        e.set_xlabel(_("çevrim"), fontsize=8)
        e.set_ylabel(_("Shannon entropisi"), fontsize=8)
        _eksen_bicimi(e, r)
    return png(fig)


def _hucre_sekli(kafes, merkez, adim):
    from matplotlib.patches import Rectangle, RegularPolygon
    from cekirdek import guc
    if guc._kafes_turu(kafes) == "altigen":
        yon = math.pi / 6 if getattr(kafes, "orientation", "y") == "y" else 0.0
        return RegularPolygon(merkez, 6, radius=adim / math.sqrt(3), orientation=yon)
    return Rectangle((merkez[0] - adim / 2, merkez[1] - adim / 2), adim, adim)


def guc_haritasi(guc_ozeti):
    """Bagil cubuk gucu haritasi (radyal, eksenel toplam); sicak cubuk isaretli."""
    from matplotlib.collections import PatchCollection
    from cekirdek import guc
    f, dagilim = guc_ozeti["faktorler"], guc_ozeti["dagilim"]
    kafes = dagilim["kafes"]
    adim = float(tuple(kafes.pitch)[0])
    anahtarlar = list(f["bagil"])
    merkezler = [guc.cubuk_merkezi(dagilim, a) for a in anahtarlar]
    degerler = [f["bagil"][a][0] for a in anahtarlar]
    fig, r = _figur(KARE)
    ax = fig.subplots(1, 1)
    kume = PatchCollection([_hucre_sekli(kafes, m, adim) for m in merkezler],
                           cmap=r["harita"], edgecolor="white", linewidth=0.3)
    kume.set_array(degerler)
    ax.add_collection(kume)
    if len(anahtarlar) <= _ETIKET_SINIRI:
        ort = sum(degerler) / len(degerler)
        boyut = max(3.0, min(7.0, 90.0 / math.sqrt(len(anahtarlar))))
        for (x, y), v in zip(merkezler, degerler):
            # in_layout=False: yuzlerce etiket constrained yerlesimi yavaslatir
            ax.text(x, y, "%.2f" % v, ha="center", va="center", fontsize=boyut,
                    color="white" if v < ort else r["metin"], in_layout=False)
    sx, sy = guc.cubuk_merkezi(dagilim, f["sicak_cubuk"])
    ax.add_patch(_hucre_sekli(kafes, (sx, sy), adim))
    ax.patches[-1].set(fill=False, edgecolor=r["hata"], linewidth=1.6)
    xs, ys = [m[0] for m in merkezler], [m[1] for m in merkezler]
    ax.set_xlim(min(xs) - adim, max(xs) + adim)
    ax.set_ylim(min(ys) - adim, max(ys) + adim)
    ax.set_aspect("equal")
    ax.set_xlabel("x [cm]", fontsize=8)
    ax.set_ylabel("y [cm]", fontsize=8)
    ax.tick_params(labelsize=7)
    fig.colorbar(kume, ax=ax, shrink=0.85).set_label(_("bağıl çubuk gücü"), fontsize=8)
    return png(fig)


def eksenel_profil(profil):
    """Eksenel bagil guc profili (tum cubuklar toplami)."""
    fig, r = _figur((4.2, 3.6))
    ax = fig.subplots(1, 1)
    n = len(profil)
    z = [(i + 0.5) / n for i in range(n)]
    ax.errorbar([p[0] for p in profil], z, xerr=[p[1] for p in profil], fmt="o-",
                color=r["seri"][0], markersize=3, linewidth=1.0, capsize=2)
    ax.set_xlabel(_("bağıl güç"), fontsize=8)
    ax.set_ylabel(_("bağıl yükseklik (alt → üst)"), fontsize=8)
    _eksen_bicimi(ax, r)
    return png(fig)


def tukenme(tuk):
    """k(yanma) ve izlenen nuklidlerin toplam atom sayisi (log olcek)."""
    fig, r = _figur()
    ak, an = fig.subplots(1, 2)
    ak.plot(tuk["yanma"], tuk["k"], "o-", color=r["seri"][0], markersize=3)
    ak.set_xlabel(_("yanma [MWd/kgHM]"), fontsize=8)
    ak.set_ylabel("k", fontsize=8)
    _eksen_bicimi(ak, r)
    for i, (n, dizi) in enumerate(sorted(tuk["atomlar"].items())):
        if any(v > 0 for v in dizi):
            an.plot(tuk["yanma"], dizi, "-", color=r["seri"][i % len(r["seri"])],
                    linewidth=1.0, label=n)
    an.set_yscale("log")
    an.set_xlabel(_("yanma [MWd/kgHM]"), fontsize=8)
    an.set_ylabel(_("atom sayısı"), fontsize=8)
    if tuk["atomlar"]:
        an.legend(fontsize=6, frameon=False, ncol=2)
    _eksen_bicimi(an, r)
    return png(fig)


def _guvenli(ad, islev, *arg):
    """Tek bir grafigi uretir; hata raporu durdurmaz: (png | None, uyari | None)."""
    try:
        return islev(*arg), None
    except Exception as e:
        _log.warning("rapor grafiği çizilemedi: %s", ad, exc_info=True)
        return None, _("grafik çizilemedi (%s): %s") % (ad, e)


def kosu_gorselleri(kosu, guc_ozeti, tuk):
    """Kosu grafikleri: ({ad: png}, uyarilar)."""
    isler = []
    if kosu and len(kosu.get("k_nesil") or []) > kosu.get("pasif", 0):
        isler.append(("yakinsama", yakinsama, kosu))
    if guc_ozeti and guc_ozeti.get("faktorler"):
        isler.append(("guc_haritasi", guc_haritasi, guc_ozeti))
        if guc_ozeti["faktorler"].get("eksenel_profil"):
            isler.append(("eksenel", eksenel_profil, guc_ozeti["faktorler"]["eksenel_profil"]))
    if tuk and len(tuk.get("yanma") or []) > 1:
        isler.append(("tukenme", tukenme, tuk))
    gorsel, uyarilar = {}, []
    for ad, islev, arg in isler:
        veri, uyari = _guvenli(ad, islev, arg)
        if veri:
            gorsel[ad] = veri
        if uyari:
            uyarilar.append(uyari)
    return gorsel, uyarilar


# ============================================================================
# GEOMETRI KESITLERI (openmc -p)
# ============================================================================

def _piksel(a, b):
    """Uzun kenar GEOMETRI_PIKSEL; en-boy orani _EKSENEL_BASIK'ta kirpilir."""
    oran = min(b / a, _EKSENEL_BASIK)
    if oran >= 1.0:
        return (max(1, int(GEOMETRI_PIKSEL / oran)), GEOMETRI_PIKSEL)
    return (GEOMETRI_PIKSEL, max(1, int(GEOMETRI_PIKSEL * oran)))


def _kesit_tanimlari(spec, bilgi):
    """[(ad, basis, genislik (a, b), piksel (pa, pb))] -- 2B modelde yalniz xy."""
    from cekirdek import sema
    gx, gy = bilgi["sinir_kutu"]
    tanimlar = [("geo_xy", "xy", (gx, gy), _piksel(gx, gy))]
    h = sema.kor_yuksekligi(spec["kor"])
    if h:
        tanimlar.append(("geo_xz", "xz", (gx, h), _piksel(gx, h)))
    return tanimlar


def _merkez(model):
    """Sinir kutusunun merkezi; sonsuz eksende 0 (2B model)."""
    alt, ust = model.geometry.bounding_box
    return tuple(0.5 * (a + b) if math.isfinite(a) and math.isfinite(b) else 0.0
                 for a, b in zip(alt, ust))


def _cizim_modeli(model, bilgi, tanimlar):
    import openmc
    merkez = _merkez(model)
    cizimler = []
    for ad, basis, genislik, piksel in tanimlar:
        p = openmc.SlicePlot(name=ad)
        p.filename, p.basis, p.width, p.pixels = ad, basis, genislik, piksel
        p.origin = merkez
        p.color_by = "material"
        p.colors = dict(bilgi["renkler"])
        cizimler.append(p)
    return openmc.Model(geometry=model.geometry, materials=model.materials,
                        settings=model.settings, plots=openmc.Plots(cizimler))


def _eksenli(ad, basis, genislik, png_yolu):
    """openmc'nin ham PNG'sini cm eksenli bir figure sarar."""
    import matplotlib.image as mimg
    fig, r = _figur(KARE if basis == "xy" else (4.0, 4.8))
    ax = fig.subplots(1, 1)
    a, b = genislik
    ax.imshow(mimg.imread(png_yolu), extent=(-a / 2, a / 2, -b / 2, b / 2),
              aspect="equal" if b / a <= _EKSENEL_BASIK else "auto", interpolation="nearest")
    ax.set_xlabel(("x" if basis != "yz" else "y") + " [cm]", fontsize=8)
    ax.set_ylabel(("y" if basis == "xy" else "z") + " [cm]", fontsize=8)
    ax.tick_params(labelsize=7)
    if b / a > _EKSENEL_BASIK:
        ax.set_title(_("eksenel ölçek sıkıştırıldı"), fontsize=7, color=r["ikincil"])
    return png(fig)


def geometri_gorselleri(spec):
    """xy (ve 3B'de xz) kesitleri: ({"geo_xy": png, "geo_xz": png}, uyarilar)."""
    exe = shutil.which("openmc")
    if exe is None:
        _log.warning("rapor: openmc çalıştırılabilir dosyası yok; geometri kesiti atlandı")
        return {}, [_("geometri kesitleri çizilemedi: openmc PATH'te yok")]
    dizin = tempfile.mkdtemp(prefix="openmc_rapor_geo_")
    try:
        from cekirdek import kurucu
        model, bilgi = kurucu.kur(spec)
        tanimlar = _kesit_tanimlari(spec, bilgi)
        _cizim_modeli(model, bilgi, tanimlar).export_to_model_xml(
            os.path.join(dizin, "model.xml"))
        subprocess.run([exe, "-p", dizin], cwd=dizin, capture_output=True, text=True,
                       timeout=_CIZIM_SURESI, check=True)
        return {ad: _eksenli(ad, basis, gen, os.path.join(dizin, ad + ".png"))
                for ad, basis, gen, _p in tanimlar}, []
    except subprocess.CalledProcessError as e:
        _log.warning("rapor: openmc -p başarısız: %s", (e.stdout or "")[-2000:])
        return {}, [_("geometri kesitleri çizilemedi: openmc -p çıkış kodu %d") % e.returncode]
    except Exception as e:
        _log.warning("rapor: geometri kesitleri çizilemedi", exc_info=True)
        return {}, [_("geometri kesitleri çizilemedi: %s") % e]
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
