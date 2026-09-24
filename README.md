# OpenMC Reaktör Kuru Arayüzü

Malzemeden kora kadar tüm model parametrelerinin tek bir arayüzden kurulduğu,
geometrinin çalıştırmadan önce görüldüğü ve hesabın aynı arayüzden başlatılıp
sonuçlarının okunduğu bir PySide6 masaüstü uygulaması.

## Hızlı başlangıç

```bash
conda activate openmc-env
cd ~/openmc_arayuz
./calistir.sh ornekler/pwr_17x17.json
```

GUI istemiyorsan çekirdek katman terminalden de çalışır:

```bash
python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json
python3 -m cekirdek.kosucu ornekler/pwr_17x17.json --dizin /tmp/deneme -s 24
python3 -m cekirdek.kosucu ornekler/mtr_plaka.json --sadece-dogrula
python3 -m cekirdek.kosucu ornekler/pwr_17x17.json --betik model.py
```

## Nasıl çalışıyor

Arayüz doğrudan OpenMC nesnelerini değil, doğrulanabilir bir **JSON model
tanımını (spec)** düzenler. Spec tek gerçek kaynaktır:

```
spec (JSON) ──► kurucu.py ──► openmc.Model ──► XML ──► openmc çalıştır
     │
     └────────► kod_uret.py ──► model.py (tek başına çalışan, elle düzenlenebilir)
```

**Arayüz çıkmaz sokak değildir.** `Dosya > Python betiği olarak dışa aktar` ile
modeli okunabilir bir OpenMC betiğine çevirip elle devam edebilirsin. Üretilen
betik `openmc_arayuz`'a bağımlı değildir. (Tek yönlüdür: betik spec'e geri
çevrilemez.)

## Dizin yapısı

```
openmc_arayuz/
├── calistir.sh              ortamı doğrulayıp GUI'yi açar
├── cekirdek/                GUI'siz katman — terminalden de çalışır
│   ├── sema.py              spec şeması, varsayılanlar, oku/yaz
│   ├── malzeme_kutup.py     21 hazır malzeme (doğrulanmış bileşimler)
│   ├── altigen.py           HexLattice halka düzeni ve konum hesabı
│   ├── veri_bilgi.py        kütüphanenin sunduğu sıcaklık aralıkları
│   ├── kurucu.py            spec → openmc.Model
│   ├── onbellek.py          model önbelleği (21.9 ms → 0.07 ms)
│   ├── dogrula.py           koşu öncesi kontroller
│   ├── kod_uret.py          spec → tek başına çalışan Python betiği
│   ├── ice_aktar.py         materials.xml → spec malzemeleri
│   ├── guc.py               çubuk bazlı güç dağılımı, F_ΔH, F_q
│   ├── tarama.py            parametre taraması → reaktivite katsayıları
│   ├── kritik_arama.py      hedef k-eff'i veren parametre değeri
│   └── kosucu.py            çalıştırma + statepoint okuma + terminal girişi
├── arayuz/                  PySide6 katmanı
│   ├── tema.py              açık/koyu tema paletleri (matplotlib dahil)
│   ├── ana_pencere.py       sekmeler, proje aç/kaydet, doğrulama paneli
│   ├── onizleme.py          canlı geometri kesiti (Model.plot sarmalayıcı)
│   ├── hex_izgara.py        altıgen harita editörü (QPainter)
│   ├── guc_harita.py        güç dağılımı ısı haritası
│   └── sekme_*.py           malzeme / çubuk / kafes / kor / ayar / çalıştır / analiz
├── ornekler/                pwr_pinhucre, pwr_17x17, mtr_plaka, sfr_altigen
└── testler/test_regresyon.py
```

## Çalışma akışı

Sekmeler numaralandırılmıştır, sırayla ilerlenir:

1. **Malzemeler** — kütüphaneden ekle veya elle tanımla. Kütüphanede UO2, UN,
   U-10Mo, MOX, U3Si2-Al, Zircaloy-4, SS316, MA956, FeCrAl, SiC, Al-6061, su
   (sıcaklığa bağlı yoğunluk + boron), D2O, LBE, Na, He, grafit, Be, B4C,
   Gd2O3, Ag-In-Cd var. S(α,β) uygun olanlara otomatik eklenir.
2. **Çubuk / Plaka** — eşmerkezli silindirik çubuk veya MTR tipi plaka elemanı.
3. **Kafesler** — kare kafeste ızgara, altıgen kafeste gerçek altıgen yerleşim
   üzerinde boyama (sol tık boyar, sağ tık fırçayı değiştirir, tekerlek
   yakınlaştırır). Kafes tipi değiştirilince harita otomatik dönüştürülür.
