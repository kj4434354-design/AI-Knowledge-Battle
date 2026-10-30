import os, random, string, asyncio
from collections import defaultdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

app = FastAPI(title="AI Knowledge Battle")
app.mount("/static", StaticFiles(directory="static"), name="static")

# A built-in question bank keeps the game playable without an API key.
QUESTION_BANK = {
    "AI": [
        ("What does NLP stand for?", ["Natural Language Processing", "Network Learning Protocol", "Neural Logic Program", "Numeric Language Prediction"], 0),
        ("Which task is an example of supervised learning?", ["Grouping customers without labels", "Predicting house prices from labelled examples", "Compressing a file", "Sorting a list"], 1),
        ("What is a large language model primarily trained to do?", ["Predict and generate sequences of tokens", "Repair computer hardware", "Increase internet speed", "Store images only"], 0),
        ("Which metric is commonly used for classification?", ["Accuracy", "Mean absolute error only", "Bitrate", "Latency only"], 0),
    ],
    "Science": [
        ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Mercury"], 1),
        ("What is the chemical symbol for water?", ["CO2", "O2", "H2O", "NaCl"], 2),
        ("Which part of a cell contains most genetic material?", ["Nucleus", "Cell wall", "Ribosome", "Membrane"], 0),
    ],
    "Technology": [
        ("What does CPU stand for?", ["Central Processing Unit", "Computer Personal Utility", "Core Program Upload", "Central Power User"], 0),
        ("Which protocol is commonly used to load web pages securely?", ["FTP", "HTTPS", "SMTP", "SSH only"], 1),
        ("What does RAM provide to a computer?", ["Long-term archival storage", "Temporary working memory", "Internet connectivity", "Power regulation"], 1),
    ],
    "Programming": [
        ("Which Python keyword defines a function?", ["func", "define", "def", "function"], 2),
        ("What is the result of 3 ** 2 in Python?", ["6", "9", "8", "5"], 1),
        ("Which data structure stores key-value pairs in Python?", ["Tuple", "Set", "Dictionary", "String"], 2),
    ],
    "General Knowledge": [
        ("What is the capital of Japan?", ["Seoul", "Beijing", "Tokyo", "Bangkok"], 2),
        ("How many sides does a hexagon have?", ["Five", "Six", "Seven", "Eight"], 1),
        ("Which is the largest ocean on Earth?", ["Atlantic", "Indian", "Arctic", "Pacific"], 3),
    ]
}

rooms = {}
lock = asyncio.Lock()

def room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def make_questions(category, difficulty, count=8):
    # Optional live AI generation. If OPENAI_API_KEY is not set or the call fails,
    # use the local question bank so the game remains fully playable.
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            prompt = (
                f"Create {count} {difficulty.lower()} multiple-choice quiz questions "
                f"about {category}. Return ONLY JSON array. Each item must have "
                f"'question', 'options' (exactly four strings), and 'answer' "
                f"(zero-based integer index). Ensure one unambiguous correct answer."
            )
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role":"user","content":prompt}],
                response_format={"type":"json_object"}
            )
            import json
            raw = json.loads(response.choices[0].message.content)
            data = raw.get("questions", raw if isinstance(raw, list) else [])
            cleaned = []
            for q in data[:count]:
                if len(q.get("options", [])) == 4 and 0 <= int(q.get("answer", -1)) < 4:
                    cleaned.append((q["question"], q["options"], int(q["answer"])))
            if cleaned:
                return cleaned
        except Exception as e:
            print("AI generation fallback:", e)
    pool = QUESTION_BANK.get(category, QUESTION_BANK["General Knowledge"])
    return random.choices(pool, k=count)

class Room:
    def __init__(self, code, host, category, difficulty):
        self.code, self.host = code, host
        self.category, self.difficulty = category, difficulty
        self.players = {}  # websocket -> player record
        self.questions = []
        self.index = 0
        self.answers = {}
        self.started = False
        self.timer_task = None

    def public_players(self):
        return [{"name": p["name"], "score": p["score"]} for p in self.players.values()]

    async def broadcast(self, payload):
        dead = []
        for ws in list(self.players):
            try: await ws.send_json(payload)
            except Exception: dead.append(ws)
        for ws in dead: self.players.pop(ws, None)

    async def state(self):
        await self.broadcast({
            "type":"state", "code":self.code, "host":self.host,
            "players":self.public_players(), "started":self.started,
            "category":self.category, "difficulty":self.difficulty
        })

    async def send_question(self):
        if self.index >= len(self.questions):
            ranking = sorted(self.public_players(), key=lambda x:x["score"], reverse=True)
            await self.broadcast({"type":"finished","leaderboard":ranking})
            self.started = False
            return
        q = self.questions[self.index]
        self.answers = {}
        await self.broadcast({
            "type":"question", "number":self.index+1, "total":len(self.questions),
            "question":q[0], "options":q[1], "seconds":15
        })
        self.timer_task = asyncio.create_task(self.question_timeout())

    async def question_timeout(self):
        await asyncio.sleep(15)
        await self.reveal_answer()

    async def reveal_answer(self):
        if not self.started or self.index >= len(self.questions): return
        if self.timer_task and self.timer_task is not asyncio.current_task():
            self.timer_task.cancel()
        correct = self.questions[self.index][2]
        await self.broadcast({"type":"reveal","correct":correct})
        await asyncio.sleep(3)
        self.index += 1
        await self.send_question()

@app.get("/")
async def home():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    room = None
    try:
        while True:
            msg = await ws.receive_json()
            action = msg.get("action")
            if action == "create":
                async with lock:
                    code = room_code()
                    while code in rooms: code = room_code()
                    room = Room(code, msg["name"], msg.get("category","AI"), msg.get("difficulty","Easy"))
                    rooms[code] = room
                    room.players[ws] = {"name":msg["name"],"score":0}
                await ws.send_json({"type":"joined","code":code,"host":True})
                await room.state()
            elif action == "join":
                code = msg.get("code","").upper()
                async with lock:
                    room = rooms.get(code)
                    if not room or room.started or len(room.players) >= 8:
                        room = None
                    else:
                        room.players[ws] = {"name":msg["name"],"score":0}
                if not room:
                    await ws.send_json({"type":"error","message":"Room not found, already started, or full (maximum 8 players)."})
                else:
                    await ws.send_json({"type":"joined","code":room.code,"host":False})
                    await room.state()
            elif action == "start" and room and msg.get("code") == room.code:
                if room.host != room.players.get(ws,{}).get("name") or room.started or len(room.players)<2:
                    await ws.send_json({"type":"error","message":"The host can start when at least 2 players have joined."})
                    continue
                room.started = True
                room.questions = await make_questions(room.category, room.difficulty)
                room.index = 0
                await room.send_question()
            elif action == "answer" and room and room.started:
                if ws in room.players and ws not in room.answers:
                    choice = int(msg.get("choice",-1))
                    correct = room.questions[room.index][2]
                    room.answers[ws] = choice
                    if choice == correct: room.players[ws]["score"] += 10
                    await ws.send_json({"type":"answer_received","correct":choice==correct})
                    if len(room.answers) == len(room.players):
                        if room.timer_task: room.timer_task.cancel()
                        await room.reveal_answer()
                    else:
                        await room.broadcast({"type":"progress","answered":len(room.answers),"total":len(room.players)})
    except WebSocketDisconnect:
        if room:
            room.players.pop(ws, None)
            if not room.players: rooms.pop(room.code, None)
            else: await room.state()
