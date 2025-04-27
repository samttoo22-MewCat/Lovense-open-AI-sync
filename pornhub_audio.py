#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import phub
import logging
import traceback

# Get logger for this module
logger = logging.getLogger(__name__)

class PornhubAudioDownloader:
    def __init__(self, save_dir='downloads'):
        self.save_dir = save_dir
    
    def download_audio(self, url):
        """Downloads audio from a Pornhub URL.

        Args:
            url (str): The Pornhub video URL.

        Returns:
            str | None: The path to the downloaded MP3 file on success, None on failure.
        """
        try:
            # Ensure save directory exists before downloading
            os.makedirs(self.save_dir, exist_ok=True)
            logger.info(f"開始處理 Pornhub URL: {url}")
            
            # Initialize client here or ensure it's initialized
            client = phub.Client()
            
            # 獲取視頻
            video = client.get(url)
            if not video:
                logger.error("無法獲取視頻信息")
                return None
            
            # Use a safe filename based on the title
            safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_title: # Handle cases where title becomes empty
                 safe_title = f"video_{video.id or 'unknown'}"
            output_filename = f"{safe_title}.mp3"
            output_path = os.path.join(self.save_dir, output_filename)

            # Check if audio already exists
            if os.path.exists(output_path):
                logger.info(f"音頻文件已存在: {output_path}，跳過下載。")
                return output_path

            # 使用最低品質下載以節省流量 (phub library might not directly support quality selection in download)
            # The phub library's download usually gets the best available stream it finds.
            # We need a temporary video file to extract audio.
            temp_video_filename = f"video_{safe_title}.mp4"
            temp_video_path = os.path.join(self.save_dir, temp_video_filename)
            
            logger.info(f"開始下載視頻到臨時文件: {temp_video_path}")
            # download() returns the path where it saved the file
            downloaded_path = video.download(path=self.save_dir, filename=temp_video_filename, quality=phub.Quality.LOW) # Request low quality
            if not downloaded_path or not os.path.exists(downloaded_path):
                logger.error("視頻下載失敗或未找到下載的文件。")
                # Clean up potentially partially downloaded file
                if os.path.exists(temp_video_path): 
                    pass
                return None
                
            # Ensure the temp path is correct in case download changed it
            temp_video_path = downloaded_path

            # 提取音頻 (Requires ffmpeg to be installed and in PATH)
            # Use -vn to avoid video processing, -acodec copy if possible, or specify mp3 codec
            cmd = f'ffmpeg -i "{temp_video_path}" -vn -acodec libmp3lame -q:a 2 "{output_path}" -y'
            # Alternative (potentially faster if source audio is compatible): cmd = f'ffmpeg -i "{temp_video_path}" -vn -acodec copy "{output_path}" -y'
            
            logger.info("正在提取音頻...")
            exit_code = os.system(cmd)
            
            # 刪除臨時視頻文件
            logger.info(f"刪除臨時視頻文件: {temp_video_path}")
            if os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except OSError as remove_err:
                    logger.warning(f"無法刪除臨時文件 {temp_video_path}: {remove_err}")
            
            if exit_code == 0 and os.path.exists(output_path):
                logger.info(f"音頻下載並提取成功: {output_path}")
                return output_path # Return the path on success
            else:
                logger.error(f"音頻提取失敗 (ffmpeg exit code: {exit_code})")
                # Clean up failed output file if it exists
                if os.path.exists(output_path): 
                    try: os.remove(output_path) 
                    except OSError: pass
                return None # Return None on failure
                
        except ImportError:
            logger.error("缺少 'phub' 庫。請運行 'pip install phub'")
            return None
        except Exception as e:
            logger.error(f"下載或提取音頻過程中出錯: {str(e)}")
            traceback.print_exc()
            # Clean up temp/output files on unexpected error
            if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
                 try: os.remove(temp_video_path) 
                 except OSError: pass
            if 'output_path' in locals() and os.path.exists(output_path):
                 try: os.remove(output_path) 
                 except OSError: pass
            return None
