import AppKit
import SwiftUI
import Testing
@testable import Nexus

@MainActor
@Test func renderPreviewSnapshots() throws {
    for bright in [false, true] {
        let view = ZStack {
            StarfieldBackground(bright: bright)
            VStack(spacing: 14) {
                Spacer().frame(height: 40)
                Text("Nexus")
                    .font(.system(size: 52, weight: .semibold, design: .rounded))
                    .foregroundStyle(.white)
                Text("Safari bookmark manager and batch URL opener")
                    .font(.system(size: 13))
                    .foregroundStyle(.white.opacity(0.72))
                HStack(spacing: 16) {
                    VStack(spacing: 8) {
                        GlassRow(accent: Color(hex: "#34D6C4"), selected: true) { Text("Quick Save").foregroundStyle(.white).padding(.leading, 10) }
                        GlassRow(accent: Color(hex: "#FF9A3C"), selected: false) { Text("Fun").foregroundStyle(.white).padding(.leading, 10) }
                        GlassRow(accent: Color(hex: "#4DA3FF"), selected: false) { Text("Tech").foregroundStyle(.white).padding(.leading, 10) }
                        GlassRow(accent: Color(hex: "#52D273"), selected: false) { Text("Favorites").foregroundStyle(.white).padding(.leading, 10) }
                    }
                    .padding(16)
                    .frame(width: 272)
                    .glass(radius: 20)
                    VStack {
                        Spacer()
                        HStack(spacing: 12) {
                            ColorActionButton(title: "Home", colors: [Color(hex: "#4DA3FF")]) {}
                            ColorActionButton(title: "Open All", colors: [Color(hex: "#3DDC97")]) {}
                            ColorActionButton(title: "Clear", colors: [Color(hex: "#FF5A52")]) {}
                        }
                        .padding(18)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .glass(radius: 20)
                }
                .padding(20)
            }
        }
        .frame(width: 1200, height: 760)
        .environment(\.nexusBright, bright)
        .environment(\.colorScheme, .dark)

        let renderer = ImageRenderer(content: view)
        renderer.scale = 1
        guard let image = renderer.nsImage,
              let tiff = image.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff),
              let png = rep.representation(using: .png, properties: [:]) else {
            Issue.record("render failed")
            return
        }
        try png.write(to: URL(fileURLWithPath: "/tmp/nexus-\(bright ? "solar" : "void").png"))
    }
}
