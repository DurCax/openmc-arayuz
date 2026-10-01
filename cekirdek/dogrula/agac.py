# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/agac.py  --  Gelismis (agac) geometri dogrulamasi (§8, G-2)

   agac_kontrol(spec, yoklama_n=YOKLAMA_N) -> [Bulgu]

 dogrula/kor.kor_kontrol gelismis modda buraya devreder (sablon denetimleri
 form mesajlari olarak orada kalir; ayni konu iki kez bildirilmez).
 Sira: (1) yapisal denetim (geometri.yapisal_denetim: tur, alan, basvuru,
 dongu, derinlik) -- HATA varsa gerisi atlanir (kurulamaz); (2) geometrik
 denetim (analitik): yerlesim sigmasi ve ortusmesi, kafes_konumu deligi,
 kesik konum / kesik cubuk / kesik bilesen (UYARI, §15 karar 2), gizli konum
 (BILGI), altigen demetin yonelimi (HATA, R9.3), plakanin bolgeyi doldurmasi,
 eksenel toplamlar, sinir kosullari, bosluk bolge, 2B tambur, satir ici
 kopyalar; (3) nokta yoklamasi (M1): kurulan modelde rastgele noktalarda
 ortusme ve bosluk (HATA).
 Yer: "geometri:<yol>" (arayuz dugumu secer).
