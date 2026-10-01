# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/referans.py  --  tally, guc dagilimi, fisil gereksinim, malzeme referanslari

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import malzeme_bul, cubuk_bul
from cekirdek import sema
from cekirdek import uygunluk
from cekirdek.dogrula._ortak import Bulgu, _kor_turu_adi


# ----------------------------------------------------------------------------
# Bilinen tally skorlari.
#
# !!! BU LISTE KURATORLUDUR !!!
#   OpenMC'nin Python tarafi gecerli skor listesi SUNMAZ; Tally.scores setter'i
#   hicbir dogrulama yapmaz (uydurma bir ad bile kabul edilir) ve hata ancak
#   kosu sirasinda C++ tarafinda cikar. Bu yuzden liste elle tutuluyor.
#   Yeni bir OpenMC surumu skor eklerse liste eskir -- bu nedenle bulunamayan
#   skor HATA degil UYARI uretir.
# ----------------------------------------------------------------------------
BILINEN_SKORLAR = {
    "flux", "total", "absorption", "elastic", "fission", "nu-fission",
    "prompt-nu-fission", "delayed-nu-fission", "kappa-fission",
    "fission-q-prompt", "fission-q-recoverable", "scatter", "nu-scatter",
    "heating", "heating-local", "damage-energy", "decay-rate",
    "inverse-velocity", "current", "events", "pulse-height",
    "(n,2n)", "(n,3n)", "(n,4n)", "(n,gamma)", "(n,p)", "(n,a)", "(n,d)",
    "(n,t)", "(n,elastic)", "(n,level)",
    "ifp-time-numerator", "ifp-beta-numerator", "ifp-denominator",
}


def tally_kontrol(spec):
    """Tally skorlarinin taninip taninmadigini kontrol eder."""
    bulgular = []
    for t in spec.get("tallyler", []):
        yer = "tally:%s" % t.get("ad", "?")
        if not t.get("skorlar"):
            bulgular.append(Bulgu("hata", yer, "en az bir skor seçilmeli"))
        for s in t.get("skorlar", []):
            if s not in BILINEN_SKORLAR and not str(s).isdigit():
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' bilinen skorlar arasında değil" % s,
                    "OpenMC bu skoru tanımayabilir; hata ancak koşu sırasında çıkar. "
                    "Liste elle tutulur (OpenMC geçerli skor listesi sunmuyor); "
                    "yeni bir skor kullanıyorsanız bu uyarı yanlış alarm olabilir."))
    return bulgular


def guc_dagilimi_kontrol(spec):
    """
    Cubuk bazli guc dagilimi ayarlarini kontrol eder. Hedefler
    sema.guc_hedefleri'nden (cok turlu liste; eski tek "cubuk" alani da).
    Tek hedefte bulgular eskisiyle aynidir.
    """
    g = spec.get("guc_dagilimi") or {}
    if not g.get("var"):
        return []
    yer = "guc dagilimi"
    hedefler = sema.guc_hedefleri(g)
    if not hedefler:
        return [Bulgu("hata", yer, "hedef çubuk seçilmemiş")]
    bulgular, gecerli = _guc_hedef_kontrolleri(spec, hedefler, yer)
    if not gecerli:
        return bulgular
    adlar = list(dict.fromkeys(h["cubuk"] for h in gecerli))
    bulgular.extend(_guc_geometri_kontrol(spec, adlar, yer))
    bulgular.extend(_guc_skor_kontrol(g, yer))
    h = sema.model_yuksekligi(spec)
    dilim = int(g.get("eksenel_dilim") or 1)
    bulgular.extend(_guc_eksenel_kontrol(spec, adlar, h, dilim, yer))
    bulgular.extend(_guc_toplam_kontrol(g, h, yer))
    bulgular.extend(_guc_tam_kor_kontrol(spec, adlar, dilim if h else 1, yer))
    bulgular.extend(_guc_cok_tur_kontrol(spec, adlar, yer))
    return bulgular


