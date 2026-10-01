<a id="terminal"></a>
# 8. Terminal ve HPC kullanımı

Uygulamanın çekirdek katmanı (`cekirdek/`) arayüze bağlı değildir: bir modeli doğrulamak,
koşmak, rapor üretmek, uygunluk denetimi yapmak ve bir koşuyu yeniden üretmek terminalden
de yapılır. Bu yol uzun koşular, sunucuda ya da hesaplama kümesinde çalışma, ders
otomasyonu ve sürekli tümleştirme (CI) içindir. Terminal, arayüzle **aynı** doğrulama
kapısını, aynı kurucuyu ve aynı sonuç okuyucusunu kullanır; iki yoldan alınan sonuçlar
aynıdır.

Komutlar `conda activate openmc-env` ile etkinleştirilmiş ortamda çalışır. Paket
`pip install -e . --no-deps` ile kurulduysa (bkz. [Kurulum](01-kurulum.md#kurulum))
`openmc-arayuz-kosu` komutu vardır; kurulmadıysa her komutun `python3 -m cekirdek.kosucu`
eşdeğeri kullanılır (depo kökünden). Her komut `--help` ile kendi kullanımını yazar.

## 8.1 Bir modeli koşmak

```bash
openmc-arayuz-kosu ornekler/pwr_pinhucre.json                    # doğrula, koş, sonucu yaz
openmc-arayuz-kosu ornekler/pwr_17x17.json --dizin /tmp/deneme -s 24
openmc-arayuz-kosu ornekler/mtr_plaka.json --sadece-dogrula      # yalnız doğrulama
openmc-arayuz-kosu ornekler/pwr_17x17.json --betik model.py      # Python betiği de üret
python3 -m cekirdek.kosucu ornekler/pwr_pinhucre.json            # kurulumsuz eşdeğeri
```

| Seçenek | Anlamı |
|---|---|
| `<spec.json>` | Modelin JSON dosyası (arayüzün kaydettiği dosya ya da `ornekler/` altındaki bir örnek). İlk argümandır. |
| `--dizin D` | Koşu dizini. Verilmezse spec dosyasının yanındaki `calistirma.dizin` (varsayılan `kosu`). |
| `-s N`, `--is-parcacigi N` | OpenMP iş parçacığı sayısı (`openmc -s N`). Verilmezse spec'teki `calistirma.is_parcacigi` (varsayılan 8). |
| `--sadece-dogrula` | Doğrulamayı yapar, bulguları yazar, koşmaz. `--betik` ile birlikte verilirse betik yine yazılır. |
| `--betik model.py` | Modeli tek başına çalışan bir OpenMC Python betiği olarak da yazar (bkz. 8.6). |

Çıktı üç adımdır: **[1/3] Doğrulama** (bulgular; hata varsa koşu başlamaz), **[2/3] Koşu**
(terminal bir TTY ise her 10 çevrimde tek satır güncellenen `k = … ± …`), **[3/3] Sonuçlar**
(k-eff ± 1σ, kritiklik yorumu, çevrim/pasif çevrim/parçacık sayısı, Shannon entropisi
yakınsaması, varsa β_eff ve Λ, güç dağılımı ve tepe faktörleri). Sabit kaynak hesabında k-eff
yoktur; komut kaynağı, şiddeti ve tally birimleri hakkındaki notu yazar (OpenMC şiddeti
kendisi uygular; tekrar çarpmayın). Sonuçları nasıl okuyacağınız: [6. Sonuçları
yorumlamak](06-sonuclar.md#sonuclar).

Çıkış kodu: `0` başarılı (ya da `--sadece-dogrula` ile hatasız doğrulama), `1` doğrulama
hatası ya da koşu başarısız, `2` bilinmeyen seçenek.

> **Örnekleri yerinde koşmayın.** `--dizin` verilmezse koşu dizini spec dosyasının yanına,
> yani `ornekler/kosu` altına yazılır. `ornekler/*.json` test referansıdır; deneme koşuları
> için `--dizin /tmp/...` ya da kendi proje dizininizi kullanın. Arayüzde kaydedilmemiş bir
> modelin koşusu ise `~/openmc_kosular` altına gider.

### Koşu dizininde ne var

| Dosya | İçerik |
|---|---|
| `model.xml` | OpenMC'nin okuduğu model (geometri, malzemeler, ayarlar, tally'ler) |
| `spec.json` | Koşunun modeli (rapor ve uygunluk denetimi buradan okur) |
| `kapsul.json` | Tekrarlanabilirlik kapsülü: spec karması, uygulama sürümü ve git commit'i, OpenMC sürümü, kütüphane ve zincir özetleri, tohum, iş parçacığı, platform, ortam karması |
| `statepoint.*.h5`, `summary.h5` | OpenMC sonuç dosyaları |
| `kosu.log` | OpenMC'nin tam ekran çıktısı (kayıp parçacık uyarıları dahil) |

Tükenme koşusunun dizini ayrıdır (`<dizin>_tukenme`, ör. `kosu_tukenme`); orada
`depletion_results.h5` ve sonucun hangi modele ait olduğunu gösteren `tukenme_spec.json`
bulunur.

## 8.2 Rapor üretmek

```bash
openmc-arayuz-kosu rapor kosu/                         # kosu/rapor.pdf
openmc-arayuz-kosu rapor kosu/ -o rapor.html           # biçim uzantıdan: .pdf | .html
openmc-arayuz-kosu rapor kosu_tukenme/ --spec model.json
```

`-o` (ya da `--cikti`) verilmezse rapor koşu dizinine `rapor.pdf` olarak yazılır. Model koşu
dizinindeki `spec.json`'dan (yoksa `tukenme_spec.json`'dan) okunur; ikisi de yoksa `--spec`
ile verilir. Rapor, arayüzdeki **Dosya → Rapor oluştur… (Ctrl+R)** ile aynıdır ve uygunluk
ekini içerir (bkz. [rapor dersi](05-dersler.md#ders-rapor)). Çıkış kodu: `0` tamam, `1` rapor
oluşturulamadı, `2` kullanım hatası (uzantı `.pdf`/`.html` değil, spec bulunamadı).

## 8.3 Uygunluk denetimi

```bash
openmc-arayuz-kosu uygunluk kosu/                      # profiller spec'teki seçimden (yoksa A,D)
openmc-arayuz-kosu uygunluk kosu/ --profil A,B,C,D
openmc-arayuz-kosu uygunluk kosu/ --profil A,D --siki  # değerlendirilemeyen kural da başarısızlık
```

Her bulgu bir satırdır: seviye (HATA / UYARI / BİLGİ), kural kimliği (K1 … K16), profil,
durum (kontrolü geçti / KONTROLÜ GEÇMEDİ / uygulanamadı / not) ve mesaj; geçmeyen kuralların
önerisi altına yazılır. Sonda sayım, seçilen profillerde USL notu ve "bu denetim sertifika
değildir" çerçevesi yazılır. Profiller ve kuralların anlamı: [7. Uygunluk denetimi ve
V&V](07-uygunluk.md#uygunluk-denetimi), tek tek kurallar ve çözümleri:
[Uygunluk kuralları](09-sorun-giderme.md#uygunluk-kurallari).

| Çıkış kodu | Anlamı |
|---|---|
| `0` | hata seviyesinde bulgu yok |
| `1` | en az bir hata bulgusu var ya da denetim yapılamadı (koşu dizini okunamadı) |
| `2` | kullanım hatası (bilinmeyen seçenek, eksik koşu dizini, bilinmeyen profil) |
| `3` | `--siki` verildi ve değerlendirilemeyen ("uygulanamadı") kural var |

`--siki` olmadan değerlendirilemeyen kurallar başarısızlık sayılmaz; sayımda görünür. Ders
otomasyonu ve CI için çıkış kodunu kullanın; örneğin bir ödev betiğinde
`openmc-arayuz-kosu uygunluk kosu/ --profil A,D || exit 1`.

## 8.4 Koşuyu yeniden üretmek

```bash
openmc-arayuz-kosu yeniden kosu/ --kuru            # koşmadan: plan ve ortam farkı
openmc-arayuz-kosu yeniden kosu/                   # aynı spec, tohum ve iş parçacığıyla koşar
openmc-arayuz-kosu yeniden kosu/ --hedef /tmp/tekrar -s 8
```

Komut önce koşu dizinindeki `spec.json`'un `kapsul.json`'daki karmayla aynı olduğunu
doğrular (değişmişse reddeder), sonra bugünkü ortamla kapsül arasındaki farkları alan alan
yazar (uygulama sürümü, OpenMC, kütüphane, zincir, ortam karması…). `--kuru` verilmezse aynı
spec, tohum ve iş parçacığı sayısıyla **ayrı** bir dizinde koşar (varsayılan
`<koşu_dizini>_yeniden`; `--hedef` ile değişir; kaynak koşu dizinine yazmaz) ve k-eff farkını
raporlar. Aynı makinede ölçülen fark 10⁻¹⁶–10⁻¹⁵ düzeyindedir (OpenMP toplama sırası); araç bu
düzeyi "yuvarlama düzeyinde aynı" diye yazar, daha büyük farkı σ cinsinden verir. Kapsül bir
**kanıttır, garanti değildir**: farklı makine, kütüphane ya da OpenMC sürümünde fark beklenir ve
listelenir (bkz. `docs/YAZILIM_KALITE.md` §3, [yazılım kalite kanıtı](../../YAZILIM_KALITE.md)).
`kapsul.json`'dan önceki eski koşu dizinleri yeniden üretilemez.

## 8.5 Tükenme terminalden

```bash
python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json --hazirla        # koşmadan bilgi
python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 16 --dizin /tmp/yanma
```

`--hazirla` koşmadan seçilen zinciri ve gerekçesini, fisyon verimi enerjisini, güç
yoğunluğunu, adımları ve transport sayısını, her yanabilir malzemenin analitik hacmini ve
ağır metal kütlesini yazar; uzun bir koşudan önce bu çıktıyı okuyun (ayrıntı:
[4.9 Tükenme](04i-tukenme.md#tukenme)). Koşu sonunda gün / MWd/kg / k-eff tablosu ve
`depletion_results.h5` yolu yazılır. `--dizin` verilmezse dizin spec'in yanındaki
`<calistirma.dizin>_tukenme`'dir (yine örnekleri yerinde koşmayın). Tükenmeyi arayüz başlatsa
da terminal başlatsa da zinciri uygulama kendisi seçer; `OPENMC_CHAIN_FILE` yalnız dışa
aktarılan betik ve OpenMC'nin kendi araçları içindir.

## 8.6 Python betiği ve OpenMC XML olarak dışa aktarma

Arayüz bir çıkmaz sokak değildir. **Dosya → Python betiği olarak dışa aktar… (Ctrl+E)** ya da
`--betik model.py` modeli okunabilir, tek başına çalışan bir OpenMC betiğine çevirir:

- Betik `openmc_arayuz`'a **bağımlı değildir**; yalnız `openmc` ve `matplotlib` ister.
- Değişken adları türe göre önekli ve benzersizdir (`m_uo2`, `c_yakit_cubugu`,
  `d_demet_17x17`); geometri kurucuyla aynı gezintiden üretilir ve testte kurucuyla aynı
  XML'i verdiği denetlenir.
- `python3 model.py` önce geometriyi çizer (`geometri_xy.png`); `model.run(...)` satırı
  **yorum içindedir** — çizim doğruysa yorumu kaldırın ([önce çiz, sonra
  çalıştır](06-sonuclar.md#once-ciz)). Tükenme açıksa `tukenme_kos()` işlevi de yazılır.
- Dönüşüm **tek yönlüdür**: betik spec'e geri çevrilemez.

**Dosya → OpenMC XML olarak dışa aktar…** seçilen dizine tek bir `model.xml` yazar; OpenMC
onu doğrudan `openmc` komutuyla koşar.

<a id="hpc"></a>
## 8.7 Hesaplama kümesi (HPC)

Bu kurulumdaki OpenMC (conda-forge, 0.16.0) **MPI'sız** derlenmiştir; tek bir düğümde OpenMP
iş parçacıklarıyla çalışır. Kümede iki yol vardır:

1. **Uygulamanın kendisiyle, tek düğümde.** Ortamı (`environment.yml`) ve nükleer veriyi
   (`./veri_indir.sh --hedef …`) düğümün görebildiği bir diske kurun, işi `openmc-arayuz-kosu`
   ile verin ve iş parçacığı sayısını düğümün çekirdek sayısına eşitleyin (`-s`). Arayüz
   gerekmez; grafik oturumu olmayan düğümde komutlar sorunsuz çalışır. Örnek bir iş betiği
   (SLURM; kümenizin kuralına göre uyarlayın):

   ```bash
   #!/bin/bash
   #SBATCH --job-name=pwr17
   #SBATCH --nodes=1
   #SBATCH --cpus-per-task=32
   #SBATCH --time=02:00:00
   source "$(conda info --base)/etc/profile.d/conda.sh"
   conda activate openmc-env
   export OPENMC_CROSS_SECTIONS=$HOME/nucdata/endfb-viii.0-hdf5/cross_sections.xml
   openmc-arayuz-kosu proje/pwr_17x17.json --dizin "$SCRATCH/pwr17" -s "$SLURM_CPUS_PER_TASK"
   openmc-arayuz-kosu uygunluk "$SCRATCH/pwr17" --profil A,D
   ```

2. **Kümenin kendi OpenMC'siyle (MPI dahil).** Modeli betik ya da `model.xml` olarak dışa
   aktarın ve kümede kurulu (MPI'lı) OpenMC ile koşun, ör. `mpirun -n 4 openmc -s 16`
   (`model.xml`'in bulunduğu dizinde). Bu durumda doğrulama kapısı, kapsül ve uygunluk
   denetimi koşu sırasında **çalışmaz**: modeli önce burada `--sadece-dogrula` ile
   doğrulayın; koşudan sonra statepoint dosyalarını `spec.json` ile aynı dizine koyarak
   `openmc-arayuz-kosu uygunluk` ve `openmc-arayuz-kosu rapor` ile okuyabilirsiniz. Kümenin
   OpenMC sürümü ve tesir kesiti kütüphanesi farklıysa sonuç bu kılavuzdaki ölçümlerle
   birebir karşılaştırılamaz (kütüphane ve sürüm raporda yazar; bkz. K4).

İş parçacığı sayısını `-s` ile verin. `OMP_NUM_THREADS` ortam değişkeni OpenMP'nin genel
ayarıdır; `openmc-arayuz-kosu` OpenMC'yi açıkça `-s N` ile başlatır, tükenme ise
`-s` verildiyse `OMP_NUM_THREADS`'i kendisi ayarlar. Bellek: 17×17 demet ve 3B modeller için
düğüm başına 16 GB rahattır; tükenmede zincirdeki 3820 nüklid yakıta eklendiği için bellek
ve süre artar (ölçümler: [4.9 Tükenme](04i-tukenme.md#tukenme)).

## 8.8 Ortam değişkenleri

| Değişken | Kim okur | Anlamı |
|---|---|---|
| `OPENMC_CROSS_SECTIONS` | OpenMC, doğrulama | `cross_sections.xml` yolu. Yoksa doğrulama hata verir ve koşu başlamaz. `./veri_indir.sh --bashrc` ayarlar. |
| `OPENMC_CHAIN_FILE` | yalnız dışa aktarılan betik ve OpenMC araçları | Tükenme zinciri. Uygulama zinciri her model için kendisi seçer, bu değişkene güvenmez. |
| `OPENMC_ARAYUZ_DIL` | arayüz, çekirdek mesajları | `tr` ya da `en`. Kayıtlı ayarın ve sistem dilinin önüne geçer. |
| `OPENMC_ARAYUZ_KILAVUZ` | uygulama içi kılavuz | Kılavuz kaynaklarının dizini (varsayılan depo içindeki `docs/kilavuz`). |
| `OPENMC_ARAYUZ_LOCALE` | çeviri kataloğu | `locale` dizini (varsayılan depo içindeki `locale`). |
| `OMP_NUM_THREADS` | OpenMP | Genel iş parçacığı sayısı (tükenme `-s` ile bunu ayarlar). |
| `XDG_STATE_HOME` | uygulama logu | Log dizininin tabanı (varsayılan `~/.local/state`). |
| `QT_QPA_PLATFORM` | Qt | `offscreen`: grafik oturum olmadan Qt (ekran görüntüsü betikleri, testler). |

## 8.9 Log dosyası

Uygulama logu `~/.local/state/openmc_arayuz/openmc_arayuz.log` dosyasına yazılır
(`XDG_STATE_HOME` ayarlıysa onun altına; ~1 MB × 5 yedek döner). Hata bildirirken bu dosyayı
ve ilgili koşu dizinindeki `kosu.log`'u ekleyin. Log dizini yazılamazsa uygulama çökmez,
durum bir kez stderr'e yazılır. Sık karşılaşılan sorunlar: [9. Sorun
giderme](09-sorun-giderme.md#sorun-giderme).
