# Örnek modeller

`ornekler/` altındaki her JSON açılabilir bir modeldir. Galeri başlığı, kategori
ve seviye dosyanın kendi meta alanlarından okunur (`baslik`, `baslik_en`,
`aciklama_en`, `kategori`, `seviye`, varsa `referans`; bkz. `cekirdek/ornek_bilgi.py`).
Kriter sonuçları ve C/E tablosu: [VV.md](VV.md).

Kaynak sütunu modelin sayılarının nereden geldiğini söyler. **"Doğrulanmadı"**
yazan değerler birincil belgeden okunmamış, tipik/açık kaynak değerlerdir;
bunlar eğitim amaçlıdır ve bir tasarım değeri gibi kullanılmamalıdır.

## Liste

| Dosya | Başlık | Kategori | Seviye | Referans | Kaynak |
|---|---|---|---|---|---|
| pwr_pinhucre.json | PWR yakıt hücresi (pin) | pwr | giriş | hesap: regresyon çıpası k∞ 1.3570 ± 0.0020 | bu aracın çıpası |
| pwr_17x17.json | PWR 17×17 yakıt demeti | pwr | giriş | — | Westinghouse tipik |
| pwr_3b.json, pwr_eksenel.json, pwr_kontrol.json | PWR demet çeşitlemeleri | pwr | orta | — | Westinghouse tipik |
| pwr_tukenme.json | PWR pin hücre — tükenme | pwr | ileri | — | — |
| **pwr_mox_demet.json** | PWR MOX demeti (3 bölgeli) | pwr | orta | — | OECD/NEA–US NRC PWR MOX/UO2 kor geçiş kriteri (2003), "MOX 4.3%" demeti |
| **pwr_gd_tukenme.json** | Gd'li çubukta tükenme | pwr | ileri | — | Westinghouse ölçüleri; Gd2O3 bileşimi tipik (doğrulanmadı) |
| **pwr_smr_kor.json** | Kare SMR tam koru (52 demet) | pwr | orta | — | eğitim tasarımı |
| **pwr_ceyrek_kor.json** | Çeyrek simetrik PWR koru | pwr | ileri | — | pwr_smr_kor'un çeyreği |
| **pwr_beavrs_kor.json** | BEAVRS benzeri PWR koru (193 demet) | pwr | ileri | — (basitleştirilmiş) | MIT BEAVRS, 1. çevrim HZP ARO |
| **bwr_10x10.json** | BWR 10×10 demeti (su kanallı) | bwr | orta | — | ATRIUM-10 benzeri, açık kaynak ölçüler (doğrulanmadı) |
| **vver1000_demet.json** | VVER-1000 demeti (Gd'li) | vver | orta | — | NEA/NSC/DOC(2002)10 yerleşimi + TVS-2M/TVSA pin ölçüleri (doğrulanmadı) |
| **vver1000_kor.json** | VVER-1000 tam koru (163 demet) | vver | ileri | — | 163 demet düzeni; yükleme eğitim amaçlı |
| sfr_altigen.json | SFR altıgen demet | sfr | orta | — | tipik |
| **sfr_met1000_demet.json** | SFR metal yakıt demeti (MET-1000) | sfr | orta | — | NEA/NSC/R(2015)9 Tablo 2.16–2.22 |
| **sfr_met1000_kor.json** | SFR tam koru (MET-1000) | sfr | ileri | hesap: 1.0355 ± 0.0078 | NEA/NSC/R(2015)9 |
| mtr_plaka.json | MTR plaka yakıt elemanı | araştırma | orta | — | tipik U3Si2 MTR |
| **mtr_kor.json** | MTR araştırma reaktörü koru | araştırma | orta | — | IAEA 10 MW MTR kriterinden esinlenmiş (aynısı değil) |
| tamburlu_kor.json | Tamburlu kompakt kor | araştırma | ileri | — | — |
| godiva_kriter.json | Godiva kritik küresi | kriter | giriş | deney: ICSBEP HEU-MET-FAST-001 | ICSBEP |
| **kriter_jezebel.json** | Jezebel plütonyum küresi | kriter | giriş | deney: ICSBEP PU-MET-FAST-001 | ICSBEP |
| **kriter_flattop25.json** | Flattop-25 yansıtıcılı küre | kriter | orta | deney: ICSBEP HEU-MET-FAST-028 | ICSBEP |
| **kriter_lct008.json** | B&W kritik kafesi (LCT-008) | kriter | ileri | deney: ICSBEP LEU-COMP-THERM-008/1 | ICSBEP |
| **kriter_vver1000_ugd.json** | VVER-1000 LEU demet kriteri (NEA) | kriter | ileri | hesap: NEA/NSC/DOC(2002)10 | NEA/NSC/DOC(2002)10 |
| zirh_kure.json | Zırh küresi (sabit kaynak) | zırh | orta | — | — |
| **zirh_katmanli.json** | Katmanlı zırh (sabit kaynak) | zırh | orta | — | PNNL-15870 beton; Cf-252 Watt değerleri (doğrulanmadı) |

Kalın dosyalar Dalga 2'de eklendi (16 dosya). "deney" referansı ölçülmüş bir
kritik düzenektir (C/E); "hesap" referansı başka kodların hesabıdır.

## Örnek ayrıntıları

### VVER-1000 demeti ve koru

- Demet: 331 konum = 300 UO2 %3.7 + 12 TVEG (UO2 %3.6 + %4 Gd2O3) + 18 kılavuz
  kanal + 1 merkez borusu; 11 halka, pin adımı 1.275 cm, demet adımı 23.6 cm,
  **kılıf (wrapper) yok**. Gd ve kılavuz kanal konumları NEA/NSC/DOC(2002)10
  Şekil A.1 kartogramından okundu ve 60° dönme simetrisi denetlendi.
- Pin: pelet dış r 0.3785, merkez deliği r 0.07, kılıf iç/dış r 0.386/0.455 cm
  (He boşluğu). Bu değerler TVS-2M/TVSA için yaygın verilen açık kaynak
  değerleridir, birincil tasarım belgesinden **doğrulanmadı**. NEA kriteri
  (kriter_vver1000_ugd.json) kendi basitleştirilmiş pin'ini kullanır: yakıt
  r 0.386, kılıf dış 0.4582, delik ve boşluk yok.
- Demetler arası su: çekirdekte kılıfsız tek altıgen demetin sınırı pin zarfıdır
  (23.358 cm). 23.6 cm'lik kabı kurmak için demete **moderatörle aynı malzemeden
  0.01 cm kalınlıkta** bir "kılıf" konur; fiziksel olarak kılıfsız demettir.
  Doğrulayıcının "kılıflı tek demet" uyarısı bu yüzden görünür ve yanlış
  alarmdır (bkz. "Çekirdekte gereken değişiklikler").
- Kor: 8 halkalı altıgen kor kafesi (169 konum); dış halkanın 6 köşesi çelik-su
  yansıtıcıdır → 163 demet (test: testler/test_ornekler.py OR2). Kor kafesi 'x',
  demet pin kafesi 'y'. Üç demet türü (A %2.0 Gd'siz, B %3.0 + TVEG, C %4.4 +
  TVEG dış halka). Radyal yansıtıcı 20 cm çelik %80 + su %20 homojen;
  yükleme deseni gerçek bir VVER-1000 haritası değildir.

### SFR MET-1000 (NEA/NSC/R(2015)9)

- Sürücü demeti: 271 pin (10 halka), yakıt r 0.3236, HT-9 kılıf dış r 0.3857 cm,
  zarf dış 15.8123 cm / duvar 0.3966 cm, demet adımı 16.2471 cm.
- **Tel sarımı:** spesifikasyon teli kılıfa homojenleştirir (kılıf dış yarıçapı
  büyütülmüştür). Model aynı yolu izler; kütle korunumu aktif bölge hacim
  kesirleriyle sınanır: yakıt 39.00, HT-9 25.66, Na 35.34 % (Tablo 2.20;
  test OR4).
- Pin adımı spesifikasyonda **verilmez**; hacim kesirleri adımdan bağımsızdır.
  Pin kafesi zarfın iç yüzüne tam oturacak biçimde p = 0.90539 cm seçildi.
- Kor: 379 konum (78 iç + 102 dış sürücü, 114 yansıtıcı, 66 kalkan, 15 + 4
  kontrol), Şekil 2.7 görüntüsünden renk örneklemesiyle çıkarıldı; bütün sayılar
  lejantla tutar (test OR5). 11 eksenel katman (alt yapı, alt yansıtıcı, 5 aktif
  dilim, bağ sodyumu, plenum ×2, üst yapı; toplam 480.20 cm). Aktif bölge dışı ve
  yansıtıcı/kalkan/kontrol demetleri Tablo 2.20 kesirleriyle homojendir.
  Kontrol çubukları tam çekilmiş; soğurucu aktif korun hemen üstünde.
- Tek demet örneği 1 halkalı altıgen kor kafesi (halka_sayisi = 1) ile kurulur;
  demetler arası sodyum boşluğu modeldedir.

### BEAVRS benzeri kor

193 adet 17×17 demet, üç zenginlik (%1.6: 65, %2.4: 64, %3.1: 64), Pyrex
yerleşimi ve bütün pin ölçüleri MIT BEAVRS OpenMC modelinden (models/openmc/beavrs).
BEAVRS OpenMC modelindeki yerleşim **1268** Pyrex çubuğu verir; spesifikasyon
tablosu 1266 der — fark doğrulanamadı. Izgara, nozul, çelik perde (baffle), kor
fıçısı, nötron kalkanı ve basınç kabı **yoktur**; bu yüzden ölçülen kritik bor
(975 ppm) bu model için referans değildir. Çok türlü güç dağılımı
(`guc_dagilimi.cubuklar`, Ajan 8b) birleşince üç yakıt türünü birlikte sayar;
test OR10 o zamana kadar ÖN_KOŞUL ile atlanır.

### Çeyrek simetrik kor (ve yükleme deseninin ayna simetrisi)

Simetri düzlemi **yansıtıcı** sınırla kurulur: çözülen model, çeyreğin iki eksende
**aynalanmasıyla** oluşan kordur. Bunun bir sonucu var ve ilk denemede bu yüzden
yanlış sonuç alındı:

> **Dama (checkerboard) deseninin 180° dönme simetrisi vardır ama AYNA simetrisi
> yoktur.** Çeyreği aynalayınca komşu çeyreklerde A/B desen yer değiştirir, yani
> çeyrek kor modeli *başka bir yükleme* çözer. Ölçüldü: aynı yan sınırla bile
> çeyrek ile tam kor arasında **+260 pcm** fark. Bu yüzden `pwr_smr_kor.json`
> yüklemesi eş merkezli kuşaklara (B = %3.1 dış, A = %2.4 iç) çevrildi.
> `testler/test_ornekler.py` OR9 çeyreğin aynasını tam korun haritasıyla
> karşılaştırır — Monte Carlo'suz, bedava bir denetim.

Geriye kalan fark yan sınır koşulundan gelir: çekirdek korun **dört yan yüzüne
tek bir** sınır koşulu uygular, yüz başına ayrı koşul yoktur. Çeyrek korun dış
iki yüzü de bu yüzden yansıtıcıdır (85.7 cm su ile ayrılmış sonsuz kor dizisi).
Ölçülen etki: tam kor, aynı geometri, yalnız yan sınır vakum → yansıtıcı
**+89 pcm** (1.08439 ± 0.00064 → 1.08528 ± 0.00073). Bu yüzden:

- Mutlak k için **tam koru** kullanın.
- Çeyrek kor ~4 kat hızlıdır; göreli karşılaştırmalar (çubuk değeri, güç şekli)
  için uygundur.
- YAVAS test OR12 iki modeli **aynı yan sınırla** karşılaştırır.

### Diğerleri

- **pwr_mox_demet:** fisil Pu yüzdesi (2.5/3.0/5.0) ağır metale göre ağırlıkça
  fisil Pu (Pu-239 + Pu-241) olarak yorumlandı; kriter bor değeri vermediği için
  borsuz HZP (560 K).
- **pwr_gd_tukenme:** tek Gd'li pin hücresi temsil edici değildir (sonsuz Gd
  kafesi); 5×5 süper hücrenin merkezindeki Gd'li pelet eşit alanlı 5 halkaya
  bölünür. Ölçülen (OR13, 5 MWd/kg): kalan Gd-157 oranı içten dışa
  0.79 / 0.71 / 0.58 / 0.30 / 0.01 — uzaysal öz-perdeleme ("soğan kabuğu")
  açıkça görünür; 16 MWd/kg'da iç halkada hâlâ ~%12 Gd-157 kalır.
  **k∞ bu modelde tepe yapmaz:** 25 çubuktan yalnız biri Gd'li olduğu için
  reaktivite tutması zayıftır ve yakıt tükenmesi baskındır. Gerçek bir demette
  (12–20 Gd'li çubuk) tepe görülür.
- **bwr_10x10:** su kanalı duvarı yok; kutu duvarı + bypass suyu 1.145 cm'lik
  homojen kuşak.
- **mtr_kor:** çekirdeğin plaka elemanı sonlu bir kutudur ve kor kafesi kare
  adımlıdır; eleman kareye tamamlanır (yan levha 0.7105 cm, elemanlar arası su
  yok).
- **zirh_katmanli:** nötron taşınımı; betondaki hidrojen için c_H_in_H2O
  (yaygın yaklaşım).

## Hassasiyet ve koşu süreleri

Tam korlar **"Hızlı deneme"** (1000 parçacık × 60 çevrim, 20 pasif) ile açılır;
Hesap ayarlarından "Normal"e geçilebilir. Ölçülen "Normal" (10000 × 150/40)
süreleri, 8 iş parçacığı, makine başka koşularla paylaşılırken:

| Dosya | Normal süre [s] | k (Normal) |
|---|---|---|
| vver1000_kor.json | 66.1 | 1.09907 ± 0.00097 |
| sfr_met1000_kor.json | 281.5 | 1.03014 ± 0.00053 |
| pwr_beavrs_kor.json | 104.5 | 1.00187 ± 0.00093 |
| pwr_smr_kor.json | 82.9 | 1.08345 ± 0.00092 |
| pwr_ceyrek_kor.json | 76.7 | 1.08778 ± 0.00097 |
| mtr_kor.json | 114.1 | 1.16884 ± 0.00095 (30.09, U3Si2-Al düzeltmesi sonrası; önce 1.16743 ± 0.00098) |

Tam korlarda "Normal" ayarın 40 pasif çevrimi kaynak yakınsaması için sınırdadır
(Shannon entropisi hâlâ düşüyordu); k karşılaştırması yapacaksanız pasif çevrimi
artırın (YAVAS test OR12 20000 × 160/60 kullanır). Çeyrek ile tam korun
karşılaştırılması için yukarıdaki "Çeyrek simetrik kor" bölümüne bakın.

Hepsi 15 dakikanın altındadır.

**İleri ayar (belgelenmiş, varsayılan değil):** güç haritası için ≥ 10–20
eksenel dilim ("guc_dagilimi.eksenel_dilim") ve ≥ 5 tohum (Hesap ayarları >
çoklu tohum). Tam korda pin gücü istatistiği için en az 50000 parçacık × 300
çevrim önerilir; süre "Normal"in yaklaşık 10 katıdır.

## Çekirdekte gereken değişiklikler (bu örneklerin ortaya çıkardığı)

- Kılıfsız tek altıgen demette demet adımı (hücre) pin zarfından büyük
  olamıyor; su-"kılıf" hilesi gerekiyor.
- Kor yan yüzü başına ayrı sınır koşulu yok (çeyrek kor su tamponuyla kuruluyor).
- Plaka elemanı sonlu kutu; kor kafesinde eleman dışı tanımsız kalıyor (kafes
  adımı eleman ölçüsüne eşit ve kare olmak zorunda).
- `sema.kullanilan_malzemeler` harita/katman anahtarlarındaki malzeme adlarını
  saymıyor → bu malzemeler için yanlış "kullanılmayan malzeme" bilgisi.
