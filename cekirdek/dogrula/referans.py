# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/referans.py  --  tally, guc dagilimi, fisil gereksinim, malzeme referanslari

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
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
    """Cubuk bazli guc dagilimi ayarlarini kontrol eder."""
    bulgular = []
    g = spec.get("guc_dagilimi") or {}
    if not g.get("var"):
        return bulgular
    yer = "guc dagilimi"

    cubuk_ad = g.get("cubuk")
    c = cubuk_bul(spec, cubuk_ad) if cubuk_ad else None
    if c is None:
        bulgular.append(Bulgu("hata", yer, "hedef çubuk tanımsız: %s" % cubuk_ad
                              if cubuk_ad else "hedef çubuk seçilmemiş"))
        return bulgular

    bolge = g.get("bolge")
    if not isinstance(bolge, int) or not (0 <= bolge < len(c["bolgeler"])):
        bulgular.append(Bulgu("hata", yer,
                              "geçersiz bölge numarası %s (çubukta %d bölge var)"
                              % (bolge + 1 if isinstance(bolge, int) else "(seçilmemiş)",
                                 len(c["bolgeler"]))))
    else:
        mal = c["bolgeler"][bolge].get("malzeme")
        m = malzeme_bul(spec, mal) if mal else None
        # "yakit" rolu uygunluk'tan (Z >= 90, kurucu ile ayni olcut). Eski
        # kural ad oneki ("U"/"Pu"/"Th") ve zenginlik alanina bakiyordu.
        fisil = bool(m) and "yakit" in uygunluk.tek_malzeme_rolleri(m)
        if not fisil:
            bulgular.append(Bulgu(
                "uyari", yer,
                "seçilen bölgenin malzemesi ('%s') fisil görünmüyor" % mal,
                "Güç dağılımı genellikle yakıt bölgesinde (1. bölge) ölçülür. "
                "Zarf ya da soğutucu seçildiyse sonuç anlamsız olur."))

    # --- cubuk geometride mi, bir kafeste tekrarlaniyor mu? ---
    # Uygun cubuk kurali uygunluk.guc_cubuklari'nda (arayuz listeyi oradan
    # alir). Eskiden "herhangi bir demetin anahtarinda geciyor mu" bakiliyordu:
    # KULLANILMAYAN bir demette gecen cubuk gecerli sayiliyor, kurucu ise
    # "cubugu modelde kullanilmiyor" diyerek duruyordu.
    uygun = uygunluk.guc_cubuklari(spec)
    if cubuk_ad not in uygun:
        geo = uygunluk.geometri_icerigi(spec)
        liste = ("Uygun çubuklar: %s" % ", ".join(uygun) if uygun else
                 "Bu modelde uygun çubuk yok: fisil bölgeli bir çubuğun bir "
                 "demette tekrarlanması gerekir.")
        if cubuk_ad not in geo["cubuk"]:
            bulgular.append(Bulgu(
                "hata", yer,
                "'%s' çubuğu modelde kullanılmıyor — güç dağılımı yalnızca "
                "geometride yer alan bir çubuk için hesaplanabilir" % cubuk_ad,
                "Model kurulurken durur. " + liste))
        elif cubuk_ad not in geo["kafesteki_cubuk"]:
            if (spec["kor"].get("tur") == "tek_cubuk"
                    and spec["kor"].get("cubuk") == cubuk_ad):
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' bir demette tekrarlanmıyor (kor türü: '%s')"
                    % (cubuk_ad, _kor_turu_adi("tek_cubuk")),
                    "Güç dağılımı tekrarlanan hücre örnekleri üzerinden "
                    "hesaplanır; tek bir çubukta dağılım yoktur. Bir demet kurun."))
            else:
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' hiçbir demet haritasında kullanılmıyor" % cubuk_ad,
                    "Tekrarlanan örnek yoksa dağılım tek bir değerden ibaret "
                    "kalır. " + liste))
        # cubuk kafeste ama fisil bolgesi yok: yukaridaki "fisil gorunmuyor"
        # uyarisi bunu zaten soyler.

    skor = g.get("skor") or "kappa-fission"
    if skor not in BILINEN_SKORLAR:
        bulgular.append(Bulgu("uyari", yer, "'%s' bilinen skorlar arasında değil" % skor))
    elif skor not in ("kappa-fission", "fission-q-prompt", "fission-q-recoverable",
                      "heating", "heating-local"):
        bulgular.append(Bulgu(
            "uyari", yer,
            "'%s' bir enerji skoru değil" % skor,
            "Güç dağılımı için enerji bırakan bir skor gerekir; standart seçim "
            "'kappa-fission'dır. 'fission' yalnızca fisyon sayısını verir."))

    # --- eksenel ---
    h = sema_kor_yuksekligi(spec["kor"])
    dilim = int(g.get("eksenel_dilim") or 1)
    if not h:
        bulgular.append(Bulgu(
            "bilgi", yer,
            "model 2B — F_q hesaplanamaz, yalnızca F_ΔH verilir",
            "Yerel güç yoğunluğu tepesi eksenel şekle bağlıdır. Kor sekmesinde "
            "aktif yükseklik tanımlayın."))
    elif dilim < 10:
        bulgular.append(Bulgu(
            "uyari", yer,
            "yalnızca %d eksenel dilim — F_q olduğundan küçük çıkar" % dilim,
            "Kaba dilimler eksenel tepeyi ortalar. En az 10–20 dilim kullanın."))

    tg = g.get("toplam_guc")
    if tg is not None:
        if tg <= 0:
            bulgular.append(Bulgu("hata", yer, "toplam güç sıfırdan büyük olmalı"))
        elif not h:
            bulgular.append(Bulgu(
                "uyari", yer,
                "toplam güç verilmiş ama model 2B — çizgisel güç [W/cm] hesaplanamaz",
                "W/cm için Kor sekmesinde aktif yükseklik tanımlayın."))
    bulgular.extend(_guc_tam_kor_kontrol(spec, cubuk_ad, dilim if h else 1, yer))
    return bulgular


