# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/kap.py  --  Kap, bolge, yerlesim, eksenel ve kok kurulumu (R1-R7, R3b)
================================================================================

 geometri/kurulum.py'deki Kurucu'nun ikinci yarisi (dosya 800 satir tavani).
 Hucre sirasi eski kurucuyla ayni ilkeyi izler: once ic bolge, sonra halkalar
 icten disa; her bolgede once yerlesim (delik) hucreleri, sonra bolgenin
 kendi hucresi (eski tamburlu: tambur hucreleri, sonra yansitici).
================================================================================
"""

import math

from cekirdek import altigen_kor as _akor
from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer
from cekirdek.geometri.eksenel import dilimler, kok_yigini

SQ3 = math.sqrt(3.0)


class KapKurucu(object):
    """Kurucu karisimi: kap/bolge/eksenel/kok. Kurucu'nun alanlarini kullanir."""

    # ------------------------------------------------------------------
    # kap
    # ------------------------------------------------------------------
    def sinir_kesitleri(self, kap):
        """[kesit, halka1 dis kesiti, ...] (kalinlik ayni sekli buyutur)."""
        kesitler = [kap["kesit"]]
        for h in kap.get("halkalar") or []:
            if h.get("dis") is not None:
                kesitler.append(h["dis"])
            else:
                kesitler.append(_k.buyut(kesitler[-1], h["kalinlik"]))
        return kesitler

    def kap_evreni(self, kap):
        """Kok olmayan kap: bolge hucreleri + '+en dis' hucresi (dis dolgu)."""
        hucreler = self.kap_hucreleri(kap, kok=False)
        return self.y.evren(hucreler, name=("g:%s" % kap["id"]) if kap.get("id") else None)

    def kap_hucreleri(self, kap, kok):
        if kap["kesit"].get("sekil") == "kafes_zarfi":
            if not kok:
                raise ValueError("'kafes_zarfi' kesiti yalnız kök kapta kullanılır")
            return self.zarf_hucreleri(kap)
        kesitler = self.sinir_kesitleri(kap)
        son = len(kesitler) - 1
        siniri = [self.kesit_siniri(s, bc=self.yan if (kok and i == son) else None,
                                    yuzler=self.yuzler if (kok and i == son) else None)
                  for i, s in enumerate(kesitler)]
        yol = "/%s" % (kap.get("id") or "kap")
        hucreler = self.bolge(siniri[0].ic(), kap.get("ic"), kap.get("yerlesimler") or [],
                              kap, kok, yol + "/ic")
        for i, h in enumerate(kap.get("halkalar") or []):
            bolge = siniri[i].dis() & siniri[i + 1].ic()
            hucreler += self.bolge(bolge, h.get("icerik"), h.get("yerlesimler") or [],
                                   kap, kok, "%s/halkalar/%d" % (yol, i))
        if not kok:
            hucreler.append(self.yuva_hucresi(kap.get("dis"), siniri[-1].dis(),
                                              yol=yol + "/dis"))
        return hucreler

    # ------------------------------------------------------------------
    # bolge ve yerlesim
    # ------------------------------------------------------------------
    def _z(self, bolge, kok):
        """Kokte 3B modelde bolge x (alt, ust) z araligi."""
        if kok and self.zk is not None:
            return self.zk if bolge is None else bolge & self.zk
        return bolge

    def bolge(self, bolge, icerik, yerlesimler, kap, kok, yol):
        """Bir kap bolgesinin hucreleri: once delikler, sonra icerik."""
        hucreler = []
        for y in yerlesimler:
            deliksiz, delik_hucreleri = self.yerlesim(y, kap, kok, yol)
            hucreler += delik_hucreleri
            for d in deliksiz:
                bolge = bolge & d
        icerik = self._coz(icerik)
        if icerik.get("tur") == "eksenel" and not icerik.get("donusum"):
            return hucreler + self.eksenel_hucreler(bolge, icerik, kok, yol)
        hucreler.append(self.yuva_hucresi(icerik, self._z(bolge, kok), yol=yol))
        return hucreler

    def yerlesim(self, y, kap, kok, yol):
        """([sahip bolgeye eklenecek dis bolgeler], [ornek hucreleri])."""
        icerik = self._coz(y.get("icerik"))
        kes = y.get("kesit")
        if kes is None:
            kes = self._dogal_kesit(icerik)
        daire = kes.get("sekil") == "silindir"
        disler, hucreler = [], []
        self.y.yorum("yerleşim '%s' (%s): ön yüz yerel +x; psi = kora bakan yön + D"
                     % (y.get("ad"), y.get("mod")))
        for i, (x, yy, psi) in enumerate(_yer.ornekler(y, kap, self.tanim, self.gruplar)):
            if psi is not None and not daire and (y.get("bakis") is not None or
                                                  _yer.grup_degeri(self.gruplar, y.get("ad"))):
                raise ValueError("'%s' yerleşimi: daire dışı delik bakış ya da dönme ile "
                                 "döndürülemez" % y.get("ad"))
            delik = self.kesit_siniri(kes, merkez=(x, yy))
            tur, h = self.dolgu(icerik)
            don = icerik.get("donusum") or {}
            o = don.get("oteleme") or (0.0, 0.0)
            ceviri = rot = None
            if tur != "malzeme":
                ceviri = (x + float(o[0]), yy + float(o[1]), 0.0)
                rot = (0.0, 0.0, psi) if psi is not None else None
            hucre = self.y.hucre(h, self._z(delik.ic(), kok), name="g:%s#%d" % (y.get("ad"), i),
                                 translation=ceviri, rotation=rot)
            hucreler.append(self.dizin.hucre(hucre, "%s/yerlesim/%s#%d" % (yol, y.get("ad"), i)))
            disler.append(delik.delik_disi())
        return disler, hucreler

    def _dogal_kesit(self, icerik):
        from cekirdek.geometri.sema import bilesen_tanimi
        if icerik.get("tur") == "bilesen":
            tur, t = bilesen_tanimi(self.tanim, icerik.get("ad"))
            if tur == "tambur":
                return {"sekil": "silindir", "yaricap": float(t["yaricap"])}
        raise ValueError("yerleşim deliğinin kesiti verilmeli (yalnız tamburun doğal "
                         "kesiti vardır)")

    # ------------------------------------------------------------------
    # eksenel
    # ------------------------------------------------------------------
    def z_duzlemleri(self, eks, kok):
        """Yigin dilim sinirlari: kok yigini -> kok duzlemleri; kokteki baska
        yigin -> uclar kok duzlemleri, ic duzlemler havuzdan; kok disi -> uclar
        acik (None)."""
        dil = dilimler(eks)
        if kok and self.kok_yigin is eks:
            return self.kok_z
        ic = [self.zduz(z1) for _z0, z1, _k in dil[:-1]]
        if kok and self.kok_z is not None:
            return [self.kok_z[0]] + ic + [self.kok_z[-1]]
        return [None] + ic + [None]

    def katman_icerigi(self, eks, k):
        """Katmani dolduran dugum ya da ("kafes", ek anahtar)."""
        if k.get("anahtar"):
            ic = self._coz(eks.get("icerik"))
            if ic.get("tur") != "kafes":
                raise ValueError(
                    "'%s' eksenel katmanı: katmana özel harf eşlemesi yalnızca kare "
                    "haritalı tam korda ya da altıgen haritalı tam korda kullanılabilir"
                    % k.get("ad"))
            return ("kafes", ic, k["anahtar"])
        return ("dugum", k.get("icerik") if k.get("icerik") is not None else eks.get("icerik"),
                None)

    def eksenel_hucreler(self, bolge, eks, kok, yol):
        duz = self.z_duzlemleri(eks, kok)
        hucreler = []
        for i, (_z0, _z1, k) in enumerate(dilimler(eks)):
            dilim = None
            if duz[i] is not None:
                dilim = +duz[i]
            if duz[i + 1] is not None:
                dilim = -duz[i + 1] if dilim is None else dilim & -duz[i + 1]
            b = dilim if bolge is None else (bolge if dilim is None else bolge & dilim)
            ad = k.get("ad") or "katman %d" % (i + 1)
            tur, d, ek = self.katman_icerigi(eks, k)
            kyol = "%s/katmanlar/%d" % (yol, i)
            if tur == "kafes":
                h = self.y.hucre(self.kafes(d, ek), b, name=ad)
                hucreler.append(self.dizin.hucre(h, kyol))
            else:
                hucreler.append(self.yuva_hucresi(d, b, name=ad, yol=kyol))
        return hucreler

    def eksenel_evreni(self, eks):
        return self.y.evren(self.eksenel_hucreler(None, eks, False, "/eksenel"))

    # ------------------------------------------------------------------
    # R3b: kafes zarfli kok (konum hucreleri)
    # ------------------------------------------------------------------
    def zarf_hucreleri(self, kok):
        ic = self._coz(kok.get("ic"))
        eks = ic if ic.get("tur") == "eksenel" else None
        kafes = self._coz(eks.get("icerik")) if eks else ic
        n, P = int(kafes["halka_sayisi"]), float(kafes["adim"])
        yon = kafes.get("yonelim", "y")
        merkezler = _akor.kor_merkezleri(n, P, yon)
        katmanlar = self._zarf_katmanlari(eks)
        dolgular = self._zarf_dolgulari(kafes, eks, len(merkezler))
        halkalar = kok.get("halkalar") or []
        yansitici = bool(halkalar)
        bolgeler, dis_halka = self._zarf_prizmalari(merkezler, P, yon, yansitici)
        hucreler = []
        for i, (x, yy) in enumerate(merkezler):
            for j, (z_bolge, ad) in enumerate(katmanlar):
                b = bolgeler[i] if z_bolge is None else bolgeler[i] & z_bolge
                hucreler.append(self.dizin.hucre(
                    self.y.hucre(dolgular[i][j], b, name=ad, translation=(x, yy, 0.0)),
                    "/kok/ic/%d/%d" % (i, j)))
        if yansitici:
            hucreler += self._zarf_halkalari(kok, halkalar, merkezler, P, yon, dis_halka)
        return hucreler

    def _zarf_katmanlari(self, eks):
        if eks is None:
            return [(self.zk, "")]
        duz = self.kok_z
        return [(+duz[i] & -duz[i + 1], k.get("ad") or "katman %d" % (i + 1))
                for i, (_a, _b, k) in enumerate(dilimler(eks))]

    def _zarf_dolgulari(self, kafes, eks, n_konum):
        harfler = [h for s in kafes.get("harita") or [] for h in s]
        anahtar = kafes.get("anahtar") or {}
        katmanlar = [k for _a, _b, k in dilimler(eks)] if eks else [None]
        sonuc = []
        for harf in harfler:
            satir = []
            for k in katmanlar:
                if k and k.get("anahtar"):
                    esleme = dict(anahtar, **k["anahtar"])
                    satir.append(self._zarf_evreni(esleme, harf))
                elif k and k.get("icerik") is not None:
                    satir.append(self.evren(k["icerik"]))
                else:
                    satir.append(self._zarf_evreni(anahtar, harf))
            sonuc.append(satir)
        if len(sonuc) != n_konum:
            raise ValueError("altıgen kor haritası konum sayısı tutmuyor")
        return sonuc

    def _zarf_evreni(self, esleme, harf):
        if harf not in esleme:
            raise KeyError("kor haritasında tanımsız harf: '%s' (kafes zarflı kökte '.' "
                           "konumu için anahtarda harf tanımlayın)" % harf)
        return self.evren(esleme[harf])

    def _zarf_prizmalari(self, merkezler, adim, yonelim, yansitici):
        """Konum prizmalari (altigen_kor.altigen_kor_hucreleri ile ayni duzlem
        havuzu). DONER (bolgeler, dis halkadaki konum bolgeleri)."""
        taban = 0.0 if yonelim == "x" else 30.0
        nor = [(math.cos(math.radians(taban + 60.0 * k)),
                math.sin(math.radians(taban + 60.0 * k))) for k in range(6)]

        def anahtar(x, y):
            return (round(x / adim, 6) + 0.0, round(y / adim, 6) + 0.0)

        kume = {anahtar(x, y) for x, y in merkezler}
        havuz = {}

        def duzlem(kk, m, bc):
            a = (kk, m, bc)
            if a not in havuz:
                havuz[a] = self.y.duzlem(nor[kk][0], nor[kk][1], 0.0, m * adim / 2.0, bc=bc)
            return havuz[a]

        yuz_bc = self._zarf_yuz_bc()
        bolgeler, dis_halka = [], []
        for x, y in merkezler:
            bolge, sinirda = None, False
            for k in range(6):
                nx, ny = nor[k]
                komsu = anahtar(x + adim * nx, y + adim * ny) in kume
                sinirda = sinirda or not komsu
                bc = "transmission" if (komsu or yansitici) else yuz_bc[k]
                isaret = 1.0 if k < 3 else -1.0
                m = int(round(2.0 * isaret * (nx * x + ny * y + adim / 2.0) / adim))
                p = duzlem(k % 3, m, bc)
                yari = -p if isaret > 0 else +p
                bolge = yari if bolge is None else bolge & yari
            bolgeler.append(bolge)
            if sinirda:
                dis_halka.append(bolge)
        return bolgeler, dis_halka

    def _zarf_yuz_bc(self):
        """Kirik cizgi sinirinin yuz basina BC'si (yuz k: normal taban + 60 k)."""
        yuzler = self.yuzler
        if isinstance(yuzler, list) and len(yuzler) == 6:
            return [b or self.yan for b in yuzler]
        return [self.yan] * 6

    def _zarf_halkalari(self, kok, halkalar, merkezler, adim, yon, dis_halka):
        hucreler = []
        halka = int(round(max(math.hypot(x, y) for x, y in merkezler) / adim)) + 1
        son = len(halkalar) - 1
        onceki, onceki_kesit = None, None
        for i, h in enumerate(halkalar):
            if h.get("dis") is not None:
                kes = h["dis"]
            elif onceki_kesit is None:
                raise ValueError("'kafes_zarfi' üzerinde 'kalinlik' kullanılamaz; 'dis' "
                                 "kesiti verin")
            else:
                kes = _k.buyut(onceki_kesit, h["kalinlik"])
            sinir = self.kesit_siniri(kes, bc=self.yan if i == son else None,
                                      yuzler=self.yuzler if i == son else None)
            if i == 0:
                bolge = sinir.ic()
                if halka > 1:
                    orta = self.y.altigen_prizma(2.0 * ((halka - 1) * adim * SQ3 / 2.0) / SQ3,
                                                 kes.get("yonelim", yon))
                    bolge = bolge & +orta
                for b in dis_halka:
                    bolge = bolge & ~b
            else:
                bolge = onceki.dis() & sinir.ic()
            hucreler += self._zarf_bolgesi(bolge, h, kok, i)
            onceki, onceki_kesit = sinir, kes
        return hucreler

    def _zarf_bolgesi(self, bolge, h, kok, i):
        hucreler = []
        for y in h.get("yerlesimler") or []:
            disler, delik_hucreleri = self.yerlesim(y, kok, True, "/kok/halkalar/%d" % i)
            hucreler += delik_hucreleri
            for d in disler:
                bolge = bolge & d
        icerik = self._coz(h.get("icerik"))
        ad = "yansıtıcı" if i == 0 else None
        hucreler.append(self.yuva_hucresi(icerik, self._z(bolge, True), name=ad,
                                          yol="/kok/halkalar/%d" % i))
        return hucreler

    # ------------------------------------------------------------------
    # kok
    # ------------------------------------------------------------------
    def kok_kur(self):
        """(kok evreni, sinir kutusu (gx, gy))."""
        kok = self.m.kok
        sinir = kok.get("sinir") or {}
        self.yan = sinir.get("yan", "reflective")
        self.yuzler = sinir.get("yuzler")
        self._kok_z_kur(kok, sinir)
        hucreler = self.kap_hucreleri(kok, kok=True)
        u = self.y.evren(hucreler, degisken="kok" if self.y.betik else None)
        return u, self.sinir_kutusu()

    def _kok_z_kur(self, kok, sinir):
        self.kok_yigin = kok_yigini(kok)
        self.kok_z, self.zk = None, None
        if kok["kesit"].get("sekil") == "kure":
            return
        alt, ust = sinir.get("alt", "reflective"), sinir.get("ust", "reflective")
        if self.kok_yigin is not None and dilimler(self.kok_yigin):
            dil = dilimler(self.kok_yigin)
            h = dil[-1][1] - dil[0][0]
            self.y.yorum("eksenel katmanlar (alttan üste); iç arayüzler 'transmission'")
            self.kok_z = ([self.y.zduzlem(-h / 2.0, bc=alt)]
                          + [self.y.zduzlem(z1) for _z0, z1, _k in dil[:-1]]
                          + [self.y.zduzlem(+h / 2.0, bc=ust)])
        elif self.yukseklik:
            h = self.yukseklik
            self.kok_z = [self.y.zduzlem(-h / 2.0, bc=alt), self.y.zduzlem(+h / 2.0, bc=ust)]
        if self.kok_z is not None:
            self.zk = +self.kok_z[0] & -self.kok_z[-1]

    def sinir_kutusu(self):
        kok = self.m.kok
        if kok.get("_kutu"):
            return tuple(kok["_kutu"])
        return sinir_kutusu(self.m)


