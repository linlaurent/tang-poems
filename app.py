"""Main Streamlit application for learning 300 Tang Poems."""

import streamlit as st
import json
from datetime import datetime
from src.data_loader import load_poems, search_poems
from src.quiz import initialize_quiz_session, get_next_question, check_answer
from src.flashcards import (
    initialize_flashcard_session,
    get_current_flashcard,
    next_flashcard,
    previous_flashcard,
    mark_as_known,
    mark_for_practice,
    reveal_content,
    get_progress_stats,
    apply_filter,
    jump_to_next_practice,
    jump_to_next_unknown,
    reset_progress,
    get_current_poem_status,
    get_filtered_indices,
    save_progress,
    jump_to_poem,
    get_all_authors,
    get_poems_by_author,
    export_progress_data,
    import_progress_data,
)
from pypinyin import lazy_pinyin

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
    except:
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
            st.markdown(
                f"""
            <div class="poem-card">
                <div class="poem-title">{poem["title"]}</div>
                <div class="poem-author">作者：{poem["author"]} | 朝代：{poem["dynasty"]}</div>
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
                except:
                    st.success("✅ 已恢复之前的进度")

    flashcard_state = st.session_state.flashcard_state

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

    # Progress bar
    if stats["total"] > 0:
        progress_pct = stats["known_percentage"] / 100
        st.progress(
            progress_pct,
            text=f"学习进度: {stats['known']}/{stats['total']} ({stats['known_percentage']:.1f}%) | 需练习: {stats['practice']}/{stats['total']} ({stats['practice_percentage']:.1f}%)",
        )

    # Filter and options
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filter_mode = st.selectbox(
            "筛选模式",
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
        )
        if filter_mode != flashcard_state.get("filter_mode"):
            flashcard_state["filter_mode"] = filter_mode
            flashcard_state = apply_filter(flashcard_state)
            st.session_state.flashcard_state = flashcard_state
            st.rerun()

    with col2:
        shuffle = st.checkbox("随机顺序", value=flashcard_state.get("shuffle", False))
        if shuffle != flashcard_state.get("shuffle"):
            flashcard_state["shuffle"] = shuffle
            flashcard_state = apply_filter(flashcard_state)
            st.session_state.flashcard_state = flashcard_state
            st.rerun()

    with col3:
        if st.button("📋 跳到下一首需练习", use_container_width=True):
            flashcard_state = jump_to_next_practice(flashcard_state)
            st.session_state.flashcard_state = flashcard_state
            st.rerun()

    with col4:
        if st.button("💾 手动保存", use_container_width=True):
            if save_progress(flashcard_state):
                st.success("✅ 进度已保存")
            else:
                st.error("❌ 保存失败")

    st.divider()

    # Navigation controls: Author dropdown, Poem dropdown, and Search
    st.subheader("🔍 快速导航")

    nav_col1, nav_col2, nav_col3 = st.columns(3)

    with nav_col1:
        # Author dropdown
        all_authors = get_all_authors(poems)
        current_poem = get_current_flashcard(flashcard_state)
        current_author = current_poem.get("author", "未知") if current_poem else "未知"

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
                    current_idx = flashcard_state.get("current_index", 0)
                    if current_idx in author_poems_indices:
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
                    "📍 跳转到此诗", use_container_width=True, key="jump_author_poem"
                ):
                    # Extract index from selection
                    option_idx = author_poem_options.index(selected_poem_option)
                    selected_idx = author_poems_indices[option_idx]
                    flashcard_state = jump_to_poem(flashcard_state, selected_idx)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()
            else:
                st.info("该作者暂无诗歌")

    with nav_col2:
        # Poem title dropdown (all poems) - sorted by title pinyin
        # Create list with (index, title, author) for sorting
        poem_data = [
            (idx, poem.get("title", "无题"), poem.get("author", "未知"))
            for idx, poem in enumerate(poems)
        ]
        # Sort by title pinyin
        poem_data.sort(key=lambda x: "".join(lazy_pinyin(x[1])))

        # Create options without IDs
        poem_options = [f"{title} - {author}" for orig_idx, title, author in poem_data]

        # Map option index to original poem index
        poem_index_map = [orig_idx for orig_idx, _, _ in poem_data]

        current_idx = flashcard_state.get("current_index", 0)
        # Find current poem in sorted list
        current_option_idx = 0
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

        if st.button("📍 跳转到此诗", use_container_width=True, key="jump_all_poem"):
            selected_option_idx = poem_options.index(selected_poem)
            selected_idx = poem_index_map[selected_option_idx]
            flashcard_state = jump_to_poem(flashcard_state, selected_idx)
            st.session_state.flashcard_state = flashcard_state
            st.rerun()

    with nav_col3:
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
                        use_container_width=True,
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
        else:
            st.info("在搜索框中输入关键词")

    st.divider()

    # Show filtered count
    filtered_indices = flashcard_state.get("filtered_indices", [])
    if flashcard_state.get("filter_mode", "all") != "all":
        st.info(f"📋 当前筛选：显示 {len(filtered_indices)} 首诗歌")

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
        st.markdown(
            f"""
        <div class="flashcard-front" style="border-left: 5px solid {status_color};">
            <div style="text-align: right; font-size: 0.9rem; opacity: 0.9; margin-bottom: 0.5rem;">
                {status_text}
            </div>
            <h2>{current_poem["title"]}</h2>
            <p style="font-size: 1.2rem; margin-top: 1rem;">作者：{current_poem["author"]}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Reveal button
        if not flashcard_state["revealed"]:
            if st.button("🔓 显示内容", type="primary", use_container_width=True):
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
                    use_container_width=True,
                    type="primary"
                    if flashcard_state["current_index"]
                    in flashcard_state["known_poems"]
                    else "secondary",
                ):
                    flashcard_state = mark_as_known(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()

            with col2:
                if st.button(
                    "📝 需练习",
                    use_container_width=True,
                    type="primary"
                    if flashcard_state["current_index"]
                    in flashcard_state["practice_poems"]
                    else "secondary",
                ):
                    flashcard_state = mark_for_practice(flashcard_state)
                    st.session_state.flashcard_state = flashcard_state
                    st.rerun()

        # Navigation
        filtered_indices = flashcard_state.get(
            "filtered_indices", list(range(len(poems)))
        )
        if filtered_indices:
            try:
                current_pos = (
                    filtered_indices.index(flashcard_state["current_index"]) + 1
                )
                total_filtered = len(filtered_indices)
            except ValueError:
                current_pos = 1
                total_filtered = len(filtered_indices)
        else:
            current_pos = 0
            total_filtered = 0

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            if st.button(
                "◀ 上一张", use_container_width=True, disabled=(not filtered_indices)
            ):
                flashcard_state = previous_flashcard(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

        with col2:
            if filtered_indices:
                st.write(f"**{current_pos} / {total_filtered}**")
                if flashcard_state.get("filter_mode", "all") != "all":
                    st.caption(f"(总第 {flashcard_state['current_index'] + 1} 首)")
            else:
                st.write("**0 / 0**")
                st.warning("当前筛选模式下无诗歌")

        with col3:
            if st.button(
                "下一张 ▶", use_container_width=True, disabled=(not filtered_indices)
            ):
                flashcard_state = next_flashcard(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

        with col4:
            if st.button("🔍 跳到下一首未学习", use_container_width=True):
                flashcard_state = jump_to_next_unknown(flashcard_state)
                st.session_state.flashcard_state = flashcard_state
                st.rerun()

    # Export and Import section at the end of the page
    st.divider()
    st.subheader("📤 导出/导入进度")
    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        # Export progress
        export_data = export_progress_data(flashcard_state)
        export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
        # Sanitize user_id for filename
        safe_user_id = "".join(
            c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id
        )
        filename = f"flashcard_progress_{safe_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        st.download_button(
            label="📥 导出进度",
            data=export_json,
            file_name=filename,
            mime="application/json",
            use_container_width=True,
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
                        f"📋 将导入: {known_count} 首已掌握, {practice_count} 首需练习"
                    )

                    if st.button(
                        "✅ 确认导入", use_container_width=True, key="confirm_import"
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
        if st.button("🔄 重置所有进度", use_container_width=True, type="secondary"):
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
            ["🃏 闪卡模式", "📖 浏览模式", "🎯 测验模式"],
            label_visibility="collapsed",
        )

    # Route to appropriate mode
    if "闪卡模式" in mode:
        flashcard_mode()
    elif "浏览模式" in mode:
        display_mode()
    elif "测验模式" in mode:
        quiz_mode()


if __name__ == "__main__":
    main()
