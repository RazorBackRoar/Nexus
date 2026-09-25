import Foundation

struct NexusSettings: Equatable, Sendable {
    var appearance: String
    var batchSize: Int
    var delayMin: Double
    var delayMax: Double
    var staggerSameSite: Bool
    var privateByDefault: Bool
    var watchClipboard: Bool
    var skipDuplicateRichLinks: Bool
    var sortRichLinks: Bool
    var keepBlankLines: Bool
    var backupCount: Int

    static let storageKey = "nexus.settings.v3"

    static func load() -> NexusSettings {
        let defaults = UserDefaults.standard
        guard let data = defaults.data(forKey: storageKey),
              let decoded = try? JSONDecoder().decode(NexusSettings.self, from: data) else {
            return NexusSettings(
                appearance: "system",
                batchSize: 20,
                delayMin: 0.35,
                delayMax: 0.6,
                staggerSameSite: true,
                privateByDefault: true,
                watchClipboard: true,
                skipDuplicateRichLinks: true,
                sortRichLinks: false,
                keepBlankLines: true,
                backupCount: 7
            )
        }
        return decoded
    }

    func save() {
        if let data = try? JSONEncoder().encode(self) {
            UserDefaults.standard.set(data, forKey: Self.storageKey)
        }
    }
}

extension NexusSettings: Codable {}
