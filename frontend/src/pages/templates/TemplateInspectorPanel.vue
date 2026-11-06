<template>
  <aside class="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto rounded-xl border border-[var(--border-card)] bg-[var(--bg-card)] p-3 text-sm">
    <h2 class="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">{{ $t('templateEditor.inspector') }}</h2>

    <template v-if="!w">
      <div class="space-y-2 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)]/45 p-3">
        <p class="text-xs font-semibold text-[var(--text-primary)]">{{ $t('templateEditor.templateSettings') }}</p>
        <div class="space-y-1.5">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.templateName') }}</label>
          <input v-model="templateName" type="text" class="input-luxury w-full text-sm" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div class="space-y-1.5">
            <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.width') }}</label>
            <input v-model.number="canvasWidthValue" type="number" min="320" max="4096" class="input-luxury w-full text-sm" />
          </div>
          <div class="space-y-1.5">
            <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.height') }}</label>
            <input v-model.number="canvasHeightValue" type="number" min="320" max="4096" class="input-luxury w-full text-sm" />
          </div>
        </div>
        <div class="grid grid-cols-[1fr_auto] gap-2">
          <div class="space-y-1.5">
            <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.canvasBackground') }}</label>
            <input v-model="canvasBgColor" type="text" class="input-luxury w-full text-sm font-mono" placeholder="#ffffff" />
          </div>
          <div class="space-y-1.5">
            <label class="block text-xs text-transparent">.</label>
            <input v-model="canvasBgColor" type="color" class="h-10 w-full min-w-[2.75rem] cursor-pointer rounded border border-[var(--border-card)] bg-transparent p-0" />
          </div>
        </div>
        <button
          type="button"
          class="btn-luxury-outline flex w-full items-center justify-center gap-2 py-2 text-xs"
          @click="te.openBackgroundPicker?.()"
        >
          <i class="fas fa-image" />
          {{ $t('templateEditor.uploadBackgroundImage') }}
        </button>
      </div>
      <p class="text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.selectWidgetHint') }}</p>
    </template>

    <template v-else>
      <div class="grid grid-cols-3 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)]/55 p-1">
        <button
          v-for="tab in inspectorTabs"
          :key="tab.id"
          type="button"
          class="rounded-md px-2 py-1.5 text-xs font-medium transition-colors"
          :class="activeTab === tab.id ? 'bg-[var(--bg-card)] text-[var(--primary)] shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="space-y-2">
        <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.name') }}</label>
        <input v-model="w.name" type="text" class="input-luxury w-full text-sm" />
      </div>

      <div class="space-y-2">
        <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.type') }}</label>
        <input :value="w.type" type="text" class="input-luxury w-full text-sm opacity-70" disabled />
      </div>

      <div v-if="activeTab === 'data' && w.type === 'text'" class="space-y-2">
        <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.priceTypeBinding') }}</label>
        <select v-model="selectedPriceTypeId" class="input-luxury w-full text-sm" @change="refitSelectedAfterTick">
          <option :value="''">{{ $t('templateEditor.selectPriceType') }}</option>
          <option v-for="pt in categoryPriceTypeOptions" :key="pt.id" :value="String(pt.id)">
            {{ pt.name }}
          </option>
        </select>
        <p v-if="linkedPriceTypeId != null" class="text-[10px] text-[var(--text-secondary)]">{{ $t('templateEditor.stableKey') }}<span class="font-mono text-[var(--text-primary)]">price_type__{{ linkedPriceTypeId }}</span>
        </p>
        <div
          v-if="showPriceDigitLocale"
          class="flex flex-col gap-2 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)]/40 p-2"
        >
          <span class="text-[10px] font-medium text-[var(--text-secondary)]">{{ $t('templateEditor.priceDigitLocale') }}</span>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-lg border px-3 py-2 text-xs font-medium transition-colors min-h-[40px]"
              :class="priceDigitLocale === 'en'
                ? 'border-[var(--primary)] bg-[var(--primary-muted)] text-[var(--primary)]'
                : 'border-[var(--border-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'"
              @click="priceDigitLocale = 'en'"
            >
              {{ $t('templateEditor.priceDigitsEnglish') }}
            </button>
            <button
              type="button"
              class="rounded-lg border px-3 py-2 text-xs font-medium transition-colors min-h-[40px]"
              :class="priceDigitLocale === 'fa'
                ? 'border-[var(--primary)] bg-[var(--primary-muted)] text-[var(--primary)]'
                : 'border-[var(--border-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'"
              @click="priceDigitLocale = 'fa'"
            >
              {{ $t('templateEditor.priceDigitsPersian') }}
            </button>
          </div>
          <p class="text-[10px] leading-snug text-[var(--text-secondary)]">{{ $t('templateEditor.priceDigitLocaleHint') }}</p>
        </div>
        <div
          v-if="bindingPreviewInfo"
          class="rounded border border-[var(--border-card)] bg-[var(--bg-input)]/40 px-2 py-1.5 text-[10px] text-[var(--text-secondary)]"
        >{{ $t('templateEditor.previewSource') }}<span class="font-semibold text-[var(--text-primary)]">{{ bindingPreviewInfo.sourceLabel }}</span>
          <span v-if="bindingPreviewDisplayValue">
            {{ $t('templateEditor.previewValue') }}
            <span class="font-mono text-[var(--text-primary)]">{{ bindingPreviewDisplayValue }}</span>
          </span>
        </div>
        <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.fallbackValue') }}</label>
        <textarea v-model="w.content" rows="3" class="input-luxury w-full text-sm font-mono" @blur="refitSelectedAfterTick" />
      </div>

      <div v-if="activeTab === 'data' && (w.type === 'date' || w.type === 'weekday')" class="space-y-2">
        <label class="block text-xs text-[var(--text-secondary)]">
          {{ w.type === 'weekday' ? $t('templateEditor.weekdaySource') : $t('templateEditor.dateSource') }}
        </label>
        <select v-model="dateKey" class="input-luxury w-full text-sm" @change="refitSelectedAfterTick">
          <option v-for="k in datePresetKeyList" :key="k" :value="k">
            {{ presetLabel(k) }}
          </option>
        </select>
        <p class="text-[10px] leading-snug text-[var(--text-secondary)]">
          {{ $t('templateEditor.dateSourceHelp') }}
        </p>
      </div>

      <div v-if="activeTab === 'data' && w.type === 'clock'" class="space-y-2">
        <p class="text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.clockSource') }}</p>
      </div>

      <div v-if="activeTab === 'typography' && isTextLikeWidget" class="space-y-3 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)]/40 p-2">
        <p class="text-xs font-semibold text-[var(--text-primary)]">{{ $t('templateEditor.typography') }}</p>
        <div class="space-y-2">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.fontSize') }}</label>
          <input v-model.number="styleFontSize" type="number" min="1" max="200" step="1" class="input-luxury w-full text-sm" />
        </div>
        <div class="grid grid-cols-[1fr_auto] gap-2">
          <div class="space-y-2">
            <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.textColor') }}</label>
            <input v-model="styleColorHex" type="text" class="input-luxury w-full text-sm font-mono" placeholder="#ffffff" />
          </div>
          <div class="space-y-2">
            <label class="block text-xs text-transparent">.</label>
            <input v-model="styleColorHex" type="color" class="h-10 w-full min-w-[2.75rem] cursor-pointer rounded border border-[var(--border-card)] bg-transparent p-0" :title="$t('templateEditor.pickColor')" />
          </div>
        </div>
        <div class="space-y-2">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.fontFile') }}</label>
          <select v-model="styleFontFile" class="input-luxury w-full text-sm" @change="refitSelectedAfterTick">
            <option value="">{{ $t('templateEditor.fontDefault') }}</option>
            <option v-for="f in fontsList" :key="f.filename" :value="f.filename">
              {{ f.display_name || f.filename }}
            </option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.alignLabel') }}</label>
          <select v-model="styleAlign" class="input-luxury w-full text-sm" @change="refitSelectedAfterTick">
            <option value="left">{{ $t('templateEditor.alignLeft') }}</option>
            <option value="center">{{ $t('templateEditor.alignCenter') }}</option>
            <option value="right">{{ $t('templateEditor.alignRight') }}</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.verticalAlign') }}</label>
          <select v-model="styleVerticalAlign" class="input-luxury w-full text-sm" @change="refitSelectedAfterTick">
            <option value="middle">{{ $t('templateEditor.alignMiddle') }}</option>
            <option value="top">Top</option>
            <option value="bottom">{{ $t('templateEditor.alignBottom') }}</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.weight') }}</label>
          <select v-model="styleFontWeight" class="input-luxury w-full text-sm" @change="refitSelectedAfterTick">
            <option value="normal">{{ $t('templateEditor.weightNormal') }}</option>
            <option value="bold">{{ $t('templateEditor.weightBold') }}</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.lineHeight') }}</label>
          <input
            v-model="styleLineHeight"
            type="text"
            class="input-luxury w-full text-sm"
            placeholder="e.g. 1.2 or 32"
            @blur="refitSelectedAfterTick"
          />
        </div>
        <BaseCheckbox v-model="stylePlainText">{{ $t('templateEditor.plainOnExport') }}</BaseCheckbox>
        <template v-if="!stylePlainText">
          <BaseCheckbox v-model="styleShadowEnabled">{{ $t('templateEditor.dropShadow') }}</BaseCheckbox>
          <BaseCheckbox v-model="styleOutlineEnabled">{{ $t('templateEditor.textOutline') }}</BaseCheckbox>
        </template>
      </div>

      <div
        v-if="activeTab === 'appearance' && canAlignWidgetToBackground"
        class="space-y-2 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)]/40 p-2"
      >
        <p class="text-xs font-semibold text-[var(--text-primary)]">{{ $t('templateEditor.snapToBackground') }}</p>
        <p class="text-[10px] leading-snug text-[var(--text-secondary)]">
          Moves the widget box to the edges of the visible image (letterboxing excluded).
        </p>
        <div class="grid grid-cols-3 gap-1">
          <button type="button" class="btn-luxury-outline py-1.5 text-[10px]" @click="alignWidgetToBackground('left')">{{ $t('templateEditor.alignLeft') }}</button>
          <button type="button" class="btn-luxury-outline py-1.5 text-[10px]" @click="alignWidgetToBackground('center-h')">H mid</button>
          <button type="button" class="btn-luxury-outline py-1.5 text-[10px]" @click="alignWidgetToBackground('right')">{{ $t('templateEditor.alignRight') }}</button>
          <button type="button" class="btn-luxury-outline py-1.5 text-[10px]" @click="alignWidgetToBackground('top')">Top</button>
          <button type="button" class="btn-luxury-outline py-1.5 text-[10px]" @click="alignWidgetToBackground('center-v')">V mid</button>
          <button type="button" class="btn-luxury-outline py-1.5 text-[10px]" @click="alignWidgetToBackground('bottom')">{{ $t('templateEditor.alignBottom') }}</button>
        </div>
      </div>

      <div v-if="activeTab === 'appearance' && w.type === 'image'" class="space-y-2">
        <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.imageUrl') }}</label>
        <input v-model="w.content" type="url" class="input-luxury w-full text-sm" placeholder="https://… or /media/…" />
        <input ref="imageFileInput" type="file" accept="image/jpeg,image/png,image/gif,image/webp" class="hidden" @change="onImageFile" />
        <button
          type="button"
          class="btn-luxury-outline flex w-full items-center justify-center gap-2 py-2 text-xs"
          :disabled="uploading"
          @click="openImagePicker"
        >
          <i class="fas fa-cloud-upload-alt" />
          {{ uploading ? 'Uploading…' : 'Upload image' }}
        </button>
        <router-link
          to="/templates/media"
          target="_blank"
          rel="noopener noreferrer"
          class="block text-center text-[10px] text-[var(--primary)] underline-offset-2 hover:underline"
        >{{ $t('templateEditor.openMediaLibrary') }}</router-link>
      </div>

      <div v-if="activeTab === 'appearance'" class="space-y-2">
        <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.opacityLabel') }}</label>
        <input v-model.number="styleOpacity" type="range" min="0" max="1" step="0.01" class="w-full accent-[var(--primary)]" />
        <div class="text-right text-[10px] tabular-nums text-[var(--text-secondary)]">{{ Math.round(styleOpacity * 100) }}%</div>
      </div>

      <div
        v-if="activeTab === 'appearance' && isTextLikeWidget"
        class="space-y-1 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)]/40 p-2"
      >
        <BaseSwitch v-model="styleUseArabicReshaper" :label="$t('templateEditor.arabicShapingLabel')" />
        <p class="text-[10px] leading-snug text-[var(--text-secondary)]">
          {{ $t('templateEditor.arabicShapingHelp') }}
        </p>
      </div>

      <div v-if="activeTab === 'appearance'" class="grid grid-cols-2 gap-2">
        <div>
          <label class="block text-xs text-[var(--text-secondary)]">z-index</label>
          <input v-model.number="w.zIndex" type="number" class="input-luxury w-full text-sm" />
        </div>
        <div>
          <label class="block text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.rotation') }}</label>
          <input v-model.number="w.rotation" type="number" class="input-luxury w-full text-sm" />
        </div>
      </div>

      <button
        type="button"
        class="btn-luxury-outline w-full py-2 text-xs text-red-600 dark:text-red-300"
        @click="te.deleteWidget(w.id)"
      >{{ $t('templateEditor.deleteWidget') }}</button>
    </template>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { formatDrfError, templateEditorApi } from '@/services/api'
