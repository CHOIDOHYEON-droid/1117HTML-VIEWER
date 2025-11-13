const CACHE_NAME = 'html-viewer-v2';
const urlsToCache = [
  '/index.html',
  '/manifest.json',
  '/share-handler.html'
];

// 설치 이벤트
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache opened');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.log('Cache failed:', err);
      })
  );
  self.skipWaiting();
});

// 활성화 이벤트
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch 이벤트 - Network First 전략
self.addEventListener('fetch', event => {
  // POST 요청 처리 (파일 공유)
  if (event.request.method === 'POST') {
    event.respondWith(
      (async () => {
        const formData = await event.request.formData();
        const file = formData.get('file');

        if (file) {
          // 파일을 클라이언트에 전달
          const cache = await caches.open(CACHE_NAME);
          const response = await cache.match('/share-handler.html');

          if (response) {
            const text = await response.text();
            const modifiedText = text.replace(
              '</head>',
              `<script>window.sharedFile = new File([${JSON.stringify(await file.text())}], "${file.name}", {type: "${file.type}"});</script></head>`
            );
            return new Response(modifiedText, {
              headers: { 'Content-Type': 'text/html' }
            });
          }
        }

        return Response.redirect('/index.html', 303);
      })()
    );
    return;
  }

  // GET 요청 처리
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // 성공하면 캐시 업데이트
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });
        }
        return response;
      })
      .catch(() => {
        // 네트워크 실패 시 캐시에서 가져오기
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            // 캐시에도 없으면 오프라인 페이지 반환
            return caches.match('/index.html');
          });
      })
  );
});
