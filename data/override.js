"use strict";
window.ready_eddy = false;

document.addEventListener('DOMContentLoaded', waitondom, false);

var waitondom = function () {
    for (let frame of document.querySelectorAll('iframe')){
        console.log("querySelectorAll('iframe')")
        if (frame.contentWindow !== "undefined") {
            console.log('contentWindow !== "undefined"')
            for (const key of Object.keys(_navigator)) {
                obj = frame.contentWindow.navigator;
                Object.defineProperty(obj, key, {
                    value:() => _navigator[key]
                });
            }
        }
    }
}

for (const key of Object.keys(_navigator)) {
    obj = window.navigator;
    Object.defineProperty(obj, key, {
        value: _navigator[key],
    });
}