<a id="mgxs"></a>
### Grup sabitleri ve random ray kartı

**Analiz** sayfasının en altındaki **Grup sabitleri ve random ray** kartı, sürekli enerji (CE)
Monte Carlo koşusundan **akı ağırlıklı çok gruplu tesir kesitleri** (grup sabitleri) üretir
(`openmc.mgxs`), bunları OpenMC'nin çok gruplu (MG) kütüphanesine (`mgxs.h5`) yazar ve aynı
geometriyi **çok gruplu Monte Carlo** ile ve **random ray** çözücüsüyle yeniden koşup sonuçları CE
ile karşılaştırır. Üç koşu da [koşu kuyruğunda](04j-is-akisi.md#is-akisi) sırayla çalışır;
kart koşu sırasında da kullanılabilir. Adım adım kullanım: [5.19 Ders](05d-ders-mgxs.md#ders-mgxs).

Bu bir **eğitim ve karşılaştırma** aracıdır: üretilen sabitler bir çekirdek simülatörüne girdi
olarak doğrulanmış değildir (sertifika değildir).

**Tanımlar** (OpenMC 0.16 `openmc.mgxs`; Stacey, *Nuclear Reactor Physics*, 2007, bölüm 4 ve 13).
V bölge, g enerji grubu (g = 1 en yüksek enerji), φ skaler akı:

    Σx,g   = ∫V ∫g Σx(r,E) φ(r,E) dE dV  /  ∫V ∫g φ(r,E) dE dV      (akı ağırlıklı)
    χg     = ∫g' νΣf φ χ(E'→g)  /  ∫ νΣf φ                           (ν-fisyon ağırlıklı, Σχg = 1)
    Σs(g→g') : g'den g'ye saçılma; ν-saçılma matrisi (n,xn) çoğalmasını da sayar

- **Tutarlı saçılma matrisi** (`consistent scatter matrix`): matris, iz uzunluğu tahmincisiyle
  ölçülen Σs,g ile analog olasılık matrisinin çarpımıdır; böylece Σt,g − Σg' Σs(g→g') = Σa,g
  aynı geçmişlerden tutarlı çıkar. Basit (analog) matrisle bu fark iki büyük ve gürültülü
  sayının farkı olurdu (ölçüldü: 4 × 10⁵ geçmişte 2 grup k∞ 950 pcm kaydı).
- **Taşıma düzeltmesi P0** (out-scatter yaklaşımı): Σtr,g = Σt,g − Σs1,g (Σs1,g: g grubundan
  çıkan P1 saçılma momenti) ve matrisin köşegeni aynı Σs1,g kadar azaltılır. Kaldırma
  Σt − Σs(g→g) değişmez, yani **sonsuz ortam k∞'u düzeltmeden bağımsızdır**; değişen sızıntıdır
  (D = 1/3Σtr). **Yok** seçeneği izotropik saçılma varsayar ve Σt kullanır.
- **Sınır**: homojenleştirme yalnız sonsuz ortamda (yansıtıcı sınırlı tek demet/pin)
  kesindir. Sızıntılı bir modelde bölge sabitleri o modelin akı tayfına özgüdür.

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Kapsam** | **Tüm model** ya da (kor modellerinde) **Demet: ad** — seçili demetin yansıtıcı sınırlı 2B alt modeli (sonsuz kafes; [K5 alt modeli](04c-demet.md#demet)). Demet başına homojenleştirme bu alt modelde yapılır. | — | tek demet/pin modelde yalnız tüm model | Kor modelinde "tüm model + Demet bölgesi" seçip demet sabiti sanmak: bu, korun tamamının tek bölge ortalamasıdır. | (spec'e yazılmaz) |
| **Bölge türü** | **Malzeme**: her malzeme bir bölge (`domain_type = material`). **Hücre**: her malzemeli hücre bir bölge (`cell`; kafeste tekrarlanan hücrenin bütün örnekleri bir bölgedir). **Demet (tüm model, tek bölge)**: kök evren tek bölge (`universe`) — 2–8 grup demet sabitleri ve G×G k∞ yalnız bunda hesaplanır. | — | homojenleştirme: Demet; MG koşusu: Malzeme | Malzeme bölgesinde k∞ özdeğeri beklemek: birden çok bölgede yalnız reaksiyon hızı oranı verilir. | `ayarlar.mgxs.bolge` |
| **Grup yapısı** | `openmc.mgxs.GROUP_STRUCTURES` adları: CASMO-2/4/8/16/25/40/70, XMAS-172. 2 grupta sınır 0.625 eV. | grup | demet sabiti: 2–8; MG koşusu: ≥ 70 | 2 grupla "aynı geometri MG koşusu" yapıp büyük farkı yönteme bağlamak: fark grup yoğunlaştırmasıdır. | `ayarlar.mgxs.grup_yapisi` |
| **Taşıma düzeltmesi** | **Yok** (izotropik saçılma, Σt) ya da **P0** (Σtr, köşegen düzeltmesi). | — | Yok | İnce grupta P0 ile MG Monte Carlo koşmak: köşegen negatif olur ve MG MC bunu işleyemez (ölçüldü: pin hücre CASMO-70'te −7600 pcm). Kart bunu sonuç notunda yazar; random ray köşegen kararlılaştırması uygular ve doğru kalır. | `ayarlar.mgxs.duzeltme` (`yok` \| `P0`) |
| **Ek türler** | Zorunlulara ek: fisyon Σf, κ-fisyon κΣf, yakalama Σc, ters hız 1/v, difüzyon katsayısı D. Σt, Σa, νΣf, χ ve tutarlı (ν-)saçılma matrisleri her zaman üretilir (MG kütüphanesi için gerekli; P0'da ayrıca ν-taşıma). | — | boş | — | `ayarlar.mgxs.turler` |
| **Random ray ayarları** (gelişmiş) | **Çevrim başına ışın**, **Çevrim / pasif**, **Ölü / aktif mesafe** (ışının tally'lenmeyen ve tally'lenen yolu), **Kaynak şekli** (düz, doğrusal, yalnız x-y doğrusal), **Kaynak bölgesi bölmesi** (kaynak bölgelerini N×N kare ağla böler; 0 = yok). Grup sabitleri üretilince modelden doldurulur: L = max(sınır kutusu köşegeni, 30 cm), ölü = L, aktif = 5L (OpenMC `convert_to_random_ray` kuralı), bölme yok, 200 ışın × 500 çevrim, 300 pasif. Pin hücrede bölme 0 / 13 × 13 / 26 × 26 aynı k'yı verdi (1.3574 / 1.3569 / 1.3569 ± 0.0005; 20 / 83 / 120 s). | ışın, çevrim, cm | pin hücre: 200 ışın, bölme yok; büyük düz bölgede (yansıtıcı) bölme ya da doğrusal kaynak | Pasif çevrimi kısaltmak: random ray her çevrimde **tek** kaynak yinelemesi yapar; sudaki termal grupta yakınsama ~0.93ⁿ hızındadır (ölçüldü: 150 pasifte homojen ortamda 24 pcm sapma, 300'de < 1 pcm). | (spec'e yazılmaz) |
| **Grup sabitlerini üret** | CE koşusu (modelin **Hesap ayarları** parçacık/çevrim sayılarıyla) + kütüphane. Kopya spec'e `ayarlar.mgxs` yazılır; projeniz değişmez. Koşu dizini `<koşu tabanı>/mgxs_ce`. | — | — | — | — |
| **MG ile yeniden koş** | Aynı geometri, her bölge `mgxs.h5`'teki makroskopik veriye bağlı (OpenMC `convert_to_multigroup` ile aynı yol); tally'ler kaldırılır, sıcaklıklar silinir (kütüphane 294 K). Dizin `mgxs_mg`. | — | — | — | — |
| **Random ray ile koş** | Aynı `mgxs.h5`, `settings.random_ray`; yalnız özdeğer hesabı. Dizin `mgxs_rr`. | — | — | — | — |
| **CSV kaydet…** | `mgxs.csv` kopyası: bölge, xsdata adı, tür, grup, giden grup, değer, σ, bağıl σ. | — | — | — | — |
| **Gösterilen tür** | Tabloyu bir türe süzer. Tablo en çok 5000 satır gösterir; tamamı CSV'dedir. | — | Hepsi | — | — |

**Sonuç alanı.** Özet satırları:

- **CE k**: MGXS koşusunun k'sı.
- **Sabitlerden k = Σ νΣf·φ / Σ Σa·φ** (bütün bölgeler ve gruplar): (n,xn) net üretimini
  içermez; CE k'dan bu kadar düşük çıkar (pin hücrede ölçülen −170 pcm).
- **Sonsuz ortam k∞ (G×G özdeğer)**: yalnız tek bölgede. M φ = (1/k) χ νΣfᵀ φ, M = diag(Σt) −
  νSᵀ (yukarı saçılma ve (n,xn) dahil); 2 grupta 2 × 2 problemdir. Random ray aynı denklemi
  çözer: homojen ortamda düz kaynak kesin olduğundan random ray k'sı bu özdeğere eşittir
  (testle denetlenir).
- **Belirsizlik**: tablodaki σ'lar OpenMC'nin istatistik sapmasıdır (1σ). k tahminlerinin σ'sı
  **birinci derece ve bağımsızlık varsayımlıdır**: aynı geçmişlerden gelen tally'ler ilişkilidir,
  bu yüzden σ yaklaşık bir büyüklüktür (pin hücrede CE σ'sının 2–5 katı çıkar). Özdeğerin σ'sı
  kaldırma biçiminden (Σa + dışarı saçılma) yayılır; Σt − Σs(g→g) iki büyük ilişkili sayının
  farkı olduğundan doğrudan yayılmaz.
- Notlar: negatif köşegen (P0) ve hesaplanamayan k.

**Karşılaştırma tablosu.** Satırlar CE, MG MC, random ray: k ± σ, **Δk CE'ye** = (k − k_CE) ×
10⁵ pcm ve ± (koşular bağımsız: σ'ların karekök toplamı), random ray için **Δk MG'ye** (aynı
`mgxs.h5`: yalnız yöntem farkı) ve koşu süresi.

**Ölçülen değerler** (`ornekler/pwr_pinhucre.json`, 10 000 parçacık × 40 aktif çevrim,
ENDF/B-VIII.0, 6 iş parçacığı; `testler/test_y8_kosu.py`):

| Durum | k | Fark | Kabul eşiği ve gerekçesi |
|---|---|---|---|
| CE (MGXS koşusu) | 1.35817 ± 0.00153 | — | — |
| 2 grup, Demet: G×G k∞ | 1.35891 | +74 pcm | ≤ 4σ_CE: aynı geçmişlerden farklı bir tahminci; homojen sonsuz ortamda akı ağırlıklı sabitler reaksiyon hızlarını korur |
| 2 grup, Demet: MG MC | 1.35911 ± 0.00067 | k∞'a +20 pcm | ≤ 3σ_MG |
| 2 grup, Demet: random ray | 1.35891 | k∞'a < 1 pcm | ≤ 10 pcm (homojen ortamda düz kaynak kesin) |
| CASMO-70, Malzeme, düzeltme yok: MG MC | 1.3575 ± 0.0010 | −66 ± 181 pcm | ≤ 500 pcm: ince grupta beklenen yöntem hatası (bölge içi homojenleştirme, grup yoğunlaştırma, izotropik saçılma) birkaç yüz pcm'dir; 500 pcm bu beklentiyi ve bu istatistikteki birleşik σ'nın (~180 pcm) yaklaşık 3 katını kapsar |
| CASMO-70, Malzeme: random ray (bölme yok, düz) | 1.3574 ± 0.0005 | MG'ye −10 pcm (13 × 13'te −57) | ≤ 300 pcm: düz kaynağın uzay ayrıklaştırma hatası ve MG MC'nin σ'sı (~100 pcm; birleşik ~110 pcm'in ≈ 3 katı) |
| CASMO-70, Malzeme, P0: MG MC | 1.2822 ± 0.0014 | −7600 pcm | negatif köşegen: geçersiz (uyarı notu) |
| CASMO-70, Malzeme, P0: random ray | 1.35695 ± 0.00035 | −122 pcm | köşegen kararlılaştırması |

Süreler (aynı koşular): CE + MGXS 27 s (70 grup), MG MC 11 s, random ray 20 s (bölme yok) – 83 s
(13 × 13), 200 ışın × 500 çevrim. Random ray bu küçük problemde hızlı değildir; avantajı büyük, optik olarak kalın
problemlerde ve sabit kaynakta belirginleşir.

**Çıktı dosyaları** (`mgxs_ce/`): `mgxs.h5` (OpenMC MG kütüphanesi, xsdata adları `m<kimlik>_<ad>`,
`c<kimlik>_<ad>`, `u<kimlik>_<ad>`), `mgxs.csv`, `mgxs_ozet.json` (ayar, adlar, k tahminleri).
Spec'inde `ayarlar.mgxs` açık olan bir model (ör. koşu dizinindeki `mgxs_ce/spec.json`)
**Dosya › Python betiği olarak dışa aktar…** ile aktarılırsa betik aynı `openmc.mgxs.Library`'yi
kurar (`mgxs_kutuphanesi`); koşudan sonraki kütüphane üretimi yorum satırı olarak yazılıdır.

**Doğrulama.** Geçersiz bölge/grup/tür/düzeltme **hata**; tükenme açıkken MGXS tally'leri
eklenmez (**bilgi**); sabit kaynakta χ ve k∞ kaynağa özgüdür (**bilgi**); tahmini tally belleği
2 GiB'ı aşarsa **uyarı** (ince grup × hücre bölgesi).
