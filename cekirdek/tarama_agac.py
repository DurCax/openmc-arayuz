# -*- coding: utf-8 -*-
"""
================================================================================
 tarama_agac.py  --  Tarama/kritik arama hedefleri: gruplar ve agac modu (G-2)
================================================================================

 docs/GEOMETRI_MODELI.md §3.10, §7 (tarama satiri). tarama.parametre_uygula
 buraya su turlerde devreder:

   grup_donme     hedef = donme grubu adi; deger derece (0 = emici kora bakar)
   grup_daldirma  hedef = daldirma grubu adi; deger %0..%100
   (agac modunda ayrica)
   tambur_donme   takma ad: TEK donme grubu varsa o grup; yoksa HATA
                  "grup secin" (grup_donme)
   cubuk_daldirma kontrol cubugunun daldirmasi; cubuk bir daldirma grubunun
                  uyesiyse HATA (grup degeri tanimdakini ezer, tarama modeli
                  degistirmezdi) -- grup_daldirma kullanilir
   kor_adim       hedef = agac kafesinin kimligi; kafes bir kabin dogrudan
                  ici ise ve kabin kesiti kafesin tam zarfiysa kesit de
                  ayni oranda olceklenir (sablonun kare_kafes davranisi)
   yansitici_kalinlik  hedef = "<kap id>/halkalar/<i>" (kalinlikli halka)

 Sablon modunda grup_* turleri geometri.grup_degeri_yaz ile tamburlu korun
 "tamburlar" grubuna yazar; digerleri tarama.py'deki eski davranistir.
 Butun islevler SAF: girdi degismez, YENI spec doner.
================================================================================
"""

import copy

from cekirdek import geometri
from cekirdek.geometri.sema import cocuklar
from cekirdek.ceviri import _

GRUP_TURLERI = ("grup_donme", "grup_daldirma")
AGAC_TURLERI = ("tambur_donme", "cubuk_daldirma", "kor_adim", "yansitici_kalinlik")
# Olcekleme: kesit kafes zarfina bu goreli payla esitse "tam zarf" sayilir
_ZARF_PAYI = 1.0e-9


def _grup(spec, ad, tur):
    for g in geometri.gruplar(geometri.model(spec)):
        if g.get("ad") == ad:
            if g.get("tur") != tur:
                raise ValueError(_("'%s' grubu bir %s grubu değil") % (ad, tur))
            return g
    raise KeyError(_("tanımsız grup: %s") % ad)


def _daldirma_siniri(deger):
    if not (0.0 <= float(deger) <= 100.0):
        raise ValueError(_("daldırma %%0–%%100 arasında olmalı: %s") % deger)


def uygula(spec, tur, hedef, deger):
    """YENI spec (tur GRUP_TURLERI ya da agac modunda AGAC_TURLERI)."""
    if tur == "grup_donme":
        _grup(spec, hedef, "donme")
        return geometri.grup_degeri_yaz(spec, hedef, float(deger))
    if tur == "grup_daldirma":
        _grup(spec, hedef, "daldirma")
        _daldirma_siniri(deger)
        return geometri.grup_degeri_yaz(spec, hedef, float(deger))
    if tur == "tambur_donme":
        return _tambur_donme(spec, deger)
    if tur == "cubuk_daldirma":
        return _cubuk_daldirma(spec, hedef, deger)
    if tur == "kor_adim":
        return _kafes_adimi(spec, hedef, float(deger))
    if tur == "yansitici_kalinlik":
        return _halka_kalinligi(spec, hedef, float(deger))
    raise ValueError(_("bilinmeyen tarama türü: %s") % tur)


def _tambur_donme(spec, deger):
    donme = [g for g in geometri.gruplar(geometri.model(spec)) if g.get("tur") == "donme"]
    if not donme:
        raise ValueError(_("modelde kontrol tamburu (dönme grubu) yok"))
    if len(donme) > 1:
        raise ValueError(_("modelde %d dönme grubu var (%s); 'grup_donme' ile bir grup seçin")
                         % (len(donme), ", ".join(g["ad"] for g in donme)))
    return geometri.grup_degeri_yaz(spec, donme[0]["ad"], float(deger))


