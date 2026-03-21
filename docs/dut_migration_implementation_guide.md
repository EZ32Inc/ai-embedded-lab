# DUT 标准化迁移 — 实施执行指南

**状态：** 待执行
**日期：** 2026-03-21
**目标仓库：** `/nvme1t/work/codex/ai-embedded-lab`
**配套文档：**
- `docs/dut_standardization_spec_v0_1.md` — 规格说明
- `docs/dut_standardization_migration_plan_v0_1.md` — 迁移总体计划

---

## 0. 背景与约束

### 当前代码库现状（已确认）

| 文件 | 问题 |
|------|------|
| `ael/assets.py:8` | `_REQUIRED_FIELDS` 包含 `"mcu"`（平铺字段），不支持多处理器 |
| `ael/assets.py:116-124` | `find_golden_reference()` 用 `manifest.get("mcu")` 查找，MCU 中心 |
| `ael/inventory.py:281` | `manifest.get("mcu") or board_cfg.get("target")` raw dict 访问 |
| `ael/inventory.py:534-546` | `mcus_with_tests` 汇总全部基于 `"mcu"` 字段 |
| `ael/strategy_resolver.py` | 全文 `board_cfg: Dict[str, Any]`，27+ 处 `.get()` raw 访问 |
| `ael/pipeline.py:383` | `board_cfg.get("target")` / `board_cfg.get("name")` raw dict |
| `ael/default_verification.py` | `board_raw.get("board", {})` raw dict 访问 |
| `configs/boards/*.yaml` (5个) | 只有 `target: esp32c3`，无 `processors:[]` 结构 |
| `ael/dut/` | **目录不存在** |

### 核心设计原则

1. **适配器优先，不搞大爆炸重写** — 参照 `ael/instruments/interfaces/` 的迁移模式
2. **向后兼容** — `DUTConfig.mcu` 保留 property 兼容，`to_legacy_dict()` 让下游调用无感知
3. **分步验证** — 每个 Step 独立可测，不破坏现有 board 验证流程
4. **strategy_resolver.py / pipeline.py 最后动** — 靠 compat shim 屏蔽，降低风险

---

## 1. 整体路线图（3 个 Step）

```
Step 1: 建模型层（纯新增，不改任何现有文件）
  └── ael/dut/ 模块：model.py + loader.py + registry.py

Step 2: 接入核心入口（改动集中在 inventory.py）
  └── inventory.py 使用 DUT loader，加 to_legacy_dict() 适配器

Step 3: 更新数据 + 清理旧字段
  └── configs/boards/*.yaml 加 processors[]
  └── assets.py _REQUIRED_FIELDS 更新
  └── find_golden_reference() 更新查询逻辑
```

---

## 2. Step 1 — 创建 `ael/dut/` 模型层

> **风险：低** — 纯新增代码，不修改任何现有文件，不破坏任何现有调用。

### 2.1 创建 `ael/dut/__init__.py`

```python
"""
DUT (Device Under Test) model layer.

Provides DUTConfig — a structured, board-first representation of a DUT,
replacing direct raw-dict access to board YAML configs.
"""

from ael.dut.model import DUTConfig, ProcessorConfig
from ael.dut.loader import load_dut
from ael.dut.registry import load_dut_from_file

__all__ = ["DUTConfig", "ProcessorConfig", "load_dut", "load_dut_from_file"]
```

### 2.2 创建 `ael/dut/model.py`

