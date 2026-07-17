<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { apiPath } from '../config/api'
import {
  addDomesticBaseMap,
  domesticMapAttribution,
  type DomesticMapStatus,
} from '../config/domesticMap'
import {
  catalogCsv,
  fetchCatalog,
  localizedPlaceName,
  normalizeEvent,
  type CatalogSource,
  type EarthquakeEvent,
} from '../services/earthquakes'

type Locale = 'zh' | 'en'
type StreamState = 'connecting' | 'live' | 'polling' | 'offline'
type SortMode = 'time' | 'magnitude'
type RegionKey = 'global' | 'china' | 'sichuan' | 'chengdu' | 'viewport'
type RegionBounds = [[number, number], [number, number]]

const MAX_LIST_ITEMS = 300

const REGION_BOUNDS: Record<Exclude<RegionKey, 'global' | 'viewport'>, RegionBounds> = {
  china: [[18, 73], [54, 135]],
  sichuan: [[25.8, 96.8], [34.5, 109.5]],
  chengdu: [[30.1, 103.3], [31.4, 105.0]],
}

const messages = {
  zh: {
    brandSub: '地震目录与实时监测',
    home: '官网首页',
    history: '历史检索',
    workbench: 'Terra 工作台',
    live: '实时数据已连接',
    connecting: '正在连接实时数据',
    polling: '定时更新模式',
    offline: '数据连接不可用',
    backendSource: '实验室目录服务',
    usgsSource: 'USGS 官方数据',
    search: '搜索位置或事件 ID',
    time: '时间',
    magnitude: '震级',
    region: '区域',
    global: '全球',
    china: '中国及邻区',
    sichuan: '四川及邻区',
    chengdu: '成都地区',
    viewport: '当前地图范围',
    queryViewport: '查询当前视野',
    refresh: '刷新数据',
    refreshing: '正在刷新',
    catalog: '地震事件目录',
    records: '条记录',
    export: '导出 CSV',
    latest: '最新优先',
    strongest: '震级优先',
    total: '事件总数',
    maxMagnitude: '最大震级',
    pastHour: '近一小时',
    averageDepth: '平均深度',
    noEvents: '当前条件下没有地震记录',
    noEventsHint: '可降低震级、扩大区域或刷新数据。',
    listLimit: '目录显示前 {shown} 条，地图显示全部 {total} 条。',
    depth: '深度',
    agoNow: '刚刚',
    minutesAgo: '{value} 分钟前',
    hoursAgo: '{value} 小时前',
    daysAgo: '{value} 天前',
    detail: '事件详情',
    localTime: '本地时间',
    utcTime: 'UTC 时间',
    coordinates: '震中坐标',
    network: '监测网络',
    eventType: '事件类型',
    status: '审核状态',
    updated: '更新时间',
    quality: '解算质量',
    copyCoordinates: '复制坐标',
    copied: '已复制',
    external: '查看数据源',
    fitEvents: '显示全部事件',
    close: '关闭',
    openList: '打开事件目录',
    closeList: '收起事件目录',
    systemInfo: '数据说明',
    systemTitle: '关于地震目录',
    systemText: '平台优先读取实验室数据库，并通过实时事件流接收新增记录。服务不可用时，会临时切换到 USGS 官方目录，页面会明确标注当前数据来源。',
    systemNote: '地震参数可能随监测机构复核而更新，研究与应急使用前请核验权威发布。',
    loadError: '暂时无法获取地震目录',
    retry: '重新连接',
    staleData: '当前保留上一次成功加载的数据。',
    lastUpdated: '更新于',
    mapCount: '地图事件',
    mapLoading: '正在加载全球自然影像',
    mapError: '自然影像暂时不可用',
    mapRetryHint: '当前已切换到无国界经纬网，请检查网络后刷新。',
    longitude: '经度',
    latitude: '纬度',
    unknown: '未知区域',
    notAvailable: '暂无',
  },
  en: {
    brandSub: 'Earthquake Catalog & Monitoring',
    home: 'Home',
    history: 'Archive',
    workbench: 'Terra Workbench',
    live: 'Live stream connected',
    connecting: 'Connecting live stream',
    polling: 'Scheduled refresh',
    offline: 'Data connection unavailable',
    backendSource: 'Laboratory catalog',
    usgsSource: 'Official USGS data',
    search: 'Search place or event ID',
    time: 'Time',
    magnitude: 'Magnitude',
    region: 'Region',
    global: 'Global',
    china: 'China & surroundings',
    sichuan: 'Sichuan & surroundings',
    chengdu: 'Chengdu area',
    viewport: 'Current map extent',
    queryViewport: 'Query map extent',
    refresh: 'Refresh',
    refreshing: 'Refreshing',
    catalog: 'Earthquake Catalog',
    records: 'events',
    export: 'Export CSV',
    latest: 'Latest first',
    strongest: 'Strongest first',
    total: 'Total events',
    maxMagnitude: 'Largest event',
    pastHour: 'Past hour',
    averageDepth: 'Average depth',
    noEvents: 'No events match the current filters',
    noEventsHint: 'Lower the magnitude, expand the region, or refresh the catalog.',
    listLimit: 'Showing {shown} of {total} events in the list. The map shows all.',
    depth: 'Depth',
    agoNow: 'just now',
    minutesAgo: '{value} min ago',
    hoursAgo: '{value} hr ago',
    daysAgo: '{value} d ago',
    detail: 'Event details',
    localTime: 'Local time',
    utcTime: 'UTC time',
    coordinates: 'Epicenter',
    network: 'Network',
    eventType: 'Event type',
    status: 'Review status',
    updated: 'Updated',
    quality: 'Solution quality',
    copyCoordinates: 'Copy coordinates',
    copied: 'Copied',
    external: 'Open source record',
    fitEvents: 'Fit all events',
    close: 'Close',
    openList: 'Open catalog',
    closeList: 'Collapse catalog',
    systemInfo: 'Data notes',
    systemTitle: 'About this catalog',
    systemText: 'The platform prioritizes the laboratory database and receives new records through a live event stream. If unavailable, it temporarily switches to the official USGS catalog and clearly identifies the active source.',
    systemNote: 'Parameters may change after agency review. Verify authoritative releases before research or emergency use.',
    loadError: 'The earthquake catalog is temporarily unavailable',
    retry: 'Reconnect',
    staleData: 'The last successfully loaded data remain visible.',
    lastUpdated: 'Updated',
    mapCount: 'Mapped events',
    mapLoading: 'Loading global natural imagery',
    mapError: 'Natural imagery is temporarily unavailable',
    mapRetryHint: 'A boundary-free coordinate grid is shown. Check the network and refresh.',
    longitude: 'Longitude',
    latitude: 'Latitude',
    unknown: 'Unknown region',
    notAvailable: 'N/A',
  },
} as const

const router = useRouter()
const route = useRoute()
const locale = ref<Locale>(route.query.lang === 'en' ? 'en' : 'zh')
const c = computed(() => messages[locale.value])

