import Foundation

public enum LibraryCodec {
    public static func decodeNodes(from data: Data) throws -> [LibraryNode] {
        let root = try JSONSerialization.jsonObject(with: data)
        guard let array = root as? [Any] else {
            throw CocoaError(.propertyListReadCorrupt)
        }
        return array.compactMap(decodeNode)
    }

    public static func encodeNodes(_ nodes: [LibraryNode]) throws -> Data {
        let objects = nodes.map(encodeNode)
        return try JSONSerialization.data(withJSONObject: objects, options: [.prettyPrinted, .sortedKeys])
    }

    public static func decodeGroups(from data: Data) throws -> [BookmarkGroup] {
        let root = try JSONSerialization.jsonObject(with: data)
        guard let array = root as? [Any] else {
            throw CocoaError(.propertyListReadCorrupt)
        }
        return array.compactMap { item -> BookmarkGroup? in
            guard let dict = item as? [String: Any],
                  let id = dict["id"] as? String,
                  let name = dict["name"] as? String else { return nil }
            let created = dict["created_at"] as? String ?? ""
            let items = (dict["items"] as? [[String: Any]] ?? []).compactMap { raw -> GroupItem? in
                guard let url = raw["url"] as? String else { return nil }
                return GroupItem(title: raw["title"] as? String ?? "", url: url)
            }
            return BookmarkGroup(id: id, name: name, createdAt: created, items: items)
        }
    }

    public static func encodeGroups(_ groups: [BookmarkGroup]) throws -> Data {
        let objects: [[String: Any]] = groups.map { group in
            [
                "id": group.id,
                "name": group.name,
                "created_at": group.createdAt,
                "items": group.items.map { ["title": $0.title, "url": $0.url] },
            ]
        }
        return try JSONSerialization.data(withJSONObject: objects, options: [.prettyPrinted, .sortedKeys])
    }

    private static func decodeNode(_ any: Any) -> LibraryNode? {
        guard let dict = any as? [String: Any] else { return nil }
        let type = dict["type"] as? String ?? ""
        switch type {
        case "folder":
            guard let name = dict["name"] as? String else { return nil }
            let children = (dict["children"] as? [Any] ?? []).compactMap(decodeNode)
            return .folder(FolderNode(name: name, accent: dict["accent"] as? String, children: children))
        case "bookmark":
            guard let name = dict["name"] as? String, let url = dict["url"] as? String else { return nil }
            guard let normalized = URLExtractor.normalize(url) else { return nil }
            return .bookmark(BookmarkItem(name: name, url: normalized, accent: dict["accent"] as? String))
        case "group":
            guard let id = dict["id"] as? String else { return nil }
            return .group(GroupMarker(id: id))
        case "quick_save":
            let id = (dict["id"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? UUID().uuidString
            let urls = (dict["urls"] as? [Any] ?? []).compactMap { $0 as? String }.filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
            return .quickSave(
                QuickSaveEntry(
                    id: id,
                    createdAt: dict["created_at"] as? String ?? ISO8601.now(),
                    urls: urls,
                    notes: dict["notes"] as? String ?? ""
                )
            )
        default:
            guard let parsed = JSONValue.parse(dict), case let .object(object) = parsed else { return nil }
            return .unknown(RawJSON(object: object))
        }
    }

    private static func encodeNode(_ node: LibraryNode) -> Any {
        switch node {
        case let .folder(folder):
            return [
                "accent": folder.accent ?? NSNull(),
                "children": folder.children.map(encodeNode),
                "name": folder.name,
                "type": "folder",
            ] as [String: Any]
        case let .bookmark(item):
            return [
                "accent": item.accent ?? NSNull(),
                "name": item.name,
                "type": "bookmark",
                "url": item.url,
            ] as [String: Any]
        case let .group(marker):
            return ["id": marker.id, "type": "group"]
        case let .quickSave(entry):
            return [
                "created_at": entry.createdAt,
                "id": entry.id,
                "notes": entry.notes,
                "type": "quick_save",
                "urls": entry.urls,
            ] as [String: Any]
        case let .unknown(raw):
            return raw.object.mapValues(\.foundationObject)
        }
    }
}

public enum ISO8601 {
    public static func now() -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: Date())
    }

    public static func date(from string: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        if let date = formatter.date(from: string) { return date }
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: string)
    }
}
