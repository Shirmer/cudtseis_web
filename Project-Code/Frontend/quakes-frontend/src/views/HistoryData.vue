<template>
  <div class="history-page">
    <div class="page-header">
      <div class="title-group">
        <h2>历史数据分析中心</h2>
        <span class="subtitle">Professional Analysis Mode</span>
      </div>
      <button class="btn-back" @click="router.push('/dashboard')">
        <span class="icon">↩</span> 返回地图
      </button>
    </div>

    <!-- 查询面板 -->
    <div class="query-panel card">
      <div class="panel-header">
        <h3>检索条件</h3>
        <div class="quick-tags">
          <span>快捷时间：</span>
          <button @click="setQuickTime(1)">24小时</button>
          <button @click="setQuickTime(7)">7天</button>
          <button @click="setQuickTime(30)">30天</button>
          <button @click="setQuickTime(365)">1年</button>
        </div>
      </div>

      <div class="query-grid" @keyup.enter="doSearch">
        <div class="query-group">
          <label class="group-label">时间范围 (UTC)</label>
          <div class="input-row">
            <input 
              type="datetime-local" 
              step="1" 
              v-model="queryParams.start" 
              class="control" 
            />
            <span class="separator">至</span>
            <input 
              type="datetime-local" 
              step="1" 
              v-model="queryParams.end" 
              class="control" 
            />
          </div>
        </div>
        
        <div class="query-group">
          <label class="group-label">事件参数</label>
          <div class="param-row">
            <span class="param-name">震级 (M)</span>
            <div class="range-inputs">
              <input type="number" step="0.1" v-model.number="queryParams.minMag" placeholder="0" />
              <span class="range-dash">-</span>
              <input type="number" step="0.1" v-model.number="queryParams.maxMag" placeholder="Max" />
            </div>
          </div>
          <div class="param-row">
            <span class="param-name">深度 (km)</span>
            <div class="range-inputs">
              <input type="number" step="10" v-model.number="queryParams.minDepth" placeholder="0" />
              <span class="range-dash">-</span>
              <input type="number" step="10" v-model.number="queryParams.maxDepth" placeholder="Max" />
            </div>
          </div>
        </div>

        <div class="query-group">
          <label class="group-label">地理坐标</label>
          <div class="geo-inputs">
            <div class="geo-row">
              <span class="geo-label">Lon</span>
              <input type="number" step="0.1" v-model.number="queryParams.minLon" placeholder="Min" />
              <span class="range-dash">-</span>
              <input type="number" step="0.1" v-model.number="queryParams.maxLon" placeholder="Max" />
            </div>
            <div class="geo-row">
              <span class="geo-label">Lat</span>
              <input type="number" step="0.1" v-model.number="queryParams.minLat" placeholder="Min" />
              <span class="range-dash">-</span>
              <input type="number" step="0.1" v-model.number="queryParams.maxLat" placeholder="Max" />
            </div>
          </div>
        </div>
        
        <div class="action-group">
          <!-- 赛博蓝白底按钮 -->
          <button class="animated-button" @click="doSearch" :disabled="loading">
            <div v-if="loading" class="spinner"></div>
            
            <template v-else>
              <svg viewBox="0 0 24 24" class="arr-2" xmlns="http://www.w3.org/2000/svg">
                <path d="M16.1716 10.9999L10.8076 5.63589L12.2218 4.22168L20 11.9999L12.2218 19.778L10.8076 18.3638L16.1716 12.9999H4V10.9999H16.1716Z"></path>
              </svg>
              <span class="text">开始检索</span>
              <span class="circle"></span>
              <svg viewBox="0 0 24 24" class="arr-1" xmlns="http://www.w3.org/2000/svg">
                <path d="M16.1716 10.9999L10.8076 5.63589L12.2218 4.22168L20 11.9999L12.2218 19.778L10.8076 18.3638L16.1716 12.9999H4V10.9999H16.1716Z"></path>
              </svg>
            </template>
          </button>

          <button class="btn-secondary" @click="resetParams">重置</button>
        </div>
      </div>
    </div>

    <!-- 结果区域 -->
    <div class="results-panel card">
      <div class="results-header">
        <div class="stats-info" v-if="hasSearched">
          <span class="stat-item">找到 <strong>{{ results.length }}</strong> 条记录</span>
          <span class="stat-divider">|</span>
          <button class="btn-sort" @click="toggleSort">
            <span v-if="sortOrder === 'desc'">⬇️ 时间倒序 (最新在前)</span>
            <span v-else>⬆️ 时间正序 (最旧在前)</span>
          </button>
        </div>
        <div class="stats-info" v-else>
          请设置条件并点击检索
        </div>

        <div class="header-actions">
          <!-- 🔥 修改部分：新版分段控制器 -->
          <div class="radio-inputs">
            <label class="radio">
              <input 
                type="radio" 
                name="viewMode" 
                value="table" 
                :checked="viewMode === 'table'"
                @change="viewMode = 'table'"
              >
              <span class="name">列表视图</span>
            </label>
            <label class="radio">
              <input 
                type="radio" 
                name="viewMode" 
                value="map" 
                :checked="viewMode === 'map'"
                @change="switchMapMode"
              >
              <span class="name">地图视图</span>
            </label>
          </div>
         
          <button class="btn-export" @click="exportCSV" :disabled="results.length === 0">📥 导出 CSV</button>
        </div>
      </div>

      <div class="content-body">
        <div 
          v-show="viewMode === 'table'" 
          class="table-wrapper" 
          ref="tableWrapperRef"
          @scroll="onTableScroll"
          :class="{ 'scrolled': isTableScrolled }"
        >
          <table class="data-table">
            <thead>
              <tr>
                <th class="sticky-col sticky-header-col" width="180">
                  <div class="th-content">
                    时间 (UTC) 
                    <span class="sort-indicator">{{ sortOrder === 'desc' ? '↓' : '↑' }}</span>
                  </div>
                </th>
                <th width="70">震级</th>
                <th width="80">MagType</th>
                <th width="200">位置描述</th>
                <th width="80">深度(km)</th>
                <th width="80">经度</th>
                <th width="80">纬度</th>
                <th width="60">NST</th>
                <th width="60">Gap</th>
                <th width="60">Dmin</th>
                <th width="60">RMS</th>
                <th width="60">Net</th>
                <th width="80">Horiz Err</th>
                <th width="80">Depth Err</th>
                <th width="80">Mag Err</th>
                <th width="80">Status</th>
                <th width="100">Event ID</th>
                <th width="160">Updated</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sortedResults" :key="item.id">
                <td class="col-time sticky-col">{{ formatTime(item.time) }}</td>
                <td><span class="mag-badge" :class="getMagClass(item.mag)">M{{ item.mag }}</span></td>
                <td class="col-meta">{{ item.magType || '-' }}</td>
                <td class="col-place">{{ item.place }}</td>
                <td class="col-depth">{{ item.depth_km }}</td>
                <td class="col-geo">{{ item.lon.toFixed(2) }}</td>
                <td class="col-geo">{{ item.lat.toFixed(2) }}</td>
                <td class="col-meta">{{ item.nst || '-' }}</td>
                <td class="col-meta">{{ item.gap || '-' }}</td>
                <td class="col-meta">{{ item.dmin || '-' }}</td>
                <td class="col-meta">{{ item.rms || '-' }}</td>
                <td class="col-meta">{{ item.net || '-' }}</td>
                <td class="col-meta">{{ formatErr(item.horizontalError) }}</td>
                <td class="col-meta">{{ formatErr(item.depthError) }}</td>
                <td class="col-meta">{{ formatErr(item.magError) }}</td>
                <td class="col-meta">{{ item.status || '-' }}</td>
                <td class="col-id">{{ item.id }}</td>
                <td class="col-time-sm">{{ formatTime(item.updated) }}</td>
              </tr>
              <tr v-if="results.length === 0 && hasSearched && !loading">
                <td colspan="18" class="empty-state">未查询到符合条件的数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-show="viewMode === 'map'" class="map-wrapper">
          <MapVisual ref="mapVisualRef" :events="sortedResults" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import MapVisual from '../components/MapVisual.vue'
