#include "SyncOutput.h"

SyncOutput::SyncOutput(int pin)
    // Python から sync_config.json が届くまでの初期値（JSONの初期値と同じ）
    : pin(pin), enabled(true), bpm(120),
      pulseHigh(false), pulseStartAt(0), lastStepAt(0) {}

void SyncOutput::begin() {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
}

void SyncOutput::update(unsigned long now) {
    // パルスを15msで下げる（無効化された直後でも必ず下げる）
    if (pulseHigh && now - pulseStartAt >= PULSE_MS) {
        digitalWrite(pin, LOW);
        pulseHigh = false;
    }
    if (!enabled) return;

    // 16分音符 = 4分音符の1/4。BPMが変わったら次のステップから新しいテンポになる
    unsigned long interval = 60000UL / (unsigned long)bpm / 4UL;
    if (now - lastStepAt < interval) return;
    // 実際に処理した時刻ではなく予定時刻から数える（loop()の周期ぶんの遅れを積み重ねない）
    lastStepAt += interval;
    // loop()のゆらぎを超えて遅れていたら（BPM変更・無効化の直後）、
    // 取り戻そうと間隔を詰めずに今から数え直す
    if (now - lastStepAt > LATE_TOLERANCE_MS) lastStepAt = now;

    digitalWrite(pin, HIGH);
    pulseHigh = true;
    pulseStartAt = now;
}

bool SyncOutput::setConfig(bool en, int newBpm) {
    int clamped = constrain(newBpm, BPM_MIN, BPM_MAX);
    bool changed = (en != enabled) || (clamped != bpm);
    bpm = clamped;
    enabled = en;
    return changed;
}

int SyncOutput::getBpm() const {
    return bpm;
}

bool SyncOutput::isEnabled() const {
    return enabled;
}
