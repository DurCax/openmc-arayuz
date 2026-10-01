# Doğrulama ve geçerleme (V&V)

Bu belge aracın kriter (benchmark) paketini ve ölçülen sonuçları verir. Sayılar
`ornekler/*.json` içindeki `referans.olcum` alanlarıyla birebir aynıdır;
`testler/test_benchmark.py` bunu denetler (BM4).

**Ortam:** OpenMC 0.16.0, ENDF/B-VIII.0 (HDF5, OpenMC resmî kütüphanesi, 294 K).
İlk beş kriter (Ajan 9): 8 OpenMP iş parçacığı, 29.09.2026. V&V kümesi (`vv/…`,
Dalga S-3): 12 OpenMP iş parçacığı, 01.10.2026. Makine her iki durumda başka Monte
Carlo işleriyle paylaşıldı; süreler bu yüzden üst sınırdır. Pasif çevrim sayısı her
satırda "çevrim/pasif" olarak verilir.

**Kabul ölçütü:** |C − E| ≤ 3·√(σc² + σe²) ve σc ≤ 30 pcm. Bu ölçüt projenin kendi
ölçütüdür, bir standarttan gelmez (docs/STANDARTLAR.md §6 md. 15–17). Ölçütü aşan kriter
yalnız aşağıda kütüphane yanlılığı olarak açıklanırsa kabul edilir (şu an yok; en
büyük sapmalar PU-MET-FAST-008 2.62σ ve
U233-SOL-INTER-001 2.19σ — ölçütün içinde, aşağıda not edildi).

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
| vv/kriter_hst009a.json | HEU-SOL-THERM-009, durum 1 | 0.9990 ± 0.0043 | 1.00088 ± 0.00024 | +188 | 0.44 | 1.00188 | 100000 | 200/50 | 343.0 | geçti |
| vv/kriter_hst013.json | HEU-SOL-THERM-013, durum 1 | 1.0012 ± 0.0026 | 0.99854 ± 0.00025 | −266 | 1.02 | 0.99734 | 100000 | 200/50 | 361.2 | geçti |
| vv/kriter_hst032.json | HEU-SOL-THERM-032 (ORNL-10) | 1.0015 ± 0.0026 | 0.99851 ± 0.00020 | −299 | 1.15 | 0.99701 | 100000 | 200/50 | 449.5 | geçti |
| vv/kriter_imf003.json | IEU-MET-FAST-003, durum 2 | 1.0000 ± 0.0017 | 1.00013 ± 0.00018 | +13 | 0.08 | 1.00013 | 100000 | 200/50 | 63.3 | geçti |
| vv/kriter_imf004.json | IEU-MET-FAST-004, durum 2 | 1.0000 ± 0.0030 | 1.00482 ± 0.00020 | +482 | 1.60 | 1.00482 | 100000 | 200/50 | 52.2 | geçti |
| vv/kriter_lst002a.json | LEU-SOL-THERM-002, durum 1 | 1.0038 ± 0.0040 | 0.99994 ± 0.00020 | −386 | 0.96 | 0.99615 | 100000 | 200/50 | 322.4 | geçti |
| vv/kriter_lst002b.json | LEU-SOL-THERM-002, durum 2 | 1.0024 ± 0.0037 | 0.99578 ± 0.00023 | −662 | 1.79 | 0.99340 | 100000 | 200/50 | 226.8 | geçti |
| vv/kriter_lst003c.json | LEU-SOL-THERM-003, durum 3 | 0.9995 ± 0.0042 | 1.00396 ± 0.00028 | +446 | 1.06 | 1.00446 | 100000 | 200/50 | 221.6 | geçti |
| vv/kriter_mmf001.json | MIX-MET-FAST-001 (Planet) | 1.0000 ± 0.0016 | 0.99937 ± 0.00017 | −63 | 0.39 | 0.99937 | 100000 | 200/50 | 49.9 | geçti |
| vv/kriter_pci001.json | PU-COMP-INTER-001 (HISS/HPG) | 1.0000 ± 0.0110 | 1.00739 ± 0.00016 | +739 | 0.67 | 1.00739 | 100000 | 200/50 | 582.4 | geçti |
| vv/kriter_pmf002.json | PU-MET-FAST-002 (Jezebel-240) | 1.0000 ± 0.0020 | 1.00194 ± 0.00016 | +194 | 0.97 | 1.00194 | 100000 | 200/50 | 18.7 | geçti |
| vv/kriter_pmf006.json | PU-MET-FAST-006 (Flattop-Pu) | 1.0000 ± 0.0030 | 0.99950 ± 0.00020 | −50 | 0.17 | 0.99950 | 100000 | 200/50 | 73.3 | geçti |
| vv/kriter_pmf008.json | PU-MET-FAST-008 (Thor), 1B model | 1.0000 ± 0.0006 | 0.99836 ± 0.00018 | −164 | 2.62 | 0.99836 | 100000 | 200/50 | 53.1 | geçti |
| vv/kriter_pmf011.json | PU-MET-FAST-011 | 1.0000 ± 0.0010 | 1.00016 ± 0.00021 | +16 | 0.16 | 1.00016 | 100000 | 200/50 | 402.6 | geçti |
| vv/kriter_pmf018.json | PU-MET-FAST-018 | 1.0000 ± 0.0030 | 0.99789 ± 0.00018 | −211 | 0.70 | 0.99789 | 100000 | 200/50 | 65.6 | geçti |
| vv/kriter_pst001.json | PU-SOL-THERM-001, durum 1 | 1.0000 ± 0.0050 | 1.00119 ± 0.00027 | +119 | 0.24 | 1.00119 | 100000 | 200/50 | 304.5 | geçti |
| vv/kriter_pst021.json | PU-SOL-THERM-021, durum 3 | 1.0000 ± 0.0065 | 1.00100 ± 0.00026 | +100 | 0.15 | 1.00100 | 100000 | 200/50 | 93.3 | geçti |
| vv/kriter_umf001.json | U233-MET-FAST-001 (Jezebel-233) | 1.0000 ± 0.0010 | 1.00025 ± 0.00018 | +25 | 0.25 | 1.00025 | 100000 | 200/50 | 18.4 | geçti |
| vv/kriter_umf005.json | U233-MET-FAST-005, durum 2 | 1.0000 ± 0.0030 | 0.99689 ± 0.00021 | −311 | 1.03 | 0.99689 | 100000 | 200/50 | 63.5 | geçti |
| vv/kriter_umf006.json | U233-MET-FAST-006 (Flattop-23) | 1.0000 ± 0.0014 | 0.99985 ± 0.00020 | −15 | 0.11 | 0.99985 | 100000 | 200/50 | 132.4 | geçti |
| vv/kriter_usi001.json | U233-SOL-INTER-001, durum 1 | 1.0000 ± 0.0083 | 0.98178 ± 0.00022 | −1822 | 2.19 | 0.98178 | 200000 | 200/50 | 196.2 | geçti |
| vv/kriter_ust008.json | U233-SOL-THERM-008 (ORNL-11) | 1.0006 ± 0.0029 | 0.99973 ± 0.00021 | −87 | 0.30 | 0.99913 | 100000 | 200/50 | 410.4 | geçti |

