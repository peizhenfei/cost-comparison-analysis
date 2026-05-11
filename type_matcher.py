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


def classify_type(type_name: str) -> str:
    """将业态名称分类到对应的大类"""
    # 特殊处理：包含"叠墅"的业态优先归类为叠墅
    if "叠墅" in type_name:
        return "住宅低层"
    
    for category, types in CATEGORY_MAP.items():
        for t in types:
            if t in type_name or type_name in t:
                return category
    return "其他"


def get_type_priority(type_name: str) -> int:
    """获取业态的优先级（数字越小优先级越高）"""
    for i, priority_type in enumerate(TYPE_PRIORITY):
        if priority_type in type_name or type_name in priority_type:
            return i
    return len(TYPE_PRIORITY)


def get_residential_index(type_name: str) -> int:
    """获取业态在住宅业态序列中的位置（用于计算距离）"""
    for i, t in enumerate(RESIDENTIAL_TYPES):
        if t in type_name or type_name in t:
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


def match_types(types_a: List[str], types_b: List[str]) -> List[Tuple[str, str]]:
    """匹配两个项目的业态
    
    匹配规则（根据用户需求）：
    1. 精确匹配 - 名称完全相同优先（联排对应联排，叠墅对应叠墅/叠拼）
    2. 如果双方都只有一个业态但不同，也要进行对比（跨分类也匹配）
    3. 如果项目A业态多于项目B，选择最接近的业态进行匹配，不相近的不对比
    4. 如果项目B业态多于项目A，A的所有业态都参与匹配
    5. 业态接近程度：联排 > 叠墅(叠拼) > 普通多层(洋房) > 小高层 > 高层 > 写字楼 > 集中商业
    6. 同类业态内部匹配（住宅低层只能和住宅低层匹配，住宅中高层只能和住宅中高层匹配）
    7. 地下室只能和地下室匹配
    
    返回: [(项目A业态, 项目B业态), ...]
    """
    
    # 特殊规则：如果双方都只有一个业态，直接匹配（即使跨分类）
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
    
    matches = []
    matched_b = set()
    matched_a = set()
    
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
                # 精确匹配或叠墅叠拼互认
                if a_type == b_type or \
                   ("叠墅" in a_type and "叠拼" in b_type) or \
                   ("叠拼" in a_type and "叠墅" in b_type):
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
    
    print(f"项目A业态: {types_a}")
    print(f"项目B业态: {types_b}")
    
    matches = match_types(types_a, types_b)
    
    print(f"\n业态匹配结果:")
    for a, b in matches:
        print(f"  {a} <-> {b}")
    
    return matches