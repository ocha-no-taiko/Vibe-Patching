#ifndef CV_OUTPUT_H
#define CV_OUTPUT_H

#include <Arduino.h>
#include "StateEngine.h"
#include "FeatureExtractor.h"

class CvOutput {
public:
    CvOutput(int pinPitch, int pinFold, int pinMod, int pinWoggle, int pinLPG, int pinSpaceOut);
    void begin();
    void update(const StateEngine& state, const FeatureExtractor& features);
    void setMode(bool manual);
    void setManualTargets(int pitch, int fold, int mod, int woggle, int lpg, int spaceOut);

private:
    int pinPitch;
    int pinFold;
    int pinMod;
    int pinWoggle;
    int pinLPG;
    int pinSpaceOut;
    
    // スルー（滑らかな変化）のための目標値と現在値
    float currentPitch, targetPitch;
    float currentFold, targetFold;
    float currentMod, targetMod;
    float currentWoggle, targetWoggle;
    float currentLPG, targetLPG;
    float currentSpaceOut, targetSpaceOut;
    
    bool isManualMode;
};

#endif
