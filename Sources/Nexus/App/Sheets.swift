import AppKit
import SwiftUI

struct NewFolderSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var accent = "#5B8DEF"
    private let swatches = ["#E5738A", "#D4A05A", "#5B8DEF", "#E85A5A", "#8A95A8", "#2A2A35", "#F0F4FA", "#5BA86A", "#2EC4A0"]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("New Folder").font(.title2.weight(.semibold))
            TextField("Folder name", text: $name)
                .textFieldStyle(.roundedBorder)
            HStack(spacing: 8) {
                ForEach(swatches, id: \.self) { hex in
                    Button {
                        accent = hex
                    } label: {
                        Circle().fill(Color(hex: hex)).frame(width: 22, height: 22)
                            .overlay(Circle().strokeBorder(accent == hex ? Color.primary : Color.clear, lineWidth: 2))
                    }
                    .buttonStyle(.plain)
                }
            }
            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                Button("Create") {
                    model.addFolder(name: name, accent: accent)
                    dismiss()
                }
                .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 460)
    }
}

struct SaveGroupSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var folder = "Tech"

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Save Group").font(.title2.weight(.semibold))
            TextField("Group name", text: $name)
                .textFieldStyle(.roundedBorder)
            Picker("Folder", selection: $folder) {
                ForEach(folderNames, id: \.self) { Text($0).tag($0) }
            }
            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                Button("Save") {
                    model.saveGroup(name: name, folderName: folder)
                    dismiss()
                }
                .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 420)
        .onAppear {
            if !LibraryDefaults.isQuickSave(model.selectedFolder) {
                folder = model.selectedFolder
            }
        }
    }

    private var folderNames: [String] {
        model.folders.compactMap { node in
            if case let .folder(folder) = node { return folder.name }
            return nil
        }
    }
}

struct HealthSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var checks: [LinkCheck] = []
    @State private var scanned = 0
    @State private var scanning = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Bookmark Health").font(.title2.weight(.semibold))
            TabView {
                duplicatePane
                    .tabItem { Text("Duplicates") }
                deadPane
                    .tabItem { Text("Dead Links") }
            }
            HStack {
                Spacer()
                Button("Done") { dismiss() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 680, height: 480)
    }

    private var duplicatePane: some View {
        let groups = HealthScanner.duplicates(folders: model.folders, groups: model.groups)
        return Group {
            if groups.isEmpty {
                Text("No duplicate links.")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(groups, id: \.first?.url) { group in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(group.first?.url ?? "")
                            .font(.system(.body, design: .monospaced))
                        Text(group.map { "\($0.name) · \($0.container)" }.joined(separator: ", "))
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    private var deadPane: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Button(scanning ? "Checking…" : "Check Links") { Task { await scan() } }
                    .disabled(scanning)
                if scanning {
                    Text("\(scanned) checked")
                        .foregroundStyle(.secondary)
                }
            }
            List(checks) { item in
                HStack {
                    VStack(alignment: .leading) {
                        Text(item.name).lineLimit(1)
                        Text(item.container).font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(item.alive ? "OK" : (item.error ?? "Failed"))
                        .foregroundStyle(item.alive ? .green : .red)
                }
            }
        }
    }

    private func scan() async {
        scanning = true
        scanned = 0
        let targets = HealthScanner.linkTargets(folders: model.folders, groups: model.groups)
        checks = []
        for target in targets {
            if Task.isCancelled { break }
            let result = await HealthScanner.check(target)
            checks.append(result)
            scanned += 1
        }
        scanning = false
    }
}

struct ShortcutsSheet: View {
    @Environment(\.dismiss) private var dismiss
    private let rows = [
        ("⌘N", "New Folder"),
        ("⌘S", "Save Group"),
        ("⌘⇧S", "Quick Save"),
        ("⌘⇧O", "Open All"),
        ("⌘⇧I", "Import Safari Tabs"),
        ("⌘O", "Import File"),
        ("⌘E", "Export"),
        ("⌘⇧C", "Copy Rich Links"),
        ("⌘⌫", "Clear List"),
        ("⌘Z", "Undo"),
        ("⌘1", "URL Workspace"),
        ("⌘2", "Quick Save"),
        ("⌘⇧H", "Bookmark Health"),
        ("⌘/", "Keyboard Shortcuts"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Keyboard Shortcuts").font(.title2.weight(.semibold))
            Grid(alignment: .leading, horizontalSpacing: 24, verticalSpacing: 8) {
                ForEach(rows, id: \.0) { shortcut, action in
                    GridRow {
                        Text(shortcut).font(.body.monospaced()).frame(width: 80, alignment: .leading)
                        Text(action)
                    }
                }
            }
            HStack {
                Spacer()
                Button("Done") { dismiss() }.keyboardShortcut(.cancelAction)
            }
        }
        .padding(20)
        .frame(width: 420)
    }
}

struct AboutSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 12) {
            Text("Nexus").font(.largeTitle.weight(.semibold))
            Text("Version 3.0.0")
            Text("Safari bookmark manager and batch URL opener.")
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Done") { dismiss() }
                .keyboardShortcut(.defaultAction)
        }
        .padding(28)
        .frame(width: 380)
    }
}

