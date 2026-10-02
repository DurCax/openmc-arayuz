<a id="tukenme"></a>
## 4.9 Tükenme

Tükenme (yanma) hesabı yakıtın zaman içinde nasıl değiştiğini hesaplar: U-235 azalır, Pu-239
birikir, Xe-135 ve Sm-149 gibi fisyon ürünü zehirleri reaktiviteyi düşürür. Her adımda bir
transport çözülür, reaksiyon hızları alınır ve Bateman denklemleri OpenMC'nin CRAM
çözücüsüyle ilerletilir (`openmc.deplete`). Ayarlar spec'in `tukenme` bölümüne yazılır.

Sekme yalnız **özdeğer (k-eff) hesabında** ve geometride **fisil malzeme** varken görünür
(`uygunluk.tukenme_uygun`); sabit kaynaklı aktivasyon hesabı bu sürümde yoktur. Sekme yine
de açılırsa yalnız nedenini söyleyen boş durum ("Bu modelde tükenme hesabı yapılamaz")
görünür. Sayfa tek akıştır: açma anahtarı → **Yanma ayarları** → **İzlenen nüklidler** →
**Koşu** → **Sonuç** → **Ayrıntılı çıktı**. Tükenme kapalıyken yalnız anahtar ve kısa
açıklama görünür.

![Tükenme sekmesi: yanma ayarları, izlenen nüklidler ve sonuç grafiği](../resimler/tr/tukenme.png)

