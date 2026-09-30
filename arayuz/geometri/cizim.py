# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/cizim.py  --  Agactan sematik xy kesit ogeleri
================================================================================
 Gelismis editorun orta paneli OpenMC cizimi degil, AGACIN kendisinden
 hesaplanan sematik bir kesittir: her oge (yol, QPainterPath, renk) uclusudur.
 Boylece tiklanan noktanin hangi DUGUME ait oldugu dogrudan bilinir (agacta
 secim) ve secili dugumun butun ogeleri vurgulanir. Gercek OpenMC cizimi sag
 paneldeki onizlemede kalir (arayuz/onizleme.py).

 KURALLAR
   * Koordinatlar model cercevesinde (cm, +y yukari). Widget donusumu yapar.
   * Ogeler CIZIM SIRASINDADIR (ust once, alt sonra); isabet testi sondan basa.
   * Her oge ustlerinin bolgesiyle kirpilir (QPainterPath.intersected).
   * Kutuphane bileseni (demet / cubuk / plaka / tambur) kendi alt yapisiyla
     cizilir; parca (geometri.parcalar) alt agaci da acilir, ama ogeleri
     KULLANIM yerinin yolunu tasir (agacta secilen sey kullanimdir).
   * Oge butcesi (_BUTCE) asilinca demet ve alt kafesler duz renkle doldurulur
     (tam kor 17x17 demetlerde binlerce pin; cizim akici kalsin).
   * Kesik/gizli konumlar (geometri.kesik_konumlar) 'kesik' alaniyla isaretli.
 Renkler malzemenin kendi rengidir (spec) -- izgara.parca_rengi ile ayni kaynak.
================================================================================
"""

import math
from dataclasses import dataclass

from PySide6 import QtCore, QtGui

from cekirdek import altigen
from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer
from cekirdek.geometri.sema import bilesen_tanimi
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.geometri.cizim")

SQ3 = math.sqrt(3.0)
_BUTCE = 6000               # en cok oge; asilinca alt yapi duz renk
_EN_DERIN = 8
_DAIRE_NOKTA = 96


@dataclass(frozen=True)
class Oge:
    """Tek cizim ogesi. yol: agactaki dugum (demet), yol_metni: "/kok/ic"."""
    yol: tuple
    yol_metni: str
    yol_yolu: QtGui.QPainterPath
    renk: tuple | None
    kesik: str | None = None          # "kesik" | "gizli" | None
    etiket: str | None = None


def yol_metni(yol):
    return "/" + "/".join(str(p) for p in yol)


# ============================================================================
# kesit -> QPainterPath (yerel cerceve)
# ============================================================================

def _cokgen(koseler):
    p = QtGui.QPainterPath()
    p.addPolygon(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in koseler]))
    p.closeSubpath()
    return p


def altigen_koseleri(apotem, prizma_yonelimi, merkez=(0.0, 0.0)):
    """Prizma anlaminda altigenin 6 kosesi (yuz normali + 30 derece)."""
    r = 2.0 * apotem / SQ3
    cx, cy = merkez
    return [(cx + r * math.cos(math.radians(a + 30.0)), cy + r * math.sin(math.radians(a + 30.0)))
            for a in _k.altigen_normal_acilari(prizma_yonelimi)]


def kesit_yolu(kes, merkez=(0.0, 0.0), zarf=None):
    """Kesitin QPainterPath'i. kafes_zarfi icin zarf=(apotem, yonelim)."""
    s = (kes or {}).get("sekil")
    cx, cy = merkez
    p = QtGui.QPainterPath()
    if s == "dikdortgen":
        gx, gy = (float(v) for v in kes["boyut"])
        p.addRect(QtCore.QRectF(cx - gx / 2.0, cy - gy / 2.0, gx, gy))
        return p
    if s in ("silindir", "kure"):
        r = float(kes["yaricap"])
        p.addEllipse(QtCore.QPointF(cx, cy), r, r)
        return p
    if s == "altigen":
        return _cokgen(altigen_koseleri(float(kes["apotem"]), kes.get("yonelim", "y"), merkez))
    if s == "kafes_zarfi" and zarf is not None:
        return _cokgen(altigen_koseleri(zarf[0], zarf[1], merkez))
    return p


