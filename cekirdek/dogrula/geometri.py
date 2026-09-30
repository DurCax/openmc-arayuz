# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/geometri.py  --  3. cubuk / kontrol cubugu / plaka / demet + kafes olculeri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

import math

from cekirdek import sema
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import altigen
from cekirdek import altigen_kor as akor
from cekirdek import uygunluk
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu


# Kullaniciya gorunen adlar (anahtarlar spec'te ASCII kalir).
_PLAKA_ALAN_ADI = {
    "plaka_sayisi": "plaka sayısı", "et_kalinlik": "yakıt (et) kalınlığı",
    "zarf_kalinlik": "zarf kalınlığı", "kanal_kalinlik": "soğutucu kanalı kalınlığı",
    "plaka_genislik": "plaka genişliği",
}


# ============================================================================
# 3. GEOMETRI
# ============================================================================

def cubuk_kontrol(spec):
    """Radyal bolgelerin sirasi ve kapanisi."""
    bulgular = []
    for c in spec.get("cubuklar", []):
        yer = "cubuk:%s" % c["ad"]
        bolgeler = c.get("bolgeler") or []
        if len(bolgeler) < 2:
            bulgular.append(Bulgu("hata", yer,
                                  "en az iki bölge gerekir (iç bölge + dış dolgu)"))
            continue
        if bolgeler[-1].get("r") is not None:
            bulgular.append(Bulgu(
                "hata", yer, "son bölgenin yarıçapı boş olmalı",
                "Son bölge çubuğun dışıdır ve hücrenin geri kalanını doldurur."))
        yaricaplar = [b.get("r") for b in bolgeler[:-1]]
        for i, r in enumerate(yaricaplar):
            if r is None or r <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "%d. bölgenin yarıçapı sıfırdan büyük olmalı: %s" % (i + 1, r)))
        temiz = [r for r in yaricaplar if isinstance(r, (int, float))]
        for i in range(len(temiz) - 1):
            if temiz[i] >= temiz[i + 1]:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "yarıçaplar artan sırada olmalı: r%d = %.5f ≥ r%d = %.5f"
                    % (i + 1, temiz[i], i + 2, temiz[i + 1])))
        for i, b in enumerate(bolgeler):
            ad = b.get("malzeme")
            if ad is None:
                # Kurucu None'u sessizce bosluk (void) kurar; bilincli bosluk
                # "bosluk" ile secilir.
                bulgular.append(Bulgu(
                    "hata", yer, "%d. bölgenin malzemesi seçilmemiş" % (i + 1),
                    "Bir malzeme seçin; bölge bilerek boş bırakılacaksa "
                    "'Boş (madde yok)' seçin."))
            elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", yer, "tanımsız malzeme: %s" % ad))
    return bulgular


