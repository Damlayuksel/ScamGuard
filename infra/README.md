# Production sunucu kurulumu

Hedef: Ubuntu 24.04, 4 GB RAM, 80/443 portları boş. Bütün servisler Docker Compose ile çalışır:

| Servis | Görev |
|---|---|
| `web` | Nginx: statik site (Expo web build), `/api` proxy, HTTPS |
| `api` | FastAPI (2 worker) |
| `worker` | USOM/URLhaus güncelleme görevleri |
| `db` | PostgreSQL 16 |
| `redis` | Redis 7 (yalnızca önbellek) |
| `certbot` | Let's Encrypt sertifika yenileme |

Komutlar sunucuda, **repo kök klasöründe** çalıştırılır. Betikler `infra/scripts/` altındadır.

## 1. Sunucuyu hazırlama (bir kez)

Güncellemeler ve otomatik güvenlik yamaları:

```bash
sudo apt update && sudo apt upgrade -y && sudo apt install -y unattended-upgrades git
```

Güvenlik duvarı: yalnızca SSH, HTTP ve HTTPS açık.

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
```

SSH'ta şifreyle girişi kapatın (`/etc/ssh/sshd_config` içinde `PasswordAuthentication no`). Bu adımdan önce anahtarla girebildiğinizden emin olun.

Docker: https://docs.docker.com/engine/install/ubuntu/ adresindeki resmî kurulum adımlarını izleyin.

Deploy için ayrı bir kullanıcı (sudo yetkisi yok, docker grubunda):

```bash
sudo adduser --disabled-password --gecos "" deploy && sudo usermod -aG docker deploy
```

## 2. Kodu çekme

Repo özel olduğu için GitHub'da **salt okunur bir deploy key** ekleyin: Repo → Settings → Deploy keys → Add deploy key (yazma izni kapalı). Anahtarı `deploy` kullanıcısıyla sunucuda üretin:

```bash
sudo -iu deploy ssh-keygen -t ed25519 -N "" -f /home/deploy/.ssh/github_deploy
```

`/home/deploy/.ssh/github_deploy.pub` içeriğini GitHub'a ekleyin, sonra repo'yu klonlayın:

```bash
sudo -iu deploy sh -c 'GIT_SSH_COMMAND="ssh -i ~/.ssh/github_deploy" git clone git@github.com:Damlayuksel/ScamShield.git ~/scamshield'
```

```bash
sudo -iu deploy git -C ~/scamshield config core.sshCommand "ssh -i ~/.ssh/github_deploy"
```

## 3. Ayarlar

```bash
cp infra/.env.prod.example infra/.env.prod && chmod 600 infra/.env.prod
```

`infra/.env.prod` içinde `DOMAIN`, `LETSENCRYPT_EMAIL`, `SECRET_KEY` ve `POSTGRES_PASSWORD` doldurulur. Rastgele değer üretmek için:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 4. DNS

Domain sağlayıcınızın panelinde `DOMAIN` ve `www.DOMAIN` için A kaydını (sunucuda IPv6 varsa AAAA kaydını da) sunucunun IP adresine yönlendirin. **Dikkat:** kayıt değiştiği anda o adresteki mevcut site yayından kalkar. Kaydın yayıldığını kontrol edin:

```bash
dig +short lovelockapp.com
```

## 5. İlk kurulum

Stack'i başlatır ve veritabanı migration'larını uygular. İlk açılışta Nginx geçici, kendinden imzalı bir sertifikayla çalışır.

```bash
sh infra/scripts/deploy.sh
```

Gerçek sertifikayı alır. Önce `STAGING=1` ile deneyip, sonra normal çalıştırmanız önerilir (Let's Encrypt deneme sınırları):

```bash
STAGING=1 sh infra/scripts/init-letsencrypt.sh
```

```bash
sh infra/scripts/init-letsencrypt.sh
```

Sertifikalar `certbot` servisi tarafından 12 saatte bir kontrol edilip yenilenir. Nginx 6 saatte bir kendini yeniden yükler.

## 6. Kontrol

```bash
curl -sI https://lovelockapp.com | head -20
```

```bash
curl -s https://lovelockapp.com/api/v1/health
```

Beklenen sonuçlar:
- `http://` adresi 301 ile `https://` adresine yönlenir.
- `/docs` adresi 404 döner.
- Yanıtta `Strict-Transport-Security` ve `Content-Security-Policy` başlıkları bulunur.

Dış testler: https://www.ssllabs.com/ssltest/ (A veya üstü) ve https://securityheaders.com/.

Loglarda mesaj metni, tam URL veya IP olmadığını kontrol edin:

```bash
docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod logs --tail 50 api web
```

HTTPS bir hafta sorunsuz çalıştıktan sonra `infra/.env.prod` içinde `HSTS_MAX_AGE=31536000` yapıp yeniden deploy edin.

