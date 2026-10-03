<a id="tukenme-bolme"></a>
### 4.9.2 Tükenme bölgesi bölme: radyal halka ve eksenel dilim

**Tükenme** sayfasındaki **Bölge bölme** kartı, pinleri radyal **halkalara** ve eksenel katmanları
**dilimlere** böler; her parça ayrı bir tükenme malzemesi olarak yanar (Serpent'in `div` komutunun
karşılığı). Neden: tek malzemeli bir pin tek ortalama bileşimle yanar. Yanabilir zehirli (Gd, Er)
pinde nötron soğuran dış kabuk önce yanar ve iç kısmı perdeler (**kendinden perdeleme**); ortalama
bileşim bunu göremez, Gd'nin tükenme hızı ve k(t) eğrisi bu yüzden yanlış çıkar. Bölme ayrıca pin
gücünün yanmayla radyal dağılımını gerçekçi kılar.

Bölme **spec düzeyinde** uygulanır: halkalar çubuğun `bolgeler` listesine (aynı malzeme, yeni
yarıçaplar), dilimler `kor.eksenel.bolgeler` listesine girer ve **çubuk çubuk yanma** otomatik
açılır (bölünen parçalar ancak böyle ayrı yanar). Geometri kurucusu, analitik hacimler, betik
üretici ve pin gücü ([K3](04i-tukenme.md#tukenme)) bu yüzden değişmeden aynı yolu izler.
Kullanıcının dosyasında yalnız `tukenme.bolme` anahtarı kalır; koşu dizinine yazılan model kaydı
da bu sade modeldir (eskime denetimi bölmeyi **fiziğe dahil** sayar).

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Bölge bölme açık** | Bölme anahtarı. Kapalıyken `bolme` dosyada yoktur (eski projeler gidiş-dönüşte değişmez). | — | kapalı | Tek örnekli modelde "bölmesiz" ile karşılaştırmadan sonuç yorumlamak | `tukenme.bolme` |
| **Çubuk türleri** | Bölünecek pin türleri (yanabilir bölgesi olan, silindirik, kontrol olmayan). İşaretli çubuğun **yanabilir** (fisil ya da Gd/Er/B zehirli) bölgeleri bölünür; kılıf, boşluk ve su bölünmez. | — | Gd'li pin | Kontrol çubuğunu bölmek (reddedilir: emici bölge daldırmaya bağlıdır) | `tukenme.bolme.cubuklar[].cubuk` |
| **Halka sayısı** | Bölgenin kaç halkaya bölüneceği (1 = bölme yok). | halka | Gd pini: 3–6 | 20'den fazla (reddedilir); halka sayısını artırınca süre ve bellek artar | `tukenme.bolme.cubuklar[].halka` |
| **Halka türü** | **Eşit hacimli** (varsayılan, Gd için önerilen başlangıç), **eşit kalınlıklı** (karşılaştırma için) ya da **dışa doğru incelen** (geometrik). Aşağıya bakın. | — | eşit hacim | Eşit kalınlık seçip dış halkanın gücün çoğunu taşıdığını gözden kaçırmak | `tukenme.bolme.cubuklar[].tur` (`esit_hacim` \| `esit_kalinlik` \| `dista_incelen`) |
| **İncelme oranı** | Yalnız dışa doğru incelen türde: her halkanın kalınlığı bir içerdekinin bu kadarıdır. Mühendislik tercihidir, ölçülmüş eşik değildir. | — | 0.6 (0.2–0.95) | Çok küçük oran: dış halka sayısal olarak çok ince olur | `tukenme.bolme.cubuklar[].oran` |
| **Eksenel dilim** | Yanabilir pin ya da plaka içeren eksenel katmanlar bu kadar eşit dilime bölünür (h/n). 3B model (yükseklik ya da eksenel katmanlar) gerekir. | dilim | 1–10 | 2B modelde dilim istemek (reddedilir) | `tukenme.bolme.eksenel.dilim` |

**Halka türleri** (r_ic ≤ r ≤ r_dış, n halka, k = 1 … n; son yarıçap tam r_dış'tır):

    eşit hacim      r_k² = r_ic² + (k/n) (r_dış² − r_ic²)         her halka aynı alan
    eşit kalınlık   r_k  = r_ic  + (k/n) (r_dış  − r_ic)           dışta büyük hacimli halkalar
    dışa incelen    kalınlıklar geometrik: t_(k+1) = oran · t_k    en sıkışık dış halka

Gd pininde yarıçapa göre soğurma güçlü olduğundan dış halka güç ve yanma bakımından baskındır
(K3 incelemesi). **Eşit hacimli** halkalar, dışa doğru zaten incelen halkalardır ve iyi bir
başlangıçtır; kaynak: Serpent `div` ve CASMO uygulamalarında Gd pininin eşit hacimli ya da dışa
doğru sıkışan halkalara bölünmesi. Halka sayısını artırınca k(t) ve Gd eğrisinin yakınsadığını
küçük bir modelde sınayın ([5.20 Ders](05d-ders-tukenme-bolme.md#ders-tukenme-bolme)).

**Hacim korunumu (analitik).** Halka alanları π(r_k² − r_(k−1)²) olduğundan toplamları π(r_dış² −
r_ic²)'ye eşittir; kart bunu **Halka hacimlerinin toplamı analitik hacme eşit (en büyük bağıl sapma
…)** satırıyla gösterir (kayan nokta düzeyi, ~10⁻¹⁶; kabul ölçütü 10⁻⁹). Tükenme hazırlığı ayrıca
her örneğin hacmini kendi hücre alanı × katman yüksekliğinden hesaplar ve toplamı analitik hacimle
10⁻⁹ içinde karşılaştırır; tutmazsa koşu başlamaz.

**Maliyet.** Her parça ayrı malzemedir: kartın özeti **Ayrı tükenme malzemesi: 264 → 1056** gibi
sayıyı yazar. Süre ve bellek bu sayıyla artar; büyük kor modelinde yalnız Gd pinlerini bölün. Bölme
**gelişmiş (ağaç) modda** desteklenmez.

**Pin gücü ile uyum.** Güç tally'si bölünen pinin **bütün** yakıt halkalarını hedefler ve aynı
konumdaki halka tally'lerini toplar: pin gücü, alt bölgelerin toplamıdır (K3 incelemesinin kuralı).
Dosyada açık güç hedefi varsa (eski bölge numaraları) bölünen bölgenin tüm halkaları hedef olur.

**Betik.** Üretilen Python betiği bölünmüş modeli içerir (halkalar çubuk tanımında, dilimler
katmanlarda); betik ile arayüz aynı yarıçaplarla aynı modeli kurar.
