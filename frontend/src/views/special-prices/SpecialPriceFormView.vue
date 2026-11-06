<template>
  <div>
    <nav class="mb-6">
      <router-link
        to="/categories"
        class="text-[var(--text-secondary)] hover:text-gold transition-colors inline-flex items-center gap-2"
      >
        <i class="fas" :class="isRtl ? 'fa-arrow-right' : 'fa-arrow-left'" />
        {{ $t('categories.backToList') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ $t('specialPrices.newTitle') }}</h1>
    <BaseCard
      variant="glass"
      padding="default"
      class="w-full max-w-xl animate-fade-in-up border border-[var(--glass-border)]"
    >
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div
          v-if="errors.non_field_errors"
          class="p-3 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm"
        >
          {{ errors.non_field_errors }}
        </div>

        <div>
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            {{ $t('common.name') }} <span class="text-danger">*</span>
          </label>
          <input
            v-model="form.name"
            type="text"
            class="input-luxury"
            :placeholder="$t('specialPrices.newTitle')"
            required
          />
          <p v-if="errors.name" class="text-sm text-red-400 mt-1">{{ errors.name }}</p>
        </div>

        <label class="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--border-card-hover)] bg-primary-muted p-4">
          <input v-model="form.is_double_price" type="checkbox" class="mt-1 h-5 w-5 shrink-0 accent-[var(--primary)]" />
          <span class="text-sm text-[var(--text-primary)]">{{ $t('specialPrices.doublePrice') }}</span>
        </label>

        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <label class="block text-sm font-medium text-[var(--text-secondary)]">
              {{ $t('exchange.currencyPair') }}
            </label>
            <button type="button" class="btn-luxury-outline !py-1 !px-3 !text-xs" @click="addPair">
              + {{ $t('common.create') }}
            </button>
          </div>
          <div
            v-for="(pair, index) in form.pair_inputs"
            :key="pair.rowId"
            class="rounded-xl border border-[var(--glass-border)] p-3 space-y-2"
          >
            <input
              v-model="pair.name"
              type="text"
              class="input-luxury"
              :placeholder="`${$t('common.name')} ${index + 1}`"
              required
            />
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 items-start">
              <BaseCurrencySelect
                v-model="pair.source_currency_id"
                :options="currencies"
                value-key="id"
                :placeholder="$t('specialPrices.sourceCurrency')"
                :search-placeholder="$t('common.search')"
                :empty-text="$t('emptyState.noData')"
              />
              <BaseCurrencySelect
                v-model="pair.target_currency_id"
                :options="currencies"
                value-key="id"
                :placeholder="$t('specialPrices.targetCurrency')"
                :search-placeholder="$t('common.search')"
                :empty-text="$t('emptyState.noData')"
              />
            </div>
            <select v-model="pair.trade_type" class="input-luxury" required>
              <option value="buy">{{ $t('specialPrices.buy') }}</option>
              <option value="sell">{{ $t('specialPrices.sell') }}</option>
            </select>
            <button
              type="button"
              class="btn-luxury-outline !px-3 !py-2 w-full"
              :disabled="form.pair_inputs.length === 1"
              @click="removePair(index)"
            >
              <i class="fas fa-trash"></i>
            </button>
            <p v-if="pairErrors[index]" class="text-sm text-red-400">{{ pairErrors[index] }}</p>
          </div>
          <p v-if="errors.pair_inputs" class="text-sm text-red-400 mt-1">{{ errors.pair_inputs }}</p>
        </div>

        <FloatingInput
          v-model="form.description"
          :label="$t('common.description')"
          multiline
          :rows="2"
        />

        <div class="flex gap-4 pt-2">
          <button type="submit" class="btn-luxury" :disabled="submitting || !!errors.name">
            <LoadingSpinner v-if="submitting" class="w-5 h-5" />
            {{ $t('common.save') }}
          </button>
          <router-link to="/categories" class="btn-luxury-outline">
            {{ $t('common.cancel') }}
          </router-link>
        </div>
      </form>
    </BaseCard>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { specialPriceApi } from '@/services/api'
