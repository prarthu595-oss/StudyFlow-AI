importScripts(
    "https://www.gstatic.com/firebasejs/12.9.0/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/12.9.0/firebase-messaging-compat.js"
);

firebase.initializeApp({
  apiKey: "AIzaSyDRpZ4446HQItNsIUHrks2z1bT-Dcc8cyk",
  authDomain: "studyflow-ai-b7674.firebaseapp.com",
  projectId: "studyflow-ai-b7674",
  storageBucket: "studyflow-ai-b7674.firebasestorage.app",
  messagingSenderId: "417963887257",
  appId: "1:417963887257:web:65fbe78dadb5ab37308608"   
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    console.log("Background notification received:", payload);

    const notificationTitle =
        payload.notification?.title || "StudyFlow AI";

    const notificationOptions = {
        body:
            payload.notification?.body ||
            "You have a new study reminder.",
        icon: "/static/icon.png"
    };

    self.registration.showNotification(
        notificationTitle,
        notificationOptions
    );
});