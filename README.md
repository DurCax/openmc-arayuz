# OpenMC Reaktör Kuru Arayüzü

English: [README.en.md](README.en.md)

Malzemeden kora kadar tüm model parametrelerinin tek bir arayüzden kurulduğu,
geometrinin çalıştırmadan önce görüldüğü ve hesabın aynı arayüzden başlatılıp
sonuçlarının okunduğu bir PySide6 masaüstü uygulaması.

> **İlk kez mi kuruyorsunuz?** Adım adım kurulum (conda ortamı, nükleer veri
> indirme, doğrulama) için **[KURULUM.md](KURULUM.md)**.

## Belge haritası

| Belge | Dil | İçerik |
|---|---|---|
| [README.md](README.md) · [README.en.md](README.en.md) | TR · EN | Genel bakış (bu dosya ayrıntılı ölçümleri ve tuzakları da içerir; İngilizcesi özettir) |
| [KURULUM.md](KURULUM.md) · [INSTALL.md](INSTALL.md) | TR · EN | Kurulum, nükleer veri, testler, sorun giderme |
| [docs/VV.md](docs/VV.md) · [docs/VV.en.md](docs/VV.en.md) | TR · EN | Doğrulama ve geçerleme: C/E tabloları, AOA, yanlılık ve USL, sınırlamalar |
| [docs/ORNEKLER.md](docs/ORNEKLER.md) · [docs/ORNEKLER.en.md](docs/ORNEKLER.en.md) | TR · EN | Örnek modeller, kaynakları ve ölçülen sonuçlar |
| [docs/GEOMETRI_MODELI.md](docs/GEOMETRI_MODELI.md) · [docs/GEOMETRI_MODELI.en.md](docs/GEOMETRI_MODELI.en.md) | TR · EN | Geometri ağacı: tam tasarım belgesi · kullanıcıya dönük İngilizce özet |
| [docs/STANDARTLAR.md](docs/STANDARTLAR.md) · [docs/STANDARTLAR.en.md](docs/STANDARTLAR.en.md) | TR · EN | Standartlar, uygunluk matrisi, NUREG/CR-6698 yöntem özeti |
| [docs/SOZLUK.md](docs/SOZLUK.md) | TR → EN | Bağlayıcı terim sözlüğü |
| [docs/GEREKSINIMLER.md](docs/GEREKSINIMLER.md) | TR | Gereksinimler (R-… kimlikleri) |
| [docs/IZLENEBILIRLIK.md](docs/IZLENEBILIRLIK.md) | TR | Gereksinim → test → sonuç matrisi (üretilir) |
| [docs/YAZILIM_KALITE.md](docs/YAZILIM_KALITE.md) | TR | Yazılım kalite kanıtı ve eksiklik listesi |

Kullanım kılavuzu (`docs/kilavuz/`, TR ve EN) hazırlanıyor.

## Hızlı başlangıç

```bash
conda activate openmc-env
cd ~/openmc_arayuz
./calistir.sh                          # başlangıç ekranı: "Ne modellemek istiyorsunuz?"
./calistir.sh ornekler/pwr_17x17.json  # doğrudan bir modelle (örnekler KOPYA açılır)
```

