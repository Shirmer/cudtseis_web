<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import { apiUrl } from '../config/api'

type Quake = {
  id: string
  time: string
  updated?: string
  mag: number
  place?: string | null
  depth_km?: number | null
  lon: number
  lat: number
  magType?: string | null
  nst?: number | null
  gap?: number | null
  dmin?: number | null
  rms?: number | null
  net?: string | null
  type?: string | null
  horizontalError?: number | null
  depthError?: number | null
  magError?: number | null
  magNst?: number | null
  status?: string | null
  locationSource?: string | null
  magSource?: string | null
}

type TopicSignal = {
  key: string
  label: string
  description: string
  paperCount: number
}

type ResearchPaper = {
  paperId: string
  title: string
  authors: string[]
  authorsText: string
  year: number
  abstract: string
  abstractPreview: string
  venue: string
  citationCount: number
  doi: string
  url: string
  source: string
  relevanceHint: string
  evidenceSnippet: string
}

type SummarySection = {
  key: string
  title: string
  paragraphs: string[]
}

type SummaryEvidenceCard = {
  title: string
  text: string
  citation: string
}

type ResearchResponse = {
  event: Quake
  cohort: {
    total: number
    maxMagnitude: number
    averageMagnitude: number
    averageDepthKm: number
    topRegions: Array<{ region: string; count: number }>
    depthBands: Array<{ label: string; count: number }>
  }
  topicSignals: TopicSignal[]
  summary: {
    headline: string
    subtitle: string
    abstract: string
    sections: SummarySection[]
    evidenceCards: SummaryEvidenceCard[]
    closing: string
    limitations: string
  }
  papers: ResearchPaper[]
  queryPlan: {
    queries: string[]
    yearMin: number
    sources: string[]
    strategy: string
  }
  sourceBreakdown: Record<string, number>
  notes: string[]
  mode: string
  generatedAt: string
}

const TILE_BASE =
  'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'
const TILE_LABEL =
  'https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'

const mapEl = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
let layer = L.layerGroup()
let eventSource: EventSource | null = null
let researchAbortController: AbortController | null = null
let pendingPopupId: string | null = null

const events = ref<Quake[]>([])
const loading = ref(true)
const researchLoading = ref(false)
const researchError = ref('')
const sidebarOpen = ref(true)
const detailPanelOpen = ref(true)
const currentZoom = ref(2)
const selectedQuake = ref<Quake | null>(null)
const research = ref<ResearchResponse | null>(null)

const recentEvents = computed(() => {
  return [...events.value]
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .slice(0, 60)
})

const dashboardStats = computed(() => {
  const list = events.value
  const maxMagnitude = list.reduce((max, quake) => Math.max(max, quake.mag || 0), 0)
  const shallowCount = list.filter((quake) => (quake.depth_km ?? 9999) < 70).length
  const averageDepth =
    list.length === 0
      ? 0
      : list.reduce((sum, quake) => sum + (quake.depth_km ?? 0), 0) / list.length

  return {
    total: list.length,
    maxMagnitude,
    shallowCount,
    averageDepth,
  }
})

function magnitudeColor(magnitude: number): string {
  if (magnitude >= 6) return '#dc2626'
  if (magnitude >= 5) return '#f59e0b'
  if (magnitude >= 4) return '#fbbf24'
  return '#10b981'
}

function formatClock(value?: string | null): string {
  if (!value) return '--:--:--'
  return new Date(value).toLocaleTimeString('zh-CN', { hour12: false })
}