C − E [pcm] = Δk × 10⁵ (k farkı; reaktivite farkı Δρ değildir).

Notlar:

- **V&V kümesi (`vv/…`, 22 vaka):** `araclar/vv_kriter_uret.py` mit-crpg/benchmarks
  (MIT lisansı, © 2011–2024 Paul Romano ve katkıda bulunanlar) OpenMC girdilerinden
  yalnız **eş merkezli küre kabuğu** olan modelleri `kuresel` şablonuna aktarır; atom
  yoğunlukları kayıpsız (atom/b-cm, nüklid bazında; ENDF/B-VIII.0'da olmayan doğal C0
  doğal bollukla C12/C13'e açılır), geometri birebir. E ± σe aynı deponun
  `uncertainties.csv`'sinden. Her JSON `referans.kaynak_model` ve `referans.lisans`
  alanlarını taşır. ICSBEP el kitabı metni yeniden dağıtılmaz (STANDARTLAR.md §6 md. 13).
  Reddedilen adaylar: kısmen dolu küreler (LEU-SOL-THERM-003 durum 1/6 ve -002 durum 3:
  çözelti üstünde boşluk), silindirik tanklar (SHEBA, STACY, HEU-MET-FAST-004 su tankı),
  kafesler (MIX-COMP-THERM-002) — içe aktarıcı bu desenleri tanımıyor ya da şablon dışı.
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

## V&V kümesi: AOA parametreleri

Her deney kriterinin uygulanabilirlik alanı (AOA, NUREG/CR-6698 §2.5 Tablo 2.3)
parametreleri `referans.aoa`'dadır. Bölünebilir tür, zenginlik, H/X ve fiziksel biçim
`cekirdek/vv/aoa.py` ile **spec'ten otomatik** çıkarılır; EALF (fisyona yol açan
nötronun ortalama letarji enerjisi) koşudaki `vv_ealf` tally'sinden (300 logaritmik
grup, 10⁻⁵ eV – 20 MeV), tayf sınıfı EALF'tan (termal < 1 eV ≤ ara < 100 keV ≤ hızlı);
yansıtıcı ve fiziksel biçim kriter tanımından girilir (`aoa_girdi`). Mevcut dört kriterin
EALF'ı 20000 × 60 çevrimlik kısa koşudan alınmıştır (k ölçümü değişmedi).
Zenginlik: tek bölünebilir türde bölünebilir izotopun (U-235, U-233 ya da Pu-239 + Pu-241)
kendi elementindeki kütle yüzdesi; "karisik"ta bölünebilir / ağır metal. H/X: H atomu /
bölünebilir atom, yalnız H bölünebilir malzemenin içindeyse; H yalnız ayrı bir malzemedeyse
(kafes, su yansıtıcı) hacim gerektiği için **verilmez**.

