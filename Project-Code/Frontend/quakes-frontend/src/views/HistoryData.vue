<template>
  <div class="history-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">历史查询工作台</p>
        <h1>历史地震数据查询</h1>
        <p class="subtitle">查询、筛选、联动地图，并快速查看关键统计与事件详情。</p>
      </div>
      <router-link class="back-link" to="/dashboard">返回总览</router-link>
    </header>

    <section class="panel card">
      <div class="panel-head">
        <div>
          <h2>查询条件</h2>
          <p>支持时间、震级、深度和空间范围组合检索，输入 `0` 也会被正确保留。</p>
        </div>
        <div class="quick-actions">
          <button type="button" class="ghost-btn" @click="applyQuickHours(24)">近 24 小时</button>
          <button type="button" class="ghost-btn" @click="applyQuickHours(72)">近 72 小时</button>
          <button type="button" class="ghost-btn" @click="applyQuickHours(168)">近 7 天</button>
        </div>
      </div>

      <div class="query-state">
        <div class="state-copy">
          <strong>当前模式</strong>
          <p>{{ queryModeText }}</p>
        </div>
        <div class="active-filters">
          <span v-for="chip in activeFilterChips" :key="chip" class="filter-chip">{{ chip }}</span>
          <span v-if="!activeFilterChips.length" class="filter-chip filter-chip-muted">默认：近 24 小时，M3.0 以上</span>
        </div>
      </div>

      <form class="query-grid" @submit.prevent="runQuery(true)">
        <label class="field">
          <span>开始时间</span>
          <input v-model="filters.start" class="control" type="datetime-local" />
        </label>
        <label class="field">
          <span>结束时间</span>
          <input v-model="filters.end" class="control" type="datetime-local" />
        </label>
        <label class="field">
          <span>结果上限</span>
          <input v-model="filters.limit" class="control" type="number" min="1" max="20000" step="100" />
        </label>
        <label class="field">
          <span>时间窗口（小时）</span>
          <input v-model="filters.hours" class="control" type="number" min="1" max="168" />
        </label>

        <label class="field">
          <span>最小震级</span>
          <input v-model="filters.minMag" class="control" type="number" step="0.1" />
        </label>
        <label class="field">
          <span>最大震级</span>
          <input v-model="filters.maxMag" class="control" type="number" step="0.1" />
        </label>
        <label class="field">
          <span>最小深度（km）</span>
          <input v-model="filters.minDepth" class="control" type="number" step="0.1" />
        </label>
        <label class="field">
          <span>最大深度（km）</span>
          <input v-model="filters.maxDepth" class="control" type="number" step="0.1" />
        </label>

        <label class="field">
          <span>最小经度</span>
          <input v-model="filters.minLon" class="control" type="number" step="0.0001" />
        </label>
        <label class="field">
          <span>最大经度</span>
          <input v-model="filters.maxLon" class="control" type="number" step="0.0001" />
        </label>
        <label class="field">
          <span>最小纬度</span>
          <input v-model="filters.minLat" class="control" type="number" step="0.0001" />
        </label>
        <label class="field">
          <span>最大纬度</span>
          <input v-model="filters.maxLat" class="control" type="number" step="0.0001" />
        </label>

        <div class="form-footer">
          <p class="helper">{{ queryHint }}</p>
          <p v-if="inlineQueryMessage" class="query-feedback" :class="{ error: Boolean(errorMessage) }">
            {{ inlineQueryMessage }}
          </p>
          <div class="footer-actions">
            <button type="button" class="ghost-btn" :disabled="!mapReady" @click="useMapBounds">使用当前视野</button>
            <button type="button" class="ghost-btn" @click="clearTimeRange">清空时间</button>
            <button type="button" class="ghost-btn" @click="clearSpatialRange">清空空间</button>
            <button type="button" class="ghost-btn" @click="resetFilters">重置</button>
            <button type="submit" class="primary-btn" :disabled="loading">
              {{ loading ? '查询中…' : '执行查询' }}
            </button>
          </div>
        </div>
      </form>
    </section>

    <section class="overview-grid">
      <article v-for="card in overviewCards" :key="card.label" class="overview-card card">
        <p class="card-label">{{ card.label }}</p>
        <strong class="card-value">{{ card.value }}</strong>
        <span class="card-note">{{ card.note }}</span>
      </article>
    </section>

    <section class="workspace-grid">
      <div class="workspace-main">
        <section class="card results-card">
          <div class="results-head">
            <div>
              <h2>结果列表</h2>
              <p>{{ resultsSummary }}</p>
            </div>
            <div class="results-actions">
              <label class="map-style-switch">
                <span>底图</span>
                <select v-model="mapTheme" class="control control-select">
                  <option value="light">浅色底图</option>
                  <option value="terrain">地形底图</option>
                </select>
              </label>
              <button type="button" class="ghost-btn" :disabled="!selectedEvent" @click="focusSelected">
                聚焦当前事件
              </button>
              <button type="button" class="ghost-btn" :disabled="!activeEvents.length" @click="focusResults">
                聚焦结果范围
              </button>
              <button type="button" class="ghost-btn" :disabled="!activeEvents.length" @click="exportResultsCsv">
                导出 CSV
              </button>
            </div>
          </div>

          <div v-if="hasSearched" class="pagination-bar">
            <span>第 {{ currentPage }} / {{ totalPages }} 页，共 {{ totalResults }} 条</span>
            <div class="pagination-actions">
              <button type="button" class="ghost-btn" :disabled="loading || currentPage <= 1" @click="goToPreviousPage">
                上一页
              </button>
              <button type="button" class="ghost-btn" :disabled="loading || !hasMoreResults" @click="goToNextPage">
                下一页
              </button>
            </div>
          </div>
          <div v-else class="preview-banner">
            <strong>历史地震速览</strong>
            <span>尚未执行自定义查询，先展示近一年较强历史地震样本，方便直接浏览和联动地图。</span>
          </div>

          <div v-if="loading || previewLoading" class="feedback-block loading-state">
            <div class="spinner"></div>
            <p>{{ hasSearched ? '正在查询并同步地图结果…' : '正在加载历史地震速览…' }}</p>
          </div>

          <div v-else-if="errorMessage || previewError" class="feedback-block error-state">
            <p>{{ errorMessage || previewError }}</p>
          </div>

          <div v-else-if="!activeEvents.length" class="feedback-block empty-state">
            <p>{{ hasSearched ? '没有匹配到事件，试着放宽震级或空间范围。' : '还没有查询结果，先执行一次查询。' }}</p>
          </div>

          <template v-else>
            <div :key="resultsRenderKey" class="table-shell">
              <table class="results-table">
                <thead>
                  <tr>
                    <th>事件</th>
                    <th>
                      <button type="button" class="sort-btn" @click="toggleSort('time')">
                        时间 {{ sortIndicator('time') }}
                      </button>
                    </th>
                    <th>
                      <button type="button" class="sort-btn" @click="toggleSort('mag')">
                        震级 {{ sortIndicator('mag') }}
                      </button>
                    </th>
                    <th>
                      <button type="button" class="sort-btn" @click="toggleSort('depth_km')">
                        深度 {{ sortIndicator('depth_km') }}
                      </button>
                    </th>
                    <th>位置</th>
                    <th>坐标</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="event in sortedEvents"
                    :key="event.id"
                    :class="{ selected: event.id === selectedEventId }"
                    @click="selectEvent(event.id, { center: false })"
                  >
                    <td>
                      <div class="event-cell">
                        <span class="mag-pill" :class="magnitudeClass(event.mag)">M{{ formatNumber(event.mag, 1) }}</span>
                        <div>
                          <strong>{{ shortPlace(event.place) }}</strong>
                          <small>{{ event.id }}</small>
                        </div>
                      </div>
                    </td>
                    <td class="mono">{{ formatDateTime(event.time) }}</td>
                    <td>{{ formatNumber(event.mag, 1) }}</td>
                    <td>{{ formatDepth(event.depth_km) }}</td>
                    <td>{{ event.place || '未知位置' }}</td>
                    <td class="mono">{{ formatCoordinate(event.lat, event.lon) }}</td>
                    <td>
                      <div class="row-actions" @click.stop>
                        <button type="button" class="tiny-btn" @click="selectEvent(event.id, { center: false })">详情</button>
                        <button type="button" class="tiny-btn" @click="copyEventId(event.id)">复制 ID</button>
                        <button type="button" class="tiny-btn" @click="selectEvent(event.id, { center: true })">定位</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </section>

        <section class="card map-card">
          <div class="map-head">
            <div>
              <h2>地图联动</h2>
              <p>支持表格选中高亮、点击地图反选表格、结果自动缩放。</p>
            </div>
            <span class="map-status">{{ mapStatus }}</span>
          </div>
          <div ref="mapEl" class="map-panel"></div>
        </section>
      </div>

      <aside class="card detail-card">
        <div class="detail-head">
          <h2>事件详情</h2>
          <p>{{ selectedEvent ? '已选中事件，支持复制与快速定位。' : '从列表或地图选择一个事件查看摘要。' }}</p>
          <span class="detail-meta">{{ selectedCountText }}</span>
        </div>

        <div v-if="selectedEvent" class="detail-body">
          <div class="detail-topline">
            <span class="mag-pill" :class="magnitudeClass(selectedEvent.mag)">
              M{{ formatNumber(selectedEvent.mag, 1) }}
            </span>
            <button type="button" class="ghost-btn" @click="copyEventId(selectedEvent.id)">复制事件 ID</button>
          </div>

          <h3>{{ selectedEvent.place || '未知位置' }}</h3>
          <p class="detail-summary">{{ detailSummary }}</p>

          <dl class="detail-grid">
            <div>
              <dt>事件 ID</dt>
              <dd class="mono">{{ selectedEvent.id }}</dd>
            </div>
            <div>
              <dt>发生时间</dt>
              <dd>{{ formatDateTime(selectedEvent.time) }}</dd>
            </div>
            <div>
              <dt>更新时间</dt>
              <dd>{{ formatDateTime(selectedEvent.updated) }}</dd>
            </div>
            <div>
              <dt>深度</dt>
              <dd>{{ formatDepth(selectedEvent.depth_km) }}</dd>
            </div>
            <div>
              <dt>震源网络</dt>
              <dd>{{ selectedEvent.net || '-' }}</dd>
            </div>
            <div>
              <dt>类型</dt>
              <dd>{{ selectedEvent.type || '-' }}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{{ selectedEvent.status || '-' }}</dd>
            </div>
            <div>
              <dt>坐标</dt>
              <dd class="mono">{{ formatCoordinate(selectedEvent.lat, selectedEvent.lon) }}</dd>
            </div>
          </dl>

          <div class="detail-actions">
            <button type="button" class="primary-btn" @click="selectEvent(selectedEvent.id, { center: true })">地图定位</button>
            <button type="button" class="ghost-btn" @click="clearSelection">取消选中</button>
          </div>
        </div>

        <div v-else class="feedback-block detail-empty">
          <p>选择一条事件后，这里会展示摘要、事件 ID、时间和快速操作。</p>
        </div>

        <p v-if="copyMessage" class="copy-feedback">{{ copyMessage }}</p>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { apiUrl } from '../config/api'

