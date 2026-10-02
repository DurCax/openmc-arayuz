# -*- coding: utf-8 -*-
"""
 test_y4_surdur.py  --  v3 Y4: kaldigi yerden surdurme denetimi
                        (cekirdek/tukenme_surdur.py; Monte Carlo KOSULMAZ)

 Fixture: testler/veri/tukenme_guc_ornek (2 adim: 2 ve 8 gun, tamamlanmis;
 h5'te reaksiyon hizlari YOK -- OpenMC varsayilani write_rates=False).

   [Y4-S1] plan_saniye: d, h, a (Julian yil, OpenMC ile ayni) ve MWd/kg.
   [Y4-S2] Biten kosuya adim eklenince tamam = 2, hiz kaydi yok (taze BOS).
   [Y4-S3] Reddedilenler: adimlar onek degil, fizik farkli, plan zaten bitmis,
           LE/QI + hizsiz dosya, spec kaydi yok.
   [Y4-S4] taze_bos: yeniden baslatmanin ilk adimi kayitli (sifir) hiz yerine
           BOS transport'u kosar (OpenMC 0.16 ic yontemleri hala var).
   [Y4-S5] Eskime: surdur bayragi fizik degildir (sonuc eskimez).
"""

import copy
import json
import os
import shutil

from testler.ortak_test import KOK, kontrol

FIXTURE = os.path.join(KOK, "testler", "veri", "tukenme_guc_ornek")


def _kopya(gecici):
    d = os.path.join(gecici, "fx")
    shutil.copytree(FIXTURE, d)
    with open(os.path.join(d, "tukenme_spec.json"), encoding="utf-8") as f:
        return d, json.load(f)


def _hata(islev):
    try:
        islev()
    except ValueError as e:
        return str(e)
    return None


def test_plan_saniye():
    print("\n[Y4-S1] plan_saniye birimleri")
    from cekirdek import tukenme_surdur as ts
    sn = ts.plan_saniye([(1, "d"), (2, "h"), (1, "a"), (0.04, "MWd/kg")], 40.0)
    kontrol("d, h, a, MWd/kg", sn == [86400.0, 7200.0, 365.25 * 86400.0, 86400.0], repr(sn))


def test_eklenen_adim(gecici):
    print("\n[Y4-S2] biten kosuya adim ekleme: tamam = 2")
    from cekirdek import tukenme_surdur as ts
    d, s = _kopya(gecici)
    s["tukenme"].update(adimlar=[2.0, 8.0, 10.0], surdur=True)
    o = ts.onceki_durum(s, d)
    kontrol("tamam = 2, hiz kaydi yok", o is not None and o.tamam == 2 and not o.hizli,
            repr(o and (o.tamam, o.hizli)))
    kontrol("dizinde sonuc yoksa None", ts.onceki_durum(s, os.path.join(gecici, "bos")) is None)


def test_reddedilenler(gecici):
    print("\n[Y4-S3] uyumsuz surdurme reddedilir")
    from cekirdek import tukenme_surdur as ts
    d, s = _kopya(gecici)
    a = copy.deepcopy(s)
    a["tukenme"]["adimlar"] = [3.0, 8.0, 10.0]
    kontrol("onek degil", "aynı değil" in (_hata(lambda: ts.onceki_durum(a, d)) or ""))
    a = copy.deepcopy(s)
    a["tukenme"].update(adimlar=[2.0, 8.0, 10.0], guc_yogunlugu=30.0)
    kontrol("fizik farkli (guc)", "fiziği" in (_hata(lambda: ts.onceki_durum(a, d)) or ""))
    kontrol("plan bitmis", "adım yok" in (_hata(lambda: ts.onceki_durum(s, d)) or ""))
    a = copy.deepcopy(s)
    a["tukenme"].update(adimlar=[2.0, 8.0, 10.0], entegrator="leqi")
    kayit = copy.deepcopy(a)
    with open(os.path.join(d, "tukenme_spec.json"), "w", encoding="utf-8") as f:
        json.dump(kayit, f)
    kontrol("LE/QI + hizsiz dosya", "LE/QI" in (_hata(lambda: ts.onceki_durum(a, d)) or ""))
    os.remove(os.path.join(d, "tukenme_spec.json"))
    kontrol("spec kaydi yok", "kaydı yok" in (_hata(lambda: ts.onceki_durum(a, d)) or ""))


def test_taze_bos():
    print("\n[Y4-S4] taze_bos: restart ilk adimi BOS transport'u")
    import openmc.deplete as d
    from cekirdek import tukenme_surdur as ts
    kontrol("OpenMC ic yontemleri var",
            hasattr(d.abc.Integrator, "_get_bos_data_from_restart")
            and hasattr(d.abc.Integrator, "_get_bos_data_from_operator"))
    cagri = []

    class Sahte:
        def _get_bos_data_from_operator(self, i, kaynak, n):
            cagri.append((i, kaynak, n))
            return n, "sonuc"
    s = Sahte()
    ts.taze_bos(s)
    sonuc = s._get_bos_data_from_restart(5.0, [1])
    kontrol("operator'den, adim 0", cagri == [(0, 5.0, [1])] and sonuc == ([1], "sonuc"))


def test_surdur_fizik_degil():
    print("\n[Y4-S5] surdur bayragi eskitmez")
    from cekirdek import tukenme
    with open(os.path.join(FIXTURE, "tukenme_spec.json"), encoding="utf-8") as f:
        s = json.load(f)
    a = copy.deepcopy(s)
    a["tukenme"]["surdur"] = True
    kontrol("_fizik_kismi ayni", tukenme._fizik_kismi(s) == tukenme._fizik_kismi(a))


HIZLI = [test_plan_saniye, test_eklenen_adim, test_reddedilenler, test_taze_bos,
         test_surdur_fizik_degil]
