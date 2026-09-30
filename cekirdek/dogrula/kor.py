# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/kor.py  --  3. kor kontrolleri (tur, harita, sinir kosullari, alanlar)

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import altigen
from cekirdek import altigen_kor as akor
from cekirdek import sema
from cekirdek import uygunluk
from cekirdek.dogrula._ortak import Bulgu, _kor_turu_adi
from cekirdek.dogrula.geometri import _kafes_icerik_kontrol
from cekirdek.ceviri import _


_YON_ADI = {"yan": "yan", "alt": "alt", "ust": "üst"}
_SINIR_ADI = {"reflective": "Yansıtıcı", "vacuum": "Vakum", "white": "Beyaz",
              "periodic": "Periyodik"}


_GECERLI_KOR = ("tek_cubuk", "tek_demet", "kare_kafes", "altigen_kafes", "tek_plaka",
                "kuresel", "tamburlu")
_GECERLI_BC = ("reflective", "vacuum", "periodic", "white")


def kor_kontrol(spec):
    """Kor turu, referanslar ve sinir kosullari. Tur basina denetim
    _TUR_DENETIMLERI'nde; ardindan sinir kosullari ve kurulmayan alanlar.
    Gelismis (agac) modda dogrula/agac.agac_kontrol (sablon denetimleri
    form mesajlaridir; ayni konu iki kez bildirilmez)."""
    if sema.agac_modu(spec):
        from cekirdek.dogrula.agac import agac_kontrol
        return agac_kontrol(spec)
    kor = spec["kor"]
    tur = kor.get("tur")
    if tur not in _GECERLI_KOR:
        return [Bulgu("hata", "kor", "bilinmeyen kor türü: %s (geçerli: %s)"
                      % (tur, ", ".join(_GECERLI_KOR)))]
    bulgular = list(_TUR_DENETIMLERI[tur](spec, kor))
    bulgular += _sinir_kontrol(spec, kor, tur)
    bulgular += _kurulmayan_alanlar(spec, kor, tur)
    return bulgular


def _tek_cubuk_kontrol(spec, kor):
    bulgular = []
    if not kor.get("cubuk"):
        bulgular.append(Bulgu("hata", "kor", "çubuk seçilmemiş"))
    elif cubuk_bul(spec, kor["cubuk"]) is None:
        bulgular.append(Bulgu("hata", "kor", "tanımsız çubuk: %s" % kor["cubuk"]))
    if kor.get("adim", 0) <= 0:
        bulgular.append(Bulgu("hata", "kor", "hücre adımı sıfırdan büyük olmalı"))
        return bulgular
    c = cubuk_bul(spec, kor.get("cubuk") or "")
    if c:
        dis_r = max([b["r"] for b in c["bolgeler"] if b.get("r")] or [0])
        if dis_r * 2 > kor["adim"]:
            bulgular.append(Bulgu(
                "hata", "kor",
                "çubuğun dış çapı (%.5f cm) hücre adımından (%.5f cm) büyük"
                % (dis_r * 2, kor["adim"])))
    return bulgular


def _tek_demet_kontrol(spec, kor):
    if not kor.get("demet") or demet_bul(spec, kor.get("demet")) is None:
        return [Bulgu("hata", "kor", "tanımsız demet: %s" % kor.get("demet")
                      if kor.get("demet") else "demet seçilmemiş")]
    return []


def _tek_plaka_kontrol(spec, kor):
    if not kor.get("plaka") or plaka_bul(spec, kor.get("plaka")) is None:
        return [Bulgu("hata", "kor", "tanımsız plaka elemanı: %s" % kor.get("plaka")
                      if kor.get("plaka") else "plaka elemanı seçilmemiş")]
    return []


def _tamburlu_kontrol(spec, kor):
    """Tamburlu kor: kor yaricapi, yansitici kusak, dolgu ve tamburlar."""
    R_kor = kor.get("kor_yaricap") or 0.0
    yans = kor.get("yansitici") or {}
    kal = yans.get("kalinlik") or 0.0
    bulgular = []
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
        bulgular.append(Bulgu("hata", "kor", "kor dolgusu tanımsız: %s" % dolgu))
    t = kor.get("tambur") or {}
    if int(t.get("sayi") or 0) <= 0:
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "tambur sayısı 0 — kontrol tamburu olmadan düz yansıtıcı kuşak"))
    else:
        bulgular += _tambur_kontrol(spec, kor, t, R_kor, kal)
    return bulgular


