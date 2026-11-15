"use strict";

// Landing / sign-in page (v1.1 spec 4.10). Signed-out visitors can reach
// only this page (and invite links); the server sends everything else here
// with ?next=<page they wanted>.

(() => {
    const { Api, Session } = window.Collectivize;
    const $ = (id) => document.getElementById(id);

    const wanted = new URLSearchParams(location.search).get("next");
    const next = Session.nextPage(wanted);
    const adminEntrance = new URLSearchParams(location.search).has("admin");

    // Already signed in: carry on to the page they asked for, or, with none
    // (e.g. the nav's wordmark link), show the home page without the sign-in
    // form: a click anywhere but the logo (which spins) opens Discover.
    Api.get("/api/session", {}, { redirectOnSignOut: false })
        .then(({ signed_in: signedIn }) => {
            if (!signedIn || adminEntrance) return; // /admin always shows the form
            if (wanted) location.replace(next);
            else showSignedIn();
        })
        .catch(() => {});

    function showSignedIn() {
        $("signin").hidden = true;
        document.body.classList.add("is-signed-in");
        const isLogo = (target) => target instanceof Element && target.closest("#logo3d");
        document.addEventListener("click", (event) => {
            if (!isLogo(event.target)) location.assign("discover");
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") location.assign("discover");
        });
    }

    // Sent here because the account was ended from somewhere else.
    const NOTICES = {
        deleted: "That account was deleted.",
        signed_out: "You were signed out.",
        expired: "Your sign-in ended. Sign in again.",
    };
    const notice = NOTICES[new URLSearchParams(location.search).get("notice")];
    if (notice) $("signin-message").textContent = notice;

    new window.SignInForm({ done: () => location.replace(next) });
})();
