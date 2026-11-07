import { APP_NAME } from '@/lib/brand';
import { LEGAL } from '@/lib/legal';

import type { PageDocument } from './types';

// Structure follows KVKK (6698 sayılı Kanun) m.10 (aydınlatma yükümlülüğü) and m.11 (haklar).
// Legal bases are a draft and must be confirmed by a lawyer before going live.
export const KVKK: PageDocument = {
  title: 'KVKK Aydınlatma Metni',
  description: `${APP_NAME} kişisel verilerin korunması kanunu kapsamında aydınlatma metni.`,
  lead: `6698 sayılı Kişisel Verilerin Korunması Kanunu ("KVKK") uyarınca, ${APP_NAME} hizmeti kapsamında işlenen kişisel veriler hakkında sizi bilgilendirmek isteriz.`,
  legal: true,
  sections: [
    {
      title: '1. Veri sorumlusu',
      paragraphs: [
        `Veri sorumlusu: ${LEGAL.controllerName}, ${LEGAL.controllerAddress}. İletişim: ${LEGAL.contactEmail}.`,
      ],
    },
    {
      title: '2. İşlenen kişisel veriler',
      bullets: [
        'Kontrol için gönderdiğiniz mesaj metni: Mesaj; sizin veya başkalarının adı, telefon numarası gibi kişisel veriler içerebilir. Yalnızca kontrol süresince bellekte işlenir, hiçbir şekilde saklanmaz.',
        'IP adresi: Yalnızca geri çevrilemeyen özeti (HMAC-SHA256), kötüye kullanımı önleyen kısa süreli sayaçta tutulur (tarama için 1 dakika, bildirimler için 1 saat).',
        'Cihaz kimliği: Şüpheli adres bildiriminde, cihazınızda rastgele oluşturulan kimliğin yalnızca geri çevrilemeyen özeti, bildirilen alan adıyla birlikte saklanır.',
        'Tarama istatistikleri (alan adı, sonuç seviyesi, tarih): kişisel veri içermez ve sizinle ilişkilendirilmez.',
      ],
    },
    {
      title: '3. İşleme amaçları',
      bullets: [
        'Talep ettiğiniz mesaj kontrolünü yapmak ve sonucu size göstermek,',
        'Hizmetin kötüye kullanılmasını ve aşırı yüklenmesini önlemek,',
        'Aynı cihazın aynı adresi tekrar tekrar bildirmesini önlemek,',
        'Hizmetin güvenliğini sağlamak.',
      ],
    },
    {
      title: '4. Toplama yöntemi ve hukuki sebep',
      paragraphs: [
        "Veriler, web sitesi ve mobil uygulama üzerinden, sizin mesajı kontrol ettirmeniz veya bir adresi bildirmeniz sırasında elektronik ortamda otomatik olarak toplanır. Hukuki sebep, KVKK m.5/2-f uyarınca temel hak ve özgürlüklerinize zarar vermemek kaydıyla veri sorumlusunun meşru menfaati (hizmetin sunulması ve güvenliği) ve ilgili durumlarda m.5/2-c'dir.",
      ],
    },
    {
      title: '5. Aktarım',
      bullets: [
        `Sunucularımız ${LEGAL.hostingProvider} tarafından ${LEGAL.hostingCountry} konumunda barındırılmaktadır. Sunucunun yurt dışında bulunması hâlinde bu durum KVKK m.9 kapsamında yurt dışına aktarım niteliği taşır.`,
        'Sitenin açılış tarihini öğrenmek için alan adının kayıt kuruluşuna (RDAP sunucusu) yalnızca alan adı gönderilir; bu kuruluşlar yurt dışında olabilir. Alan adı tek başına sizi tanımlamaz.',
        'Kısaltılmış linkler kontrol edilirken ilgili siteye sunucumuz üzerinden istek gönderilir; sizin IP adresiniz veya mesajınız iletilmez.',
        'Kişisel verileriniz bunların dışında üçüncü kişilere aktarılmaz, satılmaz ve reklam amacıyla kullanılmaz. Kanunen yetkili kurumların talepleri saklıdır.',
      ],
    },
    {
      title: '6. Saklama süreleri',
      bullets: [
        'Mesaj metni: saklanmaz.',
        'IP adresi özeti: tarama için 1 dakika, bildirimler için 1 saat.',
        `Bildirimlerdeki cihaz kimliği özeti: ${LEGAL.domainReportRetention}.`,
        `Tarama istatistikleri (kişiyle ilişkilendirilmeyen): ${LEGAL.scanStatsRetention}.`,
      ],
    },
    {
      title: '7. KVKK m.11 kapsamındaki haklarınız',
      bullets: [
        'Kişisel verilerinizin işlenip işlenmediğini öğrenme,',
        'İşlenmişse buna ilişkin bilgi talep etme,',
        'İşlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme,',
        'Yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme,',
        'Eksik veya yanlış işlenmişse düzeltilmesini isteme,',
        'KVKK m.7 çerçevesinde silinmesini veya yok edilmesini isteme,',
        'Düzeltme ve silme işlemlerinin aktarılan üçüncü kişilere bildirilmesini isteme,',
        'Münhasıran otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonuç çıkmasına itiraz etme,',
        'Kanuna aykırı işleme nedeniyle zarara uğramanız hâlinde zararın giderilmesini talep etme.',
      ],
    },
    {
      title: '8. Başvuru',
      paragraphs: [
        `Haklarınızla ilgili taleplerinizi ${LEGAL.contactEmail} adresine veya ${LEGAL.controllerAddress} adresine yazılı olarak iletebilirsiniz. Başvurular, Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ'e uygun olarak en geç 30 gün içinde ücretsiz yanıtlanır.`,
        'Hizmet hesapsız ve anonim çalıştığı için, sakladığımız özet bilgileri (hash) çoğu durumda belirli bir kişiyle eşleştiremeyiz; başvurunuzda talebinizi mümkün olduğunca açık belirtmeniz önemlidir.',
      ],
    },
  ],
};