4. **Kor** — kor türü, yükseklik, yansıtıcı, sınır koşulları.
5. **Ayarlar & Tally** — çevrim/parçacık, kaynak, tally tanımları.
6. **Çalıştır** — canlı log, k-eff yakınsama grafiği, sonuç tabloları.
7. **Analiz** — parametre taraması (reaktivite katsayıları) ve kritik arama.

Üstteki **rehber şeridi** modelin durumuna bakıp sonraki adımı söyler; "Oraya git"
ile doğrudan ilgili sekmeye gider. **F1** terim sözlüğünü açar.

Sağ tarafta her değişiklikten sonra geometri kesiti yenilenir (~0.2 s),
sağ altta doğrulama paneli canlı çalışır.

## ⚠ ÖNCE ÇİZ, SONRA ÇALIŞTIR

Geometri önizlemesi başarıyla üretilmeden ve doğrulama hataları giderilmeden
**ÇALIŞTIR düğmesi etkinleşmez.** Bu, elle yazılan betiklerdeki
*"plotlar doğruysa `model.run()` satırının yorumunu kaldır"* alışkanlığının
arayüze gömülmüş halidir — yanlış geometriyle saatlerce koşmayı önler.

## Doğrulama neyi yakalar

Monte Carlo koşusu pahalıdır; hataların çoğu saatler sonra ya da hiç fark
edilmez. `dogrula.py` koşu **öncesinde** şunları yakalar:

- `OPENMC_CROSS_SECTIONS` ayarlı değil / dosya yok
- Modelin istediği nüklid veri kütüphanesinde yok
- Su/grafit/berilyum var ama S(α,β) eklenmemiş *(termal spektrumda k'yı yüzde
  mertebesinde kaydırır)*
- U zenginliği %5 üzeri — OpenMC'nin zenginlik kısayolu U234/U235 oranını sabit
  varsayar
- Yoğunluk verilmemiş, çubuk yarıçapları ters sırada veya çakışıyor
- Çubuk dış çapı hücre adımından büyük
- Kafes haritasında tanımsız harf, satır/sütun sayısı uyuşmuyor
- Geçersiz sınır koşulu; tek hücrede `vacuum` (sızıntı riski)
- Pasif çevrim sayısı toplam çevrimden fazla ya da çok az

Seviyeler: **hata** çalıştırmayı engeller, **uyarı** kullanıcıya bırakılır,
**bilgi** sadece dikkat çeker.

## Testler

```bash
python3 testler/test_regresyon.py            # tümü (~2 dk)
python3 testler/test_regresyon.py --hizli    # Monte Carlo hariç (~10 s)
```

125 test var. Üçü bu katmanın doğruluğunun asıl kanıtıdır:

- **Regresyon çıpası** — `ornekler/pwr_pinhucre.json` referans değeri
  **k∞ = 1.3570 ± 0.0020** vermeli. 2σ dışına çıkarsa `kurucu.py`'de hata var.
- **Betik eşdeğerliği** — `kurucu.py` ile üretilen betik aynı tohumla **birebir
  aynı** k-eff vermeli (kare ve altıgen için ayrı ayrı). `kurucu.py` ya da
  `kod_uret.py` değiştirilirse mutlaka tekrar koşulmalı.
- **Altıgen düzen** — `altigen.py`'nin halka indeksleri OpenMC'nin kendi
  `HexLattice.show_indices()` çıktısıyla birebir uyuşmalı.
- **Godiva kriteri** — yayımlanmış k_eff'ten 2σ'dan fazla sapmamalı.
- **Güç toplamı korunumu** — çubuk güçlerinin toplamı filtresiz tally'ye eşit
  olmalı (ölçülen bağıl fark 9e-16). Haritalama hatası toplamı bozar; bu, yanlış
  bir haritanın sessizce doğru görünmesini önleyen en güçlü kontrol.

## Ölçülen referans sonuçlar

| Örnek | k-eff | Koşu (24 iş parçacığı) |
|---|---|---|
| `pwr_pinhucre` | 1.35698 ± 0.00197 | 7 s |
| `pwr_17x17` | 1.18325 ± 0.00075 | 44 s |
| `mtr_plaka` | 1.65368 ± 0.00083 | 42 s |
| `sfr_altigen` | 1.46634 ± 0.00070 | 53 s |
| `godiva_kriter` | 0.99900 ± 0.00045 | 6 s |
| `pwr_3b` (3B, güç dağılımı) | 1.17953 ± 0.00059 | 73 s |

