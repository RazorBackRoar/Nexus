import AppKit
import Combine
import SwiftUI
import UniformTypeIdentifiers

struct MainView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        ZStack {
            StarfieldBackground(bright: bright)
            VStack(spacing: 6) {
                Text("Nexus")
                    .font(.system(size: 52, weight: .semibold, design: .rounded))
                    .tracking(1.8)
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(white: 1), Color(red: 0.86, green: 0.90, blue: 1), Color(red: 0.70, green: 0.76, blue: 0.94)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .shadow(color: (bright ? Color(red: 1, green: 0.78, blue: 0.45) : Color(red: 0.45, green: 0.45, blue: 1)).opacity(0.45), radius: 20)
                Text("Safari bookmark manager and batch URL opener")
                    .font(.system(size: 13))
                    .foregroundStyle(.white.opacity(0.72))
                    .padding(.bottom, 6)
                HStack(spacing: 16) {
                    SidebarView()
                        .frame(width: 272)
                    DetailColumn()
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
            }
            .padding(.top, 2)
        }
        .navigationTitle("")
        .toolbar {
            ToolbarItem(placement: .principal) {
                Color.clear.frame(width: 1, height: 1)
            }
        }
        .toolbarBackground(.hidden, for: .windowToolbar)
        .environment(\.nexusBright, bright)
        .animation(.easeInOut(duration: 0.6), value: bright)
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

    private var bright: Bool {
        !model.settings.privateByDefault
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
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("Paste URLs. Open in Safari.")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.92))
                Spacer()
                ColorActionButton(title: "Load File", colors: [Color(hex: "#8C7BFF")]) { model.importFile() }
                    .scaleEffect(0.85)
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
            .glass(radius: 16, elevated: false)

            HStack(spacing: 12) {
                Spacer(minLength: 0)
                ColorActionButton(title: "Home", colors: [Color(hex: "#4DA3FF")]) { model.goHome() }
                ColorActionButton(title: "Open All", colors: [Color(hex: "#3DDC97")]) { Task { await model.openAll() } }
                ColorActionButton(title: "Save", colors: [Color(hex: "#2EC4B6")]) { model.showSaveGroup = true }
                ColorActionButton(title: "Import", colors: [Color(hex: "#8C7BFF")]) { model.importFile() }
                ColorActionButton(title: "Export", colors: [Color(hex: "#F5A623")]) { model.exportFile() }
                ColorActionButton(title: "Clear", colors: [Color(hex: "#FF5A52")]) { model.clearURLs() }
                Spacer(minLength: 0)
            }

            HStack {
                Text(model.status)
                    .font(.system(size: 12))
                    .foregroundStyle(.white.opacity(0.62))
                Spacer()
                SafariModeSwitch(isPrivate: Binding(
                    get: { model.settings.privateByDefault },
                    set: { value in
                        model.settings.privateByDefault = value
                        model.settings.save()
                    }
                ))
            }
        }
        .padding(18)
        .foregroundStyle(.white)
        .glass(radius: 20)
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
