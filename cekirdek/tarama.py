# -*- coding: utf-8 -*-
"""
================================================================================
 tarama.py  --  Parametre taramasi ve reaktivite katsayilari
================================================================================

 Bir spec alanini bir aralikta degistirip her deger icin kosar, k-eff(p)
 egrisini ve ondan reaktivite katsayisini uretir. Tek bir mekanizma su
 buyukluklerin HEPSINI verir:

   Doppler katsayisi          yakit sicakligi taramasi        [pcm/K]
   Moderator sicaklik kats.   sogutucu sicakligi taramasi     [pcm/K]
   Void katsayisi             sogutucu void orani taramasi    [pcm/%void]
   Bor degeri (worth)         cozunmus bor taramasi           [pcm/ppm]
   Zenginlik duyarliligi      zenginlik taramasi              [pcm/%]
   Moderasyon orani etudu     kafes adimi taramasi            [pcm/cm]

 !!! FIZIK UYARISI -- SICAKLIK VE YOGUNLUK BIRLIKTE DEGISIR !!!
   Sogutucu sicakligi arttiginda yogunlugu de DUSER. Yalnizca sicakligi
   degistirirseniz Doppler + spektral etkiyi olcersiniz ama etkinin en buyuk
   parcasini (yogunluk kaybini) kacirirsiniz; moderator sicaklik katsayisi
   buyuklugu birkac kat yanlis cikar.
   Bu yuzden "sogutucu_sicaklik" turu yogunlugu da korelasyonla gunceller:
     su   : doymus sivi su tablosu (malzeme_kutup.su_yogunluk)
     LBE  : rho = 11096 - 1.3236*T  [kg/m3]  (Sobolev / OECD-NEA 2007)
     Na   : rho = 1014  - 0.235*T   [kg/m3]  (Fink & Leibowitz yaklasimi)
   Korelasyonu bilinmeyen malzemede yogunluk SABIT tutulur ve bu acikca
   raporlanir -- sessizce yanlis sonuc uretmez.

 TOHUM (SEED) SECIMI
   Tum noktalar AYNI rastgele tohumla kosulur. Boylece istatistik
   dalgalanmalar farkta kismen birbirini goturur (korelasyonlu orneklem) ve
   katsayi daha az gurultulu cikar. Raporlanan belirsizlik noktalari bagimsiz
   kabul eder; yani MUHAFAZAKARDIR (gercek hata daha kucuktur).

 KULLANIM (terminal)
   python3 -m cekirdek.tarama ornekler/pwr_17x17.json \\
       --tur sogutucu_sicaklik --hedef su --bas 500 --son 600 --adet 5
================================================================================
"""

import copy
import math
import os
import sys

from cekirdek import kosucu, sema
from cekirdek import malzeme_kutup as mk

# ----------------------------------------------------------------------------
# Tarama turleri: (aciklama, hedef_turu, birim, katsayi_birimi)
# ----------------------------------------------------------------------------
TURLER = {
    "yakit_sicaklik": (
        "Yakıt sıcaklığı (Doppler) — yoğunluk sabit tutulur (katı yakıt)",
        "malzeme", "K", "pcm/K"),
    "sogutucu_sicaklik": (
        "Soğutucu sıcaklığı — yoğunluk korelasyonla birlikte değişir",
        "malzeme", "K", "pcm/K"),
    "malzeme_yogunluk": (
        "Malzeme yoğunluğu",
        "malzeme", "g/cm3", "pcm/(g/cm3)"),
    "void_orani": (
        "Soğutucu boşluk (void) oranı — yoğunluk ρ0·(1−α) olur",
        "malzeme", "%", "pcm/%void"),
    "bor_ppm": (
        "Suda çözünmüş doğal bor",
        "malzeme", "ppm", "pcm/ppm"),
    "zenginlik": (
        "Uranyum zenginliği (ağırlıkça %)",
        "malzeme", "%", "pcm/%"),
    "kafes_adim": (
        "Demet adımı (moderasyon oranı etüdü)",
        "demet", "cm", "pcm/cm"),
    "kor_adim": (
        "Kor hücre adımı",
        "kor", "cm", "pcm/cm"),
    "cubuk_daldirma": (
        "Kontrol çubuğu daldırma oranı (%0 çekilmiş, %100 tam dalmış)",
        "kontrol_cubugu", "%", "pcm/%"),
    "cubuk_yaricap": (
        "Çubuğun bir bölgesinin yarıçapı",
        "cubuk_bolge", "cm", "pcm/cm"),
    "tambur_donme": (
        "Kontrol tamburu dönmesi (0° = emici kora bakıyor, 180° = dışa)",
        "kor", "derece", "pcm/derece"),
    "yansitici_kalinlik": (
        "Yansıtıcı kuşak kalınlığı",
        "kor", "cm", "pcm/cm"),
}


