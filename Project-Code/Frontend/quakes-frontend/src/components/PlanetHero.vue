<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { PlanetSceneHandle } from '../planet/planet-scene'
import type { HoverInfo, LayerInfo, YearBucket } from '../planet/layers/types'
import { PLANET_CONFIG } from '../planet/planet-config'

const props = withDefaults(defineProps<{ variant?: 'hero' | 'full'; locale?: 'zh' | 'en' }>(), {
  variant: 'hero',
  locale: 'zh'
})
const emit = defineEmits<{ expand: [] }>()

const hostEl = ref<HTMLElement | null>(null)
const ready = ref(false)
const failed = ref(false)
const zoom = ref(1)
const layers = ref<LayerInfo[]>([])
const hover = ref<HoverInfo | null>(null)
const timeline = ref<{ min: number; max: number } | null>(null)
const year = ref(0)
const playing = ref(false)
const touring = ref(false)
const shared = ref(false)
const histogram = ref<YearBucket[]>([])
const preloadLinks: HTMLLinkElement[] = []
const showGuide = ref(false)
const layerHint = ref<{ layerId: string; x: number; y: number } | null>(null)
const barHint = ref<{ year: number; count: number; peak: number; x: number; y: number } | null>(null)
const hintLayer = computed(() =>
  layerHint.value ? layers.value.find((item) => item.id === layerHint.value?.layerId) ?? null : null
)
const GUIDE_KEY = 'geocamera:earth-guide-v1'
const query = new URLSearchParams(window.location.search)
let sharedLayersApplied = false
let sharedYearApplied = false
let timeFrame = 0
let lastFrameTs = 0

let scene: PlanetSceneHandle | null = null
let intersection: IntersectionObserver | null = null
let resizeObserver: ResizeObserver | null = null
let heroVisible = true
let booted = false

const isFull = computed(() => props.variant === 'full')
const poster = computed(() => `${import.meta.env.BASE_URL}${isFull.value ? PLANET_CONFIG.assets.posterFull : PLANET_CONFIG.assets.poster}`)
const zoomPercent = () => `${Math.round(zoom.value * 100)}%`

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
  const width = hostEl.value.clientWidth
  const aspect = width / Math.max(hostEl.value.clientHeight, 1)
  const set = isFull.value ? PLANET_CONFIG.layout.full : PLANET_CONFIG.layout.hero
  // 竖屏时手机和平板差别很大，分开给参数
  const layout = aspect < 0.95
    ? width < 600 ? set.narrow : set.tablet
    : aspect < 1.45 ? set.medium : set.wide
  scene.setOffset(layout.x, layout.y, layout.scale)
}

function onVisibility() {
  scene?.setPaused(!heroVisible || document.hidden)
}

function zoomIn() {
  scene?.zoomIn()
}

function zoomOut() {
  scene?.zoomOut()
}

function resetView() {
  scene?.resetView()
}

function requestExpand() {
  emit('expand')
}

function toggleLayer(layer: LayerInfo) {
  scene?.setLayerVisible(layer.id, !layer.visible)
}

const LAYER_DESC: Record<string, { zh: string; en: string }> = {
  clouds: { zh: '全球云系，随地球缓慢漂移', en: 'Global cloud cover drifting with the planet' },
  quakes: { zh: '显著地震点位，可沿时间轴回放', en: 'Significant earthquakes, replayable on the timeline' },
  geo: { zh: '主要断裂带、板块边界与活火山', en: 'Major faults, plate boundaries and volcanoes' },
  weather: { zh: '活跃的气旋与风暴系统', en: 'Active cyclones and storm systems' },
  currents: { zh: '主要洋流路径与流向', en: 'Major ocean current paths' }
}

function layerHintDetail(layer: LayerInfo) {
  const desc = LAYER_DESC[layer.id]
  const parts: string[] = []
  if (desc) parts.push(props.locale === 'en' ? desc.en : desc.zh)
  if (layer.count) parts.push(props.locale === 'en' ? `${layer.count} items` : `${layer.count} 项`)
  if (layer.id === 'quakes' && timeline.value) {
    parts.push(`${Math.round(timeline.value.min)}–${Math.round(timeline.value.max)}`)
  }
  if (layer.meta?.updated) {
    parts.push(props.locale === 'en' ? `updated ${layer.meta.updated}` : `数据更新 ${layer.meta.updated}`)
  }
  return parts.join(' · ')
}

function showLayerHint(layer: LayerInfo, event: Event) {
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const rect = target.getBoundingClientRect()
  const narrow = window.innerWidth <= 900
  const width = 250
  const x = narrow
    ? Math.max(12, Math.min(rect.left, window.innerWidth - width - 12))
    : rect.right + 12
  const y = narrow ? rect.bottom + 8 : Math.max(12, rect.top - 4)
  layerHint.value = { layerId: layer.id, x, y }
}

