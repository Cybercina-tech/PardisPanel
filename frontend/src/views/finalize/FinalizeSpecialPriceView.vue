<template>
  <div class="flex flex-col items-center">
    <nav class="mb-6 w-full">
      <router-link to="/finalize" class="text-gray-400 hover:text-gold transition-colors">
        <i class="fas" :class="isRtl ? 'fa-arrow-right' : 'fa-arrow-left'" />
        <span class="ms-2">{{ $t('finalize.backToList') }}</span>
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-6 w-full text-center">{{ $t('routes.finalizeSpecialPrice') }}</h1>

    <div v-if="loading" class="card-luxury max-w-lg w-full p-6 space-y-4">
      <BaseSkeleton variant="text" class="!max-w-full !h-4" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
    </div>

    <template v-else>
      <!-- Comparison card -->
      <div v-if="specialItem" class="card-luxury max-w-lg w-full p-4 mb-6">
        <h3 class="font-semibold text-gold mb-3">{{ $t('finalize.comparisonSummary') }}</h3>
        <div class="text-sm">
          <div v-if="specialItem.is_double_price" class="flex flex-wrap items-baseline gap-x-4 gap-y-0.5">
            <span class="text-gold font-bold">
              {{ $t('specialPrices.cashPrice') }}: {{ formatPrice(specialItem.cash_price ?? specialItem.price) }}
            </span>
            <span class="text-gold font-bold">
              {{ $t('specialPrices.accountPrice') }}: {{ formatPrice(specialItem.account_price) }}
            </span>
          </div>
          <div v-else-if="specialItem.previous_price != null" class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span class="text-[var(--text-secondary)]">{{ $t('finalize.oldPrice') }}: {{ formatPrice(specialItem.previous_price) }}</span>
            <span class="text-gold font-bold">{{ $t('finalize.newPrice') }}: {{ formatPrice(specialItem.price) }}</span>
            <span :class="priceChangeClass(specialItem)" class="font-medium">{{ $t('finalize.change') }}: {{ formatPriceChange(specialItem) }}</span>
          </div>
          <div v-else>
            <span class="text-gold font-bold">{{ $t('finalize.newPrice') }}: {{ formatPrice(specialItem.price) }}</span>
            <span class="text-[var(--text-secondary)] text-xs ms-1">({{ $t('finalize.firstPublication') }})</span>
          </div>
          <p v-if="specialItem.created_at" class="text-xs text-[var(--text-secondary)] mt-2">
            {{ $t('finalize.lastDraftUpdate') }}: {{ formatDate(specialItem.created_at) }}
          </p>
        </div>
      </div>

      <!-- Pre-flight checklist -->
      <div v-if="enabledDestinations.length" class="card-luxury max-w-lg w-full p-4 mb-6">
        <p class="text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('finalize.preflightDestinations') }}</p>
        <div class="flex flex-wrap gap-4">
          <span
            v-for="d in enabledDestinations"
            :key="d.id"
            class="inline-flex items-center gap-2 text-sm"
          >
            <i v-if="d.id === 'telegram'" class="fab fa-telegram-plane text-xl text-[var(--text-secondary)]"></i>
            <i v-else class="fas fa-paper-plane text-lg text-[var(--text-secondary)]"></i>
            <span>{{ d.label }}</span>
          </span>
        </div>
      </div>

    <form @submit.prevent="openConfirmModal" class="card-luxury max-w-lg w-full space-y-4">
      <div>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('finalize.channel') }}</label>
        <select v-model="channelId" class="input-luxury" required :disabled="!channels.length">
          <option value="">{{ $t('finalize.selectChannel') }}</option>
          <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
        </select>
        <p v-if="!channels.length" class="mt-2 text-sm text-amber-400">
          {{ $t('finalize.noChannelsHint') }}
          <router-link
            to="/telegram/send?tab=channels"
            class="underline text-gold hover:opacity-80 ms-1"
          >
            {{ $t('finalize.addChannelLink') }}
          </router-link>
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('finalize.notes') }}</label>
        <input v-model="notes" type="text" class="input-luxury" />
      </div>
      <div class="flex gap-4 justify-center">
        <button type="submit" class="btn-luxury" :disabled="submitting">
          <LoadingSpinner v-if="submitting" class="w-5 h-5" />
          {{ $t('finalize.startFinalize') }}
        </button>
        <button
          type="button"
          class="btn-luxury-outline"
          :disabled="isDownloading('special', specialPriceHistoryId)"
          @click="downloadBanner('special', specialPriceHistoryId)"
        >
          <LoadingSpinner v-if="isDownloading('special', specialPriceHistoryId)" class="w-4 h-4" />
          <i v-else class="fas fa-download" />
          {{ isDownloading('special', specialPriceHistoryId) ? $t('finalize.banner.downloading') : $t('finalize.banner.download') }}
        </button>
        <router-link to="/finalize" class="btn-luxury-outline">{{ $t('common.cancel') }}</router-link>
      </div>
    </form>

    <BaseModal
      v-model="confirmModalOpen"
      :title="$t('finalize.confirmTitle')"
      :aria-label="$t('finalize.confirmTitle')"
    >
      <p class="text-[var(--text-secondary)] mb-4">
        {{ $t('finalize.confirmSpecialSummary', { name: specialItem?.special_price_type_name ?? '' }) }}
      </p>
      <div v-if="enabledDestinations.length" class="flex flex-wrap gap-4 mb-4">
        <span
          v-for="d in enabledDestinations"
          :key="d.id"
          class="inline-flex items-center gap-2 text-sm"
        >
          <i v-if="d.id === 'telegram'" class="fab fa-telegram-plane text-xl"></i>
          <i v-else class="fas fa-paper-plane text-lg"></i>
          <span>{{ d.label }}</span>
        </span>
      </div>
      <div class="flex gap-3 justify-end">
        <button type="button" class="btn-luxury-outline" @click="confirmModalOpen = false">
          {{ $t('common.cancel') }}
        </button>
        <button type="button" class="btn-luxury" :disabled="submitting" @click="onConfirmPublish">
          <LoadingSpinner v-if="submitting" class="w-5 h-5" />
          {{ $t('finalize.confirmPublish') }}
        </button>
      </div>
    </BaseModal>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { finalizeApi, telegramApi } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { useI18n } from 'vue-i18n'