| Örnek | Seri | Bölünebilir | Zenginlik [%] | Biçim | Yansıtıcı | H/X | EALF [eV] | Tayf |
|---|---|---|---|---|---|---|---|---|
| godiva_kriter.json | HEU-MET-FAST-001 | U-235 | 93.71 | metal | yok | 0 | 8.28e+05 | hızlı |
| kriter_jezebel.json | PU-MET-FAST-001 | Pu | 95.48 | metal | yok | 0 | 1.27e+06 | hızlı |
| kriter_flattop25.json | HEU-MET-FAST-028 | U-235 | 93.24 | metal | dogal_u | 0 | 7.5e+05 | hızlı |
| kriter_lct008.json | LEU-COMP-THERM-008 | U-235 | 2.46 | oksit | su | — (heterojen) | 0.282 | termal |
| vv/kriter_hst009a.json | HEU-SOL-THERM-009 | U-235 | 93.18 | çözelti | su | 35.8 | 0.522 | termal |
| vv/kriter_hst013.json | HEU-SOL-THERM-013 | U-235 | 93.18 | çözelti | yok | 1.37e+03 | 0.0327 | termal |
| vv/kriter_hst032.json | HEU-SOL-THERM-032 | U-235 | 93.21 | çözelti | yok | 1.84e+03 | 0.0313 | termal |
| vv/kriter_imf003.json | IEU-MET-FAST-003 | U-235 | 36.53 | metal | yok | 0 | 6.18e+05 | hızlı |
| vv/kriter_imf004.json | IEU-MET-FAST-004 | U-235 | 36.54 | metal | grafit | 0 | 5.79e+05 | hızlı |
| vv/kriter_lst002a.json | LEU-SOL-THERM-002 | U-235 | 4.89 | çözelti | su | 1.1e+03 | 0.0385 | termal |
| vv/kriter_lst002b.json | LEU-SOL-THERM-002 | U-235 | 4.89 | çözelti | yok | 1e+03 | 0.0404 | termal |
| vv/kriter_lst003c.json | LEU-SOL-THERM-003 | U-235 | 10.07 | çözelti | yok | 897 | 0.039 | termal |
| vv/kriter_mmf001.json | MIX-MET-FAST-001 | karisik | 94.05 | metal | heu | 0 | 1.12e+06 | hızlı |
| vv/kriter_pci001.json | PU-COMP-INTER-001 | Pu | 94.62 | bileşik | sonsuz | 0.392 | 294 | ara |
| vv/kriter_pmf002.json | PU-MET-FAST-002 | Pu | 79.43 | metal | yok | 0 | 1.28e+06 | hızlı |
| vv/kriter_pmf006.json | PU-MET-FAST-006 | Pu | 95.15 | metal | dogal_u | 0 | 1.07e+06 | hızlı |
| vv/kriter_pmf008.json | PU-MET-FAST-008 | Pu | 94.85 | metal | toryum | 0 | 1.08e+06 | hızlı |
| vv/kriter_pmf011.json | PU-MET-FAST-011 | Pu | 94.76 | metal | su | — (heterojen) | 8.26e+04 | ara |
| vv/kriter_pmf018.json | PU-MET-FAST-018 | Pu | 95.08 | metal | berilyum | 0 | 9.24e+05 | hızlı |
| vv/kriter_pst001.json | PU-SOL-THERM-001 | Pu | 95.32 | çözelti | su | 370 | 0.0867 | termal |
| vv/kriter_pst021.json | PU-SOL-THERM-021 | Pu | 95.32 | çözelti | yok | 131 | 0.305 | termal |
| vv/kriter_umf001.json | U233-MET-FAST-001 | U-233 | 98.11 | metal | yok | 0 | 1.11e+06 | hızlı |
| vv/kriter_umf005.json | U233-MET-FAST-005 | U-233 | 98.20 | metal | berilyum | 0 | 7.71e+05 | hızlı |
| vv/kriter_umf006.json | U233-MET-FAST-006 | U-233 | 98.13 | metal | dogal_u | 0 | 9.62e+05 | hızlı |
| vv/kriter_usi001.json | U233-SOL-INTER-001 | U-233 | 98.56 | çözelti | berilyum | 24.6 | 7 | ara |
| vv/kriter_ust008.json | U233-SOL-THERM-008 | U-233 | 97.67 | çözelti | yok | 1.98e+03 | 0.0369 | termal |