const mapEl = ref<HTMLDivElement | null>(null)
const events = ref<EarthquakeEvent[]>([])
const loading = ref(true)
const errorMessage = ref('')
const source = ref<CatalogSource | null>(null)
const fetchedAt = ref<string | null>(null)
const streamState = ref<StreamState>('connecting')
const sidebarOpen = ref(true)
const infoOpen = ref(false)
const selectedId = ref<string | null>(null)
const searchTerm = ref('')
const selectedHours = ref(24)
const minMagnitude = ref(3)
const selectedRegion = ref<RegionKey>('global')
const activeBbox = ref<string | null>(null)
const sortMode = ref<SortMode>('time')
const copied = ref(false)
const mapViewLabel = ref('')
const mapStatus = ref<DomesticMapStatus>('loading')

let map: L.Map | null = null
let markerLayer: L.LayerGroup | null = null
let quakeRenderer: L.Canvas | null = null
let eventSource: EventSource | null = null
let reconnectTimer: number | null = null
let refreshTimer: number | null = null
let requestController: AbortController | null = null
let requestSerial = 0
let markerFrame: number | null = null
let copiedTimer: number | null = null
let attributionControl: L.Control.Attribution | null = null
let currentAttribution = ''
const markers = new Map<string, L.CircleMarker>()

const mapNotice = computed(() => {
  if (mapStatus.value === 'loading') return { title: c.value.mapLoading, hint: '' }
  if (mapStatus.value === 'error') return { title: c.value.mapError, hint: c.value.mapRetryHint }
  return { title: '', hint: '' }
})

function updateMapStatus(status: DomesticMapStatus) {
  mapStatus.value = status
  if (!attributionControl) return
  if (currentAttribution) attributionControl.removeAttribution(currentAttribution)
  currentAttribution = domesticMapAttribution(status)
  attributionControl.addAttribution(currentAttribution)
}

const timeOptions = [24, 72, 168]
const magnitudeOptions = [3, 4, 5, 6]

const regionOptions = computed(() => [
  { value: 'global', label: c.value.global },
  { value: 'china', label: c.value.china },
  { value: 'sichuan', label: c.value.sichuan },
  { value: 'chengdu', label: c.value.chengdu },
  ...(selectedRegion.value === 'viewport' ? [{ value: 'viewport', label: c.value.viewport }] : []),
])

function inActiveBbox(event: EarthquakeEvent) {
  if (!activeBbox.value) return true
  const [west, south, east, north] = activeBbox.value.split(',').map(Number)
  return event.lon >= west && event.lon <= east && event.lat >= south && event.lat <= north
}

const filteredEvents = computed(() => {
  const search = searchTerm.value.trim().toLocaleLowerCase()
  return events.value.filter((event) => {
    if (event.mag < minMagnitude.value || !inActiveBbox(event)) return false
    if (!search) return true
    return localizedPlaceName(event.place, locale.value).toLocaleLowerCase().includes(search)
      || event.place.toLocaleLowerCase().includes(search)
      || event.id.toLocaleLowerCase().includes(search)
  })
})

const sortedEvents = computed(() => {
  const list = [...filteredEvents.value]
  if (sortMode.value === 'magnitude') {
    return list.sort((a, b) => b.mag - a.mag || Date.parse(b.time) - Date.parse(a.time))
  }
  return list.sort((a, b) => Date.parse(b.time) - Date.parse(a.time))
})

const displayedEvents = computed(() => sortedEvents.value.slice(0, MAX_LIST_ITEMS))
const eventById = computed(() => new Map(events.value.map((event) => [event.id, event])))
const selectedEvent = computed(() => selectedId.value ? eventById.value.get(selectedId.value) ?? null : null)

const catalogStats = computed(() => {
  const list = filteredEvents.value
  const strongest = list.reduce<EarthquakeEvent | null>((current, event) => {
    return !current || event.mag > current.mag ? event : current
  }, null)
  const oneHourAgo = Date.now() - 60 * 60 * 1000
  const depthValues = list.flatMap((event) => event.depth_km === null ? [] : [event.depth_km])
  const averageDepth = depthValues.length
    ? depthValues.reduce((sum, depth) => sum + depth, 0) / depthValues.length
    : null

  return {
    total: list.length,
    strongest,
    pastHour: list.filter((event) => Date.parse(event.time) >= oneHourAgo).length,
    averageDepth,
  }
})

const connectionText = computed(() => {
  if (streamState.value === 'live') return c.value.live
  if (streamState.value === 'connecting') return c.value.connecting
  if (streamState.value === 'polling') return c.value.polling
  return c.value.offline
})

const sourceText = computed(() => {
  if (source.value === 'backend') return c.value.backendSource
  if (source.value === 'usgs') return c.value.usgsSource
  return c.value.connecting
})

function replaceToken(template: string, values: Record<string, string | number>) {
  return Object.entries(values).reduce((text, [key, value]) => text.replace(`{${key}}`, String(value)), template)
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(value)) return c.value.notAvailable
  return value.toFixed(digits)
}

function formatMeasurement(value: number | null | undefined, unit: string, digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(value)) return c.value.notAvailable
  return `${value.toFixed(digits)}${unit === '°' ? '' : ' '}${unit}`
}

