import AppKit
import Foundation
import SwiftUI

public enum URLStatus: String, Sendable {
    case ready = "Ready"
    case opening = "Opening"
    case opened = "Opened"
    case failed = "Failed"
}

public struct URLRow: Identifiable, Equatable, Sendable {
    public var id: UUID
    public var url: String
    public var status: URLStatus

    public init(id: UUID = UUID(), url: String, status: URLStatus = .ready) {
        self.id = id
        self.url = url
        self.status = status
    }
}

enum SidebarItem: Hashable {
    case folder(String)
    case bookmark(String, String)
    case group(String)
    case quickSave(String)
}

@MainActor
@Observable
final class AppModel {
    var folders: [LibraryNode] = []
    var groups: [BookmarkGroup] = []
    var urls: [URLRow] = []
    var undoStack: [[URLRow]] = []
    var selectedFolder: String = LibraryDefaults.quickSaveName
    var filter = ""
    var status = "Ready"
    var showQuickSave = false
    var libraryDirectory: URL
    var settings: NexusSettings
    var alertMessage: String?
    var showNewFolder = false
    var showSaveGroup = false
    var showHealth = false
    var showShortcuts = false
    var showAbout = false

    private let store: BookmarkStore

    init() {
        let directory = LibraryLocator.resolvedDirectory()
        libraryDirectory = directory
        store = BookmarkStore(directory: directory)
        settings = NexusSettings.load()
        reloadLibrary()
    }

    func reloadLibrary() {
        do {
            let loaded = try store.load()
            let normalized = LibraryNormalizer.normalize(loaded.folders)
            folders = normalized.nodes
            groups = loaded.groups
            if normalized.changed || loaded.createdDefaults {
                try store.saveFolders(folders)
            }
            if folders.contains(where: { if case let .folder(folder) = $0 { return LibraryDefaults.isQuickSave(folder.name) }; return false }) == false {
                selectedFolder = LibraryDefaults.quickSaveName
            }
        } catch {
            status = "Could not read the bookmark library."
            folders = LibraryDefaults.defaultFolders()
        }
    }

    func persist() {
        do {
            try store.saveFolders(folders)
            try store.saveGroups(groups)
        } catch {
            status = "Could not save bookmarks."
        }
    }

