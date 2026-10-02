<a id="sozluk"></a>
# 10. Terim sözlüğü

Bu sözlük, arayüzün, çekirdek iletilerinin, kılavuzun ve raporun kullandığı terimlerin
Türkçe–İngilizce karşılıklarıdır. **Her Türkçe terimin tek bir İngilizce karşılığı vardır.**
Karşılıklar önce OpenMC'nin kendi adlandırmasına, sonra IAEA *Nuclear Safety and Security
Glossary (2022)* ve ISO 12749 serisine uyar. "Kaçın" sütunu, sık düşülen yanlış ya da belirsiz
karşılıklardır.

Kurallar:

- Tanımlayıcılar (JSON anahtarları, `tur` değerleri, dosya adları) **çevrilmez**; yalnız görünen
  metin çevrilir.
- OpenMC'nin kendi terimi varsa o kullanılır (*batch*, *tally*, *universe*).
- Birim ve simgeler çevrilmez: `k-eff`, `k∞`, `pcm`, `F_ΔH`, `F_q`, `MWd/kgHM`, `W/gHM`.
- **pcm** her yerde tanımıyla verilir: Δk × 10⁵ ya da Δρ × 10⁵ (hangisi olduğu yazılır).
- Belirsizlik 1σ standart belirsizliktir; "hata" denmez.

