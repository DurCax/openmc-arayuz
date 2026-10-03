<a id="uygunluk-denetimi"></a>
# 7. Uygunluk denetimi ve V&V

Model kontrolü (doğrulama paneli) koşu **öncesinde** modelin kurulabilir ve tutarlı olup olmadığına
bakar. **Uygunluk denetimi** ise koşu **sonrasında** çalışır: koşunun Monte Carlo iyi uygulamasına
ve standartların isteyeceği kanıta göre ne durumda olduğunu söyler. Aynı denetim üç yerde görünür:

- **Çalıştır** sayfasındaki **Uygunluk** kartı (koşu bitince ya da kayıtlı bir koşu yüklenince),
- raporun **kontrol listesi** eki (Dosya → Rapor oluştur…, `openmc-arayuz-kosu rapor`),
- komut satırı: `openmc-arayuz-kosu uygunluk <koşu_dizini>` (bkz. [terminal](08-terminal.md#terminal)).

Kuralların tek tek açıklaması, neden ve çözümleriyle birlikte
[sorun giderme](09-sorun-giderme.md#uygunluk-kurallari) bölümündedir; kaynak tablosu
`docs/STANDARTLAR.md` §3'tedir ([STANDARTLAR.md](../../STANDARTLAR.md)).

## 7.1 Uygunluk kartını okumak

Kartın üstünde **Profiller:** satırı vardır (A · Monte Carlo iyi uygulaması, B · Kritiklik
güvenliği, C · Reaktör kor tasarımı, D · Raporlama). Altında bir rozet ve bir özet satırı
("Profiller A, D · 5 kontrolü geçti · 1 kontrolü geçmedi · 0 uygulanamadı · 2 not"), onun altında
bulgu listesi durur. Sorunlar her zaman önce gelir (hata > uyarı > bilgi, sonra notlar,
değerlendirilemeyenler ve geçenler).

Her satır `K1 · kontrolü geçmedi — <bulgu>` biçimindedir; geçmeyen satırın altında
`Öneri: …` yazar. Satırın ipucunda kuralın **kaynağı** (atıf), **etiketi** ve **profili** görünür.
Bir satırı seçip **Bulguya git**'e basmak (ya da çift tıklamak) düzeltmenin yapılacağı sayfayı açar:
K1 ve K2 → Hesap ayarları (pasif çevrim, parçacık), K3 → Geometri (kayıp parçacık geometri
hatasıdır), K4-sicaklik → Malzemeler.

**Durumlar**

| Panelde | Durum | Anlamı |
|---|---|---|
| kontrolü geçti | karşılandı | Kural değerlendirildi ve koşul sağlandı. Geçen kurallar da listede durur; rapor eki böylece tam bir kontrol listesi olur. |
| kontrolü geçmedi | karşılanmadı | Koşul sağlanmadı. Seviyesi **hata**, **uyarı** ya da **bilgi** olabilir. |
| uygulanamadı | uygulanamadı | Kural değerlendirilemedi: gereken girdi yok (statepoint okunamadı, V&V kümesi yok, kullanıcı sınırı girilmedi…). Bu bir "geçti" değildir. |
| not | bilgi | Değerlendirme değil, bilgi notu (ör. pozitif MTC tek başına hata sayılmaz, not düşülür). |

**Rozet** en ağır durumu söyler: "N hata", "N uyarı", "N not"; hiçbir kural değerlendirilemediyse
"Değerlendirilemedi: N kural"; bazı kurallar geçip bazıları değerlendirilemediyse "N kontrol geçti ·
N kural değerlendirilemedi". Yeşil **"Sorun yok"** yalnız en az bir kural geçtiğinde ve
değerlendirilemeyen kural kalmadığında yazılır — statepoint yokken yeşil rozet görmezsiniz.

**Etiketler** (kaynağın türü — `docs/STANDARTLAR.md` §6 madde 16–17)

| Etiket | Anlamı | Örnek |
|---|---|---|
| iyi uygulama (standart maddesi değil) | Yayımlanmış iyi uygulama; bir standardın maddesi gibi gösterilmez | K1–K3 (kaynak yakınsaması, istatistik yeterliliği, kayıp parçacık), K14 |
| standart / kılavuz | Açık bir standart ya da kılavuz maddesine dayanır | K4, K5, K6–K13, K7, K16 |
| proje ölçütü (standarttan gelmez) | Projenin kendi ölçütü | katsayı işaretinin anlamlılığı \|eğim\| > 2σ; V&V kabul ölçütü |
| kullanıcı / tesis sınırı | Eşik kullanıcıdan ya da tesisten gelir; **varsayılan yoktur** | K7-SDM (kapatma marjı), K7-F (F_ΔH / F_q) |

Kartın altında iki metin daima durur: B profili seçili ve V&V özeti yoksa
**"USL hesaplanamadı: doğrulama (V&V) kümesi yok. Bu koşunun k değeri bir üst alt-kritiklik
sınırıyla karşılaştırılmadı; bu sonuç kritiklik güvenliği kanıtı değildir."** notu, ve
[dürüst çerçeve](#ne-kanitlar) metni.

Denetim yapılamazsa (ör. koşu dizinindeki `uygunluk_girdisi.json` bozuk) liste tek bir kırmızı
satır ve "Denetlenemedi" rozeti gösterir; ayrıntı günlük dosyasındadır. Bir kuralın kendisi
çalışırken hata verirse denetim durmaz: o kural "Kural değerlendirilemedi" diye **hata** bulgusu
olarak listelenir (sessiz geçilmez).

<a id="profiller"></a>
## 7.2 Profiller, eşikler ve kullanıcı girdileri

Bir **profil**, birlikte anlamlı olan kuralların ve onların kaynaklı eşiklerinin kümesidir
(`cekirdek/uygunluk_denetimi/profiller.py`):

| Profil | Ne için | Kurallar | Varsayılan eşikler (kaynağıyla) |
|---|---|---|---|
| **A** Monte Carlo iyi uygulaması | Her koşu | K1, K2, K3 | çevrim başına en az 1000 parçacık (Brown 2009 §III.C), uzun üretim koşusu için 5000 (§V); çevrim ilintisi için z = 2 (Bartlett yaklaşımı); kayıp parçacık 0; σ hedefi ve aktif çevrim alt sınırı **yok** (standart sayı vermez → kullanıcı) |
| **B** Kritiklik güvenliği | İsteğe bağlı | K6, K6-AOA, K8–K14 | kabul k + 2σ < USL (NUREG/CR-6698 eş. 36); ΔSM = 0.05 (kaynağı **DOĞRULANMADI**), ΔSM alt sınırı 0.02 (§2.4.5); en az 10 vaka (§2.2); parametrik olmayan güven > %40 (Tablo 2.2); dış değerleme ≤ %10 (§1.2, §5) |
| **C** Reaktör kor tasarımı | Güç ya da araştırma reaktörü koru | K7, K7-SDM, K7-F, K16 | F_ΔH, F_q ve kapatma marjı sınırları **yok** (NUREG-0800 §4.3 bunları tesise özel bırakır); işaret anlamlılığı 2σ (proje ölçütü); reaktör türü "guc" (araştırma reaktöründe SSR-3 kaynağı) |
| **D** Raporlama | Her rapor | K4, K5 | belirsizlik en çok 2 anlamlı rakam (GUM §7.2.6) |

**Profil seçimi.** Kartın üstündeki kutular projenin seçimini değiştirir ve modelde
`calistirma.uygunluk_profilleri` alanına yazılır. Bu alan fiziğe girmez: seçimi değiştirmek koşu
sonucunu eskitmez. Alan yoksa varsayılan **A + D**'dir ve dosyaya yazılmaz. Komut satırında
`--profil A,B,C,D` verilirse o kullanılır; verilmezse koşu dizinindeki `spec.json`'un seçimi, o da
yoksa A,D.

**Kaynaksız eşik konmaz.** Her eşik değeriyle birlikte atfını taşır. Standart sayısal bir değer
vermiyorsa varsayılan boştur ve ilgili kural "karşılaştırılamadı" / "uygulanamadı" der; araç bir
sınır uydurmaz. Eşikleri değiştirmek için profil dosyası biçimi şudur:

```json
{"C": {"F_dH_siniri": {"deger": 1.55, "kaynak": "Tesis TS 3.2.1"}},
 "A": {"parcacik_uretim": 10000}}
```

Kaynak yazılmazsa eşik "kullanıcı girdisi — kaynak belirtilmedi" etiketini alır; bilinmeyen bir
eşik adı yazım hatası olarak reddedilir. Bu sürümde profil dosyası yalnız Python API'siyle
okunur (`profiller.dosyadan_uyarla(yol)`); arayüzde ve komut satırında henüz bir seçeneği yoktur.

**Koşuya özgü girdiler: `uygunluk_girdisi.json`.** Koşu dizinine (statepoint'in yanına) konan bu
isteğe bağlı dosya, koşunun kendisinden çıkarılamayan bilgileri verir (aşağıdaki değerler biçimi
göstermek içindir; Doppler eğimi README'deki `pwr_17x17` ölçümüdür, kapatma marjı uydurma bir
örnektir):

```json
{"kor": {"katsayilar": {"yakit_sicaklik": {"egim": -1.98, "egim_sapma": 0.17, "birim": "pcm/K"}},
         "kapatma_marji": {"deger_pcm": 1800, "sapma_pcm": 90, "en_degerli_cubuk_sikisik": true},
         "dogrulama": ["ICSBEP LEU-COMP-THERM-008"]},
 "uygulama": {"zenginlik": 4.5, "tayf": "termal"}}
```

- `kor`: Profil C'nin girdileri — reaktivite katsayıları (Analiz sekmesindeki tarama sonucu;
  `guc`, `yakit_sicaklik`, `sogutucu_sicaklik`, `void_orani`), kapatma marjı (Δρ × 10⁵, en değerli
  çubuk sıkışık varsayımıyla), F_ΔH / F_q (verilmezse statepoint'ten okunur) ve kor yönteminin
  doğrulandığı kriterler (K16). Analiz sekmesi bu dosyayı kendisi yazmaz; değerleri siz girersiniz.
- `uygulama`: Profil B'nin uygulanabilirlik alanı (AOA) parametreleri (`bolunebilir`, `zenginlik`,
  `h_x`, `fiziksel_bicim`, `ealf`, `tayf`). Verilmezse çıkarılabilenler modelden ve koşudan alınır.

<a id="ne-kanitlar"></a>
## 7.3 Ne kanıtlar, ne kanıtlamaz

Kartta ve rapor ekinde **aynen** yazılan dürüst çerçeve:

> Bu program hiçbir standarda sertifika vermez ve bir analizi "standarda uygun" diye onaylayamaz.
> Yaptığı iş, bir koşu ya da model için standartların ve iyi uygulamanın isteyeceği kanıtı üretmek
> ve eksikleri görünür kılmaktır. Tesis lisanslaması ya da güvenlik analizinde kullanım için
> kullanıcı kuruluşun kendi kalite güvence programı ve bağımsız gözden geçirmesi ayrıca gerekir.
> Kaynağı gösterilemeyen eşik konmaz; eşikler profilde ayarlanabilir.

**Denetimin ürettiği kanıt**
- Kaynak yakınsaması göstergesi (K1), istatistik yeterliliği ve çevrim ilintisi (K2), kayıp
  parçacık sayısı (K3).
- Veri izlenebilirliği (K4): kütüphane adı ve sürümü, sıcaklıklar, S(α,β), veri karmaları, OpenMC
  sürümü, işletim sistemi ve donanım özeti raporda. Her koşu dizinindeki `kapsul.json` aynı kanıtı
  yeniden üretilebilir biçimde saklar.
- Belirsizlik ve birim bildirimi (K5): k ile birlikte "1σ, standart belirsizlik" etiketi, en çok iki
  anlamlı rakam, tanımı yazılı pcm.
- V&V özeti verilirse k + 2σ < USL karşılaştırması ve doğrulama kümesinin istatistik koşulları
  (Profil B); kor tasarımında katsayı işareti tutarlılığı ve kullanıcı sınırıyla karşılaştırma
  (Profil C).
- Kriter paketinin C/E tablosu ([V&V](#vv)).

**Denetimin kanıtlaMADIKLARI**
- **Sertifika değildir.** Hiçbir bulgu "standarda uygun" anlamına gelmez; rapor eki bir kontrol
  listesidir, onay değildir.
- **Kuruluşun kalite güvencesinin yerine geçmez.** ASME NQA-1 (Subpart 2.7 dahil) bir **kuruluşun**
  kalite güvence programıdır; bir araç "NQA-1 uyumlu" olamaz ve bu araç NQA-1 programı altında
  geliştirilmemektedir. Araç ANSI/ANS-10.4 anlamında güvenlikle ilgili **olmayan** (araştırma,
  eğitim) bilimsel yazılımdır; IEEE 1012 bütünlük düzeyi bakımından geliştirici onu en düşük düzeyde
  konumlar (bkz. `docs/YAZILIM_KALITE.md` — [YAZILIM_KALITE.md](../../YAZILIM_KALITE.md)).
- **Modelin doğru olduğunu kanıtlamaz.** Geometri, malzeme ve çalışma koşulunun gerçek sistemi temsil
  etmesi kullanıcının sorumluluğudur. NUREG/CR-6698'in vurguladığı gibi doğrulama kod ve kütüphaneye
  olduğu kadar donanıma ve modeli kuran kişinin yetkinliğine de bağlıdır.
- **"Geçti" mutlak değildir.** K1'in geçmesi kaynağın her yönde yakınsadığını göstermez (entropi
  global bir skalerdir; bkz. [kaynak yakınsaması](06-sonuclar.md#kaynak-yakinsamasi)); K2'nin
  geçmesi yerel tally σ'larını gerçek yapmaz.
- **K7 bir tasarım yargısı değildir.** Yalnız katsayı işaretinin beklentiyle "tutarlı / çelişiyor"
  olduğunu söyler; GDC 11'in karşılandığını söylemez. Pozitif MTC tek başına hata sayılmaz (not
  düşülür, geçici rejim analizine işaret edilir).
- **Kritiklik güvenliği kanıtı değildir** — V&V özeti olmadan B profili "USL hesaplanamadı" der.
  V&V özeti olsa bile USL yalnız kümenin uygulanabilirlik alanında geçerlidir: bu sürümün kümesi
  yalnız **LWR / LEU oksit kafes** uygulamalarına USL verir (n = 24, iki deney serisi; öğretim
  amaçlı bir sayıdır, lisanslama değildir) ([V&V](#vv)).
- **Bağımsız V&V yoktur.** Kod, testler ve incelemeler aynı geliştirme sürecinden çıkar
  (`docs/YAZILIM_KALITE.md` §4).

<a id="vv"></a>
## 7.4 V&V: kriter kümesi, C/E, yanlılık, USL ve AOA

Aracın kriter (benchmark) paketi ve ölçülen sonuçlar `docs/VV.md`'dedir
([VV.md](../../VV.md)); oradaki sayılar örnek dosyalarının `referans.olcum` alanlarıyla birebir
aynıdır ve testle denetlenir. Ortam: OpenMC 0.16.0, ENDF/B-VIII.0 (HDF5, 294 K). Adım adım ders:
[benchmark ve C/E](05-dersler.md#ders-benchmark).

**Küme.** 49 deney kriteri (ICSBEP; v3 Y11 ile; 3 + 22 + 24): ilk üçü `ornekler/godiva_kriter.json`,
`ornekler/kriter_jezebel.json`, `ornekler/kriter_flattop25.json`;
22'si `ornekler/vv/` altında, mit-crpg/benchmarks (MIT lisansı) OpenMC modellerinden eş merkezli küre
kabukları olarak aktarılmıştır; 24'ü LEU oksit kafesidir (v3 Y11): LEU-COMP-THERM-006 (TCA, 18 durum,
kamuya açık birincil rapor JAERI 1254'ten kurulan modeller) ve LEU-COMP-THERM-008 (6 durum,
mit-crpg). LCT-008 durum 1 h_x ile yeniden üretildi; V&V kümesinde v2 dosyasının (`ornekler/kriter_lct008.json`) yerini alır; o dosya **kümeden çıkarıldı** (örnek olarak durur, 49'a sayılmaz).
Ayrıca iki hesap-hesap kriteri (VVER-1000 LEU demeti, SFR MET-1000)
vardır. **Deney ve hesap-hesap kriterleri ayrı tutulur:** deney kriterinde E ölçülmüş bir kritik
düzenektir; hesap-hesap kriterinde E başka kodların hesap ortalamasıdır, "doğru" değer değildir.

**C/E tablosunu okumak**

| Sütun | Anlamı |
|---|---|
| E ± σe | kriterin deney değeri ve belirsizliği |
| C ± σc | bu aracın hesap değeri (1σ) |
| C − E [pcm] | **Δk × 10⁵** (k farkı; reaktivite farkı Δρ değildir) |
| fark/σ | \|C − E\| / √(σc² + σe²) |
| C/E | hesap / deney |

**Kabul ölçütü** \|C − E\| ≤ 3·√(σc² + σe²) ve σc ≤ 30 pcm'dir. Bu **projenin kendi ölçütüdür**,
bir standarttan gelmez. Şu an ölçütü aşan kriter yoktur; en büyük sapmalar PU-MET-FAST-008 (2.62σ)
ve U233-SOL-INTER-001 (2.19σ, −1822 pcm; bütün kümenin normallik testini bozan uç değer). İkisi v3'te
model varyantlarıyla incelendi: aktarım, 1B basitleştirme, S(α,β) ve sıcaklık sapmayı açıklamaz;
olası neden nükleer veridir (U-233 için yayımlanmış epitermal eğilimle tutarlı) — başka kütüphaneyle
**doğrulanmadı** (`docs/VV.md`, "Sapma incelemesi").

**Yanlılık ve USL: NUREG/CR-6698 akışı.** (Kod `cekirdek/vv/`, formüller `docs/STANDARTLAR.md` §4.)
1. Normalleştirme k_norm = k_calc / k_exp ve birleşik belirsizlik σ = √(σc² + σe²) (eş. 9, 3).
2. Ağırlıklı ortalama k̄, varyans s², ortalama belirsizlik σ̄², birleştirilmiş S_p (eş. 4–7).
3. Yanlılık = k̄ − 1; **pozitif yanlılık kredilendirilmez** (USL'de 0 alınır, eş. 8; K8).
4. Normallik: Shapiro–Wilk; p ≤ 0.05 ise parametrik olmayan yöntem zorunlu (eş. 31–34).
5. Eğilim: zenginlik, H/X ve log₁₀(EALF)'a karşı ağırlıklı doğrusal uydurma; eğim anlamlılığı
   t-testiyle (bu test 6698'de yoktur, SCALE/VADER uygulamasıdır).
6. Anlamlı eğilim varsa tolerans bandı (eş. 23–30), yoksa tek taraflı tolerans sınırı (eş. 20–22).
7. USL = K_L − ΔSM − ΔAOA (eş. 22/35).
8. Kabul: **k + 2σ < USL** (eş. 36; katı eşitsizlik; K6).

**Sahte güven yok.** Kümede 10'dan az vaka varsa (6698 §2.2) istatistikler raporlanır ama **USL
verilmez** ("hesaplanamadı"); parametrik olmayan yöntemde güven β ≤ %40 ise USL yine verilmez
(Tablo 2.2: ek veri gerekli). ΔSM varsayılanı 0.05'tir (kaynağı **DOĞRULANMADI**); **0.02 mutlak alt
sınırdır** ve profilde daha küçük bir ΔSM K11 hatası verir. ΔSM'nin seçimi ve gerekçesi kullanıcı
kuruluşa aittir.

**Ölçülen sonuçlar (02.10.2026, v3 Y11 LEU kafes vakalarıyla; ΔSM = 0.05, ΔAOA = 0; ayrıntı `docs/VV.md`)**

| Alt küme (AOA) | n | yanlılık k̄ − 1 | Yöntem | USL |
|---|---|---|---|---|
| Bütün küme | 49 | −0.00018 | parametrik olmayan (β = %91.9) | 0.9235 (yalnız bilgi: farklı AOA'ları karıştırır) |
| Hızlı tayf (EALF ≥ 100 keV) | 13 | −0.00050 | tolerans sınırı | 0.9444 (yalnız bilgi) |
| Termal tayf (EALF < 1 eV) | 33 | +0.00010 | parametrik olmayan (β = %81.6) | 0.9297 (yalnız bilgi) |
| U-235 (bütün biçimler) | 34 | +0.00021 | parametrik olmayan (β = %82.5) | 0.9297 (yalnız gösterim) |
| Çözelti (termal + ara) | 10 | −0.00203 | parametrik olmayan (β = %40.1) | 0.8735 |
| **U-235, oksit, termal, LEU (LCT-006 + LCT-008)** | **24** | +0.00029 | parametrik olmayan (β = %70.8) | **0.9275** |
| Ara tayf | 3 | −0.00005 | tolerans sınırı | **hesaplanamadı** |
| Pu (bütün biçimler) | 9 | −0.00086 | parametrik olmayan (β = %37.0) | **hesaplanamadı** |
| U-233 | 5 | −0.00032 | parametrik olmayan (β = %22.6) | **hesaplanamadı** |

**Araç hangi alt kümeyi kullanır?** Yukarıdaki tablo betimseldir. K6, bir uygulamanın USL'sini
**yalnız** uygulamayla aynı bölünebilir türü, aynı fiziksel biçimi ve aynı nötron tayfını paylaşan
vakalardan hesaplar; U-235'te zenginlik sınıfı da aynı olmalıdır (ICSBEP: LEU ≤ %10, IEU %10–60,
HEU ≥ %60; NUREG/CR-6698 §2.5, Tablo 2.3). Uygun alt kümede 10'dan az vaka varsa USL verilmez.
Depodaki kümede bu ölçütle en büyük alt küme **U-235, oksit, termal, LEU (n = 24)**'dir; LWR/LEU
kafes uygulamaları (ör. pwr_17x17) **USL = 0.9275** alır (parametrik olmayan; küme normal değil
çünkü iki seri ~130 pcm farklı — TCA modelinde U-234 yok, `docs/VV.md`). 24 vaka yalnız iki deney
serisindendir (K14 notu); 6698'in bağımsızlık varsayımı tam sağlanmaz. Diğer AOA'larda en büyük alt
küme 5 vakadır (Pu, metal, hızlı) → USL yok. Tablodaki hızlı tayf, termal tayf ve U-235
satırları bölünebilir tür ya da biçim bakımından karışıktır; yalnız bilgi içindir.

**Hangi uygulamalar için USL YOK?**
- Tek bölünebilir türlü AOA'lar (Pu, U-233), ara tayf ve kümede 10'dan az eşi olan her AOA.
- MOX, oksit tozları, ağır su, beton/çelik/kurşun yansıtıcılar, zehirli (B, Gd, Cd) sistemler,
  yüksek Pu-240 (> %20) ve AOA aralığı dışındaki zenginlik/H/X/EALF değerleri — kümede temsil
  edilmiyor; K6-AOA ve K12 uyarır. Heterojen kafeste H/X çıkarılamazsa K12 bunu da uyarır.

**Sınırlamalar.** Ölçüt ve formüller NUREG/CR-6698'dendir (bir NRC **kılavuzu**, bağlayıcı değil);
deneyler arası korelasyon ele alınmaz (aynı seriden iki vaka için K14 "bağımsız değil" notu düşer);
vakalar ICSBEP'in basitleştirilmiş (çoğu 1B küresel) modelleridir; E ± σ güncel ICSBEP baskısıyla
karşılaştırılmadı; yalnız tek kod + tek kütüphane doğrulandı (başka kütüphane ya da sürümde küme
yeniden koşulmalıdır).

**Araçta kullanmak.** B profili seçildiğinde Uygunluk kartı, rapor eki ve `uygunluk` komutu V&V
özetini kendiliğinden kullanır (`kume.uygulama_ozeti`): uygulamanın AOA'sı modelden çıkarılır,
uygun alt küme seçilir; USL varsa K6 metninde alt küme, n ve yöntem yazar, yoksa "bu uygulama için
USL yok" ve nedeni görünür. Tayf için koşuda EALF tally'si (`vv_ealf`) gerekir; yoksa kart onu
eklemeyi önerir. Python API'siyle:

```bash
python -c "from cekirdek.vv import kume; import json; print(kume.uygulama_ozeti(json.load(open('ornekler/pwr_17x17.json')), uygulama={'tayf': 'termal'})[0].usl_neden)"
```

Uygulamanın AOA parametreleri (`kume.uygulama`) modelden ve koşudaki EALF tally'sinden çıkarılır;
çıkarılamayan parametre sözlükte yer almaz.
