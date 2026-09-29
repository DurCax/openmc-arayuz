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

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


def _g():
    from cekirdek import guc
    return guc


# Hedef payi bundan kucukse "F_dH yalniz hedef cubugu kapsar" notu yazilir.
_TAM_PAY = 0.999


def _radyal_satirlari(faktorler):
    f = faktorler["F_dH"]
    satirlar = ["F_ΔH = %.4f — en sıcak çubuk ortalamanın %%%.1f üstünde güç üretiyor."
                % (f, (f - 1) * 100)]
    if f < 1.02:
        satirlar.append("  Dağılım neredeyse düz. Yansıtıcı sınırlı tek demet "
                        "hesaplarında beklenen budur; gerçek bir korda kenar "
                        "etkileri ve yakıt yüklemesi tepeyi büyütür.")
    elif f > 1.65:
        satirlar.append("  Yüksek: tipik PWR tasarım sınırı F_ΔH ≈ 1.65 "
                        "civarındadır; yakıt yüklemesi düzeltilmeli.")
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
            % "; ".join("%s: %.4f / %.4f (%d çubuk)" % (ad, v["ortalama"], v["tepe"],
                                                        v["cubuk_sayisi"])
                        for ad, v in tur.items()))
    # --- maksimumun yukari yanliligi ---
    oran = faktorler.get("yanlilik_orani")
    if oran is not None and oran > 0.3:
        satirlar.append(
            "  Dikkat: çubuk başına istatistik sapma (%.4f) dağılımın gerçek "
            "saçılmasının (%.4f) %%%.0f kadarı. Bir en büyük değer hesaplandığı "
            "için F_ΔH bu durumda yukarı yanlıdır — gerçek tepe daha düşüktür. "
            "Çevrim başına parçacık sayısını artırın."
            % (faktorler["istatistik_sapma"], faktorler["sacilma"], oran * 100))
    return satirlar


def _eksenel_satirlari(faktorler):
    if not faktorler["F_q"]:
        return ["F_q tanımsız — model 2B (eksenel yükseklik yok). "
                "Eksenel tepe olmadan yerel güç yoğunluğu hesaplanamaz; "
                "Kor sekmesinde yükseklik tanımlayın."]
    satirlar = ["F_q = %.4f — yerel güç yoğunluğu tepesi (eksenel şekil dahil)."
                % faktorler["F_q"]]
    if faktorler["eksenel_dilim"] < 10:
        satirlar.append(
            "  Dikkat: yalnızca %d eksenel dilim var. Kaba dilimler tepeyi "
            "ortalar ve F_q'yu olduğundan küçük gösterir (saf kosinüs "
            "profilinde ince dilim sınırı π/2 = 1.571'dir). En az 10–20 "
            "dilim kullanın." % faktorler["eksenel_dilim"])
    bos = faktorler.get("bos_dilimler") or []
    if bos:
        satirlar.append(
            _("  %d eksenel dilim boş (hedef çubuk o katmanlarda yok: %s); bu "
              "dilimler F_q ortalamasına katılmadı.")
            % (len(bos), ", ".join(str(i + 1) for i in bos)))
    if faktorler["F_q"] > 2.6:
        satirlar.append("  Yüksek: tipik PWR sınırı F_q ≈ 2.3–2.6.")
    return satirlar


def _mutlak_satirlari(mutlak, hedef_payi_hata=None):
    """hedef_payi_hata: pay tally'si OKUNAMADI (kosucu guc["hedef_payi_hata"]);
    verilmezse pay yoklugu eski kosu (tally yok) sayilir."""
    if not mutlak:
        return []
    satirlar = ["Çubuk başına ortalama %.1f W, en sıcak çubuk %.1f W."
                % (mutlak["cubuk_ortalama_W"], mutlak["cubuk_maks_W"])]
    if mutlak.get("hedef_payi") is not None:
        satirlar.append(_("  Modelin fisyon enerjisinin %%%.1f'i bu çubuklarda "
                          "(%.4g W); kalanı diğer fisil bölgelerde.")
                        % (100.0 * mutlak["hedef_payi"], mutlak["hedef_guc"]))
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
        satirlar.append("En yüksek çizgisel güç %.1f W/cm (tepe faktörü: %s)."
                        % (lm, mutlak["lineer_tepe_kaynagi"]))
        if lm > 500:
            satirlar.append("  Sınırın üstünde: tipik PWR çizgisel güç "
                            "sınırı ~400–500 W/cm.")
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


def yorumla(faktorler, mutlak=None, hedef_payi=None, hedef_payi_hata=None):
    """
    Ogrenciye yonelik kisa yorum satirlari.
    hedef_payi: kappa_hedef / kappa_model (kosucu.sonuc_oku guc["hedef_payi"]);
    verilmezse mutlak["hedef_payi"] kullanilir.
    hedef_payi_hata: pay okunamadiysa hata metni (guc["hedef_payi_hata"]).
    """
    if not faktorler:
        return ["Güç dağılımı hesaplanamadı."]
    if hedef_payi is None and mutlak:
        hedef_payi = mutlak.get("hedef_payi")
    satirlar = (_radyal_satirlari(faktorler) + _kapsam_satiri(hedef_payi)
                + _eksenel_satirlari(faktorler)
                + _mutlak_satirlari(mutlak, hedef_payi_hata))
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

    DONER {"F_dH": [...], "F_q": [...], "ozet": {...}}
    """
    import os
    import statistics as st
    from cekirdek import kosucu

    f_dh, f_q, hatalar = [], [], []
    for i, t in enumerate(tohumlar):
        alt = dict(spec)
        alt["ayarlar"] = dict(spec["ayarlar"], tohum=int(t))
        dizin = os.path.join(kok_dizin, "tohum_%d" % t)
        try:
            kosu = kosucu.calistir(alt, dizin, is_parcacigi=is_parcacigi)
            if not kosu["basarili"]:
                hatalar.append("tohum %d: koşu başarısız" % t)
                continue
            s = kosucu.sonuc_oku(kosu["statepoint"])
            f = (s.get("guc") or {}).get("faktorler")
            if not f:
                hatalar.append("tohum %d: güç dağılımı okunamadı" % t)
                continue
            f_dh.append(f["F_dH"])
            if f["F_q"]:
                f_q.append(f["F_q"])
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
    return {"F_dH": f_dh, "F_q": f_q, "ozet": ozet}


def ozet_metni(faktorler, mutlak=None):
    """Tek satirlik ozet (terminal ve durum cubugu icin)."""
    if not faktorler:
        return "güç dağılımı yok"
    p = ["F_ΔH = %.4f ± %.4f" % (faktorler["F_dH"], faktorler["F_dH_sapma"])]
    if faktorler["F_q"]:
        p.append("F_q = %.4f ± %.4f" % (faktorler["F_q"], faktorler["F_q_sapma"]))
    p.append("en sıcak çubuk: %s" % _g().konum_metni(faktorler["sicak_cubuk"],
                                                 faktorler.get("kafes_turu"),
                                                 faktorler.get("kafes_turleri")))
    if faktorler.get("tam_kor"):
        p.append(_("en sıcak demet: %s (F_demet = %.4f)")
                 % (_g().demet_metni(faktorler["sicak_demet"], faktorler), faktorler["F_demet"]))
    return "  |  ".join(p)
