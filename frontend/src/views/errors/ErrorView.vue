<template>
  <div class="min-h-screen relative flex flex-col items-center justify-center px-4 py-12" style="background: var(--bg-base);">
    <div class="absolute top-4 end-4">
      <ThemeToggle />
    </div>

    <div class="glass card-luxury max-w-lg w-full mx-auto text-center animate-fade-in-up">
      <!-- 404: animated compass icon -->
      <div v-if="code === 404" class="error-icon-404 mb-6 mx-auto w-20 h-20 flex items-center justify-center rounded-2xl bg-primary-muted border border-[var(--border-color)]">
        <i class="fas fa-compass text-4xl text-gold"></i>
      </div>
      <!-- 500: server icon -->
      <div v-else-if="code === 500" class="mb-6 mx-auto w-20 h-20 flex items-center justify-center rounded-2xl bg-primary-muted border border-[var(--border-color)]">
        <i class="fas fa-server text-4xl text-gold"></i>
      </div>
      <!-- 403: lock icon -->
      <div v-else-if="code === 403" class="mb-6 mx-auto w-20 h-20 flex items-center justify-center rounded-2xl bg-primary-muted border border-[var(--border-color)]">
        <i class="fas fa-lock text-4xl text-gold"></i>
      </div>

      <div class="error-code" :class="code === 404 ? 'error-code-glow' : ''">{{ code }}</div>
      <h1 class="text-xl sm:text-2xl font-bold mt-4" style="color: var(--text-primary);">{{ displayTitle }}</h1>
      <p class="mt-3 text-base leading-relaxed" style="color: var(--text-secondary);">{{ displayMessage }}</p>
      <p v-if="showLogId && resolvedErrorId" class="mt-4 text-sm font-mono rounded-lg px-3 py-2 inline-block" style="background: var(--bg-input); color: var(--text-secondary);">
        {{ t('errorPages.logIdLabel') }} #{{ resolvedErrorId }}
      </p>

      <div class="flex flex-wrap items-center justify-center gap-3 mt-8">
        <router-link to="/panel" class="btn-luxury inline-flex items-center gap-2">
          <i class="fas fa-home"></i>
          <span>{{ t('errorPages.backToHome') }}</span>
        </router-link>
        <a
          :href="supportLink"
          target="_blank"
          rel="noopener noreferrer"
          class="btn-luxury-outline inline-flex items-center gap-2"
        >
          <i class="fab fa-telegram-plane"></i>
          <span>{{ t('errorPages.contactSupport') }}</span>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'

const props = defineProps({
  code: {
    type: Number,
    required: true,
    validator: (v) => [404, 500, 403].includes(v),
  },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  errorId: { type: String, default: '' },
})

const route = useRoute()
const { t } = useI18n()
const siteSettings = useSiteSettingsStore()

const displayTitle = computed(() => {
  if (props.title) return props.title
  const key = `errorPages.${props.code}.title`
  return t(key)
})

const displayMessage = computed(() => {
  if (props.message) return props.message
  const key = `errorPages.${props.code}.message`
  return t(key)
})

const resolvedErrorId = computed(() => {
  if (props.errorId) return props.errorId
  return route.query.logId || ''
})

const showLogId = computed(() => props.code === 500 && !!resolvedErrorId.value)

/* An owner-managed channel first — that is the one someone actually answers —
   then the site's Telegram link, then the built-in support handle. */
const supportLink = computed(() => {
  const channel = siteSettings.supportChannels.find((item) => item.href)
  if (channel) return channel.href
  const link = siteSettings.settings?.telegram_link?.trim()
  if (link) return link.startsWith('http') ? link : `https://t.me/${link.replace(/^@/, '')}`
  return 'https://t.me/mrexchange_support'
})

onMounted(() => {
  siteSettings.fetch().catch(() => {})
})
</script>

<style scoped>
.error-code {
  font-size: clamp(4rem, 18vw, 8rem);
  font-weight: 800;
  line-height: 1;
  color: var(--primary);
  text-shadow: var(--glow-soft);
}
.error-code-glow {
  animation: pulse-glow 2.5s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { text-shadow: var(--glow-soft); }
  50% { text-shadow: var(--glow-strong); }
}
.error-icon-404 i {
  animation: spin-slow 8s linear infinite;
}
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
