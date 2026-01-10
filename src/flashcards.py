"""Flashcard mode logic for Tang poems learning."""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from pypinyin import lazy_pinyin

# Import helper functions
try:
    # Try relative import first (when used as a module)
    from .data_loader import get_poem_id_by_index, get_poem_index_by_id
except ImportError:
    # Fall back to absolute import (when used directly)
    from src.data_loader import get_poem_id_by_index, get_poem_index_by_id


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


def migrate_progress_from_indices_to_ids(
    progress_data: dict, poems: list[dict]
) -> dict:
    """
    Migrate progress data from index-based to ID-based format.
    Converts known_poems, practice_poems, and current_index to use IDs.
    """
    migrated = progress_data.copy()

    # Migrate known_poems from indices to IDs
    if "known_poems" in migrated:
        known_indices = migrated["known_poems"]
        if isinstance(known_indices, (list, set)):
            known_ids = set()
            for idx in known_indices:
                if isinstance(idx, int) and 0 <= idx < len(poems):
                    poem_id = get_poem_id_by_index(poems, idx)
                    if poem_id:
                        known_ids.add(poem_id)
                elif isinstance(idx, str):
                    # Already an ID, keep it (validate it exists in poems)
                    if any(p.get("id") == idx for p in poems):
                        known_ids.add(idx)
            migrated["known_poems"] = known_ids
        else:
            # Invalid type, reset to empty set
            migrated["known_poems"] = set()
    else:
        migrated["known_poems"] = set()

    # Migrate practice_poems from indices to IDs
    if "practice_poems" in migrated:
        practice_indices = migrated["practice_poems"]
        if isinstance(practice_indices, (list, set)):
            practice_ids = set()
            for idx in practice_indices:
                if isinstance(idx, int) and 0 <= idx < len(poems):
                    poem_id = get_poem_id_by_index(poems, idx)
                    if poem_id:
                        practice_ids.add(poem_id)
                elif isinstance(idx, str):
                    # Already an ID, keep it (validate it exists in poems)
                    if any(p.get("id") == idx for p in poems):
                        practice_ids.add(idx)
            migrated["practice_poems"] = practice_ids
        else:
            # Invalid type, reset to empty set
            migrated["practice_poems"] = set()
    else:
        migrated["practice_poems"] = set()

    # Migrate current_index to current_id
    if "current_index" in migrated:
        current_idx = migrated["current_index"]
        if isinstance(current_idx, int) and 0 <= current_idx < len(poems):
            poem_id = get_poem_id_by_index(poems, current_idx)
            if poem_id:
                migrated["current_id"] = poem_id
            else:
                # Index valid but poem has no ID, use first poem with ID
                for poem in poems:
                    if poem.get("id"):
                        migrated["current_id"] = poem["id"]
                        break
                else:
                    migrated["current_id"] = ""
        elif isinstance(current_idx, str):
            # Already an ID (shouldn't happen, but handle it)
            if any(p.get("id") == current_idx for p in poems):
                migrated["current_id"] = current_idx
            else:
                migrated["current_id"] = ""
        # Remove old current_index
        del migrated["current_index"]
    elif "current_id" not in migrated:
        # No current_index and no current_id, set to first poem with ID
        migrated["current_id"] = ""
        for poem in poems:
            if poem.get("id"):
                migrated["current_id"] = poem["id"]
                break

    # Mark as migrated
    migrated["migrated_to_ids"] = True

    return migrated


