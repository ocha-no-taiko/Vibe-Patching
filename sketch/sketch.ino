#include <Arduino.h>
#include "FeatureExtractor.h"
#include "StateEngine.h"
#include "CvOutput.h"
#include "MidiHandler.h"
#include "Arduino_RouterBridge.h"

// 各モジュールのインスタンス生成
FeatureExtractor featureExtractor;
StateEngine stateEngine;
MidiHandler midiHandler(featureExtractor);

// PWM/CV出力ピンの割り当て（UNO QのPWM対応ピンを指定）
const int PIN_CV_PITCH    = 3;
const int PIN_CV_FOLD     = 5;
const int PIN_CV_MOD      = 6;
const int PIN_CV_WOGGLE   = 9;
const int PIN_CV_LPG      = 10;
const int PIN_CV_SPACEOUT = 11;

CvOutput cvOutput(PIN_CV_PITCH, PIN_CV_FOLD, PIN_CV_MOD, PIN_CV_WOGGLE, PIN_CV_LPG, PIN_CV_SPACEOUT);

unsigned long lastDebugPrint = 0;

// RPC 関数
void apply_manual_patch(String params) {
    int p, f, m, w, l, s;
    if (sscanf(params.c_str(), "%d,%d,%d,%d,%d,%d", &p, &f, &m, &w, &l, &s) == 6) {
        cvOutput.setManualTargets(p, f, m, w, l, s);
        cvOutput.setMode(true);
        Serial.print("Manual Patch Applied: PITCH=");
        Serial.print(p);
        Serial.print(" FOLD=");
        Serial.print(f);
        Serial.print(" MOD=");
        Serial.print(m);
        Serial.print(" WOGGLE=");
        Serial.print(w);
        Serial.print(" LPG=");
        Serial.print(l);
        Serial.print(" SPACEOUT=");
        Serial.println(s);
    } else {
        Serial.println("Invalid manual patch format. Expected: 'PITCH,FOLD,MOD,WOGGLE,LPG,SPACEOUT'");
    }
}

void enable_auto_mode(String msg) {
    cvOutput.setMode(false);
    Serial.println("Auto Mode Enabled!");
}

void setup() {
    // USB経由のシリアルモニタ出力用
    Serial.begin(115200);
    delay(2000); // シリアル接続待機
    
    Serial.println("†Vibe-Patching† AI Performance System Starting...");
    
    // システムの初期化
    cvOutput.begin();
    midiHandler.begin(); // これによりSerial1(MIDI受信用)も初期化される
    
    // Bridge (App Lab Pythonとの通信) 初期化
    Bridge.begin();
    Bridge.provide("apply_manual_patch", apply_manual_patch);
    Bridge.provide("enable_auto_mode", enable_auto_mode);
    
    Serial.println("Initialization complete. Listening for MIDI on RX pin...");
}

void loop() {
    unsigned long now = millis();
    
    
    // 1. MIDIメッセージの読み取りと特徴（メトリクス）の更新
    midiHandler.update();
    featureExtractor.update(now);
    
    // 2. AIによる状態（人格）の推論
    stateEngine.update(featureExtractor);
    
    // 3. 現在の状態と特徴に基づくCV（PWM）の生成・出力
    cvOutput.update(stateEngine, featureExtractor);
    
    // 500msごとにシリアルモニタに状態を報告
    if (now - lastDebugPrint > 500) {
        Serial.print("State: ");
        Serial.print(stateEngine.getStateName());
        Serial.print(" | Density: ");
        Serial.print(featureExtractor.getDensity());
        Serial.print(" | Avg Vel: ");
        Serial.print(featureExtractor.getVelocityAverage());
        Serial.print(" | KickHeavy: ");
        Serial.println(featureExtractor.isKickHeavy() ? "YES" : "NO");
        
        lastDebugPrint = now;
    }
    
    // マイコンへの過負荷を防ぐための短いウェイト
    delay(2);
}
