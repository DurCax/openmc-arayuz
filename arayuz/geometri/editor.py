# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/editor.py  --  Gelismis geometri editoru (agac + kesit + form)
================================================================================
 §10 eskizi:
   ust  : arac cubugu -- + Dugum ▼, + Halka, + Yerlesim, + Katman, + Grup,
          Parcaya cikar, Sarmala, Yeniden adlandir, Sil, ▲, ▼
   sol  : dugum agaci (agac_paneli.py; surukle-birak, sag tik = ayni eylemler)
   orta : sematik xy / xz kesit (kesit_gorunumu.py; tiklama agacta secer)
   sag  : secili ogenin formu (formlar*.py; sayi + birim kutulari)
   alt  : kesik / gizli konum ozeti + [Git]
 SINYALLER (Geometri sayfasi dinler)
   agac_islemi(yeni_agac, aciklama, secim)  -- yapisal islem: TEK geri al adimi
   agac_duzenlendi(yeni_agac)               -- form alani: gecmis 700 ms bosta yigar
   dugum_secildi(yol)                       -- onizleme vurgusu icin
 Editor spec'i DEGISTIRMEZ; yeni agaci yayar, sayfa spec'e yazar.
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz.geometri import duzenle
from arayuz.geometri.agac_paneli import AgacPaneli
from arayuz.geometri.form_kafes import EksenelFormu, KafesFormu, KatmanFormu, ParcaFormu
from arayuz.geometri.form_yerlesim import GrupFormu, YerlesimFormu
from arayuz.geometri.formlar import TUR_ADLARI, HalkaFormu, IcerikFormu, KapFormu
from arayuz.geometri.kesit_gorunumu import KesitGorunumu
from arayuz.tasarim import tokenlar

_log = kaydedici("arayuz.geometri.editor")
A = tokenlar.ARALIK
_CIZIM_GECIKMESI = 150            # ms: form yazarken kesit en cok bu siklikta cizilir
_AGAC_EN_AZ = 11 * A["l"]
_FORM_EN_AZ = 15 * A["l"]


