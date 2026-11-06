<template>
  <div class="min-h-[calc(100vh-10rem)] w-full flex flex-col items-center py-6">
    <div class="w-full max-w-6xl px-4 relative">
      <nav class="mb-4">
        <router-link to="/categories" class="text-[var(--text-secondary)] hover:text-gold transition-colors inline-flex items-center gap-2">
          <i class="fas fa-arrow-left icon-back me-2" />
          <span>{{ $t('categories.backToList') }}</span>
        </router-link>
      </nav>

      <h1 class="text-2xl font-bold text-gold mb-6 text-center lg:text-start">
        {{ isEdit ? $t('categories.editTitle') : $t('categories.newTitle') }}
      </h1>

      <div class="grid grid-cols-1 lg:grid-cols-[22rem_minmax(0,1fr)] gap-5 items-start">
        <BaseCard
          v-if="!isEdit"
          variant="glass"
          padding="default"
          class="order-1 lg:order-none animate-fade-in-up border border-[var(--glass-border)]"
        >
          <div class="space-y-3">
            <div>
              <h2 class="text-lg font-semibold text-[var(--text-primary)]">
                {{ $t('categories.readyCategoriesTitle') }}
              </h2>
              <p class="text-sm text-[var(--text-secondary)] mt-1">
                {{ $t('categories.readyCategoriesHint') }}
              </p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-2.5">
              <button
                v-for="preset in categoryPresets"
                :key="preset.code"
                type="button"
                class="w-full rounded-xl border border-[var(--glass-border)] bg-[var(--bg-card)] px-3 py-2.5 text-start transition-colors hover:border-[var(--primary)] hover:bg-primary-muted disabled:opacity-70 disabled:cursor-not-allowed"
                :disabled="!!activePresetCode || submitting"
                @click="createPresetCategory(preset)"
              >
                <div class="flex items-center gap-2">
                  <span class="w-8 h-8 rounded-lg bg-primary-muted border border-[var(--glass-border)] inline-flex items-center justify-center text-[var(--primary)]">
                    <LoadingSpinner v-if="activePresetCode === preset.code" class="w-4 h-4" />
                    <img
                      v-else
                      :src="preset.iconSrc"
                      :alt="`${preset.code} icon`"
                      class="h-4 w-4 object-contain"
                    />
                  </span>
                  <div class="min-w-0">
                    <div class="font-semibold text-[var(--text-primary)] truncate">
                      {{ preset.label }}
                    </div>
                    <div class="text-xs text-[var(--text-secondary)] mt-0.5 truncate">
                      {{ preset.code }}
                    </div>
                  </div>
                </div>
              </button>
            </div>
          </div>
        </BaseCard>

        <BaseCard
          variant="glass"
          padding="default"
          class="w-full max-w-2xl justify-self-center lg:justify-self-stretch animate-fade-in-up border border-[var(--glass-border)]"
        >
          <form @submit.prevent="handleSubmit" class="space-y-5">
            <div v-if="errors.non_field_errors" class="p-3 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm">
              {{ errors.non_field_errors }}
            </div>

            <FloatingInput
              v-model="form.name"
              :label="$t('common.name')"
              :error="errors.name"
              :rules="[v => !v?.trim() ? $t('validation.required') : true]"
              required
              @validate="e => errors.name = e"
            />

            <FloatingInput
              v-model="form.description"
              :label="$t('common.description')"
              multiline
              :rows="3"
            />

            <div class="flex gap-4 pt-2">
              <button type="submit" class="btn-luxury" :disabled="submitting || !!errors.name || !!activePresetCode">
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
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { categoryApi, getApiErrorDetails } from '@/services/api'
import FloatingInput from '@/components/ui/FloatingInput.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import usdIcon from '@/assets/currency-icons/usd.svg'
import eurIcon from '@/assets/currency-icons/eur.svg'
import gbpIcon from '@/assets/currency-icons/gbp.svg'
import chfIcon from '@/assets/currency-icons/chf.svg'
import cadIcon from '@/assets/currency-icons/cad.svg'
import audIcon from '@/assets/currency-icons/aud.svg'
import nzdIcon from '@/assets/currency-icons/nzd.svg'
import jpyIcon from '@/assets/currency-icons/jpy.svg'
import cnyIcon from '@/assets/currency-icons/cny.svg'
import aedIcon from '@/assets/currency-icons/aed.svg'
import sarIcon from '@/assets/currency-icons/sar.svg'
import tryIcon from '@/assets/currency-icons/try.svg'
import rubIcon from '@/assets/currency-icons/rub.svg'
import usdtIcon from '@/assets/currency-icons/usdt.svg'
import xauIcon from '@/assets/currency-icons/xau.svg'

