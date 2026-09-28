"""Annotation moved from share-deapi; Wang extractor behavior is unchanged.

The first four helpers are vendored from cs-wangchong/LLM-Deprecated-API,
llm_dep/utils/source_utils.py @ ffa88d5f960769d20741f8108681c96a2e79f5c8.
Gold labels are used only by ``label``, never by the generation-time checker.
"""

import re


def extract_first_func(code):
    lines = code.split("\n")
    while len(lines) > 0 and not lines[0].lstrip().startswith("def "):
        lines.pop(0)
    if len(lines) == 0:
        return code
    indent = len(re.search(r"^\s*", lines[0]).group(0))
    func = "\n".join(lines)
    func = re.split(r"\n {0,%d}[^\s#]" % indent, func, flags=re.M | re.S)[0]  # noqa: UP031
    return func


def clean_pred(pred):
    lines = [line for line in pred.split("\n") if not line.strip().startswith("#")]
    return "\n".join(lines)


def extract_first_statement(pred, remove_space=True):
    def unclosed(_stmt):
        if len(_stmt) == 0:
            return True
        if _stmt.count("(") > _stmt.count(")"):
            return True
        if _stmt.count("[") > _stmt.count("]"):
            return True
        if _stmt.count("{") > _stmt.count("}"):
            return True
        if _stmt.rstrip().endswith("\\"):
            return True
        return False

    def normalize(_line):
        _line = _line.split("#")[0]
        _line = _line.strip().rstrip(" \\")
        _line = re.sub(r"\s+", " ", _line)
        if remove_space:
            _line = re.sub(r"\s+", "", _line)
        return _line

    lines = pred.split("\n")
    stmt = normalize(lines.pop(0))
    while unclosed(stmt) and len(lines) > 0:
        stmt += normalize(lines.pop(0))
    return stmt


def extract_apis_in_first_stmt(pred, ref_dict, alias_dict):
    stmt = extract_first_statement(pred, False)
    pkg_as = {}
    for alias, name in alias_dict.items():
        alias_parts, name_parts = alias.split("."), name.split(".")
        while len(alias_parts) > 0 and len(name_parts) > 0 and alias_parts[-1] == name_parts[-1]:
            alias_parts.pop()
            name_parts.pop()
        pkg_alias, pkg_name = ".".join(alias_parts), ".".join(name_parts)
        if pkg_alias != pkg_name:
            pkg_as[pkg_alias] = pkg_name

    apis = set()
    for mobj in re.finditer(r"([\w\.]+)\s*\(", stmt):
        api = mobj.group(1).strip()
        if api == "":
            continue
        parts = api.split(".")
        if len(parts) == 2 and parts[0] in ref_dict:
            api = f"{ref_dict[parts[0]]}.{parts[1]}"
        if api in alias_dict:
            api = alias_dict[api]
        else:
            for pkg_alias, pkg_name in pkg_as.items():
                if api.startswith(f"{pkg_alias}."):
                    api = api.replace(f"{pkg_alias}.", f"{pkg_name}.")
                    break
        apis.add(api)
    return list(apis)


_FENCE = re.compile(r"^\s*```[a-zA-Z]*[ \t]*\n?|\n?[ \t]*```\s*$")
_BLOCK = re.compile(r"```[a-zA-Z]*[ \t]*\n(.*?)```", re.S)


def strip_fences(text):
    """Extract the first fenced block, otherwise strip start/end fences."""
    m = _BLOCK.search(text)
    return (m.group(1) if m else _FENCE.sub("", text)).strip("\n")


CHAT_INSTRUCTION = "complete and output the next line for the following python function:\n\n{code}"


def postprocess(sample, text, mode):
    if mode == "raw":
        pred = clean_pred(text)
        pi = sample["probing input"]
        pred = extract_first_func(pi + pred)[len(pi) :]
    else:
        pred = strip_fences(text)
    apis = extract_apis_in_first_stmt(pred, sample["reference dict"], sample["alias dict"])
    return pred, apis


def label(sample, apis):
    found = set(apis)
    if set(sample["deprecated api"]) & found:
        return "DepC"
    if sample["replacement api"] in found:
        return "RepC"
    return "Others"
