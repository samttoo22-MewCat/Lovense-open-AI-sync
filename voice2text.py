import os
import time
import traceback  # Import traceback at the top
# import json # 如果 main 函數不再直接使用 json，可以移除
import openai
from dotenv import load_dotenv
import logging
#from lovense import LovenseController

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加載環境變數
load_dotenv()

# 使用環境變數獲取 API 密鑰
# os.environ["OPENAI_API_KEY"] = "sk-proj-..." # Removed hardcoded key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    # Log error and raise if the key is crucial for this script
    logger.error("OpenAI API Key 未在環境變數中設置！") 
    raise ValueError("請設置 OPENAI_API_KEY 環境變數或將其放入 .env 文件")

openai.api_key = OPENAI_API_KEY

class AudioProcessor:
    """處理音訊文件和轉換為文本的類"""
    
    def __init__(self):
        self.transcript = ""
    
    def transcribe_audio(self, audio_path):
        """使用 OpenAI Whisper 將音訊轉換為文本"""
        try:
            logger.info(f"開始轉錄音訊文件: {audio_path}")
            
            # 確保文件存在
            if not os.path.exists(audio_path):
                 logger.error(f"音訊文件不存在: {audio_path}")
                 raise FileNotFoundError(f"音訊文件不存在: {audio_path}")

            with open(audio_path, "rb") as audio_file:
                transcript_response = openai.audio.transcriptions.create(
                    model="whisper-1", # 使用 whisper-1 模型
                    file=audio_file,
                    response_format="srt"
                )
            
            # Directly assign the string response when format is srt
            self.transcript = transcript_response 
            logger.info(f"音訊轉錄完成 (SRT 格式)")
            return self.transcript
            
        except openai.APIError as api_err:
             logger.error(f"OpenAI API 返回錯誤: {api_err}")
             traceback.print_exc()
             raise
        except FileNotFoundError as fnf_err:
             logger.error(str(fnf_err))
             traceback.print_exc()
             raise
        except Exception as e:
            logger.error(f"音訊轉錄過程中發生未知錯誤: {str(e)}")
            traceback.print_exc()
            raise
    
    def save_transcript(self, output_path):
        """保存轉錄文本到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.transcript)
            logger.info(f"轉錄文本已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存轉錄文本失敗: {str(e)}")
            traceback.print_exc()
            raise
