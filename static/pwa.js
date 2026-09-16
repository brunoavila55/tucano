if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js");
    });
}

let tucanoDeferredInstallPrompt;
window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    tucanoDeferredInstallPrompt = event;
    const banner = document.getElementById("install-banner-android");
    if (banner) banner.hidden = false;
});

function tucanoInstallApp() {
    if (!tucanoDeferredInstallPrompt) return;
    tucanoDeferredInstallPrompt.prompt();
    tucanoDeferredInstallPrompt = null;
    const banner = document.getElementById("install-banner-android");
    if (banner) banner.hidden = true;
}

(function showIosInstallBannerIfNeeded() {
    const isIos = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
    const isStandalone =
        window.navigator.standalone === true || window.matchMedia("(display-mode: standalone)").matches;
    if (isIos && !isStandalone) {
        const banner = document.getElementById("install-banner-ios");
        if (banner) banner.hidden = false;
    }
})();

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

function tucanoSubscribeToPush(vapidPublicKey) {
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !vapidPublicKey) return;
    navigator.serviceWorker.ready
        .then((registration) =>
            registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
            })
        )
        .then((subscription) =>
            fetch("/perfil/push/inscrever/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(subscription.toJSON()),
            })
        )
        .catch(() => {});
}
