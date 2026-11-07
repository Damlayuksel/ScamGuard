import { useRouter } from 'expo-router';
import * as Sharing from 'expo-sharing';
import { useCallback, useEffect, useState } from 'react';
import { AppState, Linking, Platform, StyleSheet, Text, TextInput, View } from 'react-native';

import { AdviceSection } from '@/components/AdviceSection';
import { Button } from '@/components/Button';
import { ReasonList } from '@/components/ReasonList';
import { ResultCard } from '@/components/ResultCard';
import { Screen } from '@/components/Screen';
import { MAX_MESSAGE_LENGTH, type ScanResponse } from '@/lib/api';
import { useTheme } from '@/lib/theme';
import { useScan } from '@/lib/useScan';

function isSharingUrl(url: string): boolean {
  try {
    return new URL(url).hostname === 'expo-sharing';
  } catch {
    return false;
  }
}

export default function SharedMessageScreen() {
  const theme = useTheme();
  const router = useRouter();
  const scan = useScan();
  const [sharedText, setSharedText] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const readSharedText = useCallback(() => {
    if (Platform.OS !== 'android') {
      return;
    }

    const payloads = Sharing.getSharedPayloads();
    if (payloads.length === 0) {
      return;
    }

    // Read only raw text. Resolving a shared URL can fetch it directly from the device,
    // bypassing the backend's SSRF protections.
    const text = payloads
      .filter((payload) => payload.mimeType === 'text/plain')
      .map((payload) => payload.value)
      .filter(Boolean)
      .join('\n');
    Sharing.clearSharedPayloads();

    setResult(null);
    setError(null);
    if (!text.trim()) {
      setSharedText(null);
      setError('Paylaşılan içerikte kontrol edilecek bir metin bulunamadı.');
      return;
    }
    if (text.length > MAX_MESSAGE_LENGTH) {
      setSharedText(null);
      setError(`Paylaşılan içerik ${MAX_MESSAGE_LENGTH} karakterden uzun.`);
      return;
    }
    setSharedText(text);
  }, []);

  useEffect(() => {
    // The first read runs right after mount instead of synchronously in the effect body
    // (react-hooks/set-state-in-effect). It cannot move to a useState initializer:
    // readSharedText also clears the native payload, and React may call initializers twice.
    let active = true;
    queueMicrotask(() => {
      if (active) {
        readSharedText();
      }
    });

    const urlSubscription = Linking.addEventListener('url', ({ url }) => {
      if (isSharingUrl(url)) {
        readSharedText();
      }
    });
    const appStateSubscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        readSharedText();
      }
    });

    return () => {
      active = false;
      urlSubscription.remove();
      appStateSubscription.remove();
    };
  }, [readSharedText]);

  const submit = async () => {
    if (!sharedText || isSubmitting) {
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const response = await scan.mutateAsync(sharedText);
      setResult(response);
      setSharedText(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Kontrol yapılamadı. Tekrar deneyin.');
    } finally {
      scan.reset();
      setIsSubmitting(false);
    }
  };

  const close = () => {
    Sharing.clearSharedPayloads();
    scan.reset();
    setSharedText(null);
    setResult(null);
    setError(null);
    router.replace('/');
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text accessibilityRole="header" style={[styles.title, { color: theme.text }]}>
          Mesaj kontrolü
        </Text>
        <Text style={[styles.description, { color: theme.textMuted }]}>
          Paylaştığınız içerik yalnızca kontrol için gönderilir ve kalıcı olarak saklanmaz.
        </Text>
      </View>

      {sharedText !== null && !result && (
        <View style={styles.content}>
          <Text style={[styles.label, { color: theme.text }]}>Paylaşılan mesaj</Text>
          <TextInput
            accessibilityLabel="Kontrol edilecek paylaşılan mesaj"
            value={sharedText}
            editable={false}
            multiline
            scrollEnabled
            style={[
              styles.preview,
              { color: theme.text, backgroundColor: theme.surface, borderColor: theme.border },
            ]}
          />
          <Button label="Mesajı kontrol et" onPress={submit} busy={isSubmitting} />
          <Button variant="secondary" label="Vazgeç" onPress={close} />
        </View>
      )}

      {!sharedText && !result && !error && (
        <Text style={[styles.description, { color: theme.textMuted }]}>
          Bir mesajda Paylaş → ScamShield seçtiğinizde burada kontrol edebilirsiniz.
        </Text>
      )}

      {isSubmitting && (
        <Text
          accessibilityLiveRegion="polite"
          style={[styles.description, { color: theme.textMuted }]}
        >
          Mesajınız kontrol ediliyor…
        </Text>
      )}

      {error && (
        <Text accessibilityRole="alert" style={[styles.error, { color: theme.dangerText }]}>
          {error}
        </Text>
      )}

      {result && (
        <View style={styles.content}>
          <ResultCard result={result} />
          <ReasonList result={result} />
          <AdviceSection result={result} />
          <Button variant="secondary" label="Kapat" onPress={close} />
        </View>
      )}

      {error && !sharedText && !result && (
        <Button variant="secondary" label="Kapat" onPress={close} />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    gap: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
  },
  description: {
    fontSize: 17,
    lineHeight: 24,
  },
  content: {
    gap: 16,
  },
  label: {
    fontSize: 18,
    fontWeight: '700',
  },
  preview: {
    minHeight: 140,
    maxHeight: 280,
    padding: 12,
    borderWidth: 1,
    borderRadius: 10,
    fontSize: 16,
    lineHeight: 23,
    textAlignVertical: 'top',
  },
  error: {
    fontSize: 17,
    lineHeight: 24,
  },
});
