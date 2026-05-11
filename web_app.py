"""
房地产项目成本对比分析系统 - Web前端入口
"""

import streamlit as st
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from data_parser import load_project, get_project_types
from type_matcher import match_types
from cost_comparator import compare_summary, compare_fixed_costs, compare_elastic_costs
from output_generator import generate_output

st.set_page_config(
    page_title="成本对比分析系统",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 房地产项目成本对比分析系统")
st.markdown("---")

with st.form("upload_form", clear_on_submit=False):
    st.subheader("📤 上传项目文件")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**项目A**")
        project_a_file = st.file_uploader("选择项目A的Excel文件", type=["xlsx"], key="file_a", label_visibility="collapsed")

    with col2:
        st.markdown("**项目B**")
        project_b_file = st.file_uploader("选择项目B的Excel文件", type=["xlsx"], key="file_b", label_visibility="collapsed")

    col_submit1, col_submit2, col_submit3 = st.columns([2, 1, 1])

    with col_submit1:
        output_filename = st.text_input("输出文件名", value="成本对比分析报告.xlsx", label_visibility="collapsed")

    with col_submit2:
        submitted = st.form_submit_button("🚀 开始分析", type="primary", use_container_width=True)

    with col_submit3:
        reset = st.form_submit_button("🔄 重置", use_container_width=True)

if submitted or 'uploaded' in st.session_state:
    if 'uploaded' not in st.session_state:
        st.session_state.uploaded = False

    if submitted:
        st.session_state.uploaded = True

    if project_a_file is not None:
        st.session_state.file_a_name = project_a_file.name
        st.session_state.file_a_size = len(project_a_file.getbuffer())
    else:
        st.session_state.file_a_name = None

    if project_b_file is not None:
        st.session_state.file_b_name = project_b_file.name
        st.session_state.file_b_size = len(project_b_file.getbuffer())
    else:
        st.session_state.file_b_name = None

    if reset:
        st.session_state.uploaded = False
        st.session_state.file_a_name = None
        st.session_state.file_b_name = None
        st.session_state.file_a_size = None
        st.session_state.file_b_size = None
        st.rerun()

if 'file_a_name' in st.session_state and st.session_state.file_a_name:
    size_str = f"{st.session_state.file_a_size/1024:.1f} KB" if st.session_state.file_a_size < 1024*1024 else f"{st.session_state.file_a_size/1024/1024:.1f} MB"
    st.success(f"📄 项目A已上传: {st.session_state.file_a_name} ({size_str})")

if 'file_b_name' in st.session_state and st.session_state.file_b_name:
    size_str = f"{st.session_state.file_b_size/1024:.1f} KB" if st.session_state.file_b_size < 1024*1024 else f"{st.session_state.file_b_size/1024/1024:.1f} MB"
    st.success(f"📄 项目B已上传: {st.session_state.file_b_name} ({size_str})")

if st.session_state.get('uploaded') and st.session_state.get('file_a_name') and st.session_state.get('file_b_name'):
    st.info("正在分析数据，请稍候...")

    with st.spinner("正在处理..."):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            file_a_path = os.path.join(temp_dir, "project_a.xlsx")
            file_b_path = os.path.join(temp_dir, "project_b.xlsx")

            with open(file_a_path, "wb") as f:
                f.write(project_a_file.getbuffer())
            with open(file_b_path, "wb") as f:
                f.write(project_b_file.getbuffer())

            try:
                data_a = load_project(file_a_path)
                data_b = load_project(file_b_path)

                types_a = get_project_types(data_a)
                types_b = get_project_types(data_b)
                matches = match_types(types_a, types_b)

                summary_data = compare_summary(data_a, data_b, matches)
                fixed_data = compare_fixed_costs(data_a, data_b, matches)
                elastic_data = compare_elastic_costs(data_a, data_b, matches)

                output_path = os.path.join(PROJECT_DIR, output_filename)
                generate_output(summary_data, fixed_data, elastic_data, output_path)

                st.success(f"✅ 报告已生成: {output_path}")

                with open(output_path, "rb") as f:
                    st.download_button(
                        label="⬇️ 下载Excel报告",
                        data=f,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                st.session_state.uploaded = False

            except Exception as e:
                st.error(f"处理失败: {str(e)}")

st.markdown("---")
st.caption("房地产项目成本对比分析系统 | 支持业态自动匹配 | Excel公式动态计算")
