# -*- coding: utf-8 -*-
"""
================================================================================
 guc_harita.py  --  Cubuk bazli guc dagilimi isi haritasi
================================================================================
 Kare kafeste izgara, altigen kafeste gercek altigen yerlesim. Altigen konumlar
 cekirdek/altigen.py'den gelir -- yani harita, modelde kullanilan AYNI kaynagi
 kullanir; ayri bir cizim mantigi yoktur.

 3B modelde eksenel dilim kaydiricisi ve eksenel guc profili de gosterilir.
================================================================================
"""

import html
import math

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.patches import RegularPolygon

from PySide6 import QtCore, QtWidgets

from cekirdek import altigen, sema, guc as _guc
from cekirdek.ceviri import _, _n
from cekirdek.gunluk import kaydedici
from arayuz import guc_harita_kor as _kor, tema

_log = kaydedici(__name__)


def _aktif_yukseklik(spec):
    """Lineer guc paydasi: hedef cubugun bulundugu katmanlarin yuksekligi
    (geometri.hedef_yuksekligi; yansitici, plenum ve blanket haric; sablon
    ve agac modunda)."""
    try:
        from cekirdek import geometri
        return geometri.hedef_yuksekligi(spec)
    except Exception:
        _log.warning("aktif eksenel aralık okunamadı; kor yüksekliği kullanılıyor",
                     exc_info=True)
        return sema.model_yuksekligi(spec)


from arayuz.ortak import GelismisBolum, baslik  # noqa: E402


