<template>
  <div
    class="flex h-full min-h-0 w-full min-w-0 overflow-hidden px-2 font-medium leading-tight text-[var(--text-primary)]"
    :class="isPersianDate ? '' : 'text-center'"
    :style="containerStyle"
  >
    <span :style="textStyle" :dir="textDirAttr">{{ display }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { editorFontFamilyToken } from '@/pages/templates/templateEditorFonts.js'
import { useTemplateEditorInjected } from '@/pages/templates/templateEditorInjectionKey.js'
import {
  previewTextForDateWidget,
  resolvedDateKey,
  isPersianDateKey,
} from '@/pages/templates/dateWidgetPresets.js'
import { toPersianDigits } from '@/utils/persianDigits.js'

const props = defineProps({
  widget: { type: Object, required: true },
})
const te = useTemplateEditorInjected()

function priceLocaleFa(style) {
  const loc = String(style?.priceLocale || style?.price_locale || 'en').toLowerCase()
  return loc === 'fa' || loc === 'fas'
}

/** Matches backend _is_price_like_key — only these bindings use price digit locale. */
function isPriceLikeBinding(widget) {
  const pt = widget?.style?.priceTypeId ?? widget?.style?.price_type_id
  if (pt != null && String(pt).trim() !== '') return true
  const bk = String(widget?.style?.bindingKey || widget?.style?.binding_key || '').trim().toLowerCase()
  if (!bk) return false
  if (bk === 'price') return true
  const prefixes = ('price__', 'price_type__', 'price_buy__', 'price_sell__', 'price_buy_', 'price_sell_', 'tether_buy_', 'tether_sell_')
  return prefixes.some((p) => bk.startsWith(p))
}

function localizePriceDisplay(raw, style, widget) {
  const s = raw != null ? String(raw).trim() : ''
  if (!s) return s
  if (!priceLocaleFa(style) || !isPriceLikeBinding(widget)) return s
  return toPersianDigits(s)
}

const display = computed(() => {
  const raw = (() => {
    const PRICE_PLACEHOLDER = '123,456'
    const w = props.widget
    const st = w?.style || {}
    const ptRaw = w?.style?.priceTypeId ?? w?.style?.price_type_id
    if (ptRaw != null && String(ptRaw).trim() !== '') {
      const idKey = `price_type__${String(ptRaw).trim()}`
      const resolved = te.priceBindingPreviewMap?.value?.[idKey]
      const fromPreview = resolved?.value != null ? String(resolved.value).trim() : ''
      if (fromPreview) return localizePriceDisplay(fromPreview, st, w)
      const bk = w?.style?.bindingKey || w?.style?.binding_key
      if (bk) {
        const byKey = te.priceBindingPreviewMap?.value?.[String(bk).trim()]
        const fromKey = byKey?.value != null ? String(byKey.value).trim() : ''
        if (fromKey) return localizePriceDisplay(fromKey, st, w)
      }
      const fallback = w?.content != null ? String(w.content).trim() : ''
      if (fallback && !/^sample text$/i.test(fallback) && !/^text$/i.test(fallback) && !/^\[.*\]$/.test(fallback)) {
        return localizePriceDisplay(fallback, st, w)
      }
      return localizePriceDisplay(PRICE_PLACEHOLDER, st, w)
    }
    const bk = w?.style?.bindingKey || w?.style?.binding_key
    if (bk) {
      const resolved = te.priceBindingPreviewMap?.value?.[String(bk).trim()]
      const fromPreview = resolved?.value != null ? String(resolved.value).trim() : ''
      if (fromPreview) return localizePriceDisplay(fromPreview, st, w)
      const fallback = w?.content != null ? String(w.content).trim() : ''
      if (fallback && !/^sample text$/i.test(fallback) && !/^text$/i.test(fallback) && !/^\[.*\]$/.test(fallback)) {
        return localizePriceDisplay(fallback, st, w)
      }
      return localizePriceDisplay(PRICE_PLACEHOLDER, st, w)
    }
    const t = w?.type
    if (t === 'date' || t === 'weekday') {
      return previewTextForDateWidget(w)
    }
    if (t === 'clock') return '14:30'
    const c = w?.content
    if (c && String(c).trim()) {
      const normalized = String(c).trim()
      if (!/^sample text$/i.test(normalized) && !/^text$/i.test(normalized)) return normalized
    }
    return PRICE_PLACEHOLDER
  })()
  // Editor preview: always native shaping (RTL/LTR from styles). PIL reshape runs on device/export only.
  return raw
})

const align = computed(() => {
  const a = String(props.widget?.style?.align || 'center').toLowerCase()
  if (a === 'left' || a === 'start') return 'left'
  if (a === 'right' || a === 'end') return 'right'
  return 'center'
})

const isPersianDate = computed(() => {
  const t = props.widget?.type
  if (t !== 'date' && t !== 'weekday') return false
  return isPersianDateKey(resolvedDateKey(props.widget))
})

const verticalAlignItems = computed(() => {
  const a = String(props.widget?.style?.verticalAlign ?? props.widget?.style?.vertical_align ?? 'middle').toLowerCase()
  if (a === 'top' || a === 'start') return 'flex-start'
  if (a === 'bottom' || a === 'end') return 'flex-end'
  return 'center'
})

const textDirAttr = computed(() => (isPersianDate.value ? 'rtl' : undefined))

/** Single-line box fit in editor (matches canvas measure in fitTextToBox). */
const useSingleLineFit = computed(() => {
  const t = props.widget?.type
  return t === 'text' || t === 'date' || t === 'weekday' || t === 'clock'
})

const containerStyle = computed(() => {
  const a = align.value
  const persian = isPersianDate.value
  let justify
  if (persian) {
    if (a === 'left') justify = 'flex-start'
    else if (a === 'right') justify = 'flex-end'
    else justify = 'flex-end'
  } else {
    justify = a === 'left' ? 'flex-start' : a === 'right' ? 'flex-end' : 'center'
  }
  return {
    justifyContent: justify,
    alignItems: verticalAlignItems.value,
  }
})

const textStyle = computed(() => {
  const s = props.widget?.style || {}
  const file = s.font || s.fontFilename || s.font_filename
  const token = file ? editorFontFamilyToken(String(file)) : ''
  const fontStack = token
    ? `'${token}', Vazirmatn, 'Segoe UI', system-ui, sans-serif`
    : 'Vazirmatn, Inter, system-ui, sans-serif'
  const persian = isPersianDate.value
  const ta = persian ? (align.value === 'left' ? 'left' : align.value === 'right' ? 'right' : 'right') : align.value
  // When a font file is selected, its @font-face token must win — legacy `fontFamily`
  // from saved templates would otherwise ignore the dropdown until removed.
  const fontFamily = file ? fontStack : (s.fontFamily || fontStack)
  const style = {
    fontSize: `${s.fontSize ?? 24}px`,
    fontFamily,
    textAlign: ta,
    maxWidth: '100%',
    wordBreak: useSingleLineFit.value ? 'normal' : 'break-word',
    display: 'block',
    width: persian ? '100%' : undefined,
    direction: persian ? 'rtl' : undefined,
    unicodeBidi: persian ? 'plaintext' : undefined,
  }
  if (useSingleLineFit.value) {
    style.whiteSpace = 'nowrap'
    style.overflow = 'hidden'
    if (s.lineHeight == null || s.lineHeight === '') {
      style.lineHeight = 1.18
    }
  }
  const fw = s.fontWeight || s.weight
  if (fw) style.fontWeight = fw === 'bold' || fw === 700 ? '700' : String(fw)
  if (s.color) style.color = s.color
  if (s.lineHeight != null && s.lineHeight !== '') {
    const lh = Number(s.lineHeight)
    style.lineHeight = Number.isFinite(lh) ? String(lh) : String(s.lineHeight)
  }
  if (s.letterSpacing != null && s.letterSpacing !== '') style.letterSpacing = String(s.letterSpacing)
  return style
})
</script>
