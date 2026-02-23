"""WebUI 服务器实现"""
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timedelta

# HTML 模板
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 关键词回复管理</title>
    <style>
        :root {{
            --bg-primary: #0f0f23;
            --bg-secondary: #1a1a2e;
            --bg-tertiary: #16213e;
            --bg-card: rgba(255, 255, 255, 0.05);
            --text-primary: #eaeaea;
            --text-secondary: #a0a0a0;
            --accent-primary: #00d4aa;
            --accent-secondary: #0099cc;
            --accent-gradient: linear-gradient(135deg, #00d4aa 0%, #0099cc 100%);
            --border-color: rgba(255, 255, 255, 0.1);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            --glass: rgba(255, 255, 255, 0.05);
            --danger: #ff4757;
            --warning: #ffa502;
            --success: #2ed573;
        }}

        [data-theme="light"] {{
            --bg-primary: #f5f5f5;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f0f0f0;
            --bg-card: rgba(0, 0, 0, 0.02);
            --text-primary: #333333;
            --text-secondary: #666666;
            --accent-primary: #00a884;
            --accent-secondary: #0077b6;
            --accent-gradient: linear-gradient(135deg, #00a884 0%, #0077b6 100%);
            --border-color: rgba(0, 0, 0, 0.1);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            --glass: rgba(0, 0, 0, 0.02);
            --danger: #dc3545;
            --warning: #ffc107;
            --success: #28a745;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* 头部样式 */
        .header {{
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(10px);
        }}

        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.5rem;
            font-weight: 700;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .nav {{
            display: flex;
            gap: 1rem;
            align-items: center;
        }}

        .nav a {{
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}

        .nav a:hover, .nav a.active {{
            color: var(--accent-primary);
            background: var(--glass);
        }}

        /* 按钮样式 */
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.3s ease;
            text-decoration: none;
        }}

        .btn-primary {{
            background: var(--accent-gradient);
            color: white;
        }}

        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 212, 170, 0.3);
        }}

        .btn-secondary {{
            background: var(--glass);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }}

        .btn-secondary:hover {{
            background: var(--bg-tertiary);
        }}

        .btn-danger {{
            background: var(--danger);
            color: white;
        }}

        .btn-sm {{
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
        }}

        /* 卡片样式 */
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            backdrop-filter: blur(10px);
        }}

        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}

        /* 统计卡片 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-4px);
        }}

        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }}

        /* 表格样式 */
        .table-container {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        tr:hover {{
            background: var(--glass);
        }}

        /* 表单样式 */
        .form-group {{
            margin-bottom: 1.5rem;
        }}

        label {{
            display: block;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        input[type="text"],
        input[type="password"],
        input[type="number"],
        textarea,
        select {{
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 0.95rem;
            transition: border-color 0.3s ease;
        }}

        input:focus,
        textarea:focus,
        select:focus {{
            outline: none;
            border-color: var(--accent-primary);
        }}

        textarea {{
            min-height: 120px;
            resize: vertical;
        }}

        /* 登录页面 */
        .login-container {{
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}

        .login-box {{
            width: 100%;
            max-width: 400px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: var(--shadow);
        }}

        .login-title {{
            text-align: center;
            margin-bottom: 2rem;
        }}

        .login-title h1 {{
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
        }}

        .login-title p {{
            color: var(--text-secondary);
        }}

        /* 开关样式 */
        .switch {{
            position: relative;
            display: inline-block;
            width: 50px;
            height: 26px;
        }}

        .switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}

        .slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--bg-tertiary);
            transition: .4s;
            border-radius: 26px;
        }}

        .slider:before {{
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 4px;
            bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }}

        input:checked + .slider {{
            background: var(--accent-gradient);
        }}

        input:checked + .slider:before {{
            transform: translateX(24px);
        }}

        /* 主题切换 */
        .theme-toggle {{
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 1.25rem;
            padding: 0.5rem;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}

        .theme-toggle:hover {{
            background: var(--glass);
            color: var(--accent-primary);
        }}

        /* 标签 */
        .tag {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: var(--accent-gradient);
            color: white;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
        }}

        .tag-secondary {{
            background: var(--bg-tertiary);
            color: var(--text-secondary);
        }}

        /* 空状态 */
        .empty-state {{
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }}

        .empty-state-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }}

        /* 消息提示 */
        .alert {{
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}

        .alert-success {{
            background: rgba(46, 213, 115, 0.1);
            border: 1px solid var(--success);
            color: var(--success);
        }}

        .alert-error {{
            background: rgba(255, 71, 87, 0.1);
            border: 1px solid var(--danger);
            color: var(--danger);
        }}

        /* 模态框 */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }}

        .modal.active {{
            display: flex;
        }}

        .modal-content {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            width: 90%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
        }}

        .modal-header {{
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .modal-body {{
            padding: 1.5rem;
        }}

        .modal-footer {{
            padding: 1rem 1.5rem;
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: flex-end;
            gap: 0.5rem;
        }}

        .close-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
        }}

        /* 响应式 */
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                gap: 1rem;
            }}

            .nav {{
                flex-wrap: wrap;
                justify-content: center;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .stat-value {{
                font-size: 1.75rem;
            }}

            table {{
                font-size: 0.85rem;
            }}

            th, td {{
                padding: 0.75rem 0.5rem;
            }}
        }}

        /* 工具栏 */
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .search-box {{
            position: relative;
            flex: 1;
            min-width: 250px;
        }}

        .search-box input {{
            padding-left: 2.5rem;
        }}

        .search-box::before {{
            content: "🔍";
            position: absolute;
            left: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            opacity: 0.5;
        }}

        /* 分页 */
        .pagination {{
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 1.5rem;
        }}

        .page-btn {{
            padding: 0.5rem 1rem;
            background: var(--glass);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s ease;
        }}

        .page-btn:hover, .page-btn.active {{
            background: var(--accent-gradient);
            border-color: transparent;
        }}

        /* 操作按钮组 */
        .actions {{
            display: flex;
            gap: 0.5rem;
        }}

        /* 图片预览 */
        .image-preview {{
            max-width: 100px;
            max-height: 100px;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }}

        .image-preview:hover {{
            transform: scale(1.05);
        }}

        /* 群组标签 */
        .group-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .group-tag {{
            padding: 0.2rem 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 4px;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    {content}
    <script>
        // 主题切换
        function toggleTheme() {{
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }}

        // 加载保存的主题
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {{
            document.documentElement.setAttribute('data-theme', savedTheme);
        }}

        // 自动消失的消息
        setTimeout(() => {{
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {{
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.5s ease';
                setTimeout(() => alert.remove(), 500);
            }});
        }}, 5000);
    </script>
</body>
</html>'''

# 登录页面内容
LOGIN_CONTENT = '''
<div class="login-container">
    <div class="login-box">
        <div class="login-title">
            <h1>关键词回复管理</h1>
            <p>WebUI 管理后台</p>
        </div>
        {error}
        <form method="post" action="/login">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" placeholder="请输入管理密码" required autofocus>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">登录</button>
        </form>
        <div style="text-align: center; margin-top: 1.5rem;">
            <button class="theme-toggle" onclick="toggleTheme()" title="切换主题">🌓</button>
        </div>
        <div style="text-align: center; margin-top: 1rem; color: var(--text-secondary); font-size: 0.85rem;">
            版本 v1.2.0
        </div>
    </div>
</div>
'''

# 头部导航
HEADER_NAV = '''
<header class="header">
    <div class="header-content">
        <div class="logo">关键词回复管理</div>
        <nav class="nav">
            <a href="/" {dashboard_active}>仪表板</a>
            <a href="/keywords" {keywords_active}>关键词</a>
            <a href="/detects" {detects_active}>检测词</a>
            <a href="/images" {images_active}>图片</a>
            <button class="theme-toggle" onclick="toggleTheme()" title="切换主题">🌓</button>
            <a href="/logout" class="btn btn-sm btn-secondary">退出</a>
        </nav>
    </div>
</header>
'''


class WebUIServer:
    """WebUI HTTP 服务器"""

    def __init__(self, plugin, host="127.0.0.1", port=8888, session_timeout=3600):
        self.plugin = plugin
        self.host = host
        self.port = port
        self.session_timeout = session_timeout
        self.server = None
        self.sessions = {}  # session_id -> {user, expires}
        self.csrf_tokens = {}  # token -> expires
        self.login_attempts = {}  # ip -> [timestamps]
        self.password_file = os.path.join(plugin.data_dir, "webui_password.hash")

    def _hash_password(self, password: str, salt: bytes = None) -> tuple:
        """使用 PBKDF2-SHA256 哈希密码"""
        if salt is None:
            salt = os.urandom(32)
        # 20万次迭代
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200000)
        return salt, key

    def _verify_password(self, password: str, salt: bytes, key: bytes) -> bool:
        """验证密码"""
        _, new_key = self._hash_password(password, salt)
        return hmac.compare_digest(key, new_key)

    def _load_password_hash(self) -> tuple:
        """加载密码哈希"""
        if os.path.exists(self.password_file):
            try:
                with open(self.password_file, 'rb') as f:
                    data = f.read()
                    if len(data) == 64:
                        salt = data[:32]
                        key = data[32:]
                        return salt, key
            except Exception:
                pass
        return None, None

    def _save_password_hash(self, salt: bytes, key: bytes):
        """保存密码哈希"""
        try:
            with open(self.password_file, 'wb') as f:
                f.write(salt + key)
            return True
        except Exception as e:
            self.plugin.logger.error(f"保存密码哈希失败: {e}")
            return False

    def has_password(self) -> bool:
        """检查是否已设置密码"""
        salt, key = self._load_password_hash()
        return salt is not None and key is not None

    def set_password(self, password: str) -> bool:
        """设置新密码"""
        if len(password) < 6:
            return False
        salt, key = self._hash_password(password)
        return self._save_password_hash(salt, key)

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        salt, key = self._load_password_hash()
        if salt is None or key is None:
            return False
        return self._verify_password(password, salt, key)

    def _check_login_rate_limit(self, client_ip: str) -> bool:
        """检查登录限流（5分钟内最多5次）"""
        now = time.time()
        window = 300  # 5分钟
        max_attempts = 5

        if client_ip not in self.login_attempts:
            self.login_attempts[client_ip] = []

        # 清理过期记录
        self.login_attempts[client_ip] = [
            t for t in self.login_attempts[client_ip] if now - t < window
        ]

        if len(self.login_attempts[client_ip]) >= max_attempts:
            return False

        self.login_attempts[client_ip].append(now)
        return True

    def _generate_csrf_token(self) -> str:
        """生成 CSRF Token"""
        token = secrets.token_urlsafe(32)
        self.csrf_tokens[token] = time.time() + 3600  # 1小时过期
        return token

    def _verify_csrf_token(self, token: str) -> bool:
        """验证 CSRF Token"""
        if token not in self.csrf_tokens:
            return False
        expires = self.csrf_tokens[token]
        if time.time() > expires:
            del self.csrf_tokens[token]
            return False
        return True

    def _clean_expired_csrf_tokens(self):
        """清理过期的 CSRF Token"""
        now = time.time()
        expired = [t for t, exp in self.csrf_tokens.items() if now > exp]
        for t in expired:
            del self.csrf_tokens[t]

    def _create_session(self) -> str:
        """创建新会话"""
        session_id = secrets.token_urlsafe(32)
        expires = time.time() + self.session_timeout
        self.sessions[session_id] = {"expires": expires}
        return session_id

    def _verify_session(self, session_id: str) -> bool:
        """验证会话"""
        if session_id not in self.sessions:
            return False
        session = self.sessions[session_id]
        if time.time() > session["expires"]:
            del self.sessions[session_id]
            return False
        # 续期会话
        session["expires"] = time.time() + self.session_timeout
        return True

    def _delete_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def _get_session_id_from_cookie(self, headers: dict) -> str:
        """从 Cookie 中获取会话 ID"""
        cookie = headers.get("Cookie", "")
        for item in cookie.split(";"):
            item = item.strip()
            if item.startswith("session_id="):
                return item[11:]
        return None

    def _parse_form_data(self, body: bytes) -> dict:
        """解析表单数据"""
        result = {}
        try:
            text = body.decode('utf-8')
            for pair in text.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    result[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
        except Exception:
            pass
        return result

    def _parse_query_string(self, path: str) -> dict:
        """解析查询字符串"""
        result = {}
        if '?' in path:
            query = path.split('?', 1)[1]
            for pair in query.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    result[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
        return result

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    def _render_page(self, title: str, content: str) -> str:
        """渲染完整页面"""
        return HTML_TEMPLATE.format(title=title, content=content)

    def _render_login_page(self, error: str = None, csrf_token: str = None) -> str:
        """渲染登录页面"""
        error_html = f'<div class="alert alert-error">{self._escape_html(error)}</div>' if error else ''
        if csrf_token is None:
            csrf_token = self._generate_csrf_token()
        content = LOGIN_CONTENT.format(error=error_html, csrf_token=csrf_token)
        return self._render_page("登录", content)

    def _render_header(self, active_page: str = "") -> str:
        """渲染头部导航"""
        return HEADER_NAV.format(
            dashboard_active='class="active"' if active_page == "dashboard" else "",
            keywords_active='class="active"' if active_page == "keywords" else "",
            detects_active='class="active"' if active_page == "detects" else "",
            images_active='class="active"' if active_page == "images" else ""
        )

    def _render_dashboard(self) -> str:
        """渲染仪表板页面"""
        data = self.plugin.data
        keywords_count = len(data.get("command_triggered", []))
        detects_count = len(data.get("auto_detect", []))

        # 统计图片数量
        images_count = 0
        if os.path.exists(self.plugin.image_dir):
            images_count = len([f for f in os.listdir(self.plugin.image_dir)
                              if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))])

        content = self._render_header("dashboard")
        content += f'''
<div class="container">
    <h1 style="margin-bottom: 1.5rem;">仪表板</h1>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{keywords_count}</div>
            <div class="stat-label">关键词</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{detects_count}</div>
            <div class="stat-label">检测词</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{images_count}</div>
            <div class="stat-label">图片</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.plugin.config.get("cooldown", 0)}s</div>
            <div class="stat-label">冷却时间</div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">快速操作</div>
        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
            <a href="/keywords?action=add" class="btn btn-primary">添加关键词</a>
            <a href="/detects?action=add" class="btn btn-primary">添加检测词</a>
            <a href="/images" class="btn btn-secondary">管理图片</a>
        </div>
    </div>

    <div class="card">
        <div class="card-title">使用说明</div>
        <div style="color: var(--text-secondary); line-height: 1.8;">
            <p><strong>关键词：</strong>通过命令 <code>/关键词</code> 触发的回复，需要精确匹配或前缀匹配。</p>
            <p><strong>检测词：</strong>自动检测消息内容并回复，支持正则匹配。</p>
            <p><strong>群聊管理：</strong>可以为每个关键词/检测词设置群聊黑白名单。</p>
            <p><strong>图片支持：</strong>回复内容可以包含图片，支持多图混合。</p>
        </div>
    </div>