def _guc_hedef_kontrolleri(spec, hedefler, yer):
    """Her hedef: tanimli mi, bolge gecerli ve fisil mi, tekrar var mi.
    DONER (bulgular, gecerli hedefler) -- tanimsiz hedef varsa gecerli bos
    (kurucu da durur)."""
    bulgular, gorulen = [], set()
    for h in hedefler:
        cubuk_ad = h["cubuk"]
        c = cubuk_bul(spec, cubuk_ad) if cubuk_ad else None
        if c is None:
            bulgular.append(Bulgu("hata", yer, "hedef çubuk tanımsız: %s" % cubuk_ad
                                  if cubuk_ad else "hedef çubuk seçilmemiş"))
            return bulgular, []
        if (cubuk_ad, h["bolge"]) in gorulen:
            bulgular.append(Bulgu("uyari", yer, "'%s' hedef listesinde iki kez var — "
                                  "bir kez sayılır" % cubuk_ad))
            continue
        gorulen.add((cubuk_ad, h["bolge"]))
        bulgular.extend(_guc_bolge_kontrol(spec, c, h["bolge"], yer))
    return bulgular, hedefler


def _guc_bolge_kontrol(spec, c, bolge, yer):
    """Hedef bolge numarasi gecerli mi ve malzemesi fisil mi."""
    if not isinstance(bolge, int) or not (0 <= bolge < len(c["bolgeler"])):
        return [Bulgu("hata", yer,
                      "geçersiz bölge numarası %s (çubukta %d bölge var)"
                      % (bolge + 1 if isinstance(bolge, int) else "(seçilmemiş)",
                         len(c["bolgeler"])))]
    mal = c["bolgeler"][bolge].get("malzeme")
    m = malzeme_bul(spec, mal) if mal else None
    # "yakit" rolu uygunluk'tan (Z >= 90, kurucu ile ayni olcut). Eski
    # kural ad oneki ("U"/"Pu"/"Th") ve zenginlik alanina bakiyordu.
    if bool(m) and "yakit" in uygunluk.tek_malzeme_rolleri(m):
        return []
    return [Bulgu(
        "uyari", yer,
        "seçilen bölgenin malzemesi ('%s') fisil görünmüyor" % mal,
        "Güç dağılımı genellikle yakıt bölgesinde (1. bölge) ölçülür. "
        "Zarf ya da soğutucu seçildiyse sonuç anlamsız olur.")]


def _guc_geometri_kontrol(spec, adlar, yer):
    """
    Hedefler geometride mi, bir kafeste tekrarlaniyor mu? Uygun cubuk kurali
    uygunluk.guc_cubuklari'nda (arayuz listeyi oradan alir). Cok turde
    geometride OLMAYAN tur "modelde yok" uyarisidir (kurucu atlar); hicbiri
    yoksa ya da tek hedef yoksa hata (kurucu durur).
    """
    uygun = uygunluk.guc_cubuklari(spec)
    geo = uygunluk.geometri_icerigi(spec)
    liste = ("Uygun çubuklar: %s" % ", ".join(uygun) if uygun else
             "Bu modelde uygun çubuk yok: fisil bölgeli bir çubuğun bir "
             "demette tekrarlanması gerekir.")
    modelde = [a for a in adlar if a in geo["cubuk"]]
    bulgular = []
    for cubuk_ad in adlar:
        if cubuk_ad in uygun:
            continue
        if cubuk_ad not in geo["cubuk"]:
            bulgular.append(_guc_modelde_yok(cubuk_ad, bool(modelde), liste, yer))
        elif cubuk_ad not in geo["kafesteki_cubuk"]:
            bulgular.append(_guc_tekrarlanmiyor(spec, cubuk_ad, liste, yer))
        # cubuk kafeste ama fisil bolgesi yok: "fisil gorunmuyor" uyarisi soyler.
    return bulgular


