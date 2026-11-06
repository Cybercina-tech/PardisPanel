<template>
  <div>
    <h1 class="text-2xl font-bold text-gold mb-6">{{ t('userCenter.title') }}</h1>

    <div class="flex gap-2 mb-6 border-b" style="border-color: var(--border-card);">
      <button
        type="button"
        class="px-4 py-3 font-medium rounded-t-xl transition-colors -mb-px"
        :class="activeTab === 'users' ? 'text-gold border-b-2 border-gold bg-[var(--bg-hover)]' : 'text-[var(--text-secondary)] hover:text-[var(--primary)]'"
        @click="activeTab = 'users'"
      >
        <i class="fas fa-users me-2"></i>{{ t('userCenter.users') }}
      </button>
      <button
        type="button"
        class="px-4 py-3 font-medium rounded-t-xl transition-colors -mb-px"
        :class="activeTab === 'activity' ? 'text-gold border-b-2 border-gold bg-[var(--bg-hover)]' : 'text-[var(--text-secondary)] hover:text-[var(--primary)]'"
        @click="activeTab = 'activity'"
      >
        <i class="fas fa-history me-2"></i>{{ t('userCenter.activity') }}
      </button>
    </div>

    <!-- Users tab -->
    <div v-show="activeTab === 'users'">
      <div class="flex justify-between items-center mb-4">
        <p class="text-[var(--text-secondary)]">{{ t('userCenter.manageUsers') }}</p>
        <button type="button" class="btn-luxury" @click="openUserModal()">
          <i class="fas fa-user-plus me-2"></i>{{ t('userCenter.addUser') }}
        </button>
      </div>
      <div v-if="usersLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <BaseSkeleton v-for="i in 6" :key="i" variant="card" class="!h-28" />
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <BaseCard
          v-for="u in users"
          :key="u.id"
          variant="glass"
          padding="sm"
          class="border border-[var(--glass-border)] hover-lift"
        >
          <div class="flex items-center gap-4">
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold shrink-0"
              :class="roleBadgeClass(u.role)"
            >
              {{ (u.full_name || u.username || '?').charAt(0).toUpperCase() }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="font-semibold text-[var(--text-primary)] truncate">{{ u.full_name || u.username }}</p>
              <p class="text-sm text-[var(--text-secondary)] truncate">@{{ u.username }}</p>
              <span
                class="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium"
                :class="roleBadgeClass(u.role)"
              >
                {{ roleLabel(u.role) }}
              </span>
              <span
                v-if="isDelegated(u.sub_role)"
                class="inline-block mt-1 ml-1 px-2 py-0.5 rounded text-xs font-medium bg-sky-500/20 text-sky-400"
              >
                {{ t(`programmerHub.${u.sub_role}`) }}
              </span>
              <span
                v-if="!u.is_active"
                class="inline-block ml-1 px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400"
              >
                {{ t('userCenter.inactive') }}
              </span>
              <p v-if="u.telegram_username" class="text-xs text-[var(--text-secondary)] truncate mt-1" dir="ltr">
                <i class="fab fa-telegram-plane me-1"></i>@{{ u.telegram_username }}
              </p>
            </div>
            <div class="flex flex-col gap-2 shrink-0">
              <button
                type="button"
                class="btn-luxury-outline text-sm py-1.5"
                @click="openUserModal(u)"
              >
                <i class="fas fa-edit"></i>
              </button>
              <button
                v-if="isSuperAdmin && u.role !== 'super_admin'"
                type="button"
                class="btn-luxury-outline text-sm py-1.5 !border-amber-500/50 !text-amber-400 hover:!bg-amber-500/10"
                :title="t('userCenter.makeAdmin')"
                :aria-label="t('userCenter.makeAdmin')"
                :disabled="promotingId === u.id"
                @click="makeAdmin(u)"
              >
                <LoadingSpinner v-if="promotingId === u.id" class="w-4 h-4" />
                <i v-else class="fas fa-user-shield"></i>
              </button>
              <button
                type="button"
                class="btn-luxury-outline text-sm py-1.5 !border-rose-500/50 !text-rose-400 hover:!bg-rose-500/10"
                :title="t('userCenter.forceLogout')"
                @click="forceLogout(u)"
              >
                <i class="fas fa-sign-out-alt"></i>
              </button>
            </div>
          </div>
        </BaseCard>
      </div>
      <p v-if="!usersLoading && !users.length" class="text-center text-[var(--text-secondary)] py-8">
        {{ t('userCenter.noUsers') }}
      </p>
    </div>

    <!-- Activity tab -->
    <div v-show="activeTab === 'activity'">
      <div class="mb-4 flex flex-wrap gap-3 items-center">
        <select
          v-model="activityFilters.action_type"
          class="input-luxury py-2 w-40 text-sm"
        >
          <option value="">{{ t('userCenter.allActions') }}</option>
          <option value="login_success">{{ actionTypeLabel('login_success') }}</option>
          <option value="login_failed">{{ actionTypeLabel('login_failed') }}</option>
          <option value="logout">{{ actionTypeLabel('logout') }}</option>
          <option value="price_update">{{ actionTypeLabel('price_update') }}</option>
          <option value="bulk_price_update">{{ actionTypeLabel('bulk_price_update') }}</option>
          <option value="special_price_update">{{ actionTypeLabel('special_price_update') }}</option>
        </select>
        <button type="button" class="btn-luxury-outline text-sm" @click="fetchActivity">
          <i class="fas fa-sync-alt me-1"></i>{{ $t('common.search') }}
        </button>
      </div>
      <div v-if="activityLoading" class="card-luxury p-6">
        <BaseSkeleton v-for="i in 8" :key="i" variant="table-row" />
      </div>
      <div v-else class="card-luxury border border-[var(--glass-border)] w-full min-w-0 overflow-hidden">
        <!-- Desktop/tablet: table in scrollable wrapper -->
        <div class="w-full overflow-x-auto max-w-full hidden md:block">
          <table class="w-full min-w-[600px]">
            <thead>
              <tr class="border-b border-[var(--border-color)]">
                <th class="text-start py-4 px-4 text-gold font-semibold">{{ t('userCenter.actionType') }}</th>
                <th class="text-start py-4 px-4 text-gold font-semibold">{{ t('userCenter.user') }}</th>
                <th class="text-start py-4 px-4 text-gold font-semibold">{{ t('userCenter.details') }}</th>
                <th class="text-start py-4 px-4 text-gold font-semibold">{{ t('userCenter.ip') }}</th>
                <th class="text-start py-4 px-4 text-gold font-semibold">{{ $t('logs.date') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="log in activity"
                :key="log.id"
                class="border-b border-[var(--border-card)] hover:bg-[var(--bg-hover)] transition-colors"
              >
                <td class="py-3 px-4">
                  <span
                    class="px-2 py-1 rounded text-xs font-medium inline-flex items-center gap-1"
                    :class="actionClass(log.action_type)"
                  >
                    <i :class="actionIcon(log.action_type)" class="text-xs"></i>
                    {{ actionTypeLabel(log.action_type) }}
                  </span>
                </td>
                <td class="py-3 px-4 text-[var(--text-secondary)]">{{ log.user_display || '—' }}</td>
                <td class="py-3 px-4 text-sm max-w-xs truncate break-words min-w-0" :title="log.details">{{ log.details || '—' }}</td>
                <td class="py-3 px-4 text-[var(--text-secondary)] text-sm">{{ log.ip_address || '—' }}</td>
                <td class="py-3 px-4 text-[var(--text-secondary)] text-sm">{{ formatDate(log.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Mobile: stacked cards -->
        <div class="block md:hidden divide-y divide-[var(--border-card)]">
          <div
            v-for="log in activity"
            :key="log.id"
            class="p-4 space-y-2"
          >
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <span
                class="px-2 py-1 rounded text-xs font-medium inline-flex items-center gap-1 shrink-0"
                :class="actionClass(log.action_type)"
              >
                <i :class="actionIcon(log.action_type)" class="text-xs"></i>
                {{ actionTypeLabel(log.action_type) }}
              </span>
              <span class="text-xs text-[var(--text-secondary)]">{{ formatDate(log.created_at) }}</span>
            </div>
            <p class="text-sm text-[var(--text-secondary)]">{{ t('userCenter.user') }}: {{ log.user_display || '—' }}</p>
            <p class="text-sm text-[var(--text-primary)] break-words" :title="log.details">{{ log.details || '—' }}</p>
            <p class="text-xs text-[var(--text-secondary)]">{{ t('userCenter.ip') }}: {{ log.ip_address || '—' }}</p>
          </div>
        </div>
        <p v-if="!activity.length" class="text-center text-[var(--text-secondary)] py-8">{{ t('userCenter.noActivity') }}</p>
      </div>
    </div>

    <!-- User create/edit modal -->
    <BaseModal
      v-model="userModalOpen"
      :title="editingUser ? t('userCenter.editUser') : t('userCenter.addUser')"
    >
      <form @submit.prevent="saveUser" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('auth.username') }}</label>
          <input
            v-model="userForm.username"
            type="text"
            class="input-luxury w-full"
            :disabled="!!editingUser"
            required
          />
        </div>
        <div v-if="!editingUser">
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('auth.password') }}</label>
          <input
            v-model="userForm.password"
            type="password"
            class="input-luxury w-full"
            :required="!editingUser"
            minlength="8"
          />
        </div>
        <div v-if="editingUser">
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('userCenter.newPasswordOptional') }}</label>
          <input
            v-model="userForm.password"
            type="password"
            class="input-luxury w-full"
            minlength="8"
            :placeholder="t('userCenter.leaveBlankToKeepCurrent')"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('userCenter.fullName') }}</label>
          <input v-model="userForm.full_name" type="text" class="input-luxury w-full" />
        </div>
        <div v-if="isSuperAdmin">
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('userCenter.role') }}</label>
          <select v-model="userForm.role" class="input-luxury w-full" required>
            <option value="super_admin">{{ roleLabel('super_admin') }}</option>
            <option value="management">{{ roleLabel('management') }}</option>
            <option value="developer">{{ roleLabel('developer') }}</option>
            <option value="employee">{{ roleLabel('employee') }}</option>
          </select>
        </div>
        <div v-if="showPosition">
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('programmerHub.subRole') }}</label>
          <select v-model="userForm.sub_role" class="input-luxury w-full" required>
            <option v-for="r in subRoleOptions" :key="r" :value="r">{{ t(`programmerHub.${r}`) }}</option>
          </select>
        </div>
        <div v-if="isSuperAdmin && showPosition && isDelegated(userForm.sub_role)">
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('programmerHub.ownerUsername') }}</label>
          <input
            v-model="userForm.owner_username"
            type="text"
            class="input-luxury w-full"
            dir="ltr"
            :required="!editingUser?.owner"
            :placeholder="editingUser?.owner_username || ''"
          />
          <p class="text-xs text-[var(--text-secondary)] mt-1">{{ t('programmerHub.ownerUsernameHint') }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('programmerHub.telegramUsername') }}</label>
          <input v-model="userForm.telegram_username" type="text" class="input-luxury w-full" dir="ltr" placeholder="@username" />
        </div>
        <div>
          <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ t('programmerHub.telegramId') }}</label>
          <input v-model="userForm.telegram_id" type="text" inputmode="numeric" pattern="[0-9]*" class="input-luxury w-full" dir="ltr" />
        </div>
        <div v-if="editingUser" class="flex items-center gap-2">
          <BaseCheckbox id="user-active" v-model="userForm.is_active">{{ t('userCenter.active') }}</BaseCheckbox>
        </div>
        <div class="flex gap-3 justify-end pt-4">
          <button type="button" class="btn-luxury-outline" @click="userModalOpen = false">
            {{ $t('common.cancel') }}
          </button>
          <button type="submit" class="btn-luxury" :disabled="saveUserLoading">
            <LoadingSpinner v-if="saveUserLoading" class="w-5 h-5" />
            <span v-else>{{ $t('common.save') }}</span>
          </button>
        </div>
      </form>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { authApi, getApiErrorDetails } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseCheckbox from '@/components/ui/BaseCheckbox.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import { useDate } from '@/composables/useDate'

