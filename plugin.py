import aquestalk
import base64
import io
import os
import pysilk
from maibot_sdk import MaiBotPlugin, PluginConfigBase, API, Command, Field, HookHandler, Tool
from maibot_sdk.types import HookMode
from .converter import Converter

class PluginSection(PluginConfigBase):
    """插件基础配置"""
    __ui_label__ = "基础设置"
    __ui_order__ = 0

    enabled: bool = Field(
        default=True,
        description="是否启用插件",
        json_schema_extra={"label": "启用插件"}
        )
    config_version: str = Field(
        default="1.3.0",
        description="配置版本",
        json_schema_extra={"label": "配置版本", "disabled": True}
        )

class VoiceSection(PluginConfigBase):
    """声音合成设置"""
    __ui_label__ = "声音合成设置"
    __ui_order__ = 1

    aquestalk_dll_path: str = Field(
        default="voices\\f1\\AquesTalk.dll",
        description="使用的AquesTalk.dll的相对路径",
        json_schema_extra={"label": "AquesTalk.dll", "hint": "使用的AquesTalk.dll的相对路径"}
        )
    mapping_path: str = Field(
        default="mapping.json",
        description="拼音转假名映射字典文件的相对路径",
        json_schema_extra={"label": "拼音转假名映射字典文件", "hint": "拼音转假名映射字典文件的相对路径"}
        )
    voice_speed: int = Field(
        default=100,
        ge=50,
        le=300,
        description="语速（%），取50-300之间整数值（若无其他需求保持默认100即可）",
        json_schema_extra={
            "label": "语速",
            "hint": "语速（%），取50-300之间整数值（若无其他需求保持默认100即可）",
            "x-widget": "slider",
            "min": 50,
            "max": 300,
            "step": 1
            }
        )

class MessageSection(PluginConfigBase):
    """消息发送设置"""
    __ui_label__ = "消息发送设置"
    __ui_order__ = 2

    enable_send_original_message: bool = Field(
        default=True,
        description="是否启用发送语音消息后补充发送原消息",
        json_schema_extra={"label": "发送原消息", "hint": "发送语音消息后补充发送原消息"}
        )
    original_message_format: str = Field(
        default="消息原文：{original_text}",
        description="补充发送原消息时的额外格式，需启用 发送语音消息后补充发送原消息 ，{original_text} 为原消息文本",
        json_schema_extra={"label": "格式","hint": "补充发送原消息时的额外格式，需启用 发送语音消息后补充发送原消息 ，{original_text} 为原消息文本"}
        )

class YukkuriVoicePluginConfig(PluginConfigBase):
    """插件完整配置"""
    plugin: PluginSection = Field(default_factory=PluginSection)
    voice: VoiceSection = Field(default_factory=VoiceSection)
    Message: MessageSection = Field(default_factory=MessageSection)

class YukkuriVoicePlugin(MaiBotPlugin):
    config_model = YukkuriVoicePluginConfig

    def __init__(self):
        super().__init__()
        self._yukkuri_pending: dict[str, bool] = {}
        self.aq = None
        self.converter = None
        self.plugin_dir = ""
        self.runtime_dir = ""

    async def on_load(self) -> None:
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.runtime_dir = self.ctx.paths.runtime_dir
        try:
            self.aq = aquestalk.load_from_path(os.path.join(self.plugin_dir, self.config.voice.aquestalk_dll_path), "f1", check_voice_type=True)
        except Exception:
            self.ctx.logger.error("Yukkuri语音在加载AquesTalk.dll文件时失败，请查看插件README.md以获取缺失的AquesTalk.dll。")
        self.converter = Converter(os.path.join(self.plugin_dir, self.config.voice.mapping_path))


    async def on_unload(self) -> None:
        self.aq = None

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == "self":
            self.ctx.logger.info("插件配置已更新: version=%s" % version)

    @Tool(
        "yukkuri_voice",
        description="将下一条reply转为 东方Project Yukkuri 语音，也就是让你能发语音（低配版），适合用于搞怪情境。请在真正调用到此工具的同时调用reply工具（注意yukkuri_voice工具顺序需在前）！",
    )
    async def yukkuri_voice(self, stream_id: str="", **kwargs) -> None:
            if stream_id:
                self._yukkuri_pending[stream_id] = True # 聊天流隔离
                return {"message": "下一条回复将被转为东方Project Yukkuri 语音！"}
            else:
                return {"status":"failed"}
        
    # 联合HookHandler实现转化replyer的输出为语音
    @HookHandler(
            hook="send_service.before_send",
            name="yukkuri_voice_interceptor",
            description="若标记则拦截发送消息并转为 Yukkuri 语音",
            mode=HookMode.BLOCKING,
        )
    async def on_before_send(self, **kwargs) -> dict:
        message = kwargs.get("message", {})        
        session_id = message.get("session_id")

        if not self._yukkuri_pending.get(session_id):
            return {"action": "continue"}

        if self._yukkuri_pending.get(session_id):
            del self._yukkuri_pending[session_id]
            original_text = message.get("processed_plain_text", "").strip()
            if not original_text:
                return {"action": "continue"}
            else:
                # 合成并发送语音
                try:
                    await self._synthesize_and_send(original_text, session_id)
                    self.ctx.send.text(self.config.message.original_message_format.replace("{original_text}", original_text))
                    return {"action": "abort"}
                except Exception as e:
                    self.ctx.logger.error(f"合成并发送Yukkuri语音失败：{e}")
                    return {"action": "continue"}
        else:
            return {"action": "continue"}

    async def _synthesize_and_send(self, original_text: str, session_id: str):
        try:
            conversion_result = self.converter.str2kana(original_text)
            wav = self.aq.synthe(conversion_result, self.config.voice.voice_speed)
            
            slk_b64 = await self._wav_to_silk_base64(wav)
            
            await self.ctx.send.custom("voice", data=slk_b64, stream_id=session_id)
            
            self.ctx.logger.info(f"Yukkuri语音发送成功: {original_text}")
        except Exception as e:
            self.ctx.logger.error(f"Yukkuri语音合成/发送失败: {e}")

    # wave转码silk以适配qq语音格式要求
    async def _wav_to_silk_base64(self, wav) -> str:
        sample_rate = wav.getframerate()
        pcm_file = io.BytesIO(wav.readframes(wav.getnframes()))
        slk_b64 = None
        self._slk_file_path = os.path.join(self.runtime_dir, "slk_file.silk")
        with open(self._slk_file_path, "wb") as _silk_file:
            pysilk.encode(pcm_file, _silk_file, sample_rate, 24000)
        with open(self._slk_file_path, "rb") as _silk_file:
            slk_b64 = base64.b64encode(_silk_file.read()).decode()
        return slk_b64

def create_plugin():
    return YukkuriVoicePlugin()