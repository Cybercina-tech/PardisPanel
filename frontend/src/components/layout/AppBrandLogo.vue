<template>
  <div
    class="brand-logo-wrapper flex items-center justify-center overflow-hidden border bg-primary-muted"
    :class="[roundedClass, sizeClass]"
    :style="{ borderColor: 'var(--border-color)' }"
  >
    <img
      v-if="hasUsableLogo"
      :src="logoSrc"
      :alt="$t('common.brandLogo')"
      class="w-full h-full object-contain bg-white p-0.5"
      @error="onImageError"
    >
    <i v-else-if="showFallbackIcon" class="fas fa-coins text-[var(--primary)]" :class="iconClass" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import { DEFAULT_LOGO_URL } from '@/constants/branding.js'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg', 'xl'].includes(v),
  },
  rounded: {
    type: String,
    default: 'xl',
    validator: (v) => ['md', 'lg', 'xl', 'full'].includes(v),
  },
  showFallbackIcon: {
    type: Boolean,
    default: true,
  },
})

const siteSettings = useSiteSettingsStore()
const imageFailed = ref(false)

const logoSrc = computed(() => {
  const logo = siteSettings.settings?.logo
  return typeof logo === 'string' && logo ? logo : DEFAULT_LOGO_URL
})

const hasUsableLogo = computed(() => Boolean(logoSrc.value) && !imageFailed.value)

watch(logoSrc, () => {
  imageFailed.value = false
})

const sizeClass = computed(() => {
  if (props.size === 'sm') return 'w-10 h-10'
  if (props.size === 'lg') return 'w-16 h-16'
  if (props.size === 'xl') return 'w-20 h-20'
  return 'w-12 h-12'
})

const iconClass = computed(() => {
  if (props.size === 'sm') return 'text-base'
  if (props.size === 'lg') return 'text-2xl'
  if (props.size === 'xl') return 'text-3xl'
  return 'text-xl'
})

const roundedClass = computed(() => {
  if (props.rounded === 'md') return 'rounded-md'
  if (props.rounded === 'lg') return 'rounded-lg'
  if (props.rounded === 'full') return 'rounded-full'
  return 'rounded-xl'
})

function onImageError() {
  imageFailed.value = true
}
</script>
