import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk 
import tkinter.font as tkFont 
import os
import subprocess
import re
import tempfile
import sys
from pathlib import Path 
import time 
import threading 
import requests 
import json 

# *** V0.1.6: การจัดการ Import Error ที่อาจทำให้โปรแกรมเด้งทันที ***
try:
    from pytubefix import YouTube
except ImportError:
    print("\n[CRITICAL ERROR] ไม่พบไลบรารี 'pytubefix' กรุณาติดตั้งโดยใช้: pip install pytubefix\\n")
    if tk._default_root:
        messagebox.showerror("Import Error", "ไม่พบไลบรารี 'pytubefix' กรุณาติดตั้งโดยใช้: pip install pytubefix")
    sys.exit(1) 

# *** Font Configuration (V0.5.3: Font Upgrade) ***
DEFAULT_FONT_NAME = "Leelawadee UI" 
TITLE_FONT_SIZE = 12
BODY_FONT_SIZE = 10

# A. ตัวแปรเวอร์ชันและชื่อนักพัฒนา (V0.6.3)
CODE_VERSION = "Loli YTDownloader V0.6.3" # <<< อัปเดตเป็น V0.6.3
DEVELOPER_NAME = "Nakano Tabasa"

# V0.6.3: Update Configuration (Fixed GitHub URL)
# *** URL สำหรับดึงไฟล์ JSON จาก Repository ของคุณ ***
GITHUB_UPDATE_JSON_URL = "https://raw.githubusercontent.com/shiawasenanami/Loli-YTDownloder/main/latest_version.json" 

DEV_PASSWORD = "lolinakano001"   # รหัสผ่านผู้พัฒนาสำหรับเข้าถึง Beta

# V0.5.2: FFMPEG Fixed Path Configuration
FFMPEG_DIR = r"C:\Users\shiaw\Desktop\LoliYTDownloader\database"
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFMPEG_AVAILABLE = False 

# ตัวแปร GUI หลัก
download_folder = None 
download_mode = None 
video_format_choice = None 
audio_format_choice = None
video_format_frame = None 
audio_format_frame = None 
# V0.5.5: ตัวแปร Progress Bar
main_progressbar = None 

# V0.2.7 PATCH: กำหนดค่าเริ่มต้นสำหรับ Download Folder ไปที่ Desktop
DEFAULT_DOWNLOAD_FOLDER = str(Path.home() / "Desktop" / "LoliDownload") 

# B. ฟังก์ชันตรวจสอบ FFMPEG (ไม่เปลี่ยนแปลง)
def check_ffmpeg_encoders():
    """ตรวจสอบว่า ffmpeg.exe อยู่ใน Fixed Path ที่ผู้ใช้กำหนดหรือไม่"""
    global FFMPEG_AVAILABLE
    if os.path.exists(FFMPEG_EXE):
        FFMPEG_AVAILABLE = True
    else:
        FFMPEG_AVAILABLE = False

# C. ฟังก์ชันช่วย: จัดการชื่อไฟล์ซ้ำ (ไม่เปลี่ยนแปลง)
def get_non_conflicting_path(original_path):
    """Generates a non-conflicting path by appending a number if the file exists."""
    if not os.path.exists(original_path):
        return original_path
        
    base, ext = os.path.splitext(original_path)
    counter = 1
    while True:
        new_path = f"{base} ({counter}){ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

# D. ฟังก์ชันเลือกโฟลเดอร์ (ไม่เปลี่ยนแปลง)
def browse_folder():
    """เปิดกล่องโต้ตอบให้ผู้ใช้เลือกโฟลเดอร์สำหรับบันทึกไฟล์"""
    global download_folder, folder_label
    
    folder_selected = filedialog.askdirectory(initialdir=download_folder)
    
    if folder_selected:
        download_folder = folder_selected 
        folder_label.config(text=f"📂 โฟลเดอร์ที่เลือก: {download_folder}")
    else:
        folder_label.config(text=f"📂 โฟลเดอร์ที่เลือก: {download_folder}")

# E. ฟังก์ชัน Callback สำหรับแสดงความคืบหน้า (ไม่เปลี่ยนแปลง)
def on_progress(stream, chunk, bytes_remaining):
    """Callback function ที่ Pytube เรียกใช้เมื่อดาวน์โหลดแต่ละก้อน พร้อมอัปเดต Progressbar"""
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    
    global progress_label, root, main_progressbar
    
    # 1. Update Progressbar
    if main_progressbar:
        main_progressbar['value'] = percentage_of_completion
    
    # 2. Update Label
    progress_label.config(text=f"📈 ดาวน์โหลด: {percentage_of_completion:.2f}%")
    root.update()

