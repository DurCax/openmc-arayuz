<a id="kinetik"></a>
### Nokta kinetiği kartı

**Analiz** sayfasının en altındaki **Nokta kinetiği** kartı, bir reaktivite değişikliğine reaktör
gücünün zamanla nasıl yanıt verdiğini **nokta kinetiği** denklemleriyle hesaplar ve P(t)/P₀
eğrisini çizer. Kart modelden bağımsızdır; gecikmeli nötron verisini üç yerden alabilir:
kinetik parametreleri açık bir koşudan (IFP), ders kitabı verisinden (Keepin) ya da elle.
Hesap birkaç saniyenin altında biter; OpenMC koşusu yapılmaz.

**Denklemler** (Duderstadt & Hamilton 1976, bölüm 6; Keepin 1965):

    dn/dt   = [(ρ(t) − β) n + Σ λ_i c_i] / Λ
    dc_i/dt = β_i n − λ_i c_i                      i = 1 … N (N = 6 ya da 8)

n = P/P₀ (t = 0'da 1, kritik denge), c_i grup i öncüllerinin Λ ile ölçeklenmiş yoğunluğu
(denge c_i = β_i/λ_i), β = Σ β_i. Ani ölçek (−(β − ρ)/Λ ≈ −10³ … −10⁶ 1/s) ile gecikmeli ölçek
(≈ 10⁻² 1/s) arasındaki fark sistemi **katı** (stiff) yapar; bu yüzden çözücü açık bir yöntem değil,
`scipy.integrate.solve_ivp` **Radau** yöntemidir (analitik Jacobian, bağıl tolerans 10⁻⁹).

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Veri kaynağı** | **Keepin U-235 termal (6 grup)**: Keepin, Wimett & Zeigler, Phys. Rev. 107, 1044 (1957) / Lamarsh & Baratta (2001) Tablo 7.4 değerleri, Σβ_i = 650.2 pcm. **Son koşu (IFP)**: son başarılı koşudan okunan β_i, λ_i ve Λ. **Elle**: tabloyu kendiniz doldurursunuz (hazır veriden başlar). Hazır veride ve koşu verisinde tablo düzenlenemez. | — | Keepin | LWR olmayan bir sistemde (hızlı, MOX) Keepin U-235 termal verisini kullanmak: β ve λ_i farklıdır. | (spec'e yazılmaz) |
| **Son koşudan al** | Bu projedeki son başarılı koşunun statepoint'ini okur. Koşuda [Hesap ayarları](04f-hesap-ayarlari.md#hesap-ayarlari) > **Kinetik parametreleri hesapla** ve **Gecikmeli nötron grupları** (6 ya da 8) açık olmalıdır; değilse kart nedenini yazar. | — | — | Kinetik kapalı bir koşudan veri beklemek. | — |
| **Grup sayısı** | Elle verideki grup sayısı (tablo satırı). | grup | 6 (1–8) | — | — |
| Tablo **β_i [pcm]**, **λ_i [1/s]** | Grup başına etkin gecikmeli nötron oranı ve öncül bozunma sabiti. β_i ≥ 0, Σβ_i > 0, λ_i > 0 olmalı; değilse hata yazılır ve hesap yapılmaz. | pcm, 1/s | λ_1 ≈ 0.0124 (≈ 56 s yarı ömür) … λ_6 ≈ 3 1/s | β_i'yi Δk/k olarak (0.0002) yazmak: tablo **pcm** ister (21.5). | — |
| **Üretim zamanı Λ** | Ani nötron üretim zamanı. | μs | örnek değerler (bu programla ölçülen): PWR 17×17 demeti 18.9 μs, Godiva 5.6 ns = 0.0056 μs | Ani nötron ömrü ℓ ile karıştırmak: Λ = ℓ/k. | — |
| **Reaktivite türü** | **Basamak**: t = 0'da sabit ρ. **Rampa**: ρ, **Rampa süresi** boyunca doğrusal artar, sonra sabit kalır. | — | Basamak | — | — |
| **Birim** | **pcm** (1 pcm = 10⁻⁵ Δk/k) ya da **$** (1 $ = β_eff). Birim değişince değer o anki Σβ_i ile dönüştürülür. | — | pcm | $'ı başka bir sistemin β'sıyla düşünmek: 1 $ her sistemde farklı pcm'dir. | — |
| **Reaktivite** | Basamakta eklenen ρ; rampada rampa sonunda ulaşılan ρ. Negatif değer kritik altı geçişi verir. | pcm ya da $ | örnek: ±(10–300) pcm | ρ ≥ 1 $ girmek: **ANİ KRİTİK** uyarısı çıkar (aşağıda). | — |
| **Rampa süresi** | Rampanın süresi; yalnızca rampada görünür. Rampa hızı = ρ / süre. | s | 1–100 s | — | — |
| **Benzetim süresi** | Çözümün bitiş zamanı. Kararlı periyot ancak en uzun ömürlü grubun geçişi sönünce (birkaç × 1/λ_1 ≈ dakikalar) ölçülür. | s | 100 s | Kısa süreden "kararlı periyot" okumak: çözümden ölçülen periyot Inhour değerine henüz yaklaşmamıştır. | — |
| **Adiyabatik sıcaklık geri beslemesi** | Isı atılmaz: dΔT/dt = P₀ (P/P₀) / C ve ρ = ρ_dış + α_T ΔT. Grafikte ΔT ikinci eksende kesikli çizilir. | — | kapalı | Isı atımı olan bir durumda (sürekli işletme) adiyabatik sonucu kalıcı sanmak. | — |
| **α_T** | Sıcaklık reaktivite katsayısı. Pozitif değer uyarı verir (kararsız geri besleme). | pcm/K | örnek değer: −2 pcm/K (kaynaklı bir tipik aralık verilmez; kendi modelinizin Doppler katsayısını Analiz taramasıyla ölçün) | Birimi Δk/k/K sanmak: kutu **pcm/K** ister. | — |
| **Isı kapasitesi C** | Isınan kütlenin toplam ısı kapasitesi. | J/K | — | — | — |
| **Başlangıç gücü P₀** | t = 0'daki güç. | W | — | — | — |
| **Hesapla** | Girdileri doğrular, çözer; sonuç metni, uyarılar ve P(t)/P₀ grafiği yazılır. Grafik, güç 100 kattan fazla değişirse logaritmik eksene geçer. | — | — | — | — |

**Sonuç metni** şunları yazar: ρ (pcm ve $), **Inhour kararlı periyodu** T = 1/ω₀ (aşağıda),
**çözümden ölçülen periyot** (zaman ekseninin son %10'unda ln P eğiminden), P(t_son)/P₀ ve
geri beslemede ΔT ile toplam ρ.

**Ters saat (Inhour) denklemi.** Basamak reaktivitesinde çözüm n(t) = Σ A_k e^(ω_k t)
biçimindedir; ω_k, ρ = ω Λ + Σ β_i ω / (ω + λ_i) denkleminin N + 1 köküdür. En büyük kök ω₀
kararlı periyodu verir (T = 1/ω₀); ρ > 0'da tek pozitif kök vardır, ρ < 0'da bütün kökler
negatiftir ve ω₀ > −λ_1'dir (negatif periyot −1/λ_1'den, Keepin verisinde ≈ −81 s'den, kısa olamaz). Kökler her
kutup aralığında ayrı ayrı (Brent yöntemi) bulunur.

**Ani kritik (ρ ≥ 1 $).** Güç artık gecikmeli nötronları beklemeden Λ ölçeğinde artar
(periyot ≈ Λ/(ρ − β)). Kart **ANİ KRİTİK** uyarısı yazar; P/P₀ 10¹⁰'u aşarsa çözüm durdurulur ve
bu da yazılır. Geri beslemesiz nokta kinetiği bu bölgede yalnızca nitel bir tablo verir.

**λ_i nereden gelir?** IFP λ_i vermez. Koşuda ayrı bir tally grup başına `decay-rate` ve
`delayed-nu-fission` sayar; λ_i = ⟨λ_i ν_d,i Σ_f φ⟩ / ⟨ν_d,i Σ_f φ⟩ (OpenMC `mgxs.DecayRate` ile
aynı tanım). Bu, grup i içinde nüklidlerin λ'larının **öncül üretim hızı** (ν_d,i Σ_f φ)
ağırlıklı aritmetik ortalamasıdır: ileri (eşlenik ağırlıksız) bir ortalama. β_i ise **eşlenik
ağırlıklıdır**; iki ağırlık farklıdır (tek baskın fisil nüklidde fark sıfıra gider). Envanteri
koruyan harmonik ortalama (Σ ν_d / Σ (ν_d/λ)) nüklid başına skor ister ve yapılmaz. λ_i **nükleer
veridir**: ENDF/B-VIII.0'da 6 grup ve nüklide göre farklı λ (U-235: 0.01334, 0.03274, 0.12078,
0.30278, 0.84949, 2.85300 1/s), JEFF-3.1+'da 8 grup ve bütün nüklidlerde aynı λ. β_i ise IFP ile
**eşlenik ağırlıklı** etkin orandır: β_eff,i = ⟨IFP beta payı⟩_i / ⟨IFP payda⟩. Λ, OpenMC
`StatePoint.get_kinetics_parameters` tanımıyla Λ = ⟨IFP zaman payı⟩ / (⟨IFP payda⟩ k_eff)'dir.
λ_i belirsizliği pay ve paydanın bağımsız olduğu varsayımıyla yazılır; ikisi güçlü ilintili
olduğundan bu bir **üst sınırdır**.

**Hangi β?** $ dönüşümü ve ani kritik eşiği her yerde aynı β ile yapılır: tablodaki **Σβ_i**
(koşudan alındığında gruplu IFP tally'sinin toplamı = sonuç kartındaki β_eff). Koşuda ayrıca
filtresiz bir `delayed-nu-fission` tally'si sayılır; Σ dnf_i bu toplamdan küçükse kütüphanede
istenenden çok grup vardır (JEFF verisiyle 6 grup) ve kart β_eff'in eksik olduğunu uyarır.

**Doğrulama** (`testler/test_y6_kinetik.py`, `testler/test_y6_tally.py`):

| Denetim | Sonuç |
|---|---|
| Tek grup basamak: çözücü ↔ analitik iki üstel çözüm | bağıl fark ≤ 1.4 × 10⁻¹⁰ |
| Tek grup Inhour kökleri ↔ kapalı biçimli ikinci derece kök | 10⁻⁹ içinde |
| 6 grup basamak: çözücü ↔ matris üstel (tam doğrusal çözüm) | ≤ 1.2 × 10⁻¹⁰; Λ = 10⁻⁷ s (katı) ≤ 10⁻¹¹ |
| Asimptotik periyot ↔ Inhour kökü (Keepin, 100 pcm) | 54.92 s ↔ 54.92 s (%0.1 içinde) |
| Ani sıçrama (0.5 $, Λ = 10⁻⁷ s) n = β/(β − ρ) | 2.008 ↔ 2.000 |
| Nordheim–Fuchs (ρ = β + 200 pcm, α = −2 pcm/K): tepede ΔT = (ρ − β)/|α|, P_max, toplam ΔT = 2(ρ − β)/|α| | 101 K ↔ 100 K; 1.02 × 10⁹ ↔ 1.00 × 10⁹; 204 K ↔ 200 K |
| Godiva IFP 6 grup: Σβ_i = β_eff; β_i ve Λ = OpenMC `get_kinetics_parameters` | birebir (10⁻⁹) |
| Godiva λ_i ↔ ENDF/B-VIII.0 U-235 | %0.4 içinde |

**Sınırlar.** Nokta kinetiği akının biçimini sabit varsayar (uzaysal etki, ksenon, ısı
atımı yok); geri besleme yalnızca adiyabatik tek sıcaklıktır. Sonuçlar eğitim amaçlıdır,
**sertifika değildir**. Adım adım örnek: [nokta kinetiği dersi](05b-ders-kinetik.md#ders-kinetik).
