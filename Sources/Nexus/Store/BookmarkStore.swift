import Darwin
import Foundation

public enum AtomicJSON {
    public static func replace(_ data: Data, at url: URL) throws {
        let directory = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let tmp = url.appendingPathExtension("tmp")
        if FileManager.default.fileExists(atPath: tmp.path) {
            try FileManager.default.removeItem(at: tmp)
        }
        let fd = open(tmp.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw CocoaError(.fileWriteUnknown) }
        var payload = data
        if !payload.isEmpty, payload.last != 0x0A {
            payload.append(0x0A)
        }
        let wrote: Int = payload.withUnsafeBytes { buffer in
            guard let base = buffer.baseAddress else { return 0 }
            return Darwin.write(fd, base, buffer.count)
        }
        if wrote != payload.count {
            close(fd)
            try? FileManager.default.removeItem(at: tmp)
            throw CocoaError(.fileWriteUnknown)
        }
        if fsync(fd) != 0 {
            close(fd)
            try? FileManager.default.removeItem(at: tmp)
            throw CocoaError(.fileWriteUnknown)
        }
        close(fd)
        _ = try? FileManager.default.removeItem(at: url)
        try FileManager.default.moveItem(at: tmp, to: url)
    }
}

public struct BookmarkStore: Sendable {
    public let directory: URL
    public var bookmarksURL: URL { directory.appendingPathComponent("bookmarks_v2.json") }
    public var groupsURL: URL { directory.appendingPathComponent("bookmark_groups.json") }

    public init(directory: URL) {
        self.directory = directory
    }

    public func load() throws -> (folders: [LibraryNode], groups: [BookmarkGroup], createdDefaults: Bool) {
        let folders = try loadList(at: bookmarksURL, decode: LibraryCodec.decodeNodes(from:))
        let groups = try loadList(at: groupsURL, decode: LibraryCodec.decodeGroups(from:))
        if folders == nil && groups == nil && !FileManager.default.fileExists(atPath: bookmarksURL.path) {
            let defaults = LibraryDefaults.defaultFolders()
            try saveFolders(defaults)
            try saveGroups([])
            return (defaults, [], true)
        }
        return (folders ?? LibraryDefaults.defaultFolders(), groups ?? [], folders == nil)
    }

    public func saveFolders(_ nodes: [LibraryNode]) throws {
        try save(LibraryCodec.encodeNodes(nodes), to: bookmarksURL)
    }

    public func saveGroups(_ groups: [BookmarkGroup]) throws {
        try save(LibraryCodec.encodeGroups(groups), to: groupsURL)
    }

    private func loadList<T>(at url: URL, decode: (Data) throws -> [T]) throws -> [T]? {
        let backup = URL(fileURLWithPath: url.path + ".bak")
        for candidate in [url, backup] {
            guard FileManager.default.fileExists(atPath: candidate.path) else { continue }
            guard let data = try? Data(contentsOf: candidate) else { continue }
            guard let parsed = try? decode(data), !parsed.isEmpty else { continue }
            if candidate != url {
                try save(data, to: url)
            }
            return parsed
        }
        return nil
    }

    private func save(_ data: Data, to url: URL) throws {
        let backup = URL(fileURLWithPath: url.path + ".bak")
        if FileManager.default.fileExists(atPath: url.path) {
            if FileManager.default.fileExists(atPath: backup.path) {
                try FileManager.default.removeItem(at: backup)
            }
            try FileManager.default.moveItem(at: url, to: backup)
        }
        do {
            try AtomicJSON.replace(data, at: url)
        } catch {
            if !FileManager.default.fileExists(atPath: url.path),
               FileManager.default.fileExists(atPath: backup.path) {
                try? FileManager.default.moveItem(at: backup, to: url)
            }
            throw error
        }
    }
}

public enum LibraryLocator {
    public static func resolvedDirectory() -> URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let candidates = [
            support.appendingPathComponent("Nexus/Nexus", isDirectory: true),
            support.appendingPathComponent("Nexus", isDirectory: true),
        ]
        for directory in candidates {
            let file = directory.appendingPathComponent("bookmarks_v2.json")
            if FileManager.default.fileExists(atPath: file.path) {
                return directory
            }
        }
        return support.appendingPathComponent("Nexus", isDirectory: true)
    }
}
