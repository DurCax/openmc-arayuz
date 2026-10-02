# -*- coding: utf-8 -*-
"""
kosucu_terminal.py -- `python -m cekirdek.kosucu` komut satiri (kosucu._terminal)

cekirdek/kosucu.py 800 satir sinirini astigi icin YALNIZ TASINDI (v3 T2);
davranis aynidir. kosucu'nun islevleri `_k.<ad>` ile cagrilir: testler ve
cagiranlar kosucu.calistir / kosucu.sonuc_oku'yu degistirdiginde (eski
davranis) bu govde de degisikligi gorur. Genel giris yine kosucu._terminal.

terminal() ~170 satirdir (islev < 50 satir kuralinin istisnasi): tasima
sirasinda davranisi korumak icin bolunmedi; adim adim (dogrulama, kosu,
sonuc) ayri islevlere ayirmak sonraki bir is.
"""

import os
import sys

from cekirdek import sema, dogrula
from cekirdek import kaynak as _kaynak
from cekirdek import kapsul as _kapsul
from cekirdek import kosucu as _k
from cekirdek.ceviri import _
from cekirdek.uygunluk_denetimi import ayristir as _ayristir


def terminal(argv):
    if not argv or argv[0] in ("-h", "--yardim", "--help"):
        print(_k.__doc__)
        return 0
    if argv[0] == "yeniden":
        return _kapsul.yeniden_komutu(argv[1:])

    spec_yolu = argv[0]
    dizin = None
    is_parcacigi = None
    sadece_dogrula = False
    betik_yolu = None

    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--dizin":
            i += 1; dizin = argv[i]
        elif a in ("-s", "--is-parcacigi"):
            i += 1; is_parcacigi = int(argv[i])
        elif a == "--sadece-dogrula":
            sadece_dogrula = True
        elif a == "--betik":
            i += 1; betik_yolu = argv[i]
        else:
            print(_("bilinmeyen seçenek: %s") % a); return 2
        i += 1

    spec = sema.yukle(spec_yolu)
    print("=" * 74)
    print(" %s" % spec.get("ad", spec_yolu))
    print("=" * 74)

    # --- 1. dogrulama (tek kapi: dogrula.kapi) ---
    try:
        bulgular = dogrula.kapi(spec)
    except dogrula.DogrulamaHatasi as e:
        bulgular = e.tum_bulgular
        print(_("\n[1/3] Doğrulama: %s") % dogrula.ozet(bulgular))
        for b in bulgular:
            print("  %s" % b)
        print(_("\nHatalar giderilmeden koşu başlatılmaz (%s).") % e)
        return 1
    print(_("\n[1/3] Doğrulama: %s") % dogrula.ozet(bulgular))
    for b in bulgular:
        print("  %s" % b)

    # --- istege bagli betik uretimi ---
    if betik_yolu:
        from cekirdek import kod_uret
        kod = kod_uret.uret(spec, os.path.basename(betik_yolu))
        with open(betik_yolu, "w", encoding="utf-8") as f:
            f.write(kod)
        print(_("\n      betik yazıldı: %s (%d satır)") % (betik_yolu, len(kod.splitlines())))

    if sadece_dogrula:
        print(_("\n(--sadece-dogrula verildi; koşu atlandı)"))
        return 0

    # --- 2. kosu ---
    if dizin is None:
        dizin = os.path.join(os.path.dirname(os.path.abspath(spec_yolu)),
                             spec["calistirma"].get("dizin", "kosu"))
    print(_("\n[2/3] Koşu başlatılıyor → %s") % dizin)

    son_yazilan = [0]
    tty = sys.stdout.isatty()

    def ilerleme(satir, bilgi):
        # Terminalde tek satir guncellenir; cikti bir dosyaya/boruya yonlendirilmisse
        # \r ise yaramaz, her guncelleme ayri satira yazilir.
        if bilgi and bilgi["ortalama"] is not None:
            if bilgi["cevrim"] - son_yazilan[0] >= 10:
                son_yazilan[0] = bilgi["cevrim"]
                metin = (_("      çevrim %4d   k = %.5f ± %.5f")
                         % (bilgi["cevrim"], bilgi["ortalama"], bilgi["sapma"]))
                sys.stdout.write(("\r" + metin) if tty else (metin + "\n"))
                sys.stdout.flush()

    # spec yukarida dogrulandi: cift dogrulama yok
    sonuc = _k.calistir(spec, dizin, geri_cagir=ilerleme, is_parcacigi=is_parcacigi,
                     dogrulama=False)
    if tty:
        sys.stdout.write("\r" + " " * 60 + "\r")

    if not sonuc["basarili"]:
        print(_("      Koşu başarısız (çıkış kodu %d)") % sonuc["cikis_kodu"])
        print(_("      log: %s") % sonuc["log"])
        return 1
    print(_("      tamamlandı: %.1f s") % sonuc["sure"])
    for satir in _ayristir.ozet_satirlari(sonuc.get("cikti")):   # M5: sessiz kalmasin
        print("      %s" % satir)

    # --- 3. sonuc ---
    print(_("\n[3/3] Sonuçlar"))
    s = _k.sonuc_oku(sonuc["statepoint"])
    if s.get("keff") is None:
        # --- sabit kaynak: k-eff yok, sonuc tally'lerdir ---
        k_tanim = (spec["ayarlar"].get("kaynak") or {})
        kuvvet = float(k_tanim.get("kuvvet") or 1.0)
        print(_("      hesap    = sabit kaynak (k-eff tanımsız)"))
        print(_("      kaynak   = %s") % _kaynak.ozet(k_tanim))
        print(_("      şiddet   = %.4g parçacık/s") % kuvvet)
        print(_("      çevrim   = %d, %d parçacık/çevrim") % (s["cevrim"], s["parcacik"]))
        # OLCULDU: OpenMC sabit kaynak tally'lerini kaynak siddetiyle ZATEN
        # carpiyor (kuvvet=1 ve kuvvet=1e12 ile kosuldu, oran tam 1e12 cikti).
        # Bu yuzden kullaniciya "siddetle carpin" demek CIFT SAYIM olurdu.
        if kuvvet == 1.0:
            print(_("      Not: tally değerleri kaynak parçacığı başınadır"))
            print(_("           (şiddet 1 bırakıldı). Mutlak birim için şiddeti girin."))
        else:
            print(_("      Not: tally değerleri mutlak birimdedir — OpenMC kaynak"))
            print(_("           şiddetini zaten uygulamıştır, tekrar çarpmayın."))
            print(_("           reaksiyon hızları: 1/s"))
            print(_("           Dikkat: 'flux' skoru hacim üzerinden integrallidir (birim cm/s)."))
            print(_("           Nokta akısı [1/cm²/s] için bölgenin hacmine bölün."))
    else:
        print(_("      k-eff    = %.5f ± %.5f") % s["keff"])
        _kin = s.get("kinetik") or {}
        from cekirdek import uygunluk as _u
        _durum, _ayrinti = _k.keff_yorumu(s["keff"][0], s["keff"][1], _kin.get("beta_eff"),
                                       sonsuz=_u.sonsuz_ortam(spec))
        print(_("      durum    = %s") % _durum)
        print(_("                 %s") % _ayrinti)
        print(_("      çevrim   = %d (%d pasif), %d parçacık/çevrim")
              % (s["cevrim"], s["pasif"], s["parcacik"]))
    # Entropi yalnizca ozdeger modunda anlamlidir: sabit kaynakta kaynak
    # zaten sabittir, "yakinsamasi" diye bir sey yoktur.
    if s.get("keff") is not None:
        if s.get("entropi"):
            yakinsadi, mesaj = _k.entropi_yakinsama(s["entropi"], s["pasif"])
            isaret = {True: _("tamam"), False: _("uyarı"), None: "  ?  "}[yakinsadi]
            print(_("      yakınsama= [%s] %s") % (isaret, mesaj))
        elif s.get("entropi_hata"):
            print(_("      yakınsama= [  ?  ] %s")
                  % (_("Shannon entropisi okunamadı: %s") % s["entropi_hata"]))
        else:
            print(_("      yakınsama= [  ?  ] Shannon entropisi kapalı — kaynak "
                  "yakınsaması doğrulanamıyor"))
    kin = s.get("kinetik")
    if kin:
        print(_("      β_eff    = %.1f ± %.1f pcm") % (kin["beta_eff"] * 1e5,
                                                      kin["beta_eff_sapma"] * 1e5))
        print(_("      Λ        = %s") % _k.lambda_metni(kin["lambda"], kin["lambda_sapma"]))
    g = s.get("guc")
    if g and g.get("faktorler"):
        from cekirdek import geometri as _geometri, guc as _guc
        f = g["faktorler"]
        spec_g = spec.get("guc_dagilimi") or {}
        # Lineer guc [W/cm] HEDEF CUBUGUN bulundugu katmanlarin toplam
        # yuksekligine bolunur (kurucu.guc_yuksekligi): yansitici, plenum ve
        # blanket katmanlari paya girmez, paydaya da girmemeli.
        m = _guc.mutlak_guc(f, spec_g.get("toplam_guc"), _geometri.hedef_yuksekligi(spec),
                            hedef_payi=g.get("hedef_payi"))
        print(_("\n      --- güç dağılımı (%d çubuk, %d eksenel dilim) ---")
              % (f["cubuk_sayisi"], f["eksenel_dilim"]))
        for satir in _k.korunum_satirlari(g):
            print("      %s" % satir)
        for satir in _guc.yorumla(f, m, hedef_payi=g.get("hedef_payi"),
                                  hedef_payi_hata=g.get("hedef_payi_hata"),
                                  kategori=spec.get("kategori")):
            print("      %s" % satir)
    elif s.get("guc_hata"):
        print(_("\n      güç dağılımı okunamadı: %s") % s["guc_hata"])

    _kuvvet = float(((spec.get("ayarlar") or {}).get("kaynak") or {}).get("kuvvet") or 1.0)
    for ad, df in s["tallyler"].items():
        print("")
        print("      " + _k.tally_metni(ad, df, s.get("malzeme_adlari"), s.get("keff") is None,
                                     _kuvvet).replace("\n", "\n      "))
    print(_("\n      statepoint: %s") % sonuc["statepoint"])
    print(_("      log       : %s") % sonuc["log"])
    return 0