import { apiUrl } from '../config/api'

const router = useRouter()

const loading = ref(false)
const hasSearched = ref(false)
const results = ref<any[]>([])
const viewMode = ref<'table' | 'map'>('table')
const mapVisualRef = ref<any>(null)
const sortOrder = ref<'desc' | 'asc'>('desc')

const tableWrapperRef = ref<HTMLElement | null>(null)
const isTableScrolled = ref(false)

function onTableScroll(e: Event) {
  const target = e.target as HTMLElement
  isTableScrolled.value = target.scrollTop > 10
}

const queryParams = reactive({
  start: '',
  end: '',
  minMag: 3.0,
  maxMag: null as number | null,
  minDepth: null as number | null,
  maxDepth: null as number | null,
  minLon: null as number | null,
  maxLon: null as number | null,
  minLat: null as number | null,
  maxLat: null as number | null,
  limit: 2000
})

const sortedResults = computed(() => {
  if (results.value.length === 0) return []
  const list = [...results.value]
  return list.sort((a, b) => {
    const tA = new Date(a.time).getTime()
    const tB = new Date(b.time).getTime()
    return sortOrder.value === 'desc' ? tB - tA : tA - tB
  })
})

function toggleSort() {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

function switchMapMode() {
  viewMode.value = 'map'
  nextTick(() => { mapVisualRef.value?.resize() })
}

function setQuickTime(days: number) {
  const now = new Date()
  const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
  const toLocalISO = (d: Date) => {
    const pad = (n: number) => n.toString().padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }
  queryParams.end = toLocalISO(now)
  queryParams.start = toLocalISO(start)
}

function resetParams() {
  queryParams.start = ''
  queryParams.end = ''
  queryParams.minMag = 3.0
  queryParams.maxMag = null
  queryParams.minDepth = null
  queryParams.maxDepth = null
  queryParams.minLon = null
  queryParams.maxLon = null
  queryParams.minLat = null
  queryParams.maxLat = null
  hasSearched.value = false
  results.value = []
  isTableScrolled.value = false
  if (tableWrapperRef.value) tableWrapperRef.value.scrollTop = 0
}

function formatTime(isoString: string) {
  if (!isoString) return '-'
  return isoString.replace('T', ' ').slice(0, 19)
}

function formatErr(val: any) {
  return val !== null && val !== undefined ? val : '-'
}

function getMagClass(mag: number) {
  if (mag >= 6) return 'mag-high'
  if (mag >= 5) return 'mag-med'
  return 'mag-low'
}

function exportCSV() {
  if (results.value.length === 0) return
  const dataToExport = sortedResults.value
  const headerMap = {
      'id': 'EventID', 'time': 'Time(UTC)', 'mag': 'Magnitude', 'magType': 'MagType',
      'place': 'Place', 'depth_km': 'Depth(km)', 'lon': 'Longitude', 'lat': 'Latitude',
      'nst': 'NST', 'gap': 'Gap', 'dmin': 'Dmin', 'rms': 'RMS', 'net': 'Net',
      'type': 'Type', 'horizontalError': 'HorizErr', 'depthError': 'DepthErr',
      'magError': 'MagErr', 'magNst': 'MagNST', 'status': 'Status',
      'locationSource': 'LocSrc', 'magSource': 'MagSrc'
  }
  const headers = Object.values(headerMap)
  const keys = Object.keys(headerMap)
  const rows = dataToExport.map(item => {
      return keys.map(key => {
          let val = item[key]
          if (val === null || val === undefined) return ''
          if (typeof val === 'string' && val.includes(',')) return `"${val}"`
          return val
      }).join(',')
  })
  const csvContent = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `earthquake_data_${new Date().toISOString().slice(0,10)}.csv`)
  link.click()
}

