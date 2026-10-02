<a id="sonuclar"></a>
# 6. Sonuçları yorumlamak

Bir koşu bittiğinde **Çalıştır** sayfası sonuç kartını (k-eff ya da sabit kaynakta tally'ler),
çevrim başına k grafiğini, Shannon entropisi grafiğini, istenmişse güç haritasını ve
[uygunluk panelini](07-uygunluk.md#uygunluk-denetimi) gösterir; OpenMC'nin ham çıktısı
"Ayrıntılı çıktı" altında katlıdır. Bu bölüm o sayıların nasıl okunacağını anlatır: tek bir
k-eff sayısı, belirsizliği, kaynağın yakınsadığı ve geometrinin doğru olduğu bilinmeden bir şey
söylemez.

Bu bölümde **pcm** her yerde × 10⁵ demektir ve hangi büyüklüğe uygulandığı yazılır:
k farkı için *Δk × 10⁵*, reaktivite farkı için *Δρ × 10⁵* (ρ = (k − 1)/k).

<a id="istatistik"></a>
## 6.1 İstatistik: k-eff ve belirsizliği

**k-eff ± σ ne demektir?** Monte Carlo sonucu bir tahmindir. Sonuç kartındaki "±" değeri
**1σ standart belirsizliktir** (JCGM 100 / GUM anlamında); bir güven aralığı değildir. Dağılım
normalse gerçek değer yaklaşık %68 olasılıkla ±1σ, %95 olasılıkla ±2σ içindedir. Belirsizliğe
"hata" demeyin: hata bilinen bir yanlışlıktır, belirsizlik istatistiğin genişliğidir.

**Pasif ve aktif çevrim.** İlk çevrimlerde fisyon kaynağı henüz doğru dağılmamıştır; bu
**pasif (inactive) çevrimler** istatistiğe katılmaz. k-eff ve bütün tally'ler yalnız
**aktif çevrimlerden** (toplam − pasif) hesaplanır.

**Belirsizlik ne kadar küçülür?** σ, izlenen nötron sayısının kareköküyle küçülür:
σ'yu yarıya indirmek için parçacık × aktif çevrim çarpımını **dört katına** çıkarmanız gerekir.
Hesap ayarlarındaki **Hesap hassasiyeti** seçeneği beklenen σ'yu bu kurala göre yazar
(σ_k ≈ 90 000 pcm / √(parçacık × aktif çevrim), pcm = Δk × 10⁵; katsayı `pwr_pinhucre`
ölçümünden gelir, başka modelde yalnız mertebe verir):

| Hesap hassasiyeti | Parçacık / çevrim | Çevrim / pasif | Beklenen σ_k |
|---|---|---|---|
| Hızlı deneme | 1000 | 60 / 20 | ~450 pcm (Δk × 10⁵) |
| Normal | 10 000 | 150 / 40 | ~86 pcm |
| Hassas | 50 000 | 300 / 80 | ~27 pcm |

"Hızlı deneme" yalnız modelin çalıştığını görmek içindir; sayı yazılacak, karşılaştırılacak ya
da rapora girecek her sonuç en az "Normal" ile koşulur.

**Çevrimler arası ilinti.** OpenMC σ'yı ardışık çevrimleri birbirinden bağımsız sayarak
hesaplar. Oysa bir çevrimin fisyon kaynağı bir öncekinden doğar; çevrimler ilintilidir ve
raporlanan σ gerçek belirsizliğin **altında** kalır. k-eff için bu etki küçüktür (F.B. Brown,
LA-UR-09-03136 §IV.C: k-eff'te belirgin yanlılık görülmemiş), yerel tally'lerde (çubuk gücü,
akı haritası) büyüktür (aynı kaynakta 1.7–4.7 kat). Uygunluk panelindeki **K2** kuralı bu
ilintiyi gecikme-1 öz ilintisiyle denetler (bkz. [kurallar](09-sorun-giderme.md#uygunluk-kurallari)).

**Sonuç kartındaki yorum.** Araç k'yı şöyle sınıflandırır (`cekirdek/kosucu.py`,
`keff_yorumu`):

| Durum | Ölçüt | Gösterilen |
|---|---|---|
| Bütün dış sınırlar yansıtıcı | sızıntı yok | "k∞ (sonsuz ortam)"; kritiklik hükmü **verilmez** |
| Kritik | \|k − 1\| ≤ 2σ | "k = 1'den istatistiksel olarak ayırt edilemez" |
| Kritik üstü | k > 1 + 2σ | "güç artar" |
| Kritik altı | k < 1 − 2σ | "güç söner" |

Kartta ayrıca reaktivite ρ = (k − 1)/k, pcm cinsinden (Δρ × 10⁵) ve belirsizliği
σ_ρ ≈ σ_k / k² yazar. Kinetik parametreler hesaplandıysa reaktivite **dolar** cinsinden de
verilir (1 $ = β_eff). ρ > 1 $ ise kart iki anlamı birlikte söyler: gerçek bir geçici rejimde
bu anlık kritikliktir, sonsuz ortam (k∞) hesabında ise yakıtın taşıdığı reaktivite fazlasıdır.

> **Örnek.** `ornekler/pwr_17x17.json` yansıtıcı yan sınırlı tek bir demettir; sonucu bir
> k∞'dur (README ölçümü 1.18443 ± 0.00088). Reaktivitesi
> ρ∞ = 0.18443 / 1.18443 = 0.15571 → **+15 571 pcm (Δρ × 10⁵)**, belirsizliği
> 0.00088 / 1.18443² ≈ 63 pcm. Bu, "reaktör süperkritik" demek değildir: sonlu bir korda
> sızıntı ve kontrol bu fazlayı dengeler.

**İki sonucu karşılaştırmak.** İki k arasındaki fark ancak
\|k₁ − k₂\| > 2·√(σ₁² + σ₂²) ise anlamlıdır (araç da kritik arama ve tarama yorumunda 2σ
ölçütünü kullanır). Farkı **iki biçimde** yazın ve hangisi olduğunu söyleyin:
Δk = k₂ − k₁ (pcm = Δk × 10⁵) ya da Δρ = (k₂ − k₁)/(k₁k₂) (pcm = Δρ × 10⁵).

> ⚠ **Farklı ayarlarla koşulan sonuçlar karşılaştırılmaz.** README'deki `pwr_3b` ile
> `pwr_eksenel` karşılaştırması bu yüzden **aynı ayarla** (250 çevrim / 100 pasif) koşuldu.
> Farklı parçacık, pasif çevrim, sıcaklık yöntemi ya da kütüphaneyle alınmış iki sayının farkı
> modelin değil ayarların farkını da içerir. Bir karşılaştırma yalnız tek bir şeyi değiştirmeli:
> o örnekte bile iki model iki yönden farklıydı (su yansıtıcı + doğal UO₂ blanket) ve
> −232 pcm'lik k farkı "yansıtıcı kazancı" olarak okunamazdı.

**Tekrarlanabilirlik.** Aynı spec, aynı tohum ve aynı iş parçacığı sayısı aynı makinede aynı
k'yı verir (ölçülen fark 10⁻¹⁵ mertebesi: OpenMP toplama sırası). Tohum değişirse sonuç
istatistik içinde değişir — bu beklenen davranıştır. Her koşu dizinindeki `kapsul.json` bu
bilgiyi saklar; yeniden üretmek için [terminal](08-terminal.md#terminal) bölümündeki
`yeniden` komutuna bakın.

<a id="kaynak-yakinsamasi"></a>
## 6.2 Kaynak yakınsaması (Shannon entropisi)

Özdeğer hesabında başlangıç kaynağı (nokta ya da kutu) gerçek fisyon dağılımı değildir; pasif
çevrimler boyunca gerçek dağılıma doğru yerleşir. Pasif dönem bitmeden kaynak yerleşmemişse
aktif çevrimler **yanlı** bir dağılımdan sayılır ve k-eff yanlı çıkar. Bu, sonuca bakarak fark
edilmez; σ küçük görünür, sayı makul görünür.

**Shannon entropisi** fisyon kaynağının bir ağ (mesh) üzerinde ne kadar yayıldığını tek bir
sayıyla ölçer. Hesap ayarlarında varsayılan olarak **açıktır** (`ayarlar.entropi_mesh`,
varsayılan ağ 8 × 8 × 1). Çalıştır sayfasındaki entropi grafiği pasif çevrimler boyunca
düzleşmelidir.

**Araç yakınsamayı nasıl değerlendirir?** (`cekirdek/kosucu.py`, `entropi_yakinsama`)

1. **Plato**, aktif dönemin son yarısıdır: ortalaması plato değeri, saçılması (σ) çevrim başına
   gürültü ölçüsüdür.
2. Pasif dönemin **son çeyreğinin** ortalaması platodan **2σ'dan çok** uzaksa kaynak pasif dönem
   sonunda hâlâ kayıyordur: "Pasif çevrim sayısını artırın — k-eff yanlı olabilir." Başta hızlı
   yükselme normaldir (nokta kaynaktan başlanırsa entropi sıfırdan başlar).
3. Aktif dönemin **ilk çeyreğinin** ortalaması platodan 2σ'dan çok uzaksa kaynak aktif dönemde de
   kaymıştır (az pasif çevrim): "aktif dönemde de kaymaya devam etti". Eski sürüm σ'yı bütün aktif
   dönemden aldığı için bu durumu kaçırıyordu (4 pasif çevrimli 3B kor "yakınsadı" çıkıyordu).

Değerlendirme yapılamayan durumlar da açıkça söylenir: pasif çevrim 4'ten azsa, aktif çevrim
çok azsa ya da entropi sabitse sonuç "değerlendirilemedi"dir — "yakınsadı" değil. Pratikte
20–50 pasif çevrim, büyük ve gevşek bağlı modellerde (tam kor, 3B katmanlı) daha fazlası gerekir.
Uygunluk panelindeki **K1** kuralı aynı ölçütü koşu sonrasında denetler.

> **Ölçülen örnek (README, `pwr_eksenel`).** Katmanlı 3B demette **40 pasif çevrim yetmedi**:
> entropi pasif dönemin sonunda hâlâ kayıyordu (kayma 0.0433 > 2σ = 0.0125). Pasif çevrim
> 100'e çıkarılınca kayma 0.0006'ya düştü.

> **Tam korlar.** `docs/ORNEKLER.md`'ye göre "Normal" hassasiyetin 40 pasif çevrimi tam korlar
> için **sınırdadır** (entropi hâlâ düşüyordu). k karşılaştırması yapacaksanız pasif çevrimi
> artırın; YAVAŞ test OR12 20 000 × 160 / 60 kullanır.

**Entropi her şeyi görmez.** Entropi global bir skalerdir; bir yöndeki sorun başka yöndeki
baskın dağılımın içinde kaybolabilir. Ölçülmüş bir örnek: eski sürümde kutu kaynağın z aralığı
±1 cm'ye sabitti; 366 cm'lik 3B bir modelde kaynak merkezdeki 2 cm'lik dilimde başlıyor ve
eksenel güç şekli **aşırı tepeli** çıkıyordu (eksenel tepe 1.49 yerine 2.32). Entropi bunu
göstermedi, çünkü o geometride radyal dağılım baskındı. (Bu hata düzeltildi: kutu kaynak artık
modelin fisil yüksekliğini kapsar.) Uzun 3B modellerde entropi ağının z bölmesini 1'den büyük
seçin; ağın z sınırları modelin gerçek yüksekliğinden türetilir.

<a id="guc-dagilimi-yorum"></a>
## 6.3 Güç dağılımını yorumlamak

Güç dağılımı [Hesap ayarlarında](04f-hesap-ayarlari.md#hesap-ayarlari) açılır (yalnız fisil
çubuğu bir kafeste tekrarlanan modellerde görünür) ve sonuç Çalıştır sayfasında güç haritası
olarak çıkar. OpenMC'nin `DistribcellFilter`'ı kafeste tekrarlanan yakıt hücresinin her örneğini
ayrı sayar; 3B modelde buna eksenel dilimler eklenir. Adım adım ders:
[güç haritası ve F_ΔH](05-dersler.md#ders-guc).

| | Tanım | Neyi sınırlar |
|---|---|---|
| **F_ΔH** | en yüksek çubuk gücü / ortalama çubuk gücü (radyal) | sıcak kanalda soğutucu sıcaklık artışı (DNB marjı) |
| **F_q** | en yüksek yerel güç yoğunluğu / ortalama (radyal × eksenel) | yakıt merkez sıcaklığı, çizgisel güç (~400–500 W/cm) |

F_q yalnız 3B modelde tanımlıdır; 2B modelde araç "F_q tanımsız" yazar.

**Ölçülen referans (README, `pwr_3b`, örneğin ayarı 20 000 × 150 / 40, 20 eksenel dilim, 5
tohum, 01.10.2026):** tek koşuda F_ΔH 1.064–1.083, F_q 1.626–1.753; harita ortalamasının tepesi
F_ΔH = 1.0620 ± 0.0055, F_q = 1.600 ± 0.032; ortalama çizgisel güç 182 W/cm (17.6 MW/demet).
Eksenel katmanlı eşi `pwr_eksenel` ile aynı ayarla (20 000 × 250 / 100, 5 tohum): F_ΔH
1.0603 ± 0.0039 ve 1.0618 ± 0.0028 — istatistik içinde aynı (katmanlama radyal dağılıma
dokunmaz; iyi bir tutarlılık kontrolü); F_q 1.6362 ± 0.0147 → 1.5909 ± 0.0133 (−%2.8, 2.3σ;
su yansıtıcı eksenel profili düzleştirir).

**1. Raporlanan belirsizlikler iyimserdir.** Çubuk başına σ, çevrimler arası ilintiyi görmez.
Bu modelde ölçüldü (`pwr_3b`, 4000 parçacık, 3 bağımsız tohum): raporlanan σ bin başına
0.003–0.008, tohumlar arasındaki gerçek saçılma 0.07–0.17 — yaklaşık **20 kat**. Farkın büyük
kısmı ilintiden değil **yakınsamamış fisyon kaynağından** gelir: az parçacık ve az pasif
çevrimle tohumlar aynı dağılımın gürültülü örnekleri değil, farklı (yanlı) dağılımlardır. Bu bir
sapmadır; parçacık sayısıyla değil pasif çevrim sayısıyla azalır. Ne yapmalı:
- Shannon entropisini açık tutun; entropi düzleşene kadar pasif çevrimi artırın.
- Gerçek belirsizlik için modeli **5–10 bağımsız tohumla** koşun ve sonuçların saçılmasına
  bakın. Arayüzde bunun için ayrı bir düğme yoktur: Hesap ayarlarında **Rastgele tohum**'u
  değiştirip yeniden koşun ya da Python'da `cekirdek.guc.coklu_tohum()` işlevini kullanın
  (varsayılan 5 tohum; 3 tohumdan hesaplanan standart sapmanın kendisi ~%50 belirsizdir).

**2. F_ΔH bir maksimumdur ve az istatistikte yukarı yanlıdır.** Yüzlerce çubuğun en büyüğü
alındığı için gürültü tepeyi büyütür. Ölçüldü: aynı modelde 3000 parçacıkla 1.1455, 20 000
parçacıkla 1.0708. Çubuk başına istatistik sapma dağılımın gerçek saçılmasının %30'unu aşarsa
araç "F_ΔH bu durumda yukarı yanlıdır" uyarısını yazar; parçacık sayısını artırın.

**3. F_q eksenel çözünürlüğe bağlıdır.** Kaba dilimler tepeyi ortalar ve F_q'yu küçük gösterir
(saf kosinüs profilinde ince dilim sınırı π/2 = 1.571). En az 10–20 eksenel dilim kullanın
(`ayarlar.guc_dagilimi.eksenel_dilim`); 10'dan azında araç uyarır. Hedef çubuğun bulunmadığı
eksenel katmanlardaki boş dilimler F_q ortalamasına katılmaz ve adları yazılır.

**4. Kapsam.** F_ΔH ve F_q yalnız seçilen hedef çubuk türlerini kapsar. Modelin fisyon
enerjisinin bir kısmı haritada olmayan başka fisil bölgelerdeyse (başka çubuk türü, blanket),
araç bu payı yazar; en sıcak çubuk onlardan biri olabilir.

**5. Mutlak güç.** `ayarlar.guc_dagilimi.toplam_guc` isteğe bağlıdır ve **modelin kapsadığı
bölgenin** gücüdür, bütün korun değil. Örnek: 3400 MWth / 193 demet = 17.6 MW; tek demetlik
modelde `17.6e6` W girilir. Doğru girdiyle ortalama çizgisel güç ~182 W/cm çıkar; bu mertebede
değilse girdi yanlıştır. En yüksek çizgisel güç 500 W/cm'yi aşarsa araç "tipik PWR sınırı
~400–500 W/cm" notunu yazar. `kappa-fission` skoru gama ısınmasının yakıt dışında bırakılan
kısmını da (PWR'da ~%2–3) çubuklara yazar; çubuk gücü bu oranda büyük çıkar.

**Araçtaki eşikler eğitim içindir.** Yorum satırlarındaki "F_ΔH < 1.02 neredeyse düz",
"F_ΔH > 1.65 yüksek", "F_q > 2.6 yüksek" ifadeleri tipik PWR değerleridir, tasarım sınırı
değildir. Gerçek sınırlar tesise özeldir; uygunluk denetimindeki **K7-F** kuralı F_ΔH ve F_q'yu
yalnız kullanıcının girdiği sınırla karşılaştırır, sınır yoksa "karşılaştırılamadı" der.

<a id="once-ciz"></a>
## 6.4 Önce çiz, sonra çalıştır

Geometri önizlemesi başarıyla üretilmeden ve doğrulama hataları giderilmeden **ÇALIŞTIR
düğmesi etkinleşmez.** Bu, elle yazılan betiklerdeki *"çizimler doğruysa `model.run()`
satırının yorumunu kaldır"* alışkanlığının arayüze gömülmüş hâlidir — yanlış geometriyle saatlerce
koşmayı önler. ÇALIŞTIR'a basarsanız önce neyin eksik olduğu söylenir; alttaki durum çubuğu da
sıradaki adımı yazar ("Geometri çiziliyor; önizleme hazır olunca ÇALIŞTIR etkinleşir.").

Önizlemede neye bakılır:
- Her bölge beklenen malzemeyle mi dolu? Boş (void) bir bölge ya da yanlış renk, kayıp parçacık
  ve yanlış sonuç demektir.
- 3B modelde önizleme xy ve xz kesitlerini yan yana gösterir; eksenel katmanları, kontrol
  çubuğu ucunu ve yansıtıcıları xz kesitinde denetleyin.
- Önizlemeyi **F6** ile yenileyin. Çizim arka planda yapılır; model değişmedikçe kesit ve renk
  değişimi hızlıdır. Şüpheli bir bölgede Gelişmiş > **Çakışmaları göster** ile hücre
  çakışmalarını ayrı renkte görün.

Önizleme koşu yerine geçmez: kesit yalnız bir düzlemi gösterir. Koşu sonunda kayıp parçacık
sayısına bakın (uygunluk denetiminde **K3**: kayıp parçacık = 0 olmalı); kayıp parçacık geometri
hatasının belirtisidir.

<a id="tuzaklar"></a>
## 6.5 Bilinen tuzaklar

Bu liste geliştirme sırasında **ölçülerek** bulunan tuzaklardır. Çoğu araçta düzeltildi ya da
doğrulamaya bağlandı; burada, aynı tuzağa dışa aktarılan betikte ya da kendi OpenMC
çalışmanızda düşmemeniz için yazılıdır.

**Veri ve fizik**
- **Veri kütüphanesi sıcaklık aralıkları dar olabilir.** Nötron verisi 250–2500 K'dir ama
  **su için S(α,β) yalnızca 284–800 K**'dir. Aralık dışına çıkan bir sıcaklık taraması koşunun
  ortasında durur; araç aralıkları önceden okur (`cekirdek/veri_bilgi.py`) ve doğrulamada uyarır.
- **`HexLattice` ve `HexagonalPrism` yönelimleri aynı harfi kullanır ama tanımları terstir**
  (biri "y eksenine dik", diğeri "y eksenine paralel"). Aynı geometrik yönelim için **aynı harf**
  verilir; bu ölçümle doğrulandı. Yanlış eşleme %2.4 Δk sapmaya yol açıyordu. Altıgen tam korda
  demet pin kafesi 'y' ise kor kafesi 'x' olmalıdır (birbirine 90°).
- **Altıgen demet kılıfının (duct) apotemi** `(halka − 1)·adım·√3/2 + adım/2`'dir,
  `(halka − 0.5)·adım` değil. İkincisi köşelerde doğru görünür ama düz yüzlerde fazla boşluk
  bırakır.
- **Kutu kaynağın z aralığı modelin yüksekliğini kapsamalıdır** (bkz.
  [kaynak yakınsaması](#kaynak-yakinsamasi)); düzeltilmeden önce 3B güç şekli aşırı tepeliydi
  ve entropi bunu göstermedi.

**OpenMC API'si (dışa aktarılan betikle çalışanlar için)**
- **`Model.plot()` renk sözlüğü** SVG renk adı ya da `(R, G, B)` demeti ister; onaltılık renk
  dizesi `KeyError` verir.
- **Entropi açıkken OpenMC'nin çevrim satırı biçimi değişir** (ek sütun). Çıktıyı kendiniz
  ayrıştırıyorsanız iki biçimi de tanıyın.
- **`Tally.scores` hiçbir doğrulama yapmaz:** uydurma bir skor adı da kabul edilir, hata ancak
  koşuda çıkar. Araç küratörlü bir skor listesine göre doğrulamada *uyarı* verir.
- **`Tally.get_pandas_dataframe`'de `distribcell_paths` diye bir argüman yoktur**; doğrusu
  `paths=True`'dur.
- **`Cell.num_instances` önce `Geometry.determine_paths()` ister**, yoksa `ValueError` verir.

**Bulunan ve düzeltilen hatalar (kullanıcıya dönük özet)**
- **Önizleme, tally'ler yüzünden uygulamayı çökertiyordu.** `Model.plot()` OpenMC kütüphanesini
  başlatır ve tally filtrelerini de çözmeye çalışır; çözülemeyen bir filtre C++ tarafında süreci
  sonlandırıyordu (Python `try/except` bunu yakalayamaz). Önizleme artık tally'siz bir model
  çizer ve aynı anda ikinci bir çizim başlatılamaz. Önizlemede yine de bir çökme yaşarsanız
  günlük dosyasını ekleyerek bildirin (bkz. [terminal](08-terminal.md#terminal)).
- **S(α,β) kuralı saf zirkonyuma hidrojen öneriyordu.** Kural yalnız "elementler izinli kümenin
  alt kümesi mi" diye bakıyordu; {Zr} ⊆ {H, Zr} olduğu için saf Zr "zirkonyum hidrür" sayılıyordu.
  Her kurala zorunlu element kümesi eklendi; `pwr_pinhucre`'nin eski uyarısı bu yanlış alarmdı.
- **Eksenel katmanlama üç hata ortaya çıkardı (hepsi ölçümle bulundu).** (1) "Fisil aralık"ın
  iki ayrı tanımı kurucu ile betik arasında farklı kaynak kutusu kurduruyordu → 1300 pcm (Δk × 10⁵);
  tek tanıma indirildi. (2) Güç korunum tally'si bütün modeli sayıyordu → sahte "BOZUK"; referans
  tally aynı hücreye bağlandı. (3) Güç ağı hedef çubuktan taşıyordu → F_q %10.4 şişti
  (1.6435 → 1.8150); ağ artık hedef çubuğun aralığını kullanır. Ayrıca entropi ağının z sınırları
  sabitti; düzeltilince `pwr_eksenel`'de 40 pasif çevrimin yetmediğini bu uyarı yakaladı.
  *Ders: aynı sayıyı iki yoldan hesaplayan iki kod er ya da geç ayrışır.*
- **U₃Si₂-Al yoğunluğu yüklemeyle tutarsızdı.** Dispersiyon yakıtı 4.8 gU/cm³ yüklemede sabit
  5.4 g/cm³ ile kuruluyordu; doğrusu ~6.73 g/cm³'tür. Yoğunluk artık yüklemeden hesaplanır;
  elle verilmiş yoğunluk (eski kayıtlar, `mtr_plaka` örneği) aynen kullanılır.
- **Dışa aktarılan betik bazı adlarda sessizce farklı model kuruyordu.** "a b" ile "a_b" gibi
  adlar aynı Python değişkenine düşüyor, "class" ya da "openmc" gibi adlar betiği bozuyordu; kinetik
  açıkken betik β_eff tally'lerini yazmıyordu. Değişkenler artık türe göre önekli ve benzersizdir
  (`m_uo2`, `c_yakit_cubugu`); betik ile arayüz modelinin eşdeğerliği testle denetlenir.

<a id="bilinen-sinirlar"></a>
## 6.6 Bilinen sınırlar

Bunlar hata değil, aracın bilinçli kapsam sınırlarıdır; sonuçları yorumlarken akılda tutun.

- **Küresel düzenek kabukları arayüzden düzenlenemez**; yalnız JSON'dan
  (`ornekler/godiva_kriter.json`). Arayüz kabukları salt okunur gösterir.
- **Tambur yayı tek parçadır** ve tambur eksenel olarak bölünmez; eksenel katmanlar tamburlu korda
  kor silindirinin içinde çalışır, tamburlar ve yansıtıcı kuşak tam yüksekliği kaplar.
- **Katmana özel harf eşlemesi (`anahtar`) yalnız JSON'dan** girilir; eksenel katman tablosu onu
  silmez, "dosyadan" diye kilitli gösterir.
- **Sabit kaynakta uzaysal dağılım sınırlıdır:** nokta ya da kutu. Yüzey kaynağı ve kaynak
  dosyası (`source.h5`) desteklenmez.
- **Doz dönüşüm katsayıları yoktur:** akı tally'si vardır, akı → doz çarpanı yoktur. Akı
  tally'si hücre hacmiyle integrallidir (birimi n·cm/s ya da kaynak nötronu başına n·cm);
  ortalama akı için bölge hacmine bölün.
- **Arayüz yalnız malzemeleri içe aktarır** (Dosya menüsü, OpenMC XML). Ham CSG geometriyi
  "çubuk → kafes → kor" katmanlarına geri çevirmek genel olarak çözülemez; yanlış bir tahmin
  sessizce yanlış model üretirdi. Python betikleri de içe aktarılamaz.
- **Tükenmede fisyon verimi sabittir** (termal 0.0253 eV, hızlı 500 keV); OpenMC'nin spektrum
  ağırlıklı ortalama modu kullanılmaz. Tükenme yalnız özdeğer modundadır, kaldığı yerden
  sürdürülemez ve kontrol elemanları (B₄C çubuk, tambur) varsayılan olarak yanmaz
  (`tukenme.ek_malzemeler` ile eklenebilir).
- **MPI yoktur:** OpenMC bu kurulumda tek düğümde OpenMP ile çalışır
  (bkz. [HPC](08-terminal.md#hpc)).
- **Uygunluk denetimi ve V&V sertifika vermez** (bkz. [ne kanıtlar](07-uygunluk.md#ne-kanitlar)).

<a id="yerel-k"></a>
## 6.7 Yerel k ve demet k∞

**Yerel k** her pin ya da demet hücresinde

  k_yerel = νΣ_f φ / (Σ_a φ − X),  X = Σ (x − 1) R_(n,xn)

oranıdır. Hücreler kare kafesin hatvesine hizalı bir mesh'in binleridir; tally'ler
`yerel_k_pin` / `yerel_k_demet` ve filtresiz `yerel_k_toplam` adını taşır (**Hesap ayarları ›
Yerel k haritası** ya da `python -m cekirdek.yerel_k ekle model.json pin|demet -o yeni.json`).

- **Yerel üretim / yok olma oranıdır, k∞ değildir.** Bin sınırlarındaki net akım ve sızıntı
  tanıma girmez. Akı komşulardan gelen nötronları içerir; oranı bindeki spektrum belirler
  (iç demetin yerel k'sı, kor içi spektrumdaki k∞'una yakındır). Kritiklik globaldir:
  k_eff = ΣP / (ΣD + L) = k_harita (1 − ℓ), ℓ = L / (ΣD + L) (Duderstadt & Hamilton,
  *Nuclear Reactor Analysis*, 1976). Statepoint okunabildiğinde özet P/(D+L)'yi de verir.
- **(n,xn) paydadadır.** OpenMC `absorption`'ı (n,2n) gibi kanalları yok olma saymaz ve
  doğurdukları nötronlar `nu-fission`'a girmez. Sızıntısız dengede P + X = A olduğundan
  k = P/(A − X); c_xn = A/(A − X). Düzeltmesiz P/A ipucunda ayrıca gösterilir. Kanallar dört
  faktör dersiyle aynı listeden gelir (MT 11, 16, 17, 24, 25, 30, 37, 41, 42).
- **Ortalama:** ΣP / Σ(A − X) — net yok olma ağırlıklı aritmetik ortalama. Üretim ağırlıklı
  harmonik ortalama ancak bütün binler fisilse eşdeğerdir; P = 0 binlerin D'si paydaya ayrıca
  eklenir. Yalnız **sonsuz kafeste** (yansıtıcı sınırlı tek pin/demet) ve harita kapsamı 1
  iken k∞ tahminidir. Düz ya da hacim ağırlıklı ortalama değildir.
- **Koşunun k-eff'iyle karşılaştırma:** ΣP_model global k-tracklength ile birebir aynıdır;
  ΣD_model'in beklenen değeri 1 − L'dir (kaynak nötronu başına) ama tracklength tahmini
  olduğu için istatistikle sapar. Bu yüzden harita ortalaması, birleşik k-eff'ten D_model'in
  sapması ve tahminci farkı kadar ayrılır; ikisi korelasyonlu tahminlerdir.
- **Harita kapsamı** = Σ_harita (A − X) / (A − X)_model. Kanal kutusu, su aralığı ya da
  yansıtıcı haritanın dışında kalırsa 1'in altına düşer. 3B modelde **tüm model** kapsamı
  eksenel yansıtıcıyı da içerir; **yalnız aktif bölge** seçilirse kapsama < 1 olur.
- **Belirsizlik:** σ, pay ile paydanın korelasyonu yok sayılarak yayılır (ihtiyatlı; demet
  düzeyinde bin σ'ları bu yüzden büyüktür). Kapsama 1 iken ortalamanın σ'sı filtresiz
  tally'den alınır (binler arası korelasyon dahil); değilse binlerin karesel toplamıdır
  (binler arası korelasyon da yok sayılır). Bin σ'ları çevrimler arası korelasyonu görmez
  (iyimser, bkz. [6.3](#guc-dagilimi-yorum)): gerçek belirsizlik için birkaç tohum ve
  Shannon entropisiyle yakınsama denetimi.
- **Sınırlar:** yalnız kare kafes; altıgen kafes (OpenMC'de altıgen mesh yok), ötelenmiş /
  döndürülmüş kafes ve demetler arası boşluklu korda pin düzeyi açık hatayla reddedilir.
  Tek eksenel bin (radyal harita).

**Demet k∞ sihirbazı** (**Araçlar › Demet k∞ sihirbazı…**) her demet türünü yansıtıcı
sınırlı tek demet modeli (2B, tally/güç/tükenme kapalı, kaynak fisil kutu, kütüphane
kullanılan parçalara budanmış) olarak koşu kuyruğuyla ayrı koşar ve "demet türü × k∞ ± σ"
tablosunu verir. Model, elle kurulan tek demet modeliyle fiziksel olarak özdeştir; budama
rastgele gerçekleşmeyi değiştirebildiği için sonuçlar istatistik sınırında aynıdır
(σ_fark = √(σ₁² + σ₂²)). Sonuç sonsuz kafes k∞'udur: su aralığı, yansıtıcı, komşu
demetlerin spektral etkisi ve sızıntı yoktur. Yanmaya göre k∞ bu sürümde yoktur.

![Çeyrek kor, demet düzeyinde yerel k](../resimler/tr/k4_yerel_k_kor_demet.png)
