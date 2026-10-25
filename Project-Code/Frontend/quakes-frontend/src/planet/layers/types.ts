import type * as THREE from 'three'

/** 图层拿到的运行环境。所有坐标都基于「星球本地空间」：半径 1 的球，北极在 +Y。 */
export interface LayerContext {
  /**
   * 随地球一起转动的父节点（已含朝向和自转）。
   * 贴地表的图层（云、点位、洋流）都挂在这里，天然跟着地球走。
   */
  pivot: THREE.Object3D
  /** 不随地球转动的父节点，用于需要独立漂移或永远朝向镜头的效果。 */
  scene: THREE.Scene
  /** 星球几何体，用于按经纬度取表面坐标 */
  planetGeometry: THREE.BufferGeometry
  /** 星球半径（场景单位） */
  radius: number
  /** 太阳方向（世界坐标，单位向量） */
  sunDirection: THREE.Vector3
  camera: THREE.PerspectiveCamera
  renderer: THREE.WebGLRenderer
  /** 把 public 下的相对路径解析成完整地址 */
  assetUrl: (path: string) => string
  /** 当前时间，給按时间演算的图层用（天气、昼夜、事件） */
  now: () => Date
}

/** 时间轴分布条的一格 */
export interface YearBucket {
  year: number
  count: number
  /** 该年最大震级（或强度），用于决定柱高 */
  peak: number
}

/** 图层的数据来路，用于在图例里标注"数据更新于……" */
export interface LayerMeta {
  source?: string
  updated?: string
}

/** 暴露给 UI 的图层描述 */
export interface LayerInfo {
  id: string
  name: string
  nameEn: string
  visible: boolean
  opacity: number
  /** 数据条数（点位/路径/风暴的数量），用于图例 */
  count?: number
  /** 数据来路（可选） */
  meta?: LayerMeta
}

/** 图层里可以被鼠标问到的一个元素（点位、风暴中心……） */
export interface Pickable {
  id: string
  label: string
  detail?: string
  /** 图层本地坐标 */
  position: THREE.Vector3
}

/** 命中的结果，交给 UI 显示 */
export interface HoverInfo {
  layerId: string
  id: string
  label: string
  detail?: string
  /** 屏幕坐标（viewport），用于定位信息卡 */
  x: number
  y: number
}

/**
 * 一个可独立开关、可动画的图层。
 * 新加可视化（洋流、地质事件、温度场……）都实现这个接口，再在 planet-scene 里注册。
 */
export interface PlanetLayer {
  readonly id: string
  readonly name: string
  readonly nameEn: string
  readonly object: THREE.Object3D
  setVisible(visible: boolean): void
  setOpacity(opacity: number): void
  /** 可选：返回可拾取的元素，供鼠标悬停查询 */
  getPickables?(): Pickable[]
  /** 数据来路（有外置数据源的图层才实现） */
  getMeta?(): LayerMeta | undefined
  /** 按年份的事件分布，给时间轴画分布条 */
  getHistogram?(): YearBucket[]
  /** 可选：高亮某个元素（传 null 取消） */
  setHighlight?(id: string | null): void
  /** 可选：设置时间轴位置（年份），用于回放类图层 */
  setTime?(value: number): void
  /** 可选：时间轴范围 */
  getTimeRange?(): { min: number; max: number }
  /** 可选：数据条数，显示在图例里 */
  getCount?(): number
  /** 每帧调用；dt 秒，elapsed 为场景累计秒数 */
  update(dt: number, elapsed: number): void
  dispose(): void
}
