# 吉他自习室官方网站

营销首页、产品事实、支持与隐私政策为无需 JavaScript 的静态 HTML。当前版本 **1.4 已上架**；2026-10-24 Apple 中国区、美国区公开 Lookup 均确认 1.4、免费、iOS 17.0 起。Apple 记录的本版发布时间为北京时间 2026-10-24 05:28:23。Build 10 来自对应发布关联与签名包记录，公开 Lookup 不提供 Build 号。

## 文件与维护

- `index.html`：营销、下载、6 条产品问答、1.4 更新。
- `about.html`：产品身份、80 课 / 72 首静态和弦分段伴奏材料、真实能力边界。
- `support.html`：24 条使用与故障问答；`privacy.html`：数据处理、旧版差异、网站与邮件。
- `llms.txt`：可引用的公开事实摘要，不是搜索排名信号。
- `sitemap.xml`：仅列四个 canonical HTML 页面，lastmod 对应实际内容更新时间。
- `assets/manifest.json`：六张实际界面的来源、尺寸与 SHA-256。采用 1.4 发布材料中的中文原图（10-21 采集、10-22 复用），宽 660px WebP，内容未重绘。
- `assets/growth.webp` 为兼容已有 URL 保留文件名，当前展示同条件录音对比。进度和音频包含演示数据与合成样本，不是学习效果证据。
- `og-card.html` / `.css`：1200×630 分享封面源模板，noindex；修改后用浏览器重截图 `assets/og-cover.png`。
- `site-accessibility.css`：键盘焦点、跳到正文、问题目录、换行与减少动态效果。

支持和隐私同时维护于 App 主仓库 `AppStore/Legal/`，FAQ JSON-LD 必须与可见正文一致。无第三方执行脚本、外部字体或新增网站跟踪器。

## 本地检查、发布与回滚

```sh
python3 verify_site.py
python3 -m unittest -v test_verify_site
python3 -m http.server 8765 --bind 127.0.0.1
```

检查四页在 375 / 768 / 1440 CSS px 下的展示、图片加载、键盘与目录跳转，以及分享封面。验证器检查 metadata、JSON-LD、可见 FAQ、当前版本、canonical、站内文件和锚点、实际图片尺寸、sitemap 与日期；18 个回归测试含缺失页面、坏 JSON、错误 metadata、隐藏 FAQ、旧版摘要、坏链接、图片与 sitemap 故障注入。

本仓库独立于 App 主仓库，远端 `weizhichao1027-collab/xianlian-legal`，Pages 从 `main:/` 自动部署。检查通过后提交并推送 main，等待验证与 Pages 工作流成功，再核对公网文件 HTTP 与 SHA-256。legacy Pages 不被验证工作流阻塞，所以本地检查必须先通过。回滚用 `git revert <commit>` 再推送，不覆盖既有历史。主 App 仓库无远端，不能将其本地提交写成已推送。

## SEO / GEO

统一名称、版本、开发者、直接问答、可见来源与能力边界；稳定实体 ID、canonical、OG/Twitter、SoftwareApplication、Breadcrumb、FAQPage 与可见内容同步。仅声明实际存在的简体中文网页，不因 App 有 13 语言而生成虚假网页 hreflang；不编造评分、下载量、评论或学习效果。

Google 当前说明 llms.txt 不影响搜索可见性或排名；不需要 AI 专用结构化数据。FAQPage 作为语义描述保留，Google 已停止 FAQ 富结果展示。结构化数据通过不等于收录或排名，GEO 也不保证生成式系统引用。

保留 Google 验证标签，尚未登录确认 Search Console 或 Bing Webmaster 所有权，也未提交 sitemap。后续在已验证资源中提交 `https://weizhichao1027-collab.github.io/xianlian-legal/sitemap.xml`，检查四页索引、生成式 AI 控制和效果报告。不使用已停用的匿名 ping 接口。

爬虫规则读取域名根 `/robots.txt`，项目目录的 `robots.txt` 只作说明，不能控制整站抓取。若需调整控制，应在域名根站点或自定义域名配置，并另行核实。

来源：[Google AI 优化](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)、[Google 更新记录](https://developers.google.com/search/updates)、[内容控制](https://developers.google.com/search/docs/crawling-indexing/control-what-you-share)、[Bing 指南](https://www.bing.com/webmasters/help/bing-webmaster-guidelines-30fba23a)、[GitHub 隐私](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)、[友盟隐私](https://www.umeng.com/page/policy/)。

完整交接、部署提交与核验结果存于 App 主仓库 `Documentation/Project/Website-Launch-2026-10-24.md` 和 `Documentation/Verification/2026-10-24-Website-Launch/`。
