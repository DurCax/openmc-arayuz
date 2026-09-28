# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/kaynak.py  --  5. baslangic / sabit kaynak kontrolleri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

import os

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek import kurucu, veri_bilgi, sema
from cekirdek import kaynak as _kaynak
from cekirdek import uygunluk
from cekirdek.dogrula._ortak import Bulgu
from cekirdek.dogrula.veri import _kutuphane_icerigi


# ============================================================================
# 5. REFERANS TUTARLILIGI
# ============================================================================

def kaynak_kontrol(spec, veri_kontrolu=True):
    """
    Kaynak tanimi: enerji tayfi, acisal dagilim, parcacik turu, siddet.

    Sabit kaynak modunun kendine ozgu tuzaklari var ve hicbiri kosuyu
    durdurmuyor -- sessizce anlamsiz sonuc uretiyorlar:
      * foton kaynagi acik ama foton tasinimi kapali -> hicbir etkilesim yok
      * hicbir tally yok -> kosu hicbir sey uretmez, k-eff de yoktur
      * kaynak enerjisi kutuphane tavaninin ustunde -> kosuda hata
      * nokta kaynak geometrinin disinda -> butun parcaciklar aninda kayip
    """
    bulgular = []
    a = spec["ayarlar"]
    k = a.get("kaynak") or {}
    e = k.get("enerji") or {}
    mod = a.get("mod", "eigenvalue")
    sabit = (mod != "eigenvalue")
    # hangi alan/secenek bu modelde gecerli: uygunluk (arayuzle ayni kural)
    alan = uygunluk.ayar_alanlari(spec)
    secenek = uygunluk.kaynak_secenekleri(spec)

    # --- dagilimlar gercekten kurulabiliyor mu ---
    for ad, fn, arg in (("enerji tayfı", _kaynak.enerji_dagilimi, e),
                        ("açısal dağılım", _kaynak.aci_dagilimi, k.get("aci"))):
        try:
            fn(arg)
        except Exception as hata:
            bulgular.append(Bulgu("hata", "kaynak", "%s kurulamadı: %s" % (ad, hata)))

    # --- siddet ---
    kuvvet = k.get("kuvvet")
    if kuvvet is not None and float(kuvvet) <= 0:
        bulgular.append(Bulgu("hata", "kaynak",
                              "kaynak şiddeti sıfırdan büyük olmalı (%s)" % kuvvet))
    elif (kuvvet is not None and not alan["kaynak_siddeti"]
          and float(kuvvet) != float(sema.VARSAYILAN_AYARLAR["kaynak"]["kuvvet"])):
        bulgular.append(Bulgu(
            "bilgi", "kaynak",
            "özdeğer hesabında kaynak şiddeti (%g) yok sayılır" % float(kuvvet),
            "Özdeğer hesabında sonuçlar fisyon kaynağına normalize edilir; "
            "mutlak ölçek için güç dağılımındaki toplam gücü kullanın."))

    # (kutu kaynagi + fisil malzeme yok: fisil_gereksinim_kontrol)

    # --- parcacik turu ---
    parca = k.get("parcacik") or "neutron"
    if parca not in ("neutron", "photon"):
        bulgular.append(Bulgu("hata", "kaynak",
                              "bilinmeyen parçacık türü: %s" % parca))
    elif parca == "photon":
        if parca not in secenek["parcaciklar"]:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "foton kaynağı Özdeğer (k-eff) hesabında anlamsız",
                "Fotonlar fisyon zincirini taşımaz. Foton kaynağı için hesap "
                "türünü Sabit kaynak yapın."))
        if veri_kontrolu:
            _, _, foton = _kutuphane_icerigi_foton()
            if foton is not None and not foton:
                bulgular.append(Bulgu(
                    "hata", "kaynak",
                    "foton kaynağı seçildi ama kütüphanede foton verisi yok",
                    "cross_sections.xml içinde type='photon' kaydı bulunamadı."))

    # --- enerji tavani ---
    tepe = _kaynak.en_yuksek_enerji(e)
    if tepe is not None and veri_kontrolu and parca == "neutron":
        try:
            nesneler, _, _ = kurucu.malzemeleri_kur(spec)
            nuklidler = set()
            for mat in nesneler.values():
                nuklidler |= set(mat.get_nuclides())
            tavan, sahibi = veri_bilgi.enerji_tavani(sorted(nuklidler))
        except Exception:
            tavan, sahibi = None, None
        if tavan is not None and tepe > tavan:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "kaynak enerjisi %s, veri tavanı %s (%s)"
                % (_kaynak.enerji_metni(tepe), _kaynak.enerji_metni(tavan), sahibi),
                "Tavanı, modeldeki nüklidler içinde en düşük üst sınıra sahip "
                "olan belirler. OpenMC koşu sırasında hata verir."))

    # --- nokta kaynak geometrinin icinde mi ---
    if k.get("tur", "nokta") == "nokta":
        konum = list(k.get("konum") or (0.0, 0.0, 0.0))
        h = sema_kor_yuksekligi(spec["kor"])
        if h and abs(float(konum[2])) >= float(h) / 2.0:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "nokta kaynak z = %g modelin dışında (yükseklik %g, sınır ±%g)"
                % (konum[2], h, h / 2.0),
                "Geometri dışında başlayan parçacıklar anında kaybolur."))

    # --- sabit kaynak moduna ozgu ---
    if sabit:
        if not spec.get("tallyler") and not (spec.get("guc_dagilimi") or {}).get("var"):
            bulgular.append(Bulgu(
                "hata", "ayarlar",
                "sabit kaynak hesabında hiçbir tally tanımlı değil — koşu hiçbir "
                "sonuç üretmez",
                "Sabit kaynak hesabında k-eff yoktur; ne ölçülecekse bir "
                "tally olarak tanımlanmalıdır (akı, doz, reaksiyon hızı)."))
        if (a.get("kinetik") or {}).get("var") and not alan["kinetik"]:
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "kinetik parametreler (β_eff, Λ) yalnızca özdeğer hesabında "
                "bulunur — sabit kaynak hesabında yok sayılır",
                "IFP yöntemi fisyon zincirini nesiller boyunca izler; sabit "
                "kaynak hesabında k-eff ve nesil kavramı yoktur."))
        if (a.get("entropi_mesh") or {}).get("var") and not alan["entropi"]:
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "Shannon entropisi sabit kaynak hesabında kullanılmaz",
                "Entropi fisyon kaynağı dağılımının yakınsamasını ölçer; sabit "
                "kaynakta kaynak zaten sabittir. OpenMC bunu yok sayar."))
        if int(a.get("pasif") or 0) > 0 and not alan["pasif"]:
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "sabit kaynak hesabında pasif çevrim (%d) yok sayılır"
                % int(a.get("pasif") or 0),
                "Pasif çevrim fisyon kaynağının yakınsaması içindir; sabit "
                "kaynak hesabında hiç yazılmaz. Bütün çevrimler sayılır."))
        if k.get("tur") == "kutu" and "kutu" in secenek["turler"]:
            # fisil malzeme yoksa fisil_gereksinim_kontrol HATA verir
            bulgular.append(Bulgu(
                "uyari", "kaynak",
                "sabit kaynak hesabında kutu kaynağı 'yalnızca fisil bölgeler' "
                "kısıtıyla örneklenir",
                "Kaynak parçacıkları yalnızca fisil malzemede başlar; kutunun "
                "geri kalanı boş kalır. Dış bir kaynak modelliyorsanız nokta "
                "kaynak kullanın."))
    else:
        tur = e.get("tur", "watt")
        if tur != "watt":
            bulgular.append(Bulgu(
                "bilgi", "kaynak",
                "özdeğer hesabında enerji tayfı (%s) yalnızca başlangıç tahminidir"
                % dict(_kaynak.TAYFLAR).get(tur, tur),
                "Pasif çevrimler içinde gerçek fisyon tayfıyla değişir; k-eff'i "
                "etkilemez. Tayf asıl sabit kaynak hesabında belirleyicidir."))
        if (k.get("aci") or {}).get("tur", "izotropik") != "izotropik":
            bulgular.append(Bulgu(
                "bilgi", "kaynak",
                "özdeğer hesabında açısal dağılım da yalnızca başlangıç tahminidir"))

    return bulgular


def _kutuphane_icerigi_foton():
    """(notron, termal, foton) ad kumeleri; okunamazsa (None, None, None)."""
    notron, termal = _kutuphane_icerigi()
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol or not os.path.exists(yol):
        return notron, termal, None
    try:
        import xml.etree.ElementTree as ET
        kok = ET.parse(yol).getroot()
        foton = {d.get("materials") for d in kok.findall("library")
                 if d.get("type") == "photon"}
        return notron, termal, foton
    except Exception:
        return notron, termal, None
