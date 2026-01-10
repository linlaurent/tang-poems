"""Flashcard mode logic for Tang poems learning."""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from pypinyin import lazy_pinyin


def get_progress_file_path(user_id: str) -> Path:
    """Get the path to the progress save file for a specific user."""
    # Validate user_id
    if not user_id or not isinstance(user_id, str):
        user_id = "guest"

    try:
        # Try to get path relative to current file location
        current_file = Path(__file__)
        project_root = current_file.parent.parent
    except (AttributeError, OSError):
        # Fallback to current working directory if __file__ is not available
        project_root = Path.cwd()

    data_dir = project_root / "data"
    try:
        data_dir.mkdir(exist_ok=True, parents=True)
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create data directory: {e}")
        # Fallback to a temporary or current directory
        data_dir = Path.cwd() / "data"
        data_dir.mkdir(exist_ok=True, parents=True)

    # Create user-specific subdirectory
    user_dir = data_dir / "users"
    try:
        user_dir.mkdir(exist_ok=True, parents=True)
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create users directory: {e}")
        # Fallback: use data_dir directly
        user_dir = data_dir

    # Sanitize user_id for filename (replace special chars)
    safe_user_id = "".join(
        c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id
    )
    return user_dir / f"flashcard_progress_{safe_user_id}.json"


def load_progress(user_id: str) -> Optional[dict]:
    """
    Load flashcard progress from file for a specific user.
    Returns None if file doesn't exist or is invalid.
    """
    # Validate user_id
    if not user_id or not isinstance(user_id, str) or user_id == "guest":
        return None

    progress_file = get_progress_file_path(user_id)

    if not progress_file.exists():
        return None

    try:
        with open(progress_file, encoding="utf-8") as f:
            data = json.load(f)

        # Convert lists back to sets
        if "known_poems" in data:
            data["known_poems"] = set(data["known_poems"])
        if "practice_poems" in data:
            data["practice_poems"] = set(data["practice_poems"])

        return data
    except Exception as e:
        print(f"Error loading progress: {e}")
        return None


def save_progress(flashcard_state: dict, user_id: Optional[str] = None) -> bool:
    """
    Save flashcard progress to file for a specific user.
    Only saves persistent data (known_poems, practice_poems, current_index).
    Returns True if successful, False otherwise.
    """
    # Get user_id from flashcard_state if not provided
    if user_id is None:
        user_id = flashcard_state.get("user_id")

    if not user_id or user_id == "guest":
        # Don't save progress for guest users
        return False

    progress_file = get_progress_file_path(user_id)

    try:
        # Prepare data for saving (convert sets to lists for JSON)
        save_data = {
            "known_poems": list(flashcard_state.get("known_poems", set())),
            "practice_poems": list(flashcard_state.get("practice_poems", set())),
            "current_index": flashcard_state.get("current_index", 0),
            "last_updated": datetime.now().isoformat(),
        }

        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        print(f"Error saving progress: {e}")
        return False


def export_progress_data(flashcard_state: dict) -> dict:
    """
    Export flashcard progress data to a dictionary format for download.
    Returns a dictionary with all progress data.
    """
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "known_poems": sorted(flashcard_state.get("known_poems", set())),
        "practice_poems": sorted(flashcard_state.get("practice_poems", set())),
        "current_index": flashcard_state.get("current_index", 0),
        "total_poems": len(flashcard_state.get("poems", [])),
    }
    return export_data


