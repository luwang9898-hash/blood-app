# 运动员血液指标分析系统 - Web版

## 📦 项目结构

```
项目文件夹/
│
├── app.py              # 主应用程序（Streamlit界面）⭐最重要
├── config.py           # 配置文件（参考范围、运动员名单等）
├── requirements.txt    # Python依赖包列表
└── README.md           # 使用说明（本文件）
```

---

## 🚀 快速开始

### 第一步：安装依赖（首次使用）

```bash
pip install streamlit pandas matplotlib numpy openpyxl
```

**命令解释**：
- `pip` - Python的包管理工具（built-in）
- `install` - 安装命令
- 后面列出的是需要安装的包名称

### 第二步：运行程序

```bash
streamlit run app.py
```

**命令解释**：
- `streamlit` - Streamlit的命令行工具
- `run` - 运行命令
- `app.py` - 要运行的Python文件

**预期结果**：
浏览器会自动打开，显示：`http://localhost:8501`

---

## 📝 逐行代码讲解

### 1. 导入模块（app.py 前20行）

```python
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
```

**解释**：
- `import` - Python的导入关键字（built-in）
- `as` - 给模块起别名
- `st` - 我们自己起的别名（our own naming）
- `pd`, `plt` - 社区常用的约定俗成的别名

**类比理解**：
就像给"中华人民共和国"起个简称"中国"，方便后续使用

---

### 2. 文件上传组件（app.py 第158行左右）

```python
uploaded_file = st.file_uploader(
    "选择Excel文件",
    type=['xlsx', 'xls'],
    help="请上传包含'月周测试指标'工作表的Excel文件"
)
```

**逐参数解析**：

| 参数 | 类型 | 作用 | 是谁提供的 |
|------|------|------|-----------|
| `st.file_uploader` | 函数 | Streamlit的文件上传组件 | Streamlit built-in |
| `"选择Excel文件"` | 字符串 | 按钮上显示的文字 | 我们自己写的 |
| `type=['xlsx', 'xls']` | 列表 | 限制文件类型 | 我们自己写的 |
| `help="..."` | 字符串 | 鼠标悬停时的提示 | 我们自己写的 |
| `uploaded_file` | 变量 | 存储上传的文件对象 | 我们自己命名的 |

**输入输出示例**：

```
【用户操作】
1. 点击"Browse files"按钮
2. 选择"血液数据.xlsx"
3. 点击打开

【程序内部】
uploaded_file = <文件对象>
- 文件名：uploaded_file.name → "血液数据.xlsx"
- 文件内容：uploaded_file.read() → 二进制数据
```

---

### 3. 数据读取函数（app.py 第35行）

```python
def load_data(file_path_or_buffer):
    try:
        df = pd.read_excel(
            file_path_or_buffer,
            sheet_name='月周测试指标'
        )
        return df
    except Exception as e:
        st.error(f"数据读取失败：{e}")
        return None
```

**逐行解析**：

1. `def load_data(file_path_or_buffer):` 
   - `def` - Python定义函数的关键字（built-in）
   - `load_data` - 我们自己起的函数名（our own）
   - `file_path_or_buffer` - 参数名，我们自己起的（our own）

2. `try:` 
   - Python的异常处理关键字（built-in）
   - 作用：尝试执行代码，如果出错就跳到except

3. `df = pd.read_excel(...)`
   - `pd` - pandas模块的别名（前面import的）
   - `read_excel` - pandas的内置函数（pandas built-in）
   - `df` - 我们自己命名的变量（our own），代表DataFrame

4. `sheet_name='月周测试指标'`
   - `sheet_name` - `read_excel`函数的参数名（pandas定义的）
   - `'月周测试指标'` - 我们指定的工作表名称（our own value）

5. `return df`
   - `return` - Python的返回关键字（built-in）
   - `df` - 返回的变量

6. `except Exception as e:`
   - `except` - Python捕获异常的关键字（built-in）
   - `Exception` - Python的异常类（built-in）
   - `e` - 我们自己起的变量名，存储错误信息（our own）

