<template>
  <BaseModal
    :model-value="true"
    :title="$t('finalize.finalizeAll')"
    :aria-label="$t('finalize.finalizeAll')"
    @update:model-value="$emit('close')"
  >
    <template v-if="!results">
      <div class="flex flex-col items-center text-center">
      <p class="text-[var(--text-secondary)] mb-4 w-full">
        {{ $t('finalize.finalizeAllSummary', { categories: categoryCount, special: specialCount }) }}
      </p>

      <div v-if="enabledDestinations.length" class="flex flex-wrap gap-4 mb-4 justify-center">
        <p class="text-sm font-medium text-[var(--text-secondary)] w-full mb-1">{{ $t('finalize.preflightDestinations') }}</p>
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

      <div class="mb-4 w-full max-w-xs">
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('finalize.channel') }}</label>
        <select v-model="channelId" class="input-luxury w-full" required :disabled="!channels.length">
          <option value="">{{ $t('finalize.selectChannel') }}</option>
          <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
        </select>
        <p v-if="!channels.length" class="mt-2 text-sm text-amber-400 text-start">
          {{ $t('finalize.noChannelsHint') }}
          <router-link
            to="/telegram/send?tab=channels"
            class="underline text-gold hover:opacity-80 ms-1"
          >
            {{ $t('finalize.addChannelLink') }}
          </router-link>
        </p>
      </div>

      <div class="flex gap-3 justify-center">
        <button type="button" class="btn-luxury-outline" @click="$emit('close')">
          {{ $t('common.cancel') }}
        </button>
        <button
          type="button"
          class="btn-luxury"
          :disabled="!channelId || submitting || !canFinalize"
          @click="submit"
        >
          <LoadingSpinner v-if="submitting" class="w-5 h-5" />
          {{ $t('finalize.confirmPublish') }}
        </button>
      </div>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-col items-center text-center">
      <p class="text-[var(--text-secondary)] mb-4 w-full">{{ $t('finalize.finalizeAllResults') }}</p>
      <ul class="space-y-2 text-sm mb-4 w-full text-start">
        <li
          v-for="(r, idx) in results"
          :key="idx"
          class="flex items-center gap-2"
        >
          <i v-if="r.success" class="fas fa-check text-success"></i>
          <i v-else class="fas fa-times text-danger"></i>
          <span>{{ r.type === 'category' ? categoryName(r.id) : r.type === 'special' ? specialName(r.id) : r.error }}</span>
          <span v-if="!r.success && r.error && r.type !== 'error'" class="text-danger text-xs">— {{ r.error }}</span>
        </li>
      </ul>
      <div class="flex justify-center">
        <button type="button" class="btn-luxury" @click="done">
          {{ $t('common.close') }}
        </button>
      </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { finalizeApi, telegramApi } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import BaseModal from '@/components/ui/BaseModal.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['close', 'success'])

const auth = useAuthStore()
const channelId = ref('')
const channels = ref([])
const submitting = ref(false)
const results = ref(null)

const canFinalize = computed(() => auth.can('finalize'))

const categoryCount = computed(() => (props.data?.pending_by_category ?? []).length)
const specialCount = computed(() => (props.data?.pending_special_prices ?? []).length)
const enabledDestinations = computed(() =>
  (props.data?.publication_destinations ?? []).filter(d => d.enabled)
)

onMounted(async () => {
  try {
    const { data } = await telegramApi.channels()
    channels.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    channels.value = []
  }
})

function categoryName(id) {
  const cat = (props.data?.pending_by_category ?? []).find(c => c.category_id === id)
  return cat?.category_name ?? `#${id}`
}

function specialName(id) {
  const sp = (props.data?.pending_special_prices ?? []).find(s => s.price_history_id === id)
  return sp?.special_price_type_name ?? `#${id}`
}

async function submit() {
  if (!channelId.value) return
  submitting.value = true
  try {
    const categoryIds = (props.data?.pending_by_category ?? []).map(c => c.category_id)
    const specialIds = (props.data?.pending_special_prices ?? []).map(s => s.price_history_id)
    const { data: res } = await finalizeApi.finalizeAll({
      channel_id: Number(channelId.value),
      category_ids: categoryIds,
      special_price_history_ids: specialIds,
    })
    results.value = res?.results ?? []
  } catch (err) {
    results.value = [{ type: 'error', success: false, error: err?.response?.data?.detail ?? err?.message ?? 'Request failed' }]
  } finally {
    submitting.value = false
  }
}

function done() {
  emit('success')
  emit('close')
}
</script>
