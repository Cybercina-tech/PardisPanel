<template>
  <div class="template-editor-workspace flex h-[100dvh] max-h-[100dvh] min-h-0 min-w-0 flex-1 flex-col text-[var(--text-primary)]">
    <header
      class="sticky top-0 z-20 flex shrink-0 items-center gap-3 border-b border-[var(--border-card)] bg-[var(--bg-card)]/95 px-3 py-2.5 backdrop-blur-md sm:px-4"
    >
      <div class="flex w-28 shrink-0 items-center">
        <router-link
          to="/templates"
          class="inline-flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--primary)]"
        >
          <i class="fas fa-arrow-left" />
          <span>{{ $t('templateEditor.back') }}</span>
        </router-link>
      </div>
      <div class="min-w-0 flex-1 text-center">
        <h1 v-if="template" class="truncate text-sm font-semibold text-[var(--primary)] sm:text-base" :title="template.name">
          {{ template.name }}
        </h1>
        <span v-else class="text-sm text-[var(--text-secondary)]">{{ $t('templateEditor.template') }}</span>
      </div>
      <div class="flex w-48 shrink-0 items-center justify-end gap-2">
        <div class="flex flex-col items-end gap-0.5">
          <span class="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-card)] bg-[var(--bg-input)]/80 px-2 py-1 text-[11px] text-[var(--text-secondary)]">
            <span
              class="h-2 w-2 rounded-full"
              :class="saveIndicatorClass"
            />
            {{ saveStatusLabelLocal }}
          </span>
          <span v-if="lastSavedAt" class="text-[10px] text-[var(--text-secondary)]">
            {{ `Last save: ${lastSavedAt.toLocaleTimeString()}` }}
          </span>
        </div>
        <button type="button" class="btn-luxury py-1.5 px-4 text-sm" :disabled="isSaving" @click="save">
          {{ isSaving ? $t('templateEditor.saving') : $t('templateEditor.save') }}
        </button>
      </div>
    </header>

    <div v-if="loadError" class="p-8 text-center text-red-600 dark:text-red-300">{{ loadError }}</div>
    <div v-else-if="loading" class="flex flex-1 items-center justify-center p-8 text-[var(--text-secondary)]">{{ $t('templateEditor.loading') }}</div>

    <div v-else class="flex min-h-0 min-w-0 flex-1 gap-2 overflow-hidden p-2 sm:p-3">
      <WidgetLibraryPanel :category-id="template?.category ?? null" />
      <main
        class="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-[var(--border-card)] bg-[var(--bg-card)] shadow-[var(--shadow-card)]"
      >
        <div
          class="flex shrink-0 items-center justify-between gap-2 border-b border-[var(--border-card)] bg-[var(--bg-input)]/80 px-3 py-2 text-xs"
        >
          <span class="text-[var(--text-secondary)]">{{ $t('templateEditor.canvas') }} {{ canvasW }}×{{ canvasH }}</span>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="rounded-md border border-[var(--border-card)] px-2 py-0.5 text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
              @click="zoomOut"
            >
              −
            </button>
            <span class="w-11 text-center tabular-nums text-[var(--text-secondary)]">{{ Math.round(scale * 100) }}%</span>
            <button
              type="button"
              class="rounded-md border border-[var(--border-card)] px-2 py-0.5 text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
              @click="zoomIn"
            >
              +
            </button>
            <button
              type="button"
              class="rounded-md border border-[var(--border-card)] px-2 py-0.5 text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
              @click="fitZoom"
            >
              {{ $t('templateEditor.fit') }}
            </button>
          </div>
        </div>
        <div
          ref="viewportRef"
          class="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-[var(--editor-workspace-bg)] p-1 sm:p-2"
        >
          <div
            class="relative overflow-visible"
            :style="{
              width: `${canvasW * scale}px`,
              height: `${canvasH * scale}px`,
            }"
          >
            <div
              class="absolute left-0 top-0 overflow-visible"
              :style="{ transform: `scale(${scale})`, transformOrigin: 'top left' }"
            >
              <div
                ref="canvasRootRef"
                class="relative overflow-hidden rounded-md border border-[var(--editor-canvas-border)] bg-white shadow-[var(--editor-canvas-shadow)]"
                :style="{
                  width: canvasW + 'px',
                  height: canvasH + 'px',
                  backgroundColor: backgroundColor,
                }"
                @mousedown.self="clearSelection"
              >
                  <img
                    v-if="imageUrl"
                    ref="baseImageEl"
                    :src="imageUrl"
                    alt=""
                    class="pointer-events-none absolute inset-0 h-full w-full object-contain opacity-100"
                    draggable="false"
                    @load="onBaseImageLoad"
                  />
                  <div
                    v-for="item in sortedWidgets"
                    :key="item.id"
                    :ref="(el) => setWidgetEl(item.id, el)"
                    class="absolute box-border will-change-transform"
                    :style="widgetDomStyle(item)"
                    :data-wid="item.id"
                    @mousedown.stop="selectWidget(item.id)"
                  >
                    <div :class="widgetInnerChromeClass(item.type)">
                      <WidgetPreviewHost :widget="item" />
                    </div>
                  </div>
              </div>
              <Moveable
                v-if="moveableTarget"
                :key="selectedId || 'none'"
                class="template-editor-moveable"
                :target="moveableTarget"
                :pass-drag-area="true"
                :draggable="true"
                :resizable="true"
                :rotatable="true"
                :origin="false"
                :zoom="1 / scale"
                :throttle-drag="0"
                @drag="onDrag"
                @resize="onResize"
                @rotate="onRotate"
                @dragEnd="onDragEnd"
                @resizeEnd="onResizeEnd"
                @rotateEnd="onRotateEnd"
              />
            </div>
          </div>
          <div v-if="!imageUrl" class="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
            <button
              type="button"
              class="pointer-events-auto flex w-[min(92vw,520px)] flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-[var(--primary)]/80 bg-white/95 px-10 py-8 text-center text-base font-semibold text-[#0f172a] shadow-[var(--editor-canvas-shadow)] transition-all hover:-translate-y-0.5 hover:border-[var(--primary)] hover:shadow-[var(--shadow-card-hover)]"
              @click="openBackgroundPicker"
            >
              <span class="inline-flex h-14 w-14 items-center justify-center rounded-full bg-[var(--primary)]/15 text-[var(--primary)]">
                <i class="fas fa-image text-2xl" />
              </span>
              <span class="text-lg leading-tight">{{ $t('templateEditor.uploadBackgroundImage') }}</span>
              <span class="text-sm font-medium leading-relaxed text-slate-600">{{ $t('templateEditor.startDesignHint') }}</span>
            </button>
          </div>
        </div>
      </main>
      <TemplateInspectorPanel />
    </div>
    <input
      ref="backgroundFileInput"
      type="file"
      accept="image/jpeg,image/png,image/gif,image/webp"
      class="hidden"
      @change="onBackgroundFile"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import Moveable from 'vue3-moveable'