    var visibleFolders: [LibraryNode] {
        let query = filter.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return folders }
        return folders.compactMap { node -> LibraryNode? in
            guard case var .folder(folder) = node else { return nil }
            if folder.name.localizedCaseInsensitiveContains(query) { return node }
            folder.children = folder.children.filter { child in
                switch child {
                case let .bookmark(item):
                    return item.name.localizedCaseInsensitiveContains(query) || item.url.localizedCaseInsensitiveContains(query)
                case let .group(marker):
                    return groupName(marker.id).localizedCaseInsensitiveContains(query)
                case let .quickSave(entry):
                    return entry.notes.localizedCaseInsensitiveContains(query) || entry.urls.contains { $0.localizedCaseInsensitiveContains(query) }
                default:
                    return false
                }
            }
            return folder.children.isEmpty ? nil : .folder(folder)
        }
    }

    func folder(named name: String) -> FolderNode? {
        for node in folders {
            if case let .folder(folder) = node, folder.name.caseInsensitiveCompare(name) == .orderedSame {
                return folder
            }
        }
        return nil
    }

    func groupName(_ id: String) -> String {
        groups.first { $0.id == id }?.name ?? "Group"
    }

    func groupItems(_ id: String) -> [GroupItem] {
        groups.first { $0.id == id }?.items ?? []
    }

    func selectFolder(_ name: String) {
        selectedFolder = name
        showQuickSave = LibraryDefaults.isQuickSave(name)
    }

    func goHome() {
        showQuickSave = false
        if let first = folders.compactMap({ node -> String? in
            if case let .folder(folder) = node, !LibraryDefaults.isQuickSave(folder.name) { return folder.name }
            return nil
        }).first {
            selectedFolder = first
        }
    }

    func ingest(_ incoming: [String]) {
        let cleaned = URLExtractor.filterOpenable(incoming)
        guard !cleaned.isEmpty else {
            status = "No links found."
            return
        }
        pushUndo()
        var combined = urls.map(\.url) + cleaned
        combined = URLExtractor.filterOpenable(combined)
        urls = combined.map { URLRow(url: $0) }
        showQuickSave = false
        status = "\(urls.count) URL\(urls.count == 1 ? "" : "s")"
    }

    func pushUndo() {
        undoStack.append(urls)
        if undoStack.count > 30 { undoStack.removeFirst() }
    }

    func undo() {
        guard let previous = undoStack.popLast() else { return }
        urls = previous
        status = urls.isEmpty ? "Waiting for pasted URLs" : "\(urls.count) URLs"
    }

    func clearURLs() {
        guard !urls.isEmpty else { return }
        pushUndo()
        urls = []
        status = "Waiting for pasted URLs"
    }

    func quickSave() {
        let list = urls.map(\.url)
        guard !list.isEmpty else {
            status = "Nothing to save."
            return
        }
        let entry = QuickSaveEntry(id: UUID().uuidString, createdAt: ISO8601.now(), urls: list, notes: "")
        updateQuickSave { folder in
            folder.children.insert(.quickSave(entry), at: 0)
        }
        persist()
        status = "Saved \(list.count) link\(list.count == 1 ? "" : "s") to Quick Save"
    }

    func quickSaveEntries() -> [QuickSaveEntry] {
        guard let folder = folder(named: LibraryDefaults.quickSaveName) else { return [] }
        let entries = folder.children.compactMap { node -> QuickSaveEntry? in
            if case let .quickSave(entry) = node { return entry }
            return nil
        }
        return entries.sorted { lhs, rhs in
            let left = ISO8601.date(from: lhs.createdAt) ?? .distantPast
            let right = ISO8601.date(from: rhs.createdAt) ?? .distantPast
            return left > right
        }
    }

    func updateQuickSaveNotes(id: String, notes: String) {
        updateQuickSave { folder in
            folder.children = folder.children.map { node in
                guard case var .quickSave(entry) = node, entry.id == id else { return node }
                entry.notes = notes
                return .quickSave(entry)
            }
        }
        persist()
    }

    func deleteQuickSave(id: String) {
        updateQuickSave { folder in
            folder.children.removeAll { node in
                if case let .quickSave(entry) = node { return entry.id == id }
                return false
            }
        }
        persist()
    }

    func loadQuickSave(id: String) {
        guard let entry = quickSaveEntries().first(where: { $0.id == id }) else { return }
        ingest(entry.urls)
    }

    func addFolder(name: String, accent: String) {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        guard folder(named: trimmed) == nil else {
            status = "A folder named \(trimmed) already exists."
            return
        }
        folders.append(.folder(FolderNode(name: trimmed, accent: accent, children: [])))
        persist()
        selectFolder(trimmed)
    }

    func saveGroup(name: String, folderName: String) {
        if LibraryDefaults.isQuickSave(folderName) {
            quickSave()
            return
        }
        let list = urls.map(\.url)
        guard !list.isEmpty else {
            status = "Nothing to save."
            return
        }
        let group = BookmarkGroup(
            id: UUID().uuidString,
            name: name.trimmingCharacters(in: .whitespacesAndNewlines),
            createdAt: ISO8601.now(),
            items: list.map { GroupItem(title: URLExtractor.hostName(from: $0), url: $0) }
        )
        groups.append(group)
        mutateFolder(named: folderName) { folder in
            folder.children.append(.group(GroupMarker(id: group.id)))
        }
        persist()
        status = "Saved \(group.name)"
    }

    func deleteFolder(named name: String) {
        guard !LibraryDefaults.isQuickSave(name) else { return }
        let doomed = groupsReferenced(in: name)
        folders.removeAll { node in
            if case let .folder(folder) = node { return folder.name.caseInsensitiveCompare(name) == .orderedSame }
            return false
        }
        groups.removeAll { doomed.contains($0.id) }
        persist()
        goHome()
    }

    func renameFolder(from old: String, to new: String) {
        guard !LibraryDefaults.isQuickSave(old) else { return }
        let trimmed = new.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        mutateFolder(named: old) { $0.name = trimmed }
        if selectedFolder.caseInsensitiveCompare(old) == .orderedSame { selectedFolder = trimmed }
        persist()
    }

    func setAccent(folder: String, accent: String) {
        mutateFolder(named: folder) { $0.accent = accent }
        persist()
    }

    func moveFolders(from offsets: IndexSet, to destination: Int) {
        var moving = offsets.map { folders[$0] }
        let quickSave = moving.contains { node in
            if case let .folder(folder) = node { return LibraryDefaults.isQuickSave(folder.name) }
            return false
        }
        if quickSave { return }
        folders.move(fromOffsets: offsets, toOffset: destination)
        if let index = folders.firstIndex(where: { node in
            if case let .folder(folder) = node { return LibraryDefaults.isQuickSave(folder.name) }
            return false
        }), index != 0 {
            let node = folders.remove(at: index)
            folders.insert(node, at: 0)
        }
        persist()
    }

    func openAll() async {
        let list = urls.map(\.url)
        guard !list.isEmpty else {
            status = "Nothing to open."
            return
        }
        status = settings.privateByDefault ? "Opening in Private Safari" : "Opening in Safari"
        let plan = OpenPlanner.plan(urls: list, batchSize: settings.batchSize, staggerSameSite: settings.staggerSameSite)
        for index in urls.indices { urls[index].status = .opening }
        let result = await SafariRunner.open(plan: plan, privateMode: settings.privateByDefault, delayMin: settings.delayMin, delayMax: settings.delayMax)
        for index in urls.indices {
            urls[index].status = result.ok ? .opened : .failed
        }
        status = result.message
        if let message = result.alert { alertMessage = message }
    }

    func openOne(_ url: String) async {
        let result = await SafariRunner.open(
            plan: OpenPlan(batches: [[url]]),
            privateMode: settings.privateByDefault,
            delayMin: 0,
            delayMax: 0
        )
        status = result.message
        if let message = result.alert { alertMessage = message }
    }

    func importSafariTabs() async {
        let result = await SafariRunner.importTabs()
        if result.urls.isEmpty {
            status = result.message
            if let alert = result.alert { alertMessage = alert }
            return
        }
        ingest(result.urls)
        status = "Imported \(result.urls.count) Safari tabs"
    }

    func exportURLs(to url: URL) {
        let lines = urls.map(\.url)
        let text: String
        if url.pathExtension.lowercased() == "csv" {
            text = lines.map { "\"\($0.replacingOccurrences(of: "\"", with: "\"\""))\"" }.joined(separator: "\n")
        } else {
            text = lines.joined(separator: "\n")
        }
        do {
            try text.write(to: url, atomically: true, encoding: .utf8)
            status = "Exported \(lines.count) URLs"
        } catch {
            status = "Export failed."
        }
    }

    func copyRichLinks() {
        let html = RichLinks.html(
            urls: urls.map(\.url),
            skipDuplicates: settings.skipDuplicateRichLinks,
            sortAlpha: settings.sortRichLinks,
            keepBlankLines: settings.keepBlankLines
        )
        let plain = urls.map(\.url).joined(separator: "\n")
        let board = NSPasteboard.general
        board.clearContents()
        board.setString(html, forType: .html)
        board.setString(plain, forType: .string)
        status = "Copied rich links"
    }

    func copyURLs(_ list: [String]) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(list.joined(separator: "\n"), forType: .string)
        status = "Copied \(list.count) URLs"
    }

    private func groupsReferenced(in folderName: String) -> Set<String> {
        guard let folder = folder(named: folderName) else { return [] }
        var ids = Set<String>()
        for child in folder.children {
            if case let .group(marker) = child { ids.insert(marker.id) }
        }
        return ids
    }

    private func updateQuickSave(_ body: (inout FolderNode) -> Void) {
        if folder(named: LibraryDefaults.quickSaveName) == nil {
            folders.insert(.folder(FolderNode(name: LibraryDefaults.quickSaveName, accent: LibraryDefaults.accents["Quick Save"], children: [])), at: 0)
        }
        mutateFolder(named: LibraryDefaults.quickSaveName, body: body)
    }

    private func mutateFolder(named name: String, body: (inout FolderNode) -> Void) {
        for index in folders.indices {
            guard case var .folder(folder) = folders[index], folder.name.caseInsensitiveCompare(name) == .orderedSame else { continue }
            body(&folder)
            folders[index] = .folder(folder)
            return
        }
    }
}

