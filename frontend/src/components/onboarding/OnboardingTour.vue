<template>
  <Teleport to="body">
    <Transition name="onboarding-tour">
      <aside v-if="open" class="onboarding-tour" role="dialog" aria-modal="false" :aria-label="t('onboarding.tour.title')">
        <header class="onboarding-tour__head">
          <div>
            <p class="onboarding-tour__eyebrow">{{ t('onboarding.badge') }}</p>
            <h2 class="onboarding-tour__title">{{ t('onboarding.tour.title') }}</h2>
          </div>
          <button type="button" class="onboarding-tour__close" :aria-label="t('common.close')" @click="close">
            <i class="fas fa-times" aria-hidden="true" />
          </button>
        </header>

        <p class="onboarding-tour__intro">{{ intro }}</p>

        <div class="onboarding-tour__progress" :aria-label="progressLabel">
          <span
            v-for="(step, i) in steps"
            :key="step.key"
            class="onboarding-tour__pip"
            :class="{ 'is-done': i <= index }"
          />
        </div>

        <div class="onboarding-tour__body">
          <div class="onboarding-tour__icon"><i :class="current.icon" aria-hidden="true" /></div>
          <p class="onboarding-tour__count">{{ progressLabel }}</p>
          <h3 class="onboarding-tour__step-title">{{ t(`onboarding.tour.steps.${current.key}.title`) }}</h3>
          <p class="onboarding-tour__text">{{ t(`onboarding.tour.steps.${current.key}.body`) }}</p>
          <p class="onboarding-tour__look">
            <i class="fas fa-eye" aria-hidden="true" />
            <span>{{ t(`onboarding.tour.steps.${current.key}.look`) }}</span>
          </p>
          <SupportChannelList v-if="current.key === 'support'" class="mt-3" />
        </div>

        <div class="onboarding-tour__nav">
          <button type="button" class="onboarding-tour__btn" :disabled="index === 0" @click="go(index - 1)">
            {{ t('onboarding.tour.prev') }}
          </button>
          <button v-if="!isLast" type="button" class="onboarding-tour__btn onboarding-tour__btn--primary" @click="go(index + 1)">
            {{ t('onboarding.tour.next') }}
          </button>
          <button v-else type="button" class="onboarding-tour__btn onboarding-tour__btn--primary" @click="close">
            {{ t('onboarding.tour.finish') }}
          </button>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SupportChannelList from '@/components/support/SupportChannelList.vue'
import { visibleTourSteps } from '@/config/onboardingTour'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const steps = computed(() => visibleTourSteps(auth))
const index = ref(0)
const current = computed(() => steps.value[index.value] ?? steps.value[0])
const isLast = computed(() => index.value === steps.value.length - 1)
const progressLabel = computed(() =>
  t('onboarding.tour.progress', { current: index.value + 1, total: steps.value.length }),
)
const intro = computed(() => t('onboarding.tour.intro', { count: steps.value.length }))

/* The tour opens on whatever page the person is already looking at rather than
   sending them to step one — a deep link into the panel must survive it. */
watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) return
    const path = router.currentRoute.value.path
    const here = steps.value.findIndex((step) => step.to === path)
    if (here !== -1) index.value = here
  },
  { immediate: true },
)

/* Stepping does open the page the step describes, so the text and the screen
   agree once the person is actually driving the tour. */
function go(next) {
  index.value = Math.min(Math.max(next, 0), steps.value.length - 1)
  const to = current.value?.to
  if (to && router.currentRoute.value.path !== to) router.push(to)
}

function close() {
  emit('close')
}
</script>

<style scoped>
.onboarding-tour {
  position: fixed;
  z-index: 60;
  inset-block-end: 1rem;
  inset-inline-end: 1rem;
  width: min(21rem, calc(100vw - 2rem));
  padding: 1.1rem;
  border-radius: 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  box-shadow: 0 24px 60px rgb(0 0 0 / 28%);
}

.onboarding-tour__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.onboarding-tour__eyebrow {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--primary);
}

.onboarding-tour__title {
  margin-top: 0.15rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.onboarding-tour__close {
  flex-shrink: 0;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 999px;
  color: var(--text-secondary);
  transition: all 0.25s ease;
}

.onboarding-tour__close:hover {
  background: var(--bg-hover);
  color: var(--primary);
}

.onboarding-tour__intro {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.7;
  color: var(--text-secondary);
}

.onboarding-tour__progress {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.9rem;
}

.onboarding-tour__pip {
  height: 3px;
  flex: 1;
  border-radius: 999px;
  background: var(--border-card);
  transition: background 0.3s ease;
}

.onboarding-tour__pip.is-done {
  background: var(--primary);
}

.onboarding-tour__body {
  margin-top: 0.9rem;
}

.onboarding-tour__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.85rem;
  background: var(--primary-muted);
  color: var(--primary);
}

.onboarding-tour__count {
  margin-top: 0.6rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.onboarding-tour__step-title {
  margin-top: 0.2rem;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
}

.onboarding-tour__text {
  margin-top: 0.4rem;
  font-size: 0.78rem;
  line-height: 1.8;
  color: var(--text-secondary);
}

.onboarding-tour__look {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.55rem 0.7rem;
  font-size: 0.73rem;
  line-height: 1.7;
  border-radius: 0.75rem;
  background: var(--primary-muted);
  color: var(--text-primary);
}

.onboarding-tour__look i {
  margin-top: 0.28rem;
  color: var(--primary);
}

.onboarding-tour__nav {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.onboarding-tour__btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.78rem;
  font-weight: 600;
  border-radius: 0.85rem;
  border: 1px solid var(--border-card);
  color: var(--text-primary);
  transition: all 0.25s ease;
}

.onboarding-tour__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.onboarding-tour__btn:not(:disabled):hover {
  border-color: var(--primary);
  color: var(--primary);
}

.onboarding-tour__btn--primary {
  border-color: transparent;
  background: var(--primary);
  color: var(--text-on-primary);
}

/* Out-specifies `.onboarding-tour__btn:not(:disabled):hover`, which would otherwise
   paint this button's label primary-on-primary. */
.onboarding-tour__btn--primary:not(:disabled):hover {
  color: var(--text-on-primary);
  filter: brightness(1.06);
}

.onboarding-tour-enter-active,
.onboarding-tour-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.onboarding-tour-enter-from,
.onboarding-tour-leave-to {
  opacity: 0;
  transform: translateY(0.75rem);
}

/* Clear of the mobile bottom nav. */
@media (max-width: 767px) {
  .onboarding-tour {
    inset-block-end: 4.75rem;
  }
}
</style>
