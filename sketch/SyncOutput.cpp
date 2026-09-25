#include "SyncOutput.h"

SyncOutput::SyncOutput(int pin)
    : pin(pin), enabled(true), pulseHigh(false),
      pulseStartAt(0), lastStepAt(0), brokenIntervalMs(0) {
    // Python から sync_config.json が届くまでの初期値（JSONの初期値と同じ）
    bpm[STATE_CALM]   = 80;
    bpm[STATE_RITUAL] = 120;
    bpm[STATE_PANIC]  = 170;
    bpm[STATE_BROKEN] = 140;
}

void SyncOutput::begin() {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
}

unsigned long SyncOutput::stepMs(AIState state) const {
    // 16分音符 = 4分音符の1/4
    return 60000UL / (unsigned long)bpm[state] / 4UL;
}

void SyncOutput::firePulse(unsigned long now) {
    digitalWrite(pin, HIGH);
    pulseHigh = true;
    pulseStartAt = now;
}

void SyncOutput::update(AIState state, unsigned long now) {
    // パルスを15msで下げる（無効化された直後でも必ず下げる）
    if (pulseHigh && now - pulseStartAt >= PULSE_MS) {
        digitalWrite(pin, LOW);
        pulseHigh = false;
    }
    if (!enabled) return;

    // ステートが変わったら、次のステップから新しいテンポになる
    unsigned long interval = (state == STATE_BROKEN && brokenIntervalMs > 0)
                                 ? brokenIntervalMs
                                 : stepMs(state);
    if (now - lastStepAt < interval) return;
    // 実際に処理した時刻ではなく予定時刻から数える（loop()の周期ぶんの遅れを積み重ねない）
    lastStepAt += interval;
    // loop()のゆらぎを超えて遅れていたら（ステート切替・無効化・沈黙の直後）、
    // 取り戻そうと間隔を詰めずに今から数え直す
    if (now - lastStepAt > LATE_TOLERANCE_MS) lastStepAt = now;

    if (state != STATE_BROKEN) {
        brokenIntervalMs = 0;
        firePulse(now);
        return;
    }

    // BROKEN: 壊れた機械のように、沈黙・つんのめり・よろめきをランダムに混ぜる
    unsigned long base = stepMs(STATE_BROKEN);
    long r = random(100);
    if (r < 20) {
        // 沈黙: パルスを出さず 0.5〜2秒止まる
        brokenIntervalMs = random(500, 2000);
        return;
    }
    if (r < 50) {
        // つんのめり: 倍速
        brokenIntervalMs = base / 2;
    } else {
        // よろめき: 半分〜2倍の間でランダム
        brokenIntervalMs = random((long)(base / 2), (long)(base * 2));
    }
    if (brokenIntervalMs < PULSE_MS * 2) brokenIntervalMs = PULSE_MS * 2;
    firePulse(now);
}

void SyncOutput::setConfig(bool en, int bpmCalm, int bpmRitual, int bpmPanic, int bpmBroken) {
    bpm[STATE_CALM]   = constrain(bpmCalm,   BPM_MIN, BPM_MAX);
    bpm[STATE_RITUAL] = constrain(bpmRitual, BPM_MIN, BPM_MAX);
    bpm[STATE_PANIC]  = constrain(bpmPanic,  BPM_MIN, BPM_MAX);
    bpm[STATE_BROKEN] = constrain(bpmBroken, BPM_MIN, BPM_MAX);
    enabled = en;
}

int SyncOutput::getBpm(AIState state) const {
    return bpm[state];
}

bool SyncOutput::isEnabled() const {
    return enabled;
}
