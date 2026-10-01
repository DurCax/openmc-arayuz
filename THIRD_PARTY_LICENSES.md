# Üçüncü taraf lisansları / Third-party licenses

Bu yazılımın kendisi özel mülktür (`LICENSE`: tüm hakları saklıdır). Aşağıdaki bileşenler
**kendi lisanslarına** tabidir; `LICENSE` bu lisansların tanıdığı hakları kısıtlamaz.
*This software itself is proprietary (`LICENSE`: all rights reserved). The components below
are governed by their own licenses; `LICENSE` does not restrict the rights they grant.*

Doğrulama yöntemi (01.10.2026): sürüm ve lisans **kurulu** paketlerden okundu —
`conda-meta/*.json` (`license` alanı), `importlib.metadata` (`License-Expression` /
`License` / sınıflandırıcı) ve paketin taşıdığı `LICENSE*` dosyası; gömülü varlıklar için
depodaki lisans dosyası; uzak depolar için GitHub API'nin lisans alanı. "Doğrulanmadı"
yazan satırın lisansı bu yollarla teyit edilemedi.

## 1. Gömülü varlıklar (depoda, değiştirilmeden)

| Bileşen | Yer | Lisans | Doğrulama |
|---|---|---|---|
| Inter 4.1 yazı tipi (Regular, Medium, SemiBold) — The Inter Project Authors | `arayuz/kaynaklar/fontlar/` | SIL Open Font License 1.1 | `fontlar/LICENSE.txt` (tam metin) |
| Lucide 1.48.0 ikonları (60 SVG) — Lucide Icons and Contributors; Feather kökenli ikonlar Cole Bemis | `arayuz/kaynaklar/ikonlar/` | ISC (Feather kökenli ikonlar MIT) | `ikonlar/LICENSE` (tam metin) |
| mit-crpg/benchmarks ICSBEP OpenMC modelleri (geometri ve atom yoğunlukları aktarıldı) | `ornekler/vv/kriter_*.json` | MIT | GitHub API `mit-crpg/benchmarks` → `MIT`; metin §5 |

Kaynak ve SHA-256: `arayuz/kaynaklar/KAYNAKLAR.txt`. Inter OFL-1.1 koşulu: yazı tipi tek
başına satılamaz; değiştirilmiş sürüm "Inter" adını taşıyamaz (burada değiştirilmedi).
ICSBEP el kitabının metni yeniden dağıtılmaz; yalnız açık model ve yayımlanmış E ± σ
kullanılır (`docs/STANDARTLAR.md` §6).

## 2. Çalışma anı bağımlılıkları (kullanıcının conda ortamına kurulur, depoda yok)

Uygulama bu paketleri **içermez**; `environment.yml` ile conda-forge'dan kurulur ve
çalışma anında içe aktarılır. Ölçülen sürümler geliştirme ortamınındır.

| Paket | Sürüm | Lisans | Doğrulama |
|---|---|---|---|
| OpenMC (MIT, UChicago Argonne LLC ve OpenMC katkıcıları) | 0.16.0 | MIT | conda-meta + `dist-info/licenses/LICENSE` |
| PySide6 / shiboken6 (Qt for Python) | 6.11.2 | LGPL-3.0-only | conda-meta + `info/licenses/LGPL-3.0-only.txt` |
| Qt 6 (qt6-main) | 6.11.2 | LGPL-3.0-only | conda-meta + `info/licenses/LGPL-3.0-only.txt` |
| Python | 3.13 | PSF-2.0 (Python-2.0) | conda-meta |
| NumPy | 2.5.3 | BSD-3-Clause (gömülü parçalar 0BSD, MIT, Zlib, CC0-1.0) | `License-Expression` |
| SciPy | 1.18.1 | BSD-3-Clause | conda-meta + `LICENSE.txt` |
| h5py | 3.16.0 | BSD-3-Clause | conda-meta + `License-Expression` |
| HDF5 | 1.14.6 | BSD-3-Clause | conda-meta |
| matplotlib | 3.11.2 | PSF tabanlı matplotlib lisansı (PSF-2.0) | conda-meta + `LICENSE` |
| pandas | 3.0.6 | BSD-3-Clause | conda-meta + `LICENSE` |
| uncertainties | 3.2.3 | BSD-3-Clause | conda-meta + `LICENSE.txt` |
| cycler | 0.12.1 | BSD-3-Clause | conda-meta |
| lxml (OpenMC bağımlılığı) | 6.1.3 | BSD-3-Clause ve MIT-CMU | conda-meta |
| endf (OpenMC bağımlılığı) | 0.1.12 | MIT | conda-meta |
| DAGMC (OpenMC derlemesinin bağımlılığı) | 3.2.4 | BSD-2-Clause | conda-meta |
| MOAB (DAGMC bağımlılığı, paylaşımlı kitaplık) | 5.6.0 | LGPL-3.0-or-later | conda-meta |
| Pillow, contourpy, fonttools, kiwisolver, pyparsing (matplotlib bağımlılıkları) | — | HPND / MIT-CMU, BSD-3-Clause, MIT, BSD, MIT | `importlib.metadata` |

