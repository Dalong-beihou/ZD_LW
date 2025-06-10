import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import subprocess
import sys

# ====== 隐藏子进程窗口的函数（仅 Windows）======
def hide_subprocess_window():
    if sys.platform != 'win32':
        return

    original_popen = subprocess.Popen

    class HiddenWindowPopen(original_popen):
        def __init__(self, *args, **kwargs):
            kwargs['creationflags'] = kwargs.get(
                'creationflags', subprocess.CREATE_NO_WINDOW
            )
            super().__init__(*args, **kwargs)

    subprocess.Popen = HiddenWindowPopen

# 在程序开始时立即调用
hide_subprocess_window()
# ====== 隐藏窗口功能结束 ======

# 本地模块导入
try:
    from backend import monitor_network
except ImportError:
    monitor_network = None

PROFILE_FILE = "wifi_profiles.json"
CONFIG_FILE = "user_settings.json"  # 用户设置文件


def load_wifi_profiles():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict) and "default" in data:
                    return data
                elif isinstance(data, dict) and "ssid" in data:
                    return {"default": None, data["ssid"]: data["password"]}
                else:
                    return {}
            except Exception as e:
                print("解析配置文件失败:", e)
                return {}
    else:
        print("未找到配置文件")
        return {}


def save_profiles(profiles):
    with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
        output_data = {
            "default": profiles.get("default"),
            **{k: v for k, v in profiles.items() if k != "default"}
        }
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存配置到 {PROFILE_FILE}")


def update_profile_list(profile_combo, profiles):
    profile_combo['values'] = [k for k in profiles if k != "default"]
    if profile_combo['values']:
        profile_combo.current(0)


def update_default_combo(default_combo, profiles):
    profile_names = [k for k in profiles if k != "default"]
    default_ssid = profiles.get("default")

    default_combo['values'] = profile_names
    if default_ssid and default_ssid in profiles:
        default_combo.set(default_ssid)
    elif profile_names:
        default_combo.set(profile_names[0])
        profiles["default"] = profile_names[0]
        save_profiles(profiles)
    else:
        default_combo.set("")


def center_window(window):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    size = tuple(int(_) for _ in window.geometry().split('+')[0].split('x'))
    x = screen_width // 2 - size[0] // 2
    y = screen_height // 2 - size[1] // 2
    window.geometry(f"+{x}+{y}")


# 添加一个全局变量用于追踪当前的toast窗口
current_toast = None


def show_toast(message, duration=1500):
    global current_toast
    if current_toast is not None:
        try:
            current_toast.destroy()
        except tk.TclError:
            pass

    toast = tk.Toplevel()
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.attributes("-alpha", 0.9)

    label = tk.Label(
        toast,
        text=message,
        bg="#f0f0f0",
        fg="black",
        font=("微软雅黑", 12),
        padx=10,
        pady=5
    )
    label.pack(expand=True)

    toast.update_idletasks()
    label_width = label.winfo_reqwidth()
    label_height = label.winfo_reqheight()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = screen_width - label_width - 20
    y = screen_height - label_height - 50
    toast.geometry(f"{label_width + 20}x{label_height + 10}+{x}+{y}")

    current_toast = toast

    def destroy_toast():
        global current_toast
        if current_toast == toast:
            try:
                toast.destroy()
            except tk.TclError:
                pass
            current_toast = None

    toast.after(duration, destroy_toast)


def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}


def save_settings(settings_dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings_dict, f)


settings = load_settings()


def start_monitor(ssid, password):
    interval = 1800  # 每30分钟检查一次

    def run_in_thread():
        if monitor_network:
            monitor_network(ssid, password, interval)
        else:
            print("❌ 无法启动监控：monitor_network 函数不存在")

    threading.Thread(target=run_in_thread, daemon=True).start()
    root.after(0, lambda: show_toast("已启动网络监控"))


