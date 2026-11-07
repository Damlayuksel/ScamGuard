/**
 * Backend API client. The message text is sent only in the request body, never in a URL.
 *
 * In production the site and API share an origin (Nginx serves /api), so the base URL is
 * empty. In development set EXPO_PUBLIC_API_URL (see mobile/.env.example).
 */

export type ScanLevel = 'dangerous' | 'suspicious' | 'no_known_threat';

export type ScannedLink = {
  domain: string;
  score: number;
  reasons: string[];
};

export type ScanResponse = {
  level: ScanLevel;
  label: string;
  message: string;
  score: number;
  reasons: string[];
  links: ScannedLink[];
  advice: string[];
};

export const MAX_MESSAGE_LENGTH = 5000;
const REQUEST_TIMEOUT_MS = 15_000;

export type ApiErrorKind = 'validation' | 'rate_limited' | 'server' | 'network';

const ERROR_MESSAGES: Record<ApiErrorKind, string> = {
  validation: `Mesaj boş olamaz ve en fazla ${MAX_MESSAGE_LENGTH} karakter olabilir.`,
  rate_limited: 'Çok fazla istek gönderdiniz. Lütfen biraz bekleyip tekrar deneyin.',
  server: 'Şu anda kontrol yapılamıyor. Lütfen biraz sonra tekrar deneyin.',
  network: 'Bağlantı kurulamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.',
};

export class ApiError extends Error {
  readonly kind: ApiErrorKind;

  constructor(kind: ApiErrorKind, message: string = ERROR_MESSAGES[kind]) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
  }
}

export function apiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/+$/, '');
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  if (response.status === 422) {
    return new ApiError('validation');
  }
  if (response.status === 429) {
    // The backend already answers in Turkish; fall back to our text if it does not.
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = typeof body?.detail === 'string' ? body.detail : undefined;
    return new ApiError('rate_limited', detail);
  }
  return new ApiError('server');
}

export async function scanMessage(text: string): Promise<ScanResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/api/v1/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ text }),
      signal: controller.signal,
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
    });
  } catch {
    throw new ApiError('network');
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as ScanResponse;
}
