# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/gezinti.py  --  Agac gezintisi: her dugum, bolgesi, carpani, z araligi
================================================================================

 docs/GEOMETRI_MODELI.md §7 (gez, icerik). Kurulumun (kurulum.py + kap.py)
 izledigi yolu openmc KURMADAN yurur ve her dugum icin bir Ziyaret uretir:

   Ziyaret(yol, dugum, carpan, z_araligi, kesik, ust_yollar,
           bolge, kafeste, tanim_turu, neden)
     carpan     : bu dugumun modeldeki ornek sayisi (kafes konumlari ve
                  yerlesim ornekleriyle carpilir)
     z_araligi  : (z0, z1) ya da None (2B)
     kesik      : dugum (ya da bir atasi) ust bolgesiyle kirpiliyor; alan
                  bilinmez (hacim stokastige duser, §8 UYARI 1/2)
     bolge      : dugumu dolduran bolge (geometri/bolge.py), dugumun yerel
                  cercevesinde; alan bilinmiyorsa bolge.alan None
     kafeste    : bir kafes (kor kafesi ya da demet) konumunun icinde
     tanim_turu : bilesen dugumunde kutuphane turu (cubuk, plaka, demet,
                  tambur, parca); kutuphane iclerinin sanal dugumlerinde de
     neden      : kesik nedeni: "konum" (kafes konumu), "cubuk" (pin hucreye
                  sigmiyor), "bilesen" (bilesen/kap bolgesine sigmiyor),
                  "dis" (kafes disi duzensiz bolge), None

 Kutuphane tanimlari (cubuk bolgeleri, plaka katmanlari, demet kafesi ve
 kilifi, tambur emicisi) SANAL dugumlerle gezilir: {"tur": "malzeme",
 "ad": ...} ve demet icin {"tur": "kafes", "id": "demet:<ad>", ...}.
 Kafesin tam konumlari harf basina TEK ziyarette toplanir (carpan = konum
 sayisi); kesik konumlar tek tek gezilir; gizli konumlar gezilmez.
