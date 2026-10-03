<a id="ders-tukenme-bolme"></a>
## 5.20 Gd pininde halka bölme ve dal tablosu

**Örnek dosya:** `ornekler/bolme/pwr_gd_bolme.json` · **Seviye:** ileri · **Tahmini süre:** 40 dakika
(halka çalışması: bir koşu ~25 dakika, CASL zinciri, 2000 × 40 / 15 çevrim, 6 iş parçacığı; dal tablosu ~10 dakika) ·
**Başvuru:** [Bölge bölme kartı](04i3-tukenme-bolme.md#tukenme-bolme), [Dal tablosu kartı](04h4-dal-tablosu.md#dal)

**Amaç.** (1) Yanabilir zehirli (Gd) pinde **tek ortalama bileşimle yanmanın** Gd'nin tükenmesini
olduğundan hızlı gösterdiğini, halka sayısı arttıkça sonucun **yakınsadığını** ölçmek ve halka
türünü (eşit hacim / eşit kalınlık / dışa incelen) karşılaştırmak. (2) Bir tükenme sonucunun yanma
adımlarında **dal tablosu** (T_yakıt, C_bor) üretip tek değişkenli taramayla tutarlılığını görmek.

**Ön koşul.** [5.6 Tükenme](05-dersler.md#ders-tukenme), [5.17 Tükenme genişletmeleri](05c-ders-tukenme.md#ders-tukenme-genisletme).

**Adımlar.**

1. `ornekler/bolme/pwr_gd_bolme.json`'u açın (5×5 süper hücre, ortada UO₂ %2 + %8 Gd₂O₃ pelet, tek
   malzeme). **Tükenme** sayfasında **Bölge bölme** kartı **5 eşit hacimli halka** gösterir;
   önizlemede iç içe 5 halka, özet satırında **Ayrı tükenme malzemesi: 25 → 29** ve halka
   hacimlerinin toplamının analitik hacme eşitliği yazar (eski `pwr_gd_tukenme.json`'un elle
   yazılmış eşit alanlı halkalarıyla aynı yarıçaplar: 0.1832 / 0.2591 / 0.3173 / 0.3664 / 0.4096 cm).
2. **Parçacık / çevrim** 2000, 40 çevrim, 15 pasif; **Gelişmiş › Zincir** = CASL termal; entegratör CE/CM,
   adımlar 0.02, 0.08, 0.4, 0.5, 1, 1, 1, 1, 1 MWd/kg. **Tükenmeyi başlat**.
3. Halka sayısını 1 (bölme kapalı), 2, 3, 5, 8 yapıp tekrar koşun; 5 halkayı **eşit kalınlık** ve
   **dışa incelen** türleriyle de koşun. Her koşuda **izlenen nüklidlerden** Gd-157'yi seçip
   Gd'li pinin bütün halkalarının toplamını alın (sonuç CSV'sinde malzeme adı `uo2_gd #i`).
4. **Analiz** sayfasında **Dal tablosu** kartı: **Tükenme adımı seçimi**nden 0 ve 2. noktayı
   işaretleyin; **Yakıt sıcaklığı** 900, **Çözünmüş bor** 500, **Birleşim** = her değişken tek
   başına → **Dal tablosunu hesapla**. Taban dal ile Δk'yı okuyun.

**Beklenen sonuç** (CASL, 2000 × 40 / 15, tohum 7; k için σ ≈ 0.004 = 400 pcm):

| Yanma (MWd/kg) → | Gd-157 kalan oranı | | | | k (6 MWd/kg) |
|---|---|---|---|---|---|
| Koşu | 1 | 3 | 5 | 6 | |
| 1 halka (bölmesiz) | 0.833 | 0.540 | 0.296 | 0.198 | 1.0551 |
| 2 halka, eşit hacim | 0.833 | 0.551 | 0.349 | 0.273 | 1.0616 |
| 3 halka, eşit hacim | 0.836 | 0.571 | 0.377 | 0.295 | 1.0580 |
| 5 halka, eşit hacim | 0.833 | 0.574 | 0.387 | 0.309 | 1.0543 |
| 8 halka, eşit hacim | 0.838 | 0.591 | 0.394 | 0.313 | 1.0586 |
| 5 halka, eşit kalınlık | 0.832 | 0.561 | 0.364 | 0.291 | 1.0562 |
| 5 halka, dışa incelen (0.6) | 0.840 | 0.590 | 0.390 | 0.312 | 1.0591 |

Dal tablosu (pin hücre `pwr_tukenme.json`, 3000 × 30 / 10, ölçüm testi `test_y5_dal.py`): taban
k = 1.3643 ± 0.0056 (adım 0) ve 1.3102 ± 0.0029 (5 MWd/kg); T_yakıt = 900 K'de Δk = −3071 ± 670 pcm
ve −2706 ± 536 pcm; bor 500 ppm'de −7484 ± 695 pcm ve −7189 ± 470 pcm.

**Neden?**

- **Ortalama bileşim Gd'yi hızlı yakar.** Bölmesiz pinde dışarıda soğurulan nötron iç kısmı da
  "yakmış" sayılır; gerçekte dış kabuk iç kısmı perdeler (kendinden perdeleme). 6 MWd/kg'da bölmesiz
  koşu Gd-157'nin %19.8'ini bırakırken halkalı koşular %29–31'ini bırakır (ağır soğurucuda ~%35
  görece fark). Sayı 3 → 5 → 8 halkada 0.295 → 0.309 → 0.313 olarak yakınsar; 5 halka 8 halkadan
  istatistik gürültü içinde ayırt edilemez.
- **k(t) farkları istatistik düzeyindedir.** Bu küçük örnekte k, koşular arasında ±400 pcm içinde
  dalgalanır; Gd-157 kalan oranı ise (güç ve normalizasyon aynı olduğundan) çok daha az gürültülüdür.
  k(t) üzerindeki halka etkisini görmek için parçacık sayısını artırın (eşik konmaz).
- **Halka türü.** Eşit hacim, eşit kalınlık ve dışa incelen türler 5 halkada Gd eğrisini %1–3 içinde
  verir; eşit kalınlıkta dış halka büyük hacimlidir ve en az incelen çözüm olduğundan eşit hacim
  önerilir (kaynak: Serpent `div`/CASMO uygulamaları).
- **Dal tablosu ile tarama tutarlıdır.** Adım 0 dalı aynı koşuldaki tek değişkenli taramayla
  (T_yakıt = 900 K: 1.3336 ± 0.0037 ve 1.3392 ± 0.0035; bor 500 ppm: 1.2895 ± 0.0042 ve
  1.2810 ± 0.0038) 2σ içinde aynı; taban dal tükenmenin k'sıyla (1.3643 / 1.3621; 1.3102 / 1.3007)
  2σ içindedir. Bor değeri ≈ −15 pcm/ppm (taze, sonsuz pin hücre) yanmayla az değişir.

**Sorular.**

1. Gd-157 kalan oranının 8 halkada hâlâ biraz artması ne anlama gelir? Yakınsama ölçütünüz ne olurdu?
2. Dal tablosunda bor değeri neden yanmayla küçülür? (İpucu: Gd-157 ve U-235 azalır, spektrum sertleşir.)
3. Aynı örnekte yalnız `gd_cubugu`'nun halkalarını 2 yapıp `yakit_cubugu`'nu bölerseniz ne beklersiniz?
