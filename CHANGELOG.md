# Changelog

## 1.6.3

### Added
- English, Ukrainian, and Simplified Chinese (zh-CN) interface translations with browser-language detection and a language selector.
- Authenticated, read-only UFW integration diagnostics for missing binaries/configuration mounts, `NET_ADMIN`, and the Fail2Ban socket path.

### Fixed
- Use `bcrypt` directly so newer `bcrypt` releases no longer trigger the `bcrypt.__about__` compatibility error; existing bcrypt password hashes remain verifiable.
- Treat failed or unrecognized UFW status as unknown and disable the status toggle instead of presenting the firewall as inactive.
- Keep locale and login flows usable when browser storage is blocked, and show localized errors without exposing raw backend details.

### Security
- Automatic firewall rollback remains disabled; diagnostics do not claim to verify the Fail2Ban daemon's liveness or the source of the UFW configuration mount.

### Acknowledgements
- Thanks to [@mtmt2012](https://github.com/mtmt2012) and [@jiriteach](https://github.com/jiriteach) for the reports and feedback in [#44](https://github.com/weby-homelab/ufw-gui/issues/44) and [#45](https://github.com/weby-homelab/ufw-gui/issues/45).