## 7. Yedekleme

Her gece `pg_dump` alınır ve **yalnızca bu sunucuda**, `/var/backups/scamshield` altında 7 gün saklanır. Veritabanında mesaj metni yoktur. Klasörü bir kez oluşturun:

```bash
sudo install -d -o deploy -g deploy -m 700 /var/backups/scamshield
```

`deploy` kullanıcısının crontab'ına ekleyin (`sudo -iu deploy crontab -e`):

```
30 3 * * * sh /home/deploy/scamshield/infra/scripts/backup-db.sh >/dev/null 2>&1
```

Geri yükleme (mevcut verinin üzerine yazar):

```bash
gunzip -c /var/backups/scamshield/<dosya>.sql.gz | docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.prod exec -T db psql -U scamshield -d scamshield
```

## 8. Uptime izleme

UptimeRobot'ta (ücretsiz plan) bir HTTP(s) monitörü oluşturun:
- adres: `https://lovelockapp.com/api/v1/health`
- aralık: 5 dakika

Bu servis yalnızca sağlık kontrolü adresini çağırır, kullanıcı verisi görmez.

## 9. Otomatik deploy (GitHub Actions)

`main` dalına yapılan her push CI'dan geçince `.github/workflows/deploy.yml` çalışır:
- Sunucuya SSH ile bağlanır ve **CI'ın test ettiği commit'i** deploy eder.
- Ardından `https://DOMAIN/api/v1/health` adresinin 200 döndüğünü kontrol eder.

Kırmızı CI ile deploy olmaz. Aynı anda tek deploy çalışır. Actions sekmesinden "Run workflow" ile elle de çalıştırılabilir (yalnızca `main`).

### Sunucu: kısıtlı deploy anahtarı

GitHub'a verilecek anahtar, sunucuda yalnızca `deploy <commit>` komutunu çalıştırabilir. Kabuk açamaz, port yönlendiremez. `deploy.sh` de yalnızca `origin/main` üzerindeki commit'leri kabul eder. Anahtar sızsa bile en fazla `main`'deki bir sürüm yeniden deploy edilebilir.

`deploy` kullanıcısıyla anahtar çifti üretin:

```bash
sudo -iu deploy ssh-keygen -t ed25519 -N "" -C github-actions -f /home/deploy/.ssh/github_actions
```

Açık anahtarı **zorunlu komutla** yetkilendirin:

```bash
sudo -iu deploy sh -c 'printf "restrict,command=\"/home/deploy/scamshield/infra/scripts/ssh-deploy-entry.sh\" %s\n" "$(cat ~/.ssh/github_actions.pub)" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

Gizli anahtarı (`/home/deploy/.ssh/github_actions`) bir sonraki adımda GitHub'a ekleyin, sonra sunucudan silin:

```bash
sudo -iu deploy rm /home/deploy/.ssh/github_actions
```

### GitHub: secret'lar ve variable

Ayarlar repo düzeyinde girilir: Repo → Settings → **Secrets and variables** → **Actions**. (GitHub "Environments" özelliği ücretsiz planda özel repolarda yok.)

**Secrets** sekmesinde **New repository secret** ile ekleyin:

| Secret | Değer |
|---|---|
| `DEPLOY_HOST` | Sunucunun IP adresi (`104.233.4.115`) |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_PORT` | SSH portu (`25416`) |
| `DEPLOY_SSH_KEY` | Gizli anahtarın tek satırlık hâli: sunucuda `base64 -w0 /home/deploy/.ssh/github_actions; echo` çıktısı. Dosyanın kendisi de olur ama kopyala-yapıştırda bozulabilir. |
| `DEPLOY_KNOWN_HOSTS` | Sunucunun kimlik satırı (aşağıdaki komutun çıktısı) |

`DEPLOY_KNOWN_HOSTS` satırını sunucunun kendi anahtar dosyasından üretin. Ağdan alınmadığı için araya girme riski yoktur:

```bash
echo "[104.233.4.115]:25416 $(cut -d' ' -f1,2 /etc/ssh/ssh_host_ed25519_key.pub)"
```

**Variables** sekmesinde **New repository variable** ile ekleyin:

| Variable | Değer |
|---|---|
| `DEPLOY_URL` | `https://lovelockapp.com` |

**Not:** Secret'lar eklenene kadar her push'ta Deploy iş akışı "Missing production settings" hatasıyla kırmızı görünür; bu beklenen bir durumdur ve siteyi etkilemez.

### Elle deploy

```bash
sh infra/scripts/deploy.sh
```

Belirli bir commit'e dönmek için (commit `origin/main` üzerinde olmalı):

```bash
sh infra/scripts/deploy.sh <commit-sha>
```
