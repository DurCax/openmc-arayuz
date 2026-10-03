<a id="sozluk"></a>
# 10. Glossary

This glossary lists the English equivalents of the terms used by the user interface, the core
messages, this guide and the report. **Every Turkish term has exactly one English equivalent.**
The equivalents follow OpenMC's own naming first, then the IAEA *Nuclear Safety and Security
Glossary (2022)* and the ISO 12749 series. The "Avoid" column lists common wrong or ambiguous
translations.

Rules:

- Identifiers (JSON keys, `tur` values, file names) are **not translated**; only visible text is.
- Where OpenMC has its own term, it is used (*batch*, *tally*, *universe*).
- Units and symbols are not translated: `k-eff`, `k∞`, `pcm`, `F_ΔH`, `F_q`, `MWd/kgHM`, `W/gHM`.
- **pcm** is always given with its definition: Δk × 10⁵ or Δρ × 10⁵ (stating which one).
- Uncertainties are 1σ standard uncertainties; they are not called "errors".

The Turkish column is kept on purpose: when the interface or a message is still shown in Turkish,
look up the term here. The source table is [SOZLUK.md](../../SOZLUK.md) in the repository; the
tables below are generated from it with `araclar/kilavuz.sh --sozluk` (do not edit them by hand;
add the term to SOZLUK.md).

<!-- sozluk:baslangic (araclar/kilavuz.sh --sozluk uretir; elle duzenlemeyin) -->

### 10.1 Model structure and geometry

| English | Turkish | Avoid |
|---|---|---|
| model | model | project, design |
| material | malzeme | substance |
| composition | bileşim | mixture |
| density | yoğunluk |  |
| enrichment | zenginlik | richness |
| component | parça | part, piece |
| pin (fuel pin) | çubuk (yakıt çubuğu) | rod, bar |
| pin cell | pin hücre | rod cell |
| pin region | bölge (çubuk bölgesi) | zone |
| cladding | kılıf (çubuk) | cover, sheath |
| duct | kılıf (demet) | wrapper, can, sheath |
| gap | boşluk (gaz aralığı) | void |
| void | boşluk (malzemesiz) | vacuum, empty |
| plate (fuel plate) | plaka (yakıt plakası) | sheet |
| plate-type fuel element | plaka elemanı |  |
| assembly | demet | bundle, cluster |
| guide tube | kılavuz boru |  |
| burnable absorber | yanabilir zehir | burnable poison |
| core | kor | heart, reactor |
| core map | kor haritası | layout |
| lattice | kafes | grid, mesh |
| rectangular lattice | kare kafes | square grid |
| hexagonal lattice | altıgen kafes | hex grid |
| ring | halka (kafes halkası) | circle, shell |
| pitch | adım | step |
| orientation | yönelim | direction |
| reflector | yansıtıcı | mirror |
| radial reflector | yansıtıcı kuşak | reflector belt |
| axial layer | eksenel katman | axial zone, slice |
| axial bin | eksenel dilim (tally) | axial slice |
| active height | aktif yükseklik | fuel length |
| plenum | plenum |  |
| truncated (position/block) | kesik (konum/blok) | cut, broken |
| hidden position | gizli konum | masked |
| geometry tree | geometri ağacı | node tree |
| node | düğüm | element |
| container | kap | box, vessel |
| placement | yerleşim | insertion, layout |
| transform | dönüşüm | conversion |
| rotation | dönme | turning |
| translation | öteleme | offset |
| template | şablon | preset |
| advanced geometry | gelişmiş geometri | expert mode |
| spherical assembly | küresel düzenek | sphere setup |
| shell | kabuk (küresel) | layer |
| cell | hücre |  |
| universe | evren |  |
| surface | yüzey | face |
| face | yüz (sınır yüzü) | side |
| boundary condition | sınır koşulu | border condition |
| vacuum / reflective / periodic / white | vakum / yansıtıcı / periyodik / beyaz | void / mirror |
| per-face boundary | yüz başına sınır |  |
| symmetry plane | simetri düzlemi |  |
| quarter core | çeyrek kor | 1/4 core |

