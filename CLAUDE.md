# Dolandırıcılık Engelleme Uygulaması (Yapay Zekâsız)

Bu dosya projenin tek doğruluk kaynağıdır. Claude Code ve ekip üyeleri her oturumda bu kurallara uyar. Burada yazmayan bir konuda karar vermek gerekiyorsa önce sor, varsayım yapma.

## Proje özeti

Türkiye'deki kullanıcılar için dolandırıcılık engelleme uygulaması. **Yapay zekâ / makine öğrenmesi kullanılmaz**; tüm kararlar kara listeler, kural tabanlı kontroller ve topluluk bildirimleriyle verilir.

İki ana özellik:

1. **Mesaj / link tarama:** Kullanıcı şüpheli bir mesajı (SMS, WhatsApp vb.) yapıştırır. Sistem mesajdaki linkleri ve metni tarar, sonucu bildirir. Mesaj **hiçbir şekilde saklanmaz** (KVKK).
2. **Şüpheli numara bildirme:** Kullanıcı dolandırıcı olduğunu anladığı bir telefon numarasını işaretler. Numaralar liste hâlinde, kaç kez işaretlendiğiyle birlikte görünür. Numara aranarak da sorgulanabilir.

**Planlanan premium özellik — uzman ikinci görüşü:** Otomatik tarama sonucundan sonra kullanıcı isteğe bağlı olarak bir insan incelemeciden değerlendirme talep edebilir. Özellik henüz geliştirilmemiştir; ücretlendirme, inceleme süresi ve anonim taleplerin takibi tasarlanmamıştır. İnceleme öncesi açık onay alınmalı, kullanıcıya hangi içeriğin kimlerle ve ne amaçla paylaşılacağı ile saklama/silme süresi bildirilmelidir. İncelemeciye yalnızca gerekli asgari içerik aktarılmalı, kişisel veriler mümkün olduğunca ayıklanmalı ve inceleme için belirlenen süre sonunda silinmelidir. Otomatik tarama, inceleme talebi olmadan mesaj içeriğini saklamaz.

**Kullanıcı hesabı yoktur.** Uygulama tamamen anonim çalışır.

Ekip: 2 geliştirici, biri macOS biri Windows. Tüm geliştirme Docker içinde yapılır.

## Teknoloji kararları

| Alan | Seçim |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Paket yönetimi (Python) | uv (`pyproject.toml` + `uv.lock`) |
| Veritabanı | PostgreSQL 16 |
| ORM / migration | SQLAlchemy 2.x (async) + Alembic |
| Önbellek / rate limit | Redis 7 |
| Zamanlanmış görevler | APScheduler, ayrı `worker` container'ında |
| HTTP istemcisi | httpx (async) |
| Domain ayrıştırma | tldextract |
| Benzerlik (marka taklidi) | rapidfuzz |
| Telefon numarası | phonenumbers (E.164 normalizasyonu) |
| Frontend | Expo SDK 57, TypeScript, Expo Router (web + Android; rotalar `mobile/app/`) |
| Web | react-native-web; Expo statik web build (`web.output: "static"`), Nginx ile sunulur |
| Veri çekme (frontend) | TanStack Query |
| Node | 24 LTS |
| Sunucu | Ubuntu 24.04, Docker Compose, Nginx, Let's Encrypt (certbot) |
| Test | pytest + pytest-asyncio (backend), Jest + React Native Testing Library (frontend) |
| Lint / format | ruff (Python), ESLint + Prettier (TS) |
| CI | GitHub Actions |

Web sitesi ve Android uygulaması **aynı Expo kod tabanından** üretilir. Ayrı bir web projesi açılmaz.

## Repo yapısı

```
/
├── CLAUDE.md
├── README.md
├── docker-compose.yml          # geliştirme ortamı
├── .env.example
├── .gitattributes
├── .github/workflows/ci.yml
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py           # pydantic-settings, .env okur
│   │   ├── db.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/                # router'lar: scan.py, numbers.py, domains.py
│   │   ├── scanner/            # tarama motoru
│   │   │   ├── pipeline.py
│   │   │   ├── url_rules.py
│   │   │   ├── text_rules.py
│   │   │   ├── blacklist.py
│   │   │   └── safe_fetch.py   # SSRF korumalı yönlendirme çözücü
│   │   ├── services/
│   │   └── worker/             # USOM/URLhaus liste güncelleme görevleri
│   ├── data/                   # kurallar: official_domains.json, brands.json, text_patterns.json,
│   │                           #   never_block.json, shorteners.json, risky_tlds.json
│   └── tests/
├── mobile/                     # Expo uygulaması (web + Android)
│   ├── app/                    # Expo Router ekranları
│   ├── components/
│   ├── lib/api.ts
│   └── ...
└── infra/
    ├── docker-compose.prod.yml
    └── nginx/
```

