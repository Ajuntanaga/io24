# Host preset-domain quarantine and HPF UI correction

This run addresses the reported Channel-1 preset disruption and the two
conflicting Host controls both labelled Low cut.

Authorized implementation scope:

- prevent ordinary Host snapshots/startup/cached reapply from moving or
  disabling device preset slots;
- keep an explicit backend opt-in for intentional selector replay;
- remove Channel-2 experiment and deferred custom-firmware controls from the
  production Effects page;
- distinguish the fixed 80 Hz preamp HPF from the digital Fat Channel HPF;
- provide Off/40/80/160 plus an exact 24 Hz..1 kHz Advanced Host control;
- tightly peer-review decisions in the dedicated Claude session.

No HPF display-correlation USB write, audio action, Host launch, slot write,
firmware modification, Wine action, installation, publication, Git setup, or
Obsidian write is authorized by this run record. A live physical-display probe
requires a separate explicit gate.
