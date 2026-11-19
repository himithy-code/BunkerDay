import asyncio
import pygame
import math
import random
import json
import os
import sys

pygame.init()

WIDTH, HEIGHT = 1200, 700
FPS = 60
WORLD_WIDTH = 4000
GROUND_Y = 590

BUILD_GRID_X = 40
BUILD_GRID_Y = 25
WALL_WIDTH = BUILD_GRID_X
WALL_HEIGHT = BUILD_GRID_Y * 5
RAMP_HEIGHT = BUILD_GRID_Y * 3
WIDE_BUILD_WIDTH = BUILD_GRID_X * 3
FLOOR_THICKNESS = BUILD_GRID_Y

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Fortnite 2D - Battle Royale')
clock = pygame.time.Clock()

font = pygame.font.SysFont('Arial', 23, bold=True)
small_font = pygame.font.SysFont('Arial', 17, bold=True)
big_font = pygame.font.SysFont('Arial', 64, bold=True)

SKY = (115, 190, 255)
WHITE = (255, 255, 255)
BLACK = (20, 20, 25)
BLUE = (45, 115, 220)
RED = (230, 55, 55)
GREEN = (75, 180, 75)
BROWN = (125, 80, 45)
YELLOW = (255, 220, 50)
BUILD_BLUE = (60, 180, 255)

KEYBIND_FOLDER = os.path.join(
    os.path.expanduser('~'),
    'Library',
    'Application Support',
    'Fortnite2D'
)
KEYBIND_FILE = os.path.join(KEYBIND_FOLDER, 'keybinds.json')

DEFAULT_KEYBINDS = {
    'Move left': pygame.K_a,
    'Move right': pygame.K_d,
    'Jump': pygame.K_SPACE,
    'Reload': pygame.K_r,
    'Edit': pygame.K_e,
    'Build mode': pygame.K_q,
    'Wall': pygame.K_1,
    'Floor': pygame.K_2,
    'Ramp': pygame.K_6,
    'Confirm edit': pygame.K_RETURN,
    'Break builds': pygame.K_g,
    'Weapon 1': pygame.K_3,
    'Weapon 2': pygame.K_4,
    'Weapon 3': pygame.K_5
}

keybinds = DEFAULT_KEYBINDS.copy()


def load_keybinds():
    try:
        with open(KEYBIND_FILE, 'r') as f:
            saved = json.load(f)

        for action, key in saved.items():
            if action in keybinds and isinstance(key, str):
                keybinds[action] = pygame.key.key_code(key)

    except (OSError, ValueError, TypeError):
        pass


def save_keybinds():
    try:
        os.makedirs(KEYBIND_FOLDER, exist_ok=True)

        with open(KEYBIND_FILE, 'w') as f:
            json.dump(
                {
                    name: pygame.key.name(key)
                    for name, key in keybinds.items()
                },
                f,
                indent=4
            )

        return True

    except OSError:
        return False


load_keybinds()

settings_open = False
waiting_for_key = None
settings_message = ''
settings_button = pygame.Rect(WIDTH - 155, 125, 135, 42)

platforms = [
    pygame.Rect(0, GROUND_Y, WORLD_WIDTH, 110),
    pygame.Rect(450, 470, 220, 25),
    pygame.Rect(900, 390, 250, 25),
    pygame.Rect(1450, 480, 240, 25),
    pygame.Rect(2050, 400, 250, 25),
    pygame.Rect(2750, 470, 250, 25),
    pygame.Rect(3400, 390, 300, 25)
]

buildings = [
    pygame.Rect(700, 490, 130, 100),
    pygame.Rect(1700, 490, 180, 100),
    pygame.Rect(2500, 490, 150, 100),
    pygame.Rect(3200, 490, 180, 100)
]

building_health = [100 for _ in buildings]

player = pygame.Rect(160, 400, 40, 75)
player_x = float(player.x)
player_y = float(player.y)

velocity_x = 0
velocity_y = 0

speed = 5
jump_power = -15
gravity = 0.7

on_ground = False
jump_buffer = 0
coyote_timer = 0

JUMP_BUFFER_TIME = 9
COYOTE_TIME = 9

health = 100
shield = 50

WEAPONS = [
    {
        'name': 'Pistol',
        'capacity': 16,
        'fire_delay': 18,
        'speed': 14,
        'damage': 34,
        'build_damage': 25,
        'pellets': 1,
        'spread': 0
    },
    {
        'name': 'Assault Rifle',
        'capacity': 30,
        'fire_delay': 7,
        'speed': 18,
        'damage': 25,
        'build_damage': 12,
        'pellets': 1,
        'spread': 0.025
    },
    {
        'name': 'Shotgun',
        'capacity': 8,
        'fire_delay': 38,
        'speed': 13,
        'damage': 20,
        'build_damage': 8,
        'pellets': 6,
        'spread': 0.22
    }
]

weapon_ammo = {
    w['name']: w['capacity']
    for w in WEAPONS
}

selected_weapon = 0
shoot_cooldown = 0
bullets = []

RARITIES = {
    'Common': {'multiplier': 1.00, 'color': (190, 190, 190)},
    'Uncommon': {'multiplier': 1.10, 'color': (80, 210, 100)},
    'Rare': {'multiplier': 1.20, 'color': (70, 145, 255)},
    'Epic': {'multiplier': 1.35, 'color': (185, 90, 235)},
    'Legendary': {'multiplier': 1.50, 'color': (255, 175, 45)}
}

RARITY_ROLLS = [
    ('Common', 45),
    ('Uncommon', 28),
    ('Rare', 16),
    ('Epic', 8),
    ('Legendary', 3)
]

weapon_rarities = ['Common' for _ in WEAPONS]
loot_drops = []

chests = [
    {'rect': pygame.Rect(x, GROUND_Y - 30, 34, 30), 'opened': False}
    for x in (560, 1080, 1550, 2250, 3050, 3650)
]