const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)
const isEdit = computed(() => !!id.value)
const isRtl = computed(() => document.documentElement.dir === 'rtl')

const form = ref({ name: '', description: '' })
const errors = reactive({ name: null, description: null, non_field_errors: null })
const submitting = ref(false)
const activePresetCode = ref('')

const categoryPresets = computed(() => ([
  { code: 'USD', iconSrc: usdIcon },
  { code: 'EUR', iconSrc: eurIcon },
  { code: 'GBP', iconSrc: gbpIcon },
  { code: 'CHF', iconSrc: chfIcon },
  { code: 'CAD', iconSrc: cadIcon },
  { code: 'AUD', iconSrc: audIcon },
  { code: 'NZD', iconSrc: nzdIcon },
  { code: 'JPY', iconSrc: jpyIcon },
  { code: 'CNY', iconSrc: cnyIcon },
  { code: 'AED', iconSrc: aedIcon },
  { code: 'SAR', iconSrc: sarIcon },
  { code: 'TRY', iconSrc: tryIcon },
  { code: 'RUB', iconSrc: rubIcon },
  { code: 'USDT', iconSrc: usdtIcon },
  { code: 'XAU', iconSrc: xauIcon },
]).map((preset) => ({
  ...preset,
  label: t(`categories.presetLabels.${preset.code}`),
  description: t(`categories.presetDescriptions.${preset.code}`),
})))

function applyServerErrors(responseData) {
  if (!responseData || typeof responseData !== 'object') return false
  let hasAny = false
  const details = getApiErrorDetails({ response: { data: responseData } })
  const normalized = details.fieldErrors || {}
  for (const field of Object.keys(errors)) {
    const val = normalized[field]
    if (!val) continue
    errors[field] = val
    hasAny = true
  }
  if (!hasAny && details.message) {
    errors.non_field_errors = details.message
    hasAny = true
  }
  return hasAny
}

onMounted(async () => {
  if (isEdit.value) {
    try {
      const { data } = await categoryApi.get(id.value)
      form.value = { name: data.name ?? '', description: data.description ?? '' }
    } catch {
      toast.error(t('toast.serverError'))
    }
  }
})

async function handleSubmit() {
  if (!form.value.name?.trim()) {
    errors.name = t('validation.required')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value) {
      await categoryApi.update(id.value, form.value)
    } else {
      const { data } = await categoryApi.create(form.value)
      if (data?.id != null) {
        sessionStorage.setItem('guideAddPriceType', String(data.id))
      }
    }
    toast.success(t('toast.saveSuccess'))
    router.push('/categories')
  } catch (err) {
    const details = getApiErrorDetails(err)
    const handled = applyServerErrors(err?.response?.data)
    if (!handled) {
      toast.error(details.message || t('toast.serverError'))
    }
  } finally {
    submitting.value = false
  }
}

async function createPresetCategory(preset) {
  if (activePresetCode.value || isEdit.value) return
  activePresetCode.value = preset.code
  errors.non_field_errors = null
  try {
    const { data } = await categoryApi.create({
      name: preset.label,
      description: preset.description,
    })
    if (data?.id != null) {
      sessionStorage.setItem('guideAddPriceType', String(data.id))
    }
    toast.success(t('toast.saveSuccess'))
    router.push('/categories')
  } catch (err) {
    const message = getApiErrorDetails(err).message || t('categories.presetCreateFailed')
    toast.error(message)
  } finally {
    activePresetCode.value = ''
  }
}
</script>