const { formatDateTime: formatDate } = useDate()

const toast = useToast()
const { t } = useI18n()
const activeTab = ref('users')
const users = ref([])
const usersLoading = ref(true)
const activity = ref([])
const activityLoading = ref(false)
const userModalOpen = ref(false)
const editingUser = ref(null)
const saveUserLoading = ref(false)

const auth = useAuthStore()
// Owners (management) only manage their own bot operators; the server fixes
// role and owner for them, so the form hides what they cannot choose.
const isSuperAdmin = computed(() => auth.role === 'super_admin')
const DELEGATED_SUB_ROLES = ['operator', 'head_operator']
const subRoleOptions = computed(() =>
  isSuperAdmin.value ? ['admin', ...DELEGATED_SUB_ROLES] : DELEGATED_SUB_ROLES
)

const userForm = reactive({
  username: '',
  password: '',
  full_name: '',
  role: 'employee',
  is_active: true,
  sub_role: 'operator',
  telegram_username: '',
  telegram_id: '',
  owner_username: '',
})

const showPosition = computed(() => !isSuperAdmin.value || userForm.role === 'employee')

function isDelegated(subRole) {
  return DELEGATED_SUB_ROLES.includes(subRole)
}

const activityFilters = reactive({
  action_type: '',
})

function roleLabel(role) {
  const map = {
    super_admin: t('userCenter.roles.super_admin'),
    management: t('userCenter.roles.management'),
    developer: t('userCenter.roles.developer'),
    employee: t('userCenter.roles.employee'),
  }
  return map[role] ?? role
}

