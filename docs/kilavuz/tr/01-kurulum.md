<a id="kurulum"></a>
# 1. Kurulum ve ilk açılış

Bu bölüm programı sıfırdan kurmayı, nükleer veriyi indirmeyi ve ilk açılıştaki **Başlangıç**
ekranını anlatır. Adımların tam metni depodaki [KURULUM.md](../../../KURULUM.md) dosyasındadır;
burada her adımın **neden** gerektiği ve nasıl doğrulanacağı da yazılıdır.

## 1.1 Gerekenler

| | |
|---|---|
| İşletim sistemi | Linux (Ubuntu 22.04 / 24.04'te geliştirildi). Windows'ta **WSL2** (Ubuntu) ile; grafik pencere için Windows 11'in WSLg desteği yeterli. macOS denenmedi. |
| Disk | ~20 GB boş alan (nükleer veri açılınca ~13 GB) |
| Bellek | 8 GB yeterli; 17×17 demet ve 3B modeller için 16 GB rahat |
| İnternet | Yalnız veri indirmesi için (tek sefer, birkaç GB) |

Program bir **conda ortamında** çalışır: OpenMC PyPI'da yayımlanmaz, conda-forge'dan gelir.

## 1.2 Kurulum adımları

**1. Conda (Miniforge).** Zaten conda/mamba varsa atlayın.

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh        # soruları varsayılanla geçin, terminali kapatıp açın
```

**2. Ortam.** Depo klasöründe:

```bash
conda env create -f environment.yml    # OpenMC 0.16.0 + PySide6 + matplotlib ... (birkaç dakika)
conda activate openmc-env
pip install -e . --no-deps             # komutlar: openmc-arayuz, openmc-arayuz-kosu
```

`--no-deps` bilerek verilir: bütün bağımlılıklar `environment.yml` ile kuruldu; pip'in
OpenMC'yi PyPI'da araması kurulumu bozar.

**3. Nükleer veri** (aşağıda [1.3](#nukleer-veri)):

```bash
./veri_indir.sh --bashrc
```

Bitince **yeni bir terminal açın** (ya da `source ~/.bashrc`) ve `conda activate openmc-env`.

**4. Doğrulama ve başlatma:**

```bash
pytest -m hizli -n auto -q          # hızlı test süiti; sonunda "passed", 0 failed
./calistir.sh                       # arayüz açılır (ya da: openmc-arayuz)
./calistir.sh ornekler/pwr_17x17.json   # doğrudan bir örnekle (kopya olarak açılır)
```

`calistir.sh` açmadan önce ortamı denetler: `openmc` komutu PATH'te mi, `OPENMC_CROSS_SECTIONS`
ayarlı mı, grafik oturum var mı, tükenme zinciri tam mı. Bir eksik varsa ne yapacağınızı yazar
(bkz. [9.4 Kurulum ve ortam sorunları](09-sorun-giderme.md#kurulum-sorunlari)).

<a id="nukleer-veri"></a>
## 1.3 Nükleer veri ve tükenme zinciri

Monte Carlo hesabı nüklidlerin **tesir kesitlerini** bir kütüphaneden okur. Bu program
**ENDF/B-VIII.0** kütüphanesinin OpenMC HDF5 sürümüyle doğrulanmıştır (bütün ölçüm çıpaları ve
kriter sonuçları bu kütüphaneyle alındı). Veri programla gelmez (açılınca ~13 GB); iki yoldan
biriyle kurulur: arayüzdeki **Veri** sayfası ya da `veri_indir.sh`. İkisi **aynı kodu**
(`cekirdek/veri_indir.py`) kullanır.

| Veri | Boyut | Ne için |
|---|---|---|
| ENDF/B-VIII.0 HDF5 tesir kesitleri (`endfb-viii.0-hdf5/cross_sections.xml`) | arşiv 3.4 GB, açılınca ~13.7 GB | her hesap |
| Tükenme zincirleri: ENDF/B-VIII.0 termal + hızlı (3820 nüklid) | ~27 MB her biri | tükenme |
| CASL termal + hızlı (228 nüklid) | ~1 MB her biri | hızlı ön tükenme incelemesi |

### Veri ve kütüphaneler sayfası

Kenar çubuğunun en altındaki **Kurulum › Veri** sayfası. Program veri bulamadan açılırsa bu
sayfa **kendiliğinden** açılır, üstte "Başlamadan önce: nükleer veri" bandı görünür; veri
seçilince bant kalkar, **Başlangıç ekranına geç** ile model kurmaya geçersiniz. Veri yokken
doğrulama şeridinde `Veri kütüphanesi · nükleer veri kütüphanesi bulunamadı` hatası durur,
**Çalıştır kapalıdır**; şeritteki **Bulguya git** bu sayfaya getirir.

- **Gereksinimler** — OpenMC ikilisi ve sürümü (`openmc --version`), OpenMC Python API (ikiliyle
  aynı sürüm mü), HDF5 (h5py), tesir kesiti kütüphanesi ve tükenme zinciri tek tabloda: ✓ tamam,
  ! uyarı, ✗ eksik; eksikte ne yapılacağı yazar.
- **Klasör seç** — bilgisayarınızda zaten bir kütüphane varsa `cross_sections.xml` içeren klasörü
  (ya da bir üstünü) seçin. **Denetle ve kullan** XML'i okur; nötron nüklidi, S(α,β) tablosu ve
  foton elementi sayısını, örnek sıcaklık aralıklarını (U235, H1, su S(α,β)) ve dosyası olmayan
  kayıtları gösterir. Eksik dosya varsa (yarım açılmış arşiv) klasör **kabul edilmez**. Tükenme
  zinciri ayrıca seçilir; termal zincirin yanındaki hızlı ve CASL zincirleri aynı klasörden okunur.
- **Kütüphane indir** — openmc.org resmî listesindeki 12 kütüphane (ENDF/B-VII.1, ENDF/B-VIII.0,
  ENDF/B-VIII.1, JEFF-3.3, JEFF-4.0, JENDL-5, LANL ve NEA sürümleri, FENDL-3.2): arşiv boyutu,
  sıcaklıklar, içerik ve kullanım notu, değerlendirme sayfası bağlantısı. Zincir kutuları
  (ENDF/B-VIII.0 termal/hızlı, CASL termal/hızlı), hedef klasör (varsayılan `~/nucdata`), gereken
  ve boş disk alanı. İndirme **arka planda** sürer (arayüz donmaz); **İptal** edilirse yarım dosya
  kalır ve düğme **Sürdür** olur — kaldığı yerden devam eder.

Seçim `~/.config/openmc_arayuz/veri.json` dosyasına yazılır ve **kalıcıdır**; ortam değişkeni
gerekmez. Koşu, tükenme ve önizleme alt süreçleri aynı yolu alır.

**Hangi veri kullanılır (sıra).** (1) `OPENMC_CROSS_SECTIONS` ortam değişkeni ayarlıysa **o**
(dosya olmasa bile; sayfa bunu not olarak yazar ve seçiminiz değişken kaldırılana dek
kullanılmaz), (2) Veri sayfasındaki seçim, (3) `~/nucdata/*/cross_sections.xml` ya da
`~/.local/share/openmc_arayuz/nucdata/*/cross_sections.xml` — birden çok aday varsa
`endfb-viii.0-hdf5` seçilir; o yoksa program **kendisi seçmez**, sayfa ve doğrulama şeridi
"birden çok kütüphane bulundu" der ve seçmenizi ister. Otomatik bulunan aday kullanılırken
şeritte bir **bilgi** bulgusu ve raporda "otomatik bulunan aday" yazar. ENDF/B-VIII.0 zinciri
başka bir kütüphaneyle (ör. JENDL-5) birlikte seçilirse Gereksinimler'de uyarı çıkar. Zincir için aynı sıra
`OPENMC_CHAIN_FILE` ile başlar; seçim yoksa kütüphanenin yanındaki `chain/` klasörüne bakılır.
Rapor, deney kapsülü ve doğrulama bu tek çözümleyiciden (`cekirdek/veri_yolu.py`) okur.

**Güvenlik ve bütünlük.** Yalnız `https` ve katalogdaki alan adları (`anl.box.com`,
`anl.app.box.com`, `public.boxcloud.com`); her yönlendirme de denetlenir. Bayt sayısı katalogla,
sha256 (biliniyorsa) karşılaştırılır; dosya önce `.part` olarak yazılır, doğrulanınca yerine
taşınır. **openmc.org sha256 yayımlamaz:** zincirlerin sha256'sı bu projede bir kez ölçülüp
katalogda tutulur; kütüphanelerde yalnız bayt sayısı denetlenir ve hesaplanan sha256 kurulan
klasördeki `KAYNAK.json` makbuzuna yazılır (`sha256_dogrulandi: false`); sayfa ve
`veri_indir.sh` bunu "sha256 yok: yalnız boyut denetlendi" etiketiyle söyler. Arşiv açılırken bağlantı (symlink/hardlink), mutlak
yol ve `..` içeren üyeler reddedilir; açılan boyut ve üye sayısı sınırlıdır; diskte yer azalırsa
açma durur; bozuk arşiv silinir (yeniden indirilir). Hedef olarak sistem dizinleri (`/usr`,
`/etc` …), ev dizininin kendisi, `~/.ssh`, `~/.gnupg` ve başka kullanıcıların yazabildiği
klasörler seçilemez; yarım dosyalar yalnız sizin okuyabildiğiniz `.indirilen/` klasöründe durur.
Komut satırından bir proje dosyasıyla açılırken veri yoksa sayfa açılmaz, yalnız bildirim çıkar.

Katalog `cekirdek/veri_katalogu.json`'dadır: kaynak `https://openmc.org/data` (erişim tarihi,
kaynak dosyanın sha256'sı ve ölçüm yöntemi katalogda yazılı). Lisans: openmc.org sayfası
kütüphanelere ayrı bir lisans yazmaz; kaynak değerlendirmenin (ENDF/B, JEFF, JENDL …) dağıtım
koşulları geçerlidir — kullanmadan önce değerlendirme sayfasına bakın.

### Terminalden: `veri_indir.sh`

```bash
./veri_indir.sh --liste                                # katalog
./veri_indir.sh                                        # ENDF/B-VIII.0 + 4 zincir -> ~/nucdata
./veri_indir.sh --hedef /baska/disk/nucdata --bashrc   # başka diske
./veri_indir.sh --kutuphane jendl-5                    # başka kütüphane
./veri_indir.sh --yalniz-zincir                        # yalnız zincirler (~57 MB)
```

Betik bitince seçimi uygulama ayarına yazar. `--bashrc` ayrıca iki ortam değişkenini
`~/.bashrc`'ye ekler (yalnız terminalden `openmc` kullanacaksanız gerekir):

```
OPENMC_CROSS_SECTIONS = ~/nucdata/endfb-viii.0-hdf5/cross_sections.xml
OPENMC_CHAIN_FILE     = ~/nucdata/chain/chain_endfb80_thermal.xml
```

- Arayüz zinciri her model için **kendisi seçer** (termal ya da hızlı; bkz.
  [4.9 Tükenme](04i-tukenme.md#tukenme)); `OPENMC_CHAIN_FILE` yalnız zincirlerin klasörünü belirler.

**Yarım indirme kabul edilmez.** (Bu projedeki ilk indirme %13'te sessizce kesilmişti; dosyanın
adı ve yeri doğruydu, bakan biri sorunu göremezdi.) İndirme kesilirse yeniden başlatın; kaldığı
yerden sürer. Arayüz de yarım bir zinciri doğrulama panelinde **hata** olarak gösterir ve
tükenmeyi başlatmaz.

> **WMP (çok kutuplu) veri bilerek indirilmez.** openmc.org'daki 1.7 GB'lık dosya ENDF/B-VII.1
> kütüphanesinin tamamıdır; VIII.0 kesitleriyle karıştırmak iki farklı değerlendirmeyi tek modelde
> birleştirmek olurdu.

**Sıcaklık aralığı.** Nötron verisi 250–2500 K aralığındadır, ama örneğin **su için S(α,β)
yalnızca 284–800 K**. Bu aralığın dışındaki bir malzeme sıcaklığı ya da sıcaklık taraması
doğrulamada uyarı/hata verir (bkz. [6.5 Bilinen tuzaklar](06-sonuclar.md#tuzaklar)).

<a id="baslangic"></a>
## 1.4 İlk açılış: Başlangıç ekranı

Program model olmadan açıldığında **"Ne modellemek istiyorsunuz?"** ekranı gelir. Hiçbir örnek
kendiliğinden yüklenmez; üç yoldan birini seçersiniz:

| Yol | Nerede | Ne kurar |
|---|---|---|
| **Sıfırdan** | ilk kart: kor türü seçici + **Sıfırdan başla** | Gerçekten boş bir model: malzeme, parça, demet, geometri yok; yalnız kor türü seçili. |
| **Şablondan** | tür kartlarındaki **Şablondan** | O türün çalışan, sade modeli (eskiden "Boş başla"). |
| **Örnekten** | tür kartlarındaki **Örnekten** ya da alttaki galeri | Hazır bir örneğin kaydedilmemiş kopyası. |

![Başlangıç ekranı: model türü kartları, son kullanılanlar ve örnek galerisi](../resimler/tr/baslangic.png)

**Sıfırdan.** Kor türlerinden birini seçin (yakıt çubuğu, tek yakıt demeti, kare ya da altıgen
haritalı tam kor, MTR plaka elemanı) ve **Sıfırdan başla**'ya basın. Editör **Malzemeler**
sayfasında açılır ve doğrulama şeridinin üstünde bir **aşama rehberi** görünür ("adım" bu programda ızgara adımı, *pitch* demektir):

| Aşama | Sayfa | Tamam sayılır |
|---|---|---|
| 1. **Malzeme ekle** | Malzemeler | en az bir malzeme var (kütüphaneden yakıt, zarf, soğutucu) |
| 2. **Parça ekle** | Parçalar | en az bir çubuk (plaka türünde bir plaka elemanı) var |
| 3. **Demet kur** (yalnız demet ve tam kor türlerinde) | Demet | en az bir demet var |
| 4. **Geometriyi kur** | Geometri | hücrenin dolgusu seçili / kor haritası dolu |

Her aşamaya tıklamak ilgili sayfayı açar; tamamlanan aşama ✓ ile, sıradaki vurguyla işaretlidir.
Pin hücrede ilk yakıt çubuğu eklenince hücreye kendiliğinden yerleşir, yani geometri aşaması da
tamamlanır. Bütün aşamalar bitince rehber gizlenir.

Model kurulurken doğrulama bulguları **hata (kırmızı) değil "Eksik aşama" (bilgi tonu)** olarak
gösterilir: boş bir modelde "çubuk seçilmemiş" bir hata değil, henüz tamamlanmamış bir aşamadır.
Şerit "Model kuruluyor: 1/3 aşama" der; **Bulguya git** sıradaki aşamanın sayfasını açar. Bu sırada
**Çalıştır kapalıdır** ve nedeni düğmenin ipucunda yazar ("Model henüz kurulmadı: 2 aşama eksik.
Sıradaki aşama: …"). Aşamalar tamamlanınca doğrulama olağan haline döner; kalan gerçek hatalar
yine kırmızıdır.

**Model türü kartları.** Her kartın bir açıklaması ve iki eylemi vardır:

| Kart | Şablondan | Örnekten | Kurulan model (kor türü) |
|---|---|---|---|
| **Yakıt çubuğu (pin hücre)** | var | `ornekler/pwr_pinhucre.json` | `tek_cubuk` |
| **Yakıt demeti — kare** | var | `ornekler/pwr_17x17.json` | `tek_demet` (kare) |
| **Yakıt demeti — altıgen** | var | `ornekler/sfr_altigen.json` | `tek_demet` (altıgen) |
| **Tam kor (kare harita)** | var | — | `kare_kafes` |
| **Tam kor — altıgen** | var | — | `altigen_kafes` |
| **MTR plaka elemanı** | var | `ornekler/mtr_plaka.json` | `tek_plaka` |
| **Tamburlu kompakt kor** | var | `ornekler/tamburlu_kor.json` | `tamburlu` |
| **Zırhlama (sabit kaynak)** | — | `ornekler/zirh_kure.json` | `kuresel` |
| **Dosyadan aç** | **Aç…** (Ctrl+O): kayıtlı bir model (`.json`) ya da OpenMC XML klasörü | | |

- **Şablondan** çalışır durumda, sade bir model kurar: malzemeler, parçalar ve geometri hazırdır;
  hesap ayarları "Normal" hassasiyettedir. Hemen **F9** ile koşabilirsiniz.
- **Örnekten** hazır bir örneğin **kaydedilmemiş kopyasını** açar. `ornekler/*.json` test
  referansıdır; üzerine yazılmaz. Kendi dosyanız için **Dosya → Farklı kaydet**.
- Küresel düzenek (zırhlama, Godiva tipi kriterler) şablondan ya da sıfırdan başlatılamaz: kabukları yalnız JSON'dan
  düzenlenir ([4.4 Geometri](04d-geometri.md#geometri)).

**Son kullanılanlar.** Kaydettiğiniz ya da açtığınız modeller bu şeritte görünür (dosya adı,
dizin, son değişiklik zamanı).

**Açılışta bu ekranı göster.** Ekranın altındaki kutu (varsayılan: işaretli) ayarlara yazılır.
İşaret kaldırılırsa program bir sonraki açılışta **son kullanılan projeyle** açılır (proje son
kullanılanlar listesinde kalır); dosya bulunamazsa yine başlangıç ekranı gelir.

**Örnek galerisi.** Depodaki bütün örnekler; üstte arama kutusu (**Örneklerde ara…**), seviye
seçici (giriş / orta / ileri) ve kategori düğmeleri (**PWR**, **BWR**, **VVER**, **SFR**,
**Araştırma**, **Kriter**, **Zırh**). Bir karta tıklamak örneği kopya olarak açar. Örneklerin
listesi, kaynakları ve ölçülen değerleri: [ORNEKLER.md](../../ORNEKLER.md).

Bir model açıkken başlangıç ekranına **Dosya → Yeni…** ile dönülür; **Açık modele dön** (Esc)
modele geri getirir.

## 1.5 Kurulumu doğrulamak: ilk koşu

Başlangıç ekranında **Yakıt çubuğu (pin hücre) → Şablondan**, sonra **F9** (Çalıştır). Yarım
dakika içinde sonuç kartında **k∞ ≈ 1.323 ± 0.001** görmelisiniz (UO₂ %3.0, sıcak çalışma
koşulu, "Normal" hassasiyet; ölçülen 1.3227 ± 0.0008). Son hanede küçük farklar istatistiktir;
±0.003'ten büyük bir fark kurulum sorununa (yanlış kütüphane, eksik S(α,β) verisi) işaret eder.

Daha kapsamlı ilk çalışma için: [2. 15 dakikada ilk hesap](02-ilk-hesap.md#ilk-hesap).

## 1.6 Log dosyası ve ayarlar

- Uygulama logu: `~/.local/state/openmc_arayuz/openmc_arayuz.log` (`XDG_STATE_HOME` ayarlıysa
  onun altında). Hata bildirirken bu dosyayı ekleyin.
- Arayüz ayarları (tema, dil, son kullanılanlar): `~/.config/openmc_arayuz/`.
- Dil: **Görünüm → Dil** (Türkçe / İngilizce) ya da `OPENMC_ARAYUZ_DIL=en` ortam değişkeni.
