#include "MidiHandler.h"

// ハードウェアシリアル（RX/TXピン）を使用
// Arduino UNO Q (および R4 等) では、ヘッダピンのRX(0)/TX(1)は一般的に Serial1 に割り当てられます
MIDI_CREATE_INSTANCE(HardwareSerial, Serial1, MIDI);

MidiHandler* MidiHandler::instance = nullptr;

MidiHandler::MidiHandler(FeatureExtractor& extractor) : featureExtractor(extractor) {
    instance = this;
}

void MidiHandler::begin() {
    MIDI.begin(MIDI_CHANNEL_OMNI);
    MIDI.setHandleNoteOn(handleNoteOn);
    MIDI.setHandleNoteOff(handleNoteOff);
}

void MidiHandler::update() {
    // 毎ループ呼び出してMIDIメッセージを処理
    MIDI.read();
}

void MidiHandler::handleNoteOn(byte channel, byte pitch, byte velocity) {
    if (instance) {
        // ベロシティ0のNoteOnはNoteOffとして扱われることがある
        if (velocity > 0) {
            instance->featureExtractor.registerNote(channel, pitch, velocity);
        }
    }
}

void MidiHandler::handleNoteOff(byte channel, byte pitch, byte velocity) {
    // 現状は発音時（NoteOn）の密度とベロシティのみを追跡するため、何もしない
}
