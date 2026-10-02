# -*- coding: utf-8 -*-
"""
baslangic_adim.py -- "Sifirdan" modelin adim rehberi (v3 K1; Qt gerektirmez)

NEDEN
  Gercekten bos bir modelle (sema.yeni_spec) baslayan ogrenci once ne
  yapacagini bilmeli: malzeme ekle -> parca -> demet -> geometri. Bos modelin
  dogrulama "hatalari" (or. "kor: cubuk secilmemis") aslinda henuz atilmamis
  ADIMLARDIR; kirmizi hata gibi degil, bilgi tonunda "eksik adim" olarak
  sunulur (arayuz/pencere/dogrulama_seridi.py).

ADIMLAR (kor turune gore; dogrula/kor.py ve model_islemleri.sekme_isaretleri
ile ayni "eksik" olcutleri)
  malzeme  : en az bir malzeme                       -> Malzemeler
  parca    : en az bir cubuk (plaka turunde plaka)    -> Parcalar
  demet    : yalniz demet/kafes turlerinde, en az bir demet -> Demet
  geometri : korun dolgusu secili / kor haritasi dolu -> Geometri
Rehberi olmayan turlerde (kuresel, tamburlu, agac) adim listesi bostur.
"""

from dataclasses import dataclass

from cekirdek import sema
from cekirdek.ceviri import _, N_

# Sifirdan secilebilen (rehberli) kor turleri, baslangic ekranindaki sirayla.
SIFIRDAN_TURLERI = ("tek_cubuk", "tek_demet", "kare_kafes", "altigen_kafes", "tek_plaka")
_DEMETLI = ("tek_demet",) + sema.HARITALI_KORLAR
_DOLGU_ALANI = {"tek_cubuk": "cubuk", "tek_plaka": "plaka", "tek_demet": "demet"}

# (anahtar, baslik, sayfa, bulgu yeri onekleri) -- baslik yalniz isaretli (N_).
_ADIM_TANIMI = {
    "malzeme": (N_("Malzeme ekle"), "malzemeler", ("malzeme",)),
    "parca": (N_("Parça ekle"), "parcalar", ("cubuk", "plaka")),
    "demet": (N_("Demet kur"), "demet", ("demet",)),
    "geometri": (N_("Geometriyi kur"), "kor", ("kor",)),
}


@dataclass(frozen=True)
class Adim:
    """Rehberin bir adimi. baslik/aciklama etkin dilde; sekme sayfa anahtari."""
    anahtar: str
    baslik: str
    aciklama: str
    sekme: str
    tamam: bool


def _tur(spec: dict) -> str | None:
    return (spec.get("kor") or {}).get("tur")


def _parca_aciklamasi(tur: str) -> str:
    if tur == "tek_plaka":
        return _("Parçalar sayfasında bir plaka elemanı ekleyin.")
    return _("Parçalar sayfasında Çubuk ▸ Yakıt çubuğu ile ilk çubuğu ekleyin.")


def _geometri_tamam(spec: dict, tur: str) -> bool:
    kor = spec.get("kor") or {}
    if tur in sema.HARITALI_KORLAR:
        return any(h for satir in kor.get("harita") or [] for h in satir)
    return bool(kor.get(_DOLGU_ALANI.get(tur, "")))


def _geometri_aciklamasi(tur: str) -> str:
    if tur in sema.HARITALI_KORLAR:
        return _("Geometri sayfasında demetleri kor haritasına yerleştirin.")
    if tur == "tek_demet":
        return _("Geometri sayfasında hücreyi dolduracak demeti seçin.")
    return _("Geometri sayfasında hücreyi dolduracak parçayı seçin.")


def _adim(anahtar: str, aciklama: str, tamam: bool) -> Adim:
    baslik, sekme, _yerler = _ADIM_TANIMI[anahtar]
    return Adim(anahtar, _(baslik), aciklama, sekme, bool(tamam))


def adimlar(spec: dict) -> tuple:
    """Modelin kor turune uyan adimlar (sirali); rehbersiz turde ()."""
    tur = _tur(spec)
    if tur not in SIFIRDAN_TURLERI:
        return ()
    parca_listesi = "plakalar" if tur == "tek_plaka" else "cubuklar"
    sonuc = [
        _adim("malzeme", _("Malzemeler sayfasında kütüphaneden yakıt, zarf ve "
                           "soğutucu ekleyin."), spec.get("malzemeler")),
        _adim("parca", _parca_aciklamasi(tur), spec.get(parca_listesi)),
    ]
    if tur in _DEMETLI:
        sonuc.append(_adim("demet", _("Demet sayfasında yeni bir demet kurup "
                                      "çubukları ızgaraya yerleştirin."),
                           spec.get("demetler")))
    sonuc.append(_adim("geometri", _geometri_aciklamasi(tur), _geometri_tamam(spec, tur)))
    return tuple(sonuc)


def eksik_adimlar(spec: dict) -> tuple:
    """Henuz tamamlanmamis adimlar (sirali)."""
    return tuple(a for a in adimlar(spec) if not a.tamam)


def siradaki(spec: dict) -> Adim | None:
    """Ilk eksik adim; model eksiksizse None."""
    eksik = eksik_adimlar(spec)
    return eksik[0] if eksik else None


def adim_bulgusu_mu(spec: dict, bulgu) -> bool:
    """Bulgu, henuz atilmamis bir adimin DOGAL sonucu mu? (eksik adimin
    sayfasindaki hata/uyari). Boyle bulgular kirmizi hata degil "eksik adim"
    olarak sunulur; adim tamamlaninca ayni bulgu gercek hata sayilir."""
    yer = (getattr(bulgu, "yer", "") or "").lower()
    for adim in eksik_adimlar(spec):
        if any(yer.startswith(onek) for onek in _ADIM_TANIMI[adim.anahtar][2]):
            return True
    return False


def ilerleme(spec: dict) -> tuple:
    """(tamamlanan, toplam) adim sayisi."""
    hepsi = adimlar(spec)
    return sum(1 for a in hepsi if a.tamam), len(hepsi)
