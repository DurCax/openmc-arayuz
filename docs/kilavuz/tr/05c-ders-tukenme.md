<a id="ders-tukenme-genisletme"></a>
## 5.17 Tükenme genişletmeleri: soğuma, bozunma ısısı ve kritik bor

**Örnek dosya:** `ornekler/pwr_tukenme.json` · **Seviye:** ileri · **Tahmini süre:** 30 dakika
(küçük istatistikle koşular birkaç dakika)

**Amaç.** Yanmadan sonra yakıtın bozunma ısısının ve aktivitesinin nasıl azaldığını görmek,
entegratör seçiminin sonuca etkisini küçük bir örnekte ölçmek ve tükenme boyunca kritik
bor derişiminin nasıl değiştiğini izlemek. Alanlar:
[4.9.1 Tükenme genişletmeleri](04i2-tukenme-genisletme.md#tukenme-genisletme).

**Adımlar.**

1. `ornekler/pwr_tukenme.json`'u açın. **Hesap ayarları**'nda parçacık 1000, çevrim 15,
   pasif 5 yapın (ders için; sonuçlar gürültülüdür). **Tükenme** sekmesinde tükenmeyi
   açın, **Adımlar** = `1, 5`, Gelişmiş › **Zincir** = **ENDF/B-VIII.0 termal** (aktivasyon
   ürünleri için tam zincir), **Entegratör** = **CE/CM**.
2. **Soğuma.** Gelişmiş › **Soğuma adımları** = `1, 10, 100, 1000`, **Soğuma birimi** = gün.
   Adım özeti "4 soğuma adımı (transport yok)" der; transport sayısı 2 × 2 = 4'tür (son
   adım soğuma olduğundan son transport koşulmaz). **Tükenmeyi başlat**.
3. Sonuç tablosunda soğuma satırlarının k sütunu "—"dur ve yanma artmaz. **Aktivite,
   bozunma ısısı ve foton kaynağı** kartında **Hesapla**: bozunma ısısı ilk günde hızla,
   sonra yavaşça düşer (kısa ömürlü fisyon ürünleri önce söner). **Seri** = Aktivite [Bq]
   ve Foton kaynağı ile tekrarlayın; **Çıktıları CSV olarak dışa aktar**.
4. **Entegratör etkisi.** Soğumayı silin, **Entegratör** = **CE/LI**, aynı tohumla tekrar
   koşun. k'yi ve U-235'i CE/CM koşusuyla karşılaştırın (iki koşunun
   CSV'si). Fark istatistik gürültü düzeyindedir: bu kadar kısa adımlarda entegratörün
   mertebesi sonucu belirlemez.
5. **Sürdürme.** **Adımlar** = `1, 5, 10` yapın, **Kaldığı yerden sürdür**'ü açın ve
   başlatın: yalnız yeni adım koşulur, ilk iki satır değişmez.
6. **Kritik bor.** Sürdürmeyi kapatın, **Tükenme sırasında kritik arama** açık, **Arama
   türü** = Çözünmüş bor, **Hedef** = su, tahminler 500 ve 1500 ppm, sınır 0–5000, **k
   toleransı** 0.005. Başlatın: tabloda her adımın bulunan bor değeri ve k ≈ 1 görünür.

**Ne görmelisiniz (ölçüldü; k ve entegratör satırları `testler/test_y4_kosu.py`, CASL zinciri, 1000 parçacık × 10 aktif çevrim; bozunma ısısı satırları 300 × 6/2, `pwr_tukenme.json`, 40 W/gHM ile 1 gün yanma + 1 ve 10 gün soğuma, yöntem: predictor).**

| Büyüklük | Değer |
|---|---|
| Soğumada k | "—" (transport yok); yanma sabit |
| Bozunma ısısı (tam zincir: ENDF/B-VIII.0 termal) | 10.68 → 0.177 → 0.0140 W (1., 2., 12. gün; ağır metal kütlesi 4.26 g, güç 170 W; yani P'nin %6.3 → %0.10 → %0.008'i) |
| Bozunma ısısı (CASL zinciri) | 0.54 → 0.097 → 0.0139 W: **EOL'de ~20×, +1 günde ~1.8× eksik** (zincirin 228 nüklidinin yalnız 133'ünde bozunma enerjisi var); 12. günde iki zincir uyuşur |
| CE/CM − CE/LI | k farkı ~1100 pcm (birleşik 1σ ≈ 1000 pcm); 6 günde U-235 bağıl farkı 1.3e-5 (eşik yok) |
| Hızlı kip (MicroXS) − tam | U-235 bağıl farkı ~3e-6 (2 gün) |
| Kritik bor (taze pin) | ~3300 ppm: **sızıntısız sonsuz pin hücrenin** değeri (k∞ ≈ 1.36, yanabilir zehir yok); gerçek bir kor değeri değildir (PWR çevrim başı ~1000–1500 ppm). Adım k'si \|k − 1\| ≤ 0.005 + 3σ |

Not: adım 6'daki k toleransı 0.005 (500 pcm ≈ 33 ppm bor), kılavuzun varsayılanı 1e-3'tür (100 pcm); ders ayarında adım gürültüsü ~400 pcm olduğundan 1e-3 aramayı çok uzatırdı.

**Sorular.** (1) Soğumanın ilk gününde bozunma ısısı neden en hızlı düşer? (Tam zincirde 10.7 → 0.18 W, ~60×; Way–Wigner: P/P₀ ≈ 0.0622[t⁻⁰·² − (t+T)⁻⁰·²].) (2) CE/LI ile
CE/CM farkı adımlar uzadıkça nasıl değişir — 5 gün yerine 50 günlük bir adımla deneyin.
(3) Kritik bor tükenmeyle neden azalır? (4) Hızlı kip yüksek yanmada neden yanılır?

**Sınırlar.** Küçük istatistik dersi hızlandırmak içindir; tasarım değeri için parçacık
sayısını artırın. Atık sınıfı (10 CFR 61.55) ve temas doz hızı bilgi amaçlıdır, **sertifika
değildir**.
