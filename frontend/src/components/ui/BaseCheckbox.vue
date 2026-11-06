<template>
  <label class="control-check-label" :class="{ 'cursor-not-allowed opacity-60': disabled }">
    <input
      :id="id"
      class="control-check-input"
      type="checkbox"
      :checked="isChecked"
      :disabled="disabled"
      :aria-label="ariaLabel || label || undefined"
      @change="onChange"
    />
    <span class="control-check-mark" />
    <span v-if="label || $slots.default" class="text-sm text-[var(--text-primary)]">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [Boolean, Array],
    default: false,
  },
  value: {
    type: [String, Number, Boolean],
    default: true,
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

const isArrayMode = computed(() => Array.isArray(props.modelValue))
const isChecked = computed(() => {
  if (isArrayMode.value) return props.modelValue.includes(props.value)
  return Boolean(props.modelValue)
})

function onChange(event) {
  if (props.disabled) return
  const checked = event.target.checked
  if (!isArrayMode.value) {
    emit('update:modelValue', checked)
    return
  }
  const next = Array.isArray(props.modelValue) ? [...props.modelValue] : []
  const idx = next.findIndex((item) => item === props.value)
  if (checked && idx === -1) next.push(props.value)
  if (!checked && idx !== -1) next.splice(idx, 1)
  emit('update:modelValue', next)
}
</script>