type SortKey = 'time' | 'mag' | 'depth_km'
type MapTheme = 'light' | 'terrain'

type EventItem = {
  id: string
  time: string
  updated: string
  mag: number | null
  place: string | null
  depth_km: number | null
  lon: number
  lat: number
  net?: string | null
  type?: string | null
  status?: string | null
}

type EventsPageResponse = {
  items: EventItem[]
  total: number
  limit: number
  offset: number
  hasMore: boolean
}

type NumericFilterKey =
  | 'hours'
  | 'limit'
  | 'minMag'
  | 'maxMag'
  | 'minDepth'
  | 'maxDepth'
  | 'minLon'
  | 'maxLon'
  | 'minLat'
  | 'maxLat'

const TILE_THEMES: Record<MapTheme, { base: string; attribution: string }> = {
  light: {
    base: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Esri, AutoNavi',
  },
  terrain: {
    base: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: 'OpenTopoMap, OpenStreetMap contributors',
  },
}

const LABEL_TILE = 'https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'

const DEFAULT_FILTERS = {
  start: '',
  end: '',
  hours: '24',
  limit: '5000',
  minMag: '3',
  maxMag: '',
  minDepth: '',
  maxDepth: '',
  minLon: '',
  maxLon: '',
  minLat: '',
  maxLat: '',
}

