# Faz 2 — Web sitesi: ayrıntılı plan

> Durum: **onaylandı (2026-10-14).** 2026-10-15 itibarıyla proje tek dal (`main`) ile çalışıyor; aşağıdaki PR numaraları yalnızca işlerin sırasını gösterir, hepsi `main`'e alındı.

## Amaç ve kabul kriteri

Teknik bilgisi olmayan kullanıcılar şüpheli bir mesajı web sitesine yapıştırıp sade, renk + ikon + metinle anlatılan bir sonuç alır. Sitede gizlilik politikası ve KVKK aydınlatma metni yayınlanır.

**Kabul (CLAUDE.md):**
- Site kendi domainimizde HTTPS ile çalışır.
- Mobil tarayıcıda düzgün görünür.

Bunlara ek olarak şunları da kontrol edeceğiz:
- 360 / 375 / 414 px genişliklerde yatay kaydırma yok.
- Açık ve koyu tema çalışıyor.
- Lighthouse erişilebilirlik puanı ≥ 90.

## Alınan kararlar

| Konu | Karar |
|---|---|
| Node | **24 LTS** (CLAUDE.md'deki "22 LTS" PR-10'da güncellenir; iki geliştirici de 24 kullanır) |
| Expo | **SDK 57** (bugünkü `latest`), TypeScript, Expo Router |
| Web çıktısı | Expo Router `web.output: "static"`: her sayfa için HTML üretilir. Gizlilik/KVKK sayfaları JavaScript olmadan da okunur, arama motorları için de iyidir |
| API adresi | Prod'da aynı origin (`/api/v1`, Nginx proxy), bu sayede CORS gerekmez. Geliştirmede `EXPO_PUBLIC_API_URL=http://localhost:8000` |
| Domain | **Geçici olarak `lovelockapp.com` ana domaini.** `www.lovelockapp.com` 301 ile ana domaine yönlenir; sertifika ikisini de kapsar. Ayarlar `${DOMAIN}` değişkeniyle yazılır, kalıcı domaine geçişte yalnızca `.env.prod` ve DNS değişir. **Dikkat:** DNS bu sunucuya yönlendirildiği anda o adresteki mevcut site yayından kalkar |
| Site adı | Şimdilik "ScamShield". Görünen ad tek bir sabitte (`lib/brand.ts`) tutulur, kolayca değiştirilir |
| Sunucu | Deneme sunucusu, Ubuntu 24.04, 4 GB RAM, boş (80/443 serbest). Kurulumu ve ilk deploy'u **siz** çalıştırırsınız; bana SSH anahtarı ya da şifre vermeniz gerekmez |
| Let's Encrypt e-postası | `applovelock@gmail.com`. Bu adres repo'ya değil, sunucudaki `.env.prod`'a yazılır |
| Yedekleme | Yalnızca sunucuda: her gece `pg_dump`, 7 gün saklama |
| Deploy | GitHub Actions: `main`'e her push'ta CI geçerse SSH ile otomatik deploy (PR-14) |
| Domain bildirme düğmesi | **Faz 3'e kalır.** Gerekçe: Faz 3'teki bildirim formlarıyla birlikte Turnstile (bot koruması) gelecek. Korumasız bir bildirim düğmesi, cihaz kimliği kolayca yenilenebildiği için topluluk kara listesini kötüye kullanıma açar |
| Loglarda IP | **Hiçbir erişim logunda IP yok** (Uvicorn'daki gibi Nginx'te de). Kötüye kullanım hash'lenmiş IP ile rate limit üzerinden engellenir. Nginx `error_log` seviyesi `crit`, çünkü `error` seviyesindeki satırlar istemci IP'si içerir. CLAUDE.md'ye kural olarak eklenir |
| Web Risk | **Eklenmiyor.** PR-9 iptal; CLAUDE.md'deki opsiyonel Web Risk satırı ve kullanılmayan `WEB_RISK_*` ayarları PR-13'te kaldırılır |
| Uptime izleme | UptimeRobot (ücretsiz plan): 5 dakikada bir `https://lovelockapp.com/api/v1/health`. Hesabı siz açarsınız; kurulum adımları `infra/README.md`'ye yazılır |
| Veri sorumlusu | Belli değil. KVKK/gizlilik metinleri `[VERİ SORUMLUSU]` gibi yer tutucularla yazılır, yayından önce doldurulur ve avukata onaylatılır |

## Gizlilik açısından ön tasarım kuralları (Faz 2'ye özel)

