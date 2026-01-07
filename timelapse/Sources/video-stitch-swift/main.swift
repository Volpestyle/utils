import Foundation
import AVFoundation
import CoreMedia
import VideoToolbox

// MARK: - Color Output
struct Colors {
    static let blue = "\u{001B}[0;34m"
    static let green = "\u{001B}[0;32m"
    static let yellow = "\u{001B}[1;33m"
    static let red = "\u{001B}[0;31m"
    static let reset = "\u{001B}[0m"
}

func logInfo(_ message: String) {
    print("\(Colors.blue)[INFO]\(Colors.reset) \(message)")
}

func logSuccess(_ message: String) {
    print("\(Colors.green)[SUCCESS]\(Colors.reset) \(message)")
}

func logWarn(_ message: String) {
    print("\(Colors.yellow)[WARN]\(Colors.reset) \(message)")
}

func logError(_ message: String) {
    print("\(Colors.red)[ERROR]\(Colors.reset) \(message)")
}

func logProgress(_ current: Int, _ total: Int, _ filename: String) {
    print("\(Colors.blue)[\(current)/\(total)]\(Colors.reset) Processing: \(filename)")
}

// MARK: - Video Processing

class VideoStitcher {
    let speedFactor: Double
    let outputURL: URL
    let sortByName: Bool
    let outputFPS: Double = 24.0

    init(speedFactor: Double, outputURL: URL, sortByName: Bool) {
        self.speedFactor = speedFactor
        self.outputURL = outputURL
        self.sortByName = sortByName
    }

