# -*- coding: utf-8 -*-
"""
 test_h1_hiz.py  --  v3 H1: hiz olcumleri (CPU suresi, time.process_time)

 OLCUM KURALI
   Sureler process_time (CPU) ile olculur: duvar saati baska yuk altinda
   oynar. Esikler MAKINEYE GORE OLCEKLENIR: once bir referans is (SFR-MET1000
   gelismis agacinin tek gezintisi; bu makinede 0.40 s) olculur ve
   olcek = max(1, olculen / 0.40) ile butun mutlak esikler carpilir. Hizli
   makinede esik sikilasmaz, yavas makinede orantili gevser.

 TABAN / SONRA (bu makine, CPU s; olcum betigi v3 cikti dizininde H1/olc.py)
                        acilis        gelismise gecis*     tus (gelismis)
   pwr_beavrs_kor       1.51 -> 1.13  2.36 -> 0.70         0.32 -> 0.055
   vver1000_kor         1.22 -> 1.01  2.68 -> 1.58         0.24 -> 0.040
   sfr_met1000_kor      7.82 -> 1.77  32.6 -> 13.7         2.90 -> 0.43
   pwr_kare_altigen_h.  1.49 -> 1.05  (zaten gelismis)     0.076 -> 0.017
   kafes_tamburlu_y.    1.19 -> 0.99  (zaten gelismis)     0.046 -> 0.010
   * gecisin ~11.5 s'si (SFR) dogrulamanin nokta yoklamasidir
     (cekirdek/geometri/yoklama.py, H1 sahipliginde degil); bu test gecisi
     dogrulama HARIC olcer ve dogrulamayi ayrica yazdirir.

 ESIKLER (olcekle carpilir; gerekce: plan hedefleri + olculen degerin ~2 kati pay)
   acilis <= 4.0 s          en kotu olculen 1.77 s x2 pay (plan hedefi 3 s)
   gecis (dogrulamasiz) <= 4.0 s   olculen SFR 1.6 s x2 pay (plan hedefi 3 s)
   Her olcu _TEKRAR olcumun ORTANCASIDIR; bellek her ornekte bosaltilir (soguk).
   tus <= 0.15 s            plan hedefi 100 ms + %50 pay; olculen <= 0.055 s
   tus (SFR) <= 0.9 s       SFR'de tek gezinti 0.40 s ve tus basina bir gezinti
                            kacinilmaz (icerik degisir); hedef 100 ms gezinti
                            hizlanmadan (cekirdek/geometri/gezinti.py, kesit.py)
                            ulasilamaz -- raporda acik nokta.
"""

import copy
import os
import statistics
import time

from testler.ortak_test import kontrol, ORNEK

_REFERANS_SURE = 0.40          # s CPU: SFR gelismis agacinin tek gezintisi (bu makine)
_ACILIS_ESIGI = 4.0            # s: olculen en kotu 1.77 s x2 pay (plan hedefi 3 s ayrica yazdirilir)
_GECIS_ESIGI = 4.0             # s: olculen SFR 1.6 s x2 pay (plan hedefi 3 s, dogrulamasiz)
_TEKRAR = 3                    # acilis/gecis/tus: bu kadar olcumun ortancasi
_TUS_ESIGI = 0.15              # s: plan hedefi 100 ms + %50 pay
_TUS_ESIGI_SFR = 0.9           # s: olculen 0.43 s (tek kacinilmaz gezinti) x2 pay
_BELLEK_ORANI = 0.10           # bellekli cagri soguk cagrinin en cok %10'u
_SAYIM_SINIRI = 150_000        # tukenme._sayim cagrisi (SFR): olculen 70 770 (x2 pay); taban 2.48 milyon
_BUYUK_ORNEKLER = ("pwr_beavrs_kor", "vver1000_kor", "sfr_met1000_kor",
                   "pwr_kare_altigen_halka", "kafes_tamburlu_yansitici")


def _cpu(islev):
    t = time.process_time()
    sonuc = islev()
    return time.process_time() - t, sonuc


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _sfr_gelismis():
    from cekirdek import geometri
    return geometri.gelismise_gec(_yukle("sfr_met1000_kor"))


def _olcek(gelismis_spec=None):
    """Makine olcegi: referans gezinti suresi / bu makinedeki deger (>= 1)."""
    from cekirdek import geometri
    from cekirdek.geometri import gezinti
    m = geometri.model(gelismis_spec or _sfr_gelismis())
    sure = min(_cpu(lambda: sum(1 for _ in gezinti.gez(m)))[0] for _i in range(2))
    return max(1.0, sure / _REFERANS_SURE), sure


# ---------------------------------------------------------------------------
# hizli: bellek isabeti ve islem sayisi (makineden bagimsiz)
# ---------------------------------------------------------------------------