1. **Mesaj metni asla URL'ye girmez.** Sonuç ayrı bir sayfada `?text=` ile gösterilmez. Tarama ve sonuç aynı ekranda, yalnızca bileşen state'inde tutulur. Aksi hâlde metin tarayıcı geçmişine, Nginx loglarına ve Referer başlığına düşerdi.
2. Mesaj `localStorage`, `sessionStorage`, IndexedDB veya TanStack Query'nin kalıcı önbelleğine yazılmaz. "Temizle" düğmesi state'i siler. Mutation sonucu kalıcı hâle getirilmez.
3. Üçüncü taraf istek yok:
   - Google Fonts, analitik, CDN ve reklam kullanılmaz.
   - Fontlar sistem fontu, ikonlar paketle birlikte gelir.
   - Bu sayede **çerez kullanılmaz**, çerez bandına gerek kalmaz.
4. Nginx loglarında request body yok, IP yok, `/numbers/...` maskeli.
5. CSP: `default-src 'self'`, `connect-src 'self'`, `frame-ancestors 'none'`. react-native-web satır içi stil ürettiği için `style-src 'self' 'unsafe-inline'` gerekir. Script için `unsafe-inline` yok.

## PR'lar

Her madde ayrı dal ve ayrı PR; hedef `dev`. Faz 3 PR numaraları buna göre kayar.

### PR-10 `feature/expo-init`: Expo iskeleti, lint, test, CI

- `npx create-expo-app@latest mobile --template` (TypeScript + Expo Router), SDK 57
- `app.json`:
  - `name`, `slug`
  - `web.output: "static"`, `web.bundler: "metro"`
  - `userInterfaceStyle: "automatic"` (koyu tema)
- `app/+html.tsx`:
  - `<html lang="tr">`, viewport, `theme-color` (açık/koyu)
  - açıklama meta etiketi, `noindex` yok
- **Bağımlılıklar** (gerekçeleri PR açıklamasına yazılır):
  - Expo şablonunun getirdikleri: expo, expo-router, react-native-web, react-dom, expo-status-bar, @expo/vector-icons.
  - @tanstack/react-query: CLAUDE.md'de seçili.
  - Geliştirme: jest-expo, @testing-library/react-native, eslint-config-expo, prettier, eslint-config-prettier.
- `package.json` script'leri: `lint`, `format:check`, `typecheck` (`tsc --noEmit`), `test`, `build:web` (`expo export -p web`)
- `.github/workflows/ci.yml`'ye `mobile` job'u eklenir: Node 24, `npm ci`, lint, format kontrolü, typecheck, jest
- CLAUDE.md: Node 24 LTS; Expo SDK 57; "mesaj URL'ye/tarayıcı deposuna girmez" kuralı
- README: `cd mobile && npm install && npx expo start --web`

### PR-11 `feature/scan-screen`: tarama ve sonuç ekranı

**Dosyalar:**
- `lib/api.ts`:
  - `scanMessage(text)`: `POST /api/v1/scan`; yanıt tipleri backend şemasıyla birebir.
  - Hata eşlemesi:
    - 422 → "Mesaj boş ya da çok uzun",
    - 429 → backend'in Türkçe mesajı,
    - ağ hatası → "Bağlantı kurulamadı, internetinizi kontrol edin".
- `lib/theme.ts`: açık/koyu renk token'ları (PR-10'da temeli kuruldu). **Webde renkler CSS değişkenidir** (`var(--color-…)`, değerleri `prefers-color-scheme` seçer). Statik HTML derleme anında üretildiği ve React hydration sırasında farklı stilleri düzeltmediği için bu gerekli; yeni renkler de aynı yolla eklenir. Kırmızı, sarı ve yeşil seviye renkleri iki temada da WCAG AA kontrastını sağlar. Büyük yazı ölçeği: gövde ≥ 18 px, başlık 28–32 px.
- `app/_layout.tsx`: QueryClientProvider, tema sağlayıcı, sade üst menü (Mesaj Tara · Hakkında · Gizlilik)
- `app/index.tsx`:
  - büyük çok satırlı metin alanı
  - "Mesajı buraya yapıştırın" yönergesi
  - 5000 karakter sayacı
  - **Tara** ve **Temizle** düğmeleri (en az 48 px dokunma alanı)
  - "Mesajınız kaydedilmez" notu
- `components/ResultCard.tsx`:
  - seviye rengi + ikon (⚠ / ❗ / ✔ benzeri vektör ikon) + metin etiketi: "Tehlikeli" / "Şüpheli" / "Bilinen tehdit yok"
  - backend'in `message` alanı
  - renk tek başına anlam taşımaz
