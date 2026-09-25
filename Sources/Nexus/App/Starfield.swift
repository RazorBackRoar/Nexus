import SwiftUI

// MARK: - Theme

private struct NexusBrightKey: EnvironmentKey {
    static let defaultValue = false
}

extension EnvironmentValues {
    /// True in Standard Safari mode (solar eclipse), false in Private Safari mode (black hole).
    var nexusBright: Bool {
        get { self[NexusBrightKey.self] }
        set { self[NexusBrightKey.self] = newValue }
    }
}

enum CosmicLight {
    static func edge(bright: Bool) -> Color {
        bright ? Color(red: 1, green: 0.84, blue: 0.58) : Color(red: 0.56, green: 0.54, blue: 1)
    }
}

// MARK: - Cosmic environment

struct StarfieldBackground: View {
    var bright: Bool
    @State private var switchedAt = Date.distantPast

    private static let dust = SkyStar.field(count: 380, seed: 5, size: 0.35...0.8)
    private static let far = SkyStar.field(count: 220, seed: 11, size: 0.5...1.1)
    private static let mid = SkyStar.field(count: 110, seed: 29, size: 0.9...1.8)
    private static let near = SkyStar.field(count: 30, seed: 47, size: 1.8...3.2)
    private static let motes = SkyStar.field(count: 14, seed: 71, size: 3.0...5.5)
    private static let galaxies = Galaxy.set()
    private static let voidClouds = NebulaCloud.voidSet()
    private static let solarClouds = NebulaCloud.solarSet()
    private static let lanes = DustLane.set()
    private static let streamers = Streamer.set()
    private static let flares = Flare.set()
    private static let meteors = Meteor.set()

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.035, green: 0.045, blue: 0.12),
                    Color(red: 0.018, green: 0.024, blue: 0.075),
                    Color(red: 0.006, green: 0.007, blue: 0.028),
                ],
                startPoint: UnitPoint(x: 0.85, y: 0),
                endPoint: UnitPoint(x: 0.15, y: 1)
            )
            .opacity(bright ? 1 : 0)
            LinearGradient(
                colors: [
                    Color(red: 0.014, green: 0.011, blue: 0.042),
                    Color(red: 0.006, green: 0.005, blue: 0.02),
                    Color(red: 0.0, green: 0.0, blue: 0.006),
                ],
                startPoint: UnitPoint(x: 0.85, y: 0),
                endPoint: UnitPoint(x: 0.15, y: 1)
            )
            .opacity(bright ? 0 : 1)

            TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
                Canvas { context, size in
                    let time = timeline.date.timeIntervalSinceReferenceDate
                    let raw = min(1, max(0, timeline.date.timeIntervalSince(switchedAt) / 0.9))
                    let eased = raw * raw * (3 - 2 * raw)
                    let solar = bright ? eased : 1 - eased
                    let dark = 1 - solar

                    drawClouds(Self.voidClouds, context, size, time, alpha: dark)
                    drawClouds(Self.solarClouds, context, size, time, alpha: solar)
                    drawLanes(context, size, time)
                    drawLayer(Self.dust, context, size, time, speed: 1.1, strength: 0.28 + 0.14 * solar, bloom: false)
                    drawGalaxies(context, size, time)
                    drawLayer(Self.far, context, size, time, speed: 2.6, strength: 0.45 + 0.2 * solar, bloom: false)
                    drawLayer(Self.mid, context, size, time, speed: 6.5, strength: 0.72, bloom: false)
                    drawMotes(context, size, time, warm: solar)
                    drawLayer(Self.near, context, size, time, speed: 15, strength: 1, bloom: true)
                    drawEclipse(context, size, time, alpha: solar)
                    drawBlackHole(context, size, time, alpha: dark)
                    drawMeteors(context, size, time)
                }
            }

            RadialGradient(
                colors: [.clear, .black.opacity(0.62)],
                center: UnitPoint(x: 0.5, y: 0.45),
                startRadius: 300,
                endRadius: 1050
            )
            .opacity(bright ? 0.7 : 1)
        }
        .animation(.easeInOut(duration: 0.9), value: bright)
        .onChange(of: bright) { _, _ in switchedAt = Date() }
        .ignoresSafeArea()
        .allowsHitTesting(false)
    }

    // MARK: Nebulae

    private func drawClouds(_ clouds: [NebulaCloud], _ context: GraphicsContext, _ size: CGSize, _ time: Double, alpha: Double) {
        guard alpha > 0.01 else { return }
        for cloud in clouds {
            let drift = CGFloat(sin(time * cloud.drift + cloud.phase)) * 22
            let base = size.width * cloud.size
            for lobe in cloud.lobes {
                let width = base * lobe.scale
                let height = width * lobe.aspect
                let x = size.width * cloud.x + base * lobe.dx + drift
                let y = size.height * cloud.y + base * lobe.dy
                let rect = CGRect(x: x - width / 2, y: y - height / 2, width: width, height: height)
                context.fill(
                    Path(ellipseIn: rect),
                    with: .radialGradient(
                        Gradient(colors: [cloud.color.opacity(cloud.strength * lobe.weight * alpha), cloud.color.opacity(cloud.strength * 0.3 * lobe.weight * alpha), .clear]),
                        center: CGPoint(x: x, y: y),
                        startRadius: 0,
                        endRadius: width / 2
                    )
                )
            }
        }
    }

    private func drawLanes(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        for lane in Self.lanes {
            var layer = context
            layer.translateBy(x: size.width * lane.x + CGFloat(sin(time * 0.02 + lane.phase)) * 14, y: size.height * lane.y)
            layer.rotate(by: .radians(lane.rotation))
            let width = size.width * lane.length
            let height = width * lane.thickness
            layer.fill(
                Path(ellipseIn: CGRect(x: -width / 2, y: -height / 2, width: width, height: height)),
                with: .radialGradient(
                    Gradient(colors: [.black.opacity(0.55), .black.opacity(0.2), .clear]),
                    center: .zero,
                    startRadius: 0,
                    endRadius: width / 2
                )
            )
        }
    }

    // MARK: Galaxies

    private func drawGalaxies(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        for galaxy in Self.galaxies {
            let span = size.width + galaxy.size * 3
            let travel = (Double(galaxy.x) * Double(span) + time * galaxy.speed).truncatingRemainder(dividingBy: Double(span))
            var layer = context
            layer.translateBy(x: size.width + galaxy.size * 1.5 - CGFloat(travel), y: size.height * galaxy.y)
            layer.rotate(by: .radians(galaxy.tilt))
            layer.scaleBy(x: 1, y: galaxy.squash)
            let radius = galaxy.size
            layer.fill(
                Path(ellipseIn: CGRect(x: -radius, y: -radius, width: radius * 2, height: radius * 2)),
                with: .radialGradient(
                    Gradient(colors: [galaxy.color.opacity(0.20), galaxy.color.opacity(0.06), .clear]),
                    center: .zero,
                    startRadius: 0,
                    endRadius: radius
                )
            )
            for arm in 0..<2 {
                var path = Path()
                for step in 0...64 {
                    let fraction = Double(step) / 64
                    let angle = fraction * 3.6 + Double(arm) * .pi + time * galaxy.spin
                    let distance = Double(radius) * (0.1 + fraction * 0.85)
                    let point = CGPoint(x: cos(angle) * distance, y: sin(angle) * distance)
                    if step == 0 { path.move(to: point) } else { path.addLine(to: point) }
                }
                layer.stroke(path, with: .color(galaxy.color.opacity(0.14)), style: StrokeStyle(lineWidth: radius * 0.14, lineCap: .round))
                layer.stroke(path, with: .color(.white.opacity(0.07)), style: StrokeStyle(lineWidth: radius * 0.035, lineCap: .round))
            }
            let core = radius * 0.15
            layer.fill(
                Path(ellipseIn: CGRect(x: -core, y: -core, width: core * 2, height: core * 2)),
                with: .radialGradient(
                    Gradient(colors: [.white.opacity(0.8), galaxy.core.opacity(0.45), .clear]),
                    center: .zero,
                    startRadius: 0,
                    endRadius: core
                )
            )
        }
    }

    // MARK: Stars

    private func drawLayer(_ stars: [SkyStar], _ context: GraphicsContext, _ size: CGSize, _ time: Double, speed: Double, strength: Double, bloom: Bool) {
        let span = size.width + 40
        for star in stars {
            let offset = (Double(star.x) * Double(span) + time * speed * star.speedJitter).truncatingRemainder(dividingBy: Double(span))
            let x = size.width + 20 - CGFloat(offset)
            let y = size.height * star.y + CGFloat(sin(time * 0.05 + star.phase)) * 2
            let twinkle = star.brightness * strength * (0.74 + 0.26 * sin(time * star.twinkle + star.phase))
            let dot = CGRect(x: x - star.size / 2, y: y - star.size / 2, width: star.size, height: star.size)
            if bloom {
                let halo = dot.insetBy(dx: -star.size * 2.6, dy: -star.size * 2.6)
                context.fill(
                    Path(ellipseIn: halo),
                    with: .radialGradient(
                        Gradient(colors: [star.color.opacity(twinkle * 0.32), .clear]),
                        center: CGPoint(x: x, y: y),
                        startRadius: 0,
                        endRadius: halo.width / 2
                    )
                )
                if star.size > 2.5 {
                    let spike = star.size * 6
                    var cross = Path()
                    cross.move(to: CGPoint(x: x - spike, y: y))
                    cross.addLine(to: CGPoint(x: x + spike, y: y))
                    cross.move(to: CGPoint(x: x, y: y - spike))
                    cross.addLine(to: CGPoint(x: x, y: y + spike))
                    context.stroke(
                        cross,
                        with: .radialGradient(
                            Gradient(colors: [.white.opacity(twinkle * 0.7), .clear]),
                            center: CGPoint(x: x, y: y),
                            startRadius: 0,
                            endRadius: spike
                        ),
                        lineWidth: 0.6
                    )
                }
            }
            context.fill(Path(ellipseIn: dot), with: .color(star.color.opacity(twinkle)))
        }
    }

    private func drawMotes(_ context: GraphicsContext, _ size: CGSize, _ time: Double, warm: Double) {
        let span = size.width + 120
        let tint = Color(
            red: 0.55 + 0.45 * warm,
            green: 0.62 + 0.18 * warm,
            blue: 1 - 0.45 * warm
        )
        for mote in Self.motes {
            let offset = (Double(mote.x) * Double(span) + time * 10 * mote.speedJitter).truncatingRemainder(dividingBy: Double(span))
            let x = size.width + 60 - CGFloat(offset)
            let y = size.height * mote.y + CGFloat(sin(time * 0.3 + mote.phase)) * 9
            let pulse = 0.5 + 0.5 * sin(time * 0.6 + mote.phase)
            let radius = mote.size * 3
            context.fill(
                Path(ellipseIn: CGRect(x: x - radius, y: y - radius, width: radius * 2, height: radius * 2)),
                with: .radialGradient(
                    Gradient(colors: [tint.opacity(0.18 * pulse), .clear]),
                    center: CGPoint(x: x, y: y),
                    startRadius: 0,
                    endRadius: radius
                )
            )
        }
    }

    // MARK: Solar eclipse (Standard Safari)

    private func drawEclipse(_ context: GraphicsContext, _ size: CGSize, _ time: Double, alpha: Double) {
        guard alpha > 0.01 else { return }
        var ctx = context
        ctx.opacity = alpha
        let center = CGPoint(x: size.width * 0.86, y: size.height * 0.13)
        let r = min(size.width, size.height) * 0.062

        ctx.fill(
            Path(ellipseIn: CGRect(x: center.x - size.width * 0.8, y: center.y - size.width * 0.8, width: size.width * 1.6, height: size.width * 1.6)),
            with: .radialGradient(
                Gradient(colors: [Color(red: 1, green: 0.70, blue: 0.36).opacity(0.16), Color(red: 0.36, green: 0.28, blue: 0.85).opacity(0.07), .clear]),
                center: center,
                startRadius: r,
                endRadius: size.width * 0.8
            )
        )
        ctx.fill(
            Path(ellipseIn: CGRect(x: center.x - r * 5.5, y: center.y - r * 5.5, width: r * 11, height: r * 11)),
            with: .radialGradient(
                Gradient(colors: [
                    Color(red: 1, green: 0.93, blue: 0.80).opacity(0.46),
                    Color(red: 1, green: 0.74, blue: 0.40).opacity(0.18),
                    Color(red: 0.48, green: 0.40, blue: 0.95).opacity(0.07),
                    .clear,
                ]),
                center: center,
                startRadius: r * 0.9,
                endRadius: r * 5.5
            )
        )
        for streamer in Self.streamers {
            let angle = streamer.angle + time * 0.004
            let start = CGPoint(x: center.x + cos(angle) * r, y: center.y + sin(angle) * r)
            let end = CGPoint(x: center.x + cos(angle) * r * streamer.length, y: center.y + sin(angle) * r * streamer.length)
            var ray = Path()
            ray.move(to: start)
            ray.addLine(to: end)
            ctx.stroke(
                ray,
                with: .linearGradient(
                    Gradient(colors: [Color(red: 1, green: 0.93, blue: 0.80).opacity(streamer.strength), .clear]),
                    startPoint: start,
                    endPoint: end
                ),
                style: StrokeStyle(lineWidth: streamer.width, lineCap: .round)
            )
        }
        ctx.fill(
            Path(ellipseIn: CGRect(x: center.x - r * 1.9, y: center.y - r * 1.9, width: r * 3.8, height: r * 3.8)),
            with: .radialGradient(
                Gradient(colors: [.white.opacity(0.95), Color(red: 1, green: 0.86, blue: 0.58).opacity(0.55), .clear]),
                center: center,
                startRadius: r * 0.95,
                endRadius: r * 1.9
            )
        )
        for (index, angle) in [0.6, 2.4, 4.3].enumerated() {
            let wobble = sin(time * 0.3 + Double(index)) * 0.04
            let a = angle + wobble
            let left = CGPoint(x: center.x + cos(a - 0.05) * r, y: center.y + sin(a - 0.05) * r)
            let right = CGPoint(x: center.x + cos(a + 0.05) * r, y: center.y + sin(a + 0.05) * r)
            let peak = CGPoint(x: center.x + cos(a) * r * 1.14, y: center.y + sin(a) * r * 1.14)
            var arc = Path()
            arc.move(to: left)
            arc.addQuadCurve(to: right, control: peak)
            ctx.stroke(arc, with: .color(Color(red: 1, green: 0.36, blue: 0.16).opacity(0.18)), style: StrokeStyle(lineWidth: 4, lineCap: .round))
            ctx.stroke(arc, with: .color(Color(red: 1, green: 0.50, blue: 0.24).opacity(0.6)), style: StrokeStyle(lineWidth: 1.2, lineCap: .round))
        }
        ctx.fill(Path(ellipseIn: CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2)), with: .color(Color(red: 0.004, green: 0.005, blue: 0.012)))
        ctx.stroke(Path(ellipseIn: CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2)), with: .color(.white.opacity(0.75)), lineWidth: 1.2)

        let diamondAngle = -2.25
        let diamond = CGPoint(x: center.x + cos(diamondAngle) * r, y: center.y + sin(diamondAngle) * r)
        let pulse = 0.85 + 0.15 * sin(time * 0.8)
        ctx.fill(
            Path(ellipseIn: CGRect(x: diamond.x - 24, y: diamond.y - 24, width: 48, height: 48)),
            with: .radialGradient(
                Gradient(colors: [.white.opacity(pulse), Color(red: 1, green: 0.85, blue: 0.55).opacity(0.4 * pulse), .clear]),
                center: diamond,
                startRadius: 0,
                endRadius: 24
            )
        )
        let flareWidth = size.width * 0.34
        ctx.fill(
            Path(CGRect(x: diamond.x - flareWidth / 2, y: diamond.y - 0.6, width: flareWidth, height: 1.2)),
            with: .linearGradient(
                Gradient(colors: [.clear, .white.opacity(0.55 * pulse), .clear]),
                startPoint: CGPoint(x: diamond.x - flareWidth / 2, y: diamond.y),
                endPoint: CGPoint(x: diamond.x + flareWidth / 2, y: diamond.y)
            )
        )
    }

    // MARK: Black hole (Private Safari)

    private func drawBlackHole(_ context: GraphicsContext, _ size: CGSize, _ time: Double, alpha: Double) {
        guard alpha > 0.01 else { return }
        var ctx = context
        ctx.opacity = alpha
        let center = CGPoint(x: size.width * 0.86, y: size.height * 0.13)
        let r = min(size.width, size.height) * 0.058
        let doppler = Angle.radians(.pi + sin(time * 0.1) * 0.25)

        ctx.fill(
            Path(ellipseIn: CGRect(x: center.x - r * 9, y: center.y - r * 9, width: r * 18, height: r * 18)),
            with: .radialGradient(
                Gradient(colors: [Color(red: 0.22, green: 0.18, blue: 0.66).opacity(0.42), Color(red: 0.05, green: 0.10, blue: 0.42).opacity(0.14), .clear]),
                center: center,
                startRadius: r,
                endRadius: r * 9
            )
        )

        var disk = ctx
        disk.translateBy(x: center.x, y: center.y)
        disk.rotate(by: .radians(-0.12))
        disk.scaleBy(x: 1, y: 0.17)
        drawDiskHalf(disk, r: r, from: 180, to: 360, doppler: doppler)

        for band in 0..<14 {
            let t = Double(band) / 13
            ctx.stroke(
                arcPath(center: center, radius: r * (1.06 + CGFloat(t) * 0.5), from: 184, to: 356),
                with: .color(Color(red: 1, green: 0.84 - 0.2 * t, blue: 0.62 - 0.3 * t).opacity(0.5 * pow(1 - t, 1.8) + 0.02)),
                style: StrokeStyle(lineWidth: r * 0.1, lineCap: .round)
            )
        }
        for band in 0..<6 {
            let t = Double(band) / 5
            ctx.stroke(
                arcPath(center: center, radius: r * (1.05 + CGFloat(t) * 0.18), from: 16, to: 164),
                with: .color(Color(red: 1, green: 0.80, blue: 0.56).opacity(0.3 * (1 - t) + 0.02)),
                style: StrokeStyle(lineWidth: r * 0.05, lineCap: .round)
            )
        }

        ctx.fill(Path(ellipseIn: CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2)), with: .color(.black))
        ctx.stroke(
            Path(ellipseIn: CGRect(x: center.x - r * 1.02, y: center.y - r * 1.02, width: r * 2.04, height: r * 2.04)),
            with: .conicGradient(
                Gradient(colors: [
                    Color(red: 1, green: 0.96, blue: 0.88),
                    Color(red: 1, green: 0.70, blue: 0.40).opacity(0.5),
                    Color(red: 1, green: 0.96, blue: 0.88),
                ]),
                center: center,
                angle: doppler
            ),
            lineWidth: 1.5
        )

        drawDiskHalf(disk, r: r, from: 0, to: 180, doppler: doppler)

        for flare in Self.flares {
            let phase = ((time + flare.offset) / flare.cycle).truncatingRemainder(dividingBy: 1)
            guard phase < 0.14 else { continue }
            let fade = sin((phase / 0.14) * .pi)
            let start = CGPoint(x: center.x + cos(flare.angle) * r * 2.2, y: center.y + sin(flare.angle) * r * 0.36)
            let control = CGPoint(x: start.x + cos(flare.angle - 1.2) * r * 0.55, y: start.y - r * 0.5)
            let end = CGPoint(x: start.x + cos(flare.angle + 0.5) * r * 0.5, y: start.y + r * 0.08)
            var arc = Path()
            arc.move(to: start)
            arc.addQuadCurve(to: end, control: control)
            ctx.stroke(arc, with: .color(Color(red: 1, green: 0.36, blue: 0.12).opacity(0.16 * fade)), style: StrokeStyle(lineWidth: 5, lineCap: .round))
            ctx.stroke(arc, with: .color(Color(red: 1, green: 0.58, blue: 0.26).opacity(0.6 * fade)), style: StrokeStyle(lineWidth: 1.2, lineCap: .round))
        }
    }

    private func drawDiskHalf(_ disk: GraphicsContext, r: CGFloat, from: Double, to: Double, doppler: Angle) {
        let bands = 40
        for band in 0..<bands {
            let t = Double(band) / Double(bands - 1)
            let radius = r * (1.18 + CGFloat(t) * 1.9)
            let color: Color
            switch t {
            case ..<0.22: color = Color(red: 1, green: 0.93, blue: 0.80)
            case ..<0.5: color = Color(red: 1, green: 0.68, blue: 0.34)
            case ..<0.78: color = Color(red: 0.90, green: 0.36, blue: 0.16)
            default: color = Color(red: 0.36, green: 0.30, blue: 0.86)
            }
            let strength = 0.34 * pow(1 - t, 1.4) + 0.03
            disk.stroke(
                arcPath(center: .zero, radius: radius, from: from, to: to),
                with: .conicGradient(
                    Gradient(colors: [color.opacity(strength), color.opacity(strength * 0.3), color.opacity(strength)]),
                    center: .zero,
                    angle: doppler
                ),
                style: StrokeStyle(lineWidth: r * 0.12, lineCap: .butt)
            )
        }
    }

    private func arcPath(center: CGPoint, radius: CGFloat, from: Double, to: Double) -> Path {
        var path = Path()
        let steps = 48
        for step in 0...steps {
            let degrees = from + (to - from) * Double(step) / Double(steps)
            let radians = degrees * .pi / 180
            let point = CGPoint(x: center.x + cos(radians) * radius, y: center.y + sin(radians) * radius)
            if step == 0 { path.move(to: point) } else { path.addLine(to: point) }
        }
        return path
    }

    // MARK: Shooting stars

    private func drawMeteors(_ context: GraphicsContext, _ size: CGSize, _ time: Double) {
        for meteor in Self.meteors {
            let phase = ((time + meteor.offset) / meteor.cycle).truncatingRemainder(dividingBy: 1)
            guard phase < meteor.visible else { continue }
            let progress = phase / meteor.visible
            let fade = sin(progress * .pi)
            let travel = CGFloat(progress) * size.width * meteor.reach
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
                    Gradient(colors: [.clear, meteor.color.opacity(0.55 * fade), .white.opacity(0.95 * fade)]),
                    startPoint: tail,
                    endPoint: CGPoint(x: x, y: y)
                ),
                style: StrokeStyle(lineWidth: 0.6 + CGFloat(meteor.depth) * 1.5, lineCap: .round)
            )
            let glow: CGFloat = 9 * CGFloat(meteor.depth)
            context.fill(
                Path(ellipseIn: CGRect(x: x - glow, y: y - glow, width: glow * 2, height: glow * 2)),
                with: .radialGradient(
                    Gradient(colors: [meteor.color.opacity(0.5 * fade), .clear]),
                    center: CGPoint(x: x, y: y),
                    startRadius: 0,
                    endRadius: glow
                )
            )
            context.fill(Path(ellipseIn: CGRect(x: x - 1.4, y: y - 1.4, width: 2.8, height: 2.8)), with: .color(.white.opacity(fade)))
        }
    }
}