const route = useRoute()
const router = useRouter()
const filters = reactive({ ...DEFAULT_FILTERS })
const events = ref<EventItem[]>([])
const previewEvents = ref<EventItem[]>([])
const loading = ref(false)
const previewLoading = ref(false)
const hasSearched = ref(false)
const errorMessage = ref('')
const previewError = ref('')
const selectedEventId = ref<string | null>(null)
const copyMessage = ref('')
const mapReady = ref(false)
const totalResults = ref(0)
const resultOffset = ref(0)
const hasMoreResults = ref(false)
const mapTheme = ref<MapTheme>('light')
const sortKey = ref<SortKey>('time')
const sortDirection = ref<'asc' | 'desc'>('desc')
const resultsRenderKey = ref(0)

const mapEl = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
let markersLayer: L.LayerGroup | null = null
let baseLayer: L.TileLayer | null = null
let labelLayer: L.TileLayer | null = null
let markerIndex = new Map<string, L.CircleMarker>()
let pendingBoundsFit = false
let boundsFitReason = ''
let copyTimeout: ReturnType<typeof setTimeout> | null = null

const activeEvents = computed(() => (hasSearched.value ? events.value : previewEvents.value))
const selectedEvent = computed(() => activeEvents.value.find((item) => item.id === selectedEventId.value) ?? null)

const overview = computed(() => {
  const total = activeEvents.value.length
  const mags = activeEvents.value.map((item) => item.mag).filter((value): value is number => value !== null)
  const depths = activeEvents.value.map((item) => item.depth_km).filter((value): value is number => value !== null)
  const latest = activeEvents.value
    .map((item) => Date.parse(item.time))
    .filter((value) => Number.isFinite(value))
    .sort((a, b) => b - a)[0]

  const maxMag = mags.length ? Math.max(...mags) : null
  const avgDepth = depths.length ? depths.reduce((sum, value) => sum + value, 0) / depths.length : null

  return {
    total,
    maxMag,
    avgDepth,
    latest,
  }
})

const overviewCards = computed(() => [
  {
    label: '总事件数',
    value: String(overview.value.total),
    note: hasSearched.value ? '当前查询命中数量' : '历史速览样本数量',
  },
  {
    label: '最大震级',
    value: overview.value.maxMag === null ? '-' : `M${formatNumber(overview.value.maxMag, 1)}`,
    note: '当前结果中的峰值事件',
  },
  {
    label: '平均深度',
    value: overview.value.avgDepth === null ? '-' : `${formatNumber(overview.value.avgDepth, 1)} km`,
    note: '仅统计有深度数据的事件',
  },
  {
    label: '最新事件时间',
    value: overview.value.latest ? formatDateTime(new Date(overview.value.latest).toISOString()) : '-',
    note: '用于快速判断结果时效性',
  },
])

const sortedEvents = computed(() => {
  const factor = sortDirection.value === 'asc' ? 1 : -1
  return [...activeEvents.value].sort((a, b) => {
    if (sortKey.value === 'time') {
      return (Date.parse(a.time) - Date.parse(b.time)) * factor
    }
    const aValue = a[sortKey.value] ?? Number.NEGATIVE_INFINITY
    const bValue = b[sortKey.value] ?? Number.NEGATIVE_INFINITY
    return ((aValue as number) - (bValue as number)) * factor
  })
})