def kafes_hucresi(sekil, adim, yonelim, merkez):
    """Kafes eleman hucresi: kare P x P; altigen ters(kafes yonelimi) prizma."""
    cx, cy = merkez
    if sekil == "kare":
        p = QtGui.QPainterPath()
        p.addRect(QtCore.QRectF(cx - adim / 2.0, cy - adim / 2.0, adim, adim))
        return p
    return _cokgen(altigen_koseleri(adim / 2.0, _k.ters_yonelim(yonelim or "y"), merkez))


def kafes_konumlari(sekil, adim, harita, boyut=None, halka_sayisi=None, yonelim="y"):
    """[((r, i), (x, y))] harita sirasiyla (kesik.py ile ayni cerceve)."""
    P = float(adim)
    if sekil == "kare":
        nx, ny = boyut if boyut else (max((len(s) for s in harita), default=0), len(harita))
        return [((r, i), (-P * nx / 2.0 + (i + 0.5) * P, P * ny / 2.0 - (r + 0.5) * P))
                for r, satir in enumerate(harita) for i in range(len(satir))]
    n = int(halka_sayisi or len(harita))
    kon = altigen.konumlar(n, yonelim or "y") if n > 0 else {}
    return [((r, i), (x * P, y * P)) for (r, i), (x, y) in sorted(kon.items())]


def zarf(d):
    """Kafes zarfli kapta (apotem, yonelim); degilse None."""
    if (d.get("kesit") or {}).get("sekil") != "kafes_zarfi":
        return None
    ic = d.get("ic")
    if isinstance(ic, dict) and ic.get("tur") == "eksenel":
        ic = ic.get("icerik")
    if not (isinstance(ic, dict) and ic.get("tur") == "kafes"):
        return None
    return (_k.kafes_zarfi_apotemi(int(ic.get("halka_sayisi") or 1), float(ic["adim"])),
            ic.get("yonelim", "y"))


def bolge_kesitleri(d):
    """[ic siniri, halka 1 dis siniri, ...] kesitleri (kafes zarfi altigene cevrilir)."""
    kesitler = [d.get("kesit") or {}]
    for h in d.get("halkalar") or []:
        if h.get("dis") is not None:
            kesitler.append(h["dis"])
            continue
        onceki = kesitler[-1]
        if onceki.get("sekil") == "kafes_zarfi" and zarf(d):
            a, yon = zarf(d)
            onceki = {"sekil": "altigen", "apotem": a, "yonelim": yon}
        try:
            kesitler.append(_k.buyut(onceki, float(h.get("kalinlik") or 0.0)))
        except (ValueError, KeyError, TypeError):
            _log.info("halka kesiti hesaplanamadi (%r); onceki kesit kullanildi", h)
            kesitler.append(onceki)
    return kesitler


# ============================================================================
# cizici
# ============================================================================

