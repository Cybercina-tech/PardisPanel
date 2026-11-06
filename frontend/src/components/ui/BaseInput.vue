<template>
  <div class="base-input-wrapper">
    <input
      :value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      class="base-input w-full px-4 py-3 rounded-xl transition-all duration-300 ease-in-out bg-[var(--bg-input)] border border-[var(--border-color)] text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20 disabled:opacity-60 disabled:cursor-not-allowed"
      :class="{ 'input-error': error }"
      @input="emit('update:modelValue', $event.target.value)"
    />
    <p v-if="error" class="mt-1.5 text-sm text-red-500">{{ error }}</p>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: [String, Number],
    default: '',
  },
  type: {
    type: String,
    default: 'text',
  },
  placeholder: String,
  disabled: Boolean,
  error: String,
})

const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.input-error {
  border-color: rgb(239 68 68) !important;
}
</style>