def _cubuk_daldirma(spec, hedef, deger):
    from cekirdek import sema
    for g in geometri.gruplar(geometri.model(spec)):
        if g.get("tur") == "daldirma" and hedef in (g.get("uyeler") or []):
            raise ValueError(_("'%s' çubuğu '%s' daldırma grubunun üyesi; grubun değeri "
                             "çubuğun daldırmasını ezer — 'grup_daldirma' ile tarayın")
                             % (hedef, g["ad"]))
    yeni = copy.deepcopy(spec)
    c = sema.cubuk_bul(yeni, hedef)
    if c is None:
        raise KeyError(_("tanımsız çubuk: %s") % hedef)
    if c.get("tur") != "kontrol":
        raise ValueError(_("'%s' bir kontrol çubuğu değil; daldırma taraması "
                         "yalnızca kontrol çubuklarına uygulanır") % hedef)
    _daldirma_siniri(deger)
    c["daldirma"] = float(deger)
    return yeni


# ----------------------------------------------------------------------------
# agac dugumu bulma
# ----------------------------------------------------------------------------

def _dugumler(agac):
    """(dugum, ata kap | None) -- ham agactaki butun dugumler (kok + parcalar)."""
    cikti = []

    def gez(d, ata):
        if not isinstance(d, dict):
            return
        cikti.append((d, ata))
        for c in cocuklar(d):
            gez(c, d if d.get("tur") == "kap" else None)
    gez(agac.get("kok"), None)
    for p in agac.get("parcalar") or []:
        gez(p.get("dugum"), None)
    return cikti


def _kimlikli(agac, kimlik, tur):
    for d, ata in _dugumler(agac):
        if d.get("tur") == tur and d.get("id") == kimlik:
            return d, ata
    raise KeyError(_("ağaçta '%s' kimlikli %s yok") % (kimlik, tur))


def _kafes_olcusu(kafes):
    """Kafesin tam zarf kesiti (kare: dikdortgen; altigen: prizma) ya da None."""
    from cekirdek.geometri import kesit as _k
    P = float(kafes["adim"])
    if kafes.get("sekil") == "kare":
        nx, ny = kafes["boyut"]
        return {"sekil": "dikdortgen", "boyut": [P * nx, P * ny]}
    return {"sekil": "altigen", "yonelim": kafes.get("yonelim", "y"),
            "apotem": _k.kafes_zarfi_apotemi(int(kafes["halka_sayisi"]), P)}


def _ayni_kesit(a, b):
    if a.get("sekil") != b.get("sekil"):
        return False
    if a["sekil"] == "dikdortgen":
        return all(abs(float(x) - float(y)) <= _ZARF_PAYI * max(1.0, abs(float(y)))
                   for x, y in zip(a["boyut"], b["boyut"]))
    return a.get("yonelim", "y") == b.get("yonelim", "y") and \
        abs(float(a["apotem"]) - float(b["apotem"])) <= _ZARF_PAYI * float(b["apotem"])


def _kafes_adimi(spec, kimlik, adim):
    if adim <= 0:
        raise ValueError(_("kafes adımı sıfırdan büyük olmalı: %s") % adim)
    yeni = copy.deepcopy(spec)
    agac = yeni.get("geometri") or {}
    kafes, _ata = _kimlikli(agac, kimlik, "kafes")
    once = _kafes_olcusu(kafes)
    kafes["adim"] = adim
    for d, _a in _dugumler(agac):
        ic = d.get("ic") if d.get("tur") == "kap" else None
        if isinstance(ic, dict) and ic.get("tur") == "eksenel":
            ic = ic.get("icerik")
        if ic is kafes and _ayni_kesit(d.get("kesit") or {}, once):
            d["kesit"] = _kafes_olcusu(kafes)
    return yeni


def _halka_kalinligi(spec, hedef, kalinlik):
    if kalinlik <= 0:
        raise ValueError(_("halka kalınlığı sıfırdan büyük olmalı: %s") % kalinlik)
    try:
        kimlik, _h, sira = str(hedef).rsplit("/", 2)
        sira = int(sira)
    except ValueError:
        raise ValueError(_("halka hedefi '<kap id>/halkalar/<i>' biçiminde olmalı: %r")
                         % (hedef,)) from None
    yeni = copy.deepcopy(spec)
    kap, _ata = _kimlikli(yeni.get("geometri") or {}, kimlik, "kap")
    halkalar = kap.get("halkalar") or []
    if not 0 <= sira < len(halkalar) or halkalar[sira].get("kalinlik") is None:
        raise ValueError(_("'%s' kabında kalınlıkla tanımlı %d. halka yok") % (kimlik, sira))
    halkalar[sira]["kalinlik"] = kalinlik
    return yeni
