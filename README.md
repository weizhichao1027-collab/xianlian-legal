# 吉他自习室官方网站

营销首页、产品事实、支持和隐私政策使用静态 HTML。当前内容口径为 1.3 已上架；上架由产品负责人于 2026-10-04 确认。本次 Apple 中国区公开网页请求返回 404、Lookup 返回空结果，未独立确认公开版本或精确发布时间。功能依据 1.3 / Build 9 发布材料和实际代码，不把查询异常解释为下架。

## 文件与发布

- `index.html`：营销与下载；`about.html`：官方产品事实和能力边界。
- `support.html`：19 条问答、更新与故障处理；`privacy.html`：数据处理、旧版差异、网站与邮件。
- `llms.txt`：公开事实摘要，辅助引用；不是搜索或 AI 排名保证。
- `sitemap.xml`：仅收录 4 个 canonical HTML 页面。
- `assets/`：实际 App 截图；六张 WebP 来自 2026-10-03 的 Build 9 简体中文 iPhone 截图，宽 660px。成长数据为演示数据。
- `og-card.html` / `.css`：1200×630 社交图源模板，noindex；修改后须用浏览器重新截图到 `assets/og-cover.png`。
- `site-accessibility.css`：键盘焦点、问题目录、小屏换行与减少动态效果。

本仓库独立于 App 主仓库。远端为 `weizhichao1027-collab/xianlian-legal`，GitHub Pages 从 `main:/` 自动部署。更新后先执行 `python3 verify_site.py`，检查响应式页面与分享图，再提交和推送 main。推送后的 GitHub Actions 校验只报告问题，不是 Pages 发布前的阻塞门禁，因此本地校验必须先通过。等待 Pages 构建完成，并比较公网响应与本地文件 SHA-256。回滚使用 `git revert <commit>`，不要覆盖历史。

支持和隐私正文的维护源同时位于 App 主仓库 `AppStore/Legal/`。修改时必须同步正文与 HTML；FAQ JSON-LD 的问题和答案必须与页面可见内容一致。`verify_site.py` 会检查链接、锚点、图片属性、canonical、社交摘要、版本及问答一致性。HTML 首屏内容无需 JavaScript，未嵌入第三方追踪脚本。

## SEO / GEO 边界

保留原有 Google 验证标签，但没有因此假定 Search Console 所有权验证成功。没有访问 Search Console、Bing Webmaster 或执行 sitemap 提交；后续在已验证的网站资源内提交 `https://weizhichao1027-collab.github.io/xianlian-legal/sitemap.xml`，再检查索引和抓取结果。不使用已停用的匿名 sitemap ping。

搜索引擎读取的是域名根路径 `/robots.txt`，不是 `/xianlian-legal/robots.txt`。2026-10-04 根路径返回 404，未观察到 robots 抓取阻止；本仓库里的文件仅保留部署说明与 sitemap 地址。若需要控制机器人，须在现有域名根站点或未来自定义域名上配置，不能声称项目目录配置已经生效。

GEO 通过清晰定义、稳定实体 ID、可见问答、官方来源、更新时间与能力边界实现。App 支持 13 语言不等于网站已提供 13 个语言版本；只声明实际存在的简体中文页面。没有虚构评分、评论、下载量、真人教学或学习成果。结构化数据有效不保证富结果；llms.txt 不保证被模型采纳。

参考：[Google AI 搜索说明](https://developers.google.com/search/docs/appearance/ai-features)、[robots.txt 文档](https://developers.google.com/search/docs/crawling-indexing/robots/intro)、[GitHub 隐私声明](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)、[友盟隐私政策](https://www.umeng.com/page/policy/)。完整交接与验证证据保留在 App 主仓库 `Documentation/Project/Website-Launch-2026-10-04.md` 和 `Documentation/Verification/2026-10-04-Website-Launch/`。