Geliştirme ve çeviri araçları (yalnız geliştirici ortamında; uygulamayla dağıtılmaz):
pytest 9.1.1 (MIT), pytest-xdist 3.8.0 (MIT), pytest-cov 7.1.0 (MIT), coverage 7.16.2
(Apache-2.0), Babel 2.18.0 (BSD-3-Clause; Unicode CLDR verisi Unicode lisansı).

### 2.1 PySide6 / Qt (LGPL-3.0) uyum notu

- PySide6 ve Qt **yalnız dinamik bağlanır**: uygulama saf Python'dur ve Qt'yi çalışma
  anında `import PySide6` ile, kullanıcının ortamındaki paylaşımlı kitaplıklar (`.so`)
  üzerinden yükler. Statik bağlama, Qt kodu kopyalama ya da derlenmiş tek dosya paketleme
  (ör. PyInstaller) **yapılmaz**.
- PySide6 ve Qt **değiştirilmedi**. Kullanılan ikili paketler conda-forge'un
  (`pyside2-feedstock` ve `qt-main-feedstock` tarifleri) değiştirilmemiş derlemeleridir;
  conda-forge derleme sırasında yalnız paketleme yamaları uygular.
- Kullanıcı Qt/PySide6'yı kendi derlediği ya da başka bir uyumlu sürümle **değiştirebilir**
  (LGPL-3.0 §4): ortamda `pyside6` paketini değiştirmek yeterlidir; uygulamada buna engel
  olan bir mekanizma (imza, sürüm kilidi, şifreleme) yoktur.
- **Kaynak erişimi:** Qt kaynağı <https://download.qt.io/official_releases/qt/> (6.11.2:
  `qt-everywhere-src-6.11.2.tar.xz`), PySide6 kaynağı
  <https://code.qt.io/cgit/pyside/pyside-setup.git> (etiket `v6.11.2`). conda-forge derleme
  tarifleri ve yamaları: <https://github.com/conda-forge/pyside2-feedstock>,
  <https://github.com/conda-forge/qt-main-feedstock>. Docker imajı dağıtılırsa imajı alan
  kişi aynı kaynaklara bu bağlantılardan ulaşır; telif sahibi istendiğinde ilgili kaynak
  arşivini de sağlar.
- LGPL-3.0 tam metni: <https://www.gnu.org/licenses/lgpl-3.0.txt> (ve conda paketinde
  `info/licenses/LGPL-3.0-only.txt`).

### 2.2 GPL/AGPL denetimi

Uygulamanın doğrudan ya da Python düzeyinde içe aktardığı hiçbir paket GPL/AGPL değildir.
Ortamın conda-meta taramasında `GPL` geçen paketler ve durumları:

| Paket | Lisans | Durum |
|---|---|---|
| libgcc, libstdcxx, libgfortran, libgomp | GPL-3.0-only WITH GCC-exception-3.1 | Çalışma anı istisnası: bunlara bağlanan program GPL'e girmez |
| readline 8.3 | GPL-3.0-only | conda-forge `python` paketinin bağımlılığı (etkileşimli kabuk için `readline` modülü). Uygulama `readline`'ı içe aktarmaz; ortamın parçasıdır, uygulamayla birlikte dağıtılmaz. Docker imajında ortamla birlikte bulunur — açık nokta, aşağıya bakınız |
| ld_impl_linux-64 | GPL-3.0-only | Bağlayıcı (binutils); yalnız derleme aracı, çalışma anında kullanılmaz |
| freetype, dbus, libev | GPL-2.0 **ya da** FTL / AFL-2.1 / BSD-2-Clause (çift lisans) | İzin verici seçenek (FTL, AFL-2.1, BSD-2-Clause) geçerlidir |
| alsa-lib, cairo, fribidi, graphite2, keyutils, libglib, libiconv, libntlm, libxcrypt | LGPL-2.x | Qt'nin/sistemin paylaşımlı kitaplıkları; dinamik bağlanır, değiştirilmedi |
| MOAB, PySide6, Qt | LGPL-3.0 | §2.1 |

**Açık nokta (readline):** conda-forge `python` paketi `readline`'a (GPL-3.0) bağımlıdır.
Uygulama bu modülü kullanmaz; yalnız ortam/imaj dağıtımında söz konusudur. İmaj yalnız izin
verilen kişilere dağıtıldığından ve uygulama kodu readline'a bağlanmadığından risk düşük
görülmüştür; kesin değerlendirme hukuki görüş gerektirir.

## 3. Nükleer veri (dağıtılmaz)

| Veri | Lisans / kullanım koşulu | Doğrulama |
|---|---|---|
| ENDF/B-VIII.0 tesir kesiti kütüphanesi (OpenMC HDF5 biçimi; openmc.org/data) | ENDF/B, ABD Ulusal Nükleer Veri Merkezi (NNDC, BNL) ve CSEWG'nin yayımladığı, kamuya açık değerlendirilmiş veri kütüphanesidir; ayrı bir yazılım lisansı belgesi bulunmadı | **doğrulanmadı** (resmî kullanım koşulu metni görülmedi) |
| Tükenme zincirleri (ENDF/B-VIII.0 termal/hızlı, CASL) | OpenMC projesinin openmc.org/data üzerinden dağıttığı XML dosyaları | **doğrulanmadı** |

Veri ne depoya ne Docker imajına gömülür; kullanıcı `veri_indir.sh` ile kaynağından indirir
ya da hazır dizini bağlar. Kullanıcı verinin kaynağındaki koşullara kendisi uyar.

## 4. Doğrulanmamış / izlenecek noktalar

- ENDF/B-VIII.0 ve zincir dosyalarının resmî kullanım koşulları (§3).
- Docker taban imajı (`condaforge/miniforge3`) ve imaja `apt` ile giren Debian/Ubuntu sistem
  paketleri (X11, noVNC, websockify, x11vnc, xvfb, fluxbox) **bu tabloda yoktur**; imaj
  dağıtılırsa `docker run … dpkg-query -W` ve `/usr/share/doc/*/copyright` ile ayrıca
  listelenmelidir. x11vnc ve fluxbox GPL-2.0'dır; uygulamaya bağlanmazlar, ayrı programlar
  olarak çalışırlar (noVNC seçeneği isteğe bağlıdır).

## 5. Lisans metinleri (dosyası depoda olmayanlar)

### mit-crpg/benchmarks — MIT

```
Copyright (c) 2011-2024 Paul Romano and other contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### OpenMC — MIT

OpenMC uygulamayla dağıtılmaz (kullanıcının ortamına kurulur). Telif satırı:
`Copyright (c) 2011-2026 Massachusetts Institute of Technology, UChicago Argonne LLC, and
OpenMC contributors`; metin yukarıdaki MIT metniyle aynıdır (paket içinde
`openmc-0.16.0.dist-info/licenses/LICENSE`).