async function doSearch() {
  loading.value = true
  hasSearched.value = true
  results.value = [] 
  try {
    const params = new URLSearchParams()
    if (queryParams.start) params.append('start', new Date(queryParams.start).toISOString())
    if (queryParams.end) params.append('end', new Date(queryParams.end).toISOString())
    params.append('minMag', queryParams.minMag.toString())
    if (queryParams.maxMag) params.append('maxMag', queryParams.maxMag.toString())
    if (queryParams.minDepth) params.append('minDepth', queryParams.minDepth.toString())
    if (queryParams.maxDepth) params.append('maxDepth', queryParams.maxDepth.toString())
    if (queryParams.minLon) params.append('minLon', queryParams.minLon.toString())
    if (queryParams.maxLon) params.append('maxLon', queryParams.maxLon.toString())
    if (queryParams.minLat) params.append('minLat', queryParams.minLat.toString())
    if (queryParams.maxLat) params.append('maxLat', queryParams.maxLat.toString())
    params.append('limit', queryParams.limit.toString())

    const url = apiUrl(`/events?${params.toString()}`)
    const res = await fetch(url)
    if (!res.ok) throw new Error('API Error')
    results.value = await res.json()
    sortOrder.value = 'desc'
    if (viewMode.value === 'map') nextTick(() => mapVisualRef.value?.resize())
  } catch (e) {
    console.error(e)
    alert("查询出错，请检查后端服务")
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 
   ========================
   1. 按钮样式 (白底赛博蓝)
   ========================
*/
.animated-button {
  --btn-color: #06b6d4; 
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 36px;
  background-color: #fff; 
  margin-top: 0; 
  border: 2px solid var(--btn-color);
  border-radius: 100px;
  font-size: 16px;
  font-weight: 600;
  color: var(--btn-color); 
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.1); 
  cursor: pointer;
  overflow: hidden;
  transition: all 0.6s cubic-bezier(0.23, 1, 0.32, 1);
  height: 48px; 
}

.animated-button svg {
  position: absolute;
  width: 22px;
  fill: var(--btn-color);
  z-index: 9;
  transition: all 0.6s cubic-bezier(0.23, 1, 0.32, 1);
}

.animated-button .arr-1 { right: 20px; }
.animated-button .arr-2 { left: -25%; }

.animated-button .circle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background-color: var(--btn-color);
  border-radius: 50%;
  opacity: 0;
  transition: all 0.8s cubic-bezier(0.23, 1, 0.32, 1);
}

