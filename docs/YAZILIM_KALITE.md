# Yazılım kalite kanıtı (Dalga S-4)

Durum: 01.10.2026. Bu belge aracın yazılım kalitesi için **elinde hangi kanıtın olduğunu ve
hangisinin olmadığını** listeler. Bir uygunluk beyanı değildir. Standart adları ve sürümleri
`docs/STANDARTLAR.md` §2.1'den alınmıştır; ücretli standartların metni görülmemiştir, madde
numarası verilmez, aşağıdaki her şey kendi sözcüklerimizle yazılmıştır.

## 1. Bağlam ve beyanlar

- **Yazılımın sınıfı.** Araç üniversite dersi, laboratuvar ve araştırma için geliştirilmektedir;
  güvenlikle ilgili (safety-related) bir hesap aracı olarak geliştirilmemiştir. En yakın çerçeve
  **ANSI/ANS-10.4-2008 (R2021)**'dir; bu standart güvenlikle ilgili **olmayan** bilimsel yazılımın
  V&V'si içindir. Aşağıdaki eksiklik listesi (§4) bu türden bir değerlendirmenin soracağı
  soruları kendi sözcüklerimizle sıralar.
- **Bütünlük düzeyi.** IEEE 1012-2024'ün bütünlük düzeyi kavramı açısından geliştirici olarak
  aracı **en düşük düzeyde** konumluyoruz (sonucu tek başına güvenlik kararına girmez). Bu
  beyan bağımsız bir değerlendirmeden geçmemiştir; daha yüksek düzeyde kullanmak isteyen
  kuruluş kendi düzeyini kendisi belirler.
- **ASME NQA-1.** NQA-1 (Subpart 2.7 dahil) bir **kuruluşun** kalite güvence programıdır;
  bir araç "NQA-1 uyumlu" olamaz ve bu araç NQA-1 programı altında geliştirilmemektedir.
  Aracı NQA-1 kapsamındaki bir işte kullanmak isteyen kuruluş, kendi edinme/kabul (commercial
  grade dedication) sürecini uygular; bu belgedeki kanıtlar o sürece **girdi** olabilir, yerine
  geçmez.
- **ANSI/ANS-10.3** tarihsel (historical) durumdadır; belge setinin esin kaynağı olarak anılabilir,
  hiçbir iddianın dayanağı yapılmaz. **ANSI/ANS-10.5** (kullanıcı ihtiyaçları) kılavuz için
  çerçevedir (Dalga 3, Ajan 13b).
- **ISO/IEC/IEEE 12207:2026** yalnız süreç **adlandırması** için kullanılır (§2 son sütun);
  süreçlerin standarda göre uygulandığı iddia edilmez.

## 2. Belge seti

| Belge | Yer | Durum (01.10.2026) | 12207 süreç adı (yalnız eşleme) |
|---|---|---|---|
| Gereksinimler | `docs/GEREKSINIMLER.md` | var (R-… kimlikli, tek cümle, yöntem T/İ/A) | Stakeholder needs / System requirements definition |
| Tasarım | `docs/GEOMETRI_MODELI.md` (geometri ağacı, §15 kararlar, §16 donmuş API) + `README.md` "Dizin yapısı" (kod haritası) | var; çekirdek dışı modüllerin tasarım belgesi yok, kod haritası README'de | Architecture / Design definition |
| Test planı | `testler/ortak_test.py` (sözleşme, `gereksinim` işareti), `conftest.py` (hizli / yavas / veri / zincir işaretleri), `.github/workflows/test.yml` | var; ayrı bir "test planı" belgesi yok — plan bu dosyalardadır | Verification |
| Test sonuçları | pytest `--junitxml` çıktısı → `docs/IZLENEBILIRLIK.md` | var; matris son verilen sonuç dosyasını gösterir, yavaş süit düzenli girmez (§4) | Verification |
| İzlenebilirlik | `docs/IZLENEBILIRLIK.md` (`araclar/izlenebilirlik.py` üretir) | var | Verification / Information management |
| V&V raporu | `docs/VV.md` (kriter C/E tablosu), `docs/STANDARTLAR.md` (uygunluk matrisi) | kısmen; yanlılık/USL (S-3) sürüyor | Validation |
| Kullanıcı kılavuzu | `docs/kilavuz/` (Dalga 3, Ajan 13b) | **yok** (planlandı); bugün `README.md` + `KURULUM.md` | Operation |
| Bilinen sınırlamalar | bu belge §5 + `README.md` "Bilinen tuzaklar" + `docs/STANDARTLAR.md` §4.10 | var, dağınık | Validation |
| Değişiklik günlüğü | `CHANGELOG.md` (§7 şablonu), `docs/SURUM_NOTLARI.md` (TR + EN) | var (Dalga 4, 2.0.0rc1); ayrıntı `git log` (conventional commits) | Configuration management |
| Yapılandırma / ortam kaydı | git + her koşu dizininde `kapsul.json` | var (S-4) | Configuration management |
| Lisans | `LICENSE`, `THIRD_PARTY_LICENSES.md` | var (Dalga 4; R-M8-01, `testler/test_paket.py`) | — |

