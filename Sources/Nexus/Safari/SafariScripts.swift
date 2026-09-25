import Foundation

public enum SafariScripts {
    public static func escape(_ value: String) -> String {
        value
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: "\\n")
            .replacingOccurrences(of: "\r", with: "\\r")
            .replacingOccurrences(of: "\t", with: "\\t")
            .replacingOccurrences(of: "\u{0B}", with: "\\v")
            .replacingOccurrences(of: "\u{0C}", with: "\\f")
            .replacingOccurrences(of: "\0", with: "")
    }

    public static func allowed(_ urls: [String]) -> [String] {
        urls.filter(URLExtractor.isAllowed)
    }

    public static func newDocument(_ url: String) -> String {
        guard URLExtractor.isAllowed(url) else { return "" }
        let safe = escape(url)
        return """
        tell application "Safari"
            make new document with properties {URL:"\(safe)"}
            activate
        end tell
        """
    }

    public static func newTab(_ url: String) -> String {
        guard URLExtractor.isAllowed(url) else { return "" }
        let safe = escape(url)
        return """
        tell application "Safari"
            tell front window
                make new tab with properties {URL:"\(safe)"}
            end tell
        end tell
        """
    }

    public static func privateWindow(_ url: String) -> String {
        guard URLExtractor.isAllowed(url) else { return "" }
        let safe = escape(url)
        return """
        tell application "Safari" to activate
        tell application "System Events"
            tell process "Safari"
                set frontmost to true
                keystroke "n" using {shift down, command down}
            end tell
        end tell
        delay 0.5
        tell application "Safari"
            set URL of front document to "\(safe)"
        end tell
        """
    }

    public static func openInFrontWindow(_ urls: [String]) -> String {
        let urls = allowed(urls)
        guard let first = urls.first else { return "" }
        var parts = [
            "tell application \"Safari\"",
            "    activate",
            "    if (count of windows) = 0 then",
            "        make new document with properties {URL:\"\(escape(first))\"}",
            "    else",
            "        set URL of front document to \"\(escape(first))\"",
            "    end if",
        ]
        for url in urls.dropFirst() {
            parts.append("    delay 0.5")
            parts.append("    tell front window to make new tab with properties {URL:\"\(escape(url))\"}")
        }
        parts.append("end tell")
        return parts.joined(separator: "\n")
    }

    public static let allTabs = """
    tell application "Safari"
        if not (exists (windows)) or (count of windows) = 0 then return ""
        set output to ""
        repeat with w in windows
            repeat with t in tabs of w
                set tabURL to URL of t
                set tabTitle to name of t
                if tabURL is not missing value and tabURL is not "" then
                    set output to output & tabTitle & tab & tabURL & linefeed
                end if
            end repeat
        end repeat
        return output
    end tell
    """

    public static func parseTabs(_ text: String) -> [(title: String, url: String)] {
        text.split(whereSeparator: \.isNewline).compactMap { line in
            let parts = line.split(separator: "\t", maxSplits: 1, omittingEmptySubsequences: false)
            guard parts.count == 2 else { return nil }
            let url = String(parts[1]).trimmingCharacters(in: .whitespaces)
            guard URLExtractor.isAllowed(url) else { return nil }
            return (String(parts[0]), url)
        }
    }
}

public struct OpenPlan: Equatable, Sendable {
    public var batches: [[String]]
    public init(batches: [[String]]) { self.batches = batches }
}

public enum OpenPlanner {
    public static func plan(
        urls: [String],
        batchSize: Int,
        staggerSameSite: Bool
    ) -> OpenPlan {
        let urls = SafariScripts.allowed(urls)
        let size = max(1, batchSize)
        if !staggerSameSite {
            return OpenPlan(batches: stride(from: 0, to: urls.count, by: size).map { start in
                Array(urls[start..<min(start + size, urls.count)])
            })
        }
        var buckets: [String: [String]] = [:]
        var order: [String] = []
        for url in urls {
            let host = URL(string: url)?.host?.lowercased() ?? "unknown"
            if buckets[host] == nil { order.append(host) }
            buckets[host, default: []].append(url)
        }
        var batches: [[String]] = []
        var remaining = buckets
        while remaining.values.contains(where: { !$0.isEmpty }) {
            var batch: [String] = []
            for host in order {
                guard var queue = remaining[host], !queue.isEmpty else { continue }
                let take = min(10, size - batch.count, queue.count)
                if take == 0 { continue }
                batch.append(contentsOf: queue.prefix(take))
                queue.removeFirst(take)
                remaining[host] = queue
                if batch.count >= size { break }
            }
            if batch.isEmpty { break }
            batches.append(batch)
        }
        return OpenPlan(batches: batches)
    }
}
