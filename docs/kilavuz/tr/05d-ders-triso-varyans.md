<a id="ders-triso-varyans"></a>
## 5.21 TRISO yakıt ve ağırlık pencereleriyle zırh hesabı

**Örnek dosyalar:** `ornekler/htgr_kompakt.json`, `ornekler/htgr_pebble.json`,
`ornekler/zirh_agirlik_pencere.json` · **Seviye:** ileri · **Tahmini süre:** 40 dakika (koşular
toplam ~10 dakika, 6 iş parçacığı) · **Başvuru:** [TRISO kartı](04b-parcalar.md#triso),
[Varyans azaltma](04f-hesap-ayarlari.md#ayar-varyans), [Verimlilik (FOM) kartı](04g-calistir.md#calistir-fom)

**Amaç.** İki ayrı Monte Carlo sorusunu aynı araçla yanıtlamak: (1) binlerce TRISO parçacığı olan bir
yakıt gövdesi nasıl modellenir, **paketleme oranı** hedefe tutuyor mu ve parçacıkların **rastgele ya da
düzenli** yerleştirilmesi k'yı değiştirir mi; (2) derin nüfuz eden bir zırh problemini **ağırlık
pencereleriyle** nasıl hızlandırırız ve sonucun **yanlılıksız** kaldığını nasıl gösteririz.

**Ön koşul.** [5.5 Tambur](05-dersler.md#ders-tambur) (gelişmiş geometride bileşen kullanımı) ve
[5.16 Zırh örneği](05d-ders-foton-sicaklik-yuzey.md#ders-foton-sicaklik-yuzey) (sabit kaynak).

### A. TRISO kompakt ve paketleme oranı

1. `ornekler/htgr_kompakt.json`'u açın (kopya olarak açılır). **Parçalar** › **TRISO** listesinden
   `agr1_kompakt`'ı seçin. Katmanlar INL AGR-1 taban tasarımıdır: çekirdek (UCO) çapı 350 µm, tampon
   100, IPyC 40, SiC 35, OPyC 40 µm (dış yarıçaplar 0.0175, 0.0275, 0.0315, 0.0350, 0.0390 cm);
   kompakt yarıçapı 0.6225 cm; model, z'de yansıtıcı sınırlı **5 mm'lik dilimdir** (eksenel sonsuz
   kompakt; uzunluk k'yı değiştirmez, dilim kurulumu hızlandırır).
2. Özet satırı **857 parçacık · gerçek paketleme oranı 0.3498 (hedef 0.3500)** yazar. **El
   hesabı:** V_kap = π·0.6225²·0.5 = 0.6086 cm³, V_p = (4/3)π·0.039³ = 2.485·10⁻⁴ cm³,
   N = int(0.35·0.6086 / 2.485·10⁻⁴) = 857, gerçek oran = 857·V_p / V_kap = 0.3498.
3. **Doğrulama** koşuyu açmadan modeli denetler: kompakt 3B ister (kökte yükseklik var), malzemeler
   tanımlı, paketleme ≤ 0.64. Paketleme 0.30'u aşınca **yakın rastgele paketleme (CRP)** uyarısı
   çıkar; bu beklenir, kurulum yavaşlar.
4. **Geometri** sayfasında kesiti çizin: önizleme parçacıkları gösterir. Betik (**Dosya › Python
   betiği**) `openmc.model.pack_spheres(...)` ve `openmc.model.create_triso_lattice(...)` satırlarını
   yazar; betik ve arayüz aynı tohumla aynı parçacık merkezlerini kurar
   (`testler/test_y9_triso.py`).
5. **Çalıştır** (4 000 × 60 / 15). k_eff bu modelde bir **eğitim örneği** değeridir (tek kompakt hücresi,
   helyum kanalı yok; gerçek HTGR bloğu değildir).

**Paketleme oranı hedefe tutuyor mu?** Rastgele yerleşimde N = int(pf·V/V_p) olduğundan oran
hedefe 1/N kadar yakındır (857 parçacıkta ≤ %0.12). Test, kurulmuş OpenMC modelindeki **kafes
hücrelerinden TRISO'ları sayarak** (aynı parçacığın birden çok kafes hücresindeki kopyaları tekilleştirilerek)
oranı yeniden hesaplar ve hedefe **±%1** içinde olduğunu, parçacıkların üst üste binmediğini
(en yakın merkez uzaklığı ≥ 2r) ve kabın içinde kaldığını doğrular.

### B. Kafes yaklaşımı: rastgele ve düzenli yerleşim

**Yerleşim** kutusunu **Düzenli (basit kübik)** yapın (pf = 0.30; kübik kafesin sınırı π/6 = 0.5236).
Düzenli kafeste sayı basamaklıdır; adım, hedef sayıya en yakın sayıyı verecek şekilde taranır ve **gerçek**
oran özet satırında yazılır (hedeften sapma %1'i aşarsa doğrulama uyarır).

**Ölçülen** (`testler/test_y9_triso.py::test_yavas_duzenli_ve_rastgele_yerlesimin_k_farki`, pf = 0.30,
5 000 × 50 / 15, ENDF/B-VIII.0, OpenMC 0.16):

| Yerleşim | k_eff ± σ |
|---|---|
| rastgele, tohum 1 | 1.37298 ± 0.00235 |
| rastgele, tohum 2 | 1.37521 ± 0.00250 |
| rastgele, tohum 3 | 1.36884 ± 0.00242 |
| düzenli (basit kübik) | 1.36965 ± 0.00233 |

Sonuç: **düzenli kafes rastgele ortalamasından −269 pcm uzaktır (rastgele tohumların ortalaması 1.37234; fark ≈ 0.9 birleşik σ); bu kesinlikte **anlamlı bir fark ölçülmedi**, tohumlar arası yayılım (636 pcm) farkın kendisinden büyüktür. Daha küçük bir etkiyi görmek için çok daha fazla geçmiş gerekir.** Bu bir modelleme yaklaşımı farkıdır: düzenli kafes parçacıkların birbirini
gölgelemesini (kendini koruma, rezonans soğurması) rastgele paketlemeden farklı hesaplar; gerçek
yakıt rastgele paketlidir, düzenli kafes bir **yaklaşımdır** ve hız ya da basitlik için seçilir.

### C. Pebble (HTR-10)

`ornekler/htgr_pebble.json`'u açın. Parçacık: UO₂ çekirdek çapı 500 µm, tampon 90, IPyC 40, SiC 35,
OPyC 40 µm; yakıt küresi yarıçapı 2.5 cm (**≈ 8335 parçacık**, paketleme ≈ %5.0; IAEA-TECDOC-1382),
0.5 cm grafit kabuk, çevresinde yatağın 0.61 paketlemesine denk gelen **Wigner–Seitz** helyum
kabuğu (hücre yarıçapı 3.54 cm) ve yansıtıcı sınır: sonsuz yatağın **kuresel hücre yaklaşımı**.
Yatağın gerçek k∞'u değildir. Pebble kuredir; 3B model şartı yoktur. Kapta kalan hacim matris
ile dolar; UO₂ hacmi = N·(4/3)π·0.025³ (test, gezintiyle 10⁻⁹ bağıl farkla doğrular).

### D. Zırh: ağırlık pencereleri

Derin nüfuz eden problemde analog Monte Carlo dedektöre çok az parçacık ulaştırır.
`ornekler/zirh_agirlik_pencere.json`'u açın: merkezde 14.1 MeV D-T nokta kaynağı, 35 cm su, 40 cm
çelik, 30 cm su ve en dışta 5 cm **dedektör suyu** (suyla aynı bileşim, ayrı ad); tally dedektör
malzemesindeki akıdır.

1. **Analog koşu.** Varyans azaltma kapalıyken **Çalıştır** (20 000 × 100 = 2·10⁶ geçmiş).
   **Verimlilik (FOM)** kartında `aki_dedektor` için toplam, σ bağıl ve FOM görünür.
2. **Pencere üret.** **Hesap ayarları › Gelişmiş › Varyans azaltma**: işaretleyin, **Mod = Pencere
   üret**, **Ağ türü = Küresel**, **Ağ boyutu = 8 × 1 × 1**, **En çok gerçekleşme = 40**; 20 000 × 40
   ile **Çalıştır**. Koşu analog taşır; koşu dizinine `weight_windows.h5` yazılır.
3. **Pencereyi uygula.** **Mod = Hazır pencere dosyasını uygula**, **Son koşudan al**; 1 000 × 20 ile
   **Çalıştır**.

**Ölçülen** (2 000 000 analog geçmiş; 20 000 pencereli geçmiş; 6 iş parçacığı; kaynak: bu depodaki
`testler/test_y9_varyans.py`):

| Koşu | Geçmiş | T [s] | dedektör akısı ± σ [1/s] | σ bağıl | FOM |
|---|---|---|---|---|---|
| analog | 2·10⁶ | 62 | 1.687·10⁹ ± 0.164·10⁹ | %9.8 | 1.69 |
| MAGIC pencereli (küresel, 8 bölme) | 2·10⁴ | 109 | 1.597·10⁹ ± 0.066·10⁹ | %4.1 | 5.37 |

- **Yanlılıksızlık:** pencereli sonuç analogla **0.51 σ** (birleşik) farkla uyumludur; kabul
  ölçütü ≤ 2σ.
- **FOM artışı:** **≈ 3.2 ×** (üretim koşusunun süresi hariç; üretim koşusu analog bir koşudur ve
  süresi ayrıca eklenmelidir). Eşik değil ölçümdür: sayı problemin derinliğine bağlıdır.

**Ağırlık pencereleri her problemde kazandırmaz.** Aynı hesabı daha ince bir zırhta (35 cm su, 20 cm
çelik, 30 cm su, dedektör 5 cm; çıkış yarıçapı 90 cm) ölçtük: analog 10⁶ geçmişte %4 bağıl hata verdi
(FOM ≈ 14); aynı pencereyle FOM 1.4–4.6 çıktı. Derin zırhta (yukarıdaki) analog yalnızca %10 hata
verdi ve FOM'u 1.7 idi. Yani pencere, **analog yöntemin kötü olduğu** derinlikte işe yarar;
ince zırhta bölünen parçacıkların maliyeti kazancı aşar. Ayrıca ağın seçimi önemlidir: 18³ düzenli
ağda 5 832 hücrenin 3 924'ü (%67) hiç pencere almadı; 8 bölmeli küresel ağda hepsi aldı. Az geçmişle
("üret ve aynı koşuda uygula", 2 000 × 60) pencere hiç oluşmadı ve sonuç analogla bit düzeyinde aynı
çıktı.

**Kapsam notu.** **FW-CADIS** (`method='fw_cadis'`) OpenMC 0.16'da vardır ancak random ray
**adjoint** çözümü ister; bu sürümde arayüzde yoktur. wwinp dosyası **yüklenir**
(`WeightWindowsList.from_wwinp`) ama OpenMC 0.16 wwinp **dışa aktarmaz**.

**Sertifika değildir.** Sayılar, bu depodaki test koşusunun ölçümleridir; kendi zırhınız için aynı
yanlılık denetimini (analog ile ≤ 2σ) yinelemeden pencereye güvenmeyin.
