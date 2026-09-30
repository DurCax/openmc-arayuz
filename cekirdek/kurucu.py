# -*- coding: utf-8 -*-
"""
================================================================================
 kurucu.py  --  spec -> openmc.Model
================================================================================

 Model tanimini (sema.py bicimimde JSON spec) calisir bir openmc.Model
 nesnesine cevirir. XML elle uretilmez; her sey openmc nesneleri uzerinden
 gecer, boylece OpenMC'nin kendi dogrulamasi devrede kalir.

 KULLANIM
   from cekirdek import kurucu, sema
   spec = sema.yukle("ornekler/pwr_pinhucre.json")
   model, bilgi = kurucu.kur(spec)
   model.export_to_model_xml("kosu/model.xml")

 DONEN BILGI SOZLUGU
   bilgi["malzemeler"] : {spec_adi: openmc.Material}
   bilgi["renkler"]    : {openmc.Material: (R,G,B)}   -- Model.plot() icin
   bilgi["universeler"]: {spec_adi: openmc.Universe}
   bilgi["sinir_kutu"] : (genislik_x, genislik_y)     -- onizleme icin

 GEOMETRI
   Tek kurucu cekirdek/geometri'dir (docs/GEOMETRI_MODELI.md): 7 sablon
   (tek_cubuk, tek_plaka, tek_demet, kare_kafes, altigen_kafes, kuresel,
   tamburlu) calisma aninda dugum agacina genisler; gelismis modda
   (kor.tur == "agac") agac spec["geometri"]dir. bilgi["geometri_dizini"]:
   hucre/kafes -> dugum yolu (R11).
================================================================================
"""

import math

import openmc

from cekirdek import kaynak as _kaynak
from cekirdek.geometri import eksenel as _geo_eks
from cekirdek.geometri.kurulum import Kurucu as _GeoKurucu, kur as _geo_kur
from cekirdek.sema import model_yuksekligi as sema_model_yuksekligi
from cekirdek.sema import guc_hedefleri as sema_guc_hedefleri
from cekirdek.sema import BOSLUK, cubuk_bul, plaka_bul

# Varsayilan renk (spec'te renk verilmemis malzemeler icin)
_VARSAYILAN_RENK = (170, 170, 170)


# ============================================================================
# 1. MALZEMELER
# ============================================================================

def malzemeleri_kur(spec):
    """
    spec["malzemeler"] -> {ad: openmc.Material}, openmc.Materials, renk haritasi
    """
    nesneler = {}
    renkler = {}
    for m in spec["malzemeler"]:
        mat = openmc.Material(name=m.get("gorunen_ad") or m["ad"])
        for b in m["bilesim"]:
            miktar = b["miktar"]
            birim = b.get("birim", "ao")
            if b.get("tur") == "nuklid":
                mat.add_nuclide(b["isim"], miktar, percent_type=birim)
            else:
                zeng = b.get("zenginlik")
                if zeng is not None:
                    mat.add_element(b["isim"], miktar, percent_type=birim,
                                    enrichment=zeng)
                else:
                    mat.add_element(b["isim"], miktar, percent_type=birim)
        yog = m["yogunluk"]
        mat.set_density(yog["birim"], yog["deger"])
        if m.get("sicaklik"):
            mat.temperature = m["sicaklik"]
        for s in m.get("sab", []):
            mat.add_s_alpha_beta(s)
        nesneler[m["ad"]] = mat
        renkler[mat] = tuple(m["renk"]) if m.get("renk") else _VARSAYILAN_RENK
    return nesneler, openmc.Materials(list(nesneler.values())), renkler


def _mat(nesneler, ad):
    """Malzeme adini nesneye cevirir; "bosluk" veya None -> None (void)."""
    if ad is None or ad == BOSLUK:
        return None
    if ad not in nesneler:
        raise KeyError("tanımsız malzeme: %s" % ad)
    return nesneler[ad]


