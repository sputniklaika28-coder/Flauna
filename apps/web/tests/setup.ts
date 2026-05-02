import "@testing-library/jest-dom";

// jsdom does not implement Element.prototype.scrollIntoView; stub it so that
// components which call it during effects do not crash in tests.
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {
    /* no-op */
  };
}
