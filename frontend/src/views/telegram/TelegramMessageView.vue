<template>
  <div class="relative w-full min-w-0 overflow-hidden">
    <div>
      <div class="flex flex-wrap items-end justify-between gap-3 mb-6">
        <h1 class="text-2xl font-bold text-gold animate-fade-in-up">
          {{ $t('telegram.hubTitle') }}
        </h1>
      </div>

      <div class="flex flex-col lg:flex-row gap-6 items-start min-w-0">
        <div class="flex-1 min-w-0 w-full">
          <div>
            <!-- Tabs -->
            <div class="card-luxury mb-6 px-3 py-2 flex flex-wrap gap-2 items-center rtl:flex-row-reverse min-w-0">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                class="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all"
                :class="activeTab === tab.id ? 'btn-luxury' : 'btn-luxury-outline bg-transparent'"
                @click="activeTab = tab.id"
              >
                <i :class="tab.icon" />
                <span>{{ $t(tab.labelKey) }}</span>
              </button>
            </div>

            <!-- Tab content -->
            <Transition name="fade-slide" mode="out-in">
              <div :key="activeTab">
        <!-- Tab 1: Messenger -->
        <div
          v-if="activeTab === 'messenger'"
          class="grid grid-cols-1 md:grid-cols-2 gap-6 items-start animate-fade-in-up rtl:md:grid-flow-dense"
        >
          <!-- Form -->
          <form @submit.prevent="handleSend" class="card-luxury space-y-4 px-4 py-3 min-w-0 w-full">
            <h2 class="text-lg font-semibold text-gold mb-2">
              {{ $t('telegram.tabs.messenger') }}
            </h2>

            <div>
              <label class="block text-sm font-medium text-gray-400 mb-2">
                {{ $t('telegram.messenger.channelLabel') }}
              </label>
              <select v-model="channelId" class="input-luxury" required>
                <option value="">{{ $t('telegram.messenger.channelPlaceholder') }}</option>
                <option
                  v-for="ch in channels"
                  :key="ch.id"
                  :value="ch.id"
                >
                  {{ ch.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-400 mb-2">
                {{ $t('telegram.messenger.bannerLabel') }}
              </label>
              <select v-model="bannerKey" class="input-luxury">
                <option
                  v-for="opt in bannerOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ $t(opt.labelKey) }}
                </option>
              </select>
            </div>

            <div v-if="useDoublePrice" class="grid grid-cols-1 gap-3">
              <div>
                <label class="block text-sm font-medium text-gray-400 mb-2">
                  {{ $t('telegram.messenger.cashPrice') }}
                </label>
                <input
                  v-model.number="cashPrice"
                  type="number"
                  step="0.01"
                  min="0"
                  class="input-luxury"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-400 mb-2">
                  {{ $t('telegram.messenger.accountPrice') }}
                </label>
                <input
                  v-model.number="accountPrice"
                  type="number"
                  step="0.01"
                  min="0"
                  class="input-luxury"
                />
              </div>
            </div>
            <div v-else>
              <label class="block text-sm font-medium text-gray-400 mb-2">
                {{ $t('telegram.messenger.price') }}
              </label>
              <input
                v-model.number="singlePrice"
                type="number"
                step="0.01"
                min="0"
                class="input-luxury"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-400 mb-2">
                {{ $t('telegram.messenger.messageLabel') }}
              </label>
              <textarea
                v-model="message"
                class="input-luxury"
                rows="4"
                :placeholder="$t('telegram.messenger.messagePlaceholder')"
              />
            </div>

            <div class="flex flex-wrap gap-4">
              <button type="submit" class="btn-luxury-gradient min-h-[48px]" :disabled="submitting || !channelId">
                <LoadingSpinner v-if="submitting" class="w-5 h-5" />
                <span v-else>{{ $t('telegram.messenger.send') }}</span>
              </button>
            </div>
          </form>

          <!-- Live preview -->
          <div class="card-luxury px-4 py-3 animate-fade-in-up hover-lift min-w-0">
            <h2 class="text-lg font-semibold text-gold mb-4">
              {{ $t('telegram.messenger.livePreview') }}
            </h2>
            <div class="bg-[var(--glass-bg)] border border-[var(--glass-border)] rounded-2xl p-4 space-y-3">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-gold/80 to-amber-500/80 flex items-center justify-center text-xs font-bold text-black shadow-soft shrink-0">
                  {{ selectedChannelInitials }}
                </div>
                <div class="min-w-0 flex-1">
                  <p class="font-semibold text-[var(--text-primary)] truncate">
                    {{ selectedChannel?.name || $t('telegram.messenger.channelDefault') }}
                  </p>
                  <p class="text-xs text-[var(--text-secondary)]">
                    Telegram • {{ previewTimestamp }}
                  </p>
                </div>
              </div>

              <div class="mt-2 rounded-2xl bg-black/20 border border-white/5 px-4 py-3 space-y-2">
                <p v-if="selectedBannerLabel" class="text-xs font-semibold text-gold uppercase tracking-wide">
                  {{ selectedBannerLabel }}
                </p>
                <p v-if="previewPriceLine" class="text-sm text-[var(--text-primary)]">
                  {{ previewPriceLine }}
                </p>
                <p v-if="message" class="text-sm text-[var(--text-primary)] whitespace-pre-line">
                  {{ message }}
                </p>
              </div>

              <div class="flex justify-end">
                <div class="inline-flex rounded-full bg-white/5 border border-white/10 px-3 py-1.5 text-xs text-[var(--text-secondary)] gap-2">
                  <span class="inline-flex items-center gap-1">
                    <i class="fas fa-eye" />
                    0
                  </span>
                  <span class="inline-flex items-center gap-1">
                    <i class="fas fa-check-double" />
                    0
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 2: Bot Setup -->
        <div
          v-else-if="activeTab === 'bot'"
          class="space-y-6 animate-fade-in-up"
        >
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-gold">
                {{ $t('telegram.tabs.botSetup') }}
              </h2>
              <p class="text-sm text-[var(--text-secondary)] mt-1">
                {{ $t('telegram.botSetup.description') }}
              </p>
            </div>
            <button
              type="button"
              class="btn-luxury inline-flex items-center gap-2"
              @click="$router.push({ name: 'telegram-bot-new' })"
            >
              <i class="fas fa-plus" />
              {{ $t('telegram.botSetup.addNewBot') }}
            </button>
          </div>

          <!-- Bot list: empty state -->
          <div
            v-if="!botsList.length"
            class="card-luxury px-6 py-12 flex flex-col items-center justify-center text-center"
          >
            <div class="w-16 h-16 rounded-2xl flex items-center justify-center mb-4 bg-[var(--glass-bg)] border border-[var(--glass-border)]">
              <i class="fas fa-robot text-2xl text-gold opacity-80" />
            </div>
            <h3 class="text-lg font-semibold text-[var(--text-primary)] mb-2">
              {{ $t('telegram.botSetup.noBots') }}
            </h3>
            <p class="text-sm text-[var(--text-secondary)] mb-6 max-w-sm">
              {{ $t('telegram.botSetup.noBotsDesc') }}
            </p>
            <button type="button" class="btn-luxury" @click="$router.push({ name: 'telegram-bot-new' })">
              <i class="fas fa-plus" />
              {{ $t('telegram.botSetup.addNewBot') }}
            </button>
          </div>

          <!-- Bot list: card grid -->
          <div
            v-else
            class="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            <div
              v-for="b in botsList"
              :key="b.id"
              class="card-luxury px-4 py-4 relative min-w-0 hover-lift transition-all"
            >
              <div class="absolute top-3 right-3 flex gap-2 rtl:flex-row-reverse">
                <button
                  type="button"
                  class="btn-luxury-outline p-2 rounded-lg text-sm"
                  :title="$t('common.edit')"
                  @click="$router.push({ name: 'telegram-bot-edit', params: { id: b.id } })"
                >
                  <i class="fas fa-pencil-alt" />
                </button>
                <button
                  type="button"
                  class="p-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/30 transition-colors"
                  :title="$t('common.delete')"
                  @click="openDeleteBotConfirm(b)"
                >
                  <i class="fas fa-trash" />
                </button>
              </div>
              <div class="pr-24 rtl:pr-4 rtl:pl-24">
                <h3 class="text-[var(--text-primary)] font-semibold truncate">
                  {{ b.name || `Bot #${b.id}` }}
                </h3>
                <p
                  v-if="b.display_name"
                  class="text-sm text-[var(--text-secondary)] truncate mt-0.5"
                >
                  {{ b.display_name }}
                </p>
                <p
                  v-if="b.notes"
                  class="text-sm text-[var(--text-secondary)] mt-2 line-clamp-2"
                >
                  {{ b.notes }}
                </p>
                <p class="text-xs text-[var(--text-secondary)] mt-2">
                  {{ formatBotCreatedAt(b.created_at) }}
                </p>
                <span
                  class="inline-block mt-2 text-xs px-2 py-1 rounded-full"
                  :class="b.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'"
                >
                  {{ b.is_active ? $t('telegram.channels.active') : $t('telegram.channels.inactive') }}
                </span>
              </div>
            </div>
          </div>

          <!-- Delete Bot Confirmation Modal -->
          <Teleport to="body">
            <Transition name="modal-fade">
              <div
                v-if="botDeleteConfirm"
                class="fixed inset-0 z-50 flex items-center justify-center"
              >
                <div
                  class="absolute inset-0 bg-black/60 backdrop-blur-sm"
                  @click="botDeleteConfirm = null"
                />
                <div
                  class="relative z-10 w-full max-w-md mx-4 rounded-2xl p-6 shadow-2xl"
                  style="background: var(--bg-card, #1e2535);"
                  role="dialog"
                  aria-modal="true"
                >
                  <h3 class="text-lg font-semibold text-[var(--text-primary)] mb-2">
                    {{ $t('common.delete') }}
                  </h3>
                  <p class="text-sm text-[var(--text-secondary)] mb-6">
                    {{ $t('telegram.botSetup.deleteBotConfirm', { name: botDeleteConfirm?.name || `Bot #${botDeleteConfirm?.id}` }) }}
                  </p>
                  <div class="flex gap-3 justify-end">
                    <button type="button" class="btn-luxury-outline" :disabled="botDeleting" @click="botDeleteConfirm = null">
                      {{ $t('common.cancel') }}
                    </button>
                    <button
                      type="button"
                      class="px-4 py-2 rounded-lg font-medium bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                      :disabled="botDeleting"
                      @click="confirmDeleteBot"
                    >
                      <LoadingSpinner v-if="botDeleting" class="w-5 h-5 inline" />
                      <span v-else>{{ $t('common.delete') }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </Transition>
          </Teleport>
        </div>

        <!-- Tab: post editor (category caption + buttons, live preview) -->
        <div
          v-else-if="activeTab === 'posts'"
          class="space-y-6 animate-fade-in-up"
        >
          <div class="card-luxury px-4 py-3 space-y-2">
            <h2 class="text-lg font-semibold text-gold">{{ $t('telegram.posts.title') }}</h2>
            <p class="text-sm text-gray-400">{{ $t('telegram.posts.hint') }}</p>
            <select v-model="postCategoryId" class="input-luxury max-w-sm">
              <option v-for="c in postCategories" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
          </div>
          <TelegramStudioView
            v-if="postCategoryId"
            :key="postCategoryId"
            :category-id="postCategoryId"
            embedded
          />
        </div>

        <!-- Tab 3: Channels -->
        <div
          v-else-if="activeTab === 'channels'"
          class="space-y-6 animate-fade-in-up"
        >
          <div class="card-luxury px-4 py-3">
            <div class="flex flex-wrap items-start justify-between gap-3 mb-2">
              <h2 class="text-lg font-semibold text-gold">
                {{ $t('telegram.channels.title') }}
              </h2>
            </div>
            <p class="text-sm text-gray-400">
              {{ $t('telegram.channels.description') }}
            </p>
            <form @submit.prevent="addChannel" class="space-y-3">
              <h3 class="text-sm font-medium text-gold">{{ $t('telegram.channels.addChannel') }}</h3>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label class="block text-sm font-medium text-gray-400 mb-1">{{ $t('telegram.channels.channelName') }}</label>
                  <input
                    v-model="channelForm.name"
                    type="text"
                    class="input-luxury w-full"
                    :placeholder="$t('telegram.channels.channelNamePlaceholder')"
                    required
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-400 mb-1">{{ $t('telegram.channels.channelId') }}</label>
                  <input
                    v-model="channelForm.chat_id"
                    type="text"
                    class="input-luxury w-full"
                    :placeholder="$t('telegram.channels.channelIdPlaceholder')"
                    required
                  />
                </div>
              </div>
              <div class="flex flex-wrap gap-4 items-center">
                <div>
                  <label class="block text-sm font-medium text-gray-400 mb-1">{{ $t('telegram.channels.bot') }}</label>
                  <select v-model="channelForm.bot" class="input-luxury" required>
                    <option value="">{{ $t('telegram.channels.selectBot') }}</option>
                    <option v-for="b in botsList" :key="b.id" :value="b.id">{{ b.name || b.display_name || `Bot #${b.id}` }}</option>
                  </select>
                </div>
                <div class="mt-6">
                  <BaseCheckbox v-model="channelForm.is_active">{{ $t('telegram.channels.active') }}</BaseCheckbox>
                </div>
                <button type="submit" class="btn-luxury" :disabled="channelSaving">
                  <LoadingSpinner v-if="channelSaving" class="w-5 h-5" />
                  <span v-else>{{ $t('telegram.channels.add') }}</span>
                </button>
              </div>
            </form>
          </div>

          <div class="card-luxury overflow-hidden w-full min-w-0 px-4 py-3">
            <div v-if="manageChannelsLoading" class="space-y-2">
              <div v-for="i in 3" :key="i" class="h-12 rounded bg-white/5 animate-pulse" />
            </div>
            <template v-else>
              <div class="w-full overflow-x-auto max-w-full">
                <table class="w-full text-sm min-w-[500px]">
                <thead>
                  <tr class="text-[var(--text-secondary)] border-b" style="border-color: var(--glass-border);">
                    <th class="text-left py-3 px-4 font-medium">{{ $t('telegram.channels.bot') }}</th>
                    <th class="text-left py-3 px-4 font-medium">{{ $t('telegram.channels.channelName') }}</th>
                    <th class="text-left py-3 px-4 font-medium">{{ $t('telegram.channels.channelId') }}</th>
                    <th class="text-left py-3 px-4 font-medium">{{ $t('common.status') }}</th>
                    <th class="text-left py-3 px-4 font-medium">{{ $t('common.actions') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(ch, idx) in manageChannelsList"
                    :key="ch.id"
                    class="border-b transition-colors hover:bg-[var(--bg-hover)] animate-fade-in-up"
                    :style="{ 'animation-delay': `${idx * 0.03}s` }"
                  >
                    <td class="py-3 px-4 text-[var(--text-primary)] break-words min-w-0">{{ ch.bot_name }}</td>
                    <td class="py-3 px-4 text-[var(--text-primary)] break-words min-w-0">{{ ch.name }}</td>
                    <td class="py-3 px-4 text-[var(--text-secondary)] font-mono text-xs break-all">{{ ch.chat_id }}</td>
                    <td class="py-3 px-4">
                      <div class="flex flex-wrap items-center gap-1.5">
                        <span
                          class="text-xs px-2 py-1 rounded-full"
                          :class="ch.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-gray-500/10 text-gray-400'"
                        >
                          {{ ch.is_active ? $t('telegram.channels.active') : $t('telegram.channels.inactive') }}
                        </span>
                        <span
                          v-if="!ch.bot_admin_verified"
                          class="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400"
                          :title="$t('telegram.channels.notAdminHint')"
                        >
                          <i class="fas fa-triangle-exclamation me-1" aria-hidden="true" />
                          {{ $t('telegram.channels.notAdmin') }}
                        </span>
                      </div>
                    </td>
                    <td class="py-3 px-4 flex gap-2">
                      <button
                        type="button"
                        class="btn-luxury-outline text-sm py-1.5 px-2"
                        @click="openEditChannel(ch)"
                      >
                        <i class="fas fa-edit" />
                      </button>
                      <button
                        type="button"
                        class="btn-luxury-outline text-sm py-1.5 px-2 text-red-400 hover:bg-red-500/10"
                        @click="confirmDeleteChannel(ch)"
                      >
                        <i class="fas fa-trash" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              </div>
              <p v-if="!manageChannelsList.length && !manageChannelsLoading" class="text-center text-gray-500 py-6">
                {{ $t('telegram.channels.noChannels') }}
              </p>
            </template>
          </div>

          <!-- Edit channel modal -->
          <div
            v-if="editingChannel"
            class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
            @click.self="editingChannel = null"
          >
            <div class="card-luxury max-w-md w-full p-4 space-y-3">
              <h3 class="text-lg font-semibold text-gold">{{ $t('telegram.channels.editChannel') }}</h3>
              <div>
                <label class="block text-sm font-medium text-gray-400 mb-1">{{ $t('telegram.channels.channelName') }}</label>
                <input v-model="editChannelForm.name" type="text" class="input-luxury w-full" required />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-400 mb-1">{{ $t('telegram.channels.channelId') }}</label>
                <input v-model="editChannelForm.chat_id" type="text" class="input-luxury w-full" required />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-400 mb-1">{{ $t('telegram.channels.bot') }}</label>
                <select v-model="editChannelForm.bot" class="input-luxury w-full" required>
                  <option value="">{{ $t('telegram.channels.selectBot') }}</option>
                  <option v-for="b in botsList" :key="b.id" :value="b.id">{{ b.name || b.display_name || `Bot #${b.id}` }}</option>
                </select>
              </div>
              <BaseCheckbox v-model="editChannelForm.is_active">{{ $t('telegram.channels.active') }}</BaseCheckbox>
              <div class="flex gap-2 pt-2">
                <button type="button" class="btn-luxury" :disabled="channelSaving" @click="saveEditChannel">
                  <LoadingSpinner v-if="channelSaving" class="w-5 h-5" />
                  <span v-else>{{ $t('common.save') }}</span>
                </button>
                <button type="button" class="btn-luxury-outline" @click="editingChannel = null">
                  {{ $t('common.cancel') }}
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useToast } from 'vue-toastification'
import { telegramApi, categoryApi } from '@/services/api'
import TelegramStudioView from '@/views/categories/TelegramStudioView.vue'
import { createAppDateTimeFormat } from '@/utils/localeFormat.js'
import LoadingSpinner from '@/components/ui/LoadingSpinner.vue'
import BaseCheckbox from '@/components/ui/BaseCheckbox.vue'

const { t, locale } = useI18n()
const toast = useToast()

const tabs = [
  { id: 'messenger', labelKey: 'telegram.tabs.messenger', icon: 'fas fa-paper-plane' },
  { id: 'posts', labelKey: 'telegram.tabs.posts', icon: 'fas fa-pen-to-square' },
  { id: 'bot', labelKey: 'telegram.tabs.botSetup', icon: 'fas fa-robot' },
  { id: 'channels', labelKey: 'telegram.tabs.channels', icon: 'fas fa-broadcast-tower' },
]

const activeTab = ref('messenger')
const route = useRoute()

watch(() => route.query.tab, (tab) => {
  if (tab === 'botSetup') activeTab.value = 'bot'
  else if (tabs.some((item) => item.id === tab)) activeTab.value = tab
}, { immediate: true })

const postCategories = ref([])
const postCategoryId = ref('')

async function loadPostCategories() {
  try {
    const { data } = await categoryApi.list()
    postCategories.value = Array.isArray(data) ? data : (data?.results ?? [])
    if (!postCategoryId.value && postCategories.value.length) {
      postCategoryId.value = String(route.query.category || postCategories.value[0].id)
    }
  } catch {
    postCategories.value = []
  }
}

watch(activeTab, (tab) => {
  if (tab === 'posts' && !postCategories.value.length) loadPostCategories()
}, { immediate: true })

const channels = ref([])
const channelId = ref('')
const message = ref('')
const submitting = ref(false)

const botsList = ref([])
const botDeleteConfirm = ref(null)
const botDeleting = ref(false)

const manageChannelsList = ref([])
const manageChannelsLoading = ref(false)
const channelForm = ref({
  name: '',
  chat_id: '',
  bot: '',
  is_active: true,
})
const channelSaving = ref(false)
const editingChannel = ref(null)
const editChannelForm = ref({ name: '', chat_id: '', bot: '', is_active: true })

const bannerKey = ref('none')
const cashPrice = ref('')
const accountPrice = ref('')
const singlePrice = ref('')

const bannerOptions = [
  { value: 'none', labelKey: 'telegram.messenger.bannerNone' },
  { value: 'buy_gbp_double', labelKey: 'telegram.messenger.bannerBuyDouble' },
  { value: 'sell_gbp_double', labelKey: 'telegram.messenger.bannerSellDouble' },
  { value: 'generic_single', labelKey: 'telegram.messenger.bannerGenericSingle' },
]

const useDoublePrice = computed(() =>
  bannerKey.value === 'buy_gbp_double' || bannerKey.value === 'sell_gbp_double',
)

const selectedChannel = computed(() =>
  channels.value.find((c) => String(c.id) === String(channelId.value)) || null,
)

const selectedChannelInitials = computed(() => {
  const name = selectedChannel.value?.name || 'CH'
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'CH'
})

const selectedBannerLabel = computed(() => {
  const found = bannerOptions.find((b) => b.value === bannerKey.value)
  return found && found.value !== 'none' ? t(found.labelKey) : ''
})

const previewPriceLine = computed(() => {
  if (useDoublePrice.value) {
    const parts = []
    if (cashPrice.value) {
      parts.push(`Cash: ${cashPrice.value}`)
    }
    if (accountPrice.value) {
      parts.push(`Account: ${accountPrice.value}`)
    }
    return parts.join(' | ')
  }
  if (singlePrice.value) {
    return `Price: ${singlePrice.value}`
  }
  return ''
})

const previewTimestamp = computed(() => {
  const now = new Date()
  const appLoc = locale.value === 'fa' ? 'fa' : 'en'
  return createAppDateTimeFormat(appLoc, { hour: '2-digit', minute: '2-digit' }).format(now)
})

async function loadChannels() {
  try {
    const { data } = await telegramApi.channels()
    channels.value = data ?? []
  } catch {
    channels.value = []
  }
}

onMounted(() => {
  loadChannels()
  loadBots()
  loadManageChannels()
})

async function loadManageChannels() {
  manageChannelsLoading.value = true
  try {
    const { data } = await telegramApi.channelsManage.list()
    manageChannelsList.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    manageChannelsList.value = []
  } finally {
    manageChannelsLoading.value = false
  }
}

async function addChannel() {
  if (!channelForm.value.bot) return
  channelSaving.value = true
  try {
    await telegramApi.channelsManage.create({
      name: channelForm.value.name.trim(),
      chat_id: channelForm.value.chat_id.trim(),
      bot: Number(channelForm.value.bot),
      is_active: channelForm.value.is_active,
    })
    toast.success(t('toast.saveSuccess'))
    channelForm.value = { name: '', chat_id: '', bot: '', is_active: true }
    await loadManageChannels()
    const { data } = await telegramApi.channels().catch(() => ({ data: [] }))
    channels.value = data ?? []
  } catch (err) {
    const msg = err.response?.data?.detail || t('toast.serverError')
    toast.error(typeof msg === 'string' ? msg : t('toast.serverError'))
  } finally {
    channelSaving.value = false
  }
}

function openEditChannel(ch) {
  editingChannel.value = ch
  editChannelForm.value = {
    name: ch.name,
    chat_id: ch.chat_id,
    bot: ch.bot,
    is_active: !!ch.is_active,
  }
}

async function saveEditChannel() {
  if (!editingChannel.value || !editChannelForm.value.bot) return
  channelSaving.value = true
  try {
    await telegramApi.channelsManage.update(editingChannel.value.id, {
      name: editChannelForm.value.name.trim(),
      chat_id: editChannelForm.value.chat_id.trim(),
      bot: Number(editChannelForm.value.bot),
      is_active: editChannelForm.value.is_active,
    })
    toast.success(t('toast.saveSuccess'))
    editingChannel.value = null
    await loadManageChannels()
    const { data } = await telegramApi.channels().catch(() => ({ data: [] }))
    channels.value = data ?? []
  } catch (err) {
    const msg = err.response?.data?.detail || t('toast.serverError')
    toast.error(typeof msg === 'string' ? msg : t('toast.serverError'))
  } finally {
    channelSaving.value = false
  }
}

function confirmDeleteChannel(ch) {
  if (!window.confirm(t('telegram.channels.deleteConfirm', { name: ch.name }))) return
  deleteChannel(ch)
}

async function deleteChannel(ch) {
  try {
    await telegramApi.channelsManage.delete(ch.id)
    toast.success(t('toast.deleteSuccess'))
    await loadManageChannels()
    const { data } = await telegramApi.channels().catch(() => ({ data: [] }))
    channels.value = data ?? []
  } catch (err) {
    toast.error(t('toast.serverError'))
  }
}

async function loadBots() {
  try {
    const { data } = await telegramApi.bots.list()
    botsList.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    botsList.value = []
  }
}

function formatBotCreatedAt(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    if (Number.isNaN(d.getTime())) return '—'
    const appLoc = locale.value === 'fa' ? 'fa' : 'en'
    return createAppDateTimeFormat(appLoc, { year: 'numeric', month: 'short', day: 'numeric' }).format(d)
  } catch {
    return '—'
  }
}

function openDeleteBotConfirm(bot) {
  botDeleteConfirm.value = { id: bot.id, name: bot.name || bot.display_name || `Bot #${bot.id}` }
}

async function confirmDeleteBot() {
  if (!botDeleteConfirm.value) return
  await deleteBot(botDeleteConfirm.value.id)
  botDeleteConfirm.value = null
}

async function deleteBot(id) {
  botDeleting.value = true
  try {
    await telegramApi.bots.delete(id)
    toast.success(t('toast.deleteSuccess'))
    await loadBots()
  } catch (err) {
    const msg = err.response?.data?.detail || t('toast.serverError')
    toast.error(typeof msg === 'string' ? msg : t('toast.serverError'))
  } finally {
    botDeleting.value = false
  }
}

async function handleSend() {
  const ch = channels.value.find((c) => String(c.id) === String(channelId.value))
  if (!ch) return
  submitting.value = true
  try {
    const payload = {
      bot_id: ch.bot,
      channel_id: Number(channelId.value),
      message: message.value?.trim() || previewPriceLine.value || selectedBannerLabel.value || '',
    }
    if (bannerKey.value && bannerKey.value !== 'none') {
      payload.banner_key = bannerKey.value
    }
    if (useDoublePrice.value) {
      if (cashPrice.value !== '' && cashPrice.value != null && !Number.isNaN(cashPrice.value)) {
        payload.cash_price = cashPrice.value
      }
      if (accountPrice.value !== '' && accountPrice.value != null && !Number.isNaN(accountPrice.value)) {
        payload.account_price = accountPrice.value
      }
    } else {
      if (singlePrice.value !== '' && singlePrice.value != null && !Number.isNaN(singlePrice.value)) {
        payload.price = singlePrice.value
      }
    }
    await telegramApi.sendMessage(payload)
  } catch (err) {
    const msg = err.response?.data?.detail || t('toast.serverError')
    toast.error(typeof msg === 'string' ? msg : t('toast.serverError'))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
