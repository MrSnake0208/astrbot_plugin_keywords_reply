from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
from astrbot.api.message_components import *
import os
import json
import re
import aiohttp
import hashlib

from .modules.command_triggered import CommandTriggeredModule
from .modules.auto_detect import AutoDetectModule

@register("astrbot_plugin_keywords_reply", "Foolllll", "支持图片回复、正则表达式和群聊过滤的关键词回复插件。", "v0.0.1", "https://github.com/Foolllll-J/astrbot_plugin_keywords_reply")
class KeywordsReplyPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_keywords_reply")
        self.image_dir = os.path.join(self.data_dir, "images")
        self.data_file = os.path.join(self.data_dir, "keywords.json")
        
        os.makedirs(self.image_dir, exist_ok=True)
        
        self.data = self._load_data()
        self.cmd_module = CommandTriggeredModule(self)
        self.detect_module = AutoDetectModule(self)
        
    def _load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载关键词数据失败: {e}")
        return {"command_triggered": [], "auto_detect": []}

    def _save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存关键词数据失败: {e}")

    async def _download_image(self, url: str) -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        filename = hashlib.md5(content).hexdigest() + ".jpg"
                        path = os.path.join(self.image_dir, filename)
                        with open(path, "wb") as f:
                            f.write(content)
                        return path
        except Exception as e:
            logger.error(f"下载图片失败: {e}")
        return None

    def _is_admin(self, event: AstrMessageEvent):
        if event.is_admin():
            return True
        sender_id = event.get_sender_id()
        whitelist = self.config.get("whitelist", [])
        return sender_id in whitelist

    def _parse_message_to_entry(self, components):
        text_parts = []
        images = []
        for comp in components:
            if isinstance(comp, Plain):
                text_parts.append(comp.text)
            elif isinstance(comp, Image):
                images.append({"url": comp.url, "file": comp.file, "path": comp.path})
        
        entry = {
            "text": "".join(text_parts).strip(),
            "images": images
        }
        return entry, len(images) > 0

    async def _process_entry_images(self, entry):
        processed_images = []
        for item in entry.get("images", []):
            url = item.get("url")
            path = item.get("path")
            # 如果是本地路径且在我们的图片目录下，只保留文件名
            if path and os.path.exists(path) and self.image_dir in path:
                processed_images.append({"path": os.path.basename(path)})
            elif url:
                local_path = await self._download_image(url)
                if local_path:
                    processed_images.append({"path": os.path.basename(local_path)})
                else:
                    processed_images.append(item)
            else:
                processed_images.append(item)
        
        entry["images"] = processed_images
        return entry

    def _get_reply_result(self, event: AstrMessageEvent, entry: dict):
        """构建回复结果。不支持图文混排，采用先文本后图片的顺序。"""
        try:
            chain = []
            
            # 1. 先添加文本
            if entry.get("text"):
                chain.append(Plain(entry["text"]))
            
            # 2. 后添加图片列表
            for img in entry.get("images", []):
                path = img.get("path")
                if path:
                    full_path = os.path.join(self.image_dir, path)
                    if os.path.exists(full_path):
                        chain.append(Image(file=full_path))
                    else:
                        logger.warning(f"图片文件不存在: {full_path}")
                elif img.get("url"):
                    chain.append(Image(url=img["url"]))

            if not chain:
                logger.warning(f"回复内容为空。Entry: {entry}")
                return None

            return MessageEventResult(chain=chain)

        except Exception as e:
            logger.error(f"构建回复结果失败: {e}", exc_info=True)
            return None

    def _is_safe_regex(self, pattern: str) -> bool:
        """正则表达式安全检查，防止 ReDoS"""
        dangerous_patterns = [
            r'\(\?\:',
            r'\(\?\!',
            r'\(\?\<',
            r'\*\+',
            r'\+\*',
            r'\*\*',
            r'\+\+',
            r'\((?:[^()]*[+*{][^()]*)\)\s*\+',
            r'\{[^{}]*\}[^{}]*\{[^{}]*\}',
        ]
        
        if len(pattern) > 100:
            return False
            
        for dangerous in dangerous_patterns:
            if re.search(dangerous, pattern):
                return False
                
        return True

    # 关键词指令
    @filter.command("添加关键词")
    async def add_keyword_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.add_item(event):
            yield res

    @filter.command("编辑关键词")
    async def edit_keyword_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.edit_item(event):
            yield res

    @filter.command("删除关键词")
    async def del_keyword_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.del_items(event):
            yield res

    @filter.command("启用关键词")
    async def enable_keyword_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.toggle_groups(event, True):
            yield res

    @filter.command("禁用关键词")
    async def disable_keyword_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.toggle_groups(event, False):
            yield res

    @filter.command("查看所有关键词")
    async def list_keywords_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.list_items(event):
            yield res

    @filter.command("删除关键词词条")
    async def del_keyword_entry_cmd(self, event: AstrMessageEvent):
        async for res in self.cmd_module.delete_entry(event):
            yield res

    # 检测词指令
    @filter.command("添加检测词")
    async def add_detect_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.add_item(event):
            yield res

    @filter.command("编辑检测词")
    async def edit_detect_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.edit_item(event):
            yield res

    @filter.command("删除检测词")
    async def del_detect_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.del_items(event):
            yield res

    @filter.command("启用检测词")
    async def enable_detect_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.toggle_groups(event, True):
            yield res

    @filter.command("禁用检测词")
    async def disable_detect_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.toggle_groups(event, False):
            yield res

    @filter.command("查看所有检测词")
    async def list_detects_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.list_items(event):
            yield res

    @filter.command("删除检测词词条")
    async def del_detect_entry_cmd(self, event: AstrMessageEvent):
        async for res in self.detect_module.delete_entry(event):
            yield res

    # 通用管理指令
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        if not msg: return
        
        # 统一处理：管理指令跳过（由 @filter.command 处理）
        management_prefixes = ["/添加", "/编辑", "/删除", "/启用", "/禁用", "/查看", "添加", "编辑", "删除", "启用", "禁用", "查看"]
        if any(msg.startswith(p) for p in management_prefixes):
            return
            
        # 1. 检查 command_triggered
        res = await self.cmd_module.handle_message(event)
        if res:
            yield res
            return

        # 2. 检查 auto_detect
        res = await self.detect_module.handle_message(event)
        if res:
            yield res
            return
