import time
import json
import os
import datetime
import sys
from wifi_utils import is_connected, connect_to_wifi
from plyer import notification
from PIL import Image
import pystray
from threading import Thread

CONFIG_FILE = "user_settings.json"
PROFILE_FILE = "wifi_profiles.json"
NOTIFY_TIMEOUT = 1.3     # 单位：秒

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

def send_notification(title, message):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "wifi.ico")
        icon = icon_path if os.path.exists(icon_path) else None

        notification.notify(
            title=title,
            message=message,
            app_name="智能联网",
            timeout=NOTIFY_TIMEOUT,
            app_icon=icon
        )
    except Exception as e:
        log(f"⚠️ 发送通知失败: {e}")

def load_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def monitor_network(ssid, password, check_interval=1800):
    while True:
        if not is_connected(target_ssid=ssid):
            log(f"⚠️ 当前未连接到 {ssid}，正在尝试重新连接...")
            success = connect_to_wifi(ssid, password)

            if success and is_connected(target_ssid=ssid):
                msg = f"✅ 已成功连接到 {ssid}"
                log(msg)
                send_notification("网络已恢复", msg)
            else:
                msg = f"❌ 无法连接到 {ssid}"
                log(msg)
                send_notification("连接失败", msg)
        else:
            log(f"✅ 当前仍连接到 {ssid}")

        time.sleep(check_interval)

# ========== 托盘图标与退出逻辑 ==========

def stop_program(icon, item):
    log("🛑 用户点击退出，程序即将关闭")
    icon.stop()
    os._exit(0)  # 强制退出所有线程

def create_tray_icon():
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wifi.ico")
    image = Image.open(icon_path) if os.path.exists(icon_path) else Image.new('RGB', (64, 64), color='blue')

    menu = pystray.Menu(
        pystray.MenuItem('退出', stop_program)
    )

    tray_icon = pystray.Icon("Wi-Fi Monitor", image, "Wi-Fi 自动连接工具", menu)
    tray_icon.run()

def run_daemon():
    profiles = load_profiles()
    settings = load_settings()

    default_ssid = profiles.get("default")
    monitor_enabled = settings.get("monitor_enabled") == "是"

    if monitor_enabled and default_ssid in profiles:
        password = profiles[default_ssid]
        log(f"启动对 {default_ssid} 的监护")

        # 启动托盘图标
        Thread(target=create_tray_icon, daemon=True).start()

        # 开始监控网络
        monitor_network(default_ssid, password)

    else:
        log("监护模式未启用，仅尝试连接一次默认网络")

        if not default_ssid:
            log("❌ 没有设置默认网络，程序退出")
            sys.exit(1)

        if default_ssid in profiles:
            password = profiles[default_ssid]

            if is_connected(target_ssid=default_ssid):
                log(f"✅ 已经连接到 {default_ssid}，程序退出")
                sys.exit(0)

            log(f"尝试连接到 {default_ssid}")
            success = connect_to_wifi(default_ssid, password)

            if success and is_connected(target_ssid=default_ssid):
                msg = f"✅ 成功连接到 {default_ssid}"
                log(msg)
                send_notification("网络已连接", msg)
                sys.exit(0)
            else:
                msg = f"❌ 无法连接到 {default_ssid}"
                log(msg)
                send_notification("连接失败", msg)
                sys.exit(1)
        else:
            log(f"❌ 配置文件中不存在默认网络 {default_ssid}")
            sys.exit(1)

if __name__ == "__main__":
    print("启动后台守护进程...")
    run_daemon()