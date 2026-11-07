# ScamShield — Proje Rehberi

> Son güncelleme: 15 Ekim 2026. Projeye yeni başlayan bir geliştiricinin bilmesi gereken her şey bu dosyada: ne yaptık, site nasıl çalışıyor, kendi bilgisayarında nasıl çalıştırılır, nasıl yayına alınır.
>
> Kuralların tek doğruluk kaynağı [CLAUDE.md](../CLAUDE.md)'dir. Bu rehber onu anlaşılır hâle getirir; ikisi çelişirse CLAUDE.md geçerlidir.

## İçindekiler

1. [Proje nedir?](#1-proje-nedir)
2. [Şu anki durum](#2-şu-anki-durum)
3. [Mimari: parçalar ve bir taramanın yolculuğu](#3-mimari-parçalar-ve-bir-taramanın-yolculuğu)
4. [Tarama motoru nasıl karar veriyor?](#4-tarama-motoru-nasıl-karar-veriyor)
5. [Kara listeler ve worker görevleri](#5-kara-listeler-ve-worker-görevleri)
6. [Gizlilik ve KVKK: asla yapılmayacaklar](#6-gizlilik-ve-kvkk-asla-yapılmayacaklar)
7. [Repo yapısı](#7-repo-yapısı)
8. [Kendi bilgisayarında çalıştırma (adım adım)](#8-kendi-bilgisayarında-çalıştırma-adım-adım)
9. [Günlük çalışma akışı (tek dal, push = yayın)](#9-günlük-çalışma-akışı-tek-dal-push--yayın)
10. [Testler](#10-testler)
11. [Production: sunucu, deploy, yedek, izleme](#11-production-sunucu-deploy-yedek-izleme)
12. [Sık kullanılan sunucu komutları](#12-sık-kullanılan-sunucu-komutları)
13. [Kural dosyalarını güncelleme](#13-kural-dosyalarını-güncelleme)
14. [Alınan kararlar (karar günlüğü)](#14-alınan-kararlar-karar-günlüğü)
15. [Değişiklik geçmişi](#15-değişiklik-geçmişi)
16. [Karşılaşılan sorunlar ve çözümleri](#16-karşılaşılan-sorunlar-ve-çözümleri)
17. [Açık işler ve sonraki adımlar](#17-açık-işler-ve-sonraki-adımlar)

---

## 1. Proje nedir?

Türkiye'deki kullanıcılar için dolandırıcılık engelleme uygulaması. **Yapay zekâ kullanılmaz**; her karar kara listelerden, kurallardan ve kullanıcı bildirimlerinden gelir. Her sonucun gerekçesi Türkçe olarak gösterilir.

**Özellikler:**
- **Mesaj / link tarama (hazır, yayında):** Kullanıcı şüpheli bir SMS ya da WhatsApp mesajını yapıştırır. Sistem mesajdaki linkleri ve metni kontrol eder; sonucu "Tehlikeli", "Şüpheli" ya da "Bilinen tehdit yok" olarak gösterir. **Mesaj hiçbir yere kaydedilmez.**
- **Şüpheli numara bildirme (Faz 3, henüz yapılmadı):** Kullanıcılar dolandırıcı numaraları işaretler; en az 3 farklı cihazdan bildirilen numaralar listede görünür.
- **Android uygulaması (Faz 4, geliştirme sürüyor):** Mesajlar Android Paylaş menüsünden ScamShield'a aktarılır; diğer platformlar kapsam dışıdır.

Kullanıcı hesabı yoktur, uygulama tamamen anonim çalışır.

## 2. Şu anki durum

| | |
|---|---|
| **Canlı site** | https://lovelockapp.com (geçici domain; `www.` ana adrese yönlenir) |
| **Repo** | https://github.com/Damlayuksel/ScamShield (15 Ekim 2026'da bazuann hesabından devredildi; eski adres yönlendirir ama kullanmayın) |
| **Faz 1** (altyapı + tarama API'si) | ✅ Bitti |
| **Faz 2** (web sitesi + HTTPS + yayın) | ✅ Yayında; yalnızca hukuki metinlerin yer tutucuları ve avukat onayı eksik |
| **Faz 3** (numara sistemi) | ⏳ Başlamadı |
| **Faz 4** (Android uygulaması) | ⏳ Paylaşım alıcısı eklendi; deneysel Expo API'si gerçek cihazda doğrulanmalı, build/yayın bekliyor |
| **Sunucu** | Ubuntu 24.04, 4 GB RAM, IP `104.233.4.115`, SSH portu `25416` |
| **Kara liste** | USOM ~493 bin, URLhaus ~2 bin kayıt (her gece otomatik güncelleniyor) |
| **Deploy** | `main`'e push → CI geçerse otomatik yayın |
| **Testler** | Backend 274, mobil 62 test |

## 3. Mimari: parçalar ve bir taramanın yolculuğu

### Parçalar

```
                 İnternet
                    │  HTTPS (80 → 443 yönlendirme)
                    ▼
        ┌──────────────────────┐
        │  web  (Nginx)        │  statik site (Expo web build) + /api proxy
        └──────────┬───────────┘
                   │  /api/...
                   ▼
        ┌──────────────────────┐      ┌──────────────────────┐
        │  api  (FastAPI)      │◄────►│  redis               │  kara liste hash'i,
        └──────────┬───────────┘      │  (yalnızca önbellek) │  rate limit, RDAP önbelleği
                   │                  └──────────▲───────────┘
                   ▼                             │
        ┌──────────────────────┐      ┌──────────┴───────────┐
        │  db  (PostgreSQL 16) │◄────►│  worker (APScheduler)│  USOM/URLhaus indirir
        └──────────────────────┘      └──────────────────────┘

        certbot: Let's Encrypt sertifikasını 12 saatte bir yeniler
```

| Servis | Teknoloji | Görev |
|---|---|---|
| `web` | Nginx | Statik siteyi sunar, `/api` isteklerini API'ye iletir, HTTPS, güvenlik başlıkları |
| `api` | Python 3.12, FastAPI | Tarama, domain bildirimi, sağlık kontrolü |
| `worker` | APScheduler | Kara listeleri indirir, Redis'e kopyalar, eski kayıtları temizler |
| `db` | PostgreSQL 16 | Kara liste, istatistik ve bildirim tabloları |
| `redis` | Redis 7 | Hızlı kara liste sorgusu, rate limit sayaçları, RDAP önbelleği |
| `certbot` | Let's Encrypt | Sertifika yenileme (yalnızca production) |

Web sitesi ve mobil uygulama **aynı Expo kod tabanından** (`mobile/`) üretilir. Webde statik HTML olarak derlenir ve Nginx tarafından sunulur.

### Bir taramanın yolculuğu

1. Kullanıcı mesajı ana sayfadaki kutuya yapıştırır ve **Kontrol et**'e basar.
2. Tarayıcı `POST /api/v1/scan` isteği atar; mesaj **yalnızca istek gövdesinde** gider, URL'de geçmez.
3. Nginx isteği API'ye iletir. İstemcinin gönderdiği `X-Forwarded-For` başlığını ezer, böylece sahte IP gönderilemez.
4. API, IP'nin HMAC özetiyle rate limit uygular (dakikada 20 tarama).
5. Tarama motoru çalışır (bkz. [4. bölüm](#4-tarama-motoru-nasıl-karar-veriyor)):
   - mesajdaki linkleri çıkarır (en fazla 10),
   - her linki kara listede arar,
   - kurallarla puanlar,
   - kısa linklerin nereye gittiğini güvenli biçimde çözer,
   - sitenin ne kadar yeni olduğuna bakar,
   - metni Türkçe kalıplarla tarar.
6. Sonuç hesaplanır. `scan_stats` tablosuna **yalnızca alan adı ve sonuç seviyesi** yazılır.
7. Yanıt döner: seviye, gerekçeler, mesajdaki alan adları (tam link değil) ve "Ne yapmalıyım?" önerileri.
8. Sonuç aynı ekranda gösterilir. Mesaj tarayıcıda da hiçbir yere (URL, localStorage vb.) yazılmaz.

## 4. Tarama motoru nasıl karar veriyor?

Her link ve metin puan alır; puan sonuç seviyesini belirler.

| Toplam puan | Seviye | Ekranda |
|---|---|---|
| 70 ve üzeri | `dangerous` | 🔴 **Tehlikeli** |
| 30–69 | `suspicious` | 🟡 **Şüpheli** |
| 0–29 | `no_known_threat` | 🟢 **Bilinen tehdit yok** ("yine de dikkatli olun") |

Sistem **hiçbir zaman "kesinlikle güvenli" demez.**

### Katman 1: Kara listeler
Link USOM, URLhaus ya da topluluk kara listesindeyse puan doğrudan **100**, sonuç **Tehlikeli** olur. Eşleşme hostname bazındadır: `a.b.evil.com` için sırasıyla `a.b.evil.com`, `b.evil.com` ve `evil.com` aranır.

### Katman 2: URL kuralları

| Kontrol | Puan |
|---|---|
| Resmî alan adı (`official_domains.json`, kayıtlı domainde tam eşleşme) | 0 |
| Marka taklidi (ör. `z1raat-guvenlik.com`) | +40 |
| Punycode / taklit harf (`xn--`) | +30 |
| Domain 30 günden yeni (RDAP) | +30 |
| Ham IP adresi (`http://203.0.113.4/...`) | +20 |
| Adres kısmında `@` (`https://banka.com.tr@evil.com`) | +20 |
| 3'ten fazla alt alan adı | +10 |
| Riskli uzantı (`.xyz`, `.top`, `.shop`…) | +10 |
| Çözülemeyen kısa link | +10 |

**Önemli ayrıntılar:**
- **Kayıtlı domain her zaman `tldextract` ile çıkarılır,** string araması yapılmaz. Örneğin `turkiye.gov.tr.giris-yap.xyz` adresinin gerçek domaini `giris-yap.xyz`'dir.
- **Marka taklidi şöyle aranır:**
  - 4 harf ve üzeri anahtar kelimeler alt dize olarak aranır.
  - 5 harf ve üzeri anahtar kelimeler ayrıca yazım hatası olarak da aranır. Bunun için **OSA mesafesi** kullanılır (harf yer değiştirmesi 1 sayılır). Yanlış alarmı önlemek için ilk harf aynı olmalı, uzunluk farkı en fazla 1 olmalı; 6 harfe kadar 1, daha uzunlarda 2 harf farkına izin verilir. Bu sayede "firsat" Ziraat sanılmaz, ama "akbnak" Akbank olarak yakalanır.
  - Kısa markalar (ptt, ing) yalnızca tam parça olarak eşleşir.
  - Kiril/Yunan benzer harfler Latin harflere çevrilip öyle kontrol edilir.
- **Kısa linkler** (bit.ly vb.) sunucuda `safe_fetch.py` ile çözülür:
  - yalnızca HEAD isteği atılır, en fazla 5 yönlendirme izlenir, toplam süre 3 saniyedir;
  - özel ya da iç ağ IP'lerine giden istekler engellenir (SSRF koruması);
  - zincirdeki her adres yeniden taranır.
- **RDAP'a** yalnızca domain gönderilir; sonuç 24 saat önbellekte tutulur. `.tr` gibi RDAP sunucusu olmayan uzantılarda bu kontrol atlanır.

### Katman 3: Mesaj metni
- `backend/data/text_patterns.json` içindeki Türkçe kalıplar aranır. Kalıplar dört grupta: aciliyet, kurum taklidi, ödül, bilgi isteme (IBAN, kart bilgisi, doğrulama kodu, şifre).
- Metin puanı en fazla **40** olabilir. Yani yalnızca metin hiçbir zaman "Tehlikeli" sonucu veremez.
- Metin ve kalıplar aynı Türkçe normalizasyondan geçer: `İ→i`, `I→ı`, sonra küçük harf, sonra `ç→c ğ→g ı→i ö→o ş→s ü→u`. Böylece "HESABINIZ", "Hesabınız" ve "hesabiniz" aynı sayılır.

### Katman 4: Topluluk bildirimleri
`POST /api/v1/domains/report` ile bir site bildirilebilir. **5 farklı cihazdan** bildirilen site topluluk kara listesine girer. Bu özelliğin arayüzü Faz 3'te bot korumasıyla (Turnstile) birlikte eklenecek.

### Toplam puan (kesinlik sırası)
1. Herhangi bir link kara listedeyse → **100**.
2. Mesajda link var ve **hepsi** resmî domainse → **0**. Metin puanı da eklenmez.
3. Diğer durumlarda → `min(100, en yüksek link puanı + metin puanı)`.

## 5. Kara listeler ve worker görevleri

**Dışarıdan veri çekme günde bir kez, gece yapılır** (karar: 15 Ekim). Saatlik ya da sürekli çalışan bir iş yok.

| Görev | Ne zaman | Ne yapar |
|---|---|---|
| `usom` | Her gece 03:30 | USOM'un tüm listesini indirir (~50 sayfa, sunucuda ~7 dk, CPU ~%85) |
| `urlhaus` | Her gece 03:50 | URLhaus metin dökümünü indirir (~2,7 MB) |
| `rdap-bootstrap` | Her gece 04:00 | Hangi uzantı için hangi RDAP sunucusunun kullanılacağını IANA'dan alır |
| `purge` | Her gece 04:30 | 7 gündür listede görülmeyen kayıtları siler. Bir kaynak 2 gündür hiç güncellenmediyse o kaynağı atlar; kesinti kara listeyi boşaltmaz |
| `sync` | Worker açılınca | Postgres'teki kara listeyi Redis'e (`blacklist:hosts`) kopyalar. Dışarıya istek atmaz, ~1,5 sn sürer |
| `usom-if-empty`, `urlhaus-if-empty` | Worker açılınca | **Yalnızca o listede hiç kayıt yoksa** (ilk kurulum, sıfırlanmış veritabanı) indirir. Aksi hâlde hiçbir şey yapmaz |
| `rdap-if-missing` | Worker açılınca | Yalnızca RDAP listesi Redis'te yoksa indirir |

Deploy ve yeniden başlatmalar worker'ı yeniden başlattığı hâlde fazladan indirme yapmaz.

**Bedeli:** yeni bir zararlı adres kara listemize en geç ~24 saat sonra girer. O süre içinde kural tabanlı kontroller (marka taklidi, riskli uzantı, yeni domain vb.) yine çalışır.

**Kullanıcıya bağlı istekler** zamanlanmış değildir, yalnızca birisi tarama yaptığında çalışır:
- mesajdaki kısa linkin nereye gittiğine bakılır;
- sitenin ne kadar yeni olduğu RDAP'a sorulur (domain başına 24 saatte en fazla bir kez).

**Notlar:**
- **USOM'un adresi değişti.** Eski `usom.gov.tr/url-list.txt` artık T.C. Siber Güvenlik Başkanlığı'nın sayfalı JSON API'sine (`siberguvenlik.gov.tr/api/address/index`) yönleniyor. Kod bu API'yi kullanıyor.
- **Hiç kara listeye alınmayan adresler:** `data/never_block.json`'daki ortak platformlar (github.com, drive.google.com…) ve resmî domainler kara listeye **hiçbir zaman** eklenmez. Bir platformun kullanıcı alt alan adı (ör. `evil.github.io`) ise eklenebilir. `suffixes` listesindeki ortak indirme sunucuları (ör. `download1350.mediafire.com`) hiç eklenmez.
- **Redis kapalıysa** kara liste sorguları Postgres'e düşer, rate limit de devre dışı kalır. Site çalışmaya devam eder.

## 6. Gizlilik ve KVKK: asla yapılmayacaklar

Bu kurallar CLAUDE.md'de "ihlal edilemez" olarak yazılı. Kod incelemesinde ilk bakılacak yer burası.

- ❌ **Mesaj metni** veritabanına, dosyaya, loga, Redis'e ya da hata takip aracına yazılmaz. Bunu kontrol eden testler var (`backend/tests/test_scan_privacy.py`).
- ❌ **Tam URL** saklanmaz; yalnızca alan adı (`scan_stats`).
- ❌ **IP adresi ve cihaz kimliği** düz metin saklanmaz; yalnızca `HMAC-SHA256(SECRET_KEY, değer)` saklanır. Erişim loglarında (Uvicorn ve Nginx) IP hiç yoktur.
- ❌ **Telefon numarası** loglara yazılmaz; `/numbers/...` yolları `/numbers/***` olarak maskelenir.
- ❌ **Frontend'de mesaj** URL'ye (route parametresi, query, hash) ve tarayıcı deposuna (localStorage, sessionStorage, IndexedDB) yazılmaz. Mesaj ve sonuç aynı ekranda, yalnızca bileşen state'inde durur.
- ❌ **Üçüncü taraf kaynak yok:** web sitesi dışarıdan font, analitik, CDN ya da reklam yüklemez ve çerez kullanmaz.
- ❌ **Kod içinde log:** exception mesajları ya da URL içeren loglar yazılmaz. Worker yalnızca sayı ve hata türü loglar; `httpx` logları WARNING seviyesindedir.
- ✅ **Doğrulama hataları** (422) gönderilen girdiyi geri döndürmez; hata mesajları Türkçedir.

## 7. Repo yapısı

```
/
├── CLAUDE.md                     # kurallar (tek doğruluk kaynağı)
├── README.md                     # kısa kurulum
├── docker-compose.yml            # GELİŞTİRME ortamı (api, worker, db, redis)
├── .env.example                  # geliştirme ayarları örneği
├── .github/workflows/
│   ├── ci.yml                    # her push'ta: backend, mobile, infra kontrolleri
│   └── deploy.yml                # CI geçince sunucuya otomatik deploy
├── docs/
│   ├── PROJE_REHBERI.md          # bu dosya
│   └── plans/faz-2-web.md        # Faz 2 planı
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI uygulaması
│   │   ├── config.py             # ayarlar (.env'den)
│   │   ├── api/                  # endpoint'ler: health, scan, domains
│   │   ├── core/                 # loglama, hata yönetimi, rate limit, HMAC, Türkçe normalizasyon
│   │   ├── scanner/              # TARAMA MOTORU
│   │   │   ├── pipeline.py       #   katmanları birleştirir
│   │   │   ├── extract.py        #   mesajdan link çıkarma
│   │   │   ├── url_rules.py      #   Katman 2 kuralları
│   │   │   ├── text_rules.py     #   Katman 3 kuralları
│   │   │   ├── blacklist.py      #   Katman 1 sorgusu
│   │   │   ├── safe_fetch.py     #   SSRF korumalı kısa link çözücü
│   │   │   ├── rdap.py           #   domain yaşı
│   │   │   └── hosts.py          #   hostname/domain yardımcıları
│   │   ├── services/             # istatistik, domain bildirimi, Türkçe sonuç metinleri
│   │   ├── models/               # veritabanı tabloları
│   │   └── worker/               # zamanlanmış görevler (USOM, URLhaus, temizlik)
│   ├── alembic/versions/         # veritabanı migration'ları
│   ├── data/                     # KURAL DOSYALARI (kod değiştirmeden güncellenebilir)
│   └── tests/                    # pytest (fixtures/messages: örnek mesajlar)
├── mobile/                       # Expo SDK 57 (web + Android)
│   ├── app/                      # sayfalar: index (tarama), hakkinda, gizlilik, kvkk
│   ├── components/               # ResultCard, ReasonList, AdviceSection, Icon, Footer…
│   ├── content/                  # Hakkında / Gizlilik / KVKK metinleri
│   ├── lib/                      # api.ts, theme.ts, legal.ts (yer tutucular), brand.ts (site adı)
│   └── __tests__/                # Jest testleri
└── infra/
    ├── docker-compose.prod.yml   # PRODUCTION ortamı
    ├── .env.prod.example         # production ayarları örneği
    ├── nginx/                    # Nginx imajı, ayarları, CSP kontrolü
    ├── scripts/                  # deploy, sertifika, yedek, kısıtlı SSH girişi
    └── README.md                 # sunucu kurulum rehberi
```

## 8. Kendi bilgisayarında çalıştırma (adım adım)

### Gerekenler
- **Docker Desktop** (macOS ya da Windows). Kurulup **açık** olmalı.
- **Git**
- **Node 24 LTS** (yalnızca `mobile/` için). Kontrol: `node --version`.
- Python ya da uv kurmanız **gerekmez**; backend tamamen Docker içinde çalışır.

### 1) Kodu çekin

```bash
git clone https://github.com/Damlayuksel/ScamShield.git
```

```bash
cd ScamShield
```

Windows'ta satır sonlarının bozulmaması için bir kez çalıştırın (macOS'ta gerek yok):

```bash
git config core.autocrlf false
```

### 2) Geliştirme ayarlarını oluşturun

```bash
cp .env.example .env
```

`.env` içindeki `SECRET_KEY` değerini rastgele bir değerle değiştirin:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

(`python3` yoksa herhangi bir uzun rastgele metin de olur; bu yalnızca sizin bilgisayarınız için.)

### 3) Backend'i başlatın

```bash
docker compose up -d --build
```

İlk seferde imajlar derlendiği için birkaç dakika sürer. Sonra veritabanı tablolarını oluşturun:

```bash
docker compose exec api alembic upgrade head
```

Worker, tablolar oluşmadan önce başladığı için ilk açılıştaki görevleri başarısız olmuştur. **Yalnızca ilk kurulumda** worker'ı bir kez yeniden başlatın:

```bash
docker compose restart worker
```

Kontrol: http://localhost:8000/api/v1/health adresi `{"status":"ok","db":"ok","redis":"ok"}` döndürmeli. API dokümantasyonu http://localhost:8000/docs adresinde (yalnızca geliştirmede açık).

Worker açılışta kara listeleri indirmeye başlar. USOM'un tam listesi yaklaşık 5–10 dakika sürer; ilerlemesini görmek için:

```bash
docker compose logs -f worker
```

`usom: 10/50 page(s) downloaded` gibi satırlar ve en sonda `usom updated: ... host(s)` görünür. Bitmesini beklemeden siteyi kullanabilirsiniz; o sürede yalnızca kara liste kontrolü eksik çalışır.

### 4) Web sitesini başlatın

```bash
cd mobile
```

```bash
npm install
```

Backend adresini tanımlayın (bu dosya git'e girmez):

```bash
cp .env.example .env.local
```

```bash
npx expo start --web
```

Tarayıcıda http://localhost:8081 açılır. Bir mesaj yapıştırıp tarayın. Backend'in CORS ayarı `localhost:8081`'e izin veriyor.

### 5) Durdurmak

```bash
docker compose down
```

Veritabanını da sıfırlamak isterseniz (`-v` tüm yerel veriyi siler):

```bash
docker compose down -v
```

## 9. Günlük çalışma akışı (tek dal, push = yayın)

Projede **tek dal var: `main`.** Feature dalı ve PR kullanılmıyor.

> ⚠️ **`main`'e push = yayına almak.** Push'tan sonra CI çalışır; geçerse değişiklik **otomatik olarak** lovelockapp.com'a çıkar. Yarım kalmış işleri push etmeyin.

**Her değişiklik için:**

1. Arkadaşınızın son değişikliklerini alın:

   ```bash
   git pull --rebase
   ```

2. Değişikliği yapın.
3. Testleri çalıştırın ([10. bölüm](#10-testler)).
4. Commit edin. Mesaj **İngilizce** ve [Conventional Commits](https://www.conventionalcommits.org/) biçiminde olmalı (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`):

   ```bash
   git commit -am "fix: short description of the change"
   ```

5. Tekrar çekip push edin:

   ```bash
   git pull --rebase && git push
   ```

6. GitHub → **Actions** sekmesinde **CI**'ın ve ardından **Deploy**'un yeşil olduğunu kontrol edin. Kırmızı olursa ilk iş onu düzeltin.

**Diğer kurallar:**
- Arayüz metinleri **Türkçe**; kod, değişken ve commit mesajları **İngilizce**.
- **Yeni paket eklerken:**
  - backend için `docker compose run --rm --no-deps api uv add <paket>` çalıştırın, ardından `docker compose build api worker`;
  - mobil için `npx expo install <paket>` kullanın (`npm install` değil).
  - Neden eklediğinizi commit mesajına yazın.
- Yapay zekâ / makine öğrenmesi kütüphanesi **eklenmez.**
- Tarama kuralı değiştirirseniz `backend/tests/fixtures/messages/` altına yeni bir örnek mesaj ekleyin.

**CI'da çalışan işler** (`.github/workflows/ci.yml`):

| İş | Kontroller |
|---|---|
| `backend` | ruff (lint + format), pytest (Postgres + Redis servisleriyle) |
| `mobile` | ESLint, Prettier, TypeScript, Jest, web build |
| `infra` | Production Compose dosyası, web imajı (CSP kontrolü dahil), `nginx -t` |

## 10. Testler

**Backend** (Docker açık olmalı):

```bash
docker compose exec api pytest
```

```bash
docker compose exec api ruff check . && docker compose exec api ruff format --check .
```

**Mobil** (`mobile/` klasöründe):

```bash
npm run lint && npm run format:check && npm run typecheck && npm test
```

**Testlerin kapsadıkları:**
- **Örnek mesajlar:** 17 dolandırıcı ve 11 resmî/sıradan mesaj (`backend/tests/fixtures/messages/`). Dolandırıcılar "Tehlikeli/Şüpheli", resmîler "Bilinen tehdit yok" çıkmalı.
- **Gizlilik:** mesaja ve URL'ye benzersiz bir işaretçi gömülüyor. Tarama sonrası bu işaretçi tüm tablolarda, Redis'te, loglarda ve dosyalarda aranıyor; hiçbirinde bulunmamalı.
- **SSRF:** özel ve iç ağ IP'leri, yasak portlar, yönlendirme zincirleri.
- **Kurallar:** marka taklidi, Türkçe karakterler, yanlış alarm örnekleri.
- **Mobil:** tarama akışı, sonuç kartı, renk kontrastı (WCAG AA), "mesaj URL'ye ya da depoya yazılmıyor" kontrolü, sayfalar.

## 11. Production: sunucu, deploy, yedek, izleme

Ayrıntılı kurulum adımları: [infra/README.md](../infra/README.md).

### Sunucu

| | |
|---|---|
| IP | `104.233.4.115` |
| SSH | port **25416**: `ssh -p 25416 root@104.233.4.115` |
| İşletim sistemi | Ubuntu 24.04, 4 GB RAM |
| Güvenlik duvarı (`ufw`) | yalnızca 25416, 80, 443 açık |
| Uygulama kullanıcısı | `deploy` (Docker grubunda, sudo yetkisi yok) |
| Kod | `/home/deploy/scamshield` |
| Ayarlar | `/home/deploy/scamshield/infra/.env.prod` (**gizli**, git'te yok) |
| Yedekler | `/var/backups/scamshield` |

- **Şifreler ve gizli değerler** bu dosyada yok. Root şifresi ekip içinde ayrıca paylaşılır.
- `SECRET_KEY` ve veritabanı şifresi yalnızca sunucudaki `.env.prod` dosyasında durur. Deploy anahtarı GitHub secret'larında saklanır.

### Otomatik deploy nasıl çalışıyor?

1. `main`'e push yapılır, ardından GitHub'da **CI** çalışır.
2. CI geçerse **Deploy** iş akışı (`deploy.yml`) başlar ve CI'ın test ettiği commit'i sunucuya SSH ile gönderir.
3. Sunucuda `infra/scripts/deploy.sh <commit>` çalışır, sırasıyla:
   - kodu o commit'e getirir (yalnızca `main`'deki commit'leri kabul eder),
   - imajları derler,
   - veritabanını ve Redis'i başlatır,
   - migration'ları uygular,
   - uygulamayı yeniden başlatır.
4. GitHub, `https://lovelockapp.com/api/v1/health` adresinin 200 döndüğünü kontrol eder.

**Güvenlik:**
- GitHub'daki deploy anahtarı sunucuda **yalnızca** `deploy <commit>` komutunu çalıştırabilir (`authorized_keys` içinde `restrict,command=` ile).
- Anahtar sızsa bile en fazla `main`'deki bir sürüm yeniden yüklenebilir.
- Sunucunun kimliği sabitlenmiş; GitHub başka bir sunucuya bağlanmaz.

**GitHub ayarları** (Settings → Secrets and variables → Actions):

| Tür | Ad | Not |
|---|---|---|
| Secret | `DEPLOY_HOST` | `104.233.4.115` |
| Secret | `DEPLOY_USER` | `deploy` |
| Secret | `DEPLOY_PORT` | `25416` |
| Secret | `DEPLOY_SSH_KEY` | Kısıtlı anahtar (tek satırlık base64). Sunucudan silindi, yalnızca GitHub'da |
| Secret | `DEPLOY_KNOWN_HOSTS` | Sunucunun kimlik satırı |
| Variable | `DEPLOY_URL` | `https://lovelockapp.com` |

**Elle deploy ya da geri dönüş** (sunucuda):

```bash
sudo -iu deploy sh /home/deploy/scamshield/infra/scripts/deploy.sh
```

Belirli bir sürüme geri dönmek için (commit `main`'de olmalı):

```bash
sudo -iu deploy sh /home/deploy/scamshield/infra/scripts/deploy.sh <commit-sha>
```

GitHub'dan elle başlatmak için: Actions → **Deploy** → **Run workflow** → `main`.

### HTTPS ve güvenlik başlıkları

- **Sertifika:** Let's Encrypt; `certbot` servisi 12 saatte bir yeniler, Nginx 6 saatte bir kendini yeniden yükler.
- **HSTS:** şimdilik 300 saniye (`HSTS_MAX_AGE`). **22 Ekim civarında** `.env.prod`'da `31536000` (1 yıl) yapılıp deploy edilecek. Domain ortak ve geçici olduğu için `includeSubDomains` kullanılmıyor.
- **CSP:** dışarıdan kaynak yükleme yasak. Expo'nun tek satır içi scripti hash ile izinli; yeni bir satır içi script çıkarsa web imajının build'i durur (`infra/nginx/check-csp.mjs`).
- **Diğer başlıklar:** nosniff, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, Permissions-Policy.

### Yedekleme

- Her gece **03:30**'da (sunucu Türkiye saatinde) `pg_dump` alınır. Yedekler **7 gün**, yalnızca bu sunucuda saklanır.
- Elle yedek ve geri yükleme komutları [12. bölümde](#12-sık-kullanılan-sunucu-komutları).

### İzleme

- **UptimeRobot:** `https://lovelockapp.com/api/v1/health` ve `https://lovelockapp.com` adresleri 5 dakikada bir kontrol ediliyor. Site kapanırsa e-posta geliyor.
- **Nginx logları:** zaman, istek yöntemi, yol (numaralar maskeli), durum kodu, boyut ve süre. IP adresi yok.

## 12. Sık kullanılan sunucu komutları

Önce sunucuya bağlanın:

```bash
ssh -p 25416 root@104.233.4.115
```

Komutları kısaltmak için oturum başında bir kısayol tanımlayın:

```bash
alias dc='sudo -iu deploy docker compose -f /home/deploy/scamshield/infra/docker-compose.prod.yml --env-file /home/deploy/scamshield/infra/.env.prod'
```

| Ne yapmak istiyorsunuz? | Komut |
|---|---|
| Servislerin durumu | `dc ps` |
| API / web logları | `dc logs --tail 50 api web` |
| Worker logu (canlı) | `dc logs -f worker` |
| Kara liste kayıt sayısı | `dc exec -T db psql -U scamshield -d scamshield -c "select source, count(*) from blacklist_domains group by source;"` |
| Worker'ı yeniden başlat | `dc restart worker` |
| Bir worker görevini elle çalıştır | `dc exec worker python -m app.worker.run_once urlhaus` (görevler: `usom`, `urlhaus`, `rdap-bootstrap`, `purge`, `sync`, `usom-if-empty`, `urlhaus-if-empty`, `rdap-if-missing`) |
| Sunucudaki sürüm | `sudo -iu deploy git -C /home/deploy/scamshield log --oneline -1` |
| Elle yedek | `sudo -iu deploy sh /home/deploy/scamshield/infra/scripts/backup-db.sh` |
| Yedekleri listele | `ls -lh /var/backups/scamshield` |
| Yedekten geri yükle (**mevcut verinin üzerine yazar**) | `gunzip -c /var/backups/scamshield/<dosya>.sql.gz \| dc exec -T db psql -U scamshield -d scamshield` |
| Sertifika durumu | `dc run --rm --entrypoint certbot certbot certificates` |
| fail2ban durumu | `fail2ban-client status sshd` |

## 13. Kural dosyalarını güncelleme

Kural dosyaları `backend/data/` altında. Kod değiştirmeden güncellenebilirler; değişiklik, push ve otomatik deploy sonrası API yeniden başlayınca geçerli olur.

| Dosya | İçerik | Ne zaman güncellenir? |
|---|---|---|
| `official_domains.json` | Resmî kurum, banka ve kargo domainleri (kayıtlı domain) | Yeni bir resmî kurum ya da banka domaini |
| `brands.json` | Taklit edilen markalar ve anahtar kelimeleri | Yeni bir dolandırıcılık dalgasında taklit edilen marka |
| `text_patterns.json` | Türkçe mesaj kalıpları (regex + ağırlık + gerekçe) | Yeni bir dolandırıcılık metni |
| `never_block.json` | Asla kara listeye alınmayacak ortak platformlar | Kara listede yanlış alarm veren ortak bir platform |
| `shorteners.json` | Kısa link servisleri | Yeni bir kısa link servisi |
| `risky_tlds.json` | Riskli uzantılar | — |

**Kurallar:**
- `text_patterns.json`'a kalıp eklerken Türkçe ekleri hesaba katın; kökün sonuna `\w*` koyun. Örneğin `savci\w*` yazarsanız "savcılığından" da yakalanır.
- Her yeni kural için `backend/tests/fixtures/messages/` altına bir örnek mesaj ekleyip testleri çalıştırın.
- Bu listeler ekipçe gözden geçirilmeli; `official_domains.json`'a yanlış bir domain eklenirse o domain her zaman "güvenli" sayılır.

## 14. Alınan kararlar (karar günlüğü)

CLAUDE.md'deki ilk plandan farklı olan ya da sonradan netleşen kararlar:

| Tarih | Karar | Neden |
|---|---|---|
| 14.10 | Tüm linkler resmîyse sonuç **0**, metin puanı eklenmez | Proje sahibinin tercihi |
| 14.10 | Kara liste eşleşmesi **hostname** bazında + `never_block.json` | USOM/URLhaus'ta github.com gibi ortak platformlardaki zararlı URL'ler var; tam URL saklanamadığı için |
| 14.10 | `never_block.json`'a `suffixes` eklendi | URLhaus'taki binlerce `downloadNNNN.mediafire.com` kaydı yanlış alarm üretirdi |
| 14.10 | Loglarda telefon numarası maskelenir, IP hiç yazılmaz | KVKK |
| 14.10 | USOM, sayfalı JSON API'den çekiliyor | Eski `url-list.txt` artık bir API sayfasına yönleniyor |
| 14.10 | Marka yazım hatası kuralı: OSA + ilk harf + uzunluk sınırı | Düz Levenshtein ≤ 2 Türkçe kelimelerde çok yanlış alarm verdi ("firsat"→Ziraat) |
| 14.10 | `@` kontrolü yalnızca adres kısmında | Sorgudaki e-posta adresleri yanlış alarm vermesin |
| 14.10 | Node 24 LTS, Expo SDK 57 | Güncel LTS ve SDK |
| 14.10 | Webde renkler CSS değişkeni | Statik HTML açık temayla üretiliyor, React hydration stilleri düzeltmiyor; koyu temada yazılar görünmüyordu |
| 14.10 | Webde `Stack` yerine `Slot`, sayfa geçişinde en üste kaydırma | Eski sayfa DOM'da kalıyordu, yeni sayfa ortasından açılıyordu |
| 14.10 | "Bu siteyi şikâyet et" düğmesi Faz 3'e | Bot koruması (Turnstile) olmadan kötüye kullanılabilir |
| 14.10 | Google Web Risk kullanılmıyor | Proje sahibinin tercihi |
| 14.10 | Geçici domain: lovelockapp.com | Kalıcı domain henüz yok |
| 15.10 | **Tek dal (`main`)**, PR yok | Ekip için daha sade |
| 15.10 | **Otomatik deploy** (CI geçince) | Proje sahibinin tercihi |
| 15.10 | GitHub secret'ları repo düzeyinde | Ücretsiz planda özel repolarda "Environments" yok |
| 15.10 | Sunucuya şifreyle giriş şimdilik açık, fail2ban önerildi | Proje sahibinin tercihi; sonra anahtara geçilecek |
| 15.10 | İkonlar SVG olarak gömülü | 1,3 MB'lık ikon fontu kaldırıldı; ilk yükleme 1,8 MB'tan 0,34 MB'a indi |
| 15.10 | **Dış veri çekme günde bir** (gece); açılışta yalnızca veri yoksa indirme | Sunucuyu ve dış servisleri gereksiz yere yormamak (proje sahibinin tercihi). Yeni zararlı adresler en geç ~24 saatte listeye girer |

## 15. Değişiklik geçmişi

| Commit | Ne yapıldı |
|---|---|
| `3bf8f6c` | Repo iskeleti, CLAUDE.md, README, `.env.example` |
| `506cd46` | FastAPI iskeleti, Docker Compose, CI, gizlilik odaklı hata yönetimi ve loglama |
| `146cde7` | Veritabanı modelleri ve Alembic migration'ları |
| `a65cbc1` | USOM ve URLhaus worker'ı, kara liste sorgusu (Redis + Postgres) |
| `874968c` | URL kuralları ve mesajdan link çıkarma |
| `4224242` | SSRF korumalı kısa link çözücü ve RDAP domain yaşı |
| `b1200fd` | Türkçe mesaj metni kuralları |
| `9856a99` | Tarama pipeline'ı, `POST /api/v1/scan`, rate limit, gizlilik testleri, örnek mesajlar |
| `1599286` | Topluluk domain bildirimi (Katman 4) |
| `1c36a73` | Expo SDK 57 iskeleti (web + mobil), tema, CI'da mobil işi |
| `9c47d9c` | Tarama ve sonuç ekranı |
| `d983253` | Hakkında, Gizlilik ve KVKK sayfaları, alt bilgi |
| `ed55069` | Production Docker Compose, Nginx, HTTPS, yedek ve deploy betikleri |
| `ccea6d3` | GitHub Actions ile otomatik deploy |
| `882b517` – `a9b11a8` | Tüm işler `main`'e alındı, tek dala geçildi |
| `a83d83a` | Deploy'da migration önce çalışıyor; USOM listesi boşsa kendini dolduruyor; yedek hatası artık görünüyor |
| `e3f859f` | USOM indirmesinde ilerleme logu ve 30 dk süre sınırı |
| `c2df5aa`, `c57ed26` | Deploy secret'ları repo düzeyinde; deploy anahtarı tek satır base64 olarak da kabul ediliyor |
| `692921a` | Başarılı sağlık kontrolleri loga yazılmıyor |
| `bd8a84c` | İkon fontu yerine SVG ikonlar (5 kat daha az veri) |

Ayrıntı için: `git log --oneline`.

## 16. Karşılaşılan sorunlar ve çözümleri

| Sorun | Çözüm |
|---|---|
| `docker: failed to connect to the docker API` | Docker Desktop açık değil; uygulamayı açıp bekleyin |
| `uv add` sırasında `Permission denied: uv.lock` (Windows) | Dosya root olarak oluşmuş: `docker compose exec -u root api chmod 666 /app/uv.lock` |
| Mobilde TypeScript hatası: yeni sayfa için "not assignable to Href" | `.expo/` içindeki eski typed-routes tipleri. `mobile/.expo` klasörünü silin ya da `npx expo start` ile yeniden oluşturun |
| DNS panelinde "CNAME and other data" hatası | Bir adda CNAME varken başka kayıt olamaz. `www` CNAME'ini `lovelockapp.com`'a yönlendirin, `www` için ayrıca A kaydı eklemeyin |
| Site bazen eski siteyi gösteriyor | Aynı ad için iki A kaydı var. Eski IP'li kaydı silin; `nslookup lovelockapp.com ns1.iyibuldum.com` ile kontrol edin |
| Deploy: `Load key ...: error in libcrypto` | `DEPLOY_SSH_KEY` secret'ı kopyalarken bozulmuş. Sunucuda yeni bir kısıtlı anahtar üretip `base64 -w0 <dosya>` çıktısını secret olarak girin |
| İlk deploy'dan sonra USOM listesi boş | Worker tablolardan önce başlamıştı (düzeltildi, `a83d83a`). Gerekirse `dc restart worker` |
| İlk USOM indirmesi "takıldı" gibi görünüyor | Sunucuda yaklaşık 7 dakika sürüyor; `dc logs -f worker` ile ilerlemesini izleyin |
| Terminale çıktı yapıştırınca `command not found` satırları | Zararsız; yalnızca komut satırını yapıştırın |

## 17. Açık işler ve sonraki adımlar

**Yayın öncesi eksikler (Faz 2'yi tam bitirmek için):**
- [ ] **Sunucu sağlayıcısı ve ülkesi:** KVKK metnindeki yurt dışı aktarım bölümü buna bağlı.
- [ ] **Veri sorumlusu bilgileri:** ad/unvan, adres, iletişim e-postası.
- [ ] **Saklama süreleri:** `scan_stats` ve `domain_reports` için (ör. 12 ay). Karar sonrası worker'a temizlik görevi eklenecek.
- [ ] **Avukat incelemesi:** `/gizlilik` ve `/kvkk` metinleri.

Bu bilgiler `mobile/lib/legal.ts` dosyasına girilir. Biri bile eksikse Gizlilik ve KVKK sayfalarında "taslak" uyarısı görünür.

**Bakım:**
- [ ] **HSTS süresini uzatmak (22 Ekim civarı):** `.env.prod`'da `HSTS_MAX_AGE=31536000` yapıp deploy edin.
- [ ] **Telefon testi:** Android Chrome ve iPhone Safari'de, açık ve koyu temada deneme; SSL Labs ve securityheaders.com notları.
- [ ] **SSH:** sunucuya şifre yerine anahtarla girişe geçmek (sonra şifreyle girişi kapatmak); fail2ban'ı kurmak.
- [ ] **Liste kontrolü:** ekipçe `official_domains.json`, `never_block.json` ve `brands.json` listelerini gözden geçirmek.
- [ ] **URLhaus Auth-Key (isteğe bağlı):** abuse.ch'de ücretsiz hesap açıp `.env.prod`'a eklemek.
- [ ] **Kalıcı domain ve site adı:** karar verilince `.env.prod`'daki `DOMAIN` ve DNS değişir; site adı `mobile/lib/brand.ts`'te.

**Faz 3: Şüpheli numara sistemi**
- Numara bildirme, sorgulama, liste ve itiraz ekranları; rate limit; web formlarında Cloudflare Turnstile.
- **Gerekenler:** Cloudflare hesabı ve Turnstile site key/secret.

**Faz 4: Android uygulaması**
- EAS Build ile Android, mağaza hazırlığı ve Paylaş menüsünden metin alma. Alınan metin sadece bellekte tutulur; kullanıcı "Mesajı kontrol et" dediğinde `/scan` çağrılır.
- **Gerekenler:** Expo hesabı, Google Play Console hesabı (tek seferlik ücret), Android paket adı.
