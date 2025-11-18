import Foundation
import Capacitor
import WebKit

@objc(FileOpenerPlugin)
public class FileOpenerPlugin: CAPPlugin {

    override public func load() {
        // Listen for file open notifications
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleFileOpened(_:)),
            name: NSNotification.Name("ExternalFileOpened"),
            object: nil
        )
    }

    @objc func handleFileOpened(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let fileName = userInfo["fileName"] as? String,
              let content = userInfo["content"] as? String else {
            return
        }

        // Escape content for JavaScript
        let escapedContent = content
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: "\\n")
            .replacingOccurrences(of: "\r", with: "\\r")

        let escapedFileName = fileName
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")

        // Call JavaScript function directly
        let jsCode = """
        if (window.openExternalFile) {
            window.openExternalFile("\(escapedFileName)", "\(escapedContent)");
        } else {
            console.error('openExternalFile not found');
        }
        """

        DispatchQueue.main.async {
            self.bridge?.webView?.evaluateJavaScript(jsCode) { result, error in
                if let error = error {
                    print("Error calling JavaScript: \(error)")
                } else {
                    print("Successfully called openExternalFile")
                }
            }
        }
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}