import { useTemplateEditorInjected } from './templateEditorInjectionKey.js'
import { injectTemplateEditorFontFaces } from './templateEditorFonts.js'
import { DATE_WIDGET_DATE_KEYS, WEEKDAY_WIDGET_KEYS } from './dateWidgetPresets.js'
import BaseCheckbox from '@/components/ui/BaseCheckbox.vue'
import BaseSwitch from '@/components/ui/BaseSwitch.vue'
import { toPersianDigits } from '@/utils/persianDigits.js'

/** Range for widget font size in px. Do not use min 8 in v-model clamping — it turned "2" into 8 and "22" into 82 while typing. */
const FONT_SIZE_MIN = 1
const FONT_SIZE_MAX = 200

const { t } = useI18n()
const te = useTemplateEditorInjected()
const toast = useToast()

function refitSelectedAfterTick() {
  nextTick(() => {
    te.refitSelectedWidget?.()
  })
}
const imageFileInput = ref(null)
const uploading = ref(false)
const fontsList = ref([])

const w = computed(() => te.selectedWidget?.value ?? null)
const activeTab = ref('appearance')
const inspectorTabs = [
  { id: 'appearance', label: 'Appearance' },
  { id: 'typography', label: 'Font' },
  { id: 'data', label: 'Data' },
]

