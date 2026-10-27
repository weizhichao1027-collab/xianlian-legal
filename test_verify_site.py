#!/usr/bin/env python3
"""Failure-injection tests for publishing safeguards (stdlib only).

Each test edits a temporary copy of the actual website. These are intentionally
broken publishing scenarios, not snapshots of the verifier's implementation.
"""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from verify_site import ROOT, VERSION, audit, stale_claims


class PublishingRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name) / 'site'
        shutil.copytree(ROOT, self.site, ignore=shutil.ignore_patterns('.git', '__pycache__'))

    def replace(self, name, before, after, count=1):
        path = self.site / name
        original = path.read_text(encoding='utf-8')
        self.assertIn(before, original, f'test fixture not found in {name}')
        path.write_text(original.replace(before, after, count), encoding='utf-8')

    def rejects(self, reason):
        output = audit(self.site)
        self.assertFalse(output['passed'])
        self.assertTrue(any(reason in error for error in output['errors']), output['errors'])

    def mutate_schema(self, name, change):
        path = self.site / name
        source = path.read_text(encoding='utf-8')
        match = re.search(r'(<script[^>]*application/ld\+json[^>]*>)(.*?)(</script>)', source, re.S)
        self.assertIsNotNone(match)
        data = json.loads(match.group(2))
        change(data['@graph'])
        path.write_text(source[:match.start(2)] + json.dumps(data, ensure_ascii=False)
                        + source[match.end(2):], encoding='utf-8')

    def mutate_app(self, change):
        def mutate(graph):
            app = next(node for node in graph if 'SoftwareApplication' in node.get('@type', []))
            change(app)
        self.mutate_schema('index.html', mutate)

    def test_release_is_publishable(self):
        output = audit(self.site)
        self.assertTrue(output['passed'], output['errors'])

    def test_duplicate_metadata_is_not_silently_overwritten(self):
        self.replace('index.html', '</head>', '<meta name="description" content="conflicting description"></head>')
        self.rejects('duplicate metadata description')

    def test_bot_specific_noindex_is_rejected(self):
        self.replace('index.html', '</head>', '<meta name="googlebot" content="noindex"></head>')
        self.rejects('googlebot blocked')

    def test_snippet_opt_out_is_rejected(self):
        self.replace('index.html', 'index, follow,', 'index, follow, nosnippet,')
        self.rejects('indexability/snippet blocked')

    def test_broken_json_ld_reports_failure_without_crashing(self):
        self.replace('index.html', '"@context":', 'INVALID "@context":')
        self.rejects('invalid JSON-LD')

    def test_missing_json_ld_reports_failure_without_crashing(self):
        path = self.site / 'index.html'
        source = path.read_text(encoding='utf-8')
        path.write_text(re.sub(r'<script\b[^>]*>.*?</script>', '', source, flags=re.S), encoding='utf-8')
        self.rejects('structured graph missing')

    def test_hidden_faq_cannot_satisfy_visible_answer_check(self):
        # Hiding the body leaves metadata/schema intact, reproducing hidden FAQ spam.
        self.replace('index.html', '<body', '<body hidden')
        self.rejects('FAQ answer differs')

    def test_wrong_version_in_string_type_schema_is_rejected(self):
        self.mutate_app(lambda app: app.update({'@type': 'SoftwareApplication', 'softwareVersion': '1.4'}))
        self.rejects('schema version')

    def test_stale_structured_release_notes_are_rejected(self):
        self.mutate_app(lambda app: app.update(releaseNotes='1.4：旧版功能说明'))
        self.rejects('stale structured release notes')

    def test_stale_structured_app_description_is_rejected(self):
        self.mutate_app(lambda app: app.update(description='吉他自习室 1.4：免费吉他练习 App。'))
        self.rejects('stale structured app description')

    def test_incorrect_minimum_system_is_rejected(self):
        self.mutate_app(lambda app: app.update(operatingSystem='iOS 18.0 or later'))
        self.rejects('minimum operating system mismatch')

    def test_missing_app_language_is_rejected(self):
        self.mutate_app(lambda app: app.update(inLanguage=['zh-Hans', 'en']))
        self.rejects('app languages mismatch')

    def test_incorrect_developer_identity_is_rejected(self):
        def change(graph):
            developer = next(node for node in graph if node.get('@type') == 'Organization')
            developer['name'] = 'Unverified developer'
        self.mutate_schema('index.html', change)
        self.rejects('structured developer identity')

    def test_incorrect_support_email_is_rejected(self):
        def change(graph):
            developer = next(node for node in graph if node.get('@type') == 'Organization')
            developer['contactPoint']['email'] = 'wrong@example.com'
        self.mutate_schema('index.html', change)
        self.rejects('structured support email')

    def test_update_date_must_be_visible_and_match_schema(self):
        path = self.site / 'index.html'
        source = path.read_text(encoding='utf-8')
        source = re.sub(r'<time\b', '<time hidden', source)
        path.write_text(source, encoding='utf-8')
        self.rejects('visible update date differs from page schema')

    def test_visible_update_date_text_must_match_datetime(self):
        path = self.site / 'index.html'
        source = path.read_text(encoding='utf-8')
        source, count = re.subn(r'(<time\b[^>]*>).*?(</time>)', r'\g<1>2020 年 1 月 1 日\g<2>', source)
        self.assertGreater(count, 0)
        path.write_text(source, encoding='utf-8')
        self.rejects('visible update date differs from page schema')

    def test_external_embed_is_rejected(self):
        self.replace('index.html', '</main>', '<iframe src="https://example.com/tracker"></iframe></main>')
        self.rejects('unexpected embedded external content')

    def test_root_relative_asset_typo_is_rejected(self):
        self.replace('index.html', './assets/app-icon.png', '/assets/app-icon.png')
        self.rejects('outside project path')

    def test_broken_anchor_is_rejected(self):
        self.replace('index.html', '</main>', '<a href="./support.html#does-not-exist">Support</a></main>')
        self.rejects('missing anchor support.html#does-not-exist')

    def test_latest_release_link_must_not_point_to_historical_release(self):
        self.replace('index.html', './about.html#release-' + VERSION.replace('.', '-'),
                     './about.html#release-1-4')
        self.rejects('current release details link missing')

    def test_missing_social_image_is_rejected(self):
        (self.site / 'assets/og-cover.png').unlink()
        self.rejects('missing target assets/og-cover.png')

    def test_incorrect_social_image_dimensions_are_rejected(self):
        self.replace('index.html', 'property="og:image:width" content="1200"', 'property="og:image:width" content="900"')
        self.rejects('social image dimensions mismatch')

    def test_duplicate_sitemap_entry_is_rejected(self):
        path = self.site / 'sitemap.xml'
        source = path.read_text(encoding='utf-8')
        first = re.search(r'<url>.*?</url>', source, re.S).group()
        path.write_text(source.replace('</urlset>', first + '</urlset>'), encoding='utf-8')
        self.rejects('canonical HTML set mismatch/duplicates')

    def test_inaccurate_sitemap_lastmod_is_rejected(self):
        path = self.site / 'sitemap.xml'
        source = path.read_text(encoding='utf-8')
        path.write_text(re.sub(r'<lastmod>.*?</lastmod>', '<lastmod>2020-01-01</lastmod>', source, count=1), encoding='utf-8')
        self.rejects('lastmod differs from page schema')

    def test_robots_disallow_is_rejected(self):
        (self.site / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
        self.rejects('Googlebot blocked')

    def test_missing_page_reports_failure_without_crashing(self):
        (self.site / 'privacy.html').unlink()
        self.rejects('privacy.html: cannot read')

    def test_llms_current_release_must_not_regress(self):
        with (self.site / 'llms.txt').open('a', encoding='utf-8') as stream:
            stream.write('\n当前公开版本：1.4。\n')
        self.rejects('llms: current release facts missing/stale')

    def test_llms_product_summary_must_not_regress(self):
        with (self.site / 'llms.txt').open('a', encoding='utf-8') as stream:
            stream.write('\n吉他自习室 1.4：提供吉他练习。\n')
        self.rejects('llms: current release facts missing/stale')

    def test_llms_recording_capacity_must_not_be_confused_with_faq_count(self):
        self.replace('llms.txt', '最多 24 条', '最多 27 条')
        self.rejects('recording duration/capacity differs from product contract')

    def test_historical_version_explanations_remain_allowed(self):
        self.assertFalse(stale_claims('旧版 1.3 的设置入口不同；从实际安装 1.3 起，使用统计默认关闭。'))
        self.assertFalse(stale_claims('历史说明：此前公开版本 1.3 曾提供该入口。'))
        self.assertFalse(stale_claims('历史说明：此前 1.4 候选版本使用相同的数据处理。'))
        self.assertFalse(stale_claims('历史说明：1.5 / Build 11 等待审核。'))
        self.assertTrue(stale_claims('当前公开版本：1.3。'))
        self.assertTrue(stale_claims('当前公开版本：1.4。'))
        self.assertTrue(stale_claims('1.5 / Build 11 候选版本尚未上架。'))
        self.assertTrue(stale_claims(f'{VERSION} 等待审核。'))


if __name__ == '__main__':
    unittest.main()