# ============================================================================
# 1. YOGUNLUK KORELASYONLARI
# ============================================================================

def _yogunluk_korelasyonu(malzeme):
    """
    Malzemenin bilesimine bakarak sicakliga bagli yogunluk fonksiyonunu secer.
    DONER (fonksiyon, ad) ya da (None, sebep)
    """
    elemanlar = set()
    for b in malzeme.get("bilesim", []):
        isim = b.get("isim", "")
        elemanlar.add("".join(ch for ch in isim if ch.isalpha()))

    if elemanlar <= {"H", "O", "B"} and "H" in elemanlar:
        return mk.su_yogunluk, "doymuş sıvı su tablosu (273–623 K)"
    if elemanlar <= {"Pb", "Bi"} and elemanlar:
        return (lambda T: (11096.0 - 1.3236 * T) / 1000.0,
                "LBE: ρ = 11096 − 1.3236·T kg/m³ (Sobolev, 400–1300 K)")
    if elemanlar == {"Na"}:
        return (lambda T: (1014.0 - 0.235 * T) / 1000.0,
                "Na: ρ = 1014 − 0.235·T kg/m³ (371–1200 K)")
    return None, ("'%s' için sıcaklığa bağlı yoğunluk korelasyonu yok — "
                  "yoğunluk sabit tutuldu; moderatör sıcaklık katsayısı "
                  "eksik çıkar" % malzeme["ad"])


# ============================================================================
# 2. PARAMETRE UYGULAMA
# ============================================================================

