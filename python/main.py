import time
import threading
import urllib.parse
import re
import random
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from arduino.app_utils import App, Bridge

# ============================================================
# †Vibe-Patching† Local LLM Engine + Preset Fallback
# 完全ローカル・完全オフライン・API不要
# ============================================================

# --- モデル設定 ---
MODEL_PATH = "/home/arduino/models/smollm2-360m-instruct.Q4_K_M.gguf"

SYSTEM_PROMPT = (
    "You are a synthesizer patch generator for KORG volca modular. "
    "The user describes a sound. Respond ONLY with exactly 6 comma-separated integers (0-255): "
    "PITCH,FOLD,MOD,WOGGLE,LPG,SPACE_OUT. "
    "Examples: sharp kick: 128,30,0,10,230,20 / cosmic drone: 60,180,100,200,120,230 / "
    "glitchy noise: 200,255,255,255,180,50 / sad ambient: 60,40,30,60,80,230. "
    "Output ONLY the 6 numbers. No text. No explanation."
)

# --- ローカルLLM初期化 ---
llm = None

def init_llm():
    """llama-cpp-python でローカルLLMをロード"""
    global llm
    if not os.path.exists(MODEL_PATH):
        print(f"[LLM] Model not found at {MODEL_PATH}")
        print(f"[LLM] Download it with:")
        print(f"  mkdir -p /home/arduino/models")
        print(f"  wget -O {MODEL_PATH} https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF/resolve/main/smollm2-360m-instruct-q4_k_m.gguf")
        print(f"[LLM] Falling back to preset engine only.")
        return

    try:
        from llama_cpp import Llama
        print(f"[LLM] Loading model: {MODEL_PATH} ...")
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=256,      # コンテキスト長（短くてOK）
            n_threads=4,    # Uno Q の CPU コア数に合わせる
            verbose=False,
        )
        print(f"[LLM] Model loaded successfully!")
    except ImportError:
        print("[LLM] llama-cpp-python not installed. Using preset fallback only.")
    except Exception as e:
        print(f"[LLM] Failed to load model: {e}")
        print("[LLM] Using preset fallback only.")

# 起動時にLLMロードを試みる
init_llm()


# ============================================================
# プリセットエンジン（フォールバック用）
# ============================================================
# 各プリセット: (PITCH, FOLD, MOD, WOGGLE, LPG, SPACE_OUT)