# ============================================================================
# 2. GEOMETRI -- cekirdek/geometri (tek kurucu, Dalga G-1)
# ============================================================================
#
# Kor artik bir dugum agacindan kurulur: sablon modunda agac genislet(spec)
# ile turetilir (cekirdek/geometri/sablon.py), gelismis modda
# spec["geometri"]dir. Eski kor_kur esdegerlik kapisindan (27 ornek x 1e5
# nokta) gectikten sonra silindi; kapi kayitli parmak izleriyle surer
# (testler/test_geometri_esdegerlik.py). Asagidaki adlar geriye uyum icin
# ince sarmalayicilardir (G-2 sonunda tuketiciler geometri API'sine gecer).

def kor_kur(spec, nesneler, universeler):
    """Kor duzenini kurar; (kok_universe, (genislik_x, genislik_y)) dondurur."""
    kok, kutu, _dizin = _geo_kur(spec, nesneler, universeler)
    return kok, kutu


def _tek_bilesen(spec, nesneler):
    """Kor gerektirmeyen bilesen kurucusu (cubuk/plaka tek basina)."""
    from cekirdek.geometri import GeometriModeli
    from cekirdek.geometri.sema import tanimlar
    from cekirdek.geometri.yapici import NesneYapici
    agac = spec.get("geometri") if isinstance(spec.get("geometri"), dict) else {}
    m = GeometriModeli(kok={}, parcalar=(), gruplar=tuple(agac.get("gruplar") or ()),
                       tanimlar=tanimlar(spec, agac))
    k = _GeoKurucu(spec, m, NesneYapici(nesneler))
    k.yukseklik = sema_model_yuksekligi(spec)
    return k


def cubuk_universe(spec, cubuk_ad, nesneler):
    """Cubuk evreni (geometri.bilesen.cubuk; kontrol cubugu dahil)."""
    from cekirdek.geometri import bilesen as _b
    c = cubuk_bul(spec, cubuk_ad)
    if c is None:
        raise KeyError("tanımsız çubuk: %s" % cubuk_ad)
    return _b.cubuk(_tek_bilesen(spec, nesneler), c, cubuk_ad)


def plaka_universe(spec, plaka_ad, nesneler):
    """MTR plaka elemani evreni (geometri.bilesen.plaka)."""
    from cekirdek.geometri import bilesen as _b
    p = plaka_bul(spec, plaka_ad)
    if p is None:
        raise KeyError("tanımsız plaka elemanı: %s" % plaka_ad)
    return _b.plaka(_tek_bilesen(spec, nesneler), p, plaka_ad)


def _altigen_sinir(halka_sayisi, adim, kafes_yonelimi, bc, buyutme=0.0):
    """Altigen kafesi saran HexagonalPrism (yonelim = kafes yonelimi; olculdu)."""
    ic_yaricap = (halka_sayisi - 1) * adim * math.sqrt(3.0) / 2.0 + adim / 2.0 + buyutme
    kenar = 2.0 * ic_yaricap / math.sqrt(3.0)
    return openmc.model.HexagonalPrism(edge_length=kenar, orientation=kafes_yonelimi,
                                       boundary_type=bc)


# eksenel araliklar: cekirdek/geometri/eksenel.py (sablon + agac modu)
aktif_eksenel_aralik = _geo_eks.aktif_aralik
cubuk_eksenel_aralik = _geo_eks.cubuk_araligi
guc_eksenel_araligi = _geo_eks.hedef_araligi
guc_yuksekligi = _geo_eks.hedef_yuksekligi
_spec_fisil_mi = _geo_eks.fisil_mi
_iceriyor_mu = _geo_eks.iceriyor_mu
_guc_hedef_adlari = _geo_eks._guc_hedef_adlari


def kor_ic_olcusu(spec, sinir_kutu):
    """
    Korun YANSITICI HARIC yanal olcusu (gx, gy) -- baslangic kaynagi kutusu.
    Yansitici eklenince yakit kutunun kucuk bir kesrine dusuyor ve OpenMC
    "Too few source sites" diyerek duruyordu (olculdu: 17x17 + 20 cm su).
    Sablonda eski kurucunun degeri (genislet kok._ic_kutu), agacta kok kesiti.
    """
    from cekirdek import geometri
    return tuple(geometri.ic_olcusu(geometri.model(spec)))


