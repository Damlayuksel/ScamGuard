import { fireEvent, screen } from '@testing-library/react-native';
import { readFileSync } from 'fs';
import { join } from 'path';
import { Linking } from 'react-native';

import ScanScreen from '@/app/index';
import { FOOTER_LINKS } from '@/components/Footer';
import { MAX_MESSAGE_LENGTH } from '@/lib/api';

import {
  DANGEROUS_RESULT,
  jsonResponse,
  NO_THREAT_RESULT,
  renderWithClient,
} from '@/testing/utils';

const fetchMock = jest.fn();
const MESSAGE = 'PTT: Kargonuz teslim edilemedi https://ptt-kargo-takip.xyz/tr';

beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
});

async function typeAndScan(text = MESSAGE) {
  await fireEvent.changeText(screen.getByTestId('message-input'), text);
  await fireEvent.press(screen.getByRole('button', { name: 'Kontrol et' }));
}

describe('ScanScreen', () => {
  it('does not send an empty or whitespace-only message', async () => {
    await renderWithClient(<ScanScreen />);

    await fireEvent.press(screen.getByRole('button', { name: 'Kontrol et' }));
    await fireEvent.changeText(screen.getByTestId('message-input'), '   ');
    await fireEvent.press(screen.getByRole('button', { name: 'Kontrol et' }));

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('counts characters and limits the input length', async () => {
    await renderWithClient(<ScanScreen />);

    await fireEvent.changeText(screen.getByTestId('message-input'), 'merhaba');

    expect(screen.getByTestId('char-counter')).toHaveTextContent(`7 / ${MAX_MESSAGE_LENGTH}`);
    expect(screen.getByTestId('message-input').props.maxLength).toBe(MAX_MESSAGE_LENGTH);
  });

  it('shows a dangerous result with reasons, domains and advice', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, DANGEROUS_RESULT));
    await renderWithClient(<ScanScreen />);

    await typeAndScan();

    expect(await screen.findByRole('header', { name: 'Tehlikeli' })).toBeOnTheScreen();
    expect(
      screen.getByTestId('result-icon-dangerous', { includeHiddenElements: true }),
    ).toBeOnTheScreen();
    expect(screen.getByText(DANGEROUS_RESULT.message)).toBeOnTheScreen();
    for (const reason of DANGEROUS_RESULT.reasons) {
      expect(screen.getByText(reason)).toBeOnTheScreen();
    }
    for (const advice of DANGEROUS_RESULT.advice) {
      expect(screen.getByText(advice)).toBeOnTheScreen();
    }
    expect(screen.getByRole('header', { name: 'Ne yapmalıyım?' })).toBeOnTheScreen();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ text: MESSAGE });
  });

  it('shows scanned domains as plain text, never as links', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, DANGEROUS_RESULT));
    await renderWithClient(<ScanScreen />);

    await typeAndScan();

    const domain = await screen.findByTestId('scanned-domain');
    expect(domain).toHaveTextContent('ptt-kargo-takip.xyz');
    expect(domain.props.onPress).toBeUndefined();
    expect(domain.props.href).toBeUndefined();
    // The only links on the page are the site's own footer links.
    const linkTexts = screen.getAllByRole('link').map((link) => link.props.children);
    expect(linkTexts).toEqual(FOOTER_LINKS.map((link) => link.label));
    expect(linkTexts.join(' ')).not.toContain('ptt-kargo');
  });

  it('offers calling 155 for risky results', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, DANGEROUS_RESULT));
    const openURL = jest.spyOn(Linking, 'openURL').mockResolvedValue(true);
    await renderWithClient(<ScanScreen />);

    await typeAndScan();
    await fireEvent.press(await screen.findByRole('button', { name: "155 Polis İmdat'ı ara" }));

    expect(openURL).toHaveBeenCalledWith('tel:155');
  });

  it('never says "safe" and explains when nothing was found', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, NO_THREAT_RESULT));
    await renderWithClient(<ScanScreen />);

    await typeAndScan('Akşam yemeğe gelir misin?');

    expect(await screen.findByRole('header', { name: 'Bilinen tehdit yok' })).toBeOnTheScreen();
    expect(screen.getByText('Mesajda bilinen bir dolandırıcılık işareti bulunamadı.')).toBeTruthy();
    expect(screen.queryByText(/kesinlikle güvenli/i)).toBeNull();
    expect(screen.queryByRole('button', { name: "155 Polis İmdat'ı ara" })).toBeNull();
  });

  it('shows the Turkish error message from the API', async () => {
    fetchMock.mockResolvedValue(jsonResponse(429, { detail: 'Çok fazla istek gönderdiniz.' }));
    await renderWithClient(<ScanScreen />);

    await typeAndScan();

    expect(await screen.findByTestId('scan-error')).toHaveTextContent(
      'Çok fazla istek gönderdiniz.',
    );
  });

  it('clears the message and the result', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, DANGEROUS_RESULT));
    await renderWithClient(<ScanScreen />);
    await typeAndScan();
    await screen.findByTestId('result-card');

    await fireEvent.press(screen.getByRole('button', { name: 'Temizle' }));

    expect(screen.getByTestId('message-input').props.value).toBe('');
    expect(screen.queryByTestId('result-card')).toBeNull();
  });
});

describe('privacy guard', () => {
  // CLAUDE.md rule 15: the message must not reach the URL or browser storage.
  const FORBIDDEN = [
    'localStorage',
    'sessionStorage',
    'indexedDB',
    'AsyncStorage',
    'setParams',
    'router.push',
    'router.replace',
    'useLocalSearchParams',
    'persistQueryClient',
  ];

  it.each([
    'app/index.tsx',
    'lib/api.ts',
    'lib/useScan.ts',
    'app/_layout.tsx',
    'components/Screen.tsx',
  ])('%s does not use URL params or browser storage', (file) => {
    const source = readFileSync(join(__dirname, '..', file), 'utf8');
    for (const word of FORBIDDEN) {
      expect(source).not.toContain(word);
    }
  });
});
