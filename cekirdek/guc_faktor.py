# -*- coding: utf-8 -*-
"""
================================================================================
 guc_faktor.py  --  Guc dagilimi: eksenel faktorler ve kesik cubuklar
================================================================================

 guc.py'den bolundu (Dalga G-2; dosya 800 satir tavani). guc bu adlari
 yeniden disa verir.

   _eksenel_faktorler, _bos_dilimler   F_q, eksenel harita ve profil (3B)
   kesik_cubuklar(dagilim, geometri, hucreler)
       §8 UYARI 2 / §15 karar 2: yakit bolgesi ust hucre sinirlariyla
       kirpilan cubuklar (karisik kafeste kesik konumdaki demetler). Her
       konumun modeldeki merkezinde (guc.cubuk_merkezi) hedef hucrenin
       dis siniri boyunca noktalar kurulan geometride yoklanir: noktalarin
       biri hedef hucrede degilse cubuk kesiktir. Kesik cubuklar F_dH ve
       F_q'ya girmez (tepe_faktorleri), ayrica sayilir. Merkezi hedef
       hucreye dusmeyen konum (donmus ust hucre) karar verilemez sayilir,
       kesik isaretlenmez.
================================================================================
"""

import math

KESIK_YOKLAMA_SINIRI = 30000     # bundan cok cubukta yoklama atlanir (sure)
_NOKTA_SAYISI = 8
_ICERI = 0.999                  # sinir noktalari yaricapin bu kesrinde


def _bos_dilimler(konumlar, eksenel_dilim):
    """
    Hicbir cubukta skor olmayan eksenel dilimler (toplam tam 0). Hedef cubuk
    kesintili katmanlardaysa (1. ve 3. katmanda var, 2.'de yok) guc mesh'i
    cubuk_eksenel_aralik ile ilk ve son katmanin arasini kapsar; aradaki
    katmanin dilimleri BOSTUR. Ortalamaya girerlerse F_q yapay siser.
    """
    return [i for i in range(eksenel_dilim)
            if sum(k["eksenel"][i][0] for k in konumlar.values()) == 0.0]


def _eksenel_faktorler(sonuc, konumlar, eksenel_dilim):
    """F_q, sicak dilim, bagil eksenel harita ve eksenel profil (3B).
    Bos dilimler (bkz. _bos_dilimler) ortalamalara katilmaz; bos dilim
    yoksa sonuc eskisiyle bit duzeyinde aynidir."""
    bos = _bos_dilimler(konumlar, eksenel_dilim)
    dolu = set(range(eksenel_dilim)) - set(bos)
    hepsi = []
    for a, k in konumlar.items():
        for i, d in enumerate(k["eksenel"]):
            if i in dolu:
                hepsi.append((a, i, d[0], d[1]))
    ort_yerel = sum(h[2] for h in hepsi) / len(hepsi) if hepsi else 0.0
    sicak = max(hepsi, key=lambda h: h[2]) if hepsi else (None, None, 0.0, 0.0)
    f_q = sicak[2] / ort_yerel if ort_yerel > 0 else None
    sonuc["F_q"] = f_q
    sonuc["F_q_sapma"] = (f_q * sicak[3] / sicak[2]) if (f_q and sicak[2]) else None
    sonuc["sicak_dilim"] = (sicak[0], sicak[1]) if f_q else None
    sonuc["ortalama_yerel"] = ort_yerel
    sonuc["bos_dilimler"] = bos
    sonuc["bagil_eksenel"] = {
        a: [(d[0] / ort_yerel, d[1] / ort_yerel) for d in k["eksenel"]]
        for a, k in konumlar.items()} if ort_yerel > 0 else None
    # eksenel guc profili (tum cubuklar toplanarak)
    profil = []
    for i in range(eksenel_dilim):
        t = sum(k["eksenel"][i][0] for k in konumlar.values())
        s = math.sqrt(sum(k["eksenel"][i][1] ** 2 for k in konumlar.values()))
        profil.append((t, s))
    dolu_profil = [p for i, p in enumerate(profil) if i in dolu]
    ort_profil = sum(p[0] for p in dolu_profil) / len(dolu_profil) if dolu_profil else 0.0
    sonuc["eksenel_profil"] = [(p[0] / ort_profil, p[1] / ort_profil)
                               for p in profil] if ort_profil > 0 else None


def _yaricap(hucre):
    """Hedef hucrenin dis yaricapi (ZCylinder -r ya da sinir kutusu yarisi)."""
    import openmc
    bolge = hucre.region
    uzaylar = [bolge] if isinstance(bolge, openmc.Halfspace) else list(
        bolge) if isinstance(bolge, openmc.Intersection) else []
    for u in uzaylar:
        if isinstance(u, openmc.Halfspace) and u.side == "-" and \
                isinstance(u.surface, openmc.ZCylinder):
            return float(u.surface.r)
    try:
        alt, ust = bolge.bounding_box
        return 0.5 * min(float(ust[0] - alt[0]), float(ust[1] - alt[1]))
    except (AttributeError, TypeError, ValueError):
        return None