def _tambur_kontrol(spec, kor, t, R_kor, kal):
    """Tambur geometrisi, malzemeleri, donme acisi ve 2B notu."""
    from cekirdek import tambur as _t
    bulgular = [Bulgu("hata", "kor", h) for h in _t.geometri_kontrol(t, R_kor, kal)]
    for anahtar, etiket in (("govde_malzeme", "tambur gövdesi"),
                            ("emici_malzeme", "tambur emicisi")):
        ad = t.get(anahtar)
        if not ad:
            bulgular.append(Bulgu("hata", "kor", "%s malzemesi seçilmemiş" % etiket))
        elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
            bulgular.append(Bulgu("hata", "kor",
                                  "%s için tanımsız malzeme: %s" % (etiket, ad)))
    em = malzeme_bul(spec, t.get("emici_malzeme") or "")
    if em and "emici" not in uygunluk.tek_malzeme_rolleri(em):
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
    return bulgular


def _kuresel_kontrol(spec, kor):
    """Kuresel duzenek: kabuklar, sira, yukseklik ve dis sinir."""
    kabuklar = kor.get("kabuklar") or []
    bulgular = []
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
    return bulgular + _kuresel_alanlar(kor)


def _kuresel_alanlar(kor):
    bulgular = []
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
    return bulgular


def _kare_kafes_kontrol(spec, kor):
    harita = kor.get("harita") or []
    if not harita:
        return [Bulgu("hata", "kor", "kor haritası boş")]
    bulgular = []
    nx, ny = kor["boyut"]
    if len(harita) != ny:
        bulgular.append(Bulgu("hata", "kor",
                              "harita %d satır, boyut %d bekliyor" % (len(harita), ny)))
    for i, satir in enumerate(harita):
        if len(satir) != nx:
            bulgular.append(Bulgu("hata", "kor", "%d. satır %d karakter, %d bekleniyor"
                                  % (i + 1, len(satir), nx)))
    kullanilan = {h for satir in harita for h in satir}
    tanimli = set((kor.get("anahtar") or {}).keys())
    for h in sorted(kullanilan - tanimli):
        bulgular.append(Bulgu("hata", "kor", "haritada tanımsız harf: '%s'" % h))
    bulgular += _kafes_icerik_kontrol(
        spec, "kor", kor.get("adim"), "kare",
        [(kor.get("anahtar") or {}).get(h) for h in sorted(kullanilan)])
    return bulgular


def _altigen_kafes_kontrol(spec, _kor):
    return altigen_kor_kontrol(spec)


_TUR_DENETIMLERI = {
    "tek_cubuk": _tek_cubuk_kontrol, "tek_demet": _tek_demet_kontrol,
    "tek_plaka": _tek_plaka_kontrol, "tamburlu": _tamburlu_kontrol,
    "kuresel": _kuresel_kontrol, "kare_kafes": _kare_kafes_kontrol,
    "altigen_kafes": _altigen_kafes_kontrol,
}


# --- sinir kosullari ---

def _sinir_kontrol(spec, kor, tur):
    sinir = kor.get("sinir") or {}
    bulgular = []
    for yon in ("yan", "alt", "ust"):
        bc = sinir.get(yon)
        if bc and bc not in _GECERLI_BC:
            bulgular.append(Bulgu("hata", "kor", "geçersiz sınır koşulu (%s): %s"
                                  % (_YON_ADI.get(yon, yon), bc)))
    # Hangi yuzeyde hangi sinirin gecerli oldugu uygunluk.sinir_secenekleri'nde
    # (arayuz de listeyi oradan alir). Burada yalnizca ihlal raporlanir.
    yan = sinir.get("yan")
    if yan in _GECERLI_BC and yan not in uygunluk.sinir_secenekleri(spec, "yan"):
        bulgular.append(_yan_periyodik_bulgusu(spec, kor, tur))
    for yon in ("alt", "ust"):
        bulgular += _eksenel_sinir_kontrol(spec, sinir, tur, yon)
    return bulgular


