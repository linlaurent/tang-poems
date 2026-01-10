"""Main Streamlit application for learning 300 Tang Poems."""

import streamlit as st
from src.data_loader import load_poems, search_poems
from src.quiz import initialize_quiz_session, get_next_question, check_answer
from src.flashcards import (
    initialize_flashcard_session, get_current_flashcard,
    next_flashcard, previous_flashcard, mark_as_known, mark_for_practice,
    reveal_content, get_progress_stats
)

# Page configuration
st.set_page_config(
    page_title="唐诗三百首学习",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better Chinese font support
st.markdown("""
<style>
    .poem-card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f8f9fa;
        margin: 1rem 0;
        border-left: 4px solid #4CAF50;
    }
    .poem-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    .poem-author {
        font-size: 1rem;
        color: #7f8c8d;
        margin-bottom: 1rem;
    }
    .poem-content {
        font-size: 1.2rem;
        line-height: 2;
        color: #34495e;
        white-space: pre-line;
    }
    .quiz-question {
        font-size: 1.3rem;
        font-weight: bold;
        margin: 1.5rem 0;
        color: #2c3e50;
    }
    .flashcard-front {
        padding: 2rem;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def display_mode():
    """Display mode: Browse and search poems."""
    st.header("📖 浏览唐诗")
    
    poems = load_poems()
    
    # Search bar
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "🔍 搜索诗歌（标题、作者或内容）", 
            placeholder="输入关键词...",
            key="poem_search_input"
        )
    with col2:
        st.write("")  # Spacing
        st.write(f"**共 {len(poems)} 首诗**")
    
    # Filter poems based on search query
    if search_query and search_query.strip():
        filtered_poems = search_poems(poems, search_query)
        if not filtered_poems:
            st.warning(f"未找到匹配「{search_query}」的诗歌。")
            st.info("💡 提示：可以尝试搜索作者名（如：李白、杜甫）或诗歌标题中的关键词")
            return
        st.success(f"找到 {len(filtered_poems)} 首匹配的诗歌")
    else:
        filtered_poems = poems
        st.info(f"显示全部 {len(filtered_poems)} 首诗歌（在搜索框输入关键词可进行筛选）")
    
    # Pagination
    poems_per_page = 5
    total_pages = (len(filtered_poems) + poems_per_page - 1) // poems_per_page
    
    # Initialize or reset page when search changes
    if 'last_search_query' not in st.session_state:
        st.session_state.last_search_query = search_query
        st.session_state.display_page = 0
    elif st.session_state.last_search_query != search_query:
        # Search query changed, reset to first page
        st.session_state.last_search_query = search_query
        st.session_state.display_page = 0
    
    if 'display_page' not in st.session_state:
        st.session_state.display_page = 0
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 上一页", disabled=(st.session_state.display_page == 0)):
            st.session_state.display_page -= 1
            st.rerun()
    with col2:
        st.write(f"**第 {st.session_state.display_page + 1} / {total_pages} 页**")
    with col3:
        if st.button("下一页 ▶", disabled=(st.session_state.display_page >= total_pages - 1)):
            st.session_state.display_page += 1
            st.rerun()
    
    # Display poems for current page
    start_idx = st.session_state.display_page * poems_per_page
    end_idx = min(start_idx + poems_per_page, len(filtered_poems))
    
    for i in range(start_idx, end_idx):
        poem = filtered_poems[i]
        with st.container():
            st.markdown(f"""
            <div class="poem-card">
                <div class="poem-title">{poem['title']}</div>
                <div class="poem-author">作者：{poem['author']} | 朝代：{poem['dynasty']}</div>
                <div class="poem-content">{poem['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.write("")


def quiz_mode():
    """Quiz mode: Test knowledge with questions."""
    st.header("🎯 测验模式")
    
    poems = load_poems()
    
    if not poems:
        st.error("无法加载诗歌数据。")
        return
    
    # Initialize quiz session
    if 'quiz_state' not in st.session_state:
        st.session_state.quiz_state = initialize_quiz_session(poems)
    
    quiz_state = st.session_state.quiz_state
    
    # Quiz type selection
    col1, col2 = st.columns(2)
    with col1:
        quiz_type = st.radio(
            "选择测验类型：",
            ["选择题", "填空题"],
            index=0 if quiz_state['quiz_type'] == 'multiple_choice' else 1,
            horizontal=True
        )
        quiz_state['quiz_type'] = 'multiple_choice' if quiz_type == '选择题' else 'fill_blank'
    
    with col2:
        if st.button("🔄 重新开始"):
            st.session_state.quiz_state = initialize_quiz_session(poems)
            st.rerun()
    
    # Score display
    if quiz_state['total_questions'] > 0:
        accuracy = (quiz_state['score'] / quiz_state['total_questions']) * 100
        st.metric("得分", f"{quiz_state['score']} / {quiz_state['total_questions']}", 
                 f"{accuracy:.1f}%")
    
    # Generate question if needed
    if quiz_state['current_question'] is None:
        quiz_state = get_next_question(poems, quiz_state)
        st.session_state.quiz_state = quiz_state
    
    # Display question
    st.markdown(f'<div class="quiz-question">{quiz_state["current_question"]}</div>', 
                unsafe_allow_html=True)
    
    # Answer input
    if quiz_state['quiz_type'] == 'multiple_choice':
        # Multiple choice
        options = quiz_state.get('options', [])
        selected_option = st.radio("选择答案：", options, key="quiz_option")
        
        if st.button("提交答案", type="primary"):
            is_correct = check_answer(quiz_state, selected_option)
            st.session_state.quiz_state = quiz_state
            
            if is_correct:
                st.success(f"✅ 正确！答案是：{quiz_state['correct_answer']}")
            else:
                st.error(f"❌ 错误。正确答案是：{quiz_state['correct_answer']}")
            
            st.session_state.quiz_state['answered'] = True
    
    else:  # fill_blank
        user_answer = st.text_input("请输入答案：", key="fill_blank_input")
        
        if st.button("提交答案", type="primary"):
            if user_answer:
                is_correct = check_answer(quiz_state, user_answer)
                st.session_state.quiz_state = quiz_state
                
                if is_correct:
                    st.success(f"✅ 正确！答案是：{quiz_state['correct_answer']}")
                else:
                    st.error(f"❌ 错误。正确答案是：{quiz_state['correct_answer']}")
                
                st.session_state.quiz_state['answered'] = True
            else:
                st.warning("请输入答案。")
    
    # Next question button
    if quiz_state.get('answered', False):
        if st.button("下一题 ➡", type="primary"):
            quiz_state = get_next_question(poems, quiz_state)
            st.session_state.quiz_state = quiz_state
            st.rerun()


def flashcard_mode():
    """Flashcard mode: Learn poems with flashcards."""
    st.header("🃏 闪卡模式")
    
    poems = load_poems()
    
    if not poems:
        st.error("无法加载诗歌数据。")
        return
    
    # Initialize flashcard session
    if 'flashcard_state' not in st.session_state:
        st.session_state.flashcard_state = initialize_flashcard_session(poems)
    
    flashcard_state = st.session_state.flashcard_state
    
    # Progress stats
    stats = get_progress_stats(flashcard_state)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总数", stats['total'])
    with col2:
        st.metric("已掌握", stats['known'], f"{stats['known_percentage']:.1f}%")
    with col3:
        st.metric("需练习", stats['practice'])
    with col4:
        st.metric("未学习", stats['remaining'])
    
    st.divider()
    
    # Current flashcard
    current_poem = get_current_flashcard(flashcard_state)
    
    if current_poem:
        # Flashcard front (title and author)
        st.markdown(f"""
        <div class="flashcard-front">
            <h2>{current_poem['title']}</h2>
            <p style="font-size: 1.2rem; margin-top: 1rem;">作者：{current_poem['author']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Reveal button
        if not flashcard_state['revealed']:
            if st.button("🔓 显示内容", type="primary", use_container_width=True):
                flashcard_state = reveal_content(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()
        else:
            # Show poem content
            st.markdown(f"""
            <div class="poem-card">
                <div class="poem-content">{current_poem['content']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Marking buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 已掌握", use_container_width=True, 
                           type="primary" if flashcard_state['current_index'] in flashcard_state['known_poems'] else "secondary"):
                    flashcard_state = mark_as_known(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()
            
            with col2:
                if st.button("📝 需练习", use_container_width=True,
                           type="primary" if flashcard_state['current_index'] in flashcard_state['practice_poems'] else "secondary"):
                    flashcard_state = mark_for_practice(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()
        
        # Navigation
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("◀ 上一张", use_container_width=True):
                flashcard_state = previous_flashcard(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()
        
        with col2:
            st.write(f"**{flashcard_state['current_index'] + 1} / {len(poems)}**")
        
        with col3:
            if st.button("下一张 ▶", use_container_width=True):
                flashcard_state = next_flashcard(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()


def main():
    """Main application entry point."""
    st.title("📚 唐诗三百首学习应用")
    st.markdown("---")
    
    # Mode selection in sidebar
    with st.sidebar:
        st.header("导航")
        mode = st.radio(
            "选择学习模式：",
            ["📖 浏览模式", "🎯 测验模式", "🃏 闪卡模式"],
            label_visibility="collapsed"
        )
    
    # Route to appropriate mode
    if "浏览模式" in mode:
        display_mode()
    elif "测验模式" in mode:
        quiz_mode()
    elif "闪卡模式" in mode:
        flashcard_mode()


if __name__ == "__main__":
    main()

