from typing import Dict, List, Tuple, Any
from data_parser import get_project_types


def safe_float(value):
    """安全地将值转换为float，处理非数字内容"""
    if value is None:
        return 0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0


def find_matching_type_key(type_name: str, detail_keys: List[str], project_data: Dict = None) -> str:
    """在detail_keys中查找匹配type_name的key，支持模糊匹配"""
    if type_name in detail_keys:
        return type_name

    candidates = []

    for key in detail_keys:
        score = 0

        if type_name in key or key in type_name:
            score = 10
        elif type_name.replace("（", "(").replace("）", ")") == key.replace("（", "(").replace("）", ")"):
            score = 10
        elif "叠" in type_name and "叠" in key:
            score = 8
        elif "别墅" in type_name and "别墅" in key:
            score = 8
        elif any(k in key for k in ["地下室", "小高层", "洋房", "高层", "多层", "公共配套"]):
            if any(k in type_name for k in ["地下室", "小高层", "洋房", "高层", "多层", "公共配套"]):
                score = 3

        if score > 0:
            candidates.append((key, score))

    candidates.sort(key=lambda x: x[1], reverse=True)

    if project_data:
        detail_dict = project_data["测算明细"]["业态明细"]

        # 特殊处理：包含"叠"的key可能对应"普通多层"类型的key
        if "叠" in type_name:
            for key in detail_keys:
                base_name = key.split("（")[0].split("(")[0]
                # 如果base_name包含"多层"、"洋房"等词，且type_name包含"叠"
                if ("多层" in base_name or "洋房" in base_name) and ("叠" in type_name or "别墅" in type_name):
                    detail = detail_dict.get(key, {})
                    if detail:
                        return key

        # 首先查找有数据的候选
        for key, score in candidates:
            detail = detail_dict.get(key, {})
            if detail:
                return key

        # 如果所有候选都没有数据，返回得分最高的候选
        if candidates:
            return candidates[0][0]

        return None
    else:
        return candidates[0][0] if candidates else None


def _aggregate_density_items(valid_items: List[Dict], subject_code: str) -> Dict:
    """聚合密度型弹性科目的子项数据（入户门/安防/电梯）

    这些科目的子项共享同一个基础工程量（电梯台数、户数），但单价不同，
    需要聚合所有子项而不是只取第一个。
    """
    result = {'content': 0, 'price': 0, 'from_hanliang': False}

    if subject_code == "03.04.09":
        # 入户门工程：子项B系数不同，需要从 C/B 反推户数
        # 配置单价 = 总成本 / 户数
        total_cost = 0
        household_count = 0
        for item in valid_items:
            h = item['hanliang']
            g = item['gongchengliang']
            d = item['danjia']
            if isinstance(h, (int, float)) and h > 0 and isinstance(g, (int, float)) and g > 0:
                if household_count == 0:
                    household_count = g / h  # 户数 = 工程量 / 含量系数
                if isinstance(d, (int, float)) and d > 0:
                    total_cost += g * d
        if household_count > 0:
            result['content'] = household_count
            result['price'] = total_cost / household_count if household_count > 0 else 0
    else:
        # 电梯工程/安防系统：所有子项共享同一个工程量，单价求和
        content = 0
        price = 0
        for item in valid_items:
            g = item['gongchengliang']
            d = item['danjia']
            if isinstance(g, (int, float)) and g > 0:
                if content == 0:
                    content = g
                if isinstance(d, (int, float)) and d > 0:
                    price += d  # 单价求和（如供货+安装+其他）
        result['content'] = content
        result['price'] = price

    return result


