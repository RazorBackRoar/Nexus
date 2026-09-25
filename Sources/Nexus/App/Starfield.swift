import SwiftUI

// MARK: - Cosmic background

struct StarfieldBackground: View {
    var day: Bool = false

    private static let far = SkyStar.field(count: 180, seed: 11, size: 0.5...1.2)
    private static let mid = SkyStar.field(count: 95, seed: 29, size: 1.0...2.0)
    private static let near = SkyStar.field(count: 34, seed: 47, size: 1.8...3.3)
    private static let motes = SkyStar.field(count: 16, seed: 71, size: 3.0...6.0)
    private static let meteors = Meteor.set()

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
            Canvas { context, size in
                let time = timeline.date.timeIntervalSinceReferenceDate
                drawSky(context, size)
                drawNebula(context, size, time)
                drawMilkyWay(context, size, time)
                drawLayer(Self.far, context: context, size: size, time: time, speed: 3.5, strength: 0.55, bloom: false)
                drawLayer(Self.mid, context: context, size: size, time: time, speed: 9, strength: 0.8, bloom: false)
                drawMotes(context, size, time)
                drawLayer(Self.near, context: context, size: size, time: time, speed: 20, strength: 1, bloom: true)
                drawMeteors(context, size, time)
                drawVignette(context, size)
            }
        }
        .ignoresSafeArea()
    }

    private func drawSky(_ context: GraphicsContext, _ size: CGSize) {
        let sky = day
            ? Gradient(stops: [
                .init(color: Color(red: 0.90, green: 0.84, blue: 1.0), location: 0),
                .init(color: Color(red: 0.76, green: 0.64, blue: 0.97), location: 0.45),
                .init(color: Color(red: 0.60, green: 0.46, blue: 0.90), location: 1),
            ])
            : Gradient(stops: [
                .init(color: Color(red: 0.16, green: 0.05, blue: 0.32), location: 0),
                .init(color: Color(red: 0.09, green: 0.03, blue: 0.21), location: 0.45),
                .init(color: Color(red: 0.03, green: 0.01, blue: 0.09), location: 1),
            ])
        context.fill(
            Path(CGRect(origin: .zero, size: size)),
            with: .linearGradient(sky, startPoint: CGPoint(x: size.width * 0.15, y: 0), endPoint: CGPoint(x: size.width * 0.85, y: size.height))
        )
    }

    private func drawNebula(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        let clouds: [(CGFloat, CGFloat, CGFloat, Color, Double)] = [
            (0.16, 0.30, 0.60, Color(red: 0.58, green: 0.24, blue: 0.95), 0.05),
            (0.82, 0.62, 0.52, Color(red: 0.22, green: 0.38, blue: 0.95), 0.04),
            (0.50, 0.12, 0.38, Color(red: 0.85, green: 0.34, blue: 0.80), 0.06),
            (0.64, 0.90, 0.34, Color(red: 0.16, green: 0.72, blue: 0.86), 0.05),
        ]
        for (index, cloud) in clouds.enumerated() {
            let drift = CGFloat(sin(time * cloud.4 + Double(index) * 1.7)) * 26
            let breathe = 0.9 + 0.1 * sin(time * 0.07 + Double(index))
            let width = size.width * cloud.2
            let height = width * 0.6 * CGFloat(breathe)
            let rect = CGRect(
                x: size.width * cloud.0 - width / 2 + drift,
                y: size.height * cloud.1 - height / 2,
                width: width,
                height: height
            )
            context.fill(
                Path(ellipseIn: rect),
                with: .radialGradient(
                    Gradient(colors: [cloud.3.opacity(day ? 0.22 : 0.34), cloud.3.opacity(day ? 0.08 : 0.12), .clear]),
                    center: CGPoint(x: rect.midX, y: rect.midY),
                    startRadius: 0,
                    endRadius: width / 2
                )
            )
        }
    }

    private func drawMilkyWay(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        var band = context
        band.translateBy(x: size.width / 2 + CGFloat(sin(time * 0.02)) * 30, y: size.height * 0.45)
        band.rotate(by: .degrees(-16))
        let rect = CGRect(x: -size.width * 0.75, y: -size.height * 0.11, width: size.width * 1.5, height: size.height * 0.22)
        band.fill(
            Path(ellipseIn: rect),
            with: .radialGradient(
                Gradient(colors: [Color(red: 0.72, green: 0.60, blue: 1).opacity(day ? 0.14 : 0.16), .clear]),
                center: .zero,
                startRadius: 0,
                endRadius: size.width * 0.7
            )
        )
    }

    private func drawLayer(_ stars: [SkyStar], context: GraphicsContext, size: CGSize, time: Double, speed: Double, strength: Double, bloom: Bool) {
        let span = size.width + 40
        for star in stars {
            let offset = (Double(star.x) * span + time * speed * star.speedJitter).truncatingRemainder(dividingBy: span)
            let x = size.width + 20 - CGFloat(offset)
            let y = size.height * star.y + CGFloat(sin(time * 0.05 + star.phase)) * 2.5
            let twinkle = star.brightness * strength * (0.72 + 0.28 * sin(time * star.twinkle + star.phase))
            let color = day ? star.dayColor : star.color
            let dot = CGRect(x: x - star.size / 2, y: y - star.size / 2, width: star.size, height: star.size)
            if bloom {
                let halo = dot.insetBy(dx: -star.size * 3.2, dy: -star.size * 3.2)
                context.fill(
                    Path(ellipseIn: halo),
                    with: .radialGradient(
                        Gradient(colors: [color.opacity(twinkle * 0.45), color.opacity(twinkle * 0.1), .clear]),
                        center: CGPoint(x: x, y: y),
                        startRadius: 0,
                        endRadius: halo.width / 2
                    )
                )
                if star.size > 2.8 {
                    let flare = star.size * 5
                    var cross = Path()
                    cross.move(to: CGPoint(x: x - flare, y: y))
                    cross.addLine(to: CGPoint(x: x + flare, y: y))
                    cross.move(to: CGPoint(x: x, y: y - flare * 0.7))
                    cross.addLine(to: CGPoint(x: x, y: y + flare * 0.7))
                    context.stroke(cross, with: .color(color.opacity(twinkle * 0.35)), lineWidth: 0.6)
                }
            }
            context.fill(Path(ellipseIn: dot), with: .color(color.opacity(twinkle)))
        }
    }

    private func drawMotes(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        let span = size.width + 120
        for mote in Self.motes {
            let offset = (Double(mote.x) * span + time * 14 * mote.speedJitter).truncatingRemainder(dividingBy: span)
            let x = size.width + 60 - CGFloat(offset)
            let y = size.height * mote.y + CGFloat(sin(time * 0.3 + mote.phase)) * 10
            let pulse = 0.5 + 0.5 * sin(time * 0.6 + mote.phase)
            let radius = mote.size * 3
            context.fill(
                Path(ellipseIn: CGRect(x: x - radius, y: y - radius, width: radius * 2, height: radius * 2)),
                with: .radialGradient(
                    Gradient(colors: [(day ? mote.dayColor : mote.color).opacity(0.28 * pulse), .clear]),
                    center: CGPoint(x: x, y: y),
                    startRadius: 0,
                    endRadius: radius
                )
            )
        }
    }

    private func drawMeteors(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        for meteor in Self.meteors {
            let phase = ((time + meteor.offset) / meteor.cycle).truncatingRemainder(dividingBy: 1)
            guard phase < meteor.visible else { continue }
            let progress = phase / meteor.visible
            let fade = sin(progress * .pi)
            let travel = CGFloat(progress) * size.width * 0.6
            let x = size.width * meteor.startX + travel * CGFloat(meteor.dirX)
            let y = size.height * meteor.startY + travel * CGFloat(meteor.dirY)
            let length = meteor.length * CGFloat(meteor.depth)
            let tail = CGPoint(x: x - length * CGFloat(meteor.dirX), y: y - length * CGFloat(meteor.dirY))
            var trail = Path()
            trail.move(to: tail)
            trail.addLine(to: CGPoint(x: x, y: y))
            context.stroke(
                trail,
                with: .linearGradient(
                    Gradient(colors: [.clear, meteor.color.opacity(0.6 * fade), .white.opacity(0.95 * fade)]),
                    startPoint: tail,
                    endPoint: CGPoint(x: x, y: y)
                ),
                style: StrokeStyle(lineWidth: 0.8 + CGFloat(meteor.depth) * 1.6, lineCap: .round)
            )
            let glow: CGFloat = 10 * CGFloat(meteor.depth)
            context.fill(
                Path(ellipseIn: CGRect(x: x - glow, y: y - glow, width: glow * 2, height: glow * 2)),
                with: .radialGradient(
                    Gradient(colors: [meteor.color.opacity(0.55 * fade), .clear]),
                    center: CGPoint(x: x, y: y),
                    startRadius: 0,
                    endRadius: glow
                )
            )
            context.fill(Path(ellipseIn: CGRect(x: x - 1.6, y: y - 1.6, width: 3.2, height: 3.2)), with: .color(.white.opacity(fade)))
        }
    }

    private func drawVignette(_ context: GraphicsContext, _ size: CGSize) {
        context.fill(
            Path(CGRect(origin: .zero, size: size)),
            with: .radialGradient(
                Gradient(colors: [.clear, .black.opacity(day ? 0.10 : 0.42)]),
                center: CGPoint(x: size.width / 2, y: size.height * 0.42),
                startRadius: size.width * 0.28,
                endRadius: size.width * 0.85
            )
        )
    }
}

