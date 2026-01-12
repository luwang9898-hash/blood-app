"""
运动员血液指标分析系统 - 增强版
包含：表格图、趋势图（多运动员对比）、雷达图
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from datetime import datetime
from scipy.interpolate import make_interp_spline
# ========== 中文字体配置（完整版）==========
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# 获取字体文件路径
font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'SimHei.ttf')

# 检查字体文件是否存在
if os.path.exists(font_path):
    # 临时注册字体
    fm.fontManager.addfont(font_path)
    
    # 设置字体
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    print(f"✅ 成功加载中文字体：{font_path}")
else:
    print(f"❌ 字体文件不存在：{font_path}")
    # 使用默认字体
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
# 导入配置

from config import (
    MALE_ATHLETES, FEMALE_ATHLETES,
    MALE_REF_RANGES, FEMALE_REF_RANGES,
    COLUMN_NAME_MAPPING, TREND_INDICATORS
)

# ============================================================================
# 参考范围解析函数
# ============================================================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "blood2026":  # ← 改成你的密码
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("密码", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("密码", type="password", on_change=password_entered, key="password")
        st.error("密码错误")
        return False
    return True


if not check_password():
    st.stop()
def parse_range_value(value_str):
    """
    解析范围值字符串

    支持格式：
    - "210-430" → (210, 430)
    - "< 210" → (None, 210)
    - "> 500" → (500, None)
    - "36.63" → (36.63, 36.63)
    - "6.0-20.0" → (6.0, 20.0)
    - "-" → (None, None)
    """
    if pd.isna(value_str) or str(value_str).strip() == '-' or str(value_str).strip() == '':
        return None, None

    value_str = str(value_str).strip()

    # 处理 "< X" 格式
    if value_str.startswith('<'):
        val = value_str.replace('<', '').strip()
        try:
            return None, float(val)
        except:
            return None, None

    # 处理 "> X" 格式
    if value_str.startswith('>'):
        val = value_str.replace('>', '').strip()
        try:
            return float(val), None
        except:
            return None, None

    # 处理 "X-Y" 格式
    if '-' in value_str:
        parts = value_str.split('-')
        if len(parts) == 2:
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except:
                return None, None

    # 处理单个数值
    try:
        val = float(value_str)
        return val, val
    except:
        return None, None


def load_reference_ranges_from_excel(file):
    """
    从上传的Excel文件加载参考范围

    返回：
    - male_ranges: 男性参考范围字典
    - female_ranges: 女性参考范围字典
    """
    try:
        # 读取参考范围sheet
        df = pd.read_excel(file, sheet_name='参考范围')

        male_ranges = {}
        female_ranges = {}
        common_ranges = {}

        # 遍历每一行
        for idx, row in df.iterrows():
            indicator = str(row['指标名称']).strip()
            gender = str(row['性别']).strip()

            # 解析五档范围
            severe_low_val = row['严重偏低 (<)']
            low_range = row['偏低 (范围)']
            normal_range = row['参考范围 (正常)']
            high_range = row['偏高 (范围)']
            severe_high_val = row['严重偏高 (>)']

            # 解析正常范围（这是最重要的）
            normal_low, normal_high = parse_range_value(normal_range)

            # 解析其他范围
            severe_low_lower, severe_low_upper = parse_range_value(severe_low_val)
            low_lower, low_upper = parse_range_value(low_range)
            high_lower, high_upper = parse_range_value(high_range)
            severe_high_lower, severe_high_upper = parse_range_value(severe_high_val)

            # 构建范围字典
            range_dict = {
                'severe_low_1': severe_low_lower if severe_low_lower is not None else severe_low_upper,
                'low_1': low_lower if low_lower is not None else None,
                'low_2': normal_low,  # 正常范围下限
                'high_2': normal_high,  # 正常范围上限
                'high_1': high_upper if high_upper is not None else None,
                'severe_high_1': severe_high_upper if severe_high_upper is not None else severe_high_lower,
            }

            # 根据性别分类
            if gender == '男':
                male_ranges[indicator] = range_dict
            elif gender == '女':
                female_ranges[indicator] = range_dict
            elif gender == '通用':
                common_ranges[indicator] = range_dict

        # 合并通用范围到男女范围
        for indicator, range_dict in common_ranges.items():
            if indicator not in male_ranges:
                male_ranges[indicator] = range_dict
            if indicator not in female_ranges:
                female_ranges[indicator] = range_dict

        return male_ranges, female_ranges

    except Exception as e:
        st.error(f"解析参考范围文件出错：{str(e)}")
        return {}, {}


# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ========== 页面配置 ==========
st.set_page_config(
    page_title="运动员血液指标分析系统 - 增强版",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 增强配置 ==========

# 主题配置 - 用于表格图
THEME_CONFIG = {
    '0_关键指标摘要': {
        '关键指标': {
            '血红蛋白': '血红蛋白Hb (g/L)',
            '铁蛋白': '铁蛋白Ferri (Ng/ml)',
            '肌酸激酶': '肌酸激酶CK (U/L)',
            '睾酮': '睾酮T (ng/dl)',
            '皮质醇': '皮质醇(ug/dL)'
        }
    },

    '1_训练负荷耐受性': {
        '一、肌肉对训练强度的耐受性': {'肌酸激酶': '肌酸激酶CK (U/L)', '肌酐': '肌酐 (μmol/L)'},
        '二、对训练量的耐受性及能量代谢': {
            '血尿素': '血尿素BUN (mmol/L)', '皮质醇': '皮质醇(ug/dL)', '血糖': '血糖(mmol/L)'},
    },
    '2_合成代谢与恢复能力': {
        '一、促合成-恢复能力': {'睾酮': '睾酮T (ng/dl)', '游离睾酮': '游离睾酮FT (ng/dl)'},
        '二、氧转运': {
            '红细胞': '红细胞RBC (10¹²/L)', '血红蛋白': '血红蛋白Hb (g/L)',
            '网织红细胞百分比': '网织红细胞百分比retic%',
        },
    },
    '3_铁状态与恢复能力': {
        '一、铁状态与恢复能力': {
            '铁蛋白': '铁蛋白Ferri (Ng/ml)', '血红蛋白': '血红蛋白Hb (g/L)',
            '平均红细胞体积': '平均红细胞体积MCV (fl)', '平均红细胞血红蛋白': '平均红细胞血红蛋白MCH (pg)',
            '平均红细胞血红蛋白浓度': '平均红细胞血红蛋白浓度MCHC (g/L)',
            '超敏C反应蛋白': '超敏C反应蛋白hsCRP (mg/L)',
        }
    },
    '4_炎症免疫反应': {
        '一、高尿酸血症': {'尿酸': '尿酸UA (umol/L)'},
        '二、免疫/炎性反应': {
            '超敏C反应蛋白': '超敏C反应蛋白hsCRP (mg/L)', '白细胞': '白细胞WBC (10⁹/L)',
            '血小板': '血小板PLT (10⁹/L)',
        }
    },
}

# 雷达图配置
RADAR_FIELDS = ['睾酮', '皮质醇', '肌酸激酶', '血尿素', '血红蛋白', '铁蛋白', '白细胞', '网织红细胞百分比']
LOWER_IS_BETTER = ['肌酸激酶', '血尿素', '超敏C反应蛋白', '皮质醇']

# 颜色配置 - 五档评价配色
COLOR_SEVERE_LOW = '#4A90E2'     # 深海蓝（严重偏低）
COLOR_LOW = '#8BC1E9'            # 浅天蓝（偏低）
COLOR_NORMAL = '#E6E6E6'         # 云雾灰（正常）
COLOR_HIGH = '#E89A9D'           # 浅柔红（偏高/良好）
COLOR_SEVERE_HIGH = '#D05A5E'    # 深砖红（严重偏高/优秀）
COLOR_CATEGORY_HEADER = '#5C7CFA'  # 靛蓝（分类标题）
COLOR_CHART_BG = '#F8F9FA'       # 极浅灰（图表背景）
COLOR_MAIN = '#1f77b4'          # 主色调

# 雷达图样式
RADAR_STYLES = [
    {'color': '#8BC1E9', 'linewidth': 2, 'linestyle': ':'},   # 第1次 - 浅天蓝
    {'color': '#E89A9D', 'linewidth': 2, 'linestyle': '-.'},  # 第2次 - 浅柔红
    {'color': '#5C7CFA', 'linewidth': 2.5, 'linestyle': '--'}, # 第3次 - 靛蓝
    {'color': '#D05A5E', 'linewidth': 3, 'linestyle': '-'},   # 第4次（最新）- 深砖红
]

# ========== 数据加载函数 ==========

def load_data_final(file_path_or_buffer):
    """数据加载函数"""
    try:
        st.info("📊 开始读取数据...")

        df = pd.read_excel(
            file_path_or_buffer,
            sheet_name='月周测试指标',
            header=0,
            skiprows=lambda x: x in range(1, 11)
        )

        st.success(f"✅ 读取成功：{len(df)} 行，{len(df.columns)} 列")

        # 确保列名唯一
        new_columns = []
        for i, col in enumerate(df.columns):
            col_str = str(col)
            count = new_columns.count(col_str)
            if count > 0:
                unique_col = f"{col_str}#{i}"
                new_columns.append(unique_col)
            else:
                new_columns.append(col_str)

        df.columns = new_columns

        if not df.columns.duplicated().any():
            st.success(f"✅ 列名已唯一化：共 {len(df.columns)} 列")

        return df

    except Exception as e:
        st.error(f"❌ 数据读取失败：{e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def clean_data_final(df):
    """数据清洗函数"""
    if df is None:
        return None

    st.info("🧹 开始清洗数据...")

    # 删除空行
    df = df.dropna(how='all')
    df = df.reset_index(drop=True)

    # 处理姓名列
    if '姓名' in df.columns:
        name_cols = [col for col in df.columns if col.startswith('Name')]
        if not name_cols:
            df['Name'] = df['姓名']
        else:
            df['Name_final'] = df['姓名']

    # 处理日期列
    possible_date_cols = ['测试日期', '日期', '开始日期']
    date_col_found = False

    for col in possible_date_cols:
        if col in df.columns:
            try:
                date_cols = [c for c in df.columns if c.startswith('Date')]

                if not date_cols:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df['Date'] = df[col]
                    else:
                        df['Date'] = pd.to_datetime(df[col], errors='coerce')

                    df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
                    date_col_found = True
                else:
                    date_col_found = True

                break

            except Exception as e:
                continue

    if not date_col_found:
        df['Date_auto'] = pd.date_range(start='2024-01-01', periods=len(df), freq='D')
        df['DateStr'] = df['Date_auto'].dt.strftime('%Y-%m-%d')

    # 最终清理
    df = df.dropna(how='all')
    df = df.reset_index(drop=True)

    st.success(f"✅ 清洗完成：保留 {len(df)} 行有效数据")

    return df

# ========== 辅助函数 ==========

def get_indicator_status(indicator, value, ref_ranges):
    """判断指标状态（五档）"""
    if indicator not in ref_ranges or pd.isna(value):
        return '数据缺失', '#F0F8FF', 'N/A'

    ranges = ref_ranges[indicator]
    low_1 = ranges.get('low_1')
    low_2 = ranges.get('low_2')
    high_2 = ranges.get('high_2')
    high_1 = ranges.get('high_1')

    # 高优指标列表（高于正常范围是好事）
    high_is_better_indicators = ['铁蛋白', '血红蛋白', '睾酮', '游离睾酮']

    if pd.notna(low_1) and value < low_1:
        return '严重偏低', COLOR_SEVERE_LOW, 'severe_low'
    elif pd.notna(low_2) and value < low_2:
        return '偏低', COLOR_LOW, 'low'
    elif pd.notna(high_1) and value > high_1:
        # 判断是否是高优指标
        if indicator in high_is_better_indicators:
            return '优秀', COLOR_SEVERE_HIGH, 'excellent'
        else:
            return '严重偏高', COLOR_SEVERE_HIGH, 'severe_high'
    elif pd.notna(high_2) and value > high_2:
        # 判断是否是高优指标
        if indicator in high_is_better_indicators:
            return '良好', COLOR_HIGH, 'good'
        else:
            return '偏高', COLOR_HIGH, 'high'
    else:
        return '正常', COLOR_NORMAL, 'normal'

# 指标别名映射（用于处理常见的名称差异）
INDICATOR_ALIASES = {
    '平均红细胞血红蛋白浓度': ['平均红细胞血红浓度', 'MCHC', '平均血红蛋白浓度'],
    '平均红细胞血红蛋白': ['平均红细胞血红蛋白量', 'MCH'],
    '平均红细胞体积': ['平均红细胞容积', 'MCV'],
    '平均血红蛋白浓度': ['平均红细胞血红蛋白浓度', 'MCHC'],
    '超敏C反应蛋白': ['C反应蛋白', 'CRP', 'hsCRP', 'hs-CRP'],
    '网织红细胞百分比': ['网织红细胞', 'retic', 'Retic'],
}

def find_indicator_column(df, indicator):
    """智能查找指标列（支持带#的列名、模糊匹配、别名匹配）"""

    # 方法1：精确匹配
    if indicator in df.columns:
        return indicator

    # 方法2：别名匹配
    # 先查找是否有直接的别名定义
    if indicator in INDICATOR_ALIASES:
        for alias in INDICATOR_ALIASES[indicator]:
            if alias in df.columns:
                return alias
            # 也尝试前缀匹配别名
            possible_cols = [col for col in df.columns if str(col).startswith(alias)]
            if possible_cols:
                return possible_cols[0]

    # 反向查找：indicator是否是某个别名
    for main_name, aliases in INDICATOR_ALIASES.items():
        if indicator in aliases:
            # 尝试匹配主名称
            if main_name in df.columns:
                return main_name
            possible_cols = [col for col in df.columns if str(col).startswith(main_name)]
            if possible_cols:
                return possible_cols[0]
            # 尝试匹配其他别名
            for alias in aliases:
                if alias in df.columns:
                    return alias
                possible_cols = [col for col in df.columns if str(col).startswith(alias)]
                if possible_cols:
                    return possible_cols[0]

    # 方法3：前缀匹配（处理带#的列名）
    possible_cols = [col for col in df.columns if str(col).startswith(indicator)]
    if possible_cols:
        return possible_cols[0]

    # 方法4：去除空格后匹配
    indicator_no_space = indicator.replace(' ', '').replace('\u3000', '')
    for col in df.columns:
        col_no_space = str(col).replace(' ', '').replace('\u3000', '')
        if col_no_space == indicator_no_space:
            return col
        if col_no_space.startswith(indicator_no_space):
            return col

    # 方法5：部分匹配（宽松匹配）
    for col in df.columns:
        col_str = str(col)
        col_base = col_str.split('#')[0]  # 去除#后缀

        # 如果指标名是列名的子串
        if indicator in col_str or indicator in col_base:
            return col

        # 如果列名是指标名的子串
        if col_base in indicator:
            return col

    # 方法6：关键词匹配（最宽松）
    import re
    indicator_clean = re.sub(r'[（(].*?[）)]', '', indicator)  # 去除括号及内容
    indicator_clean = indicator_clean.strip()

    for col in df.columns:
        col_str = str(col).split('#')[0]  # 去除#后缀
        col_clean = re.sub(r'[（(].*?[）)]', '', col_str)
        col_clean = col_clean.strip()

        # 如果清理后的名称相同
        if indicator_clean == col_clean:
            return col

        # 如果指标名包含在列名中，或列名包含在指标名中
        if indicator_clean in col_clean or col_clean in indicator_clean:
            return col

    # 方法7：模糊匹配（允许1-2个字符不同）
    # 例如："平均红细胞血红浓度" vs "平均红细胞血红蛋白浓度"
    for col in df.columns:
        col_str = str(col).split('#')[0].strip()
        # 去除括号内容后比较
        col_clean = re.sub(r'[（(].*?[）)]', '', col_str).strip()
        indicator_clean_v2 = re.sub(r'[（(].*?[）)]', '', indicator).strip()

        # 如果长度相近（差距在3个字符以内）
        if abs(len(col_clean) - len(indicator_clean_v2)) <= 3:
            # 计算相似度：有多少个字符是相同的
            common_chars = sum(1 for c in indicator_clean_v2 if c in col_clean)
            similarity = common_chars / max(len(indicator_clean_v2), len(col_clean))

            # 如果相似度超过80%，认为匹配
            if similarity >= 0.8:
                return col

    return None

