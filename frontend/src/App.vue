<template>
  <div>
    <router-view v-slot="{ Component }">
      <transition name="slide-fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <CommandPalette />
    <PwaInstallPrompt />
  </div>
</template>

<script setup>
import CommandPalette from '@/components/ui/CommandPalette.vue'
import PwaInstallPrompt from '@/components/ui/PwaInstallPrompt.vue'
</script>

<style scoped>
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease-in-out;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(12px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
</style>
