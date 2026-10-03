# Değişiklik günlüğü / Changelog

Biçim: her sürüm `docs/YAZILIM_KALITE.md` §7 şablonuna uyar ("neyi doğruladık / neyi
doğrulamadık"); boş bırakılan alan "doğrulanmadı" sayılır. Sürüm numarası tek kaynaktan
gelir (`pyproject.toml` → `cekirdek/surum.py`). Ayrıntılı değişiklikler `git log`'dadır
(conventional commits). Sürüm notunun kullanıcıya dönük özeti (TR + EN):
`docs/SURUM_NOTLARI.md`.

## Yayımlanmamış (v3)

### Yeni — TRISO yakıt ve varyans azaltma (v3 Y9)
- **Parçalar › TRISO** (kompakt, pebble): geometri ağacına yeni bileşen türü (`trisolar[]`);
  `openmc.model.pack_spheres` (rastgele, RSP/CRP) ya da basit kübik kafes + `create_triso_lattice`.
  AGR-1 ve HTR-10 şablonları. Önizleme kapsamı, betik, malzeme yeniden adlandırma, doğrulama (3B şartı,
  paketleme sınırları). Örnekler: `htgr_kompakt`, `htgr_pebble`.
- **Hesap ayarları › Gelişmiş › Varyans azaltma** (`ayarlar.varyans`): MAGIC ağırlık penceresi üretimi
  (analog `uret`, `uret_uygula`), hazır `.h5`/`wwinp` uygulama, düzenli ve küresel ağ, enerji grupları.
  **Çalıştır › Verimlilik (FOM)** kartı: FOM = 1/(σ_bağıl²·T). Örnek: `zirh_agirlik_pencere`. Ders 5.21.
- Doğrulanan: paketleme oranı hedefe ±%1 (kurulmuş modelde kafesteki TRISO sayımıyla; üst üste binme yok);
  betik ve kurucu aynı parçacık merkezlerini kurar; derin zırhta pencereli sonuç analogla 0.5σ içinde
  (yanlılıksız), FOM ≈ 3× (üretim koşusu hariç). Doğrulanmayan: FW-CADIS (kapsam dışı: random ray adjoint
  ister), wwinp dışa aktarma (OpenMC 0.16'da yok), ince zırhta pencere kazancı (ölçüldü: kazanç yok).
- Davranış: `ayarlar.varyans` ve `trisolar` yoksa model, betik ve önbellek kimliği değişmez.

### Davranış değişikliği — ağ (mesh) tally'leri (v3 Y1)
- **2B (eksenel sonsuz) modelde otomatik ağın z aralığı ±1 cm → ±10⁴ cm** (`Z_2B_YARI`,
  `cekirdek/mesh_tally/tanim.py`). `mesh_turu` alanı olmayan `otomatik: true` v2 projeleri de
  etkilenir: üretilen betik, kaynak nötronu başına ham değerler ve z dilimleri değişir
  (v2.0 betiği: `testler/veri/y1_v2_mesh_betik.txt`). Gerekçe: ağ artık bütün z kolonunu
  kapsar (z integrali); ±1 cm'lik dilim iz uzunluğunun küçük bir kesrini sayıyordu (ölçüldü:
  kappa-fission bağıl hata medyanı %21 → %2.7, aynı geçmiş sayısı). Bağıl harita aynı fiziği
  verir; 2B'de hacim başına değer hücre alanına bölünür (z integrali / cm²).
- Özdeğer hesabında ağ tally'si varsa filtresiz `mesh_genel_isi` tally'si (`kappa-fission`,
  `heating-local`) eklenir; mutlak normalizasyonun paydası buradan okunur.

### Yeni — tükenme bölgesi bölme ve dal tabloları (v3 Y5)
- **Tükenme › Bölge bölme** kartı (`tukenme.bolme`, `cekirdek/bolge_bol.py`): pini radyal halkalara
  (eşit hacim / eşit kalınlık / dışa incelen) ve eksenel katmanları dilimlere böler; her parça ayrı
  tükenme malzemesi (Serpent `div`). Spec düzeyinde uygulanır, çubuk çubuk yanma otomatik açılır;
  K3 pin gücü bölünen pinin bütün halkalarını toplar. Bölme yalnız `tukenme.var` açıkken kurucu ve
  betikte görünür; gelişmiş (ağaç) modda desteklenmez (doğrulama HATA).
- **Analiz › Dal tablosu** kartı (`cekirdek/dal.py`): tükenme sonucunun yanma adımlarında bileşim
  sabit, T_yakıt × C_bor × T_mod/ρ_mod koşulları; Y10 kuyruğunda; k ± σ, Δk [pcm], CSV; terminal
  `python3 -m cekirdek.dal`. Örnek `ornekler/bolme/pwr_gd_bolme.json`; kılavuz 4.9.2, dal kartı, ders 5.20.
- Doğrulanan: halka alanları toplamı analitik hacme 1e-9 içinde (3 tür, 2B/3B); eşit hacimli 5 halka
  eski `pwr_gd_tukenme` halkalarıyla aynı yarıçap; bölünmüş demette K3 pin gücü bölünmemişle 4σ içinde
  (en kötü 3.4σ), toplam güç aynı; betik = kurucu; dal taban k = tükenme k ve adım-0 dalı tek değişkenli
  tarama (T_yakıt, bor) 2σ içinde. Gd pininde 6 MWd/kg'da kalan Gd-157: bölmesiz 0.198, 3/5/8 halka
  0.295/0.309/0.313 (k farkları istatistik düzeyinde, eşik yok). Doğrulanmayan: kor ölçeğinde bölme
  maliyeti, eksenel dilimin k(t) etkisi, dal tablosunun çekirdek simülatörü HFP/HZP tablolarıyla kıyası.
- Davranış: `tukenme.bolme` yoksa hiçbir şey değişmez. `kod_uret.uret` sonunda openmc kimlik
  sayacı sıfırlanır (çubuk çubuk yanma hesapları kimlik tüketiyordu).

### Yeni — grup sabitleri, çok gruplu MC ve random ray (v3 Y8)
- **Analiz › Grup sabitleri ve random ray** kartı: `openmc.mgxs` ile akı ağırlıklı grup sabitleri
  (bölge: malzeme / hücre / demet; CASMO-2…70, XMAS-172; taşıma düzeltmesi yok / P0), tablo,
  `mgxs.csv`, `mgxs.h5`; aynı geometrinin MG Monte Carlo ve random ray koşusu; CE/MG/RR
  karşılaştırması (k ± σ, Δpcm, süre). Kılavuz: Grup sabitleri kartı; ders 5.19.
- Doğrulanan: pin hücre 2 grup tek bölge G×G k∞ CE ile +74 pcm (4σ_CE içinde), random ray
  homojen ortamda özdeğere < 1 pcm; CASMO-70 malzeme MG MC CE'ye −66 ± 181 pcm (eşik 500),
  random ray MG'ye −10 pcm (eşik 300). Doğrulanmayan: sızıntılı/kor ölçekli homojenleştirme,
  sabit kaynakta random ray, sabitlerin çekirdek simülatöründe kullanımı.
- Davranış: `ayarlar.mgxs` yoksa kurulan model ve betik değişmez (varsayılana yazılmaz);
  tükenmede MGXS tally'leri eklenmez. P0 ile ince grupta MG MC geçersizdir (negatif köşegen,
  ölçülen −7600 pcm) — sonuç notu uyarır; varsayılan düzeltme "yok".
