# -*- coding: utf-8 -*-
"""
================================================================================
 dogrula.py  --  Model calistirilmadan once yapilan kontroller
================================================================================

 Monte Carlo kosusu pahalidir; hatalarin cogu saatler sonra ya da hic fark
 edilmez. Bu modul bilinen tuzaklari kosu ONCESINDE yakalar.

 KULLANIM
   from cekirdek import dogrula
   bulgular = dogrula.tum_kontroller(spec)
   for b in bulgular:
       print(b)
   if dogrula.hata_var(bulgular):
       ...  # calistirma engellenir

 SEVIYELER
   hata   : model calismaz ya da sonuc kesinlikle yanlis olur -- calistirma engellenir
   uyari  : model calisir ama sonuc supheli -- kullanici karar verir
   bilgi  : dikkat cekici ama sorun degil

 KONTROL LISTESI
   1. OPENMC_CROSS_SECTIONS ortam degiskeni ve dosyanin varligi
   2. Modelin istedigi her nuklidin veri kutuphanesinde bulunmasi
   3. S(a,b) unutulmus moderatorler (su/grafit/berilyum)
   4. Malzeme tanimlari: yogunluk, bos bilesim, negatif deger
   5. Cubuk bolgeleri: artan yaricap, son bolgenin acik olmasi
   6. Kafes haritalari: satir/sutun sayisi, tanimsiz harf
   7. Sinir kosullari ve sizinti riski
   8. Ayarlar: pasif cevrim sayisi, parcacik sayisi
   9. Tanimli ama kullanilmayan / kullanilmis ama tanimsiz malzemeler
  10. Bu modelde GECERLI OLMAYAN secimler -- kurallar uygunluk.py'de (arayuz
      ayni kurallarla secenekleri gizler; burada elle yazilmis dosyalar
      yakalanir): sinir kosullari, bu kor turunde kurulmayan alanlar,
      guc dagilimi cubugu, fisil malzeme gerektiren secimler (ozdeger modu,
      kutu kaynagi, tukenme), malzeme rolleri (emici / yakit)
================================================================================
"""

import math
import os

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import altigen, kurucu, veri_bilgi, sema
from cekirdek import kaynak as _kaynak
# "Bu modelde ne gecerli?" kurallarinin TEK kaynagi. Arayuz ayni kurallarla
# secenekleri gizler/suzer; burada ayni kurali ihlal eden (elle yazilmis)
# dosyalar yakalanir. Kural burada TEKRAR YAZILMAZ.
from cekirdek import uygunluk

# Alt moduller (bolunme: Dalga 0). Bugunku butun herkese acik ve testlerin/
# arayuzun kullandigi ozel adlar burada yeniden dis verilir; boylece
# `from cekirdek import dogrula; dogrula.X` aynen calisir. Yukaridaki
# importlar da ayni nedenle (eski modulun ad alani) burada kalir.
#   _ortak   : Bulgu, hata_var, yer_etiketi       veri     : kutuphane, nuklid
#   malzeme  : malzeme, S(a,b)                    geometri : cubuk/plaka/demet, kafes
#   kor      : kor, sinir kosullari               eksenel  : eksenel katmanlar
#   tukenme  : tukenme                            ayar     : hesap ayarlari
#   kaynak   : kaynak                             referans : tally, guc, fisil, referans
from cekirdek.dogrula._ortak import (  # noqa: F401
    _kor_turu_adi, _YER_ETIKETI, yer_etiketi, Bulgu, hata_var)
from cekirdek.dogrula.veri import (  # noqa: F401
    veri_kutuphanesi_kontrol, _kutuphane_icerigi, nuklid_kontrol)
from cekirdek.dogrula.malzeme import (  # noqa: F401
    _SAB_KURALLARI, _YOGUN_FAZ_ESIGI, malzeme_kontrol, _element_kumesi, _sab_kontrol)
from cekirdek.dogrula.geometri import (  # noqa: F401
    _PLAKA_ALAN_ADI, cubuk_kontrol, kontrol_cubugu_kontrol, plaka_kontrol,
    demet_kontrol, _cubuk_dis_capi, _kafes_olculeri, _kafes_icerik_kontrol)
from cekirdek.dogrula.kor import (  # noqa: F401
    _YON_ADI, _SINIR_ADI, kor_kontrol)
from cekirdek.dogrula.eksenel import (  # noqa: F401
    eksenel_kontrol, _ad_var)
from cekirdek.dogrula.tukenme import (  # noqa: F401
    _SPEKTRUM_ADI, tukenme_kontrol)