```python
"""
DUT data model.

DUTConfig is the canonical representation of a Device Under Test.
It replaces direct dict access to board YAML configs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProcessorConfig:
    """Single processor on a DUT board."""
    id: str                          # e.g. "esp32c3", "rp2040"
    arch: str                        # e.g. "riscv", "xtensa", "arm"
    role: str = "primary"            # "primary" | "secondary"
    clock_hz: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "arch": self.arch, "role": self.role}
        if self.clock_hz is not None:
            d["clock_hz"] = self.clock_hz
        d.update(self.extra)
        return d


@dataclass
class DUTConfig:
    """
    Board-first DUT configuration.

    Replaces the raw board_cfg dict throughout the codebase.
    Provides backward-compatible .mcu property and .to_legacy_dict() method
    so existing callers can be migrated incrementally.
    """
    board_id: str
    name: str
    processors: List[ProcessorConfig]
    build: Dict[str, Any] = field(default_factory=dict)
    flash: Dict[str, Any] = field(default_factory=dict)
    observe_map: Dict[str, Any] = field(default_factory=dict)
    observe: Dict[str, Any] = field(default_factory=dict)
    pins: Dict[str, Any] = field(default_factory=dict)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    instrument: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    # ── Backward-compat accessors ──────────────────────────────────────────

    @property
    def primary_processor(self) -> ProcessorConfig:
        """Return the primary processor, or first processor if none marked."""
        for p in self.processors:
            if p.role == "primary":
                return p
        if self.processors:
            return self.processors[0]
        raise ValueError(f"DUT {self.board_id!r} has no processors defined")

    @property
    def mcu(self) -> str:
        """
        Backward-compat: return primary processor id.
        Replaces manifest.get('mcu') and board_cfg.get('target') call sites.
        """
        return self.primary_processor.id

    @property
    def target(self) -> str:
        """Alias of mcu for build/flash toolchain compat."""
        return self.mcu

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Serialize back to the flat board_cfg dict shape that
        strategy_resolver.py, pipeline.py, and default_verification.py
        currently expect.

        This shim lets those files remain unchanged during Step 2 migration.
        Once all callers are updated, this method can be removed.
        """
        d: Dict[str, Any] = {
            "name": self.name,
            "target": self.mcu,
        }
        if self.build:
            d["build"] = dict(self.build)
        if self.flash:
            d["flash"] = dict(self.flash)
        if self.observe_map:
            d["observe_map"] = dict(self.observe_map)
        if self.observe:
            d["observe"] = dict(self.observe)
        if self.pins:
            d["pins"] = dict(self.pins)
        if self.capabilities:
            d["capabilities"] = dict(self.capabilities)
        if self.instrument:
            d["instrument"] = dict(self.instrument)
        d.update(self.extra)
        return d
```

### 2.3 创建 `ael/dut/loader.py`

```python
"""
DUT loader: converts a raw board YAML dict into a DUTConfig.

Supports both the legacy format (flat `target:` field) and the new format
(structured `processors:[]` list). The compat path auto-promotes legacy
configs so callers never need to handle both shapes.
"""

from __future__ import annotations

from typing import Any, Dict

from ael.dut.model import DUTConfig, ProcessorConfig

# Mapping from known target IDs to CPU architecture.
# Extend as new board targets are added.
_TARGET_ARCH_MAP: Dict[str, str] = {
    "esp32c3": "riscv",
    "esp32c6": "riscv",
    "esp32s3": "xtensa",
    "esp32":   "xtensa",
    "rp2040":  "arm",
    "rp2350":  "arm",
}


def _infer_arch(target: str) -> str:
    return _TARGET_ARCH_MAP.get(target, "unknown")


def load_dut(board_id: str, raw: Dict[str, Any]) -> DUTConfig:
    """
    Parse a raw board YAML dict (the value under the top-level `board:` key)
    into a DUTConfig.

    Supports two input shapes:

    Legacy (existing boards):
        target: esp32c3
        name: ESP32-C3 DevKit

    New (after Step 3 YAML update):
        target: esp32c3   # kept for toolchain compat
        processors:
          - id: esp32c3
            arch: riscv
            role: primary
            clock_hz: 160000000
    """
    if not isinstance(raw, dict):
        raw = {}

    name = str(raw.get("name") or board_id)

    # Parse processors — new format takes priority
    raw_procs = raw.get("processors")
    if isinstance(raw_procs, list) and raw_procs:
        processors = []
        for i, p in enumerate(raw_procs):
            if not isinstance(p, dict):
                continue
            proc_id = str(p.get("id") or p.get("target") or "unknown")
            arch = str(p.get("arch") or _infer_arch(proc_id))
            role = str(p.get("role") or ("primary" if i == 0 else "secondary"))
            clock_hz = p.get("clock_hz")
            extra = {k: v for k, v in p.items()
                     if k not in ("id", "target", "arch", "role", "clock_hz")}
            processors.append(ProcessorConfig(
                id=proc_id, arch=arch, role=role,
                clock_hz=int(clock_hz) if clock_hz is not None else None,
                extra=extra,
            ))
    else:
        # Legacy: promote flat `target:` to a single-processor list
        target = str(raw.get("target") or board_id)
        arch = _infer_arch(target)
        clock_hz = raw.get("clock_hz")
        processors = [ProcessorConfig(
            id=target, arch=arch, role="primary",
            clock_hz=int(clock_hz) if clock_hz is not None else None,
        )]

    known_keys = {
        "name", "target", "processors", "build", "flash",
        "observe_map", "observe", "pins", "capabilities",
        "instrument", "clock_hz",
    }
    extra = {k: v for k, v in raw.items() if k not in known_keys}

    return DUTConfig(
        board_id=board_id,
        name=name,
        processors=processors,
        build=dict(raw.get("build") or {}),
        flash=dict(raw.get("flash") or {}),
        observe_map=dict(raw.get("observe_map") or {}),
        observe=dict(raw.get("observe") or {}),
        pins=dict(raw.get("pins") or {}),
        capabilities=dict(raw.get("capabilities") or {}),
        instrument=dict(raw.get("instrument") or {}),
        extra=extra,
    )
```

