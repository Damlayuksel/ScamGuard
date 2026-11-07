import { Link, type Href } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { APP_NAME } from '@/lib/brand';
import { useTheme } from '@/lib/theme';

export const FOOTER_LINKS: { href: Href; label: string }[] = [
  { href: '/', label: 'Mesaj kontrolü' },
  { href: '/hakkinda', label: 'Hakkında' },
  { href: '/gizlilik', label: 'Gizlilik Politikası' },
  { href: '/kvkk', label: 'KVKK Aydınlatma Metni' },
];

export function Footer() {
  const theme = useTheme();

  return (
    <View
      role="navigation"
      aria-label="Site bağlantıları"
      style={[styles.footer, { borderTopColor: theme.border }]}
    >
      <View style={styles.links}>
        {FOOTER_LINKS.map((link) => (
          <Link key={link.label} href={link.href} style={[styles.link, { color: theme.link }]}>
            {link.label}
          </Link>
        ))}
      </View>
      <Text style={[styles.note, { color: theme.textMuted }]}>
        {`${APP_NAME} yapay zekâ kullanmaz ve mesajınızı kaydetmez.`}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    marginTop: 16,
    paddingTop: 20,
    borderTopWidth: 1,
    gap: 12,
  },
  links: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    columnGap: 20,
    rowGap: 12,
  },
  link: {
    fontSize: 17,
    textDecorationLine: 'underline',
    paddingVertical: 4,
  },
  note: {
    fontSize: 15,
  },
});
