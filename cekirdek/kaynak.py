# -*- coding: utf-8 -*-
"""
================================================================================
 kaynak.py  --  Kaynak tanimi: enerji tayfi, acisal dagilim, parcacik turu
================================================================================

 NEDEN AYRI BIR MODUL
   Enerji tayfi eskiden kurucu.py icinde "openmc.stats.Watt()" olarak GOMULUYDU.
   Ozdeger (k-eff) modunda bu zararsizdir -- baslangic tayfi pasif cevrimlerde
   gercek fisyon tayfiyla degisir. Ama SABIT KAYNAK (zirhlama, aktivasyon,
   detektor) hesabinda kaynak tayfi sonucun kendisidir; sabit bir Watt tayfi
   14 MeV'lik bir D-T kaynagini ya da Co-60 gamalarini temsil edemez.

 OLCUMLE DOGRULANAN SAYILAR  (bkz. testler -> test_kaynak_tayfi)
   Watt(a=988 keV, b=2.249e-6)  ortalama = 2.031 MeV   [analitik 1.5a + a^2 b/4]
   Maxwell(theta=1.2932 MeV)    ortalama = 1.940 MeV   [analitik 1.5 theta]
   Muir(e0=14.08 MeV, m=5, kT=20 keV)  sigma = 336 keV
        [analitik D-T genisleme: FWHM = 177*sqrt(kT[keV]) keV -> sigma = 336.2]

 BIRIMLER
   Butun enerjiler eV cinsindendir (OpenMC'nin ic birimi). Arayuz MeV gosterir
   ve donusumu kendisi yapar; spec dosyasinda daima eV vardir.
================================================================================
"""

import math

import openmc

# Arayuzde ve dogrulamada kullanilan tayf listesi: (anahtar, gorunen ad)
TAYFLAR = [
    ("watt",      "Watt fisyon tayfı"),
    ("maxwell",   "Maxwell tayfı"),
    ("tek",       "Tek enerjili (monoenerjetik)"),
    ("ayrik",     "Ayrık çizgiler"),
    ("histogram", "Grup grup tayf (histogram)"),
    ("fuzyon",    "Füzyon tayfı (D-T / D-D, Muir)"),
]

ACILAR = [
    ("izotropik", "İzotropik"),
    ("tek_yon",   "Tek yönlü demet"),
    ("koni",      "Koni"),
]

# Shannon entropisi agi -- "otomatik" boyut.
#   Entropi FISYON KAYNAGININ yakinsamasini olcer; bu yuzden kaynak modulunde.
#   Radyal 8 x 8 bolme; 3B modelde eksenel 8 bolme (asil yakinsama riski
#   eksenel yondedir: bkz. kurucu.ayarlari_kur), 2B'de tek dilim. Butun 3B
#   ornekler (pwr_3b, pwr_eksenel, pwr_kontrol) ve 2B ornekler zaten bu
#   degerleri kullaniyordu; "otomatik" onlari DEGISTIRMEZ, model 2B <-> 3B
#   degisince agin da degismesini saglar.
ENTROPI_RADYAL = 8
ENTROPI_EKSENEL = 8


def entropi_boyutu_otomatik(spec):
    """Modelin boyutuna gore entropi agi bolmeleri [nx, ny, nz]."""
    from cekirdek import sema
    h = sema.model_yuksekligi(spec or {}) if (spec or {}).get("kor") else None
    return [ENTROPI_RADYAL, ENTROPI_RADYAL, ENTROPI_EKSENEL if h else 1]


def entropi_boyutu(spec):
    """
    Kurulacak entropi aginin bolmeleri. entropi_mesh.otomatik True ise
    modelden turetilir (entropi_boyutu_otomatik); degilse dosyadaki "boyut".
    """
    ent = ((spec or {}).get("ayarlar") or {}).get("entropi_mesh") or {}
    if ent.get("otomatik"):
        return entropi_boyutu_otomatik(spec)
    return list(ent.get("boyut") or [8, 8, 1])


