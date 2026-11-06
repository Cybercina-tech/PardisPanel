<template>
  <div class="relative w-full">
    <button
      ref="triggerRef"
      type="button"
      class="input-luxury flex w-full items-center justify-between gap-2 text-start"
      :class="{ 'opacity-60 cursor-not-allowed': disabled }"
      :disabled="disabled"
      aria-haspopup="listbox"
      :aria-expanded="open ? 'true' : 'false'"
      @click="toggleOpen"
    >
      <span class="inline-flex min-w-0 items-center gap-2">
        <span class="inline-flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-md border border-[var(--border-card)] bg-[var(--bg-card)]">
          <img
            v-if="selectedIcon"
            :src="selectedIcon"
            :alt="selected?.code || 'currency'"
            class="h-4 w-4 object-contain"
          />
          <span v-else class="text-[10px] font-semibold text-[var(--text-secondary)]">
            {{ selected?.code?.slice(0, 2) || '--' }}
          </span>
        </span>
        <span v-if="selected" class="truncate text-[var(--text-primary)]">
          {{ selected.code }} - {{ selected.name }}
        </span>
        <span v-else class="truncate text-[var(--text-secondary)]">
          {{ placeholder }}
        </span>
      </span>
      <i class="fas fa-chevron-down text-xs text-[var(--text-secondary)] transition-transform" :class="{ 'rotate-180': open }" />
    </button>

    <Teleport to="body">
      <div v-if="open" ref="panelRef" class="dropdown-panel" :style="panelStyle" role="listbox">
        <div class="mb-2 shrink-0">
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
          <li
            v-for="(item, index) in filteredOptions"
            :key="item.code"
          >
            <button
              type="button"
              role="option"
              :aria-selected="item[valueKey] === modelValue"
              class="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors"
              :class="index === activeIndex ? 'bg-primary-muted text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-primary-muted hover:text-[var(--text-primary)]'"
              @mouseenter="activeIndex = index"
              @click="select(item)"
            >
              <span class="inline-flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-md border border-[var(--border-card)] bg-[var(--bg-input)]">
                <img
                  v-if="iconFor(item.code)"
                  :src="iconFor(item.code)"
                  :alt="item.code"
                  class="h-4 w-4 object-contain"
                />
                <span v-else class="text-[10px] font-semibold">{{ item.code.slice(0, 2) }}</span>
              </span>
              <span class="min-w-0 flex-1 truncate text-start">{{ item.code }} - {{ item.name }}</span>
              <span v-if="item.symbol" class="text-xs opacity-80">{{ item.symbol }}</span>
            </button>
          </li>
          <li v-if="!filteredOptions.length" class="px-2 py-3 text-center text-xs text-[var(--text-secondary)]">
            {{ emptyText }}
          </li>
        </ul>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { getCurrencyIconByCode } from '@/utils/categoryIcons'
import { useAnchoredPanel } from '@/composables/useAnchoredPanel'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: '',
  },
  options: {
    type: Array,
    default: () => [],
  },
  valueKey: {
    type: String,
    default: 'id',
  },
  placeholder: {
    type: String,
    default: 'Select currency',
  },
  searchPlaceholder: {
    type: String,
    default: 'Search currency...',
  },
  emptyText: {
    type: String,
    default: 'No currency found',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const { triggerRef, panelRef, open, panelStyle, show, close } = useAnchoredPanel({ minWidth: 260 })

const searchRef = ref(null)
const search = ref('')
const activeIndex = ref(0)

const normalizedOptions = computed(() =>
  (Array.isArray(props.options) ? props.options : [])
    .filter((item) => item && item.code)
    .map((item) => ({ ...item, code: String(item.code).toUpperCase() }))
)

const selected = computed(() => normalizedOptions.value.find((item) => item[props.valueKey] === props.modelValue) ?? null)
const selectedIcon = computed(() => (selected.value ? iconFor(selected.value.code) : null))

const filteredOptions = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return normalizedOptions.value
  return normalizedOptions.value.filter((item) => {
    const symbol = String(item.symbol ?? '').toLowerCase()
    return item.code.toLowerCase().includes(q) || String(item.name ?? '').toLowerCase().includes(q) || symbol.includes(q)
  })
})

function iconFor(code) {
  return getCurrencyIconByCode(code)
}

function toggleOpen() {
  if (props.disabled) return
  if (open.value) {
    close()
    return
  }
  search.value = ''
  const idx = filteredOptions.value.findIndex((item) => item[props.valueKey] === props.modelValue)
  activeIndex.value = idx >= 0 ? idx : 0
  show()
  nextTick(() => searchRef.value?.focus())
}

function select(item) {
  emit('update:modelValue', item[props.valueKey])
  close()
}

function moveActive(step) {
  const total = filteredOptions.value.length
  if (!total) return
  activeIndex.value = (activeIndex.value + step + total) % total
}

function selectActive() {
  const item = filteredOptions.value[activeIndex.value]
  if (item) select(item)
}

watch(filteredOptions, (items) => {
  if (activeIndex.value >= items.length) activeIndex.value = Math.max(0, items.length - 1)
})
</script>
