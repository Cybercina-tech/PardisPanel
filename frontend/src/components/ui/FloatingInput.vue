<template>
  <div class="floating-input-group relative" :class="{ 'has-error': !!error, 'is-valid': showValid }">
    <component
      :is="multiline ? 'textarea' : 'input'"
      :id="inputId"
      ref="inputRef"
      :value="modelValue"
      :type="multiline ? undefined : type"
      :required="required"
      :disabled="disabled"
      :rows="multiline ? rows : undefined"
      class="floating-input peer w-full px-4 pt-5 pb-2 rounded-xl transition-all duration-300 ease-in-out bg-[var(--bg-input)] border text-[var(--text-primary)] placeholder-transparent focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
      :class="borderClass"
      placeholder=" "
      @input="handleInput"
      @focus="focused = true"
      @blur="handleBlur"
    />
    <label
      :for="inputId"
      class="floating-label absolute start-4 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] transition-all duration-200 ease-out pointer-events-none origin-[start_top] peer-focus:top-2.5 peer-focus:translate-y-0 peer-focus:text-xs peer-focus:text-[var(--primary)]"
      :class="{ 'top-2.5 translate-y-0 text-xs': hasValue }"
    >
      {{ label }}<span v-if="required" class="text-danger ms-0.5">*</span>
    </label>
    <div v-if="showIcon" class="absolute end-3 top-1/2 -translate-y-1/2 pointer-events-none">
      <i v-if="error" class="fas fa-exclamation-circle text-danger text-sm" />
      <i v-else-if="showValid" class="fas fa-check-circle text-success text-sm" />
    </div>
    <p v-if="error" class="mt-1.5 text-xs text-danger ps-1">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, getCurrentInstance } from 'vue'

let floatingInputCounter = 0

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, required: true },
  type: { type: String, default: 'text' },
  required: Boolean,
  disabled: Boolean,
  error: String,
  multiline: Boolean,
  rows: { type: Number, default: 3 },
  rules: { type: Array, default: () => [] },
  id: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'validate'])

const inputRef = ref(null)
const focused = ref(false)
const touched = ref(false)

const instance = getCurrentInstance()
const localId = `floating-${instance?.uid ?? 'x'}-${++floatingInputCounter}`
const inputId = computed(() => props.id || localId)

const hasValue = computed(() => props.modelValue !== '' && props.modelValue != null)
const showValid = computed(() => touched.value && hasValue.value && !props.error)
const showIcon = computed(() => touched.value && (!!props.error || showValid.value))

const borderClass = computed(() => {
  if (props.error) return 'border-danger focus:border-danger focus:ring-2 focus:ring-danger/20'
  if (focused.value) return 'border-[var(--primary)] ring-2 ring-[var(--primary)]/10'
  if (showValid.value) return 'border-success/50'
  return 'border-[var(--border-color)]'
})

function handleInput(e) {
  emit('update:modelValue', e.target.value)
  if (touched.value) validate(e.target.value)
}

function handleBlur() {
  focused.value = false
  touched.value = true
  validate(props.modelValue)
}

function validate(value) {
  for (const rule of props.rules) {
    const result = rule(value)
    if (typeof result === 'string') {
      emit('validate', result)
      return
    }
  }
  emit('validate', null)
}
</script>

<style scoped>
.floating-input-group .floating-label {
  line-height: 1;
}

textarea.floating-input ~ .floating-label {
  top: 1.25rem;
}
</style>
