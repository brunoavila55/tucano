import { describe, expect, it, vi } from 'vitest';
import { readHealth } from './health';

describe('readHealth', () => {
  it('returns online only for a healthy API response', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
    await expect(readHealth(fetcher)).resolves.toBe('online');
  });

  it('returns offline when the API cannot be reached', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('network unavailable'));
    await expect(readHealth(fetcher)).resolves.toBe('offline');
  });
});

