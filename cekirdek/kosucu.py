# -*- coding: utf-8 -*-
"""
================================================================================
 kosucu.py  --  Modeli calistir, ciktiyi ayristir, sonucu oku
================================================================================

 Qt'den BAGIMSIZDIR. Arayuz tarafi (arayuz/sekme_calistir.py) ayni islevi
 QProcess ile sarar; burada altyapi subprocess'tir, boylece terminalden de
 kullanilabilir.

 KULLANIM (terminal)
   python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json
   python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json --dizin /tmp/deneme -s 24
   python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json --sadece-dogrula
   python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json --betik model.py

 KULLANIM (kutuphane)
   from cekirdek import kosucu
   sonuc = kosucu.calistir(spec, "kosu", geri_cagir=lambda s: print(s))

 CIKTI DIZINI
   Kosu dizininde model.xml, statepoint.*.h5, summary.h5 ve kosu.log yan yana
   durur -- mevcut projelerdeki "yerinde kosu" duzenine uygun.
================================================================================
"""

import os
import re
import shutil
import subprocess
import sys
import time

from cekirdek import sema, kurucu, dogrula
from cekirdek import kaynak as _kaynak
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.uygunluk_denetimi import ayristir as _ayristir

_log = kaydedici(__name__)

# OpenMC cevrim satiri iki bicimde gelir:
#   entropi YOK :  "  54/1   1.32041   1.36400 +/- 0.00368"
#   entropi VAR :  "  54/1   1.32041   5.94225   1.36400 +/- 0.00368"
#                                      ^^^^^^^ Shannon entropisi
# Pasif cevrimlerde "ortalama +/- sapma" sutunlari bulunmaz.
#
# !!! Once bu desen yalnizca ucuncu bicimi taniyordu ve entropi acikken
# TUM cevrim satirlari sessizce atlaniyordu (ilerleme cubugu ve yakinsama
# grafigi bos kaliyordu). Sayilari genel olarak ayristirip sutun SAYISINDAN
# karar vermek bu tur bir sessiz kirilmayi onler.
_CEVRIM_DESEN = re.compile(
    r"^\s*(\d+)/(\d+)\s+([0-9.eE+-]+(?:\s+[0-9.eE+-]+)*?)"
    r"(?:\s+([0-9.eE+-]+)\s+\+/-\s+([0-9.eE+-]+))?\s*$")


def cevrim_satiri(satir):
    """
    Cevrim satirini ayristirir; entropi sutunu varsa da yoksa da calisir.

    DONER {"cevrim","nesil","k","entropi","ortalama","sapma"} ya da None.
    """
    m = _CEVRIM_DESEN.match(satir)
    if not m:
        return None
    try:
        sutunlar = [float(x) for x in m.group(3).split()]
    except ValueError:
        return None
    if not sutunlar or len(sutunlar) > 2:
        return None
    return {
        "cevrim": int(m.group(1)),
        "nesil": int(m.group(2)),
        "k": sutunlar[0],
        "entropi": sutunlar[1] if len(sutunlar) > 1 else None,
        "ortalama": float(m.group(4)) if m.group(4) else None,
        "sapma": float(m.group(5)) if m.group(5) else None,
    }


# Sabit kaynak modunda OpenMC cevrim basina tek bir satir yazar ve k-eff
# sutunu yoktur:  " Simulating batch 7"   (bkz. ornekler/kosu_zirh/kosu.log)
# cevrim_satiri() bunu tanimaz; tanimasaydi sabit kaynak kosusunda ilerleme
# cubugu hic ilerlemiyordu.
_SABIT_KAYNAK_DESEN = re.compile(r"^\s*Simulating batch\s+(\d+)\s*$")


def sabit_kaynak_cevrimi(satir):
    """' Simulating batch N' satirindan N'i dondurur; baska satirda None."""
    m = _SABIT_KAYNAK_DESEN.match(satir or "")
    return int(m.group(1)) if m else None


