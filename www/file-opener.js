// File Opener Bridge - Simple JavaScript interface
window.FileOpener = {
    listeners: [],

    addListener(callback) {
        this.listeners.push(callback);
        console.log('FileOpener listener added');
    },

    openFile(fileName, content) {
        console.log('FileOpener: Opening file', fileName);
        this.listeners.forEach(callback => {
            try {
                callback({ fileName, content });
            } catch (e) {
                console.error('FileOpener listener error:', e);
            }
        });
    }
};

// iOS에서 호출할 수 있는 전역 함수
window.openExternalFile = function(fileName, content) {
    console.log('openExternalFile called:', fileName);
    if (window.FileOpener) {
        window.FileOpener.openFile(fileName, content);
    }
};

console.log('FileOpener bridge loaded');
