# -*- coding: utf-8 -*-
"""
 test_h2_isci.py  --  v3 H2 cizim iscisi: istek dongusu (en son istek, iptal,
                      hata yaniti), openmc.lib oturumunun acik tutulmasi ve
                      giris.py dagitici kaydi
"""

import io
import os

import numpy as np

from testler.ortak_test import kontrol, ORNEK


class _SahteOturum:
    """openmc.lib'siz oturum: kesit cagrilarini kaydeder."""

    def __init__(self, kesit_kancasi=None, hazirla_hatasi=None):
        self.kesitler = []
        self.hazirlanan = []
        self._kanca = kesit_kancasi
        self._hata = hazirla_hatasi

    def hazirla(self, spec):
        if self._hata:
            raise self._hata
        self.hazirlanan.append(spec.get("ad"))
        return len(self.hazirlanan) == 1

    def ozellikler(self):
        return {"sinir_kutu": [2.0, 2.0], "yukseklik": None,
                "renkler": {"1": [255, 0, 0]}, "gosterge": [["yakit", [255, 0, 0]]]}

    def kesit(self, eksen, piksel, cakisma=False):
        self.kesitler.append(eksen)
        if self._kanca:
            self._kanca(len(self.kesitler))
        return (2.0, 2.0), np.full((piksel, piksel, 3), 1, dtype=np.int32), []

    def kapat(self):
        pass


def _istek(no, ad, kesitler=("xy", "xz")):
    return {"tur": "ciz", "no": no, "spec": {"ad": ad},
            "kesitler": [{"eksen": e, "piksel": 16} for e in kesitler]}


def _yanitlar(cikis):
    from cekirdek import cizim_sureci as cs
    return cs.CerceveCozucu().besle(cikis.getvalue())


def test_dongu_yalniz_en_son_istegi_isler():
    print("\n[H2I-1] isci dongusu: kuyrukta biriken isteklerden yalniz EN SONU islenir")
    from cekirdek import cizim_sureci as cs
    # Arrange: iki istek ardisik yazilir, sonra girdi kapanir
    oku, yaz = os.pipe()
    os.write(yaz, cs.cerceve(_istek(1, "A")) + cs.cerceve(_istek(2, "B")))
    os.close(yaz)
    cikis, oturum = io.BytesIO(), _SahteOturum()
    # Act
    kod = cs.dongu(cs.Kanal(oku, cikis), oturum)
    os.close(oku)
    # Assert
    yanit = _yanitlar(cikis)
    kontrol("girdi kapaninca cikis kodu 0", kod == 0)
    kontrol("ilk yanit 'hazir' (surum + pid)", yanit[0].baslik["tur"] == "hazir"
            and yanit[0].baslik["surum"] == cs.PROTOKOL_SURUMU)
    kontrol("yalniz B hazirlandi (A atlandi)", oturum.hazirlanan == ["B"], "-> %s" % oturum.hazirlanan)
    turler = [(c.baslik["tur"], c.baslik["no"]) for c in yanit[1:]]
    kontrol("B: model, iki kesit, son", turler == [("model", 2), ("kesit", 2), ("kesit", 2),
                                                   ("son", 2)], "-> %s" % turler)
    kontrol("kesit dizisi (16, 16, 3) int32", yanit[2].diziler["geom"].shape == (16, 16, 3))
    kontrol("son durumu tamam", yanit[-1].baslik["durum"] == "tamam")


def test_dongu_yeni_istek_eskisini_iptal_eder():
    print("\n[H2I-2] isci dongusu: kesitler arasinda yeni istek gelirse eskisi 'iptal'")
    from cekirdek import cizim_sureci as cs
    oku, yaz = os.pipe()

    def kanca(n):                      # ilk kesit cizilirken yeni istek gelir
        if n == 1:
            os.write(yaz, cs.cerceve(_istek(2, "B", ("xy",))))
            os.close(yaz)
    os.write(yaz, cs.cerceve(_istek(1, "A")))
    cikis, oturum = io.BytesIO(), _SahteOturum(kesit_kancasi=kanca)
    cs.dongu(cs.Kanal(oku, cikis), oturum)
    os.close(oku)
    sonlar = [(c.baslik["no"], c.baslik["durum"]) for c in _yanitlar(cikis)
              if c.baslik["tur"] == "son"]
    kontrol("A iptal, B tamam", sonlar == [(1, "iptal"), (2, "tamam")], "-> %s" % sonlar)
    kontrol("A'nin ikinci kesiti cizilmedi", oturum.kesitler == ["xy", "xy"],
            "-> %s" % oturum.kesitler)


