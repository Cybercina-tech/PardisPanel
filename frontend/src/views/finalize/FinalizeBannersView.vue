<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-5 px-1 pb-8">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-bold text-gold">{{ $t('finalize.banners.title') }}</h1>
      <router-link to="/finalize" class="btn-luxury-outline inline-flex px-3 py-1.5 text-sm">
        <i class="fas fa-arrow-left rtl:rotate-180" />
        {{ $t('finalize.banners.back') }}
      </router-link>
    </div>
    <p class="text-sm text-[var(--text-secondary)]">{{ $t('finalize.banners.hint') }}</p>

    <ul class="grid gap-2 sm:grid-cols-3" role="list">
      <li v-for="fmt in formats" :key="fmt.size" class="banner-format">
        <i :class="fmt.icon" class="text-gold" />
        <span class="font-semibold text-[var(--text-primary)]">{{ $t(`finalize.banners.formats.${fmt.size}`) }}</span>
        <span class="text-xs text-[var(--text-secondary)]">{{ fmt.dimensions || $t('finalize.banners.asPublished') }}</span>
      </li>
    </ul>

    <div v-if="loading" class="card-luxury space-y-3 p-4">
      <BaseSkeleton v-for="n in 4" :key="n" variant="text" class="!h-12 !max-w-full" />
    </div>

    <div v-else-if="failed" class="finalize-empty text-center text-[var(--text-secondary)]">
      {{ $t('finalize.banners.loadFailed') }}
    </div>

    <template v-else>
      <section v-for="group in groups" :key="group.key" class="space-y-2">
        <h2 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          <i :class="group.icon" class="text-gold" />
          {{ $t(group.titleKey) }}
        </h2>
        <ul class="space-y-2">
          <li v-for="row in group.rows" :key="`${row.kind}-${row.id}`" class="banner-row">
            <span class="min-w-0 flex-1 truncate font-semibold text-gold" dir="auto">{{ row.name }}</span>
            <span class="flex flex-wrap gap-2">
              <button
                v-for="fmt in formats"
                :key="fmt.size"
                type="button"
                class="btn-luxury-outline justify-center px-3 py-1.5 text-sm"
                :disabled="isBusy"
                :title="`${$t(`finalize.banners.formats.${fmt.size}`)} · ${fmt.dimensions || $t('finalize.banners.asPublished')}`"
                @click="downloadBanner(row.kind, row.id, fmt.size)"
              >
                <LoadingSpinner v-if="isDownloading(row.kind, row.id, fmt.size)" class="h-4 w-4" />
                <i v-else :class="fmt.icon" />
                {{ $t(`finalize.banners.short.${fmt.size}`) }}
              </button>
            </span>
          </li>
        </ul>
      </section>

      <div v-if="!groups.length" class="finalize-empty text-center text-[var(--text-secondary)]">
        {{ $t('finalize.banners.empty') }}
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { finalizeApi } from '@/services/api'
import { useBannerDownload } from '@/composables/useBannerDownload'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

const { downloadBanner, isDownloading, isBusy } = useBannerDownload()

const formats = [
  { size: 'standard', icon: 'fas fa-image', dimensions: '' },
  { size: 'story', icon: 'fab fa-instagram', dimensions: '1080 × 1920' },
  { size: 'post', icon: 'far fa-square', dimensions: '1080 × 1080' },
]

const loading = ref(true)
const failed = ref(false)
const data = ref({ categories: [], special_prices: [] })

const groups = computed(() =>
  [
    {
      key: 'categories',
      titleKey: 'finalize.banners.categories',
      icon: 'fas fa-list',
      rows: data.value.categories.map((c) => ({ kind: 'category', id: c.id, name: c.name })),
    },
    {
      key: 'special',
      titleKey: 'finalize.banners.specialPrices',
      icon: 'fas fa-star',
      // Special banners are addressed by their latest price history row.
      rows: data.value.special_prices.map((s) => ({ kind: 'special', id: s.history_id, name: s.name })),
    },
  ].filter((g) => g.rows.length),
)

onMounted(async () => {
  try {
    const { data: res } = await finalizeApi.banners()
    data.value = {
      categories: res?.categories ?? [],
      special_prices: res?.special_prices ?? [],
    }
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.banner-format {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  min-height: 4.25rem;
  justify-content: center;
  border: 1px dashed var(--border-card);
  border-radius: 0.75rem;
  padding: 0.5rem;
  text-align: center;
}

.banner-row,
.finalize-empty {
  border: 1px solid var(--border-card);
  border-radius: 1rem;
  background: color-mix(in srgb, var(--bg-card) 92%, transparent);
  padding: 0.75rem 0.9rem;
}

.banner-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem 0.75rem;
}

@media (max-width: 479px) {
  .banner-row > span:last-child {
    width: 100%;
  }
  .banner-row > span:last-child > button {
    flex: 1 1 0;
  }
}
</style>