import { formatDrfError, templateEditorApi } from '@/services/api'
import { injectTemplateEditorFontFaces } from './templateEditorFonts.js'
import { useTemplatesStore } from '@/stores/templatesEditor'
import { provideTemplateEditor } from './templateEditorInjectionKey.js'
import WidgetLibraryPanel from './WidgetLibraryPanel.vue'
import TemplateInspectorPanel from './TemplateInspectorPanel.vue'
import WidgetPreviewHost from '@/components/template-editor/player/widgets/WidgetPreviewHost.vue'
import { fitFontSizeToWidgetBox } from '@/utils/fitTextToBox.js'
import {
  TEXT_LIKE_WIDGETS,
  normalizeTemplateImageUrl,
  pctToPx,
  pxToPct,
  widgetDomStyle,
  widgetInnerChromeClass,
  widgetsToPercentPayload,
} from './templateEditorCanvasUtils.js'

const route = useRoute()
const toast = useToast()
const { t } = useI18n()
const templatesStore = useTemplatesStore()

const loading = ref(true)
const loadError = ref('')
const saveState = ref('saved')
const hasLoadedOnce = ref(false)
const lastSavedAt = ref(null)
const template = ref(null)
const backgroundFileInput = ref(null)

const canvasW = ref(1920)
const canvasH = ref(1080)
const backgroundColor = ref('#ffffff')

