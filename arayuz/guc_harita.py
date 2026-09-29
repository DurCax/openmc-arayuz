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
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import tema

_log = kaydedici(__name__)


def _aktif_yukseklik(spec):
    """Lineer guc paydasi: hedef cubugun bulundugu katmanlarin yuksekligi
    (kurucu.guc_yuksekligi; yansitici, plenum ve blanket haric)."""
    try:
        from cekirdek import kurucu
        return kurucu.guc_yuksekligi(spec)
    except Exception:
        _log.warning("aktif eksenel aralık okunamadı; kor yüksekliği kullanılıyor",
                     exc_info=True)
        return sema.kor_yuksekligi(spec.get("kor") or {})


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
        self.gorunum.addItem("Çubuk toplam gücü (F_ΔH)", "toplam")
        self.gorunum.addItem("Tek eksenel dilim (F_q)", "dilim")
        self.dilim = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.dilim.setMinimum(1); self.dilim.setMaximum(1); self.dilim.setValue(1)
        self.dilim_etiket = QtWidgets.QLabel("Dilim 1")
        self.degerler = QtWidgets.QCheckBox("Değerleri haritaya yaz")
        self.d_kaydet = QtWidgets.QPushButton("PNG kaydet…")
        # Tam kor: kor olceginde demet ortalamasi / cubuk haritasi
        self.olcek = QtWidgets.QComboBox()
        self.olcek.addItem(_("Demet"), "demet")
        self.olcek.addItem(_("Çubuk"), "cubuk")
        self.olcek.setToolTip(_("Tam kor: demet ortalamaları ya da kordaki bütün "
                                "çubuklar"))
        self.olcek_etiket = QtWidgets.QLabel(_("Ölçek:"))
        self._ipucu_ogeleri = []      # [(x, y, yaricap, metin)] fare ipucu icin

        self.gorunum.currentIndexChanged.connect(self._ciz)
        self.dilim.valueChanged.connect(self._ciz)
        self.degerler.toggled.connect(self._ciz)
        self.d_kaydet.clicked.connect(self._kaydet)
        self.olcek.currentIndexChanged.connect(self._ciz)

        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.olcek_etiket)
        ust.addWidget(self.olcek)
        ust.addWidget(QtWidgets.QLabel("Görünüm:"))
        ust.addWidget(self.gorunum)
        ust.addWidget(self.dilim_etiket)
        ust.addWidget(self.dilim, 1)
        ust.addWidget(self.d_kaydet)

        # --- ozet ---
        self.ozet = QtWidgets.QLabel("Güç dağılımı henüz hesaplanmadı.")
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
        duzen.addWidget(baslik("Çubuk güç dağılımı"))
        aciklama = QtWidgets.QLabel(
            "F_ΔH = en yüksek çubuk gücü / ortalama (radyal). "
            "F_q = en yüksek yerel güç yoğunluğu / ortalama (radyal × eksenel, 3B gerekir). "
            "Renk ölçeği ortalamaya göre bağıldır: 1.00 = ortalama çubuk.")
        aciklama.setObjectName("soluk")
        aciklama.setWordWrap(True)
        duzen.addWidget(aciklama)
        duzen.addLayout(ust)
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(self.belirsizlik)
        duzen.addWidget(self.gelismis)
        self._tam_kor_denetimleri(False)
        self._bos("Henüz koşu yapılmadı")

    # ==================================================================
    def sonuc_ayarla(self, sonuc, spec=None):
        """kosucu.sonuc_oku() ciktisindan guc bolumunu alir."""
        g = (sonuc or {}).get("guc") or {}
        self.dagilim = g.get("dagilim")
        self.faktorler = g.get("faktorler")
        self.korunum = g.get("korunum")
        self.korunum_notlari = [g[a] for a in ("korunum_hata", "korunum_notu") if g.get(a)]
        self.hedef_payi = g.get("hedef_payi")
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
        self._ozet_yaz()
        self._ciz()

    def _tam_kor_denetimleri(self, tam_kor):
        """Olcek anahtari ve belirsizlik etiketi yalnizca tam korda gorunur;
        tek demet modelinde gorunum eskisiyle aynidir."""
        for w in (self.olcek, self.olcek_etiket, self.belirsizlik):
            w.setVisible(tam_kor)

    def _bos(self, metin):
        self._ipucu_ogeleri, self._ipucu_dizi = [], None
        self.figur.clear()
        eks = self.figur.add_subplot(111)
        eks.set_axis_off()
        eks.text(0.5, 0.5, metin, ha="center", va="center",
                 fontsize=10, color="#7f8c8d")
        self.tuval.draw_idle()

    def _ozet_yaz(self):
        if not self.faktorler:
            self.ozet.setText("Güç dağılımı hesaplanmadı. Hesap ayarları sekmesinde "
                              "'Çubuk bazlı güç dağılımı hesapla' kutusunu işaretleyip "
                              "modeli yeniden çalıştırın.")
            return
        f = self.faktorler
        p = ["<b>F_&Delta;H = %.4f</b>" % f["F_dH"]]
        if f["F_q"]:
            p.append("<b>F_q = %.4f</b>" % f["F_q"])
        p.append("%d çubuk, %d eksenel dilim" % (f["cubuk_sayisi"], f["eksenel_dilim"]))
        p.append("en sıcak çubuk: %s" % _guc.konum_metni(f["sicak_cubuk"], f.get("kafes_turu"),
                                                        f.get("kafes_turleri")))
        if f.get("tam_kor"):
            p.append(_("en sıcak demet: %s (ortalama %.4f)")
                     % (_guc.demet_metni(f["sicak_demet"], f), f["F_demet"]))
        if f["sicak_dilim"]:
            p.append("en sıcak dilim: %d" % (f["sicak_dilim"][1] + 1))
        metin = " &nbsp;|&nbsp; ".join(p)
        if self.korunum is not None:
            iyi = self.korunum < 1e-6
            metin += ("<br><span style='color:%s'>Toplamın korunumu: bağıl fark "
                      "%.1e — %s</span>"
                      % ("#1e6b3a" if iyi else "#8b1a1a", self.korunum,
                         "tamam" if iyi else "bozuk, haritaya güvenmeyin"))
        for not_metni in getattr(self, "korunum_notlari", []):
            metin += "<br>" + html.escape(_("Toplamın korunumu denetlenemedi: %s") % not_metni)
        satirlar = _guc.yorumla(f, self.mutlak, getattr(self, "hedef_payi", None))
        metin += "<br><br>" + "<br>".join("&bull; " + s.strip() for s in satirlar)
        self.ozet.setText(metin)

    # ==================================================================
    def _veri(self):
        """Secili goruntuye gore {konum: bagil_deger} dondurur."""
        f = self.faktorler
        if self.gorunum.currentData() == "dilim" and f["bagil_eksenel"]:
            i = self.dilim.value() - 1
            return {a: v[i][0] for a, v in f["bagil_eksenel"].items()}, \
                   "dilim %d / %d" % (i + 1, f["eksenel_dilim"])
        return {a: v[0] for a, v in f["bagil"].items()}, "çubuk toplamı"

    def _ciz(self):
        if not self.faktorler or not self.dagilim:
            self._bos("Güç dağılımı hesaplanmadı")
            return
        f = self.faktorler
        self.dilim_etiket.setText("Dilim %d" % self.dilim.value())
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
            eks.set_title("Bağıl güç — %s\n○ en sıcak çubuk · beyaz: yakıtsız konum "
                          "(kılavuz/ölçüm borusu)" % alt_baslik, fontsize=8)

        if eks_p is not None and f["eksenel_profil"]:
            y = [p[0] for p in f["eksenel_profil"]]
            x = list(range(1, len(y) + 1))
            eks_p.plot(y, x, "o-", ms=3, lw=1.2, color="#2c3e50")
            eks_p.axvline(1.0, color="#95a5a6", ls="--", lw=0.8)
            if self.gorunum.currentData() == "dilim":
                eks_p.axhline(self.dilim.value(), color="#c0392b", ls="-", lw=1.2)
            eks_p.set_xlabel("bağıl güç", fontsize=8)
            eks_p.set_ylabel("eksenel dilim", fontsize=8)
            eks_p.tick_params(labelsize=7)
            eks_p.grid(alpha=0.3)
            eks_p.set_title("Eksenel profil", fontsize=9)
        self.tuval.draw_idle()

    def _renk_cubugu(self, eslenebilir, eks):
        """Renk olcegi eksenin HEMEN yaninda. figur.colorbar(ax=eks) ebeveyn
        ekseni saga capaliyordu: genis pencerede harita sagda, solunda ~1000 px
        bosluk kaliyordu (Ajan 9 bulgusu)."""
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        cax = make_axes_locatable(eks).append_axes("right", size="4%", pad=0.08)
        self.figur.colorbar(eslenebilir, cax=cax, label="bağıl güç")

    def _renk_olcegi(self, veri):
        d = list(veri.values())
        return (min(d), max(d)) if d else (0.0, 1.0)

    def _ciz_kare(self, eks, veri):
        import numpy as np
        xs = [a[0] for a in veri]; ys = [a[1] for a in veri]
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
                 mec="#00e5ff", mew=2.0)
        eks.set_xlabel("x (soldan)", fontsize=8); eks.set_ylabel("y (alttan)", fontsize=8)
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
                facecolor=renk_es(norm(v)), edgecolor="#444444", linewidth=0.4))
            if self.degerler.isChecked() and len(veri) <= 200:
                eks.text(x, y, "%.2f" % v, ha="center", va="center", fontsize=5,
                         color="white" if v < (alt + ust) / 2 else "black")
        sicak = self.faktorler["sicak_cubuk"]
        if sicak in konum:
            sx, sy = konum[sicak]
            eks.plot(sx, sy, marker="o", ms=11, mfc="none", mec="#00e5ff", mew=2.0)
        tum = list(konum.values())
        pay = yaricap * 1.5
        eks.set_xlim(min(p[0] for p in tum) - pay, max(p[0] for p in tum) + pay)
        eks.set_ylim(min(p[1] for p in tum) - pay, max(p[1] for p in tum) + pay)
        eks.set_aspect("equal")
        eks.set_xlabel("adım birimi", fontsize=8)
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

    @staticmethod
    def _eleman_yamasi(tur, merkez, adim, yonelim, **stil):
        """Kafes elemaninin sekli: kare (adim x adim) ya da altigen."""
        from matplotlib.patches import Rectangle
        if tur == "altigen":
            kose = altigen.hucre_kose_acilari(yonelim)[0]
            return RegularPolygon(merkez, numVertices=6, radius=adim / math.sqrt(3.0),
                                  orientation=math.radians(kose - 30.0), **stil)
        return Rectangle((merkez[0] - adim / 2.0, merkez[1] - adim / 2.0),
                         adim, adim, **stil)

    @staticmethod
    def _kafes_bilgisi(kafes, tur):
        """(adim, yonelim) -- cizim icin."""
        if tur == "altigen":
            return kafes.pitch[0], getattr(kafes, "orientation", "y")
        return kafes.pitch[0], None

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

    def _ciz_kor(self, eks, veri, alt_baslik):
        """Kor olceginde harita: 'demet' (demet ortalamasi) ya da 'cubuk'
        (her cubuk kordaki gercek konumunda); demet sinirlari kalin cizgi."""
        from matplotlib.collections import PatchCollection
        f, dag = self.faktorler, self.dagilim
        sigma = self._sigmalar()
        demetler = self._demet_degerleri(veri, sigma)
        kor_tur = dag["kafes_turleri"][0]
        d_adim, d_yon = self._kafes_bilgisi(dag["kafesler"][0], kor_tur)
        demet_modu = self.olcek.currentData() == "demet"
        renk_es = matplotlib.colormaps["inferno"]

        if demet_modu:
            degerler = {d: v[0] for d, v in demetler.items()}
            yamalar, renkler = self._demet_yamalari(demetler, d_adim, kor_tur, d_yon)
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
        self._demet_sinirlari(eks, demetler, d_adim, kor_tur, d_yon)
        if demet_modu and (self.degerler.isChecked() or len(demetler) <= 60):
            for d in demetler:
                x, y = _guc.demet_merkezi(dag, d)
                v = degerler[d]
                eks.text(x, y, "%.3f" % v, ha="center", va="center", fontsize=6,
                         color=tema.renk("vurgu_metin") if v < (alt + ust) / 2
                         else tema.renk("metin"))
        self._sicak_cubugu_isaretle(eks, demet_modu)
        self._kor_eksenleri(eks, demetler, d_adim)
        self._renk_cubugu(koleksiyon, eks)
        eks.set_title(_("Bağıl güç (kor ortalaması = 1) — %s · %s\n"
                        "○ en sıcak çubuk · kalın çerçeve: en sıcak demet")
                      % (_("demet ortalaması") if demet_modu else _("çubuk"), alt_baslik),
                      fontsize=8)

    def _demet_yamalari(self, demetler, adim, tur, yonelim):
        yamalar, renkler = [], []
        for d, (ort, sap, uyeler) in demetler.items():
            merkez = _guc.demet_merkezi(self.dagilim, d)
            yamalar.append(self._eleman_yamasi(tur, merkez, adim, yonelim))
            renkler.append(ort)
            kayit = (self.faktorler.get("demetler") or {}).get(d) or {}
            tepe = kayit.get("tepe")
            metin = _("demet %s\nortalama %.4f ± %.4f\n%d çubuk") % (
                _guc.demet_metni(d, self.faktorler), ort, sap, len(uyeler))
            if tepe and self.gorunum.currentData() != "dilim":
                metin += _("\ntepe %.4f ± %.4f (%s)") % (
                    tepe[0], tepe[1], _guc.konum_metni(kayit["tepe_cubuk"], None,
                                                      self.faktorler["kafes_turleri"]))
            self._ipucu_ogeleri.append((merkez[0], merkez[1], adim / 2.0, metin))
        return yamalar, renkler

    def _cubuk_yamalari(self, veri, sigma):
        dag = self.dagilim
        ic_tur = dag["kafes_turleri"][-1]
        c_adim, c_yon = self._kafes_bilgisi(dag["kafesler"][-1], ic_tur)
        yamalar, renkler = [], []
        for a, v in veri.items():
            merkez = _guc.cubuk_merkezi(dag, a)
            yamalar.append(self._eleman_yamasi(ic_tur, merkez, c_adim, c_yon))
            renkler.append(v)
            metin = "%s\n%.4f ± %.4f" % (
                _guc.konum_metni(a, None, dag["kafes_turleri"]), v, sigma[a])
            self._ipucu_ogeleri.append((merkez[0], merkez[1], c_adim / 2.0, metin))
        return yamalar, renkler

    def _demet_sinirlari(self, eks, demetler, adim, tur, yonelim):
        """Demet sinirlari kalin cizgi; en sicak demet vurgu renginde."""
        sicak = self.faktorler.get("sicak_demet")
        for d in demetler:
            merkez = _guc.demet_merkezi(self.dagilim, d)
            eks.add_patch(self._eleman_yamasi(
                tur, merkez, adim, yonelim, fill=False,
                edgecolor=tema.renk("metin"), linewidth=1.6, zorder=3))
        if sicak in demetler:
            eks.add_patch(self._eleman_yamasi(
                tur, _guc.demet_merkezi(self.dagilim, sicak), adim * 0.97, yonelim,
                fill=False, edgecolor=tema.renk("vurgu"), linewidth=3.0, zorder=4))

    def _sicak_cubugu_isaretle(self, eks, demet_modu):
        """En sicak cubuk halka isaretiyle (her iki gorunumde)."""
        sicak = self.faktorler["sicak_cubuk"]
        x, y = _guc.cubuk_merkezi(self.dagilim, sicak)
        eks.plot(x, y, marker="o", ms=11 if not demet_modu else 8, mfc="none",
                 mec=tema.renk("vurgu"), mew=2.0, zorder=5)

    def _kor_eksenleri(self, eks, demetler, d_adim):
        merkezler = [_guc.demet_merkezi(self.dagilim, d) for d in demetler]
        pay = d_adim * 0.75
        eks.set_xlim(min(m[0] for m in merkezler) - pay, max(m[0] for m in merkezler) + pay)
        eks.set_ylim(min(m[1] for m in merkezler) - pay, max(m[1] for m in merkezler) + pay)
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
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Güç haritasını kaydet", "guc_haritasi.png", "PNG (*.png)")
        if yol:
            self.figur.savefig(yol, dpi=150, bbox_inches="tight")