Notlar: PU-MET-FAST-011 (su yansıtıcılı Pu küresi) ICSBEP'te "hızlı" sınıfındadır ama
yansıtıcıdan dönen termal nötronlar EALF'ı 83 keV'e indirir; araç 6698'in EALF sınırını
uyguladığı için "ara" yazar. PU-COMP-INTER-001 sonsuz ortamdır (yansıtıcı sınırlı küre;
doğrulama kapısı "çıplak düzenekte yansıtıcı sınır" uyarısı verir — bu vakada beklenen).

## Yöntem doğrulaması (NUREG/CR-6698): yanlılık, USL, AOA

Bu bölüm Dalga S-3'ün çıktısıdır. Kod: `cekirdek/vv/istatistik.py` (yöntem),
`cekirdek/vv/kume.py` (küme → `VVOzeti`), `cekirdek/vv/aoa.py` (AOA parametreleri).
Ölçüt ve formüller **NUREG/CR-6698** (NRC, Ocak 2001; açık belge, ML050250061)
kaynaklıdır; özet ve eşitlik numaraları `docs/STANDARTLAR.md` §4'tedir. Yöntem,
belgenin §3'teki 25 vakalık örneği birebir yeniden üretilerek sınanır
(`testler/test_vv.py` VV1: k̄ = 0.99983, S_p = 0.010564, K_L = 0.97562, bant
K_L(971.7) = 0.9515, β = %72.26, Shapiro–Wilk W = 0.9201).