# F. ฟังก์ชันรวมไฟล์ภาพและเสียงด้วย FFMPEG (ไม่เปลี่ยนแปลง)
def combine_files(video_path, audio_path, output_path, output_format="mp4"):
    """ใช้ FFMPEG เพื่อรวมไฟล์วิดีโอและไฟล์เสียงเข้าด้วยกัน โดยใช้ FFMPEG_EXE (Fixed Path)"""
    global progress_label, root, messagebox, FFMPEG_EXE
    command_to_run = None 

    if output_format.lower() == "mov":
        progress_label.config(text="⚙️ กำลังแปลง MOV ด้วย **CPU (libx264)**...", fg="blue")
        root.update()
        
        command_to_run = [
            FFMPEG_EXE, '-i', video_path, '-i', audio_path, 
            '-c:v', 'libx264',      
            '-preset', 'veryfast',  
            '-crf', '23',           
            '-pix_fmt', 'yuv444p', 
            '-c:a', 'aac',          
            '-b:a', '192k',         
            '-movflags', 'faststart', 
            output_path
        ]
    else: 
        progress_label.config(text="🔗 กำลังรวมไฟล์ (Stream Copy)...", fg="purple")
        command_to_run = [
            FFMPEG_EXE, 
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy', 
            '-c:a', 'copy', 
            output_path
        ]
        
    try:
        subprocess.run(command_to_run, check=True, capture_output=True, text=True, timeout=1800, encoding='utf-8') 
        return True

    except subprocess.CalledProcessError as e:
        print(f"FFMPEG Error (Process Failed): {e.stderr}")
        messagebox.showerror("FFMPEG Error", f"ไม่สามารถรวม/แปลงไฟล์ได้! \nข้อผิดพลาด (Stderr): {e.stderr}")
        return False
    except FileNotFoundError:
        messagebox.showerror("FFMPEG Error", f"❌ ไม่พบไฟล์ 'ffmpeg.exe' ที่: \n{FFMPEG_DIR}\nกรุณาตรวจสอบว่าพาธถูกต้องและไฟล์อยู่ครบถ้วน")
        return False
    except subprocess.TimeoutExpired:
        messagebox.showerror("FFMPEG Error", "การรวม/แปลงไฟล์ใช้เวลานานเกินไปและถูกยกเลิก (Timeout)")
        return False


