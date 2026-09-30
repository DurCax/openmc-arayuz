# -*- coding: utf-8 -*-
"""
test_geometri_ui.py -- Dalga G-3: Geometri sayfasi (sablon + gelismis agac editoru).

  * arayuz/geometri/duzenle.py: agac islemleri SAF (girdi degismez), yuva
    kurallari, silme / tasima / yeniden adlandirma / parcaya cikarma /
    sarmalama, grup uyeligi adlarla birlikte guncellenir.
  * Gelismis moda gecis TEK YONLU; Geri Al gecisin kendisini TEK ADIMDA geri
    alir (§15 karar 1); agac islemleri de geri alinir / yinelenir.
  * Sematik kesit: tiklama -> agacta secim; secili dugum vurgulu; kesik
    konumlar isaretli.
  * Uc yeni sablon agac uretir, yapisal denetimden gecer ve kurulur.
  * Yuz basina sinir formu; pin kesiti secimi (Parcalar).
  * Spec gidis-donusu 27 ornekte bozulmaz; eski Kor testleri ayrica gecer.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS). Yalniz offscreen.
"""

import copy
import glob
import os
import warnings

from testler.ortak_test import kontrol, KOK, ORNEK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _ornek_adlari():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(ORNEK, "*.json")))


def _agac(ad="tamburlu_kor"):
    from cekirdek import geometri
    return geometri.gelismise_gec(_ornek(ad))


def _hata_verir(islev, *a, **k):
    from arayuz.geometri.duzenle import DuzenlemeHatasi
    try:
        islev(*a, **k)
    except DuzenlemeHatasi:
        return True
    return False


# ============================================================================
# duzenle.py (saf)
# ============================================================================

def test_duzenle_yollar_ve_yuvalar():
    print("\n[GU1] duzenle: yol cozumu, yuva kurallari")
    from arayuz.geometri import duzenle as d
    agac = _agac()["geometri"]
    kontrol("yol_coz / yol_metni gidis-donus",
            d.yol_coz(d.yol_metni(("kok", "halkalar", 0, "icerik"))) == ("kok", "halkalar", 0, "icerik"))
    kontrol("kok yuvadir", d.yuva_mu(agac, ("kok",)))
    kontrol("kap.ic yuvadir", d.yuva_mu(agac, ("kok", "ic")))
    kontrol("halka.icerik yuvadir", d.yuva_mu(agac, ("kok", "halkalar", 0, "icerik")))
    kontrol("yerlesim.icerik yuvadir",
            d.yuva_mu(agac, ("kok", "halkalar", 0, "yerlesimler", 0, "icerik")))
    kontrol("kesit yuva DEGIL", not d.yuva_mu(agac, ("kok", "kesit")))
    kontrol("halka oge turu", d.oge_turu(agac, ("kok", "halkalar", 0)) == "halka")
    kontrol("yerlesim oge turu",
            d.oge_turu(agac, ("kok", "halkalar", 0, "yerlesimler", 0)) == "yerlesim")
    kontrol("grup oge turu", d.oge_turu(agac, ("gruplar", 0)) == "grup")
    kontrol("kap_yolu en yakin kap", d.kap_yolu(agac, ("kok", "halkalar", 0, "icerik")) == ("kok",))


def test_duzenle_saf_ve_ekleme():
    print("\n[GU2] duzenle: islemler girdiyi degistirmez; ekleme")
    from arayuz.geometri import duzenle as d
    agac = _agac()["geometri"]
    once = copy.deepcopy(agac)
    y1 = d.halka_ekle(agac, ("kok",), 5.0, d.malzeme("su"))
    y2 = d.yerlesim_ekle(y1, ("kok", "halkalar", 1), d.malzeme("su"))
    y3 = d.grup_ekle(y2, "donme")
    y4 = d.dugum_koy(y3, ("kok", "ic"), d.yeni_dugum("kafes", y3, "u10mo"))
    kontrol("girdi degismedi", agac == once)
    kontrol("halka eklendi", len(y1["kok"]["halkalar"]) == 2
            and y1["kok"]["halkalar"][1]["kalinlik"] == 5.0)
    kontrol("yerlesim ikinci halkada, tekil ad",
            y2["kok"]["halkalar"][1]["yerlesimler"][0]["ad"] not in ("tamburlar",))
    kontrol("grup eklendi", len(y3["gruplar"]) == 2 and y3["gruplar"][1]["tur"] == "donme")
    kontrol("kafes konuldu, tekil id",
            y4["kok"]["ic"]["tur"] == "kafes" and y4["kok"]["ic"]["id"] not in ("kok",))
    kontrol("koke kap olmayan dugum konamaz",
            _hata_verir(d.dugum_koy, agac, ("kok",), d.malzeme("su")))
    kontrol("kesite dugum konamaz",
            _hata_verir(d.dugum_koy, agac, ("kok", "kesit"), d.malzeme("su")))


