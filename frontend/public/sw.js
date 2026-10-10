/**
 * Service worker for RentRadar WebPush notifications.
 *
 * Registered by AlertSignup.tsx when a user subscribes to price alerts.
 * Receives push events from the backend (channels/webpush.py) and shows
 * a browser notification with the alert payload.
 */

self.addEventListener("push", (event) => {
  let data = { title: "RentRadar", body: "New listings match your search!" };

  if (event.data) {
    try {
      data = event.data.json();
    } catch {
      // If the payload isn't JSON, use the text as the notification body.
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: "/favicon.ico",
    badge: "/favicon.ico",
    data: { url: data.url || "/" },
    // Vibration pattern for mobile: short-long-short
    vibrate: [100, 200, 100],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Open the app when the user clicks a notification.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      // Focus an existing tab if one is already open.
      for (const client of windowClients) {
        if (client.url === targetUrl && "focus" in client) {
          return client.focus();
        }
      }
      // Otherwise open a new tab.
      return clients.openWindow(targetUrl);
    })
  );
});