## Güç dağılımı ve tepe faktörleri

Ayarlar sekmesinden açılır; sonuç **6. Çalıştır → Güç haritası** alt sekmesinde.
`DistribcellFilter` kafeste tekrarlanan yakıt hücresinin her örneğini ayrı sayar.

| | Tanım | Neyi sınırlar |
|---|---|---|
| **F_ΔH** | maks çubuk gücü / ortalama | Sıcak kanalda soğutucu sıcaklık artışı (DNB marjı) |
| **F_q** | maks yerel güç yoğunluğu / ortalama | Yakıt merkez sıcaklığı, lineer güç (~400–500 W/cm) |

Ölçülen (`pwr_3b`, 20k parçacık, 20 eksenel dilim):
**F_ΔH = 1.071**, **F_q = 1.885**, ortalama lineer güç **182 W/cm** (17.6 MW/demet).

> 🔴 **Belirsizlikler iyimserdir.** Özdeğer hesabında ardışık çevrimlerin fisyon
> kaynakları korelasyonludur; OpenMC'nin raporladığı tally belirsizliği bu
> korelasyonu görmez. **Bu modelde ölçüldü:** raporlanan σ bin başına 0.003–0.008,
> 3 bağımsız tohum arasındaki gerçek saçılma 0.07–0.17 — yani **~20 kat**.
> Gerçek belirsizlik için `guc.coklu_tohum()` ile birkaç tohumda koşun.

> ⚠ **F_ΔH bir MAKSİMUMDUR ve az istatistikte yukarı yanlıdır.** Ölçüldü: aynı
> modelde 3k parçacıkla 1.1455, 20k parçacıkla 1.0708. Çubuk başına istatistik
> sapma dağılımın saçılmasının %30'unu aşarsa araç bunu uyarır.

> ⚠ **F_q eksenel çözünürlüğe bağlıdır.** Kaba dilimler tepeyi ortalar ve F_q'yu
> küçük gösterir (saf kosinüs limiti π/2 = 1.571). En az 10–20 dilim kullanın.

**Mutlak güç** isteğe bağlıdır. `toplam_guc` **modelin kapsadığı bölgenin**
gücüdür — tüm korun değil. Örnek: 3400 MWth / 193 demet = 17.6 MW; tek demetlik
bir modelde `17.6e6` girilir. Doğru girdiyle ortalama lineer güç ~182 W/cm çıkar;
bu mertebede değilse girdi yanlıştır.

## Reaktivite katsayıları ve kritik arama (7. Analiz)

Tek bir k-eff sayısı bir tasarım hakkında az şey söyler. Analiz sekmesi bir
parametreyi tarayıp eğimden **reaktivite katsayısını** çıkarır:

| Tarama | Katsayı | Ölçülen (pwr_17x17) |
|---|---|---|
| Yakıt sıcaklığı 600→1200 K | Doppler | **−1.98 ± 0.17 pcm/K** |
| Soğutucu sıcaklığı 540→620 K, 0 ppm bor | Moderatör sıcaklık | **−35.2 ± 1.0 pcm/K** |
| Soğutucu sıcaklığı, 1300 ppm bor | Moderatör sıcaklık | **−2.6 ± 1.2 pcm/K** |
| Bor 0→8000 ppm | Bor değeri | **−7.0 pcm/ppm** |

> ⚠ **Sıcaklık ve yoğunluk birlikte değişir.** Soğutucu sıcaklığı artınca
> yoğunluğu da düşer. Yalnızca sıcaklığı değiştirirseniz etkinin en büyük
> parçasını kaçırırsınız. `sogutucu_sicaklik` taraması yoğunluğu korelasyonla
> günceller (su: doymuş sıvı tablosu; LBE: Sobolev; Na: Fink & Leibowitz).
> Korelasyonu bilinmeyen malzemede yoğunluk sabit tutulur ve **bu açıkça
> raporlanır**.

> 📘 Yukarıdaki iki MTC değeri arasındaki fark gerçek fiziktir: bor suda
> çözünmüştür, yoğunluk düşünce soğurucu da azalır ve iki etki birbirini
> götürür. PWR'lerde çevrim başı bor sınırının sebebi budur.

**Kritik arama** hedef k-eff'i veren değeri bulur (kritik bor, kritik yükseklik…).
Durma ölçütü istatistiğe bağlıdır: `|k − hedef| < 1σ` olunca durur, çünkü daha
sıkı bir ölçüt gürültü kovalamaktır. Kök aralıkta değilse **ekstrapolasyon
yapmaz**, aralığı genişletmenizi söyler.

