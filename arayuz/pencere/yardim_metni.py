# -*- coding: utf-8 -*-
"""
 arayuz/pencere/yardim_metni.py  --  "Yardım ve terimler" diyalogunun metni

 menuler.py'den ayrildi (Dalga 3 / Ajan 12): metin parca parca N_() ile
 isaretlenir, yardim_html() etkin dilde birlestirir. YARDIM_HTML eski ad
 (kaynak dil, Turkce) -- `from arayuz.ana_pencere import YARDIM_HTML` calisir.
 Uzun anlatim kullanim kilavuzundadir (Yardim > Kullanim kilavuzu, F1).
"""

from cekirdek.ceviri import _, N_

_GIRIS = (
    N_("Yardım ve terimler"),
    N_("Nasıl ilerlenir?"),
    (N_("Yalnızca modelinize uyan sekmeler görünür. Sekme başlığındaki işaret "
        "durumu söyler: <b>!</b> düzeltilmesi gereken hata, <b>•</b> eksik adım, "
        "<b>✓</b> tamam. İşaretin üzerine gelince ne yapmanız gerektiği yazar; alttaki "
        "durum çubuğu da sıradaki adımı söyler. Kor türünü üstteki "
        "<b>Türü değiştir…</b> düğmesiyle değiştirebilirsiniz."),
     N_("<b>Önce çiz, sonra çalıştır:</b> geometri önizlemesi başarıyla "
        "çizilmeden ve doğrulama hataları giderilmeden koşu başlamaz; ÇALIŞTIR'a basarsanız "
        "önce neyin eksik olduğu söylenir."),
     N_("Ayrıntılı anlatım, rehberli dersler ve sorun giderme için "
        "<b>Yardım &gt; Kullanım kılavuzu</b> (F1) açılır; her sayfanın başlığındaki "
        "<b>?</b> düğmesi kılavuzun o bölümüne gider.")),
)

