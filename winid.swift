// Prints the window number of the largest TFWR game window (works across Spaces/fullscreen).
import CoreGraphics
let list = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]] ?? []
var best = (id: 0, area: 0.0)
for w in list where (w[kCGWindowOwnerName as String] as? String ?? "").contains("TheFarmerWasReplaced")
                  && (w[kCGWindowLayer as String] as? Int ?? -1) == 0 {
  let b = w[kCGWindowBounds as String] as? [String: Double] ?? [:]
  let area = (b["Width"] ?? 0) * (b["Height"] ?? 0)
  if area > best.area { best = (w[kCGWindowNumber as String] as? Int ?? 0, area) }
}
if best.id > 0 { print(best.id) }