private struct SkyStar {
    var x: CGFloat
    var y: CGFloat
    var size: CGFloat
    var brightness: Double
    var twinkle: Double
    var phase: Double
    var speedJitter: Double
    var color: Color
    var dayColor: Color

    static func field(count: Int, seed: Int, size: ClosedRange<CGFloat>) -> [SkyStar] {
        var rng = SeededRandom(seed: seed)
        let night: [Color] = [
            .white, .white, .white,
            Color(red: 0.86, green: 0.78, blue: 1),
            Color(red: 0.74, green: 0.62, blue: 1),
            Color(red: 0.72, green: 0.84, blue: 1),
            Color(red: 0.66, green: 0.95, blue: 1),
            Color(red: 1, green: 0.76, blue: 0.92),
        ]
        let day: [Color] = [
            .white, .white,
            Color(red: 0.50, green: 0.32, blue: 0.86),
            Color(red: 0.42, green: 0.26, blue: 0.78),
            Color(red: 0.36, green: 0.44, blue: 0.92),
            Color(red: 0.26, green: 0.62, blue: 0.82),
            Color(red: 0.80, green: 0.40, blue: 0.72),
            Color(red: 0.55, green: 0.36, blue: 0.90),
        ]
        return (0..<count).map { _ in
            let pick = Int(rng.next() * Double(night.count)) % night.count
            return SkyStar(
                x: CGFloat(rng.next()),
                y: CGFloat(rng.next()),
                size: size.lowerBound + CGFloat(rng.next()) * (size.upperBound - size.lowerBound),
                brightness: 0.35 + rng.next() * 0.65,
                twinkle: 0.3 + rng.next() * 0.9,
                phase: rng.next() * 6.28,
                speedJitter: 0.8 + rng.next() * 0.4,
                color: night[pick],
                dayColor: day[pick]
            )
        }
    }
}

