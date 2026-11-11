/**
 * Central permission config — single source of truth for roles and access.
 *
 * MUST stay in sync with backend/accounts/permissions.py. This file only decides what the
 * UI *shows*; the API is the real gate. When the two disagree the user gets a nav item
 * that 403s on click, which is exactly what used to happen here:
 *   - `settings` was ALL_PANEL_ROLES, but SiteSettings/bots/channels/logs are IsSuperAdmin.
 *   - `adminManagement` allowed `management`, but User Management is IsSuperAdmin.
 * Both were narrowed to match. `settings` has since been widened again to
 * super_admin + management — a self-serve signup owns its workspace with
 * role=management and has to be able to configure branding, uploads, fonts and
 * the webhook — and the backend was widened with it (SiteSettings and the
 * upload policy now accept IsSuperAdminOrManagement). `settingsAdmin`, which
 * gates the panel-log tab inside the page, was widened with it once more: `Log`
 * is account-scoped, so a desk owner reading it sees only its own rows.
 */

export const ROLES = {
  SUPER_ADMIN: 'super_admin',
  MANAGEMENT: 'management',
  DEVELOPER: 'developer',
  EMPLOYEE: 'employee',
}

/** All roles that can use the panel. */
export const ALL_PANEL_ROLES = Object.values(ROLES)

/** Backend: IsSuperAdminOrManagement — finalize, price writes, template editor. */
/** Employees have exactly management's access. */
const SUPER_ADMIN_OR_MANAGEMENT = [ROLES.SUPER_ADMIN, ROLES.MANAGEMENT, ROLES.EMPLOYEE]

/**
 * Which roles can access each feature. Mirrors backend/accounts/permissions.py.
 *
 * NOTE on ROLES.DEVELOPER: it is a valid choice on CustomUser.ROLE_CHOICES but no
 * backend permission class accepts it — not IsSuperAdmin, not IsSuperAdminOrManagement,
 * not IsSuperAdminOrManagementOrEmployee. A developer therefore only reaches the plain
 * IsAuthenticated endpoints (analysis, finalize dashboard read, price hub read). It is
 * listed here only where that is actually true, instead of being shown a panel that 403s.
 */
export const PERMISSIONS = {
  /** تحلیل و نمودارها — IsAuthenticated (همه) */
  analysis: ALL_PANEL_ROLES,
  /** نهایی‌سازی و انتشار به تلگرام — IsSuperAdminOrManagement */
  finalize: SUPER_ADMIN_OR_MANAGEMENT,
  /** تنظیمات پنل (برندینگ، آپلود، فونت، وبهوک) — IsSuperAdminOrManagement */
  settings: SUPER_ADMIN_OR_MANAGEMENT,
  /** لاگ‌های پنل — IsSuperAdminOrManagement (لاگ به حساب کاربر محدود است) */
  settingsAdmin: SUPER_ADMIN_OR_MANAGEMENT,
  /** صفحهٔ تلگرام — IsAuthenticated (همه؛ داده به حساب خود کاربر محدود است) */
  telegram: ALL_PANEL_ROLES,
  /** حذف آیتم‌ها (دسته‌بندی، قالب و غیره) — IsSuperAdminOrManagement */
  deleteItems: SUPER_ADMIN_OR_MANAGEMENT,
  /** مدیریت ادمین‌ها — CanManageTeam (مدیریت فقط اپراتورهای خودش را می‌بیند) */
  adminManagement: SUPER_ADMIN_OR_MANAGEMENT,
}

function normalizeRole(role) {
  const key = String(role ?? '').trim().toLowerCase().replaceAll('-', '_')
  if (key === 'superadmin') return ROLES.SUPER_ADMIN
  return key
}

/**
 * @param {string|null} role
 * @param {string} permission - key of PERMISSIONS
 * @returns {boolean}
 */
export function can(role, permission) {
  const normalizedRole = normalizeRole(role)
  if (!normalizedRole) return false
  const allowed = PERMISSIONS[permission]
  return Array.isArray(allowed) && allowed.includes(normalizedRole)
}

export default { ROLES, PERMISSIONS, ALL_PANEL_ROLES, can }