7. `st.error(f"数据读取失败：{e}")`
   - `st.error` - Streamlit显示错误消息的函数（Streamlit built-in）
   - `f"..."` - Python的f-string格式化字符串（Python 3.6+ built-in）
   - `{e}` - 在字符串中插入变量e的值

**输入输出示例**：

```python
# 示例1：成功读取
input: load_data("data.xlsx")
output: DataFrame对象，包含所有数据

# 示例2：文件不存在
input: load_data("不存在.xlsx")
output: None（并在页面显示红色错误消息）
```

---

### 4. 判断指标状态函数（app.py 第84行）

```python
def get_indicator_status(indicator, value, ref_ranges):
    if indicator not in ref_ranges or pd.isna(value):
        return '数据缺失'
    
    ranges = ref_ranges[indicator]
    low_1 = ranges.get('low_1')
    low_2 = ranges.get('low_2')
    high_2 = ranges.get('high_2')
    high_1 = ranges.get('high_1')
    
    if pd.notna(low_1) and value < low_1:
        return '严重偏低'
    elif pd.notna(low_2) and value < low_2:
        return '偏低'
    elif pd.notna(high_1) and value > high_1:
        return '严重偏高'
    elif pd.notna(high_2) and value > high_2:
        return '偏高'
    else:
        return '正常'
```

**逐步解析**：

**第1步：检查数据是否存在**
```python
if indicator not in ref_ranges or pd.isna(value):
```
- `not in` - Python的成员测试操作符（built-in）
- `or` - Python的逻辑或操作符（built-in）
- `pd.isna(value)` - pandas检查是否为空值的函数（pandas built-in）

**输入输出示例**：
```python
# 情况1：指标不在参考范围中
indicator = "不存在的指标"
ref_ranges = {'红细胞': {...}, '血红蛋白': {...}}
→ "不存在的指标" not in ref_ranges → True → 返回'数据缺失'

# 情况2：值为空
indicator = "红细胞"
value = None (或 NaN)
→ pd.isna(None) → True → 返回'数据缺失'
```

**第2步：获取参考范围**
```python
ranges = ref_ranges[indicator]
low_1 = ranges.get('low_1')
```
- `ref_ranges[indicator]` - 字典取值（Python built-in）
- `ranges.get('low_1')` - 字典的get方法（Python built-in）

**为什么用get而不用[]？**

```python
# 方法1：使用 []
value = dict['key']  # 如果key不存在，会报错KeyError

# 方法2：使用 get()
value = dict.get('key')  # 如果key不存在，返回None（不报错）

# 类比：
# [] = 强制要求 - "必须有这个东西，否则就报错！"
# get() = 温和请求 - "有就给我，没有就算了（返回None）"
```

**第3步：判断状态**
```python
if pd.notna(low_1) and value < low_1:
    return '严重偏低'
elif pd.notna(low_2) and value < low_2:
    return '偏低'
```

**完整示例**：
```python
# 输入
indicator = '红细胞'
value = 4.5
ref_ranges = {
    '红细胞': {
        'low_1': 4.7,
        'low_2': 4.91,
        'high_2': 5.38,
        'high_1': 5.61
    }
}

# 执行过程
ranges = {'low_1': 4.7, 'low_2': 4.91, 'high_2': 5.38, 'high_1': 5.61}
low_1 = 4.7
low_2 = 4.91

# 判断
4.5 < 4.7?  → True  → 返回'严重偏低'

# 输出
'严重偏低'
```

---

### 5. 趋势图绘制函数（app.py 第124行）

```python
def plot_trend_chart(athlete_df, indicator, ref_ranges):
    # 步骤1：检查数据
    if indicator not in athlete_df.columns:
        return None
    
    # 步骤2：准备数据
    plot_df = athlete_df[['Date', indicator]].copy()
    plot_df = plot_df.dropna(subset=[indicator])
    plot_df = plot_df.sort_values('Date')
    
    # 步骤3：创建图表
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # 步骤4：绘制趋势线
    x = range(len(plot_df))
    y = plot_df[indicator].values
    ax.plot(x, y, marker='o', linewidth=2)
    
    # 步骤5：添加参考线
    if indicator in ref_ranges:
        ranges = ref_ranges[indicator]
        if pd.notna(ranges.get('high_2')):
            ax.axhline(y=ranges['high_2'], color='red', linestyle='--')
    
    return fig
```

