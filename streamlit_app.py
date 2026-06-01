import random
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
    AUTO_REFRESH_AVAILABLE = True
except ImportError:
    AUTO_REFRESH_AVAILABLE = False


st.set_page_config(
    page_title="Vibe Bingo",
    page_icon="🎲",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# Preset word sets
# -----------------------------
PRESETS = {
    "Country Bingo": [
        "Germany",
        "France",
        "Italy",
        "Netherlands",
        "England",
        "Ireland",
        "Scotland",
        "Japan",
        "South Korea",
        "Spain",
        "Austria",
        "Chile",
        "Greece",
        "Portugal",
        "Denmark",
        "Australia",
        "New Zealand",
        "Switzerland",
        "Belgium",
        "Thailand",
        "Canada",
        "Iceland",
        "Guatemala",
        "Peru",
    ],
    "Theme Park Day": [
        "Long Line", "Mobile Order", "Rain Delay", "Rope Drop", "Snack Break",
        "Ride Photo", "Parade", "Gift Shop", "Early Entry", "Lightning Lane",
        "Refill Cup", "Lost Group", "Low Wait", "Character Meet", "Fireworks",
        "Crowded Path", "Random Show", "Ride Breakdown", "Cold Drink", "Shade Spot",
        "Walk-On Ride", "Souvenir", "Phone Battery Low", "Good Seat", "Unexpected Win",
        "Queue Music", "Park Map", "Hot Weather", "Indoor Ride", "Final Ride"
    ],
    "Cozy Night": [
        "Blanket", "Tea", "Candle", "Movie", "Rain Sounds",
        "Book", "Sweatpants", "Soup", "Lo-Fi", "Soft Socks",
        "Pillow", "Dim Lights", "Snack Bowl", "Pet Nap", "Window View",
        "Warm Drink", "Comfort Show", "No Plans", "Phone Away", "Puzzle",
        "Fresh Sheets", "Calm Music", "Early Bed", "Hoodie", "Stretch",
        "Journal", "Lamp Light", "Cozy Chair", "Quiet Room", "Slow Morning"
    ],
}

BOARD_SIZE = 5
FREE_SPACE = "FREE"

GAME_MODES = [
    "4 Corners",
    "1 Row, Column, or Diagonal",
    "Blackout - All But 1",
]


# -----------------------------
# Helpers
# -----------------------------
def parse_words(word_text):
    return [
        word.strip()
        for word in word_text.splitlines()
        if word.strip()
    ]


def generate_board_matrix(words):
    needed_words = BOARD_SIZE * BOARD_SIZE - 1
    selected = random.sample(words, needed_words)

    board = []
    word_index = 0

    for row in range(BOARD_SIZE):
        current_row = []

        for col in range(BOARD_SIZE):
            if row == 2 and col == 2:
                current_row.append({
                    "word": FREE_SPACE,
                    "marked": True,
                    "called": True,
                    "free": True,
                })
            else:
                current_row.append({
                    "word": selected[word_index],
                    "marked": False,
                    "called": False,
                    "free": False,
                })
                word_index += 1

        board.append(current_row)

    return board


def is_marked(board, row, col):
    return board[row][col]["marked"]


def check_win(board, game_mode):
    if board is None:
        return False

    if game_mode == "4 Corners":
        return (
            is_marked(board, 0, 0)
            and is_marked(board, 0, BOARD_SIZE - 1)
            and is_marked(board, BOARD_SIZE - 1, 0)
            and is_marked(board, BOARD_SIZE - 1, BOARD_SIZE - 1)
        )

    if game_mode == "1 Row, Column, or Diagonal":
        # Rows
        for row in range(BOARD_SIZE):
            if all(is_marked(board, row, col) for col in range(BOARD_SIZE)):
                return True

        # Columns
        for col in range(BOARD_SIZE):
            if all(is_marked(board, row, col) for row in range(BOARD_SIZE)):
                return True

        # Diagonal: top-left to bottom-right
        if all(is_marked(board, i, i) for i in range(BOARD_SIZE)):
            return True

        # Diagonal: top-right to bottom-left
        if all(is_marked(board, i, BOARD_SIZE - 1 - i) for i in range(BOARD_SIZE)):
            return True

        return False

    if game_mode == "Blackout - All But 1":
        marked_count = sum(
            1
            for row in range(BOARD_SIZE)
            for col in range(BOARD_SIZE)
            if board[row][col]["marked"]
        )

        # 25 total spaces, FREE space already counts as marked.
        # This means 24 out of 25 marked.
        return marked_count >= (BOARD_SIZE * BOARD_SIZE - 1)

    return False


def reset_card(words, preset_name):
    st.session_state.board = generate_board_matrix(words)
    st.session_state.active_card_preset = preset_name
    st.session_state.card_word_snapshot = words.copy()
    st.session_state.game_over = False
    st.session_state.show_win_balloons = False


def reset_called_words():
    st.session_state.called_words = []
    st.session_state.current_called_word = None
    st.session_state.last_called_at = None
    st.session_state.game_over = False
    st.session_state.show_win_balloons = False

    if st.session_state.board is not None:
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                cell = st.session_state.board[row][col]

                if cell["free"]:
                    cell["called"] = True
                    cell["marked"] = True
                else:
                    cell["called"] = False
                    cell["marked"] = False


def call_random_word(words):
    available_words = [
        word
        for word in words
        if word not in st.session_state.called_words
    ]

    if not available_words:
        return None

    picked_word = random.choice(available_words)

    st.session_state.called_words.append(picked_word)
    st.session_state.current_called_word = picked_word
    st.session_state.last_called_at = datetime.now(
        ZoneInfo("America/New_York")
    ).strftime("%I:%M:%S %p EST")

    # Update board matrix.
    # Called words also become marked so rules can end the game.
    if st.session_state.board is not None:
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                cell = st.session_state.board[row][col]

                if cell["word"] == picked_word:
                    cell["called"] = True
                    cell["marked"] = True

    if check_win(st.session_state.board, st.session_state.game_mode):
        st.session_state.game_over = True
        st.session_state.show_win_balloons = True

    return picked_word


def build_tile_label(word, is_marked, is_called):
    if word == FREE_SPACE:
        return f"⭐\n{word}"

    if is_marked:
        return f"✅\n{word}"

    if is_called:
        return f"🎯\n{word}"

    return f"⬜\n{word}"


def inject_board_button_colors():
    """
    Uses Streamlit widget keys to target the actual st.button face.
    Marked and FREE cells turn green.
    Called but unmarked cells turn amber.
    """
    if st.session_state.board is None:
        return

    css_lines = ["<style>"]

    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            cell = st.session_state.board[row][col]
            word = cell["word"]
            is_marked_cell = cell["marked"]
            is_called_cell = cell["called"]
            key_class = f".st-key-cell_{row}_{col}"

            if word == FREE_SPACE or is_marked_cell:
                css_lines.append(
                    f"""
                    {key_class} button {{
                        background: rgba(0, 180, 95, 0.38) !important;
                        border: 1px solid rgba(0, 230, 130, 0.95) !important;
                        color: white !important;
                        box-shadow: 0 0 18px rgba(0, 220, 120, 0.30) !important;
                    }}

                    {key_class} button p {{
                        color: white !important;
                    }}
                    """
                )

            elif is_called_cell:
                css_lines.append(
                    f"""
                    {key_class} button {{
                        background: rgba(255, 190, 0, 0.24) !important;
                        border: 1px solid rgba(255, 220, 90, 0.85) !important;
                        box-shadow: 0 0 14px rgba(255, 200, 0, 0.20) !important;
                    }}
                    """
                )

    css_lines.append("</style>")
    st.markdown("\n".join(css_lines), unsafe_allow_html=True)


def get_marked_count(board):
    if board is None:
        return 0

    return sum(
        1
        for row in range(BOARD_SIZE)
        for col in range(BOARD_SIZE)
        if board[row][col]["marked"]
    )


# -----------------------------
# Session State Defaults
# -----------------------------
if "active_word_preset" not in st.session_state:
    first_preset = list(PRESETS.keys())[0]
    st.session_state.active_word_preset = first_preset
    st.session_state.word_text = "\n".join(PRESETS[first_preset])

if "board" not in st.session_state:
    st.session_state.board = None

if "called_words" not in st.session_state:
    st.session_state.called_words = []

if "current_called_word" not in st.session_state:
    st.session_state.current_called_word = None

if "last_called_at" not in st.session_state:
    st.session_state.last_called_at = None

if "auto_call_tick" not in st.session_state:
    st.session_state.auto_call_tick = 0

if "game_mode" not in st.session_state:
    st.session_state.game_mode = "1 Row, Column, or Diagonal"

if "game_over" not in st.session_state:
    st.session_state.game_over = False

if "show_win_balloons" not in st.session_state:
    st.session_state.show_win_balloons = False


# -----------------------------
# Base Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        font-size: 2.3rem;
        font-weight: 900;
        margin-bottom: 0.1rem;
    }

    .subtitle {
        text-align: center;
        opacity: 0.75;
        margin-bottom: 1rem;
    }

    .caller-card {
        text-align: center;
        font-size: 2.3rem;
        font-weight: 900;
        padding: 1.4rem;
        border-radius: 24px;
        background: rgba(255,255,255,0.09);
        border: 1px solid rgba(255,255,255,0.22);
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 22px rgba(0,0,0,0.16);
    }

    .caller-empty {
        text-align: center;
        font-size: 1.1rem;
        font-weight: 700;
        padding: 1.2rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.05);
        border: 1px dashed rgba(255,255,255,0.22);
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }

    .bingo-header {
        text-align: center;
        font-weight: 900;
        font-size: 1.45rem;
        padding: 0.5rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.18);
        margin-bottom: 0.5rem;
    }

    /*
      Base button style.
      State-specific colors are injected later using each button key.
    */
    div[data-testid="stButton"] > button {
        min-height: 92px;
        white-space: pre-line;
        border-radius: 18px;
        font-weight: 850;
        line-height: 1.12;
        border: 1px solid rgba(255,255,255,0.22);
        background: rgba(255,255,255,0.065);
        box-shadow: 0 5px 14px rgba(0,0,0,0.12);
        transition: transform 0.08s ease, border 0.08s ease, background 0.08s ease, box-shadow 0.08s ease;
    }

    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px) scale(1.015);
        border: 1px solid rgba(255,255,255,0.45);
        background: rgba(255,255,255,0.11);
        box-shadow: 0 8px 20px rgba(0,0,0,0.16);
    }

    div[data-testid="stButton"] > button:active {
        transform: scale(0.98);
    }

    .bingo-status {
        text-align: center;
        font-size: 1.3rem;
        font-weight: 900;
        padding: 1rem;
        border-radius: 18px;
        margin-top: 1rem;
        background: rgba(0, 200, 120, 0.15);
        border: 1px solid rgba(0, 200, 120, 0.35);
    }

    .game-over-note {
        text-align: center;
        font-size: 1rem;
        font-weight: 700;
        padding: 0.8rem;
        border-radius: 16px;
        background: rgba(0, 200, 120, 0.10);
        border: 1px solid rgba(0, 200, 120, 0.25);
        margin-bottom: 1rem;
    }

    .empty-card {
        text-align: center;
        padding: 2rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.06);
        border: 1px dashed rgba(255,255,255,0.25);
    }

    .tiny-center-note {
        text-align: center;
        opacity: 0.75;
        font-size: 0.9rem;
        margin-top: -0.3rem;
        margin-bottom: 0.7rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# App Header
# -----------------------------
st.markdown("<div class='main-title'>🎲 Vibe Bingo</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle'>Generate a word card, call random words, and mark your squares.</div>",
    unsafe_allow_html=True
)


# -----------------------------
# Sidebar: Word Pool + Card Setup
# -----------------------------
with st.sidebar:
    st.header("Settings")

    preset = st.selectbox(
        "Choose a Bingo Card preset",
        list(PRESETS.keys())
    )

    if st.session_state.active_word_preset != preset:
        st.session_state.active_word_preset = preset
        st.session_state.word_text = "\n".join(PRESETS[preset])
        st.session_state.board = None
        reset_called_words()

    st.divider()

    st.subheader("📝 Word Pool")
    st.write("Words the card and caller randomly pick from.")

    word_text = st.text_area(
        "One word or phrase per line",
        key="word_text",
        height=260,
        help="A 5x5 bingo card with a FREE space needs at least 24 words."
    )

    custom_words = parse_words(word_text)

    if len(custom_words) >= 24:
        st.success(f"{len(custom_words)} words available.")
    else:
        st.warning(f"{len(custom_words)} words available. Add {24 - len(custom_words)} more.")

    with st.expander("Preview word pool"):
        if custom_words:
            st.write(", ".join(custom_words))
        else:
            st.write("No words yet.")

    st.divider()

    st.subheader("🧩 Bingo Card Setup")

    if st.button("🎯 Generate New Card", use_container_width=True):
        if len(custom_words) < 24:
            st.warning("You need at least 24 words to generate a bingo card.")
        else:
            reset_card(custom_words, preset)
            reset_called_words()

    if st.button("🧼 Clear Marks", use_container_width=True):
        if st.session_state.board is not None:
            for row in range(BOARD_SIZE):
                for col in range(BOARD_SIZE):
                    cell = st.session_state.board[row][col]
                    cell["marked"] = cell["free"]

        st.session_state.game_over = False
        st.session_state.show_win_balloons = False

    if st.button("🔄 Reset Called Words", use_container_width=True):
        reset_called_words()


# Auto-create first board once if possible
if st.session_state.board is None and len(custom_words) >= 24:
    reset_card(custom_words, st.session_state.active_word_preset)


# -----------------------------
# Game Options
# -----------------------------
st.subheader("🎮 Game Options")

st.session_state.game_mode = st.radio(
    "Win condition",
    GAME_MODES,
    index=GAME_MODES.index(st.session_state.game_mode),
    horizontal=True,
    disabled=st.session_state.game_over
)

if st.session_state.game_mode == "4 Corners":
    st.caption("Win by marking all 4 corner squares.")

elif st.session_state.game_mode == "1 Row, Column, or Diagonal":
    st.caption("Classic bingo: win with any full row, column, or diagonal.")

elif st.session_state.game_mode == "Blackout - All But 1":
    st.caption("Win by marking 24 out of 25 squares. The FREE space counts as marked.")

st.divider()


# -----------------------------
# Word Caller
# -----------------------------
st.subheader("🎤 Word Caller")

caller_mode = st.radio(
    "Caller mode",
    ["Manual Button", "Auto Every 20 Seconds", "Auto Every 30 Seconds"],
    horizontal=True,
    disabled=st.session_state.game_over
)

caller_col_1, caller_col_2 = st.columns(2)

with caller_col_1:
    if st.session_state.game_over:
        st.button("🎲 Call Random Word", use_container_width=True, disabled=True)
    else:
        if st.button("🎲 Call Random Word", use_container_width=True):
            if len(custom_words) == 0:
                st.warning("Add words first.")
            else:
                picked = call_random_word(custom_words)

                if picked is None:
                    st.info("All words have already been called.")

                if st.session_state.game_over:
                    st.rerun()

with caller_col_2:
    st.caption(f"Called words: {len(st.session_state.called_words)} / {len(custom_words)}")


# Auto caller
if caller_mode != "Manual Button" and not st.session_state.game_over:
    if AUTO_REFRESH_AVAILABLE:
        seconds = 20 if caller_mode == "Auto Every 20 Seconds" else 30

        tick = st_autorefresh(
            interval=seconds * 1000,
            key="auto_word_caller_refresh"
        )

        if tick != st.session_state.auto_call_tick:
            st.session_state.auto_call_tick = tick

            if len(custom_words) > 0:
                picked = call_random_word(custom_words)

                if picked is None:
                    st.info("All words have already been called.")

                if st.session_state.game_over:
                    st.rerun()

    else:
        st.warning(
            "Auto mode needs `streamlit-autorefresh`. Install it with: "
            "`pip install streamlit-autorefresh`"
        )


# -----------------------------
# Bingo Board
# -----------------------------
st.divider()
st.subheader("🟦 Bingo Board")

# Fire balloons once after rerun
if st.session_state.show_win_balloons:
    st.balloons()
    st.session_state.show_win_balloons = False

# Current called word directly above board
if st.session_state.current_called_word:
    st.markdown(
        f"""
        <div class="caller-card">
            🎤 {st.session_state.current_called_word}
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.last_called_at:
        st.caption(f"Last called at {st.session_state.last_called_at}")
else:
    st.markdown(
        """
        <div class="caller-empty">
            Press <b>Call Random Word</b> to start.
        </div>
        """,
        unsafe_allow_html=True
    )


if st.session_state.game_over:
    st.markdown(
        """
        <div class="game-over-note">
            Game complete. Generate a new card or reset called words to play again.
        </div>
        """,
        unsafe_allow_html=True
    )


if st.session_state.board is None:
    st.markdown(
        """
        <div class="empty-card">
            Add at least 24 words from the sidebar, then click <b>Generate New Card</b>.
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    st.markdown(
        """
        <div class="tiny-center-note">
            Overlay key: ⬜ waiting · 🎯 called · ✅ marked · ⭐ free
        </div>
        """,
        unsafe_allow_html=True
    )

    # This colors the actual button faces.
    inject_board_button_colors()

    header_cols = st.columns(BOARD_SIZE)

    for letter, col in zip("BINGO", header_cols):
        with col:
            st.markdown(
                f"<div class='bingo-header'>{letter}</div>",
                unsafe_allow_html=True
            )

    for row in range(BOARD_SIZE):
        cols = st.columns(BOARD_SIZE)

        for col in range(BOARD_SIZE):
            cell = st.session_state.board[row][col]

            word = cell["word"]
            is_marked_cell = cell["marked"]
            is_called_cell = cell["called"]
            is_free_cell = cell["free"]

            label = build_tile_label(word, is_marked_cell, is_called_cell)
            key = f"cell_{row}_{col}"

            with cols[col]:
                clicked = st.button(
                    label,
                    key=key,
                    use_container_width=True,
                    disabled=st.session_state.game_over
                )

                if clicked and not is_free_cell and not st.session_state.game_over:
                    st.session_state.board[row][col]["marked"] = not is_marked_cell

                    if check_win(st.session_state.board, st.session_state.game_mode):
                        st.session_state.game_over = True
                        st.session_state.show_win_balloons = True
                        st.rerun()

    has_won = st.session_state.game_over or check_win(
        st.session_state.board,
        st.session_state.game_mode
    )

    if has_won:
        st.session_state.game_over = True

        st.markdown(
            f"""
            <div class='bingo-status'>
                🎉 WIN! You completed: {st.session_state.game_mode}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        marked_count = get_marked_count(st.session_state.board)
        st.caption(f"Marked squares: {marked_count}/25")


# -----------------------------
# Called Word History Below Board
# -----------------------------
st.divider()

with st.expander("📜 Called Word History", expanded=False):
    if st.session_state.called_words:
        for index, word in enumerate(st.session_state.called_words, start=1):
            st.write(f"{index}. {word}")
    else:
        st.write("No words called yet.")