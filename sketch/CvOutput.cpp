#include "CvOutput.h"

CvOutput::CvOutput(int pitch, int fold, int mod, int woggle, int lpg, int spaceOut) 
    : pinPitch(pitch), pinFold(fold), pinMod(mod), pinWoggle(woggle), pinLPG(lpg), pinSpaceOut(spaceOut),
      currentPitch(0), targetPitch(0), currentFold(0), targetFold(0),
      currentMod(0), targetMod(0), currentWoggle(0), targetWoggle(0),
      currentLPG(0), targetLPG(0), currentSpaceOut(0), targetSpaceOut(0),
      isManualMode(false) {}

void CvOutput::begin() {
    pinMode(pinPitch, OUTPUT);
    pinMode(pinFold, OUTPUT);
    pinMode(pinMod, OUTPUT);
    pinMode(pinWoggle, OUTPUT);
    pinMode(pinLPG, OUTPUT);
    pinMode(pinSpaceOut, OUTPUT);
    
    // UNO Q は3.3Vロジックなので、0-255 で出力設定
    // アナログ書き込みの解像度を8bit(0-255)に明示的に設定（プラットフォーム依存対策）
    #if defined(ARDUINO_ARCH_MBED) || defined(ARDUINO_ARCH_RP2040) || defined(ARDUINO_UNOWIFI_REV2)
      analogWriteResolution(8);
    #endif
}

void CvOutput::update(const StateEngine& state, const FeatureExtractor& features) {
    AIState currentState = state.getCurrentState();
    
    // 状態とメトリクスに基づき、ターゲットとなるCV(PWM)の値を決定する (Auto mode)
    if (!isManualMode) {
        switch (currentState) {
            case STATE_CALM:
                // 穏やかなモジュレーション
                targetPitch = map(features.getVelocityAverage(), 0, 127, 60, 128);
                targetFold = 40;
                targetMod = 0;
                targetWoggle = 20;
                targetLPG = map(features.getVelocityAverage(), 0, 127, 20, 100);
                targetSpaceOut = 30;
                break;
                
            case STATE_RITUAL:
                // キックに反応してリズミカルな反応
                targetPitch = map(features.getVelocityAverage(), 0, 127, 40, 200);
                targetFold = map(features.getDensity(), 0, 10, 50, 180);
                if (random(10) > 7) targetMod = random(50, 150);
                targetWoggle = features.isKickHeavy() ? random(80, 180) : 40;
                targetLPG = features.isKickHeavy() ? 200 : 80;
                targetSpaceOut = map(features.getDensity(), 0, 10, 20, 120);
                break;
                
            case STATE_PANIC:
                // 予測不可能な荒々しい変化
                targetPitch = random(0, 255);
                targetFold = map(features.getVelocityAverage(), 0, 127, 100, 255);
                targetMod = random(0, 255);
                targetWoggle = random(100, 255);
                targetLPG = random(100, 255);
                targetSpaceOut = random(50, 255);
                break;
                
            case STATE_BROKEN:
                // 壊れた機械のような極端なジャンプや沈黙
                if (random(100) > 80) {
                    targetPitch = 255;
                    targetFold = 255;
                    targetMod = 255;
                    targetWoggle = 255;
                    targetLPG = 255;
                    targetSpaceOut = 255;
                } else {
                    targetPitch = 0;
                    targetFold = 0;
                    targetMod = 0;
                    targetWoggle = 0;
                    targetLPG = 0;
                    targetSpaceOut = 0;
                }
                break;
        }
    }
    
    // スルーレート制限（滑らかな変化）の実装
    // BROKEN の時は滑らかさを無視して急激に変化させる
    float slewRate = (currentState == STATE_BROKEN) ? 1.0f : 0.05f;
    
    currentPitch += (targetPitch - currentPitch) * slewRate;
    currentFold += (targetFold - currentFold) * slewRate;
    currentMod += (targetMod - currentMod) * slewRate;
    currentWoggle += (targetWoggle - currentWoggle) * slewRate;
    currentLPG += (targetLPG - currentLPG) * slewRate;
    currentSpaceOut += (targetSpaceOut - currentSpaceOut) * slewRate;
    
    // 実際のピンへの書き込み
    analogWrite(pinPitch, (int)currentPitch);
    analogWrite(pinFold, (int)currentFold);
    analogWrite(pinMod, (int)currentMod);
    analogWrite(pinWoggle, (int)currentWoggle);
    analogWrite(pinLPG, (int)currentLPG);
    analogWrite(pinSpaceOut, (int)currentSpaceOut);
}

void CvOutput::setMode(bool manual) {
    isManualMode = manual;
}

void CvOutput::setManualTargets(int pitch, int fold, int mod, int woggle, int lpg, int spaceOut) {
    targetPitch = constrain(pitch, 0, 255);
    targetFold = constrain(fold, 0, 255);
    targetMod = constrain(mod, 0, 255);
    targetWoggle = constrain(woggle, 0, 255);
    targetLPG = constrain(lpg, 0, 255);
    targetSpaceOut = constrain(spaceOut, 0, 255);
}