function formatLocalTime(value: string | undefined) {
  if (!value) return c.value.notAvailable
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return c.value.notAvailable
  return new Intl.DateTimeFormat(locale.value === 'zh' ? 'zh-CN' : 'en-GB', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(date)
}

function formatUtcTime(value: string | undefined) {
  if (!value) return c.value.notAvailable
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return c.value.notAvailable
  return `${date.toISOString().replace('T', ' ').slice(0, 19)} UTC`
}

function relativeTime(value: string) {
  const deltaMinutes = Math.max(0, Math.floor((Date.now() - Date.parse(value)) / 60000))
  if (deltaMinutes < 1) return c.value.agoNow
  if (deltaMinutes < 60) return replaceToken(c.value.minutesAgo, { value: deltaMinutes })
  const hours = Math.floor(deltaMinutes / 60)
  if (hours < 24) return replaceToken(c.value.hoursAgo, { value: hours })
  return replaceToken(c.value.daysAgo, { value: Math.floor(hours / 24) })
}

function magnitudeColor(magnitude: number) {
  if (magnitude >= 6) return '#c9312f'
  if (magnitude >= 5) return '#dc673c'
  if (magnitude >= 4) return '#c99a2e'
  return '#21877d'
}

function markerRadius(magnitude: number) {
  return Math.max(4.5, Math.min(17, 3.5 + magnitude * 1.65))
}

function createTooltip(event: EarthquakeEvent) {
  const container = document.createElement('div')
  container.className = 'quake-tooltip'
  const magnitude = document.createElement('strong')
  magnitude.textContent = `M ${event.mag.toFixed(1)}`
  magnitude.style.color = magnitudeColor(event.mag)
  const place = document.createElement('span')
  place.textContent = localizedPlaceName(event.place, locale.value) || c.value.unknown
  const meta = document.createElement('small')
  meta.textContent = `${formatLocalTime(event.time)} · ${c.value.depth} ${formatMeasurement(event.depth_km, 'km')}`
  container.append(magnitude, place, meta)
  return container
}

function markerStyle(event: EarthquakeEvent, selected = false): L.CircleMarkerOptions {
  return {
    renderer: quakeRenderer ?? undefined,
    radius: markerRadius(event.mag),
    color: selected ? '#111719' : '#ffffff',
    weight: selected ? 3 : 1.4,
    fillColor: magnitudeColor(event.mag),
    fillOpacity: selected ? 1 : 0.88,
    opacity: 1,
  }
}

function syncMarkers() {
  markerFrame = null
  if (!map || !markerLayer) return

  const nextIds = new Set(filteredEvents.value.map((event) => event.id))
  for (const [id, marker] of markers) {
    if (!nextIds.has(id)) {
      markerLayer.removeLayer(marker)
      markers.delete(id)
    }
  }

  for (const event of filteredEvents.value) {
    const existing = markers.get(event.id)
    const selected = event.id === selectedId.value
    if (existing) {
      existing.setLatLng([event.lat, event.lon])
      existing.setRadius(markerRadius(event.mag))
      existing.setStyle(markerStyle(event, selected))
      existing.setTooltipContent(createTooltip(event))
      continue
    }

    const marker = L.circleMarker([event.lat, event.lon], markerStyle(event, selected))
      .bindTooltip(createTooltip(event), {
        className: 'quake-tooltip-shell',
        direction: 'top',
        offset: L.point(0, -8),
        opacity: 1,
      })
      .on('click', () => selectEvent(event.id, false))

    marker.addTo(markerLayer)
    markers.set(event.id, marker)
  }
}

function scheduleMarkerSync() {
  if (markerFrame !== null) cancelAnimationFrame(markerFrame)
  markerFrame = requestAnimationFrame(syncMarkers)
}

function updateSelectedMarker(previousId: string | null, nextId: string | null) {
  if (previousId) {
    const event = eventById.value.get(previousId)
    const marker = markers.get(previousId)
    if (event && marker) marker.setStyle(markerStyle(event, false))
  }
  if (nextId) {
    const event = eventById.value.get(nextId)
    const marker = markers.get(nextId)
    if (event && marker) {
      marker.setStyle(markerStyle(event, true))
      marker.bringToFront()
    }
  }
}

function queryPayload() {
  return {
    hours: selectedHours.value,
    minMag: minMagnitude.value,
    bbox: activeBbox.value,
    limit: 5000,
  }
}

async function loadCatalog(silent = false) {
  const serial = ++requestSerial
  requestController?.abort()
  const controller = new AbortController()
  requestController = controller
  const timeout = window.setTimeout(() => controller.abort(), 18000)

  if (!silent) loading.value = true
  errorMessage.value = ''

  try {
    const result = await fetchCatalog(queryPayload(), controller.signal)
    if (serial !== requestSerial) return
    events.value = result.events
    source.value = result.source
    fetchedAt.value = result.fetchedAt
    if (selectedId.value && !result.events.some((event) => event.id === selectedId.value)) {
      selectedId.value = null
    }
    if (result.source === 'usgs' && streamState.value !== 'connecting') streamState.value = 'polling'
  } catch (error) {
    if (controller.signal.aborted || serial !== requestSerial) return
    errorMessage.value = error instanceof Error ? error.message : c.value.loadError
    if (!events.value.length) source.value = null
    streamState.value = 'offline'
  } finally {
    window.clearTimeout(timeout)
    if (serial === requestSerial) {
      loading.value = false
      requestController = null
    }
  }
}

function mergeStreamEvents(rawItems: unknown[]) {
  const incoming = rawItems
    .map((item) => normalizeEvent((item ?? {}) as Record<string, unknown>))
    .filter((item): item is EarthquakeEvent => item !== null)
  if (!incoming.length) return

  const merged = new Map(events.value.map((event) => [event.id, event]))
  for (const event of incoming) merged.set(event.id, event)
  events.value = [...merged.values()]
    .sort((a, b) => Date.parse(b.time) - Date.parse(a.time))
    .slice(0, 5000)
  fetchedAt.value = new Date().toISOString()
}

function scheduleStreamReconnect() {
  if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
  reconnectTimer = window.setTimeout(connectStream, 30000)
}

function connectStream() {
  eventSource?.close()
  eventSource = null
  streamState.value = 'connecting'

  const stream = new EventSource(apiPath('/api/stream'))
  eventSource = stream
  stream.onopen = () => {
    streamState.value = 'live'
    if (source.value === 'usgs') void loadCatalog(true)
  }
  stream.addEventListener('new_events', (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data) as { data?: unknown[] }
      mergeStreamEvents(Array.isArray(payload.data) ? payload.data : [])
    } catch {
      // Ignore malformed stream messages and keep the last valid catalog.
    }
  })
  stream.onerror = () => {
    stream.close()
    if (eventSource === stream) eventSource = null
    streamState.value = events.value.length ? 'polling' : 'offline'
    scheduleStreamReconnect()
  }
}

function updateMapViewLabel() {
  if (!map) return
  const center = map.getCenter()
  mapViewLabel.value = `${center.lat.toFixed(2)}°, ${center.lng.toFixed(2)}° · Z${map.getZoom()}`
}

function selectEvent(id: string, fly = true) {
  const event = eventById.value.get(id)
  if (!event) return
  selectedId.value = id
  infoOpen.value = false
  if (fly && map) map.flyTo([event.lat, event.lon], Math.max(map.getZoom(), 6), { duration: 0.8 })
  if (window.innerWidth <= 820) sidebarOpen.value = false
}

function fitEvents() {
  if (!map || !filteredEvents.value.length) return
  if (filteredEvents.value.length === 1) {
    const event = filteredEvents.value[0]
    map.flyTo([event.lat, event.lon], 7, { duration: 0.7 })
    return
  }
  const bounds = L.latLngBounds(filteredEvents.value.map((event) => L.latLng(event.lat, event.lon)))
  map.fitBounds(bounds, { padding: [60, 60], maxZoom: 7, animate: true })
}

function bboxForRegion(key: Exclude<RegionKey, 'global' | 'viewport'>) {
  const bounds = L.latLngBounds(REGION_BOUNDS[key])
  return `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`
}

async function handleRegionChange(changeEvent?: Event) {
  const nextRegion = changeEvent
    ? (changeEvent.currentTarget as HTMLSelectElement).value as RegionKey
    : selectedRegion.value
  selectedRegion.value = nextRegion

  if (nextRegion === 'viewport') return
  if (nextRegion === 'global') {
    activeBbox.value = null
    map?.flyTo([25, 105], 2, { duration: 0.7 })
  } else {
    const key = nextRegion as Exclude<RegionKey, 'global' | 'viewport'>
    activeBbox.value = bboxForRegion(key)
    map?.fitBounds(REGION_BOUNDS[key], { padding: [30, 30], animate: true })
  }
  await loadCatalog()
}

async function queryCurrentViewport() {
  if (!map) return
  const bounds = map.getBounds()
  const west = Math.max(-180, bounds.getWest())
  const east = Math.min(180, bounds.getEast())
  const south = Math.max(-85, bounds.getSouth())
  const north = Math.min(85, bounds.getNorth())
  activeBbox.value = `${west},${south},${east},${north}`
  selectedRegion.value = 'viewport'
  await loadCatalog()
}