PRESETS = {
    # === 打楽器系 ===
    "kick":       (128,  30,   0,  10, 230,  20),
    "キック":     (128,  30,   0,  10, 230,  20),
    "snare":      (180,  80,  20,  40, 200,  40),
    "スネア":     (180,  80,  20,  40, 200,  40),
    "hihat":      (220,  20,   0,   5, 150,  10),
    "ハイハット": (220,  20,   0,   5, 150,  10),
    "perc":       (160,  60,  10,  30, 180,  30),
    "パーカッション": (160, 60, 10, 30, 180, 30),

    # === ドローン・アンビエント系 ===
    "drone":      ( 60, 180, 100, 200, 120, 230),
    "ドローン":   ( 60, 180, 100, 200, 120, 230),
    "ambient":    ( 80,  40,  60, 100,  80, 255),
    "アンビエント": (80, 40,  60, 100,  80, 255),
    "pad":        ( 70, 100,  80, 120, 100, 200),
    "パッド":     ( 70, 100,  80, 120, 100, 200),
    "space":      ( 50,  60,  40, 150,  90, 255),
    "宇宙":       ( 50,  60,  40, 150,  90, 255),

    # === 攻撃的・ノイズ系 ===
    "harsh":      (180, 255, 200, 180, 255,  30),
    "ハーシュ":   (180, 255, 200, 180, 255,  30),
    "noise":      (200, 230, 255, 255, 200,  50),
    "ノイズ":     (200, 230, 255, 255, 200,  50),
    "glitch":     (200, 255, 255, 255, 180,  50),
    "グリッチ":   (200, 255, 255, 255, 180,  50),
    "distort":    (150, 255, 180, 100, 220,  40),
    "歪み":       (150, 255, 180, 100, 220,  40),

    # === メロディック・トーン系 ===
    "bell":       (200,  50,  30,  20, 160, 180),
    "ベル":       (200,  50,  30,  20, 160, 180),
    "pluck":      (150,  40,   0,  10, 200,  60),
    "プラック":   (150,  40,   0,  10, 200,  60),
    "bass":       ( 40, 120,  50,  30, 200,  40),
    "ベース":     ( 40, 120,  50,  30, 200,  40),
    "lead":       (180,  80,  60,  40, 180,  80),
    "リード":     (180,  80,  60,  40, 180,  80),

    # === テクスチャ・質感系 ===
    "metallic":   (190, 200, 150,  80, 170,  90),
    "メタリック": (190, 200, 150,  80, 170,  90),
    "木":         (100,  30,  20,  40, 140, 100),
    "water":      ( 90,  50,  80, 180, 100, 220),
    "水":         ( 90,  50,  80, 180, 100, 220),
    "wind":       ( 70,  20, 120, 200,  60, 200),
    "風":         ( 70,  20, 120, 200,  60, 200),

    # === 感情・雰囲気系 ===
    "怖い":       ( 30, 200, 180, 220, 100, 180),
    "scary":      ( 30, 200, 180, 220, 100, 180),
    "楽しい":     (160,  80, 100, 120, 180, 120),
    "happy":      (160,  80, 100, 120, 180, 120),
    "悲しい":     ( 60,  40,  30,  60,  80, 230),
    "sad":        ( 60,  40,  30,  60,  80, 230),
    "怒り":       (200, 255, 230, 200, 255,  20),
    "angry":      (200, 255, 230, 200, 255,  20),
    "calm":       ( 80,  30,  20,  40, 100, 180),
    "穏やか":     ( 80,  30,  20,  40, 100, 180),

    # === ネタ系 ===
    "バカ":       (random.randint(0,255), 255, 255, 255, 255, random.randint(0,255)),
    "crazy":      (random.randint(0,255), 255, 255, 255, 255, random.randint(0,255)),
    "やばい":     (255, 255, 255, 255, 255, 255),
    "max":        (255, 255, 255, 255, 255, 255),
    "silent":     (  0,   0,   0,   0,   0,   0),
    "無音":       (  0,   0,   0,   0,   0,   0),
}

DEFAULT_PATCH = (128, 128, 128, 128, 128, 128)


def match_preset(text):
    """フォールバック: キーワードマッチでプリセットを返す。
    どのキーワードにもマッチしない場合は、完全に平坦な128ではなく、
    シンセサイザーとして音が動き、かつ音が消えない面白いランダムな値を返してVibeを維持する！
    """
    text_lower = text.lower()
    matched = []
    for keyword, values in PRESETS.items():
        if keyword in text_lower:
            matched.append(values)

    if not matched:
        print("  [Preset] No keywords matched. Generating interesting random patch...")
        return (
            random.randint(40, 180),   # PITCH: まともな音域
            random.randint(20, 230),   # FOLD: 倍音変化
            random.randint(0, 255),    # MOD: モジュレーション
            random.randint(0, 255),    # WOGGLE: ランダム電圧
            random.randint(80, 220),   # LPG: ゲートが開いて音が聞こえるように最低80を確保
            random.randint(20, 240)    # SPACE OUT: スペースの広がり
        )
    if len(matched) == 1:
        return matched[0]

    return tuple(
        int(sum(vals[i] for vals in matched) / len(matched))
        for i in range(6)
    )


def parse_llm_response(text):
    """LLMのレスポンスから6つの整数を賢く抽出・パース。
    LLMがお喋りして余計な数字（例: 'Here are the 6 values:' の '6' やモデル名 '360M' など）
    を含んでしまっても、正しくカンマ区切りの6つの値を抽出できるようにする。
    """
    # 1. まずカンマ（またはスペース）で区切られた3桁以内の数字が6つ連続するパターンを探す
    # 例: "128, 64, 32, 0, 200, 50"
    comma_pattern = re.search(r'\d{1,3}(?:\s*,\s*\d{1,3}){5}', text)
    if comma_pattern:
        numbers = re.findall(r'\d+', comma_pattern.group(0))
        if len(numbers) >= 6:
            return tuple(max(0, min(255, int(n))) for n in numbers[:6])

    # 2. 上記で見つからない場合、文章全体から3桁以内の独立した数字を抽出
    numbers = re.findall(r'\b\d{1,3}\b', text)
    # 0〜255の範囲に収まる有効な数値だけをリスト化
    valid_numbers = [int(n) for n in numbers if 0 <= int(n) <= 255]
    if len(valid_numbers) >= 6:
        return tuple(valid_numbers[:6])

    return None



