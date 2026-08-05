# 自动化数字人制作

一套面向中文用户的 Codex 数字人视频制作 Skill，可自由更换人物、背景、台词、音色、版式和同步知识板。

本项目固定使用 [`video-use`](https://github.com/browser-use/video-use) 完成剪辑与质量控制，数字人生成服务商可以使用 HeyGen，也可以替换为提供同等能力的其他 API。

英文版仓库：[heygen-digital-human-video](https://github.com/Chank0710/heygen-digital-human-video)

## 解决的问题

- 防止中文台词经过非 UTF-8 命令管道后变成问号
- 防止把异常的一至十秒截断视频当作完整成片
- 正确识别 VP9 WebM 的 `alpha_mode=1` 透明通道
- 有原生透明通道时禁止再次进行黑底抠像
- 改善头发、眼镜、手指、白大褂和运动边缘
- 防止把非 WAV 音频未经本地检测和转换就上传到 HeyGen
- 在制作前主动向用户收集 API、权限、人物、背景、台词、音色和交付规格

## 环境要求

- 支持安装 Skill 的 Codex
- 已安装 `video-use`
- FFmpeg 和 FFprobe 已加入 `PATH`
- Python 3.10 或更高版本
- HeyGen 或其他数字人服务商账号与 API
- 人物肖像、声音克隆和素材的合法授权

## 安装

```powershell
git clone https://github.com/Chank0710/automated-digital-human-production.git "$env:USERPROFILE\.codex\skills\heygen-digital-human-video-zh"
```

在 Codex 中调用：

```text
使用 $heygen-digital-human-video-zh 帮我制作一条数字人视频。
```

Skill 会使用固定换行的纯文本模板收集 API、权限、人物、背景、台词、音色、画幅、字幕和同步知识板等信息，不再询问发布平台。用户可以自然描述或上传素材，不需要保持模板格式。

聊天中粘贴的 API Key 不会被当作已经自动进入运行环境。已有登录状态时可以使用 HeyGen 网页；否则用户运行 `scripts/configure_heygen_key.ps1`，通过隐藏输入把密钥配置到 Windows 用户环境。用户上传的音频会先在本地检测，并在需要时自动转换为 HeyGen 兼容的 PCM WAV。

## 目录说明

- `SKILL.md`：完整中文工作流和必须遵守的规则
- `scripts/check_video.py`：中文视频检查工具
- `scripts/configure_heygen_key.ps1`：隐藏输入并配置 HeyGen API Key
- `references/provider-adapter.md`：数字人服务商适配说明
- `agents/openai.yaml`：Codex 中文界面元数据

## 安全要求

不要提交 API Key、`.env` 文件、客户素材、克隆音色样本或生成视频。不得把聊天中粘贴的密钥放进命令参数或日志。应使用已登录的 HeyGen 网页，或使用 PowerShell 配置脚本的隐藏输入。

## 开源协议

MIT
