// macOS native global push-to-talk helper. Hold right Option (keycode 61).
// Event tap requires Input Monitoring/Accessibility permission for the executable.
import Cocoa
import ApplicationServices
import AVFoundation
import Foundation

let state = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent(".tfwr-tutor")
try? FileManager.default.createDirectory(at: state, withIntermediateDirectories: true)
let events = state.appendingPathComponent("ptt-events.jsonl")
let recording = state.appendingPathComponent("ptt-recording.wav")
let audio = AVAudioEngine()
var file: AVAudioFile?
var down = false
var active = false
let code: Int64 = Int64(ProcessInfo.processInfo.environment["TUTOR_PTT_KEYCODE"] ?? "61") ?? 61

func emit(_ event: String, _ extra: String? = nil) {
    var dict = ["event": event, "time": String(Date().timeIntervalSince1970)]
    if let extra = extra { dict["detail"] = extra }
    guard let data = try? JSONSerialization.data(withJSONObject: dict),
          let s = String(data: data, encoding: .utf8) else { return }
    if let handle = try? FileHandle(forWritingTo: events) {
        handle.seekToEndOfFile()
        handle.write(Data((s + "\n").utf8))
        try? handle.close()
    } else { try? Data((s + "\n").utf8).write(to: events) }
}

func tone(_ frequency: Double) {
    // Asynchronous system sound, completed BEFORE opening microphone.
    NSSound.beep()
}
func begin() {
    guard !down else { return }
    down = true
    emit("down")
    tone(660)
    guard AVCaptureDevice.authorizationStatus(for: .audio) == .authorized else {
        emit("error", "Mikrofon nicht freigegeben"); return
    }
    let input = audio.inputNode
    let fmt = input.outputFormat(forBus: 0)
    do {
        file = try AVAudioFile(forWriting: recording, settings: fmt.settings)
        input.installTap(onBus: 0, bufferSize: 1024, format: fmt) { buf, _ in
            try? selfWrite(buf)
        }
        try audio.start()
        active = true
        emit("recording")
    } catch {
        input.removeTap(onBus: 0)
        emit("error", "Aufnahme fehlgeschlagen: \(error.localizedDescription)")
    }
}
func selfWrite(_ buf: AVAudioPCMBuffer) throws { try file?.write(from: buf) }
func finish() {
    guard down else { return }
    down = false
    if active {
        audio.stop()
        audio.inputNode.removeTap(onBus: 0)
        file = nil
        active = false
        emit("up", recording.path)
    }
    tone(440)
}
let mask = CGEventMask(1 << CGEventType.flagsChanged.rawValue)
guard let tap = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap,
       options: .listenOnly, eventsOfInterest: mask, callback: { _, _, event, _ in
    if Int64(event.getIntegerValueField(.keyboardEventKeycode)) == code {
        let pressed = event.flags.contains(.maskAlternate)
        if pressed { begin() } else { finish() }
    }
    return Unmanaged.passUnretained(event)
}, userInfo: nil) else {
    emit("error", "Globaler Hotkey benötigt Eingabeüberwachung oder Bedienungshilfen")
    exit(3)
}
CGEvent.tapEnable(tap: tap, enable: true)
let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
CFRunLoopAddSource(CFRunLoopGetCurrent(), source, .commonModes)
emit("ready")
CFRunLoopRun()
