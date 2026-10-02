<a id="ders-mgxs"></a>
## 5.19 Grup sabitleri, çok gruplu Monte Carlo ve random ray

**Örnek dosya:** `ornekler/pwr_pinhucre.json` · **Seviye:** ileri · **Tahmini süre:** 30 dakika
(koşular toplam ~4 dakika, 6 iş parçacığı) · **Başvuru:** [Grup sabitleri ve random ray kartı](04h3-grup-sabitleri.md#mgxs)

**Amaç.** Sürekli enerji Monte Carlo'nun bir çekirdek simülatörüne nasıl **grup sabiti**
verdiğini görmek: akı ağırlıklı 2 grup sabitleriyle sonsuz ortam k∞'u elle (2 × 2 özdeğer)
yeniden bulmak, ince grup kütüphanesiyle aynı geometriyi çok gruplu (MG) Monte Carlo ve
random ray ile koşup farkların nereden geldiğini (homojenleştirme, grup yoğunlaştırması,
yöntem) ayırmak ve taşıma düzeltmesinin etkisini ölçmek.

**Ön koşul.** [5.1 Demet k∞](05-dersler.md#ders-demet) (yansıtıcı sınır = sonsuz kafes) ve
[5.11 Spektrum](05-dersler.md#ders-spektrum) (termal kesim 0.625 eV).

**Adımlar.**

1. `ornekler/pwr_pinhucre.json`'u açın. **Hesap ayarları**'nda **Parçacık / çevrim** 10 000,
   toplam 60 çevrim, 20 pasif yapın (beklenen tablodaki istatistik).
2. **Analiz** sayfasında en alttaki **Grup sabitleri ve random ray** kartına gidin.
   **Kapsam** = **Tüm model**, **Bölge türü** = **Demet (tüm model, tek bölge)**, **Grup yapısı**
   = **CASMO-2 (2 grup)**, **Taşıma düzeltmesi** = **Yok** → **Grup sabitlerini üret**.
3. Koşu bitince özet satırlarını okuyun: **CE k**, **Sabitlerden k = Σ νΣf·φ / Σ Σa·φ** ve
   **Sonsuz ortam k∞ (G×G özdeğer)**. **Gösterilen tür** ile **Toplam Σt**, **Soğurma Σa**,
   **ν-fisyon νΣf**, **Fisyon tayfı χ** ve **ν-saçılma matrisi (tutarlı)** satırlarını
   görüntüleyin.
4. **Elle doğrulama.** Tablodan 2 × 2 problemi kurun (g = 1 hızlı, 2 termal; S(g→g') ν-saçılma):

       M = | Σt1 − S11    −S21     |        k∞ = νΣf ᵀ M⁻¹ χ
           | −S12         Σt2 − S22 |

   χ = (1, 0) olduğundan k∞ = [νΣf1 (Σt2 − S22) + νΣf2 S12] / det M. Hesap makinesiyle kartın
   özdeğerini bulun (yukarı saçılma S21 küçük ama sıfır değildir).
5. **MG ile yeniden koş** ve **Random ray ile koş**. Karşılaştırma tablosunda iki çok gruplu
   sonucun da özdeğere eşit olduğunu görün (homojen ortam).
6. **Taşıma düzeltmesi.** **Taşıma düzeltmesi** = **P0** ile 2. adımı tekrarlayın: Σt yerine
   ν-taşıma Σtr gelir, saçılma matrisinin köşegeni küçülür, ama k∞ değişmez.
7. **İnce grup, aynı geometri.** **Bölge türü** = **Malzeme**, **Grup yapısı** = **CASMO-70 (70
   grup)**, **Taşıma düzeltmesi** = **Yok** → **Grup sabitlerini üret**; sonra **MG ile yeniden
   koş** ve **Random ray ile koş**. Random ray ayarları kütüphane üretilince doldurulur
   (200 ışın, 500 çevrim, 300 pasif, bölme yok).
8. 7. adımı **P0** ile tekrarlayın ve özet notunu okuyun.

**Beklenen sonuç** (ENDF/B-VIII.0; sayılar istatistikle ± birkaç yüz pcm oynar):

| Adım | Yöntem | k | Fark | Açıklama |
|---|---|---|---|---|
| 2 | CE | 1.3582 ± 0.0015 | — | MGXS tally'li koşu |
| 3 | Σ νΣf·φ / Σ Σa·φ | 1.3565 | ≈ −170 pcm | (n,xn) net üretimi bu orana girmez |
| 3–4 | G×G özdeğer | 1.3589 | ≈ +70 pcm | ν-saçılma (n,2n)'yi içerir; CE ile 4σ içinde |
| 5 | MG MC | 1.3591 ± 0.0007 | özdeğere ≈ +20 pcm | aynı sabitler, homojen ortam |
| 5 | Random ray | 1.3589 | özdeğere < 1 pcm | düz kaynak homojen ortamda kesin |
| 6 | G×G özdeğer (P0) | 1.3589 | düzeltmesizle aynı | kaldırma Σtr − S11ᶜ = Σt − S11 |
| 7 | MG MC (CASMO-70, malzeme) | 1.3575 ± 0.0010 | ≈ −70 pcm | homojenleştirme + yoğunlaştırma + izotropik saçılma |
| 7 | Random ray | 1.3574 ± 0.0005 | MG'ye ≈ −10 pcm | düz kaynak, bölme yok |
| 8 | MG MC (P0) | ≈ 1.28 | ≈ −7600 pcm | negatif köşegen: kart uyarır |
| 8 | Random ray (P0) | ≈ 1.357 | ≈ −120 pcm | köşegen kararlılaştırması |

**Neden?**

- **Akı ağırlığı reaksiyon hızlarını korur.** Σx,g = ⟨Σx φ⟩/⟨φ⟩ tanımı, aynı akıyla çarpılınca
  CE koşusunun reaksiyon hızlarını verir. Sonsuz homojen ortamda akı tek bir sayıdır (grup başına);
  bu yüzden 2 grup sabitleri CE k∞'u (istatistik içinde) yeniden üretir. Bu kesinlik **yalnız
  sonsuz ortamda** geçerlidir: sızıntılı bir problemde akının uzay ve açı dağılımı değişir ve
  sabitler o problemin tayfına bağlı kalır.
- **Oran neden düşük?** Σ νΣf φ / Σ Σa φ, (n,2n) ile doğan fazladan nötronları saymaz. Özdeğer ν-saçılma
  matrisini kullanır; (n,2n) çoğalması oradadır. İkisinin farkı (≈ 170 pcm) pin hücrede (n,xn)
  katkısıdır.
- **P0 düzeltmesi k∞'u neden değiştirmez?** Σtr = Σt − Σs1 ve köşegen S11 − Σs1: kaldırma
  Σtr − (S11 − Σs1) = Σt − S11 aynı kalır. Düzeltme yalnız sızıntıyı (D = 1/3Σtr) etkiler — difüzyon
  çözücüsünde önemlidir, sonsuz ortamda görünmez.
- **İnce grupta P0 ve MG MC.** Hızlı gruplarda sudaki ileri saçılma büyüktür (μ̄ ≈ 2/3); Σs1 köşegeni
  aşar ve köşegen negatif olur. Monte Carlo bir olasılığı negatif örnekleyemez; sonuç geçersizdir.
  Random ray köşegeni kararlılaştırır (diagonal stabilization) ve doğru kalır.
- **Aynı geometri MG MC neden CE'den farklı?** Her malzeme tek bölgedir (yakıt içinde kendini
  koruma ve akı çökmesi bölge ortalamasına iner), 70 grup içinde rezonans yapısı ortalanır ve saçılma
  izotropik varsayılır. Toplam etki burada ≈ −70 pcm'dir; kaba grupta ve büyük bölgelerde artar.
- **Random ray neden MG MC'den farklı?** İkisi aynı `mgxs.h5`'i kullanır; fark **yöntemdir**: random
  ray kaynak bölgesi başına düz (ya da doğrusal) kaynak varsayar. Bölmeyi artırmak ya da
  **Kaynak şekli** = **Doğrusal** seçmek farkı küçültür. Ayrıca random ray her çevrimde tek kaynak
  yinelemesi yapar; pasif çevrim kısa kalırsa yakınsamamış k okunur.

**Sorular.**

1. 2 grup tablosundan k∞'u 4. adımdaki formülle hesaplayın. Yukarı saçılmayı (S21) sıfır alırsanız
   k∞ ne kadar değişir?
2. Sabitlerden oran ile özdeğer farkı (n,xn) katkısıdır. U-238'in (n,2n) eşiği ≈ 6 MeV'dir; bu fark
   hangi grupta oluşur?
3. 7. adımda **Bölge türü** = **Hücre** seçin. Pin hücrede sonuç değişir mi? Neden (malzeme başına bir
   hücre)?
4. Random ray'de **Kaynak bölgesi bölmesi** 0, 13 ve 26 ile tekrarlayın; k ve süre nasıl değişir?

**Cevaplar.** (1) Formül kartın özdeğerini verir; S21 = 0 alınca k∞ ≈ 440 pcm düşer (ölçülen
tabloda 1.35891 → 1.35446): termalden hızlı gruba dönen nötronlar kaybolmuş sayılır. (2) Hızlı grup (> 0.625 eV, (n,2n) eşiği MeV
bölgesinde): (n,2n) yalnız ν-saçılma matrisinin hızlı satırını büyütür. (3) Pin hücrede her malzeme
tek hücrededir; bölgeler aynıdır, sonuç istatistik içinde aynı kalır (adlar `c…` olur). (4) Ölçülen (CASMO-70, malzeme, 200 ışın × 500
çevrim): bölme 0 → 1.3574, 13 → 1.3569, 26 → 1.3569 (her biri ± 0.0005); süre 20, 83, 120 s. Pin
hücrede bölgeler zaten incedir (yakıt yarıçapı 0.39 cm; su, zarf ile hücre kenarı arasında 0.17–0.43 cm): fark istatistik düzeyindedir,
bölme yalnız süreyi artırır. Optik olarak kalın, büyük düz bölgelerde (yansıtıcı, su boşluğu) düz
kaynak hatası büyür ve bölme ya da **Doğrusal** kaynak gerekir.

**Kaynaklar.** OpenMC 0.16 belgeleri, *Multigroup Cross Section Generation* (`openmc.mgxs`) ve
*Random Ray* bölümleri; W. M. Stacey, *Nuclear Reactor Physics* (2007), bölüm 4 (çok gruplu
difüzyon) ve 13 (homojenleştirme); J. R. Tramm vd., "The Random Ray Method for neutral particle
transport", *J. Comput. Phys.* 342 (2017) 229–252.
