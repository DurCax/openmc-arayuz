# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/denetim.py  --  Agacin YAPISAL denetimi (kurulumun on kosulu)
================================================================================

 docs/GEOMETRI_MODELI.md §8 HATA 1-6, 8, 11 ve yapisal UYARI/BILGI'ler:
 bilinmeyen tur, eksik/yanlis turde alan, tanimsiz/belirsiz basvuru, dongu,
 derinlik, kafes haritasi, kap halkalari, eksenel yigin, gruplar, sinir.
 Geometrik sigma/ortusme (delik tasmasi, kesik konum) ve fizik kurallari
 G-2'nin dogrula/agac.py'sindedir; burada ayni konu iki kez bildirilmez.

 Bulgu yeri: "geometri:<yol>" (yol JSON-isaretcisi bicimi, §2).
================================================================================
"""

import math
from numbers import Real

from cekirdek import altigen
from cekirdek.ceviri import _
from cekirdek.geometri import kesit as _k
from cekirdek.geometri.sema import (
    BOSLUK, DUGUM_TURLERI, SINIR_TURLERI, YERLESIM_MODLARI, GRUP_TURLERI,
    MAKS_DERINLIK, UYARI_DERINLIK, UYARI_DELIK_SAYISI, tanimlar, ad_bolumleri,
    yuva_adi)

DIKDORTGEN_YUZLERI = ("-x", "+x", "-y", "+y")


def _bulgu(seviye, yol, mesaj, oneri=None):
    from cekirdek.dogrula._ortak import Bulgu
    return Bulgu(seviye, "geometri:%s" % yol, mesaj, oneri)


def _sayi(x):
    return isinstance(x, Real) and not isinstance(x, bool) and math.isfinite(x)


class _Denetci(object):
    def __init__(self, spec, agac):
        self.spec = spec
        self.agac = agac
        self.tanim = tanimlar(spec, agac)
        self.bulgular = []
        self.parca_yigini = []
        self.idler = {}
        self.yerlesimler = {}
        self.denetlenen_parcalar = set()

    # --- bulgu ---
    def hata(self, yol, mesaj, oneri=None):
        self.bulgular.append(_bulgu("hata", yol, mesaj, oneri))

    def uyari(self, yol, mesaj, oneri=None):
        self.bulgular.append(_bulgu("uyari", yol, mesaj, oneri))

    def bilgi(self, yol, mesaj):
        self.bulgular.append(_bulgu("bilgi", yol, mesaj))

    # --- yuva ---
    def yuva(self, d, yol, derinlik):
        if isinstance(d, str):
            self.kisaltma(d, yol)
            if ad_bolumleri(self.tanim, d)[:1] == ["parca"]:
                self.d_bilesen({"tur": "bilesen", "ad": d}, yol, derinlik)
            return
        if not isinstance(d, dict):
            self.hata(yol, _("Yuvada düğüm ya da ad bekleniyordu (%r).") % (d,))
            return
        self.dugum(d, yol, derinlik)

    def kisaltma(self, ad, yol):
        if ad == BOSLUK or ad in self.tanim["malzeme"] or ad_bolumleri(self.tanim, ad):
            return
        self.hata(yol, _("Tanımsız ad: '%s' (çubuk, plaka, demet, tambur, parça ya da "
                         "malzeme değil).") % ad)

    def dugum(self, d, yol, derinlik):
        tur = d.get("tur")
        if tur not in DUGUM_TURLERI:
            self.hata(yol, _("Bilinmeyen düğüm türü: %r.") % (tur,))
            return
        if derinlik > MAKS_DERINLIK:
            self.hata(yol, _("İç içe derinlik %d düzeyi aşıyor.") % MAKS_DERINLIK)
            return
        if derinlik == UYARI_DERINLIK + 1:
            self.uyari(yol, _("İç içe derinlik %d düzeyden fazla; izleme yavaşlar.")
                       % UYARI_DERINLIK)
        kimlik = d.get("id")
        if kimlik is not None:
            if not isinstance(kimlik, str) or not kimlik:
                self.hata(yol, _("Düğüm kimliği (id) boş olmayan bir dize olmalı."))
            elif kimlik in self.idler and self.idler[kimlik] != yol:
                self.hata(yol, _("Kimlik '%s' ağaçta iki kez kullanılıyor (%s).")
                          % (kimlik, self.idler[kimlik]))
            else:
                self.idler[kimlik] = yol
        self.donusum(d, yol)
        getattr(self, "d_" + tur)(d, yol, derinlik)

    def donusum(self, d, yol):
        don = d.get("donusum")
        if don is None:
            return
        if d.get("tur") == "malzeme":
            self.hata(yol, _("Malzeme düğümüne dönüşüm uygulanamaz: OpenMC malzeme "
                             "dolgulu hücreyi döndürmez."))
            return
        if not isinstance(don, dict):
            self.hata(yol, _("Dönüşüm bir nesne olmalı: {\"donme\", \"oteleme\"}."))
            return
        if "donme" in don and not _sayi(don["donme"]):
            self.hata(yol, _("Dönüşüm: 'donme' sayı olmalı (derece)."))
        ot = don.get("oteleme")
        if ot is not None and not (isinstance(ot, (list, tuple)) and len(ot) == 2
                                   and all(_sayi(v) for v in ot)):
            self.hata(yol, _("Dönüşüm: 'oteleme' [x, y] olmalı (cm)."))

    # --- turler ---
    def d_malzeme(self, d, yol, _derinlik):
        ad = d.get("ad")
        if ad != BOSLUK and ad not in self.tanim["malzeme"]:
            self.hata(yol, _("Tanımsız malzeme: '%s'.") % (ad,))

    def d_referans(self, d, yol, _derinlik):
        self.hata(yol, _("Çözülmemiş referans '%s': kaydedilmeden önce parçaya "
                         "çevrilmeliydi.") % (d.get("id"),))

    def d_bilesen(self, d, yol, derinlik):
        ad = d.get("ad")
        bolumler = ad_bolumleri(self.tanim, ad)
        if not bolumler:
            self.hata(yol, _("Tanımsız bileşen: '%s'.") % (ad,))
            return
        if len(bolumler) > 1:
            self.hata(yol, _("Belirsiz ad '%s': %s bölümlerinin ikisinde de var.")
                      % (ad, ", ".join(bolumler)),
                      _("Birini yeniden adlandırın."))
            return
        if bolumler[0] != "parca":
            return
        if ad in self.parca_yigini:
            self.hata(yol, _("Döngü: '%s' parçası kendini içeriyor (%s).")
                      % (ad, " → ".join(self.parca_yigini + [ad])))
            return
        self.parca_yigini.append(ad)
        self.yuva(self.tanim["parca"][ad].get("dugum"), "parcalar/%s/dugum" % ad,
                  derinlik + 1)
        self.parca_yigini.pop()
        self.denetlenen_parcalar.add(ad)

    def d_eksenel(self, d, yol, derinlik):
        if d.get("icerik") is None:
            self.hata(yol, _("Eksenel yığında varsayılan 'icerik' yok."))
        else:
            self.yuva(d["icerik"], yol + "/icerik", derinlik + 1)
        katmanlar = d.get("katmanlar")
        if not isinstance(katmanlar, list) or not katmanlar:
            self.hata(yol, _("Eksenel yığında en az bir katman olmalı."))
            return
        varsayilan = d.get("icerik")
        for i, k in enumerate(katmanlar):
            ky = "%s/katmanlar/%d" % (yol, i)
            if not isinstance(k, dict) or not _sayi(k.get("yukseklik")):
                self.hata(ky, _("Katman yüksekliği sayı olmalı (cm)."))
                continue
            if k["yukseklik"] <= 0:
                self.bilgi(ky, _("'%s' katmanı 0 cm; atlanır.") % (k.get("ad") or i + 1))
            if k.get("icerik") is not None:
                self.yuva(k["icerik"], ky + "/icerik", derinlik + 1)
            if k.get("anahtar"):
                if not (isinstance(varsayilan, dict) and varsayilan.get("tur") == "kafes"):
                    self.hata(ky, _("Katmana özgü 'anahtar' yalnız varsayılan içerik bir "
                                    "kafes olduğunda geçerlidir."))
                for h, v in sorted(k["anahtar"].items()):
                    self.yuva(v, "%s/anahtar/%s" % (ky, h), derinlik + 2)

    def d_kafes(self, d, yol, derinlik, dis_zorunlu=True):
        sekil = d.get("sekil")
        if sekil not in ("kare", "altigen"):
            self.hata(yol, _("Kafes şekli 'kare' ya da 'altigen' olmalı (%r).") % (sekil,))
            return
        if not _sayi(d.get("adim")) or d["adim"] <= 0:
            self.hata(yol, _("Kafes adımı sıfırdan büyük bir sayı olmalı."))
        harita = d.get("harita")
        if not isinstance(harita, list) or not all(isinstance(s, str) for s in harita):
            self.hata(yol, _("Kafes haritası dize listesi olmalı."))
            return
        if sekil == "kare":
            self._kare_harita(d, harita, yol)
        else:
            self._altigen_harita(d, harita, yol)
        anahtar = d.get("anahtar") or {}
        for harf in sorted({h for s in harita for h in s} - {"."}):
            if harf not in anahtar:
                self.hata(yol, _("Haritada tanımsız harf: '%s'.") % harf)
        for harf, v in sorted(anahtar.items()):
            self.yuva(v, "%s/anahtar/%s" % (yol, harf), derinlik + 1)
        if d.get("dis") is None:
            if dis_zorunlu:
                self.hata(yol, _("Kafesin 'dis' yuvası zorunlu (kafesin dışı ve '.' "
                                 "konumları buraya düşer)."))
        else:
            self.yuva(d["dis"], yol + "/dis", derinlik + 1)

    def _kare_harita(self, d, harita, yol):
        boyut = d.get("boyut")
        if not (isinstance(boyut, (list, tuple)) and len(boyut) == 2
                and all(isinstance(n, int) and n >= 1 for n in boyut)):
            self.hata(yol, _("Kare kafes 'boyut' [nx, ny] pozitif tam sayılar olmalı."))
            return
        nx, ny = boyut
        if len(harita) != ny:
            self.hata(yol, _("Harita %d satır; boyut %d bekliyor.") % (len(harita), ny))
        for i, s in enumerate(harita):
            if len(s) != nx:
                self.hata(yol, _("Harita satırı %d: %d karakter, %d bekleniyor.")
                          % (i + 1, len(s), nx))

    def _altigen_harita(self, d, harita, yol):
        n = d.get("halka_sayisi")
        if not isinstance(n, int) or n < 1:
            self.hata(yol, _("Altıgen kafes 'halka_sayisi' pozitif tam sayı olmalı."))
            return
        if d.get("yonelim", "y") not in _k.YONELIMLER:
            self.hata(yol, _("Altıgen kafes yönelimi 'x' ya da 'y' olmalı."))
        beklenen = altigen.halka_uzunluklari(n)
        if [len(s) for s in harita] != beklenen:
            self.hata(yol, _("Altıgen harita %d halka bekliyor (öğe sayıları %s), "
                             "haritada %s.") % (n, beklenen, [len(s) for s in harita]))

    def d_kap(self, d, yol, derinlik, kok=False):
        kes = d.get("kesit")
        self.kesit(kes, yol + "/kesit", kok=kok)
        ic = d.get("ic")
        zarf = isinstance(kes, dict) and kes.get("sekil") == "kafes_zarfi"
        if ic is None:
            self.hata(yol, _("Kabın 'ic' yuvası zorunlu."))
        elif zarf:
            self._zarf_ici(ic, yol + "/ic", derinlik + 1)
        else:
            self.yuva(ic, yol + "/ic", derinlik + 1)
        self.yerlesim_listesi(d.get("yerlesimler"), yol + "/yerlesimler", derinlik, d)
        onceki = kes if isinstance(kes, dict) else None
        for i, h in enumerate(d.get("halkalar") or []):
            onceki = self.halka(h, onceki, "%s/halkalar/%d" % (yol, i), derinlik, d, zarf and i == 0)
        if kok:
            if d.get("dis") is not None:
                self.hata(yol, _("Kök kapta 'dis' olamaz (modelin dışı yoktur)."))
        else:
            for alan in ("yukseklik", "sinir"):
                if d.get(alan) is not None:
                    self.hata(yol, _("'%s' yalnız kök kapta bulunur.") % alan)
            if d.get("dis") is None:
                self.hata(yol, _("Kök olmayan kapta 'dis' yuvası zorunlu (kabın dışı ile "
                                 "yuvanın sınırı arası)."))
            else:
                self.yuva(d["dis"], yol + "/dis", derinlik + 1)

    def _zarf_ici(self, ic, yol, derinlik):
        kafes = ic.get("icerik") if isinstance(ic, dict) and ic.get("tur") == "eksenel" else ic
        if not (isinstance(kafes, dict) and kafes.get("tur") == "kafes"
                and kafes.get("sekil") == "altigen"):
            self.hata(yol, _("'kafes_zarfi' kesiti yalnız içi altıgen kafes olan kök "
                             "kapta kullanılır."))
            self.yuva(ic, yol, derinlik)
            return
        if ic is kafes:
            self.dugum_zarf(kafes, yol, derinlik)
            return
        # eksenel yigin: varsayilan icerik zarf kafesi (R3b: konum x katman)
        self.donusum(ic, yol)
        self.dugum_zarf(kafes, yol + "/icerik", derinlik + 1)
        for i, k in enumerate(ic.get("katmanlar") or []):
            ky = "%s/katmanlar/%d" % (yol, i)
            if not isinstance(k, dict) or not _sayi(k.get("yukseklik")):
                self.hata(ky, _("Katman yüksekliği sayı olmalı (cm)."))
                continue
            if k.get("icerik") is not None:
                self.yuva(k["icerik"], ky + "/icerik", derinlik + 1)
            for h, v in sorted((k.get("anahtar") or {}).items()):
                self.yuva(v, "%s/anahtar/%s" % (ky, h), derinlik + 2)

    def dugum_zarf(self, kafes, yol, derinlik):
        if kafes.get("id"):
            self.idler.setdefault(kafes["id"], yol)
        self.d_kafes(kafes, yol, derinlik, dis_zorunlu=False)
        if kafes.get("dis") is not None:
            self.bilgi(yol, _("Kafes zarflı kökte 'kafes.dis' kullanılmaz (R3b)."))

    def halka(self, h, onceki, yol, derinlik, kap, zarf_halkasi):
        if not isinstance(h, dict):
            self.hata(yol, _("Halka bir nesne olmalı."))
            return onceki
        var_k, var_d = h.get("kalinlik") is not None, h.get("dis") is not None
        yeni = None
        if var_k == var_d:
            self.hata(yol, _("Halkada 'kalinlik' ya da 'dis' alanlarından tam olarak biri "
                             "verilmeli."))
        elif var_k:
            if not _sayi(h["kalinlik"]) or h["kalinlik"] <= 0:
                self.hata(yol, _("Halka kalınlığı sıfırdan büyük olmalı."))
            elif zarf_halkasi or (onceki or {}).get("sekil") == "kafes_zarfi":
                self.hata(yol, _("'kafes_zarfi' üzerinde 'kalinlik' kullanılamaz; 'dis' "
                                 "kesiti verin."))
            elif onceki is not None and onceki.get("sekil") in ("dikdortgen", "silindir",
                                                                  "altigen", "kure"):
                yeni = _k.buyut(onceki, h["kalinlik"])
        else:
            self.kesit(h["dis"], yol + "/dis")
            yeni = h["dis"] if isinstance(h["dis"], dict) else None
            if (yeni is not None and onceki is not None and yeni.get("sekil") in _k.SEKILLER[:4]
                    and onceki.get("sekil") in _k.SEKILLER[:4] and self._kesit_gecerli(yeni)
                    and self._kesit_gecerli(onceki) and not _k.kapsar(yeni, onceki)):
                self.hata(yol, _("Halkanın dış kesiti bir önceki sınırı kapsamıyor."))
        if h.get("icerik") is None:
            self.hata(yol, _("Halkanın 'icerik' yuvası zorunlu."))
        else:
            self.yuva(h["icerik"], yol + "/icerik", derinlik + 1)
        self.yerlesim_listesi(h.get("yerlesimler"), yol + "/yerlesimler", derinlik, kap)
        return yeni if yeni is not None else onceki

    def _kesit_gecerli(self, kes):
        try:
            _k.kutu(kes)
            return True
        except (KeyError, TypeError, ValueError):
            return False

    def kesit(self, kes, yol, kok=False):
        if not isinstance(kes, dict):
            self.hata(yol, _("Kesit bir nesne olmalı ({\"sekil\": ...})."))
            return
        s = kes.get("sekil")
        if s not in _k.SEKILLER:
            self.hata(yol, _("Bilinmeyen kesit şekli: %r.") % (s,))
            return
        if s in ("kure", "kafes_zarfi") and not kok and not yol.endswith("/dis"):
            self.hata(yol, _("'%s' kesiti yalnız kök kapta kullanılır.") % s)
        alanlar = {"dikdortgen": ("boyut",), "silindir": ("yaricap",),
                   "kure": ("yaricap",), "altigen": ("apotem",), "kafes_zarfi": ()}[s]
        for a in alanlar:
            deger = kes.get(a)
            degerler = deger if a == "boyut" else [deger]
            if (not isinstance(degerler, (list, tuple)) or len(degerler) != (2 if a == "boyut" else 1)
                    or not all(_sayi(v) and v > 0 for v in degerler)):
                self.hata(yol, _("Kesit alanı '%s' pozitif sayı olmalı.") % a)
        if s == "altigen" and kes.get("yonelim", "y") not in _k.YONELIMLER:
            self.hata(yol, _("Altıgen kesit yönelimi 'x' ya da 'y' olmalı."))

    # --- yerlesim ---
    def yerlesim_listesi(self, liste, yol, derinlik, kap):
        if liste is None:
            return
        if not isinstance(liste, list):
            self.hata(yol, _("Yerleşimler bir liste olmalı."))
            return
        for i, y in enumerate(liste):
            self.yerlesim(y, "%s/%d" % (yol, i), derinlik, kap)

    def yerlesim(self, y, yol, derinlik, kap):
        if not isinstance(y, dict):
            self.hata(yol, _("Yerleşim bir nesne olmalı."))
            return
        ad = y.get("ad")
        if not isinstance(ad, str) or not ad:
            self.hata(yol, _("Yerleşimin adı ('ad') zorunlu."))
        elif ad in self.yerlesimler:
            self.hata(yol, _("Yerleşim adı '%s' iki kez kullanılıyor.") % ad)
        else:
            self.yerlesimler[ad] = yol
        mod = y.get("mod")
        if mod not in YERLESIM_MODLARI:
            self.hata(yol, _("Yerleşim modu %s olmalı (%r).")
                      % ("|".join(YERLESIM_MODLARI), mod))
        elif mod == "halka":
            if not isinstance(y.get("sayi"), int) or y["sayi"] < 1:
                self.hata(yol, _("Halka yerleşiminde 'sayi' pozitif tam sayı olmalı."))
            if not _sayi(y.get("merkez_yaricap")) or y["merkez_yaricap"] < 0:
                self.hata(yol, _("Halka yerleşiminde 'merkez_yaricap' sayı olmalı."))
        elif mod == "liste":
            kon = y.get("konumlar")
            if not isinstance(kon, list) or not kon or not all(
                    isinstance(p, (list, tuple)) and len(p) == 2 and all(_sayi(v) for v in p)
                    for p in kon):
                self.hata(yol, _("Liste yerleşiminde 'konumlar' [[x, y], ...] olmalı."))
            elif len(kon) > UYARI_DELIK_SAYISI:
                self.uyari(yol, _("Bir bölgede %d'den fazla delik; hücre arama yavaşlar.")
                           % UYARI_DELIK_SAYISI)
        else:
            self._kafes_konumu(y, yol, kap)
        icerik = y.get("icerik")
        if icerik is None:
            self.hata(yol, _("Yerleşimin 'icerik' yuvası zorunlu."))
        else:
            self.yuva(icerik, yol + "/icerik", derinlik + 1)
        if y.get("kesit") is None:
            if not self._dogal_kesitli(icerik):
                self.hata(yol, _("Delik kesiti ('kesit') zorunlu: yalnız tambur içeriğinin "
                                 "doğal kesiti vardır."))
        else:
            self.kesit(y["kesit"], yol + "/kesit")
        self._bakis(y, yol)

    def _dogal_kesitli(self, icerik):
        if isinstance(icerik, str):
            ad = icerik
        elif isinstance(icerik, dict) and icerik.get("tur") == "bilesen":
            ad = icerik.get("ad")
        else:
            return False
        return ad_bolumleri(self.tanim, ad)[:1] == ["tambur"]

    def _kafes_konumu(self, y, yol, kap):
        adaylar = [kap.get("ic")] + [h.get("icerik") for h in kap.get("halkalar") or []
                                     if isinstance(h, dict)]
        kafes = next((a for a in adaylar if isinstance(a, dict) and a.get("tur") == "kafes"
                      and a.get("id") == y.get("kafes")), None)
        if kafes is None:
            self.hata(yol, _("'kafes_konumu' yerleşimi: '%s' kimlikli kafes aynı kabın içi ya "
                             "da bir halkasının içeriği değil.") % (y.get("kafes"),))
            return
        if kafes.get("donusum"):
            self.hata(yol, _("'kafes_konumu' yerleşiminin kafesi dönüşümsüz olmalı."))
        harf = y.get("harf")
        if not isinstance(harf, str) or len(harf) != 1:
            self.hata(yol, _("'kafes_konumu' yerleşiminde tek karakterlik 'harf' zorunlu."))

    def _bakis(self, y, yol):
        b = y.get("bakis")
        if b is None:
            return
        if not isinstance(b, dict) or b.get("tur") not in ("merkez", "sabit"):
            self.hata(yol, _("Bakış türü 'merkez' ya da 'sabit' olmalı."))
            return
        if b["tur"] == "sabit" and not _sayi(b.get("aci")):
            self.hata(yol, _("Sabit bakışta 'aci' sayı olmalı (derece)."))
        if b["tur"] == "merkez":
            m = b.get("merkez", [0.0, 0.0])
            if not (isinstance(m, (list, tuple)) and len(m) == 2 and all(_sayi(v) for v in m)):
                self.hata(yol, _("Merkez bakışında 'merkez' [x, y] olmalı."))
        if y.get("donme_ofset") is not None and not _sayi(y["donme_ofset"]):
            self.hata(yol, _("'donme_ofset' sayı olmalı (derece)."))

    # --- kok ---
    def kok(self, kok):
        if not isinstance(kok, dict) or kok.get("tur") != "kap":
            self.hata("kok", _("Kök düğüm bir 'kap' olmalı."))
            if isinstance(kok, dict):
                self.yuva(kok, "kok", 1)
            return
        self.donusum(kok, "kok")
        if kok.get("id"):
            self.idler[kok["id"]] = "kok"
        self.d_kap(kok, "kok", 1, kok=True)
        self.sinir(kok)
        self.yukseklik(kok)

    def sinir(self, kok):
        s = kok.get("sinir") or {}
        if not isinstance(s, dict):
            self.hata("kok/sinir", _("Sınır bir nesne olmalı."))
            return
        for alan in ("yan", "alt", "ust"):
            if s.get(alan) is not None and s[alan] not in SINIR_TURLERI:
                self.hata("kok/sinir", _("Bilinmeyen sınır koşulu: %s = %r.") % (alan, s[alan]))
        yuzler = s.get("yuzler")
        if yuzler is None:
            return
        dis = self._en_dis_kesit(kok)
        sekil = (dis or {}).get("sekil")
        if sekil == "dikdortgen":
            self._dikdortgen_yuzleri(yuzler, s.get("yan") or "reflective")
        elif sekil in ("altigen", "kafes_zarfi"):
            self._altigen_yuzleri(yuzler)
        else:
            self.hata("kok/sinir", _("Yüz başına sınır koşulu yalnız dikdörtgen ya da altıgen "
                                     "dış sınırda verilebilir."))

    def _en_dis_kesit(self, kok):
        dis = kok.get("kesit")
        for h in kok.get("halkalar") or []:
            if isinstance(h, dict) and h.get("dis") is not None:
                dis = h["dis"]
        return dis if isinstance(dis, dict) else None

    def _dikdortgen_yuzleri(self, yuzler, yan):
        # kurulum eksik yuze 'yan'i yazar (kurulum._dikdortgen_yuzleri): esler
        # ETKIN sinir kosuluyla denetlenir
        if not isinstance(yuzler, dict) or set(yuzler) - set(DIKDORTGEN_YUZLERI):
            self.hata("kok/sinir", _("Dikdörtgen sınırda 'yuzler' anahtarları %s olmalı.")
                      % ", ".join(DIKDORTGEN_YUZLERI))
            return
        for y, v in yuzler.items():
            if v not in SINIR_TURLERI:
                self.hata("kok/sinir", _("Bilinmeyen sınır koşulu: %s = %r.") % (y, v))
        for a, b in (("-x", "+x"), ("-y", "+y")):
            if (yuzler.get(a, yan) == "periodic") != (yuzler.get(b, yan) == "periodic"):
                self.hata("kok/sinir", _("Periyodik sınır karşılıklı iki yüzde birlikte "
                                         "verilmeli (%s / %s).") % (a, b))

    def _altigen_yuzleri(self, yuzler):
        if not isinstance(yuzler, list) or len(yuzler) != 6:
            self.hata("kok/sinir", _("Altıgen sınırda 'yuzler' 6 öğeli bir liste olmalı "
                                     "(yüz normali açısı artan sırada)."))
            return
        for i, v in enumerate(yuzler):
            if v not in SINIR_TURLERI:
                self.hata("kok/sinir", _("Bilinmeyen sınır koşulu: yüz %d = %r.") % (i + 1, v))
        for i in range(3):
            if (yuzler[i] == "periodic") != (yuzler[i + 3] == "periodic"):
                self.hata("kok/sinir", _("Periyodik sınır karşılıklı iki yüzde birlikte "
                                         "verilmeli (yüz %d / %d).") % (i + 1, i + 4))

    def yukseklik(self, kok):
        h = kok.get("yukseklik")
        if h is not None and (not _sayi(h) or h <= 0):
            self.hata("kok", _("Kök yüksekliği pozitif sayı ya da boş (2B) olmalı."))
            return
        ic = kok.get("ic")
        if isinstance(ic, dict) and ic.get("tur") == "eksenel":
            toplam = sum(float(k.get("yukseklik") or 0.0) for k in ic.get("katmanlar") or []
                         if isinstance(k, dict) and _sayi(k.get("yukseklik"))
                         and k["yukseklik"] > 0)
            if h is not None and abs(float(h) - toplam) > 1e-9:
                self.hata("kok", _("Kökte hem 'yukseklik' (%g cm) hem farklı toplamlı eksenel "
                                   "yığın (%g cm) var; yükseklik boş bırakılmalı.")
                          % (h, toplam))

    # --- gruplar ---
    def gruplar(self, gruplar):
        if gruplar is None:
            return
        if not isinstance(gruplar, list):
            self.hata("gruplar", _("Gruplar bir liste olmalı."))
            return
        uye_grubu = {}
        kontrol = {c.get("ad") for c in self.tanim["cubuk"].values() if c.get("tur") == "kontrol"}
        for i, g in enumerate(gruplar):
            yol = "gruplar/%d" % i
            if not isinstance(g, dict) or g.get("tur") not in GRUP_TURLERI:
                self.hata(yol, _("Grup türü 'donme' ya da 'daldirma' olmalı."))
                continue
            if not _sayi(g.get("deger")):
                self.hata(yol, _("Grup değeri sayı olmalı."))
            uyeler = g.get("uyeler") or []
            if not uyeler:
                self.uyari(yol, _("'%s' grubu boş.") % g.get("ad"))
            elif len(uyeler) == 1:
                self.bilgi(yol, _("'%s' grubunun tek üyesi var.") % g.get("ad"))
            for u in uyeler:
                gecerli = u in self.yerlesimler if g["tur"] == "donme" else u in kontrol
                if not gecerli:
                    self.hata(yol, _("'%s' grubunun üyesi '%s' tanımsız ya da türü uyuşmuyor "
                                     "(%s).") % (g.get("ad"), u,
                                                 _("yerleşim adı") if g["tur"] == "donme"
                                                 else _("kontrol çubuğu")))
                anahtar = (g["tur"], u)
                if anahtar in uye_grubu:
                    self.hata(yol, _("'%s' aynı türden iki grupta (%s, %s).")
                              % (u, uye_grubu[anahtar], g.get("ad")))
                uye_grubu[anahtar] = g.get("ad")


def yapisal_denetim_agac(spec, agac):
    """Normalize edilmis ya da edilmemis bir agacin yapisal bulgulari."""
    d = _Denetci(spec, agac)
    if not isinstance(agac, dict):
        return [_bulgu("hata", "", _("Geometri bölümü bir nesne olmalı."))]
    for i, p in enumerate(agac.get("parcalar") or []):
        if not isinstance(p, dict) or not isinstance(p.get("ad"), str) or "dugum" not in p:
            d.hata("parcalar/%d" % i, _("Parça {\"ad\", \"dugum\"} olmalı."))
    d.kok(agac.get("kok"))
    for p in agac.get("parcalar") or []:
        if isinstance(p, dict) and p.get("ad") not in d.denetlenen_parcalar:
            d.bilgi("parcalar/%s" % p.get("ad"), _("'%s' parçası kullanılmıyor.")
                    % p.get("ad"))
            d.parca_yigini = [p.get("ad")]
            d.yuva(p.get("dugum"), "parcalar/%s/dugum" % p.get("ad"), 1)
            d.parca_yigini = []
    d.gruplar(agac.get("gruplar"))
    return d.bulgular


def yuva_ozeti(dugum):
    """Mesajlarda dugumun kisa adi."""
    return yuva_adi(dugum)
