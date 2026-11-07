/**
 * Facts the legal texts depend on. Values in [KÖŞELİ PARANTEZ] are placeholders that must be
 * filled in (and the texts reviewed by a lawyer) before going live; while any remain, the
 * pages show a visible "taslak" notice.
 */
export const LEGAL = {
  controllerName: '[VERİ SORUMLUSU ADI / UNVANI]',
  controllerAddress: '[VERİ SORUMLUSU ADRESİ]',
  contactEmail: '[İLETİŞİM E-POSTASI]',
  hostingProvider: '[SUNUCU SAĞLAYICISI]',
  hostingCountry: '[SUNUCUNUN BULUNDUĞU ÜLKE]',
  scanStatsRetention: '[İSTATİSTİK SAKLAMA SÜRESİ]',
  domainReportRetention: '[BİLDİRİM SAKLAMA SÜRESİ]',
  lastUpdated: '14 Ekim 2026',
} as const;

const PLACEHOLDER = /\[[^\]]+\]/;

export function unfilledLegalFields(): string[] {
  return Object.entries(LEGAL)
    .filter(([, value]) => PLACEHOLDER.test(value))
    .map(([key]) => key);
}

export function isLegalDraft(): boolean {
  return unfilledLegalFields().length > 0;
}
