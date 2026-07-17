import L from 'leaflet'

export type DomesticMapStatus = 'loading' | 'ready' | 'imagery' | 'error'

const token = (import.meta.env.VITE_TIANDITU_TOKEN ?? '').trim()
const approvalNumber = (import.meta.env.VITE_MAP_APPROVAL_NO ?? '').trim()
const subdomains = ['0', '1', '2', '3', '4', '5', '6', '7']
const nasaNaturalImageryUrl = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg'

export const domesticMapConfigured = token.length > 0

function tileUrl(layer: 'vec' | 'cva') {
  return `https://t{s}.tianditu.gov.cn/${layer}_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILECOL={x}&TILEROW={y}&TILEMATRIX={z}&tk=${encodeURIComponent(token)}`
}

function addCoordinateGrid(map: L.Map) {
  const style: L.PolylineOptions = {
    color: '#779095',
    weight: 0.7,
    opacity: 0.34,
    dashArray: '3 7',
    interactive: false,
  }
  const grid = L.layerGroup().addTo(map)

  for (let longitude = -180; longitude <= 180; longitude += 30) {
    L.polyline([[-80, longitude], [80, longitude]], style).addTo(grid)
  }
  for (let latitude = -60; latitude <= 60; latitude += 30) {
    const points: L.LatLngExpression[] = []
    for (let longitude = -180; longitude <= 180; longitude += 10) {
      points.push([latitude, longitude])
    }
    L.polyline(points, style).addTo(grid)
  }

  return grid
}

export function domesticMapAttribution(status: DomesticMapStatus) {
  if (status === 'ready') {
    return ['天地图', approvalNumber, 'USGS', 'CDUT SEISLAB'].filter(Boolean).join(' · ')
  }
  if (status === 'imagery' || status === 'loading') {
    return 'NASA Earthdata GIBS · USGS · CDUT SEISLAB'
  }
  return '安全经纬网 · USGS · CDUT SEISLAB'
}

function addNaturalImagery(
  map: L.Map,
  onStatus: (status: DomesticMapStatus) => void,
) {
  onStatus('loading')
  let loadedTiles = 0
  let failedTiles = 0
  let gridAdded = false

  const layer = L.tileLayer(nasaNaturalImageryUrl, {
    minZoom: 1,
    maxNativeZoom: 8,
    maxZoom: 16,
    noWrap: true,
    bounds: [[-85.051129, -180], [85.051129, 180]],
    updateWhenIdle: true,
    keepBuffer: 2,
    crossOrigin: true,
    opacity: 0.78,
    className: 'scientific-relief-tile',
  })

  layer.on('tileload', () => {
    loadedTiles += 1
    onStatus('imagery')
  })
  layer.on('tileerror', () => {
    failedTiles += 1
    if (loadedTiles > 0 || failedTiles < 2 || gridAdded) return
    gridAdded = true
    layer.remove()
    addCoordinateGrid(map)
    onStatus('error')
  })
  layer.addTo(map)
}

export function addDomesticBaseMap(
  map: L.Map,
  onStatus: (status: DomesticMapStatus) => void,
) {
  if (!domesticMapConfigured) {
    addNaturalImagery(map, onStatus)
    return
  }

  onStatus('loading')
  let loadedTiles = 0
  let failedTiles = 0
  let fallbackAdded = false

  const ensureFallback = () => {
    if (fallbackAdded) return
    fallbackAdded = true
    baseLayer.remove()
    annotationLayer.remove()
    addNaturalImagery(map, onStatus)
  }

  const baseLayer = L.tileLayer(tileUrl('vec'), {
    subdomains,
    minZoom: 1,
    maxZoom: 18,
    noWrap: true,
    updateWhenIdle: true,
    keepBuffer: 2,
    crossOrigin: true,
  })

  baseLayer.on('tileload', () => {
    loadedTiles += 1
    onStatus('ready')
  })
  baseLayer.on('tileerror', () => {
    failedTiles += 1
    if (loadedTiles === 0 && failedTiles >= 2) {
      ensureFallback()
      onStatus('error')
    }
  })
  baseLayer.addTo(map)

  const annotationLayer = L.tileLayer(tileUrl('cva'), {
    subdomains,
    minZoom: 1,
    maxZoom: 18,
    noWrap: true,
    updateWhenIdle: true,
    keepBuffer: 2,
    crossOrigin: true,
  }).addTo(map)
}