Örnek: 17×17 demeti için kritik bor = **3430 ppm**, 7 koşuda yakınsadı.

## Kinetik parametreler

Ayarlar sekmesinden açılır (IFP yöntemi). Ölçülen:

| Model | β_eff | Λ |
|---|---|---|
| PWR 17×17 | 696 ± 48 pcm | 22.4 μs |
| Godiva | 681 ± 27 pcm | 5.62 ns |

β_eff sayesinde reaktivite **dolar** cinsinden de raporlanır (1 $ = β_eff).

## Bilimsel doğrulama — Godiva kriteri

`ornekler/godiva_kriter.json` — ICSBEP **HEU-MET-FAST-001**: çıplak HEU metal
küresi, yayımlanmış k_eff = 1.0000 ± 0.0010.

| | k_eff |
|---|---|
| Bu araç | **0.99957 ± 0.00054** |
| Kriter | 1.0000 ± 0.0010 |
| Fark | **0.38 σ** |

Bu, regresyon çıpasından **farklı** bir testtir: çıpa "kod kendiyle tutarlı" der,
bu "sonuç gerçekten doğru" der. Malzeme bileşimi, geometri, tesir kesiti
kütüphanesi ve taşınım zincirinin tamamı bağımsız bir ölçüme karşı sınanır.

## Kaynak yakınsaması (Shannon entropisi)

Özdeğer hesaplarında entropi mesh'i varsayılan olarak **açıktır**. Koşu bitince
kaynak dağılımının pasif çevrimler içinde yakınsayıp yakınsamadığı otomatik
değerlendirilir:

> `kaynak = [OK] Kaynak dagilimi yakinsamis gorunuyor (kayma 0.0003 <= 2 sigma = 0.0096)`

**Yöntem:** aktif çevrimlerdeki entropi saçılması (σ) gürültü ölçüsü alınır.
Önemli olan kaynağın pasif dönemin **sonunda** durmuş olmasıdır — başta hızla
yükselmesi normaldir (nokta kaynaktan başlanırsa entropi sıfırdan başlar). Bu
yüzden yalnızca pasif dönemin son yarısı incelenir, ikiye bölünüp karşılaştırılır.
Yakınsamamış kaynak k-eff'i **yanlı** tahmin ettirir ve bu başka türlü fark
edilmez.

## Görünüm

**Görünüm > Tema** menüsünden açık/koyu geçişi yapılır; seçim hatırlanır.
matplotlib grafikleri de aynı palete uyar, böylece grafikler arayüzden kopuk
görünmez.

Kısayollar: **F10** pencereyi büyüt/eski hâline döndür, **F11** tam ekran.

> ⚠ **Pencere boyutu tuzağı.** `QTabWidget`'in minimum yüksekliği *tüm
> sayfalarının en büyüğüdür*. Ayarlar sekmesi büyüdükçe (entropi, kinetik, güç
> dağılımı) pencerenin minimumu **1317 px**'e çıkmıştı; ekranda 1048 px olduğu
> için pencere tam ekran yapılamıyor ve alt kısmı hiç görünmüyordu. İki katmanlı
> çözüm: ayarlar sekmesi iki sütuna bölündü ve **her sekme bir `QScrollArea`
> içine alındı** — minimum 1317 → **308 px**. Yeni bir bölüm eklendiğinde bu
> bağ bir daha kurulmaz.

> ⚠ **`showMaximized()` bu makinedeki pencere yöneticisinde yok sayılıyor.**
> `show()`'dan hemen sonra `setWindowState()` de tutmuyor — pencerenin önce
> haritalanması gerekiyor. Büyütme bu yüzden olay döngüsü başladıktan
> ~120 ms sonra uygulanıyor.

## Performans notları (ölçülmüş)

| Ne | Önce | Sonra | Nasıl |
|---|---|---|---|
| Bir düzenlemenin anlık maliyeti | 19–34 ms | **0.01 ms** | Konu bazlı sekme geçersizleştirme |
| `openmc.Model` kurulumu (tekrar) | 21.9 ms | **0.07 ms** | İçerik özetine dayalı model önbelleği |
| Önizleme (görüntü değişikliği) | 292 ms | **66 ms** | İsteğe bağlı "hızlı mod" |

**Çözünürlük neredeyse bedava.** Ölçüm: tek seferlik çizimde 200 px → 632 ms,
1200 px → 387 ms. Maliyet ışın izlemede değil, `Model.plot()`'un her çağrıda
OpenMC kütüphanesini yeniden başlatıp tesir kesitlerini okumasında. Bu yüzden
varsayılan çözünürlük yüksek tutuldu.

