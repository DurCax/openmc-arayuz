# Sürüm notları / Release notes — 2.0.0

Ayrıntılı ve denetlenebilir liste ("neyi doğruladık / neyi doğrulamadık"): `CHANGELOG.md`.
*The detailed, auditable list ("what we verified / what we did not"): `CHANGELOG.md`.*

---

## Türkçe

**2.0.0 (02.10.2026).**

### Öne çıkanlar
- **Esnek geometri.** Model artık bir geometri ağacıdır (beş düğüm türü): karışık kare/altıgen
  kafes, pin kesitleri, yerleşim ve yüz başına sınır koşulu. Eski modeller açılışta otomatik
  göç eder. Geometri sayfasında şablon seçici, gelişmiş ağaç editörü, kesit görünümü ve geri al.
- **Standartlara uygunluk kanıtı.** Her koşu kurallara göre denetlenir (profil A–D) ve rapora
  uygunluk eki girer; NUREG/CR-6698 yöntemiyle yanlılık, USL ve uygulanabilirlik alanı
  hesaplanır (26 deneyli V&V kümesi). Araç **sertifika vermez**: standartların isteyeceği
  kanıtı üretir ve eksikleri gösterir.
- **Tekrarlanabilirlik.** Her koşu dizinine `kapsul.json` (sürüm, commit, kütüphane ve ortam
  özeti, tohum) yazılır; `openmc-arayuz-kosu yeniden <dizin>` koşuyu yeniden üretir ve farkı
  raporlar.
- **Yeni arayüz.** Kenar çubuğu, başlangıç galerisi, komut paleti, kart düzenli sayfalar,
  açık/koyu tema; HTML/PDF rapor.
- **İngilizce.** Arayüz ve çekirdek iletileri İngilizce kullanılabilir (Ayarlar ya da
  `OPENMC_ARAYUZ_DIL=en`); temel belgelerin İngilizcesi var.
- **Dağıtım.** Docker imajı (X11/WSLg ya da tarayıcıdan noVNC; nükleer veri imaja gömülmez),
  conda paketi tarifi, lisans dosyaları.

### Kurulum
- Conda ortamı: `KURULUM.md` / `INSTALL.md` (değişmedi).
- Docker: `docker/derle.sh` ile derleyin; `docker/calistir.sh veri-indir` ile veriyi bir kez
  indirin (ya da `VERI=<veri dizini>` ile var olanı bağlayın); `docker/calistir.sh x11` ya da
  `docker/calistir.sh web` (sonra `http://localhost:6080/vnc.html`). Windows'ta Docker Desktop +
  WSL2 kullanın; WSLg varsa `x11`, yoksa `web` kipi.
- Conda paketi: `conda build conda-recipe -c conda-forge`; paket yalnız izin verilen kişilere
  dosya ya da özel kanal olarak verilir.

### Uyumluluk ve dikkat
- Eski model dosyaları açılışta şema 3'e göç eder; kaydedilen dosya şema 3 biçimindedir ve
  1.x sürümleriyle açılması desteklenmez.
- OpenMC 0.16.0'a sabittir.
- Kaynak ağacından kuranlar `pip install -e . --no-deps` komutunu yeniden çalıştırmalıdır
  (sürüm ve `setuptools>=77` gereği).

### Lisans
Yazılım **tüm hakları saklı** özel mülktür (`LICENSE`); yalnız izin verilen kişilerce
kullanılabilir. Lisans anahtarı ya da telemetri yoktur. Üçüncü taraf bileşenler:
`THIRD_PARTY_LICENSES.md`.

### Bilinen sınırlamalar
- Docker imajı bu adayda derlenmedi; conda paketi derlendi ve tarif testleri geçti, ama arayüz
  conda paketinden açılarak denenmedi (`CHANGELOG.md`).
- Yalnız Linux'ta test edildi; Windows yalnız Docker/WSL2 üzerinden hedeflenir, doğrulanmadı.
- Tam süit (Monte Carlo dahil) 724/1 → kalan yerleşim testi düzeltildi; kapsam %91.9; fizik çıpaları geçti.

---

## English

**2.0.0 (2026-10-02).**

### Highlights
- **Flexible geometry.** A model is now a geometry tree (five node types): mixed
  square/hexagonal lattices, pin cross-sections, placement and per-face boundary conditions.
  Older models are migrated automatically when opened. The Geometry page offers a template
  picker, an advanced tree editor, a cross-section view and undo.
- **Evidence for standards compliance.** Every run is checked against rules (profiles A–D)
  and the report gets a compliance appendix; bias, USL and area of applicability are computed
  with the NUREG/CR-6698 method (V&V set of 26 experiments). The tool **does not certify**: it
  produces the evidence the standards ask for and shows what is missing.
- **Reproducibility.** Each run directory gets a `kapsul.json` (version, commit, library and
  environment digest, seed); `openmc-arayuz-kosu yeniden <dir>` reproduces the run and reports
  the difference.
- **New interface.** Sidebar, start gallery, command palette, card-based pages, light/dark
  theme; HTML/PDF report.
- **English.** Interface and core messages are available in English (Settings or
  `OPENMC_ARAYUZ_DIL=en`); the main documents have English versions.
- **Distribution.** Docker image (X11/WSLg or browser via noVNC; nuclear data is not baked
  into the image), conda package recipe, license files.

### Installation
- Conda environment: `INSTALL.md` / `KURULUM.md` (unchanged).
- Docker: build with `docker/derle.sh`; download the data once with
  `docker/calistir.sh veri-indir` (or mount an existing directory with `VERI=<data dir>`);
  then `docker/calistir.sh x11` or `docker/calistir.sh web` (open
  `http://localhost:6080/vnc.html`). On Windows use Docker Desktop + WSL2: `x11` mode with
  WSLg, otherwise `web` mode.
- Conda package: `conda build conda-recipe -c conda-forge`; the package is handed only to
  permitted persons, as a file or via a private channel.

### Compatibility notes
- Old model files are migrated to schema 3 on open; a saved file is in schema 3 format and
  opening it with 1.x versions is not supported.
- Pinned to OpenMC 0.16.0.
- Source-tree installs must re-run `pip install -e . --no-deps` (new version and
  `setuptools>=77` requirement).

### License
The software is proprietary, **all rights reserved** (`LICENSE`); it may be used only by
permitted persons. There is no license key and no telemetry. Third-party components:
`THIRD_PARTY_LICENSES.md`.

### Known limitations
- The Docker image was not built for this candidate; the conda package was built and its recipe
  tests passed, but the interface was not launched from the conda package (`CHANGELOG.md`).
- Tested on Linux only; Windows is targeted only through Docker/WSL2 and is not verified.
- Full suite (Monte Carlo included) 724/1 → the remaining layout test was fixed; coverage 91.9 %; physics anchors passed.
