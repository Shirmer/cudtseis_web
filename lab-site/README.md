# 成都理工大学地震研究中心官网

中文名称：成都理工大学地震研究中心；英文标识：EARTHQUAKE CENTER。

独立的纯静态 HTML/CSS/JS 网站，无第三方依赖、构建步骤、外部字体或 CDN 请求，与公司官网源码分开维护。

## 页面与功能

- `index.html`：蓝白配色主页，包含中心概况、科研平台入口、科研快报、实验室快讯、大震信息、地震科普、成都理工大学地震台、研究方向、研究团队和联系信息。
- `catalog.html`：地震目录独立入口，支持示例事件筛选、选择与 CSV 导出；事件均为明确标注的虚构演示数据。
- `terra.html`：左侧多工具切换的 Terra 工作台，包含科研问答、波形、频谱、定位、文献检索、精读、翻译、笔记和报告草拟。分析输出为预设示例，不执行真实计算或调用 AI 后端。
- `404.html`、`robots.txt`：错误页面与搜索引擎访问规则。
- `assets/css/`、`assets/js/`、`assets/img/`：运行所需静态资源。

笔记可手动保存在当前浏览器 localStorage，并导出 Markdown。文件选择仅展示文件名，不读取或上传内容。科研快报、实验室快讯和大震信息尚无真实条目，页面使用空状态，不编造新闻。

## 本地预览

在仓库根目录执行：

```sh
python3 -m http.server 4321 --directory lab-site
```

打开 <http://127.0.0.1:4321/>。入口链接均使用相对路径，可部署在不同域名的网站根目录。

## 当前部署

- 公网临时入口：<https://seis.cdutseis.com/>。
- 网站文件位于学校服务器 `/srv/earthquake-center/current`，由独立 Nginx 容器提供服务。
- 访问链路：腾讯云 HTTPS 入口 → frp → 学校网站。腾讯云不保存该站网页副本。
- 学校正式域名 `seis.cdut.edu.cn` 保持学校统一反代设计，尚待完成公网入口验证。
- 配置、更新步骤和证书维护见 [网站部署说明](../deployment/websites/README.md) 与 [frp 说明](../deployment/frp/README.md)。

发布只包含四个 HTML、robots.txt、两份 CSS、两份 JavaScript，以及 `field-observation.webp`、`seislab-mark.png`、`seislab-favicon.png`。不要把 README、内部文档或本地预览产物上传到公开网站目录。

## 内容维护

主页配图明确标注为示意图，标记图不是已核实的学校官方校徽。网页使用的蓝色为设计配色，并非声称学校官方标准色号。团队姓名、职称及研究范围沿用现有资料，后续维护应以学院正式资料为准；未公开未经确认的联系邮箱。

旧平台模块盘点保存在 [历史功能清单](docs/functional-modules.md)，仅供未来接入参考，不代表当前静态网站已提供这些后端能力。
