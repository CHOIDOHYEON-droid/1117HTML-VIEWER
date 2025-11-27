import UIKit
import Capacitor
import WebKit

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    // Store pending file URL when app is already running
    var pendingFileURL: URL?

    // 지원하는 파일 확장자
    let htmlExtensions = ["html", "htm"]
    let modelExtensions = ["stl", "ply", "obj"]

    // Access to Capacitor's web view
    var capacitorViewController: CAPBridgeViewController? {
        return window?.rootViewController as? CAPBridgeViewController
    }

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Override point for customization after application launch.

        // Check if app was launched with a file URL
        if let url = launchOptions?[.url] as? URL {
            print("🚀 App launched with URL: \(url)")
            let ext = url.pathExtension.lowercased()

            if htmlExtensions.contains(ext) || modelExtensions.contains(ext) {
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                    self.openFileInWebView(url: url)
                }
            }
        }

        return true
    }

    func applicationWillResignActive(_ application: UIApplication) {
        // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
        // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
        // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.

        // Check if there's a pending file to open
        if let url = pendingFileURL {
            print("✅ App became active, opening pending file: \(url.lastPathComponent)")

            // IMPORTANT: Clear pendingFileURL IMMEDIATELY to prevent duplicate opens
            self.pendingFileURL = nil

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                self.openFileInWebView(url: url)
            }
        }
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        // Called when the app was launched with a url. Feel free to add additional processing here,
        // but if you want the App API to support tracking app url opens, make sure to keep this call

        print("📂 application(_:open:options:) called with URL: \(url)")
        print("   Options: \(options)")

        let ext = url.pathExtension.lowercased()

        // Handle HTML and 3D model files
        if htmlExtensions.contains(ext) || modelExtensions.contains(ext) {
            // IMPORTANT: Clear old pendingFileURL and store new one
            print("🔄 Clearing old pending file (if any)")
            pendingFileURL = nil

            // Store the NEW URL
            pendingFileURL = url
            print("💾 Stored NEW pending file URL: \(url.lastPathComponent)")

            // Try to open immediately (might fail if webView not ready)
            openFileInWebView(url: url)

            // Also try again after a delay (only if still pending)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                // Only retry if the URL is still the same one we're trying to open
                if self.pendingFileURL?.absoluteString == url.absoluteString {
                    print("🔄 Retry opening file after delay: \(url.lastPathComponent)")
                    self.openFileInWebView(url: url)
                } else {
                    print("⏭️ Skip retry - URL changed or already opened")
                }
            }
        }

        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }

    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        // Called when the app was launched with an activity, including Universal Links.
        // Feel free to add additional processing here, but if you want the App API to support
        // tracking app url opens, make sure to keep this call
        return ApplicationDelegateProxy.shared.application(application, continue: userActivity, restorationHandler: restorationHandler)
    }


    func openFileInWebView(url: URL) {
        // WebView 준비 확인 - 준비되지 않았으면 재시도
        guard let webView = capacitorViewController?.webView else {
            print("⏳ WebView not ready yet, will retry...")

            // pendingFileURL에 저장하여 나중에 재시도
            pendingFileURL = url

            // 0.5초 후 재시도
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                self.openFileInWebView(url: url)
            }
            return
        }

        // IMPORTANT: Start accessing security-scoped resource
        let didStartAccess = url.startAccessingSecurityScopedResource()
        defer {
            if didStartAccess {
                url.stopAccessingSecurityScopedResource()
            }
        }

        let ext = url.pathExtension.lowercased()
        let fileName = url.lastPathComponent

        // 파일명 이스케이프
        let escapedFileName = fileName
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "'", with: "\\'")

        // 1단계: 앱 상태 완전 초기화
        let resetCode = """
        (function() {
            console.log('🔄 [Native] Resetting app for external file');

            if (typeof window.resetAppForExternalFile === 'function') {
                window.resetAppForExternalFile();
                console.log('✅ [Native] App reset via function');
            } else {
                localStorage.clear();
                var viewer = document.getElementById('htmlViewer');
                var frame = document.getElementById('viewerFrame');
                var viewer3D = document.getElementById('viewer3D');
                var container = document.querySelector('.container');
                if (viewer) viewer.classList.remove('active');
                if (frame) frame.srcdoc = '';
                if (viewer3D) viewer3D.classList.remove('active');
                if (container) container.style.display = 'none';
                window.externalFileOpened = true;
                console.log('✅ [Native] App reset manually');
            }
        })();
        """

        // HTML 파일 처리
        if htmlExtensions.contains(ext) {
            do {
                let htmlContent = try String(contentsOf: url, encoding: .utf8)
                print("✅ HTML file read successfully: \(fileName) (Security scoped: \(didStartAccess))")

                let escapedContent = htmlContent
                    .replacingOccurrences(of: "\\", with: "\\\\")
                    .replacingOccurrences(of: "\"", with: "\\\"")
                    .replacingOccurrences(of: "\n", with: "\\n")
                    .replacingOccurrences(of: "\r", with: "\\r")
                    .replacingOccurrences(of: "'", with: "\\'")

                webView.evaluateJavaScript(resetCode) { _, _ in
                    let openFileCode = """
                    (function() {
                        console.log('🚀 Attempting to open HTML file from native');
                        var attempts = 0;
                        var maxAttempts = 50;

                        function tryOpen() {
                            attempts++;
                            if (typeof window.openExternalFile === 'function') {
                                console.log('✅ openExternalFile found');
                                window.openExternalFile("\(escapedFileName)", "\(escapedContent)", "text");
                                return true;
                            } else if (attempts < maxAttempts) {
                                setTimeout(tryOpen, 100);
                                return false;
                            } else {
                                console.error('❌ window.openExternalFile not found');
                                window.location.reload();
                                return false;
                            }
                        }
                        tryOpen();
                    })();
                    """

                    webView.evaluateJavaScript(openFileCode) { result, error in
                        if let error = error {
                            print("❌ JavaScript error: \(error)")
                        } else {
                            print("✅ JavaScript executed successfully")
                        }

                        if self.pendingFileURL?.absoluteString == url.absoluteString {
                            print("🧹 Clearing pendingFileURL for: \(url.lastPathComponent)")
                            self.pendingFileURL = nil
                        }
                    }
                }
            } catch {
                print("❌ Error reading HTML file: \(error)")
            }
        }
        // 3D 모델 파일 처리 (STL, PLY, OBJ)
        else if modelExtensions.contains(ext) {
            do {
                let data = try Data(contentsOf: url)
                let base64Content = data.base64EncodedString()
                print("✅ 3D file read successfully: \(fileName) (Size: \(data.count) bytes, Security scoped: \(didStartAccess))")

                webView.evaluateJavaScript(resetCode) { _, _ in
                    let openFileCode = """
                    (function() {
                        console.log('🚀 Attempting to open 3D file from native');
                        var attempts = 0;
                        var maxAttempts = 50;

                        function tryOpen() {
                            attempts++;
                            if (typeof window.openExternalFile === 'function') {
                                console.log('✅ openExternalFile found');
                                window.openExternalFile("\(escapedFileName)", "\(base64Content)", "base64");
                                return true;
                            } else if (attempts < maxAttempts) {
                                setTimeout(tryOpen, 100);
                                return false;
                            } else {
                                console.error('❌ window.openExternalFile not found');
                                window.location.reload();
                                return false;
                            }
                        }
                        tryOpen();
                    })();
                    """

                    webView.evaluateJavaScript(openFileCode) { result, error in
                        if let error = error {
                            print("❌ JavaScript error: \(error)")
                        } else {
                            print("✅ JavaScript executed successfully")
                        }

                        if self.pendingFileURL?.absoluteString == url.absoluteString {
                            print("🧹 Clearing pendingFileURL for: \(url.lastPathComponent)")
                            self.pendingFileURL = nil
                        }
                    }
                }
            } catch {
                print("❌ Error reading 3D file: \(error)")
            }
        }
    }

}
