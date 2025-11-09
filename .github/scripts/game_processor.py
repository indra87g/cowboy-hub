import os
import json
import random
import re
import sys

# Constants
MAX_SPACE = 8
MAX_HISTORY = 50

# Game state file
STATE_FILE = "game_state.json"
README_FILE = "README.md"

def load_game_state():
    """Load game state from file or create default state"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    else:
        # Default initial state
        return {
            "cowboy_pos": 7,
            "bandit_pos": 0,
            "bomb_pos": -1,
            "bomb_timer": 0,
            "steps_to_bomb": random.randint(3, 7),
            "step_count": 0,
            "available_space": 8,
            "game_over": False,
            "last_winner": None,
            "history": []
        }

def save_game_state(state):
    """Save game state to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def update_readme(state):
    """Update README.md with current game state and history"""
    # Generate board visualization
    cowboy_area = ['.'] * state['available_space']
    if 0 <= state['cowboy_pos'] < state['available_space']:
        cowboy_area[state['cowboy_pos']] = '🤠'
    if 0 <= state['bomb_pos'] < state['available_space']:
        cowboy_area[state['bomb_pos']] = '💣'
    
    bandit_area = ['.'] * state['available_space']
    if 0 <= state['bandit_pos'] < state['available_space']:
        bandit_area[state['bandit_pos']] = '😡'
    
    # Game status message
    status_message = ""
    if state["game_over"]:
        if state["last_winner"] == "Cowboy":
            status_message = "🎉 Cowboy win! The game has been reset."
        else:
            status_message = "💥 Cowboy lost to the bomb! The game has been reset."
    
    # Format the history
    history_text = "\n".join([f"- @{entry['user']} ({entry['role']}) - {entry['move']}" for entry in state["history"]])
    
    # Create README content
    readme_content = f"""# Cowboy Hub

This is a simple Cowboy game running on GitHub via GitHub Actions. Feel free to play by creating a new issue.

## Latest Game Status

```
Cowboy Region:
{' '.join(cowboy_area)}

Bandit Region:
{' '.join(bandit_area)}
```

Status: { status_message or None } 

Step(s): {state['step_count']}

Available space: {state['available_space']}

Last Winner: {state['last_winner']}

## How to Play

1. Create a new issue with the title: `[PLAY] <role> - <step>`
   - Example: `[PLAY] Cowboy - Left` or `[PLAY] Bandit - Right`
2. Available roles: `Cowboy` or `Bandit`
3. Available steps: `Left` or `Right`
4. The game will be updated after the issue is created

## Game Rules

- Cowboy and Bandit take turns stepping to the left and right
- Each step can generate a new point (maximum 6 points)
- A bomb will appear randomly in the Cowboy's area
- If the Cowboy is hit by a bomb, the Cowboy loses
- If the Cowboy is aligned with the Bandit, the Cowboy wins

## Player History

(History will be reset after 50 entries)

{history_text}
"""

    with open(README_FILE, 'w') as f:
        f.write(readme_content)

def process_move(title, username):
    """Process a move from a GitHub issue"""
    # Parse issue title: [MAIN] <role> - <move>
    match = re.match(r'\[PLAY\]\s*(Cowboy|Bandit)\s*-\s*(Left|Right)', title, re.IGNORECASE)
    if not match:
        print("Invalid issue format")
        return
    
    role = match.group(1).capitalize()
    move = match.group(2).lower()
    
    # Load game state
    state = load_game_state()
    
    # Record move in history
    state["history"].insert(0, {"user": username, "role": role, "move": move.capitalize()})
    if len(state["history"]) > MAX_HISTORY:
        state["history"] = state["history"][:MAX_HISTORY]
    
    # Process move
    if role == "Cowboy":
        process_cowboy_move(state, move)
    else:  # Bandit
        process_bandit_move(state, move)
    
    # Check win/lose conditions
    check_game_conditions(state)
    
    # Save state and update README
    save_game_state(state)
    update_readme(state)

def process_cowboy_move(state, move):
    """Process a cowboy (player) move"""
    # Move cowboy
    if move == "left" and state["cowboy_pos"] > 0:
        state["cowboy_pos"] -= 1
    elif move == "right" and state["cowboy_pos"] < state["available_space"] - 1:
        state["cowboy_pos"] += 1
    
    state["step_count"] += 1
    
    # Expand space randomly (30% chance)
    if state["available_space"] < MAX_SPACE and random.random() < 0.3:
        state["available_space"] += 1
    
    # Handle bomb appearance
    if state["step_count"] == state["steps_to_bomb"] and state["bomb_pos"] == -1:
        possible_positions = [i for i in range(state["available_space"]) if i != state["cowboy_pos"]]
        if possible_positions:
            state["bomb_pos"] = random.choice(possible_positions)
            state["bomb_timer"] = random.randint(1, 3)

def process_bandit_move(state, move):
    """Process a bandit (enemy) move"""
    # Move bandit based on explicit move command
    if move == "left" and state["bandit_pos"] > 0:
        state["bandit_pos"] -= 1
    elif move == "right" and state["bandit_pos"] < state["available_space"] - 1:
        state["bandit_pos"] += 1
    
    state["step_count"] += 1
    
    # Expand space randomly (30% chance)
    if state["available_space"] < MAX_SPACE and random.random() < 0.3:
        state["available_space"] += 1
    
    # Update bomb timer
    if state["bomb_pos"] != -1:
        state["bomb_timer"] -= 1
        if state["bomb_timer"] <= 0:
            state["bomb_pos"] = -1
            state["steps_to_bomb"] = state["step_count"] + random.randint(3, 6)

def check_game_conditions(state):
    """Check win/lose conditions"""
    # Check if cowboy hits bomb
    if state["cowboy_pos"] == state["bomb_pos"] and state["bomb_pos"] != -1:
        state["game_over"] = True
        state["last_winner"] = "Bandit"
        reset_game(state)
    
    # Check if cowboy and bandit align
    if state["cowboy_pos"] == state["bandit_pos"]:
        state["game_over"] = True
        state["last_winner"] = "Cowboy"
        reset_game(state)

def reset_game(state):
    """Reset game after win/lose while keeping positions"""
    # Keep positions but reset bomb
    state["bomb_pos"] = -1
    state["bomb_timer"] = 0
    state["steps_to_bomb"] = state["step_count"] + random.randint(3, 6)
    
    # If cowboy won, move bandit 2 steps
    if state["last_winner"] == "Cowboy":
        # Try to move bandit 2 steps away
        if state["bandit_pos"] + 2 < state["available_space"]:
            state["bandit_pos"] += 2
        elif state["bandit_pos"] - 2 >= 0:
            state["bandit_pos"] -= 2
        else:
            # Find a position at least 2 steps away if possible
            possible_pos = [i for i in range(state["available_space"]) if abs(i - state["cowboy_pos"]) >= 2]
            if possible_pos:
                state["bandit_pos"] = random.choice(possible_pos)
    
    # Reset game over flag
    state["game_over"] = False

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        issue_title = sys.argv[1]
        username = sys.argv[2]
        process_move(issue_title, username)
    else:
        print("Usage: python game_processor.py '<issue_title>' '<username>'")
