import { render, screen } from '@testing-library/react-native';

import { LEVEL_STYLES, ResultCard } from '@/components/ResultCard';
import type { ScanLevel } from '@/lib/api';

const CASES: [ScanLevel, string][] = [
  ['dangerous', 'Tehlikeli'],
  ['suspicious', 'Şüpheli'],
  ['no_known_threat', 'Bilinen tehdit yok'],
];

describe('ResultCard', () => {
  it.each(CASES)('%s shows an icon and a text label, not only a colour', async (level, label) => {
    await render(<ResultCard result={{ level, label, message: 'Açıklama' }} />);

    expect(screen.getByRole('header', { name: label })).toBeOnTheScreen();
    expect(
      screen.getByTestId(`result-icon-${level}`, { includeHiddenElements: true }),
    ).toBeOnTheScreen();
    expect(screen.getByTestId('result-card').props.accessibilityLabel).toBe(
      `Sonuç: ${label}. Açıklama`,
    );
  });

  it('uses a different icon for every level', () => {
    const icons = Object.values(LEVEL_STYLES).map((style) => style.icon);

    expect(new Set(icons).size).toBe(icons.length);
  });
});