Koşu, arayüzün kendi sürecinde değil `openmc-arayuz-kosu --alt tukenme` **alt süreci**
olarak yapılır (arayüz bunu aynı Python ile `python -m cekirdek.giris --alt tukenme` diye
başlatır; OpenMC C++ tarafında bir `terminate()` bütün süreci öldürebilir; önizlemede
yaşandı). Terminalden aynısı: `python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 16`
([8. Terminal](08-terminal.md#terminal)).

### Açma anahtarı ve Yanma ayarları kartı

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Tükenme (yanma) hesabını etkinleştir** | Tükenmeyi açar. Kapatıp açmak önceki sonucu eskitmez. Açık değilken **Tükenmeyi başlat** çalışmaz ("Tükenme kapalı — yukarıdan etkinleştirin"). | — | — | Hesap ayarlarında sabit kaynak seçiliyken açmak: "tükenme Özdeğer (k-eff) hesabı gerektirir" hatası | `tukenme.var` |
| **Güç yoğunluğu** | Ağır metalin gramı başına güç. **Mutlak güç [W] kullanılmaz**: 2B bir modelde "cm başına" olmak zorunda kalırdı ve bu sessiz bir birim tuzağıdır; W/gHM geometriden bağımsızdır ve mühendislerin gerçekten verdiği sayıdır. | W/gHM | PWR 38–40, BWR ~25, SFR 50–100 (`pwr_tukenme`: 40) | Mutlak güç (MW) girmek: "güç yoğunluğu … W/gHM olağan dışı" uyarısı; 0: "güç yoğunluğu sıfırdan büyük olmalı" hatası | `tukenme.guc_yogunlugu` |
| **Adım birimi** | Adım uzunluklarının birimi: **gün** ya da **MWd/kg (yanma)**. İkisi güç yoğunluğuyla birbirine çevrilir (MWd/kg = gün × W/gHM / 1000). | gün \| MWd/kg | — | Yanma değerlerini gün birimiyle girmek (ör. "20" ile 20 MWd/kg yerine 20 gün) | `tukenme.adim_birimi` (`d` \| `MWd/kg`) |
| **Adımlar** | Adım uzunlukları, virgülle (birikimli değil; her biri bir aralığın uzunluğu). Altındaki özet adım sayısını, toplam gün ve MWd/kg'ı ve **transport çözümü** sayısını yazar. İlk adımları kısa tutun (ör. 0.5, 1.5): Xe-135 ~2 günde dengeye gelir ve PWR'da birkaç bin pcm'lik hızlı bir düşüş yaratır; uzun bir ilk adım bunu tek çizgiye ezer. | gün ya da MWd/kg | `pwr_tukenme`: 0.5, 1.5, 3, 5, 10, 30, 100, 350 gün (500 gün = 20 MWd/kg) | Sayı olmayan ya da negatif değer: "Adımlar geçersiz — …" (kırmızı); ilk adım uzun: "ilk adım … gün — Xe-135 dengesi (~2 gün) tek adıma eziliyor" uyarısı; boş: "en az bir zaman adımı gerekli" hatası | `tukenme.adimlar` |
| **Yanan malzemeler** | Salt okunur: yanacak malzemeler, **analitik hacimleri** ve hesap yöntemi. Fisil malzemeler ve yanabilir zehirler (Gd, Er) kendiliğinden yanar. Hacim bölge alanı × (katman yüksekliği × o katmandaki örnek sayısı) toplamıdır; çubuk, plaka, küresel kabuk, tamburlu kor silindiri, eksenel katmanlar, altıgen demetler ve kare/altıgen pin kesiti desteklenir. | cm³ | `pwr_17x17` uo2: 139.147 cm³ (2B: 1 cm yükseklik için) | Hacmi önemsiz sanmak: hacim f kat yanlışsa yanma hızı da f kat yanlış olur ve **k-eff'te iz bırakmaz**; "hacim hesaplanamıyor" hatası koşuyu durdurur | (hesaplanır, saklanmaz) |
| **Ek yanan malzemeler** | Yakıt dışında yanması istenen malzemeler (ör. B₄C kontrol çubuğu, tambur emicisi): listede işaretlenir. Fisil malzemeler ve yanabilir zehirler "otomatik" notuyla işaretli ve kilitli durur. Dosyada olup modelde tanımsız bir ad silinmez, "(tanımsız)" notuyla gösterilir. Her ek malzemenin kesin hacmi gerekir. | — | genellikle boş | Tanımsız ad: "tanımsız ek malzeme" hatası; kontrol elemanlarının kendiliğinden yandığını sanmak (yanmazlar) | `tukenme.ek_malzemeler` |

**Yanan malzemeler** satırının altında zincir dosyası kullanılamıyorsa kırmızı uyarı çıkar
("Zincir dosyası kullanılamıyor: … (Gelişmiş › Zincir)"); çözüm
`./veri_indir.sh --yalniz-zincir` ([9. Sorun giderme](09-sorun-giderme.md#kurulum-sorunlari)).

### Gelişmiş bölümü

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Zincir** | Tükenme zinciri: **Otomatik (spektrumdan)** (modelde hidrojen/döteryum ya da grafit S(α,β)'sı varsa termal, yoksa hızlı; berilyum bilerek sayılmaz), **ENDF/B-VIII.0 termal (3820 nüklid)**, **ENDF/B-VIII.0 hızlı (3820 nüklid)**, **CASL basit termal / hızlı (228 nüklid, ~3 kat hızlı)**. Altındaki satır seçilen dosyayı, **fisyon verimi enerjisini** ve gerekçeyi yazar. | — | otomatik | Hızlı bir sistemde termal zincir seçmek: "… zincir seçildi ama model … spektrumlu görünüyor" uyarısı; CASL'ı nihai sonuç sanmak (ön inceleme içindir; "basitleştirilmiş CASL zinciri" bilgisi) | `tukenme.zincir` (`otomatik` \| `termal` \| `hizli` \| `casl_termal` \| `casl_hizli`) |
| **Entegratör** | Zaman integrasyonu: **CECM (öngörücü-düzeltici, adım başına 2 transport)** ya da **Predictor (adım başına 1 transport, kaba)**. | — | cecm | Predictor'ı uzun adımlarla kullanmak (kaba; adımları kısaltın ya da CECM seçin) | `tukenme.entegrator` (`cecm` \| `predictor`) |
| **Çubuk çubuk yanma (her örnek ayrı malzeme — çok ağır)** | Kapalıyken aynı malzemeyi içeren bütün hücreler **tek malzeme** olarak yanar (demet ortalaması, hızlı). Açıkken yakıtın her örneği (demetteki her çubuk) ayrı malzeme olur; bellek ve süre örnek sayısıyla artar (17×17: 264, MTR: 23 örnek). Yalnız bir yanabilir malzeme geometride birden fazla kez geçiyorsa görünür. | — | kapalı | Kesik (kırpılan) konumlu gelişmiş geometride açmak: "çubuk çubuk yanmada örnek hacmi kesin değil" hatası | `tukenme.malzemeleri_ayir` |

**Zincir: termal mi hızlı mı — ve fisyon verimi.** İki ENDF/B-VIII.0 zinciri 101 nüklidin
yakalama dallanma oranında farklıdır (ör. Am-241(n,γ) → Am-242m termalde %8.1, hızlıda
%13.2). Ama zincir yalnız dallanma oranlarını değiştirir; **fisyon ürünü verimleri ayrı
bir ayardır** ve OpenMC'nin varsayılanı sabit 0.0253 eV'tur — hızlı zincir seçilse bile.
Bu araç hızlı sistemde verim enerjisini 500 keV'e çeker (U-235 → Xe-135 bağımsız verimi:
termalde 0.00079, hızlıda 0.00120). Spektrum ağırlıklı `average` modu kullanılmaz (README
"Bilinen sınırlar").

### İzlenen nüklidler kartı

Grafikte, tabloda ve CSV'de izlenecek nüklidleri seçer; seçim **fizik değildir**: değişince
önceki sonuç yeniden koşmadan aynı sonuç dosyasından güncellenir ve sonuç "eski" sayılmaz.

| Öğe | Ne yapar |
|---|---|
| Arama kutusu | Yazımı normalleştirerek arar: "xe-13", "am242m", "PU" (Ara: Xe-135, pu, am242m…). |
| Ağaç | Zincirdeki nüklidler gruplu (uranyum, plütonyum, Xe/Sm dinamiği, fisyon ürünü zehirleri, yanabilir zehirler, atık / ısı…); grup başlığında seçili/toplam sayısı. |
| Hazır setler | Temel, Pu vektörü, Zehirler, Minör aktinitler, Atık / ısı… — tek tıkla eklenir. |
| Çipler | Seçili nüklidler; × ile kaldırılır. Seçili ama zincirde olmayan ad **kırmızı çip** olur (silinmez; ipucunda en yakın ad). |

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| İzlenen nüklidler | Seçim listesi (OpenMC adları: `U235`, `Pu239`, `Xe135`, `Am242_m1`). | — | varsayılan: U235, U238, Pu239, Pu240, Pu241, Xe135, Sm149 | "Xe-135" gibi OpenMC dışı yazım (eskiden sessizce atlanıyordu; şimdi kırmızı çip ve "izlenen nüklid zincirde yok" hatası) | `tukenme.izlenen` |

### Koşu kartı

**Tükenmeyi başlat** koşuyu başlatır, **Durdur** sonlandırır. Düğme, doğrulama kapısı
geçilmeden (önizleme çizilmeden, hata varken) çalışmaz; altındaki satır nedenini söyler.
İlerleme **ölçülür, tahmin edilmez**: toplam transport sayısı bilinir ((adım × entegratör
başına transport) + 1) ve ilk transport bittiğinde kalan süre onun gerçek süresinden
hesaplanır ("İlk transport bekleniyor — kalan süre ondan ölçülecek."). İş parçacığı sayısı
**Çalıştır** sayfasındaki değerdir (`calistirma.is_parcacigi`).

Koşu başında spec'in kopyası (`tukenme_spec.json`) sonuçla aynı dizine yazılır ve önce eski
sonuç (`depletion_results.h5`) silinir: yarıda kalan bir koşu eski sonucu yeni kaydın
yanında bırakıp "güncel" gösterilmesine yol açardı. Başka bir proje açılırsa süren koşunun
sonucu yeni projeye yazılmaz.

**Maliyet (ölçülmüş).** Zincirdeki nüklidler yakıta eklenir, transport bu yüzden yavaşlar.
Pin hücre, 2000 × 20 parçacık, 2 transport: CASL (228 nüklid) 37 s, ENDF/B-VIII.0 (3820
nüklid) 125 s. `pwr_tukenme` (17 transport, 5000 × 60) ~50 dakikadır (README).

### Sonuç kartı

| Öğe | Ne gösterir |
|---|---|
| Önceki sonuç satırı | Sekme açılışta son koşunun sonucunu gösterir (50 dakikalık koşuyu görmek için yeniden koşmak gerekmez). Üç durum: "Önceki koşunun sonucu (…) — **bu modele ait**."; kırmızı ve kalın "**Eski sonuç** (…): model o koşudan beri değişti (…). Gösterilen sayılar bu modele ait değil — yeniden koşun." (hangi bölümün değiştiği yazılır); "… bu modele ait olduğu **doğrulanamıyor**" (kayıt yok). Yarım kalmış koşu "Yarım kalmış koşu (…): N / M adım tamamlanmış" diye ayrıca yazılır. |
| Grafik | Üstte k-eff (± 1σ) – zaman, altta seçili nüklidlerin atom yoğunluğu – zaman. |
| Tablo | gün, MWd/kg, k-eff, ρ [pcm] (ρ = (k − 1)/k, pcm = Δρ × 10⁵). |
| CSV olarak dışa aktar | Zaman [gün], yanma [MWd/kg], k, σ ve seçili her nüklidin her malzemede atom sayısı ve yoğunluğu [atom/b-cm]. Ondalık ayırıcı nokta, alan ayırıcı virgül, tam hassasiyet. |

Eskime karşılaştırması metinle (hash) değil Python eşitliğiyle yapılır (JSON'da `3` ile `3.0`
aynı sayıdır). Ad, açıklama, koşu dizini ve izlenen nüklidler fiziği etkilemediği için
sayılmaz; tükenmeyi kapatıp açmak da sonucu eskitmez. Sonuç **kayıttaki** spec'e göre okunur
(malzeme eşlemesi ve hacimler koşudaki modelden gelir). Okuma arka planda yapılır (~3 s).

**Ayrıntılı çıktı** (katlanır) OpenMC ve `cekirdek.tukenme` çıktısını gösterir; hata olursa
kendiliğinden açılır.

<a id="tukenme-pin-gucu"></a>
#### Yanmaya göre pin gücü

Modelde güç tally'si kurulabiliyorsa (çubuklar bir kafeste tekrarlanıyorsa) tükenme koşusu her
adımda çubuk güç dağılımını da sayar — Hesap ayarlarındaki güç dağılımı kapalı olsa bile
(hedef seçilmemişse bütün yakıt çubukları). Kapatmak için spec'te `tukenme.adim_gucu` = `false`.
OpenMC her adımın **başındaki** transporttan sonra `openmc_simulation_n<i>.h5` yazar; bunlar
`depletion_results.h5`'in zaman noktalarına bire bir karşılık gelir (CECM'in düzeltici
transportu yazılmaz: gösterilen dağılım adımın başındakidir). Yeni koşu eski adım dosyalarını siler.

Sonuç kartının altında (adım dosyası varsa):

| Öğe | Ne gösterir |
|---|---|
| **Adım:** | Adım seçici (adım, gün, MWd/kg); altındaki pin tablosu o adımın tablosudur ([pin gücü tablosu](04g-calistir.md#calistir-pin-tablosu) ile aynı: sırala, süz, **Çeyrek katla**). |
| Grafik (sol) | Tablodan seçilen çubukların bağıl gücü – yanma (± 1σ); her seçim listeye eklenir (en çok 6). Başlangıçta en sıcak çubuk. **Seçimi temizle** listeyi boşaltır. |
| Grafik (sağ) ve tablo | Adım başına F_ΔH ve F_q (3B) ± σ ve en yüksek q′. |
| **Adım × pin kaydet…** | Her adımın pin tablosu tek dosyada: adım, zaman [gün], yanma [MWd/kg] + pin sütunları (CSV; openpyxl kuruluysa Excel). |
| **Tepe faktörleri CSV…** | Adım başına F_ΔH, F_q, σ'ları ve en yüksek q′. |

Mutlak güç adımın kaynak gücüdür (güç yoğunluğu × ağır metal; `Results.get_source_rates`);
2B modelde güç ve q′ 1 cm yükseklik başınadır (tükenme hacmi gibi; tablo başlığı
"Güç [W/cm yükseklik]", dosyada `W_per_cm`). **Çubuk çubuk yanma kapalıyken** bütün çubuklar
aynı ortalama bileşimle yanar: dağılımın yanmayla değişimi pin başına yanmayı yansıtmaz
(sıcak çubukların daha hızlı yanması görülmez). Pin gücü çubuğun bütün yakıt bölgelerinin
(Gd pininde bütün halkaların) toplamıdır. Gelişmiş'teki **Adım başına pin gücü** kutusu
(`tukenme.adim_gucu`) ölçümü kapatır; sonucu eskitmez. Bağıl güç her adımda o
adımın yakıt çubuğu ortalamasına göredir. Ders: [5.7](05-dersler.md#ders-guc-yanma).

### Örnek ve doğrulama

`ornekler/pwr_tukenme.json`: `pwr_pinhucre` ile aynı pin, 40 W/gHM, 500 gün (20 MWd/kg),
tam ENDF/B-VIII.0 termal zincir, CECM. Ölçülen: k∞ 1.35930 ± 0.00184 (0 gün) → 1.06545 ±
0.00168 (500 gün); Xe-135 + erken Sm-149 (0 → 2 gün) Δρ = −2634 ± 158 pcm (pcm = Δρ × 10⁵).
Adım adım: [tükenme dersi](05-dersler.md#ders-tukenme). Analitik doğrulama (Bateman, zincirin
kendi yarı ömürleriyle on hanede) ve hacimlerin OpenMC stokastik hacmiyle 1σ içinde
uyuşması testlerdedir (README "Tükenme").

### Sık doğrulama bulguları (`tukenme`, `tukenme/<malzeme>`)

| Bulgu (özet) | Seviye | Çözüm |
|---|---|---|
| tükenme Özdeğer (k-eff) hesabı gerektirir | hata | Hesap ayarlarında **Hesap türü**'nü özdeğer yapın ([4.6](04f-hesap-ayarlari.md#hesap-ayarlari)). |
| tükenme yapılamaz: geometride fisil (yakıt) malzeme yok | hata | Yanacak yakıt geometride yer almalı. |
| zincir dosyası eksik / bozuk | hata | `./veri_indir.sh --yalniz-zincir`; kaynak ve sha256: `~/nucdata/chain/KAYNAK.txt`. |
| izlenen nüklid zincirde yok: '…' | hata | Kırmızı çipi kaldırın ya da ipucundaki adı seçin. |
| ilk adım … gün — Xe-135 dengesi (~2 gün) tek adıma eziliyor | uyarı | İlk adımları 0.5, 1.5 gün yapın. |
| aktif istatistik az (… parçacık × … çevrim) | uyarı | Hesap ayarlarında parçacık ve çevrim sayısını artırın. |
| hacim hesaplanamıyor | hata | Desteklenmeyen geometri; gelişmiş modelde kesik konumları azaltın. |
| yanabilir zehir '…' tükenmeye katılmıyor | uyarı | Hacmi analitik bilinmiyor; malzeme koşu boyunca taze kalır ve ömür sonunda kontrol değerini abartır. |

Bütün bulgular: [9. Sorun giderme](09-sorun-giderme.md#bulgu-turleri). Sınırlar: tükenme
kaldığı yerden sürdürülemez (her koşu baştan), kontrol elemanları kendiliğinden yanmaz
(`tukenme.ek_malzemeler` ile eklenir), yalnız özdeğer modunda ([6. Bilinen sınırlar](06-sonuclar.md#bilinen-sinirlar)).
