# -*- coding: utf-8 -*-
"""
 test_kapanis_fizik.py  --  D1-Kapanis C (profesor denetimi) M-1, M-3, L-1,
                            L-2, L-3, L-5

 M-1 Eksenel mesh HEDEF cubugun araligini kapsar; hedef cubuk kesintili
     katmanlardaysa (arada cubuksuz katman) bir dilim sinirinin katman
     sinirina denk gelmemesi KISMEN BOS dilim uretir: o dilimin ortalamasi
     duser, dolu dilimlerin orani, dolayisiyla F_q, birkac % siser. Dogrulama
     uyarmali; hizali dilim sayisinda uyarmamali.
 L-3 Diger fisil cubuk turu yalniz AYRI eksenel katmanda (ayni cubugun uc
     parcasi, ornek blanket) ise F_dH'nin "kapsami" radyal olarak eksik
     degildir: uyari yerine bilgi.
 M-3, L-1, L-2, L-5: belge / metin cumleleri.

 HIZLI: nukleer veri yok.
"""

import copy
import os

from testler.ortak_test import kontrol, ORNEK


def _kesintili(dilim):
    """pwr_eksenel: aktif yakit 100 + 50 (su, cubuksuz) + 150 cm."""
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    bolgeler = s["kor"]["eksenel"]["bolgeler"]
    i = next(j for j, b in enumerate(bolgeler) if b.get("dolgu") is None)
    aktif = bolgeler[i]
    alt, ara, ust = (copy.deepcopy(aktif) for _ in range(3))
    alt.update(ad="aktif alt", yukseklik=100.0)
    ara.update(ad="ara", yukseklik=50.0, dolgu="su")
    ara.pop("anahtar", None)
    ust.update(ad="aktif üst", yukseklik=150.0)
    bolgeler[i:i + 1] = [alt, ara, ust]
    s["guc_dagilimi"]["eksenel_dilim"] = dilim
    return s


def _hiza_bulgulari(spec):
    from cekirdek.dogrula import referans
    return [b for b in referans.guc_dagilimi_kontrol(spec) if "hizalı değil" in b.mesaj]


def test_dilim_katman_hizasi():
    print("\n[KF1] M-1: kesintili katmanda dilim siniri katman sinirina denk gelmiyor -> uyari")
    from cekirdek import kurucu
    s = _kesintili(20)                   # dz = 300/20 = 15 cm; 100/15 tamsayi degil
    kontrol("mesh araligi 300 cm", abs(-(lambda a: a[0] - a[1])(
        kurucu.cubuk_eksenel_aralik(s, "yakit_cubugu")) - 300.0) < 1e-9)
    b = _hiza_bulgulari(s)
    kontrol("20 dilim: uyari", len(b) == 1 and b[0].seviye == "uyari", "-> %r" % [str(x) for x in b])
    kontrol("metin F_q ve 'dilim sayısını' onerisi",
            bool(b) and "F_q" in b[0].mesaj and "dilim sayısını" in (b[0].mesaj + (b[0].oneri or "")))
    kontrol("6 dilim (dz = 50 cm, hizali): uyari yok", not _hiza_bulgulari(_kesintili(6)))
    from cekirdek import sema
    duz = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    kontrol("kesintisiz pwr_eksenel (20 dilim): uyari yok", not _hiza_bulgulari(duz))
    kontrol("tek dilim: uyari yok", not _hiza_bulgulari(_kesintili(1)))


def test_cok_tur_ayri_katman_bilgi():
    print("\n[KF2] L-3: diger fisil tur yalniz ayri eksenel katmanda -> bilgi")
    from cekirdek import sema
    from cekirdek.dogrula import referans
    s = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    b = [x for x in referans.guc_dagilimi_kontrol(s) if "blanket_cubugu" in x.mesaj]
    kontrol("pwr_eksenel: blanket yalniz ortu katmaninda -> tek bulgu, bilgi",
            len(b) == 1 and b[0].seviye == "bilgi", "-> %r" % [str(x) for x in b])
    kontrol("metin eksenel katmani soyler", bool(b) and "eksenel" in b[0].mesaj)
    # ayni katmanda (radyal) ikinci tur -> yine uyari
    s2 = copy.deepcopy(s)
    d = sema.demet_bul(s2, "demet_17x17")
    d["anahtar"]["b"] = "blanket_cubugu"
    d["harita"][0] = "b" + d["harita"][0][1:]
    b2 = [x for x in referans.guc_dagilimi_kontrol(s2) if "blanket_cubugu" in x.mesaj]
    kontrol("ayni katmanda da varsa uyari", any(x.seviye == "uyari" for x in b2),
            "-> %r" % [str(x) for x in b2])


def test_belge_cumleleri():
    print("\n[KF3] M-3, L-1, L-2: guc belgesi ve mutlak guc notu")
    from cekirdek import guc
    from testler.test_guc_kor import _kare_2x2_sentetik
    belge = " ".join((guc.__doc__ or "").split())
    kontrol("M-3: tohum sacilmasi yalniz rastgele kismi olcer",
            "tohum saçılması yalnız rastgele kısmı ölçer" in belge.lower()
            and "aynı yöne yanlı" in belge)
    kontrol("L-2: F_demet belgesi 'demet gücü oranı değil'",
            "demet gücü oranı değil" in " ".join((guc.tepe_faktorleri.__doc__ or "").split()))
    f = guc.tepe_faktorleri(guc.dagilim_oku(_kare_2x2_sentetik()))
    m = guc.mutlak_guc(f, 1.6e6, 100.0, hedef_payi=0.5)
    y = " ".join(guc.yorumla(f, m))
    kontrol("L-1: mutlak guc notu gama isinmasinin yakit disi kismi (~%2-3)",
            "gama" in y and "2–3" in y, y[-500:])


def test_hacimsiz_zehir_yonu():
    print("\n[KF4] L-5: hacimsiz zehir metni etkinin yonunu soyler")
    from cekirdek import tukenme
    from cekirdek.dogrula import tukenme as dt
    eski = tukenme.hacimsiz_zehirler
    tukenme.hacimsiz_zehirler = lambda spec: {"b4c": "kor yansıtıcısı"}
    try:
        b = dt._hacimsiz_zehir_bulgulari({})
    finally:
        tukenme.hacimsiz_zehirler = eski
    metin = " ".join(x.mesaj + " " + (x.oneri or "") for x in b)
    kontrol("kontrol degeri buyuk / iyimser", "olduğundan büyük" in metin and "iyimser" in metin,
            metin)


HIZLI = [test_dilim_katman_hizasi, test_cok_tur_ayri_katman_bilgi, test_belge_cumleleri,
         test_hacimsiz_zehir_yonu]
YAVAS = []
