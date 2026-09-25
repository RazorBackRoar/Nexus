import CryptoKit
import Foundation

public struct DuplicateHit: Equatable, Sendable, Identifiable {
    public var name: String
    public var url: String
    public var container: String
    public var id: String { "\(container)|\(url)|\(name)" }
}

public struct LinkCheck: Equatable, Sendable, Identifiable {
    public var name: String
    public var url: String
    public var container: String
    public var alive: Bool
    public var status: Int?
    public var error: String?
    public var id: String { "\(container)|\(url)" }
}

public enum HealthScanner {
    public static func duplicates(folders: [LibraryNode], groups: [BookmarkGroup]) -> [[DuplicateHit]] {
        var map: [String: [DuplicateHit]] = [:]
        func walk(_ nodes: [LibraryNode], container: String) {
            for node in nodes {
                switch node {
                case let .folder(folder):
                    walk(folder.children, container: folder.name)
                case let .bookmark(item):
                    let key = URLExtractor.normalizedKey(item.url)
                    map[key, default: []].append(DuplicateHit(name: item.name, url: item.url, container: container))
                case let .quickSave(entry):
                    for url in entry.urls {
                        let key = URLExtractor.normalizedKey(url)
                        map[key, default: []].append(DuplicateHit(name: url, url: url, container: container))
                    }
                case .group, .unknown:
                    break
                }
            }
        }
        walk(folders, container: "")
        for group in groups {
            for item in group.items {
                let key = URLExtractor.normalizedKey(item.url)
                map[key, default: []].append(DuplicateHit(name: item.title, url: item.url, container: group.name))
            }
        }
        return map.values.filter { $0.count > 1 }.sorted { ($0.first?.url ?? "") < ($1.first?.url ?? "") }
    }

    public static func fingerprint(_ value: String) -> String {
        let digest = SHA256.hash(data: Data(value.utf8))
        return digest.prefix(6).map { String(format: "%02x", $0) }.joined()
    }
}

public enum RichLinks {
    public static func html(urls: [String], skipDuplicates: Bool, sortAlpha: Bool, keepBlankLines: Bool) -> String {
        var lines = urls
        if skipDuplicates {
            var seen = Set<String>()
            lines = lines.filter { seen.insert($0.lowercased()).inserted }
        }
        if sortAlpha {
            lines.sort { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
        }
        let body = lines.map { url -> String in
            let escaped = url
                .replacingOccurrences(of: "&", with: "&amp;")
                .replacingOccurrences(of: "<", with: "&lt;")
                .replacingOccurrences(of: "\"", with: "&quot;")
            return "<div><a href=\"\(escaped)\">\(escaped)</a></div>"
        }.joined(separator: keepBlankLines ? "<br>" : "")
        return "<html><body>\(body)</body></html>"
    }
}

public struct UpdateResult: Equatable, Sendable {
    public var current: String
    public var latest: String
    public var available: Bool
    public var message: String
}

public enum UpdateChecker {
    public static func compare(current: String, latestTag: String) -> UpdateResult {
        let latest = latestTag.trimmingCharacters(in: CharacterSet(charactersIn: "vV"))
        let available = latest.compare(current, options: .numeric) == .orderedDescending
        let message = available
            ? "Nexus \(latest) is available. You are on \(current)."
            : "Nexus \(current) is the latest release."
        return UpdateResult(current: current, latest: latest, available: available, message: message)
    }
}
