#!/usr/bin/env python3
"""M1-P8: AI-Based Interactive Storytelling Agent.

Usage:  python3 story_agent.py            (asks for a theme)
        python3 story_agent.py "haunted lighthouse"
In the story: type 1/2/3 to pick a choice, or type your OWN action in free text.
Commands: memory (show characters/events) | save | quit
Optional: set GROQ_API_KEY to let an LLM write the story; otherwise a built-in
rule-based engine is used. Either way the agent keeps persistent MEMORY of characters,
places and events, and every new segment is conditioned on that memory and your decisions.
"""
import json, os, random, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE = os.path.join(HERE, "story_save.json")

NAMES = ["Mira", "Kael", "Soren", "Lyra", "Tobin", "Zara", "Eldon", "Nia", "Rowan", "Isla", "Dax", "Orla"]
TRAITS = ["fearless", "cautious", "witty", "secretive", "loyal", "restless", "clever", "stubborn"]
PLACES = ["the old gate", "a whispering hall", "the lower tunnels", "a moonlit courtyard", "the archive", "a hidden stair"]
ITEMS = ["a brass key", "a torn map", "a glowing shard", "a sealed letter", "a silver compass"]

class Memory:
    def __init__(self):
        self.theme = ""; self.turn = 0; self.tension = 1
        self.characters = {}
        self.events = []
        self.places = []; self.items = []; self.story = []; self.choices = []

    def add_char(self, name, role, trait=None, status="active"):
        if name not in self.characters:
            self.characters[name] = {"role": role, "trait": trait or random.choice(TRAITS), "status": status, "trust": 0}
            self.events.append(f"{name} ({role}) entered the story")

    def summary(self):
        ch = "; ".join(f"{n} [{c['role']}, {c['trait']}, {c['status']}, trust {c['trust']:+d}]" for n, c in self.characters.items())
        return (f"Theme: {self.theme}\nCharacters: {ch or 'none'}\nPlaces: {', '.join(self.places) or 'none'}\n"
                f"Items: {', '.join(self.items) or 'none'}\nTension: {self.tension}/10\n"
                "Key events:\n" + "\n".join(f"  {i+1}. {e}" for i, e in enumerate(self.events[-25:])))

    def to_json(self): return json.dumps(self.__dict__, indent=2)
    @classmethod
    def from_json(cls, s):
        m = cls(); m.__dict__.update(json.loads(s)); return m

def llm_available():
    return bool(os.environ.get("GROQ_API_KEY"))

def llm_chat(prompt, max_tokens=300, timeout=40):
    payload = {"model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"), "max_tokens": max_tokens + 1500,
               "reasoning_effort": "low", "response_format": {"type": "json_object"},
               "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"], "Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0 ai-project/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [LLM unavailable: {type(e).__name__}; using built-in engine]", file=sys.stderr)
        return None

def llm_step(mem, decision):
    if not llm_available(): return None
    recent = "\n\n".join(mem.story[-3:])
    prompt = f"""You are an interactive storyteller. Continue the story, STRICTLY consistent with the memory below.
Reuse existing characters and refer back to earlier events; introduce a new character only when it fits.
React to the player's decision and let it change the plot.

MEMORY:
{mem.summary()}

RECENT STORY:
{recent or '(story not started)'}

PLAYER DECISION: {decision}

Reply with ONLY JSON: {{"segment": "120-180 words of story", "choices": ["...","...","..."],
"new_characters": [{{"name":"","role":"","trait":""}}], "events": ["short fact(s) that happened"],
"tension_delta": -1|0|1|2, "place": "current location", "items": ["newly gained items"]}}"""
    txt = llm_chat(prompt, 900, timeout=60)
    if not txt: return None
    try:
        d = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        seg = str(d["segment"]).strip(); choices = [str(c) for c in d["choices"]][:3]
        if not seg or len(choices) < 2: return None
        for c in d.get("new_characters", []):
            if c.get("name"): mem.add_char(c["name"], c.get("role", "stranger"), c.get("trait"))
        mem.events += [str(e) for e in d.get("events", [])][:3]
        mem.tension = max(1, min(10, mem.tension + int(d.get("tension_delta", 0))))
        if d.get("place") and d["place"] not in mem.places: mem.places.append(d["place"])
        for it in d.get("items", []):
            if it not in mem.items: mem.items.append(it)
        return seg, [("free", c) for c in choices]
    except Exception:
        return None

def pick(pool, used):
    free = [x for x in pool if x not in used]
    return random.choice(free or pool)

