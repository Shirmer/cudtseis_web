import type { QuakeEvent } from './quake-layer'

/**
 * 演示用地震数据（20 次 21 世纪以来的显著地震）。
 * 接真实数据时替换这个数组即可，渲染层不用改。
 */
export const QUAKE_EVENTS: QuakeEvent[] = [
  { lat: 31.0, lon: 103.4, magnitude: 7.9, place: '中国 四川 汶川', time: '2008-05-12' },
  { lat: 38.3, lon: 142.4, magnitude: 9.1, place: '日本 东北近海', time: '2011-03-11' },
  { lat: 3.3, lon: 95.9, magnitude: 9.1, place: '印尼 苏门答腊', time: '2004-12-26' },
  { lat: -35.8, lon: -72.7, magnitude: 8.8, place: '智利 马乌莱', time: '2010-02-27' },
  { lat: 38.3, lon: 142.4, magnitude: 7.9, place: '日本 东北近海', time: '2011-03-11' },
  { lat: 28.2, lon: 84.7, magnitude: 7.8, place: '尼泊尔 博克拉', time: '2015-04-25' },
  { lat: 37.2, lon: 37.0, magnitude: 7.8, place: '土耳其 卡赫拉曼马拉什', time: '2023-02-06' },
  { lat: 37.5, lon: 137.3, magnitude: 7.5, place: '日本 能登半岛', time: '2024-01-01' },
  { lat: -2.2, lon: 100.0, magnitude: 7.6, place: '印尼 巴东', time: '2009-09-30' },
  { lat: 19.6, lon: -155.5, magnitude: 6.9, place: '美国 夏威夷', time: '2018-05-04' },
  { lat: 34.0, lon: 105.0, magnitude: 6.6, place: '中国 甘肃 陇南', time: '2008-05-12' },
  { lat: -43.6, lon: 172.7, magnitude: 6.3, place: '新西兰 基督城', time: '2011-02-22' },
  { lat: 44.8, lon: 149.0, magnitude: 8.3, place: '俄罗斯 千岛群岛', time: '2006-11-15' },
  { lat: -31.6, lon: -71.7, magnitude: 8.8, place: '智利 伊亚佩尔', time: '2015-09-16' },
  { lat: 27.3, lon: 103.0, magnitude: 6.5, place: '中国 云南 鲁甸', time: '2014-08-03' },
  { lat: 61.3, lon: -149.9, magnitude: 7.1, place: '美国 阿拉斯加', time: '2018-11-30' },
  { lat: 24.1, lon: 121.6, magnitude: 7.4, place: '中国 台湾 花莲', time: '2024-04-03' },
  { lat: -17.9, lon: -70.7, magnitude: 8.1, place: '秘鲁 阿雷基帕', time: '2001-06-23' },
  { lat: 42.9, lon: 145.1, magnitude: 7.4, place: '日本 北海道', time: '2003-09-25' },
  { lat: 3.3, lon: 95.9, magnitude: 8.6, place: '印尼 苏门答腊', time: '2012-04-11' }
]
