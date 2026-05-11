import openpyxl
from typing import Dict, List, Any, Optional


def parse_basic_info(wb: openpyxl.Workbook) -> Dict[str, Any]:
    """解析02项目基础信息表（如果不存在则返回空字典）"""
    try:
        ws = wb["02 项目基础信息（输入）"]
    except KeyError:
        # 如果02表不存在，返回空字典，后续从其他表获取信息
        return {}
    
    info = {}
    
    # 读取建筑面积信息（根据实际格式调整）
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        if row[0] and "建筑面积" in str(row[0]):
            info["总建筑面积"] = row[1] if len(row) > 1 else None
        if row[0] and "可售面积" in str(row[0]):
            info["可售面积"] = row[1] if len(row) > 1 else None
    
    return info


def get_project_info_from_sheet(wb: openpyxl.Workbook, sheet_name: str) -> Dict[str, Any]:
    """从指定工作表获取项目基本信息（建筑面积、可售面积等）"""
    info = {}
    try:
        ws = wb[sheet_name]
    except KeyError:
        return info
    
    for row in ws.iter_rows(min_row=1, max_row=50, values_only=True):
        if len(row) == 0:
            continue
            
        # 查找建筑面积相关信息
        row_str = str(row[0]) if row[0] else ""
        if "建筑面积" in row_str or "建面" in row_str:
            for i in range(min(len(row), 10)):
                cell_val = row[i]
                if cell_val and isinstance(cell_val, (int, float)) and cell_val > 0:
                    if "总建筑面积" not in info or "总面积" in row_str:
                        info["总建筑面积"] = cell_val
                    elif "可售" in row_str:
                        info["可售面积"] = cell_val
        
        # 查找项目名称
        if "项目名称" in row_str or "项目" in row_str:
            for i in range(min(len(row), 10)):
                cell_val = row[i]
                if cell_val and isinstance(cell_val, str) and cell_val.strip():
                    if "名称" not in info:
                        info["名称"] = cell_val.strip()
                        break
    
    return info