const resultsSummary = computed(() => {
  if (!hasSearched.value) {
    return activeEvents.value.length
      ? `当前展示 ${activeEvents.value.length} 条历史地震速览，可直接点击查看详情或定位。`
      : '执行查询后会在这里展示可交互结果。'
  }
  if (!activeEvents.value.length) return '当前条件没有返回任何事件。'
  return `本页 ${activeEvents.value.length} 条，累计命中 ${totalResults.value} 条，点击行或地图点可联动详情面板。`
})

const queryHint = computed(() => {
  if (filters.start || filters.end) {
    return '已使用明确起止时间，小时窗口将作为缺省补全。'
  }
  return '未填写起止时间时，将按小时窗口回溯查询。'
})

const inlineQueryMessage = computed(() => {
  if (loading.value) {
    return '正在提交查询，请稍候…'
  }
  if (errorMessage.value) {
    return errorMessage.value
  }
  if (hasSearched.value && activeEvents.value.length) {
    return `查询完成：本页返回 ${activeEvents.value.length} 条结果。`
  }
  return ''
})

const detailSummary = computed(() => {
  if (!selectedEvent.value) return ''
  const event = selectedEvent.value
  return `${formatDateTime(event.time)} 发生于 ${event.place || '未知区域'}，震级 ${formatNumber(event.mag, 1)}，深度 ${formatDepth(event.depth_km)}。`
})

const mapStatus = computed(() => {
  if (!activeEvents.value.length) return '等待结果'
  if (selectedEvent.value) return `已高亮 ${selectedEvent.value.id}`
  return '地图已与结果同步'
})

const hasExplicitTimeRange = computed(() => Boolean(filters.start || filters.end))

const queryModeText = computed(() => {
  if (hasExplicitTimeRange.value) {
    return '当前使用明确起止时间查询；若只填写一端，系统会用小时窗口补全另一端。'
  }
  return `当前使用回溯窗口查询，向前追溯 ${filters.hours || '24'} 小时。`
})

const selectedCountText = computed(() => {
  if (!activeEvents.value.length) return '暂无结果'
  if (!selectedEvent.value) return `共 ${activeEvents.value.length} 条结果`
  return `已选中 1 条，结果总数 ${activeEvents.value.length}`
})

const pageSize = computed(() => Number(filters.limit || '200') || 200)
const currentPage = computed(() => Math.floor(resultOffset.value / pageSize.value) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil(totalResults.value / pageSize.value)))

const activeFilterChips = computed(() => {
  const chips: string[] = []

  if (filters.start) chips.push(`开始 ${filters.start.replace('T', ' ')}`)
  if (filters.end) chips.push(`结束 ${filters.end.replace('T', ' ')}`)
  if (!filters.start && !filters.end && filters.hours) chips.push(`时间窗口 ${filters.hours}h`)
  if (filters.minMag) chips.push(`最小震级 ${filters.minMag}`)
  if (filters.maxMag) chips.push(`最大震级 ${filters.maxMag}`)
  if (filters.minDepth) chips.push(`最小深度 ${filters.minDepth} km`)
  if (filters.maxDepth) chips.push(`最大深度 ${filters.maxDepth} km`)

  const lonReady = filters.minLon && filters.maxLon
  const latReady = filters.minLat && filters.maxLat
  if (lonReady && latReady) {
    chips.push(`空间范围 ${filters.minLon},${filters.minLat} ~ ${filters.maxLon},${filters.maxLat}`)
  } else {
    if (filters.minLon) chips.push(`最小经度 ${filters.minLon}`)
    if (filters.maxLon) chips.push(`最大经度 ${filters.maxLon}`)
    if (filters.minLat) chips.push(`最小纬度 ${filters.minLat}`)
    if (filters.maxLat) chips.push(`最大纬度 ${filters.maxLat}`)
  }

  if (filters.limit) chips.push(`上限 ${filters.limit}`)
  return chips
})

function normalizeNumber(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function normalizeDateTime(value: string): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toISOString()
}

function buildQueryParams() {
  const params = new URLSearchParams()
  const numericKeys: NumericFilterKey[] = [
    'hours',
    'limit',
    'minMag',
    'maxMag',
    'minDepth',
    'maxDepth',
    'minLon',
    'maxLon',
    'minLat',
    'maxLat',
  ]

  for (const key of numericKeys) {
    const normalized = normalizeNumber(filters[key])
    if (normalized !== null) {
      params.set(key, normalized)
    }
  }

  const start = normalizeDateTime(filters.start)
  const end = normalizeDateTime(filters.end)
  if (start) params.set('start', start)
  if (end) params.set('end', end)

  return params
}

function syncFiltersFromRoute() {
  const query = route.query
  for (const key of Object.keys(DEFAULT_FILTERS) as Array<keyof typeof DEFAULT_FILTERS>) {
    const rawValue = query[key]
    filters[key] = typeof rawValue === 'string' ? rawValue : DEFAULT_FILTERS[key]
  }
}

function syncRouteFromFilters() {
  const nextQuery: Record<string, string> = {}
  for (const key of Object.keys(DEFAULT_FILTERS) as Array<keyof typeof DEFAULT_FILTERS>) {
    const value = filters[key].trim()
    if (value && value !== DEFAULT_FILTERS[key]) {
      nextQuery[key] = value
    }
  }
  if (resultOffset.value > 0) {
    nextQuery.offset = String(resultOffset.value)
  }
  void router.replace({ query: nextQuery })
}

