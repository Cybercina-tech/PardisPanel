<template>
  <button
    type="button"
    class="theme-toggle inline-flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300 ease-in-out bg-[var(--bg-hover)] hover:bg-[var(--border-color)] text-[var(--primary)]"
    :aria-label="ariaLabel"
    @click="theme.toggle()"
  >
    <Transition name="icon-fade" mode="out-in">
      <i
        :key="theme.theme"
        :class="iconClass"
        class="text-lg"
      />
    </Transition>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

const iconClass = computed(() => {
  switch (theme.theme) {
    case 'light': return 'fas fa-sun'
    case 'dark': return 'fas fa-moon'
    default: return 'fas fa-moon'
  }
})

const { t } = useI18n()

const ariaLabel = computed(() => {
  switch (theme.theme) {
    case 'light': return t('common.switchToDarkTheme')
    case 'dark': return t('common.switchToLightTheme')
    default: return t('common.toggleTheme')
  }
})
</script>

<style scoped>
.icon-fade-enter-active,
.icon-fade-leave-active {
  transition: opacity 0.2s ease;
}
.icon-fade-enter-from,
.icon-fade-leave-to {
  opacity: 0;
}
</style>