### 2.4 创建 `ael/dut/registry.py`

```python
"""
DUT registry: loads a DUTConfig from the configs/boards/ directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ael.dut.loader import load_dut
from ael.dut.model import DUTConfig


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback minimal YAML parser (mirrors pipeline.py _simple_yaml_load)
        data: Dict[str, Any] = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip() or line.strip().startswith("#"):
                    continue
                key, _, value = line.strip().partition(":")
                if value.strip():
                    data[key.strip()] = value.strip().strip('"')
        return data


def load_dut_from_file(repo_root: Path, board_id: str) -> DUTConfig:
    """
    Load a DUTConfig from configs/boards/{board_id}.yaml.

    Args:
        repo_root: Repository root directory.
        board_id:  Board identifier, e.g. "esp32c3_devkit".

    Returns:
        DUTConfig parsed from the board YAML file.

    Raises:
        FileNotFoundError: If the board config file does not exist.
    """
    board_path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    if not board_path.exists():
        raise FileNotFoundError(
            f"Board config not found: {board_path}. "
            f"Expected at configs/boards/{board_id}.yaml"
        )
    raw_top = _load_yaml(board_path)
    # Board configs have a top-level `board:` key
    raw_board = raw_top.get("board") if isinstance(raw_top, dict) else raw_top
    if not isinstance(raw_board, dict):
        raw_board = {}
    return load_dut(board_id, raw_board)
```

### 2.5 Step 1 验证

创建完上述 4 个文件后，在仓库根目录运行：

```bash
cd /nvme1t/work/codex/ai-embedded-lab

python -c "
from ael.dut import load_dut_from_file
from pathlib import Path

root = Path('.')
for board_id in ['esp32c3_devkit', 'esp32c6_devkit', 'esp32s3_devkit', 'rp2040_pico', 'rp2350_pico2']:
    dut = load_dut_from_file(root, board_id)
    print(f'{dut.board_id}: mcu={dut.mcu}, processors={[p.id for p in dut.processors]}')
    print(f'  legacy_dict target={dut.to_legacy_dict()[\"target\"]}')
"
```

**预期输出：**
```
esp32c3_devkit: mcu=esp32c3, processors=['esp32c3']
  legacy_dict target=esp32c3
esp32c6_devkit: mcu=esp32c6, processors=['esp32c6']
  legacy_dict target=esp32c6
...
```

---

## 3. Step 2 — 接入 `inventory.py`（核心改动）

> **风险：中** — 改动集中，有 `to_legacy_dict()` 保护下游，测试前后对比是关键。

### 3.1 修改 `ael/inventory.py`

**改动点 1：** 在文件顶部 import 区增加：

```python
from ael.dut.registry import load_dut_from_file
from ael.dut.model import DUTConfig
```

**改动点 2：** 修改 `_load_board_cfg()` 函数（当前约 line 90）：

```python
# 修改前
def _load_board_cfg(repo_root: Path, board_id: str) -> Dict[str, Any]:
    board_path = repo_root / "configs" / "boards" / f"{board_id}.yaml"
    raw = _simple_yaml_load(board_path)
    return raw.get("board", {}) if isinstance(raw, dict) else {}

# 修改后
def _load_board_cfg(repo_root: Path, board_id: str) -> DUTConfig:
    """Load board config. Returns DUTConfig (was: raw dict)."""
    return load_dut_from_file(repo_root, board_id)
```

**改动点 3：** 在所有使用 `board_cfg` 传入下游（`strategy_resolver`、`pipeline` 等）的地方，
调用 `.to_legacy_dict()`。搜索方式：

```bash
grep -n "board_cfg" ael/inventory.py
```

凡是把 `board_cfg` 传给 `strategy_resolver.*` 或 `pipeline.*` 的调用，改为：

```python
# 修改前
strategy_resolver.normalize_probe_cfg(board_raw, board_cfg, ...)

# 修改后
strategy_resolver.normalize_probe_cfg(board_raw, board_cfg.to_legacy_dict(), ...)
```

