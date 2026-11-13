// Plain values only: both Playwright and the mock API server (run by Node as it is) import this.

/** A check that is still running when it is opened: the browser follows it live. */
export const CHECK_ID = "11111111-1111-4111-8111-111111111111";

/** A check that has finished: the server draws it from what the API stored. */
export const DONE_ID = "22222222-2222-4222-8222-222222222222";

/** A well-formed id that nothing was stored under. */
export const MISSING_ID = "33333333-3333-4333-8333-333333333333";

/** The check a re-check of DONE_ID's claim starts: done, with the reader's statistic. */
export const RECHECK_ID = "55555555-5555-4555-8555-555555555555";

/** A finished check of two claims: one the check is sure of, one it holds back (P4.5). */
export const UNSURE_ID = "66666666-6666-4666-8666-666666666666";
