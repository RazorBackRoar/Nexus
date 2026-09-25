// swift-tools-version: 6.3

import PackageDescription

let package = Package(
    name: "Nexus",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Nexus", targets: ["Nexus"])
    ],
    targets: [
        .executableTarget(
            name: "Nexus",
            path: "Sources/Nexus",
            resources: [
                .process("Resources")
            ],
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
        .testTarget(
            name: "NexusTests",
            dependencies: ["Nexus"],
            path: "Tests/NexusTests",
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
    ]
)
