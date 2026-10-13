# MURAT HOCA | KRİPTO RADAR — V0.1

Binance TR TRY spot paritelerini tarayan Streamlit prototipi. **Gerçek zamanlı bağlantı bu geliştirme ortamında test edilemedi.** API yanıtları başarısız olursa uydurma sinyal üretilmez.

## Kurulum
1. Dosyaları bir GitHub deposuna yükleyin.
2. Streamlit Community Cloud üzerinde **Create app** deyin ve `app.py` dosyasını seçin.
3. Açılan panelde **Piyasayı şimdi tara** düğmesine basın.
4. İlk denemede 5–10 parite ile başlayın; hata bölümünü kontrol edin.

Yerel çalıştırma: `pip install -r requirements.txt` ardından `streamlit run app.py`.

## Sınırlar
- Yalnızca Binance TR'nin kamuya açık piyasa verileri; API anahtarı veya emir yetkisi gerekmez.
- `type=1` ve `type=3` mum endpoint'leri resmi dokümana dayanır. `type=2` için doğrulanmış endpoint bulunmadığından atlanır.
- Son (tamamlanmamış) mum puanlamadan çıkarılır.
- Pariteler API'nin döndürdüğü sırada alınır; ilk 50 parite, en likit 50 anlamına gelmez.
- 24 saatlik değişim 15m için 96, 1h için 24 tamamlanmış mum üzerinden yaklaşık hesaplanır.
- Likidite, spread, token kilit açılışı, haber, backtest, Telegram ve 7/24 sunucu taraması henüz eklenmedi.
- Skorlar deneysel kurallardır; olasılık ya da doğrulanmış alım sinyali değildir.
- Community Cloud uyku moduna geçebilir; arka planda kesintisiz tarama sağlamaz.
