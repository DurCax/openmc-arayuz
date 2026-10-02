# -*- coding: utf-8 -*-
"""
 test_h1b_arka_yoklama.py  --  v3 H1b: nokta yoklamasi ayri surecte (arayuz)

 yoklama.arka_planda(bildir) blogunda yokla() sonucu hazir degilse isi tek
 iscili spawn surecine verir ve None doner; agac_kontrol bunu "arka planda
 suruyor" BILGI'si olarak yazar. Sonuc gelince bildir() cagrilir ve ayni
 icerikte yokla() esli yolla AYNI sonucu (nokta + hucre kimligi + metin) verir.
 Kosu kapisi (dogrula.kapi) blok disinda: esli, eksiksiz.
"""

import os
import threading

from testler.ortak_test import kontrol, ORNEK

_BEKLEME = 120.0               # s: isci sureci (spawn + openmc ice aktarma) + yoklama


def _ozet(sonuc, metinler):
    def liste(x):
        return [(tuple(p), [h.id for h in hucreler]) for p, hucreler in x]
    return sonuc.n, liste(sonuc.bosluklar), liste(sonuc.ortusmeler), list(metinler)


def _arka_planda_bekle(islev):
    """islev() blokta calisir; sonuc gelene kadar bekler, sonra ikinci cagri."""
    from cekirdek.geometri import yoklama
    geldi = threading.Event()
    with yoklama.arka_planda(geldi.set):
        ilk = islev()
    tamam = geldi.wait(_BEKLEME)
    with yoklama.arka_planda(geldi.set):
        ikinci = islev()
    return ilk, tamam, ikinci


def test_arka_plan_sonucu_esli_ile_ayni():
    print("\n[H1b-A1] arka planda yokla: once None, sonra esli yolla birebir ayni")
    from cekirdek import uygunluk_bellek
    from cekirdek.geometri import yoklama, yoklama_arka
    from testler.test_geometri_dogrulama import ortusen_model
    spec = ortusen_model()
    uygunluk_bellek.temizle()
    yoklama_arka.temizle()
    ilk, tamam, ikinci = _arka_planda_bekle(lambda: yoklama.yokla(spec, n=1500, tohum=3))
    kontrol("ilk cagri None (is surecte)", ilk is None)
    kontrol("bildirim geldi", tamam)
    esli = yoklama.yokla(spec, n=1500, tohum=3)
    kontrol("arka plan sonucu esli ile ayni (nokta, hucre kimligi, metin)",
            ikinci is not None and _ozet(*ikinci) == _ozet(*esli))
    kontrol("ortusme bulundu", ikinci is not None and len(ikinci[0].ortusmeler) > 0)


def test_agac_kontrol_bekleyen_bilgi_sonra_ayni_bulgular():
    print("\n[H1b-A2] agac_kontrol arka planda: once BILGI, sonra esli ile ayni bulgular")
    from cekirdek import uygunluk_bellek
    from cekirdek.dogrula import agac
    from cekirdek.geometri import yoklama_arka
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kare_altigen_halka.json"))
    uygunluk_bellek.temizle()
    yoklama_arka.temizle()
    ilk, tamam, ikinci = _arka_planda_bekle(lambda: agac.agac_kontrol(spec))
    kontrol("ilk: 'arka planda' BILGI", any(b.seviye == "bilgi" and "arka planda" in b.mesaj
                                            for b in ilk), "-> %s" % [b.mesaj for b in ilk])
    kontrol("bildirim geldi", tamam)
    esli = agac.agac_kontrol(spec)
    def t(liste):
        return [(b.seviye, b.yer, b.mesaj, b.oneri) for b in liste]
    kontrol("sonra esli ile ayni bulgular (bekleyen BILGI yok)", t(ikinci) == t(esli),
            "-> %s" % [b.mesaj[:60] for b in ikinci])


def test_blok_disinda_esli():
    print("\n[H1b-A3] arka_planda blogu disinda yokla esli (None donmez)")
    from cekirdek import sema
    from cekirdek.geometri import yoklama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kare_altigen_halka.json"))
    kontrol("esli sonuc", yoklama.yokla(spec, n=50) is not None)


def test_kurulum_hatasi_ayni_istisna():
    print("\n[H1b-A4] kurulamayan model: arka plan sonucu esli ile ayni istisna")
    import copy
    from cekirdek import uygunluk_bellek
    from cekirdek.geometri import yoklama, yoklama_arka
    from testler.test_geometri_dogrulama import ortusen_model
    spec = copy.deepcopy(ortusen_model())
    spec["malzemeler"] = []
    uygunluk_bellek.temizle()
    yoklama_arka.temizle()

    def dene():
        try:
            return yoklama.yokla(spec, n=50)
        except (KeyError, ValueError, RuntimeError) as e:
            return ("hata", type(e).__name__, str(e))
    ilk, tamam, ikinci = _arka_planda_bekle(dene)
    esli = dene()
    kontrol("esli yol hata veriyor", isinstance(esli, tuple) and esli[0] == "hata", "-> %r" % (esli,))
    kontrol("arka plan ayni hata", tamam and ikinci == esli, "-> %r / %r" % (ikinci, esli))


HIZLI = [test_blok_disinda_esli, test_arka_plan_sonucu_esli_ile_ayni,
         test_agac_kontrol_bekleyen_bilgi_sonra_ayni_bulgular, test_kurulum_hatasi_ayni_istisna]
YAVAS = []
