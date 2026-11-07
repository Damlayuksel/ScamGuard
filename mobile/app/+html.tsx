import { useServerDocumentContext } from 'expo-router/html';
import { type PropsWithChildren } from 'react';

import { palettes, themeCss } from '@/lib/theme';

// Theme colour variables, plus layout that lets `flex: 1` screens fill the viewport while
// keeping normal page scrolling. The background is painted before JavaScript loads, so
// there is no white flash in dark mode.
const rootStyle = `${themeCss}
html, body { height: 100%; }
body { margin: 0; background-color: var(--color-background); }
#root { display: flex; flex-direction: column; min-height: 100%; }
`;

// Web only: root HTML for every statically rendered page. Runs in Node.js at build time,
// so browser APIs are not available here.
// ScrollViewStyleReset is intentionally not used: it disables body scrolling, which works
// better on mobile browsers; rootStyle above covers the height part of it.
export default function Root({ children }: PropsWithChildren) {
  const { headNodes, bodyNodes, htmlAttributes, bodyAttributes } = useServerDocumentContext();

  return (
    <html lang="tr" {...htmlAttributes}>
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="color-scheme" content="light dark" />
        <meta
          name="theme-color"
          media="(prefers-color-scheme: light)"
          content={palettes.light.background}
        />
        <meta
          name="theme-color"
          media="(prefers-color-scheme: dark)"
          content={palettes.dark.background}
        />
        <meta name="referrer" content="no-referrer" />
        <style dangerouslySetInnerHTML={{ __html: rootStyle }} />
        {headNodes}
      </head>
      <body {...bodyAttributes}>
        {children}
        {bodyNodes}
      </body>
    </html>
  );
}