def _f(d, ad, vars_=0.0):
    v = (d or {}).get(ad, vars_)
    return float(vars_ if v is None else v)


def enerji_dagilimi(e):
    """spec ayarlar.kaynak.enerji -> openmc.stats dagilimi"""
    e = e or {}
    tur = e.get("tur", "watt")

    if tur == "watt":
        return openmc.stats.Watt(a=_f(e, "a", 988.0e3), b=_f(e, "b", 2.249e-6))

    if tur == "maxwell":
        return openmc.stats.Maxwell(theta=_f(e, "theta", 1.2932e6))

    if tur == "tek":
        return openmc.stats.Discrete([_f(e, "enerji", 14.1e6)], [1.0])

    if tur == "ayrik":
        noktalar = e.get("noktalar") or []
        if not noktalar:
            raise ValueError("ayrık tayf: en az bir (enerji, olasılık) çifti gerekli")
        x = [float(p[0]) for p in noktalar]
        p = [float(p[1]) for p in noktalar]
        return openmc.stats.Discrete(x, p)

    if tur == "histogram":
        kenarlar = [float(x) for x in (e.get("kenarlar") or [])]
        degerler = [float(x) for x in (e.get("degerler") or [])]
        if len(kenarlar) < 2:
            raise ValueError("histogram tayf: en az iki grup kenarı gerekli")
        if len(degerler) != len(kenarlar) - 1:
            raise ValueError("histogram tayf: %d kenar için %d değer olmalı, %d verildi"
                             % (len(kenarlar), len(kenarlar) - 1, len(degerler)))
        # Tabular "histogram" modunda son deger kullanilmaz; uzunluklari
        # esitlemek icin sifir eklenir (XML semasi esit uzunluk bekler).
        return openmc.stats.Tabular(kenarlar, degerler + [0.0],
                                    interpolation="histogram")

    if tur == "fuzyon":
        return openmc.stats.muir(e0=_f(e, "e0", 14.08e6),
                                 m_rat=_f(e, "kutle_orani", 5.0),
                                 kt=_f(e, "iyon_sicaklik", 20.0e3))

    raise ValueError("bilinmeyen enerji tayfı türü: %s" % tur)


def _dik_referans(yon):
    """
    "yon"a dik bir birim vektor dondurur.

    OpenMC'nin PolarAzimuthal'i azimut acisini olcmek icin ikinci bir referans
    vektor ister ve varsayilani (1,0,0)'dir. Yon x ekseni boyunca oldugunda
    ikisi PARALEL olur ve OpenMC hata atar -- yani "koni, +x yonu" gibi son
    derece siradan bir istek cokuyordu. Burada yonun en kucuk bilesenli
    eksenini secip capraz carpim aliyoruz; bu her yon icin guvenli.
    """
    yon = [float(v) for v in yon]
    n = math.sqrt(sum(v * v for v in yon))
    u = [v / n for v in yon]
    k = min(range(3), key=lambda i: abs(u[i]))
    eksen = [0.0, 0.0, 0.0]
    eksen[k] = 1.0
    v = [u[1] * eksen[2] - u[2] * eksen[1],
         u[2] * eksen[0] - u[0] * eksen[2],
         u[0] * eksen[1] - u[1] * eksen[0]]
    m = math.sqrt(sum(x * x for x in v))
    return u, [x / m for x in v]


