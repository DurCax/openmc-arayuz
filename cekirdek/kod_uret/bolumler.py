# -*- coding: utf-8 -*-
"""
 kod_uret/bolumler.py  --  betik bolumleri: malzemeler, geometri, ayarlar, kapanis

 Geometri bolumu AYRI bir kod yolu DEGILDIR: cekirdek/geometri/kurulum.py kurucusu
 ayni gezintiyi BetikYapici ile yurutur (R12). Eski ayri betik yolunun
 tamburlu + eksenel hatasi (R-4) ve sinir varsayilani farki (R-5) boylece
 ortadan kalkti.
"""

from cekirdek import sema
from cekirdek.kod_uret.ad import _ad, _f, _bolum, _mat_ifade  # noqa: F401
from cekirdek import kaynak as _kaynak
from cekirdek.kod_uret.tukenme import _tukenme
from cekirdek.kod_uret.spektrum import _spektrum_tallyleri


def _malzemeler(spec, satirlar):
    _bolum(satirlar, 1, "MALZEMELER")
    adlar = []
    for m in spec["malzemeler"]:
        v = _ad(m["ad"])
        adlar.append(v)
        satirlar.append("")
        satirlar.append("%s = openmc.Material(name=%r)" % (v, m.get("gorunen_ad") or m["ad"]))
        for b in m["bilesim"]:
            birim = b.get("birim", "ao")
            if b.get("tur") == "nuklid":
                satirlar.append("%s.add_nuclide(%r, %s, percent_type=%r)"
                                % (v, b["isim"], _f(b["miktar"]), birim))
            elif b.get("zenginlik") is not None:
                satirlar.append("%s.add_element(%r, %s, percent_type=%r, enrichment=%s)"
                                % (v, b["isim"], _f(b["miktar"]), birim, _f(b["zenginlik"])))
            else:
                satirlar.append("%s.add_element(%r, %s, percent_type=%r)"
                                % (v, b["isim"], _f(b["miktar"]), birim))
        yog = m["yogunluk"]
        satirlar.append("%s.set_density(%r, %s)" % (v, yog["birim"], _f(yog["deger"])))
        if m.get("sicaklik"):
            satirlar.append("%s.temperature = %s" % (v, _f(m["sicaklik"])))
        for s in m.get("sab", []):
            satirlar.append("%s.add_s_alpha_beta(%r)      # termal saçılma" % (v, s))
    satirlar.append("")
    satirlar.append("malzemeler = openmc.Materials([%s])" % ", ".join(adlar))
    return adlar


def _ayarlar(spec, satirlar, gx, gy):
    _bolum(satirlar, 3, "AYARLAR")
    a = spec["ayarlar"]
    satirlar.append("")
    satirlar.append("ayar = openmc.Settings()")
    satirlar.append("ayar.run_mode  = %r" % a.get("mod", "eigenvalue"))
    satirlar.append("ayar.particles = %-10s # çevrim başına parçacık" % _f(int(a["parcacik"])))
    satirlar.append("ayar.batches   = %-10s # toplam çevrim" % _f(int(a["cevrim"])))
    if a.get("mod", "eigenvalue") == "eigenvalue":
        satirlar.append("ayar.inactive  = %-10s # pasif çevrim" % _f(int(a["pasif"])))
    if a.get("tohum"):
        satirlar.append("ayar.seed      = %s" % _f(int(a["tohum"])))
    if a.get("sicaklik_yontemi"):
        satirlar.append("ayar.temperature = {'method': %r}" % a["sicaklik_yontemi"])

    k = a.get("kaynak") or {}
    satirlar.append("")
    if k.get("tur") == "kutu":
        # Z araligi modelin yuksekligini kapsamali (bkz. kurucu.py notu):
        # dar bir baslangic kutusu eksenel sekli yanlis yakinsatir.
        # Kutu AKTIF yakit araligini kapsar (kurucu.py ile ayni tanim):
        # yansitici/plenum katmanlarinda orneklenen noktalar zaten reddedilir.
        from cekirdek import geometri as _geo
        _ar = _geo.aktif_aralik(spec)
        _z0, _z1 = _ar if _ar else (-1.0, 1.0)
        # Yanal olcu yansitici HARIC (kurucu.kor_ic_olcusu ile ayni).
        _kx, _ky = _geo.ic_olcusu(_geo.model(spec))
        alt = k.get("alt") or [-_kx / 2, -_ky / 2, _z0]
        ust = k.get("ust") or [+_kx / 2, +_ky / 2, _z1]
        satirlar.append("_uzay = openmc.stats.Box(%r, %r)"
                        % (list(alt), list(ust)))
        satirlar.append("_kisit = {'fissionable': True}   # kaynak yalnızca fisil bölgelerde")
    else:
        satirlar.append("_uzay = openmc.stats.Point(%r)"
                        % (tuple(k.get("konum") or (0.0, 0.0, 0.0)),))
        satirlar.append("_kisit = None")
    satirlar.append("_enerji = %s" % _kaynak.enerji_kod(k.get("enerji")))
    satirlar.append("_aci    = %s" % _kaynak.aci_kod(k.get("aci")))
    satirlar.append("ayar.source = openmc.IndependentSource(space=_uzay,")
    satirlar.append("                                       angle=_aci,")
    satirlar.append("                                       energy=_enerji,")
    satirlar.append("                                       strength=%r,"
                    % float(k.get("kuvvet") or 1.0))
    satirlar.append("                                       particle=%r,"
                    % (k.get("parcacik") or "neutron"))
    satirlar.append("                                       constraints=_kisit)")
    if (k.get("parcacik") or "neutron") == "photon":
        satirlar.append("ayar.photon_transport = True   # foton kaynağı foton taşınımı gerektirir")
    ent = a.get("entropi_mesh") or {}
    if ent.get("var") and a.get("mod", "eigenvalue") == "eigenvalue":
        satirlar.append("")
        satirlar.append("# Shannon entropisi ağı — kaynak yakınsamasını ölçer.")
        satirlar.append("# Entropi pasif çevrimler boyunca kayıyorsa pasif çevrim")
        satirlar.append("# sayısı yetersizdir ve k-eff yanlı çıkar.")
        satirlar.append("_ent_mesh = openmc.RegularMesh()")
        satirlar.append("_ent_mesh.dimension = %r" % (_kaynak.entropi_boyutu(spec),))
        _hz = sema.model_yuksekligi(spec)
        _ez = (_hz / 2.0) if _hz else 1.0e10
        satirlar.append("_ent_mesh.lower_left  = (%s, %s, %s)" % (_f(-gx/2.0), _f(-gy/2.0), _f(-_ez)))
        satirlar.append("_ent_mesh.upper_right = (%s, %s, %s)" % (_f(gx/2.0), _f(gy/2.0), _f(_ez)))
        satirlar.append("ayar.entropy_mesh = _ent_mesh")


