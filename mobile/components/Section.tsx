import { type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/lib/theme';

type Props = {
  title: string;
  children: ReactNode;
};

export function Section({ title, children }: Props) {
  const theme = useTheme();

  return (
    <View style={[styles.section, { backgroundColor: theme.surface, borderColor: theme.border }]}>
      <Text accessibilityRole="header" aria-level={2} style={[styles.title, { color: theme.text }]}>
        {title}
      </Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 12,
    padding: 20,
    borderRadius: 14,
    borderWidth: 1,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
  },
});