class GucHaritaWidget(QtWidgets.QWidget):
    """Guc dagilimi haritasi ve tepe faktorleri."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dagilim = None
        self.faktorler = None
        self.mutlak = None

        # --- denetimler ---
        self.gorunum = QtWidgets.QComboBox()
        self.gorunum.addItem(_("Çubuk toplam gücü (F_ΔH)"), "toplam")
        self.gorunum.addItem(_("Tek eksenel dilim (F_q)"), "dilim")
        self.dilim = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.dilim.setMinimum(1); self.dilim.setMaximum(1); self.dilim.setValue(1)
        self.dilim_etiket = QtWidgets.QLabel(_("Dilim %d") % 1)
        self.degerler = QtWidgets.QCheckBox(_("Değerleri haritaya yaz"))
        self.d_kaydet = QtWidgets.QPushButton(_("PNG kaydet…"))
        # Tam kor: kor olceginde demet ortalamasi / cubuk haritasi
        self.olcek = QtWidgets.QComboBox()
        self.olcek.addItem(_("Demet"), "demet")
        self.olcek.addItem(_("Çubuk"), "cubuk")
        self.olcek.setToolTip(_("Tam kor: demet ortalamaları ya da kordaki bütün "
                                "çubuklar"))
        self.olcek_etiket = QtWidgets.QLabel(_("Ölçek:"))
        # Varsayilan Cubuk (Dalga 2): tepe faktorleri cubuk olcegindedir.
        self.olcek.setCurrentIndex(self.olcek.findData("cubuk"))
        # Cok turlu guc: haritada yalniz secili cubuk turu (ortalama yine
        # BUTUN yakit cubuklari uzerinden -- deger degismez, suzulur).
        self.tur = QtWidgets.QComboBox()
        self.tur.setToolTip(_("Çok türlü güç dağılımı: haritada yalnız seçili çubuk türü "
                              "gösterilir; bağıl güç yine bütün yakıt çubuklarına göredir."))
        self.tur_etiket = QtWidgets.QLabel(_("Çubuk türü:"))
        self._ipucu_ogeleri = []      # [(x, y, yaricap, metin)] fare ipucu icin

        self.gorunum.currentIndexChanged.connect(self._ciz)
        self.dilim.valueChanged.connect(self._ciz)
        self.degerler.toggled.connect(self._ciz)
        self.d_kaydet.clicked.connect(self._kaydet)
        self.olcek.currentIndexChanged.connect(self._ciz)
        self.tur.currentIndexChanged.connect(self._ciz)

        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.olcek_etiket)
        ust.addWidget(self.olcek)
        ust.addWidget(self.tur_etiket)
        ust.addWidget(self.tur)
        ust.addWidget(QtWidgets.QLabel(_("Görünüm:")))
        ust.addWidget(self.gorunum)
        ust.addWidget(self.dilim_etiket)
        ust.addWidget(self.dilim, 1)
        ust.addWidget(self.d_kaydet)

        # --- ozet ---
        self.ozet = QtWidgets.QLabel(_("Güç dağılımı henüz hesaplanmadı."))
        self.ozet.setWordWrap(True)
        self.ozet.setTextFormat(QtCore.Qt.RichText)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ozet.setStyleSheet(
            "background: palette(alternate-base); padding: 10px; "
            "border: 1px solid palette(mid); border-radius: 8px;")

        # --- tuval ---
        self.figur = Figure(figsize=(6, 4), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.tuval.setMinimumHeight(380)
        self.arac = NavigationToolbar2QT(self.tuval, self)
        self.tuval.mpl_connect("motion_notify_event", self._fare_hareketi)

        # Belirsizlik notu kor olceginde haritanin hemen altinda da gorunur
        self.belirsizlik = QtWidgets.QLabel(_(
            "Belirsizlik: ± değerleri OpenMC'nin raporladığı sapmalardır ve "
            "iyimserdir — ardışık çevrimler arasındaki korelasyon hesaba "
            "katılmaz. Gerçek belirsizlik için önce Shannon entropisiyle kaynak "
            "yakınsamasını doğrulayın, sonra modeli en az 5–10 farklı tohumla koşun."))
        self.belirsizlik.setObjectName("soluk")
        self.belirsizlik.setWordWrap(True)

        # Nadiren gereken: deger yazimi ve matplotlib gezinme cubugu
        self.gelismis = GelismisBolum("guc_harita_gelismis")
        self.gelismis.ekle(self.degerler)
        self.gelismis.ekle(self.arac)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(baslik(_("Çubuk güç dağılımı")))
        aciklama = QtWidgets.QLabel(_(
            "F_ΔH = en yüksek çubuk gücü / ortalama (radyal). "
            "F_q = en yüksek yerel güç yoğunluğu / ortalama (radyal × eksenel, 3B gerekir). "
            "Renk ölçeği ortalamaya göre bağıldır: 1.00 = ortalama çubuk."))
        aciklama.setObjectName("soluk")
        aciklama.setWordWrap(True)
        duzen.addWidget(aciklama)
        duzen.addLayout(ust)
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(self.belirsizlik)
        duzen.addWidget(self.gelismis)
        self._tam_kor_denetimleri(False)
        self._bos(_("Henüz koşu yapılmadı"))

    # ==================================================================
    def sonuc_ayarla(self, sonuc, spec=None):
        """kosucu.sonuc_oku() ciktisindan guc bolumunu alir."""
        g = (sonuc or {}).get("guc") or {}
        self.dagilim = g.get("dagilim")
        self.faktorler = g.get("faktorler")
        self.korunum = g.get("korunum")
        # korunum_hata ham istisna metnidir (onek gerekir); korunum_notu kendi
        # basina tam cumledir ("... denetlenemedi ...") -- onek eklenmez.
        self.korunum_notlari = (
            [_("Toplamın korunumu denetlenemedi: %s") % g["korunum_hata"]]
            if g.get("korunum_hata") else []) + (
            [g["korunum_notu"]] if g.get("korunum_notu") else [])
        self.hedef_payi = g.get("hedef_payi")
        self.hedef_payi_hata = g.get("hedef_payi_hata")
        self.kategori = (spec or {}).get("kategori")
        self.mutlak = None
        if self.faktorler and spec:
            sg = spec.get("guc_dagilimi") or {}
            self.mutlak = _guc.mutlak_guc(self.faktorler, sg.get("toplam_guc"),
                                          _aktif_yukseklik(spec),
                                          hedef_payi=g.get("hedef_payi"))
        if self.faktorler:
            n = self.faktorler["eksenel_dilim"]
            self.dilim.setMaximum(max(n, 1))
            self.dilim.setValue(max(1, n // 2 + 1))
            uc_boyut = n > 1
            for w in (self.dilim, self.dilim_etiket):
                w.setVisible(uc_boyut)
            self.gorunum.model().item(1).setEnabled(uc_boyut)
            if not uc_boyut:
                self.gorunum.setCurrentIndex(0)
        self._tam_kor_denetimleri(bool(self.faktorler and self.faktorler.get("tam_kor")))
        self._tur_secicisini_doldur()
        self._ozet_yaz()
        self._ciz()

    def _tam_kor_denetimleri(self, tam_kor):
        """Olcek anahtari ve belirsizlik etiketi yalnizca tam korda gorunur;
        tek demet modelinde gorunum eskisiyle aynidir."""
        for w in (self.olcek, self.olcek_etiket, self.belirsizlik):
            w.setVisible(tam_kor)

    def _tur_secicisini_doldur(self):
        """Tur secici yalniz cok turlu sonucta (faktorler["tur_ozeti"]) gorunur."""
        ozet = (self.faktorler or {}).get("tur_ozeti") or {}
        eski = self.tur.blockSignals(True)
        try:
            self.tur.clear()
            self.tur.addItem(_("Tüm türler"), None)
            for ad, v in ozet.items():
                self.tur.addItem("%s (%d)" % (ad or "?", v["cubuk_sayisi"]), ad)
        finally:
            self.tur.blockSignals(eski)
        for w in (self.tur, self.tur_etiket):
            w.setVisible(bool(ozet))

    def _tur_suz(self, veri):
        """Secili ture ait anahtarlar ("a+b" sutunu iki turde de gorunur)."""
        secili = None if self.tur.isHidden() else self.tur.currentData()
        turler = (self.dagilim or {}).get("cubuk_turleri") or {}
        if not secili or not turler:
            return veri
        return {a: v for a, v in veri.items()
                if secili in (turler.get(a) or "").split("+")}

    def _bos(self, metin):
        self._ipucu_ogeleri, self._ipucu_dizi = [], None
        self.figur.clear()
        eks = self.figur.add_subplot(111)
        eks.set_axis_off()
        eks.text(0.5, 0.5, metin, ha="center", va="center",
                 fontsize=10, color=tema.renk("metin_soluk"))
        self.tuval.draw_idle()

    def _ozet_yaz(self):
        if not self.faktorler:
            self.ozet.setText(_("Güç dağılımı hesaplanmadı. Hesap ayarları sekmesinde "
                                "'Çubuk bazlı güç dağılımı hesapla' kutusunu işaretleyip "
                                "modeli yeniden çalıştırın."))
            return
        f = self.faktorler
        p = ["<b>F_&Delta;H = %.4f</b>" % f["F_dH"]]
        if f["F_q"]:
            p.append("<b>F_q = %.4f</b>" % f["F_q"])
        n_dilim = f["eksenel_dilim"]
        p.append(_n("%d çubuk, %d eksenel dilim", "%d çubuk, %d eksenel dilim", n_dilim)
                 % (f["cubuk_sayisi"], n_dilim))
        p.append(_("en sıcak çubuk: %s") % _guc.konum_metni(
            f["sicak_cubuk"], f.get("kafes_turu"), f.get("kafes_turleri")))
        if f.get("tam_kor"):
            p.append(_("en sıcak demet: %s (ortalama %.4f)")
                     % (_guc.demet_metni(f["sicak_demet"], f), f["F_demet"]))
        if f["sicak_dilim"]:
            p.append(_("en sıcak dilim: %d") % (f["sicak_dilim"][1] + 1))
        metin = " &nbsp;|&nbsp; ".join(p)
        if self.korunum is not None:
            iyi = self.korunum < 1e-6
            metin += (_("<br><span style='color:%s'>Toplamın korunumu: bağıl fark "
                        "%.1e — %s</span>")
                      % (tema.renk("basari") if iyi else tema.renk("hata"), self.korunum,
                         _("tamam") if iyi else _("bozuk, haritaya güvenmeyin")))
        for not_metni in getattr(self, "korunum_notlari", []):
            metin += "<br>" + html.escape(not_metni)
        satirlar = _guc.yorumla(f, self.mutlak, getattr(self, "hedef_payi", None),
                                hedef_payi_hata=getattr(self, "hedef_payi_hata", None),
                                kategori=getattr(self, "kategori", None))
        metin += "<br><br>" + "<br>".join("&bull; " + s.strip() for s in satirlar)
        self.ozet.setText(metin)

    # ==================================================================
    def _veri(self):
        """Secili goruntuye gore {konum: bagil_deger} dondurur."""
        f = self.faktorler
        if self.gorunum.currentData() == "dilim" and f["bagil_eksenel"]:
            i = self.dilim.value() - 1
            return self._tur_suz({a: v[i][0] for a, v in f["bagil_eksenel"].items()}), \
                _("dilim %d / %d") % (i + 1, f["eksenel_dilim"])
        return self._tur_suz({a: v[0] for a, v in f["bagil"].items()}), _("çubuk toplamı")

    def _ciz(self):
        if not self.faktorler or not self.dagilim:
            self._bos(_("Güç dağılımı hesaplanmadı"))
            return
        f = self.faktorler
        self.dilim_etiket.setText(_("Dilim %d") % self.dilim.value())
        veri, alt_baslik = self._veri()

        self.figur.clear()
        uc_boyut = f["eksenel_dilim"] > 1
        if uc_boyut:
            eks = self.figur.add_subplot(1, 2, 1)
            eks_p = self.figur.add_subplot(1, 2, 2)
        else:
            eks = self.figur.add_subplot(111)
            eks_p = None

        self._ipucu_ogeleri, self._ipucu_dizi = [], None
        if f.get("tam_kor"):
            self._ciz_kor(eks, veri, alt_baslik)
        else:
            if self.dagilim["kafes_turu"] == "altigen":
                self._ciz_altigen(eks, veri)
            else:
                self._ciz_kare(eks, veri)
            # Gosterge hucrelerin ustune biniyordu (Ajan 9): aciklama baslikta.
            eks.set_title(_("Bağıl güç — %s\n○ en sıcak çubuk · beyaz: yakıtsız konum "
                            "(kılavuz/ölçüm borusu)") % alt_baslik, fontsize=8)

        if eks_p is not None and f["eksenel_profil"]:
            y = [p[0] for p in f["eksenel_profil"]]
            x = list(range(1, len(y) + 1))
            eks_p.plot(y, x, "o-", ms=3, lw=1.2, color=tema.renk("metin"))
            eks_p.axvline(1.0, color=tema.renk("kenar_guclu"), ls="--", lw=0.8)
            if self.gorunum.currentData() == "dilim":
                eks_p.axhline(self.dilim.value(), color=tema.renk("hata"), ls="-", lw=1.2)
            eks_p.set_xlabel(_("bağıl güç"), fontsize=8)
            eks_p.set_ylabel(_("eksenel dilim"), fontsize=8)
            eks_p.tick_params(labelsize=7)
            eks_p.grid(alpha=0.3)
            eks_p.set_title(_("Eksenel profil"), fontsize=9)
        self.tuval.draw_idle()

    def _renk_cubugu(self, eslenebilir, eks):
        """Renk olcegi eksenin HEMEN yaninda. figur.colorbar(ax=eks) ebeveyn
        ekseni saga capaliyordu: genis pencerede harita sagda, solunda ~1000 px
        bosluk kaliyordu (Ajan 9 bulgusu)."""
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        cax = make_axes_locatable(eks).append_axes("right", size="4%", pad=0.08)
        self.figur.colorbar(eslenebilir, cax=cax, label=_("bağıl güç"))

    def _renk_olcegi(self, veri):
        d = list(veri.values())
        return (min(d), max(d)) if d else (0.0, 1.0)

    def _ciz_kare(self, eks, veri):
        import numpy as np
        # izgara olcusu BUTUN cubuklardan (tur suzgeci haritayi kucultmesin)
        tum = list(self.faktorler["bagil"]) or list(veri)
        xs = [a[0] for a in tum]; ys = [a[1] for a in tum]
        nx, ny = max(xs) + 1, max(ys) + 1
        izgara = np.full((ny, nx), np.nan)
        for (x, y), v in veri.items():
            izgara[y, x] = v
        alt, ust = self._renk_olcegi(veri)
        # Eksenler 1'den numarali (x soldan, y alttan): hucre (x, y) -> (x+1, y+1)
        im = eks.imshow(izgara, origin="lower", cmap="inferno",
                        vmin=alt, vmax=ust, interpolation="nearest",
                        extent=(0.5, nx + 0.5, 0.5, ny + 0.5))
        self._renk_cubugu(im, eks)
        sicak = self.faktorler["sicak_cubuk"]
        eks.plot(sicak[0] + 1, sicak[1] + 1, marker="o", ms=11, mfc="none",
                 mec=tema.renk("vurgu"), mew=2.0)
        eks.set_xlabel(_("x (soldan)"), fontsize=8)
        eks.set_ylabel(_("y (alttan)"), fontsize=8)
        eks.tick_params(labelsize=7)
        if self.degerler.isChecked() and nx * ny <= 400:
            for (x, y), v in veri.items():
                eks.text(x + 1, y + 1, "%.2f" % v, ha="center", va="center", fontsize=5,
                         color="white" if v < (alt + ust) / 2 else "black")

    def _ciz_altigen(self, eks, veri):
        kafes = self.dagilim["kafes"]
        halka = kafes.num_rings
        yonelim = getattr(kafes, "orientation", "y")
        konum = altigen.konumlar(halka, yonelim)
        alt, ust = self._renk_olcegi(veri)
        renk_es = matplotlib.cm.get_cmap("inferno") if hasattr(matplotlib.cm, "get_cmap") \
            else matplotlib.colormaps["inferno"]
        norm = matplotlib.colors.Normalize(vmin=alt, vmax=ust)
        # hucre koseleri: kafes yonelimine gore (cekirdek/altigen ile ayni kural)
        kose_aci = altigen.hucre_kose_acilari(yonelim)[0]
        yaricap = 1.0 / math.sqrt(3.0)
        for anahtar, v in veri.items():
            if anahtar not in konum:
                continue
            x, y = konum[anahtar]
            eks.add_patch(RegularPolygon(
                (x, y), numVertices=6, radius=yaricap,
                orientation=math.radians(kose_aci - 30.0),
                facecolor=renk_es(norm(v)), edgecolor=tema.renk("kenar"), linewidth=0.4))
            if self.degerler.isChecked() and len(veri) <= 200:
                eks.text(x, y, "%.2f" % v, ha="center", va="center", fontsize=5,
                         color="white" if v < (alt + ust) / 2 else "black")
        sicak = self.faktorler["sicak_cubuk"]
        if sicak in konum:
            sx, sy = konum[sicak]
            eks.plot(sx, sy, marker="o", ms=11, mfc="none", mec=tema.renk("vurgu"), mew=2.0)
        tum = list(konum.values())
        pay = yaricap * 1.5
        eks.set_xlim(min(p[0] for p in tum) - pay, max(p[0] for p in tum) + pay)
        eks.set_ylim(min(p[1] for p in tum) - pay, max(p[1] for p in tum) + pay)
        eks.set_aspect("equal")
        eks.set_xlabel(_("adım birimi"), fontsize=8)
        eks.tick_params(labelsize=7)
        self._renk_cubugu(matplotlib.cm.ScalarMappable(norm=norm, cmap="inferno"), eks)

    # ==================================================================
    # KOR OLCEGI (tam kor: kafes icinde kafes)
    # ==================================================================
    def _sigmalar(self):
        """Secili goruntuye gore {konum: bagil sapma}."""
        f = self.faktorler
        if self.gorunum.currentData() == "dilim" and f["bagil_eksenel"]:
            i = self.dilim.value() - 1
            return {a: v[i][1] for a, v in f["bagil_eksenel"].items()}
        return {a: v[1] for a, v in f["bagil"].items()}

    def _demet_yamasi(self, demet, uyeler, olcek=1.0, **stil):
        """Demetin sekli: kafes elemani ya da (kafessiz yerlesimde) uyelerin kutusu."""
        dag = self.dagilim
        bicim = _kor.demet_bicimi(dag, demet)
        if bicim is not None:
            return _kor.yama(bicim, _guc.demet_merkezi(dag, demet), olcek, **stil), bicim[1] / 2.0
        noktalar = [_guc.cubuk_merkezi(dag, a) for a in uyeler]
        c_bicim = _kor.cubuk_bicimi(dag, uyeler[0]) if uyeler else None
        pay = (c_bicim[1] / 2.0) if c_bicim else 0.5
        x0, y0, g, y = _kor.kutu(noktalar, pay)
        return _kor.kutu_yamasi(noktalar, pay, **stil), max(g, y) / 2.0

    def _demet_degerleri(self, veri, sigma):
        """{demet: (ortalama, sapma, [cubuk anahtarlari])} secili goruntu icin."""
        gruplar = {}
        for a, v in veri.items():
            gruplar.setdefault(_guc.demet_anahtari(a), []).append(a)
        sonuc = {}
        for d, uyeler in gruplar.items():
            n = len(uyeler)
            sonuc[d] = (sum(veri[a] for a in uyeler) / n,
                        math.sqrt(sum(sigma[a] ** 2 for a in uyeler)) / n, uyeler)
        return sonuc

    def _kesikler(self):
        """Kesik (kirpilan) cubuklar: F_dH disi, haritada ayri isaretli."""
        f = self.faktorler or {}
        return [a for a in f.get("kesik_cubuklar") or ()
                if a in ((self.dagilim or {}).get("konumlar") or {})]

    def _ciz_kor(self, eks, veri, alt_baslik):
        """Kor olceginde harita: 'demet' (demet ortalamasi) ya da 'cubuk'
        (her cubuk kordaki gercek konumunda); demet sinirlari kalin cizgi.
        Duzeyler kare, altigen, karisik ya da yerlesim olabilir (guc_harita_kor)."""
        from matplotlib.collections import PatchCollection
        dag = self.dagilim
        sigma = self._sigmalar()
        demetler = self._demet_degerleri(veri, sigma)
        demet_modu = self.olcek.currentData() == "demet"
        renk_es = matplotlib.colormaps["inferno"]

        if demet_modu:
            degerler = {d: v[0] for d, v in demetler.items()}
            yamalar, renkler = self._demet_yamalari(demetler)
        else:
            degerler = veri
            yamalar, renkler = self._cubuk_yamalari(veri, sigma)
        alt, ust = self._renk_olcegi(degerler)
        norm = matplotlib.colors.Normalize(vmin=alt, vmax=ust)
        koleksiyon = PatchCollection(yamalar, cmap=renk_es, norm=norm,
                                     edgecolor=tema.renk("kenar"),
                                     linewidths=0.6 if demet_modu else 0.15)
        koleksiyon.set_array(renkler)
        eks.add_collection(koleksiyon)
        self._demet_sinirlari(eks, demetler)
        if demet_modu and (self.degerler.isChecked() or len(demetler) <= 60):
            for d in demetler:
                x, y = _guc.demet_merkezi(dag, d)
                v = degerler[d]
                eks.text(x, y, "%.3f" % v, ha="center", va="center", fontsize=6,
                         color=tema.renk("vurgu_metin") if v < (alt + ust) / 2
                         else tema.renk("metin"))
        kesik = self._kesikleri_isaretle(eks, demet_modu)
        self._sicak_cubugu_isaretle(eks, demet_modu)
        self._kor_eksenleri(eks)
        self._renk_cubugu(koleksiyon, eks)
        ek = (_n(" · × kesik çubuk (%d, F_ΔH dışı)", " · × kesik çubuk (%d, F_ΔH dışı)", kesik)
              % kesik) if kesik else ""
        eks.set_title(_("Bağıl güç (kor ortalaması = 1) — %s · %s\n"
                        "○ en sıcak çubuk · kalın çerçeve: en sıcak demet")
                      % (_("demet ortalaması") if demet_modu else _("çubuk"), alt_baslik)
                      + ek, fontsize=8)

    def _demet_yamalari(self, demetler):
        yamalar, renkler = [], []
        for d, (ort, sap, uyeler) in demetler.items():
            merkez = _guc.demet_merkezi(self.dagilim, d)
            yama, yaricap = self._demet_yamasi(d, uyeler)
            yamalar.append(yama)
            renkler.append(ort)
            kayit = (self.faktorler.get("demetler") or {}).get(d) or {}
            tepe = kayit.get("tepe")
            metin = _n("demet %s\nortalama %.4f ± %.4f\n%d çubuk",
                       "demet %s\nortalama %.4f ± %.4f\n%d çubuk", len(uyeler)) % (
                _guc.demet_metni(d, self.faktorler), ort, sap, len(uyeler))
            if tepe and self.gorunum.currentData() != "dilim":
                metin += _("\ntepe %.4f ± %.4f (%s)") % (
                    tepe[0], tepe[1], _guc.konum_metni(kayit["tepe_cubuk"], None,
                                                      self.faktorler["kafes_turleri"]))
            self._ipucu_ogeleri.append((merkez[0], merkez[1], yaricap, metin))
        return yamalar, renkler

    def _cubuk_yamasi(self, anahtar, **stil):
        merkez = _guc.cubuk_merkezi(self.dagilim, anahtar)
        bicim = _kor.cubuk_bicimi(self.dagilim, anahtar) or ("kare", 1.0, None)
        return merkez, _kor.yama(bicim, merkez, **stil), bicim[1] / 2.0

    def _cubuk_yamalari(self, veri, sigma):
        dag = self.dagilim
        yamalar, renkler = [], []
        for a, v in veri.items():
            merkez, yama, yaricap = self._cubuk_yamasi(a)
            yamalar.append(yama)
            renkler.append(v)
            metin = "%s\n%.4f ± %.4f" % (
                _guc.konum_metni(a, None, dag["kafes_turleri"]), v, sigma[a])
            self._ipucu_ogeleri.append((merkez[0], merkez[1], yaricap, metin))
        return yamalar, renkler

    def _kesikleri_isaretle(self, eks, demet_modu):
        """Kesik cubuklar: cubuk gorunumunde taranmis gri yama, iki gorunumde × isareti."""
        kesik = self._kesikler()
        for a in kesik:
            merkez, yama, yaricap = self._cubuk_yamasi(
                a, facecolor=tema.renk("yuzey3"), edgecolor=tema.renk("kenar"),
                hatch="xx", linewidth=0.15, zorder=2)
            if not demet_modu:
                eks.add_patch(yama)
            eks.plot(merkez[0], merkez[1], marker="x", ms=4, color=tema.renk("metin_soluk"),
                     zorder=4)
            self._ipucu_ogeleri.append((merkez[0], merkez[1], yaricap, _(
                "%s\nkesik çubuk — üst hücre sınırıyla kırpılıyor; F_ΔH ve F_q dışında")
                % _guc.konum_metni(a, None, self.dagilim["kafes_turleri"])))
        return len(kesik)

    def _demet_sinirlari(self, eks, demetler):
        """Demet sinirlari kalin cizgi; en sicak demet vurgu renginde."""
        sicak = self.faktorler.get("sicak_demet")
        for d, (_o, _s, uyeler) in demetler.items():
            eks.add_patch(self._demet_yamasi(
                d, uyeler, fill=False, edgecolor=tema.renk("metin"), linewidth=1.6,
                zorder=3)[0])
        if sicak in demetler:
            eks.add_patch(self._demet_yamasi(
                sicak, demetler[sicak][2], 0.97, fill=False, edgecolor=tema.renk("vurgu"),
                linewidth=3.0, zorder=4)[0])

    def _sicak_cubugu_isaretle(self, eks, demet_modu):
        """En sicak cubuk halka isaretiyle (her iki gorunumde)."""
        sicak = self.faktorler["sicak_cubuk"]
        x, y = _guc.cubuk_merkezi(self.dagilim, sicak)
        eks.plot(x, y, marker="o", ms=11 if not demet_modu else 8, mfc="none",
                 mec=tema.renk("vurgu"), mew=2.0, zorder=5)

    def _kor_eksenleri(self, eks):
        """Sinirlar cizilen ogelerden (ipucu ogeleri: merkez + yaricap)."""
        ogeler = self._ipucu_ogeleri or [(0.0, 0.0, 1.0, "")]
        pay = max(o[2] for o in ogeler) * 0.5
        eks.set_xlim(min(o[0] - o[2] for o in ogeler) - pay, max(o[0] + o[2] for o in ogeler) + pay)
        eks.set_ylim(min(o[1] - o[2] for o in ogeler) - pay, max(o[1] + o[2] for o in ogeler) + pay)
        eks.set_aspect("equal")
        eks.set_xlabel("x [cm]", fontsize=8)
        eks.set_ylabel("y [cm]", fontsize=8)
        eks.tick_params(labelsize=7)

    def ipucu_metni(self, x, y):
        """(x, y) [cm] noktasindaki ogenin ipucu metni; yoksa None.
        Tam PWR korunda ~50 bin cubuk olur: arama numpy ile yapilir."""
        import numpy as np
        if not self._ipucu_ogeleri:
            return None
        dizi = getattr(self, "_ipucu_dizi", None)
        if dizi is None or len(dizi) != len(self._ipucu_ogeleri):
            dizi = np.asarray([o[:3] for o in self._ipucu_ogeleri], dtype=float)
            self._ipucu_dizi = dizi
        uzak = np.hypot(dizi[:, 0] - x, dizi[:, 1] - y)
        i = int(np.argmin(uzak))
        return self._ipucu_ogeleri[i][3] if uzak[i] <= dizi[i, 2] * 1.05 else None

    def _fare_hareketi(self, olay):
        if not self._ipucu_ogeleri or olay.inaxes is None or olay.xdata is None:
            return
        metin = self.ipucu_metni(olay.xdata, olay.ydata)
        if metin:
            from PySide6 import QtGui
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), metin, self.tuval)
        else:
            QtWidgets.QToolTip.hideText()

    def _kaydet(self):
        yol, _secilen = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Güç haritasını kaydet"), "guc_haritasi.png", "PNG (*.png)")
        if yol:
            self.figur.savefig(yol, dpi=150, bbox_inches="tight")