# G. ฟังก์ชันหลัก: ดาวน์โหลดวิดีโอ/เสียง (ไม่เปลี่ยนแปลง)
def download_task(url, mode, selected_video_format, selected_audio_format):
    """ฟังก์ชันจัดการการดาวน์โหลดหลัก พร้อมจัดการ Progress Bar"""
    
    global download_folder, status_label, progress_label, root, temp_dir, FFMPEG_EXE, main_progressbar
    
    if mode == 0: # Video
        sub_folder = "Videos" 
        file_extension = "." + selected_video_format
        download_type_name = f"วิดีโอ ({selected_video_format.upper()})"
    elif mode == 1: # Music
        sub_folder = "Music"
        file_extension = "." + selected_audio_format
        download_type_name = f"เพลง ({selected_audio_format.upper()})"
    else:
        sub_folder = "Others" 
        file_extension = ".mp4" 
        download_type_name = "ไฟล์"

    final_download_path = os.path.join(download_folder, sub_folder)
    os.makedirs(final_download_path, exist_ok=True)
    temp_dir = tempfile.gettempdir() 
    
    def sanitize_filename(title):
        return re.sub(r'[\\/:*?"<>|]', '', title)
    
    # V0.5.5: Show Progressbar and reset value to 0
    if main_progressbar:
        if not main_progressbar.winfo_ismapped():
            main_progressbar.grid(row=8, column=0, sticky='ew', padx=20, pady=2) 
        main_progressbar['value'] = 0

    try:
        status_label.config(text="⏳ กำลังค้นหาและเชื่อมต่อ...", fg="blue")
        progress_label.config(text="") 
        root.update()

        yt = YouTube(url, on_progress_callback=on_progress)
        safe_title = sanitize_filename(yt.title)
        
        # 2. ตรวจสอบและจัดการไฟล์ซ้ำก่อนเริ่มดาวน์โหลดจริง
        intended_final_path = os.path.join(final_download_path, f"{safe_title}{file_extension}")
        final_output_path = intended_final_path
        
        if os.path.exists(intended_final_path):
            conflict_message = (
                f"🚨 พบไฟล์ชื่อ '{os.path.basename(intended_final_path)}' ซ้ำในโฟลเดอร์!\n"
                "คุณต้องการทำอย่างไร?"
            )
            
            user_choice = messagebox.askyesnocancel(
                "🚨 ไฟล์ซ้ำกัน!", 
                conflict_message, 
                default=messagebox.NO, 
                icon=messagebox.WARNING,
                detail="ใช่ (Yes): เขียนทับไฟล์เดิม\nไม่ (No): เปลี่ยนชื่อไฟล์ (No): เพิ่มหมายเลข)\nยกเลิก (Cancel): ข้ามการดาวน์โหลดนี้"
            )
            
            if user_choice is None: # Cancel (Skip)
                status_label.config(text=f"⏩ ยกเลิกการดาวน์โหลด {yt.title}", fg="orange")
                progress_label.config(text="")
                return # Exit on skip
            
            if user_choice is False: # No (Rename)
                final_output_path = get_non_conflicting_path(intended_final_path)
                status_label.config(text=f"🔄 เปลี่ยนชื่อไฟล์เป็น: {os.path.basename(final_output_path)}", fg="blue")
                root.update()


        # --- LOGIC การดาวน์โหลดวิดีโอ ---
        if mode == 0: 
            
            video_stream = yt.streams.filter(only_video=True).order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not video_stream or not audio_stream:
                 status_label.config(text="❌ ไม่พบ Stream ภาพหรือเสียงคุณภาพสูงสำหรับวิดีโอนี้", fg="red")
                 return
                 
            video_temp_path = os.path.join(temp_dir, f"{safe_title}_video.mp4")
            audio_temp_path = os.path.join(temp_dir, f"{safe_title}_audio.mp4")
            
            status_label.config(text=f"⬇️ ดาวน์โหลดภาพ ({video_stream.resolution})...", fg="blue")
            video_stream.download(output_path=temp_dir, filename=f"{safe_title}_video.mp4")

            status_label.config(text=f"⬇️ ดาวน์โหลดเสียง ({audio_stream.abr})...", fg="blue")
            audio_stream.download(output_path=temp_dir, filename=f"{safe_title}_audio.mp4")

            # 4. รวมไฟล์
            status_label.config(text="🔗 กำลังรวมและแปลงไฟล์ด้วย FFMPEG...", fg="purple")
            progress_label.config(text="") 
            root.update()
            
            if combine_files(video_temp_path, audio_temp_path, final_output_path, selected_video_format):
                 status_label.config(text=f"✅ ดาวน์โหลด{download_type_name} สำเร็จ!", fg="green")
            else:
                 status_label.config(text=f"❌ การรวม/แปลงไฟล์ล้มเหลว", fg="red")
                 
            # 5. ลบไฟล์ชั่วคราว
            if os.path.exists(video_temp_path): os.remove(video_temp_path)
            if os.path.exists(audio_temp_path): os.remove(audio_temp_path)
        
        # --- LOGIC การดาวน์โหลดเสียง (MP3/WAV/FLAC) ---
        elif mode == 1: 
            
            status_label.config(text=f"⬇️ กำลังดาวน์โหลด {download_type_name}: {yt.title}...", fg="blue")
            
            final_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if final_stream is None:
                 status_label.config(text=f"❌ ไม่พบ Stream เสียงที่เหมาะสม", fg="red")
                 progress_label.config(text="")
                 return
            
            # 1. ดาวน์โหลดไฟล์เสียงชั่วคราว (Always as m4a/webm)
            audio_temp_filename = f"{safe_title}_audio_temp.m4a"
            audio_temp_path = os.path.join(temp_dir, audio_temp_filename)
            final_stream.download(output_path=temp_dir, filename=audio_temp_filename)

            # 2. ตั้งค่า FFMPEG Command สำหรับแปลงไฟล์
            final_output_path = os.path.join(final_download_path, f"{safe_title}.{selected_audio_format}")
            final_output_path = get_non_conflicting_path(final_output_path)
            
            progress_label.config(text=f"⚙️ กำลังแปลงเป็น {selected_audio_format.upper()} ด้วย FFMPEG...", fg="blue")
            root.update()
            
            # FFMPEG commands for selected audio format (V0.5.7: Max quality MP3 320k)
            if selected_audio_format.lower() == "mp3":
                # Max quality MP3 (CBR 320k)
                audio_command = [FFMPEG_EXE, '-i', audio_temp_path, '-vn', '-c:a', 'libmp3lame', '-b:a', '320k', final_output_path]
            elif selected_audio_format.lower() == "wav":
                # WAV is already lossless 
                audio_command = [FFMPEG_EXE, '-i', audio_temp_path, '-vn', '-c:a', 'pcm_s16le', final_output_path]
            elif selected_audio_format.lower() == "flac":
                # FLAC is already lossless 
                audio_command = [FFMPEG_EXE, '-i', audio_temp_path, '-vn', '-c:a', 'flac', final_output_path]
            else: # Fallback to MP3
                 audio_command = [FFMPEG_EXE, '-i', audio_temp_path, '-vn', '-c:a', 'libmp3lame', '-b:a', '320k', final_output_path]


            try:
                subprocess.run(audio_command, check=True, capture_output=True, text=True, timeout=600, encoding='utf-8') 
                status_label.config(text=f"✅ ดาวน์โหลดและแปลงเป็น {download_type_name} สำเร็จ!", fg="green")
            except FileNotFoundError:
                status_label.config(text=f"❌ การแปลงไฟล์เสียงล้มเหลว: ไม่พบ FFMPEG.EXE!", fg="red")
                messagebox.showerror("FFMPEG Error", f"❌ ไม่พบไฟล์ 'ffmpeg.exe' ที่: \n{FFMPEG_DIR}\nกรุณาตรวจสอบว่าพาธถูกต้องและไฟล์อยู่ครบถ้วน")
            except Exception as e:
                status_label.config(text=f"❌ การแปลงไฟล์เสียงล้มเหลว!", fg="red")
                print(f"Audio conversion error: {e}")
            finally:
                if os.path.exists(audio_temp_path): os.remove(audio_temp_path)

        progress_label.config(text=f"ไฟล์บันทึกที่: {final_download_path}") 

    except Exception as e:
        status_label.config(text=f"❌ เกิดข้อผิดพลาดร้ายแรง: {type(e).__name__}", fg="red")
        progress_label.config(text=f"รายละเอียด: {e}")
        print(f"*** CRITICAL DOWNLOAD ERROR DETECTED ***: {e}")
        
    finally:
        # V0.5.5: Hide Progressbar regardless of success, failure, or skip.
        if main_progressbar and main_progressbar.winfo_ismapped():
            main_progressbar.grid_forget()
        if main_progressbar:
            main_progressbar['value'] = 0 # Reset value


