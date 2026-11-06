<template>
  <div
    class="telegram-mockup rounded-2xl overflow-hidden border shadow-lg max-w-[420px] mx-auto bg-slate-100 border-slate-200 dark:bg-[#1c1c1e] dark:border-[var(--glass-border)]"
    style="font-family: 'Vazirmatn', 'IRANSans', system-ui, sans-serif;"
  >
    <div class="p-3 sm:p-4">
      <!-- Telegram message bubble -->
      <div class="rounded-2xl overflow-hidden bg-white border border-slate-200 dark:bg-[#2b2b2d] dark:border-white/5">
        <div v-if="displayImageUrl" class="relative w-full aspect-video bg-slate-200 dark:bg-black/40 p-2">
          <img
            :src="displayImageUrl"
            alt=""
            class="w-full h-full object-contain rounded-lg"
            @error="imageError = true"
          />
          <div
            v-if="imageError"
            class="absolute inset-0 flex items-center justify-center text-slate-500 dark:text-[var(--text-secondary)] text-sm"
          >
            {{ $t('telegramStudio.previewImageError') || 'Image' }}
          </div>
        </div>
        <div
          v-if="description || !imageUrl"
          class="px-4 py-3 text-slate-900 dark:text-[var(--text-primary)] text-[15px] leading-relaxed whitespace-pre-line telegram-mockup-text"
          v-html="safeDescriptionHtml"
        />
        <div
          v-if="buttons.length"
          class="border-t border-slate-200 dark:border-white/5"
          :class="buttons.length === 2 ? 'flex' : 'flex flex-col'"
        >
          <a
            v-for="(btn, idx) in buttons"
            v-show="btn.label"
            :key="idx"
            href="#"
            class="inline-flex items-center justify-center px-4 py-2.5 text-[14px] font-medium text-[#2a9fd6] hover:bg-slate-100 dark:hover:bg-white/5 transition-colors telegram-mockup-btn border-b border-slate-200 dark:border-white/5 last:border-b-0"
            :class="buttons.length === 2 ? 'flex-1 border-b-0 border-e border-slate-200 dark:border-white/5 last:border-e-0' : ''"
            @click.prevent
          >
            {{ btn.label }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { normalizeMediaUrl } from '@/utils/normalizeMediaUrl.js'

const props = defineProps({
  imageUrl: { type: String, default: '' },
  description: { type: String, default: '' },
  buttons: {
    type: Array,
    default: () => [],
  },
  variableValues: {
    type: Object,
    default: () => ({}),
  },
})

const imageError = ref(false)

const displayImageUrl = computed(() => normalizeMediaUrl(props.imageUrl))

const displayDescription = computed(() => {
  let text = props.description || ''
  if (!text || !Object.keys(props.variableValues).length) return text
  Object.entries(props.variableValues).forEach(([key, value]) => {
    const legacyPlaceholder = `{{${key}}}`
    const canonicalPlaceholder = `{${key}}`
    const resolved = String(value)
    text = text.split(legacyPlaceholder).join(resolved)
    text = text.split(canonicalPlaceholder).join(resolved)
  })
  text = text.replace(/\{\{([^}]+)\}\}/g, (_, key) => props.variableValues[key] ?? `{{${key}}}`)
  text = text.replace(/\{([^{}]+)\}/g, (_, key) => props.variableValues[key] ?? `{${key}}`)
  return text
})

// Telegram renders a small HTML subset in captions. Everything is escaped first,
// then only those tags (and http(s) links) are switched back on.
const safeDescriptionHtml = computed(() => {
  const escaped = displayDescription.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  return escaped
    .replace(/&lt;(\/?)(b|strong|i|em|u|s|code)&gt;/g, '<$1$2>')
    .replace(
      /&lt;a href=&quot;(https?:\/\/[^"<>\s]*?)&quot;&gt;/g,
      (_, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-[#2a9fd6]">`,
    )
    .replace(/&lt;\/a&gt;/g, '</a>')
})
</script>

<style scoped>
.telegram-mockup-text {
  word-break: break-word;
}
.telegram-mockup-btn {
  background: rgba(42, 159, 214, 0.12);
  color: #2a9fd6;
}
.telegram-mockup-btn:hover {
  background: rgba(42, 159, 214, 0.2);
}
</style>
