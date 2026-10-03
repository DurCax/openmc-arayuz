# -*- coding: utf-8 -*-
"""
 test_y4_bor.py  --  v3 Y4: bor aramasi islevinin yan etkisizligi (MC yok)

   [Y4-R1] Tarif kurulumda BIR KEZ cozulur: arama sirasinda (ayarla) kurucu
           cagrilmaz ve yeni openmc.Material olusmaz (otomatik kimlik sayaci
           degismez); set_densities dogrusal tabloyla cagrilir ve tam tarife
           esittir (fark / toplam < 1e-9, ppm > 0).
   [Y4-R2] Hedef su tukenebilir (ek_malzemeler) ise denetim HATA verir: arama
           set_densities ile tukenmis bilesimi ezerdi.
"""

import copy
import os

from testler.ortak_test import ORNEK, kontrol


def _spec():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["tukenme"]["var"] = True
    return s


class _SahteLib:
    def __init__(self):
        self.cagri = []

    def set_densities(self, nuklidler, yogunluklar):
        self.cagri.append(dict(zip(nuklidler, yogunluklar)))


def test_tarif_bir_kez(monkeypatch):
    print("\n[Y4-R1] bor tarifi bir kez cozulur; aramada yan etki yok")
    import openmc
    import openmc.lib
    from cekirdek import kurucu, tukenme_arama
    s = _spec()
    model, bilgi = kurucu.kur(s)
    ayarla = tukenme_arama.bor_islevi(bilgi["malzemeler"], s, "su", 1500.0)
    sahte = _SahteLib()
    mid = bilgi["malzemeler"]["su"].id
    monkeypatch.setattr(openmc.lib, "materials", {mid: sahte})
    monkeypatch.setattr(kurucu, "malzemeleri_kur",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("kurucu cagrildi")))
    once = openmc.Material.next_id
    for ppm in (700.0, 2500.0):
        ayarla(ppm)
    kontrol("aramada yeni Material yok", openmc.Material.next_id == once)
    monkeypatch.undo()
    for ppm, y in zip((700.0, 2500.0), sahte.cagri):
        tam = tukenme_arama.bor_yogunluklari(s, "su", ppm)
        fark = max(abs(y.get(n, 0.0) - v) for n, v in tam.items()) / sum(tam.values())
        kontrol("%g ppm: fark / toplam %.1e" % (ppm, fark), fark < 1e-9)


def test_tukenen_su_reddedilir():
    print("\n[Y4-R2] tukenebilir hedef suya bor aramasi HATA")
    from cekirdek import tukenme_ayar
    s = _spec()
    s["tukenme"]["kritik_arama"] = {"var": True, "tur": "bor", "hedef": "su",
                                    "alt": 500.0, "ust": 1500.0, "sinir": [0.0, 3000.0]}
    kontrol("tukenmeyen su: hata yok",
            not [b for b in tukenme_ayar.ayar_bulgulari(s) if b.seviye == "hata"])
    a = copy.deepcopy(s)
    a["tukenme"]["ek_malzemeler"] = ["su"]
    hatalar = [b.mesaj for b in tukenme_ayar.ayar_bulgulari(a) if b.seviye == "hata"]
    kontrol("tukenen su: hata", any("tüken" in m for m in hatalar), repr(hatalar))


HIZLI = [test_tarif_bir_kez, test_tukenen_su_reddedilir]
VERI_GEREKEN = [test_tarif_bir_kez]
