# †Vibe-Patching†

**Arduino UNO Q × KORG volca modular — 観客参加型 AI自律パッチングシンセサイザー**

ローカルLLM + キーワードプリセットにより、自然言語でvolca modularのパッチングを制御する完全オフラインのライブパフォーマンスシステム。同一LAN上のお客さんのスマホからプロンプトを送信でき、キュー制で順番にパッチが適用される。

---

## 概要

†Vibe-Patching† は3つのモードを持ちます。

| モード | 入力 | 処理 |
|---|---|---|
| **マニュアル（キュー）** | 観客がWeb UIからテキスト入力 | キューに追加 → 順番にLLM/プリセットで6パラメータ生成 → CV出力 |
| **マニュアル（管理者）** | 管理者がSettings画面から即時入力 | キューをスキップして即座にCV出力 |
| **オート** | MIDIキーボード演奏 | MCU上のStateEngineが演奏を解析 → 自律的にCV出力 |

---

## ハードウェア構成

### 必要なもの

- Arduino UNO Q（4GB RAM / 32GB eMMC 推奨）
- KORG volca modular
- パッチケーブル × 6本
- MIDIキーボード（オートモード使用時）

### ピン接続

```
Arduino UNO Q                    volca modular
─────────────                    ──────────────
D3  (PWM) ── CV1 ───────────────→ PITCH
D5  (PWM) ── CV2 ───────────────→ FOLD
D6  (PWM) ── CV3 ───────────────→ MOD
D9  (PWM) ── CV4 ───────────────→ WOGGLE
D10 (PWM) ── CV5 ───────────────→ LPG
D11 (PWM) ── CV6 ───────────────→ SPACE OUT
D2        ── SYNC ──────────────→ SYNC IN（3.5mmモノラル: 先端=D2 / スリーブ=GND）

Serial RX ←──────────────────── MIDI OUT (キーボード)
```