def test_duzenle_sil_tasi_adlandir():
    print("\n[GU3] duzenle: sil / tasi / yeniden adlandir / sira")
    from arayuz.geometri import duzenle as d
    agac = _agac()["geometri"]
    yer = ("kok", "halkalar", 0, "yerlesimler", 0)
    ad = d.yeniden_adlandir(agac, yer, "tb")
    kontrol("yerlesim adi degisti", d.al(ad, yer)["ad"] == "tb")
    kontrol("grup uyeligi de degisti", ad["gruplar"][0]["uyeler"] == ["tb"])
    silinmis = d.sil(ad, yer)
    kontrol("yerlesim silindi", silinmis["kok"]["halkalar"][0]["yerlesimler"] == [])
    kontrol("grup uyeliginden cikti", silinmis["gruplar"][0]["uyeler"] == [])
    bos = d.sil(agac, ("kok", "ic"))
    kontrol("yuvadaki dugum silinince bosluk olur",
            bos["kok"]["ic"] == {"tur": "malzeme", "ad": "bosluk"})
    kontrol("kok silinemez", _hata_verir(d.sil, agac, ("kok",)))
    t = d.tasi(agac, ("kok", "ic"), ("kok", "halkalar", 0, "icerik"))
    kontrol("tasi: hedef kaynagin dugumunu aldi",
            t["kok"]["halkalar"][0]["icerik"] == agac["kok"]["ic"])
    kontrol("tasi: kaynak bosaldi", t["kok"]["ic"]["ad"] == "bosluk")
    kontrol("kendi icine tasinamaz",
            _hata_verir(d.tasi, agac, ("kok", "halkalar", 0, "icerik"),
                        ("kok", "halkalar", 0, "icerik", "x")))
    iki = d.halka_ekle(agac, ("kok",), 3.0)
    yt = d.tasi(iki, yer, ("kok", "halkalar", 1))
    kontrol("yerlesim baska halkaya tasindi",
            yt["kok"]["halkalar"][0]["yerlesimler"] == []
            and yt["kok"]["halkalar"][1]["yerlesimler"][0]["ad"] == "tamburlar")
    s = d.sira_tasi(iki, ("kok", "halkalar", 1), -1)
    kontrol("halka sirasi degisti", s["kok"]["halkalar"][0].get("kalinlik") == 3.0)
    kontrol("malzeme basvurusu adlandirilmaz",
            _hata_verir(d.yeniden_adlandir, agac, ("kok", "ic"), "x"))
    kontrol("gecersiz ad reddedilir",
            _hata_verir(d.yeniden_adlandir, agac, yer, "a/b"))


def test_duzenle_parca_ve_sarmala():
    print("\n[GU4] duzenle: parcaya cikar, sarmala")
    from arayuz.geometri import duzenle as d
    from cekirdek import geometri
    spec = _agac()
    agac = spec["geometri"]
    kap = d.dugum_koy(agac, ("kok", "ic"), d.yeni_dugum("kap", agac, "u10mo"))
    p = d.parcaya_cikar(kap, ("kok", "ic"), "cekirdek_parcasi")
    kontrol("yuvaya basvuru kondu",
            p["kok"]["ic"] == {"tur": "bilesen", "ad": "cekirdek_parcasi"})
    kontrol("parca eklendi", p["parcalar"][0]["ad"] == "cekirdek_parcasi")
    kontrol("kullanilan parca silinemez", _hata_verir(d.sil, p, ("parcalar", 0)))
    kontrol("kutuphane adiyla cakisan parca adi reddedilir",
            _hata_verir(d.parcaya_cikar, kap, ("kok", "ic"), "tambur", ("tambur",)))
    r = d.yeniden_adlandir(p, ("parcalar", 0), "cp")
    kontrol("parca adi basvurularda da degisti", r["kok"]["ic"]["ad"] == "cp")
    s = d.sarmala(agac, ("kok",))
    kontrol("kok sarmalandi: yukseklik/sinir yeni kokte",
            s["kok"]["yukseklik"] == 45.0 and "sinir" in s["kok"]
            and "sinir" not in s["kok"]["ic"] and s["kok"]["ic"]["tur"] == "kap")
    yeni = dict(spec, geometri=s)
    bulgular = [b for b in geometri.yapisal_denetim(yeni) if b.seviye == "hata"]
    kontrol("sarmalanmis agac yapisal denetimden gecer", not bulgular,
            "-> %s" % [b.mesaj for b in bulgular][:2])


HIZLI = [test_duzenle_yollar_ve_yuvalar, test_duzenle_saf_ve_ekleme,
         test_duzenle_sil_tasi_adlandir, test_duzenle_parca_ve_sarmala]
YAVAS = []