def parametre_uygula(spec, tur, hedef, deger, taban=None):
    """
    Spec'in bir kopyasini alip parametreyi uygular.

    hedef : tura gore malzeme adi / demet adi / (cubuk_adi, bolge_no) / None
    taban : referans spec (void ve void_orani icin baslangic yogunlugu buradan
            okunur; verilmezse spec'in kendisi kullanilir)
    DONER (yeni_spec, not_metni|None)
    """
    yeni = copy.deepcopy(spec)
    taban = taban or spec
    not_metni = None

    if tur == "yakit_sicaklik":
        m = sema.malzeme_bul(yeni, hedef)
        if m is None:
            raise KeyError("tanımsız malzeme: %s" % hedef)
        m["sicaklik"] = float(deger)

    elif tur == "sogutucu_sicaklik":
        m = sema.malzeme_bul(yeni, hedef)
        if m is None:
            raise KeyError("tanımsız malzeme: %s" % hedef)
        m["sicaklik"] = float(deger)
        fonk, aciklama = _yogunluk_korelasyonu(m)
        if fonk is not None:
            m["yogunluk"]["birim"] = "g/cm3"
            m["yogunluk"]["deger"] = float(fonk(float(deger)))
        else:
            not_metni = aciklama

    elif tur == "malzeme_yogunluk":
        m = sema.malzeme_bul(yeni, hedef)
        m["yogunluk"]["deger"] = float(deger)

    elif tur == "void_orani":
        m = sema.malzeme_bul(yeni, hedef)
        m0 = sema.malzeme_bul(taban, hedef)
        rho0 = m0["yogunluk"]["deger"]
        alfa = float(deger) / 100.0
        if not (0.0 <= alfa <= 1.0):
            raise ValueError("boşluk (void) oranı %0–100 arasında olmalı")
        m["yogunluk"]["deger"] = rho0 * (1.0 - alfa)

    elif tur == "bor_ppm":
        m = sema.malzeme_bul(yeni, hedef)
        m0 = sema.malzeme_bul(taban, hedef)
        sicaklik = m.get("sicaklik") or 293.6
        rho = m0["yogunluk"]["deger"]
        yeni_su = mk.su(sicaklik=sicaklik, yogunluk=rho, bor_ppm=float(deger),
                        ad=m["ad"])
        m["bilesim"] = yeni_su["bilesim"]
        m["gorunen_ad"] = yeni_su["gorunen_ad"]

    elif tur == "zenginlik":
        m = sema.malzeme_bul(yeni, hedef)
        bulundu = False
        for b in m["bilesim"]:
            if b.get("zenginlik") is not None:
                b["zenginlik"] = float(deger)
                bulundu = True
        if not bulundu:
            raise ValueError("'%s' malzemesinde zenginlik tanımlı bir "
                             "bileşen yok" % hedef)

    elif tur == "kafes_adim":
        d = sema.demet_bul(yeni, hedef)
        if d is None:
            raise KeyError("tanımsız demet: %s" % hedef)
        d["adim"] = float(deger)

    elif tur == "kor_adim":
        yeni["kor"]["adim"] = float(deger)

    elif tur == "cubuk_daldirma":
        c = sema.cubuk_bul(yeni, hedef)
        if c is None:
            raise KeyError("tanımsız çubuk: %s" % hedef)
        if c.get("tur") != "kontrol":
            raise ValueError("'%s' bir kontrol çubuğu değil; daldırma taraması "
                             "yalnızca kontrol çubuklarına uygulanır" % hedef)
        if not (0.0 <= float(deger) <= 100.0):
            raise ValueError("daldırma %%0–%%100 arasında olmalı: %s" % deger)
        c["daldirma"] = float(deger)

    elif tur == "cubuk_yaricap":
        cubuk_ad, bolge_no = hedef
        c = sema.cubuk_bul(yeni, cubuk_ad)
        if c is None:
            raise KeyError("tanımsız çubuk: %s" % cubuk_ad)
        c["bolgeler"][int(bolge_no)]["r"] = float(deger)

    elif tur == "tambur_donme":
        t = yeni["kor"].get("tambur") or {}
        if int(t.get("sayi") or 0) <= 0:
            raise ValueError("modelde kontrol tamburu yok")
        t["donme"] = float(deger)

    elif tur == "yansitici_kalinlik":
        yeni["kor"].setdefault("yansitici", {})["kalinlik"] = float(deger)
        yeni["kor"]["yansitici"]["var"] = True

    else:
        raise ValueError("bilinmeyen tarama türü: %s" % tur)

    return yeni, not_metni


def noktalar(bas, son, adet):
    """Esit araliklarla adet kadar nokta uretir."""
    adet = int(adet)
    if adet < 2:
        return [float(bas)]
    return [float(bas) + (float(son) - float(bas)) * i / (adet - 1)
            for i in range(adet)]


# ============================================================================
# 3. REAKTIVITE VE KATSAYI
# ============================================================================

def reaktivite(k, sapma=0.0):
    """
    k-eff'ten reaktiviteyi pcm cinsinden hesaplar.
      rho = (k - 1) / k          [mutlak]
      pcm = 1e5 * rho
    Belirsizlik: drho/dk = 1/k^2  ->  sigma_rho = sigma_k / k^2
    """
    if k <= 0:
        return float("nan"), float("nan")
    rho = (k - 1.0) / k
    s = sapma / (k * k)
    return 1.0e5 * rho, 1.0e5 * s


def katsayi(sonuclar):
    """
    Reaktivite katsayisini agirlikli en kucuk kareler ile hesaplar.

    sonuclar : [{"deger": p, "keff": k, "sapma": s}, ...]
    DONER {"egim","egim_sapma","kesisim","r2","nokta","pcm"} ya da None
    """
    veri = [(s["deger"], *reaktivite(s["keff"], s["sapma"]))
            for s in sonuclar if s.get("keff")]
    veri = [(p, r, sr) for p, r, sr in veri if sr and sr > 0
            and not math.isnan(r)]
    if len(veri) < 2:
        return None

    # agirlik = 1/sigma^2
    W = sum(1.0 / sr ** 2 for _, _, sr in veri)
    Wx = sum(p / sr ** 2 for p, _, sr in veri)
    Wy = sum(r / sr ** 2 for _, r, sr in veri)
    Wxx = sum(p * p / sr ** 2 for p, _, sr in veri)
    Wxy = sum(p * r / sr ** 2 for p, r, sr in veri)
    payda = W * Wxx - Wx * Wx
    if abs(payda) < 1e-30:
        return None
    egim = (W * Wxy - Wx * Wy) / payda
    kesisim = (Wxx * Wy - Wx * Wxy) / payda
    egim_sapma = math.sqrt(W / payda)

    # belirleme katsayisi (agirliksiz, okunabilirlik icin)
    ort = sum(r for _, r, _ in veri) / len(veri)
    ss_top = sum((r - ort) ** 2 for _, r, _ in veri)
    ss_kal = sum((r - (kesisim + egim * p)) ** 2 for p, r, _ in veri)
    r2 = 1.0 - ss_kal / ss_top if ss_top > 0 else 1.0

    return {"egim": egim, "egim_sapma": egim_sapma, "kesisim": kesisim,
            "r2": r2, "nokta": len(veri),
            "pcm": [(p, r, sr) for p, r, sr in veri]}