def en_dis_kesit(kok):
    """Kokun en dis kesiti (halkalar dahil); kafes_zarfi yalnizsa None."""
    kes = kok["kesit"]
    for h in kok.get("halkalar") or []:
        kes = h["dis"] if h.get("dis") is not None else _k.buyut(kes, h["kalinlik"])
    return kes


def _zarf_kutusu(kok):
    ic = kok.get("ic") or {}
    kafes = ic.get("icerik") if ic.get("tur") == "eksenel" else ic
    return _akor.kor_hucre_kutusu(int(kafes["halka_sayisi"]), float(kafes["adim"]),
                                  kafes.get("yonelim", "y"))


def sinir_kutusu(m):
    """Modelin sinir kutusu (gx, gy): sablonda eski kurucunun degeri."""
    kok = m.kok
    if kok.get("_kutu"):
        return tuple(kok["_kutu"])
    kes = en_dis_kesit(kok)
    if kes.get("sekil") == "kafes_zarfi":
        return _zarf_kutusu(kok)
    return _k.kutu(kes)


def ic_olcusu(m):
    """Kok kesitinin kutusu (halkalar haric) -> kaynak kutusu."""
    kok = m.kok
    if kok.get("_ic_kutu"):
        return tuple(kok["_ic_kutu"])
    if kok["kesit"].get("sekil") == "kafes_zarfi":
        return _zarf_kutusu(kok)
    return _k.kutu(kok["kesit"])