function parseOptionalNumber(value: string): number | null {
  const normalized = normalizeNumber(value)
  if (normalized === null) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function validateFilters(): string | null {
  const start = normalizeDateTime(filters.start)
  const end = normalizeDateTime(filters.end)
  if ((filters.start && !start) || (filters.end && !end)) {
    return '时间格式无效，请重新选择开始或结束时间。'
  }
  if (start && end && Date.parse(start) > Date.parse(end)) {
    return '开始时间不能晚于结束时间。'
  }

  const minMag = parseOptionalNumber(filters.minMag)
  const maxMag = parseOptionalNumber(filters.maxMag)
  if (minMag !== null && maxMag !== null && minMag > maxMag) {
    return '最小震级不能大于最大震级。'
  }

  const minDepth = parseOptionalNumber(filters.minDepth)
  const maxDepth = parseOptionalNumber(filters.maxDepth)
  if (minDepth !== null && maxDepth !== null && minDepth > maxDepth) {
    return '最小深度不能大于最大深度。'
  }

  const minLon = parseOptionalNumber(filters.minLon)
  const maxLon = parseOptionalNumber(filters.maxLon)
  if (minLon !== null && maxLon !== null && minLon > maxLon) {
    return '最小经度不能大于最大经度。'
  }

  const minLat = parseOptionalNumber(filters.minLat)
  const maxLat = parseOptionalNumber(filters.maxLat)
  if (minLat !== null && maxLat !== null && minLat > maxLat) {
    return '最小纬度不能大于最大纬度。'
  }

  const someLon = minLon !== null || maxLon !== null
  const someLat = minLat !== null || maxLat !== null
  if (someLon !== someLat) {
    return '空间筛选请同时填写经度和纬度范围，或全部留空。'
  }

  return null
}

async function runQuery(resetOffset = false) {
  const validationError = validateFilters()
  if (validationError) {
    errorMessage.value = validationError
    hasSearched.value = true
    events.value = []
    selectedEventId.value = null
    totalResults.value = 0
    hasMoreResults.value = false
    return
  }

  if (resetOffset) {
    resultOffset.value = 0
  }
  syncRouteFromFilters()

  loading.value = true
  errorMessage.value = ''
  hasSearched.value = true
  events.value = []
  selectedEventId.value = null
  totalResults.value = 0
  hasMoreResults.value = false

  try {
    const params = buildQueryParams()
    params.set('offset', String(resultOffset.value))
    const response = await fetch(`${apiUrl('/events/search')}?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`查询失败（${response.status}）`)
    }
    const data = (await response.json()) as EventsPageResponse
    events.value = data.items
    totalResults.value = data.total
    hasMoreResults.value = data.hasMore
    selectedEventId.value = data.items[0]?.id ?? null
    resultsRenderKey.value += 1
    requestResultsFit('query')
  } catch (error) {
    events.value = []
    selectedEventId.value = null
    totalResults.value = 0
    hasMoreResults.value = false
    errorMessage.value = error instanceof Error ? error.message : '查询失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

async function loadPreview() {
  previewLoading.value = true
  previewError.value = ''
  try {
    const end = new Date()
    const start = new Date(end)
    start.setUTCFullYear(end.getUTCFullYear() - 1)
    const params = new URLSearchParams({
      start: start.toISOString(),
      end: end.toISOString(),
      minMag: '5.0',
      limit: '12',
    })
    const response = await fetch(`${apiUrl('/events')}?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`历史速览加载失败（${response.status}）`)
    }
    const data = (await response.json()) as EventItem[]
    previewEvents.value = data
    if (!selectedEventId.value) {
      selectedEventId.value = data[0]?.id ?? null
    }
    requestResultsFit('preview')
  } catch (error) {
    previewEvents.value = []
    previewError.value = error instanceof Error ? error.message : '历史速览加载失败，请稍后重试。'
  } finally {
    previewLoading.value = false
  }
}

function applyQuickHours(hours: number) {
  filters.start = ''
  filters.end = ''
  filters.hours = String(hours)
  void runQuery(true)
}

function clearTimeRange() {
  filters.start = ''
  filters.end = ''
}

function clearSpatialRange() {
  filters.minLon = ''
  filters.maxLon = ''
  filters.minLat = ''
  filters.maxLat = ''
}

function resetFilters() {
  Object.assign(filters, DEFAULT_FILTERS)
  events.value = []
  selectedEventId.value = null
  hasSearched.value = false
  errorMessage.value = ''
  totalResults.value = 0
  resultOffset.value = 0
  hasMoreResults.value = false
  clearCopyMessage()
  requestResultsFit('reset')
  void loadPreview()
}

function goToPreviousPage() {
  if (currentPage.value <= 1) return
  resultOffset.value = Math.max(0, resultOffset.value - pageSize.value)
  void runQuery()
}

function goToNextPage() {
  if (!hasMoreResults.value) return
  resultOffset.value += pageSize.value
  void runQuery()
}

function toggleSort(nextKey: SortKey) {
  if (sortKey.value === nextKey) {
    sortDirection.value = sortDirection.value === 'desc' ? 'asc' : 'desc'
    return
  }
  sortKey.value = nextKey
  sortDirection.value = nextKey === 'time' ? 'desc' : 'asc'
}

function sortIndicator(key: SortKey) {
  if (sortKey.value !== key) return ''
  return sortDirection.value === 'desc' ? '↓' : '↑'
}

