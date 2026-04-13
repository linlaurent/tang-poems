"""Analytics module for flashcard learning progress."""

from collections import defaultdict
from datetime import datetime, timedelta

try:
    import pandas as pd
except ImportError:
    pd = None


def get_learning_timeline(log_entries: list[dict]) -> dict:
    """
    Groups events by date.
    Returns: {date: {"marked_known": count, "marked_practice": count, "total": count}}
    """
    timeline = defaultdict(
        lambda: {"marked_known": 0, "marked_practice": 0, "total": 0}
    )

    for entry in log_entries:
        timestamp_str = entry.get("timestamp", "")
        if not timestamp_str:
            continue

        try:
            # Parse ISO8601 timestamp
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            date_key = dt.date().isoformat()
            event_type = entry.get("event_type", "")

            if event_type == "marked_known":
                timeline[date_key]["marked_known"] += 1
                timeline[date_key]["total"] += 1
            elif event_type == "marked_practice":
                timeline[date_key]["marked_practice"] += 1
                timeline[date_key]["total"] += 1
        except (ValueError, AttributeError):
            # Skip invalid timestamps
            continue

    return dict(sorted(timeline.items()))


def get_poem_history(log_entries: list[dict], poem_id: str) -> list[dict]:
    """
    Returns all events for a specific poem in chronological order.
    Includes status changes over time.
    """
    poem_events = [
        entry
        for entry in log_entries
        if entry.get("poem_id") == poem_id
        and entry.get("event_type") in ("marked_known", "marked_practice")
    ]
    # Sort by timestamp
    poem_events.sort(key=lambda x: x.get("timestamp", ""))
    return poem_events


def get_study_stats(log_entries: list[dict]) -> dict:
    """
    Calculate study statistics.
    Returns:
    - Total study sessions (days with activity)
    - Average poems per session
    - Most active days
    - Study streak (consecutive days with activity)
    """
    if not log_entries:
        return {
            "total_sessions": 0,
            "average_poems_per_session": 0,
            "most_active_days": [],
            "current_streak": 0,
            "longest_streak": 0,
        }

    # Get timeline to count sessions
    timeline = get_learning_timeline(log_entries)

    total_sessions = len(timeline)
    total_poems = sum(day["total"] for day in timeline.values())
    average_poems_per_session = (
        total_poems / total_sessions if total_sessions > 0 else 0
    )

    # Find most active days (top 5)
    sorted_days = sorted(timeline.items(), key=lambda x: x[1]["total"], reverse=True)[
        :5
    ]
    most_active_days = [
        {"date": date, "count": data["total"]} for date, data in sorted_days
    ]

    # Calculate streaks
    streak_info = calculate_streaks(log_entries)

    return {
        "total_sessions": total_sessions,
        "average_poems_per_session": round(average_poems_per_session, 2),
        "most_active_days": most_active_days,
        "current_streak": streak_info.get("current_streak", 0),
        "longest_streak": streak_info.get("longest_streak", 0),
        "total_events": len(log_entries),
    }


def calculate_streaks(log_entries: list[dict]) -> dict:
    """
    Calculate study streaks (consecutive days with activity).
    Returns: current_streak, longest_streak, streak_history
    """
    if not log_entries:
        return {"current_streak": 0, "longest_streak": 0, "streak_history": []}

    # Get all unique dates with activity
    active_dates = set()
    for entry in log_entries:
        timestamp_str = entry.get("timestamp", "")
        if not timestamp_str:
            continue

        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            active_dates.add(dt.date())
        except (ValueError, AttributeError):
            continue

    if not active_dates:
        return {"current_streak": 0, "longest_streak": 0, "streak_history": []}

    # Sort dates
    sorted_dates = sorted(active_dates)
    today = datetime.now().date()

    # Calculate longest streak
    longest_streak = 1
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 1

    # Calculate current streak (from today backwards)
    current_streak = 0
    check_date = today
    while check_date in active_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "first_activity": sorted_dates[0].isoformat() if sorted_dates else None,
        "last_activity": sorted_dates[-1].isoformat() if sorted_dates else None,
    }