const isTextLikeWidget = computed(() => {
  const ty = w.value?.type
  return ['text', 'date', 'weekday', 'clock'].includes(ty)
})
const templateName = computed({
  get() {
    return te.template?.value?.name || ''
  },
  set(v) {
    if (!te.template?.value) return
    te.template.value.name = v
  },
})

const canvasWidthValue = computed({
  get() {
    return Number(te.canvasWidth?.value) || 1920
  },
  set(v) {
    if (!te.canvasWidth) return
    te.canvasWidth.value = Math.min(4096, Math.max(320, Number(v) || 1920))
  },
})
const canvasHeightValue = computed({
  get() {
    return Number(te.canvasHeight?.value) || 1080
  },
  set(v) {
    if (!te.canvasHeight) return
    te.canvasHeight.value = Math.min(4096, Math.max(320, Number(v) || 1080))
  },
})
const canvasBgColor = computed({
  get() {
    return te.backgroundColor?.value || '#ffffff'
  },
  set(v) {
    if (!te.backgroundColor) return
    let s = String(v || '').trim()
    if (!s.startsWith('#')) s = `#${s}`
    te.backgroundColor.value = /^#[0-9A-Fa-f]{6}$/i.test(s) || /^#[0-9A-Fa-f]{3}$/i.test(s) ? s : '#ffffff'
  },
})