</div>
'''
        return self._render_page("仪表板", content)

    def _render_keywords_page(self, query_params: dict) -> str:
        """渲染关键词管理页面"""
        action = query_params.get("action", "list")
        data = self.plugin.data
        keywords = data.get("command_triggered", [])

        content = self._render_header("keywords")
        content += '<div class="container">'

        if action == "add":
            # 添加关键词表单
            content += '''
<h1 style="margin-bottom: 1.5rem;">添加关键词</h1>
<div class="card">
    <form method="post" action="/api/keywords">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <input type="hidden" name="action" value="add">
        <div class="form-group">
            <label>关键词</label>
            <input type="text" name="keyword" placeholder="触发关键词" required>
        </div>
        <div class="form-group">
            <label>回复内容</label>
            <textarea name="reply_text" placeholder="回复文本内容"></textarea>
        </div>
        <div class="form-group">
            <label>图片文件名（可选，多个用逗号分隔）</label>
            <input type="text" name="reply_images" placeholder="如: image1.jpg, image2.jpg">
        </div>
        <div class="form-group">
            <label>群聊限制模式</label>
            <select name="mode">
                <option value="all">所有群聊</option>
                <option value="whitelist">白名单（仅指定群可用）</option>
                <option value="blacklist">黑名单（指定群不可用）</option>
            </select>
        </div>
        <div class="form-group">
            <label>群号列表（逗号分隔，仅在白名单/黑名单模式下有效）</label>
            <input type="text" name="groups" placeholder="如: 123456789,987654321">
        </div>
        <div style="display: flex; gap: 1rem;">
            <button type="submit" class="btn btn-primary">保存</button>
            <a href="/keywords" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
