# Ajan 12 (Dalga 3, arayüz metinleri EN) — durum notu

Durduruldu: kullanıcı kararı (kota; sıra 11 → 12 → 13b). Dal `v2-d3-12`.

## Kalıcı yedek (depo dışı)
`/home/enes/openmc_v2_ciktilar/ajan12/` — `ceviri/*.json` (grup çevirileri, msgid → İngilizce),
`arac/` (yardımcı betikler), `KURALLAR.md` (alt ajan kuralları). /tmp/a12 silinirse buradan geri al
(`cp -r /home/enes/openmc_v2_ciktilar/ajan12 /tmp/a12`).

## Biten
- `arayuz/yardim_baglanti.py` (yeni): sayfa → bölüm, bulgu yeri → bölüm, `ac()`, `yardim_dugmesi()` ("?").
- Sayfa başlıklarında "?": `sekme_duzen.sayfa_basligi(bolum=)` (malzemeler, parçalar, demet, analiz,
  tükenme) + kart düğmesi (kor/yerlesim "Geometri" — gelişmişte `geometri-gelismis`; ayar/yerlesim
  "Hesap"; sekme_calistir "Koşu"); uygunluk_paneli `KILAVUZ_BOLUMU` bağlantısı + "?".
- `arayuz/pencere/menuler.py`: tüm metinler sarılı; Yardım > Kullanım kılavuzu (F1, bağlamsal:
  `kilavuz_bolumu()`), Yardım ve terimler → Shift+F1; bulgu listesinde sağ tık "Kılavuzda aç".
- `arayuz/pencere/yardim_metni.py` (yeni): Yardım HTML'i çevrilebilir parçalar (`YARDIM_HTML` eski ad).
- `cekirdek/ornek_bilgi.py`: `yerel_baslik()` / `yerel_aciklama()` (EN'de `_en`, yoksa TR + log).
- `ornekler/*.json`, `ornekler/vv/*.json`: `baslik_en`/`aciklama_en` SÖZLÜK'e uyduruldu (V&V: "case",
  "1D", açıklamalar; pin, duct, truncated, k∞).
- `testler/test_dil.py` EN modu D6–D11 + `testler/dil_en_yardimci.py` (kırmızı kanıtı commit 889090e
  mesajında). D10 (30 örnek) YAVAS ~2 dk; D11 (6 örnek) HIZLI ~30 s.