**改动点 4：** 修改 `_selected_dut_payload()`（当前 line ~274）：

```python
# 修改前（约 line 281）
"mcu": manifest.get("mcu") or board_cfg.get("target"),

# 修改后（board_cfg 现在是 DUTConfig）
"mcu": manifest.get("mcu") or board_cfg.mcu,
```

**改动点 5：** 修改 `mcus_with_tests` 汇总（当前 line ~534-546）：

```python
# 修改前
"mcu": manifest.get("mcu"),
...
mcus_with_tests = sorted({str(item.get("mcu")) for item in dut_entries ...})

# 修改后 — board_cfg 现在是 DUTConfig，manifest 里的 mcu 可继续用
# 这里实际上只要 manifest dict 没变，改动最小
# 确认 manifest 仍是 dict 而非 DUTConfig，如是则不需要改这里
```

### 3.2 Step 2 验证

```bash
# 1. 跑现有 inventory 相关测试（如果有）
cd /nvme1t/work/codex/ai-embedded-lab
python -m pytest tests/ -k "inventory" -v 2>/dev/null || echo "no tests found"

# 2. 手工冒烟测试：列出所有 DUT
python -c "
import sys; sys.path.insert(0, '.')
from ael.inventory import list_duts
from pathlib import Path
result = list_duts(Path('.'))
print(result)
"

# 3. 确认 strategy_resolver 调用不崩溃
python -c "
from ael.dut import load_dut_from_file
from pathlib import Path
dut = load_dut_from_file(Path('.'), 'esp32c3_devkit')
d = dut.to_legacy_dict()
assert d['target'] == 'esp32c3', f'expected esp32c3, got {d[\"target\"]}'
print('to_legacy_dict() OK:', d['target'])
"
```

---

## 4. Step 3 — 更新 YAML + 清理旧字段

> **风险：低** — YAML 新增字段，loader compat 路径保证老格式继续工作。

### 4.1 更新 5 个 board YAML 文件

为每个 `configs/boards/*.yaml` 新增 `processors:` 字段。保留 `target:` 不删（toolchain 仍依赖它）。

**示例：`configs/boards/esp32c3_devkit.yaml`**

```yaml
board:
  name: ESP32-C3 DevKit
  target: esp32c3          # 保留，build/flash toolchain 使用
  processors:              # 新增
    - id: esp32c3
      arch: riscv
      role: primary
      clock_hz: 160000000
  build:
    ...（其余字段不变）
```

**5 个文件的 arch 对照表：**

| 文件 | target | arch |
|------|--------|------|
| `esp32c3_devkit.yaml` | esp32c3 | riscv |
| `esp32c6_devkit.yaml` | esp32c6 | riscv |
| `esp32s3_devkit.yaml` | esp32s3 | xtensa |
| `rp2040_pico.yaml` | rp2040 | arm |
| `rp2350_pico2.yaml` | rp2350 | arm |

### 4.2 更新 `ael/assets.py`

**改动点 1：** `_REQUIRED_FIELDS`（line ~6-10）

```python
# 修改前
_REQUIRED_FIELDS = [
    "board_id",
    "mcu",
    ...
]

# 修改后 — mcu 改为 processors（或两者都接受）
_REQUIRED_FIELDS = [
    "board_id",
    "processors",
    ...
]

# 如果要平滑迁移，可加兼容检查：
def _validate_fields(manifest: dict) -> list[str]:
    errors = []
    for f in _REQUIRED_FIELDS:
        if f == "processors":
            # Accept either processors[] (new) or mcu (legacy)
            if not manifest.get("processors") and not manifest.get("mcu"):
                errors.append("processors (or mcu)")
        elif f not in manifest:
            errors.append(f)
    return errors
```

**改动点 2：** `find_golden_reference()`（line ~115-124）

```python
# 修改前
def find_golden_reference(query):
    mcu = (query or {}).get("mcu")
    ...
    if mcu and manifest.get("mcu") == mcu:
        ...

# 修改后 — 支持 processors[] 查询，兼容 mcu
def find_golden_reference(query):
    mcu = (query or {}).get("mcu")
    processors = (query or {}).get("processors") or []
    target_ids = {p.get("id") or p.get("target") for p in processors if isinstance(p, dict)}
    if mcu:
        target_ids.add(mcu)
    ...
    # 匹配逻辑：检查 manifest 的 processors[].id 或 mcu
    manifest_procs = manifest.get("processors") or []
    manifest_ids = {p.get("id") for p in manifest_procs if isinstance(p, dict)}
    if not manifest_ids:
        manifest_ids = {manifest.get("mcu")}  # legacy compat
    if target_ids & manifest_ids:
        ...  # match
```