def compare_summary(project_a: Dict, project_b: Dict, type_matches: List[Tuple[str, str]]) -> Dict[str, Any]:
    """生成成本对比总表数据"""
    
    result = {
        "项目A名称": project_a["成本控制"]["项目信息"].get("名称", "项目A"),
        "项目B名称": project_b["成本控制"]["项目信息"].get("名称", "项目B"),
        "项目A总面积": project_a["成本控制"]["项目信息"].get("总建筑面积", 0),
        "项目B总面积": project_b["成本控制"]["项目信息"].get("总建筑面积", 0),
        "项目A可售面积": project_a["成本控制"]["项目信息"].get("可售面积", 0),
        "项目B可售面积": project_b["成本控制"]["项目信息"].get("可售面积", 0),
        "科目对比": [],
        "业态对比": [],
    }
    
    # 一级科目对比
    subjects = ["前期工程", "桩基础工程", "岩土工程", "单体工程", "配套工程", 
                "室外工程", "户内装饰工程", "基础设施工程", "卖场包装费用"]
    
    for subject in subjects:
        a_data = project_a["成本控制"]["科目汇总"].get(subject, {})
        b_data = project_b["成本控制"]["科目汇总"].get(subject, {})
        
        result["科目对比"].append({
            "科目": subject,
            "项目A总价": a_data.get("总价", 0),
            "项目A建面单方": a_data.get("相对建面单方", 0),
            "项目A可售单方": a_data.get("可售单方", 0),
            "项目B总价": b_data.get("总价", 0),
            "项目B建面单方": b_data.get("相对建面单方", 0),
            "项目B可售单方": b_data.get("可售单方", 0),
            "建面单方差异": a_data.get("相对建面单方", 0) - b_data.get("相对建面单方", 0),
            "可售单方差异": a_data.get("可售单方", 0) - b_data.get("可售单方", 0),
            "相对建面单方差额": a_data.get("相对建面单方", 0) - b_data.get("相对建面单方", 0),
            "总建面单方差额": a_data.get("建面单方", 0) - b_data.get("建面单方", 0),
        })
    
    # 汇总行对比
    for summary_key in ["合计-毛坯", "总建安成本"]:
        if summary_key == "合计-毛坯":
            a_data = project_a["成本控制"]["汇总行"].get(summary_key, {})
            b_data = project_b["成本控制"]["汇总行"].get(summary_key, {})
        else:
            # 总建安成本 = 毛坯成本 + 户内装饰工程 + 基础设施工程 + 卖场包装费用
            a_maopi = project_a["成本控制"]["汇总行"].get("合计-毛坯", {})
            a_hunei = project_a["成本控制"]["科目汇总"].get("户内装饰工程", {})
            a_jichu = project_a["成本控制"]["科目汇总"].get("基础设施工程", {})
            a_maichang = project_a["成本控制"]["科目汇总"].get("卖场包装费用", {})
            
            b_maopi = project_b["成本控制"]["汇总行"].get("合计-毛坯", {})
            b_hunei = project_b["成本控制"]["科目汇总"].get("户内装饰工程", {})
            b_jichu = project_b["成本控制"]["科目汇总"].get("基础设施工程", {})
            b_maichang = project_b["成本控制"]["科目汇总"].get("卖场包装费用", {})
            
            a_total_price = a_maopi.get("总价", 0) + a_hunei.get("总价", 0) + a_jichu.get("总价", 0) + a_maichang.get("总价", 0)
            b_total_price = b_maopi.get("总价", 0) + b_hunei.get("总价", 0) + b_jichu.get("总价", 0) + b_maichang.get("总价", 0)
            
            # 计算单方 = 总价 / 总面积
            a_total_area = project_a["成本控制"]["项目信息"].get("总建筑面积", 1)
            b_total_area = project_b["成本控制"]["项目信息"].get("总建筑面积", 1)
            
            a_total_unit = a_total_price * 10000 / a_total_area if a_total_area > 0 else 0
            b_total_unit = b_total_price * 10000 / b_total_area if b_total_area > 0 else 0
            
            a_data = {
                "总价": a_total_price,
                "相对建面单方": a_total_unit,
                "可售单方": a_total_price * 10000 / project_a["成本控制"]["项目信息"].get("可售面积", 1) if project_a["成本控制"]["项目信息"].get("可售面积", 0) > 0 else 0,
                "建面单方": a_total_unit,
            }
            b_data = {
                "总价": b_total_price,
                "相对建面单方": b_total_unit,
                "可售单方": b_total_price * 10000 / project_b["成本控制"]["项目信息"].get("可售面积", 1) if project_b["成本控制"]["项目信息"].get("可售面积", 0) > 0 else 0,
                "建面单方": b_total_unit,
            }
        
        result["科目对比"].append({
            "科目": summary_key,
            "项目A总价": a_data.get("总价", 0),
            "项目A建面单方": a_data.get("相对建面单方", 0),
            "项目A可售单方": a_data.get("可售单方", 0),
            "项目B总价": b_data.get("总价", 0),
            "项目B建面单方": b_data.get("相对建面单方", 0),
            "项目B可售单方": b_data.get("可售单方", 0),
            "建面单方差异": a_data.get("相对建面单方", 0) - b_data.get("相对建面单方", 0),
            "可售单方差异": a_data.get("可售单方", 0) - b_data.get("可售单方", 0),
            "相对建面单方差额": a_data.get("相对建面单方", 0) - b_data.get("相对建面单方", 0),
            "总建面单方差额": a_data.get("建面单方", 0) - b_data.get("建面单方", 0),
        })
    
    # 业态对比（按科目分类存储）
    result["业态对比_单体工程"] = []
    result["业态对比_户内装饰工程"] = []
    
    # 辅助函数：查找业态数据，处理名称不一致的情况
    def find_type_data(project, type_name):
        if not type_name:
            return {}
        # 直接查找
        if type_name in project["成本控制"]["业态数据"]:
            return project["成本控制"]["业态数据"][type_name]
        # 如果找不到，尝试查找包含"叠墅"或"叠加"的业态
        if "叠墅" in type_name or "叠加" in type_name:
            for key in project["成本控制"]["业态数据"].keys():
                if "叠墅" in key or "叠加" in key:
                    return project["成本控制"]["业态数据"][key]
        return {}
    
    for type_a, type_b in type_matches:
        # 获取业态数据（处理一方为空的情况，以及名称不一致的情况）
        a_types_data = find_type_data(project_a, type_a)
        b_types_data = find_type_data(project_b, type_b)
        
        # 获取单体工程数据
        a_mono = a_types_data.get("单体工程", {})
        b_mono = b_types_data.get("单体工程", {})
        
        # 检查是否有实际数据（总价>0 或 面积>0）
        a_has_data = a_mono.get("总价", 0) > 0 or a_mono.get("相对建面", 0) > 0
        b_has_data = b_mono.get("总价", 0) > 0 or b_mono.get("相对建面", 0) > 0
        
        # 只有当任一项目有实际数据时才添加该行
        if a_has_data or b_has_data:
            result["业态对比_单体工程"].append({
                "项目A业态": type_a or "",
                "项目B业态": type_b or "",
                "项目A总价": a_mono.get("总价", 0),
                "项目A相对建面": a_mono.get("相对建面", 0),
                "项目A相对建面单方": a_mono.get("相对建面单方", 0),
                "项目A可售面积": a_mono.get("可售面积", 0),
                "项目A可售单方": a_mono.get("可售单方", 0),
                "项目B总价": b_mono.get("总价", 0),
                "项目B相对建面": b_mono.get("相对建面", 0),
                "项目B相对建面单方": b_mono.get("相对建面单方", 0),
                "项目B可售面积": b_mono.get("可售面积", 0),
                "项目B可售单方": b_mono.get("可售单方", 0),
                "相对建面单方差异": a_mono.get("相对建面单方", 0) - b_mono.get("相对建面单方", 0),
                "可售单方差异": a_mono.get("可售单方", 0) - b_mono.get("可售单方", 0),
            })
        
        # 获取户内装饰工程数据
        a_deco = a_types_data.get("户内装饰工程", {})
        b_deco = b_types_data.get("户内装饰工程", {})
        
        # 检查是否有实际数据（总价>0 或 面积>0）
        a_deco_has_data = a_deco.get("总价", 0) > 0 or a_deco.get("相对建面", 0) > 0
        b_deco_has_data = b_deco.get("总价", 0) > 0 or b_deco.get("相对建面", 0) > 0
        
        # 只有当任一项目有实际数据时才添加该行
        if a_deco_has_data or b_deco_has_data:
            result["业态对比_户内装饰工程"].append({
                "项目A业态": type_a or "",
                "项目B业态": type_b or "",
                "项目A总价": a_deco.get("总价", 0),
                "项目A相对建面": a_deco.get("相对建面", 0),
                "项目A相对建面单方": a_deco.get("相对建面单方", 0),
                "项目A可售面积": a_deco.get("可售面积", 0),
                "项目A可售单方": a_deco.get("可售单方", 0),
                "项目B总价": b_deco.get("总价", 0),
                "项目B相对建面": b_deco.get("相对建面", 0),
                "项目B相对建面单方": b_deco.get("相对建面单方", 0),
                "项目B可售面积": b_deco.get("可售面积", 0),
                "项目B可售单方": b_deco.get("可售单方", 0),
                "相对建面单方差异": a_deco.get("相对建面单方", 0) - b_deco.get("相对建面单方", 0),
                "可售单方差异": a_deco.get("可售单方", 0) - b_deco.get("可售单方", 0),
            })
    
    return result