def on_prompt(data):
    """Handle text input from the user (Manual Mode)
    1. ローカルLLMで推論を試みる
    2. パースに失敗 or LLM未ロード → プリセットにフォールバック
    """
    print(f"Received prompt: {data}")
    source = "preset"

    if llm is not None:
        try:
            print("  [LLM] Generating...")
            result = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": data},
                ],
                max_tokens=30,
                temperature=0.7,
            )
            raw = result["choices"][0]["message"]["content"].strip()
            print(f"  [LLM] Raw response: {raw}")

            values = parse_llm_response(raw)
            if values:
                source = "llm"
                patch_params = ",".join(map(str, values))
                print(f"  [LLM] Patch accepted: {patch_params}")
                Bridge.call("apply_manual_patch", patch_params)
                return patch_params
            else:
                print(f"  [LLM] Parse failed. Falling back to preset.")
        except Exception as e:
            print(f"  [LLM] Error: {e}. Falling back to preset.")

    # フォールバック: プリセットエンジン
    values = match_preset(data)
    patch_params = ",".join(map(str, values))
    print(f"  [Preset] Patch resolved: {patch_params}")
    Bridge.call("apply_manual_patch", patch_params)
    return patch_params

def on_auto(data=""):
    """Switch back to Auto Mode (AI MIDI interpretation)"""
    print("Switching back to Auto Mode...")
    Bridge.call("enable_auto_mode", "")
    return "OK"

# ============================================================
# キュー制 + クールダウン + 管理者バイパス
# ============================================================
import json

ADMIN_PASSWORD = "vibeadmin"
COOLDOWN_SECONDS = 60
QUEUE_INTERVAL = 20  # 秒ごとにキューから1つ適用

prompt_queue = []        # [{prompt, ip, timestamp}, ...]
cooldown_map = {}        # {ip: last_submit_timestamp}
current_patch_info = {"prompt": None, "params": None, "source": None}
queue_lock = threading.Lock()


def add_to_queue(prompt, ip):
    """キューにプロンプトを追加（クールダウンチェック付き）"""
    now = time.time()
    # クールダウンチェック
    if ip in cooldown_map:
        elapsed = now - cooldown_map[ip]
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            return {"ok": False, "error": f"Cooldown: {remaining}s remaining"}

    with queue_lock:
        prompt_queue.append({"prompt": prompt, "ip": ip, "time": now})
        cooldown_map[ip] = now
        pos = len(prompt_queue)
    print(f"[Queue] Added #{pos}: '{prompt}' from {ip}")
    return {"ok": True, "position": pos}


def admin_immediate(prompt):
    """管理者: 即時適用（キューをスキップ）"""
    result = on_prompt(prompt)
    current_patch_info["prompt"] = prompt
    current_patch_info["params"] = result
    current_patch_info["source"] = "admin"
    return result


def process_queue():
    """バックグラウンドスレッド: キューから定期的にパッチを適用"""
    while True:
        time.sleep(QUEUE_INTERVAL)
        with queue_lock:
            if not prompt_queue:
                continue
            item = prompt_queue.pop(0)
        print(f"[Queue] Processing: '{item['prompt']}'")
        result = on_prompt(item["prompt"])
        current_patch_info["prompt"] = item["prompt"]
        current_patch_info["params"] = result
        current_patch_info["source"] = "queue"

threading.Thread(target=process_queue, daemon=True).start()