**关键步骤详解**：

**步骤2：数据准备**
```python
plot_df = athlete_df[['Date', indicator]].copy()
```

**拆解分析**：
- `athlete_df` - 我们传入的DataFrame（our variable）
- `[['Date', indicator]]` - DataFrame的列选择（pandas syntax）
  - 注意：双层方括号`[[]]`
  - 外层`[]` - 表示"取列"操作
  - 内层`[]` - 表示"列名列表"
- `.copy()` - 复制数据（pandas built-in method）

**为什么要copy？**
```python
# 不用copy（危险⚠️）
plot_df = athlete_df[['Date', '红细胞']]
plot_df['新列'] = 123  # 这会影响原始的athlete_df！

# 用copy（安全✅）
plot_df = athlete_df[['Date', '红细胞']].copy()
plot_df['新列'] = 123  # 只影响plot_df，不影响athlete_df
```

**类比**：
- 不copy = 直接在原文件上修改
- copy = 先复制一份，在副本上修改

**步骤3：创建图表**
```python
fig, ax = plt.subplots(figsize=(10, 5))
```

**参数详解**：
- `plt.subplots` - matplotlib创建图表的函数（matplotlib built-in）
- `figsize=(10, 5)` - 图表大小：宽10英寸，高5英寸
- `fig` - 图表对象（Figure）
- `ax` - 坐标轴对象（Axes）

**输入输出**：
```python
input: plt.subplots(figsize=(10, 5))
output: (fig, ax)两个对象
- fig: 整个图表的"画布"
- ax: 图表的"坐标系"

# 类比理解
fig = 画纸
ax = 画纸上的坐标网格
```

**步骤4：绘制线条**
```python
x = range(len(plot_df))
y = plot_df[indicator].values
ax.plot(x, y, marker='o', linewidth=2)
```

**详细分析**：

1. `x = range(len(plot_df))`
   - `len(plot_df)` - 获取DataFrame的行数（Python built-in）
   - `range()` - 生成数字序列（Python built-in）
   
   **示例**：
   ```python
   len(plot_df) = 5  # 有5行数据
   range(5) = [0, 1, 2, 3, 4]  # x轴坐标
   ```

2. `y = plot_df[indicator].values`
   - `plot_df[indicator]` - 选择某一列（pandas）
   - `.values` - 转为numpy数组（pandas attribute）
   
   **示例**：
   ```python
   plot_df['红细胞'] = pandas Series: [4.5, 4.7, 4.9, 5.0, 5.1]
   plot_df['红细胞'].values = numpy array: [4.5, 4.7, 4.9, 5.0, 5.1]
   ```

3. `ax.plot(x, y, marker='o', linewidth=2)`
   - `ax.plot` - matplotlib绘图方法（matplotlib built-in）
   - 参数详解：
     - `x` - x轴坐标列表
     - `y` - y轴坐标列表  
     - `marker='o'` - 数据点样式（圆圈）
     - `linewidth=2` - 线宽为2

**绘图流程可视化**：
```
数据：
x = [0, 1, 2, 3, 4]
y = [4.5, 4.7, 4.9, 5.0, 5.1]

绘图过程：
点(0, 4.5) → ●
点(1, 4.7) → ●
点(2, 4.9) → ●
点(3, 5.0) → ●
点(4, 5.1) → ●

然后用线连接：
●——●——●——●——●
```

---

## 🎯 关键概念对比表

### 内置(Built-in) vs 自定义(Our Own)

| 类型 | 例子 | 来源 | 说明 |
|------|------|------|------|
| **Python built-in** | `len()`, `range()`, `if`, `for` | Python语言 | 不需要import |
| **Pandas built-in** | `pd.read_excel()`, `df.dropna()` | pandas库 | 需要`import pandas` |
| **Streamlit built-in** | `st.title()`, `st.button()` | streamlit库 | 需要`import streamlit` |
| **Matplotlib built-in** | `plt.plot()`, `ax.set_title()` | matplotlib库 | 需要`import matplotlib` |
| **Our own variables** | `athlete_df`, `plot_df`, `indicator` | 我们自己 | 我们命名的变量 |
| **Our own functions** | `load_data()`, `clean_data()` | 我们自己 | 我们写的函数 |

