#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import threading
import webview

# 设置Flask应用运行在本地的端口号
FLASK_PORT = 5000

# 启动Flask应用（在子进程中运行，避免阻塞主线程）
def start_flask_app():
    # 修改工作目录结构以便导入flow_editor
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        # 直接导入本地模块
        from flask_backend.demo import app
        # 不使用debug模式，也不使用reloader，避免信号处理问题
        app.run(debug=False, host='localhost', port=FLASK_PORT, use_reloader=False)
    except Exception as e:
        print(f"启动Flask应用时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # 创建新的线程来启动Flask应用
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
    flask_thread.start()

    print(f"Flask 服务运行在 http://localhost:{FLASK_PORT}")
    print(f"流程编辑器访问地址: http://localhost:{FLASK_PORT}/flow-editor/")
    print("请确保Vue前端已经启动 (cd vue_frontend && npm run dev)")

    # 创建一个窗口并加载Vue前端页面
    window = webview.create_window('AutoMaticWorker', f'http://localhost:{FLASK_PORT}/flow-editor/')

    # 启动pywebview的主循环
    webview.start()

    print("应用已关闭")
