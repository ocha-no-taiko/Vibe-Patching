#ifndef SYNC_OUTPUT_H
#define SYNC_OUTPUT_H

#include <Arduino.h>
#include "StateEngine.h"

// volca の SYNC IN 用クロック出力。1パルス = シーケンサー1ステップ（16分音符）。
// テンポはAIステートごとのBPMで決まり、BROKEN のときだけ不規則になる。
class SyncOutput {
public:
    SyncOutput(int pin);
    void begin();
    void update(AIState state, unsigned long now);
    void setConfig(bool enabled, int bpmCalm, int bpmRitual, int bpmPanic, int bpmBroken);
    int getBpm(AIState state) const;
    bool isEnabled() const;

private:
    // volca の SYNC OUT と同じ 15ms 幅
    static const unsigned long PULSE_MS = 15;
    // loop() は1周 2〜3ms。これ以内の遅れだけ次のステップで取り戻す
    static const unsigned long LATE_TOLERANCE_MS = 10;
    // BPM 300 でも1ステップ 50ms あり、パルス幅(15ms)より十分長い
    static const int BPM_MIN = 20;
    static const int BPM_MAX = 300;

    int pin;
    // Bridge の RPC スレッドから書き換えられる
    volatile bool enabled;
    volatile int bpm[4];

    bool pulseHigh;
    unsigned long pulseStartAt;
    unsigned long lastStepAt;
    unsigned long brokenIntervalMs;

    unsigned long stepMs(AIState state) const;
    void firePulse(unsigned long now);
};

#endif
