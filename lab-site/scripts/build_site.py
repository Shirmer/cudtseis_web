#!/usr/bin/env python3
"""Build static public pages from shared templates and supplied article content."""
from pathlib import Path
from html import escape
import argparse
import json
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = '20261128-navigation'
ARTICLES = json.loads((ROOT / 'content/articles.json').read_text(encoding='utf-8'))
CATEGORIES = {
    'research-bulletin': ('科研快报', 'Research bulletin', '论文成果、研究方法与学术进展。'),
    'lab-news': ('学术交流', 'Academic exchange', '地球物理学论坛与学术活动。'),
    'major-earthquakes': ('大震信息', 'Major earthquakes', '重要地震事件与相关研究资料。'),
    'earthquake-science': ('地震科普', 'Earthquake science', '认识地震与地球，阅读地学知识。'),
}


def article_url(article):
    return article.get('external_url') or '/research-bulletin/' + article['slug'] + '/'


def root_links(value):
    replacements = {'index.html': '/'}
    replacements.update({a['legacy']: article_url(a) for a in ARTICLES if 'legacy' in a})
    def replace(match):
        attr, url = match.groups()
        path, sep, fragment = url.partition('#')
        if path in replacements:
            url = replacements[path] + (sep + fragment if sep else '')
        elif path.startswith('assets/') or path in ('catalog.html', 'terra.html'):
            url = '/' + url
        return attr + '="' + url + '"'
    return re.sub(r'(href|src)="([^"]+)"', replace, value)


def page(title, description, body, *, category='', home=False, article=False, noindex=False, nav_section=''):
    header = (ROOT / 'templates/header.html').read_text(encoding='utf-8')
    section = 'top' if home else nav_section or ('news' if category or title == '新闻资讯' else '')
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
{(ROOT / 'templates/footer.html').read_text(encoding='utf-8')}
  </div>
</body>
</html>
'''


def breadcrumb(label):
    return f'<nav class="article-breadcrumb" aria-label="当前位置"><a href="/">首页</a><span aria-hidden="true">/</span><a href="/news/">新闻资讯</a><span aria-hidden="true">/</span><span aria-current="page">{label}</span></nav>'


def category_links(section, current=''):
    label, items = {
        'news': ('新闻资讯', (('major-earthquakes', '/major-earthquakes/', '大震信息'), ('catalog', '/catalog.html', '地震目录'))),
        'science': ('科学传播', (('lab-news', '/lab-news/', '学术交流'), ('earthquake-science', '/earthquake-science/', '地震科普'))),
    }[section]
    return f'<nav class="category-links" aria-label="{label}">' + ''.join(
        f'<a href="{url}"' + (' aria-current="page"' if slug == current else '') + f'>{title}</a>'
        for slug, url, title in items) + '</nav>'


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
    home = (ROOT / 'content/home.html').read_text(encoding='utf-8').replace('{{science}}', (ROOT / 'content/science.html').read_text(encoding='utf-8'))
    pages['index.html'] = page('地震观测与深部结构研究', '成都理工大学地震研究中心：研究方向、科研快报、团队与科研工具。', home, home=True)
    for slug, (title, english, description) in CATEGORIES.items():
        if slug == 'research-bulletin':
            content = f'<p class="archive-count">共 {len(ARTICLES)} 篇成果简报，按本站发布日期排列。</p>' + cards()
        elif slug == 'earthquake-science':
            content = (ROOT / 'content/science-series.html').read_text(encoding='utf-8') + '<div class="science-archive">' + (ROOT / 'content/science.html').read_text(encoding='utf-8') + '</div>'
        elif slug == 'lab-news':
            content = (ROOT / 'content/weekly-bulletin.html').read_text(encoding='utf-8')
        else:
            content = '<div class="section-empty"><h2>暂无发布的大震信息</h2><p>地震目录目前提供虚构示例，用于体验检索与浏览，不作为实时震情信息。</p><a class="text-link" href="/catalog.html">进入地震目录 <span aria-hidden="true">→</span></a></div>'
        section = 'research' if slug == 'research-bulletin' else 'news' if slug == 'major-earthquakes' else 'science'
        trail = breadcrumb(title) if section == 'news' else ''
        navigation = category_links(section, slug) if section != 'research' else ''
        body = f'<div class="archive-shell" id="top">{trail}<header class="archive-header"><p class="article-category">{english}</p><h1>{title}</h1><p>{description}</p></header>{navigation}{content}</div>'
        pages[slug + '/index.html'] = page(title, description, body, category=slug, nav_section=section)
    for slug, title, description, section in (
        ('education', '人才培养', '《地震学》一流课程与虚拟仿真实验。', 'education'),
        ('academic-exchange', '地震公开课', '观看地震公开课，了解地震研究与抗震救灾。', 'research'),
    ):
        content = (ROOT / 'content' / (slug + '.html')).read_text(encoding='utf-8')
        body = f'<div class="archive-shell" id="top"><header class="archive-header"><h1>{title}</h1><p>{description}</p></header>{content}</div>'
        pages[slug + '/index.html'] = page(title, description, body, nav_section=section)
    description = '浏览学术活动和地震科普文章。'
    body = f'<div class="archive-shell" id="top"><header class="archive-header"><h1>科学传播</h1><p>{description}</p></header>{category_links("science")}</div>'
    pages['science/index.html'] = page('科学传播', description, body, nav_section='science')
    description = '浏览大震信息与地震目录。'
    body = f'<div class="archive-shell" id="top"><header class="archive-header"><h1>新闻资讯</h1><p>{description}</p></header>{category_links("news")}</div>'
    pages['news/index.html'] = page('新闻资讯', description, body)
    for article in ARTICLES:
        if 'external_url' in article:
            continue
        title = article['title']
        year, month, day = article['date'].split('-')
        related = ''.join(f'<li><a href="{article_url(a)}">{a["title"]}</a><time datetime="{a["date"]}">{a["date"]}</time></li>' for a in ARTICLES if a != article)
        body = f'''<div class="news-shell" id="top">
          <nav class="article-breadcrumb" aria-label="当前位置"><a href="/">首页</a><span aria-hidden="true">/</span><a href="/research-bulletin/">科研快报</a><span aria-hidden="true">/</span><span aria-current="page">正文</span></nav>
          <article class="news-article" aria-labelledby="article-title"><header class="article-header"><p class="article-category">科研快报 · {article['journal']}</p><h1 id="article-title">{title}</h1><div class="article-meta"><span>发布日期：<time datetime="{article['date']}">{year}年{int(month)}月{int(day)}日</time></span></div></header>
{(ROOT / 'content/articles' / (article['slug'] + '.html')).read_text(encoding='utf-8')}
          <div class="article-return"><a class="text-link" href="/research-bulletin/"><span aria-hidden="true">←</span> 返回科研快报</a><a class="text-link" href="/">中心首页 <span aria-hidden="true">→</span></a></div></article>
          <section class="article-related" aria-labelledby="related-title"><h2 id="related-title">继续阅读</h2><ul>{related}</ul></section></div>'''
        pages['research-bulletin/' + article['slug'] + '/index.html'] = page(title, article['summary'], body, category='research-bulletin', article=article, nav_section='research')
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
            if not target.exists() or target.read_text(encoding='utf-8') != text:
                outdated.append(name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
    if outdated:
        raise SystemExit('Outdated pages: ' + ', '.join(outdated))
    print(('Checked ' if args.check else 'Built ') + str(len(pages)) + ' static pages')


if __name__ == '__main__':
    main()