def test_uygunluk_bellek_isabeti_hizli():
    print("\n[H1-H1] uygunluk: bellekli cagri soguk cagrinin <= %10'u (SFR gelismis)")
    from cekirdek import uygunluk, uygunluk_bellek
    spec = _sfr_gelismis()
    uygunluk_bellek.temizle()
    soguk, ilk = _cpu(lambda: (uygunluk.gecerli_sekmeler(spec), uygunluk.model_ozeti(spec)))
    sicak, ikinci = _cpu(lambda: (uygunluk.gecerli_sekmeler(spec), uygunluk.model_ozeti(spec)))
    kontrol("ayni sonuc", ilk == ikinci)
    kontrol("bellekli <= %%%d soguk" % (_BELLEK_ORANI * 100), sicak <= _BELLEK_ORANI * soguk,
            "soguk %.3f s, sicak %.4f s" % (soguk, sicak))


def test_tukenme_hacim_bellegi_hizli():
    print("\n[H1-H2] tukenme.hacimler: bellekli cagri soguk cagrinin <= %10'u (SFR)")
    from cekirdek import tukenme, uygunluk_bellek
    spec = _yukle("sfr_met1000_kor")
    uygunluk_bellek.temizle()
    soguk, ilk = _cpu(lambda: tukenme.hacimler(spec))
    sicak, ikinci = _cpu(lambda: tukenme.hacimler(spec))
    kontrol("ayni sonuc", ilk == ikinci)
    kontrol("bellekli <= %%%d soguk" % (_BELLEK_ORANI * 100), sicak <= _BELLEK_ORANI * soguk,
            "soguk %.3f s, sicak %.4f s" % (soguk, sicak))
    ilk[next(iter(ilk))]["hacim"] = -1.0
    kontrol("donen kayit cagiranin (bellek bozulmaz)", tukenme.hacimler(spec) == ikinci)


def test_sayim_ozyineleme_siniri(monkeypatch):
    print("\n[H1-H3] tukenme._sayim: SFR hacim sayiminda ozyineleme sayisi sinirli")
    from cekirdek import tukenme, uygunluk_bellek
    spec = _yukle("sfr_met1000_kor")
    uygunluk_bellek.temizle()
    sayi = [0]
    asil = tukenme._bellekli_sayim

    def sayan(*a, **k):
        sayi[0] += 1
        return asil(*a, **k)
    monkeypatch.setattr(tukenme, "_bellekli_sayim", sayan)
    tukenme.hacimler(spec)
    kontrol("sayim ozyinelemesi < %d (taban 2.48 milyon)" % _SAYIM_SINIRI,
            sayi[0] < _SAYIM_SINIRI, "cagri=%d" % sayi[0])


def test_tus_basina_tek_gezinti(monkeypatch):
    print("\n[H1-H4] pencere: gelismis editorde bir alan yazmak en cok BIR agac gezintisi")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.ana_pencere import AnaPencere
    from testler.test_h1_bellek import _GeziSayaci
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    p.onizleme._ciz = lambda *a, **k: None          # onizleme H2'nin
    try:
        p.ornek_ac(os.path.join(ORNEK, "pwr_kare_altigen_halka.json"))
        p.sekmeye_git("kor", sessiz=True)
        ed = p.s_kor.gelismis_editor
        yeni = _yaricapi_degistir(ed.agac, 1.0001)
        sayac = _GeziSayaci(monkeypatch)       # gezinti.gez + hacim'in ice aktardigi gez
        ed._form_degisti(yeni)
        kontrol("tus basina en cok 1 gezinti (taban 7)", sayac.sayi <= 1,
                "gezinti=%d" % sayac.sayi)
    finally:
        p._kirli = False
        p.close()
        p.deleteLater()


def _yaricapi_degistir(agac, carpan):
    """Agacin kopyasi; ilk 'yaricap' alani carpanla (topolojiyi degistirmeyen tus)."""
    yeni = copy.deepcopy(agac)
    yigin = [yeni]
    while yigin:
        d = yigin.pop(0)
        if isinstance(d, dict):
            if isinstance(d.get("yaricap"), (int, float)) and d["yaricap"]:
                d["yaricap"] = d["yaricap"] * carpan
                return yeni
            yigin.extend(d.values())
        elif isinstance(d, list):
            yigin.extend(d)
    raise AssertionError("agacta yaricap alani yok")


# ---------------------------------------------------------------------------
# yavas: 5 buyuk ornekte pencere olcumleri
# ---------------------------------------------------------------------------

def _olaylar():
    from PySide6 import QtWidgets
    for _i in range(3):
        QtWidgets.QApplication.processEvents()


