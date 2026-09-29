# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_demet.py  --  Demet (kafes / lattice) tanimlari ve harita editoru
================================================================================
 YERLESIM (iki sutun)
   Sol  : harita -- kalan butun alani alir (17x17 kaydirmasiz, hucre ~30 px)
   Sag  : demet listesi + ekle dugmeleri, ozellikler, PARCA PALETI, Gelismis

 KULLANICI HARF GORMEZ (arayuz/izgara.py)
   Paletten bir parca secilir (firca) ve izgarada tiklanir ya da basili
   tutup SURUKLENIR; sag tik o hucredeki parcayi firca yapar. Spec yine
   harf haritasi + anahtar tutar: harfler kayitta otomatik atanir
   (izgara.adlardan_harita) ve var olan harfler korunur -- dosya bicimi
   degismez, eski dosyalar birebir geri yazilir.

 YALNIZCA ANLAMLI OLAN SUNULUR
   Palet   : cubuklar; AYNI tipte ve dongu kurmayan ic demetler (kendisi,
             onu iceren demet, altigen icinde kare ya da tersi cikmaz);
             plaka yalnizca plaka modelinde ve kare demette; malzeme
             hucresi olarak yalnizca sogutucu/moderator (Gelismis: hepsi +
             Bos). Haritada ZATEN gecen her sey her zaman listelenir.
   Tip     : "+ Kare demet" / "+ Altigen demet" ile belirlenir; sonradan
             degismez (tip degisimi haritayi yok ediyordu). Tam kor (kare
             kor haritasi) modelinde altigen demet sunulmaz.
   Adim    : alt siniri haritadaki en buyuk cubuk dis capi / plaka ya da ic
             demet olcusu (dosyadaki daha kucuk deger sessizce buyutulmez).
   Dis dolgu: kare demet tek demet modelinin kendisiyse (sinir = demet
             zarfi) hic kullanilmaz -> gizli (degeri silinmez).
   Varsayilan firca haritada EN SIK gecen parca.
