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
        .windowToolbarStyle(.unified(showsTitle: false))
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Folder…") { model.showNewFolder = true }
                    .keyboardShortcut("n", modifiers: .command)
                Divider()
                Button("Import URLs from File…") { model.importFile() }
                    .keyboardShortcut("o", modifiers: .command)
                Button("Import Safari Tabs") { Task { await model.importSafariTabs() } }
                    .keyboardShortcut("i", modifiers: [.command, .shift])
                Button("Save URLs as Group…") { model.showSaveGroup = true }
                    .keyboardShortcut("s", modifiers: .command)
                Button("Quick Save") { model.quickSave() }
                    .keyboardShortcut("s", modifiers: [.command, .shift])
                Button("Export URLs…") { model.exportFile() }
                    .keyboardShortcut("e", modifiers: .command)
            }
            CommandGroup(after: .pasteboard) {
                Button("Copy Rich Links") { model.copyRichLinks() }
                    .keyboardShortcut("c", modifiers: [.command, .shift])
                Button("Clear URL List") { model.clearURLs() }
                    .keyboardShortcut(.delete, modifiers: .command)
            }
            CommandMenu("View") {
                Button("URL Workspace") { model.goHome() }
                    .keyboardShortcut("1", modifiers: .command)
                Button("Quick Save") { model.selectFolder(LibraryDefaults.quickSaveName) }
                    .keyboardShortcut("2", modifiers: .command)
                Divider()
                Button("Find in Bookmarks") { model.filter = "" }
                    .keyboardShortcut("f", modifiers: .command)
                Divider()
                Button("System Appearance") { model.settings.appearance = "system"; model.settings.save() }
                Button("Light Purple") { model.settings.appearance = "light"; model.settings.save() }
                Button("Deep Purple") { model.settings.appearance = "dark"; model.settings.save() }
            }
            CommandMenu("Safari") {
                Button("Open All URLs in Safari") { Task { await model.openAll() } }
                    .keyboardShortcut("o", modifiers: [.command, .shift])
                Button("Import Safari Tabs") { Task { await model.importSafariTabs() } }
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
                SettingsLink {
                    Text("Settings…")
                }
                .keyboardShortcut(",", modifiers: .command)
            }
            CommandGroup(replacing: .help) {
                Button("Keyboard Shortcuts") { model.showShortcuts = true }
                    .keyboardShortcut("/", modifiers: .command)
                Button("Check for Updates…") { Task { await checkUpdates() } }
                Divider()
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
        model.alertMessage = await UpdateChecker.fetchLatest(current: current).message
    }
}
