# -*- coding: utf-8 -*-
"""
================================================================================
 guc_yorum.py  --  Guc dagilimi yorumu, coklu tohum, tek satirlik ozet
================================================================================
 cekirdek/guc.py'den ayrildi (dosya boyutu); guc.yorumla / guc.coklu_tohum /
 guc.ozet_metni adlariyla da erisilir. Belirsizlik uzerine olcumler icin
 guc.py basligina bakin.
================================================================================
"""

from cekirdek.ceviri import _, _n, pgettext
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


def _g():
    from cekirdek import guc
    return guc


# Hedef payi bundan kucukse "F_dH yalniz hedef cubugu kapsar" notu yazilir.
_TAM_PAY = 0.999


# Tipik PWR tasarim degerleri (F_dH ~1.65, F_q ~2.3-2.6, cizgisel guc ~400-500 W/cm)
# yalniz basincli su reaktoru kategorisindeki modellerde yorumlanir.
PWR_KATEGORILERI = ("pwr", "vver")


def _pwr_mi(kategori):
    return str(kategori or "").lower() in PWR_KATEGORILERI


def _yanlilik_satiri(yakin, yanlilik, buyukluk):
    """Maksimumun yukari yanliligi (guc_faktor.tepe_yanliligi)."""
    if not yakin or yakin < 2 or yanlilik is None:
        return []
    return [_("  Dikkat: en yüksek değere istatistik olarak ayırt edilemeyen (birleşik 2σ "
              "içinde) %d %s var. Bir en büyük değer hesaplandığı için %s yukarı "
              "yanlıdır: bu tepelerin gerçek değeri eşitse beklenen yanlılık ≈ +%.4f "
              "(σ_tepe × %d değerin beklenen en büyüğü). Tek koşu σ'sı iyimser olduğundan "
              "gerçek yanlılık daha büyük olabilir; çok tohumla harita ortalamasını "
              "kullanın.") % (yakin, buyukluk[0], buyukluk[1], yanlilik, yakin)]


def istatistik_yetersiz(deger, sapma, yanlilik):
    """Tepe faktorunun 1'den farki gurultu + maksimum yanliligindan ayirt
    edilemiyorsa True: (deger − 1) ≤ 2σ + yanlilik. O zaman tasarim yorumu
    (yukleme duzeltilmeli vb.) ertelenir (QA14-Q7)."""
    if deger is None or sapma is None:
        return False
    return (deger - 1.0) <= 2.0 * sapma + (yanlilik or 0.0)


def _yetersiz_satiri(ad, deger, sapma, yanlilik):
    return [_("  İstatistik yetersiz: %s = %.4f ± %.4f; 1'den farkı gürültü ve maksimum "
              "yanlılığından (2σ + %.4f) ayırt edilemiyor. Tasarım yorumu yapılmadı — önce "
              "çevrim başına parçacık ve aktif çevrim sayısını artırın.")
            % (ad, deger, sapma, yanlilik or 0.0)]


