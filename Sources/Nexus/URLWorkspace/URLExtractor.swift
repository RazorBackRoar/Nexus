import Foundation

public enum URLExtractor {
    public static let maxLength = 10_000
    private static let blacklist: Set<String> = [
        "txt", "md", "png", "jpg", "jpeg", "gif", "svg", "pdf", "doc", "docx", "xls", "xlsx",
        "ppt", "pptx", "zip", "rar", "7z", "py", "js", "css", "html", "mp3", "mp4", "avi",
        "mov", "mkv", "exe", "dmg", "pkg", "deb", "rpm",
    ]
    private static let shorteners: Set<String> = [
        "bit.ly", "tinyurl.com", "t.co", "goo.gl", "short.link", "is.gd", "v.gd", "ow.ly",
        "buff.ly", "rebrand.ly", "tiny.cc", "shorturl.at",
    ]

    public static func extract(from text: String) -> [String] {
        let clipped = String(text.prefix(maxLength))
        let cleaned = sanitize(clipped)
        var found = Set(splitConcatenated(cleaned))
        var remainder = cleaned
        for url in found {
            remainder = remainder.replacingOccurrences(of: url, with: " ")
        }
        found.formUnion(matches(shortenerPattern, in: remainder))
        found.formUnion(matches(protocolPattern, in: remainder))
        found.formUnion(matches(wwwPattern, in: remainder))
        found.formUnion(matches(domainPattern, in: remainder))
        let filtered = dropSubstrings(Array(found))
        let normalized = filtered.compactMap(normalize)
        return Array(Set(normalized)).sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
    }

    public static func filterOpenable(_ urls: [String]) -> [String] {
        var seen = Set<String>()
        var kept: [String] = []
        for raw in urls {
            guard let normalized = normalize(raw), isAllowed(normalized) else { continue }
            let key = normalized.lowercased()
            if seen.insert(key).inserted {
                kept.append(normalized)
            }
        }
        return kept.sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
    }

