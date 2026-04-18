# Oneiric Memory Template

Persistent state template for a single dream pipeline run. Hermes populates this at each stage checkpoint.

```
dream_id: {{uuid}}
status: pending | transcribed | analyzed | illustrated | narrated | composed
audio_path: {{path}}
transcript: {{text}}
analysis: {{DreamAnalysis JSON}}
frames: [{{paths}}]
narration_audio: {{path}}
film_path: {{path}}
created_at: {{iso8601}}
```
