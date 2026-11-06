<template>
  <div
    class="flex h-full w-full items-center justify-center"
    :class="src ? 'bg-transparent' : 'rounded-md bg-[var(--bg-input)]/40'"
  >
    <img
      v-if="src"
      :src="src"
      alt=""
      class="pointer-events-none max-h-full max-w-full select-none object-contain [-webkit-user-drag:none]"
      :style="imgStyle"
      draggable="false"
    />
    <span v-else class="text-xs text-[var(--text-secondary)]">{{ $t('templateEditor.imageUrl') }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  widget: { type: Object, required: true },
})

const src = computed(() => {
  const c = props.widget?.content
  return c && String(c).trim() ? String(c).trim() : ''
})

const imgStyle = computed(() => {
  const s = props.widget?.style || {}
  let o = s.opacity != null && s.opacity !== '' ? s.opacity : 1
  if (typeof o === 'string' && o.trim().endsWith('%')) {
    o = Number(o.replace('%', '')) / 100
  } else {
    o = Number(o)
  }
  if (!Number.isFinite(o)) o = 1
  o = Math.min(1, Math.max(0, o))
  return { opacity: String(o) }
})
</script>
