import AppKit
import SwiftUI

@main
struct NexusApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            MainView()
                .environment(model)
                .frame(minWidth: 1100, minHeight: 720)
        }
        .defaultSize(width: 1200, height: 760)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Folder…") { model.showNewFolder = true }
                    .keyboardShortcut("n", modifiers: .command)
            }
            CommandGroup(after: .pasteboard) {
                Button("Copy Rich Links") { model.copyRichLinks() }
                    .keyboardShortcut("c", modifiers: [.command, .shift])
                Button("Clear URL List") { model.clearURLs() }
                    .keyboardShortcut(.delete, modifiers: .command)
            }
            CommandMenu("Safari") {
                Button("Open All URLs in Safari") { Task { await model.openAll() } }
                    .keyboardShortcut("o", modifiers: [.command, .shift])
                Button("Import Safari Tabs") { Task { await model.importSafariTabs() } }
                    .keyboardShortcut("i", modifiers: [.command, .shift])
                Toggle("Private Browsing", isOn: Binding(
                    get: { model.settings.privateByDefault },
                    set: { value in
                        model.settings.privateByDefault = value
                        model.settings.save()
                    }
                ))
            }
            CommandMenu("Tools") {
                Button("Bookmark Health") { model.showHealth = true }
                    .keyboardShortcut("h", modifiers: [.command, .shift])
            }
            CommandGroup(replacing: .help) {
                Button("Keyboard Shortcuts") { model.showShortcuts = true }
                    .keyboardShortcut("/", modifiers: .command)
                Button("Check for Updates…") { Task { await checkUpdates() } }
                Button("About Nexus") { model.showAbout = true }
            }
        }

        Settings {
            SettingsView()
                .environment(model)
        }
    }

    private func checkUpdates() async {
        let current = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "3.0.0"
        model.alertMessage = UpdateChecker.compare(current: current, latestTag: current).message
    }
}
