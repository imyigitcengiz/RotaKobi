import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";

// Firebase configuration from user request
const firebaseConfig = {
  apiKey: "AIzaSyDKwMqrryelevM1l-4YVhKBEHhh5av65jw",
  authDomain: "coolops-bf6a0.firebaseapp.com",
  projectId: "coolops-bf6a0",
  storageBucket: "coolops-bf6a0.firebasestorage.app",
  messagingSenderId: "1063306383609",
  appId: "1:1063306383609:web:79105eaaaba29e2eecd228"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
window.firebaseApp = app;

console.log("Firebase client SDK başarıyla başlatıldı.");