function selectEvent(eventId: string, options: { center: boolean }) {
  selectedEventId.value = eventId
  updateMarkerStyles()
  if (options.center) {
    focusEvent(eventId)
  }
}

function clearSelection() {
  selectedEventId.value = null
  updateMarkerStyles()
}

async function copyEventId(eventId: string) {
  try {
    await navigator.clipboard.writeText(eventId)
    copyMessage.value = `已复制事件 ID：${eventId}`
  } catch {
    copyMessage.value = `复制失败，请手动复制：${eventId}`
  }
  clearCopyMessage()
}

function clearCopyMessage() {
  if (copyTimeout) clearTimeout(copyTimeout)
  copyTimeout = setTimeout(() => {
    copyMessage.value = ''
  }, 1800)
}

function focusEvent(eventId: string) {
  const event = activeEvents.value.find((item) => item.id === eventId)
  if (!event || !map) return
  map.flyTo([event.lat, event.lon], Math.max(map.getZoom(), 5), { duration: 0.8 })
}

function focusResults() {
  requestResultsFit('manual')
}

function focusSelected() {
  if (!selectedEventId.value) return
  focusEvent(selectedEventId.value)
}

function useMapBounds() {
  if (!map) return
  const bounds = map.getBounds()
  filters.minLon = bounds.getWest().toFixed(4)
  filters.maxLon = bounds.getEast().toFixed(4)
  filters.minLat = bounds.getSouth().toFixed(4)
  filters.maxLat = bounds.getNorth().toFixed(4)
}