# ========== 图表生成函数 ==========

def plot_theme_table(athlete_df, theme_name, categories, ref_ranges, gender):
    """生成主题表格图"""
    if athlete_df.empty:
        return None, []

    latest_row = athlete_df.iloc[-1]
    latest_date = latest_row.get('DateStr', '未知')
    athlete_name = latest_row.get('Name', latest_row.get('Name_final', '未知'))

    cell_text = []
    cell_colors = []
    missing_indicators = []  # 记录缺失的指标

    for category_title, indicators in categories.items():
        # 添加分类标题行（4列）
        cell_text.append([category_title, '', '', ''])
        cell_colors.append([COLOR_CATEGORY_HEADER, COLOR_CATEGORY_HEADER, COLOR_CATEGORY_HEADER, COLOR_CATEGORY_HEADER])

        for col_key, col_name in indicators.items():
            # 查找实际的列名
            actual_col = find_indicator_column(athlete_df, col_key)

            # 获取正常范围
            range_str = "—"
            if col_key in ref_ranges:
                ranges = ref_ranges[col_key]
                low_2 = ranges.get('low_2')
                high_2 = ranges.get('high_2')

                if pd.notna(low_2) and pd.notna(high_2):
                    # 两个值都存在，显示范围
                    range_str = f"{low_2:.1f}-{high_2:.1f}"
                elif pd.notna(low_2):
                    # 只有下限
                    range_str = f"≥{low_2:.1f}"
                elif pd.notna(high_2):
                    # 只有上限
                    range_str = f"≤{high_2:.1f}"

            if actual_col and actual_col in latest_row.index:
                val = latest_row[actual_col]
                status, bg_color, _ = get_indicator_status(col_key, val, ref_ranges)

                if pd.notna(val):
                    if abs(val) >= 1000:
                        val_str = f"{val:.0f}"
                    elif abs(val) >= 100:
                        val_str = f"{val:.1f}"
                    else:
                        val_str = f"{val:.2f}"
                else:
                    val_str = "—"
                    status = "N/A"
                    bg_color = '#F0F8FF'
            else:
                val_str = "—"
                status = "未找到"
                bg_color = '#FFE4E1'  # 浅红色，表示列未找到
                missing_indicators.append((col_key, col_name))

            cell_text.append([f"  {col_name}", val_str, range_str, status])
            cell_colors.append(['#F8F8F8', bg_color, '#F8F8F8', bg_color])

    # 创建图表（4列）
    fig_height = len(cell_text) * 0.7 + 1.5
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.axis('off')

    col_widths = [0.45, 0.18, 0.18, 0.19]
    table = ax.table(
        cellText=cell_text,
        colLabels=['检测指标', '结果', '正常范围', '评价'],
        cellColours=cell_colors,
        loc='center',
        cellLoc='center',
        colColours=['#333333'] * 4,
        colWidths=col_widths
    )

    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2.3)

    # 样式设置
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_edgecolor('white')
        if cell.get_facecolor() == COLOR_CATEGORY_HEADER:
            cell.set_text_props(weight='bold', color='white', ha='left')
            cell.set_edgecolor('white')
        else:
            cell.set_edgecolor('#DDDDDD')
            if r > 0 and c == 0:
                cell.get_text().set_ha('left')

    theme_display = theme_name.split('_')[-1]
    plt.title(f"{athlete_name} ({gender}) - {theme_display} ({latest_date})",
              y=0.99, fontsize=14, fontweight='bold')

    plt.tight_layout()

    return fig, missing_indicators

