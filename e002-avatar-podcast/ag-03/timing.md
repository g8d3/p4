# Timing — ag-03 TTS

## Audio durations

| File | Duration |
|------|----------|
| `persona_a.mp3` | 202.1 sec (3 min 22 sec) |
| `persona_b.mp3` | 66.3 sec (1 min 6 sec) |
| **Total** | **268.4 sec (4 min 28 sec)** |

## Dialogue sequence (speaker order from script)

```
A → B → A → B → A  [Intro]
B → A → B → A → B → A  [Topic 1: Qué es p4]
A → B → A → B → A → B → A  [Topic 2: Educación]
A → B → A → B → A → B → A  [Topic 3: Creación de contenido]
A → B → A → B → A → B → A  [Topic 4: Comunicaciones públicas]
B → A → B → A  [Topic 5: Por qué esto importa]
A → B → A → B → B → A → A → B → A → B → A  [Closing]
```

## Notes for ag-04

- Use `persona_a.mp3` for all A lines, `persona_b.mp3` for all B lines.
- Alternating segments can be cut by timestamp ratio: A duration ≈ 3× B duration.
- To reconstruct the conversation timeline, map each script line to its proportional position in the respective audio file.
