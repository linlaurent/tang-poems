"""Main Streamlit application for learning 300 Tang Poems."""

import json
from datetime import datetime

import streamlit as st
from pypinyin import lazy_pinyin

from src.analytics import (
    calculate_streaks,
    format_timeline_data,
    get_learning_timeline,
    get_poem_analytics,
    get_recommendations,
    get_study_stats,
)
from src.data_loader import load_poems, search_poems
from src.flashcards import (
    apply_filter,
    export_progress_data,
    get_all_authors,
    get_current_flashcard,
    get_current_poem_status,
    get_poems_by_author,
    get_progress_stats,
    import_progress_data,
    initialize_flashcard_session,
    jump_to_next_unknown,
    jump_to_poem,
    load_log,
    mark_as_known,
    mark_for_practice,
    next_flashcard,
    previous_flashcard,
    reset_progress,
    reveal_content,
    save_progress,
)
from src.quiz import check_answer, get_next_question, initialize_quiz_session

# Page configuration
st.set_page_config(
    page_title="唐诗三百首学习",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better Chinese font support
st.markdown(
    """
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
    .multi-progress-bar {
        width: 100%;
        height: 30px;
        background-color: #e0e0e0;
        border-radius: 15px;
        overflow: hidden;
        margin: 0.5rem 0;
        position: relative;
        display: flex;
        flex-direction: row;
    }
    .progress-segment-known {
        height: 100%;
        background-color: #4CAF50;
        transition: width 0.3s ease;
        min-width: 0;
    }
    .progress-segment-practice {
        height: 100%;
        background-color: #FF9800;
        transition: width 0.3s ease;
        min-width: 0;
    }
    .progress-segment-unknown {
        height: 100%;
        background-color: #e0e0e0;
        min-width: 0;
    }
    .progress-text {
        text-align: center;
        margin-top: 0.5rem;
        font-size: 0.9rem;
        color: #666;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_user_id() -> str:
    """
    Get or initialize user ID for per-user progress tracking.
    Tries to use Streamlit user email if available, otherwise uses session state.
    """
    # Check if user_id already exists in session state
    if (
        "user_id" in st.session_state
        and st.session_state.user_id
        and st.session_state.user_id != "guest"
    ):
        return st.session_state.user_id

    # Try to get user email from Streamlit (available in Streamlit Cloud)
    try:
        # In newer Streamlit versions, user info might be available
        # Check if st.user exists (Streamlit 1.28+)
        if hasattr(st, "user") and st.user is not None:
            user_email = st.user.email if hasattr(st.user, "email") else None
            if user_email:
                st.session_state.user_id = user_email
                return user_email
    except Exception:
        pass

    # If no user email available and no username set, return guest
    return "guest"


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
            key="poem_search_input",
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
        st.info(
            f"显示全部 {len(filtered_poems)} 首诗歌（在搜索框输入关键词可进行筛选）"
        )

    # Pagination
    poems_per_page = 5
    total_pages = (len(filtered_poems) + poems_per_page - 1) // poems_per_page

    # Initialize or reset page when search changes
    if "last_search_query" not in st.session_state:
        st.session_state.last_search_query = search_query
        st.session_state.display_page = 0
    elif st.session_state.last_search_query != search_query:
        # Search query changed, reset to first page
        st.session_state.last_search_query = search_query
        st.session_state.display_page = 0

    if "display_page" not in st.session_state:
        st.session_state.display_page = 0

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀ 上一页", disabled=(st.session_state.display_page == 0)):
            st.session_state.display_page -= 1
            st.rerun()
    with col2:
        st.write(f"**第 {st.session_state.display_page + 1} / {total_pages} 页**")
    with col3:
        if st.button(
            "下一页 ▶", disabled=(st.session_state.display_page >= total_pages - 1)
        ):
            st.session_state.display_page += 1
            st.rerun()

    # Display poems for current page
    start_idx = st.session_state.display_page * poems_per_page
    end_idx = min(start_idx + poems_per_page, len(filtered_poems))

    for i in range(start_idx, end_idx):
        poem = filtered_poems[i]
        with st.container():
            author_dynasty = f"作者：{poem['author']} | 朝代：{poem['dynasty']}"
            st.markdown(
                f"""
            <div class="poem-card">
                <div class="poem-title">{poem["title"]}</div>
                <div class="poem-author">{author_dynasty}</div>
                <div class="poem-content">{poem["content"]}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.write("")


def quiz_mode():
    """Quiz mode: Test knowledge with questions."""
    st.header("🎯 测验模式")

    poems = load_poems()

    if not poems:
        st.error("无法加载诗歌数据。")
        return

    # Initialize quiz session
    if "quiz_state" not in st.session_state:
        st.session_state.quiz_state = initialize_quiz_session(poems)

    quiz_state = st.session_state.quiz_state

    # Quiz type selection
    col1, col2 = st.columns(2)
    with col1:
        quiz_type = st.radio(
            "选择测验类型：",
            ["选择题", "填空题"],
            index=0 if quiz_state["quiz_type"] == "multiple_choice" else 1,
            horizontal=True,
        )
        quiz_state["quiz_type"] = (
            "multiple_choice" if quiz_type == "选择题" else "fill_blank"
        )

    with col2:
        if st.button("🔄 重新开始"):
            st.session_state.quiz_state = initialize_quiz_session(poems)
            st.rerun()

    # Score display
    if quiz_state["total_questions"] > 0:
        accuracy = (quiz_state["score"] / quiz_state["total_questions"]) * 100
        st.metric(
            "得分",
            f"{quiz_state['score']} / {quiz_state['total_questions']}",
            f"{accuracy:.1f}%",
        )

    # Generate question if needed
    if quiz_state["current_question"] is None:
        quiz_state = get_next_question(poems, quiz_state)
        st.session_state.quiz_state = quiz_state

    # Display question
    st.markdown(
        f'<div class="quiz-question">{quiz_state["current_question"]}</div>',
        unsafe_allow_html=True,
    )

    # Answer input
    if quiz_state["quiz_type"] == "multiple_choice":
        # Multiple choice
        options = quiz_state.get("options", [])
        selected_option = st.radio("选择答案：", options, key="quiz_option")

        if st.button("提交答案", type="primary"):
            is_correct = check_answer(quiz_state, selected_option)
            st.session_state.quiz_state = quiz_state

            if is_correct:
                st.success(f"✅ 正确！答案是：{quiz_state['correct_answer']}")
            else:
                st.error(f"❌ 错误。正确答案是：{quiz_state['correct_answer']}")

            st.session_state.quiz_state["answered"] = True

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

                st.session_state.quiz_state["answered"] = True
            else:
                st.warning("请输入答案。")

    # Next question button
    if quiz_state.get("answered", False):
        if st.button("下一题 ➡", type="primary"):
            quiz_state = get_next_question(poems, quiz_state)
            st.session_state.quiz_state = quiz_state
            st.rerun()


def flashcard_mode():
    """Flashcard mode: Learn poems with flashcards."""
    st.header("🃏 闪卡模式")

    # Get user ID for per-user progress tracking
    user_id = get_user_id()

    # Ensure user_id is always a valid string
    if not user_id or not isinstance(user_id, str):
        user_id = "guest"

    # Show warning if using guest mode
    if user_id == "guest":
        st.warning("⚠️ 您当前以访客模式使用。请在侧边栏输入用户名以保存学习进度。")

    poems = load_poems()

    if not poems:
        st.error("无法加载诗歌数据。")
        return

    # Initialize flashcard session with user_id
    # Check if we need to reinitialize (first time or user changed)
    needs_reinit = False
    if "flashcard_state" not in st.session_state:
        needs_reinit = True
    else:
        # Check if user_id matches (handle old sessions without user_id)
        existing_user_id = (
            st.session_state.flashcard_state.get("user_id")
            if isinstance(st.session_state.flashcard_state, dict)
            else None
        )
        if existing_user_id != user_id:
            needs_reinit = True

    if needs_reinit:
        # User changed or first time, reinitialize
        try:
            # Ensure poems is a list and user_id is a string
            if not isinstance(poems, list):
                st.error("诗歌数据格式错误。")
                return
            if not isinstance(user_id, str):
                user_id = "guest"

            st.session_state.flashcard_state = initialize_flashcard_session(
                poems, user_id
            )
            # Initialize filtered indices
            st.session_state.flashcard_state = apply_filter(
                st.session_state.flashcard_state
            )
        except Exception as e:
            st.error(f"初始化闪卡会话时出错: {str(e)}")
            import traceback

            st.code(traceback.format_exc())
            return

        # Show message if progress was loaded
        if "last_saved" in st.session_state.flashcard_state:
            last_saved = st.session_state.flashcard_state["last_saved"]
            if last_saved:
                try:
                    # Parse and format the timestamp
                    dt = datetime.fromisoformat(last_saved)
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                    st.success(f"✅ 已恢复之前的进度 (最后保存: {formatted_time})")
                except Exception:
                    st.success("✅ 已恢复之前的进度")

    flashcard_state = st.session_state.flashcard_state

    # Handle jump from analytics
    if "jump_to_index" in st.session_state:
        jump_idx = st.session_state.pop("jump_to_index")
        if 0 <= jump_idx < len(poems):
            flashcard_state = jump_to_poem(flashcard_state, jump_idx, save=False)
            st.session_state.flashcard_state = flashcard_state
            st.rerun()

    # Progress stats
    stats = get_progress_stats(flashcard_state)

    # Main stats row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("总数", stats["total"])
    with col2:
        st.metric("已掌握", stats["known"], f"{stats['known_percentage']:.1f}%")
    with col3:
        st.metric("需练习", stats["practice"])
    with col4:
        st.metric("未学习", stats["remaining"])
    with col5:
        st.metric("本次学习", stats.get("study_count", 0))

    # Progress bar with known and practice segments
    if stats["total"] > 0:
        known_pct = stats["known_percentage"]
        practice_pct = stats["practice_percentage"]
        unknown_pct = 100 - known_pct - practice_pct

        # Create custom multi-segment progress bar
        known_title = f"已掌握: {stats['known']}首"
        practice_title = f"需练习: {stats['practice']}首"
        unknown_title = f"未学习: {stats['remaining']}首"

        known_text = (
            f"<span style='color: #4CAF50;'>●</span> "
            f"已掌握 {stats['known']}/{stats['total']} "
            f"({known_pct:.1f}%)"
        )
        practice_text = (
            f"<span style='color: #FF9800;'>●</span> "
            f"需练习 {stats['practice']}/{stats['total']} "
            f"({practice_pct:.1f}%)"
        )
        unknown_text = (
            f"<span style='color: #9E9E9E;'>●</span> "
            f"未学习 {stats['remaining']}/{stats['total']} "
            f"({unknown_pct:.1f}%)"
        )

        progress_bar_html = f"""
        <div class="multi-progress-bar">
            <div class="progress-segment-known"
                 style="width: {known_pct}%;"
                 title="{known_title}"></div>
            <div class="progress-segment-practice"
                 style="width: {practice_pct}%;"
                 title="{practice_title}"></div>
            <div class="progress-segment-unknown"
                 style="width: {unknown_pct}%;"
                 title="{unknown_title}"></div>
        </div>
        <div class="progress-text">
            学习进度: {known_text} | {practice_text} | {unknown_text}
        </div>
        """
        st.markdown(progress_bar_html, unsafe_allow_html=True)

    # Navigation and Filter section
    st.divider()
    # Ensure shuffle is always enabled
    if not flashcard_state.get("shuffle", True):
        flashcard_state["shuffle"] = True
        flashcard_state = apply_filter(flashcard_state)
        st.session_state.flashcard_state = flashcard_state

    # Navigation controls: Filter mode, Author dropdown, Poem dropdown, and Search
    st.subheader("🔍 快速导航")

    nav_col1, nav_col2 = st.columns([1, 3])

    with nav_col1:
        # Filter mode
        st.write("**筛选模式**")
        filter_mode = st.selectbox(
            "筛选",
            ["all", "practice", "unknown", "known"],
            format_func=lambda x: {
                "all": "全部",
                "practice": "需练习",
                "unknown": "未学习",
                "known": "已掌握",
            }[x],
            index=["all", "practice", "unknown", "known"].index(
                flashcard_state.get("filter_mode", "all")
            ),
            label_visibility="collapsed",
            key="filter_mode_select",
        )
        if filter_mode != flashcard_state.get("filter_mode"):
            flashcard_state["filter_mode"] = filter_mode
            flashcard_state = apply_filter(flashcard_state)
            st.session_state.flashcard_state = flashcard_state
            st.rerun()

    with nav_col2:
        # Search box
        search_query = st.text_input(
            "搜索诗歌（标题、作者或内容）",
            placeholder="输入关键词...",
            key="flashcard_search",
        )

        if search_query and search_query.strip():
            search_results = search_poems(poems, search_query)
            if search_results:
                # Find indices of search results by matching title and author
                result_data = []  # List of (idx, title, author)
                seen = set()

                for poem in search_results:
                    poem_title = poem.get("title", "")
                    poem_author = poem.get("author", "")
                    poem_key = (poem_title, poem_author)

                    if poem_key in seen:
                        continue
                    seen.add(poem_key)

                    # Find the index in original poems list
                    for idx, p in enumerate(poems):
                        if (
                            p.get("title", "") == poem_title
                            and p.get("author", "") == poem_author
                        ):
                            result_data.append((idx, poem_title, poem_author))
                            break

                # Sort by title pinyin
                result_data.sort(key=lambda x: "".join(lazy_pinyin(x[1])))

                if result_data:
                    result_indices = [idx for idx, _, _ in result_data]
                    result_options = [
                        f"{title} - {author}" for idx, title, author in result_data
                    ]

                    st.write(f"找到 {len(result_options)} 首匹配的诗歌：")
                    selected_search_result = st.selectbox(
                        "选择诗歌",
                        result_options,
                        key="search_result_select_flashcard",
                        label_visibility="collapsed",
                    )

                    if st.button(
                        "📍 跳转到此诗",
                        width="stretch",
                        key="jump_search_result",
                    ):
                        selected_option_idx = result_options.index(
                            selected_search_result
                        )
                        selected_idx = result_indices[selected_option_idx]
                        flashcard_state = jump_to_poem(flashcard_state, selected_idx)
                        st.session_state.flashcard_state = flashcard_state
                        st.rerun()
            else:
                st.info("未找到匹配的诗歌")

    # Collapsible section for Author and Title selection
    with st.expander("📋 高级导航（按作者/标题选择）", expanded=False):
        adv_nav_col1, adv_nav_col2 = st.columns(2)

        with adv_nav_col1:
            # Author dropdown
            all_authors = get_all_authors(poems)
            current_poem = get_current_flashcard(flashcard_state)
            current_author = (
                current_poem.get("author", "未知") if current_poem else "未知"
            )

            # Determine default index for author dropdown
            author_default_idx = 0
            if current_author in all_authors:
                author_default_idx = all_authors.index(current_author) + 1

            selected_author = st.selectbox(
                "按作者选择",
                ["全部"] + all_authors,
                index=author_default_idx,
                key="author_select_flashcard",
            )

            if selected_author != "全部":
                # Get poems by this author
                author_poems_indices = get_poems_by_author(poems, selected_author)
                if author_poems_indices:
                    # Create options with titles (no ID)
                    author_poem_options = [
                        poems[idx].get("title", "无题") for idx in author_poems_indices
                    ]
                    # Find current poem index in the list if author matches
                    selected_poem_idx_in_list = 0
                    if current_author == selected_author and current_poem:
                        current_id = flashcard_state.get("current_id", "")
                        if current_id:
                            # Find current poem's index
                            from src.data_loader import get_poem_index_by_id

                            current_idx = get_poem_index_by_id(poems, current_id)
                            if (
                                current_idx is not None
                                and current_idx in author_poems_indices
                            ):
                                selected_poem_idx_in_list = author_poems_indices.index(
                                    current_idx
                                )

                    selected_poem_option = st.selectbox(
                        f"选择诗歌 ({len(author_poem_options)} 首)",
                        author_poem_options,
                        index=selected_poem_idx_in_list,
                        key="poem_select_by_author_flashcard",
                    )

                    if st.button(
                        "📍 跳转到此诗",
                        width="stretch",
                        key="jump_author_poem",
                    ):
                        # Extract index from selection
                        option_idx = author_poem_options.index(selected_poem_option)
                        selected_idx = author_poems_indices[option_idx]
                        flashcard_state = jump_to_poem(flashcard_state, selected_idx)
                        st.session_state.flashcard_state = flashcard_state
                        st.rerun()
                else:
                    st.info("该作者暂无诗歌")

        with adv_nav_col2:
            # Poem title dropdown (all poems) - sorted by title pinyin
            # Create list with (index, title, author) for sorting
            poem_data = [
                (idx, poem.get("title", "无题"), poem.get("author", "未知"))
                for idx, poem in enumerate(poems)
            ]
            # Sort by title pinyin
            poem_data.sort(key=lambda x: "".join(lazy_pinyin(x[1])))

            # Create options without IDs
            poem_options = [
                f"{title} - {author}" for orig_idx, title, author in poem_data
            ]

            # Map option index to original poem index
            poem_index_map = [orig_idx for orig_idx, _, _ in poem_data]

            current_id = flashcard_state.get("current_id", "")
            # Find current poem in sorted list
            current_option_idx = 0
            if current_id:
                from src.data_loader import get_poem_index_by_id

                current_idx = get_poem_index_by_id(poems, current_id)
                if current_idx is not None:
                    try:
                        current_option_idx = poem_index_map.index(current_idx)
                    except ValueError:
                        current_option_idx = 0

            selected_poem = st.selectbox(
                "按标题搜索",
                poem_options,
                index=current_option_idx,
                key="poem_select_all_flashcard",
            )

            if st.button("📍 跳转到此诗", width="stretch", key="jump_all_poem"):
                selected_option_idx = poem_options.index(selected_poem)
                selected_idx = poem_index_map[selected_option_idx]
                flashcard_state = jump_to_poem(flashcard_state, selected_idx)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

    st.divider()

    # Show filtered count
    filtered_ids = flashcard_state.get("filtered_ids", [])
    if flashcard_state.get("filter_mode", "all") != "all":
        st.info(f"📋 当前筛选：显示 {len(filtered_ids)} 首诗歌")

    # Current flashcard
    current_poem = get_current_flashcard(flashcard_state)
    current_status = get_current_poem_status(flashcard_state)

    if current_poem:
        # Status indicator
        status_colors = {
            "known": "#4CAF50",
            "practice": "#FF9800",
            "unknown": "#9E9E9E",
        }
        status_texts = {
            "known": "✅ 已掌握",
            "practice": "📝 需练习",
            "unknown": "❓ 未学习",
        }
        status_color = status_colors.get(current_status, "#9E9E9E")
        status_text = status_texts.get(current_status, "❓ 未学习")

        # Flashcard front (title and author)
        status_div_style = (
            "text-align: right; font-size: 0.9rem; opacity: 0.9; margin-bottom: 0.5rem;"
        )
        author_style = "font-size: 1.2rem; margin-top: 1rem;"
        st.markdown(
            f"""
        <div class="flashcard-front" style="border-left: 5px solid {status_color};">
            <div style="{status_div_style}">
                {status_text}
            </div>
            <h2>{current_poem["title"]}</h2>
            <p style="{author_style}">作者：{current_poem["author"]}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Reveal button
        if not flashcard_state["revealed"]:
            if st.button("🔓 显示内容", type="primary", width="stretch"):
                flashcard_state = reveal_content(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()
        else:
            # Show poem content
            st.markdown(
                f"""
            <div class="poem-card">
                <div class="poem-content">{current_poem["content"]}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Marking buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "✅ 已掌握",
                    width="stretch",
                    type="primary"
                    if flashcard_state.get("current_id", "")
                    in flashcard_state["known_poems"]
                    else "secondary",
                ):
                    flashcard_state = mark_as_known(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()

            with col2:
                if st.button(
                    "📝 需练习",
                    width="stretch",
                    type="primary"
                    if flashcard_state.get("current_id", "")
                    in flashcard_state["practice_poems"]
                    else "secondary",
                ):
                    flashcard_state = mark_for_practice(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()

        # Navigation
        filtered_ids = flashcard_state.get("filtered_ids", [])
        if not filtered_ids:
            # Fallback: get all poem IDs
            filtered_ids = [poem.get("id") for poem in poems if poem.get("id")]

        if filtered_ids:
            try:
                current_id = flashcard_state.get("current_id", "")
                current_pos = filtered_ids.index(current_id) + 1
                total_filtered = len(filtered_ids)
            except ValueError:
                current_pos = 1
                total_filtered = len(filtered_ids)
        else:
            current_pos = 0
            total_filtered = 0

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            if st.button("◀ 上一张", width="stretch", disabled=(not filtered_ids)):
                flashcard_state = previous_flashcard(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

        with col2:
            if filtered_ids:
                st.write(f"**{current_pos} / {total_filtered}**")
                if flashcard_state.get("filter_mode", "all") != "all":
                    # Get current poem index for display
                    from src.data_loader import get_poem_index_by_id

                    current_id = flashcard_state.get("current_id", "")
                    current_idx = get_poem_index_by_id(poems, current_id)
                    if current_idx is not None:
                        st.caption(f"(总第 {current_idx + 1} 首)")
            else:
                st.write("**0 / 0**")
                st.warning("当前筛选模式下无诗歌")

        with col3:
            if st.button("下一张 ▶", width="stretch", disabled=(not filtered_ids)):
                flashcard_state = next_flashcard(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

        with col4:
            if st.button("🔍 跳到下一首未学习", width="stretch"):
                flashcard_state = jump_to_next_unknown(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

    # Export and Import section - hidden in expander
    with st.expander("📤 导出/导入进度", expanded=False):
        exp_col1, exp_col2, exp_col3 = st.columns(3)

        with exp_col1:
            # Export progress
            export_data = export_progress_data(flashcard_state)
            export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
            # Sanitize user_id for filename
            safe_user_id = "".join(
                c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flashcard_progress_{safe_user_id}_{timestamp}.json"
            st.download_button(
                label="📥 导出进度",
                data=export_json,
                file_name=filename,
                mime="application/json",
                width="stretch",
                help="下载当前学习进度为JSON文件",
            )

        with exp_col2:
            # Import progress
            uploaded_file = st.file_uploader(
                "📤 导入进度",
                type=["json"],
                help="选择之前导出的进度JSON文件",
                key="import_progress_file",
            )

            if uploaded_file is not None:
                try:
                    import_data = json.load(uploaded_file)

                    # Validate import data structure
                    if not isinstance(import_data, dict):
                        st.error("❌ 无效的进度文件格式")
                    else:
                        # Show preview of what will be imported
                        known_count = (
                            len(import_data.get("known_poems", []))
                            if isinstance(import_data.get("known_poems"), list)
                            else 0
                        )
                        practice_count = (
                            len(import_data.get("practice_poems", []))
                            if isinstance(import_data.get("practice_poems"), list)
                            else 0
                        )
                        st.info(
                            f"📋 将导入: {known_count} 首已掌握, "
                            f"{practice_count} 首需练习"
                        )

                        if st.button(
                            "✅ 确认导入",
                            width="stretch",
                            key="confirm_import",
                        ):
                            # Import the data
                            flashcard_state = import_progress_data(
                                flashcard_state, import_data, poems
                            )
                            flashcard_state = apply_filter(flashcard_state)
                            st.session_state.flashcard_state = flashcard_state

                            # Save the imported progress
                            if save_progress(flashcard_state):
                                st.success("✅ 进度已成功导入并保存")
                            else:
                                st.warning("⚠️ 进度已导入，但保存失败（可能是访客模式）")
                            st.rerun()
                except json.JSONDecodeError:
                    st.error("❌ 文件格式错误：不是有效的JSON文件")
                except Exception as e:
                    st.error(f"❌ 导入失败: {str(e)}")

        with exp_col3:
            # Reset progress button
            if st.button(
                "🔄 重置所有进度",
                width="stretch",
                type="secondary",
            ):
                if st.session_state.get("confirm_reset", False):
                    flashcard_state = reset_progress(flashcard_state)
                    flashcard_state = apply_filter(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.session_state.confirm_reset = False
                    st.success("✅ 进度已重置")
                    st.rerun()
                else:
                    st.session_state.confirm_reset = True
                    st.warning("⚠️ 再次点击确认重置所有进度（这将删除保存的进度文件）")

        if st.session_state.get("confirm_reset", False):
            st.info("⚠️ 点击上方的'重置所有进度'按钮以确认重置")


def analytics_mode():
    """Analytics mode: Display learning analytics and insights."""
    st.header("📊 数据分析")

    # Get user ID
    user_id = get_user_id()

    if user_id == "guest":
        st.warning("⚠️ 访客模式无法查看数据分析。请登录以保存学习进度并生成分析。")
        return

    # Load poems and logs
    poems = load_poems()
    if not poems:
        st.error("无法加载诗歌数据。")
        return

    log_entries = load_log(user_id)

    if not log_entries:
        st.info(
            "📝 您还没有学习数据。开始使用闪卡模式学习诗歌，"
            "系统会自动记录您的学习进度并生成分析。"
        )
        return

    # Initialize flashcard state to get current progress
    flashcard_state = initialize_flashcard_session(poems, user_id)

    # Calculate analytics
    timeline = get_learning_timeline(log_entries)
    study_stats = get_study_stats(log_entries)
    poem_analytics = get_poem_analytics(log_entries, poems)
    recommendations = get_recommendations(log_entries, flashcard_state, poems)

    # Update distribution from current state
    current_stats = get_progress_stats(flashcard_state)
    poem_analytics["distribution"] = {
        "known": current_stats["known"],
        "practice": current_stats["practice"],
        "unknown": current_stats["remaining"],
    }

    # Overview Metrics Section
    st.subheader("📈 概览指标")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("已掌握诗歌", current_stats["known"])

    with col2:
        st.metric("需练习诗歌", current_stats["practice"])

    with col3:
        st.metric("学习天数", study_stats["total_sessions"])

    with col4:
        st.metric("当前连续", f"{study_stats['current_streak']} 天")

    with col5:
        st.metric("最长连续", f"{study_stats['longest_streak']} 天")

    # Additional stats row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("平均每天学习", f"{study_stats['average_poems_per_session']:.1f} 首")
    with col2:
        streak_info = calculate_streaks(log_entries)
        first_date = streak_info.get("first_activity")
        if first_date:
            try:
                first_dt = datetime.fromisoformat(first_date)
                days_active = (datetime.now().date() - first_dt.date()).days + 1
                st.metric("总学习天数", days_active)
            except (ValueError, AttributeError):
                st.metric("总学习天数", "N/A")
        else:
            st.metric("总学习天数", "N/A")
    with col3:
        st.metric("总学习次数", study_stats["total_events"])

    st.divider()

    # Learning Progress Timeline Section
    st.subheader("📅 学习进度时间线")

    if timeline:
        cumulative_df, daily_df = format_timeline_data(timeline)

        # Cumulative progress chart
        st.write("**累计学习进度**")
        if cumulative_df is not None:
            try:
                st.line_chart(
                    cumulative_df.set_index("日期")[["累计已掌握", "累计学习"]]
                )
            except Exception:
                # Fallback if pandas not available
                st.info("需要 pandas 库来显示图表")

        # Daily activity chart
        st.write("**每日学习活动**")
        if daily_df is not None:
            try:
                st.bar_chart(daily_df.set_index("日期")[["已掌握", "需练习"]])
            except Exception:
                st.info("需要 pandas 库来显示图表")

        # Most active days
        if study_stats["most_active_days"]:
            st.write("**最活跃的学习日**")
            for day_info in study_stats["most_active_days"][:5]:
                st.write(f"- {day_info['date']}: {day_info['count']} 首诗歌")
    else:
        st.info("暂无时间线数据")

    st.divider()

    # Poem-Level Analytics Section
    st.subheader("📚 诗歌级别分析")

    # Most studied poems
    if poem_analytics["most_studied"]:
        st.write("**学习次数最多的诗歌**")
        most_studied_data = []
        for item in poem_analytics["most_studied"][:10]:
            poem_id = item["poem_id"]
            poem = next((p for p in poems if p.get("id") == poem_id), None)
            if poem:
                most_studied_data.append(
                    {
                        "标题": poem.get("title", "未知"),
                        "作者": poem.get("author", "未知"),
                        "状态变化次数": item["change_count"],
                    }
                )

        if most_studied_data:
            st.dataframe(most_studied_data, width="stretch", hide_index=True)

    # Poems needing attention (in practice > 7 days)
    practice_poems = flashcard_state.get("practice_poems", set())
    if practice_poems:
        st.write("**需要关注的诗歌（在练习列表中超过7天）**")
        needs_attention = [
            rec for rec in recommendations if rec.get("type") == "review_practice"
        ]
        if needs_attention:
            attention_data = []
            for rec in needs_attention[:10]:
                poem_id = rec.get("poem_id")
                poem = next((p for p in poems if p.get("id") == poem_id), None)
                if poem:
                    attention_data.append(
                        {
                            "标题": poem.get("title", "未知"),
                            "作者": poem.get("author", "未知"),
                            "在练习列表天数": rec.get("days_in_practice", 0),
                        }
                    )
            if attention_data:
                st.dataframe(attention_data, width="stretch", hide_index=True)
        else:
            st.info("所有练习列表中的诗歌都是最近添加的")

    st.divider()

    # Recommendations Section
    st.subheader("💡 学习建议")

    if recommendations:
        for rec in recommendations[:10]:  # Show top 10
            rec_type = rec.get("type", "")
            priority = rec.get("priority", "low")
            message = rec.get("message", "")

            # Color code by priority
            if priority == "high":
                st.warning(f"🔴 **高优先级**: {message}")
            elif priority == "medium":
                st.info(f"🟡 **中优先级**: {message}")
            else:
                st.success(f"🟢 **建议**: {message}")

            # Add jump-to action for poem-specific recommendations
            poem_id = rec.get("poem_id")
            if poem_id and rec_type == "review_practice":
                poem_title = next(
                    (p.get("title", "") for p in poems if p.get("id") == poem_id),
                    "此诗",
                )
                if st.button(
                    f"📍 跳转到《{poem_title}》",
                    key=f"jump_rec_{poem_id}",
                ):
                    # Store in session state to trigger jump
                    st.session_state["analytics_jump_to"] = poem_id
                    st.rerun()
    else:
        st.info("暂无建议。继续学习以生成个性化建议！")

    # Handle jump-to action from recommendations
    if "analytics_jump_to" in st.session_state:
        jump_poem_id = st.session_state.pop("analytics_jump_to")
        # Switch to flashcard mode and jump to poem
        poem_idx = next(
            (i for i, p in enumerate(poems) if p.get("id") == jump_poem_id),
            None,
        )
        if poem_idx is not None:
            st.session_state["switch_to_flashcard"] = True
            st.session_state["jump_to_index"] = poem_idx

    st.divider()

    # Export Section
    st.subheader("📤 导出数据")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    col1, col2 = st.columns(2)

    with col1:
        # Export analytics as JSON
        analytics_export = {
            "user_id": user_id,
            "exported_at": datetime.now().isoformat(),
            "study_stats": study_stats,
            "poem_analytics": {
                "most_studied": poem_analytics["most_studied"],
                "distribution": poem_analytics["distribution"],
            },
            "recommendations": recommendations,
        }
        export_json = json.dumps(analytics_export, ensure_ascii=False, indent=2)
        filename = f"analytics_{user_id}_{timestamp}.json"
        st.download_button(
            label="📥 导出分析数据 (JSON)",
            data=export_json,
            file_name=filename,
            mime="application/json",
            width="stretch",
        )

    with col2:
        # Export timeline as CSV
        if timeline and daily_df is not None:
            try:
                csv_data = daily_df.to_csv(index=False)
                csv_filename = f"timeline_{user_id}_{timestamp}.csv"
                st.download_button(
                    label="📥 导出时间线 (CSV)",
                    data=csv_data,
                    file_name=csv_filename,
                    mime="text/csv",
                    width="stretch",
                )
            except Exception:
                st.info("CSV导出需要pandas库")


def main():
    """Main application entry point."""
    st.title("📚 唐诗三百首学习应用")
    st.markdown("---")

    # Get user ID (needed for flashcard mode)
    user_id = get_user_id()

    # Mode selection in sidebar
    with st.sidebar:
        st.header("导航")

        # Show current user and username input if needed
        if user_id != "guest":
            st.info(f"👤 当前用户: {user_id}")
        else:
            # Show username input for guest users
            st.info("👤 请输入用户名以保存学习进度")
            username = st.text_input(
                "用户名",
                value="",
                placeholder="输入您的用户名...",
                key="username_input",
            )

            if username and username.strip():
                st.session_state.user_id = username.strip()
                st.success(f"✅ 已登录: {username.strip()}")
                st.rerun()
            else:
                st.warning("⚠️ 访客模式：进度不会保存")

        mode = st.radio(
            "选择学习模式：",
            ["🃏 闪卡模式", "📖 浏览模式", "🎯 测验模式", "📊 数据分析"],
            label_visibility="collapsed",
        )

    # Handle mode switching from analytics
    if st.session_state.get("switch_to_flashcard", False):
        st.session_state["switch_to_flashcard"] = False
        mode = "🃏 闪卡模式"

    # Route to appropriate mode
    if "闪卡模式" in mode:
        flashcard_mode()
    elif "浏览模式" in mode:
        display_mode()
    elif "测验模式" in mode:
        quiz_mode()
    elif "数据分析" in mode:
        analytics_mode()


if __name__ == "__main__":
    main()
