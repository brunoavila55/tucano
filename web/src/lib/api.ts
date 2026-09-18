export type Role = 'professional' | 'client';

export type User = {
  id: string;
  email: string;
  display_name: string;
  email_verified: boolean;
  roles: Role[];
};

type Session = {
  access_token: string;
  access_expires_at: string;
  user: User;
};

export type ActionResponse = {
  message: string;
  user?: User;
  development_action_token?: string;
};

export type ServiceCategory = {
  id: string;
  slug: string;
  name: string;
  description: string;
};

export type Availability = {
  id?: string;
  weekday: number;
  start_time: string;
  end_time: string;
};

export type PortfolioItem = {
  id: string;
  url: string;
  original_name: string;
  media_type: string;
  size_bytes: number;
  sort_order: number;
};

export type ProfessionalProfile = {
  id: string;
  bio: string;
  primary_category: ServiceCategory | null;
  skills: string[];
  service_region: string;
  location_configured: boolean;
  service_radius_km: number;
  reference_price_cents: number | null;
  available_now: boolean;
  availability_timezone: string;
  availabilities: Availability[];
  portfolio: PortfolioItem[];
};

export type ProfessionalSearchResult = {
  id: string;
  display_name: string;
  bio: string;
  category: ServiceCategory;
  skills: string[];
  service_region: string;
  service_radius_km: number;
  reference_price_cents: number | null;
  available_now: boolean;
  distance_km: number;
  cover_url?: string;
};

export type ProfessionalSearchPage = {
  items: ProfessionalSearchResult[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export class APIError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number
  ) {
    super(message);
  }
}

let accessToken = '';

async function decode<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const body = (await response.json().catch(() => ({}))) as {
    error?: { code?: string; message?: string };
  };
  if (!response.ok) {
    throw new APIError(
      body.error?.code ?? 'request_failed',
      body.error?.message ?? 'Não foi possível concluir a solicitação.',
      response.status
    );
  }
  return body as T;
}

async function request<T>(path: string, init: RequestInit = {}, authenticate = false): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (authenticate && accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`/api${path}`, { ...init, headers, credentials: 'include' });
  return decode<T>(response);
}

function keepSession(session: Session): User {
  accessToken = session.access_token;
  return session.user;
}

export async function register(input: {
  email: string;
  password: string;
  display_name: string;
  profile_type: Role;
  company_name?: string;
}): Promise<ActionResponse> {
  return request('/auth/register', { method: 'POST', body: JSON.stringify(input) });
}

export async function verifyEmail(token: string): Promise<ActionResponse> {
  return request('/auth/verify-email', { method: 'POST', body: JSON.stringify({ token }) });
}

export async function resendVerification(email: string): Promise<ActionResponse> {
  return request('/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) });
}

export async function login(email: string, password: string): Promise<User> {
  const session = await request<Session>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });
  return keepSession(session);
}

export async function restoreSession(): Promise<User> {
  const session = await request<Session>('/auth/refresh', { method: 'POST' });
  return keepSession(session);
}

export async function logout(): Promise<void> {
  try {
    await request('/auth/logout', { method: 'POST' });
  } finally {
    accessToken = '';
  }
}

export async function getMe(): Promise<User> {
  if (!accessToken) return restoreSession();
  try {
    const response = await request<{ user: User }>('/account/me', {}, true);
    return response.user;
  } catch (error) {
    if (!(error instanceof APIError) || error.status !== 401) throw error;
    return restoreSession();
  }
}

export async function addProfile(profile_type: Role, company_name = ''): Promise<User> {
  if (!accessToken) await restoreSession();
  const response = await request<{ user: User }>(
    '/account/profiles',
    { method: 'POST', body: JSON.stringify({ profile_type, company_name }) },
    true
  );
  return response.user;
}

export async function requestPasswordReset(email: string): Promise<ActionResponse> {
  return request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) });
}

export async function resetPassword(token: string, password: string): Promise<ActionResponse> {
  return request('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, password })
  });
}

export async function listCategories(): Promise<ServiceCategory[]> {
  const response = await request<{ categories: ServiceCategory[] }>('/categories');
  return response.categories;
}

export async function getProfessionalProfile(): Promise<ProfessionalProfile> {
  if (!accessToken) await restoreSession();
  const response = await request<{ profile: ProfessionalProfile }>('/professional/profile', {}, true);
  return response.profile;
}

export async function updateProfessionalProfile(input: {
  bio: string;
  primary_category_id: string;
  skills: string[];
  service_region: string;
  latitude?: number;
  longitude?: number;
  service_radius_km: number;
  reference_price_cents: number | null;
  available_now: boolean;
  availability_timezone: string;
  availabilities: Availability[];
}): Promise<ProfessionalProfile> {
  if (!accessToken) await restoreSession();
  const response = await request<{ profile: ProfessionalProfile }>(
    '/professional/profile',
    { method: 'PUT', body: JSON.stringify(input) },
    true
  );
  return response.profile;
}

export async function uploadPortfolioItem(file: File): Promise<PortfolioItem> {
  if (!accessToken) await restoreSession();
  const form = new FormData();
  form.set('file', file);
  const response = await request<{ item: PortfolioItem }>(
    '/professional/portfolio',
    { method: 'POST', body: form },
    true
  );
  return response.item;
}

export async function deletePortfolioItem(itemId: string): Promise<void> {
  if (!accessToken) await restoreSession();
  await request(`/professional/portfolio/${encodeURIComponent(itemId)}`, { method: 'DELETE' }, true);
}

export async function searchProfessionals(input: {
  category_id: string;
  latitude: number;
  longitude: number;
  radius_km: number;
  available_now?: boolean;
  page?: number;
  page_size?: number;
}): Promise<ProfessionalSearchPage> {
  if (!accessToken) await restoreSession();
  const query = new URLSearchParams({
    category_id: input.category_id,
    latitude: String(input.latitude),
    longitude: String(input.longitude),
    radius_km: String(input.radius_km),
    available_now: String(input.available_now ?? false),
    page: String(input.page ?? 1),
    page_size: String(input.page_size ?? 20)
  });
  return request(`/professionals/search?${query}`, {}, true);
}

export function errorMessage(error: unknown): string {
  if (error instanceof APIError) return error.message;
  return 'Não foi possível conectar. Verifique sua internet e tente novamente.';
}

export function clearAccessTokenForTests(): void {
  accessToken = '';
}