def import_progress_data(
    flashcard_state: dict, import_data: dict, poems: list[dict]
) -> dict:
    """
    Import flashcard progress data from a dictionary.
    Validates and imports known_poems, practice_poems, and current_index.
    Returns updated flashcard_state.
    """
    total_poems = len(poems)

    # Validate and import known_poems
    if "known_poems" in import_data:
        known_list = import_data["known_poems"]
        if isinstance(known_list, list):
            # Filter valid indices
            valid_known = {
                idx
                for idx in known_list
                if isinstance(idx, int) and 0 <= idx < total_poems
            }
            flashcard_state["known_poems"] = valid_known

    # Validate and import practice_poems
    if "practice_poems" in import_data:
        practice_list = import_data["practice_poems"]
        if isinstance(practice_list, list):
            # Filter valid indices
            valid_practice = {
                idx
                for idx in practice_list
                if isinstance(idx, int) and 0 <= idx < total_poems
            }
            flashcard_state["practice_poems"] = valid_practice

    # Validate and import current_index
    if "current_index" in import_data:
        current_idx = import_data["current_index"]
        if isinstance(current_idx, int) and 0 <= current_idx < total_poems:
            flashcard_state["current_index"] = current_idx

    # Ensure no overlap between known and practice (known takes priority)
    known_set = flashcard_state.get("known_poems", set())
    practice_set = flashcard_state.get("practice_poems", set())
    # Remove poems from practice if they're in known
    practice_set = practice_set - known_set
    flashcard_state["practice_poems"] = practice_set

    # Reset revealed state
    flashcard_state["revealed"] = False

    return flashcard_state


def delete_progress_file(
    user_id: Optional[str] = None, flashcard_state: Optional[dict] = None
) -> bool:
    """Delete the progress file for a specific user. Returns True if successful."""
    # Get user_id from flashcard_state if provided, otherwise use parameter
    if not user_id and flashcard_state:
        user_id = flashcard_state.get("user_id")

    if not user_id:
        print("Error: user_id is required to delete progress file")
        return False

    progress_file = get_progress_file_path(user_id)
    try:
        if progress_file.exists():
            progress_file.unlink()
        return True
    except Exception as e:
        print(f"Error deleting progress file: {e}")
        return False


def initialize_flashcard_session(poems: list[dict], user_id: str) -> dict:
    """
    Initialize flashcard session state for a specific user.
    Loads progress from file if it exists.
    """
    # Validate user_id
    if not user_id or not isinstance(user_id, str):
        user_id = "guest"

    # Start with default values
    state = {
        "current_index": 0,
        "poems": poems,
        "known_poems": set(),
        "practice_poems": set(),
        "revealed": False,
        "filter_mode": "all",
        "shuffle": True,  # Enabled by default
        "filtered_indices": list(range(len(poems))),
        "study_count": 0,
        "user_id": user_id,  # Store user_id in state
    }

    # Try to load saved progress for this user (only if not guest)
    saved_progress = None
    if user_id != "guest":
        saved_progress = load_progress(user_id)

    if saved_progress:
        # Restore persistent data
        state["known_poems"] = saved_progress.get("known_poems", set())
        state["practice_poems"] = saved_progress.get("practice_poems", set())
        # Optionally restore last position (but validate it's still valid)
        last_index = saved_progress.get("current_index", 0)
        if 0 <= last_index < len(poems):
            state["current_index"] = last_index
        # Show when progress was last saved
        state["last_saved"] = saved_progress.get("last_updated", "")

    return state


def get_current_flashcard(flashcard_state: dict) -> Optional[dict]:
    """
    Get the current flashcard poem.
    """
    if flashcard_state["current_index"] < len(flashcard_state["poems"]):
        return flashcard_state["poems"][flashcard_state["current_index"]]
    return None


def mark_as_known(flashcard_state: dict, save: bool = True) -> dict:
    """
    Mark current poem as known.
    Automatically saves progress unless save=False.
    """
    current_idx = flashcard_state["current_index"]
    flashcard_state["known_poems"].add(current_idx)
    if current_idx in flashcard_state["practice_poems"]:
        flashcard_state["practice_poems"].remove(current_idx)
    flashcard_state["study_count"] = flashcard_state.get("study_count", 0) + 1

    if save:
        save_progress(flashcard_state)

    return flashcard_state


def mark_for_practice(flashcard_state: dict, save: bool = True) -> dict:
    """
    Mark current poem as needing practice.
    Automatically saves progress unless save=False.
    """
    current_idx = flashcard_state["current_index"]
    flashcard_state["practice_poems"].add(current_idx)
    if current_idx in flashcard_state["known_poems"]:
        flashcard_state["known_poems"].remove(current_idx)
    flashcard_state["study_count"] = flashcard_state.get("study_count", 0) + 1

    if save:
        save_progress(flashcard_state)

    return flashcard_state


