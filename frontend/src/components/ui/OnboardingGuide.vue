<template>
  <Teleport to="body">
    <Transition name="guide-fade">
      <div
        v-if="visible && positioned"
        class="onboarding-guide"
        role="dialog"
        :aria-label="title"
        aria-modal="true"
      >
        <div class="onboarding-guide__backdrop" />

        <div
          class="onboarding-guide__spotlight"
          :style="spotlightStyle"
          aria-hidden="true"
        />

        <div
          class="onboarding-guide__pulse"
          :style="pulseStyle"
          aria-hidden="true"
        />

        <div class="onboarding-guide__callout" :style="calloutStyle">
          <div class="onboarding-guide__card">
            <div class="onboarding-guide__badge">
              <i class="fas fa-lightbulb" aria-hidden="true" />
            </div>
            <div class="onboarding-guide__text">
              <h3 class="onboarding-guide__title">{{ title }}</h3>
              <p class="onboarding-guide__message">{{ message }}</p>
            </div>
            <button type="button" class="onboarding-guide__btn" @click="dismiss">
              {{ dismissLabel }}
            </button>
          </div>

          <div class="onboarding-guide__arrow" aria-hidden="true">
            <svg width="28" height="36" viewBox="0 0 28 36" fill="none">
              <path
                d="M14 34L14 8M14 8L6 16M14 8L22 16"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  target: { type: Object, default: null },
  title: { type: String, required: true },
  message: { type: String, required: true },
  dismissLabel: { type: String, default: 'Got it' },
  placement: { type: String, default: 'top' },
})

const emit = defineEmits(['dismiss'])

const rect = ref(null)
const positioned = ref(false)

const spotlightStyle = computed(() => {
  if (!rect.value) return null
  const pad = 6
  return {
    top: `${rect.value.top - pad}px`,
    left: `${rect.value.left - pad}px`,
    width: `${rect.value.width + pad * 2}px`,
    height: `${rect.value.height + pad * 2}px`,
  }
})

const pulseStyle = computed(() => spotlightStyle.value)

const calloutStyle = computed(() => {
  if (!rect.value) return null
  const gap = 18
  const calloutWidth = 300
  const viewportW = window.innerWidth
  const centerX = rect.value.left + rect.value.width / 2
  let left = centerX - calloutWidth / 2
  const padding = 16
  if (left < padding) left = padding
  if (left + calloutWidth > viewportW - padding) left = viewportW - padding - calloutWidth

  const top = props.placement === 'bottom'
    ? rect.value.bottom + gap + 36
    : rect.value.top - gap

  return {
    top: `${top}px`,
    left: `${left}px`,
    width: `${calloutWidth}px`,
    transform: props.placement === 'top' ? 'translateY(-100%)' : 'none',
  }
})

function updatePosition() {
  const el = props.target?.$el ?? props.target
  if (!el || typeof el.getBoundingClientRect !== 'function') {
    positioned.value = false
    rect.value = null
    return
  }
  rect.value = el.getBoundingClientRect()
  positioned.value = true
}

function dismiss() {
  emit('dismiss')
}

function onViewportChange() {
  if (!props.visible) return
  updatePosition()
}

watch(
  () => [props.visible, props.target],
  async ([visible]) => {
    if (!visible) {
      positioned.value = false
      rect.value = null
      return
    }
    await nextTick()
    updatePosition()
  },
  { immediate: true },
)

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      window.addEventListener('resize', onViewportChange)
      window.addEventListener('scroll', onViewportChange, true)
    } else {
      window.removeEventListener('resize', onViewportChange)
      window.removeEventListener('scroll', onViewportChange, true)
    }
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, true)
})
</script>

<style scoped>
.onboarding-guide {
  position: fixed;
  inset: 0;
  z-index: 200;
  pointer-events: none;
}

.onboarding-guide__backdrop {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.onboarding-guide__spotlight {
  position: fixed;
  border-radius: 14px;
  pointer-events: none;
  box-shadow: 0 0 0 9999px rgba(2, 6, 23, 0.55);
  border: 2px solid color-mix(in srgb, var(--primary) 80%, white);
  transition: top 0.25s ease, left 0.25s ease, width 0.25s ease, height 0.25s ease;
}

.onboarding-guide__pulse {
  position: fixed;
  border-radius: 14px;
  pointer-events: none;
  border: 2px solid var(--primary);
  animation: guide-pulse 2s ease-in-out infinite;
}

.onboarding-guide__callout {
  position: fixed;
  z-index: 1;
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: guide-callout-in 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.onboarding-guide__card {
  width: 100%;
  padding: 1.1rem 1.15rem;
  border-radius: 1rem;
  border: 1px solid color-mix(in srgb, var(--primary) 45%, transparent);
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--bg-card) 92%, var(--primary)) 0%,
    var(--bg-card) 100%
  );
  box-shadow:
    0 20px 50px rgba(0, 0, 0, 0.35),
    0 0 0 1px color-mix(in srgb, var(--primary) 20%, transparent),
    0 0 30px color-mix(in srgb, var(--primary) 15%, transparent);
}

.onboarding-guide__badge {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.65rem;
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--primary) 35%, transparent);
}

.onboarding-guide__title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.35rem;
}

.onboarding-guide__message {
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--text-secondary);
  margin: 0 0 0.85rem;
}

.onboarding-guide__btn {
  width: 100%;
  padding: 0.55rem 0.85rem;
  border-radius: 0.75rem;
  font-size: 0.82rem;
  font-weight: 600;
  border: 1px solid color-mix(in srgb, var(--primary) 50%, transparent);
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 10%, transparent);
  transition: background 0.2s ease, transform 0.2s ease;
}

.onboarding-guide__btn:hover {
  background: color-mix(in srgb, var(--primary) 20%, transparent);
  transform: translateY(-1px);
}

.onboarding-guide__arrow {
  color: var(--primary);
  margin-top: -2px;
  animation: guide-arrow-bounce 1.4s ease-in-out infinite;
  filter: drop-shadow(0 2px 6px color-mix(in srgb, var(--primary) 40%, transparent));
}

.guide-fade-enter-active,
.guide-fade-leave-active {
  transition: opacity 0.3s ease;
}

.guide-fade-enter-from,
.guide-fade-leave-to {
  opacity: 0;
}

@keyframes guide-pulse {
  0%, 100% {
    opacity: 0.35;
    transform: scale(1);
  }
  50% {
    opacity: 0.9;
    transform: scale(1.04);
  }
}

@keyframes guide-arrow-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(6px);
  }
}

@keyframes guide-callout-in {
  from {
    opacity: 0;
    transform: translateY(calc(-100% - 8px)) scale(0.94);
  }
  to {
    opacity: 1;
    transform: translateY(-100%) scale(1);
  }
}
</style>
