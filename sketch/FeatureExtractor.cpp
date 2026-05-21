#include "FeatureExtractor.h"

FeatureExtractor::FeatureExtractor() 
    : windowStartTime(0), noteCountInWindow(0), currentDensity(0),
      totalVelocity(0), velocityCount(0), currentVelocityAverage(0),
      kickCountInWindow(0), kickHeavyFlag(false) {}

void FeatureExtractor::update(unsigned long currentTime) {
    if (currentTime - windowStartTime >= WINDOW_SIZE_MS) {
        // 過去のウィンドウ（例: 2秒間）のメトリクスを計算
        currentDensity = (float)noteCountInWindow / (WINDOW_SIZE_MS / 1000.0f);
        
        if (velocityCount > 0) {
            currentVelocityAverage = (float)totalVelocity / velocityCount;
        } else {
            // ノート入力がない場合は少しずつ減衰させても良いが、今回は0リセット
            currentVelocityAverage *= 0.5f; 
        }
        
        // 2秒間に5回以上強い低音が鳴ったら「キックヘビー」と判定
        kickHeavyFlag = (kickCountInWindow >= 5);
        
        // 次の計算に向けてウィンドウをリセット
        windowStartTime = currentTime;
        noteCountInWindow = 0;
        totalVelocity = 0;
        velocityCount = 0;
        kickCountInWindow = 0;
    }
}

void FeatureExtractor::registerNote(uint8_t channel, uint8_t pitch, uint8_t velocity) {
    noteCountInWindow++;
    totalVelocity += velocity;
    velocityCount++;
    
    // 発見的アプローチ: ノート番号48(C3)未満でベロシティが強いものをキックとみなす
    // ※ 実際の運用では Tracker 側と合わせて調整可能
    if (pitch < 48 && velocity > 80) {
        kickCountInWindow++;
    }
}

float FeatureExtractor::getDensity() const {
    return currentDensity;
}

float FeatureExtractor::getVelocityAverage() const {
    return currentVelocityAverage;
}

bool FeatureExtractor::isKickHeavy() const {
    return kickHeavyFlag;
}
