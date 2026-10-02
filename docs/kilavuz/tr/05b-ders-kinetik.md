<a id="ders-kinetik"></a>
## 5.12 Nokta kinetiği: gecikmeli nötronlar ve periyot

**Örnek dosya:** `ornekler/godiva_kriter.json` · **Seviye:** orta · **Tahmini süre:** 15 dakika
(Godiva koşusu yaklaşık 1 dakika)

**Amaç.** Gecikmeli nötronların reaktör denetimini neden mümkün kıldığını görmek: aynı
reaktivite bir termal ve bir hızlı sistemde hangi periyodu verir, ani kritikte ne değişir, negatif
sıcaklık katsayısı bir güç patlamasını nasıl durdurur. Yöntem ve alanlar:
[nokta kinetiği kartı](04h2-kinetik.md#kinetik).

**Adımlar.**

1. **Ders kitabı verisi.** Herhangi bir projede **Analiz** sayfasına gidin; en alttaki **Nokta
   kinetiği** kartında **Veri kaynağı** = **Keepin U-235 termal (6 grup)**, **Üretim zamanı Λ**
   = 20 μs. **Reaktivite türü** **Basamak**, **Birim** **pcm**, **Reaktivite** 100, **Benzetim
   süresi** 100 s → **Hesapla**.
2. Aynı veride **Reaktivite** 200 pcm, sonra −100 pcm ile tekrarlayın.
3. **Birim** = **$**, **Reaktivite** 0.5, **Benzetim süresi** 1 s: güç ilk milisaniyelerde bir
   **ani sıçrama** yapar, sonra yavaş artar.
4. **Reaktivite** 1.2 $: kart **ANİ KRİTİK** uyarısı yazar ve P/P₀ 10¹⁰'u aşınca çözüm durur.
5. **Geri besleme.** **Reaktivite** 200 pcm, **Benzetim süresi** 50 s; **Adiyabatik sıcaklık
   geri beslemesi** açık, **α_T** −2 pcm/K, **Isı kapasitesi C** 10⁶ J/K, **Başlangıç gücü P₀**
   10⁶ W → **Hesapla**.
6. **Koşudan veri.** `ornekler/godiva_kriter.json`'u açın (kinetik parametreler açıktır).
   **Hesap ayarları** > Gelişmiş > **Gecikmeli nötron grupları** = **6 grup (ENDF/B)** olduğunu
   denetleyin ve **Çalıştır**'da koşun. Sonra **Analiz** > **Nokta kinetiği** > **Son koşudan al**:
   tablo IFP β_i ve λ_i ile, Λ kutusu koşunun Λ'sıyla dolar. **Birim** $, **Reaktivite** 0.1 →
   **Hesapla**.

**Beklenen sonuç.**

| Adım | Veri | ρ | Inhour kararlı periyot | Not |
|---|---|---|---|---|
| 1 | Keepin, Λ = 20 μs | 100 pcm (0.154 $) | **54.92 s** | 100 s'de çözümden ölçülen 54.79 s: en uzun ömürlü grubun geçişi henüz tam sönmedi |
| 2 | Keepin | 200 pcm | **17.33 s** | — |
| 2 | Keepin | −100 pcm | **−130 s** | negatif periyot −1/λ_1 ≈ −81 s'den kısa olamaz |
| 3 | Keepin | 0.5 $ | 5.73 s | 0.1 s'de P/P₀ = 2.07 ≈ β/(β − ρ) = 2 (ani sıçrama) |
| 5 | Keepin + α_T = −2 pcm/K | 200 pcm | — | güç ≈ 21 s'de 3.0 P₀ tepe yapar; 50 s'de ΔT = 127 K, toplam ρ = −54 pcm, P = 1.97 P₀ |
| 6 | Keepin, Λ = 20 μs | 0.1 $ | **98.6 s** | aynı reaktivitede termal karşılaştırma |
| 6 | Godiva, IFP 6 grup | 0.1 $ | **83.8 s** | β_eff = 680.7 ± 24.5 pcm, Λ = 5.62 ns |

Godiva koşusundan okunan gruplar (ENDF/B-VIII.0, 20 000 parçacık × 120 aktif çevrim):

| Grup | β_i [pcm] | λ_i [1/s] | ENDF/B-VIII.0 U-235 λ_i |
|---|---|---|---|
| 1 | 29.8 ± 5.1 | 0.01334 | 0.01334 |
| 2 | 119.1 ± 9.5 | 0.03273 | 0.03274 |
| 3 | 111.7 ± 9.5 | 0.12083 | 0.12078 |
| 4 | 281.0 ± 15.8 | 0.30320 | 0.30278 |
| 5 | 94.7 ± 10.3 | 0.85132 | 0.84949 |
| 6 | 44.5 ± 6.1 | 2.85853 | 2.85300 |

**Deneyle karşılaştırma (temkinli).** Godiva'nın deneysel β_eff'i 645 ± 13 pcm olarak verilir
(Los Alamos Godiva Rossi-α ölçümlerinden türetilmiş değer). Koşunun 680.7 ± 24.5 pcm'i bunun
yaklaşık %5 üstündedir; fark birleşik belirsizliğin ~1.3σ'sı kadardır, yani bu tek koşuyla
anlamlı bir sapma söylenemez ama değer sistematik olarak yüksek olabilir (nükleer veri ν_d,
IFP nesil sayısı). Rossi-α ile de bakılabilir: kritikte α = β_eff/Λ = 0.006807 / 5.624 ns ≈
1.21 × 10⁶ 1/s; deneysel değer ≈ 1.11 × 10⁶ 1/s, yani ~%9 yüksek. İkisi birlikte β_eff'in biraz
fazla, Λ'nın biraz az tahmin edildiğini düşündürür. Bu bir eğitim karşılaştırmasıdır,
**sertifika değildir**.

**Ne öğrendik / kontrol soruları.**

- Λ = 20 μs ile Λ = 5.6 ns arasında 3600 kat fark varken aynı 0.1 $'ın periyodu (Keepin 98.6 s;
  Godiva 83.8 s) neden aynı mertebede? (ρ < β iken periyodu gecikmeli öncüllerin
  bozunma zamanları belirler, Λ değil.)
- Ani kritikte (adım 4) Λ neden birden belirleyici olur? (Periyot ≈ Λ/(ρ − β): Godiva'da
  mikrosaniyeler.)
- Geri beslemeli durumda (adım 5) 50 s'deki P = 1.97 P₀ bir denge midir? (Hayır. Isı atılmadığı
  için P > 0 oldukça ΔT artar, toplam ρ giderek daha negatif olur ve güç sıfıra doğru azalmayı
  sürdürür; 1.97 P₀ geçişin bir anıdır. Azalma, gecikmeli öncüllerin bozunmasıyla sınırlıdır:
  periyot −1/λ_1'den kısa olamaz. Gerçek bir reaktörde ısı atımı yeni bir denge gücü kurar;
  adiyabatik model bunu içermez.)
- Godiva'nın λ_i'si neden ENDF/B-VIII.0 U-235 değerleriyle neredeyse aynı? (Fisyonların büyük
  çoğunluğu U-235'te; λ_i nükleer veridir, IFP'den değil `decay-rate` / `delayed-nu-fission`
  tally'sinden gelir.)
