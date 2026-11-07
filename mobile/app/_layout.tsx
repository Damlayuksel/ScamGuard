import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Slot, Stack, usePathname } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { useTheme } from '@/lib/theme';

/**
 * On web the page itself scrolls, so a stack navigator would keep earlier pages hidden in
 * the DOM and new pages would open at the old scroll position. Web renders one page at a
 * time and starts each page at the top; native keeps the stack (back gesture).
 */
function WebNavigation() {
  const pathname = usePathname();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return <Slot />;
}

export default function RootLayout() {
  const theme = useTheme();
  // In memory only; no cache persister is configured (message text must not be stored).
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider style={{ backgroundColor: theme.background }}>
        <StatusBar style="auto" />
        {Platform.OS === 'web' ? (
          <WebNavigation />
        ) : (
          <Stack
            screenOptions={{
              headerShown: false,
              contentStyle: { backgroundColor: theme.background },
            }}
          />
        )}
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
