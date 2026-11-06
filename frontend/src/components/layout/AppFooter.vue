<template>
  <footer
    class="mt-auto border-t border-[var(--border-card)]/40 bg-[var(--bg-footer)] px-3 py-2 md:px-4 md:py-2.5 pb-[max(3.1rem,calc(2.4rem+env(safe-area-inset-bottom,0px)))] md:pb-2.5"
  >
    <div class="flex items-center justify-between gap-3">
      <p class="m-0 text-[11px] md:text-xs leading-none text-slate-400/90 dark:text-slate-500/90">{{ $t('common.poweredBy') }} SIavash01</p>
      <SupportChannelList v-if="hasSupport" inline class="min-w-0" />
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="font-semibold text-[11px] md:text-xs text-[var(--primary)] truncate max-w-[120px]">{{ siteName }}</span>
        <AppBrandLogo size="sm" rounded="lg" />
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import AppBrandLogo from '@/components/layout/AppBrandLogo.vue'
import SupportChannelList from '@/components/support/SupportChannelList.vue'

const siteSettings = useSiteSettingsStore()
const siteName = computed(() => siteSettings.siteName)
const hasSupport = computed(() => siteSettings.supportChannels.length > 0)
</script>