- `components/ReasonList.tsx`: "Neden?" listesi; link başına domain ve gerekçeler
- `components/AdviceSection.tsx`: "Ne yapmalıyım?" maddeleri; 155'e ve USOM'a dokunarak aranabilir/açılabilir bağlantılar
- Erişilebilirlik:
  - `accessibilityRole` / `accessibilityLabel` tanımlı
  - sonuç gelince odak sonuç başlığına taşınır
  - `aria-live="polite"` ile sonuç duyurulur
- Yükleniyor durumu: "Mesajınız kontrol ediliyor…". Düğme devre dışı kalır, çift gönderim olmaz.

**Testler (Jest + RNTL):**
- Her seviye için doğru etiket, ikon ve metin çıkıyor; renk tek başına kullanılmıyor (etiket her zaman var)
- Tara → mock API → sonuç gösteriliyor; 429/ağ hatası mesajları
- Mesaj metni `localStorage`'a ve URL'ye yazılmıyor: `window.location` ve `localStorage` spy'ları
- Temizle düğmesi state'i siliyor

### PR-12 `feature/legal-pages`: Hakkında, Gizlilik, KVKK

- `app/hakkinda.tsx`:
  - sistem nasıl çalışır (yapay zekâ yok, kara listeler + kurallar)
  - sınırlar ("hiçbir zaman kesinlikle güvenli demeyiz")
  - USOM ve 155 bilgisi
- `app/gizlilik.tsx` (Gizlilik politikası) ve `app/kvkk.tsx` (Aydınlatma metni) taslakları. Yer tutucular: `[VERİ SORUMLUSU]`, `[ADRES]`, `[İLETİŞİM E-POSTASI]`, `[SUNUCU KONUMU]`.
  - **İşlenen veriler:**
    - mesaj metni yalnızca istek süresince bellekte tutulur, hiçbir yere kaydedilmez
    - taramalarda yalnızca alan adı + sonuç seviyesi istatistiği tutulur
    - IP adresi yalnızca HMAC özeti olarak, kısa süreli hız sınırı için Redis'te tutulur (1 dk – 1 saat)
    - domain bildirimlerinde cihaz kimliğinin HMAC özeti tutulur
  - **Amaç ve hukuki sebep:** kötüye kullanımı önleme, hizmet güvenliği; KVKK m.5/2-f meşru menfaat. Avukat teyidi gerekir.
  - **Aktarım:**
    - Kısa linkleri çözmek için yalnızca ilgili sitelere istek atılır.
    - Domain yaşı için RDAP sunucularına yalnızca alan adı gönderilir.
    - Sunucu yurt dışındaysa yurt dışı aktarım bilgisi eklenir (sunucunun ülkesi yayından önce öğrenilmeli).
  - **İlgili kişi hakları:** KVKK m.11; başvuru yolu.
  - Çerez kullanılmadığı beyanı.
  - Not: Faz 3'te numara bildirimleri eklenince metin güncellenecek (telefon numarası, 30 gün IP özeti, itiraz süreci).
- Altbilgi (footer): her sayfada Gizlilik · KVKK · Hakkında bağlantıları
- Testler: sayfalar render oluyor; bağlantılar doğru rotaya gidiyor

### PR-13 `feature/prod-infra`: production Docker Compose, Nginx, HTTPS

**`infra/docker-compose.prod.yml`:**
- `api`:
  - `INSTALL_DEV=false` imajı, `ENV=prod`
  - `uvicorn --workers 2 --proxy-headers --no-server-header`
  - `FORWARDED_ALLOW_IPS` = Nginx container'ının sabit IP'si (özel Docker ağı, ör. `172.28.0.10`)
  - kaynak volume'u yok
- `worker`: aynı imaj
- `db`:
  - postgres:16, isimli volume
  - **host'a port açılmaz**
