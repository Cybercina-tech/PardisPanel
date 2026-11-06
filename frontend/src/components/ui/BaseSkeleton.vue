<template>
  <div
    class="base-skeleton animate-pulse rounded-xl bg-[var(--bg-hover)]"
    :class="variantClasses[variant]"
    :style="customStyle"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'text',
    validator: (v) => ['text', 'card', 'avatar', 'table-row'].includes(v),
  },
  width: String,
  height: String,
})

const customStyle = computed(() => {
  const s = {}
  if (props.width) s.width = props.width
  if (props.height) s.height = props.height
  return s
})

const variantClasses = {
  text: 'h-4 w-full max-w-[200px]',
  card: 'h-24 w-full',
  avatar: 'h-10 w-10 rounded-full',
  'table-row': 'h-12 w-full',
}
</script>
