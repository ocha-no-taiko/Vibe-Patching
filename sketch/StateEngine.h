#ifndef STATE_ENGINE_H
#define STATE_ENGINE_H

#include <Arduino.h>
#include "FeatureExtractor.h"

enum AIState {
    STATE_CALM,
    STATE_RITUAL,
    STATE_PANIC,
    STATE_BROKEN
};

class StateEngine {
public:
    StateEngine();
    void update(const FeatureExtractor& features);
    AIState getCurrentState() const;
    String getStateName() const;

private:
    AIState currentState;
    unsigned long lastTransitionTime;
    
    // Internal parameter determining state shift likelihood
    float tension;
};

#endif