Başlangıç ekranında her model türü için bir kart vardır (yakıt çubuğu, kare/altıgen
yakıt demeti, tam kor, MTR plaka elemanı, tamburlu kor, zırhlama). **Boş başla**
çalışır durumda sade bir model kurar; **Örnekten başla** hazır bir örneğin
kaydedilmemiş kopyasını açar — `ornekler/*.json` test referansıdır, üzerine
yazılmaz ("Farklı kaydet" ile kendi dosyanıza kaydedin).

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
│   ├── veri_bilgi.py        kütüphane sıcaklık/enerji aralıkları, zincir bütünlüğü
│   ├── kurucu.py            spec → openmc.Model
│   ├── onbellek.py          model önbelleği (21.9 ms → 0.07 ms)
│   ├── uygunluk.py          TEK kural tablosu: bu modelde hangi sekme/alan/seçenek geçerli
│   ├── dogrula.py           koşu öncesi kontroller (uygunluk ile aynı kurallar)
│   ├── kod_uret.py          spec → tek başına çalışan Python betiği
│   ├── ice_aktar.py         materials.xml → spec malzemeleri
│   ├── tambur.py            dönen kontrol tamburu geometrisi ve yerleşimi
│   ├── kaynak.py            kaynak enerji tayfı, açısal dağılım, parçacık türü
│   ├── guc.py               çubuk bazlı güç dağılımı, F_ΔH, F_q
│   ├── tarama.py            parametre taraması → reaktivite katsayıları
│   ├── kritik_arama.py      hedef k-eff'i veren parametre değeri
│   ├── tukenme.py           yanma: zincir seçimi, analitik hacimler, koşu
│   └── kosucu.py            çalıştırma + statepoint okuma + terminal girişi
├── arayuz/                  PySide6 katmanı
│   ├── tema.py              açık/koyu tema paletleri (matplotlib dahil)
│   ├── ana_pencere.py       model başlığı, sekmeler, proje aç/kaydet, doğrulama paneli
│   ├── baslangic.py         başlangıç ekranı (kartlar, boş şablonlar, örnekler)
│   ├── izgara.py            parça paleti + kare/altıgen boyama ızgarası (demet ve kor haritası)
│   ├── ortak.py             Gelişmiş bölümü, boş durum, durum rozeti, tekerlek koruması
│   ├── onizleme.py          canlı geometri kesiti (3B'de xy + xz yan yana)
│   ├── guc_harita.py        güç dağılımı ısı haritası
│   └── sekme_*.py           malzeme / parça / demet / kor / ayar / çalıştır / analiz / tükenme
├── ornekler/                pwr_pinhucre, pwr_17x17, mtr_plaka, sfr_altigen,
│                            godiva_kriter, pwr_3b, pwr_kontrol, tamburlu_kor,
│                            zirh_kure, pwr_eksenel, pwr_tukenme
└── testler/                test_regresyon.py (giriş) + test_*.py modülleri (kendiliğinden bulunur)
```

## Çalışma akışı

Üstteki **model başlığı** ne modellediğinizi tek satırda söyler
("Model: PWR 17×17 yakıt demeti · 17×17 yakıt demeti · 2B · Özdeğer (k-eff)");
kor türü yalnızca buradaki **Türü değiştir…** ile değişir (Ctrl+Z geri alır).
Sekmeler numarasızdır ve **yalnızca modelde anlamlı olanlar görünür** (ör. zırhlamada
Parçalar/Demet/Analiz/Tükenme yoktur). Sekme adındaki işaret durumu söyler:
**✓** tamam, **!** bu sekmede hata var, **•** eksik adım.

- **Malzemeler** — kütüphane role göre gruplu (Yakıt / Zarf ve yapısal / Soğutucu ve
  moderatör / Emici / Gaz): UO₂, UN, U-10Mo, MOX, U₃Si₂-Al, Zircaloy-4, SS-316, MA956,
  FeCrAl, SiC, Al-6061, su (sıcaklıktan yoğunluk + bor), D₂O, LBE, Na, He, grafit,
  Be, B₄C, Gd₂O₃, Ag-In-Cd. Kütüphane malzemesi **parametreleriyle saklanır**:
  Düzenle aynı formu açar, sıcaklık/bor/zenginlik değişince yoğunluk ve açıklama
  yeniden hesaplanır. Zenginlik yalnız uranyum satırında yazılabilir. Ad değişimi
  modeldeki bütün kullanım yerlerini günceller.
- **Parçalar** — "+ Çubuk" şablonları (PWR yakıt çubuğu, kılavuz boru, kontrol çubuğu —
  kontrol yalnız 3B modelde); malzemeler role göre kendiliğinden seçilir. Plaka
  elemanı yalnız plaka modelinde.
- **Demet** — renkli **parça paletiyle** tıklayarak/sürükleyerek boyanır (sağ tık o
  hücrenin parçasını seçer); harf anahtarı arka planda otomatiktir. Harita solda,
  özellikler sağda.
- **Kor** — türün alanları; yükseklik tek seçim: 2B (sonsuz) / 3B tek bölge /
  3B katmanlı. Tam korun haritası da aynı paletle boyanır; katman tablosunda en üst
  katman en üsttedir.
- **Hesap ayarları** — Hesap türü + **Hesap hassasiyeti** (Hızlı deneme / Normal /
  Hassas; beklenen k-eff belirsizliği yazılır), kaynak, güç dağılımı, tally'ler
  (hazır skor setleri). Uzman alanları **Gelişmiş** altında.
- **Çalıştır** — iş parçacığı ve koşu dizini, canlı k-eff grafiği, sonuç kartı, güç
  haritası; ham çıktı katlanır "Ayrıntılı çıktı" altında.
- **Analiz** — yalnız bu modelde yapılabilecek taramalar (ör. bor hedefi yalnız su
  içeren malzeme) ve kritik arama.
- **Tükenme** — yanma hesabı (bkz. aşağı).

Sağ tarafta (tasarım sekmelerinde) her değişiklikten sonra geometri kesiti yenilenir,
altında doğrulama paneli canlı çalışır; hesap sekmelerinde bulgular durum çubuğundaki
rozettedir. **F1** Yardım ve terimler, **F5** veri kütüphanesiyle doğrula, **F6**
önizlemeyi yenile, **F9** çalıştır, **Ctrl+E** Python betiği olarak dışa aktar.

Neyin gösterilip neyin gizleneceği tek bir kural tablosundan gelir
(`cekirdek/uygunluk.py`); doğrulama da aynı kuralları kullanır, bu yüzden arayüzün
sunmadığı bir seçenek doğrulamada da hatadır. Gizlenen bir alanın değeri dosyadan
silinmez.

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
python3 -m testler.test_regresyon            # tümü (~8–25 dk; Monte Carlo ve tükenme dahil)
python3 -m testler.test_regresyon --hizli    # Monte Carlo hariç (~2–4 dk)
```

~2150 kontrol hızlı modda, ~2170 tam modda. `testler/test_*.py` modülleri
(`HIZLI`/`YAVAS` listeleri) kendiliğinden bulunur; testler kullanıcının gerçek
uygulama ayarlarına yazmaz (`testler/ortak_test.py` ayarları geçici dizine yönlendirir).
Asıl kanıtlar:

- **Regresyon çıpası** — `ornekler/pwr_pinhucre.json` referans değeri
  **k∞ = 1.3570 ± 0.0020** vermeli. 2σ dışına çıkarsa `kurucu.py`'de hata var.
- **Betik eşdeğerliği** — `kurucu.py` ile üretilen betik aynı tohumla **birebir
  aynı** k-eff vermeli (kare ve altıgen için ayrı ayrı). `kurucu.py` ya da
  `kod_uret.py` değiştirilirse mutlaka tekrar koşulmalı.
- **Altıgen düzen** — `altigen.py`'nin halka indeksleri OpenMC'nin kendi
  `HexLattice.show_indices()` çıktısıyla birebir uyuşmalı.
- **Godiva kriteri** — yayımlanmış k_eff'ten 2σ'dan fazla sapmamalı.
- **Betik anlamsal eşdeğerliği** — 11 örneğin her birinde kurucu ile betik aynı
  malzeme ve ayar XML'ini, aynı tally'leri ve 400 rastgele noktada aynı malzemeyi
  kurmalı (`test_butunlesme.py`). Betikte spec adlarından gelen değişkenler türe
  göre önekli ve benzersizdir (`m_uo2`, `c_yakit_cubugu`, `d_demet_17x17`); "a b"
  ile "a_b" ya da "class"/"openmc" gibi adlar betiği bozamaz.
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
| `pwr_kontrol` (çubuk %0) | 1.17801 ± 0.00196 | 24 s |
| `tamburlu_kor` (dönme 180°) | 1.01057 ± 0.00157 | 21 s |
| `zirh_kure` (sabit kaynak) | k-eff yok, tally | 24 s |
| `pwr_eksenel` (katmanlı) | 1.17680 ± 0.00052 | 86 s |
| `pwr_tukenme` (20 MWd/kg) | 1.35930 → 1.06545 | ~50 dk |

## Kontrol çubuğu ve kritik çubuk konumu

Kontrol çubuğu **Parçalar** sekmesinde "+ Çubuk → Kontrol çubuğu" şablonuyla eklenir (yalnız 3B modelde).
Çubuk **yukarıdan** daldırılır; emici bölge, uç konumunda ikiye bölünür:
ucun üstü emici, altı izleyici malzeme.

```
daldırma %0   → uç z = +H/2   (emici kor içinde yok)
daldırma %100 → uç z = −H/2   (emici tüm yüksekliği kaplar)
```

3B model gerektirir — eksenel bir uç konumu olmadan daldırma tanımlanamaz.

**Analiz** sekmesinde iki kullanımı var:
- *Parametre taraması* → integral çubuk değeri eğrisi
- *Kritik arama* + hedef k=1 → **kritik çubuk konumu**

Ölçülen (`pwr_kontrol`, 25 B4C çubuğu): kritik konum **%87.85 ± 0.09**, 13 koşuda.

> ⚠ **Eğri şekli hakkında.** Klasik S eğrisi yalnızca sistem *her konumda
> kritiğe yakınsa* görülür. Bu örnek yansıtıcı yan sınırlı tek bir demettir ve
> k∞ yüksektir; rodlanmamış alt bölge tek başına süperkritik kalır. Bu yüzden
> değer geç toplanır ve diferansiyel değer tepesi merkezde değil tam daldırmaya
> yakın çıkar. Ölçülen: %0 → k=1.165, %50 → k=1.131, %100 → k=0.588.

## Kontrol tamburu (dönen)

Kompakt/uzay reaktörlerinde (Kilopower, KRUSTY, PETEK) çubuk yerine **dönen
tambur** kullanılır: yansıtıcı kuşağına gömülü silindirlerin bir yayı emicidir,
dönerek kora yaklaşır veya uzaklaşır.

Kor türü **`Tamburlu kor`** ile kurulur: silindirik kor + yansıtıcı kuşak +
kuşağa gömülü N tambur.

```
dönme 0°   → emici KORA bakıyor  = daldırılmış (en düşük k)
dönme 180° → emici DIŞA bakıyor  = çekilmiş   (en yüksek k)
```

Ölçülen (`tamburlu_kor`, 8 B4C tamburu, 120° yay): k(0°)=0.963, k(180°)=1.012 →
toplam tambur değeri ~5000 pcm. **Kritik tambur konumu = 122.46° ± 3.68**,
4 koşuda bulundu.

> 📐 **Dönme matematiği ölçümle belirlendi.** `openmc.Cell.rotation = (0,0,ψ)`
> emici yayı **doğrudan ψ açısına** koyar — ters çevirme veya kaydırma yok.
> (Nokta sorgusuyla ölçüldü: ψ=45° → yay merkezi 44.5°.) Azimutu φ olan bir
> tamburda emicinin kora bakması için `ψ = φ + 180 + dönme`. Bunu çizimden
> okumaya çalışmak yanıltıcı: ilk denemede grafiği yanlış okuyup konvansiyonun
> ters olduğunu sanmıştım.

**Yerleşim canlı doğrulanır:** tamburlar kora giriyor mu, yansıtıcıdan taşıyor
mu, komşular çakışıyor mu (kiriş mesafesi `2·R_m·sin(π/N)` ile). Geçersiz
yerleşim koşuyu değil **model kurulumunu** durdurur.

## Eksenel heterojenlik

Gerçek bir reaktörde aktif yakıt tek bir eksenel bölge değildir: altta ve üstte
yansıtıcı, aktif bölgenin ucunda doğal uranyum blanket, gaz plenumu, farklı
zenginlik kuşakları bulunur. Bunlar olmadan eksenel güç şekli ve reaktivite
katsayıları gerçekçi çıkmaz.

**Kor** sekmesinde yükseklik "3B, katmanlı" seçilince açılan **Eksenel katmanlar** tablosuyla kurulur. Katmanlar
**alttan üste** sıralanır:

```json
"eksenel": {"var": true, "bolgeler": [
  {"ad": "alt yansitici", "yukseklik":  20.0, "dolgu": "su"},
  {"ad": "alt blanket",   "yukseklik":  15.0, "dolgu": "demet_blanket"},
  {"ad": "aktif yakit",   "yukseklik": 300.0, "dolgu": null},
  {"ad": "ust blanket",   "yukseklik":  15.0, "dolgu": "demet_blanket"},
  {"ad": "plenum",        "yukseklik":  25.0, "dolgu": "demet_plenum"},
  {"ad": "ust yansitici", "yukseklik":  20.0, "dolgu": "su"}
]}
```

- `dolgu` boş (`null`) bırakılırsa korun **ana dolgusu** kullanılır.
- `dolgu` bir çubuk, plaka, demet ya da malzeme adı olabilir.
- `kare_kafes` korunda katmana özel **`anahtar`** verilebilir: harita aynı kalır,
  yalnızca harf → demet eşlemesi değişir. Eksenel zenginlik kuşaklama böyle
  yapılır — hangi konumda ne olduğu eksenel olarak değişmez, fiziksel olarak da
  değişmez, değişen yalnızca her harfin o katmanda ne anlama geldiğidir.
  (Bu alan şimdilik JSON'dan girilir; tablo onu **silmez**, kilitli gösterir.)
- Katmanlama açıkken modelin yüksekliği **katman toplamıdır**; `yukseklik` alanı
  yok sayılır ve arayüz onu `null`'a çeker (tek gerçek kaynak kuralı).
- Desteklenen kor türleri: `tek_cubuk`, `tek_plaka`, `tek_demet`, `kare_kafes`,
  `tamburlu`. `kuresel`de eksen kavramı yoktur.

> ⚠ **İç katman arayüzleri daima geçirgendir.** Sınır koşulu yalnızca en alt ve
> en üst yüzeye uygulanır. İç bir yüzeye yansıtıcı sınır konursa korun üstü
> altından **kopar** ve bunu k-eff'e bakarak fark etmek neredeyse imkânsızdır;
> bu yüzden her z düzleminin sınır koşulu teste bağlandı.

### Üç ayrı yükseklik — karıştırılmamalı

Katmanlama gelince "kor yüksekliği" tek bir sayı olmaktan çıktı:

| | ne | nerede kullanılır |
|---|---|---|
| **toplam model** | katman toplamı | geometri, eksenel sınır koşulları |
| **fisil aralık** | fisil malzeme içeren katmanlar | başlangıç kaynağı kutusu, kontrol çubuğu daldırması |
| **hedef çubuk aralığı** | o çubuğun bulunduğu katmanlar | güç dağılımı eksenel mesh'i, W/cm |

`pwr_eksenel` için sırasıyla **395 / 330 / 300 cm**. Fisil aralık doğal uranyum
blanket'i içerir (U-238 fisyon yapar), ama blanket'te `yakit_cubugu` **yoktur**.

Kontrol çubuğu daldırması artık **aktif** aralıkta tanımlı: %0 = uç aktif
bölgenin tepesinde, %100 = dibinde. Katmanlama yokken üçü de `±H/2`'ye eşit
olduğu için eski modeller bit düzeyinde aynı sonucu verir.

### Örnek: `pwr_eksenel`

`pwr_3b` ile aynı 17×17 demet, katmanlı. **İkisi de aynı ayarla** koşuldu
(250 çevrim / 100 pasif) — farklı ayarlardan gelen sayıları karşılaştırmak
yanıltıcı olurdu:

| | `pwr_3b` (katmansız) | `pwr_eksenel` (katmanlı) |
|---|---|---|
| k-eff | 1.18002 ± 0.00051 | 1.17680 ± 0.00052 |
| F_ΔH | 1.0674 | **1.0674** |
| **F_q** | 1.7210 | **1.6435** |

**F_ΔH dört hanede birebir aynı çıktı.** Eksenel katmanlama radyal dağılıma
dokunmaz, dolayısıyla böyle olması gerekiyordu — iyi bir tutarlılık kontrolü.
Değişen yalnızca F_q: 1.7210 → 1.6435 (−%4.5). Su yansıtıcı eksenel
ekstrapolasyon mesafesini büyütüyor, yakıtın uçlarındaki akı yükseliyor ve
eksenel profil düzleşiyor. Vakum uçlu `pwr_3b`'de profil kesilmiş kosinüstür.

> **k-eff farkı temiz bir yansıtıcı kazancı ölçümü DEĞİL.** İki model birden
> fazla yönden farklı: yakıt kolonu 366 cm %3.2 yerine 300 cm %3.2 + 30 cm doğal
> UO2. Doğal uranyum termal spektrumda net soğurucudur, yansıtıcı ise sızıntıyı
> azaltır; iki etki ters yönde çalışıyor ve net sonuç −232 pcm. Yansıtıcı
> kazancını ayrı ölçmek isterseniz yalnızca su katmanlarını ekleyip blanket'i
> çıkarın.

> **Pasif çevrim:** katmanlı modelde 40 pasif çevrim **yetmedi** — Shannon
> entropisi pasif dönemin sonunda hâlâ kayıyordu (kayma 0.0433 > 2σ = 0.0125).
> 100'e çıkarınca kayma 0.0006'ya düştü. Bu uyarı ancak entropi mesh'inin z
> sınırları düzeltildikten sonra güvenilir oldu (aşağıdaki tuzak listesi).

## Tükenme (yanma)

Yakıtın zaman içinde nasıl değiştiğini hesaplar: U-235 tükenir, Pu-239 birikir,
Xe-135 ve Sm-149 gibi fisyon ürünü zehirleri reaktiviteyi düşürür. Her adımda
transport çözülür, reaksiyon hızları alınır, Bateman denklemleri OpenMC'nin CRAM
çözücüsüyle ilerletilir.

```json
"tukenme": {
  "var": true,
  "zincir": "otomatik",          // otomatik | termal | hizli | casl_termal | casl_hizli
  "guc_yogunlugu": 40.0,         // W/gHM
  "adimlar": [0.5, 1.5, 3, 5, 10, 30, 100, 350],
  "adim_birimi": "d",            // d | MWd/kg
  "entegrator": "cecm",          // cecm (2 transport/adım) | predictor (1)
  "malzemeleri_ayir": false,
  "izlenen": ["U235","U238","Pu239","Pu240","Pu241","Xe135","Sm149"]
}
```

Terminalden: `python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 16`
(`--hazirla` koşmadan hacim/zincir/ağır metal bilgisini yazar).

**Neden güç yoğunluğu (W/gHM), mutlak güç değil?** Mutlak güç 2B bir modelde
"cm başına" olmak zorunda kalırdı — bu projede birkaç kez yakaladığımız türden
sessiz bir birim tuzağı. W/gHM geometriden bağımsızdır ve mühendislerin
gerçekten verdiği sayıdır (PWR ~38–40, BWR ~25, SFR 50–100).

### Zincir: termal mi hızlı mı — ve fisyon verimi

| | nüklid | ne zaman |
|---|---|---|
| ENDF/B-VIII.0 termal | 3820 | su, grafit, ZrH moderatörlü sistemler |
| ENDF/B-VIII.0 hızlı | 3820 | SFR, Godiva, PETEK, U-10Mo kompakt kor |
| CASL basit termal/hızlı | 228 | ön inceleme — ~3 kat hızlı |

`otomatik`: modelde hidrojen/döteryum ya da grafit S(α,β)'sı varsa termal, yoksa
hızlı. Berilyum **bilerek** sayılmıyor: tamburlu korda Be yalnızca yansıtıcıdır,
kor spektrumu hızlıdır.

İki zincir **101 nüklidin yakalama dallanma oranında** farklı (ölçüldü). Örnek:
Am-241(n,γ) → Am-242m termalde %8.1, hızlıda %13.2.

> ⚠ **Hızlı zincir seçmek yetmez.** Zincir yalnızca dallanma oranlarını değiştirir;
> fisyon ürünü verimleri ayrı bir ayardır ve OpenMC'nin varsayılanı **sabit
> 0.0253 eV**'tur — hızlı zincir seçilse bile. Yani hızlı bir reaktörde fisyon
> ürünleri sessizce termal verimle üretilirdi. Burada hızlı sistemde verim
> enerjisi 500 keV'e çekiliyor (testte operatöre geçtiği doğrulandı; U-235 →
> Xe-135 bağımsız verimi termalde 0.00079, hızlıda 0.00120).

### Hacimler analitik — ve neden bu kadar önemli

OpenMC tükenmede her yanabilir malzemenin hacmini ister: reaksiyon hızı / (N·V)
atom başına hızı verir. **Hacim f kat yanlışsa yanma hızı da f kat yanlış olur —
k-eff'te hiçbir iz bırakmadan.** Hacim, bölge alanı × (katman yüksekliği × o
katmandaki çubuk sayısı) toplamı olarak analitik hesaplanır; çubuk, plaka,
küresel kabuk, tamburlu kor silindiri, eksenel katmanlar ve altıgen demetler
destekleniyor. OpenMC'nin stokastik hacim hesabıyla karşılaştırıldı:

