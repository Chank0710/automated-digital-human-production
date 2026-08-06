---
name: heygen-digital-human-video-zh
description: 制作可替换人物、背景、台词、音色、版式和同步知识板的专业数字人视频。用于 HeyGen 或兼容服务商的数字人、医生口播、专家讲解、AI 主播、透明人物合成视频和可中断恢复的数字人生产流程。生成前收集 API、授权和素材，固定运行内置结构化工作流，并使用 video-use 完成剪辑与质量检查。
---

# 自动化数字人制作

## 信息收集

使用以下纯文本模板。允许用户自然描述、任意顺序回答或上传文件，不要求保持格式。不得增加“发布平台”。

```text
服务商/API：
人物：
背景：
台词：
目标时长：
音色：
画幅与分辨率：
风格与品牌元素：
字幕：
同步知识板：
肖像/声音/素材授权：
```

整理回复时用 `[已收到]` 和 `[待提供]` 标记。

## 固定执行路径

禁止临时编写 `curl`、PowerShell 到 Python 的文字管道或一次性 API 请求脚本。所有中文和配置必须经过 UTF-8 JSON，并调用内置工作流。

1. 完整读取已安装的 `video-use` `SKILL.md` 和 `helpers/` 文件。不得修改它，把它作为固定剪辑与质检依赖。
2. 初始化项目：

```powershell
python scripts/workflow.py init 项目目录
```

3. 把确认后的资料写入 `项目目录/config.json`。严禁把 API Key 写入配置。持续校验直到没有缺失字段：

```powershell
python scripts/workflow.py validate 项目目录
```

4. 有 HeyGen 登录页面时可以使用网页。需要 API 时，让用户运行 `scripts/configure_heygen_key.ps1`；粘贴在聊天中的密钥不会自动进入运行环境。
5. `voice.audio_path` 有值时，上传前必须自动检测并转换音频：

```powershell
python scripts/workflow.py prepare-audio 项目目录
```

6. 只通过统一入口检查身份并查询人物、音色：

```powershell
python scripts/workflow.py auth 项目目录
python scripts/workflow.py avatars 项目目录
python scripts/workflow.py voices 项目目录
```

7. 使用服务商 TTS 时按固定顺序运行。`tts` 自动拒绝乱码和异常时长；`create` 立即保存任务 ID，并根据请求指纹防止重复提交和重复扣费；`poll` 从 `state.json` 恢复轮询。

```powershell
python scripts/workflow.py tts 项目目录
python scripts/workflow.py create 项目目录
python scripts/workflow.py poll 项目目录
```

8. 下载完成的透明人物视频，再使用 `video-use` 合成与剪辑。
9. 使用项目确认值执行机械质检：

```powershell
python scripts/check_video.py 成片 --require-audio --width 宽度 --height 高度 --expected-duration 秒数
```

## 状态与恢复

- `config.json` 是台词、人物、背景、音色、版式和授权的唯一数据源。
- `state.json` 是步骤、请求指纹、TTS 时长、任务 ID、任务状态和输出地址的唯一数据源。
- 中断后先运行 `python scripts/workflow.py status 项目目录`。相同请求指纹已有任务 ID 时禁止重新创建视频。
- 工作流采用原子方式写 JSON。除非处理明确的服务商兼容问题，不得手工修改 `state.json`。
- 服务商响应保存到 `项目目录/artifacts/`，密钥永不写入文件。

## 服务商与编码规则

- 选择或切换服务商、接口版本时读取 [服务商适配说明](references/provider-adapter.md)。
- 用户文字全程写入 UTF-8 JSON。禁止通过命令管道传输中文。
- 使用 `scripts/prepare_audio.py` 或 `workflow.py prepare-audio` 自动处理音频，不要求用户自行转换。
- 优先生成透明 WebM。确认 `alpha_mode=1`，强制使用 libvpx VP9 解码并转为 `rgba`；存在原生 Alpha 时禁止黑底抠像。

## 交付门槛

交付前必须通过机械检查，包括完整且合理的时长、必需音轨、准确分辨率、画幅和按需检查透明通道。

每次固定抽查五个画面：首帧、25%、50%、75% 和尾帧。检查人物边缘、头发、眼镜、手指、浅色衣物、知识板遮挡、中文显示、切换时机和音画同步。失败后必须修改、重渲染并重新执行机械与画面检查。禁止把占位视频、截断视频或检查失败的结果称为成片。