def _radyal_satirlari(faktorler, kategori=None):
    f = faktorler["F_dH"]
    satirlar = [_("F_ΔH = %.4f — en sıcak çubuk ortalamanın %%%.1f üstünde güç üretiyor.")
                % (f, (f - 1) * 100)]
    if istatistik_yetersiz(f, faktorler.get("F_dH_sapma"), faktorler.get("F_dH_yanlilik")):
        satirlar += _yetersiz_satiri("F_ΔH", f, faktorler["F_dH_sapma"],
                                     faktorler.get("F_dH_yanlilik"))
    elif f < 1.02:
        satirlar.append(_("  Dağılım neredeyse düz. Yansıtıcı sınırlı tek demet "
                        "hesaplarında beklenen budur; gerçek bir korda kenar "
                        "etkileri ve yakıt yüklemesi tepeyi büyütür."))
    elif f > 1.65 and _pwr_mi(kategori):
        satirlar.append(_("  Yüksek: tipik PWR tasarım sınırı F_ΔH ≈ 1.65 "
                        "civarındadır; yakıt yüklemesi düzeltilmeli."))
    if faktorler.get("tam_kor"):
        satirlar.append(
            _("Tam kor: %d demet, %d yakıt çubuğu. En sıcak demet %s; ortalaması "
              "kor ortalamasının %.4f katı (F_demet). F_ΔH ve F_q tüm kordaki "
              "yakıt çubukları üzerinden hesaplanır.")
            % (faktorler["demet_sayisi"], faktorler["cubuk_sayisi"],
               _g().demet_metni(faktorler["sicak_demet"], faktorler), faktorler["F_demet"]))
    tur = faktorler.get("tur_ozeti")
    if tur:
        satirlar.append(
            _("Çubuk türleri (bağıl ortalama / tepe; bütün yakıt çubuklarının "
              "ortalaması = 1): %s")
            % "; ".join(_n("%s: %.4f / %.4f (%d çubuk)", "%s: %.4f / %.4f (%d çubuk)",
                           v["cubuk_sayisi"])
                        % (ad, v["ortalama"], v["tepe"], v["cubuk_sayisi"])
                        for ad, v in tur.items()))
    # --- maksimumun yukari yanliligi: tepeye yakin cubuklar uzerinden ---
    satirlar += _yanlilik_satiri(faktorler.get("F_dH_tepe_yakini"),
                                 faktorler.get("F_dH_yanlilik"), (pgettext("çoğul", "çubuk"), "F_ΔH"))
    return satirlar


def _eksenel_satirlari(faktorler, kategori=None):
    if not faktorler["F_q"]:
        return [_("F_q tanımsız — model 2B (eksenel yükseklik yok). "
                "Eksenel tepe olmadan yerel güç yoğunluğu hesaplanamaz; "
                "Kor sekmesinde yükseklik tanımlayın.")]
    satirlar = [_("F_q = %.4f — yerel güç yoğunluğu tepesi (eksenel şekil dahil).")
                % faktorler["F_q"]]
    if faktorler["eksenel_dilim"] < 10:
        satirlar.append(
            _("  Dikkat: yalnızca %d eksenel dilim var. Kaba dilimler tepeyi "
            "ortalar ve F_q'yu olduğundan küçük gösterir (saf kosinüs "
            "profilinde ince dilim sınırı π/2 = 1.571'dir). En az 10–20 "
            "dilim kullanın.") % faktorler["eksenel_dilim"])
    bos = faktorler.get("bos_dilimler") or []
    if bos:
        satirlar.append(
            _("  %d eksenel dilim boş (hedef çubuk o katmanlarda yok: %s); bu "
              "dilimler F_q ortalamasına katılmadı.")
            % (len(bos), ", ".join(str(i + 1) for i in bos)))
    satirlar += _yanlilik_satiri(faktorler.get("F_q_tepe_yakini"),
                                 faktorler.get("F_q_yanlilik"),
                                 (_("(çubuk, dilim) çifti"), "F_q"))
    if istatistik_yetersiz(faktorler["F_q"], faktorler.get("F_q_sapma"),
                           faktorler.get("F_q_yanlilik")):
        return satirlar + _yetersiz_satiri("F_q", faktorler["F_q"], faktorler["F_q_sapma"],
                                           faktorler.get("F_q_yanlilik"))
    if faktorler["F_q"] > 2.6 and _pwr_mi(kategori):
        satirlar.append(_("  Yüksek: tipik PWR sınırı F_q ≈ 2.3–2.6."))
    return satirlar


