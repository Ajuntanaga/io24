# Verification

The linked-recall orchestration was added test-first.  Before implementation,
all three focused contracts failed because the action was absent.  After the
minimal implementation:

```text
python3 -m unittest tests.test_io24_linked_recall_action
Ran 3 tests in 0.001s — OK

python3 -m unittest tests.test_io24_linked_recall_action \
  tests.test_io24_factory_slap_action tests.test_io24_host_delay_action
Ran 7 tests in 0.002s — OK
```

The contracts cover exact Channel-2 selector/link order, final link-off state,
link cleanup when the slot-3 recall raises, and refusal of an already-linked
baseline before any write.

Final hardware-free discovery after the live run and documentation changes:

```text
python3 -m unittest discover -s tests
Ran 208 tests in 196.907s
OK (skipped=1)
```

The one skip is the expected absent historical artifact.  The sole diagnostic
was the pre-existing unclosed-WAV `ResourceWarning` in
`re/cp34_current_slot_survey.py:260`.