## Docker

- `docker compose up` ile şu servisler ayağa kalkar: `api`, `worker`, `db`, `redis`.
- Expo geliştirme sunucusu Docker dışında, yerel makinede çalışabilir (`cd mobile && npx expo start`). Mobil cihaz / simülatör bağlantısı container içinde sorun çıkarır.
- `mobile/` içinde paket eklerken `npx expo install <paket>` kullanılır (SDK ile uyumlu sürümü seçer); geliştirme paketleri `devDependencies`'e girer.
- Kaynak kod volume ile bağlanır, `api` servisi `--reload` ile çalışır.
- Windows uyumluluğu: shell script yerine Python veya `Makefile` alternatifi olarak `docker compose` komutları README'de yazılır. Script gerekiyorsa `.sh` dosyaları container içinde çalıştırılır.

## Mesaj / link tarama sistemi

Katmanlı puanlama sistemi. Her katman 0–100 arası puana katkı yapar.

**Sonuç seviyeleri**
- **Tehlikeli:** 70 ve üzeri
- **Şüpheli:** 30–69
- **Bilinen tehdit yok:** 0–29

Sistem hiçbir zaman "kesinlikle güvenli" demez. En iyi sonuç metni: "Bilinen bir tehdit bulunamadı, yine de dikkatli olun."

Her sonuçta kullanıcıya **Türkçe gerekçe listesi** gösterilir (ör. "Bu adres 'ziraat' markasını taklit ediyor olabilir").

### Katman 1: Kara listeler
- **USOM** zararlı bağlantılar listesi: eski `usom.gov.tr/url-list.txt` artık T.C. Siber Güvenlik Başkanlığı'nın sayfalı JSON API'sine (`https://siberguvenlik.gov.tr/api/address/index`) yönleniyor. `worker` tüm listeyi **günde bir kez** (gece 03:30) çeker; `blacklist_domains` tablosuna yükler ve Redis hash'ine (`blacklist:hosts`) kopyalar. Sorgu yerelde yapılır.
- **URLhaus (abuse.ch):** günde bir kez (gece 03:50) toplu metin dökümü alınır (Auth-Key tanımlıysa başlıkta gönderilir), aynı şekilde yerelde tutulur.
- Bir kaynak 2 gündür hiç güncellenmediyse eski kayıt temizliği o kaynak için atlanır (kaynak kesintisi kara listeyi boşaltmaz).
- **Dış veri çekme günde birdir** (karar: 2026-10-15). Worker açılırken (deploy, yeniden başlatma) dışarıdan veri çekilmez; yalnızca bir kaynağın verisi hiç yoksa (ilk kurulum, sıfırlanan veritabanı ya da Redis) o kaynak indirilir. Bedeli: yeni bir zararlı adres kara listemize en geç ~24 saat sonra girer.
- **Google Web Risk API kullanılmıyor** (karar: 2026-10-14). Eklenmesi istenirse önce bu dosyada karar güncellenir; Safe Browsing değil Web Risk kullanılır ve yalnızca hash-prefix yöntemiyle sorgulanır.
- Topluluk kara listesi: Katman 4'ten eşiği geçen domainler.
- Kara listede eşleşme → puan 100, sonuç doğrudan "Tehlikeli".

### Katman 2: Kural tabanlı URL analizi
| Kontrol | Puan |
|---|---|
| Resmî alan adı beyaz listesinde tam eşleşme (`data/official_domains.json`) | sonuç doğrudan 0 |
| Marka taklidi (marka adı domainde geçiyor veya Levenshtein ≤ 2) | +40 |
| Punycode / taklit karakter (`xn--`) | +30 |
| Domain yaşı < 30 gün (RDAP) | +30 |
| Ham IP adresli URL | +20 |
| URL'de `@` karakteri | +20 |
| 3'ten fazla alt alan adı | +10 |
| Riskli TLD (.xyz, .top, .shop, .online, .site, .click …) | +10 |
| Link kısaltıcı (çözülemezse) | +10 |