function onLayerFocus(layer: LayerInfo, event: FocusEvent) {
  const target = event.target as HTMLElement | null
  // 只有键盘聚焦（:focus-visible）才弹提示，触摸点按不弹
  if (!target?.matches(':focus-visible')) return
  showLayerHint(layer, event)
}

// 时间轴分布条：按年统计事件数，空年份留一个很矮的底
const histogramBars = computed(() => {
  if (!timeline.value) return [] as { year: number; count: number; peak: number }[]
  const min = Math.round(timeline.value.min)
  const max = Math.round(timeline.value.max)
  if (max - min > 120) return []
  const byYear = new Map(histogram.value.map((item) => [item.year, item]))
  const bars: { year: number; count: number; peak: number }[] = []
  for (let year = min; year <= max; year += 1) {
    const bucket = byYear.get(year)
    bars.push({ year, count: bucket?.count ?? 0, peak: bucket?.peak ?? 0 })
  }
  return bars
})

const currentYear = computed(() => Math.floor(year.value))

function showBarHint(bar: { year: number; count: number; peak: number }, event: MouseEvent) {
  if (!bar.count) return
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const rect = target.getBoundingClientRect()
  barHint.value = { ...bar, x: rect.left + rect.width / 2, y: rect.top - 6 }
}

function jumpToYear(target: number) {
  if (!timeline.value) return
  year.value = Math.min(timeline.value.max, Math.max(timeline.value.min, target))
  scene?.setLayerTime('quakes', year.value)
}

const histogramPeak = computed(() => Math.max(1, ...histogramBars.value.map((bar) => bar.count)))

function layerLabel(layer: LayerInfo) {
  return props.locale === 'en' ? layer.nameEn : layer.name
}

function applySharedLayers() {
  if (!scene || sharedLayersApplied) return
  const raw = query.get('layers')
  if (!raw) return
  sharedLayersApplied = true
  const wanted = new Set(raw.split(',').map((id) => id.trim()).filter(Boolean))
  for (const layer of layers.value) {
    scene.setLayerVisible(layer.id, wanted.has(layer.id))
  }
}

function syncTimeline() {
  if (!scene) return
  const quakeLayer = layers.value.find((layer) => layer.id === 'quakes')
  if (!isFull.value || !quakeLayer?.visible) {
    timeline.value = null
    stopPlayback()
    return
  }
  const range = scene.getLayerTimeRange('quakes')
  if (!range) {
    timeline.value = null
    return
  }
  const reopening = timeline.value === null
  timeline.value = range
  // 数据源换了之后年份范围可能变化，越界就收回边界
  if (year.value > range.max) {
    year.value = range.max
    scene.setLayerTime('quakes', range.max)
  }
  // 分享链接里带的年份优先，且只应用一次
  const sharedYear = query.get('year')
  if (!sharedYearApplied && sharedYear && !Number.isNaN(Number(sharedYear))) {
    sharedYearApplied = true
    year.value = Math.min(range.max, Math.max(range.min, Number(sharedYear)))
    scene.setLayerTime('quakes', year.value)
    return
  }
  // 每次重新打开地震图层都回到「全部可见」，避免停留在上次的年份
  if (reopening || !year.value) {
    year.value = range.max
    scene.setLayerTime('quakes', range.max)
  }
}

function stopPlayback() {
  playing.value = false
  if (timeFrame) cancelAnimationFrame(timeFrame)
  timeFrame = 0
}

function tickPlayback(ts: number) {
  if (!playing.value || !timeline.value) return
  if (!lastFrameTs) lastFrameTs = ts
  const delta = Math.min(ts - lastFrameTs, 120)
  lastFrameTs = ts
  const next = Math.min(timeline.value.max, year.value + delta * 0.0035)
  year.value = next
  scene?.setLayerTime('quakes', next)
  if (next >= timeline.value.max - 0.001) {
    if (touring.value) {
      year.value = timeline.value.min
      scene?.setLayerTime('quakes', timeline.value.min)
    } else {
      stopPlayback()
      return
    }
  }
  timeFrame = requestAnimationFrame(tickPlayback)
}

function togglePlayback() {
  if (!timeline.value) return
  if (touring.value) stopTour()
  if (playing.value) {
    stopPlayback()
    return
  }
  if (year.value >= timeline.value.max - 0.01) {
    year.value = timeline.value.min
    scene?.setLayerTime('quakes', year.value)
  }
  playing.value = true
  lastFrameTs = 0
  timeFrame = requestAnimationFrame(tickPlayback)
}

function onYearInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  year.value = value
  scene?.setLayerTime('quakes', value)
}

function dismissGuide() {
  showGuide.value = false
  try {
    localStorage.setItem(GUIDE_KEY, '1')
  } catch {
    // 隐私模式下拿不到 localStorage，忽略即可
  }
}