def _yan_periyodik_bulgusu(spec, kor, tur):
    yy = uygunluk.yan_yuzey(spec)
    if tur == "altigen_kafes":
        yuzey = _("demetlerin dış yüzlerinden geçen kırık bir çizgi")
        oneri = _("Altıgen tam korda eşleşen düzlem çifti yoktur.")
        if not _karisik_katmanlar(kor):
            oneri += " " + _("Sonsuz kafes için Yansıtıcı (reflective) sınır "
                             "aynı sonucu verir.")
    elif yy == "altigen":
        yuzey = "altıgen bir prizma"
        oneri = ("Bu sürüm periyodik sınırı yalnızca kare kesitte (x/y düzlem "
                 "çiftleri) sunuyor. Simetrik bir demette sonsuz kafes için "
                 "Yansıtıcı (reflective) sınır aynı k'yı verir.")
    else:
        yuzey = {"kure": "bir küre", "silindir": "bir silindir"}.get(yy, "düzlemsel değil")
        oneri = ("OpenMC periyodik yüzeyin eşini bulamaz (\"Found only one "
                 "periodic surface without a specified partner\") ve koşu "
                 "başlamadan durur. Yansıtıcı ya da Vakum seçin.")
    return Bulgu(
        "hata", "kor",
        "Periyodik (periodic) sınır yalnızca düzlemsel sınırlarda (x/y düzlem "
        "çiftleri) kullanılabilir — bu kor türünün yan yüzeyi %s" % yuzey, oneri)


def _eksenel_sinir_kontrol(spec, sinir, tur, yon):
    bc = sinir.get(yon)
    if bc not in _GECERLI_BC:
        return []
    secenek = uygunluk.sinir_secenekleri(spec, yon)
    if not secenek:
        # 2B modelde z yuzeyi kurulmaz; kurede eksen yoktur (orada hic
        # soylenmez -- kabuk yuzeyi tek sinirdir).
        if tur == "kuresel" or bc == "reflective":
            return []
        return [Bulgu(
            "bilgi", "kor",
            "model 2B — %s sınır koşulu (%s) yok sayılır"
            % (_YON_ADI.get(yon, yon), _SINIR_ADI.get(bc, bc)),
            "2B model eksenel yönde sonsuzdur (yansıtıcı alt/üst ile "
            "eşdeğer). Eksenel sızıntı için Kor sekmesinde yükseklik "
            "tanımlayın.")]
    if bc in secenek:
        return []
    return _eksenel_periyodik(sinir, yon)


def _eksenel_periyodik(sinir, yon):
    # buraya yalnizca periodic duser
    karsi = "ust" if yon == "alt" else "alt"
    if sinir.get(karsi) != "periodic":
        return [Bulgu(
            "hata", "kor",
            "%s sınır Periyodik (periodic) ama %s sınır değil — periyodik yüzeyin "
            "eşi yok" % (_YON_ADI.get(yon, yon).capitalize(), _YON_ADI.get(karsi, karsi)),
            "OpenMC koşu başlamadan durur (\"Found only one periodic surface "
            "without a specified partner\"). Alt/üst için Yansıtıcı ya da "
            "Vakum seçin.")]
    if yon == "alt":
        return [Bulgu(
            "uyari", "kor",
            "alt ve üst sınır Periyodik (periodic) — korun tepesi dibine bağlanır",
            "Sonlu yükseklikteki bir korda eksenel periyodiklik fiziksel "
            "değildir (üst yansıtıcıdan çıkan nötron alt yansıtıcıya girer). "
            "Eksenel simetri için Yansıtıcı sınır kullanın; arayüz bu seçeneği "
            "sunmaz.")]
    return []


# --- bu kor turunde KURULMAYAN alanlar (elle yazilmis dosyalar) ---

