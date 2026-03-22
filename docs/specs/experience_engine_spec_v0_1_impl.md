# Experience Engine v0.1 Spec — Implementation-Ready

**Status:** Draft
**Date:** 2026-03-22
**Source:** Extracted from AEL design discussion with ChatGPT

---

## 0. 核心定义（必须统一认知）

> Experience Engine v0.1 = 一个独立基础组件，用于接收、处理、存储、检索和进化 Experience Unit，并为上层系统提供经验能力。

**非目标（必须明确）：**
- 不做 UI
- 不做 agent
- 不做业务逻辑（AEL / KnowThyself）

**只做：**
> Experience Lifecycle Management

---

## 1. Repo 结构（直接可用）

```
experience_engine/
├── core/
│   ├── models.py          # Experience Unit 定义
│   ├── schema.py          # schema_version 管理
│
├── ingestion/
│   ├── ingest.py          # 输入入口
│
├── processing/
│   ├── pipeline.py        # normalize → summarize → tag
│   ├── summarizer.py
│   ├── classifier.py
│
├── storage/
│   ├── store.py           # 存储接口
│   ├── memory.json        # V0.1 简单存储
│
├── retrieval/
│   ├── retrieve.py        # 查询接口
│
├── feedback/
│   ├── feedback.py        # 反馈处理
│
├── utils/
│   ├── id.py
│   ├── time.py
│
├── api.py                 # 上层统一调用接口
└── README.md
```

**V0.1 原则：不要复杂化，先跑通闭环。**

---

## 2. 核心数据结构（Experience Unit）

**`core/models.py`**

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time
import uuid


def generate_id():
    return str(uuid.uuid4())


@dataclass
class Experience:
    id: str = field(default_factory=generate_id)
    schema_version: str = "v1"

    # domain
    domain: str = "general"  # engineering | self
    type: str = ""

    # intent
    intent: Optional[str] = None

    # content
    raw: str = ""
    summary: Optional[str] = None

    # structure
    context: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

    # action/result
    actions: List[str] = field(default_factory=list)
    outcome: Optional[str] = None  # success | failed | partial
    confidence: float = 0.5

    # relations
    related_experience: List[str] = field(default_factory=list)
    derived_from: List[str] = field(default_factory=list)

    # metadata
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None

    # feedback
    feedback: Optional[str] = None
```

**重点：有 intent ✔、有 outcome ✔、有 confidence ✔、有 schema_version ✔**

---

## 3. Ingestion（输入）

**`ingestion/ingest.py`**

```python
from core.models import Experience
from processing.pipeline import process_experience
from storage.store import save_experience


def ingest(raw_input: str, domain="general", intent=None, source=None):
    exp = Experience(
        raw=raw_input,
        domain=domain,
        intent=intent,
        source=source
    )

    exp = process_experience(exp)
    save_experience(exp)

    return exp
```

**上层调用方式（AEL / KnowThyself）：**

```python
ingest(
    raw_input="ADC error: adc1_config_width not found",
    domain="engineering",
    intent="migrate IDF5.2 to 6.0"
)
```

---

## 4. Processing Pipeline

**`processing/pipeline.py`**

```python
from processing.summarizer import summarize
from processing.classifier import classify


def process_experience(exp):
    exp.summary = summarize(exp.raw)
    exp.tags = classify(exp.raw)

    return exp
```

**`processing/summarizer.py`**

```python
def summarize(text):
    return text[:100]  # V0.1：先简单
```

**`processing/classifier.py`**

```python
def classify(text):
    tags = []

    if "error" in text.lower():
        tags.append("error")

    if "fix" in text.lower():
        tags.append("fix")

    return tags
```

*V0.1 不追求 AI 完美分类，先跑通流程。*

---

## 5. Storage（存储）

**`storage/store.py`**

```python
import json
from core.models import Experience


DB_FILE = "storage/memory.json"


def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_experience(exp: Experience):
    db = load_db()
    db.append(exp.__dict__)
    save_db(db)
```

*V0.1：用 JSON，先简单。*

---

## 6. Retrieval（检索）

**`retrieval/retrieve.py`**

```python
from storage.store import load_db


def search(keyword=None, domain=None):
    db = load_db()

    results = []

    for item in db:
        if domain and item["domain"] != domain:
            continue

        if keyword and keyword not in item["raw"]:
            continue

        results.append(item)

    return results
```

*V0.1：keyword search ✔、domain filter ✔。后面再升级 vector / semantic。*

---

## 7. Feedback（反馈）

**`feedback/feedback.py`**

```python
from storage.store import load_db, save_db


def apply_feedback(exp_id, feedback, outcome=None):
    db = load_db()

    for item in db:
        if item["id"] == exp_id:
            item["feedback"] = feedback

            if outcome:
                item["outcome"] = outcome

            # 简单提升 confidence
            if feedback == "correct":
                item["confidence"] += 0.1

            if feedback == "wrong":
                item["confidence"] -= 0.1

    save_db(db)
```

*这一步非常关键：系统开始"学习"。*

---

## 8. API（统一接口）

**`api.py`**

```python
from ingestion.ingest import ingest
from retrieval.retrieve import search
from feedback.feedback import apply_feedback


class ExperienceAPI:

    @staticmethod
    def add(raw, domain="general", intent=None):
        return ingest(raw, domain, intent)

    @staticmethod
    def query(keyword=None, domain=None):
        return search(keyword, domain)

    @staticmethod
    def feedback(exp_id, feedback, outcome=None):
        return apply_feedback(exp_id, feedback, outcome)
```

---

## 9. 上层接入方式

**AEL 使用：**

```python
ExperienceAPI.add(
    raw="UART failed on STM32F4, conflict with onboard STLink",
    domain="engineering",
    intent="setup UART"
)
```

**KnowThyself 使用：**

```python
ExperienceAPI.add(
    raw="I keep coming back to hardware + AI tools",
    domain="self",
    intent="understand long-term interest"
)
```

---

## 10. V0.1 成功标准

**不是功能多，是闭环成立：**

```
输入 → 存储 → 查询 → 再使用 → 反馈 → 改进
```

**测试方式：**
- Day 1：记录 5 条经验
- Day 2：用 query 找出来
- Day 3：再次任务中复用

如果做到 **第二次更快**，就成功了。

---

## 11. 最重要的设计原则（写在 README）

> We do not store data.
> We accumulate experience.

> Experience must be usable, not just recorded.

> The system improves only if experience is reused.

---

## 12. V0.2 展望

- 语义检索（semantic search）
- 自动经验选择
- scope / decay 机制
- 负面经验标注（`outcome: failed`, `avoid: true`）
- Experience 组合（多条经验合并解决复杂问题）

---

## 13. 最后一句

> Experience Engine is not proven by design —
> it is proven by repeated use.

接下来最重要的事：**跑真实 case**

- IDF migration × 5
- STM32 debug × 5
- Self reflection × 5

然后看：有没有变快？有没有变准？

---

*Extracted from AEL design discussion. Date: 2026-03-22*
*Companion spec: `experience_engine_spec_v0_1_conceptual.md`*