const datePresetKeyList = computed(() => {
  const sw = w.value
  if (!sw) return DATE_WIDGET_DATE_KEYS
  if (sw.type === 'weekday') return WEEKDAY_WIDGET_KEYS
  return DATE_WIDGET_DATE_KEYS
})

function presetLabel(key) {
  const sw = w.value
  const map = sw?.type === 'weekday' ? 'weekdayFormats' : 'dateFormats'
  const path = `templateEditor.${map}.${key}`
  const translated = t(path)
  return translated === path ? key : translated
}

onMounted(async () => {
  try {
    const { data } = await templateEditorApi.fonts()
    fontsList.value = Array.isArray(data) ? data : []
    injectTemplateEditorFontFaces(fontsList.value)
  } catch {
    fontsList.value = []
  }
})

function openImagePicker() {
  imageFileInput.value?.click()
}

async function onImageFile(ev) {
  const file = ev.target?.files?.[0]
  if (ev.target) ev.target.value = ''
  const sw = w.value
  if (!file || !sw) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await templateEditorApi.uploadMedia(fd)
    const url = data?.url
    if (url) sw.content = typeof url === 'string' ? url : ''
    toast.success(t('templateEditor.imageUploaded'))
  } catch (e) {
    toast.error(formatDrfError(e.response?.data))
  } finally {
    uploading.value = false
  }
}

