<template>
  <div>
    <h1 v-if="!embedded" class="text-2xl font-bold text-gold mb-8 animate-fade-in-up">{{ $t('sidebar.categories') }}</h1>

    <div v-if="loading" class="space-y-10">
      <div>
        <BaseSkeleton variant="text" class="!h-7 !max-w-[200px] mb-4" />
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BaseSkeleton v-for="i in 6" :key="i" variant="card" class="!h-40" />
        </div>
      </div>
      <div>
        <BaseSkeleton variant="text" class="!h-7 !max-w-[180px] mb-4" />
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BaseSkeleton v-for="i in 6" :key="'sp-' + i" variant="card" class="!h-40" />
        </div>
      </div>
    </div>

    <template v-else>
      <!-- Section 1: Standard Categories -->
      <section class="mb-12 animate-fade-in-up">
        <div class="flex justify-between items-center mb-5">
          <h2 class="text-lg font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <i class="fas fa-coins text-[var(--primary)]" />
            {{ $t('categories.standardCategories') }}
          </h2>
          <button type="button" class="btn-luxury" @click="$router.push('/categories/new')">
            <i class="fas fa-plus"></i> {{ $t('emptyState.createCategory') }}
          </button>
        </div>

        <div v-if="categories.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="(cat, index) in categories"
            :key="'cat-' + cat.id"
            class="card-vip p-5 flex flex-col overflow-hidden hover-lift animate-fade-in-up"
            :class="{ 'relative z-[210]': showPriceTypeGuide && guideCategoryId === cat.id }"
            :style="{ animationDelay: `${index * 0.05}s` }"
          >
            <div class="flex items-start justify-between gap-3 mb-4">
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <div
                  class="w-12 h-12 rounded-xl flex items-center justify-center text-xl text-[var(--primary)] shrink-0 bg-primary-muted border border-slate-200 dark:border-[var(--glass-border)]"
                >
                  <CategoryIcon :category-name="cat.name" size-class="h-6 w-6" />
                </div>
                <div class="min-w-0 flex-1">
                  <h3 class="font-semibold text-[var(--primary)] truncate">{{ cat.name }}</h3>
                  <p class="text-xs text-[var(--text-secondary)] mt-0.5">
                    {{ getCategoryPriceTypes(cat).length }} {{ $t('analysis.priceType') }}
                  </p>
                </div>
              </div>
              <span
                class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium shrink-0 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {{ $t('dashboard.active') }}
              </span>
            </div>

            <div class="mb-4">
              <div v-if="getCategoryPriceTypes(cat).length" class="space-y-2.5">
                <div
                  v-for="pt in getCategoryPriceTypes(cat)"
                  :key="`pt-${cat.id}-${pt.id ?? pt.name}`"
                  class="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-[var(--bg-card)] px-3 py-2 text-sm dark:border-[var(--glass-border)]"
                >
                  <span class="min-w-0 flex-1 truncate text-[var(--text-primary)] font-medium" :title="pt.name">
                    {{ pt.name }}
                  </span>
                  <span
                    v-if="pt.trade_type"
                    class="rounded-full px-2.5 py-1 text-xs font-semibold"
                    :class="pt.trade_type === 'buy' ? 'text-emerald-400 bg-emerald-500/15' : 'text-rose-400 bg-rose-500/15'"
                  >
                    {{ pt.trade_type === 'buy' ? $t('bulkUpdate.buy') : $t('bulkUpdate.sell') }}
                  </span>
                  <router-link
                    v-if="pt.id != null"
                    :to="`/categories/${cat.id}/price-types/${pt.id}/edit`"
                    class="rounded-lg border border-[var(--primary)]/40 px-3 py-1.5 text-xs font-semibold text-[var(--primary)] hover:bg-primary-muted transition-colors"
                  >
                    {{ $t('common.edit') }}
                  </router-link>
                  <button
                    v-if="pt.id != null && auth.canDeleteItems"
                    type="button"
                    class="rounded-lg border border-red-500/40 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-60"
                    :disabled="deletingPriceTypeId === pt.id"
                    @click="deletePriceType(cat.id, pt)"
                  >
                    <LoadingSpinner v-if="deletingPriceTypeId === pt.id" class="w-3.5 h-3.5" />
                    <span v-else>{{ $t('common.delete') }}</span>
                  </button>
                </div>
              </div>
              <p v-else class="text-xs text-[var(--text-secondary)]">
                {{ $t('emptyState.noPrices') }}
              </p>
            </div>

            <router-link
              :to="`/categories/${cat.id}/template`"
              class="btn-luxury w-full flex items-center justify-center gap-2 py-2.5 mb-2"
            >
              <i class="fas fa-palette" />
              {{ $t('specialPrices.designTemplate') }}
            </router-link>
            <router-link
              :to="`/categories/${cat.id}/telegram-studio`"
              class="btn-luxury w-full flex items-center justify-center gap-2 py-2.5 mb-4"
            >
              <i class="fab fa-telegram-plane" />
              {{ $t('specialPrices.telegramContent') }}
            </router-link>
            <div class="flex gap-2 flex-wrap mt-auto">
              <router-link
                :ref="(el) => setAddPriceTypeRef(cat.id, el)"
                :to="`/categories/${cat.id}/price-types/new`"
                class="btn-luxury-outline text-sm py-1.5 flex-[1.35] min-w-[170px] inline-flex items-center justify-center gap-2 whitespace-nowrap"
                :aria-label="addPriceTypeLabel"
                @click="dismissPriceTypeGuide"
              >
                <i class="fas fa-plus" />
                <span>{{ addPriceTypeLabel }}</span>
              </router-link>
              <router-link :to="`/categories/${cat.id}/edit`" class="btn-luxury-outline text-sm py-1.5 flex-1 min-w-0">
                {{ $t('common.edit') }}
              </router-link>
              <button
                v-if="auth.canDeleteItems"
                type="button"
                class="btn-luxury-outline text-sm py-1.5 !border-red-500/50 !text-red-400 hover:!bg-red-500/10"
                @click="openDeleteModal(cat)"
              >
                <i class="fas fa-trash" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>

        <div
          v-else
          class="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-16 text-center shadow-sm dark:border-[var(--glass-border)] dark:bg-[var(--bg-card)] dark:shadow-none"
        >
          <div
            class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl border border-slate-200 bg-primary-muted dark:border-[var(--glass-border)]"
          >
            <i class="fas fa-tags text-4xl text-[var(--primary)] opacity-80" />
          </div>
          <h3 class="text-lg font-bold text-[var(--text-primary)] mb-2">{{ $t('emptyState.noCategories') }}</h3>
          <p class="text-sm text-[var(--text-secondary)] mb-6 max-w-sm">{{ $t('emptyState.noCategoriesDesc') }}</p>
          <button type="button" class="btn-luxury" @click="$router.push('/categories/new')">
            <i class="fas fa-plus" /> {{ $t('emptyState.createCategory') }}
          </button>
        </div>
      </section>

      <!-- Section 2: Special Offers -->
      <section class="animate-fade-in-up" style="animation-delay: 0.1s">
        <div class="flex justify-between items-center mb-5">
          <h2 class="text-lg font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <i class="fas fa-star text-[var(--primary)]" />
            {{ $t('categories.specialOffers') }}
          </h2>
          <button type="button" class="btn-luxury" @click="$router.push('/special-prices/new')">
            <i class="fas fa-plus"></i> {{ $t('emptyState.createSpecialOffer') }}
          </button>
        </div>

        <div v-if="specialPrices.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="(sp, index) in specialPrices"
            :key="'sp-' + sp.id"
            class="card-vip p-5 flex flex-col overflow-hidden hover-lift animate-fade-in-up"
            :style="{ animationDelay: `${index * 0.05}s` }"
          >
            <div class="flex items-start justify-between gap-3 mb-4">
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <div
                  class="w-12 h-12 rounded-xl flex items-center justify-center text-xl text-[var(--primary)] shrink-0 bg-primary-muted border border-slate-200 dark:border-[var(--glass-border)]"
                >
                  <i :class="sp.icon || 'fas fa-star'" />
                </div>
                <div class="min-w-0 flex-1">
                  <h3 class="font-semibold text-[var(--primary)] truncate">{{ sp.name }}</h3>
                </div>
              </div>
              <span
                class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium shrink-0 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {{ $t('dashboard.active') }}
              </span>
            </div>
            <router-link
              :to="`/special-prices/${sp.id}/template`"
              class="btn-luxury w-full flex items-center justify-center gap-2 py-2.5 mb-2"
            >
              <i class="fas fa-palette" />
              {{ $t('specialPrices.designTemplate') }}
            </router-link>
            <router-link
              :to="`/special-prices/${sp.id}/telegram-studio`"
              class="btn-luxury w-full flex items-center justify-center gap-2 py-2.5 mb-4"
            >
              <i class="fab fa-telegram-plane" />
              {{ $t('specialPrices.telegramContent') }}
            </router-link>
            <div class="flex gap-2 flex-wrap mt-auto">
              <router-link
                :to="`/special-prices/${sp.id}/history`"
                class="btn-luxury-outline text-sm py-1.5 flex-1 min-w-0"
              >
                <i class="fas fa-history" />
                {{ $t('specialPrices.history') }}
              </router-link>
            </div>
          </div>
        </div>

        <div
          v-else
          class="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-16 text-center shadow-sm dark:border-[var(--glass-border)] dark:bg-[var(--bg-card)] dark:shadow-none"
        >
          <div
            class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl border border-slate-200 bg-primary-muted dark:border-[var(--glass-border)]"
          >
            <i class="fas fa-star text-4xl text-[var(--primary)] opacity-60" style="filter: blur(1px);" />
          </div>
          <h3 class="text-lg font-bold text-[var(--text-primary)] mb-2">{{ $t('emptyState.noSpecialOffers') }}</h3>
          <p class="text-sm text-[var(--text-secondary)] mb-6 max-w-sm">{{ $t('emptyState.noSpecialOffersDesc') }}</p>
          <button type="button" class="btn-luxury-gradient" @click="$router.push('/special-prices/new')">
            <i class="fas fa-plus" /> {{ $t('emptyState.createSpecialOffer') }}
          </button>
        </div>
      </section>
    </template>

    <BaseModal
      v-model="showDeleteModal"
      :title="$t('categories.deleteConfirmTitle')"
      :aria-label="$t('categories.deleteConfirmAria')"
    >
      <p class="text-[var(--text-secondary)] mb-6">
        {{ deleteConfirmMessage }}
      </p>
      <div class="flex gap-3 justify-end">
        <button type="button" class="btn-luxury-outline" @click="showDeleteModal = false">
          {{ $t('common.cancel') }}
        </button>
        <button
          type="button"
          class="inline-flex items-center justify-center gap-2 px-6 py-2.5 font-semibold rounded-2xl transition-all duration-300 border border-red-500/50 text-red-400 hover:bg-red-500/10 focus:outline-none focus:ring-2 focus:ring-red-500/50"
          @click="confirmDelete"
        >
          <i class="fas fa-trash" aria-hidden="true" />
          {{ $t('common.delete') }}
        </button>
      </div>
    </BaseModal>

    <OnboardingGuide
      :visible="showPriceTypeGuide"
      :target="guideTargetEl"
      :title="$t('categories.priceTypeGuideTitle')"
      :message="$t('categories.priceTypeGuideMessage')"
      :dismiss-label="$t('categories.priceTypeGuideDismiss')"
      @dismiss="dismissPriceTypeGuide"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { categoryApi, specialPriceApi, priceApi, priceTypeApi, formatDrfError } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import OnboardingGuide from '@/components/ui/OnboardingGuide.vue'

