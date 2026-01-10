"""Flashcard mode logic for Tang poems learning."""

from typing import List, Dict, Optional
import random
import json
from pathlib import Path
import json
from pathlib import Path
from datetime import datetime


def get_progress_file_path() -> Path:
    """Get the path to the progress save file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "flashcard_progress.json"


def load_progress() -> Optional[Dict]:
    """
    Load flashcard progress from file.
    Returns None if file doesn't exist or is invalid.
    """
    progress_file = get_progress_file_path()
    
    if not progress_file.exists():
        return None
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert lists back to sets
        if 'known_poems' in data:
            data['known_poems'] = set(data['known_poems'])
        if 'practice_poems' in data:
            data['practice_poems'] = set(data['practice_poems'])
        
        return data
    except Exception as e:
        print(f"Error loading progress: {e}")
        return None


def save_progress(flashcard_state: Dict) -> bool:
    """
    Save flashcard progress to file.
    Only saves persistent data (known_poems, practice_poems, current_index).
    Returns True if successful, False otherwise.
    """
    progress_file = get_progress_file_path()
    
    try:
        # Prepare data for saving (convert sets to lists for JSON)
        save_data = {
            'known_poems': list(flashcard_state.get('known_poems', set())),
            'practice_poems': list(flashcard_state.get('practice_poems', set())),
            'current_index': flashcard_state.get('current_index', 0),
            'last_updated': datetime.now().isoformat(),
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving progress: {e}")
        return False


def delete_progress_file() -> bool:
    """Delete the progress file. Returns True if successful."""
    progress_file = get_progress_file_path()
    try:
        if progress_file.exists():
            progress_file.unlink()
        return True
    except Exception as e:
        print(f"Error deleting progress file: {e}")
        return False


def initialize_flashcard_session(poems: List[Dict]) -> Dict:
    """
    Initialize flashcard session state.
    Loads progress from file if it exists.
    """
    # Start with default values
    state = {
        'current_index': 0,
        'poems': poems,
        'known_poems': set(),
        'practice_poems': set(),
        'revealed': False,
        'filter_mode': 'all',
        'shuffle': False,
        'filtered_indices': list(range(len(poems))),
        'study_count': 0,
    }
    
    # Try to load saved progress
    saved_progress = load_progress()
    if saved_progress:
        # Restore persistent data
        state['known_poems'] = saved_progress.get('known_poems', set())
        state['practice_poems'] = saved_progress.get('practice_poems', set())
        # Optionally restore last position (but validate it's still valid)
        last_index = saved_progress.get('current_index', 0)
        if 0 <= last_index < len(poems):
            state['current_index'] = last_index
        # Show when progress was last saved
        state['last_saved'] = saved_progress.get('last_updated', '')
    
    return state


def get_current_flashcard(flashcard_state: Dict) -> Optional[Dict]:
    """
    Get the current flashcard poem.
    """
    if flashcard_state['current_index'] < len(flashcard_state['poems']):
        return flashcard_state['poems'][flashcard_state['current_index']]
    return None




def mark_as_known(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Mark current poem as known.
    Automatically saves progress unless save=False.
    """
    current_idx = flashcard_state['current_index']
    flashcard_state['known_poems'].add(current_idx)
    if current_idx in flashcard_state['practice_poems']:
        flashcard_state['practice_poems'].remove(current_idx)
    flashcard_state['study_count'] = flashcard_state.get('study_count', 0) + 1
    
    if save:
        save_progress(flashcard_state)
    
    return flashcard_state