def plot_trend_chart_multi(df, indicator, ref_ranges, selected_athletes, date_range, gender):
    """绘制多运动员对比趋势图"""

    # 查找实际的列名
    actual_col = find_indicator_column(df, indicator)
    if not actual_col:
        return None

    # 筛选日期范围
    if date_range and len(date_range) == 2:
        # 将date转换为datetime64以匹配df['Date']的类型
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()
    else:
        df_filtered = df.copy()

    if df_filtered.empty:
        return None

    # 获取名字列
    name_col = 'Name' if 'Name' in df_filtered.columns else 'Name_final'

    # 只保留有该指标数据的日期
    df_with_indicator = df_filtered[df_filtered[actual_col].notna()].copy()

    if df_with_indicator.empty:
        return None

    # 获取所有选中运动员中有数据的日期（去重排序）
    dates_with_data = set()
    for athlete in selected_athletes:
        athlete_data = df_with_indicator[df_with_indicator[name_col] == athlete]
        if not athlete_data.empty:
            dates_with_data.update(athlete_data['DateStr'].unique())

    # 如果没有任何数据，返回None
    if not dates_with_data:
        return None

    # 排序日期
    all_dates = sorted(list(dates_with_data))
    date_to_index = {date: i for i, date in enumerate(all_dates)}

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_facecolor(COLOR_CHART_BG)

    # 标记正常范围
    if indicator in ref_ranges:
        ranges = ref_ranges[indicator]
        low_2 = ranges.get('low_2')
        high_2 = ranges.get('high_2')

        if pd.notna(low_2) and pd.notna(high_2):
            ax.axhspan(low_2, high_2, color=COLOR_NORMAL, alpha=0.15, zorder=0, label='理想范围')
            ax.axhline(low_2, color=COLOR_SEVERE_LOW, linestyle=':', linewidth=1, alpha=0.7)
            ax.axhline(high_2, color=COLOR_SEVERE_HIGH, linestyle=':', linewidth=1, alpha=0.7)

    # 协调配色列表（用于多运动员曲线）
    harmonious_colors = [
        '#4A90E2',  # 深海蓝
        '#D05A5E',  # 深砖红
        '#8BC1E9',  # 浅天蓝
        '#E89A9D',  # 浅柔红
        '#5C7CFA',  # 靛蓝
        '#9B59B6',  # 紫色
        '#1ABC9C',  # 青绿
        '#E67E22',  # 深橙
    ]

    # 确保有足够的颜色
    if len(selected_athletes) > len(harmonious_colors):
        colors = plt.cm.tab10(np.linspace(0, 1, len(selected_athletes)))
    else:
        colors = [harmonious_colors[i % len(harmonious_colors)] for i in range(len(selected_athletes))]

    # 绘制每个运动员的数据
    for idx, (athlete, color) in enumerate(zip(selected_athletes, colors)):
        athlete_data = df_with_indicator[df_with_indicator[name_col] == athlete].copy()

        if athlete_data.empty:
            continue

        athlete_data = athlete_data.sort_values('Date')
        valid_data = athlete_data.dropna(subset=[actual_col])

        if len(valid_data) == 0:
            continue

        x_data = np.array([date_to_index[d] for d in valid_data['DateStr']])
        y_data = valid_data[actual_col].values

        # 绘制平滑曲线
        if len(valid_data) > 1:
            try:
                x_smooth = np.linspace(x_data.min(), x_data.max(), 200)
                k = 2 if len(x_data) >= 3 else 1
                spl = make_interp_spline(x_data, y_data, k=k)
                y_smooth = spl(x_smooth)
                ax.plot(x_smooth, y_smooth, color=color, linewidth=2.5, label=athlete, alpha=0.8)
            except:
                ax.plot(x_data, y_data, color=color, linewidth=2.5, label=athlete, alpha=0.8)
        else:
            ax.plot(x_data, y_data, color=color, linewidth=2.5, label=athlete, linestyle='--', alpha=0.6)

        # 绘制数据点
        ax.plot(x_data, y_data, marker='o', markersize=8, markerfacecolor='white',
                markeredgecolor=color, markeredgewidth=2, linestyle='None')

    # 设置坐标轴 - 只显示有数据的日期
    ax.set_xticks(np.arange(len(all_dates)))
    ax.set_xticklabels(all_dates, rotation=45, ha='right')

    plt.title(f"{indicator} 趋势对比 ({gender})", fontsize=14, fontweight='bold')
    plt.xlabel('测试日期', fontsize=12)
    plt.ylabel(f'{indicator}', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 图例
    plt.legend(loc='upper left', bbox_to_anchor=(1.01, 1), frameon=True)
    plt.tight_layout()

    return fig

def plot_radar_chart_with_baseline(athlete_df, radar_fields, lower_is_better, ref_ranges, athlete_name, baseline_athletes_df, gender):
    """
    绘制单个运动员的雷达图（最近4次测试）

    参数：
    - athlete_df: 主运动员的数据
    - radar_fields: 雷达图指标列表
    - lower_is_better: 逆指标列表
    - ref_ranges: 参考范围
    - athlete_name: 主运动员姓名
    - baseline_athletes_df: 用于计算baseline的所有运动员数据（包括主运动员）
    - gender: 性别
    """
    if athlete_df.empty:
        return None

    # 获取主运动员的最近4次数据
    last_4_dates = athlete_df['DateStr'].unique()[-4:]
    if len(last_4_dates) == 0:
        return None

    # 计算baseline统计值：使用对比运动员组的最近4次数据
    # 这样可以看到主运动员相对于对比组的表现
    baseline_stats = {}

    for field in radar_fields:
        actual_col = find_indicator_column(baseline_athletes_df, field)
        if actual_col:
            col_data = baseline_athletes_df[actual_col].dropna()
            if len(col_data) >= 2:
                baseline_stats[field] = {'mu': col_data.mean(), 'sigma': col_data.std()}
            else:
                baseline_stats[field] = {'mu': col_data.mean() if len(col_data) > 0 else 0, 'sigma': 1}
        else:
            baseline_stats[field] = {'mu': 0, 'sigma': 1}

    # 计算Z-score范围（用于设置坐标轴）
    athlete_z_scores = []
    for date in last_4_dates:
        date_row = athlete_df[athlete_df['DateStr'] == date]
        if date_row.empty:
            continue

        for field in radar_fields:
            actual_col = find_indicator_column(date_row, field)
            stats = baseline_stats.get(field)

            if not stats or stats['sigma'] == 0:
                z = 0
            else:
                if actual_col and actual_col in date_row.columns:
                    val = date_row[actual_col].values[0]
                    if pd.notna(val):
                        z = (val - stats['mu']) / stats['sigma']
                    else:
                        z = 0
                else:
                    z = 0

            if field in lower_is_better:
                z = -z
            athlete_z_scores.append(z)

    max_abs_z = max([abs(z) for z in athlete_z_scores]) if athlete_z_scores else 0
    limit = max(2.5, np.ceil(max_abs_z * 2) / 2)

    # 设置标签
    labels = [f + ('\n(逆)' if f in lower_is_better else '') for f in radar_fields]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    plt.ylim(-limit - 1.0, limit)

    # 绘制零线
    ax.plot(angles, [0] * len(angles), color='red', linewidth=2, linestyle='--', zorder=0.5)

    # 选择样式 - 最近4次测试
    styles = RADAR_STYLES[-len(last_4_dates):]

    # 绘制主运动员的最近4次数据
    for i, date in enumerate(last_4_dates):
        date_row = athlete_df[athlete_df['DateStr'] == date]
        if date_row.empty:
            continue

        values = []
        for field in radar_fields:
            actual_col = find_indicator_column(date_row, field)
            stats = baseline_stats.get(field)

            if not stats or stats['sigma'] == 0:
                z = 0
            else:
                if actual_col and actual_col in date_row.columns:
                    val = date_row[actual_col].values[0]
                    if pd.notna(val):
                        z = (val - stats['mu']) / stats['sigma']
                    else:
                        z = 0
                else:
                    z = 0

            if field in lower_is_better:
                z = -z
            values.append(z)

        values.append(values[0])
        style = styles[i]

        ax.plot(angles, values, color=style['color'], linewidth=style['linewidth'],
                linestyle=style['linestyle'], label=date, zorder=2)

        # 最新一次填充
        if i == len(last_4_dates) - 1:
            ax.fill(angles, values, color=style['color'], alpha=0.15, zorder=3)

    # 设置坐标轴
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=11)

    # 数值刻度
    step = 1 if limit <= 3 else 2
    z_ticks = np.arange(-int(limit), int(limit) + 1, step)
    ax.set_yticks(z_ticks)
    ax.set_yticklabels([f'{i:.0f}' for i in z_ticks], color='grey', size=10)

    plt.title(f"{athlete_name} ({gender}) - 机能状态 Z-Score 雷达图",
              fontsize=16, y=1.08, fontweight='bold')
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))

    plt.tight_layout()

    return fig

