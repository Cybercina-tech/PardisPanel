<template>
  <div class="min-w-0 w-full">
    <label
      v-if="label"
      :id="labelId"
      class="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
    >
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <BaseSelect
      :model-value="modelValue"
      :options="options"
      :placeholder="placeholder"
      :disabled="disabled"
      :error="!!error"
      :labelledby="labelId"
      :empty-text="emptyText"
      @update:model-value="emit('update:modelValue', $event)"
      @blur="emit('blur')"
    />
    <p
      v-if="error"
      class="mt-1.5 flex items-start gap-1.5 text-sm text-red-500"
      role="alert"
    >
      <i class="fas fa-exclamation-circle mt-0.5 text-xs" />
      <span class="min-w-0 break-words">{{ error }}</span>
    </p>
    <p v-else-if="hint" class="mt-1.5 text-xs text-[var(--text-secondary)]">
      {{ hint }}
    </p>
  </div>
</template>

<script setup>
import { useId } from 'vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  emptyText: { type: String, default: '—' },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  options: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue', 'blur'])

const labelId = props.label ? useId() : undefined
</script>