def _mutlak_satirlari(mutlak, hedef_payi_hata=None, kategori=None):
    """hedef_payi_hata: pay tally'si OKUNAMADI (kosucu guc["hedef_payi_hata"]);
    verilmezse pay yoklugu eski kosu (tally yok) sayilir."""
    if not mutlak:
        return []
    satirlar = [_("Çubuk başına ortalama %.1f W, en sıcak çubuk %.1f W.")
                % (mutlak["cubuk_ortalama_W"], mutlak["cubuk_maks_W"])]
    if mutlak.get("hedef_payi") is not None:
        satirlar.append(_("  Modelin fisyon enerjisinin %%%.1f'i bu çubuklarda "
                          "(%.4g W); kalanı diğer fisil bölgelerde.")
                        % (100.0 * mutlak["hedef_payi"], mutlak["hedef_guc"]))
    kesik_disi = mutlak.get("kesik_disi_pay", 1.0)
    if kesik_disi < 1.0:
        satirlar.append(_("  Kesik çubukların gücü (hedef çubuk gücünün %%%.1f'i) "
                          "ortalamaya dağıtılmadı; yukarıdaki güç yalnız kesik olmayan "
                          "çubuklarındır.") % (100.0 * (1.0 - kesik_disi)))
    elif hedef_payi_hata:
        satirlar.append(_("  Uyarı: güç payı tally'si okunamadı: %s. Toplam gücün "
                          "tamamı bu çubuklara yazıldı; başka fisil bölge varsa "
                          "çubuk gücü olduğundan büyüktür.") % hedef_payi_hata)
    else:
        satirlar.append(_("  Not: güç payı ölçülemedi (eski koşu); toplam gücün "
                          "tamamı bu çubuklara yazıldı. Başka fisil bölge varsa "
                          "çubuk gücü olduğundan büyüktür."))
    if "lineer_maks_W_cm" in mutlak:
        lm = mutlak["lineer_maks_W_cm"]
        satirlar.append(_("En yüksek çizgisel güç %.1f W/cm (tepe faktörü: %s).")
                        % (lm, mutlak["lineer_tepe_kaynagi"]))
        if lm > 500 and _pwr_mi(kategori):
            satirlar.append(_("  Sınırın üstünde: tipik PWR çizgisel güç "
                            "sınırı ~400–500 W/cm."))
    satirlar.append(_("  Not: kappa-fission, gama ısınmasının yakıt dışında (zarf, "
                      "soğutucu) bırakılan kısmını da (PWR'da ~%2–3) çubuklara "
                      "yazar; çubuk gücü bu oranda büyük çıkar."))
    return satirlar


def _kapsam_satiri(hedef_payi):
    """Hedef cubuklar model fisyonunun tamamini tasimiyorsa kapsam notu."""
    if hedef_payi is None or hedef_payi >= _TAM_PAY:
        return []
    return [_("Not: F_ΔH ve F_q yalnız hedef çubuk türünü kapsar — modelin fisyon "
              "enerjisinin %%%.1f'i bu çubuklarda, kalanı haritada olmayan diğer "
              "fisil bölgelerde (başka çubuk türü, blanket). En sıcak çubuk "
              "onlardan biri olabilir.") % (100.0 * hedef_payi)]


def yorumla(faktorler, mutlak=None, hedef_payi=None, hedef_payi_hata=None, kategori=None):
    """
    Ogrenciye yonelik kisa yorum satirlari.
    hedef_payi: kappa_hedef / kappa_model (kosucu.sonuc_oku guc["hedef_payi"]);
    verilmezse mutlak["hedef_payi"] kullanilir.
    hedef_payi_hata: pay okunamadiysa hata metni (guc["hedef_payi_hata"]).
    kategori: spec["kategori"]; tipik PWR sinirlari yalniz PWR_KATEGORILERI'nde
    yazilir (SFR, arastirma reaktoru vb. icin anlamsizdir).
    """
    if not faktorler:
        return [_("Güç dağılımı hesaplanamadı.")]
    if hedef_payi is None and mutlak:
        hedef_payi = mutlak.get("hedef_payi")
    satirlar = (_radyal_satirlari(faktorler, kategori) + _kapsam_satiri(hedef_payi)
                + _eksenel_satirlari(faktorler, kategori)
                + _mutlak_satirlari(mutlak, hedef_payi_hata, kategori))
    satirlar.append(_(
        "Not: çubuk başına sapmalar iyimserdir. Özdeğer hesabında ardışık çevrimler "
        "birbirine bağlıdır ve OpenMC'nin raporladığı tally belirsizliği bunu hesaba "
        "katmaz. Ölçülen tohumlar arası farkın büyük kısmı ise yakınsamamış fisyon "
        "kaynağından gelir (sapma, yalnız gürültü değil): Shannon entropisini açın, "
        "entropi düzleşene kadar pasif çevrim sayısını artırın ve modeli en az "
        "5–10 farklı tohumla koşup sonuçların saçılmasına bakın."))
    return satirlar