# ============================================================================
# 3. AYARLAR VE TALLY'LER
# ============================================================================


def ayarlari_kur(spec, sinir_kutu, fisil_aralik=None):
    """spec["ayarlar"] -> openmc.Settings"""
    a = spec["ayarlar"]
    s = openmc.Settings()
    s.run_mode = a.get("mod", "eigenvalue")
    s.particles = int(a["parcacik"])
    s.batches = int(a["cevrim"])
    if s.run_mode == "eigenvalue":
        s.inactive = int(a["pasif"])
    if a.get("tohum"):
        s.seed = int(a["tohum"])
    if a.get("sicaklik_yontemi"):
        s.temperature = {"method": a["sicaklik_yontemi"]}

    k = a.get("kaynak") or {}
    if k.get("tur") == "kutu":
        # !!! Z ARALIGI MODELIN YUKSEKLIGINI KAPSAMALIDIR !!!
        #   Onceki surumde z araligi +/-1.0 cm'ye sabitti. 2B modelde sorun
        #   degildi ama 366 cm'lik 3B bir modelde kaynak merkezdeki 2 cm'lik
        #   bir dilimde basliyordu; eksenel sekil onlarca cevrim boyunca
        #   yayilmaya calisiyor ve GUC DAGILIMI YANLIS (asiri tepeli) cikiyordu.
        #   Shannon entropisi bunu gostermiyor: entropi global bir skalerdir ve
        #   bu geometride radyal dagilim baskin geliyor.
        h = sema_model_yuksekligi(spec)
        # Eksenel katmanlamada kutu, tum modeli degil FISIL araligi kapsar:
        # yansitici ve plenum katmanlarinda orneklenen noktalar "fissionable"
        # kisiti yuzunden reddedilirdi, bu da yakinsamayi bosa yavaslatir.
        if fisil_aralik:
            z_alt, z_ust = fisil_aralik
        else:
            yari_z = (h / 2.0) if h else 1.0
            z_alt, z_ust = -yari_z, +yari_z
        kx, ky = kor_ic_olcusu(spec, sinir_kutu)
        alt = k.get("alt") or [-kx / 2, -ky / 2, z_alt]
        ust = k.get("ust") or [+kx / 2, +ky / 2, z_ust]
        uzay = openmc.stats.Box(alt, ust)
        kisit = {"fissionable": True}
    else:
        uzay = openmc.stats.Point(tuple(k.get("konum") or (0.0, 0.0, 0.0)))
        kisit = None
    s.source = _kaynak.kaynak_kur(k, uzay, kisit)
    # Foton kaynagi foton tasinimi gerektirir; acilmazsa parcaciklar hicbir
    # etkilesime girmeden gecer ve sonuc sessizce ANLAMSIZ olur.
    if (k.get("parcacik") or "neutron") == "photon":
        s.photon_transport = True

    # --- Shannon entropisi mesh'i (kaynak yakinsamasi olcumu) ---
    ent = a.get("entropi_mesh") or {}
    if ent.get("var") and s.run_mode == "eigenvalue":
        gx, gy = sinir_kutu
        mesh = openmc.RegularMesh()
        mesh.dimension = _kaynak.entropi_boyutu(spec)   # otomatik ya da dosyadaki
        # Eksenel sinirlar: 3B modelde GERCEK kor yuksekligi kullanilmali.
        #   Onceki surumde z daima +/-1e10 idi. nz=1 iken zararsizdi, ama
        #   nz>1 istendiginde iki bin de 1e10 cm yuksekliginde oluyor, hepsi
        #   ayni dilime dusuyor ve EKSENEL yakinsama olculmemis oluyordu --
        #   entropi yine de "yakinsadi" diyordu. Eksenel heterojen bir korda
        #   (blanket, plenum) asil riskli yon tam da budur.
        h = sema_model_yuksekligi(spec)
        z = (h / 2.0) if h else 1.0e10
        mesh.lower_left = (-gx / 2.0, -gy / 2.0, -z)
        mesh.upper_right = (gx / 2.0, gy / 2.0, z)
        s.entropy_mesh = mesh
    return s


