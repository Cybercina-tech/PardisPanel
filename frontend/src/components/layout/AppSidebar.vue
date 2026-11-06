<template>
  <aside
    :class="[
      'app-sidebar hidden md:flex md:flex-col md:fixed md:inset-y-0 z-40 transition-all duration-300 ease-in-out bg-[var(--bg-navbar)]',
      'md:w-16',
      isCollapsed ? 'lg:w-16' : 'lg:w-64',
    ]"
    style="border-color: var(--border-card); inset-inline-start: 0; border-inline-end: 1px solid var(--border-card);"
  >
    <div
      class="flex items-center gap-3 px-2 py-5 border-b shrink-0 transition-all duration-300 ease-in-out md:justify-center"
      :class="isCollapsed ? 'lg:justify-center lg:px-2' : 'lg:justify-start lg:px-6'"
      style="border-color: var(--border-card);"
    >
      <router-link
        to="/panel"
        class="flex items-center gap-3 group min-w-0 md:justify-center"
        :class="isCollapsed ? '' : 'lg:justify-start'"
      >
        <AppBrandLogo size="md" rounded="xl" class="group-hover:scale-105 transition-all duration-300 ease-in-out shrink-0" />
        <!-- Text hidden on mobile/tablet and when collapsed; only icons visible in collapsed mode -->
        <div
          class="flex flex-col min-w-0 overflow-hidden transition-all duration-300 ease-in-out hidden md:hidden"
          :class="!isCollapsed ? 'lg:flex' : ''"
        >
          <span class="text-lg font-bold leading-tight text-[var(--primary)] truncate whitespace-nowrap">
            {{ siteName }}
          </span>
          <span class="text-xs text-[var(--text-secondary)] font-medium hidden sm:block truncate whitespace-nowrap">
            {{ tagline }}
          </span>
        </div>
      </router-link>
    </div>
    <nav
      class="flex-1 overflow-y-auto overflow-x-hidden py-4 px-2 transition-all duration-300 ease-in-out"
      :class="!isCollapsed ? 'lg:px-4' : 'lg:px-2'"
    >
      <ul class="space-y-1">
        <li
          v-for="(link, index) in visibleLinks"
          :key="link.to"
          :class="startsNavGroup(visibleLinks, index) ? 'nav-group-start' : ''"
        >
          <router-link
            :to="link.to"
            class="sidebar-link flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-300 ease-in-out text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] md:justify-center md:px-2 md:min-w-0"
            :class="[
              isActive(link)
                ? ['bg-[var(--bg-hover)]', link.activeColor === 'gold' ? 'text-gold' : link.activeColor === 'buy' ? 'text-buy' : link.activeColor === 'info' ? 'text-info' : 'text-template']
                : 'hover:text-[var(--primary)]',
              !isCollapsed ? 'lg:justify-start lg:px-4' : 'lg:justify-center lg:px-2',
            ]"
          >
            <span class="relative shrink-0 flex-shrink-0">
              <i :class="link.icon" class="text-base w-5 text-center" />
              <!-- Collapsed rail has no label to sit beside, so the count rides the icon;
                   hidden once the label (with its own inline count) is shown. -->
            </span>
            <!-- Label hidden on tablet and when collapsed; only icon visible -->
            <span
              class="font-medium whitespace-nowrap overflow-hidden hidden md:hidden items-center gap-2"
              :class="!isCollapsed ? 'lg:inline-flex' : ''"
            >
              {{ $t(link.labelKey) }}
            </span>
          </router-link>
        </li>
      </ul>
    </nav>
    <div class="p-2 border-t shrink-0 hidden lg:block transition-all duration-300 ease-in-out" style="border-color: var(--border-card);">
      <button
        type="button"
        class="w-full flex items-center justify-center py-2.5 rounded-xl transition-all duration-300 ease-in-out border border-[var(--border-color)] bg-[var(--bg-navbar)] hover:bg-[var(--bg-hover)] hover:border-[var(--border-card-hover)] text-[var(--text-secondary)] hover:text-[var(--primary)]"
        :aria-label="$t('common.toggleSidebar')"
        @click="toggleSidebar"
      >
        <i
          :class="isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left'"
          class="text-sm"
        />
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import { useAuthStore } from '@/stores/auth'
import { useSidebarStore } from '@/stores/sidebar'
import { navLinkIsActive, startsNavGroup, visibleNavLinks } from '@/config/navLinks'
import AppBrandLogo from '@/components/layout/AppBrandLogo.vue'

const route = useRoute()
const siteSettings = useSiteSettingsStore()
const auth = useAuthStore()
const sidebarStore = useSidebarStore()

/* The store is the only copy: a local ref here used to shadow it, so anything
   else that collapsed the rail moved the page padding and not the rail. */
const isCollapsed = computed(() => sidebarStore.isCollapsed)
function toggleSidebar() {
  sidebarStore.toggle()
}

const siteName = computed(() => siteSettings.siteName)
const tagline = computed(() => siteSettings.tagline)

const visibleLinks = computed(() => visibleNavLinks(auth))

function isActive(link) {
  return navLinkIsActive(route, link)
}
</script>

<style scoped>
/* A rule between workflow phases: pricing, publishing, reporting, admin. */
.nav-group-start {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-card);
}
</style>