storm_center = (WORLD_WIDTH // 2, 390)
storm_start_radius = 2200
storm_end_radius = 520
storm_delay = 15.0
storm_shrink_duration = 150.0
storm_elapsed = 0.0
storm_damage_timer = 0.0
storm_damage_per_tick = 5
storm_tick_seconds = 1.0
storm_radius = storm_start_radius
storm_started = False

targets = []
bot_health = []
bot_shoot_cooldowns = []
bot_respawn_timers = []
enemy_bullets = []

game_mode = 'Battle Royale'
selected_mode = 'Battle Royale'
game_started = False
eliminations = 0
DEATHMATCH_GOAL = 10

MODE_BUTTONS = {
    'Battle Royale': pygame.Rect(190, 300, 250, 82),
    'Bot Deathmatch': pygame.Rect(475, 300, 250, 82),
    'Practice': pygame.Rect(760, 300, 250, 82)
}
START_BUTTON = pygame.Rect(425, 435, 350, 82)

build_mode = False
break_mode = False
build_type = 'wall'

materials = 100
build_cost = 10

placed_builds = []

break_message = ''
break_message_timer = 0

editing = False
active_build_index = None
edit_selection = set()

game_won = False

EDIT_PRESETS = {
    'short': {(0, 0)},
    'really_short': {(0, 0), (1, 0)},
    'window': {(1, 0)},
    'door': {(1, 0), (2, 0)}
}

camera_x = 0
player_facing = 1


def roll_rarity():
    roll = random.randint(1, sum(weight for _, weight in RARITY_ROLLS))
    total = 0

    for rarity, weight in RARITY_ROLLS:
        total += weight

        if roll <= total:
            return rarity

    return 'Common'


def drop_loot(world_x, world_y):
    loot_type = random.choices(
        ['ammo', 'shield', 'health', 'materials', 'weapon'],
        weights=[35, 20, 18, 17, 10],
        k=1
    )[0]

    item = {
        'type': loot_type,
        'rect': pygame.Rect(int(world_x - 12), int(world_y - 12), 24, 24),
        'amount': 0,
        'rarity': roll_rarity(),
        'weapon_index': random.randrange(len(WEAPONS))
    }

    if loot_type == 'ammo':
        item['amount'] = random.randint(8, 20)
    elif loot_type in ('shield', 'health'):
        item['amount'] = 25
    elif loot_type == 'materials':
        item['amount'] = 20
    else:
        item['amount'] = 1

    loot_drops.append(item)


def open_nearby_chest():
    for chest in chests:
        if chest['opened']:
            continue

        if player.inflate(90, 70).colliderect(chest['rect']):
            chest['opened'] = True

            for _ in range(2):
                drop_loot(
                    chest['rect'].centerx + random.randint(-20, 20),
                    chest['rect'].top - random.randint(8, 25)
                )

            return True

    return False


def collect_loot():
    global health, shield, materials

    for item in loot_drops[:]:
        if not player.colliderect(item['rect']):
            continue

        kind = item['type']
        amount = item['amount']

        if kind == 'ammo':
            weapon_index = item['weapon_index']
            weapon_name = WEAPONS[weapon_index]['name']

            weapon_ammo[weapon_name] = min(
                WEAPONS[weapon_index]['capacity'] * 3,
                weapon_ammo[weapon_name] + amount
            )

        elif kind == 'health':
            if health >= 100:
                continue
            health = min(100, health + amount)

        elif kind == 'shield':
            if shield >= 100:
                continue
            shield = min(100, shield + amount)

        elif kind == 'materials':
            materials = min(500, materials + amount)

        elif kind == 'weapon':
            weapon_index = item['weapon_index']
            current = weapon_rarities[weapon_index]
            rarity_order = list(RARITIES)

            if rarity_order.index(item['rarity']) > rarity_order.index(current):
                weapon_rarities[weapon_index] = item['rarity']

            weapon_name = WEAPONS[weapon_index]['name']

            weapon_ammo[weapon_name] = min(
                WEAPONS[weapon_index]['capacity'] * 3,
                weapon_ammo[weapon_name] + WEAPONS[weapon_index]['capacity']
            )

        loot_drops.remove(item)


def update_storm(dt):
    global storm_elapsed, storm_radius, storm_started
    global storm_damage_timer, health, shield

    seconds = dt / 60.0
    storm_elapsed += seconds

    if storm_elapsed > storm_delay:
        storm_started = True

        progress = min(
            1.0,
            (storm_elapsed - storm_delay) / storm_shrink_duration
        )

        storm_radius = (
            storm_start_radius
            - (storm_start_radius - storm_end_radius) * progress
        )

    player_distance = math.hypot(
        player.centerx - storm_center[0],
        player.centery - storm_center[1]
    )

    if storm_started and player_distance > storm_radius:
        storm_damage_timer += seconds

        while storm_damage_timer >= storm_tick_seconds and health > 0:
            storm_damage_timer -= storm_tick_seconds
            damage = storm_damage_per_tick

            absorbed = min(shield, damage)
            shield -= absorbed
            health = max(0, health - (damage - absorbed))

    else:
        storm_damage_timer = 0.0


def ramp_surface_y(build, world_x):
    rect = build['rect']

    progress = (world_x - rect.left) / max(1, rect.width)
    progress = max(0.0, min(1.0, progress))

    if build.get('orientation', 1) == 1:
        return rect.bottom - progress * rect.height

    return rect.top + progress * rect.height


def find_build_support_y(center_x, mouse_y, build_width=1):
    possible_surfaces = []

    build_left = center_x - build_width / 2
    build_right = center_x + build_width / 2

    for platform in platforms:
        overlaps = (
            platform.left < build_right
            and platform.right > build_left
        ) if build_width > 1 else (
            platform.left <= center_x <= platform.right
        )

        if overlaps:
            possible_surfaces.append(platform.top)

    for build in placed_builds:
        rect = build['rect']

        overlaps = (
            rect.left < build_right
            and rect.right > build_left
        ) if build_width > 1 else (
            rect.left <= center_x <= rect.right
        )

        if not overlaps:
            continue

        sample_x = max(rect.left, min(center_x, rect.right))

        if build['type'] == 'ramp':
            possible_surfaces.append(
                int(round(ramp_surface_y(build, sample_x)))
            )
        else:
            possible_surfaces.append(rect.top)

    possible_surfaces = [
        y for y in possible_surfaces
        if 0 <= y <= GROUND_Y
    ]

    if not possible_surfaces:
        return GROUND_Y

    return min(
        possible_surfaces,
        key=lambda surface_y: abs(surface_y - mouse_y)
    )


def get_build_rect(mouse_x, mouse_y):
    world_x = mouse_x + camera_x

    if build_type == 'wall':
        width = WALL_WIDTH
        height = WALL_HEIGHT
    elif build_type == 'ramp':
        width = WIDE_BUILD_WIDTH
        height = RAMP_HEIGHT
    else:
        width = WIDE_BUILD_WIDTH
        height = FLOOR_THICKNESS

    grid_left = round(
        (world_x - width / 2) / BUILD_GRID_X
    ) * BUILD_GRID_X

    center_x = grid_left + width / 2

    support_y = find_build_support_y(
        center_x,
        mouse_y,
        width
    )

    if build_type == 'floor':
        # Floors sit ON TOP of the support surface.
        # They can extend beyond the platform edge.
        top = support_y - FLOOR_THICKNESS
    else:
        top = support_y - height

    return pygame.Rect(
        int(grid_left),
        int(round(top)),
        int(width),
        int(height)
    )


def get_build_cells(build):
    rect = build['rect']
    cells = []

    if build['type'] == 'ramp':
        for col in range(3):
            left = rect.left + col * rect.width // 3
            right = rect.left + (col + 1) * rect.width // 3

            top = int(min(
                ramp_surface_y(build, left),
                ramp_surface_y(build, right)
            ))

            cell = pygame.Rect(
                left,
                top,
                right - left,
                rect.bottom - top
            )

            cells.append((0, col, cell))

    else:
        for row in range(3):
            top = rect.top + row * rect.height // 3
            bottom = rect.top + (row + 1) * rect.height // 3

            cell = pygame.Rect(
                rect.left,
                top,
                rect.width,
                bottom - top
            )

            cells.append((row, 0, cell))

    return cells


def get_build_collision_rects():
    result = []

    for build in placed_builds:
        if build['type'] == 'ramp':
            continue

        for row, col, cell in get_build_cells(build):
            if (row, col) not in build['removed']:
                result.append(cell)

    return result


def point_in_build_cell(build, row, col, world_x, world_y):
    if build['type'] == 'ramp':
        rect = build['rect']

        left = rect.left + col * rect.width // 3
        right = rect.left + (col + 1) * rect.width // 3

        return (
            left <= world_x <= right
            and rect.top <= world_y <= rect.bottom
            and world_y >= ramp_surface_y(build, world_x)
        )

    for cell_row, cell_col, cell in get_build_cells(build):
        if (cell_row, cell_col) == (row, col):
            return cell.collidepoint(world_x, world_y)

    return False


def bullet_hits_build(build, world_x, world_y):
    offsets = [(0, 0), (-4, 0), (4, 0), (0, -4), (0, 4)]

    for row, col, cell in get_build_cells(build):
        if (row, col) in build['removed']:
            continue

        for offset_x, offset_y in offsets:
            if point_in_build_cell(
                build,
                row,
                col,
                world_x + offset_x,
                world_y + offset_y
            ):
                return True

    return False


def damage_build_from_bullet(build_index, damage):
    global materials, break_message, break_message_timer

    build = placed_builds[build_index]
    build['health'] -= damage

    if build['health'] <= 0:
        placed_builds.pop(build_index)

        gained = min(10, 500 - materials)
        materials += gained

        break_message = f'BUILD DESTROYED: +{gained} MATERIALS'
    else:
        break_message = f"BUILD HIT: {build['health']} HP LEFT"

    break_message_timer = 75


def bullet_hits_structure(world_x, world_y, damage):
    # Player-built pieces can take damage. Houses and terrain only stop bullets.
    for index in range(len(placed_builds) - 1, -1, -1):
        build = placed_builds[index]
        if bullet_hits_build(build, world_x, world_y):
            damage_build_from_bullet(index, damage)
            return True

    for house in buildings:
        if house.collidepoint(world_x, world_y):
            return True

    for platform in platforms:
        if platform.collidepoint(world_x, world_y):
            return True

    return False


def create_bot_positions(count):
    result = []
    attempts = 0
    while len(result) < count and attempts < count * 40:
        attempts += 1
        x = random.randint(500, WORLD_WIDTH - 100)
        candidate = pygame.Rect(x, GROUND_Y - 55, 35, 55)
        if any(candidate.colliderect(house) for house in buildings):
            continue
        if any(abs(candidate.centerx - other.centerx) < 180 for other in result):
            continue
        result.append(candidate)
    return result


def start_match(mode):
    global game_mode, game_started, game_won, eliminations
    global health, shield, player_x, player_y, velocity_x, velocity_y
    global on_ground, jump_buffer, coyote_timer, camera_x
    global storm_elapsed, storm_radius, storm_started, storm_damage_timer
    global materials, selected_weapon, shoot_cooldown, build_mode, break_mode
    global editing, active_build_index, break_message, break_message_timer

    game_mode = mode
    game_won = False
    eliminations = 0
    health = 100
    shield = 50
    player.x = 160
    player.y = 400
    player_x = float(player.x)
    player_y = float(player.y)
    velocity_x = 0
    velocity_y = 0
    on_ground = False
    jump_buffer = 0
    coyote_timer = 0
    camera_x = 0
    storm_elapsed = 0.0
    storm_radius = storm_start_radius
    storm_started = False
    storm_damage_timer = 0.0
    materials = 100
    selected_weapon = 0
    shoot_cooldown = 0
    build_mode = False
    break_mode = False
    editing = False
    active_build_index = None
    break_message = ''
    break_message_timer = 0
    placed_builds.clear()
    loot_drops.clear()
    bullets.clear()
    enemy_bullets.clear()
    for chest in chests:
        chest['opened'] = False
    for weapon in WEAPONS:
        weapon_ammo[weapon['name']] = weapon['capacity']

    count = 12 if mode == 'Battle Royale' else 6 if mode == 'Bot Deathmatch' else 0
    targets[:] = create_bot_positions(count)
    bot_health[:] = [100 for _ in targets]
    bot_shoot_cooldowns[:] = [random.uniform(25, 90) for _ in targets]
    bot_respawn_timers[:] = [0 for _ in targets]
    game_started = True


def draw_lobby():
    screen.fill((24, 35, 58))
    for i in range(12):
        x = (i * 125 + 35) % WIDTH
        pygame.draw.circle(screen, (35, 52, 80), (x, 160 + (i % 3) * 35), 55)

    title = big_font.render('FORTNITE 2D', True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 145)))
    subtitle = font.render('CHOOSE A GAME MODE', True, (160, 210, 255))
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 235)))

    for mode, rect in MODE_BUTTONS.items():
        selected = mode == selected_mode
        color = (45, 125, 210) if selected else (55, 70, 95)
        pygame.draw.rect(screen, color, rect, border_radius=12)
        pygame.draw.rect(screen, YELLOW if selected else WHITE,
                         rect, 3, border_radius=12)
        label = small_font.render(mode.upper(), True, WHITE)
        screen.blit(label, label.get_rect(center=rect.center))

    pygame.draw.rect(screen, (35, 165, 95), START_BUTTON, border_radius=14)
    pygame.draw.rect(screen, WHITE, START_BUTTON, 3, border_radius=14)
    start_label = font.render('PLAY', True, WHITE)
    screen.blit(start_label, start_label.get_rect(center=START_BUTTON.center))

    descriptions = {
        'Battle Royale': '12 bots | Be the last player standing | Storm enabled',
        'Bot Deathmatch': '6 bots | First to 10 eliminations | Bots respawn',
        'Practice': 'No enemies | Practice aiming, building and editing'
    }
    description = small_font.render(descriptions[selected_mode], True, WHITE)
    screen.blit(description, description.get_rect(center=(WIDTH // 2, 555)))
    hint = small_font.render(
        'Click a mode, then click PLAY', True, (190, 205, 225))
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 610)))