**Hızlı mod** kütüphaneyi açık tutar: ilk çizim ~3 s, sonrakiler ~40 ms.
Bitmiş bir geometriyi incelerken (eksen değiştirme, yakınlaştırma) açın;
**düzenlerken açmayın** — her spec değişikliği yeniden başlatma gerektirir.

## Bilinen tuzaklar

- **Veri kütüphanesi sıcaklık aralıkları dar olabilir.** Nötron verisi
  250–2500 K, ama **su için S(α,β) yalnızca 284–800 K**. Aralık dışına çıkan bir
  sıcaklık taraması koşunun ortasında patlar; `veri_bilgi.py` bunu önceden okur.

- **`HexLattice` ve `HexagonalPrism` yönelimleri aynı harfi kullanır ama
  tanımları terstir** (biri "y eksenine dik", diğeri "y eksenine paralel").
  Pratikte aynı geometrik yönelim için **aynı harf** verilir; bu ölçümle
  doğrulanmıştır (`testler` → `test_altigen_sinir`). Yanlış eşleme %2.4 Δk
  hataya yol açıyordu.
- **Altıgen duct apothem'i** `(halka-1)·adım·√3/2 + adım/2`'dir,
  `(halka-0.5)·adım` değil. İkincisi köşelerde doğru görünür ama düz yüzlerde
  fazla boşluk bırakır.
- **`Model.plot()` renk sözlüğü** SVG renk adı veya `(R,G,B)` demeti ister;
  hex dize (`"#d95f02"`) `KeyError` verir.
- **Entropi açıkken OpenMC çıktı formatı değişir** (ek sütun). Çevrim satırı
  ayrıştırıcısı her iki biçimi de tanımak zorundadır.
- **Kutu kaynağın z aralığı modelin yüksekliğini kapsamalıdır.** Önceki sürümde
  ±1.0 cm'ye sabitti; 2B'de sorun değildi ama 366 cm'lik 3B bir modelde kaynak
  merkezdeki 2 cm'lik dilimde başlıyor ve eksenel güç şekli **aşırı tepeli**
  çıkıyordu (eksenel tepe 2.32 yerine 1.49). **Shannon entropisi bunu
  göstermedi** — entropi global bir skalerdir ve bu geometride radyal dağılım
  baskın gelir.
- **`Tally.scores` hiçbir doğrulama yapmaz** — uydurma bir skor adı bile kabul
  edilir, hata koşuda çıkar. OpenMC geçerli skor listesi sunmadığı için
  `dogrula.py` küratörlü bir listeye göre *uyarı* verir.
- **`Tally.get_pandas_dataframe`'de `distribcell_paths` yoktur**; doğru kwarg
  `paths=True`'dur (filtre sınıfındaki isimle karışmasın).
- **`Cell.num_instances` önce `Geometry.determine_paths()` ister**, aksi halde
  `ValueError`.

## Bilinen sınırlar

- **Kontrol elemanı hareketi** yok (çubuk daldırma, tambur dönüşü).
- **Eksenel heterojenlik** yok — kor tek eksenel bölge; zenginlik kuşağı,
  blanket, plenum tanımlanamaz.
- **Sabit kaynak modu yarım** — kaynak enerji spektrumu Watt'a sabit;
  kalkanlama/aktivasyon işleri yapılamaz.
- **Geometri içe aktarılamaz.** Malzemeler `materials.xml` / `model.xml`'den
  aktarılabilir (Dosya menüsü); geometri aktarılamaz çünkü ham CSG'yi
  "çubuk → kafes → kor" katmanlarına geri çevirmek genel olarak çözülebilir bir
  problem değildir. Yanlış bir tahmin sessizce yanlış model üretirdi.
- **Python betikleri içe aktarılamaz** — keyfi Python çözümlenemez.
- **Yanma (depletion)** kapsam dışı; zincir dosyası kurulmadı. Şema sürümlü
  (`"surum": 1`) tutuluyor, `"tuketim"` bölümü sonradan eklenebilir.
- `MPI` yok — OpenMC bu makinede OpenMP ile tek düğümde çalışıyor (24 çekirdek).

## Ortam

`openmc-env` conda ortamı gerekir:

```
openmc 0.16.0 (DAGMC, MPI yok)   PySide6 6.11.2   matplotlib   pandas   h5py
OPENMC_CROSS_SECTIONS = ~/nucdata/endfb-viii.0-hdf5/cross_sections.xml
```
