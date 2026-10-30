export type Locale = 'zh' | 'en'

export const SITE = {
  brandZh: '深视地球',
  brandEn: 'DEEPSEEK EARTH',
  companyZh: '深视地球（成都）信息技术有限公司',
  companyEn: 'DeepSeek Earth (Chengdu) Information Technology Co., Ltd.',
  productName: 'GeoCamera',
  productNameZh: 'GeoCamera 地质相机',
  // ICP 备案号占位：备案完成后替换为正式备案号
  icp: '',
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