def check_download_thread_completion(thread):
    """ฟังก์ชันที่ใช้ติดตามว่า Download Thread จบการทำงานหรือยัง"""
    global download_button, root
    if thread.is_alive():
        root.after(100, check_download_thread_completion, thread)
    else:
        download_button.config(state=tk.NORMAL)


def download_video():
    """ฟังก์ชันจัดการการเริ่มต้นดาวน์โหลดใน Thread แยกเพื่อไม่ให้โปรแกรมค้าง"""
    global url_entry, download_mode, video_format_choice, audio_format_choice, download_button, status_label, FFMPEG_AVAILABLE
    
    if not FFMPEG_AVAILABLE:
        status_label.config(text="❌ FFMPEG ไม่พร้อมใช้งาน! กรุณาตรวจสอบพาธ", fg="red")
        messagebox.showerror("FFMPEG Error", f"❌ FFMPEG ไม่พร้อมใช้งาน! โปรดตรวจสอบว่าไฟล์ 'ffmpeg.exe' อยู่ที่: \n{FFMPEG_DIR}")
        return
        
    url = url_entry.get()
    mode = download_mode.get() 
    selected_video_format = video_format_choice.get() 
    selected_audio_format = audio_format_choice.get() 
    
    if not url: 
        status_label.config(text="⚠️ กรุณาใส่ลิงก์ก่อน", fg="orange")
        return
        
    download_button.config(state=tk.DISABLED)
    
    thread = threading.Thread(target=download_task, args=(url, mode, selected_video_format, selected_audio_format))
    thread.start()
    
    global root
    root.after(100, check_download_thread_completion, thread)

# H. ฟังก์ชันแสดงข้อมูล (V0.6.3 - อัปเดต Log)
def show_about_info():
    """แสดงข้อมูลเกี่ยวกับนักพัฒนาและประวัติเวอร์ชัน"""
    global CODE_VERSION, DEVELOPER_NAME, FFMPEG_DIR, DEV_PASSWORD
    about_text = f"""
    --- **{CODE_VERSION}** ---
    
    **นักพัฒนา:** {DEVELOPER_NAME}
    
    ======================================
    **✨ What's New in {CODE_VERSION}:**
    ======================================
    
    * **Fixed GitHub URL (V0.6.3):** แก้ไขและกำหนด URL การตรวจสอบอัปเดต GitHub ให้ชี้ไปที่:
      `{GITHUB_UPDATE_JSON_URL}`
      (ต้องสร้างไฟล์ `latest_version.json` ใน Root ของ Repository)
      
    * **GitHub Update Integration (V0.6.2):** ปรับปรุงฟังก์ชันอัปเดตให้เชื่อมต่อกับ GitHub URL เพื่อตรวจสอบเวอร์ชันล่าสุด
    * **New Dev Password (V0.6.1):** เปลี่ยนรหัสผ่านสำหรับเข้าถึงการตรวจสอบอัปเดต Beta เป็น **`{DEV_PASSWORD}`**
    
    ======================================
    **📜 ประวัติการอัปเดต (Log History):**
    ======================================
    
    **🎨 V0.5.9:** **Refined UI Layout**
    * **Layout:** ปรับปรุง Layout ของส่วน Mode และ Format ให้อยู่ใกล้กันและอยู่กึ่งกลาง (Centered)
    
    -------------------------------------------
    """
    messagebox.showinfo("ℹ️ ข้อมูลเกี่ยวกับโปรแกรม", about_text)

