<template>
  <div class="pb-28">
    <nav class="mb-6">
      <router-link
        to="/update"
        class="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--primary)] transition-colors font-medium"
      >
        <i class="fas" :class="isRtl ? 'fa-arrow-right' : 'fa-arrow-left'" />
        {{ $t('priceHub.backToHub') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-2 inline-flex items-center gap-2">
      <CategoryIcon :category-name="category?.name" size-class="h-5 w-5" />
      <span>{{ category?.name ?? $t('routes.category') }}</span>
    </h1>
    <p class="text-[var(--text-secondary)] mb-6">{{ $t('routes.bulkUpdate') }}</p>

    <div v-if="loading" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseSkeleton v-for="i in 6" :key="i" variant="table-row" class="!h-14" />
    </div>

    <template v-else-if="priceTypes.length">
      <!-- Two columns: Buy | Sell as large cards -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <!-- Buy column card -->
        <div
          class="price-card-buy rounded-2xl border-2 overflow-hidden border-emerald-500/40 bg-[var(--bg-card)]"
        >
          <div
            class="px-5 py-4 text-lg font-bold text-emerald-400"
            style="background: rgba(16, 185, 129, 0.15);"
          >
            {{ $t('bulkUpdate.buy') }}
          </div>
          <div class="p-5 space-y-4">
            <div
              v-for="pt in priceTypesByBuy"
              :key="pt.id"
              class="flex flex-wrap items-center gap-4 py-4 px-5 rounded-xl border border-emerald-500/25"
              style="background: rgba(16, 185, 129, 0.06);"
            >
              <label class="flex-1 min-w-[140px] text-base font-bold text-[var(--text-primary)]">
                {{ pt.name }}
                <span class="text-sm font-normal text-[var(--text-secondary)]">({{ pt.source_currency }}/{{ pt.target_currency }})</span>
              </label>
              <input
                :value="formatThousands(prices[pt.id])"
                type="text"
                inputmode="decimal"
                class="w-44 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)] px-3 py-2.5 text-xl text-[var(--text-primary)] outline-none transition focus:border-emerald-500/60 focus:bg-[var(--bg-card)] focus:ring-2 focus:ring-emerald-500/20"
                :placeholder="pt.latest_price != null ? formatThousands(Number(pt.latest_price)) : ''"
                @input="onPriceInput(pt.id, ($event.target).value)"
                @focus="($event.target).select()"
              />
              <span
                v-if="pt.latest_price_at"
                class="text-xs text-[var(--text-secondary)] whitespace-nowrap"
              >
                {{ formatDateTime(pt.latest_price_at) }}
              </span>
            </div>
            <p v-if="!priceTypesByBuy.length" class="text-sm text-[var(--text-secondary)] py-2">—</p>
          </div>
        </div>

        <!-- Sell column card -->
        <div
          class="price-card-sell rounded-2xl border-2 overflow-hidden border-rose-500/40 bg-[var(--bg-card)]"
        >
          <div
            class="px-5 py-4 text-lg font-bold text-rose-400"
            style="background: rgba(244, 63, 94, 0.15);"
          >
            {{ $t('bulkUpdate.sell') }}
          </div>
          <div class="p-5 space-y-4">
            <div
              v-for="pt in priceTypesBySell"
              :key="pt.id"
              class="flex flex-wrap items-center gap-4 py-4 px-5 rounded-xl border border-rose-500/25"
              style="background: rgba(244, 63, 94, 0.06);"
            >
              <label class="flex-1 min-w-[140px] text-base font-bold text-[var(--text-primary)]">
                {{ pt.name }}
                <span class="text-sm font-normal text-[var(--text-secondary)]">({{ pt.source_currency }}/{{ pt.target_currency }})</span>
              </label>
              <input
                :value="formatThousands(prices[pt.id])"
                type="text"
                inputmode="decimal"
                class="w-44 rounded-lg border border-[var(--border-card)] bg-[var(--bg-input)] px-3 py-2.5 text-xl text-[var(--text-primary)] outline-none transition focus:border-rose-500/60 focus:bg-[var(--bg-card)] focus:ring-2 focus:ring-rose-500/20"
                :placeholder="pt.latest_price != null ? formatThousands(Number(pt.latest_price)) : ''"
                @input="onPriceInput(pt.id, ($event.target).value)"
                @focus="($event.target).select()"
              />
              <span
                v-if="pt.latest_price_at"
                class="text-xs text-[var(--text-secondary)] whitespace-nowrap"
              >
                {{ formatDateTime(pt.latest_price_at) }}
              </span>
            </div>
            <p v-if="!priceTypesBySell.length" class="text-sm text-[var(--text-secondary)] py-2">—</p>
          </div>
        </div>
      </div>

      <!-- Notes card -->
      <div
        class="rounded-2xl border p-5 mb-6"
        style="border-color: var(--border-card); background: var(--bg-card);"
      >
        <label class="block text-sm font-bold text-[var(--text-secondary)] mb-2">
          {{ $t('bulkUpdate.notesOptional') }}
        </label>
        <input v-model="notes" type="text" class="input-luxury w-full max-w-md py-2.5" />
      </div>
    </template>

    <div
      v-else-if="!loading"
      class="rounded-2xl border p-8 text-center text-[var(--text-secondary)]"
      style="border-color: var(--border-card); background: var(--bg-card);"
    >
      {{ $t('emptyState.noPrices') }}
    </div>

    <!-- Floating Save Bar -->
    <Transition name="fade">
      <div
        v-show="priceTypes.length && !loading"
        class="fixed start-0 end-0 z-40 flex items-center justify-between gap-4 px-4 py-3 border-t shadow-lg bottom-16 md:bottom-0"
        style="background: var(--bg-card); border-color: var(--border-card); padding-left: max(1rem, env(safe-area-inset-left)); padding-right: max(1rem, env(safe-area-inset-right)); padding-bottom: max(0.75rem, env(safe-area-inset-bottom));"
      >
        <span class="text-sm text-[var(--text-secondary)]">
          {{ $t('bulkUpdate.lastSynced') }}:
          {{ lastSyncedAt ? formatDateTime(lastSyncedAt) : $t('dashboard.never') }}
        </span>
        <button
          type="button"
          class="btn-luxury flex items-center gap-2 px-6 py-2.5 font-medium"
          :class="{ 'save-pulse': hasDirty }"
          :disabled="submitting || !hasPayload"
          @click="handleSubmit"
        >
          <LoadingSpinner v-if="submitting" class="w-5 h-5" />
          <i v-else class="fas fa-save" />
          {{ saveButtonLabel }}
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { priceApi, categoryApi, getApiErrorDetails } from '@/services/api'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import { usePriceDraft } from '@/composables/usePriceDraft'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const toast = useToast()
const siteSettings = useSiteSettingsStore()
const isRtl = computed(() => document.documentElement.dir === 'rtl')

const categoryId = computed(() => route.params.id)
const loading = ref(true)
const category = ref(null)
const priceTypes = ref([])
const prices = ref({})
const notes = ref('')
const submitting = ref(false)
const draft = usePriceDraft(computed(() => `bulk:${categoryId.value}`))
const lastSyncedAt = ref(null)
let previousTitle = ''

const priceTypesByBuy = computed(() =>
  priceTypes.value.filter((p) => p.trade_type === 'buy')
)
const priceTypesBySell = computed(() =>
  priceTypes.value.filter((p) => p.trade_type === 'sell')
)

const initialPrices = ref({})
const hasDirty = computed(() => {
  const current = JSON.stringify(prices.value)
  const initial = JSON.stringify(initialPrices.value)
  return current !== initial
})
const dirtyCount = computed(() => {
  let count = 0
  for (const [key, value] of Object.entries(prices.value)) {
    const initial = initialPrices.value[key]
    if (value === '' && initial === '') continue
    if (Number(value) !== Number(initial)) count += 1
  }
  return count
})
const saveButtonLabel = computed(() => {
  const base = t('bulkUpdate.saveChanges')
  return dirtyCount.value > 0 ? `${base} (${dirtyCount.value})` : base
})

const hasPayload = computed(() => {
  return Object.keys(buildEffectivePricePayload()).length > 0
})

function formatThousands(val) {
  if (val === '' || val == null || Number.isNaN(Number(val))) return ''
  const num = Number(val)
  const fixed = Number.isInteger(num) ? num.toString() : num.toFixed(2)
  const [intPart, decPart] = fixed.split('.')
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return decPart != null ? `${withCommas}.${decPart}` : withCommas
}

function parsePriceInput(str) {
  const raw = String(str).replace(/,/g, '').trim()
  if (raw === '') return ''
  const num = parseFloat(raw)
  return Number.isNaN(num) ? '' : num
}

function onPriceInput(id, value) {
  const parsed = parsePriceInput(value)
  prices.value[id] = parsed
}

function getLatestPriceNumber(pt) {
  if (pt?.latest_price != null && pt.latest_price !== '') {
    const n = Number(pt.latest_price)
    return Number.isNaN(n) ? null : n
  }
  if (pt?.latest_price && typeof pt.latest_price === 'object' && pt.latest_price.price != null) {
    const n = Number(pt.latest_price.price)
    return Number.isNaN(n) ? null : n
  }
  return null
}

function buildEffectivePricePayload() {
  const payload = {}
  for (const pt of priceTypes.value) {
    const key = String(pt.id)
    const entered = prices.value[pt.id]
    if (entered !== '' && entered != null && !Number.isNaN(Number(entered))) {
      payload[key] = Number(entered)
      continue
    }
    const fallback = getLatestPriceNumber(pt)
    if (fallback != null) payload[key] = fallback
  }
  return payload
}

function formatDateTime(val) {
  if (!val) return '—'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(d)
}

function setPageTitle() {
  if (!category.value?.name) return
  previousTitle = document.title
  const panelName = siteSettings.siteName || 'Panel'
  document.title = `${t('routes.priceHub')}: ${category.value.name} | ${panelName}`
}

function restorePageTitle() {
  if (previousTitle) document.title = previousTitle
}

onMounted(async () => {
  window.addEventListener('keydown', onDocumentKeydown)
  try {
    const [pRes, cRes] = await Promise.all([priceApi.list(), categoryApi.list()])
    const cats = Array.isArray(cRes.data) ? cRes.data : cRes.data?.results ?? []
    category.value = cats.find((c) => String(c.id) === String(categoryId.value)) ?? null
    const allPrices = Array.isArray(pRes.data) ? pRes.data : (pRes.data?.results ?? [])
    priceTypes.value = allPrices.filter(
      (p) => String(p.category_id) === String(categoryId.value)
    )
    const next = {}
    priceTypes.value.forEach((pt) => {
      // The API sends prices as strings; read them numerically so the last saved
      // price is filled in and only changed rows need typing.
      const latest = getLatestPriceNumber(pt)
      next[pt.id] = latest != null ? latest : ''
    })
    prices.value = next
    initialPrices.value = JSON.parse(JSON.stringify(next))
    restoreDraft()
    setPageTitle()
  } catch (error) {
    priceTypes.value = []
    toast.error(getApiErrorDetails(error).message)
  } finally {
    loading.value = false
  }
})

/** Re-apply numbers typed before a failed save, a reload or an expired session. */
function restoreDraft() {
  const saved = draft.load()
  if (!saved) return
  let restored = false
  for (const pt of priceTypes.value) {
    const v = saved.prices?.[pt.id]
    if (v !== '' && v != null && !Number.isNaN(Number(v)) && Number(v) !== Number(prices.value[pt.id])) {
      prices.value[pt.id] = Number(v)
      restored = true
    }
  }
  if (saved.notes && !notes.value) {
    notes.value = saved.notes
    restored = true
  }
  if (restored) draft.notifyRestored()
  else draft.clear()
}

watch([prices, notes], () => {
  if (loading.value) return
  if (hasDirty.value || notes.value) draft.save({ prices: prices.value, notes: notes.value })
  else draft.clear()
}, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onDocumentKeydown)
  restorePageTitle()
})

