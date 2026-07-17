<template>
  <div class="map-shell">
    <div ref="mapEl" class="map-container"></div>
    <div v-if="mapStatus === 'loading' || mapStatus === 'error'" class="map-compliance-notice" :class="mapStatus" role="status">
      <strong>{{ mapStatus === 'loading' ? '正在加载全球自然影像' : '自然影像暂时不可用' }}</strong>
      <span v-if="mapStatus === 'error'">当前已切换到无国界经纬网，请检查网络后刷新。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {
  addDomesticBaseMap,
  domesticMapAttribution,
  type DomesticMapStatus,
} from '../config/domesticMap'
import { localizedPlaceName, type EarthquakeEvent } from '../services/earthquakes'

const props = defineProps<{ events: EarthquakeEvent[] }>()

const mapEl = ref<HTMLDivElement | null>(null)
const mapStatus = ref<DomesticMapStatus>('loading')
let map: L.Map | null = null
let layerGroup: L.LayerGroup | null = null
let renderer: L.Canvas | null = null
let renderFrame: number | null = null
let attributionControl: L.Control.Attribution | null = null
let currentAttribution = ''
const markers = new Map<string, L.CircleMarker>()

function updateMapStatus(status: DomesticMapStatus) {
  mapStatus.value = status
  if (!attributionControl) return
  if (currentAttribution) attributionControl.removeAttribution(currentAttribution)
  currentAttribution = domesticMapAttribution(status)
  attributionControl.addAttribution(currentAttribution)
}

function colorForMagnitude(magnitude: number) {
  if (magnitude >= 6) return '#c9312f'
  if (magnitude >= 5) return '#dc673c'
  if (magnitude >= 4) return '#c99a2e'
  return '#21877d'
}

function markerRadius(magnitude: number) {
  return Math.max(4.5, Math.min(17, 3.5 + magnitude * 1.65))
}

function popupContent(event: EarthquakeEvent) {
  const root = document.createElement('div')
  root.className = 'history-popup'
  const header = document.createElement('div')
  header.className = 'history-popup-head'
  const magnitude = document.createElement('strong')
  magnitude.textContent = `M ${event.mag.toFixed(1)}`
  magnitude.style.color = colorForMagnitude(event.mag)
  const time = document.createElement('span')
  time.textContent = new Date(event.time).toISOString().replace('T', ' ').slice(0, 19)
  header.append(magnitude, time)

  const place = document.createElement('p')
  place.textContent = localizedPlaceName(event.place, 'zh') || '未知区域'
  const meta = document.createElement('small')
  meta.textContent = `Depth ${event.depth_km === null ? 'N/A' : `${event.depth_km.toFixed(1)} km`} · ${event.lat.toFixed(4)}, ${event.lon.toFixed(4)}`
  root.append(header, place, meta)
  return root
}

function fitEvents() {
  if (!map || !props.events.length) return
  if (props.events.length === 1) {
    map.setView([props.events[0].lat, props.events[0].lon], 7)
    return
  }
  const bounds = L.latLngBounds(props.events.map((event) => L.latLng(event.lat, event.lon)))
  map.fitBounds(bounds, { padding: [36, 36], maxZoom: 7, animate: false })
}

function syncMarkers(shouldFit = true) {
  renderFrame = null
  if (!map || !layerGroup) return

  const nextIds = new Set(props.events.map((event) => event.id))
  for (const [id, marker] of markers) {
    if (!nextIds.has(id)) {
      layerGroup.removeLayer(marker)
      markers.delete(id)
    }
  }

  for (const event of props.events) {
    const options: L.CircleMarkerOptions = {
      renderer: renderer ?? undefined,
      radius: markerRadius(event.mag),
      color: '#ffffff',
      weight: 1.3,
      fillColor: colorForMagnitude(event.mag),
      fillOpacity: 0.9,
    }
    const existing = markers.get(event.id)
    if (existing) {
      existing.setLatLng([event.lat, event.lon])
      existing.setRadius(markerRadius(event.mag))
      existing.setStyle(options)
      existing.setPopupContent(popupContent(event))
      continue
    }

    const marker = L.circleMarker([event.lat, event.lon], options)
      .bindPopup(popupContent(event), { minWidth: 230, closeButton: true })
      .addTo(layerGroup)
    markers.set(event.id, marker)
  }

  if (shouldFit) fitEvents()
}

