# Models

Verified VRM files used by Avatar Studio. All files stored locally in `models/`,
fetched once from the official sources below.

## Verification

Every file was verified by parsing the binary glTF header (magic `glTF`) and the
embedded JSON chunk before being committed. All three files are valid VRM
(spec 0.0 or 1.0) with a humanoid bone hierarchy and expressions.

| File | Size (bytes) | VRM spec | SHA-256 |
|------|-------------:|----------|---------|
| `three-vrm-girl.vrm` | 5,558,600 | 0.0 | `e6e179dea8bafc712900b5012628166a64e982d45566fb705d2ec52f579279b9` |
| `Seed-san.vrm` | 10,917,800 | 1.0 | `624d0d554bc205bbdc33e22a68a2c3c20edebb3e573011ead8878a65e5329b23` |
| `VRM1_Constraint_Twist_Sample.vrm` | 10,776,032 | 1.0 | `12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2` |

## Sources & licenses

### three-vrm-girl.vrm
- **Source**: pixiv three-vrm repository (official sample)
  `https://github.com/pixiv/three-vrm/tree/v0.6.4/packages/three-vrm/examples/models/three-vrm-girl.vrm`
  (downloaded via raw.githubusercontent.com)
- **Author**: pixiv Inc.
- **License**: VRoid Hub permissive license — everyone may use, modify and
  redistribute; personal/commercial use allowed; credit not required.
  `https://hub.vroid.com/license?allowed_to_use_user=everyone&characterization_allowed_user=everyone&corporate_commercial_use=allow&credit=unnecessary&modification=allow&personal_commercial_use=profit&redistribution=allow&sexual_expression=allow&version=1&violent_expression=allow`

### Seed-san.vrm
- **Source**: VRM Consortium vrm-specification repository (official sample)
  `https://github.com/vrm-c/vrm-specification/tree/master/samples/Seed-san/vrm/Seed-san.vrm`
  (downloaded via raw.githubusercontent.com)
- **Author**: VirtualCast, Inc.
- **License**: VRM 1.0 permissive license
  `https://vrm.dev/licenses/1.0/` (VRMC_vrm extension "Everyone can use, modify and redistribute the data.")

### VRM1_Constraint_Twist_Sample.vrm
- **Source**: pixiv three-vrm repository (technical sample, bone-constraint tests)
  `https://github.com/pixiv/three-vrm/tree/dev/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm`
  (downloaded via raw.githubusercontent.com)
- **License**: permissive sample model for testing constraints; included for
  completeness / bone-count diversity.

## Notes

- Fetched once on 2026-08-16; never re-downloaded in loops.
- The two gallery characters used for screenshots are `three-vrm-girl.vrm`
  (VRM 0.0) and `Seed-san.vrm` (VRM 1.0).
- VRM 0.x models are re-oriented to face the camera via `VRMUtils.rotateVRM0`.