.animated-button .text {
  position: relative;
  z-index: 1;
  margin-right: 12px; 
  transform: translateX(-6px);
  transition: all 0.6s cubic-bezier(0.23, 1, 0.32, 1);
}

.animated-button:hover {
  color: #fff; 
  box-shadow: 0 0 0 4px rgba(6, 182, 212, 0.2);
  border-color: transparent;
}
.animated-button:hover svg { fill: #fff; }
.animated-button:hover .arr-1 { right: -25%; }
.animated-button:hover .arr-2 { left: 20px; }
.animated-button:hover .text {
  transform: translateX(12px);
  margin-right: 0;
}
.animated-button:active {
  scale: 0.95;
  box-shadow: 0 0 0 2px var(--btn-color);
}
.animated-button:hover .circle {
  width: 220px;
  height: 220px;
  opacity: 1;
}
.animated-button:disabled {
  opacity: 0.7;
  cursor: wait;
  box-shadow: none;
  border-color: #999;
  color: #999;
}

/* Loading 状态 */
.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--btn-color);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 
   ========================
   2. 视图切换样式 (Radio Inputs)
   ========================
*/
.radio-inputs {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  border-radius: 0.5rem;
  background-color: #EEE;
  box-sizing: border-box;
  box-shadow: 0 0 0px 1px rgba(0, 0, 0, 0.06);
  padding: 0.25rem;
  width: 260px;
  font-size: 14px;
}
.radio-inputs .radio {
  flex: 1 1 auto;
  text-align: center;
}
.radio-inputs .radio input {
  display: none;
}
.radio-inputs .radio .name {
  display: flex;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  border: none;
  padding: .5rem 0;
  color: rgba(51, 65, 85, 1);
  transition: all .15s ease-in-out;
  font-weight: 500;
}
.radio-inputs .radio input:checked + .name {
  background-color: #fff;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  color: #06b6d4;
}

