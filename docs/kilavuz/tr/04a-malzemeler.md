<a id="malzemeler"></a>
## 4.1 Malzemeler

Modeldeki her malzeme burada tanımlanır: yakıt, zarf ve yapısal malzemeler, soğutucu ve
moderatör, emici ve gaz. Parçalar (çubuk, plaka), demetler ve geometri malzemelere **adıyla**
başvurur. Malzeme eklemenin dört yolu vardır:

- **Kütüphaneden ekle…** (önerilen): 24 hazır, doğrulanmış bileşim. Üretim parametreleri
  (zenginlik, sıcaklık, bor…) malzemeyle birlikte saklanır; **Düzenle…** aynı parametre
  formunu açar ve malzeme o parametrelerden yeniden üretilir.
- **Elle tanımla…**: bileşimi element ya da izotop satırlarıyla kendiniz girersiniz.
- **Asistan…**: "Ne tasarlıyorsun?" sorusundan başlayan adım adım tasarım; zenginlik, %TD,
  bor, sıcaklık ve basınçtan bileşim ve yoğunluk hesaplanır ([Malzeme asistanı](#malzeme-asistani)).
- **Kütüphanem…**: bu bilgisayarda sakladığınız malzemeler ve PNNL-15870 içe aktarımı
  ([Kütüphanem](#kutuphanem)).

`bosluk` ayrılmış bir addır: geometride "Boş (madde yok)" yani void anlamına gelir ve
burada tanımlanmaz.

### Malzemeler kartı

Tablo her malzemenin özetini gösterir; satıra çift tıklamak düzenler. Sütunlar: **Renk**
(önizlemedeki renk), **Ad**, **Açıklama** (listelerde adın yanında görünen metin), **Rol**,
**Yoğunluk**, **Sıcaklık**, **S(α,β)** ve **Bileşim**. Adın ipucu malzemenin kütüphaneden mi
(hangi kayıttan) yoksa elle mi tanımlandığını söyler.

| Düğme | Ne yapar |
|---|---|
| Kütüphaneden ekle… | Kütüphane penceresini açar (aşağıda). |
| Elle tanımla… | Boş bir bileşim tablosuyla yeni malzeme penceresini açar. |
| Düzenle… | Seçili malzemeyi düzenler (çift tıkla aynı). |
| Kopyala | Seçili malzemenin `_2` ekli bir kopyasını ekler (ör. iki zenginlik için). |
| Asistan… | Malzeme asistanını açar (aşağıda); bitince malzeme projeye eklenir. |
| Kütüphanem… | Kullanıcı kütüphanesi ve PNNL-15870 penceresini açar (aşağıda). |
| Kütüphaneme kaydet | Seçili malzemeyi yalnız bu bilgisayardaki kütüphanenize kaydeder; ad çakışırsa `_2` eki alır. |
| Sil | Seçili malzemeyi siler. Malzeme modelde kullanılıyorsa kaç yerde kullanıldığını söyleyip onay ister; silinirse o yerler tanımsız kalır ve model kurulamaz. |

**Rol.** Arayüz her malzemenin rolünü bileşiminden çıkarır (`cekirdek/uygunluk.py`,
`malzeme_rolleri`): **yakıt** (atom numarası 90 ve üstü bir element içerir: Th, U, Pu…),
**gaz** (yoğunluk 0.01 g/cm³'ün altında), **soğutucu** ve **moderatör** (hafif, ağır ya da
borlu su ikisi birden; sodyum, LBE soğutucu; grafit, berilyum, ZrH moderatör), **emici**
(H, C, N, O dışındaki atomların en az %5'i B, Gd, Ag, In, Cd, Hf, Er, Eu, Dy ya da Sm),
**yapısal** (geri kalan her şey). Eser miktardaki (atom kesri %0.5'in altı) bileşenler aile
kuralına girmez: 1 ppm borlu grafit yine grafittir.
Rol bir alan değildir, düzenlenmez; şunları belirler: Parçalar şablonlarının hangi
malzemeyi seçtiği, malzeme listelerinde neyin sunulduğu (ör. kontrol çubuğunun izleyici
listesinde yakıt ve emici yoktur) ve Analiz'de hangi taramanın hangi malzemeye
uygulanabildiği (ör. bor taraması yalnız su içeren malzemeye).

**Ad değişimi** modeldeki bütün kullanım yerlerini günceller (çubuk bölgeleri, plakalar,
demet dış dolgusu, kor, eksenel katmanlar, gelişmiş geometri). Ad bir parça ya da demet adıyla
aynı olamaz: demet ve katman seçimlerinde aynı ad iki şeyi gösterirdi.

### Kütüphane penceresi ("Kütüphaneden malzeme ekle")

Solda malzemeler rol gruplarına ayrılmıştır: **Yakıt**, **Zarf ve yapısal**, **Soğutucu ve
moderatör**, **Emici**, **Gaz**. Bir malzeme seçilince sağda açıklaması, **Ad** alanı ve
yalnız o malzemede anlamlı parametreler görünür (UO₂'de bor sorulmaz, suda zenginlik
sorulmaz; sıcaklık her malzemede sorulur). Altta üretilecek bileşimin özeti, S(α,β)
tabloları ve açıklama metni yazar. Parametreler fiziksel olarak şüpheliyse (ör. %20 üstü
zenginlik, U₃Si₂-Al'da yoğunluk ile yükleme çelişkisi) formun altında ⚠ uyarısı çıkar;
uyarı malzemeyi değiştirmez. Bu değerlerle malzeme kurulamıyorsa (ör. alüminyuma yer
kalmıyor) **Ekle** düğmesi kapanır ve nedeni yazılır.

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Ad** | Malzemenin modeldeki adı; parçalar ona bu adla başvurur. Seçilen kayda göre önerilir (`uo2`, `uo2_2`…). | — | ASCII harf, rakam, `_`, `-` (betikte değişken adına dönüşür) | Var olan bir malzeme ya da parça adı; `bosluk`; başta/sonda boşluk | `malzemeler[].ad` |
| **U-235 ağırlıkça %** | U-235'in uranyum içindeki ağırlık yüzdesi (UO₂, UN, U-10Mo, U₃Si₂-Al). | % | 0.01–97; LWR 2–5 (`pwr_17x17` %3.2), HALEU 19.75 (U-10Mo, U₃Si₂-Al varsayılanı) | %5 üstünde doğrulama uyarır: OpenMC'nin zenginlik kısayolu U-234/U-235 oranını sabit 0.008 varsayar; %20 üstünde form da uyarır; %97 üstü tanımsız | `malzemeler[].kutup.param.zenginlik` |
| **Pu ağırlıkça %** | MOX'ta ağır metal (U + Pu) içindeki plütonyumun ağırlık yüzdesi. | % | 0.01–100; varsayılan 7 | Fisil Pu yüzdesiyle karıştırmak | `malzemeler[].kutup.param.pu_orani` |
| **Fisil Pu %** | Plütonyum içindeki Pu-239 + Pu-241 ağırlık yüzdesi; kalanı Pu-240 ve Pu-242. | % | 0–100; varsayılan 65 | Pu vektörü basitleştirilmiştir; ayrıntılı vektör gerekiyorsa elle tanımlayın | `malzemeler[].kutup.param.pu_fissil` |
| **Taşıyıcı U'da U-235 %** | MOX'taki uranyumun (çoğunlukla fakir U) U-235 ağırlık yüzdesi. | % | varsayılan 0.25 (fakir U) | Doğal U (0.711) yerine fakir U değerini unutmak | `malzemeler[].kutup.param.u_zenginlik` |
| **Uranyum yüklemesi** | U₃Si₂-Al dispersiyon yakıtında yakıt tabakasının uranyum yoğunluğu. Yoğunluk bundan (ve gözeneklilikten) hesaplanır. | gU/cm³ | 0.1–10; varsayılan 4.8 (MTR) | Sabit bir karışım yoğunluğu girmek: 4.8 gU/cm³'te karışım ≈ 6.73 g/cm³'tür, eski 5.4 g/cm³ alüminyum payını %23'ten %4'e düşürüyordu (README "Bilinen tuzaklar") | `malzemeler[].kutup.param.u_yukleme` |
| **Gözeneklilik** | Yakıt tabakasındaki boşluk hacim kesri. | — (kesir) | 0–0.3; varsayılan 0 | Yüzde olarak girmek (0.05 yerine 5) | `malzemeler[].kutup.param.gozeneklilik` |
| **Çözünmüş bor [ppm]** | Suda çözünmüş doğal borun ağırlıkça ppm'i (PWR kimyasal kontrolü). | ppm | 0–5000; README örnekleri: MTC ölçümü 1300 ppm, `pwr_17x17` kritik bor 3430 ppm | Borlu suyu ayrı bir malzeme sanmak: bor bu parametredir; bor taraması da bunu değiştirir | `malzemeler[].kutup.param.bor_ppm` |
| **D₂O saflığı (mol %)** | Ağır suyun molce D₂O yüzdesi; kalanı hafif sudur. | % | 50–100; varsayılan 99.75 | Saflığı %100 sanmak: küçük H₂O payı termal sistemlerde reaktiviteyi belirgin değiştirir | `malzemeler[].kutup.param.saflik` |
| **B-10 atomca %** | B₄C'de borun B-10 atom yüzdesi. En küçük değer (kutuda "doğal") doğal bor demektir. | % | doğal (≈19.9) – 100; `altigen_tambur_halkasi` %90 B-10 | Ağırlık yüzdesi girmek | `malzemeler[].kutup.param.b10_zenginlik` |
| **Yoğunluk** | Malzemenin kütle yoğunluğu. Su, LBE ve sodyumda sıcaklıktan hesaplanır ve salt okunur gösterilir (değiştirmek için sıcaklığı değiştirin). | g/cm³ | UO₂ 10.4, UN 13.5, U-10Mo 17.0, Zircaloy-4 6.55, SS-316 7.99, grafit 1.7, Be 1.85, B₄C 2.52, He 0.0001785 (kütüphane varsayılanları) | Kuramsal yoğunluk yerine pelet yoğunluğunu unutmak; suda yoğunluğu ayrıca değiştirmeye çalışmak | `malzemeler[].yogunluk.deger` |
| **Sıcaklık** | Tesir kesiti verisinin bu sıcaklıkta kullanılacağı malzeme sıcaklığı. Yanında °C karşılığı yazar. Suda yoğunluk da bu sıcaklıktaki doymuş sıvıdan hesaplanır. | K | 250–3000 (form); su 273.15–623.15; varsayılanlar: yakıt 900, zarf 600, su 293.6 | Kütüphanenin sıcaklık aralığı dışına çıkmak: nötron verisi 250–2500 K, **su için S(α,β) yalnız 284–800 K**; aralık dışı bir tarama koşunun ortasında patlar (README "Bilinen tuzaklar") | `malzemeler[].sicaklik` |

Kütüphane penceresinde **Ekle** malzemeyi ekler, **Vazgeç** kapatır. Eklenen malzemenin
`kutup` kaydı (`malzemeler[].kutup.anahtar` ve `kutup.param`) üretim parametrelerini tutar;
**Düzenle…** bu kayıttan formu yeniden açar.

### Kütüphanedeki malzemeler

| Grup | Kayıt (`kutup.anahtar`) | Malzeme | Parametreler (varsayılan) |
|---|---|---|---|
| Yakıt | `uo2` | UO₂ — uranyum dioksit | zenginlik 3.2 %, yoğunluk 10.4, 900 K |
| Yakıt | `mox` | MOX — karışık oksit (U, Pu)O₂ | Pu 7 %, fisil Pu 65 %, taşıyıcı U 0.25 %, 10.4, 900 K |
| Yakıt | `un` | UN — uranyum nitrür | 19.75 %, 13.5, 900 K |
| Yakıt | `u10mo` | U-10Mo — metalik uranyum alaşımı | 19.75 %, 17.0, 900 K |
| Yakıt | `u3si2_al` | U₃Si₂-Al — dispersiyon yakıtı | 4.8 gU/cm³, 19.75 %, gözeneklilik 0, 350 K |
| Yakıt | `uo2_gd2o3` | UO₂-Gd₂O₃ — gadolinyumlu yakıt | 3.2 %, Gd₂O₃ 8 %, 10.03 (%95 TD), 900 K |
| Zarf ve yapısal | `zirkaloy4`, `m5`, `ss304`, `ss316`, `fecral`, `ma956`, `sic`, `al6061` | Zircaloy-4, M5, SS-304, SS-316, FeCrAl, MA956, SiC, Al-6061 | yoğunluk ve sıcaklık |
| Soğutucu ve moderatör | `su` | Hafif su (H₂O) | 293.6 K, bor 0 ppm; yoğunluk sıcaklıktan |
| Soğutucu ve moderatör | `agir_su` | Ağır su (D₂O) | saflık 99.75 %, 1.1056, 293.6 K |
| Soğutucu ve moderatör | `sodyum`, `lbe` | Sıvı sodyum, kurşun-bizmut ötektiği | sıcaklık (673 K, 723 K); yoğunluk sıcaklıktan |
| Soğutucu ve moderatör | `grafit`, `berilyum` | Grafit (C), Berilyum (Be) | yoğunluk ve sıcaklık |
| Emici | `b4c`, `agincd`, `gd2o3` | B₄C, Ag-In-Cd, Gd₂O₃ | B₄C'de B-10 yüzdesi; yoğunluk ve sıcaklık |
| Gaz | `helyum` | Helyum (He) | 0.0001785 g/cm³, 600 K |

Kütüphane malzemesinin S(α,β) tablosu bileşimden kendiliğinden seçilir (su için
`c_H_in_H2O`, grafit için `c_Graphite` gibi).

### Malzeme penceresi (düzenleme ve elle tanımlama)

**Kütüphane malzemesi** düzenlenirken pencere kütüphanedekiyle aynı parametre formunu
gösterir. Gelişmiş bölümünde üretilen bileşim salt okunur bir tabloda görünür;
**Bileşimi elle düzenle** malzemeyi kütüphane parametrelerinden ayırır (zenginlik, sıcaklık
gibi değerler bir daha otomatik hesaplanmaz). Bir kütüphane malzemesi JSON'da elle
değiştirildiyse arayüz bunu fark eder ve bileşim tablosuyla açar.

**Elle tanımlanan malzemede** form şudur:

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Ad** | Malzemenin adı (yukarıdaki kurallar). | — | — | Ad değişimi bütün başvuruları günceller; aynı adlı ikinci malzeme hatadır ("aynı ad 2 kez tanımlanmış") | `malzemeler[].ad` |
| **Açıklama** | Listelerde adın yanında görünen metin (ör. "UO₂ %4.0"). Elle malzemede kendiliğinden yenilenmez. | — | — | Zenginliği değiştirip açıklamayı eski bırakmak | `malzemeler[].gorunen_ad` |
| **Yoğunluk** | Yoğunluğun değeri; birimi yanında yazar (birim Gelişmiş'tedir). Değer yuvarlanmadan saklanır. | Yoğunluk birimi | pozitif | 0 ya da boş ("yoğunluk verilmemiş", "yoğunluk sıfırdan büyük olmalı"); atom/b-cm değerini g/cm³ birimiyle girmek | `malzemeler[].yogunluk.deger` |
| **Sıcaklık** | Malzeme sıcaklığı (yukarıya bakın). | K | 0–5000 (form) | Veri aralığı dışı (250–2500 K; su S(α,β) 284–800 K) | `malzemeler[].sicaklik` |
| **Termal saçılma S(α,β)** | Bileşime uyan termal saçılma tabloları; bileşim su/grafit görünümüne yeni geldiyse öneri kendiliğinden seçilir. "Yok (termal saçılma verisi ekleme)" da seçilebilir. Uyan tablo yoksa satır gizlenir. | — | su `c_H_in_H2O`, grafit `c_Graphite`, ZrH `c_H_in_ZrH` | Eksik bırakmak: termal spektrumda k yüzde mertebesinde kayar (uyarı: "… görünümünde ama termal saçılma verisi (S(α,β)) eklenmemiş") | `malzemeler[].sab` |
| **Renk** (Gelişmiş) | Önizleme ve paletlerdeki renk. | RGB | — | — | `malzemeler[].renk` |
| **Yoğunluk birimi** (Gelişmiş) | g/cm³, atom/b-cm ya da kg/m³. | — | çoğunlukla g/cm³; kriter modelleri atom/b-cm | Birimi değiştirip değeri dönüştürmemek | `malzemeler[].yogunluk.birim` |
| **S(α,β) (elle)** (Gelişmiş) | Virgülle ayrılmış S(α,β) tablo adları; önerilen listede olmayan bir tablo için. | — | OpenMC tablo adları (`c_H_in_H2O, c_Graphite`) | Hidrojensiz malzemeye hidrojen tablosu yazmak (README tuzak: saf Zr'ye `c_H_in_ZrH`) | `malzemeler[].sab` |

**Bileşim** tablosunun sütunları (**Satır ekle** / **Satırı sil** düğmeleriyle):

| Sütun | Anlamı | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|
| **Tür** | Doğal element ya da İzotop (nüklid). | Geçersiz tür hatadır ("satırının türü geçersiz") | `malzemeler[].bilesim[].tur` (`element` \| `nuklid`) |
| **İsim** | Element sembolü (`U`, `O`, `Zr`) ya da nüklid adı (`U235`, `Am242_m1`). | Boş isim; kütüphanede olmayan nüklid (F5 veri denetimi yakalar) | `malzemeler[].bilesim[].isim` |
| **Miktar** | Satırın atom ya da ağırlık oranı (normalize edilmesi gerekmez). | 0 ya da negatif ("miktarı sıfırdan büyük olmalı") | `malzemeler[].bilesim[].miktar` |
| **Birim** | Atom oranı ya da Ağırlık oranı. Bir malzemede iki birimi karıştırmayın. | Geçersiz birim hatadır | `malzemeler[].bilesim[].birim` (`ao` \| `wo`) |
| **Zenginlik %** | Yalnız `U` element satırında yazılabilir: U-235 ağırlık yüzdesi; boş "doğal" demektir. | Başka elementte ya da nüklid satırında zenginlik hatadır (OpenMC kısayolu yalnız U'da çalışır); %5 üstü uyarı | `malzemeler[].bilesim[].zenginlik` |

Pencerenin altında bileşimin modelde hangi rolle tanınacağı yazar ("Bu bileşim modelde
şöyle tanınıyor: yakıt"). **Tamam** kaydeder; yoğunluk, isim ya da miktar eksikse kaydetmez
ve nedenini yazar.

<a id="malzeme-asistani"></a>
### Malzeme asistanı

**Asistan…** malzemeyi üç adımda kurar. Hesaplar `cekirdek/malzeme_hesap.py`,
`cekirdek/malzeme_sogutucu.py` ve `cekirdek/malzeme_tarif.py` içindedir; her formülün kaynağı
kodda yazılıdır. Her hesaplayıcı bağımsız bir el hesabıyla ya da kaynağın kendi tablosuyla
(IF97 resmî doğrulama tablosu, ANL/RE-95/2 Tablo 1.3-1, NIST) test edilir. Uygulamalı örnek:
[5.14 Malzeme asistanı ve kütüphanem](05-dersler.md#ders-malzeme-asistani).

1. **Ne tasarlıyorsun?** — **Yakıt**, **Kılıf (zarf)**, **Moderatör / soğutucu**, **Emici**,
   **Yapı malzemesi** ya da **Özel karışım**.
2. **Malzeme türü ve değerler** — yalnız o türe uygun alanlar sorulur. Sağdaki
   **Türetilmiş değerler** paneli her değişiklikte yeniden hesaplanır: yoğunluk (g/cm³ ve
   atom/b-cm), atom başına ortalama molar kütle, ağır metal yoğunluğu (gHM/cm³, Z ≥ 90),
   H/X (hidrojen / fisil atom: U-233, U-235, Pu-239, Pu-241) ve her nüklidin sayı yoğunluğu
   N_i, atomca ve ağırlıkça yüzdesi. Değer geçersizse (ör. 600 K'de 5 MPa: buhar bölgesi)
   nedeni kırmızı yazılır ve **İleri** kapanır.
3. **Doğrulama ve kaydetme** — bulgular listelenir: bileşim ve yoğunluk denetimi, S(α,β) önerisi
   (doğrulamanın kullandığı kuralla aynı), tesir kesiti kütüphanesinde **eksik nüklid** ve
   S(α,β) tablosu, sıcaklığın kütüphane aralığında olup olmadığı. `OPENMC_CROSS_SECTIONS`
   tanımlı değilse eksik nüklid denetimi **uyarıyla atlanır**. Hata varsa **Bitir** kapanır.
   **Ad**, **Projeye ekle** ve **Kütüphaneme de kaydet** buradadır.

| Tür | Alanlar | Hesap ve kaynak |
|---|---|---|
| UO₂ | U-235 ağırlıkça %, yoğunluk (%TD'den ya da doğrudan), O/M, sıcaklık | ρ = ρ_TD · %TD/100, ρ_TD = 10.963 g/cm³ (Fink, J. Nucl. Mater. 279 (2000) 1; 273 K: oda sıcaklığı değeri, ısıl genleşme uygulanmaz); U-234 = 0.0089·e, U-236 = 0.0046·e (ORNL/CSD/TM-244, OpenMC ile aynı). U-236 terimi geri kazanılmış uranyum karışmış ticari LEU'ya uydurulmuş ampiriktir: doğal beslemeden zenginleştirmede U-236 yoktur; bağıntı düşük zenginlik içindir, %5 üstünde doğrulama uyarır. |
| UO₂-Gd₂O₃ | zenginlik, Gd₂O₃ ağırlıkça %, %TD, sıcaklık | Kütle dengesi; TD ideal karışımdan 1/ρ = Σ w_i/ρ_i (Gd₂O₃ 7.407 g/cm³, CRC Handbook). Gd₂O₃ yoğunluğu faza bağlıdır (kübik 7.4–7.6, monoklinik ~8.3) ve Gd UO₂ içinde katı çözelti yapar: TD yalnız bir tahmindir. |
| MOX | Pu / ağır metal %, Pu-238…Pu-242 ve Am-241 (Pu+Am içinde ağırlıkça %), taşıyıcı U, ayrıştırmadan bu yana süre, %TD, O/M | O = x·M_O·Σ w_i/M_i; Pu-241 → Am-241 Bateman çözümü (T½ ENDF/B-VIII.0); TD UO₂ ve PuO₂ (11.46 g/cm³, Carbajo vd. 2001) ideal karışımı. Varsayılan Pu vektörü **örnektir**; ölçülmüş vektörü girin. Yaşlanma yalnız Pu-241 → Am-241'i izler (T½ = 14.29 yıl; NUBASE2020 14.290(6) yıl); Pu-238 → U-234 ve Am-241 → Np-237 ürünleri vektörden çıkar. Pu/HM yaşlanmadan **sonraki** (kullanım anı) Pu + Am payıdır; ağır metal Z ≥ 90 (Am dahil). |
| U-Mo | zenginlik, Mo ağırlıkça %, yoğunluk | — |
| Hafif su | sıcaklık, basınç, çözünmüş bor (kütlece ppm), B-10 atomca % | ρ(T, p) IAPWS-IF97 Bölge 1 (sıkıştırılmış sıvı), 273.15–623.15 K, p_s(T)–100 MPa; resmî doğrulama tablosuyla test edilir. Buhar bölgesi ya da aralık dışı **açık hatadır**. Bor ppm = mg B / kg çözelti; yoğunluk saf suyunkidir (borik asidin H₃BO₃ yoğunluğa ~+%0.2–0.3 etkisi ihmal edilir), bor yalnız bileşime girer. |
| Ağır su | sıcaklık, basınç, D₂O saflığı (mol %) | NIST WebBook (IAPWS R16-17 D₂O formülasyonu) tablosu, 0.1–20 MPa, 280 K'den doyma sıcaklığına kadar; T ve p'de doğrusal interpolasyon. Tablo izobarları 0.1, 1, 2, 5, 10, 12, 15, 20 MPa'dır: iki izobar arasındaki basınçta üst sıcaklık **küçük olan izobarın** doyma sıcaklığıdır (ör. 17 MPa'da 613.98 K). Kalanı hafif sudur (ideal karışım); saflık ≥ %99'da H₂O molar hacmi D₂O'nunkiyle eşit alınır (Kell 1977; 25 °C'de oran 1.0036). S(α,β): `c_D_in_D2O` + `c_O_in_D2O`. |
| Sıvı sodyum | sıcaklık | Fink & Leibowitz, ANL/RE-95/2 (1995), 371–2503.7 K; raporun Tablo 1.3-1 değerleriyle test edilir |
| B₄C | B-10 atomca %, %TD, sıcaklık | ρ_TD = 2.52 g/cm³ (CRC Handbook) |
| M5, SS-304 | yoğunluk, sıcaklık | M5: Zr-1Nb-0.125O (Mardon vd., ASTM STP 1354); SS-304: SCALE standart bileşim kütüphanesi (ρ = 7.94 g/cm³) |
| Zircaloy-4, FeCrAl, SS-316, SiC, Al-6061, grafit, berilyum, Ag-In-Cd, Gd₂O₃ | yoğunluk, sıcaklık | Hazır kütüphaneyle aynı kayıt; **Düzenle…** kütüphane formunu açar |
| Özel karışım | en çok dört bileşen (projeden ya da kütüphanenizden), yüzdeleri, oran türü (wo / ao / vo), sıcaklık | İdeal karışım (hacimler toplanır), `openmc.Material.mix_materials` ile aynı model; sonuç nüklid satırlarıdır. Oranların toplamı %100 olmalıdır. |

Atom kütleleri ve doğal izotop bollukları `openmc.data`'dan okunur (AME2020, IUPAC 2013).
Asistanla kurulan UO₂ (3.2 %, 10.40 g/cm³, 900 K) hazır kütüphanedeki UO₂ ile **aynı bileşimdir**;
aynı tohumla k da aynıdır (test: `testler/test_k6_tarif.py`). Alan sınırları yazım hatasını
yakalayan **girdi sınırıdır**, fiziksel bir eşik değildir. Hesaplar bir tasarım yardımıdır,
sertifika değildir: malzeme verisini kendi kaynağınızla doğrulayın.

<a id="kutuphanem"></a>
### Kütüphanem ve PNNL-15870

**Kütüphanem** yalnız bu bilgisayarda tutulur: `~/.local/share/openmc_arayuz/malzemeler.json`
(`XDG_DATA_HOME` tanımlıysa onun altında). Ağ erişimi yoktur. Pencerede **Ara…**, **Projeye ekle**,
**Düzenle…** ve **Sil** vardır; seçili kaydın bileşimi ve türetilmiş değerleri sağda görünür.

- Dosya **atomik** yazılır (geçici dosya + yeniden adlandırma): yazma yarıda kesilirse eski dosya
  sağlam kalır; son **sağlam** sürüm `malzemeler.json.onceki` olarak saklanır (bozuk bir dosya
  bu yedeğin üzerine yazılmaz). İki pencere aynı anda kaydederken yan kilit dosyası
  (`malzemeler.json.lock`) kayıt kaybını önler. Dizin yalnız size açıktır (0700); dosya en çok
  20 MB ve 10 000 kayıt olabilir.
- Dosya bozuksa (yarım JSON, şemaya uymayan kayıt) liste kilitlenir ve neden yazılır; dosya
  **silinmez**. **Bozuk dosyanın kopyasını al ve yeni kütüphane başlat** önce zaman damgalı bir kopya
  (`malzemeler.json.bozuk-…`) alır.
- Dosyanın bir `surum` alanı vardır; daha yeni bir sürümle yazılmış dosya okunmaz ve üzerine
  yazılmaz.

**PNNL-15870** (Compendium of Material Composition Data for Radiation Transport Modeling, 372/411
malzeme) açık bir lisansla yayımlanmadığı için programla **dağıtılmaz**. Derlemenin CSV dosyasını
(Rev. 1 biçimi; ör. PyNE'nin `materials_compendium.csv` dosyası) kendiniz indirin ve **Dosya seç…**
ile gösterin; dosya yalnızca okunur, son yol hatırlanır. **Ad ya da formül ara…** ile süzün;
**Projeye ekle** ya da **Kütüphaneme kaydet**. Okunamayan kayıtlar (sayı olmayan ya da negatif
ağırlık, 0–30 g/cm³ dışında yoğunluk, ağırlık toplamı 1'den 0.001'den fazla sapan — Rev. 1'de
SS-440 — ya da yinelenen numara) atlanır ve sayısı yazılır (ayrıntı günlükte).

### OpenMC XML'den içe aktarma

**Dosya → Malzemeleri içe aktar (OpenMC XML)…** bir `materials.xml` ya da `model.xml`
dosyasındaki malzemeleri bileşim, yoğunluk, sıcaklık ve S(α,β) ile ekler. Ad çakışırsa
`_2`, `_3` eki alır. İşlem tek adımda geri alınır (Ctrl+Z). **Yalnız malzemeler aktarılır**:
OpenMC geometrisi ham CSG'dir ve bu arayüzün malzeme → parça → demet → kor katmanlarına
güvenle çevrilemez; yanlış bir tahmin sessizce yanlış model üretirdi. Geometriyi arayüzde
kurun. Python betikleri içe aktarılamaz.

### Kullanılmayan malzeme ve sık bulgular

- "tanımlı ama modelde kullanılmayan malzeme: X" bir **bilgidir**; malzeme geometriye
  girmez, sonucu etkilemez. Bilinen sınır: yalnız kor haritası ya da katman anahtarında
  geçen malzemeler bu bilgiyi yanlışlıkla alabilir (`docs/ORNEKLER.md` "Çekirdekte gereken
  değişiklikler").
- "bileşim boş" ve "yoğunluk verilmemiş" **hatadır**; model kurulamaz.
- Su, grafit ya da berilyum S(α,β)'sız kalırsa **uyarı** verilir. Hızlı spektrumlu
  sistemlerde (sodyum, LBE) S(α,β) gerekmez.
- Bulgu metinlerinin tam listesi ve çözümleri:
  [Sorun giderme](09-sorun-giderme.md#bulgu-turleri).

Analiz sekmesindeki sıcaklık, yoğunluk ve bor taramaları buradaki değerleri koşu sırasında
değiştirir; kayıtlı model değişmez ([4.8](04h-analiz.md#analiz)). Tükenmede yanan malzemeler
yakıt rolündeki malzemelerdir ([4.9](04i-tukenme.md#tukenme)).
