import { APP_NAME } from '@/lib/brand';

import type { PageDocument } from './types';

export const ABOUT: PageDocument = {
  title: 'Hakkında',
  description: `${APP_NAME} nasıl çalışır, neyi yapabilir ve neyi yapamaz?`,
  lead: `${APP_NAME}, şüpheli SMS ve mesajlardaki linkleri ve metni kontrol ederek dolandırıcılık belirtilerini gösteren ücretsiz bir araçtır.`,
  sections: [
    {
      title: 'Nasıl çalışır?',
      paragraphs: [
        'Yapıştırdığınız mesajdaki linkler ve metin, belirli kurallara göre kontrol edilir. Yapay zekâ kullanılmaz; her sonucun gerekçesini açıkça gösteririz.',
      ],
      bullets: [
        'Linkler, zararlı bağlantı listeleriyle karşılaştırılır (USOM / T.C. Siber Güvenlik Başkanlığı ve URLhaus).',
        'Adresin bir bankayı, kargo firmasını veya devlet kurumunu taklit edip etmediğine bakılır.',
        'Kısaltılmış linklerin (ör. bit.ly) nereye gittiği güvenli biçimde kontrol edilir.',
        'Sitenin yeni açılıp açılmadığına bakılır.',
        'Mesaj metninde "son gün", "kazandınız", "IBAN", "doğrulama kodu" gibi dolandırıcılıkta sık geçen ifadeler aranır.',
        'Diğer kullanıcıların şüpheli olarak bildirdiği adresler dikkate alınır.',
      ],
    },
    {
      title: 'Sonuçlar ne anlama gelir?',
      bullets: [
        'Tehlikeli: Mesaj büyük olasılıkla dolandırıcılık amaçlı. Linke tıklamayın, bilgi paylaşmayın.',
        'Şüpheli: Mesajda dolandırıcılık belirtileri var. Kurumu resmî numarasından arayarak doğrulayın.',
        'Bilinen tehdit yok: Bilinen bir tehdit bulunamadı. Bu, mesajın kesinlikle güvenli olduğu anlamına gelmez; yine de dikkatli olun.',
      ],
    },
    {
      title: 'Neyi yapamaz?',
      paragraphs: [
        'Dolandırıcılar sürekli yeni adresler ve yöntemler kullanır. Henüz hiçbir listeye girmemiş yeni bir dolandırıcılık mesajı "Bilinen tehdit yok" sonucu verebilir. Bu yüzden hiçbir zaman "kesinlikle güvenli" demeyiz.',
        'Bankanız, kargo firması veya devlet kurumları sizden SMS ya da telefonla şifre, kart bilgisi veya doğrulama kodu istemez.',
      ],
    },
    {
      title: 'Dolandırıldığımı düşünüyorum, ne yapmalıyım?',
      bullets: [
        'Bankanızı hemen kartınızın arkasındaki resmî numaradan arayın ve kartınızı kapattırın.',
        "155 Polis İmdat'ı arayın veya en yakın karakola başvurun.",
        "Şüpheli linki USOM / T.C. Siber Güvenlik Başkanlığı'na bildirin.",
        'Şifrelerinizi değiştirin ve hesaplarınızdaki son işlemleri kontrol edin.',
      ],
    },
    {
      title: 'Gizlilik',
      paragraphs: [
        'Kontrol ettiğiniz mesaj kaydedilmez; yalnızca kontrol süresince kullanılır. Ayrıntılar için Gizlilik Politikası ve KVKK Aydınlatma Metni sayfalarına bakın.',
      ],
    },
  ],
};
