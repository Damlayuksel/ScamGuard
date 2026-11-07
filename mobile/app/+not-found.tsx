import { Link } from 'expo-router';
import Head from 'expo-router/head';
import { StyleSheet, Text, View } from 'react-native';

import { APP_NAME } from '@/lib/brand';
import { useTheme } from '@/lib/theme';

export default function NotFoundScreen() {
  const theme = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Head>
        <title>{`Sayfa bulunamadı · ${APP_NAME}`}</title>
      </Head>
      <Text accessibilityRole="header" style={[styles.title, { color: theme.text }]}>
        Sayfa bulunamadı
      </Text>
      <Link href="/" style={[styles.link, { color: theme.link }]}>
        Ana sayfaya dön
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
  },
  link: {
    fontSize: 18,
    textDecorationLine: 'underline',
  },
});
