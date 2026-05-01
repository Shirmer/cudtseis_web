<template>
  <div class="map-container" ref="mapEl"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface EarthquakeEvent {
  lon: number | null
  lat: number | null
  mag: number | null
  time: string | null
  place: string | null
  depth_km: number | null
}

const props = defineProps<{
  events: EarthquakeEvent[]
}>()

const mapEl = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
let layerGroup = L.layerGroup()
const currentZoom = ref(2)

// Esri 浅灰底图
const TILE_BASE = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
// 高德中文注记
const TILE_LABEL = 'https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'

function render() {
  if (!map) return
  layerGroup.clearLayers()

  const zoom = currentZoom.value
  
  // 1. 获取当前视野范围
  const b = map.getBounds()
  const west = b.getWest()
  const east = b.getEast()

  // 2. 计算当前视野跨越了多少个“地球周期” (360度)
  // Leaflet 的经度是连续增长的，例如向右拖动可能变成 400, 700...
  // 我们计算出当前视野覆盖了从第几个地球(kMin)到第几个地球(kMax)
  const kMin = Math.floor((west + 180) / 360)
  const kMax = Math.floor((east + 180) / 360)

  // 动态调整圆点大小
  let baseRadius = 1.0
  if (zoom <= 2) baseRadius = 0.8
  else if (zoom < 5) baseRadius = 1.2
  else baseRadius = 2.0

  // 3. 多重循环渲染：确保每个可见的“地球副本”上都有点
  for (let k = kMin; k <= kMax; k++) {
    // dx 是经度偏移量：0, 360, 720, -360...
    const dx = 360 * k

    props.events.forEach(q => {
      if (q.lon == null || q.lat == null) return

      // 核心技巧：原始经度 + 偏移量 = 在副本上的正确位置
      const renderLon = q.lon + dx
      
      const mag = q.mag ?? 0
      const r = Math.max(3, mag * 2 * baseRadius)
      const color = mag >= 6 ? '#dc2626' : mag >= 5 ? '#f59e0b' : mag >= 4 ? '#fbbf24' : '#10b981'
      const depth = q.depth_km == null ? '-' : `${q.depth_km} km`

      L.circleMarker([q.lat, renderLon], {
        radius: r,
        color: '#ffffff',
        weight: 1, 
        fillColor: color,
        fillOpacity: 0.9
      })
      .bindPopup(
        `<div class="custom-popup">
          <div class="popup-header">
             <span class="mag-tag" style="background:${color}">M${mag.toFixed(1)}</span>
             <span class="time">${q.time ? q.time.replace('T', ' ').slice(0,19) : '-'}</span>
          </div>
          <div class="popup-body">
            <div class="row">📍 ${q.place || 'Unknown'}</div>
            <div class="row">🌊 深度 ${depth}</div>
          </div>
        </div>`,
        { minWidth: 200 }
      )
      .addTo(layerGroup)
    })
  }

  layerGroup.addTo(map)
}

onMounted(() => {
  if (!mapEl.value) return

  // --- 初始化地图 ---
  map = L.map(mapEl.value, { 
    minZoom: 2, 
    maxZoom: 16, 
    zoomControl: false, 
    attributionControl: false,
    
    // 允许无限拖动，不需要 maxBounds
    // worldCopyJump 不需要开启，因为我们手动实现了更高级的覆盖逻辑
    
    // 辅助减少白线
    zoomSnap: 1,
    zoomDelta: 1,

    // 🔥【关键修复】限制拖动范围 🔥
    // 纬度限制在 -85 到 85 之间（去掉了两极的空白区）
    // 经度设为 Infinity 允许左右无限循环
    maxBounds: [[-85, -Infinity], [85, Infinity]],
    
    // 1.0 表示“硬边界”，一旦碰到边界就完全拖不动，不会有回弹效果
    maxBoundsViscosity: 1.0 
  }).setView([25, 105], 2)

  L.control.zoom({ position: 'topright' }).addTo(map)
  L.control.attribution({ position: 'bottomright', prefix: false })
    .addAttribution('Esri, AutoNavi').addTo(map)

  // 1. 底图：允许无限循环
  L.tileLayer(TILE_BASE, { maxZoom: 16 }).addTo(map)

  // 2. 注记：允许无限循环
  L.tileLayer(TILE_LABEL, {
    subdomains: ['1', '2', '3', '4'],
    maxZoom: 16,
    opacity: 0.85,
    className: 'label-layer-filter'
  }).addTo(map)

  // 监听 moveend，因为拖动时需要重新计算视野并补全新的副本点
  map.on('moveend zoomend', () => {
    if(map) currentZoom.value = map.getZoom()
    render()
  })

  if (props.events.length > 0) render()
})

watch(() => props.events, () => { render() }, { deep: true })

defineExpose({
  resize: () => { nextTick(() => { map?.invalidateSize() }) }
})
</script>

<!-- 保留您验证过有效的 CSS -->
<style scoped>
.map-container {
  width: 100%;
  height: 600px;
  background: #e5e5e5;
  border-radius: 4px;
  z-index: 0;
}

/* --- 🔥 核心修复白线代码 🔥 --- */
:deep(.leaflet-tile-container img) {
  outline: 1px solid transparent; 
  clip-path: inset(0 -1px 0 -1px); 
  transform: translateZ(0); 
}

/* 针对 Esri 灰底图的特殊处理 */
:deep(.leaflet-layer) { background: #d5d5d5; }
:deep(.leaflet-container) { background: #d5d5d5 !important; }

/* --- 常规样式 --- */
:deep(.label-layer-filter) { filter: contrast(0.85); }
:deep(.leaflet-popup-content-wrapper) { border-radius: 4px; padding: 0; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
:deep(.leaflet-popup-content) { margin: 0; }
:deep(.leaflet-popup-close-button) { top: 8px !important; right: 8px !important; color: #999 !important; font-size: 18px !important; width: 18px !important; height: 18px !important; line-height: 18px !important; z-index: 20; }
:deep(.popup-header) { display: flex; align-items: center; justify-content: space-between; padding: 8px 34px 8px 12px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
:deep(.mag-tag) { color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold; font-size: 12px; }
:deep(.popup-header .time) { color: #666; font-size: 12px; font-family: monospace; }
:deep(.popup-body) { padding: 12px; font-size: 13px; color: #333; line-height: 1.5; }
:deep(.popup-body .row) { margin-bottom: 4px; }
:deep(.id-row) { color: #aaa; font-size: 10px; margin-top: 6px; border-top: 1px dashed #eee; padding-top: 4px; }
</style>