| örnek | malzeme | analitik | stokastik | fark |
|---|---|---|---|---|
| pwr_17x17 | uo2 | 139.147 | 139.187 ± 0.122 | −0.33σ |
| pwr_eksenel | uo2 / uo2_dogal | 41744.1 / 4174.41 | 41786.5 ± 44 / 4164.7 ± 16 | −0.96σ / +0.62σ |
| sfr_altigen | u10mo | 40.8558 | 40.8179 ± 0.033 | +1.13σ |
| mtr_plaka | u3si2_al | 7.3899 | 7.3987 ± 0.011 | −0.80σ |
| tamburlu_kor | u10mo | 36191.1 | 36155.1 ± 36 | +1.01σ |

Ağır metal kütlesi OpenMC'nin kendi hesabıyla birebir aynı (4.2591911 g).
2B modelde hacim 1 cm yükseklik içindir; güç yoğunluğu kullanıldığı için bu
tutarlıdır (kütle ve güç aynı oranda ölçeklenir).

### Maliyet (ölçülmüş)

Zincirdeki nüklidler yakıta eklenir, transport bu yüzden yavaşlar. Pin hücre,
2000 × 20 parçacık, 2 transport:

| zincir | yakıttaki nüklid | süre |
|---|---|---|
| CASL | 228 | 37 s |
| ENDF/B-VIII.0 | 3820 | 125 s |