- `cekirdek/kuyruk.py`: genel `hazirlik_kilidi()` / `HAZIRLIK_KILIDI` (eski `_HAZIRLIK_KILIDI`
  aynı nesne).

### Davranış değişikliği — foton, sıcaklık, yüzey (v3 Y7)
- **Geçersiz `ayarlar.sicaklik_yontemi`** (ör. `spline`) artık doğrulamada **hata** verir;
  önceden değer OpenMC'ye geçer ve koşu başında OpenMC durdururdu.
- Doğrulama malzeme sıcaklığını kütüphaneyle karşılaştırır: `nearest` + tolerans dışı sıcaklık
  **hata** (OpenMC zaten dururdu), "yalnız kütüphane sıcaklığı kullanılır" **uyarı**, ara
  sıcaklıklar tek **bilgi** bulgusu.
- `kosucu.tally_metni`: ağ filtreli (MultiIndex) tablolar ham döküm yerine biçimli tablo
  (`ağ N (x=…, y=…, z=…)` etiketi; en çok 200 satır).
- `foton`, `sicaklik` ayar alanları yoksa kurulan model ve üretilen betik değişmez
  (`testler/veri/y7_altin_pinhucre.py`).

## 2.0.0 — 02.10.2026

### Ortam
- Uygulama commit: `v2.0.0` etiketi.
- OpenMC: 0.16.0 (conda-forge; sabit, `environment.yml`).
- Python 3.13, PySide6/Qt 6.11.2, numpy 2.5, scipy 1.18, matplotlib 3.11, pandas 3.0, h5py 3.16.
- Kütüphane: ENDF/B-VIII.0 HDF5 (openmc.org/data); zincirler: ENDF/B-VIII.0 termal/hızlı, CASL
  (bayt + sha256 `veri_indir.sh`'ta). `cross_sections.xml` sha256'sı her koşunun
  `kapsul.json`'unda yazılır.
- Ortam kilidi: `conda list --export` sha256'sı her koşunun `kapsul.json`'unda; depoda tam
  kilit dosyası yok (`docs/YAZILIM_KALITE.md` §4 md. 7).
- Platform: Linux (Ubuntu), x86-64.

### Neyi doğruladık (kanıtıyla)
- **Tam süit** (hızlı + yavaş, Monte Carlo dahil; `-n 4`, OMP_NUM_THREADS=6): 724 geçti,
  1 kaldı (`test_parca_demet::test_demet_yerlesim` — kılıflı altıgen demet kartı sayfayı
  kaydırıyordu; düzeltildi, test tek başına ve hızlı süit yeniden geçti). Toplam kapsam
  **%91.9** (çıktı: kapsam_tam_v2.txt, kısaltılmadan).
- **Hızlı süit** (son durum): 650 geçti / 0 kaldı.
- **Fizik çıpaları** (tam süit içinde): k∞ çıpası 1.35698 ± 0.00197 (referans 1.3570 ± 0.0020);
  Godiva 0.99957 ± 0.00054 (kriter 1.0000 ± 0.0010); kurucu ile üretilen betik aynı k
  (fark ≤ 1e-13); geometri parmak izi kapısı (30 örnek) geçti.
- **İzlenebilirlik** (`docs/IZLENEBILIRLIK.md`, tam süit JUnit sonucundan): 66 gereksinim —
  63 testle geçti, 3 inceleme; testsiz gereksinim 0.
- **V&V** (`docs/VV.md`): 26 deneyli küme, C/E tablosu ve NUREG/CR-6698 istatistiği bağımsız
  olarak (profesör denetimi, Ajan 15) yeniden hesaplandı. Uygulamanın alt kümesi bölünebilir
  tür + fiziksel biçim + tayf + zenginlik sınıfıyla seçilir; **mevcut kümeyle hiçbir uygulama
  USL almaz** (en büyük uygun alt küme < 10 vaka) ve araç bunu açıkça yazar.
- **Bağımsız denetimler:** profesör/standart denetimi (Ajan 15; tek engelleyici — LEU kafese
  USL verilmesi — düzeltildi) ve İngilizce arayüzle öğrenci QA (Ajan 14; 6 senaryo, çökme
  yok; ÖNEMLİ bulgular düzeltildi).
- Arayüz Türkçe ve İngilizce (3028 msgid); EN tarama (30 örnek × bütün sayfalar) Türkçe metin 0.
- Paket denetimi (`testler/test_paket.py`): `LICENSE` ve `THIRD_PARTY_LICENSES.md` var; sürüm
  tek kaynak; `openmc-arayuz-kosu --help` çalışır; izlenen dosyalarda `/home/` ve e-posta yok.
- Conda tarifi: `conda build` başarılı ve tarif testleri yeni ortamda geçti (rc1 adayında).

### Neyi doğrulamadık
- Docker imajı **derlenmedi** (geliştirme makinesinde Docker yok); noVNC ve WSL2/WSLg kipleri denenmedi.
- Conda paketinden arayüzün (GUI) açılması ve bir Monte Carlo koşusu denenmedi.
- Windows ve macOS: doğrulanmadı. Gerçek ekranda (başsız olmayan) tam tur: doğrulanmadı.
- ENDF/B-VIII.0 ve zincir dosyalarının resmî kullanım koşulları: doğrulanmadı.
- LWR/LEU kafes uygulamaları için kritiklik güvenliği USL'si: **yok** (açık bağımsız vaka
  bulunamadı; ICSBEP'ten yeniden modelleme gerekir).
- 1500 px genişlikte birkaç form kırpılması (görsel; QA KÜÇÜK).
- `docs/YAZILIM_KALITE.md` §4'teki açık eksiklikler: bağımsız V&V kuruluşu yok, gereksinimlerin
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
