from typing import List, Dict, Tuple
from config import CATEGORY_MAP

# 业态优先级排序（从接近到疏远）
TYPE_PRIORITY = [
    "联排", "叠墅", "叠拼",
    "普通多层", "洋房",
    "小高层", "高层",
    "写字楼", "集中商业",
    "地下室", "地下其他", "地下室其他", "地库及机房",
    "其他公共配套", "幼儿园", "配套商业",
]

# 住宅业态相似度顺序（用于计算业态间距离）
RESIDENTIAL_TYPES = ["联排", "叠墅", "叠拼", "普通多层", "洋房", "小高层", "高层"]


def clean_type_name(type_name: str) -> str:
    """清理业态名称，去掉括号及其内容
    
    例如："普通多层（5F叠墅）" -> "普通多层"
    """
    if not type_name:
        return type_name
    
    # 找到第一个左括号的位置
    idx = type_name.find("（")
    if idx == -1:
        idx = type_name.find("(")
    
    if idx != -1:
        return type_name[:idx].strip()
    
    return type_name.strip()


def classify_type(type_name: str) -> str:
    """将业态名称分类到对应的大类"""
    # 先清理括号内容
    clean_name = clean_type_name(type_name)
    
    # 特殊处理：包含"叠墅"或"叠加"的业态优先归类为叠墅（叠加别墅）
    # 检查原始名称（包含括号内容），因为"普通多层（5F叠墅）"本质是叠墅类
    if "叠墅" in type_name or "叠加" in type_name:
        return "住宅低层"
    
    for category, types in CATEGORY_MAP.items():
        for t in types:
            if t in clean_name or clean_name in t:
                return category
    return "其他"


def get_type_priority(type_name: str) -> int:
    """获取业态的优先级（数字越小优先级越高）"""
    clean_name = clean_type_name(type_name)
    for i, priority_type in enumerate(TYPE_PRIORITY):
        if priority_type in clean_name or clean_name in priority_type:
            return i
    return len(TYPE_PRIORITY)


def get_residential_index(type_name: str) -> int:
    """获取业态在住宅业态序列中的位置（用于计算距离）"""
    clean_name = clean_type_name(type_name)
    for i, t in enumerate(RESIDENTIAL_TYPES):
        if t in clean_name or clean_name in t:
            return i
    return -1


def get_type_distance(type_a: str, type_b: str) -> int:
    """计算两种业态之间的距离（距离越小越接近）"""
    idx_a = get_residential_index(type_a)
    idx_b = get_residential_index(type_b)
    
    if idx_a == -1 or idx_b == -1:
        # 如果任一业态不在住宅序列中，返回较大距离
        return 999
    
    return abs(idx_a - idx_b)


def merge_similar_types(types: List[str]) -> List[str]:
    """合并项目内部相似的业态类型
    
    规则：
    1. 原始名称包含"叠墅"或"叠加"的业态合并为一个（保留第一个遇到的名称）
       - 检查原始名称，包含括号内容，所以"普通多层（5F叠墅）"会被识别为叠墅类
       - "叠墅"、"叠加别墅"、"普通多层（5F叠墅）"会被合并
    2. 清理括号后名称相同的非叠墅类业态合并为一个（如"普通多层"和"普通多层（洋房）"）
    3. 叠墅类业态不会和非叠墅类业态合并
    4. 其他业态保持不变
    """
    merged = []
    seen_stacked = False
    first_stacked = None
    seen_types = set()  # 记录已处理的清理后名称（仅用于非叠墅类）
    stacked_types_seen = set()  # 记录已处理的叠墅类原始名称
    
    # 找到第一个叠墅类业态（检查原始名称，包含括号内容）
    for t in types:
        if "叠墅" in t or "叠加" in t:
            first_stacked = t
            break
    
    for t in types:
        # 检查是否是叠墅类业态（检查原始名称，包含括号内容）
        is_stacked = "叠墅" in t or "叠加" in t
        
        if is_stacked:
            if t not in stacked_types_seen:
                if not seen_stacked:
                    # 保留第一个叠墅类业态的原始名称
                    merged.append(t)
                    seen_stacked = True
                stacked_types_seen.add(t)
            # 跳过其他叠墅类业态（已合并）
            continue
        
        # 清理括号内容（只用于非叠墅类业态的合并）
        clean_name = clean_type_name(t)
        
        # 检查清理后名称是否已处理过
        if clean_name in seen_types:
            continue
        
        merged.append(t)
        seen_types.add(clean_name)
    
    return merged


