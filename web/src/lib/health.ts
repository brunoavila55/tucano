export type HealthStatus = 'loading' | 'online' | 'offline';

type HealthPayload = { status?: string };

export async function readHealth(fetcher: typeof fetch = fetch): Promise<HealthStatus> {
  try {
    const response = await fetcher('/api/health', { headers: { Accept: 'application/json' } });
    if (!response.ok) return 'offline';
    const body = (await response.json()) as HealthPayload;
    return body.status === 'ok' ? 'online' : 'offline';
  } catch {
    return 'offline';
  }
}

