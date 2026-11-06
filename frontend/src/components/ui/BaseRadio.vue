<template>
  <label class="control-radio-label" :class="{ 'cursor-not-allowed opacity-60': disabled }">
    <input
      :id="id"
      class="control-radio-input"
      type="radio"
      :name="name"
      :value="value"
      :checked="isChecked"
      :disabled="disabled"
      :aria-label="ariaLabel || label || undefined"
      @change="onChange"
    />
    <span class="control-radio-mark" />
    <span v-if="label || $slots.default" class="text-sm text-[var(--text-primary)]">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: null,
  },
  value: {
    type: [String, Number, Boolean],
    required: true,
  },
  name: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: '',
  },
  ariaLabel: {
    type: String,
    default: '',
  },
  id: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])
const isChecked = computed(() => props.modelValue === props.value)

function onChange() {
  if (props.disabled) return
  emit('update:modelValue', props.value)
}
</script>