function onKeydown(event: KeyboardEvent) {
  if (!isFull.value || !scene) return
  if (event.metaKey || event.ctrlKey || event.altKey) return
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea, [contenteditable="true"]')) return

  const step = 0.09
  switch (event.key) {
    case 'ArrowLeft':
      scene.rotateBy(step, 0)
      break
    case 'ArrowRight':
      scene.rotateBy(-step, 0)
      break
    case 'ArrowUp':
      scene.rotateBy(0, step)
      break
    case 'ArrowDown':
      scene.rotateBy(0, -step)
      break
    case '+':
    case '=':
      scene.zoomIn()
      break
    case '-':
    case '_':
      scene.zoomOut()
      break
    case 'r':
    case 'R':
      scene.resetView()
      break
    case ' ':
      if (timeline.value) togglePlayback()
      break
    default:
      return
  }
  dismissGuide()
  event.preventDefault()
}

function onStagePointerDown(event: PointerEvent) {
  dismissGuide()
  if (!touring.value) return
  const target = event.target as HTMLElement | null
  // 点控件不退出巡游，点地球才退出
  if (target?.closest('.planet-hud, .planet-layers, .planet-time')) return
  stopTour()
}

function stopTour() {
  if (!touring.value) return
  touring.value = false
  scene?.setTour(false)
  stopPlayback()
}

function toggleTour(event?: MouseEvent) {
  // 鼠标点完之后主动失焦：否则 :focus-within 会把压暗状态顶回去
  if (event && event.detail > 0) {
    ;(event.currentTarget as HTMLElement | null)?.blur()
  }
  if (touring.value) {
    stopTour()
    return
  }
  touring.value = true
  scene?.setTour(true)
  if (timeline.value) {
    year.value = timeline.value.min
    scene.setLayerTime('quakes', year.value)
    playing.value = true
    lastFrameTs = 0
    if (!timeFrame) timeFrame = requestAnimationFrame(tickPlayback)
  }
}

function shareView() {
  if (!scene) return
  const center = scene.getViewCenter()
  const params = new URLSearchParams()
  if (center) {
    params.set('lon', String(center.longitude))
    params.set('lat', String(center.latitude))
  }
  params.set('zoom', zoom.value.toFixed(2))
  const visible = layers.value.filter((layer) => layer.visible).map((layer) => layer.id)
  if (visible.length) params.set('layers', visible.join(','))
  if (timeline.value) params.set('year', String(Math.round(year.value)))

  const url = `${window.location.origin}${window.location.pathname}?${params.toString()}`
  if (import.meta.env.DEV) (window as unknown as Record<string, unknown>).__lastShareUrl = url

  const done = () => {
    shared.value = true
    window.setTimeout(() => { shared.value = false }, 1800)
  }
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(url).then(done).catch(done)
  } else {
    done()
  }
}

function saveView() {
  const dataUrl = scene?.capture()
  if (!dataUrl) return
  const stamp = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  const name = `deepseek-earth-${stamp.getFullYear()}${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}-${pad(stamp.getHours())}${pad(stamp.getMinutes())}.png`

  const download = (href: string) => {
    const link = document.createElement('a')
    link.href = href
    link.download = name
    link.click()
  }

  // 在导出图上压一行署名与视角信息，方便对外分享时知道是哪里的画面
  const image = new Image()
  image.onload = () => {
    try {
      const canvas = document.createElement('canvas')
      canvas.width = image.width
      canvas.height = image.height
      const context = canvas.getContext('2d')
      if (!context) {
        download(dataUrl)
        return
      }
      context.drawImage(image, 0, 0)

      const scale = Math.min(canvas.width, canvas.height)
      const padPx = Math.round(scale * 0.035)
      const fontSize = Math.max(12, Math.round(scale * 0.019))
      const baseline = canvas.height - padPx

      context.font = `500 ${fontSize}px "PingFang SC", "Microsoft YaHei", system-ui, sans-serif`
      context.textBaseline = 'alphabetic'
      context.shadowColor = 'rgba(0, 0, 0, 0.55)'
      context.shadowBlur = fontSize * 0.6

      context.textAlign = 'left'
      context.fillStyle = 'rgba(255, 255, 255, 0.72)'
      context.fillText('深视地球 · GeoCamera', padPx, baseline)

      const center = scene?.getViewCenter?.()
      const zoomPct = Math.round(zoom.value * 100)
      const bits: string[] = []
      if (center) {
        const coord = (value: number, positive: string, negative: string) =>
          `${Math.abs(value).toFixed(1)}°${value < 0 ? negative : positive}`
        bits.push(
          coord(center.longitude, 'E', 'W'),
          coord(center.latitude, 'N', 'S')
        )
      }
      bits.push(`${zoomPct}%`)
      if (year.value) bits.push(String(year.value))

      context.textAlign = 'right'
      context.fillStyle = 'rgba(255, 255, 255, 0.5)'
      context.fillText(bits.join('   '), canvas.width - padPx, baseline)
      download(canvas.toDataURL('image/png'))
    } catch {
      download(dataUrl)
    }
  }
  image.onerror = () => download(dataUrl)
  image.src = dataUrl
}

