<template>
  <component
    :is="tag"
    :type="tag === 'button' ? nativeType : undefined"
    :to="tag === 'router-link' ? to : undefined"
    :disabled="disabled || loading"
    class="base-button inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all duration-300 ease-in-out disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
    :class="[
      sizeClasses[size],
      variantClasses[variant],
    ]"
    @click="handleClick"
  >
    <template v-if="loading">
      <span
        class="inline-block w-4 h-4 border-2 rounded-full animate-spin"
        style="border-color: currentColor; border-top-color: transparent;"
      />
      <span v-if="$slots.default"><slot /></span>
    </template>
    <template v-else>
      <slot />
    </template>
  </component>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'outline', 'ghost'].includes(v),
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v),
  },
  loading: Boolean,
  disabled: Boolean,
  to: String,
  nativeType: {
    type: String,
    default: 'button',
  },
})

const emit = defineEmits(['click'])

const tag = computed(() => (props.to ? 'router-link' : 'button'))

const sizeClasses = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-2.5 text-sm',
  lg: 'px-8 py-3 text-base',
}

const variantClasses = {
  primary:
    'bg-[var(--primary)] text-[var(--text-on-primary)] border border-[var(--border-color)] hover:bg-[var(--primary-hover)] hover:-translate-y-0.5',
  outline:
    'bg-transparent border border-[var(--primary)] text-[var(--primary)] hover:bg-[var(--primary-muted)] hover:-translate-y-0.5',
  ghost:
    'bg-transparent border border-transparent text-[var(--text-primary)] hover:bg-[var(--bg-hover)]',
}

function handleClick(e) {
  if (!props.loading && !props.disabled) emit('click', e)
}
</script>