"""

import json

from cekirdek import sema, uygunluk
from cekirdek.ceviri import _, pgettext
from cekirdek.dogrula._ortak import Bulgu, hata_var
from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer
from cekirdek.gunluk import kaydedici

YOKLAMA_N = 600            # hizli dogrulamada yoklama noktasi (derin: yoklama.yokla)
ILK_KAC = 5                # mesajda listelenen konum sayisi
_UZUNLUK_PAYI = 1.0e-9
_log = kaydedici(__name__)


def _b(seviye, yol, mesaj, oneri=None):
    return Bulgu(seviye, "geometri:%s" % yol.lstrip("/"), mesaj, oneri)


def agac_kontrol(spec, yoklama_n=YOKLAMA_N):
    """Gelismis modun butun geometri bulgulari (bkz. modul notu)."""
    from cekirdek import geometri
    bulgular = list(geometri.yapisal_denetim(spec))
    if hata_var(bulgular):
        return bulgular
    try:
        m = geometri.model(spec)
        ziyaretler = list(geometri.gez(m))
    except (KeyError, ValueError, TypeError) as e:
        return bulgular + [_b("hata", "kok", _("Geometri gezilemedi: %s") % e)]
    except Exception as e:      # beklenmeyen: dogrulama cokmesin, ayrinti gunlukte
        _log.warning("geometri gezintisi beklenmeyen hatayla durdu", exc_info=True)
        return bulgular + [_b("hata", "kok", _("Geometri gezilemedi (beklenmeyen hata, "
                                               "ayrıntı günlükte): %s") % e)]
    for denetim in (_yerlesim_bulgulari, _kesik_bulgulari, _yonelim_bulgulari,
                    _plaka_bulgulari, _eksenel_bulgulari, _bosluk_ve_tambur,
                    _kopya_bulgulari):
        bulgular += denetim(spec, m, ziyaretler)
    bulgular += _sinir_bulgulari(spec)
    if yoklama_n and not hata_var(bulgular):
        bulgular += _yoklama_bulgulari(spec, yoklama_n)
    return bulgular


# ----------------------------------------------------------------------------
# yerlesim: sigma ve ortusme (§8 HATA 7)
# ----------------------------------------------------------------------------

def _kaplar(ziyaretler):
    gorulen, cikti = set(), []
    for z in ziyaretler:
        if z.dugum.get("tur") == "kap" and id(z.dugum) not in gorulen:
            gorulen.add(id(z.dugum))
            cikti.append((z.yol, z.dugum))
    return cikti


def _delik_kesiti(m, y):
    if y.get("kesit") is not None:
        return y["kesit"]
    from cekirdek.geometri.sema import bilesen_tanimi
    _t, t = bilesen_tanimi(m.tanimlar, (y.get("icerik") or {}).get("ad"))
    return {"sekil": "silindir", "yaricap": float((t or {}).get("yaricap") or 0.0)}


def _bolgeler(kap):
    from cekirdek.geometri.kesik import bolge_kesitleri
    kes = bolge_kesitleri(kap)
    cikti = [("ic", None, kes[0], kap.get("yerlesimler") or [])]
    for i, h in enumerate(kap.get("halkalar") or []):
        cikti.append(("halkalar/%d" % i, kes[i], kes[i + 1], h.get("yerlesimler") or []))
    return cikti


def _yerlesim_bulgulari(_spec, m, ziyaretler):
    bulgular = []
    for yol, kap in _kaplar(ziyaretler):
        if kap["kesit"].get("sekil") == "kafes_zarfi":
            continue
        for ek, ic, dis, yerlesimler in _bolgeler(kap):
            delikler = []
            for y in yerlesimler:
                kes = _delik_kesiti(m, y)
                for i, (x, yy, _psi) in enumerate(_yer.ornekler(y, kap, m.tanimlar, m.gruplar)):
                    delikler.append(("%s#%d" % (y.get("ad"), i), kes, (x, yy)))
                    bulgular += _delik_sigmasi(kap, y, kes, (x, yy), ic, dis,
                                               "%s/%s/yerlesimler/%s#%d" % (yol, ek, y.get("ad"), i))
            bulgular += _delik_ortusmesi(delikler, "%s/%s" % (yol, ek))
    return bulgular


def _delik_sigmasi(kap, y, kes, merkez, ic, dis, yol):
    if not _k.kapsar(dis, kes, merkez):
        return [_b("hata", yol, _("'%s' deliği bölgesinden taşıyor (dış sınıra değiyor).")
                   % y.get("ad"), _("Merkez yarıçapını ya da delik ölçüsünü küçültün."))]
    if ic is not None and any(_k.icinde(ic, px, py, pay=-1.0e-9)
                              for px, py in _k.sinir_noktalari(kes, merkez)):
        return [_b("hata", yol, _("'%s' deliği bölgenin iç sınırına taşıyor.") % y.get("ad"),
                   _("Merkez yarıçapını büyütün ya da deliği küçültün."))]
    if y.get("mod") == "kafes_konumu":
        return _kafes_konumu_sigmasi(kap, y, kes, merkez, yol)
    return []


def _kafes_konumu_sigmasi(kap, y, kes, merkez, yol):
    from cekirdek.geometri.gezinti import eleman_kesiti
    kafes = _yer._kafes_bul(kap, y.get("kafes"))
    el = eleman_kesiti(kafes.get("sekil"), kafes["adim"], kafes.get("yonelim", "y"))
    if _k.kapsar(dict(el), kes, (0.0, 0.0)):
        return []
    return [_b("hata", yol, _("'%s' deliği kafes konumu hücresinden taşıyor.") % y.get("ad"),
               _("Delik konum hücresinin içinde kalmalı (kafes adımından küçük)."))]


def _daire_mi(kes):
    return kes.get("sekil") == "silindir"


def _ortusuyor(a, b):
    (_ada, ka, ma), (_adb, kb, mb) = a, b
    if _daire_mi(ka) and _daire_mi(kb):
        d = ((ma[0] - mb[0]) ** 2 + (ma[1] - mb[1]) ** 2) ** 0.5
        return d < float(ka["yaricap"]) + float(kb["yaricap"]) - _UZUNLUK_PAYI
    return any(_k.icinde(kb, x, y, merkez=mb, pay=-1.0e-9)
               for x, y in _k.sinir_noktalari(ka, ma) + [ma]) or \
        any(_k.icinde(ka, x, y, merkez=ma, pay=-1.0e-9)
            for x, y in _k.sinir_noktalari(kb, mb) + [mb])


def _delik_ortusmesi(delikler, yol):
    bulgular = []
    for i, a in enumerate(delikler):
        for b in delikler[i + 1:]:
            if _ortusuyor(a, b):
                bulgular.append(_b("hata", yol, _("'%s' ve '%s' delikleri örtüşüyor.")
                                   % (a[0], b[0]),
                                   _("Örtüşen hücreler kayıp parçacık üretir; yerleşimleri "
                                     "ayırın.")))
    return bulgular


# ----------------------------------------------------------------------------
# kesik / gizli (§8 UYARI 1-2, BILGI), yonelim (R9.3), plaka
# ----------------------------------------------------------------------------

def _liste(yollar):
    """Ilk ILK_KAC yolun okunur listesi (';' ile: konum '(1, 2)' virgulu karismasin)."""
    from cekirdek.geometri.yol_metni import okunur
    ilk = sorted(set(yollar))[:ILK_KAC]
    return "; ".join(okunur(y.lstrip("/")) for y in ilk)


def _kesik_bulgulari(_spec, m, ziyaretler):
    from cekirdek import geometri
    bulgular = []
    # kirpilan bilesenin kendisi: kirpilan bolge ziyaretinin atasi (kap / bilesen)
    bilesen = [z.ust_yollar[-1] for z in ziyaretler if z.neden == "bilesen" and z.ust_yollar]
    cubuk = [z.ust_yollar[-1] for z in ziyaretler if z.neden == "cubuk" and z.ust_yollar]
    if bilesen:
        bulgular.append(_b("uyari", bilesen[0], _(
            "%d kesik konum/bileşen üst bölgeyle kırpılıyor (ilk %d: %s).")
            % (len(set(bilesen)), ILK_KAC, _liste(bilesen)),
            _("Kırpılan bileşenin hacmi stokastik hesaplanır; güç haritasında 'kesik' "
              "olarak işaretlenir.")))
    if cubuk:
        bulgular.append(_b("uyari", cubuk[0], _(
            "%d kesik çubuk: pin bölgesi hücre sınırıyla kesiliyor (ilk %d: %s).")
            % (len(set(cubuk)), ILK_KAC, _liste(cubuk)),
            _("Kesik çubuk F_ΔH'ye girmez ve hacmi stokastik hesaplanır; çubuk çubuk "
              "yanmada HATA verir.")))
    gizli = [k for k in geometri.kesik_konumlar(m) if k["durum"] == "gizli" and k["harf"] != "."]
    if gizli:
        bulgular.append(_b("bilgi", gizli[0]["yol"], _(
            "%d kafes konumu tamamen gizli (delik altında): haritada '.' yazılabilir.")
            % len(gizli)))
    return bulgular


def _yonelim_bulgulari(_spec, m, ziyaretler):
    """Altigen demet, altigen kafes elemaninda ayni yonelimle (R9.3, +1640 pcm)."""
    from cekirdek.geometri.sema import bilesen_tanimi
    bulgular = []
    for z in ziyaretler:
        d = z.dugum
        if d.get("tur") != "kafes" or d.get("sekil") != "altigen":
            continue
        yon = d.get("yonelim", "y")
        for h, v in sorted((d.get("anahtar") or {}).items()):
            ad = v if isinstance(v, str) else (v or {}).get("ad")
            tur, t = bilesen_tanimi(m.tanimlar, ad)
            if tur == "demet" and t.get("tur") == "altigen" and t.get("yonelim", "y") == yon:
                bulgular.append(_b("hata", "%s/anahtar/%s" % (z.yol, h), _(
                    "Altıgen '%s' demeti altıgen kafes elemanında aynı yönelimle ('%s'); "
                    "demet elemana oturmaz.") % (ad, yon),
                    _("Demet yönelimi kafes yönelimine dik olmalı: ters(kafes.yonelim).")))
    return bulgular


def _plaka_bulgulari(spec, _m, ziyaretler):
    from cekirdek.geometri.sablon import plaka_olcusu
    bulgular = []
    for z in ziyaretler:
        if z.tanim_turu != "plaka" or z.dugum.get("tur") != "bilesen" or z.bolge is None:
            continue
        p = sema.plaka_bul(spec, z.dugum.get("ad"))
        gx, gy = plaka_olcusu(p)
        if z.bolge.alan is not None and z.bolge.alan > gx * gy * (1 + 1e-9) + 1e-9:
            bulgular.append(_b("hata", z.yol, _(
                "'%s' plaka elemanı bulunduğu bölgeyi doldurmuyor (%.4g × %.4g cm; bölge "
                "%.4g cm²): aradaki nokta tanımsız (kayıp parçacık).")
                % (p["ad"], gx, gy, z.bolge.alan),
                _("Plaka elemanını ölçüsüne eşit bir kafes konumuna ya da kaba koyun.")))
    return bulgular


# ----------------------------------------------------------------------------
# eksenel, sinir, bosluk, tambur, kopyalar
# ----------------------------------------------------------------------------

def _eksenel_bulgulari(_spec, m, _ziyaretler):
    from cekirdek import geometri
    from cekirdek.geometri.eksenel import gecerli_katmanlar, kok_yigini, yiginlar, yigin_yuksekligi
    h = geometri.yukseklik(m)
    kok = kok_yigini(m.kok)
    bulgular = []
    for eks in yiginlar(m):
        yol = eks.get("id") or "eksenel"
        if not h:
            bulgular.append(_b("hata", yol, _("2B modelde eksenel yığın kurulamaz; kök "
                                               "yüksekliği verin.")))
            continue
        atlanan = [k.get("ad") or "?" for k in eks.get("katmanlar") or []
                   if k not in gecerli_katmanlar(eks)]
        if atlanan:
            bulgular.append(_b("bilgi", yol, _("0 cm katman atlandı: %s") % ", ".join(atlanan)))
        if eks is not kok and abs(yigin_yuksekligi(eks) - h) > _UZUNLUK_PAYI * max(1.0, h):
            bulgular.append(_b("hata", yol, _(
                "Kök dışındaki eksenel yığının toplamı (%g cm) model yüksekliğine (%g cm) "
                "eşit değil.") % (yigin_yuksekligi(eks), h)))
    return bulgular


def _sinir_bulgulari(spec):
    from cekirdek import geometri
    sb = geometri.sinir_bilgisi(geometri.model(spec))
    bulgular = []
    yan = uygunluk.sinir_secenekleri(spec, "yan")
    degerler = [("yan", sb.yan)]
    if sb.yuzler:
        yuzler = sb.yuzler.items() if isinstance(sb.yuzler, dict) else \
            zip(sb.yuz_adlari, sb.yuzler)
        degerler += list(yuzler)
    for ad, bc in degerler:
        if bc and bc not in yan:
            bulgular.append(_b("hata", "kok/sinir", _(
                "'%s' yüzünde %s sınır bu dış sınırda kullanılamaz (%s).")
                % (ad, bc, ", ".join(yan)),
                _("Periyodik sınır yalnız dikdörtgen/altıgen dış sınırda ve sınıra değen "
                  "delik yokken kullanılabilir.")))
    for yon, bc in (("alt", sb.alt), ("ust", sb.ust)):
        if bc == "periodic":
            bulgular.append(_b("hata", "kok/sinir", _(
                "%s sınır periyodik olamaz: sonlu bir korda eksenel periyodiklik fiziksel "
                "değildir.") % yon))
    if not geometri.yukseklik(geometri.model(spec)) and sb.yuzey != "kure":
        bulgular.append(_b("bilgi", "kok", _(
            "yükseklik verilmemiş — model eksenel yönde sonsuz (2B) kabul ediliyor")))
    return bulgular


def _bosluk_ve_tambur(_spec, m, ziyaretler):
    from cekirdek import geometri
    bulgular = []
    for z in ziyaretler:
        d = z.dugum
        if d.get("tur") == "malzeme" and d.get("ad") == sema.BOSLUK and len(z.ust_yollar) <= 1 \
                and z.tanim_turu is None and z.bolge is not None:
            bulgular.append(_b("uyari", z.yol, _("Kök içinde boş (void) bölge: nötron burada "
                                                 "etkileşmeden geçer.")))
    tambur = any(z.tanim_turu == "tambur" and z.dugum.get("tur") == "bilesen"
                 for z in ziyaretler)
    if tambur and not geometri.yukseklik(m):
        bulgular.append(_b("uyari", "kok", _("2B modelde kontrol tamburu: eksenel sızıntı "
                                             "yok; tambur değeri fazla çıkar.")))
    return bulgular


def _kanonik(d):
    def temiz(x):
        if isinstance(x, dict):
            return {k: temiz(v) for k, v in x.items() if k not in ("id", "ad")}
        if isinstance(x, list):
            return [temiz(v) for v in x]
        return x
    return json.dumps(temiz(d), sort_keys=True, default=str)


def _kopya_bulgulari(_spec, m, ziyaretler):
    """Ayni icerikli iki satir ici alt agac (§8 UYARI 3): distribcell bolunur."""
    gorulen, bulgular = {}, []
    for z in ziyaretler:
        d = z.dugum
        if d.get("tur") not in ("kap", "kafes") or str(d.get("id") or "").startswith("demet:") \
                or z.yol == "/kok" or ">" in z.yol:
            continue
        anahtar = _kanonik(d)
        if anahtar in gorulen and gorulen[anahtar] is not d:
            bulgular.append(_b("uyari", z.yol, _(
                "Aynı içerikli iki satır içi alt ağaç ('%s'): ayrı evrenler olur, "
                "distribcell ve tükenme örnekleri bölünür.") % (d.get("id") or d.get("tur")),
                _("Alt ağacı bir parçaya çevirip iki yerde 'bilesen' olarak kullanın.")))
        gorulen.setdefault(anahtar, d)
    return bulgular


# ----------------------------------------------------------------------------
# nokta yoklamasi (M1)
# ----------------------------------------------------------------------------

def _yoklama_bulgulari(spec, n):
    from cekirdek.geometri import yoklama
    try:
        sonuc, metinler = yoklama.yokla(spec, n=n, tohum=1)
    except (KeyError, ValueError, RuntimeError) as e:
        return [_b("hata", "kok", _("Model kurulamadı: %s") % e)]
    bulgular = []
    if sonuc.ortusmeler:
        bulgular.append(_b("hata", "kok", _("Nokta yoklaması: %s. %s")
                           % (yoklama.oran_metni(sonuc), "; ".join(
                               t for t in metinler if t.startswith(pgettext("yoklama", "örtüşme")))),
                           _("Örtüşen hücreler kayıp parçacık üretir.")))
    if sonuc.bosluklar:
        bulgular.append(_b("hata", "kok", _("Nokta yoklaması: %s. %s")
                           % (yoklama.oran_metni(sonuc), "; ".join(
                               t for t in metinler if t.startswith(pgettext("yoklama", "boşluk")))),
                           _("Tanımsız bölge: parçacık kaybolur. Bölgeyi bir malzemeyle "
                             "doldurun.")))
    return bulgular
