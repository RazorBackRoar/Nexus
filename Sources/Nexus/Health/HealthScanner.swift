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

    public static func linkTargets(folders: [LibraryNode], groups: [BookmarkGroup]) -> [LinkCheck] {
        var seen = Set<String>()
        var items: [LinkCheck] = []
        func add(name: String, url: String, container: String) {
            let key = URLExtractor.normalizedKey(url)
            guard seen.insert(key).inserted else { return }
            items.append(LinkCheck(name: name, url: url, container: container, alive: false, status: nil, error: nil))
        }
        func walk(_ nodes: [LibraryNode], container: String) {
            for node in nodes {
                switch node {
                case let .folder(folder):
                    walk(folder.children, container: folder.name)
                case let .bookmark(item):
                    add(name: item.name, url: item.url, container: container)
                case let .quickSave(entry):
                    for url in entry.urls { add(name: url, url: url, container: container) }
                case .group, .unknown:
                    break
                }
            }
        }
        walk(folders, container: "")
        for group in groups {
            for item in group.items { add(name: item.title, url: item.url, container: group.name) }
        }
        return items
    }

    public static func check(_ item: LinkCheck) async -> LinkCheck {
        guard let url = URL(string: item.url) else {
            return LinkCheck(name: item.name, url: item.url, container: item.container, alive: false, status: nil, error: "Invalid URL")
        }
        var request = URLRequest(url: url)
        request.httpMethod = "HEAD"
        request.timeoutInterval = 6
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            let code = (response as? HTTPURLResponse)?.statusCode
            let alive = (code ?? 0) < 400
            return LinkCheck(name: item.name, url: item.url, container: item.container, alive: alive, status: code, error: alive ? nil : "HTTP \(code ?? 0)")
        } catch {
            return LinkCheck(name: item.name, url: item.url, container: item.container, alive: false, status: nil, error: "Unreachable")
        }
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
    public static func fetchLatest(current: String) async -> UpdateResult {
        guard let url = URL(string: "https://api.github.com/repos/RazorBackRoar/Nexus/releases/latest") else {
            return compare(current: current, latestTag: current)
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 12
        request.setValue("Nexus", forHTTPHeaderField: "User-Agent")
        do {
            let (data, _) = try await URLSession.shared.data(for: request)
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
            let tag = json?["tag_name"] as? String ?? current
            return compare(current: current, latestTag: tag)
        } catch {
            return UpdateResult(current: current, latest: current, available: false, message: "Could not reach GitHub to check for updates.")
        }
    }

    public static func compare(current: String, latestTag: String) -> UpdateResult {
        let latest = latestTag.trimmingCharacters(in: CharacterSet(charactersIn: "vV"))
        let available = latest.compare(current, options: .numeric) == .orderedDescending
        let message = available
            ? "Nexus \(latest) is available. You are on \(current)."
            : "Nexus \(current) is the latest release."
        return UpdateResult(current: current, latest: latest, available: available, message: message)
    }
}
