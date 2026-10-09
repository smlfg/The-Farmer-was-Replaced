// Starter für den LaunchAgent: eigene App-Identität, damit macOS die Bildschirmaufnahme
// gezielt dieser App erlaubt (statt jedem Python). Startet tutor.py als Kindprozess.
import Foundation

let args = CommandLine.arguments
guard args.count >= 2 else { FileHandle.standardError.write("tutor.py-Pfad fehlt\n".data(using: .utf8)!); exit(2) }
let child = Process()
child.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
child.arguments = [args[1], "run"]
for sig in [SIGTERM, SIGINT] {
  signal(sig, SIG_IGN)
  let src = DispatchSource.makeSignalSource(signal: sig, queue: .main)
  src.setEventHandler { child.terminate() }
  src.resume()
  _ = Unmanaged.passRetained(src)
}
child.terminationHandler = { p in exit(p.terminationStatus) }
try child.run()
dispatchMain()