def get_queue_state():
    """キューの現在状態をJSON用dictで返す"""
    with queue_lock:
        q = [{"prompt": x["prompt"], "pos": i+1} for i, x in enumerate(prompt_queue)]
    return {
        "queue": q,
        "current": current_patch_info,
        "queue_interval": QUEUE_INTERVAL,
        "cooldown": COOLDOWN_SECONDS,
    }


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ja" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>†Vibe-Patching†</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: { extend: { fontFamily: { sans: ['Inter','sans-serif'] }, colors: { muted: '#a1a1aa' } } }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        body { background:#000; color:#fff; }
        .glass-card { background:rgba(17,17,17,0.6); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px); border:1px solid rgba(255,255,255,0.08); }
        .glowing-bg { position:fixed; top:-50%; left:-50%; width:200%; height:200%; background:radial-gradient(circle at 50% 50%,rgba(29,78,216,0.15),transparent 50%); z-index:-1; pointer-events:none; }
        .vt { transition:all 200ms cubic-bezier(0.4,0,0.2,1); }
        .tab-active { background:rgba(255,255,255,0.1); color:#fff; }
        .tab-inactive { color:#a1a1aa; }
        .tab-inactive:hover { color:#fff; background:rgba(255,255,255,0.05); }
        .panel { display:none; } .panel.active { display:flex; }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4 antialiased relative">
    <div class="glowing-bg"></div>
    <div class="w-full max-w-3xl flex flex-col gap-5">

        <!-- Header -->
        <div class="glass-card rounded-2xl p-6 vt hover:border-white/20 flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-semibold tracking-tight">†Vibe-Patching†</h1>
                <p class="text-sm text-muted mt-1">Audience-Driven Synthesizer</p>
            </div>
            <div class="h-10 w-10 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center border border-white/10">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-white"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
            </div>
        </div>

        <!-- Main Card -->
        <div class="glass-card rounded-3xl p-2 vt flex flex-col gap-2">
            <!-- Tabs -->
            <div class="flex gap-2 p-2 border-b border-white/5">
                <button onclick="switchTab('generate')" id="tab-generate" class="px-4 py-2 text-sm font-medium rounded-lg vt tab-active">Generate</button>
                <button onclick="switchTab('sequencer')" id="tab-sequencer" class="px-4 py-2 text-sm font-medium rounded-lg vt tab-inactive">Sequencer</button>
                <button onclick="switchTab('settings')" id="tab-settings" class="px-4 py-2 text-sm font-medium rounded-lg vt tab-inactive">Settings</button>
            </div>

            <!-- Generate Panel -->
            <div id="panel-generate" class="panel active flex-col gap-6 p-6">
                <div class="flex flex-col gap-2">
                    <label class="text-xs font-semibold text-muted uppercase tracking-wider">Prompt</label>
                    <input type="text" id="promptInput" class="w-full bg-black/50 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 vt text-white placeholder:text-zinc-600" placeholder="How should it sound?">
                </div>
                <div class="grid grid-cols-3 gap-3 mt-4">
                    <div class="bg-black/30 border border-white/5 rounded-xl p-3 flex flex-col gap-1 vt hover:bg-white/5"><span class="text-xs text-muted">PITCH</span><span id="val-pitch" class="text-lg font-medium">Auto</span></div>
                    <div class="bg-black/30 border border-white/5 rounded-xl p-3 flex flex-col gap-1 vt hover:bg-white/5"><span class="text-xs text-muted">FOLD</span><span id="val-fold" class="text-lg font-medium">Auto</span></div>
                    <div class="bg-black/30 border border-white/5 rounded-xl p-3 flex flex-col gap-1 vt hover:bg-white/5"><span class="text-xs text-muted">MOD</span><span id="val-mod" class="text-lg font-medium">Auto</span></div>
                    <div class="bg-black/30 border border-white/5 rounded-xl p-3 flex flex-col gap-1 vt hover:bg-white/5"><span class="text-xs text-muted">WOGGLE</span><span id="val-woggle" class="text-lg font-medium">Auto</span></div>
                    <div class="bg-black/30 border border-white/5 rounded-xl p-3 flex flex-col gap-1 vt hover:bg-white/5"><span class="text-xs text-muted">LPG</span><span id="val-lpg" class="text-lg font-medium">Auto</span></div>
                    <div class="bg-black/30 border border-white/5 rounded-xl p-3 flex flex-col gap-1 vt hover:bg-white/5"><span class="text-xs text-muted">SPACE OUT</span><span id="val-spaceout" class="text-lg font-medium">Auto</span></div>
                </div>
                <div class="flex gap-3 mt-4">
                    <button onclick="submitToQueue()" id="btn-submit" class="flex-1 bg-white text-black hover:bg-gray-200 font-medium py-2.5 px-4 rounded-xl vt shadow-[0_0_20px_rgba(255,255,255,0.1)]">Submit to Queue</button>
                    <button onclick="setAutoMode()" class="flex-1 bg-transparent border border-white/10 hover:bg-white/5 text-white font-medium py-2.5 px-4 rounded-xl vt">MIDI Auto</button>
                </div>
                <div id="cooldown-bar" class="hidden mt-2 w-full bg-white/5 rounded-full h-1.5 overflow-hidden"><div id="cooldown-fill" class="h-full bg-blue-500 rounded-full vt" style="width:0%"></div></div>
            </div>

            <!-- Sequencer Panel (Queue) -->
            <div id="panel-sequencer" class="panel flex-col gap-4 p-6">
                <div class="flex items-center justify-between">
                    <label class="text-xs font-semibold text-muted uppercase tracking-wider">Patch Queue</label>
                    <span id="queue-count" class="text-xs text-muted">0 in queue</span>
                </div>
                <div id="now-playing" class="hidden bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-4 flex items-center gap-3">
                    <div class="h-3 w-3 rounded-full bg-blue-500 animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
                    <div><span class="text-xs text-blue-400">NOW PLAYING</span><p id="now-prompt" class="text-sm font-medium mt-0.5">—</p></div>
                </div>
                <div id="queue-list" class="flex flex-col gap-2 max-h-60 overflow-y-auto"></div>
                <div id="queue-empty" class="text-center text-sm text-muted py-8">Queue is empty. Submit a prompt!</div>
            </div>

            <!-- Settings Panel -->
            <div id="panel-settings" class="panel flex-col gap-6 p-6">
                <div class="flex flex-col gap-2">
                    <label class="text-xs font-semibold text-muted uppercase tracking-wider">Admin Password</label>
                    <div class="flex gap-3">
                        <input type="password" id="adminPw" class="flex-1 bg-black/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 vt text-white placeholder:text-zinc-600" placeholder="Enter password...">
                        <button onclick="loginAdmin()" class="bg-white/10 hover:bg-white/20 text-white font-medium py-2.5 px-6 rounded-xl vt">Login</button>
                    </div>
                    <p id="admin-status" class="text-xs text-muted mt-1">Not authenticated</p>
                </div>
                <div id="admin-controls" class="hidden flex flex-col gap-4">
                    <div class="flex flex-col gap-2">
                        <label class="text-xs font-semibold text-muted uppercase tracking-wider">Admin: Instant Deploy</label>
                        <div class="flex gap-3">
                            <input type="text" id="adminPrompt" class="flex-1 bg-black/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none vt text-white placeholder:text-zinc-600" placeholder="Instant prompt (no cooldown, no queue)...">
                            <button onclick="adminDeploy()" class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2.5 px-6 rounded-xl vt">Deploy</button>
                        </div>
                    </div>
                    <div class="flex gap-3">
                        <button onclick="adminClear()" class="flex-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium py-2.5 px-4 rounded-xl vt border border-red-500/20">Clear Queue</button>
                        <button onclick="adminSkip()" class="flex-1 bg-white/10 hover:bg-white/20 text-white font-medium py-2.5 px-4 rounded-xl vt">Skip to Next</button>
                        <button onclick="setAutoMode()" class="flex-1 bg-white/10 hover:bg-white/20 text-white font-medium py-2.5 px-4 rounded-xl vt">MIDI Auto</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Status -->
        <div class="glass-card rounded-xl p-4 flex items-center gap-3 vt">
            <div class="h-2 w-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
            <div id="status" class="text-sm font-mono text-muted">System Ready. Awaiting vibes...</div>
        </div>
    </div>

<script>
let adminToken = '';
let cooldownEnd = 0;
let cooldownTimer = null;

function switchTab(name) {
    ['generate','sequencer','settings'].forEach(t => {
        document.getElementById('tab-'+t).className = 'px-4 py-2 text-sm font-medium rounded-lg vt ' + (t===name?'tab-active':'tab-inactive');
        document.getElementById('panel-'+t).classList.toggle('active', t===name);
    });
    if(name==='sequencer') refreshQueue();
}

function setStatus(msg, color) {
    const s = document.getElementById('status');
    s.innerText = msg;
    s.className = 'text-sm font-mono text-' + color;
}

async function submitToQueue() {
    const prompt = document.getElementById('promptInput').value;
    if(!prompt) return;
    if(Date.now() < cooldownEnd) return;
    try {
        const res = await fetch('/api/queue', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt}) });
        const data = await res.json();
        if(data.ok) {
            setStatus('Queued at position #' + data.position, 'green-400');
            document.getElementById('promptInput').value = '';
            startCooldown(data.cooldown || 60);
        } else {
            setStatus(data.error, 'red-400');
        }
    } catch(e) { setStatus('Error: connection failed', 'red-400'); }
}

