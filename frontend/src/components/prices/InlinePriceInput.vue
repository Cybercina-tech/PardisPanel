<template>
  <form class="inline-flex items-center gap-1.5" @submit.prevent="submit">
    <input
      ref="inputEl"
      v-model="draftValue"
      type="text"
      inputmode="decimal"
      class="w-28 rounded-md border border-[var(--border-color)] bg-[var(--bg-card)] px-2 py-1 text-sm text-[var(--text-primary)] focus:border-gold focus:outline-none"
      :placeholder="placeholder"
      @keydown.esc.prevent="cancel"
    />
    <button
      type="submit"
      class="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300 transition hover:bg-emerald-500/20"
      :disabled="saving"
    >
      <i v-if="saving" class="fas fa-spinner fa-spin"></i>
      <span v-else>{{ $t('common.save') }}</span>
    </button>
    <button
      type="button"
      class="rounded-md border border-[var(--border-color)] px-2 py-1 text-xs text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
      :disabled="saving"
      @click="cancel"
    >
      {{ $t('common.cancel') }}
    </button>
  </form>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: [Number, String, null],
    default: null,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  placeholder: {
    type: String,
    default: '0',
  },
})

const emit = defineEmits(['save', 'cancel'])

const inputEl = ref(null)
const draftValue = ref(props.modelValue == null ? '' : String(props.modelValue))

watch(
  () => props.modelValue,
  (val) => {
    draftValue.value = val == null ? '' : String(val)
    nextTick(() => inputEl.value?.focus())
  },
  { immediate: true }
)

function submit() {
  emit('save', draftValue.value)
}

function cancel() {
  emit('cancel')
}
</script>
