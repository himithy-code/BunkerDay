import asyncio
import pygame
import math
import random
import json
import os
import sys
import webbrowser

pygame.init()

WIDTH, HEIGHT = 1200, 700
FPS = 60
WORLD_WIDTH = 20000
GROUND_Y = 590

BUILD_GRID_X = 40
BUILD_GRID_Y = 25
WALL_WIDTH = BUILD_GRID_X
WALL_HEIGHT = BUILD_GRID_Y * 5
RAMP_HEIGHT = BUILD_GRID_Y * 3
WIDE_BUILD_WIDTH = BUILD_GRID_X * 3
FLOOR_THICKNESS = BUILD_GRID_Y


# BUNKERDAY WORLD UPDATE: named regions, scenery, and drivable cars.
WORLD_REGIONS = [
    (0, 2300, "PINE RIDGE", (78, 145, 92)),
    (2300, 4700, "DUSTY DEPOT", (185, 145, 95)),
    (4700, 7200, "NEON HARBOR", (85, 145, 170)),
    (7200, 9700, "RUSTY FACTORY", (135, 125, 105)),
    (9700, 12000, "SUNSET SUBURBS", (165, 145, 105)),
    (12000, 14000, "CLIFFSIDE", (100, 150, 115)),
    (14000, 16000, "FROST PEAKS", (135, 165, 185)),
    (16000, 18000, "WILD FRONTIER", (105, 155, 95)),
    (18000, WORLD_WIDTH, "SOLAR COAST", (195, 165, 105)),
]
VEHICLE_SPAWN_X = [430, 2850, 5350, 8050, 10600, 12800, 14900, 17200, 19100]
vehicles = []
vehicle_active = False
vehicle_speed = 9.5

# Persistent BUNKERDAY profile: coins, owned cosmetics, and quest progress.
PROFILE_FOLDER = os.path.join(os.path.expanduser('~'), 'Library',
                              'Application Support', 'Bunkerday')
PROFILE_FILE = os.path.join(PROFILE_FOLDER, 'profile.json')
SHOP_CATALOG = [
    {'name': 'Crown Headgear', 'category': 'HEAD',
        'option': 'Crown', 'price': 120, 'limited': True},
    {'name': 'Wing Pack', 'category': 'BACK',
        'option': 'Wings', 'price': 180, 'limited': True},
    {'name': 'Stealth Outfit', 'category': 'OUTFIT',
        'option': 'Stealth', 'price': 150},
    {'name': 'Gold Weapon', 'category': 'WEAPON',
        'option': 'Gold', 'price': 200, 'limited': True},
    {'name': 'Robot Face', 'category': 'FACE', 'option': 'Robot', 'price': 130},
    {'name': 'Mohawk Hair', 'category': 'HAIR', 'option': 'Mohawk', 'price': 100},
    {'name': 'Midnight Backpack', 'category': 'BACK',
        'option': 'Backpack', 'price': 140},
    {'name': 'Frost Beanie', 'category': 'HEAD', 'option': 'Beanie', 'price': 90},
    {'name': 'Neon Visor', 'category': 'FACE', 'option': 'Visor', 'price': 110},
    {'name': 'Carbon Pickaxe', 'category': 'PICKAXE',
        'option': 'Carbon Pickaxe', 'price': 160, 'limited': True},
    {'name': 'Pulse Pickaxe', 'category': 'PICKAXE',
        'option': 'Pulse Pickaxe', 'price': 125},
    {'name': 'Victory Dance', 'category': 'EMOTE',
        'option': 'Victory Dance', 'price': 100},
    {'name': 'Robot Groove', 'category': 'EMOTE',
        'option': 'Robot Groove', 'price': 130},
    {'name': 'Gold Chain', 'category': 'ACCESSORY',
        'option': 'Gold Chain', 'price': 85},
    {'name': 'Pilot Goggles', 'category': 'ACCESSORY',
        'option': 'Pilot Goggles', 'price': 95},
]
coins = 0
owned_cosmetics = set()
quest_stats = {'matches': 0, 'eliminations': 0, 'chests': 0}
claimed_quests = set()
shop_open = False
locker_open = False
locker_category = 'Outfits'
locker_selected_index = 0
shop_page = 0
SHOP_PAGE_SIZE = 6
equipped_locker_items = {}
quests_open = False
full_map_open = False
match_rewarded = False
match_coins_earned = 0


def get_available_shop_items():
    # Items already purchased are removed from the shop; they remain in the locker.
    return [item for item in SHOP_CATALOG if item['name'] not in owned_cosmetics]


def get_shop_page_items():
    available = get_available_shop_items()
    start = shop_page * SHOP_PAGE_SIZE
    return available[start:start + SHOP_PAGE_SIZE]


def get_shop_item_rects():
    visible = get_shop_page_items()
    return [
        pygame.Rect(205 + (i % 3) * 270, 220 + (i // 3) * 175, 245, 145)
        for i in range(len(visible))
    ]


shop_item_rects = get_shop_item_rects()
SHOP_BUTTON = pygame.Rect(1080, 48, 105, 34)
SHOP_PREV_BUTTON = pygame.Rect(435, 570, 105, 34)
SHOP_NEXT_BUTTON = pygame.Rect(660, 570, 105, 34)
QUEST_BUTTON = pygame.Rect(965, 48, 105, 34)
MENU_SETTINGS_BUTTON = pygame.Rect(850, 48, 105, 34)
LOCKER_BUTTON = pygame.Rect(735, 48, 105, 34)

# Feedback link and match-result controls.
FEEDBACK_URL = 'https://docs.google.com/document/d/17ywPdWjwL4rRH7vPPqYCY7EgRoUdoCzdYMNLnoqT07Q/edit?tab=t.0'
MENU_FEEDBACK_BUTTON = pygame.Rect(850, 8, 335, 32)
RESULT_CONTINUE_BUTTON = pygame.Rect(
    WIDTH // 2 - 145, HEIGHT // 2 + 125, 130, 48)
RESULT_FEEDBACK_BUTTON = pygame.Rect(
    WIDTH // 2 + 15, HEIGHT // 2 + 125, 190, 48)


def save_profile():
    try:
        os.makedirs(PROFILE_FOLDER, exist_ok=True)
        payload = {
            'coins': coins,
            'owned_cosmetics': sorted(owned_cosmetics),
            'quest_stats': quest_stats,
            'claimed_quests': sorted(claimed_quests),
            'equipped_locker_items': equipped_locker_items,
            'custom_selected': custom_selected if 'custom_selected' in globals() else {},
        }
        temp_path = PROFILE_FILE + '.tmp'
        with open(temp_path, 'w') as f:
            json.dump(payload, f, indent=2)
        os.replace(temp_path, PROFILE_FILE)
        return True
    except (OSError, TypeError):
        return False


def load_profile():
    global coins, owned_cosmetics, quest_stats, claimed_quests, equipped_locker_items
    try:
        with open(PROFILE_FILE, 'r') as f:
            data = json.load(f)
        coins = max(0, int(data.get('coins', 0)))
        owned_cosmetics = set(data.get('owned_cosmetics', []))
        saved_stats = data.get('quest_stats', {})
        for key in quest_stats:
            quest_stats[key] = max(0, int(saved_stats.get(key, 0)))
        claimed_quests = set(data.get('claimed_quests', []))
        equipped_locker_items = data.get('equipped_locker_items', {})
        globals()['_saved_custom_selected'] = data.get('custom_selected', {})
    except (OSError, ValueError, TypeError, AttributeError):
        pass


def add_coins(amount, reason=''):
    global coins, match_coins_earned
    amount = max(0, int(amount))
    if amount <= 0:
        return
    coins += amount
    match_coins_earned += amount
    save_profile()


def update_quest_progress(stat, amount=1):
    if stat not in quest_stats:
        return
    quest_stats[stat] += max(0, int(amount))
    quest_definitions = [
        ('first_match', 'Play 1 match', 'matches', 1, 40),
        ('eliminations_5', 'Get 5 eliminations', 'eliminations', 5, 100),
        ('chests_3', 'Open 3 chests', 'chests', 3, 60),
    ]
    for quest_id, label, key, goal, reward in quest_definitions:
        if quest_stats[key] >= goal and quest_id not in claimed_quests:
            claimed_quests.add(quest_id)
            add_coins(reward, 'quest')
            # Save after recording the claim so rewards cannot be duplicated.
            save_profile()


def complete_match_rewards():
    global match_rewarded
    if match_rewarded:
        return
    match_rewarded = True
    add_coins(20, 'match completion')
    update_quest_progress('matches')
    save_profile()


def draw_pickaxe(center, direction=1, scale=1.0):
    """Draw the currently equipped pickaxe as a clear held tool."""
    x, y = center
    selected_pickaxe = equipped_locker_items.get('PICKAXE', 'Standard Pickaxe')
    if selected_pickaxe == 'Carbon Pickaxe':
        handle_color = (28, 34, 46)
        head_color = (105, 125, 150)
        accent = (45, 205, 245)
    elif selected_pickaxe == 'Pulse Pickaxe':
        handle_color = (24, 55, 88)
        head_color = (45, 215, 250)
        accent = (180, 250, 255)
    else:
        handle_color = (125, 78, 43)
        head_color = (195, 207, 220)
        accent = (105, 120, 140)

    # Angled handle with a grip and pommel.
    bottom = (int(x - direction * 7 * scale), int(y + 25 * scale))
    top = (int(x + direction * 15 * scale), int(y - 25 * scale))
    pygame.draw.line(screen, (20, 24, 32), bottom, top,
                     max(7, int(10 * scale)))
    pygame.draw.line(screen, handle_color, bottom, top,
                     max(4, int(6 * scale)))
    grip_a = (int(x - direction * 2 * scale), int(y + 13 * scale))
    grip_b = (int(x + direction * 3 * scale), int(y + 2 * scale))
    pygame.draw.line(screen, accent, grip_a, grip_b,
                     max(2, int(3 * scale)))
    pygame.draw.circle(screen, (35, 40, 50), bottom,
                       max(3, int(5 * scale)))

    # Wide double-ended pick head, outlined for visibility against the map.
    head_y = int(y - 24 * scale)
    head_points = [
        (int(x - direction * 31 * scale), head_y + int(5 * scale)),
        (int(x - direction * 18 * scale), head_y - int(5 * scale)),
        (int(x + direction * 2 * scale), head_y - int(2 * scale)),
        (int(x + direction * 23 * scale), head_y - int(11 * scale)),
        (int(x + direction * 39 * scale), head_y - int(4 * scale)),
        (int(x + direction * 26 * scale), head_y + int(8 * scale)),
        (int(x + direction * 3 * scale), head_y + int(5 * scale)),
        (int(x - direction * 17 * scale), head_y + int(13 * scale)),
    ]
    pygame.draw.polygon(screen, (18, 24, 34), head_points)
    inner = [(int(x + (px - x) * .88), int(head_y + (py - head_y) * .88))
             for px, py in head_points]
    pygame.draw.polygon(screen, head_color, inner)
    pygame.draw.line(screen, accent,
                     (int(x - direction * 17 * scale), head_y + int(4 * scale)),
                     (int(x + direction * 25 * scale), head_y - int(4 * scale)),
                     max(1, int(2 * scale)))



def draw_car_sprite(car_rect, color):
    """Draw a more detailed car with glass, lights, trim, wheels and shadow."""
    shadow = pygame.Rect(car_rect.x + 5, car_rect.bottom - 2,
                         car_rect.width - 10, 13)
    pygame.draw.ellipse(screen, (45, 50, 55), shadow)
    body = pygame.Rect(car_rect.x, car_rect.y + 5,
                       car_rect.width, car_rect.height - 7)
    pygame.draw.rect(screen, (22, 27, 35), body.inflate(4, 3), border_radius=11)
    pygame.draw.rect(screen, color, body, border_radius=10)
    pygame.draw.line(screen, tuple(max(0, c - 35) for c in color),
                     (body.x + 12, body.bottom - 7),
                     (body.right - 12, body.bottom - 7), 3)
    windshield = [
        (body.x + 27, body.y + 3), (body.x + 65, body.y + 3),
        (body.x + 58, body.y - 12), (body.x + 37, body.y - 12)
    ]
    pygame.draw.polygon(screen, (35, 65, 88), windshield)
    pygame.draw.polygon(screen, (145, 195, 215), windshield, 2)
    pygame.draw.line(screen, (195, 220, 230),
                     (body.x + 44, body.y - 10),
                     (body.x + 44, body.y + 3), 2)
    pygame.draw.rect(screen, (245, 235, 175),
                     (body.x + 3, body.y + 10, 7, 5), border_radius=2)
    pygame.draw.rect(screen, (245, 75, 65),
                     (body.right - 10, body.y + 10, 7, 5), border_radius=2)
    for wheel_x in (body.x + 20, body.right - 20):
        pygame.draw.circle(screen, (18, 20, 25),
                           (wheel_x, body.bottom - 1), 11)
        pygame.draw.circle(screen, (105, 112, 122),
                           (wheel_x, body.bottom - 1), 6)
        pygame.draw.circle(screen, (35, 40, 48),
                           (wheel_x, body.bottom - 1), 2)
    pygame.draw.line(screen, tuple(min(255, c + 35) for c in color),
                     (body.x + 12, body.y + 7),
                     (body.right - 13, body.y + 7), 2)


def get_vehicle_hitboxes():
    """Return world-space vehicle bodies, including the car being driven."""
    hitboxes = []
    for car in vehicles:
        if car.get('occupied'):
            if vehicle_active:
                hitboxes.append(pygame.Rect(
                    player.centerx - 46, player.bottom - 38, 92, 34))
        else:
            hitboxes.append(car['rect'])
    return hitboxes


def bullet_hits_vehicle(world_x, world_y, radius=6):
    """Cars act as solid cover: bullets stop at the body instead of passing through."""
    for car_rect in get_vehicle_hitboxes():
        if car_rect.inflate(radius * 2, radius * 2).collidepoint(world_x, world_y):
            return True
    return False

def draw_shop_item_preview(rect, item):
    """Render a small visual model for each shop item, not just its label."""
    category = item.get('category', '')
    cx, cy = rect.centerx, rect.y + 47
    preview_bg = pygame.Rect(rect.x + 10, rect.y + 8, rect.width - 20, 78)
    pygame.draw.rect(screen, (17, 27, 43), preview_bg, border_radius=8)
    pygame.draw.rect(screen, (72, 95, 125), preview_bg, 1, border_radius=8)

    if category == 'PICKAXE':
        old = equipped_locker_items.get('PICKAXE')
        equipped_locker_items['PICKAXE'] = item['name']
        draw_pickaxe((cx, cy + 12), 1, 1.08)
        if old is None:
            equipped_locker_items.pop('PICKAXE', None)
        else:
            equipped_locker_items['PICKAXE'] = old
    elif category == 'OUTFIT':
        draw_custom_character(cx, cy + 15, (85, 155, 220), 0.62)
    elif category == 'BACK':
        pygame.draw.polygon(screen, (28, 40, 60),
                            [(cx-20, cy-15), (cx+20, cy-15),
                             (cx+24, cy+19), (cx-24, cy+19)])
        color = (90, 185, 245) if item.get('option') == 'Wings' else (155, 115, 75)
        if item.get('option') == 'Wings':
            pygame.draw.polygon(screen, color, [(cx-9, cy-7), (cx-34, cy-18),
                                                (cx-27, cy+17), (cx-7, cy+12)])
            pygame.draw.polygon(screen, color, [(cx+9, cy-7), (cx+34, cy-18),
                                                (cx+27, cy+17), (cx+7, cy+12)])
        else:
            pygame.draw.rect(screen, color, (cx-13, cy-13, 26, 31), border_radius=6)
        pygame.draw.rect(screen, (210, 220, 235), (cx-5, cy-9, 10, 25), 1, border_radius=3)
    elif category == 'WEAPON':
        draw_custom_weapon((cx-38, cy+5), (cx+42, cy-4), selected_weapon)
    elif category == 'EMOTE':
        pygame.draw.circle(screen, (245, 205, 160), (cx, cy-13), 10)
        pygame.draw.line(screen, (80, 190, 245), (cx, cy-2), (cx, cy+22), 6)
        pygame.draw.line(screen, (80, 190, 245), (cx, cy+4), (cx-18, cy-10), 5)
        pygame.draw.line(screen, (80, 190, 245), (cx, cy+4), (cx+18, cy-12), 5)
        pygame.draw.line(screen, (80, 190, 245), (cx, cy+20), (cx-12, cy+31), 5)
        pygame.draw.line(screen, (80, 190, 245), (cx, cy+20), (cx+12, cy+31), 5)
    else:
        # Headgear, faces, hair and accessories get a recognizable character bust.
        pygame.draw.circle(screen, (235, 190, 150), (cx, cy-4), 19)
        pygame.draw.arc(screen, (55, 40, 35), (cx-20, cy-25, 40, 30), math.pi, 2*math.pi, 5)
        if item.get('option') == 'Crown':
            pygame.draw.polygon(screen, (245, 195, 45),
                                [(cx-18, cy-20), (cx-13, cy-37), (cx, cy-25),
                                 (cx+13, cy-37), (cx+18, cy-20)])
        elif item.get('option') in ('Visor', 'Robot'):
            tint = (45, 220, 245) if item.get('option') == 'Visor' else (30, 235, 235)
            pygame.draw.rect(screen, tint, (cx-16, cy-10, 32, 9), border_radius=4)
        else:
            pygame.draw.circle(screen, (35, 45, 60), (cx-7, cy-5), 2)
            pygame.draw.circle(screen, (35, 45, 60), (cx+7, cy-5), 2)
        pygame.draw.rect(screen, (55, 95, 145), (cx-17, cy+16, 34, 20), border_radius=6)


def upgrade_selected_weapon():
    global weapon_rarities
    rarity_order = list(RARITIES)
    current = weapon_rarities[selected_weapon]
    next_index = min(len(rarity_order) - 1, rarity_order.index(current) + 1)
    weapon_rarities[selected_weapon] = rarity_order[next_index]
    return weapon_rarities[selected_weapon]


def leave_match():
    global game_started, game_won, match_end_timer, pending_player_shot, lobby_message
    global build_mode, break_mode, editing, settings_open, full_map_open
    complete_match_rewards()
    game_started = False
    game_won = False
    match_end_timer = 0.0
    pending_player_shot = False
    build_mode = False
    break_mode = False
    editing = False
    settings_open = False
    full_map_open = False
    bullets.clear()
    enemy_bullets.clear()
    elimination_effects.clear()
    lobby_message = 'You left the match. Choose another mode!'
    return lobby_message


def open_feedback_page():
    """Open the shared Bugs & Suggestions document."""
    try:
        webbrowser.open(FEEDBACK_URL, new=2)
        return True
    except Exception:
        return False


def continue_to_lobby():
    """Dismiss a match result and return to the lobby when Continue is clicked."""
    global game_started, game_won, match_end_timer, pending_player_shot
    global lobby_message, settings_open, full_map_open, build_mode, break_mode
    global editing, vehicle_active
    complete_match_rewards()
    was_eliminated = health <= 0
    game_started = False
    game_won = False
    match_end_timer = 0.0
    pending_player_shot = False
    settings_open = False
    full_map_open = False
    build_mode = False
    break_mode = False
    editing = False
    vehicle_active = False
    cancel_edit()
    bullets.clear()
    enemy_bullets.clear()
    elimination_effects.clear()
    lobby_message = ('You were eliminated. Choose another mode when you are ready!'
                     if was_eliminated else
                     'Victory! Your match is complete. Pick another mode!')


def draw_result_screen(victory=False):
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((5, 10, 20, 225))
    screen.blit(shade, (0, 0))
    panel = pygame.Rect(WIDTH // 2 - 300, HEIGHT // 2 - 205, 600, 430)
    pygame.draw.rect(screen, (25, 38, 59), panel, border_radius=20)
    pygame.draw.rect(screen, (105, 145, 190), panel, 3, border_radius=20)

    title_text = 'VICTORY!' if victory else 'ELIMINATED'
    title_color = YELLOW if victory else RED
    title = big_font.render(title_text, True, title_color)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 125)))

    if victory:
        subtitle_text = ('YOU ARE THE LAST PLAYER STANDING'
                         if game_mode == 'Battle Royale'
                         else 'YOU REACHED THE KILL GOAL!')
    else:
        subtitle_text = 'GOOD TRY! QUEUE UP FOR ANOTHER MATCH.'
    subtitle = small_font.render(subtitle_text, True, WHITE)
    screen.blit(subtitle, subtitle.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 - 65)))

    stats = font.render(f'ELIMINATIONS: {eliminations}', True, (100, 220, 255))
    screen.blit(stats, stats.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 15)))

    for rect, label, color in (
        (RESULT_CONTINUE_BUTTON, 'CONTINUE', (35, 135, 85)),
        (RESULT_FEEDBACK_BUTTON, 'BUGS & SUGGESTIONS', (65, 100, 175)),
    ):
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, (235, 240, 250), rect, 2, border_radius=10)
        rendered = small_font.render(label, True, WHITE)
        screen.blit(rendered, rendered.get_rect(center=rect.center))


