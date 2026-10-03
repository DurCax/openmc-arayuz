<a id="dal"></a>
### Dal tablosu kartı (yanma × koşul)

**Analiz** sayfasındaki **Dal tablosu** kartı, kafes kodlarının *branch* tablosunu üretir. Bir
tükenme sonucunun seçili yanma noktalarında **bileşim sabit tutulur** (yanma ilerlemez); yalnız
koşul değişir ve yalnız transport koşulur:

    yanma adımı  ×  { T_yakıt }  ×  { C_bor }  ×  { T_mod, ρ_mod }   →   k ± σ

Sonuç, aynı bileşimde koşul değişiminin **anlık** etkisidir (Doppler, bor değeri, moderatör sıcaklık
ve yoğunluk katsayıları yanmanın fonksiyonu olarak); yeni bir tükenme değildir. Koşular [koşu
kuyruğunda](04j-is-akisi.md#is-akisi) sırayla çalışır ve tablo koşu bittikçe dolar.

**Nasıl çalışır.** (1) Koşul, tek değişkenli taramayla **aynı kodla** uygulanır
(`tarama.parametre_uygula`): taban model değişmez. (2) Model tükenme koşusundakiyle aynı yoldan
kurulur (bölme ve çubuk çubuk klonlar aynı sırada, malzeme kimlikleri aynı); sonuç dosyasındaki her
malzemenin hacmi modelle karşılaştırılır, uyuşmazsa dal başlamaz (yanlış bileşim sessizce
yazılmaz). (3) Adım bileşimi malzemelere yazılır: önce malzemenin atom/b-cm yoğunlukları, sonra
zincirde olup tesir kesiti bulunan nüklidlerin yanma adımındaki atom sayısı / hacim (OpenMC 0.16
`Results.export_to_materials` ile aynı mantık). (4) `model.xml` yazılır ve iş kuyruğa girer.
Dal, tükenme sonucunun **koşu dizinindeki model kaydıyla** kurulur; sonuç şimdiki modele ait değilse
kart bunu yazar.

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Yanma adımları** | Dalın hesaplanacağı zaman noktaları (sonuç dosyasındaki noktalar; 0 = taze yakıt). | adım | birkaç nokta (0, ortası, sonu) | Her adımı seçmek: koşu sayısı adım × koşul olarak çarpılır | (spec'e yazılmaz) |
| **Yakıt sıcaklığı** | Fisil yanabilir malzemenin sıcaklığı (yoğunluk sabit; katı yakıt). | K | 600–1200 | Yalnız T_yakıt değiştirip "moderatör katsayısı" demek | (spec'e yazılmaz) |
| **Çözünmüş bor** | Soğutucu/moderatör suyunun bor derişimi (statik bor taramasının tarifi). | ppm | 0–1500 | Sudaki boru yanabilir sanmak: dal bileşimi sabittir | (spec'e yazılmaz) |
| **Soğutucu sıcaklığı** | Soğutucu sıcaklığı; yoğunluk korelasyonla birlikte değişir (su: doymuş sıvı tablosu). | K | 550–600 | Yoğunluğu sabit sanmak (katsayı birkaç kat yanlış) | (spec'e yazılmaz) |
| **Soğutucu yoğunluğu** | Yoğunluğu doğrudan verir (ρ_mod). | g/cm³ | 0.6–0.8 | Sıcaklıkla birlikte vermek: ikisi çelişir | (spec'e yazılmaz) |
| **Birleşim** | **Her değişken tek başına**: taban + her değişkenin her değeri (tek değişkenli taramayla aynı noktalar). **Tüm bileşimler**: kartezyen çarpım. | — | tek başına | Kartezyen çarpımı 3 değişkenle açmak: koşu sayısı patlar | (spec'e yazılmaz) |

**Tablo.** Her satır bir (adım, koşul): k ± σ ve taban dala göre **Δk [pcm] = (k − k_taban) × 10⁵**,
σ_Δk = √(σ² + σ_taban²) × 10⁵. Koşular bağımsız sayıldığından bu belirsizlik **muhafazakârdır**
(aynı tohum kullanıldığından gerçek belirsizlik daha küçüktür). **CSV kaydet** her satırı
yazar (ondalık nokta, sabit sütun anahtarları).

**Tutarlılık.** Adım 0 dalı, aynı koşuldaki tek değişkenli taramayla istatistik içinde aynı k'yı
verir; taban dal, tükenme koşusunun o adımdaki k'sıyla aynıdır (testlerde 2σ içinde ölçüldü).
Terminal: `python3 -m cekirdek.dal model.json tukenme_dizini --adimlar 0,4 --yakit-sicaklik 600,900
--bor 0,500` ([8. Terminal](08-terminal.md#terminal)).

Bu bir **eğitim ve ön inceleme** aracıdır: bir çekirdek simülatörünün dal tablosu (HFP/HZP, kesin
bor basamakları, soğuma) yerine geçmez; sertifika değildir.
