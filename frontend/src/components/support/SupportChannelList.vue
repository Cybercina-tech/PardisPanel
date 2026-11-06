<template>
  <div v-if="channels.length" class="support-channels" :class="{ 'support-channels--inline': inline }">
    <component
      :is="channel.href ? 'a' : 'span'"
      v-for="channel in channels"
      :key="`${channel.kind}-${channel.value}`"
      class="support-channels__item"
      :href="channel.href || undefined"
      :target="channel.href?.startsWith('http') ? '_blank' : undefined"
      :rel="channel.href?.startsWith('http') ? 'noopener' : undefined"
    >
      <i :class="channel.icon" aria-hidden="true" />
      <span class="support-channels__label">{{ channel.label }}</span>
      <span class="support-channels__value" dir="ltr">{{ channel.value }}</span>
    </component>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSiteSettingsStore } from '@/stores/siteSettings'

const props = defineProps({
  /* Row of chips instead of a stacked list — for footers and banners. */
  inline: { type: Boolean, default: false },
  /* Render these instead of the saved ones — the owner console previews edits. */
  items: { type: Array, default: null },
})

const siteSettings = useSiteSettingsStore()
const channels = computed(() => props.items ?? siteSettings.supportChannels)
</script>

<style scoped>
.support-channels {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.support-channels--inline {
  flex-direction: row;
  flex-wrap: wrap;
}

.support-channels__item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  font-size: 0.75rem;
  border-radius: 0.65rem;
  border: 1px solid var(--border-card);
  color: var(--text-primary);
  transition: all 0.25s ease;
}

a.support-channels__item:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.support-channels__item i {
  color: var(--primary);
}

.support-channels__label {
  font-weight: 600;
}

.support-channels__value {
  margin-inline-start: auto;
  color: var(--text-secondary);
}
</style>