'''.format(csrf_token=self._generate_csrf_token())
        elif action == "edit":
            # 编辑关键词表单
            idx = int(query_params.get("idx", -1))
            if 0 <= idx < len(keywords):
                item = keywords[idx]
                keyword = item.get("keyword", "")
                entries = item.get("entries", [])
                reply_text = ""
                reply_images = ""
                mode = item.get("mode", "all")
                groups = item.get("groups", [])
                groups_str = ", ".join(str(g) for g in groups) if groups else ""
                if entries:
                    first_reply = entries[0]
                    reply_text = first_reply.get("text", "")
                    images = first_reply.get("images", [])
                    reply_images = ", ".join([img.get("path", "") for img in images if img.get("path")])

                content += f'''
<h1 style="margin-bottom: 1.5rem;">编辑关键词</h1>
<div class="card">
    <form method="post" action="/api/keywords">
        <input type="hidden" name="csrf_token" value="{self._generate_csrf_token()}">
        <input type="hidden" name="action" value="edit">
        <input type="hidden" name="idx" value="{idx}">
        <div class="form-group">
            <label>关键词</label>
            <input type="text" name="keyword" value="{self._escape_html(keyword)}" required>
        </div>
        <div class="form-group">
            <label>回复内容</label>
            <textarea name="reply_text">{self._escape_html(reply_text)}</textarea>
        </div>
        <div class="form-group">
            <label>图片文件名（可选，多个用逗号分隔）</label>
            <input type="text" name="reply_images" value="{self._escape_html(reply_images)}">
        </div>
        <div class="form-group">
            <label>群聊限制模式</label>
            <select name="mode">
                <option value="all" {"selected" if mode == "all" else ""}>所有群聊</option>
                <option value="whitelist" {"selected" if mode == "whitelist" else ""}>白名单（仅指定群可用）</option>
                <option value="blacklist" {"selected" if mode == "blacklist" else ""}>黑名单（指定群不可用）</option>
            </select>
        </div>
        <div class="form-group">
            <label>群号列表（逗号分隔，仅在白名单/黑名单模式下有效）</label>
            <input type="text" name="groups" value="{self._escape_html(groups_str)}" placeholder="如: 123456789,987654321">
        </div>
        <div style="display: flex; gap: 1rem;">
            <button type="submit" class="btn btn-primary">保存</button>
            <a href="/keywords" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
