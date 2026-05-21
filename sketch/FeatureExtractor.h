#ifndef FEATURE_EXTRACTOR_H
#define FEATURE_EXTRACTOR_H

#include <Arduino.h>

class FeatureExtractor {
public:
    FeatureExtractor();
    void update(unsigned long currentTime);
    void registerNote(uint8_t channel, uint8_t pitch, uint8_t velocity);
    
    // 抽出された特徴（メトリクス）
    float getDensity() const;         // 全体的なノート密度（1秒あたりのノート数）
    float getVelocityAverage() const; // 平均ベロシティ
    bool isKickHeavy() const;         // キックが連続しているかどうか
    
private:
    static const int WINDOW_SIZE_MS = 2000; // 2秒の移動窓で計算
    unsigned long windowStartTime;
    
    // 密度トラッキング
    int noteCountInWindow;
    float currentDensity;
    
    // ベロシティトラッキング
    long totalVelocity;
    long velocityCount;
    float currentVelocityAverage;
    
    // キック検出トラッキング
    int kickCountInWindow;
    bool kickHeavyFlag;
};

#endif
