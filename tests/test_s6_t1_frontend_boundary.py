"""S6-T1 边界收口断言（统一前端冻结口径 + 后端不挂载固化）.

设计依据：《OpenBase-S6-统一前端隔离展示与段门禁收口-设计草案-v1.0.0》§4.1
断言编号：S6-T1-1 ~ S6-T1-4（对应立项方案 §4 同编号验收断言）。

断言口径（沙箱内可执行面）：
- S6-T1-1：统一前端唯一维护面口径 + 3 处改造点登记四元组 + 冻结声明落点清单；
- S6-T1-2：OpenBase 后端不存在对统一前端产物的 StaticFiles/mount/dist-v 挂载；
- S6-T1-3：统一前端侧冻结声明落点存在且口径与登记一致；
- S6-T1-4：口径闭环证据在清点总清单与跨仓提交放行清单留有引用位，且未改既有计数与红线。
"""

from __future__ import annotations

from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ROOT = _REPOSITORY_ROOT / "openbase"

_REGISTRY_DOCUMENT = (
    _REPOSITORY_ROOT
    / "doc"
    / "planning"
    / "OpenBase-S6-统一前端冻结与改造口径登记-v1.0.0.md"
)
_UI_FROZEN_DECLARATION = _REPOSITORY_ROOT / "openbase-ui" / "docs" / "frontend-frozen.md"
_CLEARANCE_CHECKLIST = (
    _REPOSITORY_ROOT
    / "doc"
    / "planning"
    / "OpenBase-联调产物清点核对总清单-v1.0.0.md"
)
_CROSS_REPOSITORY_RELEASE = (
    _REPOSITORY_ROOT
    / "doc"
    / "development"
    / "OpenBase-多系统联调-跨仓提交放行清单-v1.0.0.md"
)

# 「后端不挂载统一前端产物」的禁用标识（设计草案 §4.1 S6-T1-2 ①）
_FORBIDDEN_MOUNT_TOKENS = ("StaticFiles", "mount(", "dist-v")

# 已知非挂载引用白名单：CLI scaffold 的目标目录文案（设计草案 §4.1 S6-T1-2 ②）
_KNOWN_TARGET_DIRECTORY_REFERENCE = "openbase/cli/main.py"


def _read_text(path: Path) -> str:
    """以 UTF-8 读取文本（中文文档路径在 Windows 下不作编码猜测）."""
    return path.read_text(encoding="utf-8")


def _relative_posix(path: Path) -> str:
    """返回相对仓根的 POSIX 风格路径，便于跨平台断言."""
    return path.relative_to(_REPOSITORY_ROOT).as_posix()


def _find_mount_tokens(text: str) -> list[str]:
    """在给定文本中检出「挂载统一前端产物」的禁用标识."""
    return [token for token in _FORBIDDEN_MOUNT_TOKENS if token in text]


def _scan_backend_mount_tokens() -> list[tuple[str, str]]:
    """全量扫描 openbase/** 源码，返回 (相对路径, 命中标识) 列表."""
    hits: list[tuple[str, str]] = []
    for path in _SOURCE_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits.extend((_relative_posix(path), token) for token in _find_mount_tokens(text))
    return hits


# ---- S6-T1-1 冻结口径与改造登记 ----


def test_s6_t1_1_registry_document_registered() -> None:
    """口径登记文档存在，且含唯一维护面 / 冻结声明 / 两级闭环口径."""
    assert _REGISTRY_DOCUMENT.exists(), f"缺少 S6-T1-1 口径登记文档: {_REGISTRY_DOCUMENT}"
    content = _read_text(_REGISTRY_DOCUMENT)
    required_markers = (
        "统一前端唯一维护面",
        "openbase-ui",
        "107",
        "保留",
        "不再构建/发布",
        "后端不挂载",
        "口径闭环",
        "物理闭环",
        "PENDING",
        "Q-S6-D7",
    )
    missing = [marker for marker in required_markers if marker not in content]
    assert not missing, f"口径登记文档缺少必需表述: {missing}"


def test_s6_t1_1_three_transformation_points_registered() -> None:
    """3 处改造点（覆盖 4 仓）按「仓 / 文件:行号 / 动作 / 状态」逐项登记."""
    content = _read_text(_REGISTRY_DOCUMENT)
    required_markers = (
        "OpenMemory",
        "openmemory.conf:90",
        "openmemory.conf:93",
        "OpenLLM",
        "docker-compose.yml:141-172",
        "docker-compose.prod.yml:19",
        "DPS",
        "ci.yml",
        "68-79",
        "114-129",
        "164-195",
        "213-230",
        "OpenRAG",
        "frontend-ci.yml",
    )
    missing = [marker for marker in required_markers if marker not in content]
    assert not missing, f"3 处改造点登记缺项: {missing}"


