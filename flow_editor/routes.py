#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, jsonify, request, render_template
from .models.flow import Flow, FlowNode, FlowConnection

# 创建Blueprint
flow_editor = Blueprint('flow_editor', __name__, 
                       template_folder='templates',
                       static_folder='static',
                       url_prefix='/flow-editor')

# 获取所有流程
@flow_editor.route('/flows', methods=['GET'])
def get_flows():
    """获取所有流程列表"""
    flows = Flow.get_all_flows()
    return jsonify(flows)

# 获取单个流程
@flow_editor.route('/flows/<flow_id>', methods=['GET'])
def get_flow(flow_id):
    """获取特定流程详情"""
    flow = Flow.get_flow_by_id(flow_id)
    if flow:
        return jsonify(flow)
    return jsonify({"error": "Flow not found"}), 404

# 创建新流程
@flow_editor.route('/flows', methods=['POST'])
def create_flow():
    """创建新流程"""
    data = request.json
    flow = Flow.create_flow(data)
    return jsonify(flow), 201

# 更新流程
@flow_editor.route('/flows/<flow_id>', methods=['PUT'])
def update_flow(flow_id):
    """更新现有流程"""
    data = request.json
    flow = Flow.update_flow(flow_id, data)
    if flow:
        return jsonify(flow)
    return jsonify({"error": "Flow not found"}), 404

# 删除流程
@flow_editor.route('/flows/<flow_id>', methods=['DELETE'])
def delete_flow(flow_id):
    """删除流程"""
    result = Flow.delete_flow(flow_id)
    if result:
        return jsonify({"success": True})
    return jsonify({"error": "Flow not found"}), 404

# 导出流程为可执行脚本
@flow_editor.route('/flows/<flow_id>/export', methods=['GET'])
def export_flow(flow_id):
    """导出流程为Python脚本"""
    script = Flow.export_to_script(flow_id)
    if script:
        return jsonify({"script": script})
    return jsonify({"error": "Flow not found"}), 404

# 流程编辑器主页
@flow_editor.route('/', methods=['GET'])
def editor_home():
    """流程编辑器主页"""
    return render_template('flow_editor/index.html')

# 流程可视化编辑页面
@flow_editor.route('/editor/<flow_id>', methods=['GET'])
def editor_page(flow_id):
    """流程可视化编辑页面"""
    return render_template('flow_editor/editor.html', flow_id=flow_id) 