def coklu_tohum(spec, kok_dizin, tohumlar=(1, 2, 3, 4, 5), is_parcacigi=None,
                geri_cagir=None):
    """
    Ayni modeli birkac BAGIMSIZ tohumla kosar ve tepe faktorlerinin GERCEK
    sacilmasini olcer.

    Tek bir kosunun raporladigi sigma, cevrimler arasi korelasyon yuzunden
    gercek belirsizligin altindadir (bu modulun basligindaki olcume bakin).
    Bagimsiz tohumlar arasindaki sacilma ise dogrudan gercek belirsizliktir.

    VARSAYILAN 5 TOHUM (29.09.2026; once 3): 3 tohumdan hesaplanan standart
    sapmanin kendisi ~%50 belirsizdir (serbestlik derecesi 2); 5 tohumla ~%35.
    Ogrenciye oneri 5-10 tohum. Kaynak yakinsamamissa (Shannon entropisi
    pasif donem sonunda hala kayiyorsa) tohumlar arasi fark sapma icerir;
    once pasif cevrim sayisi artirilir.

    MAKSIMUMUN YANLILIGI: her tohumun F_dH'si bir maksimumdur ve yukari
    yanlidir; ortalamalari da yanli kalir. Bu yuzden once tohumlarin bagil
    haritalari (cubuk, ve 3B'de (cubuk, dilim)) ORTALANIR, sonra maksimum
    alinir (harita_faktorleri). "F_dH" / "F_q" listeleri tohum basina
    maksimumlardir (bilgi; ortalamalari yukari yanli).

    DONER {"F_dH": [...], "F_q": [...], "ozet": {...}}
      ozet: F_dH_harita, F_dH_harita_sapma (tepe cubugun tohumlar arasi
      sacilmasi / √N), F_dH_tepe_yakini, F_dH_yanlilik; F_q icin ayni alanlar;
      F_dH_ort / F_dH_sacilma (tohum maksimumlarinin ortalamasi -- yanli).
    """
    import os
    import statistics as st
    from cekirdek import kosucu

    f_dh, f_q, hatalar, haritalar = [], [], [], []
    for i, t in enumerate(tohumlar):
        alt = dict(spec)
        alt["ayarlar"] = dict(spec["ayarlar"], tohum=int(t))
        dizin = os.path.join(kok_dizin, "tohum_%d" % t)
        try:
            kosu = kosucu.calistir(alt, dizin, is_parcacigi=is_parcacigi)
            if not kosu["basarili"]:
                hatalar.append(_("tohum %d: koşu başarısız") % t)
                continue
            s = kosucu.sonuc_oku(kosu["statepoint"])
            f = (s.get("guc") or {}).get("faktorler")
            if not f:
                hatalar.append(_("tohum %d: güç dağılımı okunamadı") % t)
                continue
            f_dh.append(f["F_dH"])
            if f["F_q"]:
                f_q.append(f["F_q"])
            haritalar.append(f)
        except Exception as e:
            # tek tohumun hatasi olcumu durdurmaz; ozet["hatalar"]da gorunur
            _log.exception("çoklu tohum: tohum %d koşulamadı", t)
            hatalar.append("tohum %d: %s" % (t, e))
        if geri_cagir:
            geri_cagir(i, len(tohumlar), f_dh[-1] if f_dh else None)

    ozet = {"hatalar": hatalar, "tohum_sayisi": len(f_dh)}
    if len(f_dh) >= 2:
        ozet["F_dH_ort"] = st.mean(f_dh)
        ozet["F_dH_sacilma"] = st.stdev(f_dh)
    if len(f_q) >= 2:
        ozet["F_q_ort"] = st.mean(f_q)
        ozet["F_q_sacilma"] = st.stdev(f_q)
    ozet.update(harita_faktorleri(haritalar))
    return {"F_dH": f_dh, "F_q": f_q, "ozet": ozet}


