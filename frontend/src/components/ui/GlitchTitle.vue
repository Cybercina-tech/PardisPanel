<template>
  <h1
    class="vapor-about__title"
    :style="{ transform: `translateX(${shake}px)` }"
    :data-text="text"
  >
    <span class="vapor-about__title-base">{{ text }}</span>
    <span
      class="vapor-about__title-channel vapor-about__title-channel--magenta"
      aria-hidden="true"
      :style="{
        clipPath: magenta.clip,
        transform: `translateX(${magenta.x}px)`,
        opacity: magenta.opacity,
      }"
    >
      {{ text }}
    </span>
    <span
      class="vapor-about__title-channel vapor-about__title-channel--cyan"
      aria-hidden="true"
      :style="{
        clipPath: cyan.clip,
        transform: `translateX(${cyan.x}px)`,
        opacity: cyan.opacity,
      }"
    >
      {{ text }}
    </span>
  </h1>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

defineProps({
  text: {
    type: String,
    required: true,
  },
})

const IDLE = { clip: 'inset(0 0 0 0)', x: 0, opacity: 0 }

const magenta = ref({ ...IDLE })
const cyan = ref({ ...IDLE })
const shake = ref(0)

let cancelled = false
let timeoutId = 0

function randSlice(channel) {
  const top = Math.floor(Math.random() * 70)
  const height = 8 + Math.floor(Math.random() * 28)
  const bottom = Math.max(0, 100 - top - height)
  const x =
    channel === 'magenta'
      ? -(2 + Math.floor(Math.random() * 8))
      : 2 + Math.floor(Math.random() * 8)
  return {
    clip: `inset(${top}% 0 ${bottom}% 0)`,
    x,
    opacity: 0.55 + Math.random() * 0.4,
  }
}

function tick() {
  if (cancelled) return

  const burst = Math.random() < 0.35
  if (burst) {
    magenta.value = randSlice('magenta')
    cyan.value = randSlice('cyan')
    shake.value = (Math.random() - 0.5) * 3
    timeoutId = window.setTimeout(() => {
      if (cancelled) return
      magenta.value = { ...IDLE }
      cyan.value = { ...IDLE }
      shake.value = 0
      timeoutId = window.setTimeout(tick, 1800 + Math.random() * 2800)
    }, 120 + Math.random() * 220)
  } else {
    magenta.value = {
      clip: 'inset(0 0 0 0)',
      x: -(1 + Math.random() * 2),
      opacity: 0.2 + Math.random() * 0.15,
    }
    cyan.value = {
      clip: 'inset(0 0 0 0)',
      x: 1 + Math.random() * 2,
      opacity: 0.2 + Math.random() * 0.15,
    }
    shake.value = 0
    timeoutId = window.setTimeout(() => {
      if (cancelled) return
      magenta.value = { ...IDLE }
      cyan.value = { ...IDLE }
      timeoutId = window.setTimeout(tick, 2200 + Math.random() * 3200)
    }, 400 + Math.random() * 500)
  }
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return
  }
  timeoutId = window.setTimeout(tick, 900)
})

onUnmounted(() => {
  cancelled = true
  window.clearTimeout(timeoutId)
})
</script>