    func findVideos(in folder: URL) -> [URL] {
        let fileManager = FileManager.default
        let videoExtensions = ["mp4", "mov", "avi", "mkv", "webm", "m4v"]

        guard let contents = try? fileManager.contentsOfDirectory(
            at: folder,
            includingPropertiesForKeys: [.contentModificationDateKey, .isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var videos: [(url: URL, date: Date)] = []

        for url in contents {
            let ext = url.pathExtension.lowercased()
            guard videoExtensions.contains(ext) else { continue }
            if url.lastPathComponent.hasPrefix("._") { continue }

            if let resourceValues = try? url.resourceValues(forKeys: [.contentModificationDateKey, .isRegularFileKey]),
               resourceValues.isRegularFile == true {
                let date = resourceValues.contentModificationDate ?? Date.distantPast
                videos.append((url, date))
            }
        }

        if sortByName {
            videos.sort { $0.url.lastPathComponent < $1.url.lastPathComponent }
        } else {
            videos.sort { $0.date < $1.date }
        }

        return videos.map { $0.url }
    }

    func processVideos(_ videoURLs: [URL]) async throws {
        guard !videoURLs.isEmpty else {
            throw VideoError.noVideosFound
        }

        // Remove existing output file
        try? FileManager.default.removeItem(at: outputURL)

        // Get video properties from first video
        let firstAsset = AVURLAsset(url: videoURLs[0])
        guard let firstTrack = try await firstAsset.loadTracks(withMediaType: .video).first else {
            throw VideoError.cannotCreateTrack
        }

        let naturalSize = try await firstTrack.load(.naturalSize)
        let transform = try await firstTrack.load(.preferredTransform)

        // Apply transform to get correct dimensions
        let transformedSize = naturalSize.applying(transform)
        let width = abs(transformedSize.width)
        let height = abs(transformedSize.height)

        logInfo("Output resolution: \(Int(width))x\(Int(height))")

        // Setup AVAssetWriter
        let writer = try AVAssetWriter(outputURL: outputURL, fileType: .mp4)

        let videoSettings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: width,
            AVVideoHeightKey: height,
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: 8_000_000,
                AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                AVVideoExpectedSourceFrameRateKey: outputFPS
            ]
        ]

        let writerInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
        writerInput.expectsMediaDataInRealTime = false
        // Don't apply transform here - we already accounted for it in output dimensions

        let adaptor = AVAssetWriterInputPixelBufferAdaptor(
            assetWriterInput: writerInput,
            sourcePixelBufferAttributes: [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                kCVPixelBufferWidthKey as String: width,
                kCVPixelBufferHeightKey as String: height
            ]
        )

        writer.add(writerInput)
        writer.startWriting()
        writer.startSession(atSourceTime: .zero)

        var totalOriginalDuration: Double = 0
        var currentOutputTime = CMTime.zero
        let outputFrameDuration = CMTime(value: 1, timescale: CMTimeScale(outputFPS))

        // Calculate how many source frames to skip between output frames
        // At 100x speed with 30fps source and 24fps output:
        // We want 1 frame per (100/24) = 4.17 seconds of source video
        // At 30fps source, that's 125 frames between each output frame

        let total = videoURLs.count

        for (index, videoURL) in videoURLs.enumerated() {
            logProgress(index + 1, total, videoURL.lastPathComponent)

            let asset = AVURLAsset(url: videoURL)
            let duration = try await asset.load(.duration)
            totalOriginalDuration += duration.seconds

            guard let videoTrack = try await asset.loadTracks(withMediaType: .video).first else {
                logWarn("No video track in \(videoURL.lastPathComponent), skipping...")
                continue
            }

            let nominalFrameRate = try await videoTrack.load(.nominalFrameRate)
            let sourceFPS = Double(nominalFrameRate)

            // Calculate frame interval: how many source frames between each output frame
            // speedFactor / outputFPS gives us seconds between output frames in original time
            // multiply by sourceFPS to get frame count
            let frameInterval = max(1, Int((speedFactor * sourceFPS) / outputFPS))

            // Setup reader
            let reader = try AVAssetReader(asset: asset)
            let readerOutput = AVAssetReaderTrackOutput(
                track: videoTrack,
                outputSettings: [
                    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
                ]
            )
            readerOutput.alwaysCopiesSampleData = false
            reader.add(readerOutput)
            reader.startReading()

            var frameCount = 0

            while reader.status == .reading {
                autoreleasepool {
                    guard let sampleBuffer = readerOutput.copyNextSampleBuffer() else { return }

                    // Only process every Nth frame
                    if frameCount % frameInterval == 0 {
                        if let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) {
                            while !writerInput.isReadyForMoreMediaData {
                                Thread.sleep(forTimeInterval: 0.01)
                            }

                            adaptor.append(imageBuffer, withPresentationTime: currentOutputTime)
                            currentOutputTime = CMTimeAdd(currentOutputTime, outputFrameDuration)
                        }
                    }

                    frameCount += 1
                }
            }

            reader.cancelReading()
        }

        writerInput.markAsFinished()

        await writer.finishWriting()

        if writer.status == .failed {
            throw writer.error ?? VideoError.exportFailed(.unknown)
        }

        // Print summary
        let finalDuration = currentOutputTime.seconds
        let fileSize = (try? FileManager.default.attributesOfItem(atPath: outputURL.path)[.size] as? Int64) ?? 0
        let fileSizeFormatted = ByteCountFormatter.string(fromByteCount: fileSize, countStyle: .file)

        print()
        logSuccess("Video processing complete!")
        print()
        print("  \(Colors.blue)Videos processed:\(Colors.reset)    \(total)")
        print("  \(Colors.blue)Original duration:\(Colors.reset)   \(formatDuration(totalOriginalDuration))")
        print("  \(Colors.blue)Final duration:\(Colors.reset)      \(formatDuration(finalDuration))")
        print("  \(Colors.blue)Speed factor:\(Colors.reset)        \(speedFactor)x")
        print("  \(Colors.blue)Output file:\(Colors.reset)         \(outputURL.path)")
        print("  \(Colors.blue)File size:\(Colors.reset)           \(fileSizeFormatted)")
    }

    private func formatDuration(_ seconds: Double) -> String {
        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let secs = Int(seconds) % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, secs)
    }
}

// MARK: - Errors