def yorumla(tur, kats):
    """Katsayiyi fiziksel olarak yorumlar (ogrenciye yonelik kisa not)."""
    if kats is None:
        return "Katsayı hesaplanamadı (yeterli nokta yok)."
    e, s = kats["egim"], kats["egim_sapma"]
    anlamli = abs(e) > 2 * s
    isaret = "negatif" if e < 0 else "pozitif"
    if not anlamli:
        return ("Eğim istatistiksel olarak sıfırdan ayırt edilemiyor "
                "(%.2f ± %.2f). Daha fazla parçacık/çevrim ya da daha geniş "
                "aralık gerekir." % (e, s))
    notlar = {
        "yakit_sicaklik": ("Doppler katsayısı. Negatif olması beklenir: yakıt "
                           "ısındıkça U-238 rezonansları genişler, yakalama artar. "
                           "Pozitif çıkması ciddi bir güvenlik işaretidir."),
        "sogutucu_sicaklik": ("Moderatör sıcaklık katsayısı. Termal reaktörde "
                              "negatif olması istenir. Pozitifse soğutucu ısındıkça "
                              "güç artar — kararsızlık."),
        "void_orani": ("Boşluk (void) katsayısı. Termal reaktörde negatif olmalı. "
                       "Hızlı reaktörlerde merkezi bölgede pozitif olabilir."),
        "bor_ppm": ("Bor değeri (worth). Negatif olması beklenir: bor nötron emicidir."),
        "zenginlik": ("Zenginlik duyarlılığı. Pozitif olması beklenir."),
        "kafes_adim": ("Moderasyon oranı etkisi. İşareti, demetin az mı çok mu "
                       "moderatörlü olduğunu söyler: az moderatörlü tarafta "
                       "adım artışı k'yi artırır (pozitif)."),
        "tambur_donme": (
            "Tambur değeri. Dönme 0°'de emici kora bakar (en düşük k), 180°'de "
            "dışa bakar (en yüksek k); bu yüzden eğim pozitif olmalı. "
            "Diferansiyel değerin tepesi orta dönmede çıkar — klasik tambur "
            "S eğrisi."),
        "cubuk_daldirma": (
            "Kontrol çubuğu değeri. Negatif olmalı: emici daldıkça reaktivite "
            "düşer. Dikkat: klasik S eğrisi yalnızca sistem her konumda "
            "kritiğe yakın olduğunda görülür. k∞'u yüksek bir demette "
            "(ör. yansıtıcı sınırlı tek demet) çubuksuz bölge tek başına "
            "süperkritik kalır; bu yüzden değer geç toplanır ve diferansiyel "
            "değerin tepesi merkezde değil tam daldırmaya yakın çıkar."),
    }
    taban = notlar.get(tur, "")
    return "Eğim %s. %s" % (isaret, taban) if taban else "Eğim %s." % isaret


# ============================================================================
# 4. TARAMAYI CALISTIR
# ============================================================================