def aci_dagilimi(a):
    """spec ayarlar.kaynak.aci -> openmc.stats yon dagilimi (None = izotropik)"""
    a = a or {}
    tur = a.get("tur", "izotropik")
    if tur == "izotropik":
        return openmc.stats.Isotropic()

    yon = [float(x) for x in (a.get("yon") or [0.0, 0.0, 1.0])]
    if math.sqrt(sum(v * v for v in yon)) == 0.0:
        raise ValueError("kaynak yönü sıfır vektör olamaz")

    if tur == "tek_yon":
        return openmc.stats.Monodirectional(reference_uvw=yon)

    if tur == "koni":
        yari = _f(a, "koni_aci", 30.0)
        if not (0.0 < yari <= 180.0):
            raise ValueError("koninin yarı açılımı 0–180° arasında olmalı (%s)" % yari)
        # mu = cos(kutupsal aci), referans ekseni "yon". mu'da duzgun dagilim
        # koni yuzeyinde degil KATI ACIDA duzgun demektir -- dogrusu budur.
        u, v = _dik_referans(yon)
        mu = openmc.stats.Uniform(math.cos(math.radians(yari)), 1.0)
        fi = openmc.stats.Uniform(0.0, 2.0 * math.pi)
        return openmc.stats.PolarAzimuthal(mu=mu, phi=fi,
                                           reference_uvw=u, reference_vwu=v)

    raise ValueError("bilinmeyen açısal dağılım türü: %s" % tur)


def ortalama_enerji(e):
    """
    Tayfin ortalama enerjisi [eV]; bilinmiyorsa None.
    Analitik -- orneklemeye gerek yok, arayuzde aninda gosterilir.
    """
    e = e or {}
    tur = e.get("tur", "watt")
    if tur == "watt":
        a, b = _f(e, "a", 988.0e3), _f(e, "b", 2.249e-6)
        return 1.5 * a + a * a * b / 4.0
    if tur == "maxwell":
        return 1.5 * _f(e, "theta", 1.2932e6)
    if tur == "tek":
        return _f(e, "enerji", 14.1e6)
    if tur == "fuzyon":
        return _f(e, "e0", 14.08e6)
    if tur == "ayrik":
        n = e.get("noktalar") or []
        top = sum(float(p[1]) for p in n)
        if not n or top <= 0:
            return None
        return sum(float(p[0]) * float(p[1]) for p in n) / top
    if tur == "histogram":
        k = [float(x) for x in (e.get("kenarlar") or [])]
        d = [float(x) for x in (e.get("degerler") or [])]
        if len(k) < 2 or len(d) != len(k) - 1:
            return None
        agirlik = [d[i] * (k[i + 1] - k[i]) for i in range(len(d))]
        top = sum(agirlik)
        if top <= 0:
            return None
        return sum(agirlik[i] * 0.5 * (k[i] + k[i + 1]) for i in range(len(d))) / top
    return None


def en_yuksek_enerji(e):
    """Tayfin ust siniri [eV]; kutuphane enerji tavaniyla karsilastirmak icin."""
    e = e or {}
    tur = e.get("tur", "watt")
    if tur == "tek":
        return _f(e, "enerji", 14.1e6)
    if tur == "fuzyon":
        # Muir bir Gauss'tur; pratikte 5 sigma yeter.
        e0 = _f(e, "e0", 14.08e6)
        kt_kev = _f(e, "iyon_sicaklik", 20.0e3) / 1.0e3
        sigma = 177.0 * math.sqrt(max(kt_kev, 0.0)) * 1.0e3 / 2.3548
        return e0 + 5.0 * sigma
    if tur == "ayrik":
        n = e.get("noktalar") or []
        return max((float(p[0]) for p in n), default=None)
    if tur == "histogram":
        k = e.get("kenarlar") or []
        return float(k[-1]) if k else None
    # Watt ve Maxwell'in kuyrugu sonsuzdur; OpenMC ornekleri kutuphane
    # tavaninda keser, bu yuzden sinir kontrolu yapilmaz.
    return None


def kaynak_kur(k, uzay, kisit):
    """spec ayarlar.kaynak + hazir uzay dagilimi -> openmc.IndependentSource"""
    k = k or {}
    return openmc.IndependentSource(
        space=uzay,
        angle=aci_dagilimi(k.get("aci")),
        energy=enerji_dagilimi(k.get("enerji")),
        strength=_f(k, "kuvvet", 1.0),
        particle=k.get("parcacik") or "neutron",
        constraints=kisit,
    )


