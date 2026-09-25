import Foundation

public struct FolderNode: Equatable, Sendable, Identifiable {
    public var name: String
    public var accent: String?
    public var children: [LibraryNode]

    public var id: String { name.lowercased() }

    public init(name: String, accent: String? = nil, children: [LibraryNode] = []) {
        self.name = name
        self.accent = accent
        self.children = children
    }
}

public struct BookmarkItem: Equatable, Sendable, Identifiable {
    public var name: String
    public var url: String
    public var accent: String?

    public var id: String { "\(name)|\(url)" }

    public init(name: String, url: String, accent: String? = nil) {
        self.name = name
        self.url = url
        self.accent = accent
    }
}

public struct GroupMarker: Equatable, Sendable, Identifiable {
    public var id: String
    public init(id: String) { self.id = id }
}

public struct QuickSaveEntry: Equatable, Sendable, Identifiable {
    public var id: String
    public var createdAt: String
    public var urls: [String]
    public var notes: String

    public init(id: String, createdAt: String, urls: [String], notes: String) {
        self.id = id
        self.createdAt = createdAt
        self.urls = urls
        self.notes = notes
    }
}

public struct RawJSON: Equatable, Sendable {
    public var object: [String: JSONValue]
    public init(object: [String: JSONValue]) { self.object = object }
}

public enum LibraryNode: Equatable, Sendable {
    case folder(FolderNode)
    case bookmark(BookmarkItem)
    case group(GroupMarker)
    case quickSave(QuickSaveEntry)
    case unknown(RawJSON)
}

public struct GroupItem: Equatable, Sendable {
    public var title: String
    public var url: String
    public init(title: String, url: String) {
        self.title = title
        self.url = url
    }
}

public struct BookmarkGroup: Equatable, Sendable, Identifiable {
    public var id: String
    public var name: String
    public var createdAt: String
    public var items: [GroupItem]

    public init(id: String, name: String, createdAt: String, items: [GroupItem]) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
        self.items = items
    }
}

public enum JSONValue: Equatable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    public var foundationObject: Any {
        switch self {
        case let .string(value): return value
        case let .number(value): return value
        case let .bool(value): return value
        case let .object(value): return value.mapValues(\.foundationObject)
        case let .array(value): return value.map(\.foundationObject)
        case .null: return NSNull()
        }
    }

    public static func parse(_ any: Any) -> JSONValue? {
        switch any {
        case let value as String:
            return .string(value)
        case let value as NSNumber:
            if CFGetTypeID(value) == CFBooleanGetTypeID() {
                return .bool(value.boolValue)
            }
            return .number(value.doubleValue)
        case let value as [String: Any]:
            var object: [String: JSONValue] = [:]
            for (key, item) in value {
                guard let parsed = JSONValue.parse(item) else { return nil }
                object[key] = parsed
            }
            return .object(object)
        case let value as [Any]:
            return .array(value.compactMap(JSONValue.parse))
        case is NSNull:
            return .null
        default:
            return nil
        }
    }
}

public enum LibraryDefaults {
    public static let quickSaveName = "Quick Save"
    public static let folderOrder = [
        "Quick Save", "Fun", "Misc", "Tech", "Work", "Extra", "Hidden", "Special", "Favorites",
    ]
    public static let accents: [String: String] = [
        "Quick Save": "#2EC4A0",
        "Fun": "#E5738A",
        "Misc": "#D4A05A",
        "Tech": "#5B8DEF",
        "Work": "#E85A5A",
        "Extra": "#8A95A8",
        "Hidden": "#2A2A35",
        "Special": "#F0F4FA",
        "Favorites": "#5BA86A",
    ]

    public static func defaultFolders() -> [LibraryNode] {
        folderOrder.map { name in
            .folder(FolderNode(name: name, accent: accents[name], children: []))
        }
    }

    public static func isQuickSave(_ name: String) -> Bool {
        name.caseInsensitiveCompare(quickSaveName) == .orderedSame
            || name.caseInsensitiveCompare("Quick Saves") == .orderedSame
    }

    /// Display colors for the sidebar. Built-in folders get distinct hues; custom accents win.
    public static let vividAccents: [String: String] = [
        "quick save": "#34D6C4",
        "fun": "#FF9A3C",
        "misc": "#F2C14E",
        "tech": "#4DA3FF",
        "work": "#FF5A52",
        "extra": "#9D7BFF",
        "hidden": "#7C8CB5",
        "special": "#FF6FAE",
        "favorites": "#52D273",
    ]

    private static let legacyAccents: Set<String> = [
        "#2EC4A0", "#E5738A", "#D4A05A", "#5B8DEF", "#E85A5A", "#8A95A8", "#2A2A35", "#F0F4FA", "#5BA86A",
    ]

    public static func displayAccent(name: String, stored: String?) -> String {
        if let stored, !legacyAccents.contains(stored.uppercased()) {
            return stored
        }
        if let vivid = vividAccents[name.lowercased()] {
            return vivid
        }
        let palette = vividAccents.values.sorted()
        let index = name.unicodeScalars.reduce(0) { $0 &+ Int($1.value) } % palette.count
        return palette[index]
    }
}
