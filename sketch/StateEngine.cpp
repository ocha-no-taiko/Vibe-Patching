#include "StateEngine.h"

StateEngine::StateEngine() : currentState(STATE_CALM), lastTransitionTime(0), tension(0) {}

void StateEngine::update(const FeatureExtractor& features) {
    unsigned long now = millis();
    
    // 状態が頻繁に変わりすぎるのを防ぐ (最短遷移間隔 3秒)
    if (now - lastTransitionTime < 3000) return;

    AIState nextState = currentState;
    
    float density = features.getDensity();
    float velocity = features.getVelocityAverage();
    bool kickHeavy = features.isKickHeavy();

    // テンションの計算（入力が激しいと上がり、静かだと下がる）
    if (density > 5.0f || velocity > 100.0f) {
        tension += 10.0f;
    } else {
        tension -= 5.0f;
    }
    tension = constrain(tension, 0.0f, 100.0f);

    // 状態遷移のロジック（人工知能的な振る舞い）
    switch (currentState) {
        case STATE_CALM:
            if (tension > 50.0f && kickHeavy) {
                // テンションが上がってキックが強い場合、儀式モードへ
                nextState = STATE_RITUAL;
            } else if (tension > 80.0f) {
                nextState = STATE_PANIC;
            }
            break;
            
        case STATE_RITUAL:
            if (tension < 30.0f) {
                nextState = STATE_CALM;
            } else if (tension > 90.0f && random(10) > 6) {
                // さらに激しくなると時々パニックになる
                nextState = STATE_PANIC;
            }
            break;
            
        case STATE_PANIC:
            if (tension < 40.0f) {
                nextState = STATE_CALM;
            } else if (random(100) > 95) {
                // パニックが長引くとたまに壊れる
                nextState = STATE_BROKEN;
            }
            break;
            
        case STATE_BROKEN:
            if (tension < 20.0f && random(10) > 5) {
                // 静かになると再起動するように元に戻る
                nextState = STATE_CALM;
            }
            break;
    }

    // 遷移が発生した場合
    if (nextState != currentState) {
        // 20%の確率で、人間を無視して遷移をサボる（自律性の演出）
        if (random(100) > 20) {
            currentState = nextState;
            lastTransitionTime = now;
        }
    }
}

AIState StateEngine::getCurrentState() const {
    return currentState;
}

String StateEngine::getStateName() const {
    switch(currentState) {
        case STATE_CALM: return "CALM";
        case STATE_RITUAL: return "RITUAL";
        case STATE_PANIC: return "PANIC";
        case STATE_BROKEN: return "BROKEN";
        default: return "UNKNOWN";
    }
}
