import { defineStore } from 'pinia'

const STORAGE_KEY = 'mrexchange-sidebar-collapsed'

function stored() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

/**
 * Whether the panel's navigation rail is collapsed to icons.
 *
 * One piece of state, in the store: the rail and the page padding beside it
 * have to agree, and the preference has to survive a reload — a person who
 * collapsed the rail did not mean "until the next page load".
 *
 * `forced` is separate from the preference on purpose. A page that needs the
 * whole width (the website builder, previewing a customer's site) collapses the
 * rail while it is open and gives the person their own setting back on the way
 * out, instead of quietly rewriting it.
 */
export const useSidebarStore = defineStore('sidebar', {
  state: () => ({
    preference: stored(),
    forced: false,
  }),

  getters: {
    isCollapsed: (state) => state.forced || state.preference,
  },

  actions: {
    toggle() {
      this.setCollapsed(!this.isCollapsed)
    },

    setCollapsed(collapsed) {
      // Toggling by hand while a page is forcing the rail shut is an explicit
      // choice, so it releases the force rather than fighting it.
      this.forced = false
      this.preference = collapsed
      try {
        localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
      } catch {
        /* Private mode: the rail still works, it just forgets. */
      }
    },

    /** Collapse for as long as a full-width page is open. */
    force(collapsed) {
      this.forced = collapsed
    },
  },
})