private struct Meteor {
    var startX: CGFloat
    var startY: CGFloat
    var dirX: Double
    var dirY: Double
    var length: CGFloat
    var depth: Double
    var cycle: Double
    var visible: Double
    var offset: Double
    var color: Color

    static func set() -> [Meteor] {
        [
            Meteor(startX: 0.04, startY: 0.10, dirX: 0.94, dirY: 0.34, length: 140, depth: 1.0, cycle: 28, visible: 0.34, offset: 0, color: Color(red: 0.76, green: 0.88, blue: 1)),
            Meteor(startX: 0.58, startY: 0.02, dirX: 0.78, dirY: 0.62, length: 90, depth: 0.6, cycle: 35, visible: 0.30, offset: 10, color: Color(red: 0.86, green: 0.70, blue: 1)),
            Meteor(startX: 0.96, startY: 0.18, dirX: -0.90, dirY: 0.44, length: 110, depth: 0.8, cycle: 43, visible: 0.32, offset: 18, color: .white),
            Meteor(startX: 0.22, startY: 0.58, dirX: 0.97, dirY: 0.24, length: 70, depth: 0.45, cycle: 39, visible: 0.28, offset: 26, color: Color(red: 0.66, green: 0.95, blue: 1)),
            Meteor(startX: 0.72, startY: 0.74, dirX: 0.62, dirY: -0.78, length: 80, depth: 0.55, cycle: 49, visible: 0.26, offset: 33, color: Color(red: 1, green: 0.78, blue: 0.94)),
        ]
    }
}