const widgets = ref([])
const selectedId = ref(null)
const priceBindingPreviewMap = ref({})
const categoryPriceTypes = ref([])

const viewportRef = ref(null)
const canvasRootRef = ref(null)
const baseImageEl = ref(null)
const widgetEls = new Map()

const scale = ref(0.35)

const selectedWidget = computed(() => widgets.value.find((w) => w.id === selectedId.value) || null)
const isSaving = computed(() => templatesStore.saving || saveState.value === 'saving')
const saveStatusLabel = computed(() => {
  if (saveState.value === 'error') return t('templateEditor.saveFailed')
  if (isSaving.value) return t('templateEditor.saving')
  if (saveState.value === 'dirty') return t('templateEditor.unsavedChanges')
  return t('templateEditor.saved')
})
const saveIndicatorClass = computed(() => {
  if (saveState.value === 'error') return 'bg-red-500'
  if (isSaving.value) return 'bg-amber-400'
  if (saveState.value === 'dirty') return 'bg-sky-500'
  return 'bg-emerald-500'
})

const sortedWidgets = computed(() => [...widgets.value].sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0)))

const imageUrl = computed(() => {
  return normalizeTemplateImageUrl(template.value?.image)
})

/** Pixel rect where the background image is painted (`object-fit: contain` inside the canvas). Used for snap-to-image alignment. */
const backgroundImageContentRect = computed(() => {
  const cw = canvasW.value
  const ch = canvasH.value
  const el = baseImageEl.value
  if (!el?.naturalWidth || !el?.naturalHeight || cw < 1 || ch < 1) return null
  const iw = el.naturalWidth
  const ih = el.naturalHeight
  const s = Math.min(cw / iw, ch / ih)
  const dw = iw * s
  const dh = ih * s
  const ox = (cw - dw) / 2
  const oy = (ch - dh) / 2
  return {
    left: ox,
    top: oy,
    width: dw,
    height: dh,
    right: ox + dw,
    bottom: oy + dh,
  }
})

function alignSelectedToBackgroundEdge(edge) {
  const w = selectedWidget.value
  const r = backgroundImageContentRect.value
  if (!w || !r) return
  switch (edge) {
    case 'top':
      w.y = Math.round(r.top)
      break
    case 'bottom':
      w.y = Math.round(r.bottom - w.height)
      break
    case 'left':
      w.x = Math.round(r.left)
      break
    case 'right':
      w.x = Math.round(r.right - w.width)
      break
    case 'center-h':
      w.x = Math.round(r.left + (r.width - w.width) / 2)
      break
    case 'center-v':
      w.y = Math.round(r.top + (r.height - w.height) / 2)
      break
    default:
      return
  }
  clampWidgetToCanvas(w)
}

const moveableTarget = computed(() => {
  if (!selectedId.value) return null
  return widgetEls.get(selectedId.value) || null
})

function setWidgetEl(id, el) {
  if (el) widgetEls.set(id, el)
  else widgetEls.delete(id)
}

function clampWidgetToCanvas(w) {
  if (!w) return
  w.width = Math.max(24, Math.min(w.width || 0, canvasW.value))
  w.height = Math.max(24, Math.min(w.height || 0, canvasH.value))
  const maxX = Math.max(0, canvasW.value - w.width)
  const maxY = Math.max(0, canvasH.value - w.height)
  w.x = Math.min(maxX, Math.max(0, w.x || 0))
  w.y = Math.min(maxY, Math.max(0, w.y || 0))
}