def connect_button_click(ssid_entry, pwd_entry, profiles, profile_combo, default_combo):
    ssid = ssid_entry.get().strip()
    password = pwd_entry.get().strip()
    if not ssid or not password:
        messagebox.showwarning("警告", "请输入网络名称和密码")
        return

    def task():
        from wifi_utils import is_connected, connect_to_wifi, log
        if is_connected(target_ssid=ssid):
            root.after(0, lambda: show_toast(f"当前已连接到 {ssid}"))
            return

        log(f"正在尝试连接到 {ssid}...")
        success = connect_to_wifi(ssid, password)

        if success:
            log(f"✅ 成功连接到 {ssid}")
            root.after(0, lambda: show_toast(f"✅ 已成功连接到 {ssid}"))
        else:
            log(f"❌ 连接失败，请检查网络设置")
            root.after(0, lambda: show_toast(f"❌ 无法连接到 {ssid}，请检查网络设置"))

    threading.Thread(target=task).start()


def add_profile(ssid_entry, pwd_entry, profiles, profile_combo, default_combo):
    ssid = ssid_entry.get().strip()
    password = pwd_entry.get().strip()
    if not ssid or not password:
        messagebox.showwarning("警告", "请输入网络名称和密码")
        return

    profiles[ssid] = password
    save_profiles(profiles)
    update_profile_list(profile_combo, profiles)
    update_default_combo(default_combo, profiles)
    root.after(0, lambda: show_toast(f"已添加网络 {ssid}"))


def delete_profile(profiles, profile_combo, default_combo):
    selected = profile_combo.get()
    if selected in profiles:
        del profiles[selected]

        if profiles.get("default") == selected:
            profiles["default"] = None

        save_profiles(profiles)
        update_profile_list(profile_combo, profiles)
        update_default_combo(default_combo, profiles)
        root.after(0, lambda: show_toast(f"已删除网络 {selected}"))


def edit_profile(profiles, profile_combo, default_combo, root_window):
    selected = profile_combo.get()
    if selected in profiles:
        edit_window = tk.Toplevel(root_window)
        edit_window.title("编辑网络")

        window_width = 300
        window_height = 200

        screen_width = root_window.winfo_screenwidth()
        screen_height = root_window.winfo_screenheight()

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        edit_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        edit_window.resizable(False, False)

        tk.Label(edit_window, text="网络名称 (SSID):").pack(pady=5)
        ssid_entry_edit = tk.Entry(edit_window, width=30)
        ssid_entry_edit.insert(0, selected)
        ssid_entry_edit.pack(pady=5)

        tk.Label(edit_window, text="密码:").pack(pady=5)
        pwd_entry_edit = tk.Entry(edit_window, width=30)
        pwd_entry_edit.insert(0, profiles[selected])
        pwd_entry_edit.pack(pady=5)

        def on_save():
            new_ssid = ssid_entry_edit.get().strip()
            new_password = pwd_entry_edit.get().strip()
            if not new_ssid or not new_password:
                messagebox.showwarning("警告", "不能为空")
                return

            if new_ssid != selected:
                del profiles[selected]

            profiles[new_ssid] = new_password
            save_profiles(profiles)
            update_profile_list(profile_combo, profiles)
            update_default_combo(default_combo, profiles)
            edit_window.destroy()
            root.after(0, lambda: show_toast("信息已更新"))

        tk.Button(edit_window, text="保存", command=on_save).pack(pady=10)


def on_profile_selected(event, profile_combo, ssid_entry, pwd_entry):
    selected = profile_combo.get()
    if selected in profiles:
        ssid_entry.delete(0, tk.END)
        ssid_entry.insert(0, selected)
        pwd_entry.delete(0, tk.END)
        pwd_entry.insert(0, profiles[selected])


def set_default_network(event, profiles, default_combo):
    selected = default_combo.get()
    if selected in profiles:
        profiles["default"] = selected
        save_profiles(profiles)
        root.after(0, lambda: show_toast(f"{selected} 已设为默认连接网络"))


def toggle_password(pwd_entry, show_var):
    pwd_entry.config(show="" if show_var.get() else "*")


