# 自动化数字人批量视频生产流水线

基于 Python + HeyGen API 构建可断点续跑、自动质检、无人值守的数字人口播视频批量生产工具，专为自媒体科普 IP、企业培训、AI 工作室内容工业化设计

项目固定使用 [`video-use`](https://github.com/browser-use/video-use) 完成剪辑和画面质检。配置、UTF-8 API 请求、TTS 预检、状态恢复、防重复提交、音频标准化和可量化视频检查由确定性 Python 脚本执行，不再依靠模型记住长流程。

## 项目亮点

- 断点续跑
  
  使用本地 JSON 存储全流程任务状态，关机、断电、网络崩溃、程序意外终止后，重启自动从失败节点继续渲染，无需重复生成音频、重复提交付费渲染任务，节省 API 额度。

- 双层自动化质检
  
  TTS 台词预检：过滤超长文本、特殊符号、无效语句，提前拦截不合格文案；
  
  FFmpeg 视频成片校验：自动检测黑屏、无音轨、音画不同步、分辨率异常，劣质视频直接阻断归档。


## 环境要求

- 支持安装 Skill 的 Codex
- [`video-use`](https://github.com/browser-use/video-use)
- Python 3.10 或更高版本
- FFmpeg 和 FFprobe 已加入 `PATH`
- HeyGen 或兼容服务商权限
- 合法的肖像、声音和素材授权

## 安装

```powershell
git clone https://github.com/Chank0710/automated-digital-human-production.git "$env:USERPROFILE\.codex\skills\heygen-digital-human-video-zh"
```

在 Codex 中调用：

```text
使用 $heygen-digital-human-video-zh 帮我制作数字人视频。
```

## 工作流命令

```powershell
python scripts/workflow.py init 项目目录
python scripts/workflow.py channel 项目目录 api
python scripts/workflow.py validate 项目目录
python scripts/workflow.py auth 项目目录
python scripts/workflow.py avatars 项目目录
python scripts/workflow.py voices 项目目录
python scripts/workflow.py prepare-audio 项目目录
python scripts/workflow.py tts 项目目录
python scripts/workflow.py create 项目目录
python scripts/workflow.py poll 项目目录
python scripts/workflow.py record-web 项目目录 --job-id 任务ID --status submitted
python scripts/workflow.py status 项目目录
```

查询人物前必须选择 `api` 或 `web`，且整个项目只使用这一通道。网页模式会拒绝 API 命令。开始工作后确需切换时，必须先获得用户确认并运行 `channel ... --confirm-switch`；工作流会先归档旧状态，再清空原通道进度。

运行 `scripts/configure_heygen_key.ps1`，通过隐藏输入配置 API Key。严禁把密钥写进项目 JSON 或 Git。

## 验证

```powershell
python scripts/selftest.py
python scripts/check_video.py 成片 --require-audio --width 1920 --height 1080 --expected-duration 45
```

主观画面固定抽查首帧、25%、50%、75% 和尾帧。

## 开源协议

MIT
