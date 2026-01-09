"""Flashcard mode logic for Tang poems learning."""

from typing import List, Dict, Optional


def initialize_flashcard_session(poems: List[Dict]) -> Dict:
    """
    Initialize flashcard session state.
    """
    return {
        'current_index': 0,
        'poems': poems,
        'known_poems': set(),  # Set of poem indices marked as known
        'practice_poems': set(),  # Set of poem indices that need practice
        'revealed': False
    }


def get_current_flashcard(flashcard_state: Dict) -> Optional[Dict]:
    """
    Get the current flashcard poem.
    """
    if flashcard_state['current_index'] < len(flashcard_state['poems']):
        return flashcard_state['poems'][flashcard_state['current_index']]
    return None


def next_flashcard(flashcard_state: Dict) -> Dict:
    """
    Move to next flashcard.
    """
    flashcard_state['current_index'] = (flashcard_state['current_index'] + 1) % len(flashcard_state['poems'])
    flashcard_state['revealed'] = False
    return flashcard_state


def previous_flashcard(flashcard_state: Dict) -> Dict:
    """
    Move to previous flashcard.
    """
    flashcard_state['current_index'] = (flashcard_state['current_index'] - 1) % len(flashcard_state['poems'])
    flashcard_state['revealed'] = False
    return flashcard_state


def mark_as_known(flashcard_state: Dict) -> Dict:
    """
    Mark current poem as known.
    """
    current_idx = flashcard_state['current_index']
    flashcard_state['known_poems'].add(current_idx)
    if current_idx in flashcard_state['practice_poems']:
        flashcard_state['practice_poems'].remove(current_idx)
    return flashcard_state


def mark_for_practice(flashcard_state: Dict) -> Dict:
    """
    Mark current poem as needing practice.
    """
    current_idx = flashcard_state['current_index']
    flashcard_state['practice_poems'].add(current_idx)
    if current_idx in flashcard_state['known_poems']:
        flashcard_state['known_poems'].remove(current_idx)
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
        'known_percentage': (known / total * 100) if total > 0 else 0
    }

