import random
from datetime import datetime

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


def generate_card(words):
    needed_words = BOARD_SIZE * BOARD_SIZE - 1
    selected = random.sample(words, needed_words)

    card = []
    word_index = 0

    for row in range(BOARD_SIZE):
        current_row = []

        for col in range(BOARD_SIZE):
            if row == 2 and col == 2:
                current_row.append(FREE_SPACE)
            else:
                current_row.append(selected[word_index])
                word_index += 1

        card.append(current_row)

    return card


def create_marked_board():
    marked = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    marked[2][2] = True
    return marked


def check_win(marked, game_mode):
    if game_mode == "4 Corners":
        return (
            marked[0][0]
            and marked[0][BOARD_SIZE - 1]
            and marked[BOARD_SIZE - 1][0]
            and marked[BOARD_SIZE - 1][BOARD_SIZE - 1]
        )

    if game_mode == "1 Row, Column, or Diagonal":
        # Rows
        for row in marked:
            if all(row):
                return True

        # Columns
        for col in range(BOARD_SIZE):
            if all(marked[row][col] for row in range(BOARD_SIZE)):
                return True

        # Diagonal: top-left to bottom-right
        if all(marked[i][i] for i in range(BOARD_SIZE)):
            return True

        # Diagonal: top-right to bottom-left
        if all(marked[i][BOARD_SIZE - 1 - i] for i in range(BOARD_SIZE)):
            return True

        return False

    if game_mode == "Blackout - All But 1":
        marked_count = sum(
            1
            for row in marked
            for value in row
            if value
        )

        # 25 total spaces, FREE space already counts as marked.
        # This means 24 out of 25 marked.
        return marked_count >= (BOARD_SIZE * BOARD_SIZE - 1)

    return False


def reset_card(words, preset_name):
    st.session_state.card = generate_card(words)
    st.session_state.marked = create_marked_board()
    st.session_state.active_card_preset = preset_name
    st.session_state.card_word_snapshot = words.copy()


def reset_called_words():
    st.session_state.called_words = []
    st.session_state.current_called_word = None
    st.session_state.last_called_at = None


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
    st.session_state.last_called_at = datetime.now().strftime("%I:%M:%S %p")

    return picked_word


# -----------------------------
# Session State Defaults
# -----------------------------
if "active_word_preset" not in st.session_state:
    first_preset = list(PRESETS.keys())[0]
    st.session_state.active_word_preset = first_preset
    st.session_state.word_text = "\n".join(PRESETS[first_preset])

if "card" not in st.session_state:
    st.session_state.card = None

if "marked" not in st.session_state:
    st.session_state.marked = create_marked_board()

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


# -----------------------------
# Styling
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
        font-size: 2.2rem;
        font-weight: 900;
        padding: 1.4rem;
        border-radius: 22px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.20);
        margin-top: 0.5rem;
        margin-bottom: 1rem;
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
        font-size: 1.4rem;
        padding: 0.5rem;
        border-radius: 12px;
        background: rgba(255,255,255,0.08);
        margin-bottom: 0.5rem;
    }

    div[data-testid="stButton"] > button {
        min-height: 76px;
        white-space: normal;
        border-radius: 16px;
        font-weight: 800;
        line-height: 1.15;
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

    .empty-card {
        text-align: center;
        padding: 2rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.06);
        border: 1px dashed rgba(255,255,255,0.25);
    }

    .small-note {
        text-align: center;
        opacity: 0.75;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
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
        st.session_state.card = None
        st.session_state.marked = create_marked_board()
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
        st.session_state.marked = create_marked_board()

    if st.button("🔄 Reset Called Words", use_container_width=True):
        reset_called_words()


# Auto-create first card once if possible
if st.session_state.card is None and len(custom_words) >= 24:
    reset_card(custom_words, st.session_state.active_word_preset)


# -----------------------------
# Game Options
# -----------------------------
st.subheader("🎮 Game Options")

st.session_state.game_mode = st.radio(
    "Win condition",
    GAME_MODES,
    index=GAME_MODES.index(st.session_state.game_mode),
    horizontal=False
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
    horizontal=True
)

caller_col_1, caller_col_2 = st.columns(2)

with caller_col_1:
    if st.button("🎲 Call Random Word", use_container_width=True):
        if len(custom_words) == 0:
            st.warning("Add words first.")
        else:
            picked = call_random_word(custom_words)
            if picked is None:
                st.info("All words have already been called.")

with caller_col_2:
    st.caption(f"Called words: {len(st.session_state.called_words)} / {len(custom_words)}")


# Auto caller
if caller_mode != "Manual Button":
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


if st.session_state.card is None:
    st.markdown(
        """
        <div class="empty-card">
            Add at least 24 words from the sidebar, then click <b>Generate New Card</b>.
        </div>
        """,
        unsafe_allow_html=True
    )

else:
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
            word = st.session_state.card[row][col]
            is_marked = st.session_state.marked[row][col]
            is_called = word in st.session_state.called_words

            if is_marked:
                label = f"✅ {word}"
            elif is_called:
                label = f"🎯 {word}"
            else:
                label = word

            key = f"cell_{row}_{col}"

            with cols[col]:
                if st.button(label, key=key, use_container_width=True):
                    if word != FREE_SPACE:
                        st.session_state.marked[row][col] = not is_marked

    if check_win(st.session_state.marked, st.session_state.game_mode):
        st.markdown(
            f"""
            <div class='bingo-status'>
                🎉 WIN! You completed: {st.session_state.game_mode}
            </div>
            """,
            unsafe_allow_html=True
        )
        st.balloons()
    else:
        marked_count = sum(
            1
            for row in st.session_state.marked
            for value in row
            if value
        )

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