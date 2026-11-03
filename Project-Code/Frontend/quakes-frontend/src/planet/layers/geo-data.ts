import type { LatLon } from './paths'

export interface GeoLine {
  name: string
  /** 断层带 / 板块边界 / 地质界线 */
  kind: 'fault' | 'boundary' | 'belt'
  points: LatLon[]
}

export interface GeoSite {
  name: string
  lat: number
  lon: number
  kind: 'volcano' | 'site'
}

/**
 * 演示用地质构造数据：主要断裂带、板块边界和活火山。
 * 接真实数据（断层矢量、地质图）时替换这两个数组即可。
 */
export const GEO_LINES: GeoLine[] = [
  {
    name: '圣安德烈斯断层',
    kind: 'fault',
    points: [[40.5, -124.2], [38.8, -122.8], [36.8, -121.4], [34.9, -119.6], [33.2, -116.4], [31.2, -113.8]]
  },
  {
    name: '阿尔卑斯—喜马拉雅带',
    kind: 'belt',
    points: [[37, 14], [38, 24], [37, 34], [35, 44], [33, 54], [31, 64], [29, 74], [27.5, 84], [26.5, 92], [24.5, 98]]
  },
  {
    name: '青藏高原东缘断裂',
    kind: 'fault',
    points: [[36.5, 101], [33.5, 102.5], [30.5, 103], [27.5, 102], [25.5, 100], [23.5, 98]]
  },
  {
    name: '东非大裂谷',
    kind: 'belt',
    points: [[15, 40], [10.5, 38.5], [5.5, 36.5], [0.5, 36], [-4.5, 35], [-9.5, 34], [-14, 33.5]]
  },
  {
    name: '环太平洋西带',
    kind: 'boundary',
    points: [[45, 148], [38, 142], [31, 132], [24, 122], [16, 121], [9, 125], [2, 128], [-5, 130], [-9, 124], [-11, 116]]
  },
  {
    name: '环太平洋东带',
    kind: 'boundary',
    points: [[55, -158], [48, -152], [40, -142], [32, -128], [24, -112], [16, -100], [8, -86], [-2, -81], [-12, -77], [-22, -71], [-32, -72], [-42, -74]]
  },
  {
    name: '大西洋中脊',
    kind: 'boundary',
    points: [[65, -18], [55, -30], [45, -28], [35, -40], [25, -45], [10, -40], [-5, -32], [-20, -25], [-35, -18], [-50, -10]]
  }
]

export const GEO_SITES: GeoSite[] = [
  { name: '富士山', lat: 35.36, lon: 138.73, kind: 'volcano' },
  { name: '长白山天池', lat: 42.0, lon: 128.06, kind: 'volcano' },
  { name: '腾冲火山群', lat: 25.03, lon: 98.5, kind: 'volcano' },
  { name: '五大连池', lat: 48.72, lon: 126.12, kind: 'volcano' },
  { name: '维苏威火山', lat: 40.82, lon: 14.43, kind: 'volcano' },
  { name: '埃特纳火山', lat: 37.75, lon: 14.99, kind: 'volcano' },
  { name: '喀拉喀托', lat: -6.1, lon: 105.4, kind: 'volcano' },
  { name: '黄石火山', lat: 44.43, lon: -110.67, kind: 'volcano' },
  { name: '乞力马扎罗', lat: -3.07, lon: 37.36, kind: 'volcano' },
  { name: '圣海伦斯', lat: 46.19, lon: -122.19, kind: 'volcano' }
]
