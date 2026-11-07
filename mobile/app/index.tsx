import Head from 'expo-router/head';
import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { AdviceSection } from '@/components/AdviceSection';
import { Button } from '@/components/Button';
import { Icon } from '@/components/Icon';
import { ReasonList } from '@/components/ReasonList';
import { ResultCard } from '@/components/ResultCard';
import { Screen } from '@/components/Screen';
import { MAX_MESSAGE_LENGTH } from '@/lib/api';
import { APP_DESCRIPTION, APP_NAME } from '@/lib/brand';
import { useTheme } from '@/lib/theme';
import { useScan } from '@/lib/useScan';

/**
 * Scan screen. The message lives only in this component's state: it is never put in the
 * URL (no route params) or in browser storage, and the result is shown on the same screen.
 */
export default function ScanScreen() {
  const theme = useTheme();
  const [text, setText] = useState('');
  const scan = useScan();
  const resultRef = useRef<View>(null);

  const trimmed = text.trim();
  const result = scan.data;

  useEffect(() => {
    const node = resultRef.current;
    if (!result || !node) {
      return;
    }
    // Move focus to the result so screen readers and keyboard users land on it.
    if (Platform.OS === 'web') {
      const element = node as unknown as HTMLElement;
      element.focus?.({ preventScroll: true });
      element.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    } else {
      AccessibilityInfo.sendAccessibilityEvent(node, 'focus');
    }
  }, [result]);

  const submit = () => {
    if (trimmed && !scan.isPending) {
      scan.mutate(trimmed);
    }
  };

  const clear = () => {
    setText('');
    scan.reset();
  };

  return (
    <Screen>
      <Head>
        <title>{`${APP_NAME} · Şüpheli mesaj kontrolü`}</title>
        <meta name="description" content={APP_DESCRIPTION} />
      </Head>

      <View style={styles.header}>
        <Text accessibilityRole="header" style={[styles.title, { color: theme.text }]}>
          {APP_NAME}
        </Text>
        <Text style={[styles.lead, { color: theme.textMuted }]}>{APP_DESCRIPTION}</Text>
      </View>

      <View style={styles.form}>
        <Text nativeID="message-label" style={[styles.inputLabel, { color: theme.text }]}>
          Şüpheli mesajı buraya yapıştırın
        </Text>
        <TextInput
          testID="message-input"
          accessibilityLabel="Kontrol edilecek mesaj"
          aria-labelledby="message-label"
          value={text}
          onChangeText={setText}
          multiline
          numberOfLines={8}
          maxLength={MAX_MESSAGE_LENGTH}
          placeholder="Örnek: Kargonuz teslim edilemedi, adres bilgilerinizi güncelleyin…"
          placeholderTextColor={theme.textMuted}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="off"
          spellCheck={false}
          textAlignVertical="top"
          style={[
            styles.input,
            { color: theme.text, backgroundColor: theme.surface, borderColor: theme.border },
          ]}
        />
        <View style={styles.inputMeta}>
          <View style={styles.privacyNote}>
            <Icon name="lock-outline" size={18} color={theme.textMuted} />
            <Text style={[styles.meta, { color: theme.textMuted }]}>Mesajınız kaydedilmez.</Text>
          </View>
          <Text testID="char-counter" style={[styles.meta, { color: theme.textMuted }]}>
            {`${text.length} / ${MAX_MESSAGE_LENGTH}`}
          </Text>
        </View>
        <View style={styles.buttons}>
          <Button label="Kontrol et" onPress={submit} disabled={!trimmed} busy={scan.isPending} />
          <Button
            variant="secondary"
            label="Temizle"
            onPress={clear}
            disabled={!text && !result && !scan.error}
          />
        </View>
      </View>

      {scan.isPending && (
        <View style={styles.status} accessibilityLiveRegion="polite" aria-live="polite">
          <ActivityIndicator color={theme.primary} />
          <Text style={[styles.statusText, { color: theme.text }]}>
            Mesajınız kontrol ediliyor…
          </Text>
        </View>
      )}

      {scan.error && (
        <View
          testID="scan-error"
          accessibilityRole="alert"
          style={[
            styles.error,
            { backgroundColor: theme.dangerBackground, borderColor: theme.dangerBorder },
          ]}
        >
          <Text style={[styles.statusText, { color: theme.dangerText }]}>{scan.error.message}</Text>
        </View>
      )}

      {result && (
        <View style={styles.result}>
          <ResultCard ref={resultRef} result={result} />
          <ReasonList result={result} />
          <AdviceSection result={result} />
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    gap: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: '800',
  },
  lead: {
    fontSize: 18,
    lineHeight: 26,
  },
  form: {
    gap: 10,
  },
  inputLabel: {
    fontSize: 20,
    fontWeight: '700',
  },
  input: {
    minHeight: 180,
    fontSize: 18,
    lineHeight: 26,
    padding: 14,
    borderWidth: 2,
    borderRadius: 12,
  },
  inputMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
  },
  privacyNote: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  meta: {
    fontSize: 16,
  },
  buttons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 4,
  },
  status: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  statusText: {
    fontSize: 18,
    lineHeight: 26,
  },
  error: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
  },
  result: {
    gap: 16,
  },
});