private struct SeededRandom {
    private var state: UInt64

    init(seed: Int) {
        state = UInt64(seed) &* 6364136223846793005 &+ 1442695040888963407
    }

    mutating func next() -> Double {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        return Double(state >> 11) / Double(1 << 53)
    }
}

// MARK: - Static glass panels

struct GlassSurface: ViewModifier {
    var radius: CGFloat = 18
    var tint: Color = Color(red: 0.55, green: 0.30, blue: 0.95)
    var tintOpacity: Double = 0.07
    var elevated = true
    @Environment(\.colorScheme) private var scheme

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: radius, style: .continuous)
        let light = scheme == .light
        let top = elevated
            ? (light ? Color(red: 0.44, green: 0.26, blue: 0.76) : Color(red: 0.26, green: 0.11, blue: 0.48))
            : (light ? Color(red: 0.30, green: 0.16, blue: 0.56) : Color(red: 0.07, green: 0.02, blue: 0.16))
        let bottom = elevated
            ? (light ? Color(red: 0.30, green: 0.16, blue: 0.58) : Color(red: 0.10, green: 0.04, blue: 0.22))
            : (light ? Color(red: 0.36, green: 0.20, blue: 0.64) : Color(red: 0.11, green: 0.04, blue: 0.24))
        content
            .background {
                ZStack {
                    shape.fill(.ultraThinMaterial)
                    shape.fill(LinearGradient(colors: [top.opacity(0.62), bottom.opacity(0.72)], startPoint: .top, endPoint: .bottom))
                    shape.fill(RadialGradient(colors: [tint.opacity(0.26 + tintOpacity), .clear], center: .topLeading, startRadius: 0, endRadius: 440))
                    shape.fill(RadialGradient(colors: [Color(red: 0.30, green: 0.55, blue: 1).opacity(0.14), .clear], center: .bottomTrailing, startRadius: 0, endRadius: 400))
                }
            }
            .overlay {
                shape
                    .fill(LinearGradient(colors: [.white.opacity(elevated ? 0.16 : 0.07), .clear], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.28)))
                    .allowsHitTesting(false)
            }
            .overlay {
                shape.strokeBorder(
                    LinearGradient(
                        colors: [.white.opacity(0.62), Color(red: 0.78, green: 0.64, blue: 1).opacity(0.38), .white.opacity(0.08)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 1
                )
            }
            .overlay {
                shape.inset(by: 2).strokeBorder(.white.opacity(0.06), lineWidth: 1)
            }
            .shadow(color: Color(red: 0.50, green: 0.28, blue: 1).opacity(elevated ? 0.38 : 0), radius: 32)
            .shadow(color: .black.opacity(elevated ? 0.55 : 0.28), radius: elevated ? 26 : 10, y: elevated ? 16 : 5)
    }
}

