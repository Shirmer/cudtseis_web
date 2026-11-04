#!/usr/bin/env python3
"""Build static public pages from shared templates and supplied article content."""
from pathlib import Path
from html import escape
import argparse
import json
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = '20261104-structure2'
ARTICLES = json.loads((ROOT / 'content/articles.json').read_text())
CATEGORIES = {
    'research-bulletin': ('科研快报', 'Research bulletin', '论文成果、研究方法与学术进展。'),
    'lab-news': ('实验室快讯', 'Laboratory news', '学术交流、野外工作与团队活动。'),
    'major-earthquakes': ('大震信息', 'Major earthquakes', '重要地震事件与相关研究资料。'),
    'earthquake-science': ('地震科普', 'Earthquake science', '认识地震与地球，阅读地学知识。'),
}


def article_url(article):
    return '/research-bulletin/' + article['slug'] + '/'


def root_links(value):
    replacements = {'index.html': '/'}
    replacements.update({a['legacy']: article_url(a) for a in ARTICLES})
    def replace(match):
        attr, url = match.groups()
        path, sep, fragment = url.partition('#')
        if path in replacements:
            url = replacements[path] + (sep + fragment if sep else '')
        elif path.startswith('assets/') or path in ('catalog.html', 'terra.html'):
            url = '/' + url
        return attr + '="' + url + '"'
    return re.sub(r'(href|src)="([^"]+)"', replace, value)


def page(title, description, body, *, category='', home=False, article=False, noindex=False):
    header = (ROOT / 'templates/header.html').read_text()
    section = 'top' if home else 'news' if category or title == '新闻资讯' else ''
    if section:
        header = header.replace('data-section="' + section + '"', 'data-section="' + section + '" aria-current="' + ('location' if home else 'page') + '"')
    if category:
        header = header.replace('data-category="' + category + '"', 'data-category="' + category + '" aria-current="page"')
    styles = ['/assets/css/site.css']
    if home:
        styles.append('/assets/css/home.css')
    else:
        styles.append('/assets/css/news.css')
    styles.extend(['/assets/css/sections.css', '/assets/css/navigation.css'])
    css = '\n'.join('  <link rel="stylesheet" href="' + s + '?v=' + VERSION + '">' for s in styles)
    robots = '\n  <meta name="robots" content="noindex">' if noindex else ''
    date = ('\n  <meta property="article:published_time" content="' + article['date'] + '">') if article else ''
    image = '/assets/img/news/' + article['image'] if article else '/assets/img/field-observation.webp'
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · 成都理工大学地震研究中心</title>
  <meta name="description" content="{escape(description, quote=True)}">
  <meta name="theme-color" content="#00549d">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(description, quote=True)}">
  <meta property="og:type" content="{'article' if article else 'website'}">
  <meta property="og:image" content="{image}">{date}{robots}
  <link rel="icon" type="image/png" href="/assets/img/seislab-favicon.png">
{css}
  <script src="/assets/js/site.js?v={VERSION}" defer></script>
</head>
<body data-page="{'home' if home else 'article' if article else 'section'}" data-nav-section="{section}" data-category="{category}">
  <a class="skip-link" href="#main">跳到主要内容</a>
  <div class="site-page" id="site-top">
{header}
    <main id="main" tabindex="-1">
{root_links(body)}
    </main>
{(ROOT / 'templates/footer.html').read_text()}
  </div>
</body>
</html>
'''


def breadcrumb(label):
    return f'<nav class="article-breadcrumb" aria-label="当前位置"><a href="/">首页</a><span aria-hidden="true">/</span><a href="/news/">新闻资讯</a><span aria-hidden="true">/</span><span aria-current="page">{label}</span></nav>'


def category_links(current=''):
    return '<nav class="category-links" aria-label="资讯栏目">' + ''.join(
        f'<a href="/{slug}/"' + (' aria-current="page"' if slug == current else '') + f'>{data[0]}</a>'
        for slug, data in CATEGORIES.items()) + '</nav>'


def cards():
    return '<div class="archive-list">' + ''.join(f'''
<article class="archive-entry">
  <div class="archive-entry-copy"><div class="archive-meta"><time datetime="{a['date']}">{a['date']}</time><span>{a['journal']}</span></div>
  <h2><a href="{article_url(a)}">{a['title']}</a></h2><p>{a['summary']}</p>
  <a class="text-link" href="{article_url(a)}">阅读全文 <span aria-hidden="true">→</span></a></div>
  <img src="/assets/img/news/{a['image']}" alt="{a['title']}的研究配图" width="240" height="160" loading="lazy" decoding="async">