function isPriceLikeBindingKey(raw) {
  const bk = String(raw || '').trim().toLowerCase()
  if (!bk) return false
  if (bk === 'price') return true
  const prefixes = [
    'price__',
    'price_type__',
    'price_buy__',
    'price_sell__',
    'price_buy_',
    'price_sell_',
    'tether_buy_',
    'tether_sell_',
  ]
  return prefixes.some((p) => bk.startsWith(p))
}

const linkedPriceTypeId = computed(() => {
  const sw = w.value
  if (!sw || sw.type !== 'text') return null
  const raw = sw.style?.priceTypeId ?? sw.style?.price_type_id
  if (raw == null || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const showPriceDigitLocale = computed(() => {
  const sw = w.value
  if (!sw || sw.type !== 'text') return false
  if (linkedPriceTypeId.value != null) return true
  const bk = sw.style?.bindingKey ?? sw.style?.binding_key
  return isPriceLikeBindingKey(bk)
})

const priceDigitLocale = computed({
  get() {
    const raw = w.value?.style?.priceLocale ?? w.value?.style?.price_locale ?? 'en'
    const s = String(raw).toLowerCase()
    return s === 'fa' || s === 'fas' ? 'fa' : 'en'
  },
  set(v) {
    const sw = w.value
    if (!sw || !sw.style || typeof sw.style !== 'object') return
    const loc = v === 'fa' ? 'fa' : 'en'
    if (loc === 'en') {
      delete sw.style.priceLocale
      delete sw.style.price_locale
    } else {
      sw.style.priceLocale = 'fa'
      delete sw.style.price_locale
    }
    refitSelectedAfterTick()
  },
})

const categoryPriceTypeOptions = computed(() => {
  const rows = te.categoryPriceTypes?.value
  return Array.isArray(rows) ? rows : []
})

const selectedPriceTypeId = computed({
  get() {
    const id = linkedPriceTypeId.value
    return id == null ? '' : String(id)
  },
  set(v) {
    const sw = w.value
    if (!sw) return
    if (!sw.style || typeof sw.style !== 'object') sw.style = {}
    const normalized = String(v || '').trim()
    if (!normalized) {
      delete sw.style.priceTypeId
      delete sw.style.price_type_id
      delete sw.style.bindingKey
      delete sw.style.binding_key
      delete sw.style.priceLocale
      delete sw.style.price_locale
      return
    }
    const idNum = Number(normalized)
    if (!Number.isFinite(idNum)) return
    sw.style.priceTypeId = idNum
    sw.style.bindingKey = `price_type__${idNum}`
    delete sw.style.price_type_id
    delete sw.style.binding_key
    const preview = String(te.priceBindingPreviewMap?.value?.[`price_type__${idNum}`]?.value || '').trim()
    if (preview) {
      sw.content = preview
    }
  },
})

const bindingPreviewInfo = computed(() => {
  const sw = w.value
  if (!sw || sw.type !== 'text') return null
  const pt = linkedPriceTypeId.value
  let row = null
  if (pt != null) {
    row = te.priceBindingPreviewMap?.value?.[`price_type__${pt}`] || null
  }
  if (!row) {
    const key = String(sw.style?.bindingKey || sw.style?.binding_key || '').trim()
    if (!key) return null
    row = te.priceBindingPreviewMap?.value?.[key]
  }
  if (!row) return null
  const source = String(row?.source || '').trim()
  const sourceLabel = source === 'finalized'
    ? 'Latest finalized'
    : source === 'latest'
      ? 'Latest submitted'
      : 'Fallback only'
  return {
    sourceLabel,
    value: row?.value != null ? String(row.value) : '',
  }
})

const bindingPreviewDisplayValue = computed(() => {
  const raw = bindingPreviewInfo.value?.value
  if (raw == null || raw === '') return ''
  if (priceDigitLocale.value !== 'fa' || !showPriceDigitLocale.value) return String(raw)
  return toPersianDigits(String(raw))
})

const dateKey = computed({
  get() {
    const sw = w.value
    if (!sw) return 'date_fa'
    const raw = sw.style?.dateKey || sw.style?.date_key
    const fallback = sw.type === 'weekday' ? 'farsi_weekday' : 'date_fa'
    const k = String(raw || '').trim() || fallback
    const allowed = sw.type === 'weekday' ? WEEKDAY_WIDGET_KEYS : DATE_WIDGET_DATE_KEYS
    return allowed.includes(k) ? k : fallback
  },
  set(v) {
    const sw = w.value
    if (!sw) return
    if (!sw.style || typeof sw.style !== 'object') sw.style = {}
    const allowed = sw.type === 'weekday' ? WEEKDAY_WIDGET_KEYS : DATE_WIDGET_DATE_KEYS
    const fallback = sw.type === 'weekday' ? 'farsi_weekday' : 'date_fa'
    const s = String(v || '').trim()
    sw.style.dateKey = allowed.includes(s) ? s : fallback
    delete sw.style.date_key
  },
})

function ensureStyle() {
  const sw = w.value
  if (!sw) return null
  if (!sw.style || typeof sw.style !== 'object') sw.style = {}
  return sw.style
}

const styleFontSize = computed({
  get() {
    const s = w.value?.style
    const n = Number(s?.fontSize ?? s?.font_size ?? 24)
    if (!Number.isFinite(n)) return 24
    return Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, n))
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    const num = typeof v === 'number' ? v : Number(v)
    if (!Number.isFinite(num)) return
    st.fontSize = Math.min(FONT_SIZE_MAX, Math.max(FONT_SIZE_MIN, num))
    delete st.font_size
  },
})

const styleColorHex = computed({
  get() {
    const c = w.value?.style?.color
    if (typeof c === 'string' && /^#[0-9A-Fa-f]{6}$/.test(c)) return c
    if (typeof c === 'string' && /^#[0-9A-Fa-f]{3}$/.test(c)) return c
    return '#ffffff'
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    let s = String(v || '').trim()
    if (!s.startsWith('#')) s = `#${s}`
    if (/^#[0-9A-Fa-f]{3}$/.test(s) || /^#[0-9A-Fa-f]{6}$/i.test(s)) st.color = s
    else st.color = '#ffffff'
  },
})

const styleFontFile = computed({
  get() {
    const s = w.value?.style
    return s?.font || s?.fontFilename || s?.font_filename || ''
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    const s = String(v || '').trim()
    if (!s) {
      delete st.font
      delete st.fontFilename
      delete st.font_filename
      return
    }
    st.font = s
    delete st.fontFilename
    delete st.font_filename
    // Drop legacy inline family so preview & PNG use the @font-face from this file.
    delete st.fontFamily
    delete st.font_family
  },
})

const styleAlign = computed({
  get() {
    const a = String(w.value?.style?.align || 'center').toLowerCase()
    if (a === 'left' || a === 'start') return 'left'
    if (a === 'right' || a === 'end') return 'right'
    return 'center'
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    st.align = v || 'center'
  },
})

const styleUseArabicReshaper = computed({
  get() {
    const s = w.value?.style
    const v = s?.useArabicReshaper ?? s?.use_arabic_reshaper
    if (v === false) return false
    if (v === true) return true
    return true
  },
  set(val) {
    const st = ensureStyle()
    if (!st) return
    st.useArabicReshaper = Boolean(val)
    delete st.use_arabic_reshaper
    refitSelectedAfterTick()
  },
})

const canAlignWidgetToBackground = computed(() =>
  Boolean(te.template?.value?.image && te.backgroundImageContentRect?.value),
)

function alignWidgetToBackground(edge) {
  te.alignSelectedToBackgroundEdge?.(edge)
  refitSelectedAfterTick()
}

const styleVerticalAlign = computed({
  get() {
    const a = String(w.value?.style?.verticalAlign ?? w.value?.style?.vertical_align ?? 'middle').toLowerCase()
    if (a === 'top' || a === 'start') return 'top'
    if (a === 'bottom' || a === 'end') return 'bottom'
    return 'middle'
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    const val = v === 'top' || v === 'bottom' ? v : 'middle'
    st.verticalAlign = val
    delete st.vertical_align
  },
})

const styleFontWeight = computed({
  get() {
    const fw = w.value?.style?.fontWeight || w.value?.style?.weight
    if (fw === 'bold' || fw === 700 || fw === '700') return 'bold'
    return 'normal'
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    st.fontWeight = v === 'bold' ? 'bold' : 'normal'
    delete st.weight
  },
})

const styleLineHeight = computed({
  get() {
    const s = w.value?.style
    if (s?.lineHeight != null && s.lineHeight !== '') return String(s.lineHeight)
    if (s?.line_height != null && s.line_height !== '') return String(s.line_height)
    return ''
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    const s = String(v || '').trim()
    if (!s) {
      delete st.lineHeight
      delete st.line_height
      return
    }
    st.lineHeight = s
    delete st.line_height
  },
})

const stylePlainText = computed({
  get() {
    return w.value?.style?.plainText === true || w.value?.style?.plain_text === true
  },
  set(on) {
    const st = ensureStyle()
    if (!st) return
    if (on) {
      st.plainText = true
      delete st.plain_text
    } else {
      delete st.plainText
      delete st.plain_text
    }
  },
})

const styleShadowEnabled = computed({
  get() {
    if (w.value?.style?.plainText || w.value?.style?.plain_text) return false
    const ts = w.value?.style?.textShadow
    if (ts === false || ts === 0) return false
    return true
  },
  set(on) {
    const st = ensureStyle()
    if (!st) return
    if (on) delete st.textShadow
    else st.textShadow = false
  },
})

const styleOutlineEnabled = computed({
  get() {
    if (w.value?.style?.plainText || w.value?.style?.plain_text) return false
    const o = w.value?.style?.textOutline
    if (o === false) return false
    return true
  },
  set(on) {
    const st = ensureStyle()
    if (!st) return
    if (on) delete st.textOutline
    else st.textOutline = false
  },
})

const styleOpacity = computed({
  get() {
    const o = w.value?.style?.opacity
    const n = o != null && o !== '' ? Number(o) : 1
    return Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 1
  },
  set(v) {
    const st = ensureStyle()
    if (!st) return
    const n = Math.min(1, Math.max(0, Number(v)))
    if (n >= 0.999) delete st.opacity
    else st.opacity = n
  },
})

</script>