Kaynak tablo depodaki [SOZLUK.md](../../SOZLUK.md) dosyasıdır; aşağıdaki tablolar ondan
`araclar/kilavuz.sh --sozluk` ile üretilir (elle düzenlemeyin; terimi SOZLUK.md'ye ekleyin).

<!-- sozluk:baslangic (araclar/kilavuz.sh --sozluk uretir; elle duzenlemeyin) -->

### 10.1 Model yapısı ve geometri

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| model | model | project, design | bir spec dosyası |
| malzeme | material | substance |  |
| bileşim | composition | mixture |  |
| yoğunluk | density |  | g/cm³, atom/b-cm |
| zenginlik | enrichment | richness | ağırlıkça % |
| parça | component | part, piece | çubuk/plaka/tambur tanımları |
| çubuk (yakıt çubuğu) | pin (fuel pin) | rod, bar | pin-cell geleneği; kontrol çubuğu ayrı |
| pin hücre | pin cell | rod cell |  |
| bölge (çubuk bölgesi) | pin region | zone | OpenMC *region* ile karışmasın |
| kılıf (çubuk) | cladding | cover, sheath |  |
| kılıf (demet) | duct | wrapper, can, sheath | altıgen demet kılıfı |
| boşluk (gaz aralığı) | gap | void | pelet–kılıf aralığı |
| boşluk (malzemesiz) | void | vacuum, empty | `"bosluk"` dolgusu |
| plaka (yakıt plakası) | plate (fuel plate) | sheet | MTR |
| plaka elemanı | plate-type fuel element |  |  |
| demet | assembly | bundle, cluster | BWR bağlamında bile **assembly** |
| kılavuz boru | guide tube |  |  |
| yanabilir zehir | burnable absorber | burnable poison | IAEA: absorber |
| kor | core | heart, reactor |  |
| kor haritası | core map | layout |  |
| kafes | lattice | grid, mesh | OpenMC `Lattice` |
| kare kafes | rectangular lattice | square grid | OpenMC `RectLattice` |
| altıgen kafes | hexagonal lattice | hex grid | OpenMC `HexLattice` |
| halka (kafes halkası) | ring | circle, shell |  |
| adım | pitch | step |  |
| yönelim | orientation | direction | HexLattice/HexagonalPrism anlamında |
| yansıtıcı | reflector | mirror |  |
| yansıtıcı kuşak | radial reflector | reflector belt |  |
| eksenel katman | axial layer | axial zone, slice |  |
| eksenel dilim (tally) | axial bin | axial slice | güç tally'si |
| aktif yükseklik | active height | fuel length |  |
| plenum | plenum |  |  |
| kesik (konum/blok) | truncated (position/block) | cut, broken | kafes hücresi bölgeye sığmıyor |
| gizli konum | hidden position | masked |  |
| geometri ağacı | geometry tree | node tree | Dalga G |
| düğüm | node | element |  |
| kap | container | box, vessel | Dalga G düğümü |
| yerleşim | placement | insertion, layout | Dalga G alt yapısı |
| dönüşüm | transform | conversion | döndürme + öteleme |
| dönme | rotation | turning |  |
| öteleme | translation | offset |  |
| şablon | template | preset | 7 kor türü |
| gelişmiş geometri | advanced geometry | expert mode |  |
| küresel düzenek | spherical assembly | sphere setup | Godiva tipi |
| kabuk (küresel) | shell | layer |  |
| hücre | cell |  | OpenMC `Cell` |
| evren | universe |  | OpenMC `Universe`; arayüzde de *universe* |
| yüzey | surface | face |  |
| yüz (sınır yüzü) | face | side | "−x yüzü" → "−x face" |
| sınır koşulu | boundary condition | border condition |  |
| vakum / yansıtıcı / periyodik / beyaz | vacuum / reflective / periodic / white | void / mirror | OpenMC değerleri |
| yüz başına sınır | per-face boundary |  |  |
| simetri düzlemi | symmetry plane |  |  |
| çeyrek kor | quarter core | 1/4 core |  |

### 10.2 Kontrol

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| kontrol çubuğu | control rod | control bar |  |
| daldırma (oranı) | insertion (fraction) | immersion, depth | %0 çekilmiş, %100 tam dalmış |
| çekilmiş / dalmış | withdrawn / inserted | pulled out / dipped |  |
| kontrol tamburu | control drum | control cylinder, barrel |  |
| emici | absorber | poison | tambur/çubuk emicisi |
| gövde (tambur) | drum body | shell |  |
| emici yayı | absorber arc | absorber segment |  |
| tambur dönmesi | drum rotation | drum angle | 0° = emici kora bakıyor |
| grup (kontrol grubu) | control group | bank | PWR bağlamında "bank" yalnız açıklamada |
| çubuk değeri | rod worth | rod value |  |
| tambur değeri | drum worth |  |  |
| diferansiyel / integral değer | differential / integral worth |  |  |
| kritik arama | critical search | criticality search | OpenMC `search_for_keff` |
| kapatma marjı | shutdown margin | shutdown reserve | SDM |
| en etkili çubuk sıkışık | most reactive rod stuck out |  | N−1 |

### 10.3 Hesap ayarları ve Monte Carlo

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| hesap ayarları | run settings | calculation options | sayfa adı |
| hesap hassasiyeti | accuracy preset | precision level | Hızlı deneme / Normal / Hassas → Quick test / Normal / Accurate |
| özdeğer (kritiklik) hesabı | eigenvalue calculation | criticality run | OpenMC `eigenvalue` |
| sabit kaynak | fixed source | constant source | OpenMC `fixed source` |
| parçacık (çevrim başına) | particles (per batch) | neutrons, histories | OpenMC `particles` |
| çevrim | batch | cycle | OpenMC `batches` |
| pasif çevrim | inactive batch | passive cycle |  |
| aktif çevrim | active batch |  |  |
| nesil | generation |  | `generations_per_batch` |
| tohum | seed |  |  |
| iş parçacığı | thread |  | OpenMP |
| kaynak (nötron kaynağı) | source |  |  |
| kaynak yakınsaması | source convergence |  |  |
| Shannon entropisi | Shannon entropy |  |  |
| entropi ağı | entropy mesh |  |  |
| tally | tally | count, score table | çevrilmez |
| filtre | filter |  |  |
| skor | score |  | OpenMC `scores` |
| akı | flux |  |  |
| tesir kesiti | cross section |  |  |
| tesir kesiti kütüphanesi | cross section library | XS library |  |
| termal saçılma (S(α,β)) | thermal scattering (S(α,β)) |  |  |
| koşu | run | job, execution |  |
| koşu dizini | run directory | output folder |  |
| önizleme | preview |  |  |
| çizim (geometri çizimi) | plot | drawing | OpenMC `plot` |
| kayıp parçacık | lost particle |  |  |

### 10.4 Sonuçlar ve analiz

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| sonuçlar | results | outputs | sayfa adı |
| çoğaltma katsayısı | multiplication factor |  | k-eff |
| sonsuz çoğaltma katsayısı | infinite multiplication factor |  | k∞ |
| reaktivite | reactivity |  | ρ |
| reaktivite katsayısı | reactivity coefficient | reactivity factor |  |
| yakıt sıcaklık katsayısı (Doppler) | fuel temperature coefficient (Doppler) |  | FTC |
| moderatör sıcaklık katsayısı | moderator temperature coefficient |  | MTC |
| boşluk (void) katsayısı | void coefficient | emptiness coefficient |  |
| güç katsayısı | power coefficient |  |  |
| tarama | parameter sweep | scan |  |
| güç dağılımı | power distribution | power map |  |
| güç haritası | power map |  | görsel |
| tepe faktörü | peaking factor | peak coefficient | F_ΔH: enthalpy rise hot channel factor; F_q: heat flux hot channel factor |
| kinetik parametreler | kinetics parameters |  | β_eff, Λ |
| gecikmeli nötron oranı | delayed neutron fraction |  | β_eff |
| üretim zamanı | neutron generation time | production time | Λ |
| ani nötron ömrü | prompt neutron lifetime |  | ℓ = Λ·k |
| nokta kinetiği | point kinetics |  |  |
| gecikmeli nötron grubu | delayed neutron group |  | β_i, λ_i |
| öncül | precursor | predecessor | gecikmeli nötron öncülü |
| ani kritik | prompt critical | instant critical | ρ ≥ 1 $ |
| ters saat denklemi | inhour equation | inverse clock equation | Inhour |
| kararlı periyot | stable period |  | T = 1/ω₀ |
| belirsizlik | uncertainty | error | "hata" demeyin; 1σ yazılır |
| standart sapma | standard deviation |  | σ |
| kapsama faktörü | coverage factor |  | GUM |
| dört faktör | four factors (four-factor) |  | ε·p·f·η (Y3; Lamarsh, Duderstadt & Hamilton) |
| hızlı fisyon çarpanı | fast fission factor | fast fission ratio | ε |
| rezonanstan kaçma olasılığı | resonance escape probability | resonance escape factor | p |
| termal yararlanma | thermal utilization | thermal usage | f |
| sızmama olasılığı | non-leakage probability | no-leak probability | P_NL = P_FNL·P_TNL |
| letarji | lethargy |  | u = ln(E₀/E) |
| spektral indeks | spectral index (spectral indices) | spectrum index | ρ28, δ25, δ28, C* (CSEWG) |

### 10.5 Tükenme

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| tükenme | depletion | burnup calculation, exhaustion | OpenMC `deplete` |
| yanma | burnup | burning | MWd/kgHM |
| güç yoğunluğu | power density |  | W/gHM |
| tükenme zinciri | depletion chain | decay chain | OpenMC chain file |
| izlenen nüklid | tracked nuclide | followed isotope |  |
| nüklid | nuclide | isotope | izotop yalnız element-içi bağlamda |
| fisyon ürünü | fission product |  |  |
| aktinit / minör aktinit | actinide / minor actinide |  |  |
| fisyon ürünü zehiri | fission product poison |  | Xe-135, Sm-149 |
| entegratör | integrator |  | CE/CM, predictor |
| tükenme adımı | depletion step | time step |  |

### 10.6 Doğrulama, uygunluk ve rapor

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| doğrulama (model kontrolü) | model check | verification | arayüz bulgu paneli; V&V "validation" ile karışmasın |
| bulgu | finding | issue |  |
| hata / uyarı / bilgi | error / warning / info |  | seviye adları |
| bulguya git | go to finding |  |  |
| doğrulama ve geçerleme (V&V) | verification and validation (V&V) |  |  |
| kriter (benchmark) | benchmark | criterion | ICSBEP vakaları |
| deney değeri / hesap değeri | experimental value / calculated value |  | E, C |
| yanlılık | bias | error, offset |  |
| yanlılık belirsizliği | bias uncertainty |  |  |
| üst alt-kritik sınır | upper subcritical limit (USL) |  |  |
| alt-kritik pay | margin of subcriticality | safety margin | ΔSM |
| uygulanabilirlik alanı | area of applicability (AOA) |  |  |
| uygunluk denetimi | conformity check | compliance audit, certification | "sertifika değildir" çerçevesi |
| kontrol listesi | checklist |  | rapor eki başlığı |
| kontrolü geçen / geçmeyen / uygulanamayan | passed / not met / not applicable | compliant, certified |  |
| iyi uygulama | good practice | best practice | İU etiketi |
| proje ölçütü | project criterion |  | P etiketi |
| kullanıcı sınırı | user-defined limit |  | K etiketi |
| izlenebilirlik | traceability |  |  |
| tekrarlanabilirlik | reproducibility | repeatability |  |
| tekrarlanabilirlik kapsülü | reproducibility capsule |  | `kapsul.json` |
| rapor | report |  |  |
| kılavuz | user guide | manual |  |
| sözlük | glossary | dictionary |  |

### 10.7 Arayüz

| Türkçe | English | Kaçın | Not |
|---|---|---|---|
| Başlangıç | Start | Home |  |
| Malzemeler / Parçalar / Demet / Geometri / Hesap ayarları / Çalıştır / Sonuçlar / Analiz / Tükenme | Materials / Components / Assembly / Geometry / Run settings / Run / Results / Analysis / Depletion |  | kenar çubuğu |
| Model / Hesap / Sonuç (gruplar) | Model / Calculation / Results |  |  |
| Çalıştır / Durdur | Run / Stop | Start / Execute |  |
| Türü değiştir… | Change type… |  |  |
| örnek | example | sample | örnek galerisi = "Examples" |
| seviye (giriş/orta/ileri) | level (introductory/intermediate/advanced) | beginner/expert |  |
| kategori | category |  |  |
| son kullanılanlar | recent | history |  |
| komut paleti | command palette |  | Ctrl+K |
| geri al / yinele | undo / redo |  |  |
| kaydet / farklı kaydet | save / save as |  |  |
| dışa aktar / içe aktar | export / import |  |  |
| bildirim | notification | toast |  |

<!-- sozluk:son -->