def _ilk_sayi_yolu(d, anahtarlar=("yaricap", "kalinlik", "yukseklik")):
    """Gelismis agacta topolojiyi degistirmeyen bir sayi alani (olc.py ile ayni)."""
    for anahtar in anahtarlar:
        yigin = [(d, ())]
        while yigin:
            x, yol = yigin.pop()
            if isinstance(x, dict):
                if isinstance(x.get(anahtar), (int, float)) and x[anahtar]:
                    return yol + (anahtar,)
                yigin.extend((v, yol + (k,)) for k, v in reversed(list(x.items())))
            elif isinstance(x, list):
                yigin.extend((v, yol + (i,)) for i, v in reversed(list(enumerate(x))))
    return None


def _tus_agaci(agac, yol, i):
    yeni = copy.deepcopy(agac)
    d = yeni
    for k in yol[:-1]:
        d = d[k]
    d[yol[-1]] = d[yol[-1]] * (1.0 + 1e-4 * (i + 1))
    return yeni


def _ornek_olc(p, ad):
    """(acilis, gecis_dogrulamasiz, dogrulama, tus) CPU s."""
    dogrulama = [0.0]
    asil_dogrula = p._dogrula

    def olcen_dogrula(*a, **k):
        t = time.process_time()
        try:
            return asil_dogrula(*a, **k)
        finally:
            dogrulama[0] += time.process_time() - t
    p._dogrula = olcen_dogrula
    acilis, _s = _cpu(lambda: (p.ornek_ac(os.path.join(ORNEK, ad + ".json")), _olaylar()))
    p.sekmeye_git("kor", sessiz=True)
    _olaylar()
    gecis = None
    if not p.s_kor.agac_modunda_mi():
        dogrulama[0] = 0.0
        toplam, _s = _cpu(lambda: (p.s_kor.gelismise_gec(onaysiz=True), _olaylar()))
        gecis = toplam - dogrulama[0]
    gecis_dogrulama = dogrulama[0]
    ed = p.s_kor.gelismis_editor
    yol = _ilk_sayi_yolu(ed.agac)
    tuslar = []
    for i in range(3):
        yeni = _tus_agaci(ed.agac, yol, i)
        tuslar.append(_cpu(lambda: ed._form_degisti(yeni))[0])
    p._dog_sayac.stop()
    p._gecmis_sayac.stop()
    p._dogrula = asil_dogrula
    return acilis, gecis, gecis_dogrulama, statistics.median(tuslar)


def _ornek_ortanca(ad):
    """_TEKRAR taze pencerede (soguk bellek) olcum; her metrigin ortancasi."""
    from arayuz.ana_pencere import AnaPencere
    from cekirdek import uygunluk_bellek
    olcumler = []
    for _i in range(_TEKRAR):
        uygunluk_bellek.temizle()
        p = AnaPencere()
        p._kaydetme_sor = lambda: True
        p.onizleme._ciz = lambda *a, **k: None      # onizleme H2'nin; ayri olculur
        try:
            olcumler.append(_ornek_olc(p, ad))
        finally:
            p._kirli = False
            p.close()
            p.deleteLater()
            _olaylar()
    return [None if olcumler[0][j] is None else statistics.median(o[j] for o in olcumler)
            for j in range(4)]


def test_buyuk_orneklerde_sureler():
    print("\n[H1-Y1] 5 buyuk ornek: acilis, gelismise gecis (dogrulamasiz), tus -- CPU s")
    from PySide6 import QtWidgets
    from cekirdek import uygunluk_bellek
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    uygunluk_bellek.temizle()
    olcek, ref = _olcek()
    print("  makine olcegi %.2f (referans gezinti %.3f s)" % (olcek, ref))
    for ad in _BUYUK_ORNEKLER:
        acilis, gecis, dogrulama, tus = _ornek_ortanca(ad)
        tus_esigi = _TUS_ESIGI_SFR if ad.startswith("sfr") else _TUS_ESIGI
        print("  %s: plan hedefi acilis/gecis 3 s, tus 0.1 s" % ad)
        kontrol("%s acilis <= %.1f s" % (ad, _ACILIS_ESIGI * olcek),
                acilis <= _ACILIS_ESIGI * olcek, "%.3f s" % acilis)
        if gecis is not None:
            kontrol("%s gelismise gecis (dogrulamasiz) <= %.1f s" % (ad, _GECIS_ESIGI * olcek),
                    gecis <= _GECIS_ESIGI * olcek,
                    "%.3f s (+ dogrulama %.3f s, H1 disi)" % (gecis, dogrulama))
        kontrol("%s tus <= %.2f s" % (ad, tus_esigi * olcek), tus <= tus_esigi * olcek,
                "%.4f s" % tus)


HIZLI = [test_uygunluk_bellek_isabeti_hizli, test_tukenme_hacim_bellegi_hizli,
         test_sayim_ozyineleme_siniri, test_tus_basina_tek_gezinti]
YAVAS = [test_buyuk_orneklerde_sureler]
