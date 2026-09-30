# Doğrulama ve geçerleme (V&V)

Bu belge aracın kriter (benchmark) paketini ve ölçülen sonuçları verir. Sayılar
`ornekler/*.json` içindeki `referans.olcum` alanlarıyla birebir aynıdır;
`testler/test_benchmark.py` bunu denetler (BM4).

**Ortam (bütün koşular):** OpenMC 0.16.0, ENDF/B-VIII.0 (HDF5, OpenMC resmî
kütüphanesi), 8 OpenMP iş parçacığı (makine başka Monte Carlo işleriyle paylaşıldı;
süreler bu yüzden üst sınırdır), 29.09.2026. Pasif çevrim sayısı her satırda
"çevrim/pasif" olarak verilir.

**Kabul ölçütü:** |C − E| ≤ 3·√(σc² + σe²) ve σc ≤ 30 pcm. Bu ölçüt projenin kendi
ölçütüdür, bir standarttan gelmez (docs/STANDARTLAR.md §6 md. 15–17). Ölçütü aşan kriter
yalnız aşağıda kütüphane yanlılığı olarak açıklanırsa kabul edilir (şu an yok).

Deney (C/E) ve hesap-hesap karşılaştırmaları AYRI tutulur: deney kriterinde E
ölçülmüş bir kritik düzenektir (ICSBEP), hesap-hesap kriterinde E başka kodların
hesap sonucudur ve "doğru" değer değildir.

## Deney kriterleri (C/E)

| Örnek | Kriter | E ± σe | C ± σc | C − E [pcm] | fark/σ | C/E | parçacık | çevrim/pasif | süre [s] | Sonuç |
|---|---|---|---|---|---|---|---|---|---|---|
| godiva_kriter.json | HEU-MET-FAST-001 (Godiva) | 1.0000 ± 0.0010 | 1.00038 ± 0.00025 | +38 | 0.37 | 1.00038 | 100000 | 150/50 | 25.3 | geçti |
| kriter_jezebel.json | PU-MET-FAST-001 (Jezebel) | 1.0000 ± 0.0020 | 0.99996 ± 0.00023 | −4 | 0.02 | 0.99996 | 50000 | 150/50 | 5.5 | geçti |
| kriter_flattop25.json | HEU-MET-FAST-028 (Flattop-25) | 1.0000 ± 0.0030 | 1.00106 ± 0.00026 | +106 | 0.35 | 1.00106 | 100000 | 150/50 | 51.8 | geçti |
| kriter_lct008.json | LEU-COMP-THERM-008, durum 1 | 1.0007 ± 0.0012 | 1.00067 ± 0.00021 | −3 | 0.02 | 0.99997 | 100000 | 260/50 | 451.4 | geçti |

C − E [pcm] = Δk × 10⁵ (k farkı; reaktivite farkı Δρ değildir).

Notlar:

- Bütün ICSBEP modelleri el kitabının **basitleştirilmiş** kriter modelleridir;
  atom yoğunlukları ve ölçüler `mit-crpg/benchmarks` deposundaki OpenMC/MCNP
  girdileriyle birebir karşılaştırıldı (`icsbep/<kriter>/`). E ve σe aynı deponun
  `icsbep/icsbep/uncertainties.csv` tablosundan (ICSBEP değerleri).
- **LCT-008 model eşdeğerliği:** aracın kurduğu model (kontrol tamburu olmayan
  "tamburlu" kor türü, 93×93 çubuk kafesi, 76.2 cm tank) ile mit-crpg'nin özgün
  OpenMC geometrisi aynı kütüphaneyle koşuldu: özgün 1.0006 ± 0.0004
  (100000 × 80 aktif çevrim), araç 1.00067 ± 0.00021 — fark istatistik içinde.
  Çubuk haritası özgün geometriden nokta sorgusuyla çıkarıldı (4961 çubuk).
- Godiva önceki ölçümü (0.99957 ± 0.00054, 20000 parçacık) yeni ölçümle
  (1.00038 ± 0.00025) 1.4σ içinde tutarlıdır.