function actionTypeLabel(actionType) {
  const map = {
    login_success: t('userCenter.actionTypes.login_success'),
    login_failed: t('userCenter.actionTypes.login_failed'),
    logout: t('userCenter.actionTypes.logout'),
    price_update: t('userCenter.actionTypes.price_update'),
    bulk_price_update: t('userCenter.actionTypes.bulk_price_update'),
    special_price_update: t('userCenter.actionTypes.special_price_update'),
  }
  return map[actionType] ?? actionType
}

function roleBadgeClass(role) {
  const map = {
    super_admin: 'bg-amber-500/20 text-amber-400',
    management: 'bg-emerald-500/20 text-emerald-400',
    developer: 'bg-blue-500/20 text-blue-400',
    employee: 'bg-[var(--primary)]/20 text-gold',
  }
  return map[role] ?? 'bg-gray-500/20 text-gray-400'
}

function actionClass(actionType) {
  const map = {
    login_success: 'bg-emerald-500/20 text-emerald-400',
    login_failed: 'bg-rose-500/20 text-rose-400',
    logout: 'bg-gray-500/20 text-gray-400',
    price_update: 'bg-amber-500/20 text-amber-400',
    bulk_price_update: 'bg-amber-500/20 text-amber-400',
    special_price_update: 'bg-amber-500/20 text-amber-400',
  }
  return map[actionType] ?? 'bg-gray-500/20'
}

