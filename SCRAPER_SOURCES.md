# SWAT Projesi Veri Kaynakları ve Risk Analizi

Bu döküman, SWAT projesi kapsamında veri çekilen (scraping) tüm web sitelerini, bu sitelerin kullanım amaçlarını ve veri çekme işlemi sırasında karşılaşılabilecek potansiyel riskleri içermektedir.

## 1. Üniversite Sıralama Kuruluşları (Rankings)

| Kaynak Site | URL | Kullanım Amacı | Risk Seviyesi | Teknik Notlar |
| :--- | :--- | :--- | :--- | :--- |
| **Shanghai Ranking (ARWU)** | [shanghairanking.com](https://www.shanghairanking.com) | Dünya üniversite sıralamaları | **Yüksek** | Cloudflare koruması ve dinamik API yapısı nedeniyle kararlılık sorunları yaşatabilir. |
| **URAP (Türkiye)** | [newtr.urapcenter.org](https://newtr.urapcenter.org) | Türkiye üniversite sıralamaları | **Orta** | Her yıl değişen URL yapısı (örn: /2024-2025/) manuel güncelleme gerektirir. |
| **Webometrics** | [webometrics.org](https://www.webometrics.org) | Web popülerliği sıralaması | **Düşük** | Sayfalama yapısı takibi hassastır, HTML yapısı nispeten stabildir. |
| **Leiden Ranking** | [leidenranking.com](https://www.leidenranking.com) | Bilimsel performans verileri | **Orta** | "Traditional" ve "Open Edition" arası geçişlerde veri linkleri değişebilir. |
| **UI GreenMetric** | [uigreenmetric.com](https://uigreenmetric.com) | Sürdürülebilirlik sıralaması | **Düşük** | Veriler genellikle statik tablolarda sunulur. |
| **ScholarGPS** | [scholargps.com](https://scholargps.com) | Akademik performans ve yayın | **Orta** | Çok geniş veri setine sahip olduğu için hızlı isteklerde IP bloklaması yapabilir. |
| **EngiRank** | [engirank.eu](https://engirank.eu) | Avrupa mühendislik sıralaması | **Düşük** | Modern ve temiz bir yapısı var, şu an için stabil. |
| **THE (Times Higher Ed.)** | [timeshighereducation.com](https://www.timeshighereducation.com) | Dünya üniversite sıralamaları | **Yüksek** | Çok sıkı bot koruması ve dinamik JSON veri yüklemesi mevcuttur. |
| **QS World Rankings** | [topuniversities.com](https://www.topuniversities.com) | Dünya üniversite sıralamaları | **Yüksek** | Yoğun JavaScript kullanımı ve otomatik araçlara karşı gelişmiş koruma sistemleri vardır. |

## 2. Hibe ve Destek Duyuruları (Grants & Funding)

| Kaynak Site | URL | Kullanım Amacı | Risk Seviyesi | Teknik Notlar |
| :--- | :--- | :--- | :--- | :--- |
| **Yatırıma Destek** | [yatirimadestek.gov.tr](https://www.yatirimadestek.gov.tr) | Teşvik ve hibe arama | **Orta** | Devlet sitesi korumaları (WAF) bot trafiğini engelleyebilir. |
| **KOSGEB** | [kosgeb.gov.tr](https://www.kosgeb.gov.tr) | KOBİ ve girişimci destekleri | **Orta** | Duyuru başlıkları ve HTML sınıfları (CSS classes) sık güncellenir. |
| **EU Funding (AB)** | [ec.europa.eu](https://ec.europa.eu) | Avrupa Birliği fonları | **Düşük** | Resmi API üzerinden veri çekilir, oldukça güvenilirdir. |
| **AB Başkanlığı** | [ab.gov.tr](https://www.ab.gov.tr) | Güncel hibe duyuruları | **Orta** | Bağlantı hızları dalgalanabilir, zaman aşımı (timeout) yönetimi gerektirir. |

## 3. Kurumsal Veriler

| Kaynak Site | URL | Kullanım Amacı | Risk Seviyesi | Teknik Notlar |
| :--- | :--- | :--- | :--- | :--- |
| **İTÜ Haberler** | [haberler.itu.edu.tr](https://haberler.itu.edu.tr) | Üniversite içi duyuru ve haberler | **Düşük** | Kurumsal bir yapıdadır, veri çekmek genellikle sorunsuzdur. |

---

## ⚠️ Genel Riskler ve Tavsiyeler

1.  **IP Engellemesi (Rate Limiting):**
    *   *Sorun:* Aynı anda yüzlerce istek atmak sunucu tarafından "saldırı" olarak algılanabilir.
    *   *Çözüm:* İstekler arasına `time.sleep(1-3)` ekleyerek insan hızına yakın bir tarama yapın.

2.  **Veri Kırılganlığı (Data Brittleness):**
    *   *Sorun:* Sitelerin tasarımı değiştiğinde `BeautifulSoup` seçicileri veriyi bulamaz.
    *   *Çözüm:* Hata yönetimi (try-except blokları) kullanarak scraper patladığında log tutulmasını sağlayın.

3.  **Yasal ve Etik Sınırlar:**
    *   Resmi kurumların `robots.txt` dosyalarını kontrol edin.
    *   Çekilen verilerin kaynağını mutlaka projede belirtin.
    *   Kullanıcı verilerini veya kişisel bilgileri çekmekten kaçının (bu proje akademik/kurumsal odaklıdır).

4.  **Dinamik İçerik (JavaScript):**
    *   Bazı siteler (örn. Shanghai) veriyi HTML içinde değil, JS ile yükler. Bu durumlarda `requests` yerine tarayıcı emülasyonu veya doğrudan API endpoint'leri tercih edilmelidir.

---
*Son Güncelleme: 1 Mayıs 2026*
