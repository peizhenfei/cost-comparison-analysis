import os
import sys
import argparse
from data_parser import load_project
from type_matcher import get_matched_types
from cost_comparator import compare_summary, compare_fixed_costs, compare_elastic_costs
from output_generator import generate_output


def main():
    """主入口函数"""

    parser = argparse.ArgumentParser(description="房地产项目成本对比分析系统")
    parser.add_argument("project_a", nargs="?", help="项目A文件路径")
    parser.add_argument("project_b", nargs="?", help="项目B文件路径")
    parser.add_argument("-o", "--output", default="成本对比分析报告.xlsx", help="输出文件名")
    parser.add_argument("--list", action="store_true", help="列出示例文件")

    args = parser.parse_args()

    if args.list:
        print("示例文件:")
        for f in os.listdir("."):
            if f.endswith(".xlsx") and not f.startswith("~"):
                print(f"  - {f}")
        return

    # 如果没有提供文件，显示帮助
    if not args.project_a or not args.project_b:
        print("=" * 60)
        print("房地产项目成本对比分析系统")
        print("=" * 60)
        print("\n用法:")
        print("  python main.py <项目A文件> <项目B文件> [-o 输出文件]")
        print("  python main.py --list  # 列出当前目录下的Excel文件")
        print("\n示例:")
        print('  python main.py "项目A.xlsx" "项目B.xlsx" -o "对比报告.xlsx"')
        print("\n当前目录下的Excel文件:")
        for f in os.listdir("."):
            if f.endswith(".xlsx") and not f.startswith("~"):
                print(f"  - {f}")
        return

    project_a_file = args.project_a
    project_b_file = args.project_b
    output_file = args.output

    if not os.path.exists(project_a_file):
        print(f"错误: 项目A文件不存在: {project_a_file}")
        return

    if not os.path.exists(project_b_file):
        print(f"错误: 项目B文件不存在: {project_b_file}")
        return

    print("=" * 60)
    print("房地产项目成本对比分析系统")
    print("=" * 60)

    # 1. 加载项目数据
    print("\n[1/5] 正在加载项目数据...")
    try:
        project_a = load_project(project_a_file)
        print(f"  ✓ 项目A加载成功: {project_a['成本控制']['项目信息'].get('名称', '未知')}")
        print(f"    总建筑面积: {project_a['成本控制']['项目信息'].get('总建筑面积', 0):,.2f} ㎡")
        print(f"    可售面积: {project_a['成本控制']['项目信息'].get('可售面积', 0):,.2f} ㎡")
    except Exception as e:
        print(f"  ✗ 项目A加载失败: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        project_b = load_project(project_b_file)
        print(f"  ✓ 项目B加载成功: {project_b['成本控制']['项目信息'].get('名称', '未知')}")
        print(f"    总建筑面积: {project_b['成本控制']['项目信息'].get('总建筑面积', 0):,.2f} ㎡")
        print(f"    可售面积: {project_b['成本控制']['项目信息'].get('可售面积', 0):,.2f} ㎡")
    except Exception as e:
        print(f"  ✗ 项目B加载失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 业态匹配
    print("\n[2/5] 正在匹配业态...")
    type_matches = get_matched_types(project_a, project_b)

    # 3. 成本对比计算
    print("\n[3/5] 正在计算成本对比...")
    summary_data = compare_summary(project_a, project_b, type_matches)
    print(f"  ✓ 汇总对比计算完成")

    fixed_data = compare_fixed_costs(project_a, project_b, type_matches)
    print(f"  ✓ 固定成本差异分析完成 - 业态数量: {len(fixed_data['业态分析'])}")

    elastic_data = compare_elastic_costs(project_a, project_b, type_matches)
    print(f"  ✓ 弹性成本差异分析完成 - 业态数量: {len(elastic_data['业态分析'])}")

    # 4. 生成输出文件
    print("\n[4/5] 正在生成Excel报告...")
    try:
        generate_output(summary_data, fixed_data, elastic_data, output_file)
        abs_output = os.path.abspath(output_file)
        print(f"  ✓ 报告生成成功")
        print(f"\n输出文件: {abs_output}")
    except Exception as e:
        print(f"  ✗ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. 完成
    print("\n[5/5] 分析完成!")
    print("\n报告包含以下Sheet:")
    print("  1. 成本对比总表 - 项目整体成本对比")
    print("  2. 固定单方差异明细分析 - 固定成本科目差异分解")
    print("  3. 弹性单方差异明细分析 - 弹性成本科目差异分解")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
