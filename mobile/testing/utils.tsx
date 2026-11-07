import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react-native';
import { type ReactElement } from 'react';

import type { ScanResponse } from '@/lib/api';

export function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

export function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

export const DANGEROUS_RESULT: ScanResponse = {
  level: 'dangerous',
  label: 'Tehlikeli',
  message: 'Bu mesaj büyük olasılıkla dolandırıcılık amaçlı.',
  score: 90,
  reasons: [
    "Bu adres 'PTT' markasını taklit ediyor olabilir.",
    'Kargonun teslim edilemediği söyleniyor.',
  ],
  links: [{ domain: 'ptt-kargo-takip.xyz', score: 50, reasons: [] }],
  advice: ['Mesajdaki linke tıklamayın.', 'Kimseye para göndermeyin.'],
};

export const NO_THREAT_RESULT: ScanResponse = {
  level: 'no_known_threat',
  label: 'Bilinen tehdit yok',
  message: 'Bilinen bir tehdit bulunamadı, yine de dikkatli olun.',
  score: 0,
  reasons: [],
  links: [],
  advice: ['Beklemediğiniz mesajlardaki linklere karşı dikkatli olun.'],
};
