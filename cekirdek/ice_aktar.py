# -*- coding: utf-8 -*-
"""
================================================================================
 ice_aktar.py  --  Mevcut OpenMC girdilerinden spec'e aktarma
================================================================================

 NE AKTARILABILIR, NE AKTARILAMAZ

   MALZEMELER  -> aktarilabilir. materials.xml (ya da model.xml) icindeki her
                  malzeme, bilesimi/yogunlugu/sicakligi/S(a,b) ile birlikte
                  spec bicimine birebir cevrilebilir.

   GEOMETRI    -> AKTARILAMAZ. Arayuz "rehberli kor kurucusu"dur; cubuk,
                  kafes ve kor kavramlari uzerinden calisir. Keyfi bir CSG
                  agacini (yuzey + hucre + universe) bu kavramlara geri
                  cevirmek genel olarak cozulebilir bir problem degildir --
                  ayni geometri sonsuz farkli sekilde kurulmus olabilir.
                  Bu yuzden denenmiyor; yanlis bir "tahmin" sessizce yanlis
                  model uretmekten iyidir.

   PYTHON BETIGI -> AKTARILAMAZ. Keyfi Python cozumlenemez.

 Pratikte en cok ise yarayan yol malzemeleri aktarip geometriyi arayuzde
 yeniden kurmaktir; malzeme tanimlari bir modelin en zahmetli ve en cok hata
 barindiran kismidir.

 KULLANIM
   from cekirdek import ice_aktar
   malzemeler, notlar = ice_aktar.malzemeleri_oku("materials.xml")
   spec["malzemeler"].extend(malzemeler)
================================================================================
"""

import os
import re

from cekirdek.sema import malzeme, bilesen

# Aktarilan malzemelere dondurulecek renk paleti
_RENKLER = [(222, 93, 40), (90, 150, 220), (150, 150, 160), (120, 200, 140),
            (200, 170, 90), (170, 120, 200), (90, 190, 190), (210, 130, 160)]


def _ad_uret(mat, sira, mevcut):
    """
    OpenMC malzeme adindan gecerli, benzersiz bir spec adi uretir.
    Ad yoksa malzeme id'si kullanilir.
    """
    ham = (mat.name or "").strip() or ("malzeme_%d" % mat.id)
    temiz = re.sub(r"[^0-9a-zA-Z_]+", "_", ham).strip("_").lower()
    if not temiz or temiz[0].isdigit():
        temiz = "m_" + temiz
    ad, i = temiz, 2
    while ad in mevcut:
        ad = "%s_%d" % (temiz, i)
        i += 1
    return ad


def malzemeleri_oku(yol):
    """
    materials.xml / model.xml icindeki malzemeleri spec bicimine cevirir.

    DONER (malzeme_listesi, notlar)
      notlar : aktarim sirasinda dikkat cekilmesi gereken durumlar (liste)
    """
    import openmc

    if not os.path.exists(yol):
        raise IOError("dosya bulunamadı: %s" % yol)

    notlar = []
    taban = os.path.basename(yol).lower()
    if taban == "model.xml" or taban.endswith("model.xml"):
        model = openmc.Model.from_model_xml(yol)
        ham_malzemeler = list(model.materials)
    else:
        ham_malzemeler = list(openmc.Materials.from_xml(yol))

    sonuc = []
    adlar = set()
    for sira, mat in enumerate(ham_malzemeler):
        ad = _ad_uret(mat, sira, adlar)
        adlar.add(ad)

        # --- bilesim ---
        bilesim = []
        try:
            nuklidler = mat.get_nuclide_atom_densities()
        except Exception:
            nuklidler = None

        if nuklidler:
            # Atom yogunluklarindan atom oranina cevir
            toplam = sum(nuklidler.values())
            for nuklid, yog in sorted(nuklidler.items()):
                if toplam > 0:
                    bilesim.append(bilesen(nuklid, yog / toplam, tur="nuklid"))
        else:
            notlar.append("%s: bileşim okunamadı, boş bırakıldı" % ad)

        # --- yogunluk ---
        birim, deger = "g/cm3", None
        try:
            if mat.density is not None:
                birim = mat.density_units if mat.density_units != "sum" else "atom/b-cm"
                deger = float(mat.density)
        except Exception:
            pass
        if deger is None:
            try:
                deger = float(mat.get_mass_density())
                birim = "g/cm3"
                notlar.append("%s: yoğunluk 'sum' olarak verilmiş, kütle "
                              "yoğunluğuna çevrildi (%.4f g/cm³)" % (ad, deger))
            except Exception:
                deger = 1.0
                notlar.append("%s: yoğunluk belirlenemedi, 1.0 g/cm³ varsayıldı "
                              "— mutlaka düzeltin" % ad)

        # --- sicaklik ---
        sicaklik = 293.6
        try:
            if mat.temperature:
                sicaklik = float(mat.temperature)
        except Exception:
            pass

        # --- S(a,b) ---
        # S(a,b) kayitlari (ad, kesir) demeti olarak tutulur; sadece adi aliriz.
        # Kesir 1.0 disindaysa kullaniciya bildirilir -- spec tek ad tasir.
        sab = []
        try:
            for kayit in (mat._sab or []):
                if isinstance(kayit, (tuple, list)):
                    sab.append(str(kayit[0]))
                    if len(kayit) > 1 and abs(float(kayit[1]) - 1.0) > 1e-9:
                        notlar.append("%s: S(α,β) '%s' kesri %.3f — model dosyası "
                                      "yalnızca adı taşır, kesir kayboldu"
                                      % (ad, kayit[0], float(kayit[1])))
                elif isinstance(kayit, dict):
                    sab.append(str(kayit.get("name", "")))
                else:
                    sab.append(str(kayit))
            sab = [s for s in sab if s]
        except Exception as e:
            notlar.append("%s: S(α,β) okunamadı (%s)" % (ad, e))

        sonuc.append(malzeme(
            ad, bilesim, deger, birim=birim, sicaklik=sicaklik, sab=sab,
            renk=_RENKLER[sira % len(_RENKLER)],
            gorunen_ad=(mat.name or ad)))

    if sonuc:
        notlar.insert(0, "%d malzeme aktarıldı. Bileşimler nüklid bazında "
                         "aktarılır (element kısayolları korunmaz); sonuç aynı "
                         "olsa da tablo daha uzun görünür." % len(sonuc))
    return sonuc, notlar


def geometri_neden_aktarilamaz():
    """Arayuzde gosterilecek aciklama."""
    return (
        "Geometri içe aktarılamaz.\n\n"
        "Bu arayüz rehberli bir kor kurucusudur: malzeme → çubuk → demet → "
        "kor katmanları üzerinden çalışır. OpenMC XML'i ise ham CSG'dir "
        "(yüzeyler, hücreler, universe'ler). Aynı geometri sonsuz farklı "
        "şekilde kurulmuş olabileceği için ham CSG'yi bu katmanlara geri "
        "çevirmek genel olarak çözülebilir bir problem değildir.\n\n"
        "Yanlış bir tahmin, sessizce yanlış bir model üretirdi; bu yüzden "
        "denenmiyor.\n\n"
        "Pratik yol: malzemeleri buradan aktarın, geometriyi arayüzde yeniden "
        "kurun. Malzemeler bir modelin en zahmetli kısmıdır.")
