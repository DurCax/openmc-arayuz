# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/kor.py  --  3. kor kontrolleri (tur, harita, sinir kosullari, alanlar)

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import sema
from cekirdek import uygunluk
from cekirdek.dogrula._ortak import Bulgu, _kor_turu_adi
from cekirdek.dogrula.geometri import _kafes_icerik_kontrol


_YON_ADI = {"yan": "yan", "alt": "alt", "ust": "üst"}
_SINIR_ADI = {"reflective": "Yansıtıcı", "vacuum": "Vakum", "white": "Beyaz",
              "periodic": "Periyodik"}


def kor_kontrol(spec):
    """Kor turu, referanslar ve sinir kosullari."""
    bulgular = []
    kor = spec["kor"]
    tur = kor.get("tur")
    gecerli = ("tek_cubuk", "tek_demet", "kare_kafes", "tek_plaka", "kuresel",
               "tamburlu")
    if tur not in gecerli:
        bulgular.append(Bulgu("hata", "kor",
                              "bilinmeyen kor türü: %s (geçerli: %s)"
                              % (tur, ", ".join(gecerli))))
        return bulgular

    if tur == "tek_cubuk":
        if not kor.get("cubuk"):
            bulgular.append(Bulgu("hata", "kor", "çubuk seçilmemiş"))
        elif cubuk_bul(spec, kor["cubuk"]) is None:
            bulgular.append(Bulgu("hata", "kor", "tanımsız çubuk: %s" % kor["cubuk"]))
        if kor.get("adim", 0) <= 0:
            bulgular.append(Bulgu("hata", "kor", "hücre adımı sıfırdan büyük olmalı"))
        else:
            c = cubuk_bul(spec, kor.get("cubuk") or "")
            if c:
                dis_r = max([b["r"] for b in c["bolgeler"] if b.get("r")] or [0])
                if dis_r * 2 > kor["adim"]:
                    bulgular.append(Bulgu(
                        "hata", "kor",
                        "çubuğun dış çapı (%.5f cm) hücre adımından (%.5f cm) büyük"
                        % (dis_r * 2, kor["adim"])))
    elif tur == "tek_demet":
        if not kor.get("demet") or demet_bul(spec, kor.get("demet")) is None:
            bulgular.append(Bulgu("hata", "kor", "tanımsız demet: %s" % kor.get("demet")
                                  if kor.get("demet") else "demet seçilmemiş"))
    elif tur == "tek_plaka":
        if not kor.get("plaka") or plaka_bul(spec, kor.get("plaka")) is None:
            bulgular.append(Bulgu("hata", "kor", "tanımsız plaka elemanı: %s" % kor.get("plaka")
                                  if kor.get("plaka") else "plaka elemanı seçilmemiş"))
    elif tur == "tamburlu":
        from cekirdek import tambur as _t
        R_kor = kor.get("kor_yaricap") or 0.0
        yans = kor.get("yansitici") or {}
        kal = yans.get("kalinlik") or 0.0
        if R_kor <= 0:
            bulgular.append(Bulgu("hata", "kor", "kor yarıçapı sıfırdan büyük olmalı"))
        if kal <= 0:
            bulgular.append(Bulgu("hata", "kor",
                                  "tamburlu korda yansıtıcı kuşak kalınlığı sıfırdan büyük olmalı"))
        if not yans.get("malzeme") or yans["malzeme"] == BOSLUK:
            bulgular.append(Bulgu("uyari", "kor",
                                  "yansıtıcı kuşağın malzemesi seçilmemiş (boş, madde yok)"))
        dolgu = kor.get("dolgu")
        if not dolgu:
            bulgular.append(Bulgu("hata", "kor", "kor dolgusu seçilmemiş"))
        elif (dolgu != BOSLUK and cubuk_bul(spec, dolgu) is None
              and demet_bul(spec, dolgu) is None
              and malzeme_bul(spec, dolgu) is None):
            bulgular.append(Bulgu("hata", "kor",
                                  "kor dolgusu tanımsız: %s" % dolgu))
        t = kor.get("tambur") or {}
        if int(t.get("sayi") or 0) <= 0:
            bulgular.append(Bulgu(
                "bilgi", "kor",
                "tambur sayısı 0 — kontrol tamburu olmadan düz yansıtıcı kuşak"))
        else:
            for h in _t.geometri_kontrol(t, R_kor, kal):
                bulgular.append(Bulgu("hata", "kor", h))
            for anahtar, etiket in (("govde_malzeme", "tambur gövdesi"),
                                    ("emici_malzeme", "tambur emicisi")):
                ad = t.get(anahtar)
                if not ad:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%s malzemesi seçilmemiş" % etiket))
                elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%s için tanımsız malzeme: %s" % (etiket, ad)))
            em = malzeme_bul(spec, t.get("emici_malzeme") or "")
            if em:
                if "emici" not in uygunluk.tek_malzeme_rolleri(em):
                    bulgular.append(Bulgu(
                        "uyari", "kor",
                        "tambur emicisi ('%s') güçlü bir nötron emici içermiyor"
                        % t.get("emici_malzeme")))
            d = t.get("donme")
            if d is None or not (-360.0 <= float(d) <= 360.0):
                bulgular.append(Bulgu("hata", "kor",
                                      "tambur dönme açısı −360…360° aralığında olmalı: %s" % d))
            if not sema_kor_yuksekligi(kor):
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "tamburlu kor 2B — eksenel sızıntı yok, k-eff olduğundan yüksek çıkar",
                    "Gerçekçi bir tambur değeri için Kor sekmesinde aktif yükseklik tanımlayın."))

    elif tur == "kuresel":
        kabuklar = kor.get("kabuklar") or []
        if not kabuklar:
            bulgular.append(Bulgu("hata", "kor", "küresel düzenekte en az bir kabuk gerekir"))
        for i, k in enumerate(kabuklar):
            if not k.get("r") or k["r"] <= 0:
                bulgular.append(Bulgu("hata", "kor",
                                      "%d. kabuğun yarıçapı sıfırdan büyük olmalı" % (i + 1)))
            ad = k.get("malzeme")
            if ad and ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", "kor",
                                      "%d. kabukta tanımsız malzeme: %s" % (i + 1, ad)))
        r = [k.get("r") for k in kabuklar if k.get("r")]
        for i in range(len(r) - 1):
            if r[i] >= r[i + 1]:
                bulgular.append(Bulgu(
                    "hata", "kor",
                    "kabuk yarıçapları artan sırada olmalı: r%d = %.5f ≥ r%d = %.5f"
                    % (i + 1, r[i], i + 2, r[i + 1])))
        if kor.get("yukseklik"):
            bulgular.append(Bulgu(
                "hata", "kor",
                "küresel düzenekte yükseklik tanımlanamaz (%g cm)" % float(kor["yukseklik"]),
                "Küre geometrisi kabuk yarıçaplarıyla tamamen belirlenir; yükseklik "
                "kaynak kutusuna, entropi ağına ve tally ağlarına girer. Kor "
                "sekmesinde küresel tür seçiliyken alan temizlenir."))
        if kor.get("sinir", {}).get("yan") == "reflective":
            bulgular.append(Bulgu(
                "uyari", "kor",
                "küresel düzenekte dış sınır Yansıtıcı (reflective) — çıplak (bare) bir "
                "kritiklik düzeneği modelliyorsanız Vakum (vacuum) olmalı",
                "Yansıtıcı sınır sonsuz bir ortam demektir; kritik küre "
                "düzenekleri çıplaktır (Vakum)."))

    elif tur == "kare_kafes":
        harita = kor.get("harita") or []
        if not harita:
            bulgular.append(Bulgu("hata", "kor", "kor haritası boş"))
        else:
            nx, ny = kor["boyut"]
            if len(harita) != ny:
                bulgular.append(Bulgu("hata", "kor",
                                      "harita %d satır, boyut %d bekliyor" % (len(harita), ny)))
            for i, satir in enumerate(harita):
                if len(satir) != nx:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%d. satır %d karakter, %d bekleniyor"
                                          % (i + 1, len(satir), nx)))
            kullanilan = {h for satir in harita for h in satir}
            tanimli = set((kor.get("anahtar") or {}).keys())
            for h in sorted(kullanilan - tanimli):
                bulgular.append(Bulgu("hata", "kor", "haritada tanımsız harf: '%s'" % h))
            bulgular += _kafes_icerik_kontrol(
                spec, "kor", kor.get("adim"), "kare",
                [(kor.get("anahtar") or {}).get(h) for h in sorted(kullanilan)])

    # --- sinir kosullari ---
    sinir = kor.get("sinir") or {}
    gecerli_bc = ("reflective", "vacuum", "periodic", "white")
    for yon in ("yan", "alt", "ust"):
        bc = sinir.get(yon)
        if bc and bc not in gecerli_bc:
            bulgular.append(Bulgu("hata", "kor",
                                  "geçersiz sınır koşulu (%s): %s" % (_YON_ADI.get(yon, yon), bc)))
    # Hangi yuzeyde hangi sinirin gecerli oldugu uygunluk.sinir_secenekleri'nde
    # (arayuz de listeyi oradan alir). Burada yalnizca ihlal raporlanir.
    yan = sinir.get("yan")
    if yan in gecerli_bc and yan not in uygunluk.sinir_secenekleri(spec, "yan"):
        yy = uygunluk.yan_yuzey(spec)
        if yy == "altigen":
            yuzey = "altıgen bir prizma"
            oneri = ("Bu sürüm periyodik sınırı yalnızca kare kesitte (x/y düzlem "
                     "çiftleri) sunuyor. Simetrik bir demette sonsuz kafes için "
                     "Yansıtıcı (reflective) sınır aynı k'yı verir.")
        else:
            yuzey = {"kure": "bir küre", "silindir": "bir silindir"}.get(yy, "düzlemsel değil")
            oneri = ("OpenMC periyodik yüzeyin eşini bulamaz (\"Found only one "
                     "periodic surface without a specified partner\") ve koşu "
                     "başlamadan durur. Yansıtıcı ya da Vakum seçin.")
        bulgular.append(Bulgu(
            "hata", "kor",
            "Periyodik (periodic) sınır yalnızca düzlemsel sınırlarda (x/y düzlem "
            "çiftleri) kullanılabilir — bu kor türünün yan yüzeyi %s" % yuzey, oneri))
    for yon in ("alt", "ust"):
        bc = sinir.get(yon)
        if bc not in gecerli_bc:
            continue
        secenek = uygunluk.sinir_secenekleri(spec, yon)
        if not secenek:
            # 2B modelde z yuzeyi kurulmaz; kurede eksen yoktur (orada hic
            # soylenmez -- kabuk yuzeyi tek sinirdir).
            if tur != "kuresel" and bc != "reflective":
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "model 2B — %s sınır koşulu (%s) yok sayılır" % (_YON_ADI.get(yon, yon), _SINIR_ADI.get(bc, bc)),
                    "2B model eksenel yönde sonsuzdur (yansıtıcı alt/üst ile "
                    "eşdeğer). Eksenel sızıntı için Kor sekmesinde yükseklik "
                    "tanımlayın."))
            continue
        if bc in secenek:
            continue
        # buraya yalnizca periodic duser
        karsi = "ust" if yon == "alt" else "alt"
        if sinir.get(karsi) != "periodic":
            bulgular.append(Bulgu(
                "hata", "kor",
                "%s sınır Periyodik (periodic) ama %s sınır değil — periyodik yüzeyin "
                "eşi yok" % (_YON_ADI.get(yon, yon).capitalize(), _YON_ADI.get(karsi, karsi)),
                "OpenMC koşu başlamadan durur (\"Found only one periodic surface "
                "without a specified partner\"). Alt/üst için Yansıtıcı ya da "
                "Vakum seçin."))
        elif yon == "alt":
            bulgular.append(Bulgu(
                "uyari", "kor",
                "alt ve üst sınır Periyodik (periodic) — korun tepesi dibine bağlanır",
                "Sonlu yükseklikteki bir korda eksenel periyodiklik fiziksel "
                "değildir (üst yansıtıcıdan çıkan nötron alt yansıtıcıya girer). "
                "Eksenel simetri için Yansıtıcı sınır kullanın; arayüz bu seçeneği "
                "sunmaz."))

    # --- bu kor turunde KURULMAYAN alanlar (elle yazilmis dosyalar) ---
    alanlar = uygunluk.kor_alanlari(tur)
    yans = kor.get("yansitici") or {}
    if yans.get("var") and "yansitici" not in alanlar:
        bulgular.append(Bulgu(
            "uyari", "kor",
            "'%s' kor türünde yansıtıcı kuşak kurulmaz — dosyada açık ama "
            "yok sayılır" % _kor_turu_adi(tur),
            "Yansıtıcı kuşak yalnızca tek yakıt demeti ve kare haritalı tam korda "
            "(isteğe bağlı) ve tamburlu korda (zorunlu) kurulur. Model "
            "yansıtıcısız çalışır."))
    artik = [alan for alan in sema.KOR_TURE_OZGU
             if alan not in alanlar and alan not in sema.KOR_KORUNAN
             and alan != "yansitici"
             and kor.get(alan, sema.VARSAYILAN_KOR[alan]) != sema.VARSAYILAN_KOR[alan]]
    if artik:
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "'%s' kor türünde kullanılmayan alanlar dolu: %s — yok sayılır"
            % (_kor_turu_adi(tur), ", ".join(artik)),
            "Başka bir kor türünden kalmış olabilir; kurucu bu alanlara bakmaz."))
    if sinir.get("yan") == "vacuum" and tur in ("tek_cubuk", "tek_demet"):
        bulgular.append(Bulgu(
            "uyari", "kor",
            "tek hücre/demet modelinde yan sınır Vakum (vacuum) — sızıntı sonsuz "
            "kafes varsayımını bozar",
            "Sonsuz kafes (k∞) istiyorsanız Yansıtıcı (reflective) sınır kullanın."))
    # Kuresel duzenekte "yukseklik" diye bir kavram yoktur; kabuk yaricaplari
    # geometriyi tamamen belirler. Orada 2B uyarisi vermek yanlis olurdu.
    if not sema_kor_yuksekligi(kor) and kor.get("tur") != "kuresel":
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "yükseklik verilmemiş — model eksenel yönde sonsuz (2B) kabul ediliyor"))
    return bulgular
