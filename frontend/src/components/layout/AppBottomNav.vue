<template>
  <nav
    class="fixed bottom-0 start-0 end-0 z-30 flex items-center justify-around border-t border-slate-200 bg-white py-2 shadow-sm md:hidden dark:border-[var(--border-card)] dark:bg-[var(--bg-navbar)] dark:shadow-none"
    style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom));"
  >
    <router-link
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="flex flex-col items-center gap-0.5 min-h-[48px] justify-center px-4 py-2 rounded-xl transition-colors min-w-[64px]"
      :class="isActive(item) ? 'text-gold' : 'text-[var(--text-secondary)] hover:text-[var(--primary)]'"
    >
      <i :class="item.icon" class="text-lg" />
      <span class="text-xs font-medium">{{ $t(item.labelKey) }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { navLinkIsActive } from '@/config/navLinks'

const route = useRoute()
const auth = useAuthStore()

const staffItems = [
  { to: '/', labelKey: 'sidebar.dashboard', icon: 'fas fa-tachometer-alt', exact: true },
  { to: '/update', labelKey: 'sidebar.priceHub', icon: 'fas fa-dollar-sign', exact: false },
  { to: '/finalize', labelKey: 'sidebar.finalize', icon: 'fas fa-check-circle', exact: false },
]

const items = computed(() => staffItems)

function isActive(item) {
  return navLinkIsActive(route, item)
}
</script>