# ========== 主应用 ==========

def main():
    st.title("🏃 运动员血液指标分析系统")
    st.markdown("**包含：表格图、多运动员趋势对比、雷达图**")
    st.markdown("---")

    # === 侧边栏 ===
    st.sidebar.header("📂 数据上传")

    # 数据文件上传
    uploaded_file = st.sidebar.file_uploader(
        "1️⃣ 上传血液数据Excel",
        type=['xlsx', 'xls'],
        help="请上传包含'月周测试指标'工作表的Excel文件",
        key="data_file"
    )

    # 参考范围文件上传
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 参考范围设置**")

    use_custom_ranges = st.sidebar.checkbox(
        "使用自定义参考范围",
        value=False,
        help="勾选后可上传自己的参考范围Excel文件"
    )

    custom_ranges_file = None
    if use_custom_ranges:
        custom_ranges_file = st.sidebar.file_uploader(
            "2️⃣ 上传参考范围Excel",
            type=['xlsx', 'xls'],
            help="Excel文件需包含'参考范围'工作表",
            key="ranges_file"
        )

    if uploaded_file is None:
        st.info("👈 请在左侧上传Excel数据文件")
        st.stop()

    # === 加载参考范围 ===
    if use_custom_ranges and custom_ranges_file is not None:
        with st.spinner("正在加载自定义参考范围..."):
            male_ref_ranges, female_ref_ranges = load_reference_ranges_from_excel(custom_ranges_file)
            if male_ref_ranges and female_ref_ranges:
                st.sidebar.success(f"✅ 已加载自定义范围（男:{len(male_ref_ranges)}项，女:{len(female_ref_ranges)}项）")
            else:
                st.sidebar.warning("⚠️ 自定义范围加载失败，使用默认范围")
                male_ref_ranges = MALE_REF_RANGES
                female_ref_ranges = FEMALE_REF_RANGES
    else:
        # 使用默认范围
        male_ref_ranges = MALE_REF_RANGES
        female_ref_ranges = FEMALE_REF_RANGES
        if not use_custom_ranges:
            st.sidebar.info("ℹ️ 使用默认参考范围")

    # === 数据加载 ===
    with st.spinner("正在加载数据..."):
        df = load_data_final(uploaded_file)

        if df is None:
            st.stop()

        df = clean_data_final(df)

        if df is None or len(df) == 0:
            st.error("❌ 数据清洗后为空")
            st.stop()

    st.success(f"🎉 数据准备完成：共 {len(df)} 条记录")

    # === 数据预览 ===
    with st.expander("👀 查看数据"):
        st.write("**前20行：**")
        st.write(df.head(20))

    st.markdown("---")

    # === 用户选择 ===
    col1, col2 = st.columns(2)

    with col1:
        gender = st.selectbox("选择性别", ["男", "女"])

    # 筛选性别
    if '性别' in df.columns:
        gender_df = df[df['性别'] == gender].copy()
    else:
        st.warning("⚠️ 数据中没有'性别'列")
        gender_df = df.copy()

    if len(gender_df) == 0:
        st.warning(f"⚠️ 没有{gender}运动员的数据")
        st.stop()

    # 获取运动员列表
    name_col = None
    for possible_name in ['Name_final', 'Name', '姓名']:
        if possible_name in gender_df.columns:
            name_col = possible_name
            break

    if not name_col:
        st.error("❌ 未找到姓名列")
        st.stop()

    athletes = sorted(gender_df[name_col].dropna().unique())
    ref_ranges = male_ref_ranges if gender == "男" else female_ref_ranges

    with col2:
        athlete_name = st.selectbox(
            "选择运动员",
            athletes,
            help=f"共 {len(athletes)} 名{gender}运动员"
        )

    # 筛选运动员数据
    athlete_df = gender_df[gender_df[name_col] == athlete_name].copy()

    date_col = 'Date' if 'Date' in athlete_df.columns else 'Date_auto'
    if date_col in athlete_df.columns:
        athlete_df = athlete_df.sort_values(date_col)

    st.info(f"📊 **{athlete_name}**（{gender}）- 共 {len(athlete_df)} 次测试")

    st.markdown("---")

    # === 功能选项卡 ===
    tab1, tab2, tab3, tab4 = st.tabs(["📋 主题表格", "📈 趋势对比", "🎯 雷达图", "📊 数据表"])

    # --- Tab 1: 主题表格 ---
    with tab1:
        st.subheader("最新数据主题表格")
        st.markdown("显示最新一次测试的各项指标，使用五档判断")

        if st.button("🚀 生成主题表格", type="primary", use_container_width=True):
            with st.spinner("正在生成表格..."):

                for theme_name, categories in THEME_CONFIG.items():
                    st.markdown(f"### {theme_name.split('_')[-1]}")
                    result = plot_theme_table(athlete_df, theme_name, categories, ref_ranges, gender)

                    if result:
                        fig, missing = result
                        if fig:
                            st.pyplot(fig)
                            plt.close()
                        else:
                            st.info(f"ℹ️ {theme_name} 数据不足")
                    else:
                        st.info(f"ℹ️ {theme_name} 数据不足")

                st.success("✅ 表格生成完成！")

    # --- Tab 2: 趋势对比 ---
    with tab2:
        st.subheader("多运动员趋势对比")
        st.markdown("可以选择多个运动员和日期范围进行对比")

        # 选择对比运动员
        compare_athletes = st.multiselect(
            "选择对比运动员（可多选）",
            athletes,
            default=[athlete_name],
            help="选择要对比的运动员"
        )

        # 日期范围选择
        if date_col in gender_df.columns:
            min_date = gender_df[date_col].min()
            max_date = gender_df[date_col].max()

            date_range = st.date_input(
                "选择日期范围",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                help="选择要分析的日期范围"
            )
        else:
            date_range = None

        # 选择指标
        selected_indicators = st.multiselect(
            "选择要分析的指标",
            TREND_INDICATORS,
            default=TREND_INDICATORS[:3],
            help="选择要绘制趋势图的指标"
        )

        if st.button("🚀 生成趋势对比图", type="primary", use_container_width=True):
            if not compare_athletes:
                st.warning("⚠️ 请至少选择一个运动员")
            elif not selected_indicators:
                st.warning("⚠️ 请至少选择一个指标")
            else:
                with st.spinner("正在生成趋势图..."):
                    for indicator in selected_indicators:
                        st.markdown(f"### {indicator}")
                        fig = plot_trend_chart_multi(
                            gender_df, indicator, ref_ranges,
                            compare_athletes, date_range, gender
                        )
                        if fig:
                            st.pyplot(fig)
                            plt.close()
                        else:
                            st.info(f"ℹ️ {indicator} 数据不足")

                    st.success("✅ 趋势图生成完成！")

    # --- Tab 3: 雷达图 ---
    with tab3:
        st.subheader(f"{athlete_name}的机能状态雷达图")
        st.markdown(f"显示**{athlete_name}**最近4次测试的Z-Score雷达图")

        # 说明Z-Score计算方式
        st.info("💡 **Z-Score计算说明**：使用对比运动员组的数据作为基准，计算该运动员相对于组内的表现")

        # 选择对比运动员组（用于计算baseline）
        radar_athletes = st.multiselect(
            "选择对比运动员组（用于计算Z-Score基准）",
            athletes,
            default=[athlete_name],
            help="选择的运动员将作为基准组，用于计算Z-Score的均值和标准差",
            key="radar_athletes"
        )

        # 选择雷达图指标
        radar_indicators = st.multiselect(
            "选择雷达图指标",
            RADAR_FIELDS,
            default=RADAR_FIELDS,
            help="选择要在雷达图中显示的指标（建议4-10个）"
        )

        # 选择逆指标（值越低越好的指标）
        st.markdown("**逆指标设置**（值越低越好的指标）")
        lower_better = st.multiselect(
            "选择逆指标",
            radar_indicators,
            default=[ind for ind in LOWER_IS_BETTER if ind in radar_indicators],
            help="这些指标在雷达图中会取反（如肌酸激酶、血尿素等）"
        )

        if st.button("🚀 生成雷达图", type="primary", use_container_width=True, key="radar_btn"):
            if not radar_athletes:
                st.warning("⚠️ 请至少选择一个对比运动员")
            elif not radar_indicators:
                st.warning("⚠️ 请至少选择一个指标")
            elif len(radar_indicators) < 3:
                st.warning("⚠️ 请至少选择3个指标，雷达图效果更好")
            else:
                with st.spinner("正在生成雷达图..."):
                    # 获取对比运动员组的最近4次数据（用于计算baseline）
                    baseline_data_list = []
                    for comp_athlete in radar_athletes:
                        comp_athlete_df = gender_df[gender_df[name_col] == comp_athlete].sort_values('Date')
                        if not comp_athlete_df.empty:
                            # 获取该运动员的最近4次数据
                            last_4 = comp_athlete_df.tail(4)
                            baseline_data_list.append(last_4)

                    if baseline_data_list:
                        baseline_df = pd.concat(baseline_data_list, ignore_index=True)

                        # 生成雷达图：只画主运动员的近4次，但用baseline_df计算Z值
                        fig = plot_radar_chart_with_baseline(
                            athlete_df, radar_indicators, lower_better,
                            ref_ranges, athlete_name, baseline_df, gender
                        )

                        if fig:
                            st.pyplot(fig)
                            plt.close()
                            st.success("✅ 雷达图生成完成！")

                            # 添加说明
                            st.markdown("---")
                            st.markdown("### 📖 雷达图说明")
                            st.markdown(f"""
                            - **显示内容**：{athlete_name}的最近4次测试
                            - **对比基准**：使用{len(radar_athletes)}个运动员的最近4次数据计算均值和标准差
                            - **Z-Score含义**：
                              - **0**：等于基准组平均水平
                              - **正值**：高于基准组平均水平
                              - **负值**：低于基准组平均水平
                            - **逆指标**：标记"(逆)"的指标已取反显示（值越低越好）
                            - **线条样式**：
                              - 蓝色虚点线：第1次测试
                              - 橙色点划线：第2次测试
                              - 绿色虚线：第3次测试
                              - 红色实线+填充：第4次测试（最新）
                            - **解读要点**：图形越向外，表现越好；图形越规则，机能越均衡
                            """)
                        else:
                            st.info("ℹ️ 数据不足，无法生成雷达图")
                    else:
                        st.warning("⚠️ 对比运动员组没有足够的数据")

    # --- Tab 4: 数据表 ---
    with tab4:
        st.subheader("完整数据表")
        st.write(athlete_df)

        try:
            csv = athlete_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载CSV数据",
                data=csv,
                file_name=f"{athlete_name}_数据.csv",
                mime="text/csv"
            )
        except:
            st.warning("CSV下载功能暂时不可用")

if __name__ == "__main__":
    main()
