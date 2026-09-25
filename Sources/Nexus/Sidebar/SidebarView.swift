import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct SidebarView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Bookmarks")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.92))
                Spacer()
                Button {
                    model.showNewFolder = true
                } label: {
                    Image(systemName: "plus")
                        .font(.system(size: 12, weight: .semibold))
                        .frame(width: 26, height: 26)
                }
                .help("New Folder")
                .buttonStyle(.plain)
                .interactiveGlass(accent: Color(hex: "#9B7AE8"), radius: 8, lift: 1.08, sparkles: false)
            }
            TextField("Filter Bookmarks", text: $model.filter)
                .textFieldStyle(.plain)
                .padding(.horizontal, 10)
                .frame(height: 30)
                .glass(radius: 9, opacity: 0.08, elevated: false)
            ScrollView {
                LazyVStack(spacing: 8) {
                    ForEach(Array(model.visibleFolders.enumerated()), id: \.offset) { _, node in
                        if case let .folder(node) = node {
                            folderBlock(node)
                        }
                    }
                }
                .padding(.vertical, 2)
            }
            .scrollIndicators(.hidden)
        }
        .padding(16)
        .foregroundStyle(.white)
        .glass(radius: 20, opacity: 0.05)
    }

    @ViewBuilder
    private func folderBlock(_ folder: FolderNode) -> some View {
        let accent = Color(hex: folder.accent ?? "#5B8DEF")
        let selected = model.selectedFolder.caseInsensitiveCompare(folder.name) == .orderedSame
        Button {
            model.selectFolder(folder.name)
        } label: {
            GlassRow(accent: accent, selected: selected) {
                HStack(spacing: 10) {
                    Text(folder.name)
                        .font(.system(size: 13, weight: .semibold))
                        .padding(.leading, 10)
                    Spacer()
                    if folder.children.count > 0 {
                        Text("\(folder.children.count)")
                            .font(.system(size: 11, weight: .medium))
                            .monospacedDigit()
                            .foregroundStyle(.white.opacity(0.7))
                            .padding(.horizontal, 7)
                            .padding(.vertical, 2)
                            .background(accent.opacity(0.3), in: Capsule())
                    }
                }
            }
        }
        .buttonStyle(.plain)
        .contextMenu { folderMenu(folder) }

        if selected, !LibraryDefaults.isQuickSave(folder.name) {
            ForEach(Array(folder.children.enumerated()), id: \.offset) { _, child in
                childRow(child, folder: folder)
                    .padding(.leading, 16)
            }
        }
    }

    @ViewBuilder
    private func childRow(_ node: LibraryNode, folder: FolderNode) -> some View {
        switch node {
        case let .bookmark(item):
            Button {
                Task { await model.openOne(item.url) }
            } label: {
                HStack(spacing: 8) {
                    Circle().fill(Color(hex: item.accent ?? folder.accent ?? "#5B8DEF")).frame(width: 8, height: 8)
                    Text(item.name).lineLimit(1)
                }
                .frame(maxWidth: .infinity, minHeight: 36, alignment: .leading)
            }
            .buttonStyle(.plain)
            .contextMenu {
                Button("Open") { Task { await model.openOne(item.url) } }
                Button("Copy URL") { model.copyURLs([item.url]) }
            }
        case let .group(marker):
            let count = model.groupItems(marker.id).count
            Button {
                Task {
                    await model.openMany(model.groupItems(marker.id).map(\.url))
                }
            } label: {
                HStack {
                    Circle().fill(Color(hex: folder.accent ?? "#5B8DEF")).frame(width: 8, height: 8)
                    Text(model.groupName(marker.id)).lineLimit(1)
                    Spacer()
                    if count > 0 {
                        Text("\(count)").foregroundStyle(.secondary)
                    }
                }
                .frame(minHeight: 36)
            }
            .buttonStyle(.plain)
        case let .quickSave(entry):
            Text(entry.createdAt)
                .font(.callout)
                .frame(minHeight: 36, alignment: .leading)
        default:
            EmptyView()
        }
    }

    @ViewBuilder
    private func folderMenu(_ folder: FolderNode) -> some View {
        if !LibraryDefaults.isQuickSave(folder.name) {
            Button("Rename") { model.beginRename(folder.name) }
            Button("Delete", role: .destructive) { model.deleteFolder(named: folder.name) }
        }
    }
}