// MARK: - Environment data

private struct SkyStar {
    var x: CGFloat
    var y: CGFloat
    var size: CGFloat
    var brightness: Double
    var twinkle: Double
    var phase: Double
    var speedJitter: Double
    var color: Color

    static func field(count: Int, seed: Int, size: ClosedRange<CGFloat>) -> [SkyStar] {
        var rng = SeededRandom(seed: seed)
        let palette: [Color] = [
            .white, .white, .white, .white,
            Color(red: 0.80, green: 0.87, blue: 1),
            Color(red: 0.70, green: 0.80, blue: 1),
            Color(red: 0.66, green: 0.94, blue: 1),
            Color(red: 1, green: 0.92, blue: 0.74),
            Color(red: 1, green: 0.80, blue: 0.60),
            Color(red: 0.80, green: 0.74, blue: 1),
        ]
        return (0..<count).map { _ in
            SkyStar(
                x: CGFloat(rng.next()),
                y: CGFloat(rng.next()),
                size: size.lowerBound + CGFloat(rng.next()) * (size.upperBound - size.lowerBound),
                brightness: 0.35 + rng.next() * 0.65,
                twinkle: 0.3 + rng.next() * 0.9,
                phase: rng.next() * 6.28,
                speedJitter: 0.8 + rng.next() * 0.4,
                color: palette[Int(rng.next() * Double(palette.count)) % palette.count]
            )
        }
    }
}

