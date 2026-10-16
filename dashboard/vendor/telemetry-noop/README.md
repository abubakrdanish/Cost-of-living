# telemetry-noop

Evidence 40.x ships `@evidence-dev/telemetry`, which sends anonymous usage
events to Segment by default (event name, OS, Node version, an MD5 of your home
directory path, hashed source/query names). Its documented opt-out
(`send_anonymous_usage_stats: no`) is read from `evidence.settings.json` in the
current working directory, and the `SEND_ANONYMOUS_USAGE_STATS` environment
variable is ignored whenever that file is absent, so it is easy to miss.

`package.json` in `dashboard/` therefore uses an npm `overrides` entry to
replace the package with this local no-op module. The settings-file opt-out is
also set (`dashboard/evidence.settings.json`) as a second layer.

Check it is in effect:

    cd dashboard
    node -e "console.log(require('@evidence-dev/telemetry/package.json').version)"   # 2.1.3-noop
    npm ls @segment/analytics-node                                                    # (empty)
