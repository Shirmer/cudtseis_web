<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { apiUrl } from '../config/api'

// --- 类型定义 ---
type Quake = {
  id: string
  time: string
  mag: number
  place?: string
  depth_km?: number
  lon: number
  lat: number
}

// --- 关键修改：双图层叠加策略 (Esri灰底 + 高德中文注记) ---

// 1. 底图：Esri 灰色画布 (World Gray Canvas)
// 这是一个全球通用的科研风格底图，自带陆地/海洋区分和省界细节
const TILE_BASE = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'

// 2. 注记：高德地图透明注记层 (简体中文)
const TILE_LABEL = 'https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'

const mapEl = ref<HTMLDivElement | null>(null)
let map: L.Map
let layer = L.layerGroup()
const events = ref<Quake[]>([])

const loading = ref(true)
const sidebarOpen = ref(true)
const currentZoom = ref(2)

const recentEvents = computed(() => {
  return [...events.value]
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .slice(0, 50)
})

function render() {
  if (!map) return
  layer.clearLayers()

  const b = map.getBounds()
  const west = b.getWest()
  const east = b.getEast()
  const eastAdj = east < west ? east + 360 : east
  const kMin = Math.floor((west + 180) / 360)
  const kMax = Math.floor((eastAdj + 180) / 360)

  // 动态点半径逻辑
  const zoom = currentZoom.value
  let baseRadius = 1.0
  if (zoom <= 2) baseRadius = 0.7 
  else if (zoom < 5) baseRadius = 1.0
  else if (zoom < 10) baseRadius = 1.5
  else baseRadius = 2.5

  for (let k = kMin; k <= kMax; k++) {
    const dx = 360 * k
    for (const q of events.value) {
      const lon = q.lon + dx
      const lat = q.lat
      const mag = q.mag
      
      const r = Math.max(3, mag * 2 * baseRadius)

      // 颜色配置
      const color = mag >= 6 ? '#dc2626' : mag >= 5 ? '#f59e0b' : mag >= 4 ? '#fbbf24' : '#10b981'
      
      L.circleMarker([lat, lon], {
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
             <span class="time">${new Date(q.time).toLocaleTimeString()}</span>
          </div>
          <div class="popup-body">
            <div class="row">📍 ${q.place ?? 'Unknown'}</div>
            <div class="row">🌊 深度 ${q.depth_km ?? '-'} km</div>
            <div class="row id-row">ID: ${q.id}</div>
          </div>
        </div>`,
        { minWidth: 180 }
      )
      .addTo(layer)
    }
  }
  layer.addTo(map)
}

async function loadInitial() {
  try {
    const res = await fetch(apiUrl('/events?hours=24&minMag=3.0&limit=20000'))
    events.value = await res.json()
    render()
  } catch (e) {
    console.error("Fetch error:", e)
  } finally {
    loading.value = false
  }
}

function connectSSE() {
  const es = new EventSource(apiUrl('/stream'))
  es.addEventListener('new_events', (evt: MessageEvent) => {
    const msg = JSON.parse(evt.data)
    events.value.push(...msg.data)
    render()
  })
}

function flyToQuake(q: Quake) {
  map.flyTo([q.lat, q.lon], 6, { duration: 1.5 })
  if (window.innerWidth < 768) sidebarOpen.value = false
}

onMounted(async () => {
  map = L.map(mapEl.value!, { 
    minZoom: 2, 
    maxZoom: 16, 
    zoomControl: false, 
    attributionControl: false,
    maxBounds: [[-85, -Infinity], [85, Infinity]],
    maxBoundsViscosity: 1.0
  }).setView([25, 105], 2)

  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.control.attribution({ position: 'bottomright', prefix: false })
    .addAttribution('Esri, AutoNavi | CDUT Seis')
    .addTo(map)

  // 1. Esri 灰色底图
  L.tileLayer(TILE_BASE, { maxZoom: 16 }).addTo(map)

  // 2. 高德中文注记 (透明底)
  L.tileLayer(TILE_LABEL, {
    subdomains: ['1', '2', '3', '4'],
    maxZoom: 16,
    opacity: 0.85,
    className: 'label-layer-filter'
  }).addTo(map)

  map.on('moveend zoomend', () => {
    currentZoom.value = map.getZoom()
    render()
  })

  await loadInitial()
  connectSSE()
})
</script>

<template>
  <div class="dashboard light-theme">
    
    <!-- Navbar -->
    <header class="navbar">
      <div class="brand">
        <!-- 确保 public 文件夹下有 cdut_logo.png -->
        <img src="/cdut_logo.png" alt="CDUT Logo" class="school-logo" />
        <div class="title-group">
          <h1>CDUT SEIS</h1>
          <small>成都理工大学地震研究中心</small>
        </div>
      </div>
      <div class="nav-links">
        <span class="live-status"><span class="blink">●</span> 实时监控运行中</span>
        <router-link to="/history">历史数据</router-link>  <!-- 更新为路由链接 -->
        <a href="#">关于系统</a>
      </div>
    </header>

    <!-- Sidebar Toggle -->
    <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
      <div class="sidebar-header">
        <h3>实时地震列表</h3>
        <button class="close-btn" @click="sidebarOpen = false">×</button>
      </div>
      <div class="quake-list">
        <div 
          v-for="q in recentEvents" 
          :key="q.id" 
          class="quake-item"
          @click="flyToQuake(q)"
        >
          <div class="mag-badge" :style="{ backgroundColor: q.mag >= 6 ? '#dc2626' : q.mag >= 5 ? '#f59e0b' : '#10b981' }">
            {{ q.mag.toFixed(1) }}
          </div>
          <div class="quake-info">
            <div class="place" :title="q.place">{{ q.place || 'Unknown' }}</div>
            <div class="meta">
              <span>{{ new Date(q.time).toLocaleTimeString() }}</span>
              <span class="depth-tag">{{ q.depth_km }}km</span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Legend -->
    <div class="legend-panel">
      <div class="legend-title">震级 (M)</div>
      <div class="legend-items">
        <div class="l-item"><span class="dot" style="background:#10b981"></span>3-4</div>
        <div class="l-item"><span class="dot" style="background:#fbbf24"></span>4-5</div>
        <div class="l-item"><span class="dot" style="background:#f59e0b"></span>5-6</div>
        <div class="l-item"><span class="dot" style="background:#dc2626"></span>6+</div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-mask">
      <div class="spinner"></div>
    </div>

    <!-- Map -->
    <div ref="mapEl" class="map-container"></div>
  </div>
</template>

<style scoped>
/* 全局设定 */
.dashboard.light-theme {
  position: relative; width: 100vw; height: 100vh;
  background-color: #e5e5e5; /* 与 Esri 底图一致 */
  font-family: "Microsoft YaHei", sans-serif;
  color: #333; overflow: hidden;
}

.map-container { width: 100%; height: 100%; z-index: 0; background: #e5e5e5; }

/* 只有注记层需要微调对比度 */
:deep(.label-layer-filter) {
  filter: contrast(0.85); 
}

/* UI 样式 */
.navbar {
  position: absolute; top: 0; left: 0; right: 0; height: 60px;
  background: rgba(255, 255, 255, 0.98);
  border-bottom: 1px solid #ddd;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  z-index: 1000; display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px 0 70px;
}
.brand { display: flex; align-items: center; }
.school-logo { height: 38px; width: auto; margin-right: 12px; }
.title-group h1 { margin: 0; font-size: 18px; font-weight: 800; color: #1e3a8a; }
.title-group small { display: block; font-size: 11px; color: #666; }
.nav-links { display: flex; gap: 20px; font-size: 14px; }
.nav-links a { text-decoration: none; color: #555; }
.live-status { display: flex; align-items: center; gap: 6px; color: #059669; font-size: 12px; background: #ecfdf5; padding: 4px 10px; border-radius: 99px; }

.sidebar {
  position: absolute; top: 60px; bottom: 0; left: 0; width: 300px;
  background: #fff; border-right: 1px solid #eee; z-index: 1001;
  display: flex; flex-direction: column; box-shadow: 2px 0 8px rgba(0,0,0,0.05);
  transition: transform 0.3s;
}
.sidebar.collapsed { transform: translateX(-100%); }
.sidebar-toggle {
  position: absolute; top: 10px; left: 15px; width: 40px; height: 40px;
  background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px;
  display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 1002;
  color: #555;
}
.sidebar-toggle:hover { background: #fff; color: #1e3a8a; }
.sidebar-header { padding: 12px 16px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.close-btn { background: none; border: none; font-size: 20px; color: #999; cursor: pointer; }

.quake-list { flex: 1; overflow-y: auto; }
.quake-item { padding: 10px 16px; border-bottom: 1px solid #f5f5f5; display: flex; align-items: center; cursor: pointer; }
.quake-item:hover { background: #f9f9f9; }
.mag-badge { width: 32px; height: 32px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff; margin-right: 12px; font-size: 13px; }
.quake-info .place { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 2px; }
.quake-info .meta { font-size: 12px; color: #888; }
.depth-tag { background: #eee; padding: 1px 4px; border-radius: 3px; margin-left: 6px; }

.legend-panel {
  position: absolute; bottom: 25px; right: 15px;
  background: white; padding: 8px 12px; border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1); z-index: 900;
}
.legend-title { font-size: 12px; font-weight: 700; margin-bottom: 5px; }
.legend-items { display: flex; gap: 10px; }
.l-item { display: flex; align-items: center; font-size: 11px; color: #666; }
.dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }

.loading-mask { position: absolute; inset: 0; background: rgba(255,255,255,0.9); z-index: 2000; display: flex; justify-content: center; align-items: center; }
.spinner { width: 30px; height: 30px; border: 3px solid #eee; border-top-color: #1e3a8a; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

/* 
  --- 弹窗 (Popup) 样式修复 --- 
  这里是关键修改点：
  1. 给 header 增加了右内边距 (padding-right: 30px)
  2. 强制了关闭按钮的位置和 z-index
*/
:deep(.leaflet-popup-content-wrapper) { 
  border-radius: 4px; padding: 0; 
  box-shadow: 0 4px 15px rgba(0,0,0,0.15); 
}
:deep(.leaflet-popup-content) { margin: 0; }

:deep(.leaflet-popup-close-button) {
  top: 8px !important;
  right: 8px !important;
  color: #999 !important;
  font-size: 18px !important;
  width: 18px !important;
  height: 18px !important;
  line-height: 18px !important;
  z-index: 20; /* 确保它在文字上面 */
}

:deep(.popup-header) { 
  display: flex; 
  align-items: center; 
  justify-content: space-between; 
  /* 右侧留出 34px 给关闭按钮 */
  padding: 8px 34px 8px 12px; 
  background: #f5f5f5; 
  border-bottom: 1px solid #ddd; 
}

:deep(.mag-tag) { 
  color: white; 
  padding: 2px 6px; 
  border-radius: 3px; 
  font-weight: bold; 
  font-size: 12px; 
}
:deep(.popup-header .time) {
  color: #666;
  font-size: 12px;
  font-family: monospace; /* 等宽字体 */
}

:deep(.popup-body) { padding: 12px; font-size: 13px; color: #333; line-height: 1.5; }
:deep(.popup-body .row) { margin-bottom: 4px; }
:deep(.id-row) { color: #aaa; font-size: 10px; margin-top: 6px; border-top: 1px dashed #eee; padding-top: 4px; }

@media (max-width: 768px) {
  .sidebar { width: 100%; top: 60px; }
  .navbar { padding-left: 60px; }
  .nav-links, .legend-panel { display: none; }
}
</style>