    public static func parseFile(name: String, text: String) -> [String] {
        let suffix = (name as NSString).pathExtension.lowercased()
        guard ["txt", "csv", "md"].contains(suffix) else { return [] }
        if suffix == "csv" {
            let cells = text.split(whereSeparator: { $0 == "," || $0 == "\n" || $0 == "\r" || $0 == "\t" })
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "\"")) }
                .filter { !$0.isEmpty }
            return filterOpenable(cells.flatMap { extract(from: String($0)) })
        }
        return extract(from: text)
    }

    public static func hrefs(in html: String) -> [String] {
        guard let regex = try? NSRegularExpression(pattern: #"href=["'](https?://[^"']+)["']"#, options: .caseInsensitive) else {
            return []
        }
        let range = NSRange(html.startIndex..<html.endIndex, in: html)
        return regex.matches(in: html, range: range).compactMap { match in
            guard let slice = Range(match.range(at: 1), in: html) else { return nil }
            return String(html[slice])
        }
    }

    public static func isAllowed(_ url: String) -> Bool {
        guard let parts = URL(string: url), let scheme = parts.scheme?.lowercased() else { return false }
        return (scheme == "http" || scheme == "https") && parts.host != nil
    }

    public static func normalize(_ raw: String) -> String? {
        var url = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        url = url.trimmingCharacters(in: CharacterSet(charactersIn: ".,;:!?)"))
        guard !url.isEmpty, url.count <= 2048 else { return nil }
        if looksLikeBlockedFile(url) { return nil }
        if url.range(of: #"^[a-zA-Z]+://"#, options: .regularExpression) == nil {
            if url.lowercased().hasPrefix("www.") || url.range(of: #"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"#, options: .regularExpression) != nil {
                url = "https://" + url
            } else if shorteners.contains(where: { url.lowercased().hasPrefix($0 + "/") }) {
                url = "https://" + url
            } else {
                return nil
            }
        }
        guard let parts = URL(string: url), let scheme = parts.scheme?.lowercased(),
              scheme == "http" || scheme == "https", let host = parts.host, host.contains(".") else {
            return nil
        }
        let tld = host.split(separator: ".").last.map(String.init) ?? ""
        guard tld.count >= 2, tld.allSatisfy(\.isLetter) else { return nil }
        return url
    }

    public static func hostName(from url: String) -> String {
        guard let host = URL(string: url)?.host else { return url }
        return host.lowercased().hasPrefix("www.") ? String(host.dropFirst(4)) : host
    }

    public static func normalizedKey(_ url: String) -> String {
        guard let parts = URL(string: url) else { return url.lowercased() }
        let scheme = (parts.scheme ?? "https").lowercased()
        let host = (parts.host ?? "").lowercased()
        var path = parts.path
        if path.hasSuffix("/") { path.removeLast() }
        let query = parts.query.map { "?\($0)" } ?? ""
        return "\(scheme)://\(host)\(path)\(query)"
    }

    private static func sanitize(_ text: String) -> String {
        var output = ""
        output.reserveCapacity(text.count)
        var previousSpace = false
        for scalar in text.unicodeScalars {
            if scalar.value < 32 || scalar.value > 126 {
                if !previousSpace { output.append(" ") }
                previousSpace = true
                continue
            }
            if scalar == " " || scalar == "\t" {
                if !previousSpace { output.append(" ") }
                previousSpace = true
            } else {
                output.unicodeScalars.append(scalar)
                previousSpace = false
            }
        }
        return output.trimmingCharacters(in: .whitespaces)
    }

    private static func splitConcatenated(_ text: String) -> [String] {
        var urls: [String] = []
        let pieces = text.components(separatedBy: "https://") + text.components(separatedBy: "http://")
        for piece in pieces where piece != text {
            let head = piece.components(separatedBy: "http").first ?? piece
            let candidate = (text.contains("https://\(head)") ? "https://" : "http://") + head
            if let normalized = normalize(candidate.components(separatedBy: " ").first ?? candidate) {
                urls.append(normalized)
            }
        }
        if text.contains("https://") && text.components(separatedBy: "https://").count > 2 {
            let chunks = text.components(separatedBy: "https://").dropFirst()
            for chunk in chunks {
                let body = chunk.components(separatedBy: "https://").first ?? chunk
                if let normalized = normalize("https://" + body.trimmingCharacters(in: .whitespaces)) {
                    urls.append(normalized)
                }
            }
        }
        return urls
    }

    private static func looksLikeBlockedFile(_ url: String) -> Bool {
        if url.hasPrefix("http://") || url.hasPrefix("https://") || url.hasPrefix("www.") || url.contains("/") {
            return false
        }
        let ext = url.split(separator: ".").last.map(String.init)?.lowercased() ?? ""
        return blacklist.contains(ext)
    }

    private static let protocolPattern = #"https?://[^\s<>"{}|\\^`\[\]]+"#
    private static let wwwPattern = #"www\.[^\s<>"{}|\\^`\[\]]+"#
    private static let domainPattern = #"[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?"#
    private static let shortenerPattern = #"(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|short\.link|is\.gd|v\.gd|ow\.ly|buff\.ly|rebrand\.ly|tiny\.cc|shorturl\.at)/[a-zA-Z0-9]+"#

    private static func matches(_ pattern: String, in text: String) -> [String] {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else { return [] }
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        return regex.matches(in: text, range: range).compactMap { match in
            Range(match.range, in: text).map { String(text[$0]) }
        }
    }

    private static func dropSubstrings(_ urls: [String]) -> [String] {
        let sorted = urls.sorted { $0.count > $1.count }
        var kept: [String] = []
        for url in sorted {
            let buried = kept.contains { existing in
                existing != url && existing.contains(url) && (existing.hasPrefix(url) || existing.contains(url + "/") || existing.contains(url + "?"))
            }
            if !buried { kept.append(url) }
        }
        return kept
    }
}