def kontrol_cubugu_kontrol(spec):
    """Kontrol cubuklarinin gereksinimleri."""
    bulgular = []
    h = sema.model_yuksekligi(spec)
    for c in spec.get("cubuklar", []):
        if c.get("tur") != "kontrol":
            continue
        yer = "cubuk:%s" % c["ad"]
        if not h:
            bulgular.append(Bulgu(
                "hata", yer,
                "kontrol çubuğu 3B model gerektirir (kor yüksekliği tanımsız)",
                "Eksenel bir uç konumu olmadan daldırma tanımlanamaz. "
                "Kor sekmesinde aktif yükseklik tanımlayın."))
        d = c.get("daldirma")
        if d is None or not (0.0 <= float(d) <= 100.0):
            bulgular.append(Bulgu("hata", yer,
                                  "daldırma %%0–%%100 arasında olmalı: %s" % d))
        ix = c.get("emici_bolge")
        if not isinstance(ix, int) or not (0 <= ix < len(c.get("bolgeler", []))):
            bulgular.append(Bulgu("hata", yer,
                                  "geçersiz emici bölge: %s"
                                  % (ix + 1 if isinstance(ix, int) else "seçilmemiş")))
        else:
            mal = c["bolgeler"][ix].get("malzeme")
            m = malzeme_bul(spec, mal) if mal else None
            if m:
                # "emici" rolu uygunluk'tan: eskiden burada ayri bir element
                # listesi vardi; "Gd157" nuklidi ya da Dy2TiO5 yanlis alarm
                # veriyordu, borlu su ise (2000 ppm) emici sayiliyordu.
                sogurucu = "emici" in uygunluk.tek_malzeme_rolleri(m)
                if not sogurucu:
                    bulgular.append(Bulgu(
                        "uyari", yer,
                        "emici bölgenin malzemesi ('%s') güçlü bir nötron "
                        "emici içermiyor" % mal,
                        "Kontrol malzemeleri genellikle B4C, Ag-In-Cd, Gd2O3 ya "
                        "da Hf içerir."))
        iz = c.get("izleyici_malzeme")
        if iz is None:
            bulgular.append(Bulgu(
                "uyari", yer,
                "izleyici malzeme seçilmemiş — çubuk çekildiğinde yeri boş (madde yok) kalır",
                "Çekilen çubuğun yerini genellikle soğutucu doldurur; bilerek boş "
                "bırakılacaksa 'Boş (madde yok)' seçin."))
        elif iz != BOSLUK and malzeme_bul(spec, iz) is None:
            bulgular.append(Bulgu("hata", yer, "tanımsız izleyici malzeme: %s" % iz))
    return bulgular


def plaka_kontrol(spec):
    """Plaka eleman olculeri."""
    bulgular = []
    for p in spec.get("plakalar", []):
        yer = "plaka:%s" % p["ad"]
        for alan in ("plaka_sayisi", "et_kalinlik", "zarf_kalinlik",
                     "kanal_kalinlik", "plaka_genislik"):
            deger = p.get(alan)
            if deger is None or deger <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "%s sıfırdan büyük olmalı: %s"
                                      % (_PLAKA_ALAN_ADI[alan], deger)))
        for alan in ("et_malzeme", "zarf_malzeme", "sogutucu"):
            ad = p.get(alan)
            if ad is None:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "%s seçilmemiş" % {"et_malzeme": "yakıt (et) malzemesi",
                                        "zarf_malzeme": "zarf malzemesi",
                                        "sogutucu": "soğutucu"}[alan],
                    "Seçilmeyen malzeme boş (madde yok) kurulurdu."))
            elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", yer,
                                      "%s için tanımsız malzeme: %s"
                                      % (_PLAKA_ALAN_ADI[alan], ad)))
    return bulgular


