"""테트리스 - 개선판

1차 구현 범위 완료 + 추가 기능:
- 게임 오버 / 배경 음악 (assets/bgm.mp3)
- 벽차기 회전 (벽에 붙어도 밀어서 회전)
- 소프트 드롭 (아래 방향키), 하드 드롭 (스페이스)
- 고스트 블록 (착지 위치 미리보기)
- 다음 블록 미리보기 (NEXT), 레벨/속도 증가

조작: ← → 이동 / ↑ 회전 / ↓ 빠른 낙하 / Space 즉시 낙하
"""

import os
import random
import sys

import pygame


def resource_path(rel_path):
    """리소스 파일의 실제 경로를 반환한다.

    PyInstaller로 만든 exe에서는 임시 폴더(sys._MEIPASS)에서,
    일반 실행에서는 이 스크립트 폴더 기준으로 찾는다.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


# 배경 음악 파일 경로
BGM_PATH = resource_path(os.path.join("assets", "bgm.mp3"))

# 보드 설정
COLS = 10
ROWS = 20
CELL_SIZE = 40

# 보드가 그려질 위치(왼쪽 위 기준 여백)
BOARD_X = 20
BOARD_Y = 20

# 보드 픽셀 크기
BOARD_WIDTH = COLS * CELL_SIZE
BOARD_HEIGHT = ROWS * CELL_SIZE

# 오른쪽 정보 패널 폭
PANEL_WIDTH = 180

# 화면 설정
SCREEN_WIDTH = BOARD_X * 2 + BOARD_WIDTH + PANEL_WIDTH
SCREEN_HEIGHT = BOARD_Y * 2 + BOARD_HEIGHT
FPS = 60

# 자동 낙하 간격(ms) - 이 시간마다 한 칸 내려온다
FALL_INTERVAL = 500

# 소프트 드롭 간격(ms) - 아래 방향키를 누르고 있을 때
SOFT_DROP_INTERVAL = 50

# 난이도: 이 점수마다 레벨이 1 오르고 낙하가 빨라진다
LEVEL_UP_SCORE = 500
SPEED_STEP = 40        # 레벨당 줄어드는 낙하 간격(ms)
MIN_FALL_INTERVAL = 100  # 최고 난이도에서의 최소 낙하 간격(ms)

# 미리 보여줄 다음 블록 개수
NEXT_COUNT = 2

# 줄 삭제 점수표 (동시에 지운 줄 수 -> 점수)
SCORE_TABLE = {
    1: 100,
    2: 300,
    3: 500,
    4: 800,
}

# 색상
BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
WHITE = (200, 200, 200)

# 블록 색 번호(1~7) -> 실제 색. 보드에는 이 번호를 저장한다.
COLORS = {
    1: (0, 240, 240),    # I - 하늘
    2: (240, 240, 0),    # O - 노랑
    3: (160, 0, 240),    # T - 보라
    4: (0, 240, 0),      # S - 초록
    5: (240, 0, 0),      # Z - 빨강
    6: (0, 0, 240),      # J - 파랑
    7: (240, 160, 0),    # L - 주황
}

# 테트로미노 모양 (1은 채워진 칸)
SHAPES = {
    1: [[1, 1, 1, 1]],              # I
    2: [[1, 1],
        [1, 1]],                    # O
    3: [[0, 1, 0],
        [1, 1, 1]],                 # T
    4: [[0, 1, 1],
        [1, 1, 0]],                 # S
    5: [[1, 1, 0],
        [0, 1, 1]],                 # Z
    6: [[1, 0, 0],
        [1, 1, 1]],                 # J
    7: [[0, 0, 1],
        [1, 1, 1]],                 # L
}


# 게임 상태
STATE_START = "start"        # 시작 화면 (게임 시작 버튼)
STATE_PLAYING = "playing"    # 진행 중
STATE_PAUSED = "paused"      # 일시정지 (ESC)
STATE_GAMEOVER = "gameover"  # 게임 오버

# 버튼 색
BTN_BG = (55, 55, 55)
BTN_BG_HOVER = (90, 90, 90)


class Piece:
    """현재 움직이는 블록. 모양, 색 번호, 보드 상의 위치(x, y)를 가진다."""

    def __init__(self, shape, color, x, y):
        self.shape = shape
        self.color = color  # COLORS의 색 번호(1~7)
        self.x = x
        self.y = y


class Button:
    """가운데 정렬된 클릭 가능한 버튼. 마우스 호버 시 색이 밝아진다."""

    def __init__(self, label, center_x, center_y, width=220, height=52):
        self.label = label
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (center_x, center_y)

    def draw(self, screen, font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(
            screen,
            BTN_BG_HOVER if hovered else BTN_BG,
            self.rect,
            border_radius=8,
        )
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=8)
        text = font.render(self.label, True, WHITE)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        """왼쪽 클릭이 이 버튼 위에서 일어났는지 검사한다."""
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


def create_board():
    """빈 보드(20행 10열)를 만든다. 0은 빈칸."""
    return [[0 for _ in range(COLS)] for _ in range(ROWS)]


def is_valid_position(board, piece, offset_x=0, offset_y=0):
    """블록을 (offset_x, offset_y)만큼 옮겼을 때 놓을 수 있는지 검사한다."""
    for row_index, row in enumerate(piece.shape):
        for col_index, value in enumerate(row):
            if value == 0:
                continue

            new_x = piece.x + col_index + offset_x
            new_y = piece.y + row_index + offset_y

            # 좌우 벽
            if new_x < 0 or new_x >= COLS:
                return False

            # 바닥
            if new_y >= ROWS:
                return False

            # 이미 고정된 블록과 충돌
            if new_y >= 0 and board[new_y][new_x] != 0:
                return False

    return True


def rotate_clockwise(shape):
    """행렬을 시계 방향으로 90도 회전한다."""
    return [list(row) for row in zip(*shape[::-1])]


def try_rotate(board, piece):
    """블록을 회전한다. 벽/블록에 걸리면 좌우로 조금 밀어(벽차기) 시도한다."""
    old_shape = piece.shape
    old_x = piece.x
    piece.shape = rotate_clockwise(piece.shape)

    # 제자리 -> 좌우로 조금씩 밀며 들어갈 자리를 찾는다
    # (I 블록이 벽 끝에 붙었을 때 최대 3칸까지 밀어야 눕는다)
    for dx in (0, -1, 1, -2, 2, -3, 3):
        if is_valid_position(board, piece, offset_x=dx):
            piece.x += dx
            return

    # 어디에도 못 들어가면 회전 취소
    piece.shape = old_shape
    piece.x = old_x


def lock_piece(board, piece):
    """더 내려갈 수 없는 블록을 보드에 기록한다. 색 번호를 저장한다."""
    for row_index, row in enumerate(piece.shape):
        for col_index, value in enumerate(row):
            if value:
                board_y = piece.y + row_index
                board_x = piece.x + col_index
                board[board_y][board_x] = piece.color


def clear_lines(board):
    """가득 찬 줄을 지우고, 지운 줄 수를 반환한다."""
    # 빈칸(0)이 하나라도 있는 줄만 남긴다
    remaining_rows = [
        row for row in board
        if any(cell == 0 for cell in row)
    ]

    cleared_count = ROWS - len(remaining_rows)

    # 지운 만큼 빈 줄을 '위쪽'에 새로 채운다
    new_rows = [
        [0 for _ in range(COLS)]
        for _ in range(cleared_count)
    ]

    board[:] = new_rows + remaining_rows

    return cleared_count


def make_piece(color):
    """색 번호로 블록을 만들어 보드 중앙 위쪽에 놓는다."""
    shape = SHAPES[color]
    piece_width = len(shape[0])
    x = COLS // 2 - piece_width // 2
    return Piece(shape, color, x=x, y=0)


def spawn_next(next_queue):
    """대기열 맨 앞 블록을 꺼내 만들고, 대기열에 새 블록을 하나 채운다."""
    color = next_queue.pop(0)
    next_queue.append(random.randint(1, 7))
    return make_piece(color)


def lock_and_spawn(board, piece, next_queue):
    """블록을 고정하고 줄을 지운 뒤, (새 블록, 획득 점수, 게임오버 여부)를 반환한다."""
    lock_piece(board, piece)
    cleared = clear_lines(board)
    gained = SCORE_TABLE.get(cleared, 0)
    new_piece = spawn_next(next_queue)
    over = not is_valid_position(board, new_piece)
    return new_piece, gained, over


def start_new_game():
    """새 게임의 초기 상태(보드, 다음 대기열, 첫 블록)를 만들어 반환한다."""
    board = create_board()
    next_queue = [random.randint(1, 7) for _ in range(NEXT_COUNT)]
    current_piece = spawn_next(next_queue)
    return board, next_queue, current_piece


def get_level(score):
    """점수로 현재 레벨을 계산한다 (1부터 시작)."""
    return score // LEVEL_UP_SCORE + 1


def get_fall_interval(score):
    """레벨이 오를수록 낙하 간격을 줄인다 (최소 MIN_FALL_INTERVAL)."""
    level = get_level(score)
    return max(MIN_FALL_INTERVAL, FALL_INTERVAL - (level - 1) * SPEED_STEP)


def draw_grid(screen):
    """보드 영역의 격자와 테두리를 그린다."""
    # 세로 선
    for col in range(COLS + 1):
        x = BOARD_X + col * CELL_SIZE
        pygame.draw.line(
            screen, GRAY,
            (x, BOARD_Y),
            (x, BOARD_Y + BOARD_HEIGHT),
        )

    # 가로 선
    for row in range(ROWS + 1):
        y = BOARD_Y + row * CELL_SIZE
        pygame.draw.line(
            screen, GRAY,
            (BOARD_X, y),
            (BOARD_X + BOARD_WIDTH, y),
        )

    # 바깥 테두리
    pygame.draw.rect(
        screen, WHITE,
        (BOARD_X, BOARD_Y, BOARD_WIDTH, BOARD_HEIGHT),
        2,
    )


def draw_cell(screen, col, row, color):
    """보드 좌표(col, row)에 색칠된 한 칸을 그린다."""
    x = BOARD_X + col * CELL_SIZE
    y = BOARD_Y + row * CELL_SIZE
    pygame.draw.rect(screen, color, (x, y, CELL_SIZE, CELL_SIZE))
    # 칸 경계선
    pygame.draw.rect(screen, BLACK, (x, y, CELL_SIZE, CELL_SIZE), 1)


def draw_board(screen, board):
    """보드에 고정된 블록들을 각자의 색으로 그린다."""
    for row_index, row in enumerate(board):
        for col_index, value in enumerate(row):
            if value:
                draw_cell(screen, col_index, row_index, COLORS[value])


def draw_panel(screen, font, score, next_queue):
    """오른쪽 패널에 점수, 레벨, 다음 블록을 표시한다."""
    panel_x = BOARD_X * 2 + BOARD_WIDTH

    # 점수
    screen.blit(font.render("SCORE", True, WHITE), (panel_x, BOARD_Y))
    screen.blit(font.render(str(score), True, WHITE), (panel_x, BOARD_Y + 26))

    # 레벨
    screen.blit(font.render("LEVEL", True, WHITE), (panel_x, BOARD_Y + 70))
    screen.blit(
        font.render(str(get_level(score)), True, WHITE),
        (panel_x, BOARD_Y + 96),
    )

    # 다음 블록 미리보기
    screen.blit(font.render("NEXT", True, WHITE), (panel_x, BOARD_Y + 150))
    mini = 26
    slot_y = BOARD_Y + 180
    for color in next_queue:
        shape = SHAPES[color]
        for r, row in enumerate(shape):
            for c, value in enumerate(row):
                if value:
                    x = panel_x + c * mini
                    y = slot_y + r * mini
                    pygame.draw.rect(screen, COLORS[color], (x, y, mini, mini))
                    pygame.draw.rect(screen, BLACK, (x, y, mini, mini), 1)
        slot_y += 3 * mini + 10  # 블록마다 세로 간격


def draw_game_over(screen, font):
    """게임 오버 문구를 보드 중앙에 표시한다."""
    text = font.render("GAME OVER", True, WHITE)
    rect = text.get_rect(
        center=(BOARD_X + BOARD_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2)
    )
    # 글자가 잘 보이도록 뒤에 반투명 배경 상자
    box = pygame.Surface((rect.width + 20, rect.height + 20))
    box.set_alpha(200)
    box.fill(BLACK)
    screen.blit(box, (rect.x - 10, rect.y - 10))
    screen.blit(text, rect)


def draw_overlay(screen):
    """화면 전체를 어둡게 덮어 그 위 메뉴가 잘 보이게 한다."""
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(190)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))


def draw_centered_title(screen, font, text, center_y):
    """가운데 정렬된 큰 제목을 그린다."""
    surface = font.render(text, True, WHITE)
    rect = surface.get_rect(center=(SCREEN_WIDTH // 2, center_y))
    screen.blit(surface, rect)


def get_drop_y(board, piece):
    """현재 블록을 그대로 떨어뜨렸을 때 착지하는 y 좌표를 구한다."""
    drop_y = piece.y
    while is_valid_position(board, piece, offset_y=(drop_y - piece.y) + 1):
        drop_y += 1
    return drop_y


def draw_ghost(screen, board, piece):
    """현재 블록이 착지할 위치를 윤곽선으로 표시한다."""
    drop_y = get_drop_y(board, piece)
    if drop_y == piece.y:
        return  # 이미 바닥이면 그리지 않음

    color = COLORS[piece.color]
    for row_index, row in enumerate(piece.shape):
        for col_index, value in enumerate(row):
            if value:
                x = BOARD_X + (piece.x + col_index) * CELL_SIZE
                y = BOARD_Y + (drop_y + row_index) * CELL_SIZE
                # 채우지 않고 테두리만 그려 '그림자'처럼 보이게 한다
                pygame.draw.rect(screen, color, (x, y, CELL_SIZE, CELL_SIZE), 2)


def draw_piece(screen, piece):
    """현재 블록을 자기 색으로 화면에 그린다."""
    color = COLORS[piece.color]
    for row_index, row in enumerate(piece.shape):
        for col_index, value in enumerate(row):
            if value:
                draw_cell(screen, piece.x + col_index, piece.y + row_index, color)


# 한글이 보이도록 우선 시도할 시스템 폰트 목록 (윈도우 맑은 고딕 등)
KOREAN_FONTS = "malgungothic,gulim,dotum,batang,나눔고딕,notosanscjkkr"


def load_font(size):
    """한글을 지원하는 폰트를 찾아 반환한다. 없으면 기본 폰트로 대체한다."""
    matched = pygame.font.match_font(KOREAN_FONTS)
    if matched:
        return pygame.font.Font(matched, size)
    # 한글 폰트를 못 찾으면 기본 폰트 (한글은 네모로 보일 수 있음)
    return pygame.font.SysFont(None, size)


def main():
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("TETRIS")
    clock = pygame.time.Clock()
    font = load_font(28)
    big_font = load_font(48)

    # 배경 음악 준비 (파일이 없으면 music_ok=False로 두고 조용히 넘어간다)
    music_ok = False
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(BGM_PATH)
        pygame.mixer.music.set_volume(0.5)
        music_ok = True
    except pygame.error as e:
        print("배경 음악을 재생할 수 없습니다:", e)

    def music_play():
        if music_ok:
            pygame.mixer.music.play(-1)  # -1: 무한 반복

    def music_stop():
        if music_ok:
            pygame.mixer.music.stop()

    def music_pause():
        if music_ok:
            pygame.mixer.music.pause()

    def music_unpause():
        if music_ok:
            pygame.mixer.music.unpause()

    # 화면 가운데를 기준으로 메뉴 버튼을 배치한다
    cx = SCREEN_WIDTH // 2
    cy = SCREEN_HEIGHT // 2

    # 시작 화면 버튼
    start_button = Button("게임 시작", cx, cy + 20)

    # 일시정지 메뉴 버튼 (재시작=이어하기, RESET=처음부터, 게임 종료)
    pause_resume_button = Button("재시작", cx, cy - 20)
    pause_reset_button = Button("RESET", cx, cy + 44)
    pause_quit_button = Button("게임 종료", cx, cy + 108)

    # 게임 오버 메뉴 버튼
    over_reset_button = Button("RESET", cx, cy + 40)
    over_quit_button = Button("게임 종료", cx, cy + 104)

    # 게임 상태 변수 (아직 시작 전)
    board = create_board()
    next_queue = []
    current_piece = None
    score = 0
    fall_timer = 0  # 낙하 누적 시간(ms)
    state = STATE_START

    def reset_game():
        """보드/점수를 초기화하고 진행 상태로 만든다."""
        nonlocal board, next_queue, current_piece, score, fall_timer, state
        board, next_queue, current_piece = start_new_game()
        score = 0
        fall_timer = 0
        state = STATE_PLAYING
        music_play()

    running = True
    while running:
        dt = clock.tick(FPS)  # 지난 프레임 이후 경과 시간(ms)
        mouse_pos = pygame.mouse.get_pos()

        # 진행 중일 때만 낙하 시간을 누적한다
        if state == STATE_PLAYING:
            fall_timer += dt

        # ---- 입력 처리 ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif state == STATE_START:
                if start_button.is_clicked(event):
                    reset_game()

            elif state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = STATE_PAUSED
                        music_pause()
                    elif event.key == pygame.K_LEFT:
                        if is_valid_position(board, current_piece, offset_x=-1):
                            current_piece.x -= 1
                    elif event.key == pygame.K_RIGHT:
                        if is_valid_position(board, current_piece, offset_x=1):
                            current_piece.x += 1
                    elif event.key == pygame.K_UP:
                        # 벽차기 포함 회전
                        try_rotate(board, current_piece)
                    elif event.key == pygame.K_SPACE:
                        # 하드 드롭: 착지 위치로 한 번에 내리고 즉시 고정
                        current_piece.y = get_drop_y(board, current_piece)
                        current_piece, gained, over = lock_and_spawn(
                            board, current_piece, next_queue
                        )
                        score += gained
                        fall_timer = 0
                        if over:
                            state = STATE_GAMEOVER
                            music_stop()

            elif state == STATE_PAUSED:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    state = STATE_PLAYING  # ESC를 다시 누르면 이어하기
                    music_unpause()
                elif pause_resume_button.is_clicked(event):
                    state = STATE_PLAYING
                    music_unpause()
                elif pause_reset_button.is_clicked(event):
                    reset_game()
                elif pause_quit_button.is_clicked(event):
                    running = False

            elif state == STATE_GAMEOVER:
                if over_reset_button.is_clicked(event):
                    reset_game()
                elif over_quit_button.is_clicked(event):
                    running = False

        # ---- 자동 낙하 / 소프트 드롭 (진행 중일 때만) ----
        if state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                interval = SOFT_DROP_INTERVAL
            else:
                interval = get_fall_interval(score)

            if fall_timer >= interval:
                fall_timer = 0
                if is_valid_position(board, current_piece, offset_y=1):
                    current_piece.y += 1
                else:
                    # 더 못 내려가면 보드에 고정하고 줄 삭제 후 새 블록 생성
                    current_piece, gained, over = lock_and_spawn(
                        board, current_piece, next_queue
                    )
                    score += gained
                    if over:
                        state = STATE_GAMEOVER
                        music_stop()

        # ---- 화면 그리기 ----
        screen.fill(BLACK)
        draw_grid(screen)

        if state == STATE_START:
            draw_overlay(screen)
            draw_centered_title(screen, big_font, "TETRIS", cy - 70)
            start_button.draw(screen, font, mouse_pos)
        else:
            # 진행/일시정지/게임오버 공통: 보드와 현재 블록을 그린다
            draw_board(screen, board)
            if state in (STATE_PLAYING, STATE_PAUSED):
                draw_ghost(screen, board, current_piece)
                draw_piece(screen, current_piece)
            draw_panel(screen, font, score, next_queue)

            if state == STATE_PAUSED:
                draw_overlay(screen)
                draw_centered_title(screen, big_font, "일시정지", cy - 90)
                pause_resume_button.draw(screen, font, mouse_pos)
                pause_reset_button.draw(screen, font, mouse_pos)
                pause_quit_button.draw(screen, font, mouse_pos)
            elif state == STATE_GAMEOVER:
                draw_overlay(screen)
                draw_centered_title(screen, big_font, "GAME OVER", cy - 60)
                draw_centered_title(screen, font, f"SCORE  {score}", cy - 10)
                over_reset_button.draw(screen, font, mouse_pos)
                over_quit_button.draw(screen, font, mouse_pos)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