---

## 💡 重要提示

### 1. 变量命名的智慧

**好的命名（推荐）**：
```python
athlete_df       # df表示DataFrame
uploaded_file    # 明确表示上传的文件
ref_ranges       # 参考范围
```

**不好的命名（不推荐）**：
```python
a                # 太简短，不知道是什么
data123          # 数字没有意义
temp             # 太通用
```

### 2. 函数 vs 方法

**函数（Function）**：
```python
len(df)          # len是独立的函数
pd.read_excel()  # read_excel是pandas模块的函数
```

**方法（Method）**：
```python
df.head()        # head是DataFrame对象的方法
df.dropna()      # dropna是DataFrame对象的方法
```

**区别**：
- 函数：独立存在，需要传参数
- 方法：属于某个对象，通过`.`调用

**类比**：
- 函数 = 工具（锤子）：你拿着锤子去敲钉子
- 方法 = 内置功能（手机的拍照）：手机自己有拍照功能

---

## 🚀 扩展建议

### 如果想添加更多功能

1. **添加雷达图**：
   - 在`plot_trend_chart`函数旁边创建`plot_radar_chart`函数
   - 参考你原有代码的雷达图部分

2. **生成Word报告**：
   - 安装`python-docx`库
   - 创建`generate_word_report`函数

3. **添加更多图表类型**：
   - 参考matplotlib文档
   - 学习`plt.bar()`, `plt.scatter()`等

---

## ❓ 常见问题

### Q1: 为什么要分成app.py和config.py？

A: **模块化设计**（经济学思维：分工协作）
- `config.py` = 配置中心（专门存储数据）
- `app.py` = 主程序（专门处理逻辑）

**好处**：
- 修改参考范围时，只需改config.py
- 代码更清晰，容易维护

### Q2: DataFrame和普通列表有什么区别？

A: **类比理解**

```python
# 普通列表（List）= 购物清单
list = ['苹果', '香蕉', '橙子']
# 特点：简单，但只能存一列数据

# DataFrame = Excel表格
df = pd.DataFrame({
    '水果': ['苹果', '香蕉', '橙子'],
    '价格': [5, 3, 4],
    '数量': [10, 15, 8]
})
# 特点：可以存多列，有行列索引，功能强大
```

### Q3: 什么时候用if，什么时候用try-except？

A: 
- `if` - 预期内的情况分支
- `try-except` - 预期外的错误处理

```python
# 用if
if age >= 18:
    print("成年人")
else:
    print("未成年")

# 用try-except
try:
    file = open("data.txt")
except FileNotFoundError:
    print("文件不存在")  # 预料到可能找不到文件
```

---

## 📚 学习资源

1. **Streamlit官方文档**：https://docs.streamlit.io
2. **Pandas官方文档**：https://pandas.pydata.org
3. **Matplotlib教程**：https://matplotlib.org/stable/tutorials/index.html

---

## 🎓 给PhD学生的建议

1. **不要一次性理解所有代码**
   - 先让程序跑起来
   - 然后慢慢理解每个部分

2. **从修改开始学习**
   - 改一下标题文字，看效果
   - 改一下颜色，看变化
   - 通过试错学习

3. **用经济学思维理解编程**
   - 函数 = 生产函数（输入→处理→输出）
   - 变量 = 资源（需要优化使用）
   - 代码复用 = 规模经济

---

## 🌟 成功标志

当你能做到以下几点时，说明你已经掌握了：

✅ 能独立运行程序
✅ 能修改界面文字和颜色
✅ 能理解数据是如何从Excel到图表的
✅ 能向课题组同事演示如何使用
✅ 能解释"为什么需要copy数据"

---

**祝你成功！🎉**

有任何问题都可以随时问我！