def _yol(geometri, p):
    """(hucre kimlikleri, kafes adlari) -- noktanin kurulan geometrideki yolu; ya da None."""
    import numpy as np
    from cekirdek.geometri.yoklama import _iceren_hucreler, _yerel
    from cekirdek.guc_kor import kafes_adi
    evren, hucreler, kafesler = geometri.root_universe, [], []
    for _d in range(60):
        icerenler = _iceren_hucreler(evren, p)
        if len(icerenler) != 1:
            return None
        h = icerenler[0]
        hucreler.append(h.id)
        if h.fill_type == "universe":
            p, evren = _yerel(h, p), h.fill
        elif h.fill_type == "lattice":
            kafes = h.fill
            kafesler.append(kafes_adi(kafes))
            idx, p = kafes.find_element(_yerel(h, np.asarray(p, dtype=float)))
            evren = kafes.get_universe(idx) if kafes.is_valid_index(idx) else kafes.outer
            if evren is None:
                return None
        else:
            return hucreler, kafesler
    return None


def _beklenen_adlar(anahtar):
    """Anahtarin karisik duzey parcalarindaki kafes adlari (sirali)."""
    parcalar = anahtar if isinstance(anahtar, tuple) and anahtar and \
        isinstance(anahtar[0], tuple) else ()
    return [p[0] for p in parcalar if p and isinstance(p[0], str) and len(p) == 3]


def kesik_cubuklar(dagilim, geometri, hedef_hucreler, z=0.0):
    """
    Kesik ya da gizli cubuk anahtarlari (liste). hedef_hucreler: {hucre kimligi}.
    Kesik: yakit sinirindaki noktalardan biri baska yola duser. Gizli: merkez
    bu ornegin kafesinde degil (karisik duzeyde kafes adi tutmaz: konum ust
    bolgeyle tamamen oyulmus, orneğin skoru sifirdir).
    """
    import numpy as np
    from cekirdek.guc import cubuk_merkezi
    konumlar = dagilim.get("konumlar") or {}
    if not dagilim.get("tam_kor") or len(konumlar) > KESIK_YOKLAMA_SINIRI:
        return []
    hucreler = geometri.get_all_cells()
    yaricaplar = {k: _yaricap(hucreler[k]) for k in hedef_hucreler if k in hucreler}
    kesikler = []
    for anahtar in konumlar:
        cx, cy = cubuk_merkezi(dagilim, anahtar)
        merkez = _yol(geometri, np.array([cx, cy, z]))
        if merkez is None or merkez[0][-1] not in yaricaplar or not yaricaplar[merkez[0][-1]]:
            continue
        beklenen = _beklenen_adlar(anahtar)
        if beklenen and [a for a in merkez[1] if a in beklenen] != beklenen:
            kesikler.append(anahtar)
            continue
        r = yaricaplar[merkez[0][-1]]
        for i in range(_NOKTA_SAYISI):
            a = 2.0 * math.pi * i / _NOKTA_SAYISI
            y = _yol(geometri, np.array([cx + _ICERI * r * math.cos(a),
                                         cy + _ICERI * r * math.sin(a), z]))
            if y is None or y[0] != merkez[0]:
                kesikler.append(anahtar)
                break
    return kesikler


def kesikler(dagilim, geometri, taller, notlar):
    """Kesik (kirpilan) cubuklar (guc_faktor.kesik_cubuklar); F_dH disinda kalir."""
    import openmc
    from cekirdek import guc_kor as _guc_kor
    from cekirdek.ceviri import _
    # Yalniz karisik/yerlesim duzeyli (agac modu) modellerde: yoklama cubuk basina
    # ~0.6 ms (olculdu, 20856 cubuk 13 s); sablon modelleri kesik uretmez.
    if not any(isinstance(k, (_guc_kor.KarisikDuzey, _guc_kor.YerlesimDuzeyi))
               for k in dagilim.get("kafesler") or ()):
        return []
    hedef, z = set(), 0.0
    for tal in taller:
        for f in tal.filters:
            if isinstance(f, openmc.DistribcellFilter):
                hedef |= {int(getattr(b, "id", b)) for b in f.bins}
            elif isinstance(f, openmc.MeshFilter):
                z = 0.5 * (float(f.mesh.lower_left[2]) + float(f.mesh.upper_right[2]))
    kesik = kesik_cubuklar(dagilim, geometri, hedef, z)
    if kesik:
        notlar.append(_("%d kesik çubuk (yakıt bölgesi üst hücre sınırıyla kırpılıyor) "
                        "F_ΔH ve F_q dışında tutuldu.") % len(kesik))
    return kesik
