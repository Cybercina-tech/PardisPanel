<template>
  <div class="min-h-screen flex bg-slate-50 dark:bg-[var(--bg-base)] transition-colors duration-500 max-w-[100vw] overflow-x-hidden">
    <AppSidebar />
    <AppDrawer :open="drawerOpen" @close="drawerOpen = false" />
    <div
      class="flex min-h-0 flex-1 flex-col min-w-0 overflow-x-hidden transition-[padding] duration-300 ease-in-out pb-16 md:pb-0 w-full"
      :class="['md:ps-16', sidebarStore.isCollapsed ? 'lg:ps-16' : 'lg:ps-64']"
    >
      <div
        v-if="auth.isImpersonating"
        class="flex items-center justify-between gap-3 px-4 py-2 bg-amber-500/20 text-amber-200 text-sm"
      >
        <span>
          {{ $t('programmerHub.viewingAs', { name: auth.user?.username }) }}
        </span>
        <button type="button" class="btn-luxury-outline !py-1 !px-3 text-xs" @click="exitImpersonation">
          {{ $t('programmerHub.exit') }}
        </button>
      </div>
      <AppHeader @toggle-drawer="drawerOpen = !drawerOpen" />
      <main
        class="flex min-w-0 flex-1 flex-col overflow-x-hidden"
        :class="
          isTemplateEditorLayout
            ? 'min-h-0 overflow-hidden py-0 px-0'
            : isWideLayout
              ? 'min-h-0 overflow-x-hidden py-3 px-3 sm:px-4'
              : 'min-h-0 overflow-x-hidden py-4 px-3 sm:px-4 lg:px-5'
        "
      >
        <div
          class="flex w-full min-w-0 flex-col"
          :class="
            isTemplateEditorLayout || isWideLayout
              ? 'mx-0 max-w-none flex-1 min-h-0'
              : 'mx-auto max-w-7xl flex-1 min-h-0'
          "
        >
          <AppBreadcrumb v-if="!isTemplateEditorLayout && !isWideLayout" />
          <router-view v-slot="{ Component }">
            <Transition name="page" mode="out-in">
              <component :is="Component" class="min-h-0 flex-1" />
            </Transition>
          </router-view>
        </div>
      </main>
      <AppFooter v-if="!isTemplateEditorLayout && !isWideLayout && !route.meta.fixedActionBar" />
    </div>
    <AppBottomNav />
    <OnboardingTour :open="tourOpen" @close="closeTour" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AppSidebar, AppHeader, AppDrawer, AppFooter, AppBreadcrumb, AppBottomNav } from '@/components/layout'
import OnboardingTour from '@/components/onboarding/OnboardingTour.vue'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import { useSidebarStore } from '@/stores/sidebar'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const drawerOpen = ref(false)
/* The tour opens itself once per browser: helpful on arrival, not on every click. */
const tourOpen = ref(false)
const siteSettings = useSiteSettingsStore()
const sidebarStore = useSidebarStore()
const auth = useAuthStore()

const isTemplateEditorLayout = computed(() => Boolean(route.meta.templateEditorLayout))

/**
 * Pages that are mostly a canvas — the website builder previewing a real site —
 * get the whole width and hold the navigation rail shut while they are open.
 * A customer's homepage squeezed into a 1280px column between panel furniture
 * is not a preview of anything they will ever ship.
 */
const isWideLayout = computed(() => Boolean(route.meta.wideLayout))

watch(
  isWideLayout,
  (wide) => sidebarStore.force(wide),
  { immediate: true },
)
onUnmounted(() => sidebarStore.force(false))

async function exitImpersonation() {
  await auth.stopImpersonating()
  router.push('/panel')
}

/* Closing the tour is what marks onboarding done — a failed call just means it
   offers itself again next time, which is better than losing it silently. */
async function closeTour() {
  tourOpen.value = false
  if (!auth.needsOnboarding) return
  try {
    await auth.completeOnboarding()
  } catch {
    /* ignore */
  }
}

watch(
  () => auth.needsOnboarding,
  (needed) => {
    if (needed) tourOpen.value = true
  },
)

onMounted(() => {
  siteSettings.fetch()
  if (auth.needsOnboarding) tourOpen.value = true
})

</script>
