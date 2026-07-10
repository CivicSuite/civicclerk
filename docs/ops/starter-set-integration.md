# CivicMeetings Starter-Set Integration

Status: maintained module-side proof helper for the CivicCore + CivicSunshine + CivicMeetings starter set.

The umbrella installer owns the generated starter-set packages. CivicMeetings owns
the module contract it contributes to that package: version, CivicCore runtime
pin, selectability, and honest boundary language.

Run the module-side check from this repo:

```powershell
python scripts\check_starter_set_integration.py --umbrella-root ..\civicsuite --require-archives
```

The check verifies that:

- the umbrella `clerk-core` profile installs CivicCore first, then CivicRecords
  AI, then CivicMeetings;
- CivicMeetings is selectable at v1.0.2 and records the CivicCore 1.2.1 runtime
  dependency used by the current module release;
- CivicSunshine is paired at v1.7.3;
- the umbrella release contract requires package workflow proof with
  `--staff-mode bearer --workflow-proof`;
- Linux and Windows starter-set release archives exist when
  `--require-archives` is used.

This is starter-set install/test evidence. It is not a claim that CivicMeetings and
CivicSunshine exchange live workflow records through a cross-module business
API yet, and it is not macOS lifecycle certification.