def demet_kontrol(spec):
    """Kafes haritasi boyutlari ve harf cozumlemesi."""
    bulgular = []
    for d in spec.get("demetler", []):
        yer = "demet:%s" % d["ad"]
        harita = d.get("harita") or []
        if not harita:
            bulgular.append(Bulgu("hata", yer, "harita boş"))
            continue
        if d.get("tur") == "kare":
            nx, ny = d["boyut"]
            if len(harita) != ny:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "harita %d satır ama boyut %d satır bekliyor" % (len(harita), ny)))
            for i, satir in enumerate(harita):
                if len(satir) != nx:
                    bulgular.append(Bulgu(
                        "hata", yer,
                        "%d. satır %d karakter ama %d bekleniyor" % (i + 1, len(satir), nx)))
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or d.get("boyut", [0])[0]
            if not halka or halka < 1:
                bulgular.append(Bulgu("hata", yer, "halka sayısı en az 1 olmalı"))
            else:
                beklenen = altigen.halka_uzunluklari(halka)
                if len(harita) != len(beklenen):
                    bulgular.append(Bulgu(
                        "hata", yer,
                        "%d halka bekleniyor, haritada %d satır var"
                        % (len(beklenen), len(harita)),
                        "Halkalar dıştan içe sıralanır; yarıçapı k olan halkada "
                        "6k öğe, merkezde 1 öğe bulunur."))
                else:
                    for i, (satir, uzunluk) in enumerate(zip(harita, beklenen)):
                        if len(satir) != uzunluk:
                            bulgular.append(Bulgu(
                                "hata", yer,
                                "%d. halka (yarıçap %d) %d öğe bekliyor, %d var"
                                % (i + 1, halka - 1 - i, uzunluk, len(satir))))
            if d.get("yonelim", "y") not in ("x", "y"):
                bulgular.append(Bulgu("hata", yer,
                                      "yönelim 'x' ya da 'y' olmalı: %s" % d.get("yonelim")))
        if d.get("adim", 0) <= 0:
            bulgular.append(Bulgu("hata", yer, "adım sıfırdan büyük olmalı"))

        kullanilan = {h for satir in harita for h in satir}
        tanimli = set((d.get("anahtar") or {}).keys())
        for h in sorted(kullanilan - tanimli):
            bulgular.append(Bulgu("hata", yer,
                                  "haritada tanımsız harf: '%s'" % h,
                                  "Harfi demetin anahtar listesine ekleyin."))
        for h in sorted(tanimli - kullanilan):
            bulgular.append(Bulgu("bilgi", yer,
                                  "anahtarda tanımlı ama haritada kullanılmayan harf: '%s'" % h))
        for h, hedef in (d.get("anahtar") or {}).items():
            if (cubuk_bul(spec, hedef) is None and plaka_bul(spec, hedef) is None
                    and demet_bul(spec, hedef) is None
                    and hedef != BOSLUK and malzeme_bul(spec, hedef) is None):
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' harfi tanımsız bir ada işaret ediyor: %s" % (h, hedef)))
        bulgular += _kafes_icerik_kontrol(
            spec, yer, d.get("adim"), d.get("tur", "kare"),
            [(d.get("anahtar") or {}).get(h) for h in sorted(kullanilan)])
        bulgular += kilif_kontrol(spec, d)
    return bulgular


def _en_buyuk_pin_yaricapi(spec, d):
    """Haritadaki cubuklarin en buyuk dis yaricapi; cubuk yoksa adim/2."""
    anahtar = d.get("anahtar") or {}
    caplar = [_cubuk_dis_capi(cubuk_bul(spec, anahtar[h]))
              for h in {h for s in d.get("harita") or [] for h in s}
              if anahtar.get(h) and cubuk_bul(spec, anahtar[h]) is not None]
    caplar = [c for c in caplar if c]
    return max(caplar) / 2.0 if caplar else float(d.get("adim") or 0.0) / 2.0


def kilif_kontrol(spec, d):
    """Altigen demet kilifi (duct): olculer, malzeme, pinlerin kilifa sigmasi."""
    k = d.get("kilif")
    if not k:
        return []
    yer = "demet:%s" % d["ad"]
    if d.get("tur") != "altigen" or not isinstance(k, dict):
        return [Bulgu("uyari", yer, _("kılıf yalnızca altıgen demette kurulur — yok sayılır"))]
    bulgular = []
    ic, kal = k.get("ic_duz"), k.get("kalinlik")
    for deger, ad in ((ic, _("kılıf iç ölçüsü")), (kal, _("kılıf kalınlığı"))):
        if not isinstance(deger, (int, float)) or deger <= 0:
            bulgular.append(Bulgu("hata", yer, _("%s sıfırdan büyük olmalı: %s") % (ad, deger)))
    m = k.get("malzeme")
    if not m:
        bulgular.append(Bulgu("hata", yer, _("kılıf malzemesi seçilmemiş")))
    elif m != BOSLUK and malzeme_bul(spec, m) is None:
        bulgular.append(Bulgu("hata", yer, _("kılıf için tanımsız malzeme: %s") % m))
    if bulgular:
        return bulgular
    # En distaki pin merkezleri zarfin duz kenarinda: (halka-1) adim sqrt3/2
    gerekli = 2.0 * ((akor.halka_sayisi(d) - 1) * float(d.get("adim") or 0.0)
                     * math.sqrt(3.0) / 2.0 + _en_buyuk_pin_yaricapi(spec, d))
    if gerekli > float(ic) * (1.0 + 1e-9):
        bulgular.append(Bulgu(
            "hata", yer,
            _("pinler kılıfa sığmıyor: kılıf iç ölçüsü %.5f cm, en az %.5f cm gerekli")
            % (float(ic), gerekli),
            _("Kılıf, dış halkadaki pinleri keser. İç ölçüyü büyütün ya da adımı "
              "küçültün.")))
    return bulgular