- Domain ayrıştırma **her zaman** `tldextract` ile yapılır (`turkiye.gov.tr.giris-yap.xyz` → `giris-yap.xyz`). String içinde arama (`in`) ile resmî domain kontrolü yapılmaz.
- Kısaltılmış linkler `safe_fetch.py` ile çözülür, nihai adres yeniden taranır.
- RDAP sonuçları domain bazında Redis'te 24 saat önbelleğe alınır.

### Katman 3: Mesaj metni kuralları
- Kalıplar `data/text_patterns.json` dosyasında tutulur (regex + ağırlık + Türkçe açıklama). Kod değiştirmeden güncellenebilir.
- Kategoriler: aciliyet ("son gün", "24 saat içinde", "hesabınız askıya alınacak"), kurum taklidi (e-Devlet, PTT, kargo, gümrük ücreti), ödül ("kazandınız", "iade alacağınız var"), bilgi isteme (IBAN, kart bilgisi, doğrulama kodu, şifre).
- Metin puanı en fazla 40'tır; tek başına "Tehlikeli" sonucu üretemez.
- Regex'ler Türkçe karakter ve büyük/küçük harf duyarsız çalışır (`İ/i`, `I/ı` sorununa dikkat).

### Katman 4: Topluluk bildirimleri
- Kullanıcı bir domaini şüpheli olarak bildirebilir.
- 5 farklı cihazdan bildirim alan domain topluluk kara listesine girer.
- Bildirilen değer hostname'e normalize edilir (link de kabul edilir). Resmî beyaz listedeki ve `never_block.json`'daki adresler bildirilemez.
- Aynı cihazın tekrar bildirimi sessizce kabul edilir ama sayılmaz; yanıt bildirim sayısını göstermez.

### Toplam puan
`toplam = min(100, en_yüksek_link_puanı + metin_puanı)`

Kesinlik sırası:
1. Herhangi bir link kara listedeyse → toplam 100, "Tehlikeli".
2. Mesajda en az bir link var ve **tüm** linkler resmî beyaz listedeyse → toplam 0, metin puanı eklenmez.
3. Diğer durumlarda beyaz listedeki linkler 0 puan alır, diğerleri kurallarla puanlanır ve yukarıdaki formül uygulanır.

### Tarama ayrıntıları
- **Kara liste eşleşmesi hostname bazındadır.** Normalize edilmiş tam hostname saklanır (küçük harf, IDNA, port ve sondaki nokta atılır). Sorgu hostname'in kendisi ve kayıtlı domaine kadar olan üst alan adlarıyla yapılır (`a.evil.com` → `a.evil.com`, `evil.com`).
- `data/never_block.json` (github.com, github.io, drive.google.com vb. ortak platformlar) ve resmî beyaz liste kara listeye **hiçbir zaman** eklenmez; bu hostlardaki kaynak girdileri atlanır. `hosts` tam eşleşmedir (kullanıcı alt alan adları, ör. `evil.github.io`, yine kara listeye girebilir); `suffixes` ise tüm alt alan adları platformun ortak altyapısı olan sonekleri korur (ör. `download1350.mediafire.com`).
- Bilinen bir public suffix'i olmayan hostlar (ör. `.example`) yalnızca tam host olarak eşleşir.
- USOM/URLhaus'tan 7 gün boyunca görülmeyen kayıtlar silinir.
- Tarama başına en fazla 10 link işlenir.
- **Türkçe normalizasyon:** `İ→i`, `I→ı`, sonra `lower()`, sonra ASCII katlama (`ç→c ğ→g ı→i ö→o ş→s ü→u`). Metin ve kalıplar aynı fonksiyondan geçer.
- **Marka taklidi:** domain etiketleri (public suffix hariç) `.` ve `-` ile parçalanır, Türkçe/benzer karakterler Latin'e katlanır.
  - 4+ karakterli anahtar kelimeler: etiketler birleştirilmiş metinde alt dize olarak aranır.
  - 5+ karakterli anahtar kelimeler ayrıca yazım hatası olarak aranır (OSA mesafesi, yer değiştirme = 1). Yanlış alarmı önlemek için (ör. "firsat"/"ziraat", "hazir"/"hazine") ilk harf aynı olmalı, uzunluk farkı en fazla 1 olmalı; mesafe 6 harfe kadar ≤ 1, daha uzunlarda ≤ 2'dir.
  - Daha kısa markalar (ptt, ing) yalnızca tam parça eşleşmesi alır.
  - Punycode decode edilip aynı kontrolden geçer.