def next_flashcard(flashcard_state: dict, save: bool = True) -> dict:
    """
    Move to next flashcard.
    Respects filter mode if active.
    If save is True, saves current position to file.
    """
    filtered_indices = flashcard_state.get(
        "filtered_indices", list(range(len(flashcard_state["poems"])))
    )

    if not filtered_indices:
        return flashcard_state

    current_idx = flashcard_state["current_index"]

    # Find current position in filtered list
    try:
        current_pos = filtered_indices.index(current_idx)
        next_pos = (current_pos + 1) % len(filtered_indices)
    except ValueError:
        # Current index not in filtered list, go to first
        next_pos = 0

    flashcard_state["current_index"] = filtered_indices[next_pos]
    flashcard_state["revealed"] = False

    if save:
        save_progress(flashcard_state)

    return flashcard_state


def previous_flashcard(flashcard_state: dict, save: bool = True) -> dict:
    """
    Move to previous flashcard.
    Respects filter mode if active.
    If save is True, saves current position to file.
    """
    filtered_indices = flashcard_state.get(
        "filtered_indices", list(range(len(flashcard_state["poems"])))
    )

    if not filtered_indices:
        return flashcard_state

    current_idx = flashcard_state["current_index"]

    # Find current position in filtered list
    try:
        current_pos = filtered_indices.index(current_idx)
        prev_pos = (current_pos - 1) % len(filtered_indices)
    except ValueError:
        # Current index not in filtered list, go to last
        prev_pos = len(filtered_indices) - 1

    flashcard_state["current_index"] = filtered_indices[prev_pos]
    flashcard_state["revealed"] = False

    if save:
        save_progress(flashcard_state)

    return flashcard_state


def reveal_content(flashcard_state: dict) -> dict:
    """
    Reveal the poem content.
    """
    flashcard_state["revealed"] = True
    return flashcard_state


def get_progress_stats(flashcard_state: dict) -> dict:
    """
    Get progress statistics.
    """
    total = len(flashcard_state["poems"])
    known = len(flashcard_state["known_poems"])
    practice = len(flashcard_state["practice_poems"])
    remaining = total - known - practice

    return {
        "total": total,
        "known": known,
        "practice": practice,
        "remaining": remaining,
        "known_percentage": (known / total * 100) if total > 0 else 0,
        "practice_percentage": (practice / total * 100) if total > 0 else 0,
        "study_count": flashcard_state.get("study_count", 0),
    }


def get_filtered_indices(flashcard_state: dict) -> list[int]:
    """
    Get list of poem indices based on current filter mode.
    """
    filter_mode = flashcard_state.get("filter_mode", "all")
    known = flashcard_state.get("known_poems", set())
    practice = flashcard_state.get("practice_poems", set())
    total = len(flashcard_state["poems"])

    if filter_mode == "all":
        indices = list(range(total))
    elif filter_mode == "practice":
        indices = list(practice)
    elif filter_mode == "unknown":
        indices = [i for i in range(total) if i not in known and i not in practice]
    elif filter_mode == "known":
        indices = list(known)
    else:
        indices = list(range(total))

    # Shuffle if enabled
    if flashcard_state.get("shuffle", False):
        indices = indices.copy()
        random.shuffle(indices)

    return indices


def apply_filter(flashcard_state: dict, save: bool = True) -> dict:
    """
    Apply filter and update filtered_indices.
    If save is True, saves current state to file.
    """
    flashcard_state["filtered_indices"] = get_filtered_indices(flashcard_state)

    # Reset to first card in filtered list
    if flashcard_state["filtered_indices"]:
        # Try to keep current poem if it's in filtered list
        current_idx = flashcard_state.get("current_index", 0)
        if current_idx not in flashcard_state["filtered_indices"]:
            flashcard_state["current_index"] = flashcard_state["filtered_indices"][0]
            flashcard_state["revealed"] = False
    else:
        flashcard_state["current_index"] = 0
        flashcard_state["revealed"] = False

    if save:
        save_progress(flashcard_state)

    return flashcard_state


