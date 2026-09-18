import { afterEach, describe, expect, it, vi } from 'vitest';
import { APIError, clearAccessTokenForTests, login, restoreSession, uploadPortfolioItem } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
  clearAccessTokenForTests();
});

describe('authentication API', () => {
  it('always includes credentials so the HttpOnly refresh cookie can be used', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: 'access',
          access_expires_at: new Date().toISOString(),
          user: { id: '1', email: 'ana@example.com', display_name: 'Ana', email_verified: true, roles: ['professional'] }
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    );
    vi.stubGlobal('fetch', fetcher);

    await login('ana@example.com', 'senha-segura-123');

    expect(fetcher).toHaveBeenCalledWith(
      '/api/auth/login',
      expect.objectContaining({ credentials: 'include', method: 'POST' })
    );
  });

  it('surfaces the safe API error message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: { code: 'invalid_refresh_token', message: 'Sessão expirada.' } }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );

    await expect(restoreSession()).rejects.toEqual(
      expect.objectContaining<Partial<APIError>>({ code: 'invalid_refresh_token', message: 'Sessão expirada.', status: 401 })
    );
  });

  it('does not override the multipart boundary when uploading a portfolio image', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: 'access',
            access_expires_at: new Date().toISOString(),
            user: { id: '1', email: 'ana@example.com', display_name: 'Ana', email_verified: true, roles: ['professional'] }
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ item: { id: '2', url: '/api/uploads/test.jpg', original_name: 'test.jpg', media_type: 'image/jpeg', size_bytes: 3, sort_order: 0 } }),
          { status: 201, headers: { 'Content-Type': 'application/json' } }
        )
      );
    vi.stubGlobal('fetch', fetcher);
    await login('ana@example.com', 'senha-segura-123');

    await uploadPortfolioItem(new File(['abc'], 'test.jpg', { type: 'image/jpeg' }));

    const options = fetcher.mock.calls[1][1] as RequestInit;
    expect(options.body).toBeInstanceOf(FormData);
    expect(new Headers(options.headers).has('Content-Type')).toBe(false);
  });
});