def compare_fixed_costs(project_a: Dict, project_b: Dict, type_matches: List[Tuple[str, str]]) -> Dict[str, Any]:
    """生成固定单方差异明细分析数据"""
    
    result = {
        "项目A名称": project_a["成本控制"]["项目信息"].get("名称", "项目A"),
        "项目B名称": project_b["成本控制"]["项目信息"].get("名称", "项目B"),
        "业态分析": [],
    }
    
    # 固定科目列表
    fixed_subjects = [
        "03.04.01",  # 建筑工程
        "03.04.02",  # 人防工程
        "03.04.03",  # 防水工程
        "03.04.04",  # 防火门工程
        "03.04.05",  # 其他门窗工程
        "03.04.06",  # 常规机电工程
        "03.04.07",  # 消防工程
        "03.04.08",  # 钢结构工程
        "03.04.11",  # 外墙保温工程
        "03.04.15",  # 大堂门工程
        "03.04.16",  # 空调工程
        "03.04.17",  # 直饮水系统工程
        "03.04.18",  # 中水系统工程
        "03.04.19",  # 采暖工程
        "03.04.21",  # 有线电视工程
        "03.04.22",  # 电信及网络系统工程
        "03.04.24",  # 地坪处理工程
        "03.04.25",  # 交通标识工程
        "03.04.26",  # 太阳能热水器
        "03.04.27",  # 外遮阳工程
        "03.04.28",  # 泛光照明工程
        "03.04.29",  # 停车场管理系统
        "03.04.30",  # 机械停车工程
        "03.04.31",  # 其他装饰工程
        "03.04.32",  # 室内环境监测
        "03.04.33",  # 其他
    ]

    for type_a, type_b in type_matches:
        # 如果双方都没有有效的业态类型，跳过
        if not type_a and not type_b:
            continue
        
        a_keys = list(project_a["测算明细"]["业态明细"].keys())
        b_keys = list(project_b["测算明细"]["业态明细"].keys())

        matched_key_a = find_matching_type_key(type_a, a_keys, project_a) if type_a else None
        matched_key_b = find_matching_type_key(type_b, b_keys, project_b) if type_b else None

        a_detail = project_a["测算明细"]["业态明细"].get(matched_key_a, {}) if matched_key_a else {}
        b_detail = project_b["测算明细"]["业态明细"].get(matched_key_b, {}) if matched_key_b else {}

        # 如果双方都没有有效数据，跳过（与汇总表保持一致）
        if not a_detail and not b_detail:
            continue

        type_analysis = {
            "业态A": type_a or "",
            "业态B": type_b or "",
            "科目明细": [],
            # 从成本控制数据获取固定成本汇总值（用于汇总行，与成本对比总表保持一致）
            "汇总_项目A单方": 0,
            "汇总_项目B单方": 0,
            "汇总_差异": 0,
        }
        
        # 从成本控制数据获取该业态的固定成本（单体工程）汇总值
        # 需要处理业态名称可能不一致的情况（如"叠加别墅"和"叠墅"）
        def find_type_data(project, type_name):
            # 处理 None 的情况
            if not type_name:
                return {}
            # 直接查找
            if type_name in project["成本控制"]["业态数据"]:
                return project["成本控制"]["业态数据"][type_name].get("单体工程", {})
            # 如果找不到，尝试查找包含"叠墅"或"叠加"的业态
            if "叠墅" in type_name or "叠加" in type_name:
                for key in project["成本控制"]["业态数据"].keys():
                    if "叠墅" in key or "叠加" in key:
                        return project["成本控制"]["业态数据"][key].get("单体工程", {})
            return {}
        
        a_type_data = find_type_data(project_a, type_a)
        b_type_data = find_type_data(project_b, type_b)
        
        type_analysis["汇总_项目A单方"] = safe_float(a_type_data.get("相对建面单方", 0))
        type_analysis["汇总_项目B单方"] = safe_float(b_type_data.get("相对建面单方", 0))
        type_analysis["汇总_差异"] = type_analysis["汇总_项目A单方"] - type_analysis["汇总_项目B单方"]
        
        # 预检查：如果项目A没有该业态（type_a为空），检查项目B是否有任何有效数据
        # 如果没有，跳过该对比（与汇总表逻辑一致）
        if not type_a and not b_detail:
            continue
        
        for subject_code in fixed_subjects:
            a_data = a_detail.get(subject_code, {})
            b_data = b_detail.get(subject_code, {})

            if not a_data and not b_data:
                continue

            # 获取含量和单价
            a_content = safe_float(a_data.get("含量", 0))
            b_content = safe_float(b_data.get("含量", 0))
            a_price = safe_float(a_data.get("单价", 0))
            b_price = safe_float(b_data.get("单价", 0))
            a_danfang = safe_float(a_data.get("单方", 0))
            b_danfang = safe_float(b_data.get("单方", 0))

            # 如果Excel中的单方值有效，直接使用它；否则尝试用含量×单价计算
            a_unit_price = a_danfang if a_danfang > 0 else (a_content * a_price if a_content > 0 and a_price > 0 else 0)
            b_unit_price = b_danfang if b_danfang > 0 else (b_content * b_price if b_content > 0 and b_price > 0 else 0)

            # 计算影响（使用平均法）
            avg_content = (a_content + b_content) / 2 if (a_content + b_content) > 0 else 0
            avg_price = (a_price + b_price) / 2 if (a_price + b_price) > 0 else 0

            price_impact = (a_price - b_price) * avg_content
            content_impact = (a_content - b_content) * avg_price

            # 过滤掉对比数据全为0的行（但如果任一方有数据，即使另一方为0，也要保留）
            if a_unit_price == 0 and b_unit_price == 0 and a_content == 0 and b_content == 0 and a_price == 0 and b_price == 0:
                # 检查是否有任何一方有原始数据（即使计算后为0）
                has_a_data = bool(a_data) and any(safe_float(v) > 0 for v in a_data.values() if isinstance(v, (int, float, str)))
                has_b_data = bool(b_data) and any(safe_float(v) > 0 for v in b_data.values() if isinstance(v, (int, float, str)))
                if not has_a_data and not has_b_data:
                    continue

            type_analysis["科目明细"].append({
                "科目编码": subject_code,
                "科目名称": a_data.get("名称", b_data.get("名称", "")),
                "项目A单方": a_unit_price,
                "项目A含量": a_content,
                "项目A单价": a_price,
                "项目B单方": b_unit_price,
                "项目B含量": b_content,
                "项目B单价": b_price,
                "单方差异": a_unit_price - b_unit_price,
                "价格差异影响": price_impact,
                "含量差异影响": content_impact,
            })
            if subject_code == "03.04.01":
                construction_subjects = [
                    "03.04.01.01",  # 钢筋工程
                    "03.04.01.02",  # 模板工程
                    "03.04.01.03",  # 混凝土工程
                    "03.04.01.04",  # 砌筑工程
                    "03.04.01.05",  # 粗装修工程
                    "03.04.01.06",  # 保温工程
                    "03.04.01.07",  # 其他建筑工程
                    "03.04.01.08",  # 开办费
                ]

                for sub_code in construction_subjects:
                    a_sub = a_detail.get(sub_code, {})
                    b_sub = b_detail.get(sub_code, {})

                    if not a_sub and not b_sub:
                        continue

                    # 获取含量和单价
                    a_sub_content = safe_float(a_sub.get("含量", 0))
                    b_sub_content = safe_float(b_sub.get("含量", 0))
                    a_sub_price = safe_float(a_sub.get("单价", 0))
                    b_sub_price = safe_float(b_sub.get("单价", 0))
                    a_sub_danfang = safe_float(a_sub.get("单方", 0))
                    b_sub_danfang = safe_float(b_sub.get("单方", 0))

                    # 根据不同科目类型处理
                    # 钢筋工程(03.04.01.01)和混凝土工程(03.04.01.03)：使用合并单价
                    # 模板工程(03.04.01.02)和砌筑工程(03.04.01.04)：含量×单价=单方
                    # 粗装修(03.04.01.05)和开办费(03.04.01.08)：直接使用单方值
                    
                    if sub_code in ["03.04.01.01", "03.04.01.03"]:
                        # 钢筋、混凝土：使用汇总行单方，从四级子项读取含量，计算合并单价
                        # 单方：从三级科目汇总行读取
                        # 含量：从四级子项（主材）读取
                        # 单价：计算 = 单方 / 含量
                        a_sub_unit = a_sub_danfang if a_sub_danfang > 0 else 0
                        b_sub_unit = b_sub_danfang if b_sub_danfang > 0 else 0
                        
                        # 尝试从四级子项读取含量（钢筋主材或混凝土主材）
                        material_sub_code = sub_code + ".01"  # 03.04.01.01.01 或 03.04.01.03.01
                        a_material = a_detail.get(material_sub_code, {})
                        b_material = b_detail.get(material_sub_code, {})
                        
                        # 安全地转换含量为float，处理可能的非数字内容
                        a_sub_content = safe_float(a_material.get("含量", 0))
                        b_sub_content = safe_float(b_material.get("含量", 0))
                        
                        # 如果四级子项没有含量，使用三级科目本身的含量
                        if a_sub_content == 0:
                            a_sub_content = safe_float(a_sub.get("含量", 0))
                        if b_sub_content == 0:
                            b_sub_content = safe_float(b_sub.get("含量", 0))
                        
                        # 计算合并单价 = 单方 / 含量
                        a_sub_price = a_sub_unit / a_sub_content if a_sub_content > 0 else 0
                        b_sub_price = b_sub_unit / b_sub_content if b_sub_content > 0 else 0
                    elif sub_code in ["03.04.01.02", "03.04.01.04"]:
                        # 模板、砌筑：含量×单价=单方
                        a_sub_unit = a_sub_content * a_sub_price
                        b_sub_unit = b_sub_content * b_sub_price
                    else:
                        # 粗装修、开办费等：直接使用单方值
                        a_sub_unit = a_sub_danfang if a_sub_danfang > 0 else (a_sub_content * a_sub_price if a_sub_content > 0 and a_sub_price > 0 else 0)
                        b_sub_unit = b_sub_danfang if b_sub_danfang > 0 else (b_sub_content * b_sub_price if b_sub_content > 0 and b_sub_price > 0 else 0)

                    avg_sub_content = (a_sub_content + b_sub_content) / 2 if (a_sub_content + b_sub_content) > 0 else 0
                    avg_sub_price = (a_sub_price + b_sub_price) / 2 if (a_sub_price + b_sub_price) > 0 else 0

                    sub_price_impact = (a_sub_price - b_sub_price) * avg_sub_content
                    sub_content_impact = (a_sub_content - b_sub_content) * avg_sub_price

                    # 过滤掉对比数据全为0的行
                    if a_sub_unit == 0 and b_sub_unit == 0 and a_sub_content == 0 and b_sub_content == 0 and a_sub_price == 0 and b_sub_price == 0:
                        continue

                    type_analysis["科目明细"].append({
                        "科目编码": sub_code,
                        "科目名称": a_sub.get("名称", b_sub.get("名称", "")),
                        "项目A单方": a_sub_unit,
                        "项目A含量": a_sub_content,
                        "项目A单价": a_sub_price,
                        "项目B单方": b_sub_unit,
                        "项目B含量": b_sub_content,
                        "项目B单价": b_sub_price,
                        "单方差异": a_sub_unit - b_sub_unit,
                        "价格差异影响": sub_price_impact,
                        "含量差异影响": sub_content_impact,
                    })
        
        if type_analysis["科目明细"]:
            result["业态分析"].append(type_analysis)
    
    return result


