// File Opener Bridge - Simple JavaScript interface
window.FileOpener = {
    listeners: [],

    addListener(callback) {
        this.listeners.push(callback);
        console.log('FileOpener listener added');
    },

    openFile(fileName, content, encoding) {
        console.log('FileOpener: Opening file', fileName, 'encoding:', encoding || 'text');
        this.listeners.forEach(callback => {
            try {
                callback({ fileName, content, encoding: encoding || 'text' });
            } catch (e) {
                console.error('FileOpener listener error:', e);
            }
        });
    }
};

// iOS에서 호출할 수 있는 전역 함수
window.openExternalFile = function(fileName, content, encoding) {
    console.log('openExternalFile called:', fileName, 'encoding:', encoding || 'text');
    if (window.FileOpener) {
        window.FileOpener.openFile(fileName, content, encoding);
    }
};

console.log('FileOpener bridge loaded');