def parse_cost_control(wb: openpyxl.Workbook, extracted_name: str = "") -> Dict[str, Any]:
    """解析04目标成本控制表"""
    ws = wb["04 目标成本控制表"]

    result = {
        "项目信息": {},
        "科目汇总": {},
        "业态数据": {},
        "汇总行": {},
    }

    # 读取项目信息（第4行）
    row4 = list(ws.iter_rows(min_row=4, max_row=4, values_only=True))[0]
    # 项目名称在C列(索引2)，但需要处理合并单元格的情况
    # 如果C列为空，尝试从B列获取
    project_name = ""
    if len(row4) > 2 and row4[2]:
        project_name = str(row4[2]).strip()
    elif len(row4) > 1 and row4[1]:
        project_name = str(row4[1]).strip()

    # 如果还是空，尝试从02表获取
    if not project_name:
        try:
            ws02 = wb["02 项目基础信息（输入）"]
            for row in ws02.iter_rows(min_row=1, max_row=20, values_only=True):
                if row[0] and "项目名称" in str(row[0]):
                    project_name = str(row[3]) if len(row) > 3 and row[3] else ""
                    break
        except:
            pass

    # 如果项目名称是模板名称（如"集团商业标准成本"、"苏州公司U3+档毛坯标准刻度"等），
    # 使用从文件名提取的项目名称
    template_names = ["集团商业标准成本", "苏州公司U3+档毛坯标准刻度", "标准", "模板"]
    is_template_name = any(template in project_name for template in template_names)
    if is_template_name and extracted_name:
        project_name = extracted_name

    result["项目信息"]["名称"] = project_name
    
    # 从04表获取建筑面积信息
    total_area = row4[5] if len(row4) > 5 and row4[5] else 0
    saleable_area = row4[9] if len(row4) > 9 and row4[9] else 0
    
    # 如果04表没有数据，尝试从05表获取
    if total_area == 0 or saleable_area == 0:
        try:
            info_from_05 = get_project_info_from_sheet(wb, "05 成本测算明细")
            if total_area == 0 and info_from_05.get("总建筑面积"):
                total_area = info_from_05["总建筑面积"]
            if saleable_area == 0 and info_from_05.get("可售面积"):
                saleable_area = info_from_05["可售面积"]
        except:
            pass
    
    # 如果还是没有，尝试从02表获取
    if total_area == 0 or saleable_area == 0:
        try:
            info_from_02 = get_project_info_from_sheet(wb, "02 项目基础信息（输入）")
            if total_area == 0 and info_from_02.get("总建筑面积"):
                total_area = info_from_02["总建筑面积"]
            if saleable_area == 0 and info_from_02.get("可售面积"):
                saleable_area = info_from_02["可售面积"]
        except:
            pass
    
    result["项目信息"]["总建筑面积"] = total_area
    result["项目信息"]["可售面积"] = saleable_area
    
    # 读取数据行
    current_subject = None
    for row in ws.iter_rows(min_row=8, max_row=ws.max_row, values_only=True):
        a_val = row[0] if row[0] else None
        b_val = row[1] if row[1] else None
        
        # 跳过空行
        if not a_val and not b_val:
            continue
        
        # 一级科目行
        if a_val and a_val in ["前期工程", "桩基础工程", "岩土工程", "单体工程", 
                                "配套工程", "室外工程", "户内装饰工程", 
                                "基础设施工程", "卖场包装费用", "其它"]:
            current_subject = a_val
            result["科目汇总"][current_subject] = {
                "总价": row[2] if len(row) > 2 and row[2] else 0,
                "相对建面": row[3] if len(row) > 3 and row[3] else 0,
                "相对建面单方": row[4] if len(row) > 4 and row[4] else 0,
                "相对建造面积": row[5] if len(row) > 5 and row[5] else 0,
                "相对建造单方": row[6] if len(row) > 6 and row[6] else 0,
                "可售面积": row[7] if len(row) > 7 and row[7] else 0,
                "可售单方": row[8] if len(row) > 8 and row[8] else 0,
            }
        
        # 汇总行
        elif a_val and a_val in ["合计", "总建安成本"]:
            key = "合计-毛坯" if a_val == "合计" else "总建安成本"
            result["汇总行"][key] = {
                "总价": row[2] if len(row) > 2 and row[2] else 0,
                "相对建面": row[3] if len(row) > 3 and row[3] else 0,
                "相对建面单方": row[4] if len(row) > 4 and row[4] else 0,
                "相对建造面积": row[5] if len(row) > 5 and row[5] else 0,
                "相对建造单方": row[6] if len(row) > 6 and row[6] else 0,
                "可售面积": row[7] if len(row) > 7 and row[7] else 0,
                "可售单方": row[8] if len(row) > 8 and row[8] else 0,
            }
        
        # 业态子行（在单体工程或户内装饰工程下）
        elif b_val and not b_val.startswith("$") and current_subject in ["单体工程", "户内装饰工程"]:
            # 判断是否为有效业态（总价>0 或 有面积数据）
            total_price = row[2] if len(row) > 2 and row[2] else 0
            area = row[3] if len(row) > 3 and row[3] else 0
            
            # 只保留有效业态（排除模板变量和零值业态）
            if total_price > 0 or area > 0:
                type_name = b_val
                if "(住宅)" in type_name:
                    type_name = type_name.replace("(住宅)", "")
                if "(商业)" in type_name:
                    type_name = type_name.replace("(商业)", "")
                
                # 统一业态名称：包含"叠墅"的都统一为"叠墅"
                if "叠墅" in type_name:
                    type_name = "叠墅"
                
                # 检查是否有同名业态已经存在
                if type_name in result["业态数据"]:
                    # 如果已存在，检查是否需要合并数据
                    existing_data = result["业态数据"][type_name]
                    # 如果现有数据没有当前科目，直接添加
                    if current_subject not in existing_data:
                        result["业态数据"][type_name][current_subject] = {
                            "总价": total_price,
                            "相对建面": area,
                            "相对建面单方": row[4] if len(row) > 4 and row[4] else 0,
                            "相对建造面积": row[5] if len(row) > 5 and row[5] else 0,
                            "相对建造单方": row[6] if len(row) > 6 and row[6] else 0,
                            "可售面积": row[7] if len(row) > 7 and row[7] else 0,
                            "可售单方": row[8] if len(row) > 8 and row[8] else 0,
                        }
                else:
                    # 尝试查找是否有相同面积的其他业态（可能是同一个业态的不同名称）
                    matched_type = None
                    for existing_type, existing_data in result["业态数据"].items():
                        # 检查是否有相同面积但缺少当前科目的业态
                        if existing_type != type_name:
                            existing_area = 0
                            for subject_data in existing_data.values():
                                existing_area = subject_data.get("相对建面", 0)
                                if existing_area > 0:
                                    break
                            if abs(existing_area - area) < 0.01 and current_subject not in existing_data:
                                matched_type = existing_type
                                break
                    
                    if matched_type:
                        # 合并到已存在的业态
                        result["业态数据"][matched_type][current_subject] = {
                            "总价": total_price,
                            "相对建面": area,
                            "相对建面单方": row[4] if len(row) > 4 and row[4] else 0,
                            "相对建造面积": row[5] if len(row) > 5 and row[5] else 0,
                            "相对建造单方": row[6] if len(row) > 6 and row[6] else 0,
                            "可售面积": row[7] if len(row) > 7 and row[7] else 0,
                            "可售单方": row[8] if len(row) > 8 and row[8] else 0,
                        }
                    else:
                        # 创建新的业态
                        result["业态数据"][type_name] = {}
                        result["业态数据"][type_name][current_subject] = {
                            "总价": total_price,
                            "相对建面": area,
                            "相对建面单方": row[4] if len(row) > 4 and row[4] else 0,
                            "相对建造面积": row[5] if len(row) > 5 and row[5] else 0,
                            "相对建造单方": row[6] if len(row) > 6 and row[6] else 0,
                            "可售面积": row[7] if len(row) > 7 and row[7] else 0,
                            "可售单方": row[8] if len(row) > 8 and row[8] else 0,
                        }
        
        # "其它"科目下的子项（如基础设施工程、卖场包装费用、专项设备设施费用）
        elif current_subject == "其它" and b_val and not b_val.startswith("$"):
            # 这些是"其它"科目下的子项，需要单独记录到科目汇总
            subject_name = b_val
            result["科目汇总"][subject_name] = {
                "总价": row[2] if len(row) > 2 and row[2] else 0,
                "相对建面": row[3] if len(row) > 3 and row[3] else 0,
                "相对建面单方": row[4] if len(row) > 4 and row[4] else 0,
                "相对建造面积": row[5] if len(row) > 5 and row[5] else 0,
                "相对建造单方": row[6] if len(row) > 6 and row[6] else 0,
                "可售面积": row[7] if len(row) > 7 and row[7] else 0,
                "可售单方": row[8] if len(row) > 8 and row[8] else 0,
            }
    
    return result


