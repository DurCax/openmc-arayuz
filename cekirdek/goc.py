# -*- coding: utf-8 -*-
"""
================================================================================
 goc.py  --  Spec sema surumu gocu (1 -> 2 -> 3) ve bozuk dosya korumasi
================================================================================

 Her adim SAF bir islevdir: girdi sozlugu degismez, yeni bir sozluk doner.
 sema.yukle() dosyayi okur, once burada goc ettirir, sonra tamamla() ile
 eksik alanlari varsayilanla doldurur.

 ZINCIR
   1 -> 2 (M2): guc_dagilimi'nin eski tek hedefli bicimi ("cubuk", "bolge")
                yeni liste bicimine ("cubuklar") cevrilir. Icerik degismez.
   2 -> 3     : esnek geometri alanlari eklenir: "geometri": None,
                "tamburlar": []. DISKTEKI KOR DEGISMEZ -- sablonlar calisma
                aninda genisletilir (cekirdek/geometri/sablon.py), bu yuzden
                gocun kendisi risksizdir.

 BOZUK DOSYA KORUMASI
   - JSON cozulemiyorsa, kok bir nesne degilse, "surum" sayi degilse ya da
     zorunlu bolum (kor) yoksa/yanlis turdeyse GocHatasi (ValueError) --
     hicbir alan sessizce dusurulmez.
   - surum > GUNCEL_SURUM: "daha yeni bir surumle yazilmis" hatasi; eski
     surum yeni alanlari bilmedigi icin dosyayi okuyup yazmak veri kaybeder.
   - Eski surumlu (ya da bozuk) bir dosyanin USTUNE yazmadan once
     yedekle(dosya) "<dosya>.bak" yazar (sema.kaydet cagirir).
================================================================================
"""

import copy
import json
import os
import shutil

from cekirdek.ceviri import _

GUNCEL_SURUM = 3

# Dosyada bulunmasi ZORUNLU bolumler ve beklenen turleri. Digerleri eksikse
# tamamla() varsayilanla doldurur (eski dosyalar boyle acilir).
ZORUNLU_BOLUMLER = (("kor", dict),)
# Varsa turu dogru olmasi gereken bolumler (yanlis tur = bozuk dosya).
BOLUM_TURLERI = (("malzemeler", list), ("cubuklar", list), ("plakalar", list),
                 ("demetler", list), ("tallyler", list), ("tamburlar", list),
                 ("ayarlar", dict), ("guc_dagilimi", dict), ("tukenme", dict),
                 ("calistirma", dict))


class GocHatasi(ValueError):
    """Dosya okunamaz ya da bu surumle goc ettirilemez."""


def surum_oku(ham):
    """
    Ham sozlugun sema surumu (int). Alan yoksa 1 (surum alani eklenmeden
    once yazilan dosyalar). Sayi olmayan surum GocHatasi.
    """
    if "surum" not in ham:
        return 1
    s = ham["surum"]
    if isinstance(s, bool) or not isinstance(s, (int, float)):
        raise GocHatasi(_("Dosyadaki şema sürümü sayı değil: %r") % (s,))
    if isinstance(s, float) and not s.is_integer():
        raise GocHatasi(_("Dosyadaki şema sürümü tam sayı değil: %r") % (s,))
    return int(s)


def goc_1_2(ham):
    """1 -> 2: guc_dagilimi eski bicimi (cubuk/bolge) -> cubuklar listesi."""
    yeni = copy.deepcopy(ham)
    g = yeni.get("guc_dagilimi")
    if isinstance(g, dict) and "cubuklar" not in g and "cubuk" in g:
        ad = g.get("cubuk")
        g["cubuklar"] = ([{"cubuk": ad, "bolge": int(g.get("bolge") or 0)}]
                         if ad else [])
    if isinstance(g, dict):
        g.pop("cubuk", None)
        g.pop("bolge", None)
    yeni["surum"] = 2
    return yeni


