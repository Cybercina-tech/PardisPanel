<template>
  <div class="finalize-dashboard mx-auto flex w-full max-w-3xl flex-col items-center px-1 pb-64 md:pb-28">
    <h1 class="mb-6 w-full text-center text-2xl font-bold text-gold">{{ $t('finalize.title') }}</h1>

    <div v-if="loading" class="card-luxury w-full max-w-xl space-y-4 p-6">
      <BaseSkeleton variant="text" class="!h-4 !max-w-full" />
      <BaseSkeleton variant="text" class="!h-12 !max-w-full" />
      <BaseSkeleton variant="text" class="!h-12 !max-w-full" />
    </div>

    <template v-else>
      <div
        v-if="!data?.has_telegram_channel"
        class="card-luxury w-full max-w-xl space-y-4 p-6 text-center"
      >
        <i class="fab fa-telegram-plane text-4xl text-gold" />
        <p class="text-lg font-semibold text-[var(--text-primary)]">
          {{ $t('finalize.wizard.noChannelTitle') }}
        </p>
        <p class="text-sm text-[var(--text-secondary)]">
          {{ $t('finalize.wizard.noChannelHint') }}
        </p>
        <router-link to="/telegram/send?tab=channels" class="btn-luxury inline-flex">
          {{ $t('finalize.addChannelLink') }}
        </router-link>
      </div>

      <div v-else-if="!items.length" class="finalize-empty w-full max-w-xl text-center">
        <i class="fas fa-check-circle mb-3 text-4xl text-gold" />
        <p class="text-[var(--text-secondary)]">{{ $t('finalizeDashboard.allUpToDate') }}</p>
        <p class="mt-2 text-sm text-[var(--text-secondary)]">{{ $t('finalize.wizard.updatePricesHint') }}</p>
        <router-link to="/finalize/banners" class="btn-luxury-outline mt-4 inline-flex justify-center">
          <i class="fas fa-images" />
          {{ $t('finalize.banners.openPage') }}
        </router-link>
      </div>

      <section v-else class="w-full space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <label class="inline-flex cursor-pointer items-center gap-2 text-sm text-[var(--text-secondary)]">
            <input
              type="checkbox"
              class="h-4 w-4 accent-[var(--primary)]"
              :checked="allSelected"
              :disabled="publishing"
              @change="toggleAll($event.target.checked)"
            >
            {{ $t('finalize.quick.selectAll') }}
          </label>
          <div v-if="channels.length > 1" class="flex min-w-0 flex-1 items-center gap-2 sm:flex-none">
            <label class="shrink-0 text-sm text-[var(--text-secondary)]" for="finalize-channel">
              {{ $t('finalize.quick.publishTo') }}
            </label>
            <select id="finalize-channel" v-model="channelId" class="input-luxury min-w-0 flex-1 sm:!w-auto sm:flex-none" :disabled="publishing">
              <option v-for="ch in channels" :key="ch.id" :value="String(ch.id)">{{ ch.name }}</option>
            </select>
          </div>
          <span v-else-if="channels.length" class="text-sm text-[var(--text-secondary)]">
            <i class="fab fa-telegram-plane text-gold" /> {{ channels[0].name }}
          </span>
        </div>

        <ul class="space-y-3">
          <li v-for="item in items" :key="item.key">
            <label
              class="finalize-card flex w-full cursor-pointer items-start gap-3 transition hover:border-gold/50"
              :class="{ 'ring-2 ring-gold': selected.has(item.key) }"
            >
              <input
                type="checkbox"
                class="mt-1 h-5 w-5 shrink-0 accent-[var(--primary)]"
                :checked="selected.has(item.key)"
                :disabled="publishing"
                @change="toggle(item.key)"
              >
              <span class="min-w-0 flex-1">
                <span class="inline-flex items-center gap-2 text-base font-semibold text-gold">
                  <CategoryIcon v-if="item.kind === 'category'" :category-name="item.name" size-class="h-3.5 w-3.5" />
                  <i v-else class="fas fa-star text-xs" />
                  <span>{{ item.name }}</span>
                </span>
                <span class="finalize-rows mt-2 block text-sm text-[var(--text-secondary)]">
                  <template v-if="item.kind === 'category'">
                    <span v-for="pp in item.prices" :key="pp.price_history_id" class="finalize-row">
                      <span class="finalize-row-name" dir="auto">{{ pp.price_type_name }}</span>
                      <b class="finalize-row-value" dir="ltr">{{ formatPrice(pp.price) }}</b>
                    </span>
                  </template>
                  <template v-else-if="item.isDouble">
                    <span class="finalize-row">
                      <span class="finalize-row-name">{{ $t('specialPrices.cashPrice') }}</span>
                      <b class="finalize-row-value" dir="ltr">{{ formatPrice(item.cashPrice ?? item.price) }}</b>
                    </span>
                    <span class="finalize-row">
                      <span class="finalize-row-name">{{ $t('specialPrices.accountPrice') }}</span>
                      <b class="finalize-row-value" dir="ltr">{{ formatPrice(item.accountPrice) }}</b>
                    </span>
                  </template>
                  <template v-else>
                    <b class="text-[var(--text-primary)]" dir="ltr">{{ formatPrice(item.price) }}</b>
                  </template>
                </span>
                <span
                  v-if="publishing && progress.currentKey === item.key"
                  class="mt-1 flex items-center gap-2 text-xs text-gold"
                >
                  <LoadingSpinner class="h-3.5 w-3.5" />
                  {{ $t('finalize.quick.sendingItem') }}
                </span>
                <span
                  v-else-if="publishing && selected.has(item.key) && !resultFor(item)"
                  class="mt-1 block text-xs text-[var(--text-secondary)]"
                >
                  <i class="far fa-clock" /> {{ $t('finalize.quick.waitingItem') }}
                </span>
                <span
                  v-else-if="resultFor(item)"
                  class="mt-1 block text-xs"
                  :class="resultFor(item).ok ? 'text-success' : 'text-danger'"
                >
                  <i class="fas" :class="resultFor(item).ok ? 'fa-check' : 'fa-times'" />
                  {{ resultFor(item).ok ? $t('finalize.wizard.publishedSuccessfully') : resultFor(item).message }}
                </span>
              </span>
              <button
                v-if="item.kind === 'special'"
                type="button"
                class="btn-luxury-outline shrink-0 px-3 py-1.5 text-sm"
                :disabled="isDownloading('special', item.historyId)"
                :title="$t('finalize.banner.download')"
                @click.prevent="downloadBanner('special', item.historyId)"
              >
                <LoadingSpinner v-if="isDownloading('special', item.historyId)" class="h-4 w-4" />
                <i v-else class="fas fa-download" />
              </button>
            </label>
          </li>
        </ul>

        <div
          class="finalize-bar"
          :class="['start-0', 'md:start-16', sidebarStore.isCollapsed ? 'lg:start-16' : 'lg:start-64']"
        >
          <div v-if="publishing" class="w-full max-w-3xl" role="status" aria-live="polite">
            <div class="mb-1 flex items-center justify-between gap-2 text-xs text-[var(--text-secondary)]">
              <span>{{ $t('finalize.quick.progress', { done: Math.min(progress.done + 1, progress.total), total: progress.total }) }}</span>
              <span>{{ $t('finalize.quick.keepOpen') }}</span>
            </div>
            <div class="finalize-progress">
              <div class="finalize-progress-fill" :style="{ width: `${progressPercent}%` }" />
            </div>
          </div>
          <p v-else-if="!selected.size" class="text-xs text-[var(--text-secondary)]">
            {{ $t('finalize.quick.nothingSelected') }}
          </p>
          <div class="flex w-full max-w-3xl flex-col gap-2 sm:flex-row sm:items-stretch">
            <button
              type="button"
              class="btn-luxury w-full min-w-0 justify-center !px-4 !py-3 sm:flex-1"
              :disabled="!selected.size || !channelId || publishing"
              @click="confirmAndPublish"
            >
              <template v-if="publishing">
                <LoadingSpinner class="h-5 w-5" />
                {{ $t('finalize.quick.publishing') }}
              </template>
              <template v-else>
                <i class="fas fa-paper-plane" />
                {{ $t('finalize.quick.confirmAndPublish', { count: selected.size }) }}
              </template>
            </button>
            <router-link
              to="/finalize/banners"
              class="btn-luxury-outline w-full justify-center !px-4 !py-2.5 sm:w-auto sm:shrink-0"
              :title="$t('finalize.banners.openPage')"
              :aria-label="$t('finalize.banners.openPage')"
            >
              <i class="fas fa-images" />
              <span>{{ $t('finalize.banners.openPage') }}</span>
            </router-link>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { finalizeApi } from '@/services/api'
