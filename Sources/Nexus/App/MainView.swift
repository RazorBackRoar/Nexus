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
            StarfieldBackground(day: isDay)
            VStack(spacing: 6) {
                Text("Nexus")
                    .font(.system(size: 52, weight: .semibold, design: .rounded))
                    .tracking(1.8)
                    .foregroundStyle(
                        LinearGradient(
                            colors: isDay
                                ? [Color(red: 0.28, green: 0.12, blue: 0.48), Color(red: 0.45, green: 0.22, blue: 0.72)]
                                : [Color(white: 1), Color(red: 0.86, green: 0.80, blue: 1), Color(red: 0.72, green: 0.66, blue: 0.92)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .shadow(color: Color(red: 0.6, green: 0.4, blue: 1).opacity(isDay ? 0.25 : 0.55), radius: 18)
                Text("Safari bookmark manager and batch URL opener")
                    .font(.system(size: 13))
                    .foregroundStyle(isDay ? Color(red: 0.28, green: 0.16, blue: 0.42).opacity(0.75) : .white.opacity(0.62))
                    .padding(.bottom, 6)
                HStack(spacing: 16) {
                    SidebarView()
                        .frame(width: 272)
                    DetailColumn()
                }
                .background {
                    Ellipse()
                        .fill(
                            RadialGradient(
                                colors: [Color(red: 0.55, green: 0.30, blue: 1).opacity(isDay ? 0.18 : 0.32), .clear],
                                center: .center,
                                startRadius: 0,
                                endRadius: 520
                            )
                        )
                        .blur(radius: 40)
                        .allowsHitTesting(false)
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

    private var isDay: Bool {
        switch model.settings.appearance {
        case "light": return true
        case "dark": return false
        default: return colorScheme == .light
        }
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
                ColorActionButton(title: "Load File", colors: [Color(hex: "#7C5CFF"), Color(hex: "#5B3FD9")]) { model.importFile() }
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
            .glass(radius: 16, tint: Color(red: 0.55, green: 0.35, blue: 0.85), opacity: 0.04, elevated: false)

            HStack(spacing: 12) {
                Spacer(minLength: 0)
                ColorActionButton(title: "Home", colors: [Color(hex: "#5B8DEF"), Color(hex: "#2F5FD0")]) { model.goHome() }
                ColorActionButton(title: "Open All", colors: [Color(hex: "#2EC4A0"), Color(hex: "#158F72")]) { Task { await model.openAll() } }
                ColorActionButton(title: "Save", colors: [Color(hex: "#38BDF8"), Color(hex: "#0E86B8")]) { model.showSaveGroup = true }
                ColorActionButton(title: "Import", colors: [Color(hex: "#9B7AE8"), Color(hex: "#6A4BC4")]) { model.importFile() }
                ColorActionButton(title: "Export", colors: [Color(hex: "#E57BC4"), Color(hex: "#B24A93")]) { model.exportFile() }
                ColorActionButton(title: "Clear", colors: [Color(hex: "#F07070"), Color(hex: "#B83A3A")]) { model.clearURLs() }
                Spacer(minLength: 0)
            }

            HStack {
                Text(model.status)
                    .font(.system(size: 12))
                    .foregroundStyle(.white.opacity(0.62))
                Spacer()
                Picker("Safari", selection: Bindable(model).settings.privateByDefault) {
                    Text("Standard Safari").tag(false)
                    Text("Private Safari").tag(true)
                }
                .pickerStyle(.segmented)
                .labelsHidden()
                .frame(width: 260)
                .onChange(of: model.settings.privateByDefault) { _, _ in model.settings.save() }
            }
        }
        .padding(18)
        .foregroundStyle(.white)
        .glass(radius: 20, opacity: 0.05)
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
