# -*- coding: utf-8 -*-
"""
 test_y8_kosu.py  --  v3 Y8: CE -> MGXS -> MG MC -> random ray (kuyruk ile)

 HIZLI: karsilastirma tablosu (fark pcm, birlesik sapma, sure, son tamamlanan),
        random ray ayari dogrulama ve varsayilanlari, rr_modeli MG ister.
 YAVAS (pin hucre, yansitici = sonsuz kafes):
   1) 2 grup, tek bolge (demet): GxG ozdeger k_inf CE k ile tutarli
      (|fark| <= 4 sigma_CE); ayni sabitlerle MG MC (3 sigma_MG) ve random ray
      (homojen ortamda duz kaynak TAM: |fark| <= 1e-4) ozdegerle ayni.
   2) CASMO-70, malzeme bolgesi: ayni geometri MG MC CE'ye <= 500 pcm
      (homojenlestirme + grup yogunlastirmasi + izotropik sacilma; olculen
      -67 +- 180 pcm, 10^4 x 40 cevrim); random ray MG MC'ye <= 300 pcm
      (yontem farki: duz kaynak, bolme yok, 300 pasif; olculen -10 +- 110 pcm;
      13x13 bolmede -57).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import os
from types import SimpleNamespace

from cekirdek import sema
from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI

_K_SIGMA = 4.0          # ozdeger ile CE: iliskili ama ayni olmayan iki tahminci
_MG_SIGMA = 3.0
_RR_HOMOJEN_TOL = 1e-4  # homojen ortamda duz kaynak kesin; RR sapmasi ~1e-7
_MG_CE_PCM = 500.0      # ince grup ayni geometri (bkz. modul notu)
_RR_MG_PCM = 300.0      # yontem farki (bkz. modul notu)
_PARCACIK, _CEVRIM, _PASIF = 10000, 60, 20


def _durum(tur, k, s, bas=0.0, bit=1.0):
    from cekirdek import kuyruk
    return SimpleNamespace(etiket={"y8": tur}, k=(k, s), asama=kuyruk.Asama.BITTI,
                           baslangic=bas, bitis=bit)


def test_karsilastirma_tablosu():
    print("\n[Y8-I1] karsilastirma: fark pcm = (k-k_CE)1e5, sapma hypot, RR'de MG farki")
    import math
    from cekirdek import mgxs_is
    # Arrange
    ds = [_durum("ce", 1.30000, 0.00100, 0, 10), _durum("mg", 1.29900, 0.00050, 0, 4),
          _durum("rr", 1.29950, 0.00020, 0, 2)]
    # Act
    s = {x.tur: x for x in mgxs_is.karsilastirma(ds)}
    # Assert
    kontrol("MG -100 pcm", abs(s["mg"].fark_pcm + 100.0) < 1e-6, "-> %r" % (s["mg"],))
    kontrol("MG sapma hypot", abs(s["mg"].fark_sapma_pcm - math.hypot(50, 100)) < 1e-6)
    kontrol("RR MG'ye +50 pcm", abs(s["rr"].mg_fark_pcm - 50.0) < 1e-6)
    kontrol("sureler", (s["ce"].sure_s, s["rr"].sure_s) == (10.0, 2.0))
    kontrol("CE farki yok", s["ce"].fark_pcm is None)
    kontrol("bos liste", mgxs_is.karsilastirma([]) == [])


def test_random_ray_ayar_dogrulama():
    print("\n[Y8-I2] RRAyar: gecersiz mesafe/cevrim/sekil/bolme ValueError")
    from cekirdek import random_ray as rr
    hata = 0
    for ek in ({"aktif_mesafe": 0.0}, {"cevrim": 10, "pasif": 10}, {"kaynak_sekli": "kup"},
               {"bolme": rr.EN_COK_BOLME + 1}, {"isin": 0}):
        alan = dict(olu_mesafe=30.0, aktif_mesafe=150.0)
        alan.update(ek)
        try:
            rr.RRAyar(**alan)
        except ValueError:
            hata += 1
    kontrol("bes gecersiz ayar", hata == 5, "-> %d" % hata)


def test_rr_varsayilan_ve_mg_sarti():
    print("\n[Y8-I3] varsayilan: L = max(kosegen, 30); aktif 5L; bolme yok")
    from cekirdek import kurucu, random_ray as rr
    # Arrange
    model, _b = kurucu.kur(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")))
    # Act
    a = rr.varsayilan(model)
    # Assert
    kontrol("olu 30 cm (pin kosegeni < 30)", a.olu_mesafe == 30.0, "-> %r" % (a,))
    kontrol("aktif 150 cm", a.aktif_mesafe == 150.0)
    kontrol("bolme yok", a.bolme == 0)
    try:
        rr.rr_modeli(model, a)
        kontrol("CE modelde ValueError", False)
    except ValueError:
        kontrol("CE modelde ValueError", True)


def test_kapsam_secenekleri_ve_demet_alt_modeli():
    print("\n[Y8-I4] kapsam: tek demet/pin modelde yalniz tum model; kor -> demet basina alt model")
    from cekirdek import mgxs_is
    # Arrange
    kor = sema.yukle(os.path.join(ORNEK, "pwr_smr_kor.json"))
    pin = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    # Act
    sk, sp = mgxs_is.kapsam_secenekleri(kor), mgxs_is.kapsam_secenekleri(pin)
    alt = mgxs_is.kapsam_spec(kor, "demet_24")
    # Assert
    kontrol("pin: yalniz tum model", [a for a, _m in sp] == [None], "-> %r" % (sp,))
    kontrol("kor: tum model + 2 demet", [a for a, _m in sk] == [None, "demet_24", "demet_31"])
    kontrol("alt model tek demet, yansitici", alt["kor"]["tur"] == "tek_demet"
            and set(alt["kor"]["sinir"].values()) == {"reflective"}, "-> %r" % (alt["kor"].get("sinir"),))
    kontrol("tum model: ayni spec", mgxs_is.kapsam_spec(kor, None) is kor)


def _mg_kur(bolge, gecici):
    from cekirdek import kurucu, mg_model, mgxs_uret as mu
    spec = mu.ile(_pin(), mu.MgxsAyar(True, bolge, "CASMO-2"))
    _m, b = kurucu.kur(spec)
    adlar = mu.xsdata_adlari(b["mgxs"])
    h5 = os.path.join(gecici, "mgxs.h5")
    open(h5, "wb").close()                  # icerigi model kurulumunda okunmaz
    from cekirdek import onbellek
    ozet = {"ayar": {"bolge": bolge}, "adlar": {str(k): v for k, v in adlar.items()},
            "spec_ozeti": onbellek.ozet(spec)}
    return spec, ozet, h5, adlar, mg_model


def test_mg_modeli_kosusuz():
    print("\n[Y8-I5] MG model: makroskopik malzemeler, tally yok, MG kipi; eksik ad ValueError")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        # Arrange
        spec, ozet, h5, adlar, mg_model = _mg_kur("malzeme", d)
        # Act
        m = mg_model.mg_modeli(spec, ozet, h5)
        # Assert
        makro = sorted(mat._macroscopic for mat in m.materials)
        kontrol("MG kipi", m.settings.energy_mode == "multi-group")
        kontrol("tally yok", len(m.tallies) == 0)
        kontrol("her malzeme kendi xsdata'si", makro == sorted(adlar.values()), "-> %r" % makro)
        kontrol("kutuphane yolu mutlak", str(m.materials.cross_sections) == os.path.abspath(h5))
        eksik = dict(ozet, adlar={})
        try:
            mg_model.mg_modeli(spec, eksik, h5)
            kontrol("eksik ad ValueError", False)
        except ValueError:
            kontrol("eksik ad ValueError", True)
        try:
            mg_model.mg_modeli(spec, ozet, os.path.join(d, "yok.h5"))
            kontrol("kutuphane yok FileNotFoundError", False)
        except FileNotFoundError:
            kontrol("kutuphane yok FileNotFoundError", True)


def test_mg_modeli_hucre_demet_ve_random_ray():
    print("\n[Y8-I6] hucre: hucre basina yeni malzeme; demet: tek xsdata; RR ayarlari yazilir")
    import tempfile
    from cekirdek import random_ray as rr
    with tempfile.TemporaryDirectory() as d:
        # Arrange / Act
        spec, ozet, h5, adlar, mg_model = _mg_kur("hucre", d)
        mh = mg_model.mg_modeli(spec, ozet, h5)
        spec_d, ozet_d, h5_d, adlar_d, _mm = _mg_kur("demet", d)
        md = mg_model.mg_modeli(spec_d, ozet_d, h5_d)
        a = rr.ayar_degistir(rr.varsayilan(md), bolme=4, kaynak_sekli="linear")
        r = rr.rr_modeli(md, a)
        # Assert
        hucre_adlari = sorted(m._macroscopic for m in mh.materials)
        kontrol("hucre adlari", hucre_adlari == sorted(adlar.values()), "-> %r" % hucre_adlari)
        kontrol("demet tek xsdata", {m._macroscopic for m in md.materials} == set(adlar_d.values()))
        anahtar = set(r.settings.random_ray)
        kontrol("RR anahtarlari", {"distance_inactive", "distance_active", "ray_source",
                                    "source_shape", "source_region_meshes"} <= anahtar, "-> %r" % anahtar)
        kontrol("RR: entropi mesh'i yok, kaynak bos", r.settings.entropy_mesh is None
                and len(r.settings.source) == 0)
        kontrol("RR girdisi degismedi", not md.settings.random_ray)
        kontrol("isin/cevrim", (r.settings.particles, r.settings.batches, r.settings.inactive)
                == (a.isin, a.cevrim, a.pasif))


def test_hazirlik_kilidi_genel_ve_ayni_nesne():
    print("\n[Y8-I7] kuyruk.hazirlik_kilidi() genel ad; kuyrugun ic kilidiyle AYNI nesne; Y8 ozel adi kullanmaz")
    import inspect
    from cekirdek import kuyruk, mgxs_is, mgxs_uret
    # Act
    kilit = kuyruk.hazirlik_kilidi()
    # Assert
    kontrol("genel sabit ile ayni", kilit is kuyruk.HAZIRLIK_KILIDI)
    kontrol("ic kullanim ayni nesne", kilit is kuyruk._HAZIRLIK_KILIDI)
    kod = inspect.getsource(mgxs_is) + inspect.getsource(mgxs_uret)
    kontrol("Y8 ozel adi kullanmaz", "_HAZIRLIK_KILIDI" not in kod)


def test_openmc_ic_ayrinti_varsayimlari():
    print("\n[Y8-I8] OpenMC ic ayrintilari (0.16): Material._nuclides/_sab, Settings._entropy_mesh;"
          " surum degisince KIRMIZI")
    import openmc
    from cekirdek import mg_model
    # Arrange
    m = openmc.Material()
    m.add_nuclide("H1", 1.0)
    s = openmc.Settings()
    # Act / Assert
    kontrol("dogrulanan surum", openmc.__version__.startswith(mg_model.DOGRULANAN_OPENMC),
            "-> %s (bkz. mg_model._makro, random_ray.rr_modeli)" % openmc.__version__)
    kontrol("Material._nuclides liste", isinstance(m._nuclides, list) and len(m._nuclides) == 1)
    kontrol("Material._sab liste", isinstance(m._sab, list))
    kontrol("Settings._entropy_mesh okunur", s._entropy_mesh is None and s.entropy_mesh is None)
    kontrol("surum uyarisi uyumlu surumde yok", mg_model.surum_uyarisi() is None)


def test_mg_modeli_eski_ozet_acik_hata():
    print("\n[Y8-I9] spec'e malzeme eklenip ozet eskiyse (kimlik kaydi) MG modeli ACIK hata verir")
    import copy
    import tempfile
    for bolge in ("malzeme", "hucre"):
        with tempfile.TemporaryDirectory() as d:
            # Arrange
            spec, ozet, h5, _adlar, mg_model = _mg_kur(bolge, d)
            yeni = copy.deepcopy(spec)
            ek = copy.deepcopy(yeni["malzemeler"][0])
            ek["ad"] = "yeni_malzeme"
            yeni["malzemeler"].insert(0, ek)       # kimlikler kayar
            # Act / Assert
            try:
                mg_model.mg_modeli(yeni, ozet, h5)
                kontrol("%s: eski ozet ValueError" % bolge, False)
            except ValueError as e:
                kontrol("%s: eski ozet ValueError" % bolge, "eşleşmiyor" in str(e), "-> %s" % e)
        # parmak izi olmayan (eski) ozette kimlik+ad denetimi tek basina yakalar
        with tempfile.TemporaryDirectory() as d:
            spec, ozet, h5, _adlar, mg_model = _mg_kur("malzeme", d)
            yeni = copy.deepcopy(spec)
            yeni["malzemeler"].insert(0, dict(copy.deepcopy(yeni["malzemeler"][0]), ad="ek"))
            eski = {k: v for k, v in ozet.items() if k != "spec_ozeti"}
            try:
                mg_model.mg_modeli(yeni, eski, h5)
                kontrol("parmak izsiz: kimlik/ad ValueError", False)
            except ValueError as e:
                kontrol("parmak izsiz: kimlik/ad ValueError", "eşleşmiyor" in str(e))


# ---------------------------------------------------------------------------
# YAVAS
# ---------------------------------------------------------------------------

def _pin():
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"].update(parcacik=_PARCACIK, cevrim=_CEVRIM, pasif=_PASIF)
    return spec


def _kos(isler):
    from cekirdek import kuyruk
    with kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=ISLEM_PARCACIGI) as q:
        kimlikler = [q.ekle(i) for i in isler]
        q.baslat()
        q.bekle()
        return [q.durum(k) for k in kimlikler]


def _ce(spec, a, gecici):
    from cekirdek import mgxs_is
    d, = _kos([mgxs_is.ce_isi(spec, a, os.path.join(gecici, "ce"), ISLEM_PARCACIGI)])
    kontrol("CE bitti", d.asama.value == "bitti", "-> %s %s" % (d.asama, d.hata))
    return d


def test_iki_grup_homojen_k_inf(gecici):
    print("\n[Y8-Y1] 2 grup, demet (tek bolge): ozdeger k_inf = CE; MG MC ve RR ayni sabitlerle")
    from cekirdek import mgxs_is, mgxs_uret as mu
    # Arrange
    spec = _pin()
    a = mu.MgxsAyar(True, "demet", "CASMO-2")
    # Act
    ce = _ce(spec, a, gecici)
    s = ce.sonuc["mgxs"]
    ce_spec = mu.ile(spec, a)
    mg, rr = _kos([mgxs_is.mg_isi(ce_spec, ce.dizin, os.path.join(gecici, "mg"),
                                  ISLEM_PARCACIGI),
                   mgxs_is.rr_isi(ce_spec, ce.dizin, os.path.join(gecici, "rr"),
                                  ISLEM_PARCACIGI)])
    # Assert
    koz, kce = s.k_ozdeger, s.k_ce
    kontrol("mgxs.h5 ve CSV", os.path.isfile(s.h5) and os.path.isfile(s.csv))
    kontrol("ozdeger ~ CE (4 sigma_CE)", abs(koz.ort - kce.ort) <= _K_SIGMA * kce.sapma,
            "-> %.5f / %.5f +- %.5f (fark %.0f pcm)"
            % (koz.ort, kce.ort, kce.sapma, (koz.ort - kce.ort) * 1e5))
    kontrol("MG MC ~ ozdeger (3 sigma)", abs(mg.k[0] - koz.ort) <= _MG_SIGMA * mg.k[1],
            "-> %r" % (mg.k,))
    kontrol("RR = ozdeger (homojen, duz kaynak kesin)", abs(rr.k[0] - koz.ort) <= _RR_HOMOJEN_TOL,
            "-> %r / %.6f" % (rr.k, koz.ort))
    kontrol("k_oran (n,xn'siz) tanimli", s.k_oran is not None and s.k_oran.ort > 1.0,
            "-> %r" % (s.k_oran,))
    tablo = mgxs_is.karsilastirma([ce, mg, rr])
    kontrol("karsilastirma 3 satir", [t.tur for t in tablo] == ["ce", "mg", "rr"])


def test_ince_grup_mg_ve_random_ray(gecici):
    print("\n[Y8-Y2] CASMO-70 malzeme: MG MC ~ CE (500 pcm), RR ~ MG (300 pcm)")
    from cekirdek import mgxs_is, mgxs_uret as mu, random_ray
    # Arrange
    spec = _pin()
    a = mu.MgxsAyar(True, "malzeme", "CASMO-70")
    # Act
    ce = _ce(spec, a, gecici)
    ce_spec = mu.ile(spec, a)
    rra = mgxs_is.rr_varsayilan(ce_spec, ce.dizin)
    mg, rr = _kos([mgxs_is.mg_isi(ce_spec, ce.dizin, os.path.join(gecici, "mg"),
                                  ISLEM_PARCACIGI),
                   mgxs_is.rr_isi(ce_spec, ce.dizin, os.path.join(gecici, "rr"),
                                  ISLEM_PARCACIGI, rra)])
    # Assert
    t = {x.tur: x for x in mgxs_is.karsilastirma([ce, mg, rr])}
    kontrol("MG MC - CE <= 500 pcm", abs(t["mg"].fark_pcm) <= _MG_CE_PCM,
            "-> %.0f +- %.0f pcm" % (t["mg"].fark_pcm, t["mg"].fark_sapma_pcm))
    kontrol("RR - MG <= 300 pcm", abs(t["rr"].mg_fark_pcm) <= _RR_MG_PCM,
            "-> %.0f pcm (RR %.5f +- %.5f)" % (t["rr"].mg_fark_pcm, t["rr"].k, t["rr"].sapma))
    print("  [OLCUM] CE %.5f, MG %+.0f pcm, RR %+.0f pcm (MG'ye %+.0f), sure CE/MG/RR %s"
          % (t["ce"].k, t["mg"].fark_pcm, t["rr"].fark_pcm, t["rr"].mg_fark_pcm,
             ["%.0f s" % x.sure_s for x in t.values()]))


HIZLI = [test_karsilastirma_tablosu, test_random_ray_ayar_dogrulama, test_rr_varsayilan_ve_mg_sarti,
         test_kapsam_secenekleri_ve_demet_alt_modeli, test_mg_modeli_kosusuz,
         test_mg_modeli_hucre_demet_ve_random_ray, test_hazirlik_kilidi_genel_ve_ayni_nesne,
         test_openmc_ic_ayrinti_varsayimlari, test_mg_modeli_eski_ozet_acik_hata]
YAVAS = [test_iki_grup_homojen_k_inf, test_ince_grup_mg_ve_random_ray]