function formatDateTime(value?: string | null): string {
  if (!value) return '未知时间'
  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatNumber(value?: number | null, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return Number(value).toFixed(digits)
}

function formatCoordinate(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${Number(value).toFixed(3)}°`
}

function depthClass(depth?: number | null): string {
  if (depth === null || depth === undefined || Number.isNaN(depth)) return '深度待定'
  if (depth < 70) return '浅源'
  if (depth < 300) return '中源'
  return '深源'
}

function quakePlace(quake: Quake | null | undefined): string {
  return quake?.place?.trim() || 'Unknown'
}

function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function popupHtml(quake: Quake): string {
  const color = magnitudeColor(quake.mag)
  const place = escapeHtml(quakePlace(quake))
  const typeText = escapeHtml(quake.type || 'earthquake')
  const magTypeText = escapeHtml(quake.magType || 'M')
  const sourceText = escapeHtml(quake.locationSource || quake.net || 'USGS')

  return `
    <div class="custom-popup">
      <div class="popup-header">
        <span class="mag-tag" style="background:${color}">M${quake.mag.toFixed(1)}</span>
        <span class="time">${escapeHtml(formatClock(quake.time))}</span>
      </div>
      <div class="popup-body">
        <div class="popup-place">${place}</div>
        <div class="popup-grid">
          <div class="row"><span>深度</span><strong>${escapeHtml(formatNumber(quake.depth_km, 1))} km</strong></div>
          <div class="row"><span>类型</span><strong>${typeText}</strong></div>
          <div class="row"><span>震级制式</span><strong>${magTypeText}</strong></div>
          <div class="row"><span>坐标</span><strong>${escapeHtml(formatCoordinate(quake.lat))}, ${escapeHtml(formatCoordinate(quake.lon))}</strong></div>
          <div class="row"><span>网络</span><strong>${escapeHtml(quake.net || '—')}</strong></div>
          <div class="row"><span>定位源</span><strong>${sourceText}</strong></div>
        </div>
        <div class="id-row">ID: ${escapeHtml(quake.id)}</div>
      </div>
    </div>
  `
}

function focusQuake(
  quake: Quake,
  options: { flyTo?: boolean; openPopup?: boolean } = {},
): void {
  const { flyTo = false, openPopup = false } = options
  selectedQuake.value = quake
  detailPanelOpen.value = true

  if (flyTo && map) {
    map.flyTo([quake.lat, quake.lon], Math.max(map.getZoom(), 5), { duration: 1.2 })
  }

  if (openPopup) {
    pendingPopupId = quake.id
  }

  if (typeof window !== 'undefined' && window.innerWidth < 1100) {
    sidebarOpen.value = false
  }

  render()
  void loadResearch(quake.id)
}

function upsertEvents(incoming: Quake[]): void {
  const merged = new Map(events.value.map((quake) => [quake.id, quake]))
  for (const quake of incoming) {
    const previous = merged.get(quake.id)
    merged.set(quake.id, previous ? { ...previous, ...quake } : quake)
  }

  events.value = Array.from(merged.values())
  if (selectedQuake.value) {
    const refreshed = merged.get(selectedQuake.value.id)
    if (refreshed) {
      selectedQuake.value = refreshed
    }
  }

  if (!selectedQuake.value && events.value.length > 0) {
    selectedQuake.value = [...events.value].sort(
      (a, b) => new Date(b.time).getTime() - new Date(a.time).getTime(),
    )[0]
  }

  render()
}

function render(): void {
  if (!map) return
  layer.clearLayers()

  const bounds = map.getBounds()
  const west = bounds.getWest()
  const east = bounds.getEast()
  const eastAdjusted = east < west ? east + 360 : east
  const kMin = Math.floor((west + 180) / 360)
  const kMax = Math.floor((eastAdjusted + 180) / 360)
  const zoom = currentZoom.value
  const selectedId = selectedQuake.value?.id

  let baseRadius = 1
  if (zoom <= 2) baseRadius = 0.7
  else if (zoom < 5) baseRadius = 1
  else if (zoom < 10) baseRadius = 1.5
  else baseRadius = 2.3

  const sortedEvents = [...events.value].sort((a, b) => {
    if (a.id === selectedId) return 1
    if (b.id === selectedId) return -1
    return 0
  })

  let selectedMarker: L.CircleMarker | null = null

  for (let k = kMin; k <= kMax; k += 1) {
    const dx = 360 * k

    for (const quake of sortedEvents) {
      const radius = Math.max(3, quake.mag * 2 * baseRadius)
      const color = magnitudeColor(quake.mag)
      const isSelected = quake.id === selectedId

      const marker = L.circleMarker([quake.lat, quake.lon + dx], {
        radius: isSelected ? radius + 2 : radius,
        color: isSelected ? '#0f172a' : '#ffffff',
        weight: isSelected ? 2 : 1,
        fillColor: color,
        fillOpacity: isSelected ? 1 : 0.9,
      })

      marker.bindPopup(popupHtml(quake), {
        minWidth: 260,
        className: 'quake-popup',
      })

      marker.on('click', () => {
        focusQuake(quake, { openPopup: true })
      })

      if (isSelected) {
        selectedMarker = marker
      }

      marker.addTo(layer)
    }
  }

  layer.addTo(map)

  if (selectedMarker && pendingPopupId === selectedId) {
    selectedMarker.openPopup()
    pendingPopupId = null
  }
}

async function loadInitial(): Promise<void> {
  try {
    const response = await fetch(apiUrl('/events?hours=24&minMag=3.0&limit=20000'))
    const data = (await response.json()) as Quake[]
    upsertEvents(data)

    const first = [...data].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())[0]
    if (first) {
      selectedQuake.value = first
      render()
      void loadResearch(first.id)
    }
  } catch (error) {
    console.error('Fetch error:', error)
  } finally {
    loading.value = false
  }
}

async function loadResearch(eventId: string): Promise<void> {
  researchAbortController?.abort()
  const controller = new AbortController()
  researchAbortController = controller
  researchLoading.value = true
  researchError.value = ''

  try {
    const response = await fetch(
      apiUrl(`/events/${eventId}/research?hours=24&minMag=3.0&cohortLimit=2000&paperLimit=12&yearMin=2015`),
      { signal: controller.signal },
    )

    if (!response.ok) {
      throw new Error(`Research API failed with ${response.status}`)
    }

    research.value = (await response.json()) as ResearchResponse
  } catch (error) {
    if ((error as Error).name === 'AbortError') return
    console.error('Research fetch error:', error)
    research.value = null
    researchError.value = '文献检索暂时不可用，可能是网络或学术接口限流导致。'
  } finally {
    if (researchAbortController === controller) {
      researchLoading.value = false
    }
  }
}

function connectSSE(): void {
  eventSource = new EventSource(apiUrl('/stream'))
  eventSource.addEventListener('new_events', (event: MessageEvent) => {
    const message = JSON.parse(event.data) as { data: Quake[] }
    upsertEvents(message.data || [])
  })
}

onMounted(async () => {
  if (!mapEl.value) return

  map = L.map(mapEl.value, {
    minZoom: 2,
    maxZoom: 16,
    zoomControl: false,
    attributionControl: false,
    maxBounds: [[-85, -Infinity], [85, Infinity]],
    maxBoundsViscosity: 1.0,
  }).setView([25, 105], 2)

  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.control.attribution({ position: 'bottomright', prefix: false })
    .addAttribution('Esri, AutoNavi | CDUT Seis')
    .addTo(map)

  L.tileLayer(TILE_BASE, { maxZoom: 16 }).addTo(map)
  L.tileLayer(TILE_LABEL, {
    subdomains: ['1', '2', '3', '4'],
    maxZoom: 16,
    opacity: 0.85,
    className: 'label-layer-filter',
  }).addTo(map)

  map.on('moveend zoomend', () => {
    if (!map) return
    currentZoom.value = map.getZoom()
    render()
  })

  await loadInitial()
  connectSSE()
})

onBeforeUnmount(() => {
  researchAbortController?.abort()
  eventSource?.close()
  map?.remove()
})
</script>

<template>
  <div class="dashboard-shell">
    <header class="navbar">
      <div class="brand">
        <img src="/cdut_logo.png" alt="CDUT Logo" class="school-logo" />
        <div class="title-group">
          <h1>CDUT SEIS</h1>
          <small>成都理工大学地震研究中心</small>
        </div>
      </div>

      <div class="nav-actions">
        <span class="live-status"><span class="blink">●</span> 实时监控运行中</span>
        <button class="panel-toggle desktop-only" @click="detailPanelOpen = !detailPanelOpen">
          {{ detailPanelOpen ? '收起科研面板' : '展开科研面板' }}
        </button>
        <router-link to="/history">历史数据</router-link>
        <a href="#">关于系统</a>
      </div>
    </header>

    <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <main class="workspace" :class="{ 'detail-collapsed': !detailPanelOpen }">
      <aside class="sidebar" :class="{ collapsed: !sidebarOpen }">
        <div class="sidebar-header">
          <div>
            <h3>实时地震列表</h3>
            <p>点击事件可联动地图与文献检索</p>
          </div>
          <button class="close-btn" @click="sidebarOpen = false">×</button>
        </div>

        <div class="sidebar-stats">
          <div class="stat-card">
            <strong>{{ dashboardStats.total }}</strong>
            <span>24h 事件</span>
          </div>
          <div class="stat-card">
            <strong>M{{ formatNumber(dashboardStats.maxMagnitude, 1) }}</strong>
            <span>最大震级</span>
          </div>
          <div class="stat-card">
            <strong>{{ dashboardStats.shallowCount }}</strong>
            <span>浅源事件</span>
          </div>
        </div>

        <div class="quake-list">
          <button
            v-for="quake in recentEvents"
            :key="quake.id"
            class="quake-item"
            :class="{ active: quake.id === selectedQuake?.id }"
            @click="focusQuake(quake, { flyTo: true, openPopup: true })"
          >
            <div class="mag-badge" :style="{ backgroundColor: magnitudeColor(quake.mag) }">
              {{ quake.mag.toFixed(1) }}
            </div>
            <div class="quake-info">
              <div class="place" :title="quakePlace(quake)">{{ quakePlace(quake) }}</div>
              <div class="meta">
                <span>{{ formatClock(quake.time) }}</span>
                <span class="depth-tag">{{ formatNumber(quake.depth_km, 1) }}km</span>
                <span class="type-tag">{{ depthClass(quake.depth_km) }}</span>
              </div>
            </div>
          </button>
        </div>
      </aside>

      <section class="map-stage">
        <div class="map-top-strip">
          <div class="overlay-card">
            <span class="overlay-label">监测概览</span>
            <strong>{{ dashboardStats.total }}</strong>
            <small>当前 24h 已加载事件</small>
          </div>
          <div class="overlay-card">
            <span class="overlay-label">平均深度</span>
            <strong>{{ formatNumber(dashboardStats.averageDepth, 1) }} km</strong>
            <small>用于科研面板综合研判</small>
          </div>
          <div class="overlay-card selected" v-if="selectedQuake">
            <span class="overlay-label">当前选中</span>
            <strong>M{{ selectedQuake.mag.toFixed(1) }}</strong>
            <small>{{ quakePlace(selectedQuake) }}</small>
          </div>
        </div>

        <div ref="mapEl" class="map-container"></div>

        <div class="legend-panel">
          <div class="legend-title">震级 (M)</div>
          <div class="legend-items">
            <div class="legend-item"><span class="dot" style="background:#10b981"></span>3-4</div>
            <div class="legend-item"><span class="dot" style="background:#fbbf24"></span>4-5</div>
            <div class="legend-item"><span class="dot" style="background:#f59e0b"></span>5-6</div>
            <div class="legend-item"><span class="dot" style="background:#dc2626"></span>6+</div>
          </div>
        </div>
      </section>

      <aside class="detail-panel" :class="{ collapsed: !detailPanelOpen }">
        <div class="detail-header">
          <div>
            <h3>地震详情与科研解读</h3>
            <p>摘要级文献检索 + 事件科学总结</p>
          </div>
          <button class="close-btn" @click="detailPanelOpen = false">×</button>
        </div>

        <div v-if="selectedQuake" class="detail-content">
          <section class="hero-card">
            <div class="hero-top">
              <span class="hero-mag" :style="{ backgroundColor: magnitudeColor(selectedQuake.mag) }">
                M{{ selectedQuake.mag.toFixed(1) }}
              </span>
              <span class="hero-time">{{ formatDateTime(selectedQuake.time) }}</span>
            </div>
            <h2>{{ quakePlace(selectedQuake) }}</h2>
            <p>{{ depthClass(selectedQuake.depth_km) }}地震，深度 {{ formatNumber(selectedQuake.depth_km, 1) }} km</p>
            <div class="chip-row">
              <span class="chip">{{ selectedQuake.type || 'earthquake' }}</span>
              <span class="chip">网络 {{ selectedQuake.net || '—' }}</span>
              <span class="chip">状态 {{ selectedQuake.status || '—' }}</span>
              <span class="chip">坐标 {{ formatCoordinate(selectedQuake.lat) }}, {{ formatCoordinate(selectedQuake.lon) }}</span>
            </div>
          </section>

          <section class="detail-card">
            <div class="section-head">
              <div>
                <span class="section-kicker">Expanded Event Detail</span>
                <h4>点击地震点后的详细信息</h4>
              </div>
            </div>
            <div class="detail-grid">
              <div class="metric">
                <span>更新时间</span>
                <strong>{{ formatDateTime(selectedQuake.updated) }}</strong>
              </div>
              <div class="metric">
                <span>震级类型</span>
                <strong>{{ selectedQuake.magType || '—' }}</strong>
              </div>
              <div class="metric">
                <span>Gap</span>
                <strong>{{ formatNumber(selectedQuake.gap, 1) }}</strong>
              </div>
              <div class="metric">
                <span>RMS</span>
                <strong>{{ formatNumber(selectedQuake.rms, 2) }}</strong>
              </div>
              <div class="metric">
                <span>水平误差</span>
                <strong>{{ formatNumber(selectedQuake.horizontalError, 2) }}</strong>
              </div>
              <div class="metric">
                <span>深度误差</span>
                <strong>{{ formatNumber(selectedQuake.depthError, 2) }}</strong>
              </div>
              <div class="metric">
                <span>震级误差</span>
                <strong>{{ formatNumber(selectedQuake.magError, 2) }}</strong>
              </div>
              <div class="metric">
                <span>定位来源</span>
                <strong>{{ selectedQuake.locationSource || '—' }}</strong>
              </div>
              <div class="metric">
                <span>震级来源</span>
                <strong>{{ selectedQuake.magSource || '—' }}</strong>
              </div>
              <div class="metric">
                <span>NST / MagNST</span>
                <strong>{{ selectedQuake.nst ?? '—' }} / {{ selectedQuake.magNst ?? '—' }}</strong>
              </div>
            </div>
          </section>

          <section v-if="researchLoading" class="detail-card loading-card">
            <div class="skeleton-line wide"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line short"></div>
          </section>

          <section v-else-if="researchError" class="detail-card error-card">
            <h4>文献检索暂不可用</h4>
            <p>{{ researchError }}</p>
          </section>

          <template v-else-if="research">
            <section class="detail-card article-card">
              <div class="article-header">
                <span class="section-kicker">Research Conclusion</span>
                <h4>{{ research.summary.headline }}</h4>
                <p class="article-subtitle">{{ research.summary.subtitle }}</p>
                <div class="article-meta">
                  <span>{{ formatDateTime(research.generatedAt) }}</span>
                  <span>{{ research.mode }}</span>
                  <span>{{ research.queryPlan.sources.join(' / ') }} API</span>
                </div>
              </div>

              <div class="article-abstract">
                <div class="abstract-label">摘要式结论</div>
                <p>{{ research.summary.abstract }}</p>
              </div>

              <div class="report-article">
                <section
                  v-for="section in research.summary.sections"
                  :key="section.key"
                  class="report-section"
                >
                  <h5>{{ section.title }}</h5>
                  <p v-for="paragraph in section.paragraphs" :key="paragraph">{{ paragraph }}</p>
                </section>
              </div>

              <div v-if="research.summary.evidenceCards.length" class="evidence-gallery">
                <article
                  v-for="card in research.summary.evidenceCards"
                  :key="`${card.title}-${card.citation}`"
                  class="evidence-card"
                >
                  <span class="evidence-label">摘要证据</span>
                  <h5>{{ card.title }}</h5>
                  <p>{{ card.text }}</p>
                  <small>{{ card.citation }}</small>
                </article>
              </div>

              <div class="article-closing">
                <h5>综合结论</h5>
                <p>{{ research.summary.closing }}</p>
                <p class="limit-text">{{ research.summary.limitations }}</p>
              </div>
            </section>

            <section class="detail-card">
              <div class="section-head">
                <div>
                  <span class="section-kicker">Literature Signals</span>
                  <h4>文献主题与检索策略</h4>
                </div>
              </div>

              <p class="summary-paragraph">{{ research.queryPlan.strategy }}</p>

              <div class="chip-row">
                <span v-for="signal in research.topicSignals" :key="signal.key" class="topic-chip">
                  {{ signal.label }} · {{ signal.paperCount }}
                </span>
              </div>

              <div class="cohort-grid">
                <div class="metric">
                  <span>事件样本</span>
                  <strong>{{ research.cohort.total }}</strong>
                </div>
                <div class="metric">
                  <span>最大震级</span>
                  <strong>M{{ formatNumber(research.cohort.maxMagnitude, 1) }}</strong>
                </div>
                <div class="metric">
                  <span>平均震级</span>
                  <strong>M{{ formatNumber(research.cohort.averageMagnitude, 2) }}</strong>
                </div>
                <div class="metric">
                  <span>平均深度</span>
                  <strong>{{ formatNumber(research.cohort.averageDepthKm, 1) }} km</strong>
                </div>
              </div>

              <div class="info-group">
                <h5>检索查询</h5>
                <div class="query-list">
                  <span v-for="query in research.queryPlan.queries" :key="query" class="query-chip">{{ query }}</span>
                </div>
              </div>

              <div class="info-group">
                <h5>来源统计</h5>
                <div class="query-list">
                  <span
                    v-for="(count, source) in research.sourceBreakdown"
                    :key="source"
                    class="source-chip"
                  >
                    {{ source }} · {{ count }}
                  </span>
                </div>
              </div>

              <div class="info-group" v-if="research.cohort.topRegions.length">
                <h5>当前样本高频区域</h5>
                <div class="query-list">
                  <span
                    v-for="region in research.cohort.topRegions"
                    :key="region.region"
                    class="region-chip"
                  >
                    {{ region.region }} · {{ region.count }}
                  </span>
                </div>
              </div>

              <div class="info-group" v-if="research.notes.length">
                <h5>检索备注</h5>
                <p v-for="note in research.notes" :key="note" class="note-item">{{ note }}</p>
              </div>
            </section>

            <section class="detail-card">
              <div class="section-head">
                <div>
                  <span class="section-kicker">Related Papers</span>
                  <h4>相关文献</h4>
                </div>
                <span class="paper-count">{{ research.papers.length }} 篇</span>
              </div>

              <div v-if="research.papers.length" class="paper-list">
                <article v-for="paper in research.papers" :key="paper.paperId || paper.title" class="paper-card">
                  <div class="paper-meta-row">
                    <span class="paper-source">{{ paper.source }}</span>
                    <span class="paper-citation">引用 {{ paper.citationCount }}</span>
                    <span class="paper-year">{{ paper.year || '未知年份' }}</span>
                  </div>
                  <h5>{{ paper.title }}</h5>
                  <p class="paper-authors">{{ paper.authorsText }}</p>
                  <p class="paper-venue">{{ paper.venue || '期刊/会议待补充' }}</p>
                  <div class="chip-row tight">
                    <span class="topic-chip">{{ paper.relevanceHint }}</span>
                    <span v-if="paper.doi" class="source-chip">DOI</span>
                  </div>
                  <p class="paper-abstract">{{ paper.abstractPreview || '暂无摘要信息。' }}</p>
                  <p v-if="paper.evidenceSnippet" class="paper-evidence">摘要证据：{{ paper.evidenceSnippet }}</p>
                  <a v-if="paper.url" class="paper-link" :href="paper.url" target="_blank" rel="noreferrer">
                    查看原文
                  </a>
                </article>
              </div>
              <div v-else class="empty-state">
                当前没有返回可展示的文献结果，可以稍后重试检索。
              </div>
            </section>
          </template>
        </div>

        <div v-else class="empty-state panel-empty">
          请选择一个地震事件，右侧将展示详情、相关文献和自动生成的科学总结。
        </div>
      </aside>
    </main>

    <div v-if="loading" class="loading-mask">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-shell {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  color: #1f2937;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(249, 115, 22, 0.12), transparent 28%),
    radial-gradient(circle at right center, rgba(14, 165, 233, 0.12), transparent 24%),
    #d9dce3;
}

.navbar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  padding: 0 24px 0 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.95);
  border-bottom: 1px solid rgba(148, 163, 184, 0.28);
  backdrop-filter: blur(18px);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  z-index: 1200;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.school-logo {
  width: auto;
  height: 38px;
}

.title-group h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #1e3a8a;
}

.title-group small {
  display: block;
  margin-top: 2px;
  color: #64748b;
  font-size: 11px;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
}

.nav-actions a,
.panel-toggle {
  color: #475569;
  text-decoration: none;
}

.panel-toggle {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: #fff;
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
}

.panel-toggle:hover {
  color: #0f172a;
  border-color: rgba(15, 23, 42, 0.16);
}

.live-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: #ecfdf5;
  color: #059669;
  font-size: 12px;
}

.workspace {
  position: absolute;
  top: 64px;
  right: 0;
  bottom: 0;
  left: 0;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 430px;
}

.workspace.detail-collapsed {
  grid-template-columns: 320px minmax(0, 1fr) 0;
}

.sidebar,
.detail-panel {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(18px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  z-index: 1050;
}

.sidebar {
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 10px 0 40px rgba(15, 23, 42, 0.06);
  transition: transform 0.3s ease;
}

.detail-panel {
  border-left: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: -10px 0 40px rgba(15, 23, 42, 0.06);
  transition: width 0.3s ease, opacity 0.3s ease;
}

.detail-panel.collapsed {
  width: 0;
  opacity: 0;
  pointer-events: none;
}

.sidebar.collapsed {
  transform: translateX(-100%);
}

.sidebar-toggle {
  position: absolute;
  top: 12px;
  left: 18px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  cursor: pointer;
  z-index: 1300;
}

.sidebar-toggle:hover {
  color: #0f172a;
}

.sidebar-header,
.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.sidebar-header h3,
.detail-header h3 {
  margin: 0;
  font-size: 18px;
}

.sidebar-header p,
.detail-header p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
}

.close-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.sidebar-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 18px;
}

.stat-card {
  padding: 10px 12px;
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.8));
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.stat-card strong {
  display: block;
  font-size: 18px;
  color: #0f172a;
}

.stat-card span {
  color: #64748b;
  font-size: 11px;
}

.quake-list,
.detail-content {
  flex: 1;
  overflow-y: auto;
}

.quake-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 18px;
  border: none;
  border-bottom: 1px solid rgba(241, 245, 249, 0.95);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.18s ease;
}

.quake-item:hover,
.quake-item.active {
  background: rgba(255, 255, 255, 0.75);
}

.quake-item.active {
  box-shadow: inset 3px 0 0 #0f766e;
}

.mag-badge {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 800;
  font-size: 14px;
  flex-shrink: 0;
}

.quake-info {
  min-width: 0;
}

.quake-info .place {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
  color: #0f172a;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.depth-tag,
.type-tag {
  padding: 2px 7px;
  border-radius: 999px;
  background: #eef2ff;
  color: #475569;
}

.map-stage {
  position: relative;
  min-width: 0;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
  background: #d5d9df;
}

.map-top-strip {
  position: absolute;
  top: 18px;
  left: 18px;
  right: 18px;
  display: flex;
  gap: 12px;
  z-index: 900;
  pointer-events: none;
}

.overlay-card {
  min-width: 160px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.1);
}

.overlay-card.selected {
  margin-left: auto;
  max-width: 300px;
}

.overlay-card strong {
  display: block;
  margin-top: 6px;
  font-size: 22px;
  color: #0f172a;
}

.overlay-card small,
.overlay-label {
  display: block;
  color: #64748b;
}

.overlay-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.legend-panel {
  position: absolute;
  right: 18px;
  bottom: 24px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.1);
  z-index: 900;
}

.legend-title {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
}

.legend-items {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #475569;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.detail-content {
  padding: 18px;
}

.detail-card,
.hero-card {
  margin-bottom: 16px;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.9));
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.06);
}

.hero-card h2 {
  margin: 14px 0 10px;
  font-size: 24px;
  line-height: 1.28;
}

.hero-card p {
  margin: 0;
  color: #64748b;
}

.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.hero-mag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 8px 14px;
  border-radius: 14px;
  color: #fff;
  font-weight: 800;
  font-size: 20px;
}

.hero-time {
  color: #64748b;
  font-size: 12px;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.chip-row.tight {
  margin-top: 10px;
}

.chip,
.topic-chip,
.source-chip,
.region-chip,
.query-chip,
.mode-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
}

.chip,
.query-chip {
  background: #eef2ff;
  color: #334155;
}

.topic-chip {
  background: #ecfeff;
  color: #0f766e;
}

.source-chip {
  background: #fff7ed;
  color: #c2410c;
}

.region-chip {
  background: #f1f5f9;
  color: #475569;
}

.mode-chip {
  background: #dcfce7;
  color: #166534;
  white-space: nowrap;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-kicker {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #94a3b8;
}

.section-head h4 {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
  color: #0f172a;
}

.summary-paragraph,
.hint-text,
.limit-text {
  margin: 0 0 14px;
  font-size: 14px;
  line-height: 1.72;
  color: #475569;
}

.limit-text {
  color: #64748b;
  font-size: 12px;
}

.article-card {
  background:
    linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(251, 248, 243, 0.94));
}

.article-header h4 {
  margin: 0;
  font-size: 22px;
  line-height: 1.45;
  color: #111827;
}

.article-subtitle {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.8;
  color: #4b5563;
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.article-meta span,
.abstract-label,
.evidence-label {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.1);
  color: #64748b;
  font-size: 11px;
  letter-spacing: 0.04em;
}

.article-abstract {
  margin-top: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(180, 83, 9, 0.12);
  background: rgba(255, 247, 237, 0.7);
}

.article-abstract p {
  margin: 10px 0 0;
  color: #374151;
  line-height: 1.9;
  font-size: 14px;
}

.report-article {
  margin-top: 18px;
  padding: 22px 22px 8px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.report-section {
  position: relative;
  margin-bottom: 22px;
  padding-left: 18px;
  border-left: 3px solid rgba(249, 115, 22, 0.24);
  font-family: 'Songti SC', 'STSong', 'Noto Serif SC', serif;
}

.report-section h5 {
  margin: 0 0 12px;
  font-size: 18px;
  line-height: 1.5;
  color: #7c2d12;
}

.report-section p {
  margin: 0 0 12px;
  color: #1f2937;
  font-size: 15px;
  line-height: 2;
  text-align: justify;
}

.evidence-gallery {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.evidence-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.42);
}

.evidence-card h5,
.info-group h5,
.paper-card h5 {
  margin: 0 0 10px;
  font-size: 14px;
}

.evidence-card p,
.note-item,
.paper-abstract,
.paper-evidence,
.paper-authors,
.paper-venue {
  margin: 0 0 10px;
  font-size: 13px;
  line-height: 1.65;
  color: #475569;
}

.evidence-card small {
  color: #9a3412;
  font-size: 12px;
}

.article-closing {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
}

.article-closing h5 {
  margin: 0 0 10px;
  color: #f8fafc;
  font-size: 16px;
}

.article-closing p {
  margin: 0 0 10px;
  color: rgba(248, 250, 252, 0.9);
  font-size: 14px;
  line-height: 1.85;
}

.article-closing .limit-text {
  margin-bottom: 0;
  color: rgba(226, 232, 240, 0.78);
}

.note-item:last-child,
.paper-evidence:last-child {
  margin-bottom: 0;
}

.detail-grid,
.cohort-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  padding: 12px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.metric span {
  display: block;
  color: #64748b;
  font-size: 11px;
  margin-bottom: 6px;
}

.metric strong {
  color: #0f172a;
  font-size: 14px;
  line-height: 1.4;
  word-break: break-word;
}

.info-group {
  margin-top: 16px;
}

.query-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.paper-count {
  color: #64748b;
  font-size: 12px;
}

.paper-list {
  display: grid;
  gap: 14px;
}

.paper-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(255, 255, 255, 0.94);
}

.paper-card h5 {
  margin: 10px 0 8px;
  font-size: 16px;
  line-height: 1.45;
  color: #0f172a;
}

.paper-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #64748b;
  font-size: 11px;
}

.paper-source {
  color: #0f766e;
  font-weight: 700;
}

.paper-link {
  color: #0f766e;
  font-weight: 700;
  text-decoration: none;
}

.paper-link:hover {
  text-decoration: underline;
}

.empty-state {
  padding: 18px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.9);
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.panel-empty {
  margin: 18px;
}

.loading-card {
  display: grid;
  gap: 10px;
}

.skeleton-line {
  height: 14px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(226, 232, 240, 0.8), rgba(241, 245, 249, 1), rgba(226, 232, 240, 0.8));
  background-size: 240% 100%;
  animation: shimmer 1.4s linear infinite;
}

.skeleton-line.wide {
  width: 96%;
}

.skeleton-line.short {
  width: 54%;
}

.error-card {
  border-color: rgba(248, 113, 113, 0.18);
  background: rgba(254, 242, 242, 0.92);
}

.error-card h4 {
  margin: 0 0 8px;
  color: #991b1b;
}

.error-card p {
  margin: 0;
  color: #7f1d1d;
  font-size: 13px;
  line-height: 1.65;
}

.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.82);
  z-index: 1600;
}

.spinner {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 4px solid rgba(148, 163, 184, 0.22);
  border-top-color: #0f766e;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.blink {
  animation: blink 1.2s infinite;
}

:deep(.label-layer-filter) {
  filter: contrast(0.85);
}

:deep(.leaflet-popup-content-wrapper) {
  border-radius: 18px;
  padding: 0;
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.18);
}

:deep(.leaflet-popup-content) {
  margin: 0;
}

:deep(.leaflet-popup-tip) {
  background: rgba(255, 255, 255, 0.98);
}

:deep(.leaflet-popup-close-button) {
  top: 10px !important;
  right: 10px !important;
  color: #94a3b8 !important;
  font-size: 18px !important;
}

:deep(.popup-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 38px 12px 14px;
  background: rgba(248, 250, 252, 0.96);
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

:deep(.mag-tag) {
  color: #fff;
  padding: 4px 8px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
}

:deep(.popup-header .time) {
  color: #64748b;
  font-size: 12px;
  font-family: monospace;
}

:deep(.popup-body) {
  padding: 14px;
  color: #334155;
}

:deep(.popup-place) {
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.45;
  color: #0f172a;
}

:deep(.popup-grid) {
  display: grid;
  gap: 6px;
}

:deep(.popup-grid .row) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
}

:deep(.popup-grid .row span) {
  color: #64748b;
}

:deep(.popup-grid .row strong) {
  color: #334155;
  text-align: right;
}

:deep(.id-row) {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(148, 163, 184, 0.18);
  color: #94a3b8;
  font-size: 11px;
}

@media (max-width: 1360px) {
  .workspace,
  .workspace.detail-collapsed {
    grid-template-columns: 300px minmax(0, 1fr);
  }

  .detail-panel {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(420px, 100%);
    z-index: 1150;
  }

  .detail-panel.collapsed {
    transform: translateX(100%);
    width: min(420px, 100%);
    opacity: 1;
  }
}

@media (max-width: 1100px) {
  .map-top-strip {
    right: 90px;
    flex-wrap: wrap;
  }

  .overlay-card.selected {
    margin-left: 0;
  }

  .detail-panel {
    width: min(100%, 460px);
  }
}

@media (max-width: 768px) {
  .navbar {
    padding-right: 14px;
    padding-left: 70px;
  }

  .nav-actions {
    gap: 10px;
    font-size: 12px;
  }

  .desktop-only,
  .nav-actions a:last-child,
  .legend-panel {
    display: none;
  }

  .workspace,
  .workspace.detail-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }

  .sidebar {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(88vw, 320px);
    z-index: 1250;
  }

  .detail-panel {
    top: auto;
    height: min(60vh, 560px);
    width: 100%;
    bottom: 0;
    border-left: none;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 26px 26px 0 0;
  }

  .detail-panel.collapsed {
    transform: translateY(100%);
    width: 100%;
  }

  .map-top-strip {
    left: 14px;
    right: 14px;
    top: 14px;
    gap: 10px;
  }

  .overlay-card {
    min-width: 0;
    flex: 1 1 0;
  }

  .sidebar-stats,
  .detail-grid,
  .cohort-grid {
    grid-template-columns: 1fr;
  }
}
</style>