**Akış.** (1) k_norm = k_calc / k_exp ve σ = √(σc² + σe²) (eş. 9, 3); (2) ağırlıklı
k̄, s², σ̄², S_p (eş. 4–7); (3) yanlılık = k̄ − 1, pozitifse USL'de 0 (eş. 8);
(4) normallik: Shapiro–Wilk (§2.4.3), p ≤ 0.05 ise parametrik olmayan yöntem
zorunlu (eş. 31–34, Tablo 2.2); (5) eğilim: zenginlik, H/X ve log₁₀(EALF)'a karşı
ağırlıklı doğrusal uydurma (eş. 10–15), eğim anlamlılığı t-testiyle (t-testi 6698'de
yok; SCALE/VADER uygulaması); (6) anlamlı eğilim varsa tolerans bandı (eş. 23–30),
yoksa tek taraflı tolerans sınırı (eş. 20–22, U(n) merkezî olmayan t ile; n > 50
için U(50)); (7) USL = K_L − ΔSM − ΔAOA (eş. 22/35), ΔSM ≥ 0.02 (§2.4.5);
(8) kabul k + 2σ < USL (eş. 36; `denetle()` K6).

**Aracın ek kuralı (sahte güven yok):** kümede 10'dan az vaka varsa (6698 §2.2:
teknik gerekçe ister) istatistikler raporlanır ama **USL verilmez**
("hesaplanamadı"); kullanıcı kuruluş gerekçesini yazıp `n_usl_asgari`'yi
düşürebilir — K10 yine uyarır. Parametrik olmayan yöntemde β ≤ %40 ise USL yine
verilmez (Tablo 2.2).

**ΔSM.** Varsayılan 0.05 (NUREG-1718 / NUREG-1520 Bl. 5 Ek B'de ek gerekçesiz kabul
edildiği bildirilen değer — **DOĞRULANMADI**, bkz. STANDARTLAR.md §2.2); 0.02 mutlak
alt sınırdır. ΔSM seçimi ve gerekçesi kullanıcı kuruluşa aittir.

### Sonuçlar (01.10.2026; ΔSM = 0.05, ΔAOA = 0)

σ_bias olarak birleştirilmiş standart sapma S_p (eş. 7; bant yönteminde eş. 28) verilir.
K_L tolerans sınırı / parametrik olmayan alt sınırdır; USL = K_L − ΔSM − ΔAOA.