import { useFinalizeStore } from '@/stores/finalize'
import { useSidebarStore } from '@/stores/sidebar'
import { useBannerDownload } from '@/composables/useBannerDownload'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { formatAppDecimal } from '@/utils/localeFormat.js'

const { downloadBanner, isDownloading } = useBannerDownload()
const { locale } = useI18n()
const finalizeStore = useFinalizeStore()
const sidebarStore = useSidebarStore()
const { channelId, publishing, results, progress } = storeToRefs(finalizeStore)

const loading = ref(true)
const data = ref(null)
const selected = ref(new Set())

const channels = computed(() => data.value?.channels ?? [])

// One flat list: pending categories first, then special prices.
const items = computed(() => [
  ...(data.value?.pending_by_category ?? []).map((c) => ({
    key: `c${c.category_id}`,
    kind: 'category',
    id: c.category_id,
    name: c.category_name,
    prices: c.pending_prices ?? [],
  })),
  ...(data.value?.pending_special_prices ?? []).map((sp) => ({
    key: `s${sp.price_history_id}`,
    kind: 'special',
    id: sp.special_price_type_id,
    historyId: sp.price_history_id,
    name: sp.special_price_type_name,
    price: sp.price,
    isDouble: Boolean(sp.is_double_price),
    cashPrice: sp.cash_price,
    accountPrice: sp.account_price,
  })),
])