def match_types(types_a: List[str], types_b: List[str]) -> List[Tuple[str, str]]:
    """匹配两个项目的业态
    
    匹配规则（根据用户需求）：
    1. 精确匹配 - 名称完全相同优先（联排对应联排，叠墅对应叠墅/叠拼）
    2. 如果双方都只有一个业态但不同，也要进行对比（跨分类也匹配）
    3. 如果项目A业态多于项目B，选择最接近的业态进行匹配，不相近的不对比
    4. 如果项目B业态多于项目A，A的所有业态都参与匹配
    5. 业态接近程度：联排 > 叠墅(叠拼) > 普通多层(洋房) > 小高层 > 高层 > 写字楼 > 集中商业
    6. 同类业态内部匹配（住宅低层优先和住宅低层匹配，住宅中高层优先和住宅中高层匹配）
    7. 地下室只能和地下室匹配
    8. 如果一个项目只有一个住宅业态，另一个项目也只有一个住宅业态（不同分类），跨分类匹配
    9. 业态名称中的括号内容（如"普通多层（5F叠墅）"）视为说明，不影响匹配
    
    返回: [(项目A业态, 项目B业态), ...]
    """
    
    # 先合并项目内部的相似业态（如叠墅和叠加别墅合并为一个）
    types_a = merge_similar_types(types_a)
    types_b = merge_similar_types(types_b)
    
    # 特殊规则1：如果双方都只有一个业态，直接匹配（即使跨分类）
    if len(types_a) == 1 and len(types_b) == 1:
        return [(types_a[0], types_b[0])]
    
    # 分类
    a_categories = {"地下": [], "住宅低层": [], "住宅中高层": [], "公共配套": [], "商业": [], "其他": []}
    b_categories = {"地下": [], "住宅低层": [], "住宅中高层": [], "公共配套": [], "商业": [], "其他": []}
    
    for t in types_a:
        cat = classify_type(t)
        a_categories[cat].append(t)
    
    for t in types_b:
        cat = classify_type(t)
        b_categories[cat].append(t)
    
    # 统计住宅业态数量（住宅低层 + 住宅中高层）
    a_residential = a_categories["住宅低层"] + a_categories["住宅中高层"]
    b_residential = b_categories["住宅低层"] + b_categories["住宅中高层"]
    
    matches = []
    matched_b = set()
    matched_a = set()
    
    # 特殊规则2：如果一方只有一个住宅业态，另一方也只有一个住宅业态，先进行跨分类匹配
    if len(a_residential) == 1 and len(b_residential) == 1:
        a_res = a_residential[0]
        b_res = b_residential[0]
        # 检查是否已经匹配过（精确匹配）
        if a_res not in matched_a and b_res not in matched_b:
            # 如果不在同一分类，强制跨分类匹配
            a_cat = classify_type(a_res)
            b_cat = classify_type(b_res)
            if a_cat != b_cat:
                matches.append((a_res, b_res))
                matched_a.add(a_res)
                matched_b.add(b_res)
                # 从分类列表中移除
                if a_res in a_categories[a_cat]:
                    a_categories[a_cat].remove(a_res)
                if b_res in b_categories[b_cat]:
                    b_categories[b_cat].remove(b_res)
    
    for category in ["地下", "住宅低层", "住宅中高层", "公共配套", "商业", "其他"]:
        a_list = a_categories[category].copy()
        b_list = b_categories[category].copy()
        
        if not a_list and not b_list:
            continue
        
        # 规则1: 精确匹配（名称相同或叠墅/叠拼互认）
        for a_type in a_list[:]:
            for b_type in b_list[:]:
                if b_type in matched_b or a_type in matched_a:
                    continue
                
                # 使用清理后的名称进行比较（去掉括号内容）
                a_clean = clean_type_name(a_type)
                b_clean = clean_type_name(b_type)
                
                # 检查原始名称中是否包含叠墅/叠加（用于识别"普通多层（5F叠墅）"这种情况）
                a_has_stacked = "叠墅" in a_type or "叠加" in a_type
                b_has_stacked = "叠墅" in b_type or "叠加" in b_type
                
                # 精确匹配或叠墅叠拼互认
                # 如果任一业态原始名称包含叠墅/叠加，则视为可匹配的叠墅类业态
                if a_clean == b_clean or \
                   ("叠墅" in a_clean and "叠拼" in b_clean) or \
                   ("叠拼" in a_clean and "叠墅" in b_clean) or \
                   ("叠墅" in a_clean and "叠加" in b_clean) or \
                   ("叠加" in a_clean and "叠墅" in b_clean) or \
                   (a_has_stacked and b_has_stacked):
                    matches.append((a_type, b_type))
                    matched_b.add(b_type)
                    matched_a.add(a_type)
                    a_list.remove(a_type)
                    b_list.remove(b_type)
                    break
        
        # 规则2: 如果该分类下双方都只有一个业态且尚未匹配，则强制匹配
        if len(a_list) == 1 and len(b_list) == 1:
            a_type = a_list[0]
            b_type = b_list[0]
            if b_type not in matched_b and a_type not in matched_a:
                matches.append((a_type, b_type))
                matched_b.add(b_type)
                matched_a.add(a_type)
                a_list.remove(a_type)
                b_list.remove(b_type)
                continue
        
        # 规则3: 如果A业态多于B业态，选择最接近的业态进行匹配
        # 如果B业态多于或等于A业态，A的所有业态都参与匹配
        remaining_a = [t for t in a_list if t not in matched_a]
        remaining_b = [t for t in b_list if t not in matched_b]
        
        if len(remaining_a) > 0 and len(remaining_b) > 0:
            if len(remaining_a) > len(remaining_b):
                # A业态多，选择与B最接近的业态进行匹配
                # 为每个B业态找到最近的A业态
                for b_type in remaining_b[:]:
                    min_distance = 999
                    best_a = None
                    for a_type in remaining_a[:]:
                        if a_type in matched_a:
                            continue
                        distance = get_type_distance(a_type, b_type)
                        if distance < min_distance:
                            min_distance = distance
                            best_a = a_type
                    if best_a:
                        matches.append((best_a, b_type))
                        matched_a.add(best_a)
                        matched_b.add(b_type)
                        remaining_a.remove(best_a)
                        remaining_b.remove(b_type)
            else:
                # B业态多或相等，A的所有业态都参与匹配
                # 使用贪心算法：为每个A业态找到最近的B业态
                for a_type in remaining_a[:]:
                    min_distance = 999
                    best_b = None
                    for b_type in remaining_b[:]:
                        if b_type in matched_b:
                            continue
                        distance = get_type_distance(a_type, b_type)
                        if distance < min_distance:
                            min_distance = distance
                            best_b = b_type
                    if best_b:
                        matches.append((a_type, best_b))
                        matched_a.add(a_type)
                        matched_b.add(best_b)
                        remaining_a.remove(a_type)
                        remaining_b.remove(best_b)
        
        # 规则4: 如果B还有未匹配的业态，且A该分类已经没有业态了，添加B的业态（项目A为空）
        for b_type in b_list:
            if b_type not in matched_b:
                # 检查是否已经在matches中作为B出现
                if b_type not in [m[1] for m in matches if m[1]]:
                    matches.append((None, b_type))
    
    return matches


def get_matched_types(project_a_data: Dict, project_b_data: Dict) -> List[Tuple[str, str]]:
    """获取两个项目匹配后的业态对应关系"""
    from data_parser import get_project_types
    
    types_a = get_project_types(project_a_data)
    types_b = get_project_types(project_b_data)
    
    # 合并项目内部相似业态
    types_a_merged = merge_similar_types(types_a)
    types_b_merged = merge_similar_types(types_b)
    
    print(f"项目A业态: {types_a_merged}")
    print(f"项目B业态: {types_b_merged}")
    
    matches = match_types(types_a_merged, types_b_merged)
    
    print(f"\n业态匹配结果:")
    for a, b in matches:
        print(f"  {a} <-> {b}")
    
    return matches