from cekirdek.dogrula.ayar import (  # noqa: F401
    ayar_kontrol)
from cekirdek.dogrula.kaynak import (  # noqa: F401
    kaynak_kontrol, _kutuphane_icerigi_foton)
from cekirdek.dogrula.referans import (  # noqa: F401
    BILINEN_SKORLAR, tally_kontrol, guc_dagilimi_kontrol, fisil_gereksinim_kontrol,
    referans_kontrol)


# ============================================================================
# 6. TOPLU CALISTIRMA
# ============================================================================

def tum_kontroller(spec, veri_kontrolu=True):
    """
    Tum kontrolleri sirayla calistirir.
    veri_kontrolu=False ise nuklid/kutuphane kontrolu atlanir (hizli mod).
    DONER Bulgu listesi -- once hatalar, sonra uyarilar, sonra bilgiler.
    """
    bulgular = []
    if veri_kontrolu:
        bulgular += veri_kutuphanesi_kontrol()
    bulgular += malzeme_kontrol(spec)
    bulgular += cubuk_kontrol(spec)
    bulgular += kontrol_cubugu_kontrol(spec)
    bulgular += plaka_kontrol(spec)
    bulgular += demet_kontrol(spec)
    bulgular += kor_kontrol(spec)
    bulgular += eksenel_kontrol(spec)
    bulgular += ayar_kontrol(spec)
    bulgular += kaynak_kontrol(spec, veri_kontrolu)
    bulgular += tukenme_kontrol(spec, veri_kontrolu)
    bulgular += tally_kontrol(spec)
    bulgular += guc_dagilimi_kontrol(spec)
    bulgular += referans_kontrol(spec)
    # nuklid kontrolu malzemeleri kurmayi gerektirir; once temel hatalar temiz olmali
    if veri_kontrolu and not hata_var(bulgular):
        bulgular += nuklid_kontrol(spec)
    # fisil gereksinimi nuklid kontrolunden SONRA (bkz. fonksiyon notu)
    bulgular += fisil_gereksinim_kontrol(spec)

    sira = {"hata": 0, "uyari": 1, "bilgi": 2}
    return sorted(bulgular, key=lambda b: sira[b.seviye])


class DogrulamaHatasi(ValueError):
    """Spec'te "hata" seviyesinde bulgu var; kosu baslatilmaz.

    ValueError alt sinifidir: kosu hatalarini ValueError olarak yakalayan
    mevcut cagiranlar (tarama noktasi, kritik arama) davranisini korur.
    `bulgular` yalnizca hata seviyesindeki bulgulardir; `tum_bulgular` ayni
    denetimin butun bulgulari (hata + uyari + bilgi, sirali) -- cagiran
    tum_kontroller'i ikinci kez kosmadan hepsini gosterebilsin. Verilmezse
    `bulgular`in kopyasidir."""

    def __init__(self, bulgular, tum_bulgular=None):
        self.bulgular = list(bulgular)
        self.tum_bulgular = list(self.bulgular if tum_bulgular is None else tum_bulgular)
        ilk = self.bulgular[0] if self.bulgular else None
        metin = "%d doğrulama hatası; önce bunları giderin" % len(self.bulgular)
        if ilk is not None:
            metin += ": %s" % ilk.mesaj
        super().__init__(metin)


def kapi(spec, veri_kontrolu=True):
    """
    Kosu oncesi TEK dogrulama kapisi (arayuz, terminal ve programatik yol).

    Hata bulgusu varsa DogrulamaHatasi firlatir; yoksa butun bulgulari (uyari,
    bilgi) dondurur. spec'i DEGISTIRMEZ. Cagiranlar dosya silmeden / kosu
    dizinini temizlemeden ONCE cagirir: gecersiz bir spec eski sonucu silmesin.
    """
    bulgular = tum_kontroller(spec, veri_kontrolu=veri_kontrolu)
    hatalar = [b for b in bulgular if b.seviye == "hata"]
    if hatalar:
        raise DogrulamaHatasi(hatalar, tum_bulgular=bulgular)
    return bulgular


def ozet(bulgular):
    """Bulgulari '2 hata, 1 uyari, 3 bilgi' seklinde ozetler."""
    say = {"hata": 0, "uyari": 0, "bilgi": 0}
    for b in bulgular:
        say[b.seviye] += 1
    return "%d hata, %d uyarı, %d bilgi" % (say["hata"], say["uyari"], say["bilgi"])