const progressPercent = computed(() => {
  const { done, total } = progress.value
  if (!total) return 0
  // Count the job in flight as half done so the bar moves as soon as publishing starts.
  return Math.min(100, Math.round(((done + 0.5) / total) * 100))
})

const allSelected = computed(() => items.value.length > 0 && selected.value.size === items.value.length)

function formatPrice(value) {
  if (value == null || value === '') return '—'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(num)) return String(value)
  return formatAppDecimal(locale.value === 'fa' ? 'fa' : 'en', num, 2)
}

function resultFor(item) {
  const id = item.kind === 'category' ? item.id : item.historyId
  return results.value.find((r) => r.kind === item.kind && String(r.id) === String(id)) ?? null
}

function toggle(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

function toggleAll(on) {
  selected.value = on ? new Set(items.value.map((i) => i.key)) : new Set()
}

async function confirmAndPublish() {
  const chosen = items.value.filter((i) => selected.value.has(i.key))
  await finalizeStore.quickPublish({
    categoryIds: chosen.filter((i) => i.kind === 'category').map((i) => i.id),
    specialHistoryIds: chosen.filter((i) => i.kind === 'special').map((i) => i.historyId),
  })
  const failedKeys = new Set(
    results.value
      .filter((r) => !r.ok)
      .map((r) => (r.kind === 'category' ? `c${r.id}` : `s${r.id}`)),
  )
  await fetchData()
  // Sent items drop off the pending list; failed ones stay selected for a retry.
  selected.value = new Set(items.value.filter((i) => failedKeys.has(i.key)).map((i) => i.key))
}

async function fetchData() {
  try {
    const { data: res } = await finalizeApi.dashboard()
    data.value = res
    const known = (res?.channels ?? []).map((c) => String(c.id))
    if (known.length && !known.includes(String(channelId.value))) {
      channelId.value = known[0]
    }
  } catch {
    data.value = { pending_by_category: [], pending_special_prices: [], channels: [], has_telegram_channel: false }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  finalizeStore.results = []
  await fetchData()
  toggleAll(true)
})
</script>

<style scoped>
.finalize-card,
.finalize-empty {
  border: 1px solid var(--border-card);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--bg-card) 92%, transparent);
  padding: 0.9rem;
  box-shadow: 0 8px 20px -18px rgba(15, 23, 42, 0.8);
}

/* One price per line: name at the start edge, number at the end edge. Mixed
   Persian/Latin inline text reorders unpredictably when it wraps on a phone. */
.finalize-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.3rem 0;
}

.finalize-row + .finalize-row {
  border-top: 1px dashed color-mix(in srgb, var(--border-card) 70%, transparent);
}

.finalize-row-name {
  min-width: 0;
  overflow-wrap: anywhere;
}

.finalize-row-value {
  flex-shrink: 0;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  unicode-bidi: isolate;
}

.finalize-link-btn {
  width: 100%;
  justify-content: center;
}

.finalize-bar {
  position: fixed;
  inset-inline-end: 0;
  /* Sit on top of the mobile bottom nav: 48px tap target + 0.5rem top padding + its
     bottom padding (grows with the iOS home-indicator inset) + 1px border. From md the
     nav is gone and the sidebar sits beside the bar. */
  bottom: calc(4.0625rem + max(0rem, env(safe-area-inset-bottom) - 0.5rem));
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 0.75rem 1rem;
  background: color-mix(in srgb, var(--bg-base) 94%, transparent);
  border-top: 1px solid var(--border-card);
  backdrop-filter: blur(8px);
}

.finalize-progress {
  height: 0.375rem;
  overflow: hidden;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--primary) 18%, transparent);
}

.finalize-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--primary);
  transition: width 0.4s ease;
}

@media (min-width: 768px) {
  .finalize-bar {
    bottom: 0;
    padding-bottom: calc(0.75rem + env(safe-area-inset-bottom));
  }
}
</style>
