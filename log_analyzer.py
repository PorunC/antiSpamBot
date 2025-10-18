"""
日志分析工具，用于统计封禁垃圾账号的数据。
"""
from __future__ import annotations

import logging
import re
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 备用
    ZoneInfo = None  # type: ignore[attr-defined]

import config

logger = logging.getLogger(__name__)

BAN_LOG_PATTERN_WITH_CHAT = re.compile(
    (
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?"
        r"已封禁用户 - 群组: (?P<chat_title>.+?) \((?P<chat_id>-?\d+)\) - "
        r"(?P<username>.+?) \(ID: (?P<user_id>\d+)\)"
    )
)
BAN_LOG_PATTERN_LEGACY = re.compile(
    (
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?"
        r"已封禁用户 - (?P<username>.+?) \(ID: (?P<user_id>\d+)\)"
    )
)
TIME_FORMAT = "%Y-%m-%d %H:%M:%S,%f"
BAN_EVENT_MARKER = "BAN_EVENT"
if ZoneInfo is not None:
    try:
        BEIJING_TZ = ZoneInfo("Asia/Shanghai")
    except Exception:  # pragma: no cover - 缺少时区数据
        logger.warning("未找到 Asia/Shanghai 时区信息，使用固定 UTC+8 偏移")
        BEIJING_TZ = timezone(timedelta(hours=8))
else:  # pragma: no cover - Python <3.9 兼容路径
    logger.warning("标准库 ZoneInfo 不可用，使用固定 UTC+8 偏移")
    BEIJING_TZ = timezone(timedelta(hours=8))


def _parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse a timestamp string from the log into a timezone-aware datetime."""
    try:
        parsed = datetime.strptime(timestamp_str, TIME_FORMAT)
    except ValueError:
        logger.debug("无法解析日志时间戳: %s", timestamp_str)
        return None
    return parsed.replace(tzinfo=BEIJING_TZ)


def _safe_int(value: Any) -> Optional[int]:
    """Try to coerce a value into int."""
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _parse_ban_event_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a structured BAN_EVENT log line."""
    if BAN_EVENT_MARKER not in line:
        return None

    try:
        prefix, payload = line.split(BAN_EVENT_MARKER, 1)
    except ValueError:
        return None

    payload = payload.strip()
    if not payload:
        return None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        logger.debug("无法解析 BAN_EVENT JSON: %s | %s", exc, payload)
        return None

    timestamp_str = prefix.split(" - ", 1)[0].strip()
    timestamp = _parse_timestamp(timestamp_str)
    if not timestamp:
        return None

    chat_id = _safe_int(data.get("chat_id"))
    chat_title = data.get("chat_title") or None
    user_id_raw = data.get("user_id")
    user_id = str(user_id_raw) if user_id_raw is not None else None

    return {
        "timestamp": timestamp,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "username": data.get("username"),
        "user_id": user_id,
        "category": data.get("category") or "unknown",
        "reason": data.get("reason"),
        "confidence": data.get("confidence"),
        "extra": data.get("extra"),
        "source": "ban_event",
    }


