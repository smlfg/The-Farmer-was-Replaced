// Offline German recognition using Apple's Speech framework.
// Usage: ./ptt-transcribe /path/to/recording.wav
import Foundation
import Speech
import AVFoundation

guard CommandLine.arguments.count == 2 else { exit(2) }
let locale = Locale(identifier: "de-DE")
let recognizer = SFSpeechRecognizer(locale: locale)
guard let recognizer = recognizer, recognizer.isAvailable, recognizer.supportsOnDeviceRecognition else {
    fputs("Lokale Spracherkennung für de-DE ist nicht verfügbar\n", stderr); exit(3)
}
let sem = DispatchSemaphore(value: 0)
var transcript = ""
var failure: Error?
let request = SFSpeechURLRecognitionRequest(url: URL(fileURLWithPath: CommandLine.arguments[1]))
request.requiresOnDeviceRecognition = true
request.shouldReportPartialResults = false
let task = recognizer.recognitionTask(with: request) { result, error in
    if let result = result {
        transcript = result.bestTranscription.formattedString
        if result.isFinal { sem.signal() }
    } else if let error = error { failure = error; sem.signal() }
}
if sem.wait(timeout: .now() + 20) == .timedOut {
    task.cancel(); fputs("Timeout bei lokaler Transkription\n", stderr); exit(4)
}
if let failure = failure {
    fputs("\(failure.localizedDescription)\n", stderr); exit(5)
}
print(transcript)