def calistir(spec, tur, hedef, degerler, kok_dizin, geri_cagir=None,
             is_parcacigi=None, dur_bayragi=None):
    """
    Her nokta icin modeli kurar ve kosar.

    geri_cagir(indeks, toplam, sonuc_sozlugu) her nokta bitince cagrilir.
    dur_bayragi : cagrilabilir; True dondururse tarama durur.
    DONER (sonuclar, notlar)
    """
    sonuclar = []
    notlar = []
    toplam = len(degerler)
    for i, deger in enumerate(degerler):
        if dur_bayragi and dur_bayragi():
            notlar.append("Tarama kullanıcı tarafından durduruldu (%d/%d)."
                          % (i, toplam))
            break
        nokta_spec, uyari = parametre_uygula(spec, tur, hedef, deger, taban=spec)
        if uyari and uyari not in notlar:
            notlar.append(uyari)
        dizin = os.path.join(kok_dizin, "nokta_%02d" % i)
        sonuc = {"deger": deger, "keff": None, "sapma": None, "dizin": dizin}
        try:
            kosu = kosucu.calistir(nokta_spec, dizin, is_parcacigi=is_parcacigi)
            if kosu["basarili"]:
                okunan = kosucu.sonuc_oku(kosu["statepoint"])
                sonuc["keff"], sonuc["sapma"] = okunan["keff"]
                sonuc["entropi"] = okunan.get("entropi")
                sonuc["pasif"] = okunan.get("pasif")
            else:
                sonuc["hata"] = "koşu başarısız (çıkış kodu %d)" % kosu["cikis_kodu"]
        except Exception as e:
            sonuc["hata"] = str(e)
        sonuclar.append(sonuc)
        if geri_cagir:
            geri_cagir(i, toplam, sonuc)
    return sonuclar, notlar


# ============================================================================
# 5. TERMINAL GIRISI
# ============================================================================

def _terminal(argv):
    if not argv or argv[0] in ("-h", "--yardim", "--help"):
        print(__doc__)
        print("\nTARAMA TÜRLERİ")
        for ad, (aciklama, _h, birim, kbirim) in sorted(TURLER.items()):
            print("  %-20s %-58s [%s → %s]" % (ad, aciklama, birim, kbirim))
        return 0

    spec_yolu = argv[0]
    p = {"tur": None, "hedef": None, "bas": None, "son": None, "adet": 5,
         "dizin": None, "s": None}
    i = 1
    while i < len(argv):
        a = argv[i].lstrip("-")
        if a in p:
            i += 1
            p[a] = argv[i]
        else:
            print("bilinmeyen seçenek: %s" % argv[i]); return 2
        i += 1
    if not all([p["tur"], p["bas"], p["son"]]):
        print("--tur, --bas ve --son zorunlu."); return 2

    spec = sema.yukle(spec_yolu)
    tur = p["tur"]
    if tur not in TURLER:
        print("bilinmeyen tür: %s" % tur); return 2
    hedef = p["hedef"]
    if tur == "cubuk_yaricap" and hedef:
        ad, no = hedef.split(":")
        hedef = (ad, int(no))
    degerler = noktalar(float(p["bas"]), float(p["son"]), int(p["adet"]))
    dizin = p["dizin"] or os.path.join(
        os.path.dirname(os.path.abspath(spec_yolu)), "tarama_%s" % tur)

    aciklama, _h, birim, kbirim = TURLER[tur]
    print("=" * 74)
    print(" TARAMA: %s" % aciklama)
    print(" hedef: %s   |   %g → %g %s   |   %d nokta"
          % (hedef, degerler[0], degerler[-1], birim, len(degerler)))
    print("=" * 74)

    def ilerleme(i, toplam, s):
        if s.get("keff"):
            r, sr = reaktivite(s["keff"], s["sapma"])
            print("  [%d/%d] %-12g %s  k = %.5f ± %.5f   ρ = %+9.1f pcm"
                  % (i + 1, toplam, s["deger"], birim, s["keff"], s["sapma"], r))
        else:
            print("  [%d/%d] %-12g %s  başarısız: %s"
                  % (i + 1, toplam, s["deger"], birim, s.get("hata", "?")))

    sonuclar, notlar = calistir(spec, tur, hedef, degerler, dizin,
                                geri_cagir=ilerleme,
                                is_parcacigi=int(p["s"]) if p["s"] else None)
    for n in notlar:
        print("\n  Not: %s" % n)

    k = katsayi(sonuclar)
    print("\n" + "=" * 74)
    if k:
        print("  Katsayı = %+.3f ± %.3f %s   (R² = %.4f, %d nokta)"
              % (k["egim"], k["egim_sapma"], kbirim, k["r2"], k["nokta"]))
        print("  %s" % yorumla(tur, k))
    else:
        print("  Katsayı hesaplanamadı.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(_terminal(sys.argv[1:]))
