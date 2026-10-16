// No-op replacement for @evidence-dev/telemetry 2.1.3.
// The original sends anonymous usage events to Segment (on by default) on
// every dev/build/sources run and query. This keeps the same exports and
// does nothing, so no usage data ever leaves the machine.
const logEvent = async () => {};
const logQueryEvent = async () => {};

module.exports = { logEvent, logQueryEvent };
