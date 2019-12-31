"use strict";
window.ready_eddy = false;

document.addEventListener('DOMContentLoaded', waitondom, false);
window.RTCPeerConnection = undefined;
window.webkitRTCPeerConnection = undefined;
var waitondom = function () {
    for (let frame of window.document.querySelectorAll('iframe')) {
        if (frame.contentWindow !== "undefined") {
            for (const key of Object.keys(_navigator)) {
                obj = frame.contentWindow.navigator;
                Object.defineProperty(obj, key, {
                    value: _navigator[key]
                });
            }
        }
    }
}

for (const key of Object.keys(_navigator)) {
    obj = window.navigator;
    Object.defineProperty(obj, key, {
        value: _navigator[key]
    });
}

jQuery.noConflict();
