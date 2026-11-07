/** Routes Android text shares to the in-memory share handler without putting text in a URL. */
export function redirectSystemPath({ path }: { path: string; initial: boolean }) {
  try {
    if (new URL(path).hostname === 'expo-sharing') {
      return '/paylas';
    }
  } catch {
    // Invalid external paths fall through to Expo Router's regular handling.
  }

  return path;
}
