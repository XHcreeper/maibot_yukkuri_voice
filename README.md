# 油库里语音（YukkuriVoice）
**让你的麦麦能发送油库里语音**
~~可以作为TTS使用~~ 在不会配置TTS插件的情况下可选 ~~（虽然这个插件可能更难配置）~~
本插件中的语音合成功能主要使用了「**株式会社アクエスト**」的**AquesTalk.dll**实现

## 功能概览  
- 使用 AquesTalk-python 库搭配 `AquesTalk.dll` 进行语音合成
- 将原消息文本转为拼音再映射为假名
- 支持更换音色与调整语速
- 由 planner 判读是否使用为语音

## 运行周期
1. planner 调用 `yukkuri_voice` 工具标记当前聊天，并返回工具结果，提示下一条消息将被转换
2. planner 调用 `reply` 工具生成回复
3. 消息入站时 `hook 检测到标记则拦截原消息并删除标记
4. 将原消息文本转换为假名
5. 使用 AquesTalk-python 库相关函数生成 wave 类型音频文件
6. 将生成结果转码为 silk 类型音频文件
7. 将转码结果通过 API 作为语音类型消息发送出站
8. （可选）为原消息文本添加格式并补发

## 环境要求
**目前仅支持 Windows 环境（或能加载dll文件的环境）**

## 使用指南
1. 前往[「株式会社アクエスト」官网下载页](https://www.a-quest.com/download.html)获取 `AquesTalk1` 对应自己系统架构与特定音色的 `AquesTalk.dll` 文件
2. 调整配置文件中的 `aquestalk_dll_path` 配置项为你的 `AquesTalk.dll` 的位置
3. 应该能用了

## 其他
- 感谢[zh-yukkuri.js](https://github.com/Love-Kogasa/zh-yukkuri.js)项目提供的参考
- 此项目是开发者的第一个项目，若写得不好可以提 issue ，请见谅awa