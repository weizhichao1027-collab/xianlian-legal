#!/usr/bin/env python3
"""Offline publishing checks; no third-party packages or network required.

Checks consistency and discoverability, not search rankings or legal compliance.
Historical release notes are allowed; current-version claims must be up to date.
"""
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent
BASE = 'https://weizhichao1027-collab.github.io/xianlian-legal/'
APP_STORE = 'https://apps.apple.com/cn/app/id6788635183'
VERSION = '1.5'
DEVELOPER = 'Shanghai Qishan Cultural Communication Co., Ltd.'
SUPPORT_EMAIL = 'weizhichao1027@gmail.com'
APP_LANGUAGES = {'zh-Hans', 'en', 'es', 'fr', 'de', 'ja', 'ko', 'pt-BR', 'ru', 'ar', 'hi', 'id', 'it'}
PAGES = ['index.html', 'about.html', 'support.html', 'privacy.html']
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags, self.text, self.titles, self.scripts, self.stack = [], [], [], [], []
        self.visible_times = []
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        hidden = (any(item[1] for item in self.stack)
                  or tag in ('head', 'script', 'style', 'template')
                  or 'hidden' in attrs or attrs.get('aria-hidden') == 'true'
                  or bool(re.search(r'(display\s*:\s*none|visibility\s*:\s*hidden)', attrs.get('style', ''), re.I)))
        if tag == 'title':
            self.titles.append('')
        if tag == 'script':
            self.scripts.append((attrs, []))
        if tag == 'time' and not hidden:
            self.visible_times.append({'datetime': attrs.get('datetime', ''), 'text': ''})
        if tag not in VOID:
            self.stack.append((tag, hidden))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        tags = [tag for tag, hidden in self.stack]
        if 'script' in tags:
            self.scripts[-1][1].append(data)
        elif 'title' in tags:
            self.titles[-1] += data
        elif 'body' in tags and not any(hidden for tag, hidden in self.stack):
            self.text.append(data)
            if 'time' in tags:
                self.visible_times[-1]['text'] += data


def norm(value):
    return re.sub(r'\s+', '', str(value))


def types(node):
    value = node.get('@type', [])
    return value if isinstance(value, list) else [value]


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def image_size(path):
    """Read PNG and WebP dimensions without requiring Pillow in CI."""
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        return struct.unpack('>II', data[16:24])
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        kind = data[12:16]
        if kind == b'VP8X' and len(data) >= 30:
            return 1 + int.from_bytes(data[24:27], 'little'), 1 + int.from_bytes(data[27:30], 'little')
        if kind == b'VP8L' and len(data) >= 25:
            bits = int.from_bytes(data[21:25], 'little')
            return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
        if kind == b'VP8 ' and len(data) >= 30 and data[23:26] == b'\x9d\x01\x2a':
            width, height = struct.unpack('<HH', data[26:30])
            return width & 0x3fff, height & 0x3fff
    return None


def stale_claims(text):
    """Only reject present-tense claims; '旧版 1.3' and '从 1.3 起' are valid."""
    compact = norm(text)
    old = r'1\.[0-' + str(int(VERSION.split('.')[1]) - 1) + r'](?!\d)'
    current = re.escape(VERSION)
    pending = r'(?:候选版本|尚未上架|待发布|尚未发布|等待审核|待审核)'
    patterns = (r'(?:吉他自习室(?:App)?|当前(?:公开)?版本|现行版本|公开版本)[:：]?' + old,
                current + r'(?:/Build\d+)?' + pending,
                pending + r'[:：]?' + current)
    for sentence in re.split(r'[。；;\n]', compact):
        for pattern in patterns:
            for match in re.finditer(pattern, sentence):
                prefix = sentence[max(0, match.start() - 8):match.start()]
                if not re.search(r'历史|旧版|此前|曾经|当时', prefix):
                    return True
    return False