function exportResultsCsv() {
  if (!activeEvents.value.length) return

  const headers = ['id', 'time', 'updated', 'mag', 'depth_km', 'place', 'lat', 'lon', 'net', 'type', 'status']
  const rows = sortedEvents.value.map((event) =>
    [
      event.id,
      event.time,
      event.updated,
      event.mag ?? '',
      event.depth_km ?? '',
      event.place ?? '',
      event.lat,
      event.lon,
      event.net ?? '',
      event.type ?? '',
      event.status ?? '',
    ]
      .map((value) => csvEscape(String(value)))
      .join(','),
  )

  const blob = new Blob(['\uFEFF' + [headers.join(','), ...rows].join('\n')], {
    type: 'text/csv;charset=utf-8;',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `earthquakes-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  copyMessage.value = `已导出 ${activeEvents.value.length} 条结果为 CSV`
  clearCopyMessage()
}

function csvEscape(value: string) {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

function requestResultsFit(reason: string) {
  pendingBoundsFit = true
  boundsFitReason = reason
  nextTick(() => fitResultsBoundsIfNeeded())
}

function fitResultsBoundsIfNeeded() {
  if (!pendingBoundsFit || !map) return
  pendingBoundsFit = false

  const sourceEvents = activeEvents.value

  if (!sourceEvents.length) {
    if (boundsFitReason === 'reset' || boundsFitReason === 'preview') {
      map.setView([25, 105], 2)
    }
    return
  }

  const bounds = L.latLngBounds(sourceEvents.map((item) => [item.lat, item.lon] as [number, number]))
  if (!bounds.isValid()) return

  if (sourceEvents.length === 1) {
    const only = sourceEvents[0]
    map.flyTo([only.lat, only.lon], Math.max(map.getZoom(), 5), { duration: 0.8 })
    return
  }

  map.fitBounds(bounds.pad(0.22), { animate: true, duration: 0.8 })
}

function shortPlace(place: string | null) {
  if (!place) return '未知位置'
  return place.length > 30 ? `${place.slice(0, 30)}…` : place
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  }).format(date).replace(/\//g, '-')
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return value.toFixed(digits)
}

function formatDepth(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${value.toFixed(1)} km`
}

function formatCoordinate(lat: number | null | undefined, lon: number | null | undefined) {
  if (lat === null || lon === null || lat === undefined || lon === undefined) return '-'
  return `${lat.toFixed(3)}, ${lon.toFixed(3)}`
}

function magnitudeClass(mag: number | null) {
  if ((mag ?? 0) >= 6) return 'high'
  if ((mag ?? 0) >= 5) return 'medium'
  return 'low'
}

function createMarker(event: EventItem) {
  const marker = L.circleMarker([event.lat, event.lon], markerStyle(event.id === selectedEventId.value, event.mag))
  marker.on('click', () => {
    selectedEventId.value = event.id
    updateMarkerStyles()
  })
  marker.bindTooltip(`${event.id} | M${formatNumber(event.mag, 1)}`, {
    direction: 'top',
    offset: [0, -6],
    opacity: 0.95,
  })
  return marker
}

function markerStyle(selected: boolean, mag: number | null): L.CircleMarkerOptions {
  const radiusBase = Math.max(5, (mag ?? 0) * 2 + 3)
  const fillColor = (mag ?? 0) >= 6 ? '#c2410c' : (mag ?? 0) >= 5 ? '#d97706' : '#0f766e'
  return {
    radius: selected ? radiusBase + 3 : radiusBase,
    color: selected ? '#111827' : '#ffffff',
    weight: selected ? 2.5 : 1.4,
    fillColor,
    fillOpacity: selected ? 0.95 : 0.78,
  }
}

function renderMarkers() {
  if (!map || !markersLayer) return
  markersLayer.clearLayers()
  markerIndex = new Map()

  for (const event of activeEvents.value) {
    const marker = createMarker(event)
    marker.addTo(markersLayer)
    markerIndex.set(event.id, marker)
  }

  updateMarkerStyles()
  fitResultsBoundsIfNeeded()
}

function updateMarkerStyles() {
  for (const event of activeEvents.value) {
    const marker = markerIndex.get(event.id)
    if (!marker) continue
    marker.setStyle(markerStyle(event.id === selectedEventId.value, event.mag))
    if (event.id === selectedEventId.value) {
      marker.bringToFront()
    }
  }
}

function setBaseLayers() {
  if (!map) return
  if (baseLayer) map.removeLayer(baseLayer)
  if (labelLayer) map.removeLayer(labelLayer)

  const theme = TILE_THEMES[mapTheme.value]
  baseLayer = L.tileLayer(theme.base, {
    maxZoom: 16,
    subdomains: ['a', 'b', 'c'],
  })
  labelLayer = L.tileLayer(LABEL_TILE, {
    maxZoom: 16,
    subdomains: ['1', '2', '3', '4'],
    opacity: mapTheme.value === 'terrain' ? 0.6 : 0.85,
  })

  baseLayer.addTo(map)
  labelLayer.addTo(map)
  requestResultsFit('theme')
}

onMounted(async () => {
  syncFiltersFromRoute()
  const queryOffset = Number(route.query.offset ?? 0)
  resultOffset.value = Number.isFinite(queryOffset) && queryOffset >= 0 ? queryOffset : 0
  if (!mapEl.value) return

  map = L.map(mapEl.value, {
    zoomControl: false,
    attributionControl: false,
    minZoom: 2,
    maxZoom: 16,
    worldCopyJump: true,
  }).setView([25, 105], 2)
  mapReady.value = true

  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.control.attribution({ position: 'bottomleft', prefix: false }).addTo(map)
  markersLayer = L.layerGroup().addTo(map)
  setBaseLayers()

  watch(
    mapTheme,
    () => {
      setBaseLayers()
    },
    { flush: 'post' },
  )

  watch(
    activeEvents,
    () => {
      renderMarkers()
    },
    { deep: true },
  )

  watch(selectedEventId, () => updateMarkerStyles())

  const hasRouteQuery = Object.keys(route.query).length > 0
  if (hasRouteQuery) {
    hasSearched.value = true
    await runQuery()
  } else {
    await loadPreview()
  }
})

onBeforeUnmount(() => {
  if (copyTimeout) clearTimeout(copyTimeout)
  map?.remove()
})
</script>

<style scoped>
.history-page {
  --bg: #f3f0e8;
  --surface: rgba(255, 255, 255, 0.88);
  --surface-strong: #ffffff;
  --line: rgba(109, 84, 52, 0.14);
  --text: #2d2418;
  --muted: #6d5d4b;
  --accent: #1f6f78;
  --accent-strong: #164e63;
  --shadow: 0 18px 36px rgba(69, 48, 24, 0.08);
  min-height: 100vh;
  padding: 28px;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(205, 163, 102, 0.18), transparent 26%),
    radial-gradient(circle at top right, rgba(31, 111, 120, 0.16), transparent 24%),
    linear-gradient(180deg, #f7f4ed 0%, var(--bg) 100%);
}

.page-header,
.panel-head,
.results-head,
.map-head,
.detail-head,
.form-footer,
.results-actions,
.detail-topline,
.detail-actions,
.event-cell,
.row-actions,
.quick-actions,
.footer-actions {
  display: flex;
  align-items: center;
}

.page-header,
.panel-head,
.results-head,
.map-head,
.detail-head,
.form-footer {
  justify-content: space-between;
  gap: 16px;
}

.page-header {
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted);
}

h1,
h2,
h3,
strong,
.primary-btn,
.ghost-btn,
.tiny-btn,
.back-link {
  font-family: Georgia, 'Times New Roman', serif;
}

h1 {
  margin: 0;
  font-size: 34px;
}

h2,
h3,
p {
  margin-top: 0;
}

.subtitle,
.panel-head p,
.results-head p,
.map-head p,
.detail-head p,
.helper,
.card-note,
.copy-feedback {
  color: var(--muted);
}

.back-link {
  padding: 11px 16px;
  border-radius: 999px;
  color: var(--text);
  text-decoration: none;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--line);
}

.card {
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
}

.panel,
.results-card,
.map-card,
.detail-card {
  border-radius: 24px;
}

.panel {
  padding: 24px;
}

.query-state {
  display: grid;
  grid-template-columns: minmax(220px, 0.9fr) minmax(0, 2fr);
  gap: 14px;
  padding: 16px 18px;
  margin: 18px 0 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(109, 84, 52, 0.12);
}

.state-copy strong {
  display: block;
  margin-bottom: 6px;
}

.state-copy p {
  margin-bottom: 0;
  color: var(--muted);
}

.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-content: flex-start;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 8px 12px;
  border-radius: 999px;
  color: var(--accent-strong);
  background: rgba(31, 111, 120, 0.08);
  border: 1px solid rgba(31, 111, 120, 0.12);
  font-size: 12px;
  line-height: 1.4;
}

.filter-chip-muted {
  color: var(--muted);
  background: rgba(255, 255, 255, 0.84);
  border-color: rgba(109, 84, 52, 0.16);
}

.quick-actions,
.footer-actions,
.results-actions,
.detail-actions,
.row-actions {
  gap: 10px;
}

