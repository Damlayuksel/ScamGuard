import { Link } from 'expo-router';
import Head from 'expo-router/head';
import { StyleSheet, Text, View } from 'react-native';

import { BulletList } from '@/components/BulletList';
import { Screen } from '@/components/Screen';
import type { PageDocument } from '@/content/types';
import { APP_NAME } from '@/lib/brand';
import { isLegalDraft, LEGAL } from '@/lib/legal';
import { useTheme } from '@/lib/theme';

export const DRAFT_NOTICE =
  'Bu metin taslaktır: köşeli parantez içindeki bilgiler henüz doldurulmamış ve metin hukuki incelemeden geçmemiştir.';

type Props = {
  document: PageDocument;
};

/** Renders a static text page (Hakkında, Gizlilik, KVKK). */
export function DocumentPage({ document }: Props) {
  const theme = useTheme();
  const draft = document.legal && isLegalDraft();

  return (
    <Screen>
      <Head>
        <title>{`${document.title} · ${APP_NAME}`}</title>
        <meta name="description" content={document.description} />
      </Head>

      <Link href="/" style={[styles.back, { color: theme.link }]}>
        ← Mesaj kontrolüne dön
      </Link>

      <View style={styles.header}>
        <Text accessibilityRole="header" style={[styles.title, { color: theme.text }]}>
          {document.title}
        </Text>
        {document.legal && (
          <Text style={[styles.meta, { color: theme.textMuted }]}>
            {`Son güncelleme: ${LEGAL.lastUpdated}`}
          </Text>
        )}
        <Text style={[styles.paragraph, { color: theme.text }]}>{document.lead}</Text>
      </View>

      {draft && (
        <View
          testID="draft-notice"
          style={[
            styles.notice,
            { backgroundColor: theme.warningBackground, borderColor: theme.warningBorder },
          ]}
        >
          <Text style={[styles.paragraph, { color: theme.warningText }]}>{DRAFT_NOTICE}</Text>
        </View>
      )}

      {document.sections.map((section) => (
        <View key={section.title} style={styles.section}>
          <Text
            accessibilityRole="header"
            aria-level={2}
            style={[styles.sectionTitle, { color: theme.text }]}
          >
            {section.title}
          </Text>
          {section.paragraphs?.map((paragraph) => (
            <Text key={paragraph} style={[styles.paragraph, { color: theme.text }]}>
              {paragraph}
            </Text>
          ))}
          {section.bullets && <BulletList items={section.bullets} />}
        </View>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  back: {
    fontSize: 17,
    textDecorationLine: 'underline',
    alignSelf: 'flex-start',
    paddingVertical: 4,
  },
  header: {
    gap: 8,
  },
  title: {
    fontSize: 30,
    fontWeight: '800',
  },
  meta: {
    fontSize: 15,
  },
  section: {
    gap: 10,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: '700',
  },
  paragraph: {
    fontSize: 18,
    lineHeight: 27,
  },
  notice: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
  },
});