import FloatingInput from '@/components/ui/FloatingInput.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseCurrencySelect from '@/components/ui/BaseCurrencySelect.vue'
import { useCurrenciesStore } from '@/stores/currencies'

const { t } = useI18n()
const toast = useToast()
const router = useRouter()
const currenciesStore = useCurrenciesStore()
const isRtl = computed(() => document.documentElement.dir === 'rtl')

const form = ref({
  name: '',
  pair_inputs: [{ rowId: 1, source_currency_id: '', target_currency_id: '', trade_type: 'buy', name: '' }],
  description: '',
  is_double_price: false,
})
const errors = reactive({
  name: null,
  pair_inputs: null,
  non_field_errors: null,
})
const pairErrors = ref({})
const currencies = ref([])
const submitting = ref(false)
let rowSequence = 2

function applyServerErrors(responseData) {
  if (!responseData || typeof responseData !== 'object') return
  for (const field of Object.keys(errors)) {
    const val = responseData[field]
    if (Array.isArray(val)) {
      errors[field] = val.join(' ')
    } else if (typeof val === 'string') {
      errors[field] = val
    }
  }
}

function addPair() {
  form.value.pair_inputs.push({
    rowId: rowSequence++,
    source_currency_id: '',
    target_currency_id: '',
    trade_type: 'buy',
    name: '',
  })
}

function removePair(index) {
  if (form.value.pair_inputs.length === 1) return
  form.value.pair_inputs.splice(index, 1)
}

function validatePairs() {
  const localErrors = {}
  const seen = new Set()
  const tradeTypes = new Set()
  for (const [index, pair] of form.value.pair_inputs.entries()) {
    if (!pair.name?.trim()) {
      localErrors[index] = t('validation.required')
      continue
    }
    if (!pair.source_currency_id || !pair.target_currency_id) {
      localErrors[index] = t('validation.required')
      continue
    }
    if (Number(pair.source_currency_id) === Number(pair.target_currency_id)) {
      localErrors[index] = 'Source and target currency cannot be the same.'
      continue
    }
    const key = `${pair.name.trim().toLowerCase()}-${pair.source_currency_id}-${pair.target_currency_id}-${pair.trade_type}`
    if (seen.has(key)) {
      localErrors[index] = 'Duplicate currency pair.'
      continue
    }
    seen.add(key)
    tradeTypes.add(pair.trade_type)
  }
  if (!Object.keys(localErrors).length && form.value.pair_inputs.length > 1 && tradeTypes.size === 1) {
    errors.pair_inputs = 'When multiple pairs are provided, include both buy and sell.'
    pairErrors.value = localErrors
    return false
  }
  pairErrors.value = localErrors
  errors.pair_inputs = Object.keys(localErrors).length ? t('toast.validationError') : null
  return !Object.keys(localErrors).length
}

onMounted(async () => {
  try {
    const rows = await currenciesStore.fetch()
    currencies.value = Array.isArray(rows) ? rows : []
  } catch {
    currencies.value = []
  }
})

async function handleSubmit() {
  if (!form.value.name?.trim()) {
    errors.name = t('validation.required')
    return
  }
  if (!validatePairs()) {
    return
  }
  submitting.value = true
  try {
    await specialPriceApi.create({
      name: form.value.name.trim(),
      source_currency_id: Number(form.value.pair_inputs[0].source_currency_id),
      target_currency_id: Number(form.value.pair_inputs[0].target_currency_id),
      trade_type: form.value.pair_inputs[0].trade_type,
      pair_inputs: form.value.pair_inputs.map((pair) => ({
        name: pair.name.trim(),
        source_currency_id: Number(pair.source_currency_id),
        target_currency_id: Number(pair.target_currency_id),
        trade_type: pair.trade_type,
      })),
      description: form.value.description?.trim() || '',
      is_double_price: form.value.is_double_price,
    })
    toast.success(t('toast.saveSuccess'))
    router.push('/categories')
  } catch (err) {
    const serverData = err?.response?.data
    if (serverData && typeof serverData === 'object' && err?.response?.status < 500) {
      applyServerErrors(serverData)
    } else {
      toast.error(t('toast.serverError'))
    }
  } finally {
    submitting.value = false
  }
}
</script>
