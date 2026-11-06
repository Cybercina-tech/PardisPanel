<template>
  <div>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('routes.update') }}</h1>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <BaseSkeleton v-for="i in 6" :key="i" variant="card" class="!h-32" />
    </div>

    <template v-else>
      <!-- Categories: big bold cards -->
      <section class="mb-8">
        <h2 class="text-lg font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
          <i class="fas fa-folder text-gold"></i>
          {{ $t('dashboard.categories') }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <router-link
            v-for="cat in categories"
            :key="cat.id"
            :to="`/prices/category/${cat.id}/update`"
            class="group block rounded-2xl border-2 p-6 transition-all duration-300 ease-in-out hover:scale-[1.02] hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--bg-base)]"
            style="border-color: var(--border-color); background: var(--bg-card);"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <h3 class="text-xl font-bold text-[var(--text-primary)] group-hover:text-gold transition-colors truncate">
                  {{ cat.name }}
                </h3>
                <p class="text-sm text-[var(--text-secondary)] mt-1">
                  {{ cat.price_type_count ?? cat.price_types?.length ?? 0 }} {{ $t('analysis.priceType') }}
                </p>
              </div>
              <div
                class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl transition-colors bg-primary-muted"
              >
                <i class="fas fa-chevron-left text-gold text-lg group-hover:translate-x-[-2px] transition-transform"></i>
              </div>
            </div>
          </router-link>
        </div>
        <p v-if="!categories.length" class="text-center text-[var(--text-secondary)] py-8">
          {{ $t('dashboard.noCategoriesFound') }}
        </p>
      </section>

      <!-- Special Prices: big bold cards -->
      <section v-if="specialPrices.length">
        <h2 class="text-lg font-bold text-[var(--text-secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
          <i class="fas fa-star text-gold"></i>
          {{ $t('dashboard.specialPrices') }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <router-link
            v-for="sp in specialPrices"
            :key="sp.id"
            :to="`/special-prices/${sp.id}/update`"
            class="group block rounded-2xl border-2 p-6 transition-all duration-300 ease-in-out hover:scale-[1.02] hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--bg-base)]"
            style="border-color: var(--border-color); background: var(--bg-card);"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <h3 class="text-xl font-bold text-[var(--text-primary)] group-hover:text-gold transition-colors truncate">
                  {{ sp.name }}
                </h3>
                <p class="text-sm text-[var(--text-secondary)] mt-1">
                  {{ renderPairSummary(sp) }}
                </p>
              </div>
              <div
                class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl transition-colors bg-primary-muted"
              >
                <i v-if="sp.icon" :class="sp.icon" class="text-gold text-lg"></i>
                <i v-else class="fas fa-chevron-left text-gold text-lg group-hover:translate-x-[-2px] transition-transform"></i>
              </div>
            </div>
          </router-link>
        </div>
      </section>

      <!-- Link to full price list -->
      <div class="mt-8 pt-6 border-t" style="border-color: var(--border-card);">
        <router-link
          to="/prices"
          class="inline-flex items-center gap-2 text-[var(--text-secondary)] hover:text-gold transition-colors text-sm font-medium"
        >
          <i class="fas fa-list"></i>
          {{ $t('update.viewPriceList') }}
        </router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { categoryApi, specialPriceApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'

const loading = ref(true)
const categories = ref([])
const specialPrices = ref([])

function renderPairSummary(sp) {
  const pairs = Array.isArray(sp?.pairs) ? sp.pairs : []
  if (!pairs.length) {
    return `${sp.source_currency?.code ?? sp.source_currency ?? '—'} / ${sp.target_currency?.code ?? sp.target_currency ?? '—'}`
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
    const catData = catRes.data
    categories.value = Array.isArray(catData) ? catData : (catData?.results ?? []).filter((c) => c && c.id != null)
    const spData = spRes.data
    specialPrices.value = Array.isArray(spData) ? spData : (spData?.results ?? [])
  } catch {
    categories.value = []
    specialPrices.value = []
  } finally {
    loading.value = false
  }
})
</script>