| Alt küme (AOA) | n | yanlılık k̄ − 1 | S_p | Normallik (Shapiro–Wilk) | Eğilim | Yöntem | K_L | USL |
|---|---|---|---|---|---|---|---|---|
| Bütün küme | 26 | −0.00051 | 0.00235 | W = 0.794, p = 0.000 → normal değil | ealf: yok (t = 0.63), zenginlik: yok (t = 0.60) | parametrik olmayan (β = %73.6) | 0.9535 | 0.9035 |
| Hızlı tayf (EALF ≥ 100 keV) | 13 | −0.00050 | 0.00191 | W = 0.927, p = 0.311 → normal | ealf: yok (t = 1.23), zenginlik: yok (t = 1.60) | tolerans sınırı | 0.9944 | 0.9444 |
| Termal tayf (EALF < 1 eV) | 10 | −0.00089 | 0.00355 | W = 0.984, p = 0.984 → normal | ealf: yok (t = 1.89), zenginlik: yok (t = 0.52) | tolerans sınırı | 0.9888 | 0.9388 |
| Ara tayf | 3 | −0.00005 | 0.00334 | W = 0.941, p = 0.530 → normal | ealf: yok (t = 1.15), zenginlik: yok (t = 3.75) | tolerans sınırı | 0.9744 | **hesaplanamadı** |
| Çözelti (termal + ara) | 10 | −0.00203 | 0.00532 | W = 0.841, p = 0.045 → normal değil | ealf: yok (t = 0.40), h_x: yok (t = 0.31), zenginlik: yok (t = 0.24) | parametrik olmayan (β = %40.1) | 0.9235 | 0.8735 |
| U-235 (bütün biçimler) | 11 | −0.00006 | 0.00289 | W = 0.964, p = 0.819 → normal | ealf: yok (t = 1.59), zenginlik: yok (t = 0.08) | tolerans sınırı | 0.9918 | 0.9418 |
| Pu (bütün biçimler) | 9 | −0.00086 | 0.00189 | W = 0.831, p = 0.046 → normal değil | ealf: yok (t = 1.37), zenginlik: yok (t = 1.98) | parametrik olmayan (β = %37.0) | — | **hesaplanamadı** |
| U-233 | 5 | −0.00032 | 0.00268 | W = 0.689, p = 0.007 → normal değil | ealf: yok (t = 0.56), h_x: yok (t = 0.15), zenginlik: yok (t = 0.52) | parametrik olmayan (β = %22.6) | — | **hesaplanamadı** |
| LEU (U-235, zenginlik ≤ %20) | 4 | −0.00056 | 0.00350 | W = 0.980, p = 0.904 → normal | ealf: yok (t = 0.64), zenginlik: yok (t = 0.21) | tolerans sınırı | 0.9814 | **hesaplanamadı** |

Ortak notlar: kullanılan yanlılık = min(k̄ − 1, 0) — bütün alt kümelerde yanlılık
negatiftir, pozitif yanlılık kredilendirilmesi söz konusu değildir (eş. 8). H/X eğilimi
yalnız bütün vakalarda H/X tanımlıysa hesaplanır (LCT-008 ve PMF-011'de tanımsız →
o alt kümelerde H/X eğilimi yok). Hiçbir alt kümede anlamlı eğilim çıkmadı
(t < t₀.₉₇₅,ₙ₋₂), bu yüzden tolerans bandı yöntemi seçilmedi. Aynı deney serisinden
iki vaka (LEU-SOL-THERM-002 durum 1 ve 2) vardır: K14 "bağımsız değil" notu verir.

### Araç hangi alt kümeyi kullanır (panel, rapor eki, CLI)

Yukarıdaki tablo kümenin **betimsel** dökümüdür. Uygunluk denetimi (K6) bir uygulama için
USL'yi **yalnız** uygulamayla aynı bölünebilir türü, aynı fiziksel biçimi ve aynı nötron
tayfını paylaşan vakalardan hesaplar; U-235'te ayrıca zenginlik sınıfı aynı olmalıdır
(ICSBEP adlandırması: LEU ≤ %10, IEU %10–60, HEU ≥ %60) — `cekirdek/vv/kume.py`
`aoa_filtresi`, 6698 §2.5 ve Tablo 2.3. Uygun alt kümede 10'dan az vaka varsa USL
**verilmez** ve K6 "bu uygulama için USL yok (AOA dışında)" der. K6 geçtiğinde metinde alt
küme, n ve yöntem yazılır. Yansıtıcı ve H/X alt kümeyi daraltmaz: K6-AOA ve K12 ayrıca
denetler; heterojen kafeste H/X çıkarılamazsa K12 uyarır (H/X karşılaştırılmadı).

Depodaki kümede (26 vaka) bu ölçütle en büyük alt küme 5 vakadır:

| Alt küme | n |
|---|---|
| Pu, metal, hızlı | 5 |
| U-235, çözelti, termal, HEU | 3 |
| U-233, metal, hızlı | 3 |
| U-235, metal, hızlı, HEU (Godiva, Flattop-25) | 2 |
| U-235, metal, hızlı, IEU (IMF-003, -004) | 2 |
| U-235, çözelti, termal, LEU | 2 |
| Pu, çözelti, termal | 2 |
| U-235, oksit, termal, LEU (LCT-008) | 1 |
| diğer 6 alt küme | birer vaka |

