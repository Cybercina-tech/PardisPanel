/**
 * Mirror backend template_editor.utils._shape_rtl_text_for_pil for editor preview:
 * arabic reshape + bidi-js visual reorder (like python-bidi get_display).
 *
 * Reshape uses in-repo vendor (GPL-3.0); bidi uses vendored bidi-js (MIT) — both work when
 * Docker mounts a named volume over node_modules that lags package.json changes.
 */
import reshaperApi from '@/vendor/arabicReshaperLouy.js'
import bidiFactory from '@/vendor/bidiJs.mjs'

function isRtlScript(text) {
  if (!text) return false
  const s = String(text)
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i)
    if (c >= 0x0600 && c <= 0x06ff) return true
    if (c >= 0x0750 && c <= 0x077f) return true
  }
  return false
}

let bidiInstance = null
function getBidi() {
  if (!bidiInstance) bidiInstance = bidiFactory()
  return bidiInstance
}

export function shapeLikePil(text, enabled) {
  const s = text == null ? '' : String(text)
  if (!enabled || !isRtlScript(s)) return s
  try {
    const reshaped = reshaperApi.convertArabic(s)
    const bidi = getBidi()
    const embed = bidi.getEmbeddingLevels(reshaped, 'ltr')
    return bidi.getReorderedString(reshaped, embed)
  } catch {
    return s
  }
}

export function useArabicReshaperFromStyle(style) {
  if (!style || typeof style !== 'object') return true
  const v = style.useArabicReshaper ?? style.use_arabic_reshaper
  if (v === false) return false
  if (v === true) return true
  return true
}