def draw_shop_screen():
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((4, 8, 18, 235))
    screen.blit(shade, (0, 0))
    panel = pygame.Rect(115, 65, 970, 575)
    pygame.draw.rect(screen, (27, 39, 61), panel, border_radius=18)
    pygame.draw.rect(screen, (105, 145, 190), panel, 3, border_radius=18)
    title = big_font.render('BUNKERDAY SHOP', True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 112)))
    balance = font.render(f'YOUR COINS: {coins}', True, YELLOW)
    screen.blit(balance, balance.get_rect(center=(WIDTH // 2, 165)))
    available_items = get_shop_page_items()
    available_rects = get_shop_item_rects()
    if not available_items:
        empty_label = font.render(
            'YOU OWN EVERYTHING IN THE SHOP!', True, (120, 235, 160))
        screen.blit(empty_label, empty_label.get_rect(
            center=(WIDTH // 2, 360)))
    for i, item in enumerate(available_items):
        rect = available_rects[i]
        pygame.draw.rect(screen, (38, 52, 76), rect, border_radius=12)
        pygame.draw.rect(screen, (95, 125, 165), rect, 2, border_radius=12)
        draw_shop_item_preview(rect, item)
        item_title = small_font.render(item['name'], True, WHITE)
        screen.blit(item_title, item_title.get_rect(
            center=(rect.centerx, rect.y + 96)))
        state_text = small_font.render(f"{item['price']} COINS", True, YELLOW)
        screen.blit(state_text, state_text.get_rect(
            center=(rect.centerx, rect.y + 117)))
        category_text = small_font.render(
            item['category'], True, (175, 195, 220))
        screen.blit(category_text, category_text.get_rect(
            center=(rect.centerx, rect.y + 137)))
        bottom_label = 'LIMITED EDITION' if item.get('limited') else 'CLICK TO BUY'
        bottom_color = (255, 105, 125) if item.get('limited') else (120, 220, 165)
        bottom_surface = small_font.render(bottom_label, True, bottom_color)
        screen.blit(bottom_surface, bottom_surface.get_rect(
            center=(rect.centerx, rect.y + 152)))
    total_pages = max(1, (len(get_available_shop_items()) +
                      SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE)
    page_label = small_font.render(
        f'PAGE {shop_page + 1} / {total_pages}', True, WHITE)
    screen.blit(page_label, page_label.get_rect(center=(WIDTH // 2, 586)))
    for page_rect, page_label_text in ((SHOP_PREV_BUTTON, 'PREVIOUS'), (SHOP_NEXT_BUTTON, 'NEXT')):
        pygame.draw.rect(screen, (55, 85, 125), page_rect, border_radius=7)
        pygame.draw.rect(screen, WHITE, page_rect, 1, border_radius=7)
        page_surface = small_font.render(page_label_text, True, WHITE)
        screen.blit(page_surface, page_surface.get_rect(
            center=page_rect.center))
    draw_text('Only unowned items are shown. ESC closes the shop.',
              300, 615, WHITE, small_font)


LOCKER_GROUPS = {
    'Outfits': ['OUTFIT'],
    'Back Bling': ['BACK'],
    'Pickaxes': ['PICKAXE'],
    'Emotes': ['EMOTE'],
    'Accessories': ['FACE', 'HEAD', 'HAIR', 'ACCESSORY'],
    'Weapon Wraps': ['WEAPON'],
}
LOCKER_TAB_RECTS = {
    name: pygame.Rect(145 + i * 153, 155, 145, 38)
    for i, name in enumerate(LOCKER_GROUPS)
}
LOCKER_EQUIP_BUTTON = pygame.Rect(755, 555, 190, 48)
LOCKER_CLOSE_BUTTON = pygame.Rect(965, 555, 105, 48)


def get_locker_items(category_name):
    categories = LOCKER_GROUPS.get(category_name, [])
    return [item for item in SHOP_CATALOG
            if item['name'] in owned_cosmetics and item['category'] in categories]


def get_locker_item_rects(items):
    return [pygame.Rect(155 + (i % 3) * 190, 220 + (i // 3) * 105, 170, 82)
            for i in range(len(items))]


def equip_locker_item(item):
    category = item['category']
    option = item.get('option', '')
    if category in CUSTOM_OPTIONS and option in CUSTOM_OPTIONS[category]:
        custom_selected[category] = CUSTOM_OPTIONS[category].index(option)
    equipped_locker_items[category] = item['name']
    save_profile()
    return item['name'] + ' equipped!'


def draw_locker_screen():
    global locker_selected_index
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((4, 8, 18, 238))
    screen.blit(shade, (0, 0))
    panel = pygame.Rect(105, 55, 990, 590)
    pygame.draw.rect(screen, (24, 36, 58), panel, border_radius=18)
    pygame.draw.rect(screen, (110, 155, 205), panel, 3, border_radius=18)
    title = big_font.render('YOUR LOCKER', True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 105)))

    for name, rect in LOCKER_TAB_RECTS.items():
        active = name == locker_category
        pygame.draw.rect(screen, (45, 125, 190) if active else (42, 55, 76),
                         rect, border_radius=8)
        pygame.draw.rect(screen, YELLOW if active else (105, 125, 150), rect,
                         2 if active else 1, border_radius=8)
        label = small_font.render(name, True, WHITE)
        screen.blit(label, label.get_rect(center=rect.center))

    items = get_locker_items(locker_category)
    rects = get_locker_item_rects(items)
    preview_panel = pygame.Rect(770, 215, 285, 300)
    pygame.draw.rect(screen, (14, 24, 40), preview_panel, border_radius=12)
    pygame.draw.rect(screen, (75, 105, 145),
                     preview_panel, 2, border_radius=12)
    preview_item = items[min(locker_selected_index,
                             len(items) - 1)] if items else None
    old_equipped = dict(equipped_locker_items)
    old_custom = dict(custom_selected)
    if preview_item:
        preview_category = preview_item['category']
        preview_option = preview_item.get('option', '')
        if preview_category in CUSTOM_OPTIONS and preview_option in CUSTOM_OPTIONS[preview_category]:
            custom_selected[preview_category] = CUSTOM_OPTIONS[preview_category].index(
                preview_option)
        equipped_locker_items[preview_category] = preview_item['name']
    draw_lobby_avatar(912, 350, LOBBY_SKINS[selected_skin][1], 1.0)
    equipped_locker_items.clear()
    equipped_locker_items.update(old_equipped)
    custom_selected.update(old_custom)
    draw_text('CHARACTER PREVIEW', 820, 235, (170, 205, 245), small_font)

    if not items:
        empty = font.render(
            'Nothing owned in this section yet.', True, (205, 215, 230))
        screen.blit(empty, empty.get_rect(center=(455, 330)))
        draw_text('Visit the Shop to unlock more items.', 280, 365,
                  (160, 185, 215), small_font)
    else:
        locker_selected_index = min(globals().get(
            'locker_selected_index', 0), len(items) - 1)
        for i, (item, rect) in enumerate(zip(items, rects)):
            selected = i == locker_selected_index
            equipped = equipped_locker_items.get(
                item['category']) == item['name']
            pygame.draw.rect(screen, (48, 68, 94) if selected else (32, 47, 68),
                             rect, border_radius=9)
            pygame.draw.rect(screen, YELLOW if selected else (90, 115, 150),
                             rect, 3 if selected else 1, border_radius=9)
            name = small_font.render(item['name'][:19], True, WHITE)
            screen.blit(name, name.get_rect(
                center=(rect.centerx, rect.y + 25)))
            status = 'EQUIPPED' if equipped else item['category']
            status_color = (120, 235, 160) if equipped else (175, 195, 220)
            detail = small_font.render(status, True, status_color)
            screen.blit(detail, detail.get_rect(
                center=(rect.centerx, rect.y + 56)))

    # Character color/style presets are managed here, not on the lobby screen.
    if locker_category == 'Outfits':
        draw_text('CHARACTER STYLE', 155, 505, (190, 210, 235), small_font)
        for skin_index, (skin_label, skin_color) in enumerate(LOBBY_SKINS):
            skin_rect = pygame.Rect(155 + skin_index * 96, 520, 88, 27)
            pygame.draw.rect(screen, skin_color, skin_rect, border_radius=6)
            pygame.draw.rect(screen, YELLOW if skin_index == selected_skin else WHITE,
                             skin_rect, 3 if skin_index == selected_skin else 1,
                             border_radius=6)
            skin_text = small_font.render(skin_label[:10], True, WHITE)
            screen.blit(skin_text, skin_text.get_rect(center=skin_rect.center))

        selected_item = items[locker_selected_index]
        item_name = font.render(selected_item['name'], True, WHITE)
        screen.blit(item_name, item_name.get_rect(center=(912, 445)))
        equipped = equipped_locker_items.get(
            selected_item['category']) == selected_item['name']
        info = small_font.render('CURRENTLY EQUIPPED' if equipped else 'OWNED ITEM', True,
                                 (120, 235, 160) if equipped else (180, 200, 225))
        screen.blit(info, info.get_rect(center=(912, 475)))

    for rect, label, color in (
        (LOCKER_EQUIP_BUTTON, 'EQUIP SELECTED', (35, 135, 85)),
        (LOCKER_CLOSE_BUTTON, 'CLOSE', (65, 85, 115)),
    ):
        pygame.draw.rect(screen, color, rect, border_radius=9)
        pygame.draw.rect(screen, WHITE, rect, 2, border_radius=9)
        text_surface = small_font.render(label, True, WHITE)
        screen.blit(text_surface, text_surface.get_rect(center=rect.center))
    draw_text(f'OWNED ITEMS: {len(owned_cosmetics)}',
              155, 585, YELLOW, small_font)
    draw_text('ESC closes the Locker', 155, 610, (185, 200, 220), small_font)


def draw_weapon_inventory_bar():
    """Draw the match inventory panel in the top-right for BR and Deathmatch."""
    if game_mode in ('Battle Royale', 'Bot Deathmatch'):
        panel = pygame.Rect(WIDTH - 458, 12, 440, 96)
        pygame.draw.rect(screen, (9, 17, 30), panel, border_radius=12)
        pygame.draw.rect(screen, (130, 155, 190), panel, 2, border_radius=12)
        title = small_font.render('INVENTORY', True, (235, 242, 255))
        screen.blit(title, (panel.x + 14, panel.y + 8))

        # Materials and the currently selected build piece.
        mats = small_font.render(f'MATS: {materials}', True, (225, 205, 145))
        screen.blit(mats, (panel.x + 14, panel.y + 34))
        build_label = small_font.render(
            f'BUILD: {build_type.upper()}', True, (170, 215, 255)
        )
        screen.blit(build_label, (panel.x + 14, panel.y + 61))

        # Show the three carried weapon slots, with the selected one highlighted.
        slot_x = panel.x + 150
        slot_y = panel.y + 30
        slot_w, slot_h, gap = 88, 52, 7
        visible_weapons = weapon_inventory[:3]
        if not visible_weapons:
            empty = small_font.render('NO WEAPONS', True, (185, 195, 210))
            screen.blit(empty, (slot_x, slot_y + 16))
        for slot_index, weapon_index in enumerate(visible_weapons):
            weapon = WEAPONS[weapon_index]
            rect = pygame.Rect(slot_x + slot_index * (slot_w + gap),
                               slot_y, slot_w, slot_h)
            selected = weapon_index == selected_weapon
            rarity_color = RARITIES[weapon_rarities[weapon_index]]['color']
            pygame.draw.rect(screen, (20, 31, 48), rect, border_radius=7)
            pygame.draw.rect(screen, rarity_color if selected else (100, 115, 140),
                             rect, 3 if selected else 1, border_radius=7)
            name = small_font.render(weapon['name'][:11], True, WHITE)
            screen.blit(name, name.get_rect(
                center=(rect.centerx, rect.y + 15)))
            ammo = small_font.render(
                f"{weapon_ammo[weapon['name']]}/{weapon_reserve[weapon['name']]}",
                True, (205, 215, 230)
            )
            screen.blit(ammo, ammo.get_rect(
                center=(rect.centerx, rect.y + 37)))
        return

    # Preserve the compact bottom-right weapon bar in Practice and Creative.
    slot_w, slot_h, gap = 112, 62, 8
    count = min(3, len(weapon_inventory))
    total_w = count * slot_w + max(0, count - 1) * gap
    left = WIDTH - total_w - 18
    top = HEIGHT - slot_h - 18
    panel = pygame.Rect(left - 9, top - 25, total_w + 18, slot_h + 34)
    pygame.draw.rect(screen, (9, 17, 30), panel, border_radius=12)
    pygame.draw.rect(screen, (130, 155, 190), panel, 2, border_radius=12)
    title = small_font.render('WEAPONS', True, (235, 242, 255))
    screen.blit(title, (left, top - 21))
    for slot_index, weapon_index in enumerate(weapon_inventory[:3]):
        weapon = WEAPONS[weapon_index]
        rect = pygame.Rect(left + slot_index *
                           (slot_w + gap), top, slot_w, slot_h)
        selected = weapon_index == selected_weapon
        rarity_color = RARITIES[weapon_rarities[weapon_index]]['color']
        pygame.draw.rect(screen, (20, 31, 48), rect, border_radius=8)
        pygame.draw.rect(screen, rarity_color if selected else (100, 115, 140),
                         rect, 3 if selected else 1, border_radius=8)
        number = small_font.render(str(slot_index + 3), True,
                                   YELLOW if selected else WHITE)
        screen.blit(number, (rect.x + 6, rect.y + 4))
        name = small_font.render(weapon['name'][:13], True, WHITE)
        screen.blit(name, name.get_rect(center=(rect.centerx, rect.y + 25)))
        ammo = small_font.render(
            f"{weapon_ammo[weapon['name']]}/{weapon_reserve[weapon['name']]}",
            True, (205, 215, 230)
        )
        screen.blit(ammo, ammo.get_rect(center=(rect.centerx, rect.y + 48)))


def draw_quests_screen():
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((4, 8, 18, 235))
    screen.blit(shade, (0, 0))
    panel = pygame.Rect(170, 90, 860, 520)
    pygame.draw.rect(screen, (27, 39, 61), panel, border_radius=18)
    pygame.draw.rect(screen, (105, 145, 190), panel, 3, border_radius=18)
    title = big_font.render('QUESTS', True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 145)))
    draw_text(f'COIN BALANCE: {coins}', 470, 190, YELLOW, font)
    rows = [
        ('Play 1 match', quest_stats['matches'], 1, 40, 'first_match'),
        ('Get 5 eliminations',
         quest_stats['eliminations'], 5, 100, 'eliminations_5'),
        ('Open 3 chests', quest_stats['chests'], 3, 60, 'chests_3'),
    ]
    for i, (label, progress, goal, reward, quest_id) in enumerate(rows):
        y = 255 + i * 92
        row = pygame.Rect(235, y, 730, 70)
        pygame.draw.rect(screen, (44, 61, 86), row, border_radius=10)
        draw_text(label, row.x + 20, row.y + 12, WHITE, font)
        draw_text(f'PROGRESS: {min(progress, goal)}/{goal}', row.x + 20,
                  row.y + 43, (185, 205, 230), small_font)
        status = 'CLAIMED' if quest_id in claimed_quests else f'+{reward} COINS'
        draw_text(status, row.right - 175, row.y + 27,
                  (120, 235, 160) if quest_id in claimed_quests else YELLOW, small_font)
    draw_text('Quests save automatically. ESC closes this screen.',
              330, 565, WHITE, small_font)


def draw_minimap():
    # Keep the minimap directly below the health and shield bars.
    map_rect = (pygame.Rect(20, 88, 294, 78)
                if game_mode in ('Battle Royale', 'Bot Deathmatch')
                else pygame.Rect(20, 100, 198, 116))
    pygame.draw.rect(screen, (13, 24, 35), map_rect, border_radius=8)
    pygame.draw.rect(screen, (225, 235, 245), map_rect, 2, border_radius=8)
    inner = map_rect.inflate(-8, -8)
    # Color-coded regions and the map road.
    for left, right, name, color in WORLD_REGIONS:
        x1 = inner.x + int(left / WORLD_WIDTH * inner.width)
        x2 = inner.x + int(right / WORLD_WIDTH * inner.width)
        pygame.draw.rect(screen, color, (x1, inner.y,
                         max(1, x2-x1), inner.height))
    pygame.draw.line(screen, (65, 67, 72),
                     (inner.x, inner.centery), (inner.right, inner.centery), 5)
    for house in buildings:
        px = inner.x + int(house.centerx / WORLD_WIDTH * inner.width)
        if inner.left <= px <= inner.right:
            pygame.draw.rect(screen, (235, 220, 185),
                             (px, inner.centery - 5, 3, 5))
    for car in vehicles:
        if not car['occupied']:
            px = inner.x + int(car['rect'].centerx / WORLD_WIDTH * inner.width)
            pygame.draw.circle(screen, (245, 195, 65),
                               (px, inner.centery + 9), 2)
    player_px = inner.x + int(player.centerx / WORLD_WIDTH * inner.width)
    pygame.draw.circle(screen, (255, 255, 255),
                       (max(inner.x+2, min(inner.right-2, player_px)), inner.centery), 5)
    pygame.draw.circle(screen, (40, 80, 130),
                       (max(inner.x+2, min(inner.right-2, player_px)), inner.centery), 2)
    label = small_font.render('TAB: FULL MAP', True, WHITE)
    if game_mode in ('Battle Royale', 'Bot Deathmatch'):
        screen.blit(label, (map_rect.x + 8, map_rect.bottom - 17))
    else:
        screen.blit(label, (map_rect.x + 4, map_rect.bottom + 4))


def draw_full_map():
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((5, 10, 20, 225))
    screen.blit(shade, (0, 0))
    panel = pygame.Rect(55, 45, WIDTH - 110, HEIGHT - 90)
    pygame.draw.rect(screen, (25, 38, 57), panel, border_radius=16)
    pygame.draw.rect(screen, (215, 230, 245), panel, 3, border_radius=16)
    title = big_font.render('ISLAND MAP', True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 82)))
    map_area = pygame.Rect(95, 125, WIDTH - 190, HEIGHT - 220)
    for left, right, name, color in WORLD_REGIONS:
        x1 = map_area.x + int(left / WORLD_WIDTH * map_area.width)
        x2 = map_area.x + int(right / WORLD_WIDTH * map_area.width)
        region_rect = pygame.Rect(
            x1, map_area.y, max(1, x2-x1), map_area.height)
        pygame.draw.rect(screen, color, region_rect)
        pygame.draw.rect(screen, (35, 50, 60), region_rect, 2)
        region_label = small_font.render(name, True, WHITE)
        screen.blit(region_label, region_label.get_rect(
            center=(region_rect.centerx, map_area.y + 28)))
    # Road and map features are drawn in world-to-map coordinates.
    road_y = map_area.y + int(552 / HEIGHT * map_area.height)
    pygame.draw.line(screen, (60, 65, 72), (map_area.x, road_y),
                     (map_area.right, road_y), 13)
    for house in buildings:
        px = map_area.x + int(house.centerx / WORLD_WIDTH * map_area.width)
        py = road_y - 10
        pygame.draw.rect(screen, (245, 225, 190), (px-3, py-3, 6, 6))
    for bot in targets:
        px = map_area.x + int(bot.centerx / WORLD_WIDTH * map_area.width)
        py = road_y + 18
        pygame.draw.circle(screen, (220, 75, 75), (px, py), 4)
    for car in vehicles:
        if not car['occupied']:
            px = map_area.x + \
                int(car['rect'].centerx / WORLD_WIDTH * map_area.width)
            pygame.draw.circle(screen, (245, 195, 65), (px, road_y + 32), 5)
    px = map_area.x + int(player.centerx / WORLD_WIDTH * map_area.width)
    pygame.draw.circle(screen, (255, 255, 255), (px, road_y), 9)
    pygame.draw.circle(screen, (35, 95, 180), (px, road_y), 4)
    draw_text('YOU', max(map_area.x, min(map_area.right - 45, px + 10)),
              road_y - 23, WHITE, small_font)
    draw_text('WHITE = YOU   RED = BOTS   GOLD = CARS   BEIGE = BUILDINGS',
              170, HEIGHT - 72, WHITE, small_font)
    draw_text('PRESS TAB OR ESC TO CLOSE', 430,
              HEIGHT - 48, YELLOW, small_font)


load_profile()


screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Bunkerday - Battle Royale')
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
    'Bunkerday'
)
KEYBIND_FILE = os.path.join(KEYBIND_FOLDER, 'keybinds.json')

DEFAULT_KEYBINDS = {
    'Move left': pygame.K_a,
    'Move right': pygame.K_d,
    'Fire weapon': None,
    'Jump': pygame.K_SPACE,
    'Reload': pygame.K_r,
    'Pick up loot': pygame.K_e,
    'Edit': pygame.K_t,
    'Build mode': pygame.K_q,
    'Wall': pygame.K_1,
    'Floor': pygame.K_2,
    'Ramp': pygame.K_6,
    'Cycle build': pygame.K_c,
    'Open chest': pygame.K_f,
    'Confirm edit': pygame.K_RETURN,
    'Break builds': pygame.K_g,
    'Weapon 1': pygame.K_3,
    'Weapon 2': pygame.K_4,
    'Weapon 3': pygame.K_5,
    'Drop weapon': pygame.K_x
}

keybinds = DEFAULT_KEYBINDS.copy()
# Each action can use a keyboard key OR a mouse button, optional modifiers,
# and one of three activation styles: Tap, Hold, or Double.
action_modes = {name: ('Hold' if name in ('Move left', 'Move right', 'Fire weapon') else 'Tap')
                for name in DEFAULT_KEYBINDS}
action_mouse = {name: None for name in DEFAULT_KEYBINDS}
action_mouse['Fire weapon'] = 1
action_mods = {name: 0 for name in DEFAULT_KEYBINDS}
active_binding_actions = set()
hold_started = {}
hold_fired = set()
last_action_tap = {}
tap_action_until = {}
HOLD_DELAY_MS = 180
DOUBLE_TAP_MS = 350


def load_keybinds():
    try:
        with open(KEYBIND_FILE, 'r') as f:
            saved = json.load(f)
        # Read both the old flat format and the new advanced format.
        if isinstance(saved, dict) and 'keys' in saved:
            saved_keys = saved.get('keys', {})
            saved_modes = saved.get('modes', {})
            saved_mouse = saved.get('mouse', {})
            saved_mods = saved.get('mods', {})
        else:
            saved_keys, saved_modes, saved_mouse, saved_mods = saved, {}, {}, {}

        for action, key in saved_keys.items():
            if action in keybinds and key is None:
                keybinds[action] = None
            elif action in keybinds and isinstance(key, str) and key:
                try:
                    keybinds[action] = pygame.key.key_code(key)
                except (ValueError, TypeError):
                    pass
        for action, mode in saved_modes.items():
            if action in action_modes and mode in ('Tap', 'Hold', 'Double'):
                action_modes[action] = mode
        for action, button in saved_mouse.items():
            if action in action_mouse and button in (1, 2, 3, 4, 5):
                action_mouse[action] = button
        for action, mods in saved_mods.items():
            if action in action_mods and isinstance(mods, int):
                action_mods[action] = mods

        # Older versions used E for Edit. E is now the pickup key.
        if 'Pick up loot' not in saved_keys and keybinds.get('Edit') == pygame.K_e:
            keybinds['Edit'] = pygame.K_t
    except (OSError, ValueError, TypeError, AttributeError):
        pass


def save_keybinds():
    try:
        os.makedirs(KEYBIND_FOLDER, exist_ok=True)
        with open(KEYBIND_FILE, 'w') as f:
            json.dump({
                'keys': {name: (pygame.key.name(key) if key is not None else None)
                         for name, key in keybinds.items()},
                'modes': action_modes,
                'mouse': action_mouse,
                'mods': action_mods,
            }, f, indent=4)
        return True
    except OSError:
        return False


def binding_mods_match(required, actual):
    mask = pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_ALT
    return (required & mask) == (actual & mask)


def action_matches_key(action, event):
    return (keybinds.get(action) == event.key
            and action_mouse.get(action) is None
            and binding_mods_match(action_mods.get(action, 0), getattr(event, 'mod', 0)))


def action_matches_mouse(action, event):
    return (action_mouse.get(action) == event.button
            and binding_mods_match(action_mods.get(action, 0), pygame.key.get_mods()))


def cycle_build_type():
    global build_type, build_mode, break_mode
    order = ('wall', 'floor', 'ramp')
    build_type = order[(order.index(build_type) + 1) % len(order)]
    build_mode = True
    break_mode = False


def run_bound_action(action):
    global jump_buffer, break_mode, build_mode, pending_player_shot
    if action == 'Move left' or action == 'Move right':
        tap_action_until[action] = pygame.time.get_ticks() + 140
    elif action == 'Fire weapon':
        pending_player_shot = True
    elif action == 'Jump':
        jump_buffer = JUMP_BUFFER_TIME
    elif action == 'Reload':
        weapon = WEAPONS[selected_weapon]
        name = weapon['name']
        missing = weapon['capacity'] - weapon_ammo[name]
        amount = min(missing, weapon_reserve[name])
        weapon_ammo[name] += amount
        weapon_reserve[name] -= amount
    elif action == 'Pick up loot':
        pickup_nearby_loot()
    elif action == 'Edit':
        start_editing()
    elif action == 'Break builds':
        break_mode = not break_mode
        build_mode = False
    elif action == 'Build mode':
        build_mode = not build_mode
        break_mode = False
    elif action == 'Wall':
        build_type, build_mode, break_mode = 'wall', True, False
    elif action == 'Floor':
        build_type, build_mode, break_mode = 'floor', True, False
    elif action == 'Ramp':
        build_type, build_mode, break_mode = 'ramp', True, False
    elif action == 'Cycle build':
        cycle_build_type()
    elif action == 'Open chest':
        open_nearby_chest()
    elif action == 'Weapon 1':
        select_weapon_slot(0)
    elif action == 'Weapon 2':
        select_weapon_slot(1)
    elif action == 'Weapon 3':
        select_weapon_slot(2)
    elif action == 'Drop weapon':
        drop_selected_weapon()
    elif action == 'Confirm edit':
        if editing:
            confirm_edit()


def activate_bound_action(action):
    mode = action_modes.get(action, 'Tap')
    now = pygame.time.get_ticks()
    if mode == 'Double':
        previous = last_action_tap.get(action, -10000)
        if now - previous <= DOUBLE_TAP_MS:
            last_action_tap[action] = -10000
            run_bound_action(action)
        else:
            last_action_tap[action] = now
    elif mode == 'Tap':
        run_bound_action(action)
    # Hold actions are handled after HOLD_DELAY_MS while the input stays down.


def begin_bound_action(action):
    if action in active_binding_actions:
        return
    active_binding_actions.add(action)
    if action_modes.get(action, 'Tap') == 'Hold':
        hold_started[action] = pygame.time.get_ticks()
        hold_fired.discard(action)
    else:
        activate_bound_action(action)


def end_bound_action(action):
    active_binding_actions.discard(action)
    hold_started.pop(action, None)
    hold_fired.discard(action)


def update_held_bindings():
    now = pygame.time.get_ticks()
    for action in tuple(active_binding_actions):
        if (action_modes.get(action) == 'Hold'
                and action not in hold_fired
                and now - hold_started.get(action, now) >= HOLD_DELAY_MS):
            hold_fired.add(action)
            if action not in ('Move left', 'Move right'):
                run_bound_action(action)


def action_is_held(action):
    held_mode_active = (action in active_binding_actions
                        and action_modes.get(action) == 'Hold')
    return (held_mode_active
            or pygame.time.get_ticks() < tap_action_until.get(action, 0))


load_keybinds()

settings_open = False
waiting_for_key = None
settings_message = ''
settings_scroll = 0
settings_button = pygame.Rect(WIDTH - 112, 118, 100, 42)
current_mode_button = pygame.Rect(WIDTH - 310, 118, 188, 42)
practice_exit_button = pygame.Rect(WIDTH - 175, 175, 155, 46)

platforms = [
    pygame.Rect(0, GROUND_Y, WORLD_WIDTH, 110),
    pygame.Rect(450, 470, 220, 25),
    pygame.Rect(900, 390, 250, 25),
    pygame.Rect(1450, 480, 240, 25),
    pygame.Rect(2050, 400, 250, 25),
    pygame.Rect(2750, 470, 250, 25),
    pygame.Rect(3400, 390, 300, 25),
    pygame.Rect(4100, 470, 260, 25),
    pygame.Rect(4750, 385, 280, 25),
    pygame.Rect(5450, 465, 250, 25),
    pygame.Rect(6150, 380, 300, 25),
    pygame.Rect(6650, 475, 220, 25),
    pygame.Rect(7350, 400, 280, 25),
    pygame.Rect(8050, 475, 260, 25),
    pygame.Rect(8750, 385, 300, 25),
    pygame.Rect(9500, 465, 250, 25), pygame.Rect(10150, 390, 280, 25), pygame.Rect(10850, 470, 260, 25), pygame.Rect(
        11550, 385, 300, 25), pygame.Rect(12250, 465, 280, 25), pygame.Rect(13000, 395, 300, 25), pygame.Rect(13600, 470, 250, 25),
    pygame.Rect(14350, 390, 300, 25), pygame.Rect(15050, 465, 260, 25),
    pygame.Rect(15700, 380, 320, 25), pygame.Rect(16450, 465, 280, 25),
    pygame.Rect(17150, 390, 300, 25), pygame.Rect(17850, 470, 260, 25),
    pygame.Rect(18500, 385, 300, 25), pygame.Rect(19300, 465, 280, 25)
]

buildings = [
    pygame.Rect(700, 490, 130, 100),
    pygame.Rect(1700, 490, 180, 100),
    pygame.Rect(2500, 490, 150, 100),
    pygame.Rect(3200, 490, 180, 100),
    pygame.Rect(4250, 490, 170, 100),
    pygame.Rect(5150, 490, 190, 100),
    pygame.Rect(6000, 490, 160, 100),
    pygame.Rect(6650, 490, 170, 100),
    pygame.Rect(7450, 490, 180, 100),
    pygame.Rect(8350, 490, 190, 100),
    pygame.Rect(9250, 490, 170, 100), pygame.Rect(10100, 490, 180, 100), pygame.Rect(
        11100, 490, 190, 100), pygame.Rect(12100, 490, 170, 100), pygame.Rect(13100, 490, 190, 100),
    pygame.Rect(14500, 490, 180, 100), pygame.Rect(15300, 490, 190, 100),
    pygame.Rect(16200, 490, 170, 100), pygame.Rect(17000, 490, 190, 100),
    pygame.Rect(18100, 490, 180, 100), pygame.Rect(19000, 490, 190, 100)
]

building_health = [100 for _ in buildings]

TREE_POSITIONS = [
    (x, random.randint(505, 555), random.randint(22, 34))
    for x in range(250, WORLD_WIDTH, 310)
    if all(abs(x - house.centerx) > 125 for house in buildings)
]
TREE_POSITIONS_INITIAL = TREE_POSITIONS.copy()

player = pygame.Rect(160, 400, 40, 75)
player_x = float(player.x)
player_y = float(player.y)

velocity_x = 0
velocity_y = 0

speed = 5.8
jump_power = -15.5
gravity = 0.68
# Momentum-based movement: quick response, gentle braking, and air steering.
movement_velocity = 0.0
GROUND_ACCELERATION = 0.82
AIR_ACCELERATION = 0.48
GROUND_FRICTION = 0.72
AIR_FRICTION = 0.965
player_walk_phase = 0.0

elimination_effects = []
leave_game_button = pygame.Rect(WIDTH - 458, 118, 140, 42)
PICKAXE_REACH = 115

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
    },
    {
        'name': 'SMG',
        'capacity': 35,
        'fire_delay': 4,
        'speed': 17,
        'damage': 13,
        'build_damage': 7,
        'pellets': 1,
        'spread': 0.07
    },
    {
        'name': 'Hunting Rifle',
        'capacity': 5,
        'fire_delay': 48,
        'speed': 25,
        'damage': 75,
        'build_damage': 35,
        'pellets': 1,
        'spread': 0.005
    },
    {
        'name': 'Burst Rifle',
        'capacity': 24,
        'fire_delay': 16,
        'speed': 19,
        'damage': 19,
        'build_damage': 10,
        'pellets': 3,
        'spread': 0.045
    },
    {
        'name': 'Tactical Rifle',
        'capacity': 24,
        'fire_delay': 9,
        'speed': 20,
        'damage': 23,
        'build_damage': 11,
        'pellets': 1,
        'spread': 0.035
    },
    {
        'name': 'Marksman Rifle',
        'capacity': 10,
        'fire_delay': 30,
        'speed': 26,
        'damage': 52,
        'build_damage': 24,
        'pellets': 1,
        'spread': 0.012
    },
    {
        'name': 'Sniper Rifle',
        'capacity': 5,
        'fire_delay': 58,
        'speed': 34,
        'damage': 92,
        'build_damage': 30,
        'pellets': 1,
        'spread': 0.002
    }
]

weapon_ammo = {
    w['name']: w['capacity']
    for w in WEAPONS
}
# Finite reserve ammunition: each weapon starts with two extra magazines.
weapon_reserve = {
    w['name']: w['capacity'] * 2
    for w in WEAPONS
}

selected_weapon = 0
weapon_inventory = [0, 1, 2]
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
    {'rect': pygame.Rect(x, GROUND_Y - 30, 34, 30),
     'opened': False, 'rarity': 'Common'}
    for x in (560, 1080, 1550, 2250, 3050, 3650,
              4300, 4900, 5550, 6250, 6800, 7600, 8400, 9200, 10100, 11000, 11900, 12800, 13700,
              14500, 15300, 16100, 16900, 17700, 18500, 19300)
]

storm_center = (WORLD_WIDTH // 2, 390)
storm_start_radius = 7600
storm_end_radius = 650
storm_delay = 60.0
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
# Every bot has its own magazine, reserve ammo, and reload timer.
BOT_MAGAZINE_SIZE = 12
BOT_STARTING_RESERVE = 48
BOT_RELOAD_TIME = 120.0  # approximately two seconds at 60 FPS
bot_ammo = []
bot_reserve_ammo = []
bot_reload_timers = []
enemy_bullets = []
bot_skin_colors = []
bot_weapon_indices = []
PICKUP_RANGE = 105

game_mode = 'Battle Royale'
selected_mode = 'Battle Royale'
game_started = False
eliminations = 0
DEATHMATCH_GOAL = 10
MATCH_CHALLENGE_GOAL = 3
challenge_complete = False

MODE_BUTTONS = {
    'Battle Royale': pygame.Rect(430, 240, 365, 56),
    'Bot Deathmatch': pygame.Rect(430, 304, 365, 56),
    'Practice': pygame.Rect(430, 368, 365, 56),
    'Creative': pygame.Rect(430, 432, 365, 56)
}
START_BUTTON = pygame.Rect(875, 565, 270, 55)

# Local lobby UI. Online friends and real invitations will be connected later.
LOBBY_SKINS = [
    ("BLUE", (45, 115, 220)),
    ("RED", (220, 65, 65)),
    ("GREEN", (55, 165, 95)),
    ("PURPLE", (145, 85, 210)),
    ("ORANGE", (225, 125, 40)),
    ("CYAN", (35, 175, 190)),
]
selected_skin = 0

# Character customization: these choices are drawn in both the lobby and matches.
CUSTOM_OPTIONS = {
    "FACE": ["Classic", "Shades", "Visor", "Mask", "Robot", "Happy", "Neon"],
    "HEAD": ["None", "Cap", "Helmet", "Headphones", "Beanie", "Crown", "Antenna"],
    "BACK": ["None", "Backpack", "Wings", "Drone", "Cape", "Jetpack", "Shield"],
    "HAIR": ["None", "Spiky", "Mohawk", "Long", "Curly", "Bun"],
    "OUTFIT": ["Classic", "Camo", "Stripes", "Split", "Stealth", "Neon"],
    "WEAPON": ["Steel", "Crimson", "Neon", "Gold", "Purple", "Arctic", "Lava", "Carbon", "Forest"],
}
custom_selected = {category: 0 for category in CUSTOM_OPTIONS}
for _category, _index in globals().get('_saved_custom_selected', {}).items():
    if _category in custom_selected and isinstance(_index, int):
        custom_selected[_category] = max(
            0, min(_index, len(CUSTOM_OPTIONS[_category]) - 1))
CUSTOM_ROWS = {
    category: pygame.Rect(48, 430 + i * 27, 304, 24)
    for i, category in enumerate(CUSTOM_OPTIONS)
}
CUSTOM_PREV_BUTTONS = {
    category: pygame.Rect(292, 430 + i * 27, 26, 24)
    for i, category in enumerate(CUSTOM_OPTIONS)
}
CUSTOM_NEXT_BUTTONS = {
    category: pygame.Rect(322, 430 + i * 27, 26, 24)
    for i, category in enumerate(CUSTOM_OPTIONS)
}
lobby_code = ""
joining_lobby = False
join_code_input = ""
adding_friend = False
friend_input_text = ""
friend_list = []
lobby_message = "Choose a mode, customize your character, or create a party."

SKIN_BUTTONS = [
    pygame.Rect(48 + (i % 3) * 105, 405 + (i // 3) * 58, 94, 48)
    for i in range(len(LOBBY_SKINS))
]
CREATE_LOBBY_BUTTON = pygame.Rect(430, 505, 175, 52)
JOIN_LOBBY_BUTTON = pygame.Rect(620, 505, 175, 52)
INVITE_BUTTON = pygame.Rect(430, 565, 365, 42)
FRIEND_ADD_BUTTON = pygame.Rect(875, 185, 270, 42)
FRIEND_INPUT_RECT = pygame.Rect(875, 185, 270, 42)
FRIEND_ROW_RECTS = [
    pygame.Rect(875, 250 + i * 58, 270, 48)
    for i in range(5)
]

# Remember a click until the weapon cooldown ends.
pending_player_shot = False

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
match_end_timer = 0.0

EDIT_PRESETS = {
    'short': {(0, 0)},
    'really_short': {(0, 0), (1, 0)},
    'window': {(1, 0)},
    'door': {(1, 0), (2, 0)}
}

camera_x = 0
player_facing = 1


def fire_player_weapon():
    global shoot_cooldown

    weapon = WEAPONS[selected_weapon]
    ammo = weapon_ammo[weapon['name']]

    if ammo <= 0 or shoot_cooldown > 0:
        return False

    mouse_x, mouse_y = pygame.mouse.get_pos()
    world_mouse_x = mouse_x + camera_x

    start_x = player.centerx
    start_y = player.centery
    angle_to_mouse = math.atan2(
        mouse_y - start_y,
        world_mouse_x - start_x
    )

    damage_multiplier = RARITIES[
        weapon_rarities[selected_weapon]
    ]['multiplier']

    # Start the projectile just outside the player's body.
    muzzle_x = start_x + math.cos(angle_to_mouse) * 27
    muzzle_y = start_y + math.sin(angle_to_mouse) * 27

    for _ in range(weapon['pellets']):
        shot_angle = angle_to_mouse + random.uniform(
            -weapon['spread'],
            weapon['spread']
        )
        bullets.append([
            float(muzzle_x),
            float(muzzle_y),
            math.cos(shot_angle) * weapon['speed'],
            math.sin(shot_angle) * weapon['speed'],
            int(weapon['damage'] * damage_multiplier),
            int(weapon['build_damage'] * damage_multiplier)
        ])

    weapon_ammo[weapon['name']] -= 1
    shoot_cooldown = weapon['fire_delay']
    return True


def roll_rarity():
    roll = random.randint(1, sum(weight for _, weight in RARITY_ROLLS))
    total = 0

    for rarity, weight in RARITY_ROLLS:
        total += weight

        if roll <= total:
            return rarity

    return 'Common'


def drop_loot(world_x, world_y, forced_rarity=None):
    loot_type = random.choices(
        ['ammo', 'shield', 'health', 'materials', 'weapon'],
        weights=[35, 20, 18, 17, 10],
        k=1
    )[0]

    item = {
        'type': loot_type,
        'rect': pygame.Rect(int(world_x - 12), int(world_y - 12), 24, 24),
        'amount': 0,
        'rarity': forced_rarity or roll_rarity(),
        'weapon_index': random.randrange(len(WEAPONS)),
        'ammo': 0
    }

    if loot_type == 'ammo':
        item['amount'] = random.randint(8, 20)
    elif loot_type in ('shield', 'health'):
        item['amount'] = 25
    elif loot_type == 'materials':
        item['amount'] = 20
    else:
        item['amount'] = 1
        item['ammo'] = WEAPONS[item['weapon_index']]['capacity']

    loot_drops.append(item)


def open_nearby_chest():
    for chest in chests:
        if chest['opened']:
            continue

        if player.inflate(90, 70).colliderect(chest['rect']):
            chest['opened'] = True
            add_coins(5, 'chest')
            update_quest_progress('chests')

            rarity = chest.get('rarity', 'Common')
            loot_count = {'Common': 2, 'Uncommon': 3,
                          'Rare': 4, 'Epic': 5, 'Legendary': 6}[rarity]
            for _ in range(loot_count):
                drop_loot(chest['rect'].centerx + random.randint(-35, 35),
                          chest['rect'].top - random.randint(8, 30), rarity)

            return True

    return False


def nearest_loot():
    nearby = []
    for item in loot_drops:
        distance = math.hypot(item["rect"].centerx - player.centerx,
                              item["rect"].centery - player.centery)
        if distance <= PICKUP_RANGE:
            nearby.append((distance, item))
    return min(nearby, key=lambda pair: pair[0])[1] if nearby else None


def pickup_nearby_loot():
    item = nearest_loot()
    if item is None:
        return False
    collect_loot(item)
    return True


def draw_ammo_icon(center, size=26):
    x, y = center
    rect = pygame.Rect(x-size//2, y-size//2, size, size)
    pygame.draw.rect(screen, (225, 185, 55), rect, border_radius=4)
    pygame.draw.rect(screen, (90, 65, 25), rect, 2, border_radius=4)
    for offset in (-6, 0, 6):
        pygame.draw.rect(screen, (255, 230, 145),
                         (x+offset-2, y-7, 4, 14), border_radius=1)


def collect_loot(only_item=None):
    global health, shield, materials, selected_weapon

    for item in ([only_item] if only_item is not None else []):
        if item not in loot_drops:
            continue

        kind = item['type']
        amount = item['amount']

        if kind == 'ammo':
            weapon_index = item['weapon_index']
            weapon_name = WEAPONS[weapon_index]['name']

            weapon_reserve[weapon_name] = min(
                WEAPONS[weapon_index]['capacity'] * 2,
                weapon_reserve[weapon_name] + amount
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
            rarity_order = list(RARITIES)

            if weapon_index in weapon_inventory:
                current = weapon_rarities[weapon_index]
                if rarity_order.index(item['rarity']) > rarity_order.index(current):
                    weapon_rarities[weapon_index] = item['rarity']
                weapon_name = WEAPONS[weapon_index]['name']
                weapon_reserve[weapon_name] = min(
                    WEAPONS[weapon_index]['capacity'] * 2,
                    weapon_reserve[weapon_name] + max(
                        1, item.get('ammo', WEAPONS[weapon_index]['capacity'])
                    )
                )
            else:
                # Keep three weapon slots. A new weapon replaces the selected slot
                # when all three slots are occupied.
                if len(weapon_inventory) >= 3:
                    old_weapon = selected_weapon
                    old_name = WEAPONS[old_weapon]['name']
                    old_total_ammo = weapon_ammo[old_name] + \
                        weapon_reserve[old_name]
                    loot_drops.append({
                        'type': 'weapon',
                        'rect': pygame.Rect(player.centerx + player_facing * 35 - 12,
                                            player.bottom - 24, 24, 24),
                        'amount': 1, 'rarity': weapon_rarities[old_weapon],
                        'weapon_index': old_weapon, 'ammo': old_total_ammo
                    })
                    slot = weapon_inventory.index(old_weapon)
                    weapon_inventory[slot] = weapon_index
                else:
                    weapon_inventory.append(weapon_index)

                weapon_rarities[weapon_index] = item['rarity']
                weapon_name = WEAPONS[weapon_index]['name']
                total_ammo = max(0, item.get(
                    'ammo', WEAPONS[weapon_index]['capacity']))
                weapon_ammo[weapon_name] = min(
                    WEAPONS[weapon_index]['capacity'], total_ammo
                )
                weapon_reserve[weapon_name] = min(
                    WEAPONS[weapon_index]['capacity'] * 2,
                    max(0, total_ammo - weapon_ammo[weapon_name])
                )
                selected_weapon = weapon_index

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
            platform.left <= build_right
            and platform.right >= build_left
        ) if build_width > 1 else (
            platform.left <= center_x <= platform.right
        )

        if overlaps:
            possible_surfaces.append(platform.top)

    for build in placed_builds:
        rect = build['rect']

        overlaps = (
            rect.left <= build_right
            and rect.right >= build_left
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
    # Bullets pass through houses, but collide with player-built pieces
    # and the map's platforms. Player builds can take bullet damage.
    for index in range(len(placed_builds) - 1, -1, -1):
        build = placed_builds[index]
        if bullet_hits_build(build, world_x, world_y):
            damage_build_from_bullet(index, damage)
            return True

    for platform in platforms:
        if platform.collidepoint(world_x, world_y):
            return True

    return False


def bullet_hits_bot(bullet_x, bullet_y, bullet_radius, target):
    """Use generous body and head hit areas so shots register more easily."""
    body_hitbox = target.inflate(80 + bullet_radius * 2,
                                 70 + bullet_radius * 2)
    if body_hitbox.collidepoint(bullet_x, bullet_y):
        return True

    head_center = (target.centerx, target.y - 12)
    head_radius = 28 + bullet_radius
    return math.hypot(
        bullet_x - head_center[0],
        bullet_y - head_center[1]
    ) <= head_radius


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


def select_weapon_slot(slot):
    global selected_weapon
    if 0 <= slot < len(weapon_inventory):
        selected_weapon = weapon_inventory[slot]


def drop_selected_weapon():
    global selected_weapon

    if selected_weapon not in weapon_inventory:
        return

    dropped_index = selected_weapon
    weapon_name = WEAPONS[dropped_index]['name']
    dropped_ammo = (
        weapon_ammo[weapon_name] + weapon_reserve[weapon_name]
    )

    # Don't allow the player to drop their last weapon.
    if len(weapon_inventory) <= 1:
        return

    loot_drops.append({
        'type': 'weapon',
        'rect': pygame.Rect(
            player.centerx + player_facing * 33 - 12,
            player.bottom - 24,
            24,
            24
        ),
        'amount': 1,
        'rarity': weapon_rarities[dropped_index],
        'weapon_index': dropped_index,
        'ammo': dropped_ammo
    })

    weapon_inventory.remove(dropped_index)
    selected_weapon = weapon_inventory[0]


def start_match(mode):
    global game_mode, game_started, game_won, eliminations, match_end_timer
    global health, shield, player_x, player_y, velocity_x, velocity_y
    global on_ground, jump_buffer, coyote_timer, camera_x
    global storm_elapsed, storm_radius, storm_started, storm_damage_timer
    global materials, selected_weapon, shoot_cooldown, build_mode, break_mode
    global weapon_inventory
    global editing, active_build_index, break_message, break_message_timer
    global pending_player_shot, vehicles, vehicle_active, challenge_complete
    global match_rewarded, match_coins_earned
    global shop_open, quests_open, full_map_open, movement_velocity, TREE_POSITIONS

    game_mode = mode
    match_rewarded = False
    match_coins_earned = 0
    shop_open = False
    quests_open = False
    full_map_open = False
    game_won = False
    match_end_timer = 0.0
    movement_velocity = 0.0
    elimination_effects.clear()
    TREE_POSITIONS = TREE_POSITIONS_INITIAL.copy()
    eliminations = 0
    challenge_complete = False
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
    materials = 999999 if mode == 'Creative' else 100
    selected_weapon = 0
    weapon_inventory[:] = [0, 1, 2]
    shoot_cooldown = 0
    pending_player_shot = False
    vehicle_active = False
    vehicles = [
        {'rect': pygame.Rect(x, GROUND_Y - 38, 92, 34),
         'color': random.choice([(195, 55, 55), (55, 115, 205), (220, 175, 55),
                                 (65, 155, 100), (125, 85, 175)]),
         'occupied': False}
        for x in VEHICLE_SPAWN_X
    ]
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
        chest['rarity'] = roll_rarity()
    for weapon in WEAPONS:
        weapon_ammo[weapon['name']] = weapon['capacity']
        weapon_reserve[weapon['name']] = weapon['capacity'] * 2

    count = 20 if mode == 'Battle Royale' else 10 if mode == 'Bot Deathmatch' else 0
    if mode == 'Creative':
        materials = 999999
    targets[:] = create_bot_positions(count)
    bot_health[:] = [100 for _ in targets]
    bot_shoot_cooldowns[:] = [random.uniform(0, 8) for _ in targets]
    bot_respawn_timers[:] = [0 for _ in targets]
    bot_ammo[:] = [BOT_MAGAZINE_SIZE for _ in targets]
    bot_reserve_ammo[:] = [BOT_STARTING_RESERVE for _ in targets]
    bot_reload_timers[:] = [0.0 for _ in targets]
    bot_skin_colors[:] = [random.choice([(45, 115, 220), (220, 65, 65), (55, 165, 95),
                                         (145, 85, 210), (225, 125, 40), (35, 175, 190), (55, 65, 80), (210, 185, 125)])
                          for _ in targets]
    bot_weapon_indices[:] = [random.randrange(len(WEAPONS)) for _ in targets]
    for ammo_x in range(350, WORLD_WIDTH - 250, 520):
        if random.random() < 0.72:
            loot_drops.append({
                'type': 'ammo',
                'rect': pygame.Rect(ammo_x + random.randint(-100, 100), GROUND_Y-28, 26, 24),
                'amount': random.randint(12, 30), 'rarity': 'Common',
                'weapon_index': random.randrange(len(WEAPONS)), 'ammo': 0
            })
    game_started = True


def create_lobby_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(alphabet) for _ in range(6))


def get_outfit_color(base_color):
    outfit = CUSTOM_OPTIONS["OUTFIT"][custom_selected["OUTFIT"]]
    if outfit == "Stealth":
        return (55, 62, 76)
    if outfit == "Neon":
        return (40, 220, 205)
    if outfit == "Camo":
        return (83, 112, 65)
    if outfit == "Stripes":
        return (max(0, base_color[0] - 25), max(0, base_color[1] - 25), min(255, base_color[2] + 35))
    if outfit == "Split":
        return base_color
    return base_color


def draw_custom_character(center_x, center_y, color, scale=1.0,
                          walk_phase=0.0, movement_amount=0.0, facing=1):
    body_w = max(10, int(48 * scale))
    body_h = max(15, int(76 * scale))
    head_r = max(7, int(18 * scale))
    outfit = CUSTOM_OPTIONS["OUTFIT"][custom_selected["OUTFIT"]]
    face = CUSTOM_OPTIONS["FACE"][custom_selected["FACE"]]
    head = CUSTOM_OPTIONS["HEAD"][custom_selected["HEAD"]]
    back = CUSTOM_OPTIONS["BACK"][custom_selected["BACK"]]
    hair = CUSTOM_OPTIONS["HAIR"][custom_selected["HAIR"]]
    body = pygame.Rect(center_x - body_w // 2, center_y -
                       body_h // 2 + int(12 * scale), body_w, body_h)
    body_color = get_outfit_color(color)

    # Back props are deliberately drawn first so they sit behind the character.
    if back != "None":
        prop_color = (95, 150, 220) if back in (
            "Wings", "Drone", "Shield") else (135, 95, 60)
        if back == "Wings":
            pygame.draw.polygon(screen, prop_color, [(body.left, body.top + 12*scale), (body.left-int(
                24*scale), body.top-int(2*scale)), (body.left-int(17*scale), body.bottom-int(5*scale))])
            pygame.draw.polygon(screen, prop_color, [(body.right, body.top + 12*scale), (body.right+int(
                24*scale), body.top-int(2*scale)), (body.right+int(17*scale), body.bottom-int(5*scale))])
        elif back == "Cape":
            pygame.draw.polygon(screen, (145, 45, 55), [(body.left+3, body.top+5), (body.right-3, body.top+5), (body.right+int(
                10*scale), body.bottom+int(8*scale)), (body.left-int(10*scale), body.bottom+int(8*scale))])
        elif back == "Drone":
            pygame.draw.circle(screen, prop_color, (center_x,
                               body.top-int(18*scale)), max(3, int(7*scale)))
            pygame.draw.line(screen, WHITE, (center_x, body.top-int(11*scale)),
                             (center_x, body.top), max(1, int(2*scale)))
        else:
            pygame.draw.rect(screen, prop_color, (body.left-int(8*scale), body.top +
                             int(12*scale), int(16*scale), int(30*scale)), border_radius=4)

    # Arms sit behind the torso and use layered outlines/shading for depth.
    shoulder_y = body.top + int(15 * scale)
    elbow_y = body.top + int(34 * scale)
    hand_y = body.bottom - int(8 * scale)
    arm_outline = (24, 29, 39)
    arm_width = max(4, int(11 * scale))
    for side in (-1, 1):
        shoulder = (center_x + side * int(17 * scale), shoulder_y)
        swing = math.sin(walk_phase) * movement_amount * 8 * scale
        elbow = (center_x + side * int(27 * scale),
                 elbow_y + int(swing * 0.35))
        wrist = (center_x + side * int(22 * scale),
                 hand_y - int(swing))
        pygame.draw.line(screen, arm_outline, shoulder, elbow,
                         arm_width + max(1, int(3 * scale)))
        pygame.draw.line(screen, body_color, shoulder, elbow, arm_width)
        pygame.draw.line(screen, arm_outline, elbow, wrist,
                         arm_width + max(1, int(3 * scale)))
        pygame.draw.line(screen, body_color, elbow, wrist, arm_width)
        pygame.draw.circle(screen, (35, 39, 49), wrist, max(3, int(6 * scale)))
        pygame.draw.circle(screen, (65, 70, 82), wrist, max(2, int(4 * scale)))

    pygame.draw.rect(screen, (25, 30, 40), body.inflate(max(2, int(4*scale)), max(2, int(4*scale))),
                     max(3, int(9*scale)), border_radius=max(4, int(9*scale)))
    pygame.draw.rect(screen, body_color, body,
                     border_radius=max(3, int(8*scale)))
    pygame.draw.line(screen,
                     tuple(min(255, c + 35) for c in body_color),
                     (body.left + int(5 * scale), body.top + int(8 * scale)),
                     (body.left + int(5 * scale), body.bottom - int(20 * scale)),
                     max(1, int(2 * scale)))
    if outfit == "Stripes":
        for offset in (-12, 0, 12):
            pygame.draw.line(screen, WHITE, (center_x+int(offset*scale), body.top+int(8*scale)),
                             (center_x+int(offset*scale), body.bottom-int(8*scale)), max(1, int(3*scale)))
    elif outfit == "Split":
        pygame.draw.rect(screen, (35, 35, 45), (center_x,
                         body.top, body_w//2, body_h), border_radius=3)

    # Layered field vest, shoulder panels, belt, and utility pouches.
    vest = pygame.Rect(center_x - int(14 * scale), body.top + int(8 * scale),
                       int(28 * scale), int(37 * scale))
    pygame.draw.rect(screen, (35, 43, 54), vest, max(1, int(2 * scale)),
                     border_radius=max(2, int(4 * scale)))
    pygame.draw.line(screen, (165, 175, 185),
                     (center_x, vest.top + int(3 * scale)),
                     (center_x, vest.bottom - int(3 * scale)), max(1, int(2 * scale)))
    pygame.draw.line(screen, (105, 115, 125),
                     (vest.left + int(4 * scale), vest.top + int(4 * scale)),
                     (vest.right - int(4 * scale), vest.top + int(4 * scale)), max(1, int(2 * scale)))
    for side in (-1, 1):
        pouch = pygame.Rect(center_x + side * int(10 * scale) - int(4 * scale),
                            body.bottom - int(19 * scale),
                            max(3, int(8 * scale)), max(3, int(10 * scale)))
        pygame.draw.rect(screen, (65, 75, 82), pouch,
                         border_radius=max(1, int(2 * scale)))
        shoulder_pad = (center_x + side * int(18 * scale),
                        shoulder_y - int(1 * scale))
        pygame.draw.circle(screen, (75, 85, 98),
                           shoulder_pad, max(3, int(7 * scale)))
    pygame.draw.line(screen, (25, 30, 38),
                     (body.left + int(3 * scale), body.bottom - int(13 * scale)),
                     (body.right - int(3 * scale), body.bottom - int(13 * scale)), max(2, int(4 * scale)))
    pygame.draw.circle(screen, (190, 160, 75), (center_x,
                       body.bottom - int(13 * scale)), max(1, int(3 * scale)))
    if equipped_locker_items.get('ACCESSORY') == 'Gold Chain':
        chain_y = body.top + int(12 * scale)
        pygame.draw.arc(screen, (225, 185, 65),
                        (center_x - int(13 * scale), chain_y,
                         int(26 * scale), int(18 * scale)),
                        math.pi, 2 * math.pi, max(1, int(3 * scale)))

    # Animated legs, knee pads, and boots make running feel alive.
    leg_color = (35, 35, 45)
    stride = math.sin(walk_phase) * movement_amount * 8 * scale
    for side in (-1, 1):
        hip = (center_x + side * int(8 * scale), body.bottom - int(2 * scale))
        knee = (center_x + side * int(11 * scale) + int(stride * side),
                body.bottom + int(8 * scale))
        boot = (center_x + side * int(13 * scale) + int(stride * side * 1.35),
                body.bottom + int(17 * scale) - int(abs(stride) * 0.22))
        pygame.draw.line(screen, (20, 24, 32), hip, boot,
                         max(5, int(11 * scale)))
        pygame.draw.line(screen, leg_color, hip, knee,
                         max(4, int(8 * scale)))
        pygame.draw.line(screen, (55, 62, 75), knee, boot,
                         max(4, int(7 * scale)))
        pygame.draw.circle(screen, (105, 115, 130), knee,
                           max(2, int(4 * scale)))
        pygame.draw.ellipse(screen, (22, 25, 32),
                            (boot[0] - int(7 * scale), boot[1] - int(3 * scale),
                             max(4, int(16 * scale)), max(3, int(8 * scale))))
        pygame.draw.line(screen, (120, 130, 145),
                         (boot[0] - int(3 * scale), boot[1] - int(1 * scale)),
                         (boot[0] + int(4 * scale), boot[1] - int(1 * scale)),
                         max(1, int(2 * scale)))

    head_center = (center_x, body.top-int(2*scale))
    pygame.draw.circle(screen, (255, 210, 165), head_center, head_r)

    # Hair styles
    hair_color = (55, 35, 25)
    if hair == "Spiky":
        for dx in (-10, 0, 10):
            pygame.draw.polygon(screen, hair_color, [(center_x+int(dx*scale), head_center[1]-head_r+5), (center_x+int(
                (dx-4)*scale), head_center[1]-head_r-int(10*scale)), (center_x+int((dx+5)*scale), head_center[1]-head_r+4)])
    elif hair == "Mohawk":
        pygame.draw.rect(screen, hair_color, (center_x-int(4*scale),
                         head_center[1]-head_r-int(10*scale), int(8*scale), int(15*scale)))
    elif hair == "Long":
        pygame.draw.rect(screen, hair_color, (center_x-head_r,
                         head_center[1]-int(7*scale), max(2, int(6*scale)), int(28*scale)))
        pygame.draw.rect(screen, hair_color, (center_x+head_r-int(6*scale),
                         head_center[1]-int(7*scale), max(2, int(6*scale)), int(28*scale)))
    elif hair in ("Curly", "Bun"):
        for dx in (-9, 0, 9):
            pygame.draw.circle(screen, hair_color, (center_x+int(dx*scale),
                               head_center[1]-head_r+3), max(2, int(6*scale)))
        if hair == "Bun":
            pygame.draw.circle(screen, hair_color, (center_x,
                               head_center[1]-head_r-int(5*scale)), max(3, int(6*scale)))

    # Face styles
    eye_y = head_center[1] - int(2*scale)
    if face == "Shades":
        pygame.draw.rect(screen, (20, 25, 35), (center_x-int(14*scale),
                         eye_y-int(3*scale), int(28*scale), int(9*scale)), border_radius=3)
    elif face == "Visor":
        pygame.draw.rect(screen, (45, 210, 235), (center_x-int(15*scale),
                         eye_y-int(5*scale), int(30*scale), int(12*scale)), border_radius=4)
    elif face == "Mask":
        pygame.draw.rect(screen, (70, 80, 95), (center_x-int(12*scale),
                         eye_y+int(2*scale), int(24*scale), int(10*scale)), border_radius=3)
    elif face == "Robot":
        pygame.draw.circle(screen, (40, 230, 245),
                           (center_x-int(6*scale), eye_y), max(1, int(3*scale)))
        pygame.draw.circle(screen, (40, 230, 245),
                           (center_x+int(6*scale), eye_y), max(1, int(3*scale)))
        pygame.draw.line(screen, (80, 90, 105), (center_x-int(8*scale), head_center[1]+int(
            7*scale)), (center_x+int(8*scale), head_center[1]+int(7*scale)), max(1, int(2*scale)))
    elif face == "Neon":
        pygame.draw.line(screen, (40, 255, 220), (center_x-int(10*scale),
                         eye_y), (center_x+int(10*scale), eye_y), max(2, int(3*scale)))
    else:
        pygame.draw.circle(
            screen, BLACK, (center_x-int(6*scale), eye_y), max(1, int(2*scale)))
        pygame.draw.circle(
            screen, BLACK, (center_x+int(6*scale), eye_y), max(1, int(2*scale)))
        if face == "Happy":
            pygame.draw.arc(screen, (120, 45, 45), (center_x-int(7*scale),
                            head_center[1], int(14*scale), int(9*scale)), 3.3, 6.1, max(1, int(2*scale)))

    if equipped_locker_items.get('ACCESSORY') == 'Pilot Goggles':
        goggle_y = head_center[1] - int(2 * scale)
        pygame.draw.rect(screen, (45, 55, 70),
                         (center_x - int(15 * scale), goggle_y - int(5 * scale),
                          int(30 * scale), int(11 * scale)),
                         max(1, int(2 * scale)), border_radius=max(2, int(4 * scale)))
        pygame.draw.line(screen, (105, 205, 235),
                         (center_x - int(12 * scale), goggle_y),
                         (center_x + int(12 * scale), goggle_y), max(1, int(2 * scale)))

    # Head accessories
    if head == "Cap":
        pygame.draw.arc(screen, (35, 65, 145), (center_x-head_r,
                        head_center[1]-head_r, head_r*2, head_r), 0, math.pi, max(3, int(7*scale)))
        pygame.draw.line(screen, (35, 65, 145), (center_x, head_center[1]-head_r+2), (center_x+int(
            18*scale), head_center[1]-head_r+int(4*scale)), max(2, int(5*scale)))
    elif head == "Helmet":
        pygame.draw.arc(screen, (100, 115, 135), (center_x-head_r,
                        head_center[1]-head_r, head_r*2, head_r*2), math.pi, 2*math.pi, max(3, int(7*scale)))
    elif head == "Headphones":
        pygame.draw.arc(screen, (30, 35, 45), (center_x-head_r-int(4*scale), head_center[1]-head_r-int(
            3*scale), 2*head_r+int(8*scale), 2*head_r), math.pi, 2*math.pi, max(2, int(4*scale)))
        pygame.draw.circle(screen, (60, 170, 230), (center_x -
                           head_r, head_center[1]), max(2, int(5*scale)))
        pygame.draw.circle(screen, (60, 170, 230), (center_x +
                           head_r, head_center[1]), max(2, int(5*scale)))
    elif head == "Beanie":
        pygame.draw.arc(screen, (180, 55, 65), (center_x-head_r,
                        head_center[1]-head_r, head_r*2, head_r), 0, math.pi, max(3, int(8*scale)))
    elif head == "Crown":
        pygame.draw.polygon(screen, (245, 195, 45), [(center_x-head_r, head_center[1]-head_r+4), (center_x-int(10*scale), head_center[1]-head_r-int(
            10*scale)), (center_x, head_center[1]-head_r+2), (center_x+int(10*scale), head_center[1]-head_r-int(10*scale)), (center_x+head_r, head_center[1]-head_r+4)])
    elif head == "Antenna":
        pygame.draw.line(screen, (190, 200, 215), (center_x, head_center[1]-head_r), (
            center_x, head_center[1]-head_r-int(13*scale)), max(1, int(2*scale)))
        pygame.draw.circle(screen, (60, 230, 245), (center_x,
                           head_center[1]-head_r-int(14*scale)), max(2, int(4*scale)))


def draw_lobby_avatar(center_x, center_y, color, scale=1.0):
    draw_custom_character(center_x, center_y, color, scale)


def draw_custom_weapon(start, end, weapon_index=None):
    """Draw a distinct, readable silhouette for each weapon."""
    if weapon_index is None:
        weapon_index = selected_weapon
    weapon_index = max(0, min(weapon_index, len(WEAPONS) - 1))

    design = CUSTOM_OPTIONS["WEAPON"][custom_selected["WEAPON"]]
    colors = {
        "Steel": (105, 115, 130), "Crimson": (190, 40, 50),
        "Neon": (30, 225, 205), "Gold": (220, 170, 45),
        "Purple": (135, 70, 205), "Arctic": (155, 220, 245),
        "Lava": (230, 85, 30), "Carbon": (35, 40, 48),
        "Forest": (55, 125, 65)
    }
    body = colors[design]
    dark = (28, 32, 40)
    metal = (185, 195, 205)

    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    def point(along, across=0):
        return (int(start[0] + ux * along + px * across),
                int(start[1] + uy * along + py * across))

    # Rear stock / grip / receiver proportions vary by weapon class.
    if weapon_index == 0:  # Pistol
        pygame.draw.polygon(screen, dark, [point(
            7, -4), point(24, -4), point(29, 5), point(17, 8), point(11, 4)])
        pygame.draw.polygon(screen, body, [point(
            3, -5), point(29, -5), point(36, -2), point(36, 3), point(3, 3)])
        pygame.draw.polygon(screen, dark, [point(18, 2), point(
            25, 2), point(22, 13), point(15, 12)])
        pygame.draw.line(screen, metal, point(9, -6), point(28, -6), 2)
    elif weapon_index == 1:  # Assault rifle
        pygame.draw.polygon(
            screen, dark, [point(-5, -5), point(10, -5), point(15, 5), point(-4, 5)])
        pygame.draw.polygon(screen, body, [point(
            5, -6), point(34, -6), point(39, 5), point(7, 5)])
        pygame.draw.polygon(screen, dark, [point(18, 4), point(
            25, 4), point(22, 15), point(15, 13)])
        pygame.draw.line(screen, metal, point(31, -2), point(48, -2), 3)
        pygame.draw.line(screen, dark, point(8, -8), point(26, -8), 2)
    elif weapon_index == 2:  # Shotgun
        pygame.draw.polygon(
            screen, dark, [point(-7, -5), point(12, -5), point(16, 5), point(-7, 5)])
        pygame.draw.polygon(screen, body, [point(
            7, -7), point(27, -7), point(31, 6), point(7, 6)])
        pygame.draw.line(screen, metal, point(25, -4), point(53, -4), 5)
        pygame.draw.line(screen, dark, point(25, 1), point(53, 1), 2)
        pygame.draw.polygon(screen, dark, [point(17, 5), point(
            24, 5), point(21, 14), point(15, 13)])
    elif weapon_index == 3:  # SMG
        pygame.draw.polygon(screen, dark, [point(
            1, -5), point(11, -5), point(15, 4), point(1, 4)])
        pygame.draw.polygon(screen, body, [point(
            5, -6), point(29, -6), point(33, 5), point(5, 5)])
        pygame.draw.line(screen, metal, point(27, -2), point(44, -2), 3)
        pygame.draw.polygon(screen, dark, [point(14, 4), point(
            21, 4), point(18, 15), point(12, 13)])
        pygame.draw.line(screen, metal, point(9, 6), point(24, 6), 2)
    elif weapon_index == 4:  # Hunting rifle
        pygame.draw.polygon(
            screen, dark, [point(-9, -4), point(12, -4), point(18, 4), point(-9, 4)])
        pygame.draw.polygon(screen, body, [point(
            8, -5), point(31, -5), point(34, 4), point(8, 4)])
        pygame.draw.line(screen, metal, point(28, -3), point(60, -3), 3)
        pygame.draw.line(screen, dark, point(14, -9), point(25, -9), 3)
        pygame.draw.circle(screen, metal, point(20, -9), 3)
        pygame.draw.polygon(screen, dark, [point(16, 4), point(
            22, 4), point(19, 12), point(14, 11)])
    elif weapon_index == 5:  # Burst rifle
        pygame.draw.polygon(
            screen, dark, [point(-5, -5), point(10, -5), point(15, 5), point(-5, 5)])
        pygame.draw.polygon(screen, body, [point(
            5, -7), point(33, -7), point(38, 5), point(6, 5)])
        pygame.draw.line(screen, metal, point(33, -2), point(53, -2), 4)
        pygame.draw.polygon(screen, dark, [point(18, 5), point(
            25, 5), point(22, 14), point(16, 13)])
        pygame.draw.line(screen, metal, point(13, -9), point(27, -9), 2)
    elif weapon_index == 6:  # Tactical rifle
        pygame.draw.polygon(screen, dark, [point(-5, -5), point(12, -5),
                                           point(16, 5), point(-5, 5)])
        pygame.draw.polygon(screen, body, [point(5, -7), point(36, -7),
                                           point(40, 5), point(6, 5)])
        pygame.draw.line(screen, metal, point(35, -3), point(56, -3), 3)
        pygame.draw.rect(screen, dark, (*point(17, 4), 7, 10))
        pygame.draw.line(screen, metal, point(15, -10), point(29, -10), 2)
    else:  # Marksman rifle
        pygame.draw.polygon(screen, dark, [point(-10, -4), point(12, -4),
                                           point(17, 5), point(-10, 5)])
        pygame.draw.polygon(screen, body, [point(8, -5), point(34, -5),
                                           point(38, 4), point(8, 4)])
        pygame.draw.line(screen, metal, point(32, -3), point(66, -3), 3)
        pygame.draw.line(screen, dark, point(16, -10), point(31, -10), 4)
        pygame.draw.circle(screen, metal, point(23, -10), 3)

    # Small sight and muzzle make the direction immediately clear.
    pygame.draw.circle(screen, dark, point(8, -7), 2)
    pygame.draw.circle(screen, metal, point(length * 0.92), 2)


def draw_lobby_panel(rect, title):
    # Clean light panels inspired by the new BUNKERDAY menu mockup.
    pygame.draw.rect(screen, (239, 239, 239), rect, border_radius=42)
    pygame.draw.rect(screen, (92, 101, 116), rect, 2, border_radius=42)
    draw_text(title, rect.x + 18, rect.y + 14, (27, 48, 78), font)


def draw_lobby():
    # Bright blue background and spacious three-panel layout.
    screen.fill((59, 119, 211))

    # Large title sits beside the compact navigation, like the reference.
    title = big_font.render("BUNKERDAY", True, WHITE)
    screen.blit(title, (330, 18))

    # Top-right navigation: feedback above Settings / Quests / Shop.
    nav_items = (
        (MENU_FEEDBACK_BUTTON, 'Bugs and Suggestions', (12, 55, 105)),
        (LOCKER_BUTTON, 'Locker', (12, 75, 125)),
        (MENU_SETTINGS_BUTTON, 'Settings', (12, 55, 105)),
        (QUEST_BUTTON, 'Quests', (12, 55, 105)),
        (SHOP_BUTTON, 'Shop', (12, 55, 105)),
    )
    for rect, label, color in nav_items:
        pygame.draw.rect(screen, color, rect, border_radius=2)
        rendered = small_font.render(label, True, WHITE)
        screen.blit(rendered, rendered.get_rect(center=rect.center))

    # Three rounded light-gray panels form the main menu structure.
    left_panel = pygame.Rect(25, 105, 350, 535)
    middle_panel = pygame.Rect(395, 135, 430, 505)
    right_panel = pygame.Rect(845, 120, 330, 520)
    draw_lobby_panel(left_panel, "CHARACTER")
    draw_lobby_panel(middle_panel, "GAME MODE")
    draw_lobby_panel(right_panel, "SOCIAL")

    # Character preview only: all appearance controls now live in the Locker.
    skin_name, skin_color = LOBBY_SKINS[selected_skin]
    preview_rect = pygame.Rect(48, 165, 304, 225)
    pygame.draw.rect(screen, (21, 31, 49), preview_rect, border_radius=12)
    pygame.draw.rect(screen, (70, 88, 120), preview_rect, 2, border_radius=12)
    draw_lobby_avatar(200, 260, skin_color, 1.25)
    draw_custom_weapon((270, 285), (315, 270), selected_weapon)
    draw_text(skin_name + " OUTFIT", 142, 350, YELLOW, small_font)
    draw_text("CHANGE YOUR LOOK IN THE LOCKER", 58, 420,
              (35, 55, 85), small_font)
    locker_hint = pygame.Rect(75, 455, 250, 58)
    pygame.draw.rect(screen, (35, 85, 135), locker_hint, border_radius=10)
    pygame.draw.rect(screen, (210, 225, 245), locker_hint, 2, border_radius=10)
    hint_text = font.render("OPEN LOCKER", True, WHITE)
    screen.blit(hint_text, hint_text.get_rect(center=locker_hint.center))
    draw_text("Outfits • Back Bling • Pickaxes • More", 53, 535,
              (35, 55, 85), small_font)

    # Game mode choices.
    descriptions = {
        "Battle Royale": "20 bots  |  Be the last player standing",
        "Bot Deathmatch": "10 bots  |  First to 10 eliminations",
        "Practice": "No bots  |  Test weapons and movement",
        "Creative": "No bots  |  Free build with unlimited materials"
    }
    for mode, rect in MODE_BUTTONS.items():
        selected = mode == selected_mode
        fill = (42, 105, 170) if selected else (47, 61, 85)
        pygame.draw.rect(screen, fill, rect, border_radius=10)
        pygame.draw.rect(screen, YELLOW if selected else (110, 130, 160),
                         rect, 3 if selected else 1, border_radius=10)
        label = font.render(mode.upper(), True, WHITE)
        screen.blit(label, (rect.x + 16, rect.y + 8))
        detail = small_font.render(descriptions[mode], True, (205, 215, 230))
        screen.blit(detail, (rect.x + 16, rect.y + 36))

    # Create/join controls.
    for rect, label, color in (
        (CREATE_LOBBY_BUTTON, "CREATE PARTY", (35, 135, 85)),
        (JOIN_LOBBY_BUTTON, "JOIN BY CODE", (65, 100, 175)),
        (INVITE_BUTTON, "INVITE FRIENDS", (125, 85, 165)),
    ):
        pygame.draw.rect(screen, color, rect, border_radius=9)
        pygame.draw.rect(screen, (220, 230, 245), rect, 2, border_radius=9)
        txt = small_font.render(label, True, WHITE)
        screen.blit(txt, txt.get_rect(center=rect.center))

    # Social panel.
    draw_text("FRIENDS", 875, 153, (35, 55, 85), small_font)
    if adding_friend:
        pygame.draw.rect(screen, (19, 29, 46),
                         FRIEND_INPUT_RECT, border_radius=8)
        pygame.draw.rect(screen, YELLOW, FRIEND_INPUT_RECT, 2, border_radius=8)
        value = friend_input_text if friend_input_text else "Type username..."
        draw_text(value, FRIEND_INPUT_RECT.x + 12, FRIEND_INPUT_RECT.y + 12,
                  WHITE if friend_input_text else (145, 160, 180), small_font)
    else:
        pygame.draw.rect(screen, (55, 105, 165),
                         FRIEND_ADD_BUTTON, border_radius=8)
        pygame.draw.rect(screen, WHITE, FRIEND_ADD_BUTTON, 1, border_radius=8)
        add_label = small_font.render("+ ADD FRIEND", True, WHITE)
        screen.blit(add_label, add_label.get_rect(
            center=FRIEND_ADD_BUTTON.center))

    if not friend_list:
        draw_text("No friends added yet.", 875, 250, (55, 65, 80), small_font)
        draw_text("Add a username to create a local", 875, 276,
                  (85, 95, 110), small_font)
        draw_text("friends-list preview.", 875, 298, (85, 95, 110), small_font)
    else:
        for i, friend in enumerate(friend_list[:5]):
            rect = FRIEND_ROW_RECTS[i]
            pygame.draw.rect(screen, (42, 55, 77), rect, border_radius=8)
            pygame.draw.circle(screen, (125, 135, 150),
                               (rect.x + 20, rect.centery), 7)
            draw_text(friend, rect.x + 36, rect.y + 7, WHITE, small_font)
            draw_text("OFFLINE*", rect.x + 36, rect.y + 27,
                      (165, 175, 190), small_font)
            invite_rect = pygame.Rect(rect.right - 148, rect.y + 7, 64, 34)
            remove_rect = pygame.Rect(rect.right - 78, rect.y + 7, 68, 34)
            pygame.draw.rect(screen, (105, 75, 155),
                             invite_rect, border_radius=6)
            invite_label = small_font.render("INVITE", True, WHITE)
            screen.blit(invite_label, invite_label.get_rect(
                center=invite_rect.center))
            pygame.draw.rect(screen, (165, 65, 70),
                             remove_rect, border_radius=6)
            remove_label = small_font.render("REMOVE", True, WHITE)
            screen.blit(remove_label, remove_label.get_rect(
                center=remove_rect.center))

    party_rect = pygame.Rect(875, 515, 270, 38)
    pygame.draw.rect(screen, (25, 37, 56), party_rect, border_radius=8)
    draw_text("PARTY: YOU  |  1/4 PLAYERS", 887, 526, WHITE, small_font)

    pygame.draw.rect(screen, (35, 165, 95), START_BUTTON, border_radius=12)
    pygame.draw.rect(screen, WHITE, START_BUTTON, 2, border_radius=12)
    play_label = font.render("PLAY", True, WHITE)
    screen.blit(play_label, play_label.get_rect(center=START_BUTTON.center))

    if joining_lobby:
        message = "ENTER CODE: " + join_code_input + "  (ENTER TO SUBMIT)"
    elif adding_friend:
        message = "Type a username and press ENTER. ESC cancels."
    elif lobby_code:
        message = "PARTY CODE: " + lobby_code + "  |  " + lobby_message
    else:
        message = lobby_message
    status = small_font.render(message[:100], True, WHITE)
    screen.blit(status, status.get_rect(center=(WIDTH // 2, 655)))
    note = small_font.render(
        "*Offline is a demo status. Real online presence and invites need the server connection.",
        True, (220, 230, 245)
    )
    screen.blit(note, note.get_rect(center=(WIDTH // 2, 680)))


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
                platform.left <= new_rect.right
                and platform.right >= new_rect.left
                and abs(platform.top - new_rect.bottom) <= 2
            ):
                has_support = True
                break

        if not has_support:
            for build in placed_builds:
                rect = build['rect']

                if (
                    rect.left <= new_rect.right
                    and rect.right >= new_rect.left
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

    if game_mode != 'Creative':
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

    # Trees can also be harvested with the pickaxe for building materials.
    for tree_index, (tree_x, tree_y, tree_size) in enumerate(TREE_POSITIONS):
        tree_hitbox = pygame.Rect(tree_x - tree_size, tree_y - tree_size * 2,
                                  tree_size * 2, tree_size * 2 + 35)
        if tree_hitbox.collidepoint(world_mouse):
            TREE_POSITIONS.pop(tree_index)
            gained = min(20, 500 - materials)
            materials += gained
            break_message = f'TREE HARVESTED: +{gained} MATERIALS'
            break_message_timer = 90
            return

    break_message = 'SWING PICKAXE AT A TREE, HOUSE OR BUILD'
    break_message_timer = 90


def binding_label(action):
    parts = []
    mods = action_mods.get(action, 0)
    if mods & pygame.KMOD_CTRL:
        parts.append('CTRL')
    if mods & pygame.KMOD_SHIFT:
        parts.append('SHIFT')
    if mods & pygame.KMOD_ALT:
        parts.append('ALT')
    mouse_button = action_mouse.get(action)
    if mouse_button is not None:
        name = {1: 'MOUSE 1', 2: 'MOUSE 2', 3: 'MOUSE 3',
                4: 'MOUSE 4', 5: 'MOUSE 5'}.get(mouse_button, f'MOUSE {mouse_button}')
    else:
        key = keybinds.get(action)
        name = pygame.key.name(key).upper() if key is not None else 'UNBOUND'
    parts.append(name)
    return ' + '.join(parts)


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
    global settings_open, waiting_for_key, settings_message, settings_scroll
    global game_won, match_end_timer, jump_buffer, selected_weapon
    global break_mode, build_mode, build_type, editing
    global velocity_x, velocity_y, player_x, player_y, movement_velocity
    global player_facing, on_ground, coyote_timer, camera_x, player_walk_phase
    global shoot_cooldown, targets, bullets, health, shield
    global game_started, selected_mode, game_mode, eliminations
    global bot_health, bot_shoot_cooldowns, bot_respawn_timers, enemy_bullets
    global bot_ammo, bot_reserve_ammo, bot_reload_timers
    global selected_skin, lobby_code, joining_lobby, join_code_input
    global lobby_message, pending_player_shot
    global adding_friend, friend_input_text
    global vehicle_active, vehicles, challenge_complete, materials
    global shop_open, locker_open, locker_category, locker_selected_index, shop_page
    global quests_open, full_map_open, coins, owned_cosmetics, equipped_locker_items
    running = True

    while running:
        # Yield control so the browser can process events and render each frame.
        await asyncio.sleep(0)
        # Keep frame timing bounded if the browser briefly stalls.
        dt = min(clock.tick(FPS) / 16.67, 3.0)

        if break_message_timer > 0:
            break_message_timer -= 1

        for effect in elimination_effects[:]:
            effect['timer'] -= dt
            if effect['timer'] <= 0:
                elimination_effects.remove(effect)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            # Result-page buttons must be handled before the elimination screen's
            # early-render branch, so Continue reliably dismisses either result.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and game_started and (health <= 0 or game_won)):
                if RESULT_CONTINUE_BUTTON.collidepoint(event.pos):
                    continue_to_lobby()
                elif RESULT_FEEDBACK_BUTTON.collidepoint(event.pos):
                    open_feedback_page()
                continue

            # Give the Settings button priority over every gameplay mouse binding.
            # This also lets it open/close reliably regardless of the selected controls.
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and game_started and not full_map_open
                    and settings_button.collidepoint(event.pos)):
                if settings_open:
                    settings_open = False
                    waiting_for_key = None
                else:
                    settings_open = True
                    waiting_for_key = None
                    settings_scroll = 0
                    settings_message = 'Bind keyboard or mouse; choose Tap, Hold, or Double.'
                continue

            if game_started and full_map_open and event.type in (
                    pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
                continue

            if not game_started:
                if event.type == pygame.KEYDOWN and (shop_open or quests_open or locker_open):
                    if event.key == pygame.K_ESCAPE:
                        shop_open = False
                        quests_open = False
                        locker_open = False
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if MENU_FEEDBACK_BUTTON.collidepoint(event.pos):
                        open_feedback_page()
                        continue
                    if MENU_SETTINGS_BUTTON.collidepoint(event.pos):
                        lobby_message = 'Settings: open a match and press the Settings button to customize controls.'
                        continue
                    if locker_open:
                        if LOCKER_CLOSE_BUTTON.collidepoint(event.pos):
                            locker_open = False
                            continue
                        for tab_name, tab_rect in LOCKER_TAB_RECTS.items():
                            if tab_rect.collidepoint(event.pos):
                                locker_category = tab_name
                                locker_selected_index = 0
                                break
                        else:
                            if locker_category == 'Outfits':
                                for skin_index in range(len(LOBBY_SKINS)):
                                    skin_rect = pygame.Rect(155 + skin_index * 96, 520, 88, 27)
                                    if skin_rect.collidepoint(event.pos):
                                        selected_skin = skin_index
                                        save_profile()
                                        lobby_message = LOBBY_SKINS[skin_index][0] + ' style selected.'
                                        break
                                else:
                                    skin_index = None
                                if skin_index is not None and skin_rect.collidepoint(event.pos):
                                    continue
                            locker_items = get_locker_items(locker_category)
                            locker_rects = get_locker_item_rects(locker_items)
                            clicked_item = False
                            for locker_index, item_rect in enumerate(locker_rects):
                                if item_rect.collidepoint(event.pos):
                                    locker_selected_index = locker_index
                                    clicked_item = True
                                    break
                            if not clicked_item and LOCKER_EQUIP_BUTTON.collidepoint(event.pos):
                                if locker_items:
                                    locker_selected_index = min(
                                        locker_selected_index, len(locker_items) - 1)
                                    lobby_message = equip_locker_item(
                                        locker_items[locker_selected_index])
                        continue
                    if LOCKER_BUTTON.collidepoint(event.pos) or (
                            pygame.Rect(75, 455, 250, 58).collidepoint(event.pos)):
                        locker_open = True
                        shop_open = False
                        quests_open = False
                        locker_category = 'Outfits'
                        locker_selected_index = 0
                        continue
                    if shop_open:
                        total_shop_pages = max(
                            1, (len(get_available_shop_items()) + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE)
                        if SHOP_PREV_BUTTON.collidepoint(event.pos):
                            shop_page = max(0, shop_page - 1)
                            continue
                        if SHOP_NEXT_BUTTON.collidepoint(event.pos):
                            shop_page = min(
                                total_shop_pages - 1, shop_page + 1)
                            continue
                        available_items = get_shop_page_items()
                        available_rects = get_shop_item_rects()
                        for shop_index, item_rect in enumerate(available_rects):
                            if item_rect.collidepoint(event.pos):
                                item = available_items[shop_index]
                                if coins >= item['price']:
                                    coins -= item['price']
                                    owned_cosmetics.add(item['name'])
                                    category = item['category']
                                    if category in CUSTOM_OPTIONS and item.get('option') in CUSTOM_OPTIONS[category]:
                                        custom_selected[category] = CUSTOM_OPTIONS[category].index(
                                            item['option'])
                                    equipped_locker_items[category] = item['name']
                                    lobby_message = item['name'] + \
                                        ' purchased and equipped!'
                                    save_profile()
                                    total_shop_pages = max(
                                        1, (len(get_available_shop_items()) + SHOP_PAGE_SIZE - 1) // SHOP_PAGE_SIZE)
                                    shop_page = min(
                                        shop_page, total_shop_pages - 1)
                                    shop_item_rects = get_shop_item_rects()
                                else:
                                    lobby_message = 'Not enough coins for ' + \
                                        item['name'] + '.'
                                break
                        continue
                    if quests_open:
                        quests_open = False
                        continue
                    if SHOP_BUTTON.collidepoint(event.pos):
                        shop_open = True
                        shop_page = 0
                        quests_open = False
                        continue
                    if QUEST_BUTTON.collidepoint(event.pos):
                        quests_open = True
                        shop_open = False
                        continue

                if event.type == pygame.KEYDOWN:
                    if adding_friend:
                        if event.key == pygame.K_ESCAPE:
                            adding_friend = False
                            friend_input_text = ''
                        elif event.key == pygame.K_BACKSPACE:
                            friend_input_text = friend_input_text[:-1]
                        elif event.key == pygame.K_RETURN:
                            cleaned = friend_input_text.strip()
                            if cleaned and cleaned.lower() not in [n.lower() for n in friend_list]:
                                if len(friend_list) < 5:
                                    friend_list.append(cleaned[:18])
                                    lobby_message = cleaned[:18] + \
                                        ' added to your local friends list.'
                                else:
                                    lobby_message = 'Friends list is full in this preview.'
                            elif cleaned:
                                lobby_message = 'That friend is already on your list.'
                            else:
                                lobby_message = 'Enter a username first.'
                            adding_friend = False
                            friend_input_text = ''
                        else:
                            if event.unicode.isprintable() and len(friend_input_text) < 18:
                                friend_input_text += event.unicode
                    elif joining_lobby:
                        if event.key == pygame.K_ESCAPE:
                            joining_lobby = False
                            join_code_input = ''
                        elif event.key == pygame.K_BACKSPACE:
                            join_code_input = join_code_input[:-1]
                        elif event.key == pygame.K_RETURN:
                            if len(join_code_input) == 6:
                                lobby_message = (
                                    'Code entered: ' + join_code_input +
                                    ' (online joining will be added with server support).'
                                )
                            else:
                                lobby_message = 'Please enter all 6 characters.'
                            joining_lobby = False
                        else:
                            typed = event.unicode.upper()
                            if typed.isalnum() and len(join_code_input) < 6:
                                join_code_input += typed
                    else:
                        if event.key == pygame.K_1:
                            selected_mode = 'Battle Royale'
                        elif event.key == pygame.K_2:
                            selected_mode = 'Bot Deathmatch'
                        elif event.key == pygame.K_3:
                            selected_mode = 'Practice'
                        elif event.key == pygame.K_4:
                            selected_mode = 'Creative'
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            start_match(selected_mode)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if adding_friend:
                        pass
                    else:
                        for mode, mode_rect in MODE_BUTTONS.items():
                            if mode_rect.collidepoint(event.pos):
                                selected_mode = mode

                        if CREATE_LOBBY_BUTTON.collidepoint(event.pos):
                            lobby_code = create_lobby_code()
                            lobby_message = 'Party created. Your local party code is ready.'
                        elif JOIN_LOBBY_BUTTON.collidepoint(event.pos):
                            joining_lobby = True
                            join_code_input = ''
                        elif INVITE_BUTTON.collidepoint(event.pos):
                            if not lobby_code:
                                lobby_code = create_lobby_code()
                            lobby_message = 'Party code ready to share: ' + lobby_code
                        elif FRIEND_ADD_BUTTON.collidepoint(event.pos):
                            adding_friend = True
                            friend_input_text = ''
                        elif any(
                            rect.collidepoint(event.pos)
                            for rect in FRIEND_ROW_RECTS[:len(friend_list)]
                        ):
                            row_index = next(
                                i for i, rect in enumerate(FRIEND_ROW_RECTS[:len(friend_list)])
                                if rect.collidepoint(event.pos)
                            )
                            row_rect = FRIEND_ROW_RECTS[row_index]
                            invite_rect = pygame.Rect(
                                row_rect.right - 148, row_rect.y + 7, 64, 34
                            )
                            remove_rect = pygame.Rect(
                                row_rect.right - 78, row_rect.y + 7, 68, 34
                            )
                            if invite_rect.collidepoint(event.pos):
                                if not lobby_code:
                                    lobby_code = create_lobby_code()
                                lobby_message = (
                                    'Local invite prepared for ' + friend_list[row_index] +
                                    '. It has not been sent online.'
                                )
                            elif remove_rect.collidepoint(event.pos):
                                removed_friend = friend_list.pop(row_index)
                                lobby_message = removed_friend + ' was removed from your friends list.'
                        elif START_BUTTON.collidepoint(event.pos):
                            start_match(selected_mode)
                continue

            if event.type == pygame.KEYDOWN:

                if settings_open:
                    if waiting_for_key is not None:
                        if event.key == pygame.K_ESCAPE:
                            waiting_for_key = None
                            settings_message = 'Rebinding cancelled.'
                        elif event.key == pygame.K_BACKSPACE:
                            keybinds[waiting_for_key] = None
                            action_mouse[waiting_for_key] = None
                            action_mods[waiting_for_key] = 0
                            settings_message = f'{waiting_for_key} unbound.'
                            save_keybinds()
                            waiting_for_key = None
                        else:
                            keybinds[waiting_for_key] = event.key
                            action_mouse[waiting_for_key] = None
                            action_mods[waiting_for_key] = event.mod & (
                                pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_ALT)
                            settings_message = f'{waiting_for_key} saved!'
                            save_keybinds()
                            waiting_for_key = None
                    elif event.key == pygame.K_ESCAPE:
                        settings_open = False
                    continue

                if full_map_open:
                    if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                        full_map_open = False
                    continue
                if event.key == pygame.K_TAB:
                    full_map_open = True
                    continue

                if game_won:
                    continue

                # P equips/toggles the pickaxe tool for harvesting.
                if event.key == pygame.K_p and not editing:
                    break_mode = not break_mode
                    build_mode = False
                    if break_mode:
                        vehicle_active = False
                    continue

                # V enters/exits a nearby drivable car.
                if event.key == pygame.K_v and not editing:
                    if vehicle_active:
                        vehicle_active = False
                        for car in vehicles:
                            if car['occupied']:
                                car['occupied'] = False
                                car['rect'].centerx = player.centerx
                                break
                    else:
                        nearby_vehicle = next(
                            (car for car in vehicles
                             if not car['occupied']
                             and abs(car['rect'].centerx - player.centerx) < 105),
                            None
                        )
                        if nearby_vehicle is not None:
                            nearby_vehicle['occupied'] = True
                            vehicle_active = True
                            build_mode = False
                            break_mode = False
                            player.centerx = nearby_vehicle['rect'].centerx
                            player_x = float(player.x)
                    continue

                if editing:
                    if action_matches_key('Confirm edit', event):
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

                if not getattr(event, 'repeat', False):
                    for action in keybinds:
                        if action_matches_key(action, event):
                            begin_bound_action(action)

                    # Keep jumping responsive even if an old saved control mode
                    # was set to Double or a stale binding state was left behind.
                    if (keybinds.get('Jump') is not None
                            and event.key == keybinds.get('Jump')
                            and action_mouse.get('Jump') is None):
                        jump_buffer = JUMP_BUFFER_TIME

                if event.key == pygame.K_ESCAPE:
                    build_mode = False
                    break_mode = False

            if event.type == pygame.KEYUP and not settings_open:
                for action in keybinds:
                    if keybinds.get(action) == event.key and action_mouse.get(action) is None:
                        end_bound_action(action)

            if event.type == pygame.MOUSEBUTTONUP and not settings_open:
                for action in keybinds:
                    if action_mouse.get(action) == event.button:
                        end_bound_action(action)

            if event.type == pygame.MOUSEWHEEL:
                if settings_open:
                    settings_view_height = 465
                    settings_content_height = len(keybinds) * 38
                    settings_max_scroll = max(
                        0, settings_content_height - settings_view_height
                    )
                    settings_scroll = max(
                        0, min(settings_max_scroll,
                               settings_scroll - event.y * 42)
                    )
                elif game_started and event.y > 0:
                    current_slot = weapon_inventory.index(selected_weapon)
                    select_weapon_slot((current_slot - 1) %
                                       len(weapon_inventory))
                elif game_started and event.y < 0:
                    current_slot = weapon_inventory.index(selected_weapon)
                    select_weapon_slot((current_slot + 1) %
                                       len(weapon_inventory))

            mouse_action_consumed = False
            if (event.type == pygame.MOUSEBUTTONDOWN and not settings_open
                    and not settings_button.collidepoint(event.pos)
                    and not ((game_mode in ('Practice', 'Creative') and practice_exit_button.collidepoint(event.pos)) or (game_mode in ('Battle Royale', 'Bot Deathmatch') and leave_game_button.collidepoint(event.pos)))
                    # Left-click belongs to the active build/edit/break tool,
                    # not the default left-mouse Fire weapon binding.
                    and not (event.button == 1 and game_started
                             and (break_mode or build_mode or editing))):
                for action in keybinds:
                    if action_matches_mouse(action, event):
                        begin_bound_action(action)
                        mouse_action_consumed = True

            if event.type == pygame.MOUSEBUTTONDOWN and settings_open and waiting_for_key is not None:
                action_mouse[waiting_for_key] = event.button
                keybinds[waiting_for_key] = None
                action_mods[waiting_for_key] = pygame.key.get_mods() & (
                    pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_ALT)
                settings_message = f'{waiting_for_key} set to mouse button {event.button}.'
                save_keybinds()
                waiting_for_key = None
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not mouse_action_consumed:

                if settings_open:
                    if settings_button.collidepoint(event.pos):
                        settings_open = False
                    else:
                        settings_viewport = pygame.Rect(310, 115, 580, 465)
                        if settings_viewport.collidepoint(event.pos):
                            for index, action in enumerate(keybinds):
                                row = pygame.Rect(
                                    325,
                                    120 + index * 38 - settings_scroll,
                                    550,
                                    34
                                )

                                if row.colliderect(settings_viewport) and row.collidepoint(event.pos):
                                    mode_rect = pygame.Rect(
                                        row.right - 112, row.y + 3, 104, 28)
                                    if mode_rect.collidepoint(event.pos):
                                        modes = ('Tap', 'Hold', 'Double')
                                        action_modes[action] = modes[(modes.index(
                                            action_modes[action]) + 1) % len(modes)]
                                        settings_message = f'{action}: {action_modes[action]} press.'
                                        save_keybinds()
                                    else:
                                        waiting_for_key = action
                                        settings_message = f'Press a keyboard key or mouse button for {action}...'
                                    break

                elif game_won:
                    pass

                elif (game_mode in ('Battle Royale', 'Bot Deathmatch')
                      and leave_game_button.collidepoint(event.pos)):
                    leave_match()
                    waiting_for_key = None

                elif (game_mode in ('Practice', 'Creative')
                      and practice_exit_button.collidepoint(event.pos)):
                    complete_match_rewards()
                    game_started = False
                    game_won = False
                    match_end_timer = 0.0
                    settings_open = False
                    waiting_for_key = None
                    pending_player_shot = False
                    build_mode = False
                    break_mode = False
                    cancel_edit()
                    bullets.clear()
                    enemy_bullets.clear()
                    lobby_message = f'You left {game_mode} Mode. Choose another mode!'

                elif settings_button.collidepoint(event.pos):
                    pass  # Handled at the top of the event loop.

                elif editing:
                    if toggle_edit_section():
                        confirm_edit()

                elif build_mode:
                    place_build()

                elif break_mode:
                    break_build_at_mouse()

                else:
                    pass

        update_held_bindings()

        # End the match immediately when the player's health reaches zero.
        # This runs before movement, shooting, bot AI, storm damage, or loot updates.
        if game_started and health <= 0:
            draw_result_screen(victory=False)
            pygame.display.flip()
            continue

        # A queued click fires as soon as the weapon cooldown ends.
        # Holding the mouse also fires at the weapon's normal rate.
        fire_held = action_is_held('Fire weapon')
        if (
            game_started
            and not settings_open
            and not full_map_open
            and not game_won
            and not editing
            and not build_mode
            and not break_mode
            and not vehicle_active
            and (pending_player_shot or fire_held)
        ):
            if fire_player_weapon():
                pending_player_shot = False

        if not game_started:
            draw_lobby()
            if shop_open:
                draw_shop_screen()
            elif quests_open:
                draw_quests_screen()
            elif locker_open:
                draw_locker_screen()
            pygame.display.flip()
            continue

        if settings_open or full_map_open:
            dt = 0

        keys = pygame.key.get_pressed()
        mouse_x_now, _ = pygame.mouse.get_pos()

        player_facing = (
            1 if mouse_x_now + camera_x >= player.centerx else -1
        )

        desired_horizontal = 0.0

        if not editing and not settings_open and not full_map_open and not game_won:
            # Read movement directly from the configured keys.
            left_key = keybinds.get('Move left')
            right_key = keybinds.get('Move right')
            left_down = (left_key is not None and action_mouse.get('Move left') is None
                         and keys[left_key])
            right_down = (right_key is not None and action_mouse.get('Move right') is None
                          and keys[right_key])
            max_speed = vehicle_speed if vehicle_active else speed
            if left_down and not right_down:
                desired_horizontal = -max_speed
            elif right_down and not left_down:
                desired_horizontal = max_speed

        if vehicle_active:
            if desired_horizontal:
                movement_velocity += (desired_horizontal - movement_velocity) * min(1.0, 0.20 * dt)
            else:
                movement_velocity *= 0.94 ** dt
                if abs(movement_velocity) < 0.12:
                    movement_velocity = 0.0
        elif desired_horizontal:
            acceleration = GROUND_ACCELERATION if on_ground else AIR_ACCELERATION
            movement_velocity += (desired_horizontal -
                                  movement_velocity) * min(1.0, acceleration * dt)
        else:
            friction = GROUND_FRICTION if on_ground else AIR_FRICTION
            movement_velocity *= friction ** dt
            if abs(movement_velocity) < 0.08:
                movement_velocity = 0.0
        velocity_x = movement_velocity
        if abs(velocity_x) > 0.12 and not vehicle_active:
            player_walk_phase += abs(velocity_x) * 0.075 * dt

        # Horizontal movement is allowed both on the ground and in the air.
        # Only resolve a platform collision when the player actually crosses
        # its LEFT or RIGHT side. A player falling onto a platform must not be
        # pushed sideways by the horizontal collision pass.
        previous_player_left = player.left
        previous_player_right = player.right
        player_x += velocity_x * dt
        player.x = round(player_x)

        all_platforms = platforms + get_build_collision_rects()

        for platform in all_platforms:
            vertical_overlap = (
                player.bottom > platform.top
                and player.top < platform.bottom
            )
            if not vertical_overlap or not player.colliderect(platform):
                continue

            if velocity_x > 0 and previous_player_right <= platform.left:
                player.right = platform.left
                player_x = float(player.x)
            elif velocity_x < 0 and previous_player_left >= platform.right:
                player.left = platform.right
                player_x = float(player.x)

        previous_bottom = player.bottom
        previous_top = player.top
        was_on_ground = on_ground

        if vehicle_active:
            player.bottom = GROUND_Y
            player_y = float(player.y)
            velocity_y = 0
            on_ground = True
        elif not game_won:
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
                    and abs(previous_bottom - surface_y) <= 26
                )

                if crossed_surface or following_slope:
                    player.bottom = surface_y
                    player_y = float(player.y)
                    velocity_y = 0
                    on_ground = True

                # Smoothly follow the ramp when walking uphill; this prevents
                # the ramp's invisible rectangular volume acting like a wall.
                elif abs(velocity_x) > 0.1 and abs(player.bottom - surface_y) <= 22:
                    uphill_direction = 1 if build.get(
                        'orientation', 1) == 1 else -1
                    moving_uphill = velocity_x * uphill_direction > 0
                    if moving_uphill and surface_y < player.bottom:
                        player.bottom = surface_y
                        player_y = float(player.y)
                        velocity_y = 0
                        on_ground = True

        if on_ground:
            coyote_timer = COYOTE_TIME
        else:
            coyote_timer = max(0, coyote_timer - dt)

        jump_buffer = max(0, jump_buffer - dt)

        if not game_won and not vehicle_active and jump_buffer > 0 and coyote_timer > 0:
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
            # Move player bullets. Houses do not block shots; builds and platforms do.
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

                    if (bullet_hits_vehicle(check_x, check_y, 5)
                            or bullet_hits_structure(check_x, check_y, bullet[5])):
                        bullets.remove(bullet)
                        bullet_removed = True
                        break

                    hit_index = next(
                        (i for i, target in enumerate(targets)
                         if target.x >= 0 and bullet_hits_bot(
                             check_x, check_y, 5, target
                        )),
                        None
                    )

                    if hit_index is not None:
                        bot_health[hit_index] -= bullet[4]
                        if bot_health[hit_index] <= 0:
                            defeated = targets[hit_index]
                            drop_loot(defeated.centerx, defeated.centery)
                            loot_drops.append({'type': 'ammo',
                                               'rect': pygame.Rect(defeated.centerx-13, defeated.centery-10, 26, 24),
                                               'amount': random.randint(18, 36), 'rarity': 'Common',
                                               'weapon_index': random.randrange(len(WEAPONS)), 'ammo': 0})
                            eliminations += 1
                            add_coins(2, 'elimination')
                            update_quest_progress('eliminations')
                            upgraded_rarity = upgrade_selected_weapon()
                            elimination_effects.append({
                                'x': defeated.centerx, 'y': defeated.centery,
                                'timer': 42, 'label': f'ELIMINATION  |  {upgraded_rarity.upper()} UPGRADE'
                            })
                            if not challenge_complete and eliminations >= MATCH_CHALLENGE_GOAL:
                                challenge_complete = True
                                materials = min(500, materials + 75)
                            if game_mode == 'Bot Deathmatch':
                                targets[hit_index].x = -1000
                                bot_respawn_timers[hit_index] = 150
                                bot_health[hit_index] = 100
                            else:
                                targets.pop(hit_index)
                                bot_health.pop(hit_index)
                                bot_shoot_cooldowns.pop(hit_index)
                                bot_respawn_timers.pop(hit_index)
                                bot_ammo.pop(hit_index)
                                bot_reserve_ammo.pop(hit_index)
                                bot_reload_timers.pop(hit_index)
                                bot_skin_colors.pop(hit_index)
                                bot_weapon_indices.pop(hit_index)
                        bullets.remove(bullet)
                        bullet_removed = True
                        break

                if bullet_removed:
                    continue
                bullet[0], bullet[1] = new_x, new_y
                if new_x < 0 or new_x > WORLD_WIDTH or new_y < -50 or new_y > HEIGHT + 50:
                    bullets.remove(bullet)

            # Bot AI: actively pursue the player and fire frequently.
            if game_mode != 'Practice' and health > 0:
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
                            bot_shoot_cooldowns[index] = 8
                            bot_ammo[index] = BOT_MAGAZINE_SIZE
                            bot_reserve_ammo[index] = BOT_STARTING_RESERVE
                            bot_reload_timers[index] = 0.0
                            bot_skin_colors[index] = random.choice(
                                [(45, 115, 220), (220, 65, 65), (55, 165, 95), (145, 85, 210), (225, 125, 40), (35, 175, 190)])
                            bot_weapon_indices[index] = random.randrange(
                                len(WEAPONS))
                        continue

                    # Bots choose the closest opponent: another bot or the player.
                    # This makes battles happen across the map instead of every bot
                    # concentrating exclusively on the player.
                    possible_targets = []
                    player_distance = math.hypot(
                        player.centerx - bot.centerx,
                        player.centery - bot.centery
                    )
                    possible_targets.append((player_distance, None, player))
                    # In Battle Royale, bots only target the human player.
                    # This prevents bot-vs-bot eliminations and keeps the
                    # last-player-standing objective fair and predictable.
                    if game_mode != 'Battle Royale':
                        for other_index, other_bot in enumerate(targets):
                            if other_index == index or other_bot.x < 0:
                                continue
                            other_distance = math.hypot(
                                other_bot.centerx - bot.centerx,
                                other_bot.centery - bot.centery
                            )
                            possible_targets.append(
                                (other_distance, other_index, other_bot))

                    target_distance, target_index, chosen_target = min(
                        possible_targets, key=lambda item: item[0]
                    )
                    dx = chosen_target.centerx - bot.centerx
                    dy = chosen_target.centery - bot.centery

                    # Bots can pass through houses, but not through player builds
                    # or platforms. They pursue opponents more actively and close
                    # the distance before stopping to fire.
                    bot_stop_distance = 180
                    if abs(dx) > bot_stop_distance:
                        # Small personality differences make bots feel less identical.
                        move_speed = (2.0 + (index % 4) * 0.22) * dt
                        step_x = (1 if dx > 0 else -1) * \
                            min(abs(dx) - bot_stop_distance, move_speed)
                        candidate = bot.copy()
                        candidate.x += round(step_x)
                        # Houses and player-built structures are solid to bots.
                        # Check each intact build cell (including ramp sections),
                        # so bots cannot walk straight through player walls/floors.
                        blocked_by_build = False
                        for build in placed_builds:
                            for row, col, cell in get_build_cells(build):
                                if (row, col) in build['removed']:
                                    continue
                                if candidate.colliderect(cell):
                                    blocked_by_build = True
                                    break
                            if blocked_by_build:
                                break

                        blocked_by_platform = any(
                            candidate.colliderect(platform)
                            for platform in platforms
                        )

                        if (
                            candidate.left >= 0
                            and candidate.right <= WORLD_WIDTH
                            and not blocked_by_build
                            and not blocked_by_platform
                        ):
                            bot.x = candidate.x

                    # Reloading takes time and bots cannot shoot while reloading.
                    if bot_reload_timers[index] > 0:
                        bot_reload_timers[index] = max(
                            0.0, bot_reload_timers[index] - dt)
                        if bot_reload_timers[index] <= 0:
                            needed = BOT_MAGAZINE_SIZE - bot_ammo[index]
                            loaded = min(needed, bot_reserve_ammo[index])
                            bot_ammo[index] += loaded
                            bot_reserve_ammo[index] -= loaded

                    # Empty magazines trigger an automatic reload.
                    if bot_ammo[index] <= 0 and bot_reserve_ammo[index] > 0 and bot_reload_timers[index] <= 0:
                        bot_reload_timers[index] = BOT_RELOAD_TIME

                    bot_shoot_cooldowns[index] -= dt
                    if (
                        target_distance < 1800
                        and bot_shoot_cooldowns[index] <= 0
                        and bot_reload_timers[index] <= 0
                        and bot_ammo[index] > 0
                    ):
                        aim_angle = math.atan2(dy, dx)
                        # Bots lead moving targets a little, but keep imperfect aim.
                        if chosen_target is player:
                            aim_angle += (velocity_x * 0.018)
                        aim_angle += random.uniform(-0.075, 0.075)
                        bullet_speed = 14
                        enemy_bullets.append([
                            float(bot.centerx), float(bot.centery),
                            math.cos(aim_angle) * bullet_speed,
                            math.sin(aim_angle) * bullet_speed,
                            6, chosen_target if target_index is not None else None
                        ])
                        bot_ammo[index] -= 1
                        bot_shoot_cooldowns[index] = random.uniform(24, 38)

            # Enemy bullets pass through houses but are stopped by builds/platforms.
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
                    if (bullet_hits_vehicle(check_x, check_y, 6)
                            or bullet_hits_structure(check_x, check_y, 8)):
                        enemy_bullets.remove(bullet)
                        removed = True
                        break
                    hit_rect = pygame.Rect(
                        int(check_x - 5), int(check_y - 5), 10, 10)
                    bot_target = bullet[5] if len(bullet) > 5 else None
                    if bot_target is not None:
                        # Bullets from bots only damage the bot they were aimed at.
                        if bot_target in targets and bot_target.x >= 0 and hit_rect.colliderect(bot_target.inflate(26, 24)):
                            target_index = targets.index(bot_target)
                            bot_health[target_index] -= bullet[4]
                            if bot_health[target_index] <= 0:
                                defeated = targets[target_index]
                                drop_loot(defeated.centerx, defeated.centery)
                                loot_drops.append({'type': 'ammo',
                                                   'rect': pygame.Rect(defeated.centerx-13, defeated.centery-10, 26, 24),
                                                   'amount': random.randint(18, 36), 'rarity': 'Common',
                                                   'weapon_index': random.randrange(len(WEAPONS)), 'ammo': 0})
                                if game_mode == 'Bot Deathmatch':
                                    defeated.x = -1000
                                    bot_respawn_timers[target_index] = 150
                                    bot_health[target_index] = 100
                                else:
                                    targets.pop(target_index)
                                    bot_health.pop(target_index)
                                    bot_shoot_cooldowns.pop(target_index)
                                    bot_respawn_timers.pop(target_index)
                                    bot_ammo.pop(target_index)
                                    bot_reserve_ammo.pop(target_index)
                                    bot_reload_timers.pop(target_index)
                                    bot_skin_colors.pop(target_index)
                                    bot_weapon_indices.pop(target_index)
                            enemy_bullets.remove(bullet)
                            removed = True
                            break
                    elif hit_rect.colliderect(player):
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

        for i in range(16):
            hill_x = i * 500 - camera_x // 2
            pygame.draw.ellipse(
                screen,
                (95, 175, 105),
                (hill_x, 390, 600, 300)
            )

        # Distant harbor cranes add a recognizable skyline in NEON HARBOR.
        for crane_x in (5050, 5550, 6100, 6650):
            sx = crane_x - camera_x
            if -100 < sx < WIDTH + 100:
                pygame.draw.line(screen, (75, 90, 105),
                                 (sx, 360), (sx, 520), 8)
                pygame.draw.line(screen, (75, 90, 105),
                                 (sx - 65, 365), (sx + 85, 365), 7)
                pygame.draw.line(screen, (95, 110, 125),
                                 (sx + 65, 365), (sx + 65, 430), 4)
                pygame.draw.rect(screen, (175, 145, 70),
                                 (sx + 53, 430, 24, 18), border_radius=2)

        # Region ground tint, road, roadside markings, trees and location signs.
        for region_left, region_right, region_name, region_color in WORLD_REGIONS:
            left = int(region_left - camera_x)
            right = int(region_right - camera_x)
            if right >= 0 and left <= WIDTH:
                pygame.draw.rect(screen, region_color, (max(0, left), 575,
                                                        min(WIDTH, right) - max(0, left), 15))
                if left < WIDTH and right > 0:
                    sign_x = max(35, min(WIDTH - 160, (left + right) // 2))
                    sign = pygame.Rect(sign_x, 145, 155, 34)
                    pygame.draw.rect(screen, (28, 48, 55),
                                     sign, border_radius=6)
                    pygame.draw.rect(screen, (210, 220, 195),
                                     sign, 2, border_radius=6)
                    label = small_font.render(region_name, True, WHITE)
                    screen.blit(label, label.get_rect(center=sign.center))

        road_y = 552
        pygame.draw.rect(screen, (65, 68, 74), (0, road_y, WIDTH, 38))
        pygame.draw.line(screen, (235, 205, 110), (0, road_y + 19),
                         (WIDTH, road_y + 19), 3)
        for dash_x in range(-80, WIDTH + 100, 100):
            world_dash = dash_x + (camera_x % 100)
            pygame.draw.line(screen, (225, 225, 210),
                             (dash_x - (camera_x % 100), road_y + 19),
                             (dash_x - (camera_x % 100) + 42, road_y + 19), 3)

        for tree_x, tree_y, tree_size in TREE_POSITIONS:
            sx = int(tree_x - camera_x)
            if -60 < sx < WIDTH + 60:
                pygame.draw.rect(screen, (95, 65, 40),
                                 (sx - 5, tree_y, 10, 34))
                pygame.draw.circle(screen, (35, 115, 65),
                                   (sx, tree_y - 10), tree_size)
                pygame.draw.circle(screen, (55, 145, 78),
                                   (sx - tree_size // 2, tree_y - 18),
                                   max(8, tree_size // 2))

        # Snowy ridges and coastal palms distinguish the newly added regions.
        for peak_x in (14350, 14850, 15350, 15850):
            sx = peak_x - camera_x
            if -180 < sx < WIDTH + 180:
                pygame.draw.polygon(screen, (115, 145, 165),
                                    [(sx - 105, 575), (sx, 300), (sx + 115, 575)])
                pygame.draw.polygon(screen, (225, 238, 245),
                                    [(sx - 38, 395), (sx, 300), (sx + 42, 405),
                                     (sx + 10, 385), (sx - 5, 410)])
        for palm_x in (18200, 18700, 19400, 19800):
            sx = palm_x - camera_x
            if -90 < sx < WIDTH + 90:
                pygame.draw.line(screen, (105, 75, 42),
                                 (sx, 570), (sx + 8, 465), 8)
                for angle in (-2.6, -1.8, -0.8, 0.1, 0.9):
                    end = (sx + int(math.cos(angle) * 48),
                           465 + int(math.sin(angle) * 32))
                    pygame.draw.line(screen, (40, 125, 65),
                                     (sx + 8, 465), end, 7)

        # Small industrial skyline around the factory district.
        for factory_x in (7550, 7820, 8150, 8420, 8750):
            sx = factory_x - camera_x
            if -100 < sx < WIDTH + 100:
                pygame.draw.rect(screen, (90, 100, 108),
                                 (sx, 330, 72, 220))
                pygame.draw.rect(screen, (55, 65, 75),
                                 (sx + 12, 350, 48, 28))
                pygame.draw.rect(screen, (115, 120, 125),
                                 (sx + 25, 270, 22, 60))
                pygame.draw.circle(screen, (155, 165, 170),
                                   (sx + 36, 260), 12, 3)

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

        # Parked and occupied cars.
        for car in vehicles:
            if car['occupied']:
                continue
            car_rect = car['rect'].copy()
            car_screen = pygame.Rect(car_rect.x - camera_x, car_rect.y,
                                     car_rect.width, car_rect.height)
            if -120 < car_screen.x < WIDTH + 120:
                draw_car_sprite(car_screen, car['color'])
                hint = small_font.render("V: DRIVE", True, WHITE)
                screen.blit(hint, hint.get_rect(
                    midbottom=(car_screen.centerx, car_screen.top - 5)))

        for chest in chests:
            chest_rect = pygame.Rect(
                chest['rect'].x - camera_x,
                chest['rect'].y,
                chest['rect'].width,
                chest['rect'].height
            )

            rarity = chest.get('rarity', 'Common')
            chest_color = (
                105, 90, 65) if chest['opened'] else RARITIES[rarity]['color']

            pygame.draw.rect(
                screen, chest_color, chest_rect, border_radius=5
            )
            pygame.draw.rect(
                screen, (75, 50, 25), chest_rect, 3, border_radius=5
            )
            if not chest['opened']:
                rarity_label = small_font.render(
                    chest.get('rarity', 'Common').upper(), True, WHITE)
                screen.blit(rarity_label, rarity_label.get_rect(
                    midbottom=(chest_rect.centerx, chest_rect.top - 3)))
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

            if item['type'] == 'weapon':
                draw_custom_weapon((item_rect.left-8, item_rect.centery),
                                   (item_rect.right+25, item_rect.centery-3),
                                   item['weapon_index'])
                pygame.draw.circle(
                    screen, RARITIES[item['rarity']]['color'], item_rect.center, 15, 2)
            elif item['type'] == 'ammo':
                draw_ammo_icon(item_rect.center, 27)
            elif item['type'] == 'health':
                pygame.draw.rect(screen, (225, 230, 235),
                                 item_rect, border_radius=5)
                pygame.draw.rect(
                    screen, (195, 35, 45), (item_rect.centerx-4, item_rect.y+4, 8, item_rect.height-8))
                pygame.draw.rect(
                    screen, (195, 35, 45), (item_rect.x+4, item_rect.centery-4, item_rect.width-8, 8))
                pygame.draw.rect(screen, WHITE, item_rect, 2, border_radius=5)
            elif item['type'] == 'shield':
                shield_points = [(item_rect.centerx, item_rect.top), (item_rect.right, item_rect.top+6),
                                 (item_rect.right-3, item_rect.bottom -
                                  5), (item_rect.centerx, item_rect.bottom),
                                 (item_rect.left+3, item_rect.bottom-5), (item_rect.left, item_rect.top+6)]
                pygame.draw.polygon(screen, (65, 150, 255), shield_points)
                pygame.draw.polygon(screen, WHITE, shield_points, 2)
            else:
                pygame.draw.rect(screen, item_color,
                                 item_rect, border_radius=5)
                pygame.draw.rect(screen, WHITE, item_rect, 2, border_radius=5)
                symbol = small_font.render('M', True, BLACK)
                screen.blit(symbol, symbol.get_rect(center=item_rect.center))
            if item['type'] == 'weapon':
                weapon_label = small_font.render(
                    WEAPONS[item['weapon_index']]['name'],
                    True, WHITE
                )
                label_rect = weapon_label.get_rect(
                    midbottom=(item_rect.centerx, item_rect.top - 3)
                )
                screen.blit(weapon_label, label_rect)

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

        if build_mode and not editing and not game_won and not vehicle_active:
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
                'PICKAXE EQUIPPED  |  LEFT-CLICK TO HARVEST  |  P TO HOLSTER',
                WIDTH // 2 - 300, 20, YELLOW
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
            bot_color = bot_skin_colors[index] if index < len(
                bot_skin_colors) else RED
            pygame.draw.ellipse(screen, (55, 75, 70),
                                (target_draw.centerx - 17, target_draw.bottom - 3, 34, 8))
            draw_custom_character(target_draw.centerx,
                                  target_draw.centery-3, bot_color, 0.68)
            bot_weapon = bot_weapon_indices[index] if index < len(
                bot_weapon_indices) else 1
            bot_direction = 1 if player.centerx >= target.centerx else -1
            draw_custom_weapon((target_draw.centerx, target_draw.centery+4),
                               (target_draw.centerx+bot_direction *
                                38, target_draw.centery-2),
                               bot_weapon)
            if index < len(bot_reload_timers) and bot_reload_timers[index] > 0:
                reload_tag = small_font.render('RELOADING', True, YELLOW)
                screen.blit(reload_tag, reload_tag.get_rect(
                    midbottom=(target_draw.centerx, target_draw.top-5)))
            draw_health_bar(target_draw, bot_health[index])

        player_draw = pygame.Rect(
            player.x - camera_x,
            player.y,
            player.width,
            player.height
        )

        if vehicle_active:
            car_color = next((car['color'] for car in vehicles if car['occupied']),
                             (195, 55, 55))
            car_rect = pygame.Rect(player_draw.centerx - 46,
                                   player_draw.bottom - 38, 92, 34)
            draw_car_sprite(car_rect, car_color)
        else:
            pygame.draw.ellipse(screen, (55, 75, 70),
                                (player_draw.centerx - 20, player_draw.bottom - 3, 40, 9))
            draw_custom_character(
                player_draw.centerx,
                player_draw.centery - 3,
                LOBBY_SKINS[selected_skin][1],
                0.78,
                player_walk_phase,
                min(1.0, abs(velocity_x) / max(1.0, speed)),
                player_facing
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

        if break_mode:
            # Keep the equipped pickaxe visibly in the character's hand.
            pickaxe_hand = (
                player_draw.centerx + player_facing * 23,
                player_draw.centery + 8
            )
            draw_pickaxe(pickaxe_hand, player_facing, 1.28)
        else:
            draw_custom_weapon(player_draw.center, gun_end, selected_weapon)

        # Lightweight, non-graphic elimination effects.
        for effect in elimination_effects:
            progress = 1.0 - max(0.0, effect['timer']) / 42.0
            radius = int(12 + progress * 34)
            effect_x = int(effect['x'] - camera_x)
            effect_y = int(effect['y'])
            pygame.draw.circle(screen, (255, 220, 95),
                               (effect_x, effect_y), radius, 3)
            pygame.draw.circle(screen, (255, 255, 220),
                               (effect_x, effect_y), max(3, radius // 3), 2)
            if effect['timer'] > 20:
                effect_label = small_font.render('ELIMINATED!', True, YELLOW)
                screen.blit(effect_label, effect_label.get_rect(
                    midbottom=(effect_x, effect_y - radius - 8)))

        for bullet in bullets:
            bullet_x = int(bullet[0] - camera_x)
            bullet_y = int(bullet[1])
            trail_end = (int(bullet_x - bullet[2] * 2.2),
                         int(bullet_y - bullet[3] * 2.2))
            pygame.draw.line(screen, (255, 235, 145),
                             (bullet_x, bullet_y), trail_end, 3)
            pygame.draw.circle(screen, (255, 250, 205),
                               (bullet_x, bullet_y), 4)

        for bullet in enemy_bullets:
            bullet_x = int(bullet[0] - camera_x)
            bullet_y = int(bullet[1])
            trail_end = (int(bullet_x - bullet[2] * 2.0),
                         int(bullet_y - bullet[3] * 2.0))
            pygame.draw.line(screen, (190, 65, 45),
                             (bullet_x, bullet_y), trail_end, 3)
            pygame.draw.circle(screen, (255, 145, 85),
                               (bullet_x, bullet_y), 4)

        if game_mode in ('Battle Royale', 'Bot Deathmatch'):
            health_panel = pygame.Rect(20, 12, 294, 65)
            pygame.draw.rect(screen, (9, 17, 30),
                             health_panel, border_radius=10)
            pygame.draw.rect(screen, (130, 155, 190),
                             health_panel, 2, border_radius=10)
            draw_text('HEALTH', 32, 22, WHITE, small_font)
            pygame.draw.rect(screen, (48, 55, 68),
                             (112, 24, 184, 12), border_radius=5)
            pygame.draw.rect(screen, RED, (112, 24, int(
                184 * max(0, health) / 100), 12), border_radius=5)
            draw_text(str(max(0, health)), 268, 20, WHITE, small_font)
            draw_text('SHIELD', 32, 48, WHITE, small_font)
            pygame.draw.rect(screen, (48, 55, 68),
                             (112, 50, 184, 12), border_radius=5)
            pygame.draw.rect(screen, BLUE, (112, 50, int(
                184 * max(0, shield) / 100), 12), border_radius=5)
            draw_text(str(max(0, shield)), 268, 46, WHITE, small_font)
        else:
            pygame.draw.rect(screen, BLACK, (20, 20, 250, 60))
            pygame.draw.rect(
                screen, RED, (25, 25, int(220 * health / 100), 12))
            pygame.draw.rect(
                screen, BLUE, (25, 45, int(220 * shield / 100), 12))
            draw_text(f'HEALTH: {health}', 290, 15)
            draw_text(f'SHIELD: {shield}', 290, 45)

        if game_mode not in ('Battle Royale', 'Bot Deathmatch'):
            draw_text(game_mode.upper(), WIDTH //
                      2 - 70, 15, YELLOW, small_font)
        if vehicle_active:
            draw_text('DRIVING: V TO EXIT', WIDTH // 2 -
                      85, 48, (255, 225, 100), small_font)
        elif not break_mode and not game_won:
            draw_text('P: EQUIP PICKAXE', WIDTH - 190, HEIGHT - 28,
                      (235, 225, 160), small_font)

        weapon = WEAPONS[selected_weapon]
        rarity_name = weapon_rarities[selected_weapon]
        rarity_color = RARITIES[rarity_name]['color']

        if game_mode not in ('Battle Royale', 'Bot Deathmatch'):
            draw_text(
                f"{rarity_name.upper()} {weapon['name'].upper()}: "
                f"{weapon_ammo[weapon['name']]}/{weapon['capacity']}  |  "
                f"RESERVE {weapon_reserve[weapon['name']]}",
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
        elif game_mode == 'Creative':
            storm_status = 'CREATIVE MODE - FREE BUILD - UNLIMITED MATERIALS'
        else:
            storm_status = 'PRACTICE MODE - NO ENEMY BOTS'

        draw_text(storm_status, WIDTH // 2 - 160,
                  82 if game_mode not in (
                      'Battle Royale', 'Bot Deathmatch') else 178,
                  (40, 65, 150), small_font)

        nearby_item = nearest_loot()
        if nearby_item is not None:
            item_name = (WEAPONS[nearby_item['weapon_index']]['name']
                         if nearby_item['type'] == 'weapon'
                         else nearby_item['type'].upper())
            pickup_hint = f"{binding_label('Pick up loot')}: PICK UP {item_name}"
            pickup_color = YELLOW
        else:
            pickup_hint = f"{binding_label('Pick up loot')}: PICK UP LOOT"
            pickup_color = WHITE
        draw_text('F: OPEN CHEST', WIDTH // 2 - 85, 105, WHITE, small_font)
        draw_text(pickup_hint,
                  WIDTH -
                  300 if game_mode not in (
                      'Battle Royale', 'Bot Deathmatch') else WIDTH // 2 + 35,
                  105 if game_mode not in (
                      'Battle Royale', 'Bot Deathmatch') else 145,
                  pickup_color, small_font)

        if game_mode == 'Battle Royale':
            draw_text(f'BOTS LEFT: {len(targets)}',
                      WIDTH // 2 - 70, 48, WHITE, small_font)
        elif game_mode == 'Bot Deathmatch':
            draw_text(f'KILLS: {eliminations}/{DEATHMATCH_GOAL}',
                      WIDTH // 2 - 70, 48, WHITE, small_font)
        elif game_mode == 'Creative':
            draw_text('CREATIVE', WIDTH - 180, 60)
        else:
            draw_text('PRACTICE', WIDTH - 180, 60)
        if game_mode not in ('Battle Royale', 'Bot Deathmatch'):
            draw_text(f'MATERIALS: {materials}', WIDTH - 260, 100)
            draw_text(f'COINS: {coins}', WIDTH - 260, 125, YELLOW, small_font)
        if game_mode not in ('Practice', 'Creative'):
            challenge_text = ('CHALLENGE COMPLETE: +75 MATERIALS'
                              if challenge_complete
                              else f'CHALLENGE: GET {MATCH_CHALLENGE_GOAL} ELIMINATIONS ({eliminations}/{MATCH_CHALLENGE_GOAL})')
            draw_text(challenge_text, 20, 165,
                      (120, 235, 150) if challenge_complete else YELLOW,
                      small_font)

        draw_text(
            f"{binding_label('Move left')}/"
            f"{binding_label('Move right')}: MOVE   "
            f"{binding_label('Jump')}: JUMP   "
            f"MOUSE: SHOOT   "
            f"{binding_label('Reload')}: RELOAD",
            20, HEIGHT - 40, WHITE, small_font
        )

        draw_text(
            f"{binding_label('Build mode')}: BUILD   "
            f"{binding_label('Wall')}: WALL   "
            f"{binding_label('Floor')}: FLOOR   "
            f"{binding_label('Ramp')}: RAMP   {binding_label('Cycle build')}: CYCLE   "
            f"{binding_label('Edit')}: EDIT   "
            f"{binding_label('Break builds')}: BREAK",
            20, HEIGHT - 68, WHITE, small_font
        )

        draw_text(
            'P: PICKAXE   V: CAR   3/4/5: WEAPONS   X: DROP   SCROLL: SWITCH   R: RELOAD',
            20, HEIGHT - 96, WHITE, small_font
        )

        if game_mode in ('Battle Royale', 'Bot Deathmatch'):
            if not settings_open and not game_won:
                pygame.draw.rect(screen, (155, 48, 58),
                                 leave_game_button, border_radius=8)
                pygame.draw.rect(
                    screen, WHITE, leave_game_button, 2, border_radius=8)
                leave_label = small_font.render('EXIT GAME', True, WHITE)
                screen.blit(leave_label, leave_label.get_rect(
                    center=leave_game_button.center))

                pygame.draw.rect(screen, (45, 75, 112),
                                 current_mode_button, border_radius=8)
                pygame.draw.rect(
                    screen, WHITE, current_mode_button, 2, border_radius=8)
                mode_label = small_font.render(game_mode.upper(), True, WHITE)
                screen.blit(mode_label, mode_label.get_rect(
                    center=current_mode_button.center))

            pygame.draw.rect(screen, (35, 45, 65),
                             settings_button, border_radius=8)
            pygame.draw.rect(screen, WHITE, settings_button,
                             2, border_radius=8)
            label = small_font.render('SETTINGS', True, WHITE)
            screen.blit(label, label.get_rect(center=settings_button.center))
        else:
            pygame.draw.rect(screen, (35, 45, 65),
                             settings_button, border_radius=8)
            pygame.draw.rect(screen, WHITE, settings_button,
                             2, border_radius=8)
            label = font.render('SETTINGS', True, WHITE)
            screen.blit(label, label.get_rect(center=settings_button.center))

        if game_mode in ('Practice', 'Creative') and not settings_open and not game_won:
            pygame.draw.rect(
                screen, (170, 45, 45), practice_exit_button, border_radius=8
            )
            pygame.draw.rect(
                screen, WHITE, practice_exit_button, 2, border_radius=8
            )
            exit_label = font.render('EXIT MODE', True, WHITE)
            screen.blit(
                exit_label,
                exit_label.get_rect(center=practice_exit_button.center)
            )

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
                'Bind a key or mouse button. Add Shift/Ctrl/Alt; click mode for Tap/Hold/Double.',
                370, 80, WHITE, small_font
            )

            # Scrollable keybind list: rows are clipped to the viewport.
            settings_viewport = pygame.Rect(310, 115, 580, 465)
            settings_content_height = len(keybinds) * 38
            settings_max_scroll = max(
                0, settings_content_height - settings_viewport.height
            )
            settings_scroll = max(0, min(settings_max_scroll, settings_scroll))

            old_clip = screen.get_clip()
            screen.set_clip(settings_viewport)

            for index, (action, key_code) in enumerate(keybinds.items()):
                row_rect = pygame.Rect(
                    325,
                    120 + index * 38 - settings_scroll,
                    550,
                    34
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

                key_text = ('PRESS KEY / MOUSE...' if waiting_for_key == action
                            else binding_label(action))
                value = small_font.render(key_text, True, YELLOW)
                screen.blit(value, value.get_rect(
                    midleft=(row_rect.x + 175, row_rect.centery)))

                mode_rect = pygame.Rect(
                    row_rect.right - 112, row_rect.y + 3, 104, 28)
                pygame.draw.rect(screen, (35, 115, 135),
                                 mode_rect, border_radius=5)
                mode_label = small_font.render(
                    action_modes[action].upper(), True, WHITE)
                screen.blit(mode_label, mode_label.get_rect(
                    center=mode_rect.center))

            screen.set_clip(old_clip)

            # Scrollbar on the right side of the list.
            scrollbar_track = pygame.Rect(880, 120, 8, 455)
            pygame.draw.rect(
                screen, (22, 29, 42), scrollbar_track, border_radius=4
            )
            if settings_content_height > settings_viewport.height:
                thumb_height = max(
                    35,
                    int(settings_viewport.height * settings_viewport.height /
                        settings_content_height)
                )
                thumb_range = scrollbar_track.height - thumb_height
                thumb_y = scrollbar_track.y + int(
                    (settings_scroll / settings_max_scroll) * thumb_range
                ) if settings_max_scroll else scrollbar_track.y
                pygame.draw.rect(
                    screen,
                    (130, 155, 190),
                    pygame.Rect(scrollbar_track.x, thumb_y, 8, thumb_height),
                    border_radius=4
                )
            else:
                pygame.draw.rect(
                    screen, (130, 155, 190), scrollbar_track,
                    border_radius=4
                )

            draw_text(
                settings_message,
                350, 620, YELLOW, small_font
            )
            draw_text(
                'Press ESC or click SETTINGS to close',
                390, 645, WHITE, small_font
            )

        if game_started and health > 0 and game_won:
            draw_result_screen(victory=True)

        if game_started and health > 0 and not settings_open and not game_won:
            if full_map_open:
                draw_full_map()
            else:
                draw_minimap()

        if (game_started and health > 0 and not game_won
                and not settings_open and not full_map_open):
            draw_weapon_inventory_bar()

        pygame.display.flip()

    pygame.quit()


asyncio.run(main())