class _Cizici:
    def __init__(self, spec, model, z=0.0, kesikler=None):
        from arayuz import izgara
        self.spec = spec
        self.m = model
        self.z = float(z)
        self.ogeler = []
        self._renk = {}
        self._izgara = izgara
        self._kesik = {(k.get("kafes"), tuple(k.get("indeks") or ())): k.get("durum")
                       for k in (kesikler or [])}
        self._parca_indeksi = {p.get("ad"): p for p in model.parcalar}

    # ---------------- yardimcilar ----------------
    def renk(self, ad):
        if ad not in self._renk:
            self._renk[ad] = self._izgara.parca_rengi(self.spec, ad)
        return self._renk[ad]

    def ekle(self, yol, yol_yolu, renk, kesik=None, etiket=None):
        if yol_yolu.isEmpty():
            return
        self.ogeler.append(Oge(tuple(yol), yol_metni(yol), yol_yolu, renk, kesik, etiket))

    def butce_var(self):
        return len(self.ogeler) < _BUTCE

    @staticmethod
    def kirp(bolge, yol_yolu):
        if bolge.contains(yol_yolu):
            return yol_yolu
        return bolge.intersected(yol_yolu)

    # ---------------- dugum ----------------
    def dugum(self, d, yol, T, bolge, derinlik=0):
        if bolge.isEmpty() or derinlik > _EN_DERIN:
            return
        if isinstance(d, str) or d is None:
            ad = d or "bosluk"
            self.ekle(yol, bolge, self.renk(ad), etiket=ad)
            return
        tur = d.get("tur")
        T = self._donusum(d, T)
        if tur == "malzeme":
            self.ekle(yol, bolge, self.renk(d.get("ad")), etiket=d.get("ad"))
        elif tur == "bilesen":
            self.bilesen(d.get("ad"), yol, T, bolge, derinlik)
        elif tur == "kafes":
            self.kafes(d, yol, T, bolge, derinlik)
        elif tur == "kap":
            self.kap(d, yol, T, bolge, derinlik)
        elif tur == "eksenel":
            self.eksenel(d, yol, T, bolge, derinlik)
        else:
            self.ekle(yol, bolge, None, etiket=str(tur))

    @staticmethod
    def _donusum(d, T):
        don = d.get("donusum") or {}
        if not don:
            return T
        yeni = QtGui.QTransform(T)
        ot = don.get("oteleme") or (0.0, 0.0)
        yeni.translate(float(ot[0]), float(ot[1]))
        if don.get("donme"):
            yeni.rotate(float(don["donme"]))
        return yeni

    def bilesen(self, ad, yol, T, bolge, derinlik):
        tur, tanim = bilesen_tanimi(self.m.tanimlar, ad)
        if tur == "parca":
            self.dugum(self._parca_indeksi.get(ad, tanim).get("dugum"), yol, T, bolge,
                       derinlik + 1)
            return
        if tur == "tambur":
            self.tambur(tanim, yol, T, bolge)
            return
        if tur == "cubuk":
            self.cubuk(tanim, yol, T, bolge)
            return
        if tur == "demet" and self.butce_var():
            self.demet(tanim, yol, T, bolge, derinlik)
            return
        self.ekle(yol, bolge, self.renk(ad), etiket=ad)

    def tambur(self, t, yol, T, bolge):
        R = float(t.get("yaricap") or 0.0)
        r_ic = float(t.get("emici_ic_yaricap") or 0.0)
        aci = float(t.get("emici_aci") or 120.0)
        govde = QtGui.QPainterPath()
        govde.addEllipse(QtCore.QPointF(0, 0), R, R)
        self.ekle(yol, self.kirp(bolge, T.map(govde)), self.renk(t.get("govde_malzeme")),
                  etiket=t.get("ad"))
        kama = QtGui.QPainterPath()
        kama.moveTo(0, 0)
        kama.arcTo(QtCore.QRectF(-R, -R, 2 * R, 2 * R), -aci / 2.0, aci)
        kama.closeSubpath()
        if r_ic > 0:
            ic = QtGui.QPainterPath()
            ic.addEllipse(QtCore.QPointF(0, 0), r_ic, r_ic)
            kama = kama.subtracted(ic)
        # QPainterPath acilari ekranda saat yonunun tersi, y asagi: model
        # cercevesinde (+y yukari) yayi +x'e ortalamak icin ayna gerekmez
        # cunku yay +x etrafinda simetriktir.
        self.ekle(yol, self.kirp(bolge, T.map(kama)), self.renk(t.get("emici_malzeme")),
                  etiket=t.get("emici_malzeme"))

    def cubuk(self, c, yol, T, bolge):
        """Es merkezli bolgeler (silindir / kare / altigen pin kesiti)."""
        sekil = c.get("kesit") or "silindir"
        yon = c.get("kesit_yonelim") or "y"
        bolgeler = list(c.get("bolgeler") or [])
        dis = bolgeler[-1] if bolgeler else {}
        self.ekle(yol, bolge, self.renk(dis.get("malzeme")), etiket=c.get("ad"))
        for b in reversed(bolgeler[:-1]):
            if b.get("r") is None:
                continue
            p = kesit_yolu(_k.pin_bolge_kesiti(sekil, float(b["r"]), yon))
            self.ekle(yol, self.kirp(bolge, T.map(p)), self.renk(b.get("malzeme")),
                      etiket=b.get("malzeme"))

    def demet(self, d, yol, T, bolge, derinlik):
        sekil = "kare" if d.get("tur", "kare") == "kare" else "altigen"
        self.ekle(yol, bolge, self.renk(d.get("dolgu_disi") or "bosluk"), etiket=d.get("ad"))
        harita = d.get("harita") or []
        kon = kafes_konumlari(sekil, d["adim"], harita, d.get("boyut"),
                              d.get("halka_sayisi"), d.get("yonelim", "y"))
        if len(kon) + len(self.ogeler) > _BUTCE:
            return
        anahtar = d.get("anahtar") or {}
        for (r, i), (x, y) in kon:
            try:
                harf = harita[r][i]
            except IndexError:
                continue
            ad = anahtar.get(harf)
            if ad is None:
                continue
            hucre = T.map(kafes_hucresi(sekil, float(d["adim"]), d.get("yonelim", "y"), (x, y)))
            alt = self.kirp(bolge, hucre)
            T2 = QtGui.QTransform(T)
            T2.translate(x, y)
            self.bilesen(ad, yol, T2, alt, derinlik + 1)

    # ---------------- kafes ----------------
    def kafes(self, d, yol, T, bolge, derinlik):
        sekil = d.get("sekil", "kare")
        P = float(d.get("adim") or 0.0)
        if P <= 0:
            self.ekle(yol, bolge, None, etiket="kafes")
            return
        dis = d.get("dis")
        self.dugum(dis, yol + ("dis",), T, bolge, derinlik + 1)
        harita = d.get("harita") or []
        kon = kafes_konumlari(sekil, P, harita, d.get("boyut"), d.get("halka_sayisi"),
                              d.get("yonelim", "y"))
        anahtar = d.get("anahtar") or {}
        duz = len(kon) + len(self.ogeler) > _BUTCE
        for (r, i), (x, y) in kon:
            try:
                harf = harita[r][i]
            except IndexError:
                continue
            hucre = T.map(kafes_hucresi(sekil, P, d.get("yonelim", "y"), (x, y)))
            alt = self.kirp(bolge, hucre)
            if alt.isEmpty():
                continue
            kesik = self._kesik.get((d.get("id"), (r, i)))
            if harf == "." or harf not in anahtar:
                self.dugum(dis, yol + ("dis",), T, alt, derinlik + 1)
            else:
                T2 = QtGui.QTransform(T)
                T2.translate(x, y)
                icerik = anahtar[harf]
                alt_yol = yol + ("anahtar", harf)
                if duz and isinstance(icerik, dict) and icerik.get("tur") not in ("malzeme",):
                    self.ekle(alt_yol, alt, self.renk(icerik.get("ad")), etiket=icerik.get("ad"))
                else:
                    self.dugum(icerik, alt_yol, T2, alt, derinlik + 1)
            if kesik:
                self.ekle(yol + ("anahtar", harf), alt, None, kesik=kesik)

    # ---------------- kap ----------------
    def kap(self, d, yol, T, bolge, derinlik):
        kesitler = self._bolge_kesitleri(d)
        yollar = [T.map(kesit_yolu(k, zarf=self._zarf(d))) for k in kesitler]
        en_dis = yollar[-1]
        if d.get("dis") is not None:
            self.dugum(d.get("dis"), yol + ("dis",), T, bolge.subtracted(en_dis), derinlik + 1)
        bolgeler = [(("ic",), d.get("ic"), d.get("yerlesimler") or [], yollar[0], None)]
        for i, h in enumerate(d.get("halkalar") or []):
            bolgeler.append((("halkalar", i, "icerik"), h.get("icerik"),
                             h.get("yerlesimler") or [], yollar[i + 1], yollar[i]))
        for alt_yol, icerik, yerlesimler, dis_yol, ic_yol in bolgeler:
            reg = self.kirp(bolge, dis_yol)
            if ic_yol is not None:
                reg = reg.subtracted(ic_yol)
            delikler = self._delikler(d, alt_yol, yerlesimler, T)
            dolu = reg
            for _y, _i, _T, delik in delikler:
                dolu = dolu.subtracted(delik)
            self.dugum(icerik, yol + alt_yol, T, dolu, derinlik + 1)
            for y_yol, y_icerik, T2, delik in delikler:
                self.dugum(y_icerik, yol + y_yol, T2, self.kirp(reg, delik), derinlik + 1)

    @staticmethod
    def _zarf(d):
        return zarf(d)

    @staticmethod
    def _bolge_kesitleri(d):
        return bolge_kesitleri(d)

    def _delikler(self, kap, bolge_yol, yerlesimler, T):
        """[(yerlesim icerik yolu, icerik, donusum, delik yolu)]."""
        cikti = []
        taban = bolge_yol[:-1] if bolge_yol[-1] == "icerik" else ()
        for j, y in enumerate(yerlesimler):
            try:
                ornekler = _yer.ornekler(y, kap, self.m.tanimlar, self.m.gruplar)
            except (ValueError, KeyError, TypeError) as e:
                _log.info("yerlesim ornekleri hesaplanamadi: %s", e)
                continue
            kes = y.get("kesit")
            if kes is None:
                _t, t = bilesen_tanimi(self.m.tanimlar, (y.get("icerik") or {}).get("ad"))
                kes = {"sekil": "silindir", "yaricap": float((t or {}).get("yaricap") or 0.0)}
            for x, yy, psi in ornekler:
                T2 = QtGui.QTransform(T)
                T2.translate(x, yy)
                if psi:
                    T2.rotate(psi)
                cikti.append((taban + ("yerlesimler", j, "icerik"), y.get("icerik"), T2,
                              T2.map(kesit_yolu(kes))))
        return cikti

    # ---------------- eksenel ----------------
    def eksenel(self, d, yol, T, bolge, derinlik):
        k_ix = katman_indeksi(d, self.z)
        if k_ix is None:
            self.dugum(d.get("icerik"), yol + ("icerik",), T, bolge, derinlik + 1)
            return
        secili = d["katmanlar"][k_ix]
        if secili.get("icerik") is not None:
            self.dugum(secili["icerik"], yol + ("katmanlar", k_ix, "icerik"), T, bolge,
                       derinlik + 1)
            return
        self.dugum(katman_icerigi(d, secili), yol + ("icerik",), T, bolge, derinlik + 1)