def _ortalama_harita(haritalar):
    """[{anahtar: deger}] -> {anahtar: (ortalama, ortalamanin σ'si)}; yalniz
    butun tohumlarda bulunan anahtarlar. Tohum sayisi < 2 ise {}."""
    import math
    import statistics as st
    if len(haritalar) < 2:
        return {}
    ortak = set(haritalar[0]).intersection(*haritalar[1:])
    n = len(haritalar)
    return {a: (st.mean(h[a] for h in haritalar),
                st.stdev([h[a] for h in haritalar]) / math.sqrt(n)) for a in ortak}


def _harita_tepesi(ort, ad):
    from cekirdek.guc_faktor import tepe_yanliligi
    if not ort:
        return {}
    tepe = max(ort.values(), key=lambda v: v[0])
    yan = tepe_yanliligi(list(ort.values()))
    return {ad + "_harita": tepe[0], ad + "_harita_sapma": tepe[1],
            ad + "_tepe_yakini": yan["yakin"], ad + "_yanlilik": yan["yanlilik"]}


def harita_faktorleri(faktorler_listesi):
    """
    Tohum basina tepe_faktorleri kayitlarindan, ORTALAMA haritanin tepesi.
    F_dH: tohumlarin bagil cubuk gucleri ortalanir, en buyugu alinir.
    F_q : bagil (cubuk, dilim) degerleri ortalanir; yalniz yakitli ciftler
          (her tohumda deger > 0). Bagil degerler her tohumda kendi
          ortalamasina gore oldugundan ortalama harita da ~1 ortalamalidir.
    Ortalamanin σ'si tohumlar arasi sacilma / √N'dir (tohumlar bagimsiz).
    """
    cubuk = [{a: v[0] for a, v in (f.get("bagil") or {}).items()}
             for f in faktorler_listesi if f.get("bagil")]
    dilim = [{(a, i): d[0] for a, k in (f.get("bagil_eksenel") or {}).items()
              for i, d in enumerate(k) if d[0] > 0.0}
             for f in faktorler_listesi if f.get("bagil_eksenel")]
    sonuc = _harita_tepesi(_ortalama_harita(cubuk), "F_dH")
    sonuc.update(_harita_tepesi(_ortalama_harita(dilim), "F_q"))
    return sonuc


def ozet_metni(faktorler, mutlak=None):
    """Tek satirlik ozet (terminal ve durum cubugu icin)."""
    if not faktorler:
        return _("güç dağılımı yok")
    p = ["F_ΔH = %.4f ± %.4f" % (faktorler["F_dH"], faktorler["F_dH_sapma"])]
    if faktorler["F_q"]:
        p.append("F_q = %.4f ± %.4f" % (faktorler["F_q"], faktorler["F_q_sapma"]))
    p[-1] += " " + _("(tek koşu σ'sı iyimser)")
    p.append(_("en sıcak çubuk: %s") % _g().konum_metni(faktorler["sicak_cubuk"],
                                                 faktorler.get("kafes_turu"),
                                                 faktorler.get("kafes_turleri")))
    if faktorler.get("tam_kor"):
        p.append(_("en sıcak demet: %s (F_demet = %.4f)")
                 % (_g().demet_metni(faktorler["sicak_demet"], faktorler), faktorler["F_demet"]))
    return "  |  ".join(p)


def tur_ozeti(bagil, cubuk_turleri):
    """
    Cok turlu guc: tur basina ozet (bagil birimde; TUM cubuklarin ortalamasi
    = 1). Tek turde (ya da tur bilgisi yoksa) None.
    DONER {tur: {"cubuk_sayisi", "ortalama", "tepe", "tepe_cubuk"}}
    """
    if not cubuk_turleri or len(set(cubuk_turleri.values())) < 2:
        return None
    gruplar = {}
    for a, v in bagil.items():
        gruplar.setdefault(cubuk_turleri.get(a), []).append((a, v[0]))
    ozet = {}
    for tur, uyeler in gruplar.items():
        tepe_a, tepe = max(uyeler, key=lambda av: av[1])
        ozet[tur] = {"cubuk_sayisi": len(uyeler),
                     "ortalama": sum(v for _a, v in uyeler) / len(uyeler),
                     "tepe": tepe, "tepe_cubuk": tepe_a}
    return ozet