def keff_yorumu(k, sapma, beta_eff=None, sonsuz=False):
    """
    k-eff'i fiziksel olarak yorumlar.

    Bir sayinin kendisi bir seyi anlatmaz; reaktorun kritik olup olmadigi,
    ne kadar reaktivite fazlasi tasidigi ve bunun dolar cinsinden karsiligi
    anlatir. ($ = reaktivite / beta_eff; 1 $ ustu ANI KRITIK demektir ve
    reaktorun kontrolu gecikmis notronlara degil, ani notronlara kalir.)

    DONER (durum_metni, ayrinti_metni)
    """
    if k <= 0:
        return "geçersiz k-eff", ""
    rho = (k - 1.0) / k
    pcm = rho * 1.0e5
    s_pcm = (sapma / (k * k)) * 1.0e5

    if sonsuz:
        # Butun dis sinirlar sizintisiz: bu k∞'dur, bir reaktorun durumu degil.
        durum = ("k∞ (sonsuz ortam) — sızıntı yok, kritiklik hükmü verilmez; "
                 "sonlu bir reaktörde k-eff daha küçüktür")
    elif abs(k - 1.0) <= 2.0 * sapma:
        durum = "Kritik (k = 1'den istatistiksel olarak ayırt edilemez)"
    elif k > 1.0:
        durum = "Kritik üstü (k > 1 — güç artar)"
    else:
        durum = "Kritik altı (k < 1 — güç söner)"

    if sonsuz:
        parcalar = ["ρ∞ = %+.0f ± %.0f pcm (yakıtın taşıdığı reaktivite fazlası)" % (pcm, s_pcm)]
    else:
        parcalar = ["reaktivite = %+.0f ± %.0f pcm" % (pcm, s_pcm)]
    if beta_eff and beta_eff > 0:
        dolar = rho / beta_eff
        parcalar.append("%+.2f $ (β_eff = %.0f pcm)" % (dolar, beta_eff * 1e5))
        if dolar >= 1.0:
            # Bu ifadeyi dikkatli kurmak gerekir: sonsuz kafes (k-inf) hesabinda
            # 1 $ ustu bir deger bir GECICI REJIM degil, yakitin tasidigi
            # reaktivite fazlasidir ve kontrol sistemiyle dengelenir. Ayni sayi
            # gercek bir gecici rejimde ani kritiklik anlamina gelir. Kod hangi
            # durumda oldugunu bilemez, bu yuzden ikisini de soyler.
            parcalar.append("ρ > 1 $: gerçek bir geçici rejimde bu anlık kritiklik "
                            "demektir; sonsuz ortam (k∞) hesabında ise yakıtın "
                            "taşıdığı reaktivite fazlasıdır (kontrol sistemiyle "
                            "dengelenir)")
    return durum, "  |  ".join(parcalar)


def lambda_metni(lam, sapma):
    """
    Uretim zamanini okunabilir birimde yazar.
    Termal reaktorde ~20 us, hizli metal sistemde ~6 ns olabilir; sabit birim
    birini okunmaz yapar.
    """
    if lam >= 1e-6:
        return "%.2f ± %.2f µs" % (lam * 1e6, sapma * 1e6)
    if lam >= 1e-9:
        return "%.2f ± %.2f ns" % (lam * 1e9, sapma * 1e9)
    return "%.3e ± %.1e s" % (lam, sapma)


def entropi_yakinsama(entropiler, pasif):
    """
    Kaynak dagiliminin pasif cevrimler icinde yakinsayip yakinsamadigini
    degerlendirir.

    YONTEM
      Aktif cevrimlerdeki entropi sacilmasi (sigma) gurultu olcusu olarak
      alinir. Onemli olan kaynagin pasif donemin SONUNDA durmus olmasidir;
      basta hizla yukselmesi normaldir (nokta kaynaktan baslanirsa entropi
      sifirdan baslar). Bu yuzden yalnizca pasif donemin SON YARISI incelenir,
      o yari ikiye bolunur ve iki ceyregin ortalamalari karsilastirilir.
      Fark 2 sigmayi asiyorsa kaynak hala kayiyordur.

      (Ilk surumde pasif donemin TAMAMI ikiye bolunuyordu; bu, basta hizla
      yukselip sonra duzlesen -- yani yakinsamis -- kosulara yanlis alarm
      veriyordu. Godiva kriterinde tam olarak bu oldu.)

    DONER (yakinsadi_mi, mesaj) -- degerlendirilemezse (None, aciklama)
    """
    dizi = [e for e in entropiler if e is not None]
    if pasif < 4:
        return None, ("pasif çevrim sayısı (%d) kaynak yakınsamasını "
                      "değerlendirmek için çok az — en az 4, pratikte 20–50 "
                      "pasif çevrim kullanın" % pasif)
    if len(dizi) < 8 or len(dizi) <= pasif + 4:
        return None, ("aktif çevrim sayısı değerlendirme için yetersiz "
                      "(%d çevrim, %d pasif)" % (len(dizi), pasif))
    aktif = dizi[pasif:]
    ortalama = sum(aktif) / len(aktif)
    sigma = (sum((x - ortalama) ** 2 for x in aktif) / max(len(aktif) - 1, 1)) ** 0.5
    if sigma <= 0:
        return None, "entropi sabit; değerlendirilemedi"
    # Yalnizca pasif donemin son yarisi; o da ikiye bolunur.
    bas = pasif // 2
    orta = bas + (pasif - bas) // 2
    if orta <= bas or pasif <= orta:
        return None, "pasif çevrim sayısı bölünemeyecek kadar az"
    ceyrek1 = sum(dizi[bas:orta]) / (orta - bas)
    ceyrek2 = sum(dizi[orta:pasif]) / (pasif - orta)
    kayma = abs(ceyrek2 - ceyrek1)
    if kayma > 2.0 * sigma:
        return False, ("Kaynak dağılımı pasif dönemin sonunda hâlâ kayıyor "
                       "(kayma %.4f, aktif saçılma σ = %.4f). Pasif çevrim "
                       "sayısını artırın — k-eff yanlı olabilir."
                       % (kayma, sigma))
    return True, ("Kaynak dağılımı yakınsamış görünüyor "
                  "(pasif dönem sonunda kayma %.4f ≤ 2σ = %.4f)."
                  % (kayma, 2 * sigma))


