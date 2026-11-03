import { watchEffect } from 'vue'
import { SITE, type Locale } from '../config/site'

export interface PageMeta {
  /** 浏览器标题 */
  title: string
  /** 页面描述，用于搜索引擎摘要与分享卡片 */
  description?: string
  /** 分享卡片标题，缺省用 title */
  shareTitle?: string
  /** 分享卡片图片（相对路径或绝对地址），缺省用站点封面 */
  image?: string
  /** 不允许搜索引擎收录（例如工具的演示页） */
  noindex?: boolean
}

const OG_IMAGE = 'media/og-cover.jpg'

function upsertMeta(attr: 'name' | 'property', key: string, value: string | undefined) {
  const existing = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`)
  if (!value) {
    existing?.remove()
    return
  }
  const el = existing ?? document.createElement('meta')
  if (!existing) {
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.setAttribute('content', value)
}

function upsertLink(rel: string, href: string | undefined) {
  const existing = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`)
  if (!href) {
    existing?.remove()
    return
  }
  const el = existing ?? document.createElement('link')
  if (!existing) {
    el.rel = rel
    document.head.appendChild(el)
  }
  el.href = href
}

/**
 * 页面级元信息：标题、描述、canonical、Open Graph / Twitter 卡片。
 * 站点是 SPA，这些标签在路由切换时由这里维护，爬虫执行 JS 时也能读到。
 */
export function usePageMeta(locale: () => Locale, meta: () => PageMeta) {
  watchEffect(() => {
    const info = meta()
    const isZh = locale() === 'zh'
    document.documentElement.lang = isZh ? 'zh-CN' : 'en'

    const origin = window.location.origin
    const canonical = `${origin}${window.location.pathname}`
    const fallbackImage = new URL(`${import.meta.env.BASE_URL}${OG_IMAGE}`, origin).toString()
    const image = info.image ? new URL(info.image, origin).toString() : fallbackImage

    document.title = info.title
    upsertMeta('name', 'description', info.description)
    upsertMeta('name', 'robots', info.noindex ? 'noindex,nofollow' : 'index,follow')
    // noindex 的页面（如 404）不要给 canonical，避免把错误地址登记为标准地址
    upsertLink('canonical', info.noindex ? undefined : canonical)

    upsertMeta('property', 'og:site_name', isZh ? SITE.brandZh : SITE.brandEn)
    upsertMeta('property', 'og:type', 'website')
    upsertMeta('property', 'og:locale', isZh ? 'zh_CN' : 'en_US')
    upsertMeta('property', 'og:url', canonical)
    upsertMeta('property', 'og:title', info.shareTitle ?? info.title)
    upsertMeta('property', 'og:description', info.description)
    upsertMeta('property', 'og:image', image)

    upsertMeta('name', 'twitter:card', 'summary_large_image')
    upsertMeta('name', 'twitter:title', info.shareTitle ?? info.title)
    upsertMeta('name', 'twitter:description', info.description)
    upsertMeta('name', 'twitter:image', image)
  })
}