def _guc_modelde_yok(cubuk_ad, digeri_var, liste, yer):
    from cekirdek.ceviri import _
    if digeri_var:
        return Bulgu(
            "uyari", yer,
            _("'%s' çubuğu modelde yok — güç haritasında bu tür yer almaz") % cubuk_ad,
            _("Listedeki diğer türler hesaplanır; bu tür atlanır. ") + liste)
    return Bulgu(
        "hata", yer,
        "'%s' çubuğu modelde kullanılmıyor — güç dağılımı yalnızca "
        "geometride yer alan bir çubuk için hesaplanabilir" % cubuk_ad,
        "Model kurulurken durur. " + liste)


def _guc_tekrarlanmiyor(spec, cubuk_ad, liste, yer):
    if (spec["kor"].get("tur") == "tek_cubuk"
            and spec["kor"].get("cubuk") == cubuk_ad):
        return Bulgu(
            "hata", yer,
            "'%s' bir demette tekrarlanmıyor (kor türü: '%s')"
            % (cubuk_ad, _kor_turu_adi("tek_cubuk")),
            "Güç dağılımı tekrarlanan hücre örnekleri üzerinden "
            "hesaplanır; tek bir çubukta dağılım yoktur. Bir demet kurun.")
    return Bulgu(
        "uyari", yer,
        "'%s' hiçbir demet haritasında kullanılmıyor" % cubuk_ad,
        "Tekrarlanan örnek yoksa dağılım tek bir değerden ibaret "
        "kalır. " + liste)


def _guc_skor_kontrol(g, yer):
    skor = g.get("skor") or "kappa-fission"
    if skor not in BILINEN_SKORLAR:
        return [Bulgu("uyari", yer, "'%s' bilinen skorlar arasında değil" % skor)]
    if skor not in ("kappa-fission", "fission-q-prompt", "fission-q-recoverable",
                    "heating", "heating-local"):
        return [Bulgu(
            "uyari", yer,
            "'%s' bir enerji skoru değil" % skor,
            "Güç dağılımı için enerji bırakan bir skor gerekir; standart seçim "
            "'kappa-fission'dır. 'fission' yalnızca fisyon sayısını verir.")]
    return []


def _guc_eksenel_kontrol(spec, adlar, h, dilim, yer):
    if not h:
        return [Bulgu(
            "bilgi", yer,
            "model 2B — F_q hesaplanamaz, yalnızca F_ΔH verilir",
            "Yerel güç yoğunluğu tepesi eksenel şekle bağlıdır. Kor sekmesinde "
            "aktif yükseklik tanımlayın.")]
    bulgular = []
    if dilim < 10:
        bulgular.append(Bulgu(
            "uyari", yer,
            "yalnızca %d eksenel dilim — F_q olduğundan küçük çıkar" % dilim,
            "Kaba dilimler eksenel tepeyi ortalar. En az 10–20 dilim kullanın."))
    if dilim > 1:
        bulgular.extend(_guc_dilim_hizasi(spec, adlar, dilim, yer))
    return bulgular


def _guc_toplam_kontrol(g, h, yer):
    tg = g.get("toplam_guc")
    if tg is None:
        return []
    if tg <= 0:
        return [Bulgu("hata", yer, "toplam güç sıfırdan büyük olmalı")]
    if not h:
        return [Bulgu(
            "uyari", yer,
            "toplam güç verilmiş ama model 2B — çizgisel güç [W/cm] hesaplanamaz",
            "W/cm için Kor sekmesinde aktif yükseklik tanımlayın.")]
    return []


# Dilim siniri ile katman siniri arasindaki fark (dilim kalinligi cinsinden)
# bundan kucukse hizali sayilir.
_DILIM_HIZA_TOL = 1e-6


def _adlar(cubuk_ad):
    return [cubuk_ad] if isinstance(cubuk_ad, str) else list(cubuk_ad)


def _hedef_katman_durumu(spec, cubuk_ad):
    """[(z_alt, z_ust, hedeflerden biri bu katmanda mi)] ya da None
    (katmanlama yok). cubuk_ad: tek ad ya da ad listesi."""
    from cekirdek.geometri import eksenel as _ge
    adlar = _adlar(cubuk_ad)
    if sema.agac_modu(spec):
        from cekirdek import geometri
        m = geometri.model(spec)
        dilim = _ge.eksenel_dilimler(m)
        return [(z0, z1, _ge.dugum_iceriyor(m, ic, _ge._ad_sinama(adlar)))
                for z0, z1, _ad, ic in dilim] or None
    kor = spec["kor"]
    katmanlar = sema.eksenel_katmanlar(kor)
    if katmanlar is None:
        return None
    return [(z0, z1, any(_ge.iceriyor_mu(spec, x, a)
                         for x in sema.katman_adaylari(kor, k) for a in adlar))
            for z0, z1, k in katmanlar]


