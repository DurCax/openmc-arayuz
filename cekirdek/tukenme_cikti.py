# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_cikti.py  --  Tukenme sonucundan aktivite, bozunma isisi, foton
                       kaynagi, temas doz hizi ve atik sinifi (v3 Y4)
================================================================================

 KAYNAKLAR (hepsi OpenMC 0.16; elle hesap YOK)
   aktivite        openmc.Material.get_activity(units="Bq")  -- lambda N;
                   yari omur zincirden (chain_file), zincirde olmayan
                   nuklidler icin OpenMC'nin ENDF/B-VIII.0 verisi.
   bozunma isisi   openmc.Material.get_decay_heat(units="W") -- lambda N Q;
                   Q = zincirdeki decay_energy (ENDF/B-VIII.0 bozunum alt
                   kutuphanesinin ortalama isik + EM + agir parcacik
                   enerjisi). Notrino enerjisi DAHIL DEGIL.
   foton kaynagi   openmc.Material.get_decay_photon_energy(units="Bq"):
                   integral = foton/s; dagilim zincirdeki foton spektrumu.
   temas doz hizi  openmc.Material.get_photon_contact_dose_rate():
                   FISPACT-II yontemi (UKAEA-CCFE-RE(21)02, Ek C.7.1): yari
                   sonsuz levha yuzeyinde havada sogurulan doz [Gy/h],
                   birikim katsayisi 2. Bremsstrahlung YOK.
   atik sinifi     openmc.Material.waste_classification(): ABD NRC 10 CFR
                   61.55 yakin-yuzey sinifi (A, B, C, GTCC). Kullanilmis
                   yakit yuksek duzeyli atiktir; sinif BILGI amaclidir,
                   sertifika degildir.

 Zincir: kosunun zinciri openmc.config["chain_file"]'a gecici yazilir (Q ve
 foton verisi oradan okunur; OpenMC degistiginde onbellegini temizler).
 Kilitli: arayuzun arka plan iscileri ayni anda okuyabilir.
================================================================================
"""

from __future__ import annotations

import contextlib
import csv
import io
import threading

from cekirdek.ceviri import _

_ZINCIR_KILIDI = threading.RLock()
_SANIYE_GUN = 86400.0
SERI_ANAHTARLARI = ("aktivite", "aktivite_ozgul", "isi", "isi_ozgul", "foton")
# CSV sutun birimleri (seri anahtari -> birim)
BIRIMLER = {"aktivite": "Bq", "aktivite_ozgul": "Bq/g", "isi": "W",
            "isi_ozgul": "W/g", "foton": "1/s"}


@contextlib.contextmanager
def zincir_ortami(zincir_yolu: str | None):
    """openmc.config["chain_file"]'i gecici olarak zincir_yolu yapar."""
    import openmc
    with _ZINCIR_KILIDI:
        eski = openmc.config.get("chain_file")
        degisti = zincir_yolu and str(eski) != str(zincir_yolu)
        if degisti:
            openmc.config["chain_file"] = zincir_yolu
        try:
            yield
        finally:
            if degisti:
                if eski is None:
                    del openmc.config["chain_file"]
                else:
                    openmc.config["chain_file"] = eski


def _adim_degerleri(malzeme) -> dict:
    """Tek adim, tek malzeme: SERI_ANAHTARLARI degerleri."""
    kutle = malzeme.get_mass()                       # g
    aktivite = float(malzeme.get_activity(units="Bq"))
    isi = float(malzeme.get_decay_heat(units="W"))
    dagilim = malzeme.get_decay_photon_energy(units="Bq")
    foton = float(dagilim.integral()) if dagilim is not None else 0.0
    return {"aktivite": aktivite, "isi": isi, "foton": foton,
            "aktivite_ozgul": aktivite / kutle if kutle > 0 else 0.0,
            "isi_ozgul": isi / kutle if kutle > 0 else 0.0}


def seriler(r, ad_by_id: dict, zincir_yolu: str | None) -> dict:
    """
    DONER {"zaman_d": [gun], "malzeme": {ad: {anahtar: [deger]}},
           "toplam": {"aktivite", "isi", "foton": [..]}} (SERI_ANAHTARLARI).
    r: openmc.deplete.Results; ad_by_id: {malzeme_id: gorunen ad}.
    """
    zaman = [float(t) / _SANIYE_GUN for t in r.get_times(time_units="s")]
    malzeme = {}
    with zincir_ortami(zincir_yolu):
        for mid in r[0].index_mat:
            ad = ad_by_id.get(str(mid), str(mid))
            adimlar = [_adim_degerleri(adim.get_material(mid)) for adim in r]
            malzeme[ad] = {a: [d[a] for d in adimlar] for a in SERI_ANAHTARLARI}
    toplam = {a: [sum(v) for v in zip(*(m[a] for m in malzeme.values()))]
              for a in ("aktivite", "isi", "foton")}
    return {"zaman_d": zaman, "malzeme": malzeme, "toplam": toplam}


