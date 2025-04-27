import requests
import hashlib
import socketio
from typing import Dict, Any

class LovenseController:
    def __init__(self, developer_token: str):
        self.developer_token = developer_token
        self.socket = None
        self.domain = None
        self.https_port = None
    
    def get_qr_code(self, user_id: str, username: str) -> Dict[str, Any]:
        """获取二维码供用户扫描连接玩具"""
        url = "https://api.lovense-api.com/api/lan/getQrCode"
        
        # 创建用户令牌（实际使用时应该使用更安全的方法）
        utoken = hashlib.md5(f"{user_id}salt".encode()).hexdigest()
        
        data = {
            "token": self.developer_token,
            "uid": user_id,
            "uname": username,
            "utoken": utoken,
            "v": 2
        }
        
        response = requests.post(url, data=data)
        return response.json()
    
    def connect_socket(self, domain: str, port: str):
        """连接到玩具的WebSocket服务器"""
        socket_url = f"https://{domain}:{port}"
        self.socket = socketio.Client()
        self.socket.connect(socket_url, transports=["websocket"])
    
    def vibrate(self, strength: int, duration: int, toy_id: str = None):
        """控制玩具振动
        
        Args:
            strength: 振动强度 (0-20)
            duration: 持续时间（秒）
            toy_id: 特定玩具ID，不指定则控制所有玩具
        """
        command = {
            "command": "Function",
            "action": f"Vibrate:{strength}",
            "timeSec": duration,
            "apiVer": 1
        }
        
        if toy_id:
            command["toy"] = toy_id
            
        self.socket.emit("basicapi_send_toy_command_ts", command)
    
    def stop_all(self):
        """停止所有玩具"""
        command = {
            "command": "Function",
            "action": "Stop",
            "timeSec": 0,
            "apiVer": 1
        }
        self.socket.emit("basicapi_send_toy_command_ts", command)

# 使用示例
def main():
    # 替换为你的开发者令牌
    controller = LovenseController("your_developer_token")
    
    # 获取二维码
    qr_result = controller.get_qr_code("user123", "TestUser")
    print(f"请使用Lovense Remote应用扫描二维码: {qr_result['data']['qr']}")
    
    # 等待用户扫描二维码并连接...
    # 实际应用中需要实现回调处理
    
    # 假设已经从回调获得了domain和port
    controller.connect_socket("example.lovense.club", "34568")
    
    # 控制示例
    try:
        # 振动强度16，持续20秒
        controller.vibrate(16, 20)
        
        # 停止所有玩具
        controller.stop_all()
    finally:
        if controller.socket:
            controller.socket.disconnect()

if __name__ == "__main__":
    main()
