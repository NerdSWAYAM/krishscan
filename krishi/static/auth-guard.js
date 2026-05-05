(function () {
    var auth = window.KrishiScanAuth || {};
    var isAuthenticated = Boolean(auth.isAuthenticated);
    var loginUrl = auth.loginUrl || "/login/";
    var path = window.location.pathname || "/";

    var publicPaths = [
        "/",
        "/login/",
        "/signup/",
        "/send-otp/"
    ];

    if (publicPaths.indexOf(path) !== -1) {
        return;
    }

    if (!isAuthenticated) {
        var next = encodeURIComponent(window.location.pathname + window.location.search);
        var separator = loginUrl.indexOf("?") === -1 ? "?" : "&";
        window.location.replace(loginUrl + separator + "next=" + next);
    }
})();