def parse_cost_detail(wb: openpyxl.Workbook) -> Dict[str, Any]:
    """解析05成本测算明细表
    
    05表结构特点：
    - 业态名称行：不以"03."开头，但包含业态关键词（如"地下室其他(住宅)"、"小高层"等）
    - 科目行：以"03.04."开头，包含编码和名称
    - 属性列：S列（索引18），值为"固定"、"弹性"或"暂定"
    
    数据列对应关系（基于实际Excel结构）：
    - D列(3): 含量说明（如"建筑面积（业态）"、"钢筋含量"等）
    - E列(4): 单位（如"㎡"、"kg"等）
    - G列(6): 含量/系数值（钢筋、混凝土等的含量数据）
    - J列(9): 相对建筑面积单方（元/㎡）- 成本单方
    - I列(8): 工程量值
    - S列(18): 属性（固定/弹性/暂定）
    """
    ws = wb["05 成本测算明细"]
    
    result = {
        "科目属性": {},
        "业态明细": {},
    }
    
    current_type = None  # 当前业态
    
    # 已知业态关键词列表
    type_keywords = [
        "地下室其他(住宅)", "地下室其他", "普通多层", "小高层", "高层", 
        "洋房", "叠拼", "叠墅", "联排", "其他公共配套", "幼儿园",
        "地库及机房(商业)", "集中商业", "写字楼", "酒店", "地库及机房"
    ]
    
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
        code_name = row[0] if row[0] else None
        if not code_name:
            continue
        
        code_name_str = str(code_name).strip()
        
        # 识别业态名称行
        # 特征：不以"03."开头，长度较短，包含已知业态关键词
        is_type_row = False
        for keyword in type_keywords:
            if code_name_str == keyword:
                is_type_row = True
                break
        
        # 也尝试通过特征识别未知业态
        if not is_type_row and not code_name_str.startswith("03.") and not code_name_str.startswith(" "):
            if len(code_name_str) < 30 and any(k in code_name_str for k in ["地下室", "小高层", "叠墅", "洋房", "公共配套", "多层", "高层", "商业", "办公", "地库"]):
                is_type_row = True
        
        if is_type_row:
            current_type = code_name_str.replace("(住宅)", "").replace("(商业)", "")
            if current_type not in result["业态明细"]:
                result["业态明细"][current_type] = {}
            continue

        # 识别科目行（以03.04.开头的行）
        if current_type and code_name_str.startswith("03.04."):
            # 提取科目编码和名称
            # 格式可能是 "03.04.01建筑工程" 或 "         03.04.01建筑工程"
            clean_code = code_name_str.strip()
            
            # 分割编码和名称
            # 编码格式：03.04.01 或 03.04.01.01 等
            parts = clean_code.split(None, 1)  # 按空白分割一次
            if len(parts) >= 2:
                code = parts[0].strip()
                name = parts[1].strip()
            else:
                # 尝试其他分割方式
                # 找到第一个中文字符的位置
                code = ""
                name = ""
                for i, char in enumerate(clean_code):
                    if '\u4e00' <= char <= '\u9fff':  # 中文字符
                        code = clean_code[:i].strip()
                        name = clean_code[i:].strip()
                        break
                if not code:
                    continue
            
            # 读取属性（S列，索引18）
            attr = row[18] if len(row) > 18 and row[18] else None
            if attr and attr in ["固定", "弹性", "暂定"]:
                # 记录二级科目的属性（编码格式为 XX.XX.XX）
                if code.count(".") == 2:
                    result["科目属性"][code] = attr
            
            # 读取数据列
            # G列(6):含量/系数值（钢筋含量等）
            # I列(8):工程量（门窗面积、电梯数量等）
            # K列(10):单价（元/kg、元/m3、元/㎡等）
            # O列(14):相对建筑面积单方（元/㎡）- 这是成本单方
            # N列(13):相对建筑面积
            danfang_val = row[14] if len(row) > 14 and row[14] else 0
            hanliang_val = row[6] if len(row) > 6 and row[6] else 0
            gongchengliang_val = row[8] if len(row) > 8 and row[8] else 0  # I列-工程量
            danjia_val = row[10] if len(row) > 10 and row[10] else 0

            # 如果该科目已有数据且当前行数据为空（或全为0），跳过以保留原始数据
            # 某些Excel可能有重复的科目行（子科目合计行等）
            existing = result["业态明细"][current_type].get(code)
            if existing and danfang_val == 0 and danjia_val == 0 and hanliang_val == 0:
                # 当前行无有效数据，但已有数据存在，跳过
                continue

            data = {
                "编码": code,
                "名称": name,
                "单方": danfang_val,  # O列-相对建筑面积单方(元/㎡)
                "含量": hanliang_val,  # G列-含量/系数值
                "工程量": gongchengliang_val,  # I列-工程量（门窗面积等）
                "含量说明": row[3] if len(row) > 3 and row[3] else "",  # D列-含量说明
                "单价": danjia_val,  # K列-单价(元/kg、元/m3等)
                "成本": row[11] if len(row) > 11 and row[11] else 0,  # L列-测算成本
                "相对建面": row[13] if len(row) > 13 and row[13] else 0,  # N列-相对建筑面积
                "属性": attr,
            }

            result["业态明细"][current_type][code] = data
    
    return result