Sonuç: **şu an depodaki küme hiçbir uygulama için USL vermez.** Bu bir hata değil, dürüst
sonuçtur: LWR/LEU kafes (pwr_17x17 vb.) için uygun alt küme yalnız LCT-008'dir (n = 1);
Godiva benzeri HEU hızlı metal için n = 2. Önceki sürüm alt kümeyi yalnız tayfla seçiyor ve
pwr_17x17'ye 9 çözelti + 1 kafesten USL = 0.93877 veriyordu (6698 Tablo 2.3'e aykırı;
düzeltildi, regresyon testi `testler/test_vv_altkume.py`). USL için ilgili alt kümeye en az
10 bağımsız deney eklenmelidir (STANDARTLAR.md §5).

### Tablodaki karışık alt kümeler neden USL için kullanılmaz

- **Hızlı tayf (0.9444, n = 13)**, **termal tayf (0.9388, n = 10)** ve **U-235 (bütün
  biçimler, 0.9418, n = 11)** satırları bölünebilir tür ve/veya biçim bakımından karışıktır;
  6698 Tablo 2.3 bunların aynı olmasını ister. Bu satırlar yalnız bilgi içindir; araç bunları
  hiçbir uygulamaya USL olarak vermez.
- **LWR / LEU kafes uygulamaları** (üniversitede en sık kullanılan): LEU oksit kafes alt
  kümesinde 1 vaka var (LCT-008) → **USL yok**. Açık modeli bulunan bağımsız LEU-COMP-THERM
  serileri (LCT-001, -002, -039 …) mit-crpg'de yoktur; ICSBEP el kitabından yeniden
  modellenmeleri gerekir (STANDARTLAR.md §5).
- **Tek bölünebilir türlü AOA'lar:** Pu (n = 9, normal değil, β = %37.0) ve U-233
  (n = 5, β = %22.6) → **USL hesaplanamadı** (Tablo 2.2: ek veri gerekli).
- **Ara tayf** (n = 3) → **USL hesaplanamadı**.
- MOX, oksit tozları, ıslak toz/bileşikler, ağır su, beton/çelik/kurşun yansıtıcılar,
  zehirli (B, Gd, Cd) sistemler, yüksek Pu-240 (> %20) ve AOA aralığı dışındaki
  zenginlik/H/X/EALF değerleri — kümede temsil edilmiyor; K6-AOA ve K12 uyarır.
- Bütün küme USL'si (0.9035, parametrik olmayan) farklı AOA'ları karıştırır; 6698 USL'nin
  her AOA için ayrı hesaplanmasını ister — bu satır yalnız bilgi içindir.
- PU-COMP-INTER-001 (PCI-001) modelinde H için S(α,β) termal saçılma verisi yoktur
  (mit-crpg modeli; bileşikteki H serbest gaz olarak taşınır). Ara tayfta etkisi küçük
  beklenir ama ölçülmedi; vaka yalnız betimsel tabloda yer alır.

### Sınırlamalar

- Ölçüt ve formüller NUREG/CR-6698'dendir; bu bir NRC **kılavuzudur** (bağlayıcı değil).
  ANS-8.24 metni görülmedi (STANDARTLAR.md §2.2). ΔSM = 0.05 varsayılanının kaynağı
  **DOĞRULANMADI**; 0.02 mutlak alt sınırdır. Pay seçimi kullanıcı kuruluşundur.
- Deneyler arası korelasyon ele alınmaz (6698 bağımsızlık varsayar; UACSA açık konu).
- Vakaların hepsi ICSBEP **basitleştirilmiş** (çoğu 1B küresel) modelleridir; modelleme
  yanlılığı E ± σ'nın içinde kabul edilir (ICSBEP değerlendirmesi). E ± σ mit-crpg
  `uncertainties.csv`'den alındı; güncel ICSBEP baskısıyla **karşılaştırılmadı**
  (STANDARTLAR.md §5 uyarısı).