- **`@` kontrolü** URL'nin yalnızca adres (authority) kısmına bakar (`https://banka.com.tr@evil.com`); sorgu dizesindeki e-posta adresleri puan almaz.
- **RDAP:** IANA bootstrap worker tarafından günde bir alınır. RDAP sunucusu olmayan TLD'lerde kontrol puan vermeden atlanır. RDAP'a yalnızca domain gönderilir.
- **Redis erişilemezse:** kara liste sorgusu Postgres'e düşer, rate limit fail-open çalışır (içeriksiz uyarı logu).

## Şüpheli numara sistemi

- Tüm numaralar `phonenumbers` ile **E.164** formatına normalize edilir, varsayılan bölge `TR` (`0532…`, `532…`, `+90532…` aynı kayıttır).
- Geçersiz numaralar reddedilir.
- Bildirimde kategori seçilir: `sahte_banka`, `kargo`, `sahte_kamu_gorevlisi` (polis/savcı), `yatirim_kripto`, `cekilis_odul`, `diger`.
- İsteğe bağlı kısa açıklama (en fazla 280 karakter). Açıklama içinde başka numara, IBAN veya isim olup olmadığı basit regex ile kontrol edilir ve maskelenir.
- **Kamuya gösterim eşiği:** Bir numara en az **3 farklı cihazdan** bildirim almadan listede ve aramada "şüpheli" olarak görünmez. Eşiğin altındaysa "Yeterli bildirim yok" denir.
- **İtiraz:** Numarasının haksız işaretlendiğini düşünen kişi kaldırma talebi gönderebilir. Talepler `number_disputes` tablosuna düşer, elle incelenir. İnceleme süresince numara "itiraz edildi" etiketiyle gösterilir.

### Hesapsız kötüye kullanım önleme
- Uygulama ilk açılışta rastgele bir **cihaz kimliği (UUID)** üretir. Mobilde `expo-secure-store`, web'de `localStorage` içinde tutar. Her istekte `X-Device-Id` başlığıyla gönderir.
- Sunucu cihaz kimliğini ve IP adresini **asla düz metin saklamaz**; `HMAC-SHA256(SECRET_KEY, değer)` olarak saklar.
- Aynı cihaz aynı numarayı yalnızca **bir kez** bildirebilir.
- Rate limit (Redis):
  - Tarama: IP başına dakikada 20 istek
  - Numara bildirimi: cihaz başına saatte 10, IP başına saatte 20
  - Domain bildirimi: cihaz başına saatte 10
- Web'de bildirim formlarında Cloudflare Turnstile kullanılır (Faz 3).
- IP hash'leri 30 gün sonra silinir (worker görevi).

## API uç noktaları

Tümü `/api/v1` altındadır.

| Metot | Yol | Açıklama |
|---|---|---|
| POST | `/scan` | `{ "text": "..." }` alır, sonuç döner. **Hiçbir şey kaydetmez** (yalnızca `scan_stats`). Metin en fazla 5000 karakter. |
| POST | `/numbers/report` | Numara bildirir |
| GET | `/numbers/{phone}` | Numaranın durumu, bildirim sayısı, kategori dağılımı |
| GET | `/numbers` | En çok bildirilen numaralar (sayfalı, eşiği geçenler) |
| POST | `/numbers/{phone}/dispute` | İtiraz talebi |
| POST | `/domains/report` | Domain bildirir |
| GET | `/health` | Sağlık kontrolü |

Hata mesajları kullanıcıya Türkçe döner. API dokümantasyonu FastAPI'nin `/docs` sayfasından alınır; production'da kapatılır.

## Veritabanı tabloları

- `blacklist_domains`: domain, kaynak (`usom`, `urlhaus`, `community`), eklenme tarihi, son görülme
- `reported_numbers`: id, telefon (E.164, unique), toplam bildirim, ilk/son bildirim tarihi, durum (`active`, `disputed`, `removed`)
- `number_reports`: id, number_id, device_hash, ip_hash, kategori, açıklama, tarih. `(number_id, device_hash)` unique
- `number_disputes`: id, number_id, açıklama, iletişim (isteğe bağlı e-posta), durum, tarih
- `domain_reports`: id, domain, device_hash, tarih. `(domain, device_hash)` unique
- `scan_stats`: id, domain (tam URL değil), sonuç seviyesi, tarih

**Hiçbir tabloda mesaj metni, tam URL, düz IP veya düz cihaz kimliği bulunmaz.**

## Güvenlik ve KVKK kuralları (ihlal edilemez)

