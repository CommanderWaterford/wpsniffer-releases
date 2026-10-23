# WPSniffer releases

[WPSniffer](https://wpsniffer.com) is a free, open-source command-line malware
scanner for WordPress and PHP sites. It scans the files on your own server
against thousands of community [YARA Forge](https://yarahq.github.io/) rules
with the [YARA-X](https://virustotal.github.io/yara-x/) engine. No account, no
license key, nothing phones home.

This repository holds the public releases and the issue tracker.

## Install

Requires Python 3.8 or newer.

    python3 -m venv ~/wpsniffer
    ~/wpsniffer/bin/pip install wpsniffer
    ~/wpsniffer/bin/wpsniffer malware-scan --progress /var/www/html

Every release on the [Releases page](https://github.com/CommanderWaterford/wpsniffer-releases/releases)
carries the same wheel and source archive that are published to
[PyPI](https://pypi.org/project/wpsniffer/). On a server without access to
PyPI, download the wheel and install it with `pip install ./wpsniffer-*.whl`.

## Documentation

- [Install and first scan](https://wpsniffer.com/docs/)
- [Options reference](https://wpsniffer.com/docs/#options)
- [Rule packages and custom YARA rules](https://wpsniffer.com/rules/)
- [Guides](https://wpsniffer.com/guides/): scanning over SSH, finding webshells in
  uploads, recently modified files, scanning every site on a server, nightly
  scans with cron, and cleanup after a scan finds matches
- [FAQ](https://wpsniffer.com/faq/)

## Bugs and feature requests

Open an [issue](https://github.com/CommanderWaterford/wpsniffer-releases/issues).
Include the command you ran, the output of `wpsniffer version`, and, for a
suspected false positive, the rule name from the `signature_id` column.

## License

WPSniffer is released under the [GNU GPLv3](https://wpsniffer.com/license/).
The complete source is included in every release archive. Detection rules are
written by their respective authors and distributed by YARA Forge under their
own licenses; WPSniffer credits the author of every matching rule in its
reports.