def load_progress(user_id: str, poems: Optional[list[dict]] = None) -> Optional[dict]:
    """
    Load flashcard progress from file for a specific user.
    Automatically migrates from index-based to ID-based format if needed.
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

        # Check if migration is needed BEFORE converting to sets
        # Migration needed if:
        # 1. Poems list is provided and not empty
        # 2. File hasn't been migrated yet (no migrated_to_ids flag)
        # 3. File contains old format indicators
        #    (current_index or integer-based known/practice poems)
        has_old_format = False
        if "current_index" in data:
            has_old_format = True
        else:
            # Check if known_poems or practice_poems contain integers (indices)
            # instead of strings (IDs)
            known_list = data.get("known_poems", [])
            practice_list = data.get("practice_poems", [])
            if isinstance(known_list, list) and len(known_list) > 0:
                has_old_format = isinstance(known_list[0], int)
            if (
                not has_old_format
                and isinstance(practice_list, list)
                and len(practice_list) > 0
            ):
                has_old_format = isinstance(practice_list[0], int)

        needs_migration = (
            poems is not None
            and len(poems) > 0
            and not data.get("migrated_to_ids", False)
            and has_old_format
        )

        # Migrate from indices to IDs if needed (before converting to sets)
        if needs_migration:
            try:
                print(
                    f"Migrating progress file for user {user_id} "
                    f"from index-based to ID-based format..."
                )
                original_last_updated = data.get(
                    "last_updated", datetime.now().isoformat()
                )
                data = migrate_progress_from_indices_to_ids(data, poems)
                # Preserve original last_updated timestamp
                data["last_updated"] = original_last_updated
                # Save migrated version back to file immediately
                save_data = {
                    "known_poems": sorted(data.get("known_poems", set())),
                    "practice_poems": sorted(data.get("practice_poems", set())),
                    "current_id": data.get("current_id", ""),
                    "last_updated": data.get(
                        "last_updated", datetime.now().isoformat()
                    ),
                    "migrated_to_ids": True,
                }
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                print(f"Successfully migrated progress file for user {user_id}")
            except Exception as e:
                print(f"Error migrating progress file for user {user_id}: {e}")
                import traceback

                traceback.print_exc()
                # Continue with non-migrated data rather than failing completely

        # Convert lists back to sets (after migration)
        if "known_poems" in data:
            if isinstance(data["known_poems"], list):
                data["known_poems"] = set(data["known_poems"])
            elif not isinstance(data["known_poems"], set):
                data["known_poems"] = set()
        if "practice_poems" in data:
            if isinstance(data["practice_poems"], list):
                data["practice_poems"] = set(data["practice_poems"])
            elif not isinstance(data["practice_poems"], set):
                data["practice_poems"] = set()

        return data
    except Exception as e:
        print(f"Error loading progress: {e}")
        return None


def save_progress(flashcard_state: dict, user_id: Optional[str] = None) -> bool:
    """
    Save flashcard progress to file for a specific user.
    Only saves persistent data (known_poems, practice_poems, current_id).
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
            "current_id": flashcard_state.get("current_id", ""),
            "last_updated": datetime.now().isoformat(),
            "migrated_to_ids": True,
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
        "version": "2.0",  # Updated version for ID-based system
        "exported_at": datetime.now().isoformat(),
        "known_poems": sorted(flashcard_state.get("known_poems", set())),
        "practice_poems": sorted(flashcard_state.get("practice_poems", set())),
        "current_id": flashcard_state.get("current_id", ""),
        "total_poems": len(flashcard_state.get("poems", [])),
        "migrated_to_ids": True,
    }
    return export_data


def import_progress_data(
    flashcard_state: dict, import_data: dict, poems: list[dict]
) -> dict:
    """
    Import flashcard progress data from a dictionary.
    Validates and imports known_poems, practice_poems, and current_id.
    Supports both old index-based and new ID-based formats.
    Returns updated flashcard_state.
    """
    # Check if this is old format (index-based) or new format (ID-based)
    is_old_format = "current_index" in import_data and "current_id" not in import_data

    if is_old_format:
        # Migrate old format to new format
        import_data = migrate_progress_from_indices_to_ids(import_data, poems)

    # Create a set of valid poem IDs for validation
    valid_poem_ids = {poem.get("id") for poem in poems if poem.get("id")}

    # Validate and import known_poems
    if "known_poems" in import_data:
        known_list = import_data["known_poems"]
        if isinstance(known_list, list):
            # Filter valid IDs
            valid_known = {
                poem_id
                for poem_id in known_list
                if isinstance(poem_id, str) and poem_id in valid_poem_ids
            }
            flashcard_state["known_poems"] = valid_known

    # Validate and import practice_poems
    if "practice_poems" in import_data:
        practice_list = import_data["practice_poems"]
        if isinstance(practice_list, list):
            # Filter valid IDs
            valid_practice = {
                poem_id
                for poem_id in practice_list
                if isinstance(poem_id, str) and poem_id in valid_poem_ids
            }
            flashcard_state["practice_poems"] = valid_practice

    # Validate and import current_id
    if "current_id" in import_data:
        current_id = import_data["current_id"]
        if isinstance(current_id, str) and current_id in valid_poem_ids:
            flashcard_state["current_id"] = current_id

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

    # Get default current_id (first poem's ID)
    # If no poems have IDs, we'll need to fall back to index-based system
    default_id = ""
    if poems:
        # Find first poem with an ID
        for poem in poems:
            if poem.get("id"):
                default_id = poem["id"]
                break

    # Get all poem IDs for filtered list (only poems with IDs)
    all_ids = [poem.get("id") for poem in poems if poem.get("id")]

    # Start with default values
    state = {
        "current_id": default_id,
        "poems": poems,
        "known_poems": set(),
        "practice_poems": set(),
        "revealed": False,
        "filter_mode": "all",
        "shuffle": True,  # Enabled by default
        "filtered_ids": all_ids.copy(),
        "study_count": 0,
        "user_id": user_id,  # Store user_id in state
    }

    # Try to load saved progress for this user (only if not guest)
    saved_progress = None
    if user_id != "guest":
        saved_progress = load_progress(user_id, poems)

    if saved_progress:
        # Restore persistent data
        state["known_poems"] = saved_progress.get("known_poems", set())
        state["practice_poems"] = saved_progress.get("practice_poems", set())
        # Optionally restore last position (but validate it's still valid)
        last_id = saved_progress.get("current_id", "")
        if last_id and any(poem.get("id") == last_id for poem in poems):
            state["current_id"] = last_id
        elif not state["current_id"] and poems:
            # If saved ID is invalid and we don't have a default, use first poem with ID
            for poem in poems:
                if poem.get("id"):
                    state["current_id"] = poem["id"]
                    break
        # Show when progress was last saved
        state["last_saved"] = saved_progress.get("last_updated", "")

    return state


