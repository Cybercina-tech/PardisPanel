<template>
  <Teleport to="body">
    <Transition name="cmd-fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]"
        @click.self="close"
        @keydown.escape="close"
      >
        <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="close" />
        <div
          ref="paletteRef"
          class="relative w-full max-w-lg mx-4 rounded-2xl overflow-hidden shadow-2xl border"
          style="background: var(--bg-card); border-color: var(--border-card);"
        >
          <!-- Search input -->
          <div class="flex items-center gap-3 px-5 py-4 border-b" style="border-color: var(--border-card);">
            <i class="fas fa-search text-[var(--primary)]" />
            <input
              ref="searchInput"
              v-model="query"
              type="text"
              :placeholder="$t('search.placeholder')"
              class="flex-1 bg-transparent text-[var(--text-primary)] placeholder-[var(--text-secondary)] focus:outline-none text-base"
              @keydown.down.prevent="moveDown"
              @keydown.up.prevent="moveUp"
              @keydown.enter.prevent="selectCurrent"
            />
            <kbd class="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-xs font-mono text-[var(--text-secondary)] border" style="border-color: var(--border-card);">
              ESC
            </kbd>
          </div>

          <!-- Results -->
          <div class="max-h-80 overflow-y-auto py-2">
            <template v-if="query.trim()">
              <template v-if="filteredResults.length">
                <div v-for="group in groupedResults" :key="group.label" class="mb-1">
                  <p class="px-5 py-1.5 text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    {{ group.label }}
                  </p>
                  <button
                    v-for="item in group.items"
                    :key="item.id"
                    class="w-full flex items-center gap-3 px-5 py-3 text-start transition-colors"
                    :class="activeIndex === item._globalIndex ? 'bg-[var(--bg-hover)] text-[var(--primary)]' : 'text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'"
                    @click="selectItem(item)"
                    @mouseenter="activeIndex = item._globalIndex"
                  >
                    <i :class="item.icon" class="text-sm w-5 text-center text-[var(--text-secondary)]" />
                    <span class="flex-1 truncate" v-html="highlight(item.label)" />
                    <i class="fas fa-arrow-left text-xs text-[var(--text-secondary)] rtl:rotate-180" />
                  </button>
                </div>
              </template>
              <div v-else class="px-5 py-8 text-center">
                <i class="fas fa-search text-3xl text-[var(--text-secondary)] mb-3" />
                <p class="text-[var(--text-secondary)]">{{ $t('search.noResults') }}</p>
              </div>
            </template>

            <!-- Recent searches / quick links when empty -->
            <template v-else>
              <div v-if="recentSearches.length" class="mb-2">
                <div class="flex items-center justify-between px-5 py-1.5">
                  <p class="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                    {{ $t('search.recentSearches') }}
                  </p>
                  <button class="text-xs text-[var(--text-secondary)] hover:text-[var(--primary)]" @click="clearRecent">
                    {{ $t('search.clearRecent') }}
                  </button>
                </div>
                <button
                  v-for="(term, idx) in recentSearches"
                  :key="idx"
                  class="w-full flex items-center gap-3 px-5 py-2.5 text-start text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                  @click="query = term"
                >
                  <i class="fas fa-clock text-sm w-5 text-center text-[var(--text-secondary)]" />
                  <span class="truncate">{{ term }}</span>
                </button>
              </div>
              <div v-else class="px-5 py-8 text-center">
                <i class="fas fa-keyboard text-3xl text-[var(--text-secondary)] mb-3" />
                <p class="text-[var(--text-secondary)]">{{ $t('search.hint') }}</p>
              </div>

              <p class="px-5 py-1.5 text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                {{ $t('search.pages') }}
              </p>
              <button
                v-for="page in pageLinks"
                :key="page.to"
                class="w-full flex items-center gap-3 px-5 py-2.5 text-start text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                @click="navigateTo(page.to)"
              >
                <i :class="page.icon" class="text-sm w-5 text-center text-[var(--text-secondary)]" />
                <span>{{ $t(page.labelKey) }}</span>
              </button>
            </template>
          </div>

          <!-- Footer hint -->
          <div class="flex items-center gap-4 px-5 py-3 border-t text-xs text-[var(--text-secondary)]" style="border-color: var(--border-card);">
            <span class="flex items-center gap-1">
              <kbd class="px-1.5 py-0.5 rounded border text-[10px]" style="border-color: var(--border-card);">↑↓</kbd>
              navigate
            </span>
            <span class="flex items-center gap-1">
              <kbd class="px-1.5 py-0.5 rounded border text-[10px]" style="border-color: var(--border-card);">↵</kbd>
              select
            </span>
            <span class="flex items-center gap-1">
              <kbd class="px-1.5 py-0.5 rounded border text-[10px]" style="border-color: var(--border-card);">esc</kbd>
              close
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { categoryApi, specialPriceApi } from '@/services/api'
import {
  STORAGE_RECENT_SEARCHES,
  STORAGE_RECENT_SEARCHES_LEGACY,
  storageGet,
  storageSet,
  storageRemove,
} from '@/constants/branding.js'