# (bolum basligi, ((terim, aciklama), ...)) -- terim ve aciklama ayri msgid.
_TABLOLAR = (
    (N_("Temel büyüklükler"), (
        ("k-eff", N_("Çoğalma çarpanı. Bir nötron neslinin bir sonraki nesli ne kadar "
                     "büyüttüğü. k&gt;1 güç artar, k=1 kritik, k&lt;1 söner.")),
        ("k&infin; (k-inf)", N_("Sonsuz ortam çoğalma çarpanı. Sınırlardan sızıntı olmadığı "
                                "varsayılır (yansıtıcı sınır koşulu). Gerçek bir reaktör için "
                                "üst sınırdır.")),
        (N_("Reaktivite (&rho;)"), N_("(k-1)/k. Kritiklikten ne kadar uzak olunduğunun "
                                      "ölçüsü. <b>pcm</b> = 10<sup>-5</sup> birim.")),
        (N_("Dolar ($)"), N_("Reaktivite / &beta;<sub>eff</sub>. 1 $ üstü geçici rejimde "
                             "anlık kritiklik demektir.")),
        ("&beta;<sub>eff</sub>", N_("Etkin gecikmiş nötron kesri. Fisyon nötronlarının küçük "
                                    "bir kısmı (~%0.7) gecikmeli çıkar; reaktör denetimi bu "
                                    "gecikmeye dayanır.")),
        ("&Lambda;", N_("Nötron üretim zamanı. Termal reaktörde ~20 &mu;s, hızlı metal "
                        "sistemde ~6 ns.")),
    )),
    (N_("Reaktivite katsayıları (Analiz sekmesi)"), (
        (N_("Doppler katsayısı"), N_(
            "Yakıt sıcaklığı arttığında reaktivite değişimi [pcm/K]. U-238 rezonansları "
            "genişler, yakalama artar &rarr; <b>negatif</b> olmalı. Güvenliğin ilk savunma "
            "hattıdır: güç artarsa yakıt ısınır ve reaktivite kendiliğinden düşer.")),
        (N_("Moderatör sıcaklık katsayısı"), N_(
            "Soğutucu sıcaklığı arttığında reaktivite değişimi [pcm/K]. Sıcaklık artınca "
            "yoğunluk da düşer; ikisi birlikte hesaplanmalıdır. Termal reaktörde "
            "<b>negatif</b> olmalı.")),
        (N_("Boşluk (void) katsayısı"), N_(
            "Soğutucuda boşluk oluşursa reaktivite değişimi [pcm/%void]. Termal reaktörde "
            "negatif olmalı.")),
        (N_("Bor değeri (worth)"), N_(
            "Suda çözünmüş bor başına reaktivite [pcm/ppm]. Bor nötron emicidir &rarr; "
            "negatif. Çok bor, moderatör sıcaklık katsayısını pozitife doğru iter; bu yüzden "
            "sınırlanır.")),
    )),
    (N_("Monte Carlo terimleri"), (
        (N_("Çevrim (batch)"), N_("Bir grup nötronun izlendiği tur.")),
        (N_("Pasif çevrim"), N_(
            "Baştaki çevrimler. Kaynak dağılımı henüz doğru değildir, bu yüzden istatistiğe "
            "<b>katılmaz</b>. Tipik 20–50.")),
        (N_("Aktif çevrim"), N_(
            "Pasif çevrimlerden sonraki çevrimler; k-eff ve tally sonuçları yalnızca "
            "bunlardan hesaplanır.")),
        (N_("Shannon entropisi"), N_(
            "Kaynak dağılımının ne kadar yayıldığını ölçer. Pasif çevrimler boyunca "
            "düzleşmelidir; hâlâ kayıyorsa pasif çevrim sayısı yetersizdir ve k-eff "
            "<b>yanlı</b> çıkar.")),
        (N_("Tally (ölçüm)"), N_(
            "Sayaç. Modelin belirli bir yerinde/enerjisinde hangi reaksiyonların kaç kez "
            "olduğunu toplar (akı, fisyon, soğurma…).")),
        (N_("k-eff ve k&infin;"), N_(
            "Çoğaltma katsayısı. Bütün dış sınırlar yansıtıcı (sızıntısız) ise sonuç "
            "<b>k&infin;</b>'dur: sonsuz tekrarlanan ortamın katsayısı. k&infin; &gt; 1 "
            "reaktörün süperkritik olduğunu değil, yakıtın reaktivite fazlası taşıdığını "
            "söyler; sonlu bir korda sızıntı yüzünden k-eff daha küçüktür.")),
        (N_("Sabit kaynak"), N_(
            "Fisyon zinciri yerine dışarıdan verilen bir kaynağın (ör. D-T füzyon, 14.1 MeV) "
            "nötronları izlenir; k-eff tanımsızdır. Kaynak şiddeti [1/s] girilirse sonuçlar "
            "mutlak birimdedir (OpenMC şiddeti kendisi uygular).")),
        (N_("Akı (flux)"), N_(
            "OpenMC'nin akı tally'si hücre hacmi üzerinden integrallidir: birimi "
            "n&middot;cm/s (ya da kaynak nötronu başına n&middot;cm). Ortalama akı "
            "[n/cm²/s] için bölgenin hacmine bölün. Arayüz <b>doz</b> hesaplamaz; doz için "
            "akı–doz dönüşüm katsayıları (ör. ICRP-116) gerekir.")),
        (N_("F<sub>&Delta;H</sub> ve F<sub>q</sub>"), N_(
            "Güç tepe faktörleri: en yüksek çubuk gücü / ortalama (radyal) ve en yüksek yerel "
            "güç yoğunluğu / ortalama (3B). Az parçacıkla F<sub>&Delta;H</sub> istatistik "
            "gürültüsüyle <b>yukarı</b> yanlıdır; güvenilir değer için Normal ya da Hassas "
            "hassasiyet kullanın.")),
        ("S(&alpha;,&beta;)", N_(
            "Termal saçılma verisi. Düşük enerjide nötron serbest bir çekirdekten değil, "
            "<b>bağlı</b> bir molekülden saçılır (sudaki hidrojen gibi). Unutulursa termal "
            "reaktörde k yüzde mertebesinde kayar.")),
    )),
    (N_("Geometri terimleri"), (
        (N_("Çubuk (pin, rod)"), N_(
            "Eş merkezli bölgelerden oluşan yakıt, kontrol ya da boş kanal çubuğu: yakıt, "
            "yakıt-zarf aralığı, zarf ve çevresindeki soğutucu.")),
        (N_("Plaka elemanı"), N_(
            "Araştırma reaktörlerindeki (MTR) düz plakalı yakıt elemanı.")),
        (N_("Demet (fuel assembly)"), N_(
            "Çubukların kare ya da altıgen ızgarada düzenli dizilimi (OpenMC'de kafes, "
            "<i>lattice</i>). Kare (PWR) ya da altıgen (VVER, SFR).")),
        (N_("Kor ve kor haritası"), N_(
            "Demetlerin yerleşimi. Kor haritası her konuma hangi demetin geldiğini gösterir.")),
        (N_("Yansıtıcı kuşak (reflector)"), N_(
            "Koru saran, kaçan nötronları geri gönderen malzeme katmanı.")),
        (N_("Kontrol tamburu"), N_(
            "Yansıtıcı kuşağa gömülü, bir yüzü emici kaplı dönen silindir. Emici kora "
            "döndükçe reaktivite düşer.")),
        (N_("Eksenel katman"), N_(
            "Koru yükseklik boyunca bölen katmanlar (alt/üst yansıtıcı, örtü, farklı "
            "zenginlikte yakıt).")),
        (N_("Adım (pitch)"), N_("Komşu iki hücre merkezi arası mesafe.")),
        ("Universe", N_(
            "OpenMC'de tekrar kullanılabilir geometri parçası. Her çubuk bir universe'tür; "
            "demet onu tekrarlar.")),
        (N_("Sınır koşulu"), N_(
            "<b>Vakum (vacuum)</b>: nötron kaçar (gerçek dış yüzey). <b>Yansıtıcı "
            "(reflective)</b>: aynadaki gibi geri yansır (sonsuz tekrar varsayımı). "
            "<b>Beyaz (white)</b>: rastgele yönde geri döner. <b>Periyodik (periodic)</b>: "
            "karşı yüzden geri girer.")),
    )),
    (N_("Tükenme terimleri"), (
        (N_("Tükenme (depletion)"), N_(
            "Yakıttaki nüklidlerin zamanla değişmesi: fisil çekirdekler azalır, fisyon "
            "ürünleri ve aktinitler birikir.")),
        (N_("Yanma (burnup)"), N_(
            "Birim ağır metal kütlesi başına üretilen enerji [MWd/kg].")),
        (N_("Zincir (chain)"), N_(
            "Bozunma ve reaksiyon yollarını tanımlayan veri dosyası; termal ve hızlı spektrum "
            "için ayrı zincirler vardır.")),
        (N_("Güç yoğunluğu"), N_("Ağır metal gramı başına güç [W/gHM].")),
    )),
)


# Cevrilmeyen terimler (sembol / OpenMC adi): _() ile aranmaz.
_SEMBOLLER = frozenset({"k-eff", "k&infin; (k-inf)", "&beta;<sub>eff</sub>", "&Lambda;",
                        "S(&alpha;,&beta;)", "Universe"})


def yardim_html(cevir=None):
    """Yardim diyalogunun HTML'i; cevir=None -> etkin dil (_)."""
    ceviri = _ if cevir is None else cevir

    def c(metin):
        return metin if metin in _SEMBOLLER else ceviri(metin)
    baslik, alt, paragraflar = _GIRIS
    parca = ["<h2>%s</h2>" % c(baslik), "<h3>%s</h3>" % c(alt)]
    parca += ["<p>%s</p>" % c(p) for p in paragraflar]
    for bolum, satirlar in _TABLOLAR:
        parca.append("<h3>%s</h3>\n<table cellpadding=\"5\">" % c(bolum))
        for terim, aciklama in satirlar:
            parca.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (c(terim), c(aciklama)))
        parca.append("</table>")
    return "\n".join(parca)


# Eski ad: kaynak dildeki (Turkce) metin.
YARDIM_HTML = yardim_html(cevir=lambda s: s)
