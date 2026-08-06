# 数字人服务商适配说明

剪辑与合成流程保持服务商无关。任何服务商适配层都必须提供：

- API 身份和额度检查
- 素材库人物查询，或上传人物素材
- 音色查询、授权克隆音色、上传音频或文字转语音
- 使用已验证音频生成数字人视频
- 异步任务状态查询和媒体下载地址
- 清楚说明透明背景或背景移除能力

## HeyGen 参考流程

使用 HeyGen 当前官方 API。默认 v3 接口表保存在 `config.json`，接口版本变化时修改配置，不重新编写请求代码。

`scripts/heygen_client.py` 统一负责认证头、UTF-8 JSON、安全的 GET 重试、超时、轮询和密钥读取。`scripts/workflow.py` 统一负责请求指纹、状态检查点、防重复提交和响应存档。禁止用临时请求替换这些入口。

1. `GET /v3/users/me` 检查身份。
2. `GET /v3/avatars/looks` 查询人物 Look ID。分页时，把响应中的 `next_token` 作为下一次请求的 `token` 参数。
3. `GET /v3/voices/{voice_id}` 或音色列表接口确认音色。
4. `POST /v3/voices/speech` 以 UTF-8 生成语音，并检查时长和文字时间戳。
5. `POST /v3/videos` 使用 `type: avatar` 和已经验证的 `audio_url` 生成数字人。
6. 轮询 `GET /v3/videos/{video_id}` 直至完成。

需要后期精确控制时，请求 `output_format: webm`。下载后确认 `alpha_mode=1`，并使用 libvpx VP9 解码。只有透明输出不可用时，才使用可控纯色背景的 MP4 作为备用方案。

不得假设聊天中的 API Key 已进入运行环境。可以使用已有登录状态的服务商网页；否则运行 `scripts/configure_heygen_key.ps1`。`heygen_client.py` 会从当前进程或 Windows 用户环境读取且不打印。严禁把密钥写入 `config.json`、`state.json`、日志、响应存档、Git 或交付物。

上传用户音频前，必须用 FFprobe 检测格式、编码、采样率、声道和时长。提交给 HeyGen 的音频必须是 WAV；其他格式应先在本地用 FFmpeg 转成 PCM 16-bit WAV。服务商文档没有其他要求时默认使用 48 kHz 单声道，并在上传前重新检查转换后的文件。

## 替换其他服务商

把新服务商映射到前述六项能力，并接入同一套工作流和状态契约，禁止另起一套自由流程。无论更换哪家服务商，都必须保留 UTF-8 预检、TTS 时长拒绝、请求指纹、原子状态、Alpha 检查和 `video-use` 质量控制。
