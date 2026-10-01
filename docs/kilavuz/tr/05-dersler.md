<a id="dersler"></a>
# 5. Rehberli dersler

Her ders bir örnek dosyayla başlar, arayüzde adım adım ilerler ve **beklenen sonuçla** biter.
Dersler kolaydan zora sıralıdır; 1. ders ötekilerin ön koşuludur. Örnekler başlangıç ekranının
örnek listesinden ya da **Dosya › Aç…** ile açılır ve **kopya** olarak açılır: `ornekler/`
altındaki dosyalar test referansıdır, üzerlerine yazılmaz. Kendi değişikliklerinizi saklamak
için **Dosya › Farklı kaydet…** kullanın.

| Ders | Konu | Örnek dosya | Seviye |
|---|---|---|---|
| [5.1](#ders-demet) | Demet k∞ | `ornekler/pwr_17x17.json` | giriş |
| [5.2](#ders-tam-kor) | Tam kor (kare harita) | `ornekler/pwr_smr_kor.json` | orta |
| [5.3](#ders-altigen-kor) | Altıgen demet ve altıgen kor | `ornekler/sfr_altigen.json`, `ornekler/vver1000_kor.json` | orta |
| [5.4](#ders-kare-altigen) | Kare çekirdek + altıgen halka | `ornekler/pwr_kare_altigen_halka.json` | ileri |
| [5.5](#ders-tambur) | Tamburu herhangi bir geometriye yerleştirmek | `ornekler/kafes_tamburlu_yansitici.json`, `ornekler/altigen_tambur_halkasi.json` | ileri |
| [5.6](#ders-tukenme) | Tükenme ve nüklid seçimi | `ornekler/pwr_tukenme.json` | ileri |
| [5.7](#ders-guc) | Güç haritası ve F_ΔH | `ornekler/pwr_3b.json` | orta |
| [5.8](#ders-benchmark) | Benchmark ve C/E | `ornekler/godiva_kriter.json` ve `kriter_*` | giriş–ileri |
| [5.9](#ders-kritik-arama) | Kritik arama | `ornekler/pwr_17x17.json`, `ornekler/pwr_kontrol.json`, `ornekler/tamburlu_kor.json` | orta |
| [5.10](#ders-rapor) | Rapor ve uygunluk eki | herhangi bir koşu | orta |

**Beklenen sonuçlar nereden geliyor?** Her değer bir kaynağa dayanır: örnek dosyasının
`referans.olcum` alanı, [VV.md](../../VV.md), [ORNEKLER.md](../../ORNEKLER.md) ya da
[README.md](../../../README.md) ölçüm tabloları. Ölçüm koşulu (parçacık × çevrim / pasif çevrim)
her derste yazılıdır. Monte Carlo sonucu istatistiktir: aynı ayarla farklı tohum ya da farklı
iş parçacığı sayısıyla son hanelerde fark olur; **farklı ayarla 2–3σ fark olağandır**. Belirsizlik
her yerde 1σ standart belirsizliktir. Sonucun nasıl okunacağı:
[6. Sonuçları yorumlamak](06-sonuclar.md#sonuclar).

Kenar çubuğundaki sayfa adları: **Malzemeler**, **Parçalar**, **Demet**, **Geometri**,
**Hesap ayarları**, **Çalıştır**, **Analiz**, **Tükenme**. Yalnızca modelde anlamlı olan
sayfalar görünür ([4.0 Pencerenin düzeni](04-sekmeler.md#pencere-duzeni)).

---

<a id="ders-demet"></a>
## 5.1 Demet k∞: PWR 17×17

**Örnek dosya:** `ornekler/pwr_17x17.json` · **Seviye:** giriş · **Tahmini süre:** 15 dakika
(koşu 1–3 dakika)

**Amaç.** Bir yakıt demetinin modelini sayfa sayfa okumak, neden **k∞** (sonsuz ortam çoğaltma
katsayısı) hesaplandığını anlamak ve ilk koşuyu yapıp sonucu ölçülen değerle karşılaştırmak.
Arayüzü ilk kez kullanıyorsanız önce [2. 15 dakikada ilk hesap](02-ilk-hesap.md#ilk-hesap)
bölümünü izleyin; bu ders aynı modelin fiziğine odaklanır.

**Adımlar.**

1. Başlangıç ekranının örnek listesinden **PWR 17×17 yakıt demeti**'ni açın. Üstteki model
   başlığı türü söyler: tek yakıt demeti, 2B, özdeğer (k-eff).
2. **Malzemeler** sayfası: dört malzeme vardır (`uo2`, `helyum`, `zirkaloy4`, `su`). `su`'ya
   çift tıklayın; kütüphane malzemesidir ve sıcaklık, bor gibi üretim parametreleriyle saklanır
   ([4.1 Malzemeler](04a-malzemeler.md#malzemeler)). Hiçbir şeyi değiştirmeden **İptal** ile
   kapatın.
3. **Parçalar** sayfası: yakıt çubuğu ve kılavuz boru. Yakıt çubuğunu seçin; **Radyal bölgeler**
   kartında yakıt, boşluk (gap), zarf bölgeleri içten dışa sıralıdır. Bölgelerin dış yarıçapı
   artan sırada olmalı ve en dış bölge hücre adımından küçük kalmalıdır
   ([4.2 Parçalar](04b-parcalar.md#parcalar)).
4. **Demet** sayfası: 17×17 kare harita; renkli palet hangi hücrede hangi çubuğun olduğunu
   gösterir. **Adım** 1.26 cm'dir (çubuk merkezleri arası).
5. **Geometri** sayfası: düzenek şablonu tek demettir; **Yan sınır** `reflective`
   (yansıtıcı) ve model 2B'dir (sonsuz yükseklik). Sağdaki önizlemede demetin xy kesiti
   çizilir.
6. **Neden k∞?** Bütün dış sınırlar yansıtıcı olduğunda nötron dışarı kaçamaz; model sonsuz
   tekrarlanan bir demet ortamıdır. Sonuç kartı bu durumda **k∞** yazar ve kritiklik hükmü
   vermez: k∞ > 1 reaktörün süperkritik olduğunu değil, yakıtın reaktivite fazlası taşıdığını
   söyler ([6.1 İstatistik](06-sonuclar.md#istatistik)).
7. **Hesap ayarları** sayfası: **Hesap hassasiyeti** **Normal** olmalıdır (10 000 parçacık × 150
   çevrim, 40 pasif). Altındaki satır beklenen k-eff belirsizliğini yazar
   ([4.6 Hesap ayarları](04f-hesap-ayarlari.md#hesap-ayarlari)).
8. **Çalıştır** sayfasına geçin. Düğmenin altındaki satır "Model çalıştırılmaya hazır." ya da
   uyarı sayısını yazmalıdır; önizleme çizilmeden düğme etkinleşmez
   ([Önce çiz, sonra çalıştır](06-sonuclar.md#once-ciz)). **Çalıştır**'a basın (ya da **F9**).
9. Koşu sürerken yakınsama grafiğini izleyin: pasif çevrimlerden sonra kümülatif ortalama
   düz bir banda oturmalıdır. **Shannon entropisi** rozeti **Yakınsadı** olmalıdır.

**Beklenen sonuç.** k∞ = **1.18325 ± 0.00075** ([README.md](../../../README.md) "Ölçülen
referans sonuçlar" tablosu; 24 iş parçacığıyla 44 s). Sizin değeriniz bu aralığın 2–3σ
yakınında olmalıdır. Daha büyük bir fark ya da kayıp parçacık uyarısı bir sorun işaretidir
([9. Sorun giderme](09-sorun-giderme.md#sorun-giderme)).

**Ne öğrendik / kontrol soruları.**

- Bütün yan sınırlar `vacuum` olsaydı sonuç k∞ mu, k-eff mi olurdu? Tek bir demette değer büyür mü,
  küçülür mü? (Sızıntı → k-eff, küçülür.)
- σ'yı yarıya indirmek için parçacık × aktif çevrim sayısını yaklaşık kaç kat artırmak gerekir?
  (σ ∝ 1/√N → yaklaşık 4 kat.)
- Regresyon çıpası: aynı yakıtın pin hücresi `ornekler/pwr_pinhucre.json` k∞ = 1.3570 ± 0.0020
  vermelidir. Demet neden daha düşük? (Kılavuz borulardaki su ve demet içi heterojenlik.)

---

<a id="ders-tam-kor"></a>
## 5.2 Tam kor: kare SMR koru

**Örnek dosya:** `ornekler/pwr_smr_kor.json` (ayrıca `ornekler/pwr_ceyrek_kor.json`) ·
**Seviye:** orta · **Tahmini süre:** 30 dakika (Normal koşu 1–3 dakika)

**Amaç.** Demetleri bir kor haritasına yerleştirmek, sonlu bir korda sızıntının k-eff'i nasıl
düşürdüğünü görmek ve çeyrek kor simetrisini doğru sınır koşuluyla kurmak.

**Adımlar.**

1. **Kare SMR tam koru (52 demet)** örneğini açın. Model başlığında tür "Tam kor (kare harita)"
   görünür.
2. **Demet** sayfasında iki demet vardır: `demet_24` (%2.4) ve `demet_31` (%3.1); ikisi de
   PWR 17×17 demetidir.
3. **Geometri** sayfası, **Kor haritası** kartı: 12×12 harita, **Hücre adımı** (demet adımı)
   21.42 cm. Harfler: `A` → `demet_24` (iç bölge), `B` → `demet_31` (dış kuşak), `s` → `su`
   (çevredeki iki sıra su yansıtıcı). Paletten bir öge seçip hücrelere tıklayarak boyanır; sağ tık
   o hücrenin içeriğini seçer ([4.4.3 Kor haritası](04d-geometri.md#geo-harita)). Haritayı
   değiştirmeyin.
4. Aynı sayfada yükseklik **3B, katmanlı**dır: alt su 20 cm, aktif 200 cm, üst su 20 cm
   ([4.4.8 Eksenel katmanlar](04d-geometri.md#geo-katmanlar)). **Yan**, **Alt** ve **Üst sınır**
   `vacuum`'dur: nötron dışarı kaçar, sonuç **k-eff**'tir.
5. **Hesap ayarları**: örnek **Hızlı deneme** (1 000 × 60, 20 pasif) ile açılır; bu yalnızca
   modelin koştuğunu görmek içindir (σ birkaç yüz pcm). **Hesap hassasiyeti**'ni **Normal**'e
   alın.
6. **Çalıştır**. Sonuç kartının k-eff yorumuna bakın (kritik üstü / kritik / kritik altı;
   ölçüt |k − 1| ≤ 2σ). Entropi rozetini kontrol edin: tam korda 40 pasif çevrim kaynak
   yakınsaması için **sınırdadır** ([6.2 Kaynak yakınsaması](06-sonuclar.md#kaynak-yakinsamasi)).
7. (İsteğe bağlı) **Çeyrek kor:** `ornekler/pwr_ceyrek_kor.json`'u açın. Haritanın yalnızca
   çeyreği vardır; **Geometri** sayfasında **Yüz başına yan sınır** açıktır: −x ve +y yüzleri
   `reflective` (simetri düzlemleri), +x ve −y yüzleri `vacuum` (dış yüzler)
   ([4.4.6 Yükseklik ve sınır koşulları](04d-geometri.md#geo-yukseklik)).

**Beklenen sonuç.**

- Tam kor, **Normal** (10 000 × 150, 40 pasif): k-eff = **1.06005 ± 0.00086** ([ORNEKLER.md](../../ORNEKLER.md)
  "Hassasiyet ve koşu süreleri" tablosu; 6 iş parçacığıyla 81 s).
- Tam kor ile çeyrek kor, 20 000 × 160 çevrim / 60 pasif: **1.05881 ± 0.00059** ve
  **1.05922 ± 0.00066**; fark 41 pcm (Δk × 10⁵), yani 0.46σ ([ORNEKLER.md](../../ORNEKLER.md)
  "Çeyrek simetrik kor").

**Ne öğrendik / kontrol soruları.**

- Aynı demetlerin k∞'u (5.1 dersi, ~1.18) ile korun k-eff'i (~1.06) arasındaki fark nereden geliyor?
  (Sızıntı ve iç bölgenin düşük zenginliği.)
- Çeyrek kor neden **dama** desenli bir yüklemeyle kurulamaz? (Yansıtıcı simetri düzlemi çeyreği
  **aynalar**; dama deseninin ayna simetrisi yoktur, aynalanan kor başka bir yüklemedir —
  ölçülen fark +260 pcm. [ORNEKLER.md](../../ORNEKLER.md))
- Çeyrek kor aynı parçacık sayısında daha hızlı mı? (Hayır; kazanç demet başına istatistiktedir.)

---

<a id="ders-altigen-kor"></a>
## 5.3 Altıgen demet ve altıgen kor

**Örnek dosyalar:** `ornekler/sfr_altigen.json` (demet), `ornekler/vver1000_kor.json` (kor) ·
**Seviye:** orta · **Tahmini süre:** 40 dakika

**Amaç.** Altıgen kafesin halka düzenini ve **yönelim** kuralını öğrenmek; altıgen demetleri altıgen
bir kor haritasına yerleştirmek.

**Adımlar — altıgen demet.**

1. **SFR altıgen demet** örneğini açın. **Demet** sayfasında harita kare değil altıgendir:
   **Halka sayısı** 7 (merkez dahil; 1 + 6 + 12 + … = 127 çubuk), **Adım** 0.9 cm, **Yönelim**
   `y`. Altıgen haritada konumlar dıştan içe halka halka yazılır ([4.3 Demet](04c-demet.md#demet)).
2. **Geometri** sayfasında yan sınır yansıtıcıdır; sonuç yine k∞'dur. Bu demetin kılıfı (duct)
   yoktur; çubukların dışı **Demet dışı** dolgusuyla (`sodyum`) doludur.
3. **Hesap ayarları** dosyadaki gibi kalsın (10 000 × 120, 30 pasif). **Çalıştır**.

**Beklenen sonuç (demet).** k∞ = **1.46634 ± 0.00070** ([README.md](../../../README.md) "Ölçülen
referans sonuçlar"; 24 iş parçacığıyla 53 s). Hızlı spektrumlu, U-10Mo yakıtlı, sodyum soğutmalı bir
demet olduğu için k∞ PWR demetinden çok büyüktür.

**Adımlar — altıgen kor.**

4. **VVER-1000 tam koru (163 demet)** örneğini açın. **Demet** sayfasında üç demet vardır
   (`tvs_a20`, `tvs_b30`, `tvs_c44`); her biri 11 halkalı, pin kafesi **`y`** yönelimlidir.
5. **Geometri** sayfası: tür "Tam kor (altıgen harita)", **Halka sayısı** 8 (169 konum),
   **Demet adımı** 23.6 cm, kor kafesinin yönelimi **`x`**. Haritada dış halkanın altı köşesi
   `R` (çelik-su yansıtıcı) ile doludur; geri kalan 163 konum demettir. Yansıtıcı kuşak 20 cm'dir.
6. **Yönelim kuralı:** demet pin kafesi `y` ise kor kafesi `x` olmalıdır (ikisi birbirine 90°).
   Denemek için kor yönelimini geçici olarak `y` yapın: doğrulama panelinde her demet için
   **hata** çıkar: "'tvs_a20' demetinin yönelimi ('y') kor yönelimiyle aynı — demet köşeleri komşu
   hücreye taşar". **Ctrl+Z** ile geri alın. Bu kuralın
   arkasındaki ölçüm ve `HexLattice`/`HexagonalPrism` yönelim tuzağı:
   [6.5 Bilinen tuzaklar](06-sonuclar.md#tuzaklar).
7. Örnek **Hızlı deneme** ile açılır. **Hesap hassasiyeti**'ni **Normal** yapıp **Çalıştır**.

**Beklenen sonuç (kor).** k-eff = **1.09907 ± 0.00097**, **Normal** (10 000 × 150, 40 pasif;
8 iş parçacığıyla 66 s; [ORNEKLER.md](../../ORNEKLER.md) "Hassasiyet ve koşu süreleri"). Yükleme
deseni eğitim amaçlıdır; gerçek bir VVER-1000 haritası değildir.

**Ne öğrendik / kontrol soruları.**

- 8 halkalı bir altıgen kafeste kaç konum vardır? (1 + 3·n·(n−1) = 169.)
- Altıgen kafeste **adım** neyi ölçer? (Düz yüzden düz yüze; köşeden köşeye değil.)
- Kılıflı bir altıgen demette kılıfın (duct) apotemi neden `(halka − 1)·adım·√3/2 + adım/2`'dir,
  `(halka − 0.5)·adım` değil? ([6.5 Bilinen tuzaklar](06-sonuclar.md#tuzaklar))
