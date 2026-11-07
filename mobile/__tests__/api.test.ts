import { ApiError, scanMessage } from '@/lib/api';

import { DANGEROUS_RESULT, jsonResponse } from '@/testing/utils';

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  globalThis.fetch = fetchMock as unknown as typeof fetch;
});

describe('scanMessage', () => {
  it('posts the text in the body, never in the URL', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, DANGEROUS_RESULT));
    const text = 'Kargonuz bekliyor: https://ptt-kargo-takip.xyz/a?id=1';

    const result = await scanMessage(text);

    expect(result).toEqual(DANGEROUS_RESULT);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/scan$/);
    expect(url).not.toContain('ptt-kargo');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ text });
    expect(init.credentials).toBe('omit');
    expect(init.referrerPolicy).toBe('no-referrer');
  });

  it('uses the backend Turkish message for rate limits', async () => {
    fetchMock.mockResolvedValue(jsonResponse(429, { detail: 'Biraz bekleyin.' }));

    await expect(scanMessage('x')).rejects.toMatchObject({
      kind: 'rate_limited',
      message: 'Biraz bekleyin.',
    });
  });

  it.each([
    [422, 'validation'],
    [500, 'server'],
    [503, 'server'],
  ])('maps HTTP %i to %s', async (status, kind) => {
    fetchMock.mockResolvedValue(jsonResponse(status, { detail: 'x' }));

    const error = await scanMessage('x').catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).kind).toBe(kind);
    expect((error as ApiError).message).not.toBe('x');
  });

  it('reports network failures in Turkish', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(scanMessage('x')).rejects.toMatchObject({
      kind: 'network',
      message: expect.stringContaining('Bağlantı kurulamadı'),
    });
  });
});
