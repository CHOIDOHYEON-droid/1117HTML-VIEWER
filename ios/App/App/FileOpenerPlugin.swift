import Foundation
import Capacitor

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

        // Send data to JavaScript
        self.notifyListeners("fileOpened", data: [
            "fileName": fileName,
            "content": content
        ])
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}
