import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { PLANET_CONFIG } from './planet-config'
import { CloudLayer } from './layers/cloud-layer'
import { CurrentLayer } from './layers/current-layer'
import { GEO_LINES, GEO_SITES } from './layers/geo-data'
import { GeoLayer } from './layers/geo-layer'
import { CURRENT_PATHS } from './layers/current-data'
import { STORM_CELLS } from './layers/weather-data'
import { WeatherLayer } from './layers/weather-layer'
import { LayerManager } from './layers/layer-manager'
import { QUAKE_EVENTS } from './layers/quake-data'
import { loadQuakeFeed } from './layers/quake-source'
import { QuakeLayer } from './layers/quake-layer'
import type { HoverInfo, LayerContext, LayerInfo, PlanetLayer } from './layers/types'

export interface PlanetSceneOptions {
  onReady?: () => void
  onError?: () => void
  /** 缩放变化时回调，用于界面上显示倍数 */
  onZoom?: (zoom: number) => void
  /** 图层列表变化（初始化、开关、透明度） */
  onLayers?: (layers: LayerInfo[]) => void
  /** 鼠标悬停到可拾取元素时回调（移开时传 null） */
  onHover?: (info: HoverInfo | null) => void
  /** 是否开启悬停拾取（首页只做装饰时关掉） */
  picking?: boolean
  /** 像素比上限覆盖（首页那颗装饰地球不需要满分辨率） */
  maxPixelRatio?: number
  /** 调用方提前发起的模型下载，和动态 import 并行，省掉一次串行 */
  modelBuffer?: Promise<ArrayBuffer>
}

export interface PlanetSceneHandle {
  setOffset(x: number, y: number, scale?: number): void
  setPaused(paused: boolean): void
  zoomIn(): void
  zoomOut(): void
  resetView(): void
  getZoom(): number
  getLayers(): LayerInfo[]
  /** 取图层实例，用于 setData 之类运行期操作 */
  getLayer(id: string): PlanetLayer | undefined
  /** 设置图层时间轴（年） */
  setLayerTime(id: string, value: number): void
  /** 图层时间轴范围，没有时间维度时返回 null */
  getLayerTimeRange(id: string): { min: number; max: number } | null
  /** 把当前画面导出成 PNG dataURL（只含 3D，不含 DOM 控件） */
  capture(): string | null
  /** 巡游模式：强制自转并加速，任意交互会关掉它 */
  setTour(enabled: boolean): void
  /** 当前正对镜头的经纬度（用于生成分享链接） */
  getViewCenter(): { longitude: number; latitude: number } | null
  /** 键盘/程序控制的旋转增量 */
  rotateBy(yaw: number, pitch: number): void
  /** 当前画质等级：0 完整 / 1 已关云层 / 2 再关天气 */
  getQuality(): number
  /** 手动设置画质等级（性能自适应内部走的也是它） */
  setQuality(level: number): void
  /** 某图层的按年事件分布，用来画时间轴分布条 */
  getLayerHistogram(id: string): { year: number; count: number; peak: number }[]
  /** 运行时统计（调试用）：拾取次数、画质等级、当前像素比与上限 */
  getStats(): {
    frames: number
    picks: number
    quality: number
    pixelRatio: number
    maxRatio: number
    calls: number
    triangles: number
  }
  setLayerVisible(id: string, visible: boolean): void
  setLayerOpacity(id: string, opacity: number): void
  dispose(): void
}

const CONFIG = PLANET_CONFIG
const asset = (path: string) => `${import.meta.env.BASE_URL}${path}`

// 调试/美术调参：?lon=116&lat=39 指定初始朝向，?spin=0 冻结自转，?perf 显示帧率。
const QUERY = new URLSearchParams(window.location.search)
const numberParam = (key: string, fallback: number) => {
  const raw = QUERY.get(key)
  const value = raw === null ? Number.NaN : Number(raw)
  return Number.isFinite(value) ? value : fallback
}
const INITIAL_LONGITUDE = numberParam('lon', CONFIG.initial.longitude)
const INITIAL_LATITUDE = numberParam('lat', CONFIG.initial.latitude)
const SPIN_ENABLED = CONFIG.spin.enabled && QUERY.get('spin') !== '0'
const INITIAL_ZOOM = THREE.MathUtils.clamp(numberParam('zoom', 1), CONFIG.zoom.min, CONFIG.zoom.max)

const PLANET_POSITION = new THREE.Vector3().fromArray(CONFIG.planet.position)
const CAMERA_TARGET = new THREE.Vector3().fromArray(CONFIG.camera.target)
const CAMERA_ORIGIN = new THREE.Vector3().fromArray(CONFIG.camera.position)
const VIEW_DIRECTION = CAMERA_ORIGIN.clone().sub(CAMERA_TARGET).normalize()
const BASE_DISTANCE = CAMERA_ORIGIN.distanceTo(CAMERA_TARGET)
const SUN_DIRECTION = new THREE.Vector3().fromArray(CONFIG.sunDirection).normalize()

function cinematicFov(baseFov: number, referenceAspect: number, aspect: number) {
  return THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(baseFov) / 2) * Math.max(1, referenceAspect / aspect)))
}

/**
 * 找到 UV 上离目标经纬度最近的顶点，再把它转到镜头方向。
 * 这样换任意球体模型 / 任意等距柱状贴图都不用重新试角度。
 */
function faceQuaternion(
  mesh: THREE.Mesh,
  longitude: number,
  latitude: number,
  pivotWorld: THREE.Vector3,
  cameraPosition: THREE.Vector3
) {
  const uv = mesh.geometry.getAttribute('uv')
  const position = mesh.geometry.getAttribute('position')
  // 等距柱状贴图：u 从西经 180° 起算，v 从北极（图片顶部）起算
  const u = (longitude + 180) / 360
  const v = (90 - latitude) / 180
  let best = 0
  let bestDistance = Infinity
  for (let i = 0; i < uv.count; i += 1) {
    let du = uv.getX(i) - u
    du -= Math.round(du)
    const dv = uv.getY(i) - v
    const distance = du * du + dv * dv
    if (distance < bestDistance) {
      bestDistance = distance
      best = i
    }
  }
  const local = new THREE.Vector3().fromBufferAttribute(position, best).normalize()
  // 朝向要按「星球世界位置 -> 当前相机」算：分享链接可能带着缩放，
  // 相机离得更近时，正对镜头的点本来就会偏一点。
  const toCamera = cameraPosition.clone().sub(pivotWorld).normalize()
  return new THREE.Quaternion().setFromUnitVectors(local, toCamera)
}

