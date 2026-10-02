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
6. **Kritik bor.** Sürdürmeyi kapatın, **Tükenme sırasında kritiklik araması** açık, **Arama
   türü** = Çözünmüş bor, **Hedef** = su, tahminler 500 ve 1500 ppm, sınır 0–5000, **k
   toleransı** 0.005. Başlatın: tabloda her adımın bulunan bor değeri ve k ≈ 1 görünür.

**Ne görmelisiniz (ölçüldü, `testler/test_y4_kosu.py`, CASL zinciri, 1000 parçacık × 10 aktif çevrim).**

| Büyüklük | Değer |
|---|---|
| Soğumada k | "—" (transport yok); yanma sabit |
| Bozunma ısısı | 1 gün yanmadan sonra azalır: 0.53 → 0.095 → 0.014 W (1 cm pin; 1, 2, 12. gün) |
| CE/CM − CE/LI | birkaç yüz pcm'e kadar fark, 1σ ≈ 500 pcm düzeyinde (eşik yok) |
| Hızlı kip (MicroXS) − tam | U-235 bağıl farkı ~3e-6 (2 gün) |
| Kritik bor (taze pin) | ~3300 ppm; adım k'si \|k − 1\| ≤ 0.005 + 3σ |

**Sorular.** (1) Soğumanın ilk gününde bozunma ısısı neden en hızlı düşer? (2) CE/LI ile
CE/CM farkı adımlar uzadıkça nasıl değişir — 5 gün yerine 50 günlük bir adımla deneyin.
(3) Kritik bor tükenmeyle neden azalır? (4) Hızlı kip yüksek yanmada neden yanılır?

**Sınırlar.** Küçük istatistik dersi hızlandırmak içindir; tasarım değeri için parçacık
sayısını artırın. Atık sınıfı (10 CFR 61.55) ve temas doz hızı bilgi amaçlıdır, **sertifika
değildir**.
