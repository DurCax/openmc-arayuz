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

import openmc

from cekirdek import geometri
from cekirdek import kaynak as _kaynak
from cekirdek import mgxs_uret
from cekirdek import spektrum
from cekirdek import foton as _foton, sicaklik as _sicaklik, yuzey_akim as _yuzey
from cekirdek import varyans as _varyans
from cekirdek.geometri.kurulum import kur as _geo_kur
from cekirdek.sema import model_yuksekligi as sema_model_yuksekligi
from cekirdek.sema import guc_hedefleri as sema_guc_hedefleri
from cekirdek.sema import BOSLUK, cubuk_bul
from cekirdek.ceviri import _

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
        raise KeyError(_("tanımsız malzeme: %s") % ad)
    return nesneler[ad]


# ============================================================================
# 2. GEOMETRI -- cekirdek/geometri (tek kurucu, Dalga G-1)
# ============================================================================
#
# Kor bir dugum agacindan kurulur: sablon modunda agac genislet(spec) ile
# turetilir (cekirdek/geometri/sablon.py), gelismis modda spec["geometri"]dir.
# Eksenel araliklar, kaynak kutusu ve tek bilesen evrenleri cekirdek/geometri
# API'sindedir (G-1 sarmalayicilari Dalga G temizliginde silindi).


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
        # yanal olcu YANSITICI HARIC: yansitici eklenince yakit kutunun kucuk
        # bir kesrine dusuyor, OpenMC "Too few source sites" diyordu (olculdu).
        kx, ky = geometri.ic_olcusu(geometri.model(spec))
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
    _foton.uygula(s, spec)          # Y7: foton tasinimi (cekirdek/foton.py)
    _sicaklik.uygula(s, spec)       # Y7: sicaklik isleme (cekirdek/sicaklik.py)
    _varyans.uygula(s, spec, sinir_kutu)   # Y9: agirlik pencereleri (cekirdek/varyans.py)

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
             2B modelde +/-1 cm -- AMA mesh tally'leri bunu kullanmaz: v3 Y1'den
             beri cekirdek/mesh_tally/tanim.py 2B'de z'yi +/-Z_2B_YARI (butun z
             kolonu; geometri z'de sinirliysa o aralik) yapar (bkz. Z_2B_YARI notu).
    Eski dosyalardaki acik "alt"/"ust" oldugu gibi kullanilir.

    Mesh tally'leri (kurucu ve betik) yalniz mesh_tally.sinir_onerisi uzerinden
    buraya gelir -- ayni sayiyi iki yoldan hesaplayan iki kod er ya da gec ayrisir.
    """
    if not f.get("otomatik") and f.get("alt") and f.get("ust"):
        return list(f["alt"]), list(f["ust"])
    if sinir_kutu is None:
        raise ValueError(_("otomatik ağ sınırları için modelin sınır kutusu gerekli"))
    gx, gy = sinir_kutu
    h = sema_model_yuksekligi(spec)
    if h:
        z = h / 2.0
    elif _kure_mu(spec):
        z = gx / 2.0
    else:
        z = 1.0
    return [-gx / 2.0, -gy / 2.0, -z], [gx / 2.0, gy / 2.0, z]


def tallyleri_kur(spec, nesneler, sinir_kutu=None, z_aralik=None):
    """spec["tallyler"] -> openmc.Tallies. z_aralik: 2B modelde geometrinin sonlu
    z sinirlari (mesh tally kirpmasi; v3 Y1). Ozdegerde mesh tally varsa
    filtresiz genel isinma tally'si de eklenir (mesh_tally.genel)."""
    from cekirdek import mesh_tally as _mt
    liste = []
    for t in spec.get("tallyler", []):
        if _yuzey.yuzey_tally_mi(t):
            continue          # Y7: kur() sonunda yuzey_akim.tally_ekle (geometri gerekir)
        tal = openmc.Tally(name=t["ad"])
        tal.scores = list(t["skorlar"])
        if t.get("nuklidler"):
            tal.nuclides = list(t["nuklidler"])
        filtreler = []
        for f in t.get("filtreler", []):
            if f["tur"] == "enerji":
                filtreler.append(openmc.EnergyFilter(f["gruplar"]))
            elif f["tur"] == "mesh":   # v3 Y1: duzenli/silindirik/kuresel (tek kaynak)
                filtreler.append(_mt.mesh_filtresi_kur(spec, f, sinir_kutu, z_aralik))
            elif f["tur"] == "malzeme":
                filtreler.append(openmc.MaterialFilter(
                    [nesneler[a] for a in f["adlar"]]))
            else:
                raise ValueError(_("bilinmeyen filtre türü: %s") % f["tur"])
        tal.filters = filtreler
        liste.append(tal)
    genel = _mt.genel_isi_tally_kur(spec)
    if genel is not None:
        liste.append(genel)
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
        raise ValueError(_("güç dağılımı için geçerli bir çubuk seçilmeli")
                         + (_(" ('%s' tanımsız)") % cubuk_ad if cubuk_ad else ""))
    univ = universeler.get(cubuk_ad)
    if univ is None:
        return None
    hucreler = _guc.bolge_hucresi(univ, c, nesneler)
    bolge_no = int(hedef.get("bolge") or 0)
    if not (0 <= bolge_no < len(hucreler)):
        raise ValueError(_("'%s': geçersiz bölge numarası %d (çubukta %d bölge var)")
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
        raise ValueError(_("güç dağılımı için geçerli bir çubuk seçilmeli"))
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
            _("'%s' çubuğu modelde kullanılmıyor. Güç dağılımı yalnızca geometride "
            "yer alan bir çubuk için hesaplanabilir.") % "', '".join(eksik))
    return bulunan, eksik


def _guc_mesh_filtresi(spec, adlar, sinir_kutu, dilim):
    """Eksenel 1x1xN mesh filtresi (3B ve dilim > 1); yoksa None.

    !!! EKSENEL MESH HEDEF CUBUKLARIN ARALIGIYLA TAM ORTUSMELIDIR !!!
      Mesh yakittan tasarsa bos bin'ler ortalamayi dusurur ve F_q yapay
      olarak siser. Sinirlar kor yuksekliginden TURETILIR, elle girilmez;
      yansitici/plenum katmanlari mesh'e girmez."""
    aralik = geometri.hedef_araligi(spec, adlar)
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
    from cekirdek import bolge_bol
    spec = bolge_bol.uygula(spec)    # v3 Y5: tukenme.bolme (yalniz tukenme.var acikken)

    nesneler, materials, renkler = malzemeleri_kur(spec)
    universeler = {}
    kok, sinir_kutu, dizin = _geo_kur(spec, nesneler, universeler)

    geometry = openmc.Geometry(kok)
    # AKTIF (fisil) eksenel aralik: kaynak kutusu, guc mesh'i ve kontrol
    # cubugu daldirmasi hep bu TEK tanimdan okur. Bir zamanlar geometriden
    # turetilen ikinci bir tanim daha vardi; uretilen betik onu bilemedigi
    # icin betik ile kurucu FARKLI kaynak kutusu kuruyordu (1300 pcm).
    fisil = geometri.aktif_aralik(spec)
    settings = ayarlari_kur(spec, sinir_kutu, fisil)
    from cekirdek import mesh_tally as _mt
    tallies = tallyleri_kur(spec, nesneler, sinir_kutu, _mt.model_z_araligi(spec, kok))

    model = openmc.Model(geometry=geometry, materials=materials,
                         settings=settings, tallies=tallies)

    # --- kinetik parametreler (IFP) ---
    # add_kinetics_parameters_tallies() modele tally EKLER; bu yuzden model
    # kurulurken yapilmalidir, sonradan degil (onbellek kimliginin parcasi).
    kin = spec["ayarlar"].get("kinetik") or {}
    if kin.get("var") and settings.run_mode == "eigenvalue":
        # beta_i (DelayedGroupFilter) + lambda_i tally'si: cekirdek/kinetik_oku.py
        from cekirdek import kinetik_oku
        kinetik_oku.tallyleri_ekle(model, kin)
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
    spektrum.tally_ekle(spec, model, nesneler)   # Y3: spektrum/dort faktor (cekirdek/spektrum.py)
    _yuzey.tally_ekle(spec, model, sinir_kutu)   # Y7: yuzey akimi (cekirdek/yuzey_akim.py)
    bilgi["mgxs"] = mgxs_uret.tally_ekle(spec, model)   # Y8: grup sabitleri (cekirdek/mgxs_uret.py)
    return model, bilgi
