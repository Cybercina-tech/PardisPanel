<template>
  <nav v-if="crumbs.length > 1" class="flex items-center gap-1 text-sm py-3" :aria-label="$t('common.breadcrumb')">
    <template v-for="(crumb, idx) in crumbs">
      <router-link
        v-if="idx < crumbs.length - 1"
        :key="'link-' + crumb.path"
        :to="crumb.path"
        class="text-[var(--text-secondary)] hover:text-[var(--primary)] transition-colors"
      >
        {{ crumb.label }}
      </router-link>
      <span v-else :key="'current-' + crumb.path" class="text-[var(--primary)] font-medium">
        {{ crumb.label }}
      </span>
      <i
        v-if="idx < crumbs.length - 1"
        :key="'sep-' + crumb.path"
        class="fas text-xs text-[var(--text-secondary)] opacity-50"
        :class="isRtl ? 'fa-chevron-left' : 'fa-chevron-right'"
      />
    </template>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const { t, locale } = useI18n()

const isRtl = computed(() => locale.value === 'fa')

const crumbs = computed(() => {
  return route.matched
    .filter((r) => r.meta?.titleKey)
    .map((r) => ({
      path: r.path || '/',
      label: t(r.meta.titleKey),
    }))
})
</script>
