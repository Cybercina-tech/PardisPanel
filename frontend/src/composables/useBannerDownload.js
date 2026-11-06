import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { finalizeApi, resolveApiErrorMessage } from '@/services/api'

function filenameFromDisposition(header, fallback) {
  if (!header) return fallback
  const encoded = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(header)
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, '')) || fallback
    } catch {
      /* fall through to the plain filename */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header)
  return plain ? plain[1].trim() || fallback : fallback
}

/** A failed blob request carries its JSON error body as a Blob. */
async function errorMessageFrom(err) {
  const body = err?.response?.data
  let data = body
  if (body instanceof Blob) {
    try {
      data = JSON.parse(await body.text())
    } catch {
      data = null
    }
  }
  return resolveApiErrorMessage({ data, status: err?.response?.status })
}

/**
 * Downloads a rendered banner PNG for a category (`kind: 'category'`, id = category id)
 * or a special price (`kind: 'special'`, id = special price history id) in one of the
 * sizes `standard`, `story` or `post`. Only renders: it never finalizes a price or
 * uploads to a channel.
 */
export function useBannerDownload() {
  const { t } = useI18n()
  const toast = useToast()
  const busyKey = ref(null)

  const keyOf = (kind, id, size) => `${kind}:${id}:${size}`
  const isDownloading = (kind, id, size = 'standard') => busyKey.value === keyOf(kind, id, size)
  const isBusy = computed(() => busyKey.value != null)

  async function downloadBanner(kind, id, size = 'standard') {
    if (busyKey.value != null) return
    busyKey.value = keyOf(kind, id, size)
    try {
      // `silent` suppresses the global error toast; the one below says it in the user's language.
      const request = kind === 'category' ? finalizeApi.categoryBanner : finalizeApi.specialPriceBanner
      const res = await request(id, size, { silent: true })
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: 'image/png' })
      const filename = filenameFromDisposition(res.headers?.['content-disposition'], `${kind}-${id}-${size}.png`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      toast.error((await errorMessageFrom(err)) || t('finalize.banner.error'))
    } finally {
      busyKey.value = null
    }
  }

  return { downloadBanner, isDownloading, isBusy }
}
