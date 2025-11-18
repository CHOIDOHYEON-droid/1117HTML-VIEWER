import UIKit
import Capacitor
import WebKit

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    // Store pending file URL when app is already running
    var pendingFileURL: URL?

    // Access to Capacitor's web view
    var capacitorViewController: CAPBridgeViewController? {
        return window?.rootViewController as? CAPBridgeViewController
    }

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Override point for customization after application launch.

        // Check if app was launched with a file URL
        if let url = launchOptions?[.url] as? URL {
            print("🚀 App launched with URL: \(url)")
            if url.pathExtension.lowercased() == "html" || url.pathExtension.lowercased() == "htm" {
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

        // Handle HTML files
        if url.pathExtension.lowercased() == "html" || url.pathExtension.lowercased() == "htm" {
            // Store the URL and try to open immediately
            pendingFileURL = url
            print("💾 Stored pending file URL: \(url.lastPathComponent)")

            // Try to open immediately (might fail if webView not ready)
            openFileInWebView(url: url)

            // Also try again after a delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                if self.pendingFileURL != nil {
                    print("🔄 Retry opening file after delay")
                    self.openFileInWebView(url: url)
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

        do {
            let htmlContent = try String(contentsOf: url, encoding: .utf8)
            let fileName = url.lastPathComponent

            print("✅ File read successfully: \(fileName) (Security scoped: \(didStartAccess))")

            // Escape content for JavaScript
            let escapedContent = htmlContent
                .replacingOccurrences(of: "\\", with: "\\\\")
                .replacingOccurrences(of: "\"", with: "\\\"")
                .replacingOccurrences(of: "\n", with: "\\n")
                .replacingOccurrences(of: "\r", with: "\\r")
                .replacingOccurrences(of: "'", with: "\\'")

            let escapedFileName = fileName
                .replacingOccurrences(of: "\\", with: "\\\\")
                .replacingOccurrences(of: "\"", with: "\\\"")
                .replacingOccurrences(of: "'", with: "\\'")

            // 1단계: 외부 파일 플래그 먼저 설정
            let setFlagCode = """
            (function() {
                console.log('🚀 Setting external file flag');
                localStorage.setItem('__external_file_launch', 'true');
                if (typeof window.setExternalFileFlag === 'function') {
                    window.setExternalFileFlag();
                }
                console.log('✅ Flag set');
            })();
            """

            webView.evaluateJavaScript(setFlagCode) { _, _ in
                // 2단계: 플래그 설정 후 파일 열기 시도
                let openFileCode = """
                (function() {
                    console.log('🚀 Attempting to open file from native');

                    // FileOpener가 준비될 때까지 최대 5초 대기
                    var attempts = 0;
                    var maxAttempts = 50;

                    function tryOpen() {
                        attempts++;
                        console.log('Attempt ' + attempts + ': Checking for FileOpener...');

                        if (typeof window.openExternalFile === 'function') {
                            console.log('✅ openExternalFile found, calling it now');
                            window.openExternalFile("\(escapedFileName)", "\(escapedContent)");
                            return true;
                        } else if (attempts < maxAttempts) {
                            console.log('⏳ FileOpener not ready, retrying in 100ms...');
                            setTimeout(tryOpen, 100);
                            return false;
                        } else {
                            console.error('❌ window.openExternalFile not found after ' + attempts + ' attempts');
                            console.log('Available:', Object.keys(window).filter(k => k.includes('open')));

                            // 최후의 수단: 페이지 새로고침으로 플래그 적용
                            console.log('🔄 Reloading page to apply flag...');
                            window.location.reload();
                            return false;
                        }
                    }

                    tryOpen();
                })();
                """

                webView.evaluateJavaScript(openFileCode) { result, error in
                    if let error = error {
                        print("❌ JavaScript error: \\(error)")
                    } else {
                        print("✅ JavaScript executed successfully")
                        // Clear pending file after successful execution
                        self.pendingFileURL = nil
                    }
                }
            }

        } catch {
            print("❌ Error reading file: \(error)")
        }
    }

}
