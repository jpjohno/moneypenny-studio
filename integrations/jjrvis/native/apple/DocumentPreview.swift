// Owner-selected PDFs only. Read bounded input on stdin; emit metadata or a page PNG.
import AppKit
import PDFKit
import Foundation
let data = FileHandle.standardInput.readDataToEndOfFile()
guard data.count <= 20_000_000, let document = PDFDocument(data: data), !document.isLocked else { exit(2) }
let args = CommandLine.arguments
if args.count == 1 {
    var text = ""
    var truncated = false
    for index in 0..<min(document.pageCount, 200) {
        if text.count >= 60_000 { truncated = true; break }
        if let words = document.page(at: index)?.string {
            text += String(words.prefix(60_000 - text.count)) + "\n\n"
        }
    }
    let value: [String: Any] = ["pages": document.pageCount, "text": String(text.prefix(60_000)), "truncated": truncated || document.pageCount > 200]
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: value))
} else {
    guard let index = Int(args[1]), index >= 0, index < min(document.pageCount, 200), let page = document.page(at: index) else { exit(3) }
    let image = page.thumbnail(of: NSSize(width: 1200, height: 1600), for: .mediaBox)
    guard let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff), let png = bitmap.representation(using: .png, properties: [:]) else { exit(4) }
    FileHandle.standardOutput.write(png)
}
