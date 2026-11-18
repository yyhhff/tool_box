"""<工具名> - 一句话描述工具功能"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="<工具名>：一句话描述")
    parser.add_argument("input", help="输入说明（路径/内容）")
    parser.add_argument("-o", "--output", help="输出路径，默认写到 data/output/")
    args = parser.parse_args()

    # TODO: 实现工具逻辑
    print(f"input={args.input}, output={args.output}")


if __name__ == "__main__":
    main()
