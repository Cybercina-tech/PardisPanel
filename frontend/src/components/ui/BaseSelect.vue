<template>
  <div class="w-full min-w-0">
    <button
      ref="triggerRef"
      type="button"
      class="input-luxury flex w-full items-center justify-between gap-2 text-start"
      :class="[
        disabled ? 'cursor-not-allowed opacity-60' : '',
        error ? '!border-red-500' : '',
      ]"
      :disabled="disabled"
      :aria-haspopup="'listbox'"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-labelledby="labelledby || undefined"
      @click="onTriggerClick"
      @keydown.down.prevent="openAndMove(1)"
      @keydown.up.prevent="openAndMove(-1)"
      @keydown.enter.prevent="onTriggerClick"
      @keydown.esc.prevent="close"
    >
      <span class="min-w-0 truncate" :class="selected ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'">
        {{ selected ? selected.label : placeholder }}
      </span>
      <i
        class="fas fa-chevron-down shrink-0 text-xs text-[var(--text-secondary)] transition-transform"
        :class="{ 'rotate-180': open }"
      />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="panelRef"
        class="dropdown-panel"
        :style="panelStyle"
        role="listbox"
        :dir="dir"
      >
        <div v-if="searchable" class="mb-2 shrink-0">
          <input
            ref="searchRef"
            v-model.trim="search"
            type="text"
            class="input-luxury !py-2 text-sm"
            :placeholder="searchPlaceholder"
            @keydown.down.prevent="moveActive(1)"
            @keydown.up.prevent="moveActive(-1)"
            @keydown.enter.prevent="selectActive"
            @keydown.esc.prevent="close"
            @keydown.tab="close"
          />
        </div>

        <ul class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <li v-for="(opt, index) in filtered" :key="String(opt.value)">
            <button
              type="button"
              role="option"
              :aria-selected="opt.value === modelValue"
              :disabled="opt.disabled"
              class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-start text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              :class="index === activeIndex
                ? 'bg-primary-muted text-[var(--text-primary)]'
                : 'text-[var(--text-secondary)] hover:bg-primary-muted hover:text-[var(--text-primary)]'"
              @mouseenter="activeIndex = index"
              @click="select(opt)"
            >
              <span class="min-w-0 flex-1 truncate">{{ opt.label }}</span>
              <i v-if="opt.value === modelValue" class="fas fa-check shrink-0 text-xs text-[var(--primary)]" />
            </button>
          </li>
          <li v-if="!filtered.length" class="px-3 py-4 text-center text-xs text-[var(--text-secondary)]">
            {{ emptyText }}
          </li>
        </ul>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useAnchoredPanel } from '@/composables/useAnchoredPanel'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean, null], default: '' },
  /** `{ value, label, disabled? }`; plain strings are accepted as both. */
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' },
  searchPlaceholder: { type: String, default: '' },
  emptyText: { type: String, default: '—' },
  disabled: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
  /** Filter box appears automatically past this many options. */
  searchThreshold: { type: Number, default: 8 },
  labelledby: { type: String, default: '' },
  dir: { type: String, default: 'auto' },
})

const emit = defineEmits(['update:modelValue', 'change', 'blur'])

const { triggerRef, panelRef, open, panelStyle, show, close, toggle } = useAnchoredPanel()

const searchRef = ref(null)
const search = ref('')
const activeIndex = ref(0)

const normalized = computed(() =>
  (Array.isArray(props.options) ? props.options : []).map((opt) =>
    opt !== null && typeof opt === 'object'
      ? { value: opt.value, label: String(opt.label ?? opt.value ?? ''), disabled: !!opt.disabled }
      : { value: opt, label: String(opt), disabled: false },
  ),
)

const searchable = computed(() => normalized.value.length > props.searchThreshold)

const selected = computed(() => normalized.value.find((opt) => opt.value === props.modelValue) ?? null)

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return normalized.value
  return normalized.value.filter((opt) => opt.label.toLowerCase().includes(q))
})

function onTriggerClick() {
  if (props.disabled) return
  if (open.value) {
    close()
    return
  }
  search.value = ''
  const idx = normalized.value.findIndex((opt) => opt.value === props.modelValue)
  activeIndex.value = idx >= 0 ? idx : 0
  show()
  if (searchable.value) nextTick(() => searchRef.value?.focus())
}

function openAndMove(step) {
  if (props.disabled) return
  if (!open.value) {
    onTriggerClick()
    return
  }
  moveActive(step)
}

function moveActive(step) {
  const total = filtered.value.length
  if (!total) return
  activeIndex.value = (activeIndex.value + step + total) % total
}

function select(opt) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  close()
  emit('blur')
  triggerRef.value?.focus()
}

function selectActive() {
  const opt = filtered.value[activeIndex.value]
  if (opt) select(opt)
}

watch(filtered, (items) => {
  if (activeIndex.value >= items.length) activeIndex.value = Math.max(0, items.length - 1)
})

watch(() => props.disabled, (isDisabled) => {
  if (isDisabled) close()
})
</script>
