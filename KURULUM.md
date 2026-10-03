# Kurulum — OpenMC Reaktör Kuru Arayüzü

<!-- CI rozeti (depo herkese açılınca ya da oturum açıkken görünür):
[![test](https://github.com/DurCax/openmc-arayuz/actions/workflows/test.yml/badge.svg?branch=ana)](https://github.com/DurCax/openmc-arayuz/actions/workflows/test.yml)
-->

Bu klasör, OpenMC ile reaktör modeli (yakıt çubuğundan tam kora, zırhlamadan
tükenmeye) kurup çalıştırmayı sağlayan bir masaüstü uygulamasıdır. Model
arayüzde kurulur, geometri çalıştırmadan önce görülür, hesap aynı yerden
başlatılır ve sonuçlar orada okunur. Ayrıntılar `README.md`'de.

Kurulum dört adımdır; en uzunu nükleer veri indirmesidir (bir kez).

## Gerekenler

| | |
|---|---|
| İşletim sistemi | Linux (Ubuntu 22.04 / 24.04'te geliştirildi). Windows'ta **WSL2** (Ubuntu) ile çalışır; grafik pencere için Windows 11'in WSLg desteği yeterli. macOS'ta conda-forge OpenMC paketi var ama denenmedi. |
| Disk | ~20 GB boş alan (nükleer veri açılınca ~13 GB) |
| Bellek | 8 GB yeterli; 17×17 demet ve 3B modeller için 16 GB rahat |
| İnternet | Veri indirmesi için (tek sefer, birkaç GB) |

## Hızlı kurulum (tek dosya, conda gerekmez)

Tek bir kendiliğinden açılan kurulum dosyası Python'u, OpenMC 0.16.0'ı, PySide6'yı ve uygulamayı
içerir (yaklaşık 410 MB; kurulunca 1,7 GB). Çevrimdışı çalışır, kök yetkisi istemez ve **nükleer veri
içermez** (uygulamanın *Veri* sayfası indirir). Gereken: Linux x86-64, glibc >= 2.28
(Ubuntu 20.04/22.04/24.04, Fedora 29+, Debian 10+).

```bash
bash openmc-arayuz-3.0.0-Linux-x86_64.sh            # klasörü sorar; varsayılan ~/openmc-arayuz
bash openmc-arayuz-3.0.0-Linux-x86_64.sh -b -p ~/openmc-arayuz   # soru sormadan
~/openmc-arayuz/bin/openmc-arayuz                  # uygulamayı başlat
bash ~/openmc-arayuz/share/openmc-arayuz-paket/kaldir.sh         # kaldır (yalnız o klasörü siler)
```

Projelerinize, `~/nucdata`'ya ve `~/.config/openmc_arayuz` ayarlarına dokunulmaz; kurulum `~/.bashrc`'yi
değiştirmez. Kurulum dosyasını kendiniz üretmek için: `paket/constructor/uret.sh`
(`constructor` kurulu `openmc-paketleme` conda ortamı gerekir; çıktı `dist/`).
Bu yolu kullanıyorsanız aşağıdaki 1. ve 2. adımı atlayıp 3. adımdan (nükleer veri) sürdürün.

## 1. Conda (Miniforge) kurun

Zaten conda/mamba varsa bu adımı atlayın.

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh        # soruları varsayılanla geçin, sonra terminali kapatıp açın
```

## 2. Ortamı kurun

Zip'i açtığınız klasörde:

```bash
cd openmc_arayuz
conda env create -f environment.yml    # OpenMC 0.16.0 + PySide6 + matplotlib ... (birkaç dakika)
conda activate openmc-env
pip install -e . --no-deps             # uygulamayı ortama bağlar: openmc-arayuz, openmc-arayuz-kosu
```

OpenMC PyPI'da yayımlanmıyor; conda-forge'dan gelir. Bu yüzden `pip install`
**`--no-deps`** ile çalıştırılır: bütün bağımlılıklar zaten `environment.yml`
ile kuruldu. Ortam önceden kurulduysa eksik araçlar için:
`conda install -c conda-forge pytest pytest-xdist babel`.

## 3. Nükleer veriyi indirin

```bash
./veri_indir.sh --bashrc
```

Bu betik `~/nucdata` altına şunları indirir ve doğrular:
- ENDF/B-VIII.0 HDF5 tesir kesiti kütüphanesi (OpenMC'nin resmi kütüphanesi, https://openmc.org/data)
- Tükenme zincirleri (ENDF/B-VIII.0 termal/hızlı ve CASL). Her dosyanın bayt
  sayısı ve sha256'sı kontrol edilir; yarım kalan indirme kabul edilmez.

`--bashrc`, `OPENMC_CROSS_SECTIONS` ve `OPENMC_CHAIN_FILE` değişkenlerini
`~/.bashrc`'ye ekler. Bitince **yeni bir terminal açın** (ya da `source ~/.bashrc`)
ve ortamı yeniden etkinleştirin: `conda activate openmc-env`.

İndirme kesilirse betiği yeniden çalıştırın; kaldığı yerden sürer. Veriyi başka
bir diske koymak için: `./veri_indir.sh --hedef /baska/disk/nucdata --bashrc`.

## 4. Doğrulayın ve başlatın

```bash
pytest -m hizli -n auto -q                  # hızlı süit, paralel (~40 sn); "passed", 0 failed
./calistir.sh                               # uygulama açılır (ya da: openmc-arayuz)
```

Testleri çalıştırmanın diğer yolları:

| Komut | Ne yapar |
|---|---|
| `pytest -m hizli -q` | Hızlı süit, tek çekirdek (~2,5 dk) |
| `pytest -m "hizli and not veri"` | Nükleer veri gerektirmeyenler (CI bunu koşar) |
| `pytest -m yavas` | Monte Carlo testleri (uzun; veri gerekir) |
| `python3 -m testler.test_regresyon --hizli` | Eski çalıştırıcı; sonunda "0 kaldi" yazmalı |
| `python3 -m testler.test_regresyon` | Tam süit (Monte Carlo dahil) |
| `TEST_SURE=1 python3 -m testler.test_regresyon --hizli` | Test başına süre ve en yavaş 20 test |

`veri` işaretli testler `OPENMC_CROSS_SECTIONS` yoksa atlanır (3. adım).
Uygulama logu `~/.local/state/openmc_arayuz/openmc_arayuz.log` dosyasına yazılır
(`XDG_STATE_HOME` ayarlıysa onun altına); hata bildirirken bu dosyayı ekleyin.

İlk deneme: açılan **"Ne modellemek istiyorsunuz?"** ekranında **Yakıt çubuğu → Boş
başla**, sonra **F9** (Çalıştır). Yarım dakika içinde sonuç kartında
**k∞ ≈ 1.323 ± 0.001** görmelisiniz (UO₂ %3.0, sıcak çalışma koşulu, "Normal"
hassasiyet; ölçülen 1.3227 ± 0.0008). Farklı bir makinede istatistik yüzünden son
hanede küçük farklar olağandır; ±0.003'ten büyük bir fark kurulum sorununa işaret eder.

Hazır örnekler başlangıç ekranının altındaki listede (17×17 PWR demeti, altıgen
SFR demeti, MTR plakası, Godiva kritiklik küresi, zırhlama küresi, tükenme...).
Örnekler **kopya** olarak açılır; kendi dosyanız için **Dosya → Farklı kaydet**.

## Sık karşılaşılanlar

| Belirti | Çözüm |
|---|---|
| `openmc PATH'te yok` | `conda activate openmc-env` unutulmuş. |
| `OPENMC_CROSS_SECTIONS ayarli degil` | 3. adım tamamlanmamış ya da yeni terminal açılmamış: `source ~/.bashrc`. |
| `Grafik oturum yok (DISPLAY...)` | SSH ile bağlısınız ya da WSL'de grafik yok. Uygulamayı masaüstü oturumunda açın; WSL için Windows 11 + güncel WSL gerekir (`wsl --update`). |
| Tükenme sekmesi "zincir eksik/bozuk" diyor | `./veri_indir.sh --yalniz-zincir` |
| `conda env create` çok uzun sürüyor | `conda config --set solver libmamba` (Miniforge'da varsayılan) ya da `mamba env create -f environment.yml` |
| Hesap sonuçları nereye yazılıyor? | Kayıtlı projede projenin yanındaki `kosu` dizinine; kaydedilmemiş (yeni/örnek) projede `~/openmc_kosular` altına. Çalıştır sekmesinde tam yol yazar. |

## Arayüzü kullanmadan

Çekirdek katman terminalden de çalışır ve her modeli tek başına çalışan,
okunabilir bir OpenMC Python betiğine çevirebilir:

```bash
openmc-arayuz-kosu ornekler/pwr_pinhucre.json                   # koş ve sonucu yaz
openmc-arayuz-kosu ornekler/pwr_pinhucre.json --sadece-dogrula  # yalnızca doğrula
openmc-arayuz-kosu ornekler/pwr_17x17.json --betik model.py     # Python betiği üret
openmc-arayuz-kosu uygunluk kosu/ --profil A,D [--siki]          # uygunluk denetimi
```

`uygunluk` çıkış kodu (CI / ders otomasyonu): 0 hata bulgusu yok, 1 hata bulgusu
var (ya da denetim yapılamadı), 2 kullanım hatası, 3 `--siki` verildiyse
değerlendirilemeyen ("uygulanamadı") kural var. `--siki` olmadan
değerlendirilemeyen kurallar başarısızlık sayılmaz; çıktıdaki sayımda görünür.

`pip install -e .` yapılmadıysa aynı komutlar `python3 -m cekirdek.kosucu ...` ile çalışır.

Arayüzde aynı işlem: **Dosya → Python betiği olarak dışa aktar (Ctrl+E)**.