def _kure_mu(spec):
    """Kuresel duzenek mi (sablon: kor.tur; agac: kok kesiti kure)."""
    if (spec.get("kor") or {}).get("tur") == "agac":
        kok = (spec.get("geometri") or {}).get("kok") or {}
        return (kok.get("kesit") or {}).get("sekil") == "kure"
    return spec["kor"].get("tur") == "kuresel"


def tally_mesh_sinirlari(spec, f, sinir_kutu):
    """
    Tally mesh filtresinin (alt, ust) sinirlari [cm].

    "otomatik": true (ya da sinir yok) -> model KURULURKEN turetilir:
      x, y : modelin sinir kutusu (yansitici dahil)
      z    : 3B modelde kor yuksekligi; kuresel duzenekte kure capi;
             2B modelde +/-1 cm (eksenel yonde sonsuz model, tek dilim)
    Eski dosyalardaki acik "alt"/"ust" oldugu gibi kullanilir.

    Uretilen betik (kod_uret.py) AYNI fonksiyonu cagirir -- ayni sayiyi iki
    yoldan hesaplayan iki kod er ya da gec ayrisir.
    """
    if not f.get("otomatik") and f.get("alt") and f.get("ust"):
        return list(f["alt"]), list(f["ust"])
    if sinir_kutu is None:
        raise ValueError("otomatik ağ sınırları için modelin sınır kutusu gerekli")
    gx, gy = sinir_kutu
    h = sema_model_yuksekligi(spec)
    if h:
        z = h / 2.0
    elif _kure_mu(spec):
        z = gx / 2.0
    else:
        z = 1.0
    return [-gx / 2.0, -gy / 2.0, -z], [gx / 2.0, gy / 2.0, z]


def tallyleri_kur(spec, nesneler, sinir_kutu=None):
    """spec["tallyler"] -> openmc.Tallies"""
    liste = []
    for t in spec.get("tallyler", []):
        tal = openmc.Tally(name=t["ad"])
        tal.scores = list(t["skorlar"])
        if t.get("nuklidler"):
            tal.nuclides = list(t["nuklidler"])
        filtreler = []
        for f in t.get("filtreler", []):
            if f["tur"] == "enerji":
                filtreler.append(openmc.EnergyFilter(f["gruplar"]))
            elif f["tur"] == "mesh":
                mesh = openmc.RegularMesh()
                mesh.dimension = f["boyut"]
                mesh.lower_left, mesh.upper_right = tally_mesh_sinirlari(
                    spec, f, sinir_kutu)
                filtreler.append(openmc.MeshFilter(mesh))
            elif f["tur"] == "malzeme":
                filtreler.append(openmc.MaterialFilter(
                    [nesneler[a] for a in f["adlar"]]))
            else:
                raise ValueError("bilinmeyen filtre türü: %s" % f["tur"])
        tal.filters = filtreler
        liste.append(tal)
    return openmc.Tallies(liste)


# ============================================================================
# 4. ANA GIRIS
# ============================================================================


def _guc_hedef_hucresi(spec, hedef, nesneler, universeler):
    """Bir hedefin ({"cubuk", "bolge"}) hucresi; cubuk geometride yoksa None.
    Tanimsiz cubuk ve gecersiz bolge ValueError."""
    from cekirdek import guc as _guc
    cubuk_ad = hedef.get("cubuk")
    c = cubuk_bul(spec, cubuk_ad) if cubuk_ad else None
    if c is None:
        raise ValueError("güç dağılımı için geçerli bir çubuk seçilmeli"
                         + (" ('%s' tanımsız)" % cubuk_ad if cubuk_ad else ""))
    univ = universeler.get(cubuk_ad)
    if univ is None:
        return None
    hucreler = _guc.bolge_hucresi(univ, c, nesneler)
    bolge_no = int(hedef.get("bolge") or 0)
    if not (0 <= bolge_no < len(hucreler)):
        raise ValueError("'%s': geçersiz bölge numarası %d (çubukta %d bölge var)"
                         % (cubuk_ad, bolge_no + 1, len(hucreler)))
    return hucreler[bolge_no]