defineProps({
  embedded: { type: Boolean, default: false },
})

const { t, locale } = useI18n()
const toast = useToast()
const auth = useAuthStore()
const loading = ref(true)
const categories = ref([])
const specialPrices = ref([])
const showDeleteModal = ref(false)
const categoryToDelete = ref(null)
const deletingPriceTypeId = ref(null)
const showPriceTypeGuide = ref(false)
const guideCategoryId = ref(null)
const addPriceTypeRefs = ref({})

const deleteConfirmMessage = computed(() =>
  categoryToDelete.value
    ? t('categories.deleteConfirmMessage', { name: categoryToDelete.value.name })
    : ''
)
const addPriceTypeLabel = computed(() => t('categories.addPriceType'))
const guideTargetEl = computed(() => {
  if (!guideCategoryId.value) return null
  return addPriceTypeRefs.value[guideCategoryId.value] ?? null
})

function setAddPriceTypeRef(categoryId, el) {
  if (el) {
    addPriceTypeRefs.value[categoryId] = el
  } else {
    delete addPriceTypeRefs.value[categoryId]
  }
}

const PRICE_TYPE_GUIDE_KEY = 'guideAddPriceType'
const PRICE_TYPE_GUIDE_SEEN_PREFIX = 'priceTypeGuideSeen:'

