<template>
  <div>
    <nav class="mb-6">
      <router-link to="/prices" class="text-gray-400 hover:text-gold transition-colors">
        <i class="fas fa-arrow-left mr-2"></i>{{ $t('prices.backToPrices') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-4">{{ $t('routes.updatePrice') }}</h1>
    <div v-if="loading" class="card-luxury max-w-md px-4 py-3 space-y-4">
      <BaseSkeleton variant="text" class="!max-w-[200px] !h-4" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
      <BaseSkeleton variant="text" class="!max-w-full !h-12" />
    </div>
    <div v-else-if="priceType" class="card-luxury max-w-md px-4 py-3 space-y-4">
      <p class="text-gray-400 mb-2">{{ priceType.name }}</p>
      <p class="text-sm text-gray-500 mb-4">{{ priceType.source_currency }} / {{ priceType.target_currency }} - {{ priceType.category_name }}</p>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div v-if="isDoublePrice" class="grid grid-cols-1 gap-3">
          <div class="card-buy rounded-xl p-3 border border-buy/30 bg-buy/5">
            <label class="block text-sm font-medium text-buy mb-2">{{ $t('dashboard.cashPrice') }}</label>
            <input v-model.number="cashPrice" type="number" step="0.01" min="0" class="input-luxury focus:border-buy focus:ring-2 focus:ring-buy/20" />
          </div>
          <div class="card-sell rounded-xl p-3 border border-sell/30 bg-sell/5">
            <label class="block text-sm font-medium text-sell mb-2">{{ $t('dashboard.accountPrice') }}</label>
            <input v-model.number="accountPrice" type="number" step="0.01" min="0" class="input-luxury focus:border-sell focus:ring-2 focus:ring-sell/20" />
          </div>
        </div>
        <div v-else>
          <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('prices.newPrice') }}</label>
          <input v-model.number="price" type="number" step="0.01" min="0" class="input-luxury" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('prices.notesOptional') }}</label>
          <input v-model="notes" type="text" class="input-luxury" :placeholder="$t('prices.optionalNotes')" />
        </div>
        <div class="flex gap-4">
          <button type="submit" class="btn-luxury" :disabled="submitting">
            <LoadingSpinner v-if="submitting" class="w-5 h-5" />
            <i v-else class="fas fa-save"></i>
            {{ $t('common.save') }}
          </button>
          <router-link to="/prices" class="btn-luxury-outline">{{ $t('common.cancel') }}</router-link>
        </div>
      </form>
    </div>
    <div
      v-else
      class="card-luxury max-w-md px-4 py-6 text-center text-gray-500"
    >
      {{ $t('errors.priceNotFound') }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { priceApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { usePriceDraft } from '@/composables/usePriceDraft'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)
const loading = ref(true)
const priceType = ref(null)
const price = ref('')
const cashPrice = ref('')
const accountPrice = ref('')
const notes = ref('')
const submitting = ref(false)
const draft = usePriceDraft(computed(() => `price:${id.value}`))

const isDoublePrice = computed(() => !!priceType.value?.is_double_price)

onMounted(async () => {
  if (!id.value) {
    priceType.value = null
    loading.value = false
    return
  }
  try {
    const { data } = await priceApi.get(id.value)
    priceType.value = data
    if (priceType.value) {
      if (priceType.value.cash_price != null) {
        cashPrice.value = Number(priceType.value.cash_price)
      }
      if (priceType.value.account_price != null) {
        accountPrice.value = Number(priceType.value.account_price)
      }
      if (!isDoublePrice.value && priceType.value.latest_price != null) {
        const latest = priceType.value.latest_price
        if (typeof latest === 'number') {
          price.value = Number(latest)
        } else if (latest && typeof latest === 'object' && latest.price != null) {
          price.value = Number(latest.price)
        }
      }
    }
  } catch (err) {
    if (err.response?.status === 404) {
      priceType.value = null
    } else {
      try {
        const { data } = await priceApi.list()
        const items = Array.isArray(data) ? data : (data?.results ?? [])
        priceType.value = items.find((p) => String(p.id) === String(id.value)) || null
        if (priceType.value) {
          if (priceType.value.cash_price != null) cashPrice.value = Number(priceType.value.cash_price)
          if (priceType.value.account_price != null) accountPrice.value = Number(priceType.value.account_price)
          if (!isDoublePrice.value && priceType.value.latest_price != null) {
            const latest = priceType.value.latest_price
            if (typeof latest === 'number') price.value = Number(latest)
            else if (latest && typeof latest === 'object' && latest.price != null) price.value = Number(latest.price)
          }
        }
      } catch {
        priceType.value = null
      }
    }
  } finally {
    loading.value = false
    restoreDraft()
    draftArmed = true
  }
})

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

async function handleSubmit() {
  submitting.value = true
  try {
    const body = { notes: notes.value }
    if (isDoublePrice.value) {
      if (cashPrice.value !== '' && cashPrice.value != null && !Number.isNaN(cashPrice.value)) {
        body.cash_price = cashPrice.value
      }
      if (accountPrice.value !== '' && accountPrice.value != null && !Number.isNaN(accountPrice.value)) {
        body.account_price = accountPrice.value
      }
    } else {
      body.price = price.value
    }
    await priceApi.update(id.value, body, { silent: true })
    draft.clear()
    router.push('/prices')
  } catch (error) {
    if (error.response?.status !== 401) draft.notifyNotSaved()
  } finally {
    submitting.value = false
  }
}
</script>
