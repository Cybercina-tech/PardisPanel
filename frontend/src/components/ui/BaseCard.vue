<template>
  <div
    class="base-card rounded-2xl transition-all duration-300 ease-in-out"
    :class="[
      paddingClasses[padding],
      variantClasses[variant],
      {
        'hover:shadow-md hover:border-slate-200 dark:hover:shadow-glow dark:hover:border-[var(--border-card-hover)]':
          hover && variant === 'default',
      },
      {
        'hover:scale-[1.01] hover:shadow-xl hover:border-slate-200 dark:hover:shadow-lg dark:hover:border-[var(--border-card-hover)]':
          hover && variant === 'elevated',
      },
    ]"
  >
    <slot />
  </div>
</template>

<script setup>
defineProps({
  padding: {
    type: String,
    default: 'default',
    validator: (v) => ['none', 'sm', 'default', 'lg'].includes(v),
  },
  hover: {
    type: Boolean,
    default: true,
  },
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'glass', 'elevated'].includes(v),
  },
})

const paddingClasses = {
  none: 'p-0',
  sm: 'p-4',
  default: 'p-6',
  lg: 'p-8',
}

const variantClasses = {
  default:
    'bg-white border border-slate-100 shadow-sm dark:bg-[var(--bg-card)] dark:border-[var(--border-card)] dark:shadow-soft',
  glass: 'glass',
  elevated:
    'bg-white border border-slate-100 shadow-md dark:bg-[var(--bg-elevated)] dark:border-[var(--border-card)] dark:shadow-card',
}
</script>