/* 
   ========================
   3. 布局微调
   ========================
*/
.action-group { 
  display: flex; 
  flex-direction: column; 
  gap: 10px; 
  /* 增加 padding-top 以便对齐左边的输入框标签 */
  padding-top: 28px; 
  align-items: flex-end; 
}
.btn-secondary { 
  background: white; 
  border: 1px solid #dcdfe6; 
  color: #606266; 
  padding: 10px 24px; 
  border-radius: 100px; 
  cursor: pointer; 
  transition: 0.2s; 
  height: 50px; /* 和主按钮高度一致 */
  font-weight: 500; 
  min-width: 100px; 
}
.btn-secondary:hover { border-color: #c0c4cc; background: #f4f4f5; }


/* 
   --------------------------
   表格样式 (Sticky)
   --------------------------
*/
.table-wrapper {
  max-height: 600px;
  overflow: auto;
  position: relative;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.data-table {
  min-width: 1500px;
  border-collapse: separate; 
  border-spacing: 0;
  font-size: 13px;
}
.data-table th {
  background: #f5f7fa;
  color: #909399;
  font-weight: 600;
  text-align: left;
  padding: 12px 12px;
  border-bottom: 1px solid #dcdfe6;
  box-shadow: 0 1px 0 #dcdfe6;
  position: sticky;
  top: 0;
  z-index: 10;
  transition: opacity 0.3s ease;
  opacity: 1; 
}
.sticky-col {
  position: sticky;
  left: 0;
  background-color: #fff;
  z-index: 5;
  border-right: 1px solid #ebeef5;
}
.sticky-header-col {
  z-index: 20 !important;
  background-color: #f5f7fa !important;
}
.table-wrapper.scrolled .data-table th {
  opacity: 0; 
  pointer-events: none; 
}
.table-wrapper:hover .data-table th {
  opacity: 1 !important; 
  pointer-events: auto;
}

/* --------------------------
   Layout & Components
   -------------------------- */
.data-table td { padding: 8px 12px; border-bottom: 1px solid #ebeef5; color: #606266; white-space: nowrap; background: #fff; }
.data-table tr:hover td { background-color: #f5f7fa; }
.history-page { max-width: 1400px; margin: 0 auto; padding: 24px; background-color: #f8f9fa; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #2c3e50; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.title-group h2 { margin: 0; font-size: 24px; color: #1a1a1a; }
.subtitle { font-size: 13px; color: #666; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }
.btn-back { background: white; border: 1px solid #dcdfe6; padding: 8px 16px; border-radius: 6px; cursor: pointer; color: #606266; transition: all 0.2s; display: flex; align-items: center; gap: 6px; font-weight: 500; }
.btn-back:hover { border-color: #409eff; color: #409eff; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #ebeef5; margin-bottom: 24px; overflow: hidden; }
.query-panel { padding: 24px; }
.panel-header { display: flex; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 15px; }
.panel-header h3 { margin: 0; font-size: 16px; font-weight: 600; color: #303133; margin-right: 20px; }
.quick-tags { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.quick-tags span { color: #909399; }
.quick-tags button { background: #f4f4f5; border: none; padding: 4px 10px; border-radius: 4px; color: #606266; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.quick-tags button:hover { background: #e9e9eb; color: #409eff; }
.query-grid { display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 1fr; gap: 24px; align-items: start; }
.group-label { display: block; font-size: 13px; color: #909399; margin-bottom: 8px; font-weight: 600; }
.input-row { display: flex; align-items: center; gap: 8px; }
.control { flex: 1; padding: 8px; border: 1px solid #dcdfe6; border-radius: 4px; width: 100%; outline: none; }
.control:focus { border-color: #409eff; }
.separator { color: #909399; font-size: 12px; }
.param-row { display: flex; align-items: center; margin-bottom: 10px; }
.param-name { width: 70px; font-size: 13px; color: #606266; }
.range-inputs { flex: 1; display: flex; align-items: center; }
.range-inputs input { width: 100%; padding: 6px 8px; border: 1px solid #dcdfe6; border-radius: 4px; outline: none; transition: 0.2s; font-family: monospace; }
.range-inputs input:focus { border-color: #409eff; }
.geo-row { display: flex; align-items: center; margin-bottom: 12px; }
.geo-label { width: 45px; text-align: right; margin-right: 12px; font-size: 13px; font-weight: 600; color: #606266; flex-shrink: 0; }
.geo-inputs .geo-row input { flex: 1; width: 0; padding: 6px 8px; border: 1px solid #dcdfe6; border-radius: 4px; outline: none; transition: 0.2s; font-family: monospace; }
.geo-inputs .geo-row input:focus { border-color: #409eff; }
.range-dash { margin: 0 8px; color: #c0c4cc; flex-shrink: 0; }

.results-header { padding: 16px 24px; border-bottom: 1px solid #ebeef5; background: #fafafa; display: flex; justify-content: space-between; align-items: center; }
.stats-info { font-size: 14px; color: #606266; display: flex; gap: 10px; align-items: center; }
.stat-divider { color: #dcdfe6; }
.stat-item strong { color: #303133; font-weight: 700; }
.btn-export { background: #303133; color: white; border: none; padding: 6px 16px; border-radius: 4px; font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: 0.2s; }
.btn-export:hover { background: #525457; }
.btn-export:disabled { background: #909399; cursor: not-allowed; }
.btn-sort { background: none; border: 1px solid #dcdfe6; border-radius: 4px; padding: 4px 10px; font-size: 13px; color: #606266; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 4px; }
.btn-sort:hover { border-color: #409eff; color: #409eff; background-color: #ecf5ff; }
.sort-indicator { margin-left: 4px; color: #409eff; }
.col-time { font-family: monospace; color: #303133; font-weight: 500; }
.col-time-sm { font-family: monospace; color: #909399; font-size: 12px; }
.col-id { color: #909399; font-size: 12px; font-family: monospace; }
.col-geo { font-family: monospace; }
.col-meta { color: #606266; }
.mag-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; color: white; font-weight: bold; font-size: 12px; min-width: 45px; text-align: center; }
.mag-high { background-color: #f56c6c; box-shadow: 0 2px 4px rgba(245, 108, 108, 0.3); }
.mag-med { background-color: #e6a23c; }
.mag-low { background-color: #67c23a; }
.empty-state { text-align: center; padding: 40px; color: #909399; font-style: italic; }
.header-actions { display: flex; align-items: center; gap: 16px; }
.map-wrapper { min-height: 600px; border-top: 1px solid #ebeef5; }
@media (max-width: 1000px) {
  .query-grid { grid-template-columns: 1fr 1fr; }
  .action-group { grid-column: span 2; padding-top: 0; flex-direction: row; justify-content: flex-end; }
  .header-actions { flex-direction: column; align-items: flex-end; gap: 10px; }
}
</style>