function startCooldown(seconds) {
    cooldownEnd = Date.now() + seconds*1000;
    const btn = document.getElementById('btn-submit');
    const bar = document.getElementById('cooldown-bar');
    const fill = document.getElementById('cooldown-fill');
    btn.disabled = true; btn.classList.add('opacity-50');
    bar.classList.remove('hidden');
    if(cooldownTimer) clearInterval(cooldownTimer);
    cooldownTimer = setInterval(() => {
        const remain = Math.max(0, cooldownEnd - Date.now());
        const pct = 100 - (remain / (seconds*1000)) * 100;
        fill.style.width = pct + '%';
        if(remain <= 0) {
            clearInterval(cooldownTimer);
            btn.disabled = false; btn.classList.remove('opacity-50');
            bar.classList.add('hidden');
            btn.innerText = 'Submit to Queue';
        } else {
            btn.innerText = 'Wait ' + Math.ceil(remain/1000) + 's';
        }
    }, 200);
}

async function refreshQueue() {
    try {
        const res = await fetch('/api/queue');
        const data = await res.json();
        const list = document.getElementById('queue-list');
        const empty = document.getElementById('queue-empty');
        const count = document.getElementById('queue-count');
        const np = document.getElementById('now-playing');
        count.innerText = data.queue.length + ' in queue';
        if(data.current && data.current.prompt) {
            np.classList.remove('hidden');
            document.getElementById('now-prompt').innerText = data.current.prompt;
            if(data.current.params) {
                const vals = data.current.params.split(',');
                const ids = ['val-pitch','val-fold','val-mod','val-woggle','val-lpg','val-spaceout'];
                ids.forEach((id,i) => { const el=document.getElementById(id); if(el&&vals[i]) el.innerText=vals[i].trim(); });
            }
        } else { np.classList.add('hidden'); }
        if(data.queue.length === 0) { list.innerHTML=''; empty.classList.remove('hidden'); }
        else {
            empty.classList.add('hidden');
            list.innerHTML = data.queue.map(q =>
                '<div class="bg-black/30 border border-white/5 rounded-lg p-3 flex items-center gap-3 vt">' +
                '<span class="text-xs text-muted font-mono w-6">#'+q.pos+'</span>' +
                '<span class="text-sm flex-1">'+q.prompt+'</span></div>'
            ).join('');
        }
    } catch(e) {}
}