class GelismisEditor(QtWidgets.QWidget):
    agac_islemi = QtCore.Signal(object, str, object)
    agac_duzenlendi = QtCore.Signal(object)
    dugum_secildi = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec, self.agac = None, {}
        self._secili = duzenle.KOK
        self.agac_paneli = AgacPaneli()
        self.kesit = KesitGorunumu()
        self._formlari_kur()
        self._eylemleri_kur()
        self._yerlesimi_kur()
        self._cizim_sayaci = QtCore.QTimer(self)
        self._cizim_sayaci.setSingleShot(True)
        self._cizim_sayaci.setInterval(_CIZIM_GECIKMESI)
        self._cizim_sayaci.timeout.connect(self.kesit.tazele)
        self.agac_paneli.secildi.connect(self._secildi)
        self.agac_paneli.tasima_istendi.connect(self._tasi)
        self.agac_paneli.baglam_menusu_istendi.connect(self._baglam_menusu)
        self.kesit.yol_secildi.connect(self._kesitten_secildi)

    # ------------------------------------------------------------------ kurulum
    def _formlari_kur(self):
        self.icerik_formu = IcerikFormu()
        self.formlar = {"kap": KapFormu(), "kafes": KafesFormu(), "eksenel": EksenelFormu(),
                        "halka": HalkaFormu(), "yerlesim": YerlesimFormu(),
                        "katman": KatmanFormu(), "parca": ParcaFormu(), "grup": GrupFormu()}
        for f in [self.icerik_formu] + list(self.formlar.values()):
            f.agac_degisti.connect(self._form_degisti)
        self.form_basligi = QtWidgets.QLabel("-")
        self.form_basligi.setObjectName("kartBaslik")
        self.form_yolu = QtWidgets.QLabel("")
        self.form_yolu.setObjectName("soluk")
        self.bos_etiketi = QtWidgets.QLabel(
            _("Parçalar: birden çok yerde kullanılan adlandırılmış alt ağaçlar.\n"
              "Gruplar: birden çok yerleşimi (dönme) ya da kontrol çubuğunu (daldırma) "
              "tek değerle sürer. “+ Grup” ile ekleyin."))
        self.bos_etiketi.setWordWrap(True)
        self.bos_etiketi.setObjectName("soluk")

    def _eylem(self, ikon, metin, islev, ipucu=None):
        # Simge dugmesi: adi (kilavuzdaki "+ Yerlesim" vb.) ipucunun basinda ve
        # erisilebilir adda gorunur (QA14-Q6)
        d = b.ikon_dugmesi(ikon, "%s — %s" % (metin, ipucu) if ipucu else metin)
        d.setAccessibleName(metin)
        d.clicked.connect(islev)
        return d

    def _eylemleri_kur(self):
        self.d_dugum = QtWidgets.QToolButton()
        self.d_dugum.setText(_("+ Düğüm"))
        self.d_dugum.setAccessibleName(_("+ Düğüm"))
        self.d_dugum.setToolTip(_("Seçili yuvaya yeni düğüm koyar (eskisi Geri Al ile döner)."))
        self.d_dugum.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(self.d_dugum)
        for tur, ad in TUR_ADLARI.items():
            menu.addAction(_(ad), lambda t=tur: self.dugum_ekle(t))
        self.d_dugum.setMenu(menu)
        self.dugmeler = {
            "halka": self._eylem("circle-dot", _("+ Halka"), self.halka_ekle,
                                 _("Seçili kaba dış halka ekler")),
            "yerlesim": self._eylem("target", _("+ Yerleşim"), self.yerlesim_ekle,
                                    _("Seçili bölgeye (kap içi ya da halka) delik + içerik "
                                      "yerleştirir: tambur, kanal, alt kafes")),
            "katman": self._eylem("layers", _("+ Katman"), self.katman_ekle,
                                  _("Seçili eksenel yığına katman ekler")),
            "grup": self._eylem("sliders-horizontal", _("+ Grup"), self.grup_ekle,
                                _("Dönme ya da daldırma grubu ekler")),
            "parca": self._eylem("box", _("Parçaya çıkar"), self.parcaya_cikar,
                                 _("Seçili alt ağacı adlandırılmış parçaya çevirir")),
            "sarmala": self._eylem("square", _("Sarmala"), self.sarmala,
                                   _("Seçiliyi yeni bir kabın içine alır")),
            "ad": self._eylem("file-text", _("Yeniden adlandır"), self.yeniden_adlandir),
            "sil": self._eylem("trash", _("Sil"), self.sil),
            "yukari": self._eylem("chevron-up", _("Yukarı taşı"), lambda: self.sira(-1)),
            "asagi": self._eylem("chevron-down", _("Aşağı taşı"), lambda: self.sira(+1)),
        }

    def _yerlesimi_kur(self):
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        cubuk = QtWidgets.QWidget()
        c = QtWidgets.QHBoxLayout(cubuk)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(A["xs"])
        c.addWidget(self.d_dugum)
        for k in ("halka", "yerlesim", "katman", "grup", "parca", "sarmala", "ad", "sil",
                  "yukari", "asagi"):
            c.addWidget(self.dugmeler[k])
        c.addStretch(1)
        d.addWidget(cubuk)
        self.bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.bolucu.setChildrenCollapsible(False)
        self.agac_paneli.setMinimumWidth(_AGAC_EN_AZ)
        self.bolucu.addWidget(self.agac_paneli)
        self.bolucu.addWidget(self.kesit)
        self.bolucu.addWidget(self._form_paneli())
        self.bolucu.setStretchFactor(0, 3)
        self.bolucu.setStretchFactor(1, 4)
        self.bolucu.setStretchFactor(2, 3)
        d.addWidget(self.bolucu, 1)
        d.addWidget(self._alt_serit())

    def _form_paneli(self):
        alan = QtWidgets.QScrollArea()
        alan.setWidgetResizable(True)
        alan.setFrameShape(QtWidgets.QFrame.NoFrame)
        alan.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        alan.setMinimumWidth(_FORM_EN_AZ)
        ic = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(ic)
        v.setContentsMargins(A["s"], 0, A["s"], 0)
        v.setSpacing(A["s"])
        v.addWidget(self.form_basligi)
        v.addWidget(self.form_yolu)
        v.addWidget(self.icerik_formu)
        for f in self.formlar.values():
            v.addWidget(f)
        v.addWidget(self.bos_etiketi)
        v.addStretch(1)
        alan.setWidget(ic)
        self.form_alani = alan
        return alan

    def _alt_serit(self):
        serit = QtWidgets.QWidget()
        s = QtWidgets.QHBoxLayout(serit)
        s.setContentsMargins(0, 0, 0, 0)
        self.kesik_etiketi = QtWidgets.QLabel("")
        self.kesik_etiketi.setWordWrap(True)
        self.d_git = b.duz_dugme(_("Git"), "chevron-right",
                                 _("Kesik konumu olan ilk kafesi seçer"))
        self.d_git.clicked.connect(self.kesige_git)
        s.addWidget(self.kesik_etiketi, 1)
        s.addWidget(self.d_git)
        return serit

    # ------------------------------------------------------------------ veri
    def yukle(self, spec):
        """Spec'in agacini gosterir (secim korunur)."""
        self.spec = spec
        self.agac = spec.get("geometri") or {}
        self.agac_paneli.yukle(self.agac, self._secili)
        self._secili = self.agac_paneli.secili_yol() or duzenle.KOK
        self.kesit.spec_ayarla(spec)
        self.kesit.secimi_ayarla(self._secili)
        self._formu_goster()
        self._kesik_ozeti()

    def agaci_tazele(self, spec):
        """Form bir alan yazdi: agac etiketleri ve kesit tazelenir, form kalir."""
        self.spec = spec
        self.agac = spec.get("geometri") or {}
        self.agac_paneli.yukle(self.agac, self._secili)
        self.kesit.spec = spec
        self._cizim_sayaci.start()
        for f in [self.icerik_formu] + list(self.formlar.values()):
            f.agaci_tazele(self.agac)
        self._kesik_ozeti()
        self._eylem_durumu()

    def secili_yol(self):
        return self._secili

    def sec(self, yol):
        """Disaridan (onizleme tiklamasi) secim."""
        secilen = self.agac_paneli.sec(yol, sinyal=False)
        if secilen is not None:
            self._secildi(secilen)

    # ------------------------------------------------------------------ secim
    def _secildi(self, yol):
        self._secili = tuple(yol)
        self.kesit.secimi_ayarla(self._secili)
        self._formu_goster()
        self.dugum_secildi.emit(self._secili)

    def _kesitten_secildi(self, yol):
        secilen = self.agac_paneli.sec(yol, sinyal=False)
        if secilen is not None:
            self._secildi(secilen)

    def _form_anahtari(self):
        tur = duzenle.oge_turu(self.agac, self._secili)
        if tur == "dugum":
            d = duzenle.al(self.agac, self._secili)
            return (d or {}).get("tur") if isinstance(d, dict) else "malzeme"
        return tur

    def _formu_goster(self):
        anahtar = self._form_anahtari()
        dugum = duzenle.oge_turu(self.agac, self._secili) == "dugum"
        kok = self._secili == duzenle.KOK
        self.icerik_formu.setVisible(dugum and not kok)
        if dugum and not kok:
            self.icerik_formu.yukle(self.spec, self.agac, self._secili)
        for ad, f in self.formlar.items():
            gorunur = ad == anahtar
            f.setVisible(gorunur)
            if gorunur:
                f.yukle(self.spec, self.agac, self._secili)
        self.bos_etiketi.setVisible(anahtar in ("parcalar", "gruplar", None))
        oge = self.agac_paneli.oge(self._secili)
        self.form_basligi.setText(oge.text(0) if oge is not None else "-")
        self.form_yolu.setText(duzenle.yol_metni(self._secili))
        self._eylem_durumu()

    def _eylem_durumu(self):
        a, y = self.agac, self._secili
        tur = duzenle.oge_turu(a, y)
        d = duzenle.al(a, y)
        dugum = tur == "dugum"
        kap = dugum and isinstance(d, dict) and d.get("tur") == "kap"
        eksenel = dugum and isinstance(d, dict) and d.get("tur") == "eksenel"
        kopya = dugum and isinstance(d, dict) and d.get("tur") not in ("malzeme", "bilesen")
        durum = {"halka": kap, "yerlesim": kap or tur == "halka", "katman": eksenel,
                 "grup": True, "parca": kopya and y != duzenle.KOK,
                 "sarmala": dugum and isinstance(d, dict),
                 "ad": tur in ("halka", "yerlesim", "katman", "parca", "grup") and tur != "halka"
                 or (dugum and isinstance(d, dict) and d.get("tur") in ("kap", "kafes", "eksenel")),
                 "sil": y != duzenle.KOK and tur not in (None, "parcalar", "gruplar"),
                 "yukari": tur in ("halka", "yerlesim", "katman", "parca", "grup"),
                 "asagi": tur in ("halka", "yerlesim", "katman", "parca", "grup")}
        for k, v in durum.items():
            self.dugmeler[k].setEnabled(bool(v))
        self.d_dugum.setEnabled(dugum)

    # ------------------------------------------------------------------ islemler
    def _uygula(self, islev, aciklama, secim=None):
        """Saf islemi uygular; hata kullaniciya bildirim olarak gosterilir."""
        try:
            yeni = islev()
        except duzenle.DuzenlemeHatasi as e:
            self._hata(str(e))
            return False
        self.agac_islemi.emit(yeni, aciklama, tuple(secim) if secim else self._secili)
        return True

    def _hata(self, metin):
        _log.info("agac islemi reddedildi: %s", metin)
        pencere = self.window()
        if pencere is not None and pencere is not self:
            b.bildir(pencere, metin, "hata")
        self.son_hata = metin

    def _form_degisti(self, yeni):
        self.agac = yeni
        self.agac_duzenlendi.emit(yeni)

    def _varsayilan_malzeme(self):
        malz = [m["ad"] for m in (self.spec or {}).get("malzemeler") or []]
        return malz[0] if malz else duzenle.BOSLUK

    def _bilesen_adi(self):
        for bolum in ("demetler", "cubuklar", "tamburlar", "plakalar"):
            for t in (self.spec or {}).get(bolum) or []:
                return t["ad"]
        return None

    def dugum_ekle(self, tur):
        y = self._secili
        self._uygula(lambda: duzenle.dugum_koy(self.agac, y, duzenle.yeni_dugum(
            tur, self.agac, self._varsayilan_malzeme(), self._bilesen_adi())),
            _("Düğüm kondu: {tur}").format(tur=_(TUR_ADLARI[tur])), y)

    def halka_ekle(self):
        y = self._secili
        n = len((duzenle.al(self.agac, y) or {}).get("halkalar") or [])
        self._uygula(lambda: duzenle.halka_ekle(self.agac, y, 10.0,
                                                duzenle.malzeme(self._varsayilan_malzeme())),
                     _("Halka eklendi"), y + ("halkalar", n))

    def yerlesim_ekle(self):
        y = self._secili
        try:
            liste = duzenle.bolge_yerlesim_listesi(self.agac, y)
        except duzenle.DuzenlemeHatasi as e:
            self._hata(str(e))
            return
        n = len(duzenle.al(self.agac, liste) or [])
        tambur = next(iter((self.spec or {}).get("tamburlar") or []), None)
        icerik = {"tur": "bilesen", "ad": tambur["ad"]} if tambur else duzenle.malzeme(
            self._varsayilan_malzeme())
        kesit = None if tambur else {"sekil": "silindir", "yaricap": 1.0}
        self._uygula(lambda: duzenle.yerlesim_ekle(self.agac, y, icerik, kesit=kesit),
                     _("Yerleşim eklendi"), liste + (n,))

    def katman_ekle(self):
        y = self._secili
        n = len((duzenle.al(self.agac, y) or {}).get("katmanlar") or [])
        self._uygula(lambda: duzenle.katman_ekle(self.agac, y), _("Katman eklendi"),
                     y + ("katmanlar", n))

    def grup_ekle(self):
        n = len(self.agac.get("gruplar") or [])
        self._uygula(lambda: duzenle.grup_ekle(self.agac, "donme"), _("Grup eklendi"),
                     ("gruplar", n))

    def parcaya_cikar(self):
        y = self._secili
        ad = self._ad_sor(_("Parçaya çıkar"), _("Parça adı:"), "parca")
        if not ad:
            return
        n = len(self.agac.get("parcalar") or [])
        self._uygula(lambda: duzenle.parcaya_cikar(self.agac, y, ad, self._kutuphane_adlari()),
                     _("Parçaya çıkarıldı: {ad}").format(ad=ad), ("parcalar", n))

    def sarmala(self):
        y = self._secili
        self._uygula(lambda: duzenle.sarmala(self.agac, y), _("Kapla sarmalandı"), y)

    def yeniden_adlandir(self):
        y = self._secili
        eski = (duzenle.al(self.agac, y) or {}).get("ad") or ""
        ad = self._ad_sor(_("Yeniden adlandır"), _("Yeni ad:"), eski)
        if not ad or ad == eski:
            return
        self._uygula(lambda: duzenle.yeniden_adlandir(self.agac, y, ad,
                                                      self._kutuphane_adlari()),
                     _("Yeniden adlandırıldı: {ad}").format(ad=ad), y)

    def sil(self):
        y = self._secili
        ust = y[:-1] if isinstance(y[-1], int) else y
        self._uygula(lambda: duzenle.sil(self.agac, y), _("Silindi"), ust or duzenle.KOK)

    def sira(self, yon):
        y = self._secili
        hedef = y[:-1] + (y[-1] + yon,) if y and isinstance(y[-1], int) else y
        liste = duzenle.al(self.agac, y[:-1]) if y else None
        if not isinstance(liste, list) or not (0 <= hedef[-1] < len(liste)):
            return
        self._uygula(lambda: duzenle.sira_tasi(self.agac, y, yon), _("Sıra değişti"), hedef)

    def _tasi(self, kaynak, hedef):
        self._uygula(lambda: duzenle.tasi(self.agac, kaynak, hedef), _("Taşındı"), hedef)

    def _kutuphane_adlari(self):
        adlar = set()
        for bolum in ("cubuklar", "plakalar", "demetler", "tamburlar", "malzemeler"):
            adlar |= {t.get("ad") for t in (self.spec or {}).get(bolum) or []}
        return adlar

    def _ad_sor(self, baslik, etiket, varsayilan):
        """Ad penceresi. Testler bunu degistirir (modal acilmaz)."""
        metin, tamam = QtWidgets.QInputDialog.getText(self, baslik, etiket,
                                                      text=varsayilan or "")
        return metin.strip() if tamam else None

    def _baglam_menusu(self, _yol, konum):
        menu = QtWidgets.QMenu(self)
        alt = menu.addMenu(_("+ Düğüm"))
        alt.setEnabled(self.d_dugum.isEnabled())
        for tur, ad in TUR_ADLARI.items():
            alt.addAction(_(ad), lambda t=tur: self.dugum_ekle(t))
        for k in ("halka", "yerlesim", "katman", "grup", "parca", "sarmala", "ad", "sil",
                  "yukari", "asagi"):
            d = self.dugmeler[k]
            e = menu.addAction(d.accessibleName(), d.click)
            e.setEnabled(d.isEnabled())
        menu.popup(konum)
        self.son_menu = menu

    # ------------------------------------------------------------------ kesik
    def _kesikler(self):
        """Kesik konumlar; hesaplanamazsa None (bos liste 'kesik yok' demektir)."""
        from cekirdek import geometri
        try:
            return geometri.kesik_konumlar(geometri.model(self.spec))
        except Exception:
            _log.warning("kesik konumlar hesaplanamadi", exc_info=True)
            return None

    def _kesik_ozeti(self):
        kesikler = self._kesikler() if self.spec else []
        if kesikler is None:
            self.kesik_etiketi.setText(_("Kesik konumlar hesaplanamadı (ayrıntı günlükte)."))
            self.d_git.setEnabled(False)
            self._kesik_listesi = []
            return
        n_k = sum(1 for k in kesikler if k.get("durum") == "kesik")
        n_g = len(kesikler) - n_k
        if not kesikler:
            self.kesik_etiketi.setText(_("Kesik konum yok."))
        else:
            self.kesik_etiketi.setText(
                _("⚠ {k} kesik konum (üst bölge ya da delik kırpıyor; hacim stokastik, "
                  "güç haritasında ayrı)  ⓘ {g} gizli konum").format(k=n_k, g=n_g))
        self.d_git.setEnabled(bool(kesikler))
        self._kesik_listesi = kesikler

    def kesige_git(self):
        for k in getattr(self, "_kesik_listesi", []):
            yol = _id_yolu(self.agac, k.get("kafes"))
            if yol is not None:
                self.sec(yol)
                return yol
        return None


def _id_yolu(agac, kimlik, yol=duzenle.KOK):
    """id'si 'kimlik' olan dugumun yolu (kok ve parcalar)."""
    def ara(d, y):
        if isinstance(d, dict):
            if d.get("id") == kimlik and d.get("tur"):
                return y
            for k, v in d.items():
                r = ara(v, y + (k,))
                if r is not None:
                    return r
        elif isinstance(d, list):
            for i, v in enumerate(d):
                r = ara(v, y + (i,))
                if r is not None:
                    return r
        return None
    if not kimlik:
        return None
    return ara(agac.get("kok"), duzenle.KOK) or ara(agac.get("parcalar"), ("parcalar",))
