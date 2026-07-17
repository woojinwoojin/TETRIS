# Python + Pygame 테트리스 개발 가이드

> ### ▶ [최신 버전 다운로드 (TETRIS.exe)](https://github.com/woojinwoojin/TETRIS/releases/latest)
>
> 다운로드 후 더블클릭하면 바로 실행됩니다. (Python / pygame 설치 불필요)
> 실행 시 윈도우 보안 경고가 뜨면 **"추가 정보" → "실행"** 을 눌러 주세요. ([자세히](#12-윈도우-보안-경고))

## 1. 프로젝트 목표

처음부터 완성형 테트리스를 만들기보다, 기본 동작이 가능한 버전을 단계적으로 구현한다.

### 1차 구현 범위

- 10×20 게임 보드
- 7종 테트로미노 생성
- 좌우 이동
- 자동 낙하
- 블록 회전
- 벽·바닥·블록 충돌 판정
- 블록 고정
- 완성된 줄 삭제
- 점수 계산
- 게임 오버

### 나중에 추가할 기능

- 다음 블록 미리 보기
- 하드 드롭
- 소프트 드롭
- 홀드
- 고스트 블록
- 레벨 및 속도 증가
- 콤보
- 벽차기
- 시작·재시작 화면

---

## 2. 개발 환경

- 언어: Python
- 라이브러리: Pygame

### 설치

```bash
pip install pygame
```

### 프로젝트 구조

처음에는 한 파일로 시작해도 된다.

```text
tetris/
├── main.py
└── requirements.txt
```

코드가 커지면 다음처럼 분리한다.

```text
tetris/
├── main.py
├── board.py
├── piece.py
├── shapes.py
└── settings.py
```

---

## 3. 핵심 자료구조

## 3.1 게임 보드

테트리스 보드는 20행 10열의 2차원 리스트로 표현한다.

```python
ROWS = 20
COLS = 10

board = [
    [0 for _ in range(COLS)]
    for _ in range(ROWS)
]
```

- `0`: 빈칸
- `1` 이상: 고정된 블록

---

## 3.2 테트로미노 모양

블록도 작은 2차원 리스트로 표현한다.

```python
T_SHAPE = [
    [0, 1, 0],
    [1, 1, 1],
]

I_SHAPE = [
    [1, 1, 1, 1],
]

O_SHAPE = [
    [1, 1],
    [1, 1],
]
```

정식 테트리스에는 다음 7가지 블록이 있다.

- I
- O
- T
- S
- Z
- J
- L

---

## 3.3 현재 움직이는 블록

현재 블록은 모양과 위치를 가진 객체로 관리한다.

```python
class Piece:
    def __init__(self, shape, x, y):
        self.shape = shape
        self.x = x
        self.y = y
```

중요한 원칙:

> 움직이는 블록은 `Piece` 객체로 관리하고, 착지한 블록만 `board`에 기록한다.

---

## 4. 핵심 함수

## 4.1 이동 가능 여부 검사

```python
def is_valid_position(board, piece, offset_x=0, offset_y=0):
    for row_index, row in enumerate(piece.shape):
        for col_index, value in enumerate(row):
            if value == 0:
                continue

            new_x = piece.x + col_index + offset_x
            new_y = piece.y + row_index + offset_y

            if new_x < 0 or new_x >= COLS:
                return False

            if new_y >= ROWS:
                return False

            if new_y >= 0 and board[new_y][new_x] != 0:
                return False

    return True
```

사용 예시:

```python
is_valid_position(board, piece, offset_x=-1)  # 왼쪽
is_valid_position(board, piece, offset_x=1)   # 오른쪽
is_valid_position(board, piece, offset_y=1)   # 아래
```

---

## 4.2 블록 회전

행렬을 시계 방향으로 회전한다.

```python
def rotate_clockwise(shape):
    return [list(row) for row in zip(*shape[::-1])]
```

회전 후 충돌하면 원래 모양으로 되돌린다.

```python
old_shape = piece.shape
piece.shape = rotate_clockwise(piece.shape)

if not is_valid_position(board, piece):
    piece.shape = old_shape
```

---

## 4.3 블록 고정

블록이 더 내려갈 수 없을 때 보드에 기록한다.

```python
def lock_piece(board, piece):
    for row_index, row in enumerate(piece.shape):
        for col_index, value in enumerate(row):
            if value:
                board_y = piece.y + row_index
                board_x = piece.x + col_index
                board[board_y][board_x] = value
```

---

## 4.4 완성된 줄 삭제

```python
def clear_lines(board):
    remaining_rows = [
        row for row in board
        if any(cell == 0 for cell in row)
    ]

    cleared_count = ROWS - len(remaining_rows)

    new_rows = [
        [0 for _ in range(COLS)]
        for _ in range(cleared_count)
    ]

    board[:] = new_rows + remaining_rows

    return cleared_count
```

---

## 5. 게임 루프

테트리스는 다음 흐름을 반복한다.

```text
입력 처리
→ 블록 이동
→ 충돌 검사
→ 블록 고정
→ 줄 삭제
→ 새 블록 생성
→ 화면 그리기
```

기본 형태:

```python
while running:
    handle_input()

    if fall_time_passed:
        if is_valid_position(board, current_piece, offset_y=1):
            current_piece.y += 1
        else:
            lock_piece(board, current_piece)
            clear_lines(board)
            current_piece = create_new_piece()

    draw_board()
    draw_piece(current_piece)
    update_screen()
```

---

## 6. 추천 개발 순서

### 1단계: Pygame 창 만들기

- 게임 창 생성
- FPS 설정
- 종료 이벤트 처리

### 2단계: 10×20 격자 그리기

- 각 칸의 크기 설정
- 보드 테두리와 격자 출력

### 3단계: O 블록 하나 표시하기

- 블록 좌표를 화면 좌표로 변환
- 보드 중앙 위쪽에 출력

### 4단계: 좌우 이동 구현

- 왼쪽 방향키
- 오른쪽 방향키
- 벽 충돌 검사

### 5단계: 자동 낙하 구현

- 일정 시간이 지나면 `y += 1`
- Pygame 타이머 또는 누적 시간 사용

### 6단계: 바닥 충돌과 고정

- 더 내려갈 수 없으면 보드에 기록
- 새로운 블록 생성

### 7단계: 블록끼리 충돌

- 보드에 고정된 칸 검사
- 겹치지 못하게 처리

### 8단계: 7가지 블록 추가

- 블록 목록 생성
- 무작위 블록 선택

### 9단계: 회전 구현

- 행렬 회전
- 회전 후 충돌 검사

### 10단계: 줄 삭제와 점수

- 가득 찬 행 제거
- 삭제한 줄 수만큼 점수 증가

### 11단계: 게임 오버

- 새 블록이 생성되는 위치부터 충돌하면 종료

---

## 7. 점수 계산 예시

```python
SCORE_TABLE = {
    1: 100,
    2: 300,
    3: 500,
    4: 800,
}

score += SCORE_TABLE.get(cleared_count, 0)
```

---

## 8. 자주 발생하는 오류

### 행과 열 순서 혼동

```python
board[y][x]
```

보통 2차원 리스트는 `board[행][열]`, 즉 `board[y][x]` 순서로 접근한다.

### 현재 블록을 너무 일찍 보드에 저장함

이동 중인 블록은 보드에 직접 넣지 않는다. 화면을 그릴 때만 보드 위에 임시로 표시한다.

### 회전 후 화면 밖으로 나감

회전 결과에 대해 반드시 충돌 검사를 한다.

### 줄 삭제 후 빈 줄을 아래에 추가함

새 빈 줄은 보드 위쪽에 추가해야 한다.

### 새 블록을 먼저 생성함

기존 블록을 보드에 고정하고 줄을 삭제한 뒤 새 블록을 생성한다.

---

## 9. 첫 번째 완성 목표

처음에는 다음 기능만 구현한다.

1. 창이 열린다.
2. 10×20 격자가 보인다.
3. O 블록이 위에서 내려온다.
4. 방향키로 좌우 이동할 수 있다.
5. 바닥에 닿으면 고정된다.
6. 새로운 O 블록이 생성된다.

이 버전이 정상 동작하면 다른 블록, 회전, 줄 삭제 기능을 순서대로 추가한다.

---

## 10. 실행 방법

### 소스로 실행

```bash
pip install -r requirements.txt
python main.py
```

### 조작법

| 키 | 동작 |
|----|------|
| ← → | 좌우 이동 |
| ↑ | 회전 (벽차기 지원) |
| ↓ | 소프트 드롭 (빠르게 낙하) |
| Space | 하드 드롭 (한 번에 낙하) |

### 구현된 기능

1차 구현 범위(보드·7종 블록·이동·낙하·회전·충돌·고정·줄삭제·점수·게임오버)에 더해:

- 배경 음악 (`assets/bgm.mp3`)
- 벽차기 회전
- 소프트 드롭 / 하드 드롭
- 고스트 블록 (착지 위치 미리보기)
- 다음 블록 미리보기 (NEXT)
- 레벨 / 낙하 속도 증가 (500점마다 난이도 상승)

---

## 11. exe 빌드

윈도우 실행 파일(exe)을 만들려면 PyInstaller를 사용한다.

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name TETRIS --add-data "assets/bgm.mp3;assets" main.py
```

- 결과물: `dist/TETRIS.exe` (음악 파일이 내부에 포함됨)
- `build/`, `dist/`, `*.spec`는 빌드 산출물이라 git에 커밋하지 않는다(`.gitignore` 처리).
- 배포 시에는 저장소에 직접 커밋하는 대신 **GitHub Release**에 exe를 첨부하는 것을 권장한다.

---

## 12. 윈도우 보안 경고

exe를 처음 실행하면 **"Windows의 PC 보호"** 라는 파란 경고 창이 뜰 수 있다.

이는 바이러스가 아니라, **코드 서명(비용이 드는 인증서)** 이 없는 프로그램이라
윈도우 SmartScreen이 "잘 모르는 프로그램"으로 판단해서 뜨는 정상적인 경고다.
직접 만든 프로그램이므로 안전하다.

### 실행 방법

1. 경고 창에서 **"추가 정보(More info)"** 클릭
2. 나타나는 **"실행(Run anyway)"** 버튼 클릭

### 경고를 없애려면 (선택)

- **코드 서명 인증서**를 구입해 exe에 서명하면 경고가 사라진다(유료, 개인 프로젝트에는 과함).
- 또는 exe 대신 소스로 실행하면 경고가 없다: `python main.py`
