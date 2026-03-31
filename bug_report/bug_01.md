# Bug 01 修复记录

> [!summary]
> 状态: 已完成  
> 最后更新: 2026-03-31  
> 范围: 首页、课程 portal、PDF 上传、lecture 跳转、右键删除与内部回收站

## 总览

- [x] 底部栏补上 `Lectures` 入口
- [x] 首页排布调整，上传区移到列表后方并适配横屏并排布局
- [x] 新课程 icon 去掉 emoji，统一改为课程编号
- [x] 修复课程点击无反应
- [x] 上传处理改为角落加载提示，完成后 toast 通知
- [x] 修复新增 lecture 的链接生成问题
- [x] 生成内容标题改为优先从 PDF 提取
- [x] 首页和 portal 支持独立右键删除，并移动到内部回收站
- [x] 保留输入框/文本选择场景下的基础复制、粘贴、原生右键能力

## 1. 底部栏

> [!success] 已修复
> 首页底部栏已补充 `Lectures` 按钮，并同步到 portal 底部导航。

原始参考:
![[Attachments/5da1c4e09fb4f9fa174dd3153f25266e_MD5.jpg]]

## 2. 首页排布

> [!success] 已修复
> 上传区域已放到课程列表后方。横屏下课程列表与上传区可并排展示，并对高度做了限制与滚动处理。

原始参考 1:
![[Attachments/f481fd1b99ed9a15db9ce4beea25e7f5_MD5.jpg]]

原始参考 2:
![[Attachments/da632ad418f0c91090018869a1db1c02_MD5.jpg]]

## 3. emoji 禁用

> [!success] 已修复
> 课程 icon 不再使用 emoji，统一改为课程编号，例如 `7034`、`7049`、`7002`。

原始参考:
![[Attachments/76fbab14d1c566826f2b795ccc13045a_MD5.jpg]]

## 4. 点击无反应

> [!success] 已修复
> 课程 portal 的 lecture 数据现在会返回 `slug`，卡片点击和按钮跳转均恢复正常。

原始参考:
![[Attachments/987cc0dc393a3ef788f3896072df9fba_MD5.jpg]]

## 5. 处理加载问题

> [!success] 已修复
> 上传处理改为后台轮询，加载状态显示在页面角落，完成后使用 toast 提示。  
> 同时修复了新生成 lecture 的 HTML/PDF 链接拼接错误。

补充说明:
- 生成中的状态不再阻塞主界面
- lecture 生成完成后不强制跳转
- portal 会自动刷新 lecture 列表

原始参考:
![[Attachments/815549fae484e9ac972bffd61eca5bd2_MD5.jpg]]

## 6. 生成内容标题问题

> [!success] 已修复
> 新生成内容会优先从 PDF 元数据和首页文本提取标题，不再默认显示 `upload_时间戳`。

修复结果示例:
- `Lecture 5: Portfolio Theory and Practice`

## 7. 首页和 Portal 页支持独立右键

> [!success] 已修复
> 首页课程卡片与 portal lecture 卡片都支持独立右键菜单。

当前行为:
- 首页右键: 支持删除课程，移动到内部回收站
- Portal 右键: 支持打开 lecture、复制链接、删除 lecture
- 删除操作不会直接硬删除，而是移动到 `.recycle_bin/`
- 删除记录会写入 `.recycle_bin/index.json`

回收站结构:
- 课程: `.recycle_bin/courses/...`
- Lecture: `.recycle_bin/lectures/<course_id>/...`

## 8. 保留基础复制 / 粘贴能力

> [!success] 已修复
> 自定义右键菜单只在课程卡片或 lecture 卡片上触发。  
> 输入框、可编辑区域、以及存在文本选择时，会让出原生右键菜单；如果此前已打开自定义菜单，也会先收起。

覆盖场景:
- 首页搜索框
- Portal 搜索框
- 其他输入/可编辑区域

## 验证记录

> [!check]
> 2026-03-31 已完成本地验证。

代码验证:
- `python3 -m py_compile serve.py`

功能验证:
- lecture 卡片右键菜单可正常弹出
- 在 portal 搜索框右键后，自定义菜单会关闭，原生菜单路径不再被拦截
- 删除操作后内容移动到内部回收站，而不是直接删除

Playwright 截图:
- [首页右键菜单](/Users/yaoyao/code/hku/mfin7034/Lectures/output/playwright/home-context-menu.png)
- [Portal 右键菜单](/Users/yaoyao/code/hku/mfin7034/Lectures/output/playwright/portal-after-fix.png)

## 备注

> [!info]
> 当前这个 bug 单中的条目已经全部收尾。后续如果要补“回收站恢复”功能，可以在此基础上继续扩展 `.recycle_bin/index.json` 的恢复入口。
