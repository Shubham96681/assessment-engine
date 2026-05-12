const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''
const origin = raw.replace(/\/$/, '')

export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return origin ? `${origin}${p}` : p
}

/** Placeholder token when the UI skips login; never send as Bearer (invalid JWT). Backend uses AUTH_DISABLED instead. */
export const AUTH_DISABLED_PLACEHOLDER = 'auth-disabled'

/** Authorization header only for real JWTs — omit placeholder so the API can use AUTH_DISABLED without verifying garbage tokens. */
export function authHeaders(accessToken: string | null): Record<string, string> {
  const h: Record<string, string> = {}
  if (accessToken && accessToken !== AUTH_DISABLED_PLACEHOLDER) {
    h.Authorization = `Bearer ${accessToken}`
  }
  return h
}