async function setAutoMode() {
    try { await fetch('/auto'); setStatus('MIDI Auto Mode Enabled','green-400');
        ['val-pitch','val-fold','val-mod','val-woggle','val-lpg','val-spaceout'].forEach(id => document.getElementById(id).innerText='Auto');
    } catch(e) { setStatus('Error','red-400'); }
}

async function loginAdmin() {
    const pw = document.getElementById('adminPw').value;
    try {
        const res = await fetch('/api/admin/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: pw})
        });
        const data = await res.json();
        if(data.ok) {
            adminToken = pw;
            document.getElementById('admin-status').innerText = 'Authenticated ✓';
            document.getElementById('admin-status').className = 'text-xs text-green-400 mt-1';
            document.getElementById('admin-controls').classList.remove('hidden');
        } else {
            document.getElementById('admin-status').innerText = 'Error: ' + (data.error || 'Wrong password');
            document.getElementById('admin-status').className = 'text-xs text-red-400 mt-1';
            document.getElementById('admin-controls').classList.add('hidden');
        }
    } catch(e) {
        document.getElementById('admin-status').innerText = 'Error: Connection failed';
        document.getElementById('admin-status').className = 'text-xs text-red-400 mt-1';
    }
}

async function adminDeploy() {
    const prompt = document.getElementById('adminPrompt').value;
    if(!prompt) return;
    try {
        const res = await fetch('/api/admin/deploy', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt, password: adminToken}) });
        const data = await res.json();
        if(data.ok) { setStatus('Admin Deploy: '+data.params, 'blue-400'); document.getElementById('adminPrompt').value=''; }
        else setStatus(data.error, 'red-400');
    } catch(e) { setStatus('Error','red-400'); }
}