function tipStyle() {
  if (!hover.value) return {}
  const width = 232
  const height = 74
  const gap = 16
  const x = Math.min(hover.value.x + gap, window.innerWidth - width - 10)
  const y = Math.min(hover.value.y + gap, window.innerHeight - height - 10)
  return { left: `${Math.max(10, x)}px`, top: `${Math.max(10, y)}px` }
}

async function boot() {
  if (booted || !hostEl.value || !supports3d()) return
  booted = true
  try {
    // 模型下载和下面的动态 import 并行，别等分块下完再开始拿 489KB 的 glb
    const modelBuffer = fetch(`${import.meta.env.BASE_URL}${PLANET_CONFIG.assets.model}`, {
      credentials: 'same-origin'
    }).then((response) => {
      if (!response.ok) throw new Error(`model HTTP ${response.status}`)
      return response.arrayBuffer()
    })
    modelBuffer.catch(() => undefined)

    // 白天/夜景贴图是首帧的必要资源，但请求写在场景模块里，只能等分块下完。
    // 先在这里用 preload 起个头，等场景要图时直接命中缓存。
    for (const relative of [PLANET_CONFIG.assets.dayMap, PLANET_CONFIG.assets.nightMap]) {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.as = 'image'
      link.href = `${import.meta.env.BASE_URL}${relative}`
      document.head.appendChild(link)
      preloadLinks.push(link)
    }

    const { createPlanetScene } = await import('../planet/planet-scene')
    if (!hostEl.value) return
    scene = createPlanetScene(hostEl.value, {
      onReady: () => { ready.value = true },
      onError: () => { failed.value = true },
      onZoom: (value) => { zoom.value = value },
      onLayers: (list) => {
        layers.value = list
        // 回调发生在 createPlanetScene 返回之前，等句柄赋值后再同步时间轴
        queueMicrotask(() => {
          applySharedLayers()
          syncTimeline()
          histogram.value = scene?.getLayerHistogram?.('quakes') ?? []
        })
      },
      onHover: (info) => { hover.value = info },
      // 只有全屏页需要悬停信息卡，首页保持干净
      picking: isFull.value,
      // 首页那颗是装饰性的，1.5x 足够省填充率；全屏页保持 2x
      maxPixelRatio: isFull.value ? 2 : 1.5,
      modelBuffer
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
    hostEl.value.addEventListener('pointerdown', onStagePointerDown, true)
    if (isFull.value) {
      window.addEventListener('keydown', onKeydown)
      try {
        showGuide.value = localStorage.getItem(GUIDE_KEY) !== '1'
      } catch {
        showGuide.value = false
      }
      if (showGuide.value) window.setTimeout(() => { showGuide.value = false }, 9000)
    }
  } catch {
    failed.value = true
  }
}

onMounted(boot)

onBeforeUnmount(() => {
  stopPlayback()
  for (const link of preloadLinks.splice(0)) link.remove()
  window.removeEventListener('keydown', onKeydown)
  hostEl.value?.removeEventListener('pointerdown', onStagePointerDown, true)
  document.removeEventListener('visibilitychange', onVisibility)
  intersection?.disconnect()
  resizeObserver?.disconnect()
  scene?.dispose()
  scene = null
})
</script>

<template>
  <div
  ref="hostEl"
  class="planet-stage"
  :class="{ 'is-ready': ready, 'is-failed': failed, 'is-full': isFull, 'is-touring': touring }"
>
    <img class="planet-poster" :src="poster" alt="" aria-hidden="true" />
    <p class="planet-loading" :class="{ 'is-hidden': ready || failed }" role="status">
      <span class="planet-loading-dot" aria-hidden="true"></span>正在加载地球
    </p>
    <div class="planet-hud">
      <div class="planet-actions">
        <button
          v-if="!isFull"
          type="button"
          class="planet-expand"
          aria-label="全屏查看地球"
          @click="requestExpand"
        >
          <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4">
            <path d="M6 2H2v4M10 14h4v-4M14 6V2h-4M2 10v4h4" />
          </svg>
          全屏地球
        </button>
        <div v-if="isFull && ready" class="planet-tools" role="group" aria-label="视角工具">
          <button type="button" class="planet-tool" aria-label="复制当前视角链接" @click="shareView">
            <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4">
              <path d="M6.5 9.5 9.5 6.5M6 11.5 4.5 13a2.1 2.1 0 0 1-3-3L5 6.5M10 4.5 11.5 3a2.1 2.1 0 0 1 3 3L11 9.5" />
            </svg>
            {{ shared ? '已复制' : '分享' }}
          </button>
          <button
            type="button"
            class="planet-tool"
            :class="{ 'is-on': touring }"
            :aria-pressed="touring"
            :aria-label="touring ? '停止巡游' : '开始自动巡游'"
            @click="toggleTour"
          >
            <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4">
              <circle cx="8" cy="8" r="5.6" />
              <path d="M6.6 5.6 10.4 8l-3.8 2.4z" fill="currentColor" stroke="none" />
            </svg>
            巡游
          </button>
          <button type="button" class="planet-tool" aria-label="保存当前视角" @click="saveView">
            <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4">
              <path d="M8 2v8m0 0 3-3m-3 3L5 7M2.5 12.5v1h11v-1" />
            </svg>
            保存
          </button>
        </div>
        <div v-if="ready" class="planet-zoom" role="group" aria-label="地球缩放">
          <button
            type="button"
            aria-label="缩小"
            :disabled="zoom <= PLANET_CONFIG.zoom.min + 0.001"
            @click="zoomOut"
          >−</button>
          <output class="planet-zoom-value" aria-label="当前缩放">{{ zoomPercent() }}</output>
          <button
            type="button"
            aria-label="放大"
            :disabled="zoom >= PLANET_CONFIG.zoom.max - 0.001"
            @click="zoomIn"
          >＋</button>
          <span class="planet-zoom-divider" aria-hidden="true"></span>
          <button type="button" aria-label="复位视角" @click="resetView">复位</button>
        </div>
      </div>
      <p v-if="!isFull && ready" class="planet-hint">拖动旋转 · 双击复位 · ⌘/Ctrl + 滚轮缩放</p>
    </div>

    <div v-if="isFull && showGuide" class="planet-guide">
      <p>拖动旋转 · 点击点位查看详情<br />底栏回放地震 · 右下角可「巡游」</p>
      <button type="button" @click="dismissGuide">开始探索</button>
    </div>

    <div v-if="isFull && timeline" class="planet-time">
      <button
        type="button"
        class="planet-time-play"
        :aria-label="playing ? '暂停回放' : '回放地震'"
        @click="togglePlayback"
      >
        <svg v-if="!playing" viewBox="0 0 12 12" width="11" height="11" aria-hidden="true"><path d="M3 1.5v9l7-4.5z" fill="currentColor" /></svg>
        <svg v-else viewBox="0 0 12 12" width="11" height="11" aria-hidden="true"><path d="M2.5 1.5h2.5v9H2.5zM7 1.5h2.5v9H7z" fill="currentColor" /></svg>
      </button>
      <div class="planet-time-track">
        <div v-if="histogramBars.length" class="planet-time-bars" aria-hidden="true">
          <button
            v-for="bar in histogramBars"
            :key="bar.year"
            type="button"
            class="planet-time-bar"
            tabindex="-1"
            @mouseenter="showBarHint(bar, $event)"
            @mouseleave="barHint = null"
            @click="jumpToYear(bar.year)"
          >
            <i
              :class="{
                'is-empty': !bar.count,
                'is-strong': bar.peak >= 7.5,
                'is-major': bar.peak >= 8.5,
                'is-current': bar.year === currentYear
              }"
              :style="{ height: `${bar.count ? 32 + (bar.count / histogramPeak) * 68 : 12}%` }"
            />
          </button>
        </div>
        <input
          class="planet-time-range"
          type="range"
          :min="timeline.min"
          :max="timeline.max"
          step="0.05"
          :value="year"
          aria-label="地震时间轴"
          @input="onYearInput"
        />
      </div>
      <output class="planet-time-year">{{ Math.floor(year) }}</output>
    </div>

    <div
      v-if="barHint"
      class="planet-tip planet-bar-hint"
      :style="{ left: `${barHint.x}px`, top: `${barHint.y}px` }"
      role="status"
    >
      <span class="planet-tip-body">
        <strong>{{ barHint.year }} 年</strong>
        <span>{{ barHint.count }} 条 · 最大 M{{ barHint.peak.toFixed(1) }}</span>
      </span>
    </div>

    <div
      v-if="layerHint && hintLayer"
      class="planet-tip planet-layer-hint"
      :style="{ left: `${layerHint.x}px`, top: `${layerHint.y}px` }"
      role="status"
    >
      <span class="planet-tip-body">
        <strong>{{ layerLabel(hintLayer) }}</strong>
        <span>{{ layerHintDetail(hintLayer) }}</span>
      </span>
    </div>

    <div v-if="hover" class="planet-tip" :style="tipStyle()" role="status" aria-live="polite">
      <span class="planet-tip-dot" :class="`is-${hover.layerId}`" aria-hidden="true"></span>
      <span class="planet-tip-body">
        <strong>{{ hover.label }}</strong>
        <span v-if="hover.detail">{{ hover.detail }}</span>
      </span>
    </div>

    <div v-if="isFull && layers.length" class="planet-layers" role="group" aria-label="图层">
      <button
        v-for="layer in layers"
        :key="layer.id"
        type="button"
        class="planet-layer"
        :class="[{ 'is-on': layer.visible }, `is-${layer.id}`]"
        :aria-pressed="layer.visible"
        @click="toggleLayer(layer)"
        @mouseenter="showLayerHint(layer, $event)"
        @mouseleave="layerHint = null"
        @focus="onLayerFocus(layer, $event)"
        @blur="layerHint = null"
      >
        <span class="planet-layer-dot" aria-hidden="true"></span>
        {{ layerLabel(layer) }}
        <span v-if="layer.count" class="planet-layer-count">{{ layer.count }}</span>
      </button>
    </div>
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
  transform-origin: 50% 46%;
  transition: opacity 1100ms ease, transform 1600ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* 海报淡出的同时轻微推近，像是镜头穿进画面 */
.planet-stage.is-ready .planet-poster {
  opacity: 0;
  transform: scale(1.07);
}

.planet-loading {
  position: absolute;
  left: 50%;
  bottom: clamp(96px, 15vh, 150px);
  transform: translateX(-50%);
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.5);
  backdrop-filter: blur(8px);
  color: rgba(255, 255, 255, 0.72);
  font-size: 11.5px;
  letter-spacing: 0.14em;
  pointer-events: none;
  transition: opacity 420ms ease;
}