def offline_step(mem, decision):
    hero = next(n for n, c in mem.characters.items() if c["role"] == "hero")
    ally = next((n for n, c in mem.characters.items() if c["role"] == "ally" and c["status"] == "active"), None)
    foe = next((n for n, c in mem.characters.items() if c["role"] == "rival"), None)
    place = pick(PLACES, mem.places)
    theme = mem.theme
    t = mem.turn
    parts = []
    kind, text = decision
    if kind == "brave":
        mem.tension += 2; mem.events.append(f"{hero} bravely confronted danger at {mem.places[-1]}")
        parts.append(f"{hero} charged ahead without hesitation. The risk paid off, but the noise echoed through the dark and the {theme} grew restless.")
    elif kind == "careful":
        mem.tension = max(1, mem.tension - 1); mem.events.append(f"{hero} chose caution and scouted ahead")
        parts.append(f"{hero} slowed down and studied every shadow. The patience revealed a detail others would have missed, though time was slipping away.")
    elif kind == "talk" and ally:
        mem.characters[ally]["trust"] += 1; mem.events.append(f"{hero} confided in {ally}")
        parts.append(f"{hero} turned to {ally} and spoke honestly. {ally}, who is {mem.characters[ally]['trait']}, listened, and something between them shifted.")
    elif kind == "talk":
        mem.events.append(f"{hero} called out into the silence"); parts.append(f"{hero} called into the silence. Something answered, faintly.")
    else:
        mem.tension += 1; mem.events.append(f"{hero} decided to: {text}")
        parts.append(f"{hero} decided to {text.rstrip('.')}. It was an unexpected move, and the {theme} seemed to take notice.")
    old = [e for e in mem.events[:-1] if "entered the story" not in e]
    if len(old) >= 2:
        recall = random.choice(old[:-1] or old)
        parts.append(f"The memory of an earlier moment returned: {recall}.")
    if t == 2 and not foe:
        foe = pick(NAMES, mem.characters); mem.add_char(foe, "rival", "ambitious")
        parts.append(f"At {place}, a figure stepped from the dark: {foe}, who had been tracking the same secret and meant to claim it first.")
    elif t == 4:
        item = pick(ITEMS, mem.items); mem.items.append(item); mem.events.append(f"{hero} found {item} at {place}")
        parts.append(f"Beneath loose stones at {place}, {hero} found {item}. It clearly mattered to the {theme}.")
    elif t == 5 and ally:
        mem.events.append(f"{ally} revealed a secret about the {theme}")
        parts.append(f"{ally} finally admitted knowing more about the {theme} than they had claimed, and the group's trust wavered.")
    elif t == 6:
        n = pick(NAMES, mem.characters); mem.add_char(n, "stranger", "mysterious")
        parts.append(f"A stranger named {n} appeared at {place}, offering help in exchange for a favour.")
    else:
        parts.append(f"They moved on to {place}. " + random.choice([
            f"The air felt heavier, as if the {theme} were listening.",
            "Every step brought them closer to an answer, and further from home.",
            "Far behind them, something old began to stir."]))
    if place not in mem.places: mem.places.append(place)
    if foe and mem.characters[foe]["status"] == "active" and mem.tension >= 4:
        parts.append(f"{foe} was close now, never more than a step behind.")
    if mem.tension >= 8:
        parts.append("The tension reached breaking point. Everything would be decided soon.")
    mem.tension = min(10, mem.tension)
    choices = [("brave", "Act boldly and confront the danger head-on"),
               ("careful", "Hold back, observe, and look for another way")]
    if ally: choices.append(("talk", f"Talk to {ally} and share what you know"))
    elif foe: choices.append(("talk", f"Try to reason with {foe}"))
    else: choices.append(("talk", "Call out and see who answers"))
    return " ".join(parts), choices

def offline_open(mem):
    hero, ally = random.sample(NAMES, 2)
    mem.add_char(hero, "hero", random.choice(TRAITS)); mem.add_char(ally, "ally", random.choice(TRAITS))
    place = random.choice(PLACES); mem.places.append(place)
    seg = (f"Our story begins with the {mem.theme}. {hero}, {mem.characters[hero]['trait']} and determined, arrived at {place} "
           f"with {ally}, their {mem.characters[ally]['trait']} companion. Rumours said the {mem.theme} held a secret worth any risk, "
           f"and tonight, they would find out whether the rumours were true.")
    mem.events.append(f"{hero} and {ally} arrived at {place} seeking the secret of the {mem.theme}")
    return seg, [("brave", "Push forward boldly"), ("careful", "Scout the area first"), ("talk", f"Talk to {ally} about the plan")]

def step(mem, decision):
    mem.turn += 1
    seg, ch = llm_step(mem, decision[1]) or offline_step(mem, decision)
    mem.story.append(seg)
    mem.choices = ch
    return seg, ch

def begin(mem):
    mem.turn = 1
    res = None
    if llm_available():
        mem.add_char(random.choice(NAMES), "hero")
        res = llm_step(mem, "Begin the story with an engaging opening.")
        if not res:
            mem.characters.clear(); mem.events.clear(); mem.places.clear()
    seg, ch = res or offline_open(mem)
    mem.story.append(seg)
    mem.choices = ch
    return seg, ch

def show(seg, ch, turn):
    print(f"\n--- Chapter {turn} ---\n{seg}\n")
    for i, (_, c) in enumerate(ch, 1): print(f"  {i}. {c}")

def main():
    mem = Memory()
    if os.path.exists(SAVE) and sys.stdin.isatty() and len(sys.argv) < 2:
        if input("Saved story found. Continue it? [y/N] ").strip().lower() == "y":
            mem = Memory.from_json(open(SAVE).read())
            mem.choices = [tuple(c) for c in mem.choices]
            show(mem.story[-1], mem.choices, mem.turn)
    if not mem.theme:
        theme = " ".join(sys.argv[1:]).strip()
        if not theme:
            try: theme = input("Enter a theme for your story: ").strip()
            except EOFError: theme = ""
        mem.theme = theme or "forgotten castle"
        seg, ch = begin(mem)
        show(seg, ch, mem.turn)
    print("\n(type 1/2/3, or your own action; commands: memory, save, quit)")
    while True:
        try: raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt): raw = "quit"
        low = raw.lower()
        if low in ("quit", "exit", "q"):
            open(SAVE, "w").write(mem.to_json()); print(f"\nStory saved to {SAVE}. The end... for now."); break
        if low == "memory": print("\n=== AGENT MEMORY ===\n" + mem.summary()); continue
        if low == "save": open(SAVE, "w").write(mem.to_json()); print("Saved."); continue
        if not raw: continue
        if raw.isdigit() and 1 <= int(raw) <= len(mem.choices): decision = mem.choices[int(raw) - 1]
        elif raw.isdigit(): print("Pick a valid number or type your own action."); continue
        else: decision = ("free", raw)
        seg, ch = step(mem, decision)
        show(seg, ch, mem.turn)

if __name__ == "__main__":
    main()
