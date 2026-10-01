# Değişiklik günlüğü / Changelog

Biçim: her sürüm `docs/YAZILIM_KALITE.md` §7 şablonuna uyar ("neyi doğruladık / neyi
doğrulamadık"); boş bırakılan alan "doğrulanmadı" sayılır. Sürüm numarası tek kaynaktan
gelir (`pyproject.toml` → `cekirdek/surum.py`). Ayrıntılı değişiklikler `git log`'dadır
(conventional commits). Sürüm notunun kullanıcıya dönük özeti (TR + EN):
`docs/SURUM_NOTLARI.md`.

## 2.0.0rc1 — 01.10.2026 (sürüm adayı; nihai `v2.0.0` etiketi henüz atılmadı)

### Ortam
- Uygulama commit: `v2-d4-16` dalı (birleştirme commit'i etikette yazılır).
- OpenMC: 0.16.0 (conda-forge; sabit, `environment.yml`).
- Python 3.13, PySide6/Qt 6.11.2, numpy 2.5, scipy 1.18, matplotlib 3.11, pandas 3.0, h5py 3.16.
- Kütüphane: ENDF/B-VIII.0 HDF5 (openmc.org/data); zincirler: ENDF/B-VIII.0 termal/hızlı, CASL
  (bayt + sha256 `veri_indir.sh`'ta). `cross_sections.xml` sha256'sı her koşunun
  `kapsul.json`'unda yazılır; bu sürüm notu için ayrıca alınmadı.
- Ortam kilidi: `conda list --export` sha256'sı her koşunun `kapsul.json`'unda; depoda tam
  kilit dosyası yok (`docs/YAZILIM_KALITE.md` §4 md. 7).
- Platform: Linux (Ubuntu), x86-64.

### Neyi doğruladık (kanıtıyla)
- Hızlı süit: `QT_QPA_PLATFORM=offscreen python -m pytest -m hizli -n 4 -q` — 0 kaldı
  — `v2-d4-16` dalında 597 geçti / 0 kaldı (01.10.2026; Dalga 3 sonu: 589 / 0). Birleştirme
  sonrası sayı etikette yeniden alınır.
- Paket denetimi (`testler/test_paket.py`, hızlı): `LICENSE` ve `THIRD_PARTY_LICENSES.md`
  var; sürüm tek kaynak; `openmc-arayuz-kosu --help` çalışır; izlenen dosyalarda `/home/`
  yolu ve e-posta adresi yok.
- İzlenebilirlik: 66 gereksinim (`docs/GEREKSINIMLER.md`); son matris (`docs/IZLENEBILIRLIK.md`,
  01.10.2026, yalnız hızlı süit sonucu): 44 geçti, 12 kısmen, 4 inceleme, 6 çalıştırılmadı.
- Benchmark C/E ve NUREG/CR-6698 yanlılık/USL: `docs/VV.md` (ör. Godiva 1.00038 ± 0.00025,
  deneysel 1.0000 ± 0.0010; hızlı metal USL 0.9444, n = 13; termal USL 0.9388, n = 10).
  Bu ölçümler Dalga S-3'te yapıldı; bu adayda yeniden koşulmadı.
- Üçüncü taraf lisansları kurulu paketlerden doğrulandı (`THIRD_PARTY_LICENSES.md`).
- Conda tarifi: `conda render conda-recipe` (sonuç dal raporunda).

### Neyi doğrulamadık
- Yavaş (Monte Carlo) süit ve fizik çıpaları (R-FZ-01…03) bu adayda koşulmadı; matriste
  "çalıştırılmadı" görünürler (`docs/YAZILIM_KALITE.md` §4 md. 4).
- Docker imajı bu adayda **derlenmedi** (geliştirme makinesinde Docker yok); `Dockerfile`
  gözden geçirildi ama `docker build` ile denenmedi. noVNC ve WSL2/WSLg kipleri denenmedi.
- `conda build` ile tam paket derlemesi ve kurulum testi (render dışında) — dal raporuna bakın.
- Windows ve macOS: doğrulanmadı.
- ENDF/B-VIII.0 ve zincir dosyalarının resmî kullanım koşulları: doğrulanmadı
  (`THIRD_PARTY_LICENSES.md` §3).
- `docs/YAZILIM_KALITE.md` §4'te açık kalan eksiklikler: bağımsız V&V yok, gereksinimlerin
  resmî gözden geçirme kaydı yok, numaralı hata kaydı yok, h5 içeriği karmalanmıyor.

### Değişiklikler (1.x → 2.0.0)

**Dalga 0–1 — altyapı ve sessiz hatalar.** pytest köprüsü (`hizli`/`yavas`/`veri`/`zincir`
işaretleri, `-n` paralel), `pyproject.toml` ve giriş komutları (`openmc-arayuz`,
`openmc-arayuz-kosu`), CI (GitHub Actions, veri gerektirmeyen hızlı süit), dönen uygulama
günlüğü, i18n iskeleti. Altıgen tam korda güç haritası, demet kılıfı, izlenen nüklid seçicisi
(yazım hatası doğrulaması, CSV), doğrudan yakıt hacmi ve tükenme kapısı, kapsam ölçümü.

**Dalga 2 — arayüzün yeniden düzeni.** Tasarım tokenları ve ortak bileşenler (Inter yazı tipi,
Lucide ikonları), kenar çubuğu kabuğu, başlangıç galerisi, komut paleti; Malzemeler, Parçalar,
Demet, Çalıştır, Hesap ayarları, Kor, Analiz ve Tükenme kart düzenleri. HTML/PDF rapor ve
`rapor` alt komutu; çok türlü güç tally'leri; 16 yeni örnek/kriter.

**Dalga G — esnek geometri.** Şema 3 ve otomatik göç; geometri ağacı (beş düğüm türü),
tek gezinti betiği, pin kesitleri, karışık (kare/altıgen) kafes, yerleşim, yüz başına sınır
koşulu; eşdeğerlik kapısı (nokta yoklaması, hacim, k∞ çıpası, Godiva, betik eşdeğerliği).
Geometri sayfası: şablon seçici + gelişmiş ağaç editörü, kesit görünümü, geri al. Eski kurucu
sarmalayıcıları kaldırıldı; 3 yeni ağaç örneği.

**Dalga S — uluslararası standartlara uygunluk kanıtı.** Sonuç uygunluk denetçisi (profil A–D,
kurallar K1–K16) ve `uygunluk` alt komutu; uygunluk paneli ve rapor eki; NUREG/CR-6698 yanlılık,
USL ve uygulanabilirlik alanı (AOA) ile 26 deneyli V&V kümesi (mit-crpg/benchmarks, MIT);
gereksinimler (66), izlenebilirlik matrisi, tekrarlanabilirlik kapsülü (`kapsul.json`) ve
`yeniden` alt komutu; yazılım kalite belgesi. Araç sertifika vermez; standartların isteyeceği
kanıtı üretir ve eksikleri gösterir (`docs/STANDARTLAR.md`).

**Dalga 3 — İngilizce.** Çekirdek (~1430 msgid) ve arayüz (1657 msgid) metinleri İngilizce;
`OPENMC_ARAYUZ_DIL` / Ayarlar'dan dil seçimi; `docs/SOZLUK.md` terim denetimi; README, INSTALL ve
V&V/örnek/standart/geometri belgelerinin İngilizcesi; kılavuz bağlantıları (F1, "?" düğmeleri).

**Dalga 4 — dağıtım (bu aday).** `LICENSE` (tüm hakları saklıdır), `THIRD_PARTY_LICENSES.md`,
Docker imajı (`Dockerfile`, `docker/`; veri gömülmez), conda tarifi (`conda-recipe/`), bu
değişiklik günlüğü ve `docs/SURUM_NOTLARI.md`. Sürüm okuma sırası değişti: kaynak ağacında
`pyproject.toml` önce okunur (düzenlenebilir kurulumun meta verisi sürüm değişince eski
kalıyordu); geri dönüşte sabit sürüm numarası yok (`0+bilinmiyor`). `scipy` doğrudan bağımlılık
olarak `pyproject.toml`'a yazıldı (V&V istatistikleri; önceden yalnız openmc üzerinden geliyordu).

**Sonuçları etkileyebilecek değişiklikler:** geometri çekirdeği yeniden yazıldı (Dalga G) →
eşdeğerlik kapısı ve k∞/Godiva çıpaları Dalga G'de yeniden koşuldu; tambur etkileşimi yeniden
ölçüldü (Dalga G+S düzeltmeleri). Dalga 3 ve 4 fiziği değiştirmez.

### Bilinen sınırlamalar
- Uygulama kaynak ağacına göre çalışır (ikonlar, yazı tipleri, `locale/`, `ornekler/`); düz
  bir `pip install .` wheel'i bunları taşımaz. Desteklenen yollar: kaynak ağacından
  `pip install -e . --no-deps`, Docker imajı ya da conda tarifi (ağacı `share/` altına kopyalar).
- `docs/YAZILIM_KALITE.md` §4 ve §5, `README.md` "Bilinen tuzaklar".

## 1.x — 23–28.09.2026

v2 öncesi tek geliştirici sürümleri (etiketsiz): pin hücresi → demet → kor modelleri, altıgen
kafes, malzeme içe aktarma, reaktivite katsayıları, kritik arama, kinetik parametreler, Godiva
kriteri, çubuk bazlı güç dağılımı (F_ΔH, F_q), kontrol çubuğu ve dönen tambur, eksenel katmanlı
kor, kaynak tayfı ve sabit kaynak modu, tükenme (yanma) çekirdeği ve sekmesi, Türkçe arayüz ve
tek terim düzeni, öğrenci QA düzeltmeleri, `KURULUM.md` / `environment.yml` / `veri_indir.sh`.
