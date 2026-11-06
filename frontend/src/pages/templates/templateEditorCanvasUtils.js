import { normalizeMediaUrl } from '@/utils/normalizeMediaUrl.js'

export const TEXT_LIKE_WIDGETS = new Set(['text', 'date', 'clock', 'weekday'])

export function defaultWidgetName(type) {
  const map = {
    text: 'Text',
    image: 'Image',
    date: 'Date',
    weekday: 'Weekday',
    clock: 'Clock',
  }
  return map[type] || type
}

export function pctToPx(val, total) {
  if (val == null) return 0
  if (typeof val === 'number' && !Number.isNaN(val)) return (val / 100) * total
  const s = String(val).trim().replace('%', '')
  const n = parseFloat(s)
  if (Number.isNaN(n)) return 0
  return (n / 100) * total
}

export function pxToPct(px, total) {
  if (!total) return '0%'
  return `${((Number(px) / total) * 100).toFixed(4)}%`
}

export function normalizeTemplateImageUrl(rawUrl) {
  return normalizeMediaUrl(rawUrl)
}

export function widgetDomStyle(w) {
  return {
    width: `${w.width}px`,
    height: `${w.height}px`,
    transform: `translate(${w.x}px, ${w.y}px) rotate(${w.rotation || 0}deg)`,
    zIndex: w.zIndex ?? 1,
  }
}

export function widgetInnerChromeClass(type) {
  if (TEXT_LIKE_WIDGETS.has(type)) {
    return 'h-full min-h-0 w-full min-w-0 overflow-hidden rounded-none bg-transparent'
  }
  return 'h-full w-full overflow-hidden rounded-md border border-[var(--border-card)] bg-[var(--bg-input)]/50 dark:border-white/10 dark:bg-black/25'
}

export function parseWidgetsFromConfigJson(cj, canvasW, canvasH) {
  const cw = canvasW
  const ch = canvasH
  const list = Array.isArray(cj?.widgets) ? cj.widgets : []
  return list.map((raw) => {
    const rawType = String(raw.type || 'text').trim() || 'text'
    const widgetType = rawType === 'marquee' ? 'text' : rawType
    return {
      id: String(raw.id),
      type: widgetType,
      name: raw.name || defaultWidgetName(widgetType),
      x: pctToPx(raw.x, cw),
      y: pctToPx(raw.y, ch),
      width: pctToPx(raw.width, cw),
      height: pctToPx(raw.height, ch),
      rotation: Number(raw.rotation) || 0,
      zIndex: Number(raw.zIndex) || 1,
      visible: raw.visible !== false,
      content: raw.content ?? '',
      style: raw.style && typeof raw.style === 'object' ? { ...raw.style } : {},
    }
  })
}

export function widgetsToPercentPayload(widgets, canvasW, canvasH) {
  const cw = canvasW
  const ch = canvasH
  return widgets.map((w) => ({
    id: w.id,
    type: w.type,
    name: w.name,
    x: pxToPct(w.x, cw),
    y: pxToPct(w.y, ch),
    width: pxToPct(w.width, cw),
    height: pxToPct(w.height, ch),
    rotation: w.rotation || 0,
    zIndex: w.zIndex ?? 1,
    visible: w.visible !== false,
    content: w.content ?? '',
    style: w.style && typeof w.style === 'object' ? { ...w.style } : {},
  }))
}

export function buildPriceBindingPreviewMap(rows) {
  const mapped = {}
  for (const row of rows) {
    const key = String(row?.key || '').trim()
    if (!key) continue
    const entry = {
      value: row?.previous_price != null ? String(row.previous_price) : '',
      source: row?.source || 'none',
      hasValue: Boolean(row?.has_value),
      label: row?.label || key,
      bindingKey: key,
    }
    mapped[key] = entry
    const ptid = row?.price_type_id
    if (ptid != null && ptid !== '') {
      mapped[`price_type__${ptid}`] = entry
    }
  }
  return mapped
}

export function buildPriceBindingMapFromContext(priceBindingMap) {
  if (!priceBindingMap || typeof priceBindingMap !== 'object') return {}
  const mapped = {}
  for (const [key, row] of Object.entries(priceBindingMap)) {
    const entry = {
      value: row?.value != null ? String(row.value) : '',
      source: row?.source || 'publish',
      hasValue: Boolean(row?.has_value ?? row?.hasValue ?? row?.value),
      label: row?.label || key,
      bindingKey: row?.binding_key || row?.bindingKey || key,
    }
    mapped[key] = entry
  }
  return mapped
}