'''
            else:
                content += '<div class="alert alert-error">关键词不存在</div>'
        else:
            # 关键词列表
            search = query_params.get("search", "").lower()
            filtered = []
            for i, item in enumerate(keywords):
                keyword = item.get("keyword", "")
                if not search or search in keyword.lower():
                    filtered.append((i, item))

            content += '''
<h1 style="margin-bottom: 1.5rem;">关键词管理</h1>
<div class="toolbar">
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="搜索关键词..." value="{search}" onkeypress="if(event.key==='Enter')doSearch()">
    </div>
    <a href="/keywords?action=add" class="btn btn-primary">添加关键词</a>
</div>
<script>
function doSearch() {{
    const val = document.getElementById('searchInput').value;
    window.location.href = '/keywords?search=' + encodeURIComponent(val);
}}
</script>
'''.format(search=self._escape_html(search))

            if filtered:
                content += '<div class="card"><div class="table-container"><table>'
                content += '<thead><tr><th>序号</th><th>关键词</th><th>回复数</th><th>群聊限制</th><th>操作</th></tr></thead><tbody>'
                for idx, item in filtered:
                    keyword = item.get("keyword", "")
                    entries = item.get("entries", [])
                    reply_count = len(entries)

                    # 群聊限制
                    mode = item.get("mode", "all")
                    groups = item.get("groups", [])
                    if mode == "all":
                        group_display = '<span class="tag tag-secondary">所有群聊</span>'
                    elif mode == "whitelist":
                        group_display = f'<span class="tag">白名单 ({len(groups)}个)</span>'
                    else:
                        group_display = f'<span class="tag" style="background: var(--danger)">黑名单 ({len(groups)}个)</span>'

                    content += f'''
<tr>
    <td>{idx + 1}</td>
    <td>{self._escape_html(keyword)}</td>
    <td>{reply_count}</td>
    <td>{group_display}</td>
    <td>
        <div class="actions">
            <a href="/keywords?action=edit&idx={idx}" class="btn btn-sm btn-secondary">编辑</a>
            <form method="post" action="/api/keywords" style="display:inline" onsubmit="return confirm('确定删除此关键词？')">
                <input type="hidden" name="csrf_token" value="{self._generate_csrf_token()}">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="idx" value="{idx}">
                <button type="submit" class="btn btn-sm btn-danger">删除</button>
            </form>
        </div>
    </td>
</tr>
'''
                content += '</tbody></table></div></div>'
            else:
                content += '''
<div class="card empty-state">
    <div class="empty-state-icon">📭</div>
    <p>暂无关键词</p>
    <a href="/keywords?action=add" class="btn btn-primary" style="margin-top: 1rem;">添加第一个关键词</a>
</div>
'''

        content += '</div>'
        return self._render_page("关键词管理", content)

    def _render_detects_page(self, query_params: dict) -> str:
        """渲染检测词管理页面"""
        action = query_params.get("action", "list")
        data = self.plugin.data
        detects = data.get("auto_detect", [])

        content = self._render_header("detects")
        content += '<div class="container">'

        if action == "add":
            # 添加检测词表单
            content += '''
<h1 style="margin-bottom: 1.5rem;">添加检测词</h1>
<div class="card">
    <form method="post" action="/api/detects">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <input type="hidden" name="action" value="add">
        <div class="form-group">
            <label>检测词</label>
            <input type="text" name="keyword" placeholder="检测关键词" required>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" name="is_regex" style="width: auto; margin-right: 0.5rem;">
                使用正则匹配
            </label>
        </div>
        <div class="form-group">
            <label>回复内容</label>
            <textarea name="reply_text" placeholder="回复文本内容"></textarea>
        </div>
        <div class="form-group">
            <label>图片文件名（可选，多个用逗号分隔）</label>
            <input type="text" name="reply_images" placeholder="如: image1.jpg, image2.jpg">
        </div>
        <div class="form-group">
            <label>群聊限制模式</label>
            <select name="mode">
                <option value="all">所有群聊</option>
                <option value="whitelist">白名单（仅指定群可用）</option>
                <option value="blacklist">黑名单（指定群不可用）</option>
            </select>
        </div>
        <div class="form-group">
            <label>群号列表（逗号分隔，仅在白名单/黑名单模式下有效）</label>
            <input type="text" name="groups" placeholder="如: 123456789,987654321">
        </div>
        <div style="display: flex; gap: 1rem;">
            <button type="submit" class="btn btn-primary">保存</button>
            <a href="/detects" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
