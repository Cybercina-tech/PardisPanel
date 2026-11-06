<template>
  <!--
    With its own label the switch is a full-width row and spreads to the edges.
    Bare — inside a row that already has a label of its own — it is just the
    control: `w-full` there made it claim the whole flex line and sit on top of
    the neighbouring text. A bare switch is also not a <label>, since it is
    almost always nested inside one.
  -->
  <component
    :is="hasLabel ? 'label' : 'span'"
    class="inline-flex items-center gap-3"
    :class="[
      hasLabel ? 'w-full justify-between' : 'shrink-0',
      { 'cursor-not-allowed opacity-60': disabled },
    ]"
  >
    <span v-if="hasLabel" class="min-w-0 text-sm text-[var(--text-primary)]">
      <slot>{{ label }}</slot>
    </span>
    <button
      type="button"
      role="switch"
      class="control-switch"
      :data-on="isOn ? 'true' : 'false'"
      :data-size="size"
      :aria-checked="isOn ? 'true' : 'false'"
      :aria-label="ariaLabel || label || undefined"
      :disabled="disabled"
      @click="toggle"
    >
      <span class="control-switch-thumb" />
    </button>
  </component>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
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
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md'].includes(v),
  },
})

const emit = defineEmits(['update:modelValue'])

const slots = useSlots()
const hasLabel = computed(() => Boolean(props.label || slots.default))
const isOn = computed(() => Boolean(props.modelValue))

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !isOn.value)
}
</script>
