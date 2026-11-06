import { unref } from 'vue'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const PREFIX = 'price-draft:'
const MAX_AGE_MS = 24 * 60 * 60 * 1000

/**
 * Keeps what an operator typed into a price form in this browser until the save
 * succeeds, so a failed request, an expired session (the API client bounces to
 * /login) or an accidental reload never costs them the numbers.
 *
 * `key` may be a string or a ref; storage failures (private mode, quota) are
 * swallowed because the form still works without a draft.
 */
export function usePriceDraft(key) {
  const toast = useToast()
  const { t } = useI18n()

  const storageKey = () => `${PREFIX}${unref(key)}`

  function load() {
    try {
      const raw = localStorage.getItem(storageKey())
      if (!raw) return null
      const draft = JSON.parse(raw)
      if (!draft?.savedAt || Date.now() - draft.savedAt > MAX_AGE_MS) {
        localStorage.removeItem(storageKey())
        return null
      }
      return draft.values ?? null
    } catch {
      return null
    }
  }

  function save(values) {
    try {
      localStorage.setItem(storageKey(), JSON.stringify({ savedAt: Date.now(), values }))
    } catch {
      /* draft is a convenience, never block the form */
    }
  }

  function clear() {
    try {
      localStorage.removeItem(storageKey())
    } catch {
      /* ignore */
    }
  }

  function notifyRestored() {
    toast.info(t('toast.draftRestored'))
  }

  function notifyNotSaved() {
    toast.error(t('toast.pricesNotSaved'))
  }

  return { load, save, clear, notifyRestored, notifyNotSaved }
}
