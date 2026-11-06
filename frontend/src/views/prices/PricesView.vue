<template>
  <div class="w-full min-w-0 overflow-hidden">
    <h1 class="text-2xl font-bold text-gold mb-4">{{ $t('routes.prices') }}</h1>
    <div v-if="loading" class="space-y-4">
      <div class="card-luxury overflow-x-auto px-4 py-3">
        <div class="space-y-4">
          <BaseSkeleton v-for="i in 8" :key="i" variant="table-row" />
        </div>
      </div>
      <div class="card-luxury px-4 py-3">
        <BaseSkeleton variant="text" class="mb-3 !max-w-[200px] !h-5" />
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BaseSkeleton v-for="i in 6" :key="i" variant="card" class="!h-20" />
        </div>
      </div>
    </div>
    <div v-else class="card-luxury w-full min-w-0 overflow-hidden px-4 py-3">
      <div class="w-full overflow-x-auto max-w-full">
        <table class="w-full text-sm min-w-[400px]">
        <thead>
          <tr class="border-b border-[var(--border-color)]">
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('prices.priceType') }}</th>
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('prices.category') }}</th>
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('prices.pair') }}</th>
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('prices.latestPrice') }}</th>
            <th class="text-left py-4 px-4 text-gold font-semibold">{{ $t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="pt in prices"
            :key="pt.id"
            class="border-b border-[var(--border-card)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <td class="py-4 px-4">{{ pt.name }}</td>
            <td class="py-4 px-4 text-gray-400">
              <span class="inline-flex items-center gap-2">
                <span class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-primary-muted">
                  <CategoryIcon :category-name="pt.category_name" size-class="h-3.5 w-3.5" />
                </span>
                <span>{{ pt.category_name }}</span>
              </span>
            </td>
            <td class="py-4 px-4">{{ pt.source_currency }} / {{ pt.target_currency }}</td>
            <td class="py-4 px-4 text-gold font-semibold">{{ pt.latest_price != null ? Number(pt.latest_price).toFixed(2) : '-' }}</td>
            <td class="py-4 px-4">
              <router-link :to="`/prices/${pt.id}/history`" class="btn-luxury-outline text-sm py-1.5 px-3">
                <i class="fas fa-history"></i> {{ $t('prices.history') }}
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <p
        v-if="!loading && (!prices || !prices.length)"
        class="text-center text-gray-500 py-6"
      >
        {{ $t('emptyState.noPrices') }}
      </p>
    </div>
    <div class="mt-4">
      <router-link
        to="/categories"
        class="inline-flex items-center gap-2 rounded-2xl border-2 p-4 transition-all duration-300 hover:scale-[1.01] hover:shadow-lg border-[var(--border-color)] bg-[var(--bg-card)]"
      >
        <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-muted">
          <i class="fas fa-sync-alt text-gold text-xl"></i>
        </div>
        <div>
          <span class="text-lg font-bold text-[var(--text-primary)]">{{ $t('common.update') }}</span>
          <p class="text-sm text-[var(--text-secondary)]">{{ $t('update.byCategory') }}</p>
        </div>
        <i class="fas fa-chevron-left text-gold ms-auto"></i>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { priceApi, categoryApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'

const loading = ref(true)
const prices = ref([])
const categories = ref([])

onMounted(async () => {
  try {
    const [pRes, cRes] = await Promise.all([priceApi.list(), categoryApi.list()])

    const priceData = pRes.data
    prices.value = Array.isArray(priceData) ? priceData : (priceData?.results ?? [])

    const catData = cRes.data
    const rawCategories = Array.isArray(catData) ? catData : (catData?.results ?? [])
    categories.value = rawCategories.filter((c) => c && c.id != null)
  } catch {
    prices.value = []
    categories.value = []
  } finally {
    loading.value = false
  }
})
</script>