def _guc_dilim_hizasi(spec, cubuk_ad, dilim, yer):
    """
    M-1 (profesor denetimi): eksenel mesh hedef cubuklarin ARALIGINI kapsar
    (kurucu.guc_eksenel_araligi). Hedef kesintili katmanlardaysa (arada
    cubuksuz katman) ve bir dilim siniri, cubuklu / cubuksuz katman
    sinirina denk gelmiyorsa o dilim KISMEN BOS olur: tepe_faktorleri yalniz
    tamamen bos dilimleri dislar, kismen bos dilim ortalamayi dusurur ve F_q
    birkac % siser. Hizalama: her durum degisim siniri z icin
    (z - z_alt) / dz tamsayiya yakin mi.
    """
    from cekirdek import geometri
    from cekirdek.ceviri import _
    durum = _hedef_katman_durumu(spec, cubuk_ad)
    aralik = geometri.hedef_araligi(spec, _adlar(cubuk_ad))
    if not durum or not aralik:
        return []
    z_alt, z_ust = aralik
    dz = (z_ust - z_alt) / dilim
    sinirlar = [a[1] for a, b in zip(durum, durum[1:])
                if a[2] != b[2] and z_alt < a[1] < z_ust]
    kayik = [z for z in sinirlar
             if abs((z - z_alt) / dz - round((z - z_alt) / dz)) > _DILIM_HIZA_TOL]
    if not kayik:
        return []
    return [Bulgu(
        "uyari", yer,
        _("eksenel dilim sınırları katman sınırlarıyla hizalı değil (z = %s cm); "
          "F_q birkaç %% şişebilir — dilim sayısını katmanlara göre seçin")
        % ", ".join("%g" % z for z in kayik),
        _("Hedef çubuk bazı katmanlarda yok; %d dilimle (%.4g cm) bir dilim hem "
          "çubuklu hem çubuksuz katmana düşer ve ortalamayı düşürür. Katman "
          "kalınlıklarının ortak böleni olan bir dilim kalınlığı seçin.") % (dilim, dz))]


def _guc_cok_tur_kontrol(spec, cubuk_ad, yer):
    """
    Guc tally'leri yalniz HEDEF LISTESINDEKI cubuk turlerini sayar. Modelde
    (ayni kor ya da demet) listede olmayan baska bir fisil cubuk turu
    tekrarlaniyorsa F_dH / F_q yalniz hedefleri kapsar: uyari. Butun uygun
    turler listedeyse uyari YOK. "Fisil ve kafeste tekrarlanan" olcutu
    arayuzun hedef listesiyle aynidir (uygunluk.guc_cubuklari).
    L-3: diger tur hedeflerle HICBIR eksenel katmani paylasmiyorsa (ayni
    cubugun uc parcasi, ornek blanket ortusu) radyal harita eksik degildir: bilgi.
    """
    adlar = _adlar(cubuk_ad)
    digerleri = [c for c in uygunluk.guc_cubuklari(spec) if c not in adlar]
    if not digerleri:
        return []
    hedef = _hedef_katman_durumu(spec, adlar)
    ayri = []
    if hedef is not None:
        for c in digerleri:
            diger = _hedef_katman_durumu(spec, c)
            if not any(h[2] and d[2] for h, d in zip(hedef, diger)):
                ayri.append(c)
    ayni = [c for c in digerleri if c not in ayri]
    return _cok_tur_bulgulari(", ".join(adlar), ayni, ayri, yer)