function scheduleSync(shouldFit = true) {
  if (renderFrame !== null) cancelAnimationFrame(renderFrame)
  renderFrame = requestAnimationFrame(() => syncMarkers(shouldFit))
}

onMounted(() => {
  if (!mapEl.value) return
  renderer = L.canvas({ padding: 0.5, tolerance: 6 })
  map = L.map(mapEl.value, {
    preferCanvas: true,
    renderer,
    minZoom: 2,
    maxZoom: 16,
    zoomControl: false,
    attributionControl: false,
    worldCopyJump: true,
    maxBounds: [[-85, -180], [85, 180]],
    maxBoundsViscosity: 0.85,
  }).setView([25, 105], 2)

  addDomesticBaseMap(map, updateMapStatus)

  layerGroup = L.layerGroup().addTo(map)
  L.control.zoom({ position: 'topright' }).addTo(map)
  attributionControl = L.control.attribution({ position: 'bottomright', prefix: false })
  currentAttribution = domesticMapAttribution(mapStatus.value)
  attributionControl.addAttribution(currentAttribution).addTo(map)

  scheduleSync(true)
})

watch(() => props.events, () => scheduleSync(true))

onBeforeUnmount(() => {
  if (renderFrame !== null) cancelAnimationFrame(renderFrame)
  map?.remove()
  markers.clear()
})

defineExpose({
  resize: () => {
    nextTick(() => {
      map?.invalidateSize()
      fitEvents()
    })
  },
})
</script>

<style scoped>
.map-shell {
  position: relative;
  width: 100%;
  height: 600px;
}

.map-container {
  width: 100%;
  height: 100%;
  z-index: 0;
  background: #dfe3e1;
  border-radius: 4px;
}

.map-compliance-notice { position: absolute; z-index: 720; top: 14px; left: 50%; display: grid; gap: 3px; max-width: min(430px, calc(100% - 28px)); padding: 9px 13px; transform: translateX(-50%); border: 1px solid rgba(17, 23, 25, 0.16); border-radius: 5px; color: #465355; background: rgba(250, 252, 250, 0.94); box-shadow: 0 8px 20px rgba(17, 23, 25, 0.1); text-align: center; backdrop-filter: blur(8px); }
.map-compliance-notice strong { font-size: 10px; }
.map-compliance-notice span { color: #687375; font-size: 8px; line-height: 1.45; }
.map-compliance-notice.error { border-color: rgba(201, 49, 47, 0.3); color: #8b302c; }

:deep(.leaflet-container) { background: #dfe3e1; font-family: inherit; }
:deep(.leaflet-tile-container img) { outline: 1px solid transparent; clip-path: inset(0 -1px 0 -1px); transform: translateZ(0); }
:deep(.leaflet-popup-content-wrapper) { padding: 0; overflow: hidden; border-radius: 6px; box-shadow: 0 14px 34px rgba(17, 23, 25, 0.18); }
:deep(.leaflet-popup-content) { margin: 0; }
:deep(.leaflet-popup-close-button) { top: 7px !important; right: 7px !important; z-index: 2; color: #687375 !important; }
:deep(.history-popup) { min-width: 230px; color: #111719; background: white; }
:deep(.history-popup-head) { min-height: 42px; display: flex; align-items: center; justify-content: space-between; gap: 28px; padding: 8px 34px 8px 12px; background: #f1f3f1; border-bottom: 1px solid #d9dfde; }
:deep(.history-popup-head strong) { font-family: "Fira Code", monospace; font-size: 13px; }
:deep(.history-popup-head span) { color: #687375; font-family: "Fira Code", monospace; font-size: 8px; }
:deep(.history-popup p) { margin: 0; padding: 11px 12px 4px; font-size: 11px; font-weight: 700; line-height: 1.45; }
:deep(.history-popup small) { display: block; padding: 0 12px 12px; color: #687375; font-family: "Fira Code", monospace; font-size: 8px; }
:deep(.leaflet-control-attribution) { font-size: 8px; }
</style>
