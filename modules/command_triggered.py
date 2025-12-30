import re
import random
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain

class CommandTriggeredModule:
    def __init__(self, plugin):
        self.plugin = plugin
        self.data_key = "command_triggered"

    def _match_keyword(self, text, keyword_cfg):
        keyword = keyword_cfg["keyword"]
        is_regex = keyword_cfg.get("regex", False)
        case_sensitive = self.plugin.config.get("case_sensitive", False)
        
        flags = 0
        if not case_sensitive:
            flags = re.IGNORECASE
            
        if is_regex:
            try:
                return re.fullmatch(keyword, text, flags)
            except Exception as e:
                logger.error(f"正则表达式匹配错误 (关键词: {keyword}): {e}")
                return False
        else:
            if not case_sensitive:
                text = text.lower()
                keyword = keyword.lower()
            return text == keyword

    async def handle_message(self, event: AstrMessageEvent):
        # 使用 AstrBot 原生指令识别逻辑
        if not event.is_at_or_wake_command:
            return None
            
        # 此时 message_str 应该是去掉前缀后的内容，例如 "菜单" 或 "菜单 参数"
        msg_str = event.message_str.strip()
        if not msg_str:
            return None
            
        potential_cmd = msg_str.split()[0]
        group_id = event.get_group_id()
        
        for cfg in self.plugin.data[self.data_key]:
            if self._match_keyword(potential_cmd, cfg):
                if cfg.get("enabled_groups") and group_id not in cfg["enabled_groups"]:
                    continue
                
                logger.info(f"关键词触发: {potential_cmd} (来自: {event.get_sender_id()})")
                entry = random.choice(cfg["entries"])
                return self.plugin._get_reply_result(event, entry)
        return None

    async def add_item(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return

        # 移除指令名，获取参数部分
        full_text = event.message_str.strip()
        parts = full_text.split(None, 1)
        if len(parts) < 2:
            yield event.plain_result("格式错误。用法: /添加关键词 [-r] <关键词> <回复内容>")
            return
            
        args_text = parts[1].lstrip()
        
        is_regex = False
        if args_text.startswith("-r"):
            is_regex = True
            args_text = args_text[2:].lstrip()
            
        if not args_text:
            yield event.plain_result("格式错误。用法: /添加关键词 [-r] <关键词> <回复内容>")
            return

        # 提取关键词和回复内容，只拆分第一个空白字符（空格或换行）
        match = re.search(r'\s+', args_text)
        if match:
            keyword = args_text[:match.start()]
            remaining = args_text[match.end():]
        else:
            keyword = args_text
            remaining = ""

        if not keyword:
            yield event.plain_result("关键词不能为空。")
            return

        # 验证正则合法性
        if is_regex:
            if not self.plugin._is_safe_regex(keyword):
                yield event.plain_result("正则表达式存在安全风险，请简化后重试。")
                return
            try:
                re.compile(keyword)
            except Exception as e:
                yield event.plain_result(f"无效的正则表达式: {e}")
                return

        # 构建回复内容组件
        components = event.get_messages()
        reply_components = []
        
        # 第一个组件包含指令和关键词，我们需要提取出后面的回复文本
        first_comp = components[0]
        if isinstance(first_comp, Plain):
            text = first_comp.text
            # 回复内容在第一个组件中的起始位置
            if remaining:
                # 寻找关键词后的第一个 remaining，防止关键词和回复内容相同时找错位置
                k_idx = text.find(keyword)
                search_start = k_idx + len(keyword) if k_idx != -1 else 0
                r_idx = text.find(remaining, search_start)
                if r_idx != -1:
                    reply_components.append(Plain(text[r_idx:]))
                elif k_idx != -1:
                    # 如果 remaining 不在第一个组件（可能跨组件），则尝试获取 keyword 之后的所有内容
                    after_keyword = text[search_start:].lstrip()
                    if after_keyword:
                        reply_components.append(Plain(after_keyword))
        
        # 添加后续所有组件（如图片、表情等）
        reply_components.extend(components[1:])
        
        entry, has_image = self.plugin._parse_message_to_entry(reply_components)
        if not entry.get("text") and not entry.get("images"):
            yield event.plain_result("回复内容不能为空。")
            return

        words_limit = self.plugin.config.get("words_limit", 10)
        keyword_cfg = next((item for item in self.plugin.data[self.data_key] if item["keyword"] == keyword), None)
        
        if keyword_cfg:
            # 检查是否已有图文词条，或者新添加的是否为图文词条
            has_existing_image = any(e.get("images") for e in keyword_cfg["entries"])
            if has_image or has_existing_image:
                yield event.plain_result("包含图片的关键词只能有一个词条。")
                return
            
            if len(keyword_cfg["entries"]) >= words_limit:
                yield event.plain_result(f"词条数量已达上限 ({words_limit})。")
                return
            processed_entry = await self.plugin._process_entry_images(entry)
            keyword_cfg["entries"].append(processed_entry)
            keyword_cfg["regex"] = is_regex
        else:
            processed_entry = await self.plugin._process_entry_images(entry)
            keyword_cfg = {
                "keyword": keyword,
                "entries": [processed_entry],
                "regex": is_regex,
                "enabled_groups": []
            }
            self.plugin.data[self.data_key].append(keyword_cfg)

        self.plugin._save_data()
        logger.info(f"添加关键词: {keyword} (操作者: {event.get_sender_id()})")
        yield event.plain_result(f"成功添加关键词: {keyword}")

    async def edit_item(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        msg_parts = event.message_str.strip().split()
        # 格式可能为:
        # 1. /编辑关键词 序号 新关键词 -> ['/编辑关键词', '序号', '新关键词']
        # 2. /编辑关键词 -r 序号 新关键词 -> ['/编辑关键词', '-r', '序号', '新关键词']

        if len(msg_parts) < 3:
            yield event.plain_result("格式错误。用法: /编辑关键词 [-r] <序号> <新关键词>")
            return

        is_regex = False
        idx_str = ""
        new_keyword = ""

        if msg_parts[1] == "-r":
            is_regex = True
            if len(msg_parts) < 4:
                yield event.plain_result("格式错误。用法: /编辑关键词 -r <序号> <新关键词>")
                return
            idx_str = msg_parts[2]
            new_keyword = msg_parts[3]
        else:
            idx_str = msg_parts[1]
            new_keyword = msg_parts[2]

        try:
            idx = int(idx_str) - 1
        except ValueError:
            yield event.plain_result("序号必须是数字。")
            return
        
        if is_regex:
            try:
                re.compile(new_keyword)
            except Exception as e:
                yield event.plain_result(f"无效的正则表达式: {e}")
                return
        
        if 0 <= idx < len(self.plugin.data[self.data_key]):
            old_keyword = self.plugin.data[self.data_key][idx]["keyword"]
            self.plugin.data[self.data_key][idx]["keyword"] = new_keyword
            self.plugin.data[self.data_key][idx]["regex"] = is_regex
            self.plugin._save_data()
            logger.info(f"编辑关键词: {old_keyword} -> {new_keyword} (操作者: {event.get_sender_id()})")
            yield event.plain_result(f"已更新序号 {idx+1} 的关键词为: {new_keyword}")
        else:
            yield event.plain_result("序号无效。")

    async def del_items(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        parts = event.message_str.strip().split()
        if len(parts) < 2:
            yield event.plain_result("格式错误。用法: /删除关键词 <序号1> <序号2> ...")
            return
            
        try:
            indices = [int(a) - 1 for a in parts[1:]]
            indices.sort(reverse=True)
            deleted_keywords = []
            for idx in indices:
                if 0 <= idx < len(self.plugin.data[self.data_key]):
                    keyword = self.plugin.data[self.data_key].pop(idx)["keyword"]
                    deleted_keywords.append(keyword)
            if deleted_keywords:
                self.plugin._save_data()
                logger.info(f"删除关键词: {', '.join(deleted_keywords)} (操作者: {event.get_sender_id()})")
                yield event.plain_result(f"已删除 {len(deleted_keywords)} 个关键词。")
            else:
                yield event.plain_result("未找到有效的序号。")
        except ValueError:
            yield event.plain_result("序号必须是数字。")
        except Exception as e:
            logger.error(f"删除关键词异常: {e}")
            yield event.plain_result(f"操作失败: {e}")

    async def toggle_groups(self, event: AstrMessageEvent, enable: bool):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        parts = event.message_str.strip().split()
        if len(parts) < 2:
            cmd_name = "启用" if enable else "禁用"
            yield event.plain_result(f"格式错误。用法: /{cmd_name}关键词 <序号> [群号1] [群号2] ...")
            return
            
        try:
            idx = int(parts[1]) - 1
            group_ids = parts[2:]
            
            if 0 <= idx < len(self.plugin.data[self.data_key]):
                cfg = self.plugin.data[self.data_key][idx]
                if "enabled_groups" not in cfg: cfg["enabled_groups"] = []
                
                if not group_ids:
                    # 如果没传群号，启用则清空限制（全群），禁用则不做操作或提示
                    if enable:
                        cfg["enabled_groups"] = []
                    else:
                        yield event.plain_result("请指定要禁用的群号。")
                        return
                else:
                    for gid in group_ids:
                        if enable:
                            if gid not in cfg["enabled_groups"]:
                                cfg["enabled_groups"].append(gid)
                        else:
                            if gid in cfg["enabled_groups"]:
                                cfg["enabled_groups"].remove(gid)
                
                self.plugin._save_data()
                status = "已启用" if enable else "已禁用"
                groups_str = ", ".join(group_ids) if group_ids else "所有群聊 (清除限制)"
                logger.info(f"修改关键词群聊限制: {cfg['keyword']} -> {status} {groups_str} (操作者: {event.get_sender_id()})")
                yield event.plain_result(f"关键词 '{cfg['keyword']}' {status} 群聊: {groups_str}")
            else:
                yield event.plain_result("序号无效。")
        except ValueError:
            yield event.plain_result("序号必须是数字。")

    async def list_items(self, event):
        res = "关键词列表 (指令触发):\n"
        if not self.plugin.data[self.data_key]:
            res += "无\n"
        else:
            for i, cfg in enumerate(self.plugin.data[self.data_key], 1):
                regex_str = " [正则]" if cfg.get("regex", False) else ""
                groups_str = f" [群:{','.join(cfg['enabled_groups'])}]" if cfg.get("enabled_groups") else " [全群]"
                res += f"{i}. {cfg['keyword']}{regex_str}{groups_str}\n"
                for j, entry in enumerate(cfg["entries"], 1):
                    imgs_str = "[图片]" * len(entry.get("images", []))
                    content = f"{entry.get('text', '')}{imgs_str}"
                    res += f"  └─ {j}. {content[:50]}{'...' if len(content) > 50 else ''}\n"
        yield event.plain_result(res.strip())

    async def delete_entry(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            yield event.plain_result("格式错误。用法: /删除关键词词条 <关键词序号> <词条序号>")
            return
            
        try:
            idx = int(parts[1]) - 1
            entry_idx = int(parts[2]) - 1
            
            if 0 <= idx < len(self.plugin.data[self.data_key]):
                keyword_cfg = self.plugin.data[self.data_key][idx]
                if 0 <= entry_idx < len(keyword_cfg["entries"]):
                    keyword_cfg["entries"].pop(entry_idx)
                    keyword = keyword_cfg["keyword"]
                    if not keyword_cfg["entries"]:
                        self.plugin.data[self.data_key].pop(idx)
                        logger.info(f"关键词 {keyword} 已无词条，自动删除关键词。")
                    
                    self.plugin._save_data()
                    logger.info(f"删除关键词词条: {keyword} 序号 {idx+1}, 词条序号 {entry_idx+1} (操作者: {event.get_sender_id()})")
                    yield event.plain_result(f"已删除关键词 '{keyword}' 的第 {entry_idx+1} 个词条。")
                else:
                    yield event.plain_result("词条序号无效。")
            else:
                yield event.plain_result("关键词序号无效。")
        except ValueError:
            yield event.plain_result("序号必须是数字。")
