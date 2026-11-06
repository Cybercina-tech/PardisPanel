/**
 * Sidebar / drawer / bottom-nav entries.
 *
 * Order follows the day's workflow rather than the order features were built:
 * price the desk, publish it, then read what came back. `group` marks where one
 * phase ends so the rail can draw a rule; it never affects routing.
 */
export const staffNavLinks = [
  { to: '/panel', labelKey: 'sidebar.dashboard', icon: 'fas fa-tachometer-alt', exact: true, activeColor: 'gold', group: 'work' },
  { to: '/update', labelKey: 'sidebar.priceHub', icon: 'fas fa-dollar-sign', exact: false, activeColor: 'buy', group: 'work' },
  { to: '/finalize', labelKey: 'sidebar.finalize', icon: 'fas fa-check-circle', exact: false, permission: 'finalize', activeColor: 'buy', group: 'work' },
  { to: '/telegram/send', labelKey: 'sidebar.telegram', icon: 'fab fa-telegram', exact: false, activeColor: 'info', group: 'publish' },
  { to: '/templates', labelKey: 'sidebar.templates', icon: 'fas fa-file-image', exact: false, activeColor: 'template', group: 'publish' },
  { to: '/analysis', labelKey: 'sidebar.analysis', icon: 'fas fa-chart-line', exact: false, permission: 'analysis', activeColor: 'info', group: 'insight' },
  { to: '/users', labelKey: 'sidebar.adminManagement', icon: 'fas fa-user-shield', exact: false, permission: 'adminManagement', activeColor: 'gold', group: 'admin' },
  { to: '/settings', labelKey: 'sidebar.settings', icon: 'fas fa-cog', exact: false, permission: 'settings', activeColor: 'gold', group: 'admin' },
]

export function navLinkIsActive(route, link) {
  if (link.exact) return route.path === link.to
  if (link.to === '/update') {
    return route.path === '/update' ||
      (route.path.startsWith('/prices/category/') && route.path.endsWith('/update')) ||
      (route.path.startsWith('/prices/special/') && route.path.endsWith('/update'))
  }
  if (link.to === '/settings') {
    return route.path.startsWith('/settings') || route.path.startsWith('/categories')
  }
  return route.path.startsWith(link.to)
}

export function visibleNavLinks(auth) {
  return staffNavLinks.filter((link) => {
    if (!link.permission) return true
    return auth.can(link.permission)
  })
}

/**
 * True when a rule belongs above this link — i.e. it opens a phase and is not
 * the first entry left after permission filtering.
 */
export function startsNavGroup(links, index) {
  if (index === 0) return false
  return links[index].group !== links[index - 1].group
}
