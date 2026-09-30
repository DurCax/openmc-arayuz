# -*- coding: utf-8 -*-
"""
test_hata_yutma.py -- SESSIZ HATA YUTMA denetimi (AST).

`cekirdek/` ve `arayuz/` altindaki genis `except` bloklarindan (Exception,
BaseException ya da ciplak `except:`) govdesi YALNIZCA su ifadelerden olusanlari
bulur:
  - `pass`, `continue`, `return`, `return <sabit>`, aciklama metni;
  - bir ada sabit atama (`x = None`, `a, b = None, None`, `x = []`);
  - hata METNINI bir degiskene, nitelige ya da sozluk alanina yazma
    (`self.hata = str(e)`, `d["hata"] = "%s" % e`, `m = f"...{e}"`,
    `m = "{}".format(e)`, `repr(e)`, `hatalar.append(str(e))`): metin saklanir ama ne loglanir ne
    gosterilir -- cogu zaman hic okunmaz.
Ayrica `contextlib.suppress(Exception)` kullanimlarini bulur. Log cagrisi,
`raise` ya da degiskenle `return` iceren yakalayici bu kurala takilmaz
(bilinmeyen herhangi bir cagri da "belki logluyor" sayilir ve gecer).

IZIN LISTESI (IZINLI) satira DEGIL, "modul:islev" anahtarina (ornek
"cekirdek.kosucu:sonuc_oku", "arayuz.pencere.ana_pencere:AnaPencere._ciz")
ve o islevdeki kayit SAYISINA gore tutulur. Modul adi anahtardadir: farkli
modullerdeki ayni adli islevler (kosucu.sonuc_oku / tukenme.sonuc_oku)
butce paylasmaz. Modul duzeyindeki kayitlar "<modul>:<modul>" anahtarini alir.

  - Listede olmayan yeni kayit           -> KALDI (hatayi logla ya da goster)
  - Listedeki islevde kayit sayisi artti -> KALDI
  - Listedeki kayit azaldi ya da yok     -> KALDI: listeden SILIN/azaltin
    (liste yalnizca kuculur; Dalga 3 sonunda bos olmali)

BILGI (KALDI degil): DAR tipli (`except RuntimeError: return`) ama
GEREKCESIZ sessiz yutmalar ayri listede raporlanir. Gerekce, except
satirinda ya da yakalayici govdesinde bir `#` yorumudur.

Hatayi loglamak icin: `from cekirdek.gunluk import kaydedici`,
`kaydedici(__name__).exception("...")`.
"""

import ast
import io
import os
import tokenize
from collections import Counter

from testler.ortak_test import kontrol, KOK

TARANAN_DIZINLER = ("cekirdek", "arayuz")
GENIS_ISTISNALAR = {"Exception", "BaseException"}
# Hata nesnesini METNE ceviren (baska yan etkisi olmayan) cagrilar.
METIN_CAGRILARI = {"str", "repr", "type", "format"}
# Hata metnini bir kaba birakan (loglamayan) yontemler: `hatalar.append(str(e))`.
KABA_EKLEME = {"append", "add", "extend", "insert"}