private struct NebulaCloud {
    struct Lobe {
        var dx: CGFloat
        var dy: CGFloat
        var scale: CGFloat
        var aspect: CGFloat
        var weight: Double
    }

    var x: CGFloat
    var y: CGFloat
    var size: CGFloat
    var color: Color
    var strength: Double
    var drift: Double
    var phase: Double
    var lobes: [Lobe]

    static func make(_ x: CGFloat, _ y: CGFloat, _ size: CGFloat, _ color: Color, _ strength: Double, seed: Int) -> NebulaCloud {
        var rng = SeededRandom(seed: seed)
        let lobes = (0..<6).map { _ in
            Lobe(
                dx: CGFloat(rng.next() - 0.5) * 1.1,
                dy: CGFloat(rng.next() - 0.5) * 0.6,
                scale: 0.35 + CGFloat(rng.next()) * 0.7,
                aspect: 0.35 + CGFloat(rng.next()) * 0.5,
                weight: 0.5 + rng.next() * 0.5
            )
        }
        return NebulaCloud(x: x, y: y, size: size, color: color, strength: strength, drift: 0.02 + rng.next() * 0.03, phase: rng.next() * 6, lobes: lobes)
    }

    static func voidSet() -> [NebulaCloud] {
        [
            make(0.82, 0.18, 0.46, Color(red: 0.20, green: 0.16, blue: 0.66), 0.50, seed: 101),
            make(0.22, 0.26, 0.40, Color(red: 0.06, green: 0.16, blue: 0.54), 0.44, seed: 102),
            make(0.42, 0.74, 0.46, Color(red: 0.24, green: 0.12, blue: 0.54), 0.40, seed: 103),
            make(0.90, 0.78, 0.32, Color(red: 0.03, green: 0.28, blue: 0.40), 0.38, seed: 104),
            make(0.62, 0.36, 0.20, Color(red: 0.55, green: 0.16, blue: 0.08), 0.22, seed: 105),
            make(0.08, 0.84, 0.32, Color(red: 0.10, green: 0.12, blue: 0.48), 0.38, seed: 106),
        ]
    }

