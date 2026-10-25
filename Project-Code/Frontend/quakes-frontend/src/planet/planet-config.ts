/**
 * 首页地球模型的全部可调参数。
 *
 * 日常调整只改这个文件，不需要动 planet-scene.ts：
 * - 换地球贴图 / 换模型：改 assets
 * - 打开页面时正对哪块大陆：改 initial
 * - 自转快慢、拖拽灵敏度、缩放范围：改 spin / drag / zoom
 * - 大气光晕颜色与强度：改 atmosphere
 *
 * 贴图路径写相对 public/ 的路径即可（不需要前导斜杠）。
 */
export const PLANET_CONFIG = {
  /** 模型与贴图。dayMap 是首屏贴图，dayMapHigh 在空闲时替换成高清版。 */
  assets: {
    model: 'media/planet/planet.glb',
    dayMap: 'media/planet/earth-day-2k.webp',
    dayMapHigh: 'media/planet/earth-day-4k.webp',
    nightMap: 'media/planet/earth-night-2k.webp',
    background: 'media/planet/space-subtle.webp',
    poster: 'media/planet/planet-poster.webp',
    /** 全屏页 /earth 的兜底海报（地球居中） */
    posterFull: 'media/planet/planet-poster-full.webp'
  },

  /** 首屏朝向：正对镜头的经纬度（默认成都）。longitude 东经为正，latitude 北纬为正。 */
  initial: {
    longitude: 103.9,
    latitude: 30.6
  },

  /** 自转与拖拽手感 */
  spin: {
    enabled: true,
    /** 弧度/秒，0.05 ≈ 两分钟转一圈 */
    speed: 0.045,
    /** 松手后多少秒恢复自转 */
    resumeDelay: 1.6,
    /** 巡游模式的自转倍数 */
    tourBoost: 3.2
  },

  /** 点击点位聚焦 */
  focus: {
    /** 缓动速度，越大转得越快 */
    ease: 5.5,
    /** 聚焦完成后暂停自转多少秒 */
    hold: 3
  },

  drag: {
    /** 每像素转多少弧度 */
    yawPerPixel: 0.005,
    pitchPerPixel: 0.003,
    /** 上下翻转的最大角度（弧度），避免翻到南极以外 */
    pitchLimit: 1.2,
    /** 惯性衰减，越大停得越快 */
    inertia: 3.6,
    /** 触摸时水平位移超过这个像素才判定为拖拽（否则让页面滚动） */
    touchThreshold: 10
  },

  /** 缩放（1 = 初始大小） */
  zoom: {
    min: 1,
    max: 2.4,
    /** 点一次 +/- 变化多少 */
    step: 0.25,
    /** 滚轮灵敏度 */
    wheel: 0.0016,
    /** 是否必须按住 Ctrl / ⌘ 才响应滚轮（false 时鼠标滚轮直接缩放） */
    wheelRequiresModifier: true,
    /** 缓动速度，越大跟手越硬 */
    ease: 8
  },

  material: {
    roughness: 0.92,
    /** 夜面城市灯光的强弱 */
    nightIntensity: 1.0,
    /** 晨昏线暖光强度（0 = 关闭） */
    twilightIntensity: 0.05,
    /** 星球边缘的大气内辉光（白天一侧），0 = 关闭 */
    hazeIntensity: 0.32,
    /** 是否合成夜景灯光（关闭后夜面接近纯黑） */
    nightLights: true,
    /** 海面高光：海洋的粗糙度（越小反光越锐利） */
    oceanRoughness: 0.42,
    /** 判定海洋的「蓝色占比」阈值 */
    oceanThreshold: 0.5,
    /** 阈值过渡宽度 */
    oceanSoftness: 0.08,
    /** 海面高光强度（0-1，越小越含蓄） */
    oceanSpecular: 0.18
  },

  camera: {
    position: [0.03301453835, 0.69856543589, 33.25363458814],
    target: [-0.1, 0.1, 0],
    fov: 31.41727565803149,
    near: 0.1,
    far: 150,
    /** 取景参考宽高比，竖屏时会自动放宽视野 */
    referenceAspect: 4 / 3
  },

  /**
   * 星球在画面里的位置与大小：按容器宽高比三档切换。
   * hero = 首页首屏（偏右，给文案让位）；full = /earth 全屏页（居中）。
   * x 右为正、y 上为正，scale 是整体缩放。
   */
  layout: {
    hero: {
      wide: { x: 7.2, y: 0.2, scale: 1 },
      medium: { x: 4.8, y: 1.6, scale: 0.86 },
      narrow: { x: 11.8, y: 13.5, scale: 0.8 },
      /** 竖屏平板：右上角露出完整球体，别像手机那样只留一角 */
      tablet: { x: 5.2, y: 6.4, scale: 0.95 }
    },
    full: {
      wide: { x: 0, y: 0, scale: 1.3 },
      medium: { x: 0, y: 0, scale: 1.5 },
      /** 竖屏手机：球体几乎顶满宽度 */
      narrow: { x: 0, y: 0, scale: 2 },
      /** 竖屏平板：宽度足够，别放太大 */
      tablet: { x: 0, y: 0, scale: 1.7 }
    }
  },

  /** 太阳方向（世界坐标），同时驱动主光与大气边缘光 */
  sunDirection: [0.52, 0.48, 0.71],

  /** 大气光晕：两层球壳叠加，power 越大边缘越窄 */
  atmosphere: {
    layers: [
      { radius: 5.064, power: 8, opacity: 0.7, color: [0.16, 0.48, 1.0], emission: 5.0, blending: 'normal' as const },
      { radius: 5.102, power: 12, opacity: 0.25, color: [0.18, 0.22, 1.0], emission: 0.8, blending: 'normal' as const },
      // 大范围柔和辉光，让边缘不是一条硬线
    ]
  },

  /**
   * 图层：每个图层都能单独开关，未来新的可视化（洋流、地质事件、温度场）
   * 也在这里加配置，并在 planet-scene 的 buildLayers() 里注册。
   */
  layers: {
    clouds: {
      /** 默认是否开启 */
      enabled: true,
      texture: 'media/planet/clouds-2k.webp',
      /** 距地表高度倍数 */
      altitude: 1.0015,
      opacity: 0.55,
      /** 相对地球的漂移速度（弧度/秒） */
      drift: 0.012,
      /** 云密度阈值，调大云变少 */
      threshold: 0.1,
      /** 边缘柔和度 */
      softness: 0.4,
      tint: [1, 1, 1]
    },
    quakes: {
      enabled: false,
      /** 外置数据源（相对 public/），留空则只用内置示例数据 */
      dataUrl: 'data/earthquakes.json',
      altitude: 1.002,
      opacity: 1,
      /** 点位基础尺寸（世界单位，会随视角缩放） */
      size: 0.5,
      /** 每级震级增加的尺寸 */
      magnitudeScale: 0.11,
      color: [1, 0.45, 0.22],
      /** 时间轴推进时，大地震位置泛起冲击波纹 */
      ripple: {
        enabled: true,
        minMagnitude: 6.5,
        life: 2.2,
        maxRadius: 1.35,
        color: [1, 0.62, 0.22],
        max: 8
      }
    },
    geo: {
      enabled: false,
      altitude: 1.0025,
      opacity: 0.9,
      /** 断层线颜色；板块边界会自动暗一些 */
      lineColor: [1, 0.45, 0.3],
      /** 火山三角形颜色 */
      siteColor: [1, 0.58, 0.12],
      lineOpacity: 0.55,
      /** 火山点大小（世界单位） */
      siteSize: 0.4
    },
    weather: {
      enabled: false,
      /** 要在云层之上，所以比 clouds.altitude 略高 */
      altitude: 1.004,
      opacity: 0.85,
      /** 螺旋旋转速度 */
      speed: 1,
      color: [0.78, 0.88, 1]
    },
    currents: {
      enabled: false,
      altitude: 1.001,
      opacity: 0.9,
      color: [0.3, 0.85, 1],
      /** 流动速度 */
      speed: 0.12,
      /** 每条路径上的流动段数 */
      dash: 6,
      /** 粒子大小（世界单位） */
      size: 0.16
    }
  },

  /** 星球打光，数量和顺序都可以改 */
  lights: [
    { color: [1, 0.88, 0.78], intensity: 2.4, position: [8, 7, 11] },
    { color: [0.17, 0.35, 1], intensity: 0.12, position: [-8, 4, 7] },
    { color: [1, 0.49, 0.3], intensity: 0.6, position: [6, 7, -4] }
  ],

  ambient: { color: [0.05, 0.065, 0.13], intensity: 0.24 },

  /** 星球本体在世界中的位置与半径，改动会影响大气球壳对齐 */
  planet: {
    position: [-0.55, 0.35, 0],
    radius: 5.05
  }
}
