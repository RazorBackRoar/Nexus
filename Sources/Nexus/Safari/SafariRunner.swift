import Foundation

struct SafariRunResult: Sendable {
    var ok: Bool
    var message: String
    var alert: String?
    var urls: [String]
}

enum SafariRunner {
    /// Opens one Safari tab at a time. The pause keeps Safari from failing when many links fire at once.
    static func open(urls: [String], privateMode: Bool, delay: Double) async -> SafariRunResult {
        let urls = SafariScripts.allowed(urls)
        guard let first = urls.first else {
            return SafariRunResult(ok: false, message: "No links to open.", alert: nil, urls: [])
        }
        let pause = max(delay, 0.55)
        let firstScript = privateMode ? SafariScripts.privateWindow(first) : SafariScripts.newDocument(first)
        let firstResult = await run(firstScript)
        if !firstResult.ok {
            if privateMode {
                return SafariRunResult(
                    ok: false,
                    message: "Private Safari needs Accessibility permission.",
                    alert: "Could not open a Safari Private Window. Enable Accessibility for Nexus in System Settings → Privacy & Security, then try again. URLs were not opened in a standard window.",
                    urls: []
                )
            }
            return SafariRunResult(ok: false, message: "Safari did not open the links.", alert: firstResult.error, urls: [])
        }
        for url in urls.dropFirst() {
            try? await Task.sleep(nanoseconds: UInt64(pause * 1_000_000_000))
            let tabResult = await run(SafariScripts.newTab(url))
            if !tabResult.ok {
                return SafariRunResult(ok: false, message: "Some links did not open.", alert: tabResult.error, urls: [])
            }
        }
        return SafariRunResult(
            ok: true,
            message: privateMode ? "Opened in Private Safari" : "Opened in Safari",
            alert: nil,
            urls: []
        )
    }

    static func importTabs() async -> SafariRunResult {
        let result = await run(SafariScripts.allTabs)
        if !result.ok {
            return SafariRunResult(ok: false, message: "Could not read Safari tabs.", alert: result.error, urls: [])
        }
        let tabs = SafariScripts.parseTabs(result.output)
        return SafariRunResult(ok: true, message: "Imported tabs", alert: nil, urls: tabs.map(\.url))
    }

    private static func run(_ source: String) async -> (ok: Bool, output: String, error: String?) {
        await Task.detached {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
            process.arguments = ["-e", source]
            let stdout = Pipe()
            let stderr = Pipe()
            process.standardOutput = stdout
            process.standardError = stderr
            do {
                try process.run()
                process.waitUntilExit()
            } catch {
                return (false, "", error.localizedDescription)
            }
            let output = String(data: stdout.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            let error = String(data: stderr.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            if process.terminationStatus != 0 {
                return (false, output, error.isEmpty ? "Safari automation was denied." : error)
            }
            return (true, output, nil)
        }.value
    }
}