Arayüz kalan süreyi **ilk transportun gerçek süresinden** hesaplar, tahmin etmez.

### Önceki sonuç — ve eskimesi

Sekme açılışta son koşunun sonucunu gösterir; 50 dakikalık bir koşuyu görmek için
yeniden koşmak gerekmez. Tuzak: o sonuç **şu anki modele ait olmayabilir**.
Kullanıcı koşudan sonra gücü ya da zenginliği değiştirmiş olabilir; eski bir
sonucu güncelmiş gibi göstermek hiç göstermemekten kötüdür. Bu yüzden:

- Koşu başında spec'in kopyası (`tukenme_spec.json`) sonuçla aynı dizine yazılır.
  Önce **eski sonuç silinir**: yarıda kalan bir koşu eski sonucu yeni kaydın
  yanında bırakıp "güncel" gösterilmesine yol açardı.
- Açılışta ve her düzenlemede karşılaştırılır: **bu modele ait** / kırmızı
  **ESKİ SONUÇ** (hangi bölümün değiştiği yazılır) / **doğrulanamıyor** (kayıt yok).
  Ad, açıklama ve koşu dizini fiziği etkilemediği için sayılmaz; tükenmeyi
  kapatıp açmak da sonucu eskitmez.
- Karşılaştırma metinle (hash) değil Python eşitliğiyle yapılır: JSON'da `3` ile
  `3.0` farklı metindir ama aynı sayıdır.
