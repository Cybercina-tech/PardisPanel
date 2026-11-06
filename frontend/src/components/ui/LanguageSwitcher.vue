<template>
  <div class="relative">
    <button
      ref="triggerRef"
      type="button"
      class="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium transition-all duration-300 ease-in-out border hover:scale-105 min-w-[3.75rem]"
      style="background: var(--bg-card); border-color: var(--border-color); color: var(--primary);"
      :title="$t('lang.' + locale)"
      aria-haspopup="listbox"
      :aria-expanded="open ? 'true' : 'false'"
      @click="toggle"
    >
      <i class="fas fa-globe text-xs" />
      <span>{{ localeLabel(locale) }}</span>
    </button>
    <!-- Teleported: the header is a sticky, backdrop-blurred bar, which is its
         own stacking context — an absolute menu inside it sank under the page. -->
    <Teleport to="body">
      <div
        v-if="open"
        ref="panelRef"
        class="dropdown-panel !p-1"
        :style="panelStyle"
        role="listbox"
      >
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <button
            v-for="loc in locales"
            :key="loc"
            type="button"
            role="option"
            :aria-selected="locale === loc"
            class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-start transition-colors hover:bg-[var(--bg-hover)]"
            :class="locale === loc ? 'text-[var(--primary)] font-semibold' : 'text-[var(--text-secondary)]'"
            @click="selectLocale(loc)"
          >
            <span>{{ $t('lang.' + loc) }}</span>
            <i v-if="locale === loc" class="fas fa-check text-xs ms-auto" />
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES } from '@/i18n'
import { setLocale } from '@/i18n'
import { useAnchoredPanel } from '@/composables/useAnchoredPanel'

const { locale } = useI18n({ useScope: 'global' })
const locales = SUPPORTED_LOCALES

const { triggerRef, panelRef, open, panelStyle, close, toggle } =
  useAnchoredPanel({ minWidth: 150, maxHeight: 320, minSpace: 180 })

function localeLabel(code) {
  return code.toUpperCase()
}

function selectLocale(code) {
  setLocale(code)
  close()
}
</script>
