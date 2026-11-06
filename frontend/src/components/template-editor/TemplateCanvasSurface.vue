<template>
  <div
    :id="rootId"
    class="relative overflow-hidden bg-white"
    :class="rootClass"
    :style="{
      width: canvasW + 'px',
      height: canvasH + 'px',
      backgroundColor: backgroundColor,
    }"
  >
    <img
      v-if="imageUrl"
      ref="baseImageEl"
      :src="imageUrl"
      alt=""
      class="pointer-events-none absolute inset-0 h-full w-full object-contain opacity-100"
      draggable="false"
      @load="emit('background-load')"
      @error="emit('background-load')"
    />
    <div
      v-for="item in sortedWidgets"
      :key="item.id"
      class="absolute box-border will-change-transform"
      :style="widgetDomStyle(item)"
      :data-wid="item.id"
    >
      <div :class="widgetInnerChromeClass(item.type)">
        <WidgetPreviewHost :widget="item" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import WidgetPreviewHost from '@/components/template-editor/player/widgets/WidgetPreviewHost.vue'
import { widgetDomStyle, widgetInnerChromeClass } from '@/pages/templates/templateEditorCanvasUtils.js'

const props = defineProps({
  widgets: { type: Array, default: () => [] },
  canvasW: { type: Number, required: true },
  canvasH: { type: Number, required: true },
  backgroundColor: { type: String, default: '#ffffff' },
  imageUrl: { type: String, default: '' },
  rootId: { type: String, default: 'template-canvas-root' },
  rootClass: { type: String, default: '' },
})

const emit = defineEmits(['background-load'])

const baseImageEl = ref(null)

const sortedWidgets = computed(() =>
  [...props.widgets]
    .filter((w) => w.visible !== false)
    .sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0)),
)

defineExpose({ baseImageEl })
</script>