def _cok_tur_bulgulari(hedef_metni, ayni, ayri, yer):
    from cekirdek.ceviri import _
    bulgular = []
    if ayni:
        bulgular.append(Bulgu(
            "uyari", yer,
            _("F_ΔH yalnız '%s' çubuğunu kapsar — modelde yakıt içeren başka çubuk "
              "türleri de var (%s)") % (hedef_metni, ", ".join(ayni)),
            _("Güç dağılımı yalnız hedef listesindeki çubuk türlerinin örnekleri "
              "üzerinden sayılır; diğer türlerin çubukları haritada yoktur ve en "
              "sıcak çubuk onlardan biri olabilir. Hesap ayarlarında hedef olarak "
              "bütün yakıt çubuklarını seçin. Mutlak güç, hedef çubukların model "
              "fisyon enerjisindeki payıyla dağıtılır.")))
    if ayri:
        bulgular.append(Bulgu(
            "bilgi", yer,
            _("'%s' yalnız ayrı eksenel katmanlarda (%s): güç haritası '%s' çubuğunun "
              "katmanlarını kapsar") % (", ".join(ayri), _("örtü, uç parçası"), hedef_metni),
            _("Bu türler hedef çubukla aynı katmanda bulunmaz; radyal harita eksik "
              "değildir. Onların gücü haritada görünmez ve mutlak güç hedef "
              "çubukların model fisyon enerjisindeki payıyla dağıtılır.")))
    return bulgular


# Guc tally'sinin bin sayisi (ornek x eksenel dilim) bunu asarsa sonuc okuma
# (get_pandas_dataframe(paths=True)) belirgin yavaslar ve bellek buyur.
GUC_BIN_BILGI_ESIGI = 200000


def _guc_tam_kor_kontrol(spec, cubuk_ad, dilim, yer):
    """
    Tam korda (demet haritali kor) guc dagilimi kapsami:
      - hedef cubuklardan HICBIRINI icermeyen demetler haritada bos kalir
        (uyari). Farkli zenginlikteki demetler cogu zaman FARKLI cubuk tanimi
        kullanir: hepsi hedef listesine alinirsa harita tamamlanir.
      - tally bin sayisi = cubuk ornegi x eksenel dilim (bilgi, buyukse).
    """
    from cekirdek.ceviri import _
    kor = spec.get("kor") or {}
    adlar = set(_adlar(cubuk_ad))
    if sema.agac_modu(spec):
        ornek, eksik = _agac_demet_kapsami(spec, adlar)
    elif kor.get("tur") not in ("kare_kafes", "altigen_kafes"):
        return []
    else:
        ornek, eksik = _sablon_demet_kapsami(spec, kor, adlar)
    if sema.agac_modu(spec) and ornek == 0:
        return []
    hedef_metni = ", ".join(_adlar(cubuk_ad))
    bulgular = []
    if eksik:
        bulgular.append(Bulgu(
            "uyari", yer,
            _("'%s' çubuğunu içermeyen demetler var (%s) — güç haritasında bu "
              "demetler boş kalır") % (hedef_metni, ", ".join(eksik)),
            _("Güç dağılımı yalnız hedef listesindeki çubuk türlerinin örnekleri "
              "üzerinden sayılır. Tepe faktörleri yalnızca bu çubukları içeren "
              "demetler için geçerlidir; farklı zenginlikteki demetlerin çubuklarını "
              "da hedef listesine ekleyin.")))
    if ornek * dilim > GUC_BIN_BILGI_ESIGI:
        bulgular.append(Bulgu(
            "bilgi", yer,
            _("güç tally'si %d bin (%d çubuk × %d eksenel dilim)") % (ornek * dilim, ornek, dilim),
            _("Sonuç okuma ve harita çizimi yavaşlayabilir; gerekmiyorsa eksenel "
              "dilim sayısını azaltın.")))
    return bulgular


