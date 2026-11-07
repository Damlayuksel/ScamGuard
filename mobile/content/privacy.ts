import { APP_NAME } from '@/lib/brand';
import { LEGAL } from '@/lib/legal';

import type { PageDocument } from './types';

// Every statement here must match what the backend actually does (see CLAUDE.md,
// "Güvenlik ve KVKK kuralları"). Update this text whenever data handling changes.
export const PRIVACY: PageDocument = {
  title: 'Gizlilik Politikası',
  description: `${APP_NAME} hangi bilgileri işler, ne kadar saklar ve kimseyle paylaşır mı?`,
  lead: `${APP_NAME} kullanıcı hesabı olmadan, anonim olarak çalışır. Kontrol ettiğiniz mesajı kaydetmeyiz. Bu sayfa, hizmeti sunarken hangi bilgileri ve nasıl işlediğimizi sade bir dille anlatır.`,
  legal: true,
  sections: [
    {
      title: 'Kontrol ettiğiniz mesaj',
      bullets: [
        'Mesaj yalnızca kontrol süresince sunucumuzun belleğinde tutulur ve kontrol biter bitmez silinir.',
        'Mesaj veritabanına, dosyaya, kayıtlara (loglara) veya önbelleğe yazılmaz.',
        'Mesaj, tarayıcınızın adres çubuğuna veya tarayıcı deposuna (çerez, yerel depolama) da yazılmaz.',
        'Mesajın tamamı ve linklerin tam adresi hiçbir dış hizmete gönderilmez.',
      ],
    },
    {
      title: 'Sakladığımız istatistikler',
      paragraphs: [
        `Hizmeti geliştirmek için her kontrolde yalnızca mesajdaki sitelerin alan adı (ör. "ornek-site.com"; linkin tamamı değil), sonuç seviyesi (Tehlikeli, Şüpheli, Bilinen tehdit yok) ve tarih saklanır. Bu kayıtlar sizinle ilişkilendirilmez. Saklama süresi: ${LEGAL.scanStatsRetention}.`,
      ],
    },
    {
      title: 'IP adresiniz',
      paragraphs: [
        'Hizmetin kötüye kullanılmasını (ör. dakikada çok sayıda istek gönderilmesini) önlemek için IP adresiniz kullanılır. IP adresiniz hiçbir zaman açık olarak saklanmaz; yalnızca geri çevrilemeyen bir özeti (HMAC-SHA256) kısa süreli bir sayaçta tutulur ve kendiliğinden silinir: tarama için 1 dakika, bildirimler için 1 saat.',
        'Sunucu erişim kayıtlarında IP adresiniz ve mesaj içeriği bulunmaz.',
      ],
    },
    {
      title: 'Şüpheli adres bildirimleri',
      paragraphs: [
        `Bir siteyi şüpheli olarak bildirdiğinizde, cihazınızda rastgele oluşturulan bir kimliğin yalnızca geri çevrilemeyen özeti, bildirilen alan adı ve tarih saklanır. Bu, aynı cihazın aynı adresi birden çok kez bildirmesini önlemek içindir. 5 farklı cihazdan bildirilen adresler, diğer kullanıcıları korumak için şüpheli adresler listesine eklenir. Saklama süresi: ${LEGAL.domainReportRetention}.`,
      ],
    },
    {
      title: 'Linkleri nasıl kontrol ediyoruz?',
      bullets: [
        'Zararlı bağlantı listeleri (USOM / T.C. Siber Güvenlik Başkanlığı, URLhaus) sunucumuza indirilir ve kontrol sunucumuzda yapılır; bu kurumlara sizinle ilgili bilgi gönderilmez.',
        'Sitenin ne zaman açıldığını öğrenmek için alan adının kayıt bilgisini tutan kuruluşa (RDAP sunucusu) yalnızca alan adı gönderilir. Sonuç 24 saat önbellekte tutulur.',
        'Kısaltılmış linklerin (ör. bit.ly) nereye gittiğini öğrenmek için sunucumuz o adrese kısa bir istek gönderir. Bu sırada karşı taraf sizin değil, sunucumuzun adresini görür. Sayfa açılmaz, içindeki kodlar çalıştırılmaz.',
      ],
    },
    {
      title: 'Çerezler ve üçüncü taraflar',
      bullets: [
        'Web sitemiz çerez kullanmaz.',
        'Reklam, analiz veya takip aracı kullanmayız; sayfalarımız başka sitelerden yazı tipi, görsel veya kod yüklemez.',
        `Sunucumuz ${LEGAL.hostingProvider} tarafından ${LEGAL.hostingCountry} konumunda barındırılmaktadır.`,
        'Sitenin çalışıp çalışmadığını izleyen bir hizmet, yalnızca sağlık kontrolü adresimizi çağırır; sizinle ilgili bir bilgiye erişmez.',
      ],
    },
    {
      title: 'Güvenlik',
      bullets: [
        'Sitemiz yalnızca şifreli bağlantı (HTTPS) ile çalışır.',
        'Kısaltılmış linkler kontrol edilirken sunucumuzun iç ağına erişim engellenir.',
      ],
    },
    {
      title: 'İletişim ve haklarınız',
      paragraphs: [
        `Kişisel verilerinizle ilgili haklarınız ve başvuru yolları KVKK Aydınlatma Metni'nde yer alır. Sorularınız için: ${LEGAL.contactEmail}.`,
      ],
    },
  ],
};