def place_build():
    global materials

    if materials < build_cost:
        return

    mx, my = pygame.mouse.get_pos()
    new_rect = get_build_rect(mx, my)

    if new_rect.left < 0 or new_rect.right > WORLD_WIDTH:
        return

    if new_rect.top < 0 or new_rect.bottom > GROUND_Y + FLOOR_THICKNESS:
        return

    if new_rect.colliderect(player):
        return

    # Prevent overlapping other player-built pieces.
    if any(new_rect.colliderect(b['rect']) for b in placed_builds):
        return

    # Floors are allowed to hang over an edge. Their support is checked
    # using any horizontal overlap with a platform or existing build.
    if build_type == 'floor':
        has_support = False

        for platform in platforms:
            if (
                platform.left < new_rect.right
                and platform.right > new_rect.left
                and abs(platform.top - new_rect.bottom) <= 2
            ):
                has_support = True
                break

        if not has_support:
            for build in placed_builds:
                rect = build['rect']

                if (
                    rect.left < new_rect.right
                    and rect.right > new_rect.left
                    and abs(rect.top - new_rect.bottom) <= 2
                ):
                    has_support = True
                    break

        if not has_support:
            return

    placed_builds.append({
        'rect': new_rect,
        'type': build_type,
        'orientation': player_facing if build_type == 'ramp' else 1,
        'removed': set(),
        'health': 100
    })

    materials -= build_cost


def find_build_at_mouse():
    mx, my = pygame.mouse.get_pos()
    world_mx = mx + camera_x

    for index in range(len(placed_builds) - 1, -1, -1):
        build = placed_builds[index]

        if build['rect'].collidepoint(world_mx, my):
            for row, col, cell in get_build_cells(build):
                if (
                    (row, col) not in build['removed']
                    and point_in_build_cell(
                        build, row, col, world_mx, my
                    )
                ):
                    return index

    return None