def get_poem_analytics(log_entries: list[dict], poems: list[dict]) -> dict:
    """
    Analyze poem-level data.
    Returns:
    - Time to learn each poem (first practice → marked_known)
    - Most/least studied poems
    - Poems that changed status multiple times
    - Distribution: known vs practice vs unknown
    """
    if not log_entries:
        return {
            "poem_learning_times": {},
            "most_studied": [],
            "status_changes": {},
            "distribution": {"known": 0, "practice": 0, "unknown": 0},
        }

    # Track status changes per poem
    poem_status_changes = defaultdict(int)
    poem_first_seen = {}
    poem_marked_known_time = {}

    for entry in log_entries:
        poem_id = entry.get("poem_id")
        if not poem_id:
            continue

        event_type = entry.get("event_type")
        timestamp_str = entry.get("timestamp", "")

        if not timestamp_str:
            continue

        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        if event_type in ("marked_known", "marked_practice"):
            poem_status_changes[poem_id] += 1

            if poem_id not in poem_first_seen:
                poem_first_seen[poem_id] = dt

            if event_type == "marked_known":
                poem_marked_known_time[poem_id] = dt

        # Track first practice
        if event_type == "marked_practice" and poem_id not in poem_first_seen:
            poem_first_seen[poem_id] = dt

    # Calculate learning times (first practice → marked_known)
    poem_learning_times = {}
    for poem_id, known_time in poem_marked_known_time.items():
        first_seen = poem_first_seen.get(poem_id)
        if first_seen:
            time_diff = known_time - first_seen
            poem_learning_times[poem_id] = {
                "days": time_diff.days,
                "hours": time_diff.total_seconds() / 3600,
                "first_seen": first_seen.isoformat(),
                "marked_known": known_time.isoformat(),
            }

    # Most studied poems (by status change count)
    most_studied = sorted(
        poem_status_changes.items(), key=lambda x: x[1], reverse=True
    )[:10]

    # Get current distribution from flashcard state (will be passed separately)
    distribution = {"known": 0, "practice": 0, "unknown": 0}

    return {
        "poem_learning_times": poem_learning_times,
        "most_studied": [
            {"poem_id": pid, "change_count": count} for pid, count in most_studied
        ],
        "status_changes": dict(poem_status_changes),
        "distribution": distribution,
    }


def get_recommendations(
    log_entries: list[dict],
    flashcard_state: dict,
    poems: list[dict],
) -> list[dict]:
    """
    Generate actionable recommendations.
    Returns list of recommendation dicts with type, message, and optional poem_id.
    """
    recommendations = []

    if not log_entries:
        recommendations.append(
            {
                "type": "info",
                "priority": "low",
                "message": "开始使用闪卡模式来生成学习数据和分析",
            }
        )
        return recommendations

    practice_poems = flashcard_state.get("practice_poems", set())
    known_poems = flashcard_state.get("known_poems", set())
    all_poem_ids = {poem.get("id") for poem in poems if poem.get("id")}
    unknown_poems = all_poem_ids - known_poems - practice_poems

    # Find poems in practice for > 7 days
    today = datetime.now().date()
    practice_time = {}
    for entry in log_entries:
        poem_id = entry.get("poem_id")
        event_type = entry.get("event_type")
        timestamp_str = entry.get("timestamp", "")

        if poem_id and event_type == "marked_practice" and timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Track most recent practice marking
                if poem_id not in practice_time or dt.date() > practice_time[poem_id]:
                    practice_time[poem_id] = dt.date()
            except (ValueError, AttributeError):
                continue

    # Recommendations for practice poems ready to review
    for poem_id in practice_poems:
        if poem_id in practice_time:
            days_in_practice = (today - practice_time[poem_id]).days
            if days_in_practice >= 7:
                poem_title = next(
                    (p.get("title", "未知") for p in poems if p.get("id") == poem_id),
                    "未知",
                )
                recommendations.append(
                    {
                        "type": "review_practice",
                        "priority": "high",
                        "message": (
                            f"《{poem_title}》已在练习列表中 {days_in_practice} 天，"
                            "可以考虑标记为已掌握"
                        ),
                        "poem_id": poem_id,
                        "days_in_practice": days_in_practice,
                    }
                )

    # Recommendations for never-studied poems
    if unknown_poems:
        recommendations.append(
            {
                "type": "discover",
                "priority": "medium",
                "message": f"还有 {len(unknown_poems)} 首诗歌尚未学习，继续探索吧！",
                "count": len(unknown_poems),
            }
        )

    # Learning velocity insights
    timeline = get_learning_timeline(log_entries)
    if len(timeline) >= 7:
        recent_days = list(timeline.values())[-7:]
        recent_avg = sum(day["total"] for day in recent_days) / 7
        if recent_avg > 5:
            recommendations.append(
                {
                    "type": "encouragement",
                    "priority": "low",
                    "message": (
                        f"最近7天平均每天学习 {recent_avg:.1f} 首诗歌，保持这个节奏！"
                    ),
                }
            )

    # Sort by priority (high, medium, low)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

    return recommendations


def format_timeline_data(timeline: dict) -> tuple:
    """
    Format timeline data for Streamlit charts.
    Returns tuple of (DataFrame for cumulative, DataFrame for daily)
    """
    if not timeline:
        return None, None

    if pd is None:
        # Fallback to dict format if pandas not available
        return timeline, timeline

    dates = sorted(timeline.keys())
    daily_data = {
        "日期": dates,
        "已掌握": [timeline[date]["marked_known"] for date in dates],
        "需练习": [timeline[date]["marked_practice"] for date in dates],
        "总计": [timeline[date]["total"] for date in dates],
    }
    daily_df = pd.DataFrame(daily_data)

    # Calculate cumulative
    cumulative_known = []
    cumulative_total = []
    running_known = 0
    running_total = 0

    for date in dates:
        running_known += timeline[date]["marked_known"]
        running_total += timeline[date]["total"]
        cumulative_known.append(running_known)
        cumulative_total.append(running_total)

    cumulative_data = {
        "日期": dates,
        "累计已掌握": cumulative_known,
        "累计学习": cumulative_total,
    }
    cumulative_df = pd.DataFrame(cumulative_data)

    return cumulative_df, daily_df