# *** ฟังก์ชันใหม่: เพื่อเปิด URL ในเบราว์เซอร์ให้ผู้ใช้ดาวน์โหลดเอง ***
def open_url_in_browser(url):
    """เปิดลิงก์ในเบราว์เซอร์เริ่มต้นของผู้ใช้"""
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as e:
        messagebox.showerror("Error", f"ไม่สามารถเปิดเบราว์เซอร์ได้: {e}")

# I. ฟังก์ชันตรวจสอบอัปเดต (V0.6.2: GitHub Integration)
def check_for_updates_thread(is_beta_check=False):
    """ฟังก์ชันหลักสำหรับตรวจสอบอัปเดตจาก GitHub ใน Thread แยก"""
    
    global status_label, progress_label, root, CODE_VERSION, GITHUB_UPDATE_JSON_URL
    
    status_label.config(text="🔍 กำลังเชื่อมต่อ GitHub เพื่อตรวจสอบเวอร์ชันล่าสุด...", fg="orange")
    progress_label.config(text="") 
    root.update()
    
    try:
        # 1. ดึงข้อมูล JSON จาก GitHub
        response = requests.get(GITHUB_UPDATE_JSON_URL, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        update_info = response.json()
        
    except requests.exceptions.RequestException as e:
        status_label.config(text="❌ ตรวจสอบอัปเดตล้มเหลว: ไม่พบ GitHub URL หรือไม่มีอินเทอร์เน็ต", fg="red")
        progress_label.config(text=f"ข้อผิดพลาด: {e}")
        return

    # 2. เปรียบเทียบเวอร์ชัน
    current_version_str = CODE_VERSION.split()[-1] 
    
    if is_beta_check:
        LATEST_VERSION = update_info.get("beta_version", "N/A")
        UPDATE_URL = update_info.get("beta_url", "")
        version_type = "Beta (Dev)"
    else:
        LATEST_VERSION = update_info.get("stable_version", "N/A")
        UPDATE_URL = update_info.get("stable_url", "")
        version_type = "Stable (Public)"
    
    
    # Simple version comparison (V0.6.2 > V0.6.1)
    if LATEST_VERSION == "N/A" or LATEST_VERSION == current_version_str:
        status_label.config(text=f"✅ โปรแกรมเป็นเวอร์ชันล่าสุด ({version_type}) แล้ว!", fg="green")
        progress_label.config(text=f"เวอร์ชันปัจจุบัน: {current_version_str}")
        
    else:
        status_label.config(text=f"🔥 พบเวอร์ชันใหม่ {version_type}: {LATEST_VERSION}!", fg="red")
        progress_label.config(text=f"เวอร์ชันปัจจุบัน: {current_version_str}")
        
        # 3. ให้ผู้ใช้ตัดสินใจอัปเดต
        if messagebox.askyesno("อัปเดตโปรแกรม", 
                               f"มีเวอร์ชันใหม่ ({LATEST_VERSION})! \nต้องการเปิดหน้าดาวน์โหลดเพื่ออัปเดตตอนนี้หรือไม่?\n\n(ปัจจุบัน: {current_version_str})"):
            
            if UPDATE_URL:
                 status_label.config(text="🌐 กำลังเปิดหน้าดาวน์โหลดในเบราว์เซอร์...", fg="purple")
                 progress_label.config(text=UPDATE_URL)
                 root.update()
                 open_url_in_browser(UPDATE_URL)
            else:
                 messagebox.showinfo("ข้อมูล", "ไม่พบลิงก์อัปเดตในไฟล์ JSON")
                 status_label.config(text="❌ ไม่พบลิงก์อัปเดต", fg="red")
    

def start_update_in_thread(is_beta_check=False):
    """เริ่มต้นการตรวจสอบอัปเดตใน Thread แยก เพื่อไม่ให้ GUI ค้าง"""
    thread = threading.Thread(target=check_for_updates_thread, args=(is_beta_check,))
    thread.start()

def ask_for_dev_password():
    """Shows a dialog to ask for the Developer Password before starting Beta check."""
    global root, DEV_PASSWORD, DEFAULT_FONT_NAME, BODY_FONT_SIZE
    
    # 1. สร้างหน้าต่าง Toplevel (Dialog)
    dialog = tk.Toplevel(root)
    dialog.title("🔒 รหัสผ่าน Dev")
    dialog.geometry("300x150")
    dialog.transient(root) 
    dialog.grab_set() # Block main window
    
    dialog.grid_columnconfigure(0, weight=1)
    
    # 2. ข้อความแนะนำ
    tk.Label(dialog, text="สำหรับตรวจสอบอัปเดต Beta เท่านั้น", 
             font=(DEFAULT_FONT_NAME, BODY_FONT_SIZE)).grid(row=0, column=0, pady=10)
             
    # 3. ช่องใส่รหัสผ่าน
    password_entry = tk.Entry(dialog, show="*", width=30, font=(DEFAULT_FONT_NAME, BODY_FONT_SIZE))
    password_entry.grid(row=1, column=0, pady=5, padx=20, sticky='ew')
    
    def check_password_and_start():
        if password_entry.get() == DEV_PASSWORD:
            dialog.destroy()
            start_update_in_thread(is_beta_check=True)
        else:
            messagebox.showerror("รหัสผ่านไม่ถูกต้อง", "❌ รหัสผ่านผู้พัฒนาไม่ถูกต้อง")
            password_entry.delete(0, tk.END) 
            # Focus back to dialog/entry
            dialog.lift()
            password_entry.focus_set()

    # 4. ปุ่มยืนยัน
    confirm_button = tk.Button(dialog, text="ยืนยัน", command=check_password_and_start, 
                               bg="#008CBA", fg="white", font=(DEFAULT_FONT_NAME, BODY_FONT_SIZE, "bold"))
    confirm_button.grid(row=2, column=0, pady=10)
    
    # 5. Event Binding (Enter key)
    password_entry.bind('<Return>', lambda event=None: check_password_and_start())
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy) 
    password_entry.focus_set() # Set initial focus
    root.wait_window(dialog) # Wait until dialog is closed


