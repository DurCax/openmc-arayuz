# -*- coding: utf-8 -*-
"""
================================================================================
 test_uygunluk.py  --  cekirdek/uygunluk.py kurallarinin DOGRULUGU
================================================================================
 Imzalar test_sozlesme.py'dedir; burada DAVRANIS sinanir.

   [U1] Kahin tablolari   : 27 ornegin HER sorusu (sekmeler, 12 taramanin
                            hedefleri, kritik arama, sinirlar, ayarlar,
                            kaynak, guc, tukenme, parcalar, roller) elle
                            cikarilmis beklentiyle birebir.
   [U2] Olcum             : sunulan her (tarama, hedef) cifti kurulan modeli
                            GERCEKTEN degistirir; modeli degistirmeyen ya da
                            kurulamayan hicbir cift sunulmaz. (Monte Carlo
                            yok: kurucu.kur + geometri/malzeme XML'i.)
   [U3] Kutuphane rolleri : malzeme_kutup.KUTUPHANE'nin TAMAMI + sinir durumlari
   [U4] Sentetik modeller : orneklerde gorunmeyen kurallar (agir su,
                            kullanilmayan kafes/cubuk, tambur dolgusu kafes...)
   [U5] dogrula ile uyum  : arayuzun sundugu her secenek dogrulamadan hatasiz
                            gecer, sunmadigi her secenek bir bulgu uretir;
                            elle yazilmis dosyalar icin yeni bulgular.

 Her kontrol istisnayi yakalar: bir fonksiyonun eksik ya da hatali olmasi
 butun paketi durdurmaz, KALDI olarak gorunur.
================================================================================
"""

import copy
import os
import xml.etree.ElementTree as ET

from testler.ortak_test import kontrol, ORNEK


# ----------------------------------------------------------------------------
# yardimcilar
# ----------------------------------------------------------------------------

class _Istisna(object):
    """Cagri istisna atti; hicbir beklenen degere esit degildir."""

    def __init__(self, e):
        self.e = e

    def __eq__(self, diger):
        return False

    def __ne__(self, diger):
        return True

    def __repr__(self):
        return "ISTISNA(%s: %s)" % (type(self.e).__name__, self.e)


