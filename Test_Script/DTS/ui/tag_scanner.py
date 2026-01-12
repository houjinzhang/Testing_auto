import os
import ast

def scan_pytest_markers(root_dir):
    markers = set()

    for base, _, files in os.walk(root_dir):
        for f in files:
            if not f.endswith(".py"):
                continue

            file_path = os.path.join(base, f)

            try:
                with open(file_path, "r", encoding="utf-8") as fp:
                    tree = ast.parse(fp.read(), filename=f)
            except:
                continue

            # 遍历所有装饰器
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
                    if node.decorator_list:
                        for dec in node.decorator_list:
                            # 查找 pytest.mark.xxx
                            if isinstance(dec, ast.Attribute) and isinstance(dec.value, ast.Attribute):
                                if dec.value.attr == "mark":
                                    markers.add(dec.attr)

                            # pytest.mark.xxx() 带括号形式
                            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                                if isinstance(dec.func.value, ast.Attribute):
                                    if dec.func.value.attr == "mark":
                                        markers.add(dec.func.attr)

    return sorted(list(markers))