## 3. Tekrarlanabilirlik kapsülü (Y2)

Her koşu (`kosucu.calistir`, arayüzün Çalıştır düğmesi ve `openmc-arayuz-kosu`) koşu dizinine
`spec.json`'un yanına `kapsul.json` yazar (`cekirdek/kapsul.py`):

| Alan | İçerik |
|---|---|
| `spec` | `spec.json` dosyasının bayt sha256'sı |
| `uygulama` | ad, sürüm, git commit, commit edilmemiş değişiklik var mı |
| `openmc` | sürüm + çalıştırılabilir yolu |
| `kutuphane` | `cross_sections.xml` yolu + sha256; dizin özeti (dosya sayısı, toplam boyut, en yeni mtime). h5 dosyaları **karmalanmaz** (~13 GB) — içerik değişikliği yalnız boyut/mtime ile görülür |
| `zincir` | tükenme açıksa zincir yolu + sha256 (64 MiB üstünde yalnız boyut + mtime) |
| `tohum`, `tohum_kaynagi` | etkin tohum (spec'te yoksa OpenMC varsayılanı 1) |
| `is_parcacigi`, `python`, `platform` | koşu ortamı |
| `ortam` | `conda list --export` çıktısının sha256'sı; conda yoksa `pip freeze`; ikisi de yoksa `yontem: null` + neden |

`openmc-arayuz-kosu yeniden <koşu_dizini> [--hedef D] [--kuru] [-s N]`: `spec.json`'un kapsüldeki
karmayla aynı olduğunu doğrular (değişmişse reddeder), bugünkü ortamla kapsül arasındaki farkları
alan alan yazar; `--kuru` değilse aynı spec, tohum ve iş parçacığıyla **ayrı** bir dizinde koşar
ve k-eff farkını raporlar. Ölçüm (01.10.2026, aynı makine, 4 iş parçacığı): iki koşunun k-eff farkı
4·10⁻¹⁶–6·10⁻¹⁵ (OpenMP indirgeme sırası); araç bu düzeydeki farkı "yuvarlama düzeyinde aynı"
diye yazar, daha büyük farkı σ cinsinden verir. Kapsül **kanıttır, garanti değildir**: farklı
makine, kütüphane ya da OpenMC sürümünde fark beklenir ve listelenir.

## 4. Eksiklik listesi (ANS-10.4 türü bir değerlendirmenin soracakları)

Her madde açık bir eksikliktir; "kapatıldı" denmeden önce kanıtı bu belgeye bağlanır.

1. **Bağımsız V&V yok.** Kod, testler ve incelemeler aynı geliştirme sürecinden (geliştirici +
   yapay zekâ ajanları) çıkıyor; bağımsız bir gözden geçiren ya da ikinci bir kodla bağımsız hesap
   yok (Ek öneri İ-3: MCNP/Serpent dışa aktarma).
2. **Gereksinimlerin resmi gözden geçirme kaydı yok.** Kaynak, kullanıcının plan onaylarıdır
   (28.09 ve 30.09.2026); imzalı/sürümlü bir gözden geçirme kaydı tutulmuyor.
3. **Testsiz gereksinimler var.** Güncel liste `docs/IZLENEBILIRLIK.md` "Testsiz gereksinimler"
   bölümündedir (01.10.2026: R-M2-01 ve R-S-14 — benchmark ve V&V testleri S-3'ün dosyalarında,
   işaret bekliyor).
4. **Yavaş (Monte Carlo) süit düzenli koşmuyor.** CI yalnız `hizli and not veri` koşar (nükleer
   veri CI'da yok); fizik çıpaları (R-FZ-01…03) ve benchmark'lar yerel makinede, elle koşuluyor.
   Matrisin "çalıştırılmadı" satırları bunun görünür hâlidir.
5. **Gereksinim kapsamı ölçülüyor, kod kapsamı ayrıca.** `araclar/kapsam.sh` satır kapsamını
   ölçer (%80 hedefi uyarıdır); hangi kod satırının hangi gereksinime hizmet ettiği izlenmiyor.
6. **Kullanıcı kılavuzu, değişiklik günlüğü ve lisans dosyası yok** (Dalga 3 ve 4'te planlı).
7. **Ortam kilidi yalnız karmadır.** `kapsul.json` ortamın özetini taşır, kendisini değil; tam
   kilit dosyası (ör. `conda list --explicit`) depoda ve koşu dizininde saklanmıyor.
8. **Sorun bildirme ve düzeltme süreci yazılı değil.** Hatalar commit mesajlarında ve plan
   dosyasında izleniyor; numaralı hata kaydı ve "hata → gerileme testi" bağı yok (gelenek olarak
   kırmızı→yeşil test yazılıyor ama belgelenmiyor).
9. **Tek platform.** Testler Linux (Ubuntu) üzerinde koşuyor; Windows/macOS doğrulanmadı.
10. **Kütüphane içeriği karmalanmıyor.** h5 tesir kesiti dosyalarının değişmesi yalnız boyut/mtime
    ile fark edilir; bit düzeyinde değişen ama boyutu aynı kalan bir dosya gözden kaçabilir.
11. **Kritik testlerin bir kısmı gereksinime bağlı değil.** Liste `docs/IZLENEBILIRLIK.md`
    "Gereksinimsiz kritik testler" bölümündedir; bağlanmaları ya da gereksiz ilan edilmeleri
    gerekir.

## 5. Bilinen sınırlamalar (yazılım kalitesi açısından)

- Uygunluk denetimi ve V&V "kanıt üretir, sertifika vermez" (STANDARTLAR §1); USL için yeterli
  doğrulama kümesi yoksa araç "hesaplanamadı" der.
- Matris yalnız kendisine verilen pytest sonuç dosyasını yansıtır; dosya eskiyse matris de eskidir
  (kaynak dosyalar ve zaman damgaları matrisin başında yazılır).
- `yeniden` aynı spec'i kullanır; arada şema göçü olduysa yeni `spec.json` baytları farklı olabilir
  (araç bunu not eder). Eski koşu dizinlerinde (`kapsul.json` öncesi) yeniden üretim yapılamaz.
- Fizik ve geometri sınırlamaları için: `README.md` "Bilinen tuzaklar", `docs/GEOMETRI_MODELI.md`
  §16 "Sapmalar", `docs/STANDARTLAR.md` §4.10.

## 6. Matrisi ve kanıtı yeniden üretmek

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -m hizli -n 4 -q --junitxml=/tmp/hizli.xml
QT_QPA_PLATFORM=offscreen python -m pytest -m "yavas and gereksinim" -q --junitxml=/tmp/yavas.xml
python araclar/izlenebilirlik.py --junit /tmp/hizli.xml --junit /tmp/yavas.xml
python araclar/izlenebilirlik.py --denetle        # testsiz T / tanımsız kimlik -> çıkış 1
openmc-arayuz-kosu yeniden <koşu_dizini> --kuru   # kapsül ile bugünkü ortam farkı
```

## 7. Sürüm notu şablonu

Her sürümde (etiket `vX.Y.Z`) aşağıdaki şablon doldurulur; boş bırakılan alan "doğrulanmadı" sayılır.

```markdown
## vX.Y.Z — GG.AA.YYYY

### Ortam
- Uygulama commit: …        - OpenMC: …        - Kütüphane: … (cross_sections.xml sha256 …)
- Zincir: … (sha256 …)      - Ortam kilidi: conda list --export sha256 …
- Platform: …               - Test makinesi / iş parçacığı: …

### Neyi doğruladık (kanıtıyla)
- Hızlı süit: N geçti / 0 kaldı (junit: …)
- Yavaş süit (gereksinimli): N geçti / 0 kaldı (junit: …)
- Fizik çıpaları: k∞ = … ± … (R-FZ-01), Godiva = … ± … (R-FZ-02), betik farkı … (R-FZ-03)
- Benchmark C/E: docs/VV.md tablosu (R-M2-01); USL: … ya da "hesaplanamadı" (R-S-14)
- İzlenebilirlik: G gereksinimden T'si testli; testsiz: … (docs/IZLENEBILIRLIK.md)

### Neyi doğrulamadık
- Testsiz gereksinimler: …
- Bu sürümde koşulmayan testler ("çalıştırılmadı"): …
- Doğrulanmamış platformlar / kütüphaneler: …
- docs/YAZILIM_KALITE.md §4'ten açık kalan eksiklikler: …

### Değişiklikler
- Kullanıcıya görünen davranış değişiklikleri: …
- Sonuçları etkileyebilecek değişiklikler (fizik, geometri, veri): … → yeniden koşulan çıpalar: …

### Bilinen sınırlamalar
- …
```