extension View {
    func glass(radius: CGFloat = 18, tint: Color = Color(red: 0.55, green: 0.30, blue: 0.95), opacity: Double = 0.07, elevated: Bool = true) -> some View {
        modifier(GlassSurface(radius: radius, tint: tint, tintOpacity: opacity, elevated: elevated))
    }

    func interactiveGlass(
        accent: Color,
        radius: CGFloat,
        selected: Bool = false,
        intensity: Double = 1,
        lift: CGFloat = 1.03,
        sparkles: Bool = true,
        pressable: Bool = true
    ) -> some View {
        modifier(InteractiveGlass(accent: accent, radius: radius, selected: selected, intensity: intensity, lift: lift, sparkles: sparkles, pressable: pressable))
    }
}

struct GlassPanelModifier: ViewModifier {
    func body(content: Content) -> some View {
        content.glass()
    }
}

// MARK: - Cursor-reactive glass

struct InteractiveGlass: ViewModifier {
    var accent: Color
    var radius: CGFloat
    var selected: Bool
    var intensity: Double
    var lift: CGFloat
    var sparkles: Bool
    var pressable: Bool

    @State private var hovering = false
    @State private var pressed = false
    @State private var cursor: CGPoint?
    @State private var hoverStart: Date?

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: radius, style: .continuous)
        let lit = hovering || selected
        content
            .background {
                ZStack {
                    shape.fill(.ultraThinMaterial)
                    shape.fill(
                        LinearGradient(
                            colors: [Color(red: 0.30, green: 0.14, blue: 0.54).opacity(0.55), Color(red: 0.11, green: 0.04, blue: 0.25).opacity(0.62)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    shape.fill(
                        LinearGradient(
                            colors: [
                                accent.opacity((selected ? 0.62 : (hovering ? 0.52 : 0.34)) * intensity),
                                accent.opacity((selected ? 0.30 : 0.14) * intensity),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                }
            }
            .overlay {
                shape
                    .fill(LinearGradient(colors: [.white.opacity(lit ? 0.30 : 0.18), .white.opacity(0.03), .clear], startPoint: .top, endPoint: .center))
                    .allowsHitTesting(false)
            }
            .overlay {
                GeometryReader { proxy in
                    ZStack {
                        if hovering, let cursor {
                            Circle()
                                .fill(RadialGradient(colors: [.white.opacity(0.34), accent.opacity(0.30), .clear], center: .center, startRadius: 0, endRadius: 62))
                                .frame(width: 124, height: 124)
                                .position(cursor)
                                .blendMode(.plusLighter)
                        }
                        if hovering, let start = hoverStart {
                            TimelineView(.animation) { timeline in
                                let elapsed = timeline.date.timeIntervalSince(start)
                                let progress = min(1, elapsed / 0.85)
                                ZStack {
                                    LinearGradient(colors: [.clear, .white.opacity(0.42), .clear], startPoint: .leading, endPoint: .trailing)
                                        .frame(width: max(26, proxy.size.width * 0.26), height: proxy.size.height * 2.2)
                                        .rotationEffect(.degrees(20))
                                        .position(x: -proxy.size.width * 0.3 + CGFloat(progress) * proxy.size.width * 1.6, y: proxy.size.height / 2)
                                        .opacity(progress < 1 ? 1 : 0)
                                        .blendMode(.plusLighter)
                                    if sparkles, let cursor {
                                        SparkleCluster(center: cursor, tint: accent, time: elapsed)
                                    }
                                }
                            }
                        }
                    }
                    .clipShape(shape)
                }
                .allowsHitTesting(false)
            }
            .overlay {
                shape.strokeBorder(
                    LinearGradient(
                        colors: [.white.opacity(lit ? 0.9 : 0.48), accent.opacity(lit ? 1 : 0.6), accent.opacity(0.28)],
                        startPoint: .top,
                        endPoint: .bottom
                    ),
                    lineWidth: lit ? 1.4 : 1
                )
            }
            .shadow(color: accent.opacity((lit ? 0.62 : 0.2) * intensity), radius: lit ? 18 : 8, y: 2)
            .shadow(color: .black.opacity(0.45), radius: hovering ? 16 : 8, y: hovering ? 10 : 5)
            .scaleEffect(pressed ? 0.96 : (hovering ? lift : 1))
            .brightness(pressed ? 0.1 : (hovering ? 0.03 : 0))
            .onContinuousHover { phase in
                switch phase {
                case let .active(point):
                    cursor = point
                    if !hovering {
                        hovering = true
                        hoverStart = Date()
                    }
                case .ended:
                    hovering = false
                    cursor = nil
                    hoverStart = nil
                }
            }
            .pressEvents { if pressable { pressed = $0 } }
            .animation(.spring(duration: 0.24, bounce: 0.2), value: hovering)
            .animation(.spring(duration: 0.14, bounce: 0.3), value: pressed)
            .animation(.easeOut(duration: 0.22), value: selected)
    }
}

private struct SparkleCluster: View {
    var center: CGPoint
    var tint: Color
    var time: Double

    var body: some View {
        ZStack {
            ForEach(0..<4, id: \.self) { index in
                let angle = time * 0.9 + Double(index) * .pi / 2
                let radius = 15.0 + Double(index % 2) * 9
                let pulse = 0.5 + 0.5 * sin(time * 3.2 + Double(index) * 1.3)
                Image(systemName: "sparkle")
                    .font(.system(size: 5 + CGFloat(index % 3) * 2, weight: .bold))
                    .foregroundStyle(index % 2 == 0 ? Color.white : tint)
                    .opacity(0.2 + 0.65 * pulse)
                    .position(
                        x: center.x + CGFloat(cos(angle) * radius),
                        y: center.y + CGFloat(sin(angle) * radius * 0.6)
                    )
            }
        }
    }
}

// MARK: - Controls

struct ColorActionButton: View {
    var title: String
    var colors: [Color]
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.45), radius: 1, y: 1)
                .frame(minWidth: 104, minHeight: 40)
                .padding(.horizontal, 12)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .interactiveGlass(accent: colors.first ?? .purple, radius: 12)
    }
}

struct GlassRow<Content: View>: View {
    var accent: Color
    var selected: Bool
    var content: Content

    init(accent: Color, selected: Bool, @ViewBuilder content: () -> Content) {
        self.accent = accent
        self.selected = selected
        self.content = content()
    }

    var body: some View {
        content
            .padding(.horizontal, 12)
            .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
            .overlay(alignment: .leading) {
                RoundedRectangle(cornerRadius: 2)
                    .fill(LinearGradient(colors: [.white.opacity(0.9), accent], startPoint: .top, endPoint: .bottom))
                    .frame(width: 3)
                    .padding(.vertical, 10)
                    .padding(.leading, 7)
                    .shadow(color: accent, radius: selected ? 8 : 4)
            }
            .contentShape(Rectangle())
            .interactiveGlass(accent: accent, radius: 12, selected: selected, intensity: 0.9, lift: 1.018, sparkles: true)
    }
}

// MARK: - Press tracking

private struct PressEvents: ViewModifier {
    var onChange: (Bool) -> Void

    func body(content: Content) -> some View {
        content.simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in onChange(true) }
                .onEnded { _ in onChange(false) }
        )
    }
}

extension View {
    func pressEvents(_ onChange: @escaping (Bool) -> Void) -> some View {
        modifier(PressEvents(onChange: onChange))
    }
}