async function changeHours(hours: number) {
  if (selectedHours.value === hours) return
  selectedHours.value = hours
  await loadCatalog()
}

async function changeMagnitude(magnitude: number) {
  if (minMagnitude.value === magnitude) return
  minMagnitude.value = magnitude
  await loadCatalog()
}

function downloadCsv() {
  if (!sortedEvents.value.length) return
  const blob = new Blob([catalogCsv(sortedEvents.value)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `cdut-seislab-catalog-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function copyCoordinates() {
  if (!selectedEvent.value) return
  try {
    await navigator.clipboard.writeText(`${selectedEvent.value.lat.toFixed(5)}, ${selectedEvent.value.lon.toFixed(5)}`)
    copied.value = true
    if (copiedTimer !== null) window.clearTimeout(copiedTimer)
    copiedTimer = window.setTimeout(() => { copied.value = false }, 1800)
  } catch {
    copied.value = false
  }
}

function setLocale(next: Locale) {
  if (locale.value === next) return
  locale.value = next
  const query = { ...route.query }
  if (next === 'en') query.lang = 'en'
  else delete query.lang
  void router.replace({ query })
}

function handleVisibilityChange() {
  if (document.hidden) {
    eventSource?.close()
    eventSource = null
    if (streamState.value === 'live') streamState.value = 'polling'
    return
  }
  connectStream()
  if (!fetchedAt.value || Date.now() - Date.parse(fetchedAt.value) > 120000) void loadCatalog(true)
}

watch(filteredEvents, scheduleMarkerSync, { flush: 'post' })
watch(selectedId, (next, previous) => updateSelectedMarker(previous, next))
watch(locale, () => {
  document.title = locale.value === 'zh'
    ? '地震目录 | CDUT SEISLAB'
    : 'Earthquake Catalog | CDUT SEISLAB'
  scheduleMarkerSync()
})

onMounted(async () => {
  sidebarOpen.value = window.innerWidth > 820
  document.title = locale.value === 'zh'
    ? '地震目录 | CDUT SEISLAB'
    : 'Earthquake Catalog | CDUT SEISLAB'

  quakeRenderer = L.canvas({ padding: 0.5, tolerance: 6 })
  map = L.map(mapEl.value!, {
    preferCanvas: true,
    renderer: quakeRenderer,
    minZoom: 2,
    maxZoom: 16,
    zoomControl: false,
    attributionControl: false,
    worldCopyJump: true,
    maxBounds: [[-85, -180], [85, 180]],
    maxBoundsViscosity: 0.85,
  }).setView([25, 105], 2)

  addDomesticBaseMap(map, updateMapStatus)

  markerLayer = L.layerGroup().addTo(map)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  attributionControl = L.control.attribution({ position: 'bottomright', prefix: false })
  currentAttribution = domesticMapAttribution(mapStatus.value)
  attributionControl.addAttribution(currentAttribution).addTo(map)

  map.on('moveend zoomend', updateMapViewLabel)
  updateMapViewLabel()

  await loadCatalog()
  await nextTick()
  scheduleMarkerSync()
  connectStream()
  refreshTimer = window.setInterval(() => {
    if (streamState.value !== 'live' && !loading.value && !document.hidden) void loadCatalog(true)
  }, 60000)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  requestController?.abort()
  eventSource?.close()
  if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
  if (refreshTimer !== null) window.clearInterval(refreshTimer)
  if (markerFrame !== null) cancelAnimationFrame(markerFrame)
  if (copiedTimer !== null) window.clearTimeout(copiedTimer)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  map?.remove()
  markers.clear()
})
</script>

<template>
  <div class="catalog-page">
    <header class="topbar">
      <button class="brand" type="button" @click="router.push(locale === 'en' ? '/en' : '/')">
        <img src="/brand/cdut-seislab-mark-512.png" alt="CDUT SEISLAB" />
        <span>
          <strong>CDUT SEISLAB</strong>
          <small>{{ c.brandSub }}</small>
        </span>
      </button>

      <div class="connection-block" :class="streamState">
        <span class="status-dot" aria-hidden="true"></span>
        <span><strong>{{ connectionText }}</strong><small>{{ sourceText }}</small></span>
      </div>

      <nav class="header-actions" :aria-label="locale === 'zh' ? '目录导航' : 'Catalog navigation'">
        <button type="button" @click="router.push(locale === 'en' ? '/en' : '/')">{{ c.home }}</button>
        <button type="button" @click="router.push('/history')">{{ c.history }}</button>
        <button type="button" @click="infoOpen = !infoOpen">{{ c.systemInfo }}</button>
        <div class="locale-switch" aria-label="Language">
          <button type="button" :class="{ active: locale === 'zh' }" @click="setLocale('zh')">中</button>
          <button type="button" :class="{ active: locale === 'en' }" @click="setLocale('en')">EN</button>
        </div>
        <button class="workbench-button" type="button" @click="router.push('/terra/chat')">{{ c.workbench }}</button>
      </nav>
    </header>

    <section class="filterbar" :aria-label="locale === 'zh' ? '目录筛选' : 'Catalog filters'">
      <label class="search-control">
        <span class="sr-only">{{ c.search }}</span>
        <input v-model="searchTerm" type="search" :placeholder="c.search" autocomplete="off" />
      </label>

      <div class="filter-group">
        <span class="filter-label">{{ c.time }}</span>
        <div class="segmented-control">
          <button
            v-for="hours in timeOptions"
            :key="hours"
            type="button"
            :class="{ active: selectedHours === hours }"
            @click="changeHours(hours)"
          >{{ hours === 24 ? '24H' : `${hours / 24}D` }}</button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-label">{{ c.magnitude }}</span>
        <div class="segmented-control magnitude-control">
          <button
            v-for="magnitude in magnitudeOptions"
            :key="magnitude"
            type="button"
            :class="{ active: minMagnitude === magnitude }"
            @click="changeMagnitude(magnitude)"
          >M{{ magnitude }}+</button>
        </div>
      </div>

      <label class="region-control">
        <span class="filter-label">{{ c.region }}</span>
        <select v-model="selectedRegion" @change="handleRegionChange($event)">
          <option v-for="option in regionOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </label>

      <button class="secondary-command" type="button" @click="queryCurrentViewport">{{ c.queryViewport }}</button>
      <button class="primary-command" type="button" :disabled="loading" @click="loadCatalog()">
        {{ loading ? c.refreshing : c.refresh }}
      </button>
    </section>

    <main class="map-stage">
      <div ref="mapEl" class="map-container"></div>
      <div v-if="mapStatus === 'loading' || mapStatus === 'error'" class="map-compliance-notice" :class="mapStatus" role="status">
        <strong>{{ mapNotice.title }}</strong>
        <span v-if="mapNotice.hint">{{ mapNotice.hint }}</span>
      </div>
      <div v-if="loading" class="loading-line" aria-hidden="true"><span></span></div>

      <button
        v-if="!sidebarOpen"
        class="catalog-toggle"
        type="button"
        :title="c.openList"
        :aria-label="c.openList"
        @click="sidebarOpen = true"
      >›</button>

      <aside class="catalog-panel" :class="{ closed: !sidebarOpen }">
        <div class="panel-header">
          <div>
            <span class="eyebrow">CATALOG / {{ selectedHours }}H</span>
            <h1>{{ c.catalog }}</h1>
            <p>{{ filteredEvents.length }} {{ c.records }}</p>
          </div>
          <div class="panel-header-actions">
            <button type="button" :disabled="!sortedEvents.length" @click="downloadCsv">{{ c.export }}</button>
            <button class="icon-button" type="button" :title="c.closeList" :aria-label="c.closeList" @click="sidebarOpen = false">‹</button>
          </div>
        </div>

        <div class="stats-strip">
          <div><span>{{ c.total }}</span><strong>{{ catalogStats.total }}</strong></div>
          <div><span>{{ c.maxMagnitude }}</span><strong>{{ catalogStats.strongest ? `M${catalogStats.strongest.mag.toFixed(1)}` : '—' }}</strong></div>
          <div><span>{{ c.pastHour }}</span><strong>{{ catalogStats.pastHour }}</strong></div>
          <div><span>{{ c.averageDepth }}</span><strong>{{ catalogStats.averageDepth === null ? '—' : `${catalogStats.averageDepth.toFixed(0)} km` }}</strong></div>
        </div>

        <div class="list-tools">
          <div class="list-sort segmented-control">
            <button type="button" :class="{ active: sortMode === 'time' }" @click="sortMode = 'time'">{{ c.latest }}</button>
            <button type="button" :class="{ active: sortMode === 'magnitude' }" @click="sortMode = 'magnitude'">{{ c.strongest }}</button>
          </div>
          <span>{{ sourceText }}</span>
        </div>

        <div class="event-list">
          <button
            v-for="event in displayedEvents"
            :key="event.id"
            :data-event-id="event.id"
            class="event-row"
            :class="{ selected: selectedId === event.id }"
            type="button"
            @click="selectEvent(event.id)"
          >
            <span class="magnitude-badge" :style="{ '--mag-color': magnitudeColor(event.mag) }">{{ event.mag.toFixed(1) }}</span>
            <span class="event-copy">
              <strong>{{ localizedPlaceName(event.place, locale) || c.unknown }}</strong>
              <small>{{ relativeTime(event.time) }} · {{ c.depth }} {{ formatMeasurement(event.depth_km, 'km') }}</small>
            </span>
            <span class="event-chevron" aria-hidden="true">›</span>
          </button>

          <div v-if="!displayedEvents.length && !loading" class="empty-state">
            <strong>{{ c.noEvents }}</strong>
            <p>{{ c.noEventsHint }}</p>
          </div>
        </div>

        <div v-if="filteredEvents.length > MAX_LIST_ITEMS" class="list-note">
          {{ replaceToken(c.listLimit, { shown: MAX_LIST_ITEMS, total: filteredEvents.length }) }}
        </div>

        <div class="mobile-panel-links">
          <button type="button" @click="router.push('/history')">{{ c.history }}</button>
          <button type="button" @click="router.push('/terra/chat')">{{ c.workbench }}</button>
        </div>
      </aside>

      <aside v-if="selectedEvent" class="detail-panel">
        <div class="detail-head">
          <span>{{ c.detail }}</span>
          <button class="icon-button" type="button" :title="c.close" :aria-label="c.close" @click="selectedId = null">×</button>
        </div>
        <div class="detail-title">
          <span class="detail-magnitude" :style="{ color: magnitudeColor(selectedEvent.mag) }">M{{ selectedEvent.mag.toFixed(1) }}</span>
          <div><h2>{{ localizedPlaceName(selectedEvent.place, locale) }}</h2><p>{{ selectedEvent.id }}</p></div>
        </div>
        <dl class="detail-grid">
          <div><dt>{{ c.localTime }}</dt><dd>{{ formatLocalTime(selectedEvent.time) }}</dd></div>
          <div><dt>{{ c.utcTime }}</dt><dd>{{ formatUtcTime(selectedEvent.time) }}</dd></div>
          <div><dt>{{ c.depth }}</dt><dd>{{ formatMeasurement(selectedEvent.depth_km, 'km') }}</dd></div>
          <div><dt>{{ c.coordinates }}</dt><dd>{{ selectedEvent.lat.toFixed(4) }}, {{ selectedEvent.lon.toFixed(4) }}</dd></div>
          <div><dt>{{ c.network }}</dt><dd>{{ selectedEvent.net || c.notAvailable }}</dd></div>
          <div><dt>{{ c.eventType }}</dt><dd>{{ selectedEvent.type || c.notAvailable }}</dd></div>
          <div><dt>{{ c.status }}</dt><dd>{{ selectedEvent.status || c.notAvailable }}</dd></div>
          <div><dt>{{ c.updated }}</dt><dd>{{ formatUtcTime(selectedEvent.updated) }}</dd></div>
        </dl>
        <div class="quality-block">
          <span>{{ c.quality }}</span>
          <div><small>RMS</small><strong>{{ formatNumber(selectedEvent.rms, 2) }}</strong></div>
          <div><small>GAP</small><strong>{{ formatMeasurement(selectedEvent.gap, '°', 0) }}</strong></div>
          <div><small>ERR</small><strong>{{ formatMeasurement(selectedEvent.horizontalError, 'km', 1) }}</strong></div>
        </div>
        <div class="detail-actions">
          <button type="button" @click="copyCoordinates">{{ copied ? c.copied : c.copyCoordinates }}</button>
          <a v-if="selectedEvent.url" :href="selectedEvent.url" target="_blank" rel="noopener noreferrer">{{ c.external }} ↗</a>
        </div>
      </aside>

      <aside v-if="infoOpen" class="info-panel" role="dialog" :aria-label="c.systemTitle">
        <div class="detail-head"><span>{{ c.systemTitle }}</span><button class="icon-button" type="button" :aria-label="c.close" @click="infoOpen = false">×</button></div>
        <p>{{ c.systemText }}</p>
        <p class="info-note">{{ c.systemNote }}</p>
        <div class="source-row"><span>{{ sourceText }}</span><strong>{{ fetchedAt ? formatLocalTime(fetchedAt) : '—' }}</strong></div>
      </aside>

      <div v-if="errorMessage" class="error-banner" role="status">
        <div><strong>{{ c.loadError }}</strong><span v-if="events.length">{{ c.staleData }}</span></div>
        <button type="button" @click="loadCatalog()">{{ c.retry }}</button>
      </div>

      <div class="map-meta">
        <span>{{ c.mapCount }} <strong>{{ filteredEvents.length }}</strong></span>
        <span>{{ mapViewLabel }}</span>
        <span v-if="fetchedAt">{{ c.lastUpdated }} {{ relativeTime(fetchedAt) }}</span>
      </div>

      <div class="map-tools">
        <button type="button" :disabled="!filteredEvents.length" @click="fitEvents">{{ c.fitEvents }}</button>
      </div>

      <div class="legend" aria-label="Magnitude legend">
        <span><i style="--color:#21877d"></i>M3–4</span>
        <span><i style="--color:#c99a2e"></i>M4–5</span>
        <span><i style="--color:#dc673c"></i>M5–6</span>
        <span><i style="--color:#c9312f"></i>M6+</span>
      </div>
    </main>
  </div>
</template>

<style scoped>
.catalog-page {
  --ink: #111719;
  --muted: #667174;
  --line: #d9dfde;
  --paper: #f3f5f3;
  --white: #ffffff;
  --red: #c93a31;
  --teal: #187d79;
  --amber: #b98525;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  color: var(--ink);
  background: #dfe3e1;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.catalog-page *,
.catalog-page *::before,
.catalog-page *::after {
  box-sizing: border-box;
  letter-spacing: 0;
}

button, input, select { font: inherit; }
button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible { outline: 2px solid var(--red); outline-offset: 2px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }

.topbar {
  position: absolute;
  inset: 0 0 auto;
  z-index: 1200;
  height: 68px;
  display: grid;
  grid-template-columns: minmax(230px, 1fr) auto minmax(390px, 1fr);
  align-items: center;
  gap: 24px;
  padding: 0 22px;
  background: rgba(249, 250, 248, 0.97);
  border-bottom: 1px solid rgba(17, 23, 25, 0.14);
  backdrop-filter: blur(16px);
}

.brand {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 11px;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  cursor: pointer;
  text-align: left;
}
.brand img { width: 40px; height: 40px; object-fit: contain; flex: 0 0 auto; }
.brand > span { min-width: 0; display: grid; gap: 2px; }
.brand strong { font-size: 15px; line-height: 1.1; }
.brand small { color: var(--muted); font-size: 10px; white-space: nowrap; }

.connection-block { display: flex; align-items: center; gap: 9px; min-width: 160px; }
.connection-block > span:last-child { display: grid; gap: 1px; }
.connection-block strong { font-size: 11px; font-weight: 750; }
.connection-block small { color: var(--muted); font-size: 9px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #8b9697; box-shadow: 0 0 0 4px rgba(139, 150, 151, 0.13); }
.connection-block.live .status-dot { background: var(--teal); box-shadow: 0 0 0 4px rgba(24, 125, 121, 0.13); }
.connection-block.connecting .status-dot { background: var(--amber); animation: status-pulse 1.2s ease-in-out infinite; }
.connection-block.polling .status-dot { background: var(--amber); }
.connection-block.offline .status-dot { background: var(--red); }
@keyframes status-pulse { 50% { opacity: 0.35; } }

.header-actions { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }
.header-actions > button { min-height: 34px; padding: 0 10px; border: 0; color: #495153; background: transparent; cursor: pointer; font-size: 11px; font-weight: 650; white-space: nowrap; }
.header-actions > button:hover { color: var(--red); }
.header-actions .workbench-button { padding-inline: 13px; color: white; background: var(--ink); border: 1px solid var(--ink); border-radius: 6px; }
.header-actions .workbench-button:hover { color: white; background: var(--red); border-color: var(--red); }

.locale-switch { width: 65px; height: 30px; display: grid; grid-template-columns: 1fr 1fr; padding: 2px; border: 1px solid var(--line); border-radius: 6px; background: #eef1ef; }
.locale-switch button { padding: 0; border: 0; border-radius: 4px; color: var(--muted); background: transparent; cursor: pointer; font-size: 10px; font-weight: 750; }
.locale-switch button.active { color: var(--ink); background: white; box-shadow: 0 1px 3px rgba(17, 23, 25, 0.12); }

.filterbar {
  position: absolute;
  inset: 68px 0 auto;
  z-index: 1100;
  height: 70px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 18px;
  overflow-x: auto;
  background: rgba(245, 247, 245, 0.96);
  border-bottom: 1px solid rgba(17, 23, 25, 0.12);
  scrollbar-width: none;
}
.filterbar::-webkit-scrollbar { display: none; }
.search-control { flex: 1 1 220px; min-width: 190px; max-width: 310px; }
.search-control input { width: 100%; height: 42px; padding: 0 13px; border: 1px solid #cdd4d2; border-radius: 6px; color: var(--ink); background: white; font-size: 12px; outline: 0; }
.search-control input:focus { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(24, 125, 121, 0.1); }

.filter-group, .region-control { flex: 0 0 auto; display: grid; gap: 4px; }
.filter-label { color: var(--muted); font-size: 8px; font-weight: 800; text-transform: uppercase; }
.segmented-control { display: inline-flex; height: 30px; padding: 2px; border: 1px solid #d4dad8; border-radius: 6px; background: #e9edeb; }
.segmented-control button { min-width: 45px; padding: 0 8px; border: 0; border-radius: 4px; color: #5e686a; background: transparent; cursor: pointer; font-size: 10px; font-weight: 700; white-space: nowrap; }
.segmented-control button.active { color: var(--ink); background: white; box-shadow: 0 1px 3px rgba(17, 23, 25, 0.13); }
.magnitude-control button.active { color: var(--red); }
.region-control select { width: 142px; height: 30px; padding: 0 26px 0 9px; border: 1px solid #d4dad8; border-radius: 6px; color: var(--ink); background: white; font-size: 10px; outline: 0; }

.secondary-command, .primary-command { flex: 0 0 auto; min-height: 38px; padding: 0 13px; border-radius: 6px; cursor: pointer; font-size: 10px; font-weight: 750; white-space: nowrap; }
.secondary-command { border: 1px solid #cdd4d2; color: #3f494b; background: white; }
.secondary-command:hover { border-color: var(--teal); color: var(--teal); }
.primary-command { border: 1px solid var(--ink); color: white; background: var(--ink); }
.primary-command:hover:not(:disabled) { border-color: var(--red); background: var(--red); }
.primary-command:disabled { opacity: 0.55; cursor: wait; }

.map-stage { position: absolute; inset: 138px 0 0; overflow: hidden; }
.map-container { width: 100%; height: 100%; z-index: 0; background: #dfe3e1; }
.map-compliance-notice { position: absolute; z-index: 720; top: 16px; left: 50%; display: grid; gap: 3px; max-width: min(430px, calc(100% - 32px)); padding: 9px 13px; transform: translateX(-50%); border: 1px solid rgba(17, 23, 25, 0.16); border-radius: 5px; color: #465355; background: rgba(250, 252, 250, 0.94); box-shadow: 0 8px 20px rgba(17, 23, 25, 0.1); text-align: center; backdrop-filter: blur(8px); }
.map-compliance-notice strong { font-size: 10px; }
.map-compliance-notice span { color: var(--muted); font-size: 8px; line-height: 1.45; }
.map-compliance-notice.error { border-color: rgba(201, 49, 47, 0.3); color: #8b302c; }
.loading-line { position: absolute; z-index: 1300; inset: 0 0 auto; height: 3px; overflow: hidden; background: rgba(24, 125, 121, 0.12); }
.loading-line span { display: block; width: 34%; height: 100%; background: var(--teal); animation: loading-slide 1s ease-in-out infinite; }
@keyframes loading-slide { from { transform: translateX(-110%); } to { transform: translateX(330%); } }

.catalog-panel {
  position: absolute;
  z-index: 900;
  inset: 16px auto 16px 16px;
  width: 350px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(252, 253, 251, 0.97);
  border: 1px solid rgba(17, 23, 25, 0.14);
  border-radius: 7px;
  box-shadow: 0 18px 42px rgba(17, 23, 25, 0.13);
  backdrop-filter: blur(14px);
  transition: transform 220ms ease, opacity 180ms ease;
}
.catalog-panel.closed { transform: translateX(calc(-100% - 30px)); opacity: 0; pointer-events: none; }
.catalog-toggle { position: absolute; z-index: 880; top: 18px; left: 16px; width: 38px; height: 38px; border: 1px solid rgba(17, 23, 25, 0.18); border-radius: 6px; color: var(--ink); background: white; box-shadow: 0 8px 18px rgba(17, 23, 25, 0.12); cursor: pointer; font-size: 25px; line-height: 1; }

.panel-header { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; padding: 17px 17px 14px; border-bottom: 1px solid var(--line); }
.panel-header h1 { margin: 4px 0 2px; font-size: 18px; line-height: 1.2; }
.panel-header p { margin: 0; color: var(--muted); font-size: 10px; }
.eyebrow { color: var(--teal); font-family: "Fira Code", monospace; font-size: 8px; font-weight: 750; }
.panel-header-actions { display: flex; align-items: center; gap: 5px; }
.panel-header-actions > button:first-child { min-height: 30px; padding: 0 9px; border: 1px solid #d2d8d6; border-radius: 5px; color: #4d5759; background: white; cursor: pointer; font-size: 9px; font-weight: 700; }
.panel-header-actions > button:disabled { opacity: 0.45; cursor: not-allowed; }
.icon-button { width: 30px; height: 30px; padding: 0; border: 0; border-radius: 5px; color: #687375; background: transparent; cursor: pointer; font-size: 20px; line-height: 1; }
.icon-button:hover { color: var(--red); background: #f0f2f0; }

.stats-strip { display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid var(--line); background: #f2f4f2; }
.stats-strip div { min-width: 0; padding: 10px 7px; border-right: 1px solid var(--line); }
.stats-strip div:last-child { border-right: 0; }
.stats-strip span { display: block; overflow: hidden; color: var(--muted); font-size: 7px; text-overflow: ellipsis; white-space: nowrap; }
.stats-strip strong { display: block; margin-top: 3px; font-family: "Fira Code", monospace; font-size: 13px; }

.list-tools { min-height: 43px; display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 10px; border-bottom: 1px solid var(--line); }
.list-tools > span { overflow: hidden; color: var(--muted); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.list-sort { height: 28px; }
.list-sort button { min-width: 70px; font-size: 9px; }
.event-list { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
.event-row { position: relative; width: 100%; min-height: 68px; display: grid; grid-template-columns: 44px minmax(0, 1fr) 14px; gap: 10px; align-items: center; padding: 9px 12px; border: 0; border-bottom: 1px solid #e7ebe9; color: inherit; background: transparent; cursor: pointer; text-align: left; }
.event-row:hover { background: #f1f4f2; }
.event-row.selected { background: #e8efec; box-shadow: inset 3px 0 var(--teal); }
.magnitude-badge { width: 40px; height: 40px; display: grid; place-items: center; border: 1px solid color-mix(in srgb, var(--mag-color) 64%, white); border-radius: 50%; color: var(--mag-color); background: color-mix(in srgb, var(--mag-color) 9%, white); font-family: "Fira Code", monospace; font-size: 12px; font-weight: 800; }
.event-copy { min-width: 0; display: grid; gap: 5px; }
.event-copy strong { overflow: hidden; font-size: 11px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.event-copy small { overflow: hidden; color: var(--muted); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.event-chevron { color: #8b9596; font-size: 18px; }
.empty-state { min-height: 220px; display: grid; place-content: center; padding: 30px; text-align: center; }
.empty-state strong { font-size: 12px; }
.empty-state p { max-width: 230px; margin: 8px auto 0; color: var(--muted); font-size: 10px; line-height: 1.6; }
.list-note { padding: 8px 12px; color: var(--muted); background: #f3f5f3; border-top: 1px solid var(--line); font-size: 8px; line-height: 1.4; }
.mobile-panel-links { display: none; }

.detail-panel, .info-panel {
  position: absolute;
  z-index: 940;
  top: 16px;
  right: 16px;
  width: 330px;
  overflow: hidden;
  background: rgba(252, 253, 251, 0.98);
  border: 1px solid rgba(17, 23, 25, 0.16);
  border-radius: 7px;
  box-shadow: 0 20px 48px rgba(17, 23, 25, 0.16);
  backdrop-filter: blur(14px);
}
.detail-head { min-height: 44px; display: flex; align-items: center; justify-content: space-between; padding: 7px 10px 7px 15px; border-bottom: 1px solid var(--line); }
.detail-head > span { color: var(--muted); font-size: 9px; font-weight: 800; text-transform: uppercase; }
.detail-title { display: grid; grid-template-columns: auto 1fr; gap: 14px; align-items: center; padding: 18px 16px; border-bottom: 1px solid var(--line); }
.detail-magnitude { font-family: "Fira Code", monospace; font-size: 28px; font-weight: 800; }
.detail-title h2 { margin: 0; font-size: 14px; line-height: 1.45; }
.detail-title p { margin: 5px 0 0; color: var(--muted); font-family: "Fira Code", monospace; font-size: 8px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; margin: 0; }
.detail-grid div { min-width: 0; padding: 11px 14px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.detail-grid div:nth-child(even) { border-right: 0; }
.detail-grid dt { color: var(--muted); font-size: 8px; }
.detail-grid dd { margin: 5px 0 0; overflow-wrap: anywhere; font-family: "Fira Code", monospace; font-size: 10px; line-height: 1.45; }
.quality-block { display: grid; grid-template-columns: 1fr repeat(3, auto); gap: 14px; align-items: end; padding: 13px 14px; background: #f0f3f1; border-bottom: 1px solid var(--line); }
.quality-block > span { align-self: center; color: var(--muted); font-size: 8px; font-weight: 800; }
.quality-block div { display: grid; gap: 2px; }
.quality-block small { color: var(--muted); font-size: 7px; }
.quality-block strong { font-family: "Fira Code", monospace; font-size: 10px; }
.detail-actions { display: flex; gap: 8px; padding: 12px 14px; }
.detail-actions button, .detail-actions a { min-height: 34px; display: inline-flex; align-items: center; justify-content: center; padding: 0 12px; border-radius: 5px; font-size: 9px; font-weight: 750; text-decoration: none; }
.detail-actions button { border: 1px solid var(--ink); color: white; background: var(--ink); cursor: pointer; }
.detail-actions a { border: 1px solid #cfd6d3; color: var(--teal); background: white; }

.info-panel { padding-bottom: 4px; }
.info-panel > p { margin: 0; padding: 15px; color: #4e585a; font-size: 11px; line-height: 1.75; }
.info-panel .info-note { padding-top: 0; color: var(--muted); font-size: 9px; }
.source-row { display: flex; justify-content: space-between; gap: 14px; padding: 11px 15px; border-top: 1px solid var(--line); background: #f1f3f1; font-size: 8px; }
.source-row strong { font-family: "Fira Code", monospace; }

.error-banner { position: absolute; z-index: 930; top: 16px; left: 50%; min-width: 320px; max-width: 520px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 11px 12px 11px 15px; transform: translateX(-50%); border: 1px solid rgba(201, 58, 49, 0.34); border-radius: 6px; color: #7d2823; background: rgba(255, 248, 247, 0.97); box-shadow: 0 12px 28px rgba(17, 23, 25, 0.12); }
.error-banner div { display: grid; gap: 2px; }
.error-banner strong { font-size: 10px; }
.error-banner span { font-size: 8px; opacity: 0.72; }
.error-banner button { min-height: 30px; padding: 0 10px; border: 0; border-radius: 4px; color: white; background: var(--red); cursor: pointer; font-size: 9px; font-weight: 750; }

.map-meta { position: absolute; z-index: 700; bottom: 13px; left: 50%; display: flex; align-items: center; gap: 12px; padding: 7px 11px; transform: translateX(-50%); border: 1px solid rgba(17, 23, 25, 0.15); border-radius: 5px; color: #536062; background: rgba(252, 253, 251, 0.92); box-shadow: 0 6px 18px rgba(17, 23, 25, 0.1); backdrop-filter: blur(8px); font-family: "Fira Code", monospace; font-size: 8px; white-space: nowrap; }
.map-meta strong { color: var(--ink); }
.map-tools { position: absolute; z-index: 700; top: 16px; right: 16px; }
.map-tools button { min-height: 34px; padding: 0 11px; border: 1px solid rgba(17, 23, 25, 0.16); border-radius: 5px; color: #475254; background: rgba(252, 253, 251, 0.94); box-shadow: 0 7px 18px rgba(17, 23, 25, 0.1); cursor: pointer; font-size: 9px; font-weight: 700; }
.map-tools button:disabled { opacity: 0.45; cursor: not-allowed; }
.detail-panel ~ .map-tools, .info-panel ~ .map-tools { top: auto; right: 16px; bottom: 80px; }
.legend { position: absolute; z-index: 700; right: 16px; bottom: 42px; display: flex; gap: 9px; padding: 7px 10px; border: 1px solid rgba(17, 23, 25, 0.15); border-radius: 5px; color: #596466; background: rgba(252, 253, 251, 0.93); box-shadow: 0 6px 18px rgba(17, 23, 25, 0.1); font-size: 8px; }
.legend span { display: flex; align-items: center; gap: 4px; white-space: nowrap; }
.legend i { width: 7px; height: 7px; border-radius: 50%; background: var(--color); }

:deep(.leaflet-container) { background: #dfe3e1; font-family: inherit; }
:deep(.leaflet-tile-container img) { outline: 1px solid transparent; clip-path: inset(0 -1px 0 -1px); transform: translateZ(0); }
:deep(.leaflet-control-zoom) { margin-right: 16px !important; margin-bottom: 80px !important; border: 1px solid rgba(17, 23, 25, 0.16) !important; border-radius: 5px !important; overflow: hidden; box-shadow: 0 7px 18px rgba(17, 23, 25, 0.1) !important; }
:deep(.leaflet-control-zoom a) { color: var(--ink) !important; background: rgba(252, 253, 251, 0.96) !important; border-bottom-color: var(--line) !important; }
:deep(.leaflet-control-attribution) { margin: 0 5px 3px 0 !important; color: #687476; background: rgba(255, 255, 255, 0.72) !important; font-size: 7px !important; }
:deep(.quake-tooltip-shell) { padding: 0; border: 1px solid rgba(17, 23, 25, 0.14); border-radius: 5px; background: rgba(252, 253, 251, 0.97); box-shadow: 0 10px 24px rgba(17, 23, 25, 0.14); }
:deep(.quake-tooltip-shell::before) { border-top-color: rgba(252, 253, 251, 0.97); }
:deep(.quake-tooltip) { min-width: 170px; display: grid; gap: 4px; padding: 9px 11px; }
:deep(.quake-tooltip strong) { font-family: "Fira Code", monospace; font-size: 12px; }
:deep(.quake-tooltip span) { max-width: 240px; overflow: hidden; color: var(--ink); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
:deep(.quake-tooltip small) { color: var(--muted); font-size: 8px; }

@media (max-width: 1180px) {
  .topbar { grid-template-columns: minmax(210px, 1fr) auto minmax(300px, 1fr); gap: 14px; padding-inline: 16px; }
  .header-actions > button:not(.workbench-button) { display: none; }
  .filterbar { gap: 10px; }
  .search-control { max-width: 240px; }
}

@media (max-width: 820px) {
  .topbar { height: 64px; grid-template-columns: 1fr auto; padding: 0 12px; }
  .brand img { width: 36px; height: 36px; }
  .brand strong { font-size: 13px; }
  .brand small { display: none; }
  .connection-block { display: none; }
  .header-actions > button { display: none !important; }
  .header-actions { gap: 7px; }
  .locale-switch { display: grid; }
  .filterbar { inset-block-start: 64px; height: 68px; padding: 9px 10px; }
  .search-control { flex-basis: 190px; }
  .map-stage { inset-block-start: 132px; }
  .catalog-panel { inset: 0; width: 100%; border: 0; border-radius: 0; box-shadow: none; }
  .catalog-panel.closed { transform: translateX(-100%); }
  .catalog-toggle { top: 10px; left: 10px; }
  .mobile-panel-links { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px; border-top: 1px solid var(--line); }
  .mobile-panel-links button { min-height: 38px; border: 1px solid #d2d8d6; border-radius: 5px; color: var(--ink); background: white; font-size: 10px; font-weight: 700; }
  .detail-panel, .info-panel { top: auto; right: 8px; bottom: 8px; left: 8px; width: auto; max-height: calc(100% - 16px); overflow-y: auto; }
  .detail-grid { grid-template-columns: 1fr 1fr; }
  .map-meta { bottom: 8px; max-width: calc(100% - 20px); overflow: hidden; }
  .map-meta span:nth-child(2), .map-meta span:nth-child(3) { display: none; }
  .legend { right: 8px; bottom: 45px; }
  .map-tools { top: 10px; right: 8px; }
  .detail-panel ~ .map-tools, .info-panel ~ .map-tools { display: none; }
  :deep(.leaflet-control-zoom) { margin-right: 8px !important; margin-bottom: 74px !important; }
  .error-banner { top: 8px; width: calc(100% - 20px); min-width: 0; }
}

@media (max-width: 480px) {
  .filterbar { gap: 8px; }
  .search-control { min-width: 176px; }
  .secondary-command, .primary-command { min-height: 36px; }
  .stats-strip span { font-size: 6px; }
  .detail-title { padding: 14px; }
  .detail-magnitude { font-size: 24px; }
  .quality-block { gap: 9px; }
  .legend { gap: 6px; font-size: 7px; }
}

@media (prefers-reduced-motion: reduce) {
  .catalog-panel, .status-dot, .loading-line span { animation: none !important; transition: none !important; }
}
</style>