def _sablon_demet_kapsami(spec, kor, adlar):
    """(hedef cubuk ornegi, hedef icermeyen demetler) -- kor haritasi."""
    esleme = kor.get("anahtar") or {}
    ornek, eksik = 0, []
    for harf in "".join(kor.get("harita") or []):
        d = sema.demet_bul(spec, esleme.get(harf)) if esleme.get(harf) else None
        if d is None:
            continue
        d_esleme = d.get("anahtar") or {}
        adet = sum(1 for h in "".join(d.get("harita") or []) if d_esleme.get(h) in adlar)
        ornek += adet
        if adet == 0 and d["ad"] not in eksik:
            eksik.append(d["ad"])
    return ornek, eksik


def _agac_demet_kapsami(spec, adlar):
    """Agac: (hedef cubuk ornegi, hedef icermeyen kullanilan demetler)."""
    from cekirdek import geometri
    from cekirdek.geometri import eksenel as _ge
    m = geometri.model(spec)
    ornek, demetler = 0, []
    for z in geometri.gez(m):
        if z.dugum.get("tur") != "bilesen":
            continue
        if z.tanim_turu == "cubuk" and z.dugum.get("ad") in adlar:
            ornek += z.carpan
        elif z.tanim_turu == "demet" and z.dugum.get("ad") not in demetler:
            demetler.append(z.dugum["ad"])
    eksik = [d for d in demetler if not _ge.dugum_iceriyor(m, d, _ge._ad_sinama(adlar))]
    return ornek, eksik


def fisil_gereksinim_kontrol(spec):
    """
    Fisil malzeme gerektiren secimler: ozdeger modu ve kutu kaynagi.

    "Fisil" uygunluk'tan gelir: GEOMETRIDE KULLANILAN yakit (Z >= 90). Arayuz
    ayni kuralla analiz/tukenme sekmelerini ve kutu kaynagini gizler.
    Iki durumda da model KURULUR ama OpenMC kosuda durur (olculdu:
    ozdegerde "No fission sites banked"). Bu yuzden tum_kontroller bunu
    nuklid kontrolunden SONRA cagirir: bozuk bir yakit bilesimi (or. veri
    kutuphanesinde olmayan bir nuklid) once KOK NEDEN olarak raporlanmali,
    bu bulgu onu gizlememeli.
    """
    bulgular = []
    a = spec["ayarlar"]
    oz = uygunluk.model_ozeti(spec)
    if oz["fisil"]:
        return bulgular
    # Geometri hic cozulmuyorsa kor hatalari zaten soyler; katmanli korda
    # eksenel_kontrol ayni seyi katman diliyle soyler.
    geometri_var = bool(uygunluk.geometri_icerigi(spec)["malzeme"])
    if (a.get("mod", "eigenvalue") == "eigenvalue" and geometri_var
            and uygunluk.model_boyutu(spec) != "3B_katmanli"):
        bulgular.append(Bulgu(
            "hata", "ayarlar",
            "Özdeğer (k-eff) hesabı fisil malzeme gerektirir — geometride "
            "fisil malzeme yok",
            "OpenMC ilk çevrimde durur (\"No fission sites banked\"). "
            "Zırhlama/aktivasyon hesabı için hesap türünü Sabit kaynak yapın."))
    if (a.get("kaynak") or {}).get("tur") == "kutu":
        bulgular.append(Bulgu(
            "hata", "kaynak",
            "kutu kaynağı fisil malzeme gerektirir — geometride fisil malzeme yok",
            "Kutu kaynağı yalnızca fisil bölgelerde örneklenir; OpenMC hiç "
            "örnek bulamaz ve durur. Nokta kaynak kullanın."))
    return bulgular


def referans_kontrol(spec):
    """Tanimli ama kullanilmayan / kullanilan ama tanimsiz ogeler."""
    from cekirdek.sema import kullanilan_malzemeler
    bulgular = []
    tanimli = {m["ad"] for m in spec["malzemeler"]}
    kullanilan = kullanilan_malzemeler(spec)

    for ad in sorted(kullanilan - tanimli):
        bulgular.append(Bulgu("hata", "malzemeler", "kullanılan ama tanımsız malzeme: %s" % ad))
    for ad in sorted(tanimli - kullanilan):
        bulgular.append(Bulgu("bilgi", "malzemeler",
                              "tanımlı ama modelde kullanılmayan malzeme: %s" % ad))
    return bulgular