.planet-loading.is-hidden {
  opacity: 0;
}

.planet-loading-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--amber, #d97a1c);
  animation: loading-pulse 1.4s ease-in-out infinite;
}

@keyframes loading-pulse {
  0%, 100% { opacity: 0.35; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1); }
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

.planet-hud {
  position: absolute;
  right: clamp(20px, 4vw, 56px);
  bottom: 172px;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  letter-spacing: 0.08em;
}

.planet-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.planet-expand {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.58);
  backdrop-filter: blur(10px);
  color: inherit;
  font: inherit;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 180ms ease, border-color 180ms ease, color 180ms ease;
}

.planet-expand:active,
.planet-zoom button:active:not(:disabled),
.planet-time-play:active,
.planet-layer:active {
  transform: scale(0.96);
}

.planet-expand {
  border-color: rgba(217, 122, 28, 0.7);
  background: rgba(217, 122, 28, 0.82);
  color: #fff;
}

.planet-zoom {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  height: 40px;
  padding: 4px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.58);
  backdrop-filter: blur(10px);
}

.planet-zoom button {
  min-width: 32px;
  height: 30px;
  padding: 0 10px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease, transform 120ms ease;
}

.planet-zoom button:hover:not(:disabled) {
  background: rgba(217, 122, 28, 0.9);
  color: #fff;
}