def guc_hedef_hucreleri(spec, nesneler, universeler):
    """
    Guc dagilimi hedeflerinin hucreleri.
    DONER ([(cubuk adi, openmc.Cell)], [modelde olmayan cubuk adlari])
    Tanimsiz cubuk ya da gecersiz bolge ValueError. Listedeki bir tur
    geometride yoksa atlanir ("modelde yok"); HICBIRI yoksa ValueError.
    Ayni (cubuk, bolge) iki kez yazilmissa bir kez sayilir.
    """
    hedefler = sema_guc_hedefleri(spec.get("guc_dagilimi"))
    if not hedefler:
        raise ValueError("güç dağılımı için geçerli bir çubuk seçilmeli")
    bulunan, eksik, gorulen = [], [], set()
    for h in hedefler:
        anahtar = (h["cubuk"], h["bolge"])
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        hucre = _guc_hedef_hucresi(spec, h, nesneler, universeler)
        if hucre is None:
            eksik.append(h["cubuk"])
        else:
            bulunan.append((h["cubuk"], hucre))
    if not bulunan:
        raise ValueError(
            "'%s' çubuğu modelde kullanılmıyor. Güç dağılımı yalnızca geometride "
            "yer alan bir çubuk için hesaplanabilir." % "', '".join(eksik))
    return bulunan, eksik


def _guc_mesh_filtresi(spec, adlar, sinir_kutu, dilim):
    """Eksenel 1x1xN mesh filtresi (3B ve dilim > 1); yoksa None.

    !!! EKSENEL MESH HEDEF CUBUKLARIN ARALIGIYLA TAM ORTUSMELIDIR !!!
      Mesh yakittan tasarsa bos bin'ler ortalamayi dusurur ve F_q yapay
      olarak siser. Sinirlar kor yuksekliginden TURETILIR, elle girilmez;
      yansitici/plenum katmanlari mesh'e girmez."""
    aralik = guc_eksenel_araligi(spec, adlar)
    if not aralik or dilim <= 1:
        return None
    gx, gy = sinir_kutu
    pay = max(gx, gy)          # x,y'de tek bin -- her seyi kapsamasi yeter
    mesh = openmc.RegularMesh()
    mesh.dimension = [1, 1, dilim]
    mesh.lower_left = (-pay, -pay, aralik[0])
    mesh.upper_right = (pay, pay, aralik[1])
    return openmc.MeshFilter(mesh)