def test_s6_t1_1_freeze_declaration_landing_listed() -> None:
    """冻结声明 4 仓落点待执行清单登记（含 OpenLLM 无 README 的候选落点）."""
    content = _read_text(_REGISTRY_DOCUMENT)
    required_markers = ("README.md", "frontend-frozen.md", "Q-S6-D5")
    missing = [marker for marker in required_markers if marker not in content]
    assert not missing, f"冻结声明落点清单缺项: {missing}"


# ---- S6-T1-2 后端不挂载确认断言 ----


def test_s6_t1_2_no_frontend_artifact_mount_in_backend() -> None:
    """OpenBase 后端 0 命中 StaticFiles / mount( / dist-v（防漂移固化）."""
    hits = _scan_backend_mount_tokens()
    assert not hits, f"OpenBase 后端出现挂载统一前端产物的痕迹: {hits}"


def test_s6_t1_2_target_directory_reference_is_whitelisted() -> None:
    """openbase/** 中 openbase-ui 引用仅限 CLI 目标目录文案（排除误报）."""
    referencing_files = [
        _relative_posix(path)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "openbase-ui" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert referencing_files == [_KNOWN_TARGET_DIRECTORY_REFERENCE], (
        f"openbase/** 中 openbase-ui 引用超出白名单: {referencing_files}"
    )


def test_s6_t1_2_mount_scanner_is_not_vacuous() -> None:
    """负向自检：扫描器对违规样本必须命中、对 CLI 文案必须不误报."""
    assert _find_mount_tokens("app.mount('/ui', StaticFiles(directory='dist-v1.3.0'))") != []
    assert _find_mount_tokens("target: 目标目录（openbase/modules 或 openbase-ui/src/modules）") == []


# ---- S6-T1-3 统一前端侧冻结声明落点 ----


def test_s6_t1_3_ui_frozen_declaration_present() -> None:
    """统一前端内冻结声明落点存在，且含唯一维护面 + 冻结口径 + 3 处改造指引."""
    assert _UI_FROZEN_DECLARATION.exists(), (
        f"缺少统一前端侧冻结声明落点: {_UI_FROZEN_DECLARATION}"
    )
    content = _read_text(_UI_FROZEN_DECLARATION)
    required_markers = (
        "统一前端唯一维护面",
        "OpenBase/openbase-ui",
        "保留",
        "不再构建/发布",
        "后端不挂载",
        "openmemory.conf:90",
        "docker-compose.yml:141-172",
        "ci.yml",
        "frontend-ci.yml",
    )
    missing = [marker for marker in required_markers if marker not in content]
    assert not missing, f"统一前端侧冻结声明缺少必需表述: {missing}"


# ---- S6-T1-4 口径闭环证据（清单引用位） ----


def test_s6_t1_4_registry_referenced_in_checklists() -> None:
    """清点总清单与跨仓放行清单留 S6-T1 口径闭环 + PENDING 移交引用位."""
    registry_name = _REGISTRY_DOCUMENT.name
    documents = {
        "清点总清单": _CLEARANCE_CHECKLIST,
        "跨仓提交放行清单": _CROSS_REPOSITORY_RELEASE,
    }
    for label, path in documents.items():
        content = _read_text(path)
        assert "S6-T1" in content, f"{label} 缺少 S6-T1 口径闭环注记"
        assert "口径闭环" in content, f"{label} 缺少「口径闭环」表述"
        assert "物理闭环" in content, f"{label} 缺少「物理闭环」移交表述"
        assert "PENDING" in content, f"{label} 缺少 PENDING 移交注记"
        assert registry_name in content, f"{label} 未引用登记文档 {registry_name}"


def test_s6_t1_4_existing_counts_and_redlines_preserved() -> None:
    """加注不得改动既有计数口径与通用提交红线."""
    clearance = _read_text(_CLEARANCE_CHECKLIST)
    assert "不改变任何既有计数与归类" in clearance
    assert "107" in clearance

    release = _read_text(_CROSS_REPOSITORY_RELEASE)
    assert "统一前端口径" in release
    assert "禁止将各子系统" in release