    static func solarSet() -> [NebulaCloud] {
        [
            make(0.20, 0.34, 0.46, Color(red: 0.08, green: 0.22, blue: 0.64), 0.46, seed: 201),
            make(0.54, 0.76, 0.48, Color(red: 0.28, green: 0.18, blue: 0.66), 0.40, seed: 202),
            make(0.88, 0.70, 0.34, Color(red: 0.04, green: 0.34, blue: 0.48), 0.40, seed: 203),
            make(0.80, 0.22, 0.34, Color(red: 0.72, green: 0.44, blue: 0.16), 0.26, seed: 204),
            make(0.08, 0.82, 0.32, Color(red: 0.16, green: 0.14, blue: 0.54), 0.38, seed: 205),
        ]
    }
}

private struct DustLane {
    var x: CGFloat
    var y: CGFloat
    var length: CGFloat
    var thickness: CGFloat
    var rotation: Double
    var phase: Double

    static func set() -> [DustLane] {
        [
            DustLane(x: 0.40, y: 0.46, length: 0.8, thickness: 0.07, rotation: -0.22, phase: 0),
            DustLane(x: 0.70, y: 0.66, length: 0.5, thickness: 0.09, rotation: 0.3, phase: 2),
            DustLane(x: 0.18, y: 0.30, length: 0.4, thickness: 0.08, rotation: -0.5, phase: 4),
        ]
    }
}

