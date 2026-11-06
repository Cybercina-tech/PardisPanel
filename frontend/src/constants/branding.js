/** Default site / product name shown in UI, PWA, and document title. */
export const DEFAULT_SITE_NAME = 'Sarafi Pardis'

/** Bundled Sarafi Pardis logo, used until a logo is uploaded in Settings. */
export const DEFAULT_LOGO_URL = '/brand/sarafi-pardis-logo.png'

/** localStorage primary keys (rebrand); legacy keys are still read for migration. */
export const STORAGE_LOCALE = 'mrexchange-locale'
export const STORAGE_LOCALE_LEGACY = 'smartexchange-locale'
export const STORAGE_THEME = 'mrexchange-theme'
export const STORAGE_THEME_LEGACY = 'smartexchange-theme'
export const STORAGE_PWA_DISMISSED = 'mrexchange-pwa-dismissed'
export const STORAGE_PWA_DISMISSED_LEGACY = 'smartexchange-pwa-dismissed'
export const STORAGE_RECENT_SEARCHES = 'mrexchange-recent-searches'
export const STORAGE_RECENT_SEARCHES_LEGACY = 'smartexchange-recent-searches'

export function storageGet(primaryKey, legacyKey) {
  if (typeof window === 'undefined') return null
  try {
    const v = window.localStorage.getItem(primaryKey)
    if (v != null && v !== '') return v
    if (legacyKey) return window.localStorage.getItem(legacyKey)
    return null
  } catch {
    return null
  }
}

export function storageSet(primaryKey, legacyKey, value) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(primaryKey, value)
    if (legacyKey) window.localStorage.removeItem(legacyKey)
  } catch {
    // ignore
  }
}

export function storageRemove(primaryKey, legacyKey) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(primaryKey)
    if (legacyKey) window.localStorage.removeItem(legacyKey)
  } catch {
    // ignore
  }
}
