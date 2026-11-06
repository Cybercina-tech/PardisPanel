<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div
        v-show="open"
        class="fixed inset-0 z-50 flex md:hidden"
        aria-modal="true"
        role="dialog"
      >
        <div
          class="fixed inset-0 bg-black/60 transition-opacity duration-300 ease-in-out"
          aria-hidden="true"
          @click="$emit('close')"
        />
        <Transition name="drawer-panel">
          <aside
            v-show="open"
            class="drawer-aside fixed top-0 bottom-0 w-full sm:max-w-xs flex flex-col bg-[var(--bg-navbar)] shadow-xl"
            style="inset-inline-start: 0; border-inline-end: 1px solid var(--border-card);"
          >
            <div class="flex items-center justify-between px-6 py-5 border-b" style="border-color: var(--border-card);">
              <router-link to="/panel" class="flex items-center gap-3" @click="$emit('close')">
                <AppBrandLogo size="md" rounded="xl" />
                <span class="text-lg font-bold text-[var(--primary)]">{{ siteName }}</span>
              </router-link>
              <button
                class="w-10 h-10 rounded-xl flex items-center justify-center text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--primary)] transition-all duration-300"
                :aria-label="$t('header.closeMenu')"
                @click="$emit('close')"
              >
                <i class="fas fa-times text-xl" />
              </button>
            </div>
            <nav class="flex-1 overflow-y-auto py-4 px-3">
              <ul class="space-y-1">
                <li
                  v-for="(link, index) in visibleLinks"
                  :key="link.to"
                  :class="startsNavGroup(visibleLinks, index) ? 'nav-group-start' : ''"
                >
                  <router-link
                    :to="link.to"
                    class="drawer-link flex items-center gap-3 px-4 py-3 min-h-[48px] rounded-xl transition-all duration-300 ease-in-out text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                    :class="[
                      isActive(link)
                        ? ['bg-[var(--bg-hover)]', link.activeColor === 'gold' ? 'text-gold' : link.activeColor === 'buy' ? 'text-buy' : link.activeColor === 'info' ? 'text-info' : 'text-template']
                        : 'hover:text-[var(--primary)]',
                    ]"
                    @click="$emit('close')"
                  >
                    <i :class="link.icon" class="text-base w-5 text-center" />
                    <span class="font-medium">{{ $t(link.labelKey) }}</span>
                  </router-link>
                </li>
              </ul>
            </nav>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import { useAuthStore } from '@/stores/auth'
import { navLinkIsActive, startsNavGroup, visibleNavLinks } from '@/config/navLinks'
import AppBrandLogo from '@/components/layout/AppBrandLogo.vue'

defineProps({
  open: Boolean,
})

defineEmits(['close'])

const route = useRoute()
const siteSettings = useSiteSettingsStore()
const auth = useAuthStore()

const siteName = computed(() => siteSettings.siteName)

const visibleLinks = computed(() => visibleNavLinks(auth))

function isActive(link) {
  return navLinkIsActive(route, link)
}
</script>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.3s ease-in-out;
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(calc(-100% * var(--drawer-dir, 1)));
}

:root[dir="rtl"] .drawer-aside {
  --drawer-dir: -1;
}
:root[dir="ltr"] .drawer-aside {
  --drawer-dir: 1;
}

/* Matches the desktop rail: a rule between workflow phases. */
.nav-group-start {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-card);
}
</style>
