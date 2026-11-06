<template>
  <div>
    <nav class="mb-6">
      <router-link to="/update" class="text-[var(--text-secondary)] hover:text-gold transition-colors">
        <i class="fas me-2" :class="$i18n.locale === 'fa' ? 'fa-arrow-right' : 'fa-arrow-left'"></i>{{ $t('priceHub.backToHub') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('specialPrices.updateTitle') }}</h1>
    <div v-if="loading" class="card-luxury max-w-md p-6 space-y-4">
      <BaseSkeleton variant="text" class="!max-w-[200px] !h-4" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
    </div>
    <form v-else-if="sp" @submit.prevent="handleSubmit" class="card-luxury space-y-4" :class="isDouble ? 'max-w-2xl' : 'max-w-md'">
      <p class="text-[var(--text-secondary)]">{{ sp.name }}</p>
      <div>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('exchange.currencyPair') }}</label>
        <select v-model.number="selectedPairId" class="input-luxury" required>
          <option v-for="pair in sp.pairs || []" :key="pair.id" :value="pair.id">
            {{ pair.name }} ({{ pair.source_currency?.code }} / {{ pair.target_currency?.code }} - {{ pair.trade_type === 'buy' ? $t('specialPrices.buy') : $t('specialPrices.sell') }})
          </option>
        </select>
      </div>
      <div v-if="isDouble" class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div class="rounded-xl border border-[var(--border-card-hover)] bg-primary-muted p-4">
          <label class="mb-2 flex items-center gap-2 text-sm font-semibold text-gold" for="special-cash-price">
            <i class="fas fa-money-bill-wave" />{{ $t('specialPrices.cashPrice') }}
          </label>
          <input
            id="special-cash-price"
            v-model.number="cashPrice"
            type="number"
            step="0.01"
            min="0"
            class="input-luxury"
            required
          />
        </div>
        <div class="rounded-xl border border-[var(--border-card-hover)] bg-primary-muted p-4">
          <label class="mb-2 flex items-center gap-2 text-sm font-semibold text-gold" for="special-account-price">
            <i class="fas fa-credit-card" />{{ $t('specialPrices.accountPrice') }}
          </label>
          <input
            id="special-account-price"
            v-model.number="accountPrice"
            type="number"
            step="0.01"
            min="0"
            class="input-luxury"
            required
          />
        </div>
      </div>
      <div v-else>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('specialPrices.price') }}</label>
        <input v-model.number="price" type="number" step="0.01" min="0" class="input-luxury" required />
      </div>
      <div>
        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('specialPrices.notesOptional') }}</label>
        <input v-model="notes" type="text" class="input-luxury" />
      </div>
      <div class="flex gap-4">
        <button type="submit" class="btn-luxury" :disabled="submitting">{{ $t('common.save') }}</button>
        <router-link to="/update" class="btn-luxury-outline">{{ $t('common.cancel') }}</router-link>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { specialPriceApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import { usePriceDraft } from '@/composables/usePriceDraft'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)
const loading = ref(true)
const sp = ref(null)
const selectedPairId = ref(null)
const price = ref('')
const cashPrice = ref('')
const accountPrice = ref('')
const isDouble = computed(() => Boolean(sp.value?.is_double_price))
const notes = ref('')
const submitting = ref(false)
const draft = usePriceDraft(computed(() => `special:${id.value}:${selectedPairId.value}`))

function num(value) {
  return value != null && value !== '' ? Number(value) : ''
}

function prefill(latest) {
  price.value = num(latest?.price)
  // Cash lives in `price` for rows saved before the two columns existed.
  cashPrice.value = num(latest?.cash_price ?? latest?.price)
  accountPrice.value = num(latest?.account_price)
  restoreDraft()
}

/** Re-apply numbers typed before a failed save, a reload or an expired session. */
function restoreDraft() {
  baseline = snapshot()
  const saved = draft.load()
  if (!saved) return
  price.value = saved.price ?? price.value
  cashPrice.value = saved.cashPrice ?? cashPrice.value
  accountPrice.value = saved.accountPrice ?? accountPrice.value
  notes.value = saved.notes ?? notes.value
  if (snapshot() !== baseline) draft.notifyRestored()
  else draft.clear()
}

const snapshot = () => JSON.stringify([price.value, cashPrice.value, accountPrice.value, notes.value])
let baseline = ''
let draftArmed = false
watch([price, cashPrice, accountPrice, notes], () => {
  if (!draftArmed) return
  if (snapshot() === baseline) {
    draft.clear()
    return
  }
  draft.save({
    price: price.value,
    cashPrice: cashPrice.value,
    accountPrice: accountPrice.value,
    notes: notes.value,
  })
})

onMounted(async () => {
  try {
    const { data } = await specialPriceApi.get(id.value)
    sp.value = data
    if (Array.isArray(data?.pairs) && data.pairs.length) {
      selectedPairId.value = data.pairs[0].id
      prefill(data.pairs[0]?.latest_price)
    } else {
      prefill(data?.latest_price)
    }
  } catch {
    sp.value = null
  } finally {
    loading.value = false
    draftArmed = true
  }
})

watch(selectedPairId, (pairId) => {
  const pair = sp.value?.pairs?.find((item) => item.id === pairId)
  prefill(pair?.latest_price)
})

async function handleSubmit() {
  if (!selectedPairId.value) return
  submitting.value = true
  try {
    await specialPriceApi.updatePrice(id.value, {
      pair_id: selectedPairId.value,
      ...(isDouble.value
        ? { cash_price: cashPrice.value, account_price: accountPrice.value }
        : { price: price.value }),
      notes: notes.value,
    }, { silent: true })
    draft.clear()
    router.push('/update')
  } catch (error) {
    if (error.response?.status !== 401) draft.notifyNotSaved()
  } finally {
    submitting.value = false
  }
}
</script>