def get_current_flashcard(flashcard_state: dict) -> Optional[dict]:
    """
    Get the current flashcard poem.
    """
    current_id = flashcard_state.get("current_id", "")
    if not current_id:
        return None

    for poem in flashcard_state["poems"]:
        if poem.get("id") == current_id:
            return poem
    return None


def mark_as_known(flashcard_state: dict, save: bool = True) -> dict:
    """
    Mark current poem as known.
    Automatically saves progress unless save=False.
    """
    current_id = flashcard_state.get("current_id", "")
    if current_id:
        flashcard_state["known_poems"].add(current_id)
        if current_id in flashcard_state["practice_poems"]:
            flashcard_state["practice_poems"].remove(current_id)
        flashcard_state["study_count"] = flashcard_state.get("study_count", 0) + 1

    if save:
        save_progress(flashcard_state)

    return flashcard_state


def mark_for_practice(flashcard_state: dict, save: bool = True) -> dict:
    """
    Mark current poem as needing practice.
    Automatically saves progress unless save=False.
    """
    current_id = flashcard_state.get("current_id", "")
    if current_id:
        flashcard_state["practice_poems"].add(current_id)
        if current_id in flashcard_state["known_poems"]:
            flashcard_state["known_poems"].remove(current_id)
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
    filtered_ids = flashcard_state.get("filtered_ids", [])
    if not filtered_ids:
        # Fallback: get all poem IDs
        filtered_ids = [
            poem.get("id") for poem in flashcard_state["poems"] if poem.get("id")
        ]

    if not filtered_ids:
        return flashcard_state

    current_id = flashcard_state.get("current_id", "")

    # Find current position in filtered list
    try:
        current_pos = filtered_ids.index(current_id)
        next_pos = (current_pos + 1) % len(filtered_ids)
    except ValueError:
        # Current ID not in filtered list, go to first
        next_pos = 0

    flashcard_state["current_id"] = filtered_ids[next_pos]
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
    filtered_ids = flashcard_state.get("filtered_ids", [])
    if not filtered_ids:
        # Fallback: get all poem IDs
        filtered_ids = [
            poem.get("id") for poem in flashcard_state["poems"] if poem.get("id")
        ]

    if not filtered_ids:
        return flashcard_state

    current_id = flashcard_state.get("current_id", "")

    # Find current position in filtered list
    try:
        current_pos = filtered_ids.index(current_id)
        prev_pos = (current_pos - 1) % len(filtered_ids)
    except ValueError:
        # Current ID not in filtered list, go to last
        prev_pos = len(filtered_ids) - 1

    flashcard_state["current_id"] = filtered_ids[prev_pos]
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


def get_filtered_ids(flashcard_state: dict) -> list[str]:
    """
    Get list of poem IDs based on current filter mode.
    """
    filter_mode = flashcard_state.get("filter_mode", "all")
    known = flashcard_state.get("known_poems", set())
    practice = flashcard_state.get("practice_poems", set())
    poems = flashcard_state["poems"]

    # Get all poem IDs
    all_ids = [poem.get("id") for poem in poems if poem.get("id")]

    if filter_mode == "all":
        ids = all_ids
    elif filter_mode == "practice":
        ids = [poem_id for poem_id in all_ids if poem_id in practice]
    elif filter_mode == "unknown":
        ids = [
            poem_id
            for poem_id in all_ids
            if poem_id not in known and poem_id not in practice
        ]
    elif filter_mode == "known":
        ids = [poem_id for poem_id in all_ids if poem_id in known]
    else:
        ids = all_ids

    # Shuffle if enabled
    if flashcard_state.get("shuffle", False):
        ids = ids.copy()
        random.shuffle(ids)

    return ids


