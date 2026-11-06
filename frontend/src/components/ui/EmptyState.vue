<template>
  <div class="flex flex-col items-center justify-center py-16 px-4 text-center">
    <div
      class="w-20 h-20 rounded-2xl mx-auto mb-6 flex items-center justify-center bg-primary-muted border border-[var(--border-color)]"
    >
      <i :class="icon" class="text-3xl text-[var(--primary)] opacity-70" />
    </div>
    <h3 class="text-lg font-bold text-[var(--text-primary)] mb-2">
      {{ $t(titleKey) }}
    </h3>
    <p v-if="descriptionKey" class="text-sm text-[var(--text-secondary)] mb-8 max-w-sm">
      {{ $t(descriptionKey) }}
    </p>
    <router-link v-if="actionTo" :to="actionTo">
      <button class="btn-luxury">
        <i v-if="actionIcon" :class="actionIcon" />
        {{ $t(actionLabel) }}
      </button>
    </router-link>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    default: 'fas fa-inbox',
  },
  titleKey: {
    type: String,
    required: true,
  },
  descriptionKey: {
    type: String,
    default: '',
  },
  actionLabel: {
    type: String,
    default: '',
  },
  actionTo: {
    type: String,
    default: '',
  },
  actionIcon: {
    type: String,
    default: 'fas fa-plus',
  },
})
</script>