### 4.3 Step 3 验证

```bash
cd /nvme1t/work/codex/ai-embedded-lab

# 验证所有 board 的 processors 字段被正确读取
python -c "
from ael.dut import load_dut_from_file
from pathlib import Path
root = Path('.')
boards = ['esp32c3_devkit', 'esp32c6_devkit', 'esp32s3_devkit', 'rp2040_pico', 'rp2350_pico2']
for b in boards:
    dut = load_dut_from_file(root, b)
    p = dut.primary_processor
    print(f'{b}: id={p.id} arch={p.arch} role={p.role} clock_hz={p.clock_hz}')
"

# 预期输出示例：
# esp32c3_devkit: id=esp32c3 arch=riscv role=primary clock_hz=160000000
# rp2040_pico: id=rp2040 arch=arm role=primary clock_hz=None
```

---

## 5. 文件改动汇总

| 操作 | 文件 | Step | 改动量 |
|------|------|------|--------|
| 新建 | `ael/dut/__init__.py` | 1 | ~10 行 |
| 新建 | `ael/dut/model.py` | 1 | ~90 行 |
| 新建 | `ael/dut/loader.py` | 1 | ~80 行 |
| 新建 | `ael/dut/registry.py` | 1 | ~50 行 |
| 修改 | `ael/inventory.py` | 2 | ~20 行 |
| 修改 | `configs/boards/esp32c3_devkit.yaml` | 3 | +5 行 |
| 修改 | `configs/boards/esp32c6_devkit.yaml` | 3 | +5 行 |
| 修改 | `configs/boards/esp32s3_devkit.yaml` | 3 | +5 行 |
| 修改 | `configs/boards/rp2040_pico.yaml` | 3 | +5 行 |
| 修改 | `configs/boards/rp2350_pico2.yaml` | 3 | +5 行 |
| 修改 | `ael/assets.py` | 3 | ~15 行 |
| **不动** | `ael/strategy_resolver.py` | — | 0（靠 compat shim） |
| **不动** | `ael/pipeline.py` | — | 0（靠 compat shim） |
| **不动** | `ael/default_verification.py` | — | 0（Phase 2+ 再说） |

**总计：** 4 个新文件（~230 行）+ 8 个文件修改（~55 行）

---

## 6. 不动的文件 — 原因说明

`strategy_resolver.py`、`pipeline.py`、`default_verification.py` 在本次迁移中**故意不动**。

原因：
- 这三个文件全部接收 `board_cfg: Dict[str, Any]`（raw dict）
- `DUTConfig.to_legacy_dict()` 保证产出的 dict 和现在完全一致
- 等 Step 1-3 稳定、测试通过后，这三个文件可以在后续 Phase 中逐步改为直接接收 `DUTConfig`
- 避免一次改动面过宽导致难以定位问题

---

## 7. 完成标志

以下条件全部满足时，本次迁移完成：

- [ ] `python -c "from ael.dut import load_dut_from_file"` 无报错
- [ ] 5 个 board 的 `load_dut_from_file()` 都能返回正确的 `DUTConfig`
- [ ] `dut.mcu` 和原来 `board_cfg.get("target")` 返回相同值
- [ ] `dut.to_legacy_dict()` 产出的 dict 与修改前 `_load_board_cfg()` 返回的 dict 字段一致
- [ ] `ael/inventory.py` 使用 DUT loader 后，现有 pipeline 正常运行（无崩溃）
- [ ] 5 个 board YAML 都有 `processors:[]` 字段
- [ ] `ael/assets.py` `_REQUIRED_FIELDS` 不再硬编码 `"mcu"` 作为唯一处理器字段

---

## 8. 后续（本次不实施）

完成上述 3 个 Step 后，可继续推进：

1. **`strategy_resolver.py` 原生接受 `DUTConfig`** — 去掉 `to_legacy_dict()` 转换
2. **`pipeline.py` 原生接受 `DUTConfig`** — `_selected_dut_payload()` 直接用 `dut.processors`
3. **`default_verification.py` 接入 DUT registry** — 去掉 `board_raw.get("board", {})` raw 访问
4. **`ael/dut/interfaces/`** — 实现 `DUTProvider` 接口，对齐 `ael/instruments/interfaces/` 模式
5. **manifest YAML 支持 `processors[]`** — 测试 manifest 侧也升级

---

*本文档由 Claude Code 根据代码库实际状态生成。执行前建议先在 git 新分支上操作。*