enum VideoError: LocalizedError {
    case noVideosFound
    case cannotCreateTrack
    case cannotCreateExportSession
    case exportFailed(AVAssetExportSession.Status)
    case invalidArguments

    var errorDescription: String? {
        switch self {
        case .noVideosFound:
            return "No video files found in the specified folder"
        case .cannotCreateTrack:
            return "Cannot create composition track"
        case .cannotCreateExportSession:
            return "Cannot create export session"
        case .exportFailed(let status):
            return "Export failed with status: \(status.rawValue)"
        case .invalidArguments:
            return "Invalid arguments"
        }
    }
}

// MARK: - Main

func printUsage() {
    print("""
    \(Colors.blue)video-stitch-swift\(Colors.reset) - Fast video timelapse creator using AVFoundation

    \(Colors.yellow)USAGE:\(Colors.reset)
        video-stitch-swift [OPTIONS] <input_folder>

    \(Colors.yellow)OPTIONS:\(Colors.reset)
        -s, --speed <factor>    Speed multiplier (default: 1.0)
        -o, --output <file>     Output filename (default: output_<timestamp>.mp4)
        -n, --sort-name         Sort videos by filename instead of modification time
        -h, --help              Show this help message

    \(Colors.yellow)EXAMPLES:\(Colors.reset)
        video-stitch-swift -s 100 ~/Videos
        video-stitch-swift -s 50 -o timelapse.mp4 ~/Videos
    """)
}

@main
struct VideoStitchApp {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())

        var speedFactor: Double = 1.0
        var outputFile: String?
        var sortByName = false
        var inputFolder: String?

        var i = 0
        while i < args.count {
            switch args[i] {
            case "-s", "--speed":
                i += 1
                if i < args.count, let speed = Double(args[i]) {
                    speedFactor = speed
                }
            case "-o", "--output":
                i += 1
                if i < args.count {
                    outputFile = args[i]
                }
            case "-n", "--sort-name":
                sortByName = true
            case "-h", "--help":
                printUsage()
                return
            default:
                if !args[i].hasPrefix("-") {
                    inputFolder = args[i]
                }
            }
            i += 1
        }

        guard let folder = inputFolder else {
            logError("No input folder specified. Use -h for help.")
            return
        }

        let folderURL = URL(fileURLWithPath: (folder as NSString).expandingTildeInPath)

        guard FileManager.default.fileExists(atPath: folderURL.path) else {
            logError("Input folder does not exist: \(folder)")
            return
        }

        let outputPath: String
        if let out = outputFile {
            outputPath = (out as NSString).expandingTildeInPath
        } else {
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyyMMdd_HHmmss"
            let timestamp = dateFormatter.string(from: Date())
            outputPath = "output_\(timestamp).mp4"
        }
        let outputURL = URL(fileURLWithPath: outputPath)

        print()
        print("\(Colors.blue)═══════════════════════════════════════════════════════════\(Colors.reset)")
        print("\(Colors.blue)              video-stitch-swift (AVFoundation)            \(Colors.reset)")
        print("\(Colors.blue)═══════════════════════════════════════════════════════════\(Colors.reset)")
        print()

        let stitcher = VideoStitcher(speedFactor: speedFactor, outputURL: outputURL, sortByName: sortByName)

        logInfo("Scanning folder for videos: \(folderURL.path)")
        let videos = stitcher.findVideos(in: folderURL)

        guard !videos.isEmpty else {
            logError("No video files found in \(folder)")
            return
        }

        logInfo("Found \(videos.count) video(s) to process")
        logInfo("Speed factor: \(speedFactor)x (keeping 1 of every \(Int(speedFactor)) frames)")
        logInfo("Output file: \(outputURL.path)")
        print()

        logInfo("Processing order:")
        for (index, video) in videos.enumerated() {
            print("  \(index + 1). \(video.lastPathComponent)")
        }
        print()

        do {
            try await stitcher.processVideos(videos)
        } catch {
            logError("Failed: \(error.localizedDescription)")
        }
    }
}
