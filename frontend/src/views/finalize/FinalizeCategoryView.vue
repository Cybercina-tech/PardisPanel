<template>
  <div class="flex flex-col items-center">
    <nav class="mb-6 w-full">
      <router-link to="/finalize" class="text-gray-400 hover:text-gold transition-colors">
        <i class="fas" :class="isRtl ? 'fa-arrow-right' : 'fa-arrow-left'" />
        <span class="ms-2">{{ $t('finalize.backToList') }}</span>
      </router-link>
    </nav>

    <h1 class="text-2xl font-bold text-gold mb-6 w-full text-center">{{ $t('finalize.title') }}</h1>

    <div v-if="loading" class="card-luxury max-w-lg w-full p-6 space-y-4">
      <BaseSkeleton variant="text" class="!max-w-full !h-4" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
    </div>

    <template v-else>
      <!-- Comparison summary + Pre-flight (config phase) -->
      <div v-if="phase === 'config'" class="max-w-lg w-full space-y-6">
        <!-- Comparison summary -->
        <div v-if="categoryPending?.pending_prices?.length" class="card-luxury p-4">
          <h3 class="font-semibold text-gold mb-3">{{ $t('finalize.comparisonSummary') }}</h3>
          <ul class="space-y-2 text-sm">
            <li
              v-for="pp in categoryPending.pending_prices"
              :key="pp.price_history_id"
              class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5"
            >
              <span class="font-medium text-[var(--text-primary)]">{{ pp.price_type_name }}</span>
              <template v-if="pp.previous_price != null">
                <span class="text-[var(--text-secondary)]">{{ $t('finalize.oldPrice') }}: {{ formatPrice(pp.previous_price) }}</span>
                <span class="text-gold font-bold">{{ $t('finalize.newPrice') }}: {{ formatPrice(pp.price) }}</span>
                <span :class="priceChangeClass(pp)" class="font-medium">{{ formatPriceChange(pp) }}</span>
              </template>
              <template v-else>
                <span class="text-gold font-bold">{{ formatPrice(pp.price) }}</span>
                <span class="text-[var(--text-secondary)]">({{ $t('finalize.firstPublication') }})</span>
              </template>
            </li>
          </ul>
        </div>

        <!-- Pre-flight checklist -->
        <div v-if="enabledDestinations.length" class="card-luxury p-4">
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

      <!-- Configuration form (pre-finalization) -->
      <form @submit.prevent="openConfirmModal" class="card-luxury max-w-lg space-y-4">
        <p class="text-[var(--text-secondary)] mb-4">
          {{ $t('finalize.pendingCount', { count: pendingCount }) }}
        </p>

        <div>
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            {{ $t('finalize.channel') }}
          </label>
          <select v-model="channelId" class="input-luxury" required>
            <option value="">{{ $t('finalize.selectChannel') }}</option>
            <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
          </select>
        </div>

        <FloatingInput
          v-model="notes"
          :label="$t('finalize.notes')"
        />

        <div class="flex gap-4 justify-center">
          <button type="button" class="btn-luxury" :disabled="!channelId" @click="openConfirmModal">
            <i class="fas fa-play" />
            {{ $t('finalize.startFinalize') }}
          </button>
          <router-link to="/finalize" class="btn-luxury-outline">
            {{ $t('common.cancel') }}
          </router-link>
        </div>
      </form>
      </div>

      <!-- Step-by-step progress -->
      <div v-else class="card-luxury max-w-lg w-full space-y-6">
        <div class="space-y-3">
          <div
            v-for="(step, idx) in steps"
            :key="step.key"
            class="flex items-center gap-4 p-4 rounded-xl border transition-all duration-300"
            :style="stepStyle(step)"
          >
            <div class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300"
              :class="stepIconBg(step)"
            >
              <i v-if="step.status === 'success'" class="fas fa-check text-white" />
              <i v-else-if="step.status === 'failed'" class="fas fa-times text-white" />
              <span v-else-if="step.status === 'inProgress'"
                class="inline-block w-5 h-5 border-2 border-gold border-t-transparent rounded-full animate-spin"
              />
              <span v-else class="text-sm font-bold text-[var(--text-secondary)]">{{ idx + 1 }}</span>
            </div>

            <div class="flex-1 min-w-0">
              <p class="font-medium" :class="step.status === 'success' ? 'text-success' : step.status === 'failed' ? 'text-danger' : step.status === 'inProgress' ? 'text-gold' : 'text-[var(--text-secondary)]'">
                {{ $t(`finalize.step.${step.key}`) }}
              </p>
              <p v-if="step.detail" class="text-xs text-[var(--text-secondary)] mt-0.5 truncate">{{ step.detail }}</p>
            </div>

            <div class="flex-shrink-0">
              <span class="text-xs font-medium px-2 py-1 rounded-lg"
                :class="statusBadge(step.status)"
              >
                {{ $t(`finalize.status.${step.status}`) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Overall progress bar -->
        <div class="relative h-2 bg-[var(--bg-input)] rounded-full overflow-hidden">
          <div
            class="absolute inset-y-0 start-0 rounded-full transition-all duration-500 ease-out"
            :class="overallFailed ? 'bg-danger' : 'bg-gradient-to-r from-gold to-success'"
            :style="{ width: progressPercent + '%' }"
          />
        </div>

        <!-- Completion message -->
        <div v-if="phase === 'done' && telegramNotSentReason" class="text-center py-4">
          <i class="fas fa-exclamation-triangle text-4xl text-gold mb-3" />
          <p class="text-lg font-bold text-gold">{{ $t('finalize.completedNoTelegram') }}</p>
          <p class="text-xs text-[var(--text-secondary)] mt-1">{{ telegramNotSentReason }}</p>
        </div>
        <div v-else-if="phase === 'done'" class="text-center py-4">
          <i class="fas fa-check-circle text-4xl text-success mb-3" />
          <p class="text-lg font-bold text-success">{{ $t('finalize.completed') }}</p>
        </div>
        <div v-else-if="phase === 'error'" class="text-center py-4">
          <i class="fas fa-exclamation-triangle text-4xl text-danger mb-3" />
          <p class="text-lg font-bold text-danger">{{ $t('finalize.failed') }}</p>
        </div>

        <div class="flex gap-4 pt-2 justify-center">
          <router-link v-if="phase === 'done' || phase === 'error'" to="/finalize" class="btn-luxury">
            <i class="fas fa-arrow-left" />
            {{ $t('common.back') }}
          </router-link>
          <button v-if="phase === 'error'" class="btn-luxury-outline" @click="retryFinalize">
            <i class="fas fa-redo" />
            {{ $t('common.submit') }}
          </button>
        </div>
      </div>
    </template>

    <BaseModal
      v-model="confirmModalOpen"
      :title="$t('finalize.confirmTitle')"
      :aria-label="$t('finalize.confirmTitle')"
    >
      <p class="text-[var(--text-secondary)] mb-4">
        {{ $t('finalize.confirmCategorySummary', { count: pendingCount, name: categoryPending?.category_name ?? '' }) }}
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
        <button type="button" class="btn-luxury" @click="onConfirmPublish">
          {{ $t('finalize.confirmPublish') }}
        </button>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { finalizeApi, telegramApi, getApiErrorDetails } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import FloatingInput from '@/components/ui/FloatingInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { formatAppDecimal } from '@/utils/localeFormat.js'

const { t, locale } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const categoryId = computed(() => route.params.id)
const isRtl = computed(() => document.documentElement.dir === 'rtl')

const loading = ref(true)
const channels = ref([])
const pendingCount = ref(0)
const channelId = ref('')
const notes = ref('')
const phase = ref('config')
const categoryPending = ref(null)
const publicationDestinations = ref([])
const confirmModalOpen = ref(false)

const enabledDestinations = computed(() =>
  (publicationDestinations.value || []).filter(d => d.enabled)
)

const STEP_KEYS = ['validate', 'render', 'send', 'confirm']

const steps = reactive(
  STEP_KEYS.map(key => ({ key, status: 'pending', detail: '' }))
)

// Set when the backend saved the finalization but Telegram rejected the post
// (non-strict mode returns 200 with message_sent: false).
const telegramNotSentReason = ref('')

const completedSteps = computed(() => steps.filter(s => s.status === 'success').length)
const overallFailed = computed(() => steps.some(s => s.status === 'failed'))
const progressPercent = computed(() => Math.round((completedSteps.value / steps.length) * 100))

function stepStyle(step) {
  if (step.status === 'success') return { borderColor: 'rgba(16, 185, 129, 0.3)', background: 'rgba(16, 185, 129, 0.05)' }
  if (step.status === 'failed') return { borderColor: 'rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.05)' }
  if (step.status === 'inProgress') return { borderColor: 'var(--border-card-hover)', background: 'var(--primary-muted)' }
  return { borderColor: 'var(--border-card)', background: 'transparent' }
}

function stepIconBg(step) {
  if (step.status === 'success') return 'bg-success'
  if (step.status === 'failed') return 'bg-danger'
  if (step.status === 'inProgress') return 'bg-transparent'
  return 'bg-[var(--bg-input)]'
}

function statusBadge(status) {
  if (status === 'success') return 'bg-success/10 text-success'
  if (status === 'failed') return 'bg-danger/10 text-danger'
  if (status === 'inProgress') return 'bg-gold/10 text-gold'
  return 'bg-gray-500/10 text-gray-400'
}

onMounted(async () => {
  try {
    const [dashRes, chRes] = await Promise.all([
      finalizeApi.dashboard(),
      telegramApi.channels(),
    ])
    const dash = dashRes.data
    publicationDestinations.value = dash?.publication_destinations ?? []
    const cat = dash?.pending_by_category?.find(
      c => String(c.category_id) === String(categoryId.value)
    )
    categoryPending.value = cat ?? null
    pendingCount.value = cat?.pending_prices?.length ?? 0
    channels.value = chRes.data ?? []
  } catch (error) {
    channels.value = []
    toast.error(getApiErrorDetails(error).message)
  } finally {
    loading.value = false
  }
})

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

function openConfirmModal() {
  if (!channelId.value) return
  confirmModalOpen.value = true
}

function onConfirmPublish() {
  confirmModalOpen.value = false
  startFinalize()
}

async function runStep(idx, fn) {
  steps[idx].status = 'inProgress'
  try {
    const result = await fn()
    steps[idx].status = 'success'
    steps[idx].detail = result ?? ''
    return true
  } catch (err) {
    steps[idx].status = 'failed'
    steps[idx].detail = getApiErrorDetails(err).message ?? err.message ?? ''
    return false
  }
}

async function startFinalize() {
  phase.value = 'progress'
  telegramNotSentReason.value = ''
  steps.forEach(s => { s.status = 'pending'; s.detail = '' })

  const ok1 = await runStep(0, async () => {
    await new Promise(r => setTimeout(r, 400))
    return t('finalize.status.success')
  })
  if (!ok1) { phase.value = 'error'; return }

  const ok2 = await runStep(1, async () => {
    await new Promise(r => setTimeout(r, 600))
    return t('finalize.status.success')
  })
  if (!ok2) { phase.value = 'error'; return }

  const ok3 = await runStep(2, async () => {
    const { data } = await finalizeApi.finalizeCategory(categoryId.value, {
      channel_id: Number(channelId.value),
      notes: notes.value,
    })
    // A 200 only means the finalization was saved. Outside strict mode the backend
    // still persists it when the channel refused the post, so report what actually
    // reached Telegram instead of assuming the step succeeded.
    if (data && data.message_sent === false) {
      telegramNotSentReason.value = data.telegram_response || t('finalize.telegramNotSent')
    }
    return t('finalize.status.success')
  })
  if (!ok3) { phase.value = 'error'; return }

  if (telegramNotSentReason.value) {
    steps[2].status = 'failed'
    steps[2].detail = telegramNotSentReason.value
  }

  const ok4 = await runStep(3, async () => {
    await new Promise(r => setTimeout(r, 300))
    return t('finalize.status.success')
  })
  if (!ok4) { phase.value = 'error'; return }

  // Prices are finalized either way, so the flow ends in 'done'; the warning block
  // below tells the operator the Telegram post has to be retried from the hub.
  phase.value = 'done'
  if (telegramNotSentReason.value) {
    toast.warning(t('finalize.telegramNotSent'))
  } else {
    toast.success(t('toast.finalizeSuccess'))
  }
}

function retryFinalize() {
  startFinalize()
}
</script>