private struct Galaxy {
    var x: CGFloat
    var y: CGFloat
    var size: CGFloat
    var tilt: Double
    var squash: CGFloat
    var color: Color
    var core: Color
    var speed: Double
    var spin: Double

    static func set() -> [Galaxy] {
        [
            Galaxy(x: 0.10, y: 0.22, size: 120, tilt: -0.5, squash: 0.34, color: Color(red: 0.46, green: 0.44, blue: 1), core: Color(red: 1, green: 0.86, blue: 0.62), speed: 0.8, spin: 0.010),
            Galaxy(x: 0.50, y: 0.84, size: 96, tilt: -0.2, squash: 0.30, color: Color(red: 0.36, green: 0.62, blue: 1), core: .white, speed: 1.0, spin: 0.008),
            Galaxy(x: 0.30, y: 0.58, size: 42, tilt: 1.1, squash: 0.5, color: Color(red: 0.62, green: 0.54, blue: 1), core: .white, speed: 0.45, spin: 0.015),
            Galaxy(x: 0.92, y: 0.86, size: 56, tilt: -0.9, squash: 0.44, color: Color(red: 0.30, green: 0.80, blue: 0.86), core: .white, speed: 0.55, spin: -0.01),
            Galaxy(x: 0.62, y: 0.06, size: 30, tilt: 0.4, squash: 0.55, color: Color(red: 0.70, green: 0.74, blue: 1), core: .white, speed: 0.35, spin: 0.02),
            Galaxy(x: 0.20, y: 0.92, size: 62, tilt: 0.2, squash: 0.32, color: Color(red: 0.40, green: 0.46, blue: 0.96), core: Color(red: 1, green: 0.90, blue: 0.70), speed: 0.7, spin: -0.009),
            Galaxy(x: 0.40, y: 0.36, size: 22, tilt: 0.9, squash: 0.5, color: Color(red: 0.54, green: 0.80, blue: 1), core: .white, speed: 0.3, spin: -0.02),
        ]
    }
}