def ozet(k):
    """Kaynagi tek satirda anlatir (arayuz ve terminal ciktisi icin)."""
    k = k or {}
    e = k.get("enerji") or {}
    tur = e.get("tur", "watt")
    ad = dict(TAYFLAR).get(tur, tur)
    ort = ortalama_enerji(e)
    parca = "foton" if (k.get("parcacik") == "photon") else "nötron"
    metin = "%s, %s" % (parca, ad)
    if ort is not None:
        metin += " (ortalama %s)" % enerji_metni(ort)
    aci = (k.get("aci") or {}).get("tur", "izotropik")
    metin += ", %s" % dict(ACILAR).get(aci, aci)
    return metin


def enerji_metni(ev):
    """eV -> okunabilir birim. 0.0253 eV ile 14 MeV ayni bicimde okunamaz."""
    if ev is None:
        return "—"
    ev = float(ev)
    if ev >= 1.0e6:
        return "%.3g MeV" % (ev / 1.0e6)
    if ev >= 1.0e3:
        return "%.3g keV" % (ev / 1.0e3)
    return "%.3g eV" % ev


# ----------------------------------------------------------------------------
# Betik uretimi
#   Uretilen betik TEK BASINA calisir; bu paketi import edemez. Bu yuzden
#   ayni esleme burada bir kez daha, bu sefer METIN olarak yazilir. Ikisi
#   yan yana dursun ki ayrisma gozle gorulsun; test ikisinin ayni k-eff'i
#   verdigini zaten dogruluyor.
# ----------------------------------------------------------------------------

def enerji_kod(e):
    """enerji_dagilimi() ile ayni dagilimi ureten Python kaynak metni."""
    e = e or {}
    tur = e.get("tur", "watt")
    if tur == "watt":
        return "openmc.stats.Watt(a=%r, b=%r)" % (_f(e, "a", 988.0e3), _f(e, "b", 2.249e-6))
    if tur == "maxwell":
        return "openmc.stats.Maxwell(theta=%r)" % _f(e, "theta", 1.2932e6)
    if tur == "tek":
        return "openmc.stats.Discrete([%r], [1.0])" % _f(e, "enerji", 14.1e6)
    if tur == "ayrik":
        n = e.get("noktalar") or []
        return "openmc.stats.Discrete(%r, %r)" % ([float(p[0]) for p in n],
                                                  [float(p[1]) for p in n])
    if tur == "histogram":
        k = [float(x) for x in (e.get("kenarlar") or [])]
        d = [float(x) for x in (e.get("degerler") or [])]
        return ("openmc.stats.Tabular(%r, %r,\n"
                "                     interpolation='histogram')" % (k, d + [0.0]))
    if tur == "fuzyon":
        return ("openmc.stats.muir(e0=%r, m_rat=%r, kt=%r)"
                % (_f(e, "e0", 14.08e6), _f(e, "kutle_orani", 5.0),
                   _f(e, "iyon_sicaklik", 20.0e3)))
    raise ValueError("bilinmeyen enerji tayfı türü: %s" % tur)


def aci_kod(a):
    """aci_dagilimi() ile ayni dagilimi ureten Python kaynak metni."""
    a = a or {}
    tur = a.get("tur", "izotropik")
    if tur == "izotropik":
        return "openmc.stats.Isotropic()"
    yon = [float(x) for x in (a.get("yon") or [0.0, 0.0, 1.0])]
    if tur == "tek_yon":
        return "openmc.stats.Monodirectional(reference_uvw=%r)" % (yon,)
    if tur == "koni":
        mu0 = math.cos(math.radians(_f(a, "koni_aci", 30.0)))
        u, v = _dik_referans(yon)
        return ("openmc.stats.PolarAzimuthal(\n"
                "    mu=openmc.stats.Uniform(%r, 1.0),\n"
                "    phi=openmc.stats.Uniform(0.0, %r),\n"
                "    reference_uvw=%r,\n"
                "    reference_vwu=%r)" % (mu0, 2.0 * math.pi, u, v))
    raise ValueError("bilinmeyen açısal dağılım türü: %s" % tur)
