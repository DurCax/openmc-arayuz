# -*- coding: utf-8 -*-
"""
test_hata_yutma.py -- SESSIZ HATA YUTMA denetimi (AST).

`cekirdek/` ve `arayuz/` altindaki genis `except` bloklarindan (Exception,
BaseException ya da ciplak `except:`) govdesi YALNIZCA `pass`, `continue`,
`return`, `return <sabit>` ya da bir ada sabit atama (`x = None`,
`a, b = None, None`, `x = []`) olanlari, ayrica `contextlib.suppress(Exception)`
kullanimlarini bulur. Boyle bir blok hatayi ne loglar ne de kullaniciya
gosterir: hata sessizce kaybolur.

IZIN LISTESI (IZINLI) dosya yoluna ya da satira DEGIL, islevin NITELIKLI
ADINA (ornek "AnaPencere._ciz") ve o islevdeki kayit SAYISINA gore tutulur;
boylece kod baska dosyaya tasininca liste bozulmaz.

  - Listede olmayan yeni kayit           -> KALDI (hatayi logla ya da goster)
  - Listedeki islevde kayit sayisi artti -> KALDI
  - Listedeki kayit azaldi ya da yok     -> KALDI: listeden SILIN/azaltin
    (liste yalnizca kuculur; Dalga 3 sonunda bos olmali)

Hatayi loglamak icin: `from cekirdek.gunluk import kaydedici`,
`kaydedici(__name__).exception("...")`.
"""

import ast
import os
from collections import Counter

from testler.ortak_test import kontrol, KOK

TARANAN_DIZINLER = ("cekirdek", "arayuz")
GENIS_ISTISNALAR = {"Exception", "BaseException"}

# Nitelikli islev adi -> o islevdeki sessiz except sayisi.
# Modul duzeyindeki kayitlar "<modul:dosya_adi>" anahtariyla tutulur.
IZINLI = {  # olculen: 31 kayit, 26 islev (28.09.2026; sabit atama kalibi eklenince)
    "AnalizSekmesi._bos_nedeni": 1,
    "AnalizSekmesi._hedefleri_listele": 1,
    "BaslangicEkrani._renkleri_uygula": 1,
    "AnalizSekmesi._varsayilan_aralik": 1,
    "CalistirSekmesi._bitti": 1,
    "CalistirSekmesi._guc_etkin": 1,
    "GelismisBolum._oku": 1,
    "GelismisBolum._yaz": 1,
    "MalzemeSekmesi.doldur": 1,
    "TukenmeSekmesi._ayirma_anlamli": 1,
    "TukenmeSekmesi._bitti": 1,
    "TukenmeSekmesi._uygunluk_oku": 1,
    "_LibYoneticisi.kapat": 1,
    "_h5_sicakliklari": 1,
    "_korelasyon": 1,
    "_kutle": 1,
    "_kutuphane_icerigi": 1,
    "_ortalama_kutle": 1,
    "_spec_fisil_mi": 1,
    "dagilim_oku": 1,
    "malzemeleri_oku": 3,
    "nuklid_enerji_tavani": 1,
    "ornek_listesi": 1,
    "sab_onerileri": 1,
    "sonuc_oku": 3,
    "tukenme_ayirma_anlamli": 1,
}


def _genis_mi(tur):
    """except tipi ciplak, Exception/BaseException ya da bunlari iceren demet mi?"""
    if tur is None:
        return True
    adlar = tur.elts if isinstance(tur, ast.Tuple) else [tur]
    for ad in adlar:
        if isinstance(ad, ast.Name) and ad.id in GENIS_ISTISNALAR:
            return True
        if isinstance(ad, ast.Attribute) and ad.attr in GENIS_ISTISNALAR:
            return True
    return False


def _sabit_mi(deger):
    """Sabit ya da yalnizca sabitlerden olusan literal: None, 0, "", (None, None),
    [], {}, -1 ..."""
    if isinstance(deger, ast.Constant):
        return True
    if isinstance(deger, ast.UnaryOp):
        return _sabit_mi(deger.operand)
    if isinstance(deger, (ast.Tuple, ast.List, ast.Set)):
        return all(_sabit_mi(e) for e in deger.elts)
    if isinstance(deger, ast.Dict):
        return all(k is not None and _sabit_mi(k) and _sabit_mi(v)
                   for k, v in zip(deger.keys, deger.values))
    return False


def _ad_hedefi_mi(hedef):
    if isinstance(hedef, ast.Name):
        return True
    return isinstance(hedef, (ast.Tuple, ast.List)) and all(
        _ad_hedefi_mi(e) for e in hedef.elts)


def _sessiz_ifade_mi(ifade):
    if isinstance(ifade, (ast.Pass, ast.Continue)):
        return True
    if isinstance(ifade, ast.Assign):
        # "x = None" / "a, b = None, None" / "x = []": hata varsayilan degerle
        # ortulur, iz kalmaz.
        return all(_ad_hedefi_mi(h) for h in ifade.targets) and _sabit_mi(ifade.value)
    if isinstance(ifade, ast.Return):
        return ifade.value is None or _sabit_mi(ifade.value)
    # Yalnizca aciklama metni (docstring benzeri) de sessizdir.
    return isinstance(ifade, ast.Expr) and isinstance(ifade.value, ast.Constant)


def _sessiz_mi(yakalayici):
    return all(_sessiz_ifade_mi(i) for i in yakalayici.body)