def mark_for_practice(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Mark current poem as needing practice.
    Automatically saves progress unless save=False.
    """
    current_idx = flashcard_state['current_index']
    flashcard_state['practice_poems'].add(current_idx)
    if current_idx in flashcard_state['known_poems']:
        flashcard_state['known_poems'].remove(current_idx)
    flashcard_state['study_count'] = flashcard_state.get('study_count', 0) + 1
    
    if save:
        save_progress(flashcard_state)
    
    return flashcard_state


def next_flashcard(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Move to next flashcard.
    Respects filter mode if active.
    If save is True, saves current position to file.
    """
    filtered_indices = flashcard_state.get('filtered_indices', list(range(len(flashcard_state['poems']))))
    
    if not filtered_indices:
        return flashcard_state
    
    current_idx = flashcard_state['current_index']
    
    # Find current position in filtered list
    try:
        current_pos = filtered_indices.index(current_idx)
        next_pos = (current_pos + 1) % len(filtered_indices)
    except ValueError:
        # Current index not in filtered list, go to first
        next_pos = 0
    
    flashcard_state['current_index'] = filtered_indices[next_pos]
    flashcard_state['revealed'] = False
    
    if save:
        save_progress(flashcard_state)
    
    return flashcard_state


def previous_flashcard(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Move to previous flashcard.
    Respects filter mode if active.
    If save is True, saves current position to file.
    """
    filtered_indices = flashcard_state.get('filtered_indices', list(range(len(flashcard_state['poems']))))
    
    if not filtered_indices:
        return flashcard_state
    
    current_idx = flashcard_state['current_index']
    
    # Find current position in filtered list
    try:
        current_pos = filtered_indices.index(current_idx)
        prev_pos = (current_pos - 1) % len(filtered_indices)
    except ValueError:
        # Current index not in filtered list, go to last
        prev_pos = len(filtered_indices) - 1
    
    flashcard_state['current_index'] = filtered_indices[prev_pos]
    flashcard_state['revealed'] = False
    
    if save:
        save_progress(flashcard_state)
    
    return flashcard_state


def reveal_content(flashcard_state: Dict) -> Dict:
    """
    Reveal the poem content.
    """
    flashcard_state['revealed'] = True
    return flashcard_state


def get_progress_stats(flashcard_state: Dict) -> Dict:
    """
    Get progress statistics.
    """
    total = len(flashcard_state['poems'])
    known = len(flashcard_state['known_poems'])
    practice = len(flashcard_state['practice_poems'])
    remaining = total - known - practice
    
    return {
        'total': total,
        'known': known,
        'practice': practice,
        'remaining': remaining,
        'known_percentage': (known / total * 100) if total > 0 else 0,
        'study_count': flashcard_state.get('study_count', 0)
    }


def get_filtered_indices(flashcard_state: Dict) -> List[int]:
    """
    Get list of poem indices based on current filter mode.
    """
    filter_mode = flashcard_state.get('filter_mode', 'all')
    known = flashcard_state.get('known_poems', set())
    practice = flashcard_state.get('practice_poems', set())
    total = len(flashcard_state['poems'])
    
    if filter_mode == 'all':
        indices = list(range(total))
    elif filter_mode == 'practice':
        indices = list(practice)
    elif filter_mode == 'unknown':
        indices = [i for i in range(total) if i not in known and i not in practice]
    elif filter_mode == 'known':
        indices = list(known)
    else:
        indices = list(range(total))
    
    # Shuffle if enabled
    if flashcard_state.get('shuffle', False):
        indices = indices.copy()
        random.shuffle(indices)
    
    return indices


def apply_filter(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Apply filter and update filtered_indices.
    If save is True, saves current state to file.
    """
    flashcard_state['filtered_indices'] = get_filtered_indices(flashcard_state)
    
    # Reset to first card in filtered list
    if flashcard_state['filtered_indices']:
        # Try to keep current poem if it's in filtered list
        current_idx = flashcard_state.get('current_index', 0)
        if current_idx not in flashcard_state['filtered_indices']:
            flashcard_state['current_index'] = flashcard_state['filtered_indices'][0]
            flashcard_state['revealed'] = False
    else:
        flashcard_state['current_index'] = 0
        flashcard_state['revealed'] = False
    
    if save:
        save_progress(flashcard_state)
    
    return flashcard_state


def jump_to_next_practice(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Jump to next poem that needs practice.
    If save is True, automatically saves progress to file.
    """
    practice_poems = list(flashcard_state.get('practice_poems', set()))
    if not practice_poems:
        return flashcard_state
    
    current_idx = flashcard_state.get('current_index', 0)
    
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
        flashcard_state['current_index'] = next_practice
        flashcard_state['revealed'] = False
        
        if save:
            save_progress(flashcard_state)
    
    return flashcard_state


def jump_to_next_unknown(flashcard_state: Dict, save: bool = True) -> Dict:
    """
    Jump to next unknown poem.
    If save is True, automatically saves progress to file.
    """
    known = flashcard_state.get('known_poems', set())
    practice = flashcard_state.get('practice_poems', set())
    total = len(flashcard_state['poems'])
    
    unknown_poems = [i for i in range(total) if i not in known and i not in practice]
    if not unknown_poems:
        return flashcard_state
    
    current_idx = flashcard_state.get('current_index', 0)
    
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
        flashcard_state['current_index'] = next_unknown
        flashcard_state['revealed'] = False
        
        if save:
            save_progress(flashcard_state)
    
    return flashcard_state


def reset_progress(flashcard_state: Dict) -> Dict:
    """
    Reset all progress (clear known and practice sets).
    Also deletes the progress file.
    """
    flashcard_state['known_poems'] = set()
    flashcard_state['practice_poems'] = set()
    flashcard_state['study_count'] = 0
    flashcard_state['revealed'] = False
    delete_progress_file()
    return flashcard_state


def get_current_poem_status(flashcard_state: Dict) -> str:
    """
    Get status of current poem: 'known', 'practice', or 'unknown'.
    """
    current_idx = flashcard_state.get('current_index', 0)
    if current_idx in flashcard_state.get('known_poems', set()):
        return 'known'
    elif current_idx in flashcard_state.get('practice_poems', set()):
        return 'practice'
    else:
        return 'unknown'

