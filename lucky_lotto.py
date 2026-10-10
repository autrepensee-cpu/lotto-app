# -*- coding: utf-8 -*-
import json
import itertools
import threading
import urllib.request
import tkinter as tk
from collections import Counter

DATA_URL = "https://smok95.github.io/lotto/results/all.json"
TOP_N_COMBOS = 20

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

    # 최근 10회 출현빈도 TOP12
    top12 = sorted(
        range(1, 46),
        key=lambda n: (-freq[n], n)
    )[:12]

    # TOP12에서 6개를 제한 없이 선택 = 924개
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

    # 상위 20개 조합
    top_combos = scored[:TOP_N_COMBOS]

    # 상위 조합에 반복 등장한 숫자
    survivor = Counter()

    for item in top_combos:
        survivor.update(item[5])

    # 살아남은 TOP10
    top10 = sorted(
        survivor,
        key=lambda n: (
            -survivor[n],
            -freq[n],
            n
        )
    )[:10]

    # TOP5 고정 + 나머지 5개를 하나씩 교체
    fixed5 = top10[:5]
    rotating5 = top10[5:]

    games = [
        tuple(sorted(fixed5 + [number]))
        for number in rotating5
    ]

    return recent, top12, top10, games


class LuckyLottoApp(tk.Tk):

    BALL_COLORS = [
        "#ff2028",
        "#ffae00",
        "#75c900",
        "#18a9dc",
        "#a500b8"
    ]

    def __init__(self):
        super().__init__()

        self.title("행운의 로또번호")
        self.geometry("620x470")
        self.resizable(False, False)
        self.configure(bg="#806f5b")

        # 제목
        tk.Label(
            self,
            text="행운의 로또번호",
            font=("맑은 고딕", 23, "bold"),
            fg="white",
            bg="#806f5b"
        ).pack(pady=(16, 0))

        self.info = tk.Label(
            self,
            text="최근 10회 분석 중...",
            font=("맑은 고딕", 10),
            fg="white",
            bg="#806f5b"
        )
        self.info.pack(pady=(3, 8))

        # A~E 영역
        self.game_area = tk.Frame(
            self,
            bg="#806f5b",
            width=590,
            height=330
        )
        self.game_area.pack(pady=0)
        self.game_area.pack_propagate(False)

        self.rows = []

        for index, letter in enumerate(["A", "B", "C", "D", "E"]):

            row = tk.Frame(
                self.game_area,
                bg="#806f5b",
                width=590,
                height=60
            )
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # A~E 원
            letter_label = tk.Label(
                row,
                text=letter,
                font=("맑은 고딕", 14, "bold"),
                fg="black",
                bg=self.BALL_COLORS[index],
                width=3,
                height=1
            )
            letter_label.place(x=8, y=8, width=42, height=42)

            # 번호 6개를 직접 배치
            number_labels = []

            for j in range(6):
                label = tk.Label(
                    row,
                    text="--",
                    font=("맑은 고딕", 12, "bold"),
                    fg="black",
                    bg=self.BALL_COLORS[index],
                    anchor="center"
                )

                label.place(
                    x=70 + j * 82,
                    y=7,
                    width=62,
                    height=44
                )

                number_labels.append(label)

            self.rows.append(number_labels)

        self.status = tk.Label(
            self,
            text="최신 번호를 가져오는 중...",
            font=("맑은 고딕", 9),
            fg="white",
            bg="#806f5b"
        )
        self.status.pack(pady=(4, 0))

        # 실행 즉시 자동 업데이트
        self.after(150, self.refresh)

    def refresh(self):
        self.info.config(text="최신 직전 10회 자동 분석 중...")
        threading.Thread(
            target=self.worker,
            daemon=True
        ).start()

    def worker(self):
        try:
            rows = load_results()
            result = make_games(rows)

            self.after(
                0,
                lambda: self.show_result(result)
            )

        except Exception as exc:
            self.after(
                0,
                lambda: self.show_error(str(exc))
            )

    def show_result(self, result):

        recent, top12, top10, games = result

        # 회차 / 분석 상태
        latest_draw, latest_numbers = recent[-1]
        latest_numbers_text = " · ".join(f"{n:02d}" for n in latest_numbers)

        self.info.config(
            text=(
                f"분석 데이터 {recent[0][0]}회 ~ {recent[-1][0]}회"
                "  ·  추천번호 생성 완료\n"
                f"{latest_draw}회 당첨번호  ·  {latest_numbers_text}"
            ),
            justify="center"
        )

        # 최종 5게임 표시
        for row_index in range(5):

            game = games[row_index]

            for col_index in range(6):

                number = game[col_index]

                self.rows[row_index][col_index].config(
                    text=f"{number:02d}"
                )

        self.status.config(
            text="자동 업데이트 완료"
        )

    def show_error(self, message):

        self.info.config(
            text="데이터를 가져오지 못했습니다."
        )

        self.status.config(
            text=message
        )


if __name__ == "__main__":
    app = LuckyLottoApp()
    app.mainloop()