'''.format(csrf_token=self._generate_csrf_token())
        elif action == "edit":
            # 编辑检测词表单
            idx = int(query_params.get("idx", -1))
            if 0 <= idx < len(detects):
                item = detects[idx]
                keyword = item.get("keyword", "")
                is_regex = item.get("is_regex", False)
                entries = item.get("entries", [])
                reply_text = ""
                reply_images = ""
                mode = item.get("mode", "all")
                groups = item.get("groups", [])
                groups_str = ", ".join(str(g) for g in groups) if groups else ""
                if entries:
                    first_reply = entries[0]
                    reply_text = first_reply.get("text", "")
                    images = first_reply.get("images", [])
                    reply_images = ", ".join([img.get("path", "") for img in images if img.get("path")])

                content += f'''
<h1 style="margin-bottom: 1.5rem;">编辑检测词</h1>
<div class="card">
    <form method="post" action="/api/detects">
        <input type="hidden" name="csrf_token" value="{self._generate_csrf_token()}">
        <input type="hidden" name="action" value="edit">
        <input type="hidden" name="idx" value="{idx}">
        <div class="form-group">
            <label>检测词</label>
            <input type="text" name="keyword" value="{self._escape_html(keyword)}" required>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" name="is_regex" {"checked" if is_regex else ""} style="width: auto; margin-right: 0.5rem;">
                使用正则匹配
            </label>
        </div>
        <div class="form-group">
            <label>回复内容</label>
            <textarea name="reply_text">{self._escape_html(reply_text)}</textarea>
        </div>
        <div class="form-group">
            <label>图片文件名（可选，多个用逗号分隔）</label>
            <input type="text" name="reply_images" value="{self._escape_html(reply_images)}">
        </div>
        <div class="form-group">
            <label>群聊限制模式</label>
            <select name="mode">
                <option value="all" {"selected" if mode == "all" else ""}>所有群聊</option>
                <option value="whitelist" {"selected" if mode == "whitelist" else ""}>白名单（仅指定群可用）</option>
                <option value="blacklist" {"selected" if mode == "blacklist" else ""}>黑名单（指定群不可用）</option>
            </select>
        </div>
        <div class="form-group">
            <label>群号列表（逗号分隔，仅在白名单/黑名单模式下有效）</label>
            <input type="text" name="groups" value="{self._escape_html(groups_str)}" placeholder="如: 123456789,987654321">
        </div>
        <div style="display: flex; gap: 1rem;">
            <button type="submit" class="btn btn-primary">保存</button>
            <a href="/detects" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
'''
            else:
                content += '<div class="alert alert-error">检测词不存在</div>'
        else:
            # 检测词列表
            search = query_params.get("search", "").lower()
            filtered = []
            for i, item in enumerate(detects):
                keyword = item.get("keyword", "")
                if not search or search in keyword.lower():
                    filtered.append((i, item))

            content += '''
<h1 style="margin-bottom: 1.5rem;">检测词管理</h1>
<div class="toolbar">
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="搜索检测词..." value="{search}" onkeypress="if(event.key==='Enter')doSearch()">
    </div>
    <a href="/detects?action=add" class="btn btn-primary">添加检测词</a>
</div>
<script>
function doSearch() {{
    const val = document.getElementById('searchInput').value;
    window.location.href = '/detects?search=' + encodeURIComponent(val);
}}
</script>
'''.format(search=self._escape_html(search))

            if filtered:
                content += '<div class="card"><div class="table-container"><table>'
                content += '<thead><tr><th>序号</th><th>检测词</th><th>类型</th><th>回复数</th><th>群聊限制</th><th>操作</th></tr></thead><tbody>'
                for idx, item in filtered:
                    keyword = item.get("keyword", "")
                    is_regex = item.get("is_regex", False)
                    entries = item.get("entries", [])
                    reply_count = len(entries)

                    type_display = '<span class="tag">正则</span>' if is_regex else '<span class="tag tag-secondary">普通</span>'

                    # 群聊限制
                    mode = item.get("mode", "all")
                    groups = item.get("groups", [])
                    if mode == "all":
                        group_display = '<span class="tag tag-secondary">所有群聊</span>'
                    elif mode == "whitelist":
                        group_display = f'<span class="tag">白名单 ({len(groups)}个)</span>'
                    else:
                        group_display = f'<span class="tag" style="background: var(--danger)">黑名单 ({len(groups)}个)</span>'

                    content += f'''
<tr>
    <td>{idx + 1}</td>
    <td>{self._escape_html(keyword)}</td>
    <td>{type_display}</td>
    <td>{reply_count}</td>
    <td>{group_display}</td>
    <td>
        <div class="actions">
            <a href="/detects?action=edit&idx={idx}" class="btn btn-sm btn-secondary">编辑</a>
            <form method="post" action="/api/detects" style="display:inline" onsubmit="return confirm('确定删除此检测词？')">
                <input type="hidden" name="csrf_token" value="{self._generate_csrf_token()}">
                <input type="hidden" name="action" value="delete">
                <input type="hidden" name="idx" value="{idx}">
                <button type="submit" class="btn btn-sm btn-danger">删除</button>
            </form>
        </div>
    </td>
</tr>
'''
                content += '</tbody></table></div></div>'
            else:
                content += '''
<div class="card empty-state">
    <div class="empty-state-icon">📭</div>
    <p>暂无检测词</p>
    <a href="/detects?action=add" class="btn btn-primary" style="margin-top: 1rem;">添加第一个检测词</a>