def openmc_yolu():
    """openmc calistirilabilir dosyasinin yolu; bulunamazsa None."""
    return shutil.which("openmc")


# ============================================================================
# HAZIRLIK
# ============================================================================

def dizin_hazirla(dizin, temizle=True):
    """Kosu dizinini olusturur; temizle=True ise eski ciktilari siler."""
    if temizle and os.path.isdir(dizin):
        for ad in os.listdir(dizin):
            # particle_*.h5: kayip parcacik restart dosyasi; eskisi kalirsa
            # yeni kosuya kayip parcacik (K3) diye yanlis alarm verirdi.
            if (ad.startswith(("statepoint", "particle_")) or ad in ("summary.h5", "tallies.out",
                                                      "model.xml", "kosu.log",
                                                      "spec.json")):
                try:
                    os.remove(os.path.join(dizin, ad))
                except OSError:
                    pass
    os.makedirs(dizin, exist_ok=True)
    return dizin


def xml_yaz(spec, dizin):
    """Modeli kurar ve model.xml'i kosu dizinine yazar. DONER (model, bilgi, yol)"""
    # Kosu icin DAIMA taze model -- onbellekteki nesne paylasilir, uzerinde
    # calisma dizinine bagli islemler yapilmamalidir (bkz. onbellek.py).
    model, bilgi = kurucu.kur(spec)
    yol = os.path.join(dizin, "model.xml")
    model.export_to_model_xml(yol)
    # Kosunun modeli dizinde kalir: rapor (CLI ve arayuz) spec'i buradan okur.
    sema.kaydet(spec, os.path.join(dizin, "spec.json"))
    return model, bilgi, yol


# ============================================================================
# CALISTIRMA
# ============================================================================

def calistir(spec, dizin, geri_cagir=None, is_parcacigi=None, temizle=True,
             dogrulama=True, veri_kontrolu=True):
    """
    Modeli dogrular, kurar, XML yazar ve openmc'yi alt surec olarak calistirir.

    geri_cagir : her cikti satiri icin cagrilan fonksiyon -- f(satir, cevrim_bilgisi)
                 cevrim_bilgisi cevrim satiri degilse None'dir.
    dogrulama  : True (varsayilan) ise dogrula.kapi() kosu dizinine DOKUNMADAN
                 once cagrilir; hata bulgusu varsa dogrula.DogrulamaHatasi
                 firlatilir ve onceki kosunun dosyalari SILINMEZ. Spec'i zaten
                 dogrulamis cagiran (terminal girisi) False verir. (Parametre
                 adi 'dogrula' degildir: modul adini golgelerdi.)
                 Maliyet (olculdu, 29.09.2026): ornek modellerde ~30 ms (veri
                 denetimiyle), ~10 ms (verisiz) -- tarama / kritik arama /
                 coklu tohum her noktada dogrular.
    veri_kontrolu : kapiya iletilir (nukleer veri denetimi).
    DONER sozluk:
       {"basarili":bool, "cikis_kodu":int, "statepoint":yol|None,
        "sure":float, "log":yol, "cevrimler":[...],
        "cikti": uygunluk_denetimi.ayristir.CiktiOzeti (kayip parcacik, uyarilar)}
    """
    if dogrulama:
        dogrula.kapi(spec, veri_kontrolu=veri_kontrolu)
    dizin = dizin_hazirla(dizin, temizle=temizle)
    xml_yaz(spec, dizin)

    n = is_parcacigi or spec["calistirma"].get("is_parcacigi", 8)
    exe = openmc_yolu()
    if exe is None:
        raise RuntimeError("openmc çalıştırılabilir dosyası PATH'te bulunamadı "
                           "(conda ortamı etkin mi?)")

    komut = [exe, "-s", str(int(n))]
    log_yolu = os.path.join(dizin, "kosu.log")
    cevrimler = []
    t0 = time.time()

    with open(log_yolu, "w", encoding="utf-8") as log:
        log.write("# komut: %s\n# dizin: %s\n\n" % (" ".join(komut), dizin))
        surec = subprocess.Popen(komut, cwd=dizin, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 bufsize=1, universal_newlines=True)
        for satir in surec.stdout:
            satir = satir.rstrip("\n")
            log.write(satir + "\n")
            bilgi = cevrim_satiri(satir)
            if bilgi:
                cevrimler.append(bilgi)
            if geri_cagir:
                geri_cagir(satir, bilgi)
        surec.wait()

    sure = time.time() - t0
    sp = son_statepoint(dizin)
    return {
        "basarili": surec.returncode == 0 and sp is not None,
        "cikis_kodu": surec.returncode,
        "statepoint": sp,
        "sure": sure,
        "log": log_yolu,
        "cevrimler": cevrimler,
        "cikti": _ayristir.cikti_ozeti(dizin),
    }


