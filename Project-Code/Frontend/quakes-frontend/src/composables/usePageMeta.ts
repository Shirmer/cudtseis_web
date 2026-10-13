import { watchEffect } from 'vue'
import type { Locale } from '../config/site'

export function usePageMeta(locale: () => Locale, title: () => string) {
  watchEffect(() => {
    document.documentElement.lang = locale() === 'zh' ? 'zh-CN' : 'en'
    document.title = title()
  })
}
