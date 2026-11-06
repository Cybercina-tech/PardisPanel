<template>
  <div class="w-full min-w-0 overflow-x-hidden pb-20 md:pb-10 px-4 md:px-0">
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div class="flex min-w-0 items-center gap-4">
        <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-2 border-[var(--primary)] bg-primary-muted">
          <span class="text-lg font-bold text-[var(--primary)]">{{ initials }}</span>
        </div>
        <div class="min-w-0">
          <h1 class="truncate text-xl font-bold text-gold sm:text-2xl">
            {{ auth.user?.full_name || auth.username }}
          </h1>
          <p class="truncate text-sm text-[var(--text-secondary)]">
            <span v-if="auth.user?.email">{{ auth.user.email }} · </span>{{ roleLabel }}
          </p>
        </div>
      </div>
      <BaseButton variant="outline" size="sm" @click="goBack">
        <i class="fas fa-arrow-left rtl:rotate-180" />
        <span>{{ $t('common.back') }}</span>
      </BaseButton>
    </div>

    <div class="flex w-full min-w-0 flex-col gap-4 md:flex-row md:gap-6">
      <nav class="w-full shrink-0 md:w-56">
        <div class="card-luxury flex gap-1 overflow-x-auto p-2 md:flex-col md:overflow-visible">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="flex min-h-[48px] shrink-0 items-center gap-3 rounded-xl px-4 py-3 text-start font-medium transition-colors duration-200"
            :class="activeTab === tab.id
              ? 'border border-gold/30 bg-[var(--bg-hover)] text-gold'
              : 'border border-transparent text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--primary)]'"
            @click="activeTab = tab.id"
          >
            <i :class="tab.icon" class="w-5 shrink-0 text-center text-base" />
            <span class="truncate">{{ $t(tab.labelKey) }}</span>
          </button>
        </div>
      </nav>

      <div class="min-w-0 flex-1">
        <Transition name="fade-slide" mode="out-in">
          <!-- Profile -->
          <form
            v-if="activeTab === 'profile'"
            key="profile"
            class="card-luxury space-y-5 p-4 sm:p-6"
            @submit.prevent="saveProfile"
          >
            <h2 class="text-lg font-semibold text-gold">{{ $t('account.profile.title') }}</h2>
            <p class="text-sm text-[var(--text-secondary)]">{{ $t('account.profile.intro') }}</p>

            <div class="grid gap-4 sm:grid-cols-2">
              <TextField
                v-model="profileForm.first_name"
                :label="$t('account.profile.firstName')"
                :error="fieldError('first_name')"
              />
              <TextField
                v-model="profileForm.last_name"
                :label="$t('account.profile.lastName')"
                :error="fieldError('last_name')"
              />
              <TextField
                v-model="profileForm.full_name"
                :label="$t('account.profile.displayName')"
                :hint="$t('account.profile.displayNameHint')"
                :error="fieldError('full_name')"
              />
              <TextField
                v-model="profileForm.exchange_name"
                :label="$t('account.profile.exchangeName')"
                :error="fieldError('exchange_name')"
              />
              <TextField
                v-model="profileForm.email"
                type="email"
                :label="$t('account.profile.email')"
                :hint="$t('account.profile.emailHint')"
                :error="fieldError('email')"
              />
              <TextField
                v-model="profileForm.phone"
                :label="$t('account.profile.phone')"
                :error="fieldError('phone')"
              />
              <TextField
                v-model="profileForm.telegram_username"
                :label="$t('account.profile.telegramUsername')"
                placeholder="@username"
                :error="fieldError('telegram_username')"
              />
              <TextField
                v-model="profileForm.country"
                :label="$t('account.profile.country')"
                :error="fieldError('country')"
              />
              <div class="sm:col-span-2">
                <TextField
                  v-model="profileForm.website"
                  type="url"
                  :label="$t('account.profile.website')"
                  placeholder="https://"
                  :error="fieldError('website')"
                />
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-3 border-t border-[var(--border-card)] pt-4">
              <BaseButton native-type="submit" :loading="savingProfile">
                {{ $t('common.save') }}
              </BaseButton>
              <BaseButton variant="ghost" :disabled="savingProfile" @click="resetProfile">
                {{ $t('common.cancel') }}
              </BaseButton>
            </div>
          </form>

          <!-- Security -->
          <div v-else-if="activeTab === 'security'" key="security" class="space-y-4">
            <form class="card-luxury space-y-5 p-4 sm:p-6" @submit.prevent="savePassword">
              <h2 class="text-lg font-semibold text-gold">{{ $t('account.security.title') }}</h2>
              <p class="text-sm text-[var(--text-secondary)]">{{ $t('account.security.intro') }}</p>

              <div class="grid max-w-md gap-4">
                <TextField
                  v-model="passwordForm.current_password"
                  type="password"
                  autocomplete="current-password"
                  :label="$t('account.security.currentPassword')"
                  :error="fieldError('current_password')"
                />
                <TextField
                  v-model="passwordForm.new_password"
                  type="password"
                  autocomplete="new-password"
                  :label="$t('account.security.newPassword')"
                  :hint="$t('account.security.newPasswordHint')"
                  :error="fieldError('new_password')"
                />
                <TextField
                  v-model="passwordForm.confirm_password"
                  type="password"
                  autocomplete="new-password"
                  :label="$t('account.security.confirmPassword')"
                  :error="confirmError"
                />
              </div>

              <div class="border-t border-[var(--border-card)] pt-4">
                <BaseButton native-type="submit" :loading="savingPassword">
                  {{ $t('account.security.changePassword') }}
                </BaseButton>
              </div>
            </form>

            <div v-if="auth.needsEmailVerification" class="card-luxury space-y-3 p-4 sm:p-6">
              <h2 class="text-lg font-semibold text-gold">{{ $t('account.security.emailVerification') }}</h2>
              <p class="text-sm text-[var(--text-secondary)]">{{ $t('account.security.emailVerificationHint') }}</p>
              <BaseButton variant="outline" :loading="resending" @click="resendVerification">
                {{ $t('account.security.resendVerification') }}
              </BaseButton>
            </div>
          </div>

          <!-- Preferences -->
          <div v-else key="preferences" class="card-luxury space-y-6 p-4 sm:p-6">
            <div>
              <h2 class="text-lg font-semibold text-gold">{{ $t('account.preferences.title') }}</h2>
              <p class="text-sm text-[var(--text-secondary)]">{{ $t('account.preferences.intro') }}</p>
            </div>

            <div>
              <p class="mb-2 text-sm font-medium text-[var(--text-primary)]">{{ $t('account.preferences.theme') }}</p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="option in themeOptions"
                  :key="option.value"
                  type="button"
                  class="flex min-h-[48px] items-center gap-2 rounded-xl border px-4 py-2 text-sm transition-colors"
                  :class="theme.theme === option.value
                    ? 'border-[var(--primary)] bg-primary-muted text-[var(--primary)]'
                    : 'border-[var(--border-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'"
                  @click="theme.set(option.value)"
                >
                  <i :class="option.icon" />
                  <span>{{ $t(option.labelKey) }}</span>
                </button>
              </div>
            </div>

            <div class="max-w-xs">
              <p class="mb-2 text-sm font-medium text-[var(--text-primary)]">{{ $t('account.preferences.language') }}</p>
              <BaseSelect
                :model-value="locale"
                :options="localeOptions"
                @update:model-value="setLocale"
              />
            </div>

            <div class="space-y-3 border-t border-[var(--border-card)] pt-4">
              <BaseSwitch
                :model-value="sidebar.preference"
                :label="$t('account.preferences.collapseSidebar')"
                @update:model-value="sidebar.setCollapsed($event)"
              />
              <div>
                <p class="mb-2 text-sm text-[var(--text-secondary)]">{{ $t('account.preferences.replayTourHint') }}</p>
                <BaseButton variant="outline" size="sm" :loading="replaying" @click="replayTour">
                  <i class="fas fa-route" />
                  <span>{{ $t('onboarding.tour.replay') }}</span>
                </BaseButton>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseSwitch from '@/components/ui/BaseSwitch.vue'