def son_statepoint(dizin):
    """Dizindeki en yuksek cevrim numarali statepoint dosyasini dondurur."""
    adaylar = []
    for ad in os.listdir(dizin) if os.path.isdir(dizin) else []:
        m = re.match(r"statepoint\.(\d+)\.h5$", ad)
        if m:
            adaylar.append((int(m.group(1)), os.path.join(dizin, ad)))
    return max(adaylar)[1] if adaylar else None


# ============================================================================
# SONUC OKUMA
# ============================================================================

_SKOR_ADLARI = {
    "flux": "akı", "absorption": "soğurma", "fission": "fisyon", "nu-fission": "fisyon nötronu üretimi",
    "total": "toplam tepkime", "scatter": "saçılma", "heating": "ısınma",
    "heating-local": "yerel ısınma", "kappa-fission": "fisyon enerjisi", "(n,gamma)": "(n,γ) yakalama",
    "elastic": "esnek saçılma", "current": "akım",
}


def _enerji_metni(ev):
    if ev >= 1e6:
        return "%.4g MeV" % (ev / 1e6)
    if ev >= 1e3:
        return "%.4g keV" % (ev / 1e3)
    return "%.4g eV" % ev


def _birim(skor, sabit, kuvvet):
    """Tally degerinin birimi. OpenMC sabit kaynakta siddeti zaten uygular."""
    mutlak = sabit and kuvvet not in (None, 1.0)
    if skor in ("flux",):
        return "n·cm/s (hacim-integralli)" if mutlak else "n·cm / kaynak nötronu"
    if skor in ("heating", "heating-local", "kappa-fission"):
        return "eV/s" if mutlak else "eV / kaynak nötronu"
    return "1/s" if mutlak else "/ kaynak nötronu"


def tally_metni(ad, df, malzeme_adlari=None, sabit=False, kuvvet=1.0):
    """
    Tally DataFrame'ini okunur metin tablosuna cevirir: malzeme kimligi
    yerine adi, enerji araligi okunur birimle, skor Turkce, birim ve bagil
    hata sutunu. Eskiden ham pandas dokumu basiliyordu: "material 1",
    "..." ile gizlenen sutunlar, birim yok (Ajan 9 bulgusu, zirh ornegi).
    """
    try:
        import pandas as pd
    except Exception:                                  # pragma: no cover
        return "tally: %s\n%s" % (ad, df)
    if not isinstance(df, pd.DataFrame):
        return "tally: %s\n%s" % (ad, df)
    adlar = malzeme_adlari or {}
    satirlar = []
    for _, r in df.iterrows():
        etiket = []
        if "material" in df.columns:
            etiket.append(str(adlar.get(int(r["material"]), "malzeme %s" % r["material"])))
        if "energy low [eV]" in df.columns:
            etiket.append("%s – %s" % (_enerji_metni(r["energy low [eV]"]),
                                       _enerji_metni(r["energy high [eV]"])))
        if "nuclide" in df.columns and r["nuclide"] != "total":
            etiket.append(str(r["nuclide"]))
        skor = str(r.get("score", ""))
        ort, sap = float(r["mean"]), float(r["std. dev."])
        bagil = (100.0 * sap / abs(ort)) if ort else 0.0
        satirlar.append((" · ".join(etiket) or "tüm model", _SKOR_ADLARI.get(skor, skor),
                         "%.4e" % ort, "± %.1f%%" % bagil, _birim(skor, sabit, kuvvet)))
    ek_sutun = [c for c in df.columns if c not in (
        "material", "energy low [eV]", "energy high [eV]", "nuclide", "score", "mean", "std. dev.")]
    if ek_sutun or not satirlar:
        # tanimadigimiz filtre (mesh vb.): tam tabloyu kirpmadan bas
        with pd.option_context("display.max_columns", None, "display.width", 200,
                               "display.max_rows", 60):
            return "tally: %s\n%s" % (ad, df.to_string())
    genislik = [max(len(s[i]) for s in satirlar) for i in range(5)]
    baslik = ("Bölge / enerji", "Ölçülen", "Değer", "Bağıl hata", "Birim")
    genislik = [max(g, len(b)) for g, b in zip(genislik, baslik)]
    def bicimle(sat):
        return "  ".join(str(x).ljust(g) for x, g in zip(sat, genislik)).rstrip()
    cikti = ["tally: %s" % ad, bicimle(baslik), bicimle(["─" * g for g in genislik])]
    cikti += [bicimle(sat) for sat in satirlar]
    return "\n".join(cikti)