def katman_araliklari(d):
    """Eksenel yiginin pozitif katmanlari [(indeks, z0, z1)] (z = 0 merkezli)."""
    katmanlar = [(i, float(k.get("yukseklik") or 0.0))
                 for i, k in enumerate(d.get("katmanlar") or [])]
    katmanlar = [(i, h) for i, h in katmanlar if h > 0]
    z = -sum(h for _i, h in katmanlar) / 2.0
    cikti = []
    for i, h in katmanlar:
        cikti.append((i, z, z + h))
        z += h
    return cikti


def katman_indeksi(d, z):
    """z yuksekligindeki katmanin indeksi (disindaysa en yakin uc katman)."""
    araliklar = katman_araliklari(d)
    if not araliklar:
        return None
    for i, z0, z1 in araliklar:
        if z0 <= z < z1:
            return i
    return araliklar[0][0] if z < araliklar[0][1] else araliklar[-1][0]


def katman_icerigi(d, katman):
    """Katmanin varsayilan icerigi (katman anahtari kafese uygulanmis)."""
    icerik = d.get("icerik")
    if katman.get("anahtar") and isinstance(icerik, dict) and icerik.get("tur") == "kafes":
        return dict(icerik, anahtar=dict(icerik.get("anahtar") or {}, **katman["anahtar"]))
    return icerik


