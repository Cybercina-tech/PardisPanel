<template>
  <div>
    <nav class="mb-6">
      <router-link to="/categories" class="text-gray-400 hover:text-gold transition-colors">
        <i class="fas me-2" :class="$i18n.locale === 'fa' ? 'fa-arrow-right' : 'fa-arrow-left'"></i>{{ $t('priceTypeForm.backToCategories') }}
      </router-link>
    </nav>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ isEdit ? $t('priceTypeForm.pageTitleEdit') : $t('priceTypeForm.pageTitleCreate') }}</h1>
    <form @submit.prevent="handleSubmit" class="card-luxury max-w-md space-y-4">
      <p v-if="formError" class="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
        {{ formError }}
      </p>
      <div>
        <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('common.name') }}</label>
        <input v-model="form.name" type="text" class="input-luxury" required />
        <p v-if="fieldErrors.name" class="mt-1 text-xs text-red-300">{{ fieldErrors.name }}</p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('priceTypeForm.sourceCurrency') }}</label>
        <BaseCurrencySelect
          v-model="form.source_currency_id"
          :options="currencies"
          value-key="id"
          :placeholder="$t('priceTypeForm.sourceCurrency')"
          :search-placeholder="$t('common.search')"
          :empty-text="$t('emptyState.noData')"
        />
        <p v-if="fieldErrors.source_currency_id || fieldErrors.source_currency" class="mt-1 text-xs text-red-300">
          {{ fieldErrors.source_currency_id || fieldErrors.source_currency }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('priceTypeForm.targetCurrency') }}</label>
        <BaseCurrencySelect
          v-model="form.target_currency_id"
          :options="currencies"
          value-key="id"
          :placeholder="$t('priceTypeForm.targetCurrency')"
          :search-placeholder="$t('common.search')"
          :empty-text="$t('emptyState.noData')"
        />
        <p v-if="fieldErrors.target_currency_id || fieldErrors.target_currency" class="mt-1 text-xs text-red-300">
          {{ fieldErrors.target_currency_id || fieldErrors.target_currency }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('priceTypeForm.tradeType') }}</label>
        <p class="mb-2 text-xs text-[var(--text-secondary)]">
          {{ $t('priceTypeForm.tradeTypeHelp') }}
        </p>
        <div class="grid grid-cols-2 gap-2">
          <button
            type="button"
            class="rounded-lg border px-3 py-2 text-sm font-medium transition"
            :class="form.trade_type === 'buy'
              ? 'border-emerald-500/60 bg-emerald-500/15 text-emerald-300'
              : 'border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'"
            @click="form.trade_type = 'buy'"
          >
            {{ $t('priceTypeForm.buy') }}
          </button>
          <button
            type="button"
            class="rounded-lg border px-3 py-2 text-sm font-medium transition"
            :class="form.trade_type === 'sell'
              ? 'border-rose-500/60 bg-rose-500/15 text-rose-300'
              : 'border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'"
            @click="form.trade_type = 'sell'"
          >
            {{ $t('priceTypeForm.sell') }}
          </button>
        </div>
        <input v-model="form.trade_type" type="hidden" required />
        <p v-if="fieldErrors.trade_type" class="mt-1 text-xs text-red-300">{{ fieldErrors.trade_type }}</p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('priceTypeForm.descriptionOptional') }}</label>
        <input v-model="form.description" type="text" class="input-luxury" />
        <p v-if="fieldErrors.description" class="mt-1 text-xs text-red-300">{{ fieldErrors.description }}</p>
      </div>
      <div class="flex gap-4">
        <button type="submit" class="btn-luxury" :disabled="submitting">
          <LoadingSpinner v-if="submitting" class="w-5 h-5" />
          {{ $t('common.save') }}
        </button>
        <router-link to="/categories" class="btn-luxury-outline">{{ $t('common.cancel') }}</router-link>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { categoryApi, priceTypeApi, getApiErrorDetails } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import BaseCurrencySelect from '@/components/ui/BaseCurrencySelect.vue'
import { useCurrenciesStore } from '@/stores/currencies'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { t } = useI18n()
const currenciesStore = useCurrenciesStore()
const categoryId = computed(() => route.params.id)
const priceTypeId = computed(() => route.params.priceTypeId)
const isEdit = computed(() => !!priceTypeId.value)
const form = ref({
  name: '',
  source_currency_id: '',
  target_currency_id: '',
  trade_type: 'buy',
  description: '',
})
const currencies = ref([])
const submitting = ref(false)
const formError = ref('')
const fieldErrors = ref({})

onMounted(async () => {
  try {
    const rows = await currenciesStore.fetch()
    currencies.value = Array.isArray(rows) ? rows : []
    if (currencies.value.length) {
      if (!form.value.source_currency_id) form.value.source_currency_id = currencies.value[0].id
      if (!form.value.target_currency_id) form.value.target_currency_id = currencies.value[0].id
    }
  } catch (e) {
    currencies.value = []
    formError.value = getApiErrorDetails(e).message || t('priceTypeForm.loadCurrenciesError')
  }

  if (isEdit.value) {
    try {
      const { data } = await priceTypeApi.get(categoryId.value, priceTypeId.value)
      form.value = {
        name: data?.name ?? '',
        source_currency_id: data?.source_currency?.id ?? data?.source_currency_id ?? '',
        target_currency_id: data?.target_currency?.id ?? data?.target_currency_id ?? '',
        trade_type: data?.trade_type ?? 'buy',
        description: data?.description ?? '',
      }
    } catch (e) {
      const msg = getApiErrorDetails(e).message || t('priceTypeForm.loadPriceTypeError')
      formError.value = msg
      toast.error(msg)
    }
  }
})

async function handleSubmit() {
  formError.value = ''
  fieldErrors.value = {}
  if (!categoryId.value) {
    formError.value = t('priceTypeForm.missingCategoryId')
    return
  }
  if (!form.value.source_currency_id || !form.value.target_currency_id) {
    formError.value = t('priceTypeForm.selectBothCurrencies')
    return
  }
  submitting.value = true
  try {
    const payload = {
      ...form.value,
      source_currency_id: Number(form.value.source_currency_id),
      target_currency_id: Number(form.value.target_currency_id),
    }
    if (isEdit.value) {
      await priceTypeApi.update(categoryId.value, priceTypeId.value, payload)
    } else {
      await categoryApi.addPriceType(categoryId.value, payload)
    }
    toast.success(isEdit.value ? t('priceTypeForm.updateSuccess') : t('priceTypeForm.createSuccess'))
    router.push('/categories')
  } catch (e) {
    const details = getApiErrorDetails(e)
    fieldErrors.value = details.fieldErrors || {}
    const msg = details.message || t('priceTypeForm.saveError')
    formError.value = msg
    toast.error(msg)
  } finally {
    submitting.value = false
  }
}
</script>
