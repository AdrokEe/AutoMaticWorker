#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import uuid
import datetime
from pathlib import Path

# 设置流程文件保存路径
FLOW_DIR = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'process', 'flows'))
# 确保目录存在
FLOW_DIR.mkdir(parents=True, exist_ok=True)

class FlowNode:
    """流程节点类"""
    
    def __init__(self, node_id=None, node_type=None, position=None, data=None):
        self.id = node_id or str(uuid.uuid4())
        self.type = node_type  # 节点类型: start, action, condition, end
        self.position = position or {"x": 0, "y": 0}
        self.data = data or {}
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "position": self.position,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建节点"""
        return cls(
            node_id=data.get("id"),
            node_type=data.get("type"),
            position=data.get("position"),
            data=data.get("data")
        )


class FlowConnection:
    """流程连接类"""
    
    def __init__(self, connection_id=None, source_id=None, target_id=None, label=None, condition=None):
        self.id = connection_id or str(uuid.uuid4())
        self.source_id = source_id
        self.target_id = target_id
        self.label = label
        self.condition = condition
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "source": self.source_id,
            "target": self.target_id,
            "label": self.label,
            "condition": self.condition
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建连接"""
        return cls(
            connection_id=data.get("id"),
            source_id=data.get("source"),
            target_id=data.get("target"),
            label=data.get("label"),
            condition=data.get("condition")
        )


class Flow:
    """流程类"""
    
    def __init__(self, flow_id=None, name=None, description=None, nodes=None, connections=None, created_at=None, updated_at=None):
        self.id = flow_id or str(uuid.uuid4())
        self.name = name or f"New Flow {self.id[:8]}"
        self.description = description or ""
        self.nodes = nodes or []
        self.connections = connections or []
        self.created_at = created_at or datetime.datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": [conn.to_dict() for conn in self.connections],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建流程"""
        nodes = [FlowNode.from_dict(node_data) for node_data in data.get("nodes", [])]
        connections = [FlowConnection.from_dict(conn_data) for conn_data in data.get("connections", [])]
        
        return cls(
            flow_id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            nodes=nodes,
            connections=connections,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def save(self):
        """保存流程到文件"""
        file_path = FLOW_DIR / f"{self.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return self.to_dict()
    
    @classmethod
    def get_flow_by_id(cls, flow_id):
        """通过ID获取流程"""
        file_path = FLOW_DIR / f"{flow_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls.from_dict(data).to_dict()
    
    @classmethod
    def get_all_flows(cls):
        """获取所有流程"""
        flows = []
        for file_path in FLOW_DIR.glob('*.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 简化数据，只返回基本信息
                flows.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "nodes_count": len(data.get("nodes", [])),
                    "connections_count": len(data.get("connections", []))
                })
        
        return flows
    
    @classmethod
    def create_flow(cls, data):
        """创建新流程"""
        flow = cls(
            name=data.get("name"),
            description=data.get("description")
        )
        
        # 创建起始节点
        start_node = FlowNode(node_type="start", position={"x": 100, "y": 150}, data={"label": "开始"})
        flow.nodes.append(start_node)
        
        # 创建结束节点
        end_node = FlowNode(node_type="end", position={"x": 500, "y": 150}, data={"label": "结束"})
        flow.nodes.append(end_node)
        
        # 保存流程
        return flow.save()
    
    @classmethod
    def update_flow(cls, flow_id, data):
        """更新流程"""
        file_path = FLOW_DIR / f"{flow_id}.json"
        if not file_path.exists():
            return None
        
        # 读取现有数据
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        # 更新基本信息
        if "name" in data:
            existing_data["name"] = data["name"]
        if "description" in data:
            existing_data["description"] = data["description"]
        
        # 更新节点和连接
        if "nodes" in data:
            existing_data["nodes"] = data["nodes"]
        if "connections" in data:
            existing_data["connections"] = data["connections"]
        
        # 更新时间
        existing_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # 保存更新后的数据
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        return existing_data
    
    @classmethod
    def delete_flow(cls, flow_id):
        """删除流程"""
        file_path = FLOW_DIR / f"{flow_id}.json"
        if not file_path.exists():
            return False
        
        file_path.unlink()
        return True
    
    @classmethod
    def export_to_script(cls, flow_id):
        """导出流程为Python脚本"""
        flow_data = cls.get_flow_by_id(flow_id)
        if not flow_data:
            return None
        
        # 转换为Flow对象
        flow = cls.from_dict(flow_data)
        
        # 生成Python脚本
        script_lines = [
            "#!/usr/bin/env python",
            "# -*- coding: utf-8 -*-",
            f"# 自动生成的流程脚本: {flow.name}",
            f"# 创建时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "import time",
            "import logging",
            "",
            "# 配置日志",
            "logging.basicConfig(",
            "    level=logging.INFO,",
            "    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'",
            ")",
            "logger = logging.getLogger(__name__)",
            "",
            f"def run_flow_{flow.id.replace('-', '_')}():",
            f'    """',
            f'    {flow.name}',
            f'    ',
            f'    {flow.description}',
            f'    """',
            "    logger.info('开始执行流程')",
            ""
        ]
        
        # 为每个节点生成代码
        for node in flow.nodes:
            if node.type == "start":
                continue
            elif node.type == "end":
                script_lines.append("    logger.info('流程执行完成')")
                script_lines.append("    return True")
            elif node.type == "action":
                script_lines.append(f"    # 执行动作: {node.data.get('label', '未命名动作')}")
                script_lines.append(f"    logger.info('执行: {node.data.get('label', '未命名动作')}')")
                # 添加动作代码
                action_code = node.data.get('code', '    pass')
                for line in action_code.split('\n'):
                    script_lines.append(f"    {line}")
                script_lines.append("")
            elif node.type == "condition":
                script_lines.append(f"    # 条件判断: {node.data.get('label', '未命名条件')}")
                script_lines.append(f"    if {node.data.get('condition', 'True')}:")
                script_lines.append(f"        logger.info('条件 {node.data.get('label', '未命名条件')} 为真')")
                script_lines.append("        # 条件为真时执行的代码")
                script_lines.append("    else:")
                script_lines.append(f"        logger.info('条件 {node.data.get('label', '未命名条件')} 为假')")
                script_lines.append("        # 条件为假时执行的代码")
                script_lines.append("")
        
        script_lines.append("")
        script_lines.append("if __name__ == '__main__':")
        script_lines.append(f"    run_flow_{flow.id.replace('-', '_')}()")
        
        return "\n".join(script_lines) 