struct SettingsView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        TabView {
            Form {
                Picker("Appearance", selection: $model.settings.appearance) {
                    Text("System").tag("system")
                    Text("Light").tag("light")
                    Text("Dark").tag("dark")
                }
            }
            .padding(20)
            .tabItem { Text("Appearance") }

            Form {
                Stepper("Batch size: \(model.settings.batchSize)", value: $model.settings.batchSize, in: 1...100)
                TextField("Minimum delay", value: $model.settings.delayMin, format: .number)
                TextField("Maximum delay", value: $model.settings.delayMax, format: .number)
                Toggle("Pause longer between links on the same site", isOn: $model.settings.staggerSameSite)
                Toggle("Open in Private Safari by default", isOn: $model.settings.privateByDefault)
            }
            .padding(20)
            .tabItem { Text("Safari") }

            Form {
                Toggle("Add copied links automatically", isOn: $model.settings.watchClipboard)
                Toggle("Keep URLs out of logs", isOn: .constant(true))
                    .disabled(true)
            }
            .padding(20)
            .tabItem { Text("Privacy") }

            Form {
                Toggle("Skip duplicate URLs", isOn: $model.settings.skipDuplicateRichLinks)
                Toggle("Sort links alphabetically", isOn: $model.settings.sortRichLinks)
                Toggle("Keep blank lines", isOn: $model.settings.keepBlankLines)
            }
            .padding(20)
            .tabItem { Text("Rich Links") }

            Form {
                LabeledContent("Library") {
                    Text(model.libraryDirectory.path)
                        .font(.callout)
                        .textSelection(.enabled)
                }
                Button("Show in Finder") {
                    NSWorkspace.shared.activateFileViewerSelecting([model.libraryDirectory])
                }
                Stepper("Backup copies to keep: \(model.settings.backupCount)", value: $model.settings.backupCount, in: 1...50)
            }
            .padding(20)
            .tabItem { Text("Storage") }
        }
        .frame(width: 560, height: 320)
        .onChange(of: model.settings) { _, newValue in newValue.save() }
    }
}

struct RenameSheet: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Rename Folder").font(.title2.weight(.semibold))
            TextField("Folder name", text: Bindable(model).renameText)
                .textFieldStyle(.roundedBorder)
            HStack {
                Spacer()
                Button("Cancel") { dismiss() }
                Button("Rename") {
                    model.renameFolder(from: model.renameTarget, to: model.renameText)
                    dismiss()
                }
                .disabled(model.renameText.trimmingCharacters(in: .whitespaces).isEmpty)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 420)
    }
}

extension Color {
    init(hex: String) {
        var text = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.hasPrefix("#") { text.removeFirst() }
        var value: UInt64 = 0
        Scanner(string: text).scanHexInt64(&value)
        let red = Double((value >> 16) & 0xFF) / 255
        let green = Double((value >> 8) & 0xFF) / 255
        let blue = Double(value & 0xFF) / 255
        self.init(red: red, green: green, blue: blue)
    }
}
