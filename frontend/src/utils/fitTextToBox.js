import {
  getLiveDatePreviewSamples,
  previewTextForDateWidget,
} from '@/pages/templates/dateWidgetPresets.js'
import { editorFontFamilyToken } from '@/pages/templates/templateEditorFonts.js'
import { toPersianDigits } from '@/utils/persianDigits.js'

function priceLocaleIsFa(style) {
  const loc = String(style?.priceLocale || style?.price_locale || 'en').toLowerCase()
  return loc === 'fa' || loc === 'fas'
}

/** String used to estimate rendered width/height for a widget. */
/** Same sample strings as TextWidgetPreview; no PIL reshape so canvas measure matches editor preview. */
export function getWidgetTextForMeasure(w) {
  if (!w) return 'M'
  const bk = w.style?.bindingKey || w.style?.binding_key
  const t = w.type
  let raw = 'M'
  if (t === 'text') {
    const pt = w.style?.priceTypeId ?? w.style?.price_type_id
    const hasPriceBinding =
      (pt != null && String(pt).trim() !== '') ||
      (bk && String(bk).trim().toLowerCase().startsWith('price'))
    if (hasPriceBinding) {
      const c = w.content && String(w.content).trim() ? String(w.content).trim() : '123,456'
      const sample = priceLocaleIsFa(w.style) ? toPersianDigits(c) : c
      raw = sample.split('\n')[0] || sample
      return raw
    }
    if (bk) raw = `[${String(bk).trim()}]`
    else {
      const c = w.content
      raw = c && String(c).trim() ? String(c).trim() : 'Sample text'
    }
    return raw
  }
  if (t === 'date' || t === 'weekday')
    raw = previewTextForDateWidget(w) || getLiveDatePreviewSamples().date_fa
  else if (t === 'clock') raw = '99:99'
  return raw
}

export function fontStackForWidgetMeasure(w) {
  const s = w?.style || {}
  const file = s.font || s.fontFilename || s.font_filename
  const token = file ? editorFontFamilyToken(String(file)) : ''
  return token
    ? `'${token}', Vazirmatn, "Segoe UI", system-ui, sans-serif`
    : 'Vazirmatn, Inter, system-ui, sans-serif'
}

/**
 * Largest font size (px) so a single line fits inside the box (canvas measureText).
 */
export function measureMaxFontSize(
  boxW,
  boxH,
  text,
  { fontFamily = 'Vazirmatn, sans-serif', fontWeight = 'normal', min = 8, max = 220 } = {},
) {
  const line = String(text || 'M').split('\n')[0] || 'M'
  const bw = Math.max(4, Number(boxW) || 0)
  const bh = Math.max(4, Number(boxH) || 0)
  if (typeof document === 'undefined') {
    return Math.min(max, Math.max(min, Math.round(bh * 0.55)))
  }
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) return Math.min(max, Math.max(min, Math.round(bh * 0.55)))
  const weightPrefix = fontWeight === 'bold' || fontWeight === 700 || fontWeight === '700' ? 'bold ' : ''
  let lo = min
  let hi = max
  let best = min
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    ctx.font = `${weightPrefix}${mid}px ${fontFamily}`
    let tw = 0
    try {
      tw = ctx.measureText(line).width
    } catch {
      tw = line.length * mid * 0.62
    }
    const lineH = mid * 1.18
    if (tw <= bw && lineH <= bh) {
      best = mid
      lo = mid + 1
    } else {
      hi = mid - 1
    }
  }
  return Math.max(min, Math.min(max, best))
}

export function fitFontSizeToWidgetBox(w) {
  if (!w?.style || typeof w.style !== 'object') w.style = {}
  const padX = 16
  const padY = 8
  const fw = Math.max(8, (Number(w.width) || 0) - padX)
  const fh = Math.max(8, (Number(w.height) || 0) - padY)
  const txt = getWidgetTextForMeasure(w)
  const fam = fontStackForWidgetMeasure(w)
  const fwgt = w.style.fontWeight || w.style.weight || 'normal'
  w.style.fontSize = measureMaxFontSize(fw, fh, txt, { fontFamily: fam, fontWeight: fwgt })
}