def _kapanis(spec, satirlar, renkli):
    _bolum(satirlar, 5, "MODEL VE ÇALIŞTIRMA")
    tallyler = ("tallyler" if (spec.get("tallyler")
                or (spec.get("guc_dagilimi") or {}).get("var"))
                else "openmc.Tallies()")
    satirlar.append("")
    satirlar.append("model = openmc.Model(geometry=geometri, materials=malzemeler,")
    satirlar.append("                     settings=ayar, tallies=%s)" % tallyler)
    kin = spec["ayarlar"].get("kinetik") or {}
    if kin.get("var") and spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        # kurucu.kur ile ayni: onceden betik IFP'yi hic yazmiyordu ve disa
        # aktarilan Godiva beta_eff / notron omru vermiyordu.
        satirlar.append("")
        satirlar.append("# Kinetik parametreler (IFP): etkin gecikmiş nötron kesri (beta_eff)")
        satirlar.append("# ve ortalama nötron nesil süresi. Koşu süresini biraz uzatır.")
        satirlar.append("model.add_kinetics_parameters_tallies()")
        satirlar.append("model.settings.ifp_n_generation = %d" % int(kin.get("nesil") or 10))
    _spektrum_tallyleri(spec, satirlar)          # Y3 (cekirdek/kod_uret/spektrum.py)
    if renkli:
        satirlar.append("")
        satirlar.append("# Model.plot() SVG renk adı ya da (R,G,B) demeti ister — hex dize kabul etmez")
        satirlar.append("renkler = {")
        for m in spec["malzemeler"]:
            if m.get("renk"):
                satirlar.append("    %s: %r," % (_ad(m["ad"]), tuple(m["renk"])))
        satirlar.append("}")
    tukenme_var = _tukenme(spec, satirlar)
    satirlar.append("")
    if tukenme_var:
        satirlar.append("")
    satirlar.append("if __name__ == '__main__':")
    satirlar.append("    import matplotlib.pyplot as plt")
    satirlar.append("")
    satirlar.append("    # --- Önce çiz, sonra çalıştır ---")
    satirlar.append("    # Geometri doğru görünmeden koşu başlatmak zaman kaybıdır.")
    satirlar.append("    for _eksen in ('xy',):")
    satirlar.append("        _ax = model.plot(basis=_eksen, color_by='material',")
    satirlar.append("                         colors=%s pixels=(600, 600))"
                    % ("renkler," if renkli else "None,"))
    satirlar.append("        _ax.get_figure().savefig('geometri_%s.png' % _eksen, dpi=110)")
    satirlar.append("        print('çizildi: geometri_%s.png' % _eksen)")
    satirlar.append("")
    satirlar.append("    # Çizimler doğruysa aşağıdaki satırın yorumunu kaldırın.")
    satirlar.append("    # sp = model.run(threads=%d)" % spec["calistirma"].get("is_parcacigi", 8))
    satirlar.append("    # print(openmc.StatePoint(sp).keff)")
    if tukenme_var:
        satirlar.append("")
        satirlar.append("    # Yanma hesabı (uzun sürer; OMP_NUM_THREADS ortam değişkeniyle")
        satirlar.append("    # iş parçacığı sayısını ayarlayın):")
        satirlar.append("    # tukenme_kos()")


def _geometri(spec, satirlar):
    """
    Geometri bolumu -- kurucu ile AYNI gezinti (geometri.kur.betik).
    DONER (gx, gy, uretilen) -- uretilen: {bilesen adi: betikteki degisken adi}
    (guc dagilimi tally'si hedef cubugun degiskenine ihtiyac duyar).
    """
    from cekirdek.geometri import kurulum as _gk
    _bolum(satirlar, 2, "GEOMETRİ")
    satirlar.append("")
    satirlar.append("# Kurucu ile aynı gezintiden üretildi (cekirdek/geometri/kurulum.py).")
    return _gk.betik(spec, satirlar, _ad, degisken_adi=_ad)
