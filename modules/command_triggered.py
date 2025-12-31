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
        if not event.is_at_or_wake_command:
            return None
            
        msg_str = event.message_str.strip()
        if not msg_str:
            return None
            
        potential_cmd = msg_str.split()[0]
        group_id = event.get_group_id()
        
        for cfg in self.plugin.data[self.data_key]:
            if self._match_keyword(potential_cmd, cfg):
                if not cfg.get("enabled", True):
                    continue
                
                mode = cfg.get("mode", "whitelist")
                groups = cfg.get("groups", [])
                
                if group_id:
                    if mode == "whitelist":
                        if group_id not in groups:
                            continue
                    else: # blacklist
                        if group_id in groups:
                            continue
                
                logger.info(f"关键词触发: {potential_cmd} (来自: {event.get_sender_id()})")
                if not cfg["entries"]:
                    return None
                entry = random.choice(cfg["entries"])
                return self.plugin._get_reply_result(event, entry)
        return None

    def _find_indices(self, param: str) -> list[int]:
        data = self.plugin.data[self.data_key]
        if not data:
            return []

        try:
            indices = []
            parts = param.split(',')
            for part in parts:
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    indices.extend(range(start-1, end))
                else:
                    indices.append(int(part)-1)
            
            valid_indices = [i for i in indices if 0 <= i < len(data)]
            if valid_indices:
                return valid_indices
        except ValueError:
            pass

        indices = []
        for i, cfg in enumerate(data):
            if cfg['keyword'] == param:
                indices.append(i)
        
        return indices

    async def add_item(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return

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

        if is_regex:
            if not self.plugin._is_safe_regex(keyword):
                yield event.plain_result("正则表达式存在安全风险，请简化后重试。")
                return
            try:
                re.compile(keyword)
            except Exception as e:
                yield event.plain_result(f"无效的正则表达式: {e}")
                return

        components = event.get_messages()
        reply_components = []
        
        first_comp = components[0]
        if isinstance(first_comp, Plain):
            text = first_comp.text
            if remaining:
                k_idx = text.find(keyword)
                search_start = k_idx + len(keyword) if k_idx != -1 else 0
                r_idx = text.find(remaining, search_start)
                if r_idx != -1:
                    reply_components.append(Plain(text[r_idx:]))
                elif k_idx != -1:
                    after_keyword = text[search_start:].lstrip()
                    if after_keyword:
                        reply_components.append(Plain(after_keyword))
        
        reply_components.extend(components[1:])
        
        entry, has_image = self.plugin._parse_message_to_entry(reply_components)
        if not entry.get("text") and not entry.get("images"):
            yield event.plain_result("回复内容不能为空。")
            return

        words_limit = self.plugin.config.get("words_limit", 10)
        keyword_cfg = next((item for item in self.plugin.data[self.data_key] if item["keyword"] == keyword), None)
        
        current_group_id = event.get_group_id()
        is_group = event.get_platform_name() != "private"
        
        if keyword_cfg:
            if len(keyword_cfg["entries"]) >= words_limit:
                yield event.plain_result(f"回复数量已达上限 ({words_limit})。")
                return
            processed_entry = await self.plugin._process_entry_images(entry)
            keyword_cfg["entries"].append(processed_entry)
            keyword_cfg["regex"] = is_regex
            status_msg = f"已为现有关键词添加新回复（当前共有 {len(keyword_cfg['entries'])} 个回复）。"
        else:
            processed_entry = await self.plugin._process_entry_images(entry)
            
            if is_group and current_group_id:
                enabled = True
                mode = "whitelist"
                groups = [current_group_id]
                status_msg = f"已成功添加关键词，并在当前群聊启用。"
            else:
                enabled = False
                mode = "whitelist"
                groups = []
                status_msg = "已成功添加关键词。由于在非群聊环境创建，已默认全局禁用。"
            
            keyword_cfg = {
                "keyword": keyword,
                "entries": [processed_entry],
                "regex": is_regex,
                "enabled": enabled,
                "mode": mode,
                "groups": groups
            }
            self.plugin.data[self.data_key].append(keyword_cfg)

        self.plugin._save_data()
        logger.info(f"添加关键词: {keyword} (操作者: {event.get_sender_id()})")
        
        yield event.plain_result(f"成功操作关键词: {keyword}\n{status_msg}")

    async def edit_item(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("只有管理员可以执行此操作。")
            return
            
        msg_parts = event.message_str.strip().split()
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
            yield event.plain_result(f"关键词 '{old_keyword}' 已修改为 '{new_keyword}'。")
        else:
            yield event.plain_result("序号无效。")

    async def del_items(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        parts = event.message_str.strip().split(None, 1)
        if len(parts) < 2:
            yield event.plain_result("格式错误。用法: /删除关键词 <序号或关键词内容>")
            return
            
        param = parts[1]
        indices = self._find_indices(param)
        
        if not indices:
            yield event.plain_result(f"未找到匹配 '{param}' 的关键词。")
            return

        try:
            indices.sort(reverse=True)
            deleted_keywords = []
            for idx in indices:
                cfg = self.plugin.data[self.data_key].pop(idx)
                deleted_keywords.append(cfg['keyword'])
            
            self.plugin._save_data()
            logger.info(f"删除关键词: {', '.join(deleted_keywords)} (操作者: {event.get_sender_id()})")
            yield event.plain_result(f"关键词 '{', '.join(deleted_keywords)}' 已删除。")
        except Exception as e:
            logger.error(f"删除关键词异常: {e}")
            yield event.plain_result(f"操作失败: {e}")

    async def toggle_groups(self, event: AstrMessageEvent, enable: bool):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        parts = event.message_str.strip().split()
        cmd_name = "启用" if enable else "禁用"
        if len(parts) < 2:
            yield event.plain_result(f"格式错误。用法: /{cmd_name}关键词 <序号或关键词内容> [群号1] [群号2] ...")
            return
            
        param = parts[1]
        indices = self._find_indices(param)
        
        if not indices:
            yield event.plain_result(f"未找到匹配 '{param}' 的关键词。")
            return

        args = parts[2:]
        for idx in indices:
            cfg = self.plugin.data[self.data_key][idx]
            
            current_group_id = event.get_group_id()
            is_group = event.get_platform_name() != "private"

            if enable:
                if not args:
                    if is_group and current_group_id:
                        if cfg["mode"] == "blacklist":
                            if current_group_id in cfg["groups"]:
                                cfg["groups"].remove(current_group_id)
                        else:
                            if current_group_id not in cfg["groups"]:
                                cfg["groups"].append(current_group_id)
                        cfg["enabled"] = True
                        groups_str = f"当前群聊 ({current_group_id})"
                    else:
                        yield event.plain_result("当前不在群聊中，请指定群号或使用'全局'参数。")
                        return
                elif args[0] == "全局":
                    cfg["enabled"] = True
                    cfg["mode"] = "blacklist"
                    cfg["groups"] = []
                    groups_str = "全局 (所有群聊)"
                else:
                    if cfg["mode"] != "whitelist":
                        cfg["mode"] = "whitelist"
                        cfg["groups"] = []
                    
                    for gid in args:
                        if not gid.isdigit():
                            yield event.plain_result(f"群号格式错误: {gid}")
                            return
                        if gid not in cfg["groups"]:
                            cfg["groups"].append(gid)
                    groups_str = ", ".join(args)
                    cfg["enabled"] = True
            else: # 禁用
                if not args:
                    if is_group and current_group_id:
                        if cfg["mode"] != "blacklist":
                            cfg["mode"] = "blacklist"
                            cfg["groups"] = []
                        if current_group_id not in cfg["groups"]:
                            cfg["groups"].append(current_group_id)
                        groups_str = f"当前群聊 ({current_group_id})"
                        cfg["enabled"] = True
                    else:
                        cfg["enabled"] = False
                        groups_str = "全局"
                elif args[0] == "全局":
                    cfg["enabled"] = False
                    groups_str = "全局"
                else:
                    if cfg["mode"] != "blacklist":
                        cfg["mode"] = "blacklist"
                        cfg["groups"] = []
                    
                    for gid in args:
                        if not gid.isdigit():
                            yield event.plain_result(f"群号格式错误: {gid}")
                            return
                        if gid not in cfg["groups"]:
                            cfg["groups"].append(gid)
                    groups_str = ", ".join(args)
                    cfg["enabled"] = True

            self.plugin._save_data()
            logger.info(f"修改关键词群聊限制: {cfg['keyword']} -> {cmd_name} {groups_str} (操作者: {event.get_sender_id()})")
            yield event.plain_result(f"关键词 '{cfg['keyword']}' {cmd_name} 群聊: {groups_str}")

    async def list_items(self, event):
        res = "关键词列表:\n"
        if not self.plugin.data[self.data_key]:
            res += "无\n"
        else:
            for i, cfg in enumerate(self.plugin.data[self.data_key], 1):
                regex_str = " [正则]" if cfg.get("regex", False) else ""
                
                enabled = cfg.get("enabled", True)
                mode = cfg.get("mode", "whitelist")
                groups = cfg.get("groups", [])
                
                if not enabled:
                    groups_str = " [全局禁用]"
                else:
                    if mode == "blacklist":
                        if not groups:
                            groups_str = " [全局启用]"
                        else:
                            groups_str = f" [黑名单:{','.join(groups)}]"
                    else: # whitelist
                        if not groups:
                            groups_str = " [未启用]"
                        else:
                            groups_str = f" [白名单:{','.join(groups)}]"
                
                res += f"{i}. {cfg['keyword']}{regex_str}{groups_str}\n"
                for j, entry in enumerate(cfg["entries"], 1):
                    imgs_str = "[图片]" * len(entry.get("images", []))
                    content = f"{entry.get('text', '')}{imgs_str}"
                    res += f"  └─ {j}. {content[:50]}{'...' if len(content) > 50 else ''}\n"
        yield event.plain_result(res.strip())

    async def view_item(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: /查看关键词 <序号或关键词内容>")
            return
        
        if len(parts) >= 3:
            async for res in self.view_reply(event):
                yield res
            return
            
        param = parts[1]
        indices = self._find_indices(param)
        
        if not indices:
            yield event.plain_result(f"未找到匹配 '{param}' 的关键词。")
            return
            
        for idx in indices:
            cfg = self.plugin.data[self.data_key][idx]
            entries = cfg.get("entries", [])
            
            if len(entries) == 1:
                entry = entries[0]
                
                enabled = cfg.get("enabled", True)
                mode = cfg.get("mode", "whitelist")
                groups = cfg.get("groups", [])
                
                if not enabled:
                    groups_str = "全局禁用"
                else:
                    if mode == "blacklist":
                        groups_str = "全局启用" if not groups else f"黑名单模式 (禁用群: {', '.join(groups)})"
                    else:
                        groups_str = "未在任何群聊启用" if not groups else f"白名单模式 (允许群: {', '.join(groups)})"

                intro = f"【{idx+1}】 关键词: {cfg['keyword']}\n"
                intro += f"类型: {'正则匹配' if cfg.get('regex') else '精确匹配'}\n"
                intro += f"状态: {groups_str}\n"

                has_images = len(entry.get("images", [])) > 0
                if not has_images:
                    intro += "回复详情：\n"
                    intro += entry.get("text", "")
                    yield event.plain_result(intro)
                    continue

                intro += "回复详情："
                res_obj = self.plugin._get_reply_result(event, entry)
                if res_obj and res_obj.chain:
                    res_obj.chain.insert(0, Plain("\n"))
                    res_obj.chain.insert(0, Plain(intro))
                    yield res_obj
                else:
                    yield event.plain_result(intro + "(回复内容为空)")
            else:
                enabled = cfg.get("enabled", True)
                mode = cfg.get("mode", "whitelist")
                groups = cfg.get("groups", [])
                
                if not enabled:
                    groups_str = "全局禁用"
                else:
                    if mode == "blacklist":
                        groups_str = "全局启用" if not groups else f"黑名单模式 (禁用群: {', '.join(groups)})"
                    else:
                        groups_str = "未在任何群聊启用" if not groups else f"白名单模式 (允许群: {', '.join(groups)})"

                res = f"【{idx+1}】 关键词: {cfg['keyword']}\n"
                res += f"类型: {'正则匹配' if cfg.get('regex') else '精确匹配'}\n"
                res += f"状态: {groups_str}\n"
                res += f"回复数量: {len(entries)}\n"
                res += "回复列表：\n"
                
                for i, entry in enumerate(entries, 1):
                    text = entry.get("text", "").replace("\n", " ")
                    imgs_str = " [图片]" if entry.get("images") else ""
                    res += f"{i}. {text[:30]}{'...' if len(text) > 30 else ''}{imgs_str}\n"
                
                res += f"\n提示: 使用 /查看关键词回复 {idx+1} <回复序号> 查看完整内容"
                yield event.plain_result(res.strip())

    async def view_reply(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            yield event.plain_result("用法: /查看关键词回复 <关键词序号> <回复序号>")
            return
        
        try:
            idx = int(parts[1]) - 1
            reply_idx = int(parts[2]) - 1
            
            if 0 <= idx < len(self.plugin.data[self.data_key]):
                cfg = self.plugin.data[self.data_key][idx]
                if 0 <= reply_idx < len(cfg["entries"]):
                    entry = cfg["entries"][reply_idx]
                    intro = f"关键词 '{cfg['keyword']}' 的第 {reply_idx+1} 个回复：\n\n"
                    
                    has_images = len(entry.get("images", [])) > 0
                    if not has_images:
                        intro += entry.get("text", "")
                        yield event.plain_result(intro)
                        return

                    res_obj = self.plugin._get_reply_result(event, entry)
                    if res_obj and res_obj.chain:
                        res_obj.chain.insert(0, Plain(intro))
                        yield res_obj
                    else:
                        yield event.plain_result(intro + "(回复内容为空)")
                else:
                    yield event.plain_result("回复序号无效。")
            else:
                yield event.plain_result("关键词序号无效。")
        except ValueError:
            yield event.plain_result("序号必须是数字。")

    async def edit_reply(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return

        # 格式: /编辑关键词回复 [关键词ID] [回复序号] [新内容]
        # 或: /编辑关键词回复 [关键词ID] [新内容] (当仅有一个回复时)
        full_text = event.message_str.strip()
        parts = full_text.split(None, 3) # 最多拆分4部分: 指令, ID, (序号), 内容
        
        if len(parts) < 3:
            yield event.plain_result("格式错误。用法:\n/编辑关键词回复 <关键词序号> <回复序号> <新内容>\n/编辑关键词回复 <关键词序号> <新内容> (单回复时)")
            return

        try:
            kw_idx = int(parts[1]) - 1
            if kw_idx < 0 or kw_idx >= len(self.plugin.data[self.data_key]):
                yield event.plain_result("关键词序号无效。")
                return
            
            cfg = self.plugin.data[self.data_key][kw_idx]
            entries = cfg["entries"]
            
            # 判断是标准格式还是简化格式
            # 尝试将 parts[2] 解析为回复序号
            try:
                reply_idx = int(parts[2]) - 1
                if 0 <= reply_idx < len(entries):
                    # 是有效的回复序号，内容在 parts[3]
                    if len(parts) < 4:
                        yield event.plain_result("请输入新的回复内容。")
                        return
                    new_content_raw = parts[3]
                else:
                    # 不是有效的回复序号，尝试简化格式
                    if len(entries) == 1:
                        reply_idx = 0
                        new_content_raw = full_text.split(None, 2)[2]
                    else:
                        yield event.plain_result(f"该关键词有 {len(entries)} 个回复，请指定要编辑的序号。")
                        return
            except ValueError:
                # parts[2] 不是数字，尝试简化格式
                if len(entries) == 1:
                    reply_idx = 0
                    new_content_raw = full_text.split(None, 2)[2]
                else:
                    yield event.plain_result(f"该关键词有 {len(entries)} 个回复，请指定要编辑的序号。")
                    return

            # 解析新内容 (包含图片处理)
            components = event.get_messages()
            # 需要从 components 中提取出新内容部分
            # 这是一个比较复杂的逻辑，因为要跳过指令、ID、序号等 Plain 文本
            # 简化处理：重新解析所有组件，但过滤掉前面的 Plain 文本
            
            new_reply_components = []
            found_content = False
            
            # 找到 new_content_raw 在消息链中的位置
            # 实际上更简单的方法是：直接用 parse_message_to_entry，但需要先剔除前面的参数
            # 我们复用 add_item 的逻辑
            
            # 这里的处理逻辑需要非常小心
            # 暂时采用简单方案：如果新内容只有文字，直接更新；如果有图片，则使用当前消息的所有组件（过滤掉指令头）
            
            # 重新获取组件并剔除前面的指令部分
            # 我们找第一个 Plain 组件，并替换它的 text
            processed_comps = []
            first_plain_found = False
            for comp in components:
                if isinstance(comp, Plain) and not first_plain_found:
                    # 找到第一个文字组件，它包含了指令
                    # 我们将其替换为提取出的 new_content_raw
                    processed_comps.append(Plain(new_content_raw))
                    first_plain_found = True
                elif not isinstance(comp, Plain) or first_plain_found:
                    # 后续组件（图片等）或第一个文字组件之后的文字
                    processed_comps.append(comp)
            
            entry, has_image = self.plugin._parse_message_to_entry(processed_comps)
            if not entry.get("text") and not entry.get("images"):
                 yield event.plain_result("回复内容不能为空。")
                 return
            
            processed_entry = await self.plugin._process_entry_images(entry)
            cfg["entries"][reply_idx] = processed_entry
            
            self.plugin._save_data()
            logger.info(f"编辑关键词回复: {cfg['keyword']} (序号 {reply_idx+1}) (操作者: {event.get_sender_id()})")
            yield event.plain_result(f"已更新关键词 '{cfg['keyword']}' 的第 {reply_idx+1} 个回复。")

        except Exception as e:
            logger.error(f"编辑回复异常: {e}", exc_info=True)
            yield event.plain_result(f"操作失败: {e}")

    async def delete_reply(self, event: AstrMessageEvent):
        if not self.plugin._is_admin(event):
            yield event.plain_result("权限不足。")
            return
            
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            yield event.plain_result("格式错误。用法: /删除关键词回复 <关键词序号> <回复序号>")
            return
            
        try:
            idx = int(parts[1]) - 1
            reply_idx = int(parts[2]) - 1
            
            if 0 <= idx < len(self.plugin.data[self.data_key]):
                keyword_cfg = self.plugin.data[self.data_key][idx]
                if 0 <= reply_idx < len(keyword_cfg["entries"]):
                    keyword_cfg["entries"].pop(reply_idx)
                    keyword = keyword_cfg["keyword"]
                    
                    self.plugin._save_data()
                    logger.info(f"删除关键词回复: {keyword} 序号 {idx+1}, 回复序号 {reply_idx+1} (操作者: {event.get_sender_id()})")
                    yield event.plain_result(f"已删除关键词 '{keyword}' 的第 {reply_idx+1} 个回复。")
                else:
                    yield event.plain_result("回复序号无效。")
            else:
                yield event.plain_result("关键词序号无效。")
        except ValueError:
            yield event.plain_result("序号必须是数字。")
