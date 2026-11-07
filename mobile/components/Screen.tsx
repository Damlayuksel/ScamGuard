import { type ReactNode } from 'react';
import { Platform, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Footer } from '@/components/Footer';
import { useTheme } from '@/lib/theme';

type Props = {
  children: ReactNode;
};

/**
 * Page container with a centred, readable column and the site footer.
 *
 * On web the whole page scrolls (no inner scroll box), so mobile browsers keep their
 * native behaviour: collapsing address bar, momentum scrolling, find-in-page.
 * On native a ScrollView provides the scrolling.
 */
export function Screen({ children }: Props) {
  const theme = useTheme();
  const column = (
    <View style={styles.column}>
      <View role="main" style={styles.main}>
        {children}
      </View>
      <Footer />
    </View>
  );

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: theme.background }]}>
      {Platform.OS === 'web' ? (
        <View style={styles.page}>{column}</View>
      ) : (
        <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
          {column}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  page: {
    flexGrow: 1,
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 24,
  },
  column: {
    flexGrow: 1,
    width: '100%',
    maxWidth: 720,
    gap: 24,
  },
  main: {
    flexGrow: 1,
    gap: 24,
  },
});
