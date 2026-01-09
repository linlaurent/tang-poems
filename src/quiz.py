"""Quiz mode logic for Tang poems learning."""

import random
from typing import List, Dict, Tuple, Optional


def generate_multiple_choice_question(poems: List[Dict], current_poem: Dict) -> Tuple[str, List[str], int]:
    """
    Generate a multiple choice question about the current poem.
    Returns: (question_text, options_list, correct_index)
    """
    question_types = [
        ('author', f"这首诗《{current_poem['title']}》的作者是谁？"),
        ('title', f"以下哪首诗是{current_poem['author']}的作品？"),
    ]
    
    question_type, question_text = random.choice(question_types)
    
    if question_type == 'author':
        # Question: Who is the author?
        correct_answer = current_poem['author']
        wrong_authors = [p['author'] for p in random.sample(
            [p for p in poems if p['author'] != correct_answer],
            min(3, len(poems) - 1)
        )]
        options = [correct_answer] + wrong_authors
        random.shuffle(options)
        correct_index = options.index(correct_answer)
        
    else:  # question_type == 'title'
        # Question: Which poem is by this author?
        correct_answer = current_poem['title']
        wrong_titles = [p['title'] for p in random.sample(
            [p for p in poems if p['title'] != correct_answer],
            min(3, len(poems) - 1)
        )]
        options = [correct_answer] + wrong_titles
        random.shuffle(options)
        correct_index = options.index(correct_answer)
    
    return question_text, options, correct_index


def generate_fill_in_blank_question(poem: Dict) -> Tuple[str, str]:
    """
    Generate a fill-in-the-blank question.
    Returns: (question_text_with_blank, correct_answer)
    """
    lines = [line.strip() for line in poem['content'].split('\n') if line.strip()]
    
    if not lines:
        return "", ""
    
    # Pick a random line
    line = random.choice(lines)
    
    # Split line into words and remove one
    words = list(line)
    if len(words) < 2:
        return line, ""
    
    # Remove a random character (but keep it meaningful)
    blank_index = random.randint(0, len(words) - 1)
    correct_answer = words[blank_index]
    words[blank_index] = '___'
    
    question = ''.join(words)
    full_question = f"请填空：{question}"
    
    return full_question, correct_answer


def initialize_quiz_session(poems: List[Dict]) -> Dict:
    """
    Initialize quiz session state.
    """
    return {
        'score': 0,
        'total_questions': 0,
        'current_question': None,
        'current_poem': None,
        'quiz_type': 'multiple_choice',  # or 'fill_blank'
        'answered': False,
        'correct_answer': None,
        'user_answer': None
    }


def get_next_question(poems: List[Dict], quiz_state: Dict) -> Dict:
    """
    Generate next quiz question.
    """
    current_poem = random.choice(poems)
    quiz_state['current_poem'] = current_poem
    quiz_state['answered'] = False
    quiz_state['user_answer'] = None
    
    if quiz_state['quiz_type'] == 'multiple_choice':
        question, options, correct_index = generate_multiple_choice_question(poems, current_poem)
        quiz_state['current_question'] = question
        quiz_state['options'] = options
        quiz_state['correct_index'] = correct_index
        quiz_state['correct_answer'] = options[correct_index]
    else:  # fill_blank
        question, correct_answer = generate_fill_in_blank_question(current_poem)
        quiz_state['current_question'] = question
        quiz_state['correct_answer'] = correct_answer
    
    return quiz_state


def check_answer(quiz_state: Dict, user_answer: str) -> bool:
    """
    Check if user's answer is correct.
    """
    quiz_state['user_answer'] = user_answer
    quiz_state['answered'] = True
    quiz_state['total_questions'] += 1
    
    is_correct = False
    if quiz_state['quiz_type'] == 'multiple_choice':
        is_correct = (user_answer == quiz_state['correct_answer'])
    else:  # fill_blank
        is_correct = (user_answer.strip() == quiz_state['correct_answer'].strip())
    
    if is_correct:
        quiz_state['score'] += 1
    
    return is_correct

