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

# OpenMC cevrim satiri:  "       54/1    1.32041    1.36400 +/- 0.00368"
# pasif cevrimlerde ortalama sutunlari yoktur.
_CEVRIM_DESEN = re.compile(
    r"^\s*(\d+)/(\d+)\s+([0-9.]+)(?:\s+([0-9.]+)\s+\+/-\s+([0-9.]+))?\s*$")


def cevrim_satiri(satir):
    """
    Cevrim satirini ayristirir.
    DONER {"cevrim":int,"nesil":int,"k":float,"ortalama":float|None,"sapma":float|None}
    ya da satir cevrim satiri degilse None.
    """
    m = _CEVRIM_DESEN.match(satir)
    if not m:
        return None
    return {
        "cevrim": int(m.group(1)),
        "nesil": int(m.group(2)),
        "k": float(m.group(3)),
        "ortalama": float(m.group(4)) if m.group(4) else None,
        "sapma": float(m.group(5)) if m.group(5) else None,
    }


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
            if (ad.startswith("statepoint") or ad in ("summary.h5", "tallies.out",
                                                      "model.xml", "kosu.log")):
                try:
                    os.remove(os.path.join(dizin, ad))
                except OSError:
                    pass
    os.makedirs(dizin, exist_ok=True)
    return dizin


def xml_yaz(spec, dizin):
    """Modeli kurar ve model.xml'i kosu dizinine yazar. DONER (model, bilgi, yol)"""
    model, bilgi = kurucu.kur(spec)
    yol = os.path.join(dizin, "model.xml")
    model.export_to_model_xml(yol)
    return model, bilgi, yol


# ============================================================================
# CALISTIRMA
# ============================================================================

def calistir(spec, dizin, geri_cagir=None, is_parcacigi=None, temizle=True):
    """
    Modeli kurar, XML yazar ve openmc'yi alt surec olarak calistirir.

    geri_cagir : her cikti satiri icin cagrilan fonksiyon -- f(satir, cevrim_bilgisi)
                 cevrim_bilgisi cevrim satiri degilse None'dir.
    DONER sozluk:
       {"basarili":bool, "cikis_kodu":int, "statepoint":yol|None,
        "sure":float, "log":yol, "cevrimler":[...]}
    """
    dizin = dizin_hazirla(dizin, temizle=temizle)
    xml_yaz(spec, dizin)

    n = is_parcacigi or spec["calistirma"].get("is_parcacigi", 8)
    exe = openmc_yolu()
    if exe is None:
        raise RuntimeError("openmc calistirilabilir dosyasi PATH'te bulunamadi "
                           "(conda ortami aktif mi?)")

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

def sonuc_oku(statepoint_yolu):
    """
    Statepoint'ten k-eff ve tally sonuclarini okur.
    DONER {"keff":(deger,sapma), "cevrim":int, "pasif":int, "tallyler":{ad: DataFrame}}
    """
    import openmc
    sp = openmc.StatePoint(statepoint_yolu)
    sonuc = {
        "keff": (sp.keff.nominal_value, sp.keff.std_dev),
        "cevrim": sp.n_batches,
        "pasif": sp.n_inactive,
        "parcacik": sp.n_particles,
        "tallyler": {},
    }
    for _, t in sp.tallies.items():
        try:
            sonuc["tallyler"][t.name or "tally_%d" % t.id] = t.get_pandas_dataframe()
        except Exception as e:
            sonuc["tallyler"][t.name or "tally_%d" % t.id] = "okunamadi: %s" % e
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
            print("bilinmeyen secenek: %s" % a); return 2
        i += 1

    spec = sema.yukle(spec_yolu)
    print("=" * 74)
    print(" %s" % spec.get("ad", spec_yolu))
    print("=" * 74)

    # --- 1. dogrulama ---
    bulgular = dogrula.tum_kontroller(spec)
    print("\n[1/3] Dogrulama: %s" % dogrula.ozet(bulgular))
    for b in bulgular:
        print("  %s" % b)
    if dogrula.hata_var(bulgular):
        print("\n!!! Hatalar giderilmeden kosu baslatilmaz !!!")
        return 1

    # --- istege bagli betik uretimi ---
    if betik_yolu:
        from cekirdek import kod_uret
        kod = kod_uret.uret(spec, os.path.basename(betik_yolu))
        with open(betik_yolu, "w", encoding="utf-8") as f:
            f.write(kod)
        print("\n      betik yazildi: %s (%d satir)" % (betik_yolu, len(kod.splitlines())))

    if sadece_dogrula:
        print("\n(--sadece-dogrula verildi, kosu atlandi)")
        return 0

    # --- 2. kosu ---
    if dizin is None:
        dizin = os.path.join(os.path.dirname(os.path.abspath(spec_yolu)),
                             spec["calistirma"].get("dizin", "kosu"))
    print("\n[2/3] Kosu baslatiliyor -> %s" % dizin)

    son_yazilan = [0]
    tty = sys.stdout.isatty()

    def ilerleme(satir, bilgi):
        # Terminalde tek satir guncellenir; cikti bir dosyaya/boruya yonlendirilmisse
        # \r ise yaramaz, her guncelleme ayri satira yazilir.
        if bilgi and bilgi["ortalama"] is not None:
            if bilgi["cevrim"] - son_yazilan[0] >= 10:
                son_yazilan[0] = bilgi["cevrim"]
                metin = ("      cevrim %4d   k = %.5f +/- %.5f"
                         % (bilgi["cevrim"], bilgi["ortalama"], bilgi["sapma"]))
                sys.stdout.write(("\r" + metin) if tty else (metin + "\n"))
                sys.stdout.flush()

    sonuc = calistir(spec, dizin, geri_cagir=ilerleme, is_parcacigi=is_parcacigi)
    if tty:
        sys.stdout.write("\r" + " " * 60 + "\r")

    if not sonuc["basarili"]:
        print("      KOSU BASARISIZ (cikis kodu %d)" % sonuc["cikis_kodu"])
        print("      log: %s" % sonuc["log"])
        return 1
    print("      tamamlandi: %.1f s" % sonuc["sure"])

    # --- 3. sonuc ---
    print("\n[3/3] Sonuclar")
    s = sonuc_oku(sonuc["statepoint"])
    print("      k-eff    = %.5f +/- %.5f" % s["keff"])
    print("      cevrim   = %d (%d pasif), %d parcacik/cevrim"
          % (s["cevrim"], s["pasif"], s["parcacik"]))
    for ad, df in s["tallyler"].items():
        print("\n      --- tally: %s ---" % ad)
        print("      " + str(df).replace("\n", "\n      "))
    print("\n      statepoint: %s" % sonuc["statepoint"])
    print("      log       : %s" % sonuc["log"])
    return 0


if __name__ == "__main__":
    sys.exit(_terminal(sys.argv[1:]))
