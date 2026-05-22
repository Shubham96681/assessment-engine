/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_RESOURCES_LIBRARY_URL?: string
  /** Sent as login password when the form has no password field (must match seeded accounts). */
  readonly VITE_DEFAULT_LOGIN_PASSWORD?: string
  /** Skip login UI; pair with backend AUTH_DISABLED. */
  readonly VITE_AUTH_DISABLED?: string
}
