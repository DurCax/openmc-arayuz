# -*- coding: utf-8 -*-
"""
tukenme_spektrum.py -- tukenme zinciri icin spektrum (termal / hizli) tahmini.

Oncelik sirasi (ilk uygulanabilen kullanilir; secilen yol "yontem" ile doner):
  1. "ealf"      kosu dizininde EALF tally'si (vv.aoa.EALF_TALLY) varsa olculen
                 EALF: zincirdeki fisyon verimi enerjilerine (0.0253 eV, 500 keV)
                 letarji olarak hangisi yakinsa (sinir √(0.0253 · 5e5) ≈ 112 eV).
  2. "komsuluk"  yakit (bolunebilir nuklid iceren) malzemeyle AYNI cubukta,
                 cubugun icinde bulundugu demetin dolgusunda ya da ayni plaka
                 elemaninda (sogutucu) moderator varsa termal, yoksa hizli.
                 Yalniz moderatoru yakitla temas etmeyen (yansitici, zirh, havuz)
                 modeller boylece yanlislikla termal sayilmaz.
  3. "genel"     yakit cubuk/plaka icinde degilse (dogrudan hucre, tamburlu kor
                 dolgusu ...): modelin herhangi bir malzemesinde moderator varsa
                 termal (kaba kural; gerekce bunu soyler).
Moderator: H/D iceren malzeme ya da moderator S(α,β)'si (hafif/agir su, grafit,
ZrH ...). Berilyum BILEREK yok (tamburlu korda yalniz yansitici).
"""

import math

from cekirdek.ceviri import _

_MODERATOR_SAB = ("c_H_", "c_D_", "c_Graphite", "c_ortho", "c_para")
_FISIL = ("U233", "U235", "Pu239", "Pu241")
VERIM_ENERJILERI = (0.0253, 5.0e5)          # zincirdeki termal / hizli verim [eV]
EALF_SINIRI_EV = math.sqrt(VERIM_ENERJILERI[0] * VERIM_ENERJILERI[1])


def _moderator_nedeni(m):
    """Malzeme moderatorse kisa neden metni, degilse None."""
    for s in m.get("sab") or []:
        if any(str(s).startswith(o) for o in _MODERATOR_SAB):
            return _("'%s' malzemesinde %s var") % (m["ad"], s)
    for b in m.get("bilesim", []):
        isim = b.get("isim") or ""
        eleman = isim.rstrip("0123456789") if b.get("tur") == "nuklid" else isim
        if eleman in ("H", "D") and float(b.get("miktar") or 0) > 0:
            return _("'%s' malzemesi hidrojen içeriyor") % m["ad"]
    return None


def fisil_mi(m):
    """Malzemede pozitif miktarda fisil nuklid (ya da U/Pu elementi) var mi (Y3 de kullanir)."""
    return _fisil_mi(m)


def _fisil_mi(m):
    for b in m.get("bilesim", []):
        isim = b.get("isim") or ""
        if (isim in _FISIL or (b.get("tur") == "element" and isim in ("U", "Pu"))) \
                and float(b.get("miktar") or 0) > 0:
            return True
    return False


def yakit_komsulari(spec):
    """Yakita komsu malzeme adlari (kume) ya da None (yakit cubuk/plakada degil)."""
    malzemeler = {m["ad"]: m for m in spec.get("malzemeler", [])}
    fisil = {ad for ad, m in malzemeler.items() if _fisil_mi(m)}
    komsu, bulundu = set(), False
    yakitli_cubuklar = set()
    for c in spec.get("cubuklar") or []:
        adlar = {b.get("malzeme") for b in c.get("bolgeler") or []} - {None}
        if adlar & fisil:
            bulundu = True
            yakitli_cubuklar.add(c.get("ad"))
            komsu |= adlar
    for d in spec.get("demetler") or []:
        if set((d.get("anahtar") or {}).values()) & yakitli_cubuklar and d.get("dolgu_disi"):
            komsu.add(d["dolgu_disi"])
    for p in spec.get("plakalar") or []:
        if p.get("et_malzeme") in fisil:
            bulundu = True
            komsu |= {p.get(k) for k in ("et_malzeme", "zarf_malzeme", "sogutucu",
                                          "yan_levha_malzeme")} - {None}
    return komsu if bulundu else None


def _ealf_tahmini(kosu_dizini):
    if not kosu_dizini:
        return None
    from cekirdek.vv import aoa
    ealf = aoa.ealf_oku(kosu_dizini)
    if ealf is None:
        return None
    tur = "termal" if ealf < EALF_SINIRI_EV else "hizli"
    return tur, _("koşudaki EALF = %.3g eV ('%s' tally'si; sınır %.0f eV)") % (
        ealf, aoa.EALF_TALLY, EALF_SINIRI_EV), "ealf"


def tahmin(spec, kosu_dizini=None):
    """("termal"|"hizli", gerekce, yontem) -- bkz. modul basligi."""
    olcum = _ealf_tahmini(kosu_dizini)
    if olcum:
        return olcum
    malzemeler = spec.get("malzemeler", [])
    komsu = yakit_komsulari(spec)
    if komsu is not None:
        for m in malzemeler:
            neden = m["ad"] in komsu and _moderator_nedeni(m)
            if neden:
                return "termal", _("yakıta komşu %s") % neden, "komsuluk"
        uzak = [m["ad"] for m in malzemeler if _moderator_nedeni(m)]
        if uzak:
            return "hizli", _("yakıta komşu malzemelerde moderatör yok (%s yakıtla "
                              "temas etmiyor)") % ", ".join(uzak), "komsuluk"
        return "hizli", _("modelde hidrojen ya da grafit moderatör yok"), "komsuluk"
    for m in malzemeler:
        neden = _moderator_nedeni(m)
        if neden:
            return "termal", _("%s (kaba kural: yakıt komşuluğu çıkarılamadı)") % neden, "genel"
    return "hizli", _("modelde hidrojen ya da grafit moderatör yok"), "genel"
