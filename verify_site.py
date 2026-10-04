#!/usr/bin/env python3
"""Dependency-free prepublish checks for content, SEO metadata and local links."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

ROOT = Path(__file__).resolve().parent
BASE = 'https://weizhichao1027-collab.github.io/xianlian-legal/'
PAGES = ['index.html', 'about.html', 'support.html', 'privacy.html']

class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []; self.text = []; self.hidden = 0
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden -= 1
    def handle_data(self, data):
        if not self.hidden: self.text.append(data)

def norm(value):
    return re.sub(r'\s+', '', value)

def verify():
    errors = []; result = []; docs = {}
    def check(condition, message):
        if not condition: errors.append(message)
    for name in PAGES:
        source = (ROOT / name).read_text(); page = Page(source); docs[name] = page
        canonical = BASE + ('' if name == 'index.html' else name)
        metas = {a.get('name', a.get('property')): a.get('content') for t,a in page.tags if t == 'meta'}
        check(sum(t == 'h1' for t,a in page.tags) == 1, f'{name}: one h1 required')
        check(sum(t == 'main' for t,a in page.tags) == 1, f'{name}: one main required')
        check(len(re.findall('<title>.+?</title>', source)) == 1, f'{name}: title missing')
        check(bool(metas.get('description')), f'{name}: description missing')
        check(metas.get('og:url') == canonical, f'{name}: OG URL mismatch')
        check(metas.get('description') == metas.get('og:description') == metas.get('twitter:description'), f'{name}: descriptions differ')
        check('index' in metas.get('robots','') and 'noindex' not in metas.get('robots',''), f'{name}: indexability')
        check([a.get('href') for t,a in page.tags if t == 'link' and a.get('rel') == 'canonical'] == [canonical], f'{name}: canonical mismatch')
        ids = [a['id'] for t,a in page.tags if 'id' in a]
        check(len(ids) == len(set(ids)), f'{name}: duplicate IDs')
        check(not re.search('待发布|尚未在 App Store 发布|公开版本 1\\.2|当前下载仍为', source), f'{name}: stale release claims')
        for tag, attrs in page.tags:
            if tag == 'img':
                check(all(x in attrs for x in ('alt','width','height')), f'{name}: image dimensions/alt missing')
            if tag == 'script': check(attrs.get('type') == 'application/ld+json', f'{name}: unexpected executable script')
        graphs = [json.loads(x)['@graph'] for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',source,re.S)]
        check(len(graphs) == 1, f'{name}: structured graph missing')
        faqs = 0
        for node in graphs[0]:
            if isinstance(node['@type'],list) and 'SoftwareApplication' in node['@type']:
                check(node.get('softwareVersion') == '1.3', f'{name}: schema version')
                check('aggregateRating' not in node, f'{name}: unverified rating')
            if node['@type'] == 'FAQPage':
                faqs += len(node['mainEntity'])
                for q in node['mainEntity']:
                    check(norm(q['name']) in norm(' '.join(page.text)), f'{name}: FAQ question not visible: {q["name"]}')
                    check(norm(q['acceptedAnswer']['text']) in norm(' '.join(page.text)), f'{name}: FAQ answer differs: {q["name"]}')
        result.append({'page': name, 'canonical': canonical, 'faq_count': faqs, 'bytes': len(source.encode())})
    for name, page in docs.items():
        for tag, attrs in page.tags:
            for attr in ('href','src'):
                if attr not in attrs: continue
                u = urlparse(urljoin(BASE + name,attrs[attr]))
                if u.netloc != urlparse(BASE).netloc: continue
                if not u.path.startswith('/xianlian-legal/'): continue
                rel = unquote(u.path.removeprefix('/xianlian-legal/')) or 'index.html'
                target = ROOT / rel
                check(target.is_file(), f'{name}: missing target {rel}')
                if u.fragment and rel in docs:
                    check(any(a.get('id') == unquote(u.fragment) for t,a in docs[rel].tags), f'{name}: missing anchor {rel}#{u.fragment}')
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    tree=ET.parse(ROOT/'sitemap.xml')
    urls=[x.text for x in tree.findall('s:url/s:loc',ns)]
    check(set(urls) == {BASE, *(BASE+n for n in PAGES[1:])}, 'sitemap: canonical HTML set mismatch')
    for x in tree.findall('s:url/s:lastmod',ns): check(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',x.text)), 'sitemap: invalid lastmod')
    check('待发布' not in (ROOT/'llms.txt').read_text(), 'llms: stale release claims')
    output={'passed':not errors,'pages':result,'errors':errors}
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__ == '__main__': sys.exit(verify())
