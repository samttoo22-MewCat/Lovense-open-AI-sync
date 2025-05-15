# tkinter_app.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import time
import logging
import traceback
import json
import openai
from dotenv import load_dotenv
import threading
import queue
import sys

# --- 導入你的模組 ---
try:
    from voice2text import AudioProcessor
    from content_analyzer import ContentAnalyzer
    from pornhub_audio import PornhubAudioDownloader
except ImportError as e:
    root_check = tk.Tk()
    root_check.withdraw()
    messagebox.showerror("啟動錯誤", f"無法導入必要的模組 ({e})。\n請確保 voice2text.py, content_analyzer.py, pornhub_audio.py 檔案存在。")
    root_check.destroy()
    sys.exit(1)

# --- 基本設定 ---
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format, filename='app.log', filemode='a')
logger = logging.getLogger(__name__)

load_dotenv()

# --- 常數 ---
DOWNLOAD_DIR = './downloads'
TRANSCRIPT_DIR = './transcripts'
ANALYSIS_DIR = './analysis_outputs'
TOY_FUNCTIONS_JSON = 'toys_funcs.json'

# --- 全域變數 ---
toy_data = None

# --- 載入玩具資料 ---
def load_toy_data(json_path):
    global toy_data
    if not os.path.exists(json_path):
        logger.error(f"玩具功能 JSON 文件未找到: {json_path}")
        return False, f"找不到玩具功能文件:\n{json_path}"
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "toys" in data and isinstance(data["toys"], dict):
             logger.info(f"成功從 {json_path} 加載玩具功能數據。")
             toy_data = data["toys"]
             return True, "玩具數據加載成功。"
        else:
            msg = f"JSON 文件 {json_path} 缺少 'toys' 鍵或格式不正確。"
            logger.error(msg)
            return False, msg
    except Exception as e:
        msg = f"加載玩具功能文件時出錯:\n{json_path}\n{e}"
        logger.error(f"加載或解析玩具功能 JSON 時出錯: {e}")
        traceback.print_exc()
        return False, msg

# --- 執行緒工作函數 (與之前版本類似，但輸出特定訊息) ---

# Step 0: Download & Extract Audio
def download_extract_thread_func(url, status_queue):
    """下載 P**nhub 影片並提取音訊"""
    try:
        status_queue.put(f"INFO: 開始從 {url} 下載並提取音訊...")
        downloader = PornhubAudioDownloader(save_dir=DOWNLOAD_DIR)
        audio_file_path = downloader.download_audio(url) # This already extracts audio

        if not audio_file_path:
            msg = "錯誤：無法下載或提取音訊。請檢查 URL 或 ffmpeg/phub 是否安裝正確。"
            status_queue.put(msg)
            status_queue.put("DOWNLOAD_EXTRACT_FAILED")
        else:
            msg = f"成功：音訊文件已保存到 '{audio_file_path}'"
            status_queue.put(msg)
            status_queue.put(f"RESULT_AUDIO_PATH:{audio_file_path}") # Send path back
            status_queue.put("DOWNLOAD_EXTRACT_COMPLETE")

    except Exception as e:
        error_msg = f"錯誤：下載提取過程中發生錯誤: {e}"
        logger.error(error_msg + f"\n{traceback.format_exc()}")
        status_queue.put(error_msg)
        status_queue.put("DOWNLOAD_EXTRACT_FAILED")