### 10.2 Control

| English | Turkish | Avoid |
|---|---|---|
| control rod | kontrol çubuğu | control bar |
| insertion (fraction) | daldırma (oranı) | immersion, depth |
| withdrawn / inserted | çekilmiş / dalmış | pulled out / dipped |
| control drum | kontrol tamburu | control cylinder, barrel |
| absorber | emici | poison |
| drum body | gövde (tambur) | shell |
| absorber arc | emici yayı | absorber segment |
| drum rotation | tambur dönmesi | drum angle |
| control group | grup (kontrol grubu) | bank |
| rod worth | çubuk değeri | rod value |
| drum worth | tambur değeri |  |
| differential / integral worth | diferansiyel / integral değer |  |
| critical search | kritik arama | criticality search |
| shutdown margin | kapatma marjı | shutdown reserve |
| most reactive rod stuck out | en etkili çubuk sıkışık |  |

### 10.3 Run settings and Monte Carlo

| English | Turkish | Avoid |
|---|---|---|
| run settings | hesap ayarları | calculation options |
| accuracy preset | hesap hassasiyeti | precision level |
| eigenvalue calculation | özdeğer (kritiklik) hesabı | criticality run |
| fixed source | sabit kaynak | constant source |
| particles (per batch) | parçacık (çevrim başına) | neutrons, histories |
| batch | çevrim | cycle |
| inactive batch | pasif çevrim | passive cycle |
| active batch | aktif çevrim |  |
| generation | nesil |  |
| seed | tohum |  |
| thread | iş parçacığı |  |
| source | kaynak (nötron kaynağı) |  |
| source convergence | kaynak yakınsaması |  |
| Shannon entropy | Shannon entropisi |  |
| entropy mesh | entropi ağı |  |
| tally | tally | count, score table |
| filter | filtre |  |
| score | skor |  |
| flux | akı |  |
| cross section | tesir kesiti |  |
| cross section library | tesir kesiti kütüphanesi | XS library |
| group constant (multigroup cross section) | grup sabiti (çok gruplu tesir kesiti) |  |
| transport correction | taşıma düzeltmesi |  |
| region type | bölge türü (homojenleştirme) | domain type |
| source region | kaynak bölgesi (random ray) | flat source region, FSR |
| thermal scattering (S(α,β)) | termal saçılma (S(α,β)) |  |
| run | koşu | job, execution |
| run directory | koşu dizini | output folder |
| preview | önizleme |  |
| plot | çizim (geometri çizimi) | drawing |
| lost particle | kayıp parçacık |  |

### 10.4 Results and analysis

| English | Turkish | Avoid |
|---|---|---|
| results | sonuçlar | outputs |
| multiplication factor | çoğaltma katsayısı |  |
| infinite multiplication factor | sonsuz çoğaltma katsayısı |  |
| reactivity | reaktivite |  |
| reactivity coefficient | reaktivite katsayısı | reactivity factor |
| fuel temperature coefficient (Doppler) | yakıt sıcaklık katsayısı (Doppler) |  |
| moderator temperature coefficient | moderatör sıcaklık katsayısı |  |
| void coefficient | boşluk (void) katsayısı | emptiness coefficient |
| power coefficient | güç katsayısı |  |
| parameter sweep | tarama | scan |
| power distribution | güç dağılımı | power map |
| power map | güç haritası |  |
| peaking factor | tepe faktörü | peak coefficient |
| kinetics parameters | kinetik parametreler |  |
| delayed neutron fraction | gecikmeli nötron oranı |  |
| neutron generation time | üretim zamanı | production time |
| prompt neutron lifetime | ani nötron ömrü |  |
| point kinetics | nokta kinetiği |  |
| delayed neutron group | gecikmeli nötron grubu |  |
| precursor | öncül | predecessor |
| prompt critical | ani kritik | instant critical |
| inhour equation | ters saat denklemi | inverse clock equation |
| stable period | kararlı periyot |  |
| uncertainty | belirsizlik | error |
| standard deviation | standart sapma |  |
| coverage factor | kapsama faktörü |  |
| four factors (four-factor) | dört faktör |  |
| fast fission factor | hızlı fisyon çarpanı | fast fission ratio |
| resonance escape probability | rezonanstan kaçma olasılığı | resonance escape factor |
| thermal utilization | termal yararlanma | thermal usage |
| non-leakage probability | sızmama olasılığı | no-leak probability |
| lethargy | letarji |  |
| spectral index (spectral indices) | spektral indeks | spectrum index |

