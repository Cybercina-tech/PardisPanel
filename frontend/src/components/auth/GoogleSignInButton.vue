<template>
  <div v-if="clientId" class="google-signin">
    <div class="google-signin__divider">
      <span>{{ t('auth.or') }}</span>
    </div>
    <!-- Google renders its own button into this node; the markup is theirs. -->
    <div ref="target" class="google-signin__target" />
    <p v-if="error" class="google-signin__error">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSiteSettingsStore } from '@/stores/siteSettings'

const emit = defineEmits(['credential'])

const { t } = useI18n()
const siteSettings = useSiteSettingsStore()

const target = ref(null)
const error = ref('')
const clientId = computed(() => siteSettings.settings.google_client_id || '')

const GSI_SRC = 'https://accounts.google.com/gsi/client'

/* Loaded on demand rather than from index.html: an install with no client id
   should not fetch Google's script at all. */
function loadGsi() {
  if (window.google?.accounts?.id) return Promise.resolve()
  const existing = document.querySelector(`script[src="${GSI_SRC}"]`)
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', resolve)
      existing.addEventListener('error', reject)
    })
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = GSI_SRC
    script.async = true
    script.defer = true
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

async function render() {
  if (!clientId.value || !target.value) return
  try {
    await loadGsi()
    window.google.accounts.id.initialize({
      client_id: clientId.value,
      callback: ({ credential }) => emit('credential', credential),
    })
    window.google.accounts.id.renderButton(target.value, {
      theme: 'outline',
      size: 'large',
      width: target.value.offsetWidth || 320,
    })
  } catch {
    error.value = t('auth.googleUnavailable')
  }
}

onMounted(render)
watch(clientId, render)
</script>

<style scoped>
.google-signin {
  margin-top: 1.25rem;
}

.google-signin__divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--text-secondary);
}

.google-signin__divider::before,
.google-signin__divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-card);
}

.google-signin__target {
  display: flex;
  justify-content: center;
  min-height: 2.5rem;
}

.google-signin__error {
  margin-top: 0.5rem;
  font-size: 0.72rem;
  text-align: center;
  color: var(--danger, #ef4444);
}
</style>
