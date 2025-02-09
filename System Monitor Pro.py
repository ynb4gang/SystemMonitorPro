import psutil
import time
import logging
import json
import csv
import platform
import GPUtil
from tkinter import filedialog, messagebox
from datetime import datetime
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from tkinter import ttk
from matplotlib import style
from PIL import Image, ImageTk
import threading
import requests
import os
import boto3

# Настройка логирования
logging.basicConfig(
    filename='system_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Загрузка конфигурации из файла
def load_config():
    default_config = {
        "cpu_threshold": 80,
        "memory_threshold": 80,
        "disk_threshold": 80,
        "gpu_threshold": 80,
        "gpu_memory_threshold": 80,
        "update_interval": 5000,
        "max_processes": 10,
        "max_connections": 10,
        "theme": "dark",
        "language": "en",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "google_sheets_api_key": "",
        "aws_access_key": "",
        "aws_secret_key": ""
    }
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
    except FileNotFoundError:
        with open("config.json", "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config

config = load_config()

# Пороги для уведомлений
CPU_THRESHOLD = config["cpu_threshold"]
MEMORY_THRESHOLD = config["memory_threshold"]
DISK_THRESHOLD = config["disk_threshold"]
GPU_THRESHOLD = config["gpu_threshold"]
GPU_MEMORY_THRESHOLD = config["gpu_memory_threshold"]
UPDATE_INTERVAL = config["update_interval"]
MAX_PROCESSES = config["max_processes"]
MAX_CONNECTIONS = config["max_connections"]
THEME = config["theme"]
LANGUAGE = config["language"]

# Локализация
translations = {
    "en": {
        "cpu_usage": "CPU Usage",
        "memory_usage": "Memory Usage",
        "disk_usage": "Disk Usage",
        "gpu_usage": "GPU Usage",
        "gpu_memory": "GPU Memory",
        "temperature": "Temperature",
        "processes": "Processes",
        "network": "Network",
        "notifications": "Notifications",
        "settings": "Settings",
        "system_info": "System Info",
        "save_data": "Save Data",
        "save_settings": "Save Settings",
        "clear_notifications": "Clear Notifications",
        "filter_notifications": "Filter Notifications",
        "terminate_process": "Terminate Process",
        "send_to_cloud": "Send to Cloud",
        "cpu_alert": "CPU Alert",
        "memory_alert": "Memory Alert",
        "disk_alert": "Disk Alert",
        "gpu_alert": "GPU Alert",
        "gpu_memory_alert": "GPU Memory Alert",
        "settings_saved": "Settings Saved",
        "data_saved": "Data Saved",
        "process_terminated": "Process Terminated",
        "error": "Error"
    },
    "ru": {
        "cpu_usage": "Использование CPU",
        "memory_usage": "Использование памяти",
        "disk_usage": "Использование диска",
        "gpu_usage": "Использование GPU",
        "gpu_memory": "Видеопамять GPU",
        "temperature": "Температура",
        "processes": "Процессы",
        "network": "Сеть",
        "notifications": "Уведомления",
        "settings": "Настройки",
        "system_info": "Информация о системе",
        "save_data": "Сохранить данные",
        "save_settings": "Сохранить настройки",
        "clear_notifications": "Очистить уведомления",
        "filter_notifications": "Фильтровать уведомления",
        "terminate_process": "Завершить процесс",
        "send_to_cloud": "Отправить в облако",
        "cpu_alert": "Оповещение CPU",
        "memory_alert": "Оповещение памяти",
        "disk_alert": "Оповещение диска",
        "gpu_alert": "Оповещение GPU",
        "gpu_memory_alert": "Оповещение видеопамяти GPU",
        "settings_saved": "Настройки сохранены",
        "data_saved": "Данные сохранены",
        "process_terminated": "Процесс завершен",
        "error": "Ошибка"
    }
}

def translate(key):
    return translations[LANGUAGE].get(key, key)

# Функции для получения данных системы
def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_memory_usage():
    mem = psutil.virtual_memory()
    return {
        'percent': mem.percent,
        'used': mem.used / (1024 ** 2),
        'total': mem.total / (1024 ** 2)
    }

def get_disk_usage():
    disk = psutil.disk_usage('/')
    return {
        'percent': disk.percent,
        'used': disk.used / (1024 ** 3),
        'total': disk.total / (1024 ** 3)
    }

def get_cpu_temperature():
    try:
        temps = psutil.sensors_temperatures()
        if temps and 'coretemp' in temps:
            return temps['coretemp'][0].current
        elif temps and 'k10temp' in temps:
            return temps['k10temp'][0].current
        return None
    except Exception as e:
        logging.error(f"Error getting CPU temperature: {e}")
        return None

def get_gpu_usage():
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            return {
                'usage': gpu.load * 100,
                'memory_used': gpu.memoryUsed,
                'memory_total': gpu.memoryTotal,
                'temperature': gpu.temperature
            }
        return None
    except Exception as e:
        logging.error(f"Error getting GPU info: {e}")
        return None

def get_top_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'cpu': proc.info['cpu_percent'],
                'memory': proc.info['memory_info'].rss / (1024 ** 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    processes.sort(key=lambda x: x['cpu'], reverse=True)
    return processes[:MAX_PROCESSES]

def get_network_connections():
    connections = psutil.net_connections(kind='inet')
    net_conns = []
    for conn in connections:
        if conn.status == 'ESTABLISHED':
            net_conns.append({
                'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                'status': conn.status,
                'pid': conn.pid
            })
    return net_conns[:MAX_CONNECTIONS]

def check_thresholds(cpu, memory, disk, gpu=None):
    alerts = []
    if cpu > CPU_THRESHOLD:
        alerts.append((translate("cpu_alert"), f"CPU usage is high: {cpu}%"))
    if memory > MEMORY_THRESHOLD:
        alerts.append((translate("memory_alert"), f"Memory usage is high: {memory}%"))
    if disk > DISK_THRESHOLD:
        alerts.append((translate("disk_alert"), f"Disk usage is high: {disk}%"))
    if gpu:
        if gpu['usage'] > GPU_THRESHOLD:
            alerts.append((translate("gpu_alert"), f"GPU usage is high: {gpu['usage']}%"))
        if (gpu['memory_used'] / gpu['memory_total']) * 100 > GPU_MEMORY_THRESHOLD:
            alerts.append((translate("gpu_memory_alert"), f"GPU memory usage is high: {gpu['memory_used']} MB / {gpu['memory_total']} MB"))
    return alerts

def notify(title, message):
    try:
        import plyer
        plyer.notification.notify(title=title, message=message)
    except ImportError:
        messagebox.showwarning(title, message)

class SystemMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Monitor")
        self.root.geometry("1200x800")
        ctk.set_appearance_mode(THEME)
        ctk.set_default_color_theme("blue")

        # Данные для графиков
        self.cpu_data = []
        self.memory_data = []
        self.disk_data = []
        self.gpu_data = []
        self.time_data = []

        # Переменные для интерфейса
        self.update_interval_var = ctk.StringVar(value=str(UPDATE_INTERVAL))
        self.cpu_threshold_var = ctk.StringVar(value=str(CPU_THRESHOLD))
        self.memory_threshold_var = ctk.StringVar(value=str(MEMORY_THRESHOLD))
        self.disk_threshold_var = ctk.StringVar(value=str(DISK_THRESHOLD))
        self.gpu_threshold_var = ctk.StringVar(value=str(GPU_THRESHOLD))
        self.gpu_memory_threshold_var = ctk.StringVar(value=str(GPU_MEMORY_THRESHOLD))
        self.theme_var = ctk.StringVar(value=THEME)
        self.language_var = ctk.StringVar(value=LANGUAGE)

        # Уведомления
        self.notifications = []

        self.setup_ui()
        self.update_system_info()

    def setup_ui(self):
        # Вкладки
        self.tab_control = ctk.CTkTabview(self.root)
        self.tab_control.add(translate("overview"))
        self.tab_control.add(translate("processes"))
        self.tab_control.add(translate("network"))
        self.tab_control.add(translate("notifications"))
        self.tab_control.add(translate("settings"))
        self.tab_control.add(translate("system_info"))
        self.tab_control.pack(fill="both", expand=True)

        # Вкладка Overview
        self.setup_overview_tab(self.tab_control.tab(translate("overview")))
        # Вкладка Processes
        self.setup_processes_tab(self.tab_control.tab(translate("processes")))
        # Вкладка Network
        self.setup_network_tab(self.tab_control.tab(translate("network")))
        # Вкладка Notifications
        self.setup_notifications_tab(self.tab_control.tab(translate("notifications")))
        # Вкладка Settings
        self.setup_settings_tab(self.tab_control.tab(translate("settings")))
        # Вкладка System Info
        self.setup_system_info_tab(self.tab_control.tab(translate("system_info")))

    def setup_overview_tab(self, tab):
        # Сетка для плиток
        tab.grid_columnconfigure((0, 1, 2, 3), weight=1)
        tab.grid_rowconfigure((0, 1), weight=1)

        # Плитка CPU
        cpu_frame = ctk.CTkFrame(tab, corner_radius=10)
        cpu_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(cpu_frame, text=translate("cpu_usage"), font=("Arial", 16, "bold")).pack(pady=10)
        self.cpu_usage_label = ctk.CTkLabel(cpu_frame, text="CPU Usage: 0%", font=("Arial", 14))
        self.cpu_usage_label.pack()
        self.cpu_progress = ctk.CTkProgressBar(cpu_frame, orientation="horizontal")
        self.cpu_progress.pack(fill="x", padx=10, pady=5)
        self.cpu_progress.set(0)

        # Плитка Memory
        memory_frame = ctk.CTkFrame(tab, corner_radius=10)
        memory_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(memory_frame, text=translate("memory_usage"), font=("Arial", 16, "bold")).pack(pady=10)
        self.memory_usage_label = ctk.CTkLabel(memory_frame, text="Memory Usage: 0%", font=("Arial", 14))
        self.memory_usage_label.pack()
        self.memory_progress = ctk.CTkProgressBar(memory_frame, orientation="horizontal")
        self.memory_progress.pack(fill="x", padx=10, pady=5)
        self.memory_progress.set(0)

        # Плитка Disk
        disk_frame = ctk.CTkFrame(tab, corner_radius=10)
        disk_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(disk_frame, text=translate("disk_usage"), font=("Arial", 16, "bold")).pack(pady=10)
        self.disk_usage_label = ctk.CTkLabel(disk_frame, text="Disk Usage: 0%", font=("Arial", 14))
        self.disk_usage_label.pack()
        self.disk_progress = ctk.CTkProgressBar(disk_frame, orientation="horizontal")
        self.disk_progress.pack(fill="x", padx=10, pady=5)
        self.disk_progress.set(0)

        # Плитка GPU
        gpu_frame = ctk.CTkFrame(tab, corner_radius=10)
        gpu_frame.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(gpu_frame, text=translate("gpu_usage"), font=("Arial", 16, "bold")).pack(pady=10)
        self.gpu_usage_label = ctk.CTkLabel(gpu_frame, text="GPU Usage: 0%", font=("Arial", 14))
        self.gpu_usage_label.pack()
        self.gpu_progress = ctk.CTkProgressBar(gpu_frame, orientation="horizontal")
        self.gpu_progress.pack(fill="x", padx=10, pady=5)
        self.gpu_progress.set(0)

        # Графики
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.cpu_plot = self.figure.add_subplot(411)
        self.memory_plot = self.figure.add_subplot(412)
        self.disk_plot = self.figure.add_subplot(413)
        self.gpu_plot = self.figure.add_subplot(414)
        self.canvas = FigureCanvasTkAgg(self.figure, tab)
        self.canvas.get_tk_widget().grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

        # Настройка стиля графиков
        style.use("dark_background" if THEME == "dark" else "classic")
        self.cpu_plot.set_title(translate("cpu_usage"), color="white" if THEME == "dark" else "black")
        self.cpu_plot.set_ylabel("CPU (%)", color="white" if THEME == "dark" else "black")
        self.cpu_plot.grid(True, linestyle="--", alpha=0.6)
        self.memory_plot.set_title(translate("memory_usage"), color="white" if THEME == "dark" else "black")
        self.memory_plot.set_ylabel("Memory (%)", color="white" if THEME == "dark" else "black")
        self.memory_plot.grid(True, linestyle="--", alpha=0.6)
        self.disk_plot.set_title(translate("disk_usage"), color="white" if THEME == "dark" else "black")
        self.disk_plot.set_ylabel("Disk (%)", color="white" if THEME == "dark" else "black")
        self.disk_plot.grid(True, linestyle="--", alpha=0.6)
        self.gpu_plot.set_title(translate("gpu_usage"), color="white" if THEME == "dark" else "black")
        self.gpu_plot.set_ylabel("GPU (%)", color="white" if THEME == "dark" else "black")
        self.gpu_plot.grid(True, linestyle="--", alpha=0.6)

        # Кнопка для сохранения данных
        save_button = ctk.CTkButton(tab, text=translate("save_data"), command=self.save_data, corner_radius=10)
        save_button.grid(row=2, column=0, columnspan=4, pady=10)

    def setup_processes_tab(self, tab):
        # Таблица процессов
        self.process_tree = ttk.Treeview(tab, columns=("PID", "Name", "CPU", "Memory"), show="headings")
        self.process_tree.heading("PID", text="PID")
        self.process_tree.heading("Name", text=translate("processes"))
        self.process_tree.heading("CPU", text="CPU (%)")
        self.process_tree.heading("Memory", text="Memory (MB)")
        self.process_tree.pack(fill="both", expand=True)

        # Кнопка для завершения процесса
        terminate_button = ctk.CTkButton(tab, text=translate("terminate_process"), command=self.terminate_process, corner_radius=10)
        terminate_button.pack(pady=10)

    def setup_network_tab(self, tab):
        # Таблица сетевых соединений
        self.network_tree = ttk.Treeview(tab, columns=("Local Address", "Remote Address", "Status", "PID"), show="headings")
        self.network_tree.heading("Local Address", text="Local Address")
        self.network_tree.heading("Remote Address", text="Remote Address")
        self.network_tree.heading("Status", text="Status")
        self.network_tree.heading("PID", text="PID")
        self.network_tree.pack(fill="both", expand=True)

    def setup_notifications_tab(self, tab):
        # Список уведомлений
        self.notifications_listbox = ctk.CTkTextbox(tab, wrap="none")
        self.notifications_listbox.pack(fill="both", expand=True)

        # Кнопки для управления уведомлениями
        clear_button = ctk.CTkButton(tab, text=translate("clear_notifications"), command=self.clear_notifications, corner_radius=10)
        clear_button.pack(pady=10)

        filter_button = ctk.CTkButton(tab, text=translate("filter_notifications"), command=self.filter_notifications, corner_radius=10)
        filter_button.pack(pady=10)

    def setup_settings_tab(self, tab):
        # Настройки порогов и интервала обновления
        ctk.CTkLabel(tab, text="CPU Threshold (%):").grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkEntry(tab, textvariable=self.cpu_threshold_var).grid(row=0, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="Memory Threshold (%):").grid(row=1, column=0, padx=10, pady=10)
        ctk.CTkEntry(tab, textvariable=self.memory_threshold_var).grid(row=1, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="Disk Threshold (%):").grid(row=2, column=0, padx=10, pady=10)
        ctk.CTkEntry(tab, textvariable=self.disk_threshold_var).grid(row=2, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="GPU Threshold (%):").grid(row=3, column=0, padx=10, pady=10)
        ctk.CTkEntry(tab, textvariable=self.gpu_threshold_var).grid(row=3, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="GPU Memory Threshold (%):").grid(row=4, column=0, padx=10, pady=10)
        ctk.CTkEntry(tab, textvariable=self.gpu_memory_threshold_var).grid(row=4, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="Update Interval (ms):").grid(row=5, column=0, padx=10, pady=10)
        ctk.CTkEntry(tab, textvariable=self.update_interval_var).grid(row=5, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="Theme:").grid(row=6, column=0, padx=10, pady=10)
        ctk.CTkOptionMenu(tab, values=["dark", "light"], variable=self.theme_var).grid(row=6, column=1, padx=10, pady=10)
        ctk.CTkLabel(tab, text="Language:").grid(row=7, column=0, padx=10, pady=10)
        ctk.CTkOptionMenu(tab, values=["en", "ru"], variable=self.language_var).grid(row=7, column=1, padx=10, pady=10)
        ctk.CTkButton(tab, text=translate("save_settings"), command=self.save_settings, corner_radius=10).grid(row=8, column=0, columnspan=2, pady=10)

    def setup_system_info_tab(self, tab):
        # Информация о системе
        system_info = {
            "OS": platform.system(),
            "OS Version": platform.version(),
            "Python Version": platform.python_version(),
            "CPU Cores": psutil.cpu_count(logical=False),
            "Logical CPUs": psutil.cpu_count(logical=True),
            "Total Memory": f"{psutil.virtual_memory().total / (1024 ** 3):.2f} GB",
            "Total Disk": f"{psutil.disk_usage('/').total / (1024 ** 3):.2f} GB"
        }
        for i, (key, value) in enumerate(system_info.items()):
            ctk.CTkLabel(tab, text=f"{key}: {value}", font=("Arial", 14)).grid(row=i, column=0, padx=10, pady=5, sticky="w")

    def save_settings(self):
        global CPU_THRESHOLD, MEMORY_THRESHOLD, DISK_THRESHOLD, GPU_THRESHOLD, GPU_MEMORY_THRESHOLD, UPDATE_INTERVAL, THEME, LANGUAGE
        CPU_THRESHOLD = int(self.cpu_threshold_var.get())
        MEMORY_THRESHOLD = int(self.memory_threshold_var.get())
        DISK_THRESHOLD = int(self.disk_threshold_var.get())
        GPU_THRESHOLD = int(self.gpu_threshold_var.get())
        GPU_MEMORY_THRESHOLD = int(self.gpu_memory_threshold_var.get())
        UPDATE_INTERVAL = int(self.update_interval_var.get())
        THEME = self.theme_var.get()
        LANGUAGE = self.language_var.get()
        ctk.set_appearance_mode(THEME)
        self.update_plots_theme()
        config.update({
            "cpu_threshold": CPU_THRESHOLD,
            "memory_threshold": MEMORY_THRESHOLD,
            "disk_threshold": DISK_THRESHOLD,
            "gpu_threshold": GPU_THRESHOLD,
            "gpu_memory_threshold": GPU_MEMORY_THRESHOLD,
            "update_interval": UPDATE_INTERVAL,
            "theme": THEME,
            "language": LANGUAGE
        })
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        messagebox.showinfo(translate("settings_saved"), "Settings have been saved successfully.")

    def update_plots_theme(self):
        self.cpu_plot.set_title(translate("cpu_usage"), color="white" if THEME == "dark" else "black")
        self.cpu_plot.set_ylabel("CPU (%)", color="white" if THEME == "dark" else "black")
        self.memory_plot.set_title(translate("memory_usage"), color="white" if THEME == "dark" else "black")
        self.memory_plot.set_ylabel("Memory (%)", color="white" if THEME == "dark" else "black")
        self.disk_plot.set_title(translate("disk_usage"), color="white" if THEME == "dark" else "black")
        self.disk_plot.set_ylabel("Disk (%)", color="white" if THEME == "dark" else "black")
        self.gpu_plot.set_title(translate("gpu_usage"), color="white" if THEME == "dark" else "black")
        self.gpu_plot.set_ylabel("GPU (%)", color="white" if THEME == "dark" else "black")
        self.canvas.draw()

    def update_system_info(self):
        # Получение данных
        cpu = get_cpu_usage()
        mem = get_memory_usage()
        disk = get_disk_usage()
        gpu = get_gpu_usage()
        temp = get_cpu_temperature()
        processes = get_top_processes()
        connections = get_network_connections()

        # Обновление меток
        self.cpu_usage_label.configure(text=f"CPU Usage: {cpu}%")
        self.cpu_progress.set(cpu / 100)
        self.memory_usage_label.configure(text=f"Memory Usage: {mem['percent']}%")
        self.memory_progress.set(mem['percent'] / 100)
        self.disk_usage_label.configure(text=f"Disk Usage: {disk['percent']}%")
        self.disk_progress.set(disk['percent'] / 100)
        if gpu:
            self.gpu_usage_label.configure(text=f"GPU Usage: {gpu['usage']:.1f}%")
            self.gpu_progress.set(gpu['usage'] / 100)

        # Обновление графиков
        self.time_data.append(datetime.now())
        self.cpu_data.append(cpu)
        self.memory_data.append(mem['percent'])
        self.disk_data.append(disk['percent'])
        if gpu:
            self.gpu_data.append(gpu['usage'])

        if len(self.time_data) > 10:
            self.time_data.pop(0)
            self.cpu_data.pop(0)
            self.memory_data.pop(0)
            self.disk_data.pop(0)
            if gpu:
                self.gpu_data.pop(0)

        self.cpu_plot.clear()
        self.cpu_plot.plot(self.time_data, self.cpu_data, label="CPU (%)", color="cyan")
        self.cpu_plot.legend()
        self.cpu_plot.grid(True, linestyle="--", alpha=0.6)

        self.memory_plot.clear()
        self.memory_plot.plot(self.time_data, self.memory_data, label="Memory (%)", color="lime")
        self.memory_plot.legend()
        self.memory_plot.grid(True, linestyle="--", alpha=0.6)

        self.disk_plot.clear()
        self.disk_plot.plot(self.time_data, self.disk_data, label="Disk (%)", color="magenta")
        self.disk_plot.legend()
        self.disk_plot.grid(True, linestyle="--", alpha=0.6)

        if gpu:
            self.gpu_plot.clear()
            self.gpu_plot.plot(self.time_data, self.gpu_data, label="GPU (%)", color="orange")
            self.gpu_plot.legend()
            self.gpu_plot.grid(True, linestyle="--", alpha=0.6)

        self.canvas.draw()

        # Обновление таблицы процессов
        self.process_tree.delete(*self.process_tree.get_children())
        for proc in processes:
            self.process_tree.insert("", "end", values=(proc['pid'], proc['name'], f"{proc['cpu']:.1f}", f"{proc['memory']:.1f}"))

        # Обновление таблицы сетевых соединений
        self.network_tree.delete(*self.network_tree.get_children())
        for conn in connections:
            self.network_tree.insert("", "end", values=(
                conn['local_address'], conn['remote_address'], conn['status'], conn['pid']
            ))

        # Проверка порогов и уведомления
        alerts = check_thresholds(cpu, mem['percent'], disk['percent'], gpu)
        for title, message in alerts:
            notify(title, message)
            self.notifications.append(f"{datetime.now()} - {title}: {message}")
            self.notifications_listbox.insert("end", f"{datetime.now()} - {title}: {message}\n")

        # Планирование следующего обновления
        self.root.after(int(self.update_interval_var.get()), self.update_system_info)

    def save_data(self):
        # Сохранение данных в файл
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json")])
        if filename:
            if filename.endswith(".csv"):
                with open(filename, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Time", "CPU (%)", "Memory (%)", "Disk (%)", "GPU (%)"])
                    for i in range(len(self.time_data)):
                        writer.writerow([
                            self.time_data[i],
                            self.cpu_data[i],
                            self.memory_data[i],
                            self.disk_data[i],
                            self.gpu_data[i] if self.gpu_data else "N/A"
                        ])
            elif filename.endswith(".json"):
                data = {
                    "time": [str(t) for t in self.time_data],
                    "cpu": self.cpu_data,
                    "memory": self.memory_data,
                    "disk": self.disk_data,
                    "gpu": self.gpu_data if self.gpu_data else []
                }
                with open(filename, "w") as f:
                    json.dump(data, f, indent=4)
            messagebox.showinfo(translate("data_saved"), "Data has been saved successfully.")

    def clear_notifications(self):
        self.notifications_listbox.delete("1.0", "end")
        self.notifications = []

    def filter_notifications(self):
        filter_window = ctk.CTkToplevel(self.root)
        filter_window.title("Filter Notifications")
        filter_window.geometry("300x200")

        ctk.CTkLabel(filter_window, text="Filter by type:").pack(pady=10)
        filter_type = ctk.CTkOptionMenu(filter_window, values=["CPU", "Memory", "Disk", "GPU"])
        filter_type.pack(pady=10)

        def apply_filter():
            filter_text = filter_type.get()
            self.notifications_listbox.delete("1.0", "end")
            for note in self.notifications:
                if filter_text in note:
                    self.notifications_listbox.insert("end", note + "\n")

        ctk.CTkButton(filter_window, text="Apply", command=apply_filter).pack(pady=10)

    def terminate_process(self):
        # Завершение выбранного процесса
        selected_item = self.process_tree.selection()
        if selected_item:
            pid = int(self.process_tree.item(selected_item, "values")[0])
            try:
                psutil.Process(pid).terminate()
                messagebox.showinfo(translate("process_terminated"), f"Process {pid} terminated successfully.")
            except psutil.NoSuchProcess:
                messagebox.showerror(translate("error"), "Process not found.")
            except psutil.AccessDenied:
                messagebox.showerror(translate("error"), "Access denied.")

    def send_to_cloud(self):
        # Отправка данных в облако (AWS S3)
        def upload_to_s3():
            try:
                s3 = boto3.client('s3', aws_access_key_id=config["aws_access_key"], aws_secret_access_key=config["aws_secret_key"])
                s3.upload_file('system_monitor.log', 'your-bucket-name', 'system_monitor.log')
                messagebox.showinfo("Success", "Data has been sent to the cloud.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send data to the cloud: {e}")

        threading.Thread(target=upload_to_s3).start()

if __name__ == "__main__":
    root = ctk.CTk()
    app = SystemMonitorApp(root)
    root.mainloop()