_GUC_TALLYLERI = ("guc_dagilimi", "guc_toplam_ref", "guc_model_toplam")


def _entropi_oku(sp):
    """(entropi listesi, hata metni). Entropi kapaliysa ([], None); okuma
    hatasinda ([], metin) -- hata loglanir ve "kapali" ile karistirilmaz."""
    try:
        return ([float(x) for x in sp.entropy] if sp.entropy is not None else []), None
    except Exception as e:
        _log.warning("statepoint entropisi okunamadı", exc_info=True)
        return [], str(e)


def _malzeme_adlari(sp):
    """{malzeme kimligi: ad} -- tally tablolarinda kimlik yerine ad gosterilsin
    (Ajan 9: "material 1 / 2" hangisinin su oldugunu soylemiyordu)."""
    try:
        return {m.id: m.name for m in sp.summary.materials}
    except Exception:
        _log.warning("summary.h5 malzeme adları okunamadı; tallylerde kimlik "
                     "gösterilecek", exc_info=True)
        return {}


def _tallyleri_oku(sp, sonuc):
    """Kullanici tally'leri sonuc['tallyler']'e; IFP paylari ayrica dondurulur."""
    import math as _m
    ifp = {}
    for _tid, t in sp.tallies.items():
        ad = t.name or "tally_%d" % t.id
        if ad in _GUC_TALLYLERI:
            continue          # guc bolumunde ayrica islenir
        try:
            df = t.get_pandas_dataframe()
        except Exception as e:
            _log.warning("'%s' tally'si okunamadı", ad, exc_info=True)
            sonuc["tallyler"][ad] = "okunamadı: %s" % e
            continue
        if ad.startswith("IFP "):
            ifp[ad] = (float(df["mean"].sum()),
                       _m.sqrt(float((df["std. dev."] ** 2).sum())))
        else:
            sonuc["tallyler"][ad] = df
    return ifp


def _kinetik(ifp):
    """
    Kinetik parametreler (IFP yontemi); eksikse None.
    beta_eff = <beta payi> / <payda>,  Lambda = <zaman payi> / <payda>
    Belirsizlik oransal olarak birlestirilir (paylar ve payda bagimsiz kabul).
    """
    import math as _m
    gerekli = ("IFP beta numerator", "IFP time numerator", "IFP denominator")
    if not all(g in ifp for g in gerekli):
        return None
    pb, spb = ifp["IFP beta numerator"]
    pt, spt = ifp["IFP time numerator"]
    pd, spd = ifp["IFP denominator"]
    if not (pd > 0 and pb > 0 and pt > 0):
        return None
    beta, lam = pb / pd, pt / pd
    return {
        "beta_eff": beta,
        "beta_eff_sapma": beta * _m.sqrt((spb / pb) ** 2 + (spd / pd) ** 2),
        "lambda": lam,
        "lambda_sapma": lam * _m.sqrt((spt / pt) ** 2 + (spd / pd) ** 2),
    }


def _tally_toplami(sp, ad):
    """Tally ortalamalarinin toplami; tally yoksa None (LookupError, DEBUG log).
    Diger istisnalar (bozuk dosya vb.) yukari cikar."""
    try:
        tal = sp.get_tally(name=ad)
    except LookupError:
        _log.debug("'%s' tally'si statepoint'te yok", ad)
        return None
    return float(tal.get_pandas_dataframe()["mean"].sum())


