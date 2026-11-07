import { type ColorToken, palettes, themeCss } from '@/lib/theme';

// WCAG 2.x relative luminance / contrast ratio.
function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const TEXT_PAIRS: [ColorToken, ColorToken][] = [
  ['text', 'background'],
  ['text', 'surface'],
  ['textMuted', 'background'],
  ['textMuted', 'surface'],
  ['link', 'background'],
  ['onPrimary', 'primary'],
  ['dangerText', 'dangerBackground'],
  ['warningText', 'warningBackground'],
  ['safeText', 'safeBackground'],
];

// Borders, icons and focus rings only need 3:1 (WCAG non-text contrast).
const NON_TEXT_PAIRS: [ColorToken, ColorToken][] = [
  ['border', 'background'],
  ['focus', 'background'],
  ['dangerBorder', 'dangerBackground'],
  ['warningBorder', 'warningBackground'],
  ['safeBorder', 'safeBackground'],
];

describe.each(Object.entries(palettes))('%s theme', (_name, palette) => {
  it.each(TEXT_PAIRS)('%s on %s meets 4.5:1', (fg, bg) => {
    expect(contrast(palette[fg], palette[bg])).toBeGreaterThanOrEqual(4.5);
  });

  it.each(NON_TEXT_PAIRS)('%s on %s meets 3:1', (fg, bg) => {
    expect(contrast(palette[fg], palette[bg])).toBeGreaterThanOrEqual(3);
  });
});

describe('theme', () => {
  it('defines every colour token for both themes', () => {
    expect(Object.keys(palettes.dark).sort()).toEqual(Object.keys(palettes.light).sort());
  });

  it('emits CSS variables for light and dark (web hydrates without style mismatches)', () => {
    expect(themeCss).toContain(`--color-text: ${palettes.light.text};`);
    expect(themeCss).toContain('@media (prefers-color-scheme: dark)');
    expect(themeCss).toContain(`--color-danger-background: ${palettes.dark.dangerBackground};`);
  });
});
