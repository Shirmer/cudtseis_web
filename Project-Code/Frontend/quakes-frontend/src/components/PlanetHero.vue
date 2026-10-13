<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { PlanetSceneHandle } from '../planet/planet-scene'

const hostEl = ref<HTMLElement | null>(null)
const ready = ref(false)
const failed = ref(false)

let scene: PlanetSceneHandle | null = null
let intersection: IntersectionObserver | null = null
let resizeObserver: ResizeObserver | null = null
let heroVisible = true
let booted = false

const POSTER = `${import.meta.env.BASE_URL}media/planet/planet-poster.jpg`

function supports3d(): boolean {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
  const connection = (navigator as { connection?: { saveData?: boolean } }).connection
  if (connection?.saveData) return false
  try {
    const probe = document.createElement('canvas')
    return !!(probe.getContext('webgl2') || probe.getContext('webgl'))
  } catch {
    return false
  }
}

function applyOffset() {
  if (!scene || !hostEl.value) return
  const aspect = hostEl.value.clientWidth / Math.max(hostEl.value.clientHeight, 1)
  if (aspect < 0.95) {
    scene.setOffset(1.2, -5.2, 0.8)
  } else if (aspect < 1.45) {
    scene.setOffset(4.8, 1.6, 0.86)
  } else {
    scene.setOffset(7.2, 0.2, 1)
  }
}

function onVisibility() {
  scene?.setPaused(!heroVisible || document.hidden)
}

async function boot() {
  if (booted || !hostEl.value || !supports3d()) return
  booted = true
  try {
    const { createPlanetScene } = await import('../planet/planet-scene')
    if (!hostEl.value) return
    scene = createPlanetScene(hostEl.value, {
      onReady: () => { ready.value = true },
      onError: () => { failed.value = true }
    })
    applyOffset()
    resizeObserver = new ResizeObserver(applyOffset)
    resizeObserver.observe(hostEl.value)
    intersection = new IntersectionObserver((entries) => {
      heroVisible = entries.some((entry) => entry.isIntersecting)
      onVisibility()
    }, { threshold: 0.01 })
    intersection.observe(hostEl.value)
    document.addEventListener('visibilitychange', onVisibility)
  } catch {
    failed.value = true
  }
}

onMounted(boot)

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisibility)
  intersection?.disconnect()
  resizeObserver?.disconnect()
  scene?.dispose()
  scene = null
})
</script>

<template>
  <div ref="hostEl" class="planet-stage" :class="{ 'is-ready': ready, 'is-failed': failed }">
    <img class="planet-poster" :src="POSTER" alt="" aria-hidden="true" />
  </div>
</template>

<style scoped>
.planet-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #02040a;
}

.planet-poster {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity 900ms ease;
}

.planet-stage.is-ready .planet-poster {
  opacity: 0;
}

.planet-stage :deep(canvas) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 900ms ease;
  cursor: grab;
}

.planet-stage :deep(canvas:active) {
  cursor: grabbing;
}

.planet-stage.is-ready :deep(canvas) {
  opacity: 1;
}
</style>
