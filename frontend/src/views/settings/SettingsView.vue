<template>
  <div class="w-full min-w-0 overflow-x-hidden pb-20 md:pb-28 px-4 md:px-0">
    <h1 class="text-xl sm:text-2xl font-bold text-gold mb-4 sm:mb-6">{{ $t('settings.title') }}</h1>

    <!-- Mobile (< 768px): horizontal scrollable tabs, hidden scrollbar -->
    <div class="settings-tabs-mobile md:hidden w-full min-w-0 mb-4 border-b border-[var(--glass-border)]">
      <div class="overflow-x-auto overflow-y-hidden flex flex-nowrap gap-2 pb-4 -mx-4 px-4" style="-webkit-overflow-scrolling: touch;">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="settings-tab flex-shrink-0 flex items-center gap-2 px-3 sm:px-4 py-3 rounded-xl font-medium transition-colors duration-200 whitespace-nowrap min-h-[48px]"
          :class="activeTab === tab.id ? 'bg-[var(--bg-hover)] text-gold border border-gold/40' : 'text-[var(--text-secondary)] border border-transparent hover:bg-[var(--bg-hover)] hover:text-[var(--primary)]'"
          @click="setTab(tab.id)"
        >
          <i :class="tab.icon" class="text-base shrink-0" />
          <span class="truncate max-w-[120px] sm:max-w-none">{{ $t(tab.labelKey) }}</span>
        </button>
      </div>
    </div>

    <div class="flex flex-col md:flex-row gap-4 sm:gap-6 w-full min-w-0">
      <!-- Desktop (≥768px): vertical tab menu -->
      <nav class="hidden md:flex md:flex-col md:w-56 md:min-w-[200px] shrink-0">
        <div class="card-luxury p-2 space-y-1" style="background: var(--glass-bg); backdrop-filter: blur(16px); border-color: var(--glass-border);">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="settings-tab w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors duration-200 text-start min-h-[48px]"
            :class="activeTab === tab.id ? 'bg-[var(--bg-hover)] text-gold border border-gold/30' : 'text-[var(--text-secondary)] border border-transparent hover:bg-[var(--bg-hover)] hover:text-[var(--primary)]'"
            @click="setTab(tab.id)"
          >
            <i :class="tab.icon" class="text-base w-5 text-center shrink-0" />
            <span class="truncate">{{ $t(tab.labelKey) }}</span>
          </button>
        </div>
      </nav>

      <!-- Content area with transition -->
      <div class="flex-1 min-w-0 w-full overflow-hidden">
        <div class="card-luxury overflow-hidden w-full min-w-0" style="background: var(--glass-bg); backdrop-filter: blur(16px); border-color: var(--glass-border);">
          <Transition name="fade-slide" mode="out-in">
            <!-- General -->
            <div v-if="activeTab === 'general'" key="general" class="p-4 sm:p-6 w-full min-w-0">
              <h2 class="text-lg font-semibold text-gold mb-4 sm:mb-6">{{ $t('settings.tabs.general') }}</h2>
              <form class="space-y-4 md:space-y-6 w-full max-w-xl min-w-0" @submit.prevent="saveGeneral">
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.general.platformName') }}</label>
                  <input
                    v-model="generalForm.platformName"
                    type="text"
                    class="input-luxury w-full min-w-0 min-h-[48px]"
                    :placeholder="$t('settings.general.platformName')"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.general.brandLogo') }}</label>
                  <div class="rounded-xl border p-3 sm:p-4 flex flex-col gap-3" style="border-color: var(--glass-border); background: var(--bg-input);">
                    <div class="flex items-center gap-3 sm:gap-4">
                      <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-xl border bg-primary-muted flex items-center justify-center overflow-hidden shrink-0" style="border-color: var(--border-color);">
                        <img
                          v-if="logoPreviewUrl"
                          :src="logoPreviewUrl"
                          :alt="$t('settings.general.logoPreviewAlt')"
                          class="w-full h-full object-contain"
                        >
                        <i v-else class="fas fa-coins text-xl sm:text-2xl text-[var(--primary)]" />
                      </div>
                      <div class="min-w-0">
                        <p class="text-sm font-medium text-[var(--text-primary)]">
                          {{ selectedLogoFile ? selectedLogoFile.name : $t('settings.general.currentLogo') }}
                        </p>
                        <p class="text-xs mt-1 text-[var(--text-secondary)]">
                          {{ $t('settings.general.logoFormatsHint') }}
                        </p>
                      </div>
                    </div>
                    <div class="flex flex-col sm:flex-row gap-2 sm:gap-3">
                      <input
                        ref="logoInputRef"
                        type="file"
                        accept="image/png,image/jpeg,image/gif,image/webp"
                        class="hidden"
                        @change="onLogoFileChange"
                      >
                      <button
                        type="button"
                        class="btn-luxury-outline min-h-[48px]"
                        :disabled="!canEditSiteSettings"
                        @click="openLogoPicker"
                      >
                        <i class="fas fa-upload" />
                        {{ $t('settings.general.uploadLogo') }}
                      </button>
                      <button
                        type="button"
                        class="btn-luxury-outline min-h-[48px] border-red-500/50 text-red-400 hover:bg-red-500/10"
                        :disabled="!canEditSiteSettings || (!logoPreviewUrl && !selectedLogoFile)"
                        @click="removeSelectedLogo"
                      >
                        <i class="fas fa-trash-alt" />
                        {{ $t('settings.general.removeLogo') }}
                      </button>
                    </div>
                  </div>
                </div>
                <!-- Vertical stack on mobile, row on desktop; touch target 48px for switch -->
                <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                  <BaseSwitch v-model="generalForm.maintenanceMode" :label="$t('settings.general.maintenanceMode')" size="md" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.general.defaultBaseCurrency') }}</label>
                  <BaseCurrencySelect
                    v-model="generalForm.defaultBaseCurrency"
                    :options="currenciesStore.canonicalItems"
                    value-key="code"
                    :placeholder="$t('settings.general.defaultBaseCurrency')"
                    :search-placeholder="$t('common.search')"
                    :empty-text="$t('emptyState.noData')"
                  />
                </div>
                <!-- Desktop: inline submit -->
                <button type="submit" class="btn-luxury min-h-[48px] hidden md:inline-flex" :disabled="!canEditSiteSettings">
                  <i class="fas fa-save" />
                  {{ $t('settings.general.saveChanges') }}
                </button>
              </form>
            </div>

            <!-- Uploads -->
            <div v-else-if="activeTab === 'uploads'" key="uploads" class="p-4 sm:p-6 w-full min-w-0">
              <h2 class="text-lg font-semibold text-gold mb-4 sm:mb-6">{{ $t('settings.tabs.uploads') }}</h2>
              <div class="space-y-4 md:space-y-6 w-full max-w-xl min-w-0">
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.uploads.maxFileSize') }}</label>
                  <select v-model="uploadsForm.maxFileSizeMb" class="input-luxury w-full min-w-0 min-h-[48px]">
                    <option :value="1">1 MB</option>
                    <option :value="2">2 MB</option>
                    <option :value="5">5 MB</option>
                    <option :value="10">10 MB</option>
                    <option :value="20">20 MB</option>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-3">{{ $t('settings.uploads.allowedFormats') }}</label>
                  <div class="flex flex-wrap gap-3 sm:gap-4">
                    <BaseCheckbox v-model="uploadsForm.allowedFormats" value="PNG">{{ $t('settings.uploads.formatPng') }}</BaseCheckbox>
                    <BaseCheckbox v-model="uploadsForm.allowedFormats" value="JPG">{{ $t('settings.uploads.formatJpg') }}</BaseCheckbox>
                    <BaseCheckbox v-model="uploadsForm.allowedFormats" value="SVG">{{ $t('settings.uploads.formatSvg') }}</BaseCheckbox>
                  </div>
                </div>
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.uploads.storageUsage') }}</label>
                  <p class="text-xs md:text-sm text-[var(--text-secondary)] mb-2">
                    {{ $t('settings.uploads.storageUsed', { percent: storageUsedPercent, total: storageTotalGb }) }}
                  </p>
                  <div class="h-2 md:h-3 w-full rounded-full bg-[var(--bg-hover)] overflow-hidden border border-[var(--glass-border)]">
                    <div
                      class="h-full rounded-full transition-all duration-300"
                      :style="{ background: 'linear-gradient(90deg, var(--primary), var(--primary-hover))', width: storageUsedPercent + '%' }"
                    />
                  </div>
                </div>
                <div class="pt-4 border-t" style="border-color: var(--glass-border);">
                  <button
                    type="button"
                    class="btn-luxury min-h-[48px] mb-3"
                    :disabled="!canEditSiteSettings || uploadsSaving"
                    @click="saveUploadsSettings"
                  >
                    <i class="fas fa-save" />
                    {{ uploadsSaving ? $t('common.loading') : $t('settings.general.saveChanges') }}
                  </button>
                  <button
                    type="button"
                    class="btn-luxury-outline border-red-500/50 text-red-400 hover:bg-red-500/10 hover:border-red-500/70 min-h-[48px]"
                    :disabled="!canSeeGlobalSettings || clearingCache"
                    @click="showClearCacheModal = true"
                  >
                    <i class="fas fa-trash-alt" />
                    {{ clearingCache ? $t('common.loading') : $t('settings.uploads.clearTempUploads') }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Fonts -->
            <div v-else-if="activeTab === 'fonts'" key="fonts" class="p-4 sm:p-6 w-full min-w-0">
              <h2 class="text-lg font-semibold text-gold mb-2 sm:mb-3">{{ $t('settings.tabs.fonts') }}</h2>
              <p class="text-sm text-[var(--text-secondary)] mb-4 sm:mb-6 max-w-2xl">{{ $t('settings.fonts.description') }}</p>

              <div class="space-y-6 w-full max-w-3xl min-w-0">
                <div class="rounded-xl border p-4" style="border-color: var(--glass-border); background: var(--bg-input);">
                  <p class="text-xs text-[var(--text-secondary)] mb-3">{{ $t('settings.fonts.uploadLabel') }}</p>
                  <p class="text-xs text-[var(--text-secondary)] mb-3">{{ $t('settings.fonts.uploadHint') }}</p>
                  <input
                    ref="fontFileInputRef"
                    type="file"
                    accept=".ttf,.otf,font/ttf,font/otf"
                    class="hidden"
                    :disabled="!canEditSiteSettings || fontsUploading"
                    @change="onFontFileSelected"
                  >
                  <button
                    type="button"
                    class="btn-luxury-outline min-h-[48px]"
                    :disabled="!canEditSiteSettings || fontsUploading"
                    @click="fontFileInputRef?.click()"
                  >
                    <i class="fas fa-upload" />
                    {{ fontsUploading ? $t('common.loading') : $t('settings.fonts.uploadLabel') }}
                  </button>
                  <p
                    v-if="fontUploadError"
                    class="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-[var(--text-primary)]"
                    role="alert"
                  >
                    <i class="fas fa-circle-exclamation mt-0.5 text-red-400" aria-hidden="true" />
                    <span class="min-w-0">{{ fontUploadError }}</span>
                  </p>
                </div>

                <div v-if="fontsList.length" class="overflow-x-auto rounded-xl border" style="border-color: var(--glass-border);">
                  <table class="min-w-full text-sm text-start">
                    <thead>
                      <tr class="border-b text-[var(--text-secondary)]" style="border-color: var(--glass-border);">
                        <th class="py-3 px-4 font-medium">{{ $t('settings.fonts.tableFile') }}</th>
                        <th class="py-3 px-4 font-medium">{{ $t('settings.fonts.tableDisplay') }}</th>
                        <th v-if="canSeeGlobalSettings" class="py-3 px-4 w-24" />
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="row in fontsList"
                        :key="row.filename"
                        class="border-b border-[var(--glass-border)]/60"
                      >
                        <td class="py-2 px-4 font-mono text-xs break-all">{{ row.filename }}</td>
                        <td class="py-2 px-4">{{ row.display_name || row.filename }}</td>
                        <td v-if="canSeeGlobalSettings" class="py-2 px-4">
                          <button
                            type="button"
                            class="text-red-400 hover:text-red-300 text-xs min-h-[40px]"
                            @click="openDeleteFontModal(row.filename)"
                          >
                            {{ $t('common.delete') }}
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="text-sm text-[var(--text-secondary)]">{{ $t('settings.fonts.noFonts') }}</p>

                <div class="space-y-4 pt-2 border-t" style="border-color: var(--glass-border);">
                  <div>
                    <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.fonts.rtlUiFont') }}</label>
                    <select v-model="fontsForm.rtl" class="input-luxury w-full min-w-0 min-h-[48px]" :disabled="!canEditSiteSettings">
                      <option value="">{{ $t('settings.fonts.defaultSystem') }}</option>
                      <optgroup v-if="fontsGroupedForRtl.both.length" :label="$t('settings.fonts.optgroupPersianDual')">
                        <option v-for="f in fontsGroupedForRtl.both" :key="'rtl-b-' + f.filename" :value="f.filename">{{ f.display_name || f.filename }}</option>
                      </optgroup>
                      <optgroup v-if="fontsGroupedForRtl.ltr.length" :label="$t('settings.fonts.optgroupLatin')">
                        <option v-for="f in fontsGroupedForRtl.ltr" :key="'rtl-l-' + f.filename" :value="f.filename">{{ f.display_name || f.filename }}</option>
                      </optgroup>
                      <optgroup v-if="fontsGroupedForRtl.other.length" :label="$t('settings.fonts.optgroupOther')">
                        <option v-for="f in fontsGroupedForRtl.other" :key="'rtl-o-' + f.filename" :value="f.filename">{{ f.display_name || f.filename }}</option>
                      </optgroup>
                    </select>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.fonts.ltrUiFont') }}</label>
                    <select v-model="fontsForm.ltr" class="input-luxury w-full min-w-0 min-h-[48px]" :disabled="!canEditSiteSettings">
                      <option value="">{{ $t('settings.fonts.defaultSystem') }}</option>
                      <optgroup v-if="fontsGroupedForLtr.ltr.length" :label="$t('settings.fonts.optgroupLatin')">
                        <option v-for="f in fontsGroupedForLtr.ltr" :key="'ltr-l-' + f.filename" :value="f.filename">{{ f.display_name || f.filename }}</option>
                      </optgroup>
                      <optgroup v-if="fontsGroupedForLtr.both.length" :label="$t('settings.fonts.optgroupPersianDual')">
                        <option v-for="f in fontsGroupedForLtr.both" :key="'ltr-b-' + f.filename" :value="f.filename">{{ f.display_name || f.filename }}</option>
                      </optgroup>
                      <optgroup v-if="fontsGroupedForLtr.other.length" :label="$t('settings.fonts.optgroupOther')">
                        <option v-for="f in fontsGroupedForLtr.other" :key="'ltr-o-' + f.filename" :value="f.filename">{{ f.display_name || f.filename }}</option>
                      </optgroup>
                    </select>
                  </div>
                  <button
                    type="button"
                    class="btn-luxury inline-flex w-full sm:w-auto min-h-[48px] items-center justify-center gap-2"
                    :disabled="!canEditSiteSettings || fontsSaving"
                    @click="saveFontsSettings"
                  >
                    <i class="fas fa-save" />
                    {{ fontsSaving ? $t('common.loading') : $t('settings.fonts.saveUiFonts') }}
                  </button>
                </div>

                <p class="text-xs text-[var(--text-secondary)]">{{ $t('settings.fonts.dockerHint') }}</p>
              </div>
            </div>

            <!-- API (prices webhook + public GET URL) -->
            <div v-else-if="activeTab === 'api'" key="api" class="p-4 sm:p-6 w-full min-w-0">
              <h2 class="text-lg font-semibold text-gold mb-4 sm:mb-6">{{ $t('settings.tabs.api') }}</h2>
              <div class="space-y-6 w-full max-w-2xl min-w-0">
                <p class="text-sm text-[var(--text-secondary)]">{{ $t('settings.api.intro') }}</p>
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.api.webhookLabel') }}</label>
                  <input
                    v-model="apiForm.webhookUrl"
                    type="url"
                    class="input-luxury w-full min-w-0 min-h-[48px]"
                    :placeholder="$t('settings.api.webhookPlaceholder')"
                    :disabled="!canEditSiteSettings"
                  >
                  <p class="text-xs mt-2 text-[var(--text-secondary)]">{{ $t('settings.api.webhookHint') }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">{{ $t('settings.api.publicGetLabel') }}</label>
                  <div class="flex flex-col sm:flex-row gap-2 sm:items-center">
                    <code class="flex-1 text-xs sm:text-sm break-all rounded-xl border px-3 py-3 min-h-[48px] flex items-center" style="border-color: var(--glass-border); background: var(--bg-input);">{{ publicPricesUrl }}</code>
                    <button type="button" class="btn-luxury-outline shrink-0 min-h-[48px] px-4" @click="copyPublicPricesUrl">
                      <i class="fas fa-copy me-2" />
                      {{ copyPublicLabel }}
                    </button>
                  </div>
                  <p class="text-xs mt-2 text-[var(--text-secondary)]">{{ $t('settings.api.publicGetHint') }}</p>
                </div>
                <button
                  type="button"
                  class="btn-luxury inline-flex w-full sm:w-auto min-h-[48px] items-center justify-center gap-2"
                  :disabled="!canEditSiteSettings || apiSaving"
                  @click="saveApiSettings"
                >
                  <i class="fas fa-save" />
                  {{ apiSaving ? $t('common.loading') : $t('settings.api.save') }}
                </button>
              </div>
            </div>

            <!-- Categories -->
            <div v-else-if="activeTab === 'categories'" key="categories" class="p-4 sm:p-6 w-full min-w-0">
              <CategoriesView embedded />
            </div>

            <!-- Logs -->
            <div v-else-if="activeTab === 'logs' && canSeeGlobalSettings" key="logs" class="p-4 sm:p-6 w-full min-w-0 overflow-x-auto overflow-y-hidden">
              <LogsView embedded />
            </div>

            <!-- Install App -->
            <div v-else-if="activeTab === 'install-app'" key="install-app" class="p-4 sm:p-6 w-full min-w-0">
              <h2 class="text-lg font-semibold text-gold mb-4 sm:mb-6">{{ $t('settings.tabs.installApp') }}</h2>
              <div class="space-y-6 w-full max-w-xl min-w-0">
                <p class="text-sm text-[var(--text-secondary)]">
                  {{ $t('settings.installAppContent.description') }}
                </p>
                <!-- Already in standalone (installed) -->
                <div
                  v-if="isStandalone"
                  class="flex items-center gap-3 p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10"
                >
                  <i class="fas fa-check-circle text-emerald-400 text-xl shrink-0" />
                  <span class="text-sm text-[var(--text-primary)]">{{ $t('settings.installAppContent.alreadyInstalled') }}</span>
                </div>
                <!-- Install button (Android/Chrome when beforeinstallprompt is available) -->
                <div v-else-if="deferredPrompt" class="flex flex-wrap gap-3">
                  <button
                    type="button"
                    class="btn-luxury flex items-center gap-2 min-h-[48px] px-6"
                    :disabled="installing"
                    @click="triggerInstall"
                  >
                    <i class="fas fa-download" />
                    {{ installing ? $t('common.loading') : $t('settings.installAppContent.installButton') }}
                  </button>
                </div>
                <!-- iOS instructions -->
                <div
                  v-if="isIos && !isStandalone"
                  class="rounded-xl border p-4 space-y-2"
                  style="border-color: var(--border-card); background: var(--bg-input);"
                >
                  <p class="text-sm font-medium text-[var(--text-primary)] flex items-center gap-2">
                    <i class="fas fa-apple-alt text-gold" />
                    {{ $t('settings.installAppContent.iosInstructions') }}
                  </p>
                  <ol class="mt-2 list-decimal space-y-1 ps-5 text-xs text-[var(--text-secondary)]">
                    <li v-for="step in iosInstallSteps" :key="step">{{ step }}</li>
                  </ol>
                </div>
                <!-- Desktop: show install hint for mobile -->
                <div
                  v-if="!deferredPrompt && !isIos && !isStandalone"
                  class="text-sm text-[var(--text-secondary)] rounded-xl border p-4"
                  style="border-color: var(--border-card);"
                >
                  {{ $t('settings.installAppContent.title') }} — {{ $t('settings.installAppContent.description') }}
                  <p class="mt-2 text-xs opacity-90">{{ $t('pwa.installDesc') }}</p>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- Mobile: Sticky Save bar (General + Fonts) -->
    <div
      v-show="activeTab === 'general'"
      class="fixed bottom-0 left-0 right-0 z-30 p-4 md:hidden border-t transition-colors duration-300"
      style="background: var(--bg-base); border-color: var(--glass-border); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);"
    >
      <button
        type="button"
        class="btn-luxury w-full min-h-[48px] flex items-center justify-center gap-2"
        :disabled="!canEditSiteSettings"
        @click="saveGeneral"
      >
        <i class="fas fa-save" />
        {{ $t('settings.general.saveChanges') }}
      </button>
    </div>
    <div
      v-show="activeTab === 'fonts'"
      class="fixed bottom-0 left-0 right-0 z-30 p-4 md:hidden border-t transition-colors duration-300"
      style="background: var(--bg-base); border-color: var(--glass-border); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);"
    >
      <button
        type="button"
        class="btn-luxury w-full min-h-[48px] flex items-center justify-center gap-2"
        :disabled="!canEditSiteSettings || fontsSaving"
        @click="saveFontsSettings"
      >
        <i class="fas fa-save" />
        {{ fontsSaving ? $t('common.loading') : $t('settings.fonts.saveUiFonts') }}
      </button>
    </div>
    <div
      v-show="activeTab === 'api'"
      class="fixed bottom-0 left-0 right-0 z-30 p-4 md:hidden border-t transition-colors duration-300"
      style="background: var(--bg-base); border-color: var(--glass-border); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);"
    >
      <button
        type="button"
        class="btn-luxury w-full min-h-[48px] flex items-center justify-center gap-2"
        :disabled="!canEditSiteSettings || apiSaving"
        @click="saveApiSettings"
      >
        <i class="fas fa-save" />
        {{ apiSaving ? $t('common.loading') : $t('settings.api.save') }}
      </button>
    </div>

    <!-- Clear cache confirmation modal -->
    <BaseModal
      v-model="showClearCacheModal"
      :title="$t('common.confirm')"
      :aria-label="$t('settings.confirmClearCache')"
    >
      <p class="text-[var(--text-secondary)] mb-6">{{ $t('settings.uploads.clearCacheConfirm') }}</p>
      <div class="flex gap-3 justify-end">
        <button type="button" class="btn-luxury-outline" @click="showClearCacheModal = false">
          {{ $t('common.cancel') }}
        </button>
        <button
          type="button"
          class="btn-luxury-outline border-red-500/50 text-red-400 hover:bg-red-500/10"
          @click="clearCache"
        >
          {{ $t('common.confirm') }}
        </button>
      </div>
    </BaseModal>

    <!-- Delete font confirmation -->
    <BaseModal
      v-model="showDeleteFontModal"
      :title="$t('common.confirm')"
      :aria-label="$t('settings.confirmDeleteFont')"
    >
      <p class="text-[var(--text-secondary)] mb-6">{{ $t('settings.fonts.deleteConfirm', { name: fontPendingDelete || '' }) }}</p>
      <div class="flex gap-3 justify-end">
        <button type="button" class="btn-luxury-outline" @click="showDeleteFontModal = false">
          {{ $t('common.cancel') }}
        </button>
        <button
          type="button"
          class="btn-luxury-outline border-red-500/50 text-red-400 hover:bg-red-500/10"
          @click="confirmDeleteFont"
        >
          {{ $t('common.delete') }}
        </button>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { useI18n } from 'vue-i18n'
import { useSiteSettingsStore } from '@/stores/siteSettings'
import { useCurrenciesStore } from '@/stores/currencies'
import { useAuthStore } from '@/stores/auth'
import { settingsApi, templateEditorApi, getApiErrorDetails } from '@/services/api'
import LogsView from './LogsView.vue'
import CategoriesView from '@/views/categories/CategoriesView.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCheckbox from '@/components/ui/BaseCheckbox.vue'
import BaseCurrencySelect from '@/components/ui/BaseCurrencySelect.vue'
import BaseSwitch from '@/components/ui/BaseSwitch.vue'

const route = useRoute()
const toast = useToast()
const { t } = useI18n()
const siteSettings = useSiteSettingsStore()
const currenciesStore = useCurrenciesStore()
const auth = useAuthStore()

const allTabs = [
  { id: 'general', labelKey: 'settings.tabs.general', icon: 'fas fa-sliders-h' },
  { id: 'categories', labelKey: 'settings.tabs.categories', icon: 'fas fa-tags' },
  { id: 'uploads', labelKey: 'settings.tabs.uploads', icon: 'fas fa-cloud-upload-alt' },
  { id: 'fonts', labelKey: 'settings.tabs.fonts', icon: 'fas fa-font' },
  { id: 'api', labelKey: 'settings.tabs.api', icon: 'fas fa-code' },
  { id: 'logs', labelKey: 'settings.tabs.logs', icon: 'fas fa-list', adminOnly: true },
  { id: 'install-app', labelKey: 'settings.tabs.installApp', icon: 'fas fa-mobile-alt' },
]

const tabs = computed(() => allTabs.filter((t) => !t.adminOnly || canSeeGlobalSettings.value))

const activeTab = ref('general')
const showClearCacheModal = ref(false)
let deferredInstallPrompt = null
const installing = ref(false)
const uploadsSaving = ref(false)
const clearingCache = ref(false)
const logoInputRef = ref(null)
const selectedLogoFile = ref(null)
const logoPreviewUrl = ref('')
const removeLogo = ref(false)

const isStandalone = computed(() => {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true ||
    document.referrer.includes('android-app://')
})

const isIos = computed(() => {
  if (typeof navigator === 'undefined') return false
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
})

const deferredPrompt = ref(null)
// Branding, uploads, fonts and the webhook belong to whoever owns the
// workspace; bots, channels and the activity log stay global (IsSuperAdmin),
// so the Logs tab is dropped rather than shown and 403ing on load.
const canEditSiteSettings = computed(() => auth.canAccessSettings)
const canSeeGlobalSettings = computed(() => auth.canAccessSettingsAdmin)

// General form: platform name from store, rest local
const generalForm = reactive({
  platformName: '',
  maintenanceMode: false,
  defaultBaseCurrency: 'USD',
})

// Uploads: managed by backend
const uploadsForm = reactive({
  maxFileSizeMb: 5,
  allowedFormats: ['PNG', 'JPG'],
})
const storageUsedPercent = ref(0)
const storageTotalGb = ref('10 GB')


const fontsList = ref([])
const fontsForm = reactive({ rtl: '', ltr: '' })
const fontsUploading = ref(false)
const fontUploadError = ref('')
const fontsSaving = ref(false)

const apiForm = reactive({ webhookUrl: '' })
const apiSaving = ref(false)
const copyPublicState = ref(false)
const publicPricesUrl = computed(() => {
  if (typeof window === 'undefined') return '/api/public/prices/'
  return `${window.location.origin}/api/public/prices/`
})
const copyPublicLabel = computed(() =>
  copyPublicState.value ? t('settings.api.copied') : t('settings.api.copyLink'),
)
const fontFileInputRef = ref(null)
const showDeleteFontModal = ref(false)
const fontPendingDelete = ref('')

function fontScriptKey(f) {
  const s = f?.script
  if (s === 'ltr' || s === 'both') return s
  return 'other'
}

const fontsGroupedForRtl = computed(() => {
  const both = []
  const ltr = []
  const other = []
  for (const f of fontsList.value) {
    const k = fontScriptKey(f)
    if (k === 'both') both.push(f)
    else if (k === 'ltr') ltr.push(f)
    else other.push(f)
  }
  return { both, ltr, other }
})

const fontsGroupedForLtr = computed(() => {
  const ltr = []
  const both = []
  const other = []
  for (const f of fontsList.value) {
    const k = fontScriptKey(f)
    if (k === 'ltr') ltr.push(f)
    else if (k === 'both') both.push(f)
    else other.push(f)
  }
  return { ltr, both, other }
})

const iosInstallSteps = computed(() =>
  [1, 2, 3, 4].map((step) => t(`settings.iosInstall.step${step}`))
)

function setTab(id) {
  activeTab.value = id
  if (id === 'api') {
    syncApiFormFromStore()
  }
  const hash = '#' + id
  if (typeof window !== 'undefined' && window.history.replaceState) {
    window.history.replaceState(null, '', route.path + hash)
  }
}

function initFromHash() {
  const hash = window.location.hash?.slice(1)
  if (hash && tabs.value.some(t => t.id === hash)) {
    activeTab.value = hash
  }
}

async function saveGeneral() {
  if (!canEditSiteSettings.value) {
    toast.error(t('errors.forbidden'))
    return
  }
  try {
    let payload = null
    if (selectedLogoFile.value) {
      const formData = new FormData()
      formData.append('site_name', generalForm.platformName || '')
      formData.append('base_currency_code', generalForm.defaultBaseCurrency || 'USD')
      formData.append('logo', selectedLogoFile.value)
      payload = formData
    } else {
      payload = {
        site_name: generalForm.platformName,
        base_currency_code: generalForm.defaultBaseCurrency,
      }
      if (removeLogo.value) {
        payload.logo = null
      }
    }
    const { data } = await settingsApi.updateSite(payload)
    siteSettings.applySettings(data)
    selectedLogoFile.value = null
    removeLogo.value = false
    setLogoPreviewFromSettings()
    toast.success(t('toast.saveSuccess'))
  } catch {
    toast.error(t('toast.serverError'))
  }
}

function openLogoPicker() {
  logoInputRef.value?.click()
}

function clearLogoPreviewObjectUrl() {
  if (logoPreviewUrl.value && logoPreviewUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(logoPreviewUrl.value)
  }
}

function setLogoPreviewFromSettings() {
  clearLogoPreviewObjectUrl()
  const logo = siteSettings.settings?.logo
  logoPreviewUrl.value = typeof logo === 'string' ? logo : ''
}

function onLogoFileChange(event) {
  const file = event.target?.files?.[0] ?? null
  if (!file) return
  clearLogoPreviewObjectUrl()
  selectedLogoFile.value = file
  removeLogo.value = false
  logoPreviewUrl.value = URL.createObjectURL(file)
}

function removeSelectedLogo() {
  clearLogoPreviewObjectUrl()
  selectedLogoFile.value = null
  removeLogo.value = true
  logoPreviewUrl.value = ''
  if (logoInputRef.value) {
    logoInputRef.value.value = ''
  }
}

async function loadUploadSettings() {
  try {
    const { data } = await settingsApi.uploads()
    uploadsForm.maxFileSizeMb = Number(data?.max_file_size_mb ?? 5)
    uploadsForm.allowedFormats = Array.isArray(data?.allowed_formats) ? data.allowed_formats : ['PNG', 'JPG']
    storageUsedPercent.value = Number(data?.storage?.used_percent ?? 0)
    storageTotalGb.value = data?.storage?.total_human ?? '10 GB'
  } catch {
    // Keep safe defaults when endpoint is unavailable.
  }
}

async function saveUploadsSettings() {
  if (!canEditSiteSettings.value) {
    toast.error(t('errors.forbidden'))
    return
  }
  uploadsSaving.value = true
  try {
    const { data } = await settingsApi.updateUploads({
      max_file_size_mb: uploadsForm.maxFileSizeMb,
      allowed_formats: uploadsForm.allowedFormats,
    })
    uploadsForm.maxFileSizeMb = Number(data?.max_file_size_mb ?? uploadsForm.maxFileSizeMb)
    uploadsForm.allowedFormats = Array.isArray(data?.allowed_formats) ? data.allowed_formats : uploadsForm.allowedFormats
    storageUsedPercent.value = Number(data?.storage?.used_percent ?? storageUsedPercent.value)
    storageTotalGb.value = data?.storage?.total_human ?? storageTotalGb.value
    toast.success(t('toast.saveSuccess'))
  } catch {
    toast.error(t('toast.serverError'))
  } finally {
    uploadsSaving.value = false
  }
}

function syncFontsFormFromStore() {
  fontsForm.rtl = siteSettings.settings?.ui_font_filename_rtl || ''
  fontsForm.ltr = siteSettings.settings?.ui_font_filename_ltr || ''
}

function syncApiFormFromStore() {
  apiForm.webhookUrl = siteSettings.settings?.prices_webhook_url ?? ''
}

async function saveApiSettings() {
  if (!canEditSiteSettings.value) {
    toast.error(t('errors.forbidden'))
    return
  }
  apiSaving.value = true
  try {
    const { data } = await settingsApi.updateSite({ prices_webhook_url: apiForm.webhookUrl.trim() })
    siteSettings.applySettings(data)
    syncApiFormFromStore()
    toast.success(t('toast.saveSuccess'))
  } catch {
    toast.error(t('toast.serverError'))
  } finally {
    apiSaving.value = false
  }
}

async function copyPublicPricesUrl() {
  try {
    await navigator.clipboard.writeText(publicPricesUrl.value)
    copyPublicState.value = true
    setTimeout(() => {
      copyPublicState.value = false
    }, 2000)
  } catch {
    toast.error(t('toast.serverError'))
  }
}

async function loadFontsList() {
  try {
    const { data } = await templateEditorApi.fonts()
    fontsList.value = Array.isArray(data) ? data : []
    await siteSettings.refreshUiTypography(siteSettings.settings)
  } catch {
    fontsList.value = []
  }
}

async function saveFontsSettings() {
  if (!canEditSiteSettings.value) {
    toast.error(t('errors.forbidden'))
    return
  }
  fontsSaving.value = true
  try {
    const { data } = await settingsApi.updateSite({
      ui_font_filename_rtl: fontsForm.rtl || '',
      ui_font_filename_ltr: fontsForm.ltr || '',
    })
    siteSettings.applySettings(data)
    syncFontsFormFromStore()
    toast.success(t('toast.saveSuccess'))
  } catch (e) {
    const msg = e?.response?.data?.ui_font_filename_rtl?.[0] ||
      e?.response?.data?.ui_font_filename_ltr?.[0] ||
      e?.response?.data?.detail
    toast.error(msg || t('toast.serverError'))
  } finally {
    fontsSaving.value = false
  }
}

async function onFontFileSelected(event) {
  const file = event.target?.files?.[0]
  if (!file || !canEditSiteSettings.value) return
  fontsUploading.value = true
  fontUploadError.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    await templateEditorApi.uploadFont(formData)
    toast.success(t('settings.fonts.uploadSuccess'))
    await loadFontsList()
  } catch (e) {
    // The API says which font it could not read and why; that reason is the
    // whole point of the message, so it stays on the page.
    fontUploadError.value = e?.response?.data?.detail || getApiErrorDetails(e).message
  } finally {
    event.target.value = ''
    fontsUploading.value = false
  }
}

function openDeleteFontModal(filename) {
  fontPendingDelete.value = filename
  showDeleteFontModal.value = true
}

async function confirmDeleteFont() {
  const name = fontPendingDelete.value
  if (!name || !canSeeGlobalSettings.value) {
    showDeleteFontModal.value = false
    return
  }
  try {
    await templateEditorApi.deleteFont(name)
    showDeleteFontModal.value = false
    fontPendingDelete.value = ''
    await loadFontsList()
    syncFontsFormFromStore()
    toast.success(t('toast.deleteSuccess'))
  } catch (e) {
    const detail = e?.response?.data?.detail
    if (detail && String(detail).toLowerCase().includes('ui')) {
      toast.error(t('settings.fonts.deleteBlocked'))
    } else {
      toast.error(typeof detail === 'string' ? detail : t('toast.serverError'))
    }
  }
}

async function clearCache() {
  if (!canSeeGlobalSettings.value) {
    toast.error(t('errors.forbidden'))
    return
  }
  clearingCache.value = true
  try {
    await settingsApi.clearTempUploads()
    showClearCacheModal.value = false
    await loadUploadSettings()
    toast.success(t('toast.cacheCleared'))
  } catch {
    toast.error(t('toast.serverError'))
  } finally {
    clearingCache.value = false
  }
}

function handleBeforeInstall(e) {
  // Keep the browser's native banner behavior if our custom install UI is not needed.
  const dismissed =
    localStorage.getItem('mrexchange-pwa-dismissed') || localStorage.getItem('smartexchange-pwa-dismissed')
  if (dismissed) return
  e.preventDefault()
  deferredInstallPrompt = e
  deferredPrompt.value = e
}

async function triggerInstall() {
  if (!deferredInstallPrompt) return
  installing.value = true
  try {
    deferredInstallPrompt.prompt()
    const { outcome } = await deferredInstallPrompt.userChoice
    deferredInstallPrompt = null
    deferredPrompt.value = null
    if (outcome === 'accepted') {
      toast.success(t('pwa.installTitle'))
    }
  } finally {
    installing.value = false
  }
}

onMounted(() => {
  window.addEventListener('beforeinstallprompt', handleBeforeInstall)
  initFromHash()
  loadUploadSettings()
  currenciesStore.fetch()
  syncFontsFormFromStore()
  if (siteSettings.settings?.site_name != null) {
    generalForm.platformName = siteSettings.settings.site_name
    generalForm.defaultBaseCurrency = siteSettings.settings?.base_currency_code ?? 'USD'
    setLogoPreviewFromSettings()
    syncApiFormFromStore()
  } else {
    siteSettings.fetch().then(() => {
      generalForm.platformName = siteSettings.settings?.site_name ?? ''
      generalForm.defaultBaseCurrency = siteSettings.settings?.base_currency_code ?? 'USD'
      setLogoPreviewFromSettings()
      syncFontsFormFromStore()
      syncApiFormFromStore()
    })
  }
  if (activeTab.value === 'fonts') {
    loadFontsList()
  }
  syncApiFormFromStore()
})

let fontsPreviewTimer = null
watch(activeTab, (id, prev) => {
  if (id === 'fonts') {
    loadFontsList()
  }
  if (prev === 'fonts' && id !== 'fonts') {
    siteSettings.refreshUiTypography(siteSettings.settings).catch(() => {})
  }
})

watch(
  () => [fontsForm.rtl, fontsForm.ltr, activeTab.value],
  () => {
    if (activeTab.value !== 'fonts') return
    if (fontsPreviewTimer) clearTimeout(fontsPreviewTimer)
    fontsPreviewTimer = setTimeout(() => {
      siteSettings
        .previewUiTypography({
          ui_font_filename_rtl: fontsForm.rtl,
          ui_font_filename_ltr: fontsForm.ltr,
        })
        .catch(() => {})
    }, 200)
  },
)

onUnmounted(() => {
  if (fontsPreviewTimer) clearTimeout(fontsPreviewTimer)
  window.removeEventListener('beforeinstallprompt', handleBeforeInstall)
  clearLogoPreviewObjectUrl()
})

watch(() => route.path, () => initFromHash())
</script>

<style scoped>
/* Hide scrollbar on horizontal tab strip (mobile) */
.settings-tabs-mobile .overflow-x-auto {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.settings-tabs-mobile .overflow-x-auto::-webkit-scrollbar {
  display: none;
}
</style>
