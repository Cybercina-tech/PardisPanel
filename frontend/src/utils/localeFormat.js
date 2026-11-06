/**
 * Number and date formatting tied to the app's UI language (en | fa),
 * not the browser default locale (which caused wrong digit shapes).
 */

const PRESETS = {
  en: { tag: 'en-US', numberingSystem: 'latn' },
  fa: { tag: 'fa-IR', numberingSystem: 'arabext' },
}

function pack(appLocale) {
  return appLocale === 'fa' ? PRESETS.fa : PRESETS.en
}

/** @param {'en'|'fa'} appLocale */
export function formatAppNumber(appLocale, value, options = {}) {
  const { tag, numberingSystem } = pack(appLocale)
  const n = Number(value)
  if (value == null || value === '' || !Number.isFinite(n)) {
    if (value == null || value === '') return ''
    return String(value)
  }
  try {
    return new Intl.NumberFormat(tag, { numberingSystem, ...options }).format(n)
  } catch {
    return new Intl.NumberFormat(tag, options).format(n)
  }
}

/** @param {'en'|'fa'} appLocale */
export function formatAppDecimal(appLocale, value, fractionDigits = 2) {
  return formatAppNumber(appLocale, value, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

/**
 * @param {'en'|'fa'} appLocale
 * @param {Intl.DateTimeFormatOptions} options
 */
export function createAppDateTimeFormat(appLocale, options = {}) {
  const { tag, numberingSystem } = pack(appLocale)
  try {
    return new Intl.DateTimeFormat(tag, { numberingSystem, ...options })
  } catch {
    return new Intl.DateTimeFormat(tag, options)
  }
}