def _guc_korunumu(sp, dagilim):
    """
    TOPLAM KORUNUMU: cubuk guclerinin toplami, ayni hucreye bagli bolunmemis
    tally'ye (guc_toplam_ref) esit olmalidir. Esit degilse haritalama
    bozuktur; bu, yanlis bir haritanin sessizce dogru gorunmesini onleyen en
    guclu kontroldur. DONER guc sozlugune eklenecek alanlar.
    """
    try:
        ref_toplam = _tally_toplami(sp, "guc_toplam_ref")
    except Exception as e:
        _log.exception("güç toplamı korunum denetimi yapılamadı")
        return {"korunum_hata": str(e)}
    if ref_toplam is None:
        # Referans tally'si guc tally'siyle birlikte kurulur; yoksa ya eski
        # bir statepoint ya da kurucuda regresyon vardir. Iz birakilir.
        return {"korunum_notu": _(
            "Referans tally yok — korunum denetlenemedi (eski statepoint ya da "
            "model regresyonu).")}
    if ref_toplam <= 0:
        return {"korunum_notu": _(
            "Referans güç toplamı sıfır ya da negatif (%.3g): hedef bölgede fisyon "
            "sayılmadı, toplamın korunumu denetlenemedi.") % ref_toplam}
    dag_toplam = sum(k["toplam"][0] for k in dagilim["konumlar"].values())
    bagil = abs(dag_toplam / ref_toplam - 1.0)
    alanlar = {"korunum": bagil}
    if bagil > 1e-6:
        alanlar["korunum_uyari"] = (
            "Çubuk güçlerinin toplamı filtresiz tally'den %.2e bağıl "
            "fark gösteriyor. Haritalama bozuk olabilir — sonuçlara "
            "güvenmeyin." % bagil)
    return alanlar


def _hedef_payi(sp):
    """
    Hedef cubuk bolgesinin model geneli fisyon enerjisindeki payi:
    kappa_hedef (guc_toplam_ref) / kappa_model (guc_model_toplam). Mutlak guc
    bu payla dagitilir (guc.mutlak_guc).
    DONER {"hedef_payi": pay | None}; okuma HATASINDA ek "hedef_payi_hata"
    (eski statepoint'te tally yoksa -- LookupError -- yalniz None).
    """
    try:
        hedef = _tally_toplami(sp, "guc_toplam_ref")
        model = _tally_toplami(sp, "guc_model_toplam")
    except Exception as e:
        _log.exception("güç payı (hedef / model) okunamadı")
        return {"hedef_payi": None, "hedef_payi_hata": str(e)}
    if hedef is None or model is None or model <= 0:
        return {"hedef_payi": None}
    return {"hedef_payi": hedef / model}


def _guc_oku(sp, sonuc):
    """Cubuk bazli guc dagilimi: sonuc['guc'] ya da sonuc['guc_hata']."""
    from cekirdek import guc as _guc
    try:
        dagilim = _guc.dagilim_oku(sp)
    except Exception as e:
        _log.exception("güç dağılımı okunamadı")
        sonuc["guc_hata"] = str(e)
        return
    if not dagilim:
        return
    try:
        faktorler = _guc.tepe_faktorleri(dagilim)
    except Exception as e:
        _log.exception("güç tepe faktörleri hesaplanamadı")
        sonuc["guc_hata"] = str(e)
        return
    g = {"dagilim": dagilim, "faktorler": faktorler}
    g.update(_guc_korunumu(sp, dagilim))
    g.update(_hedef_payi(sp))
    sonuc["guc"] = g


def korunum_satirlari(g):
    """Guc sozlugunun korunum durumu, kullaniciya gosterilecek satirlar
    (terminal ve Calistir sekmesi ayni metni kullanir)."""
    satirlar = []
    if "korunum" in g:
        satirlar.append(_("toplamın korunumu: bağıl fark %.1e — %s") % (
            g["korunum"], _("tamam") if g["korunum"] < 1e-6
            else _("bozuk, haritaya güvenmeyin")))
    if g.get("korunum_hata"):
        satirlar.append(_("toplamın korunumu denetlenemedi: %s") % g["korunum_hata"])
    if g.get("korunum_notu"):
        satirlar.append(g["korunum_notu"])
    return satirlar


def sonuc_oku(statepoint_yolu):
    """
    Statepoint'ten k-eff ve tally sonuclarini okur.
    DONER {"keff":(deger,sapma), "cevrim":int, "pasif":int, "tallyler":{ad: DataFrame}}
      guc (varsa): {"dagilim", "faktorler", "korunum" | "korunum_hata" |
                    "korunum_notu", "korunum_uyari", "hedef_payi",
                    "hedef_payi_hata" (yalniz okuma hatasinda)}
      entropi_hata (yalniz okuma hatasinda): entropi [] ama "kapali" DEGIL
    """
    import openmc
    sp = openmc.StatePoint(statepoint_yolu)
    # Sabit kaynak modunda k-eff YOKTUR: sp.keff istisna atmaz, None doner.
    # Once bunu kontrol etmeyen kod "'NoneType' object has no attribute
    # 'nominal_value'" ile cokuyordu -- kosu basariyla bitmis olmasina ragmen.
    ozdeger = getattr(sp, "keff", None) is not None
    entropi, entropi_hata = _entropi_oku(sp)
    sonuc = {
        "mod": "eigenvalue" if ozdeger else "fixed source",
        "keff": (sp.keff.nominal_value, sp.keff.std_dev) if ozdeger else None,
        "cevrim": sp.n_batches,
        "pasif": sp.n_inactive if ozdeger else 0,
        "parcacik": sp.n_particles,
        "entropi": entropi,
        "tallyler": {},
        "malzeme_adlari": _malzeme_adlari(sp),
    }
    if entropi_hata is not None:
        sonuc["entropi_hata"] = entropi_hata
    kinetik = _kinetik(_tallyleri_oku(sp, sonuc))
    if kinetik:
        sonuc["kinetik"] = kinetik
    _guc_oku(sp, sonuc)
    return sonuc


