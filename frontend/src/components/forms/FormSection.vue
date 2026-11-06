<template>
  <section class="card-luxury w-full px-4 py-5 sm:px-6 sm:py-6">
    <header class="mb-5 flex items-start gap-3">
      <span
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-muted text-[var(--primary)]"
      >
        <i :class="[icon, 'text-lg']" />
      </span>
      <div class="min-w-0">
        <h2 class="text-base font-bold text-[var(--text-primary)]">{{ title }}</h2>
        <p v-if="description" class="mt-0.5 text-sm text-[var(--text-secondary)]">
          {{ description }}
        </p>
      </div>
    </header>
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  icon: { type: String, default: 'fas fa-circle-info' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>