================================================================================
"""

import math
from collections import namedtuple

from cekirdek import altigen
from cekirdek.geometri import bolge as _b
from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer
from cekirdek.geometri.eksenel import dilimler, katman_icerigi, model_yuksekligi
from cekirdek.geometri.kesik import bolge_kesitleri
from cekirdek.geometri.sema import BOSLUK, bilesen_tanimi, kisaltma_coz
from cekirdek.uygunluk_bellek import Bellek, icerik_anahtari

SQ3 = math.sqrt(3.0)
MAKS_GEZINTI = 40          # kutuphane icleri dahil derinlik siniri (dongu korumasi)

Ziyaret = namedtuple("Ziyaret", "yol dugum carpan z_araligi kesik ust_yollar "
                                "bolge kafeste tanim_turu neden")


def eleman_kesiti(sekil, adim, yonelim="y"):
    """Kafes eleman hucresinin kesiti (0, 0 merkezli)."""
    P = float(adim)
    if sekil == "kare":
        return {"sekil": "dikdortgen", "boyut": [P, P]}
    return {"sekil": "altigen", "apotem": P / 2.0, "yonelim": _k.ters_yonelim(yonelim)}


def kafes_konumlari(kafes):
    """[((r, i), (x, y), harf)] -- harita sirasi, kafes cercevesi."""
    P = float(kafes["adim"])
    harita = kafes.get("harita") or []
    if kafes.get("sekil") == "kare":
        nx, ny = kafes["boyut"]
        return [((r, i), (-P * nx / 2.0 + (i + 0.5) * P, P * ny / 2.0 - (r + 0.5) * P), h)
                for r, satir in enumerate(harita) for i, h in enumerate(satir)]
    kon = altigen.konumlar(int(kafes["halka_sayisi"]), kafes.get("yonelim", "y"))
    return [((r, i), (x * P, y * P), harita[r][i]) for (r, i), (x, y) in sorted(kon.items())
            if r < len(harita) and i < len(harita[r])]


def demet_dugumu(ad, d):
    """Kutuphane demetinin sanal agac dugumu (kafes; kilifliysa kap icinde)."""
    tur = d.get("tur")
    kafes = {"tur": "kafes", "id": "demet:%s" % ad, "sekil": tur,
             "adim": float(d.get("adim") or 0.0), "harita": list(d.get("harita") or []),
             "anahtar": dict(d.get("anahtar") or {}), "dis": d.get("dolgu_disi"),
             "yonelim": d.get("yonelim", "y")}
    if tur == "kare":
        kafes["boyut"] = list(d.get("boyut") or [0, 0])
    else:
        kafes["halka_sayisi"] = int(d.get("halka_sayisi") or (d.get("boyut") or [1])[0])
    kf = d.get("kilif") if tur == "altigen" else None
    if not (isinstance(kf, dict) and kf):
        return kafes
    yon = d.get("yonelim", "y")
    return {"tur": "kap", "id": "demet:%s/kilif" % ad,
            "kesit": {"sekil": "altigen", "apotem": float(kf["ic_duz"]) / 2.0, "yonelim": yon},
            "ic": kafes, "yerlesimler": [],
            "halkalar": [{"kalinlik": float(kf["kalinlik"]),
                          "icerik": {"tur": "malzeme", "ad": kf.get("malzeme")}}],
            "dis": {"tur": "malzeme", "ad": d.get("dolgu_disi")}}


class _Gezgin(object):
    """Agaci kurulumla ayni sirada yuruyen ziyaretci uretici."""

    def __init__(self, m):
        self.m = m
        self.tanim = m.tanimlar
        self.gruplar = m.gruplar
        self.yukseklik = model_yuksekligi(m)
        self._aktif = None

    # ------------------------------------------------------------------
    def coz(self, d):
        return kisaltma_coz(self.tanim, d) if isinstance(d, str) or d is None else d

    @property
    def aktif(self):
        if self._aktif is None:
            from cekirdek.geometri.eksenel import _agac_aktif_aralik
            self._aktif = _agac_aktif_aralik(self.m) or ()
        return self._aktif or None

    def daldirma(self, c):
        g = _yer.grup_degeri(self.gruplar, c.get("ad"), "daldirma")
        return float(c.get("daldirma") or 0.0) if g is None else g

    # ------------------------------------------------------------------
    def kok(self):
        kok = self.m.kok
        h = self.yukseklik
        z = (-h / 2.0, h / 2.0) if h else None
        yield Ziyaret("/kok", kok, 1, z, False, (), None, False, None, None)
        yield from self.kap_ici(kok, None, 1, z, "/kok", ("/kok",), False, False, kok=True)

    def dugum(self, d, bolge, carpan, z, yol, ust, kafeste, kesik, neden=None, derinlik=0):
        """Tek dugum (yuva icerigi): donusum uygulanir, ziyaret uretilir, inilir."""
        if derinlik > MAKS_GEZINTI:
            return
        d = self.coz(d)
        if not isinstance(d, dict):
            return
        don = d.get("donusum") or {}
        if don and d.get("tur") != "malzeme" and bolge is not None:
            bolge = _b.geri_cek(bolge, don.get("donme"), don.get("oteleme"))
        tur = d.get("tur")
        tanim_turu = None
        if tur == "bilesen":
            tanim_turu, _t = bilesen_tanimi(self.tanim, d.get("ad"))
        yield Ziyaret(yol, d, carpan, z, kesik, ust, bolge, kafeste, tanim_turu, neden)
        alt = ust + (yol,)
        a = (bolge, carpan, z, yol, alt, kafeste, kesik, neden, derinlik + 1)
        if tur == "kap":
            yield from self.kap_ici(d, *a)
        elif tur == "kafes":
            yield from self.kafes(d, *a)
        elif tur == "eksenel":
            yield from self.eksenel(d, *a)
        elif tur == "bilesen":
            yield from self.bilesen(d, tanim_turu, *a)

    # ------------------------------------------------------------------
    # kap
    # ------------------------------------------------------------------
    def kap_ici(self, kap, ust_bolge, carpan, z, yol, ust, kafeste, kesik, neden=None,
                derinlik=0, kok=False):
        if kap["kesit"].get("sekil") == "kafes_zarfi":
            yield from self.zarf(kap, carpan, z, yol, ust, kafeste, kesik, derinlik)
            return
        kesitler = bolge_kesitleri(kap)
        if kap["kesit"].get("sekil") == "kure":
            bolgeler = self._kure_bolgeleri(kesitler)
        else:
            sade = [_b.kesit_bolgesi(k) for k in kesitler]
            bolgeler = [sade[0]] + [_b.fark(sade[i + 1], sade[i]) for i in range(len(sade) - 1)]
        if ust_bolge is not None:
            # ust bolgeye sigmayan kap bolgesi ust bolgeyle kirpilir: alan bilinmez
            for i, kes in enumerate(kesitler):
                if not _b.sigar(ust_bolge, kes):
                    bolgeler[i] = _b.kesisim(bolgeler[i], ust_bolge)
                    kesik, neden = True, "bilesen"
        icler = [("ic", kap.get("ic"), kap.get("yerlesimler") or [])]
        icler += [("halkalar/%d" % i, h.get("icerik"), h.get("yerlesimler") or [])
                  for i, h in enumerate(kap.get("halkalar") or [])]
        for (ek, icerik, yerlesimler), bolge in zip(icler, bolgeler):
            yield from self.bolge_ici(kap, bolge, icerik, yerlesimler, carpan, z,
                                      "%s/%s" % (yol, ek), ust, kafeste, kesik, neden, derinlik)
        if not kok and kap.get("dis") is not None:
            dis = _b.fark(ust_bolge, _b.kesit_bolgesi(kesitler[-1])) if ust_bolge else None
            if dis is not None and not _b.sifir_mi(dis.alan, ust_bolge.alan or 1.0):
                yield from self.dugum(kap.get("dis"), dis, carpan, z, yol + "/dis", ust,
                                      kafeste, kesik, neden, derinlik)

    def _kure_bolgeleri(self, kesitler):
        r = [float(k["yaricap"]) for k in kesitler]
        return [_b.kure_bolgesi(r[0])] + [_b.kure_bolgesi(r[i + 1], r[i])
                                          for i in range(len(r) - 1)]

    def bolge_ici(self, kap, bolge, icerik, yerlesimler, carpan, z, yol, ust, kafeste,
                  kesik, neden, derinlik=0):
        """Kap bolgesi: once delik ornekleri, sonra deliklerle oyulmus bolgenin icerigi."""
        delikler = []
        for y in yerlesimler:
            icerik_y = self.coz(y.get("icerik"))
            kes = y.get("kesit") or self._dogal_kesit(icerik_y)
            for i, (x, yy, psi) in enumerate(_yer.ornekler(y, kap, self.tanim, self.gruplar)):
                delik = _b.kesit_bolgesi(kes, (x, yy)) if kes else None
                if delik is not None:
                    delikler.append(delik)
                yield from self._delik(y, i, icerik_y, kes, psi, carpan, z,
                                       "%s/yerlesimler/%s#%d" % (yol, y.get("ad"), i),
                                       ust, kafeste, kesik, neden, derinlik)
        oyulmus = _b.delikli(bolge, delikler)
        if _b.sifir_mi(oyulmus.alan, bolge.alan or 1.0):
            return
        yield from self.dugum(icerik, oyulmus, carpan, z, yol, ust, kafeste, kesik, neden,
                              derinlik)

    def _delik(self, y, i, icerik, kes, psi, carpan, z, yol, ust, kafeste, kesik, neden,
               derinlik=0):
        if kes is None:
            return
        yerel = _b.kesit_bolgesi(kes)
        don = icerik.get("donusum") or {}
        if icerik.get("tur") != "malzeme":
            yerel = _b.geri_cek(yerel, psi or 0.0, don.get("oteleme"))
            icerik = dict(icerik)
            icerik.pop("donusum", None)       # donme psi'de; oteleme yukarida
        yield from self.dugum(icerik, yerel, carpan, z, yol, ust, kafeste, kesik, neden,
                              derinlik)

    def _dogal_kesit(self, icerik):
        tur, t = bilesen_tanimi(self.tanim, (icerik or {}).get("ad"))
        if tur == "tambur" or (tur == "triso" and t.get("sekil", "kompakt") == "kompakt"):
            return {"sekil": "silindir", "yaricap": float(t.get("yaricap") or 0.0)}
        return None

    # ------------------------------------------------------------------
    # kafes
    # ------------------------------------------------------------------
    def kafes(self, d, bolge, carpan, z, yol, ust, kafeste, kesik, neden, derinlik):
        eleman = eleman_kesiti(d.get("sekil"), d["adim"], d.get("yonelim", "y"))
        eb = _b.kesit_bolgesi(eleman)
        anahtar = d.get("anahtar") or {}
        gruplar, kesikler, tam_alan, dis_bilinmez = {}, [], 0.0, False
        for idx, (cx, cy), harf in kafes_konumlari(d):
            durum = "tam" if bolge is None else \
                _b.durum(bolge, _b.sinir_noktalari_iceri(eleman, (cx, cy)))
            if durum == "gizli" or harf == ".":
                continue
            if durum == "tam":
                gruplar[harf] = gruplar.get(harf, 0) + 1
                tam_alan += eb.alan
            else:
                kesikler.append((idx, (cx, cy), harf))
                dis_bilinmez = True
        for harf in sorted(gruplar):
            yield from self.dugum(anahtar.get(harf), eb, carpan * gruplar[harf], z,
                                  "%s/[%s]" % (yol, harf), ust, True, kesik, neden, derinlik)
        for idx, (cx, cy), harf in kesikler:
            kb = _b.kesisim(eb, _b.otele(bolge, cx, cy))
            yield from self.dugum(anahtar.get(harf), kb, carpan, z,
                                  "%s/(%d,%d)" % (yol, idx[0], idx[1]), ust, True, True,
                                  "konum", derinlik)
        yield from self._kafes_disi(d, bolge, tam_alan, dis_bilinmez, carpan, z, yol, ust,
                                    kafeste, kesik, neden, derinlik)

    def _kafes_disi(self, d, bolge, tam_alan, bilinmez, carpan, z, yol, ust, kafeste, kesik,
                    neden, derinlik):
        if d.get("dis") is None or bolge is None:
            return
        alan = None if (bilinmez or bolge.alan is None) else max(bolge.alan - tam_alan, 0.0)
        if _b.sifir_mi(alan, bolge.alan or 1.0):
            return
        icerik = self.coz(d.get("dis"))
        duzensiz = icerik.get("tur") != "malzeme"
        # malzeme disindaki dis dolgu duzensiz bir bolgeyi doldurur: hicbir
        # sekil ona "sigmaz" (alanlar bilinmez, stokastige duser)
        dis = _b.Bolge((lambda x, y, pay: False) if duzensiz else bolge.icinde,
                       None if duzensiz else alan)
        yield from self.dugum(icerik, dis, carpan, z, yol + "/dis", ust, kafeste,
                              kesik or duzensiz, "dis" if duzensiz else neden, derinlik)

    # ------------------------------------------------------------------
    # kafes zarfli kok (R3b): her konum kendi prizmasi, kirpma yok
    # ------------------------------------------------------------------
    def zarf(self, kok, carpan, z, yol, ust, kafeste, kesik, derinlik=0):
        ic = self.coz(kok.get("ic"))
        eks = ic if ic.get("tur") == "eksenel" else None
        kafes = self.coz(eks.get("icerik")) if eks else ic
        eleman = eleman_kesiti("altigen", kafes["adim"], kafes.get("yonelim", "y"))
        eb = _b.kesit_bolgesi(eleman)
        konumlar = kafes_konumlari(kafes)
        # konum hucreleri (R3b): kafes ve yigin dugumleri de ziyaret edilir
        # (bolgesi kokun ic'i; kafes konumlari ayri kok hucreleridir)
        if eks is not None:
            yield Ziyaret(yol + "/ic", eks, carpan, z, kesik, ust, None, kafeste, None, None)
        kyol = yol + "/ic" + ("/icerik" if eks is not None else "")
        yield Ziyaret(kyol, kafes, carpan, z, kesik, ust, None, kafeste, None, None)
        katmanlar = [(z, None)] if eks is None else \
            [((z0, z1), k) for z0, z1, k in dilimler(eks)]
        for j, (zz, k) in enumerate(katmanlar):
            kyol = "%s/ic" % yol if k is None else "%s/ic/katmanlar/%d" % (yol, j)
            if k is not None and k.get("icerik") is not None and not k.get("anahtar"):
                yield from self.dugum(k["icerik"], eb, carpan * len(konumlar), zz, kyol, ust,
                                      kafeste, kesik, None, derinlik)
                continue
            anahtar = dict(kafes.get("anahtar") or {}, **((k or {}).get("anahtar") or {}))
            sayim = {}
            for _idx, _c, harf in konumlar:
                sayim[harf] = sayim.get(harf, 0) + 1
            for harf in sorted(sayim):
                yield from self.dugum(anahtar.get(harf), eb, carpan * sayim[harf], zz,
                                      "%s/[%s]" % (kyol, harf), ust, True, kesik, None,
                                      derinlik)
        halkalar = kok.get("halkalar") or []
        if not halkalar:
            return
        kesitler = bolge_kesitleri(kok)[1:]
        pozlar = [c for _i, c, _h in konumlar]
        hucre_ici = lambda x, y, pay: any(eb.icinde(x - cx, y - cy, -pay) for cx, cy in pozlar)
        ilk = _b.kesit_bolgesi(kesitler[0])
        alan = ilk.alan - len(pozlar) * eb.alan if ilk.alan is not None else None
        bolgeler = [_b.Bolge(lambda x, y, pay: ilk.icinde(x, y, pay) and not hucre_ici(x, y, pay),
                             alan)]
        sade = [_b.kesit_bolgesi(k) for k in kesitler]
        bolgeler += [_b.fark(sade[i + 1], sade[i]) for i in range(len(sade) - 1)]
        for i, (h, bolge) in enumerate(zip(halkalar, bolgeler)):
            yield from self.bolge_ici(kok, bolge, h.get("icerik"), h.get("yerlesimler") or [],
                                      carpan, z, "%s/halkalar/%d" % (yol, i), ust, kafeste,
                                      kesik, None, derinlik)

    # ------------------------------------------------------------------
    # eksenel
    # ------------------------------------------------------------------
    def eksenel(self, d, bolge, carpan, z, yol, ust, kafeste, kesik, neden, derinlik):
        for j, (z0, z1, k) in enumerate(dilimler(d)):
            zz = (z0, z1) if z is None else (max(z0, z[0]), min(z1, z[1]))
            if zz[1] <= zz[0]:
                continue
            yield from self.dugum(katman_icerigi(d, k), bolge, carpan, zz,
                                  "%s/katmanlar/%d" % (yol, j), ust, kafeste, kesik, neden,
                                  derinlik)

    # ------------------------------------------------------------------
    # kutuphane bilesenleri (sanal dugumler)
    # ------------------------------------------------------------------
    def bilesen(self, d, tur, bolge, carpan, z, yol, ust, kafeste, kesik, neden, derinlik):
        ad = d.get("ad")
        _tur, t = bilesen_tanimi(self.tanim, ad)
        a = (carpan, z, ust, kafeste, derinlik)
        if tur == "parca":
            yield from self.dugum(t.get("dugum"), bolge, carpan, z, "%s>%s" % (yol, ad), ust,
                                  kafeste, kesik, neden, derinlik)
        elif tur == "demet":
            yield from self.dugum(demet_dugumu(ad, t), bolge, carpan, z, "%s>%s" % (yol, ad),
                                  ust, kafeste, kesik, neden, derinlik)
        elif tur == "cubuk":
            yield from self.cubuk(ad, t, bolge, yol, kesik, neden, *a)
        elif tur == "plaka":
            yield from self.plaka(ad, t, bolge, yol, kesik, neden, *a)
        elif tur == "tambur":
            yield from self.tambur(ad, t, bolge, yol, kesik, neden, *a)
        elif tur == "triso":
            yield from self.triso(ad, t, bolge, yol, kesik, neden, *a)

    def _sanal(self, ad, alan, carpan, z, yol, ust, kafeste, kesik, neden, tur):
        if ad is None or _b.sifir_mi(alan):
            return []
        if alan is not None and alan < 0:
            alan = None
        return [Ziyaret(yol, {"tur": "malzeme", "ad": ad}, carpan, z, kesik, ust,
                        _b.Bolge(lambda x, y, pay: False, alan), kafeste, tur, neden)]

    def cubuk(self, ad, c, bolge, yol, kesik, neden, carpan, z, ust, kafeste, derinlik):
        """Pin bolgeleri: ust bolgeye sigan bolgenin alani kesindir; sigmayan
        bolgeden disari kesik cubuk (§8 UYARI 2), alan bilinmez."""
        bolgeler = c.get("bolgeler") or []
        sekil = c.get("kesit") or "silindir"
        yon = c.get("kesit_yonelim") or "y"
        alt = ust + ("%s>%s" % (yol, ad),)
        cikti, r_ic, sigdi = [], 0.0, True
        emici_ix = int(c.get("emici_bolge") or 0) if c.get("tur") == "kontrol" else -1
        for i, b in enumerate(bolgeler):
            son = i == len(bolgeler) - 1
            if son:
                dis = _k.pin_bolge_alani(sekil, r_ic)
                alan = None if (bolge is None or bolge.alan is None or not sigdi) \
                    else bolge.alan - dis
            else:
                r = float(b.get("r") or 0.0)
                if sigdi and bolge is not None and \
                        not _b.sigar(bolge, _k.pin_bolge_kesiti(sekil, r, yon)):
                    sigdi, kesik, neden = False, True, "cubuk"
                alan = (_k.pin_bolge_alani(sekil, r) - _k.pin_bolge_alani(sekil, r_ic)) \
                    if sigdi else None
                r_ic = r
            byol = "%s>%s/bolgeler/%d" % (yol, ad, i)
            if i == emici_ix:
                cikti += self._kontrol_bolgesi(c, b, alan, carpan, z, byol, alt, kafeste,
                                               kesik, neden)
            else:
                cikti += self._sanal(b.get("malzeme"), alan, carpan, z, byol, alt, kafeste,
                                     kesik, neden, "cubuk")
        return cikti

    def _kontrol_bolgesi(self, c, b, alan, carpan, z, yol, ust, kafeste, kesik, neden):
        """Kontrol cubugunun emici bolgesi uc duzleminde ikiye bolunur (R8)."""
        h = self.yukseklik
        if not h or z is None:
            return self._sanal(b.get("malzeme"), alan, carpan, z, yol, ust, kafeste, kesik,
                               neden, "cubuk")
        z_alt, z_ust = self.aktif or (-h / 2.0, h / 2.0)
        z_uc = z_ust - self.daldirma(c) / 100.0 * (z_ust - z_alt)
        # Iki hucre de kurulur (bos z araligi = sifir hacim; malzeme modelde
        # "var" sayilir -- uygunluk.geometri_icerigi ile ayni)
        orta = min(max(z_uc, z[0]), z[1])
        return (self._sanal(b.get("malzeme"), alan, carpan, (orta, z[1]), yol + "/emici", ust,
                            kafeste, kesik, neden, "cubuk")
                + self._sanal(c.get("izleyici_malzeme"), alan, carpan, (z[0], orta),
                              yol + "/izleyici", ust, kafeste, kesik, neden, "cubuk"))

    def plaka(self, ad, p, bolge, yol, kesik, neden, carpan, z, ust, kafeste, _derinlik):
        from cekirdek.geometri.sablon import plaka_olcusu
        n = int(p["plaka_sayisi"])
        et, zarf, kanal = (float(p[k]) for k in ("et_kalinlik", "zarf_kalinlik", "kanal_kalinlik"))
        gen = float(p["plaka_genislik"])
        yan = float(p.get("yan_levha_kalinlik") or 0.0)
        top_x, top_y = plaka_olcusu(p)
        sigar = bolge is None or _b.sigar(bolge, {"sekil": "dikdortgen",
                                                  "boyut": [top_x, top_y]})
        if not sigar:
            kesik, neden = True, "bilesen"
        alt = ust + ("%s>%s" % (yol, ad),)
        y = "%s>%s/" % (yol, ad)
        # (malzeme, HUCRE basina alan, hucre sayisi, ek): her plaka/kanal ayri hucre
        katmanlar = [(p["et_malzeme"], et * gen, n, "et"),
                     (p["zarf_malzeme"], zarf * gen, 2 * n, "zarf"),
                     (p["sogutucu"], kanal * gen, n + 1, "kanal")]
        if yan > 0:
            katmanlar.append((p.get("yan_levha_malzeme") or p["zarf_malzeme"], yan * top_x, 2,
                              "yan_levha"))
        cikti = []
        for malzeme, alan, adet, ek in katmanlar:
            cikti += self._sanal(malzeme, alan if sigar else None, carpan * adet, z, y + ek,
                                 alt, kafeste, kesik, neden, "plaka")
        return cikti

    def triso(self, ad, t, bolge, yol, kesik, neden, carpan, z, ust, kafeste, _derinlik):
        """TRISO kompakt/pebble: katman malzemeleri parcacik sayisi x katman hacmi; matris
        kap hacminin kalani (kompaktta bolge alani bilinirse kabin disi da matris).
        Alan = hacim / z uzunlugu (hacim = alan x z uzunlugu x carpan)."""
        from cekirdek import triso as _t
        L = 1.0 if z is None else max(float(z[1]) - float(z[0]), 0.0)
        if L <= 0.0:
            return []
        kap = _t.konteyner(t)
        n = _t.yerlesim_ozeti(t).n
        alt = ust + ("%s>%s" % (yol, ad),)
        cikti = []
        for i, (k, v) in enumerate(_t.katman_hacimleri(t)):
            cikti += self._sanal(k["malzeme"], n * v / L, carpan, z, "%s>%s/%s" % (yol, ad, k.get("ad") or i),
                                 alt, kafeste, kesik, neden, "triso")
        icte = kap.hacim - n * _t.parcacik_hacmi(t)
        if kap.sekil == "pebble":
            r, R = kap.yaricap, float(t["dis_yaricap"])
            matris = icte / L
            cikti += self._sanal(t.get("kabuk_malzeme"), 4.0 / 3.0 * math.pi * (R ** 3 - r ** 3) / L,
                                 carpan, z, "%s>%s/kabuk" % (yol, ad), alt, kafeste, kesik, neden, "triso")
            cikti += self._sanal(t.get("dis_malzeme"), None, carpan, z, "%s>%s/dis" % (yol, ad),
                                 alt, kafeste, True, "bilesen", "triso")
        else:
            disi = None if (bolge is None or bolge.alan is None) else \
                max(bolge.alan - math.pi * kap.yaricap ** 2, 0.0)
            matris = None if disi is None else icte / L + disi
        cikti += self._sanal(t.get("matris_malzeme"), matris, carpan, z, "%s>%s/matris" % (yol, ad),
                             alt, kafeste, kesik, neden, "triso")
        return cikti

    def tambur(self, ad, t, bolge, yol, kesik, neden, carpan, z, ust, kafeste, _derinlik):
        R = float(t["yaricap"])
        r_ic = float(t.get("emici_ic_yaricap") or 0.0)
        aci = min(float(t.get("emici_aci") or 120.0), 360.0)
        disk = {"sekil": "silindir", "yaricap": R}
        sigar = bolge is None or _b.sigar(bolge, disk)
        if not sigar:
            kesik, neden = True, "bilesen"
        emici = aci / 360.0 * math.pi * (R * R - r_ic * r_ic) if sigar else None
        govde = None if (not sigar or bolge is None or bolge.alan is None) \
            else bolge.alan - emici
        alt = ust + ("%s>%s" % (yol, ad),)
        return (self._sanal(t.get("emici_malzeme"), emici, carpan, z, "%s>%s/emici" % (yol, ad),
                            alt, kafeste, kesik, neden, "tambur")
                + self._sanal(t.get("govde_malzeme"), govde, carpan, z,
                              "%s>%s/govde" % (yol, ad), alt, kafeste, kesik, neden, "tambur"))


def gez(m):
    """GeometriModeli -> Ziyaret ureteci (kok once; kurulum sirasi)."""
    return _Gezgin(m).kok()


_ZIYARETLER = Bellek("gezinti_ziyaretleri", sinir=4)


def ziyaretler(m):
    """gez(m)'in butun ziyaretleri (demet), model icerigine gore bellekli (H1b):
    tusun uygunluk gezintisi ile dogrulamanin agac denetimi AYNI gezintiyi paylasir.
    Ziyaretlerin dugum sozlukleri salt okunur kullanilmali."""
    anahtar = icerik_anahtari([m.kok, m.parcalar, m.gruplar, m.tanimlar, m.sablon,
                               m.kaynaklar, m.agac])
    return _ZIYARETLER.al(anahtar, lambda: tuple(gez(m)))


# ----------------------------------------------------------------------------
# icerik: uygunluk.geometri_icerigi ile ayni bicim (§7)
# ----------------------------------------------------------------------------

def icerik(m):
    """
    Modelde GERCEKTEN yer alan adlar: {"malzeme", "cubuk", "plaka", "demet",
    "kafesteki_cubuk", "tambur", "parca"} (kumeler). Gizli konumlar ve sifir
    alanli bolgeler sayilmaz; malzemeler yalniz spec'te tanimliysa (bosluk
    haric) eklenir -- uygunluk.geometri_icerigi ile ayni kural.
    """
    ic = {k: set() for k in ("malzeme", "cubuk", "plaka", "demet", "kafesteki_cubuk",
                             "tambur", "parca")}
    tanimli = m.tanimlar.get("malzeme") or {}
    for z in ziyaretler(m):
        d = z.dugum
        if d.get("tur") == "malzeme":
            ad = d.get("ad")
            if ad and ad != BOSLUK and ad in tanimli:
                ic["malzeme"].add(ad)
        elif d.get("tur") == "bilesen" and z.tanim_turu in ic:
            ic[z.tanim_turu].add(d.get("ad"))
            if z.tanim_turu == "cubuk" and z.kafeste:
                ic["kafesteki_cubuk"].add(d.get("ad"))
    return ic
