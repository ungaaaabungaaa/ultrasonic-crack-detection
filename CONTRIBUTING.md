# Contributing

Run the tests, lint, format check, frozen benchmark, and installed-wheel check before a pull request. Explain the input, change, observed result, and remaining limit. Keep calibration and evaluation specimen IDs separate, with all repeated captures in one group. A change to simulation assumptions or threshold fitting is a new benchmark version; record it and keep prior results recoverable.

Add behavior fixtures for signal timing, filtering, invalid sampling, quality exclusions, threshold fitting, and count denominators. Do not tune parameters on held-out results or remove rejected captures to improve a metric. Indication scores are not probabilities. Synthetic results do not establish physical crack accuracy.

Do not upload private scans, instrument identifiers, credentials, large recordings, caches, or virtual environments. Measured-data contributions need clear permission, provenance, calibration details, independent labels, and a license. No hardware integration should be described as tested without instrument evidence.
