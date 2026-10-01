# -*- coding: utf-8 -*-
"""
 test_eksenel.py  --  14-16. eksenel heterojenlik, betik esdegerligi + guc korunumu, onizleme

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import copy
import importlib.util
import os

from cekirdek import sema, kurucu, kod_uret
from testler.ortak_test import kontrol
from cekirdek import geometri  # noqa: E402
from cekirdek.geometri import eksenel as geo_eks  # noqa: E402,F401
from testler.regresyon_ortak import ORNEK, _ornek_adlari


# ============================================================================
# 14. EKSENEL HETEROJENLIK
# ============================================================================

def _eksenel_spec():
    """pwr_3b uzerine uc katman: su / aktif / su."""
    spec = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    spec["kor"]["yukseklik"] = None
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt yansitici", 20.0, "su"),
        sema.eksenel_bolge("aktif", 366.0, None),
        sema.eksenel_bolge("ust yansitici", 20.0, "su"),
    ]}
    return spec


def test_eksenel_geometri():
    """
    Katman yigini dogru mu kuruluyor?

    En kritik nokta IC ARAYUZLERIN SINIR KOSULU: ic bir yuzeye yansitici
    sinir konsa korun ustu altindan KOPAR ve bunu k-eff'e bakarak fark etmek
    neredeyse imkansizdir. Bu yuzden her z duzleminin bc'si tek tek okunuyor.
    """
    print("\n[14] EKSENEL GEOMETRI: katman siniri ve sinir kosullari")
    spec = _eksenel_spec()
    h = sema.kor_yuksekligi(spec["kor"])
    kontrol("toplam yukseklik katman toplami (406 cm)", abs(h - 406.0) < 1e-9,
            "-> %g" % h)

    model, _ = kurucu.kur(spec)
    kok = model.geometry.root_universe
    kontrol("kok universe'de 3 katman hucresi var",
            {c.name for c in kok.cells.values()}
            == {"alt yansitici", "aktif", "ust yansitici"},
            "-> %s" % sorted(c.name for c in kok.cells.values()))
    # Fiziksel sira: ad degil z konumu belirleyici
    z_sirali = [c.name for c in sorted(kok.cells.values(),
                                      key=lambda c: c.region.bounding_box[0][2])]
    kontrol("katmanlar ALTTAN USTE dogru sirada",
            z_sirali == ["alt yansitici", "aktif", "ust yansitici"],
            "-> %s" % z_sirali)

    duzlemler = sorted((srf.z0, srf.boundary_type)
                       for srf in model.geometry.get_all_surfaces().values()
                       if srf.type == "z-plane")
    beklenen = [(-203.0, "vacuum"), (-183.0, "transmission"),
                (183.0, "transmission"), (203.0, "vacuum")]
    kontrol("z duzlemleri ve sinir kosullari dogru", duzlemler == beklenen,
            "-> %s" % duzlemler)

    # katman z araliklari
    kutular = sorted((float(c.region.bounding_box[0][2]),
                      float(c.region.bounding_box[1][2]), c.name)
                     for c in kok.cells.values())
    kontrol("katmanlar bitisik ve bosluksuz",
            all(abs(kutular[i][1] - kutular[i + 1][0]) < 1e-9
                for i in range(len(kutular) - 1)),
            "-> %s" % [(a, b) for a, b, _ in kutular])


def test_eksenel_araliklar():
    """
    Uc ayri yuksekligin uc ayri tanimi oldugunu dogrular:
      toplam model / fisil aralik / hedef cubugun araligi
    Bunlari karistirmak iki gercek hataya yol acti (kaynak kutusu 1300 pcm,
    F_q %6 sisme), bu yuzden sayilar teste caktirildi.
    """
    print("\n[14b] EKSENEL ARALIKLAR: toplam / fisil / cubuk ayri ayri")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    kontrol("toplam yukseklik 395 cm",
            abs(sema.kor_yuksekligi(spec["kor"]) - 395.0) < 1e-9)
    ar = geometri.aktif_aralik(spec)
    kontrol("fisil aralik (-177.5, 152.5) -- blanket dahil",
            ar is not None and abs(ar[0] + 177.5) < 1e-9 and abs(ar[1] - 152.5) < 1e-9,
            "-> %s" % (ar,))
    cr = geo_eks.cubuk_araligi(spec, "yakit_cubugu")
    kontrol("yakit_cubugu araligi (-162.5, 137.5) -- blanket HARIC",
            cr is not None and abs(cr[0] + 162.5) < 1e-9 and abs(cr[1] - 137.5) < 1e-9,
            "-> %s" % (cr,))
    kontrol("blanket cubugu blanket katmanlarinda",
            geo_eks.cubuk_araligi(spec, "blanket_cubugu") is not None)

    # kaynak kutusu ve guc mesh'i dogru araligi kullaniyor mu
    model, bilgi = kurucu.kur(spec)
    uzay = model.settings.source[0].space
    kontrol("kaynak kutusu FISIL araligi kapsiyor",
            abs(uzay.lower_left[2] + 177.5) < 1e-9
            and abs(uzay.upper_right[2] - 152.5) < 1e-9,
            "-> [%g, %g]" % (uzay.lower_left[2], uzay.upper_right[2]))
    mesh = None
    for t in model.tallies:
        if t.name == "guc_dagilimi":
            for f in t.filters:
                if hasattr(f, "mesh"):
                    mesh = f.mesh
    kontrol("guc mesh'i CUBUK araligini kapsiyor",
            mesh is not None and abs(mesh.lower_left[2] + 162.5) < 1e-9
            and abs(mesh.upper_right[2] - 137.5) < 1e-9,
            "-> [%g, %g]" % (mesh.lower_left[2], mesh.upper_right[2]) if mesh else "")

    # GERIYE DONUK UYUM: katmansiz modelde ikisi de +/-H/2 olmali
    duz = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    h = sema.kor_yuksekligi(duz["kor"])
    kontrol("katmansiz modelde fisil aralik = +/-H/2 (geriye donuk uyum)",
            geometri.aktif_aralik(duz) == (-h / 2.0, h / 2.0))
    kontrol("katmansiz modelde cubuk araligi = +/-H/2",
            geo_eks.cubuk_araligi(duz, "yakit_cubugu") == (-h / 2.0, h / 2.0))
    kontrol("2B modelde aralik None",
            geometri.aktif_aralik(
                sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))) is None)


def test_eksenel_dogrulama():
    """Katmanlamanin sessiz hatalari kosudan once yakalaniyor mu?"""
    print("\n[14c] EKSENEL DOGRULAMA: bozuk katmanlamalar")
    from cekirdek import dogrula as dg
    temel = _eksenel_spec()

    def hata(degistir):
        t = copy.deepcopy(temel)
        degistir(t)
        v = [b for b in dg.eksenel_kontrol(t) if b.seviye == "hata"]
        return v[0].mesaj if v else None

    for ad, degistir, parca in (
            ("desteklenmeyen kor turu",
             lambda t: t["kor"].update(tur="kuresel"), "desteklenmiyor"),
            ("tanimsiz dolgu adi",
             lambda t: t["kor"]["eksenel"]["bolgeler"][0].update(dolgu="yok_boyle"),
             "tanımsız dolgu"),
            ("sifir katman yuksekligi",
             lambda t: t["kor"]["eksenel"]["bolgeler"][1].update(yukseklik=0.0),
             "sıfırdan büyük olmalı"),
            ("hic katman yok",
             lambda t: t["kor"]["eksenel"].update(bolgeler=[]), "hiç katman"),
            ("fisil katman yok",
             lambda t: t["kor"]["eksenel"].update(
                 bolgeler=[sema.eksenel_bolge("su", 20.0, "su")]), "fisil malzeme yok"),
            ("anahtar kare_kafes disinda",
             lambda t: t["kor"]["eksenel"]["bolgeler"][1].update(
                 anahtar={"y": "demet_17x17"}), "yalnızca kare haritalı tam kor"),
    ):
        m = hata(degistir)
        kontrol("%s -> HATA" % ad, bool(m) and parca in m,
                "-> %s" % (m or "YAKALANMADI"))

    kontrol("temiz katmanlama hata vermiyor",
            not dg.hata_var(dg.eksenel_kontrol(temel)))


def test_kontrol_cubugu_eksenel():
    """
    Katmanli modelde cubuk ucu AKTIF araliktan hesaplanmali.

    Gercek z0 geometriden okunuyor -- "hata vermedi" testi bu hatayi gormez.
    """
    print("\n[14d] KONTROL CUBUGU: daldirma aktif aralikta olculuyor")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    spec["kor"]["yukseklik"] = None
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt yansitici", 25.0, "su"),
        sema.eksenel_bolge("aktif", 300.0, None),
        sema.eksenel_bolge("plenum", 30.0, "su"),
    ]}
    ar = geometri.aktif_aralik(spec)
    kontrol("aktif aralik plenumu disliyor (-152.5, 147.5)",
            abs(ar[0] + 152.5) < 1e-9 and abs(ar[1] - 147.5) < 1e-9, "-> %s" % (ar,))

    kontrol_cubugu = [c for c in spec["cubuklar"] if c.get("tur") == "kontrol"][0]
    for daldirma, beklenen in ((0.0, 147.5), (50.0, -2.5), (100.0, -152.5)):
        kontrol_cubugu["daldirma"] = daldirma
        _m, bilgi = kurucu.kur(spec)
        evrenler = bilgi["geometri_dizini"].kontrol_cubuklari[kontrol_cubugu["ad"]]
        z0lar = sorted({float(srf.z0)
                        for univ in evrenler for c in univ.cells.values()
                        for srf in c.region.get_surfaces().values()
                        if srf.type == "z-plane"})
        kontrol("daldirma %%%g -> uc z = %g" % (daldirma, beklenen),
                any(abs(z - beklenen) < 1e-9 for z in z0lar), "-> %s" % z0lar)


def test_arayuz_eksenel_gidip_gelme():
    """
    Katman tablosu spec'i bozmuyor mu?

    Ozellikle katmana ozel 'anahtar' alani: arayuzde duzenlenmiyor, bu yuzden
    kaydederken SESSIZCE SILINMESI cok kolay olurdu (ayni hatayi kaynak
    sekmesinde bir kez yaptim).
    """
    print("\n[14e] ARAYUZ: eksenel katman tablosu gidip gelmede bozmuyor")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_kor import KorSekmesi

    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    sekme = KorSekmesi()
    sekme.spec = spec
    sekme._yukleniyor = True
    sekme.doldur()
    sekme._yukleniyor = False
    kontrol("6 katman tabloya yuklendi", sekme.katman_tablo.rowCount() == 6,
            "-> %d" % sekme.katman_tablo.rowCount())
    kontrol("ozet uc araligi da gosteriyor",
            "395" in sekme.katman_ozet.text()
            and "330" in sekme.katman_ozet.text()
            and "300" in sekme.katman_ozet.text())

    adlar = lambda: [b["ad"] for b in spec["kor"]["eksenel"]["bolgeler"]]
    ilk = adlar()
    sekme._katman_ekle()
    kontrol("katman eklendi", len(adlar()) == 7)
    # Dalga 3: tablo fiziksel sirada (en ust katman ilk satirda); yeni katman
    # en uste eklenir -> tablonun ilk satiri.
    sekme.katman_tablo.setCurrentCell(0, 0)
    sekme._katman_sil()
    kontrol("katman silindi, sira bozulmadi", adlar() == ilk)
    sekme.katman_tablo.setCurrentCell(5, 0)       # en alt katman (spec[0])
    sekme._katman_tasi(-1)                        # yukari
    kontrol("katman kaydirildi", adlar()[:2] == [ilk[1], ilk[0]])
    sekme._katman_tasi(+1)                        # asagi
    kontrol("geri kaydirildi", adlar() == ilk)

    kontrol("katmanli modelde kor.yukseklik None (tek gercek kaynak)",
            spec["kor"]["yukseklik"] is None)

    # katmana ozel anahtar korunmali
    spec["kor"]["eksenel"]["bolgeler"][2]["anahtar"] = {"y": "demet_blanket"}
    sekme._yukleniyor = True
    sekme._katman_doldur()
    sekme._yukleniyor = False
    sekme.katman_tablo.cellWidget(1, 1).setValue(30.0)
    kontrol("katmana ozel anahtar KORUNDU",
            spec["kor"]["eksenel"]["bolgeler"][2].get("anahtar")
            == {"y": "demet_blanket"})
    kontrol("anahtarli katmanin dolgu kutusu devre disi",       # spec[2] -> satir 3
            not sekme.katman_tablo.cellWidget(3, 2).isEnabled())
    uyg  # noqa: B018


def test_eksenel_betik_ve_korunum(gecici):
    """
    Katmanli modelde betik esdegerligi VE guc toplami korunumu.

    Bu test bu turda bulunan uc hatadan ikisini yakalar:
      * kurucu ile betigin farkli kaynak kutusu kurmasi (1300 pcm)
      * guc mesh'inin hedef cubuktan tasmasi (F_q %6 sisme -> korunum bozulur)
    Tek is parcacigiyla bit esitligi aranir (8 is parcacigi ~6e-15 gurultu uretir).
    """
    print("\n[15] EKSENEL: betik esdegerligi + guc korunumu (tek is parcacigi)")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    spec["ayarlar"]["parcacik"] = 3000
    spec["ayarlar"]["cevrim"] = 30
    spec["ayarlar"]["pasif"] = 10

    eski = os.getcwd()
    try:
        ya = os.path.join(gecici, "eks_a")
        os.makedirs(ya, exist_ok=True)
        os.chdir(ya)
        model_a, _ = kurucu.kur(spec)
        sp_a = model_a.run(threads=1, output=False)
        k_a = openmc.StatePoint(sp_a).keff

        yb = os.path.join(gecici, "eks_b")
        os.makedirs(yb, exist_ok=True)
        os.chdir(yb)
        betik = os.path.join(yb, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("eksuret", betik)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        k_b = openmc.StatePoint(mod.model.run(threads=1, output=False)).keff
    finally:
        os.chdir(eski)
    kontrol("kurucu %.10f vs betik %.10f" % (k_a.nominal_value, k_b.nominal_value),
            k_a.nominal_value == k_b.nominal_value,
            "-> bit duzeyinde %s"
            % ("ayni" if k_a.nominal_value == k_b.nominal_value else "FARKLI"))

    from cekirdek import kosucu as _kos
    s = _kos.sonuc_oku(sp_a)
    g = s.get("guc") or {}
    kor = g.get("korunum")
    kontrol("guc toplami korunuyor (bagil fark %.2e)" % (kor if kor is not None else -1),
            kor is not None and kor < 1e-6)
    f = g.get("faktorler") or {}
    kontrol("F_q hesaplandi ve makul (1.3-2.5): %.4f" % (f.get("F_q") or 0),
            1.3 < (f.get("F_q") or 0) < 2.5)


def test_onizleme_tallyli_model(gecici=None):
    """
    ONIZLEME TALLY'LERE TAKILMAMALI.

    Model.plot() geometriyi dilimlemek icin OpenMC KUTUPHANESINI baslatiyor ve
    bu sirada tally'leri de cozmeye calisiyor. Guc dagilimi tally'sine eklenen
    CellFilter cozulemedigi icin OpenMC C++ tarafinda terminate() cagriliyordu:
    Python istisnasi degil, DOGRUDAN SIGABRT -- butun arayuz kapaniyordu.
    Olculdu: duzeltmeden once 3/3 kosuda cokme, duzeltmeden sonra 4/4 temiz.

    DURUSTLUK NOTU: cokme yalnizca GERCEK bir X oturumunda, tam arayuz
    akisinda tekrarlanabiliyordu; basssiz (offscreen) ortamda duzeltme
    kapaliyken bile cokmuyor. Yani bu test cokmenin KENDISINI degil,
    cokmeyi ortadan kaldiran DEGISMEZI sinar: cizime giden modelde tally
    olmamalidir. Elle tekrar tarifi README'de yazili.
    """
    print("\n[16] ONIZLEME: tally'li modeller cizimi cokertmemeli")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        kontrol("PySide6 yok, onizleme testi atlandi", True, "-> %s" % e)
        return
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.onizleme import OnizlemeWidget

    tallyli = [ad for ad in _ornek_adlari()
               if (lambda sp: sp.get("tallyler")
                   or (sp.get("guc_dagilimi") or {}).get("var"))(
                       sema.yukle(os.path.join(ORNEK, ad + ".json")))]
    kontrol("tally tasiyan ornek var (test anlamli olsun)", len(tallyli) >= 3,
            "-> %s" % ", ".join(tallyli))

    # Model.plot() sarmalanip cagrildigi modelin tally sayisi kaydediliyor.
    # Duzeltme geri alinirsa bu sayi sifirdan buyuk cikar ve test KALIR.
    import openmc
    gorulen = []
    asil_plot = openmc.Model.plot

    def izleyen_plot(self, *a, **kw):
        gorulen.append(len(self.tallies))
        return asil_plot(self, *a, **kw)

    w = OnizlemeWidget()
    openmc.Model.plot = izleyen_plot
    try:
        for ad in tallyli:
            w.spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
            iyi = True
            for eksen in ("xy", "xz"):
                w.eksen.setCurrentText(eksen)
                w._ciz()
                iyi = iyi and w.cizildi_mi()
            kontrol("%s xy+xz cizildi" % ad, iyi, "-> %s" % (w._son_hata or ""))
    finally:
        openmc.Model.plot = asil_plot
    kontrol("cizime giden modellerin hicbiri tally tasimiyor (%d cizim)"
            % len(gorulen), bool(gorulen) and max(gorulen) == 0,
            "-> gorulen tally sayilari: %s" % sorted(set(gorulen)))

    # Yeniden girme korumasi: cizim surerken ikinci cizim baslamamali.
    w.spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    w._ciziliyor = True
    onceki = len(gorulen)
    openmc.Model.plot = izleyen_plot
    try:
        w._ciz()
    finally:
        openmc.Model.plot = asil_plot
        w._ciziliyor = False
    kontrol("cizim surerken ikinci cizim atlaniyor", len(gorulen) == onceki)
    uyg  # noqa: B018


def test_ana_dolgu_ture_gore():
    """
    Ana dolgu kor TURUNE gore secilmeli; 'cubuk or demet or ...' zinciri
    eski bir alani seciyor, kare_kafes'te ise kor haritasini hic gormuyordu.
    """
    print("\n[19b] ANA DOLGU: tur'e duyarli secim")
    # (a) tek_demet + katmanlar (su / aktif / su), JSON'da ESKI bir kor.cubuk
    #     kalintisi (yakitsiz kilavuz boru). pwr_eksenel KULLANILMADI: oradaki
    #     blanket katmanlari kendi dolgulariyla TESADUFEN ayni araligi veriyor
    #     ve kontrol eski kodda da geciyordu -- hicbir sey kanitlamiyordu.
    sp = _eksenel_spec()
    sp["kor"]["cubuk"] = "kilavuz_boru"
    ar = geometri.aktif_aralik(sp)
    kontrol("eski kor.cubuk kalintisi aktif araligi bozmuyor (-183, 183)",
            ar == (-183.0, 183.0), "-> %s" % (ar,))
    # (b) kare_kafes + eksenel katman, aktif katmanin kendi dolgusu yok
    kk = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    kk["kor"].update(tur="kare_kafes", demet=None, boyut=[1, 1], harita=["a"],
                     anahtar={"a": "demet_17x17"}, adim=21.42, yukseklik=None)
    kk["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 20.0, "su"),
        sema.eksenel_bolge("aktif", 100.0, None),
        sema.eksenel_bolge("ust", 20.0, "su")]}
    ar = geometri.aktif_aralik(kk)
    kontrol("kare_kafes: aktif aralik yalniz yakitli katman (-50, 50)",
            ar == (-50.0, 50.0), "-> %s" % (ar,))
    cr = geo_eks.cubuk_araligi(kk, "yakit_cubugu")
    kontrol("kare_kafes: cubuk araligi haritadaki demetten bulunuyor (-50, 50)",
            cr == (-50.0, 50.0), "-> %s" % (cr,))
    kontrol("sema.ana_dolgu kare_kafes icin None", sema.ana_dolgu(kk["kor"]) is None)
    kontrol("sema.katman_adaylari kare_kafes haritasini veriyor",
            sema.katman_adaylari(kk["kor"]) == ["demet_17x17"])


HIZLI = [
    test_ana_dolgu_ture_gore, test_eksenel_geometri, test_eksenel_araliklar,
    test_eksenel_dogrulama, test_kontrol_cubugu_eksenel,
    test_arayuz_eksenel_gidip_gelme, ]
YAVAS = [
    test_eksenel_betik_ve_korunum, test_onizleme_tallyli_model]
