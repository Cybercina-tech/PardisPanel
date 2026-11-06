<template>
  <div class="min-w-0 w-full">
    <label
      v-if="label"
      :for="id"
      class="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
    >
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <input
      :id="id"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :required="required"
      :inputmode="inputmode"
      :autocomplete="autocomplete || undefined"
      class="input-luxury w-full disabled:opacity-60 disabled:cursor-not-allowed"
      :class="{ '!border-red-500 focus:!ring-red-500/20': error }"
      @input="emit('update:modelValue', $event.target.value)"
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
    <p
      v-else-if="hint"
      class="mt-1.5 text-xs text-[var(--text-secondary)]"
    >
      {{ hint }}
    </p>
  </div>
</template>

<script setup>
import { useId } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  inputmode: { type: String, default: '' },
  autocomplete: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'blur'])

const id = props.label ? useId() : undefined
</script>
