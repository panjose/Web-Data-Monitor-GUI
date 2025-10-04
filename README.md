# Web-Data-Monitor-GUI: 网页数据自动化监控工具
A GUI-based Python automation tool using Selenium and Tkinter to monitor specific web page elements and execute conditional actions.

## 🚀 项目概述 (Overview)

**Web-Data-Monitor-GUI** 是一个功能全面的网页自动化监控工具，使用 **Python** 编写，结合 **Selenium** 实现对网页元素的动态监测。

用户可以通过友好的 **Tkinter GUI 界面**设置监控目标的 URL、元素选择器和检查频率。当被监控元素的值发生变化，或满足预设的条件（如值增大、包含特定文本）时，程序可以自动触发**桌面通知**，甚至执行**自动化点击**等动作。

本项目非常适用于需要实时关注网页信息变动（如库存、价格、抢购状态等）的场景。

## ✨ 主要特点 (Features)

* **🖥️ 图形化界面 (GUI)：** 使用 Tkinter 构建，提供友好的配置和日志查看界面。
* **🌐 网页数据监测：** 基于 **Selenium**，能够处理动态加载内容的网页（支持 JavaScript）。
* **🔗 灵活的选择器：** 支持 ID、Class、XPath、CSS Selector 等多种元素定位方式。
* **🛠️ 条件自动化动作：** 支持设定多种触发条件（`any_change`, `contains`, `equals`, `greater`, `less`），并可执行跳转 URL 或点击元素等动作。
* **🔔 实时通知：** 通过 `plyer` 库发送桌面通知，及时提醒用户数据变化。
* **🔒 Cookie/配置管理：** 支持手动登录保存 Cookies，以便监控需要登录的页面；支持配置的保存与加载。
* **⚙️ 独立线程运行：** 监控逻辑在独立线程中运行，确保 GUI 界面不会卡顿。

## ⚙️ 环境要求与安装 (Installation)

本项目需要 Python 3 环境，并依赖多个库。

### 1. 克隆仓库

```bash
git clone https://github.com/panjose/Web-Data-Monitor-GUI.git
cd Web-Data-Monitor-GUI
````

### 2\. 安装 Python 依赖

```bash
# 安装核心依赖库
pip install selenium plyer pandas openpyxl
```

### 3\. 浏览器驱动 (WebDriver)

本项目默认使用 **Chrome 浏览器**。请确保您的系统已安装 Chrome 浏览器，并下载与其版本匹配的 **ChromeDriver**。

  * 建议使用 `webdriver-manager` 库来自动化驱动下载（如果您的项目中未使用，可以手动安装 `pip install webdriver-manager`）。
  * 如果手动下载，请确保 ChromeDriver 的路径位于系统 PATH 中，或与脚本放在同一目录下。

## 📚 使用指南 (Usage Guide)

### 1\. 启动程序

```bash
python web-monitor-tool.py
```

### 2\. 登录设置 (Login Setup)

如果您要监控需要登录后才能访问的页面：

1.  在 **【登录设置】** 标签页输入登录页面的 **URL**。
2.  点击 **【手动登录】** 按钮。程序将打开一个浏览器窗口，请您手动完成登录操作。
3.  登录完成后，回到终端按下 **Enter** 键，程序将自动保存 Cookies，后续监控将默认使用这些 Cookies。

### 3\. 配置监控目标

1.  切换到 **【监控目标】** 标签页。
2.  输入待监控页面的 **URL**、目标元素的 **选择器**（如 XPath）和 **选择器类型**。
3.  设定 **检查间隔**（秒）。
4.  （可选）点击 **【测试选择器】** 按钮，验证元素是否能被正确抓取。
5.  点击 **【添加目标】** 按钮。

### 4\. 配置动作规则

1.  切换到 **【动作规则】** 标签页。
2.  设置 **触发条件**（例如：`greater`，条件值填 `100`）。
3.  设置 **动作 URL**（触发时跳转的页面）和 **动作元素**（触发时要点击的元素）。
4.  勾选 **【发送通知】**。
5.  点击 **【添加规则】** 按钮。

### 5\. 开始监控

1.  点击主界面的 **【保存配置】** 按钮，以便下次加载。
2.  点击 **【开始监控】** 按钮，程序将进入后台监控循环。
3.  所有日志和触发信息将在 **【监控日志】** 标签页显示。


## 🛠️ 核心技术栈 (Technology Stack)

| 模块 | 作用 | 库/技术 |
| :--- | :--- | :--- |
| **Web 自动化** | 驱动浏览器，抓取动态数据 | `selenium` (WebDriver, By, EC) |
| **用户界面** | 配置输入与日志展示 | `tkinter` (ttk, messagebox, scrolledtext) |
| **通知** | 跨平台桌面通知 | `plyer` (notification) |
| **并发** | 后台监控与前台 GUI 隔离 | `threading`, `queue` |
| **数据序列化** | 配置和 Cookies 的保存与加载 | `json`, `pickle` |