1. Mesaj metni yalnızca istek süresince bellekte kalır. Veritabanına, dosyaya, loga, Redis'e, hata takip aracına yazılmaz.
2. Uvicorn ve Nginx loglarında request body loglanmaz. Hata durumunda exception loglarına mesaj içeriği eklenmez.
3. `/scan` için yazılan testler, metnin hiçbir kalıcı depoya yazılmadığını doğrular.
4. Linkler sunucuda tarayıcıyla açılmaz. `safe_fetch.py` yalnızca `HEAD` (gerekirse `GET` ile ilk birkaç KB) istek atar, JavaScript çalıştırmaz, en fazla 5 yönlendirme izler, timeout 3 saniyedir.
5. **SSRF koruması:** Her istek ve her yönlendirme adımında DNS çözümlenir; çözümlenen IP özel, loopback, link-local, multicast veya ayrılmış aralıktaysa istek reddedilir. Yalnızca 80 ve 443 portlarına izin verilir.
6. Dış API'lere tam URL gönderilmez. Kara liste sorguları yerelde yapılır; RDAP'a yalnızca kayıtlı domain gönderilir.
7. Telefon numarası kişisel veridir: eşik altındaki numaralar gösterilmez, itiraz mekanizması zorunludur.
8. Gizli anahtarlar yalnızca `.env` içindedir. `.env` git'e eklenmez; `.env.example` güncel tutulur.
9. CORS yalnızca kendi domainimize ve Expo geliştirme adreslerine izin verir.
10. Production'da HTTPS zorunludur (Nginx + Let's Encrypt), HTTP istekleri HTTPS'e yönlendirilir.
11. Gizlilik politikası ve KVKK aydınlatma metni web sitesinde yayınlanır (Faz 2).
12. Telefon numarası URL yolunda geçtiği için Uvicorn ve Nginx erişim loglarında `/numbers/<herhangi>` yolu `/numbers/***` olarak maskelenir. Erişim loglarında istemci IP adresi de yer almaz; Nginx `error_log` seviyesi `crit`'tir (daha düşük seviyeler istemci IP'si yazar).
13. `httpx`/`httpcore` loggerları WARNING seviyesinde tutulur (INFO'da URL loglarlar). Doğrulama hatası yanıtları gönderilen girdiyi (`input`) geri döndürmez.
14. İstemci IP'si için `X-Forwarded-For` yalnızca `TRUSTED_PROXIES` içindeki proxy'den (Nginx) gelirse kabul edilir.
15. Frontend'de mesaj metni **URL'ye** (route parametresi, query string, hash) ve **tarayıcı deposuna** (`localStorage`, `sessionStorage`, IndexedDB, kalıcı sorgu önbelleği) yazılmaz. Tarama ve sonuç aynı ekranda, yalnızca bileşen state'inde tutulur.
16. Web sitesi üçüncü taraf kaynak yüklemez (font, analitik, CDN, reklam yok) ve çerez kullanmaz.
17. Android'de paylaşılan mesaj `expo-sharing` ile yalnızca bellekte alınır; `getResolvedSharedPayloadsAsync()` kullanılmaz (paylaşılan URL'yi cihazdan doğrudan açabilir ve SSRF korumasını atlar). Yalnızca `text/plain` kabul edilir, kullanıcı "Mesajı kontrol et" dediğinde `/scan` çağrılır ve native paylaşım yükü hemen temizlenir.

## Arayüz

- Arayüz dili **Türkçe**. Kod, değişken, fonksiyon ve commit mesajları **İngilizce**.
- Hedef kitle teknik olmayan kişiler: büyük yazı, sade dil, teknik terim yok.
- Sonuç ekranı renk kodlu: kırmızı (Tehlikeli), sarı (Şüpheli), yeşil (Bilinen tehdit yok). Renk tek başına anlam taşımaz; ikon ve metin de bulunur.
- Her sonuçta "Ne yapmalıyım?" bölümü: linke tıklamayın, bilgi paylaşmayın, bankanızı arayın, USOM'a / 155'e bildirin vb.
- Ekranlar: Ana sayfa (mesaj tara), Numara sorgula, Numara bildir, Şüpheli numaralar listesi, Hakkında / Gizlilik.
- Açık ve koyu tema desteklenir.

## Geliştirme aşamaları

Her faz bitmeden sonrakine geçilmez. Her faz küçük, tek amaçlı commit'ler hâlinde ilerler.