function actionIcon(actionType) {
  const map = {
    login_success: 'fas fa-sign-in-alt',
    login_failed: 'fas fa-times-circle',
    logout: 'fas fa-sign-out-alt',
    price_update: 'fas fa-dollar-sign',
    bulk_price_update: 'fas fa-sync-alt',
    special_price_update: 'fas fa-star',
  }
  return map[actionType] ?? 'fas fa-circle'
}


async function fetchUsers() {
  usersLoading.value = true
  try {
    const { data } = await authApi.users.list()
    users.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    users.value = []
  } finally {
    usersLoading.value = false
  }
}

async function fetchActivity() {
  activityLoading.value = true
  try {
    const params = {}
    if (activityFilters.action_type) params.action_type = activityFilters.action_type
    const { data } = await authApi.activity(params)
    activity.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    activity.value = []
  } finally {
    activityLoading.value = false
  }
}

function openUserModal(user = null) {
  editingUser.value = user
  userForm.username = user?.username ?? ''
  userForm.password = ''
  userForm.full_name = user?.full_name ?? ''
  userForm.role = user?.role ?? 'employee'
  userForm.is_active = user?.is_active ?? true
  userForm.sub_role = user?.sub_role ?? subRoleOptions.value[0]
  userForm.telegram_username = user?.telegram_username ?? ''
  userForm.telegram_id = user?.telegram_id ?? ''
  userForm.owner_username = ''
  userModalOpen.value = true
}

