import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

/**
 * Position a teleported panel against a trigger element.
 *
 * Dropdowns used to be absolutely positioned next to their trigger, which put
 * them inside whatever card, modal or `overflow-hidden` wrapper the form lived
 * in — so they were clipped by the card, stacked under the next field, or
 * scrolled away from their input. The panel instead renders at the end of
 * `<body>` on the popover layer and is placed here in viewport coordinates,
 * flipping above the trigger and shrinking to fit when the space below runs
 * out.
 *
 * Returns the refs a component binds to its trigger and panel plus the `open`
 * state; the caller owns selection and keyboard behaviour.
 */
export function useAnchoredPanel({
  /** Never render the panel narrower than this, however small the trigger is. */
  minWidth = 200,
  /** Panels stop growing here so a long list scrolls instead of filling the page. */
  maxHeight = 360,
  /** A panel with less room than this below the trigger flips above it. */
  minSpace = 220,
  gap = 8,
  viewportPadding = 12,
} = {}) {
  const triggerRef = ref(null)
  const panelRef = ref(null)
  const open = ref(false)
  const panelStyle = ref({})
  const placement = ref('bottom')

  function updatePosition() {
    const trigger = triggerRef.value
    if (!trigger) return
    const rect = trigger.getBoundingClientRect()
    const viewportW = window.innerWidth
    const viewportH = window.innerHeight

    const available = viewportW - viewportPadding * 2
    const width = Math.min(Math.max(rect.width, Math.min(minWidth, available)), available)

    let left = rect.left
    // RTL panels are anchored to the trigger's end edge, which is its left in
    // LTR and its right in RTL; clamping both edges covers either direction.
    if (left + width > viewportW - viewportPadding) left = viewportW - viewportPadding - width
    if (left < viewportPadding) left = viewportPadding

    const spaceBelow = viewportH - rect.bottom - viewportPadding
    const spaceAbove = rect.top - viewportPadding
    const flip = spaceBelow < minSpace && spaceAbove > spaceBelow
    placement.value = flip ? 'top' : 'bottom'

    const room = Math.max(140, (flip ? spaceAbove : spaceBelow) - gap)

    panelStyle.value = {
      width: `${width}px`,
      left: `${left}px`,
      top: flip ? `${rect.top - gap}px` : `${rect.bottom + gap}px`,
      transform: flip ? 'translateY(-100%)' : 'none',
      // Capped on the panel, not on the list inside it: a search box or a
      // heading above the list counts towards the height that has to fit.
      maxHeight: `${Math.min(maxHeight, room)}px`,
    }
  }

  function show() {
    open.value = true
    nextTick(updatePosition)
  }

  function close() {
    open.value = false
  }

  function toggle() {
    open.value ? close() : show()
  }

  function onDocumentPointerDown(event) {
    if (!open.value) return
    if (triggerRef.value?.contains(event.target)) return
    if (panelRef.value?.contains(event.target)) return
    close()
  }

  function onViewportChange() {
    if (open.value) updatePosition()
  }

  onMounted(() => {
    document.addEventListener('pointerdown', onDocumentPointerDown, true)
    window.addEventListener('resize', onViewportChange)
    // Capture phase: the scroller is usually an ancestor panel, not the window.
    window.addEventListener('scroll', onViewportChange, true)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onDocumentPointerDown, true)
    window.removeEventListener('resize', onViewportChange)
    window.removeEventListener('scroll', onViewportChange, true)
  })

  watch(open, (isOpen) => {
    if (isOpen) nextTick(updatePosition)
  })

  return { triggerRef, panelRef, open, panelStyle, placement, show, close, toggle, updatePosition }
}