# === 监护模式选择框（新增）===
def setup_monitor_choice_frame(root_window, profiles, default_combo):
    monitor_choice = tk.StringVar(value=settings.get("monitor_enabled", "否"))

    def on_monitor_choice(*args):
        choice = monitor_choice.get()
        ssid = default_combo.get().strip()
        password = profiles.get(ssid, "") if ssid else ""

        if choice == "是":
            if not ssid or not password:
                messagebox.showwarning("警告", "请先设置一个有效的默认网络及其密码")
                monitor_choice.set("否")  # 回退选择
                return

            start_monitor(ssid, password)
        else:
            pass  # 可选：添加停止监控逻辑

        # 无论是否成功，都保存设置
        save_settings({"monitor_enabled": choice})

    monitor_label = tk.Label(root_window, text="启用网络监护模式（仅作用于默认网络）", font=("微软雅黑", 10))
    monitor_label.pack(pady=(10, 0))

    monitor_combo = ttk.Combobox(
        root_window,
        textvariable=monitor_choice,
        values=["是", "否"],
        state="readonly",
        width=10,
        font=("微软雅黑", 10)
    )
    monitor_combo.pack(pady=5)
    monitor_combo.bind("<<ComboboxSelected>>", on_monitor_choice)


# === GUI 主体开始 ===
root = tk.Tk()
root.title("Wi-Fi 自动连接工具")
root.geometry("450x600")
center_window(root)
root.resizable(False, False)

profiles = load_wifi_profiles()

# === 默认连接网络 ===
default_frame = tk.Frame(root)
default_frame.pack(pady=10, fill=tk.X)

tk.Label(default_frame, text="默认连接网络", font=("微软雅黑", 14, "bold"), fg="green").pack(fill=tk.X)
default_combo = ttk.Combobox(default_frame, width=35, font=("微软雅黑", 12, "bold"))
default_combo.pack(pady=10)
default_combo.bind("<<ComboboxSelected>>", lambda event: set_default_network(event, profiles, default_combo))
update_default_combo(default_combo, profiles)

# === 网络名称 (SSID) 输入区 ===
ssid_frame = tk.Frame(root)
ssid_frame.pack(pady=10, fill=tk.X)

tk.Label(ssid_frame, text="网络名称 (SSID):", font=("微软雅黑", 10)).pack(anchor=tk.W)
ssid_entry = tk.Entry(ssid_frame, width=35, font=("微软雅黑", 11))
ssid_entry.pack(pady=5)

# === 密码输入区 ===
pwd_frame = tk.Frame(root)
pwd_frame.pack(pady=10, fill=tk.X)

tk.Label(pwd_frame, text="密码:", font=("微软雅黑", 10)).pack(anchor=tk.W)
pwd_entry = tk.Entry(pwd_frame, width=35, font=("微软雅黑", 11), show="*")
pwd_entry.pack(pady=5)

# === 显示密码勾选框 ===
show_var = tk.IntVar()
tk.Checkbutton(pwd_frame, text="显示密码", variable=show_var,
               command=lambda: toggle_password(pwd_entry, show_var),
               font=("微软雅黑", 10)).pack(anchor=tk.E)

# === 按钮区域 ===
frame = tk.Frame(root)
frame.pack(pady=10)

tk.Button(frame, text="连接", command=lambda: connect_button_click(ssid_entry, pwd_entry, profiles, profile_combo, default_combo), width=10).grid(row=0, column=0, padx=5)
tk.Button(frame, text="添加记录", command=lambda: add_profile(ssid_entry, pwd_entry, profiles, profile_combo, default_combo), width=10).grid(row=0, column=1, padx=5)
tk.Button(frame, text="编辑", command=lambda: edit_profile(profiles, profile_combo, default_combo, root), width=10).grid(row=0, column=2, padx=5)
tk.Button(frame, text="删除", command=lambda: delete_profile(profiles, profile_combo, default_combo), width=10).grid(row=0, column=3, padx=5)

# === 常用网络记录本 下拉框 ===
profile_frame = tk.Frame(root)
profile_frame.pack(pady=10, fill=tk.X)

tk.Label(profile_frame, text="常用网络记录本:", font=("微软雅黑", 10)).pack(anchor=tk.W)
profile_combo = ttk.Combobox(profile_frame, width=35, font=("微软雅黑", 11))
profile_combo.pack(pady=5)

profile_combo.bind("<<ComboboxSelected>>", lambda e: on_profile_selected(e, profile_combo, ssid_entry, pwd_entry))
update_profile_list(profile_combo, profiles)

# === 监护模式开关 ===
setup_monitor_choice_frame(root, profiles, default_combo)

# === 启动主循环 ===
root.mainloop()