/**
 * Normalize asset URLs returned by the backend API.
 *
 * Django REST Framework returns absolute URLs (e.g. http://127.0.0.1:8000/media/...)
 * for ImageField/FileField when request context is available. The browser can't
 * reach Docker-internal IPs, so we rewrite those to same-origin paths that Vite
 * proxies or the production web server will serve.
 *
 * Also handles the DRF dict format { url, name } for file fields.
 *
 * @param {string|object|null|undefined} value
 * @returns {string} usable URL or empty string
 */
export function normalizeMediaUrl(value) {
  if (!value) return ''

  // DRF file-field object: { url: 'http://...', name: 'bg.png' }
  if (typeof value === 'object' && value.url) {
    return normalizeMediaUrl(value.url)
  }

  if (typeof value !== 'string') return ''
  const trimmed = value.trim()
  if (!trimmed) return ''

  // Object/data URLs are already browser-local.
  if (trimmed.startsWith('blob:') || trimmed.startsWith('data:')) return trimmed

  // Already relative — return as is (Vite dev proxy or production serves these)
  if (trimmed.startsWith('/media/') || trimmed.startsWith('/static/')) return trimmed

  // Absolute URL from backend — extract pathname for same-origin use
  try {
    const parsed = new URL(trimmed, window.location.origin)
    if (parsed.pathname.startsWith('/media/') || parsed.pathname.startsWith('/static/')) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}`
    }
  } catch {
    // Invalid URL, return empty
    return ''
  }

  return trimmed
}