function teamFields() {
  const fields = {
    full_name: userForm.full_name,
    sub_role: showPosition.value ? userForm.sub_role : 'admin',
    telegram_username: userForm.telegram_username.trim().replace(/^@/, ''),
    telegram_id: userForm.telegram_id.trim(),
  }
  if (isSuperAdmin.value) {
    fields.role = userForm.role
    if (userForm.owner_username.trim()) fields.owner_username = userForm.owner_username.trim()
  }
  return fields
}

async function saveUser() {
  saveUserLoading.value = true
  try {
    if (editingUser.value) {
      const payload = { ...teamFields(), is_active: userForm.is_active }
      if (userForm.password) payload.password = userForm.password
      await authApi.users.update(editingUser.value.id, payload)
      toast.success(t('userCenter.userUpdated'))
    } else {
      await authApi.users.create({
        ...teamFields(),
        username: userForm.username,
        password: userForm.password,
        is_active: true,
      })
      toast.success(t('userCenter.userCreated'))
    }
    userModalOpen.value = false
    await fetchUsers()
  } catch (err) {
    // Server messages (e.g. "You cannot remove your own admin access.") arrive in
    // the standard error envelope, not as DRF's bare field lists.
    toast.error(getApiErrorDetails(err).message || t('userCenter.failedToSave'))
  } finally {
    saveUserLoading.value = false
  }
}

const promotingId = ref(null)

async function makeAdmin(user) {
  const name = user.full_name || user.username
  if (!confirm(t('userCenter.makeAdminConfirm', { name }))) return
  promotingId.value = user.id
  try {
    // An operator's position must be cleared too: the server only allows the
    // operator positions on the employee role.
    await authApi.users.update(user.id, { role: 'super_admin', sub_role: 'admin' })
    toast.success(t('userCenter.madeAdmin', { name }))
    await fetchUsers()
  } catch (err) {
    toast.error(getApiErrorDetails(err).message || t('userCenter.failedToSave'))
  } finally {
    promotingId.value = null
  }
}

async function forceLogout(user) {
  if (!confirm(t('userCenter.forceLogoutConfirm'))) return
  try {
    await authApi.users.forceLogout(user.id)
    toast.success(t('userCenter.userLoggedOutAllDevices'))
  } catch {
    toast.error(t('userCenter.failedToForceLogout'))
  }
}

watch(activeTab, (tab) => {
  if (tab === 'activity' && !activity.value.length && !activityLoading.value) {
    fetchActivity()
  }
})

onMounted(() => {
  fetchUsers()
})
</script>