private struct Streamer {
    var angle: Double
    var length: CGFloat
    var strength: Double
    var width: CGFloat

    static func set() -> [Streamer] {
        var rng = SeededRandom(seed: 303)
        return (0..<64).map { index in
            Streamer(
                angle: Double(index) / 64 * 2 * .pi + (rng.next() - 0.5) * 0.08,
                length: 1.3 + CGFloat(pow(rng.next(), 2.2)) * 3.2,
                strength: 0.08 + rng.next() * 0.18,
                width: 0.6 + CGFloat(rng.next()) * 1.2
            )
        }
    }
}

private struct Flare {
    var angle: Double
    var cycle: Double
    var offset: Double

    static func set() -> [Flare] {
        [
            Flare(angle: 0.3, cycle: 17, offset: 0),
            Flare(angle: 2.8, cycle: 23, offset: 6),
            Flare(angle: 4.9, cycle: 29, offset: 13),
        ]
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
    var reach: CGFloat
    var color: Color

    static func set() -> [Meteor] {
        [
            Meteor(startX: 0.04, startY: 0.10, dirX: 0.94, dirY: 0.34, length: 150, depth: 1.0, cycle: 34, visible: 0.22, offset: 0, reach: 0.7, color: Color(red: 0.76, green: 0.88, blue: 1)),
            Meteor(startX: 0.58, startY: 0.02, dirX: 0.78, dirY: 0.62, length: 90, depth: 0.6, cycle: 41, visible: 0.18, offset: 8, reach: 0.45, color: Color(red: 0.72, green: 0.70, blue: 1)),
            Meteor(startX: 0.96, startY: 0.40, dirX: -0.90, dirY: 0.44, length: 120, depth: 0.85, cycle: 47, visible: 0.20, offset: 15, reach: 0.6, color: .white),
            Meteor(startX: 0.20, startY: 0.56, dirX: 0.97, dirY: 0.24, length: 60, depth: 0.4, cycle: 38, visible: 0.16, offset: 22, reach: 0.4, color: Color(red: 0.62, green: 0.95, blue: 1)),
            Meteor(startX: 0.74, startY: 0.76, dirX: 0.62, dirY: -0.78, length: 80, depth: 0.5, cycle: 53, visible: 0.17, offset: 29, reach: 0.4, color: Color(red: 1, green: 0.84, blue: 0.62)),
            Meteor(startX: 0.40, startY: 0.04, dirX: -0.55, dirY: 0.84, length: 70, depth: 0.45, cycle: 59, visible: 0.15, offset: 36, reach: 0.35, color: Color(red: 1, green: 0.90, blue: 0.72)),
            Meteor(startX: 0.02, startY: 0.84, dirX: 0.92, dirY: -0.40, length: 110, depth: 0.75, cycle: 64, visible: 0.18, offset: 44, reach: 0.65, color: Color(red: 0.70, green: 0.76, blue: 1)),
            Meteor(startX: 0.86, startY: 0.56, dirX: -0.96, dirY: 0.10, length: 50, depth: 0.35, cycle: 45, visible: 0.14, offset: 51, reach: 0.3, color: .white),
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

// MARK: - Spacecraft glass panels

struct GlassSurface: ViewModifier {
    var radius: CGFloat = 18
    var tint: Color = .clear
    var tintOpacity: Double = 0
    var elevated = true
    @Environment(\.nexusBright) private var bright

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: radius, style: .continuous)
        let edge = CosmicLight.edge(bright: bright)
        content
            .background {
                ZStack {
                    shape.fill(Color(red: 0.02, green: 0.025, blue: 0.06).opacity(elevated ? 0.30 : 0.24))
                    shape.fill(
                        LinearGradient(
                            colors: [edge.opacity(0.08), .clear, Color(red: 0.25, green: 0.45, blue: 1).opacity(0.04)],
                            startPoint: .topTrailing,
                            endPoint: .bottomLeading
                        )
                    )
                    shape.fill(RadialGradient(colors: [tint.opacity(tintOpacity), .clear], center: .topLeading, startRadius: 0, endRadius: 420))
                }
            }
            .overlay {
                shape
                    .fill(LinearGradient(colors: [.white.opacity(elevated ? 0.07 : 0.03), .white.opacity(0)], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.08)))
                    .allowsHitTesting(false)
            }
            .overlay {
                shape
                    .fill(
                        LinearGradient(
                            stops: [
                                .init(color: .clear, location: 0.34),
                                .init(color: .white.opacity(0.045), location: 0.44),
                                .init(color: .clear, location: 0.54),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .allowsHitTesting(false)
            }
            .overlay {
                shape.strokeBorder(
                    LinearGradient(
                        colors: [edge.opacity(0.85), .white.opacity(0.18), .white.opacity(0.05), edge.opacity(0.28)],
                        startPoint: .topTrailing,
                        endPoint: .bottomLeading
                    ),
                    lineWidth: 1
                )
            }
            .overlay {
                shape.inset(by: 1.5).strokeBorder(.white.opacity(0.05), lineWidth: 1)
            }
            .shadow(color: edge.opacity(elevated ? 0.12 : 0), radius: 22)
            .shadow(color: .black.opacity(elevated ? 0.6 : 0.3), radius: elevated ? 28 : 10, y: elevated ? 18 : 5)
    }
}

extension View {
    func glass(radius: CGFloat = 18, tint: Color = .clear, opacity: Double = 0, elevated: Bool = true) -> some View {
        modifier(GlassSurface(radius: radius, tint: tint, tintOpacity: opacity, elevated: elevated))
    }

    func interactiveGlass(
        accent: Color,
        radius: CGFloat,
        selected: Bool = false,
        intensity: Double = 1,
        lift: CGFloat = 1.03,
        pressable: Bool = true
    ) -> some View {
        modifier(InteractiveGlass(accent: accent, radius: radius, selected: selected, intensity: intensity, lift: lift, pressable: pressable))
    }
}

// MARK: - Cursor-reactive glass

struct InteractiveGlass: ViewModifier {
    var accent: Color
    var radius: CGFloat
    var selected: Bool
    var intensity: Double
    var lift: CGFloat
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
                    shape.fill(Color(red: 0.02, green: 0.025, blue: 0.06).opacity(0.58))
                    shape.fill(
                        LinearGradient(
                            colors: [
                                accent.opacity((selected ? 0.34 : (hovering ? 0.26 : 0.16)) * intensity),
                                accent.opacity((selected ? 0.12 : 0.04) * intensity),
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    shape.fill(
                        RadialGradient(
                            colors: [accent.opacity((lit ? 0.40 : 0.22) * intensity), .clear],
                            center: .leading,
                            startRadius: 0,
                            endRadius: 130
                        )
                    )
                }
            }
            .overlay {
                shape
                    .fill(LinearGradient(colors: [.white.opacity(lit ? 0.18 : 0.11), .white.opacity(0)], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.45)))
                    .allowsHitTesting(false)
            }
            .overlay {
                GeometryReader { proxy in
                    ZStack {
                        if hovering, let cursor {
                            Circle()
                                .fill(RadialGradient(colors: [.white.opacity(0.20), accent.opacity(0.16), .clear], center: .center, startRadius: 0, endRadius: 60))
                                .frame(width: 120, height: 120)
                                .position(cursor)
                                .blendMode(.plusLighter)
                            Circle()
                                .fill(RadialGradient(colors: [accent.opacity(0.18), .clear], center: .center, startRadius: 0, endRadius: 44))
                                .frame(width: 88, height: 88)
                                .position(x: proxy.size.width - cursor.x, y: proxy.size.height - cursor.y)
                                .blendMode(.plusLighter)
                        }
                        if hovering, let start = hoverStart {
                            SweepBand(size: proxy.size)
                                .id(start)
                        }
                    }
                    .clipShape(shape)
                }
                .allowsHitTesting(false)
            }
            .overlay {
                shape.strokeBorder(
                    LinearGradient(
                        colors: [.white.opacity(lit ? 0.72 : 0.40), accent.opacity(lit ? 0.95 : 0.62), accent.opacity(0.2)],
                        startPoint: .top,
                        endPoint: .bottom
                    ),
                    lineWidth: lit ? 1.3 : 1
                )
            }
            .overlay {
                shape.inset(by: 1).strokeBorder(.white.opacity(0.05), lineWidth: 1)
            }
            .shadow(color: accent.opacity((lit ? 0.55 : 0.10) * intensity), radius: lit ? 16 : 5, y: 2)
            .shadow(color: .black.opacity(0.55), radius: hovering ? 16 : 8, y: hovering ? 11 : 5)
            .offset(y: hovering ? -1.5 : 0)
            .scaleEffect(pressed ? 0.965 : (hovering ? lift : 1))
            .brightness(pressed ? 0.08 : 0)
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

private struct SweepBand: View {
    var size: CGSize
    @State private var progress: CGFloat = 0

    var body: some View {
        LinearGradient(colors: [.clear, .white.opacity(0.28), .clear], startPoint: .leading, endPoint: .trailing)
            .frame(width: max(24, size.width * 0.22), height: size.height * 2.2)
            .rotationEffect(.degrees(20))
            .position(x: -size.width * 0.3 + progress * size.width * 1.6, y: size.height / 2)
            .blendMode(.plusLighter)
            .onAppear {
                withAnimation(.easeOut(duration: 0.9)) { progress = 1 }
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
                .frame(minWidth: 104, minHeight: 40)
                .padding(.horizontal, 12)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .interactiveGlass(accent: colors.first ?? .blue, radius: 12)
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
                    .fill(LinearGradient(colors: [.white.opacity(0.85), accent], startPoint: .top, endPoint: .bottom))
                    .frame(width: 3)
                    .padding(.vertical, 10)
                    .padding(.leading, 7)
                    .shadow(color: accent, radius: selected ? 7 : 3)
            }
            .contentShape(Rectangle())
            .interactiveGlass(accent: accent, radius: 12, selected: selected, intensity: 1, lift: 1.02)
    }
}

// MARK: - Safari mode switch

struct SafariModeSwitch: View {
    @Binding var isPrivate: Bool
    @Namespace private var thumb

    var body: some View {
        HStack(spacing: 4) {
            segment("Standard Safari", icon: "sun.max.fill", selected: !isPrivate, accent: Color(hex: "#F5C26B")) { isPrivate = false }
            segment("Private Safari", icon: "lock.fill", selected: isPrivate, accent: Color(hex: "#8C7BFF")) { isPrivate = true }
        }
        .padding(4)
        .glass(radius: 14, elevated: false)
    }

    private func segment(_ title: String, icon: String, selected: Bool, accent: Color, action: @escaping () -> Void) -> some View {
        Button {
            withAnimation(.spring(duration: 0.35, bounce: 0.25)) { action() }
        } label: {
            Label(title, systemImage: icon)
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(selected ? Color.white : Color.white.opacity(0.58))
                .padding(.horizontal, 12)
                .frame(height: 28)
                .background {
                    if selected {
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(LinearGradient(colors: [accent.opacity(0.42), accent.opacity(0.16)], startPoint: .top, endPoint: .bottom))
                            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(accent.opacity(0.9), lineWidth: 1))
                            .shadow(color: accent.opacity(0.55), radius: 9)
                            .matchedGeometryEffect(id: "thumb", in: thumb)
                    }
                }
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
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
