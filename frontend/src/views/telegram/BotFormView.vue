<template>
  <div class="w-full min-w-0">
    <!-- Breadcrumb: Home → Telegram → Bot Setup → New Bot / Edit Bot -->
    <nav class="mb-6 flex flex-wrap items-center gap-2 text-sm text-[var(--text-secondary)]">
      <router-link to="/panel" class="hover:text-gold transition-colors">{{ $t('breadcrumb.home') }}</router-link>
      <span class="opacity-60" aria-hidden="true">/</span>
      <router-link :to="{ name: 'telegram-send', query: { tab: 'botSetup' } }" class="hover:text-gold transition-colors">
        {{ $t('sidebar.telegram') }}
      </router-link>
      <span class="opacity-60" aria-hidden="true">/</span>
      <span class="text-[var(--text-secondary)]">{{ $t('telegram.tabs.botSetup') }}</span>
      <span class="opacity-60" aria-hidden="true">/</span>
      <span class="text-gold font-medium">
        {{ isEdit ? $t('telegram.botSetup.editBot') : $t('telegram.botSetup.newBotTitle') }}
      </span>
    </nav>

    <div class="max-w-2xl mx-auto">
      <div
        class="card-luxury rounded-2xl p-6 shadow-xl border border-[var(--glass-border)] animate-fade-in-up"
        style="background: var(--bg-card, #1e2535);"
      >
        <h1 class="text-2xl font-bold text-gold mb-6">
          {{ isEdit ? $t('telegram.botSetup.editBot') : $t('telegram.botSetup.newBotTitle') }}
        </h1>

        <form @submit.prevent="handleSubmit" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">
              {{ $t('telegram.botSetup.name') }}
            </label>
            <input
              v-model="form.name"
              type="text"
              class="input-luxury w-full"
              :placeholder="$t('telegram.botSetup.namePlaceholder')"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">
              {{ $t('telegram.botSetup.token') }}
            </label>
            <div class="flex gap-2">
              <input
                v-model="form.token"
                :type="tokenRevealed ? 'text' : 'password'"
                class="input-luxury flex-1"
                :placeholder="isEdit ? $t('telegram.botSetup.tokenPlaceholderChange') : $t('telegram.botSetup.tokenPlaceholder')"
                :required="!isEdit"
                autocomplete="off"
              />
              <button
                type="button"
                class="btn-luxury-outline shrink-0 px-3"
                :title="tokenRevealed ? $t('telegram.botSetup.hide') : $t('telegram.botSetup.reveal')"
                @click="tokenRevealed = !tokenRevealed"
              >
                <i :class="tokenRevealed ? 'fas fa-eye-slash' : 'fas fa-eye'" />
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">
              {{ $t('telegram.botSetup.displayName') }}
            </label>
            <input
              v-model="form.display_name"
              type="text"
              class="input-luxury w-full"
              :placeholder="$t('telegram.botSetup.displayNamePlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">
              {{ $t('telegram.botSetup.notes') }}
            </label>
            <textarea
              v-model="form.notes"
              class="input-luxury w-full"
              rows="3"
              :placeholder="$t('telegram.botSetup.notesPlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">
              {{ $t('telegram.botSetup.defaultExchangeTtl') }}
            </label>
            <input
              v-model.number="form.default_exchange_ttl_minutes"
              type="number"
              min="1"
              step="1"
              class="input-luxury w-full"
              required
            />
            <p class="mt-1 text-xs text-[var(--text-secondary)]">
              {{ $t('telegram.botSetup.defaultExchangeTtlHint') }}
            </p>
          </div>

          <div class="space-y-3">
            <BaseSwitch v-model="form.is_active" :label="$t('telegram.botSetup.isActive')" />
            <BaseSwitch v-model="form.restrict_to_known_channels" :label="$t('telegram.botSetup.restrictChannels')" />
            <BaseSwitch v-model="form.log_all_messages" :label="$t('telegram.botSetup.logMessages')" />
          </div>

          <div class="flex flex-wrap gap-3 pt-4 border-t border-[var(--glass-border)]">
            <button type="button" class="btn-luxury-outline" :disabled="submitting" @click="goBack">
              {{ $t('common.cancel') }}
            </button>
            <button type="submit" class="btn-luxury" :disabled="submitting">
              <LoadingSpinner v-if="submitting" class="w-5 h-5" />
              <span v-else>{{ isEdit ? $t('common.save') : $t('common.create') }}</span>
            </button>
            <button
              v-if="isEdit"
              type="button"
              class="btn-luxury-outline"
              :disabled="submitting || testing"
              @click="testConnection"
            >
              <LoadingSpinner v-if="testing" class="w-5 h-5" />
              <span v-else>{{ $t('telegram.botSetup.testConnection') }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { telegramApi } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import BaseSwitch from '@/components/ui/BaseSwitch.vue'

const { t } = useI18n()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const botId = computed(() => route.params.id)
const isEdit = computed(() => !!botId.value)

const form = reactive({
  name: '',
  token: '',
  display_name: '',
  notes: '',
  is_active: true,
  restrict_to_known_channels: false,
  log_all_messages: false,
  default_exchange_ttl_minutes: 5,
})
const tokenRevealed = ref(false)
const submitting = ref(false)
const testing = ref(false)
const loading = ref(true)

// A rejected token comes back as `errors.token` in the standard error body;
// reading only `detail` turned every reason into a bare "server error".
function apiErrorMessage(err, fallbackKey) {
  const data = err?.response?.data
  const msg = data?.detail || data?.errors?.token || data?.message
  return typeof msg === 'string' && msg ? msg : t(fallbackKey)
}

function goBack() {
  router.push({ name: 'telegram-send', query: { tab: 'botSetup' } })
}

const redirectAfterSave = () => {
  router.push({ name: 'telegram-send', query: { tab: 'botSetup' } })
}

onMounted(async () => {
  if (isEdit.value) {
    try {
      const { data } = await telegramApi.bots.list()
      const list = Array.isArray(data) ? data : (data?.results ?? [])
      const bot = list.find((b) => String(b.id) === String(botId.value))
      if (bot) {
        form.name = bot.name || ''
        form.token = ''
        form.display_name = bot.display_name || ''
        form.notes = bot.notes || ''
        form.is_active = !!bot.is_active
        form.restrict_to_known_channels = !!bot.restrict_to_known_channels
        form.log_all_messages = !!bot.log_all_messages
        form.default_exchange_ttl_minutes = Number(bot.default_exchange_ttl_minutes) > 0
          ? Number(bot.default_exchange_ttl_minutes)
          : 5
      } else {
        toast.error(t('toast.serverError'))
        goBack()
      }
    } catch {
      toast.error(t('toast.serverError'))
      goBack()
    } finally {
      loading.value = false
    }
  } else {
    loading.value = false
  }
})

async function handleSubmit() {
  const ttl = Number(form.default_exchange_ttl_minutes)
  if (!Number.isInteger(ttl) || ttl < 1) {
    toast.error(t('validation.required'))
    return
  }
  const payload = {
    name: (form.name || '').trim(),
    display_name: (form.display_name || '').trim(),
    notes: (form.notes || '').trim(),
    is_active: form.is_active,
    restrict_to_known_channels: form.restrict_to_known_channels,
    log_all_messages: form.log_all_messages,
    default_exchange_ttl_minutes: ttl,
  }
  if (isEdit.value) {
    if ((form.token || '').trim()) {
      payload.token = form.token.trim()
    }
    if (!payload.name) {
      toast.error(t('validation.required'))
      return
    }
    submitting.value = true
    try {
      await telegramApi.bots.update(botId.value, payload)
      toast.success(t('toast.saveSuccess'))
      redirectAfterSave()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'toast.serverError'))
    } finally {
      submitting.value = false
    }
  } else {
    const token = (form.token || '').trim()
    if (!token || !payload.name) {
      toast.error(t('telegram.botSetup.tokenRequired'))
      return
    }
    payload.token = token
    submitting.value = true
    try {
      await telegramApi.bots.create(payload)
      toast.success(t('toast.saveSuccess'))
      redirectAfterSave()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'toast.serverError'))
    } finally {
      submitting.value = false
    }
  }
}

async function testConnection() {
  if (!isEdit.value || !botId.value) return
  testing.value = true
  try {
    const { data } = await telegramApi.bots.testConnection(botId.value, {})
    if (data?.success) {
      // The backend says what it actually reached — token only, or a channel too.
      toast.success(data.detail || t('telegram.botSetup.testSuccess'))
    } else {
      toast.error(data?.detail || t('telegram.botSetup.testFailed'))
    }
  } catch (err) {
    toast.error(apiErrorMessage(err, 'telegram.botSetup.testFailed'))
  } finally {
    testing.value = false
  }
}
</script>