def load_project(file_path: str) -> Dict[str, Any]:
    """加载单个项目的所有数据"""
    wb = openpyxl.load_workbook(file_path, data_only=True)

    # 从文件路径提取项目名称
    import os
    file_name = os.path.basename(file_path)
    # 尝试从文件名提取项目名称
    # 格式如: "02 永旺北地块-V1 2025_11_27（U3+）.xlsx" 或 "摩天轮地块V1测算（9F小高+5F叠墅）(1)(1).xlsx"
    extracted_name = ""
    # 移除扩展名
    name_part = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    # 尝试找到项目名称（通常在序号后面，如 "02 " 或 "04 " 后面）
    import re
    # 匹配 "序号 项目名称-版本号" 或 "项目名称V版本号" 格式
    patterns = [
        r'^\d+\s+(.+?)(?:-V\d+|$)',  # "02 永旺北地块-V1" -> "永旺北地块"
        r'^(.+?)(?:V\d+|$)',          # "摩天轮地块V1" -> "摩天轮地块"
    ]
    for pattern in patterns:
        match = re.match(pattern, name_part)
        if match:
            extracted_name = match.group(1).strip()
            break
    if not extracted_name:
        # 尝试取文件名开头的连续中文字符
        match = re.match(r'^[\u4e00-\u9fff]+', name_part)
        if match:
            extracted_name = match.group(0)

    project_data = {
        "文件路径": file_path,
        "文件名称": file_name,
        "提取的项目名称": extracted_name,
        "基础信息": parse_basic_info(wb),
        "成本控制": parse_cost_control(wb, extracted_name),
        "测算明细": parse_cost_detail(wb),
    }

    wb.close()
    return project_data


def get_project_types(project_data: Dict[str, Any]) -> List[str]:
    """获取项目中实际存在的业态列表（排除零值业态）"""
    types = []
    for type_name, type_data in project_data["成本控制"]["业态数据"].items():
        # 检查该业态是否有有效数据
        has_data = False
        for subject, data in type_data.items():
            if data.get("总价", 0) > 0 or data.get("相对建面", 0) > 0:
                has_data = True
                break
        if has_data:
            types.append(type_name)
    
    return types
