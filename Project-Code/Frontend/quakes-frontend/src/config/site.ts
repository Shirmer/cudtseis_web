export type Locale = 'zh' | 'en'

export const SITE = {
  brandZh: '深视地球',
  brandEn: 'DEEPSEEK EARTH',
  companyZh: '深视地球（成都）信息技术有限公司',
  companyEn: 'DeepSeek Earth (Chengdu) Information Technology Co., Ltd.',
  productName: 'GeoCamera',
  productNameZh: 'GeoCamera 地质相机',
  websiteUrl: 'https://deepseek-earth.cdutseis.com',
  productUrl: 'https://geocamera.deepseek-earth.cdutseis.com',
  icp: '蜀ICP备2026068507号-1',
  appIcp: '蜀ICP备2026068507号-2A',
  icpUrl: 'https://beian.miit.gov.cn/',
  // 联系方式占位：发布前替换为正式联系方式
  contact: {
    email: 'contact@geocamera.com',
    businessEmail: 'contact@geocamera.com',
    addressZh: '四川省成都市成华区二仙桥东三路 1 号',
    addressEn: 'No. 1, East Third Road, Erxianqiao, Chenghua District, Chengdu, Sichuan, China'
  },
  releaseApi: '/api/release/latest'
} as const

export function localeFromPath(path: string): Locale {
  return path.startsWith('/en') ? 'en' : 'zh'
}

export function localizedPath(locale: Locale, path: string): string {
  const bare = path.startsWith('/en') ? path.slice(3) || '/' : path
  if (locale === 'zh') return bare
  return bare === '/' ? '/en' : `/en${bare}`
}

// 正式站点按域名分工；本地开发可用 ?site=geocamera 预览产品站。
export const isProductSite = window.location.hostname === 'geocamera.deepseek-earth.cdutseis.com'
  || (import.meta.env.DEV && new URLSearchParams(window.location.search).get('site') === 'geocamera')

export function productUrl(locale: Locale, path = '/'): string {
  return SITE.productUrl + localizedPath(locale, path)
}