class _Tarayici(ast.NodeVisitor):
    """Sessiz genis except bloklarini nitelikli islev adiyla toplar."""

    def __init__(self, modul_etiketi):
        self._yigin = []
        self._modul = modul_etiketi
        self.kayitlar = []          # [(nitelikli_ad, satir)]

    def _kapsam(self, dugum):
        self._yigin.append(dugum.name)
        self.generic_visit(dugum)
        self._yigin.pop()

    visit_FunctionDef = _kapsam
    visit_AsyncFunctionDef = _kapsam
    visit_ClassDef = _kapsam

    def _kayit(self, satir):
        ad = ".".join(self._yigin) if self._yigin else "<modul:%s>" % self._modul
        self.kayitlar.append((ad, satir))

    def visit_With(self, dugum):
        # with contextlib.suppress(Exception): ...  (ya da suppress(...))
        for oge in dugum.items:
            cagri = oge.context_expr
            if (isinstance(cagri, ast.Call)
                    and getattr(cagri.func, "attr", getattr(cagri.func, "id", "")) == "suppress"
                    and any(_genis_mi(a) for a in cagri.args)):
                self._kayit(dugum.lineno)
        self.generic_visit(dugum)

    def visit_ExceptHandler(self, dugum):
        if _genis_mi(dugum.type) and _sessiz_mi(dugum):
            self._kayit(dugum.lineno)
        self.generic_visit(dugum)


def sessiz_yakalayicilar(kok=KOK):
    """{nitelikli_ad: sayi} ve ayrinti icin {nitelikli_ad: ["dosya:satir"]}."""
    sayac = Counter()
    yerler = {}
    for dizin in TARANAN_DIZINLER:
        for kok_dizin, _, dosyalar in os.walk(os.path.join(kok, dizin)):
            for dosya in sorted(dosyalar):
                if not dosya.endswith(".py"):
                    continue
                yol = os.path.join(kok_dizin, dosya)
                with open(yol, encoding="utf-8") as f:
                    agac = ast.parse(f.read(), filename=yol)
                tarayici = _Tarayici(os.path.splitext(dosya)[0])
                tarayici.visit(agac)
                goreli = os.path.relpath(yol, kok)
                for ad, satir in tarayici.kayitlar:
                    sayac[ad] += 1
                    yerler.setdefault(ad, []).append("%s:%d" % (goreli, satir))
    return dict(sayac), yerler


def izin_farki(bulunan, izinli):
    """(yeni_kayitlar, silinmesi_gerekenler): her biri {ad: (bulunan, izinli)}."""
    yeni = {ad: (n, izinli.get(ad, 0)) for ad, n in bulunan.items()
            if n > izinli.get(ad, 0)}
    eski = {ad: (bulunan.get(ad, 0), n) for ad, n in izinli.items()
            if bulunan.get(ad, 0) < n}
    return yeni, eski


def test_tarayici_ornekleri():
    print("\n[HY1] Sessiz except tarayicisi: ornek kodda dogru siniflandirma")
    kaynak = (
        "def a():\n    try:\n        x()\n    except Exception:\n        pass\n"
        "def b():\n    try:\n        x()\n    except:\n        return None\n"
        "class K:\n    def c(self):\n        for i in y:\n            try:\n"
        "                x()\n            except (ValueError, BaseException):\n"
        "                continue\n"
        "def d():\n    try:\n        x()\n    except Exception:\n"
        "        log.exception('x')\n"
        "def e():\n    try:\n        x()\n    except ValueError:\n        pass\n"
        "def f():\n    try:\n        x()\n    except Exception:\n        raise\n"
        "def g():\n    try:\n        x()\n    except Exception:\n        return (None, [])\n"
        "def h():\n    try:\n        x()\n    except Exception:\n        return y\n"
        "def i():\n    try:\n        x()\n    except Exception:\n        a, b = None, None\n"
        "def j():\n    with contextlib.suppress(Exception):\n        x()\n"
        "def k():\n    try:\n        x()\n    except Exception:\n        self.a = None\n"
        "def m():\n    try:\n        x()\n    except Exception:\n        a = hesapla()\n"
    )
    t = _Tarayici("ornek")
    t.visit(ast.parse(kaynak))
    adlar = sorted(ad for ad, _ in t.kayitlar)
    kontrol("pass / return None / continue / sabit literal yakalandi; log, raise, "
            "dar tip ve degisken donusu yakalanmadi; sabit atama ve suppress yakalandi",
            adlar == ["K.c", "a", "b", "g", "i", "j"],
            "-> %s" % adlar)
    yeni, eski = izin_farki({"a": 2, "b": 1}, {"a": 1, "c": 1})
    kontrol("izin farki: artan ve yeni kayit bulunur", yeni == {"a": (2, 1), "b": (1, 0)},
            "-> %s" % yeni)
    kontrol("izin farki: kaybolan kayit silinmesi istenir", eski == {"c": (0, 1)},
            "-> %s" % eski)


def test_sessiz_hata_yutma():
    print("\n[HY2] cekirdek/ ve arayuz/ icinde yeni sessiz 'except' yok")
    bulunan, yerler = sessiz_yakalayicilar()
    yeni, eski = izin_farki(bulunan, IZINLI)
    for ad, (n, izin) in sorted(yeni.items()):
        kontrol("YENI sessiz except: %s (%d > izinli %d)" % (ad, n, izin), False,
                "-> %s ; hatayi cekirdek.gunluk ile loglayin ya da gosterin"
                % ", ".join(yerler.get(ad, [])))
    for ad, (n, izin) in sorted(eski.items()):
        kontrol("IZIN LISTESI kuculmeli: %s artik %d (listede %d)" % (ad, n, izin),
                False, "-> testler/test_hata_yutma.py IZINLI'den silin/azaltin")
    kontrol("sessiz except sayisi izin listesiyle ayni (%d kayit)"
            % sum(bulunan.values()), not yeni and not eski)


HIZLI = [test_tarayici_ornekleri, test_sessiz_hata_yutma]
YAVAS = []