- Sonuç **kayıttaki** spec'e göre okunur, şu ankine göre değil — malzeme
  eşlemesi ve hacimler koşudaki modelden gelsin.

Okuma arka planda yapılır. Ölçüldü: 3.4 s (`openmc.deplete` içe aktarımı 1.2 s +
`Results` dosyadaki 3820 nüklidin hepsini ayrıştırıyor 2.0 s). Arayüz 0.001 s
bloklanıyor. İlk sürüm pencere kapanırken okumanın bitmesini beklemiyordu:
örneği açıp hemen kapatınca süreç **kapanışta asılı kalıyordu** (60 s zaman
aşımı). Test alt süreçte bunu sınıyor.

### Örnek: `pwr_tukenme`

`pwr_pinhucre` ile aynı pin, 40 W/gHM, 500 gün (20 MWd/kg), tam ENDF/B-VIII.0
termal zincir, CECM, 5000 × 60 parçacık. Ağır metal 4.259 g, 17 transport, ~50 dakika:

| gün | MWd/kg | k∞ | not |
|---|---|---|---|
| 0 | 0 | 1.35930 ± 0.00184 | regresyon çıpasıyla (1.3570 ± 0.0020) 1σ içinde |
| 0.5 | 0.02 | 1.32788 ± 0.00179 | Xe-135 birikiyor |
| 2 | 0.08 | 1.31232 ± 0.00211 | Xe-135 dengede |
| 5 | 0.2 | 1.30615 ± 0.00179 | |
| 10 | 0.4 | 1.30014 ± 0.00173 | Sm-149 birikmeye devam ediyor |
| 20 | 0.8 | 1.29382 ± 0.00176 | |
| 50 | 2 | 1.27547 ± 0.00175 | |
| 150 | 6 | 1.22697 ± 0.00177 | |
| 500 | 20 | 1.06545 ± 0.00168 | |

- **Xe-135 + erken Sm-149 (0 → 2 gün): Δρ = −2634 ± 158 pcm** — tam güç PWR için
  yayımlanan ~2500–3000 pcm bandında. Xe-135 7.74e-9 atom/b·cm'de dengeye oturuyor.
- **20 MWd/kg'da** U-235'in %40'ı kalıyor, Pu-239 ağır metalin ~%0.5'i
  (Pu-239/U-235 = 0.42). Kaba bir elle hesap (200 MeV/fisyon, Pu ve U-238 fisyon
  payı, α ≈ 0.17) %38–48 veriyor — tutarlı. Bunlar **akla yatkınlık**
  kontrolleridir; asıl kanıtlar aşağıdaki Bateman testi, hacim karşılaştırması ve
  betik eşdeğerliğidir.

