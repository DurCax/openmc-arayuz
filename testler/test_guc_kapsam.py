# -*- coding: utf-8 -*-
"""
 test_guc_kapsam.py  --  Guc haritasinin kapsami ve belirsizlik notlari
                         (D1-A bulgu 2a ve 6)

 * Guc tally'si TEK cubuk tanimina baglidir (cok turlu tally Dalga 2'de). Ayni
   modelde baska bir fisil cubuk turu varsa F_dH yalniz hedef cubugu kapsar;
   dogrulama bunu soylemeli, tek turlu modelde SOYLEMEMELI. Yorum, mutlak guc
   payi (kappa_hedef / kappa_model) 1'den kucukse bunu yazar.
 * F_q: hedef cubuk kesintili katmanlardaysa (1. ve 3. katmanda var, 2.'de
   yok) o dilimlerde tally SIFIRDIR; ortalamaya girerse F_q yapay siser.
 * Belirsizlik notu: "20 kat" farkin buyuk kismi yakinsamamis kaynaktan;
   Shannon entropisi, daha fazla pasif cevrim ve >= 5 tohum onerilir;
   coklu_tohum varsayilani 5 tohum.

 HIZLI: nukleer veri yok (veri_kontrolu=False), Monte Carlo yok.
"""

import copy
import inspect
import os

from testler.ortak_test import kontrol, ORNEK


def _spec(ikinci_tur):
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    s["guc_dagilimi"].update(var=True, cubuk="yakit_cubugu", bolge=0, eksenel_dilim=20)
    if ikinci_tur:
        c = copy.deepcopy(sema.cubuk_bul(s, "yakit_cubugu"))
        c["ad"] = "gd_cubugu"
        s["cubuklar"].append(c)
        d = sema.demet_bul(s, "demet_17x17")
        d["anahtar"]["g"] = "gd_cubugu"
        d["harita"][0] = "g" + d["harita"][0][1:]
    return s


def _mesajlar(spec):
    from cekirdek.dogrula import referans
    return [(b.seviye, b.mesaj) for b in referans.guc_dagilimi_kontrol(spec)]


def test_cok_turlu_cubuk_uyarisi():
    print("\n[GP1] Dogrulama: ayni modelde baska fisil cubuk turu -> uyari")
    b = _mesajlar(_spec(True))
    uyari = [m for sv, m in b if sv == "uyari" and "gd_cubugu" in m]
    kontrol("uyari: F_dH yalniz yakit_cubugu'nu kapsar",
            bool(uyari) and "yakit_cubugu" in uyari[0] and "F_ΔH" in uyari[0], "-> %r" % b)
    b = _mesajlar(_spec(False))
    kontrol("tek turlu modelde uyari yok", not any("kapsar" in m for _sv, m in b), "-> %r" % b)


def test_yorum_hedef_payi_notu():
    print("\n[GP2] Yorum: hedef payi < 1 ise kapsam notu")
    from cekirdek import guc
    from testler.test_guc_kor import _kare_2x2_sentetik
    f = guc.tepe_faktorleri(guc.dagilim_oku(_kare_2x2_sentetik()))
    y = " ".join(guc.yorumla(f, hedef_payi=0.8))
    kontrol("pay 0.8: 'yalnız' ve %%80 notu", "yalnız" in y and "80.0" in y, y[-400:])
    y1 = " ".join(guc.yorumla(f, hedef_payi=1.0))
    y0 = " ".join(guc.yorumla(f))
    kontrol("pay 1.0 ya da yok: kapsam notu yok",
            "kapsar" not in y1 and "kapsar" not in y0)


def _eksenel_dagilim(degerler):
    """degerler: {anahtar: [dilim degerleri]} -> tepe_faktorleri girdisi."""
    konumlar = {a: {"eksenel": [(v, 0.01) for v in d],
                    "toplam": (sum(d), 0.01)} for a, d in degerler.items()}
    return {"konumlar": konumlar, "eksenel_dilim": len(next(iter(degerler.values()))),
            "kafes_turu": "kare", "tam_kor": False}


def test_fq_bos_dilim_dislanir():
    print("\n[GP3] F_q: hedef cubugun olmadigi (bos) dilim ortalamaya girmez")
    from cekirdek import guc
    d = _eksenel_dagilim({(0, 0): [1.0, 0.0, 3.0], (1, 0): [2.0, 0.0, 2.0]})
    f = guc.tepe_faktorleri(d)
    beklenen = 3.0 / ((1.0 + 3.0 + 2.0 + 2.0) / 4.0)
    kontrol("F_q = maks / ortalama (dolu dilimler)", abs(f["F_q"] - beklenen) < 1e-12,
            "-> %.6f (beklenen %.6f; eski %.6f)" % (f["F_q"], beklenen, 3.0 / (8.0 / 6.0)))
    kontrol("bos dilim listesi [1]", f.get("bos_dilimler") == [1], "-> %r" % f.get("bos_dilimler"))
    kontrol("eksenel profil: bos dilim 0, dolu dilimlerin ortalamasi 1",
            f["eksenel_profil"][1][0] == 0.0
            and abs((f["eksenel_profil"][0][0] + f["eksenel_profil"][2][0]) / 2 - 1.0) < 1e-12)
    kontrol("yorum bos dilimi soyler", any("boş" in s for s in guc.yorumla(f)))
    d2 = _eksenel_dagilim({(0, 0): [1.0, 2.0, 3.0], (1, 0): [2.0, 1.0, 2.0]})
    f2 = guc.tepe_faktorleri(d2)
    kontrol("bos dilim yoksa eskisiyle ayni",
            abs(f2["F_q"] - 3.0 / (11.0 / 6.0)) < 1e-12 and f2.get("bos_dilimler") == [])


def test_belirsizlik_notu_ve_tohum():
    print("\n[GP4] Belirsizlik notu: entropi + pasif cevrim + >= 5 tohum; coklu_tohum 5")
    from cekirdek import guc
    from testler.test_guc_kor import _kare_2x2_sentetik
    f = guc.tepe_faktorleri(guc.dagilim_oku(_kare_2x2_sentetik()))
    y = " ".join(guc.yorumla(f))
    kontrol("not: Shannon entropisi, pasif cevrim, 5-10 tohum",
            "Shannon" in y and "pasif" in y and "5" in y, y[-500:])
    varsayilan = inspect.signature(guc.coklu_tohum).parameters["tohumlar"].default
    kontrol("coklu_tohum varsayilani 5 tohum", len(varsayilan) == 5, "-> %r" % (varsayilan,))
    kontrol("modul notu yakinsamayi soyler", "yakınsa" in (guc.__doc__ or "").lower()
            or "yakinsa" in (guc.__doc__ or "").lower())


HIZLI = [test_cok_turlu_cubuk_uyarisi, test_yorum_hedef_payi_notu,
         test_fq_bos_dilim_dislanir, test_belirsizlik_notu_ve_tohum]
YAVAS = []