enum LibraryNormalizer {
    static func normalize(_ nodes: [LibraryNode]) -> (nodes: [LibraryNode], changed: Bool) {
        var changed = false
        var kept: [LibraryNode] = []
        var quickSave: FolderNode?
        let retired: Set<String> = ["hey", "sort", "future"]
        let emptyLegacy: Set<String> = ["favorites", "tech", "misc", "work", "later", "news"]
        for node in nodes {
            guard case let .folder(folder) = node else {
                kept.append(node)
                continue
            }
            let key = folder.name.lowercased()
            if retired.contains(key) {
                changed = true
                continue
            }
            if emptyLegacy.contains(key), folder.children.isEmpty {
                changed = true
                continue
            }
            if LibraryDefaults.isQuickSave(folder.name) {
                var coerced = folder
                coerced.name = LibraryDefaults.quickSaveName
                if coerced.accent == nil { coerced.accent = LibraryDefaults.accents["Quick Save"] }
                if quickSave == nil {
                    quickSave = coerced
                } else {
                    quickSave?.children.append(contentsOf: coerced.children)
                }
                if coerced.name != folder.name { changed = true }
                continue
            }
            kept.append(node)
        }
        if quickSave == nil {
            quickSave = FolderNode(name: LibraryDefaults.quickSaveName, accent: LibraryDefaults.accents["Quick Save"], children: [])
            changed = true
        }
        var result: [LibraryNode] = [.folder(quickSave!)]
        result.append(contentsOf: kept)
        var names = Set(result.compactMap { node -> String? in
            if case let .folder(folder) = node { return folder.name.lowercased() }
            return nil
        })
        for name in LibraryDefaults.folderOrder where name != LibraryDefaults.quickSaveName {
            if !names.contains(name.lowercased()) {
                result.append(.folder(FolderNode(name: name, accent: LibraryDefaults.accents[name], children: [])))
                names.insert(name.lowercased())
                changed = true
            }
        }
        return (result, changed)
    }
}
