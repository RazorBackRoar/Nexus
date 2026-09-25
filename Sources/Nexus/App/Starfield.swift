import SwiftUI

struct StarfieldBackground: View {
    private static let stars: [(CGFloat, CGFloat, CGFloat)] = [
        (0.08, 0.12, 1.2), (0.16, 0.68, 1.6), (0.22, 0.30, 1.0), (0.29, 0.85, 1.3),
        (0.34, 0.15, 1.8), (0.41, 0.52, 1.1), (0.47, 0.78, 1.4), (0.53, 0.22, 1.2),
        (0.58, 0.62, 1.7), (0.64, 0.40, 1.0), (0.71, 0.90, 1.5), (0.76, 0.18, 1.2),
        (0.82, 0.55, 1.9), (0.88, 0.34, 1.1), (0.93, 0.74, 1.4), (0.12, 0.44, 0.9),
        (0.38, 0.94, 1.2), (0.67, 0.08, 1.3), (0.86, 0.92, 1.0), (0.05, 0.86, 1.5),
        (0.19, 0.56, 2.0), (0.61, 0.28, 2.2), (0.44, 0.71, 1.8),
    ]

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { timeline in
            Canvas { context, size in
                let time = timeline.date.timeIntervalSinceReferenceDate
                let sky = Gradient(colors: [
                    Color(red: 0.016, green: 0.035, blue: 0.08),
                    Color(red: 0.008, green: 0.024, blue: 0.055),
                    Color(red: 0.004, green: 0.012, blue: 0.03),
                ])
                context.fill(Path(CGRect(origin: .zero, size: size)), with: .linearGradient(
                    sky, startPoint: .zero, endPoint: CGPoint(x: size.width, y: size.height)
                ))

                var nebula = context
                nebula.opacity = 0.45
                let wash = Gradient(colors: [
                    .clear,
                    Color(red: 0.47, green: 0.27, blue: 0.82).opacity(0.35),
                    Color(red: 0.24, green: 0.43, blue: 0.90).opacity(0.28),
                    .clear,
                ])
                nebula.fill(Path(CGRect(origin: .zero, size: size)), with: .linearGradient(
                    wash,
                    startPoint: CGPoint(x: 0, y: size.height * 0.35),
                    endPoint: CGPoint(x: size.width, y: size.height * 0.7)
                ))

                for (index, star) in Self.stars.enumerated() {
                    let twinkle = 0.55 + 0.45 * abs(sin(time * 1.6 + Double(index)))
                    let rect = CGRect(
                        x: size.width * star.0,
                        y: size.height * star.1,
                        width: star.2 * 2,
                        height: star.2 * 2
                    )
                    context.fill(Path(ellipseIn: rect), with: .color(.white.opacity(twinkle)))
                }

                for index in 0..<5 {
                    let cycle = 3.4 + Double(index) * 0.45
                    let phase = (time + Double(index) * 0.8).truncatingRemainder(dividingBy: cycle) / cycle
                    let startX = size.width * (-0.15 + CGFloat(phase) * 1.35)
                    let startY = size.height * (0.05 + CGFloat(index) * 0.12 + CGFloat(phase) * 0.35)
                    var trail = Path()
                    trail.move(to: CGPoint(x: startX - 90, y: startY - 38))
                    trail.addLine(to: CGPoint(x: startX, y: startY))
                    context.stroke(
                        trail,
                        with: .linearGradient(
                            Gradient(colors: [.clear, Color(red: 0.55, green: 0.82, blue: 1), .white]),
                            startPoint: CGPoint(x: startX - 90, y: startY - 38),
                            endPoint: CGPoint(x: startX, y: startY)
                        ),
                        lineWidth: 2
                    )
                    context.fill(
                        Path(ellipseIn: CGRect(x: startX - 2, y: startY - 2, width: 4, height: 4)),
                        with: .color(.white)
                    )
                }
            }
        }
        .ignoresSafeArea()
    }
}

struct ColorActionButton: View {
    var title: String
    var colors: [Color]
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.body.weight(.semibold))
                .foregroundStyle(.white)
                .frame(minWidth: 108, minHeight: 46)
                .background(
                    LinearGradient(colors: colors, startPoint: .top, endPoint: .bottom),
                    in: RoundedRectangle(cornerRadius: 12, style: .continuous)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .strokeBorder(.white.opacity(0.35), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
    }
}