def _parse_legacy_ban_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse legacy log lines without structured payloads."""
    match = BAN_LOG_PATTERN_WITH_CHAT.search(line)
    if match:
        timestamp = _parse_timestamp(match.group("timestamp"))
        if not timestamp:
            return None
        username = match.group("username").strip()
        return {
            "timestamp": timestamp,
            "chat_id": _safe_int(match.group("chat_id")),
            "chat_title": match.group("chat_title").strip(),
            "username": username,
            "user_id": match.group("user_id"),
            "category": "legacy_message_violation",
            "reason": None,
            "confidence": None,
            "extra": None,
            "source": "legacy_with_chat",
        }

    match = BAN_LOG_PATTERN_LEGACY.search(line)
    if match:
        timestamp = _parse_timestamp(match.group("timestamp"))
        if not timestamp:
            return None
        username = match.group("username").strip()
        return {
            "timestamp": timestamp,
            "chat_id": None,
            "chat_title": None,
            "username": username,
            "user_id": match.group("user_id"),
            "category": "legacy_message_violation",
            "reason": None,
            "confidence": None,
            "extra": None,
            "source": "legacy_basic",
        }

    return None


def get_recent_ban_stats(window_hours: int = 24) -> Dict[str, object]:
    """
    统计最近 window_hours 小时内被封禁的垃圾账号数量。

    返回结构:
    {
        "total": int,  # 封禁记录总数
        "unique_accounts": int,  # 唯一用户 ID 数量
        "entries": List[Dict[str, Any]],  # 每条封禁记录
        "since": datetime,  # 统计起始时间（含）
        "until": datetime,  # 统计结束时间（含）
        "by_chat": Dict[int, Dict[str, Any]],  # 按群组聚合的数据
        "by_category": Dict[str, Dict[str, Any]]  # 按封禁类别聚合的数据
    }
    """
    entries, window_start, now = _collect_recent_ban_entries(window_hours)

    unique_accounts = {entry["user_id"] for entry in entries if entry.get("user_id")}

    by_chat: Dict[int, Dict[str, Any]] = {}
    by_category: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        chat_id = entry.get("chat_id")
        category = entry.get("category") or "unknown"

        cat_stats = by_category.setdefault(
            category,
            {
                "total": 0,
                "unique_accounts": set(),
                "chat_counts": defaultdict(int),
            },
        )
        cat_stats["total"] += 1
        if entry.get("user_id"):
            cat_stats["unique_accounts"].add(entry["user_id"])
        if chat_id is not None:
            cat_stats["chat_counts"][chat_id] += 1

        if chat_id is None:
            # 旧日志缺少群组信息，无法纳入按群组聚合
            continue

        chat_stats = by_chat.setdefault(
            chat_id,
            {
                "chat_title": entry.get("chat_title"),
                "total": 0,
                "unique_accounts": set(),
                "entries": [],
                "by_category": defaultdict(int),
            },
        )
        if entry.get("chat_title") and not chat_stats.get("chat_title"):
            chat_stats["chat_title"] = entry.get("chat_title")
        chat_stats["total"] += 1
        if entry.get("user_id"):
            chat_stats["unique_accounts"].add(entry["user_id"])
        chat_stats["entries"].append(entry)
        chat_stats["by_category"][category] += 1

    # 排序每个群组的记录并清理集合
    for chat_stats in by_chat.values():
        chat_stats["entries"].sort(key=lambda item: item["timestamp"])
        chat_stats["unique_accounts"] = len(chat_stats["unique_accounts"])
        chat_stats["by_category"] = dict(chat_stats["by_category"])

    for cat_stats in by_category.values():
        cat_stats["unique_accounts"] = len(cat_stats["unique_accounts"])
        cat_stats["chat_counts"] = dict(cat_stats["chat_counts"])

    return {
        "total": len(entries),
        "unique_accounts": len(unique_accounts),
        "entries": entries,
        "since": window_start,
        "until": now,
        "by_chat": by_chat,
        "by_category": by_category,
    }


def _collect_recent_ban_entries(window_hours: int = 24):
    log_path = Path(config.LOG_FILE)
    now = datetime.now(BEIJING_TZ)
    window_start = now - timedelta(hours=window_hours)

    if not log_path.exists():
        logger.warning("日志文件不存在，无法生成封禁统计: %s", log_path)
        return [], window_start, now

    entries: List[Dict[str, object]] = []

    try:
        with log_path.open("r", encoding="utf-8") as log_file:
            for line in log_file:
                entry: Optional[Dict[str, Any]] = None

                if BAN_EVENT_MARKER in line:
                    entry = _parse_ban_event_line(line)

                if entry is None:
                    entry = _parse_legacy_ban_line(line)

                if entry is None:
                    continue

                timestamp = entry.get("timestamp")
                if not timestamp or timestamp < window_start or timestamp > now:
                    continue

                entries.append(entry)
    except OSError as exc:
        logger.error("读取日志文件失败: %s", exc)
        return [], window_start, now

    entries.sort(key=lambda entry: entry["timestamp"])
    return entries, window_start, now
