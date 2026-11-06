<template>
  <div>
    <nav v-if="!embedded" class="mb-6">
      <router-link to="/settings" class="text-[var(--text-secondary)] hover:text-gold transition-colors">
        <i class="fas me-2" :class="$i18n.locale === 'fa' ? 'fa-arrow-right' : 'fa-arrow-left'"></i>{{ $t('logs.backToSettings') }}
      </router-link>
    </nav>
    <h1 v-if="!embedded" class="text-2xl font-bold text-gold mb-6">{{ $t('logs.title') }}</h1>

    <!-- Filters -->
    <div
      v-if="!initialLoading"
      class="card-luxury mb-4 p-4 flex flex-col gap-4 md:flex-row md:flex-wrap md:items-end"
    >
      <div class="flex flex-col gap-1 min-w-[140px]">
        <label class="text-xs text-[var(--text-secondary)]">{{ $t('logs.level') }}</label>
        <select
          v-model="filterLevel"
          class="rounded-lg border border-[var(--border-color)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)]"
        >
          <option value="">{{ $t('logs.allLevels') }}</option>
          <option v-for="lv in levelOptions" :key="lv" :value="lv">{{ levelLabel(lv) }}</option>
        </select>
      </div>
      <div class="flex flex-col gap-1 min-w-[160px]">
        <label class="text-xs text-[var(--text-secondary)]">{{ $t('logs.source') }}</label>
        <select
          v-model="filterSource"
          class="rounded-lg border border-[var(--border-color)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)]"
        >
          <option value="">{{ $t('logs.allSources') }}</option>
          <option v-for="s in sourceOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </div>
      <div class="flex flex-col gap-1 flex-1 min-w-[200px]">
        <label class="text-xs text-[var(--text-secondary)]">{{ $t('logs.search') }}</label>
        <input
          v-model="filterSearch"
          type="search"
          :placeholder="$t('logs.searchPlaceholder')"
          class="rounded-lg border border-[var(--border-color)] bg-[var(--bg-input)] px-3 py-2 text-sm text-[var(--text-primary)] w-full"
          @keydown.enter="applyFilters"
        />
      </div>
      <div class="flex gap-2">
        <button
          type="button"
          class="px-4 py-2 rounded-lg bg-gold/20 text-gold text-sm font-medium hover:bg-gold/30 transition-colors"
          @click="applyFilters"
        >
          {{ $t('logs.apply') }}
        </button>
        <button
          type="button"
          class="px-4 py-2 rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] text-sm hover:bg-[var(--bg-hover)] transition-colors"
          @click="clearFilters"
        >
          {{ $t('logs.clearFilters') }}
        </button>
      </div>
    </div>

    <div v-if="initialLoading" class="card-luxury overflow-x-auto p-6">
      <div class="space-y-4">
        <BaseSkeleton v-for="i in 8" :key="i" variant="table-row" />
      </div>
    </div>
    <div
      v-else
      class="card-luxury w-full min-w-0 overflow-hidden relative"
      :class="{ 'opacity-70 pointer-events-none': fetching }"
    >
      <div class="w-full overflow-x-auto max-w-full hidden md:block">
        <table class="w-full min-w-[720px]">
          <thead>
            <tr class="border-b border-[var(--border-color)]">
              <th class="text-start py-4 px-4 text-gold font-semibold text-sm md:text-base whitespace-nowrap">{{ $t('logs.level') }}</th>
              <th class="text-start py-4 px-4 text-gold font-semibold text-sm md:text-base whitespace-nowrap">{{ $t('logs.source') }}</th>
              <th class="text-start py-4 px-4 text-gold font-semibold text-sm md:text-base">{{ $t('logs.message') }}</th>
              <th class="text-start py-4 px-4 text-gold font-semibold text-sm md:text-base whitespace-nowrap">{{ $t('logs.user') }}</th>
              <th class="text-start py-4 px-4 text-gold font-semibold text-sm md:text-base whitespace-nowrap">{{ $t('logs.date') }}</th>
              <th class="text-start py-4 px-4 text-gold font-semibold text-sm md:text-base whitespace-nowrap">{{ $t('logs.details') }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="log in logs" :key="log.id">
              <tr
                class="border-b border-[var(--border-card)] hover:bg-[var(--bg-hover)] transition-colors"
              >
                <td class="py-4 px-4 whitespace-nowrap">
                  <span
                    class="px-2 py-1 rounded text-xs font-medium"
                    :class="levelClass(log.level)"
                  >
                    {{ levelLabel(log.level) }}
                  </span>
                </td>
                <td class="py-4 px-4 text-[var(--text-secondary)] text-xs md:text-base break-words min-w-0 max-w-[160px]">{{ sourceLabel(log.source) }}</td>
                <td class="py-4 px-4 text-xs md:text-base break-words min-w-0 max-w-md">{{ log.message }}</td>
                <td class="py-4 px-4 text-[var(--text-secondary)] text-xs md:text-sm whitespace-nowrap">{{ log.username || '—' }}</td>
                <td class="py-4 px-4 text-[var(--text-secondary)] text-xs md:text-sm whitespace-nowrap">{{ formatDate(log.created_at) }}</td>
                <td class="py-4 px-4 whitespace-nowrap">
                  <button
                    v-if="log.details"
                    type="button"
                    class="text-xs text-gold hover:underline"
                    @click="toggleDetails(log.id)"
                  >
                    {{ expandedId === log.id ? $t('logs.hideDetails') : $t('logs.showDetails') }}
                  </button>
                  <span v-else class="text-xs text-[var(--text-secondary)] opacity-60">—</span>
                </td>
              </tr>
              <tr v-if="expandedId === log.id && log.details" class="border-b border-[var(--border-card)] bg-[var(--bg-hover)]/50">
                <td colspan="6" class="px-4 py-3">
                  <pre class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words max-h-64 overflow-y-auto font-mono">{{ formatDetails(log.details) }}</pre>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div class="block md:hidden divide-y divide-[var(--border-card)]">
        <div
          v-for="log in logs"
          :key="log.id"
          class="p-4 space-y-2"
        >
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <span
              class="px-2 py-1 rounded text-xs font-medium shrink-0"
              :class="levelClass(log.level)"
            >
              {{ levelLabel(log.level) }}
            </span>
            <span class="text-xs text-[var(--text-secondary)]">{{ formatDate(log.created_at) }}</span>
          </div>
          <p class="text-xs font-medium text-[var(--text-primary)]">{{ sourceLabel(log.source) }}</p>
          <p v-if="log.username" class="text-xs text-[var(--text-secondary)]">{{ $t('logs.user') }}: {{ log.username }}</p>
          <p class="text-xs text-[var(--text-secondary)] break-words">{{ log.message }}</p>
          <button
            v-if="log.details"
            type="button"
            class="text-xs text-gold"
            @click="toggleDetails(log.id)"
          >
            {{ expandedId === log.id ? $t('logs.hideDetails') : $t('logs.showDetails') }}
          </button>
          <pre
            v-if="expandedId === log.id && log.details"
            class="text-xs text-[var(--text-secondary)] whitespace-pre-wrap break-words max-h-48 overflow-y-auto font-mono mt-2"
          >{{ formatDetails(log.details) }}</pre>
        </div>
      </div>
      <p v-if="!fetching && (!logs || !logs.length)" class="text-center text-[var(--text-secondary)] py-8">{{ $t('logs.noLogsFound') }}</p>

      <!-- Pagination -->
      <div
        v-if="totalCount > 0"
        class="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-4 border-t border-[var(--border-card)]"
      >
        <p class="text-xs text-[var(--text-secondary)]">
          {{ $t('logs.page') }} {{ currentPage }} {{ $t('logs.of') }} {{ totalPages }} ({{ totalCount }})
        </p>
        <div class="flex gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg border border-[var(--border-color)] text-sm text-[var(--text-primary)] disabled:opacity-40"
            :disabled="currentPage <= 1 || fetching"
            @click="goPage(currentPage - 1)"
          >
            {{ $t('logs.prev') }}
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg border border-[var(--border-color)] text-sm text-[var(--text-primary)] disabled:opacity-40"
            :disabled="currentPage >= totalPages || fetching"
            @click="goPage(currentPage + 1)"
          >
            {{ $t('logs.next') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { settingsApi } from '@/services/api'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import { useDate } from '@/composables/useDate'

const { formatDateTime: formatDate } = useDate()
const { t, te } = useI18n()

defineProps({
  embedded: { type: Boolean, default: false },
})

const PAGE_SIZE = 50

const initialLoading = ref(true)
const fetching = ref(false)
const logs = ref([])
const totalCount = ref(0)
const currentPage = ref(1)

const filterLevel = ref('')
const filterSource = ref('')
const filterSearch = ref('')
const expandedId = ref(null)

const levelOptions = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

const sourceOptions = computed(() =>
  ['telegram', 'finalize', 'price_publisher', 'template_editor', 'external_api', 'system', 'other']
    .map((value) => ({ value, label: sourceLabel(value) })),
)

// Level and source are stored as codes (setting.Log); unknown ones show as-is.
function levelLabel(level) {
  const key = `logs.levels.${level}`
  return te(key) ? t(key) : level
}

function sourceLabel(source) {
  const key = `logs.sources.${source}`
  return te(key) ? t(key) : source
}

const totalPages = computed(() =>
  Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE)),
)

function levelClass(level) {
  const map = {
    ERROR: 'bg-red-500/20 text-red-400',
    WARNING: 'bg-amber-500/20 text-amber-400',
    INFO: 'bg-blue-500/20 text-blue-400',
    DEBUG: 'bg-gray-500/20 text-gray-400',
    CRITICAL: 'bg-red-600/20 text-red-300',
  }
  return map[level] ?? 'bg-gray-500/20'
}


function formatDetails(raw) {
  if (!raw) return ''
  try {
    const parsed = JSON.parse(raw)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return raw
  }
}

function toggleDetails(id) {
  expandedId.value = expandedId.value === id ? null : id
}

async function fetchLogs(page = 1) {
  fetching.value = true
  expandedId.value = null
  try {
    const params = { page }
    if (filterLevel.value) params.level = filterLevel.value
    if (filterSource.value) params.source = filterSource.value
    if (filterSearch.value.trim()) params.search = filterSearch.value.trim()

    const { data } = await settingsApi.logs(params)
    if (data && typeof data.count === 'number') {
      logs.value = data.results ?? []
      totalCount.value = data.count
      currentPage.value = page
    } else {
      logs.value = Array.isArray(data) ? data : data?.results ?? []
      totalCount.value = logs.value.length
      currentPage.value = 1
    }
  } catch {
    logs.value = []
    totalCount.value = 0
  } finally {
    fetching.value = false
    initialLoading.value = false
  }
}

function applyFilters() {
  fetchLogs(1)
}

function clearFilters() {
  filterLevel.value = ''
  filterSource.value = ''
  filterSearch.value = ''
  fetchLogs(1)
}

function goPage(page) {
  if (page < 1 || page > totalPages.value) return
  fetchLogs(page)
}

onMounted(() => {
  fetchLogs(1)
})
</script>