</div>
'''

        content += '</div>'
        return self._render_page("检测词管理", content)

    def _render_images_page(self, query_params: dict) -> str:
        """渲染图片管理页面"""
        content = self._render_header("images")
        content += '<div class="container">'
        content += '<h1 style="margin-bottom: 1.5rem;">图片管理</h1>'

        # 获取所有图片
        images = []
        if os.path.exists(self.plugin.image_dir):
            for f in os.listdir(self.plugin.image_dir):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    path = os.path.join(self.plugin.image_dir, f)
                    size = os.path.getsize(path)
                    images.append({"name": f, "size": size})

        # 上传表单
        content += '''
<div class="card" style="margin-bottom: 1.5rem;">
    <div class="card-title">上传图片</div>
    <form method="post" action="/api/images" enctype="multipart/form-data">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <input type="hidden" name="action" value="upload">
        <div style="display: flex; gap: 1rem; align-items: flex-end;">
            <div style="flex: 1;">
                <input type="file" name="image" accept="image/*" required>
            </div>
            <button type="submit" class="btn btn-primary">上传</button>
        </div>
    </form>
</div>
'''.format(csrf_token=self._generate_csrf_token())

        if images:
            content += '<div class="card"><div class="table-container"><table>'
            content += '<thead><tr><th>预览</th><th>文件名</th><th>大小</th><th>操作</th></tr></thead><tbody>'
            for img in images:
                size_str = f"{img['size'] / 1024:.1f} KB" if img['size'] < 1024 * 1024 else f"{img['size'] / (1024 * 1024):.2f} MB"
                content += f'''
<tr>
    <td><img src="/api/images/{img['name']}" class="image-preview" onclick="viewImage('/api/images/{img['name']}')"></td>
    <td>{img['name']}</td>
    <td>{size_str}</td>
    <td>
        <form method="post" action="/api/images" style="display:inline" onsubmit="return confirm('确定删除此图片？')">
            <input type="hidden" name="csrf_token" value="{self._generate_csrf_token()}">
            <input type="hidden" name="action" value="delete">
            <input type="hidden" name="filename" value="{img['name']}">
            <button type="submit" class="btn btn-sm btn-danger">删除</button>
        </form>
    </td>
</tr>
'''
            content += '</tbody></table></div></div>'
            content += '''
<script>
function viewImage(src) {
    window.open(src, '_blank');
}
</script>
'''
        else:
            content += '''
<div class="card empty-state">
    <div class="empty-state-icon">🖼️</div>
    <p>暂无图片</p>