def _kurulmayan_alanlar(spec, kor, tur):
    alanlar = uygunluk.kor_alanlari(tur)
    yans = kor.get("yansitici") or {}
    bulgular = []
    if yans.get("var") and "yansitici" not in alanlar:
        bulgular.append(Bulgu(
            "uyari", "kor",
            "'%s' kor türünde yansıtıcı kuşak kurulmaz — dosyada açık ama "
            "yok sayılır" % _kor_turu_adi(tur),
            "Yansıtıcı kuşak yalnızca tek yakıt demeti ve haritalı tam korda "
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
    return bulgular + _sonsuz_ve_2b(spec, kor, tur)


def _sonsuz_ve_2b(spec, kor, tur):
    bulgular = []
    if (kor.get("sinir") or {}).get("yan") == "vacuum" and tur in ("tek_cubuk", "tek_demet"):
        bulgular.append(Bulgu(
            "uyari", "kor",
            "tek hücre/demet modelinde yan sınır Vakum (vacuum) — sızıntı sonsuz "
            "kafes varsayımını bozar",
            "Sonsuz kafes (k∞) istiyorsanız Yansıtıcı (reflective) sınır kullanın."))
    bulgular += _sonsuz_kafes_uyarilari(spec)
    # Kuresel duzenekte "yukseklik" diye bir kavram yoktur; kabuk yaricaplari
    # geometriyi tamamen belirler. Orada 2B uyarisi vermek yanlis olurdu.
    if not sema_kor_yuksekligi(kor) and kor.get("tur") != "kuresel":
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "yükseklik verilmemiş — model eksenel yönde sonsuz (2B) kabul ediliyor"))
    return bulgular


def _katman_konum_adlari(kor):
    """Katman basina haritadaki konumlarin dolgu adlari: [[ad, ...], ...].
    Katmanin kendi dolgusu (butun konumlarda ayni) tek bir ad sayilir."""
    harfler = [h for satir in kor.get("harita") or [] for h in satir]
    ana = kor.get("anahtar") or {}
    katmanlar = sema.eksenel_katmanlar(kor) or [(None, None, {})]
    sonuc = []
    for _z0, _z1, k in katmanlar:
        if k.get("dolgu") and not k.get("anahtar"):
            sonuc.append([k["dolgu"]])
            continue
        esleme = dict(ana)
        esleme.update(k.get("anahtar") or {})
        sonuc.append([esleme.get(h) for h in harfler])
    return sonuc


def _karisik_katmanlar(kor):
    """En az bir katmanda haritada birden fazla farkli dolgu var mi?"""
    return any(len(set(adlar)) > 1 for adlar in _katman_konum_adlari(kor))


def _sonsuz_kafes_uyarilari(spec):
    """
    Yansitici yan sinirin sonsuz kafes anlami ne zaman gecerli?

    * Kilifli tek demet: sinir kilifin DIS yuzundedir, kor adimi kurulmaz;
      demetler arasi sogutucu (SFR'da sodyum) modelde yoktur.
    * Altigen tam kor + reflective kirik cizgi sinir: her demet komsusunun
      aynadaki goruntusuyle cevrilir. Bu yalniz AYNI ve simetrik demetlerde
      sonsuz kafese esittir; karisik haritada (bir katmanda birden fazla
      dolgu) sinir fiziksel bir simetri duzlemi degildir.
    """
    kor = spec["kor"]
    tur = kor.get("tur")
    bulgular = []
    if tur == "tek_demet":
        d = demet_bul(spec, kor.get("demet") or "")
        if d is not None and akor.kilif(d):
            bulgular.append(Bulgu(
                "uyari", "kor",
                _("kılıflı tek demette sınır kılıfın dış yüzündedir — demetler arası "
                  "boşluk (soğutucu) modelde yok"),
                _("SFR tek demet için halka=1 altigen_kafes kullanın (demetler arası "
                  "boşluk): demet adımı kılıf dış ölçüsünden büyük verilir ve aradaki "
                  "boşluk demetin dış dolgusuyla dolar.")))
    elif (tur == "altigen_kafes" and (kor.get("sinir") or {}).get("yan") == "reflective"
          and not (kor.get("yansitici") or {}).get("var") and _karisik_katmanlar(kor)):
        bulgular.append(Bulgu(
            "uyari", "kor",
            _("yan sınır Yansıtıcı ve haritada birden fazla demet türü var — sonsuz "
              "kafes eşdeğerliği yalnız aynı ve simetrik demetlerde geçerli"),
            _("Kırık çizgi sınırda her demet komşusunun aynadaki görüntüsüyle çevrilir; "
              "karışık bir haritada bu gerçek bir simetri düzlemi değildir. Tam kor "
              "için yansıtıcı kuşak ve Vakum sınır kullanın.")))
    return bulgular


