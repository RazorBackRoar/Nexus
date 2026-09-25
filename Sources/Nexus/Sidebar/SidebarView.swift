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
                    .font(.title3.weight(.semibold))
                Spacer()
                Button {
                    model.showNewFolder = true
                } label: {
                    Image(systemName: "plus")
                }
                .help("New Folder")
                .buttonStyle(.bordered)
            }
            TextField("Filter Bookmarks", text: $model.filter)
                .textFieldStyle(.roundedBorder)
            List {
                ForEach(Array(model.visibleFolders.enumerated()), id: \.offset) { _, node in
                    if case let .folder(folder) = node {
                        folderBlock(folder)
                    }
                }
                .onMove(perform: model.moveFolders)
            }
            .listStyle(.sidebar)
            .scrollContentBackground(.hidden)
        }
        .padding(16)
    }

    @ViewBuilder
    private func folderBlock(_ folder: FolderNode) -> some View {
        Button {
            model.selectFolder(folder.name)
        } label: {
            HStack(spacing: 10) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color(hex: folder.accent ?? "#5B8DEF"))
                    .frame(width: 3, height: 22)
                Text(folder.name)
                    .font(.body.weight(.semibold))
                Spacer()
                if folder.children.count > 0 {
                    Text("\(folder.children.count)")
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                }
            }
            .frame(minHeight: 44)
            .padding(.horizontal, 8)
            .background(
                model.selectedFolder.caseInsensitiveCompare(folder.name) == .orderedSame
                    ? Color.accentColor.opacity(0.16)
                    : Color.clear,
                in: RoundedRectangle(cornerRadius: 10, style: .continuous)
            )
        }
        .buttonStyle(.plain)
        .contextMenu { folderMenu(folder) }

        if model.selectedFolder.caseInsensitiveCompare(folder.name) == .orderedSame,
           !LibraryDefaults.isQuickSave(folder.name) {
            ForEach(Array(folder.children.enumerated()), id: \.offset) { _, child in
                childRow(child, folder: folder)
                    .padding(.leading, 18)
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
                    for item in model.groupItems(marker.id) {
                        await model.openOne(item.url)
                    }
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
            Button("Rename") { model.renameFolder(from: folder.name, to: folder.name + " ") }
            Button("Delete", role: .destructive) { model.deleteFolder(named: folder.name) }
        }
    }
}

struct EmptyURLState: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            Text("Paste URLs to get started")
                .font(.title2.weight(.semibold))
            Text("Copied links show up here. Paste, import your open Safari tabs, or drop a text file.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 460)
            HStack(spacing: 12) {
                Button("Paste from Clipboard") {
                    model.ingest(URLExtractor.extract(from: NSPasteboard.general.string(forType: .string) ?? ""))
                }
                Button("Import Safari Tabs") { Task { await model.importSafariTabs() } }
            }
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
            LazyVStack(spacing: 2) {
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
        .background(.background, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(Color.primary.opacity(0.08)))
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

