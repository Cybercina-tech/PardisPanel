<template>
  <div class="min-h-screen flex items-center justify-center px-4 py-12 relative" style="background: var(--bg-base);">
    <div class="absolute top-4 right-4 flex items-center gap-2">
      <LanguageSwitcher />
      <ThemeToggle />
    </div>
    <div class="w-full max-w-md">
      <div class="card-luxury text-center mb-6">
        <div class="mx-auto w-fit mb-4">
          <AppBrandLogo size="xl" rounded="xl" />
        </div>
        <h1 class="text-2xl font-bold text-gold mb-1">{{ siteName }}</h1>
        <p class="text-gray-400 text-sm">{{ $t('auth.loginTitle') }}</p>
      </div>

      <div class="card-luxury">
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <AlertMessage v-if="error" type="error" :show="true" @dismiss="error = ''">
            {{ error }}
          </AlertMessage>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('auth.identifier') }}</label>
            <input
              v-model="identifier"
              type="text"
              class="input-luxury"
              :placeholder="$t('auth.identifierPlaceholder')"
              autocomplete="username"
              required
              autofocus
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">{{ $t('auth.password') }}</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="input-luxury !pe-12"
                :placeholder="$t('auth.password')"
                autocomplete="current-password"
                required
              />
              <button
                type="button"
                class="absolute inset-y-0 end-0 flex w-12 items-center justify-center text-gray-400 hover:text-gold focus:outline-none focus-visible:text-gold"
                :aria-label="showPassword ? $t('auth.hidePassword') : $t('auth.showPassword')"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'" aria-hidden="true"></i>
              </button>
            </div>
          </div>

          <label class="flex cursor-pointer select-none items-center gap-2 text-sm text-gray-400">
            <input
              v-model="rememberMe"
              type="checkbox"
              class="h-4 w-4 rounded accent-[var(--primary)]"
            />
            <span>{{ $t('auth.rememberMe') }}</span>
          </label>

          <button
            type="submit"
            class="btn-luxury w-full"
            :disabled="loading"
          >
            <LoadingSpinner v-if="loading" class="w-5 h-5" />
            <i v-else class="fas fa-sign-in-alt"></i>
            <span>{{ loading ? $t('auth.loggingIn') : $t('auth.loginButton') }}</span>
          </button>
        </form>

        <GoogleSignInButton @credential="handleGoogle" />
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import { getApiErrorDetails } from '@/services/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import LanguageSwitcher from '@/components/ui/LanguageSwitcher.vue'
import AlertMessage from '@/components/ui/AlertMessage.vue'
import AppBrandLogo from '@/components/layout/AppBrandLogo.vue'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const siteSettings = useSiteSettingsStore()

const identifier = ref('')
const password = ref('')
const showPassword = ref(false)
const rememberMe = ref(true)
const error = ref('')
const loading = ref(false)

const siteName = computed(() => siteSettings.siteName)

onMounted(() => {
  siteSettings.fetch()
})

async function handleGoogle(credential) {
  error.value = ''
  loading.value = true
  try {
    await auth.loginWithGoogle(credential)
    router.push(route.query.redirect || '/panel')
  } catch (err) {
    error.value = getApiErrorDetails(err).message
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(identifier.value, password.value, rememberMe.value)
    const redirect = route.query.redirect
    router.push(redirect || '/panel')
  } catch (err) {
    error.value = getApiErrorDetails(err).message
  } finally {
    loading.value = false
  }
}
</script>
