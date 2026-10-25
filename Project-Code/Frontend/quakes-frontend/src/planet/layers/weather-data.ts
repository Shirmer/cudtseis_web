import type { StormCell } from './weather-layer'

/**
 * 演示用气旋/风暴数据。
 * 接真实天气数据（比如 GFS 气旋中心）时替换这个数组即可。
 * spin: 1 = 逆时针（北半球），-1 = 顺时针（南半球）
 */
export const STORM_CELLS: StormCell[] = [
  { lat: 18, lon: 132, size: 9, intensity: 1, spin: 1, name: '西北太平洋台风' },
  { lat: 22, lon: -62, size: 8, intensity: 0.9, spin: 1, name: '北大西洋飓风' },
  { lat: 15, lon: -120, size: 6.5, intensity: 0.75, spin: 1, name: '东太平洋热带气旋' },
  { lat: -18, lon: 62, size: 8.5, intensity: 0.85, spin: -1, name: '南印度洋气旋' },
  { lat: -20, lon: -170, size: 7, intensity: 0.7, spin: -1, name: '南太平洋气旋' },
  { lat: 48, lon: -30, size: 11, intensity: 0.55, spin: 1, name: '北大西洋温带气旋' }
]
