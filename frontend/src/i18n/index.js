import { createI18n } from 'vue-i18n'
import fa from '@/locales/fa.json'
import en from '@/locales/en.json'
import ar from '@/locales/ar.json'
import de from '@/locales/de.json'
import fr from '@/locales/fr.json'
import es from '@/locales/es.json'
import tr from '@/locales/tr.json'
import {
  STORAGE_LOCALE,
  STORAGE_LOCALE_LEGACY,
  storageGet,
  storageSet,
} from '@/constants/branding.js'

const SUPPORTED_LOCALES = ['en', 'fa', 'ar', 'de', 'fr', 'es', 'tr']
const RTL_LOCALES = new Set(['fa', 'ar'])

const safeStorage = {
  get() {
    return storageGet(STORAGE_LOCALE, STORAGE_LOCALE_LEGACY)
  },
  set(value) {
    storageSet(STORAGE_LOCALE, STORAGE_LOCALE_LEGACY, value)
  },
}

// English-first: the marketing page and its crawler metadata are en_GB, and the
// panel now shares one locale with it. A returning visitor keeps their choice.
const savedLocale = safeStorage.get() || 'en'
const initialLocale = SUPPORTED_LOCALES.includes(savedLocale) ? savedLocale : 'en'

// Some bundlers may expose JSON as { default: ... }
const resolveMessages = (mod) => mod?.default ?? mod

const localeMessages = {
  en: resolveMessages(en),
  fa: resolveMessages(fa),
  ar: resolveMessages(ar),
  de: resolveMessages(de),
  fr: resolveMessages(fr),
  es: resolveMessages(es),
  tr: resolveMessages(tr),
}

const enMessages = localeMessages.en

/** Resolve nested key (e.g. "dashboard.title") from a messages object */
function getMessageByPath(obj, path) {
  if (!obj || typeof path !== 'string') return undefined
  const keys = path.split('.')
  let current = obj
  for (const k of keys) {
    if (current == null || typeof current !== 'object') return undefined
    current = current[k]
  }
  return typeof current === 'string' ? current : undefined
}

function applyDocumentLocale(locale) {
  document.documentElement.lang = locale
  document.documentElement.dir = RTL_LOCALES.has(locale) ? 'rtl' : 'ltr'
}

// Composition mode: `useI18n()` in a legacy-mode app returns a *local* composer
// with its own locale, which left the landing page (useI18n) in English while the
// panel ($t) followed the stored locale — English copy laid out RTL. One composer
// for both; `globalInjection` keeps `$t` working in every template.
const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
  globalInjection: true,
  missingWarn: false,
  fallbackWarn: false,
  messages: localeMessages,
  missing: (locale, key) => {
    // If key is missing in current locale, return fallback (en) message so raw key is never shown
    const fallback = getMessageByPath(enMessages, key)
    return fallback ?? key
  },
})

applyDocumentLocale(initialLocale)

export { SUPPORTED_LOCALES, RTL_LOCALES }

export function setLocale(locale) {
  const next = SUPPORTED_LOCALES.includes(locale) ? locale : 'en'
  const g = i18n.global
  if (typeof g.locale === 'string') {
    g.locale = next
  } else if (g.locale && typeof g.locale === 'object' && 'value' in g.locale) {
    g.locale.value = next
  }
  safeStorage.set(next)
  applyDocumentLocale(next)
}

export default i18n