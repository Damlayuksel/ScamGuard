import { Platform, useColorScheme } from 'react-native';

// Colour tokens for light and dark themes. Result levels (danger = Tehlikeli,
// warning = Şüpheli, safe = Bilinen tehdit yok) are never shown by colour alone: every
// result also has an icon and a text label. Contrast is checked in __tests__/theme.test.ts.
export const palettes = {
  light: {
    background: '#ffffff',
    surface: '#f4f6f8',
    text: '#111418',
    textMuted: '#4a5360',
    border: '#8a94a3',
    link: '#0b57d0',
    primary: '#0b57d0',
    onPrimary: '#ffffff',
    focus: '#0b57d0',
    dangerBackground: '#fdecea',
    dangerBorder: '#c62828',
    dangerText: '#8e1414',
    warningBackground: '#fff4d6',
    warningBorder: '#9a5b00',
    warningText: '#5c3600',
    safeBackground: '#e8f5e9',
    safeBorder: '#2e7d32',
    safeText: '#1b5e20',
  },
  dark: {
    background: '#111418',
    surface: '#1c2128',
    text: '#f2f4f7',
    textMuted: '#b4bcc8',
    border: '#6b7480',
    link: '#8ab4f8',
    primary: '#8ab4f8',
    onPrimary: '#0b1d3a',
    focus: '#8ab4f8',
    dangerBackground: '#3a1414',
    dangerBorder: '#ef5350',
    dangerText: '#ffb4ab',
    warningBackground: '#3a2a00',
    warningBorder: '#ffb300',
    warningText: '#ffe08a',
    safeBackground: '#10301a',
    safeBorder: '#66bb6a',
    safeText: '#b9f6ca',
  },
} as const;

export type ColorToken = keyof (typeof palettes)['light'];
export type Palette = Record<ColorToken, string>;

const tokens = Object.keys(palettes.light) as ColorToken[];

function cssVarName(token: ColorToken): string {
  return `--color-${token.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;
}

/**
 * Web pages are rendered at build time, before the visitor's theme is known, and React
 * does not patch mismatched styles while hydrating. On web every colour is therefore a
 * CSS variable whose value is chosen by `prefers-color-scheme` (see `themeCss`).
 */
const webPalette = Object.fromEntries(
  tokens.map((token) => [token, `var(${cssVarName(token)})`]),
) as Palette;

function declarations(palette: Palette): string {
  return tokens.map((token) => `${cssVarName(token)}: ${palette[token]};`).join(' ');
}

/** CSS custom properties for both themes; injected once in app/+html.tsx. */
export const themeCss = `
:root { ${declarations(palettes.light)} }
@media (prefers-color-scheme: dark) { :root { ${declarations(palettes.dark)} } }
`;

export function useTheme(): Palette {
  const scheme = useColorScheme();
  if (Platform.OS === 'web') {
    return webPalette;
  }
  return scheme === 'dark' ? palettes.dark : palettes.light;
}
