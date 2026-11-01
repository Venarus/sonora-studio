# Security Policy

## 🔒 Offline & Local-First Security Guarantee

**SONORA Studio** is strictly designed as an **offline-first desktop application**:

1. **Zero External Data Transmission:** No microphone audio, recorded waveform, processed file, or user metadata is ever transmitted over the network or uploaded to external servers.
2. **No Cloud Dependency:** SONORA does not use external cloud APIs, telemetry collectors, tracking SDKs, or paid subscriptions. All digital signal processing (DSP) and AI speech enhancement algorithms run locally on the user's host CPU.
3. **Safe Filesystem Operations:** SONORA Studio never silently overwrites existing audio files. Processed recordings are generated non-destructively, preserving raw recording takes.

---

## 🛡️ Reporting a Vulnerability

If you discover a potential security vulnerability or file safety issue in SONORA Studio, please report it responsibly:

1. **Do not create a public GitHub issue** for undisclosed security vulnerabilities.
2. Please open a Private Security Advisory via GitHub's **"Report a vulnerability"** tab under the Security tab of the repository, or email `security@sonora-audio.local`.
3. Provide detailed steps to reproduce the issue and any relevant system logs.
4. We will acknowledge receipt of your report within 48 hours and work with you on a resolution.
