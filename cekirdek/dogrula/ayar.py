# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/ayar.py  --  4. hesap ayarlari kontrolleri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.dogrula._ortak import Bulgu
from cekirdek.ceviri import _


def ayar_kontrol(spec):
    """Cevrim/parcacik sayilari ve kaynak tanimi."""
    bulgular = []
    a = spec["ayarlar"]
    cevrim = a.get("cevrim", 0)
    pasif = a.get("pasif", 0)
    parcacik = a.get("parcacik", 0)

    if parcacik <= 0:
        bulgular.append(Bulgu("hata", "ayarlar", _("parçacık sayısı sıfırdan büyük olmalı")))
    if cevrim <= 0:
        bulgular.append(Bulgu("hata", "ayarlar", _("çevrim sayısı sıfırdan büyük olmalı")))
    if a.get("mod") == "eigenvalue":
        if pasif >= cevrim:
            bulgular.append(Bulgu(
                "hata", "ayarlar",
                _("pasif çevrim (%d) toplam çevrimden (%d) az olmalı") % (pasif, cevrim)))
        elif pasif < 5:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                _("pasif çevrim çok az (%d) — kaynak dağılımı yakınsamamış olabilir") % pasif,
                _("Tipik olarak en az 20–50 pasif çevrim kullanılır.")))
        elif cevrim - pasif < 20:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                _("aktif çevrim sayısı az (%d) — istatistik zayıf kalır") % (cevrim - pasif)))
        ent = a.get("entropi_mesh") or {}
        if not ent.get("var"):
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                _("Shannon entropisi kapalı — kaynak dağılımının yakınsayıp "
                "yakınsamadığı ölçülemez"),
                _("Yakınsamamış kaynak k-eff'i yanlı tahmin ettirir ve bu başka "
                "türlü fark edilmez. Özdeğer hesaplarında açık tutun.")))
        elif any(n <= 0 for n in (ent.get("boyut") or [0])):
            bulgular.append(Bulgu("hata", "ayarlar",
                                  _("entropi ağı boyutları sıfırdan büyük olmalı")))
        if parcacik < 1000:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                _("çevrim başına parçacık az (%d) — kaynak yakınsaması bozulabilir") % parcacik))
    return bulgular