D2 からは、AIステートに応じたテンポのクロックパルスを SYNC IN に出す（→「[SYNCクロック出力](#syncクロック出力)」）。

### PWMピンの拡張（オプション）

6本では足りない場合、Arduino UNO R3をI2Cスレーブとして追加接続できます。

```
UNO Q                レベルシフター        UNO R3
─────                ──────────────        ──────
SDA ──── LV1 ←→ HV1 ──── A4 (SDA)
SCL ──── LV2 ←→ HV2 ──── A5 (SCL)
3.3V ─── LV      HV ──── 5V
GND ──── GND ──── GND ─── GND
```

⚠️ 3.3V ↔ 5V間には双方向ロジックレベルシフター（BSS138ベース等）が必要です。

---

## ソフトウェア構成

```
sample/
├── app.yaml                  # App Lab アプリ設定（ポート8080開放）
├── python/
│   ├── main.py               # LLMエンジン + キューシステム + Web UI
│   ├── ui_labels.json        # Web UIのメトリクスカード表示名（CV1〜CV6）
│   ├── sync_config.json      # SYNCクロックのON/OFFとステートごとのBPM
│   └── requirements.txt      # llama-cpp-python
└── sketch/
    ├── sketch.ino            # メインスケッチ（Bridge + MIDI + CV制御）
    ├── sketch.yaml           # ビルドプロファイル
    ├── CvOutput.h / .cpp     # 6ch CV出力 + スルーレート制御
    ├── SyncOutput.h / .cpp   # D2 → SYNC IN のクロックパルス出力
    ├── StateEngine.h / .cpp  # AI人格エンジン（CALM/RITUAL/PANIC/BROKEN）
    ├── FeatureExtractor.h / .cpp  # MIDI特徴量抽出
    └── MidiHandler.h / .cpp  # MIDI受信処理
```

### アーキテクチャ

```
[観客のスマホ]                [Linux MPU]                     [MCU (Zephyr)]
                             ┌─────────────────────┐  Bridge  ┌──────────────┐
 ブラウザ ──HTTP──→ Web UI   │  main.py            │ ──RPC──→ │ sketch.ino   │
                  (:8080)    │  ├─ Queue System     │          │ ├─ CvOutput  │
                             │  ├─ Cooldown / Admin │          │ ├─ StateEng  │
                             │  ├─ Local LLM        │          │ └─ MIDI解析  │
                             │  └─ Preset Fallback  │          └──────┬───────┘
                             └─────────────────────┘                  ↓
                                                              volca modular (CV)
```

---

## セットアップ

### 1. モデルのダウンロード

UNO Qのターミナルで実行：

```bash
mkdir -p /home/arduino/models
wget -O /home/arduino/models/smollm2-360m-instruct.Q4_K_M.gguf \
  https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/resolve/main/SmolLM2-360M-Instruct-Q4_K_M.gguf
```

約258MB。モデルがなくてもプリセットフォールバックで動作します。

### 2. アプリのデプロイ

1. `Hiou_AppLab.zip` を Arduino App Lab にアップロード
2. **Run** を押す
3. コンソールログで以下を確認：
   ```
   [LLM] Model loaded successfully!
   †Vibe-Patching† LIVE MODE
   http://<YOUR_BOARD_IP>:8080
   Admin PW: vibeadmin
   Cooldown: 60s | Queue interval: 20s
   ```

### 3. Web UIにアクセス

**ローカルLAN内から:**
ブラウザで `http://arduino.local:8080`（または `http://<YOUR_BOARD_IP>:8080`）を開く。

**外部（独自ドメイン）から:**
Cloudflare Tunnel 経由で `https://vibe-patching.ocha-no-taiko.com` を開く。
セットアップ手順は下記「[リモートアクセス（Cloudflare Tunnel）](#リモートアクセスcloudflare-tunnel)」を参照。

---

## リモートアクセス（Cloudflare Tunnel）

会場のWi-Fiに観客を接続させる代わりに、独自ドメインから直接アクセスできるようにする構成。
**ポート開放・固定IP・動的DNSは不要**。Arduino側からCloudflareへアウトバウンド専用の接続を張るため、ルーター設定を触らずに公開できる。

```
[観客のスマホ] ──HTTPS──→ vibe-patching.ocha-no-taiko.com
                              │ (Cloudflare edge)
                              ↓ Tunnel（アウトバウンド接続）
                      [UNO Q] cloudflared ──→ http://localhost:8080 （main.py）
```

### セットアップ手順

1. **トンネル作成**: Cloudflareダッシュボード → Zero Trust → ネットワーク → Tunnels で、名前 `vibe-patching` のトンネルを作成。
2. **UNO Q に cloudflared を導入**: 表示された接続コマンドに従い、UNO Q（Debian / arm64）で cloudflared をインストールし、サービスとして登録・接続する。

   ```bash
   sudo cloudflared service install <CONNECTOR_TOKEN>
   ```

   ⚠️ `<CONNECTOR_TOKEN>` はアカウント連携用の**機密情報**。ターミナル出力やコマンド全文をそのまま共有・コミット・チャット貼付しないこと。
3. **公開ルートを追加**: トンネル詳細 → 「ルートを追加」→「公開アプリケーション」で、
   ホスト名 `vibe-patching.ocha-no-taiko.com` を サービスURL `http://localhost:8080` に紐づける。
   これで DNS の CNAME レコードが自動生成される（`vibe-patching.ocha-no-taiko.com` → `<TUNNEL_ID>.cfargotunnel.com`）。
4. **動作確認**: ブラウザで `https://vibe-patching.ocha-no-taiko.com` を開き、Web UI が表示されればOK。

### トークンを再発行する場合

トークンが漏れた/ローテートしたときは、**必ず UNO Q 側で先にアンインストールしてから**新トークンで入れ直す。

```bash
sudo cloudflared service uninstall
sudo cloudflared service install <NEW_CONNECTOR_TOKEN>
```

### ⚠️ Tunnel化に伴うクールダウンの注意（v1.2.1で対応済み）

Tunnel経由だと、Python側から見たアクセス元IPは全観客が `127.0.0.1`（cloudflared自身）になる。
そのため **IPベースのクールダウンだと全端末で共有されてしまい、最初の1人以降が全員ブロックされる**。
v1.2.1 では判定基準を **IPからブラウザ単位のCookie（`vibe_id`）** に変更してこれを解消済み。
詳細は「[クールダウンの仕組み](#クールダウンの仕組み)」を参照。

---

## Web UI — 3つのタブ

### Generate（観客向け）

プロンプトを入力して **Submit to Queue** を押すと、キューに追加される。

- 送信後 **60秒間クールダウン**（プログレスバーで残り時間を表示）※ブラウザ（スマホ1台）ごとに個別に効く（→[クールダウンの仕組み](#クールダウンの仕組み)）
- 6つのメトリクスカード（CV1〜CV6）に現在値を表示
  - 表示名は `python/ui_labels.json` の `cv_labels` で変更可能（ページ再読み込みで反映、アプリ再起動は不要）
  - CV番号とピンの対応は「[ピン接続](#ピン接続)」を参照
- **MIDI Auto** ボタンでオートモードに切り替え

### Sequencer（キュー表示）

現在のキューをリアルタイム表示（3秒ごと自動更新）。

- **NOW PLAYING**: 現在適用中のプロンプトとパルスアニメーション
- **#1, #2, #3...**: 待機中のプロンプト一覧
- キューから20秒ごとに先頭のプロンプトが自動的にポップされ、パッチとして適用される

### Settings（管理者向け）

パスワード（デフォルト: `vibeadmin`）を入力してログインすると、管理者コントロールが出現。

| 操作 | 説明 |
|---|---|
| **Instant Deploy** | キューを無視して即座にパッチを適用（クールダウンなし） |
| **Clear Queue** | キューを全消去 |
| **Skip to Next** | キューの先頭を今すぐ適用 |
| **MIDI Auto** | オートモードに切り替え |

---

## ライブパフォーマンスの流れ

```
1. ライブ開始前
   - UNO Qとvolca modularをパッチケーブルで接続
   - App Labからアプリを起動
   - アクセスURLを観客に共有
     - ローカル運用: 会場のWi-Fi情報 + `http://192.168.1.34:8080` 等
     - リモート運用: `https://vibe-patching.ocha-no-taiko.com`（Cloudflare Tunnel経由、Wi-Fi接続不要）

2. ライブ中
   観客A → "ドローン" を送信 → キュー#1（20秒後に適用 🔊）
   観客B → "グリッチノイズ" を送信 → キュー#2
   観客A → 再送信 → "Wait 42s" でブロック 🔒
   あなた → Settings → "怖い ambient" を即時Deploy（キュー無視）
   あなた → Clear Queue or Skip to Next で流れをコントロール

3. MIDIセッション
   あなた → MIDI Auto ボタン → キーボード演奏に合わせてAIが自律パッチング
```

---

## 音の生成ロジック

### LLM（メイン）
ローカルLLM（SmolLM2-360M, Q4量子化）がプロンプトから6つの数値を生成。

### プリセット（フォールバック）
LLMのパースに失敗した場合、キーワードマッチで即座にフォールバック。

| カテゴリ | キーワード |
|---|---|
| 打楽器 | kick / キック / snare / スネア / hihat / ハイハット / perc |
| ドローン | drone / ドローン / ambient / アンビエント / pad / 宇宙 / space |
| 攻撃的 | harsh / noise / ノイズ / glitch / グリッチ / distort / 歪み |
| メロディック | bell / ベル / pluck / bass / ベース / lead / リード |
| 質感 | metallic / メタリック / 木 / water / 水 / wind / 風 |
| 感情 | 怖い / scary / 楽しい / happy / 悲しい / sad / 怒り / angry / 穏やか |
| ネタ | バカ / crazy / やばい / max / 無音 / silent |

複数キーワードがマッチした場合は値をブレンド（平均）します。

---

## 設定値

`main.py` 先頭付近で変更可能：

| 変数 | デフォルト | 説明 |
|---|---|---|
| `ADMIN_PASSWORD` | `vibeadmin` | 管理者パスワード |
| `COOLDOWN_SECONDS` | `60` | 1ブラウザあたりのクールダウン秒数 |
| `QUEUE_INTERVAL` | `20` | キューから次のパッチを適用する間隔（秒） |
| `MODEL_PATH` | `/home/arduino/models/smollm2-360m-instruct.Q4_K_M.gguf` | LLMモデルのパス |

JSONで変更できるもの（書き換えるとアプリ再起動なしで反映）：

| ファイル | 内容 |
|---|---|
| `python/ui_labels.json` | Web UIのメトリクスカード表示名 |
| `python/sync_config.json` | SYNCクロックのON/OFFとステートごとのBPM |

---

## クールダウンの仕組み

「N秒ごとに1人1回」の連投防止を、**ブラウザ単位**で判定する。

- 初回アクセス時にランダムなトークンを Cookie（`vibe_id`, 24時間有効）としてブラウザに発行。
- 送信時はこの Cookie を識別子として `COOLDOWN_SECONDS` のクールダウンを適用する。
- Cookie が無い環境（直叩き等）のみ、アクセス元IPにフォールバック。

### なぜIPではなくCookieなのか

| 方式 | LAN直アクセス | Cloudflare Tunnel経由 |
|---|---|---|
| IPベース（v1.2.1以前） | スマホごとに別IP＝正常 | **全員 `127.0.0.1` 扱い → 最初の1人以降が全ブロック** |
| Cookieベース（v1.3〜） | スマホ1台=1人 ✅ | スマホ1台=1人 ✅（NAT/Tunnelの影響を受けない） |

キャリアの4G/5G（キャリアNAT）や会場Wi-Fiでは複数人が同一IPに見えるため、IP方式だと別人が巻き込まれてブロックされる。Cookie方式はこれを回避する。

### 制限（回避可能性）

Cookie方式は、**シークレットモード・Cookie削除・別ブラウザ**で送り直せば回避できる。ライブの公平性としては十分だが、「完全に1人1回・回避不可」を求める場合は入場時に配る一意コード（QR等）を必須にする方式が別途必要。

---

## オートモード（MIDI AI解釈）

MIDIキーボードの演奏に基づいてAIが自律的にパッチングを行います。

| ステート | 条件 | 挙動 | SYNCテンポ（初期値） |
|---|---|---|---|
| `CALM` | テンション低 | 穏やかなモジュレーション | 80 BPM |
| `RITUAL` | テンション中 + キック多 | リズミカルな反応 | 120 BPM |
| `PANIC` | テンション高 | 予測不能な荒々しい変化 | 170 BPM |
| `BROKEN` | テンション極高 + ランダム | 壊れた機械（急激なジャンプと沈黙） | 140 BPMを基準に不規則 |

---

## SYNCクロック出力

D2 から volca modular の SYNC IN にクロックパルスを出し、シーケンサーのテンポをAIステートに連動させる。

- **1パルス = シーケンサー1ステップ（16分音符）**。パルスは volca の SYNC OUT と同じ 15ms 幅。
- SYNC IN にケーブルが挿さっている間、volca modular は内部クロックを無視し、受け取ったパルスでのみステップを進める。
- ステートはMIDI演奏から常に推論されている（マニュアルモード中もテンポは変わる）。MIDI入力がなければテンションが下がり `CALM` のテンポになる。
- ステートが変わると、次のステップから新しいテンポになる。

### BROKEN のときの挙動

基準BPMをもとに、次の3つがランダムに混ざる。

| 確率 | 挙動 |
|---|---|
| 20% | 沈黙（0.5〜2秒パルスが止まる） |
| 30% | つんのめり（倍速） |
| 50% | よろめき（基準の半分〜2倍の間隔） |

### 設定（`python/sync_config.json`）

```json
{
  "enabled": true,
  "bpm": { "CALM": 80, "RITUAL": 120, "PANIC": 170, "BROKEN": 140 }
}
```

- `enabled` を `false` にするとパルスが止まる（volca 側は止まったままになるので、内部クロックに戻すにはケーブルを抜く）。
- BPMは 20〜300 の範囲に丸められる。書いていないステートや数値でない値は初期値になる。
- Python が起動時と JSON の更新時（2秒ごとにチェック）にマイコンへ送る。マイコン側の準備が終わるまでは自動で再送する。
- スケッチだけを書き直してマイコンが再起動した場合は、JSON を更新するまでマイコン内の初期値（上の値と同じ）で動く。

### 配線と電圧の注意

- UNO Q の D2 は **3.3V** 出力。volca の同期信号は通常 5V で、SYNC IN の最大入力は 20V なので壊れる心配はないが、**何V以上で反応するかは公式仕様に記載がない**。
- 3.3V でステップが進まない場合は、5V で動かしたバッファ（74AHCT125 など、3.3V入力を5Vとして受けられるもの）を D2 と SYNC IN の間に入れる。
- UNO Q と volca modular の GND は共通にする。

## ライセンス

個人利用・パフォーマンス利用を想定しています。
