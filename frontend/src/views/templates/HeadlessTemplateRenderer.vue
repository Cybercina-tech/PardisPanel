<template>
  <div class="headless-render-root overflow-hidden bg-black">
    <div v-if="loadError" class="p-4 text-center text-red-500">{{ loadError }}</div>
    <div v-else-if="loading" class="p-4 text-center text-white">{{ $t('common.loading') }}</div>
    <div
      v-else
      class="inline-block"
      :style="{ width: canvasW + 'px', height: canvasH + 'px' }"
    >
      <TemplateCanvasSurface
        :widgets="widgets"
        :canvas-w="canvasW"
        :canvas-h="canvasH"
        :background-color="backgroundColor"
        :image-url="imageUrl"
        root-id="template-canvas-root"
        @background-load="onBackgroundLoad"
      />
      <div v-if="isRenderReady" id="render-ready" aria-hidden="true" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import TemplateCanvasSurface from '@/components/template-editor/TemplateCanvasSurface.vue'
import { provideTemplateEditor } from '@/pages/templates/templateEditorInjectionKey.js'
import { injectTemplateEditorFontFaces } from '@/pages/templates/templateEditorFonts.js'
import {
  parseWidgetsFromConfigJson,
  buildPriceBindingMapFromContext,
  normalizeTemplateImageUrl,
} from '@/pages/templates/templateEditorCanvasUtils.js'

const route = useRoute()
const { t } = useI18n()

const loading = ref(true)
const loadError = ref('')
const isRenderReady = ref(false)
const canvasW = ref(1080)
const canvasH = ref(1080)
const backgroundColor = ref('#ffffff')
const imageUrl = ref('')
const widgets = ref([])
const priceBindingPreviewMap = ref({})
const template = ref(null)

let backgroundLoaded = false
let fontsLoaded = false
let contextLoaded = false

function onBackgroundLoad() {
  backgroundLoaded = true
  tryMarkReady()
}

async function tryMarkReady() {
  if (!contextLoaded || !fontsLoaded) return
  if (imageUrl.value && !backgroundLoaded) return
  await nextTick()
  try {
    if (document.fonts?.ready) {
      await document.fonts.ready
    }
  } catch {
    /* ignore */
  }
  await nextTick()
  isRenderReady.value = true
}

provideTemplateEditor({
  widgets,
  selectedId: ref(null),
  selectedWidget: ref(null),
  canvasWidth: canvasW,
  canvasHeight: canvasH,
  addWidget: () => {},
  openBackgroundPicker: () => {},
  deleteWidget: () => {},
  selectWidget: () => {},
  refitSelectedWidget: () => {},
  template,
  priceBindingPreviewMap,
  categoryPriceTypes: ref([]),
  backgroundColor,
  saveState: ref('saved'),
  backgroundImageContentRect: ref(null),
  alignSelectedToBackgroundEdge: () => {},
})

onMounted(async () => {
  const token = route.query.token
  if (!token || typeof token !== 'string') {
    loadError.value = t('templateRenderer.missingToken')
    loading.value = false
    return
  }

  try {
    const { data } = await axios.get('/api/template-editor/headless-render/context/', {
      params: { token },
    })

    const ctx = data || {}
    template.value = { id: ctx.template_id, category: ctx.category_id }
    canvasW.value = Number(ctx.canvas_width) || 1080
    canvasH.value = Number(ctx.canvas_height) || 1080
    backgroundColor.value = ctx.background_color || ctx.backgroundColor || '#ffffff'
    imageUrl.value = normalizeTemplateImageUrl(ctx.image_url || '')

    const widgetList = Array.isArray(ctx.widgets) ? ctx.widgets : []
    if (widgetList.length && typeof widgetList[0]?.x === 'number') {
      widgets.value = widgetList.map((w) => ({
        ...w,
        id: String(w.id),
        style: w.style && typeof w.style === 'object' ? { ...w.style } : {},
      }))
    } else {
      widgets.value = parseWidgetsFromConfigJson({ widgets: widgetList }, canvasW.value, canvasH.value)
    }

    priceBindingPreviewMap.value = buildPriceBindingMapFromContext(ctx.price_binding_map || {})

    const fonts = Array.isArray(ctx.fonts) ? ctx.fonts : []
    injectTemplateEditorFontFaces(fonts)
    fontsLoaded = true

    if (!imageUrl.value) {
      backgroundLoaded = true
    }

    contextLoaded = true
    loading.value = false
    await tryMarkReady()
  } catch (e) {
    loadError.value = e?.response?.data?.message || e?.response?.data?.detail || e?.message || t('templateRenderer.loadFailed')
    loading.value = false
  }
})
</script>

<style scoped>
.headless-render-root {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  min-width: 100vw;
}

#render-ready {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
</style>