# "modul:nitelikli_islev" -> o islevdeki sessiz except sayisi.
# Olculen 29.09.2026 (D1-C): 33 kayit. Kaynak dosya satirlari rapordadir.
#   (T) Dalga 1 tabani (eski anahtar "islev" -> "modul:islev" tasindi; 26 kayit).
#   (Y) D1-C yeni kurali (hata metnini alana/listeye yazip birakma) ile eklenen
#       taban cizgisi; DUZELTME Dalga 2 sahiplerine kalir (7 kayit).
IZINLI = {
    "arayuz.malzeme.yardimcilar:sab_onerileri": 1,                # (T)
    "arayuz.onizleme:_LibYoneticisi.kapat": 1,                    # (T)
    "arayuz.sekme_analiz:AnalizSekmesi._bos_nedeni": 1,           # (T)
    "arayuz.sekme_analiz:AnalizSekmesi._hedefleri_listele": 1,    # (T)
    "arayuz.sekme_analiz:AnalizSekmesi._varsayilan_aralik": 1,    # (T)
    "arayuz.sekme_calistir:CalistirSekmesi._bitti": 1,            # (T)
    "arayuz.sekme_calistir:CalistirSekmesi._guc_etkin": 1,        # (T)
    "arayuz.sekme_malzeme:MalzemeSekmesi.doldur": 1,              # (T)
    "cekirdek.dogrula.veri:_kutuphane_icerigi": 1,                # (T)
    "cekirdek.ice_aktar:malzemeleri_oku": 4,                      # (T) 3 + (Y) 1
    "cekirdek.kurucu:_spec_fisil_mi": 1,                          # (T)
    "cekirdek.uygunluk:_korelasyon": 1,                           # (T)
    "cekirdek.uygunluk:_kutle": 1,                                # (T)
    "cekirdek.uygunluk:_ortalama_kutle": 1,                       # (T)
    "cekirdek.uygunluk:tukenme_ayirma_anlamli": 1,                # (T)
    "cekirdek.veri_bilgi:_h5_sicakliklari": 1,                    # (T)
    "cekirdek.veri_bilgi:nuklid_enerji_tavani": 1,                # (T)
    "cekirdek.veri_bilgi:zincir_kontrol": 1,                      # (Y) sonuc = (False, "...%s" % e, None)
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


def _metin_cagrisi_mi(cagri):
    ad = getattr(cagri.func, "id", None) or getattr(cagri.func, "attr", None)
    return ad in METIN_CAGRILARI


def _hata_metni_mi(deger, hata_adi):
    """Deger yalnizca sabitlerden, hata nesnesinden ve onu metne ceviren
    ifadelerden (str/repr/format, %, +, f-string) mi olusuyor VE hata
    nesnesini kullaniyor mu? Baska bir cagri (olasi log) varsa hayir."""
    if hata_adi is None:
        return False
    kullanildi = False
    for dugum in ast.walk(deger):
        if isinstance(dugum, ast.Call) and not _metin_cagrisi_mi(dugum):
            return False
        if isinstance(dugum, ast.Name) and dugum.id == hata_adi:
            kullanildi = True
    return kullanildi


def _ad_hedefi_mi(hedef):
    if isinstance(hedef, ast.Name):
        return True
    return isinstance(hedef, (ast.Tuple, ast.List)) and all(
        _ad_hedefi_mi(e) for e in hedef.elts)


def _atama_sessiz_mi(ifade, hata_adi):
    hedefler = ifade.targets if isinstance(ifade, ast.Assign) else [ifade.target]
    if ifade.value is None:                         # "x: int" (bildirim)
        return True
    if _hata_metni_mi(ifade.value, hata_adi):
        # Hata metni bir ada, niteliğe ya da sozluk alanina yazilip birakilir.
        return True
    # "x = None" / "a, b = None, None" / "x = []": hata varsayilan degerle
    # ortulur, iz kalmaz.
    return all(_ad_hedefi_mi(h) for h in hedefler) and _sabit_mi(ifade.value)


def _sessiz_ifade_mi(ifade, hata_adi=None):
    if isinstance(ifade, (ast.Pass, ast.Continue)):
        return True
    if isinstance(ifade, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return _atama_sessiz_mi(ifade, hata_adi)
    if isinstance(ifade, ast.Return):
        return ifade.value is None or _sabit_mi(ifade.value)
    if not isinstance(ifade, ast.Expr):
        return False
    # Yalnizca aciklama metni (docstring benzeri) de sessizdir.
    if isinstance(ifade.value, ast.Constant):
        return True
    return _kaba_ekleme_mi(ifade.value, hata_adi)


def _kaba_ekleme_mi(cagri, hata_adi):
    """`hatalar.append("... %s" % e)`: hata metni bir listeye birakilir."""
    return (isinstance(cagri, ast.Call) and isinstance(cagri.func, ast.Attribute)
            and cagri.func.attr in KABA_EKLEME and bool(cagri.args)
            and all(_hata_metni_mi(a, hata_adi) or _sabit_mi(a) for a in cagri.args)
            and any(_hata_metni_mi(a, hata_adi) for a in cagri.args))


def _sessiz_mi(yakalayici):
    return all(_sessiz_ifade_mi(i, yakalayici.name) for i in yakalayici.body)


def yorum_satirlari(kaynak):
    """Kaynaktaki `#` yorumlarinin satir numaralari (metin icindeki # sayilmaz)."""
    satirlar = set()
    try:
        for jeton in tokenize.generate_tokens(io.StringIO(kaynak).readline):
            if jeton.type == tokenize.COMMENT:
                satirlar.add(jeton.start[0])
    except (tokenize.TokenError, SyntaxError) as hata:
        raise ValueError("kaynak jetonlanamadi: %s" % hata) from hata
    return satirlar


class _Tarayici(ast.NodeVisitor):
    """Sessiz except bloklarini "modul:nitelikli_ad" anahtariyla toplar.

    kayitlar: genis tipli sessiz bloklar (izin listesiyle karsilastirilir).
    bilgi:    dar tipli, gerekcesiz (yorumsuz) sessiz bloklar (yalniz rapor).
    """

    def __init__(self, modul_etiketi, yorumlar=frozenset()):
        self._yigin = []
        self._modul = modul_etiketi
        self._yorumlar = yorumlar
        self.kayitlar = []          # [(anahtar, satir)]
        self.bilgi = []             # [(anahtar, satir)]

    def _kapsam(self, dugum):
        self._yigin.append(dugum.name)
        self.generic_visit(dugum)
        self._yigin.pop()

    visit_FunctionDef = _kapsam
    visit_AsyncFunctionDef = _kapsam
    visit_ClassDef = _kapsam

    def _anahtar(self):
        islev = ".".join(self._yigin) if self._yigin else "<modul>"
        return "%s:%s" % (self._modul, islev)

    def _kayit(self, satir):
        self.kayitlar.append((self._anahtar(), satir))

    def visit_With(self, dugum):
        # with contextlib.suppress(Exception): ...  (ya da suppress(...))
        for oge in dugum.items:
            cagri = oge.context_expr
            if (isinstance(cagri, ast.Call)
                    and getattr(cagri.func, "attr", getattr(cagri.func, "id", "")) == "suppress"
                    and any(_genis_mi(a) for a in cagri.args)):
                self._kayit(dugum.lineno)
        self.generic_visit(dugum)

    def _gerekceli_mi(self, dugum):
        son = getattr(dugum, "end_lineno", None) or dugum.lineno
        return any(s in self._yorumlar for s in range(dugum.lineno, son + 1))

    def visit_ExceptHandler(self, dugum):
        if _sessiz_mi(dugum):
            if _genis_mi(dugum.type):
                self._kayit(dugum.lineno)
            elif not self._gerekceli_mi(dugum):
                self.bilgi.append((self._anahtar(), dugum.lineno))
        self.generic_visit(dugum)


def modul_adi(goreli_yol):
    """"cekirdek/dogrula/veri.py" -> "cekirdek.dogrula.veri"."""
    return os.path.splitext(goreli_yol)[0].replace(os.sep, ".")


def tara_dizinler(kok=KOK):
    """Her dosya icin (goreli_yol, tarayici)."""
    for dizin in TARANAN_DIZINLER:
        for kok_dizin, _, dosyalar in os.walk(os.path.join(kok, dizin)):
            for dosya in sorted(dosyalar):
                if not dosya.endswith(".py"):
                    continue
                yol = os.path.join(kok_dizin, dosya)
                with open(yol, encoding="utf-8") as f:
                    kaynak = f.read()
                goreli = os.path.relpath(yol, kok)
                tarayici = _Tarayici(modul_adi(goreli), yorum_satirlari(kaynak))
                tarayici.visit(ast.parse(kaynak, filename=yol))
                yield goreli, tarayici


def _say(tarayicilar, alan):
    sayac, yerler = Counter(), {}
    for goreli, tarayici in tarayicilar:
        for ad, satir in getattr(tarayici, alan):
            sayac[ad] += 1
            yerler.setdefault(ad, []).append("%s:%d" % (goreli, satir))
    return dict(sayac), yerler


def sessiz_yakalayicilar(kok=KOK):
    """{anahtar: sayi} ve ayrinti icin {anahtar: ["dosya:satir"]}."""
    return _say(tara_dizinler(kok), "kayitlar")


def gerekcesiz_dar_yakalayicilar(kok=KOK):
    """BILGI: dar tipli gerekcesiz sessiz yutmalar ({anahtar: sayi}, yerler)."""
    return _say(tara_dizinler(kok), "bilgi")


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
            adlar == ["ornek:K.c", "ornek:a", "ornek:b", "ornek:g", "ornek:i", "ornek:j"],
            "-> %s" % adlar)
    yeni, eski = izin_farki({"a": 2, "b": 1}, {"a": 1, "c": 1})
    kontrol("izin farki: artan ve yeni kayit bulunur", yeni == {"a": (2, 1), "b": (1, 0)},
            "-> %s" % yeni)
    kontrol("izin farki: kaybolan kayit silinmesi istenir", eski == {"c": (0, 1)},
            "-> %s" % eski)


def tara_kaynak(kaynak, modul="ornek"):
    """Kaynak metni tarar: (kayitlar, bilgi) -- her biri [(anahtar, satir)]."""
    t = _Tarayici(modul, yorum_satirlari(kaynak))
    t.visit(ast.parse(kaynak))
    return t.kayitlar, t.bilgi


def _adlar(kayitlar):
    return sorted(ad for ad, _ in kayitlar)


def test_hata_metni_atamasi():
    print("\n[HY3] Hata metnini yalnizca bir alana yazan genis except de sessizdir")
    kaynak = (
        "def a(self):\n    try:\n        x()\n    except Exception as e:\n"
        "        self.hata = str(e)\n"
        "def b(d):\n    try:\n        x()\n    except Exception as e:\n"
        "        d['hata'] = '%s' % e\n"
        "def c():\n    try:\n        x()\n    except Exception as e:\n"
        "        mesaj = f'olmadi: {e}'\n"
        "def d():\n    try:\n        x()\n    except Exception as e:\n"
        "        mesaj = '{}'.format(e)\n        sonuc = None\n"
        "def e():\n    try:\n        x()\n    except Exception as hata:\n"
        "        mesaj = repr(hata)\n"
        "def k(hatalar):\n    for t in y:\n        try:\n            x()\n"
        "        except Exception as e:\n            hatalar.append('tohum %d: %s' % (t, e))\n"
        # --- gecenler: log, raise, disari aktarim, bilinmeyen cagri
        "def f():\n    try:\n        x()\n    except Exception as e:\n"
        "        mesaj = str(e)\n        log.warning(mesaj)\n"
        "def g():\n    try:\n        x()\n    except Exception as e:\n"
        "        mesaj = str(e)\n        raise\n"
        "def h(d):\n    try:\n        x()\n    except Exception as e:\n"
        "        d['hata'] = str(e)\n        return d\n"
        "def i():\n    try:\n        x()\n    except Exception as e:\n"
        "        mesaj = hesapla(e)\n"
        "def j():\n    try:\n        x()\n    except Exception as e:\n"
        "        self.hata = kaydedici(__name__).exception(str(e))\n"
        "def m(s):\n    try:\n        x()\n    except Exception as e:\n"
        "        s.mesaj = str(e); return s\n"
    )
    kayitlar, _ = tara_kaynak(kaynak)
    adlar = _adlar(kayitlar)
    kontrol("str(e) / '%s' % e / f-string / format / repr atamasi ve listeye ekleme "
            "sessiz; log, raise, degisken donusu ve bilinmeyen cagri sessiz degil",
            adlar == ["ornek:a", "ornek:b", "ornek:c", "ornek:d", "ornek:e", "ornek:k"],
            "-> %s" % adlar)


def test_modul_nitelikli_anahtar():
    print("\n[HY4] Izin anahtari modul:islev -- ayni adli islevler butce paylasmaz")
    kaynak = "def sonuc_oku():\n    try:\n        x()\n    except Exception:\n        pass\n"
    k1, _ = tara_kaynak(kaynak, "kosucu")
    k2, _ = tara_kaynak(kaynak, "tukenme")
    kontrol("anahtarlar modul adini tasir", _adlar(k1 + k2)
            == ["kosucu:sonuc_oku", "tukenme:sonuc_oku"], "-> %s" % _adlar(k1 + k2))
    kaynak_modul = "try:\n    x()\nexcept Exception:\n    pass\n"
    k3, _ = tara_kaynak(kaynak_modul, "ayar")
    kontrol("modul duzeyi kayit 'modul:<modul>'", _adlar(k3) == ["ayar:<modul>"],
            "-> %s" % _adlar(k3))
    yeni, _ = izin_farki({"kosucu:sonuc_oku": 1, "tukenme:sonuc_oku": 1},
                         {"kosucu:sonuc_oku": 1})
    kontrol("baska moduldeki ayni adli islev yeni kayit sayilir",
            yeni == {"tukenme:sonuc_oku": (1, 0)}, "-> %s" % yeni)


def test_dar_tip_gerekcesiz_bilgi():
    print("\n[HY5] Dar tipli gerekcesiz sessiz yutma: ayri BILGI listesi (KALDI degil)")
    kaynak = (
        "def a():\n    try:\n        x()\n    except RuntimeError:\n        return\n"
        "def b():\n    try:\n        x()\n    except (KeyError, ValueError):\n        pass\n"
        "def c():\n    try:\n        x()\n    except RuntimeError:  # kapali: yok sayilir\n"
        "        return\n"
        "def d():\n    try:\n        x()\n    except KeyError:\n"
        "        # anahtar yoksa varsayilan kalir\n        pass\n"
        "def e():\n    try:\n        x()\n    except ValueError:\n"
        "        kaydedici(__name__).warning('x')\n"
        "def f():\n    try:\n        x()\n    except ValueError:\n        raise\n"
        "def g():\n    try:\n        x()\n    except Exception:\n        pass\n"
    )
    kayitlar, bilgi = tara_kaynak(kaynak)
    kontrol("gerekcesiz dar tip bilgi listesinde; yorumlu, loglayan, yeniden "
            "firlatan ve genis olanlar yok", _adlar(bilgi) == ["ornek:a", "ornek:b"],
            "-> %s" % _adlar(bilgi))
    kontrol("dar tipli kayitlar sessiz (KALDI) listesine girmez",
            _adlar(kayitlar) == ["ornek:g"], "-> %s" % _adlar(kayitlar))


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
    # BILGI (KALDI degil): dar tipli ama gerekcesiz sessiz yutmalar.
    dar, dar_yerler = gerekcesiz_dar_yakalayicilar()
    print("  [BILGI] dar tipli gerekcesiz sessiz yutma: %d kayit (except satirina "
          "ya da govdeye kisa bir # gerekce yazin)" % sum(dar.values()))
    for ad in sorted(dar_yerler):
        print("    - %s -> %s" % (ad, ", ".join(dar_yerler[ad])))


HIZLI = [test_tarayici_ornekleri, test_hata_metni_atamasi, test_modul_nitelikli_anahtar,
         test_dar_tip_gerekcesiz_bilgi, test_sessiz_hata_yutma]
YAVAS = []