# Step 1: Transcribe Audio (Takes audio path)
def transcribe_thread_func(audio_path, status_queue):
    """將音訊檔案轉錄為 SRT 字幕"""
    try:
        # Basic check if path is valid (though AudioProcessor does it too)
        if not audio_path or not os.path.exists(audio_path):
             status_queue.put(f"錯誤：用於轉錄的音訊文件路徑無效或不存在: {audio_path}")
             status_queue.put("TRANSCRIBE_FAILED")
             return

        status_queue.put(f"INFO: 開始轉錄音訊文件: {os.path.basename(audio_path)} (可能需要幾分鐘)...")
        audio_processor = AudioProcessor()
        timestamp_str = time.strftime('%Y%m%d_%H%M%S')
        base_filename = os.path.splitext(os.path.basename(audio_path))[0]
        final_transcript_path = os.path.join(TRANSCRIPT_DIR, f"{base_filename}_transcript_{timestamp_str}.srt")
        transcript_content = audio_processor.transcribe_audio(audio_path) # Returns SRT string
        audio_processor.save_transcript(final_transcript_path) # Saves the SRT string
        msg = f"成功：音訊轉錄完成，SRT 保存到 '{final_transcript_path}'"
        status_queue.put(msg)
        status_queue.put(f"RESULT_SRT_PATH:{final_transcript_path}") # Send path back
        status_queue.put(f"RESULT_SRT_CONTENT:{transcript_content}") # Send content for analysis
        status_queue.put("TRANSCRIBE_COMPLETE")

    except Exception as e:
        error_msg = f"錯誤：轉錄過程中發生錯誤: {e}"
        logger.error(error_msg + f"\n{traceback.format_exc()}")
        status_queue.put(error_msg)
        status_queue.put("TRANSCRIBE_FAILED")

# Step 2: Analyze SRT Content (Takes SRT content string)
def analyze_thread_func(srt_content_string, srt_input_path, toy_key, status_queue):
    """分析 SRT 字幕內容生成分析檔案"""
    try:
        if not srt_content_string:
            status_queue.put("錯誤：用於分析的 SRT 內容為空。")
            status_queue.put("ANALYZE_FAILED")
            return

        status_queue.put(f"INFO: 開始分析 SRT 內容 (使用玩具: {toy_key})...")
        analyzer = ContentAnalyzer(functions_json_path=TOY_FUNCTIONS_JSON)
        timestamp_str_analysis = time.strftime('%Y%m%d_%H%M%S')

        # Determine base filename for analysis output
        if srt_input_path: # Prefer name based on input SRT file
            base_filename = os.path.splitext(os.path.basename(srt_input_path))[0]
        else: # Fallback if content came from transcription without saving path yet
            base_filename = f"analysis_output_{timestamp_str_analysis}"

        final_analysis_path = os.path.join(ANALYSIS_DIR, f"{base_filename}_analysis_{timestamp_str_analysis}.json")

        analysis_result = analyzer.analyze_content(srt_content_string, toy_key) # Pass SRT string
        analyzer.save_analysis(final_analysis_path)
        event_count = len(analysis_result.get("events", [])) if analysis_result else 0
        msg = f"成功：內容分析完成，生成 {event_count} 個事件，保存到 '{final_analysis_path}'"
        status_queue.put(msg)
        status_queue.put(f"RESULT_ANALYSIS_PATH:{final_analysis_path}")
        status_queue.put("ANALYZE_COMPLETE")

    except Exception as e:
        error_msg = f"錯誤：分析過程中發生錯誤: {e}"
        logger.error(error_msg + f"\n{traceback.format_exc()}")
        status_queue.put(error_msg)
        status_queue.put("ANALYZE_FAILED")