def test_dongu_hata_yanit_olur_ve_surer():
    print("\n[H2I-3] isci dongusu: kurulum hatasi ve gecersiz istek 'hata' yaniti olur")
    from cekirdek import cizim_sureci as cs
    oku, yaz = os.pipe()
    os.write(yaz, cs.cerceve({"tur": "ciz", "no": 1, "spec": {}, "kesitler": []}))
    os.close(yaz)
    cikis = io.BytesIO()
    cs.dongu(cs.Kanal(oku, cikis), _SahteOturum())
    os.close(oku)
    son = [c.baslik for c in _yanitlar(cikis) if c.baslik["tur"] == "son"]
    kontrol("gecersiz istek -> hata yaniti (no korunur)", son and son[0]["no"] == 1
            and son[0]["durum"] == "hata" and son[0]["hata"], "-> %s" % son)
    oku, yaz = os.pipe()
    os.write(yaz, cs.cerceve(_istek(5, "A")))
    os.close(yaz)
    cikis = io.BytesIO()
    cs.dongu(cs.Kanal(oku, cikis), _SahteOturum(hazirla_hatasi=KeyError("tanımsız malzeme: x")))
    os.close(oku)
    son = [c.baslik for c in _yanitlar(cikis) if c.baslik["tur"] == "son"]
    kontrol("kurulum hatasi -> hata + iz; KeyError tirnaksiz",
            son and son[0]["durum"] == "hata" and son[0]["hata"] == "tanımsız malzeme: x"
            and "KeyError" in son[0]["iz"], "-> %s" % son)


def test_dongu_cik_istegi():
    print("\n[H2I-4] isci dongusu: 'cik' kuyrukta oncelikli, kesit cizilmez")
    from cekirdek import cizim_sureci as cs
    oku, yaz = os.pipe()
    os.write(yaz, cs.cerceve(_istek(1, "A")) + cs.cerceve({"tur": "cik", "no": 2}))
    cikis, oturum = io.BytesIO(), _SahteOturum()
    kod = cs.dongu(cs.Kanal(oku, cikis), oturum)
    os.close(yaz)
    os.close(oku)
    kontrol("cik -> 0, istek islenmedi", kod == 0 and oturum.hazirlanan == [])


def test_giris_cizim_alt_sureci():
    print("\n[H2I-5] giris.py: '--alt cizim' dagiticida kayitli, arguman kabul etmez")
    from cekirdek import giris
    program, arg = giris.alt_surec_komutu(giris.ALT_CIZIM, [], python="/py")
    kontrol("komut: python -m cekirdek.giris --alt cizim",
            (program, arg) == ("/py", giris._GUVENLI_YOL + ["-m", "cekirdek.giris", "--alt", "cizim"]))
    kontrol("arguman verilirse kullanim hatasi (2)", giris.alt_komutu(["cizim", "fazla"]) == 2)


def test_oturum_acik_tutulur_ve_kapanir():
    print("\n[H2I-6] openmc.lib oturumu: ayni spec yeniden baslatmaz, degisen spec baslatir")
    import openmc.lib
    from cekirdek import cizim_sureci as cs, sema
    s1 = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    s2 = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    oturum = cs.Oturum()
    eski = os.getcwd()
    try:
        ilk = oturum.hazirla(s1)
        ikinci = oturum.hazirla(s1)
        genislik, geom, cak = oturum.kesit("xy", 32)
        kontrol("ilk hazirla baslatir, ikinci baslatmaz", ilk and not ikinci)
        kontrol("kesit: sinir kutusu genisligi, (32, 32, 3) int32",
                genislik == tuple(oturum.ozellikler()["sinir_kutu"])
                and geom.shape == (32, 32, 3) and geom.dtype == np.int32 and cak == [])
        kontrol("pin kesitinde malzeme var", int((geom[..., 2] > 0).sum()) > 0)
        kontrol("degisen spec yeniden baslatir", oturum.hazirla(s2))
        _g, _geom, cak = oturum.kesit("xz", 32, cakisma=True)
        kontrol("cakisma denetimi: temiz modelde cakisma yok", cak == [])
        bozuk = dict(s1, malzemeler=[])
        try:
            oturum.hazirla(bozuk)
            hata = False
        except Exception:
            hata = True
        kontrol("bozuk spec istisna verir, kutuphane kapali kalir",
                hata and not openmc.lib.is_initialized and oturum.ozet is None)
    finally:
        oturum.kapat()
        os.chdir(eski)
    kontrol("kapat sonrasi kutuphane kapali, calisma dizini geri",
            not openmc.lib.is_initialized and os.getcwd() == eski)


HIZLI = [test_dongu_yalniz_en_son_istegi_isler, test_dongu_yeni_istek_eskisini_iptal_eder,
         test_dongu_hata_yanit_olur_ve_surer, test_dongu_cik_istegi, test_giris_cizim_alt_sureci,
         test_oturum_acik_tutulur_ve_kapanir]
YAVAS = []
# '-p' kipi veri istemez; ama conftest koruyucusu test surecinde openmc.lib.init'i
# veri yokken yasaklar (kipi ayirt edemez): surec ici oturum testi listede kalir.
VERI_GEREKEN = [test_oturum_acik_tutulur_ve_kapanir]