</div>
'''

        content += '</div>'
        return self._render_page("图片管理", content)

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理 HTTP 请求"""
        try:
            # 读取请求头
            header_data = await reader.readuntil(b"\r\n\r\n")
            header_text = header_data.decode('utf-8', errors='ignore')

            # 解析请求行
            lines = header_text.split("\r\n")
            if not lines:
                return

            request_line = lines[0]
            parts = request_line.split()
            if len(parts) < 3:
                return

            method = parts[0]
            path = parts[1]
            http_version = parts[2]

            # 解析请求头
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

            # 获取客户端 IP
            client_ip = writer.get_extra_info('peername', ('unknown', 0))[0]

            # 读取请求体
            body = b""
            content_length = int(headers.get("Content-Length", 0))
            if content_length > 0:
                body = await reader.read(content_length)

            # 路由处理
            response = await self._route_request(method, path, headers, body, client_ip)

            # 发送响应
            writer.write(response)
            await writer.drain()

        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            self.plugin.logger.error(f"处理请求异常: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _route_request(self, method: str, path: str, headers: dict, body: bytes, client_ip: str) -> bytes:
        """路由请求到对应的处理器"""
        # 清理过期 CSRF Token
        self._clean_expired_csrf_tokens()

        # 解析路径和查询参数
        query_params = self._parse_query_string(path)
        clean_path = path.split('?', 1)[0]

        # 检查登录状态
        session_id = self._get_session_id_from_cookie(headers)
        is_logged_in = session_id and self._verify_session(session_id)

        # 公开路由
        if clean_path == "/login":
            if method == "GET":
                html = self._render_login_page()
                return self._make_response(200, "text/html", html.encode('utf-8'))
            elif method == "POST":
                return await self._handle_login(body, client_ip)

        # 需要登录的路由
        if not is_logged_in:
            return self._redirect_response("/login")

        if clean_path == "/logout":
            if session_id:
                self._delete_session(session_id)
            return self._redirect_response("/login")

        if clean_path == "/":
            html = self._render_dashboard()
            return self._make_response(200, "text/html", html.encode('utf-8'))

        if clean_path == "/keywords":
            html = self._render_keywords_page(query_params)
            return self._make_response(200, "text/html", html.encode('utf-8'))

        if clean_path == "/detects":
            html = self._render_detects_page(query_params)
            return self._make_response(200, "text/html", html.encode('utf-8'))

        if clean_path == "/images":
            html = self._render_images_page(query_params)
            return self._make_response(200, "text/html", html.encode('utf-8'))

        # API 路由
        if clean_path == "/api/keywords":
            return await self._handle_keywords_api(method, body)

        if clean_path == "/api/detects":
            return await self._handle_detects_api(method, body)

        if clean_path == "/api/images":
            return await self._handle_images_api(method, path, headers, body)

        if clean_path.startswith("/api/images/"):
            filename = clean_path[12:]
            return self._serve_image(filename)

        # 404
        return self._make_response(404, "text/plain", b"Not Found")

    async def _handle_login(self, body: bytes, client_ip: str) -> bytes:
        """处理登录请求"""
        # 检查限流
        if not self._check_login_rate_limit(client_ip):
            html = self._render_login_page("登录尝试次数过多，请5分钟后再试")
            return self._make_response(429, "text/html", html.encode('utf-8'))

        form_data = self._parse_form_data(body)
        password = form_data.get("password", "")
        csrf_token = form_data.get("csrf_token", "")

        # 验证 CSRF Token
        if not self._verify_csrf_token(csrf_token):
            html = self._render_login_page("安全验证失败，请刷新页面重试")
            return self._make_response(403, "text/html", html.encode('utf-8'))

        # 验证密码
        if self.verify_password(password):
            session_id = self._create_session()
            response_body = self._render_dashboard().encode('utf-8')
            response = self._make_response(200, "text/html", response_body, [
                f"Set-Cookie: session_id={session_id}; HttpOnly; Path=/; Max-Age={self.session_timeout}"
            ])
            return response
        else:
            html = self._render_login_page("密码错误")
            return self._make_response(401, "text/html", html.encode('utf-8'))

    async def _handle_keywords_api(self, method: str, body: bytes) -> bytes:
        """处理关键词 API"""
        if method != "POST":
            return self._redirect_response("/keywords")

        form_data = self._parse_form_data(body)
        action = form_data.get("action", "")

        # 验证 CSRF Token
        if not self._verify_csrf_token(form_data.get("csrf_token", "")):
            return self._redirect_response("/keywords")

        data = self.plugin.data
        keywords = data.setdefault("command_triggered", [])

        if action == "add":
            keyword = form_data.get("keyword", "").strip()
            reply_text = form_data.get("reply_text", "").strip()
            reply_images = form_data.get("reply_images", "").strip()
            mode = form_data.get("mode", "all")
            groups_str = form_data.get("groups", "").strip()
            groups = [g.strip() for g in groups_str.split(",") if g.strip()]

            if keyword:
                # 构建回复
                reply = {"text": reply_text, "images": []}
                if reply_images:
                    for img_name in reply_images.split(","):
                        img_name = img_name.strip()
                        if img_name:
                            reply["images"].append({"path": img_name})

                # 检查是否已存在
                existing = None
                for item in keywords:
                    if item.get("keyword") == keyword:
                        existing = item
                        break

                if existing:
                    existing.setdefault("entries", []).append(reply)
                else:
                    keywords.append({
                        "keyword": keyword,
                        "entries": [reply],
                        "mode": mode,
                        "groups": groups
                    })

                self.plugin._save_data()

        elif action == "edit":
            idx = int(form_data.get("idx", -1))
            keyword = form_data.get("keyword", "").strip()
            reply_text = form_data.get("reply_text", "").strip()
            reply_images = form_data.get("reply_images", "").strip()
            mode = form_data.get("mode", "all")
            groups_str = form_data.get("groups", "").strip()
            groups = [g.strip() for g in groups_str.split(",") if g.strip()]

            if 0 <= idx < len(keywords) and keyword:
                item = keywords[idx]
                item["keyword"] = keyword
                item["mode"] = mode
                item["groups"] = groups

                # 更新第一个回复
                if not item.get("entries"):
                    item["entries"] = []
                if not item["entries"]:
                    item["entries"].append({"text": "", "images": []})

                item["entries"][0]["text"] = reply_text
                item["entries"][0]["images"] = []
                if reply_images:
                    for img_name in reply_images.split(","):
                        img_name = img_name.strip()
                        if img_name:
                            item["entries"][0]["images"].append({"path": img_name})

                self.plugin._save_data()

        elif action == "delete":
            idx = int(form_data.get("idx", -1))
            if 0 <= idx < len(keywords):
                keywords.pop(idx)
                self.plugin._save_data()

        return self._redirect_response("/keywords")

    async def _handle_detects_api(self, method: str, body: bytes) -> bytes:
        """处理检测词 API"""
        if method != "POST":
            return self._redirect_response("/detects")

        form_data = self._parse_form_data(body)
        action = form_data.get("action", "")

        # 验证 CSRF Token
        if not self._verify_csrf_token(form_data.get("csrf_token", "")):
            return self._redirect_response("/detects")

        data = self.plugin.data
        detects = data.setdefault("auto_detect", [])

        if action == "add":
            keyword = form_data.get("keyword", "").strip()
            reply_text = form_data.get("reply_text", "").strip()
            reply_images = form_data.get("reply_images", "").strip()
            is_regex = form_data.get("is_regex", "") == "on"
            mode = form_data.get("mode", "all")
            groups_str = form_data.get("groups", "").strip()
            groups = [g.strip() for g in groups_str.split(",") if g.strip()]

            if keyword:
                # 构建回复
                reply = {"text": reply_text, "images": []}
                if reply_images:
                    for img_name in reply_images.split(","):
                        img_name = img_name.strip()
                        if img_name:
                            reply["images"].append({"path": img_name})

                # 检查是否已存在
                existing = None
                for item in detects:
                    if item.get("keyword") == keyword:
                        existing = item
                        break

                if existing:
                    existing.setdefault("entries", []).append(reply)
                else:
                    detects.append({
                        "keyword": keyword,
                        "is_regex": is_regex,
                        "entries": [reply],
                        "mode": mode,
                        "groups": groups
                    })

                self.plugin._save_data()

        elif action == "edit":
            idx = int(form_data.get("idx", -1))
            keyword = form_data.get("keyword", "").strip()
            reply_text = form_data.get("reply_text", "").strip()
            reply_images = form_data.get("reply_images", "").strip()
            is_regex = form_data.get("is_regex", "") == "on"
            mode = form_data.get("mode", "all")
            groups_str = form_data.get("groups", "").strip()
            groups = [g.strip() for g in groups_str.split(",") if g.strip()]

            if 0 <= idx < len(detects) and keyword:
                item = detects[idx]
                item["keyword"] = keyword
                item["is_regex"] = is_regex
                item["mode"] = mode
                item["groups"] = groups

                # 更新第一个回复
                if not item.get("entries"):
                    item["entries"] = []
                if not item["entries"]:
                    item["entries"].append({"text": "", "images": []})

                item["entries"][0]["text"] = reply_text
                item["entries"][0]["images"] = []
                if reply_images:
                    for img_name in reply_images.split(","):
                        img_name = img_name.strip()
                        if img_name:
                            item["entries"][0]["images"].append({"path": img_name})

                self.plugin._save_data()

        elif action == "delete":
            idx = int(form_data.get("idx", -1))
            if 0 <= idx < len(detects):
                detects.pop(idx)
                self.plugin._save_data()

        return self._redirect_response("/detects")

    async def _handle_images_api(self, method: str, path: str, headers: dict, body: bytes) -> bytes:
        """处理图片 API"""
        if method != "POST":
            return self._redirect_response("/images")

        content_type = headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            # 处理文件上传
            return await self._handle_image_upload(headers, body)
        else:
            # 处理删除
            form_data = self._parse_form_data(body)
            action = form_data.get("action", "")

            # 验证 CSRF Token
            if not self._verify_csrf_token(form_data.get("csrf_token", "")):
                return self._redirect_response("/images")

            if action == "delete":
                filename = form_data.get("filename", "")
                if filename and ".." not in filename:
                    filepath = os.path.join(self.plugin.image_dir, filename)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            self.plugin.logger.error(f"删除图片失败: {e}")

            return self._redirect_response("/images")

    async def _handle_image_upload(self, headers: dict, body: bytes) -> bytes:
        """处理图片上传"""
        content_type = headers.get("Content-Type", "")

        # 解析 boundary
        if "boundary=" not in content_type:
            return self._redirect_response("/images")

        boundary = content_type.split("boundary=")[1].split(";")[0].strip()
        boundary_bytes = ("--" + boundary).encode()

        # 简单的 multipart 解析
        parts = body.split(boundary_bytes)

        csrf_valid = False
        file_data = None
        filename = None

        for part in parts:
            if b"Content-Disposition" not in part:
                continue

            # 检查 CSRF token
            if b'name="csrf_token"' in part:
                # 提取 token 值
                lines = part.split(b"\r\n\r\n", 1)
                if len(lines) > 1:
                    token = lines[1].strip().decode('utf-8', errors='ignore')
                    if self._verify_csrf_token(token):
                        csrf_valid = True

            # 提取文件
            if b'name="image"' in part and b"filename=" in part:
                header_end = part.find(b"\r\n\r\n")
                if header_end > 0:
                    header = part[:header_end].decode('utf-8', errors='ignore')
                    # 提取文件名
                    if 'filename="' in header:
                        start = header.find('filename="') + 10
                        end = header.find('"', start)
                        filename = header[start:end]

                    file_data = part[header_end + 4:].rstrip(b"\r\n")

        if not csrf_valid:
            return self._redirect_response("/images")

        if file_data and filename:
            # 验证文件类型
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # 使用 MD5 命名
                file_hash = hashlib.md5(file_data).hexdigest()
                new_filename = f"{file_hash}{ext}"
                filepath = os.path.join(self.plugin.image_dir, new_filename)

                try:
                    with open(filepath, 'wb') as f:
                        f.write(file_data)
                except Exception as e:
                    self.plugin.logger.error(f"保存图片失败: {e}")

        return self._redirect_response("/images")

    def _serve_image(self, filename: str) -> bytes:
        """提供图片文件"""
        # 安全检查
        if ".." in filename or "/" in filename:
            return self._make_response(403, "text/plain", b"Forbidden")

        filepath = os.path.join(self.plugin.image_dir, filename)
        if not os.path.exists(filepath):
            return self._make_response(404, "text/plain", b"Not Found")

        # 确定 MIME 类型
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')

        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            return self._make_response(200, mime_type, data)
        except Exception:
            return self._make_response(500, "text/plain", b"Internal Server Error")

    def _make_response(self, status: int, content_type: str, body: bytes, extra_headers: list = None) -> bytes:
        """构造 HTTP 响应"""
        status_text = {200: "OK", 302: "Found", 401: "Unauthorized", 403: "Forbidden",
                      404: "Not Found", 429: "Too Many Requests", 500: "Internal Server Error"}

        headers = [
            f"HTTP/1.1 {status} {status_text.get(status, 'Unknown')}",
            f"Content-Type: {content_type}; charset=utf-8" if "text" in content_type else f"Content-Type: {content_type}",
            f"Content-Length: {len(body)}",
            "X-Frame-Options: DENY",
            "X-Content-Type-Options: nosniff",
            "Referrer-Policy: strict-origin-when-cross-origin"
        ]

        if extra_headers:
            headers.extend(extra_headers)

        headers.append("")
        headers.append("")

        header_bytes = "\r\n".join(headers).encode('utf-8')
        return header_bytes + body

    def _redirect_response(self, location: str) -> bytes:
        """构造重定向响应"""
        body = b""
        headers = [
            "HTTP/1.1 302 Found",
            f"Location: {location}",
            f"Content-Length: {len(body)}"
        ]
        return "\r\n".join(headers).encode('utf-8') + b"\r\n\r\n" + body

    async def start(self):
        """启动 WebUI 服务器"""
        try:
            self.server = await asyncio.start_server(
                self.handle_request,
                self.host,
                self.port
            )
            self.plugin.logger.info(f"WebUI 服务器已启动: http://{self.host}:{self.port}")
        except OSError as e:
            if "Address already in use" in str(e):
                # 尝试下一个端口
                self.port += 1
                if self.port < 65535:
                    await self.start()
                else:
                    self.plugin.logger.error("WebUI 服务器启动失败: 无可用端口")
            else:
                self.plugin.logger.error(f"WebUI 服务器启动失败: {e}")

    async def stop(self):
        """停止 WebUI 服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.plugin.logger.info("WebUI 服务器已停止")