# J. การตั้งค่า Menu Bar (ไม่เปลี่ยนแปลง)
def setup_menu_bar():
    """สร้างและตั้งค่า Menu Bar พร้อมกำหนด Font"""
    global root, DEFAULT_FONT_NAME, BODY_FONT_SIZE
    
    menu_font = (DEFAULT_FONT_NAME, BODY_FONT_SIZE)
    
    menubar = tk.Menu(root, font=menu_font) 
    root.config(menu=menubar)
    
    # 1. ไฟล์เมนู
    file_menu = tk.Menu(menubar, tearoff=0, font=menu_font)
    menubar.add_cascade(label="ไฟล์", menu=file_menu)
    file_menu.add_command(label="เลือกโฟลเดอร์บันทึก", command=browse_folder)
    file_menu.add_separator()
    file_menu.add_command(label="ออก", command=root.quit)
    
    # 2. อัปเดตเมนู (V0.6.0: Split Update)
    update_menu = tk.Menu(menubar, tearoff=0, font=menu_font)
    menubar.add_cascade(label="อัปเดต", menu=update_menu)
    # Stable Check: No password needed
    update_menu.add_command(label="ตรวจสอบอัปเดต Stable", command=lambda: start_update_in_thread(is_beta_check=False))
    # Beta Check: Password needed
    update_menu.add_command(label="ตรวจสอบอัปเดต Beta (Dev Only)", command=ask_for_dev_password)
    
    # 3. เกี่ยวกับเมนู 
    help_menu = tk.Menu(menubar, tearoff=0, font=menu_font)
    menubar.add_cascade(label="เกี่ยวกับ", menu=help_menu)
    help_menu.add_command(label="ข้อมูล & ประวัติเวอร์ชัน", command=show_about_info)


# K. ฟังก์ชันควบคุมการซ่อน/แสดงรูปแบบไฟล์ (ไม่เปลี่ยนแปลง)
def update_format_visibility(*args):
    """Shows the appropriate format selection frame (Video or Audio) based on the download_mode."""
    global download_mode, video_format_frame, audio_format_frame
    
    if video_format_frame is None or audio_format_frame is None:
        return

    # V0.5.8: ใช้ grid/grid_forget แทน pack/pack_forget เพื่อให้เข้ากับระบบ Grid
    if download_mode.get() == 0:  # Video Mode
        # ใช้ grid เพื่อแสดงผล
        video_format_frame.grid(row=0, column=0, padx=10, sticky='n') 
        audio_format_frame.grid_forget()
    elif download_mode.get() == 1:  # Music Mode
        # ใช้ grid เพื่อแสดงผล
        audio_format_frame.grid(row=0, column=0, padx=10, sticky='n')
        video_format_frame.grid_forget()


