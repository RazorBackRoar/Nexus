import AppKit
import Combine
import SwiftUI
import UniformTypeIdentifiers

struct MainView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        @Bindable var model = model
        NavigationSplitView {
            SidebarView()
                .navigationSplitViewColumnWidth(min: 240, ideal: 260, max: 320)
        } detail: {
            DetailColumn()
        }
        .navigationTitle("Nexus")
        .tint(Color(red: 0.10, green: 0.27, blue: 0.49))
        .background(WindowFrameSaver())
        .alert("Nexus", isPresented: Binding(
            get: { model.alertMessage != nil },
            set: { if !$0 { model.alertMessage = nil } }
        )) {
            Button("OK", role: .cancel) { model.alertMessage = nil }
        } message: {
            Text(model.alertMessage ?? "")
        }
        .sheet(isPresented: $model.showNewFolder) { NewFolderSheet() }
        .sheet(isPresented: $model.showSaveGroup) { SaveGroupSheet() }
        .sheet(isPresented: $model.showHealth) { HealthSheet() }
        .sheet(isPresented: $model.showShortcuts) { ShortcutsSheet() }
        .sheet(isPresented: $model.showAbout) { AboutSheet() }
        .onAppear {
            applyAppearance()
            model.status = model.urls.isEmpty ? "Waiting for pasted URLs" : "\(model.urls.count) URLs"
        }
        .onChange(of: model.settings.appearance) { _, _ in applyAppearance() }
        .onReceive(Timer.publish(every: 1.2, on: .main, in: .common).autoconnect()) { _ in
            watchClipboard()
        }
    }

    private func applyAppearance() {
        let name: NSAppearance.Name? = switch model.settings.appearance {
        case "dark": .darkAqua
        case "light": .aqua
        default: nil
        }
        NSApp.appearance = name.map { NSAppearance(named: $0) } ?? nil
    }

    private func watchClipboard() {
        guard model.settings.watchClipboard else { return }
        guard let text = NSPasteboard.general.string(forType: .string), !text.isEmpty else { return }
        let key = "nexus.lastClipboard"
        if UserDefaults.standard.string(forKey: key) == text { return }
        let found = URLExtractor.extract(from: text)
        guard !found.isEmpty else { return }
        UserDefaults.standard.set(text, forKey: key)
        model.ingest(found)
    }
}

private struct WindowFrameSaver: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            view.window?.setFrameAutosaveName("NexusMainWindow")
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}

struct DetailColumn: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .firstTextBaseline) {
                Text("Paste URLs. Open in Safari.")
                    .font(.title3.weight(.semibold))
                Spacer()
                Button("Load File") { loadFile() }
            }
            Group {
                if model.showQuickSave {
                    QuickSaveList()
                } else if model.urls.isEmpty {
                    EmptyURLState()
                } else {
                    URLList()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(.background.secondary, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .strokeBorder(Color.primary.opacity(0.08))
            )

            HStack(spacing: 12) {
                Spacer(minLength: 0)
                action("Home") { model.goHome() }
                action("Open All") { Task { await model.openAll() } }
                action("Save") { model.showSaveGroup = true }
                action("Import") { loadFile() }
                action("Export") { exportFile() }
                action("Clear") { model.clearURLs() }
                Spacer(minLength: 0)
            }

            HStack {
                Text(model.status)
                    .foregroundStyle(.secondary)
                Spacer()
                Picker("Safari", selection: Bindable(model).settings.privateByDefault) {
                    Text("Standard Safari").tag(false)
                    Text("Private Safari").tag(true)
                }
                .pickerStyle(.segmented)
                .frame(width: 280)
                .onChange(of: model.settings.privateByDefault) { _, _ in model.settings.save() }
            }
        }
        .padding(20)
        .background(KeyboardCatcher())
    }

    private func action(_ title: String, perform: @escaping () -> Void) -> some View {
        Button(title, action: perform)
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .frame(minWidth: 108)
    }

    private func loadFile() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.plainText, .commaSeparatedText]
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            let text = (try? String(contentsOf: url, encoding: .utf8)) ?? ""
            model.ingest(URLExtractor.parseFile(name: url.lastPathComponent, text: text))
        }
    }

    private func exportFile() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.plainText, .commaSeparatedText]
        panel.nameFieldStringValue = "nexus-urls.txt"
        if panel.runModal() == .OK, let url = panel.url {
            model.exportURLs(to: url)
        }
    }
}

private struct KeyboardCatcher: NSViewRepresentable {
    @Environment(AppModel.self) private var model

    func makeNSView(context: Context) -> Catcher {
        let view = Catcher()
        view.onPaste = { model.ingest(URLExtractor.extract(from: NSPasteboard.general.string(forType: .string) ?? "")) }
        view.onUndo = { model.undo() }
        view.onQuickSave = { model.quickSave() }
        view.onHome = { model.goHome() }
        view.onQuickSaveView = { model.selectFolder(LibraryDefaults.quickSaveName) }
        return view
    }

    func updateNSView(_ nsView: Catcher, context: Context) {}

    final class Catcher: NSView {
        var onPaste: () -> Void = {}
        var onUndo: () -> Void = {}
        var onQuickSave: () -> Void = {}
        var onHome: () -> Void = {}
        var onQuickSaveView: () -> Void = {}

        override var acceptsFirstResponder: Bool { true }

        override func keyDown(with event: NSEvent) {
            let command = event.modifierFlags.contains(.command)
            let shift = event.modifierFlags.contains(.shift)
            switch event.charactersIgnoringModifiers?.lowercased() {
            case "v" where command && !shift:
                onPaste()
            case "z" where command:
                onUndo()
            case "s" where command && shift:
                onQuickSave()
            case "h", "1" where command && !shift:
                onHome()
            case "2" where command:
                onQuickSaveView()
            default:
                super.keyDown(with: event)
            }
        }
    }
}