def jump_to_next_practice(flashcard_state: dict, save: bool = True) -> dict:
    """
    Jump to next poem that needs practice.
    If save is True, automatically saves progress to file.
    """
    practice_poems = list(flashcard_state.get("practice_poems", set()))
    if not practice_poems:
        return flashcard_state

    current_idx = flashcard_state.get("current_index", 0)

    # Find next practice poem after current
    next_practice = None
    for idx in sorted(practice_poems):
        if idx > current_idx:
            next_practice = idx
            break

    # If none found, wrap around to first practice poem
    if next_practice is None and practice_poems:
        next_practice = min(practice_poems)

    if next_practice is not None:
        flashcard_state["current_index"] = next_practice
        flashcard_state["revealed"] = False

        if save:
            save_progress(flashcard_state)

    return flashcard_state


def jump_to_next_unknown(flashcard_state: dict, save: bool = True) -> dict:
    """
    Jump to next unknown poem.
    If save is True, automatically saves progress to file.
    """
    known = flashcard_state.get("known_poems", set())
    practice = flashcard_state.get("practice_poems", set())
    total = len(flashcard_state["poems"])

    unknown_poems = [i for i in range(total) if i not in known and i not in practice]
    if not unknown_poems:
        return flashcard_state

    current_idx = flashcard_state.get("current_index", 0)

    # Find next unknown poem after current
    next_unknown = None
    for idx in sorted(unknown_poems):
        if idx > current_idx:
            next_unknown = idx
            break

    # If none found, wrap around to first unknown poem
    if next_unknown is None and unknown_poems:
        next_unknown = min(unknown_poems)

    if next_unknown is not None:
        flashcard_state["current_index"] = next_unknown
        flashcard_state["revealed"] = False

        if save:
            save_progress(flashcard_state)

    return flashcard_state


def reset_progress(flashcard_state: dict) -> dict:
    """
    Reset all progress (clear known and practice sets).
    Also deletes the progress file for this user.
    """
    flashcard_state["known_poems"] = set()
    flashcard_state["practice_poems"] = set()
    flashcard_state["study_count"] = 0
    flashcard_state["revealed"] = False
    delete_progress_file(flashcard_state=flashcard_state)
    return flashcard_state


def get_current_poem_status(flashcard_state: dict) -> str:
    """
    Get status of current poem: 'known', 'practice', or 'unknown'.
    """
    current_idx = flashcard_state.get("current_index", 0)
    if current_idx in flashcard_state.get("known_poems", set()):
        return "known"
    elif current_idx in flashcard_state.get("practice_poems", set()):
        return "practice"
    else:
        return "unknown"


def jump_to_poem(flashcard_state: dict, poem_index: int, save: bool = True) -> dict:
    """
    Jump to a specific poem by index.
    If save is True, automatically saves progress to file.
    """
    total = len(flashcard_state["poems"])
    if 0 <= poem_index < total:
        flashcard_state["current_index"] = poem_index
        flashcard_state["revealed"] = False

        if save:
            save_progress(flashcard_state)

    return flashcard_state


def get_all_authors(poems: list[dict]) -> list[str]:
    """
    Get list of all unique authors from poems, sorted by pinyin.
    """
    authors = set()
    for poem in poems:
        author = poem.get("author", "未知")
        if author:
            authors.add(author)
    # Sort by pinyin
    authors_list = list(authors)
    authors_list.sort(key=lambda x: "".join(lazy_pinyin(x)))
    return authors_list


def get_poems_by_author(poems: list[dict], author: str) -> list[int]:
    """
    Get list of poem indices for a specific author, sorted by poem title pinyin.
    """
    indices_with_titles = []
    for idx, poem in enumerate(poems):
        if poem.get("author", "") == author:
            title = poem.get("title", "无题")
            indices_with_titles.append((idx, title))

    # Sort by title pinyin
    indices_with_titles.sort(key=lambda x: "".join(lazy_pinyin(x[1])))
    return [idx for idx, _ in indices_with_titles]