async function adminClear() {
    try {
        await fetch('/api/admin/clear', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: adminToken}) });
        setStatus('Queue cleared', 'green-400'); refreshQueue();
    } catch(e) {}
}

async function adminSkip() {
    try {
        const res = await fetch('/api/admin/skip', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: adminToken}) });
        const data = await res.json();
        if(data.ok) setStatus('Skipped to: '+data.prompt, 'blue-400');
        else setStatus(data.error || 'Queue empty', 'muted');
        refreshQueue();
    } catch(e) {}
}

// 自動リフレッシュ：観客がどのタブを開いていても常に最新のパラメータやキューをバックグラウンドで反映する！
// これにより、Generate画面のカードUIもリアルタイムで最新のパッチ値に自動ピコピコ更新される！
refreshQueue(); // 起動時に一回ロード
setInterval(refreshQueue, 2000); // 2秒ごとに自動更新
</script>
</body>
</html>
"""


class UIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _client_ip(self):
        return self.client_address[0]

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path == '/api/queue':
            self._send_json(get_queue_state())
        elif self.path.startswith('/auto'):
            on_auto()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        body = self._read_body()

        if self.path == '/api/admin/login':
            if body.get('password') == ADMIN_PASSWORD:
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False, "error": "Wrong password"}, 403)

        elif self.path == '/api/queue':
            prompt = body.get('prompt', '')
            if not prompt:
                self._send_json({"ok": False, "error": "Empty prompt"}, 400)
                return
            result = add_to_queue(prompt, self._client_ip())
            result["cooldown"] = COOLDOWN_SECONDS
            self._send_json(result)

        elif self.path == '/api/admin/deploy':
            if body.get('password') != ADMIN_PASSWORD:
                self._send_json({"ok": False, "error": "Wrong password"}, 403)
                return
            params = admin_immediate(body.get('prompt', ''))
            self._send_json({"ok": True, "params": params})

        elif self.path == '/api/admin/clear':
            if body.get('password') != ADMIN_PASSWORD:
                self._send_json({"ok": False, "error": "Wrong password"}, 403)
                return
            with queue_lock:
                prompt_queue.clear()
            print("[Admin] Queue cleared")
            self._send_json({"ok": True})

        elif self.path == '/api/admin/skip':
            if body.get('password') != ADMIN_PASSWORD:
                self._send_json({"ok": False, "error": "Wrong password"}, 403)
                return
            with queue_lock:
                if prompt_queue:
                    item = prompt_queue.pop(0)
                else:
                    self._send_json({"ok": False, "error": "Queue empty"})
                    return
            result = on_prompt(item["prompt"])
            current_patch_info["prompt"] = item["prompt"]
            current_patch_info["params"] = result
            current_patch_info["source"] = "admin-skip"
            self._send_json({"ok": True, "prompt": item["prompt"], "params": result})
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_server():
    print("Starting Web UI server on port 8080...")
    try:
        server = HTTPServer(('0.0.0.0', 8080), UIHandler)
        print("=====================================================")
        print(" †Vibe-Patching† LIVE MODE")
        print(" http://<YOUR_BOARD_IP>:8080")
        print(f" Admin PW: {ADMIN_PASSWORD}")
        print(f" Cooldown: {COOLDOWN_SECONDS}s | Queue interval: {QUEUE_INTERVAL}s")
        print("=====================================================")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start Web UI server: {e}")

threading.Thread(target=start_server, daemon=True).start()

def loop():
    time.sleep(1)

App.run(user_loop=loop)