.planet-zoom button:disabled {
  opacity: 0.35;
  cursor: default;
}

.planet-zoom-value {
  min-width: 46px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  color: #fff;
}

.planet-zoom-divider {
  width: 1px;
  height: 16px;
  margin: 0 2px;
  background: rgba(255, 255, 255, 0.18);
}

.planet-hint {
  margin: 0;
  padding-right: 4px;
  color: rgba(255, 255, 255, 0.42);
}

/* 巡游时把次要控件压暗，让地球成为主体；鼠标移上去恢复 */
.planet-stage.is-touring .planet-layers,
.planet-stage.is-touring .planet-hud {
  opacity: 0.34;
  transition: opacity 420ms ease;
}

.planet-stage.is-touring .planet-layers:hover,
.planet-stage.is-touring .planet-layers:focus-within,
.planet-stage.is-touring .planet-hud:hover,
.planet-stage.is-touring .planet-hud:focus-within {
  opacity: 1;
}

/* 玻璃面板：统一盒模型、高度 40、内高光 */
.planet-expand,
.planet-layer,
.planet-tools,
.planet-zoom {
  box-sizing: border-box;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}


/* 键盘焦点：只在键盘操作时显示，避免鼠标点击出现描边 */
.planet-expand:focus-visible,
.planet-tool:focus-visible,
.planet-layer:focus-visible,
.planet-zoom button:focus-visible,
.planet-time-play:focus-visible,
.planet-guide button:focus-visible,
.planet-time-range:focus-visible {
  outline: 2px solid var(--amber, #d97a1c);
  outline-offset: 2px;
  border-radius: 999px;
}

/* 入场编排：不同层按顺序淡入 */
@keyframes ui-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes ui-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

.planet-layers {
  /* backwards：动画结束后把 opacity 交还给样式表，巡游压暗才能生效 */
  animation: ui-fade 520ms ease backwards;
  animation-delay: 140ms;
}

.planet-hud {
  animation: ui-rise 520ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
  animation-delay: 260ms;
}

.planet-time {
  animation: ui-fade 520ms ease backwards;
  animation-delay: 200ms;
}

/* 首次进入引导 */
.planet-guide {
  position: absolute;
  left: 50%;
  bottom: clamp(120px, 18vh, 180px);
  transform: translateX(-50%);
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 22px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  background: rgba(6, 12, 20, 0.78);
  backdrop-filter: blur(14px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  color: rgba(255, 255, 255, 0.78);
  text-align: center;
  animation: guide-in 420ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.planet-guide p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  letter-spacing: 0.08em;
}

.planet-guide button {
  height: 30px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  background: rgba(217, 122, 28, 0.9);
  color: #fff;
  font: inherit;
  font-size: 12px;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: background 160ms ease;
}

.planet-guide button:hover {
  background: rgba(217, 122, 28, 1);
}

@keyframes guide-in {
  from { opacity: 0; transform: translate(-50%, 8px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}

/* 时间轴 */
.planet-time {
  position: absolute;
  left: 50%;
  bottom: clamp(18px, 3vh, 34px);
  transform: translateX(-50%);
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 12px;
  width: min(460px, calc(100% - 32px));
  padding: 8px 16px 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.62);
  backdrop-filter: blur(12px);
}

.planet-time-play {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  cursor: pointer;
  transition: background 160ms ease, transform 120ms ease;
}

.planet-time-play:hover {
  background: rgba(217, 122, 28, 0.9);
}

.planet-time-track {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
}

/* 按年份的事件分布，帮人一眼看出哪几年密集 */
.planet-time-bars {
  display: flex;
  align-items: flex-end;
  gap: 1px;
  height: 10px;
  padding: 0 4px;
}

/* 外层只负责命中区和点击，真正的高度画在 i 上 */
.planet-time-bar {
  flex: 1;
  height: 100%;
  min-width: 0;
  display: flex;
  align-items: flex-end;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
}

.planet-time-bar i {
  width: 100%;
  min-height: 1px;
  border-radius: 2px;
  background: rgba(217, 122, 28, 0.55);
  transition: filter 140ms ease;
}

.planet-time-bar:hover i {
  filter: brightness(1.14);
}

.planet-time-bar i.is-strong {
  background: rgba(242, 152, 52, 0.8);
}

.planet-time-bar i.is-major {
  background: rgba(255, 186, 92, 1);
}

.planet-time-bar i.is-empty {
  background: rgba(255, 255, 255, 0.12);
}

/* 当前年份的柱子当播放头，用白色标出来 */
.planet-time-bar i.is-current {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 0 7px rgba(255, 255, 255, 0.5);
}

.planet-time-range {
  width: 100%;
  height: 3px;
  accent-color: var(--amber, #d97a1c);
  cursor: pointer;
}

.planet-time-year {
  flex: none;
  min-width: 46px;
  text-align: right;
  color: #fff;
  font-size: 13px;
  letter-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
}

/* 悬停信息卡 */
.planet-tip {
  position: fixed;
  z-index: 6;
  display: flex;
  align-items: flex-start;
  gap: 9px;
  max-width: 232px;
  padding: 10px 13px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  background: rgba(6, 12, 20, 0.86);
  backdrop-filter: blur(14px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  color: #fff;
  pointer-events: none;
  animation: tip-in 140ms ease-out;
}

.planet-layer-hint {
  max-width: 250px;
}

/* 分布条的浮层：锚在柱子上方居中 */
.planet-bar-hint {
  transform: translate(-50%, -100%);
  padding: 7px 11px;
  text-align: center;
}

.planet-bar-hint .planet-tip-body {
  align-items: center;
}

.planet-tip-dot {
  flex: none;
  width: 7px;
  height: 7px;
  margin-top: 6px;
  border-radius: 50%;
  background: #d97a1c;
  box-shadow: 0 0 8px currentColor;
}

.planet-tip-dot.is-quakes { background: #ff6a3d; }
.planet-tip-dot.is-geo { background: #ffb03a; }
.planet-tip-dot.is-weather { background: #7fc4ff; }
.planet-tip-dot.is-currents { background: #5fe0ff; }

.planet-tip-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.planet-tip-body strong {
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.3;
}

.planet-tip-body span {
  font-size: 11px;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.55);
  font-variant-numeric: tabular-nums;
}

@keyframes tip-in {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: none; }
}

/* 图层开关：全屏页左侧竖排 */
.planet-layers {
  position: absolute;
  left: clamp(16px, 3vw, 40px);
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.planet-layer {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  height: 40px;
  padding: 0 16px 0 13px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.56);
  backdrop-filter: blur(10px);
  color: rgba(255, 255, 255, 0.62);
  font: inherit;
  font-size: 12px;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: color 180ms ease, border-color 180ms ease, background 180ms ease, transform 120ms ease;
}

.planet-layer.is-on {
  border-color: rgba(217, 122, 28, 0.55);
  color: #fff;
}

.planet-layer:hover {
  background: rgba(6, 12, 20, 0.8);
}

.planet-layer-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  transition: background 180ms ease, box-shadow 180ms ease;
}

.planet-layer.is-on .planet-layer-dot {
  background: var(--amber, #d97a1c);
  box-shadow: 0 0 10px rgba(217, 122, 28, 0.8);
}

/* 每个图层的点色和地球上一致，充当图例 */
.planet-layer.is-on.is-quakes .planet-layer-dot {
  background: #ff6a3d;
  box-shadow: 0 0 10px rgba(255, 106, 61, 0.8);
}

.planet-layer.is-on.is-geo .planet-layer-dot {
  background: #ffb03a;
  box-shadow: 0 0 10px rgba(255, 176, 58, 0.8);
}

.planet-layer.is-on.is-weather .planet-layer-dot {
  background: #7fc4ff;
  box-shadow: 0 0 10px rgba(127, 196, 255, 0.8);
}

.planet-layer.is-on.is-currents .planet-layer-dot {
  background: #5fe0ff;
  box-shadow: 0 0 10px rgba(95, 224, 255, 0.8);
}

.planet-layer.is-on.is-clouds .planet-layer-dot {
  background: #e8eef6;
  box-shadow: 0 0 10px rgba(232, 238, 246, 0.7);
}

.planet-layer-count {
  margin-left: 2px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 10.5px;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}

.planet-layer.is-on .planet-layer-count {
  color: rgba(255, 255, 255, 0.62);
}

.planet-tools {
  display: inline-flex;
  align-items: center;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  background: rgba(6, 12, 20, 0.58);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.planet-tool {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 100%;
  padding: 0 14px;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 180ms ease, color 180ms ease, transform 120ms ease;
}

.planet-tool + .planet-tool {
  border-left: 1px solid rgba(255, 255, 255, 0.1);
}

.planet-tool:hover {
  background: rgba(217, 122, 28, 0.72);
  color: #fff;
}

.planet-tool.is-on {
  background: rgba(217, 122, 28, 0.88);
  color: #fff;
}

.planet-tool:active {
  transform: scale(0.97);
}

.planet-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* 全屏页：控件贴着右下角 */
.planet-stage.is-full .planet-hud {
  right: clamp(16px, 3vw, 40px);
  bottom: clamp(16px, 3vh, 36px);
}

@media (prefers-reduced-motion: reduce) {
  .planet-poster {
    transition: opacity 200ms linear;
  }

  .planet-stage.is-ready .planet-poster {
    transform: none;
  }

  .planet-layers,
  .planet-hud,
  .planet-time {
    animation: none;
  }
}

@media (max-width: 380px) {
  .planet-time {
    gap: 8px;
    padding: 6px 12px 6px 8px;
  }

  .planet-tool {
    padding: 0 11px;
  }
}

@media (max-width: 900px) {
  /* 竖屏平板：图层条也放到顶部横排，避免压在地球上 */
  .planet-layers {
    top: 76px;
    left: 16px;
    right: 16px;
    transform: none;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
  }

  .planet-layer {
    height: 32px;
    padding: 0 13px 0 11px;
    font-size: 11px;
  }
}

/* 手机横屏：首页那颗装饰地球只留「全屏地球」入口，别压住文案 */
@media (max-height: 520px) and (orientation: landscape) {
  /* 首页 hero 比视口高时，地球层固定在首屏高度，入口按钮才不会被推到屏幕外 */
  .planet-stage:not(.is-full) {
    inset: 0 0 auto 0;
    height: 100vh;
  }

  .planet-stage:not(.is-full) .planet-hud {
    right: 16px;
    bottom: 16px;
  }

  .planet-stage:not(.is-full) .planet-zoom,
  .planet-stage:not(.is-full) .planet-hint {
    display: none;
  }
}

/* 宽度不够（常见笔记本 / 平板横屏）时，时间轴抬到工具条上方，避免横向相撞 */
@media (min-width: 721px) and (max-width: 1410px) {
  .planet-time {
    bottom: 86px;
  }
}

/* 手机横屏：竖向空间紧张，底部控件改为上下两层，去掉提示文字 */
@media (max-height: 520px) and (orientation: landscape) {
  .planet-stage.is-full .planet-hud {
    right: 16px;
    bottom: 66px;
  }

  .planet-time {
    bottom: 14px;
    width: min(440px, calc(100% - 330px));
  }

  .planet-layers {
    top: 64px;
  }

  .planet-layer-hint {
    display: none;
  }
}

@media (max-width: 720px) {
  .planet-hud {
    right: 16px;
    bottom: 150px;
  }

  .planet-hint {
    display: none;
  }

  .planet-stage.is-full .planet-hud {
    right: 16px;
    bottom: 24px;
  }

  .planet-time {
    /* 工具条是「分段控件 + 缩放条」两行（40 + 10 + 40），时间轴要压到它上面 */
    bottom: 124px;
    width: calc(100% - 32px);
  }

  /* 手机：图层改成顶部横排，避免压在球面上 */
  .planet-layers {
    top: 76px;
    left: 16px;
    right: 16px;
    transform: none;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
  }

  .planet-layer {
    height: 32px;
    padding: 0 13px 0 11px;
    font-size: 11px;
  }
}
</style>