# L. ส่วนของการสร้าง GUI ด้วย Tkinter และเริ่มโปรแกรม (ไม่เปลี่ยนแปลงในส่วน UI)
def start_application():
    """ฟังก์ชันหลักที่รัน GUI"""
    
    check_ffmpeg_encoders() 
    
    global root, CODE_VERSION, download_mode, video_format_choice, audio_format_choice, url_entry, download_button, status_label, progress_label, folder_label, DEFAULT_DOWNLOAD_FOLDER, video_format_frame, audio_format_frame, FFMPEG_AVAILABLE, FFMPEG_EXE, DEFAULT_FONT_NAME, TITLE_FONT_SIZE, BODY_FONT_SIZE, main_progressbar, download_folder

    # V0.5.6 FIX: กำหนดค่าเริ่มต้นให้ download_folder ก่อนเริ่มใช้งาน GUI
    if download_folder is None: 
         download_folder = DEFAULT_DOWNLOAD_FOLDER 

    # กำหนด Font Style สำหรับใช้ทั่วโปรแกรม
    title_font_style = (DEFAULT_FONT_NAME, TITLE_FONT_SIZE, "bold")
    body_font_style = (DEFAULT_FONT_NAME, BODY_FONT_SIZE)
    body_bold_font_style = (DEFAULT_FONT_NAME, BODY_FONT_SIZE, "bold")
    
    # 1. สร้างหน้าต่างหลัก
    root = tk.Tk()
    root.title(f"{CODE_VERSION}") 
    
    # V0.5.8: กำหนดขนาดเริ่มต้นและอนุญาตให้ยืดหยุ่น (Resizable)
    root.geometry("600x450") # Wide Default Size
    root.resizable(True, True) 

    setup_menu_bar() 

    # ปรับ Grid Configuration เพื่อให้ยืดหยุ่น
    root.grid_columnconfigure(0, weight=1) # คอลัมน์หลักยืดหยุ่นแนวกว้าง
    
    # กำหนด weight สำหรับแถว (Row 6 เป็น Spacer)
    for i in [0, 1, 2, 3, 4, 5, 7, 9, 10, 11]:
        root.grid_rowconfigure(i, weight=0)
    root.grid_rowconfigure(6, weight=1) # Row 6 เป็น Spacer หลัก

    # 2. สร้างองค์ประกอบ GUI (Widgets)
    current_row = 0
    
    # Row 0 (Instruction) - Centered
    instruction_label = tk.Label(root, text="**วางลิงก์ YouTube ที่นี่:**", font=title_font_style) 
    instruction_label.grid(row=current_row, column=0, pady=(15, 5), padx=20) 
    current_row += 1

    # Row 1 (URL Entry) - Stretches horizontally
    url_entry = tk.Entry(root, width=50, font=body_font_style) 
    url_entry.grid(row=current_row, column=0, pady=5, padx=20, sticky='ew') 
    current_row += 1

    # Row 2 (Mode and Format) - Centered Group 
    mode_format_frame = tk.Frame(root) 
    mode_format_frame.grid(row=current_row, column=0, pady=8) # No sticky='ew' -> Centered
    
    # --- โหมดดาวน์โหลด (ซ้าย) ---
    mode_frame = tk.Frame(mode_format_frame) 
    mode_frame.grid(row=0, column=0, padx=15, sticky='n') # Column 0, sticky='n'
    
    tk.Label(mode_frame, text="**โหมดดาวน์โหลด:**", font=body_bold_font_style).pack(anchor='w') 
    
    download_mode = tk.IntVar(value=0) # Default: Video (0)
    download_mode.trace_add("write", update_format_visibility) 

    tk.Radiobutton(mode_frame, text="วิดีโอ 🎥", variable=download_mode, 
                   value=0, font=body_font_style).pack(anchor='w') 
    tk.Radiobutton(mode_frame, text="เพลง 🎵", variable=download_mode, 
                   value=1, font=body_font_style).pack(anchor='w') 


    # --- Format Selection Container (ขวา) ---
    format_selection_frame = tk.Frame(mode_format_frame)
    format_selection_frame.grid(row=0, column=1, padx=15, sticky='n') # Column 1, sticky='n'
    
    # Video Format Frame 
    video_format_frame = tk.Frame(format_selection_frame)
    tk.Label(video_format_frame, text="**รูปแบบวิดีโอ:**", font=body_bold_font_style).pack(anchor='w') 
    VIDEO_FORMATS = ["mp4", "mkv", "mov"] 
    video_format_choice = tk.StringVar(value=VIDEO_FORMATS[0])
    format_menu_video = tk.OptionMenu(video_format_frame, video_format_choice, *VIDEO_FORMATS)
    format_menu_video.config(font=body_font_style, width=6) 
    format_menu_video.pack(anchor='w')

    # Audio Format Frame 
    audio_format_frame = tk.Frame(format_selection_frame)
    tk.Label(audio_format_frame, text="**รูปแบบเพลง:**", font=body_bold_font_style).pack(anchor='w') 
    AUDIO_FORMATS = ["mp3", "wav", "flac"]
    audio_format_choice = tk.StringVar(value=AUDIO_FORMATS[0])
    format_menu_audio = tk.OptionMenu(audio_format_frame, audio_format_choice, *AUDIO_FORMATS)
    format_menu_audio.config(font=body_font_style, width=6) 
    format_menu_audio.pack(anchor='w')

    current_row += 1 

    update_format_visibility() # Set initial visibility


    # Row 3 (Choose Folder Button) - Centered
    # V0.5.9: Change button color to Folder Yellow
    choose_folder_button = tk.Button(root, text="📁 **เลือกโฟลเดอร์บันทึกไฟล์**", command=browse_folder, 
                                     bg="#FFC300", fg="black", font=body_bold_font_style) 
    choose_folder_button.grid(row=current_row, column=0, pady=5, padx=20, ipadx=10, ipady=5)
    current_row += 1

    # Row 4 (Folder Label) - Stretches horizontally
    folder_label = tk.Label(root, text=f"📂 โฟลเดอร์ที่เลือก: {download_folder}", fg="gray", font=body_font_style) 
    folder_label.grid(row=current_row, column=0, pady=0, padx=20, sticky='ew') 
    current_row += 1

    # Row 5 (Download Button) - Centered
    download_button = tk.Button(root, text="⬇️ **เริ่มดาวน์โหลด**", command=download_video, 
                                bg="#ff0000", fg="white", font=title_font_style) 
    download_button.grid(row=current_row, column=0, pady=10, padx=20, ipadx=10, ipady=5) 
    current_row += 1
    
    # 3. สถานะ FFMPEG 
    if not FFMPEG_AVAILABLE:
        download_button.config(state=tk.DISABLED, text="❌ FFMPEG ไม่พร้อมใช้งาน! (ดูสถานะด้านล่าง)")
        status_text = f"❌ FFMPEG.EXE ไม่พบที่: {FFMPEG_EXE}"
        status_color = "red"
    else:
        status_text = "พร้อมทำงาน!"
        status_color = "green"

    # --- Row 6 เป็น Row ว่างสำหรับยืดหยุ่น (Spacer) ---
    current_row += 1 # Row 6 is the spacer with weight=1

    # Row 7 (Status Label) - Stretches horizontally
    status_label = tk.Label(root, text=status_text, fg=status_color, font=body_font_style) 
    status_label.grid(row=current_row, column=0, pady=5, padx=20, sticky='ew') 
    current_row += 1

    # Row 8 (Progress Bar) - Stretches horizontally (Managed dynamically)
    main_progressbar = ttk.Progressbar(root, orient='horizontal', mode='determinate', length=400, maximum=100, style='green.Horizontal.TProgressbar')
    style = ttk.Style()
    style.theme_use('default')
    style.configure("green.Horizontal.TProgressbar", background='#5cb85c', troughcolor='lightgray')
    # main_progressbar will be gridded in download_task

    # Row 9 (Progress Label) - Stretches horizontally
    progress_label = tk.Label(root, text="", fg="blue", font=body_bold_font_style) 
    progress_label.grid(row=current_row, column=0, pady=5, padx=20, sticky='ew') 
    current_row += 1

    # Row 10 (Footer Frame: Check Update Button) - Stretches horizontally
    footer_frame = tk.Frame(root) 
    footer_frame.grid(row=current_row, column=0, sticky='ew', padx=10, pady=5) 
    footer_frame.grid_columnconfigure(0, weight=1) 
    
    # About Button
    about_button = tk.Button(footer_frame, text="ℹ️ ข้อมูลโปรแกรม", command=show_about_info, 
                                    bg="#008CBA", fg="white", font=body_bold_font_style) 
    about_button.grid(row=0, column=1, sticky='e') 

    # --- Row 11 (Developer Info) ---
    current_row += 1 
    
    dev_info_text = f"Dev: {DEVELOPER_NAME} | Version: {CODE_VERSION}"
    footer_font_style = (DEFAULT_FONT_NAME, 9) 
    dev_info_label = tk.Label(root, text=dev_info_text, fg="gray", font=footer_font_style)
    dev_info_label.grid(row=current_row, column=0, pady=(0, 5), sticky='ew') 
    
    # 4. เริ่มต้น Loop หลักของ GUI
    root.mainloop()

# M. Main Execution Block (Protected)
if __name__ == '__main__':
    # *** V0.6.2: ต้องติดตั้งไลบรารี requests และ pytubefix ก่อนรัน ***
    try:
        # ตรวจสอบการ import requests ก่อนเริ่มโปรแกรมจริง
        import requests 
        # ... 
        start_application()
    except ImportError as e:
        print(f"\n[CRITICAL ERROR] ไม่พบไลบรารีที่จำเป็น: {e}\n")
        temp_root = tk.Tk()
        temp_root.withdraw() 
        messagebox.showerror(
            "❌ ข้อผิดพลาดร้ายแรงตอนเริ่มต้น", 
            f"โปรแกรมเด้งหายไป! \n\nสาเหตุ: ไม่พบไลบรารี 'requests' หรือ 'pytubefix' \n"
            "กรุณาติดตั้งโดยใช้: pip install requests pytubefix"
        )
        temp_root.destroy()
        sys.exit(1)
    except Exception as e:
        print(f"*** CRITICAL STARTUP ERROR DETECTED ***: {e}")
        # ... (แสดงข้อผิดพลาดอื่นๆ) ...
        sys.exit(1)