function isPriceTypeGuideSeen(categoryId) {
  return localStorage.getItem(`${PRICE_TYPE_GUIDE_SEEN_PREFIX}${categoryId}`) === '1'
}

function markPriceTypeGuideSeen(categoryId) {
  if (categoryId == null) return
  localStorage.setItem(`${PRICE_TYPE_GUIDE_SEEN_PREFIX}${categoryId}`, '1')
}

function dismissPriceTypeGuide() {
  markPriceTypeGuideSeen(guideCategoryId.value)
  showPriceTypeGuide.value = false
  guideCategoryId.value = null
}

async function maybeShowPriceTypeGuide() {
  const rawId = sessionStorage.getItem(PRICE_TYPE_GUIDE_KEY)
  if (!rawId) return
  sessionStorage.removeItem(PRICE_TYPE_GUIDE_KEY)

  const categoryId = Number(rawId)
  if (!Number.isFinite(categoryId) || isPriceTypeGuideSeen(categoryId)) return

  const category = categories.value.find((cat) => cat.id === categoryId)
  if (!category || getCategoryPriceTypes(category).length > 0) return

  guideCategoryId.value = categoryId
  await nextTick()
  if (!addPriceTypeRefs.value[categoryId]) return

  showPriceTypeGuide.value = true
}

