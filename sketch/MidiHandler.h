#ifndef MIDI_HANDLER_H
#define MIDI_HANDLER_H

#include <Arduino.h>
#include <MIDI.h>
#include "FeatureExtractor.h"

class MidiHandler {
public:
    MidiHandler(FeatureExtractor& extractor);
    void begin();
    void update();

private:
    FeatureExtractor& featureExtractor;
    
    // ArduinoのMIDIライブラリのコールバック用の静的ポインタ
    static MidiHandler* instance;
    
    static void handleNoteOn(byte channel, byte pitch, byte velocity);
    static void handleNoteOff(byte channel, byte pitch, byte velocity);
};

#endif