import TextField from '@/components/forms/TextField.vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useSidebarStore } from '@/stores/sidebar'
import { SUPPORTED_LOCALES, setLocale as applyLocale } from '@/i18n'
import { getApiErrorDetails } from '@/services/api'

const router = useRouter()
const toast = useToast()
const { t, locale } = useI18n({ useScope: 'global' })
const auth = useAuthStore()
const theme = useThemeStore()
const sidebar = useSidebarStore()

const tabs = [
  { id: 'profile', labelKey: 'account.tabs.profile', icon: 'fas fa-id-card' },
  { id: 'security', labelKey: 'account.tabs.security', icon: 'fas fa-lock' },
  { id: 'preferences', labelKey: 'account.tabs.preferences', icon: 'fas fa-sliders-h' },
]
const activeTab = ref('profile')

const themeOptions = [
  { value: 'light', labelKey: 'account.preferences.themeLight', icon: 'fas fa-sun' },
  { value: 'dark', labelKey: 'account.preferences.themeDark', icon: 'fas fa-moon' },
]

const localeOptions = computed(() =>
  SUPPORTED_LOCALES.map((code) => ({ value: code, label: t(`lang.${code}`) })),
)

const PROFILE_FIELDS = [
  'first_name',
  'last_name',
  'full_name',
  'exchange_name',
  'email',
  'phone',
  'telegram_username',
  'country',
  'website',
]

