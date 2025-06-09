# wifi_utils.py

import subprocess
import os
import re
import json
import datetime
import time

PROFILE_PATH = os.path.join(os.getcwd(), "{}.xml")

def sanitize_ssid(ssid):
    """清理SSID中可能导致文件名错误的字符"""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", ssid)

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

def is_connected(target_ssid):
    try:
        output = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], stderr=subprocess.STDOUT)
        for encoding in ('utf-8', 'gbk'):
            try:
                output_str = output.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("无法识别的字符编码")

        for line in output_str.split('\n'):
            if "SSID" in line and "BSSID" not in line:
                current_ssid = line.strip().split(":")[1].strip()
                return current_ssid == target_ssid
        return False
    except Exception as e:
        log(f"❌ 检查网络状态失败: {e}")
        return False

def connect_to_wifi(ssid, password):
    safe_ssid = sanitize_ssid(ssid)
    profile_path = PROFILE_PATH.format(safe_ssid)

    config = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{safe_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""

    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            f.write(config)

        # 删除旧配置
        subprocess.run(["netsh", "wlan", "delete", "profile", f"name={safe_ssid}"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        # 添加新配置
        subprocess.run(["netsh", "wlan", "add", "profile", f"filename={profile_path}"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        # 断开当前连接
        subprocess.run(["netsh", "wlan", "disconnect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 尝试连接
        subprocess.run(["netsh", "wlan", "connect", f"name={safe_ssid}"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        # 等待连接完成
        for _ in range(10):
            if is_connected(target_ssid=ssid):
                return True
            time.sleep(1)
        return False

    except Exception as e:
        log(f"❌ 连接异常: {e}")
        return False
    finally:
        # 清理 XML 配置文件
        if os.path.exists(profile_path):
            os.remove(profile_path)

def load_wifi_profiles():
    PROFILE_FILE = "wifi_profiles.json"
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                default_ssid = data.get("default")
                if default_ssid and default_ssid in data:
                    return {"ssid": default_ssid, "password": data[default_ssid]}
                else:
                    raise ValueError("未设置默认网络或配置不完整")
            except Exception as e:
                log(f"❌ 加载配置失败: {e}")
                return {}
    else:
        log("⚠️ 配置文件不存在")
        return {}