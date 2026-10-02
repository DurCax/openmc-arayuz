<a id="tukenme-genisletme"></a>
### 4.9.1 Tükenme genişletmeleri: entegratör, soğuma, sürdürme, kritiklik araması, hızlı kip

Bu alanlar **Tükenme** sekmesinin **Yanma ayarları › Gelişmiş** bölümündedir. Hepsi
`openmc.deplete` (OpenMC 0.16) üzerine kuruludur; arayüz elle bir çözücü yazmaz. Dosyada
yoksa varsayılanları kullanılır ve **varsayılan değerler dosyaya yazılmaz** (eski projeler
gidiş-dönüşte değişmez). Aynı ayarlar üretilen Python betiğinin `tukenme_kos()` işlevine de
yazılır ([8. Terminal](08-terminal.md#terminal)).

#### Entegratör

| Seçenek | OpenMC sınıfı | Adım başına transport | Not |
|---|---|---|---|
| Predictor | `PredictorIntegrator` | 1 | 1. mertebe; kısa adımlarla ön inceleme |
| CE/CM (varsayılan) | `CECMIntegrator` | 2 | 2. mertebe öngörücü-düzeltici |
| CE/LI | `CELIIntegrator` | 2 | sabit dışdeğerleme / doğrusal aradeğerleme |
| LE/QI | `LEQIIntegrator` | 2 | önceki adımın hızlarını da kullanır (ilk adım CE/LI) |
| EPC-RK4 | `EPCRK4Integrator` | 4 | genişletilmiş öngörücü-düzeltici, Runge-Kutta 4 |
| CF4 | `CF4Integrator` | 4 | 4. mertebe komütatörsüz Lie |
| SI-CE/LI, SI-LE/QI | `SICELIIntegrator`, `SILEQIIntegrator` | iç yineleme + 1 | stokastik örtük; ilk adımda bir BOS transport'u (iç yineleme kat parçacıkla) |

Transport sayıları OpenMC kaynağındaki `_num_stages` değerleridir; adım özeti bunları
(soğuma ve kritiklik araması dahil) yazar. Mertebe yükseldikçe aynı doğruluk için daha az
adım gerekir ama adım başına daha çok transport koşar. **Hangisi daha iyi** sorusunun tek
cevabı yoktur: küçük bir örnekte CE/CM ile CE/LI farkı [ders 5.17](05c-ders-tukenme.md#ders-tukenme-genisletme)'de
ölçülür (eşik konmaz; fark istatistik gürültü düzeyindedir).

#### Alanlar

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Soğuma adımları** | Yanma adımlarından SONRA sıfır güçte (yalnız bozunma) adımlar, virgülle. OpenMC güç 0 olan adımda transport koşmaz; bu adımlarda k-eff yoktur (tabloda "—") ve yanma artmaz. | **Soğuma birimi** | 1, 10, 100, 1000 gün | Soğumayı yanma adımı olarak girmek (güç sürer) | `tukenme.sogutma.adimlar` |
| **Soğuma birimi** | gün, saat, yıl (Julian, 365.25 gün) ya da saniye. MWd/kg anlamsızdır (güç yok). | — | gün | — | `tukenme.sogutma.birim` |
| **SI iç döngü** | Yalnız SI-* entegratörlerinde görünür: OpenMC `n_steps`. | — | 10 (OpenMC varsayılanı) | Çok büyük değer: süre adım başına (n+1) transport ile artar | `tukenme.si_ic_adim` |
| **Kaldığı yerden sürdür** | Dizindeki önceki sonuç silinmez. Yarıda kalan koşu son kayıtlı adımın başından devam eder; biten koşuya adım eklendiyse yalnız yeni adımlar koşulur. Önceki koşunun fiziği (malzeme, geometri, güç, entegratör) aynı ve adım listesi öncekinin devamı olmalıdır; değilse koşu başlamaz ve nedeni yazılır. | — | kapalı | Fiziği değiştirip sürdürmek (reddedilir) | `tukenme.surdur` |
| **Hızlı kip (MicroXS, transport'suz)** | Tek transport'tan tek gruplu mikroskobik tesir kesitleri (`get_microxs_and_flux`, "direct"), sonra `IndependentOperator`: adımlarda transport yok. Spektrum değişimi görülmez, k-eff adım adım hesaplanmaz. Ön inceleme içindir. | — | kapalı | Yüksek yanmada sonucu tam tükenme yerine kullanmak | `tukenme.hizli_kip` |
| **Tükenme sırasında kritik arama (k = 1)** | Her güçlü adımın başında k = 1 veren değer aranır (`Integrator.add_keff_search_control`, `Model.keff_search` GRsecant). Bulunan değer sonuç tablosunda ve h5'te (`keff_search_root`) durur. SI-* ve hızlı kiple birlikte kullanılamaz. | — | kapalı | Çok dar tolerans: arama adım başına onlarca transport koşar | `tukenme.kritik_arama.var` |
| **Arama türü** | **Çözünmüş bor [ppm]**: su malzemesinin bileşimi her denemede statik bor taramasıyla aynı tariften kurulur. **Kontrol çubuğu daldırma [%]**: çubuk evreninde emici + izleyici iç evrene taşınır ve dış hücrenin `translation`'ı ucun konumudur (3B model). Hareket eden emici tükenmez (yanan bir emiciyse doğrulama bunu UYARI olarak gösterir: "çubuk araması: hareketli emici … tükenmeden çıkarılır"). Dış hücrenin bölgesi emici ve izleyici hücrelerinin birleşimidir; çubuk evrenindeki plenum ya da uç tıpası değişmez. | ppm \| % | — | Çubuk aramasını çubuk çubuk yanmayla açmak (desteklenmez) | `tukenme.kritik_arama.tur` (`bor` \| `cubuk`) |
| **Hedef** | Bor için su (soğutucu/moderatör) malzemesi, çubuk için kontrol çubuğu. | — | — | Yakıta bor araması (hata); tükenen (ek yanan) suya bor araması (hata: arama tükenmiş bileşimi ezerdi) | `tukenme.kritik_arama.hedef` |
| **Başlangıç tahminleri** | GRsecant'ın ilk iki noktası. | ppm \| % | 500 ve 1500 ppm | Aynı iki değer (hata) | `tukenme.kritik_arama.alt`, `tukenme.kritik_arama.ust` |
| **Sınır [en az, en çok]** | Değerin çıkamayacağı aralık; dışına düşen kök sınıra kırpılır (OpenMC uyarısı). | ppm \| % | 0–3000 ppm; 0–100 % | Tahminin sınır dışında olması (hata) | `tukenme.kritik_arama.sinir` |
| **k toleransı** | Arama \|k − 1\| ≤ tolerans ve σ ≤ tolerans olunca durur. Varsayılan 1e-3 (100 pcm): tipik bir tükenme adımının istatistik belirsizliği düzeyi; OpenMC'nin varsayılanı (1e-4) küçük modelde onlarca transport ister. | — | 1e-3 | 1e-5 gibi değerler | `tukenme.kritik_arama.k_tol`, `tukenme.kritik_arama.sigma` |

#### Aktivite, bozunma ısısı ve foton kaynağı kartı

Sonuç gelince **Hesapla** ile hesaplanır (büyük zincirde adım başına saniyeler sürer).
**Seri** seçimi: bozunma ısısı [W], [W/g]; aktivite [Bq], [Bq/g]; foton kaynağı [foton/s].
Tablo her zaman noktasında toplamları, alttaki metin son adımda malzeme başına **temas doz
hızını** ve **atık sınıfını** yazar; **Çıktıları CSV olarak dışa aktar** her seriyi
malzeme başına yazar.

| Büyüklük | Kaynak (OpenMC 0.16) | Not |
|---|---|---|
| Aktivite | `Material.get_activity` | λN; yarı ömür koşunun zincirinden |
| Bozunma ısısı | `Material.get_decay_heat` | λNQ; Q zincirin `decay_energy`'si (ENDF/B-VIII.0 bozunum alt kütüphanesi; nötrino hariç). W/g malzeme kütlesi başınadır |
| Foton kaynağı | `Material.get_decay_photon_energy` | zincirdeki bozunma fotonu spektrumunun integrali |
| Temas doz hızı | `Material.get_photon_contact_dose_rate` | FISPACT-II yöntemi (yarı sonsuz levha, havada, birikim katsayısı 2), Gy/h; bremsstrahlung yok |
| Atık sınıfı | `Material.waste_classification` | ABD NRC 10 CFR 61.55 yakın-yüzey sınıfı; kullanılmış yakıt yüksek düzeyli atıktır — **bilgi amaçlıdır, sertifika değildir** |

Basitleştirilmiş CASL zincirinde birçok aktivasyon ürünü (ör. Co-60) yoktur; aktivite ve
bozunma ısısı eksik çıkar. Bu çıktılar için tam ENDF/B-VIII.0 zincirini seçin.

#### Doğrulama

Soğumada bozunma ısısı tek nüklidli analitikle karşılaştırılır (`testler/test_y4_cikti.py`):
saf Co-60, P(t) = λN₀e^(−λt)Q; bağıl fark < 1e-6 (W) ve < 1e-4 (W/g; Co-60 → Ni-60 kütle
farkı). Kritiklik aramasında her güçlü adımın k'si \|k − 1\| ≤ tolerans + 3σ
(`testler/test_y4_kosu.py`): arama tolerans içinde durur, adımın kendi transport'u bağımsız
bir ölçümdür (%99.7). Sonuçlar eğitim amaçlıdır, **sertifika değildir**.
