// Push-to-Talk-Lauscher: meldet auf stdout DOWN/UP der Sprechtaste und OTHER, wenn währenddessen
// eine andere Taste gedrückt wird. Nur mithören (listenOnly): stiehlt keine Tasten, ändert keinen Fokus.
// Läuft als Kind von „TFWR Tutor.app“, damit die Eingabeüberwachung dieser App gilt.
import CoreGraphics
import Foundation

setvbuf(stdout, nil, _IOLBF, 0)
let key = Int64(CommandLine.arguments.count > 1 ? Int(CommandLine.arguments[1]) ?? 61 : 61)  // 61 = rechte Wahltaste
let flagFor: [Int64: CGEventFlags] = [61: .maskAlternate, 58: .maskAlternate, 54: .maskCommand, 55: .maskCommand,
                                      59: .maskControl, 62: .maskControl, 56: .maskShift, 60: .maskShift, 63: .maskSecondaryFn]
let flag = flagFor[key] ?? .maskAlternate
var isDown = false
var tap: CFMachPort?

if !CGPreflightListenEventAccess() {
  _ = CGRequestListenEventAccess()
  print("NOPERM")
}

let mask = (1 << CGEventType.flagsChanged.rawValue) | (1 << CGEventType.keyDown.rawValue)
let callback: CGEventTapCallBack = { _, type, event, _ in
  if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
    if let t = tap { CGEvent.tapEnable(tap: t, enable: true) }
    return Unmanaged.passUnretained(event)
  }
  let code = event.getIntegerValueField(.keyboardEventKeycode)
  if type == .flagsChanged && code == key {
    let now = event.flags.contains(flag)
    if now != isDown { isDown = now; print(now ? "DOWN" : "UP") }
  } else if type == .keyDown && isDown {
    print("OTHER")
  }
  return Unmanaged.passUnretained(event)
}

tap = CGEvent.tapCreate(tap: .cgSessionEventTap, place: .headInsertEventTap, options: .listenOnly,
                        eventsOfInterest: CGEventMask(mask), callback: callback, userInfo: nil)
guard let t = tap else { print("NOPERM"); exit(3) }
let src = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, t, 0)
CFRunLoopAddSource(CFRunLoopGetCurrent(), src, .commonModes)
CGEvent.tapEnable(tap: t, enable: true)
print("READY")
CFRunLoopRun()