/** Editor-only frame: text-like widgets show raw text; image keeps a light frame. */
function selectWidget(id) {
  selectedId.value = id
}

function clearSelection() {
  selectedId.value = null
}

function nextZIndex() {
  const zs = widgets.value.map((w) => w.zIndex || 0)
  return (zs.length ? Math.max(...zs) : 0) + 1
}

function defaultName(type) {
  const map = {
    text: 'Text',
    image: 'Image',
    date: 'Date',
    weekday: 'Weekday',
    clock: 'Clock',
  }
  return map[type] || type
}

/** Date / weekday / clock: scale box + font from canvas size so large banners stay readable (library adds only). */
function scaledDateLikePlacement(cw, ch) {
  const w = Math.max(1, Number(cw) || 1920)
  const h = Math.max(1, Number(ch) || 1080)
  const short = Math.min(w, h)
  const fontSize = Math.round(Math.min(96, Math.max(20, short * 0.032)))
  const boxW = Math.round(Math.min(w * 0.82, Math.max(280, w * 0.38)))
  const boxH = Math.round(Math.min(h * 0.12, Math.max(48, fontSize * 2.35)))
  return {
    x: Math.round(Math.max(0, (w - boxW) / 2)),
    y: Math.round(Math.max(0, h * 0.06)),
    width: boxW,
    height: boxH,
    fontSize,
  }
}