İlk iki adım bilerek kısa (0.5 ve 1.5 gün): Xe-135 ~2 günde dengeye gelir;
uzun bir ilk adım bu hızlı düşüşü tek bir çizgiye ezer ve görünmez kılar.
Doğrulama bunu uyarır.

### Analitik doğrulama — Bateman

Güç sıfırken tek bir radyonüklid N(t) = N₀·exp(−ln2·t/T½) izlemeli. Yarı ömür
**zincirin kendisinden** okunur, dolayısıyla test hem zincir dosyasını hem
çözücüyü sınar. Xe-135, I-131, Co-60 için bir ve iki yarı ömürde N/N₀ = 0.5 ve
0.25, **on hanede**. (Zincirdeki yarı ömürler gerçek değerler: 9.14 saat,
8.02 gün, 5.27 yıl.)

Üretilen betiğin `tukenme_kos()` fonksiyonu ile `cekirdek/tukenme.py` her
adımda **bit düzeyinde aynı** k-eff'i veriyor (iki yol ayrı alt süreçte,
`OMP_NUM_THREADS=1` ile).

### Zinciri kendin indirmek ve doğrulamak

İlk indirme (23.09.2026) **%13'te sessizce kesilmişti**: 3 645 440 / 27 526 672
bayt, bir özniteliğin ortasında bitiyordu. Dosyanın adı ve yeri doğruydu; bakan
biri bir sorun görmezdi. Bir dahaki sefere:

```bash
URL=https://anl.box.com/shared/static/nyezmyuofd4eqt6wzd626lqth7wvpprr.xml
# 1. Sunucunun söylediği boyut (box.com HEAD'e 404 verir, 1 baytlık GET kullanın)
curl -sL -r 0-0 -D - "$URL" -o /dev/null | grep -i content-range   # .../27526672
# 2. Önce geçici adla indir, yarım kalırsa -C - ile sürdür
curl -L --fail --retry 3 -C - -o zincir.xml.part "$URL"
# 3. Boyut eşit mi, dosya kapanıyor mu, ayrıştırılıyor mu?
stat -c %s zincir.xml.part
tail -c 200 zincir.xml.part | grep -c "</depletion_chain>"            # 1 olmalı
python3 -c "import openmc.deplete as d; print(len(d.Chain.from_xml('zincir.xml.part').nuclides))"
# 4. Ancak hepsi tamamsa asıl adına taşı
mv zincir.xml.part chain_endfb80_thermal.xml
```

Arayüz ve `calistir.sh` bunu artık kendileri yapar: yarım bir zincir doğrulama
panelinde **hata** olarak görünür ve tükenme başlatılamaz.

> **WMP (çok kutuplu) veri bilerek indirilmedi.** openmc.org'daki 1.7 GB'lık
> dosya ayrı bir WMP verisi değil, **ENDF/B-VII.1 kütüphanesinin tamamı**; WMP
> yalnızca VII.1 ile sunuluyor. VIII.0 kesitleriyle karıştırmak iki farklı
> değerlendirmeyi tek modelde birleştirmek olurdu; kütüphaneyi değiştirmek ise
> bütün ölçüm çıpalarını geçersiz kılardı.

## Güç dağılımı ve tepe faktörleri

Hesap ayarları sekmesinden açılır (yalnız fisil çubuğu tekrarlanan modellerde görünür); sonuç **Çalıştır** sayfasında güç haritası olarak çıkar.
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

## Reaktivite katsayıları ve kritik arama (Analiz)

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

**Kritik arama** hedef k-eff'i veren değeri bulur (kritik bor, kritik çubuk
konumu, kritik yükseklik…). Kök aralıkta değilse **ekstrapolasyon yapmaz**,
aralığı genişletmenizi söyler.