struct EmptyURLState: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(spacing: 14) {
            Spacer()
            Image(systemName: "sparkles")
                .font(.system(size: 30, weight: .light))
                .foregroundStyle(
                    LinearGradient(colors: [Color(hex: "#C9B8FF"), Color(hex: "#7C5CFF")], startPoint: .top, endPoint: .bottom)
                )
                .shadow(color: Color(hex: "#7C5CFF").opacity(0.7), radius: 14)
            Text("Paste URLs to get started")
                .font(.system(size: 19, weight: .semibold))
                .foregroundStyle(.white.opacity(0.95))
            Text("Copied links show up here. Paste, import your open Safari tabs, or drop a text file.")
                .font(.system(size: 13))
                .foregroundStyle(.white.opacity(0.62))
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
            HStack(spacing: 12) {
                ColorActionButton(title: "Paste from Clipboard", colors: [Color(hex: "#5B8DEF"), Color(hex: "#2F5FD0")]) {
                    model.ingest(URLExtractor.extract(from: NSPasteboard.general.string(forType: .string) ?? ""))
                }
                ColorActionButton(title: "Import Safari Tabs", colors: [Color(hex: "#2EC4A0"), Color(hex: "#158F72")]) {
                    Task { await model.importSafariTabs() }
                }
            }
            .padding(.top, 6)
            Spacer()
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onDrop(of: [.plainText, .url], isTargeted: nil) { providers in
            guard let provider = providers.first else { return false }
            _ = provider.loadObject(ofClass: String.self) { text, _ in
                let value = text ?? ""
                Task { @MainActor in
                    model.ingest(URLExtractor.extract(from: value))
                }
            }
            return true
        }
    }
}

struct URLList: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 6) {
                ForEach(model.urls) { row in
                    HStack(spacing: 12) {
                        Text(row.url)
                            .font(.system(.body, design: .monospaced))
                            .lineLimit(1)
                            .textSelection(.enabled)
                        Spacer(minLength: 12)
                        Text(row.status.rawValue)
                            .font(.callout.weight(.medium))
                            .foregroundStyle(statusColor(row.status))
                    }
                    .frame(minHeight: 36)
                    .padding(.horizontal, 14)
                    .contentShape(Rectangle())
                    .interactiveGlass(accent: statusColor(row.status), radius: 10, intensity: 0.45, lift: 1.006, sparkles: false, pressable: false)
                    .padding(.horizontal, 10)
                    .onTapGesture(count: 2) { Task { await model.openOne(row.url) } }
                }
            }
            .padding(.vertical, 8)
        }
    }

    private func statusColor(_ status: URLStatus) -> Color {
        switch status {
        case .ready: return .green
        case .opening: return .orange
        case .opened: return .blue
        case .failed: return .red
        }
    }
}

struct QuickSaveList: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(model.quickSaveEntries()) { entry in
                    QuickSaveCard(entry: entry)
                }
            }
            .padding(16)
        }
    }
}

private struct QuickSaveCard: View {
    @Environment(AppModel.self) private var model
    let entry: QuickSaveEntry
    @State private var notes: String = ""

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text(dateLine)
                    .font(.headline)
                Text(timeLine)
                    .foregroundStyle(.secondary)
            }
            .frame(width: 108, alignment: .leading)
            VStack(alignment: .leading, spacing: 6) {
                ForEach(entry.urls, id: \.self) { url in
                    Button(url) { Task { await model.openOne(url) } }
                        .buttonStyle(.plain)
                        .font(.system(.callout, design: .monospaced))
                        .foregroundStyle(.blue)
                        .lineLimit(1)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            TextField("Notes", text: $notes, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .frame(width: 180)
                .onSubmit { model.updateQuickSaveNotes(id: entry.id, notes: notes) }
        }
        .padding(14)
        .interactiveGlass(accent: Color(hex: "#2EC4A0"), radius: 14, intensity: 0.55, lift: 1.008, sparkles: false, pressable: false)
        .onAppear { notes = entry.notes }
        .onChange(of: notes) { _, newValue in
            model.updateQuickSaveNotes(id: entry.id, notes: newValue)
        }
        .contextMenu {
            Button("Copy URLs") { model.copyURLs(entry.urls) }
            Button("Load into URL List") { model.loadQuickSave(id: entry.id) }
            Button("Delete", role: .destructive) { model.deleteQuickSave(id: entry.id) }
        }
    }

    private var dateLine: String {
        guard let date = ISO8601.date(from: entry.createdAt) else { return entry.createdAt }
        return date.formatted(.dateTime.month(.abbreviated).day().year(.twoDigits))
    }

    private var timeLine: String {
        guard let date = ISO8601.date(from: entry.createdAt) else { return "" }
        return date.formatted(date: .omitted, time: .shortened)
    }
}