- `redis`:
  - redis:7, host'a port açılmaz
  - `maxmemory 256mb` (USOM hash'i yaklaşık 60–80 MB)
- `web` (Nginx):
  - çok aşamalı `infra/nginx/Dockerfile`: `node:24` ile `mobile` web build alınır, çıktı `nginx:stable-alpine` imajına kopyalanır
  - 80/443 portları açık
  - sertifika volume'u bağlanır
- `certbot`:
  - webroot yöntemi
  - 12 saatte bir `certbot renew`
  - Nginx yenilemeden sonra `nginx -s reload` ile tazelenir
- Docker log rotasyonu: `json-file`, `max-size: 10m`, `max-file: 3`

**`infra/nginx/templates/site.conf.template`** (`envsubst` ile `${DOMAIN}` doldurulur):
- **80. port:**
  - `/.well-known/acme-challenge/` webroot'a gider
  - diğer her şey 301 ile `https://`'e yönlenir
- **`www.${DOMAIN}`:** 443'te 301 ile `https://${DOMAIN}`'e yönlenir (tek sertifika iki adı kapsar)
- **443. port:**
  - TLS 1.2/1.3, HTTP/2, OCSP stapling
  - HSTS (ilk hafta kısa `max-age`, sonra 1 yıl)
  - güvenlik başlıkları: CSP (yukarıda), `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `Permissions-Policy`
- **`/api/`:**
  - `proxy_pass http://api:8000`
  - `proxy_set_header X-Forwarded-For $remote_addr` (zinciri **ekleme**, istemcinin gönderdiğini ezer)
  - `client_max_body_size 32k`
  - `/docs` ve `/openapi.json` dışarıya 404 döner
- **Statik dosyalar:**
  - `try_files $uri $uri.html $uri/index.html =404`
  - `error_page 404 /+not-found.html` (Türkçe 404 sayfası; PR-10'da `expo serve` ile görüldü)
  - Expo Router'ın ürettiği `/_sitemap` sayfası dışarıya 404 döner
  - `/_expo/static/` 1 yıl `immutable`, HTML `no-cache`
  - gzip açık
- **Loglar:**
  - `map $request_uri $log_uri` ile `/numbers/...` maskelenir
  - `log_format` IP içermez; `error_log ... crit`
  - request body loglanmaz (Nginx varsayılanı)
- Ek koruma katmanı olarak `limit_req`: IP başına saniyede 5 istek (API'deki Redis limitine ek)

**Uygulamada eklenenler (PR-13):**
- CSP'de `script-src` için `unsafe-inline` yok. Expo Router'ın tek satır içi scripti hash ile izinli. `infra/nginx/check-csp.mjs`, yeni bir satır içi script çıkarsa web imajının build'ini durdurur.
- `api` adı Docker DNS'i ile en fazla 10 saniyede bir yeniden çözülür. Deploy'da yeniden oluşturulan container yeni IP alsa da Nginx 502'de takılı kalmaz.
- Nginx'in kendi ürettiği hatalar (413, 429, 502/503/504) `/api` altında Türkçe JSON döner.
- Let's Encrypt OCSP desteğini 2025'te kaldırdığı için OCSP stapling kullanılmıyor.

**İlk sertifika ve kurulum:**
- `infra/scripts/init-letsencrypt.sh`: geçici kendinden imzalı sertifika → Nginx başlar → certbot gerçek sertifikayı alır → reload. Script sunucuda (Linux) çalışır; geliştiricilerin Windows/macOS ortamını etkilemez.

**`infra/README.md` (sunucu kurulumu):**
- `ufw` ile yalnızca 22/80/443 açık
- SSH yalnızca anahtarla, `unattended-upgrades`
- Docker kurulumu
- `.env.prod` oluşturma: `SECRET_KEY` üretimi, `DOMAIN`, `CORS_ORIGINS=https://${DOMAIN}`, `LETSENCRYPT_EMAIL`
- DNS A/AAAA kaydı
- İlk deploy
- Migration: `docker compose -f infra/docker-compose.prod.yml run --rm api alembic upgrade head`

**Deploy betiği:** `infra/scripts/deploy.sh`. Hem ilk kurulumda elle hem PR-14'teki GitHub Actions tarafından kullanılır. Çalıştırdığı komutlar:

```
git fetch origin main && git checkout main && git pull --ff-only
docker compose -f infra/docker-compose.prod.yml up -d --build
docker compose -f infra/docker-compose.prod.yml run --rm api alembic upgrade head
docker image prune -f
```

**4 GB RAM notu:** Expo web build'i (Node) sunucuda yaklaşık 1–1,5 GB bellek kullanır; Postgres, Redis ve USOM hash'iyle birlikte sığar. Sorun olursa web build'i GitHub Actions'ta alıp yalnızca `dist` klasörünü sunucuya göndermeye geçeriz.

**Yedekleme:** `infra/scripts/backup-db.sh` + host cron. Her gece `pg_dump`, `/var/backups/scamshield` altında **yalnızca sunucuda**, 7 gün saklama. Veritabanında mesaj metni yok; yalnızca domain istatistikleri, kara liste ve hash'ler var.

**Temizlik:** Kullanılmayan `WEB_RISK_*` ayarları `config.py`'den ve `.env.example`'dan, Web Risk satırı da CLAUDE.md'den kaldırılır.

**Testler:**
- CI'da `docker compose -f infra/docker-compose.prod.yml config` (sözdizimi kontrolü)
- `nginx -t` (template doldurulmuş hâlde)
- Yerelde `DOMAIN=localhost` ile HTTP smoke testi

### PR-14 `feature/deploy-workflow`: GitHub Actions ile otomatik deploy

- `.github/workflows/deploy.yml`:
  - Tetikleyici: `main`'deki CI iş akışı başarıyla bitince (`workflow_run`). Kırmızı CI ile deploy olmaz.
  - `concurrency: deploy-production`: aynı anda iki deploy çalışmaz.
  - GitHub `production` ortamı; isterseniz deploy öncesi elle onay da açılabilir.
  - Adım: SSH ile sunucuya bağlanıp `infra/scripts/deploy.sh` çalıştırılır. Ardından `https://${DOMAIN}/api/v1/health` 200 dönene kadar en fazla 2 dakika beklenir; dönmezse iş başarısız sayılır.
- **Sizin GitHub'a ekleyeceğiniz secret'lar** (değerleri ben görmem):
  - `DEPLOY_HOST`
  - `DEPLOY_USER`
  - `DEPLOY_SSH_KEY`: yalnızca bu iş için üretilmiş anahtar
  - `DEPLOY_KNOWN_HOSTS`: sunucunun host anahtarı; ortadaki adam saldırısına karşı sabitlenir
- **Uygulamada eklenenler (PR-14):**
  - Deploy edilen commit, CI'ın test ettiği commit'tir (`workflow_run.head_sha`). Arada `main`'e yeni bir commit gelse bile test edilmemiş kod yayına çıkmaz.
  - Deploy anahtarı `authorized_keys`'te `restrict,command=` ile kısıtlıdır. Yalnızca `deploy <40 karakterlik sha>` çalıştırabilir; `deploy.sh` de yalnızca `origin/main` üzerindeki commit'leri kabul eder.
- **Sunucu tarafı:**
  - Ayrı bir `deploy` kullanıcısı (docker grubunda, sudo yetkisiz).
  - Repo'yu çekmek için GitHub'da salt okunur bir **deploy key**.
  - Kurulum adımları `infra/README.md`'ye yazılır.

### Yayın kontrol listesi

1. `lovelockapp.com` ve `www.lovelockapp.com` için A (varsa AAAA) kayıtları sunucuya yönlendirilir, `init-letsencrypt.sh` çalıştırılır.
2. `https://${DOMAIN}` açılır. `http://` adresinin 301 ile yönlendiğini, sertifikanın geçerli olduğunu, `/docs`'un 404 döndüğünü kontrol edin.
3. SSL Labs testi (A veya üstü), securityheaders.com testi.
4. Gerçek telefonda (Android Chrome + iOS Safari) tarama yapılır; açık ve koyu tema denenir.
5. Lighthouse (mobil): Erişilebilirlik ≥ 90, Performans ≥ 80.
6. Sunucuda `docker compose logs api web` çıktısında mesaj metni ve tam URL olmadığı elle doğrulanır.
7. KVKK/gizlilik metinlerindeki yer tutucular doldurulmuş ve avukat onayı alınmış olmalı.
8. UptimeRobot izleyicisi kurulur, uyarı e-postası alındığı test edilir.

## Yayından önce kalan bilgiler (kodlamayı engellemez)

- **Sunucunun ülkesi ve sağlayıcısı:** KVKK metnindeki yurt dışı aktarım bölümü buna bağlı.
- **Veri sorumlusu bilgileri:** ad/unvan, adres, iletişim.
- **Saklama süreleri:** `scan_stats` (tarama istatistikleri) ve `domain_reports` (bildirimlerdeki cihaz özeti) için CLAUDE.md'de süre tanımlı değil. Karar verilince `mobile/lib/legal.ts`'e yazılır ve worker'a temizlik görevi eklenir.
- Bu bilgilerin hepsi `mobile/lib/legal.ts`'te tutuluyor. Biri bile eksikse Gizlilik ve KVKK sayfaları "taslak" uyarısı gösterir.
- **Kalıcı site adı ve domain:** şimdilik "ScamShield" ve `lovelockapp.com`.
