/**
 * Guided tour shown on a new customer's first sign-in.
 *
 * One step per thing the panel actually does, in the order a rate desk uses it:
 * quote → publish → brand → measure → ask for help. `to` is the panel route the
 * step opens; copy resolves to `onboarding.tour.steps.<key>.title` / `.body` /
 * `.look`.
 *
 * `permission` hides a step the signed-in role cannot open (see config/permissions).
 * The final `support` step has no route: it renders the live support channels
 * so the answer to "who do I ask?" is never a dead phone number in a template.
 */
export const ONBOARDING_TOUR_STEPS = [
  { key: 'dashboard', to: '/panel', icon: 'fas fa-tachometer-alt' },
  { key: 'prices', to: '/update', icon: 'fas fa-dollar-sign' },
  { key: 'finalize', to: '/finalize', icon: 'fas fa-check-circle', permission: 'finalize' },
  { key: 'categories', to: '/categories', icon: 'fas fa-tags' },
  { key: 'templates', to: '/templates', icon: 'fas fa-file-image' },
  { key: 'telegram', to: '/telegram/send', icon: 'fab fa-telegram' },
  { key: 'analytics', to: '/analysis', icon: 'fas fa-chart-line', permission: 'analysis' },
  { key: 'support', to: '', icon: 'fas fa-headset' },
]

export function visibleTourSteps(auth) {
  return ONBOARDING_TOUR_STEPS.filter((step) => !step.permission || auth.can(step.permission))
}