def start_editing():
    global editing, active_build_index, edit_selection

    index = find_build_at_mouse()

    if index is None:
        return

    editing = True
    active_build_index = index
    edit_selection = set(placed_builds[index]['removed'])


def confirm_edit():
    global editing, active_build_index, edit_selection

    if not editing or active_build_index is None:
        return

    placed_builds[active_build_index]['removed'] = set(edit_selection)

    editing = False
    active_build_index = None
    edit_selection = set()


def cancel_edit():
    global editing, active_build_index, edit_selection

    editing = False
    active_build_index = None
    edit_selection = set()


def apply_edit_preset(name):
    global edit_selection

    if (
        editing
        and active_build_index is not None
        and placed_builds[active_build_index]['type'] == 'wall'
        and name in EDIT_PRESETS
    ):
        edit_selection = set(EDIT_PRESETS[name])
        confirm_edit()


def toggle_edit_section():
    if not editing or active_build_index is None:
        return False

    build = placed_builds[active_build_index]
    rect = build['rect']

    mx, my = pygame.mouse.get_pos()
    world_mx = mx + camera_x

    if not rect.collidepoint(world_mx, my):
        return False

    if build['type'] == 'ramp':
        col = int((world_mx - rect.left) * 3 / rect.width)
        col = max(0, min(2, col))
        section = (0, col)

        if not point_in_build_cell(build, 0, col, world_mx, my):
            return False
    else:
        row = int((my - rect.top) * 3 / rect.height)
        row = max(0, min(2, row))
        section = (row, 0)

    if section in edit_selection:
        edit_selection.remove(section)
    else:
        edit_selection.add(section)

    return True


def break_build_at_mouse():
    global materials, break_message, break_message_timer

    mx, my = pygame.mouse.get_pos()
    world_mouse = (mx + camera_x, my)

    for index in range(len(buildings) - 1, -1, -1):
        house = buildings[index]

        if house.collidepoint(world_mouse):
            building_health[index] -= 25

            if building_health[index] <= 0:
                buildings.pop(index)
                building_health.pop(index)

                gained = min(30, 500 - materials)
                materials += gained
                break_message = f'HOUSE DESTROYED: +{gained} MATERIALS'
            else:
                break_message = f'HOUSE HIT: {building_health[index]} HP LEFT'

            break_message_timer = 90
            return

    for index in range(len(placed_builds) - 1, -1, -1):
        build = placed_builds[index]

        if build['rect'].collidepoint(world_mouse):
            build['health'] -= 50

            if build['health'] <= 0:
                placed_builds.pop(index)

                gained = min(10, 500 - materials)
                materials += gained
                break_message = f'BUILD DESTROYED: +{gained} MATERIALS'
            else:
                break_message = f"BUILD HIT: {build['health']} HP LEFT"

            break_message_timer = 90
            return

    break_message = 'CLICK DIRECTLY ON A HOUSE OR BUILD'
    break_message_timer = 90


def draw_text(text, x, y, color=WHITE, selected_font=None):
    if selected_font is None:
        selected_font = font

    screen.blit(
        selected_font.render(text, True, color),
        (x, y)
    )


def draw_health_bar(rect, value):
    pygame.draw.rect(
        screen, BLACK,
        (rect.x, rect.y - 9, rect.width, 5)
    )

    pygame.draw.rect(
        screen, (70, 230, 90),
        (
            rect.x, rect.y - 9,
            int(rect.width * max(0, value) / 100), 5
        )
    )