def audit(root=ROOT):
    root = Path(root).resolve()
    errors, results, docs, graphs, modified, inbound = [], [], {}, {}, {}, set()

    def check(condition, message):
        if not condition:
            errors.append(message)

    def read(name):
        try:
            return (root / name).read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            errors.append(f'{name}: cannot read: {exc}')
            return ''

    def local_target(url, source, anchor=True):
        parsed = urlparse(urljoin(BASE + source, url))
        base = urlparse(BASE)
        if parsed.netloc != base.netloc:
            return None
        check(parsed.scheme == 'https', f'{source}: non-HTTPS local URL {url}')
        # A project-relative /assets/... typo escapes this site's deployed prefix.
        if not parsed.path.startswith(base.path):
            check(False, f'{source}: local URL outside project path: {url}')
            return None
        relative = unquote(parsed.path[len(base.path):]) or 'index.html'
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            check(False, f'{source}: local URL escapes site: {url}')
            return None
        check(target.is_file(), f'{source}: missing target {relative}')
        if anchor and parsed.fragment and relative in docs:
            check(any(attrs.get('id') == unquote(parsed.fragment) for tag, attrs in docs[relative].tags),
                  f'{source}: missing anchor {relative}#{parsed.fragment}')
        return target if target.is_file() else None

    for name in PAGES:
        source = read(name)
        page = Page(source)
        docs[name] = page
        canonical = BASE + ('' if name == 'index.html' else name)
        meta_tags = [(a.get('name', a.get('property')), a.get('content', '')) for t, a in page.tags if t == 'meta' and ('name' in a or 'property' in a)]
        metas = dict(meta_tags)
        for key, count in Counter(key for key, content in meta_tags).items():
            check(count == 1, f'{name}: duplicate metadata {key}')
        check(sum(t == 'h1' for t, a in page.tags) == 1, f'{name}: one h1 required')
        check(sum(t == 'main' for t, a in page.tags) == 1, f'{name}: one main required')
        check(any(t == 'html' and a.get('lang') == 'zh-Hans' for t, a in page.tags), f'{name}: document language')
        check(len(page.titles) == 1 and bool(page.titles[0].strip()), f'{name}: one nonempty title required')
        title = page.titles[0].strip() if page.titles else ''
        check(title == metas.get('og:title') == metas.get('twitter:title'), f'{name}: social titles differ')
        check(bool(metas.get('description')), f'{name}: description missing')
        check(metas.get('author') == DEVELOPER, f'{name}: metadata developer identity')
        check(metas.get('description') == metas.get('og:description') == metas.get('twitter:description'), f'{name}: descriptions differ')
        check(VERSION in metas.get('description', ''), f'{name}: description lacks current version {VERSION}')
        check(metas.get('og:url') == canonical, f'{name}: OG URL mismatch')
        robots = {v.strip().lower() for v in metas.get('robots', '').split(',')}
        check({'index', 'follow'} <= robots and not {'noindex', 'nofollow', 'none', 'nosnippet', 'max-snippet:0'} & robots, f'{name}: indexability/snippet blocked')
        for key in ('googlebot', 'bingbot'):
            check(not re.search(r'noindex|nofollow|nosnippet|none|max-snippet\s*:\s*0', metas.get(key, ''), re.I), f'{name}: {key} blocked')
        check([a.get('href') for t, a in page.tags if t == 'link' and 'canonical' in a.get('rel', '').split()] == [canonical], f'{name}: canonical mismatch')
        check('app-id=6788635183' in metas.get('apple-itunes-app', ''), f'{name}: App Store banner ID')
        for tag, attrs in page.tags:
            if tag == 'link' and attrs.get('hreflang'):
                check(attrs['hreflang'] in ('zh-Hans', 'x-default') and attrs.get('href') == canonical, f'{name}: nonexistent language alternate')
        ids = [a['id'] for t, a in page.tags if 'id' in a]
        check(len(ids) == len(set(ids)), f'{name}: duplicate IDs')
        visible = ''.join(page.text)
        check(VERSION in visible, f'{name}: current version not visible')
        check(not stale_claims(visible), f'{name}: stale release claims')
        for key in ('description', 'og:description', 'twitter:description'):
            check(not stale_claims(metas.get(key, '')), f'{name}: stale release claims in {key}')
        for tag, attrs in page.tags:
            if tag == 'img':
                check('alt' in attrs, f'{name}: image alt missing')
                width, height = attrs.get('width', ''), attrs.get('height', '')
                check(width.isdigit() and height.isdigit() and int(width) > 0 and int(height) > 0, f'{name}: positive image dimensions required')
                target = local_target(attrs.get('src', ''), name)
                if target:
                    size = image_size(target)
                    check(size is not None, f'{name}: invalid/unsupported image {target.name}')
                    if size and width.isdigit() and height.isdigit() and int(height) > 0:
                        check(abs((int(width) / int(height)) / (size[0] / size[1]) - 1) < 0.02, f'{name}: image aspect ratio mismatch {target.name}')
        check(metas.get('twitter:card') == 'summary_large_image', f'{name}: social card type')
        check(bool(metas.get('og:image:alt')) and bool(metas.get('twitter:image:alt')), f'{name}: social image alt missing')
        og_image = metas.get('og:image', '')
        check(og_image.startswith(BASE) and og_image == metas.get('twitter:image') == metas.get('og:image:secure_url'), f'{name}: social image URL mismatch')
        target = local_target(og_image, name)
        if target:
            size = image_size(target)
            check(size is not None and tuple(str(x) for x in size) == (metas.get('og:image:width'), metas.get('og:image:height')), f'{name}: social image dimensions mismatch')
        nodes = []
        for attrs, chunks in page.scripts:
            check(attrs.get('type') == 'application/ld+json' and 'src' not in attrs, f'{name}: unexpected executable script')
            if attrs.get('type') != 'application/ld+json':
                continue
            try:
                document = json.loads(''.join(chunks))
                check(isinstance(document, dict) and document.get('@context') == 'https://schema.org', f'{name}: JSON-LD context')
                graph = document.get('@graph', []) if isinstance(document, dict) else []
                check(isinstance(graph, list) and bool(graph), f'{name}: structured graph missing')
                if isinstance(graph, list):
                    nodes.extend(node for node in graph if isinstance(node, dict))
            except (ValueError, TypeError) as exc:
                errors.append(f'{name}: invalid JSON-LD: {exc}')
        graphs[name] = nodes
        check(bool(nodes), f'{name}: structured graph missing')
        node_ids = [n['@id'] for n in nodes if '@id' in n]
        check(len(node_ids) == len(set(node_ids)), f'{name}: duplicate structured entity IDs')
        apps = [n for n in nodes if 'SoftwareApplication' in types(n)]
        check(len(apps) == 1, f'{name}: one SoftwareApplication required')
        developers = [n for n in nodes if n.get('@id') == BASE + '#developer']
        check(len(developers) == 1 and developers[0].get('name') == DEVELOPER,
              f'{name}: structured developer identity')
        if developers:
            contact = developers[0].get('contactPoint', {})
            check(isinstance(contact, dict) and contact.get('email') == SUPPORT_EMAIL,
                  f'{name}: structured support email')
        faqs = 0
        for node in nodes:
            if 'SoftwareApplication' in types(node):
                check(node.get('softwareVersion') == VERSION, f'{name}: schema version')
                if 'description' in node:
                    description = str(node['description'])
                    check(VERSION in description and not stale_claims(description),
                          f'{name}: stale structured app description')
                check(node.get('@id') == BASE + '#app', f'{name}: app entity identity')
                check(node.get('downloadUrl') == APP_STORE, f'{name}: app download URL')
                check(node.get('author') == {'@id': BASE + '#developer'}, f'{name}: app developer reference')
                if 'operatingSystem' in node or name in ('index.html', 'about.html', 'support.html'):
                    check(node.get('operatingSystem') == 'iOS 17.0 or later; iPadOS 17.0 or later',
                          f'{name}: minimum operating system mismatch')
                if name in ('index.html', 'about.html'):
                    languages = node.get('inLanguage', [])
                    check(isinstance(languages, list) and all(isinstance(item, str) for item in languages)
                          and len(languages) == len(APP_LANGUAGES)
                          and set(languages) == APP_LANGUAGES, f'{name}: app languages mismatch')
                    check(str(node.get('releaseNotes', '')).startswith(VERSION + '：'),
                          f'{name}: stale structured release notes')
                check(node.get('isAccessibleForFree') is True, f'{name}: app free status')
                offer = node.get('offers', {})
                check(isinstance(offer, dict) and str(offer.get('price')) in ('0', '0.0') and offer.get('priceCurrency') == 'CNY', f'{name}: free offer mismatch')
                check('aggregateRating' not in node and 'review' not in node, f'{name}: unverified rating/review')
            if node.get('@id') == canonical + '#webpage':
                check(node.get('url') == canonical and node.get('name') == title, f'{name}: page schema identity')
                check(node.get('description') == metas.get('description'), f'{name}: page schema description differs')
                modified[name] = node.get('dateModified')
            if 'FAQPage' in types(node):
                questions = node.get('mainEntity', [])
                check(isinstance(questions, list) and bool(questions), f'{name}: empty FAQ')
                for question in questions if isinstance(questions, list) else []:
                    if not isinstance(question, dict):
                        check(False, f'{name}: invalid FAQ question')
                        continue
                    faqs += 1
                    answer = question.get('acceptedAnswer', {})
                    answer = answer.get('text', '') if isinstance(answer, dict) else ''
                    check(bool(question.get('name')) and norm(question.get('name')) in norm(visible), f'{name}: FAQ question not visible: {question.get("name")}')
                    check(bool(answer) and norm(answer) in norm(visible), f'{name}: FAQ answer differs: {question.get("name")}')
            for item in walk(node):
                for field in ('datePublished', 'dateModified'):
                    if field in item:
                        try:
                            if not isinstance(item[field], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item[field]):
                                raise ValueError('expected YYYY-MM-DD')
                            date.fromisoformat(item[field])
                        except (ValueError, TypeError):
                            check(False, f'{name}: invalid {field}')
        check(name in modified, f'{name}: page schema dateModified missing')
        check(any(item['datetime'] == modified.get(name)
                  and re.sub(r'\D', '', item['text']) == str(modified.get(name, '')).replace('-', '')
                  for item in page.visible_times), f'{name}: visible update date differs from page schema')
        check(not any(tag in ('iframe', 'object', 'embed') for tag, attrs in page.tags),
              f'{name}: unexpected embedded external content')
        if name == 'index.html':
            release_url = BASE + 'about.html#release-' + VERSION.replace('.', '-')
            check(any(tag == 'a' and urljoin(BASE, attrs.get('href', '')) == release_url
                      for tag, attrs in page.tags), f'{name}: current release details link missing')
        results.append({'page': name, 'canonical': canonical, 'faq_count': faqs, 'bytes': len(source.encode('utf-8'))})

    for name, page in docs.items():
        for tag, attrs in page.tags:
            for attr in ('href', 'src'):
                if attr in attrs:
                    target = local_target(attrs[attr], name)
                    if tag == 'a' and target and target.name in PAGES and target.name != name:
                        inbound.add(target.name)
            if 'srcset' in attrs:
                for candidate in attrs['srcset'].split(','):
                    if candidate.strip():
                        local_target(candidate.strip().split()[0], name)
        for node in walk(graphs[name]):
            for field in ('url', 'contentUrl', 'screenshot'):
                values = node.get(field, [])
                for value in values if isinstance(values, list) else [values]:
                    if isinstance(value, str):
                        local_target(value, name)
    check(set(PAGES) <= inbound, 'navigation: orphan canonical page')
    for css in root.glob('*.css'):
        for url in re.findall(r'url\(\s*[\'"]?([^\)\'"\s]+)', css.read_text(encoding='utf-8')):
            if not url.startswith('data:'):
                local_target(url, css.name)
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'image': 'http://www.google.com/schemas/sitemap-image/1.1'}
    try:
        tree = ET.fromstring(read('sitemap.xml'))
        entries = tree.findall('s:url', ns)
        urls = [x.findtext('s:loc', namespaces=ns) for x in entries]
        expected = {BASE: 'index.html', **{BASE + n: n for n in PAGES[1:]}}
        check(len(urls) == len(set(urls)) and set(urls) == set(expected), 'sitemap: canonical HTML set mismatch/duplicates')
        for entry in entries:
            url = entry.findtext('s:loc', namespaces=ns)
            lastmod = entry.findtext('s:lastmod', namespaces=ns)
            try:
                if not isinstance(lastmod, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', lastmod):
                    raise ValueError('expected YYYY-MM-DD')
                date.fromisoformat(lastmod)
            except (ValueError, TypeError):
                check(False, f'sitemap: invalid lastmod for {url}')
            if url in expected:
                check(lastmod == modified.get(expected[url]), f'sitemap: lastmod differs from page schema for {url}')
            for image in entry.findall('image:image/image:loc', ns):
                local_target(image.text or '', 'sitemap.xml')
    except ET.ParseError as exc:
        errors.append(f'sitemap: invalid XML: {exc}')
    llms = read('llms.txt')
    check(VERSION in llms and not stale_claims(llms), 'llms: current release facts missing/stale')
    recording_limits = re.search(r'主动演奏留档最长\s*(\d+)\s*秒[、，]\s*最多\s*(\d+)\s*条', llms)
    check(recording_limits is not None and recording_limits.groups() == ('180', '24'),
          'llms: recording duration/capacity differs from product contract')
    for url in re.findall(r'\]\((https?://[^\s)]+)\)', llms):
        local_target(url, 'llms.txt')
    robots = read('robots.txt')
    robot_parser = RobotFileParser()
    robot_parser.parse(robots.splitlines())
    check(BASE + 'sitemap.xml' in (robot_parser.site_maps() or []), 'robots: sitemap declaration missing')
    for bot in ('Googlebot', 'Bingbot', 'OAI-SearchBot'):
        for url in (BASE, BASE + 'support.html', BASE + 'privacy.html', BASE + 'assets/og-cover.png'):
            check(robot_parser.can_fetch(bot, url), f'robots: {bot} blocked for {url}')
    # robots.txt here is only informational: production policy lives at host /robots.txt.
    return {'passed': not errors, 'version': VERSION, 'pages': results, 'errors': errors}


def verify():
    output = audit()
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output['passed'] else 1


if __name__ == '__main__':
    sys.exit(verify())
