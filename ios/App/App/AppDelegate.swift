import UIKit
import Capacitor
import WebKit

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

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
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        // Called when the app was launched with a url. Feel free to add additional processing here,
        // but if you want the App API to support tracking app url opens, make sure to keep this call

        print("📂 application(_:open:options:) called with URL: \(url)")
        print("   Options: \(options)")

        // Handle HTML files immediately
        if url.pathExtension.lowercased() == "html" || url.pathExtension.lowercased() == "htm" {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                self.openFileInWebView(url: url)
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
        guard let webView = capacitorViewController?.webView else {
            print("❌ WebView not found")
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

            // Call JavaScript function
            let jsCode = """
            (function() {
                console.log('🚀 Attempting to open file from native');
                if (typeof window.openExternalFile === 'function') {
                    window.openExternalFile("\(escapedFileName)", "\(escapedContent)");
                    console.log('✅ openExternalFile called');
                } else {
                    console.error('❌ window.openExternalFile not found');
                    console.log('Available:', Object.keys(window).filter(k => k.includes('open')));
                }
            })();
            """

            webView.evaluateJavaScript(jsCode) { result, error in
                if let error = error {
                    print("❌ JavaScript error: \(error)")
                } else {
                    print("✅ JavaScript executed successfully")
                }
            }

        } catch {
            print("❌ Error reading file: \(error)")
        }
    }

}
