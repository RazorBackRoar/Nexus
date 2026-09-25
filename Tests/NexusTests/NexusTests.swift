import Foundation
import Testing
@testable import Nexus

@Test func roundTripsBookmarkShapes() throws {
    let nodes: [LibraryNode] = [
        .folder(FolderNode(name: "Tech", accent: "#5B8DEF", children: [
            .bookmark(BookmarkItem(name: "Example", url: "https://example.com", accent: nil)),
            .group(GroupMarker(id: "stable-id")),
            .quickSave(QuickSaveEntry(id: "qs-1", createdAt: "2026-09-24T18:00:00Z", urls: ["https://example.com"], notes: "")),
            .unknown(RawJSON(object: ["type": .string("future"), "id": .string("x")])),
        ])),
    ]
    let data = try LibraryCodec.encodeNodes(nodes)
    let decoded = try LibraryCodec.decodeNodes(from: data)
    #expect(decoded.count == 1)
    guard case let .folder(folder) = decoded[0] else {
        Issue.record("expected folder")
        return
    }
    #expect(folder.children.count == 4)
    let json = String(decoding: data, as: UTF8.self)
    #expect(json.contains("null"))
}

@Test func restoresBackupWhenPrimaryIsEmpty() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let store = BookmarkStore(directory: directory)
    try store.saveFolders(LibraryDefaults.defaultFolders())
    try Data("[]".utf8).write(to: store.bookmarksURL)
    let loaded = try store.load()
    #expect(loaded.folders.contains { node in
        if case let .folder(folder) = node { return folder.name == "Tech" }
        return false
    })
}

@Test func extractsPlainHTMLAndRejectsScripts() {
    let urls = URLExtractor.extract(from: "see https://example.com/a and www.apple.com")
    #expect(urls.contains("https://example.com/a"))
    #expect(urls.contains("https://www.apple.com"))
    #expect(URLExtractor.extract(from: "javascript:alert(1)").isEmpty)
    #expect(URLExtractor.normalize("notes.pdf") == nil)
    let hrefs = URLExtractor.hrefs(in: "<a href=\"https://example.com/x\">x</a>")
    #expect(hrefs == ["https://example.com/x"])
}

@Test func privateScriptUsesShortcutAndDoesNotFallback() {
    let script = SafariScripts.privateWindow("https://example.com")
    #expect(script.contains("keystroke \"n\" using {shift down, command down}"))
    #expect(!script.contains("make new document"))
    #expect(SafariScripts.newDocument("javascript:alert(1)").isEmpty)
    #expect(SafariScripts.escape("a\"b\\c\n").contains("\\\""))
}

@Test func duplicateNormalizationAndQuickSaveOrder() {
    let folders: [LibraryNode] = [
        .folder(FolderNode(name: "Tech", accent: nil, children: [
            .bookmark(BookmarkItem(name: "A", url: "https://Example.com/path/", accent: nil)),
            .bookmark(BookmarkItem(name: "B", url: "https://example.com/path", accent: nil)),
        ])),
    ]
    #expect(HealthScanner.duplicates(folders: folders, groups: []).count == 1)
    let entries = [
        QuickSaveEntry(id: "old", createdAt: "2026-01-01T00:00:00Z", urls: [], notes: ""),
        QuickSaveEntry(id: "new", createdAt: "2026-09-01T00:00:00Z", urls: [], notes: ""),
    ]
    let sorted = entries.sorted { (ISO8601.date(from: $0.createdAt) ?? .distantPast) > (ISO8601.date(from: $1.createdAt) ?? .distantPast) }
    #expect(sorted.first?.id == "new")
}

@Test func quickSaveCannotBeRenamedAwayByNormalizer() {
    let nodes = LibraryNormalizer.normalize([
        .folder(FolderNode(name: "Fun", accent: nil, children: [])),
    ])
    guard case let .folder(first) = nodes.nodes.first else {
        Issue.record("missing quick save")
        return
    }
    #expect(first.name == "Quick Save")
}
