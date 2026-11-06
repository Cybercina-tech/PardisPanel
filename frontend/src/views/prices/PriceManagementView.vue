<template>
  <div>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('routes.priceHub') }}</h1>

    <div v-if="loading" class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <BaseSkeleton v-for="i in 8" :key="i" variant="card" class="!h-16" />
    </div>

    <template v-else>
      <section class="mb-10">
        <h2 class="text-lg font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
          <i class="fas fa-coins text-gold"></i>
          {{ $t('priceHub.standardCategories') }}
        </h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="cat in categories"
            :key="cat.id"
            class="hub-card group flex flex-col gap-5 rounded-2xl border p-5"
          >
            <div class="flex items-center gap-4">
              <span class="hub-icon flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl">
                <CategoryIcon :category-name="cat.name" size-class="h-7 w-7" />
              </span>
              <div class="min-w-0 flex-1">
                <h3 class="truncate text-lg font-bold text-[var(--text-primary)]" dir="auto" :title="cat.name">
                  {{ cat.name }}
                </h3>
                <p class="mt-0.5 text-sm text-[var(--text-secondary)]">
                  {{ priceTypeCount(cat) }} {{ $t('dashboard.priceTypes') }}
                </p>
              </div>
            </div>
            <div class="mt-auto flex items-center justify-between gap-3">
              <span class="min-w-0 truncate text-xs text-[var(--text-secondary)]">
                <i class="far fa-clock me-1" />{{ lastUpdatedLabel(cat) }}
              </span>
              <router-link :to="`/prices/category/${cat.id}/update`" class="hub-update-btn">
                <i class="fas fa-sync-alt text-xs" />
                {{ $t('common.update') }}
              </router-link>
            </div>
          </article>
        </div>
        <EmptyState
          v-if="!categories.length"
          icon="fas fa-layer-group"
          title-key="priceHub.noCategoriesTitle"
          description-key="priceHub.noCategoriesDesc"
          action-label="priceHub.createCategory"
          action-to="/categories/new"
        />
      </section>

      <section v-if="specialPrices.length">
        <h2 class="text-lg font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
          <i class="fas fa-star text-gold"></i>
          {{ $t('priceHub.specialOffersVip') }}
        </h2>
        <div class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="sp in specialPrices"
            :key="sp.id"
            class="hub-card group flex flex-col gap-4 rounded-2xl border p-4 sm:p-5"
          >
            <div class="flex items-start gap-3 sm:gap-4">
              <span class="hub-icon flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl sm:h-14 sm:w-14">
                <i :class="sp.icon || 'fas fa-star'" class="text-2xl" />
              </span>
              <div class="min-w-0 flex-1">
                <h3 class="break-words text-base font-bold leading-snug text-[var(--text-primary)] sm:text-lg" dir="auto">
                  {{ sp.name }}
                </h3>
                <p class="mt-1 break-words text-xs leading-relaxed text-[var(--text-secondary)] sm:text-sm">
                  {{ renderPairSummary(sp) }}
                </p>
              </div>
            </div>
            <div class="mt-auto flex sm:justify-end">
              <router-link :to="`/prices/special/${sp.id}/update`" class="hub-update-btn w-full justify-center sm:w-auto">
                <i class="fas fa-sync-alt text-xs" />
                {{ $t('common.update') }}
              </router-link>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDate } from '@/composables/useDate'
import { categoryApi, specialPriceApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const { formatRelative } = useDate()
const loading = ref(true)
const categories = ref([])
const specialPrices = ref([])

function priceTypeCount(cat) {
  return cat.price_type_count ?? cat.price_types?.length ?? 0
}

function lastUpdatedLabel(cat) {
  const stamps = (cat.price_types ?? [])
    .map((pt) => pt.latest_price_at)
    .filter(Boolean)
    .map((iso) => new Date(iso).getTime())
    .filter((ms) => Number.isFinite(ms))
  if (!stamps.length) return '—'
  return formatRelative(new Date(Math.max(...stamps)))
}

function normalizeCategoryList(catData) {
  return Array.isArray(catData)
    ? catData
    : (catData?.results ?? []).filter((c) => c && c.id != null)
}

function normalizeSpecialList(spData) {
  return Array.isArray(spData) ? spData : (spData?.results ?? [])
}

function renderPairSummary(sp) {
  const pairs = Array.isArray(sp?.pairs) ? sp.pairs : []
  if (!pairs.length) {
    const src = sp?.source_currency?.code ?? sp?.source_currency ?? '—'
    const tgt = sp?.target_currency?.code ?? sp?.target_currency ?? '—'
    return `${src} / ${tgt}`
  }
  if (pairs.length === 1) {
    const type = pairs[0].trade_type === 'sell' ? 'Sell' : 'Buy'
    return `${pairs[0].name ?? ''} - ${pairs[0].source_currency?.code ?? '—'} / ${pairs[0].target_currency?.code ?? '—'} (${type})`
  }
  const type = pairs[0].trade_type === 'sell' ? 'Sell' : 'Buy'
  return `${pairs[0].name ?? ''} - ${pairs[0].source_currency?.code ?? '—'} / ${pairs[0].target_currency?.code ?? '—'} (${type}) +${pairs.length - 1}`
}

onMounted(async () => {
  try {
    const [catRes, spRes] = await Promise.all([
      categoryApi.list(),
      specialPriceApi.list(),
    ])
    categories.value = normalizeCategoryList(catRes.data)
    specialPrices.value = normalizeSpecialList(spRes.data)
  } catch {
    categories.value = []
    specialPrices.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.hub-card {
  border-color: var(--border-card-hover);
  background: linear-gradient(145deg, var(--bg-card) 0%, var(--primary-muted) 100%);
  box-shadow: 0 10px 28px -20px rgba(0, 0, 0, 0.7);
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}
.hub-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary);
  box-shadow: 0 16px 34px -18px rgba(0, 0, 0, 0.75);
}
.hub-icon {
  color: var(--primary);
  background: var(--primary-muted);
  border: 1px solid var(--border-card-hover);
}
.hub-update-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.75rem;
  padding: 0.55rem 1.1rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--bg-base);
  background: var(--primary);
  transition: filter 0.2s ease, transform 0.2s ease;
}
.hub-update-btn:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}
</style>
