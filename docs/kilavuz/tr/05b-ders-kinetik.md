<a id="ders-kinetik"></a>
## 5.11 Nokta kinetiği: gecikmeli nötronlar ve periyot

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

Godiva için IFP doğrulama çalışmalarında kullanılan ölçülmüş β_eff yaklaşık 659 ± 10 pcm'dir
(Rossi-α ölçümünden; ör. Kiedrowski, Brown & Wilson, Nucl. Sci. Eng. 168, 2011); koşunun
680.7 ± 24.5 pcm'i bununla 1σ içinde uyumludur.

**Ne öğrendik / kontrol soruları.**

- Λ = 20 μs ile Λ = 5.6 ns arasında 3600 kat fark varken 0.1 $'ın periyodu (adım 1'de 0.154 $ →
  55 s; Godiva'da 0.1 $ → 84 s) neden aynı mertebede? (ρ < β iken periyodu gecikmeli öncüllerin
  bozunma zamanları belirler, Λ değil.)
- Ani kritikte (adım 4) Λ neden birden belirleyici olur? (Periyot ≈ Λ/(ρ − β): Godiva'da
  mikrosaniyeler.)
- Geri beslemeli durumda güç neden sıfıra değil, P₀'ın üstünde bir değere iner? (Isı atılmadığı
  için ΔT artmayı sürdürür ve ρ negatif kalır; güç gecikmeli öncüllerin bozunmasıyla yavaşça
  azalır. Gerçek bir reaktörde ısı atımı yeni bir denge kurar.)
- Godiva'nın λ_i'si neden ENDF/B-VIII.0 U-235 değerleriyle neredeyse aynı? (Fisyonların büyük
  çoğunluğu U-235'te; λ_i nükleer veridir, IFP'den değil `decay-rate` / `delayed-nu-fission`
  tally'sinden gelir.)