function addWidget(type, extra = null) {
  const cw = canvasW.value
  const ch = canvasH.value
  const id = globalThis.crypto?.randomUUID?.() || `widget-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const base = {
    id,
    type,
    name: defaultName(type),
    x: cw * 0.08,
    y: ch * 0.08,
    width: Math.min(520, cw * 0.35),
    height: Math.min(200, ch * 0.18),
    rotation: 0,
    zIndex: nextZIndex(),
    visible: true,
    content: '',
    style: {},
  }
  if (extra && typeof extra === 'object') {
    if (extra.name) base.name = extra.name
    if (extra.content != null) base.content = extra.content
    if (typeof extra.x === 'number') base.x = extra.x
    if (typeof extra.y === 'number') base.y = extra.y
    if (typeof extra.width === 'number') base.width = extra.width
    if (typeof extra.height === 'number') base.height = extra.height
    if (extra.style && typeof extra.style === 'object') {
      base.style = { ...base.style, ...extra.style }
    }
  }
  if (type === 'text') {
    base.width = Math.min(640, cw * 0.45)
    base.height = Math.min(120, ch * 0.12)
    if (!String(base.content || '').trim()) {
      base.content = t('templateEditor.sampleText')
    }
    base.style = {
      fontSize: 28,
      ...(base.style && typeof base.style === 'object' ? base.style : {}),
    }
  } else if (type === 'image') {
    base.width = Math.min(480, cw * 0.35)
    base.height = Math.min(320, ch * 0.35)
  } else if (type === 'date') {
    const m = scaledDateLikePlacement(cw, ch)
    base.x = m.x
    base.y = m.y
    base.width = m.width
    base.height = m.height
    base.content = ''
    base.style = {
      ...base.style,
      fontSize: m.fontSize,
      dateKey: base.style.dateKey || base.style.date_key || 'date_fa',
    }
    delete base.style.date_key
  } else if (type === 'weekday') {
    const m = scaledDateLikePlacement(cw, ch)
    base.x = m.x
    base.y = m.y
    base.width = m.width
    base.height = m.height
    base.content = ''
    base.style = {
      ...base.style,
      fontSize: m.fontSize,
      dateKey: base.style.dateKey || base.style.date_key || 'farsi_weekday',
    }
    delete base.style.date_key
  } else if (type === 'clock') {
    const m = scaledDateLikePlacement(cw, ch)
    base.x = m.x
    base.y = m.y
    base.width = m.width
    base.height = m.height
    if (!String(base.content || '').trim()) {
      base.content = '12:00'
    }
    base.style = {
      fontSize: m.fontSize,
      ...(base.style && typeof base.style === 'object' ? base.style : {}),
    }
  }
  widgets.value.push(base)
  clampWidgetToCanvas(base)
  selectedId.value = id
  if (FONT_AUTOSCALE_TYPES.has(type)) {
    nextTick(() => fitFontSizeToWidgetBox(base))
  }
}

async function loadPriceBindingPreviewValues() {
  const categoryId = template.value?.category
  if (categoryId == null || categoryId === '') {
    priceBindingPreviewMap.value = {}
    return
  }
  try {
    const { data } = await templateEditorApi.priceBindingsPreview({ category: categoryId })
    const rows = Array.isArray(data) ? data : []
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
    priceBindingPreviewMap.value = mapped
  } catch {
    priceBindingPreviewMap.value = {}
  }
}

async function loadCategoryPriceTypes() {
  const categoryId = template.value?.category
  if (categoryId == null || categoryId === '') {
    categoryPriceTypes.value = []
    return
  }
  try {
    const { data } = await templateEditorApi.categoryPriceTypes({ category: categoryId })
    categoryPriceTypes.value = Array.isArray(data) ? data : []
  } catch {
    categoryPriceTypes.value = []
  }
}

function onBaseImageLoad(ev) {
  const el = ev?.target
  if (!el?.naturalWidth || !template.value) return
  const nw = el.naturalWidth
  const nh = el.naturalHeight
  if (nw < 1 || nh < 1) return
  if (nw === canvasW.value && nh === canvasH.value) return
  canvasW.value = nw
  canvasH.value = nh
  const cj = template.value.config_json && typeof template.value.config_json === 'object' ? template.value.config_json : {}
  backgroundColor.value = cj.backgroundColor || backgroundColor.value
  loadWidgetsFromConfigJson(cj)
  nextTick(() => {
    fitZoom()
    refitAllTextWidgets()
  })
}

function deleteWidget(id) {
  widgets.value = widgets.value.filter((w) => w.id !== id)
  widgetEls.delete(id)
  if (selectedId.value === id) selectedId.value = null
}

function parseTransform(target) {
  const tf = target.style.transform || ''
  const tr = tf.match(/translate\(([-0-9.]+)px,\s*([-0-9.]+)px\)/)
  const rr = tf.match(/rotate\(([-0-9.]+)deg\)/)
  return {
    x: tr ? parseFloat(tr[1]) : 0,
    y: tr ? parseFloat(tr[2]) : 0,
    rotation: rr ? parseFloat(rr[1]) : 0,
  }
}

const FONT_AUTOSCALE_TYPES = new Set(['text', 'date', 'weekday', 'clock'])

function refitSelectedTextWidget() {
  const sw = selectedWidget.value
  if (sw && FONT_AUTOSCALE_TYPES.has(sw.type)) fitFontSizeToWidgetBox(sw)
}

function refitAllTextWidgets() {
  widgets.value.forEach((w) => {
    if (FONT_AUTOSCALE_TYPES.has(w.type)) fitFontSizeToWidgetBox(w)
  })
}

function syncWidgetFromTarget(target) {
  const id = target.dataset.wid
  const w = widgets.value.find((x) => x.id === id)
  if (!w) return
  const { x, y, rotation } = parseTransform(target)
  w.x = x
  w.y = y
  w.rotation = rotation
  const width = parseFloat(target.style.width)
  const height = parseFloat(target.style.height)
  if (!Number.isNaN(width) && width > 0) w.width = width
  if (!Number.isNaN(height) && height > 0) w.height = height
  clampWidgetToCanvas(w)
}

/** Resolve widget root (Moveable usually sets event.target to the :target element). */
function getMoveableDomTarget(e) {
  const t = e?.target
  if (!t) return null
  if (t.dataset?.wid) return t
  const el = typeof t.closest === 'function' ? t.closest('[data-wid]') : null
  return el || null
}

function onDrag(e) {
  const t = getMoveableDomTarget(e) || e?.target
  if (t) t.style.transform = e.transform
}

function onResize(e) {
  const target = getMoveableDomTarget(e) || e?.target
  if (!target?.dataset?.wid) return
  target.style.width = `${e.width}px`
  target.style.height = `${e.height}px`
  target.style.transform = e.drag.transform

  const id = target.dataset?.wid
  const w = id ? widgets.value.find((x) => x.id === id) : null
  if (!w || !FONT_AUTOSCALE_TYPES.has(w.type)) return
  w.width = e.width
  w.height = e.height
  fitFontSizeToWidgetBox(w)
}

function onRotate(e) {
  const t = getMoveableDomTarget(e) || e?.target
  if (t) t.style.transform = e.drag.transform
}

function onDragEnd(e) {
  const target = getMoveableDomTarget(e) || e?.target
  if (target?.dataset?.wid) syncWidgetFromTarget(target)
}

function onResizeEnd(e) {
  const target = getMoveableDomTarget(e) || e?.target
  if (target?.dataset?.wid) syncWidgetFromTarget(target)
}

function onRotateEnd(e) {
  const target = getMoveableDomTarget(e) || e?.target
  if (target?.dataset?.wid) syncWidgetFromTarget(target)
}

function loadWidgetsFromConfigJson(cj) {
  const cw = canvasW.value
  const ch = canvasH.value
  const list = Array.isArray(cj?.widgets) ? cj.widgets : []
  widgets.value = list.map((raw) => {
    const rawType = String(raw.type || 'text').trim() || 'text'
    const widgetType = rawType === 'marquee' ? 'text' : rawType
    return {
      id: String(raw.id),
      type: widgetType,
      name: raw.name || defaultName(widgetType),
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

async function save() {
  if (!template.value) return
  saveState.value = 'saving'
  try {
    const config_json = {
      backgroundColor: backgroundColor.value,
      widgets: widgetsToPercentPayload(widgets.value, canvasW.value, canvasH.value),
    }
    await templatesStore.saveConfigJsonOnly(template.value.id, {
      config_json,
      canvas_width: canvasW.value,
      canvas_height: canvasH.value,
    })
    template.value = templatesStore.current
    await Promise.all([loadPriceBindingPreviewValues(), loadCategoryPriceTypes()])
    lastSavedAt.value = new Date()
    saveState.value = 'saved'
    const categoryLabel = template.value?.category_name || (template.value?.category ? `#${template.value.category}` : t('templateEditor.noCategory'))
    toast.success(t('templateEditor.templateSaved', { category: categoryLabel }))
  } catch (e) {
    saveState.value = 'error'
    toast.error(formatDrfError(e.response?.data) || t('templateEditor.saveFailed'))
  }
}

