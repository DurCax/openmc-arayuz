<a id="goruntuleyici"></a>
## 4.12 Görüntüleyici

**Araçlar › Görüntüleyici…** ayrı bir pencerede modelin geometrisini inceler: istenen eksen,
konum ve genişlikte kesit, malzeme/hücre/çakışma renk kipleri, fare altındaki hücre ve malzeme,
[ağ (mesh) tally'si](04k-mesh-tally.md#mesh-tally) sonuçlarının kesitin üstüne bindirilmesi,
kaynak noktaları ve 3B gölgeli görünüm. Pencere modeli **değiştirmez**; geometri ya da ayar
düzeltmesi ilgili sekmede yapılır, sonra **Modeli yenile** ile görüntüleyiciye alınır.

Görüntüleyicinin kendi çizim süreci vardır (önizlemenin H2 çizim işçisi, `cekirdek/cizim_sureci.py`):
dilimleme, 3B ışın izleme ve kaynak örneklemesi bu süreçte yapılır, arayüz beklemez. Görüntüleyici
önizlemenin oturumunu ve **Çalıştır** kapısını etkilemez. Adım adım kullanım:
[5.18 Ders](05d-ders-goruntuleyici.md#ders-goruntuleyici).

<a id="goruntuleyici-kesit"></a>
### Kesit

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım |
|---|---|---|---|---|
| **Kesit ekseni** | Kesit düzlemi: `xy` (z sabit), `xz` (y sabit), `yz` (x sabit). Eksen değişince görünüm o eksende bütün modele döner. | — | xy | 2B modelde `xz`/`yz` beklemek: model eksenel sonsuzdur, kesit dikey bir şerittir. |
| **Kesit konumu** | Düzlemin normal eksendeki konumu (xy'de z). | cm | 0 (model merkezi) | Eksenel katmanlı modelde z = 0 yalnız bir katmanı gösterir; plenum ya da yansıtıcı için z'yi değiştirin. |
| **Görünür genişlik** | Pencerenin yatay genişliği; dikey genişlik oranı korur. Fare tekerleği aynı şeyi imleç noktası sabit kalarak yapar. | cm | sınır kutusu | Çok küçük genişlik (< 1 µm) sınırlanır. |
| **Çözünürlük** | Yatay piksel (400/800/1400); dikey piksel kare piksel için orandan hesaplanır. | piksel | 800 | Ayrıntıyı çözünürlükle değil yakınlaştırmayla arayın: yeni pencere tam çözünürlükte dilimlenir. |
| **Renklendirme** | **Malzeme** (spec renkleri), **Hücre** (hücre kimliğine göre), **Çakışma ve tanımsız bölge** (model soluk gri; çakışma hata renginde, hücresiz bölge turuncu). | — | Malzeme | Hücre renklerine fiziksel anlam yüklemek: yalnız hücreleri ayırt eder. |
| **Çakışma denetimi** | `slice_data(show_overlaps=True)`: bir noktanın birden çok hücrede olduğunu bulur. Çakışma kipi kendiliğinden açar. | — | kapalı | Büyük modelde yavaştır (SFR ~12 s). |
| **Tüm modeli göster** | Görünümü sınır kutusuna döndürür. | — | — | — |

Fare: **tekerlek** yakınlaştırır/uzaklaştırır, **sol tuşla sürükleme** kaydırır; imlecin altındaki
nokta pencerenin altında yazılır: koordinat (x, y, z), hücre kimliği ve adı, örnek (instance),
malzeme kimliği ve adı. Özel kodlar (OpenMC `slice_data`, 0.16.0):

| Kod | Anlamı | Görünüm |
|---|---|---|
| −1 | boşluk (void) malzemesi | beyaz |
| −2 | hücre yok: geometri dışı **ya da** tanımsız bölge (OpenMC ikisini ayırmaz) | saydam; çakışma kipinde turuncu |
| −3 | çakışma (yalnız denetim açıkken; malzeme kanalı −3, hücre kanalı −4 ölçüldü) | hata rengi |

Silindirik ya da altıgen modelin sınır kutusu köşelerindeki −2 olağandır (geometri dışı);
modelin **içinde** −2 bir tanımsız bölgedir ve koşuda "lost particle" verir.

<a id="goruntuleyici-tally"></a>
### Ağ (mesh) tally bindirmesi

Son başarılı koşunun statepoint'i açılışta kendiliğinden yüklenir (yoksa **Statepoint seç…**).
Statepoint okuması ayrı iş parçacığındadır.

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım |
|---|---|---|---|---|
| **Tally** / **Skor** / **Enerji grubu** | Bindirilen dizi; grup **Toplam (tüm gruplar)** ya da tek grup. | — | ilk tally | Grup toplamında σ iyimserdir (bkz. 4.11). |
| **Normalizasyon** | **Kaynak nötronu başına**, **Hacim başına (/cm³)**, **Ortalamaya bağıl (1 = ortalama)** — Y1 ile aynı işlev (`cekirdek/mesh_tally/normalizasyon.py`). Mutlak (W/cm³) için **Çalıştır › Ağ (mesh) haritası** kullanılır. | birim satırda | hacim başına | 2B modelde hacim başına değer z integralidir (alan başına). |
| **Opaklık** | Bindirmenin opaklığı (0 = görünmez, 100 = geometriyi örter). | % | 60 | — |
| **Güvenilmez hücreleri gizle (σ maskesi)** | Bağıl hatası eşiği aşan ya da skorsuz hücreler çizilmez (geometri görünür). | — | açık | Maskeyi kapatıp gürültülü hücreyi fizik sanmak. |
| **Bağıl hata eşiği** | Maske eşiği (kaynak: 4.11, MCNP kaba yönergesi R < 0.10). | % | 10 | — |

Bindirme geometri kesitinin piksel ızgarasında örneklenir: her pikselin merkezi ağ koordinatına
(düzenli x, y, z; silindirik r, φ, z; küresel r, θ, φ) çevrilir ve ağ hücresi aranır. Ağ hücresi
böylece geometrinin tam üstüne düşer (`testler/test_y2_gorunum.py`, `test_y2_pencere.py`: bilinen
hücre ↔ koordinat). Renk ölçeği `cividis`; ağ dışı saydamdır. Fare altındaki değer bilgi satırına
eklenir.

<a id="goruntuleyici-kaynak"></a>
### Kaynak noktaları

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım |
|---|---|---|---|---|
| **Kaynak** | **Model kaynağı (örnekleme)**: `settings.source` (kutu ya da nokta) örneklenir; `fissionable` kısıtı noktadaki malzemeye bakılarak uygulanır. **Statepoint kaynak bankası**: koşunun son kaynak noktaları (`source_bank`). | — | model kaynağı | Model kaynağını koşunun yakınsamış dağılımı sanmak: ilk çevrimin kaynağıdır. |
| **Nokta sayısı** | Gösterilecek nokta (bankadan rastgele alt küme). | nokta | 2000 (10–20000) | — |
| **Dilim kalınlığı** | Yalnız kesit düzlemine bu kalınlıktaki noktalar; **tümü (izdüşüm)** bütün noktaları düzleme izdüşürür. | cm | tümü | 3B modelde xz'de kalınlık 0: bütün eksenel noktalar üst üste. |

Örnekleme notu: OpenMC'nin `openmc.lib.sample_external_source` işlevi çizim kipinde (nükleer
veri yüklenmeden) fisil kısıtlı kaynakta süreci sonlandırır (ölçüldü); bu yüzden örnekleme numpy
ile yapılır. Fisil malzeme: en az bir nüklidi aktinit (Z ≥ 90). Kabul oranı %5'in altına düşerse
(OpenMC `source_rejection_fraction` varsayılanı) açık hata verilir.

<a id="goruntuleyici-3b"></a>
### 3B görünüm

**3B görünüm** sekmesi `openmc.lib.SolidRayTracePlot` (OpenMC 0.16.0) ile gölgeli bir resim
üretir. Kamera modelin merkezine bakar.

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım |
|---|---|---|---|---|
| **Renklendirme** | Malzeme (spec renkleri) ya da hücre (OpenMC varsayılan renkleri; kesitin hücre renkleriyle aynı değildir). | — | Malzeme | — |
| **Azimut** / **Yükselti** | Kameranın yönü: x ekseninden z çevresinde açı / xy düzleminden açı. | ° | 45 / 30 | — |
| **Uzaklık katı** | 1 = modelin sınır küresi görüş açısına tam sığar; küçük değer yakınlaştırır. | — | 1.1 | Model içine girmek (< ~0.3): yalnız iç yüzey görünür. |
| **Görüş açısı** | Yatay görüş açısı. | ° | 40 | — |
| **Gizlenen malzemeler** | İşaretli malzemeler saydam olur (ör. su gizlenince çubuklar görünür). Yalnız malzeme renklendirmesinde. | — | hiçbiri | — |
| **Çiz** | 3B resmi ister (tuval boyutunda). | — | — | — |

Sınırlamalar (ölçüldü, OpenMC 0.16.0): 2B modelde geometri eksenel sonsuzdur, resim sonsuz bir
prizmadır. VVER-1000 ve BEAVRS tam kor örneklerinde ışın izleyici "pure virtual method called" /
"Lost particle after reflection" ile süreci çökertir ya da asılı bırakır; görüntüleyici süreci
30 s'de durdurur, 3B sekmesinde açık hata gösterir ve süreci yeniden başlatır. Kafesli 3B
modellerde (PWR 3B demet, SMR koru) yükselti ≳ 45° ya da gizlenmiş su ile bazı ışınlar "negative
distance to a lattice boundary" hatası verir; yükseltiyi düşürün ya da gizlemeyi kaldırın.
Varsayılan kamerayla (45° / 30°) demet, SMR koru, SFR altıgen, tamburlu kor ve kritik deney
örnekleri çalışır (320 × 240 piksel 0.01–0.12 s).

**PNG olarak kaydet…** etkin sekmenin (kesit ya da 3B) resmini kaydeder. Görüntüleyici bir
inceleme aracıdır; çakışma bulunmaması geometrinin doğru olduğunun kanıtı değildir (yalnız
çizilen kesitlerdeki noktalar denetlenir) — sertifika değildir.
