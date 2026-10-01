# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/form_kafes.py  --  Kafes, eksenel yigin, katman ve parca formlari
================================================================================
 KafesFormu: sekil (kare / altigen), adim, boyut ya da halka sayisi + yonelim,
             HARITA DUZENLEYICISI (izgara.KareIzgara / AltigenIzgara; palette
             harfler ve "." = dis dolgu), "+ Harf". Harfin icerigi agacta o
             harfin dugumu secilerek duzenlenir. Kesik / gizli konumlar
             (geometri.kesik_konumlar) haritada taranir (§15 karar 2: UYARI).
 EksenelFormu, KatmanFormu, ParcaFormu: yigin ozeti; katman adi / yuksekligi /
             varsayilan icerik; parca adi ve kullanim sayisi.
================================================================================
"""

import string

from PySide6 import QtWidgets

from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz.geometri import renk as _renk
from arayuz import izgara, tema
from arayuz.geometri import duzenle
from arayuz.geometri.form_ortak import FormTabani, form_duzeni, sayi_yaz, uzunluk
from arayuz.ortak import ipucu
from arayuz.tasarim import tokenlar

_log = kaydedici("arayuz.geometri.form_kafes")
A = tokenlar.ARALIK
DIS = "."
_HARFLER = string.ascii_uppercase + string.ascii_lowercase + string.digits


def halka_uzunlugu(halka_sayisi, r):
    """Distan ice r. halkanin hucre sayisi (merkez 1)."""
    k = halka_sayisi - 1 - r
    return 1 if k == 0 else 6 * k


def altigen_yeniden_boyutla(harita, eski_n, yeni_n, dolgu):
    """Halka sayisi degisince ICTEN hizalanir: ic halkalar korunur."""
    ic_ten = list(reversed(harita or []))
    yeni = []
    for j in range(yeni_n):                 # j = icten indeks (0 = merkez)
        uzunluk_ = 1 if j == 0 else 6 * j
        if j < len(ic_ten) and len(ic_ten[j]) == uzunluk_:
            yeni.append(ic_ten[j])
        else:
            yeni.append(dolgu * uzunluk_)
    return list(reversed(yeni))


def kare_yeniden_boyutla(harita, nx, ny, dolgu):
    """Sol ust koseden hizali; yeni hucreler dolgu harfiyle."""
    eski = list(harita or [])
    return [(eski[r] if r < len(eski) else "")[:nx].ljust(nx, dolgu) for r in range(ny)]


class KafesFormu(FormTabani):
    BASLIK = N_("Kafes")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.kimlik = QtWidgets.QLabel("-")
        self.kimlik.setObjectName("soluk")
        self.sekil = QtWidgets.QComboBox()
        self.sekil.addItem(_("Kare"), "kare")
        self.sekil.addItem(_("Altıgen"), "altigen")
        self.adim = uzunluk(1.26, 1e-6, _("kafes adımı"))
        self.nx = QtWidgets.QSpinBox()
        self.ny = QtWidgets.QSpinBox()
        self.halka = QtWidgets.QSpinBox()
        for k in (self.nx, self.ny, self.halka):
            k.setRange(1, 60)
        self.yonelim = QtWidgets.QComboBox()
        self.yonelim.addItem(_("y — komşular yukarıda"), "y")
        self.yonelim.addItem(_("x — komşular sağda"), "x")
        self.palet = izgara.ParcaPaleti()
        self.kare = izgara.KareIzgara()
        self.altigen = izgara.AltigenIzgara()
        for g in (self.kare, self.altigen):
            g.etiketleri_goster(True)
            g.setMinimumHeight(12 * A["l"])
        self.d_harf = QtWidgets.QPushButton(_("+ Harf"))
        self.kesik_notu = ipucu("")
        self._kur()
        self._bagla()

    def _kur(self):
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Kimlik"), self.kimlik)
        f.addRow(_("Şekil"), self.sekil)
        f.addRow(_("Adım"), self.adim)
        f.addRow(_("Sütun"), self.nx)
        f.addRow(_("Satır"), self.ny)
        f.addRow(_("Halka sayısı"), self.halka)
        f.addRow(_("Yönelim"), self.yonelim)
        f.addRow(ipucu(_("Adım: kare kafeste hücre kenarı, altıgende düz yüzden düz yüze. "
                         "Harita paletinde “·” kafesin dış dolgusudur.")))
        f.addRow(self.palet)
        f.addRow(self.kare)
        f.addRow(self.altigen)
        f.addRow(self.d_harf)
        f.addRow(self.kesik_notu)
        self._form = f

    def _bagla(self):
        self.ad.editingFinished.connect(lambda: self.yaz("ad", self.ad.text().strip() or None))
        self.sekil.currentIndexChanged.connect(self._sekil_degisti)
        self.adim.degisti.connect(lambda v: self.yaz("adim", float(v)))
        for k in (self.nx, self.ny):
            k.valueChanged.connect(self._boyut_degisti)
        self.halka.valueChanged.connect(self._halka_degisti)
        self.yonelim.currentIndexChanged.connect(
            lambda _i: self.yaz("yonelim", self.yonelim.currentData()))
        for g in (self.kare, self.altigen):
            self.palet.secildi.connect(g.firca_ayarla)
            g.firca_istendi.connect(self.palet.sec)
            g.degisti.connect(self._boyandi)
        self.d_harf.clicked.connect(self._harf_ekle)

    # ------------------------------------------------------------------
    def doldur(self, k):
        kare = k.get("sekil", "kare") == "kare"
        self.ad.setText(k.get("ad") or "")
        self.kimlik.setText(k.get("id") or "-")
        self.sekil.setCurrentIndex(0 if kare else 1)
        sayi_yaz(self.adim, k.get("adim") or 1.0)
        nx, ny = k.get("boyut") or (len((k.get("harita") or [""])[0]), len(k.get("harita") or []))
        self.nx.setValue(int(nx or 1))
        self.ny.setValue(int(ny or 1))
        self.halka.setValue(int(k.get("halka_sayisi") or 1))
        self.yonelim.setCurrentIndex(0 if k.get("yonelim", "y") == "y" else 1)
        for w, g in ((self.nx, kare), (self.ny, kare), (self.halka, not kare),
                     (self.yonelim, not kare), (self.kare, kare), (self.altigen, not kare)):
            self._form.setRowVisible(w, g)
        self._paleti_doldur(k)
        harita = [list(s) for s in k.get("harita") or []]
        izg = self.kare if kare else self.altigen
        if kare:
            self.kare.yukle(harita, self.palet.renkler())
        else:
            self.altigen.yukle(harita, int(k.get("halka_sayisi") or 1), k.get("yonelim", "y"),
                               self.palet.renkler())
        izg.firca_ayarla(self.palet.secili())
        self._kesikleri_isaretle(k, izg)

    def _paleti_doldur(self, k):
        from cekirdek.geometri.sema import yuva_adi
        ogeler = []
        for h, icerik in sorted((k.get("anahtar") or {}).items()):
            ad = yuva_adi(icerik)
            ogeler.append((h, "%s → %s" % (h, ad), _renk.parca_rengi(self.spec, _renk_adi(icerik))))
        dis = k.get("dis")
        ogeler.append((DIS, _("· → dış ({ad})").format(ad=yuva_adi(dis)),
                       _renk.parca_rengi(self.spec, _renk_adi(dis))))
        self.palet.parcalari_ayarla(ogeler)
        self.kare.kisaltmalari_ayarla({h: h for h, *_r in ogeler})
        self.altigen.kisaltmalari_ayarla({h: h for h, *_r in ogeler})

    def _kesikleri_isaretle(self, k, izg):
        from cekirdek import geometri
        isaret = {}
        try:
            m = geometri.model(dict(self.spec, geometri=self.agac))
            for kk in geometri.kesik_konumlar(m):
                if kk.get("kafes") == k.get("id") and kk.get("kafes"):
                    isaret[tuple(kk["indeks"])] = kk["durum"]
        except Exception:
            _log.warning("kesik konumlar hesaplanamadi", exc_info=True)
            izg.isaretleri_ayarla({}, tema.renk("uyari"))
            self.kesik_notu.setText(_("Kesik konumlar hesaplanamadı (ayrıntı günlükte)."))
            self._form.setRowVisible(self.kesik_notu, True)
            return
        izg.isaretleri_ayarla(isaret, tema.renk("uyari"))
        n_k = sum(1 for v in isaret.values() if v == "kesik")
        n_g = len(isaret) - n_k
        self.kesik_notu.setText(
            _("Taralı: {k} kesik konum (üst bölge ya da delik kırpıyor — uyarı), "
              "{g} gizli konum.").format(k=n_k, g=n_g) if isaret else "")
        self._form.setRowVisible(self.kesik_notu, bool(isaret))

    # ------------------------------------------------------------------
    def _sekil_degisti(self, *_a):
        if self._yukleniyor:
            return
        k = dict(self.oge())
        dolgu = next(iter(sorted(k.get("anahtar") or {})), DIS)
        if self.sekil.currentData() == "kare":
            k.update(sekil="kare", boyut=[3, 3], harita=[dolgu * 3] * 3)
            k.pop("halka_sayisi", None)
            k.pop("yonelim", None)
        else:
            k.update(sekil="altigen", halka_sayisi=2, yonelim="y",
                     harita=[dolgu * 6, dolgu])
            k.pop("boyut", None)
        self._yeni_kafes(k)

    def _boyut_degisti(self, *_a):
        if self._yukleniyor:
            return
        k = dict(self.oge())
        dolgu = next(iter(sorted(k.get("anahtar") or {})), DIS)
        k["boyut"] = [self.nx.value(), self.ny.value()]
        k["harita"] = kare_yeniden_boyutla(k.get("harita"), self.nx.value(), self.ny.value(),
                                           dolgu)
        self._yeni_kafes(k)

    def _halka_degisti(self, *_a):
        if self._yukleniyor:
            return
        k = dict(self.oge())
        dolgu = next(iter(sorted(k.get("anahtar") or {})), DIS)
        n = self.halka.value()
        k["harita"] = altigen_yeniden_boyutla(k.get("harita"), int(k.get("halka_sayisi") or 1),
                                              n, dolgu)
        k["halka_sayisi"] = n
        self._yeni_kafes(k)

    def _yeni_kafes(self, k):
        self.agac_yay(duzenle.yaz(self.agac, self.yol, k))
        self._yukleniyor = True
        try:
            self.doldur(self.oge())
        finally:
            self._yukleniyor = False

    def _boyandi(self):
        izg = self.kare if self.sekil.currentData() == "kare" else self.altigen
        harita = ["".join(h or DIS for h in satir) for satir in izg.adlar()]
        self.yaz("harita", harita)

    def _harf_ekle(self):
        k = self.oge() or {}
        kullanilan = set(k.get("anahtar") or {})
        harf = next((h for h in _HARFLER if h not in kullanilan), None)
        if harf is None:
            return
        malzemeler = self.malzeme_secenekleri()
        dolgu = malzemeler[1][0] if len(malzemeler) > 1 else duzenle.BOSLUK
        yeni = duzenle.yaz(self.agac, self.yol + ("anahtar",),
                           dict(k.get("anahtar") or {}, **{harf: duzenle.malzeme(dolgu)}))
        self._yeni_kafes_agac(yeni)

    def _yeni_kafes_agac(self, yeni):
        self.agac_yay(yeni)
        self._yukleniyor = True
        try:
            self.doldur(self.oge())
        finally:
            self._yukleniyor = False


def _renk_adi(icerik):
    if isinstance(icerik, dict):
        if icerik.get("tur") in ("malzeme", "bilesen"):
            return icerik.get("ad")
        return icerik.get("id") or icerik.get("tur")
    return icerik


class EksenelFormu(FormTabani):
    BASLIK = N_("Eksenel yığın")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.ozet = QtWidgets.QLabel("-")
        self.ozet.setWordWrap(True)
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Katmanlar"), self.ozet)
        f.addRow(ipucu(_("Katmanlar alttan üste dizilir; yığın z = 0 etrafında ortalanır. "
                         "Katman eklemek için araç çubuğundaki “+ Katman”; sırayı ▲/▼ "
                         "değiştirir. İçeriği boş katman varsayılan içeriği kullanır.")))
        self.ad.editingFinished.connect(lambda: self.yaz("ad", self.ad.text().strip() or None))

    def doldur(self, e):
        self.ad.setText(e.get("ad") or "")
        katmanlar = e.get("katmanlar") or []
        toplam = sum(float(k.get("yukseklik") or 0.0) for k in katmanlar)
        self.ozet.setText(_("{n} katman, toplam {h:g} cm").format(n=len(katmanlar), h=toplam))


class KatmanFormu(FormTabani):
    BASLIK = N_("Katman")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.yukseklik = uzunluk(10.0, 0.0, _("katman yüksekliği"))
        self.varsayilan = QtWidgets.QCheckBox(_("Yığının varsayılan içeriğini kullan"))
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Yükseklik"), self.yukseklik)
        f.addRow(self.varsayilan)
        f.addRow(ipucu(_("0 cm katman atlanır. Kök dışındaki bir yığının toplamı model "
                         "yüksekliğine eşit olmalıdır.")))
        self.ad.editingFinished.connect(lambda: self.yaz("ad", self.ad.text().strip() or None))
        self.yukseklik.degisti.connect(lambda v: self.yaz("yukseklik", float(v)))
        self.varsayilan.toggled.connect(self._varsayilan_degisti)

    def doldur(self, k):
        self.ad.setText(k.get("ad") or "")
        sayi_yaz(self.yukseklik, k.get("yukseklik") or 0.0)
        self.varsayilan.setChecked(k.get("icerik") is None)

    def _varsayilan_degisti(self, acik):
        if self._yukleniyor:
            return
        k = dict(self.oge())
        k["icerik"] = None if acik else duzenle.malzeme(
            (self.malzeme_secenekleri()[1:2] or [(duzenle.BOSLUK, "")])[0][0])
        self.agac_yay(duzenle.yaz(self.agac, self.yol, k))


class ParcaFormu(FormTabani):
    BASLIK = N_("Parça")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.kullanim = QtWidgets.QLabel("-")
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Kullanım"), self.kullanim)
        f.addRow(ipucu(_("Parça, birden çok yerde kullanılan alt ağaçtır: OpenMC'de tek "
                         "evren kurulur (distribcell ve tükenme örnekleri bölünmez).")))
        self.ad.editingFinished.connect(self._ad_degisti)

    def doldur(self, p):
        self.ad.setText(p.get("ad") or "")
        n = _sayac(self.agac, p.get("ad"))
        self.kullanim.setText(_("{n} yerde kullanılıyor").format(n=n))

    def _ad_degisti(self):
        if self._yukleniyor or self.ad.text().strip() == (self.oge() or {}).get("ad"):
            return
        try:
            self.agac_yay(duzenle.yeniden_adlandir(self.agac, self.yol, self.ad.text(),
                                                   self.kutuphane_adlari()))
        except duzenle.DuzenlemeHatasi as e:
            self.ad.setText((self.oge() or {}).get("ad") or "")
            self.ad.setToolTip(str(e))


def _sayac(deger, ad):
    if isinstance(deger, dict):
        n = 1 if deger.get("tur") == "bilesen" and deger.get("ad") == ad else 0
        return n + sum(_sayac(v, ad) for v in deger.values())
    if isinstance(deger, list):
        return sum(_sayac(v, ad) for v in deger)
    return 0