## Hesap-hesap kriterleri

| Örnek | Kriter | E ± σe | C ± σc | C − E [pcm] | fark/σ | parçacık | çevrim/pasif | süre [s] | Sonuç |
|---|---|---|---|---|---|---|---|---|---|
| kriter_vver1000_ugd.json | NEA VVER-1000 LEU (UGD), S5, yanma 0 | 1.3185 ± 0.0040 | 1.31910 ± 0.00021 | +60 | 0.15 | 100000 | 250/50 | 574.6 | geçti |
| sfr_met1000_kor.json (bilgi) | OECD/NEA SFR MET-1000, BOC | 1.0355 ± 0.0078 | 1.03014 ± 0.00053 | −536 | 0.69 | 10000 | 150/40 | 281.5 | tutarlı (σc > 30 pcm, referans koşusu değil) |

C − E [pcm] = Δk × 10⁵ (k farkı; reaktivite farkı Δρ değildir).

Notlar:

- **VVER-1000 (NEA/NSC/DOC(2002)10):** E, Ek C Tablo C.1'deki altı katılımcının
  (MCU 1.3197, TVS-M 1.3213, WIMS8A 1.3122, HELIOS 1.3181, MCNP4B 1.3235,
  MULTICELL 1.3164) ortalaması, σe örnek standart sapmasıdır (kod/kütüphane
  saçılımı; istatistik belirsizlik değil). Sürekli enerjili tek Monte Carlo
  katılımcısı MCNP4B'ye göre fark 1.31910 − 1.3235 = −440 pcm'dir (katılımcı
  ortalamasına göre +60 pcm); MCNP4B'nin kütüphanesi (1990'lar,
  ENDF/B-VI tabanlı) ENDF/B-VIII.0'dan farklıdır — özellikle U-238 rezonans ve
  O-16 verisi değişti. Bu fark yalnız bilgi amaçlıdır, kabul ölçütü ortalamaya
  göredir.
- **SFR MET-1000 (NEA/NSC/R(2015)9):** E, Tablo 4.3 BOC katılımcı ortalaması
  (20 hesap, farklı kod ve kütüphaneler), σe katılımcılar arası standart sapma
  (780 pcm). Bu satır kriter paketinin parçası DEĞİLDİR (örnek; σc ≤ 30 pcm koşusu
  yapılmadı), yalnız tutarlılık bilgisidir.

## Kütüphane yanlılığı açıklamaları

Şu an 3σ ölçütünü aşan kriter yok. Aşan bir kriter eklenirse açıklaması bu
başlığın altına "### <örnek dosyası>" başlığıyla yazılır ve
`testler/test_benchmark.py` içindeki `KUTUPHANE_YANLILIGI` sözlüğüne o başlık
eklenir.

## Yeniden üretme

- Hızlı denetim (Monte Carlo yok): `python -m pytest testler/test_benchmark.py -m hizli`
- Azaltılmış istatistikli yeniden koşu (her kriter ≤ ~2 dk, 8 iş parçacığı):
  `python -m pytest testler/test_benchmark.py -m yavas`
- Tablodaki referans koşuları: örneği açın, parçacık/çevrim/pasif değerlerini
  tablodakiyle değiştirin, `OMP_NUM_THREADS=8` ile çalıştırın.

## Kaynaklar

- ICSBEP: International Handbook of Evaluated Criticality Safety Benchmark
  Experiments, NEA/NSC/DOC(95)03 (HEU-MET-FAST-001, HEU-MET-FAST-028,
  PU-MET-FAST-001, LEU-COMP-THERM-008). Model girdileri:
  https://github.com/mit-crpg/benchmarks
- NEA/NSC/DOC(2002)10: A VVER-1000 LEU and MOX Assembly Computational Benchmark,
  Specification and Results.
- NEA/NSC/R(2015)9: Benchmark for Neutronic Analysis of Sodium-cooled Fast
  Reactor Cores with Various Fuel Types and Core Sizes.