def _altigen_harita_kontrol(kor, n):
    """Halka uzunluklari; (bulgular, harita_gecerli)."""
    beklenen = altigen.halka_uzunluklari(n)
    harita = kor.get("harita") or []
    if not harita:
        return [Bulgu("hata", "kor", _("kor haritası boş"))], False
    if len(harita) != len(beklenen):
        return [Bulgu("hata", "kor",
                      _("%d halka bekleniyor, haritada %d satır var")
                      % (len(beklenen), len(harita)),
                      _("Halkalar dıştan içe sıralanır; yarıçapı k olan halkada "
                        "6k öğe, merkezde 1 öğe bulunur."))], False
    bulgular = [Bulgu("hata", "kor", _("%d. halka (yarıçap %d) %d öğe bekliyor, %d var")
                      % (i + 1, n - 1 - i, u, len(satir)))
                for i, (satir, u) in enumerate(zip(harita, beklenen)) if len(satir) != u]
    return bulgular, not bulgular


def _altigen_hedef_kontrol(spec, kor, harfler):
    """Haritadaki her ad: altigen demet, malzeme ya da bosluk olmali."""
    bulgular = []
    anahtar = kor.get("anahtar") or {}
    for h in sorted(harfler - set(anahtar)):
        bulgular.append(Bulgu("hata", "kor", _("haritada tanımsız harf: '%s'") % h))
    yon = kor.get("yonelim") or "x"
    P = float(kor.get("adim") or 0.0)
    for ad in sorted({anahtar[h] for h in harfler if anahtar.get(h)}):
        d = demet_bul(spec, ad)
        if d is None:
            if ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu(
                    "hata", "kor",
                    _("'%s' altıgen kor haritasına konamaz: altıgen demet ya da "
                      "malzeme olmalı") % ad,
                    _("Çubuk ya da plaka tek başına bir demet hücresini doldurmaz; "
                      "önce bir altıgen demete yerleştirin.")))
            continue
        if d.get("tur") != "altigen":
            bulgular.append(Bulgu("hata", "kor",
                                  _("'%s' kare bir demet; altıgen kor haritasına "
                                    "yalnızca altıgen demet konabilir") % ad))
            continue
        bulgular += _altigen_demet_uyumu(d, yon, P)
    return bulgular


def _altigen_demet_uyumu(d, kor_yonelimi, P):
    """Demet yonelimi ve olcusu kor hucresine uyuyor mu? (olculdu: altigen_kor)."""
    bulgular = []
    if d.get("yonelim", "y") == kor_yonelimi:
        bulgular.append(Bulgu(
            "hata", "kor",
            _("'%s' demetinin yönelimi ('%s') kor yönelimiyle aynı — demet "
              "köşeleri komşu hücreye taşar") % (d["ad"], kor_yonelimi),
            _("Kor kafesi pin kafesine göre 90° dönüktür: demet '%s' ise kor "
              "yönelimi '%s' olmalı (VVER / SFR tam korları böyledir).")
            % (d.get("yonelim", "y"), akor.ters_yonelim(d.get("yonelim", "y")))))
    dis = akor.demet_dis_olcu(d)
    if P > 0 and dis > P * (1.0 + 1e-9):
        bulgular.append(Bulgu(
            "hata", "kor",
            _("demet adımı (%.5f cm) '%s' demetinin dış ölçüsünden (%.5f cm%s) küçük")
            % (P, d["ad"], dis, _(", kılıf dahil") if akor.kilif(d) else ""),
            _("Demet adımı düz yüzden düz yüze ölçülür ve en az demetin dış ölçüsü "
              "kadar olmalı; yoksa kor hücresi demeti keser.")))
    return bulgular


def altigen_kor_kontrol(spec):
    """altigen_kafes: halka, harita, yonelim, adim, demet uyumu."""
    kor = spec["kor"]
    bulgular = []
    n = kor.get("halka_sayisi")
    if not isinstance(n, int) or n < 1:
        return [Bulgu("hata", "kor", _("kor halka sayısı en az 1 olmalı: %s") % n)]
    if kor.get("yonelim") not in ("x", "y"):
        bulgular.append(Bulgu("hata", "kor", _("kor yönelimi 'x' ya da 'y' olmalı: %s")
                              % kor.get("yonelim")))
    if float(kor.get("adim") or 0.0) <= 0:
        bulgular.append(Bulgu("hata", "kor", _("demet adımı sıfırdan büyük olmalı")))
    harita_bulgu, gecerli = _altigen_harita_kontrol(kor, n)
    bulgular += harita_bulgu
    if gecerli:
        bulgular += _altigen_hedef_kontrol(spec, kor, {h for s in kor["harita"] for h in s})
    return bulgular
