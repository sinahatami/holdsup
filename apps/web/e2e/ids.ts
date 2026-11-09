// Plain values only: both Playwright and the mock API server (run by Node as it is) import this.

/** A check that is still running when it is opened: the browser follows it live. */
export const CHECK_ID = "11111111-1111-4111-8111-111111111111";

/** A check that has finished: the server draws it from what the API stored. */
export const DONE_ID = "22222222-2222-4222-8222-222222222222";

/** A well-formed id that nothing was stored under. */
export const MISSING_ID = "33333333-3333-4333-8333-333333333333";