onMounted(async () => {
  try {
    const [catRes, spRes, pricesRes] = await Promise.all([categoryApi.list(), specialPriceApi.list(), priceApi.list()])
    const rawCategories = Array.isArray(catRes.data) ? catRes.data : (catRes.data?.results ?? [])
    const rawPrices = Array.isArray(pricesRes.data) ? pricesRes.data : (pricesRes.data?.results ?? [])
    const groupedByCategory = rawPrices.reduce((acc, pt) => {
      const categoryId = pt?.category_id
      if (categoryId == null) return acc
      if (!acc[categoryId]) acc[categoryId] = []
      acc[categoryId].push({
        id: pt.id,
        name: pt.name,
        trade_type: pt.trade_type,
      })
      return acc
    }, {})
    categories.value = rawCategories.map((cat) => {
      const existing = Array.isArray(cat?.price_types) ? cat.price_types : []
      const merged = existing.length ? existing : (groupedByCategory[cat.id] ?? [])
      return { ...cat, price_types: merged }
    })
    specialPrices.value = Array.isArray(spRes.data) ? spRes.data : (spRes.data?.results ?? [])
  } catch {
    categories.value = []
    specialPrices.value = []
  } finally {
    loading.value = false
    await maybeShowPriceTypeGuide()
  }
})

function openDeleteModal(cat) {
  categoryToDelete.value = cat
  showDeleteModal.value = true
}

function getCategoryPriceTypes(category) {
  const fromNested = Array.isArray(category?.price_types)
    ? category.price_types
        .map((pt) => ({
          id: pt?.id ?? null,
          name: typeof pt?.name === 'string' ? pt.name.trim() : '',
          trade_type: typeof pt?.trade_type === 'string' ? pt.trade_type : '',
        }))
        .filter((pt) => pt.name)
    : []

  if (fromNested.length) return fromNested

  return Array.isArray(category?.price_type_names)
    ? category.price_type_names
        .map((name) => ({
          id: null,
          name: typeof name === 'string' ? name.trim() : '',
          trade_type: '',
        }))
        .filter((pt) => pt.name)
    : []
}

async function deletePriceType(categoryId, priceType) {
  if (!priceType?.id) return
  const ok = window.confirm(t('categories.deletePriceTypeConfirm', { name: priceType.name }))
  if (!ok) return

  deletingPriceTypeId.value = priceType.id
  try {
    await priceTypeApi.delete(categoryId, priceType.id)
    categories.value = categories.value.map((cat) => {
      if (cat.id !== categoryId) return cat
      const nextList = Array.isArray(cat.price_types)
        ? cat.price_types.filter((pt) => pt.id !== priceType.id)
        : cat.price_types
      return { ...cat, price_types: nextList }
    })
    toast.success(t('toast.deleteSuccess'))
  } catch (err) {
    toast.error(formatDrfError(err?.response?.data) || t('toast.serverError'))
  } finally {
    deletingPriceTypeId.value = null
  }
}

async function confirmDelete() {
  const cat = categoryToDelete.value
  if (!cat) return
  showDeleteModal.value = false
  try {
    await categoryApi.delete(cat.id)
    categories.value = categories.value.filter((c) => c.id !== cat.id)
    toast.success(t('toast.deleteSuccess'))
  } catch (err) {
    const code = err?.response?.data?.code
    if (code === 'category_protected_by_orders') {
      const count = err?.response?.data?.order_count
      toast.error(
        count
          ? t('categories.deleteBlockedByOrdersCount', { count })
          : t('categories.deleteBlockedByOrders'),
      )
    } else {
      toast.error(formatDrfError(err?.response?.data) || t('toast.serverError'))
    }
  } finally {
    categoryToDelete.value = null
  }
}
</script>
