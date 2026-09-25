import AppKit
import Combine
import SwiftUI
import UniformTypeIdentifiers

struct MainView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        @Bindable var model = model
        ZStack {
            StarfieldBackground()
            VStack(spacing: 8) {
                Text("Nexus")
                    .font(.system(size: 44, weight: .semibold, design: .default))
                    .tracking(2)
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(white: 0.98), Color(red: 0.72, green: 0.78, blue: 0.88), Color(white: 0.86)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                Text("Safari bookmark manager and batch URL opener")
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.72))
                NavigationSplitView {
                    SidebarView()
                        .navigationSplitViewColumnWidth(min: 240, ideal: 260, max: 320)
                } detail: {
                    DetailColumn()
                }
                .navigationSplitViewStyle(.balanced)
            }
            .padding(.top, 8)
        }
        .navigationTitle("")
        .toolbarBackground(.hidden, for: .windowToolbar)
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
        .sheet(isPresented: $model.showRename) { RenameSheet() }
        .confirmationDialog("Clear every URL in the list?", isPresented: $model.confirmClear, titleVisibility: .visible) {
            Button("Clear", role: .destructive) { model.confirmClearURLs() }
            Button("Cancel", role: .cancel) {}
        }
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
                Button("Load File") { model.importFile() }
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
                ColorActionButton(title: "Home", colors: [Color(hex: "#3B82F6"), Color(hex: "#1D4ED8")]) { model.goHome() }
                ColorActionButton(title: "Open All", colors: [Color(hex: "#10B981"), Color(hex: "#047857")]) { Task { await model.openAll() } }
                ColorActionButton(title: "Save", colors: [Color(hex: "#22D3EE"), Color(hex: "#0E7490")]) { model.showSaveGroup = true }
                ColorActionButton(title: "Import", colors: [Color(hex: "#818CF8"), Color(hex: "#4338CA")]) { model.importFile() }
                ColorActionButton(title: "Export", colors: [Color(hex: "#C084FC"), Color(hex: "#7E22CE")]) { model.exportFile() }
                ColorActionButton(title: "Clear", colors: [Color(hex: "#FB7185"), Color(hex: "#BE123C")]) { model.clearURLs() }
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
        .foregroundStyle(.white)
        .background(Color.black.opacity(0.28), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .background(KeyboardCatcher())
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