ATIK_UYGULANAMAZ = "uygulanamaz"
_ATIK_TABLOLARI = ("NRC_long", "NRC_short_A", "NRC_short_B", "NRC_short_C")


def atik_sinifi(m) -> str:
    """10 CFR 61.55 tablo karsilastirmasi; malzemede tablo nuklidi yoksa
    (taze/az yanmis yakit) OpenMC "Class A" doner (§61.55(a)(6)) -- bu bir
    siniflandirma degil, tablonun uygulanamamasidir: ATIK_UYGULANAMAZ."""
    if not any(m.waste_disposal_rating(limits=t, metal=True) > 0.0 for t in _ATIK_TABLOLARI):
        return ATIK_UYGULANAMAZ
    return m.waste_classification()


def doz_ve_atik(r, ad_by_id: dict, zincir_yolu: str | None, adim: int = -1) -> dict:
    """{ad: {"doz_gy_h": float, "atik_sinifi": str}} -- secilen adimda.
    Doz: yari sonsuz levha, yalniz yakit, havada sogurulan doz (ust sinir
    gostergesi; hacimden bagimsiz). atik_sinifi: ATIK_UYGULANAMAZ olabilir.
    Malzeme basina hata metni "hata" anahtarinda (sessiz degil)."""
    from cekirdek.gunluk import kaydedici
    sonuc = {}
    with zincir_ortami(zincir_yolu):
        for mid in r[adim].index_mat:
            ad = ad_by_id.get(str(mid), str(mid))
            m = r[adim].get_material(mid)
            try:
                sonuc[ad] = {"doz_gy_h": float(m.get_photon_contact_dose_rate()),
                             "atik_sinifi": atik_sinifi(m)}
            except (ValueError, KeyError, RuntimeError) as e:
                kaydedici(__name__).warning("doz/atik hesaplanamadi (%s): %s", ad, e)
                sonuc[ad] = {"doz_gy_h": float("nan"), "atik_sinifi": "",
                             "hata": str(e)}
    return sonuc


def foton_spektrumu(r, mid: str, zincir_yolu: str | None, adim: int = -1) -> tuple:
    """(enerjiler [eV], yogunluk [foton/s]) -- ayrik cizgiler; sürekli
    bilesen (varsa) dagilimin ayriklastirilmis hali. Foton yoksa ([], [])."""
    with zincir_ortami(zincir_yolu):
        d = r[adim].get_material(mid).get_decay_photon_energy(units="Bq")
    if d is None:
        return [], []
    x = getattr(d, "x", None)
    p = getattr(d, "p", None)
    if x is None or p is None:
        return [], []
    return [float(e) for e in x], [float(w) for w in p]


def csv_metni(s: dict) -> str:
    """Seriler CSV'si: gun + malzeme basina her seri (birimli baslik)."""
    tampon = io.StringIO()
    yaz = csv.writer(tampon, lineterminator="\n")
    adlar = list(s["malzeme"])
    baslik = ["gun"] + ["%s %s [%s]" % (ad, a, BIRIMLER[a])
                        for ad in adlar for a in SERI_ANAHTARLARI]
    yaz.writerow(baslik)
    for i, t in enumerate(s["zaman_d"]):
        yaz.writerow(["%.10g" % t] + ["%.10g" % s["malzeme"][ad][a][i]
                                      for ad in adlar for a in SERI_ANAHTARLARI])
    return tampon.getvalue()


def cikti_oku(h5: str, spec: dict) -> dict:
    """Arayuz icin: seriler + zincir yolu (kosunun zinciri; spec kaydindan)."""
    from cekirdek import tukenme
    r, ad_by_id, _hacim = tukenme._sonuc_kaynagi(h5, spec)
    yol = tukenme.zincir_secimi(spec)["yol"]
    s = seriler(r, ad_by_id, yol)
    s["zincir"] = yol
    return s


def birim_aciklamasi() -> str:
    """Arayuz/kilavuz notu: birimler ve kaynaklar (etkin dilde)."""
    return _("Aktivite Bq, Bq/g (malzeme kütlesi başına); bozunma ısısı W, W/g (Q: zincirin "
             "bozunma enerjisi, nötrino hariç); foton kaynağı foton/s. Temas doz hızı "
             "FISPACT-II yöntemi (yarı sonsuz levha, yalnız yakıt, havada soğurulan doz "
             "[Gy(hava) ≠ Sv]; hacimden bağımsız, kılıf yok: üst sınır göstergesi); atık "
             "sınıfı NRC 10 CFR 61.55 tablo karşılaştırması (yakın-yüzey; kullanılmış "
             "yakıt için geçerli değil) — bilgi amaçlıdır, sertifika değildir. Bozunma "
             "ısısında λ ENDF/B-VIII.0 yarı ömründen, Q zincirden; aktivitede λ zincirden "
             "alınır (zincir ≠ ENDF/B-VIII.0 ise ikisi birbirini tutmaz).")
