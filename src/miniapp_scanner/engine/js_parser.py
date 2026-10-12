"""统一的 JS 解析入口 + 常量折叠 + 缓存。"""
import esprima
from typing import Optional, Dict


# 解析缓存：源字符串 → AST（只读，不会被修改）
_PARSE_CACHE = {}


def parse_js(source: str) -> Optional[Dict]:
    # 命中缓存直接返回
    if source in _PARSE_CACHE:
        cached = _PARSE_CACHE[source]
        return cached if cached is None else _copy_tree(cached)

    try:
        tree = esprima.parseScript(source, {"loc": True, "tolerant": True})
        if hasattr(tree, "toDict"):
            tree = tree.toDict()
    except Exception:
        _PARSE_CACHE[source] = None
        return None
    if not isinstance(tree, dict):
        _PARSE_CACHE[source] = None
        return None
    tree = fold_constants(tree)

    # 缓存（限制大小，避免内存爆炸）
    if len(_PARSE_CACHE) < 200:
        _PARSE_CACHE[source] = tree
    return _copy_tree(tree)


def _copy_tree(tree):
    """深拷贝 AST（防止下游修改污染缓存）"""
    import copy
    return copy.deepcopy(tree)


def fold_constants(node):
    """递归折叠：字符串拼接、模板字面量、计算成员访问"""
    if isinstance(node, list):
        return [fold_constants(n) for n in node]
    if not isinstance(node, dict):
        return node

    for k, v in list(node.items()):
        node[k] = fold_constants(v)

    t = node.get("type")

    if t == "BinaryExpression" and node.get("operator") == "+":
        l, r = node.get("left"), node.get("right")
        if (l and l.get("type") == "Literal" and isinstance(l.get("value"), str)
                and r and r.get("type") == "Literal" and isinstance(r.get("value"), str)):
            return {
                "type": "Literal",
                "value": l["value"] + r["value"],
                "loc": node.get("loc"),
                "_folded": True,
            }

    if t == "TemplateLiteral" and not node.get("expressions"):
        text = "".join(q.get("value", {}).get("cooked", "")
                       for q in node.get("quasis", []))
        return {
            "type": "Literal", "value": text,
            "loc": node.get("loc"), "_folded": True,
        }

    if t == "MemberExpression" and node.get("computed"):
        prop = node.get("property")
        if prop and prop.get("type") == "Literal" and isinstance(prop.get("value"), str):
            node["computed"] = False
            node["property"] = {"type": "Identifier", "name": prop["value"],
                                "loc": prop.get("loc")}
            node["_folded"] = True

    return node