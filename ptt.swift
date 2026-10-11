// macOS native global push-to-talk helper. Hold right Option (keycode 61).
// Event tap requires Input Monitoring/Accessibility permission for the executable.
import Cocoa
import ApplicationServices
import AVFoundation
import Speech
import Foundation

let state = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent(".tfwr-tutor")
try? FileManager.default.createDirectory(at: state, withIntermediateDirectories: true)
let events = state.appendingPathComponent("ptt-events.jsonl")
let audio = AVAudioEngine()
// Permission prompts require signed app attribution on target macOS.
SFSpeechRecognizer.requestAuthorization { status in
    if status != .authorized { emit("error", "Spracherkennung nicht freigegeben") }
}
var file: AVAudioFile?
var currentRecording: URL?
var down = false
var active = false
var opening = false  // Startsignal läuft, Mikrofon noch zu
var openGen = 0
let code: Int64 = Int64(ProcessInfo.processInfo.environment["TUTOR_PTT_KEYCODE"] ?? "61") ?? 61

// Device-dependent modifier bits (NX_DEVICE*KEYMASK). The shared maskAlternate
// bit stays set while the other Option key is held, so a right-Option release
// must be read from the right-Option bit alone.
func heldBit(_ keycode: Int64) -> CGEventFlags {
    switch keycode {
    case 58: return CGEventFlags(rawValue: 0x00000020) // left Option
    case 61: return CGEventFlags(rawValue: 0x00000040) // right Option
    case 56: return CGEventFlags(rawValue: 0x00000002) // left Shift
    case 60: return CGEventFlags(rawValue: 0x00000004) // right Shift
    case 59: return CGEventFlags(rawValue: 0x00000001) // left Control
    case 62: return CGEventFlags(rawValue: 0x00002000) // right Control
    case 55: return CGEventFlags(rawValue: 0x00000008) // left Command
    case 54: return CGEventFlags(rawValue: 0x00000010) // right Command
    default: return .maskAlternate
    }
}
let held = heldBit(code)

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

func le16(_ v: UInt16) -> [UInt8] { [UInt8(v & 0xff), UInt8(v >> 8)] }
func le32(_ v: UInt32) -> [UInt8] {
    [UInt8(v & 0xff), UInt8((v >> 8) & 0xff), UInt8((v >> 16) & 0xff), UInt8(v >> 24)]
}
func writeTone(_ frequency: Double, to url: URL) throws {
    let rate = 22050
    let n = rate / 8  // 0.125 s
    var pcm = Data(capacity: n * 2)
    for i in 0..<n {
        let env = min(1.0, min(Double(i) / 60.0, Double(n - i) / 60.0))
        let s = Int16(sin(2 * Double.pi * frequency * Double(i) / Double(rate)) * env * 8000)
        let u = UInt16(bitPattern: s)
        pcm.append(contentsOf: [UInt8(u & 0xff), UInt8(u >> 8)])
    }
    let dataLen = UInt32(pcm.count)
    var data = Data()
    data.append(contentsOf: [0x52, 0x49, 0x46, 0x46]) // RIFF
    data.append(contentsOf: le32(UInt32(36) + dataLen))
    data.append(contentsOf: [0x57, 0x41, 0x56, 0x45, 0x66, 0x6d, 0x74, 0x20]) // WAVE fmt
    data.append(contentsOf: le32(16))
    data.append(contentsOf: le16(1)) // PCM
    data.append(contentsOf: le16(1)) // mono
    data.append(contentsOf: le32(UInt32(rate)))
    data.append(contentsOf: le32(UInt32(rate * 2)))
    data.append(contentsOf: le16(2))
    data.append(contentsOf: le16(16))
    data.append(contentsOf: [0x64, 0x61, 0x74, 0x61]) // data
    data.append(contentsOf: le32(dataLen))
    data.append(pcm)
    try data.write(to: url)
}

var cueCache: [Int: NSSound] = [:]
func cue(_ frequency: Double) -> NSSound? {
    let key = Int(frequency)
    if let s = cueCache[key] { return s }
    let url = state.appendingPathComponent("ptt-tone-\(key).wav")
    if !FileManager.default.fileExists(atPath: url.path) {
        try? writeTone(frequency, to: url)
    }
    guard let s = NSSound(contentsOf: url, byReference: true) else { return nil }
    cueCache[key] = s
    return s
}

// Startet den Ton und liefert, wie lange das Mikrofon noch zu bleiben muss.
func tone(_ frequency: Double) -> Double {
    if let s = cue(frequency) {
        s.stop()
        if s.play() { return max(s.duration, 0.12) }
    }
    NSSound.beep()
    return 0.35
}
func begin() {
    guard !down else { return }
    down = true
    emit("down")
    guard AVCaptureDevice.authorizationStatus(for: .audio) == .authorized else {
        emit("error", "Mikrofon nicht freigegeben"); return
    }
    opening = true
    openGen += 1
    let gen = openGen
    cue(440)?.stop()
    let wait = tone(660)
    // Timer on this run loop, not a blocking sleep: the cue plays out before the mic opens.
    Timer.scheduledTimer(withTimeInterval: wait + 0.05, repeats: false) { _ in
        guard gen == openGen else { return }
        openMic()
    }
}
func openMic() {
    guard down, opening else { return }
    opening = false
    cue(660)?.stop()
    cue(440)?.stop()
    let input = audio.inputNode
    let fmt = input.outputFormat(forBus: 0)
    let path = state.appendingPathComponent("ptt-\(UUID().uuidString).wav")
    do {
        file = try AVAudioFile(forWriting: path, settings: fmt.settings)
        currentRecording = path
        input.installTap(onBus: 0, bufferSize: 1024, format: fmt) { buf, _ in
            try? selfWrite(buf)
        }
        try audio.start()
        active = true
        emit("recording")
    } catch {
        input.removeTap(onBus: 0)
        file = nil
        currentRecording = nil
        emit("error", "Aufnahme fehlgeschlagen: \(error.localizedDescription)")
    }
}
func selfWrite(_ buf: AVAudioPCMBuffer) throws { try file?.write(from: buf) }
func finish() {
    guard down else { return }
    down = false
    let cancelled = opening
    opening = false
    openGen += 1  // verzögertes openMic dieser Taste verwerfen
    cue(660)?.stop()
    if active {
        audio.stop()
        audio.inputNode.removeTap(onBus: 0)
        let path = currentRecording?.path ?? ""
        file = nil
        currentRecording = nil
        active = false
        emit("up", path)
    } else if cancelled {
        emit("error", "Taste losgelassen bevor die Aufnahme begann")
    }
    _ = tone(440)
}
let mask = CGEventMask(1 << CGEventType.flagsChanged.rawValue)
guard let tap = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap,
       options: .listenOnly, eventsOfInterest: mask, callback: { _, _, event, _ in
    if Int64(event.getIntegerValueField(.keyboardEventKeycode)) == code {
        let pressed = event.flags.contains(held)
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
