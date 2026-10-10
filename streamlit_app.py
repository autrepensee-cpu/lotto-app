import json
import itertools
import urllib.request
import streamlit as st
from collections import Counter

DATA_URL = "https://smok95.github.io/lotto/results/all.json"
TOP_N_COMBOS = 20

@st.cache_data(ttl=3600)
def load_results():
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "LuckyLottoNumber/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))

    if isinstance(data, dict):
        for key in ("results", "data", "draws"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue

        draw = item.get("draw_no", item.get("round", item.get("drwtNo")))
        nums = item.get("numbers")

        if nums is None:
            nums = []
            for key in (
                "drwtNo1", "drwtNo2", "drwtNo3",
                "drwtNo4", "drwtNo5", "drwtNo6"
            ):
                if key in item:
                    nums.append(item[key])

        try:
            draw = int(draw)
            nums = sorted(int(x) for x in nums)

            if len(nums) == 6 and all(1 <= x <= 45 for x in nums):
                rows.append((draw, nums))
        except Exception:
            continue

    rows.sort(key=lambda x: x[0])

    if len(rows) < 10:
        raise RuntimeError("최근 10회 데이터를 가져오지 못했습니다.")

    return rows

def make_games(rows):
    recent = rows[-10:]

    freq = Counter(
        number
        for _, numbers in recent
        for number in numbers
    )

    top12 = sorted(
        range(1, 46),
        key=lambda n: (-freq[n], n)
    )[:12]

    scored = []

    for combo in itertools.combinations(top12, 6):
        combo_set = set(combo)

        hits = [
            len(combo_set & set(numbers))
            for _, numbers in recent
        ]

        total = sum(hits)
        hit3 = sum(h >= 3 for h in hits)
        hit4 = sum(h >= 4 for h in hits)
        hit5 = sum(h >= 5 for h in hits)
        hit6 = sum(h == 6 for h in hits)

        scored.append(
            (
                total,
                hit3,
                hit4,
                hit5,
                hit6,
                combo
            )
        )

    scored.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            -x[2],
            -x[3],
            -x[4],
            x[5]
        )
    )

    top_combos = scored[:TOP_N_COMBOS]

    survivor = Counter()

    for item in top_combos:
        survivor.update(item[5])

    top10 = sorted(
        survivor,
        key=lambda n: (
            -survivor[n],
            -freq[n],
            n
        )
    )[:10]

    fixed5 = top10[:5]
    rotating5 = top10[5:]

    games = [
        tuple(sorted(fixed5 + [number]))
        for number in rotating5
    ]

    return recent, top12, top10, games

# Streamlit UI 설정
st.set_page_config(page_title="행운의 로또번호", page_icon="🍀", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #806f5b;
        color: white;
    }
    .ball {
        display: inline-block;
        width: 38px;
        height: 38px;
        text-align: center;
        border-radius: 50%;
        font-weight: bold;
        color: black;
        margin-right: 6px;
        line-height: 38px;
        font-size: 15px;
    }
    .ball-A { background-color: #ff2028; color: white; }
    .ball-B { background-color: #ffae00; color: black; }
    .ball-C { background-color: #75c900; color: black; }
    .ball-D { background-color: #18a9dc; color: white; }
    .ball-E { background-color: #a500b8; color: white; }
    .num-ball { background-color: white; color: black; border: 2px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: white;'>🍀 행운의 로또번호</h1>", unsafe_allow_html=True)

if st.button("🔄 번호새로고침 / 생성하기", use_container_width=True):
    st.cache_data.clear()

with st.spinner("최신 데이터를 분석 중입니다..."):
    try:
        rows = load_results()
        recent, top12, top10, games = make_games(rows)

        latest_draw, latest_numbers = recent[-1]
        latest_numbers_text = " · ".join(f"{n:02d}" for n in latest_numbers)

        st.markdown(f"<p style='text-align: center; color: #f0f0f0;'>분석 데이터: {recent[0][0]}회 ~ {recent[-1][0]}회<br><b>{latest_draw}회 당첨번호: {latest_numbers_text}</b></p>", unsafe_allow_html=True)
        st.markdown("---")

        ball_classes = ["ball-A", "ball-B", "ball-C", "ball-D", "ball-E"]
        letters = ["A", "B", "C", "D", "E"]

        for idx, game in enumerate(games):
            letter = letters[idx]
            b_cls = ball_classes[idx]
            
            balls_html = f"<span class='ball {b_cls}'>{letter}</span>"
            for num in game:
                balls_html += f"<span class='ball num-ball'>{num:02d}</span>"
            
            st.markdown(f"<div style='margin-bottom: 12px; text-align: center;'>{balls_html}</div>", unsafe_allow_html=True)

        st.success("추천번호 생성 완료!")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")