def apply_filter(flashcard_state: dict, save: bool = True) -> dict:
    """
    Apply filter and update filtered_ids.
    If save is True, saves current state to file.
    """
    flashcard_state["filtered_ids"] = get_filtered_ids(flashcard_state)

    # Reset to first card in filtered list
    if flashcard_state["filtered_ids"]:
        # Try to keep current poem if it's in filtered list
        current_id = flashcard_state.get("current_id", "")
        if current_id not in flashcard_state["filtered_ids"]:
            flashcard_state["current_id"] = flashcard_state["filtered_ids"][0]
            flashcard_state["revealed"] = False
    else:
        # No filtered poems, set to empty or first available
        poems = flashcard_state.get("poems", [])
        if poems and poems[0].get("id"):
            flashcard_state["current_id"] = poems[0]["id"]
        else:
            flashcard_state["current_id"] = ""
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

    current_id = flashcard_state.get("current_id", "")
    poems = flashcard_state.get("poems", [])

    # Get current index for comparison
    current_idx = None
    if current_id:
        current_idx = get_poem_index_by_id(poems, current_id)

    # Find next practice poem after current
    next_practice_id = None
    if current_idx is not None:
        for poem in poems:
            poem_id = poem.get("id")
            if poem_id and poem_id in practice_poems:
                poem_idx = get_poem_index_by_id(poems, poem_id)
                if poem_idx is not None and poem_idx > current_idx:
                    next_practice_id = poem_id
                    break

    # If none found, wrap around to first practice poem
    if next_practice_id is None and practice_poems:
        # Find first practice poem by index
        practice_indices = []
        for poem_id in practice_poems:
            idx = get_poem_index_by_id(poems, poem_id)
            if idx is not None:
                practice_indices.append((idx, poem_id))
        if practice_indices:
            practice_indices.sort()
            next_practice_id = practice_indices[0][1]

    if next_practice_id:
        flashcard_state["current_id"] = next_practice_id
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
    poems = flashcard_state.get("poems", [])

    # Get unknown poem IDs
    unknown_poem_ids = [
        poem.get("id")
        for poem in poems
        if poem.get("id")
        and poem.get("id") not in known
        and poem.get("id") not in practice
    ]

    if not unknown_poem_ids:
        return flashcard_state

    current_id = flashcard_state.get("current_id", "")
    current_idx = None
    if current_id:
        current_idx = get_poem_index_by_id(poems, current_id)

    # Find next unknown poem after current
    next_unknown_id = None
    if current_idx is not None:
        for poem in poems:
            poem_id = poem.get("id")
            if poem_id and poem_id in unknown_poem_ids:
                poem_idx = get_poem_index_by_id(poems, poem_id)
                if poem_idx is not None and poem_idx > current_idx:
                    next_unknown_id = poem_id
                    break

    # If none found, wrap around to first unknown poem
    if next_unknown_id is None and unknown_poem_ids:
        # Find first unknown poem by index
        unknown_indices = []
        for poem_id in unknown_poem_ids:
            idx = get_poem_index_by_id(poems, poem_id)
            if idx is not None:
                unknown_indices.append((idx, poem_id))
        if unknown_indices:
            unknown_indices.sort()
            next_unknown_id = unknown_indices[0][1]

    if next_unknown_id:
        flashcard_state["current_id"] = next_unknown_id
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
    current_id = flashcard_state.get("current_id", "")
    if not current_id:
        return "unknown"

    if current_id in flashcard_state.get("known_poems", set()):
        return "known"
    elif current_id in flashcard_state.get("practice_poems", set()):
        return "practice"
    else:
        return "unknown"


def jump_to_poem(flashcard_state: dict, poem_index: int, save: bool = True) -> dict:
    """
    Jump to a specific poem by index.
    If save is True, automatically saves progress to file.
    """
    poems = flashcard_state.get("poems", [])
    if 0 <= poem_index < len(poems):
        poem_id = get_poem_id_by_index(poems, poem_index)
        if poem_id:
            flashcard_state["current_id"] = poem_id
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
    Returns indices (for backward compatibility with app.py).
    """
    indices_with_titles = []
    for idx, poem in enumerate(poems):
        if poem.get("author", "") == author:
            title = poem.get("title", "无题")
            indices_with_titles.append((idx, title))

    # Sort by title pinyin
    indices_with_titles.sort(key=lambda x: "".join(lazy_pinyin(x[1])))
    return [idx for idx, _ in indices_with_titles]
