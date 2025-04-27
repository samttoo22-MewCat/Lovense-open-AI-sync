import json
import openai
import logging
import os  # Import os
import traceback # Import traceback
from typing import List, Dict, Any, Optional
import re
from dotenv import load_dotenv

load_dotenv() # <--- 確保這一行在讀取 API Key 之前被呼叫

# 取得 logger
# 建議在主腳本中配置 logger，這裡只獲取
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Added basicConfig for standalone testing
logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """分析轉錄文本內容並生成玩具控制建議的類 (可根據玩具名稱查詢功能)"""

    def __init__(self, functions_json_path: str = 'toys_funcs.json'): # Corrected default path if needed
        """
        初始化 ContentAnalyzer 並加載玩具功能數據。

        Args:
            functions_json_path (str): 包含玩具功能數據的 JSON 文件路徑。
        """
        self.analysis_result = {}
        self.toy_functions_data = self._load_toy_functions(functions_json_path)
        if not self.toy_functions_data:
             logger.warning(f"未能從 {functions_json_path} 加載玩具功能數據。分析將不考慮特定玩具功能。")

        # Removed hardcoded API key setting
        # os.environ["OPENAI_API_KEY"] = "sk-proj-..."

        # Ensure dotenv is loaded before this point (typically in the main script or at the top)
        # Load the API key from environment variable
        OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        if not OPENAI_API_KEY:
            # Optionally, make this less strict if the class might be used without analysis
            logger.error("OpenAI API Key 未在環境變數中設置！")
            raise ValueError("請設置 OPENAI_API_KEY 環境變數或將其放入 .env 文件")

        # Set the API key for the openai library
        openai.api_key = OPENAI_API_KEY

    def _load_toy_functions(self, json_path: str) -> Optional[Dict[str, Any]]:
        """從 JSON 文件加載玩具功能數據"""
        if not os.path.exists(json_path):
            logger.error(f"玩具功能 JSON 文件未找到: {json_path}")
            return None
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 假設 JSON 頂層有 "toys" 鍵
                if "toys" in data and isinstance(data["toys"], dict):
                     logger.info(f"成功從 {json_path} 加載玩具功能數據。")
                     return data["toys"]
                else:
                    logger.error(f"JSON 文件 {json_path} 缺少 'toys' 鍵或格式不正確。")
                    return None
        except json.JSONDecodeError as e:
            logger.error(f"解析 JSON 文件 {json_path} 失敗: {e}")
            traceback.print_exc()
            return None
        except Exception as e:
            logger.error(f"加載玩具功能數據時發生未知錯誤: {e}")
            traceback.print_exc()
            return None

    def analyze_content(self, transcript: str, toy_key: Optional[str] = None) -> Dict[str, Any]:
        """
        使用 OpenAI GPT 分析轉錄文本，根據提供的玩具 key (名稱) 查找其功能，並給出控制建議。

        Args:
            transcript (str): 要分析的文本記錄。
            toy_key (Optional[str]): 在 JSON 文件中定義的玩具 key (例如 "nora", "lush4")。

        Returns:
            Dict[str, Any]: 包含分析結果的字典。
        """
        toy_capabilities: Optional[List[str]] = None
        capabilities_prompt = ""

        # --- 根據 toy_key 查找功能 ---
        if toy_key and self.toy_functions_data:
            toy_data = self.toy_functions_data.get(toy_key)
            if toy_data and "functions" in toy_data:
                toy_capabilities = toy_data["functions"]
                if toy_capabilities:
                    capabilities_prompt = f"""
                    當前玩具 '{toy_data.get('name', toy_key)}' 支持以下功能：
                    {', '.join(toy_capabilities)}
                    請主要使用這些可用的功能來給出建議。如果某個功能未在列表中，請不要建議使用它。
                    """
                    logger.info(f"已為玩具 '{toy_key}' 找到功能: {toy_capabilities}")
                else:
                    logger.info(f"玩具 '{toy_key}' 功能列表為空。")
                    capabilities_prompt = f"\n當前玩具 '{toy_data.get('name', toy_key)}' 功能列表為空或未指定。\n"
            else:
                logger.warning(f"在功能數據中未找到名為 '{toy_key}' 的玩具或其功能列表。")
        elif toy_key:
             logger.warning(f"提供了玩具 key '{toy_key}' 但未能加載功能數據。")
        # -----------------------------

        try:
            logger.info(f"開始對 SRT 內容進行詳細分析並遵循指令 (玩具 key: {toy_key or '未指定'})")

            # --- MODIFIED SYSTEM PROMPT to follow speaker instructions ---
            system_prompt = f"""
            你是一個高度專業的內容分析助手，負責對成人內容的 SRT 格式文本記錄進行 **極其詳細和細膩** 的分析。
            輸入的文本是 SRT (SubRip Text) 字幕格式，記錄了對話和聲音。

            {capabilities_prompt}
            請 **仔細分析** 以下 SRT 文本內容。你需要做兩件事：
            1.  **識別並優先執行說話者給出的直接指令**: 留意文本中任何關於 **如何操作玩具** 的明確指示（例如："開大一點"、"停下"、"用 XX 強度"、"加快"等）。當你偵測到這類指令時，生成的 `command` **必須直接反映該指令**。
            2.  **捕捉情緒和動作變化**: 在沒有直接指令的區間，你需要像之前一樣，找出 **盡可能多** 的轉折點、情緒波動、關鍵動作描述、節奏或強度變化，**即使是細微的變化也要捕捉**，並據此生成控制建議。

            基礎可用的控制功能類型包括（但請 **嚴格優先** 使用上面為特定玩具指定的功能，**並優先執行直接指令**）：
            - Vibrate: 震動 (強度 1-20)
            - Rotate: 旋轉 (強度 1-20)
            - Pump: 泵送/收縮 (強度 1-20)
            - Thrusting: 抽插 (強度 1-20)
            - All: 設置其他功能 (強度 1-20)
            - Stop: 停止

            對於 **每一個** 識別出的事件點（無論是直接指令還是情緒變化），請提供：
            1.  **精確的開始時間戳 (timestamp)**: 從對應的 SRT 時間行提取 **開始時間** (格式 "HH:MM:SS,ms")。
            2.  場景/情緒/動作/指令的簡短描述 (description): 描述是基於情緒/動作推斷，還是直接引用了說話者的指令。例如："說話者指示停止" 或 "情緒逐漸升溫"。
            3.  建議的功能組合 (action):
                *   **如果偵測到直接指令**: action **必須** 執行該指令。如果指令包含具體強度（如"用 15 級"），則使用該強度；如果指令是相對的（如"開大點"），則在當前基礎上適當增加強度；如果指令是"停止"，則 action 為 "Stop"。
                *   **如果沒有直接指令**: 根據情緒/動作推斷 action 和強度。
                *   **強度 (1-20) 必須非常細膩且動態變化**:
                    *   低強度 (1-8): 溫柔、挑逗、緩和。
                    *   中強度 (9-15): 興奮上升、節奏加快。
                    *   高強度 (16-20): 高潮、激烈動作。
                    *   **根據文本內容和指令頻繁調整強度。**
                *   如果玩具支持，可組合功能。
            4.  建議的持續時間 (timeSec):
                *   根據事件/指令的上下文決定時長，力求多樣性。
                *   "Stop" 指令的 timeSec 應為 0。
            5.  可選：循環模式（loopRunningSec, loopPauseSec）。

            以JSON格式返回分析結果 (**確保 timestamp 是精確的 SRT 開始時間格式**):
            {{
                "events": [
                    {{
                        "timestamp": "HH:MM:SS,ms",
                        "description": "詳細描述(包含是否為直接指令)...",
                        "command": {{
                            "command": "Function",
                            "action": "指令(優先執行文本中的指令)...",
                            "timeSec": 持續時間(數字),
                            "loopRunningSec": 運行秒數(數字, 可選),
                            "loopPauseSec": 暫停秒數(數字, 可選),
                            "apiVer": 1
                        }}
                    }},
                    // ... 預期會有很多事件 ...
                ]
            }}
            仔細檢查強度值在 1-20 範圍內，時間值為數字。確保 command 字典結構完整。
            **目標是生成一個事件密集、強度變化豐富、既能反映內容情緒又能嚴格遵循說話者指令的控制序列。**
            """
            # --- END OF MODIFIED SYSTEM PROMPT ---

            response = openai.chat.completions.create(
                model="o4-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                response_format={"type": "json_object"}
            )

            # 嘗試解析 JSON 結果
            try:
                raw_response_content = response.choices[0].message.content
                # Log the raw response before attempting to parse or validate
                logger.debug(f"從 AI 收到的原始回應內容: {raw_response_content}") 

                self.analysis_result = json.loads(raw_response_content)
                logger.info("詳細文本分析（含指令遵循）完成")
                
                # Basic validation
                if "events" not in self.analysis_result or not isinstance(self.analysis_result["events"], list):
                    logger.error(f"分析結果缺少 'events' 列表或格式錯誤。收到的結構: {self.analysis_result}") # Log the problematic structure
                    raise ValueError("分析結果格式錯誤")
                
                # Validate timestamp format
                for event in self.analysis_result.get("events", []):
                    ts = event.get("timestamp")
                    if not isinstance(ts, str) or not re.match(r"\d{2}:\d{2}:\d{2},\d{3}", ts):
                        logger.warning(f"事件的時間戳格式可能不正確: {ts}")
                
                logger.info(f"分析生成了 {len(self.analysis_result.get('events', []))} 個事件。")
                return self.analysis_result
            except json.JSONDecodeError as json_err:
                logger.error(f"解析 AI 返回的 JSON 失敗: {json_err}")
                logger.error(f"導致解析失敗的原始回應內容: {raw_response_content}") # Log content that failed parsing
                traceback.print_exc()
                raise ValueError("無法解析 AI 的回應") from json_err

        except openai.APIError as api_err:
             logger.error(f"OpenAI API 返回錯誤: {api_err}")
             traceback.print_exc()
             raise
        except Exception as e:
            logger.error(f"內容分析過程中發生未知錯誤: {str(e)}")
            traceback.print_exc()
            raise

    def save_analysis(self, output_path: str):
        """保存分析結果到文件"""
        try:
            if not self.analysis_result:
                 logger.warning("分析結果為空，無法保存。")
                 return

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_result, f, ensure_ascii=False, indent=4)
            logger.info(f"分析結果已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存分析結果失敗: {str(e)}")
            traceback.print_exc()
            raise

# --- Removed main test function and if __name__ == '__main__' block ---
