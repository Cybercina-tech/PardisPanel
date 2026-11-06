<template>
  <div>
    <nav v-if="!embedded" class="mb-6">
      <router-link
        :to="'/categories'"
        class="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-gold transition-colors font-medium"
      >
        <i class="fas" :class="isRtl ? 'fa-arrow-right' : 'fa-arrow-left'" />
        <span>{{ $t('telegramStudio.backToCategories') || 'Back to Categories' }}</span>
      </router-link>
    </nav>

    <div v-if="loading" class="card-luxury p-8 flex items-center justify-center min-h-[200px]">
      <LoadingSpinner class="w-10 h-10 text-gold" />
    </div>

    <template v-else-if="category">
      <h1 v-if="!embedded" class="text-2xl font-bold text-gold mb-2 animate-fade-in-up">
        {{ $t('telegramStudio.title') || 'Telegram Message Studio' }}
      </h1>
      <p class="text-[var(--text-secondary)] mb-6">
        {{ category.name }}
      </p>

      <!-- Template media warning -->
      <div
        v-if="isIncomplete"
        class="mb-6 rounded-xl border px-4 py-3 text-sm flex items-center gap-2 border-[var(--border-card-hover)] bg-primary-muted text-[var(--text-primary)]"
      >
        <i class="fas fa-exclamation-triangle shrink-0 text-gold" />
        <span>{{ $t('telegramStudio.incompleteMessage') || 'No active template media found. Preview is unavailable until a template image is set.' }}</span>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 items-start">
        <!-- Left: Form sections (first on mobile) -->
        <div class="space-y-6 animate-fade-in-up order-1 lg:order-1">
          <!-- Section 1: Media -->
          <section class="card-luxury overflow-hidden">
            <div
              class="flex items-center gap-3 pb-4 mb-4 border-b"
              style="border-color: var(--border-card);"
            >
              <span
                class="flex items-center justify-center w-10 h-10 rounded-xl shrink-0 bg-primary-muted text-[var(--primary)]"
              >
                <i class="fas fa-image" />
              </span>
              <h2 class="text-lg font-semibold text-gold m-0">
                {{ $t('telegramStudio.media') || 'Media' }}
              </h2>
            </div>
            <div class="flex flex-col sm:flex-row gap-4 items-start">
              <div
                class="w-full sm:w-52 h-36 rounded-xl border-2 border-dashed flex items-center justify-center overflow-hidden p-2"
                style="border-color: var(--border-card); background: var(--bg-input);"
              >
                <img
                  v-if="templateMediaUrl"
                  :src="templateMediaUrl"
                  alt=""
                  class="w-full h-full object-contain rounded-lg"
                />
                <span v-else class="text-sm text-[var(--text-secondary)] px-2 text-center">
                  {{ $t('telegramStudio.uploadImage') || 'No template media' }}
                </span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-[var(--text-secondary)] mb-2">
                  {{ $t('telegramStudio.mediaHint') || 'Media is inherited from the active Template Editor template.' }}
                </p>
                <p v-if="category.last_used_template" class="text-xs text-[var(--text-secondary)]">
                  {{ $t('telegramStudio.templateMediaHint') || 'Template ID:' }} {{ category.last_used_template }}
                </p>
              </div>
            </div>
          </section>

          <!-- Section 2: Description -->
          <section class="card-luxury overflow-visible">
            <div
              class="flex items-center justify-between gap-2 flex-wrap pb-4 mb-4 border-b"
              style="border-color: var(--border-card);"
            >
              <div class="flex items-center gap-3">
                <span
                  class="flex items-center justify-center w-10 h-10 rounded-xl shrink-0 bg-primary-muted text-[var(--primary)]"
                >
                  <i class="fas fa-align-left" />
                </span>
                <h2 class="text-lg font-semibold text-gold m-0">
                  {{ $t('telegramStudio.description') || 'Description' }}
                </h2>
              </div>
              <div class="relative">
                <button
                  ref="variableTriggerRef"
                  type="button"
                  class="btn-luxury-outline text-sm py-1.5 px-3 gap-1"
                  :title="$t('telegramStudio.insertVariable') || 'Insert variable'"
                  aria-haspopup="menu"
                  :aria-expanded="showVariableMenu ? 'true' : 'false'"
                  @click="toggleVariableMenu"
                >
                  <i class="fas fa-braces" />
                  <span class="hidden sm:inline">{{ $t('telegramStudio.insertVariable') || 'Insert variable' }}</span>
                </button>
                <!-- Teleported: the editor column clips its overflow, which cut
                     this menu off a few rows in. -->
                <Teleport to="body">
                <div
                  v-if="showVariableMenu"
                  ref="variablePanelRef"
                  class="dropdown-panel !py-2 overflow-y-auto overscroll-contain"
                  :style="variablePanelStyle"
                  role="menu"
                >
                  <p class="px-3 py-1 text-xs text-[var(--text-secondary)]">
                    {{ $t('telegramStudio.commonVariables') || 'Common variables' }}
                  </p>
                  <button
                    v-for="v in staticVariables"
                    :key="v.key"
                    type="button"
                    class="w-full text-start px-3 py-2 text-sm transition-colors hover:bg-[var(--bg-hover)]"
                    style="color: var(--text-primary);"
                    @click="insertVariable(v.key)"
                  >
                    {{ v.label }} — <code class="text-gold">{{ variableCode({ slug: v.key, name: v.key }) }}</code>
                  </button>
                  <p class="px-3 py-1 text-xs text-[var(--text-secondary)]">
                    {{ $t('telegramStudio.priceTypes') || 'Price types' }}
                  </p>
                  <button
                    v-for="pt in (category.price_types || [])"
                    :key="pt.id"
                    type="button"
                    class="w-full text-start px-3 py-2 text-sm transition-colors hover:bg-[var(--bg-hover)]"
                    style="color: var(--text-primary);"
                    @click="insertVariable(pt.slug || pt.name)"
                  >
                    {{ pt.name }} — <code class="text-gold">{{ variableCode(pt) }}</code>
                  </button>
                  <p v-if="!(category.price_types || []).length" class="px-3 py-2 text-sm text-[var(--text-secondary)]">
                    {{ $t('telegramStudio.noPriceTypes') || 'No price types in this category.' }}
                  </p>
                </div>
                </Teleport>
              </div>
            </div>
            <textarea
              ref="descriptionTextarea"
              v-model="form.telegram_message_description"
              class="input-luxury min-h-[120px] resize-y"
              :placeholder="$t('telegramStudio.descriptionPlaceholder') || 'Message text under the image…'"
            />
          </section>

          <!-- Section 3: Inline Buttons -->
          <section class="card-luxury overflow-hidden">
            <div
              class="flex items-center gap-3 pb-4 mb-4 border-b"
              style="border-color: var(--border-card);"
            >
              <span
                class="flex items-center justify-center w-10 h-10 rounded-xl shrink-0 bg-primary-muted text-[var(--primary)]"
              >
                <i class="fas fa-th-large" />
              </span>
              <h2 class="text-lg font-semibold text-gold m-0">
                {{ $t('telegramStudio.inlineButtons') || 'Inline buttons' }}
              </h2>
            </div>
            <div class="space-y-2">
              <div
                v-for="(btn, idx) in form.inline_buttons"
                :key="idx"
                class="flex flex-wrap gap-2 items-center p-3 rounded-xl"
                style="background: var(--bg-input); border: 1px solid var(--border-card);"
              >
                <input
                  v-model="btn.label"
                  type="text"
                  class="input-luxury flex-1 min-w-[100px] py-2"
                  :placeholder="$t('telegramStudio.buttonLabel') || 'Label'"
                />
                <input
                  v-model="btn.url"
                  type="url"
                  class="input-luxury flex-1 min-w-[120px] py-2"
                  :placeholder="$t('telegramStudio.buttonUrl') || 'URL'"
                />
                <button
                  type="button"
                  class="btn-luxury-outline p-2 border-red-500/50 text-red-400 hover:bg-red-500/10 shrink-0"
                  :aria-label="$t('common.delete')"
                  @click="removeButton(idx)"
                >
                  <i class="fas fa-trash" />
                </button>
              </div>
            </div>
            <button
              type="button"
              class="btn-luxury-outline text-sm py-2 w-full mt-3"
              @click="addButton"
            >
              <i class="fas fa-plus me-2" />
              {{ $t('telegramStudio.addButton') || 'Add button' }}
            </button>
          </section>

          <!-- Save -->
          <div class="flex justify-end pt-2">
            <button
              type="button"
              class="btn-luxury px-8 py-3 text-lg gap-2"
              :class="{ 'opacity-80 pointer-events-none': saving }"
              :disabled="saving"
              @click="save"
            >
              <LoadingSpinner v-if="saving" class="w-5 h-5" />
              <i v-else class="fas fa-check-double" />
              <span>{{ saving ? ($t('telegramStudio.saving') || 'Saving…') : ($t('telegramStudio.saveSync') || 'Save & Sync') }}</span>
            </button>
          </div>
        </div>

        <!-- Right: Live Preview (below form on mobile) -->
        <div class="lg:sticky lg:top-6 order-2 lg:order-2">
          <div
            class="card-luxury p-5 border-2 border-[var(--border-card-hover)] shadow-glow"
          >
            <div
              class="flex items-center gap-2 mb-4 pb-3 border-b"
              style="border-color: var(--border-card);"
            >
              <i class="fas fa-mobile-alt text-gold" />
              <h2 class="text-lg font-semibold text-gold m-0">
                {{ $t('telegramStudio.livePreview') || 'Live preview' }}
              </h2>
            </div>
            <TelegramMockup
              :image-url="templateMediaUrl"
              :description="form.telegram_message_description"
              :buttons="validButtons"
              :variable-values="variableValues"
            />
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card-luxury p-8 text-center text-[var(--text-secondary)]">
      {{ $t('telegramStudio.categoryNotFound') || 'Category not found.' }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'
import { categoryApi, templateEditorApi, finalizeApi } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { useAnchoredPanel } from '@/composables/useAnchoredPanel'
import TelegramMockup from '@/components/telegram/TelegramMockup.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { t } = useI18n()

const props = defineProps({
  // Set when the editor is embedded in the Telegram section instead of its own route.
  categoryId: { type: [String, Number], default: null },
  embedded: { type: Boolean, default: false },
})

const categoryId = computed(() => props.categoryId ?? route.params.id)
const isRtl = computed(() => document.documentElement.dir === 'rtl')
const loading = ref(true)
const category = ref(null)
const form = ref({
  telegram_message_description: '',
  inline_buttons: [],
})
const {
  triggerRef: variableTriggerRef,
  panelRef: variablePanelRef,
  open: showVariableMenu,
  panelStyle: variablePanelStyle,
  close: closeVariableMenu,
  toggle: toggleVariableMenu,
} = useAnchoredPanel({ minWidth: 260, maxHeight: 448 })
const descriptionTextarea = ref(null)
let bannerObjectUrl = ''
const saving = ref(false)
const templateMediaUrl = ref('')
function formatPricePreview(raw) {
  if (raw == null || raw === '') return '—'
  const n = Number(String(raw).replace(/,/g, ''))
  if (Number.isNaN(n)) return String(raw)
  if (Math.abs(n - Math.round(n)) < 1e-9) return Math.round(n).toLocaleString('en-US')
  const s = n.toFixed(2).replace(/\.?0+$/, '')
  if (!s.includes('.')) return Number(s).toLocaleString('en-US')
  const [w, frac] = s.split('.')
  return `${Number(w).toLocaleString('en-US')}.${frac}`
}

const staticVariables = [
  { key: 'date_fa', label: 'Persian date' },
  { key: 'date_en', label: 'English date' },
  { key: 'farsi_weekday', label: 'Persian weekday' },
  { key: 'english_weekday', label: 'English weekday' },
  { key: 'time', label: 'Time' },
]

const validButtons = computed(() =>
  (form.value.inline_buttons || []).filter((b) => b && (b.label || b.url)).map((b) => ({ label: b.label || '', url: b.url || '' }))
)

const isIncomplete = computed(() => {
  return !templateMediaUrl.value
})

const variableValues = computed(() => {
  const now = new Date()
  const faWeek = new Intl.DateTimeFormat('fa-IR', { weekday: 'long' }).format(now)
  const enWeek = new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(now)
  const out = {
    date_fa: new Intl.DateTimeFormat('fa-IR-u-ca-persian', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(now),
    date_en: new Intl.DateTimeFormat('en-GB', {
      year: 'numeric',
      month: 'long',
      day: '2-digit',
    }).format(now),
    farsi_weekday: faWeek,
    english_weekday: enWeek,
    weekday_fa: faWeek,
    weekday_en: enWeek,
    time: new Intl.DateTimeFormat('fa-IR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(now),
  }
  const pts = category.value?.price_types || []
  pts.forEach((pt) => {
    const raw = pt.latest_price
    const val = formatPricePreview(raw)
    const slug = (pt.slug || '').trim()
    const name = (pt.name || '').trim()
    if (slug) out[slug] = val
    if (name) out[name] = val
  })
  return out
})

onMounted(async () => {
  await loadCategory()
})

onBeforeUnmount(() => {
  if (bannerObjectUrl) URL.revokeObjectURL(bannerObjectUrl)
})

watch(() => props.categoryId, (next, prev) => {
  if (props.embedded && next && next !== prev) loadCategory()
})

async function loadCategory() {
  loading.value = true
  try {
    const { data } = await categoryApi.get(categoryId.value)
    category.value = data
    templateMediaUrl.value = (data.template_media_url || '').trim()
    // Show the banner exactly as it would be posted, drawn from the latest prices.
    try {
      const { data: blob } = await finalizeApi.categoryBanner(categoryId.value, 'standard', { silent: true })
      if (bannerObjectUrl) URL.revokeObjectURL(bannerObjectUrl)
      bannerObjectUrl = URL.createObjectURL(blob)
      templateMediaUrl.value = bannerObjectUrl
    } catch {
      // keep the template image as the preview
    }
    if (!templateMediaUrl.value && data.last_used_template) {
      try {
        const templateRes = await templateEditorApi.get(data.last_used_template)
        const rawImage = templateRes?.data?.image
        // image may be a DRF file-field object { url, name } or a raw URL string
        templateMediaUrl.value = rawImage?.url || rawImage || ''
      } catch {
        templateMediaUrl.value = ''
      }
    }
    form.value = {
      telegram_message_description: data.telegram_message_description ?? '',
      inline_buttons: Array.isArray(data.inline_buttons)
        ? data.inline_buttons.map((b) => ({ label: b?.label ?? '', url: b?.url ?? '', row: b?.row }))
        : [],
    }
  } catch {
    category.value = null
  } finally {
    loading.value = false
  }
}

function insertVariable(slugOrName) {
  const code = `{${slugOrName}}`
  const ta = descriptionTextarea.value
  if (ta) {
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const text = form.value.telegram_message_description
    form.value.telegram_message_description = text.slice(0, start) + code + text.slice(end)
    nextTick(() => {
      ta.focus()
      ta.setSelectionRange(start + code.length, start + code.length)
    })
  } else {
    form.value.telegram_message_description = (form.value.telegram_message_description || '') + code
  }
  closeVariableMenu()
}

function variableCode(pt) {
  return `{${pt.slug || pt.name}}`
}

function addButton() {
  if (!form.value.inline_buttons) form.value.inline_buttons = []
  form.value.inline_buttons.push({ label: '', url: '' })
}

function removeButton(idx) {
  form.value.inline_buttons.splice(idx, 1)
}

async function save() {
  saving.value = true
  try {
    await categoryApi.patch(categoryId.value, {
      telegram_message_description: form.value.telegram_message_description || null,
      inline_buttons: form.value.inline_buttons
        .filter((b) => b && (b.label || b.url))
        .map(({ label, url, row }) => (row == null ? { label, url } : { label, url, row })),
    })
    toast.success(t('toast.saveSuccess'))
    if (!props.embedded) router.push('/categories')
  } catch (err) {
    toast.error(err.response?.data?.detail || t('toast.serverError'))
  } finally {
    saving.value = false
  }
}
</script>