- Yalnız tek kod + tek kütüphane (OpenMC 0.16.0, ENDF/B-VIII.0, 294 K) doğrulanmıştır;
  başka kütüphane ya da sürümde küme yeniden koşulmalıdır (`araclar/vv_kriter_uret.py`).
- n > 50 için 6698 normallik testi önermez; araç yine Shapiro–Wilk kullanır ve not eder.
- Eğilim anlamlılığı t-testi 6698'de tanımlı değildir (SCALE/VADER uygulaması).
- Bu araç sertifika vermez (STANDARTLAR.md §1); USL, kullanıcı kuruluşun kendi doğrulama
  raporunun yerine geçmez.

## Kütüphane yanlılığı açıklamaları

Şu an 3σ ölçütünü aşan kriter yok. Ölçütün içinde kalan ama dikkat çeken iki sapma
(nedenleri bu çalışmada incelenmedi): PU-MET-FAST-008 (Thor) C − E = −164 pcm, σe yalnız
60 pcm olduğu için 2.62σ; U233-SOL-INTER-001 C − E = −1822 pcm, σe = 830 pcm ile 2.19σ.
Bu iki vaka küme istatistiğinde ağırlıklarıyla yer alır; U233-SOL-INTER-001 bütün kümenin
normallik testini başarısız kılan uç değerdir. Aşan bir kriter eklenirse açıklaması bu
başlığın altına "### <örnek dosyası>" başlığıyla yazılır ve
`testler/test_benchmark.py` içindeki `KUTUPHANE_YANLILIGI` sözlüğüne o başlık
eklenir.

## Yeniden üretme

- Hızlı denetim (Monte Carlo yok): `python -m pytest testler/test_benchmark.py -m hizli`
- Azaltılmış istatistikli yeniden koşu (her kriter ≤ ~2 dk, 8 iş parçacığı):
  `python -m pytest testler/test_benchmark.py -m yavas`
- Tablodaki referans koşuları: örneği açın, parçacık/çevrim/pasif değerlerini
  tablodakiyle değiştirin, `OMP_NUM_THREADS=8` ile çalıştırın.

- V&V kümesini yeniden üretmek (mit-crpg/benchmarks klonu gerekir; ~2 saat, 12 iş):
  `OMP_NUM_THREADS=12 python araclar/vv_kriter_uret.py <benchmarks dizini>`;
  mevcut dört kritere AOA eki: `... --aoa-mevcut`.
- Yanlılık/USL özeti: `python -c "from cekirdek.vv import kume; print(kume.ozet(filtre={'tayf': 'termal'}))"`;
  denetçide: `denetle(spec, kosu_dizini, ("B",), vv=kume.ozet(...), uygulama=kume.uygulama(spec, kosu_dizini))`.

## Kaynaklar

- NUREG/CR-6698: J.C. Dean, R.W. Tayloe Jr., Guide for Validation of Nuclear Criticality
  Safety Calculational Methodology, NRC, Ocak 2001 (ML050250061) — yanlılık, USL, AOA yöntemi.
- mit-crpg/benchmarks (MIT lisansı): https://github.com/mit-crpg/benchmarks — V&V kümesi
  modelleri ve `icsbep/icsbep/uncertainties.csv` E ± σ değerleri.

- ICSBEP: International Handbook of Evaluated Criticality Safety Benchmark
  Experiments, NEA/NSC/DOC(95)03 (HEU-MET-FAST-001, HEU-MET-FAST-028,
  PU-MET-FAST-001, LEU-COMP-THERM-008). Model girdileri:
  https://github.com/mit-crpg/benchmarks
- NEA/NSC/DOC(2002)10: A VVER-1000 LEU and MOX Assembly Computational Benchmark,
  Specification and Results.
- NEA/NSC/R(2015)9: Benchmark for Neutronic Analysis of Sodium-cooled Fast
  Reactor Cores with Various Fuel Types and Core Sizes.
