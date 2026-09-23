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
│   ├── kurucu.py            spec → openmc.Model
│   ├── onbellek.py          model önbelleği (21.9 ms → 0.07 ms)
│   ├── dogrula.py           koşu öncesi kontroller
│   ├── kod_uret.py          spec → tek başına çalışan Python betiği
│   ├── ice_aktar.py         materials.xml → spec malzemeleri
│   └── kosucu.py            çalıştırma + statepoint okuma + terminal girişi
├── arayuz/                  PySide6 katmanı
│   ├── ana_pencere.py       sekmeler, proje aç/kaydet, doğrulama paneli
│   ├── onizleme.py          canlı geometri kesiti (Model.plot sarmalayıcı)
│   ├── hex_izgara.py        altıgen harita editörü (QPainter)
│   └── sekme_*.py           malzeme / çubuk / kafes / kor / ayar / çalıştır
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

64 test var. Üçü bu katmanın doğruluğunun asıl kanıtıdır:

- **Regresyon çıpası** — `ornekler/pwr_pinhucre.json` referans değeri
  **k∞ = 1.3570 ± 0.0020** vermeli. 2σ dışına çıkarsa `kurucu.py`'de hata var.
- **Betik eşdeğerliği** — `kurucu.py` ile üretilen betik aynı tohumla **birebir
  aynı** k-eff vermeli (kare ve altıgen için ayrı ayrı). `kurucu.py` ya da
  `kod_uret.py` değiştirilirse mutlaka tekrar koşulmalı.
- **Altıgen düzen** — `altigen.py`'nin halka indeksleri OpenMC'nin kendi
  `HexLattice.show_indices()` çıktısıyla birebir uyuşmalı.

## Ölçülen referans sonuçlar

| Örnek | k-eff | Koşu (24 iş parçacığı) |
|---|---|---|
| `pwr_pinhucre` | 1.35698 ± 0.00197 | 7 s |
| `pwr_17x17` | 1.18325 ± 0.00075 | 44 s |
| `mtr_plaka` | 1.65368 ± 0.00083 | 42 s |
| `sfr_altigen` | 1.46634 ± 0.00070 | 53 s |

## Kaynak yakınsaması (Shannon entropisi)

Özdeğer hesaplarında entropi mesh'i varsayılan olarak **açıktır**. Koşu bitince
kaynak dağılımının pasif çevrimler içinde yakınsayıp yakınsamadığı otomatik
değerlendirilir:

> `kaynak = [OK] Kaynak dagilimi yakinsamis gorunuyor (kayma 0.0003 <= 2 sigma = 0.0096)`

**Yöntem:** aktif çevrimlerdeki entropi saçılması (σ) gürültü ölçüsü alınır;
pasif çevrimlerin ilk ve ikinci yarısının ortalamaları arasındaki kayma 2σ'yı
aşıyorsa kaynak hâlâ kayıyor demektir ve pasif çevrim sayısı yetersizdir.
Yakınsamamış kaynak k-eff'i **yanlı** tahmin ettirir ve bu başka türlü fark
edilmez.

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

## Bilinen sınırlar

- **Kontrol tamburu / dönen bileşenler** kapsam dışı.
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
