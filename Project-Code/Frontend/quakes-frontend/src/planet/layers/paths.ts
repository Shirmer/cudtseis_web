import * as THREE from 'three'
import { latLonToVector } from './sphere'

export type LatLon = [number, number]

/**
 * 把一串经纬度路标插值成球面上的点列。
 * - 相邻两点按大圆短弧插值（先线性插值再归一化，路标间距小的时候足够）
 * - 跨 180° 经线时自动走短弧，不会绕地球一圈
 */
export function sampleSphericalPath(
  geometry: THREE.BufferGeometry,
  points: LatLon[],
  radius: number,
  maxStep = 0.015
): THREE.Vector3[] {
  const samples: THREE.Vector3[] = []
  for (let i = 0; i < points.length - 1; i += 1) {
    const [lat1, lon1] = points[i]
    let [lat2, lon2] = points[i + 1]
    if (Math.abs(lon2 - lon1) > 180) lon2 += lon2 > lon1 ? -360 : 360

    const from = latLonToVector(geometry, lat1, lon1, 1)
    const to = latLonToVector(geometry, lat2, lon2, 1)
    const steps = Math.max(4, Math.ceil(from.angleTo(to) / maxStep))
    for (let step = i === 0 ? 0 : 1; step <= steps; step += 1) {
      const t = step / steps
      samples.push(from.clone().lerp(to, t).normalize().multiplyScalar(radius))
    }
  }
  return samples
}

/** 点列 -> 供 LineSegments 使用的顶点数组（两两成段） */
export function toLineSegments(samples: THREE.Vector3[], out: number[] = []) {
  for (let i = 1; i < samples.length; i += 1) {
    out.push(samples[i - 1].x, samples[i - 1].y, samples[i - 1].z)
    out.push(samples[i].x, samples[i].y, samples[i].z)
  }
  return out
}