export function createPlanetScene(host: HTMLElement, options: PlanetSceneOptions = {}): PlanetSceneHandle {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.AgXToneMapping
  renderer.toneMappingExposure = 2 ** 0.35
  renderer.setClearColor(0x02040a, 1)
  // 触屏设备（手机/平板）像素比上限收到 1.6：3x 屏按 2x 渲染是纯填充率浪费，
  // 地球本身是柔和的大气画面，1.6x 观感几乎无差别，像素量少约 35%
  const coarsePointer = window.matchMedia?.('(pointer: coarse)').matches ?? false
  const pixelRatioCeiling = Math.min(
    coarsePointer ? 1.6 : 2,
    options.maxPixelRatio ?? 2
  )
  const maxPixelRatio = Math.min(window.devicePixelRatio || 1, pixelRatioCeiling)
  const minPixelRatio = 0.75
  let pixelRatio = Math.min(maxPixelRatio, 1.5)
  renderer.setPixelRatio(pixelRatio)
  const canvas = renderer.domElement
  canvas.setAttribute('aria-hidden', 'true')
  canvas.style.touchAction = 'pan-y'
  host.appendChild(canvas)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(CONFIG.camera.fov, 1, CONFIG.camera.near, CONFIG.camera.far)
  camera.position.copy(CAMERA_ORIGIN)
  camera.lookAt(CAMERA_TARGET)

  // Whole composition can slide horizontally/vertically for hero layouts.
  const composer = new THREE.Group()
  scene.add(composer)

  const planetPivot = new THREE.Group()
  planetPivot.position.copy(PLANET_POSITION)
  composer.add(planetPivot)

  // 贴在地表的内容都挂在这里：朝向放在父级，图层就能直接用星球本地坐标
  // （半径 = CONFIG.planet.radius，北极 +Y）而不用关心初始朝向。
  const surfaceGroup = new THREE.Group()
  planetPivot.add(surfaceGroup)

  let planetMesh: THREE.Mesh | null = null
  let background: THREE.Texture | null = null
  const textures = new Set<THREE.Texture>()
  let disposed = false
  let paused = false
  let running = false
  let frameId = 0
  let ready = false
  let lastInteractionAt = performance.now()
  let highQualityTimer = 0
  let layers: LayerManager | null = null
  let elapsed = 0

  // Zoom lives on the camera so the planet keeps its light and atmosphere.
  let zoom = INITIAL_ZOOM
  let zoomTarget = INITIAL_ZOOM
  let introStart = 0
  let introBoost = 1

  // 悬停拾取：把图层的本地坐标投到屏幕上比距离，比 raycast 便宜得多
  const PICK_RADIUS = 16
  const PICK_INTERVAL = 80
  const projected = new THREE.Vector3()
  const planetCenterWorld = new THREE.Vector3()
  const cameraDirection = new THREE.Vector3()
  let hovered: { layerId: string; id: string } | null = null
  const hoveredPosition = new THREE.Vector3()
  const pointerDownAt = { x: 0, y: 0, time: 0 }
  let focus: { yaw: number; pitch: number } | null = null
  let focusHoldUntil = 0
  let touring = false
  let surfaceUniforms: Record<string, THREE.IUniform> | null = null
  let pendingDetail: THREE.Texture | null = null
  /** 0 = 完整, 1 = 关云层, 2 = 再关天气 */
  let qualityLevel = 0
  /** 被画质系统关掉的图层，升档时只还原这些 */
  const disabledByQuality = new Set<string>()
  let detailFadeStart = 0
  let pointer: { x: number; y: number } | null = null
  let lastPickAt = 0
  /** 指针或场景是否变化过；没变化就不用重复拾取 */
  let pickDirty = true
  let lastPickSignature = Number.NaN
  let pickCount = 0
  let frameCount = 0
  /** 缓存的 canvas 矩形；滚动/尺寸变化才重新读，避免每次移动都强制布局 */
  let canvasRect = { left: 0, top: 0, width: 0, height: 0 }
  let rectDirty = true

  function markRectDirty() {
    rectDirty = true
  }

  const perf = {
    hud: new URLSearchParams(window.location.search).has('perf') ? document.createElement('div') : null,
    warmup: 90,
    frames: 0,
    totalMs: 0,
    cooldownUntil: 0,
    samples: [] as number[],
    refreshHz: 60
  }
  if (perf.hud) {
    perf.hud.style.cssText =
      'position:absolute;left:12px;bottom:44px;z-index:9;pointer-events:none;padding:6px 10px;border-radius:8px;background:rgba(4,10,20,0.78);border:1px solid rgba(120,180,255,0.18);color:#9fd0ff;font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:nowrap'
    host.appendChild(perf.hud)
  }

  const geometryCache: THREE.BufferGeometry[] = []
  const materialCache: THREE.Material[] = []

  function trackTexture(texture: THREE.Texture) {
    textures.add(texture)
    return texture
  }

  const atmosphereShells: THREE.Mesh[] = []

  function addAtmosphere() {
    const geometry = new THREE.SphereGeometry(1, 64, 32)
    geometryCache.push(geometry)
    for (const layer of CONFIG.atmosphere.layers) {
      const material = new THREE.ShaderMaterial({
        uniforms: {
          tint: { value: new THREE.Color().fromArray(layer.color).multiplyScalar(layer.emission) },
          power: { value: layer.power },
          opacity: { value: layer.opacity },
          sunDirection: { value: SUN_DIRECTION.clone() },
          ambient: { value: 0.1 }
        },
        vertexShader: `varying vec3 worldNormal; varying vec3 worldPosition;
          void main(){ vec4 world = modelMatrix * vec4(position, 1.0); worldPosition = world.xyz;
          worldNormal = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * world; }`,
        fragmentShader: `uniform vec3 tint; uniform float power; uniform float opacity;
          uniform vec3 sunDirection; uniform float ambient; varying vec3 worldNormal; varying vec3 worldPosition;
          void main(){
            vec3 n = normalize(worldNormal);
            vec3 v = normalize(cameraPosition - worldPosition);
            float rim = pow(1.0 - clamp(abs(dot(n, v)), 0.0, 1.0), power);
            float sunFacing = max(dot(n, sunDirection), 0.0);
            float light = sunFacing + ambient;

            // 朝阳侧偏暖、背阳侧偏冷，让边缘光有方向感而不是一圈死蓝
            vec3 warm = tint * vec3(1.16, 1.02, 0.86);
            vec3 cool = tint * vec3(0.66, 0.82, 1.18);
            vec3 color = mix(cool, warm, pow(sunFacing, 0.75));

            gl_FragColor = vec4(color, clamp(rim * opacity * light, 0.0, 1.0));
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
          }`,
        transparent: true,
        depthWrite: false,
        blending: (layer as { blending?: string }).blending === 'additive' ? THREE.AdditiveBlending : THREE.NormalBlending,
        side: THREE.FrontSide
      })
      materialCache.push(material)
      const shell = new THREE.Mesh(geometry, material)
      shell.position.copy(PLANET_POSITION)
      shell.scale.setScalar(layer.radius)
      composer.add(shell)
      atmosphereShells.push(shell)
    }
  }

  function addLights() {
    for (const spec of CONFIG.lights) {
      const light = new THREE.DirectionalLight(new THREE.Color().fromArray(spec.color), spec.intensity)
      light.position.fromArray(spec.position)
      light.target.position.copy(PLANET_POSITION)
      composer.add(light, light.target)
    }
    composer.add(new THREE.AmbientLight(new THREE.Color().fromArray(CONFIG.ambient.color), CONFIG.ambient.intensity))
  }

  addAtmosphere()
  addLights()

  const textureLoader = new THREE.TextureLoader()

  function loadTexture(path: string) {
    return new Promise<THREE.Texture>((resolve, reject) => {
      textureLoader.load(
        asset(path),
        (texture) => {
          if (disposed) {
            texture.dispose()
            reject(new Error('disposed'))
            return
          }
          // glTF 的 UV 以左上角为原点，和贴图一致时不能再翻转
          texture.flipY = false
          texture.colorSpace = THREE.SRGBColorSpace
          texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8)
          resolve(trackTexture(texture))
        },
        undefined,
        () => reject(new Error(`texture unavailable: ${path}`))
      )
    })
  }

  /**
   * 表面材质增强（一次注入，两件事）：
   * 1. 夜面城市灯光：用太阳方向压暗夜面，只让背光一侧透出夜景贴图
   * 2. 海面高光：用白天贴图的蓝-红色差判断海洋，把海洋的粗糙度调低，
   *    阳光会在洋面上留下镜面反光，陆地保持粗糙
   */
  function enhanceSurfaceMaterial(material: THREE.MeshStandardMaterial, nightMap: THREE.Texture | null) {
    const oceanLow = (CONFIG.material.oceanThreshold - CONFIG.material.oceanSoftness).toFixed(3)
    const oceanHigh = (CONFIG.material.oceanThreshold + CONFIG.material.oceanSoftness).toFixed(3)
    const oceanRoughness = CONFIG.material.oceanRoughness.toFixed(3)

    material.onBeforeCompile = (shader) => {
      shader.uniforms.detailMap = { value: null }
      shader.uniforms.detailMix = { value: 0 }
      shader.uniforms.sunDirection = { value: SUN_DIRECTION.clone() }
      shader.uniforms.twilightIntensity = { value: CONFIG.material.twilightIntensity }
      shader.uniforms.hazeIntensity = { value: CONFIG.material.hazeIntensity }
      if (nightMap) {
        shader.uniforms.nightMap = { value: nightMap }
        shader.uniforms.nightIntensity = { value: CONFIG.material.nightIntensity }
      }

      const declarations = [
        'uniform sampler2D detailMap;',
        'uniform float detailMix;',
        'uniform float twilightIntensity;',
        'uniform float hazeIntensity;',
        'uniform vec3 sunDirection;',
        nightMap ? 'uniform sampler2D nightMap;\nuniform float nightIntensity;' : ''
      ].filter(Boolean).join('\n')

      // 发光项一次性接管：夜面城市灯 + 晨昏暖光 + 星球边缘大气内辉光
      const emissive = [
        `vec3 sunView = normalize(mat3(viewMatrix) * sunDirection);
         float sunDot = dot(normal, sunView);
         float daylight = smoothstep(-0.18, 0.32, sunDot);
         totalEmissiveRadiance = vec3(0.0);`,
        nightMap
          ? 'totalEmissiveRadiance += texture2D(nightMap, vMapUv).rgb * nightIntensity * (1.0 - daylight);'
          : '',
        `float twilight = smoothstep(-0.06, 0.05, sunDot) * (1.0 - smoothstep(0.05, 0.22, sunDot));
         totalEmissiveRadiance += vec3(1.0, 0.42, 0.16) * twilight * twilightIntensity;`,
        `vec3 viewDir = normalize(vViewPosition);
         float planetRim = pow(1.0 - clamp(dot(normal, viewDir), 0.0, 1.0), 3.0);
         totalEmissiveRadiance += vec3(0.24, 0.44, 0.9) * planetRim * daylight * hazeIntensity;`
      ].filter(Boolean).join('\n')

      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>\n${declarations}`)
        // 2K -> 4K 贴图交叉淡入，避免瞬切闪一下
        .replace(
          '#include <map_fragment>',
          `vec4 baseSample = texture2D(map, vMapUv);
           vec4 detailSample = texture2D(detailMap, vMapUv);
           diffuseColor *= mix(baseSample, detailSample, detailMix);`
        )
        .replace('#include <emissivemap_fragment>', emissive)
        .replace(
          '#include <roughnessmap_fragment>',
          `#include <roughnessmap_fragment>
           // 复用 map_fragment 已经采过的颜色，避免同一张大贴图再取一次
           vec3 oceanSample = mix(baseSample.rgb, detailSample.rgb, detailMix);
           // 深蓝海洋在线性空间里也很暗，用「蓝色占比」比蓝-红差值稳
           float oceanRatio = oceanSample.b / max(oceanSample.r + oceanSample.g + oceanSample.b, 1e-4);
           float oceanMask = smoothstep(${oceanLow}, ${oceanHigh}, oceanRatio);
           roughnessFactor = mix(roughnessFactor, ${oceanRoughness}, oceanMask);`
        )
    }

    // 海洋会变光滑，这里把整体高光强度压下来，避免出现一个刺眼的白点
    const physical = material as THREE.MeshPhysicalMaterial
    if ('specularIntensity' in physical) physical.specularIntensity = CONFIG.material.oceanSpecular
    const compile = material.onBeforeCompile
    material.onBeforeCompile = (shader, renderer) => {
      compile.call(material, shader, renderer)
      surfaceUniforms = shader.uniforms as Record<string, THREE.IUniform>
    }
    material.customProgramCacheKey = () => 'planet-surface-v5'
    material.needsUpdate = true
  }

  function preparePlanet(mesh: THREE.Mesh, dayMap: THREE.Texture, nightMap: THREE.Texture | null) {
    mesh.position.set(0, 0, 0)
    const pivotWorld = PLANET_POSITION.clone()
    composer.localToWorld(pivotWorld)
    surfaceGroup.quaternion.copy(
      faceQuaternion(mesh, INITIAL_LONGITUDE, INITIAL_LATITUDE, pivotWorld, camera.position)
    )
    const material = mesh.material as THREE.MeshStandardMaterial
    material.roughness = CONFIG.material.roughness
    material.metalness = 0
    const previous = material.map
    material.map = dayMap
    material.emissiveMap = null
    material.needsUpdate = true
    previous?.dispose()
    const useNight = Boolean(nightMap && CONFIG.material.nightLights)
    if (!useNight) material.emissive.setRGB(0, 0, 0)
    enhanceSurfaceMaterial(material, useNight ? nightMap : null)
    surfaceGroup.add(mesh)
    planetMesh = mesh
    mesh.visible = true
    // 星球真正出现时才开始入场镜头，避免在加载期间白白播完
    introStart = performance.now()
    introBoost = 1.08
    buildLayers(mesh.geometry)
    renderer.compile(scene, camera)
  }

  /**
   * 注册图层。新增可视化（洋流、地质事件、温度场……）在这里加一段，
   * 图层自己实现 PlanetLayer 即可，渲染循环和 UI 都会自动接上。
   */
  function buildLayers(planetGeometry: THREE.BufferGeometry) {
    layers?.dispose()
    const manager = new LayerManager()
    const context: LayerContext = {
      pivot: surfaceGroup,
      scene,
      planetGeometry,
      radius: CONFIG.planet.radius,
      sunDirection: SUN_DIRECTION.clone(),
      camera,
      renderer,
      assetUrl: asset,
      now: () => new Date()
    }

    const clouds = CONFIG.layers.clouds
    manager.add(
      new CloudLayer(context, {
        texture: clouds.texture,
        altitude: clouds.altitude,
        opacity: clouds.opacity,
        drift: clouds.drift,
        threshold: clouds.threshold,
        softness: clouds.softness,
        tint: clouds.tint as [number, number, number]
      }),
      { visible: clouds.enabled, opacity: clouds.opacity }
    )

    const quakes = CONFIG.layers.quakes
    manager.add(
      new QuakeLayer(context, QUAKE_EVENTS, {
        color: quakes.color as [number, number, number],
        size: quakes.size,
        magnitudeScale: quakes.magnitudeScale,
        altitude: quakes.altitude,
        opacity: quakes.opacity,
        ripple: {
          enabled: quakes.ripple.enabled,
          minMagnitude: quakes.ripple.minMagnitude,
          life: quakes.ripple.life,
          maxRadius: quakes.ripple.maxRadius,
          color: quakes.ripple.color as [number, number, number],
          max: quakes.ripple.max
        }
      }),
      { visible: quakes.enabled, opacity: quakes.opacity }
    )

    const geo = CONFIG.layers.geo
    manager.add(
      new GeoLayer(context, GEO_LINES, GEO_SITES, {
        altitude: geo.altitude,
        opacity: geo.opacity,
        lineColor: geo.lineColor as [number, number, number],
        siteColor: geo.siteColor as [number, number, number],
        lineOpacity: geo.lineOpacity,
        siteSize: geo.siteSize
      }),
      { visible: geo.enabled, opacity: geo.opacity }
    )

    const weather = CONFIG.layers.weather
    manager.add(
      new WeatherLayer(context, STORM_CELLS, {
        altitude: weather.altitude,
        opacity: weather.opacity,
        speed: weather.speed,
        color: weather.color as [number, number, number]
      }),
      { visible: weather.enabled, opacity: weather.opacity }
    )

    const currents = CONFIG.layers.currents
    manager.add(
      new CurrentLayer(context, CURRENT_PATHS, {
        altitude: currents.altitude,
        opacity: currents.opacity,
        color: currents.color as [number, number, number],
        speed: currents.speed,
        dash: currents.dash,
        size: currents.size
      }),
      { visible: currents.enabled, opacity: currents.opacity }
    )

    layers = manager
    if (QUERY.get('quality') === 'low') applyQuality(2)
    options.onLayers?.(manager.list())

    // 外置数据源：读取 public/data/earthquakes.json，成功后热替换内置示例数据
    const dataUrl = CONFIG.layers.quakes.dataUrl
    if (dataUrl) {
      loadQuakeFeed(asset(dataUrl))
        .then((feed) => {
          if (disposed || layers !== manager) return
          const quakeLayer = manager.get('quakes') as QuakeLayer | undefined
          if (!quakeLayer) return
          quakeLayer.setMeta({ source: feed.source, updated: feed.updated })
          quakeLayer.setData(feed.events)
          pickDirty = true
          options.onLayers?.(manager.list())
        })
        .catch(() => undefined)
    }
  }

  const gltfLoader = new GLTFLoader()
  const modelBase = asset(CONFIG.assets.model).replace(/[^/]+$/, '')

  const handleGltf = async (gltf: { scene: THREE.Group }) => {
      if (disposed) return
      const mesh = gltf.scene.getObjectByName('Planet_Core') as THREE.Mesh | null
      if (!mesh) {
        options.onError?.()
        return
      }
      // 模型自带的是占位贴图，贴图到位前先不显示
      mesh.visible = false
      try {
        const [dayMap, nightMap] = await Promise.all([
          loadTexture(CONFIG.assets.dayMap),
          CONFIG.material.nightLights ? loadTexture(CONFIG.assets.nightMap).catch(() => null) : Promise.resolve(null)
        ])
        if (disposed) return
        preparePlanet(mesh, dayMap, nightMap)
      } catch {
        if (!disposed) options.onError?.()
        return
      }

      // 首屏用 2K 贴图，空闲后再换成 4K，避免拖慢首屏。
      // 但手机上屏幕像素远小于 4K：多下约 480KB、多占 33MB 显存（含 mipmap 约 44MB），画质收益接近零。
      const screenPixels = window.innerWidth * (window.devicePixelRatio || 1)
      const wantsHighRes = !coarsePointer && screenPixels >= 1600 && renderer.capabilities.maxTextureSize >= 4096
      if (wantsHighRes) {
        highQualityTimer = window.setTimeout(() => {
          loadTexture(CONFIG.assets.dayMapHigh)
            .then((high) => {
              if (disposed || !planetMesh) return
              if (surfaceUniforms) {
                surfaceUniforms.detailMap.value = high
                surfaceUniforms.detailMix.value = 0
                pendingDetail = high
                detailFadeStart = performance.now()
                return
              }
              // 兜底：着色器还没编译过，直接换
              const material = planetMesh.material as THREE.MeshStandardMaterial
              const previous = material.map
              material.map = high
              material.needsUpdate = true
              previous?.dispose()
            })
            .catch(() => undefined)
        }, 1200)
      }
  }

  // 调用方已经开始了模型下载（和动态 import 并行），这里直接解析；
  // 否则退回按 URL 加载，行为和以前一致。
  if (options.modelBuffer) {
    options.modelBuffer
      .then((buffer) => {
        if (disposed) return
        gltfLoader.parse(buffer, modelBase, handleGltf, () => {
          if (!disposed) options.onError?.()
        })
      })
      .catch(() => {
        if (!disposed) options.onError?.()
      })
  } else {
    gltfLoader.load(asset(CONFIG.assets.model), handleGltf, undefined, () => {
      if (!disposed) options.onError?.()
    })
  }

  fetch(asset(CONFIG.assets.background))
    .then((response) => response.blob())
    .then((blob) => createImageBitmap(blob, { imageOrientation: 'flipY' }))
    .then((bitmap) => {
      if (disposed) {
        bitmap.close()
        return
      }
      background = new THREE.Texture(bitmap)
      background.flipY = false
      background.colorSpace = THREE.SRGBColorSpace
      background.needsUpdate = true
      scene.background = background
    })
    .catch(() => {})

  function applyZoom() {
    camera.position.copy(CAMERA_TARGET).addScaledVector(VIEW_DIRECTION, (BASE_DISTANCE * introBoost) / zoom)
    camera.lookAt(CAMERA_TARGET)
  }

  function resize() {
    const width = Math.max(host.clientWidth, 1)
    const height = Math.max(host.clientHeight, 1)
    camera.aspect = width / height
    camera.fov = cinematicFov(CONFIG.camera.fov, CONFIG.camera.referenceAspect, camera.aspect)
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
    applyZoom()
    rectDirty = true
  }

  const resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host)
  resize()
  // 首页的地球在页面中部，滚动会改变它的视口位置
  window.addEventListener('scroll', markRectDirty, { passive: true })

  let lastFrameAt = performance.now()
  let spinAngle = 0
  let dragging = false
  let touchCandidate: { id: number; x: number; y: number } | null = null
  let lastX = 0
  let lastY = 0
  let dragYaw = 0
  let dragPitch = 0
  let velocityYaw = 0
  let velocityPitch = 0
  let lastMoveAt = 0

  const spinQ = new THREE.Quaternion()
  const dragQ = new THREE.Quaternion()
  const dragEuler = new THREE.Euler()
  const worldUp = new THREE.Vector3(0, 1, 0)

  function setZoom(next: number) {
    const clamped = THREE.MathUtils.clamp(next, CONFIG.zoom.min, CONFIG.zoom.max)
    if (clamped === zoomTarget) return
    zoomTarget = clamped
    options.onZoom?.(zoomTarget)
  }

  function beginDrag(x: number, y: number) {
    focus = null
    touring = false
    dragging = true
    lastX = x
    lastY = y
    lastMoveAt = performance.now()
    lastInteractionAt = lastMoveAt
    velocityYaw = 0
    velocityPitch = 0
  }

  function clearHover() {
    if (!hovered) return
    layers?.get(hovered.layerId)?.setHighlight?.(null)
    hovered = null
    options.onHover?.(null)
  }

  function pickAt(x: number, y: number) {
    if (!options.picking || !layers) return
    pickCount += 1
    if (rectDirty) {
      const box = canvas.getBoundingClientRect()
      canvasRect = { left: box.left, top: box.top, width: box.width, height: box.height }
      rectDirty = false
    }
    const rect = canvasRect
    if (rect.width < 1 || rect.height < 1) return

    planetCenterWorld.copy(PLANET_POSITION)
    composer.localToWorld(planetCenterWorld)
    cameraDirection.copy(camera.position).sub(planetCenterWorld).normalize()

    let best: {
      layerId: string
      id: string
      label: string
      detail?: string
      x: number
      y: number
      distance: number
      position: THREE.Vector3
    } | null = null

    for (const info of layers.list()) {
      if (!info.visible) continue
      const layer = layers.get(info.id)
      const pickables = layer?.getPickables?.()
      if (!layer || !pickables?.length) continue

      for (const item of pickables) {
        projected.copy(item.position)
        layer.object.localToWorld(projected)
        // 背面（球体另一侧）的点不参与拾取
        const facing = projected.clone().sub(planetCenterWorld).normalize().dot(cameraDirection)
        if (facing < 0.05) continue

        projected.project(camera)
        if (projected.z > 1) continue
        const sx = rect.left + (projected.x * 0.5 + 0.5) * rect.width
        const sy = rect.top + (-projected.y * 0.5 + 0.5) * rect.height
        const distance = Math.hypot(sx - x, sy - y)
        if (distance > PICK_RADIUS) continue
        if (!best || distance < best.distance) {
          best = { layerId: info.id, id: item.id, label: item.label, detail: item.detail, x: sx, y: sy, distance, position: item.position }
        }
      }
    }

    if (!best) {
      canvas.style.cursor = ''
      clearHover()
      return
    }

    canvas.style.cursor = 'pointer'
    hoveredPosition.copy(best.position)
    if (hovered?.layerId === best.layerId && hovered.id === best.id) return

    if (hovered) layers.get(hovered.layerId)?.setHighlight?.(null)
    layers.get(best.layerId)?.setHighlight?.(best.id)
    hovered = { layerId: best.layerId, id: best.id }
    options.onHover?.({
      layerId: best.layerId,
      id: best.id,
      label: best.label,
      detail: best.detail,
      x: best.x,
      y: best.y
    })
  }

  /**
   * 让某个地表点转到正对镜头。
   * 旋转顺序是 Ry(spin + yaw) * Rx(pitch)，所以可以先解 pitch、再解 yaw，
   * 然后把 yaw 折回 dragYaw（减去自转角），整个求解不会让画面跳变。
   */
  function focusOn(position: THREE.Vector3) {
    if (!options.picking) return
    const u = position.clone().normalize().applyQuaternion(surfaceGroup.quaternion)
    planetCenterWorld.copy(PLANET_POSITION)
    composer.localToWorld(planetCenterWorld)
    const view = camera.position.clone().sub(planetCenterWorld).normalize()

    const normalize = (angle: number) => Math.atan2(Math.sin(angle), Math.cos(angle))
    const reach = Math.hypot(u.y, u.z)
    const ratio = reach > 1e-4 ? THREE.MathUtils.clamp(view.y / reach, -1, 1) : 1
    const phi = Math.atan2(u.z, u.y)
    const alpha = Math.acos(ratio)

    // 两组解取离当前 pitch 更近的那组，转身更短
    const pitchA = normalize(alpha - phi)
    const pitchB = normalize(-alpha - phi)
    const pitch = Math.abs(pitchA - dragPitch) <= Math.abs(pitchB - dragPitch) ? pitchA : pitchB

    const cosP = Math.cos(pitch)
    const sinP = Math.sin(pitch)
    const rotatedZ = u.z * cosP + u.y * sinP
    const thetaPoint = Math.atan2(u.x, rotatedZ)
    const thetaView = Math.atan2(view.x, view.z)
    const desiredYaw = thetaView - thetaPoint - spinAngle

    velocityYaw = 0
    velocityPitch = 0
    lastInteractionAt = performance.now()
    focus = {
      yaw: dragYaw + normalize(desiredYaw - dragYaw),
      pitch: THREE.MathUtils.clamp(pitch, -CONFIG.drag.pitchLimit, CONFIG.drag.pitchLimit)
    }
  }

  function onPointerDown(event: PointerEvent) {
    pointerDownAt.x = event.clientX
    pointerDownAt.y = event.clientY
    pointerDownAt.time = performance.now()
    if (event.pointerType === 'mouse') {
      if (event.button !== 0) return
      beginDrag(event.clientX, event.clientY)
      canvas.setPointerCapture(event.pointerId)
      return
    }
    touchCandidate = { id: event.pointerId, x: event.clientX, y: event.clientY }
  }

  function onPointerMove(event: PointerEvent) {
    pointer = { x: event.clientX, y: event.clientY }
    pickDirty = true
    if (!dragging && event.pointerType === 'mouse') {
      pickAt(event.clientX, event.clientY)
      // 立刻拾取过了，让帧循环按节流节奏再补，避免一次移动算两遍
      lastPickAt = performance.now()
    }

    if (!dragging && touchCandidate && touchCandidate.id === event.pointerId) {
      const dx = event.clientX - touchCandidate.x
      const dy = event.clientY - touchCandidate.y
      if (Math.abs(dx) > CONFIG.drag.touchThreshold && Math.abs(dx) > Math.abs(dy)) {
        const startX = touchCandidate.x
        const startY = touchCandidate.y
        touchCandidate = null
        beginDrag(startX, startY)
        canvas.setPointerCapture(event.pointerId)
      }
    }
    if (!dragging) return
    const now = performance.now()
    const moveDt = Math.max((now - lastMoveAt) / 1000, 1 / 240)
    lastMoveAt = now
    lastInteractionAt = now
    const yawDelta = (event.clientX - lastX) * CONFIG.drag.yawPerPixel
    // 向下拖动 => 画面跟着往下走（之前是反的）
    const pitchDelta = (lastY - event.clientY) * CONFIG.drag.pitchPerPixel
    dragYaw += yawDelta
    dragPitch = THREE.MathUtils.clamp(dragPitch + pitchDelta, -CONFIG.drag.pitchLimit, CONFIG.drag.pitchLimit)
    velocityYaw = THREE.MathUtils.lerp(velocityYaw, yawDelta / moveDt, 0.55)
    velocityPitch = THREE.MathUtils.lerp(velocityPitch, pitchDelta / moveDt, 0.55)
    lastX = event.clientX
    lastY = event.clientY
  }

  function onPointerUp(event: PointerEvent) {
    if (touchCandidate && touchCandidate.id === event.pointerId) touchCandidate = null
    if (dragging) {
      dragging = false
      lastInteractionAt = performance.now()
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId)

      // 位移很小才当作「点击」，拖拽结束时不要触发聚焦
      const moved = Math.hypot(event.clientX - pointerDownAt.x, event.clientY - pointerDownAt.y)
      if (moved < 6 && hovered && performance.now() - pointerDownAt.time < 600) {
        focusOn(hoveredPosition)
      }
    }
  }

  function onWheel(event: WheelEvent) {
    if (CONFIG.zoom.wheelRequiresModifier && !event.ctrlKey && !event.metaKey) return
    event.preventDefault()
    lastInteractionAt = performance.now()
    setZoom(zoomTarget * (1 - event.deltaY * CONFIG.zoom.wheel))
  }

  function resetView() {
    focus = null
    setZoom(1)
    dragYaw = 0
    dragPitch = 0
    spinAngle = 0
    velocityYaw = 0
    velocityPitch = 0
    lastInteractionAt = performance.now()
  }

  const onDoubleClick = () => resetView()

  canvas.addEventListener('pointerdown', onPointerDown)
  canvas.addEventListener('pointermove', onPointerMove)
  canvas.addEventListener('pointerup', onPointerUp)
  canvas.addEventListener('pointerleave', () => {
    pointer = null
    canvas.style.cursor = ''
    clearHover()
  })
  canvas.addEventListener('pointercancel', onPointerUp)
  canvas.addEventListener('wheel', onWheel, { passive: false })
  canvas.addEventListener('dblclick', onDoubleClick)

  function renderFrame() {
    const now = performance.now()
    const dt = Math.min((now - lastFrameAt) / 1000, 0.1)
    lastFrameAt = now

    // 2K -> 4K 交叉淡入
    if (pendingDetail && surfaceUniforms) {
      const t = Math.min(1, (now - detailFadeStart) / 450)
      surfaceUniforms.detailMix.value = 1 - Math.pow(1 - t, 2)
      if (t >= 1) {
        const material = planetMesh?.material as THREE.MeshStandardMaterial | undefined
        if (material) {
          const previous = material.map
          material.map = pendingDetail
          material.needsUpdate = true
          previous?.dispose()
        }
        surfaceUniforms.detailMix.value = 0
        surfaceUniforms.detailMap.value = null
        pendingDetail = null
      }
    }

    // 入场：镜头从 8% 远处缓入，1.4 秒归位
    if (introStart > 0 && introBoost !== 1) {
      const t = Math.min(1, (now - introStart) / 1400)
      introBoost = 1 + 0.08 * Math.pow(1 - t, 3)
      if (t >= 1) introBoost = 1
      applyZoom()
    }

    if (zoom !== zoomTarget) {
      zoom += (zoomTarget - zoom) * (1 - Math.exp(-CONFIG.zoom.ease * dt))
      if (Math.abs(zoomTarget - zoom) < 0.001) zoom = zoomTarget
      applyZoom()
    }

    if (!dragging && focus) {
      // 聚焦动画：指数缓动到目标角度，同时冻结自转，避免目标点在途中漂走
      const ease = 1 - Math.exp(-dt * CONFIG.focus.ease)
      dragYaw += (focus.yaw - dragYaw) * ease
      dragPitch += (focus.pitch - dragPitch) * ease
      if (Math.abs(focus.yaw - dragYaw) < 0.003 && Math.abs(focus.pitch - dragPitch) < 0.003) {
        dragYaw = focus.yaw
        dragPitch = focus.pitch
        focus = null
        lastInteractionAt = now
        focusHoldUntil = now + CONFIG.focus.hold * 1000
      }
    } else if (!dragging) {
      const idle = now - lastInteractionAt > CONFIG.spin.resumeDelay * 1000 && now > focusHoldUntil
      const spinSpeed = CONFIG.spin.speed * (touring ? CONFIG.spin.tourBoost : 1)
      if (SPIN_ENABLED && (idle || touring)) spinAngle += dt * spinSpeed
      if (velocityYaw !== 0 || velocityPitch !== 0) {
        const decay = Math.exp(-CONFIG.drag.inertia * dt)
        dragYaw += velocityYaw * dt
        dragPitch = THREE.MathUtils.clamp(dragPitch + velocityPitch * dt, -CONFIG.drag.pitchLimit, CONFIG.drag.pitchLimit)
        velocityYaw *= decay
        velocityPitch *= decay
        if (Math.abs(velocityYaw) < 1e-4) velocityYaw = 0
        if (Math.abs(velocityPitch) < 1e-4) velocityPitch = 0
      }
    } else if (now - lastMoveAt > 120) {
      const decay = Math.exp(-16 * dt)
      velocityYaw *= decay
      velocityPitch *= decay
    }
    spinQ.setFromAxisAngle(worldUp, spinAngle)
    dragEuler.set(dragPitch, dragYaw, 0, 'YXZ')
    dragQ.setFromEuler(dragEuler)
    planetPivot.quaternion.copy(spinQ).multiply(dragQ)
    elapsed += dt
    frameCount += 1
    layers?.update(dt, elapsed)

    if (options.picking && pointer && !dragging) {
      const now = performance.now()
      // 球体静止、指针也没动时，重复拾取没有意义
      const signature = spinAngle + dragYaw + dragPitch + zoom
      if (now - lastPickAt > PICK_INTERVAL && (pickDirty || signature !== lastPickSignature)) {
        lastPickAt = now
        lastPickSignature = signature
        pickDirty = false
        pickAt(pointer.x, pointer.y)
      }
    } else if (!pointer && hovered) {
      clearHover()
    }
    renderer.render(scene, camera)
    trackFrame(dt)
    if (!ready && planetMesh) {
      ready = true
      options.onReady?.()
    }
  }

  /**
   * 性能不足时先降分辨率，分辨率到底了就逐级关掉最耗的图层。
   * 只还原"是画质系统自己关掉的"图层，不覆盖用户手动开关。
   */
  function applyQuality(level: number) {
    const next = Math.max(0, Math.min(2, level))
    if (next === qualityLevel) return
    qualityLevel = next
    if (!layers) return

    // 只关"当前是开着"的图层，否则还原时会把用户本来就没开的图层打开
    const hideIfVisible = (id: string) => {
      if (disabledByQuality.has(id)) return
      const info = layers?.list().find((item) => item.id === id)
      if (!info?.visible) return
      layers?.setVisible(id, false)
      disabledByQuality.add(id)
    }
    if (next >= 1) hideIfVisible('clouds')
    if (next >= 2) hideIfVisible('weather')
    for (const id of [...disabledByQuality]) {
      const shouldBeOn = id === 'clouds' ? next < 1 : next < 2
      if (shouldBeOn) {
        layers.setVisible(id, true)
        disabledByQuality.delete(id)
      }
    }

    // 大气壳：1 级只留最内层贴边的那一圈，外面的大范围柔光壳整层砍掉（每个壳都是一次全屏 overdraw）
    const keepShells = next >= 1 ? Math.min(atmosphereShells.length, 1) : atmosphereShells.length
    atmosphereShells.forEach((shell, index) => {
      shell.visible = index < keepShells
    })
    options.onLayers?.(layers.list())
  }

  function applyPixelRatio() {
    renderer.setPixelRatio(pixelRatio)
    resize()
  }

  function trackFrame(dt: number) {
    const ms = Math.min(dt * 1000, 80)
    if (perf.warmup > 0) {
      perf.warmup -= 1
      if (ms >= 4 && ms <= 40) {
        perf.samples.push(ms)
        if (perf.samples.length >= 60) {
          perf.samples.sort((a, b) => a - b)
          const reference = perf.samples[Math.floor(perf.samples.length * 0.25)]
          perf.refreshHz = Math.max(30, Math.min(144, Math.round(1000 / reference / 15) * 15))
          perf.samples.length = 0
        }
      }
      return
    }
    perf.frames += 1
    perf.totalMs += ms
    if (perf.frames < 45) return
    const average = perf.totalMs / perf.frames
    perf.frames = 0
    perf.totalMs = 0
    const budget = (1000 / perf.refreshHz) * 1.14
    const now = performance.now()
    if (now >= perf.cooldownUntil) {
      if (average > budget * 1.2 && pixelRatio > minPixelRatio) {
        pixelRatio = Math.max(minPixelRatio, pixelRatio - 0.15)
        applyPixelRatio()
        perf.cooldownUntil = now + 1600
      } else if (average < budget * 0.85 && pixelRatio < maxPixelRatio) {
        pixelRatio = Math.min(maxPixelRatio, pixelRatio + 0.1)
        applyPixelRatio()
        perf.cooldownUntil = now + 3200
      } else if (
        average > budget * 1.6 &&
        pixelRatio <= minPixelRatio + 0.001 &&
        qualityLevel < 2
      ) {
        // 分辨率已经到底还卡，就关图层（云层最耗填充率）
        applyQuality(qualityLevel + 1)
        perf.cooldownUntil = now + 4200
      }
    }
    if (perf.hud) {
      const calls = renderer.info.render.calls
      const tris = Math.round(renderer.info.render.triangles / 1000)
      perf.hud.textContent =
        `${Math.round(1000 / average)} fps · ${average.toFixed(1)}ms · dpr ${pixelRatio.toFixed(2)}` +
        ` · q${qualityLevel} · ${calls} draws · ${tris}k tris · target ${perf.refreshHz}Hz`
    }
  }

  function loop() {
    if (disposed || paused) {
      running = false
      return
    }
    renderFrame()
    frameId = requestAnimationFrame(loop)
  }

  function start() {
    if (disposed || paused || running) return
    running = true
    lastFrameAt = performance.now()
    frameId = requestAnimationFrame(loop)
  }

  loop()
  // 让 UI 一开始就显示真实缩放（分享链接里可能带了 zoom）
  options.onZoom?.(zoomTarget)

  const handle: PlanetSceneHandle = {
    setOffset(x: number, y: number, scale = 1) {
      composer.position.set(x, y, 0)
      composer.scale.setScalar(scale)
    },
    setPaused(next: boolean) {
      if (paused === next) return
      paused = next
      if (paused) {
        cancelAnimationFrame(frameId)
        running = false
      } else {
        start()
      }
    },
    zoomIn() {
      setZoom(zoomTarget + CONFIG.zoom.step)
    },
    zoomOut() {
      setZoom(zoomTarget - CONFIG.zoom.step)
    },
    resetView,
    getZoom() {
      return zoomTarget
    },
    getLayers() {
      return layers?.list() ?? []
    },
    getLayer(id) {
      return layers?.get(id)
    },
    setLayerTime(id, value) {
      layers?.get(id)?.setTime?.(value)
    },
    getLayerTimeRange(id) {
      return layers?.get(id)?.getTimeRange?.() ?? null
    },
    setTour(enabled) {
      touring = enabled
      lastInteractionAt = performance.now()
    },
    rotateBy(yaw, pitch) {
      focus = null
      lastInteractionAt = performance.now()
      dragYaw += yaw
      dragPitch = THREE.MathUtils.clamp(dragPitch + pitch, -CONFIG.drag.pitchLimit, CONFIG.drag.pitchLimit)
    },
    getQuality() {
      return qualityLevel
    },
    setQuality(level) {
      applyQuality(level)
    },
    getLayerHistogram(id) {
      return layers?.get(id)?.getHistogram?.() ?? []
    },
    getStats() {
      return {
        frames: frameCount,
        picks: pickCount,
        quality: qualityLevel,
        pixelRatio,
        maxRatio: maxPixelRatio,
        calls: renderer.info.render.calls,
        triangles: renderer.info.render.triangles
      }
    },
    getViewCenter() {
      if (!planetMesh) return null
      const center = composer.localToWorld(PLANET_POSITION.clone())
      const direction = camera.position.clone().sub(center).normalize()

      const pivotQuat = new THREE.Quaternion()
      planetPivot.getWorldQuaternion(pivotQuat)
      direction.applyQuaternion(pivotQuat.invert())
      direction.applyQuaternion(surfaceGroup.quaternion.clone().invert())

      // 用最近顶点反查 UV，再换算经纬度（和 latLonToVector 是同一套约定）
      const position = planetMesh.geometry.getAttribute('position')
      const uv = planetMesh.geometry.getAttribute('uv')
      let best = 0
      let bestDot = -2
      for (let i = 0; i < position.count; i += 1) {
        const dot = direction.x * position.getX(i) + direction.y * position.getY(i) + direction.z * position.getZ(i)
        if (dot > bestDot) {
          bestDot = dot
          best = i
        }
      }
      return {
        longitude: Math.round((uv.getX(best) * 360 - 180) * 10) / 10,
        latitude: Math.round((90 - uv.getY(best) * 180) * 10) / 10
      }
    },
    capture() {
      if (disposed) return null
      // 同一帧内先渲染再取图，preserveDrawingBuffer 关着也能拿到内容
      renderer.render(scene, camera)
      return canvas.toDataURL('image/png')
    },
    setLayerVisible(id, visible) {
      layers?.setVisible(id, visible)
      pickDirty = true
      options.onLayers?.(layers?.list() ?? [])
    },
    setLayerOpacity(id, opacity) {
      layers?.setOpacity(id, opacity)
      options.onLayers?.(layers?.list() ?? [])
    },
    dispose() {
      if (disposed) return
      disposed = true
      cancelAnimationFrame(frameId)
      layers?.dispose()
      layers = null
      pendingDetail?.dispose()
      pendingDetail = null
      window.clearTimeout(highQualityTimer)
      resizeObserver.disconnect()
      window.removeEventListener('scroll', markRectDirty)
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('pointerup', onPointerUp)
      canvas.removeEventListener('pointercancel', onPointerUp)
      canvas.removeEventListener('wheel', onWheel)
      canvas.removeEventListener('dblclick', onDoubleClick)
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry?.dispose()
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          materials.forEach((material) => {
            for (const value of Object.values(material as Record<string, unknown>)) {
              if (value instanceof THREE.Texture) (value as THREE.Texture).dispose()
            }
            material.dispose()
          })
        }
      })
      geometryCache.forEach((geometry) => geometry.dispose())
      materialCache.forEach((material) => material.dispose())
      textures.forEach((texture) => texture.dispose())
      textures.clear()
      background?.dispose()
      perf.hud?.remove()
      renderer.dispose()
      renderer.forceContextLoss()
      canvas.remove()
    }
  }

  // ?debug 时把句柄挂到 window，方便在控制台调图层、换数据
  if (QUERY.has('debug')) {
    ;(window as unknown as Record<string, unknown>).__planet = handle
  }

  return handle
}
