"""Flatten arbitrary JSON API responses into flat tabular rows.

Design rules (documented, deterministic):
- A row is a flat dict whose values are scalars (str/int/float/None).
  Nested objects/arrays that cannot become columns are JSON-encoded into a
  single cell so nothing is ever lost.
- Lists produce one row per element.
- Dicts whose values are all scalars produce ONE row, UNLESS the dict looks
  like a name->value map (e.g. allMids: {BTC: "65000.0", ...}) in which case
  each entry becomes a row with columns `key` and `value`.
- Dicts containing list-of-object fields are expanded: each list element
  becomes a row merged with the parent's scalar fields.
- Multiple same-index list fields are merged index-wise (metaAndAssetCtxs
  has `universe` + `assetCtxs` -> one combined row per coin).
- A `levels` field shaped as list-of-lists-of-objects (l2Book) is expanded
  into rows with a `side` column ("bids"/"asks").
- List-of-list responses (raw candles) get generic columns c0..cN.

`shape` values (per call config):
  auto  - smart extraction described above (default)
  rows  - top-level elements are rows; inner lists stay JSON cells
  raw   - a single row with the whole response in a `_raw` column
"""

import json


def json_cell(v):
    """Serialize a nested value into a storage-safe scalar."""
    if v is None or isinstance(v, (str, int, float)):
        return v
    if isinstance(v, bool):
        return 1 if v else 0
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def rows_from_response(data, shape="auto"):
    if shape == "raw":
        return [{"_raw": json.dumps(data, ensure_ascii=False)}]
    if shape == "rows":
        if isinstance(data, list):
            return [_flat(el) for el in data]
        return [_flat(data)]
    return _auto(data)


def _flat(value):
    if isinstance(value, dict):
        return {k: json_cell(v) for k, v in value.items()}
    return {"value": json_cell(value)}


def _auto(data):
    if isinstance(data, list):
        if not data:
            return []
        if any(isinstance(x, dict) for x in data) and any(isinstance(x, list) for x in data):
            # mixed payload (metaAndAssetCtxs / spotMetaAndAssetCtxs):
            # [{universe, ...}, assetCtxs, ...] -> merge dict list fields with
            # sibling lists index-wise into combined rows.
            merged = {}
            for x in data:
                if isinstance(x, dict):
                    merged.update(x)
                elif isinstance(x, list):
                    merged[f"__list{len(merged)}"] = x
            return _dict_rows(merged)
        first = data[0]
        if isinstance(first, dict):
            out = []
            for el in data:
                out.extend(_dict_rows(el))
            return out
        if isinstance(first, list):
            return [{f"c{i}": json_cell(v) for i, v in enumerate(el)} for el in data]
        return [{"value": json_cell(v)} for v in data]
    if isinstance(data, dict):
        return _dict_rows(data)
    return [{"value": json_cell(data)}]


def _dict_rows(d):
    scalars = {}
    expand_lists = {}
    cell_lists = {}
    dicts = {}
    for k, v in d.items():
        if isinstance(v, list):
            if v and isinstance(v[0], dict):
                expand_lists[k] = v
            elif k == "levels" and v and isinstance(v[0], list) and all(
                all(isinstance(x, dict) for x in el) for el in v
            ):
                expand_lists[k] = v
            else:
                cell_lists[k] = v
        elif isinstance(v, dict):
            dicts[k] = v
        else:
            scalars[k] = v

    if not expand_lists and not dicts:
        if len(d) > 20 and all(not isinstance(v, (list, dict)) for v in d.values()):
            return [{"key": k, "value": json_cell(v)} for k, v in d.items()]
        return [scalars]

    if not expand_lists:
        row = dict(scalars)
        row.update({k: json_cell(v) for k, v in dicts.items()})
        row.update({k: json_cell(v) for k, v in cell_lists.items()})
        return [row]

    if len(expand_lists) == 1 and "levels" in expand_lists:
        rows = []
        for idx, level_list in enumerate(expand_lists["levels"]):
            side = "asks" if idx == 1 else "bids" if idx == 0 else str(idx)
            for lv in level_list:
                rows.append({**scalars, "side": side, **{k: json_cell(v) for k, v in lv.items()}})
        return rows

    driver = max(expand_lists.values(), key=len)
    n = len(driver)
    rows = []
    for i in range(n):
        row = dict(scalars)
        for k, arr in expand_lists.items():
            if i < len(arr):
                el = arr[i]
                if isinstance(el, dict):
                    row.update({kk: json_cell(vv) for kk, vv in el.items()})
                elif isinstance(el, list):
                    row.update({f"c{j}": json_cell(v) for j, v in enumerate(el)})
                else:
                    row[k] = json_cell(el)
        row.update({k: json_cell(v) for k, v in dicts.items()})
        row.update({k: json_cell(v) for k, v in cell_lists.items()})
        rows.append(row)
    return rows