function openBackgroundPicker() {
  backgroundFileInput.value?.click()
}

async function onBackgroundFile(ev) {
  const file = ev.target?.files?.[0]
  if (ev.target) ev.target.value = ''
  if (!file || !template.value) return
  saveState.value = 'saving'
  try {
    const imgMeta = await readImageNaturalSize(file)
    if (imgMeta.width > 0 && imgMeta.height > 0) {
      canvasW.value = imgMeta.width
      canvasH.value = imgMeta.height
      widgets.value.forEach((w) => clampWidgetToCanvas(w))
    }
    const fd = new FormData()
    fd.append('image', file)
    const { data: updated } = await templateEditorApi.patch(template.value.id, fd)
    template.value = updated
    templatesStore.current = updated
    saveState.value = 'saved'
    lastSavedAt.value = new Date()
    nextTick(() => fitZoom())
    toast.success(t('templateEditor.backgroundUploaded'))
  } catch (e) {
    saveState.value = 'error'
    const msg = e?.response?.data ? formatDrfError(e.response.data) : (e?.message || t('templateEditor.backgroundUploadFailed'))
    toast.error(msg)
  }
}

function readImageNaturalSize(source) {
  return new Promise((resolve) => {
    const img = new Image()
    let objectUrl = ''
    if (source instanceof File) objectUrl = URL.createObjectURL(source)
    img.onload = () => {
      resolve({ width: img.naturalWidth || 0, height: img.naturalHeight || 0 })
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
    img.onerror = () => {
      resolve({ width: 0, height: 0 })
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
    img.src = objectUrl || source
  })
}

function zoomIn() {
  scale.value = Math.min(2, Math.round((scale.value + 0.05) * 100) / 100)
}
function zoomOut() {
  scale.value = Math.max(0.1, Math.round((scale.value - 0.05) * 100) / 100)
}
function fitZoom() {
  const el = viewportRef.value
  if (!el) return
  const pad = 12
  const rw = (el.clientWidth - pad) / canvasW.value
  const rh = (el.clientHeight - pad) / canvasH.value
  scale.value = Math.max(0.1, Math.min(2, Math.min(rw, rh)))
}

watch([canvasW, canvasH], () => {
  nextTick(() => fitZoom())
})

watch(
  [widgets, backgroundColor, canvasW, canvasH, () => template.value?.name],
  () => {
    if (!hasLoadedOnce.value) return
    if (isSaving.value) return
    if (saveState.value === 'saved') saveState.value = 'dirty'
  },
  { deep: true }
)

watch(selectedId, () => {
  nextTick(() => {})
})

watch(
  () => template.value?.category,
  () => {
    loadPriceBindingPreviewValues()
    loadCategoryPriceTypes()
  }
)

provideTemplateEditor({
  widgets,
  selectedId,
  selectedWidget,
  canvasWidth: canvasW,
  canvasHeight: canvasH,
  addWidget,
  openBackgroundPicker,
  deleteWidget,
  selectWidget,
  refitSelectedWidget: refitSelectedTextWidget,
  template,
  priceBindingPreviewMap,
  categoryPriceTypes,
  backgroundColor,
  saveState,
  backgroundImageContentRect,
  alignSelectedToBackgroundEdge,
})

onMounted(async () => {
  const id = route.params.id
  if (!id) {
    loadError.value = 'Missing template id'
    loading.value = false
    return
  }
  try {
    const data = await templatesStore.fetchTemplate(id)
    template.value = data
    canvasW.value = Number(data.canvas_width) || 1920
    canvasH.value = Number(data.canvas_height) || 1080
    const cj = data.config_json && typeof data.config_json === 'object' ? data.config_json : {}
    backgroundColor.value = cj.backgroundColor || '#ffffff'
    loadWidgetsFromConfigJson(cj)
    await Promise.all([loadPriceBindingPreviewValues(), loadCategoryPriceTypes()])
    nextTick(() => {
      fitZoom()
      refitAllTextWidgets()
    })
    try {
      const { data } = await templateEditorApi.fonts()
      injectTemplateEditorFontFaces(Array.isArray(data) ? data : [])
    } catch {
      /* preview falls back to system fonts */
    }
    if (viewportRef.value) {
      ro = new ResizeObserver(() => fitZoom())
      ro.observe(viewportRef.value)
    }
    hasLoadedOnce.value = true
    saveState.value = 'saved'
  } catch (e) {
    loadError.value = e?.response?.data?.detail || t('templateEditor.failedToLoadTemplate')
  } finally {
    loading.value = false
  }
})

let ro = null
onBeforeUnmount(() => {
  ro?.disconnect()
  ro = null
  widgetEls.clear()
})
</script>

<style scoped>
/*
 * Moveable sits after the canvas in DOM order (always painted on top). Forcing pointer-events:auto on it
 * made the whole layer capture clicks so widgets underneath could not be selected.
 * Root ignores hits; interactive descendants (handles/lines) still receive events per Moveable CSS.
 */
.template-editor-moveable {
  pointer-events: none;
}
</style>
