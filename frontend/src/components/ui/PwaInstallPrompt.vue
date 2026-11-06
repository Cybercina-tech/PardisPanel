<template>
  <Transition name="pwa-slide">
    <div
      v-if="showPrompt"
      class="fixed bottom-4 start-4 end-4 sm:start-auto sm:end-4 sm:w-80 z-50 rounded-2xl p-4 shadow-2xl border"
      style="background: var(--bg-card); border-color: var(--border-card);"
    >
      <div class="flex items-start gap-3">
        <div
          class="flex-shrink-0 p-2.5 rounded-xl"
          style="background: var(--primary-muted);"
        >
          <i class="fas fa-mobile-alt text-xl text-gold" />
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-[var(--text-primary)] mb-1">{{ $t('pwa.installTitle') }}</h3>
          <p class="text-sm text-[var(--text-secondary)] mb-3">{{ $t('pwa.installDesc') }}</p>
          <div class="flex gap-2">
            <button class="btn-luxury text-sm py-2 px-4" @click="install">
              <i class="fas fa-download" />
              {{ $t('pwa.install') }}
            </button>
            <button
              class="btn-luxury-outline text-sm py-2 px-4"
              @click="dismiss"
            >
              {{ $t('pwa.dismiss') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import {
  STORAGE_PWA_DISMISSED,
  STORAGE_PWA_DISMISSED_LEGACY,
  storageGet,
  storageSet,
  storageRemove,
} from '@/constants/branding.js'

const showPrompt = ref(false)
let deferredPrompt = null

function handleBeforeInstall(e) {
  const dismissed = storageGet(STORAGE_PWA_DISMISSED, STORAGE_PWA_DISMISSED_LEGACY)
  if (dismissed) {
    const dismissedAt = Number(dismissed)
    const daysSinceDismissed = (Date.now() - dismissedAt) / (1000 * 60 * 60 * 24)
    if (daysSinceDismissed < 7) return
  }

  e.preventDefault()
  deferredPrompt = e
  showPrompt.value = true
}

async function install() {
  if (!deferredPrompt) return
  deferredPrompt.prompt()
  const { outcome } = await deferredPrompt.userChoice
  deferredPrompt = null
  showPrompt.value = false
  if (outcome === 'accepted') {
    storageRemove(STORAGE_PWA_DISMISSED, STORAGE_PWA_DISMISSED_LEGACY)
  }
}

function dismiss() {
  showPrompt.value = false
  storageSet(STORAGE_PWA_DISMISSED, STORAGE_PWA_DISMISSED_LEGACY, String(Date.now()))
}

onMounted(() => {
  window.addEventListener('beforeinstallprompt', handleBeforeInstall)
})

onUnmounted(() => {
  window.removeEventListener('beforeinstallprompt', handleBeforeInstall)
})
</script>

<style scoped>
.pwa-slide-enter-active,
.pwa-slide-leave-active {
  transition: all 0.3s ease;
}
.pwa-slide-enter-from,
.pwa-slide-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}
</style>
