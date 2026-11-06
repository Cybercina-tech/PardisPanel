<template>
  <div
    v-if="show"
    class="p-4 rounded-xl border flex items-center gap-3 mb-4"
    :class="variantClass"
  >
    <i :class="iconClass" class="text-lg flex-shrink-0"></i>
    <div class="flex-1">
      <slot></slot>
    </div>
    <button
      v-if="dismissible"
      @click="$emit('dismiss')"
      class="p-1 rounded hover:bg-white/10 transition-colors"
      :aria-label="$t('common.dismiss')"
    >
      <i class="fas fa-times"></i>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: true },
  type: { type: String, default: 'info' }, // success, error, warning, info
  dismissible: { type: Boolean, default: false },
})

const variantClass = computed(() => {
  const map = {
    success: 'bg-green-500/10 border-green-500/30 text-green-200',
    error: 'bg-red-500/10 border-red-500/30 text-red-200',
    warning: 'bg-amber-500/10 border-amber-500/30 text-amber-200',
    info: 'bg-blue-500/10 border-blue-500/30 text-blue-200',
  }
  return map[props.type] ?? map.info
})

const iconClass = computed(() => {
  const map = {
    success: 'fas fa-check-circle text-green-400',
    error: 'fas fa-exclamation-circle text-red-400',
    warning: 'fas fa-exclamation-triangle text-amber-400',
    info: 'fas fa-info-circle text-blue-400',
  }
  return map[props.type] ?? map.info
})
</script>
