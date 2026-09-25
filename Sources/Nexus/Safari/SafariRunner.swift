import Foundation

struct SafariRunResult: Sendable {
    var ok: Bool
    var message: String
    var alert: String?
    var urls: [String]
}

enum SafariRunner {
    static func open(plan: OpenPlan, privateMode: Bool, delayMin: Double, delayMax: Double) async -> SafariRunResult {
        let batches = plan.batches
        guard !batches.isEmpty else {
            return SafariRunResult(ok: false, message: "No links to open.", alert: nil, urls: [])
        }
        if privateMode {
            guard let first = batches.first?.first else {
                return SafariRunResult(ok: false, message: "No links to open.", alert: nil, urls: [])
            }
            let script = SafariScripts.privateWindow(first)
            let firstResult = await run(script)
            if !firstResult.ok {
                return SafariRunResult(
                    ok: false,
                    message: "Private Safari needs Accessibility permission.",
                    alert: "Could not open a Safari Private Window. Enable Accessibility for Nexus in System Settings → Privacy & Security, then try again. URLs were not opened in a standard window.",
                    urls: []
                )
            }
            let rest = batches.flatMap { $0 }.dropFirst()
            if !rest.isEmpty {
                let tabScript = SafariScripts.openInFrontWindow(Array(rest))
                let tabResult = await run(tabScript.replacingOccurrences(of: "make new document", with: "make new tab"))
                if !tabResult.ok {
                    return SafariRunResult(ok: false, message: "Some links did not open.", alert: tabResult.error, urls: [])
                }
            }
            return SafariRunResult(ok: true, message: "Opened in Private Safari", alert: nil, urls: [])
        }
        for (index, batch) in batches.enumerated() {
            let script = SafariScripts.openInFrontWindow(batch)
            let result = await run(script)
            if !result.ok {
                return SafariRunResult(ok: false, message: "Safari did not open the links.", alert: result.error, urls: [])
            }
            if index + 1 < batches.count {
                let low = min(delayMin, delayMax)
                let high = max(delayMin, delayMax)
                let span = high - low
                let delay = low + Double.random(in: 0...max(span, 0.01))
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }
        }
        return SafariRunResult(ok: true, message: "Opened in Safari", alert: nil, urls: [])
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