# Guc tally'sinin bin sayisi (ornek x eksenel dilim) bunu asarsa sonuc okuma
# (get_pandas_dataframe(paths=True)) belirgin yavaslar ve bellek buyur.
GUC_BIN_BILGI_ESIGI = 200000


def _guc_tam_kor_kontrol(spec, cubuk_ad, dilim, yer):
    """
    Tam korda (demet haritali kor) guc dagilimi kapsami:
      - hedef cubugu ICERMEYEN demetler haritada bos kalir (uyari). Guc tally'si
        tek bir hucreye (hedef cubugun bolgesi) baglidir; farkli zenginlikteki
        demetler cogu zaman FARKLI cubuk tanimi kullanir ve haritaya girmez.
      - tally bin sayisi = cubuk ornegi x eksenel dilim (bilgi, buyukse).
    """
    from cekirdek.ceviri import _
    kor = spec.get("kor") or {}
    if kor.get("tur") not in ("kare_kafes", "altigen_kafes"):
        return []
    esleme = kor.get("anahtar") or {}
    ornek, eksik = 0, []
    for harf in "".join(kor.get("harita") or []):
        d = sema.demet_bul(spec, esleme.get(harf)) if esleme.get(harf) else None
        if d is None:
            continue
        d_esleme = d.get("anahtar") or {}
        adet = sum(1 for h in "".join(d.get("harita") or []) if d_esleme.get(h) == cubuk_ad)
        ornek += adet
        if adet == 0 and d["ad"] not in eksik:
            eksik.append(d["ad"])
    bulgular = []
    if eksik:
        bulgular.append(Bulgu(
            "uyari", yer,
            _("'%s' çubuğunu içermeyen demetler var (%s) — güç haritasında bu "
              "demetler boş kalır") % (cubuk_ad, ", ".join(eksik)),
            _("Güç dağılımı tek bir çubuk tanımının örnekleri üzerinden sayılır. "
              "Tepe faktörleri yalnızca bu çubuğu içeren demetler için geçerlidir; "
              "farklı zenginlikteki demetler ayrı çubuk tanımı kullanıyorsa "
              "haritaya girmez.")))
    if ornek * dilim > GUC_BIN_BILGI_ESIGI:
        bulgular.append(Bulgu(
            "bilgi", yer,
            _("güç tally'si %d bin (%d çubuk × %d eksenel dilim)") % (ornek * dilim, ornek, dilim),
            _("Sonuç okuma ve harita çizimi yavaşlayabilir; gerekmiyorsa eksenel "
              "dilim sayısını azaltın.")))
    return bulgular


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
            and sema.eksenel_katmanlar(spec["kor"]) is None):
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
