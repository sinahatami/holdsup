import pkg from "../../package.json";

/**
 * The release this build of the site is. release-please raises it in package.json with
 * every release, so it is read at build time and costs no request. The API's version is on
 * each receipt; the two can differ for a while, since the API is deployed by hand.
 */
export const APP_VERSION: string = pkg.version;
