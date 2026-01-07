// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "video-stitch-swift",
    platforms: [
        .macOS(.v13)
    ],
    targets: [
        .executableTarget(
            name: "video-stitch-swift",
            path: "Sources/video-stitch-swift"
        )
    ]
)
