# Ajan 12 (Dalga 3, arayüz metinleri EN) — durum: BİTTİ (01.10.2026)

- `arayuz/**` görünen metinler sarılı; `locale/arayuz.pot` + `locale/en/LC_MESSAGES/arayuz.po`
  (1657 msgid, hepsi çevrili, SÖZLÜK terim denetimi temiz). Birleşik openmc_arayuz.po/.mo
  orkestratörün (commit edilmedi).
- Kılavuz bağlantıları: `arayuz/yardim_baglanti.py`; Yardım → Kullanım kılavuzu (F1 bağlamsal),
  sayfa "?" düğmeleri, bulgu sağ tık "Kılavuzda aç", uygunluk paneli `KILAVUZ_BOLUMU`.
- `test_dil` EN modu D6–D11 yeşil; hızlı süit 589 geçti / 0 kaldı.
- EN ekranları: `~/openmc_v2_ciktilar/d3_en/` (yatay kaydırma yok).
- Çeviri kaynak JSON'ları ve araçlar: `~/openmc_v2_ciktilar/ajan12/`.

Başkasına düşen: `araclar/vv_kriter_uret.py` eski EN metnini üretir; `araclar/ekran_turu.py`'de
dil seçeneği yok; çekirdek `dogrula.yer_etiketi` "geometri:<yol>" yerini etiketlemiyor;
`sekme_tukenme._cikti_oku` "TÜKENME"/"HATA" işaretleriyle süzüyor (alt süreç artık
OPENMC_ARAYUZ_DIL alıyor; çekirdek çıktısı çevrilirse anahtarla eşlenmeli).
