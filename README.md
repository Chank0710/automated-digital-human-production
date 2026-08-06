# 自动化数字人制作

一套可中断恢复的 Codex 数字人视频工作流。支持替换人物、背景、台词、音色、版式、字幕和同步知识板。

项目固定使用 [`video-use`](https://github.com/browser-use/video-use) 完成剪辑和画面质检。配置、UTF-8 API 请求、TTS 预检、状态恢复、防重复提交、音频标准化和可量化视频检查由确定性 Python 脚本执行，不再依靠模型记住长流程。

## 可靠性结构

- `config.json` 是用户资料和授权的唯一数据源。
- `state.json` 原子记录锁定的 API/网页通道、步骤、请求指纹、TTS 时长、任务 ID、状态和输出地址。
- `heygen_client.py` 统一读取密钥并发送 UTF-8 HTTP 请求。
- `workflow.py` 是唯一支持的 API 工作流入口。
- `check_tts.py` 自动拒绝问号、替换字符、异常中文语速以及长台词只生成 1-10 秒音频。
- `check_video.py` 检查时长窗口、音轨、透明通道、宽度和高度。

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
