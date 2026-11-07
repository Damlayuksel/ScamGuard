import { render, screen } from '@testing-library/react-native';

import AboutPage from '@/app/hakkinda';
import PrivacyPage from '@/app/gizlilik';
import KvkkPage from '@/app/kvkk';
import { DRAFT_NOTICE } from '@/components/DocumentPage';
import { FOOTER_LINKS } from '@/components/Footer';
import { ABOUT } from '@/content/about';
import { KVKK } from '@/content/kvkk';
import { PRIVACY } from '@/content/privacy';
import type { PageDocument } from '@/content/types';
import { isLegalDraft, LEGAL, unfilledLegalFields } from '@/lib/legal';

const PAGES: [string, () => React.JSX.Element, PageDocument][] = [
  ['Hakkında', AboutPage, ABOUT],
  ['Gizlilik', PrivacyPage, PRIVACY],
  ['KVKK', KvkkPage, KVKK],
];

describe.each(PAGES)('%s page', (_name, Page, document) => {
  it('renders the title, every section heading and the footer', async () => {
    await render(<Page />);

    expect(screen.getByRole('header', { name: document.title })).toBeOnTheScreen();
    for (const section of document.sections) {
      expect(screen.getByRole('header', { name: section.title })).toBeOnTheScreen();
    }
    for (const link of FOOTER_LINKS) {
      expect(screen.getByRole('link', { name: link.label })).toBeOnTheScreen();
    }
  });

  it('shows the draft notice only on legal pages while placeholders remain', async () => {
    await render(<Page />);

    const shouldShow = Boolean(document.legal) && isLegalDraft();
    expect(screen.queryByText(DRAFT_NOTICE) !== null).toBe(shouldShow);
  });
});

describe('legal facts', () => {
  it('lists every unfilled placeholder so go-live can be checked', () => {
    expect(unfilledLegalFields()).toEqual(
      Object.entries(LEGAL)
        .filter(([, value]) => value.startsWith('['))
        .map(([key]) => key),
    );
  });

  it('never claims the message is stored or that cookies are used', () => {
    const text = JSON.stringify([PRIVACY, KVKK, ABOUT]);

    expect(text).toContain('Web sitemiz çerez kullanmaz.');
    expect(text).toContain('kaydetmeyiz');
    expect(text).not.toMatch(/kesinlikle güvenli(dir)?\./);
  });

  it('states the actual rate-limit retention of IP hashes', () => {
    const text = JSON.stringify(PRIVACY);

    expect(text).toContain('tarama için 1 dakika, bildirimler için 1 saat');
  });
});