# ============================================================================
# TERMINAL GIRISI
# ============================================================================

def _terminal(argv):
    if not argv or argv[0] in ("-h", "--yardim", "--help"):
        print(__doc__)
        return 0

    spec_yolu = argv[0]
    dizin = None
    is_parcacigi = None
    sadece_dogrula = False
    betik_yolu = None

    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--dizin":
            i += 1; dizin = argv[i]
        elif a in ("-s", "--is-parcacigi"):
            i += 1; is_parcacigi = int(argv[i])
        elif a == "--sadece-dogrula":
            sadece_dogrula = True
        elif a == "--betik":
            i += 1; betik_yolu = argv[i]
        else:
            print("bilinmeyen seçenek: %s" % a); return 2
        i += 1

    spec = sema.yukle(spec_yolu)
    print("=" * 74)
    print(" %s" % spec.get("ad", spec_yolu))
    print("=" * 74)

    # --- 1. dogrulama (tek kapi: dogrula.kapi) ---
    try:
        bulgular = dogrula.kapi(spec)
    except dogrula.DogrulamaHatasi as e:
        bulgular = e.tum_bulgular
        print("\n[1/3] Doğrulama: %s" % dogrula.ozet(bulgular))
        for b in bulgular:
            print("  %s" % b)
        print("\nHatalar giderilmeden koşu başlatılmaz (%s)." % e)
        return 1
    print("\n[1/3] Doğrulama: %s" % dogrula.ozet(bulgular))
    for b in bulgular:
        print("  %s" % b)

    # --- istege bagli betik uretimi ---
    if betik_yolu:
        from cekirdek import kod_uret
        kod = kod_uret.uret(spec, os.path.basename(betik_yolu))
        with open(betik_yolu, "w", encoding="utf-8") as f:
            f.write(kod)
        print("\n      betik yazıldı: %s (%d satır)" % (betik_yolu, len(kod.splitlines())))

    if sadece_dogrula:
        print("\n(--sadece-dogrula verildi; koşu atlandı)")
        return 0

    # --- 2. kosu ---
    if dizin is None:
        dizin = os.path.join(os.path.dirname(os.path.abspath(spec_yolu)),
                             spec["calistirma"].get("dizin", "kosu"))
    print("\n[2/3] Koşu başlatılıyor → %s" % dizin)

    son_yazilan = [0]
    tty = sys.stdout.isatty()

    def ilerleme(satir, bilgi):
        # Terminalde tek satir guncellenir; cikti bir dosyaya/boruya yonlendirilmisse
        # \r ise yaramaz, her guncelleme ayri satira yazilir.
        if bilgi and bilgi["ortalama"] is not None:
            if bilgi["cevrim"] - son_yazilan[0] >= 10:
                son_yazilan[0] = bilgi["cevrim"]
                metin = ("      çevrim %4d   k = %.5f ± %.5f"
                         % (bilgi["cevrim"], bilgi["ortalama"], bilgi["sapma"]))
                sys.stdout.write(("\r" + metin) if tty else (metin + "\n"))
                sys.stdout.flush()

    # spec yukarida dogrulandi: cift dogrulama yok
    sonuc = calistir(spec, dizin, geri_cagir=ilerleme, is_parcacigi=is_parcacigi,
                     dogrulama=False)
    if tty:
        sys.stdout.write("\r" + " " * 60 + "\r")

    if not sonuc["basarili"]:
        print("      Koşu başarısız (çıkış kodu %d)" % sonuc["cikis_kodu"])
        print("      log: %s" % sonuc["log"])
        return 1
    print("      tamamlandı: %.1f s" % sonuc["sure"])
    for satir in _ayristir.ozet_satirlari(sonuc.get("cikti")):   # M5: sessiz kalmasin
        print("      %s" % satir)

    # --- 3. sonuc ---
    print("\n[3/3] Sonuçlar")
    s = sonuc_oku(sonuc["statepoint"])
    if s.get("keff") is None:
        # --- sabit kaynak: k-eff yok, sonuc tally'lerdir ---
        k_tanim = (spec["ayarlar"].get("kaynak") or {})
        kuvvet = float(k_tanim.get("kuvvet") or 1.0)
        print("      hesap    = sabit kaynak (k-eff tanımsız)")
        print("      kaynak   = %s" % _kaynak.ozet(k_tanim))
        print("      şiddet   = %.4g parçacık/s" % kuvvet)
        print("      çevrim   = %d, %d parçacık/çevrim" % (s["cevrim"], s["parcacik"]))
        # OLCULDU: OpenMC sabit kaynak tally'lerini kaynak siddetiyle ZATEN
        # carpiyor (kuvvet=1 ve kuvvet=1e12 ile kosuldu, oran tam 1e12 cikti).
        # Bu yuzden kullaniciya "siddetle carpin" demek CIFT SAYIM olurdu.
        if kuvvet == 1.0:
            print("      Not: tally değerleri kaynak parçacığı başınadır")
            print("           (şiddet 1 bırakıldı). Mutlak birim için şiddeti girin.")
        else:
            print("      Not: tally değerleri mutlak birimdedir — OpenMC kaynak")
            print("           şiddetini zaten uygulamıştır, tekrar çarpmayın.")
            print("           reaksiyon hızları: 1/s")
            print("           Dikkat: 'flux' skoru hacim üzerinden integrallidir (birim cm/s).")
            print("           Nokta akısı [1/cm²/s] için bölgenin hacmine bölün.")
    else:
        print("      k-eff    = %.5f ± %.5f" % s["keff"])
        _kin = s.get("kinetik") or {}
        from cekirdek import uygunluk as _u
        _durum, _ayrinti = keff_yorumu(s["keff"][0], s["keff"][1], _kin.get("beta_eff"),
                                       sonsuz=_u.sonsuz_ortam(spec))
        print("      durum    = %s" % _durum)
        print("                 %s" % _ayrinti)
        print("      çevrim   = %d (%d pasif), %d parçacık/çevrim"
              % (s["cevrim"], s["pasif"], s["parcacik"]))
    # Entropi yalnizca ozdeger modunda anlamlidir: sabit kaynakta kaynak
    # zaten sabittir, "yakinsamasi" diye bir sey yoktur.
    if s.get("keff") is not None:
        if s.get("entropi"):
            yakinsadi, mesaj = entropi_yakinsama(s["entropi"], s["pasif"])
            isaret = {True: "tamam", False: "uyarı", None: "  ?  "}[yakinsadi]
            print("      yakınsama= [%s] %s" % (isaret, mesaj))
        elif s.get("entropi_hata"):
            print("      yakınsama= [  ?  ] %s"
                  % (_("Shannon entropisi okunamadı: %s") % s["entropi_hata"]))
        else:
            print("      yakınsama= [  ?  ] Shannon entropisi kapalı — kaynak "
                  "yakınsaması doğrulanamıyor")
    kin = s.get("kinetik")
    if kin:
        print("      β_eff    = %.1f ± %.1f pcm" % (kin["beta_eff"] * 1e5,
                                                      kin["beta_eff_sapma"] * 1e5))
        print("      Λ        = %s" % lambda_metni(kin["lambda"], kin["lambda_sapma"]))
    g = s.get("guc")
    if g and g.get("faktorler"):
        from cekirdek import guc as _guc
        f = g["faktorler"]
        spec_g = spec.get("guc_dagilimi") or {}
        # Lineer guc [W/cm] HEDEF CUBUGUN bulundugu katmanlarin toplam
        # yuksekligine bolunur (kurucu.guc_yuksekligi): yansitici, plenum ve
        # blanket katmanlari paya girmez, paydaya da girmemeli.
        m = _guc.mutlak_guc(f, spec_g.get("toplam_guc"), kurucu.guc_yuksekligi(spec),
                            hedef_payi=g.get("hedef_payi"))
        print("\n      --- güç dağılımı (%d çubuk, %d eksenel dilim) ---"
              % (f["cubuk_sayisi"], f["eksenel_dilim"]))
        for satir in korunum_satirlari(g):
            print("      %s" % satir)
        for satir in _guc.yorumla(f, m, hedef_payi=g.get("hedef_payi"),
                                  hedef_payi_hata=g.get("hedef_payi_hata")):
            print("      %s" % satir)
    elif s.get("guc_hata"):
        print("\n      güç dağılımı okunamadı: %s" % s["guc_hata"])

    _kuvvet = float(((spec.get("ayarlar") or {}).get("kaynak") or {}).get("kuvvet") or 1.0)
    for ad, df in s["tallyler"].items():
        print("")
        print("      " + tally_metni(ad, df, s.get("malzeme_adlari"), s.get("keff") is None,
                                     _kuvvet).replace("\n", "\n      "))
    print("\n      statepoint: %s" % sonuc["statepoint"])
    print("      log       : %s" % sonuc["log"])
    return 0


if __name__ == "__main__":
    sys.exit(_terminal(sys.argv[1:]))