**Faz 1: Altyapı ve tarama API'si**
- Docker Compose (api, worker, db, redis), Alembic, temel yapılandırma
- USOM ve URLhaus liste güncelleme görevi
- Tarama motoru (4 katman) ve `/scan` endpoint'i
- Kabul kriteri: örnek dolandırıcı mesajlar "Tehlikeli/Şüpheli", resmî kurum mesajları "Bilinen tehdit yok" sonucu verir; testler geçer; mesajın hiçbir yere yazılmadığı testle doğrulanır.

**Faz 2: Web sitesi**
- Expo projesi, mesaj tarama ekranı, sonuç ekranı, gizlilik / KVKK sayfaları
- Production Docker Compose, Nginx, HTTPS, domain yayını
- Kabul kriteri: site kendi domainimizde HTTPS ile çalışır, mobil tarayıcıda düzgün görünür.

**Faz 3: Şüpheli numara sistemi**
- Bildirme, sorgulama, liste, itiraz, rate limit, Turnstile
- Kabul kriteri: aynı cihaz aynı numarayı iki kez bildiremez; eşik altı numaralar görünmez; farklı formatlardaki aynı numara tek kayıt olur.

**Faz 4: Android uygulaması**
- Android build (EAS Build), mağaza hazırlığı
- Android "Paylaş" menüsünden yalnızca metin paylaşımı (`text/plain`); mesaj uygulamada önizlenir, kullanıcı onaylayınca `/scan` ile taranır
- Paylaşılan metin URL'ye, dosyaya veya kalıcı depoya yazılmaz; link yönlendirmeleri yalnızca backend'in SSRF korumalı çözücüsünden geçer
- Expo SDK 57 `expo-sharing` gelen paylaşım API'si deneysel olarak işaretlidir; mağaza yayını öncesi gerçek Android cihazda doğrulanmalıdır

**İleri faz: Premium uzman incelemesi (planlama aşamasında)**
- Kullanıcı otomatik tarama sonrası isteğe bağlı insan incelemesi talep edebilir.
- İnceleme kuyruğu, gerçekçi yanıt süresi, ücretlendirme ve anonim talep takibi kararlaştırılmadan geliştirmeye başlanmaz.
- Açık onay, veri minimizasyonu, incelemeci erişim kontrolleri ve sınırlı saklama/silme süreci tasarlanır.
- Hizmet, otomatik taramanın kesinlik garantisi olarak değil, gerekçeli ikinci görüş olarak sunulur.

## Ekip çalışması kuralları

- **Tek dal: `main`** (karar: 2026-10-15). Feature dalı, `dev` dalı ve PR kullanılmaz; herkes doğrudan `main`'e commit ve push yapar.
- Push'tan önce `git pull --rebase` yapılır (iki kişi aynı dalda çalışıyor).
- Push etmeden önce testler yerelde çalıştırılır: backend için `docker compose exec api pytest`, mobil için `cd mobile && npm test`.
- **Commit formatı:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`). Her commit tek bir işe odaklanır.
- **Satır sonları:** `.gitattributes` ile `* text=auto eol=lf`. Windows'ta da LF kullanılır.
- **CI (GitHub Actions):** `main`'e her push'ta ruff, pytest, ESLint, TypeScript kontrolü, Jest ve altyapı kontrolleri çalışır. CI kırmızıysa ilk iş düzeltilir.
- **Deploy:** `main`'e yapılan her push, CI geçince `deploy.yml` ile otomatik olarak production'a çıkar (CI'ın test ettiği commit). Yani **`main`'e push = yayına almak**; yarım işler push edilmez. Deploy anahtarı sunucuda yalnızca `deploy <commit>` çalıştırabilir (`infra/scripts/ssh-deploy-entry.sh`). Kurulum: `infra/README.md`.
- Yeni bir bağımlılığın gerekçesi commit mesajına yazılır.

## Claude Code için çalışma kuralları

- Büyük bir göreve başlamadan önce plan çıkar ve onay bekle.
- Küçük, tek amaçlı değişiklikler yap. Bir commit'te birden fazla özelliği karıştırma.
- Doğrudan `main`'de çalış. Testler geçmeden push etme; push yayına almak demektir.
- Her değişiklikten sonra ilgili testleri yaz ve çalıştır (`docker compose exec api pytest`).
- Tarama kurallarını değiştirirken `backend/tests/fixtures/` altındaki örnek mesajlarla test et; yeni kural için yeni örnek ekle.
- Güvenlik ve KVKK kurallarına aykırı bir şey istenirse uygulamadan önce uyar.
- Bu dosyada olmayan bir mimari karar gerekiyorsa sor; karar verildikten sonra bu dosyayı güncelle.
- Yapay zekâ / ML kütüphanesi ekleme.