const { t } = useI18n()
const router = useRouter()

const visible = ref(false)
const query = ref('')
const activeIndex = ref(0)
const searchInput = ref(null)
const paletteRef = ref(null)

const categories = ref([])
const specialPrices = ref([])
const recentSearches = ref([])

const pageLinks = [
  { to: '/', labelKey: 'sidebar.dashboard', icon: 'fas fa-tachometer-alt' },
  { to: '/update', labelKey: 'sidebar.priceHub', icon: 'fas fa-dollar-sign' },
  { to: '/categories', labelKey: 'sidebar.categories', icon: 'fas fa-tags' },
  { to: '/finalize', labelKey: 'sidebar.finalize', icon: 'fas fa-check-circle' },
  { to: '/analysis', labelKey: 'sidebar.analysis', icon: 'fas fa-chart-line' },
  { to: '/settings', labelKey: 'sidebar.settings', icon: 'fas fa-cog' },
  { to: '/telegram/send', labelKey: 'sidebar.telegram', icon: 'fab fa-telegram' },
  { to: '/templates', labelKey: 'sidebar.templates', icon: 'fas fa-file-image' },
]

const searchableItems = computed(() => {
  const items = []

  for (const cat of categories.value) {
    items.push({
      id: `cat-${cat.id}`,
      label: cat.name,
      group: t('search.categories'),
      icon: 'fas fa-tags',
      to: `/categories/${cat.id}/edit`,
    })
  }

  for (const sp of specialPrices.value) {
    items.push({
      id: `sp-${sp.id}`,
      label: sp.name,
      group: t('search.specialPrices'),
      icon: 'fas fa-star',
      to: `/prices/special/${sp.id}/update`,
    })
  }

  for (const page of pageLinks) {
    items.push({
      id: `page-${page.to}`,
      label: t(page.labelKey),
      group: t('search.pages'),
      icon: page.icon,
      to: page.to,
    })
  }

  return items
})

const filteredResults = computed(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return []
  return searchableItems.value.filter(item =>
    item.label.toLowerCase().includes(q)
  )
})

const groupedResults = computed(() => {
  const groups = {}
  let globalIndex = 0
  for (const item of filteredResults.value) {
    if (!groups[item.group]) groups[item.group] = { label: item.group, items: [] }
    groups[item.group].items.push({ ...item, _globalIndex: globalIndex++ })
  }
  return Object.values(groups)
})

function highlight(text) {
  const q = query.value.trim()
  if (!q) return text
  const regex = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<mark class="bg-gold/30 text-[var(--text-primary)] rounded px-0.5">$1</mark>')
}

function moveDown() {
  if (activeIndex.value < filteredResults.value.length - 1) activeIndex.value++
}

function moveUp() {
  if (activeIndex.value > 0) activeIndex.value--
}

function selectCurrent() {
  const item = filteredResults.value[activeIndex.value]
  if (item) selectItem(item)
}

function selectItem(item) {
  saveRecentSearch(query.value.trim())
  close()
  router.push(item.to)
}

function navigateTo(to) {
  close()
  router.push(to)
}

function open() {
  visible.value = true
  query.value = ''
  activeIndex.value = 0
  loadRecent()
  fetchData()
  nextTick(() => searchInput.value?.focus())
}

function close() {
  visible.value = false
  query.value = ''
}

function loadRecent() {
  try {
    const raw = storageGet(STORAGE_RECENT_SEARCHES, STORAGE_RECENT_SEARCHES_LEGACY) || '[]'
    recentSearches.value = JSON.parse(raw).slice(0, 5)
  } catch {
    recentSearches.value = []
  }
}

function saveRecentSearch(term) {
  if (!term) return
  let recent = recentSearches.value.filter(r => r !== term)
  recent.unshift(term)
  recent = recent.slice(0, 5)
  storageSet(STORAGE_RECENT_SEARCHES, STORAGE_RECENT_SEARCHES_LEGACY, JSON.stringify(recent))
  recentSearches.value = recent
}

function clearRecent() {
  storageRemove(STORAGE_RECENT_SEARCHES, STORAGE_RECENT_SEARCHES_LEGACY)
  recentSearches.value = []
}

async function fetchData() {
  try {
    const [catRes, spRes] = await Promise.all([
      categoryApi.list().catch(() => ({ data: [] })),
      specialPriceApi.list().catch(() => ({ data: [] })),
    ])
    categories.value = catRes.data ?? []
    specialPrices.value = Array.isArray(spRes.data) ? spRes.data : []
  } catch { /* noop */ }
}

watch(query, () => { activeIndex.value = 0 })

function handleKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    if (visible.value) close()
    else open()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  loadRecent()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

defineExpose({ open, close })
</script>

<style scoped>
.cmd-fade-enter-active,
.cmd-fade-leave-active {
  transition: opacity 0.2s ease;
}
.cmd-fade-enter-from,
.cmd-fade-leave-to {
  opacity: 0;
}
</style>
