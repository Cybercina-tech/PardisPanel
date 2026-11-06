<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="ariaLabel"
        @click.self="close"
      >
        <div
          class="modal-backdrop absolute inset-0 bg-black/50 backdrop-blur-xl"
          aria-hidden="true"
        />
        <div
          class="modal-panel relative w-full max-w-lg max-h-[90vh] flex flex-col rounded-2xl overflow-hidden shadow-2xl"
          :class="panelClass"
          @click.stop
        >
          <header
            class="flex items-center justify-between gap-4 px-6 py-4 border-b shrink-0"
            style="border-color: var(--glass-border); background: var(--glass-bg);"
          >
            <slot name="header">
              <h2 class="text-lg font-bold text-[var(--text-primary)]">
                {{ title }}
              </h2>
            </slot>
            <button
              type="button"
              class="flex items-center justify-center w-10 h-10 rounded-xl text-[var(--text-secondary)] hover:text-[var(--primary)] hover:bg-[var(--bg-hover)] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--bg-base)]"
              :aria-label="$t('common.close')"
              @click="close"
            >
              <i class="fas fa-times text-lg" />
            </button>
          </header>
          <div class="modal-body flex-1 overflow-y-auto p-6">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  ariaLabel: { type: String, default: '' },
  panelClass: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}

function onKeydown(e) {
  if (e.key === 'Escape') close()
}

watch(() => props.modelValue, (open) => {
  if (open) {
    document.addEventListener('keydown', onKeydown)
    document.body.style.overflow = 'hidden'
  } else {
    document.removeEventListener('keydown', onKeydown)
    document.body.style.overflow = ''
  }
}, { immediate: true })

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.modal-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid var(--glass-border);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: scale(0.95);
}
.modal-enter-to .modal-panel,
.modal-leave-from .modal-panel {
  transform: scale(1);
}
</style>