def compare_elastic_costs(project_a: Dict, project_b: Dict, type_matches: List[Tuple[str, str]]) -> Dict[str, Any]:
    """生成弹性单方差异明细分析数据"""
    
    result = {
        "项目A名称": project_a["成本控制"]["项目信息"].get("名称", "项目A"),
        "项目B名称": project_b["成本控制"]["项目信息"].get("名称", "项目B"),
        "业态分析": [],
    }
    
    # 弹性科目配置（根据SKILL文档）
    # content_unit = "-" 表示该科目不需要显示含量指标
    # price_unit = "-" 表示该科目不需要显示配置单价
    elastic_subjects = {
        "03.04.09": {"name": "入户门工程", "content_unit": "户/万㎡", "price_unit": "元/套"},  # 户密度
        "03.04.10": {"name": "外立面门窗工程", "content_unit": "窗面积/建筑面积", "price_unit": "元/㎡"},  # 窗积比
        "03.04.12": {"name": "外立面装饰工程", "content_unit": None, "price_unit": None},  # 无含量指标和配置单价
        "03.04.13": {"name": "栏杆工程", "content_unit": None, "price_unit": None},  # 无含量指标和配置单价
        "03.04.14": {"name": "公共部位装饰工程", "content_unit": None, "price_unit": None},  # 无含量指标和配置单价
        "03.04.20": {"name": "安防系统", "content_unit": "户/万㎡", "price_unit": "元/户"},  # 户密度
        "03.04.23": {"name": "电梯工程", "content_unit": "梯/万㎡", "price_unit": "元/部"},  # 梯密度
    }
    
    for type_a, type_b in type_matches:
        # 如果双方都没有有效的业态类型，跳过
        if not type_a and not type_b:
            continue
        
        # 如果项目A或项目B没有有效的业态类型（空值或None），跳过对比
        if not type_a or not type_b:
            continue
        
        a_keys = list(project_a["测算明细"]["业态明细"].keys())
        b_keys = list(project_b["测算明细"]["业态明细"].keys())

        matched_key_a = find_matching_type_key(type_a, a_keys, project_a) if type_a else None
        matched_key_b = find_matching_type_key(type_b, b_keys, project_b) if type_b else None

        a_detail = project_a["测算明细"]["业态明细"].get(matched_key_a, {}) if matched_key_a else {}
        b_detail = project_b["测算明细"]["业态明细"].get(matched_key_b, {}) if matched_key_b else {}

        # 如果双方都没有有效数据，跳过（与汇总表保持一致）
        if not a_detail and not b_detail:
            continue

        # 成本控制业态key可能与type_a名称不一致，使用模糊匹配
        cc_keys_a = list(project_a["成本控制"]["业态数据"].keys()) if type_a else []
        cc_key_a = find_matching_type_key(type_a, cc_keys_a) if type_a else None
        cc_keys_b = list(project_b["成本控制"]["业态数据"].keys()) if type_b else []
        cc_key_b = find_matching_type_key(type_b, cc_keys_b) if type_b else None
        a_type_data = project_a["成本控制"]["业态数据"].get(cc_key_a, {}).get("单体工程", {}) if cc_key_a else {}
        b_type_data = project_b["成本控制"]["业态数据"].get(cc_key_b, {}).get("单体工程", {}) if cc_key_b else {}
        a_relative_area = a_type_data.get("相对建面", 0) or project_a["成本控制"]["项目信息"].get("总建筑面积", 1) if type_a else project_a["成本控制"]["项目信息"].get("总建筑面积", 1)
        b_relative_area = b_type_data.get("相对建面", 0) or project_b["成本控制"]["项目信息"].get("总建筑面积", 1) if type_b else project_b["成本控制"]["项目信息"].get("总建筑面积", 1)

        # 预检查：如果项目A没有该业态（type_a为空），检查项目B是否有任何有效数据
        # 如果没有，跳过该对比（与汇总表逻辑一致）
        if not type_a and not b_detail:
            continue

        type_analysis = {
            "业态A": type_a or "",
            "业态B": type_b or "",
            "科目明细": [],
        }

        has_any_data = False

        for subject_code, config in elastic_subjects.items():
            a_data = a_detail.get(subject_code, {})
            b_data = b_detail.get(subject_code, {})
            
            if not a_data and not b_data:
                continue
            
            # 获取基础数据
            a_danfang = safe_float(a_data.get("单方", 0))
            b_danfang = safe_float(b_data.get("单方", 0))
            
            # 获取科目配置
            content_unit = config.get("content_unit")
            price_unit = config.get("price_unit")
            
            # 尝试从子项获取含量指标和配置单价
            a_content = 0
            b_content = 0
            a_price = 0
            b_price = 0
            a_content_from_hanliang = False  # 标记是否从含量字段获取的
            b_content_from_hanliang = False
            
            # 只有当科目需要含量指标和配置单价时，才从子项获取数据
            if content_unit is not None and price_unit is not None:
                # 遍历子项获取数据（子项代码如03.04.09.05，四级科目）
                # 策略：首先收集所有有效的含量值（不是1或0），然后选择最合理的一个
                
                # 先收集项目A的有效数据
                valid_a_items = []
                for key, sub_data in a_detail.items():
                    if key.startswith(subject_code + ".") and len(key.split(".")) == 4:
                        sub_hanliang = sub_data.get("含量", 0)
                        sub_gongchengliang = sub_data.get("工程量", 0)
                        sub_danjia = sub_data.get("单价", 0)
                        if isinstance(sub_hanliang, (int, float)) or isinstance(sub_gongchengliang, (int, float)):
                            valid_a_items.append({
                                'hanliang': sub_hanliang,
                                'gongchengliang': sub_gongchengliang,
                                'danjia': sub_danjia
                            })
                
                # 密度型科目（入户门/安防/电梯）使用聚合逻辑
                if subject_code in ["03.04.09", "03.04.20", "03.04.23"]:
                    # 聚合所有子项：电梯/安防的单价求和，入户门反推户数
                    a_aggregated = _aggregate_density_items(valid_a_items, subject_code)
                    a_content = a_aggregated['content']
                    a_price = a_aggregated['price']
                    a_content_from_hanliang = a_aggregated['from_hanliang']
                else:
                    # 非密度型科目：从有效数据中选择最优值（原有逻辑）
                    for item in valid_a_items:
                        h = item['hanliang']
                        g = item['gongchengliang']
                        d = item['danjia']

                        if isinstance(h, (int, float)) and h > 0 and h != 1 and h != 0:
                            a_content = h
                            a_content_from_hanliang = True
                            if isinstance(d, (int, float)) and d > 0:
                                a_price = d
                        elif a_content == 0 and isinstance(g, (int, float)) and g > 0:
                            a_content = g
                            if isinstance(d, (int, float)) and d > 0 and a_price == 0:
                                a_price = d

                # 项目B同样处理
                valid_b_items = []
                for key, sub_data in b_detail.items():
                    if key.startswith(subject_code + ".") and len(key.split(".")) == 4:
                        sub_hanliang = sub_data.get("含量", 0)
                        sub_gongchengliang = sub_data.get("工程量", 0)
                        sub_danjia = sub_data.get("单价", 0)
                        if isinstance(sub_hanliang, (int, float)) or isinstance(sub_gongchengliang, (int, float)):
                            valid_b_items.append({
                                'hanliang': sub_hanliang,
                                'gongchengliang': sub_gongchengliang,
                                'danjia': sub_danjia
                            })

                if subject_code in ["03.04.09", "03.04.20", "03.04.23"]:
                    b_aggregated = _aggregate_density_items(valid_b_items, subject_code)
                    b_content = b_aggregated['content']
                    b_price = b_aggregated['price']
                    b_content_from_hanliang = b_aggregated['from_hanliang']
                else:
                    for item in valid_b_items:
                        h = item['hanliang']
                        g = item['gongchengliang']
                        d = item['danjia']

                        if isinstance(h, (int, float)) and h > 0 and h != 1 and h != 0:
                            b_content = h
                            b_content_from_hanliang = True
                            if isinstance(d, (int, float)) and d > 0:
                                b_price = d
                        elif b_content == 0 and isinstance(g, (int, float)) and g > 0:
                            b_content = g
                            if isinstance(d, (int, float)) and d > 0 and b_price == 0:
                                b_price = d

            # 计算含量指标（根据定义）
            if subject_code in ["03.04.09", "03.04.20"]:
                # 户密度 = 户数 / 相对建筑面积 × 10000
                a_content_ratio = a_content / a_relative_area * 10000 if a_relative_area > 0 else 0
                b_content_ratio = b_content / b_relative_area * 10000 if b_relative_area > 0 else 0
            elif subject_code == "03.04.10":
                # 窗积比：如果从含量字段获取，已经是窗积比；如果从工程量获取，需要除以建筑面积
                if a_content_from_hanliang:
                    a_content_ratio = a_content  # 已经是窗积比
                else:
                    a_content_ratio = a_content / a_relative_area if a_relative_area > 0 else 0
                
                if b_content_from_hanliang:
                    b_content_ratio = b_content  # 已经是窗积比
                else:
                    b_content_ratio = b_content / b_relative_area if b_relative_area > 0 else 0
            elif subject_code == "03.04.23":
                # 梯密度 = 电梯数 / 相对建筑面积 × 10000
                a_content_ratio = a_content / a_relative_area * 10000 if a_relative_area > 0 else 0
                b_content_ratio = b_content / b_relative_area * 10000 if b_relative_area > 0 else 0
            else:
                a_content_ratio = a_content
                b_content_ratio = b_content
            
            # 计算单方：当含量指标和配置单价都可用时，始终用公式重新计算
            # 公式: 单方 = 含量指标 × 配置单价 / 10000 (入户门/安防/电梯)
            # 公式: 单方 = 含量指标 × 配置单价      (外立面门窗)
            # 这样做确保: 含量影响 + 单价影响 = 单方差异（等式恒成立）
            is_density_subject = subject_code in ["03.04.09", "03.04.20", "03.04.23"]
            divisor = 10000 if is_density_subject else 1
            
            # 项目A单方
            if a_content_ratio > 0 and a_price > 0:
                a_unit_price = a_content_ratio * a_price / divisor
            elif a_danfang > 0:
                a_unit_price = a_danfang
            else:
                a_unit_price = 0
            
            # 项目B单方
            if b_content_ratio > 0 and b_price > 0:
                b_unit_price = b_content_ratio * b_price / divisor
            elif b_danfang > 0:
                b_unit_price = b_danfang
            else:
                b_unit_price = 0
            
            # 反推缺失的配置单价：当单方和含量都有，但单价缺失时
            if a_unit_price > 0 and a_content_ratio > 0 and a_price == 0:
                a_price = a_unit_price * divisor / a_content_ratio
            if b_unit_price > 0 and b_content_ratio > 0 and b_price == 0:
                b_price = b_unit_price * divisor / b_content_ratio
            
            # 计算影响（使用平均法）
            avg_content = (a_content_ratio + b_content_ratio) / 2 if (a_content_ratio + b_content_ratio) > 0 else 0
            avg_price = (a_price + b_price) / 2 if (a_price + b_price) > 0 else 0
            
            content_impact = (a_content_ratio - b_content_ratio) * avg_price
            if subject_code in ["03.04.09", "03.04.20", "03.04.23"]:
                content_impact = content_impact / 10000
            price_impact = (a_price - b_price) * avg_content
            if subject_code in ["03.04.09", "03.04.20", "03.04.23"]:
                price_impact = price_impact / 10000
            
            # 过滤掉对比数据全为0的行
            if a_unit_price == 0 and b_unit_price == 0 and a_content_ratio == 0 and b_content_ratio == 0:
                continue

            # 生成差异说明
            diff_parts = []
            if abs(content_impact) > 0.01:
                diff_parts.append(f"含量影响: {content_impact:.2f}元/㎡")
            if abs(price_impact) > 0.01:
                diff_parts.append(f"配置影响: {price_impact:.2f}元/㎡")

            # 如果含量和配置影响都为0但单方有差异，说明缺少明细数据无法分解
            if not diff_parts and abs(a_unit_price - b_unit_price) > 0.01:
                diff_parts.append(f"无法分解（缺少含量/单价明细），单方差: {a_unit_price - b_unit_price:.2f}元/㎡")

            diff_desc = "；".join(diff_parts) if diff_parts else ""

            type_analysis["科目明细"].append({
                "科目编码": subject_code,
                "科目名称": a_data.get("名称", b_data.get("名称", config["name"])),
                "项目A单方": a_unit_price,
                "项目A含量指标": a_content_ratio,
                "项目A配置单价": a_price,
                "项目B单方": b_unit_price,
                "项目B含量指标": b_content_ratio,
                "项目B配置单价": b_price,
                "单方差异": a_unit_price - b_unit_price,
                "差异说明": diff_desc,
                "含量差异影响": content_impact,
                "配置差异影响": price_impact,
                "含量单位": config["content_unit"],
                "配置单价单位": config["price_unit"],
            })

        if type_analysis["科目明细"]:
            result["业态分析"].append(type_analysis)

    return result
