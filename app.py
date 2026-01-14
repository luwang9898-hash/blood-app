"""
运动员血液指标分析系统 - 增强版 (已修复数值格式化Bug)
包含：表格图、趋势图（多运动员对比）、雷达图
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from datetime import datetime
from scipy.interpolate import make_interp_spline
import matplotlib.font_manager as fm
import os
import traceback

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
try:
    from config import (
        MALE_REF_RANGES, FEMALE_REF_RANGES,
        COLUMN_NAME_MAPPING
    )
except ImportError:
    MALE_REF_RANGES = {}
    FEMALE_REF_RANGES = {}
    COLUMN_NAME_MAPPING = {}

# 趋势图默认指标
TREND_INDICATORS = ['睾酮', '皮质醇', '肌酸激酶', '血尿素', '血红蛋白', '铁蛋白', '白细胞', '网织红细胞百分比']

# ============================================================================
# 基础功能函数
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
    if pd.isna(value_str) or str(value_str).strip() == '-' or str(value_str).strip() == '':
        return None, None
    value_str = str(value_str).strip()
    if value_str.startswith('<'):
        val = value_str.replace('<', '').strip()
        try: return None, float(val)
        except: return None, None
    if value_str.startswith('>'):
        val = value_str.replace('>', '').strip()
        try: return float(val), None
        except: return None, None
    if '-' in value_str:
        parts = value_str.split('-')
        if len(parts) == 2:
            try: return float(parts[0].strip()), float(parts[1].strip())
            except: return None, None
    try:
        val = float(value_str)
        return val, val
    except:
        return None, None


def load_reference_ranges_from_excel(file):
    try:
        df = pd.read_excel(file, sheet_name='参考范围')
        male_ranges = {}
        female_ranges = {}
        common_ranges = {}
        for idx, row in df.iterrows():
            indicator = str(row['指标名称']).strip()
            gender = str(row['性别']).strip()
            severe_low_val = row['严重偏低 (<)']
            low_range = row['偏低 (范围)']
            normal_range = row['参考范围 (正常)']
            high_range = row['偏高 (范围)']
            severe_high_val = row['严重偏高 (>)']
            normal_low, normal_high = parse_range_value(normal_range)
            severe_low_lower, severe_low_upper = parse_range_value(severe_low_val)
            low_lower, low_upper = parse_range_value(low_range)
            high_lower, high_upper = parse_range_value(high_range)
            severe_high_lower, severe_high_upper = parse_range_value(severe_high_val)
            range_dict = {
                'severe_low_1': severe_low_lower if severe_low_lower is not None else severe_low_upper,
                'low_1': low_lower if low_lower is not None else None,
                'low_2': normal_low,
                'high_2': normal_high,
                'high_1': high_upper if high_upper is not None else None,
                'severe_high_1': severe_high_upper if severe_high_upper is not None else severe_high_lower,
            }
            if gender == '男': male_ranges[indicator] = range_dict
            elif gender == '女': female_ranges[indicator] = range_dict
            elif gender == '通用': common_ranges[indicator] = range_dict
        for indicator, range_dict in common_ranges.items():
            if indicator not in male_ranges: male_ranges[indicator] = range_dict
            if indicator not in female_ranges: female_ranges[indicator] = range_dict
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
CATEGORY_NAMES = {
    '1_调控与指挥中心': ('调控与指挥中心（神经-内分泌系统）', 'Control and Command Center (Neuroendocrine System)'),
    '2_执行与代谢系统': ('执行与代谢系统（肌肉与能量状态）', 'Execution and Metabolic System (Muscle and Energy Status)'),
    '3_循环与运载系统': ('循环与运载系统（血液运载能力）', 'Circulation and Transport System (Blood Transport Capacity)'),
    '4_后勤保障与维护': ('后勤保障与维护（免疫与内环境）', 'Logistics Support and Maintenance (Immunity and Internal Environment)'),
    '5_甲状腺功能': ('甲状腺功能', 'Thyroid Function'),
    '6_肝脏功能': ('肝脏功能', 'Liver Function'),
    '7_血脂': ('血脂', 'Blood Lipids'),
}

THEME_CONFIG = {
    '1_调控与指挥中心': {
        '合成代谢\nAnabolism': {'睾酮': ('睾酮', 'Testosterone'), '游离睾酮': ('游离睾酮', 'Free Testosterone')},
        '分解代谢\nCatabolism': {'皮质醇': ('皮质醇', 'Cortisol')},
        '状态平衡\nStatus Balance': {'睾酮/皮质醇比值': ('睾酮/皮质醇比值', 'T/C Ratio')}
    },
    '2_执行与代谢系统': {
        '结构完整性（硬件）\nStructural Integrity (Hardware)': {'肌酸激酶': ('肌酸激酶', 'Creatine Kinase')},
        '能量储备与代谢（软件/燃料）\nEnergy Reserves and Metabolism (Software/Fuel)': {'血糖': ('血糖', 'Blood Glucose'), '血尿素': ('血尿素', 'Blood Urea'), '尿酸': ('尿酸', 'Uric Acid')}
    },
    '3_循环与运载系统': {
        '输送载体（红细胞）\nTransport Carrier (Red Blood Cells)': {'血红蛋白': ('血红蛋白', 'Hemoglobin'), '红细胞': ('红细胞', 'RBC Count'), '红细胞压积': ('红细胞压积', 'Hematocrit'), '网织红细胞百分比': ('网织红细胞百分比', 'Reticulocyte %'), '平均红细胞容积': ('平均红细胞容积', 'MCV')},
        '生化原料（造血储备）\nBiochemical Raw Materials (Hematopoietic Reserves)': {'铁蛋白': ('铁蛋白', 'Ferritin'), '维生素B12': ('维生素B12', 'Vitamin B12'), '维生素B6': ('维生素B6', 'Vitamin B6'), '叶酸': ('叶酸', 'Folic Acid')}
    },
    '4_后勤保障与维护': {
        '免疫防御（炎性监控）\nImmune Defense (Inflammatory Monitoring)': {'白细胞': ('白细胞', 'WBC Count'), '超敏C反应蛋白': ('超敏C反应蛋白', 'hs-CRP'), '触珠蛋白': ('触珠蛋白', 'Haptoglobin')},
        '代谢辅酶（微量营养）\nMetabolic Coenzymes (Micronutrients)': {'维生素B1': ('维生素B1', 'Vitamin B1'), '维生素B2': ('维生素B2', 'Vitamin B2'), '维生素D3': ('维生素D3', 'Vitamin D3')},
        '内环境稳态（水盐平衡）\nInternal Environment Homeostasis (Water-Electrolyte Balance)': {'钾': ('钾', 'Potassium'), '钠': ('钠', 'Sodium'), '氯': ('氯', 'Chloride'), '渗透压': ('渗透压', 'Osmotic Pressure'), '血尿素/肌酐': ('血尿素/肌酐', 'BUN/Cr Ratio')}
    },
    '5_甲状腺功能': {
        '甲状腺功能\nThyroid Function': {'总甲状腺素': ('总甲状腺素', 'Total Thyroxine'), '总三碘甲状腺原氨酸': ('总三碘甲状腺原氨酸', 'Total T3'), '游离三碘甲状原氨酸': ('游离三碘甲状原氨酸', 'Free T3'), '游离甲状腺素': ('游离甲状腺素', 'Free T4'), '超敏促甲状腺素': ('超敏促甲状腺素', 'hs-TSH')}
    },
    '6_肝脏功能': {
        '肝脏功能\nLiver Function': {'丙氨酸氨基转移酶': ('丙氨酸氨基转移酶', 'ALT'), '天冬氨酸氨基转移酶': ('天冬氨酸氨基转移酶', 'AST'), '碱性磷酸酶': ('碱性磷酸酶', 'ALP'), 'γ-谷氨酰基转移酶': ('γ-谷氨酰基转移酶', 'γ-GT'), '总胆红素': ('总胆红素', 'Total Bilirubin'), '直接胆红素': ('直接胆红素', 'Direct Bilirubin'), '总蛋白': ('总蛋白', 'Total Protein'), '间接胆红素': ('间接胆红素', 'Indirect Bilirubin')}
    },
    '7_血脂': {
        '血脂\nBlood Lipids': {'甘油三酯': ('甘油三酯', 'Triglycerides'), '高密度脂蛋白': ('高密度脂蛋白', 'HDL'), '总胆固醇': ('总胆固醇', 'Total Cholesterol'), '低密度脂蛋白': ('低密度脂蛋白', 'LDL')}
    },
}

RADAR_FIELDS = ['睾酮', '皮质醇', '肌酸激酶', '血尿素', '血红蛋白', '铁蛋白', '白细胞', '网织红细胞百分比']
LOWER_IS_BETTER = ['肌酸激酶', '血尿素', '超敏C反应蛋白', '皮质醇']

COLOR_SEVERE_LOW = '#4A90E2'
COLOR_LOW = '#8BC1E9'
COLOR_NORMAL = '#E6E6E6'
COLOR_HIGH = '#E89A9D'
COLOR_SEVERE_HIGH = '#D05A5E'
COLOR_CATEGORY_HEADER = '#5C7CFA'
COLOR_CHART_BG = '#F8F9FA'
RADAR_STYLES = [{'color': '#8BC1E9', 'linewidth': 2, 'linestyle': ':'}, {'color': '#E89A9D', 'linewidth': 2, 'linestyle': '-.'}, {'color': '#5C7CFA', 'linewidth': 2.5, 'linestyle': '--'}, {'color': '#D05A5E', 'linewidth': 3, 'linestyle': '-'}]

# ============================================================================
# 数据处理核心函数
# ============================================================================
def deduplicate_columns(df):
    if df is None: return None
    new_columns = []
    seen = {}
    for col in df.columns:
        col_str = str(col).strip()
        if col_str in seen:
            seen[col_str] += 1
            new_col = f"{col_str}.{seen[col_str]}"
        else:
            seen[col_str] = 0
            new_col = col_str
        new_columns.append(new_col)
    df.columns = new_columns
    return df

def load_data_multisheet(file_path_or_buffer):
    try:
        st.info("📊 开始读取多个sheet的数据...")
        st.write("正在读取：月周测试指标...")
        df_monthly = pd.read_excel(file_path_or_buffer, sheet_name='月周测试指标', header=0, skiprows=lambda x: x in range(1, 11))
        df_monthly = deduplicate_columns(df_monthly)
        st.write(f"   ✓ 月周测试：{len(df_monthly)} 行，{len(df_monthly.columns)} 列")
        
        df_quarterly = None
        try:
            st.write("正在读取：季度测试指标...")
            df_q_raw = pd.read_excel(file_path_or_buffer, sheet_name='季度测试指标', header=[0, 1])
            df_quarterly = flatten_multiindex_columns(df_q_raw, '季度测试')
            df_quarterly = deduplicate_columns(df_quarterly)
            st.write(f"   ✓ 季度测试：{len(df_quarterly)} 行，{len(df_quarterly.columns)} 列")
        except Exception as e:
            st.warning(f"   ⚠ 季度测试指标读取失败：{e}")
        
        df_yearly = None
        try:
            st.write("正在读取：年度测试指标...")
            df_y_raw = pd.read_excel(file_path_or_buffer, sheet_name='年度测试指标', header=[0, 1])
            df_yearly = flatten_multiindex_columns(df_y_raw, '年度测试')
            df_yearly = deduplicate_columns(df_yearly)
            st.write(f"   ✓ 年度测试：{len(df_yearly)} 行，{len(df_yearly.columns)} 列")
        except Exception as e:
            st.warning(f"   ⚠ 年度测试指标读取失败：{e}")
        
        df_other = None
        try:
            st.write("正在读取：其他指标...")
            df_o_raw = pd.read_excel(file_path_or_buffer, sheet_name='其他', header=[0, 1])
            df_other = flatten_multiindex_columns(df_o_raw, '其他')
            df_other = deduplicate_columns(df_other)
            st.write(f"   ✓ 其他指标：{len(df_other)} 行，{len(df_other.columns)} 列")
        except Exception as e:
            st.warning(f"   ⚠ 其他指标读取失败：{e}")
        
        st.write("\n正在合并数据...")
        df_merged = merge_all_sheets(df_monthly, df_quarterly, df_yearly, df_other)
        df_merged = deduplicate_columns(df_merged)
        st.success(f"✅ 数据合并完成：{len(df_merged)} 行，{len(df_merged.columns)} 列")
        return df_merged
    except Exception as e:
        st.error(f"❌ 数据加载失败：{e}")
        st.error(traceback.format_exc())
        return None

def flatten_multiindex_columns(df, sheet_name):
    new_columns = []
    for col in df.columns:
        if isinstance(col, tuple):
            level0, level1 = col[0], col[1]
            if not (pd.isna(level0) or str(level0).startswith('Unnamed')): new_columns.append(str(level0))
            elif not (pd.isna(level1) or str(level1).startswith('Unnamed')): new_columns.append(str(level1))
            else: new_columns.append(f'Unnamed_{len(new_columns)}')
        else: new_columns.append(str(col))
    df.columns = new_columns
    return df

def merge_all_sheets(df_monthly, df_quarterly, df_yearly, df_other):
    df_result = df_monthly.copy()
    name_col_monthly = None
    for col_name in ['姓名', 'Name', 'Name_final']:
        if col_name in df_result.columns:
            name_col_monthly = col_name
            break
    date_col_monthly = None
    for col_name in ['测试日期', 'Date', 'Date_auto']:
        if col_name in df_result.columns:
            date_col_monthly = col_name
            break
    if not name_col_monthly or not date_col_monthly:
        st.warning("⚠ 无法找到姓名或日期列，仅使用月周测试数据")
        return df_result
    
    df_result['_merge_key'] = df_result[name_col_monthly].astype(str).fillna('') + '_' + df_result[date_col_monthly].astype(str).fillna('')
    
    if df_quarterly is not None: df_result = merge_sheet_data(df_result, df_quarterly, name_col_monthly, date_col_monthly, '季度测试')
    if df_yearly is not None: df_result = merge_sheet_data(df_result, df_yearly, name_col_monthly, date_col_monthly, '年度测试')
    if df_other is not None: df_result = merge_sheet_data(df_result, df_other, name_col_monthly, date_col_monthly, '其他')
    
    if '_merge_key' in df_result.columns: df_result = df_result.drop('_merge_key', axis=1)
    return df_result

def merge_sheet_data(df_main, df_add, name_col, date_col, sheet_name):
    try:
        df_add = deduplicate_columns(df_add)
        name_col_add = None
        if name_col in df_add.columns: name_col_add = name_col
        else:
            for col_name in ['姓名', 'Name', 'Name_final']:
                if col_name in df_add.columns:
                    name_col_add = col_name
                    break
        date_col_add = None
        if date_col in df_add.columns: date_col_add = date_col
        else:
            for col_name in ['测试日期', 'Date', 'Date_auto']:
                if col_name in df_add.columns:
                    date_col_add = col_name
                    break
        if not name_col_add or not date_col_add:
            st.warning(f"   ⚠ {sheet_name}：无法找到姓名或日期列，跳过合并")
            return df_main
        
        s_name = df_add[name_col_add].astype(str).fillna('')
        s_date = df_add[date_col_add].astype(str).fillna('')
        df_add['_merge_key'] = s_name + '_' + s_date
        
        exclude_cols = ['项目', '编号', '姓名', '性别', '出生年月日', '身高', '体重', '测试日期', 'Name', 'Name_final', 'Date', 'Date_auto', '_merge_key', '教练', '训练地点', '测试单位', '测试阶段', '重点运动员', '专项', name_col_add, date_col_add]
        indicator_cols = []
        for col in df_add.columns:
            if col in exclude_cols: continue
            if str(col).startswith('Unnamed'): continue
            if col == '_merge_key': continue
            indicator_cols.append(col)
        
        if not indicator_cols: return df_main
        
        df_add_indicators = df_add[['_merge_key'] + indicator_cols].drop_duplicates(subset=['_merge_key'])
        df_merged = df_main.merge(df_add_indicators, on='_merge_key', how='left', suffixes=('', f'_{sheet_name}'))
        st.write(f"   ✓ {sheet_name}合并：添加了 {len(indicator_cols)} 个指标")
        return df_merged
    except Exception as e:
        st.warning(f"   ⚠ {sheet_name}合并失败：{e}")
        return df_main

def get_indicator_status(indicator, value, ref_ranges):
    if indicator not in ref_ranges or pd.isna(value): return '数据缺失', '#F0F8FF', 'N/A'
    try:
        if isinstance(value, str):
            value = value.strip()
            if value == '' or value == '-' or value.lower() == 'nan': return '数据缺失', '#F0F8FF', 'N/A'
            value = float(value)
        elif not isinstance(value, (int, float)): value = float(value)
    except (ValueError, TypeError): return '数据缺失', '#F0F8FF', 'N/A'

    ranges = ref_ranges[indicator]
    try:
        low_1 = ranges.get('low_1')
        low_2 = ranges.get('low_2')
        high_2 = ranges.get('high_2')
        high_1 = ranges.get('high_1')
        for v in [low_1, low_2, high_2, high_1]:
            if v is not None and not isinstance(v, (int, float)):
                try: v = float(v) 
                except: pass
    except (ValueError, TypeError): return '数据缺失', '#F0F8FF', 'N/A'

    high_is_better_indicators = ['铁蛋白', '血红蛋白', '睾酮', '游离睾酮']
    try:
        if pd.notna(low_1) and value < low_1: return '严重偏低', COLOR_SEVERE_LOW, 'severe_low'
        elif pd.notna(low_2) and value < low_2: return '偏低', COLOR_LOW, 'low'
        elif pd.notna(high_1) and value > high_1:
            if indicator in high_is_better_indicators: return '优秀', COLOR_SEVERE_HIGH, 'excellent'
            else: return '严重偏高', COLOR_SEVERE_HIGH, 'severe_high'
        elif pd.notna(high_2) and value > high_2:
            if indicator in high_is_better_indicators: return '良好', COLOR_HIGH, 'good'
            else: return '偏高', COLOR_HIGH, 'high'
        else: return '正常', COLOR_NORMAL, 'normal'
    except (TypeError, ValueError): return '数据缺失', '#F0F8FF', 'N/A'

def clean_data_final(df):
    if df is None: return None
    st.info("🧹 开始清洗数据...")
    df = df.dropna(how='all').reset_index(drop=True)
    if '姓名' in df.columns:
        name_cols = [col for col in df.columns if col.startswith('Name')]
        if not name_cols: df['Name'] = df['姓名']
        else: df['Name_final'] = df['姓名']
    possible_date_cols = ['测试日期', '日期', '开始日期']
    date_col_found = False
    for col in possible_date_cols:
        if col in df.columns:
            try:
                date_cols = [c for c in df.columns if c.startswith('Date')]
                if not date_cols:
                    if pd.api.types.is_datetime64_any_dtype(df[col]): df['Date'] = df[col]
                    else: df['Date'] = pd.to_datetime(df[col], errors='coerce')
                    df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
                    date_col_found = True
                else: date_col_found = True
                break
            except Exception as e: continue
    if not date_col_found:
        df['Date_auto'] = pd.date_range(start='2024-01-01', periods=len(df), freq='D')
        df['DateStr'] = df['Date_auto'].dt.strftime('%Y-%m-%d')
    df = df.dropna(how='all').reset_index(drop=True)
    st.success(f"✅ 清洗完成：保留 {len(df)} 行有效数据")
    return df

INDICATOR_ALIASES = {
    '平均红细胞血红蛋白浓度': ['平均红细胞血红浓度', 'MCHC', '平均血红蛋白浓度'],
    '平均红细胞血红蛋白': ['平均红细胞血红蛋白量', 'MCH'],
    '平均红细胞体积': ['平均红细胞容积', 'MCV'],
    '平均红细胞容积': ['平均红细胞体积', 'MCV'],
    '平均血红蛋白浓度': ['平均红细胞血红蛋白浓度', 'MCHC'],
    '网织红细胞百分比': ['网织红细胞', 'retic', 'Retic'],
    '超敏C反应蛋白': ['C反应蛋白', 'CRP', 'hsCRP', 'hs-CRP'],
    '维生素B1': ['VB1', 'VitB1'],
    '维生素B2': ['VB2', 'VitB2'],
    '维生素B6': ['VB6', 'VitB6', 'VitB6(PA)', 'vitB6（PLP）'],
    '维生素B12': ['VB12', 'VitB12'],
    '叶酸': ['FOL', '维生素B9'],
    '维生素D3': ['VD3', 'VD3(25-OH)', 'VD-(25-OH)'],
    '钾': ['K'],
    '钠': ['Na'],
    '氯': ['Cl'],
    '钙': ['Ca'],
    '镁': ['Mg'],
    '总甲状腺素': ['T4', 'TT4'],
    '总三碘甲状腺原氨酸': ['T3', 'TT3'],
    '游离三碘甲状原氨酸': ['FT3', '游离T3'],
    '游离甲状腺素': ['FT4', '游离T4'],
    '超敏促甲状腺素': ['TSH', 'hs-TSH', '促甲状腺激素'],
    '丙氨酸氨基转移酶': ['ALT', '谷丙转氨酶', '丙氨酸基转移酶'],
    '天冬氨酸氨基转移酶': ['AST', '谷草转氨酶'],
    '碱性磷酸酶': ['ALP'],
    'γ-谷氨酰基转移酶': ['GGT', 'γ-GT', 'γ-谷氨酰转移酶'],
    '总胆红素': ['TBIL', 'TB'],
    '直接胆红素': ['DBIL', 'DB'],
    '间接胆红素': ['IBIL', 'IB'],
    '总蛋白': ['TP'],
    '白蛋白': ['ALB', 'Alb'],
    '甘油三酯': ['TG', 'TAG'],
    '高密度脂蛋白': ['HDL', 'HDL-C'],
    '总胆固醇': ['TC', 'CHOL'],
    '低密度脂蛋白': ['LDL', 'LDL-C'],
}

def find_indicator_column(df, indicator):
    if indicator in df.columns: return indicator
    if indicator in INDICATOR_ALIASES:
        for alias in INDICATOR_ALIASES[indicator]:
            if alias in df.columns: return alias
            possible_cols = [col for col in df.columns if str(col).startswith(alias)]
            if possible_cols: return possible_cols[0]
    for main_name, aliases in INDICATOR_ALIASES.items():
        if indicator in aliases:
            if main_name in df.columns: return main_name
            possible_cols = [col for col in df.columns if str(col).startswith(main_name)]
            if possible_cols: return possible_cols[0]
            for alias in aliases:
                if alias in df.columns: return alias
                possible_cols = [col for col in df.columns if str(col).startswith(alias)]
                if possible_cols: return possible_cols[0]
    possible_cols = [col for col in df.columns if str(col).startswith(indicator)]
    if possible_cols: return possible_cols[0]
    indicator_no_space = indicator.replace(' ', '').replace('\u3000', '')
    for col in df.columns:
        col_no_space = str(col).replace(' ', '').replace('\u3000', '')
        if col_no_space == indicator_no_space: return col
        if col_no_space.startswith(indicator_no_space): return col
    import re
    indicator_clean = re.sub(r'[（(].*?[）)]', '', indicator).strip()
    for col in df.columns:
        col_str = str(col).split('#')[0]
        col_clean = re.sub(r'[（(].*?[）)]', '', col_str).strip()
        if indicator_clean == col_clean: return col
        if indicator_clean in col_clean or col_clean in indicator_clean: return col
    for col in df.columns:
        col_str = str(col).split('#')[0].strip()
        col_clean = re.sub(r'[（(].*?[）)]', '', col_str).strip()
        indicator_clean_v2 = re.sub(r'[（(].*?[）)]', '', indicator).strip()
        if abs(len(col_clean) - len(indicator_clean_v2)) <= 3:
            common_chars = sum(1 for c in indicator_clean_v2 if c in col_clean)
            similarity = common_chars / max(len(indicator_clean_v2), len(col_clean))
            if similarity >= 0.8: return col
    return None

def plot_theme_table(athlete_df, theme_name, categories, ref_ranges, gender):
    """生成主题表格图 (修复数值格式化问题)"""
    if athlete_df.empty: return None, []
    latest_row = athlete_df.iloc[-1]
    latest_date = latest_row.get('DateStr', '未知')
    athlete_name = latest_row.get('Name', latest_row.get('Name_final', '未知'))
    cell_text = []
    cell_colors = []
    missing_indicators = []
    status_translation = {
        '严重偏低': ('严重偏低', 'Severely Low'), '偏低': ('偏低', 'Low'),
        '正常': ('正常', 'Normal'), '良好': ('良好', 'Good'),
        '偏高': ('偏高', 'High'), '优秀': ('优秀', 'Excellent'),
        '严重偏高': ('严重偏高', 'Severely High'),
        '-': ('—', '—'), 'N/A': ('—', '—'), '未找到': ('—', '—'),
    }

    for category_title, indicators in categories.items():
        cell_text.append([category_title, '', '', ''])
        cell_colors.append([COLOR_CATEGORY_HEADER, COLOR_CATEGORY_HEADER, COLOR_CATEGORY_HEADER, COLOR_CATEGORY_HEADER])
        for col_key, name_tuple in indicators.items():
            cn_name, en_name = name_tuple
            # 睾酮/皮质醇比值计算
            if col_key == '睾酮/皮质醇比值':
                testosterone_col = find_indicator_column(athlete_df, '睾酮')
                cortisol_col = find_indicator_column(athlete_df, '皮质醇')
                val_str = "—"
                status = "-"
                bg_color = '#F8F8F8'
                range_str = "—"
                if testosterone_col and cortisol_col and testosterone_col in latest_row.index and cortisol_col in latest_row.index:
                    t_val = latest_row[testosterone_col]
                    c_val = latest_row[cortisol_col]
                    if pd.notna(t_val) and pd.notna(c_val) and c_val != 0:
                        val = t_val / c_val
                        val_str = f"{val:.2f}"
                        status, bg_color, _ = get_indicator_status(col_key, val, ref_ranges)
                    else: missing_indicators.append((col_key, f"{cn_name}/{en_name}"))
                else: missing_indicators.append((col_key, f"{cn_name}/{en_name}"))
                if col_key in ref_ranges:
                    ranges = ref_ranges[col_key]
                    low_2 = ranges.get('low_2')
                    high_2 = ranges.get('high_2')
                    if pd.notna(low_2) and pd.notna(high_2): range_str = f"{low_2:.1f}-{high_2:.1f}"
                    elif pd.notna(low_2): range_str = f"≥{low_2:.1f}"
                    elif pd.notna(high_2): range_str = f"≤{high_2:.1f}"
            else:
                actual_col = find_indicator_column(athlete_df, col_key)
                range_str = "—"
                if col_key in ref_ranges:
                    ranges = ref_ranges[col_key]
                    low_2 = ranges.get('low_2')
                    high_2 = ranges.get('high_2')
                    if pd.notna(low_2) and pd.notna(high_2): range_str = f"{low_2:.1f}-{high_2:.1f}"
                    elif pd.notna(low_2): range_str = f"≥{low_2:.1f}"
                    elif pd.notna(high_2): range_str = f"≤{high_2:.1f}"

                if actual_col and actual_col in latest_row.index:
                    raw_val = latest_row[actual_col]
                    
                    # 尝试转为float用于数值判断和格式化 (Fix TypeError)
                    val = None
                    try: val = float(raw_val)
                    except (ValueError, TypeError): val = None

                    status, bg_color, _ = get_indicator_status(col_key, raw_val, ref_ranges)
                    
                    if val is not None and pd.notna(val):
                        if abs(val) >= 1000: val_str = f"{val:.0f}"
                        elif abs(val) >= 100: val_str = f"{val:.1f}"
                        else: val_str = f"{val:.2f}"
                    else:
                        # 非数值数据直接显示字符串
                        val_str = str(raw_val) if pd.notna(raw_val) and str(raw_val).lower() != 'nan' else "—"
                else:
                    val_str = "—"
                    status = "-"
                    bg_color = '#F8F8F8'
                    missing_indicators.append((col_key, f"{cn_name}/{en_name}"))

            indicator_text = f"{cn_name}\n{en_name}"
            if status == "-": status_text = "—"
            else:
                status_cn, status_en = status_translation.get(status, (status, status))
                status_text = f"{status_cn}\n{status_en}"
            
            cell_text.append([indicator_text, val_str, range_str, status_text])
            cell_colors.append(['#F8F8F8', bg_color, '#F8F8F8', bg_color])

    fig_height = len(cell_text) * 0.9 + 1.5
    fig, ax = plt.subplots(figsize=(10, fig_height), dpi=150)
    ax.axis('off')
    col_widths = [0.45, 0.18, 0.18, 0.19]
    table = ax.table(
        cellText=cell_text, colLabels=['检测指标\nIndicator', '结果\nResult', '参考范围\nReference', '评价\nEvaluation'],
        cellColours=cell_colors, loc='center', cellLoc='center', colColours=['#333333'] * 4, colWidths=col_widths
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.8)
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=9)
            cell.set_edgecolor('white')
        elif cell.get_facecolor() == COLOR_CATEGORY_HEADER:
            cell.set_text_props(weight='bold', color='white', ha='center', fontsize=11)
            cell.set_edgecolor('white')
        else:
            cell.set_edgecolor('#DDDDDD')
            if r > 0 and c == 0: cell.set_text_props(ha='left', fontsize=9)
            elif r > 0 and c in [1, 2]: cell.set_text_props(fontsize=10)
            elif r > 0 and c == 3: cell.set_text_props(fontsize=8.5)

    if theme_name in CATEGORY_NAMES:
        cn_title, en_title = CATEGORY_NAMES[theme_name]
        title_text = f"{athlete_name} ({gender}) - {cn_title}\n{en_title} ({latest_date})"
    else:
        theme_display = theme_name.split('_')[-1]
        title_text = f"{athlete_name} ({gender}) - {theme_display} ({latest_date})"
    plt.title(title_text, y=0.99, fontsize=13, fontweight='bold')
    plt.tight_layout()
    return fig, missing_indicators

def plot_trend_chart_multi(df, indicator, ref_ranges, selected_athletes, date_range, gender):
    actual_col = find_indicator_column(df, indicator)
    if not actual_col: return None
    if date_range and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        df_filtered = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()
    else: df_filtered = df.copy()
    if df_filtered.empty: return None
    name_col = 'Name' if 'Name' in df_filtered.columns else 'Name_final'
    df_with_indicator = df_filtered[df_filtered[actual_col].notna()].copy()
    if df_with_indicator.empty: return None
    dates_with_data = set()
    for athlete in selected_athletes:
        athlete_data = df_with_indicator[df_with_indicator[name_col] == athlete]
        if not athlete_data.empty: dates_with_data.update(athlete_data['DateStr'].unique())
    if not dates_with_data: return None
    all_dates = sorted(list(dates_with_data))
    date_to_index = {date: i for i, date in enumerate(all_dates)}
    fig, ax = plt.subplots(figsize=(12, 7), dpi=150)
    ax.set_facecolor(COLOR_CHART_BG)
    harmonious_colors = ['#4A90E2', '#D05A5E', '#8BC1E9', '#E89A9D', '#5C7CFA', '#9B59B6', '#1ABC9C', '#E67E22']
    if len(selected_athletes) > len(harmonious_colors): colors = plt.cm.tab10(np.linspace(0, 1, len(selected_athletes)))
    else: colors = [harmonious_colors[i % len(harmonious_colors)] for i in range(len(selected_athletes))]
    all_y_values = []
    for idx, (athlete, color) in enumerate(zip(selected_athletes, colors)):
        athlete_data = df_with_indicator[df_with_indicator[name_col] == athlete].copy()
        if athlete_data.empty: continue
        athlete_data = athlete_data.sort_values('Date')
        valid_data = athlete_data.dropna(subset=[actual_col])
        if len(valid_data) == 0: continue
        x_data = np.array([date_to_index[d] for d in valid_data['DateStr']])
        y_data = valid_data[actual_col].values
        all_y_values.extend(y_data)
        if len(valid_data) > 1:
            try:
                x_smooth = np.linspace(x_data.min(), x_data.max(), 200)
                k = 2 if len(x_data) >= 3 else 1
                spl = make_interp_spline(x_data, y_data, k=k)
                y_smooth = spl(x_smooth)
                ax.plot(x_smooth, y_smooth, color=color, linewidth=2.5, label=athlete, alpha=0.8)
            except: ax.plot(x_data, y_data, color=color, linewidth=2.5, label=athlete, alpha=0.8)
        else: ax.plot(x_data, y_data, color=color, linewidth=2.5, label=athlete, linestyle='--', alpha=0.6)
        ax.plot(x_data, y_data, marker='o', markersize=8, markerfacecolor='white', markeredgecolor=color, markeredgewidth=2, linestyle='None')
        if idx == 0:
            for x, y in zip(x_data, y_data):
                ax.text(x, y, f'{y:.1f}', fontsize=9, ha='center', va='bottom', color=color, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.8, linewidth=1))
    if indicator in ref_ranges and len(all_y_values) > 0:
        ranges = ref_ranges[indicator]
        low_2 = ranges.get('low_2')
        high_2 = ranges.get('high_2')
        data_min = min(all_y_values)
        data_max = max(all_y_values)
        y_range = data_max - data_min
        if pd.notna(low_2) and pd.notna(high_2):
            ax.axhspan(low_2, high_2, color='#4A90E2', alpha=0.15, zorder=0, label='理想范围')
            ax.axhline(low_2, color=COLOR_SEVERE_LOW, linestyle=':', linewidth=1, alpha=0.7)
            ax.axhline(high_2, color=COLOR_SEVERE_HIGH, linestyle=':', linewidth=1, alpha=0.7)
        elif pd.notna(high_2) and not pd.notna(low_2):
            y_min = min(0, data_min - y_range * 0.1)
            ax.axhspan(y_min, high_2, color='#4A90E2', alpha=0.15, zorder=0, label=f'理想范围 (< {high_2})')
            ax.axhline(high_2, color=COLOR_SEVERE_HIGH, linestyle=':', linewidth=1.5, alpha=0.7)
        elif pd.notna(low_2) and not pd.notna(high_2):
            y_max = data_max + y_range * 0.1
            ax.axhspan(low_2, y_max, color='#4A90E2', alpha=0.15, zorder=0, label=f'理想范围 (> {low_2})')
            ax.axhline(low_2, color=COLOR_SEVERE_LOW, linestyle=':', linewidth=1.5, alpha=0.7)
    ax.set_xticks(np.arange(len(all_dates)))
    ax.set_xticklabels(all_dates, rotation=45, ha='right')
    plt.title(f"{indicator} 趋势对比 ({gender})", fontsize=14, fontweight='bold')
    plt.xlabel('测试日期', fontsize=12)
    plt.ylabel(f'{indicator}', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.legend(loc='upper left', bbox_to_anchor=(1.01, 1), frameon=True)
    plt.tight_layout()
    return fig

def plot_radar_chart_with_baseline(athlete_df, radar_fields, lower_is_better, ref_ranges, athlete_name, baseline_athletes_df, gender):
    if athlete_df.empty: return None
    last_4_dates = athlete_df['DateStr'].unique()[-4:]
    if len(last_4_dates) == 0: return None
    baseline_stats = {}
    for field in radar_fields:
        actual_col = find_indicator_column(baseline_athletes_df, field)
        if actual_col:
            col_data = baseline_athletes_df[actual_col].dropna()
            if len(col_data) >= 2: baseline_stats[field] = {'mu': col_data.mean(), 'sigma': col_data.std()}
            else: baseline_stats[field] = {'mu': col_data.mean() if len(col_data) > 0 else 0, 'sigma': 1}
        else: baseline_stats[field] = {'mu': 0, 'sigma': 1}
    athlete_z_scores = []
    for date in last_4_dates:
        date_row = athlete_df[athlete_df['DateStr'] == date]
        if date_row.empty: continue
        for field in radar_fields:
            actual_col = find_indicator_column(date_row, field)
            stats = baseline_stats.get(field)
            if not stats or stats['sigma'] == 0: z = 0
            else:
                if actual_col and actual_col in date_row.columns:
                    val = date_row[actual_col].values[0]
                    z = (val - stats['mu']) / stats['sigma'] if pd.notna(val) else 0
                else: z = 0
            if field in lower_is_better: z = -z
            athlete_z_scores.append(z)
    max_abs_z = max([abs(z) for z in athlete_z_scores]) if athlete_z_scores else 0
    limit = max(2.5, np.ceil(max_abs_z * 2) / 2)
    labels = [f + ('\n(逆)' if f in lower_is_better else '') for f in radar_fields]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True), dpi=150)
    plt.ylim(-limit - 1.0, limit)
    ax.plot(angles, [0] * len(angles), color='red', linewidth=2, linestyle='--', zorder=0.5)
    normal_range_lower = []
    normal_range_upper = []
    for field in radar_fields:
        if field in ref_ranges:
            ranges = ref_ranges[field]
            low_2 = ranges.get('low_2')
            high_2 = ranges.get('high_2')
            stats = baseline_stats.get(field)
            if pd.notna(low_2) and pd.notna(high_2) and stats and stats['sigma'] != 0:
                z_lower = (low_2 - stats['mu']) / stats['sigma']
                z_upper = (high_2 - stats['mu']) / stats['sigma']
                if field in lower_is_better: z_lower, z_upper = -z_upper, -z_lower
                normal_range_lower.append(z_lower)
                normal_range_upper.append(z_upper)
            else: normal_range_lower.append(-1); normal_range_upper.append(1)
        else: normal_range_lower.append(-1); normal_range_upper.append(1)
    normal_range_lower.append(normal_range_lower[0])
    normal_range_upper.append(normal_range_upper[0])
    ax.fill_between(angles, normal_range_lower, normal_range_upper, color='#90EE90', alpha=0.2, zorder=1, label='理想范围')
    ax.plot(angles, normal_range_lower, color='#32CD32', linewidth=1.5, linestyle=':', alpha=0.6, zorder=1)
    ax.plot(angles, normal_range_upper, color='#32CD32', linewidth=1.5, linestyle=':', alpha=0.6, zorder=1)
    styles = RADAR_STYLES[-len(last_4_dates):]
    for i, date in enumerate(last_4_dates):
        date_row = athlete_df[athlete_df['DateStr'] == date]
        if date_row.empty: continue
        values = []
        for field in radar_fields:
            actual_col = find_indicator_column(date_row, field)
            stats = baseline_stats.get(field)
            if not stats or stats['sigma'] == 0: z = 0
            else:
                if actual_col and actual_col in date_row.columns:
                    val = date_row[actual_col].values[0]
                    z = (val - stats['mu']) / stats['sigma'] if pd.notna(val) else 0
                else: z = 0
            if field in lower_is_better: z = -z
            values.append(z)
        values.append(values[0])
        style = styles[i]
        ax.plot(angles, values, color=style['color'], linewidth=style['linewidth'], linestyle=style['linestyle'], label=date, zorder=2)
        if i == len(last_4_dates) - 1: ax.fill(angles, values, color=style['color'], alpha=0.15, zorder=3)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=11)
    step = 1 if limit <= 3 else 2
    z_ticks = np.arange(-int(limit), int(limit) + 1, step)
    ax.set_yticks(z_ticks)
    ax.set_yticklabels([f'{i:.0f}' for i in z_ticks], color='grey', size=10)
    plt.title(f"{athlete_name} ({gender}) - 机能状态 Z-Score 雷达图", fontsize=16, y=1.08, fontweight='bold')
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout()
    return fig

def main():
    st.title("🏃 运动员血液指标分析系统")
    st.markdown("**包含：表格图、多运动员趋势对比、雷达图**")
    st.markdown("---")
    st.sidebar.header("📂 数据上传")
    uploaded_file = st.sidebar.file_uploader("1️⃣ 上传血液数据Excel", type=['xlsx', 'xls'], help="请上传包含'月周测试指标'工作表的Excel文件", key="data_file")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 参考范围设置**")
    use_custom_ranges = st.sidebar.checkbox("使用自定义参考范围", value=False)
    custom_ranges_file = None
    if use_custom_ranges: custom_ranges_file = st.sidebar.file_uploader("2️⃣ 上传参考范围Excel", type=['xlsx', 'xls'], key="ranges_file")
    if uploaded_file is None: st.info("👈 请在左侧上传Excel数据文件"); st.stop()
    if use_custom_ranges and custom_ranges_file is not None:
        with st.spinner("正在加载自定义参考范围..."):
            male_ref_ranges, female_ref_ranges = load_reference_ranges_from_excel(custom_ranges_file)
            if male_ref_ranges and female_ref_ranges: st.sidebar.success(f"✅ 已加载自定义范围（男:{len(male_ref_ranges)}项，女:{len(female_ref_ranges)}项）")
            else: st.sidebar.warning("⚠️ 自定义范围加载失败，使用默认范围"); male_ref_ranges = MALE_REF_RANGES; female_ref_ranges = FEMALE_REF_RANGES
    else: male_ref_ranges = MALE_REF_RANGES; female_ref_ranges = FEMALE_REF_RANGES;
    with st.spinner("正在加载数据..."):
        df = load_data_multisheet(uploaded_file)
        if df is None: st.stop()
        df = clean_data_final(df)
        if df is None or len(df) == 0: st.error("❌ 数据清洗后为空"); st.stop()
    st.success(f"🎉 数据准备完成：共 {len(df)} 条记录")
    with st.expander("👀 查看数据"): st.write("**前20行：**"); st.write(df.head(20))
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1: gender = st.selectbox("选择性别", ["男", "女"])
    if '性别' in df.columns: gender_df = df[df['性别'] == gender].copy()
    else: st.warning("⚠️ 数据中没有'性别'列"); gender_df = df.copy()
    if len(gender_df) == 0: st.warning(f"⚠️ 没有{gender}运动员的数据"); st.stop()
    name_col = None
    for possible_name in ['Name_final', 'Name', '姓名']:
        if possible_name in gender_df.columns: name_col = possible_name; break
    if not name_col: st.error("❌ 未找到姓名列"); st.stop()
    athletes = sorted(gender_df[name_col].dropna().unique())
    ref_ranges = male_ref_ranges if gender == "男" else female_ref_ranges
    with col2: athlete_name = st.selectbox("选择运动员", athletes, help=f"共 {len(athletes)} 名{gender}运动员")
    athlete_df = gender_df[gender_df[name_col] == athlete_name].copy()
    date_col = 'Date' if 'Date' in athlete_df.columns else 'Date_auto'
    if date_col in athlete_df.columns: athlete_df = athlete_df.sort_values(date_col)
    st.info(f"📊 **{athlete_name}**（{gender}）- 共 {len(athlete_df)} 次测试")
    st.markdown("---")
    exclude_cols = ['Name', 'Name_final', '姓名', 'Date', 'Date_auto', '日期', 'DateStr', '性别', 'Gender', '编号', 'ID', 'Unnamed: 0']
    all_numeric_indicators = []
    for col in gender_df.columns:
        if col not in exclude_cols:
            try:
                if gender_df[col].dtype in ['float64', 'int64'] or pd.to_numeric(gender_df[col], errors='coerce').notna().any(): all_numeric_indicators.append(col)
            except: pass
    if not all_numeric_indicators: all_numeric_indicators = TREND_INDICATORS
    tab1, tab2, tab3, tab4 = st.tabs(["📋 主题表格", "📈 趋势对比", "🎯 雷达图", "📊 数据表"])
    with tab1:
        st.subheader("最新数据主题表格")
        if st.button("🚀 生成主题表格", type="primary", use_container_width=True):
            with st.spinner("正在生成表格..."):
                for theme_name, categories in THEME_CONFIG.items():
                    st.markdown(f"### {theme_name.split('_')[-1]}")
                    result = plot_theme_table(athlete_df, theme_name, categories, ref_ranges, gender)
                    if result:
                        fig, missing = result
                        if fig: st.pyplot(fig); plt.close()
                        else: st.info(f"ℹ️ {theme_name} 数据不足")
                    else: st.info(f"ℹ️ {theme_name} 数据不足")
                st.success("✅ 表格生成完成！")
    with tab2:
        st.subheader("多运动员趋势对比")
        compare_athletes = st.multiselect("选择对比运动员（可多选）", athletes, default=[athlete_name])
        if date_col in gender_df.columns:
            min_date = gender_df[date_col].min()
            max_date = gender_df[date_col].max()
            date_range = st.date_input("选择日期范围", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        else: date_range = None
        default_trend = [ind for ind in TREND_INDICATORS if ind in all_numeric_indicators]
        if not default_trend and all_numeric_indicators: default_trend = all_numeric_indicators[:3] if len(all_numeric_indicators) >= 3 else all_numeric_indicators
        selected_indicators = st.multiselect("选择要分析的指标", all_numeric_indicators, default=default_trend)
        if st.button("🚀 生成趋势对比图", type="primary", use_container_width=True):
            if not compare_athletes: st.warning("⚠️ 请至少选择一个运动员")
            elif not selected_indicators: st.warning("⚠️ 请至少选择一个指标")
            else:
                with st.spinner("正在生成趋势图..."):
                    for indicator in selected_indicators:
                        st.markdown(f"### {indicator}")
                        fig = plot_trend_chart_multi(gender_df, indicator, ref_ranges, compare_athletes, date_range, gender)
                        if fig: st.pyplot(fig); plt.close()
                        else: st.info(f"ℹ️ {indicator} 数据不足")
                    st.success("✅ 趋势图生成完成！")
    with tab3:
        st.subheader(f"{athlete_name}的机能状态雷达图")
        st.info("💡 **Z-Score计算说明**：使用对比运动员组的数据作为基准，计算该运动员相对于组内的表现")
        radar_athletes = st.multiselect("选择对比运动员组（用于计算Z-Score基准）", athletes, default=[athlete_name], key="radar_athletes")
        default_radar = [ind for ind in RADAR_FIELDS if ind in all_numeric_indicators]
        if not default_radar and all_numeric_indicators: default_radar = all_numeric_indicators[:8] if len(all_numeric_indicators) >= 8 else all_numeric_indicators
        radar_indicators = st.multiselect("选择雷达图指标", all_numeric_indicators, default=default_radar)
        st.markdown("**逆指标设置**（值越低越好的指标）")
        lower_better = st.multiselect("选择逆指标", radar_indicators, default=[ind for ind in LOWER_IS_BETTER if ind in radar_indicators])
        if st.button("🚀 生成雷达图", type="primary", use_container_width=True, key="radar_btn"):
            if not radar_athletes: st.warning("⚠️ 请至少选择一个对比运动员")
            elif not radar_indicators: st.warning("⚠️ 请至少选择一个指标")
            elif len(radar_indicators) < 3: st.warning("⚠️ 请至少选择3个指标，雷达图效果更好")
            else:
                with st.spinner("正在生成雷达图..."):
                    baseline_data_list = []
                    for comp_athlete in radar_athletes:
                        comp_athlete_df = gender_df[gender_df[name_col] == comp_athlete].sort_values('Date')
                        if not comp_athlete_df.empty: last_4 = comp_athlete_df.tail(4); baseline_data_list.append(last_4)
                    if baseline_data_list:
                        baseline_df = pd.concat(baseline_data_list, ignore_index=True)
                        fig = plot_radar_chart_with_baseline(athlete_df, radar_indicators, lower_better, ref_ranges, athlete_name, baseline_df, gender)
                        if fig: st.pyplot(fig); plt.close(); st.success("✅ 雷达图生成完成！")
                        else: st.info("ℹ️ 数据不足，无法生成雷达图")
                    else: st.warning("⚠️ 对比运动员组没有足够的数据")
    with tab4:
        st.subheader("完整数据表")
        st.write(athlete_df)
        try:
            csv = athlete_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(label="📥 下载CSV数据", data=csv, file_name=f"{athlete_name}_数据.csv", mime="text/csv")
        except: st.warning("CSV下载功能暂时不可用")

if __name__ == "__main__":
    main()