def _cubuk_dis_capi(c):
    """Cubugun dis capi: 2 x en buyuk SONLU bolge yaricapi (son bolge 'disarisi')."""
    r = [b.get("r") for b in (c.get("bolgeler") or [])
         if isinstance(b.get("r"), (int, float)) and b.get("r") > 0]
    return 2.0 * max(r) if r else None


def _kafes_olculeri(d):
    """
    Ic ice yerlestirilen kafesin olculeri: (zarf_x, zarf_y, en_dar_genislik).

    Zarf kurucu.py'nin kullandigi olcudur (kare: adim x n; altigen:
    altigen.kapsayan_olcu). En dar genislik altigende kurucu._altigen_sinir'in
    duz yuzden duz yuze olcusudur: (halka-1) * adim * sqrt(3) + adim.
    """
    adim = float(d.get("adim") or 0.0)
    if d.get("tur") == "altigen":
        halka = d.get("halka_sayisi") or (d.get("boyut") or [1])[0] or 1
        gx, gy = altigen.kapsayan_olcu(halka, adim, d.get("yonelim", "y"))
        if akor.kilif(d):
            dis = akor.demet_dis_olcu(d)
            return (*akor.prizma_kutusu(dis / 2.0, d.get("yonelim", "y")), dis)
        return gx, gy, (halka - 1) * adim * math.sqrt(3.0) + adim
    nx, ny = (d.get("boyut") or [1, 1])[:2]
    return adim * nx, adim * ny, adim * min(nx, ny)


def _kafes_icerik_kontrol(spec, yer, adim, kafes_turu, hedefler):
    """
    Kafes adimi, konumlara yerlestirilen iceriklerden kucuk mu?

    Cubuk: dis cap > adim ise cubuk komsu hucreye TASAR. OpenMC bunu hata
    saymaz -- kafes hucresi cubugu sessizce keser. Ic ice kafes: zarfi hucreye
    sigmiyorsa dis halkadaki cubuklar kesilir.
      kare hucre (adim x adim)  : zarfin iki boyutu da adima sigmali
      altigen hucre (duz yuz = adim): en dar genislik adimdan buyukse hicbir
                                    yonelimde sigmaz
    Yalnizca KESIN tasmalar raporlanir (yanlis alarm yerine sessiz kalir).
    """
    bulgular = []
    try:
        P = float(adim or 0.0)
    except (TypeError, ValueError):
        return bulgular
    if P <= 0:
        return bulgular
    pay = P * (1.0 + 1e-9)
    gorulen = set()
    for hedef in hedefler:
        if not hedef or hedef in gorulen:
            continue
        gorulen.add(hedef)
        c = cubuk_bul(spec, hedef)
        if c is not None:
            cap = _cubuk_dis_capi(c)
            if cap and cap > pay:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' çubuğunun dış çapı (%.5f cm) kafes adımından (%.5f cm) "
                    "büyük — çubuk komşu hücreye taşar" % (hedef, cap, P),
                    "OpenMC bunu hata saymaz: kafes hücresi çubuğu sessizce keser. "
                    "Adımı büyütün ya da çubuk yarıçaplarını küçültün."))
            continue
        ic = demet_bul(spec, hedef)
        if ic is not None:
            gx, gy, dar = _kafes_olculeri(ic)
            gerekli = max(gx, gy) if kafes_turu != "altigen" else dar
            if gerekli > pay:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "iç içe demet '%s' (%.4f × %.4f cm) demet adımına (%.5f cm) "
                    "sığmıyor" % (hedef, gx, gy, P),
                    "Kafes hücresi içteki demeti keser; dış halkadaki çubuklar "
                    "sessizce kaybolur. Dış demetin adımı en az %.5f cm olmalı."
                    % gerekli))
    return bulgular
