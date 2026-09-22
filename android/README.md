# io24 Android Controller

This directory is reserved for the standalone Android companion app for the
PreSonus Revelator io24.

The intended runtime connection is direct:

```text
Android phone -> USB-C -> Revelator io24
```

The Linux Host remains a separate application. The first Android milestone is
a read-only USB control probe that verifies device control can remain connected
while Android records audio from the io24.
