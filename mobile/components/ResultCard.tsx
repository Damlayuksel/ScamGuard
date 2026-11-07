import { type Ref } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Icon, type IconName } from '@/components/Icon';
import type { ScanLevel, ScanResponse } from '@/lib/api';
import { type ColorToken, useTheme } from '@/lib/theme';

type LevelStyle = {
  icon: IconName;
  background: ColorToken;
  border: ColorToken;
  text: ColorToken;
};

// Colour is never the only signal: each level has its own icon and the text label.
export const LEVEL_STYLES: Record<ScanLevel, LevelStyle> = {
  dangerous: {
    icon: 'alert-octagon',
    background: 'dangerBackground',
    border: 'dangerBorder',
    text: 'dangerText',
  },
  suspicious: {
    icon: 'alert',
    background: 'warningBackground',
    border: 'warningBorder',
    text: 'warningText',
  },
  no_known_threat: {
    icon: 'check-circle-outline',
    background: 'safeBackground',
    border: 'safeBorder',
    text: 'safeText',
  },
};

type Props = {
  result: Pick<ScanResponse, 'level' | 'label' | 'message'>;
  ref?: Ref<View>;
};

export function ResultCard({ result, ref }: Props) {
  const theme = useTheme();
  const level = LEVEL_STYLES[result.level];

  return (
    <View
      ref={ref}
      testID="result-card"
      focusable
      accessible
      accessibilityLabel={`Sonuç: ${result.label}. ${result.message}`}
      aria-live="polite"
      style={[
        styles.card,
        { backgroundColor: theme[level.background], borderColor: theme[level.border] },
      ]}
    >
      <Icon
        testID={`result-icon-${result.level}`}
        name={level.icon}
        size={44}
        color={theme[level.border]}
      />
      <View style={styles.texts}>
        <Text accessibilityRole="header" style={[styles.label, { color: theme[level.text] }]}>
          {result.label}
        </Text>
        <Text style={[styles.message, { color: theme[level.text] }]}>{result.message}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    padding: 20,
    borderRadius: 14,
    borderWidth: 3,
  },
  texts: {
    flex: 1,
    gap: 4,
  },
  label: {
    fontSize: 28,
    fontWeight: '800',
  },
  message: {
    fontSize: 18,
    lineHeight: 26,
  },
});