def xy_ogeleri(spec, z=0.0):
    """
    Spec'in sematik xy kesiti: (ogeler, sinir kutusu (x0, y0, x1, y1)).
    Model kurulamazsa ([], None); hata gunluge yazilir.
    """
    from cekirdek import geometri
    try:
        m = geometri.model(spec)
        kesikler = geometri.kesik_konumlar(m)
    except Exception:
        _log.warning("sematik kesit icin model kurulamadi", exc_info=True)
        return [], None
    c = _Cizici(spec, m, z, kesikler)
    kok = m.kok
    evren = QtGui.QPainterPath()
    kesitler = c._bolge_kesitleri(kok)
    dis = kesit_yolu(kesitler[-1], zarf=c._zarf(kok))
    evren.addRect(dis.boundingRect().adjusted(-1, -1, 1, 1))
    try:
        c.dugum(kok, ("kok",), QtGui.QTransform(), dis)
    except Exception:
        _log.warning("sematik kesit cizilemedi", exc_info=True)
    r = dis.boundingRect()
    return c.ogeler, (r.left(), r.top(), r.right(), r.bottom())


def isabet(ogeler, x, y):
    """(x, y) noktasindaki en ustteki (en derin) ogenin yolu; yoksa None."""
    nokta = QtCore.QPointF(x, y)
    for oge in reversed(ogeler):
        if oge.kesik is None and oge.yol_yolu.contains(nokta):
            return oge.yol
    return None