def _g(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:           # noqa: BLE001 -- testte bilincli
        return _Istisna(e)


def _gu(ad, *a, **kw):
    """uygunluk.<ad>(...) -- fonksiyon yoksa da (eski surum) istisna degil KALDI."""
    return _g(lambda: getattr(_u(), ad)(*a, **kw))


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _u():
    from cekirdek import uygunluk
    return uygunluk


# tarama.TURLER'in sirasi; kahin tablosu bu 12 turun HEPSINI kapsar.
TURLER = ("yakit_sicaklik", "sogutucu_sicaklik", "malzeme_yogunluk",
          "void_orani", "bor_ppm", "zenginlik", "kafes_adim", "kor_adim",
          "cubuk_daldirma", "cubuk_yaricap", "tambur_donme",
          "yansitici_kalinlik")


def _h(**kw):
    """Hedef tablosu: verilmeyen turler bos liste."""
    d = {t: [] for t in TURLER}
    d.update(kw)
    return d


SM = {"sogutucu", "moderator"}
TUM_SEKME = ["malzemeler", "parcalar", "demet", "kor", "ayarlar", "calistir",
             "analiz", "tukenme"]
KARE = ["reflective", "vacuum", "white", "periodic"]
ALTIGEN = ["reflective", "vacuum", "white", "periodic"]   # altigen prizma: periodic GECERLI
EGRI = ["reflective", "vacuum", "white"]            # silindir
KURE = ["vacuum", "reflective", "white"]
ZB = ["vacuum", "reflective", "white"]              # 3B alt/ust
OZDEGER = {"pasif": True, "entropi": True, "kinetik": True,
           "kaynak_siddeti": False, "foton": False, "kaynak_tayfi_temel": False,
           "kutu_kaynagi": True}
YAKIT_3 = [("yakit_cubugu", 0), ("yakit_cubugu", 1), ("yakit_cubugu", 2)]


def _ozet(tur, boyut, kafes=False, kontrol_cubugu=False, tambur=False,
          fisil=True, mod="eigenvalue"):
    return {"tur": tur, "boyut": boyut, "mod": mod, "kafes": kafes,
            "kontrol_cubugu": kontrol_cubugu, "tambur": tambur, "fisil": fisil}


# ----------------------------------------------------------------------------
# [U1] KAHIN TABLOSU -- denetim raporundaki tablolar, koda karsi dogrulanmis
# ----------------------------------------------------------------------------
# sinir: (yan, alt, ust) ; kaynak: (turler, parcaciklar) ;
# parca: (cubuk, plaka, kontrol_cubugu)

KAHIN = {
    "godiva_kriter": dict(
        ozet=_ozet("kuresel", "2B"),
        roller={"heu": {"yakit"}},
        sekmeler=["malzemeler", "kor", "ayarlar", "calistir", "analiz", "tukenme"],
        # heu atom/b-cm: yogunluk taramasi g/cm3 yazardi -> sunulmaz
        hedefler=_h(yakit_sicaklik=["heu"]),
        kritik=[],
        sinir=(KURE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=[], tukenme=True, parca=(False, False, False)),
    "mtr_plaka": dict(
        ozet=_ozet("tek_plaka", "2B"),
        roller={"u3si2_al": {"yakit"}, "al6061": {"yapisal"}, "su": SM},
        sekmeler=["malzemeler", "parcalar", "kor", "ayarlar", "calistir",
                  "analiz", "tukenme"],
        hedefler=_h(yakit_sicaklik=["u3si2_al"], sogutucu_sicaklik=["su"],
                    malzeme_yogunluk=["u3si2_al", "al6061", "su"],
                    void_orani=["su"], bor_ppm=["su"], zenginlik=["u3si2_al"]),
        kritik=["bor_ppm", "zenginlik"],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=[], tukenme=True, parca=(False, True, False)),
    "pwr_17x17": dict(
        ozet=_ozet("tek_demet", "2B", kafes=True),
        roller={"uo2": {"yakit"}, "helyum": {"gaz"}, "zirkaloy4": {"yapisal"},
                "su": SM},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=["uo2"], sogutucu_sicaklik=["su"],
                    malzeme_yogunluk=["uo2", "helyum", "zirkaloy4", "su"],
                    void_orani=["su"], bor_ppm=["su"], zenginlik=["uo2"],
                    kafes_adim=["demet_17x17"],
                    cubuk_yaricap=YAKIT_3 + [("kilavuz_boru", 0), ("kilavuz_boru", 1)]),
        kritik=["bor_ppm", "zenginlik"],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=["yakit_cubugu"], tukenme=True, parca=(True, False, False)),
    "pwr_3b": dict(
        ozet=_ozet("tek_demet", "3B", kafes=True),
        roller={"uo2": {"yakit"}, "helyum": {"gaz"}, "zirkaloy4": {"yapisal"},
                "su": SM},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=["uo2"], sogutucu_sicaklik=["su"],
                    malzeme_yogunluk=["uo2", "helyum", "zirkaloy4", "su"],
                    void_orani=["su"], bor_ppm=["su"], zenginlik=["uo2"],
                    kafes_adim=["demet_17x17"],
                    cubuk_yaricap=YAKIT_3 + [("kilavuz_boru", 0), ("kilavuz_boru", 1)]),
        kritik=["bor_ppm", "zenginlik"],
        sinir=(KARE, ZB, ZB),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=["yakit_cubugu"], tukenme=True, parca=(True, False, True)),
    "pwr_eksenel": dict(
        ozet=_ozet("tek_demet", "3B_katmanli", kafes=True),
        roller={"uo2": {"yakit"}, "helyum": {"gaz"}, "zirkaloy4": {"yapisal"},
                "su": SM, "uo2_dogal": {"yakit"}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=["uo2", "uo2_dogal"], sogutucu_sicaklik=["su"],
                    malzeme_yogunluk=["uo2", "helyum", "zirkaloy4", "su", "uo2_dogal"],
                    void_orani=["su"], bor_ppm=["su"], zenginlik=["uo2", "uo2_dogal"],
                    # her katmanin kafesi ayri (katman uyarisi: rapor)
                    kafes_adim=["demet_17x17", "demet_blanket", "demet_plenum"],
                    cubuk_yaricap=YAKIT_3 + [("kilavuz_boru", 0), ("kilavuz_boru", 1),
                                             ("blanket_cubugu", 0), ("blanket_cubugu", 1),
                                             ("blanket_cubugu", 2), ("plenum_cubugu", 0),
                                             ("plenum_cubugu", 1), ("plenum_cubugu", 2)]),
        kritik=["bor_ppm", "zenginlik"],
        sinir=(KARE, ZB, ZB),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        # dogal uranyum blanket de fisildir (Z >= 90)
        guc=["yakit_cubugu", "blanket_cubugu"], tukenme=True,
        parca=(True, False, True)),
    "pwr_kontrol": dict(
        ozet=_ozet("tek_demet", "3B", kafes=True, kontrol_cubugu=True),
        roller={"uo2": {"yakit"}, "helyum": {"gaz"}, "zirkaloy4": {"yapisal"},
                "su": SM, "b4c": {"emici"}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=["uo2"], sogutucu_sicaklik=["su"],
                    malzeme_yogunluk=["uo2", "helyum", "zirkaloy4", "su", "b4c"],
                    void_orani=["su"], bor_ppm=["su"], zenginlik=["uo2"],
                    kafes_adim=["demet_17x17"], cubuk_daldirma=["kontrol_cubugu"],
                    # kilavuz_boru tanimli ama haritada yok (k, e -> kontrol_cubugu)
                    cubuk_yaricap=YAKIT_3 + [("kontrol_cubugu", 0), ("kontrol_cubugu", 1)]),
        kritik=["bor_ppm", "zenginlik", "cubuk_daldirma"],
        sinir=(KARE, ZB, ZB),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=["yakit_cubugu"], tukenme=True, parca=(True, False, True)),
    "pwr_pinhucre": dict(
        ozet=_ozet("tek_cubuk", "2B"),
        roller={"uo2": {"yakit"}, "zirkaloy": {"yapisal"}, "su": SM},
        sekmeler=["malzemeler", "parcalar", "kor", "ayarlar", "calistir",
                  "analiz", "tukenme"],
        hedefler=_h(yakit_sicaklik=["uo2"], sogutucu_sicaklik=["su"],
                    malzeme_yogunluk=["uo2", "zirkaloy", "su"],
                    void_orani=["su"], bor_ppm=["su"], zenginlik=["uo2"],
                    kor_adim=[None],
                    cubuk_yaricap=[("yakit_cubugu", 0), ("yakit_cubugu", 1)]),
        kritik=["bor_ppm", "zenginlik"],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=[], tukenme=True, parca=(True, False, False)),
    "sfr_altigen": dict(
        ozet=_ozet("tek_demet", "2B", kafes=True),
        roller={"u10mo": {"yakit"}, "ss316": {"yapisal"}, "sodyum": {"sogutucu"},
                "b4c": {"emici"}},
        sekmeler=TUM_SEKME,
        # emici_cubuk (ve b4c) anahtarda var, haritada yok -> geometride yok
        hedefler=_h(yakit_sicaklik=["u10mo"], sogutucu_sicaklik=["sodyum"],
                    malzeme_yogunluk=["u10mo", "ss316", "sodyum"],
                    void_orani=["sodyum"], zenginlik=["u10mo"],
                    kafes_adim=["demet_hex"], cubuk_yaricap=YAKIT_3),
        kritik=["zenginlik"],
        sinir=(ALTIGEN, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=["yakit_cubugu"], tukenme=True, parca=(True, False, False)),
    "tamburlu_kor": dict(
        ozet=_ozet("tamburlu", "3B", tambur=True),
        roller={"u10mo": {"yakit"}, "berilyum": {"moderator"}, "b4c": {"emici"}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=["u10mo"],
                    malzeme_yogunluk=["u10mo", "berilyum", "b4c"],
                    zenginlik=["u10mo"], tambur_donme=[None],
                    yansitici_kalinlik=[None]),
        kritik=["zenginlik", "tambur_donme", "yansitici_kalinlik"],
        sinir=(EGRI, ZB, ZB),
        # dolgu malzeme (u10mo): kafes yok -> guc dagilimi yok
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(["nokta", "kutu"], ["neutron"]),
        guc=[], tukenme=True, parca=(True, False, True)),
    "zirh_kure": dict(
        ozet=_ozet("kuresel", "2B", fisil=False, mod="fixed source"),
        roller={"su": SM, "celik": {"yapisal"}},
        sekmeler=["malzemeler", "kor", "ayarlar", "calistir"],
        hedefler=_h(),
        kritik=[],
        sinir=(KURE, [], []),
        ayar={"pasif": False, "entropi": False, "kinetik": False,
              "kaynak_siddeti": True, "foton": True, "kaynak_tayfi_temel": True,
              "kutu_kaynagi": False, "guc_dagilimi": False, "eksenel_dilim": False},
        kaynak=(["nokta"], ["neutron", "photon"]),
        guc=[], tukenme=False, parca=(False, False, False)),
    "bwr_10x10": dict(
        ozet=_ozet('tek_demet', '2B', kafes=True),
        roller={'uo2_44': {'yakit'}, 'uo2_36': {'yakit'}, 'uo2_gd': {'yakit'}, 'zirkaloy2': {'yapisal'}, 'helyum': {'gaz'}, 'su_bosluklu': SM, 'su_dolu': SM, 'kutu_bypass': {'yapisal'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2_44', 'uo2_36', 'uo2_gd'], sogutucu_sicaklik=['su_bosluklu', 'su_dolu'], malzeme_yogunluk=['uo2_44', 'uo2_36', 'uo2_gd', 'zirkaloy2', 'helyum', 'su_bosluklu', 'su_dolu', 'kutu_bypass'], void_orani=['su_bosluklu', 'su_dolu'], bor_ppm=['su_bosluklu', 'su_dolu'], zenginlik=['uo2_44', 'uo2_36', 'uo2_gd'], kafes_adim=['bwr_10x10'], cubuk_yaricap=[('cubuk_44', 0), ('cubuk_44', 1), ('cubuk_44', 2), ('cubuk_36', 0), ('cubuk_36', 1), ('cubuk_36', 2), ('cubuk_gd', 0), ('cubuk_gd', 1), ('cubuk_gd', 2)], yansitici_kalinlik=[None]),
        kritik=['bor_ppm', 'zenginlik', 'yansitici_kalinlik'],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['cubuk_44', 'cubuk_36', 'cubuk_gd'], tukenme=True, parca=(True, False, False)),
    "kriter_flattop25": dict(
        ozet=_ozet('kuresel', '2B'),
        roller={'heu': {'yakit'}, 'dogal_u': {'yakit'}},
        sekmeler=['malzemeler', 'kor', 'ayarlar', 'calistir', 'analiz', 'tukenme'],
        hedefler=_h(yakit_sicaklik=['heu', 'dogal_u']),
        kritik=[],
        sinir=(KURE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=[], tukenme=True, parca=(False, False, False)),
    "kriter_jezebel": dict(
        ozet=_ozet('kuresel', '2B'),
        roller={'pu_metal': {'yakit'}},
        sekmeler=['malzemeler', 'kor', 'ayarlar', 'calistir', 'analiz', 'tukenme'],
        hedefler=_h(yakit_sicaklik=['pu_metal']),
        kritik=[],
        sinir=(KURE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=[], tukenme=True, parca=(False, False, False)),
    "kriter_lct008": dict(
        ozet=_ozet('tamburlu', '3B', kafes=True),
        roller={'uo2': {'yakit'}, 'al6061': {'yapisal'}, 'su_borlu': SM},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2'], sogutucu_sicaklik=['su_borlu'], void_orani=['su_borlu'], bor_ppm=['su_borlu'], kafes_adim=['kor_kafesi'], cubuk_yaricap=[('yakit_cubugu', 0), ('yakit_cubugu', 1)], yansitici_kalinlik=[None]),
        kritik=['bor_ppm', 'yansitici_kalinlik'],
        sinir=(EGRI, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_cubugu'], tukenme=True, parca=(True, False, True)),
    "kriter_vver1000_ugd": dict(
        ozet=_ozet('tek_demet', '2B', kafes=True),
        roller={'u1': {'yakit'}, 'gd1': {'yakit'}, 'cl1': {'yapisal'}, 'mod3': SM},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['u1', 'gd1'], sogutucu_sicaklik=['mod3'], void_orani=['mod3'], bor_ppm=['mod3'], kafes_adim=['tvs_ugd'], cubuk_yaricap=[('yakit_u1', 0), ('yakit_u1', 1), ('yakit_gd', 0), ('yakit_gd', 1), ('kilavuz_boru', 0), ('kilavuz_boru', 1), ('merkez_boru', 0), ('merkez_boru', 1)]),
        kritik=['bor_ppm'],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_u1', 'yakit_gd'], tukenme=True, parca=(True, False, False)),
    "mtr_kor": dict(
        ozet=_ozet('kare_kafes', '3B_katmanli'),
        roller={'u3si2_al': {'yakit'}, 'al6061': {'yapisal'}, 'su': SM, 'berilyum': {'moderator'}, 'grafit': {'moderator'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['u3si2_al'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['u3si2_al', 'al6061', 'su', 'berilyum', 'grafit'], void_orani=['su'], bor_ppm=['su'], zenginlik=['u3si2_al'], kor_adim=[None], yansitici_kalinlik=[None]),
        kritik=['bor_ppm', 'zenginlik', 'yansitici_kalinlik'],
        sinir=(KARE, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=False, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=[], tukenme=True, parca=(True, False, True)),
    # BEAVRS: dogal bolluktaki H2 (%0.016) agir su SAYILMAZ -> sogutucu_sicaklik
    # ve bor_ppm hedefi sunulur (agir su ayrimi H2 kesrine bakar)
    "pwr_beavrs_kor": dict(
        ozet=_ozet('kare_kafes', '3B_katmanli', kafes=True),
        roller={'uo2_a': {'yakit'}, 'uo2_b': {'yakit'}, 'uo2_c': {'yakit'}, 'su_borlu': SM, 'zirkaloy4': {'yapisal'}, 'ss304': {'yapisal'}, 'helyum': {'gaz'}, 'hava': {'gaz'}, 'pyrex': {'emici'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2_a', 'uo2_b', 'uo2_c'], sogutucu_sicaklik=['su_borlu'], void_orani=['su_borlu'], bor_ppm=['su_borlu'], kafes_adim=['dc_yok', 'dc_6s', 'dc_16', 'da_yok', 'dc_20', 'dc_15se', 'db_16', 'dc_15sw', 'db_yok', 'db_12', 'dc_6e', 'dc_6w', 'dc_15ne', 'dc_15nw', 'dc_6n'], kor_adim=[None], cubuk_yaricap=[('yakit_a', 0), ('yakit_a', 1), ('yakit_a', 2), ('yakit_b', 0), ('yakit_b', 1), ('yakit_b', 2), ('yakit_c', 0), ('yakit_c', 1), ('yakit_c', 2), ('kilavuz_boru', 0), ('kilavuz_boru', 1),  ('pyrex_cubugu', 0), ('pyrex_cubugu', 1), ('pyrex_cubugu', 2), ('pyrex_cubugu', 3), ('pyrex_cubugu', 4), ('pyrex_cubugu', 5), ('pyrex_cubugu', 6), ('pyrex_cubugu', 7)], yansitici_kalinlik=[None]),
        kritik=['bor_ppm', 'yansitici_kalinlik'],
        sinir=(KARE, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_a', 'yakit_b', 'yakit_c'], tukenme=True, parca=(True, False, True)),
    "pwr_ceyrek_kor": dict(
        ozet=_ozet('kare_kafes', '3B_katmanli', kafes=True),
        roller={'uo2_24': {'yakit'}, 'helyum': {'gaz'}, 'zirkaloy4': {'yapisal'}, 'su': SM, 'uo2_31': {'yakit'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2_24', 'uo2_31'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['uo2_24', 'helyum', 'zirkaloy4', 'su', 'uo2_31'], void_orani=['su'], bor_ppm=['su'], zenginlik=['uo2_24', 'uo2_31'], kafes_adim=['demet_24', 'demet_31'], kor_adim=[None], cubuk_yaricap=[('yakit_24', 0), ('yakit_24', 1), ('yakit_24', 2), ('kilavuz_boru', 0), ('kilavuz_boru', 1), ('yakit_31', 0), ('yakit_31', 1), ('yakit_31', 2)]),
        kritik=['bor_ppm', 'zenginlik'],
        sinir=(KARE, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_24', 'yakit_31'], tukenme=True, parca=(True, False, True)),
    "pwr_gd_tukenme": dict(
        ozet=_ozet('tek_demet', '2B', kafes=True),
        roller={'uo2': {'yakit'}, 'uo2_gd_1': {'yakit'}, 'uo2_gd_2': {'yakit'}, 'uo2_gd_3': {'yakit'}, 'uo2_gd_4': {'yakit'}, 'uo2_gd_5': {'yakit'}, 'helyum': {'gaz'}, 'zirkaloy4': {'yapisal'}, 'su': SM},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2', 'uo2_gd_1', 'uo2_gd_2', 'uo2_gd_3', 'uo2_gd_4', 'uo2_gd_5'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['uo2', 'uo2_gd_1', 'uo2_gd_2', 'uo2_gd_3', 'uo2_gd_4', 'uo2_gd_5', 'helyum', 'zirkaloy4', 'su'], void_orani=['su'], bor_ppm=['su'], zenginlik=['uo2', 'uo2_gd_1', 'uo2_gd_2', 'uo2_gd_3', 'uo2_gd_4', 'uo2_gd_5'], kafes_adim=['super_hucre'], cubuk_yaricap=[('yakit_cubugu', 0), ('yakit_cubugu', 1), ('yakit_cubugu', 2), ('gd_cubugu', 0), ('gd_cubugu', 1), ('gd_cubugu', 2), ('gd_cubugu', 3), ('gd_cubugu', 4), ('gd_cubugu', 5), ('gd_cubugu', 6)]),
        kritik=['bor_ppm', 'zenginlik'],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_cubugu', 'gd_cubugu'], tukenme=True, parca=(True, False, False)),
    "pwr_mox_demet": dict(
        ozet=_ozet('tek_demet', '2B', kafes=True),
        roller={'mox_25': {'yakit'}, 'mox_30': {'yakit'}, 'mox_50': {'yakit'}, 'zirkaloy2': {'yapisal'}, 'bosluk_o16': {'gaz'}, 'waba': {'emici'}, 'su': SM},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['mox_25', 'mox_30', 'mox_50'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['mox_25', 'mox_30', 'mox_50', 'zirkaloy2', 'bosluk_o16', 'waba', 'su'], void_orani=['su'], bor_ppm=['su'], kafes_adim=['mox_demeti'], cubuk_yaricap=[('mox_25', 0), ('mox_25', 1), ('mox_25', 2), ('mox_30', 0), ('mox_30', 1), ('mox_30', 2), ('mox_50', 0), ('mox_50', 1), ('mox_50', 2), ('kilavuz_boru', 0), ('kilavuz_boru', 1), ('waba_cubugu', 0),  ('waba_cubugu', 1), ('waba_cubugu', 2), ('waba_cubugu', 3), ('waba_cubugu', 4), ('waba_cubugu', 5)]),
        kritik=['bor_ppm'],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['mox_25', 'mox_30', 'mox_50'], tukenme=True, parca=(True, False, False)),
    "pwr_smr_kor": dict(
        ozet=_ozet('kare_kafes', '3B_katmanli', kafes=True),
        roller={'uo2_24': {'yakit'}, 'helyum': {'gaz'}, 'zirkaloy4': {'yapisal'}, 'su': SM, 'uo2_31': {'yakit'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2_24', 'uo2_31'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['uo2_24', 'helyum', 'zirkaloy4', 'su', 'uo2_31'], void_orani=['su'], bor_ppm=['su'], zenginlik=['uo2_24', 'uo2_31'], kafes_adim=['demet_24', 'demet_31'], kor_adim=[None], cubuk_yaricap=[('yakit_24', 0), ('yakit_24', 1), ('yakit_24', 2), ('kilavuz_boru', 0), ('kilavuz_boru', 1), ('yakit_31', 0), ('yakit_31', 1), ('yakit_31', 2)]),
        kritik=['bor_ppm', 'zenginlik'],
        sinir=(KARE, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_24', 'yakit_31'], tukenme=True, parca=(True, False, True)),
    "sfr_met1000_demet": dict(
        ozet=_ozet('altigen_kafes', '2B', kafes=True),
        roller={'yakit_ic3': {'yakit'}, 'sodyum': {'sogutucu'}, 'ht9': {'yapisal'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['yakit_ic3'], sogutucu_sicaklik=['sodyum'], void_orani=['sodyum'], kafes_adim=['surucu_ic3'], kor_adim=[None], cubuk_yaricap=[('pin_ic3', 0), ('pin_ic3', 1)]),
        kritik=[],
        sinir=(EGRI, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['pin_ic3'], tukenme=True, parca=(True, False, False)),
    "sfr_met1000_kor": dict(
        ozet=_ozet('altigen_kafes', '3B_katmanli', kafes=True),
        roller={'yakit_ic1': {'yakit'}, 'yakit_ic2': {'yakit'}, 'yakit_ic3': {'yakit'}, 'yakit_ic4': {'yakit'}, 'yakit_ic5': {'yakit'}, 'yakit_dis1': {'yakit'}, 'yakit_dis2': {'yakit'}, 'yakit_dis3': {'yakit'}, 'yakit_dis4': {'yakit'}, 'yakit_dis5': {'yakit'}, 'sodyum': {'sogutucu'}, 'ht9': {'yapisal'}, 'alt_yapi': {'yapisal'}, 'alt_yansitici': {'yapisal'}, 'bag_na': {'yapisal'}, 'plenum': {'yapisal'}, 'radyal_yansitici': {'yapisal'}, 'radyal_kalkan': {'emici'}, 'sogurucu': {'emici'}, 'bos_kanal': {'yapisal'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['yakit_ic1', 'yakit_ic2', 'yakit_ic3', 'yakit_ic4', 'yakit_ic5', 'yakit_dis1', 'yakit_dis2', 'yakit_dis3', 'yakit_dis4', 'yakit_dis5'], sogutucu_sicaklik=['sodyum'], void_orani=['sodyum'], kafes_adim=['surucu_ic1', 'surucu_ic2', 'surucu_ic3', 'surucu_ic4', 'surucu_ic5', 'surucu_dis1', 'surucu_dis2', 'surucu_dis3', 'surucu_dis4', 'surucu_dis5'], kor_adim=[None], cubuk_yaricap=[('pin_ic1', 0), ('pin_ic1', 1), ('pin_ic2', 0), ('pin_ic2', 1), ('pin_ic3', 0), ('pin_ic3', 1), ('pin_ic4', 0), ('pin_ic4', 1), ('pin_ic5', 0), ('pin_ic5', 1), ('pin_dis1', 0), ('pin_dis1', 1),  ('pin_dis2', 0), ('pin_dis2', 1), ('pin_dis3', 0), ('pin_dis3', 1), ('pin_dis4', 0), ('pin_dis4', 1), ('pin_dis5', 0), ('pin_dis5', 1)]),
        kritik=[],
        sinir=(EGRI, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['pin_ic1', 'pin_ic2', 'pin_ic3', 'pin_ic4', 'pin_ic5', 'pin_dis1', 'pin_dis2', 'pin_dis3', 'pin_dis4', 'pin_dis5'], tukenme=True, parca=(True, False, True)),
    "vver1000_demet": dict(
        ozet=_ozet('tek_demet', '2B', kafes=True),
        roller={'uo2_37': {'yakit'}, 'uo2_gd': {'yakit'}, 'zr1nb': {'yapisal'}, 'su': SM, 'helyum': {'gaz'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2_37', 'uo2_gd'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['uo2_37', 'uo2_gd', 'helyum'], void_orani=['su'], bor_ppm=['su'], zenginlik=['uo2_37', 'uo2_gd'], kafes_adim=['tvs'], cubuk_yaricap=[('yakit_cubugu', 0), ('yakit_cubugu', 1), ('yakit_cubugu', 2), ('yakit_cubugu', 3), ('tveg_cubugu', 0), ('tveg_cubugu', 1), ('tveg_cubugu', 2), ('tveg_cubugu', 3), ('kilavuz_boru', 0),  ('kilavuz_boru', 1), ('merkez_boru', 0), ('merkez_boru', 1)]),
        kritik=['bor_ppm', 'zenginlik'],
        sinir=(KARE, [], []),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=False),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_cubugu', 'tveg_cubugu'], tukenme=True, parca=(True, False, False)),
    "vver1000_kor": dict(
        ozet=_ozet('altigen_kafes', '3B_katmanli', kafes=True),
        roller={'uo2_20': {'yakit'}, 'uo2_30': {'yakit'}, 'uo2_44': {'yakit'}, 'uo2_gd': {'yakit'}, 'zr1nb': {'yapisal'}, 'su': SM, 'helyum': {'gaz'}, 'yansitici_celik_su': {'yapisal'}},
        sekmeler=TUM_SEKME,
        hedefler=_h(yakit_sicaklik=['uo2_20', 'uo2_30', 'uo2_44', 'uo2_gd'], sogutucu_sicaklik=['su'], malzeme_yogunluk=['uo2_20', 'uo2_30', 'uo2_44', 'uo2_gd', 'helyum', 'yansitici_celik_su'], void_orani=['su'], bor_ppm=['su'], zenginlik=['uo2_20', 'uo2_30', 'uo2_44', 'uo2_gd'], kafes_adim=['tvs_a20', 'tvs_b30', 'tvs_c44'], kor_adim=[None], cubuk_yaricap=[('yakit_20', 0), ('yakit_20', 1), ('yakit_20', 2), ('yakit_20', 3), ('yakit_30', 0), ('yakit_30', 1), ('yakit_30', 2), ('yakit_30', 3), ('yakit_44', 0), ('yakit_44', 1), ('yakit_44', 2),  ('yakit_44', 3), ('tveg_cubugu', 0), ('tveg_cubugu', 1), ('tveg_cubugu', 2), ('tveg_cubugu', 3), ('kilavuz_boru', 0), ('kilavuz_boru', 1), ('merkez_boru', 0), ('merkez_boru', 1)], yansitici_kalinlik=[None]),
        kritik=['bor_ppm', 'zenginlik', 'yansitici_kalinlik'],
        sinir=(EGRI, KURE, KURE),
        ayar=dict(OZDEGER, guc_dagilimi=True, eksenel_dilim=True),
        kaynak=(['nokta', 'kutu'], ['neutron']),
        guc=['yakit_20', 'yakit_30', 'yakit_44', 'tveg_cubugu'], tukenme=True, parca=(True, False, True)),
    "zirh_katmanli": dict(
        ozet=_ozet('kuresel', '2B', fisil=False, mod='fixed source'),
        roller={'hava': {'gaz'}, 'borlu_pe': {'emici'}, 'kursun': {'sogutucu'}, 'beton': {'yapisal'}},
        sekmeler=['malzemeler', 'kor', 'ayarlar', 'calistir'],
        hedefler=_h(),
        kritik=[],
        sinir=(KURE, [], []),
        ayar={'pasif': False, 'entropi': False, 'kinetik': False, 'kaynak_siddeti': True, 'foton': True, 'kaynak_tayfi_temel': True, 'kutu_kaynagi': False, 'guc_dagilimi': False, 'eksenel_dilim': False},
        kaynak=(['nokta'], ['neutron', 'photon']),
        guc=[], tukenme=False, parca=(False, False, False)),
}
# pwr_tukenme, pwr_pinhucre ile ayni geometridir (tukenme bolumu eklenmis)
KAHIN["pwr_tukenme"] = copy.deepcopy(KAHIN["pwr_pinhucre"])


def test_kahin_tablosu():
    print("\n[U1] UYGUNLUK KAHIN TABLOSU: 27 ornek x butun sorular")
    from cekirdek import tarama
    u = _u()
    kontrol("kahin 12 tarama turunun hepsini kapsiyor (tarama.TURLER sirasi)",
            tuple(tarama.TURLER) == TURLER, "(%s)" % list(tarama.TURLER))
    orn = sorted(os.path.splitext(a)[0] for a in os.listdir(ORNEK) if a.endswith(".json"))
    kontrol("kahin 27 ornegin hepsini kapsiyor", orn == sorted(KAHIN), "(%s)" % orn)

    for ad in sorted(KAHIN):
        k = KAHIN[ad]
        s = _yukle(ad)

        def bak(baslik, gercek, beklenen):
            kontrol("%s: %s" % (ad, baslik), gercek == beklenen,
                    "" if gercek == beklenen else "-> %r (beklenen %r)" % (gercek, beklenen))

        bak("model_ozeti", _g(u.model_ozeti, s), k["ozet"])
        bak("malzeme_rolleri", _g(u.malzeme_rolleri, s), k["roller"])
        bak("gecerli_sekmeler", _g(u.gecerli_sekmeler, s), k["sekmeler"])
        for t in TURLER:
            bak("hedef %s" % t, _g(u.gecerli_hedefler, s, t), k["hedefler"][t])
        bak("gecerli_taramalar (katsayi)", _g(u.gecerli_taramalar, s),
            [t for t in TURLER if k["hedefler"][t]])
        bak("gecerli_taramalar (kritik)", _g(u.gecerli_taramalar, s, "kritik"), k["kritik"])
        bak("sinir_secenekleri yan/alt/ust",
            tuple(_g(u.sinir_secenekleri, s, y) for y in ("yan", "alt", "ust")), k["sinir"])
        bak("ayar_alanlari", _g(u.ayar_alanlari, s), k["ayar"])
        ks = _g(u.kaynak_secenekleri, s)
        bak("kaynak_secenekleri",
            (ks.get("turler"), ks.get("parcaciklar")) if isinstance(ks, dict) else ks,
            k["kaynak"])
        bak("guc_cubuklari", _g(u.guc_cubuklari, s), k["guc"])
        tu = _g(u.tukenme_uygun, s)
        bak("tukenme_uygun", tu[0] if isinstance(tu, tuple) else tu, k["tukenme"])
        pt = _g(u.parca_turleri, s)
        bak("parca_turleri",
            (pt.get("cubuk"), pt.get("plaka"), pt.get("kontrol_cubugu"))
            if isinstance(pt, dict) else pt, k["parca"])

    # denetim raporunun sayilari: pwr_17x17'de 12 taramanin 8'i gecerli,
    # 20 malzeme hedefinden (5 malzeme turu x 4 malzeme) yalnizca 5'i.
    s = _yukle("pwr_17x17")
    kontrol("pwr_17x17: 12 taramadan 8'i gecerli", len(_g(u.gecerli_taramalar, s)) == 8)
    malz = ("yakit_sicaklik", "sogutucu_sicaklik", "void_orani", "bor_ppm", "zenginlik")
    kontrol("pwr_17x17: 20 malzeme hedefinden 5'i gecerli",
            sum(len(_g(u.gecerli_hedefler, s, t)) for t in malz) == 5)
    # kritik arama: yalnizca denetim parametreleri ve katsayi listesinin alt kumesi
    for ad in sorted(KAHIN):
        s = _yukle(ad)
        kr, ka = _g(u.gecerli_taramalar, s, "kritik"), _g(u.gecerli_taramalar, s)
        kontrol("%s: kritik arama yalnizca denetim parametreleri ve gecerli taramalar" % ad,
                isinstance(kr, list) and isinstance(ka, list)
                and all(t in u.KRITIK_PARAMETRELER and t in ka for t in kr))


# ----------------------------------------------------------------------------
# [U2] OLCUM: sunulan her hedef modeli degistirir
# ----------------------------------------------------------------------------

def _parmak_izi(spec):
    """Geometri + geometrideki malzemelerin XML'i (kullanilmayan malzemeler haric)."""
    from cekirdek import kurucu
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model, _ = kurucu.kur(spec)
    parca = [ET.tostring(model.geometry.to_xml_element())]
    mats = model.geometry.get_all_materials()
    for i in sorted(mats):
        parca.append(ET.tostring(mats[i].to_xml_element()))
    return b"".join(parca)


def _adaylar(spec, tur):
    """Naif aday listesi: tarama hedef turune uyan HER sey (ilk surumun sundugu)."""
    from cekirdek import tarama
    ht = tarama.TURLER[tur][1]
    if ht == "malzeme":
        return [m["ad"] for m in spec["malzemeler"]]
    if ht == "demet":
        return [d["ad"] for d in spec["demetler"]]
    if ht == "kontrol_cubugu":
        return [c["ad"] for c in spec["cubuklar"]]
    if ht == "cubuk_bolge":
        return [(c["ad"], i) for c in spec["cubuklar"]
                for i in range(len(c["bolgeler"]) - 1)]
    return [None]


def _deger(spec, tur, hedef):
    """Mevcut degerden FARKLI, fiziksel olarak gecerli bir deger."""
    from cekirdek import sema
    if tur in ("yakit_sicaklik", "sogutucu_sicaklik"):
        return float(sema.malzeme_bul(spec, hedef).get("sicaklik") or 300.0) + 37.0
    if tur == "malzeme_yogunluk":
        return sema.malzeme_bul(spec, hedef)["yogunluk"]["deger"] * 0.9
    if tur == "void_orani":
        return 20.0
    if tur == "bor_ppm":
        return 700.0
    if tur == "zenginlik":
        return 2.1
    if tur == "kafes_adim":
        return sema.demet_bul(spec, hedef)["adim"] * 1.1
    if tur == "kor_adim":
        return spec["kor"]["adim"] * 1.1
    if tur == "cubuk_daldirma":
        return 50.0
    if tur == "cubuk_yaricap":
        c = sema.cubuk_bul(spec, hedef[0])
        i = hedef[1]
        r0 = c["bolgeler"][i - 1]["r"] if i > 0 else 0.0
        return 0.5 * (r0 + c["bolgeler"][i]["r"])
    if tur == "tambur_donme":
        return float((spec["kor"].get("tambur") or {}).get("donme") or 0.0) + 30.0
    if tur == "yansitici_kalinlik":
        return float((spec["kor"].get("yansitici") or {}).get("kalinlik") or 10.0) + 3.0
    raise ValueError(tur)


def test_sunulan_hedef_modeli_degistirir(gecici=None):
    """
    Ilk surum pwr_kontrol'de kilavuz_boru yaricaplarini (kafeste yok), sfr'de
    b4c yogunlugunu ve emici_cubuk yaricaplarini (anahtarda var, haritada yok)
    sunuyordu: bu taramalar modeli HIC degistirmez, egim gurultudur.
    """
    print("\n[U2] OLCUM: sunulan her (tarama, hedef) kurulan modeli degistirir")
    from cekirdek import tarama
    u = _u()
    for ad in sorted(KAHIN):
        s = _yukle(ad)
        taban = _parmak_izi(s)
        sorun, sayi = [], 0
        for tur in TURLER:
            sunulan = _g(u.gecerli_hedefler, s, tur)
            if isinstance(sunulan, _Istisna):
                sorun.append((tur, repr(sunulan)))
                continue
            for h in _adaylar(s, tur):
                sayi += 1
                try:
                    yeni, _n = tarama.parametre_uygula(s, tur, h, _deger(s, tur, h), taban=s)
                    durum = "degisti" if _parmak_izi(yeni) != taban else "degismedi"
                except Exception as e:     # noqa: BLE001
                    durum = "kurulamadi (%s)" % type(e).__name__
                if h in sunulan and durum != "degisti":
                    sorun.append((tur, h, durum))
        kontrol("%s: %d adayda sunulan her hedef modeli degistiriyor" % (ad, sayi),
                not sorun, "-> %s" % sorun if sorun else "")

    # Denetim iddiasi: kor_adim kurucunun okumadigi turlerde bos islemdir.
    for ad, bos in (("pwr_17x17", True), ("sfr_altigen", True), ("mtr_plaka", True),
                    ("godiva_kriter", True), ("zirh_kure", True), ("tamburlu_kor", True),
                    ("pwr_pinhucre", False)):
        s = _yukle(ad)
        yeni, _n = tarama.parametre_uygula(s, "kor_adim", None, 1.5, taban=s)
        ayni = _parmak_izi(yeni) == _parmak_izi(s)
        kontrol("%s: kor_adim %s (olculdu) ve %s" % (
            ad, "modeli degistirmiyor" if bos else "modeli degistiriyor",
            "sunulmuyor" if bos else "sunuluyor"),
            ayni == bos and (_g(u.gecerli_hedefler, s, "kor_adim") == ([] if bos else [None])))


# ----------------------------------------------------------------------------
# [U3] MALZEME ROLLERI
# ----------------------------------------------------------------------------

KUTUPHANE_ROLLERI = {
    "uo2": {"yakit"}, "un": {"yakit"}, "u10mo": {"yakit"}, "mox": {"yakit"},
    "u3si2_al": {"yakit"},
    "zirkaloy4": {"yapisal"}, "ss316": {"yapisal"}, "ma956": {"yapisal"},
    "fecral": {"yapisal"}, "sic": {"yapisal"}, "al6061": {"yapisal"},
    "su": SM, "agir_su": SM, "lbe": {"sogutucu"}, "sodyum": {"sogutucu"},
    "helyum": {"gaz"}, "grafit": {"moderator"}, "berilyum": {"moderator"},
    "b4c": {"emici"}, "gd2o3": {"emici"}, "agincd": {"emici"},
}


def _rol(malzeme):
    """Tek malzemelik bir spec uzerinden rol (sozlesme fonksiyonu malzeme_rolleri)."""
    return _u().malzeme_rolleri({"malzemeler": [malzeme]}).get(malzeme["ad"])


def test_kutuphane_rolleri():
    print("\n[U3] MALZEME ROLLERI: kutuphanenin tamami ve sinir durumlari")
    from cekirdek import malzeme_kutup as mk
    from cekirdek import sema
    kontrol("kutuphanedeki her malzemenin beklenen rolu yazili",
            set(mk.KUTUPHANE) == set(KUTUPHANE_ROLLERI),
            "(eksik: %s)" % sorted(set(mk.KUTUPHANE) ^ set(KUTUPHANE_ROLLERI)))
    for anahtar in sorted(mk.KUTUPHANE):
        m = mk.uret(anahtar)
        r = _g(_rol, m)
        kontrol("kutuphane %-10s -> %s" % (anahtar, sorted(KUTUPHANE_ROLLERI.get(anahtar, ()))),
                r == KUTUPHANE_ROLLERI.get(anahtar), "-> %r" % (r,))
    # kutuphane varyantlari
    for baslik, m, beklenen in (
            ("borlu su 1500 ppm: sogutucu+moderator, emici DEGIL",
             mk.su(sicaklik=580.0, bor_ppm=1500.0), SM),
            ("B4C %90 B10 (nuklid bazli)", mk.b4c(b10_zenginlik=90.0), {"emici"}),
            ("sicak LBE", mk.lbe(sicaklik=900.0), {"sogutucu"})):
        r = _g(_rol, m)
        kontrol("kutuphane varyanti: %s" % baslik, r == beklenen, "-> %r" % (r,))

    B, M = sema.bilesen, sema.malzeme
    ornekler = [
        # (baslik, malzeme, beklenen) -- ilk surumu yanlis olanlar isaretli (*)
        ("(*) 1 ppm B'li grafit hala grafit (eser B emici yapmaz)",
         M("g", [B("C", 99.9999, birim="wo"), B("B", 1.0e-4, birim="wo")], 1.7),
         {"moderator"}),
        ("eser Hf'li zirkaloy yapisal",
         M("z", [B("Zr", 98.2, birim="wo"), B("Sn", 1.45, birim="wo"),
                 B("Fe", 0.21, birim="wo"), B("Cr", 0.11, birim="wo"),
                 B("Hf", 0.01, birim="wo")], 6.55), {"yapisal"}),
        ("(*) Dy2TiO5 (VVER emicisi)", M("d", [B("Dy", 2), B("Ti", 1), B("O", 5)], 7.0),
         {"emici"}),
        ("(*) %2 borlu celik", M("bc", [B("Fe", 98.0, birim="wo"), B("B", 2.0, birim="wo")], 7.7),
         {"emici"}),
        ("(*) polietilen", M("pe", [B("C", 1), B("H", 2)], 0.94), {"moderator"}),
        ("ZrH1.6", M("zrh", [B("Zr", 1), B("H", 1.6)], 5.6), {"moderator"}),
        ("U-ZrH (TRIGA yakiti) yalnizca yakit",
         M("uzrh", [B("U", 8.5, birim="wo", zenginlik=19.75), B("Zr", 89.9, birim="wo"),
                    B("H", 1.6, birim="wo")], 6.0), {"yakit"}),
        ("(*) CO2 (AGR sogutucusu) moderator degil",
         M("co2", [B("C", 1), B("O", 2)], 0.04), {"sogutucu"}),
        ("(*) atom/b-cm cinsinden helyum gaz",
         M("he", [B("He", 1)], 2.7e-5, birim="atom/b-cm"), {"gaz"}),
        ("atom/b-cm cinsinden HEU gaz degil",
         M("heu", [B("U235", 0.045, tur="nuklid"), B("U238", 0.0027, tur="nuklid")],
           0.048, birim="atom/b-cm"), {"yakit"}),
        ("NaK", M("nak", [B("Na", 22.0, birim="wo"), B("K", 78.0, birim="wo")], 0.85),
         {"sogutucu"}),
        ("saf kursun", M("pb", [B("Pb", 1)], 10.5), {"sogutucu"}),
        ("hafniyum", M("hf", [B("Hf", 1)], 13.3), {"emici"}),
        ("Gd157 nuklidiyle zenginlestirilmis Gd2O3",
         M("gd", [B("Gd157", 2, tur="nuklid"), B("O", 3)], 7.4), {"emici"}),
        ("BeO", M("beo", [B("Be", 1), B("O", 1)], 3.0), {"moderator"}),
        ("agir su (nuklid H2/H1)", mk.agir_su(), SM),
    ]
    for baslik, m, beklenen in ornekler:
        r = _g(_rol, m)
        kontrol("rol: %s" % baslik, r == beklenen, "-> %r" % (r,))
    kontrol("rol_malzemeleri spec sirasiyla ve kullanilmasa da listeler",
            _g(_u().rol_malzemeleri, _yukle("sfr_altigen"), "emici") == ["b4c"])


# ----------------------------------------------------------------------------
# [U4] SENTETIK MODELLER
# ----------------------------------------------------------------------------

def _agir_sulu_pin():
    from cekirdek import malzeme_kutup as mk
    s = _yukle("pwr_pinhucre")
    s["malzemeler"] = [m if m["ad"] != "su" else mk.agir_su(ad="su")
                       for m in s["malzemeler"]]
    return s


def _yedek_demetli():
    """pwr_17x17 + TANIMLI ama kullanilmayan bir kafes ve onun yakit cubugu."""
    from cekirdek import sema
    s = _yukle("pwr_17x17")
    s["cubuklar"].append(sema.cubuk("yedek_cubugu", [sema.bolge(0.40, "uo2"),
                                                     sema.bolge(0.47, "zirkaloy4"),
                                                     sema.bolge(None, "su")]))
    s["demetler"].append(sema.demet("yedek", 1.26, [2, 2], ["yy", "yy"],
                                    {"y": "yedek_cubugu"}, "su"))
    return s


def _kafesli_tamburlu(dolgu_kafes=True):
    from cekirdek import sema
    s = _yukle("tamburlu_kor")
    s["cubuklar"].append(sema.cubuk("tc", [sema.bolge(0.40, "u10mo"),
                                           sema.bolge(None, "berilyum")]))
    s["demetler"].append(sema.demet("td", 1.0, [3, 3], ["yyy", "yyy", "yyy"],
                                    {"y": "tc"}, "u10mo"))
    if dolgu_kafes:
        s["kor"]["dolgu"] = "td"
    return s


def _cubuk_kafesli_kor():
    """kare_kafes: kor haritasi DOGRUDAN cubuklara isaret ediyor (demet yok)."""
    s = _yukle("pwr_pinhucre")
    s["kor"].update(tur="kare_kafes", cubuk=None, adim=1.26, boyut=[2, 2],
                    harita=["yy", "yy"], anahtar={"y": "yakit_cubugu"})
    return s


def test_sentetik_kurallar():
    print("\n[U4] SENTETIK MODELLER: orneklerde gorunmeyen kurallar")
    from cekirdek import sema, tarama
    u = _u()

    # a) agir su: tarama hafif su korelasyonunu uygular -> sicaklik ve bor yok
    s = _agir_sulu_pin()
    m = sema.malzeme_bul(s, "su")
    yeni, _n = tarama.parametre_uygula(s, "sogutucu_sicaklik", "su", m["sicaklik"], taban=s)
    rho0, rho1 = m["yogunluk"]["deger"], sema.malzeme_bul(yeni, "su")["yogunluk"]["deger"]
    kontrol("a) (kanit) tarama agir suya hafif su tablosu uyguluyor: ayni sicaklikta "
            "yogunluk %%%.1f dusuyor" % (100 * (1 - rho1 / rho0)), rho1 < 0.95 * rho0,
            "(%.4f -> %.4f g/cm3)" % (rho0, rho1))
    kontrol("a) agir su: sogutucu_sicaklik SUNULMUYOR",
            _g(u.gecerli_hedefler, s, "sogutucu_sicaklik") == [])
    kontrol("a) agir su: bor_ppm SUNULMUYOR (hafif suya donerdi)",
            _g(u.gecerli_hedefler, s, "bor_ppm") == [])
    kontrol("a) agir su: void_orani sunuluyor (rho0*(1-a), birimden bagimsiz)",
            _g(u.gecerli_hedefler, s, "void_orani") == ["su"])

    # b) tanimli ama kullanilmayan kafes ve cubuk
    s = _yedek_demetli()
    kontrol("b) kullanilmayan kafes kafes_adim'da yok",
            _g(u.gecerli_hedefler, s, "kafes_adim") == ["demet_17x17"])
    kontrol("b) kullanilmayan kafesteki yakit cubugu guc hedefi degil",
            _g(u.guc_cubuklari, s) == ["yakit_cubugu"])
    kontrol("b) kullanilmayan cubugun yaricapi sunulmuyor",
            not any(h[0] == "yedek_cubugu"
                    for h in _g(u.gecerli_hedefler, s, "cubuk_yaricap") or []))
    geo = _gu("geometri_icerigi", s)
    kontrol("b) geometri_icerigi kullanilmayan kafesi ve cubugu disarida birakiyor",
            isinstance(geo, dict) and geo.get("demet") == {"demet_17x17"}
            and geo.get("cubuk") == {"yakit_cubugu", "kilavuz_boru"}
            and geo.get("kafesteki_cubuk") == {"yakit_cubugu", "kilavuz_boru"})

    # c) tanimli ama yerlestirilmemis kontrol cubugu (3B)
    s = _yukle("pwr_3b")
    s["malzemeler"].append(sema.malzeme("b4c", [sema.bilesen("B", 4), sema.bilesen("C", 1)], 2.52))
    s["cubuklar"].append(sema.kontrol_cubugu("kc", [sema.bolge(0.43, "b4c"),
                                                    sema.bolge(None, "su")], "su"))
    kontrol("c) yerlestirilmemis kontrol cubugu: daldirma sunulmuyor",
            _g(u.gecerli_hedefler, s, "cubuk_daldirma") == [])
    kontrol("c) model_ozeti kontrol_cubugu = False",
            (_g(u.model_ozeti, s) or {}).get("kontrol_cubugu") is False)
    kontrol("c) yalnizca o cubukta kullanilan b4c yogunluk hedefi degil",
            "b4c" not in (_g(u.gecerli_hedefler, s, "malzeme_yogunluk") or []))
    s["demetler"][0]["anahtar"]["k"] = "kc"
    kontrol("c) haritaya konunca daldirma sunuluyor",
            _g(u.gecerli_hedefler, s, "cubuk_daldirma") == ["kc"])
    s["kor"]["yukseklik"] = None
    kontrol("c) 2B'de daldirma sunulmuyor",
            _g(u.gecerli_hedefler, s, "cubuk_daldirma") == [])

    # d) tamburlu kor: guc dagilimi yalnizca dolgu KAFES ise
    s = _kafesli_tamburlu(True)
    kontrol("d) tamburlu + kafes dolgu: guc cubugu var",
            _g(u.guc_cubuklari, s) == ["tc"])
    kontrol("d) tamburlu + kafes dolgu: kafes_adim sunuluyor",
            _g(u.gecerli_hedefler, s, "kafes_adim") == ["td"])
    aa = _g(u.ayar_alanlari, s) or {}
    kontrol("d) tamburlu + kafes dolgu (3B): guc ve eksenel dilim acik",
            aa.get("guc_dagilimi") is True and aa.get("eksenel_dilim") is True)
    s = _kafesli_tamburlu(False)
    kontrol("d) tamburlu + malzeme dolgu: tanimli kafes olsa da guc yok",
            _g(u.guc_cubuklari, s) == [])
    kontrol("d) tamburlu + malzeme dolgu: tanimli kafesin adimi sunulmuyor",
            _g(u.gecerli_hedefler, s, "kafes_adim") == [])

    # e) yansitici
    s = _yukle("tamburlu_kor")
    s["kor"]["yansitici"]["malzeme"] = None
    kontrol("e) bosluk yansiticinin kalinligi sunulmuyor",
            _g(u.gecerli_hedefler, s, "yansitici_kalinlik") == [])
    s = _yukle("pwr_17x17")
    s["kor"]["yansitici"]["var"] = True
    kontrol("e) tek_demet + su yansitici: kalinlik sunuluyor",
            _g(u.gecerli_hedefler, s, "yansitici_kalinlik") == [None])
    s = _yukle("pwr_pinhucre")
    s["kor"]["yansitici"].update(var=True, malzeme="su")
    kontrol("e) tek_cubuk yansiticiyi kurmaz: kalinlik sunulmuyor",
            _g(u.gecerli_hedefler, s, "yansitici_kalinlik") == [])

    # f) ozdeger modu ama fisil malzeme yok
    s = _yukle("zirh_kure")
    s["ayarlar"]["mod"] = "eigenvalue"
    kontrol("f) fisilsiz ozdeger: analiz ve tukenme sekmesi yok",
            _g(u.gecerli_sekmeler, s) == ["malzemeler", "kor", "ayarlar", "calistir"])
    kontrol("f) fisilsiz ozdeger: hicbir tarama yok",
            _g(u.gecerli_taramalar, s) == [] and _g(u.gecerli_hedefler, s, "sogutucu_sicaklik") == [])
    tu = _g(u.tukenme_uygun, s)
    kontrol("f) fisilsiz ozdeger: tukenme uygun degil, sebep fisil",
            isinstance(tu, tuple) and tu[0] is False and "fisil" in tu[1])
    kontrol("f) fisilsiz: kutu kaynagi ve kinetik sunulmuyor",
            (_g(u.kaynak_secenekleri, s) or {}).get("turler") == ["nokta"]
            and (_g(u.ayar_alanlari, s) or {}).get("kinetik") is False)

    # g) yakit tanimli ama geometride yok
    s = _yukle("pwr_pinhucre")
    s["cubuklar"].append(sema.cubuk("bos_cubuk", [sema.bolge(0.45, "zirkaloy"),
                                                  sema.bolge(None, "su")]))
    s["kor"]["cubuk"] = "bos_cubuk"
    kontrol("g) yakit geometride yok: fisil = False",
            (_g(u.model_ozeti, s) or {}).get("fisil") is False)
    kontrol("g) yakit geometride yok: tukenme ve analiz yok",
            (_g(u.tukenme_uygun, s) or (None,))[0] is False
            and "analiz" not in (_g(u.gecerli_sekmeler, s) or ["analiz"]))

    # h) zenginlik yalnizca U ELEMENTINDE
    s = _yukle("pwr_pinhucre")
    for b in sema.malzeme_bul(s, "uo2")["bilesim"]:
        if b["isim"] == "U":
            b.pop("zenginlik", None)
        else:
            b["zenginlik"] = 4.0
    kontrol("h) zenginlik O elementindeyse zenginlik taramasi sunulmuyor",
            _g(u.gecerli_hedefler, s, "zenginlik") == [])

    # i) kare_kafes: cubuklar dogrudan kor haritasinda
    s = _cubuk_kafesli_kor()
    kontrol("i) kor haritasindaki cubuk da tekrarlanir: guc hedefi",
            _g(u.guc_cubuklari, s) == ["yakit_cubugu"])
    kontrol("i) kare_kafes: kor_adim sunuluyor, periodic secilebilir",
            _g(u.gecerli_hedefler, s, "kor_adim") == [None]
            and "periodic" in (_g(u.sinir_secenekleri, s, "yan") or []))

    # j) eksenel: aktif katmana kendi dolgusu verilince ana kafes geometriden cikar
    s = _yukle("pwr_eksenel")
    for b in s["kor"]["eksenel"]["bolgeler"]:
        if b["ad"] == "aktif yakıt":
            b["dolgu"] = "demet_blanket"
    kontrol("j) ana dolgu hicbir katmanda yok: demet_17x17 sunulmuyor",
            _g(u.gecerli_hedefler, s, "kafes_adim") == ["demet_blanket", "demet_plenum"])
    kontrol("j) ... yakit_cubugu guc hedefi degil, uo2 yakit sicakligi hedefi degil",
            _g(u.guc_cubuklari, s) == ["blanket_cubugu"]
            and _g(u.gecerli_hedefler, s, "yakit_sicaklik") == ["uo2_dogal"])

    # k) kare_kafes + katmana ozel anahtar
    s = _yukle("pwr_eksenel")
    s["kor"].update(tur="kare_kafes", demet=None, adim=21.42, boyut=[1, 1],
                    harita=["a"], anahtar={"a": "demet_17x17"})
    s["kor"]["eksenel"]["bolgeler"] = [
        sema.eksenel_bolge("alt", 20.0, anahtar={"a": "demet_blanket"}),
        sema.eksenel_bolge("aktif", 300.0)]
    kontrol("k) kare_kafes katman anahtari: iki kafes de geometride",
            _g(u.gecerli_hedefler, s, "kafes_adim") == ["demet_17x17", "demet_blanket"])

    # l) sabit kaynak + fisil (alt kritik): guc dagilimi moddan bagimsiz
    s = _yukle("pwr_17x17")
    s["ayarlar"]["mod"] = "fixed source"
    aa = _g(u.ayar_alanlari, s) or {}
    kontrol("l) sabit kaynak + fisil: guc ve kutu var; pasif/entropi/kinetik yok; foton var",
            aa.get("guc_dagilimi") is True and aa.get("kutu_kaynagi") is True
            and not aa.get("pasif") and not aa.get("entropi") and not aa.get("kinetik")
            and aa.get("foton") is True)
    kontrol("l) sabit kaynak: analiz ve tukenme yok",
            _g(u.gecerli_sekmeler, s) == ["malzemeler", "parcalar", "demet", "kor",
                                          "ayarlar", "calistir"])

    # m) ortak kor alanlari ve yan yuzey
    ko = _gu("kor_ortak_alanlari", _yukle("godiva_kriter"))
    kontrol("m) kurede yukseklik/eksenel/alt/ust yok",
            ko == {"yukseklik": False, "eksenel": False, "sinir_yan": True,
                   "sinir_alt": False, "sinir_ust": False}, "-> %r" % (ko,))
    ko = _gu("kor_ortak_alanlari", _yukle("pwr_17x17"))
    kontrol("m) 2B tek_demet: yukseklik var, alt/ust yok",
            ko == {"yukseklik": True, "eksenel": True, "sinir_yan": True,
                   "sinir_alt": False, "sinir_ust": False}, "-> %r" % (ko,))
    beklenen = {"godiva_kriter": "kure", "tamburlu_kor": "silindir", "sfr_altigen": "altigen",
                "pwr_17x17": "kare", "mtr_plaka": "kare", "pwr_pinhucre": "kare"}
    kontrol("m) yan_yuzey kurucunun kurdugu yuzey",
            {a: _gu("yan_yuzey", _yukle(a)) for a in beklenen} == beklenen)

    # n) bozuk / yarim modellerde cokmez, dongude takilmaz
    kontrol("n) bos yeni model: yalnizca kurulum sekmeleri",
            _g(u.gecerli_sekmeler, sema.yeni_spec()) ==
            ["malzemeler", "parcalar", "kor", "ayarlar", "calistir"])
    dongu = _yukle("pwr_17x17")
    dongu["demetler"][0]["anahtar"]["k"] = "demet_17x17"       # kendini iceren kafes
    kontrol("n) kendini iceren kafes: sonsuz dongu yok",
            isinstance(_g(u.gecerli_taramalar, dongu), list))
    kontrol("n) bos sozluk spec: cokmez",
            all(not isinstance(_g(f, {}), _Istisna)
                for f in (u.model_ozeti, u.gecerli_sekmeler, u.ayar_alanlari,
                          u.guc_cubuklari, u.gecerli_taramalar)))


# ----------------------------------------------------------------------------
# [U5] DOGRULA ILE UYUM ve elle yazilmis dosyalar icin yeni bulgular
# ----------------------------------------------------------------------------

def _bul(spec, seviye, parca, fn=None):
    from cekirdek import dogrula
    b = fn(spec) if fn else dogrula.tum_kontroller(spec, veri_kontrolu=False)
    return [x for x in b if (seviye is None or x.seviye == seviye)
            and parca.lower() in x.mesaj.lower()]


def test_dogrula_uyumu():
    print("\n[U5] DOGRULA: arayuzun sundugu = dogrulamanin kabul ettigi")
    from cekirdek import dogrula
    u = _u()
    for ad in sorted(KAHIN):
        s = _yukle(ad)
        # ornegin kendi ayarlari sunulan secenekler icinde
        kor = s["kor"]
        yan_ok = kor["sinir"]["yan"] in (_g(u.sinir_secenekleri, s, "yan") or [])
        ks = _g(u.kaynak_secenekleri, s) or {}
        k = s["ayarlar"]["kaynak"]
        kaynak_ok = (k.get("tur", "nokta") in ks.get("turler", [])
                     and (k.get("parcacik") or "neutron") in ks.get("parcaciklar", []))
        g = s.get("guc_dagilimi") or {}
        from cekirdek import sema as _sema
        guc_ok = not g.get("var") or all(
            h["cubuk"] in (_g(u.guc_cubuklari, s) or []) for h in _sema.guc_hedefleri(g))
        t = s.get("tukenme") or {}
        tuk_ok = not t.get("var") or (_g(u.tukenme_uygun, s) or (False,))[0]
        kontrol("%s: dosyadaki sinir/kaynak/guc/tukenme sunulan secenekler icinde" % ad,
                yan_ok and kaynak_ok and guc_ok and tuk_ok)

        # sunulan her yan/alt/ust sinir dogrulamadan sinir HATASIZ gecer;
        # gecerli adli ama sunulmayan her yan sinir HATA verir
        sorun = []
        for yon in ("yan", "alt", "ust"):
            secenek = _g(u.sinir_secenekleri, s, yon) or []
            for bc in ("reflective", "vacuum", "white", "periodic"):
                if yon != "yan" and not secenek:
                    continue
                x = copy.deepcopy(s)
                x["kor"]["sinir"][yon] = bc
                if yon != "yan" and bc == "periodic":
                    continue                     # ayrica sinanir (tek/cift tarafli)
                hatalar = [b for b in dogrula.kor_kontrol(x) if b.seviye == "hata"
                           and ("periodic" in b.mesaj or "sınır" in b.mesaj.lower())]
                if (bc in secenek) == bool(hatalar):
                    sorun.append((yon, bc, [b.mesaj[:50] for b in hatalar]))
        kontrol("%s: sunulan sinir <=> sinir hatasi yok" % ad, not sorun,
                "-> %s" % sorun if sorun else "")

        # guc: uygun cubuklarda guc hatasi yok, digerlerinde bir bulgu var
        sorun = []
        uygun = _g(u.guc_cubuklari, s) or []
        yakit_malz = {ad for ad, rol in (_g(u.malzeme_rolleri, s) or {}).items()
                      if "yakit" in rol}
        for c in s["cubuklar"]:
            x = copy.deepcopy(s)
            # merkez deligi gazli cubuklarda (VVER) ilk fisil bolge secilir
            bolge = next((i for i, r in enumerate(c.get("bolgeler") or [])
                          if r.get("malzeme") in yakit_malz), 0)
            x["guc_dagilimi"].update(var=True, cubuk=c["ad"], bolge=bolge)
            b = [y for y in dogrula.guc_dagilimi_kontrol(x) if y.seviye in ("hata", "uyari")
                 and ("demet" in y.mesaj or "kullanılmıyor" in y.mesaj
                      or "fisil" in y.mesaj)]
            if c["ad"] in uygun:
                # cok demetli korlarda cubuk yalniz bazi demetlerdedir (BEAVRS,
                # SMR, SFR): hedef listesine digerleri eklenir. Bu yalnizca bir
                # kapsama UYARISIDIR, cubuk yine gecerli bir guc hedefidir.
                b = [y for y in b if "içermeyen demetler var" not in y.mesaj]
            if (c["ad"] in uygun) == bool(b):
                sorun.append((c["ad"], [y.mesaj[:50] for y in b]))
        kontrol("%s: guc_cubuklari <=> guc bulgusu yok" % ad, not sorun,
                "-> %s" % sorun if sorun else "")

        # kaynak turu: sunulan kutu hatasiz, sunulmayan kutu HATA
        x = copy.deepcopy(s)
        x["ayarlar"]["kaynak"]["tur"] = "kutu"
        h = _bul(x, "hata", "kutu kaynağı fisil")
        kontrol("%s: kutu kaynagi sunuluyor <=> hata yok" % ad,
                ("kutu" in ks.get("turler", [])) != bool(h))


def test_dogrula_yeni_bulgular():
    print("\n[U6] DOGRULA: elle yazilmis dosyalarin yeni yakalanan ihlalleri")
    from cekirdek import sema, dogrula

    # 1) alt/ust periodic: tek tarafli HATA (OpenMC durur -- olculdu), cift tarafli UYARI
    s = _yukle("pwr_3b")
    s["kor"]["sinir"].update(alt="periodic", ust="vacuum")
    kontrol("1) 3B tek tarafli periodic alt -> HATA", bool(_bul(s, "hata", "periodic")))
    s["kor"]["sinir"].update(ust="periodic")
    kontrol("1) alt+ust periodic -> UYARI, hata degil",
            bool(_bul(s, "uyari", "periodic")) and not _bul(s, "hata", "periodic"))

    # 2) 2B modelde alt/ust yok sayilir
    s = _yukle("pwr_17x17")
    s["kor"]["sinir"]["alt"] = "vacuum"
    kontrol("2) 2B + alt vacuum -> BILGI 'yok sayılır'", bool(_bul(s, "bilgi", "yok sayılır")))
    kontrol("2) kure: alt/ust vacuum icin bilgi yok (godiva)",
            not _bul(_yukle("godiva_kriter"), None, "sınır koşulu ("))

    # 3) altigen periodic GECERLI (olculdu: reflective ile ayni k)
    s = _yukle("sfr_altigen")
    s["kor"]["sinir"]["yan"] = "periodic"
    kontrol("3) altigen + periodic hata degil", not _bul(s, "hata", "periodic"))

    # 4) guc: kullanilmayan kafesteki cubuk -> HATA (kurucu durur)
    s = _yedek_demetli()
    s["guc_dagilimi"].update(var=True, cubuk="yedek_cubugu", bolge=0)
    kontrol("4) guc hedefi kullanilmayan kafeste -> HATA 'kullanilmiyor'",
            bool(_bul(s, "hata", "modelde kullanılmıyor")))

    # 5) guc: tamburlu malzeme dolgu + tanimli cubuk
    s = _kafesli_tamburlu(False)
    s["guc_dagilimi"].update(var=True, cubuk="tc", bolge=0)
    kontrol("5) tamburlu (malzeme dolgu) guc -> HATA", bool(_bul(s, "hata", "kullanılmıyor")))

    # 6) fisilsiz kutu kaynagi
    s = _yukle("zirh_kure")
    s["ayarlar"]["kaynak"]["tur"] = "kutu"
    kontrol("6) fisil malzemesiz kutu kaynagi -> HATA",
            bool(_bul(s, "hata", "kutu kaynağı fisil")))

    # 7) fisilsiz ozdeger (OpenMC: "No fission sites banked" -- olculdu)
    s = _yukle("zirh_kure")
    s["ayarlar"]["mod"] = "eigenvalue"
    kontrol("7) fisilsiz ozdeger -> HATA", bool(_bul(s, "hata", "fisil malzeme gerektirir")))

    # 8) tek_cubuk'ta yansitici acik
    s = _yukle("pwr_pinhucre")
    s["kor"]["yansitici"].update(var=True, malzeme="su")
    kontrol("8) tek_cubuk + yansitici.var -> UYARI 'yansıtıcı kurulmaz'",
            bool(_bul(s, "uyari", "yansıtıcı kuşak kurulmaz")))

    # 9) baska kor turunden kalan alan
    s = _yukle("pwr_17x17")
    s["kor"]["tambur"]["sayi"] = 8
    kontrol("9) tek_demet + tambur -> BILGI 'kullanılmayan alanlar'",
            bool(_bul(s, "bilgi", "kullanılmayan alanlar")))

    # 10) kontrol cubugu emicisi: rol uygunluk'tan
    def emici_uyarisi(malzeme):
        s = _yukle("pwr_kontrol")
        s["malzemeler"] = [m for m in s["malzemeler"] if m["ad"] != "b4c"] + [malzeme]
        return bool(_bul(s, "uyari", "emici içermiyor", dogrula.kontrol_cubugu_kontrol))
    B, M = sema.bilesen, sema.malzeme
    kontrol("10) Gd157 nuklidli emici icin yanlis alarm yok",
            not emici_uyarisi(M("b4c", [B("Gd157", 2, tur="nuklid"), B("O", 3)], 7.4)))
    kontrol("10) Dy2TiO5 icin yanlis alarm yok",
            not emici_uyarisi(M("b4c", [B("Dy", 2), B("Ti", 1), B("O", 5)], 7.0)))
    kontrol("10) borlu su kontrol emicisi olarak -> UYARI",
            emici_uyarisi(M("b4c", [B("H", 11.19, birim="wo"), B("O", 88.66, birim="wo"),
                                    B("B", 0.15, birim="wo")], 0.7)))

    # 11) tukenme: yakit geometride yok
    s = _yukle("pwr_tukenme")
    s["cubuklar"].append(sema.cubuk("bos_cubuk", [sema.bolge(0.45, "zirkaloy"),
                                                  sema.bolge(None, "su")]))
    s["kor"]["cubuk"] = "bos_cubuk"
    kontrol("11) tukenme + geometride yakit yok -> HATA 'tukenme yapilamaz'",
            bool(_bul(s, "hata", "tükenme yapılamaz", dogrula.tukenme_kontrol)))

    # 12) ozdegerde kaynak siddeti, 13) sabit kaynakta pasif cevrim
    s = _yukle("pwr_17x17")
    s["ayarlar"]["kaynak"]["kuvvet"] = 1.0e12
    kontrol("12) ozdeger + kaynak siddeti -> BILGI", bool(_bul(s, "bilgi", "kaynak şiddeti")))
    s = _yukle("zirh_kure")
    s["ayarlar"]["pasif"] = 10
    kontrol("13) sabit kaynak + pasif -> BILGI", bool(_bul(s, "bilgi", "pasif çevrim")))


HIZLI = [test_kahin_tablosu, test_kutuphane_rolleri, test_sentetik_kurallar, test_dogrula_uyumu,
         test_dogrula_yeni_bulgular]
YAVAS = [test_sunulan_hedef_modeli_degistirir]
