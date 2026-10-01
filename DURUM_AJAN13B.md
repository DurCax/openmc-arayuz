# Ajan 13b (kullanım kılavuzu) — durum notu

Dal `v2-d3-13b` (worktree `agent-a300f841befd48df8`). Kota kararıyla DURDURULDU
(sıra 11 → 12 → 13b). Devam mesajı gelince buradan sürülür.

## Biten

**Altyapı (kod + test, hepsi commit'li):**
- `arayuz/yardim/__init__.py` — sözleşme: `ac(bolum_kimligi, pencere=None)`, `BOLUMLER`
  (Ajan 12'nin 18 kimliği + ekler), `bolum_var`; ek `ara`, `bolum_basligi`.
- `arayuz/yardim/kaynak.py` (Qt'siz Markdown ayrıştırıcı/birleştirici, EN→TR düşme),
  `belge.py` (QTextDocument + başlık çapaları + resim ölçekleme), `gosterici.py`
  (QTextBrowser penceresi: içindekiler, arama, uyarı şeridi), `derle.py` (HTML + PDF,
  sözlük üretimi).
- `araclar/kilavuz.sh` (derleme; `--sozluk`, `--ekran`), `araclar/kilavuz_ekran.py`
  (`--dil tr|en`, offscreen, manifest + girdi özeti).
- TR ekran görüntüleri: `docs/kilavuz/resimler/tr/*.png` (13 adet, 436 kB) + `ekranlar.json`.
  NOT: `.gitignore`'daki `*.png` yüzünden `git add -f` ile eklendi.
- `testler/test_kilavuz.py` KL1–KL8 (HIZLI). Son koşu: 6 geçti, 2 kaldı — kalanlar YALNIZ
  05-dersler eksiklerinden (ders-guc, ders-benchmark, ders-kritik-arama, ders-rapor; EN 05 yok).

**Kılavuz metni (TR ve EN tam):** 00-giris, 01-kurulum, 02-ilk-hesap, 03-kavramlar,
04-sekmeler, 04a-malzemeler, 04b-parcalar, 04c-demet, 04d-geometri, 04e-geometri-gelismis,
04f-hesap-ayarlari, 04g-calistir, 04h-analiz, 04i-tukenme, 06-sonuclar, 07-uygunluk,
08-terminal, 09-sorun-giderme, 10-sozluk.

## Kalan

1. `docs/kilavuz/tr/05-dersler.md` — 5.1–5.6 yazıldı (dersler, ders-demet, ders-tam-kor,
   ders-altigen-kor, ders-kare-altigen, ders-tambur, ders-tukenme). EKSİK: 5.7 `ders-guc`,
   5.8 `ders-benchmark`, 5.9 `ders-kritik-arama`, 5.10 `ders-rapor` (çatal F3 durduruldu;
   son commit'ine bak: `git log -- docs/kilavuz/tr/05-dersler.md`).
2. `docs/kilavuz/en/05-dersler.md` — yok (TR bitince tam çeviri).
3. Bütünlük denetimi: `QT_QPA_PLATFORM=offscreen python -m pytest testler/test_kilavuz.py -m hizli`
   0 kalmalı; sonra tam hızlı süit (`pytest -m hizli -n 4`), `araclar/kapsam.sh`
   (arayuz/yardim ≥ %80), `graphify update .`.
4. Kalite gözden geçirmesi: çatalların yazdığı bölümlerde SOZLUK terimleri ve TR/EN eşliği
   örneklem denetimi; `araclar/kilavuz.sh` ile TR+EN PDF/HTML derlemesi.
5. `_kazi/` (commit edilmeyen çalışma dizini) silinir.

## Çatalların durumu

A–F (ilk tur) kota ile öldü; işleri dosyalarda/commit'lerde. F1 (04c, 04i TR + 04, 04a–c, 04i EN),
F2 (04d–h EN), F4 (08 TR+EN, 07/09 EN), F5 (01, 03 EN) BİTTİ. F3 (05-dersler) durdurma mesajı
aldı; yazdığını commit+push ediyor. Açık çatal kalmadı (F3 dışında).

## Orkestratöre notlar (başkasının dosyası)

- README.md'deki "ÖNCE ÇİZ, SONRA ÇALIŞTIR" ve "Bilinen tuzaklar" kılavuza taşındı
  (`06-sonuclar.md#once-ciz`, `#tuzaklar`); README'de bu bölümlerin kılavuza bağlantıyla
  kısaltılması orkestratörün kararı (README benim dosyam değil).
- `.gitignore`: `!docs/kilavuz/resimler/**/*.png` ve `build/` eklenmeli.
- Ajan 12: menü öğesi "Yardım → Kullanım kılavuzu" ve F1 bağlamı kılavuz metninde böyle anıldı.
- Gelişmiş editörde daldırma grubu değer kutusu "°" birimi gösteriyor ama değer yüzde (çatal F2).
- `demetler[].kilif` ve `tukenme.ek_malzemeler` için arayüzde düzenleyici yok (kılavuzda "yalnız JSON").
- `arayuz/yardim/` yeni msgid'leri (pencere başlığı, arama, uyarı şeridi, BOLUMLER) EN .po'ya girmeli.
