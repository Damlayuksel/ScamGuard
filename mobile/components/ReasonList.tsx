import { StyleSheet, Text, View } from 'react-native';

import { BulletList } from '@/components/BulletList';
import { Section } from '@/components/Section';
import type { ScanResponse } from '@/lib/api';
import { useTheme } from '@/lib/theme';

const NO_SIGNS_TEXT = 'Mesajda bilinen bir dolandırıcılık işareti bulunamadı.';

type Props = {
  result: Pick<ScanResponse, 'reasons' | 'links'>;
};

/**
 * "Neden bu sonuç?". Domains are shown as plain text on purpose: a scam link must never
 * become clickable in our own UI.
 */
export function ReasonList({ result }: Props) {
  const theme = useTheme();
  const domains = [...new Set(result.links.map((link) => link.domain))];

  return (
    <Section title="Neden bu sonuç?">
      {result.reasons.length > 0 ? (
        <BulletList items={result.reasons} testID="reasons" />
      ) : (
        <Text style={[styles.text, { color: theme.text }]}>{NO_SIGNS_TEXT}</Text>
      )}
      {domains.length > 0 && (
        <View style={styles.domains}>
          <Text style={[styles.subtitle, { color: theme.textMuted }]}>
            Mesajda bulunan adresler:
          </Text>
          {domains.map((domain) => (
            <Text
              key={domain}
              testID="scanned-domain"
              selectable={false}
              style={[styles.domain, { color: theme.text, borderColor: theme.border }]}
            >
              {domain}
            </Text>
          ))}
        </View>
      )}
    </Section>
  );
}

const styles = StyleSheet.create({
  text: {
    fontSize: 18,
    lineHeight: 26,
  },
  domains: {
    gap: 8,
  },
  subtitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  domain: {
    alignSelf: 'flex-start',
    fontSize: 18,
    fontFamily: 'monospace',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderWidth: 1,
    borderRadius: 6,
  },
});