</article>''' for a in ARTICLES) + '</div>'


def build():
    pages = {}
    home = (ROOT / 'content/home.html').read_text().replace('{{science}}', (ROOT / 'content/science.html').read_text())
    pages['index.html'] = page('地震观测与深部结构研究', '成都理工大学地震研究中心：研究方向、科研快报、团队与科研工具。', home, home=True)
    for slug, (title, english, description) in CATEGORIES.items():
        if slug == 'research-bulletin':
            content = f'<p class="archive-count">共 {len(ARTICLES)} 篇成果简报，按本站发布日期排列。</p>' + cards()
        elif slug == 'earthquake-science':
            content = '<div class="science-archive">' + (ROOT / 'content/science.html').read_text() + '</div>'
        elif slug == 'lab-news':
            content = '<div class="section-empty"><h2>暂无发布的实验室快讯</h2><p>科研论文与成果简报可在“科研快报”中阅读。</p><a class="text-link" href="/research-bulletin/">浏览科研快报 <span aria-hidden="true">→</span></a></div>'
        else:
            content = '<div class="section-empty"><h2>暂无发布的大震信息</h2><p>地震目录目前提供虚构示例，用于体验检索与浏览，不作为实时震情信息。</p><a class="text-link" href="/catalog.html">进入地震目录 <span aria-hidden="true">→</span></a></div>'
        body = f'<div class="archive-shell" id="top">{breadcrumb(title)}<header class="archive-header"><p class="article-category">{english}</p><h1>{title}</h1><p>{description}</p></header>{category_links(slug)}{content}</div>'
        pages[slug + '/index.html'] = page(title, description, body, category=slug)
    body = '<div class="archive-shell" id="top">' + breadcrumb('资讯总览') + '<header class="archive-header"><p class="article-category">News & updates</p><h1>新闻资讯</h1><p>浏览研究成果、实验室动态、地震信息与科普内容。</p></header>' + category_links() + '<h2 class="archive-section-title">最新科研快报</h2>' + cards() + '</div>'
    pages['news/index.html'] = page('新闻资讯', '研究成果、实验室动态、地震信息与科普内容。', body)
    for article in ARTICLES:
        title = article['title']
        year, month, day = article['date'].split('-')
        related = ''.join(f'<li><a href="{article_url(a)}">{a["title"]}</a><time datetime="{a["date"]}">{a["date"]}</time></li>' for a in ARTICLES if a != article)
        body = f'''<div class="news-shell" id="top">
          <nav class="article-breadcrumb" aria-label="当前位置"><a href="/">首页</a><span aria-hidden="true">/</span><a href="/research-bulletin/">科研快报</a><span aria-hidden="true">/</span><span aria-current="page">正文</span></nav>
          <article class="news-article" aria-labelledby="article-title"><header class="article-header"><p class="article-category">科研快报 · {article['journal']}</p><h1 id="article-title">{title}</h1><div class="article-meta"><span>发布日期：<time datetime="{article['date']}">{year}年{int(month)}月{int(day)}日</time></span></div></header>
{(ROOT / 'content/articles' / (article['slug'] + '.html')).read_text()}
          <div class="article-return"><a class="text-link" href="/research-bulletin/"><span aria-hidden="true">←</span> 返回科研快报</a><a class="text-link" href="/">中心首页 <span aria-hidden="true">→</span></a></div></article>
          <section class="article-related" aria-labelledby="related-title"><h2 id="related-title">继续阅读</h2><ul>{related}</ul></section></div>'''
        pages['research-bulletin/' + article['slug'] + '/index.html'] = page(title, article['summary'], body, category='research-bulletin', article=article)
        url = article_url(article)
        pages[article['legacy']] = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><link rel="canonical" href="https://seis.cdut.edu.cn{url}"><meta http-equiv="refresh" content="0; url={url}"></head><body><p>文章地址已更新。<a href="{url}">前往阅读：{title}</a></p></body></html>
'''
    pages['404.html'] = page('页面未找到', '返回研究中心首页或浏览资讯栏目。', '<div class="not-found" id="top"><div class="not-found__inner"><span class="section-index">404 / PAGE NOT FOUND</span><h1>这里没有找到页面</h1><p>链接可能已经失效，或者地址输入有误。你可以返回首页，或从新闻资讯中继续浏览。</p><div class="not-found-actions"><a class="button primary" href="/">返回首页</a><a class="button" href="/news/">浏览新闻资讯</a></div></div></div>', noindex=True)
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check generated HTML without modifying files')
    args = parser.parse_args()
    outdated = []
    pages = build()
    for name, text in pages.items():
        target = ROOT / name
        if args.check:
            if not target.exists() or target.read_text() != text:
                outdated.append(name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    if outdated:
        raise SystemExit('Outdated pages: ' + ', '.join(outdated))
    print(('Checked ' if args.check else 'Built ') + str(len(pages)) + ' static pages')


if __name__ == '__main__':
    main()