const profileForm = reactive(Object.fromEntries(PROFILE_FIELDS.map((key) => [key, ''])))
const passwordForm = reactive({ current_password: '', new_password: '', confirm_password: '' })
const errors = ref({})
const savingProfile = ref(false)
const savingPassword = ref(false)
const resending = ref(false)
const replaying = ref(false)

function resetProfile() {
  for (const key of PROFILE_FIELDS) {
    profileForm[key] = auth.user?.[key] ?? ''
  }
  errors.value = {}
}

watch(() => auth.user, resetProfile, { immediate: true })

const initials = computed(() => {
  const source = auth.user?.full_name || auth.username || '?'
  return source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
})

const roleLabel = computed(() => {
  const key = `userCenter.roles.${auth.role}`
  return t(key) === key ? (auth.role ?? '') : t(key)
})

const confirmError = computed(() => {
  if (!passwordForm.confirm_password) return ''
  return passwordForm.confirm_password === passwordForm.new_password
    ? ''
    : t('account.security.mismatch')
})

function fieldError(field) {
  return errors.value[field] ?? ''
}

function goBack() {
  // A deep link straight to /account has nothing to go back to.
  if (window.history.state?.back) router.back()
  else router.push('/panel')
}

async function saveProfile() {
  savingProfile.value = true
  errors.value = {}
  try {
    await auth.updateProfile({ ...profileForm })
    toast.success(t('toast.saveSuccess'))
  } catch (err) {
    const { message, fieldErrors } = getApiErrorDetails(err)
    errors.value = fieldErrors || {}
    toast.error(message)
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  if (confirmError.value) return
  savingPassword.value = true
  errors.value = {}
  try {
    await auth.changePassword({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    })
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    toast.success(t('account.security.changed'))
  } catch (err) {
    const { message, fieldErrors } = getApiErrorDetails(err)
    errors.value = fieldErrors || {}
    toast.error(message)
  } finally {
    savingPassword.value = false
  }
}

async function resendVerification() {
  resending.value = true
  try {
    await auth.resendVerification()
    toast.success(t('account.security.verificationSent'))
  } catch (err) {
    toast.error(getApiErrorDetails(err).message)
  } finally {
    resending.value = false
  }
}

async function replayTour() {
  replaying.value = true
  try {
    await auth.completeOnboarding({ replay: true })
    router.push('/panel')
  } catch (err) {
    toast.error(getApiErrorDetails(err).message)
  } finally {
    replaying.value = false
  }
}

function setLocale(code) {
  applyLocale(code)
}
</script>