# --- Tkinter GUI 類 ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("音訊同步分析器 v3 - 多步驟")
        self.root.geometry("800x700") # 增加寬度和高度

        # --- Check API Key & Load Toy Data ---
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            messagebox.showerror("API Key 錯誤", "找不到 OpenAI API Key。")
            self.root.quit(); return
        openai.api_key = self.api_key
        logger.info("OpenAI API Key 已成功加載。")

        loaded_ok, msg = load_toy_data(TOY_FUNCTIONS_JSON)
        if not loaded_ok:
            messagebox.showerror("玩具數據錯誤", msg)
            self.root.quit(); return

        # --- 創建資料夾 ---
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
        os.makedirs(ANALYSIS_DIR, exist_ok=True)

        # --- 狀態變數 ---
        self.ph_url = tk.StringVar(value=os.getenv('PORNHUB_URL', ''))
        self.video_path = tk.StringVar()
        self.audio_path = tk.StringVar() # Path to the audio file for transcription
        self.srt_path = tk.StringVar()   # Path to the SRT file for analysis
        self.srt_content_for_analysis = None # Store SRT content here
        self.analysis_result_path = tk.StringVar() # Path to the final analysis JSON
        self.selected_toy_name = tk.StringVar()

        # --- UI 框架 ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 輸入區 ---
        input_frame = ttk.LabelFrame(main_frame, text="輸入來源", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        input_frame.columnconfigure(1, weight=1) # Allow entry/label to expand

        # URL Input
        ttk.Label(input_frame, text="P**nhub 網址:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.url_entry = ttk.Entry(input_frame, textvariable=self.ph_url, width=60)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        # Video Input
        ttk.Label(input_frame, text="本地視訊檔案:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.video_path_entry = ttk.Entry(input_frame, textvariable=self.video_path, width=60, state='readonly')
        self.video_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        video_select_button = ttk.Button(input_frame, text="瀏覽...", command=self.select_video_file)
        video_select_button.grid(row=1, column=2, padx=5, pady=5)

        # Audio Input (for Transcription/Analysis)
        ttk.Label(input_frame, text="本地音訊檔案:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.audio_path_entry = ttk.Entry(input_frame, textvariable=self.audio_path, width=60, state='readonly')
        self.audio_path_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.EW)
        audio_select_button = ttk.Button(input_frame, text="瀏覽...", command=self.select_audio_file)
        audio_select_button.grid(row=2, column=2, padx=5, pady=5)

        # SRT Input (for Analysis)
        ttk.Label(input_frame, text="本地字幕檔案:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.srt_path_entry = ttk.Entry(input_frame, textvariable=self.srt_path, width=60, state='readonly')
        self.srt_path_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.EW)
        srt_select_button = ttk.Button(input_frame, text="瀏覽...", command=self.select_srt_file)
        srt_select_button.grid(row=3, column=2, padx=5, pady=5)

        # Toy Selection (Needed for Analysis)
        ttk.Label(input_frame, text="目標玩具型號:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.toy_key_map = {data.get("name", key): key for key, data in toy_data.items()}
        self.toy_names = sorted(self.toy_key_map.keys())
        self.toy_combobox = ttk.Combobox(input_frame, textvariable=self.selected_toy_name, values=self.toy_names, state="readonly", width=57)
        self.toy_combobox.grid(row=4, column=1, padx=5, pady=5, sticky=tk.EW)
        default_toy_key = os.getenv('TOY_KEY', 'lush4')
        default_name = next((name for name, key in self.toy_key_map.items() if key == default_toy_key), self.toy_names[0] if self.toy_names else "")
        if default_name:
            self.toy_combobox.set(default_name)

        # --- 按鈕區 ---
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=10)
        button_frame.columnconfigure(0, weight=1)

        self.process_button = ttk.Button(button_frame, text="開始處理", command=self.start_processing)
        self.process_button.grid(row=0, column=0, padx=10, pady=5, sticky=tk.EW)

        # --- 狀態/日誌顯示區 ---
        log_frame = ttk.LabelFrame(main_frame, text="處理狀態與日誌", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- 狀態管理 ---
        self.processing_thread = None
        self.status_queue = queue.Queue()

        # Initial button state update
        self.update_button_states()


    # --- 文件選擇方法 ---
    def select_video_file(self):
        filepath = filedialog.askopenfilename(title="選擇視訊檔 (MP4)", filetypes=[("MP4 檔案", "*.mp4"), ("所有檔案", "*.*")])
        if filepath:
            self.video_path.set(filepath)
            self.audio_path.set("") # Clear audio if video is selected
            self.srt_path.set("")   # Clear SRT if video is selected
            self.log_message(f"INFO: 已選擇視訊檔案: {filepath}")
            self.update_button_states()

    def select_audio_file(self):
        filepath = filedialog.askopenfilename(title="選擇音訊檔 (MP3)", filetypes=[("MP3 檔案", "*.mp3"), ("所有檔案", "*.*")])
        if filepath:
            self.audio_path.set(filepath)
            self.video_path.set("") # Clear video
            self.srt_path.set("")   # Clear SRT
            self.log_message(f"INFO: 已選擇音訊檔案: {filepath}")
            self.update_button_states()

    def select_srt_file(self):
        filepath = filedialog.askopenfilename(title="選擇字幕檔 (SRT)", filetypes=[("SRT 檔案", "*.srt"), ("所有檔案", "*.*")])
        if filepath:
            self.srt_path.set(filepath)
            self.video_path.set("") # Clear video
            self.audio_path.set("") # Clear audio
            self.log_message(f"INFO: 已選擇字幕檔案: {filepath}")
            self.update_button_states()


    # --- 按鈕命令 ---
    def start_processing(self):
        """統一的處理入口，自動判斷當前狀態並執行相應步驟"""
        toy_key = self.toy_key_map.get(self.selected_toy_name.get())
        if not toy_key:
            messagebox.showwarning("選擇錯誤", "請選擇一個目標玩具型號。")
            return

        # --- 自動判斷當前狀態並執行相應步驟 ---
        audio_input = self.audio_path.get()
        srt_input = self.srt_path.get()
        video_input = self.video_path.get()
        url_input = self.ph_url.get()

        if audio_input and os.path.exists(audio_input):
            # 如果有音訊檔案，先轉錄
            self.log_message(f"INFO: 檢測到音訊輸入 '{os.path.basename(audio_input)}'，將先執行轉錄再分析。")
            self._start_task(self.process_button, transcribe_thread_func, audio_input)
        elif srt_input and os.path.exists(srt_input):
            # 如果有SRT檔案，直接分析
            self.log_message(f"INFO: 檢測到 SRT 輸入 '{os.path.basename(srt_input)}'，將直接執行分析。")
            try:
                with open(srt_input, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                if not srt_content:
                    messagebox.showwarning("檔案錯誤", f"選擇的 SRT 文件 '{srt_input}' 為空。")
                    return
                self._start_task(self.process_button, analyze_thread_func, srt_content, srt_input, toy_key)
            except Exception as e:
                messagebox.showerror("讀取錯誤", f"讀取 SRT 文件失敗:\n{e}")
                logger.error(f"讀取 SRT 失敗: {traceback.format_exc()}")
        elif video_input and os.path.exists(video_input):
            # 如果有視訊檔案，先提取音訊再轉錄
            self.log_message(f"INFO: 檢測到視訊輸入 '{os.path.basename(video_input)}'，將先提取音訊再轉錄分析。")
            try:
                import subprocess
                audio_path = os.path.join(DOWNLOAD_DIR, f"{os.path.splitext(os.path.basename(video_input))[0]}.mp3")
                subprocess.run(['ffmpeg', '-i', video_input, '-vn', '-acodec', 'libmp3lame', audio_path], check=True)
                self.audio_path.set(audio_path)
                self.log_message(f"INFO: 音訊提取完成，開始轉錄...")
                self._start_task(self.process_button, transcribe_thread_func, audio_path)
            except Exception as e:
                messagebox.showerror("音訊提取錯誤", f"從視訊提取音訊失敗:\n{e}")
                logger.error(f"音訊提取失敗: {traceback.format_exc()}")
        elif url_input and url_input.startswith("http"):
            # 如果有網址，先下載再處理
            self.log_message(f"INFO: 檢測到網址輸入，將開始下載並處理...")
            self._start_task(self.process_button, download_extract_thread_func, url_input)
        else:
            messagebox.showwarning("缺少輸入", "請提供以下任一輸入：\n1. 視訊檔案\n2. 音訊檔案\n3. 字幕檔案\n4. 有效的網址")

    def _start_task(self, button, target_func, *args):
        """通用啟動執行緒的內部方法"""
        self._set_all_buttons_state(tk.DISABLED)

        # Clear subsequent results based on which function is being called
        if target_func == download_extract_thread_func:
            self.audio_path.set("")
            self.srt_path.set("")
            self.analysis_result_path.set("")
        elif target_func == transcribe_thread_func:
            self.srt_path.set("")
            self.analysis_result_path.set("")
        elif target_func == analyze_thread_func:
            self.analysis_result_path.set("")

        self.log_message(f"INFO: 正在啟動 {target_func.__name__}...")
        self.processing_thread = threading.Thread(
            target=target_func,
            args=args + (self.status_queue,),
            daemon=True
        )
        self.processing_thread.start()
        self.root.after(100, self.check_queue)

    def _set_all_buttons_state(self, state):
        """啟用或禁用主要操作按鈕"""
        try:
            self.process_button.config(state=state)
        except: pass
        # Always update based on inputs if enabling
        if state == tk.NORMAL:
            self.update_button_states()

    def update_button_states(self):
        """根據輸入更新按鈕啟用狀態"""
        if self.processing_thread and self.processing_thread.is_alive():
            self.process_button.config(state=tk.DISABLED)
        else:
            # Enable button if any valid input is present
            has_valid_input = (
                (self.audio_path.get() and os.path.exists(self.audio_path.get())) or
                (self.srt_path.get() and os.path.exists(self.srt_path.get())) or
                (self.video_path.get() and os.path.exists(self.video_path.get())) or
                (self.ph_url.get() and self.ph_url.get().startswith("http"))
            )
            self.process_button.config(state=tk.NORMAL if has_valid_input else tk.DISABLED)

    def log_message(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def check_queue(self):
        """檢查執行緒隊列中的訊息並更新 UI"""
        process_ended = False
        try:
            while True:
                message = self.status_queue.get_nowait()

                # Handle process completion/failure flags
                if message in ["DOWNLOAD_EXTRACT_COMPLETE", "DOWNLOAD_EXTRACT_FAILED",
                               "TRANSCRIBE_COMPLETE", "TRANSCRIBE_FAILED",
                               "ANALYZE_COMPLETE", "ANALYZE_FAILED"]:
                    log_prefix = "✅" if "COMPLETE" in message else "❌"
                    step_name = message.split("_")[0].capitalize()
                    status = "完成" if "COMPLETE" in message else "失敗"
                    self.log_message(f"{log_prefix} {step_name} 步驟 {status}！")
                    process_ended = True # Mark that *a* process ended

                # Handle results
                elif message.startswith("RESULT_AUDIO_PATH:"):
                    self.audio_path.set(message.split(":", 1)[1])
                    self.log_message(f"音訊路徑已更新: {self.audio_path.get()}")
                elif message.startswith("RESULT_SRT_PATH:"):
                    self.srt_path.set(message.split(":", 1)[1])
                    self.log_message(f"字幕路徑已更新: {self.srt_path.get()}")
                elif message.startswith("RESULT_SRT_CONTENT:"):
                    # Store content for potential analysis chain
                    self.srt_content_for_analysis = message.split(":", 1)[1]
                    # --- CHAINING LOGIC for Button 2 ---
                    # If transcription just finished successfully, trigger analysis
                    if not process_ended: # Avoid double triggering if already marked ended
                         toy_key = self.toy_key_map.get(self.selected_toy_name.get())
                         if toy_key and self.srt_content_for_analysis:
                              self.log_message("INFO: 自動接續執行內容分析...")
                              # No need to call _start_task again, just start the new thread
                              # Re-disable buttons as a new task starts
                              self._set_all_buttons_state(tk.DISABLED)
                              self.processing_thread = threading.Thread(
                                  target=analyze_thread_func,
                                  args=(self.srt_content_for_analysis, self.srt_path.get(), toy_key, self.status_queue),
                                  daemon=True
                              )
                              self.processing_thread.start()
                         else:
                              self.log_message("警告：無法自動接續分析（缺少玩具選擇或轉錄內容）。")
                              process_ended = True # Mark process as ended here
                elif message.startswith("RESULT_ANALYSIS_PATH:"):
                    self.analysis_result_path.set(message.split(":", 1)[1])
                    self.log_message(f"分析結果路徑: {self.analysis_result_path.get()}")
                else:
                    self.log_message(message) # Display general status/error messages

        except queue.Empty:
            pass # No messages in queue
        finally:
            # Keep checking if the thread is alive
            if self.processing_thread and self.processing_thread.is_alive():
                 self.root.after(100, self.check_queue)
            else:
                 # Thread finished (or never started), update button states
                 self.update_button_states()


# --- 啟動應用程式 ---
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()