import { formatAppDecimal, createAppDateTimeFormat } from '@/utils/localeFormat.js'
import { useBannerDownload } from '@/composables/useBannerDownload'

const { locale } = useI18n()
const { downloadBanner, isDownloading } = useBannerDownload()
const route = useRoute()
const router = useRouter()
const specialPriceHistoryId = computed(() => route.params.id)
const isRtl = computed(() => document.documentElement.dir === 'rtl')

const loading = ref(true)
const channels = ref([])
const channelId = ref('')
const notes = ref('')
const submitting = ref(false)
const specialItem = ref(null)
const publicationDestinations = ref([])
const confirmModalOpen = ref(false)

const enabledDestinations = computed(() =>
  (publicationDestinations.value || []).filter(d => d.enabled)
)

function formatPrice(value) {
  if (value == null || value === '') return '—'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(num)) return String(value)
  const appLoc = locale.value === 'fa' ? 'fa' : 'en'
  return formatAppDecimal(appLoc, num, 2)
}

function formatPriceChange(item) {
  const prev = item.previous_price != null ? parseFloat(item.previous_price) : null
  const next = item.price != null ? parseFloat(item.price) : null
  if (prev == null || next == null || Number.isNaN(prev) || Number.isNaN(next)) return '—'
  const diff = next - prev
  const sign = diff >= 0 ? '+' : ''
  return sign + formatPrice(String(diff))
}

function priceChangeClass(item) {
  const prev = item.previous_price != null ? parseFloat(item.previous_price) : null
  const next = item.price != null ? parseFloat(item.price) : null
  if (prev == null || next == null || Number.isNaN(prev) || Number.isNaN(next)) return 'text-[var(--text-secondary)]'
  const diff = next - prev
  if (diff > 0) return 'text-success'
  if (diff < 0) return 'text-danger'
  return 'text-[var(--text-secondary)]'
}

function formatDate(isoString) {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    const appLoc = locale.value === 'fa' ? 'fa' : 'en'
    return createAppDateTimeFormat(appLoc, { dateStyle: 'short', timeStyle: 'short' }).format(d)
  } catch {
    return isoString
  }
}

onMounted(async () => {
  try {
    const [dashRes, chRes] = await Promise.all([
      finalizeApi.dashboard(),
      telegramApi.channels(),
    ])
    const dash = dashRes.data
    publicationDestinations.value = dash?.publication_destinations ?? []
    const id = specialPriceHistoryId.value
    const item = dash?.pending_special_prices?.find(
      sp => String(sp.price_history_id) === String(id)
    )
    specialItem.value = item ?? null
    channels.value = Array.isArray(chRes.data) ? chRes.data : (chRes.data?.results ?? [])
  } catch {
    channels.value = []
  } finally {
    loading.value = false
  }
})

async function handleSubmit() {
  submitting.value = true
  try {
    await finalizeApi.finalizeSpecialPrice(specialPriceHistoryId.value, {
      channel_id: Number(channelId.value),
      notes: notes.value,
    })
    router.push('/finalize')
  } finally {
    submitting.value = false
  }
}

function openConfirmModal() {
  if (!channelId.value) return
  confirmModalOpen.value = true
}

function onConfirmPublish() {
  confirmModalOpen.value = false
  handleSubmit()
}
</script>