- Grup B (geometri/, kor/, sekme_kor, kor_altigen, izgara): sarma + çeviri BİTTİ (B.json 402 girdi,
  terim ihlali 0); cizim/cizim_xz 3 BİLGİ kaydı gerekçelendi (test_hata_yutma'da arayuz kaydı yok).
- Grup M (menuler, yardim_metni, yardim_baglanti): M.json 120 girdi, terim ihlali 0.

## Kalan (madde madde)
SARMA + JSON ÇEVİRİ 6 grupta BİTTİ (msgid.py 0 eksik): A 179, B 402, C 358, D 483, E 281, M 120 girdi
(`/home/enes/openmc_v2_ciktilar/ajan12/ceviri/`). Grup sahipleri: A pencere/bilesenler/ortak/onizleme;
B geometri/kor/izgara; C cubuk/demet/malzeme/baslangic; D ayar/calistir/analiz/guc/tukenme/uygunluk;
E tasarim; M menuler/yardim_metni/yardim_baglanti.
1. Kalan düzeltmeler: D "Çubuk çubuk yanma" → "Pin-by-pin burnup"; `celiski.py` "Sonuç" (D "Result"
   kart vs A/E "Results"; A sidebar için pgettext("gezinme") kullandı) ve "Alt/Üst sınır:" (D
   pgettext("arama") vs başka grup); `terim_json.py D` koşulmadı.
2. `pencere/ana_pencere._bulgu_ogeleri` ipucuna "sağ tık: kılavuzda aç"; `ana_pencere.py:~346`
   `kart["baslik"]` → değişkene al + `_()`; `sekme_kor.py:71` TUR_ADLARI gösteriminde `_()`.
3. EN taraması (derle.py + tara.py) A, C, D için son kez koşulmadı; D11/D10 ile bak.
4. `_` gölgeleme (`*_`, `x, _ = ...`) A/C/D'de bulunup düzeltildi; `/tmp/a12/C_golge.py` ile tüm
   arayuz'u bir kez tara.
5. Her grup bitince: `python /tmp/a12/arac/msgid.py G <dosyalar>` 0 eksik, `terim_json.py G`,
   `celiski.py` (gruplar arası aynı msgid farklı çeviri).
6. Katalog: `araclar/ceviri.sh cikar` → YALNIZ arayuz için
   `pybabel update -i locale/arayuz.pot -o locale/en/LC_MESSAGES/arayuz.po -l en -D arayuz --width=88
   --no-fuzzy-matching` (yoksa önce openmc_arayuz.po'dan kopyala) → `python /tmp/a12/arac/po_doldur.py`.
   Commit: `locale/arayuz.pot`, `locale/en/LC_MESSAGES/arayuz.po`. COMMIT ETME: openmc_arayuz.po/.mo,
   cekirdek.pot/po.
7. Testler: `test_dil` D6–D11 yeşil (TERIM_MUAF gerekirse gerekçeli); hızlı süit 0 KALDI;
   `test_hata_yutma` arayuz.* temiz.
8. Ekran turu EN: `QT_QPA_PLATFORM=offscreen python /tmp/a12/ekran_en.py --cikti
   /home/enes/openmc_v2_ciktilar/d3_en --tema acik --boyut 1280x800 --ornek pwr_17x17.json
   --ornek pwr_tukenme.json --ornek altigen_tambur_halkasi.json`; tur_ozeti.txt'de YATAY KAYDIRMA yok.
9. `graphify update .`, rapor.

## Sonraki adım
Madde 1–4, sonra 5–9 (katalog → testler → ekran turu). Alt ajan gerekmez; hepsi küçük işler.

## Bilinen sorunlar / başkasına düşen
- msgid = msgstr olan çeviriler ("Model", "Normal (800)", "JSON model (*.json)") `ceviri._` içinde
  "ceviri eksik" loglanır → D9/D11 eksik sayar: `cekirdek/ceviri.py` (Ajan 11) katalogda VAR mı diye
  bakmalı ya da test bu msgid'leri ayırmalı.
- `cekirdek/surum.py` UYGULAMA_ADI N_ ile işaretlenmeli (arayüz `_(UYGULAMA_ADI)` gösteriyor) — Ajan 11.
- `araclar/vv_kriter_uret.py` V&V örneklerini yeniden üretirse eski EN metinleri ("durum", "(ICSBEP
  benchmark, V&V set)") geri gelir — sahibi yeni `baslik_en/aciklama_en` kalıbını almalı.
- `araclar/ekran_turu.py`'de dil seçeneği yok (şimdilik /tmp/a12/ekran_en.py sarmalayıcı).
- Babel tuzağı: `_(x["ad"])` sahte msgid ("ad", "baslik") çıkarır — değişkene alıp `_()`.
- Çekirdek kaynaklı Türkçe (KOR_TURU_ADLARI, bulgular) Ajan 11 birleşince 0 olmalı (D10/D11 BİLGİ).
- `sekme_tukenme._cikti_oku` alt süreç günlüğünü "TÜKENME"/"HATA" ile süzüyor: Ajan 11 çekirdek
  terminal çıktısını çevirirse EN'de satırlar kaybolur (anahtar ile eşleşmeli).
- `cekirdek/malzeme_kutup` KATALOG ad/açıklama, `_PARAM` etiketleri, `dogrula/malzeme._SAB_KURALLARI`
  N_ ile işaretlenmeli (arayüz gösterirken `_()` sarıyor) — Ajan 11. `cekirdek/rapor_sablon` "Adım"
  (tükenme adımı) pgettext gerektirir (arayüzde "Adım" = Pitch).
- `cekirdek/ornek_bilgi.KATEGORI_ADLARI` ("Araştırma", "Zırh") çekirdek çevirisi bekliyor — Ajan 11.