def guc_tally_ekle(spec, model, nesneler, universeler, sinir_kutu,
                   fisil_aralik=None, bilgi=None):
    """
    Cubuk bazli guc dagilimi tally'lerini modele ekler.

    Her hedef tur (guc_dagilimi.cubuklar) icin AYRI bir "guc_dagilimi"
    tally'si: DistribcellFilter tek hucre alir. Hepsi ayni adi tasir
    (guc.dagilim_oku hepsini birlestirir; kosucu kullanici tally'si saymaz)
    ve 3B modelde AYNI eksenel mesh'i paylasir (dilimler turler arasinda
    hizali). Cok turde hedef hucreye cubuk adi yazilir (Cell.name; fizige
    girmez): okurken tur buradan anlasilir. Tek turde XML eskisiyle aynidir.

    guc_toplam_ref: ayni hucrelere bagli bolunmemis tally (toplam korunumu;
    eksenel mesh'in hucrelerin tamamini kapsayip kapsamadigini da sinar).
    guc_model_toplam: filtresiz; hedef payi = ref / model (mutlak guc).

    bilgi verilirse "guc_hucreler" [(ad, hucre)] ve "guc_eksik" [ad] yazilir.
    DONER ilk hedef hucre
    """
    hedefler, eksik = guc_hedef_hucreleri(spec, nesneler, universeler)
    g = spec.get("guc_dagilimi") or {}
    skor = g.get("skor") or "kappa-fission"
    cok_tur = len(hedefler) > 1
    taller, mesh_f = [], None
    # Nesne olusturma sirasi (tally, distribcell, mesh) eskisiyle ayni: tek
    # turde uretilen XML (kimlikler dahil) degismez (test_guc_coklu).
    for i, (ad, hucre) in enumerate(hedefler):
        if cok_tur:
            hucre.name = ad
        tal = openmc.Tally(name="guc_dagilimi")
        tal.scores = [skor]
        dc = openmc.DistribcellFilter(hucre)
        if i == 0:
            mesh_f = _guc_mesh_filtresi(spec, [a for a, _h in hedefler], sinir_kutu,
                                        int(g.get("eksenel_dilim") or 1))
        tal.filters = [dc] + ([mesh_f] if mesh_f else [])
        taller.append(tal)
    ref = openmc.Tally(name="guc_toplam_ref")
    ref.scores = [skor]
    ref.filters = [openmc.CellFilter([h for _a, h in hedefler])]
    tum = openmc.Tally(name="guc_model_toplam")
    tum.scores = [skor]
    model.tallies = openmc.Tallies(list(model.tallies) + taller + [ref, tum])
    if bilgi is not None:
        bilgi["guc_hucreler"] = hedefler
        bilgi["guc_eksik"] = eksik
    return hedefler[0][1]


def kur(spec):
    """
    Spec'i tam bir openmc.Model'e cevirir.

    DONER  (model, bilgi)
      model : openmc.Model
      bilgi : {"malzemeler", "renkler", "universeler", "sinir_kutu"}
    """
    openmc.reset_auto_ids()          # ardarda kurulumlarda id cakismasini onler

    nesneler, materials, renkler = malzemeleri_kur(spec)
    universeler = {}
    kok, sinir_kutu, dizin = _geo_kur(spec, nesneler, universeler)

    geometry = openmc.Geometry(kok)
    # AKTIF (fisil) eksenel aralik: kaynak kutusu, guc mesh'i ve kontrol
    # cubugu daldirmasi hep bu TEK tanimdan okur. Bir zamanlar geometriden
    # turetilen ikinci bir tanim daha vardi; uretilen betik onu bilemedigi
    # icin betik ile kurucu FARKLI kaynak kutusu kuruyordu (1300 pcm).
    fisil = aktif_eksenel_aralik(spec)
    settings = ayarlari_kur(spec, sinir_kutu, fisil)
    tallies = tallyleri_kur(spec, nesneler, sinir_kutu)

    model = openmc.Model(geometry=geometry, materials=materials,
                         settings=settings, tallies=tallies)

    # --- kinetik parametreler (IFP) ---
    # add_kinetics_parameters_tallies() modele tally EKLER; bu yuzden model
    # kurulurken yapilmalidir, sonradan degil (onbellek kimliginin parcasi).
    kin = spec["ayarlar"].get("kinetik") or {}
    if kin.get("var") and settings.run_mode == "eigenvalue":
        model.add_kinetics_parameters_tallies()
        model.settings.ifp_n_generation = int(kin.get("nesil") or 10)
    bilgi = {
        "malzemeler": nesneler,
        "renkler": renkler,
        "universeler": universeler,
        "sinir_kutu": sinir_kutu,
        "guc_hucre": None,
        "guc_hucreler": [],
        "guc_eksik": [],
        "aktif_aralik": fisil,
        "geometri_dizini": dizin,
    }

    # --- cubuk bazli guc dagilimi ---
    g = spec.get("guc_dagilimi") or {}
    if g.get("var"):
        bilgi["guc_hucre"] = guc_tally_ekle(spec, model, nesneler, universeler,
                                            sinir_kutu, fisil, bilgi=bilgi)
    return model, bilgi