watch(
  () => category.value?.name,
  () => setPageTitle()
)

/** Enter acts like Save (same rules as the floating save button). */
function onDocumentKeydown(e) {
  if (e.key !== 'Enter' || e.repeat || e.isComposing) return
  if (loading.value || !priceTypes.value.length) return
  if (!hasPayload.value || submitting.value) return

  const el = e.target
  if (el?.closest?.('a[href]')) return
  // Let Enter activate focused buttons (avoid double-submit with handleSubmit).
  if (el instanceof HTMLButtonElement || el?.closest?.('button')) return

  e.preventDefault()
  handleSubmit()
}

async function handleSubmit() {
  if (submitting.value) return
  const pricePayload = buildEffectivePricePayload()
  if (!Object.keys(pricePayload).length) return

  submitting.value = true
  try {
    await priceApi.bulkUpdate(categoryId.value, {
      prices: pricePayload,
      notes: notes.value,
    }, { silent: true })
    draft.clear()
    lastSyncedAt.value = new Date()
    initialPrices.value = JSON.parse(JSON.stringify(prices.value))
    toast.success(t('toast.pricesUpdatedBroadcast'))
    await router.push('/update')
  } catch (error) {
    // The typed prices stay in the form (and in the saved draft) for another try.
    if (error.response?.status !== 401) draft.notifyNotSaved()
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.save-pulse {
  animation: savePulse 2s ease-in-out infinite;
}

@keyframes savePulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(212, 175, 55, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(212, 175, 55, 0);
  }
}
</style>
