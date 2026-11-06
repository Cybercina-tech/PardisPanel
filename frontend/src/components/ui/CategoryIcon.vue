<template>
  <img
    :src="iconSrc"
    :alt="`${categoryName || 'category'} icon`"
    :class="['object-contain', sizeClass]"
  />
</template>

<script setup>
import { computed } from 'vue'
import { getCategoryIcon } from '@/utils/categoryIcons'

const props = defineProps({
  categoryName: {
    type: String,
    default: '',
  },
  sizeClass: {
    type: String,
    default: 'h-4 w-4',
  },
})

const iconSrc = computed(() => getCategoryIcon(props.categoryName))
</script>

