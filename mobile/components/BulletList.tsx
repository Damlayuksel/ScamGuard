import { StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/lib/theme';

type Props = {
  items: string[];
  testID?: string;
};

export function BulletList({ items, testID }: Props) {
  const theme = useTheme();

  return (
    <View role="list" testID={testID} style={styles.list}>
      {items.map((item) => (
        <View key={item} role="listitem" style={styles.row}>
          <Text style={[styles.bullet, { color: theme.textMuted }]} aria-hidden>
            •
          </Text>
          <Text style={[styles.text, { color: theme.text }]}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: {
    gap: 10,
  },
  row: {
    flexDirection: 'row',
    gap: 10,
  },
  bullet: {
    fontSize: 18,
    lineHeight: 26,
  },
  text: {
    flex: 1,
    fontSize: 18,
    lineHeight: 26,
  },
});