def goc_2_3(ham):
    """2 -> 3: esnek geometri alanlari (geometri, tamburlar). Kor degismez."""
    yeni = copy.deepcopy(ham)
    yeni.setdefault("geometri", None)
    yeni.setdefault("tamburlar", [])
    yeni["surum"] = 3
    return yeni


ZINCIR = {1: goc_1_2, 2: goc_2_3}


def _bolum_denetimi(ham):
    """Zorunlu bolumler ve bolum turleri. Sorun varsa GocHatasi."""
    for ad, tur in ZORUNLU_BOLUMLER:
        if ad not in ham:
            raise GocHatasi(_("Dosyada zorunlu '%s' bölümü yok; dosya bozuk ya da "
                              "bir model dosyası değil.") % ad)
        if not isinstance(ham[ad], tur):
            raise GocHatasi(_("'%s' bölümünün türü yanlış (%s bekleniyordu).")
                            % (ad, tur.__name__))
    for ad, tur in BOLUM_TURLERI:
        if ham.get(ad) is not None and not isinstance(ham[ad], tur):
            raise GocHatasi(_("'%s' bölümünün türü yanlış (%s bekleniyordu).")
                            % (ad, tur.__name__))
    geo = ham.get("geometri")
    if geo is not None and not isinstance(geo, dict):
        raise GocHatasi(_("'geometri' bölümü bir nesne olmalı."))


def goc_ettir(ham, zorunlu_denetim=True):
    """
    Ham sozlugu GUNCEL_SURUM'e getirir. DONER (yeni sozluk, [uygulanan adimlar]).
    Girdi DEGISMEZ. Daha yeni surum ya da bozuk yapi GocHatasi.
    """
    if not isinstance(ham, dict):
        raise GocHatasi(_("Dosyanın kökü bir JSON nesnesi değil."))
    surum = surum_oku(ham)
    if surum > GUNCEL_SURUM:
        raise GocHatasi(_("Bu dosya daha yeni bir sürümle yazılmış (şema sürümü %d; "
                          "bu uygulama en çok %d okur). Uygulamayı güncelleyin.")
                        % (surum, GUNCEL_SURUM))
    if surum < 1:
        raise GocHatasi(_("Geçersiz şema sürümü: %d") % surum)
    if zorunlu_denetim:
        _bolum_denetimi(ham)
    yeni, adimlar = copy.deepcopy(ham), []
    while surum < GUNCEL_SURUM:
        yeni = ZINCIR[surum](yeni)
        adimlar.append("%d->%d" % (surum, surum + 1))
        surum += 1
    return yeni, adimlar


def dosya_oku(dosya):
    """JSON dosyasini okur ve goc ettirir. DONER (sozluk, adimlar)."""
    try:
        with open(dosya, encoding="utf-8") as f:
            ham = json.load(f)
    except json.JSONDecodeError as e:
        raise GocHatasi(_("Dosya bozuk (JSON çözülemedi): %s, satır %d sütun %d: %s")
                        % (os.path.basename(dosya), e.lineno, e.colno, e.msg)) from e
    except UnicodeDecodeError as e:
        raise GocHatasi(_("Dosya UTF-8 metin değil: %s") % os.path.basename(dosya)) from e
    return goc_ettir(ham)


def _diskteki_surum(dosya):
    """Diskteki dosyanin surumu; okunamiyorsa (bozuk) None."""
    try:
        with open(dosya, encoding="utf-8") as f:
            return surum_oku(json.load(f))
    except (OSError, ValueError):     # bozuk/okunamayan dosya: belgelenen donus None
        return None


def yedekle(dosya):
    """
    'dosya' eski surumluyse ya da bozuksa ustune yazilmadan once
    '<dosya>.bak' kopyasini yazar (var olan yedek korunur: ilk ozgun hali
    kaybolmasin). DONER yedek yolu ya da None (yedek gerekmedi).
    """
    if not os.path.exists(dosya):
        return None
    surum = _diskteki_surum(dosya)
    if surum is not None and surum >= GUNCEL_SURUM:
        return None
    hedef = dosya + ".bak"
    if os.path.exists(hedef):
        return hedef
    shutil.copy2(dosya, hedef)
    return hedef