Yöntem **parantez korumalı yanlış konum + ikiye bölme**: kiriş tahmini parantez
dışına düşerse ya da daha önce ölçülen bir noktaya denk gelirse ikiye bölmeye
geçer. (İlk sürüm saf sekanttı ve aralık ucunu üst üste koşuyordu — 12
iterasyonun 2'si boşa gidiyordu.)

Durma ölçütü `|k − hedef| ≤ 2σ`'dır; aynı tanımı sonuç paneli de kullanır
(`keff_yorumu`). Daha sıkı bir ölçüt (1σ) aramanın, panelin **kritik dediği** bir
konfigürasyonu reddetmesine yol açıyordu.

**Kökün kendisi de belirsizdir.** Yerel eğimden `δx = σ_k / |dk/dx|` olarak
tahmin edilip raporlanır. Parantez bu belirsizliğin altına indiğinde daha fazla
iterasyon bilgi katmaz — arama durur ve bunu söyler.

Örnekler: 17×17 için kritik bor **3430 ppm** (7 koşu); `pwr_kontrol` için
kritik çubuk konumu **%87.85 ± 0.09** (13 koşu); `tamburlu_kor` için kritik
tambur konumu **122.46° ± 3.68** (4 koşu).

## Kinetik parametreler

Hesap ayarlarından açılır (IFP yöntemi; dışa aktarılan betik de aynı IFP ayarını yazar). Ölçülen:

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

## Sabit kaynak ve enerji tayfı

Özdeğer (k-eff) hesabında kaynak tayfı yalnızca **başlangıç tahminidir** — pasif
çevrimler içinde gerçek fisyon tayfıyla değişir. Sabit kaynak hesabında
(zırhlama, aktivasyon, dedektör) ise **sonucun kendisidir**. Eskiden tayf
`openmc.stats.Watt()` olarak gömülüydü; artık Hesap ayarları sekmesinden seçilir:

| Tayf | Parametre | Analitik ortalama | Ölçülen |
|---|---|---|---|
| Watt (fisyon) | a=988 keV, b=2.249e-6 | 1.5a + a²b/4 = 2.031 MeV | 2.034 MeV |
| Maxwell | θ=1.2932 MeV | 1.5θ = 1.940 MeV | 1.943 MeV |
| Tek enerjili | E | E | tam |
| Ayrık çizgiler | [E, p] çiftleri | Σ E·p / Σ p | tam |
| Histogram | N+1 kenar, N değer | grup ağırlıklı | — |
| Füzyon (Muir) | E₀, kütle oranı, kT | E₀ | σ = 335 keV |

Füzyon genişlemesi analitik değerle doğrulandı: D-T için `FWHM = 177·√(kT[keV]) keV`
→ kT=20 keV'de σ = 336.2 keV, ölçülen 335.2 keV.

Ayrıca **açısal dağılım** (izotropik / tek yönlü demet / koni), **parçacık türü**
(nötron / foton — foton seçilince foton taşınımı otomatik açılır) ve **kaynak
şiddeti** ayarlanabilir.

> 📐 **Şiddet normalizasyonu ölçüldü.** OpenMC sabit kaynak tally'lerini kaynak
> şiddetiyle **kendisi çarpar** (şiddet=1 ve 1e12 ile koşuldu, oran tam 1e12).
> Yani sonuçlar zaten mutlak birimdedir; kullanıcıya "şiddetle çarpın" demek
> çift sayım olurdu. İlk yazdığım not tam olarak bu hatayı yapıyordu.
>
> Bir tuzak daha: `flux` skoru **hacimle integrelidir** (birim cm/s). Nokta akısı
> [1/cm²/s] için bölge hacmine bölmek gerekir.

### Analitik doğrulama — üstel zayıflatma

Sabit kaynak yolunun doğruluğu **tam analitik** bir sonuçla sınandı. Merkezde
monoenerjetik termal kaynak, çevresinde optik kalınlığı τ=1 olan B-10 küresi
(termalde saçılma 2.1 b, soğurma 3847 b → saçılma ihmal edilebilir):

```
soğurulan kesir = 1 − exp(−τ) = 0.63212   (analitik)
                              = 0.63180 ± 0.00032   (ölçülen, 1.0σ)
```

Bu tek test aynı anda şunları doğrular: tek enerjili kaynağın enerjisi doğru,
sabit kaynak modu çalışıyor, tally normalizasyonu kaynak parçacığı başına.

### Örnek: `zirh_kure`

Merkezde 14.1 MeV D-T kaynağı, 30 cm su + 5 cm çelik. Ölçülen nötron dengesi:

| | değer |
|---|---|
| suda soğurma | 0.678 / kaynak nötronu |
| çelikte soğurma | 0.080 |
| sızıntı | 0.242 |

Suda termal akı (2.55e8) hızlı akıyı (2.35e8) geçiyor — su yavaşlatıyor.
Çelikte oran tersine dönüyor (4.17e7 hızlı / 5.1e6 termal) — ağır çekirdek
yavaşlatmaz, demir termali soğurur. Beklenen fizik bu.

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

Kısayol: **F11** tam ekran.

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


### Önizleme, tally'ler yüzünden bütün uygulamayı çökertiyordu

Arayüzü gerçekten açıp bakınca çıktı — testler görmemişti. `Model.plot()`
geometriyi dilimlemek için **OpenMC kütüphanesini başlatıyor** ve bu sırada
tally'leri de çözmeye çalışıyor. Güç dağılımı tally'sine eklenen `CellFilter`
çözülemeyince OpenMC C++ tarafında `terminate()` çağrılıyor:

```
terminate called after throwing an instance of 'std::runtime_error'
  what():  Could not find cell 0 specified on tally filter.
```

Bu bir Python istisnası değil — `try/except` yakalayamaz, süreç doğrudan
**SIGABRT** ile ölür. Ölçüldü: düzeltmeden önce 3/3 koşuda çökme, sonra 4/4 temiz.

İki önlem alındı:
- **Önizleme tally'siz bir model çiziyor.** Zaten sadece geometri, malzeme ve
  sıcaklık ayarları gerekiyor; ileride eklenecek her tally türü de aynı riski
  taşırdı.
- **Yeniden girme koruması.** Çizim sürerken ikinci bir çizim başlarsa aynı
  süreçte ikinci bir kütüphane oturumu açılırdı.

> ⚠ **Çökme yalnızca gerçek bir X oturumunda, tam arayüz akışında tekrarlanıyor.**
> Başsız (`QT_QPA_PLATFORM=offscreen`) ortamda düzeltme kapalıyken bile
> çökmüyor, dolayısıyla otomatik test çökmenin kendisini üretemiyor. Test bunun
> yerine **değişmezi** sınıyor: çizime giden modelde tally sayısı sıfır olmalı
> (`Model.plot` sarmalanıp ölçülüyor). Elle tekrar tarifi: `pwr_eksenel.json`'ı
> arayüzde açın, Kor sekmesine geçin; 3B modelde önizleme xy ve xz kesitlerini yan yana gösterir.

**İkinci ders aynı yerden:** `test_cizim` ve `test_dogrulama_temiz` örnek
listelerini **elle** tutuyordu; yeni eklenen `zirh_kure` ve `pwr_eksenel` kapsam
dışında kalmıştı. İkisi de artık `ornekler/*.json` dizinini tarıyor.

### S(α,β) kuralı saf zirkonyuma hidrojen öneriyordu

Kural yalnızca "malzemenin elementleri izin verilen kümenin alt kümesi mi" diye
bakıyordu. {Zr} ⊆ {H, Zr} olduğu için **saf zirkonyum "zirkonyum hidrür"**
sayılıyor ve kullanıcıya `c_H_in_ZrH` eklemesi öneriliyordu — hidrojensiz bir
malzemeye hidrojen S(α,β)'sı, yani yanlış fizik. Aynı mantıkla B₂O₃ "borlu su"
çıkardı. Her kurala **zorunlu** element kümesi eklendi. `pwr_pinhucre`'nin
başından beri taşıdığı uyarı bu yanlış alarmdı.

### Eksenel katmanlama üç hata ortaya çıkardı (hepsi ölçümle bulundu)

**1. "Fisil aralık"ın iki ayrı tanımı → 1300 pcm.** Kurucu aralığı kurulmuş
geometriden türetiyordu, üretilen betik ise spec'ten. Betik ötekinin ne yaptığını
bilemediği için farklı kaynak kutusu kuruyordu. Geometri 400 noktada birebir
aynıydı — fark **ayarlardaydı**. Tek tanıma indirildi.
*Ders: aynı sayıyı iki yoldan hesaplayan iki kod, er ya da geç ayrışır.*

**2. Korunum tally'si tüm modeli sayıyordu → sahte "BOZUK" (4.73e-03).**
Doğal uranyum blanket de fisyon yapıyor ama distribcell'e dahil değil. Referans
tally `CellFilter` ile aynı hücreye bağlandı; kontrol böylece **güçlendi** —
artık eksenel mesh'in hücrenin tamamını kapsayıp kapsamadığını da sınıyor.

**3. Güç mesh'i hedef çubuktan taşıyordu → F_q %6 şişti (1.6435 → 1.8150).**
Mesh fisil aralığı kapsıyordu, ama blanket katmanlarında `yakit_cubugu` yok;
boş bin'ler ortalamayı düşürüp tepeyi şişiriyordu. Sayılar makul görünüyordu —
sessiz hata tam olarak budur. Mesh artık **hedef çubuğun** aralığını kullanıyor.

**Ayrıca:** entropi mesh'inin z sınırları `±1e10`'da sabitti. `nz=1` iken
zararsızdı ama `nz>1` istendiğinde bütün parçacıklar tek dilime düşüyor ve
eksenel yakınsama hiç ölçülmemiş oluyordu; entropi yine "yakınsadı" diyordu.
Gerçek yükseklikten türetildikten sonra `pwr_eksenel`'de 40 pasif çevrimin
yetmediğini **bu uyarı yakaladı**.

### U₃Si₂-Al yoğunluğu yüklemeyle tutarsızdı

Kütüphanedeki dispersiyon yakıtı 4.8 gU/cm³ yüklemede sabit **5.4 g/cm³**
yoğunlukla kuruluyordu; U₃Si₂ (12.2 g/cm³) + Al (2.70 g/cm³) karışımından bu
yüklemede **6.73 g/cm³** çıkar ve eski değerde alüminyumun kütle payı %23 yerine
%4'e düşüyordu. Yoğunluk artık yüklemeden hesaplanır
(`malzeme_kutup.u3si2_yogunlugu`; isteğe bağlı gözeneklilik). Elle verilmiş
yoğunluk (eski kayıtlar, `mtr_plaka` örneği) aynen kullanılır.

### Dışa aktarılan betik bazı adlarda sessizce farklı model kuruyordu

Spec adları doğrudan Python değişkeni oluyordu: "a b" ve "a_b" malzemeleri aynı
değişkene düşüyor (400 noktanın 4'ünde farklı malzeme), "class", "None",
"openmc", "malzemeler" adları betiği çalışmaz yapıyordu; ayrıca kinetik (IFP)
açıkken betik β_eff tally'lerini yazmıyordu. Değişkenler artık türe göre önekli
ve benzersiz, IFP betikte de var; `test_butunlesme.py` 11 örnekte anlamsal
eşdeğerliği denetler.

## Bilinen sınırlar

- **Küresel düzenek kabukları arayüzden düzenlenemiyor** — yalnızca JSON'dan
  (`ornekler/godiva_kriter.json`). Arayüz kor türünü gösterir ve uyarır.
- **Tambur yayı tek parça.** Çok parçalı ya da eksenel olarak bölünmüş tambur
  desteklenmiyor.
- **Tambur eksenel olarak bölünmüyor.** Eksenel katmanlar tamburlu korda kor
  silindirinin içinde çalışır; tamburlar ve yansıtıcı kuşak tam yüksekliği kaplar.
- **Katmana özel harf eşlemesi (`anahtar`) yalnızca JSON'dan** girilir ve yalnızca
  `kare_kafes` korunda geçerlidir. Tablo onu silmez, kilitli gösterir.
- **Sabit kaynakta uzaysal dağılım sınırlı** — nokta ya da kutu. Yüzey kaynağı,
  hacimsel kaynak dosyası ve dış kaynak dosyası (`source.h5`) desteklenmiyor.
- **Doz dönüşüm faktörleri yok** — akı tally'si var, ICRP akı→doz çarpanı yok;
  doz için dönüşümü kullanıcı kendisi yapar.
- **Geometri içe aktarılamaz.** Malzemeler `materials.xml` / `model.xml`'den
  aktarılabilir (Dosya menüsü); geometri aktarılamaz çünkü ham CSG'yi
  "çubuk → kafes → kor" katmanlarına geri çevirmek genel olarak çözülebilir bir
  problem değildir. Yanlış bir tahmin sessizce yanlış model üretirdi.
- **Python betikleri içe aktarılamaz** — keyfi Python çözümlenemez.
- **Tükenmede fisyon verimi sabit** (termal 0.0253 eV, hızlı 500 keV). OpenMC'nin
  spektrum ağırlıklı `average` modu kullanılmıyor.
- **Tükenme yalnızca özdeğer modunda.** Sabit kaynaklı aktivasyon hesabı yok.
- **Tükenme kaldığı yerden sürdürülemiyor** (`prev_results`); her koşu baştan.
- **Kontrol elemanları yanmıyor.** B4C çubuk ve tamburlar yanabilir malzeme
  sayılmıyor (`ek_malzemeler` ile JSON'dan eklenebilir).
- `MPI` yok — OpenMC bu makinede OpenMP ile tek düğümde çalışıyor (24 çekirdek).

## Ortam

`openmc-env` conda ortamı gerekir:

```
openmc 0.16.0 (DAGMC, MPI yok)   PySide6 6.11.2   matplotlib   pandas   h5py
OPENMC_CROSS_SECTIONS = ~/nucdata/endfb-viii.0-hdf5/cross_sections.xml
OPENMC_CHAIN_FILE     = ~/nucdata/chain/chain_endfb80_thermal.xml   (~/.bashrc)
```

Tükenme zincirleri `~/nucdata/chain/` altında; kaynak URL'leri ve sha256'lar
`~/nucdata/chain/KAYNAK.txt`'te. Uygulama `OPENMC_CHAIN_FILE`'a güvenmez, zinciri
her model için kendisi seçer; değişken yalnızca terminal/betik kullanımı içindir.
