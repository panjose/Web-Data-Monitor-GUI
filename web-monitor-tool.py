"""
网页数据监控自动化工具
功能：监控指定网页元素的变化，并根据规则自动执行操作
"""

import time
import json
import os
import threading
import queue
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from plyer import notification
import pickle


class SelectorType(Enum):
    """选择器类型枚举"""
    ID = "id"
    CLASS = "class"
    XPATH = "xpath"
    CSS = "css"
    NAME = "name"
    TAG = "tag"


@dataclass
class MonitorTarget:
    """监控目标数据类"""
    url: str
    element_selector: str
    selector_type: SelectorType
    check_interval: int = 30  # 检查间隔（秒）
    description: str = ""


@dataclass
class ActionRule:
    """动作规则数据类"""
    condition: str  # 变化条件：'any_change', 'contains', 'equals', 'greater', 'less'
    condition_value: Optional[str] = None
    action_url: Optional[str] = None
    action_selector: Optional[str] = None
    action_selector_type: Optional[SelectorType] = None
    notify: bool = True
    description: str = ""


class WebMonitor:
    """网页监控核心类"""
    
    def __init__(self):
        self.driver = None
        self.monitoring = False
        self.monitor_thread = None
        self.targets: List[MonitorTarget] = []
        self.rules: List[ActionRule] = []
        self.last_values: Dict[int, str] = {}
        self.cookies_file = "cookies.pkl"
        self.config_file = "monitor_config.json"
        self.message_queue = queue.Queue()
        
    def init_driver(self, headless=False):
        """初始化浏览器驱动"""
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1280, 800)
        
    def close_driver(self):
        """关闭浏览器驱动"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def save_cookies(self):
        """保存cookies到文件"""
        if self.driver:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
                
    def load_cookies(self):
        """从文件加载cookies"""
        if os.path.exists(self.cookies_file) and self.driver:
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    try:
                        self.driver.add_cookie(cookie)
                    except:
                        pass
                        
    def manual_login(self, url: str):
        """允许用户手动登录"""
        if not self.driver:
            self.init_driver(headless=False)
            
        self.driver.get(url)
        input("请在浏览器中完成登录，然后按Enter键继续...")
        self.save_cookies()
        return True
        
    def get_element(self, selector: str, selector_type: SelectorType):
        """根据选择器获取元素"""
        by_map = {
            SelectorType.ID: By.ID,
            SelectorType.CLASS: By.CLASS_NAME,
            SelectorType.XPATH: By.XPATH,
            SelectorType.CSS: By.CSS_SELECTOR,
            SelectorType.NAME: By.NAME,
            SelectorType.TAG: By.TAG_NAME
        }
        
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by_map[selector_type], selector))
            )
            return element
        except TimeoutException:
            return None
            
    def get_element_value(self, target: MonitorTarget) -> Optional[str]:
        """获取目标元素的值"""
        try:
            self.driver.get(target.url)
            time.sleep(2)  # 等待页面加载
            
            element = self.get_element(target.element_selector, target.selector_type)
            if element:
                # 尝试获取不同类型的值
                value = element.text
                if not value:
                    value = element.get_attribute('value')
                if not value:
                    value = element.get_attribute('innerHTML')
                return value
        except Exception as e:
            self.message_queue.put(f"获取元素值错误: {e}")
            return None
            
    def check_condition(self, rule: ActionRule, old_value: str, new_value: str) -> bool:
        """检查是否满足触发条件"""
        if rule.condition == 'any_change':
            return old_value != new_value
        elif rule.condition == 'contains' and rule.condition_value:
            return rule.condition_value in new_value
        elif rule.condition == 'equals' and rule.condition_value:
            return new_value == rule.condition_value
        elif rule.condition == 'greater' and rule.condition_value:
            try:
                return float(new_value) > float(rule.condition_value)
            except:
                return False
        elif rule.condition == 'less' and rule.condition_value:
            try:
                return float(new_value) < float(rule.condition_value)
            except:
                return False
        return False
        
    def execute_action(self, rule: ActionRule):
        """执行动作规则"""
        try:
            if rule.action_url:
                self.driver.get(rule.action_url)
                time.sleep(2)
                
            if rule.action_selector and rule.action_selector_type:
                element = self.get_element(rule.action_selector, rule.action_selector_type)
                if element:
                    # 尝试点击元素
                    try:
                        element.click()
                    except:
                        # 如果直接点击失败，使用JavaScript点击
                        self.driver.execute_script("arguments[0].click();", element)
                    
                    self.message_queue.put(f"已执行动作: 点击 {rule.action_selector}")
                    
        except Exception as e:
            self.message_queue.put(f"执行动作错误: {e}")
            
    def send_notification(self, title: str, message: str):
        """发送桌面通知"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_icon=None,
                timeout=10
            )
        except:
            pass
            
    def monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            for i, target in enumerate(self.targets):
                if not self.monitoring:
                    break
                    
                try:
                    new_value = self.get_element_value(target)
                    
                    if new_value is not None:
                        old_value = self.last_values.get(i, "")
                        
                        if old_value and old_value != new_value:
                            # 数据发生变化
                            change_msg = f"监控目标 {target.description} 数据变化:\n旧值: {old_value[:100]}\n新值: {new_value[:100]}"
                            self.message_queue.put(change_msg)
                            
                            # 检查并执行规则
                            for rule in self.rules:
                                if self.check_condition(rule, old_value, new_value):
                                    if rule.notify:
                                        self.send_notification("数据变化通知", change_msg)
                                    self.execute_action(rule)
                                    
                        self.last_values[i] = new_value
                        
                except Exception as e:
                    self.message_queue.put(f"监控错误: {e}")
                    
                time.sleep(target.check_interval)
                
    def start_monitoring(self):
        """开始监控"""
        if not self.monitoring and self.targets:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            return True
        return False
        
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            
    def save_config(self):
        """保存配置到文件"""
        config = {
            'targets': [
                {
                    'url': t.url,
                    'selector': t.element_selector,
                    'selector_type': t.selector_type.value,
                    'interval': t.check_interval,
                    'description': t.description
                } for t in self.targets
            ],
            'rules': [
                {
                    'condition': r.condition,
                    'condition_value': r.condition_value,
                    'action_url': r.action_url,
                    'action_selector': r.action_selector,
                    'action_selector_type': r.action_selector_type.value if r.action_selector_type else None,
                    'notify': r.notify,
                    'description': r.description
                } for r in self.rules
            ]
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            
    def load_config(self):
        """从文件加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.targets = [
                MonitorTarget(
                    url=t['url'],
                    element_selector=t['selector'],
                    selector_type=SelectorType(t['selector_type']),
                    check_interval=t['interval'],
                    description=t['description']
                ) for t in config.get('targets', [])
            ]
            
            self.rules = [
                ActionRule(
                    condition=r['condition'],
                    condition_value=r['condition_value'],
                    action_url=r['action_url'],
                    action_selector=r['action_selector'],
                    action_selector_type=SelectorType(r['action_selector_type']) if r['action_selector_type'] else None,
                    notify=r['notify'],
                    description=r['description']
                ) for r in config.get('rules', [])
            ]


class MonitorGUI:
    """图形用户界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("网页数据监控工具")
        self.root.geometry("900x700")
        
        self.monitor = WebMonitor()
        self.setup_ui()
        self.update_message_loop()
        
    def setup_ui(self):
        """设置UI界面"""
        # 创建标签页
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 登录标签页
        self.login_frame = ttk.Frame(notebook)
        notebook.add(self.login_frame, text="登录设置")
        self.setup_login_tab()
        
        # 监控目标标签页
        self.target_frame = ttk.Frame(notebook)
        notebook.add(self.target_frame, text="监控目标")
        self.setup_target_tab()
        
        # 动作规则标签页
        self.rule_frame = ttk.Frame(notebook)
        notebook.add(self.rule_frame, text="动作规则")
        self.setup_rule_tab()
        
        # 监控日志标签页
        self.log_frame = ttk.Frame(notebook)
        notebook.add(self.log_frame, text="监控日志")
        self.setup_log_tab()
        
        # 底部控制按钮
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="开始监控", command=self.start_monitoring)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="停止监控", command=self.stop_monitoring, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="保存配置", command=self.save_config).pack(side='left', padx=5)
        ttk.Button(control_frame, text="加载配置", command=self.load_config).pack(side='left', padx=5)
        
    def setup_login_tab(self):
        """设置登录标签页"""
        ttk.Label(self.login_frame, text="登录URL:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        self.login_url_entry = ttk.Entry(self.login_frame, width=50)
        self.login_url_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Button(self.login_frame, text="手动登录", command=self.manual_login).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Label(self.login_frame, text="说明: 点击手动登录后，将打开浏览器，请完成登录后按Enter键").grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
    def setup_target_tab(self):
        """设置监控目标标签页"""
        # 输入区域
        input_frame = ttk.LabelFrame(self.target_frame, text="添加监控目标")
        input_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(input_frame, text="网页URL:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.target_url_entry = ttk.Entry(input_frame, width=50)
        self.target_url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
        
        ttk.Label(input_frame, text="元素选择器:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.selector_entry = ttk.Entry(input_frame, width=30)
        self.selector_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.selector_type_var = tk.StringVar(value="xpath")
        selector_type_combo = ttk.Combobox(input_frame, textvariable=self.selector_type_var, width=15)
        selector_type_combo['values'] = ['id', 'class', 'xpath', 'css', 'name', 'tag']
        selector_type_combo.grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Label(input_frame, text="检查间隔(秒):").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.interval_entry = ttk.Entry(input_frame, width=10)
        self.interval_entry.insert(0, "30")
        self.interval_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(input_frame, text="描述:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.target_desc_entry = ttk.Entry(input_frame, width=50)
        self.target_desc_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=5)
        
        ttk.Button(input_frame, text="添加目标", command=self.add_target).grid(row=4, column=1, padx=5, pady=10)
        ttk.Button(input_frame, text="测试选择器", command=self.test_selector).grid(row=4, column=2, padx=5, pady=10)
        
        # 目标列表
        list_frame = ttk.LabelFrame(self.target_frame, text="监控目标列表")
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.target_listbox = tk.Listbox(list_frame)
        self.target_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Button(list_frame, text="删除选中", command=self.delete_target).pack(padx=5, pady=5)
        
    def setup_rule_tab(self):
        """设置动作规则标签页"""
        # 输入区域
        input_frame = ttk.LabelFrame(self.rule_frame, text="添加动作规则")
        input_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(input_frame, text="触发条件:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.condition_var = tk.StringVar(value="any_change")
        condition_combo = ttk.Combobox(input_frame, textvariable=self.condition_var, width=15)
        condition_combo['values'] = ['any_change', 'contains', 'equals', 'greater', 'less']
        condition_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(input_frame, text="条件值:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.condition_value_entry = ttk.Entry(input_frame, width=20)
        self.condition_value_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(input_frame, text="动作URL:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.action_url_entry = ttk.Entry(input_frame, width=50)
        self.action_url_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5)
        
        ttk.Label(input_frame, text="动作元素:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.action_selector_entry = ttk.Entry(input_frame, width=30)
        self.action_selector_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        self.action_selector_type_var = tk.StringVar(value="xpath")
        action_selector_combo = ttk.Combobox(input_frame, textvariable=self.action_selector_type_var, width=15)
        action_selector_combo['values'] = ['id', 'class', 'xpath', 'css', 'name', 'tag']
        action_selector_combo.grid(row=2, column=3, padx=5, pady=5)
        
        self.notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="发送通知", variable=self.notify_var).grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(input_frame, text="描述:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.rule_desc_entry = ttk.Entry(input_frame, width=50)
        self.rule_desc_entry.grid(row=4, column=1, columnspan=3, padx=5, pady=5)
        
        ttk.Button(input_frame, text="添加规则", command=self.add_rule).grid(row=5, column=1, padx=5, pady=10)
        
        # 规则列表
        list_frame = ttk.LabelFrame(self.rule_frame, text="动作规则列表")
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.rule_listbox = tk.Listbox(list_frame)
        self.rule_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Button(list_frame, text="删除选中", command=self.delete_rule).pack(padx=5, pady=5)
        
    def setup_log_tab(self):
        """设置日志标签页"""
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Button(self.log_frame, text="清空日志", command=self.clear_log).pack(padx=10, pady=5)
        
    def manual_login(self):
        """手动登录"""
        url = self.login_url_entry.get()
        if not url:
            messagebox.showwarning("警告", "请输入登录URL")
            return
            
        self.log_message("开始手动登录...")
        if self.monitor.manual_login(url):
            self.log_message("登录成功，cookies已保存")
            messagebox.showinfo("成功", "登录成功，cookies已保存")
            
    def add_target(self):
        """添加监控目标"""
        url = self.target_url_entry.get()
        selector = self.selector_entry.get()
        
        if not url or not selector:
            messagebox.showwarning("警告", "请填写完整信息")
            return
            
        target = MonitorTarget(
            url=url,
            element_selector=selector,
            selector_type=SelectorType(self.selector_type_var.get()),
            check_interval=int(self.interval_entry.get()),
            description=self.target_desc_entry.get()
        )
        
        self.monitor.targets.append(target)
        self.update_target_list()
        self.log_message(f"添加监控目标: {target.description or url}")
        
    def test_selector(self):
        """测试选择器"""
        url = self.target_url_entry.get()
        selector = self.selector_entry.get()
        
        if not url or not selector:
            messagebox.showwarning("警告", "请填写URL和选择器")
            return
            
        try:
            if not self.monitor.driver:
                self.monitor.init_driver(headless=False)
                self.monitor.load_cookies()
                
            self.monitor.driver.get(url)
            time.sleep(2)
            
            element = self.monitor.get_element(selector, SelectorType(self.selector_type_var.get()))
            if element:
                value = element.text or element.get_attribute('value') or element.get_attribute('innerHTML')
                messagebox.showinfo("测试结果", f"找到元素，值为:\n{value[:200]}")
                self.log_message(f"测试选择器成功: {value[:100]}")
            else:
                messagebox.showwarning("测试结果", "未找到元素")
                
        except Exception as e:
            messagebox.showerror("错误", f"测试失败: {e}")
            
    def add_rule(self):
        """添加动作规则"""
        rule = ActionRule(
            condition=self.condition_var.get(),
            condition_value=self.condition_value_entry.get() or None,
            action_url=self.action_url_entry.get() or None,
            action_selector=self.action_selector_entry.get() or None,
            action_selector_type=SelectorType(self.action_selector_type_var.get()) if self.action_selector_entry.get() else None,
            notify=self.notify_var.get(),
            description=self.rule_desc_entry.get()
        )
        
        self.monitor.rules.append(rule)
        self.update_rule_list()
        self.log_message(f"添加动作规则: {rule.description or rule.condition}")
        
    def delete_target(self):
        """删除选中的监控目标"""
        selection = self.target_listbox.curselection()
        if selection:
            index = selection[0]
            del self.monitor.targets[index]
            self.update_target_list()
            
    def delete_rule(self):
        """删除选中的动作规则"""
        selection = self.rule_listbox.curselection()
        if selection:
            index = selection[0]
            del self.monitor.rules[index]
            self.update_rule_list()
            
    def update_target_list(self):
        """更新监控目标列表显示"""
        self.target_listbox.delete(0, tk.END)
        for target in self.monitor.targets:
            self.target_listbox.insert(tk.END, f"{target.description or target.url} - {target.element_selector}")
            
    def update_rule_list(self):
        """更新动作规则列表显示"""
        self.rule_listbox.delete(0, tk.END)
        for rule in self.monitor.rules:
            self.rule_listbox.insert(tk.END, f"{rule.description or rule.condition} - {rule.action_selector or '仅通知'}")
            
    def start_monitoring(self):
        """开始监控"""
        if not self.monitor.targets:
            messagebox.showwarning("警告", "请先添加监控目标")
            return
            
        if not self.monitor.driver:
            self.monitor.init_driver(headless=True)
            self.monitor.load_cookies()
            
        if self.monitor.start_monitoring():
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.log_message("监控已启动")
            messagebox.showinfo("成功", "监控已启动")
            
    def stop_monitoring(self):
        """停止监控"""
        self.monitor.stop_monitoring()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.log_message("监控已停止")
        messagebox.showinfo("提示", "监控已停止")
        
    def save_config(self):
        """保存配置"""
        self.monitor.save_config()
        self.log_message("配置已保存")
        messagebox.showinfo("成功", "配置已保存")
        
    def load_config(self):
        """加载配置"""
        self.monitor.load_config()
        self.update_target_list()
        self.update_rule_list()
        self.log_message("配置已加载")
        messagebox.showinfo("成功", "配置已加载")
        
    def log_message(self, message: str):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def update_message_loop(self):
        """更新消息循环"""
        try:
            while not self.monitor.message_queue.empty():
                message = self.monitor.message_queue.get_nowait()
                self.log_message(message)
        except:
            pass
        finally:
            self.root.after(1000, self.update_message_loop)
            
    def run(self):
        """运行GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """关闭窗口时的处理"""
        self.monitor.stop_monitoring()
        self.monitor.close_driver()
        self.root.destroy()


if __name__ == "__main__":
    # 安装依赖提示
    print("""
    请确保已安装以下依赖：
    pip install selenium
    pip install plyer
    pip install webdriver-manager
    
    并下载Chrome浏览器和对应版本的ChromeDriver
    """)
    
    # 启动GUI应用
    app = MonitorGUI()
    app.run()