.query-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
}

.control {
  width: 100%;
  border: 1px solid rgba(109, 84, 52, 0.22);
  border-radius: 14px;
  padding: 11px 12px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.92);
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.control:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(31, 111, 120, 0.1);
}

.control-select {
  min-width: 130px;
}

.form-footer {
  grid-column: 1 / -1;
  margin-top: 8px;
}

.helper {
  margin-bottom: 0;
}

.query-feedback {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--accent-strong);
}

.query-feedback.error {
  color: #b45309;
}

.primary-btn,
.ghost-btn,
.tiny-btn {
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.18s ease, opacity 0.18s ease, background 0.18s ease;
}

.primary-btn {
  padding: 12px 18px;
  color: #fff;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
}

.ghost-btn,
.tiny-btn {
  padding: 10px 14px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--line);
}

.tiny-btn {
  padding: 7px 11px;
  font-size: 12px;
}

.primary-btn:hover,
.ghost-btn:hover,
.tiny-btn:hover,
.back-link:hover {
  transform: translateY(-1px);
}

.primary-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 22px 0;
}

.overview-card {
  padding: 20px;
  border-radius: 22px;
}

.card-label {
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--muted);
}

.card-value {
  display: block;
  font-size: 32px;
  line-height: 1.1;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 0.95fr);
  gap: 18px;
  align-items: start;
}

.workspace-main {
  display: grid;
  gap: 18px;
}

.results-card,
.map-card,
.detail-card {
  overflow: hidden;
}

.results-head,
.map-head,
.detail-head,
.detail-body {
  padding: 20px 22px;
}

.results-head,
.panel-head,
.detail-head {
  flex-wrap: wrap;
}

.map-style-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}

.feedback-block {
  min-height: 180px;
  display: grid;
  place-items: center;
  padding: 28px;
  text-align: center;
  color: var(--muted);
}

.pagination-bar,
.pagination-actions {
  display: flex;
  align-items: center;
}

.preview-banner {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 22px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  background: rgba(255, 255, 255, 0.54);
}

.preview-banner strong {
  color: var(--text);
}

.pagination-bar {
  justify-content: space-between;
  gap: 12px;
  padding: 14px 22px;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  background: rgba(255, 255, 255, 0.54);
}

.pagination-actions {
  gap: 10px;
}

.loading-state {
  gap: 10px;
}

.spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 3px solid rgba(31, 111, 120, 0.2);
  border-top-color: var(--accent);
  animation: spin 0.9s linear infinite;
}

.table-shell {
  overflow: auto;
  border-top: 1px solid var(--line);
  max-height: 560px;
}

.results-table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(109, 84, 52, 0.12);
  text-align: left;
  vertical-align: middle;
}

.results-table tbody tr {
  cursor: pointer;
  transition: background 0.18s ease;
}

.results-table tbody tr:hover {
  background: rgba(31, 111, 120, 0.06);
}

.results-table tbody tr.selected {
  background: rgba(31, 111, 120, 0.12);
  box-shadow: inset 4px 0 0 var(--accent);
}

.sort-btn {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-weight: 600;
}

.event-cell {
  gap: 12px;
}

.event-cell small,
.mono {
  font-family: 'Fira Code', monospace;
  color: var(--muted);
}

.mag-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding: 6px 10px;
  border-radius: 999px;
  color: #fff;
  font-weight: 700;
}

.mag-pill.low {
  background: #0f766e;
}

.mag-pill.medium {
  background: #d97706;
}

.mag-pill.high {
  background: #b45309;
}

.map-panel {
  height: 540px;
  border-top: 1px solid var(--line);
}

.map-status {
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--muted);
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid var(--line);
}

.detail-meta {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--accent-strong);
  background: rgba(31, 111, 120, 0.08);
  border: 1px solid rgba(31, 111, 120, 0.14);
}

.detail-body {
  padding-top: 0;
}

.detail-card {
  position: sticky;
  top: 24px;
}

.detail-topline {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.detail-summary {
  margin-bottom: 18px;
  line-height: 1.7;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 14px;
  margin: 0 0 22px;
}

.detail-grid dt {
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--muted);
}

.detail-grid dd {
  margin: 0;
  font-weight: 600;
}

.detail-empty {
  min-height: 320px;
}

.copy-feedback {
  padding: 0 22px 18px;
  margin: 0;
}

:deep(.leaflet-container) {
  background: #d5d3cf;
}

:deep(.leaflet-control-attribution) {
  background: rgba(255, 255, 255, 0.72);
  border-radius: 999px;
  padding: 4px 8px;
}

:deep(.leaflet-tooltip) {
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 999px;
  box-shadow: 0 10px 22px rgba(17, 24, 39, 0.08);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1200px) {
  .query-state,
  .query-grid,
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .detail-card {
    position: static;
  }
}

@media (max-width: 720px) {
  .history-page {
    padding: 18px;
  }

  .page-header,
  .panel-head,
  .results-head,
  .map-head,
  .detail-head,
  .form-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .query-grid,
  .overview-grid,
  .detail-grid,
  .query-state {
    grid-template-columns: 1fr;
  }

  .results-actions,
  .footer-actions,
  .detail-actions,
  .quick-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .pagination-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .preview-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-chip {
    width: 100%;
    border-radius: 16px;
  }

  .map-panel {
    height: 420px;
  }
}
</style>
