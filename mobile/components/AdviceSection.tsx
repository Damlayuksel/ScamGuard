import { Linking, StyleSheet, View } from 'react-native';

import { BulletList } from '@/components/BulletList';
import { Button } from '@/components/Button';
import { Section } from '@/components/Section';
import type { ScanResponse } from '@/lib/api';

type Props = {
  result: Pick<ScanResponse, 'level' | 'advice'>;
};

/** "Ne yapmalıyım?": advice comes from the backend; calling 155 is offered for risky results. */
export function AdviceSection({ result }: Props) {
  const risky = result.level !== 'no_known_threat';

  return (
    <Section title="Ne yapmalıyım?">
      <BulletList items={result.advice} testID="advice" />
      {risky && (
        <View style={styles.actions}>
          <Button
            variant="secondary"
            label="155 Polis İmdat'ı ara"
            accessibilityHint="Telefon uygulamanızda 155 numarasını açar"
            onPress={() => Linking.openURL('tel:155')}
          />
        </View>
      )}
    </Section>
  );
}

const styles = StyleSheet.create({
  actions: {
    alignItems: 'flex-start',
  },
});
