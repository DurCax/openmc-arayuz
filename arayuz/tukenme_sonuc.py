# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_sonuc.py  --  Tukenme sonucu: onceki kosu, grafik, tablo, secim, CSV
================================================================================
 sekme_tukenme.py'den ayrildi (dosya 800 satiri asiyordu). Sonuc daima
 cekirdek.tukenme.sonuc_oku() ciktisidir. Izlenen nuklid secimi degisince
 gosterilen sonuc AYNI h5'ten yeniden okunur (kosu tekrarlanmaz; Results
 onbellekte). Izlenen nuklidler fizik degildir: secim degisti diye sonuc
 "eski" sayilmaz (cekirdek.tukenme._fizik_kismi izlenen'i dislar).

 YANMAYA GORE PIN GUCU (v3 K3): arayuz/tukenme_pin_bolumu.PinGucuBolumu karisimi.

 CSV: zaman [gun], yanma [MWd/kg], k, sigma ve her malzeme x nuklid icin atom
 sayisi ve yogunluk [atom/b-cm]. Ondalik ayirici NOKTA, alan ayirici virgul;
 sayilar repr() ile tam hassasiyette yazilir (yerel ayardan bagimsiz).
================================================================================
"""

import copy
import csv
import io
import os
import time

from PySide6 import QtCore, QtWidgets

from arayuz.analiz.adlar import renk
from arayuz.analiz.tuval import canli_mi
from arayuz.tukenme_pin_bolumu import PinGucuBolumu
from cekirdek import nuklidler as _nk
from cekirdek import tukenme as _tk
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
YAZI_LEJANT = 6         # nuklid grafigi lejanti [pt] (matplotlib)


def _sayi(x):
    return repr(float(x))


def csv_metni(sonuc):
    """sonuc_oku() ciktisindan CSV metni."""
    atomlar = sonuc.get("atomlar") or {}
    yogunluk = sonuc.get("yogunluk") or {}
    sutunlar = []                      # (baslik, degerler | None)
    for malz in sorted(set(atomlar) | set(yogunluk)):
        nuklidler = list(atomlar.get(malz, {}))
        nuklidler += [n for n in yogunluk.get(malz, {}) if n not in nuklidler]
        for n in nuklidler:
            sutunlar.append(("%s %s atom" % (malz, n), atomlar.get(malz, {}).get(n)))
            sutunlar.append(("%s %s [atom/b-cm]" % (malz, n), yogunluk.get(malz, {}).get(n)))
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    yazici.writerow([_("zaman [gün]"), _("yanma [MWd/kg]"), "k", "σ"]
                    + [b for b, _d in sutunlar])
    for i, z in enumerate(sonuc["zaman_d"]):
        satir = [_sayi(z), _sayi(sonuc["yanma"][i]), _sayi(sonuc["k"][i]),
                 _sayi(sonuc["k_sapma"][i])]
        satir += [(_sayi(d[i]) if d is not None and i < len(d) else "") for _b, d in sutunlar]
        yazici.writerow(satir)
    return tampon.getvalue()


def grafik_bos(eksen_k, eksen_n):
    for e, y in ((eksen_k, "k-eff"), (eksen_n, "atom/b-cm")):
        e.clear()
        e.grid(alpha=0.3)
        e.set_ylabel(y, fontsize=8)
        e.tick_params(labelsize=7)
    eksen_n.set_xlabel(_("yanma [MWd/kg]"), fontsize=8)


def grafik_ciz(eksen_k, eksen_n, s):
    """k-eff (ust) ve secili nuklidlerin yogunlugu (alt, log)."""
    from arayuz import tema as _t
    bu = s["yanma"]
    grafik_bos(eksen_k, eksen_n)
    eksen_k.errorbar(bu, s["k"], yerr=s["k_sapma"], fmt="o-", ms=3, lw=1.2,
                     color=_t.renk("vurgu"), capsize=2)
    eksen_k.axhline(1.0, color=_t.renk("metin_soluk"), lw=0.8, ls="--")
    yogunluk = s.get("yogunluk") or {}
    cizgi = False
    for ad, yog in yogunluk.items():
        for n, v in yog.items():
            if not any(x > 0 for x in v):
                continue
            xs = [b for b, x in zip(bu, v) if x > 0]
            ys = [x for x in v if x > 0]
            eksen_n.plot(xs, ys, "o-", ms=2, lw=1.0,
                         label=n if len(yogunluk) == 1 else "%s (%s)" % (n, ad))
            cizgi = True
    if cizgi:
        eksen_n.set_yscale("log")
        eksen_n.legend(fontsize=YAZI_LEJANT, ncol=2, loc="best")


def tablo_doldur(tablo, s):
    tablo.setRowCount(0)
    for z, b, kk, ss in zip(s["zaman_d"], s["yanma"], s["k"], s["k_sapma"]):
        r = tablo.rowCount()
        tablo.insertRow(r)
        rho = (kk - 1.0) / kk * 1e5
        for c, metin in enumerate(("%.3f" % z, "%.4f" % b,
                                   "%.5f +/- %.5f" % (kk, ss), "%+.0f" % rho)):
            tablo.setItem(r, c, QtWidgets.QTableWidgetItem(metin))
    tablo.resizeColumnsToContents()


def csv_kaydet(ebeveyn, sonuc, onerilen_yol):
    """Kullaniciya yol sorar ve CSV'yi yazar. DONER yazilan yol ya da None (vazgecti)."""
    yol, _suzgec = QtWidgets.QFileDialog.getSaveFileName(
        ebeveyn, _("Tükenme sonucunu CSV olarak kaydet"), onerilen_yol,
        _("CSV dosyası (*.csv)"))
    if not yol:
        return None
    if not yol.lower().endswith(".csv"):
        yol += ".csv"
    with open(yol, "w", encoding="utf-8", newline="") as f:
        f.write(csv_metni(sonuc))
    return yol


def _onceki_oku(spec, dizin, izlenen):
    """onceki_sonuc + SECILI nuklidlerle okuma (Results onbellekte: ikinci okuma ucuz)."""
    o = _tk.onceki_sonuc(spec, dizin)
    if o is not None:
        o["kaynak_spec"] = _tk._kayit_oku(dizin) or spec
        o["sonuc"] = _tk.sonuc_oku(o["h5"], o["kaynak_spec"], izlenen=izlenen)
    return o


def onceki_metni(durum, farklar, tarih, yapilan, beklenen):
    """
    Onceki sonucun durum satiri: (metin, tema rengi adi | None, kalin mi).
    Yarim kalmis kosu (durdurulmus ya da hala suren) "bu modele ait"
    denmez (Ajan 9 bulgusu K11); eski sonuc kirmizi ve kalin yazilir.
    """
    if beklenen and yapilan is not None and yapilan < beklenen:
        return (_("Yarım kalmış koşu (%s): %d / %d adım tamamlanmış. Koşu durdurulmuş "
                  "ya da hâlâ sürüyor olabilir; tam sonuç için yeniden koşun.")
                % (tarih, yapilan, beklenen), "uyari", True)
    if durum == "guncel":
        return _("Önceki koşunun sonucu (%s) — bu modele ait.") % tarih, None, False
    if durum == "eski":
        return (_("Eski sonuç (%s): model o koşudan beri değişti (%s). "
                  "Gösterilen sayılar bu modele ait değil — yeniden koşun.")
                % (tarih, _tk.fark_metni(farklar)), "hata", True)
    return (_("Önceki koşunun sonucu (%s). Koşunun model kaydı yok; bu "
              "modele ait olduğu doğrulanamıyor.") % tarih, "uyari", False)


class _Isci(QtCore.QThread):
    """
    Tukenme sonucunu arka planda okur (onceki sonuc ya da yeni secim).

    Olculdu: ilk okuma 3.4 s -- openmc.deplete ice aktarimi (1.2 s) +
    Results() dosyadaki 3820 nuklidin hepsini ayristiriyor (2.0 s). Resmi
    API'de kacinilmaz; arayuzde calissa donardi. Secim degisince Results
    onbellekten gelir (sonuc_oku), okuma milisaniyeler surer.
    """
    bitti = QtCore.Signal(object, object)      # (anahtar, sonuc | Exception)

    def __init__(self, islev, anahtar, parent=None):
        super().__init__(parent)
        self._islev = islev
        self._anahtar = anahtar

    def run(self):
        try:
            self.bitti.emit(self._anahtar, self._islev())
        except Exception as e:
            _log.exception("tükenme sonucu okunamadı")
            self.bitti.emit(self._anahtar, e)


class SonucBolumu(PinGucuBolumu):
    """
    TukenmeSekmesi'nin sonuc bolumu (karisim): onceki kosunun okunmasi,
    grafik/tablo, izlenen secimi degisince h5'ten yeniden okuma, CSV.
    Sekmenin nitelikleri (spec, izlenen, tablo, eksen_k/n, onceki_etiket,
    _kusak, _surec ...) TukenmeSekmesi.__init__'te kurulur.
    """

    # ==================================================================
    # onceki kosu
    # ==================================================================
    def _onceki_yukle(self):
        """
        Dizinde bir sonuc varsa gosterir. Dosya degismediyse tekrar okumaz:
        sekme her tazelendiginde 3.7 MB'lik sonucu okumak gereksiz.
        """
        if not self.canli_mi() or self._surec is not None or not self.spec:
            return
        dizin = self._okuma_dizini()
        h5 = os.path.join(dizin, "depletion_results.h5")
        if not os.path.exists(h5):
            degisti = self.sonuc_var()
            self._onceki = self._onceki_anahtar = None
            # Sonucun nereye yazilacagini soyle: dizin Calistir'daki kosu
            # dizininden turer; onu degistiren kullanici onceki sonucun neden
            # "kayboldugunu" gorebilsin (Ajan 9 bulgusu K12).
            self.onceki_etiket.setText(
                _("Bu model için kayıtlı tükenme sonucu yok. Sonuçlar şuraya yazılır: %s "
                  "(Çalıştır sekmesindeki koşu dizininden türetilir).")
                % _tk.kosu_dizini(self.spec, self.proje_yolu))
            self.onceki_etiket.setStyleSheet("color: %s;" % renk("metin_soluk"))
            self._sonucu_unut()
            self._grafik_bos()
            self.tablo.setRowCount(0)
            self._gorunum_guncelle()
            if degisti:
                self.sonuc_degisti.emit()
            return
        anahtar = (h5, os.path.getmtime(h5))
        if anahtar == self._onceki_anahtar:
            self._onceki_durum_guncelle()
            return
        if self._isci is not None and self._isci.isRunning():
            return                              # zaten okunuyor
        self.onceki_etiket.setStyleSheet("")
        self.onceki_etiket.setText(_("Önceki koşunun sonucu okunuyor…"))
        self._okuma_kusagi = self._kusak
        spec, izlenen = copy.deepcopy(self.spec), self.izlenen.secim()
        self._isci = _Isci(lambda: _onceki_oku(spec, dizin, izlenen), anahtar, self)
        self._isci.bitti.connect(self._onceki_geldi)
        # Kapanista calisan isci yok edilmesin (Qt sureci dusurur): aboutToQuit ->
        # isleri_durdur baglantisi TukenmeSekmesi.__init__'te kurulur.
        self._gorunum_guncelle()
        self._isci.start()

    def canli_mi(self):
        """Sekmenin C++ nesnesi duruyor mu. Arka plandaki okuma, sekme
        silindikten SONRA bitebilir (sayfa degisti / uygulama kapaniyor);
        sonucu olu widget'lara yazmak sureci dusururdu."""
        return canli_mi(self)

    def _onceki_geldi(self, anahtar, sonuc):
        if not self.canli_mi():
            _log.debug("tükenme sekmesi silindi; önceki sonuç yok sayıldı")
            return
        if self._okuma_kusagi is not None and self._okuma_kusagi != self._kusak:
            return                              # onceki projenin okumasi: atilir
        if self._surec is not None:
            return                              # bu arada yeni kosu basladi
        if isinstance(sonuc, Exception):
            self._onceki = None
            self.onceki_etiket.setText(_("Önceki sonuç okunamadı: %s") % sonuc)
            self._gorunum_guncelle()
            return
        if sonuc is None:
            return
        self._onceki, self._onceki_anahtar = sonuc, anahtar
        self._sonuc_goster(sonuc["sonuc"], (sonuc["h5"], sonuc.get("kaynak_spec") or self.spec))
        self._onceki_durum_guncelle()

    def bekle(self, ms=30000):
        """Arka plandaki okuma bitene kadar bekler (testler ve kapanis icin)."""
        son = time.monotonic() + ms / 1000.0
        if self._isci is not None:
            self._isci.wait(ms)
        QtWidgets.QApplication.processEvents()
        # Onceki sonuc gelince adim basina pin gucu okumasi baslar (K3): o da beklenir.
        self.pin_iscilerini_bekle(max(int((son - time.monotonic()) * 1000), 1))
        QtWidgets.QApplication.processEvents()
        # Secim okumasi zincirlenebilir (sirada bekleyen secim): bitene kadar.
        while self._secim_okunuyor and time.monotonic() < son:
            if self._secim_isci is not None:
                self._secim_isci.wait(max(int((son - time.monotonic()) * 1000), 1))
            QtWidgets.QApplication.processEvents()

    def _onceki_durum_guncelle(self):
        """Gosterilen sonucun SU ANKI spec'e ait olup olmadigini yazar."""
        if not self._onceki or self._surec is not None:
            return
        dizin = os.path.dirname(self._onceki["h5"])
        durum, farklar = _tk.eskime(self.spec, dizin)
        tarih = time.strftime("%Y-%m-%d %H:%M", time.localtime(self._onceki["tarih"]))  # ISO 8601
        kayit = _tk._kayit_oku(dizin) or {}
        beklenen = len((kayit.get("tukenme") or {}).get("adimlar") or [])
        yapilan = (self._onceki.get("sonuc") or {}).get("adim_sayisi")
        metin, ton, kalin = onceki_metni(durum, farklar, tarih, yapilan, beklenen)
        stil = ("color: %s;" % renk(ton)) if ton else ""
        if kalin:
            stil += " font-weight: bold;"
        self.onceki_etiket.setText(metin)
        self.onceki_etiket.setStyleSheet(stil)
        self._pin_eskime_yaz()

    # ==================================================================
    # sonuclar
    # ==================================================================
    def _grafik_bos(self):
        if not self.canli_mi():
            return
        grafik_bos(self.eksen_k, self.eksen_n)
        self.tuval.draw_idle()

    def _sonucu_unut(self):
        """Gosterilen sonucun kaynagini birakir (proje degisti / yeni kosu)."""
        self._sonuc = self._kaynak = None
        self._secim_bekliyor = False
        self._pin_gucu_unut()
        self.csv_dugmesi.setEnabled(False)
        self.bulunamayan_etiket.setText("")
        self.bulunamayan_etiket.setVisible(False)

    def _sonuc_goster(self, s, kaynak=None):
        """s: sonuc_oku() ciktisi. kaynak: (h5, okuma spec'i) -- secim degisince
        ayni dosyadan yeniden okumak icin (None: onceki kaynak korunur)."""
        if not self.canli_mi():
            _log.debug("tükenme sekmesi silindi; sonuç gösterilmedi")
            return
        if kaynak is not None:
            self._kaynak = kaynak
            self._pin_gucu_yukle(kaynak)
        self._sonuc = s
        grafik_ciz(self.eksen_k, self.eksen_n, s)
        self.tuval.draw_idle()
        tablo_doldur(self.tablo, s)
        self._bulunamayan_yaz(s.get("bulunamayan") or [])
        self.csv_dugmesi.setEnabled(True)
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()

    def _bulunamayan_yaz(self, bulunamayan):
        """Sonucta olmayan izlenen adlar: eskiden SESSIZCE atlaniyordu."""
        if not self.canli_mi():
            return
        parcalar = []
        for ad in bulunamayan:
            onerilen = _nk.oneri(ad, self.izlenen.adlar())
            parcalar.append(_nk.oneri_metni(ad, onerilen) if onerilen else ad)
        self.bulunamayan_etiket.setText(
            _("Sonuçta bulunamayan nüklidler (grafikte yok): %s") % ", ".join(parcalar)
            if parcalar else "")
        self.bulunamayan_etiket.setStyleSheet("color: %s;" % renk("hata"))
        self.bulunamayan_etiket.setVisible(bool(parcalar))

    # ==================================================================
    # izlenen nuklidler: secim degisince h5'ten yeniden okuma
    # ==================================================================
    def _izlenen_degisti(self, liste):
        if self._yukleniyor or not self.spec:
            return
        self.spec.setdefault("tukenme", {})["izlenen"] = list(liste)
        self.bildir()
        self._secim_oku()

    def _secim_oku(self):
        """Gosterilen sonucu yeni secimle ayni h5'ten okur (kosu tekrarlanmaz)."""
        if self._kaynak is None or self._surec is not None:
            return
        if self._secim_okunuyor:
            self._secim_bekliyor = True           # bitince son secimle tekrar
            return
        self._secim_bekliyor = False
        self._secim_okunuyor = True
        h5, spec = self._kaynak
        izlenen, kusak = self.izlenen.secim(), self._kusak
        self._secim_isci = _Isci(lambda: _tk.sonuc_oku(h5, spec, izlenen=izlenen),
                                 (kusak, h5), self)
        self._secim_isci.bitti.connect(self._secim_geldi)
        self._secim_isci.start()

    def _secim_geldi(self, anahtar, sonuc):
        self._secim_okunuyor = False
        if not self.canli_mi():
            _log.debug("tükenme sekmesi silindi; seçim sonucu yok sayıldı")
            return
        if anahtar[0] != self._kusak or self._surec is not None or self._kaynak is None:
            return                                  # proje degisti ya da kosu basladi
        if self._secim_bekliyor:
            self._secim_oku()                       # bu sonuc eski secime ait
            return
        if isinstance(sonuc, Exception):
            self.bulunamayan_etiket.setText(_("Seçim sonuç dosyasından okunamadı: %s") % sonuc)
            self.bulunamayan_etiket.setVisible(True)
            return
        self._sonuc_goster(sonuc)

    def csv_disa_aktar(self):
        if not self._sonuc:
            return
        dizin = os.path.dirname(self._kaynak[0]) if self._kaynak else os.getcwd()
        try:
            yol = csv_kaydet(self, self._sonuc, os.path.join(dizin, "tukenme.csv"))
        except OSError as e:
            _log.exception("CSV yazılamadı")
            QtWidgets.QMessageBox.warning(self, _("CSV yazılamadı"), str(e))
            return
        if yol:
            self.durum.emit(_("CSV kaydedildi: %s") % yol, True)