### 10.5 Depletion

| English | Turkish | Avoid |
|---|---|---|
| depletion | tükenme | burnup calculation, exhaustion |
| burnup | yanma | burning |
| power density | güç yoğunluğu |  |
| depletion chain | tükenme zinciri | decay chain |
| tracked nuclide | izlenen nüklid | followed isotope |
| nuclide | nüklid | isotope |
| fission product | fisyon ürünü |  |
| actinide / minor actinide | aktinit / minör aktinit |  |
| fission product poison | fisyon ürünü zehiri |  |
| integrator | entegratör |  |
| depletion step | tükenme adımı | time step |
| depletion region subdivision | tükenme bölgesi bölme | mesh refinement |
| radial ring (pin ring) | radyal halka (pin halkası) | shell, annulus |
| axial slice | eksenel dilim | axial zone, node |
| equal-volume ring | eşit hacimli halka |  |
| branch calculation | dal hesabı |  |
| branch table | dal tablosu |  |
| reference branch | taban dal | base case |

### 10.6 Model check, conformity and report

| English | Turkish | Avoid |
|---|---|---|
| model check | doğrulama (model kontrolü) | verification |
| finding | bulgu | issue |
| error / warning / info | hata / uyarı / bilgi |  |
| go to finding | bulguya git |  |
| verification and validation (V&V) | doğrulama ve geçerleme (V&V) |  |
| benchmark | kriter (benchmark) | criterion |
| experimental value / calculated value | deney değeri / hesap değeri |  |
| bias | yanlılık | error, offset |
| bias uncertainty | yanlılık belirsizliği |  |
| upper subcritical limit (USL) | üst alt-kritik sınır |  |
| margin of subcriticality | alt-kritik pay | safety margin |
| area of applicability (AOA) | uygulanabilirlik alanı |  |
| conformity check | uygunluk denetimi | compliance audit, certification |
| checklist | kontrol listesi |  |
| passed / not met / not applicable | kontrolü geçen / geçmeyen / uygulanamayan | compliant, certified |
| good practice | iyi uygulama | best practice |
| project criterion | proje ölçütü |  |
| user-defined limit | kullanıcı sınırı |  |
| traceability | izlenebilirlik |  |
| reproducibility | tekrarlanabilirlik | repeatability |
| reproducibility capsule | tekrarlanabilirlik kapsülü |  |
| report | rapor |  |
| user guide | kılavuz | manual |
| glossary | sözlük | dictionary |

### 10.7 User interface

| English | Turkish | Avoid |
|---|---|---|
| Start | Başlangıç | Home |
| Materials / Components / Assembly / Geometry / Run settings / Run / Results / Analysis / Depletion | Malzemeler / Parçalar / Demet / Geometri / Hesap ayarları / Çalıştır / Sonuçlar / Analiz / Tükenme |  |
| Model / Calculation / Results | Model / Hesap / Sonuç (gruplar) |  |
| Run / Stop | Çalıştır / Durdur | Start / Execute |
| Change type… | Türü değiştir… |  |
| example | örnek | sample |
| level (introductory/intermediate/advanced) | seviye (giriş/orta/ileri) | beginner/expert |
| category | kategori |  |
| recent | son kullanılanlar | history |
| command palette | komut paleti |  |
| undo / redo | geri al / yinele |  |
| save / save as | kaydet / farklı kaydet |  |
| export / import | dışa aktar / içe aktar |  |
| notification | bildirim | toast |

<!-- sozluk:son -->