async def main():
    global break_message_timer, break_message
    global settings_open, waiting_for_key, settings_message
    global game_won, jump_buffer, selected_weapon
    global break_mode, build_mode, build_type, editing
    global velocity_x, velocity_y, player_x, player_y
    global player_facing, on_ground, coyote_timer, camera_x
    global shoot_cooldown, targets, bullets, health, shield
    global game_started, selected_mode, game_mode, eliminations
    global bot_health, bot_shoot_cooldowns, bot_respawn_timers, enemy_bullets
    running = True

    while running:
        # Yield control so the browser can process events and render each frame.
        await asyncio.sleep(0)
        # Keep frame timing bounded if the browser briefly stalls.
        dt = min(clock.tick(FPS) / 16.67, 3.0)

        if break_message_timer > 0:
            break_message_timer -= 1

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            if not game_started:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        selected_mode = 'Battle Royale'
                    elif event.key == pygame.K_2:
                        selected_mode = 'Bot Deathmatch'
                    elif event.key == pygame.K_3:
                        selected_mode = 'Practice'
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        start_match(selected_mode)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for mode, mode_rect in MODE_BUTTONS.items():
                        if mode_rect.collidepoint(event.pos):
                            selected_mode = mode
                    if START_BUTTON.collidepoint(event.pos):
                        start_match(selected_mode)
                continue

            if event.type == pygame.KEYDOWN:

                if settings_open:
                    if waiting_for_key is not None:
                        used_by = next(
                            (
                                name for name, value in keybinds.items()
                                if value == event.key and name != waiting_for_key
                            ),
                            None
                        )

                        if used_by:
                            settings_message = f'That key is already used for {used_by}.'
                        else:
                            keybinds[waiting_for_key] = event.key

                            if save_keybinds():
                                settings_message = f'{waiting_for_key} saved!'
                            else:
                                settings_message = 'Could not save keybinds.'

                            waiting_for_key = None

                    elif event.key == pygame.K_ESCAPE:
                        settings_open = False

                    continue

                if game_won:
                    continue

                if editing:
                    if event.key == keybinds['Confirm edit']:
                        confirm_edit()
                    elif event.key == pygame.K_ESCAPE:
                        cancel_edit()
                    elif event.key == pygame.K_1:
                        apply_edit_preset('short')
                    elif event.key == pygame.K_2:
                        apply_edit_preset('really_short')
                    elif event.key == pygame.K_3:
                        apply_edit_preset('window')
                    elif event.key == pygame.K_4:
                        apply_edit_preset('door')

                    continue

                if event.key == keybinds['Jump']:
                    jump_buffer = JUMP_BUFFER_TIME

                if event.key == keybinds['Reload']:
                    weapon = WEAPONS[selected_weapon]
                    weapon_ammo[weapon['name']] = weapon['capacity']

                if event.key == keybinds['Edit']:
                    start_editing()

                if event.key == pygame.K_f:
                    open_nearby_chest()

                if event.key == keybinds['Break builds']:
                    break_mode = not break_mode
                    build_mode = False

                if event.key == keybinds['Build mode']:
                    build_mode = not build_mode
                    break_mode = False

                if event.key == keybinds['Wall']:
                    build_type = 'wall'
                    build_mode = True
                    break_mode = False

                if event.key == keybinds['Floor']:
                    build_type = 'floor'
                    build_mode = True
                    break_mode = False

                if event.key == keybinds['Ramp']:
                    build_type = 'ramp'
                    build_mode = True
                    break_mode = False

                if event.key == keybinds['Weapon 1']:
                    selected_weapon = 0

                if event.key == keybinds['Weapon 2']:
                    selected_weapon = 1

                if event.key == keybinds['Weapon 3']:
                    selected_weapon = 2

                if event.key == pygame.K_ESCAPE:
                    build_mode = False
                    break_mode = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                if settings_open:
                    if settings_button.collidepoint(event.pos):
                        settings_open = False
                    else:
                        for index, action in enumerate(keybinds):
                            row = pygame.Rect(
                                325, 120 + index * 38, 550, 34
                            )

                            if row.collidepoint(event.pos):
                                waiting_for_key = action
                                settings_message = f'Press a key for {action}...'
                                break

                elif game_won:
                    pass

                elif settings_button.collidepoint(event.pos):
                    settings_open = True
                    waiting_for_key = None
                    settings_message = 'Click an action, then press its new key.'

                elif editing:
                    if toggle_edit_section():
                        confirm_edit()

                elif build_mode:
                    place_build()

                elif break_mode:
                    break_build_at_mouse()

                else:
                    weapon = WEAPONS[selected_weapon]
                    ammo = weapon_ammo[weapon['name']]

                    if ammo > 0 and shoot_cooldown <= 0:
                        mx, my = pygame.mouse.get_pos()
                        world_mx = mx + camera_x

                        start_x = player.centerx
                        start_y = player.centery

                        base_angle = math.atan2(
                            my - start_y,
                            world_mx - start_x
                        )

                        rarity_multiplier = RARITIES[
                            weapon_rarities[selected_weapon]
                        ]['multiplier']

                        for _ in range(weapon['pellets']):
                            angle = base_angle + random.uniform(
                                -weapon['spread'],
                                weapon['spread']
                            )

                            bullets.append([
                                float(start_x),
                                float(start_y),
                                math.cos(angle) * weapon['speed'],
                                math.sin(angle) * weapon['speed'],
                                int(weapon['damage'] * rarity_multiplier),
                                int(weapon['build_damage'] * rarity_multiplier)
                            ])

                        weapon_ammo[weapon['name']] -= 1
                        shoot_cooldown = weapon['fire_delay']

        if not game_started:
            draw_lobby()
            pygame.display.flip()
            continue

        if settings_open:
            dt = 0

        keys = pygame.key.get_pressed()
        mouse_x_now, _ = pygame.mouse.get_pos()

        player_facing = (
            1 if mouse_x_now + camera_x >= player.centerx else -1
        )

        velocity_x = 0

        if not editing and not settings_open and not game_won:
            if keys[keybinds['Move left']]:
                velocity_x = -speed
            if keys[keybinds['Move right']]:
                velocity_x = speed

        player_x += velocity_x * dt
        player.x = round(player_x)

        all_platforms = platforms + get_build_collision_rects()

        for platform in all_platforms:
            if player.colliderect(platform):
                if velocity_x > 0:
                    player.right = platform.left
                elif velocity_x < 0:
                    player.left = platform.right

                player_x = float(player.x)

        previous_bottom = player.bottom
        previous_top = player.top
        was_on_ground = on_ground

        if not game_won:
            velocity_y += gravity * dt
            player_y += velocity_y * dt

        player.y = round(player_y)
        on_ground = False

        all_platforms = platforms + get_build_collision_rects()

        for platform in all_platforms:
            horizontal_overlap = (
                player.right > platform.left
                and player.left < platform.right
            )

            if not horizontal_overlap:
                continue

            if (
                velocity_y >= 0
                and previous_bottom <= platform.top
                and player.bottom >= platform.top
            ):
                player.bottom = platform.top
                player_y = float(player.y)
                velocity_y = 0
                on_ground = True

            elif (
                velocity_y < 0
                and previous_top >= platform.bottom
                and player.top <= platform.bottom
            ):
                player.top = platform.bottom
                player_y = float(player.y)
                velocity_y = 0

        for build in placed_builds:
            if build['type'] != 'ramp':
                continue

            rect = build['rect']

            for col in range(3):
                if (0, col) in build['removed']:
                    continue

                segment_left = rect.left + col * rect.width // 3
                segment_right = rect.left + (col + 1) * rect.width // 3

                if (
                    player.right <= segment_left
                    or player.left >= segment_right
                ):
                    continue

                sample_x = max(
                    segment_left,
                    min(player.centerx, segment_right)
                )

                surface_y = int(ramp_surface_y(build, sample_x))

                crossed_surface = (
                    velocity_y >= 0
                    and previous_bottom <= surface_y + 12
                    and player.bottom >= surface_y
                )

                following_slope = (
                    was_on_ground
                    and velocity_y >= 0
                    and abs(previous_bottom - surface_y) <= 12
                )

                if crossed_surface or following_slope:
                    player.bottom = surface_y
                    player_y = float(player.y)
                    velocity_y = 0
                    on_ground = True

        if on_ground:
            coyote_timer = COYOTE_TIME
        else:
            coyote_timer = max(0, coyote_timer - dt)

        jump_buffer = max(0, jump_buffer - dt)

        if not game_won and jump_buffer > 0 and coyote_timer > 0:
            velocity_y = jump_power
            on_ground = False
            jump_buffer = 0
            coyote_timer = 0

        if player.left < 0:
            player.left = 0

        if player.right > WORLD_WIDTH:
            player.right = WORLD_WIDTH

        player_x = float(player.x)

        camera_x = player.centerx - WIDTH // 2
        camera_x = max(0, min(camera_x, WORLD_WIDTH - WIDTH))

        if shoot_cooldown > 0:
            shoot_cooldown -= dt

        if not game_won:
            # Move the player's bullets. Every platform, house and build blocks shots.
            for bullet in bullets[:]:
                old_x, old_y = bullet[0], bullet[1]
                new_x = old_x + bullet[2] * dt
                new_y = old_y + bullet[3] * dt
                distance = math.hypot(new_x - old_x, new_y - old_y)
                steps = max(1, int(math.ceil(distance / 4)))
                bullet_removed = False

                for step in range(1, steps + 1):
                    progress = step / steps
                    check_x = old_x + (new_x - old_x) * progress
                    check_y = old_y + (new_y - old_y) * progress

                    if bullet_hits_structure(check_x, check_y, bullet[5]):
                        bullets.remove(bullet)
                        bullet_removed = True
                        break

                    bullet_rect = pygame.Rect(
                        int(check_x - 5), int(check_y - 5), 10, 10)
                    hit_index = next(
                        (i for i, target in enumerate(targets)
                         if target.x >= 0 and bullet_rect.colliderect(target)),
                        None
                    )

                    if hit_index is not None:
                        bot_health[hit_index] -= bullet[4]
                        if bot_health[hit_index] <= 0:
                            defeated = targets[hit_index]
                            drop_loot(defeated.centerx, defeated.centery)
                            eliminations += 1
                            if game_mode == 'Bot Deathmatch':
                                targets[hit_index].x = -1000
                                bot_respawn_timers[hit_index] = 150
                                bot_health[hit_index] = 100
                            else:
                                targets.pop(hit_index)
                                bot_health.pop(hit_index)
                                bot_shoot_cooldowns.pop(hit_index)
                                bot_respawn_timers.pop(hit_index)
                        bullets.remove(bullet)
                        bullet_removed = True
                        break

                if bullet_removed:
                    continue
                bullet[0], bullet[1] = new_x, new_y
                if new_x < 0 or new_x > WORLD_WIDTH or new_y < -50 or new_y > HEIGHT + 50:
                    bullets.remove(bullet)

            # Bot AI: respawn, approach the player, aim and fire back.
            if game_mode != 'Practice':
                for index, bot in enumerate(targets):
                    if bot.x < 0:
                        bot_respawn_timers[index] -= dt
                        if bot_respawn_timers[index] <= 0:
                            fresh = create_bot_positions(1)
                            if fresh:
                                targets[index] = fresh[0]
                            else:
                                targets[index].x = random.randint(
                                    500, WORLD_WIDTH - 100)
                            bot_health[index] = 100
                            bot_shoot_cooldowns[index] = 45
                        continue

                    dx = player.centerx - bot.centerx
                    if abs(dx) > 250:
                        step_x = (1 if dx > 0 else -1) * 1.05 * dt
                        candidate = bot.copy()
                        candidate.x += round(step_x)
                        if candidate.left >= 0 and candidate.right <= WORLD_WIDTH and not any(candidate.colliderect(h) for h in buildings):
                            bot.x = candidate.x

                    bot_shoot_cooldowns[index] -= dt
                    distance_to_player = math.hypot(
                        player.centerx - bot.centerx, player.centery - bot.centery)
                    if distance_to_player < 850 and bot_shoot_cooldowns[index] <= 0:
                        aim_angle = math.atan2(
                            player.centery - bot.centery, player.centerx - bot.centerx)
                        spread = random.uniform(-0.055, 0.055)
                        aim_angle += spread
                        enemy_bullets.append([
                            float(bot.centerx), float(bot.centery),
                            math.cos(aim_angle) * 12,
                            math.sin(aim_angle) * 12,
                            8
                        ])
                        bot_shoot_cooldowns[index] = random.uniform(65, 105)

            # Enemy bullets are stopped by the same world obstacles and can hit the player.
            for bullet in enemy_bullets[:]:
                old_x, old_y = bullet[0], bullet[1]
                new_x = old_x + bullet[2] * dt
                new_y = old_y + bullet[3] * dt
                distance = math.hypot(new_x - old_x, new_y - old_y)
                steps = max(1, int(math.ceil(distance / 4)))
                removed = False
                for step in range(1, steps + 1):
                    progress = step / steps
                    check_x = old_x + (new_x - old_x) * progress
                    check_y = old_y + (new_y - old_y) * progress
                    if bullet_hits_structure(check_x, check_y, 8):
                        enemy_bullets.remove(bullet)
                        removed = True
                        break
                    hit_rect = pygame.Rect(
                        int(check_x - 5), int(check_y - 5), 10, 10)
                    if hit_rect.colliderect(player):
                        damage = bullet[4]
                        absorbed = min(shield, damage)
                        shield -= absorbed
                        health = max(0, health - (damage - absorbed))
                        enemy_bullets.remove(bullet)
                        removed = True
                        break
                if not removed:
                    bullet[0], bullet[1] = new_x, new_y
                    if new_x < 0 or new_x > WORLD_WIDTH or new_y < -50 or new_y > HEIGHT + 50:
                        enemy_bullets.remove(bullet)

        if game_mode == 'Battle Royale' and len(targets) == 0 and health > 0:
            game_won = True
        elif game_mode == 'Bot Deathmatch' and eliminations >= DEATHMATCH_GOAL and health > 0:
            game_won = True

        if game_won:
            build_mode = False
            break_mode = False
            editing = False
            bullets.clear()
            enemy_bullets.clear()

        collect_loot()

        if not game_won and game_mode == 'Battle Royale':
            update_storm(dt)

        screen.fill(SKY)

        storm_screen_center = (
            int(storm_center[0] - camera_x),
            int(storm_center[1])
        )

        if game_mode == 'Battle Royale':
            pygame.draw.circle(
                screen,
                (80, 120, 255),
                storm_screen_center,
                max(1, int(storm_radius)),
                5
            )

        for i in range(12):
            cloud_x = (i * 400 - camera_x // 3) % 1500
            cloud_y = 80 + i % 4 * 45

            pygame.draw.circle(screen, WHITE, (int(cloud_x), cloud_y), 25)
            pygame.draw.circle(
                screen, WHITE,
                (int(cloud_x + 25), cloud_y + 5), 22
            )

        for i in range(10):
            hill_x = i * 500 - camera_x // 2
            pygame.draw.ellipse(
                screen,
                (95, 175, 105),
                (hill_x, 390, 600, 300)
            )

        for platform in platforms:
            rect = pygame.Rect(
                platform.x - camera_x,
                platform.y,
                platform.width,
                platform.height
            )

            pygame.draw.rect(screen, BROWN, rect)
            pygame.draw.rect(
                screen, GREEN,
                (rect.x, rect.y, rect.width, 12)
            )

        for index, house in enumerate(buildings):
            rect = pygame.Rect(
                house.x - camera_x,
                house.y,
                house.width,
                house.height
            )

            pygame.draw.rect(screen, (190, 140, 90), rect)
            pygame.draw.rect(screen, (100, 65, 40), rect, 4)

            pygame.draw.rect(
                screen, (90, 150, 220),
                (rect.x + 15, rect.y + 20, 35, 35)
            )

            pygame.draw.rect(
                screen, (90, 150, 220),
                (rect.x + 75, rect.y + 20, 35, 35)
            )

            draw_health_bar(rect, building_health[index])

        for chest in chests:
            chest_rect = pygame.Rect(
                chest['rect'].x - camera_x,
                chest['rect'].y,
                chest['rect'].width,
                chest['rect'].height
            )

            chest_color = (
                (105, 90, 65)
                if chest['opened']
                else (245, 180, 35)
            )

            pygame.draw.rect(
                screen, chest_color, chest_rect, border_radius=5
            )
            pygame.draw.rect(
                screen, (75, 50, 25), chest_rect, 3, border_radius=5
            )
            pygame.draw.line(
                screen, (255, 230, 120),
                (chest_rect.left + 5, chest_rect.top + 8),
                (chest_rect.right - 5, chest_rect.top + 8),
                3
            )

        loot_symbols = {
            'ammo': 'A',
            'health': '+',
            'shield': 'S',
            'materials': 'M',
            'weapon': 'W'
        }

        for item in loot_drops:
            item_rect = pygame.Rect(
                item['rect'].x - camera_x,
                item['rect'].y,
                item['rect'].width,
                item['rect'].height
            )

            if item['type'] == 'weapon':
                item_color = RARITIES[item['rarity']]['color']
            elif item['type'] == 'health':
                item_color = (70, 220, 100)
            elif item['type'] == 'shield':
                item_color = (65, 150, 255)
            elif item['type'] == 'materials':
                item_color = (180, 135, 85)
            else:
                item_color = (245, 210, 60)

            pygame.draw.rect(
                screen, item_color, item_rect, border_radius=5
            )
            pygame.draw.rect(
                screen, WHITE, item_rect, 2, border_radius=5
            )

            symbol = small_font.render(
                loot_symbols[item['type']], True, BLACK
            )

            screen.blit(
                symbol,
                symbol.get_rect(center=item_rect.center)
            )

        for build in placed_builds:
            rect = pygame.Rect(
                build['rect'].x - camera_x,
                build['rect'].y,
                build['rect'].width,
                build['rect'].height
            )

            for row, col, cell in get_build_cells(build):
                if (row, col) in build['removed']:
                    continue

                if build['type'] == 'ramp':
                    left = build['rect'].left + col * build['rect'].width // 3
                    right = build['rect'].left + \
                        (col + 1) * build['rect'].width // 3

                    points = [
                        (int(left - camera_x), int(ramp_surface_y(build, left))),
                        (int(right - camera_x), int(ramp_surface_y(build, right))),
                        (int(right - camera_x), build['rect'].bottom),
                        (int(left - camera_x), build['rect'].bottom)
                    ]

                    pygame.draw.polygon(screen, BUILD_BLUE, points)
                    pygame.draw.polygon(screen, WHITE, points, 1)

                else:
                    cell_screen = pygame.Rect(
                        cell.x - camera_x,
                        cell.y,
                        cell.width,
                        cell.height
                    )

                    pygame.draw.rect(screen, BUILD_BLUE, cell_screen)
                    pygame.draw.rect(screen, WHITE, cell_screen, 1)

            if build['type'] == 'ramp':
                if build.get('orientation', 1) == 1:
                    ramp_start = (rect.left, rect.bottom)
                    ramp_end = (rect.right, rect.top)
                else:
                    ramp_start = (rect.left, rect.top)
                    ramp_end = (rect.right, rect.bottom)

                pygame.draw.line(
                    screen, WHITE, ramp_start, ramp_end, 3
                )
            else:
                pygame.draw.rect(screen, WHITE, rect, 2)

            draw_health_bar(rect, build['health'])

        if editing and active_build_index is not None:
            build = placed_builds[active_build_index]

            for row, col, cell in get_build_cells(build):
                if build['type'] == 'ramp':
                    left = build['rect'].left + col * build['rect'].width // 3
                    right = build['rect'].left + \
                        (col + 1) * build['rect'].width // 3

                    points = [
                        (int(left - camera_x), int(ramp_surface_y(build, left))),
                        (int(right - camera_x), int(ramp_surface_y(build, right))),
                        (int(right - camera_x), build['rect'].bottom),
                        (int(left - camera_x), build['rect'].bottom)
                    ]

                    overlay_color = (
                        (240, 50, 50, 170)
                        if (row, col) in edit_selection
                        else (60, 220, 100, 130)
                    )

                    overlay = pygame.Surface(
                        (WIDTH, HEIGHT), pygame.SRCALPHA
                    )

                    pygame.draw.polygon(overlay, overlay_color, points)
                    pygame.draw.polygon(overlay, WHITE, points, 2)
                    screen.blit(overlay, (0, 0))

                else:
                    cell_screen = pygame.Rect(
                        cell.x - camera_x,
                        cell.y,
                        cell.width,
                        cell.height
                    )

                    overlay = pygame.Surface(
                        (cell_screen.width, cell_screen.height),
                        pygame.SRCALPHA
                    )

                    if (row, col) in edit_selection:
                        overlay.fill((240, 50, 50, 170))
                    else:
                        overlay.fill((60, 220, 100, 130))

                    screen.blit(overlay, cell_screen)
                    pygame.draw.rect(screen, WHITE, cell_screen, 2)

            draw_text('EDIT MODE', WIDTH // 2 - 65, 15)

            if build['type'] == 'wall':
                draw_text(
                    '1: SHORT   2: REALLY SHORT   3: WINDOW   4: DOOR',
                    WIDTH // 2 - 250, 45, WHITE, small_font
                )
            elif build['type'] == 'ramp':
                draw_text(
                    'CLICK ONE OF THE 3 RAMP SECTIONS',
                    WIDTH // 2 - 190, 45, WHITE, small_font
                )

            draw_text(
                'CLICK A SECTION TO AUTO-SAVE | ESC: CANCEL',
                WIDTH // 2 - 220, 70, WHITE, small_font
            )

        if build_mode and not editing and not game_won:
            mx, my = pygame.mouse.get_pos()
            preview = get_build_rect(mx, my)

            preview_screen = pygame.Rect(
                preview.x - camera_x,
                preview.y,
                preview.width,
                preview.height
            )

            valid = (
                materials >= build_cost
                and preview.left >= 0
                and preview.right <= WORLD_WIDTH
                and preview.top >= 0
                and preview.bottom <= GROUND_Y + FLOOR_THICKNESS
                and not preview.colliderect(player)
                and not any(
                    preview.colliderect(b['rect'])
                    for b in placed_builds
                )
            )

            if build_type == 'floor':
                has_support = any(
                    p.left < preview.right
                    and p.right > preview.left
                    and abs(p.top - preview.bottom) <= 2
                    for p in platforms
                ) or any(
                    b['rect'].left < preview.right
                    and b['rect'].right > preview.left
                    and abs(b['rect'].top - preview.bottom) <= 2
                    for b in placed_builds
                )

                valid = valid and has_support

            ghost_color = (
                (60, 220, 100, 130)
                if valid
                else (240, 60, 60, 130)
            )

            if build_type == 'ramp':
                if player_facing == 1:
                    preview_points = [
                        (preview_screen.left, preview_screen.bottom),
                        (preview_screen.right, preview_screen.top),
                        (preview_screen.right, preview_screen.bottom)
                    ]
                else:
                    preview_points = [
                        (preview_screen.left, preview_screen.top),
                        (preview_screen.right, preview_screen.bottom),
                        (preview_screen.left, preview_screen.bottom)
                    ]

                pygame.draw.polygon(screen, ghost_color, preview_points)
                pygame.draw.polygon(screen, WHITE, preview_points, 2)

            else:
                ghost = pygame.Surface(
                    (preview.width, preview.height),
                    pygame.SRCALPHA
                )

                ghost.fill(ghost_color)
                screen.blit(ghost, preview_screen)
                pygame.draw.rect(screen, WHITE, preview_screen, 2)

            draw_text(
                f'BUILD MODE: {build_type.upper()} | {build_cost} MATERIALS',
                WIDTH // 2 - 200, 20
            )
            draw_text(
                'SNAPPED TO GRID',
                WIDTH // 2 - 80, 48, WHITE, small_font
            )

        if break_mode and not game_won:
            draw_text(
                'BREAK MODE: LEFT-CLICK A HOUSE OR BUILD',
                WIDTH // 2 - 260, 20, YELLOW
            )

            if break_message_timer > 0:
                draw_text(
                    break_message,
                    WIDTH // 2 - 180, 50, WHITE, small_font
                )

        for index, target in enumerate(targets):
            if target.x < 0:
                continue
            target_draw = pygame.Rect(
                target.x - camera_x, target.y, target.width, target.height
            )
            pygame.draw.rect(screen, RED, target_draw, border_radius=5)
            pygame.draw.circle(
                screen, (255, 210, 160),
                (target_draw.centerx, target_draw.y - 12), 15
            )
            pygame.draw.line(
                screen, BLACK,
                (target_draw.centerx, target_draw.centery),
                (target_draw.centerx + (8 if player.centerx >
                 target.centerx else -8), target_draw.centery),
                4
            )
            draw_health_bar(target_draw, bot_health[index])

        player_draw = pygame.Rect(
            player.x - camera_x,
            player.y,
            player.width,
            player.height
        )

        pygame.draw.rect(screen, BLUE, player_draw)
        pygame.draw.circle(
            screen,
            (255, 210, 160),
            (player_draw.centerx, player_draw.y + 10),
            17
        )

        mx, my = pygame.mouse.get_pos()

        angle = math.atan2(
            my - player_draw.centery,
            mx - player_draw.centerx
        )

        gun_end = (
            int(player_draw.centerx + math.cos(angle) * 40),
            int(player_draw.centery + math.sin(angle) * 40)
        )

        pygame.draw.line(
            screen, BLACK, player_draw.center, gun_end, 8
        )

        for bullet in bullets:
            pygame.draw.circle(
                screen, YELLOW,
                (int(bullet[0] - camera_x), int(bullet[1])), 6
            )

        for bullet in enemy_bullets:
            pygame.draw.circle(
                screen, (255, 105, 65),
                (int(bullet[0] - camera_x), int(bullet[1])), 6
            )

        pygame.draw.rect(screen, BLACK, (20, 20, 250, 60))
        pygame.draw.rect(
            screen,
            RED,
            (25, 25, int(220 * health / 100), 12)
        )
        pygame.draw.rect(
            screen,
            BLUE,
            (25, 45, int(220 * shield / 100), 12)
        )

        draw_text(f'HEALTH: {health}', 290, 15)
        draw_text(f'SHIELD: {shield}', 290, 45)
        draw_text(game_mode.upper(), WIDTH // 2 - 70, 15, YELLOW, small_font)

        weapon = WEAPONS[selected_weapon]
        rarity_name = weapon_rarities[selected_weapon]
        rarity_color = RARITIES[rarity_name]['color']

        draw_text(
            f"{rarity_name.upper()} {weapon['name'].upper()}: "
            f"{weapon_ammo[weapon['name']]}/{weapon['capacity']}",
            WIDTH - 390, 25, rarity_color, small_font
        )

        if game_mode == 'Battle Royale':
            storm_status = (
                f'STORM: {int(max(0, storm_delay - storm_elapsed))}s UNTIL SHRINK'
                if storm_elapsed < storm_delay
                else f'STORM SAFE RADIUS: {int(storm_radius)}'
            )
        elif game_mode == 'Bot Deathmatch':
            storm_status = f'ELIMINATIONS: {eliminations}/{DEATHMATCH_GOAL}'
        else:
            storm_status = 'PRACTICE MODE - NO ENEMY BOTS'

        draw_text(storm_status, WIDTH // 2 - 160,
                  82, (40, 65, 150), small_font)

        draw_text(
            'F: OPEN CHEST | WALK OVER LOOT TO PICK IT UP',
            WIDTH // 2 - 205, 105, WHITE, small_font
        )

        if game_mode == 'Battle Royale':
            draw_text(f'BOTS LEFT: {len(targets)}', WIDTH - 180, 60)
        elif game_mode == 'Bot Deathmatch':
            draw_text(
                f'KILLS: {eliminations}/{DEATHMATCH_GOAL}', WIDTH - 180, 60)
        else:
            draw_text('PRACTICE', WIDTH - 180, 60)
        draw_text(f'MATERIALS: {materials}', WIDTH - 260, 100)

        draw_text(
            f"{pygame.key.name(keybinds['Move left']).upper()}/"
            f"{pygame.key.name(keybinds['Move right']).upper()}: MOVE   "
            f"{pygame.key.name(keybinds['Jump']).upper()}: JUMP   "
            f"MOUSE: SHOOT   "
            f"{pygame.key.name(keybinds['Reload']).upper()}: RELOAD",
            20, HEIGHT - 40, WHITE, small_font
        )

        draw_text(
            f"{pygame.key.name(keybinds['Build mode']).upper()}: BUILD   "
            f"{pygame.key.name(keybinds['Wall']).upper()}: WALL   "
            f"{pygame.key.name(keybinds['Floor']).upper()}: FLOOR   "
            f"{pygame.key.name(keybinds['Ramp']).upper()}: RAMP   "
            f"{pygame.key.name(keybinds['Edit']).upper()}: EDIT   "
            f"{pygame.key.name(keybinds['Break builds']).upper()}: BREAK",
            20, HEIGHT - 68, WHITE, small_font
        )

        draw_text(
            '3/4/5: SWITCH WEAPON   R: RELOAD   ESC: EXIT MODE',
            20, HEIGHT - 96, WHITE, small_font
        )

        pygame.draw.rect(
            screen, (35, 45, 65), settings_button, border_radius=8
        )
        pygame.draw.rect(
            screen, WHITE, settings_button, 2, border_radius=8
        )

        label = font.render('SETTINGS', True, WHITE)
        screen.blit(label, label.get_rect(center=settings_button.center))

        if settings_open:
            shade = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            shade.fill((0, 0, 0, 175))
            screen.blit(shade, (0, 0))

            panel = pygame.Rect(275, 25, 650, 650)
            pygame.draw.rect(
                screen, (35, 45, 65), panel, border_radius=14
            )
            pygame.draw.rect(
                screen, WHITE, panel, 3, border_radius=14
            )

            title = font.render('CUSTOMIZE KEYBINDS', True, WHITE)
            screen.blit(
                title,
                title.get_rect(center=(WIDTH // 2, 55))
            )

            draw_text(
                'Click an action, then press the key you want.',
                370, 80, WHITE, small_font
            )

            for index, (action, key_code) in enumerate(keybinds.items()):
                row_rect = pygame.Rect(
                    325, 120 + index * 38, 550, 34
                )

                row_color = (
                    (75, 100, 135)
                    if waiting_for_key == action
                    else (55, 70, 95)
                )

                pygame.draw.rect(
                    screen, row_color, row_rect, border_radius=6
                )

                draw_text(
                    action,
                    row_rect.x + 12,
                    row_rect.y + 8,
                    WHITE,
                    small_font
                )

                key_text = (
                    'PRESS A KEY...'
                    if waiting_for_key == action
                    else pygame.key.name(key_code).upper()
                )

                value = small_font.render(key_text, True, YELLOW)

                screen.blit(
                    value,
                    value.get_rect(
                        midright=(row_rect.right - 12, row_rect.centery)
                    )
                )

            draw_text(
                settings_message,
                350, 620, YELLOW, small_font
            )
            draw_text(
                'Press ESC or click SETTINGS to close',
                390, 645, WHITE, small_font
            )

        if health <= 0:
            shade = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            shade.fill((0, 0, 0, 185))
            screen.blit(shade, (0, 0))

            message = big_font.render('ELIMINATED', True, RED)
            screen.blit(
                message,
                message.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35))
            )

            draw_text(
                'Close the window to exit the match.',
                WIDTH // 2 - 170,
                HEIGHT // 2 + 20,
                WHITE,
                small_font
            )

        elif game_won:
            shade = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            shade.fill((0, 0, 0, 190))
            screen.blit(shade, (0, 0))

            victory_text = big_font.render(
                'VICTORY!', True, YELLOW
            )

            screen.blit(
                victory_text,
                victory_text.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 - 85)
                )
            )

            subtitle = font.render(
                ('YOU ELIMINATED EVERYONE!' if game_mode ==
                 'Battle Royale' else 'YOU REACHED THE KILL GOAL!'), True, WHITE
            )

            screen.blit(
                subtitle,
                subtitle.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 - 20)
                )
            )

            stats = font.render(
                f'ELIMINATIONS: {eliminations}',
                True,
                (100, 220, 255)
            )

            screen.blit(
                stats,
                stats.get_rect(
                    center=(WIDTH // 2, HEIGHT // 2 + 35)
                )
            )

            draw_text(
                ('YOU ARE THE LAST PLAYER STANDING' if game_mode ==
                 'Battle Royale' else 'MATCH COMPLETE'),
                WIDTH // 2 - 185,
                HEIGHT // 2 + 85,
                WHITE,
                small_font
            )

        pygame.display.flip()

    pygame.quit()


asyncio.run(main())
