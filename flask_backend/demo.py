from flask import Flask, jsonify, redirect
from flask_cors import CORS
import os
import sys

# 添加正确的路径以导入flow_editor模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 使用相对导入
from flow_editor.routes import flow_editor

app = Flask(__name__)
# 允许跨域请求, vue默认端口为5173而flask默认为5000
CORS(app)

# 注册流程编辑器Blueprint
app.register_blueprint(flow_editor)

# 添加根路径重定向到流程编辑器
@app.route('/')
def index():
    return redirect('/flow-editor/')

@app.route('/api/data', methods=['GET'])
def get_data():
    data = {
        "message": "Hello from Flask backend!"
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)