================================================================================
"""

import copy
from collections import Counter

from PySide6 import QtCore, QtWidgets

from cekirdek import altigen, sema, uygunluk
from arayuz import izgara
from arayuz.ortak import BosDurum, GelismisBolum, SekmeTabani, baslik, ipucu, renk_simgesi, \
    sayi, tamsayi
from arayuz.sekme_cubuk import (BOS_ETIKETI, MalzemeKutusu, ad_hatasi, benzersiz_ad,
                                parca_adini_degistir, parca_kullanimlari, rol_listesi, _renk)

TUR_ADI = {"kare": "Kare demet", "altigen": "Altıgen demet"}


# ============================================================================
# saf yardimcilar (testler/test_parca_demet.py sinar)
# ============================================================================

def demet_turleri(spec):
    """Bu modelde eklenebilecek demet tipleri (uygunluk.parca_turleri)."""
    t = uygunluk.parca_turleri(spec)
    return tuple(tip for tip in ("kare", "altigen") if t.get("demet_" + tip))

def _harita_adlari(d):
    return izgara.harita_adlara(d.get("harita"), d.get("anahtar"))


def iceriyor(spec, kapsayan, aranan, derinlik=0):
    """'kapsayan' demeti (ic ice) 'aranan' adli parcayi iceriyor mu?"""
    if derinlik > 12 or not kapsayan:
        return False
    if kapsayan == aranan:
        return True
    d = sema.demet_bul(spec, kapsayan)
    if d is None:
        return False
    return any(iceriyor(spec, h, aranan, derinlik + 1)
               for h in set((d.get("anahtar") or {}).values()) if h)


def ic_demet_adaylari(spec, d):
    """
    (uygun, sigmayan): bu demete ic demet olarak konabilecek demetler.
    Aday: AYNI tipte (kare icine kare, altigen icine altigen), kendisi
    olmayan ve onu icermeyen (dongu yok). uygun = zarfi adima sigan;
    sigmayan = tip/dongu uygun ama adim kucuk (dogrula tasma hatasi verirdi).
    """
    from cekirdek import dogrula
    tur = d.get("tur", "kare")
    P = float(d.get("adim") or 0.0) * (1.0 + 1e-9)
    uygun, sigmayan = [], []
    for x in spec.get("demetler", []):
        if (x["ad"] == d["ad"] or x.get("tur", "kare") != tur
                or iceriyor(spec, x["ad"], d["ad"])):
            continue
        gx, gy, dar = dogrula._kafes_olculeri(x)
        (uygun if (dar if tur == "altigen" else max(gx, gy)) <= P else sigmayan).append(x["ad"])
    return uygun, sigmayan


def palet_izinli(spec, d, tum_malzemeler=False):
    """
    Bu demete yerlestirilebilecek adlar (kume). Haritada zaten gecenler
    CAGIRAN tarafindan eklenir (bkz. palet_listesi).
    """
    tur = d.get("tur", "kare")
    izin = {c["ad"] for c in spec.get("cubuklar", [])}
    if tur == "kare" and uygunluk.parca_turleri(spec)["plaka"]:
        izin |= {p["ad"] for p in spec.get("plakalar", [])}
    izin |= set(ic_demet_adaylari(spec, d)[0])
    if tum_malzemeler:
        izin |= {m["ad"] for m in spec.get("malzemeler", [])}
        izin.add(sema.BOSLUK)
    else:
        izin |= set(rol_listesi(spec, "sogutucu"))
        izin |= set(rol_listesi(spec, "moderator"))
    return izin


def palet_listesi(spec, d, tum_malzemeler=False):
    """
    Paletin girdileri [(ad, etiket, rgb, tur_etiketi)] -- izgara.palet_ogeleri
    turler/haric suzgeciyle: yalnizca bu demette uygun olanlar + haritada
    zaten gecenler (veri gizlenmez).
    """
    kullanilan = {a for satir in _harita_adlari(d) for a in satir if a}
    istenen = palet_izinli(spec, d, tum_malzemeler) | kullanilan
    bolum = {"cubuk": "cubuklar", "plaka": "plakalar", "demet": "demetler",
             "malzeme": "malzemeler"}
    turler, haric = [], []
    for tur in ("cubuk", "plaka", "demet", "malzeme"):
        adlar = [x["ad"] for x in spec.get(bolum[tur], [])]
        if any(a in istenen for a in adlar):
            turler.append(tur)
            haric += [a for a in adlar if a not in istenen]
    if sema.BOSLUK in istenen:
        turler.append("bosluk")
    ogeler = izgara.palet_ogeleri(spec, turler=tuple(turler), haric=tuple(haric))
    return [(ad, BOS_ETIKETI if ad == sema.BOSLUK else etiket, rgb, tur_e)
            for ad, etiket, rgb, tur_e in ogeler]


def en_sik_parca(adlar):
    """Haritada en sik gecen parca adi (esitlikte ilk gorulen); bossa None."""
    sayac = Counter(a for satir in adlar for a in satir if a)
    if not sayac:
        return None
    en_cok = max(sayac.values())
    for satir in adlar:
        for a in satir:
            if a and sayac[a] == en_cok:
                return a
    return None


def _plaka_olcusu(p):
    tx = p["plaka_sayisi"] * (2 * p["zarf_kalinlik"] + p["et_kalinlik"]) \
        + (p["plaka_sayisi"] + 1) * p["kanal_kalinlik"]
    ty = p["plaka_genislik"] + 2 * (p.get("yan_levha_kalinlik") or 0.0)
    return tx, ty


def gerekli_adim(spec, d):
    """
    (en_kucuk_adim, sebep) -- haritadaki en buyuk icerigin hucreye sigmasi
    icin gereken adim. dogrula._kafes_icerik_kontrol ile AYNI olcu:
      cubuk     : dis cap (2 x en buyuk sonlu yaricap)
      plaka     : eleman dis olcusunun buyuk kenari
      ic demet  : kare -> zarfin buyuk kenari; altigen -> duz yuzden duz yuze
    """
    from cekirdek import dogrula
    en, sebep = 0.0, ""
    tur = d.get("tur", "kare")
    for ad in {a for satir in _harita_adlari(d) for a in satir if a}:
        olcu, metin = 0.0, ""
        c = sema.cubuk_bul(spec, ad)
        if c is not None:
            olcu = dogrula._cubuk_dis_capi(c) or 0.0
            metin = "'%s' çubuğunun dış çapı" % ad
        elif sema.plaka_bul(spec, ad) is not None:
            olcu = max(_plaka_olcusu(sema.plaka_bul(spec, ad)))
            metin = "'%s' plaka elemanının ölçüsü" % ad
        elif sema.demet_bul(spec, ad) is not None:
            gx, gy, dar = dogrula._kafes_olculeri(sema.demet_bul(spec, ad))
            olcu = dar if tur == "altigen" else max(gx, gy)
            metin = "iç demet '%s' ölçüsü" % ad
        if olcu > en:
            en, sebep = olcu, metin
    return en, sebep


def dis_dolgu_anlamli(spec, d):
    """
    'Kafes disi dolgu' kullaniliyor mu? Kare demet tek_demet modelinin kok
    dolgusuysa (ana dolgu ya da eksenel katman dolgusu) model siniri demet
    zarfidir -- dis bolgeye hic ulasilmaz. Altigen demette kose bosluklari,
    ic ice / tam kor / tamburlu kullaniminda hucre ya da silindir kalanini
    doldurur.
    """
    if d.get("tur", "kare") == "altigen":
        return True
    kor = spec.get("kor") or {}
    if kor.get("tur") != "tek_demet":
        return True
    kok = {kor.get("demet")} | {b.get("dolgu") for b in
                                (kor.get("eksenel") or {}).get("bolgeler") or []}
    if d["ad"] not in kok:
        return True
    ic_ice = any(d["ad"] in (x.get("anahtar") or {}).values()
                 for x in spec.get("demetler", []) if x["ad"] != d["ad"])
    return ic_ice


def _yakit_cubugu(spec):
    """Yeni demetin dolgusu: yakit bolgeli ilk cubuk, yoksa ilk cubuk."""
    yakit = set(rol_listesi(spec, "yakit"))
    cubuklar = spec.get("cubuklar", [])
    for c in cubuklar:
        if any(b.get("malzeme") in yakit for b in c.get("bolgeler") or []):
            return c
    return cubuklar[0] if cubuklar else None


def yeni_demet(spec, tur, ad):
    """Yakit cubuguyla dolu yeni demet; adim cubuga sigacak kadar."""
    from cekirdek import dogrula
    c = _yakit_cubugu(spec)
    cap = (dogrula._cubuk_dis_capi(c) or 0.0) if c else 0.0
    sog = (rol_listesi(spec, "sogutucu")
           or [m["ad"] for m in spec.get("malzemeler", [])
               if m["ad"] not in rol_listesi(spec, "yakit")]
           or [sema.BOSLUK])[0]
    if tur == "altigen":
        halka = 5
        adim = max(1.0, round(cap * 1.33, 4))
        adlar = [[c["ad"]] * u for u in altigen.halka_uzunluklari(halka)]
        harita, anahtar = izgara.adlardan_harita(adlar)
        return sema.demet_altigen(ad, adim, halka, harita, anahtar, sog)
    n = 5
    adim = max(1.26, round(cap * 1.33, 4))
    harita, anahtar = izgara.adlardan_harita([[c["ad"]] * n for _ in range(n)])
    return sema.demet(ad, adim, [n, n], harita, anahtar, sog)


# ============================================================================
# sekme
# ============================================================================

class DemetSekmesi(SekmeTabani):
    """Demet listesi + boyanabilir kare/altigen harita + parca paleti."""

    KONU = "demet"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._firca_demeti = None      # firca hangi demet icin secildi

        # ================= sol: harita =================
        self.bos = BosDurum("Henüz demet yok", "", "+ Kare demet")
        self.bos.eylem.connect(lambda: self._yeni(self._bos_tipi))
        self._bos_tipi = "kare"
        self.kare_izgara = izgara.KareIzgara()
        self.hex_izgara = izgara.AltigenIzgara()
        for iz in (self.kare_izgara, self.hex_izgara):
            iz.etiketleri_goster(True)
            iz.degisti.connect(self._harita_kaydet)
            iz.firca_istendi.connect(self._firca_istendi)
        self.harita_yigin = QtWidgets.QStackedWidget()
        self.harita_yigin.addWidget(self.bos)            # 0
        self.harita_yigin.addWidget(self.kare_izgara)    # 1
        self.harita_yigin.addWidget(self.hex_izgara)     # 2
        self.harita_yigin.setMinimumSize(240, 240)

        # ================= sag: liste =================
        self.liste = QtWidgets.QListWidget()
        self.liste.setIconSize(QtCore.QSize(14, 14))
        self.liste.currentRowChanged.connect(self._secim_degisti)
        self.d_kare = QtWidgets.QPushButton("+ Kare demet")
        self.d_hex = QtWidgets.QPushButton("+ Altıgen demet")
        # Kopyala/Sil baslik satirinda: dar sutunda dikey yer harcamasin.
        self.d_kopya = QtWidgets.QToolButton()
        self.d_kopya.setText("Kopyala")
        self.d_sil = QtWidgets.QToolButton()
        self.d_sil.setText("Sil")
        for b in (self.d_kopya, self.d_sil):
            b.setAutoRaise(True)
            b.setCursor(QtCore.Qt.PointingHandCursor)
        self.d_kopya.setToolTip("Seçili demetin kopyasını ekler.")
        self.d_sil.setToolTip("Seçili demeti siler (kullanılıyorsa önce sorar).")
        self.d_kare.clicked.connect(lambda: self._yeni("kare"))
        self.d_hex.clicked.connect(lambda: self._yeni("altigen"))
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)

        # ================= sag: ozellikler =================
        self.ad = QtWidgets.QLineEdit()
        self.ad.editingFinished.connect(self._ad_degisti)
        self.ad_hata = QtWidgets.QLabel("")
        self.ad_hata.setWordWrap(True)
        self.ad_hata.setVisible(False)
        self.adim = sayi(1.26, 5, 0.0001, 1000.0, 0.01, "cm")
        self.adim.setKeyboardTracking(False)
        self.nx = tamsayi(17, 1, 200)
        self.ny = tamsayi(17, 1, 200)
        self.halka = tamsayi(7, 1, 40, 1, "halka")
        # Yazarken ara degerler islenmesin: "17" secip "15" yazmak once nx=1
        # yapip haritayi TEK SUTUNA kirpiyordu. Deger Enter/odak kaybinda ya da
        # ok tuslariyla islenir.
        for _w in (self.nx, self.ny, self.halka):
            _w.setKeyboardTracking(False)
        self.dis = None                                  # her yuklemede kurulur
        self.ozet = QtWidgets.QLabel("-")

        self.ozellik = QtWidgets.QWidget()
        oz = QtWidgets.QVBoxLayout(self.ozellik)
        oz.setContentsMargins(0, 0, 0, 0)
        self.oz_baslik = baslik("Kare demet")
        oz.addWidget(self.oz_baslik)
        self.form = QtWidgets.QFormLayout()
        self.form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.form.addRow("Ad:", self.ad)
        self.form.addRow(self.ad_hata)
        self.adim.setToolTip("Komşu hücre merkezleri arası uzaklık (pitch).")
        self.form.addRow("Adım (pitch):", self.adim)
        kare_boyut = QtWidgets.QWidget()
        kb = QtWidgets.QHBoxLayout(kare_boyut)
        kb.setContentsMargins(0, 0, 0, 0)
        self.nx.setMinimumWidth(64)
        self.ny.setMinimumWidth(64)
        kb.addWidget(self.nx)
        kb.addWidget(QtWidgets.QLabel("×"))
        kb.addWidget(self.ny)
        kb.addWidget(QtWidgets.QLabel("hücre"))
        kb.addStretch(1)
        self.nx.setToolTip("Sütun sayısı (x)")
        self.ny.setToolTip("Satır sayısı (y)")
        self.e_kare_boyut = QtWidgets.QLabel("Boyut:")
        self.w_kare_boyut = kare_boyut
        self.form.addRow(self.e_kare_boyut, self.w_kare_boyut)
        self.e_halka = QtWidgets.QLabel("Halka sayısı:")
        self.halka.setToolTip("Merkez dahil halka sayısı; k. halkada 6k hücre vardır.")
        self.form.addRow(self.e_halka, self.halka)
        self._dis_yer = QtWidgets.QWidget()
        dy = QtWidgets.QHBoxLayout(self._dis_yer)
        dy.setContentsMargins(0, 0, 0, 0)
        self._dis_duzen = dy
        self.e_dis = QtWidgets.QLabel("Demet dışı:")
        self.e_dis.setToolTip("Demet hücrelerinin dışında kalan alanı dolduran malzeme.")
        self.form.addRow(self.e_dis, self._dis_yer)
        self.form.addRow("Toplam ölçü:", self.ozet)
        oz.addLayout(self.form)

        # ================= sag: palet =================
        self.palet = izgara.ParcaPaleti()
        self.palet.secildi.connect(self._firca_degisti)
        self.palet.liste.setMinimumHeight(66)
        self.d_hepsi = QtWidgets.QPushButton("Tümünü doldur")
        self.d_hepsi.setToolTip("Bütün hücreleri seçili parçayla doldurur (Ctrl+Z geri alır).")
        self.d_hepsi.clicked.connect(self._tumunu_doldur)
        self.halka_secim = QtWidgets.QComboBox()
        self.d_halka_doldur = QtWidgets.QPushButton("Halkayı doldur")
        self.d_halka_doldur.clicked.connect(self._halka_doldur)
        self.halka_secim.setToolTip("Doldurulacak halka (merkezden dışa numaralı)")
        self.palet_kutu = QtWidgets.QWidget()
        pk = QtWidgets.QVBoxLayout(self.palet_kutu)
        pk.setContentsMargins(0, 0, 0, 0)
        pk.addWidget(baslik("Parça paleti"))
        pk.addWidget(ipucu("Tıklayın ya da sürükleyin · sağ tık: parçayı seç"))
        pk.addWidget(self.palet, 1)
        self.palet_notu = ipucu("")
        self.palet_notu.setVisible(False)
        pk.addWidget(self.palet_notu)
        pk.addWidget(self.halka_secim)
        doldur = QtWidgets.QHBoxLayout()
        doldur.addWidget(self.d_halka_doldur)
        doldur.addWidget(self.d_hepsi)
        pk.addLayout(doldur)

        # ================= sag: gelismis =================
        self.gelismis = GelismisBolum("demet_gelismis")
        gf = QtWidgets.QFormLayout()
        gf.setContentsMargins(0, 0, 0, 0)
        self.yonelim = QtWidgets.QComboBox()
        self.yonelim.addItem("Üst/alt yüzler yatay (tepede hücre)", "y")
        self.yonelim.addItem("Sağ/sol yüzler düşey (sağda hücre)", "x")
        self.e_yonelim = QtWidgets.QLabel("Yönelim:")
        gf.addRow(self.e_yonelim, self.yonelim)
        self.tum_malzemeler = QtWidgets.QCheckBox("Palette bütün malzemeler ve Boş hücre")
        self.tum_malzemeler.setToolTip(
            "Varsayılan palet yalnızca çubukları, iç demetleri ve soğutucu/moderatör "
            "hücrelerini gösterir.")
        self.tum_malzemeler.toggled.connect(lambda _a: self._palet_yenile())
        gf.addRow(self.tum_malzemeler)
        gw = QtWidgets.QWidget()
        gw.setLayout(gf)
        self.gelismis.ekle(gw)

        # ================= sag sutun =================
        sag = QtWidgets.QWidget()
        sag.setMinimumWidth(260)
        sag.setMaximumWidth(340)
        sd = QtWidgets.QVBoxLayout(sag)
        sd.setContentsMargins(0, 0, 0, 0)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(baslik("Demetler"))
        ust.addStretch(1)
        ust.addWidget(self.d_kopya)
        ust.addWidget(self.d_sil)
        sd.addLayout(ust)
        sd.addWidget(self.liste)
        r1 = QtWidgets.QHBoxLayout()
        r1.addWidget(self.d_kare)
        r1.addWidget(self.d_hex)
        sd.addLayout(r1)
        sd.addWidget(self.ozellik)
        sd.addWidget(self.palet_kutu, 1)
        sd.addWidget(self.gelismis)
        self._bosluk = QtWidgets.QWidget()               # bos durumda sutunu iter
        sd.addWidget(self._bosluk, 1)
        self._sag = sag

        duzen = QtWidgets.QHBoxLayout(self)
        duzen.addWidget(self.harita_yigin, 1)
        duzen.addWidget(sag, 0)

        self.adim.valueChanged.connect(self._kaydet)
        self.yonelim.currentIndexChanged.connect(self._yonelim_degisti)
        self.nx.valueChanged.connect(self._boyut_degisti)
        self.ny.valueChanged.connect(self._boyut_degisti)
        self.halka.valueChanged.connect(self._halka_degisti)

    # ==================================================================
    def doldur(self):
        secili = self._secili_ad()
        self.liste.blockSignals(True)
        try:
            self.liste.clear()
            renk = {o[0]: o[2] for o in izgara.palet_ogeleri(self.spec, turler=("demet",))}
            for d in self.spec.get("demetler", []):
                if d.get("tur") == "altigen":
                    ek = "altıgen, %d halka" % (d.get("halka_sayisi") or 1)
                else:
                    nx, ny = (d.get("boyut") or [1, 1])[:2]
                    ek = "kare %d×%d" % (nx, ny)
                oge = QtWidgets.QListWidgetItem(renk_simgesi(renk.get(d["ad"])),
                                                "%s  · %s" % (d["ad"], ek))
                oge.setData(QtCore.Qt.UserRole, d["ad"])
                self.liste.addItem(oge)
            hedef = 0
            for i in range(self.liste.count()):
                if self.liste.item(i).data(QtCore.Qt.UserRole) == secili:
                    hedef = i
            if self.liste.count():
                self.liste.setCurrentRow(hedef)
        finally:
            self.liste.blockSignals(False)
        satir = max(self.liste.sizeHintForRow(0), self.liste.fontMetrics().height() + 4)
        self.liste.setFixedHeight(min(max(self.liste.count(), 1), 5) * (satir + 2)
                                  + 2 * self.liste.frameWidth() + 2)
        self._eylemleri_guncelle()
        self._secim_degisti(self.liste.currentRow())

    def _eylemleri_guncelle(self):
        turler = demet_turleri(self.spec)
        cubuk_var = bool(self.spec.get("cubuklar"))
        self.d_kare.setVisible("kare" in turler)
        self.d_hex.setVisible("altigen" in turler)
        for d, tur in ((self.d_kare, "kare"), (self.d_hex, "altigen")):
            d.setEnabled(cubuk_var)
            d.setToolTip(("%s ekler; çubukları paletten seçip ızgaraya yerleştirirsiniz."
                          % TUR_ADI[tur]) if cubuk_var else
                         "Önce Parçalar sekmesinde en az bir çubuk tanımlayın.")
        secili = self._secili() is not None
        self.d_kopya.setEnabled(secili)
        self.d_sil.setEnabled(secili)
        # Demet kullanmayan modelde (pin hucre, plaka) sekme gizlidir ama yine
        # yuklenir: tip listesi bos olabilir.
        self._bos_tipi = turler[0] if turler else None
        if not turler:
            self.bos.ayarla("Bu modelde demet kullanılmıyor",
                            "Bu kor türü demet içermez. Demet gerekiyorsa kor türünü "
                            "model başlığındaki “Türü değiştir…” ile değiştirin.", "")
        elif not cubuk_var:
            self.bos.ayarla("Önce çubuk gerekli",
                            "Demet, Parçalar sekmesinde tanımlanan çubuklardan kurulur. "
                            "Önce bir yakıt çubuğu ekleyin.", "")
        else:
            self.bos.ayarla("Henüz demet yok",
                            "Bir demet ekleyin; çubukları sağdaki paletten seçip ızgaraya "
                            "tıklayarak ya da sürükleyerek yerleştirin.",
                            "+ " + TUR_ADI[self._bos_tipi])

    def _onay_al(self, baslik_, metin):
        """Veri silen islemler icin onay. Testler bunu degistirir (modal acilmaz)."""
        cevap = QtWidgets.QMessageBox.question(
            self, baslik_, metin,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return cevap == QtWidgets.QMessageBox.Yes

    def _bilgi(self, baslik_, metin):
        """Bilgi mesaji (testler degistirir)."""
        QtWidgets.QMessageBox.information(self, baslik_, metin)

    def _geri_al_kutu(self, kutu, deger):
        """Reddedilen degisiklikte kutuyu sinyal islemeden eski degere dondurur."""
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            if isinstance(kutu, QtWidgets.QComboBox):
                kutu.setCurrentIndex(max(kutu.findData(deger), 0))
            else:
                kutu.setValue(deger)
        finally:
            self._yukleniyor = eski

    def _temizle(self):
        """Demet secili degil: harita yerine bos durum; ozellikler devre disi ve gizli."""
        self.harita_yigin.setCurrentWidget(self.bos)
        for w in (self.ozellik, self.palet_kutu, self.gelismis):
            w.setEnabled(False)
            w.setVisible(False)
        self._bosluk.setVisible(True)
        self.ad.clear()
        self.kare_izgara.yukle([])
        self.hex_izgara.yukle([], 0)
        self.ozet.setText("-")

    def _secili_ad(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else None

    def _secili(self):
        ad = self._secili_ad()
        return sema.demet_bul(self.spec, ad) if ad and self.spec else None

    def _izgara(self, d=None):
        d = d or self._secili()
        return self.hex_izgara if d is not None and d.get("tur") == "altigen" \
            else self.kare_izgara

    def _secim_degisti(self, _satir):
        d = self._secili()
        self.d_kopya.setEnabled(d is not None)
        self.d_sil.setEnabled(d is not None)
        if d is None:
            self._temizle()
            return
        for w in (self.ozellik, self.palet_kutu, self.gelismis):
            w.setEnabled(True)
            w.setVisible(True)
        self._bosluk.setVisible(False)
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            hex_mi = d.get("tur") == "altigen"
            self.oz_baslik.setText(TUR_ADI["altigen" if hex_mi else "kare"])
            self.ad.setText(d["ad"])
            self.ad_hata.setVisible(False)
            self._adim_siniri(d)
            self.adim.setValue(d["adim"])
            self.nx.setValue((d.get("boyut") or [1, 1])[0])
            self.ny.setValue((d.get("boyut") or [1, 1])[1])
            self.halka.setValue(d.get("halka_sayisi") or 7)
            self.yonelim.setCurrentIndex(max(self.yonelim.findData(d.get("yonelim", "y")), 0))
            for w in (self.e_kare_boyut, self.w_kare_boyut):
                w.setVisible(not hex_mi)
            for w in (self.e_halka, self.halka, self.halka_secim, self.d_halka_doldur,
                      self.e_yonelim, self.yonelim):
                w.setVisible(hex_mi)
            self._dis_doldur(d)
            self._halka_secenekleri(d)
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = eski

    # ==================================================================
    def _dis_doldur(self, d):
        while self._dis_duzen.count():
            w = self._dis_duzen.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        yakit = set(rol_listesi(self.spec, "yakit"))
        adaylar = [m["ad"] for m in self.spec.get("malzemeler", []) if m["ad"] not in yakit]
        self.dis = MalzemeKutusu(self.spec, d.get("dolgu_disi"), adaylar, bos=True,
                                 rol_goster=False)
        self.dis.currentIndexChanged.connect(self._kaydet)
        self._dis_duzen.addWidget(self.dis, 1)
        anlamli = dis_dolgu_anlamli(self.spec, d)
        self.e_dis.setVisible(anlamli)
        self._dis_yer.setVisible(anlamli)

    def _halka_secenekleri(self, d):
        """Halkayi doldur: merkezden disa numaralanir (merkez, 1. halka ...)."""
        self.halka_secim.clear()
        if d.get("tur") != "altigen":
            return
        n = d.get("halka_sayisi") or 1
        for k in range(n):
            if k == 0:
                metin = "Merkez hücre"
            else:
                metin = "%d. halka · %d hücre%s" % (k, 6 * k, " (en dış)" if k == n - 1 else "")
            # izgara.halkayi_doldur DISTAN ICE indeks kullanir.
            self.halka_secim.addItem(metin, n - 1 - k)
        self.halka_secim.setCurrentIndex(self.halka_secim.count() - 1)

    def _adim_siniri(self, d):
        """Adimin alt siniri: haritadaki en buyuk icerik (dosyadaki daha kucuk
        deger sessizce buyutulmez -- dogrulama onu hata olarak bildirir)."""
        gerekli, sebep = gerekli_adim(self.spec, d)
        alt = max(0.0001, min(gerekli, float(d.get("adim") or gerekli or 0.0001)))
        eski = self.adim.blockSignals(True)
        try:
            self.adim.setMinimum(alt)
        finally:
            self.adim.blockSignals(eski)
        self.adim.setToolTip(
            "Komşu hücre merkezleri arası uzaklık (pitch)."
            + ("\nEn az %.5f cm: %s." % (gerekli, sebep) if gerekli else ""))

    def _palet_yenile(self, d=None, firca=None):
        d = d or self._secili()
        if d is None:
            return
        ogeler = palet_listesi(self.spec, d, self.tum_malzemeler.isChecked())
        adlar = _harita_adlari(d)
        if firca is None:
            onceki = self.palet.secili() if self._firca_demeti == d["ad"] else None
            firca = onceki if onceki in [o[0] for o in ogeler] else en_sik_parca(adlar)
        self._firca_demeti = d["ad"]
        sigmayan = ic_demet_adaylari(self.spec, d)[1]
        self.palet_notu.setText(
            "Adıma sığmayan iç demetler: %s" % ", ".join(sigmayan) if sigmayan else "")
        self.palet_notu.setToolTip(
            "Bir demeti iç demet olarak yerleştirmek için adım en az o demetin "
            "ölçüsü kadar olmalı." if sigmayan else "")
        self.palet_notu.setVisible(bool(sigmayan))
        self.palet.parcalari_ayarla(ogeler, secili=firca)
        renkler = self.palet.renkler()
        for iz in (self.kare_izgara, self.hex_izgara):
            iz.renkleri_ayarla(renkler)
            iz.firca_ayarla(self.palet.secili())

    def _harita_doldur(self, d):
        adlar = _harita_adlari(d)
        self._palet_yenile(d)
        renkler = self.palet.renkler()
        if d.get("tur") == "altigen":
            self.hex_izgara.yukle(adlar, d.get("halka_sayisi") or len(adlar),
                                  d.get("yonelim", "y"), renkler)
            self.harita_yigin.setCurrentWidget(self.hex_izgara)
        else:
            self.kare_izgara.yukle(adlar, renkler)
            self.harita_yigin.setCurrentWidget(self.kare_izgara)

    def _ozet_guncelle(self, d):
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or 1
            gx, gy = altigen.kapsayan_olcu(halka, d["adim"], d.get("yonelim", "y"))
            self.ozet.setText("%.3f × %.3f cm\n%d hücre, %d halka"
                              % (gx, gy, altigen.toplam_hucre(halka), halka))
        else:
            nx, ny = d["boyut"]
            self.ozet.setText("%.3f × %.3f cm\n%d hücre"
                              % (d["adim"] * nx, d["adim"] * ny, nx * ny))

    # ==================================================================
    # firca ve boyama
    # ==================================================================
    def _firca_degisti(self, ad):
        for iz in (self.kare_izgara, self.hex_izgara):
            iz.firca_ayarla(ad)

    def _firca_istendi(self, ad):
        if not self.palet.sec(ad):
            # Palette olmayan (or. yeni gizlenen) parca: listeye alinsin.
            self._palet_yenile(firca=ad)

    def _harita_kaydet(self):
        """Bir boyama darbesi bitti: adlar -> harf haritasi (harfler korunur)."""
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        adlar = self._izgara(d).adlar()
        try:
            harita, anahtar = izgara.adlardan_harita(adlar, d.get("anahtar"), d.get("harita"))
        except ValueError as e:
            self._bilgi("Çok fazla parça", str(e))
            self._harita_doldur(d)
            return
        d["harita"], d["anahtar"] = harita, anahtar
        self._adim_siniri(d)
        self.bildir()

    def _tumunu_doldur(self):
        ad = self.palet.secili()
        if self._secili() is None or ad is None:
            return
        self._izgara().tumunu_doldur(ad)          # degisti -> _harita_kaydet

    def _halka_doldur(self):
        d = self._secili()
        ad = self.palet.secili()
        ix = self.halka_secim.currentData()
        if d is None or d.get("tur") != "altigen" or ad is None or ix is None:
            return
        self.hex_izgara.halkayi_doldur(int(ix), ad)

    # ==================================================================
    # ozellik degisiklikleri
    # ==================================================================
    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        adim_degisti = d.get("adim") != self.adim.value()
        d["adim"] = self.adim.value()
        if self.dis is not None:
            d["dolgu_disi"] = self.dis.currentData()
        self._ozet_guncelle(d)
        if adim_degisti:
            self._palet_yenile(d)          # sigan ic demetler degisebilir
        self.bildir()

    def _yonelim_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        d["yonelim"] = self.yonelim.currentData()
        self._yukleniyor = True
        try:
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self.bildir()

    def _varsayilan_harf(self, d):
        """Buyutmede yeni hucreler haritada EN SIK gecen parcayla dolar."""
        sayac = Counter(h for satir in d.get("harita") or [] for h in satir)
        if sayac:
            return sayac.most_common(1)[0][0]
        harfler = sorted((d.get("anahtar") or {}).keys())
        return harfler[0] if harfler else izgara.BOS_HARF

    def _boyut_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None or d.get("tur") == "altigen":
            return
        nx, ny = self.nx.value(), self.ny.value()
        eski_nx, eski_ny = (d.get("boyut") or [nx, ny])[:2]
        if (nx, ny) == (eski_nx, eski_ny):
            return
        if nx < eski_nx or ny < eski_ny:
            # Kucultme haritanin sag/alt kismini KIRPAR; eskiden sessizdi.
            if not self._onay_al(
                    "Harita küçülüyor",
                    "Demet %d×%d'den %d×%d'ye küçülüyor: haritanın sağ/alt kısmındaki "
                    "hücreler silinecek (büyütmek onları geri getirmez).\n\n"
                    "Devam edilsin mi?" % (eski_nx, eski_ny, nx, ny)):
                self._geri_al_kutu(self.nx, eski_nx)
                self._geri_al_kutu(self.ny, eski_ny)
                return
        eski = d.get("harita") or []
        varsayilan = self._varsayilan_harf(d)
        yeni = []
        for r in range(ny):
            eski_satir = eski[r] if r < len(eski) else ""
            yeni.append("".join(eski_satir[c] if c < len(eski_satir) else varsayilan
                                for c in range(nx)))
        d["boyut"] = [nx, ny]
        d["harita"] = yeni
        self._yukleniyor = True
        try:
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self._liste_metni(d)
        self.bildir()

    def _halka_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None or d.get("tur") != "altigen":
            return
        halka = self.halka.value()
        eski_halka = d.get("halka_sayisi") or halka
        if halka == eski_halka:
            return
        if halka < eski_halka:
            # Halka azaltmak DIS halkalari siler; eskiden sessizdi.
            if not self._onay_al(
                    "Halka sayısı azalıyor",
                    "Halka sayısı %d'den %d'ye iniyor: dıştaki %d halka silinecek "
                    "(artırmak onları geri getirmez).\n\nDevam edilsin mi?"
                    % (eski_halka, halka, eski_halka - halka)):
                self._geri_al_kutu(self.halka, eski_halka)
                return
        d["halka_sayisi"] = halka
        d["boyut"] = [halka, halka]
        d["harita"] = altigen.harita_yeniden_boyutlandir(
            d.get("harita"), halka, self._varsayilan_harf(d))
        self._yukleniyor = True
        try:
            self._halka_secenekleri(d)
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self._liste_metni(d)
        self.bildir()

    def _liste_metni(self, d):
        oge = self.liste.currentItem()
        if oge is None:
            return
        if d.get("tur") == "altigen":
            ek = "altıgen, %d halka" % (d.get("halka_sayisi") or 1)
        else:
            ek = "kare %d×%d" % tuple((d.get("boyut") or [1, 1])[:2])
        oge.setText("%s  · %s" % (d["ad"], ek))

    # ==================================================================
    # liste islemleri
    # ==================================================================
    def _sec(self, ad):
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == ad:
                self.liste.setCurrentRow(i)
                return

    def _yeni(self, tur):
        """'+ Kare demet' / '+ Altigen demet'. Kontrol ettigi sey mesajiyla ayni."""
        if tur not in demet_turleri(self.spec):
            return None
        if not self.spec.get("cubuklar"):
            self._bilgi("Önce çubuk gerekli",
                        "Demet kurmadan önce Parçalar sekmesinde en az bir çubuk "
                        "tanımlayın.")
            return None
        ad = benzersiz_ad(self.spec, "demet_altigen" if tur == "altigen" else "demet_kare")
        self.spec.setdefault("demetler", []).append(yeni_demet(self.spec, tur, ad))
        kor = self.spec.get("kor") or {}
        # Tek demet modelinde kor henuz bir demete isaret etmiyorsa bu demet
        # atanir: bos modelde ilk demet eklenince model hemen kurulur.
        if kor.get("tur") == "tek_demet" and (
                not kor.get("demet") or sema.demet_bul(self.spec, kor["demet"]) is None):
            kor["demet"] = ad
        self.spec_yukle(self.spec)
        self._sec(ad)
        self.bildir()
        return ad

    def _kopyala(self):
        d = self._secili()
        if d is None:
            return
        y = copy.deepcopy(d)
        y["ad"] = benzersiz_ad(self.spec, d["ad"])
        self.spec["demetler"].append(y)
        self.spec_yukle(self.spec)
        self._sec(y["ad"])
        self.bildir()

    def _sil(self):
        ad = self._secili_ad()
        if ad is None:
            return
        yerler = parca_kullanimlari(self.spec, ad)
        if yerler and not self._onay_al(
                "Demet kullanılıyor",
                "'%s' şurada kullanılıyor: %s.\n\nSilinirse bu yerler tanımsız bir "
                "demete işaret eder ve doğrulama hata verir. Silinsin mi?"
                % (ad, ", ".join(yerler))):
            return
        self.spec["demetler"] = [d for d in self.spec["demetler"] if d["ad"] != ad]
        self.spec_yukle(self.spec)
        self.bildir()

    def _ad_degisti(self):
        d = self._secili()
        if d is None:
            return
        yeni = self.ad.text().strip()
        eski = d["ad"]
        if yeni == eski:
            self.ad_hata.setVisible(False)
            return
        hata = ad_hatasi(self.spec, yeni, eski)
        if hata:
            self.ad.setText(eski)
            self.ad_hata.setText(hata + " Ad değiştirilmedi.")
            self.ad_hata.setStyleSheet("color: %s;" % _renk("hata"))
            self.ad_hata.setVisible(True)
            return
        parca_adini_degistir(self.spec, eski, yeni)
        self._firca_demeti = yeni if self._firca_demeti == eski else self._firca_demeti
        self.spec_yukle(self.spec)
        self._sec(yeni)
        self.bildir()
